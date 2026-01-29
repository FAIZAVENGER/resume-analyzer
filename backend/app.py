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
import math

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
MAX_CONCURRENT_REQUESTS = 3
MAX_BATCH_SIZE = 10
MIN_SKILLS_TO_SHOW = 5  # Minimum skills to show
MAX_SKILLS_TO_SHOW = 8  # Maximum skills to show (5-8 range)

# Rate limiting protection
MAX_RETRIES = 3
RETRY_DELAY_BASE = 3

# Track key usage
key_usage = {
    0: {'count': 0, 'last_used': None, 'cooling': False},
    1: {'count': 0, 'last_used': None, 'cooling': False},
    2: {'count': 0, 'last_used': None, 'cooling': False}
}

# Memory optimization
service_running = True

# Resume storage tracking
resume_storage = {}

def update_activity():
    """Update last activity timestamp"""
    global last_activity_time
    last_activity_time = datetime.now()

def get_available_key(resume_index=None):
    """Get the next available Groq API key using round-robin strategy"""
    if not any(GROQ_API_KEYS):
        return None, None
    
    if resume_index is not None:
        key_index = resume_index % 3
        if GROQ_API_KEYS[key_index]:
            return GROQ_API_KEYS[key_index], key_index + 1
    
    for i, key in enumerate(GROQ_API_KEYS):
        if key and not key_usage[i]['cooling']:
            return key, i + 1
    
    return None, None

def mark_key_cooling(key_index, duration=30):
    """Mark a key as cooling down"""
    key_usage[key_index]['cooling'] = True
    key_usage[key_index]['last_used'] = datetime.now()
    
    def reset_cooling():
        time.sleep(duration)
        key_usage[key_index]['cooling'] = False
        print(f"✅ Key {key_index + 1} cooling completed")
    
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
        
        # Also create a PDF version for preview if not already PDF
        file_ext = os.path.splitext(filename)[1].lower()
        pdf_preview_path = None
        
        if file_ext == '.pdf':
            pdf_preview_path = preview_path
        else:
            # Try to convert to PDF for better preview
            try:
                pdf_filename = f"{analysis_id}_{safe_filename.rsplit('.', 1)[0]}_preview.pdf"
                pdf_preview_path = os.path.join(RESUME_PREVIEW_FOLDER, pdf_filename)
                
                if file_ext in ['.docx', '.doc']:
                    # Try to convert DOC/DOCX to PDF
                    convert_doc_to_pdf(preview_path, pdf_preview_path)
                elif file_ext == '.txt':
                    # Convert TXT to PDF
                    convert_txt_to_pdf(preview_path, pdf_preview_path)
            except Exception as e:
                print(f"⚠️ Could not create PDF preview: {str(e)}")
                pdf_preview_path = None
        
        # Store in memory for quick access
        resume_storage[analysis_id] = {
            'filename': preview_filename,
            'original_filename': filename,
            'path': preview_path,
            'pdf_path': pdf_preview_path,
            'file_type': file_ext[1:],  # Remove dot
            'has_pdf_preview': pdf_preview_path is not None and os.path.exists(pdf_preview_path),
            'stored_at': datetime.now().isoformat()
        }
        
        print(f"✅ Resume stored for preview: {preview_filename}")
        return preview_filename
    except Exception as e:
        print(f"❌ Error storing resume for preview: {str(e)}")
        return None

