from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PyPDF2 import PdfReader
from docx import Document
import os
import json
import time
from datetime import datetime
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
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure Groq API Keys
GROQ_API_KEYS = [
    os.getenv('GROQ_API_KEY_1'),
    os.getenv('GROQ_API_KEY_2'),
    os.getenv('GROQ_API_KEY_3')
]

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Track API status
warmup_complete = False
last_activity_time = datetime.now()

# Get absolute path for uploads folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

# Cache for consistent scoring
score_cache = {}
cache_lock = threading.Lock()

# Batch processing configuration
MAX_BATCH_SIZE = 10
MIN_SKILLS_TO_SHOW = 5
MAX_SKILLS_TO_SHOW = 8

# Rate limiting configuration
MIN_TIME_BETWEEN_REQUESTS = 30  # 30 seconds between API calls
MAX_RETRIES = 2

# Track key usage with timestamps
key_usage = {
    0: {'count': 0, 'last_request_time': None, 'cooling': False},
    1: {'count': 0, 'last_request_time': None, 'cooling': False},
    2: {'count': 0, 'last_request_time': None, 'cooling': False}
}

# Service running flag
service_running = True

def update_activity():
    """Update last activity timestamp"""
    global last_activity_time
    last_activity_time = datetime.now()

def safe_sleep(seconds):
    """Safe sleep that can be interrupted"""
    try:
        deadline = time.time() + seconds
        while time.time() < deadline and service_running:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            time.sleep(min(1.0, remaining))
    except Exception as e:
        logger.warning(f"Sleep interrupted: {e}")
        return

def get_available_key():
    """Get the next available Groq API key"""
    now = datetime.now()
    
    # First, check for available non-cooling keys
    available_keys = []
    for i, key in enumerate(GROQ_API_KEYS):
        if key and not key_usage[i]['cooling']:
            if key_usage[i]['last_request_time']:
                time_since_last = (now - key_usage[i]['last_request_time']).total_seconds()
                if time_since_last >= MIN_TIME_BETWEEN_REQUESTS:
                    available_keys.append((i, key))
            else:
                available_keys.append((i, key))
    
    if available_keys:
        # Return the key that hasn't been used the longest
        available_keys.sort(key=lambda x: key_usage[x[0]]['last_request_time'] 
                          if key_usage[x[0]]['last_request_time'] else datetime.min)
        i, key = available_keys[0]
        return key, i + 1
    
    # If no keys available immediately, find the one that will be available soonest
    soonest_time = float('inf')
    soonest_key = None
    soonest_index = None
    
    for i, key in enumerate(GROQ_API_KEYS):
        if key:
            if key_usage[i]['last_request_time']:
                time_since_last = (now - key_usage[i]['last_request_time']).total_seconds()
                time_until_available = max(0, MIN_TIME_BETWEEN_REQUESTS - time_since_last)
                if time_until_available < soonest_time:
                    soonest_time = time_until_updated_available
                    soonest_key = key
                    soonest_index = i
            else:
                # Key never used
                return key, i + 1
    
    if soonest_key and soonest_time <= 60:  # Only wait up to 60 seconds
        if soonest_time > 0:
            logger.info(f"⏳ Waiting {soonest_time:.1f}s for key {soonest_index + 1}...")
            safe_sleep(soonest_time + 1)
        return soonest_key, soonest_index + 1
    
    return None, None

def mark_key_used(key_index):
    """Mark a key as used and update timestamp"""
    key_usage[key_index]['count'] += 1
    key_usage[key_index]['last_request_time'] = datetime.now()

def mark_key_cooling(key_index, duration=60):
    """Mark a key as cooling down"""
    key_usage[key_index]['cooling'] = True
    
    def reset_cooling():
        safe_sleep(duration)
        key_usage[key_index]['cooling'] = False
        logger.info(f"✅ Key {key_index + 1} cooling completed")
    
    threading.Thread(target=reset_cooling, daemon=True).start()

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

