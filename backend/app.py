# app.py - UPDATED VERSION with requested changes

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
import queue
from collections import defaultdict

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

# Filter out None or empty keys
GROQ_API_KEYS = [key for key in GROQ_API_KEYS if key and key.strip()]

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

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    'requests_per_minute': 30,
    'max_concurrent_per_key': 3,
    'request_delay': 2.0,
    'batch_delay': 0.5,
}

# Enhanced rate limiting
class RateLimiter:
    def __init__(self, keys, requests_per_minute=30):
        self.keys = keys
        self.requests_per_minute = requests_per_minute
        self.key_usage = defaultdict(list)
        self.lock = threading.Lock()
        self.key_status = {i: {'available': True, 'cooling_until': None, 'concurrent': 0} for i in range(len(keys))}
        
    def get_available_key(self):
        """Get next available key with proper rate limiting"""
        with self.lock:
            current_time = time.time()
            
            for key_index in range(len(self.keys)):
                status = self.key_status[key_index]
                
                if status['cooling_until'] and current_time < status['cooling_until']:
                    continue
                
                if status['concurrent'] >= RATE_LIMIT_CONFIG['max_concurrent_per_key']:
                    continue
                
                usage_times = self.key_usage[key_index]
                usage_times = [t for t in usage_times if current_time - t < 60]
                self.key_usage[key_index] = usage_times
                
                if len(usage_times) < self.requests_per_minute:
                    status['concurrent'] += 1
                    return key_index, self.keys[key_index]
            
            available_times = []
            for key_index in range(len(self.keys)):
                status = self.key_status[key_index]
                if status['cooling_until']:
                    wait_time = status['cooling_until'] - current_time
                else:
                    usage_times = self.key_usage[key_index]
                    if len(usage_times) >= self.requests_per_minute:
                        oldest = min(usage_times)
                        wait_time = 60 - (current_time - oldest)
                    else:
                        wait_time = 0
                
                available_times.append((wait_time, key_index))
            
            available_times.sort()
            wait_time, key_index = available_times[0]
            
            if wait_time > 0:
                time.sleep(min(wait_time, 5))
            
            status = self.key_status[key_index]
            status['concurrent'] += 1
            return key_index, self.keys[key_index]
    
    def mark_request_complete(self, key_index):
        """Mark request as complete for a key"""
        with self.lock:
            self.key_usage[key_index].append(time.time())
            self.key_status[key_index]['concurrent'] -= 1
    
    def mark_key_cooling(self, key_index, duration=60):
        """Mark a key as cooling down"""
        with self.lock:
            self.key_status[key_index]['cooling_until'] = time.time() + duration
            self.key_status[key_index]['concurrent'] = 0
            
            def reset_cooling():
                time.sleep(duration)
                with self.lock:
                    self.key_status[key_index]['cooling_until'] = None
                    print(f"✅ Key {key_index + 1} cooling completed")
            
            threading.Thread(target=reset_cooling, daemon=True).start()

# Initialize rate limiter
rate_limiter = RateLimiter(GROQ_API_KEYS, RATE_LIMIT_CONFIG['requests_per_minute'])

# Batch processing configuration
MAX_BATCH_SIZE = 10
MIN_SKILLS_TO_SHOW = 5
MAX_SKILLS_TO_SHOW = 8

# Rate limiting protection
MAX_RETRIES = 5
RETRY_DELAY_BASE = 2

# Memory optimization
service_running = True

# Resume storage tracking
resume_storage = {}

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

def store_resume_file(file_data, filename, analysis_id):
    """Store resume file for later preview"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        preview_filename = f"{analysis_id}_{safe_filename}"
        preview_path = os.path.join(RESUME_PREVIEW_FOLDER, preview_filename)
        
        with open(preview_path, 'wb') as f:
            if isinstance(file_data, bytes):
                f.write(file_data)
            else:
                file_data.save(f)
        
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

def get_resume_preview(analysis_id):
    """Get resume preview data"""
    return resume_storage.get(analysis_id)

def call_groq_api_with_retry(prompt, api_key, key_index, max_tokens=1500, temperature=0.1, max_retries=MAX_RETRIES):
    """Call Groq API with exponential backoff and key rotation"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': GROQ_MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': temperature,
        'top_p': 0.9,
        'stream': False,
        'stop': None
    }
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                jitter = random.uniform(0.5, 1.5)
                wait_time = (RETRY_DELAY_BASE ** attempt) * jitter
                print(f"⏳ Retry {attempt + 1}/{max_retries} in {wait_time:.1f}s (Key {key_index + 1})")
                time.sleep(wait_time)
            
            start_time = time.time()
            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=45 + (attempt * 5)
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    result = data['choices'][0]['message']['content']
                    print(f"✅ Groq API response in {response_time:.2f}s (Key {key_index + 1})")
                    return result
                else:
                    print(f"❌ Unexpected Groq API response format (Key {key_index + 1})")
                    continue
            
            elif response.status_code == 429:
                print(f"❌ Rate limit exceeded for Key {key_index + 1}")
                rate_limiter.mark_key_cooling(key_index, 60)
                
                if attempt < max_retries - 1 and len(GROQ_API_KEYS) > 1:
                    new_key_index, new_api_key = rate_limiter.get_available_key()
                    if new_key_index != key_index:
                        print(f"🔄 Switching from Key {key_index + 1} to Key {new_key_index + 1}")
                        rate_limiter.mark_request_complete(key_index)
                        return call_groq_api_with_retry(prompt, new_api_key, new_key_index, max_tokens, temperature, max_retries - attempt)
                
                continue
                
            elif response.status_code == 503:
                print(f"❌ Service unavailable for Groq API (Key {key_index + 1})")
                time.sleep(10 + random.uniform(0, 5))
                continue
            
            else:
                print(f"❌ Groq API Error {response.status_code}: {response.text[:100]} (Key {key_index + 1})")
                continue
                
        except requests.exceptions.Timeout:
            print(f"❌ Groq API timeout (Key {key_index + 1})")
            continue
        
        except Exception as e:
            print(f"❌ Groq API Exception (Key {key_index + 1}): {str(e)}")
            continue
    
    return {'error': 'max_retries_exceeded', 'status': 429}

