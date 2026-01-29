from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from PyPDF2 import PdfReader, PdfWriter
from docx import Document
import os
import json
import time
import concurrent.futures
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from dotenv import load_dotenv
import traceback
import threading
import atexit
import requests
import re
import hashlib
import random
import gc
import sys
import base64
import io
import subprocess
import tempfile
import shutil
from pathlib import Path
from queue import Queue, Empty
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure Groq API Keys (3 keys for parallel processing)
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

# Batch processing configuration
MAX_CONCURRENT_REQUESTS = 3  # Use all 3 keys concurrently
MAX_BATCH_SIZE = 10
MIN_SKILLS_TO_SHOW = 5
MAX_SKILLS_TO_SHOW = 8

# Rate limiting configuration
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 65  # Wait 65 seconds when rate limited
REQUEST_TIMEOUT = 60
MIN_DELAY_BETWEEN_REQUESTS = 2  # Small delay between requests

# Track key usage with timestamps
key_usage = {
    0: {'count': 0, 'last_used': None, 'cooling': False, 'last_request_time': None, 'lock': threading.Lock()},
    1: {'count': 0, 'last_used': None, 'cooling': False, 'last_request_time': None, 'lock': threading.Lock()},
    2: {'count': 0, 'last_used': None, 'cooling': False, 'last_request_time': None, 'lock': threading.Lock()}
}

# Memory optimization
service_running = True

# Resume storage tracking
resume_storage = {}

# Background job tracking
background_jobs = {}
job_lock = threading.Lock()

def update_activity():
    """Update last activity timestamp"""
    global last_activity_time
    last_activity_time = datetime.now()

def get_next_available_key():
    """Get next available API key (non-blocking check)"""
    available_keys = []
    
    for i, key in enumerate(GROQ_API_KEYS):
        if not key:
            continue
            
        with key_usage[i]['lock']:
            # Skip if cooling down
            if key_usage[i]['cooling']:
                continue
            
            # Check if minimum delay has passed
            if key_usage[i]['last_request_time']:
                time_since = (datetime.now() - key_usage[i]['last_request_time']).total_seconds()
                if time_since < MIN_DELAY_BETWEEN_REQUESTS:
                    continue
            
            available_keys.append((i, key))
    
    if available_keys:
        # Return the least recently used key
        available_keys.sort(key=lambda x: key_usage[x[0]]['last_request_time'] or datetime.min)
        i, key = available_keys[0]
        return key, i
    
    return None, None

def mark_key_used(key_index):
    """Mark a key as used and update timestamp"""
    with key_usage[key_index]['lock']:
        key_usage[key_index]['count'] += 1
        key_usage[key_index]['last_request_time'] = datetime.now()
        key_usage[key_index]['last_used'] = datetime.now()

def mark_key_rate_limited(key_index):
    """Mark a key as rate limited and start cooldown"""
    with key_usage[key_index]['lock']:
        key_usage[key_index]['cooling'] = True
        key_usage[key_index]['last_used'] = datetime.now()
    
    def reset_cooling():
        logger.info(f"⏳ Key {key_index + 1} cooling for {RATE_LIMIT_DELAY}s...")
        time.sleep(RATE_LIMIT_DELAY)
        with key_usage[key_index]['lock']:
            key_usage[key_index]['cooling'] = False
        logger.info(f"✅ Key {key_index + 1} ready again")
    
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
        
        # Create PDF preview if not already PDF
        file_ext = os.path.splitext(filename)[1].lower()
        pdf_preview_path = None
        
        if file_ext == '.pdf':
            pdf_preview_path = preview_path
        elif file_ext == '.docx':
            try:
                pdf_preview_filename = f"{analysis_id}_{os.path.splitext(safe_filename)[0]}.pdf"
                pdf_preview_path = os.path.join(RESUME_PREVIEW_FOLDER, pdf_preview_filename)
                convert_docx_to_pdf(preview_path, pdf_preview_path)
            except Exception as e:
                logger.warning(f"⚠️ Could not convert DOCX to PDF: {str(e)}")
                pdf_preview_path = None
        
        # Store metadata
        resume_storage[analysis_id] = {
            'filename': filename,
            'original_path': preview_path,
            'pdf_preview_path': pdf_preview_path,
            'has_pdf_preview': pdf_preview_path is not None,
            'created_at': datetime.now(),
            'file_ext': file_ext
        }
        
        logger.info(f"✅ Resume stored for preview: {preview_filename}")
        
        return preview_path, pdf_preview_path
        
    except Exception as e:
        logger.error(f"❌ Error storing resume file: {str(e)}")
        return None, None

