from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google import genai
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
import random

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

print("=" * 50)
print("🔍 Checking for API keys...")

# Configure Gemini AI - Try multiple keys
api_keys = []
clients = []

# Check for individual keys (KEY1, KEY2, KEY3)
for i in range(1, 4):  # Check KEY1, KEY2, KEY3
    key = os.getenv(f'GEMINI_API_KEY{i}', '').strip()
    if key and len(key) > 10:  # Basic validation
        api_keys.append(key)
        print(f"✅ Found GEMINI_API_KEY{i}: {key[:8]}...")

# Also check for single key (backward compatibility)
single_key = os.getenv('GEMINI_API_KEY', '').strip()
if single_key and len(single_key) > 10:
    api_keys.append(single_key)
    print(f"✅ Found GEMINI_API_KEY: {single_key[:8]}...")

# Initialize clients with all valid keys
for i, key in enumerate(api_keys):
    try:
        print(f"🔄 Initializing client for Key {i+1}...")
        client = genai.Client(api_key=key)
        
        # Test the client
        test_response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents="Say 'OK'"
        )
        
        if test_response and hasattr(test_response, 'text'):
            clients.append({
                'client': client,
                'key': key,
                'name': f"Key {i+1}",
                'requests': 0,
                'errors': 0,
                'last_used': None,
                'status': 'active'
            })
            print(f"  ✅ Key {i+1} initialized successfully")
        else:
            print(f"  ⚠️  Key {i+1} failed test response")
            
    except Exception as e:
        print(f"  ❌ Key {i+1} initialization failed: {str(e)[:100]}")

print(f"\n📊 Summary: {len(api_keys)} keys found, {len(clients)} clients initialized")

# Get absolute path for uploads folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"📁 Upload folder: {UPLOAD_FOLDER}")

def get_available_client():
    """Get an available Gemini client, rotating through available keys"""
    if not clients:
        return None
    
    # Try to find a client with no recent errors
    active_clients = [c for c in clients if c['status'] == 'active']
    
    if not active_clients:
        # If all clients have errors, try the one with fewest errors
        clients.sort(key=lambda x: x['errors'])
        return clients[0]['client']
    
    # Use round-robin: pick client with fewest requests
    active_clients.sort(key=lambda x: x['requests'])
    selected_client = active_clients[0]
    
    # Update stats
    selected_client['requests'] += 1
    selected_client['last_used'] = datetime.now()
    
    print(f"🤖 Using {selected_client['name']} (Requests: {selected_client['requests']}, Errors: {selected_client['errors']})")
    return selected_client['client']

def mark_client_error(client_name):
    """Mark a client as having an error"""
    for client in clients:
        if client['name'] == client_name:
            client['errors'] += 1
            # If too many errors, mark as inactive temporarily
            if client['errors'] > 3:
                client['status'] = 'inactive'
                print(f"⚠️  Marked {client_name} as inactive due to too many errors")
            break

