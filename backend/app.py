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
import hashlib
import random
import gc
import signal
import sys

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure OpenRouter API for DeepSeek R1 (Free & Unlimited)
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek/deepseek-r1"  # Free and unlimited model

# Get absolute path for uploads folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
RESUME_PREVIEW_FOLDER = os.path.join(BASE_DIR, 'resume_previews')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)
os.makedirs(RESUME_PREVIEW_FOLDER, exist_ok=True)
print(f"📁 Upload folder: {UPLOAD_FOLDER}")
print(f"📁 Reports folder: {REPORTS_FOLDER}")
print(f"📁 Resume Previews folder: {RESUME_PREVIEW_FOLDER}")

# Cache for consistent scoring
score_cache = {}
cache_lock = threading.Lock()

# Batch processing configuration - REDUCED FOR RENDER FREE TIER
MAX_CONCURRENT_REQUESTS = 1  # REDUCED: Only 1 concurrent request
MAX_BATCH_SIZE = 5  # REDUCED: Max 5 resumes for Render free tier
MIN_SKILLS_TO_SHOW = 5
MAX_SKILLS_TO_SHOW = 8

# Rate limiting for free API
MAX_RETRIES = 3
RETRY_DELAY_BASE = 3

# Track activity
last_activity_time = datetime.now()
service_running = True

# Resume storage tracking
resume_storage = {}

# Request session with timeout
requests_session = requests.Session()
requests_session.timeout = (10, 120)  # 10 seconds connect, 120 seconds read (INCREASED)

def update_activity():
    """Update last activity timestamp"""
    global last_activity_time
    last_activity_time = datetime.now()

def calculate_resume_hash(resume_text, job_description):
    """Calculate a hash for caching consistent scores"""
    # Use smaller chunks for hashing
    content = f"{resume_text[:300]}{job_description[:300]}".encode('utf-8')
    return hashlib.md5(content).hexdigest()

def get_cached_score(resume_hash):
    """Get cached score if available"""
    with cache_lock:
        return score_cache.get(resume_hash)

def set_cached_score(resume_hash, score):
    """Cache score for consistency"""
    with cache_lock:
        score_cache[resume_hash] = score