def convert_docx_to_pdf(docx_path, pdf_path):
    """Convert DOCX to PDF using LibreOffice"""
    try:
        output_dir = os.path.dirname(pdf_path)
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', output_dir,
            docx_path
        ], check=True, timeout=30, capture_output=True)
        
        # LibreOffice creates file with same name but .pdf extension
        generated_pdf = os.path.join(output_dir, os.path.splitext(os.path.basename(docx_path))[0] + '.pdf')
        if os.path.exists(generated_pdf) and generated_pdf != pdf_path:
            shutil.move(generated_pdf, pdf_path)
            
    except Exception as e:
        logger.warning(f"⚠️ LibreOffice conversion failed: {str(e)}")
        raise

def cleanup_resume_previews():
    """Clean up resume previews older than 1 hour"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=1)
        removed_count = 0
        
        # Clean up from storage dict
        keys_to_remove = []
        for analysis_id, info in resume_storage.items():
            if info['created_at'] < cutoff_time:
                keys_to_remove.append(analysis_id)
                
                # Remove files
                for path_key in ['original_path', 'pdf_preview_path']:
                    if info.get(path_key) and os.path.exists(info[path_key]):
                        try:
                            os.remove(info[path_key])
                            removed_count += 1
                        except:
                            pass
        
        for key in keys_to_remove:
            del resume_storage[key]
        
        if removed_count > 0:
            logger.info(f"🧹 Cleaned up {removed_count} old resume previews")
            
    except Exception as e:
        logger.error(f"❌ Error cleaning up resume previews: {str(e)}")

def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    try:
        pdf_reader = PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"❌ PDF extraction error: {str(e)}")
        return ""

def extract_text_from_docx(file):
    """Extract text from DOCX file"""
    try:
        doc = Document(file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        logger.error(f"❌ DOCX extraction error: {str(e)}")
        return ""

def call_groq_api(prompt, max_tokens=2000, temperature=0.3, key_index=None, timeout=60):
    """
    Call Groq API with retry logic for rate limits (NON-BLOCKING)
    Returns response or error dict
    """
    api_key, actual_key_index = get_next_available_key() if key_index is None else (GROQ_API_KEYS[key_index], key_index)
    
    if not api_key:
        return {'error': 'No API keys available', 'retry': True}
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"⚡ Calling Groq API (Key {actual_key_index + 1}, attempt {attempt + 1}/{MAX_RETRIES})...")
            
            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=data,
                timeout=timeout
            )
            
            # Mark key as used
            mark_key_used(actual_key_index)
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content']
                return {'error': 'Invalid API response format'}
            
            elif response.status_code == 429:
                logger.warning(f"⚠️ Rate limit hit on Key {actual_key_index + 1}")
                mark_key_rate_limited(actual_key_index)
                
                # Try next available key instead of waiting
                if attempt < MAX_RETRIES - 1:
                    api_key, actual_key_index = get_next_available_key()
                    if api_key:
                        headers["Authorization"] = f"Bearer {api_key}"
                        time.sleep(2)  # Small delay before retry
                        continue
                
                return {'error': 'Rate limit exceeded on all keys', 'retry': True}
            
            else:
                error_msg = f"API error {response.status_code}: {response.text[:200]}"
                logger.error(f"❌ {error_msg}")
                
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                    
                return {'error': error_msg}
                
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ Request timeout (attempt {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
                continue
            return {'error': 'Request timeout', 'retry': True}
            
        except Exception as e:
            logger.error(f"❌ API call error: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
                continue
            return {'error': str(e)}
    
    return {'error': 'Max retries exceeded'}

def warmup_groq_service():
    """Warm up the Groq service with a test request"""
    global warmup_complete
    
    try:
        logger.info("🔥 Warming up Groq service...")
        test_prompt = "Say 'ready' if you can process resume analysis requests."
        
        response = call_groq_api(
            prompt=test_prompt,
            max_tokens=50,
            temperature=0.1,
            timeout=30
        )
        
        if response and not isinstance(response, dict):
            warmup_complete = True
            logger.info("✅ Groq service warmed up successfully")
        else:
            logger.warning("⚠️ Warmup completed with warning")
            warmup_complete = True
            
    except Exception as e:
        logger.error(f"❌ Warmup error: {str(e)}")
        warmup_complete = True

def keep_service_warm():
    """Keep service warm with periodic pings"""
    while service_running:
        try:
            time.sleep(300)  # Every 5 minutes
            
            inactive_time = (datetime.now() - last_activity_time).total_seconds()
            if inactive_time < 600 and warmup_complete:
                test_prompt = "Quick check: Are you ready?"
                call_groq_api(test_prompt, max_tokens=10, timeout=20)
                logger.info("🔥 Keep-warm ping sent")
                
        except Exception as e:
            logger.error(f"❌ Keep-warm error: {str(e)}")

def analyze_resume_with_ai(resume_text, job_description, company_name, resume_filename, key_index=None):
    """Analyze resume using Groq AI with concise output"""
    
    # Check cache first
    resume_hash = calculate_resume_hash(resume_text, job_description)
    cached_score = get_cached_score(resume_hash)
    
    prompt = f"""You are an expert ATS (Applicant Tracking System) and resume analyzer. Analyze this resume against the job description and provide a detailed, actionable assessment.