def call_groq_api(prompt, api_key, max_tokens=1500, temperature=0.1, timeout=45):
    """Call Groq API with optimized settings"""
    if not api_key:
        logger.error(f"❌ No Groq API key provided")
        return {'error': 'no_api_key', 'status': 500}
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': GROQ_MODEL,
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
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                result = data['choices'][0]['message']['content']
                logger.info(f"✅ Groq API response in {response_time:.2f}s")
                return result
            else:
                logger.error(f"❌ Unexpected Groq API response format")
                return {'error': 'invalid_response', 'status': response.status_code}
        
        elif response.status_code == 429:
            logger.warning(f"❌ Rate limit exceeded for Groq API")
            return {'error': 'rate_limit', 'status': 429}
        
        elif response.status_code == 503:
            logger.warning(f"❌ Service unavailable for Groq API")
            return {'error': 'service_unavailable', 'status': 503}
        
        else:
            logger.error(f"❌ Groq API Error {response.status_code}: {response.text[:100]}")
            return {'error': f'api_error_{response.status_code}', 'status': response.status_code}
            
    except requests.exceptions.Timeout:
        logger.warning(f"❌ Groq API timeout after {timeout}s")
        return {'error': 'timeout', 'status': 408}
    
    except Exception as e:
        logger.error(f"❌ Groq API Exception: {str(e)}")
        return {'error': str(e), 'status': 500}

def warmup_groq_service():
    """Warm up Groq service connection"""
    global warmup_complete
    
    available_keys = sum(1 for key in GROQ_API_KEYS if key)
    if available_keys == 0:
        logger.warning("⚠️ Skipping Groq warm-up: No API keys configured")
        return False
    
    try:
        logger.info(f"🔥 Warming up Groq connection with {available_keys} keys...")
        
        for i, api_key in enumerate(GROQ_API_KEYS):
            if api_key:
                logger.info(f"  Testing key {i+1}...")
                start_time = time.time()
                
                response = call_groq_api(
                    prompt="Hello, are you ready? Respond with just 'ready'.",
                    api_key=api_key,
                    max_tokens=10,
                    temperature=0.1,
                    timeout=15
                )
                
                if isinstance(response, dict) and 'error' in response:
                    logger.warning(f"    ⚠️ Key {i+1} failed: {response.get('error')}")
                elif response and 'ready' in response.lower():
                    elapsed = time.time() - start_time
                    logger.info(f"    ✅ Key {i+1} warmed up in {elapsed:.2f}s")
                else:
                    logger.warning(f"    ⚠️ Key {i+1} warm-up failed: Unexpected response")
                
                if i < available_keys - 1:
                    safe_sleep(5)
        
        warmup_complete = True
        logger.info(f"✅ Groq service warmed up successfully")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Warm-up attempt failed: {str(e)}")
        return False

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        text = ""
        reader = PdfReader(file_path)
        
        for page in reader.pages[:5]:
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            except Exception as e:
                logger.warning(f"⚠️ PDF page extraction error: {e}")
                continue
        
        if not text.strip():
            return "Error: PDF appears to be empty"
        
        return text[:3000]  # Limit text length
    except Exception as e:
        logger.error(f"❌ PDF Error: {traceback.format_exc()}")
        return f"Error reading PDF: {str(e)[:100]}"

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs[:100] if paragraph.text.strip()])
        
        if not text.strip():
            return "Error: Document appears to be empty"
        
        return text[:3000]
    except Exception as e:
        logger.error(f"❌ DOCX Error: {traceback.format_exc()}")
        return f"Error reading DOCX: {str(e)}"

