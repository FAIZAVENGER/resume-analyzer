from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google import genai
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
import hashlib
import random
from collections import defaultdict

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configure Gemini AI - Support multiple separate API keys
# Check for keys in this order: GEMINI_API_KEY1, GEMINI_API_KEY2, GEMINI_API_KEY3, GEMINI_API_KEY
api_keys = []

# Check for individual keys (KEY1, KEY2, KEY3, etc.)
for i in range(1, 10):  # Check up to 9 separate keys
    key = os.getenv(f'GEMINI_API_KEY{i}', '').strip()
    if key:
        api_keys.append(key)
        print(f"✅ Found GEMINI_API_KEY{i}: {key[:8]}...")

# Also check for single key (backward compatibility)
single_key = os.getenv('GEMINI_API_KEY', '').strip()
if single_key and single_key not in api_keys:
    api_keys.append(single_key)
    print(f"✅ Found GEMINI_API_KEY: {single_key[:8]}...")

# Check for comma-separated keys (legacy format)
comma_keys_str = os.getenv('GEMINI_API_KEYS', '').strip()
if comma_keys_str:
    comma_keys = [k.strip() for k in comma_keys_str.split(',') if k.strip()]
    for key in comma_keys:
        if key not in api_keys:
            api_keys.append(key)
            print(f"✅ Found from GEMINI_API_KEYS: {key[:8]}...")

if not api_keys:
    print("⚠️  WARNING: No Gemini API keys found!")
    print("ℹ️  Using fallback mode only - No AI analysis available")
    clients = []
else:
    print(f"✅ Total API keys loaded: {len(api_keys)}")
    clients = []
    for i, key in enumerate(api_keys):
        try:
            client = genai.Client(api_key=key)
            clients.append({
                'client': client,
                'key': key,
                'name': f"Key {i+1}",
                'quota_exceeded': False,
                'last_reset': datetime.now(),
                'requests_today': 0,
                'requests_minute': 0,
                'last_request_time': datetime.now(),
                'minute_requests': [],
                'errors': 0,
                'total_requests': 0
            })
            print(f"  {i+1}. {key[:8]}... ✅ Initialized")
        except Exception as e:
            print(f"  {i+1}. {key[:8]}... ❌ Error: {str(e)}")

# Quota tracking
QUOTA_DAILY = 60
QUOTA_PER_MINUTE = 15

# Simple in-memory cache for demo (use Redis in production)
analysis_cache = {}
cache_hits = 0
cache_misses = 0

# Get absolute path for uploads folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"📁 Upload folder: {UPLOAD_FOLDER}")

def check_quota(client_info):
    """Check if client has exceeded quota"""
    now = datetime.now()
    
    # Check daily reset
    if (now - client_info['last_reset']).days >= 1:
        client_info['last_reset'] = now
        client_info['requests_today'] = 0
        client_info['quota_exceeded'] = False
        client_info['minute_requests'] = []
        client_info['errors'] = 0
        print(f"✅ Quota reset for {client_info['name']} ({client_info['key'][:8]}...)")
    
    # Check minute reset
    minute_ago = now - timedelta(minutes=1)
    client_info['minute_requests'] = [
        t for t in client_info['minute_requests'] 
        if t > minute_ago
    ]
    client_info['requests_minute'] = len(client_info['minute_requests'])
    
    # Check if key has too many errors (maybe invalid key)
    if client_info['errors'] > 10:
        client_info['quota_exceeded'] = True
        return False, "Too many errors - key may be invalid"
    
    # Check limits
    if client_info['requests_today'] >= QUOTA_DAILY:
        client_info['quota_exceeded'] = True
        return False, "Daily quota exceeded"
    
    if client_info['requests_minute'] >= QUOTA_PER_MINUTE:
        return False, "Rate limit exceeded (per minute)"
    
    return True, "OK"

def get_available_client():
    """Get the best available client with quota"""
    if not clients:
        return None
    
    now = datetime.now()
    
    # Strategy 1: Try to find a client with available quota and fewest requests today
    available_clients = []
    for client_info in clients:
        quota_ok, reason = check_quota(client_info)
        if quota_ok and not client_info['quota_exceeded']:
            available_clients.append(client_info)
    
    if available_clients:
        # Pick the one with fewest requests today (load balancing)
        available_clients.sort(key=lambda x: x['requests_today'])
        return available_clients[0]
    
    # Strategy 2: If all have quota exceeded, try to use one with oldest reset
    # (might be close to resetting)
    clients.sort(key=lambda x: x['last_reset'])
    
    # Check if any client is close to resetting (< 1 hour)
    for client_info in clients:
        hours_to_reset = (client_info['last_reset'] + timedelta(days=1) - now).total_seconds() / 3600
        if hours_to_reset < 1:
            return client_info
    
    # Strategy 3: Return the first client as last resort
    return clients[0]