**IMPORTANT OUTPUT REQUIREMENTS:**
1. Overall Summary: 3-5 sentences maximum
2. Experience Summary: 3-5 sentences maximum
3. Education Summary: 2-3 sentences maximum
4. Technical Skills: List {MIN_SKILLS_TO_SHOW}-{MAX_SKILLS_TO_SHOW} most relevant skills only
5. Soft Skills: List {MIN_SKILLS_TO_SHOW}-{MAX_SKILLS_TO_SHOW} most relevant skills only
6. Key Strengths: Exactly 4 bullet points
7. Areas for Improvement: Exactly 4 bullet points
8. ATS Match Score: Single percentage (0-100)

**Job Details:**
Company: {company_name}
Position: {job_description[:500]}

**Resume Content:**
{resume_text[:3000]}

**Output Format (JSON ONLY, NO MARKDOWN):**
{{
  "overall_summary": "3-5 sentence summary here",
  "experience_summary": "3-5 sentence summary here",
  "education_summary": "2-3 sentence summary here",
  "technical_skills": ["skill1", "skill2", "skill3", "skill4", "skill5"],
  "soft_skills": ["skill1", "skill2", "skill3", "skill4", "skill5"],
  "key_strengths": ["strength1", "strength2", "strength3", "strength4"],
  "areas_for_improvement": ["improvement1", "improvement2", "improvement3", "improvement4"],
  "ats_score": 85,
  "match_highlights": ["highlight1", "highlight2", "highlight3"]
}}

