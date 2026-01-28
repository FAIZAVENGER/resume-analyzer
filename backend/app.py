from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PyPDF2 import PdfReader
from docx import Document
import os
import json
import time
import concurrent.futures
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from dotenv import load_dotenv
import traceback
import threading
import atexit
import requests
import re
from collections import defaultdict
import queue
import asyncio
import hashlib
import random
from itertools import cycle
import gc
import sys

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure DeepSeek API
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')

# Available DeepSeek models
DEEPSEEK_MODELS = {
    'deepseek-chat': {
        'name': 'DeepSeek Chat',
        'context_length': 32768,
        'provider': 'DeepSeek',
        'description': 'General purpose chat model with 32K context',
        'status': 'production',
        'free_tier': False,
        'max_tokens': 8192
    },
    'deepseek-coder': {
        'name': 'DeepSeek Coder',
        'context_length': 16384,
        'provider': 'DeepSeek',
        'description': 'Specialized for coding tasks',
        'status': 'production',
        'free_tier': False,
        'max_tokens': 8192
    }
}

# Default working model
DEFAULT_MODEL = 'deepseek-chat'

# Track API status
warmup_complete = False
last_activity_time = datetime.now()

# Get absolute path for uploads folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)
print(f"📁 Upload folder: {UPLOAD_FOLDER}")
print(f"📁 Reports folder: {REPORTS_FOLDER}")

# Cache for consistent scoring (resume hash -> score)
score_cache = {}
cache_lock = threading.Lock()

# Batch processing configuration
MAX_CONCURRENT_REQUESTS = 3  # Max concurrent requests to DeepSeek API
MAX_BATCH_SIZE = 10  # Maximum number of resumes per batch
MAX_INDIVIDUAL_REPORTS = 10  # Limit individual Excel reports

# Rate limiting protection
MAX_RETRIES = 3
RETRY_DELAY_BASE = 3

# Memory optimization
service_running = True

def update_activity():
    """Update last activity timestamp"""
    global last_activity_time
    last_activity_time = datetime.now()

def calculate_resume_hash(resume_text, job_description):
    """Calculate a hash for caching consistent scores"""
    content = f"{resume_text[:500]}{job_description[:500]}".encode('utf-8')
    return hashlib.md5(content).hexdigest()

def get_cached_score(resume_hash):
    """Get cached score if available"""
    with cache_lock:
        return score_cache.get(resume_hash)

def set_cached_score(resume_hash, score):
    """Cache score for consistency"""
    with cache_lock:
        score_cache[resume_hash] = score

def call_deepseek_api(prompt, max_tokens=600, temperature=0.1, timeout=45, model_override=None, retry_count=0):
    """Call DeepSeek API with optimized settings"""
    if not DEEPSEEK_API_KEY:
        print(f"❌ No DeepSeek API key configured")
        return {'error': 'no_api_key', 'status': 500}
    
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    model_to_use = model_override or DEEPSEEK_MODEL or DEFAULT_MODEL
    
    # Optimized payload for batch processing
    payload = {
        'model': model_to_use,
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'max_tokens': max_tokens,
        'temperature': temperature,
        'top_p': 0.9,
        'stream': False,
        'stop': None
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                result = data['choices'][0]['message']['content']
                print(f"✅ DeepSeek API response in {response_time:.2f}s using {model_to_use}")
                return result
            else:
                print(f"❌ Unexpected DeepSeek API response format")
                return {'error': 'invalid_response', 'status': response.status_code}
        
        # Handle specific error codes
        if response.status_code == 429:
            print(f"❌ Rate limit exceeded for DeepSeek API")
            
            if retry_count < MAX_RETRIES:
                wait_time = RETRY_DELAY_BASE ** (retry_count + 1) + random.uniform(5, 10)
                print(f"⏳ Rate limited, retrying in {wait_time:.1f}s (attempt {retry_count + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                return call_deepseek_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1)
            return {'error': 'rate_limit', 'status': 429}
        
        elif response.status_code == 503:
            print(f"❌ Service unavailable for DeepSeek API")
            
            if retry_count < 2:
                wait_time = 15 + random.uniform(5, 10)
                print(f"⏳ Service unavailable, retrying in {wait_time:.1f}s")
                time.sleep(wait_time)
                return call_deepseek_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1)
            return {'error': 'service_unavailable', 'status': 503}
        
        else:
            print(f"❌ DeepSeek API Error {response.status_code}: {response.text[:100]}")
            return {'error': f'api_error_{response.status_code}', 'status': response.status_code}
            
    except requests.exceptions.Timeout:
        print(f"❌ DeepSeek API timeout after {timeout}s")
        
        if retry_count < 2:
            wait_time = 10 + random.uniform(5, 10)
            print(f"⏳ Timeout, retrying in {wait_time:.1f}s (attempt {retry_count + 1}/3)")
            time.sleep(wait_time)
            return call_deepseek_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1)
        return {'error': 'timeout', 'status': 408}
    
    except Exception as e:
        print(f"❌ DeepSeek API Exception: {str(e)}")
        return {'error': str(e), 'status': 500}