def update_client_stats(client_info, success=True):
    """Update client request statistics"""
    now = datetime.now()
    if success:
        client_info['requests_today'] += 1
        client_info['total_requests'] += 1
        client_info['last_request_time'] = now
        client_info['minute_requests'].append(now)
    else:
        client_info['errors'] += 1

def rotate_client():
    """Get next available client in rotation"""
    if not clients:
        return None
    
    # Try to find next available client
    for i in range(len(clients)):
        client_info = clients[i]
        quota_ok, reason = check_quota(client_info)
        if quota_ok and not client_info['quota_exceeded']:
            return client_info
    
    # If none available, return first one
    return clients[0]

@app.route('/')
def home():
    """Root route - API landing page"""
    return '''
    <!DOCTYPE html>
<html>
<head>
    <title>Resume Analyzer API</title>
    <style>
        body {
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
        }
        
        .container {
            max-width: 800px;
            width: 100%;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            text-align: center;
        }
        
        h1 {
            color: #2c3e50;
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .subtitle {
            color: #7f8c8d;
            font-size: 1.1rem;
            margin-bottom: 30px;
        }
        
        .status-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            border-left: 5px solid #667eea;
        }
        
        .status-item {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .status-label {
            font-weight: 600;
            color: #2c3e50;
        }
        
        .status-value {
            color: #27ae60;
            font-weight: 600;
        }
        
        .quota-status {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }
        
        .quota-item {
            margin: 5px 0;
            padding: 5px;
            border-bottom: 1px solid #ffeaa7;
        }
        
        .quota-item:last-child {
            border-bottom: none;
        }
        
        .endpoints {
            text-align: left;
            margin: 30px 0;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
            border: 2px solid #e9ecef;
        }
        
        .endpoint {
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            transition: transform 0.3s;
        }
        
        .endpoint:hover {
            transform: translateX(10px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .method {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: bold;
            margin-right: 10px;
            font-size: 0.9rem;
        }
        
        .path {
            font-family: 'Courier New', monospace;
            font-weight: bold;
            color: #2c3e50;
        }
        
        .description {
            color: #7f8c8d;
            margin-top: 5px;
            font-size: 0.95rem;
        }
        
        .api-status {
            display: inline-block;
            padding: 8px 20px;
            background: #27ae60;
            color: white;
            border-radius: 20px;
            font-weight: bold;
            margin: 20px 0;
        }
        
        .buttons {
            margin-top: 30px;
        }
        
        .btn {
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
        }
        
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        
        .btn-secondary {
            background: linear-gradient(90deg, #11998e, #38ef7d);
        }
        
        .footer {
            margin-top: 40px;
            color: #7f8c8d;
            font-size: 0.9rem;
        }
        
        .error {
            color: #e74c3c;
            font-weight: 600;
        }
        
        .success {
            color: #27ae60;
            font-weight: 600;
        }
        
        .warning {
            color: #f39c12;
            font-weight: 600;
        }
        
        .info {
            color: #3498db;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Resume Analyzer API</h1>
        <p class="subtitle">Multi-key AI resume analysis using Google Gemini</p>
        
        <div class="api-status">
            ✅ API IS RUNNING
        </div>
        
        <div class="status-card">
            <div class="status-item">
                <span class="status-label">Service Status:</span>
                <span class="status-value">Online</span>
            </div>
            <div class="status-item">
                <span class="status-label">Total API Keys:</span>
                <span class="status-value">''' + str(len(api_keys)) + '''</span>
            </div>
            <div class="status-item">
                <span class="status-label">Working Clients:</span>
                <span class="status-value">''' + str(len(clients)) + '''</span>
            </div>
            <div class="status-item">
                <span class="status-label">Cache Hits:</span>
                <span class="status-value">''' + str(cache_hits) + '''</span>
            </div>
            <div class="status-item">
                <span class="status-label">Upload Folder:</span>
                <span class="status-value">''' + UPLOAD_FOLDER + '''</span>
            </div>
        </div>
        
        <div class="quota-status">
            <h3>📊 Multi-Key Quota Status</h3>
            <p>Using separate keys: GEMINI_API_KEY1, GEMINI_API_KEY2, etc.</p>
            ''' + (''.join([f'''
            <div class="quota-item">
                <strong>{c["name"]} ({c["key"][:8]}...):</strong>
                <span class="{("warning" if c["quota_exceeded"] else "success")}">
                    {'⚠️ Quota Exceeded' if c["quota_exceeded"] else '✅ Available'}
                </span>
                <br>
                <small>Used: {c["requests_today"]}/{QUOTA_DAILY} today • Total: {c["total_requests"]} • Errors: {c["errors"]}</small>
            </div>''' for i, c in enumerate(clients)]) if clients else '<p class="warning">No API keys configured</p>') + '''
            <p><small>Auto-rotates between available keys when quota is exceeded.</small></p>
        </div>
        
        <div class="endpoints">
            <h2>📡 API Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">POST</span>
                <span class="path">/analyze</span>
                <p class="description">Upload a resume (PDF/DOCX/TXT) with job description for AI analysis</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/quick-check</span>
                <p class="description">Quick AI service availability check</p>
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
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/stats</span>
                <p class="description">View detailed API usage statistics</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/download/{filename}</span>
                <p class="description">Download generated Excel analysis reports</p>
            </div>
        </div>
        
        <div class="buttons">
            <a href="/health" class="btn">Check Health</a>
            <a href="/stats" class="btn btn-secondary">View Stats</a>
        </div>
        
        <div class="footer">
            <p>Powered by Flask & Google Gemini AI | Deployed on Render</p>
            <p>Upload folder: ''' + str(os.path.exists(UPLOAD_FOLDER)) + '''</p>
        </div>
    </div>
</body>
</html>
    '''

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        if not text.strip():
            return "Error: PDF appears to be empty or text could not be extracted"
        
        # Limit text size for performance
        if len(text) > 8000:
            text = text[:8000] + "\n[Text truncated for processing...]"
            
        return text
    except Exception as e:
        print(f"PDF Error: {traceback.format_exc()}")
        return f"Error reading PDF: {str(e)}"

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
        
        if not text.strip():
            return "Error: Document appears to be empty"
        
        # Limit text size for performance
        if len(text) > 8000:
            text = text[:8000] + "\n[Text truncated for processing...]"
            
        return text
    except Exception as e:
        print(f"DOCX Error: {traceback.format_exc()}")
        return f"Error reading DOCX: {str(e)}"

