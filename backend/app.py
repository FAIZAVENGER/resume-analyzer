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
from openpyxl.cell.cell import MergedCell
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
        print(f"⚠️ PDF conversion failed: {str(e)}")
        return False

def convert_txt_to_pdf(txt_path, pdf_path):
    """Convert TXT to PDF"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            text_content = f.read()
        
        # Simple text wrapping
        y = height - inch
        for line in text_content.split('\n'):
            if y < inch:
                c.showPage()
                y = height - inch
            c.drawString(inch, y, line[:100])  # Limit line length
            y -= 15
        
        c.save()
        return True
    except Exception as e:
        print(f"⚠️ TXT to PDF conversion failed: {str(e)}")
        return False

def extract_text_and_create_pdf(doc_path, pdf_path):
    """Fallback: Extract text from DOC and create a simple PDF"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        # Extract text from DOCX
        doc = Document(doc_path)
        text_content = '\n'.join([para.text for para in doc.paragraphs])
        
        # Create PDF
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        
        y = height - 50
        for line in text_content.split('\n')[:50]:  # Limit to first 50 lines
            if y < 50:
                break
            c.drawString(50, y, line[:100])
            y -= 15
        
        c.save()
        return True
    except Exception as e:
        print(f"⚠️ Fallback PDF creation failed: {str(e)}")
        return False

def cleanup_resume_previews(max_age_hours=24):
    """Clean up old resume preview files"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Clean from storage dict
        to_remove = []
        for analysis_id, info in resume_storage.items():
            stored_time = datetime.fromisoformat(info['stored_at'])
            if stored_time < cutoff_time:
                to_remove.append(analysis_id)
                # Delete files
                try:
                    if os.path.exists(info['path']):
                        os.remove(info['path'])
                    if info.get('pdf_path') and os.path.exists(info['pdf_path']):
                        os.remove(info['pdf_path'])
                except:
                    pass
        
        for analysis_id in to_remove:
            del resume_storage[analysis_id]
        
        if to_remove:
            print(f"🧹 Cleaned up {len(to_remove)} old resume previews")
            
    except Exception as e:
        print(f"⚠️ Cleanup error: {str(e)}")

def extract_text_from_pdf(file):
    """Extract text from PDF using PyPDF2"""
    try:
        pdf_reader = PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"❌ Error extracting text from PDF: {str(e)}")
        return ""

def extract_text_from_docx(file):
    """Extract text from DOCX file"""
    try:
        doc = Document(file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        print(f"❌ Error extracting text from DOCX: {str(e)}")
        return ""

def extract_text_from_txt(file):
    """Extract text from TXT file"""
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                file.seek(0)
                content = file.read()
                if isinstance(content, bytes):
                    text = content.decode(encoding)
                else:
                    text = content
                return text.strip()
            except (UnicodeDecodeError, AttributeError):
                continue
        return ""
    except Exception as e:
        print(f"❌ Error extracting text from TXT: {str(e)}")
        return ""

def call_groq_api(prompt, api_key, max_tokens=2000, timeout=45):
    """Call Groq API with timeout and error handling"""
    try:
        if not api_key:
            return {"error": "No API key provided"}
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": GROQ_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert ATS (Applicant Tracking System) resume analyzer. Provide detailed, accurate, and helpful analysis."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": max_tokens,
            "top_p": 0.9
        }
        
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=data,
            timeout=timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        elif response.status_code == 429:
            return {"error": "rate_limit", "message": "Rate limit exceeded"}
        elif response.status_code == 401:
            return {"error": "auth", "message": "Invalid API key"}
        else:
            return {"error": "api_error", "message": f"API error: {response.status_code}"}
            
    except requests.exceptions.Timeout:
        return {"error": "timeout", "message": "Request timed out"}
    except requests.exceptions.ConnectionError:
        return {"error": "connection", "message": "Connection failed"}
    except Exception as e:
        return {"error": "unknown", "message": str(e)}

def parse_analysis_response(response_text):
    """Parse the AI response with enhanced error handling and fallbacks"""
    try:
        # Clean the response
        cleaned_response = response_text.strip()
        
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            parsed = json.loads(json_str)
        else:
            # If no JSON found, try to parse the entire response
            parsed = json.loads(cleaned_response)
        
        # Validate and set defaults for required fields
        result = {
            'overall_score': int(parsed.get('overall_score', 0)),
            'candidate_name': str(parsed.get('candidate_name', 'Unknown Candidate')),
            'recommendation': str(parsed.get('recommendation', 'Review Required')),
            'skills_matched': parsed.get('skills_matched', [])[:MAX_SKILLS_TO_SHOW],
            'skills_missing': parsed.get('skills_missing', [])[:MAX_SKILLS_TO_SHOW],
            'experience_summary': str(parsed.get('experience_summary', 'No experience summary available.')),
            'education_summary': str(parsed.get('education_summary', 'No education summary available.')),
            'key_strengths': parsed.get('key_strengths', [])[:3],
            'areas_for_improvement': parsed.get('areas_for_improvement', [])[:3]
        }
        
        # Ensure we have at least minimum skills
        if len(result['skills_matched']) < MIN_SKILLS_TO_SHOW:
            result['skills_matched'].extend(['N/A'] * (MIN_SKILLS_TO_SHOW - len(result['skills_matched'])))
        if len(result['skills_missing']) < MIN_SKILLS_TO_SHOW:
            result['skills_missing'].extend(['N/A'] * (MIN_SKILLS_TO_SHOW - len(result['skills_missing'])))
        
        # Ensure we have exactly 3 strengths and improvements
        if len(result['key_strengths']) < 3:
            result['key_strengths'].extend(['N/A'] * (3 - len(result['key_strengths'])))
        if len(result['areas_for_improvement']) < 3:
            result['areas_for_improvement'].extend(['N/A'] * (3 - len(result['areas_for_improvement'])))
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parsing error: {str(e)}")
        print(f"Response text: {response_text[:200]}...")
        return create_fallback_analysis(response_text)
    except Exception as e:
        print(f"⚠️ Parsing error: {str(e)}")
        return create_fallback_analysis(response_text)

def create_fallback_analysis(response_text=""):
    """Create a basic fallback analysis when parsing fails"""
    return {
        'overall_score': 50,
        'candidate_name': 'Unknown Candidate',
        'recommendation': 'Review Required - Analysis Incomplete',
        'skills_matched': ['Analysis', 'In Progress'] + ['N/A'] * (MIN_SKILLS_TO_SHOW - 2),
        'skills_missing': ['Complete', 'Review Needed'] + ['N/A'] * (MIN_SKILLS_TO_SHOW - 2),
        'experience_summary': 'Unable to complete full analysis. Please review manually.',
        'education_summary': 'Unable to complete full analysis. Please review manually.',
        'key_strengths': ['Pending detailed review', 'N/A', 'N/A'],
        'areas_for_improvement': ['Requires manual review', 'N/A', 'N/A']
    }

def analyze_resume_with_retry(resume_text, job_description, filename="", resume_index=0):
    """Analyze resume with retry logic and consistent scoring"""
    # Check cache first
    resume_hash = calculate_resume_hash(resume_text, job_description)
    cached_result = get_cached_score(resume_hash)
    
    if cached_result:
        print(f"✅ Using cached score for resume")
        return cached_result
    
    for attempt in range(MAX_RETRIES):
        try:
            # Get API key using round-robin
            api_key, key_num = get_available_key(resume_index)
            
            if not api_key:
                print(f"❌ No API keys available")
                return create_fallback_analysis()
            
            print(f"🔑 Using API Key {key_num} for resume {resume_index + 1} (Attempt {attempt + 1})")
            
            # Create comprehensive prompt
            prompt = f"""Analyze this resume against the job description and provide a detailed JSON response.