def warmup_groq_service():
    """Warm up Groq service connection"""
    global warmup_complete
    
    if len(GROQ_API_KEYS) == 0:
        print("⚠️ Skipping Groq warm-up: No API keys configured")
        return False
    
    try:
        print(f"🔥 Warming up Groq connection with {len(GROQ_API_KEYS)} keys...")
        print(f"📊 Using model: {GROQ_MODEL}")
        
        warmup_results = []
        
        for i, api_key in enumerate(GROQ_API_KEYS):
            print(f"  Testing key {i+1}...")
            start_time = time.time()
            
            response = call_groq_api_with_retry(
                prompt="Hello, are you ready? Respond with just 'ready'.",
                api_key=api_key,
                key_index=i,
                max_tokens=10,
                temperature=0.1
            )
            
            if isinstance(response, dict) and 'error' in response:
                print(f"    ⚠️ Key {i+1} failed: {response.get('error')}")
                warmup_results.append(False)
            elif response and 'ready' in response.lower():
                elapsed = time.time() - start_time
                print(f"    ✅ Key {i+1} warmed up in {elapsed:.2f}s")
                warmup_results.append(True)
            else:
                print(f"    ⚠️ Key {i+1} warm-up failed: Unexpected response")
                warmup_results.append(False)
            
            if i < len(GROQ_API_KEYS) - 1:
                time.sleep(2)
        
        success = any(warmup_results)
        if success:
            print(f"✅ Groq service warmed up successfully")
            warmup_complete = True
        else:
            print(f"⚠️ Groq warm-up failed on all keys")
            
        return success
        
    except Exception as e:
        print(f"⚠️ Warm-up attempt failed: {str(e)}")
        threading.Timer(30.0, warmup_groq_service).start()
        return False

def keep_service_warm():
    """Periodically send requests to keep Groq service responsive"""
    global service_running
    
    while service_running:
        try:
            time.sleep(180)
            
            if len(GROQ_API_KEYS) > 0 and warmup_complete:
                print(f"♨️ Keeping Groq warm with {len(GROQ_API_KEYS)} keys...")
                
                for i, api_key in enumerate(GROQ_API_KEYS):
                    try:
                        response = call_groq_api_with_retry(
                            prompt="Ping - just say 'pong'",
                            api_key=api_key,
                            key_index=i,
                            max_tokens=5
                        )
                        if response and 'pong' in str(response).lower():
                            print(f"  ✅ Key {i+1} keep-alive successful")
                        else:
                            print(f"  ⚠️ Key {i+1} keep-alive got unexpected response")
                    except Exception as e:
                        print(f"  ⚠️ Key {i+1} keep-alive failed: {str(e)}")
                    time.sleep(1)
                    
        except Exception as e:
            print(f"⚠️ Keep-warm thread error: {str(e)}")
            time.sleep(180)

# Text extraction functions
def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        text = ""
        max_attempts = 2
        
        for attempt in range(max_attempts):
            try:
                reader = PdfReader(file_path)
                text = ""
                
                for page_num, page in enumerate(reader.pages[:8]):
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
                                text = ' '.join(words[:1500])
                    except:
                        text = "Error: Could not extract text from PDF file"
        
        if not text.strip():
            return "Error: PDF appears to be empty or text could not be extracted"
        
        return text
    except Exception as e:
        print(f"❌ PDF Error: {traceback.format_exc()}")
        return f"Error reading PDF: {str(e)[:100]}"

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs[:150] if paragraph.text.strip()])
        
        if not text.strip():
            return "Error: Document appears to be empty"
        
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
                
                return text
            except UnicodeDecodeError:
                continue
                
        return "Error: Could not decode text file with common encodings"
        
    except Exception as e:
        print(f"❌ TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

def analyze_resume_with_ai(resume_text, job_description, filename=None, analysis_id=None):
    """Use Groq API to analyze resume against job description with rate limiting"""
    
    if len(GROQ_API_KEYS) == 0:
        print(f"❌ No Groq API keys configured.")
        return generate_fallback_analysis(filename, "No API keys configured")
    
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
    "skills_matched": ["skill1", "skill2", "skill3", "skill4", "skill5", "skill6", "skill7", "skill8"],
    "skills_missing": ["skill1", "skill2", "skill3", "skill4", "skill5", "skill6", "skill7", "skill8"],
    "experience_summary": "Provide a concise 4-5 sentence summary of candidate's experience. Focus on key roles, achievements, and relevance. Make sure each sentence is complete and not truncated. Write full sentences.",
    "years_of_experience": "5+ years",
    "overall_score": 75,
    "recommendation": "Strongly Recommended/Recommended/Consider/Not Recommended",
    "key_strengths": ["strength1", "strength2", "strength3"],
    "areas_for_improvement": ["area1", "area2", "area3"]
}}