def convert_doc_to_pdf(doc_path, pdf_path):
    """Convert DOC/DOCX to PDF using LibreOffice or fallback methods"""
    try:
        # Check if LibreOffice is available
        if shutil.which('libreoffice'):
            # Use LibreOffice for conversion
            cmd = [
                'libreoffice', '--headless', '--convert-to', 'pdf',
                '--outdir', os.path.dirname(pdf_path),
                doc_path
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            
            # Rename the output file
            expected_pdf = doc_path.rsplit('.', 1)[0] + '.pdf'
            if os.path.exists(expected_pdf):
                shutil.move(expected_pdf, pdf_path)
                return True
        else:
            # Fallback: Try using python-docx2pdf if available
            try:
                from docx2pdf import convert
                convert(doc_path, pdf_path)
                return True
            except ImportError:
                pass
            
            # Another fallback: Create a simple PDF from text
            extract_text_and_create_pdf(doc_path, pdf_path)
            return True
            
    except Exception as e:
        print(f"⚠️ DOC to PDF conversion failed: {str(e)}")
        # Create a simple PDF from extracted text
        extract_text_and_create_pdf(doc_path, pdf_path)
        return True
    
    return False

def convert_txt_to_pdf(txt_path, pdf_path):
    """Convert TXT to PDF"""
    try:
        extract_text_and_create_pdf(txt_path, pdf_path)
        return True
    except Exception as e:
        print(f"⚠️ TXT to PDF conversion failed: {str(e)}")
        return False

def extract_text_and_create_pdf(input_path, pdf_path):
    """Extract text and create a simple PDF"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        from reportlab.lib.units import inch
        
        # Extract text based on file type
        file_ext = os.path.splitext(input_path)[1].lower()
        
        if file_ext == '.pdf':
            text = extract_text_from_pdf(input_path)
        elif file_ext in ['.docx', '.doc']:
            text = extract_text_from_docx(input_path)
        elif file_ext == '.txt':
            text = extract_text_from_txt(input_path)
        else:
            text = "Cannot preview this file type."
        
        # Create PDF
        doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=72)
        
        styles = getSampleStyleSheet()
        story = []
        
        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30
        )
        title = Paragraph("Resume Preview", title_style)
        story.append(title)
        
        # Add file info
        info_style = ParagraphStyle(
            'CustomInfo',
            parent=styles['Normal'],
            fontSize=10,
            textColor='gray',
            spaceAfter=20
        )
        info_text = f"Original file: {os.path.basename(input_path)} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        info = Paragraph(info_text, info_style)
        story.append(info)
        
        story.append(Spacer(1, 20))
        
        # Add content
        content_style = ParagraphStyle(
            'CustomContent',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            spaceBefore=6,
            spaceAfter=6
        )
        
        # Split text into paragraphs
        paragraphs = text.split('\n')
        for para in paragraphs:
            if para.strip():
                story.append(Paragraph(para.replace('\t', '&nbsp;' * 4), content_style))
        
        # Build PDF
        doc.build(story)
        return True
        
    except Exception as e:
        print(f"⚠️ Failed to create PDF from text: {str(e)}")
        # Create minimal PDF
        try:
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(pdf_path)
            c.drawString(100, 750, "Resume Preview")
            c.drawString(100, 730, f"File: {os.path.basename(input_path)}")
            c.drawString(100, 710, "Unable to display content. Please download the original file.")
            c.save()
            return True
        except:
            return False

def get_resume_preview(analysis_id):
    """Get resume preview data"""
    if analysis_id in resume_storage:
        return resume_storage[analysis_id]
    return None

def cleanup_resume_previews():
    """Clean up old resume previews"""
    try:
        now = datetime.now()
        for analysis_id in list(resume_storage.keys()):
            stored_time = datetime.fromisoformat(resume_storage[analysis_id]['stored_at'])
            if (now - stored_time).total_seconds() > 3600:  # 1 hour retention
                try:
                    # Clean up all related files
                    paths_to_clean = [
                        resume_storage[analysis_id]['path'],
                        resume_storage[analysis_id].get('pdf_path')
                    ]
                    
                    for path in paths_to_clean:
                        if path and os.path.exists(path):
                            os.remove(path)
                    
                    del resume_storage[analysis_id]
                    print(f"🧹 Cleaned up resume preview for {analysis_id}")
                except Exception as e:
                    print(f"⚠️ Error cleaning up files for {analysis_id}: {str(e)}")
        # Also clean up any orphaned files
        cleanup_orphaned_files()
    except Exception as e:
        print(f"⚠️ Error cleaning up resume previews: {str(e)}")

def cleanup_orphaned_files():
    """Clean up orphaned files in preview folder"""
    try:
        now = datetime.now()
        for filename in os.listdir(RESUME_PREVIEW_FOLDER):
            filepath = os.path.join(RESUME_PREVIEW_FOLDER, filename)
            if os.path.isfile(filepath):
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if (now - file_time).total_seconds() > 7200:  # 2 hours
                    try:
                        os.remove(filepath)
                        print(f"🧹 Cleaned up orphaned file: {filename}")
                    except:
                        pass
    except Exception as e:
        print(f"⚠️ Error cleaning up orphaned files: {str(e)}")

def call_groq_api(prompt, api_key, max_tokens=1500, temperature=0.1, timeout=45, retry_count=0):
    """Call Groq API with optimized settings"""
    if not api_key:
        print(f"❌ No Groq API key provided")
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
                print(f"✅ Groq API response in {response_time:.2f}s")
                return result
            else:
                print(f"❌ Unexpected Groq API response format")
                return {'error': 'invalid_response', 'status': response.status_code}
        
        if response.status_code == 429:
            print(f"❌ Rate limit exceeded for Groq API")
            
            if retry_count < MAX_RETRIES:
                wait_time = RETRY_DELAY_BASE ** (retry_count + 1) + random.uniform(5, 10)
                print(f"⏳ Rate limited, retrying in {wait_time:.1f}s (attempt {retry_count + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                return call_groq_api(prompt, api_key, max_tokens, temperature, timeout, retry_count + 1)
            return {'error': 'rate_limit', 'status': 429}
        
        elif response.status_code == 503:
            print(f"❌ Service unavailable for Groq API")
            
            if retry_count < 2:
                wait_time = 15 + random.uniform(5, 10)
                print(f"⏳ Service unavailable, retrying in {wait_time:.1f}s")
                time.sleep(wait_time)
                return call_groq_api(prompt, api_key, max_tokens, temperature, timeout, retry_count + 1)
            return {'error': 'service_unavailable', 'status': 503}
        
        else:
            print(f"❌ Groq API Error {response.status_code}: {response.text[:100]}")
            return {'error': f'api_error_{response.status_code}', 'status': response.status_code}
            
    except requests.exceptions.Timeout:
        print(f"❌ Groq API timeout after {timeout}s")
        
        if retry_count < 2:
            wait_time = 10 + random.uniform(5, 10)
            print(f"⏳ Timeout, retrying in {wait_time:.1f}s (attempt {retry_count + 1}/3)")
            time.sleep(wait_time)
            return call_groq_api(prompt, api_key, max_tokens, temperature, timeout, retry_count + 1)
        return {'error': 'timeout', 'status': 408}
    
    except Exception as e:
        print(f"❌ Groq API Exception: {str(e)}")
        return {'error': str(e), 'status': 500}

def warmup_groq_service():
    """Warm up Groq service connection"""
    global warmup_complete
    
    available_keys = sum(1 for key in GROQ_API_KEYS if key)
    if available_keys == 0:
        print("⚠️ Skipping Groq warm-up: No API keys configured")
        return False
    
    try:
        print(f"🔥 Warming up Groq connection with {available_keys} keys...")
        print(f"📊 Using model: {GROQ_MODEL}")
        
        warmup_results = []
        
        for i, api_key in enumerate(GROQ_API_KEYS):
            if api_key:
                print(f"  Testing key {i+1}...")
                start_time = time.time()
                
                response = call_groq_api(
                    prompt="Hello, are you ready? Respond with just 'ready'.",
                    api_key=api_key,
                    max_tokens=10,
                    temperature=0.1,
                    timeout=15
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
                
                if i < available_keys - 1:
                    time.sleep(1)
        
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
            
            available_keys = sum(1 for key in GROQ_API_KEYS if key)
            if available_keys > 0 and warmup_complete:
                print(f"♨️ Keeping Groq warm with {available_keys} keys...")
                
                for i, api_key in enumerate(GROQ_API_KEYS):
                    if api_key and not key_usage[i]['cooling']:
                        try:
                            response = call_groq_api(
                                prompt="Ping - just say 'pong'",
                                api_key=api_key,
                                max_tokens=5,
                                timeout=20
                            )
                            if response and 'pong' in str(response).lower():
                                print(f"  ✅ Key {i+1} keep-alive successful")
                            else:
                                print(f"  ⚠️ Key {i+1} keep-alive got unexpected response")
                        except Exception as e:
                            print(f"  ⚠️ Key {i+1} keep-alive failed: {str(e)}")
                        break
                    
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
                
                for page_num, page in enumerate(reader.pages[:8]):  # Increased to 8 pages
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
                                text = ' '.join(words[:1500])  # Increased word limit
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

def analyze_resume_with_ai(resume_text, job_description, filename=None, analysis_id=None, api_key=None, key_index=None):
    """Use Groq API to analyze resume against job description with STRICT scoring"""
    
    if not api_key:
        print(f"❌ No Groq API key provided for analysis.")
        return generate_fallback_analysis(filename, "No API key available")
    
    resume_text = resume_text[:3000]  # Increased from 2500
    job_description = job_description[:1500]  # Increased from 1200
    
    resume_hash = calculate_resume_hash(resume_text, job_description)
    cached_score = get_cached_score(resume_hash)
    
    prompt = f"""Analyze resume against job description with EXTREMELY STRICT and DIFFERENTIATED scoring:

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

CRITICAL SCORING INSTRUCTIONS:
You MUST calculate the ATS score using the EXACT following 5 dimensions. Each dimension MUST have a decimal score (not whole numbers). NO two resumes should have identical scores.

SCORING DIMENSIONS (Total: 100 points):
1. SKILLS MATCH (30 points) - Evaluate ONLY REQUIRED skills from job description:
   • Full points ONLY if skill is demonstrated with REAL usage, projects, or responsibilities
   • Partial or indirect usage: 50-75% of points
   • Skill mention without proof: 10-25% of points
   • Missing required skill: 0 points for that skill
   • Score: 0-30 with 1 decimal place (e.g., 24.7, 18.3)

2. EXPERIENCE RELEVANCE (25 points) - Count ONLY RELEVANT experience:
   • Each relevant year: 3-5 points depending on depth and responsibility
   • Penalize seniority mismatch: -2 to -5 points
   • Years without relevance: 0 points (must not increase score)
   • Score: 0-25 with 1 decimal place (e.g., 19.5, 22.8)

3. ROLE AND DOMAIN ALIGNMENT (20 points) - Compare previous roles with target role:
   • High overlap (same role/industry): 15-20 points
   • Medium overlap (similar responsibilities): 8-14 points
   • Low overlap (different domain): 0-7 points
   • Score: 0-20 with 1 decimal place (e.g., 16.2, 11.7)

4. PROJECTS AND PRACTICAL IMPACT (15 points) - Evaluate hands-on work:
   • System design/architecture projects: 12-15 points
   • Complex implementation projects: 8-11 points
   • Basic/tool-only projects: 3-7 points
   • No relevant projects: 0-2 points
   • Score: 0-15 with 1 decimal place (e.g., 12.4, 8.9)

5. RESUME QUALITY (10 points) - Evaluate clarity and specificity:
   • Clear, specific achievements with metrics: 8-10 points
   • Good structure but vague language: 5-7 points
   • Unclear responsibilities, repetition: 2-4 points
   • Poor formatting, hard to parse: 0-1 points
   • Score: 0-10 with 1 decimal place (e.g., 8.3, 6.7)

FINAL SCORE CALCULATION:
• Sum all 5 dimensions (0-100 total)
• MUST include 1 decimal place (e.g., 74.3, 81.7, 65.9)
• NO round numbers (avoid .0, .5 unless truly exact)
• Add small random variation (±0.1-0.3) if scores are too close
• Two resumes with identical content should have AT LEAST 0.2 difference

Provide analysis in this JSON format:
{{
    "candidate_name": "Extracted name or filename",
    "skills_matched": ["skill1", "skill2", "skill3", "skill4", "skill5", "skill6", "skill7", "skill8"],
    "skills_missing": ["skill1", "skill2", "skill3", "skill4", "skill5", "skill6", "skill7", "skill8"],
    "experience_summary": "Provide a concise 3-5 sentence summary of the candidate's professional experience. Highlight key achievements, roles, technologies used, and relevance to the job description. Keep it brief but informative.",
    "education_summary": "Provide a concise 3-5 sentence summary of the candidate's educational background. Include degrees, institutions, specializations, and any notable achievements or certifications. Keep it brief but informative.",
    "overall_score": 78.3,
    "score_breakdown": {{
        "skills_match": 24.7,
        "experience_relevance": 19.5,
        "role_alignment": 16.2,
        "projects_impact": 12.4,
        "resume_quality": 8.3
    }},
    "recommendation": "Strongly Recommended/Recommended/Consider/Not Recommended",
    "key_strengths": ["strength1", "strength2", "strength3", "strength4"],
    "areas_for_improvement": ["area1", "area2", "area3", "area4"]
}}

IMPORTANT: 
1. Provide 5-8 skills in both skills_matched and skills_missing arrays
2. Overall_score MUST have 1 decimal place and be between 0-100 (e.g., 74.3, 81.7)
3. Score_breakdown MUST have all 5 dimensions with 1 decimal place each
4. Provide CONCISE 3-5 sentence summaries for experience and education
5. Make key_strengths and areas_for_improvement lists 4 items each
6. Use STRICT evaluation - most candidates should score 40-80, not 70-90
7. If two resumes seem similar, add small variations (±0.1-0.3) to differentiate"""

    try:
        print(f"⚡ Sending to Groq API (Key {key_index}) with STRICT scoring...")
        start_time = time.time()
        
        response = call_groq_api(
            prompt=prompt,
            api_key=api_key,
            max_tokens=1800,
            temperature=0.3,  # Slightly higher for more variation
            timeout=60
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            print(f"❌ Groq API error: {error_type}")
            
            if 'rate_limit' in error_type or '429' in str(error_type):
                if key_index:
                    mark_key_cooling(key_index - 1, 30)
            
            return generate_fallback_analysis(filename, f"API Error: {error_type}", partial_success=True)
        
        elapsed_time = time.time() - start_time
        print(f"✅ Groq API response in {elapsed_time:.2f} seconds (Key {key_index})")
        
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
        
        analysis = validate_strict_analysis(analysis, filename)
        
        # Ensure overall_score has decimal
        try:
            overall_score = float(analysis['overall_score'])
            if overall_score.is_integer():
                # Add small decimal variation if it's a round number
                overall_score += random.uniform(0.1, 0.9)
                analysis['overall_score'] = round(overall_score, 1)
            else:
                analysis['overall_score'] = round(overall_score, 1)
            
            # Ensure score is within bounds
            if analysis['overall_score'] < 0:
                analysis['overall_score'] = 0.1
            elif analysis['overall_score'] > 100:
                analysis['overall_score'] = 99.9
                
        except:
            if cached_score:
                analysis['overall_score'] = cached_score + random.uniform(0.1, 0.9)
            else:
                analysis['overall_score'] = 50.0 + random.uniform(0.1, 9.9)
            analysis['overall_score'] = round(analysis['overall_score'], 1)
        
        # Ensure score_breakdown has decimals
        if 'score_breakdown' in analysis:
            for key in analysis['score_breakdown']:
                try:
                    val = float(analysis['score_breakdown'][key])
                    if val.is_integer():
                        analysis['score_breakdown'][key] = round(val + random.uniform(0.1, 0.9), 1)
                    else:
                        analysis['score_breakdown'][key] = round(val, 1)
                except:
                    analysis['score_breakdown'][key] = round(random.uniform(5.0, 20.0), 1)
        
        set_cached_score(resume_hash, analysis['overall_score'])
        
        analysis['ai_provider'] = "groq"
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['ai_model'] = GROQ_MODEL
        analysis['response_time'] = f"{elapsed_time:.2f}s"
        analysis['key_used'] = f"Key {key_index}"
        analysis['scoring_method'] = "Strict 5-Dimension ATS"
        
        if analysis_id:
            analysis['analysis_id'] = analysis_id
        
        print(f"✅ Analysis completed: {analysis['candidate_name']} (Score: {analysis['overall_score']}) (Key {key_index})")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Groq Analysis Error: {str(e)}")
        return generate_fallback_analysis(filename, f"Analysis Error: {str(e)[:100]}")
    
def validate_strict_analysis(analysis, filename):
    """Validate analysis data and fill missing fields with strict scoring"""
    # Generate unique decimal scores
    base_score = random.uniform(40.0, 80.0)
    
    # Ensure all required fields exist
    required_fields = {
        'candidate_name': 'Professional Candidate',
        'skills_matched': ['Python', 'JavaScript', 'SQL', 'Communication', 'Problem Solving', 'Team Collaboration', 'Project Management', 'Agile Methodology'],
        'skills_missing': ['Machine Learning', 'Cloud Computing', 'Data Analysis', 'DevOps', 'UI/UX Design', 'Cybersecurity', 'Mobile Development', 'Database Administration'],
        'experience_summary': 'The candidate demonstrates professional experience with varying levels of responsibility. Their background includes work with relevant technologies and methodologies. Specific achievements and project impacts are noted in the resume.',
        'education_summary': 'The candidate possesses educational qualifications that provide foundational knowledge for the role. Academic background includes relevant coursework and specializations. Additional certifications complement the formal education.',
        'overall_score': round(base_score, 1),
        'score_breakdown': {
            'skills_match': round(random.uniform(15.0, 28.0), 1),
            'experience_relevance': round(random.uniform(12.0, 23.0), 1),
            'role_alignment': round(random.uniform(10.0, 19.0), 1),
            'projects_impact': round(random.uniform(8.0, 14.0), 1),
            'resume_quality': round(random.uniform(6.0, 9.5), 1)
        },
        'recommendation': 'Consider for Interview',
        'key_strengths': ['Strong technical foundation', 'Effective communication skills', 'Proven ability to deliver results', 'Adaptability to new challenges'],
        'areas_for_improvement': ['Could benefit from advanced certifications', 'Limited experience in specific platforms', 'Could enhance project documentation skills', 'Needs more industry-specific knowledge']
    }
    
    for field, default_value in required_fields.items():
        if field not in analysis:
            analysis[field] = default_value
    
    if analysis['candidate_name'] == 'Professional Candidate' and filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').title()
        if len(clean_name.split()) <= 4:
            analysis['candidate_name'] = clean_name
    
    # Ensure score_breakdown exists and has all dimensions
    if 'score_breakdown' not in analysis:
        analysis['score_breakdown'] = required_fields['score_breakdown']
    else:
        for dim in ['skills_match', 'experience_relevance', 'role_alignment', 'projects_impact', 'resume_quality']:
            if dim not in analysis['score_breakdown']:
                analysis['score_breakdown'][dim] = round(random.uniform(5.0, 20.0), 1)
    
    # Ensure overall_score matches breakdown sum (approximately)
    breakdown_sum = sum(analysis['score_breakdown'].values())
    if abs(analysis.get('overall_score', 0) - breakdown_sum) > 5:
        analysis['overall_score'] = round(breakdown_sum, 1)
    
    # Ensure 5-8 skills in each category
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
    
    # Ensure 4 strengths and improvements
    analysis['key_strengths'] = analysis.get('key_strengths', [])[:4]
    analysis['areas_for_improvement'] = analysis.get('areas_for_improvement', [])[:4]
    
    # Trim summaries to be concise
    if len(analysis.get('experience_summary', '').split('. ')) > 5:
        sentences = analysis['experience_summary'].split('. ')
        analysis['experience_summary'] = '. '.join(sentences[:5]) + '.'
    
    if len(analysis.get('education_summary', '').split('. ')) > 5:
        sentences = analysis['education_summary'].split('. ')
        analysis['education_summary'] = '. '.join(sentences[:5]) + '.'
    
    # Remove unwanted fields
    unwanted_fields = ['job_title_suggestion', 'years_experience', 'industry_fit', 'salary_expectation']
    for field in unwanted_fields:
        if field in analysis:
            del analysis[field]
    
    return analysis

def generate_fallback_analysis(filename, reason, partial_success=False):
    """Generate a fallback analysis with decimal scoring"""
    candidate_name = "Professional Candidate"
    
    if filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').replace('resume', '').replace('cv', '').strip()
        if clean_name:
            parts = clean_name.split()
            if len(parts) >= 2 and len(parts) <= 4:
                candidate_name = ' '.join(part.title() for part in parts)
    
    # Generate unique decimal score
    base_score = random.uniform(45.0, 65.0)
    
    if partial_success:
        return {
            "candidate_name": candidate_name,
            "skills_matched": ['Python Programming', 'JavaScript Development', 'Database Management', 'Communication Skills', 'Problem Solving', 'Team Collaboration', 'Project Planning', 'Technical Documentation'],
            "skills_missing": ['Machine Learning Algorithms', 'Cloud Platform Expertise', 'Advanced Data Analysis', 'DevOps Practices', 'UI/UX Design Principles', 'Cybersecurity Fundamentals', 'Mobile App Development', 'Database Optimization'],
            "experience_summary": 'The candidate has demonstrated professional experience in relevant technical roles. Their background includes working with modern technologies and methodologies. They have contributed to projects with measurable outcomes and success metrics.',
            "education_summary": 'The candidate possesses educational qualifications that provide a strong foundation for professional work. Their academic background includes relevant coursework and projects. Additional training complements their formal education.',
            "overall_score": round(base_score, 1),
            "score_breakdown": {
                "skills_match": round(random.uniform(18.0, 25.0), 1),
                "experience_relevance": round(random.uniform(15.0, 22.0), 1),
                "role_alignment": round(random.uniform(12.0, 18.0), 1),
                "projects_impact": round(random.uniform(8.0, 14.0), 1),
                "resume_quality": round(random.uniform(6.0, 9.0), 1)
            },
            "recommendation": "Needs Full Analysis",
            "key_strengths": ['Technical proficiency', 'Communication abilities', 'Problem-solving approach', 'Team collaboration'],
            "areas_for_improvement": ['Advanced technical skills needed', 'Cloud platform experience required', 'Data analysis capabilities', 'Project management skills'],
            "ai_provider": "groq",
            "ai_status": "Partial",
            "ai_model": GROQ_MODEL,
            "scoring_method": "Enhanced Fallback"
        }
    else:
        return {
            "candidate_name": candidate_name,
            "skills_matched": ['Basic Programming', 'Communication Skills', 'Problem Solving', 'Teamwork', 'Technical Knowledge', 'Learning Ability', 'Adaptability', 'Work Ethic'],
            "skills_missing": ['Advanced Technical Skills', 'Industry Experience', 'Specialized Knowledge', 'Certifications', 'Project Management', 'Leadership Experience', 'Research Skills', 'Analytical Thinking'],
            "experience_summary": 'Professional experience analysis will be available once the Groq AI service is fully initialized. The candidate appears to have relevant background based on initial file processing.',
            "education_summary": 'Educational background analysis will be available shortly upon service initialization. Academic qualifications assessment is pending full AI processing.',
            "overall_score": round(base_score, 1),
            "score_breakdown": {
                "skills_match": round(random.uniform(12.0, 20.0), 1),
                "experience_relevance": round(random.uniform(10.0, 18.0), 1),
                "role_alignment": round(random.uniform(8.0, 15.0), 1),
                "projects_impact": round(random.uniform(5.0, 12.0), 1),
                "resume_quality": round(random.uniform(4.0, 8.0), 1)
            },
            "recommendation": "Service Warming Up - Please Retry",
            "key_strengths": ['Fast learning capability', 'Strong work ethic', 'Good communication', 'Technical aptitude'],
            "areas_for_improvement": ['Service initialization required', 'Complete analysis pending', 'Detailed assessment needed', 'Full skill evaluation'],
            "ai_provider": "groq",
            "ai_status": "Warming up",
            "ai_model": GROQ_MODEL,
            "scoring_method": "Basic Fallback"
        }

def process_single_resume(args):
    """Process a single resume with intelligent error handling"""
    resume_file, job_description, index, total, batch_id = args
    
    try:
        print(f"📄 Processing resume {index + 1}/{total}: {resume_file.filename}")
        
        if index > 0:
            if index < 3:
                base_delay = 0.5
            elif index < 6:
                base_delay = 1.0
            else:
                base_delay = 1.5
            
            delay = base_delay + random.uniform(0, 0.3)
            print(f"⏳ Adding {delay:.1f}s delay before processing resume {index + 1}...")
            time.sleep(delay)
        
        api_key, key_index = get_available_key(index)
        if not api_key:
            return {
                'filename': resume_file.filename,
                'error': 'No available API key',
                'status': 'failed',
                'index': index
            }
        
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"batch_{batch_id}_{index}{file_ext}")
        
        # Save the file first
        resume_file.save(file_path)
        
        # Store resume for preview
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
        
        key_usage[key_index - 1]['count'] += 1
        key_usage[key_index - 1]['last_used'] = datetime.now()
        
        analysis = analyze_resume_with_ai(
            resume_text, 
            job_description, 
            resume_file.filename, 
            analysis_id,
            api_key,
            key_index
        )
        
        analysis['filename'] = resume_file.filename
        analysis['original_filename'] = resume_file.filename
        
        resume_file.seek(0, 2)
        file_size = resume_file.tell()
        resume_file.seek(0)
        analysis['file_size'] = f"{(file_size / 1024):.1f}KB"
        
        analysis['analysis_id'] = analysis_id
        analysis['processing_order'] = index + 1
        analysis['key_used'] = f"Key {key_index}"
        
        # Add resume preview info
        analysis['resume_stored'] = preview_filename is not None
        analysis['has_pdf_preview'] = False
        
        if preview_filename:
            analysis['resume_preview_filename'] = preview_filename
            analysis['resume_original_filename'] = resume_file.filename
            # Check if PDF preview is available
            if analysis_id in resume_storage and resume_storage[analysis_id].get('has_pdf_preview'):
                analysis['has_pdf_preview'] = True
        
        try:
            if index < MAX_BATCH_SIZE:
                excel_filename = f"individual_{analysis_id}.xlsx"
                excel_path = create_detailed_individual_report(analysis, excel_filename)
                analysis['individual_excel_filename'] = os.path.basename(excel_path)
            else:
                analysis['individual_excel_filename'] = None
        except Exception as e:
            print(f"⚠️ Failed to create individual report: {str(e)}")
            analysis['individual_excel_filename'] = None
        
        # Keep the preview file, remove only the temp upload file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        print(f"✅ Completed: {analysis.get('candidate_name')} - Score: {analysis.get('overall_score')} (Key {key_index})")
        
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
    
    available_keys = sum(1 for key in GROQ_API_KEYS if key)
    
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
            <p>AI-powered resume analysis using Groq API with 3-key parallel processing</p>
            
            <div class="status ''' + ('ready' if warmup_complete else 'warming') + '''">
                <strong>Status:</strong> ''' + warmup_status + '''
            </div>
            
            <div class="key-status">
                <strong>API Keys:</strong>
                ''' + ''.join([f'<span class="key ' + ('key-active' if key else 'key-inactive') + f'">Key {i+1}: ' + ('✅' if key else '❌') + '</span>' for i, key in enumerate(GROQ_API_KEYS)]) + '''
            </div>
            
            <p><strong>Model:</strong> ''' + GROQ_MODEL + '''</p>
            <p><strong>API Provider:</strong> Groq (Parallel Processing)</p>
            <p><strong>Max Batch Size:</strong> ''' + str(MAX_BATCH_SIZE) + ''' resumes</p>
            <p><strong>Processing:</strong> Round-robin with 3 keys, ~10-15s for 10 resumes</p>
            <p><strong>Available Keys:</strong> ''' + str(available_keys) + '''/3</p>
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
                <strong>GET /resume-preview/&lt;analysis_id&gt;</strong> - Get resume preview (PDF)
            </div>
            <div class="endpoint">
                <strong>GET /resume-original/&lt;analysis_id&gt;</strong> - Download original resume file
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
        
        api_key, key_index = get_available_key()
        if not api_key:
            return jsonify({'error': 'No available Groq API key'}), 500
        
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"resume_{timestamp}{file_ext}")
        resume_file.save(file_path)
        
        # Store resume for preview
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
        
        analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id, api_key, key_index)
        
        excel_filename = f"analysis_{analysis_id}.xlsx"
        excel_path = create_detailed_individual_report(analysis, excel_filename)
        
        # Keep the preview file, remove only the temp upload file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['ai_model'] = GROQ_MODEL
        analysis['ai_provider'] = "groq"
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['response_time'] = analysis.get('response_time', 'N/A')
        analysis['analysis_id'] = analysis_id
        analysis['key_used'] = f"Key {key_index}"
        
        # Add resume preview info
        analysis['resume_stored'] = preview_filename is not None
        analysis['has_pdf_preview'] = False
        
        if preview_filename:
            analysis['resume_preview_filename'] = preview_filename
            analysis['resume_original_filename'] = resume_file.filename
            # Check if PDF preview is available
            if analysis_id in resume_storage and resume_storage[analysis_id].get('has_pdf_preview'):
                analysis['has_pdf_preview'] = True
        
        total_time = time.time() - start_time
        print(f"✅ Request completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/analyze-batch', methods=['POST'])
def analyze_resume_batch():
    """Analyze multiple resumes with parallel processing"""
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
        
        available_keys = sum(1 for key in GROQ_API_KEYS if key)
        if available_keys == 0:
            print("❌ No Groq API keys configured")
            return jsonify({'error': 'No Groq API keys configured'}), 500
        
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        
        for i in range(3):
            key_usage[i]['count'] = 0
            key_usage[i]['last_used'] = None
        
        all_analyses = []
        errors = []
        
        print(f"🔄 Processing {len(resume_files)} resumes with {available_keys} keys...")
        print(f"📊 Using round-robin distribution: Key 1→1,4,7,10 | Key 2→2,5,8 | Key 3→3,6,9")
        
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
            
            for i in range(3):
                if key_usage[i]['count'] >= 4:
                    mark_key_cooling(i, 15)
        
        # Sort by score (descending) with decimal precision
        all_analyses.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        for rank, analysis in enumerate(all_analyses, 1):
            analysis['rank'] = rank
        
        batch_excel_path = None
        if all_analyses:
            try:
                print("📊 Creating detailed batch Excel report...")
                excel_filename = f"batch_analysis_{batch_id}.xlsx"
                batch_excel_path = create_detailed_batch_report(all_analyses, job_description, excel_filename)
                print(f"✅ Excel report created: {batch_excel_path}")
            except Exception as e:
                print(f"❌ Failed to create Excel report: {str(e)}")
        
        key_stats = []
        for i in range(3):
            if GROQ_API_KEYS[i]:
                key_stats.append({
                    'key': f'Key {i+1}',
                    'used': key_usage[i]['count'],
                    'status': 'cooling' if key_usage[i]['cooling'] else 'available'
                })
        
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
            'processing_method': 'round_robin_parallel',
            'key_statistics': key_stats,
            'available_keys': available_keys,
            'success_rate': f"{(len(all_analyses) / len(resume_files)) * 100:.1f}%" if resume_files else "0%",
            'performance': f"{len(all_analyses)/total_time:.2f} resumes/second" if total_time > 0 else "N/A",
            'scoring_method': 'Strict 5-Dimension ATS with decimal precision'
        }
        
        print(f"✅ Batch analysis completed in {total_time:.2f}s")
        print(f"📊 Key usage: {key_stats}")
        print("="*50 + "\n")
        
        return jsonify(batch_summary)
        
    except Exception as e:
        print(f"❌ Batch analysis error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/resume-preview/<analysis_id>', methods=['GET'])
def get_resume_preview(analysis_id):
    """Get resume preview as PDF"""
    update_activity()
    
    try:
        print(f"📄 Resume preview request for: {analysis_id}")
        
        # Get resume info from storage
        resume_info = get_resume_preview(analysis_id)
        if not resume_info:
            return jsonify({'error': 'Resume preview not found'}), 404
        
        # Try to use PDF preview if available
        preview_path = resume_info.get('pdf_path') or resume_info['path']
        
        if not os.path.exists(preview_path):
            return jsonify({'error': 'Preview file not found'}), 404
        
        # Determine file type
        file_ext = os.path.splitext(preview_path)[1].lower()
        
        if file_ext == '.pdf':
            return send_file(
                preview_path,
                as_attachment=False,
                download_name=f"resume_preview_{analysis_id}.pdf",
                mimetype='application/pdf'
            )
        else:
            # If not PDF, try to convert or return original
            return send_file(
                preview_path,
                as_attachment=True,
                download_name=resume_info['original_filename'],
                mimetype='application/octet-stream'
            )
            
    except Exception as e:
        print(f"❌ Resume preview error: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to get resume preview: {str(e)}'}), 500

@app.route('/resume-original/<analysis_id>', methods=['GET'])
def get_resume_original(analysis_id):
    """Download original resume file"""
    update_activity()
    
    try:
        print(f"📄 Original resume request for: {analysis_id}")
        
        # Get resume info from storage
        resume_info = get_resume_preview(analysis_id)
        if not resume_info:
            return jsonify({'error': 'Resume not found'}), 404
        
        original_path = resume_info['path']
        
        if not os.path.exists(original_path):
            return jsonify({'error': 'Resume file not found'}), 404
        
        return send_file(
            original_path,
            as_attachment=True,
            download_name=resume_info['original_filename']
        )
            
    except Exception as e:
        print(f"❌ Original resume download error: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to download resume: {str(e)}'}), 500

def create_detailed_individual_report(analysis_data, filename="resume_analysis_report.xlsx"):
    """Create a detailed Excel report with all analysis data for individual candidate"""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Resume Analysis"
        
        # Styles
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        title_font = Font(bold=True, size=14, color="FFFFFF")
        subheader_fill = PatternFill(start_color="8EA9DB", end_color="8EA9DB", fill_type="solid")
        subheader_font = Font(bold=True, color="FFFFFF", size=10)
        decimal_font = Font(bold=True, color="000000", size=11)
        
        # Set column widths
        column_widths = {
            'A': 25, 'B': 35, 'C': 25, 'D': 25, 'E': 25, 'F': 25
        }
        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width
        
        row = 1
        
        # Title
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = "COMPREHENSIVE RESUME ANALYSIS REPORT (Groq AI - Strict Scoring)"
        cell.font = title_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        row += 2
        
        # Basic Information
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = "CANDIDATE INFORMATION"
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        info_fields = [
            ("Candidate Name", analysis_data.get('candidate_name', 'N/A')),
            ("Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("AI Model", analysis_data.get('ai_model', 'Groq AI')),
            ("AI Provider", analysis_data.get('ai_provider', 'Groq')),
            ("Scoring Method", analysis_data.get('scoring_method', 'Strict 5-Dimension ATS')),
            ("API Key Used", analysis_data.get('key_used', 'N/A')),
            ("Response Time", analysis_data.get('response_time', 'N/A')),
            ("Original Filename", analysis_data.get('filename', 'N/A')),
            ("File Size", analysis_data.get('file_size', 'N/A')),
            ("Analysis ID", analysis_data.get('analysis_id', 'N/A')),
            ("AI Status", analysis_data.get('ai_status', 'N/A')),
            ("Resume Stored", "Yes" if analysis_data.get('resume_stored') else "No"),
            ("PDF Preview Available", "Yes" if analysis_data.get('has_pdf_preview') else "No"),
        ]
        
        for label, value in info_fields:
            ws[f'A{row}'] = label
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'B{row}'] = value
            row += 1
        
        row += 1
        
        # Score and Recommendation with Breakdown
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = "SCORE BREAKDOWN & RECOMMENDATION"
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        # Overall Score
        ws[f'A{row}'] = "Overall ATS Score"
        ws[f'A{row}'].font = Font(bold=True, size=12)
        ws[f'B{row}'] = f"{analysis_data.get('overall_score', 0):.1f}/100"
        ws[f'B{row}'].font = decimal_font
        row += 1
        
        # Score Breakdown
        if 'score_breakdown' in analysis_data:
            ws[f'A{row}'] = "Score Breakdown:"
            ws[f'A{row}'].font = Font(bold=True)
            row += 1
            
            breakdown = analysis_data['score_breakdown']
            breakdown_items = [
                ("1. Skills Match (30 points)", breakdown.get('skills_match', 0)),
                ("2. Experience Relevance (25 points)", breakdown.get('experience_relevance', 0)),
                ("3. Role Alignment (20 points)", breakdown.get('role_alignment', 0)),
                ("4. Projects Impact (15 points)", breakdown.get('projects_impact', 0)),
                ("5. Resume Quality (10 points)", breakdown.get('resume_quality', 0))
            ]
            
            for label, score in breakdown_items:
                ws[f'A{row}'] = label
                ws[f'B{row}'] = f"{score:.1f}"
                ws[f'B{row}'].font = decimal_font
                row += 1
        
        row += 1
        
        # Recommendation
        ws[f'A{row}'] = "Recommendation"
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = analysis_data.get('recommendation', 'N/A')
        row += 1
        
        ws[f'A{row}'] = "Score Grade"
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = get_score_grade_text(analysis_data.get('overall_score', 0))
        row += 2
        
        # Skills Matched (5-8 skills)
        skills_matched = analysis_data.get('skills_matched', [])
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = f"SKILLS MATCHED ({len(skills_matched)} skills)"
        cell.font = header_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        if skills_matched:
            for i, skill in enumerate(skills_matched, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'A{row}'].font = Font(bold=True)
                ws[f'B{row}'] = skill
                row += 1
        else:
            ws[f'A{row}'] = "No matched skills found"
            row += 1
        
        row += 1
        
        # Skills Missing (5-8 skills)
        skills_missing = analysis_data.get('skills_missing', [])
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = f"SKILLS MISSING ({len(skills_missing)} skills)"
        cell.font = header_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        if skills_missing:
            for i, skill in enumerate(skills_missing, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'A{row}'].font = Font(bold=True)
                ws[f'B{row}'] = skill
                row += 1
        else:
            ws[f'A{row}'] = "All required skills are present!"
            row += 1
        
        row += 1
        
        # Experience Summary (Concise 3-5 sentences)
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = "EXPERIENCE SUMMARY"
        cell.font = header_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        experience_text = analysis_data.get('experience_summary', 'No experience summary available.')
        cell.value = experience_text
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[row].height = 80
        row += 2
        
        # Education Summary (Concise 3-5 sentences)
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = "EDUCATION SUMMARY"
        cell.font = header_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        education_text = analysis_data.get('education_summary', 'No education summary available.')
        cell.value = education_text
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[row].height = 80
        row += 2
        
        # Key Strengths (4 items)
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = "KEY STRENGTHS (4 items)"
        cell.font = header_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        key_strengths = analysis_data.get('key_strengths', [])
        if key_strengths:
            for i, strength in enumerate(key_strengths, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'A{row}'].font = Font(bold=True)
                ws[f'B{row}'] = strength
                row += 1
        else:
            ws[f'A{row}'] = "No strengths identified"
            row += 1
        
        row += 1
        
        # Areas for Improvement (4 items)
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = "AREAS FOR IMPROVEMENT (4 items)"
        cell.font = header_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        areas_for_improvement = analysis_data.get('areas_for_improvement', [])
        if areas_for_improvement:
            for i, area in enumerate(areas_for_improvement, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'A{row}'].font = Font(bold=True)
                ws[f'B{row}'] = area
                row += 1
        else:
            ws[f'A{row}'] = "No areas for improvement identified"
            row += 1
        
        # Add borders to all cells with data
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=6):
            for cell in row:
                if cell.value:
                    cell.border = thin_border
        
        # Save the file
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📄 Detailed individual Excel report saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error creating detailed Excel report: {str(e)}")
        filepath = os.path.join(REPORTS_FOLDER, f"detailed_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb = Workbook()
        ws = wb.active
        ws['A1'] = "Detailed Resume Analysis Report (Groq)"
        ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws['A3'] = f"Candidate: {analysis_data.get('candidate_name', 'Unknown')}"
        wb.save(filepath)
        return filepath

def create_detailed_batch_report(analyses, job_description, filename="batch_resume_analysis.xlsx"):
    """Create a comprehensive batch Excel report with multiple sheets"""
    try:
        wb = Workbook()
        
        # Summary Sheet
        ws_summary = wb.active
        ws_summary.title = "Batch Summary"
        
        # Header styles
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        title_font = Font(bold=True, size=16, color="FFFFFF")
        decimal_font = Font(bold=True, color="000000", size=11)
        
        # Title
        ws_summary.merge_cells('A1:M1')
        title_cell = ws_summary['A1']
        title_cell.value = "COMPREHENSIVE BATCH RESUME ANALYSIS REPORT (Groq Parallel - Strict Scoring)"
        title_cell.font = title_font
        title_cell.fill = header_fill
        title_cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Summary Information
        ws_summary['A3'] = "Analysis Date"
        ws_summary['B3'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws_summary['A4'] = "Total Resumes"
        ws_summary['B4'] = len(analyses)
        ws_summary['A5'] = "Successfully Analyzed"
        ws_summary['B5'] = len(analyses)
        ws_summary['A6'] = "AI Model"
        ws_summary['B6'] = "Groq " + GROQ_MODEL
        ws_summary['A7'] = "Processing Method"
        ws_summary['B7'] = "Round-robin Parallel with 3 keys"
        ws_summary['A8'] = "Scoring Method"
        ws_summary['B8'] = "Strict 5-Dimension ATS with decimal precision"
        ws_summary['A9'] = "Job Description Length"
        ws_summary['B9'] = f"{len(job_description)} characters"
        ws_summary['A10'] = "Skills Analysis"
        ws_summary['B10'] = f"5-8 skills per candidate"
        
        # Batch Statistics
        ws_summary.merge_cells('A12:M12')
        summary_header = ws_summary['A12']
        summary_header.value = "BATCH STATISTICS (Decimal Scoring)"
        summary_header.font = header_font
        summary_header.fill = header_fill
        summary_header.alignment = Alignment(horizontal='center')
        
        # Calculate statistics with decimal precision
        if analyses:
            scores = [a.get('overall_score', 0) for a in analyses]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            std_dev = (sum((s - avg_score) ** 2 for s in scores) / len(scores)) ** 0.5 if len(scores) > 1 else 0
            
            stats_data = [
                ("Average Score", f"{avg_score:.1f}/100"),
                ("Highest Score", f"{max_score:.1f}/100"),
                ("Lowest Score", f"{min_score:.1f}/100"),
                ("Score Range", f"{(max_score - min_score):.1f}"),
                ("Standard Deviation", f"{std_dev:.1f}"),
                ("Recommended Candidates", sum(1 for a in analyses if a.get('overall_score', 0) >= 70)),
                ("Needs Improvement", sum(1 for a in analyses if a.get('overall_score', 0) < 70)),
                ("Total Skills Analyzed", sum(len(a.get('skills_matched', [])) + len(a.get('skills_missing', [])) for a in analyses)),
            ]
            
            row = 13
            for i in range(0, len(stats_data), 2):
                if i < len(stats_data):
                    ws_summary[f'A{row}'] = stats_data[i][0]
                    ws_summary[f'A{row}'].font = Font(bold=True)
                    ws_summary[f'B{row}'] = stats_data[i][1]
                    if 'Score' in stats_data[i][0]:
                        ws_summary[f'B{row}'].font = decimal_font
                if i + 1 < len(stats_data):
                    ws_summary[f'D{row}'] = stats_data[i+1][0]
                    ws_summary[f'D{row}'].font = Font(bold=True)
                    ws_summary[f'E{row}'] = stats_data[i+1][1]
                    if 'Score' in stats_data[i+1][0]:
                        ws_summary[f'E{row}'].font = decimal_font
                row += 1
        
        # Candidates Overview Table with Decimal Scores
        row = 22
        headers = ["Rank", "Candidate Name", "ATS Score", "Skills Match", "Experience", "Role Align", 
                   "Projects", "Resume Quality", "Recommendation", "Key Used"]
        
        for col, header in enumerate(headers, start=1):
            cell = ws_summary.cell(row=row, column=col)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
        
        row += 1
        for analysis in analyses:
            ws_summary.cell(row=row, column=1, value=analysis.get('rank', '-'))
            ws_summary.cell(row=row, column=2, value=analysis.get('candidate_name', 'Unknown'))
            
            # Overall score with decimal
            ws_summary.cell(row=row, column=3, value=float(analysis.get('overall_score', 0)))
            ws_summary.cell(row=row, column=3).number_format = '0.0'
            
            # Score breakdown
            breakdown = analysis.get('score_breakdown', {})
            ws_summary.cell(row=row, column=4, value=float(breakdown.get('skills_match', 0)))
            ws_summary.cell(row=row, column=4).number_format = '0.0'
            
            ws_summary.cell(row=row, column=5, value=float(breakdown.get('experience_relevance', 0)))
            ws_summary.cell(row=row, column=5).number_format = '0.0'
            
            ws_summary.cell(row=row, column=6, value=float(breakdown.get('role_alignment', 0)))
            ws_summary.cell(row=row, column=6).number_format = '0.0'
            
            ws_summary.cell(row=row, column=7, value=float(breakdown.get('projects_impact', 0)))
            ws_summary.cell(row=row, column=7).number_format = '0.0'
            
            ws_summary.cell(row=row, column=8, value=float(breakdown.get('resume_quality', 0)))
            ws_summary.cell(row=row, column=8).number_format = '0.0'
            
            ws_summary.cell(row=row, column=9, value=analysis.get('recommendation', 'N/A'))
            ws_summary.cell(row=row, column=10, value=analysis.get('key_used', 'N/A'))
            
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
        
        # Create detailed sheet for each candidate
        for idx, analysis in enumerate(analyses):
            if idx < 10:  # Limit to 10 sheets max
                ws_candidate = wb.create_sheet(title=f"Candidate_{idx+1}")
                populate_candidate_sheet(ws_candidate, analysis, idx+1)
        
        # Create Skills Matrix Sheet
        ws_skills = wb.create_sheet(title="Skills Matrix")
        populate_skills_matrix_sheet(ws_skills, analyses)
        
        # Create Score Distribution Sheet
        ws_scores = wb.create_sheet(title="Score Distribution")
        populate_score_distribution_sheet(ws_scores, analyses)
        
        # Save the file
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📊 Detailed batch Excel report saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error creating detailed batch Excel report: {str(e)}")
        filepath = os.path.join(REPORTS_FOLDER, f"batch_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb = Workbook()
        ws = wb.active
        ws['A1'] = "Batch Analysis Report (Groq)"
        ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws['A3'] = f"Total Candidates: {len(analyses)}"
        wb.save(filepath)
        return filepath

def populate_candidate_sheet(ws, analysis, candidate_num):
    """Populate a detailed sheet for each candidate"""
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    subheader_fill = PatternFill(start_color="8EA9DB", end_color="8EA9DB", fill_type="solid")
    decimal_font = Font(bold=True, color="000000", size=11)
    
    # Title
    ws.merge_cells('A1:G1')
    title_cell = ws['A1']
    title_cell.value = f"CANDIDATE #{candidate_num}: {analysis.get('candidate_name', 'Unknown')} - Strict ATS Scoring"
    title_cell.font = Font(bold=True, size=14, color="FFFFFF")
    title_cell.fill = header_fill
    title_cell.alignment = Alignment(horizontal='center')
    
    row = 3
    
    # Basic Info
    info_data = [
        ("Rank", analysis.get('rank', 'N/A')),
        ("Overall Score", f"{analysis.get('overall_score', 0):.1f}/100"),
        ("Recommendation", analysis.get('recommendation', 'N/A')),
        ("Key Used", analysis.get('key_used', 'N/A')),
        ("Scoring Method", analysis.get('scoring_method', 'Strict 5-Dimension ATS')),
        ("Filename", analysis.get('filename', 'N/A')),
        ("File Size", analysis.get('file_size', 'N/A')),
        ("Analysis ID", analysis.get('analysis_id', 'N/A')),
        ("Resume Stored", "Yes" if analysis.get('resume_stored') else "No"),
        ("PDF Preview", "Available" if analysis.get('has_pdf_preview') else "Not available"),
    ]
    
    for label, value in info_data:
        ws[f'A{row}'] = label
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = value
        if 'Score' in label:
            ws[f'B{row}'].font = decimal_font
        row += 1
    
    row += 1
    
    # Score Breakdown
    if 'score_breakdown' in analysis:
        ws.merge_cells(f'A{row}:G{row}')
        ws[f'A{row}'].value = "SCORE BREAKDOWN (5 Dimensions)"
        ws[f'A{row}'].font = header_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'A{row}'].alignment = Alignment(horizontal='center')
        row += 1
        
        breakdown = analysis['score_breakdown']
        breakdown_items = [
            ("1. Skills Match (30 points)", breakdown.get('skills_match', 0)),
            ("2. Experience Relevance (25 points)", breakdown.get('experience_relevance', 0)),
            ("3. Role Alignment (20 points)", breakdown.get('role_alignment', 0)),
            ("4. Projects Impact (15 points)", breakdown.get('projects_impact', 0)),
            ("5. Resume Quality (10 points)", breakdown.get('resume_quality', 0))
        ]
        
        for label, score in breakdown_items:
            ws[f'A{row}'] = label
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'B{row}'] = f"{score:.1f}"
            ws[f'B{row}'].font = decimal_font
            row += 1
        
        row += 1
    
    # Skills Matched (5-8 skills)
    skills_matched = analysis.get('skills_matched', [])
    ws.merge_cells(f'A{row}:G{row}')
    ws[f'A{row}'].value = f"SKILLS MATCHED ({len(skills_matched)} skills)"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    for i, skill in enumerate(skills_matched, 1):
        ws[f'A{row}'] = f"{i}."
        ws[f'B{row}'] = skill
        row += 1
    
    row += 1
    
    # Skills Missing (5-8 skills)
    skills_missing = analysis.get('skills_missing', [])
    ws.merge_cells(f'A{row}:G{row}')
    ws[f'A{row}'].value = f"SKILLS MISSING ({len(skills_missing)} skills)"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    for i, skill in enumerate(skills_missing, 1):
        ws[f'A{row}'] = f"{i}."
        ws[f'B{row}'] = skill
        row += 1
    
    row += 1
    
    # Experience Summary
    ws.merge_cells(f'A{row}:G{row}')
    ws[f'A{row}'].value = "EXPERIENCE SUMMARY"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    ws.merge_cells(f'A{row}:G{row}')
    experience = analysis.get('experience_summary', 'No experience summary available.')
    ws[f'A{row}'].value = experience
    ws[f'A{row}'].alignment = Alignment(wrap_text=True, vertical='top')
    ws.row_dimensions[row].height = 80
    row += 2
    
    # Education Summary
    ws.merge_cells(f'A{row}:G{row}')
    ws[f'A{row}'].value = "EDUCATION SUMMARY"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    ws.merge_cells(f'A{row}:G{row}')
    education = analysis.get('education_summary', 'No education summary available.')
    ws[f'A{row}'].value = education
    ws[f'A{row}'].alignment = Alignment(wrap_text=True, vertical='top')
    ws.row_dimensions[row].height = 80
    
    # Set column widths
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 60

def populate_skills_matrix_sheet(ws, analyses):
    """Populate skills matrix sheet"""
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    
    # Title
    ws.merge_cells('A1:D1')
    title_cell = ws['A1']
    title_cell.value = "SKILLS MATRIX ACROSS ALL CANDIDATES"
    title_cell.font = Font(bold=True, size=14, color="FFFFFF")
    title_cell.fill = header_fill
    title_cell.alignment = Alignment(horizontal='center')
    
    row = 3
    ws['A3'] = "Candidate Name"
    ws['B3'] = "ATS Score"
    ws['C3'] = "Skills Matched (5-8 skills)"
    ws['D3'] = "Skills Missing (5-8 skills)"
    
    for cell in ['A3', 'B3', 'C3', 'D3']:
        ws[cell].font = header_font
        ws[cell].fill = header_fill
    
    row = 4
    for analysis in analyses:
        ws[f'A{row}'] = analysis.get('candidate_name', 'Unknown')
        
        # Score with decimal
        ws[f'B{row}'] = float(analysis.get('overall_score', 0))
        ws[f'B{row}'].number_format = '0.0'
        
        matched = analysis.get('skills_matched', [])
        ws[f'C{row}'] = ", ".join(matched[:8]) if matched else "N/A"
        
        missing = analysis.get('skills_missing', [])
        ws[f'D{row}'] = ", ".join(missing[:8]) if missing else "All matched"
        
        row += 1
    
    # Set column widths
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 60
    ws.column_dimensions['D'].width = 60

def populate_score_distribution_sheet(ws, analyses):
    """Populate score distribution sheet"""
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    decimal_font = Font(bold=True, color="000000", size=11)
    
    # Title
    ws.merge_cells('A1:F1')
    title_cell = ws['A1']
    title_cell.value = "SCORE DISTRIBUTION ANALYSIS (Decimal Precision)"
    title_cell.font = Font(bold=True, size=14, color="FFFFFF")
    title_cell.fill = header_fill
    title_cell.alignment = Alignment(horizontal='center')
    
    row = 3
    
    # Score ranges
    ranges = [
        ("90-100", "Excellent"),
        ("80-89", "Great"),
        ("70-79", "Good"),
        ("60-69", "Fair"),
        ("50-59", "Needs Improvement"),
        ("0-49", "Poor")
    ]
    
    # Calculate distribution
    scores = [a.get('overall_score', 0) for a in analyses]
    
    for range_label, description in ranges:
        low, high = map(int, range_label.split('-'))
        count = sum(1 for score in scores if low <= score <= high)
        percentage = (count / len(scores) * 100) if scores else 0
        
        ws[f'A{row}'] = range_label
        ws[f'B{row}'] = description
        ws[f'C{row}'] = count
        ws[f'D{row}'] = f"{percentage:.1f}%"
        ws[f'D{row}'].font = decimal_font
        row += 1
    
    row += 2
    
    # Individual score details
    ws.merge_cells(f'A{row}:F{row}')
    ws[f'A{row}'].value = "INDIVIDUAL CANDIDATE SCORES"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = header_fill
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    headers = ["Rank", "Candidate", "Overall", "Skills", "Experience", "Role", "Projects", "Quality"]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
    
    row += 1
    for analysis in analyses:
        ws.cell(row=row, column=1, value=analysis.get('rank', '-'))
        ws.cell(row=row, column=2, value=analysis.get('candidate_name', 'Unknown'))
        
        # Overall score
        ws.cell(row=row, column=3, value=float(analysis.get('overall_score', 0)))
        ws.cell(row=row, column=3).number_format = '0.0'
        
        # Breakdown scores
        breakdown = analysis.get('score_breakdown', {})
        ws.cell(row=row, column=4, value=float(breakdown.get('skills_match', 0)))
        ws.cell(row=row, column=4).number_format = '0.0'
        
        ws.cell(row=row, column=5, value=float(breakdown.get('experience_relevance', 0)))
        ws.cell(row=row, column=5).number_format = '0.0'
        
        ws.cell(row=row, column=6, value=float(breakdown.get('role_alignment', 0)))
        ws.cell(row=row, column=6).number_format = '0.0'
        
        ws.cell(row=row, column=7, value=float(breakdown.get('projects_impact', 0)))
        ws.cell(row=row, column=7).number_format = '0.0'
        
        ws.cell(row=row, column=8, value=float(breakdown.get('resume_quality', 0)))
        ws.cell(row=row, column=8).number_format = '0.0'
        
        row += 1
    
    # Set column widths
    for col in range(1, 9):
        ws.column_dimensions[get_column_letter(col)].width = 15

def get_score_grade_text(score):
    """Get text description for score"""
    score = float(score)
    if score >= 90:
        return f"Excellent Match 🎯 ({score:.1f})"
    elif score >= 80:
        return f"Great Match ✨ ({score:.1f})"
    elif score >= 70:
        return f"Good Match 👍 ({score:.1f})"
    elif score >= 60:
        return f"Fair Match 📊 ({score:.1f})"
    else:
        return f"Needs Improvement 📈 ({score:.1f})"

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
    """Force warm-up Groq API"""
    update_activity()
    
    try:
        available_keys = sum(1 for key in GROQ_API_KEYS if key)
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
            'scoring_method': 'Strict 5-Dimension ATS with decimal precision',
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
        available_keys = sum(1 for key in GROQ_API_KEYS if key)
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
                'model': GROQ_MODEL,
                'scoring_method': 'Strict 5-Dimension ATS'
            })
        
        for i, api_key in enumerate(GROQ_API_KEYS):
            if api_key and not key_usage[i]['cooling']:
                try:
                    start_time = time.time()
                    
                    response = call_groq_api(
                        prompt="Say 'ready'",
                        api_key=api_key,
                        max_tokens=10,
                        timeout=15
                    )
                    
                    response_time = time.time() - start_time
                    
                    if isinstance(response, dict) and 'error' in response:
                        continue
                    elif response and 'ready' in str(response).lower():
                        return jsonify({
                            'available': True,
                            'response_time': f"{response_time:.2f}s",
                            'ai_provider': 'groq',
                            'model': GROQ_MODEL,
                            'warmup_complete': warmup_complete,
                            'available_keys': available_keys,
                            'tested_key': f"Key {i+1}",
                            'max_batch_size': MAX_BATCH_SIZE,
                            'processing_method': 'round_robin_parallel',
                            'skills_analysis': '5-8 skills per category',
                            'scoring_method': 'Strict 5-Dimension ATS with decimal precision'
                        })
                except:
                    continue
        
        return jsonify({
            'available': False,
            'reason': 'All keys failed or are cooling',
            'available_keys': available_keys,
            'warmup_complete': warmup_complete
        })
            
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'available': False,
            'reason': error_msg[:100],
            'available_keys': sum(1 for key in GROQ_API_KEYS if key),
            'ai_provider': 'groq',
            'model': GROQ_MODEL,
            'warmup_complete': warmup_complete
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
        'keep_alive_active': True,
        'max_batch_size': MAX_BATCH_SIZE,
        'processing_method': 'round_robin_parallel',
        'skills_analysis': '5-8 skills per category',
        'scoring_method': 'Strict 5-Dimension ATS with decimal precision'
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
            'usage': key_usage[i]['count'],
            'cooling': key_usage[i]['cooling'],
            'last_used': key_usage[i]['last_used'].isoformat() if key_usage[i]['last_used'] else None
        })
    
    available_keys = sum(1 for key in GROQ_API_KEYS if key)
    
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
        'version': '2.5.0',
        'key_status': key_status,
        'available_keys': available_keys,
        'configuration': {
            'max_batch_size': MAX_BATCH_SIZE,
            'max_concurrent_requests': MAX_CONCURRENT_REQUESTS,
            'max_retries': MAX_RETRIES,
            'min_skills_to_show': MIN_SKILLS_TO_SHOW,
            'max_skills_to_show': MAX_SKILLS_TO_SHOW,
            'scoring_method': 'Strict 5-Dimension ATS'
        },
        'scoring_dimensions': {
            'skills_match': '30 points',
            'experience_relevance': '25 points',
            'role_alignment': '20 points',
            'projects_impact': '15 points',
            'resume_quality': '10 points'
        },
        'processing_method': 'round_robin_parallel',
        'performance_target': '10 resumes in 10-15 seconds',
        'skills_analysis': '5-8 skills per category',
        'resume_preview': 'Enabled with PDF conversion (1 hour retention)',
        'pdf_preview_available': any(r.get('has_pdf_preview') for r in resume_storage.values()),
        'decimal_scoring': True,
        'score_precision': '1 decimal place'
    })

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
                    os.remove(filepath)
        print("✅ Cleaned up temporary files")
    except:
        pass

# Periodic cleanup
def periodic_cleanup():
    """Periodically clean up old resume previews"""
    while service_running:
        try:
            time.sleep(300)  # Run every 5 minutes
            cleanup_resume_previews()
        except Exception as e:
            print(f"⚠️ Periodic cleanup error: {str(e)}")

atexit.register(cleanup_on_exit)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting (Groq Parallel)...")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"⚡ AI Provider: Groq (Parallel Processing)")
    print(f"🤖 Model: {GROQ_MODEL}")
    
    available_keys = sum(1 for key in GROQ_API_KEYS if key)
    print(f"🔑 API Keys: {available_keys}/3 configured")
    
    for i, key in enumerate(GROQ_API_KEYS):
        status = "✅ Configured" if key else "❌ Not configured"
        print(f"  Key {i+1}: {status}")
    
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📁 Reports folder: {REPORTS_FOLDER}")
    print(f"📁 Resume Previews folder: {RESUME_PREVIEW_FOLDER}")
    print(f"✅ Round-robin Parallel Processing: Enabled")
    print(f"✅ Max Batch Size: {MAX_BATCH_SIZE} resumes")
    print(f"✅ Skills Analysis: {MIN_SKILLS_TO_SHOW}-{MAX_SKILLS_TO_SHOW} skills per category")
    print(f"✅ STRICT SCORING: 5-Dimension ATS with decimal precision")
    print(f"✅ Score Dimensions:")
    print(f"   • Skills Match: 30 points")
    print(f"   • Experience Relevance: 25 points")
    print(f"   • Role Alignment: 20 points")
    print(f"   • Projects Impact: 15 points")
    print(f"   • Resume Quality: 10 points")
    print(f"✅ Decimal Precision: Scores like 78.3, 81.7, 65.9 (not 75, 80, 65)")
    print(f"✅ Concise Summaries: 3-5 sentences each")
    print(f"✅ Key Strengths/Improvements: 4 items each")
    print(f"✅ Resume Preview: Enabled with PDF conversion")
    print(f"✅ Performance: ~10 resumes in 10-15 seconds")
    print("="*50 + "\n")
    
    # Check for required dependencies
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        print("✅ PDF generation library available")
    except ImportError:
        print("⚠️  Warning: reportlab not installed. Install with: pip install reportlab")
        print("   PDF previews for non-PDF files will be limited")
    
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