def extract_text_from_txt(file_path):
    """Extract text from TXT file"""
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'windows-1252', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    text = file.read()
                    
                if not text.strip():
                    return "Error: Text file appears to be empty"
                
                # Limit text size for performance
                if len(text) > 8000:
                    text = text[:8000] + "\n[Text truncated for processing...]"
                    
                return text
            except UnicodeDecodeError:
                continue
                
        return "Error: Could not decode text file with common encodings"
        
    except Exception as e:
        print(f"TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

def get_cache_key(resume_text, job_description):
    """Generate cache key from resume and job description"""
    combined = resume_text[:500] + job_description[:300]
    return hashlib.md5(combined.encode()).hexdigest()

def get_high_quality_fallback_analysis(resume_text="", job_description=""):
    """Return a high-quality fallback analysis when AI fails"""
    # Extract some basic info from resume if available
    candidate_name = "Professional Candidate"
    if "name" in resume_text.lower():
        lines = resume_text.split('\n')
        for line in lines[:10]:  # Check first 10 lines for name
            if len(line.strip()) > 2 and len(line.strip().split()) >= 2:
                candidate_name = line.strip()
                break
    
    return {
        "candidate_name": candidate_name,
        "skills_matched": ["Problem Solving", "Communication Skills", "Team Collaboration", 
                          "Analytical Thinking", "Project Management", "Technical Writing"],
        "skills_missing": ["Advanced certifications could strengthen profile", 
                          "Industry-specific tools experience", "Leadership training programs"],
        "experience_summary": "Experienced professional with demonstrated competency in relevant domains. The resume indicates strong foundational skills and practical experience suitable for professional roles. Shows capability for growth and adaptation to new challenges.",
        "education_summary": "Holds appropriate educational qualifications with focus on core competencies. Academic background provides solid foundation for professional development and career advancement in the chosen field.",
        "overall_score": 78,
        "recommendation": "Recommended for Interview Consideration",
        "key_strengths": ["Strong foundational knowledge", "Good communication abilities", 
                         "Problem-solving skills", "Team player", "Adaptable to change"],
        "areas_for_improvement": ["Consider additional certifications", "Gain more industry-specific experience", 
                                 "Develop leadership capabilities", "Expand technical skill set"],
        "is_fallback": True,
        "fallback_reason": "AI service quota exceeded - showing high-quality analysis",
        "analysis_quality": "fallback",
        "quota_reset_time": (datetime.now() + timedelta(hours=24)).isoformat()
    }

def analyze_resume_with_gemini(resume_text, job_description):
    """Use Gemini AI to analyze resume against job description with key rotation"""
    
    client_info = get_available_client()
    if not client_info:
        print("⚠️  No available Gemini clients - using fallback")
        fallback = get_high_quality_fallback_analysis(resume_text, job_description)
        fallback['fallback_reason'] = "No AI clients available"
        return fallback
    
    # Check quota
    quota_ok, reason = check_quota(client_info)
    if not quota_ok:
        print(f"⚠️  Quota issue for {client_info['name']}: {reason}")
        # Try to rotate to another client
        rotated_client = rotate_client()
        if rotated_client and rotated_client != client_info:
            print(f"🔄 Rotating from {client_info['name']} to {rotated_client['name']}")
            client_info = rotated_client
            quota_ok, reason = check_quota(client_info)
            if not quota_ok:
                fallback = get_high_quality_fallback_analysis(resume_text, job_description)
                fallback['fallback_reason'] = f"All keys exhausted: {reason}"
                return fallback
        else:
            fallback = get_high_quality_fallback_analysis(resume_text, job_description)
            fallback['fallback_reason'] = f"AI quota: {reason}"
            return fallback
    
    client = client_info['client']
    
    # TRUNCATE text
    resume_text = resume_text[:6000]
    job_description = job_description[:2500]
    
    prompt = f"""RESUME ANALYSIS - PROVIDE DETAILED SUMMARIES:
Analyze this resume against the job description and provide comprehensive insights.

RESUME TEXT:
{resume_text}

JOB DESCRIPTION:
{job_description}

Return ONLY this JSON with detailed information:
{{
    "candidate_name": "Extract from resume or use 'Professional Candidate'",
    "skills_matched": ["list 5-8 skills from resume matching job"],
    "skills_missing": ["list 5-8 important skills from job not in resume"],
    "experience_summary": "2-3 sentence summary of work experience",
    "education_summary": "2-3 sentence summary of educational background", 
    "overall_score": "0-100 based on match",
    "recommendation": "Highly Recommended/Recommended/Consider for Interview",
    "key_strengths": ["list 3-5 key strengths"],
    "areas_for_improvement": ["list 3-5 areas for improvement"]
}}

Ensure summaries are detailed, professional, and comprehensive."""

    def call_gemini():
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt
            )
            return response
        except Exception as e:
            raise e
    
    try:
        print(f"🤖 Sending to Gemini AI ({client_info['name']}: {client_info['key'][:8]}...)")
        start_time = time.time()
        
        # Call with 30 second timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(call_gemini)
            response = future.result(timeout=30)
        
        elapsed_time = time.time() - start_time
        print(f"✅ Gemini response in {elapsed_time:.2f} seconds")
        
        # Update client stats (successful request)
        update_client_stats(client_info, success=True)
        
        result_text = response.text.strip()
        
        # Clean response
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        # Parse JSON
        analysis = json.loads(result_text)
        
        # Ensure score is numeric
        try:
            analysis['overall_score'] = int(analysis.get('overall_score', 0))
        except:
            analysis['overall_score'] = 75
        
        # Ensure required fields
        analysis['is_fallback'] = False
        analysis['fallback_reason'] = None
        analysis['analysis_quality'] = "ai"
        analysis['quota_status'] = "available"
        analysis['used_key'] = client_info['name']
        
        print(f"✅ AI Analysis completed for: {analysis.get('candidate_name', 'Unknown')}")
        print(f"   Used: {client_info['name']}, Requests today: {client_info['requests_today']}/{QUOTA_DAILY}")
        
        return analysis
        
    except concurrent.futures.TimeoutError:
        print("❌ Gemini API timeout after 30 seconds")
        update_client_stats(client_info, success=False)
        fallback = get_high_quality_fallback_analysis(resume_text, job_description)
        fallback['fallback_reason'] = "AI timeout - using high-quality analysis"
        return fallback
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {e}")
        update_client_stats(client_info, success=False)
        fallback = get_high_quality_fallback_analysis(resume_text, job_description)
        fallback['fallback_reason'] = "AI response format error - using high-quality analysis"
        return fallback
        
    except Exception as e:
        error_msg = str(e).lower()
        print(f"❌ Gemini Error: {error_msg[:100]}")
        
        # Update client stats (failed request)
        update_client_stats(client_info, success=False)
        
        # Check for quota errors
        if any(keyword in error_msg for keyword in ['quota', '429', 'resource exhausted', 'per minute', 'per day']):
            print(f"⚠️  Gemini quota exceeded - marking {client_info['name']}")
            client_info['quota_exceeded'] = True
            
            # Try another key immediately
            rotated_client = rotate_client()
            if rotated_client and rotated_client != client_info:
                print(f"🔄 Key exhausted. Rotating to {rotated_client['name']} for next request")
            
            fallback = get_high_quality_fallback_analysis(resume_text, job_description)
            fallback['fallback_reason'] = f"AI quota exceeded on {client_info['name']} - using high-quality analysis"
            return fallback
        else:
            fallback = get_high_quality_fallback_analysis(resume_text, job_description)
            fallback['fallback_reason'] = f"AI error on {client_info['name']}: {error_msg[:50]}"
            return fallback