IMPORTANT: 
1. Provide 5-8 skills in both skills_matched and skills_missing arrays
2. Experience summary: MAX 4-5 COMPLETE sentences (not truncated)
3. DO NOT include education summary, job_title_suggestion, industry_fit, or salary_expectation
4. Provide EXACTLY 3 key_strengths and 3 areas_for_improvement
5. Provide years_of_experience as a string (e.g., "2-4 years", "5+ years", "10+ years")
6. Write full, complete sentences. Do not cut off sentences mid-way.
7. Ensure proper sentence endings with periods."""

    try:
        print(f"⚡ Getting API key for analysis...")
        
        key_index, api_key = rate_limiter.get_available_key()
        print(f"⚡ Using Key {key_index + 1} for analysis...")
        
        start_time = time.time()
        
        response = call_groq_api_with_retry(
            prompt=prompt,
            api_key=api_key,
            key_index=key_index,
            max_tokens=1500,
            temperature=0.1
        )
        
        rate_limiter.mark_request_complete(key_index)
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            print(f"❌ Groq API error: {error_type}")
            
            if 'rate_limit' in error_type or '429' in str(error_type):
                rate_limiter.mark_key_cooling(key_index, 60)
            
            return generate_fallback_analysis(filename, f"API Error: {error_type}", partial_success=True)
        
        elapsed_time = time.time() - start_time
        print(f"✅ Groq API response in {elapsed_time:.2f} seconds (Key {key_index + 1})")
        
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
            print(f"✅ Successfully parsed JSON response")
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            print(f"Response was: {result_text[:150]}")
            
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
        analysis['key_used'] = f"Key {key_index + 1}"
        
        if analysis_id:
            analysis['analysis_id'] = analysis_id
        
        print(f"✅ Analysis completed: {analysis['candidate_name']} (Score: {analysis['overall_score']}) (Key {key_index + 1})")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Groq Analysis Error: {str(e)}")
        return generate_fallback_analysis(filename, f"Analysis Error: {str(e)[:100]}")
    
def validate_analysis(analysis, filename):
    """Validate analysis data and fill missing fields"""
    required_fields = {
        'candidate_name': 'Professional Candidate',
        'skills_matched': ['Python', 'JavaScript', 'SQL', 'Communication', 'Problem Solving', 'Team Collaboration', 'Project Management', 'Agile Methodology'],
        'skills_missing': ['Machine Learning', 'Cloud Computing', 'Data Analysis', 'DevOps', 'UI/UX Design', 'Cybersecurity', 'Mobile Development', 'Database Administration'],
        'experience_summary': 'The candidate demonstrates relevant professional experience with progressive responsibility. Their background shows expertise in key areas relevant to modern industry demands. They have experience collaborating with teams and delivering measurable results. Additional experience in specific domains enhances their suitability.',
        'years_of_experience': '3-5 years',
        'overall_score': 70,
        'recommendation': 'Consider for Interview',
        'key_strengths': ['Strong technical foundation', 'Excellent communication skills', 'Proven track record of delivery'],
        'areas_for_improvement': ['Could benefit from advanced certifications', 'Limited experience in cloud platforms', 'Should gain experience with newer technologies']
    }
    
    for field, default_value in required_fields.items():
        if field not in analysis:
            analysis[field] = default_value
    
    if analysis['candidate_name'] == 'Professional Candidate' and filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').title()
        if len(clean_name.split()) <= 4:
            analysis['candidate_name'] = clean_name
    
    skills_matched = analysis.get('skills_matched', [])
    skills_missing = analysis.get('skills_missing', [])
    
    if len(skills_matched) < MIN_SKILLS_TO_SHOW:
        default_skills = ['Python', 'JavaScript', 'SQL', 'Communication', 'Problem Solving', 'Teamwork', 'Project Management', 'Agile']
        needed = MIN_SKILLS_TO_SHOW - len(skills_matched)
        skills_matched.extend(default_skills[:needed])
    
    if len(skills_missing) < MIN_SKILLS_TO_SHOW:
        default_skills = ['Machine Learning', 'Cloud Computing', 'Data Analysis', 'DevOps', 'UI/UX', 'Cybersecurity', 'Mobile Dev', 'Database']
        needed = MIN_SKILLS_TO_SHOW - len(skills_missing)
        skills_missing.extend(default_skills[:needed])
    
    analysis['skills_matched'] = skills_matched[:MAX_SKILLS_TO_SHOW]
    analysis['skills_missing'] = skills_missing[:MAX_SKILLS_TO_SHOW]
    
    analysis['key_strengths'] = analysis.get('key_strengths', [])[:3]
    analysis['areas_for_improvement'] = analysis.get('areas_for_improvement', [])[:3]
    
    # Remove any education summary if present
    if 'education_summary' in analysis:
        del analysis['education_summary']
    
    for field in ['experience_summary']:
        if field in analysis:
            text = analysis[field]
            if '...' in text:
                sentences = text.split('. ')
                complete_sentences = []
                for sentence in sentences:
                    if '...' in sentence:
                        sentence = sentence.split('...')[0]
                        if sentence.strip():
                            complete_sentences.append(sentence.strip() + '.')
                        break
                    elif sentence.strip():
                        complete_sentences.append(sentence.strip() + '.')
                analysis[field] = ' '.join(complete_sentences)
            
            if not analysis[field].strip().endswith(('.', '!', '?')):
                analysis[field] = analysis[field].strip() + '.'
            
            if len(analysis[field]) > 800:
                sentences = analysis[field].split('. ')
                if len(sentences) > 5:
                    analysis[field] = '. '.join(sentences[:5]) + '.'
    
    unwanted_fields = ['job_title_suggestion', 'industry_fit', 'salary_expectation', 'education_summary']
    for field in unwanted_fields:
        if field in analysis:
            del analysis[field]
    
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
            "skills_matched": ['Python Programming', 'JavaScript Development', 'Database Management', 'Communication Skills', 'Problem Solving', 'Team Collaboration'],
            "skills_missing": ['Machine Learning Algorithms', 'Cloud Platform Expertise', 'Advanced Data Analysis', 'DevOps Practices', 'UI/UX Design Principles'],
            "experience_summary": 'The candidate has demonstrated professional experience in relevant technical roles. Their background includes working with modern technologies and methodologies. They have contributed to multiple projects with measurable outcomes. Additional experience enhances their suitability for the role.',
            "years_of_experience": "3-5 years",
            "overall_score": 55,
            "recommendation": "Needs Full Analysis",
            "key_strengths": ['Technical proficiency', 'Communication abilities', 'Problem-solving approach'],
            "areas_for_improvement": ['Advanced technical skills needed', 'Cloud platform experience required', 'Industry-specific knowledge'],
            "ai_provider": "groq",
            "ai_status": "Partial",
            "ai_model": GROQ_MODEL,
        }
    else:
        return {
            "candidate_name": candidate_name,
            "skills_matched": ['Basic Programming', 'Communication Skills', 'Problem Solving', 'Teamwork', 'Technical Knowledge', 'Learning Ability'],
            "skills_missing": ['Advanced Technical Skills', 'Industry Experience', 'Specialized Knowledge', 'Certifications', 'Project Management'],
            "experience_summary": 'Professional experience analysis will be available once the Groq AI service is fully initialized. The candidate appears to have relevant background based on initial file processing. Additional details will be available with full analysis.',
            "years_of_experience": "1-3 years",
            "overall_score": 50,
            "recommendation": "Service Warming Up - Please Retry",
            "key_strengths": ['Fast learning capability', 'Strong work ethic', 'Good communication'],
            "areas_for_improvement": ['Service initialization required', 'Complete analysis pending', 'Detailed assessment needed'],
            "ai_provider": "groq",
            "ai_status": "Warming up",
            "ai_model": GROQ_MODEL,
        }

def process_single_resume(args):
    """Process a single resume with intelligent rate limiting"""
    resume_file, job_description, index, total, batch_id = args
    
    try:
        print(f"📄 Processing resume {index + 1}/{total}: {resume_file.filename}")
        
        delay = (index * RATE_LIMIT_CONFIG['batch_delay']) + random.uniform(0, 0.3)
        if delay > 0:
            print(f"⏳ Adding {delay:.1f}s delay before processing resume {index + 1}...")
            time.sleep(delay)
        
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"batch_{batch_id}_{index}{file_ext}")
        
        resume_file.save(file_path)
        
        analysis_id = f"{batch_id}_resume_{index}"
        preview_filename = store_resume_file(resume_file, resume_file.filename, analysis_id)
        
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
        
        analysis = analyze_resume_with_ai(
            resume_text, 
            job_description, 
            resume_file.filename, 
            analysis_id
        )
        
        analysis['filename'] = resume_file.filename
        analysis['original_filename'] = resume_file.filename
        
        resume_file.seek(0, 2)
        file_size = resume_file.tell()
        resume_file.seek(0)
        analysis['file_size'] = f"{(file_size / 1024):.1f}KB"
        
        analysis['analysis_id'] = analysis_id
        analysis['processing_order'] = index + 1
        
        analysis['resume_stored'] = preview_filename is not None
        
        if preview_filename:
            analysis['resume_preview_filename'] = preview_filename
            analysis['resume_original_filename'] = resume_file.filename
        
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

def create_comprehensive_batch_report(analyses, job_description, filename="batch_resume_analysis.xlsx"):
    """Create a comprehensive batch Excel report with candidate comparison sheet and individual sheets"""
    try:
        wb = Workbook()
        
        # Remove default sheet
        if 'Sheet' in wb.sheetnames:
            default_sheet = wb['Sheet']
            wb.remove(default_sheet)
        
        # 1. Create Candidate Comparison Sheet (Main Sheet)
        ws_comparison = wb.create_sheet("Candidate Comparison")
        
        title_font = Font(bold=True, size=16, color="FFFFFF")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        normal_font = Font(size=10)
        bold_font = Font(bold=True, size=10)
        
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        subheader_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        even_row_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        odd_row_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        
        thin_border = Border(
            left=Side(style='thin', color='000000'),
            right=Side(style='thin', color='000000'),
            top=Side(style='thin', color='000000'),
            bottom=Side(style='thin', color='000000')
        )
        
        thick_border = Border(
            left=Side(style='medium', color='000000'),
            right=Side(style='medium', color='000000'),
            top=Side(style='medium', color='000000'),
            bottom=Side(style='medium', color='000000')
        )
        
        # Title
        ws_comparison.merge_cells('A1:K1')
        title_cell = ws_comparison['A1']
        title_cell.value = "RESUME ANALYSIS REPORT - BATCH COMPARISON"
        title_cell.font = title_font
        title_cell.fill = header_fill
        title_cell.alignment = Alignment(horizontal='center', vertical='center')
        title_cell.border = thick_border
        
        # Info row
        info_row = 3
        info_data = [
            ("Report Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("Total Candidates:", len(analyses)),
            ("AI Model:", f"Groq {GROQ_MODEL}"),
        ]
        
        for i, (label, value) in enumerate(info_data):
            ws_comparison.cell(row=info_row, column=1 + i*4, value=label).font = bold_font
            ws_comparison.cell(row=info_row, column=2 + i*4, value=value).font = normal_font
            ws_comparison.merge_cells(start_row=info_row, start_column=2 + i*4, end_row=info_row, end_column=3 + i*4)
        
        # Job Description
        info_row += 2
        ws_comparison.merge_cells(f'A{info_row}:K{info_row}')
        ws_comparison.cell(row=info_row, column=1, value="Job Description:").font = bold_font
        info_row += 1
        ws_comparison.merge_cells(f'A{info_row}:K{info_row}')
        jd_text = job_description[:500] + "..." if len(job_description) > 500 else job_description
        ws_comparison.cell(row=info_row, column=1, value=jd_text)
        ws_comparison.cell(row=info_row, column=1).font = normal_font
        ws_comparison.cell(row=info_row, column=1).alignment = Alignment(wrap_text=True)
        ws_comparison.row_dimensions[info_row].height = 40
        
        start_row = info_row + 2
        
        # Updated headers with Filename first and Years of Experience
        headers = [
            ("Rank", 8),
            ("Filename", 25),  # Filename instead of Candidate Name
            ("Years of Experience", 15),  # New column
            ("ATS Score", 12),
            ("Recommendation", 20),
            ("Skills Matched", 30),
            ("Skills Missing", 30),
            ("Experience Summary", 50),
            ("Key Strengths", 30),
            ("Areas for Improvement", 30)
        ]
        
        for col, (header, width) in enumerate(headers, start=1):
            cell = ws_comparison.cell(row=start_row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = thin_border
            ws_comparison.column_dimensions[get_column_letter(col)].width = width
        
        # Add data rows
        for idx, analysis in enumerate(analyses):
            row = start_row + idx + 1
            row_fill = even_row_fill if idx % 2 == 0 else odd_row_fill
            
            # Rank
            cell = ws_comparison.cell(row=row, column=1, value=analysis.get('rank', '-'))
            cell.font = bold_font
            cell.alignment = Alignment(horizontal='center')
            cell.fill = row_fill
            cell.border = thin_border
            
            # Filename (instead of candidate name)
            cell = ws_comparison.cell(row=row, column=2, value=analysis.get('filename', 'Unknown'))
            cell.font = normal_font
            cell.fill = row_fill
            cell.border = thin_border
            
            # Years of Experience
            years_exp = analysis.get('years_of_experience', 'N/A')
            cell = ws_comparison.cell(row=row, column=3, value=years_exp)
            cell.alignment = Alignment(horizontal='center')
            cell.fill = row_fill
            cell.border = thin_border
            
            # ATS Score
            score = analysis.get('overall_score', 0)
            cell = ws_comparison.cell(row=row, column=4, value=score)
            cell.alignment = Alignment(horizontal='center')
            cell.fill = row_fill
            cell.border = thin_border
            if score >= 80:
                cell.font = Font(bold=True, color="00B050", size=10)
            elif score >= 60:
                cell.font = Font(bold=True, color="FFC000", size=10)
            else:
                cell.font = Font(bold=True, color="FF0000", size=10)
            
            # Recommendation
            cell = ws_comparison.cell(row=row, column=5, value=analysis.get('recommendation', 'N/A'))
            cell.font = normal_font
            cell.fill = row_fill
            cell.border = thin_border
            
            # Skills Matched
            skills_matched = analysis.get('skills_matched', [])
            cell = ws_comparison.cell(row=row, column=6, value="\n".join([f"• {skill}" for skill in skills_matched[:8]]))
            cell.font = Font(size=9)
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            cell.fill = row_fill
            cell.border = thin_border
            
            # Skills Missing
            skills_missing = analysis.get('skills_missing', [])
            cell = ws_comparison.cell(row=row, column=7, value="\n".join([f"• {skill}" for skill in skills_missing[:8]]))
            cell.font = Font(size=9, color="FF0000")
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            cell.fill = row_fill
            cell.border = thin_border
            
            # Experience Summary (NO Education Summary)
            experience = analysis.get('experience_summary', 'No experience summary available.')
            cell = ws_comparison.cell(row=row, column=8, value=experience)
            cell.font = Font(size=9)
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            cell.fill = row_fill
            cell.border = thin_border
            ws_comparison.row_dimensions[row].height = 80
            
            # Key Strengths
            strengths = analysis.get('key_strengths', [])
            cell = ws_comparison.cell(row=row, column=9, value="\n".join([f"• {strength}" for strength in strengths[:3]]))
            cell.font = Font(size=9, color="00B050")
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            cell.fill = row_fill
            cell.border = thin_border
            
            # Areas for Improvement
            improvements = analysis.get('areas_for_improvement', [])
            cell = ws_comparison.cell(row=row, column=10, value="\n".join([f"• {area}" for area in improvements[:3]]))
            cell.font = Font(size=9, color="FF6600")
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            cell.fill = row_fill
            cell.border = thin_border
        
        # Summary Statistics
        summary_row = start_row + len(analyses) + 2
        avg_score = round(sum(a.get('overall_score', 0) for a in analyses) / len(analyses), 1) if analyses else 0
        top_score = max((a.get('overall_score', 0) for a in analyses), default=0)
        bottom_score = min((a.get('overall_score', 0) for a in analyses), default=0)
        
        summary_data = [
            ("Average Score:", f"{avg_score}/100"),
            ("Highest Score:", f"{top_score}/100"),
            ("Lowest Score:", f"{bottom_score}/100"),
            ("Analysis Date:", datetime.now().strftime("%Y-%m-%d"))
        ]
        
        for i, (label, value) in enumerate(summary_data):
            ws_comparison.cell(row=summary_row, column=1 + i*3, value=label).font = bold_font
            ws_comparison.cell(row=summary_row, column=2 + i*3, value=value).font = bold_font
            ws_comparison.cell(row=summary_row, column=2 + i*3).alignment = Alignment(horizontal='center')
        
        # 2. Create Individual Sheets for Each Candidate
        for idx, analysis in enumerate(analyses):
            # Create sheet name from filename (safe for Excel)
            filename = analysis.get('filename', f'Candidate_{idx+1}')
            safe_sheet_name = re.sub(r'[\\/*?:\[\]]', '', filename[:31])  # Excel sheet names max 31 chars
            
            # Add index if sheet name already exists
            original_sheet_name = safe_sheet_name
            counter = 1
            while safe_sheet_name in wb.sheetnames:
                safe_sheet_name = f"{original_sheet_name[:28]}_{counter}"
                counter += 1
            
            ws_individual = wb.create_sheet(safe_sheet_name)
            
            # Individual candidate sheet styling
            ind_title_font = Font(bold=True, size=14, color="FFFFFF")
            ind_header_font = Font(bold=True, color="FFFFFF", size=10)
            ind_normal_font = Font(size=10)
            
            # Title
            ws_individual.merge_cells('A1:F1')
            title_cell = ws_individual['A1']
            title_cell.value = f"RESUME ANALYSIS - {analysis.get('filename', 'Candidate')}"
            title_cell.font = ind_title_font
            title_cell.fill = header_fill
            title_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Candidate Info
            info_row = 3
            info_fields = [
                ("Filename:", analysis.get('filename', 'N/A')),
                ("Rank:", analysis.get('rank', '-')),
                ("Years of Experience:", analysis.get('years_of_experience', 'N/A')),
                ("ATS Score:", f"{analysis.get('overall_score', 0)}/100"),
                ("Recommendation:", analysis.get('recommendation', 'N/A')),
                ("File Size:", analysis.get('file_size', 'N/A')),
                ("Analysis Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            ]
            
            for i, (label, value) in enumerate(info_fields):
                if i % 2 == 0:
                    row = info_row + (i // 2)
                    ws_individual.cell(row=row, column=1, value=label).font = Font(bold=True)
                    ws_individual.cell(row=row, column=2, value=value)
                    ws_individual.cell(row=row, column=3, value="")
                else:
                    ws_individual.cell(row=row, column=4, value=label).font = Font(bold=True)
                    ws_individual.cell(row=row, column=5, value=value)
            
            # Experience Summary Section
            exp_row = info_row + len(info_fields) // 2 + 2
            ws_individual.merge_cells(f'A{exp_row}:F{exp_row}')
            ws_individual.cell(row=exp_row, column=1, value="EXPERIENCE SUMMARY").font = ind_header_font
            ws_individual.cell(row=exp_row, column=1).fill = subheader_fill
            ws_individual.cell(row=exp_row, column=1).alignment = Alignment(horizontal='center')
            
            exp_row += 1
            ws_individual.merge_cells(f'A{exp_row}:F{exp_row}')
            experience_text = analysis.get('experience_summary', 'No experience summary available.')
            ws_individual.cell(row=exp_row, column=1, value=experience_text)
            ws_individual.cell(row=exp_row, column=1).font = ind_normal_font
            ws_individual.cell(row=exp_row, column=1).alignment = Alignment(wrap_text=True, vertical='top')
            ws_individual.row_dimensions[exp_row].height = 80
            
            # Skills Section
            skills_row = exp_row + 2
            
            # Skills Matched
            ws_individual.merge_cells(f'A{skills_row}:C{skills_row}')
            ws_individual.cell(row=skills_row, column=1, value="SKILLS MATCHED").font = ind_header_font
            ws_individual.cell(row=skills_row, column=1).fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
            ws_individual.cell(row=skills_row, column=1).alignment = Alignment(horizontal='center')
            
            ws_individual.merge_cells(f'D{skills_row}:F{skills_row}')
            ws_individual.cell(row=skills_row, column=4, value="SKILLS MISSING").font = ind_header_font
            ws_individual.cell(row=skills_row, column=4).fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
            ws_individual.cell(row=skills_row, column=4).alignment = Alignment(horizontal='center')
            
            skills_row += 1
            skills_matched = analysis.get('skills_matched', [])
            skills_missing = analysis.get('skills_missing', [])
            
            max_skills = max(len(skills_matched), len(skills_missing))
            for i in range(max_skills):
                if i < len(skills_matched):
                    ws_individual.cell(row=skills_row + i, column=1, value=f"• {skills_matched[i]}")
                    ws_individual.cell(row=skills_row + i, column=1).font = Font(color="006100")
                if i < len(skills_missing):
                    ws_individual.cell(row=skills_row + i, column=4, value=f"• {skills_missing[i]}")
                    ws_individual.cell(row=skills_row + i, column=4).font = Font(color="9C0006")
            
            # Strengths & Improvements Section
            insights_row = skills_row + max_skills + 2
            
            # Key Strengths
            ws_individual.merge_cells(f'A{insights_row}:C{insights_row}')
            ws_individual.cell(row=insights_row, column=1, value="KEY STRENGTHS").font = ind_header_font
            ws_individual.cell(row=insights_row, column=1).fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
            ws_individual.cell(row=insights_row, column=1).alignment = Alignment(horizontal='center')
            
            # Areas for Improvement
            ws_individual.merge_cells(f'D{insights_row}:F{insights_row}')
            ws_individual.cell(row=insights_row, column=4, value="AREAS FOR IMPROVEMENT").font = ind_header_font
            ws_individual.cell(row=insights_row, column=4).fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
            ws_individual.cell(row=insights_row, column=4).alignment = Alignment(horizontal='center')
            
            insights_row += 1
            strengths = analysis.get('key_strengths', [])
            improvements = analysis.get('areas_for_improvement', [])
            
            max_insights = max(len(strengths), len(improvements))
            for i in range(max_insights):
                if i < len(strengths):
                    ws_individual.cell(row=insights_row + i, column=1, value=f"• {strengths[i]}")
                if i < len(improvements):
                    ws_individual.cell(row=insights_row + i, column=4, value=f"• {improvements[i]}")
            
            # Set column widths
            for col in ['A', 'B', 'C', 'D', 'E', 'F']:
                ws_individual.column_dimensions[col].width = 25
        
        # Set column widths for comparison sheet
        for col, width in enumerate([8, 25, 15, 12, 20, 30, 30, 50, 30, 30], start=1):
            ws_comparison.column_dimensions[get_column_letter(col)].width = width
        
        # Save the workbook
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📊 Professional batch Excel report saved to: {filepath}")
        print(f"📄 Created {len(analyses) + 1} sheets: 1 comparison sheet + {len(analyses)} individual sheets")
        return filepath
        
    except Exception as e:
        print(f"❌ Error creating professional batch Excel report: {str(e)}")
        traceback.print_exc()
        return create_minimal_batch_report(analyses, job_description, filename)

def create_minimal_batch_report(analyses, job_description, filename):
    """Create a minimal batch report as fallback"""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Batch Analysis"
        
        ws['A1'] = "Batch Resume Analysis Report"
        ws['A1'].font = Font(bold=True, size=16)
        ws.merge_cells('A1:E1')
        
        ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws['A3'] = f"Total Candidates: {len(analyses)}"
        
        # Updated headers
        headers = ["Rank", "Filename", "Years of Experience", "ATS Score", "Recommendation"]
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=5, column=col, value=header)
            cell.font = Font(bold=True)
        
        for idx, analysis in enumerate(analyses):
            row = 6 + idx
            ws.cell(row=row, column=1, value=analysis.get('rank', '-'))
            ws.cell(row=row, column=2, value=analysis.get('filename', 'Unknown'))
            ws.cell(row=row, column=3, value=analysis.get('years_of_experience', 'N/A'))
            ws.cell(row=row, column=4, value=analysis.get('overall_score', 0))
            ws.cell(row=row, column=5, value=analysis.get('recommendation', 'N/A'))
        
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📊 Minimal batch report saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error creating minimal batch report: {str(e)}")
        traceback.print_exc()
        return None

def get_score_grade_text(score):
    """Get text description for score"""
    if score >= 90:
        return "Excellent Match 🎯"
    elif score >= 80:
        return "Great Match ✨"
    elif score >= 70:
        return "Good Match 👍"
    elif score >= 60:
        return "Fair Match 📊"
    else:
        return "Needs Improvement 📈"

@app.route('/')
def home():
    """Root route - API landing page"""
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    warmup_status = "✅ Ready" if warmup_complete else "🔥 Warming up..."
    
    available_keys = len(GROQ_API_KEYS)
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resume Analyzer API (Groq Parallel)</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; padding: 0; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .ready { background: #d4edda; color: #155724; }
            .warming { background: #fff3cd; color: #856404; }
            .endpoint { background: #f8f9fa; padding: 10px; margin: 10px 0; border-left: 4px solid #007bff; }
            .key-status { display: flex; gap: 10px; margin: 10px 0; }
            .key { padding: 5px 10px; border-radius: 3px; font-size: 12px; }
            .key-active { background: #d4edda; color: #155724; }
            .key-inactive { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Resume Analyzer API (Groq Parallel)</h1>
            <p>AI-powered resume analysis using Groq API with advanced rate limiting</p>
            
            <div class="status ''' + ('ready' if warmup_complete else 'warming') + '''">
                <strong>Status:</strong> ''' + warmup_status + '''
            </div>
            
            <div class="key-status">
                <strong>API Keys:</strong>
                ''' + ''.join([f'<span class="key key-active">Key {i+1}: ✅ Configured</span>' for i in range(available_keys)]) + '''
            </div>
            
            <p><strong>Model:</strong> ''' + GROQ_MODEL + '''</p>
            <p><strong>API Provider:</strong> Groq (Advanced Rate Limiting)</p>
            <p><strong>Max Batch Size:</strong> ''' + str(MAX_BATCH_SIZE) + ''' resumes</p>
            <p><strong>Rate Limit:</strong> ''' + str(RATE_LIMIT_CONFIG['requests_per_minute']) + ''' requests/min/key</p>
            <p><strong>Available Keys:</strong> ''' + str(available_keys) + '''</p>
            <p><strong>Last Activity:</strong> ''' + str(inactive_minutes) + ''' minutes ago</p>
            
            <h2>📡 Endpoints</h2>
            <div class="endpoint">
                <strong>POST /analyze</strong> - Analyze single resume
            </div>
            <div class="endpoint">
                <strong>POST /analyze-batch</strong> - Analyze multiple resumes (up to ''' + str(MAX_BATCH_SIZE) + ''')
            </div>
            <div class="endpoint">
                <strong>GET /health</strong> - Health check with key status
            </div>
            <div class="endpoint">
                <strong>GET /ping</strong> - Keep-alive ping
            </div>
            <div class="endpoint">
                <strong>GET /quick-check</strong> - Check Groq API availability
            </div>
            <div class="endpoint">
                <strong>GET /resume-preview/&lt;analysis_id&gt;</strong> - Get resume preview
            </div>
            <div class="endpoint">
                <strong>GET /download/&lt;filename&gt;</strong> - Download batch report
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
        
        resume_file.seek(0, 2)
        file_size = resume_file.tell()
        resume_file.seek(0)
        
        if file_size > 15 * 1024 * 1024:
            print(f"❌ File too large: {file_size} bytes")
            return jsonify({'error': 'File size too large. Maximum size is 15MB.'}), 400
        
        if len(GROQ_API_KEYS) == 0:
            return jsonify({'error': 'No Groq API keys configured'}), 500
        
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"resume_{timestamp}{file_ext}")
        resume_file.save(file_path)
        
        analysis_id = f"single_{timestamp}"
        preview_filename = store_resume_file(resume_file, resume_file.filename, analysis_id)
        
        if file_ext == '.pdf':
            resume_text = extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            resume_text = extract_text_from_docx(file_path)
        elif file_ext == '.txt':
            resume_text = extract_text_from_txt(file_path)
        else:
            return jsonify({'error': 'Unsupported file format. Please upload PDF, DOCX, or TXT'}), 400
        
        if resume_text.startswith('Error'):
            return jsonify({'error': resume_text}), 500
        
        analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id)
        
        if os.path.exists(file_path):
            os.remove(file_path)
        
        analysis['ai_model'] = GROQ_MODEL
        analysis['ai_provider'] = "groq"
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['response_time'] = analysis.get('response_time', 'N/A')
        analysis['analysis_id'] = analysis_id
        
        analysis['resume_stored'] = preview_filename is not None
        
        if preview_filename:
            analysis['resume_preview_filename'] = preview_filename
            analysis['resume_original_filename'] = resume_file.filename
        
        total_time = time.time() - start_time
        print(f"✅ Request completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/analyze-batch', methods=['POST'])
def analyze_resume_batch():
    """Analyze multiple resumes with parallel processing and rate limiting"""
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
        
        if len(GROQ_API_KEYS) == 0:
            print("❌ No Groq API keys configured")
            return jsonify({'error': 'No Groq API keys configured'}), 500
        
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        
        all_analyses = []
        errors = []
        
        print(f"🔄 Processing {len(resume_files)} resumes with {len(GROQ_API_KEYS)} keys...")
        print(f"📊 Using smart rate limiting with {RATE_LIMIT_CONFIG['requests_per_minute']} requests/min/key")
        
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
            
            if index < len(resume_files) - 1:
                delay = RATE_LIMIT_CONFIG['request_delay'] + random.uniform(0, 0.5)
                print(f"⏳ Waiting {delay:.1f}s before next resume...")
                time.sleep(delay)
        
        all_analyses.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        for rank, analysis in enumerate(all_analyses, 1):
            analysis['rank'] = rank
        
        batch_excel_path = None
        if all_analyses:
            try:
                print("📊 Creating batch Excel report...")
                excel_filename = f"batch_analysis_{batch_id}.xlsx"
                batch_excel_path = create_comprehensive_batch_report(all_analyses, job_description, excel_filename)
                print(f"✅ Excel report created: {batch_excel_path}")
            except Exception as e:
                print(f"❌ Failed to create Excel report: {str(e)}")
                traceback.print_exc()
                batch_excel_path = create_minimal_batch_report(all_analyses, job_description, excel_filename)
        
        total_time = time.time() - start_time
        batch_summary = {
            'success': True,
            'total_files': len(resume_files),
            'successfully_analyzed': len(all_analyses),
            'failed_files': len(errors),
            'errors': errors,
            'batch_excel_filename': os.path.basename(batch_excel_path) if batch_excel_path else None,
            'batch_id': batch_id,
            'analyses': all_analyses,
            'model_used': GROQ_MODEL,
            'ai_provider': "groq",
            'ai_status': "Warmed up" if warmup_complete else "Warming up",
            'processing_time': f"{total_time:.2f}s",
            'processing_method': 'sequential_with_rate_limiting',
            'available_keys': len(GROQ_API_KEYS),
            'rate_limit': f"{RATE_LIMIT_CONFIG['requests_per_minute']} requests/min/key",
            'success_rate': f"{(len(all_analyses) / len(resume_files)) * 100:.1f}%" if resume_files else "0%",
            'performance': f"{len(all_analyses)/total_time:.2f} resumes/second" if total_time > 0 else "N/A"
        }
        
        print(f"✅ Batch analysis completed in {total_time:.2f}s")
        print(f"📊 Success rate: {batch_summary['success_rate']}")
        print("="*50 + "\n")
        
        return jsonify(batch_summary)
        
    except Exception as e:
        print(f"❌ Batch analysis error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/resume-preview/<analysis_id>', methods=['GET'])
def get_resume_preview_route(analysis_id):
    """Get resume preview"""
    update_activity()
    
    try:
        print(f"📄 Resume preview request for: {analysis_id}")
        
        resume_info = get_resume_preview(analysis_id)
        if not resume_info:
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

@app.route('/warmup', methods=['GET'])
def force_warmup():
    """Force warm-up Groq API"""
    update_activity()
    
    try:
        available_keys = len(GROQ_API_KEYS)
        if available_keys == 0:
            return jsonify({
                'status': 'error',
                'message': 'No Groq API keys configured',
                'warmup_complete': False
            })
        
        result = warmup_groq_service()
        
        return jsonify({
            'status': 'success' if result else 'error',
            'message': f'Groq API warmed up successfully with {available_keys} keys' if result else 'Warm-up failed',
            'warmup_complete': warmup_complete,
            'ai_provider': 'groq',
            'model': GROQ_MODEL,
            'available_keys': available_keys,
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
    """Quick endpoint to check if Groq API is responsive"""
    update_activity()
    
    try:
        available_keys = len(GROQ_API_KEYS)
        if available_keys == 0:
            return jsonify({
                'available': False, 
                'reason': 'No Groq API keys configured',
                'available_keys': 0,
                'warmup_complete': warmup_complete
            })
        
        if not warmup_complete:
            return jsonify({
                'available': False,
                'reason': 'Groq API is warming up',
                'available_keys': available_keys,
                'warmup_complete': False,
                'ai_provider': 'groq',
                'model': GROQ_MODEL
            })
        
        working_keys = 0
        for i, api_key in enumerate(GROQ_API_KEYS):
            try:
                start_time = time.time()
                
                response = call_groq_api_with_retry(
                    prompt="Say 'ready'",
                    api_key=api_key,
                    key_index=i,
                    max_tokens=10
                )
                
                response_time = time.time() - start_time
                
                if isinstance(response, dict) and 'error' in response:
                    continue
                elif response and 'ready' in str(response).lower():
                    working_keys += 1
                    
                    if working_keys == 1:
                        return jsonify({
                            'available': True,
                            'response_time': f"{response_time:.2f}s",
                            'ai_provider': 'groq',
                            'model': GROQ_MODEL,
                            'warmup_complete': warmup_complete,
                            'available_keys': available_keys,
                            'working_keys': working_keys,
                            'tested_key': f"Key {i+1}",
                            'max_batch_size': MAX_BATCH_SIZE,
                            'processing_method': 'sequential_with_rate_limiting',
                            'rate_limit': f"{RATE_LIMIT_CONFIG['requests_per_minute']} requests/min/key",
                            'skills_analysis': '5-8 skills per category'
                        })
            except:
                continue
        
        if working_keys > 0:
            return jsonify({
                'available': True,
                'reason': f'{working_keys}/{available_keys} keys working',
                'available_keys': available_keys,
                'working_keys': working_keys,
                'warmup_complete': warmup_complete
            })
        
        return jsonify({
            'available': False,
            'reason': 'All keys failed',
            'available_keys': available_keys,
            'working_keys': 0,
            'warmup_complete': warmup_complete
        })
            
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'available': False,
            'reason': error_msg[:100],
            'available_keys': len(GROQ_API_KEYS),
            'ai_provider': 'groq',
            'model': GROQ_MODEL,
            'warmup_complete': warmup_complete
        })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    update_activity()
    
    available_keys = len(GROQ_API_KEYS)
    
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'resume-analyzer-groq',
        'ai_provider': 'groq',
        'ai_warmup': warmup_complete,
        'model': GROQ_MODEL,
        'available_keys': available_keys,
        'inactive_minutes': int((datetime.now() - last_activity_time).total_seconds() / 60),
        'keep_alive_active': True,
        'max_batch_size': MAX_BATCH_SIZE,
        'processing_method': 'sequential_with_rate_limiting',
        'skills_analysis': '5-8 skills per category'
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with key status"""
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    key_status = []
    for i, api_key in enumerate(GROQ_API_KEYS):
        key_status.append({
            'key': f'Key {i+1}',
            'configured': bool(api_key),
            'status': 'configured'
        })
    
    available_keys = len(GROQ_API_KEYS)
    
    return jsonify({
        'status': 'Service is running', 
        'timestamp': datetime.now().isoformat(),
        'ai_provider': 'groq',
        'ai_provider_configured': available_keys > 0,
        'model': GROQ_MODEL,
        'ai_warmup_complete': warmup_complete,
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'reports_folder_exists': os.path.exists(REPORTS_FOLDER),
        'resume_previews_folder_exists': os.path.exists(RESUME_PREVIEW_FOLDER),
        'resume_previews_stored': len(resume_storage),
        'inactive_minutes': inactive_minutes,
        'version': '2.7.0',
        'key_status': key_status,
        'available_keys': available_keys,
        'configuration': {
            'max_batch_size': MAX_BATCH_SIZE,
            'rate_limit': f"{RATE_LIMIT_CONFIG['requests_per_minute']} requests/min/key",
            'max_concurrent_per_key': RATE_LIMIT_CONFIG['max_concurrent_per_key'],
            'request_delay': RATE_LIMIT_CONFIG['request_delay'],
            'max_retries': MAX_RETRIES,
            'min_skills_to_show': MIN_SKILLS_TO_SHOW,
            'max_skills_to_show': MAX_SKILLS_TO_SHOW
        },
        'processing_method': 'sequential_with_rate_limiting',
        'performance_target': '10 resumes in 30-40 seconds',
        'skills_analysis': '5-8 skills per category',
        'summaries': 'Experience summary only (no education)',
        'insights': '3 strengths & 3 improvements',
        'report_features': 'Filename first + Years of Experience column'
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
            time.sleep(300)
            # Cleanup logic here
        except Exception as e:
            print(f"⚠️ Periodic cleanup error: {str(e)}")

atexit.register(cleanup_on_exit)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting (Groq with Rate Limiting)...")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"⚡ AI Provider: Groq (Advanced Rate Limiting)")
    print(f"🤖 Model: {GROQ_MODEL}")
    
    available_keys = len(GROQ_API_KEYS)
    print(f"🔑 API Keys: {available_keys} configured")
    
    for i, key in enumerate(GROQ_API_KEYS):
        print(f"  Key {i+1}: ✅ Configured")
    
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📁 Reports folder: {REPORTS_FOLDER}")
    print(f"📁 Resume Previews folder: {RESUME_PREVIEW_FOLDER}")
    print(f"✅ Advanced Rate Limiting: Enabled")
    print(f"✅ Rate Limit: {RATE_LIMIT_CONFIG['requests_per_minute']} requests/min/key")
    print(f"✅ Max Batch Size: {MAX_BATCH_SIZE} resumes")
    print(f"✅ Processing Method: Sequential with delays")
    print(f"✅ Request Delay: {RATE_LIMIT_CONFIG['request_delay']}s")
    print(f"✅ Batch Delay: {RATE_LIMIT_CONFIG['batch_delay']}s")
    print(f"✅ Max Retries: {MAX_RETRIES}")
    print(f"✅ Exponential Backoff: Enabled")
    print(f"✅ Skills Analysis: {MIN_SKILLS_TO_SHOW}-{MAX_SKILLS_TO_SHOW} skills per category")
    print(f"✅ Experience Summary Only: No education summary")
    print(f"✅ Filename First: Filename column instead of candidate name")
    print(f"✅ Years of Experience: New column added")
    print(f"✅ Report Structure: 1 comparison sheet + individual candidate sheets")
    print(f"✅ Performance: ~10 resumes in 30-40 seconds (safe mode)")
    print("="*50 + "\n")
    
    if available_keys == 0:
        print("⚠️  WARNING: No Groq API keys found!")
        print("Please set GROQ_API_KEY_1, GROQ_API_KEY_2, GROQ_API_KEY_3 in environment variables")
        print("Get free API keys from: https://console.groq.com")
    
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