Provide ONLY the JSON output, no explanations or markdown formatting."""

    try:
        response = call_groq_api(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3,
            key_index=key_index,
            timeout=REQUEST_TIMEOUT
        )
        
        # Check for error response
        if isinstance(response, dict) and 'error' in response:
            return response
        
        # Parse JSON response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            analysis = json.loads(json_match.group())
            
            # Use cached score if available for consistency
            if cached_score is not None:
                analysis['ats_score'] = cached_score
            else:
                score = analysis.get('ats_score', 0)
                # Ensure score is in valid range
                if isinstance(score, (int, float)):
                    score = max(0, min(100, int(score)))
                    analysis['ats_score'] = score
                    set_cached_score(resume_hash, score)
                else:
                    analysis['ats_score'] = 0
            
            # Ensure all required fields exist with limits
            analysis.setdefault('overall_summary', 'Analysis not available')
            analysis.setdefault('experience_summary', 'Not specified')
            analysis.setdefault('education_summary', 'Not specified')
            
            # Limit skills
            analysis['technical_skills'] = analysis.get('technical_skills', [])[:MAX_SKILLS_TO_SHOW]
            analysis['soft_skills'] = analysis.get('soft_skills', [])[:MAX_SKILLS_TO_SHOW]
            
            # Ensure exactly 4 items
            analysis['key_strengths'] = (analysis.get('key_strengths', []) + ['Not specified'] * 4)[:4]
            analysis['areas_for_improvement'] = (analysis.get('areas_for_improvement', []) + ['Not specified'] * 4)[:4]
            
            analysis.setdefault('match_highlights', [])
            
            return analysis
        
        return {'error': 'Failed to parse AI response'}
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parse error: {str(e)}")
        return {'error': f'Invalid JSON response: {str(e)}'}
    except Exception as e:
        logger.error(f"❌ Analysis error: {str(e)}")
        return {'error': str(e)}

def process_single_resume_background(args):
    """Process a single resume (for background worker)"""
    try:
        resume_file = args['resume_file']
        filename = args['filename']
        job_description = args['job_description']
        company_name = args['company_name']
        resume_index = args['resume_index']
        job_id = args['job_id']
        
        logger.info(f"📄 Processing resume {resume_index + 1}: {filename}")
        
        # Extract text
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext == '.pdf':
            resume_text = extract_text_from_pdf(io.BytesIO(resume_file))
        elif file_ext == '.docx':
            resume_text = extract_text_from_docx(io.BytesIO(resume_file))
        else:
            return {
                'filename': filename,
                'error': f'Unsupported file format: {file_ext}',
                'status': 'error'
            }
        
        if not resume_text:
            return {
                'filename': filename,
                'error': 'Could not extract text from resume',
                'status': 'error'
            }
        
        # Store resume for preview
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        analysis_id = f"{timestamp}_resume_{resume_index}_{re.sub(r'[^a-zA-Z0-9]', '_', os.path.splitext(filename)[0])}"
        
        store_resume_file(resume_file, filename, analysis_id)
        
        # Analyze with AI
        logger.info(f"⚡ Analyzing resume {resume_index + 1} with AI...")
        
        # Get next available key (will wait if needed)
        max_wait = 120  # Max 2 minutes wait for a key
        wait_start = time.time()
        
        while time.time() - wait_start < max_wait:
            key, key_index = get_next_available_key()
            if key:
                break
            time.sleep(5)  # Check every 5 seconds
        else:
            return {
                'filename': filename,
                'error': 'All API keys busy, please try again',
                'status': 'error'
            }
        
        analysis = analyze_resume_with_ai(
            resume_text,
            job_description,
            company_name,
            filename,
            key_index=key_index
        )
        
        # Check for errors
        if isinstance(analysis, dict) and 'error' in analysis:
            return {
                'filename': filename,
                'error': analysis['error'],
                'status': 'error',
                'retry': analysis.get('retry', False)
            }
        
        # Success
        result = {
            'filename': filename,
            'analysis': analysis,
            'analysis_id': analysis_id,
            'status': 'success'
        }
        
        logger.info(f"✅ Resume {resume_index + 1} analyzed successfully (Score: {analysis.get('ats_score', 0)}%)")
        
        # Update job status
        with job_lock:
            if job_id in background_jobs:
                background_jobs[job_id]['completed'] += 1
                background_jobs[job_id]['results'].append(result)
        
        return result
        
    except Exception as e:
        error_msg = f"Error processing {args.get('filename', 'unknown')}: {str(e)}"
        logger.error(f"❌ {error_msg}")
        traceback.print_exc()
        
        with job_lock:
            if args.get('job_id') in background_jobs:
                background_jobs[args['job_id']]['completed'] += 1
        
        return {
            'filename': args.get('filename', 'unknown'),
            'error': error_msg,
            'status': 'error'
        }

@app.route('/analyze-batch', methods=['POST'])
def analyze_resume_batch():
    """
    Analyze multiple resumes in batch (ASYNC)
    Returns job ID immediately, processing happens in background
    """
    try:
        update_activity()
        
        # Get files and parameters
        files = request.files.getlist('resumes')
        job_description = request.form.get('jobDescription', '')
        company_name = request.form.get('companyName', 'Company')
        
        if not files:
            return jsonify({'error': 'No resume files provided'}), 400
        
        if len(files) > MAX_BATCH_SIZE:
            return jsonify({'error': f'Maximum {MAX_BATCH_SIZE} resumes allowed per batch'}), 400
        
        # Create job ID
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        logger.info("="*50)
        logger.info(f"📦 New batch analysis request")
        logger.info(f"📦 Job ID: {job_id}")
        logger.info(f"📦 Batch size: {len(files)} resumes")
        logger.info(f"🔄 Processing with {len([k for k in GROQ_API_KEYS if k])} API keys...")
        logger.info("="*50)
        
        # Prepare arguments for processing
        process_args = []
        for i, file in enumerate(files):
            filename = file.filename
            file_data = file.read()
            file.seek(0)  # Reset for potential reuse
            
            process_args.append({
                'resume_file': file_data,
                'filename': filename,
                'job_description': job_description,
                'company_name': company_name,
                'resume_index': i,
                'job_id': job_id
            })
        
        # Initialize job tracking
        with job_lock:
            background_jobs[job_id] = {
                'status': 'processing',
                'total': len(files),
                'completed': 0,
                'results': [],
                'created_at': datetime.now()
            }
        
        # Start background processing
        def process_batch():
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
                    futures = [executor.submit(process_single_resume_background, args) for args in process_args]
                    concurrent.futures.wait(futures)
                
                # Mark job as complete
                with job_lock:
                    if job_id in background_jobs:
                        background_jobs[job_id]['status'] = 'completed'
                        logger.info(f"✅ Job {job_id} completed")
                        
            except Exception as e:
                logger.error(f"❌ Batch processing error: {str(e)}")
                with job_lock:
                    if job_id in background_jobs:
                        background_jobs[job_id]['status'] = 'error'
                        background_jobs[job_id]['error'] = str(e)
        
        # Start in background thread
        threading.Thread(target=process_batch, daemon=True).start()
        
        # Return job ID immediately
        return jsonify({
            'job_id': job_id,
            'status': 'processing',
            'total_resumes': len(files),
            'message': 'Batch processing started. Use /job-status endpoint to check progress.'
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Batch analysis error: {error_msg}")
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500

@app.route('/job-status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get status of a background job"""
    with job_lock:
        if job_id not in background_jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = background_jobs[job_id]
        
        response = {
            'job_id': job_id,
            'status': job['status'],
            'total': job['total'],
            'completed': job['completed'],
            'progress': round((job['completed'] / job['total']) * 100, 1) if job['total'] > 0 else 0
        }
        
        # Include results if completed
        if job['status'] == 'completed':
            response['results'] = job['results']
        
        if 'error' in job:
            response['error'] = job['error']
        
        return jsonify(response)

