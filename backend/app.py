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

# Configure multiple Groq API keys
GROQ_API_KEYS = [
    os.getenv('GROQ_API_KEY_1'),
    os.getenv('GROQ_API_KEY_2'),
    os.getenv('GROQ_API_KEY_3'),
]

# Filter out None values and create key pool
ACTIVE_API_KEYS = [key for key in GROQ_API_KEYS if key]

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')

# Track API key usage and limits
KEY_USAGE = {key: {'count': 0, 'last_used': None, 'available': True, 'errors': 0, 'requests_today': 0, 'concurrent': 0} for key in ACTIVE_API_KEYS}
KEY_LIMIT = 5  # Increased to 5 resumes per key for better distribution
KEY_COOLDOWN = 60  # Seconds to cooldown if key has errors

# Available Groq models
GROQ_MODELS = {
    'llama-3.1-8b-instant': {
        'name': 'Llama 3.1 8B Instant',
        'context_length': 8192,
        'provider': 'Groq',
        'description': 'Fast 8B model for quick responses',
        'status': 'production',
        'free_tier': True,
        'max_batch_size': 5
    }
}

# Default working model
DEFAULT_MODEL = 'llama-3.1-8b-instant'

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
MAX_CONCURRENT_PER_KEY = 2  # Max concurrent requests per key
MAX_BATCH_SIZE = 15  # Maximum number of resumes per batch (5 per key * 3 keys)
MAX_INDIVIDUAL_REPORTS = 10  # Limit individual Excel reports

# Rate limiting protection
MAX_RETRIES = 5  # Increased retries
RETRY_DELAY_BASE = 2

# Memory optimization
service_running = True

def update_activity():
    """Update last activity timestamp"""
    global last_activity_time
    last_activity_time = datetime.now()

def get_key_for_index(index):
    """Get API key for a specific resume index using round-robin distribution"""
    with threading.Lock():
        if not ACTIVE_API_KEYS:
            return None
        
        # Round-robin distribution
        key_index = index % len(ACTIVE_API_KEYS)
        selected_key = ACTIVE_API_KEYS[key_index]
        
        # Check if key is available
        key_info = KEY_USAGE[selected_key]
        
        # Reset if key is at limit and it's been a while
        current_time = datetime.now()
        if key_info['count'] >= KEY_LIMIT and key_info['last_used']:
            time_diff = (current_time - key_info['last_used']).seconds
            if time_diff > 30:  # Reset if 30 seconds passed
                key_info['count'] = 0
                key_info['available'] = True
        
        # Skip if key has too many errors
        if key_info['errors'] >= 3:
            # Try next key
            key_index = (index + 1) % len(ACTIVE_API_KEYS)
            selected_key = ACTIVE_API_KEYS[key_index]
        
        # Update usage
        key_info['count'] += 1
        key_info['last_used'] = current_time
        key_info['requests_today'] += 1
        key_info['concurrent'] += 1
        
        # Check if key should be marked as unavailable
        if key_info['count'] >= KEY_LIMIT:
            key_info['available'] = False
        
        print(f"🔑 Assigning API key {key_index + 1} to resume {index + 1} (Usage: {key_info['count']}/{KEY_LIMIT}, Errors: {key_info['errors']})")
        return selected_key

def mark_key_complete(key):
    """Mark key as having completed a request"""
    with threading.Lock():
        if key in KEY_USAGE:
            KEY_USAGE[key]['concurrent'] = max(0, KEY_USAGE[key]['concurrent'] - 1)

def mark_key_as_error(key):
    """Mark a key as having an error"""
    with threading.Lock():
        if key in KEY_USAGE:
            KEY_USAGE[key]['errors'] += 1
            KEY_USAGE[key]['last_error'] = datetime.now()
            
            # Put key in cooldown if too many errors
            if KEY_USAGE[key]['errors'] >= 2:
                cooldown_time = KEY_COOLDOWN * KEY_USAGE[key]['errors']
                KEY_USAGE[key]['cooldown_until'] = datetime.now() + timedelta(seconds=cooldown_time)
                print(f"⚠️ Key {ACTIVE_API_KEYS.index(key) + 1} in cooldown for {cooldown_time}s")