def extract_text_from_txt(file_path):
    """Extract text from TXT file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            text = file.read()
            
        if not text.strip():
            return "Error: Text file appears to be empty"
        
        return text[:3000]
    except Exception as e:
        logger.error(f"❌ TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

def analyze_resume_with_ai(resume_text, job_description, filename=None, api_key=None, key_index=None):
    """Use Groq API to analyze resume against job description"""
    
    if not api_key:
        logger.error(f"❌ No Groq API key provided for analysis.")
        return generate_fallback_analysis(filename, "No API key available")
    
    resume_text = resume_text[:3000]
    job_description = job_description[:1500]
    
    resume_hash = calculate_resume_hash(resume_text, job_description)
    cached_score = get_cached_score(resume_hash)
    
    prompt = f"""Analyze resume against job description:

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Provide analysis in this JSON format:
{{
    "candidate_name": "Extracted name or filename",
    "skills_matched": ["skill1", "skill2", "skill3", "skill4", "skill5"],
    "skills_missing": ["skill1", "skill2", "skill3", "skill4", "skill5"],
    "experience_summary": "3-4 sentence summary of professional experience",
    "education_summary": "3-4 sentence summary of educational background",
    "overall_score": 75,
    "recommendation": "Strongly Recommended/Recommended/Consider/Not Recommended",
    "key_strengths": ["strength1", "strength2", "strength3", "strength4"],
    "areas_for_improvement": ["area1", "area2", "area3", "area4"]
}}

