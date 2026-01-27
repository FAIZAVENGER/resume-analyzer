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
import requests
import re
import hashlib
import random

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure multiple Groq API keys
GROQ_API_KEYS = [
    os.getenv('GROQ_API_KEY_1'),
    os.getenv('GROQ_API_KEY_2'),
    os.getenv('GROQ_API_KEY_3')
]

# Filter out None values
ACTIVE_API_KEYS = [key for key in GROQ_API_KEYS if key]

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')

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

# Rate limiting protection
RATE_LIMIT_DELAY = 2.0  # Increased delay between requests
MAX_RETRIES = 3

# Global variables
service_running = True

# Track last API call time to respect rate limits
last_api_call_time = {}
for key in ACTIVE_API_KEYS:
    last_api_call_time[key] = datetime.now() - timedelta(minutes=5)

def get_next_available_key():
    """Get next available API key with rate limit protection"""
    if not ACTIVE_API_KEYS:
        return None
    
    # Find key with oldest last API call (round-robin with rate limit protection)
    now = datetime.now()
    available_keys = []
    
    for key in ACTIVE_API_KEYS:
        time_since_last_call = (now - last_api_call_time.get(key, now - timedelta(minutes=5))).total_seconds()
        # Only use keys that haven't been used in the last 2 seconds
        if time_since_last_call >= RATE_LIMIT_DELAY:
            available_keys.append((key, time_since_last_call))
    
    if not available_keys:
        # If all keys were recently used, use the one with oldest call
        available_keys = [(key, (now - last_api_call_time.get(key, now - timedelta(minutes=5))).total_seconds()) 
                         for key in ACTIVE_API_KEYS]
    
    # Sort by time since last call (oldest first)
    available_keys.sort(key=lambda x: x[1], reverse=True)
    selected_key = available_keys[0][0]
    
    # Update last call time
    last_api_call_time[selected_key] = now
    
    key_index = ACTIVE_API_KEYS.index(selected_key) + 1 if selected_key in ACTIVE_API_KEYS else 0
    print(f"🔑 Selected API key {key_index} (last used {available_keys[0][1]:.1f}s ago)")
    return selected_key

def wait_for_rate_limit(key):
    """Wait if necessary to respect rate limits"""
    if key not in last_api_call_time:
        return
    
    now = datetime.now()
    time_since_last_call = (now - last_api_call_time[key]).total_seconds()
    
    if time_since_last_call < RATE_LIMIT_DELAY:
        wait_time = RATE_LIMIT_DELAY - time_since_last_call
        print(f"⏳ Rate limit wait: {wait_time:.2f}s for key {ACTIVE_API_KEYS.index(key) + 1}")
        time.sleep(wait_time)