@app.route('/generate-report', methods=['POST'])
def generate_report():
    """Generate Excel report from analysis results"""
    try:
        data = request.json
        results = data.get('results', [])
        company_name = data.get('companyName', 'Company')
        job_description = data.get('jobDescription', 'Position')
        
        if not results:
            return jsonify({'error': 'No results provided'}), 400
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Resume Analysis"
        
        # Define styles
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        subheader_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        subheader_font = Font(bold=True, size=11)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Add title
        ws.merge_cells('A1:H1')
        title_cell = ws['A1']
        title_cell.value = f"Resume Analysis Report - {company_name}"
        title_cell.font = Font(bold=True, size=14)
        title_cell.fill = header_fill
        title_cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Add metadata
        ws['A2'] = f"Position: {job_description[:100]}"
        ws['A3'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws['A4'] = f"Total Resumes Analyzed: {len(results)}"
        
        current_row = 6
        
        # Process each resume
        for idx, result in enumerate(results, 1):
            if result.get('status') == 'error':
                # Show error
                ws.merge_cells(f'A{current_row}:H{current_row}')
                error_cell = ws[f'A{current_row}']
                error_cell.value = f"❌ {result['filename']}: {result.get('error', 'Unknown error')}"
                error_cell.fill = PatternFill(start_color="FFE699", end_color="FFE699", fill_type="solid")
                error_cell.font = Font(bold=True)
                current_row += 2
                continue
            
            analysis = result.get('analysis', {})
            
            # Resume header
            ws.merge_cells(f'A{current_row}:H{current_row}')
            header_cell = ws[f'A{current_row}']
            header_cell.value = f"Resume #{idx}: {result['filename']}"
            header_cell.font = header_font
            header_cell.fill = header_fill
            header_cell.alignment = Alignment(horizontal='center')
            current_row += 1
            
            # ATS Score
            ws[f'A{current_row}'] = "ATS Match Score:"
            ws[f'B{current_row}'] = f"{analysis.get('ats_score', 0)}%"
            ws[f'B{current_row}'].font = Font(bold=True, size=14)
            current_row += 1
            
            # Overall Summary
            ws[f'A{current_row}'] = "Overall Summary:"
            ws[f'A{current_row}'].font = subheader_font
            current_row += 1
            ws.merge_cells(f'A{current_row}:H{current_row}')
            ws[f'A{current_row}'] = analysis.get('overall_summary', 'N/A')
            ws[f'A{current_row}'].alignment = Alignment(wrap_text=True)
            current_row += 1
            
            # Experience Summary
            ws[f'A{current_row}'] = "Experience Summary:"
            ws[f'A{current_row}'].font = subheader_font
            current_row += 1
            ws.merge_cells(f'A{current_row}:H{current_row}')
            ws[f'A{current_row}'] = analysis.get('experience_summary', 'N/A')
            ws[f'A{current_row}'].alignment = Alignment(wrap_text=True)
            current_row += 1
            
            # Education Summary
            ws[f'A{current_row}'] = "Education Summary:"
            ws[f'A{current_row}'].font = subheader_font
            current_row += 1
            ws.merge_cells(f'A{current_row}:H{current_row}')
            ws[f'A{current_row}'] = analysis.get('education_summary', 'N/A')
            ws[f'A{current_row}'].alignment = Alignment(wrap_text=True)
            current_row += 1
            
            # Technical Skills
            ws[f'A{current_row}'] = "Technical Skills:"
            ws[f'A{current_row}'].font = subheader_font
            current_row += 1
            for skill in analysis.get('technical_skills', []):
                ws[f'A{current_row}'] = f"• {skill}"
                current_row += 1
            
            # Soft Skills
            ws[f'A{current_row}'] = "Soft Skills:"
            ws[f'A{current_row}'].font = subheader_font
            current_row += 1
            for skill in analysis.get('soft_skills', []):
                ws[f'A{current_row}'] = f"• {skill}"
                current_row += 1
            
            # Key Strengths
            ws[f'A{current_row}'] = "Key Strengths:"
            ws[f'A{current_row}'].font = subheader_font
            current_row += 1
            for strength in analysis.get('key_strengths', []):
                ws.merge_cells(f'A{current_row}:H{current_row}')
                ws[f'A{current_row}'] = f"✓ {strength}"
                ws[f'A{current_row}'].alignment = Alignment(wrap_text=True)
                current_row += 1
            
            # Areas for Improvement
            ws[f'A{current_row}'] = "Areas for Improvement:"
            ws[f'A{current_row}'].font = subheader_font
            current_row += 1
            for improvement in analysis.get('areas_for_improvement', []):
                ws.merge_cells(f'A{current_row}:H{current_row}')
                ws[f'A{current_row}'] = f"→ {improvement}"
                ws[f'A{current_row}'].alignment = Alignment(wrap_text=True)
                current_row += 1
            
            current_row += 2  # Space between resumes
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 80
        for col in ['B', 'C', 'D', 'E', 'F', 'G', 'H']:
            ws.column_dimensions[col].width = 15
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"resume_analysis_report_{timestamp}.xlsx"
        report_path = os.path.join(REPORTS_FOLDER, report_filename)
        
        wb.save(report_path)
        
        logger.info(f"✅ Report generated: {report_filename}")
        
        return jsonify({
            'success': True,
            'report_filename': report_filename,
            'report_path': f'/download-report/{report_filename}'
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Report generation error: {error_msg}")
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500

@app.route('/download-report/<filename>', methods=['GET'])
def download_report(filename):
    """Download generated report"""
    try:
        return send_from_directory(
            REPORTS_FOLDER,
            filename,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/preview-resume/<analysis_id>', methods=['GET'])
def preview_resume(analysis_id):
    """Serve resume preview (PDF preferred)"""
    try:
        if analysis_id not in resume_storage:
            return jsonify({'error': 'Resume not found or expired'}), 404
        
        info = resume_storage[analysis_id]
        
        # Try PDF preview first
        if info['has_pdf_preview'] and os.path.exists(info['pdf_preview_path']):
            return send_file(
                info['pdf_preview_path'],
                mimetype='application/pdf',
                as_attachment=False
            )
        
        # Fallback to original file
        if os.path.exists(info['original_path']):
            mimetype = 'application/pdf' if info['file_ext'] == '.pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            return send_file(
                info['original_path'],
                mimetype=mimetype,
                as_attachment=False
            )
        
        return jsonify({'error': 'Resume file not found'}), 404
        
    except Exception as e:
        logger.error(f"❌ Preview error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/check-api', methods=['GET'])
def check_api():
    """Check if Groq API is available"""
    try:
        update_activity()
        
        available_keys = sum(1 for key in GROQ_API_KEYS if key)
        
        if available_keys == 0:
            return jsonify({
                'available': False,
                'reason': 'No API keys configured',
                'available_keys': 0
            })
        
        # Quick test with first available key
        start_time = time.time()
        
        for i, key in enumerate(GROQ_API_KEYS):
            if key and not key_usage[i]['cooling']:
                try:
                    response = call_groq_api(
                        prompt="Say 'ready' in one word.",
                        max_tokens=10,
                        temperature=0.1,
                        key_index=i,
                        timeout=15
                    )
                    
                    response_time = time.time() - start_time
                    
                    if response and not isinstance(response, dict):
                        return jsonify({
                            'available': True,
                            'response_time': f"{response_time:.2f}s",
                            'ai_provider': 'groq',
                            'model': GROQ_MODEL,
                            'warmup_complete': warmup_complete,
                            'available_keys': available_keys,
                            'tested_key': f"Key {i+1}",
                            'max_batch_size': MAX_BATCH_SIZE,
                            'processing_method': 'concurrent_async'
                        })
                except:
                    continue
        
        return jsonify({
            'available': False,
            'reason': 'All keys are cooling or unavailable',
            'available_keys': available_keys,
            'warmup_complete': warmup_complete
        })
            
    except Exception as e:
        return jsonify({
            'available': False,
            'reason': str(e)[:100],
            'ai_provider': 'groq',
            'model': GROQ_MODEL
        })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    update_activity()
    
    available_keys = sum(1 for key in GROQ_API_KEYS if key)
    
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'resume-analyzer-groq',
        'ai_provider': 'groq',
        'ai_warmup': warmup_complete,
        'model': GROQ_MODEL,
        'available_keys': available_keys,
        'inactive_minutes': int((datetime.now() - last_activity_time).total_seconds() / 60),
        'processing_method': 'concurrent_async'
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with key status"""
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    key_status = []
    for i, api_key in enumerate(GROQ_API_KEYS):
        last_used_ago = None
        if key_usage[i]['last_request_time']:
            last_used_ago = int((datetime.now() - key_usage[i]['last_request_time']).total_seconds())
        
        key_status.append({
            'key': f'Key {i+1}',
            'configured': bool(api_key),
            'usage': key_usage[i]['count'],
            'cooling': key_usage[i]['cooling'],
            'last_used_seconds_ago': last_used_ago
        })
    
    available_keys = sum(1 for key in GROQ_API_KEYS if key)
    
    # Clean up old jobs
    with job_lock:
        cutoff_time = datetime.now() - timedelta(hours=1)
        jobs_to_remove = [
            job_id for job_id, job in background_jobs.items()
            if job['created_at'] < cutoff_time
        ]
        for job_id in jobs_to_remove:
            del background_jobs[job_id]
    
    return jsonify({
        'status': 'Service is running',
        'timestamp': datetime.now().isoformat(),
        'ai_provider': 'groq',
        'model': GROQ_MODEL,
        'ai_warmup_complete': warmup_complete,
        'available_keys': available_keys,
        'key_status': key_status,
        'active_jobs': len(background_jobs),
        'version': '3.0.0-async',
        'processing_method': 'concurrent_async'
    })

def cleanup_on_exit():
    """Cleanup function called on exit"""
    global service_running
    service_running = False
    print("\n🛑 Shutting down service...")
    
    try:
        for folder in [UPLOAD_FOLDER, RESUME_PREVIEW_FOLDER]:
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
        print("✅ Cleaned up temporary files")
    except:
        pass

def periodic_cleanup():
    """Periodically clean up old resume previews"""
    while service_running:
        try:
            time.sleep(300)  # Every 5 minutes
            cleanup_resume_previews()
        except Exception as e:
            logger.error(f"⚠️ Periodic cleanup error: {str(e)}")

atexit.register(cleanup_on_exit)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting (Async Mode)...")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"⚡ AI Provider: Groq (Async Processing)")
    print(f"🤖 Model: {GROQ_MODEL}")
    
    available_keys = sum(1 for key in GROQ_API_KEYS if key)
    print(f"🔑 API Keys: {available_keys}/3 configured")
    
    for i, key in enumerate(GROQ_API_KEYS):
        status = "✅ Configured" if key else "❌ Not configured"
        print(f"  Key {i+1}: {status}")
    
    print(f"✅ Concurrent Processing: {MAX_CONCURRENT_REQUESTS} workers")
    print(f"✅ Max Batch Size: {MAX_BATCH_SIZE} resumes")
    print(f"✅ Async Mode: Immediate response + background processing")
    print("="*50 + "\n")
    
    if available_keys == 0:
        print("⚠️  WARNING: No Groq API keys found!")
        print("Please set GROQ_API_KEY_1, GROQ_API_KEY_2, GROQ_API_KEY_3")
    
    gc.enable()
    
    if available_keys > 0:
        warmup_thread = threading.Thread(target=warmup_groq_service, daemon=True)
        warmup_thread.start()
        
        keep_warm_thread = threading.Thread(target=keep_service_warm, daemon=True)
        keep_warm_thread.start()
        
        cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
        cleanup_thread.start()
        
        print("✅ Background threads started")
    
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode, threaded=True)