def reset_key_usage():
    """Reset key usage counters periodically"""
    with threading.Lock():
        for key in ACTIVE_API_KEYS:
            KEY_USAGE[key]['count'] = 0
            KEY_USAGE[key]['available'] = True
            KEY_USAGE[key]['concurrent'] = 0
            # Reduce error counts gradually
            if KEY_USAGE[key]['errors'] > 0:
                KEY_USAGE[key]['errors'] = max(0, KEY_USAGE[key]['errors'] - 1)
        print("🔄 Reset all API key usage counters")

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

def call_groq_api(prompt, max_tokens=800, temperature=0.2, timeout=30, model_override=None, retry_count=0, api_key=None):
    """Call Groq API with the given prompt with optimized retry logic"""
    if not api_key:
        print("❌ No API key provided")
        return {'error': 'no_api_key', 'status': 500}
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    model_to_use = model_override or GROQ_MODEL or DEFAULT_MODEL
    
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
        'top_p': 0.95,
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
                print(f"✅ Groq API response in {response_time:.2f}s using {model_to_use}")
                return result
            else:
                print(f"❌ Unexpected Groq API response format")
                return {'error': 'invalid_response', 'status': response.status_code}
        elif response.status_code == 429:
            print(f"❌ Groq API rate limit exceeded for key")
            mark_key_as_error(api_key)
            
            if retry_count < MAX_RETRIES:
                wait_time = RETRY_DELAY_BASE ** (retry_count + 1) + random.uniform(0, 2)
                print(f"⏳ Rate limited, retrying in {wait_time:.1f}s (attempt {retry_count + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                return call_groq_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1, api_key)
            return {'error': 'rate_limit', 'status': 429}
        elif response.status_code == 503:
            print(f"❌ Groq API service unavailable")
            mark_key_as_error(api_key)
            
            if retry_count < 3:
                wait_time = 10 + random.uniform(0, 5)
                print(f"⏳ Service unavailable, retrying in {wait_time:.1f}s")
                time.sleep(wait_time)
                return call_groq_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1, api_key)
            return {'error': 'service_unavailable', 'status': 503}
        else:
            print(f"❌ Groq API Error {response.status_code}: {response.text[:200]}")
            mark_key_as_error(api_key)
            return {'error': f'api_error_{response.status_code}', 'status': response.status_code}
            
    except requests.exceptions.Timeout:
        print(f"❌ Groq API timeout after {timeout}s")
        mark_key_as_error(api_key)
        
        if retry_count < 2:
            wait_time = 5 + random.uniform(0, 3)
            print(f"⏳ Timeout, retrying in {wait_time:.1f}s (attempt {retry_count + 1}/3)")
            time.sleep(wait_time)
            return call_groq_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1, api_key)
        return {'error': 'timeout', 'status': 408}
    except Exception as e:
        print(f"❌ Groq API Exception: {str(e)}")
        mark_key_as_error(api_key)
        return {'error': str(e), 'status': 500}

def warmup_groq_service():
    """Warm up Groq service connection for all keys"""
    global warmup_complete
    
    if not ACTIVE_API_KEYS:
        print("⚠️ Skipping Groq warm-up: No API keys configured")
        return False
    
    try:
        model_to_use = GROQ_MODEL or DEFAULT_MODEL
        print(f"🔥 Warming up Groq connections...")
        print(f"📊 Using model: {model_to_use}")
        print(f"🔑 Active API keys: {len(ACTIVE_API_KEYS)}")
        
        successful_warmups = 0
        
        for idx, api_key in enumerate(ACTIVE_API_KEYS, 1):
            print(f"  Warming up key {idx}...")
            start_time = time.time()
            
            response = call_groq_api(
                prompt="Hello, are you ready? Respond with just 'ready'.",
                max_tokens=10,
                temperature=0.1,
                timeout=10,
                api_key=api_key
            )
            
            if isinstance(response, dict) and 'error' in response:
                error_type = response.get('error')
                print(f"  ⚠️ Key {idx} warm-up failed: {error_type}")
            elif response and 'ready' in response.lower():
                elapsed = time.time() - start_time
                print(f"  ✅ Key {idx} warmed up in {elapsed:.2f}s")
                successful_warmups += 1
            else:
                print(f"  ⚠️ Key {idx} warm-up failed: Unexpected response")
        
        if successful_warmups > 0:
            print(f"✅ {successful_warmups}/{len(ACTIVE_API_KEYS)} API keys warmed up successfully")
            warmup_complete = True
            return True
        else:
            print("⚠️ All warm-up attempts failed")
            threading.Timer(10.0, warmup_groq_service).start()
            return False
        
    except Exception as e:
        print(f"⚠️ Warm-up attempt failed: {str(e)}")
        threading.Timer(10.0, warmup_groq_service).start()
        return False