IMPORTANT: Provide 5 skills in both matched and missing arrays."""

    try:
        logger.info(f"⚡ Sending to Groq API (Key {key_index})...")
        start_time = time.time()
        
        response = call_groq_api(
            prompt=prompt,
            api_key=api_key,
            max_tokens=1000,
            temperature=0.1,
            timeout=30
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            logger.error(f"❌ Groq API error: {error_type}")
            
            if 'rate_limit' in error_type:
                if key_index:
                    mark_key_cooling(key_index - 1, 120)
            
            return generate_fallback_analysis(filename, f"API Error: {error_type}", partial_success=True)
        
        elapsed_time = time.time() - start_time
        logger.info(f"✅ Groq API response in {elapsed_time:.2f} seconds (Key {key_index})")
        
        result_text = response.strip()
        
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = result_text[json_start:json_end]
        else:
            json_str = result_text
        
        json_str = json_str.replace('```json', '').replace('```', '').strip()
        
        try:
            analysis = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON Parse Error: {e}")
            return generate_fallback_analysis(filename, "JSON Parse Error", partial_success=True)
        
        analysis = validate_analysis(analysis, filename)
        
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
        
        analysis['ai_provider'] = "groq"
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['ai_model'] = GROQ_MODEL
        analysis['response_time'] = f"{elapsed_time:.2f}s"
        analysis['key_used'] = f"Key {key_index}"
        
        logger.info(f"✅ Analysis completed: {analysis['candidate_name']} (Score: {analysis['overall_score']}) (Key {key_index})")
        
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Groq Analysis Error: {str(e)}")
        return generate_fallback_analysis(filename, f"Analysis Error: {str(e)[:100]}")

def validate_analysis(analysis, filename):
    """Validate analysis data and fill missing fields"""
    required_fields = {
        'candidate_name': 'Professional Candidate',
        'skills_matched': ['Python', 'JavaScript', 'SQL', 'Communication', 'Problem Solving'],
        'skills_missing': ['Machine Learning', 'Cloud Computing', 'Data Analysis', 'DevOps', 'UI/UX'],
        'experience_summary': 'The candidate demonstrates professional experience with progressive responsibility.',
        'education_summary': 'The candidate holds relevant educational qualifications.',
        'overall_score': 70,
        'recommendation': 'Consider for Interview',
        'key_strengths': ['Technical foundation', 'Communication skills', 'Problem-solving', 'Teamwork'],
        'areas_for_improvement': ['Advanced certifications', 'Cloud experience', 'Project management', 'Industry knowledge']
    }
    
    for field, default_value in required_fields.items():
        if field not in analysis:
            analysis[field] = default_value
    
    if analysis['candidate_name'] == 'Professional Candidate' and filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').title()
        if len(clean_name.split()) <= 4:
            analysis['candidate_name'] = clean_name
    
    # Ensure 5 skills in each category
    skills_matched = analysis.get('skills_matched', [])
    skills_missing = analysis.get('skills_missing', [])
    
    if len(skills_matched) < MIN_SKILLS_TO_SHOW:
        default_skills = ['Python', 'JavaScript', 'SQL', 'Communication', 'Problem Solving']
        needed = MIN_SKILLS_TO_SHOW - len(skills_matched)
        skills_matched.extend(default_skills[:needed])
    
    if len(skills_missing) < MIN_SKILLS_TO_SHOW:
        default_skills = ['Machine Learning', 'Cloud Computing', 'Data Analysis', 'DevOps', 'UI/UX']
        needed = MIN_SKILLS_TO_SHOW - len(skills_missing)
        skills_missing.extend(default_skills[:needed])
    
    analysis['skills_matched'] = skills_matched[:MAX_SKILLS_TO_SHOW]
    analysis['skills_missing'] = skills_missing[:MAX_SKILLS_TO_SHOW]
    
    analysis['key_strengths'] = analysis.get('key_strengths', [])[:4]
    analysis['areas_for_improvement'] = analysis.get('areas_for_improvement', [])[:4]
    
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
    
    return {
        "candidate_name": candidate_name,
        "skills_matched": ['Basic Programming', 'Communication', 'Problem Solving', 'Teamwork', 'Adaptability'],
        "skills_missing": ['Advanced Skills', 'Industry Experience', 'Specialized Knowledge', 'Certifications', 'Leadership'],
        "experience_summary": 'Analysis limited due to service constraints. Please try again shortly.',
        "education_summary": 'Educational background analysis pending full service restoration.',
        "overall_score": 50,
        "recommendation": "Service Limited - Please Retry",
        "key_strengths": ['Learning ability', 'Work ethic', 'Communication', 'Technical aptitude'],
        "areas_for_improvement": ['Service restoration needed', 'Complete analysis pending', 'Detailed assessment required'],
        "ai_provider": "groq",
        "ai_status": "Limited",
        "ai_model": GROQ_MODEL,
    }

@app.route('/')
def home():
    """Root route - API landing page"""
    
    available_keys = sum(1 for key in GROQ_API_KEYS if key)
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resume Analyzer API</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; padding: 0; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #333; }}
            .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .ready {{ background: #d4edda; color: #155724; }}
            .warming {{ background: #fff3cd; color: #856404; }}
            .endpoint {{ background: #f8f9fa; padding: 10px; margin: 10px 0; border-left: 4px solid #007bff; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Resume Analyzer API</h1>
            <p>AI-powered resume analysis using Groq API</p>
            
            <div class="status {'ready' if warmup_complete else 'warming'}">
                <strong>Status:</strong> {'✅ Ready' if warmup_complete else '🔥 Warming up...'}
            </div>
            
            <p><strong>API Keys:</strong> {available_keys}/3 configured</p>
            <p><strong>Model:</strong> {GROQ_MODEL}</p>
            <p><strong>Processing:</strong> Sequential with 30s delay between requests</p>
            
            <h2>📡 Endpoints</h2>
            <div class="endpoint">
                <strong>POST /analyze</strong> - Analyze single resume
            </div>
            <div class="endpoint">
                <strong>POST /analyze-batch</strong> - Analyze multiple resumes (up to {MAX_BATCH_SIZE})
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
        logger.info("\n" + "="*50)
        logger.info("📥 New single analysis request received")
        
        if 'resume' not in request.files:
            return jsonify({'error': 'No resume file provided'}), 400
        
        if 'jobDescription' not in request.form:
            return jsonify({'error': 'No job description provided'}), 400
        
        resume_file = request.files['resume']
        job_description = request.form['jobDescription']
        
        if resume_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        file_path = os.path.join(UPLOAD_FOLDER, f"temp_{int(time.time())}{file_ext}")
        resume_file.save(file_path)
        
        # Extract text
        if file_ext == '.pdf':
            resume_text = extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            resume_text = extract_text_from_docx(file_path)
        elif file_ext == '.txt':
            resume_text = extract_text_from_txt(file_path)
        else:
            os.remove(file_path)
            return jsonify({'error': 'Unsupported file format'}), 400
        
        if resume_text.startswith('Error'):
            os.remove(file_path)
            return jsonify({'error': resume_text}), 500
        
        # Get API key
        api_key, key_index = get_available_key()
        if not api_key:
            os.remove(file_path)
            return jsonify({'error': 'No available Groq API key'}), 500
        
        # Mark key as used
        mark_key_used(key_index - 1)
        
        analysis = analyze_resume_with_ai(
            resume_text, 
            job_description, 
            resume_file.filename, 
            api_key,
            key_index
        )
        
        analysis['filename'] = resume_file.filename
        analysis['key_used'] = f"Key {key_index}"
        
        # Clean up
        os.remove(file_path)
        
        logger.info(f"✅ Single analysis completed in {analysis.get('response_time', 'N/A')}")
        logger.info("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/analyze-batch', methods=['POST'])
def analyze_resume_batch():
    """Analyze multiple resumes with sequential processing"""
    update_activity()
    
    try:
        logger.info("\n" + "="*50)
        logger.info("📦 New batch analysis request received")
        start_time = time.time()
        
        if 'resumes' not in request.files:
            return jsonify({'error': 'No resume files provided'}), 400
        
        resume_files = request.files.getlist('resumes')
        
        if 'jobDescription' not in request.form:
            return jsonify({'error': 'No job description provided'}), 400
        
        job_description = request.form['jobDescription']
        
        if len(resume_files) == 0:
            return jsonify({'error': 'No files selected'}), 400
        
        logger.info(f"📦 Batch size: {len(resume_files)} resumes")
        
        if len(resume_files) > MAX_BATCH_SIZE:
            return jsonify({'error': f'Maximum {MAX_BATCH_SIZE} resumes allowed per batch'}), 400
        
        available_keys = sum(1 for key in GROQ_API_KEYS if key)
        if available_keys == 0:
            return jsonify({'error': 'No Groq API keys configured'}), 500
        
        all_analyses = []
        errors = []
        
        logger.info(f"🔄 Processing {len(resume_files)} resumes...")
        
        # Process resumes sequentially
        for index, resume_file in enumerate(resume_files):
            try:
                if resume_file.filename == '':
                    errors.append({
                        'filename': 'Empty file',
                        'error': 'File has no name',
                        'index': index
                    })
                    continue
                
                logger.info(f"📄 Processing resume {index + 1}/{len(resume_files)}: {resume_file.filename}")
                
                # Extract text
                file_ext = os.path.splitext(resume_file.filename)[1].lower()
                file_path = os.path.join(UPLOAD_FOLDER, f"batch_{int(time.time())}_{index}{file_ext}")
                resume_file.save(file_path)
                
                if file_ext == '.pdf':
                    resume_text = extract_text_from_pdf(file_path)
                elif file_ext in ['.docx', '.doc']:
                    resume_text = extract_text_from_docx(file_path)
                elif file_ext == '.txt':
                    resume_text = extract_text_from_txt(file_path)
                else:
                    os.remove(file_path)
                    errors.append({
                        'filename': resume_file.filename,
                        'error': f'Unsupported format: {file_ext}',
                        'index': index
                    })
                    continue
                
                if resume_text.startswith('Error'):
                    os.remove(file_path)
                    errors.append({
                        'filename': resume_file.filename,
                        'error': resume_text,
                        'index': index
                    })
                    continue
                
                # Get API key
                api_key, key_index = get_available_key()
                if not api_key:
                    os.remove(file_path)
                    errors.append({
                        'filename': resume_file.filename,
                        'error': 'No available API key',
                        'index': index
                    })
                    continue
                
                # Mark key as used
                mark_key_used(key_index - 1)
                
                analysis = analyze_resume_with_ai(
                    resume_text, 
                    job_description, 
                    resume_file.filename, 
                    api_key,
                    key_index
                )
                
                analysis['filename'] = resume_file.filename
                analysis['processing_order'] = index + 1
                analysis['key_used'] = f"Key {key_index}"
                
                all_analyses.append(analysis)
                
                # Clean up
                os.remove(file_path)
                
                logger.info(f"✅ Completed: {analysis.get('candidate_name')} - Score: {analysis.get('overall_score')}")
                
                # Wait before next resume (except for last one)
                if index < len(resume_files) - 1:
                    logger.info(f"⏳ Waiting {MIN_TIME_BETWEEN_REQUESTS}s before next resume...")
                    safe_sleep(MIN_TIME_BETWEEN_REQUESTS)
                
            except Exception as e:
                logger.error(f"❌ Error processing resume {index + 1}: {str(e)}")
                errors.append({
                    'filename': resume_file.filename,
                    'error': f"Processing error: {str(e)[:100]}",
                    'index': index
                })
                continue
        
        # Sort by score
        all_analyses.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        for rank, analysis in enumerate(all_analyses, 1):
            analysis['rank'] = rank
        
        total_time = time.time() - start_time
        
        batch_summary = {
            'success': True,
            'total_files': len(resume_files),
            'successfully_analyzed': len(all_analyses),
            'failed_files': len(errors),
            'errors': errors,
            'analyses': all_analyses,
            'model_used': GROQ_MODEL,
            'ai_provider': "groq",
            'ai_status': "Warmed up" if warmup_complete else "Warming up",
            'processing_time': f"{total_time:.2f}s",
            'processing_method': 'sequential',
            'min_delay_between_requests': f"{MIN_TIME_BETWEEN_REQUESTS}s",
            'success_rate': f"{(len(all_analyses) / len(resume_files)) * 100:.1f}%" if resume_files else "0%",
            'note': 'Processing resumes sequentially with 30s delay between API calls'
        }
        
        logger.info(f"✅ Batch analysis completed in {total_time:.2f}s")
        logger.info(f"📊 Successfully analyzed: {len(all_analyses)}/{len(resume_files)}")
        logger.info("="*50 + "\n")
        
        return jsonify(batch_summary)
        
    except Exception as e:
        logger.error(f"❌ Batch analysis error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    update_activity()
    
    available_keys = sum(1 for key in GROQ_API_KEYS if key)
    
    return jsonify({
        'status': 'Service is running', 
        'timestamp': datetime.now().isoformat(),
        'ai_provider': 'groq',
        'ai_provider_configured': available_keys > 0,
        'model': GROQ_MODEL,
        'ai_warmup_complete': warmup_complete,
        'available_keys': available_keys,
        'max_batch_size': MAX_BATCH_SIZE,
        'min_time_between_requests': MIN_TIME_BETWEEN_REQUESTS
    })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    update_activity()
    
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'resume-analyzer',
        'ai_provider': 'groq'
    })

def cleanup_on_exit():
    """Cleanup function called on exit"""
    global service_running
    service_running = False
    logger.info("\n🛑 Shutting down service...")

atexit.register(cleanup_on_exit)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"⚡ AI Provider: Groq")
    print(f"🤖 Model: {GROQ_MODEL}")
    
    available_keys = sum(1 for key in GROQ_API_KEYS if key)
    print(f"🔑 API Keys: {available_keys}/3 configured")
    
    if available_keys > 0:
        warmup_thread = threading.Thread(target=warmup_groq_service, daemon=True)
        warmup_thread.start()
    
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
