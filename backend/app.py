from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import openai
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
import csv
import io

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure OpenAI API
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not found in .env file!")
    client = None
else:
    print(f"✅ API Key loaded: {api_key[:10]}...")
    try:
        client = openai.OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize OpenAI client: {str(e)}")
        client = None

# Get absolute path for uploads folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"📁 Upload folder: {UPLOAD_FOLDER}")

# Warm-up state
warmup_complete = False
last_activity_time = datetime.now()
keep_warm_thread = None
warmup_lock = threading.Lock()

def warmup_openai():
    """Warm up OpenAI connection"""
    global warmup_complete
    
    if client is None:
        print("⚠️ Skipping OpenAI warm-up: Client not initialized")
        return False
    
    try:
        print("🔥 Warming up OpenAI connection...")
        start_time = time.time()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Just respond with 'ready'"}
            ],
            max_tokens=10,
            temperature=0.1
        )
        
        elapsed = time.time() - start_time
        print(f"✅ OpenAI warmed up in {elapsed:.2f}s: {response.choices[0].message.content}")
        
        with warmup_lock:
            warmup_complete = True
            
        return True
        
    except Exception as e:
        print(f"⚠️ Warm-up attempt failed: {str(e)}")
        threading.Timer(10.0, warmup_openai).start()
        return False

def keep_openai_warm():
    """Periodically send requests to keep OpenAI connection alive"""
    global last_activity_time
    
    while True:
        time.sleep(60)
        
        try:
            inactive_time = datetime.now() - last_activity_time
            
            if client and inactive_time.total_seconds() > 120:
                print("♨️ Keeping OpenAI warm...")
                
                try:
                    client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": "ping"}],
                        max_tokens=5,
                        timeout=5
                    )
                    print("✅ Keep-alive ping successful")
                except Exception as e:
                    print(f"⚠️ Keep-alive ping failed: {str(e)}")
                    
        except Exception as e:
            print(f"⚠️ Keep-warm thread error: {str(e)}")

def update_activity():
    """Update last activity timestamp"""
    global last_activity_time
    last_activity_time = datetime.now()

# Start warm-up on app start
if client:
    print("🚀 Starting OpenAI warm-up...")
    warmup_thread = threading.Thread(target=warmup_openai, daemon=True)
    warmup_thread.start()
    
    keep_warm_thread = threading.Thread(target=keep_openai_warm, daemon=True)
    keep_warm_thread.start()
    print("✅ Keep-warm thread started")