def warmup_deepseek_service():
    """Warm up DeepSeek service connection"""
    global warmup_complete
    
    if not DEEPSEEK_API_KEY:
        print("⚠️ Skipping DeepSeek warm-up: No API key configured")
        return False
    
    try:
        model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
        print(f"🔥 Warming up DeepSeek connection...")
        print(f"📊 Using model: {model_to_use}")
        
        start_time = time.time()
        
        response = call_deepseek_api(
            prompt="Hello, are you ready? Respond with just 'ready'.",
            max_tokens=10,
            temperature=0.1,
            timeout=15
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            print(f"  ⚠️ DeepSeek warm-up failed: {error_type}")
            return False
        elif response and 'ready' in response.lower():
            elapsed = time.time() - start_time
            print(f"✅ DeepSeek warmed up in {elapsed:.2f}s")
            warmup_complete = True
            return True
        else:
            print(f"  ⚠️ DeepSeek warm-up failed: Unexpected response")
            return False
        
    except Exception as e:
        print(f"⚠️ Warm-up attempt failed: {str(e)}")
        threading.Timer(30.0, warmup_deepseek_service).start()
        return False

def keep_service_warm():
    """Periodically send requests to keep DeepSeek service responsive"""
    global service_running
    
    while service_running:
        try:
            time.sleep(180)  # Check every 3 minutes
            
            if DEEPSEEK_API_KEY and warmup_complete:
                print(f"♨️ Keeping DeepSeek warm...")
                
                try:
                    response = call_deepseek_api(
                        prompt="Ping - just say 'pong'",
                        max_tokens=5,
                        timeout=20
                    )
                    if response and 'pong' in str(response).lower():
                        print(f"  ✅ DeepSeek keep-alive successful")
                    else:
                        print(f"  ⚠️ DeepSeek keep-alive got unexpected response")
                except Exception as e:
                    print(f"  ⚠️ DeepSeek keep-alive failed: {str(e)}")
                    
        except Exception as e:
            print(f"⚠️ Keep-warm thread error: {str(e)}")
            time.sleep(180)

# Text extraction functions
def extract_text_from_pdf(file_path):
    """Extract text from PDF file with error handling"""
    try:
        text = ""
        max_attempts = 2
        
        for attempt in range(max_attempts):
            try:
                reader = PdfReader(file_path)
                text = ""
                
                for page_num, page in enumerate(reader.pages[:4]):  # Reduced to 4 pages
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as e:
                        print(f"⚠️ PDF page extraction error: {e}")
                        continue
                
                if text.strip():
                    break
                    
            except Exception as e:
                print(f"❌ PDFReader attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read()
                            text = content.decode('utf-8', errors='ignore')
                            if text.strip():
                                words = text.split()
                                text = ' '.join(words[:600])  # Reduced length
                    except:
                        text = "Error: Could not extract text from PDF file"
        
        if not text.strip():
            return "Error: PDF appears to be empty or text could not be extracted"
        
        if len(text) > 2000:  # Reduced from 3000
            text = text[:2000] + "\n[Text truncated for optimal processing...]"
            
        return text
    except Exception as e:
        print(f"❌ PDF Error: {traceback.format_exc()}")
        return f"Error reading PDF: {str(e)[:100]}"

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs[:40] if paragraph.text.strip()])  # Reduced to 40
        
        if not text.strip():
            return "Error: Document appears to be empty"
        
        if len(text) > 2000:  # Reduced from 3000
            text = text[:2000] + "\n[Text truncated for optimal processing...]"
            
        return text
    except Exception as e:
        print(f"❌ DOCX Error: {traceback.format_exc()}")
        return f"Error reading DOCX: {str(e)}"