def call_groq_api(prompt, max_tokens=1000, temperature=0.2, timeout=30, model_override=None, retry_count=0, api_key=None):
    """Call Groq API with the given prompt with optimized retry logic"""
    if not api_key:
        print("❌ No API key provided")
        return {'error': 'no_api_key', 'status': 500}
    
    # Wait before making API call to respect rate limits
    wait_for_rate_limit(api_key)
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    model_to_use = model_override or GROQ_MODEL or DEFAULT_MODEL
    
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
        
        # Update last API call time
        last_api_call_time[api_key] = datetime.now()
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                result = data['choices'][0]['message']['content']
                print(f"✅ Groq API response in {response_time:.2f}s using {model_to_use}")
                return result
            else:
                print(f"❌ Unexpected Groq API response format")
                return {'error': 'invalid_response', 'status': response.status_code}
        elif response.status_code == 400:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', 'Bad Request')
            print(f"❌ Groq API Error 400: {error_msg[:200]}")
            
            if 'decommissioned' in error_msg.lower() or 'deprecated' in error_msg.lower():
                print(f"⚠️ Model {model_to_use} is deprecated. Trying default model {DEFAULT_MODEL}...")
                return call_groq_api(prompt, max_tokens, temperature, timeout, DEFAULT_MODEL, retry_count, api_key)
            
            return {'error': f'api_error_400: {error_msg[:100]}', 'status': 400}
        elif response.status_code == 429:
            print(f"❌ Groq API rate limit exceeded for key")
            # Exponential backoff with jitter for rate limiting
            if retry_count < MAX_RETRIES:
                wait_time = (2 ** retry_count) * 3 + random.uniform(0, 2)  # Increased wait time
                print(f"⏳ Rate limited, retrying in {wait_time:.1f}s (attempt {retry_count + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                return call_groq_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1, api_key)
            return {'error': 'rate_limit', 'status': 429}
        elif response.status_code == 503:
            print(f"❌ Groq API service unavailable")
            if retry_count < 2:
                wait_time = 5 + random.uniform(0, 2)
                print(f"⏳ Service unavailable, retrying in {wait_time:.1f}s")
                time.sleep(wait_time)
                return call_groq_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1, api_key)
            return {'error': 'service_unavailable', 'status': 503}
        else:
            print(f"❌ Groq API Error {response.status_code}: {response.text[:200]}")
            return {'error': f'api_error_{response.status_code}', 'status': response.status_code}
            
    except requests.exceptions.Timeout:
        print(f"❌ Groq API timeout after {timeout}s")
        if retry_count < 2:
            wait_time = 3 + random.uniform(0, 2)
            print(f"⏳ Timeout, retrying in {wait_time:.1f}s (attempt {retry_count + 1}/3)")
            time.sleep(wait_time)
            return call_groq_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1, api_key)
        return {'error': 'timeout', 'status': 408}
    except requests.exceptions.ConnectionError:
        print(f"❌ Groq API connection error")
        if retry_count < 2:
            wait_time = 3 + random.uniform(0, 2)
            print(f"⏳ Connection error, retrying in {wait_time:.1f}s")
            time.sleep(wait_time)
            return call_groq_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1, api_key)
        return {'error': 'connection_error', 'status': 503}
    except Exception as e:
        print(f"❌ Groq API Exception: {str(e)}")
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
            
            # Add delay between warm-up calls
            if idx > 1:
                time.sleep(1.5)
            
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
            return False
        
    except Exception as e:
        print(f"⚠️ Warm-up attempt failed: {str(e)}")
        return False

def update_activity():
    """Update last activity timestamp"""
    global last_activity_time
    last_activity_time = datetime.now()

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        update_activity()
        
        reader = PdfReader(file_path)
        text = ""
        
        for page in reader.pages:
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            except Exception as e:
                print(f"⚠️ PDF page extraction error: {e}")
                continue
        
        if not text.strip():
            return "Error: PDF appears to be empty or text could not be extracted"
        
        # Optimize for Groq processing - keep it concise
        if len(text) > 8000:
            text = text[:8000] + "\n[Text truncated for optimal processing...]"
            
        return text
    except Exception as e:
        print(f"❌ PDF Error: {traceback.format_exc()}")
        return f"Error reading PDF: {str(e)[:100]}"

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        update_activity()
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
        
        if not text.strip():
            return "Error: Document appears to be empty"
        
        # Optimize for Groq processing
        if len(text) > 8000:
            text = text[:8000] + "\n[Text truncated for optimal processing...]"
            
        return text
    except Exception as e:
        print(f"❌ DOCX Error: {traceback.format_exc()}")
        return f"Error reading DOCX: {str(e)}"