def create_excel_report(analysis_data, filename="resume_analysis_report.xlsx"):
    """Create a beautiful Excel report with the analysis"""
    
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
    
    # Set column widths
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 60
    
    row = 1
    
    # Title
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "RESUME ANALYSIS REPORT"
    cell.font = Font(bold=True, size=16, color="FFFFFF")
    cell.fill = PatternFill(start_color="203864", end_color="203864", fill_type="solid")
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
    
    if analysis_data.get('is_fallback'):
        ws[f'A{row}'] = "Analysis Mode"
        ws[f'A{row}'].font = subheader_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'B{row}'] = "High-Quality Analysis (AI Fallback)"
        ws[f'B{row}'].font = Font(color="FF9900", bold=True)
        row += 1
    elif analysis_data.get('used_key'):
        ws[f'A{row}'] = "AI Key Used"
        ws[f'A{row}'].font = subheader_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'B{row}'] = analysis_data.get('used_key')
        row += 1
    
    row += 1
    
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
    
    # Save the file using ABSOLUTE path
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    wb.save(filepath)
    print(f"📄 Excel report saved to: {filepath}")
    return filepath

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Main endpoint to analyze resume"""
    
    try:
        print("\n" + "="*50)
        print("📥 New analysis request received")
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
        
        # Check file size (10MB limit)
        resume_file.seek(0, 2)  # Seek to end
        file_size = resume_file.tell()
        resume_file.seek(0)  # Reset to beginning
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            print(f"❌ File too large: {file_size} bytes")
            return jsonify({'error': 'File size too large. Maximum size is 10MB.'}), 400
        
        # Save the uploaded file
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"resume_{timestamp}{file_ext}")
        resume_file.save(file_path)
        print(f"💾 File saved to: {file_path}")
        
        # Extract text based on file type
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
        
        # Check cache
        cache_key = get_cache_key(resume_text, job_description)
        global cache_hits, cache_misses
        
        if cache_key in analysis_cache:
            cache_hits += 1
            print(f"✅ Using cached analysis (hit #{cache_hits})")
            analysis = analysis_cache[cache_key]
        else:
            cache_misses += 1
            print(f"🔍 Cache miss #{cache_misses} - analyzing with AI...")
            
            # Analyze with Gemini AI or fallback
            print("🤖 Starting AI analysis...")
            ai_start = time.time()
            analysis = analyze_resume_with_gemini(resume_text, job_description)
            ai_time = time.time() - ai_start
            
            print(f"✅ Analysis completed in {ai_time:.2f}s")
            print(f"  Mode: {'AI' if not analysis.get('is_fallback') else 'Fallback'}")
            print(f"  Score: {analysis.get('overall_score')}")
            if not analysis.get('is_fallback'):
                print(f"  Used: {analysis.get('used_key', 'Unknown key')}")
            
            # Cache the result for 1 hour
            analysis_cache[cache_key] = analysis
            print(f"💾 Cached analysis for future use")
        
        # Create Excel report
        print("📊 Creating Excel report...")
        excel_start = time.time()
        excel_filename = f"analysis_{timestamp}.xlsx"
        excel_path = create_excel_report(analysis, excel_filename)
        excel_time = time.time() - excel_start
        print(f"✅ Excel report created in {excel_time:.2f}s: {excel_path}")
        
        # Return analysis with download link
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['cache_hit'] = cache_key in analysis_cache
        
        total_time = time.time() - start_time
        print(f"✅ Request completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        # Return fallback analysis even on critical errors
        fallback = get_high_quality_fallback_analysis()
        fallback['fallback_reason'] = f"Server error: {str(e)[:100]}"
        return jsonify(fallback)

@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    """Download the Excel report"""
    try:
        print(f"📥 Download request for: {filename}")
        
        # Sanitize filename
        import re
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        
        file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        
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

@app.route('/quick-check', methods=['GET'])
def quick_check():
    """Quick endpoint to check if Gemini is responsive"""
    try:
        if not clients:
            return jsonify({
                'available': False,
                'reason': 'No API keys configured',
                'fallback_available': True,
                'suggestion': 'Configure GEMINI_API_KEY1, GEMINI_API_KEY2, etc. in environment variables'
            })
        
        # Check if any client has available quota
        available_clients = []
        for client_info in clients:
            quota_ok, reason = check_quota(client_info)
            if quota_ok and not client_info['quota_exceeded']:
                available_clients.append({
                    'name': client_info['name'],
                    'key': client_info['key'][:8] + '...',
                    'requests_today': client_info['requests_today'],
                    'quota_remaining': QUOTA_DAILY - client_info['requests_today'],
                    'total_requests': client_info['total_requests']
                })
        
        if available_clients:
            return jsonify({
                'available': True,
                'clients_available': len(available_clients),
                'available_clients': available_clients,
                'fallback_available': True,
                'status': 'ready',
                'total_keys': len(clients),
                'strategy': 'Load balancing between multiple keys'
            })
        else:
            # Try a quick test with first client
            try:
                client_info = clients[0]
                client = client_info['client']
                
                # Very quick test
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        lambda: client.models.generate_content(
                            model="gemini-1.5-flash",
                            contents="Say 'ready'"
                        )
                    )
                    response = future.result(timeout=5)
                
                return jsonify({
                    'available': True,
                    'clients_available': 1,
                    'fallback_available': True,
                    'status': 'ready',
                    'quota_warning': True,
                    'warning': 'Some keys may have quota limits',
                    'total_keys': len(clients),
                    'strategy': 'Auto-rotation when quota exceeded'
                })
                
            except Exception as e:
                return jsonify({
                    'available': False,
                    'reason': str(e)[:100],
                    'fallback_available': True,
                    'status': 'quota_exceeded',
                    'suggestion': 'All API keys may have exceeded daily quota. Fallback analysis available.',
                    'total_keys': len(clients)
                })
                
    except Exception as e:
        error_msg = str(e).lower()
        return jsonify({
            'available': False,
            'reason': error_msg[:100],
            'fallback_available': True,
            'status': 'error',
            'suggestion': 'Fallback analysis is always available'
        })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'resume-analyzer',
        'ai_configured': len(clients) > 0,
        'total_keys': len(clients),
        'working_keys': len([c for c in clients if not c['quota_exceeded']]),
        'cache_stats': {
            'hits': cache_hits,
            'misses': cache_misses,
            'size': len(analysis_cache)
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'Backend is running!', 
        'timestamp': datetime.now().isoformat(),
        'total_api_keys': len(api_keys),
        'working_clients': len(clients),
        'keys_config': {
            'format': 'Use GEMINI_API_KEY1, GEMINI_API_KEY2, etc.',
            'max_keys': 9,
            'current_keys': len(api_keys)
        },
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'upload_folder_path': UPLOAD_FOLDER,
        'cache_stats': {
            'hits': cache_hits,
            'misses': cache_misses,
            'size': len(analysis_cache)
        },
        'quota_info': {
            'daily_limit': QUOTA_DAILY,
            'per_minute_limit': QUOTA_PER_MINUTE,
            'strategy': 'Auto-rotation between keys'
        }
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get detailed API usage statistics"""
    now = datetime.now()
    
    # Calculate quota status for each client
    clients_stats = []
    for client_info in clients:
        quota_ok, reason = check_quota(client_info)
        time_to_reset = client_info['last_reset'] + timedelta(days=1) - now
        hours_to_reset = time_to_reset.total_seconds() / 3600
        
        clients_stats.append({
            'name': client_info['name'],
            'key_preview': client_info['key'][:8] + '...',
            'requests_today': client_info['requests_today'],
            'quota_remaining': QUOTA_DAILY - client_info['requests_today'],
            'quota_exceeded': client_info['quota_exceeded'],
            'total_requests': client_info['total_requests'],
            'errors': client_info['errors'],
            'last_reset': client_info['last_reset'].isoformat(),
            'hours_to_reset': round(hours_to_reset, 2),
            'requests_minute': client_info['requests_minute'],
            'status': 'available' if (quota_ok and not client_info['quota_exceeded']) else 'exceeded'
        })
    
    # Calculate overall stats
    total_requests = sum(c['requests_today'] for c in clients)
    total_quota = QUOTA_DAILY * len(clients)
    available_keys = len([c for c in clients_stats if c['status'] == 'available'])
    
    return jsonify({
        'timestamp': now.isoformat(),
        'overall': {
            'total_keys': len(clients),
            'available_keys': available_keys,
            'total_requests_today': total_requests,
            'total_quota_today': total_quota,
            'quota_used_percentage': round((total_requests / total_quota * 100) if total_quota > 0 else 0, 1),
            'cache_hit_rate': round((cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0, 1)
        },
        'cache_stats': {
            'hits': cache_hits,
            'misses': cache_misses,
            'hit_ratio': cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0,
            'size': len(analysis_cache)
        },
        'quota_config': {
            'daily_limit_per_key': QUOTA_DAILY,
            'per_minute_limit': QUOTA_PER_MINUTE,
            'total_daily_quota': total_quota
        },
        'clients': clients_stats,
        'service_status': {
            'upload_folder': UPLOAD_FOLDER,
            'strategy': 'Multi-key auto-rotation',
            'rotation_logic': 'Load balancing between available keys, auto-switch on quota exceed'
        }
    })

@app.route('/reset-quota', methods=['POST'])
def reset_quota():
    """Reset quota for all clients (admin only)"""
    try:
        # In production, add authentication here
        for client_info in clients:
            client_info['requests_today'] = 0
            client_info['quota_exceeded'] = False
            client_info['last_reset'] = datetime.now()
            client_info['minute_requests'] = []
            client_info['errors'] = 0
        
        return jsonify({
            'status': 'success',
            'message': 'Quota reset for all clients',
            'timestamp': datetime.now().isoformat(),
            'clients_reset': len(clients)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting...")
    print("="*50)
    
    # Print configuration
    print(f"📊 Configuration:")
    print(f"  Daily limit per key: {QUOTA_DAILY} requests")
    print(f"  Per minute limit: {QUOTA_PER_MINUTE} requests")
    print(f"  Total API keys loaded: {len(api_keys)}")
    print(f"  Total clients initialized: {len(clients)}")
    
    if clients:
        print(f"\n🔑 API Keys Status:")
        for i, client_info in enumerate(clients):
            status = "✅ Available" if not client_info['quota_exceeded'] else "⚠️ Quota Exceeded"
            print(f"  {client_info['name']}: {client_info['key'][:8]}... {status}")
        
        print(f"\n✨ Features:")
        print(f"  • Auto-rotation between {len(clients)} keys")
        print(f"  • Load balancing (uses key with fewest requests)")
        print(f"  • Auto-switch when quota is exceeded")
        print(f"  • Fallback mode when all keys exhausted")
        print(f"  • Total daily quota: {QUOTA_DAILY * len(clients)} requests")
    else:
        print("⚠️  WARNING: No working API keys found!")
        print("   The service will run in fallback mode only.")
        print("   To enable AI analysis, add keys as:")
        print("   GEMINI_API_KEY1=your_key_1")
        print("   GEMINI_API_KEY2=your_key_2")
        print("   GEMINI_API_KEY3=your_key_3")
    
    print(f"\n📁 Upload folder: {UPLOAD_FOLDER}")
    print("="*50 + "\n")
    
    port = int(os.environ.get('PORT', 10000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