def keep_service_warm():
    """Periodically send requests to keep Groq service responsive"""
    global service_running
    
    while service_running:
        try:
            time.sleep(120)  # Check every 120 seconds
            
            if ACTIVE_API_KEYS and warmup_complete:
                print(f"♨️ Keeping Groq warm with {len(ACTIVE_API_KEYS)} keys...")
                
                for idx, api_key in enumerate(ACTIVE_API_KEYS, 1):
                    try:
                        response = call_groq_api(
                            prompt="Ping - just say 'pong'",
                            max_tokens=5,
                            timeout=15,
                            api_key=api_key
                        )
                        if response and 'pong' in str(response).lower():
                            print(f"  ✅ Key {idx} keep-alive successful")
                        else:
                            print(f"  ⚠️ Key {idx} keep-alive got unexpected response")
                    except Exception as e:
                        print(f"  ⚠️ Key {idx} keep-alive failed: {str(e)}")
                    
        except Exception as e:
            print(f"⚠️ Keep-warm thread error: {str(e)}")
            time.sleep(120)

# Text extraction functions (keep the same as before)
def extract_text_from_pdf(file_path):
    """Extract text from PDF file with error handling"""
    try:
        text = ""
        max_attempts = 2
        
        for attempt in range(max_attempts):
            try:
                reader = PdfReader(file_path)
                text = ""
                
                for page_num, page in enumerate(reader.pages[:5]):
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
                                text = ' '.join(words[:800])
                    except:
                        text = "Error: Could not extract text from PDF file"
        
        if not text.strip():
            return "Error: PDF appears to be empty or text could not be extracted"
        
        if len(text) > 3000:
            text = text[:3000] + "\n[Text truncated for optimal processing...]"
            
        return text
    except Exception as e:
        print(f"❌ PDF Error: {traceback.format_exc()}")
        return f"Error reading PDF: {str(e)[:100]}"

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs[:50] if paragraph.text.strip()])
        
        if not text.strip():
            return "Error: Document appears to be empty"
        
        if len(text) > 3000:
            text = text[:3000] + "\n[Text truncated for optimal processing...]"
            
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
                
                if len(text) > 3000:
                    text = text[:3000] + "\n[Text truncated for optimal processing...]"
                    
                return text
            except UnicodeDecodeError:
                continue
                
        return "Error: Could not decode text file with common encodings"
        
    except Exception as e:
        print(f"❌ TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

def analyze_resume_with_ai(resume_text, job_description, filename=None, analysis_id=None, api_key=None, key_index=None):
    """Use Groq API to analyze resume against job description"""
    
    if not api_key:
        print("❌ No API key provided for analysis.")
        return fallback_response("API Configuration Error", filename)
    
    if not warmup_complete:
        print(f"⚠️ Groq API not warmed up yet, analysis may be slower")
    
    # Check cache for consistent scoring
    resume_hash = calculate_resume_hash(resume_text, job_description)
    cached_score = get_cached_score(resume_hash)
    
    # Optimize text length
    resume_text = resume_text[:2500]
    job_description = job_description[:1000]
    
    # Optimized prompt for faster processing
    prompt = f"""Analyze this resume against the job description:

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Provide analysis in this JSON format:
{{
    "candidate_name": "Extract name from resume or use filename",
    "skills_matched": ["skill 1", "skill 2", "skill 3"],
    "skills_missing": ["skill 1", "skill 2"],
    "experience_summary": "Brief summary of relevant experience",
    "education_summary": "Brief education summary",
    "overall_score": 75,
    "recommendation": "Recommended/Consider/Needs Improvement",
    "key_strengths": ["strength 1", "strength 2"],
    "areas_for_improvement": ["area 1", "area 2"]
}}

Keep responses concise and return ONLY the JSON."""

    try:
        model_to_use = GROQ_MODEL or DEFAULT_MODEL
        print(f"⚡ Sending to Groq API (Key {key_index}, {model_to_use})...")
        start_time = time.time()
        
        response = call_groq_api(
            prompt=prompt,
            max_tokens=500,
            temperature=0.1,
            timeout=45,
            api_key=api_key
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            print(f"❌ Groq API error: {error_type}")
            return fallback_response(f"Groq API Error: {error_type}", filename)
        
        elapsed_time = time.time() - start_time
        print(f"✅ Groq API response in {elapsed_time:.2f} seconds (Key {key_index})")
        
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
            print(f"Response was: {result_text[:200]}")
            
            return fallback_response("JSON Parse Error", filename)
        
        # Ensure required fields exist with defaults
        required_fields = {
            'candidate_name': 'Professional Candidate',
            'skills_matched': ['Analysis completed'],
            'skills_missing': ['Check requirements'],
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
        
        # Limit array lengths
        analysis['skills_matched'] = analysis['skills_matched'][:4]
        analysis['skills_missing'] = analysis['skills_missing'][:4]
        analysis['key_strengths'] = analysis['key_strengths'][:2]
        analysis['areas_for_improvement'] = analysis['areas_for_improvement'][:2]
        
        # Add AI provider info
        analysis['ai_provider'] = "groq"
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['ai_model'] = model_to_use
        analysis['response_time'] = f"{elapsed_time:.2f}s"
        analysis['api_key_used'] = f"key_{key_index}" if key_index else "unknown"
        
        # Add analysis ID if provided
        if analysis_id:
            analysis['analysis_id'] = analysis_id
        
        print(f"✅ Analysis completed for: {analysis['candidate_name']} (Score: {analysis['overall_score']}, Key: {key_index})")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Groq Analysis Error: {str(e)}")
        traceback.print_exc()
        return fallback_response(f"Groq API Error: {str(e)[:100]}", filename)

def fallback_response(reason, filename=None):
    """Return a fallback response when Groq API fails"""
    candidate_name = "Professional Candidate"
    if filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').title()
        if len(clean_name.split()) <= 4:
            candidate_name = clean_name
    
    return {
        "candidate_name": candidate_name,
        "skills_matched": ["AI service is initializing", "Please try again in a moment"],
        "skills_missing": ["Detailed analysis coming soon", "Service warming up"],
        "experience_summary": f"The Groq AI analysis service is currently warming up.",
        "education_summary": f"Educational background analysis will be available once the service is ready.",
        "overall_score": 50,
        "recommendation": "Service Warming Up - Please Retry",
        "key_strengths": ["Ultra-fast analysis once model is loaded", "Accurate skill matching"],
        "areas_for_improvement": ["Please wait for model to load", "Try again in 15 seconds"],
        "ai_provider": "groq",
        "ai_status": "Warming up",
        "ai_model": GROQ_MODEL or DEFAULT_MODEL
    }

def process_single_resume(args):
    """Process a single resume with thread-safe operations"""
    resume_file, job_description, index, total, batch_id = args
    
    try:
        print(f"📄 Processing resume {index + 1}/{total}: {resume_file.filename}")
        
        # Get API key for this resume index
        api_key = get_key_for_index(index)
        key_index = ACTIVE_API_KEYS.index(api_key) + 1 if api_key in ACTIVE_API_KEYS else 0
        
        if not api_key:
            return {
                'filename': resume_file.filename,
                'error': 'No available API key',
                'status': 'failed',
                'index': index
            }
        
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
        
        # Analyze with Groq API
        analysis_id = f"{batch_id}_resume_{index}"
        analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id, api_key, key_index)
        
        if 'error' in analysis:
            return {
                'filename': resume_file.filename,
                'error': analysis.get('error', 'Unknown error'),
                'status': 'failed',
                'index': index
            }
        
        analysis['filename'] = resume_file.filename
        analysis['original_filename'] = resume_file.filename
        
        # Get file size
        resume_file.seek(0, 2)
        file_size = resume_file.tell()
        resume_file.seek(0)
        analysis['file_size'] = f"{(file_size / 1024):.1f}KB"
        
        # Add analysis ID
        analysis['analysis_id'] = analysis_id
        analysis['key_index'] = key_index
        
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
        
        # Mark key as complete
        mark_key_complete(api_key)
        
        print(f"✅ Completed: {analysis.get('candidate_name')} - Score: {analysis.get('overall_score')} (Key: {key_index})")
        
        return {
            'analysis': analysis,
            'status': 'success',
            'index': index,
            'api_key_used': key_index
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
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    
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
            <p>AI-powered resume analysis using Multi-Key Groq API</p>
            
            <div class="status ''' + ('ready' if warmup_complete else 'warming') + '''">
                <strong>Status:</strong> ''' + warmup_status + '''
            </div>
            
            <p><strong>Model:</strong> ''' + model_to_use + '''</p>
            <p><strong>API Keys:</strong> ''' + str(len(ACTIVE_API_KEYS)) + ''' active</p>
            <p><strong>Max Batch Size:</strong> ''' + str(MAX_BATCH_SIZE) + ''' resumes</p>
            <p><strong>Key Distribution:</strong> Round-robin across ''' + str(len(ACTIVE_API_KEYS)) + ''' keys</p>
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
        if not ACTIVE_API_KEYS:
            print("❌ No Groq API keys configured")
            return jsonify({'error': 'Groq API not configured'}), 500
        
        # Analyze with Groq API
        model_to_use = GROQ_MODEL or DEFAULT_MODEL
        print(f"⚡ Starting Groq API analysis ({model_to_use})...")
        ai_start = time.time()
        
        # Get API key
        api_key = get_key_for_index(0)
        key_index = ACTIVE_API_KEYS.index(api_key) + 1 if api_key in ACTIVE_API_KEYS else 0
        
        analysis_id = f"single_{timestamp}"
        analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id, api_key, key_index)
        ai_time = time.time() - ai_start
        
        print(f"✅ Groq API analysis completed in {ai_time:.2f}s")
        
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
        
        # Mark key as complete
        mark_key_complete(api_key)
        
        # Return analysis
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['ai_model'] = model_to_use
        analysis['ai_provider'] = "groq"
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['response_time'] = f"{ai_time:.2f}s"
        analysis['analysis_id'] = analysis_id
        analysis['api_key_used'] = f"key_{key_index}"
        
        total_time = time.time() - start_time
        print(f"✅ Request completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/analyze-batch', methods=['POST'])
def analyze_resume_batch():
    """Analyze multiple resumes against a single job description"""
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
        if not ACTIVE_API_KEYS:
            print("❌ No Groq API keys configured")
            return jsonify({'error': 'Groq API not configured'}), 500
        
        # Prepare batch analysis
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        
        # Prepare arguments for parallel processing
        args_list = []
        for index, resume_file in enumerate(resume_files):
            if resume_file.filename == '':
                continue
            args_list.append((resume_file, job_description, index, len(resume_files), batch_id))
        
        # Process resumes in parallel with ThreadPoolExecutor
        all_analyses = []
        errors = []
        
        print(f"🔄 Processing {len(args_list)} resumes with {len(ACTIVE_API_KEYS)} API keys...")
        print(f"📊 Key distribution: Round-robin across {len(ACTIVE_API_KEYS)} keys")
        
        # Use ThreadPoolExecutor for parallel processing
        max_workers = min(len(args_list), len(ACTIVE_API_KEYS) * MAX_CONCURRENT_PER_KEY)
        max_workers = max(1, max_workers)  # At least 1 worker
        
        print(f"⚡ Using {max_workers} parallel workers")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_args = {executor.submit(process_single_resume, args): args for args in args_list}
            
            for future in concurrent.futures.as_completed(future_to_args):
                args = future_to_args[future]
                try:
                    result = future.result(timeout=120)  # 2 minute timeout per resume
                    
                    if result['status'] == 'success':
                        all_analyses.append(result['analysis'])
                        # Add delay between successful analyses to avoid rate limits
                        time.sleep(0.5)  # 500ms delay
                    else:
                        errors.append({
                            'filename': result.get('filename', 'Unknown'),
                            'error': result.get('error', 'Unknown error'),
                            'index': result.get('index')
                        })
                except concurrent.futures.TimeoutError:
                    errors.append({
                        'filename': args[0].filename if args else 'Unknown',
                        'error': 'Processing timeout (120 seconds)',
                        'index': args[2] if len(args) > 2 else None
                    })
                except Exception as e:
                    errors.append({
                        'filename': args[0].filename if args else 'Unknown',
                        'error': f'Processing error: {str(e)[:100]}',
                        'index': args[2] if len(args) > 2 else None
                    })
        
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
        
        # Calculate key distribution
        key_distribution = {}
        for analysis in all_analyses:
            key_used = analysis.get('api_key_used', 'unknown')
            if key_used not in key_distribution:
                key_distribution[key_used] = []
            key_distribution[key_used].append(analysis.get('candidate_name', 'Unknown'))
        
        # Prepare key distribution description
        key_distribution_desc = []
        for key_idx in range(1, len(ACTIVE_API_KEYS) + 1):
            key_name = f"key_{key_idx}"
            if key_name in key_distribution:
                count = len(key_distribution[key_name])
                key_distribution_desc.append(f"Key {key_idx}: {count} resume(s)")
        
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
            'model_used': GROQ_MODEL or DEFAULT_MODEL,
            'ai_provider': "groq",
            'ai_status': "Warmed up" if warmup_complete else "Warming up",
            'processing_time': f"{time.time() - start_time:.2f}s",
            'job_description_preview': job_description[:200] + ("..." if len(job_description) > 200 else ""),
            'batch_size': len(resume_files),
            'api_keys_used': len(ACTIVE_API_KEYS),
            'key_distribution': ", ".join(key_distribution_desc),
            'key_limit_per_key': KEY_LIMIT,
            'max_batch_size': MAX_BATCH_SIZE,
            'processing_method': 'parallel_multi_key',
            'key_details': key_distribution
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
            ("AI Model", analysis_data.get('ai_model', 'Groq AI')),
            ("API Key Used", analysis_data.get('api_key_used', 'N/A')),
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
        ws_summary.merge_cells('A1:G1')
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
        ws_summary['B5'] = GROQ_MODEL or DEFAULT_MODEL
        ws_summary['A6'] = "API Keys Used"
        ws_summary['B6'] = len(ACTIVE_API_KEYS)
        
        # Candidates Ranking Table
        row = 8
        headers = ["Rank", "Candidate Name", "ATS Score", "Recommendation", "API Key", "Key Strengths", "Skills Missing"]
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
            
            api_key = analysis.get('api_key_used', 'N/A')
            ws_summary.cell(row=row, column=5, value=f"Key {api_key.replace('key_', '')}" if api_key != 'N/A' else 'N/A')
            
            # Key strengths (first 2)
            strengths = analysis.get('key_strengths', [])
            ws_summary.cell(row=row, column=6, value=", ".join(strengths[:2]) if strengths else "N/A")
            
            # Missing skills (first 2)
            missing = analysis.get('skills_missing', [])
            ws_summary.cell(row=row, column=7, value=", ".join(missing[:2]) if missing else "All skills matched")
            
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
            adjusted_width = min(max_length + 2, 50)
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

# ... [Keep the remaining routes and functions the same as before] ...

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
    """Force warm-up Groq API"""
    update_activity()
    
    try:
        if not ACTIVE_API_KEYS:
            return jsonify({
                'status': 'error',
                'message': 'Groq API not configured',
                'warmup_complete': False
            })
        
        result = warmup_groq_service()
        
        return jsonify({
            'status': 'success' if result else 'error',
            'message': f'Groq API warmed up successfully with {len(ACTIVE_API_KEYS)} keys' if result else 'Warm-up failed',
            'warmup_complete': warmup_complete,
            'ai_provider': 'groq',
            'model': GROQ_MODEL or DEFAULT_MODEL,
            'api_keys': len(ACTIVE_API_KEYS),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'warmup_complete': False
        })

@app.route('/keys-status', methods=['GET'])
def keys_status():
    """Check status of all API keys"""
    update_activity()
    
    try:
        keys_info = []
        for i, key in enumerate(ACTIVE_API_KEYS, 1):
            key_info = KEY_USAGE.get(key, {})
            keys_info.append({
                'key_number': i,
                'usage': key_info.get('count', 0),
                'limit': KEY_LIMIT,
                'available': key_info.get('available', True),
                'errors': key_info.get('errors', 0),
                'requests_today': key_info.get('requests_today', 0),
                'concurrent': key_info.get('concurrent', 0),
                'status': 'active' if key_info.get('errors', 0) < 2 else 'error'
            })
        
        # Calculate distribution
        distribution = {}
        for i in range(1, len(ACTIVE_API_KEYS) + 1):
            start_idx = (i - 1) * KEY_LIMIT + 1
            end_idx = i * KEY_LIMIT
            distribution[f"Key {i}"] = f"Resumes {start_idx}-{end_idx}"
        
        return jsonify({
            'total_keys': len(ACTIVE_API_KEYS),
            'keys': keys_info,
            'key_limit_per_key': KEY_LIMIT,
            'max_batch_size': MAX_BATCH_SIZE,
            'key_distribution': distribution,
            'max_concurrent_per_key': MAX_CONCURRENT_PER_KEY,
            'round_robin_enabled': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/quick-check', methods=['GET'])
def quick_check():
    """Quick endpoint to check if Groq API is responsive"""
    update_activity()
    
    try:
        if not ACTIVE_API_KEYS:
            return jsonify({
                'available': False, 
                'reason': 'No Groq API keys configured',
                'warmup_complete': warmup_complete
            })
        
        if not warmup_complete:
            return jsonify({
                'available': False,
                'reason': 'Groq API is warming up',
                'warmup_complete': False,
                'ai_provider': 'groq',
                'model': GROQ_MODEL or DEFAULT_MODEL,
                'api_keys': len(ACTIVE_API_KEYS)
            })
        
        # Test first key
        start_time = time.time()
        
        try:
            response = call_groq_api(
                prompt="Say 'ready'",
                max_tokens=10,
                timeout=10,
                api_key=ACTIVE_API_KEYS[0]
            )
            
            response_time = time.time() - start_time
            
            if isinstance(response, dict) and 'error' in response:
                return jsonify({
                    'available': False,
                    'response_time': f'{response_time:.2f}s',
                    'status': 'error',
                    'error': response.get('error'),
                    'ai_provider': 'groq',
                    'model': GROQ_MODEL or DEFAULT_MODEL,
                    'api_keys': len(ACTIVE_API_KEYS),
                    'warmup_complete': warmup_complete
                })
            elif response and 'ready' in str(response).lower():
                return jsonify({
                    'available': True,
                    'response_time': f'{response_time:.2f}s',
                    'status': 'ready',
                    'ai_provider': 'groq',
                    'model': GROQ_MODEL or DEFAULT_MODEL,
                    'api_keys': len(ACTIVE_API_KEYS),
                    'warmup_complete': True,
                    'max_batch_size': MAX_BATCH_SIZE,
                    'key_limit': KEY_LIMIT
                })
            else:
                return jsonify({
                    'available': False,
                    'response_time': f'{response_time:.2f}s',
                    'status': 'no_response',
                    'ai_provider': 'groq',
                    'model': GROQ_MODEL or DEFAULT_MODEL,
                    'api_keys': len(ACTIVE_API_KEYS),
                    'warmup_complete': warmup_complete
                })
                
        except Exception as e:
            return jsonify({
                'available': False,
                'reason': str(e)[:100],
                'status': 'error',
                'ai_provider': 'groq',
                'model': GROQ_MODEL or DEFAULT_MODEL,
                'api_keys': len(ACTIVE_API_KEYS),
                'warmup_complete': warmup_complete
            })
            
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'available': False,
            'reason': error_msg[:100],
            'status': 'error',
            'ai_provider': 'groq',
            'model': GROQ_MODEL or DEFAULT_MODEL,
            'api_keys': len(ACTIVE_API_KEYS),
            'warmup_complete': warmup_complete
        })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    update_activity()
    
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'resume-analyzer',
        'ai_provider': 'groq',
        'ai_warmup': warmup_complete,
        'model': model_to_use,
        'api_keys': len(ACTIVE_API_KEYS),
        'inactive_minutes': int((datetime.now() - last_activity_time).total_seconds() / 60),
        'keep_alive_active': True,
        'max_batch_size': MAX_BATCH_SIZE,
        'key_limit': KEY_LIMIT,
        'processing_method': 'parallel_multi_key'
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    
    # Calculate key distribution
    key_distribution = {}
    for i in range(len(ACTIVE_API_KEYS)):
        start_resume = i * KEY_LIMIT + 1
        end_resume = (i + 1) * KEY_LIMIT
        key_distribution[f"Key {i + 1}"] = f"Resumes {start_resume}-{end_resume}"
    
    return jsonify({
        'status': 'Service is running', 
        'timestamp': datetime.now().isoformat(),
        'ai_provider': 'groq',
        'ai_provider_configured': bool(ACTIVE_API_KEYS),
        'api_keys_count': len(ACTIVE_API_KEYS),
        'model': model_to_use,
        'ai_warmup_complete': warmup_complete,
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'reports_folder_exists': os.path.exists(REPORTS_FOLDER),
        'inactive_minutes': inactive_minutes,
        'version': '13.0.0',
        'optimizations': ['parallel_processing', 'round_robin_keys', 'intelligent_retry', 'rate_limit_protection'],
        'configuration': {
            'max_batch_size': MAX_BATCH_SIZE,
            'key_limit': KEY_LIMIT,
            'max_concurrent_per_key': MAX_CONCURRENT_PER_KEY,
            'max_retries': MAX_RETRIES,
            'max_individual_reports': MAX_INDIVIDUAL_REPORTS
        },
        'key_distribution': key_distribution,
        'processing_method': 'parallel_multi_key_round_robin'
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
    print(f"⚡ AI Provider: GROQ")
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    print(f"🤖 Model: {model_to_use}")
    print(f"🔑 Active API Keys: {len(ACTIVE_API_KEYS)}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📁 Reports folder: {REPORTS_FOLDER}")
    print(f"✅ Parallel Processing: Enabled")
    print(f"✅ Round-robin Key Distribution: Enabled")
    print(f"✅ Max Batch Size: {MAX_BATCH_SIZE} resumes")
    print(f"✅ Key Limit: {KEY_LIMIT} resumes per key")
    print(f"✅ Max Concurrent per Key: {MAX_CONCURRENT_PER_KEY}")
    print("="*50 + "\n")
    
    if not ACTIVE_API_KEYS:
        print("⚠️  WARNING: No Groq API keys found!")
        print("Please set GROQ_API_KEY_1, GROQ_API_KEY_2, GROQ_API_KEY_3 in Render environment variables")
    
    # Enable garbage collection
    gc.enable()
    
    # Start warm-up in background
    if ACTIVE_API_KEYS:
        warmup_thread = threading.Thread(target=warmup_groq_service, daemon=True)
        warmup_thread.start()
        
        # Start keep-warm thread
        keep_warm_thread = threading.Thread(target=keep_service_warm, daemon=True)
        keep_warm_thread.start()
        
        # Start periodic key reset
        def periodic_key_reset():
            while service_running:
                time.sleep(300)  # Every 5 minutes
                reset_key_usage()
                print("🔄 Periodic key usage reset")
        
        reset_thread = threading.Thread(target=periodic_key_reset, daemon=True)
        reset_thread.start()
        
        print("✅ Background threads started")
    
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode, threaded=True)