def extract_text_from_txt(file_path):
    """Extract text from TXT file"""
    try:
        update_activity()
        encodings = ['utf-8', 'latin-1', 'windows-1252', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    text = file.read()
                    
                if not text.strip():
                    return "Error: Text file appears to be empty"
                
                # Optimize for Groq processing
                if len(text) > 8000:
                    text = text[:8000] + "\n[Text truncated for optimal processing...]"
                    
                return text
            except UnicodeDecodeError:
                continue
                
        return "Error: Could not decode text file with common encodings"
        
    except Exception as e:
        print(f"❌ TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

def analyze_resume_with_ai(resume_text, job_description, filename=None, analysis_id=None, api_key=None):
    """Use Groq API to analyze resume against job description"""
    update_activity()
    
    if not api_key:
        api_key = get_next_available_key()
    
    if not api_key:
        print("❌ No available API key.")
        return create_fallback_response(filename)
    
    if not warmup_complete:
        print(f"⚠️ Groq API not warmed up yet, analysis may be slower")
    
    # Optimize text length for better performance
    resume_text = resume_text[:4000]
    job_description = job_description[:1500]
    
    prompt = f"""You are an expert ATS (Applicant Tracking System) analyzer and recruitment specialist. 
Analyze this resume against the job description and provide a comprehensive analysis.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Provide analysis in this exact JSON format:
{{
    "candidate_name": "Extract name from resume or use filename",
    "skills_matched": ["exact skill 1", "exact skill 2", "exact skill 3"],
    "skills_missing": ["exact skill 1", "exact skill 2"],
    "experience_summary": "2-3 sentence summary focusing on relevant experience",
    "education_summary": "1-2 sentence summary of education and certifications",
    "overall_score": 75,
    "recommendation": "Highly Recommended/Recommended/Moderately Recommended/Needs Improvement/Not Recommended",
    "key_strengths": ["specific strength 1", "specific strength 2"],
    "areas_for_improvement": ["specific area 1", "specific area 2"]
}}

Return ONLY the JSON object, no other text."""

    try:
        model_to_use = GROQ_MODEL or DEFAULT_MODEL
        key_index = ACTIVE_API_KEYS.index(api_key) + 1 if api_key in ACTIVE_API_KEYS else 0
        print(f"⚡ Sending to Groq API (Key {key_index}, {model_to_use})...")
        start_time = time.time()
        
        response = call_groq_api(
            prompt=prompt,
            max_tokens=800,
            temperature=0.1,
            timeout=45,
            api_key=api_key
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            if error_type == 'rate_limit':
                print("❌ Rate limit exceeded, using fallback response")
                return create_fallback_response(filename)
            elif error_type == 'timeout':
                print("❌ Groq API timeout, using fallback response")
                return create_fallback_response(filename)
            else:
                print(f"❌ Groq API error: {error_type}, using fallback response")
                return create_fallback_response(filename)
        
        elapsed_time = time.time() - start_time
        print(f"✅ Groq API response in {elapsed_time:.2f} seconds (Key {key_index})")
        
        result_text = response.strip()
        
        # Extract JSON from response
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
            return create_fallback_response(filename)
        
        # Ensure required fields exist with defaults
        analysis['candidate_name'] = analysis.get('candidate_name', filename.replace('.pdf', '').replace('.docx', '').replace('.txt', '').title() if filename else "Professional Candidate")
        analysis['skills_matched'] = analysis.get('skills_matched', ["Analysis completed"])
        analysis['skills_missing'] = analysis.get('skills_missing', ["Review job description"])
        analysis['experience_summary'] = analysis.get('experience_summary', "Candidate demonstrates relevant professional experience.")
        analysis['education_summary'] = analysis.get('education_summary', "Candidate possesses appropriate educational qualifications.")
        analysis['overall_score'] = analysis.get('overall_score', 70)
        analysis['recommendation'] = analysis.get('recommendation', 'Consider for Interview')
        analysis['key_strengths'] = analysis.get('key_strengths', ["Strong analytical skills", "Good communication"])
        analysis['areas_for_improvement'] = analysis.get('areas_for_improvement', ["Could benefit from additional training"])
        
        # Add AI provider info
        analysis['ai_provider'] = "groq"
        analysis['ai_model'] = model_to_use
        analysis['response_time'] = f"{elapsed_time:.2f}s"
        analysis['api_key_used'] = f"key_{key_index}" if key_index > 0 else "unknown"
        
        # Add analysis ID if provided
        if analysis_id:
            analysis['analysis_id'] = analysis_id
        
        print(f"✅ Analysis completed for: {analysis['candidate_name']} (Score: {analysis['overall_score']}, Key: {key_index})")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Groq Analysis Error: {str(e)}")
        return create_fallback_response(filename)

def create_fallback_response(filename=None):
    """Create a fallback response when Groq API fails"""
    candidate_name = "Professional Candidate"
    if filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').title()
        if len(clean_name.split()) <= 4:
            candidate_name = clean_name
    
    return {
        "candidate_name": candidate_name,
        "skills_matched": ["Rate limit protection active", "Please try again in a moment"],
        "skills_missing": ["Detailed analysis coming soon", "Service optimizing for rate limits"],
        "experience_summary": f"Resume analysis service is optimizing API calls to avoid rate limits.",
        "education_summary": f"Educational background analysis will proceed with next available API slot.",
        "overall_score": 60,
        "recommendation": "Rate Limit Protection - Please Retry",
        "key_strengths": ["Rate limit protection enabled", "Automatic retry system"],
        "areas_for_improvement": ["Waiting for API quota refresh", "Try single resume analysis"],
        "ai_provider": "groq",
        "ai_status": "Rate limit protection"
    }

def create_excel_report(analysis_data, filename="resume_analysis_report.xlsx"):
    """Create a beautiful Excel report with the analysis"""
    update_activity()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Resume Analysis"
    
    # Define styles
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    subheader_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    subheader_font = Font(bold=True, size=11)
    groq_fill = PatternFill(start_color="00B09B", end_color="96C93D", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Set column widths
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 60
    
    row = 1
    
    # Title
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "⚡ GROQ RESUME ANALYSIS REPORT"
    cell.font = Font(bold=True, size=16, color="FFFFFF")
    cell.fill = groq_fill
    cell.alignment = Alignment(horizontal='center', vertical='center')
    row += 2
    
    # Candidate Information
    ws[f'A{row}'] = "Candidate Name"
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = analysis_data.get('candidate_name', 'N/A')
    row += 1
    
    ws[f'A{row}'] = "Analysis Date"
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row += 1
    
    ws[f'A{row}'] = "AI Provider"
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = "GROQ"
    row += 1
    
    model_to_use = analysis_data.get('ai_model', GROQ_MODEL or DEFAULT_MODEL)
    ws[f'A{row}'] = "AI Model"
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = model_to_use
    row += 1
    
    if analysis_data.get('api_key_used'):
        ws[f'A{row}'] = "API Key Used"
        ws[f'A{row}'].font = subheader_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'B{row}'] = f"Key {analysis_data['api_key_used'].replace('key_', '')}"
        row += 2
    
    # Overall Score
    ws[f'A{row}'] = "Overall Match Score"
    ws[f'A{row}'].font = Font(bold=True, size=12)
    ws[f'A{row}'].fill = header_fill
    ws[f'A{row}'].font = Font(bold=True, size=12, color="FFFFFF")
    ws[f'B{row}'] = f"{analysis_data.get('overall_score', 0)}/100"
    score_color = "C00000" if analysis_data.get('overall_score', 0) < 60 else "70AD47" if analysis_data.get('overall_score', 0) >= 80 else "FFC000"
    ws[f'B{row}'].font = Font(bold=True, size=12, color=score_color)
    row += 1
    
    ws[f'A{row}'] = "Recommendation"
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = analysis_data.get('recommendation', 'N/A')
    row += 2
    
    # Skills Matched Section
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "SKILLS MATCHED ✓"
    cell.font = header_font
    cell.fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
    cell.alignment = Alignment(horizontal='center')
    row += 1
    
    skills_matched = analysis_data.get('skills_matched', [])
    if skills_matched:
        for i, skill in enumerate(skills_matched, 1):
            ws[f'A{row}'] = f"{i}."
            ws[f'B{row}'] = skill
            ws[f'B{row}'].alignment = Alignment(wrap_text=True)
            row += 1
    else:
        ws[f'A{row}'] = "No matched skills found"
        row += 1
    
    row += 1
    
    # Skills Missing Section
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "SKILLS MISSING ✗"
    cell.font = header_font
    cell.fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
    cell.alignment = Alignment(horizontal='center')
    row += 1
    
    skills_missing = analysis_data.get('skills_missing', [])
    if skills_missing:
        for i, skill in enumerate(skills_missing, 1):
            ws[f'A{row}'] = f"{i}."
            ws[f'B{row}'] = skill
            ws[f'B{row}'].alignment = Alignment(wrap_text=True)
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
    ws.row_dimensions[row].height = 80
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
    ws.row_dimensions[row].height = 60
    row += 2
    
    # Key Strengths
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "KEY STRENGTHS"
    cell.font = header_font
    cell.fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
    cell.alignment = Alignment(horizontal='center')
    row += 1
    
    for strength in analysis_data.get('key_strengths', []):
        ws[f'A{row}'] = "•"
        ws[f'B{row}'] = strength
        ws[f'B{row}'].alignment = Alignment(wrap_text=True)
        row += 1
    
    row += 1
    
    # Areas for Improvement
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "AREAS FOR IMPROVEMENT"
    cell.font = header_font
    cell.fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
    cell.alignment = Alignment(horizontal='center')
    row += 1
    
    for area in analysis_data.get('areas_for_improvement', []):
        ws[f'A{row}'] = "•"
        ws[f'B{row}'] = area
        ws[f'B{row}'].alignment = Alignment(wrap_text=True)
        row += 1
    
    # Apply borders to all cells
    for row_cells in ws.iter_rows(min_row=1, max_row=row, min_col=1, max_col=2):
        for cell in row_cells:
            cell.border = border
    
    # Save the file
    filepath = os.path.join(REPORTS_FOLDER, filename)
    wb.save(filepath)
    print(f"📄 Excel report saved to: {filepath}")
    return filepath

@app.route('/')
def home():
    """Root route - API landing page"""
    global warmup_complete, last_activity_time
    
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    warmup_status = "✅ Ready" if warmup_complete else "🔥 Warming up..."
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    
    return f'''
    <!DOCTYPE html>
<html>
<head>
    <title>Resume Analyzer API</title>
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            margin: 0;
            padding: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }}
        
        .container {{
            max-width: 800px;
            width: 100%;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            text-align: center;
        }}
        
        h1 {{
            color: #2c3e50;
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .subtitle {{
            color: #7f8c8d;
            font-size: 1.1rem;
            margin-bottom: 30px;
        }}
        
        .status-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            border-left: 5px solid #667eea;
        }}
        
        .status-item {{
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .status-label {{
            font-weight: 600;
            color: #2c3e50;
        }}
        
        .status-value {{
            color: #27ae60;
            font-weight: 600;
        }}
        
        .warmup-status {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px;
            background: #e3f2fd;
            border-radius: 10px;
            margin: 15px 0;
            border-left: 4px solid #2196f3;
        }}
        
        .warmup-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: {'#4caf50' if warmup_complete else '#ff9800'};
            animation: {'none' if warmup_complete else 'pulse 1.5s infinite'};
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        .endpoints {{
            text-align: left;
            margin: 30px 0;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
            border: 2px solid #e9ecef;
        }}
        
        .endpoint {{
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            transition: transform 0.3s;
        }}
        
        .endpoint:hover {{
            transform: translateX(10px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        
        .method {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: bold;
            margin-right: 10px;
            font-size: 0.9rem;
        }}
        
        .path {{
            font-family: 'Courier New', monospace;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .description {{
            color: #7f8c8d;
            margin-top: 5px;
            font-size: 0.95rem;
        }}
        
        .api-status {{
            display: inline-block;
            padding: 8px 20px;
            background: #27ae60;
            color: white;
            border-radius: 20px;
            font-weight: bold;
            margin: 20px 0;
        }}
        
        .buttons {{
            margin-top: 30px;
        }}
        
        .btn {{
            display: inline-block;
            padding: 12px 30px;
            margin: 0 10px;
            background: linear-gradient(90deg, #667eea, #764ba2);
            color: white;
            text-decoration: none;
            border-radius: 30px;
            font-weight: bold;
            transition: all 0.3s;
            border: none;
            cursor: pointer;
            font-size: 1rem;
        }}
        
        .btn:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }}
        
        .btn-secondary {{
            background: linear-gradient(90deg, #11998e, #38ef7d);
        }}
        
        .btn-warmup {{
            background: linear-gradient(90deg, #ff9800, #ff5722);
        }}
        
        .footer {{
            margin-top: 40px;
            color: #7f8c8d;
            font-size: 0.9rem;
        }}
        
        .error {{
            color: #e74c3c;
            font-weight: 600;
        }}
        
        .success {{
            color: #27ae60;
            font-weight: 600;
        }}
        
        .warning {{
            color: #ff9800;
            font-weight: 600;
        }}
        
        .info {{
            color: #2196f3;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Resume Analyzer API</h1>
        <p class="subtitle">AI-powered resume analysis • Latest Groq Models • Rate Limit Protected</p>
        
        <div class="api-status">
            ⚡ GROQ API IS RUNNING • RATE LIMIT PROTECTION ENABLED
        </div>
        
        <div class="warmup-status">
            <div class="warmup-dot"></div>
            <div>
                <strong>Groq Service Status:</strong> {warmup_status}
                <br>
                <small>Last activity: {inactive_minutes} minute(s) ago</small>
            </div>
        </div>
        
        <div class="status-card">
            <div class="status-item">
                <span class="status-label">Service Status:</span>
                <span class="status-value"><span class="success">✅ Always Active</span></span>
            </div>
            <div class="status-item">
                <span class="status-label">AI Provider:</span>
                <span class="status-value info">GROQ</span>
            </div>
            <div class="status-item">
                <span class="status-label">Model:</span>
                <span class="status-value">{model_to_use}</span>
            </div>
            <div class="status-item">
                <span class="status-label">API Keys:</span>
                <span class="status-value">{len(ACTIVE_API_KEYS)} Active Keys</span>
            </div>
            <div class="status-item">
                <span class="status-label">Rate Limit Protection:</span>
                <span class="status-value success">✅ Enabled ({RATE_LIMIT_DELAY}s delay)</span>
            </div>
            <div class="status-item">
                <span class="status-label">API Status:</span>
                {'<span class="success">✅ Available</span>' if warmup_complete else '<span class="warning">🔥 Warming...</span>'}
            </div>
        </div>
        
        <div class="endpoints">
            <h2>📡 API Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">POST</span>
                <span class="path">/analyze</span>
                <p class="description">Upload a single resume (PDF/DOCX/TXT) with job description for AI analysis</p>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span>
                <span class="path">/analyze-batch</span>
                <p class="description">Upload multiple resumes for batch analysis with rate limit protection</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/health</span>
                <p class="description">Check API health status and configuration</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/ping</span>
                <p class="description">Simple ping to keep service awake</p>
            </div>
        </div>
        
        <div class="buttons">
            <a href="/health" class="btn">Check Health</a>
            <a href="/warmup" class="btn btn-warmup">Warm Up Groq API</a>
            <a href="/ping" class="btn btn-secondary">Ping Service</a>
        </div>
        
        <div class="footer">
            <p>Powered by Flask & Groq API | Deployed on Render | Rate Limit Protection Enabled</p>
            <p>AI Service: GROQ | Status: {'<span class="success">Ready</span>' if warmup_complete else '<span class="warning">Warming up...</span>'}</p>
            <p>Model: {model_to_use} | API Keys: {len(ACTIVE_API_KEYS)} | Rate Limit Delay: {RATE_LIMIT_DELAY}s</p>
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
        print(f"📋 Job description length: {len(job_description)} characters")
        
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
            return jsonify({'error': 'Groq API not configured. Please set GROQ_API_KEY_1, GROQ_API_KEY_2, GROQ_API_KEY_3 in environment variables'}), 500
        
        # Analyze with Groq API
        model_to_use = GROQ_MODEL or DEFAULT_MODEL
        print(f"⚡ Starting Groq API analysis ({model_to_use})...")
        ai_start = time.time()
        
        # Generate unique analysis ID
        analysis_id = f"single_{timestamp}"
        api_key = get_next_available_key()
        analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id, api_key)
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
        
        # Return analysis
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['ai_model'] = model_to_use
        analysis['ai_provider'] = "groq"
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
    """Analyze multiple resumes against a single job description with rate limit protection"""
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
        
        # Check API configuration
        if not ACTIVE_API_KEYS:
            print("❌ No Groq API keys configured")
            return jsonify({'error': 'Groq API not configured'}), 500
        
        # Prepare batch analysis
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        all_analyses = []
        errors = []
        
        # Process resumes SEQUENTIALLY to avoid rate limits
        print("🔄 Processing resumes sequentially with rate limit protection...")
        
        for idx, resume_file in enumerate(resume_files):
            try:
                if resume_file.filename == '':
                    errors.append({'filename': 'Empty file', 'error': 'File has no name'})
                    continue
                
                print(f"\n📄 Processing resume {idx + 1}/{len(resume_files)}: {resume_file.filename}")
                
                # Save file temporarily
                file_ext = os.path.splitext(resume_file.filename)[1].lower()
                file_path = os.path.join(UPLOAD_FOLDER, f"batch_{batch_id}_{idx}{file_ext}")
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
                    errors.append({'filename': resume_file.filename, 'error': f'Unsupported format: {file_ext}'})
                    continue
                
                if resume_text.startswith('Error'):
                    os.remove(file_path)
                    errors.append({'filename': resume_file.filename, 'error': resume_text})
                    continue
                
                # Analyze with Groq API
                analysis_id = f"{batch_id}_candidate_{idx}"
                api_key = get_next_available_key()
                analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id, api_key)
                
                # Add file info
                analysis['filename'] = resume_file.filename
                analysis['original_filename'] = resume_file.filename
                resume_file.seek(0, 2)
                file_size = resume_file.tell()
                resume_file.seek(0)
                analysis['file_size'] = f"{(file_size / 1024):.1f}KB"
                analysis['analysis_id'] = analysis_id
                
                # Create individual Excel report
                try:
                    excel_filename = f"individual_{analysis_id}.xlsx"
                    excel_path = create_excel_report(analysis, excel_filename)
                    analysis['individual_excel_filename'] = os.path.basename(excel_path)
                except Exception as e:
                    print(f"⚠️ Failed to create individual report: {str(e)}")
                    analysis['individual_excel_filename'] = None
                
                # Clean up
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                all_analyses.append(analysis)
                print(f"✅ Completed: {analysis.get('candidate_name')} - Score: {analysis.get('overall_score')}")
                
                # Add delay between resumes to respect rate limits
                if idx < len(resume_files) - 1:
                    delay = RATE_LIMIT_DELAY + random.uniform(0, 0.5)
                    print(f"⏳ Rate limit delay: {delay:.1f}s before next resume...")
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"❌ Error processing {resume_file.filename if resume_file else 'Unknown'}: {str(e)}")
                errors.append({'filename': resume_file.filename if resume_file else 'Unknown', 'error': f"Processing error: {str(e)[:100]}"})
        
        print(f"\n📊 Batch processing complete. Successful: {len(all_analyses)}, Failed: {len(errors)}")
        
        # Sort by score
        all_analyses.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        # Add ranking
        for rank, analysis in enumerate(all_analyses, 1):
            analysis['rank'] = rank
        
        # Create batch Excel report if we have analyses
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
            'model_used': GROQ_MODEL or DEFAULT_MODEL,
            'ai_provider': "groq",
            'processing_time': f"{time.time() - start_time:.2f}s",
            'job_description_preview': job_description[:200] + ("..." if len(job_description) > 200 else ""),
            'batch_size': len(resume_files),
            'api_keys_used': len(ACTIVE_API_KEYS),
            'rate_limit_protection': f"Enabled ({RATE_LIMIT_DELAY}s delay between requests)"
        }
        
        print(f"✅ Batch analysis completed in {time.time() - start_time:.2f}s")
        print("="*50 + "\n")
        
        return jsonify(batch_summary)
        
    except Exception as e:
        print(f"❌ Batch analysis error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

def create_batch_excel_report(analyses, job_description, filename="batch_resume_analysis.xlsx"):
    """Create a comprehensive Excel report for batch analysis"""
    update_activity()
    
    wb = Workbook()
    
    # Summary Sheet
    ws_summary = wb.active
    ws_summary.title = "Batch Summary"
    
    # Define styles
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    subheader_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    subheader_font = Font(bold=True, size=11)
    groq_fill = PatternFill(start_color="00B09B", end_color="96C93D", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # ========== SUMMARY SHEET ==========
    ws_summary.column_dimensions['A'].width = 25
    ws_summary.column_dimensions['B'].width = 40
    ws_summary.column_dimensions['C'].width = 20
    ws_summary.column_dimensions['D'].width = 15
    ws_summary.column_dimensions['E'].width = 25
    
    # Title
    ws_summary.merge_cells('A1:E1')
    title_cell = ws_summary['A1']
    title_cell.value = "⚡ GROQ BATCH RESUME ANALYSIS"
    title_cell.font = Font(bold=True, size=16, color="FFFFFF")
    title_cell.fill = groq_fill
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Summary Information
    summary_info = [
        ("Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Total Resumes", len(analyses)),
        ("AI Provider", "GROQ"),
        ("AI Model", GROQ_MODEL or DEFAULT_MODEL),
        ("API Keys Used", f"{len(ACTIVE_API_KEYS)} keys"),
        ("Rate Limit Protection", f"{RATE_LIMIT_DELAY}s delay between requests"),
        ("Job Description", job_description[:100] + ("..." if len(job_description) > 100 else "")),
    ]
    
    for i, (label, value) in enumerate(summary_info, start=3):
        ws_summary[f'A{i}'] = label
        ws_summary[f'A{i}'].font = subheader_font
        ws_summary[f'A{i}'].fill = subheader_fill
        ws_summary[f'B{i}'] = value
    
    # Candidates Ranking Header
    row = len(summary_info) + 4
    ws_summary.merge_cells(f'A{row}:E{row}')
    header_cell = ws_summary[f'A{row}']
    header_cell.value = "CANDIDATES RANKING (BY ATS SCORE)"
    header_cell.font = header_font
    header_cell.fill = header_fill
    header_cell.alignment = Alignment(horizontal='center')
    row += 1
    
    # Table Headers
    headers = ["Rank", "Candidate Name", "ATS Score", "Recommendation", "API Key Used"]
    for col, header in enumerate(headers, start=1):
        cell = ws_summary.cell(row=row, column=col)
        cell.value = header
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill(start_color="5B9BD5", end_color="5B9BD5", fill_type="solid")
        cell.alignment = Alignment(horizontal='center')
    
    row += 1
    
    # Add candidates data
    for analysis in analyses:
        ws_summary.cell(row=row, column=1, value=analysis.get('rank', '-'))
        ws_summary.cell(row=row, column=2, value=analysis.get('candidate_name', 'Unknown'))
        
        score_cell = ws_summary.cell(row=row, column=3, value=analysis.get('overall_score', 0))
        score = analysis.get('overall_score', 0)
        if score >= 80:
            score_cell.font = Font(color="00B050", bold=True)
        elif score >= 60:
            score_cell.font = Font(color="FFC000", bold=True)
        else:
            score_cell.font = Font(color="FF0000", bold=True)
        
        ws_summary.cell(row=row, column=4, value=analysis.get('recommendation', 'N/A'))
        
        api_key = analysis.get('api_key_used', 'N/A')
        ws_summary.cell(row=row, column=5, value=f"Key {api_key.replace('key_', '')}" if api_key != 'N/A' else 'N/A')
        
        row += 1
    
    # Add border to the table
    for r in range(row - len(analyses) - 1, row):
        for c in range(1, 6):
            ws_summary.cell(row=r, column=c).border = border
    
    # Save the file
    filepath = os.path.join(REPORTS_FOLDER, filename)
    wb.save(filepath)
    print(f"📊 Batch Excel report saved to: {filepath}")
    return filepath

@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    """Download the Excel report"""
    update_activity()
    
    try:
        print(f"📥 Download request for: {filename}")
        
        import re
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        
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

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    
    return jsonify({
        'status': 'Backend is running!', 
        'timestamp': datetime.now().isoformat(),
        'ai_provider': 'groq',
        'ai_provider_configured': bool(ACTIVE_API_KEYS),
        'api_keys_count': len(ACTIVE_API_KEYS),
        'model': model_to_use,
        'ai_warmup_complete': warmup_complete,
        'rate_limit_delay': RATE_LIMIT_DELAY,
        'max_retries': MAX_RETRIES,
        'inactive_minutes': inactive_minutes,
        'version': '1.0.0',
        'features': ['rate_limit_protection', 'sequential_processing', 'fallback_responses']
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
        'rate_limit_protection': f'{RATE_LIMIT_DELAY}s delay',
        'message': 'Service is alive!'
    })

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
    print(f"✅ Rate Limit Protection: Enabled ({RATE_LIMIT_DELAY}s delay between API calls)")
    print(f"✅ Sequential Processing: Resumes processed one at a time")
    print(f"✅ Fallback Responses: Automatic fallback when rate limited")
    print("="*50 + "\n")
    
    if not ACTIVE_API_KEYS:
        print("⚠️  WARNING: No Groq API keys found!")
        print("Please set GROQ_API_KEY_1, GROQ_API_KEY_2, GROQ_API_KEY_3 in Render environment variables")
        print("Get your API keys from: https://console.groq.com/keys")
    
    # Start warm-up in background
    if ACTIVE_API_KEYS:
        warmup_thread = threading.Thread(target=warmup_groq_service, daemon=True)
        warmup_thread.start()
        print("✅ Warm-up thread started")
    
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode, threaded=True)