def extract_text_from_txt(file_path):
    """Extract text from TXT file"""
    try:
        encodings = ['utf-8', 'latin-1', 'windows-1252', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    text = file.read()
                    
                if not text.strip():
                    return "Error: Text file appears to be empty"
                
                if len(text) > 2000:  # Reduced from 3000
                    text = text[:2000] + "\n[Text truncated for optimal processing...]"
                    
                return text
            except UnicodeDecodeError:
                continue
                
        return "Error: Could not decode text file with common encodings"
        
    except Exception as e:
        print(f"❌ TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

def analyze_resume_with_ai(resume_text, job_description, filename=None, analysis_id=None):
    """Use DeepSeek API to analyze resume against job description with fallback"""
    
    if not DEEPSEEK_API_KEY:
        print(f"❌ No DeepSeek API key configured.")
        return generate_fallback_analysis(filename, "No API key available")
    
    # Optimize text length to reduce API load
    resume_text = resume_text[:1800]  # Reduced from 2500
    job_description = job_description[:800]  # Reduced from 1000
    
    # Check cache for consistent scoring
    resume_hash = calculate_resume_hash(resume_text, job_description)
    cached_score = get_cached_score(resume_hash)
    
    # Optimized prompt for faster processing and lower token usage
    prompt = f"""Analyze resume against job description:

RESUME (truncated):
{resume_text}

JOB DESCRIPTION (truncated):
{job_description}

Provide analysis in this JSON format only:
{{
    "candidate_name": "Extracted name or filename",
    "skills_matched": ["skill1", "skill2"],
    "skills_missing": ["skill1", "skill2"],
    "experience_summary": "One sentence summary",
    "education_summary": "One sentence summary",
    "overall_score": 75,
    "recommendation": "Recommended/Consider/Needs Improvement",
    "key_strengths": ["strength1", "strength2"],
    "areas_for_improvement": ["area1", "area2"]
}}"""

    try:
        model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
        print(f"⚡ Sending to DeepSeek API ({model_to_use})...")
        start_time = time.time()
        
        response = call_deepseek_api(
            prompt=prompt,
            max_tokens=400,  # Reduced from 500
            temperature=0.1,
            timeout=30  # Reduced from 45
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            print(f"❌ DeepSeek API error: {error_type}")
            
            # Return fallback analysis with partial success
            return generate_fallback_analysis(filename, f"API Error: {error_type}", partial_success=True)
        
        elapsed_time = time.time() - start_time
        print(f"✅ DeepSeek API response in {elapsed_time:.2f} seconds")
        
        result_text = response.strip()
        
        # Try to extract JSON
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = result_text[json_start:json_end]
        else:
            json_str = result_text
        
        json_str = json_str.replace('```json', '').replace('```', '').strip()
        
        try:
            analysis = json.loads(json_str)
            print(f"✅ Successfully parsed JSON response")
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            print(f"Response was: {result_text[:150]}")
            
            return generate_fallback_analysis(filename, "JSON Parse Error", partial_success=True)
        
        # Validate and fill missing fields
        analysis = validate_analysis(analysis, filename)
        
        # Ensure score is valid
        try:
            score = int(analysis['overall_score'])
            if score < 0 or score > 100:
                score = 70
            analysis['overall_score'] = score
            set_cached_score(resume_hash, score)
        except:
            if cached_score:
                analysis['overall_score'] = cached_score
            else:
                analysis['overall_score'] = 70
        
        # Add metadata
        analysis['ai_provider'] = "deepseek"
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['ai_model'] = model_to_use
        analysis['response_time'] = f"{elapsed_time:.2f}s"
        
        # Add analysis ID if provided
        if analysis_id:
            analysis['analysis_id'] = analysis_id
        
        print(f"✅ Analysis completed: {analysis['candidate_name']} (Score: {analysis['overall_score']})")
        
        return analysis
        
    except Exception as e:
        print(f"❌ DeepSeek Analysis Error: {str(e)}")
        return generate_fallback_analysis(filename, f"Analysis Error: {str(e)[:100]}")
    
def validate_analysis(analysis, filename):
    """Validate analysis data and fill missing fields"""
    required_fields = {
        'candidate_name': 'Professional Candidate',
        'skills_matched': ['Text analysis completed'],
        'skills_missing': ['Compare with job description'],
        'experience_summary': 'Candidate demonstrates relevant experience.',
        'education_summary': 'Candidate has appropriate qualifications.',
        'overall_score': 70,
        'recommendation': 'Consider for Interview',
        'key_strengths': ['Strong skills', 'Good communication'],
        'areas_for_improvement': ['Could benefit from training']
    }
    
    for field, default_value in required_fields.items():
        if field not in analysis:
            analysis[field] = default_value
    
    # Extract name from filename if candidate_name is default
    if analysis['candidate_name'] == 'Professional Candidate' and filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').title()
        if len(clean_name.split()) <= 4:
            analysis['candidate_name'] = clean_name
    
    # Limit array lengths to reduce response size
    analysis['skills_matched'] = analysis['skills_matched'][:3]
    analysis['skills_missing'] = analysis['skills_missing'][:3]
    analysis['key_strengths'] = analysis['key_strengths'][:2]
    analysis['areas_for_improvement'] = analysis['areas_for_improvement'][:2]
    
    return analysis

def generate_fallback_analysis(filename, reason, partial_success=False):
    """Generate a better fallback analysis based on filename"""
    candidate_name = "Professional Candidate"
    
    if filename:
        base_name = os.path.splitext(filename)[0]
        # Clean up the filename
        clean_name = base_name.replace('-', ' ').replace('_', ' ').replace('resume', '').replace('cv', '').strip()
        if clean_name:
            # Extract potential name parts
            parts = clean_name.split()
            if len(parts) >= 2 and len(parts) <= 4:
                candidate_name = ' '.join(part.title() for part in parts)
    
    if partial_success:
        return {
            "candidate_name": candidate_name,
            "skills_matched": ["Partial analysis completed", "Basic skill matching done"],
            "skills_missing": ["Full AI analysis pending", "Review required"],
            "experience_summary": f"Basic analysis completed. Full DeepSeek AI analysis was interrupted.",
            "education_summary": "Educational background requires full AI analysis.",
            "overall_score": 55,
            "recommendation": "Needs Full Analysis",
            "key_strengths": ["File processed successfully", "Ready for detailed analysis"],
            "areas_for_improvement": ["Complete AI analysis pending", "Try single file analysis"],
            "ai_provider": "deepseek",
            "ai_status": "Partial",
            "ai_model": DEEPSEEK_MODEL or DEFAULT_MODEL,
        }
    else:
        return {
            "candidate_name": candidate_name,
            "skills_matched": ["AI service is initializing", "Please try again in a moment"],
            "skills_missing": ["Detailed analysis coming soon", "Service warming up"],
            "experience_summary": f"The DeepSeek AI analysis service is currently warming up.",
            "education_summary": f"Educational background analysis will be available once the service is ready.",
            "overall_score": 50,
            "recommendation": "Service Warming Up - Please Retry",
            "key_strengths": ["Fast analysis once model is loaded", "Accurate skill matching"],
            "areas_for_improvement": ["Please wait for model to load", "Try again in 15 seconds"],
            "ai_provider": "deepseek",
            "ai_status": "Warming up",
            "ai_model": DEEPSEEK_MODEL or DEFAULT_MODEL,
        }

def process_single_resume(args):
    """Process a single resume with intelligent error handling"""
    resume_file, job_description, index, total, batch_id = args
    
    try:
        print(f"📄 Processing resume {index + 1}/{total}: {resume_file.filename}")
        
        # Add delay based on index to avoid overwhelming API
        if index > 0:
            delay = 0.5 + (index % 3) * 0.3  # Stagger delays
            print(f"⏳ Adding {delay:.1f}s delay before processing resume {index + 1}...")
            time.sleep(delay)
        
        # Save file temporarily
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"batch_{batch_id}_{index}{file_ext}")
        resume_file.save(file_path)
        
        # Extract text
        if file_ext == '.pdf':
            resume_text = extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            resume_text = extract_text_from_docx(file_path)
        elif file_ext == '.txt':
            resume_text = extract_text_from_txt(file_path)
        else:
            if os.path.exists(file_path):
                os.remove(file_path)
            return {
                'filename': resume_file.filename,
                'error': f'Unsupported format: {file_ext}',
                'status': 'failed',
                'index': index
            }
        
        if resume_text.startswith('Error'):
            if os.path.exists(file_path):
                os.remove(file_path)
            return {
                'filename': resume_file.filename,
                'error': resume_text,
                'status': 'failed',
                'index': index
            }
        
        # Analyze with DeepSeek API
        analysis_id = f"{batch_id}_resume_{index}"
        analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id)
        
        # Add file info
        analysis['filename'] = resume_file.filename
        analysis['original_filename'] = resume_file.filename
        
        # Get file size
        resume_file.seek(0, 2)
        file_size = resume_file.tell()
        resume_file.seek(0)
        analysis['file_size'] = f"{(file_size / 1024):.1f}KB"
        
        # Add metadata
        analysis['analysis_id'] = analysis_id
        analysis['processing_order'] = index + 1
        
        # Create individual Excel report
        try:
            if index < MAX_INDIVIDUAL_REPORTS:
                excel_filename = f"individual_{analysis_id}.xlsx"
                excel_path = create_excel_report(analysis, excel_filename)
                analysis['individual_excel_filename'] = os.path.basename(excel_path)
            else:
                analysis['individual_excel_filename'] = None
        except Exception as e:
            print(f"⚠️ Failed to create individual report: {str(e)}")
            analysis['individual_excel_filename'] = None
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        
        print(f"✅ Completed: {analysis.get('candidate_name')} - Score: {analysis.get('overall_score')}")
        
        return {
            'analysis': analysis,
            'status': 'success',
            'index': index
        }
        
    except Exception as e:
        print(f"❌ Error processing {resume_file.filename}: {str(e)}")
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return {
            'filename': resume_file.filename,
            'error': f"Processing error: {str(e)[:100]}",
            'status': 'failed',
            'index': index
        }

@app.route('/')
def home():
    """Root route - API landing page"""
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    warmup_status = "✅ Ready" if warmup_complete else "🔥 Warming up..."
    model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resume Analyzer API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; padding: 0; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .ready { background: #d4edda; color: #155724; }
            .warming { background: #fff3cd; color: #856404; }
            .endpoint { background: #f8f9fa; padding: 10px; margin: 10px 0; border-left: 4px solid #007bff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Resume Analyzer API</h1>
            <p>AI-powered resume analysis using DeepSeek API</p>
            
            <div class="status ''' + ('ready' if warmup_complete else 'warming') + '''">
                <strong>Status:</strong> ''' + warmup_status + '''
            </div>
            
            <p><strong>Model:</strong> ''' + model_to_use + '''</p>
            <p><strong>API Provider:</strong> DeepSeek</p>
            <p><strong>Max Batch Size:</strong> ''' + str(MAX_BATCH_SIZE) + ''' resumes</p>
            <p><strong>Processing:</strong> Sequential with delays</p>
            <p><strong>Last Activity:</strong> ''' + str(inactive_minutes) + ''' minutes ago</p>
            
            <h2>📡 Endpoints</h2>
            <div class="endpoint">
                <strong>POST /analyze</strong> - Analyze single resume
            </div>
            <div class="endpoint">
                <strong>POST /analyze-batch</strong> - Analyze multiple resumes (up to ''' + str(MAX_BATCH_SIZE) + ''')
            </div>
            <div class="endpoint">
                <strong>GET /health</strong> - Health check
            </div>
            <div class="endpoint">
                <strong>GET /ping</strong> - Keep-alive ping
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Main endpoint to analyze single resume"""
    update_activity()
    
    try:
        print("\n" + "="*50)
        print("📥 New single analysis request received")
        start_time = time.time()
        
        if 'resume' not in request.files:
            print("❌ No resume file in request")
            return jsonify({'error': 'No resume file provided'}), 400
        
        if 'jobDescription' not in request.form:
            print("❌ No job description in request")
            return jsonify({'error': 'No job description provided'}), 400
        
        resume_file = request.files['resume']
        job_description = request.form['jobDescription']
        
        print(f"📄 Resume file: {resume_file.filename}")
        print(f"📋 Job description: {len(job_description)} chars")
        
        if resume_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file size (15MB limit)
        resume_file.seek(0, 2)
        file_size = resume_file.tell()
        resume_file.seek(0)
        
        if file_size > 15 * 1024 * 1024:
            print(f"❌ File too large: {file_size} bytes")
            return jsonify({'error': 'File size too large. Maximum size is 15MB.'}), 400
        
        # Save the uploaded file
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"resume_{timestamp}{file_ext}")
        resume_file.save(file_path)
        print(f"💾 File saved to: {file_path}")
        
        # Extract text
        print(f"📖 Extracting text from {file_ext} file...")
        extraction_start = time.time()
        
        if file_ext == '.pdf':
            resume_text = extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            resume_text = extract_text_from_docx(file_path)
        elif file_ext == '.txt':
            resume_text = extract_text_from_txt(file_path)
        else:
            print(f"❌ Unsupported file format: {file_ext}")
            return jsonify({'error': 'Unsupported file format. Please upload PDF, DOCX, or TXT'}), 400
        
        if resume_text.startswith('Error'):
            print(f"❌ Text extraction error: {resume_text}")
            return jsonify({'error': resume_text}), 500
        
        extraction_time = time.time() - extraction_start
        print(f"✅ Extracted {len(resume_text)} characters in {extraction_time:.2f}s")
        
        # Check API configuration
        if not DEEPSEEK_API_KEY:
            print("❌ No DeepSeek API key configured")
            return jsonify({'error': 'DeepSeek API not configured'}), 500
        
        # Analyze with DeepSeek API
        model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
        print(f"⚡ Starting DeepSeek API analysis ({model_to_use})...")
        ai_start = time.time()
        
        analysis_id = f"single_{timestamp}"
        analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id)
        ai_time = time.time() - ai_start
        
        print(f"✅ DeepSeek API analysis completed in {ai_time:.2f}s")
        
        # Create Excel report
        print("📊 Creating Excel report...")
        excel_start = time.time()
        excel_filename = f"analysis_{analysis_id}.xlsx"
        excel_path = create_excel_report(analysis, excel_filename)
        excel_time = time.time() - excel_start
        print(f"✅ Excel report created in {excel_time:.2f}s: {excel_path}")
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Return analysis
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['ai_model'] = model_to_use
        analysis['ai_provider'] = "deepseek"
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['response_time'] = f"{ai_time:.2f}s"
        analysis['analysis_id'] = analysis_id
        
        total_time = time.time() - start_time
        print(f"✅ Request completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/analyze-batch', methods=['POST'])
def analyze_resume_batch():
    """Analyze multiple resumes against a single job description with staggered processing"""
    update_activity()
    
    try:
        print("\n" + "="*50)
        print("📦 New batch analysis request received")
        start_time = time.time()
        
        if 'resumes' not in request.files:
            print("❌ No 'resumes' key in request.files")
            return jsonify({'error': 'No resume files provided'}), 400
        
        resume_files = request.files.getlist('resumes')
        
        if 'jobDescription' not in request.form:
            print("❌ No job description in request")
            return jsonify({'error': 'No job description provided'}), 400
        
        job_description = request.form['jobDescription']
        
        if len(resume_files) == 0:
            print("❌ No files selected")
            return jsonify({'error': 'No files selected'}), 400
        
        print(f"📦 Batch size: {len(resume_files)} resumes")
        print(f"📋 Job description: {job_description[:100]}...")
        
        if len(resume_files) > MAX_BATCH_SIZE:
            print(f"❌ Too many files: {len(resume_files)} (max: {MAX_BATCH_SIZE})")
            return jsonify({'error': f'Maximum {MAX_BATCH_SIZE} resumes allowed per batch'}), 400
        
        # Check API configuration
        if not DEEPSEEK_API_KEY:
            print("❌ No DeepSeek API key configured")
            return jsonify({'error': 'DeepSeek API not configured'}), 500
        
        # Prepare batch analysis
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        
        # Process resumes sequentially with delays to avoid rate limits
        all_analyses = []
        errors = []
        
        print(f"🔄 Processing {len(resume_files)} resumes sequentially with delays...")
        
        for index, resume_file in enumerate(resume_files):
            if resume_file.filename == '':
                errors.append({
                    'filename': 'Empty file',
                    'error': 'File has no name',
                    'index': index
                })
                continue
            
            print(f"🔑 Processing resume {index + 1}/{len(resume_files)}")
            
            # Process the resume
            args = (resume_file, job_description, index, len(resume_files), batch_id)
            result = process_single_resume(args)
            
            if result['status'] == 'success':
                all_analyses.append(result['analysis'])
            else:
                errors.append({
                    'filename': result.get('filename', 'Unknown'),
                    'error': result.get('error', 'Unknown error'),
                    'index': result.get('index')
                })
            
            # Add delay between processing to avoid rate limits
            if index < len(resume_files) - 1:
                delay = 1.0 + random.uniform(0, 0.5)  # Increased base delay
                print(f"⏳ Adding {delay:.1f}s delay before next resume...")
                time.sleep(delay)
        
        print(f"\n📊 Batch processing complete. Successful: {len(all_analyses)}, Failed: {len(errors)}")
        
        # Sort by score
        all_analyses.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        # Add ranking
        for rank, analysis in enumerate(all_analyses, 1):
            analysis['rank'] = rank
        
        # Create batch Excel report
        batch_excel_path = None
        if all_analyses:
            try:
                print("📊 Creating batch Excel report...")
                excel_filename = f"batch_analysis_{batch_id}.xlsx"
                batch_excel_path = create_batch_excel_report(all_analyses, job_description, excel_filename)
                print(f"✅ Excel report created: {batch_excel_path}")
            except Exception as e:
                print(f"❌ Failed to create Excel report: {str(e)}")
        
        # Prepare response
        batch_summary = {
            'success': True,
            'total_files': len(resume_files),
            'successfully_analyzed': len(all_analyses),
            'failed_files': len(errors),
            'errors': errors,
            'batch_excel_filename': os.path.basename(batch_excel_path) if batch_excel_path else None,
            'batch_id': batch_id,
            'analyses': all_analyses,
            'model_used': DEEPSEEK_MODEL or DEFAULT_MODEL,
            'ai_provider': "deepseek",
            'ai_status': "Warmed up" if warmup_complete else "Warming up",
            'processing_time': f"{time.time() - start_time:.2f}s",
            'job_description_preview': job_description[:200] + ("..." if len(job_description) > 200 else ""),
            'batch_size': len(resume_files),
            'max_batch_size': MAX_BATCH_SIZE,
            'processing_method': 'staggered_sequential',
            'success_rate': f"{(len(all_analyses) / len(resume_files)) * 100:.1f}%" if resume_files else "0%"
        }
        
        print(f"✅ Batch analysis completed in {time.time() - start_time:.2f}s")
        print("="*50 + "\n")
        
        return jsonify(batch_summary)
        
    except Exception as e:
        print(f"❌ Batch analysis error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

def create_excel_report(analysis_data, filename="resume_analysis_report.xlsx"):
    """Create a simple Excel report with the analysis"""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Resume Analysis"
        
        # Simple styles
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        
        # Set column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 50
        
        row = 1
        
        # Title
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws[f'A{row}']
        cell.value = "Resume Analysis Report"
        cell.font = Font(bold=True, size=14, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        row += 2
        
        # Basic Information
        info_fields = [
            ("Candidate Name", analysis_data.get('candidate_name', 'N/A')),
            ("Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("Overall Score", f"{analysis_data.get('overall_score', 0)}/100"),
            ("Recommendation", analysis_data.get('recommendation', 'N/A')),
            ("AI Model", analysis_data.get('ai_model', 'DeepSeek AI')),
            ("AI Provider", analysis_data.get('ai_provider', 'DeepSeek')),
            ("AI Status", analysis_data.get('ai_status', 'N/A')),
        ]
        
        for label, value in info_fields:
            ws[f'A{row}'] = label
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'B{row}'] = value
            row += 1
        
        row += 1
        
        # Skills Matched
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws[f'A{row}']
        cell.value = "SKILLS MATCHED"
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        skills_matched = analysis_data.get('skills_matched', [])
        if skills_matched:
            for i, skill in enumerate(skills_matched, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'B{row}'] = skill
                row += 1
        else:
            ws[f'A{row}'] = "No matched skills found"
            row += 1
        
        row += 1
        
        # Skills Missing
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws[f'A{row}']
        cell.value = "SKILLS MISSING"
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        skills_missing = analysis_data.get('skills_missing', [])
        if skills_missing:
            for i, skill in enumerate(skills_missing, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'B{row}'] = skill
                row += 1
        else:
            ws[f'A{row}'] = "All required skills are present!"
            row += 1
        
        row += 1
        
        # Experience Summary
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws[f'A{row}']
        cell.value = "EXPERIENCE SUMMARY"
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws[f'A{row}']
        cell.value = analysis_data.get('experience_summary', 'N/A')
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[row].height = 60
        row += 2
        
        # Education Summary
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws[f'A{row}']
        cell.value = "EDUCATION SUMMARY"
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws[f'A{row}']
        cell.value = analysis_data.get('education_summary', 'N/A')
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[row].height = 40
        
        # Save the file
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📄 Excel report saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error creating Excel report: {str(e)}")
        # Return a fallback file path
        return os.path.join(REPORTS_FOLDER, f"fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

def create_batch_excel_report(analyses, job_description, filename="batch_resume_analysis.xlsx"):
    """Create a comprehensive batch Excel report"""
    try:
        wb = Workbook()
        
        # Summary Sheet
        ws_summary = wb.active
        ws_summary.title = "Summary"
        
        # Header styles
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        
        # Title
        ws_summary.merge_cells('A1:H1')
        title_cell = ws_summary['A1']
        title_cell.value = "Batch Resume Analysis Report"
        title_cell.font = Font(bold=True, size=16, color="FFFFFF")
        title_cell.fill = header_fill
        title_cell.alignment = Alignment(horizontal='center')
        
        # Summary Information
        ws_summary['A3'] = "Analysis Date"
        ws_summary['B3'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws_summary['A4'] = "Total Resumes"
        ws_summary['B4'] = len(analyses)
        ws_summary['A5'] = "AI Model"
        ws_summary['B5'] = DEEPSEEK_MODEL or DEFAULT_MODEL
        ws_summary['A6'] = "Processing Method"
        ws_summary['B6'] = "Staggered Sequential"
        ws_summary['A7'] = "Success Rate"
        success_rate = f"{(len(analyses) / len(analyses)) * 100:.1f}%" if analyses else "100%"
        ws_summary['B7'] = success_rate
        
        # Candidates Ranking Table
        row = 9
        headers = ["Rank", "Candidate Name", "ATS Score", "Recommendation", "AI Status", "Skills Matched", "Skills Missing"]
        for col, header in enumerate(headers, start=1):
            cell = ws_summary.cell(row=row, column=col)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
        
        row += 1
        for analysis in analyses:
            ws_summary.cell(row=row, column=1, value=analysis.get('rank', '-'))
            ws_summary.cell(row=row, column=2, value=analysis.get('candidate_name', 'Unknown'))
            ws_summary.cell(row=row, column=3, value=analysis.get('overall_score', 0))
            ws_summary.cell(row=row, column=4, value=analysis.get('recommendation', 'N/A'))
            
            ai_status = analysis.get('ai_status', 'N/A')
            ws_summary.cell(row=row, column=5, value=ai_status)
            
            # Skills matched (first 2)
            strengths = analysis.get('skills_matched', [])
            ws_summary.cell(row=row, column=6, value=", ".join(strengths[:2]) if strengths else "N/A")
            
            # Missing skills (first 2)
            missing = analysis.get('skills_missing', [])
            ws_summary.cell(row=row, column=7, value=", ".join(missing[:2]) if missing else "All matched")
            
            row += 1
        
        # Auto-adjust column widths
        for column in ws_summary.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 40)
            ws_summary.column_dimensions[column_letter].width = adjusted_width
        
        # Save the file
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📊 Batch Excel report saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error creating batch Excel report: {str(e)}")
        # Create a minimal file
        filepath = os.path.join(REPORTS_FOLDER, f"batch_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb = Workbook()
        ws = wb.active
        ws['A1'] = "Batch Analysis Report"
        ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws['A3'] = f"Total Candidates: {len(analyses)}"
        wb.save(filepath)
        return filepath

@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    """Download the Excel report"""
    update_activity()
    
    try:
        print(f"📥 Download request for: {filename}")
        
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        
        # Check reports folder
        file_path = os.path.join(REPORTS_FOLDER, safe_filename)
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404
        
        print(f"✅ File found! Size: {os.path.getsize(file_path)} bytes")
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=safe_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        print(f"❌ Download error: {traceback.format_exc()}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/download-individual/<analysis_id>', methods=['GET'])
def download_individual_report(analysis_id):
    """Download individual candidate report"""
    update_activity()
    
    try:
        print(f"📥 Download individual request for analysis ID: {analysis_id}")
        
        # Look for individual report file
        filename = f"individual_{analysis_id}.xlsx"
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        
        file_path = os.path.join(REPORTS_FOLDER, safe_filename)
        
        if not os.path.exists(file_path):
            print(f"❌ Individual report not found: {file_path}")
            return jsonify({'error': 'Individual report not found'}), 404
        
        print(f"✅ Individual file found! Size: {os.path.getsize(file_path)} bytes")
        
        download_name = f"candidate_report_{analysis_id}.xlsx"
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        print(f"❌ Individual download error: {traceback.format_exc()}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/warmup', methods=['GET'])
def force_warmup():
    """Force warm-up DeepSeek API"""
    update_activity()
    
    try:
        if not DEEPSEEK_API_KEY:
            return jsonify({
                'status': 'error',
                'message': 'DeepSeek API not configured',
                'warmup_complete': False
            })
        
        result = warmup_deepseek_service()
        
        return jsonify({
            'status': 'success' if result else 'error',
            'message': f'DeepSeek API warmed up successfully' if result else 'Warm-up failed',
            'warmup_complete': warmup_complete,
            'ai_provider': 'deepseek',
            'model': DEEPSEEK_MODEL or DEFAULT_MODEL,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'warmup_complete': False
        })

@app.route('/quick-check', methods=['GET'])
def quick_check():
    """Quick endpoint to check if DeepSeek API is responsive"""
    update_activity()
    
    try:
        if not DEEPSEEK_API_KEY:
            return jsonify({
                'available': False, 
                'reason': 'No DeepSeek API key configured',
                'warmup_complete': warmup_complete
            })
        
        if not warmup_complete:
            return jsonify({
                'available': False,
                'reason': 'DeepSeek API is warming up',
                'warmup_complete': False,
                'ai_provider': 'deepseek',
                'model': DEEPSEEK_MODEL or DEFAULT_MODEL
            })
        
        try:
            start_time = time.time()
            
            response = call_deepseek_api(
                prompt="Say 'ready'",
                max_tokens=10,
                timeout=15
            )
            
            response_time = time.time() - start_time
            
            if isinstance(response, dict) and 'error' in response:
                return jsonify({
                    'available': False,
                    'reason': response.get('error'),
                    'warmup_complete': warmup_complete
                })
            elif response and 'ready' in str(response).lower():
                return jsonify({
                    'available': True,
                    'response_time': f"{response_time:.2f}s",
                    'ai_provider': 'deepseek',
                    'model': DEEPSEEK_MODEL or DEFAULT_MODEL,
                    'warmup_complete': warmup_complete,
                    'max_batch_size': MAX_BATCH_SIZE
                })
            else:
                return jsonify({
                    'available': False,
                    'reason': 'Unexpected response',
                    'warmup_complete': warmup_complete
                })
                
        except Exception as e:
            return jsonify({
                'available': False,
                'reason': str(e)[:100],
                'warmup_complete': warmup_complete
            })
            
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'available': False,
            'reason': error_msg[:100],
            'status': 'error',
            'ai_provider': 'deepseek',
            'model': DEEPSEEK_MODEL or DEFAULT_MODEL,
            'warmup_complete': warmup_complete
        })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    update_activity()
    
    model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'resume-analyzer',
        'ai_provider': 'deepseek',
        'ai_warmup': warmup_complete,
        'model': model_to_use,
        'inactive_minutes': int((datetime.now() - last_activity_time).total_seconds() / 60),
        'keep_alive_active': True,
        'max_batch_size': MAX_BATCH_SIZE
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
    
    return jsonify({
        'status': 'Service is running', 
        'timestamp': datetime.now().isoformat(),
        'ai_provider': 'deepseek',
        'ai_provider_configured': bool(DEEPSEEK_API_KEY),
        'model': model_to_use,
        'ai_warmup_complete': warmup_complete,
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'reports_folder_exists': os.path.exists(REPORTS_FOLDER),
        'inactive_minutes': inactive_minutes,
        'version': '15.0.0',
        'optimizations': ['staggered_processing', 'single_api_key', 'reduced_token_usage', 'better_fallback'],
        'configuration': {
            'max_batch_size': MAX_BATCH_SIZE,
            'max_concurrent_requests': MAX_CONCURRENT_REQUESTS,
            'max_retries': MAX_RETRIES,
            'max_individual_reports': MAX_INDIVIDUAL_REPORTS
        },
        'processing_method': 'staggered_sequential_with_delays'
    })

def cleanup_on_exit():
    """Cleanup function called on exit"""
    global service_running
    service_running = False
    print("\n🛑 Shutting down service...")
    
    # Clean up temporary files
    try:
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        print("✅ Cleaned up temporary files")
    except:
        pass

# Register cleanup function
atexit.register(cleanup_on_exit)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting...")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"⚡ AI Provider: DeepSeek")
    model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
    print(f"🤖 Model: {model_to_use}")
    print(f"🔑 API Key: {'Configured' if DEEPSEEK_API_KEY else 'Not configured'}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📁 Reports folder: {REPORTS_FOLDER}")
    print(f"✅ Staggered Sequential Processing: Enabled")
    print(f"✅ Max Batch Size: {MAX_BATCH_SIZE} resumes")
    print(f"✅ Max Concurrent Requests: {MAX_CONCURRENT_REQUESTS}")
    print(f"✅ Optimized Token Usage: Enabled")
    print(f"✅ Better Fallback Analysis: Enabled")
    print("="*50 + "\n")
    
    if not DEEPSEEK_API_KEY:
        print("⚠️  WARNING: No DeepSeek API key found!")
        print("Please set DEEPSEEK_API_KEY in Render environment variables")
    
    # Enable garbage collection
    gc.enable()
    
    # Start warm-up in background
    if DEEPSEEK_API_KEY:
        warmup_thread = threading.Thread(target=warmup_deepseek_service, daemon=True)
        warmup_thread.start()
        
        # Start keep-warm thread
        keep_warm_thread = threading.Thread(target=keep_service_warm, daemon=True)
        keep_warm_thread.start()
        
        print("✅ Background threads started")
    
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode, threaded=True)