JOB DESCRIPTION:
{job_description}

RESUME:
{resume_text[:4000]}

IMPORTANT INSTRUCTIONS:
1. Provide EXACTLY {MIN_SKILLS_TO_SHOW}-{MAX_SKILLS_TO_SHOW} skills for both matched and missing (no more, no less)
2. For Experience Summary and Education Summary: Write COMPLETE, DETAILED 4-5 sentence paragraphs - DO NOT TRUNCATE
3. Provide EXACTLY 3 key strengths and 3 areas for improvement
4. Extract the candidate's name from the resume
5. Be specific and detailed in all summaries

Return ONLY valid JSON in this exact format (no markdown, no extra text):
{{
  "overall_score": <number 0-100>,
  "candidate_name": "<extract from resume>",
  "recommendation": "<Strong Match / Good Match / Potential Match / Not Recommended>",
  "skills_matched": [<{MIN_SKILLS_TO_SHOW}-{MAX_SKILLS_TO_SHOW} specific matching skills>],
  "skills_missing": [<{MIN_SKILLS_TO_SHOW}-{MAX_SKILLS_TO_SHOW} specific missing skills>],
  "experience_summary": "<COMPLETE 4-5 sentence detailed summary - DO NOT TRUNCATE>",
  "education_summary": "<COMPLETE 4-5 sentence detailed summary - DO NOT TRUNCATE>",
  "key_strengths": [<exactly 3 detailed strengths>],
  "areas_for_improvement": [<exactly 3 specific improvements>]
}}"""
            
            response = call_groq_api(prompt, api_key, max_tokens=2000, timeout=45)
            
            if isinstance(response, dict) and 'error' in response:
                if response.get('error') == 'rate_limit':
                    key_index = key_num - 1
                    mark_key_cooling(key_index, duration=30)
                    print(f"⚠️ Key {key_num} hit rate limit, cooling down...")
                    time.sleep(2)
                    continue
                else:
                    print(f"❌ API Error: {response.get('message', 'Unknown error')}")
                    time.sleep(RETRY_DELAY_BASE * (attempt + 1))
                    continue
            
            # Parse the response
            analysis = parse_analysis_response(response)
            analysis['filename'] = filename
            analysis['analysis_id'] = f"resume_{resume_index}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            analysis['key_used'] = f"Key {key_num}"
            
            # Cache the result
            set_cached_score(resume_hash, analysis)
            
            # Update key usage
            key_usage[key_num - 1]['count'] += 1
            key_usage[key_num - 1]['last_used'] = datetime.now()
            
            return analysis
            
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_BASE * (attempt + 1))
            else:
                print(f"❌ All retries exhausted for resume {resume_index + 1}")
    
    return create_fallback_analysis()

def warmup_groq_service():
    """Warm up Groq API on startup"""
    global warmup_complete, warmup_status
    
    try:
        print("🔥 Warming up Groq service...")
        
        test_prompt = "Respond with just 'ready' if you can process this message."
        
        warmed_keys = 0
        for i, api_key in enumerate(GROQ_API_KEYS):
            if api_key:
                try:
                    response = call_groq_api(test_prompt, api_key, max_tokens=10, timeout=15)
                    if response and 'ready' in str(response).lower():
                        warmed_keys += 1
                        print(f"✅ Key {i+1} warmed up successfully")
                    else:
                        print(f"⚠️ Key {i+1} warmup uncertain")
                except Exception as e:
                    print(f"❌ Key {i+1} warmup failed: {str(e)}")
        
        warmup_complete = True
        print(f"✅ Groq warmup complete! {warmed_keys}/{len([k for k in GROQ_API_KEYS if k])} keys ready")
        
    except Exception as e:
        print(f"❌ Warmup failed: {str(e)}")
        warmup_complete = True

def keep_service_warm():
    """Keep service warm with periodic pings"""
    while service_running:
        try:
            time.sleep(300)  # Every 5 minutes
            
            if (datetime.now() - last_activity_time).total_seconds() > 600:
                print("🔄 Keeping service warm...")
                api_key, _ = get_available_key()
                if api_key:
                    call_groq_api("ping", api_key, max_tokens=5, timeout=10)
                    
        except Exception as e:
            print(f"⚠️ Keep-warm error: {str(e)}")

def create_individual_excel_report(analysis_data, job_description, filename="individual_resume_analysis.xlsx"):
    """Create an individual Excel report for a single resume"""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Resume Analysis"
        
        # Styling
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        subheader_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        title_font = Font(bold=True, size=16)
        
        # Set column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 50
        ws.column_dimensions['C'].width = 50
        ws.column_dimensions['D'].width = 50
        
        row = 1
        
        # Title
        ws.merge_cells('A1:D1')
        ws['A1'] = "RESUME ANALYSIS REPORT (Groq Parallel Processing)"
        ws['A1'].font = title_font
        ws['A1'].fill = header_fill
        ws['A1'].alignment = Alignment(horizontal='center')
        row += 2
        
        # Basic Information
        basic_info = [
            ("Candidate Name", analysis_data.get('candidate_name', 'Unknown')),
            ("ATS Score", f"{analysis_data.get('overall_score', 0)}/100"),
            ("Recommendation", analysis_data.get('recommendation', 'N/A')),
            ("Original File", analysis_data.get('filename', 'N/A')),
            ("Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("AI Model", "Groq " + GROQ_MODEL),
            ("Key Used", analysis_data.get('key_used', 'N/A'))
        ]
        
        for label, value in basic_info:
            ws[f'A{row}'] = label
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'B{row}'] = value
            row += 1
        
        row += 1
        
        # Job Description (first 500 chars)
        ws[f'A{row}'] = "JOB DESCRIPTION (Preview)"
        ws[f'A{row}'].font = header_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'A{row}'].alignment = Alignment(horizontal='center')
        
        for col in ['B', 'C', 'D']:
            cell = f'{col}{row}'
            ws[cell] = ""
            ws[cell].fill = subheader_fill
        row += 1
        
        job_desc_preview = job_description[:500] + "..." if len(job_description) > 500 else job_description
        ws[f'A{row}'] = job_desc_preview
        ws[f'A{row}'].alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[row].height = 60
        
        for col in ['B', 'C', 'D']:
            ws[f'{col}{row}'] = ""
        
        row += 2
        
        # Skills Matched (5-8 skills)
        skills_matched = analysis_data.get('skills_matched', [])
        ws[f'A{row}'] = f"SKILLS MATCHED ({len(skills_matched)} skills)"
        ws[f'A{row}'].font = header_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'A{row}'].alignment = Alignment(horizontal='center')
        
        for col in ['B', 'C', 'D']:
            cell = f'{col}{row}'
            ws[cell] = ""
            ws[cell].fill = subheader_fill
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
        ws[f'A{row}'] = f"SKILLS MISSING ({len(skills_missing)} skills)"
        ws[f'A{row}'].font = header_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'A{row}'].alignment = Alignment(horizontal='center')
        
        for col in ['B', 'C', 'D']:
            cell = f'{col}{row}'
            ws[cell] = ""
            ws[cell].fill = subheader_fill
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
        
        # Experience Summary (Complete sentences, not truncated)
        ws[f'A{row}'] = "EXPERIENCE SUMMARY (4-5 complete sentences)"
        ws[f'A{row}'].font = header_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'A{row}'].alignment = Alignment(horizontal='center')
        
        for col in ['B', 'C', 'D']:
            cell = f'{col}{row}'
            ws[cell] = ""
            ws[cell].fill = subheader_fill
        row += 1
        
        experience_text = analysis_data.get('experience_summary', 'No experience summary available.')
        ws[f'A{row}'] = experience_text
        ws[f'A{row}'].alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[row].height = 80
        
        for col in ['B', 'C', 'D']:
            ws[f'{col}{row}'] = ""
        
        row += 2
        
        # Education Summary (Complete sentences, not truncated)
        ws[f'A{row}'] = "EDUCATION SUMMARY (4-5 complete sentences)"
        ws[f'A{row}'].font = header_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'A{row}'].alignment = Alignment(horizontal='center')
        
        for col in ['B', 'C', 'D']:
            cell = f'{col}{row}'
            ws[cell] = ""
            ws[cell].fill = subheader_fill
        row += 1
        
        education_text = analysis_data.get('education_summary', 'No education summary available.')
        ws[f'A{row}'] = education_text
        ws[f'A{row}'].alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[row].height = 80
        
        for col in ['B', 'C', 'D']:
            ws[f'{col}{row}'] = ""
        
        row += 2
        
        # Key Strengths (3 items)
        ws[f'A{row}'] = "KEY STRENGTHS (3)"
        ws[f'A{row}'].font = header_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'A{row}'].alignment = Alignment(horizontal='center')
        
        for col in ['B', 'C', 'D']:
            cell = f'{col}{row}'
            ws[cell] = ""
            ws[cell].fill = subheader_fill
        row += 1
        
        key_strengths = analysis_data.get('key_strengths', [])
        if key_strengths:
            for i, strength in enumerate(key_strengths[:3], 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'A{row}'].font = Font(bold=True)
                ws[f'B{row}'] = strength
                row += 1
        else:
            ws[f'A{row}'] = "No strengths identified"
            row += 1
        
        row += 1
        
        # Areas for Improvement (3 items)
        ws[f'A{row}'] = "AREAS FOR IMPROVEMENT (3)"
        ws[f'A{row}'].font = header_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'A{row}'].alignment = Alignment(horizontal='center')
        
        for col in ['B', 'C', 'D']:
            cell = f'{col}{row}'
            ws[cell] = ""
            ws[cell].fill = subheader_fill
        row += 1
        
        areas_for_improvement = analysis_data.get('areas_for_improvement', [])
        if areas_for_improvement:
            for i, area in enumerate(areas_for_improvement[:3], 1):
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
        
        for row_cells in ws.iter_rows(min_row=1, max_row=row-1, min_col=1, max_col=4):
            for cell in row_cells:
                if cell.value is not None:
                    cell.border = thin_border
        
        # Save the file
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📄 Individual Excel report saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error creating individual Excel report: {str(e)}")
        traceback.print_exc()
        filepath = os.path.join(REPORTS_FOLDER, f"individual_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb = Workbook()
        ws = wb.active
        ws['A1'] = "Resume Analysis Report (Groq)"
        ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws['A3'] = f"Candidate: {analysis_data.get('candidate_name', 'Unknown')}"
        ws['A4'] = f"Score: {analysis_data.get('overall_score', 0)}/100"
        wb.save(filepath)
        return filepath

def create_comprehensive_batch_report(analyses, job_description, filename="batch_resume_analysis.xlsx"):
    """Create a comprehensive batch Excel report with Candidate Details and Individual sheets only"""
    try:
        wb = Workbook()
        
        # Remove the default sheet created by Workbook()
        default_sheet = wb.active
        
        # ================== CANDIDATE DETAILS SHEET ==================
        ws_details = wb.create_sheet(title="Candidate Details")
        
        # Styles
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        title_font = Font(bold=True, size=16, color="FFFFFF")
        
        # Title
        ws_details.merge_cells('A1:H1')
        title_cell = ws_details['A1']
        title_cell.value = "CANDIDATE DETAILED ANALYSIS"
        title_cell.font = title_font
        title_cell.fill = header_fill
        title_cell.alignment = Alignment(horizontal='center')
        
        row = 3
        
        # Create separate sections for each candidate
        for analysis in analyses:
            # Candidate Header
            ws_details[f'A{row}'] = f"Candidate #{analysis.get('rank', 'N/A')}: {analysis.get('candidate_name', 'Unknown')}"
            ws_details[f'A{row}'].font = Font(bold=True, size=14, color="4472C4")
            row += 1
            
            # Basic Info
            ws_details[f'A{row}'] = "Score:"
            ws_details[f'A{row}'].font = Font(bold=True)
            ws_details[f'B{row}'] = f"{analysis.get('overall_score', 0)}/100"
            ws_details[f'C{row}'] = "Recommendation:"
            ws_details[f'C{row}'].font = Font(bold=True)
            ws_details[f'D{row}'] = analysis.get('recommendation', 'N/A')
            row += 1
            
            ws_details[f'A{row}'] = "Filename:"
            ws_details[f'A{row}'].font = Font(bold=True)
            ws_details[f'B{row}'] = analysis.get('filename', 'N/A')
            ws_details[f'C{row}'] = "File Size:"
            ws_details[f'C{row}'].font = Font(bold=True)
            ws_details[f'D{row}'] = analysis.get('file_size', 'N/A')
            row += 1
            
            # Experience Summary (complete)
            ws_details[f'A{row}'] = "Experience Summary:"
            ws_details[f'A{row}'].font = Font(bold=True)
            ws_details.merge_cells(f'B{row}:H{row}')
            exp_text = analysis.get('experience_summary', 'No experience summary available.')
            ws_details[f'B{row}'] = exp_text
            ws_details[f'B{row}'].alignment = Alignment(wrap_text=True)
            row += 1
            
            # Education Summary (complete)
            ws_details[f'A{row}'] = "Education Summary:"
            ws_details[f'A{row}'].font = Font(bold=True)
            ws_details.merge_cells(f'B{row}:H{row}')
            edu_text = analysis.get('education_summary', 'No education summary available.')
            ws_details[f'B{row}'] = edu_text
            ws_details[f'B{row}'].alignment = Alignment(wrap_text=True)
            row += 1
            
            # Skills Matched
            ws_details[f'A{row}'] = "Skills Matched:"
            ws_details[f'A{row}'].font = Font(bold=True, color="00FF00")
            skills_matched = analysis.get('skills_matched', [])
            for i, skill in enumerate(skills_matched[:8], start=0):
                col = get_column_letter(2 + i)
                if i < 7:  # Limit to 7 columns
                    ws_details[f'{col}{row}'] = skill
            row += 1
            
            # Skills Missing
            ws_details[f'A{row}'] = "Skills Missing:"
            ws_details[f'A{row}'].font = Font(bold=True, color="FF0000")
            skills_missing = analysis.get('skills_missing', [])
            for i, skill in enumerate(skills_missing[:8], start=0):
                col = get_column_letter(2 + i)
                if i < 7:
                    ws_details[f'{col}{row}'] = skill
            row += 1
            
            # Key Strengths
            ws_details[f'A{row}'] = "Key Strengths:"
            ws_details[f'A{row}'].font = Font(bold=True, color="00AA00")
            strengths = analysis.get('key_strengths', [])
            for i, strength in enumerate(strengths[:3], start=0):
                col = get_column_letter(2 + i * 2)
                if i < 3:
                    ws_details[f'{col}{row}'] = strength
            row += 1
            
            # Areas for Improvement
            ws_details[f'A{row}'] = "Areas for Improvement:"
            ws_details[f'A{row}'].font = Font(bold=True, color="FF6600")
            improvements = analysis.get('areas_for_improvement', [])
            for i, area in enumerate(improvements[:3], start=0):
                col = get_column_letter(2 + i * 2)
                if i < 3:
                    ws_details[f'{col}{row}'] = area
            row += 2
            
            # Add separator line
            ws_details.merge_cells(f'A{row}:H{row}')
            ws_details[f'A{row}'] = "─" * 100
            ws_details[f'A{row}'].font = Font(color="CCCCCC")
            row += 2
        
        # Set column widths for details sheet
        column_widths_details = [20, 25, 20, 25, 25, 25, 25, 25]
        for i, width in enumerate(column_widths_details, start=1):
            ws_details.column_dimensions[get_column_letter(i)].width = width
        
        # ================== INDIVIDUAL CANDIDATE SHEETS ==================
        for analysis in analyses:
            candidate_name = analysis.get('candidate_name', f"Candidate_{analysis.get('rank', 'Unknown')}")
            # Clean sheet name (remove invalid characters)
            sheet_name = re.sub(r'[\\/*?:[\]]', '_', candidate_name[:31])
            
            # Create individual sheet for each candidate
            ws_candidate = wb.create_sheet(title=sheet_name)
            
            # Title
            ws_candidate.merge_cells('A1:D1')
            title_cell = ws_candidate['A1']
            title_cell.value = f"RESUME ANALYSIS: {candidate_name}"
            title_cell.font = title_font
            title_cell.fill = header_fill
            title_cell.alignment = Alignment(horizontal='center')
            
            row = 3
            
            # Basic Information
            info_data = [
                ("Candidate Name", analysis.get('candidate_name', 'N/A')),
                ("Rank", analysis.get('rank', 'N/A')),
                ("ATS Score", f"{analysis.get('overall_score', 0)}/100"),
                ("Recommendation", analysis.get('recommendation', 'N/A')),
                ("Original File", analysis.get('filename', 'N/A')),
                ("File Size", analysis.get('file_size', 'N/A')),
                ("Analysis ID", analysis.get('analysis_id', 'N/A')),
                ("Key Used", analysis.get('key_used', 'N/A')),
                ("Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            ]
            
            for label, value in info_data:
                ws_candidate[f'A{row}'] = label
                ws_candidate[f'A{row}'].font = Font(bold=True)
                ws_candidate[f'B{row}'] = value
                row += 1
            
            row += 1
            
            # Experience Summary (complete)
            ws_candidate[f'A{row}'] = "EXPERIENCE SUMMARY"
            ws_candidate[f'A{row}'].font = Font(bold=True, size=12, color="4472C4")
            ws_candidate.merge_cells(f'A{row}:D{row}')
            row += 1
            
            exp_text = analysis.get('experience_summary', 'No experience summary available.')
            ws_candidate[f'A{row}'] = exp_text
            ws_candidate[f'A{row}'].alignment = Alignment(wrap_text=True)
            ws_candidate.merge_cells(f'A{row}:D{row}')
            ws_candidate.row_dimensions[row].height = 80
            row += 2
            
            # Education Summary (complete)
            ws_candidate[f'A{row}'] = "EDUCATION SUMMARY"
            ws_candidate[f'A{row}'].font = Font(bold=True, size=12, color="4472C4")
            ws_candidate.merge_cells(f'A{row}:D{row}')
            row += 1
            
            edu_text = analysis.get('education_summary', 'No education summary available.')
            ws_candidate[f'A{row}'] = edu_text
            ws_candidate[f'A{row}'].alignment = Alignment(wrap_text=True)
            ws_candidate.merge_cells(f'A{row}:D{row}')
            ws_candidate.row_dimensions[row].height = 80
            row += 2
            
            # Skills Section
            ws_candidate[f'A{row}'] = "SKILLS ANALYSIS"
            ws_candidate[f'A{row}'].font = Font(bold=True, size=12, color="4472C4")
            ws_candidate.merge_cells(f'A{row}:D{row}')
            row += 1
            
            # Skills Matched
            ws_candidate[f'A{row}'] = "Matched Skills:"
            ws_candidate[f'A{row}'].font = Font(bold=True, color="00AA00")
            skills_matched = analysis.get('skills_matched', [])
            for i, skill in enumerate(skills_matched[:8], start=1):
                ws_candidate[f'B{row}'] = f"{i}. {skill}"
                row += 1
            
            row += 1
            
            # Skills Missing
            ws_candidate[f'A{row}'] = "Missing Skills:"
            ws_candidate[f'A{row}'].font = Font(bold=True, color="FF0000")
            skills_missing = analysis.get('skills_missing', [])
            for i, skill in enumerate(skills_missing[:8], start=1):
                ws_candidate[f'B{row}'] = f"{i}. {skill}"
                row += 1
            
            row += 1
            
            # Key Strengths
            ws_candidate[f'A{row}'] = "KEY STRENGTHS"
            ws_candidate[f'A{row}'].font = Font(bold=True, size=12, color="4472C4")
            ws_candidate.merge_cells(f'A{row}:D{row}')
            row += 1
            
            strengths = analysis.get('key_strengths', [])
            for i, strength in enumerate(strengths[:3], start=1):
                ws_candidate[f'A{row}'] = f"{i}."
                ws_candidate[f'A{row}'].font = Font(bold=True)
                ws_candidate[f'B{row}'] = strength
                ws_candidate.merge_cells(f'B{row}:D{row}')
                row += 1
            
            row += 1
            
            # Areas for Improvement
            ws_candidate[f'A{row}'] = "AREAS FOR IMPROVEMENT"
            ws_candidate[f'A{row}'].font = Font(bold=True, size=12, color="4472C4")
            ws_candidate.merge_cells(f'A{row}:D{row}')
            row += 1
            
            improvements = analysis.get('areas_for_improvement', [])
            for i, area in enumerate(improvements[:3], start=1):
                ws_candidate[f'A{row}'] = f"{i}."
                ws_candidate[f'A{row}'].font = Font(bold=True)
                ws_candidate[f'B{row}'] = area
                ws_candidate.merge_cells(f'B{row}:D{row}')
                row += 1
            
            # Set column widths for candidate sheet
            ws_candidate.column_dimensions['A'].width = 25
            ws_candidate.column_dimensions['B'].width = 40
            ws_candidate.column_dimensions['C'].width = 40
            ws_candidate.column_dimensions['D'].width = 40
        
        # Remove the default sheet if it still exists
        if default_sheet.title in wb.sheetnames:
            wb.remove(default_sheet)
        
        # Add borders to all cells in all sheets (skip merged cells)
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for sheet in wb.worksheets:
            for row in sheet.iter_rows():
                for cell in row:
                    # Skip merged cells to avoid the attribute error
                    if not isinstance(cell, MergedCell) and cell.value is not None:
                        cell.border = thin_border
        
        # Save the file
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📊 Comprehensive batch Excel report saved to: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Error creating comprehensive batch Excel report: {str(e)}")
        traceback.print_exc()
        # Create a minimal report as fallback
        return create_minimal_batch_report(analyses, job_description, filename)

def create_minimal_batch_report(analyses, job_description, filename):
    """Create a comprehensive batch report with all candidate details including summaries"""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Batch Analysis"
        
        # Header styling
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        title_font = Font(bold=True, size=16)
        
        # Title
        ws.merge_cells('A1:H1')
        ws['A1'] = "Batch Resume Analysis Report (Comprehensive)"
        ws['A1'].font = title_font
        ws['A1'].fill = header_fill
        ws['A1'].alignment = Alignment(horizontal='center')
        
        row = 3
        
        # Headers with all fields including summaries
        headers = ["Rank", "Candidate", "Score", "Recommendation", "Skills Matched", "Skills Missing", "Experience Summary", "Education Summary"]
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', wrap_text=True)
        
        row += 1
        
        # Data rows with complete summaries
        for analysis in analyses:
            ws.cell(row=row, column=1, value=analysis.get('rank', 'N/A')).alignment = Alignment(horizontal='center')
            ws.cell(row=row, column=2, value=analysis.get('candidate_name', 'Unknown'))
            
            score = analysis.get('overall_score', 0)
            score_cell = ws.cell(row=row, column=3, value=score)
            score_cell.alignment = Alignment(horizontal='center')
            
            # Color coding
            if score >= 80:
                score_cell.font = Font(bold=True, color="00FF00")
            elif score >= 60:
                score_cell.font = Font(bold=True, color="FFA500")
            else:
                score_cell.font = Font(bold=True, color="FF0000")
            
            ws.cell(row=row, column=4, value=analysis.get('recommendation', 'N/A'))
            
            # Skills
            skills_matched = analysis.get('skills_matched', [])
            ws.cell(row=row, column=5, value=", ".join(skills_matched) if skills_matched else "N/A")
            
            skills_missing = analysis.get('skills_missing', [])
            ws.cell(row=row, column=6, value=", ".join(skills_missing) if skills_missing else "All matched")
            
            # Complete summaries (not truncated)
            experience_summary = analysis.get('experience_summary', 'No experience summary available.')
            ws.cell(row=row, column=7, value=experience_summary)
            ws.cell(row=row, column=7).alignment = Alignment(wrap_text=True, vertical='top')
            
            education_summary = analysis.get('education_summary', 'No education summary available.')
            ws.cell(row=row, column=8, value=education_summary)
            ws.cell(row=row, column=8).alignment = Alignment(wrap_text=True, vertical='top')
            
            # Set row height for summaries
            ws.row_dimensions[row].height = 80
            
            row += 1
        
        # Set column widths
        column_widths = [8, 25, 12, 20, 30, 30, 40, 40]
        for i, width in enumerate(column_widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = width
        
        # Add borders
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for row_cells in ws.iter_rows(min_row=1, max_row=row-1, min_col=1, max_col=8):
            for cell in row_cells:
                if cell.value is not None and not isinstance(cell, MergedCell):
                    cell.border = thin_border
        
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📊 Minimal batch report saved: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Error creating minimal batch report: {str(e)}")
        traceback.print_exc()
        return None

# ============ API ROUTES ============

@app.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        'message': 'Resume Analyzer API (Groq Parallel Processing)',
        'version': '2.5.2',
        'status': 'running',
        'ai_provider': 'groq',
        'model': GROQ_MODEL,
        'processing_method': 'round_robin_parallel',
        'max_batch_size': MAX_BATCH_SIZE,
        'endpoints': {
            '/analyze': 'POST - Analyze single resume',
            '/batch-analyze': 'POST - Analyze multiple resumes',
            '/download/<filename>': 'GET - Download report',
            '/preview-resume/<analysis_id>': 'GET - Preview resume',
            '/check-ai': 'GET - Check AI availability',
            '/health': 'GET - Health check',
            '/ping': 'GET - Keep alive ping'
        }
    })

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Analyze a single resume"""
    try:
        update_activity()
        
        if 'resume' not in request.files:
            return jsonify({'error': 'No resume file uploaded'}), 400
        
        if 'jobDescription' not in request.form:
            return jsonify({'error': 'No job description provided'}), 400
        
        resume_file = request.files['resume']
        job_description = request.form['jobDescription']
        
        if resume_file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        # Check file extension
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        if file_ext not in ['.pdf', '.docx', '.txt', '.doc']:
            return jsonify({'error': 'Unsupported file format. Please upload PDF, DOCX, DOC, or TXT.'}), 400
        
        # Extract text based on file type
        if file_ext == '.pdf':
            resume_text = extract_text_from_pdf(resume_file)
        elif file_ext in ['.docx', '.doc']:
            resume_text = extract_text_from_docx(resume_file)
        elif file_ext == '.txt':
            resume_text = extract_text_from_txt(resume_file)
        
        if not resume_text or len(resume_text.strip()) < 50:
            return jsonify({'error': 'Could not extract sufficient text from resume. Please ensure the file is not empty or corrupted.'}), 400
        
        # Analyze the resume
        analysis = analyze_resume_with_retry(resume_text, job_description, resume_file.filename)
        
        # Store resume for preview
        resume_file.seek(0)
        preview_filename = store_resume_file(resume_file, resume_file.filename, analysis['analysis_id'])
        analysis['preview_available'] = preview_filename is not None
        
        # Create individual Excel report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_filename = f"resume_analysis_{timestamp}.xlsx"
        excel_path = create_individual_excel_report(analysis, job_description, excel_filename)
        
        # Prepare response
        analysis['excel_report'] = excel_filename if excel_path else None
        analysis['file_size'] = f"{len(resume_text)} characters"
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Error in /analyze: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/batch-analyze', methods=['POST'])
def batch_analyze_resumes():
    """Analyze multiple resumes in parallel"""
    try:
        update_activity()
        
        if 'resumes[]' not in request.files:
            return jsonify({'error': 'No resume files uploaded'}), 400
        
        if 'jobDescription' not in request.form:
            return jsonify({'error': 'No job description provided'}), 400
        
        resume_files = request.files.getlist('resumes[]')
        job_description = request.form['jobDescription']
        
        if len(resume_files) == 0:
            return jsonify({'error': 'No resume files provided'}), 400
        
        if len(resume_files) > MAX_BATCH_SIZE:
            return jsonify({'error': f'Maximum {MAX_BATCH_SIZE} resumes allowed per batch'}), 400
        
        print(f"\n{'='*60}")
        print(f"🎯 BATCH ANALYSIS STARTED")
        print(f"{'='*60}")
        print(f"📊 Total Resumes: {len(resume_files)}")
        print(f"🔑 Available Keys: {sum(1 for k in GROQ_API_KEYS if k)}")
        print(f"⚡ Processing Method: Round-robin Parallel")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        # Extract text from all resumes
        resume_data = []
        for i, resume_file in enumerate(resume_files):
            file_ext = os.path.splitext(resume_file.filename)[1].lower()
            
            if file_ext not in ['.pdf', '.docx', '.txt', '.doc']:
                continue
            
            # Extract text
            if file_ext == '.pdf':
                text = extract_text_from_pdf(resume_file)
            elif file_ext in ['.docx', '.doc']:
                text = extract_text_from_docx(resume_file)
            elif file_ext == '.txt':
                text = extract_text_from_txt(resume_file)
            
            if text and len(text.strip()) >= 50:
                resume_file.seek(0)
                file_data = resume_file.read()
                resume_data.append({
                    'text': text,
                    'filename': resume_file.filename,
                    'index': i,
                    'file_data': file_data,
                    'file_size': len(text)
                })
        
        if not resume_data:
            return jsonify({'error': 'No valid resumes could be processed'}), 400
        
        print(f"✅ Extracted text from {len(resume_data)} resumes")
        
        # Analyze all resumes in parallel using round-robin
        def analyze_resume_task(resume_info):
            result = analyze_resume_with_retry(
                resume_info['text'],
                job_description,
                resume_info['filename'],
                resume_info['index']
            )
            result['file_size'] = f"{resume_info['file_size']} characters"
            
            # Store resume for preview
            preview_filename = store_resume_file(
                resume_info['file_data'],
                resume_info['filename'],
                result['analysis_id']
            )
            result['preview_available'] = preview_filename is not None
            
            return result
        
        # Use ThreadPoolExecutor for parallel processing
        analyses = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
            future_to_resume = {
                executor.submit(analyze_resume_task, resume_info): resume_info
                for resume_info in resume_data
            }
            
            for future in concurrent.futures.as_completed(future_to_resume):
                try:
                    result = future.result()
                    analyses.append(result)
                    print(f"✅ Completed: {result.get('candidate_name', 'Unknown')} - Score: {result.get('overall_score', 0)}")
                except Exception as e:
                    print(f"❌ Analysis failed: {str(e)}")
        
        # Sort by score (descending)
        analyses.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        # Add rankings
        for rank, analysis in enumerate(analyses, start=1):
            analysis['rank'] = rank
        
        processing_time = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"✅ BATCH ANALYSIS COMPLETE")
        print(f"{'='*60}")
        print(f"⏱️  Processing Time: {processing_time:.2f}s")
        print(f"📊 Resumes Analyzed: {len(analyses)}")
        print(f"⚡ Avg Time/Resume: {processing_time/len(analyses):.2f}s")
        print(f"{'='*60}\n")
        
        # Create comprehensive Excel report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        batch_filename = f"batch_analysis_{timestamp}.xlsx"
        batch_excel_path = create_comprehensive_batch_report(analyses, job_description, batch_filename)
        
        return jsonify({
            'analyses': analyses,
            'total_resumes': len(analyses),
            'processing_time': f"{processing_time:.2f}s",
            'batch_excel_report': batch_filename if batch_excel_path else None,
            'top_candidate': analyses[0] if analyses else None,
            'ai_model': GROQ_MODEL,
            'processing_method': 'round_robin_parallel'
        })
        
    except Exception as e:
        print(f"❌ Error in /batch-analyze: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Batch analysis failed: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_report(filename):
    """Download a report file"""
    try:
        update_activity()
        filepath = os.path.join(REPORTS_FOLDER, filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        print(f"❌ Error downloading file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/preview-resume/<analysis_id>')
def preview_resume(analysis_id):
    """Preview a stored resume"""
    try:
        update_activity()
        
        if analysis_id not in resume_storage:
            return jsonify({'error': 'Resume not found'}), 404
        
        resume_info = resume_storage[analysis_id]
        
        # Try to serve PDF preview if available
        if resume_info.get('has_pdf_preview') and resume_info.get('pdf_path'):
            pdf_path = resume_info['pdf_path']
            if os.path.exists(pdf_path):
                return send_file(pdf_path, mimetype='application/pdf')
        
        # Fallback to original file
        file_path = resume_info['path']
        if os.path.exists(file_path):
            return send_file(file_path)
        
        return jsonify({'error': 'File not found'}), 404
        
    except Exception as e:
        print(f"❌ Error previewing resume: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/check-ai', methods=['GET'])
def check_ai_availability():
    """Check if AI service is available and ready"""
    try:
        update_activity()
        
        available_keys = sum(1 for key in GROQ_API_KEYS if key)
        
        if available_keys == 0:
            return jsonify({
                'available': False,
                'reason': 'No API keys configured',
                'available_keys': 0,
                'ai_provider': 'groq',
                'model': GROQ_MODEL
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
                            'skills_analysis': '5-8 skills per category'
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
        'version': '2.5.2',
        'key_status': key_status,
        'available_keys': available_keys,
        'configuration': {
            'max_batch_size': MAX_BATCH_SIZE,
            'max_concurrent_requests': MAX_CONCURRENT_REQUESTS,
            'max_retries': MAX_RETRIES,
            'min_skills_to_show': MIN_SKILLS_TO_SHOW,
            'max_skills_to_show': MAX_SKILLS_TO_SHOW
        },
        'processing_method': 'round_robin_parallel',
        'performance_target': '10 resumes in 10-15 seconds',
        'skills_analysis': '5-8 skills per category',
        'summaries': 'Complete 4-5 sentences each',
        'insights': '3 strengths & 3 improvements'
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
    print(f"✅ Complete Summaries: 4-5 sentences each (no truncation)")
    print(f"✅ Insights: 3 strengths & 3 improvements")
    print(f"✅ Resume Preview: Enabled with PDF conversion")
    print(f"✅ Performance: ~10 resumes in 10-15 seconds")
    print(f"✅ Excel Reports: Candidate Details + Individual Sheets Only")
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