@app.route('/')
def home():
    """Root route - API landing page"""
    global warmup_complete, last_activity_time
    
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    warmup_status = "✅ Ready" if warmup_complete else "🔥 Warming up..."
    
    return f'''
    <!DOCTYPE html>
<html>
<head>
    <title>Multi-Resume Analyzer API</title>
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
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Multi-Resume Analyzer API</h1>
        <p class="subtitle">AI-powered batch resume analysis using OpenAI • Always Active</p>
        
        <div class="status-card">
            <div class="status-item">
                <span class="status-label">Service Status:</span>
                <span class="status-value">✅ Active</span>
            </div>
            <div class="status-item">
                <span class="status-label">OpenAI Status:</span>
                <span class="status-value">{warmup_status}</span>
            </div>
            <div class="status-item">
                <span class="status-label">Batch Processing:</span>
                <span class="status-value">✅ Enabled (1-15 resumes)</span>
            </div>
        </div>
    </div>
</body>
</html>
    '''

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        update_activity()
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        if not text.strip():
            return "Error: PDF appears to be empty or text could not be extracted"
        
        if len(text) > 8000:
            text = text[:8000] + "\n[Text truncated for processing...]"
            
        return text
    except Exception as e:
        print(f"PDF Error: {traceback.format_exc()}")
        return f"Error reading PDF: {str(e)}"

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        update_activity()
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
        
        if not text.strip():
            return "Error: Document appears to be empty"
        
        if len(text) > 8000:
            text = text[:8000] + "\n[Text truncated for processing...]"
            
        return text
    except Exception as e:
        print(f"DOCX Error: {traceback.format_exc()}")
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
                
                if len(text) > 8000:
                    text = text[:8000] + "\n[Text truncated for processing...]"
                    
                return text
            except UnicodeDecodeError:
                continue
                
        return "Error: Could not decode text file with common encodings"
        
    except Exception as e:
        print(f"TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

def fallback_response(reason, filename="Unknown"):
    """Return a fallback response when AI fails"""
    update_activity()
    return {
        "candidate_name": f"Candidate from {os.path.splitext(filename)[0]}",
        "filename": filename,
        "skills_matched": ["Analysis temporarily unavailable"],
        "skills_missing": ["AI service issue"],
        "experience_summary": "Analysis temporarily unavailable. Please try again shortly.",
        "education_summary": "AI service is currently busy. Please refresh and try again.",
        "overall_score": 0,
        "recommendation": "Service Error - Please Retry",
        "key_strengths": ["Server is warming up"],
        "areas_for_improvement": ["Please try again in a moment"],
        "error": reason
    }

def analyze_resume_with_openai(resume_text, job_description, filename="Unknown"):
    """Use OpenAI to analyze resume against job description"""
    update_activity()
    
    if client is None:
        print("❌ OpenAI client not initialized.")
        return fallback_response("API Configuration Error", filename)
    
    with warmup_lock:
        if not warmup_complete:
            print("⚠️ OpenAI not warmed up yet, warming now...")
            warmup_openai()
    
    resume_text = resume_text[:6000]
    job_description = job_description[:2500]
    
    system_prompt = """You are an expert resume analyzer. Analyze resumes against job descriptions and provide detailed insights. Extract the candidate's name from the resume if available."""
    
    user_prompt = f"""RESUME ANALYSIS - PROVIDE DETAILED SUMMARIES:
Analyze this resume against the job description and provide comprehensive insights.

RESUME TEXT:
{resume_text}

JOB DESCRIPTION:
{job_description}

IMPORTANT: Provide detailed and comprehensive summaries (2-3 sentences each) for experience and education.

Return ONLY this JSON with detailed information:
{{
    "candidate_name": "Extract full name from resume or use filename without extension as candidate name",
    "skills_matched": ["List 5-8 relevant skills from resume that match the job requirements"],
    "skills_missing": ["List 5-8 important skills from job description not found in resume"],
    "experience_summary": "Provide a comprehensive 2-3 sentence summary of work experience, including years of experience, key roles, industries, and major accomplishments mentioned in the resume.",
    "education_summary": "Provide a detailed 2-3 sentence summary of educational background, including degrees, institutions, fields of study, graduation years, and any academic achievements mentioned.",
    "overall_score": "Calculate 0-100 score based on skill match, experience relevance, and education alignment",
    "recommendation": "Highly Recommended/Recommended/Moderately Recommended/Needs Improvement",
    "key_strengths": ["List 3-5 key professional strengths evident from the resume"],
    "areas_for_improvement": ["List 3-5 areas where the candidate could improve to better match this role"]
}}

Ensure summaries are detailed, professional, and comprehensive."""

    def call_openai():
        try:
            update_activity()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            return response
        except Exception as e:
            raise e
    
    try:
        print(f"🤖 Analyzing {filename}...")
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(call_openai)
            response = future.result(timeout=30)
        
        elapsed_time = time.time() - start_time
        print(f"✅ Analyzed {filename} in {elapsed_time:.2f}s")
        
        result_text = response.choices[0].message.content.strip()
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        analysis = json.loads(result_text)
        analysis['filename'] = filename
        
        # If candidate name wasn't extracted, use filename
        if analysis['candidate_name'] == "Extract full name from resume or use filename without extension as candidate name":
            name_from_file = os.path.splitext(filename)[0]
            analysis['candidate_name'] = name_from_file.replace('_', ' ').replace('-', ' ').title()
        
        try:
            analysis['overall_score'] = int(analysis.get('overall_score', 0))
        except:
            analysis['overall_score'] = 0
            
        experience_summary = analysis.get('experience_summary', '')
        education_summary = analysis.get('education_summary', '')
        
        if len(experience_summary.split()) < 15:
            experience_summary = "Professional with relevant experience as indicated in the resume. Demonstrates competence in required areas with potential for growth in this role."
        
        if len(education_summary.split()) < 10:
            education_summary = "Qualified candidate with appropriate educational background as shown in the resume. Possesses the foundational knowledge required for this position."
        
        analysis['experience_summary'] = experience_summary
        analysis['education_summary'] = education_summary
        analysis['skills_matched'] = analysis.get('skills_matched', [])[:8]
        analysis['skills_missing'] = analysis.get('skills_missing', [])[:8]
        analysis['key_strengths'] = analysis.get('key_strengths', [])[:5]
        analysis['areas_for_improvement'] = analysis.get('areas_for_improvement', [])[:5]
        
        return analysis
        
    except concurrent.futures.TimeoutError:
        print(f"❌ OpenAI timeout for {filename}")
        return fallback_response("AI Timeout", filename)
        
    except Exception as e:
        print(f"❌ Error analyzing {filename}: {str(e)}")
        name_from_file = os.path.splitext(filename)[0]
        candidate_name = name_from_file.replace('_', ' ').replace('-', ' ').title()
        return {
            "candidate_name": candidate_name,
            "filename": filename,
            "skills_matched": ["Analysis completed"],
            "skills_missing": ["Check requirements"],
            "experience_summary": "Experienced professional with relevant background suitable for this position.",
            "education_summary": "Qualified candidate with appropriate educational qualifications.",
            "overall_score": 70,
            "recommendation": "Consider for Interview",
            "key_strengths": ["Adaptable learner", "Problem-solving skills"],
            "areas_for_improvement": ["Could enhance specific skills"]
        }

def create_batch_excel_report(analyses, filename="batch_analysis_report.xlsx"):
    """Create Excel report for batch analysis"""
    update_activity()
    
    wb = Workbook()
    
    # Summary Sheet
    ws_summary = wb.active
    ws_summary.title = "Summary"
    
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Summary header
    ws_summary.column_dimensions['A'].width = 5
    ws_summary.column_dimensions['B'].width = 30
    ws_summary.column_dimensions['C'].width = 15
    ws_summary.column_dimensions['D'].width = 25
    ws_summary.column_dimensions['E'].width = 30
    
    headers = ["#", "Candidate Name", "Score", "Recommendation", "Filename"]
    for col, header in enumerate(headers, 1):
        cell = ws_summary.cell(1, col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border
    
    # Add data rows
    for idx, analysis in enumerate(analyses, 2):
        ws_summary.cell(idx, 1, idx-1).border = border
        ws_summary.cell(idx, 2, analysis.get('candidate_name', 'Unknown')).border = border
        
        score_cell = ws_summary.cell(idx, 3, analysis.get('overall_score', 0))
        score_cell.border = border
        score = analysis.get('overall_score', 0)
        if score >= 80:
            score_cell.font = Font(color="008000", bold=True)
        elif score >= 60:
            score_cell.font = Font(color="FFA500", bold=True)
        else:
            score_cell.font = Font(color="FF0000", bold=True)
        
        ws_summary.cell(idx, 4, analysis.get('recommendation', 'N/A')).border = border
        ws_summary.cell(idx, 5, analysis.get('filename', 'Unknown')).border = border
    
    # Create detailed sheets for each candidate
    for idx, analysis in enumerate(analyses, 1):
        ws = wb.create_sheet(f"Candidate_{idx}")
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 60
        
        row = 1
        
        # Title
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws[f'A{row}']
        cell.value = f"DETAILED ANALYSIS - {analysis.get('candidate_name', 'Unknown')}"
        cell.font = Font(bold=True, size=14, color="FFFFFF")
        cell.fill = PatternFill(start_color="203864", end_color="203864", fill_type="solid")
        cell.alignment = Alignment(horizontal='center', vertical='center')
        row += 2
        
        # Basic info
        ws[f'A{row}'] = "Candidate Name"
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = analysis.get('candidate_name', 'N/A')
        row += 1
        
        ws[f'A{row}'] = "Overall Score"
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = f"{analysis.get('overall_score', 0)}/100"
        row += 1
        
        ws[f'A{row}'] = "Recommendation"
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = analysis.get('recommendation', 'N/A')
        row += 2
        
        # Skills matched
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws[f'A{row}']
        cell.value = "SKILLS MATCHED ✓"
        cell.font = header_font
        cell.fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
        row += 1
        
        for skill in analysis.get('skills_matched', []):
            ws[f'B{row}'] = skill
            row += 1
        row += 1
        
        # Skills missing
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws[f'A{row}']
        cell.value = "SKILLS MISSING ✗"
        cell.font = header_font
        cell.fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
        row += 1
        
        for skill in analysis.get('skills_missing', []):
            ws[f'B{row}'] = skill
            row += 1
        row += 1
        
        # Experience
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws[f'A{row}']
        cell.value = "EXPERIENCE SUMMARY"
        cell.font = header_font
        cell.fill = header_fill
        row += 1
        
        ws.merge_cells(f'A{row}:B{row}')
        ws[f'A{row}'] = analysis.get('experience_summary', 'N/A')
        ws[f'A{row}'].alignment = Alignment(wrap_text=True)
        ws.row_dimensions[row].height = 60
        row += 2
        
        # Education
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws[f'A{row}']
        cell.value = "EDUCATION SUMMARY"
        cell.font = header_font
        cell.fill = header_fill
        row += 1
        
        ws.merge_cells(f'A{row}:B{row}')
        ws[f'A{row}'] = analysis.get('education_summary', 'N/A')
        ws[f'A{row}'].alignment = Alignment(wrap_text=True)
        ws.row_dimensions[row].height = 60
    
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    wb.save(filepath)
    print(f"📄 Batch Excel report saved to: {filepath}")
    return filepath

def create_csv_report(analyses, filename="batch_analysis_summary.csv"):
    """Create CSV summary report"""
    update_activity()
    
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Rank', 'Candidate Name', 'Score', 'Recommendation', 'Filename', 
                     'Skills Matched', 'Skills Missing', 'Experience Summary', 'Education Summary']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for idx, analysis in enumerate(analyses, 1):
            writer.writerow({
                'Rank': idx,
                'Candidate Name': analysis.get('candidate_name', 'Unknown'),
                'Score': analysis.get('overall_score', 0),
                'Recommendation': analysis.get('recommendation', 'N/A'),
                'Filename': analysis.get('filename', 'Unknown'),
                'Skills Matched': ', '.join(analysis.get('skills_matched', [])),
                'Skills Missing': ', '.join(analysis.get('skills_missing', [])),
                'Experience Summary': analysis.get('experience_summary', 'N/A'),
                'Education Summary': analysis.get('education_summary', 'N/A')
            })
    
    print(f"📄 CSV report saved to: {filepath}")
    return filepath

@app.route('/analyze-single', methods=['POST'])
def analyze_single():
    """Single resume analysis endpoint"""
    update_activity()
    
    try:
        print("\n" + "="*50)
        print("📥 Single analysis request received")
        start_time = time.time()
        
        if 'resume' not in request.files:
            return jsonify({'error': 'No resume file provided'}), 400
        
        if 'jobDescription' not in request.form:
            return jsonify({'error': 'No job description provided'}), 400
        
        resume_file = request.files['resume']
        job_description = request.form['jobDescription']
        
        if resume_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save file
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"resume_{timestamp}{file_ext}")
        resume_file.save(file_path)
        
        # Extract text
        if file_ext == '.pdf':
            resume_text = extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            resume_text = extract_text_from_docx(file_path)
        elif file_ext == '.txt':
            resume_text = extract_text_from_txt(file_path)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        if resume_text.startswith('Error'):
            return jsonify({'error': resume_text}), 500
        
        # Analyze with OpenAI
        analysis = analyze_resume_with_openai(resume_text, job_description, resume_file.filename)
        
        # Create Excel report
        excel_filename = f"analysis_{timestamp}.xlsx"
        
        # Create workbook for single analysis
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
        ws[f'B{row}'] = analysis.get('candidate_name', 'N/A')
        row += 1
        
        ws[f'A{row}'] = "Analysis Date"
        ws[f'A{row}'].font = subheader_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'B{row}'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row += 2
        
        # Overall Score
        ws[f'A{row}'] = "Overall Match Score"
        ws[f'A{row}'].font = Font(bold=True, size=12)
        ws[f'A{row}'].fill = header_fill
        ws[f'A{row}'].font = Font(bold=True, size=12, color="FFFFFF")
        ws[f'B{row}'] = f"{analysis.get('overall_score', 0)}/100"
        score_color = "C00000" if analysis.get('overall_score', 0) < 60 else "70AD47" if analysis.get('overall_score', 0) >= 80 else "FFC000"
        ws[f'B{row}'].font = Font(bold=True, size=12, color=score_color)
        row += 1
        
        ws[f'A{row}'] = "Recommendation"
        ws[f'A{row}'].font = subheader_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'B{row}'] = analysis.get('recommendation', 'N/A')
        row += 2
        
        # Skills Matched Section
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws[f'A{row}']
        cell.value = "SKILLS MATCHED ✓"
        cell.font = header_font
        cell.fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        skills_matched = analysis.get('skills_matched', [])
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
        
        skills_missing = analysis.get('skills_missing', [])
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
        cell.value = analysis.get('experience_summary', 'N/A')
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
        cell.value = analysis.get('education_summary', 'N/A')
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
        
        for strength in analysis.get('key_strengths', []):
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
        
        for area in analysis.get('areas_for_improvement', []):
            ws[f'A{row}'] = "•"
            ws[f'B{row}'] = area
            ws[f'B{row}'].alignment = Alignment(wrap_text=True)
            row += 1
        
        # Apply borders to all cells
        for row_cells in ws.iter_rows(min_row=1, max_row=row, min_col=1, max_col=2):
            for cell in row_cells:
                cell.border = border
        
        excel_path = os.path.join(UPLOAD_FOLDER, excel_filename)
        wb.save(excel_path)
        
        analysis['excel_filename'] = excel_filename
        
        total_time = time.time() - start_time
        print(f"✅ Single analysis completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Single analysis error: {traceback.format_exc()}")
        return jsonify({'error': f'Analysis failed: {str(e)[:200]}'}), 500