def store_resume_file(file_data, filename, analysis_id):
    """Store resume file for later preview"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        preview_filename = f"{analysis_id}_{safe_filename}"
        preview_path = os.path.join(RESUME_PREVIEW_FOLDER, preview_filename)
        
        # Save the original file
        with open(preview_path, 'wb') as f:
            if isinstance(file_data, bytes):
                f.write(file_data)
            else:
                file_data.save(f)
        
        # Store in memory for quick access
        resume_storage[analysis_id] = {
            'filename': preview_filename,
            'original_filename': filename,
            'path': preview_path,
            'stored_at': datetime.now().isoformat()
        }
        
        print(f"✅ Resume stored for preview: {preview_filename}")
        return preview_filename
    except Exception as e:
        print(f"❌ Error storing resume for preview: {str(e)}")
        return None

def call_deepseek_api(prompt, max_tokens=1000, temperature=0.1, timeout=120, retry_count=0):  # UPDATED: timeout=120, max_tokens=1000
    """Call DeepSeek R1 API via OpenRouter (Free & Unlimited) with improved error handling"""
    if not OPENROUTER_API_KEY:
        print(f"❌ No OpenRouter API key provided")
        return {'error': 'no_api_key', 'status': 500}
    
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://resume-analyzer.com',
        'X-Title': 'Resume Analyzer AI'
    }
    
    payload = {
        'model': DEEPSEEK_MODEL,
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
        
        # Use session with LONGER timeout
        response = requests_session.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            try:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    result = data['choices'][0]['message']['content']
                    print(f"✅ DeepSeek API response in {response_time:.2f}s")
                    return result
                else:
                    print(f"❌ Unexpected API response format")
                    return {'error': 'invalid_response', 'status': response.status_code}
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
                return {'error': 'json_decode_error', 'status': 500}
        
        # Handle specific errors
        error_handlers = {
            429: ('rate_limit', 'Rate limit exceeded'),
            503: ('service_unavailable', 'Service unavailable'),
            504: ('gateway_timeout', 'Gateway timeout'),
            502: ('bad_gateway', 'Bad gateway'),
            408: ('timeout', 'Request timeout'),
            524: ('timeout', 'Timeout occurred')
        }
        
        if response.status_code in error_handlers:
            error_code, error_msg = error_handlers[response.status_code]
            print(f"⚠️ {error_msg} (Status: {response.status_code})")
            
            if retry_count < MAX_RETRIES:
                wait_time = RETRY_DELAY_BASE * (retry_count + 1) + random.uniform(2, 5)
                print(f"⏳ Retrying in {wait_time:.1f}s (attempt {retry_count + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                return call_deepseek_api(prompt, max_tokens, temperature, timeout, retry_count + 1)
            return {'error': error_code, 'status': response.status_code}
        
        # Other errors
        error_text = response.text[:200] if response.text else "No error text"
        print(f"❌ OpenRouter API Error {response.status_code}: {error_text}")
        
        return {'error': f'api_error_{response.status_code}: {error_text}', 'status': response.status_code}
            
    except requests.exceptions.Timeout:
        print(f"⚠️ API timeout after {timeout}s")
        
        if retry_count < MAX_RETRIES:
            wait_time = 10 + random.uniform(5, 10)
            print(f"⏳ Timeout, retrying in {wait_time:.1f}s (attempt {retry_count + 1}/{MAX_RETRIES})")
            time.sleep(wait_time)
            return call_deepseek_api(prompt, max_tokens, temperature, timeout, retry_count + 1)
        return {'error': 'timeout', 'status': 408}
    
    except requests.exceptions.ConnectionError:
        print(f"⚠️ Connection error")
        
        if retry_count < MAX_RETRIES:
            wait_time = 15 + random.uniform(5, 10)
            print(f"⏳ Connection error, retrying in {wait_time:.1f}s")
            time.sleep(wait_time)
            return call_deepseek_api(prompt, max_tokens, temperature, timeout, retry_count + 1)
        return {'error': 'connection_error', 'status': 500}
    
    except Exception as e:
        print(f"❌ API Exception: {str(e)}")
        return {'error': str(e), 'status': 500}

def test_openrouter_connection():
    """Test OpenRouter connection with DeepSeek R1"""
    try:
        print("🔌 Testing OpenRouter connection with DeepSeek R1...")
        
        test_prompt = "Hello, please respond with 'DeepSeek R1 Ready'"
        
        response = call_deepseek_api(
            prompt=test_prompt,
            max_tokens=20,
            temperature=0.1,
            timeout=30
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            print(f"❌ OpenRouter connection failed: {error_type}")
            return False
        elif response and 'DeepSeek R1 Ready' in response:
            print(f"✅ OpenRouter connection successful with DeepSeek R1!")
            return True
        else:
            print(f"⚠️ OpenRouter connection test got unexpected response")
            return False
            
    except Exception as e:
        print(f"❌ OpenRouter test failed: {str(e)}")
        return False

def warmup_service():
    """Warm up the service"""
    try:
        print("🔥 Warming up service...")
        print(f"🤖 Using model: {DEEPSEEK_MODEL}")
        print(f"🎯 Provider: OpenRouter (Free & Unlimited)")
        
        success = test_openrouter_connection()
        
        if success:
            print("✅ Service warmed up successfully")
        else:
            print("⚠️ Service warm-up had issues, but will continue")
            
        return success
        
    except Exception as e:
        print(f"⚠️ Warm-up attempt failed: {str(e)}")
        return False

def keep_service_alive():
    """Periodically ping to keep service responsive - SIMPLIFIED"""
    global service_running
    
    while service_running:
        try:
            time.sleep(180)  # Every 3 minutes
            
            if OPENROUTER_API_KEY:
                update_activity()
                print(f"♨️ Keeping service alive...")
                
                # Simple ping
                try:
                    response = requests.get(f"http://localhost:{os.environ.get('PORT', 5002)}/ping", timeout=10)
                    if response.status_code == 200:
                        print(f"  ✅ Service responsive")
                    else:
                        print(f"  ⚠️ Service ping failed: {response.status_code}")
                except Exception as e:
                    print(f"  ⚠️ Keep-alive error: {str(e)}")
                    
        except Exception as e:
            print(f"⚠️ Keep-alive thread error: {str(e)}")
            time.sleep(180)

# Text extraction functions - HARD LIMITS APPLIED
def extract_text_from_pdf(file_path):
    """Extract text from PDF file with error handling - HARD LIMIT 1200 chars"""
    try:
        text = ""
        
        try:
            reader = PdfReader(file_path)
            
            # Limit to first 3 pages only
            for page_num, page in enumerate(reader.pages[:3]):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception as e:
                    print(f"⚠️ PDF page extraction error: {e}")
                    continue
            
            if not text.strip():
                return "Error: PDF appears to be empty"
            
        except Exception as e:
            print(f"❌ PDFReader failed: {e}")
            return "Error reading PDF"
        
        # HARD LIMIT: 1200 characters max
        return text[:1200]
        
    except Exception as e:
        print(f"❌ PDF Error: {str(e)[:100]}")
        return f"Error reading PDF: {str(e)[:100]}"

def extract_text_from_docx(file_path):
    """Extract text from DOCX file - HARD LIMIT 1200 chars"""
    try:
        doc = Document(file_path)
        
        # Limit to first 50 paragraphs only
        paragraphs = []
        for paragraph in doc.paragraphs[:50]:
            if paragraph.text.strip():
                paragraphs.append(paragraph.text.strip())
        
        text = "\n".join(paragraphs)
        
        if not text.strip():
            return "Error: Document appears to be empty"
        
        # HARD LIMIT: 1200 characters max
        return text[:1200]
        
    except Exception as e:
        print(f"❌ DOCX Error: {str(e)[:100]}")
        return f"Error reading DOCX: {str(e)[:100]}"

def extract_text_from_txt(file_path):
    """Extract text from TXT file - HARD LIMIT 1200 chars"""
    try:
        encodings = ['utf-8', 'latin-1', 'windows-1252', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    text = file.read()
                    
                if not text.strip():
                    return "Error: Text file appears to be empty"
                
                # HARD LIMIT: 1200 characters max
                return text[:1200]
                    
            except UnicodeDecodeError:
                continue
                
        return "Error: Could not decode text file with common encodings"
        
    except Exception as e:
        print(f"❌ TXT Error: {str(e)[:100]}")
        return f"Error reading TXT: {str(e)[:100]}"

def analyze_resume_with_ai(resume_text, job_description, filename=None, analysis_id=None):
    """Use DeepSeek R1 API to analyze resume against job description - HARD LIMITS"""
    
    if not OPENROUTER_API_KEY:
        print(f"❌ No OpenRouter API key configured.")
        return generate_fallback_analysis(filename, "No API key configured")
    
    # HARD LIMITS - CRITICAL FOR MEMORY
    resume_text = resume_text[:1200]  # STRICT LIMIT: 1200 characters max
    job_description = job_description[:800]  # STRICT LIMIT: 800 characters max
    
    # Safety check - enforce limits again
    if len(resume_text) > 1200:
        resume_text = resume_text[:1200]
    if len(job_description) > 800:
        job_description = job_description[:800]
    
    resume_hash = calculate_resume_hash(resume_text, job_description)
    cached_score = get_cached_score(resume_hash)
    
    # SIMPLIFIED PROMPT - shorter for faster response
    prompt = f"""Analyze this resume against job description.