def reset_inactive_clients():
    """Reset inactive clients after some time"""
    for client in clients:
        if client['status'] == 'inactive' and client['errors'] > 0:
            # Reset errors after 5 minutes
            if client['last_used']:
                time_diff = (datetime.now() - client['last_used']).total_seconds()
                if time_diff > 300:  # 5 minutes
                    client['errors'] = 0
                    client['status'] = 'active'
                    print(f"✅ Reset {client['name']} to active")

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
        
        .client-status {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }
        
        .client-item {
            margin: 5px 0;
            padding: 5px;
            border-bottom: 1px solid #ffeaa7;
        }
        
        .client-item:last-child {
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
                <span class="status-label">Total API Keys Found:</span>
                <span class="status-value">''' + str(len(api_keys)) + '''</span>
            </div>
            <div class="status-item">
                <span class="status-label">Active Clients:</span>
                <span class="status-value">''' + str(len([c for c in clients if c['status'] == 'active'])) + '''</span>
            </div>
            <div class="status-item">
                <span class="status-label">Upload Folder:</span>
                <span class="status-value">''' + UPLOAD_FOLDER + '''</span>
            </div>
        </div>
        
        <div class="client-status">
            <h3>🔑 API Key Status</h3>
            ''' + (''.join([f'''
            <div class="client-item">
                <strong>{c["name"]} ({c["key"][:8]}...):</strong>
                <span class="{("error" if c["status"] == "inactive" else "success")}">
                    {'⚠️ Inactive' if c["status"] == 'inactive' else '✅ Active'}
                </span>
                <br>
                <small>Requests: {c["requests"]} • Errors: {c["errors"]} • Last Used: {c["last_used"].strftime("%H:%M:%S") if c["last_used"] else "Never"}</small>
            </div>''' for c in clients]) if clients else '<p class="warning">No API clients configured</p>') + '''
            <p><small>Keys rotate automatically • Inactive keys auto-reset after 5 minutes</small></p>
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
                <span class="path">/health</span>
                <p class="description">Check API health status and configuration</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/stats</span>
                <p class="description">View API key usage statistics</p>
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
            <p>Supports multiple API keys (GEMINI_API_KEY1, GEMINI_API_KEY2, GEMINI_API_KEY3)</p>
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
            text += page.extract_text()
        if not text.strip():
            return "Error: PDF appears to be empty or text could not be extracted"
        return text
    except Exception as e:
        print(f"PDF Error: {traceback.format_exc()}")
        return f"Error reading PDF: {str(e)}"

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        if not text.strip():
            return "Error: Document appears to be empty"
        return text
    except Exception as e:
        print(f"DOCX Error: {traceback.format_exc()}")
        return f"Error reading DOCX: {str(e)}"

def extract_text_from_txt(file_path):
    """Extract text from TXT file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        if not text.strip():
            return "Error: Text file appears to be empty"
        return text
    except Exception as e:
        print(f"TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

def analyze_resume_with_gemini(resume_text, job_description, client_name="Unknown"):
    """Use Gemini AI to analyze resume against job description"""
    
    client = get_available_client()
    
    if client is None:
        print("❌ No available Gemini clients. Check API keys.")
        return {
            "candidate_name": "API Error",
            "skills_matched": [],
            "skills_missing": [],
            "experience_summary": "Gemini API not available. Check your API keys.",
            "education_summary": "Please ensure GEMINI_API_KEY1, KEY2, or KEY3 are set",
            "overall_score": 0,
            "recommendation": "Configuration Error",
            "key_strengths": [],
            "areas_for_improvement": [],
            "used_key": "None"
        }
    
    prompt = f"""ANALYSIS INSTRUCTIONS:
1. Read the resume carefully
2. Extract ALL information ONLY from the provided resume text
3. DO NOT use any external knowledge or assumptions
4. If information is missing from resume, acknowledge it's missing

RESUME TEXT TO ANALYZE:
{resume_text[:8000]}

JOB DESCRIPTION:
{job_description[:4000]}

IMPORTANT: Extract the candidate name from the resume. If no name is found, use "Unknown Candidate".

Return ONLY this JSON format with analysis based SOLELY on the provided resume:
{{
    "candidate_name": "Name extracted from resume or 'Unknown Candidate'",
    "skills_matched": ["list actual skills from resume that match job"],
    "skills_missing": ["list skills from job not found in resume"],
    "experience_summary": "1-2 sentence summary of experience from resume",
    "education_summary": "1-2 sentence summary of education from resume",
    "overall_score": 0-100 based on match percentage,
    "recommendation": "Highly Recommended/Recommended/Not Recommended",
    "key_strengths": ["strengths evident from resume"],
    "areas_for_improvement": ["areas to improve based on resume gaps"]
}}"""

    try:
        print(f"🤖 Sending to Gemini AI using {client_name}...")
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        
        result_text = response.text.strip()
        
        # Clean response
        if '```json' in result_text:
            result_text = result_text.replace('```json', '').replace('```', '').strip()
        elif '```' in result_text:
            result_text = result_text.replace('```', '').strip()
        
        # Parse JSON
        analysis = json.loads(result_text)
        print(f"✅ Analysis received for: {analysis.get('candidate_name', 'Unknown')}")
        
        # Add which key was used
        analysis['used_key'] = client_name
        
        # Validate required fields
        required_fields = [
            'candidate_name', 'skills_matched', 'skills_missing',
            'experience_summary', 'education_summary', 'overall_score',
            'recommendation', 'key_strengths', 'areas_for_improvement'
        ]
        
        for field in required_fields:
            if field not in analysis:
                if 'skill' in field or 'strength' in field or 'improvement' in field:
                    analysis[field] = []
                else:
                    analysis[field] = "Information not found in resume"
        
        return analysis
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON Error: {e}")
        mark_client_error(client_name)
        return {
            "candidate_name": "Parse Error",
            "skills_matched": ["JSON parsing failed"],
            "skills_missing": [],
            "experience_summary": "Error parsing AI response",
            "education_summary": "Please try again",
            "overall_score": 0,
            "recommendation": "Error - Retry analysis",
            "key_strengths": [],
            "areas_for_improvement": [],
            "used_key": client_name
        }
    except Exception as e:
        print(f"❌ Gemini Error: {str(e)[:100]}")
        mark_client_error(client_name)
        return {
            "candidate_name": "API Error",
            "skills_matched": [],
            "skills_missing": [],
            "experience_summary": f"API Error: {str(e)[:50]}",
            "education_summary": "Check API configuration",
            "overall_score": 0,
            "recommendation": "Error occurred",
            "key_strengths": [],
            "areas_for_improvement": [],
            "used_key": client_name
        }

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
    
    if 'used_key' in analysis_data:
        ws[f'A{row}'] = "API Key Used"
        ws[f'A{row}'].font = subheader_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'B{row}'] = analysis_data.get('used_key', 'Unknown')
        row += 1
    
    row += 1
    
    # Overall Score
    ws[f'A{row}'] = "Overall Match Score"
    ws[f'A{row}'].font = Font(bold=True, size=12)
    ws[f'A{row}'].fill = header_fill
    ws[f'A{row}'].font = Font(bold=True, size=12, color="FFFFFF")
    score = analysis_data.get('overall_score', 0)
    ws[f'B{row}'] = f"{score}/100"
    if score < 60:
        score_color = "C00000"  # Red
    elif score >= 80:
        score_color = "70AD47"  # Green
    else:
        score_color = "FFC000"  # Yellow
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
        
        # Reset inactive clients
        reset_inactive_clients()
        
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
        
        print(f"✅ Extracted {len(resume_text)} characters from resume")
        
        # Check if any API keys are configured
        if not api_keys:
            print("❌ No API keys configured")
            return jsonify({'error': 'No API keys configured. Please add GEMINI_API_KEY1, KEY2, or KEY3 to environment variables'}), 500
        
        if not clients:
            print("❌ No Gemini clients initialized")
            return jsonify({'error': 'Gemini AI clients not properly initialized. Check API keys.'}), 500
        
        # Get current client name for tracking
        current_client_name = None
        for c in clients:
            if c['status'] == 'active':
                current_client_name = c['name']
                break
        
        if not current_client_name:
            current_client_name = clients[0]['name'] if clients else "Unknown"
        
        # Analyze with Gemini AI
        print(f"🤖 Starting AI analysis with {current_client_name}...")
        analysis = analyze_resume_with_gemini(resume_text, job_description, current_client_name)
        
        print(f"✅ Analysis completed. Score: {analysis.get('overall_score', 0)}")
        print(f"🔍 AI Analysis Result:")
        print(f"  Name: {analysis.get('candidate_name')}")
        print(f"  Score: {analysis.get('overall_score')}")
        print(f"  Matched Skills: {len(analysis.get('skills_matched', []))}")
        print(f"  Missing Skills: {len(analysis.get('skills_missing', []))}")
        print(f"  Used Key: {analysis.get('used_key', 'Unknown')}")
        
        # Create Excel report
        print("📊 Creating Excel report...")
        excel_filename = f"analysis_{timestamp}.xlsx"
        excel_path = create_excel_report(analysis, excel_filename)
        print(f"✅ Excel report created: {excel_path}")
        
        # Return analysis with download link
        analysis['excel_filename'] = os.path.basename(excel_path)
        
        print("✅ Request completed successfully")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    """Download the Excel report"""
    try:
        print(f"📥 Download request for: {filename}")
        print(f"📁 Upload folder path: {UPLOAD_FOLDER}")
        
        # Sanitize filename
        import re
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        
        file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        
        print(f"🔍 Looking for file at: {file_path}")
        print(f"📁 Upload folder exists: {os.path.exists(UPLOAD_FOLDER)}")
        
        if not os.path.exists(UPLOAD_FOLDER):
            print(f"❌ Upload folder doesn't exist: {UPLOAD_FOLDER}")
            return jsonify({'error': 'Upload folder not found'}), 500
            
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            # List available files
            available_files = os.listdir(UPLOAD_FOLDER)
            print(f"📂 Available files in {UPLOAD_FOLDER}: {available_files}")
            return jsonify({'error': f'File not found. Available files: {available_files}'}), 404
        
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

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    active_clients = [c for c in clients if c['status'] == 'active']
    
    return jsonify({
        'status': 'Backend is running!', 
        'timestamp': datetime.now().isoformat(),
        'total_api_keys': len(api_keys),
        'active_clients': len(active_clients),
        'total_clients': len(clients),
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'upload_folder_path': UPLOAD_FOLDER,
        'clients': [
            {
                'name': c['name'],
                'status': c['status'],
                'requests': c['requests'],
                'errors': c['errors'],
                'last_used': c['last_used'].isoformat() if c['last_used'] else None
            }
            for c in clients
        ]
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get detailed API usage statistics"""
    active_clients = [c for c in clients if c['status'] == 'active']
    total_requests = sum(c['requests'] for c in clients)
    total_errors = sum(c['errors'] for c in clients)
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_api_keys': len(api_keys),
            'active_clients': len(active_clients),
            'inactive_clients': len(clients) - len(active_clients),
            'total_requests': total_requests,
            'total_errors': total_errors,
            'success_rate': round((total_requests - total_errors) / total_requests * 100, 2) if total_requests > 0 else 0
        },
        'clients': [
            {
                'name': c['name'],
                'key_preview': c['key'][:8] + '...',
                'status': c['status'],
                'requests': c['requests'],
                'errors': c['errors'],
                'error_rate': round(c['errors'] / c['requests'] * 100, 2) if c['requests'] > 0 else 0,
                'last_used': c['last_used'].isoformat() if c['last_used'] else 'Never',
                'is_active': c['status'] == 'active'
            }
            for c in clients
        ]
    })

@app.route('/reset-clients', methods=['POST'])
def reset_clients():
    """Reset all clients (admin function)"""
    try:
        for client in clients:
            client['errors'] = 0
            client['status'] = 'active'
            print(f"✅ Reset {client['name']}")
        
        return jsonify({
            'status': 'success',
            'message': 'All clients reset to active',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting...")
    print("="*50)
    
    port = int(os.environ.get('PORT', 5002))
    
    print(f"📍 Server: http://localhost:{port}")
    print(f"🔑 API Keys Found: {len(api_keys)}")
    print(f"🤖 Clients Initialized: {len(clients)}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    
    if not api_keys:
        print("⚠️  WARNING: No API keys found!")
        print("Please set environment variables:")
        print("  GEMINI_API_KEY1=your_key_here")
        print("  GEMINI_API_KEY2=your_key_here")
        print("  GEMINI_API_KEY3=your_key_here")
        print("\nGet your API keys from: https://makersuite.google.com/app/apikey")
    
    print("="*50 + "\n")
    
    # Use PORT environment variable (Render provides $PORT)
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