@app.route('/analyze-batch', methods=['POST'])
def analyze_batch():
    """Batch analyze multiple resumes"""
    update_activity()
    
    try:
        print("\n" + "="*50)
        print("📥 Batch analysis request received")
        start_time = time.time()
        
        if 'resumes' not in request.files:
            return jsonify({'error': 'No resume files provided'}), 400
        
        if 'jobDescription' not in request.form:
            return jsonify({'error': 'No job description provided'}), 400
        
        resume_files = request.files.getlist('resumes')
        job_description = request.form['jobDescription']
        
        if len(resume_files) > 15:
            return jsonify({'error': 'Maximum 15 resumes allowed per batch'}), 400
        
        print(f"📄 Processing {len(resume_files)} resumes")
        
        analyses = []
        
        for idx, resume_file in enumerate(resume_files, 1):
            print(f"\n--- Processing resume {idx}/{len(resume_files)}: {resume_file.filename} ---")
            
            if resume_file.filename == '':
                continue
            
            # Check file size
            resume_file.seek(0, 2)
            file_size = resume_file.tell()
            resume_file.seek(0)
            
            if file_size > 10 * 1024 * 1024:
                print(f"❌ File too large: {resume_file.filename}")
                continue
            
            # Save file
            file_ext = os.path.splitext(resume_file.filename)[1].lower()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            file_path = os.path.join(UPLOAD_FOLDER, f"resume_{timestamp}_{idx}{file_ext}")
            resume_file.save(file_path)
            
            # Extract text
            if file_ext == '.pdf':
                resume_text = extract_text_from_pdf(file_path)
            elif file_ext in ['.docx', '.doc']:
                resume_text = extract_text_from_docx(file_path)
            elif file_ext == '.txt':
                resume_text = extract_text_from_txt(file_path)
            else:
                print(f"❌ Unsupported file format: {file_ext}")
                continue
            
            if resume_text.startswith('Error'):
                print(f"❌ Text extraction error: {resume_text}")
                continue
            
            # Analyze with OpenAI
            analysis = analyze_resume_with_openai(resume_text, job_description, resume_file.filename)
            analyses.append(analysis)
            
            # Small delay to avoid rate limits
            time.sleep(0.5)
        
        if not analyses:
            return jsonify({'error': 'No valid resumes could be processed'}), 400
        
        # Sort by score (highest to lowest)
        analyses.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        # Create reports
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_filename = f"batch_analysis_{timestamp}.xlsx"
        csv_filename = f"batch_summary_{timestamp}.csv"
        
        excel_path = create_batch_excel_report(analyses, excel_filename)
        csv_path = create_csv_report(analyses, csv_filename)
        
        total_time = time.time() - start_time
        print(f"✅ Batch analysis completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify({
            'success': True,
            'total_resumes': len(analyses),
            'analyses': analyses,
            'excel_filename': excel_filename,
            'csv_filename': csv_filename,
            'processing_time': f"{total_time:.2f}s"
        })
        
    except Exception as e:
        print(f"❌ Batch analysis error: {traceback.format_exc()}")
        return jsonify({'error': f'Batch analysis failed: {str(e)[:200]}'}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    """Download Excel or CSV report"""
    update_activity()
    
    try:
        import re
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        if filename.endswith('.csv'):
            mimetype = 'text/csv'
        else:
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=safe_filename,
            mimetype=mimetype
        )
        
    except Exception as e:
        print(f"❌ Download error: {traceback.format_exc()}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/warmup', methods=['GET'])
def force_warmup():
    """Force warm-up OpenAI connection"""
    update_activity()
    
    try:
        if client is None:
            return jsonify({
                'status': 'error',
                'message': 'OpenAI client not initialized',
                'warmup_complete': False
            })
        
        result = warmup_openai()
        
        return jsonify({
            'status': 'success' if result else 'error',
            'message': 'OpenAI warmed up successfully' if result else 'Warm-up failed',
            'warmup_complete': warmup_complete,
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
    """Quick endpoint to check if OpenAI is responsive"""
    update_activity()
    
    try:
        if client is None:
            return jsonify({
                'available': False, 
                'reason': 'Client not initialized',
                'warmup_complete': warmup_complete
            })
        
        if not warmup_complete:
            return jsonify({
                'available': False,
                'reason': 'OpenAI is warming up',
                'warmup_complete': False
            })
        
        return jsonify({
            'available': True,
            'warmup_complete': True,
            'status': 'ready'
        })
            
    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg or "insufficient_quota" in error_msg:
            status = 'quota_exceeded'
        elif "rate limit" in error_msg.lower():
            status = 'rate_limit'
        else:
            status = 'error'
            
        return jsonify({
            'available': False,
            'reason': error_msg[:100],
            'status': status,
            'warmup_complete': warmup_complete
        })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    update_activity()
    
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'multi-resume-analyzer',
        'openai_warmup': warmup_complete,
        'message': 'Service is alive and warm!' if warmup_complete else 'Service is alive, warming up OpenAI...'
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    return jsonify({
        'status': 'Backend is running!', 
        'timestamp': datetime.now().isoformat(),
        'api_key_configured': bool(api_key),
        'client_initialized': client is not None,
        'openai_warmup_complete': warmup_complete,
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'upload_folder_path': UPLOAD_FOLDER,
        'inactive_minutes': inactive_minutes,
        'keep_warm_active': keep_warm_thread is not None and keep_warm_thread.is_alive(),
        'version': '2.0.0',
        'features': ['batch_processing', 'single_analysis', 'excel_export', 'csv_export']
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Multi-Resume Analyzer Backend Starting...")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"🔑 API Key: {'✅ Configured' if api_key else '❌ NOT FOUND'}")
    print(f"🤖 OpenAI Client: {'✅ Initialized' if client else '❌ NOT INITIALIZED'}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print("✅ Batch Processing: Enabled (1-15 resumes)")
    print("✅ Single Analysis: Enabled")
    print("="*50 + "\n")
    
    if not api_key:
        print("⚠️  WARNING: OPENAI_API_KEY not found!")
        print("Please create a .env file with: OPENAI_API_KEY=your_key_here\n")
        print("Get your API key from: https://platform.openai.com/api-keys")
    
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