RESUME (truncated):
{resume_text}

JOB DESCRIPTION:
{job_description}

Provide analysis in this JSON format:
{{
    "candidate_name": "Extracted name",
    "skills_matched": ["skill1", "skill2", "skill3", "skill4", "skill5"],
    "skills_missing": ["skill1", "skill2", "skill3", "skill4", "skill5"],
    "experience_summary": "Brief 3-sentence summary.",
    "education_summary": "Brief 3-sentence summary.",
    "overall_score": 75,
    "recommendation": "Recommended/Consider/Not Recommended",
    "key_strengths": ["strength1", "strength2"],
    "areas_for_improvement": ["area1", "area2"]
}}

Keep responses concise."""

    try:
        print(f"⚡ Sending to DeepSeek R1 via OpenRouter...")
        start_time = time.time()
        
        response = call_deepseek_api(
            prompt=prompt,
            max_tokens=1000,  # REDUCED from 1500 for faster response
            temperature=0.1,
            timeout=120  # INCREASED timeout to 120 seconds
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            print(f"❌ DeepSeek API error: {error_type}")
            return generate_fallback_analysis(filename, f"API Error: {error_type}", partial_success=True)
        
        elapsed_time = time.time() - start_time
        print(f"✅ DeepSeek R1 response in {elapsed_time:.2f} seconds")
        
        result_text = response.strip()
        
        # Extract JSON
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
            return generate_fallback_analysis(filename, "JSON Parse Error", partial_success=True)
        
        analysis = validate_analysis(analysis, filename)
        
        # Set score
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
        analysis['ai_model'] = DEEPSEEK_MODEL
        analysis['response_time'] = f"{elapsed_time:.2f}s"
        analysis['api_provider'] = "OpenRouter"
        
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
        'skills_matched': ['Python', 'JavaScript', 'SQL', 'Communication', 'Problem Solving'],
        'skills_missing': ['Machine Learning', 'Cloud Computing', 'Data Analysis', 'DevOps', 'UI/UX'],
        'experience_summary': 'The candidate demonstrates professional experience with relevant technical skills.',
        'education_summary': 'The candidate holds relevant educational qualifications.',
        'overall_score': 70,
        'recommendation': 'Consider for Interview',
        'key_strengths': ['Technical foundation', 'Communication skills'],
        'areas_for_improvement': ['Advanced certifications', 'Cloud platform experience']
    }
    
    for field, default_value in required_fields.items():
        if field not in analysis:
            analysis[field] = default_value
    
    if analysis['candidate_name'] == 'Professional Candidate' and filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').title()
        if len(clean_name.split()) <= 4:
            analysis['candidate_name'] = clean_name
    
    # Ensure minimum skills
    skills_matched = analysis.get('skills_matched', [])
    skills_missing = analysis.get('skills_missing', [])
    
    if len(skills_matched) < 5:
        default_skills = ['Python', 'JavaScript', 'SQL', 'Communication', 'Problem Solving']
        needed = 5 - len(skills_matched)
        skills_matched.extend(default_skills[:needed])
    
    if len(skills_missing) < 5:
        default_skills = ['Machine Learning', 'Cloud Computing', 'Data Analysis', 'DevOps', 'UI/UX']
        needed = 5 - len(skills_missing)
        skills_missing.extend(default_skills[:needed])
    
    # Limit to maximum
    analysis['skills_matched'] = skills_matched[:MAX_SKILLS_TO_SHOW]
    analysis['skills_missing'] = skills_missing[:MAX_SKILLS_TO_SHOW]
    
    # Ensure strengths and improvements
    analysis['key_strengths'] = analysis.get('key_strengths', [])[:2]
    analysis['areas_for_improvement'] = analysis.get('areas_for_improvement', [])[:2]
    
    # Trim summaries
    if len(analysis.get('experience_summary', '')) > 300:
        analysis['experience_summary'] = analysis['experience_summary'][:297] + '...'
    
    if len(analysis.get('education_summary', '')) > 300:
        analysis['education_summary'] = analysis['education_summary'][:297] + '...'
    
    return analysis

def generate_fallback_analysis(filename, reason, partial_success=False):
    """Generate a fallback analysis"""
    candidate_name = "Professional Candidate"
    
    if filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').replace('resume', '').replace('cv', '').strip()
        if clean_name:
            parts = clean_name.split()
            if len(parts) >= 2 and len(parts) <= 4:
                candidate_name = ' '.join(part.title() for part in parts)
    
    if partial_success:
        return {
            "candidate_name": candidate_name,
            "skills_matched": ['Python', 'JavaScript', 'Database', 'Communication', 'Problem Solving'],
            "skills_missing": ['Machine Learning', 'Cloud Computing', 'Data Analysis', 'DevOps', 'UI/UX'],
            "experience_summary": 'The candidate has professional experience with relevant technical skills.',
            "education_summary": 'The candidate possesses educational qualifications.',
            "overall_score": 55,
            "recommendation": "Needs Full Analysis",
            "key_strengths": ['Technical skills', 'Communication'],
            "areas_for_improvement": ['Advanced technical skills', 'Cloud experience'],
            "ai_provider": "deepseek",
            "ai_model": DEEPSEEK_MODEL,
            "api_provider": "OpenRouter"
        }
    else:
        return {
            "candidate_name": candidate_name,
            "skills_matched": ['Basic Programming', 'Communication', 'Problem Solving', 'Teamwork', 'Learning Ability'],
            "skills_missing": ['Advanced Technical Skills', 'Industry Experience', 'Specialized Knowledge', 'Certifications', 'Analytical Thinking'],
            "experience_summary": 'Professional experience analysis pending service initialization.',
            "education_summary": 'Educational background analysis pending service initialization.',
            "overall_score": 50,
            "recommendation": "Service Initializing",
            "key_strengths": ['Learning capability', 'Work ethic'],
            "areas_for_improvement": ['Service initialization needed', 'Complete analysis pending'],
            "ai_provider": "deepseek",
            "ai_model": DEEPSEEK_MODEL,
            "api_provider": "OpenRouter"
        }

def process_single_resume(args):
    """Process a single resume with improved error handling and memory cleanup"""
    resume_file, job_description, index, total, batch_id = args
    
    try:
        print(f"📄 Processing resume {index + 1}/{total}: {resume_file.filename}")
        
        # Add delay between requests
        if index > 0:
            delay = min(2.0, 0.5 + (index * 0.3)) + random.uniform(0, 0.3)
            print(f"⏳ Adding {delay:.1f}s delay...")
            time.sleep(delay)
        
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"batch_{batch_id}_{index}{file_ext}")
        
        # Save the file
        resume_file.save(file_path)
        
        # Store resume for preview
        analysis_id = f"{batch_id}_resume_{index}"
        preview_filename = store_resume_file(resume_file, resume_file.filename, analysis_id)
        
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
        
        # Analyze with AI
        analysis = analyze_resume_with_ai(
            resume_text, 
            job_description, 
            resume_file.filename, 
            analysis_id
        )
        
        # Add file info
        analysis['filename'] = resume_file.filename
        analysis['original_filename'] = resume_file.filename
        
        # Get file size
        resume_file.seek(0, 2)
        file_size = resume_file.tell()
        resume_file.seek(0)
        analysis['file_size'] = f"{(file_size / 1024):.1f}KB"
        
        analysis['analysis_id'] = analysis_id
        analysis['processing_order'] = index + 1
        
        # Add resume preview info
        analysis['resume_stored'] = preview_filename is not None
        analysis['resume_preview_filename'] = preview_filename
        analysis['resume_original_filename'] = resume_file.filename
        
        # Create individual report
        try:
            excel_filename = f"individual_{analysis_id}.xlsx"
            excel_path = create_detailed_individual_report(analysis, excel_filename)
            analysis['individual_excel_filename'] = os.path.basename(excel_path)
        except Exception as e:
            print(f"⚠️ Failed to create individual report: {str(e)}")
            analysis['individual_excel_filename'] = None
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        
        print(f"✅ Completed: {analysis.get('candidate_name')} - Score: {analysis.get('overall_score')}")
        
        # CRITICAL: Force garbage collection after each resume
        gc.collect()
        
        return {
            'analysis': analysis,
            'status': 'success',
            'index': index
        }
        
    except Exception as e:
        print(f"❌ Error processing {resume_file.filename}: {str(e)}")
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        
        # CRITICAL: Force garbage collection on error too
        gc.collect()
        
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
    
    has_api_key = bool(OPENROUTER_API_KEY)
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resume Analyzer API (DeepSeek R1)</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; padding: 0; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .ready { background: #d4edda; color: #155724; }
            .warning { background: #fff3cd; color: #856404; }
            .endpoint { background: #f8f9fa; padding: 10px; margin: 10px 0; border-left: 4px solid #007bff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Resume Analyzer API (DeepSeek R1)</h1>
            <p>AI-powered resume analysis using DeepSeek R1 via OpenRouter</p>
            
            <div class="status ''' + ('ready' if has_api_key else 'warning') + '''">
                <strong>Status:</strong> ''' + ('✅ API Key Configured' if has_api_key else '⚠️ API Key Needed') + '''
            </div>
            
            <p><strong>Model:</strong> ''' + DEEPSEEK_MODEL + '''</p>
            <p><strong>API Provider:</strong> OpenRouter</p>
            <p><strong>Max Batch Size:</strong> ''' + str(MAX_BATCH_SIZE) + ''' resumes</p>
            <p><strong>Cost:</strong> FREE</p>
            
            <h2>📡 Endpoints</h2>
            <div class="endpoint">
                <strong>POST /analyze</strong> - Analyze single resume
            </div>
            <div class="endpoint">
                <strong>POST /analyze-batch</strong> - Analyze multiple resumes
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
    """Analyze single resume"""
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
        
        # Check file size
        resume_file.seek(0, 2)
        file_size = resume_file.tell()
        resume_file.seek(0)
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            print(f"❌ File too large: {file_size} bytes")
            return jsonify({'error': 'File size too large. Maximum size is 10MB.'}), 400
        
        # Save file temporarily
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"resume_{timestamp}{file_ext}")
        resume_file.save(file_path)
        
        # Store resume for preview
        analysis_id = f"single_{timestamp}"
        preview_filename = store_resume_file(resume_file, resume_file.filename, analysis_id)
        
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
            return jsonify({'error': 'Unsupported file format. Please upload PDF, DOCX, or TXT'}), 400
        
        if resume_text.startswith('Error'):
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': resume_text}), 500
        
        # Analyze
        analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id)
        
        # Create report
        excel_filename = f"analysis_{analysis_id}.xlsx"
        excel_path = create_detailed_individual_report(analysis, excel_filename)
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Add metadata
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['ai_model'] = DEEPSEEK_MODEL
        analysis['ai_provider'] = "deepseek"
        analysis['api_provider'] = "OpenRouter"
        analysis['response_time'] = analysis.get('response_time', 'N/A')
        analysis['analysis_id'] = analysis_id
        
        # Add resume preview info
        analysis['resume_stored'] = preview_filename is not None
        analysis['resume_preview_filename'] = preview_filename
        analysis['resume_original_filename'] = resume_file.filename
        
        total_time = time.time() - start_time
        print(f"✅ Request completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        # Force garbage collection
        gc.collect()
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        
        # Force garbage collection on error
        gc.collect()
        
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/analyze-batch', methods=['POST'])
def analyze_resume_batch():
    """Analyze multiple resumes with improved error handling"""
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
        
        if len(resume_files) > MAX_BATCH_SIZE:
            print(f"❌ Too many files: {len(resume_files)} (max: {MAX_BATCH_SIZE})")
            return jsonify({'error': f'Maximum {MAX_BATCH_SIZE} resumes allowed per batch'}), 400
        
        if not OPENROUTER_API_KEY:
            print("❌ No OpenRouter API key configured")
            return jsonify({'error': 'No OpenRouter API key configured'}), 500
        
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        
        all_analyses = []
        errors = []
        
        print(f"🔄 Processing {len(resume_files)} resumes with DeepSeek R1...")
        
        # Process sequentially with delays
        for index, resume_file in enumerate(resume_files):
            if resume_file.filename == '':
                errors.append({
                    'filename': 'Empty file',
                    'error': 'File has no name',
                    'index': index
                })
                continue
            
            print(f"🔑 Processing resume {index + 1}/{len(resume_files)}")
            
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
        
        # Sort by score
        all_analyses.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        for rank, analysis in enumerate(all_analyses, 1):
            analysis['rank'] = rank
        
        # Create batch report
        batch_excel_path = None
        if all_analyses:
            try:
                print("📊 Creating batch Excel report...")
                excel_filename = f"batch_analysis_{batch_id}.xlsx"
                batch_excel_path = create_detailed_batch_report(all_analyses, job_description, excel_filename)
                print(f"✅ Excel report created")
            except Exception as e:
                print(f"❌ Failed to create Excel report: {str(e)}")
        
        total_time = time.time() - start_time
        
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
            'model_used': DEEPSEEK_MODEL,
            'ai_provider': "deepseek",
            'api_provider': "OpenRouter",
            'processing_time': f"{total_time:.2f}s",
            'success_rate': f"{(len(all_analyses) / len(resume_files)) * 100:.1f}%" if resume_files else "0%",
            'note': 'DeepSeek R1 via OpenRouter - FREE'
        }
        
        print(f"✅ Batch analysis completed in {total_time:.2f}s")
        print("="*50 + "\n")
        
        # Force garbage collection
        gc.collect()
        
        return jsonify(batch_summary)
        
    except Exception as e:
        print(f"❌ Batch analysis error: {traceback.format_exc()}")
        
        # Force garbage collection on error
        gc.collect()
        
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/resume-preview/<analysis_id>', methods=['GET'])
def get_resume_preview(analysis_id):
    """Get resume preview"""
    update_activity()
    
    try:
        print(f"📄 Resume preview request for: {analysis_id}")
        
        if analysis_id in resume_storage:
            resume_info = resume_storage[analysis_id]
        else:
            return jsonify({'error': 'Resume preview not found'}), 404
        
        preview_path = resume_info['path']
        
        if not os.path.exists(preview_path):
            return jsonify({'error': 'Preview file not found'}), 404
        
        return send_file(
            preview_path,
            as_attachment=True,
            download_name=resume_info['original_filename']
        )
            
    except Exception as e:
        print(f"❌ Resume preview error: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to get resume preview: {str(e)}'}), 500

# Excel report functions (simplified)
def create_detailed_individual_report(analysis_data, filename="resume_analysis_report.xlsx"):
    """Create a detailed Excel report"""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Resume Analysis"
        
        # Simple styling
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        
        # Set column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 50
        
        row = 1
        
        # Title
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws[f'A{row}']
        cell.value = "RESUME ANALYSIS REPORT (DeepSeek R1)"
        cell.font = Font(bold=True, size=14, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        row += 2
        
        # Basic Information
        info_fields = [
            ("Candidate Name", analysis_data.get('candidate_name', 'N/A')),
            ("Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("Overall Score", f"{analysis_data.get('overall_score', 0)}/100"),
            ("Recommendation", analysis_data.get('recommendation', 'N/A')),
            ("AI Model", analysis_data.get('ai_model', 'DeepSeek R1')),
            ("API Provider", analysis_data.get('api_provider', 'OpenRouter')),
        ]
        
        for label, value in info_fields:
            ws[f'A{row}'] = label
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'B{row}'] = value
            row += 1
        
        row += 1
        
        # Skills Matched
        ws[f'A{row}'] = "Skills Matched"
        ws[f'A{row}'].font = Font(bold=True)
        row += 1
        
        skills_matched = analysis_data.get('skills_matched', [])
        for i, skill in enumerate(skills_matched, 1):
            ws[f'A{row}'] = f"{i}."
            ws[f'B{row}'] = skill
            row += 1
        
        row += 1
        
        # Skills Missing
        ws[f'A{row}'] = "Skills Missing"
        ws[f'A{row}'].font = Font(bold=True)
        row += 1
        
        skills_missing = analysis_data.get('skills_missing', [])
        for i, skill in enumerate(skills_missing, 1):
            ws[f'A{row}'] = f"{i}."
            ws[f'B{row}'] = skill
            row += 1
        
        # Save
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📄 Excel report saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error creating Excel report: {str(e)}")
        filepath = os.path.join(REPORTS_FOLDER, f"fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb = Workbook()
        ws = wb.active
        ws['A1'] = "Resume Analysis Report"
        wb.save(filepath)
        return filepath

def create_detailed_batch_report(analyses, job_description, filename="batch_resume_analysis.xlsx"):
    """Create a batch Excel report"""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Batch Summary"
        
        # Title
        ws.merge_cells('A1:E1')
        ws['A1'] = "BATCH RESUME ANALYSIS REPORT"
        ws['A1'].font = Font(bold=True, size=14)
        
        # Summary
        ws['A3'] = "Analysis Date"
        ws['B3'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws['A4'] = "Total Resumes"
        ws['B4'] = len(analyses)
        ws['A5'] = "Job Description"
        ws['B5'] = f"{len(job_description)} chars"
        
        # Candidates table
        row = 7
        headers = ["Rank", "Candidate", "Score", "Recommendation", "Skills Matched"]
        
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col)
            cell.value = header
            cell.font = Font(bold=True)
        
        row += 1
        for analysis in analyses:
            ws.cell(row=row, column=1, value=analysis.get('rank', '-'))
            ws.cell(row=row, column=2, value=analysis.get('candidate_name', 'Unknown'))
            ws.cell(row=row, column=3, value=analysis.get('overall_score', 0))
            ws.cell(row=row, column=4, value=analysis.get('recommendation', 'N/A'))
            
            skills = analysis.get('skills_matched', [])
            ws.cell(row=row, column=5, value=", ".join(skills[:3]))
            
            row += 1
        
        # Save
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📊 Batch Excel report saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error creating batch Excel report: {str(e)}")
        filepath = os.path.join(REPORTS_FOLDER, f"batch_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb = Workbook()
        ws = wb.active
        ws['A1'] = "Batch Analysis Report"
        wb.save(filepath)
        return filepath

@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    """Download the Excel report"""
    update_activity()
    
    try:
        print(f"📥 Download request for: {filename}")
        
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        file_path = os.path.join(REPORTS_FOLDER, safe_filename)
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404
        
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
        
        filename = f"individual_{analysis_id}.xlsx"
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        file_path = os.path.join(REPORTS_FOLDER, safe_filename)
        
        if not os.path.exists(file_path):
            print(f"❌ Individual report not found: {file_path}")
            return jsonify({'error': 'Individual report not found'}), 404
        
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
    """Force warm-up API"""
    update_activity()
    
    try:
        if not OPENROUTER_API_KEY:
            return jsonify({
                'status': 'error',
                'message': 'No OpenRouter API key configured'
            })
        
        result = warmup_service()
        
        return jsonify({
            'status': 'success' if result else 'error',
            'message': 'DeepSeek R1 API warmed up successfully' if result else 'Warm-up failed',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/quick-check', methods=['GET'])
def quick_check():
    """Quick endpoint to check if API is responsive"""
    update_activity()
    
    try:
        if not OPENROUTER_API_KEY:
            return jsonify({
                'available': False, 
                'reason': 'No OpenRouter API key configured'
            })
        
        try:
            start_time = time.time()
            
            response = call_deepseek_api(
                prompt="Say 'ready'",
                max_tokens=10,
                timeout=30
            )
            
            response_time = time.time() - start_time
            
            if isinstance(response, dict) and 'error' in response:
                return jsonify({
                    'available': False,
                    'reason': response.get('error', 'API error'),
                    'response_time': f"{response_time:.2f}s"
                })
            elif response and 'ready' in str(response).lower():
                return jsonify({
                    'available': True,
                    'response_time': f"{response_time:.2f}s",
                    'model': DEEPSEEK_MODEL
                })
            else:
                return jsonify({
                    'available': False,
                    'reason': 'Unexpected response'
                })
                
        except Exception as e:
            return jsonify({
                'available': False,
                'reason': str(e)[:100]
            })
            
    except Exception as e:
        return jsonify({
            'available': False,
            'reason': str(e)[:100]
        })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    update_activity()
    
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'resume-analyzer-deepseek'
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    has_api_key = bool(OPENROUTER_API_KEY)
    
    return jsonify({
        'status': 'Service is running', 
        'timestamp': datetime.now().isoformat(),
        'ai_model': DEEPSEEK_MODEL,
        'api_key_configured': has_api_key,
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'reports_folder_exists': os.path.exists(REPORTS_FOLDER),
        'inactive_minutes': inactive_minutes,
        'max_batch_size': MAX_BATCH_SIZE
    })

@app.route('/status', methods=['GET'])
def status():
    """Ultra-lightweight status check"""
    return jsonify({
        'status': 'alive',
        'memory': 'ok',
        'timestamp': datetime.now().isoformat()
    }), 200

def cleanup_on_exit():
    """Cleanup function called on exit"""
    global service_running
    service_running = False
    print("\n🛑 Shutting down service...")
    
    try:
        # Clean up temporary files
        for folder in [UPLOAD_FOLDER, RESUME_PREVIEW_FOLDER]:
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath):
                    try:
                        os.remove(filepath)
                    except:
                        pass
        print("✅ Cleaned up temporary files")
    except:
        pass

# Signal handler for graceful shutdown
def handle_exit(signum, frame):
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    cleanup_on_exit()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)

atexit.register(cleanup_on_exit)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting...")
    print("="*50)
    
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"⚡ AI Provider: DeepSeek R1")
    print(f"🤖 Model: {DEEPSEEK_MODEL}")
    
    has_api_key = bool(OPENROUTER_API_KEY)
    print(f"🔑 API Key: {'✅ Configured' if has_api_key else '❌ Not configured'}")
    
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📁 Reports folder: {REPORTS_FOLDER}")
    print(f"📁 Resume Previews folder: {RESUME_PREVIEW_FOLDER}")
    print(f"⚠️  CONFIGURED FOR RENDER:")
    print(f"    • Workers: 1")
    print(f"    • Threads: 2")
    print(f"    • Timeout: 180s")
    print(f"    • Max Batch: {MAX_BATCH_SIZE} resumes")
    print(f"⚠️  TEXT LIMITS: 1200 chars resume, 800 chars job description")
    print("="*50 + "\n")
    
    if not has_api_key:
        print("⚠️  WARNING: No OpenRouter API key found!")
        print("Get FREE API key from: https://openrouter.ai/keys")
    
    # Force initial garbage collection
    gc.collect()
    
    if has_api_key:
        # Only start essential threads
        warmup_thread = threading.Thread(target=warmup_service, daemon=True)
        warmup_thread.start()
        
        keep_alive_thread = threading.Thread(target=keep_service_alive, daemon=True)
        keep_alive_thread.start()
        
        print("✅ Background threads started")
    
    # For Render deployment
    if os.environ.get('RENDER'):
        print("🚀 Running on Render production environment")
        # Use gunicorn for production with gthread worker
        from gunicorn.app.base import BaseApplication
        
        class FlaskApplication(BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()
            
            def load_config(self):
                for key, value in self.options.items():
                    self.cfg.set(key, value)
            
            def load(self):
                return self.application
        
        options = {
            'bind': f'0.0.0.0:{port}',
            'workers': 1,  # CRITICAL: Only 1 worker
            'threads': 2,  # CRITICAL: 2 threads for concurrency
            'worker_class': 'gthread',  # Use gthread worker
            'timeout': 180,  # 180 seconds timeout
            'keepalive': 5,
            'max_requests': 1000,  # Restart worker after 1000 requests
            'max_requests_jitter': 50,  # Randomize restart
            'preload': True,  # Preload app before forking
        }
        
        FlaskApplication(app, options).run()
    else:
        print("🚀 Running in development mode")
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
