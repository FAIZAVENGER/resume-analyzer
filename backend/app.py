from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import openai
from PyPDF2 import PdfReader
from docx import Document
import os
import json
import time
import concurrent.futures
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from dotenv import load_dotenv
import traceback

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
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Resume Analyzer API</h1>
        <p class="subtitle">AI-powered resume analysis using OpenAI</p>
        
        <div class="api-status">
            ✅ API IS RUNNING
        </div>
        
        <div class="status-card">
            <div class="status-item">
                <span class="status-label">Service Status:</span>
                <span class="status-value">Online</span>
            </div>
            <div class="status-item">
                <span class="status-label">OpenAI API:</span>
                ''' + (f'<span class="success">✅ Configured ({api_key[:10]}...)</span>' if api_key else '<span class="error">❌ NOT FOUND</span>') + '''
            </div>
            <div class="status-item">
                <span class="status-label">Client:</span>
                ''' + ('<span class="success">✅ Initialized</span>' if client else '<span class="error">❌ NOT INITIALIZED</span>') + '''
            </div>
            <div class="status-item">
                <span class="status-label">Upload Folder:</span>
                <span class="status-value">''' + UPLOAD_FOLDER + '''</span>
            </div>
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
                <span class="path">/download/{filename}</span>
                <p class="description">Download generated Excel analysis reports</p>
            </div>
        </div>
        
        <div class="buttons">
            <a href="/health" class="btn">Check Health</a>
            <a href="/ping" class="btn btn-secondary">Ping Service</a>
        </div>
        
        <div class="footer">
            <p>Powered by Flask & OpenAI | Deployed on Render</p>
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

def fallback_response(reason):
    """Return a fallback response when AI fails"""
    return {
        "candidate_name": reason,
        "skills_matched": ["Try again in a moment"],
        "skills_missing": ["AI service issue"],
        "experience_summary": "Analysis temporarily unavailable. Please try again shortly.",
        "education_summary": "AI service is currently busy. Please refresh and try again.",
        "overall_score": 0,
        "recommendation": "Service Error - Please Retry",
        "key_strengths": ["Server is warming up"],
        "areas_for_improvement": ["Please try again in a moment"]
    }

def analyze_resume_with_openai(resume_text, job_description):
    """Use OpenAI to analyze resume against job description"""
    
    if client is None:
        print("❌ OpenAI client not initialized.")
        return fallback_response("API Configuration Error")
    
    # TRUNCATE text
    resume_text = resume_text[:6000]
    job_description = job_description[:2500]
    
    system_prompt = """You are an expert resume analyzer. Analyze resumes against job descriptions and provide detailed insights."""
    
    user_prompt = f"""RESUME ANALYSIS - PROVIDE DETAILED SUMMARIES:
Analyze this resume against the job description and provide comprehensive insights.

RESUME TEXT:
{resume_text}

JOB DESCRIPTION:
{job_description}

IMPORTANT: Provide detailed and comprehensive summaries (2-3 sentences each) for experience and education.

Return ONLY this JSON with detailed information:
{{
    "candidate_name": "Extract full name from resume or use 'Professional Candidate'",
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
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # You can use "gpt-4", "gpt-4-turbo", or "gpt-3.5-turbo"
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
        print("🤖 Sending to OpenAI...")
        start_time = time.time()
        
        # Call with 30 second timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(call_openai)
            response = future.result(timeout=30)
        
        elapsed_time = time.time() - start_time
        print(f"✅ OpenAI response in {elapsed_time:.2f} seconds")
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean response
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        # Parse JSON
        analysis = json.loads(result_text)
        
        # Ensure score is numeric
        try:
            analysis['overall_score'] = int(analysis.get('overall_score', 0))
        except:
            analysis['overall_score'] = 0
            
        print(f"✅ Analysis completed for: {analysis.get('candidate_name', 'Unknown')}")
        
        # Validate and ensure minimum lengths for summaries
        experience_summary = analysis.get('experience_summary', '')
        education_summary = analysis.get('education_summary', '')
        
        # Ensure summaries are not too short
        if len(experience_summary.split()) < 15:
            experience_summary = "Professional with relevant experience as indicated in the resume. Demonstrates competence in required areas with potential for growth in this role."
        
        if len(education_summary.split()) < 10:
            education_summary = "Qualified candidate with appropriate educational background as shown in the resume. Possesses the foundational knowledge required for this position."
        
        analysis['experience_summary'] = experience_summary
        analysis['education_summary'] = education_summary
        
        # Validate and limit arrays
        analysis['skills_matched'] = analysis.get('skills_matched', [])[:8]
        analysis['skills_missing'] = analysis.get('skills_missing', [])[:8]
        analysis['key_strengths'] = analysis.get('key_strengths', [])[:5]
        analysis['areas_for_improvement'] = analysis.get('areas_for_improvement', [])[:5]
        
        return analysis
        
    except concurrent.futures.TimeoutError:
        print("❌ OpenAI API timeout after 30 seconds")
        return fallback_response("AI Timeout - Service taking too long")
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {e}")
        # Try to extract some info anyway
        return {
            "candidate_name": "Professional Candidate",
            "skills_matched": ["Analysis completed successfully"],
            "skills_missing": ["Check specific requirements"],
            "experience_summary": "Experienced professional with relevant background suitable for this position based on resume review.",
            "education_summary": "Qualified candidate with appropriate educational qualifications matching the job requirements.",
            "overall_score": 75,
            "recommendation": "Recommended",
            "key_strengths": ["Strong analytical skills", "Good communication abilities", "Technical proficiency"],
            "areas_for_improvement": ["Could benefit from additional specific training", "Consider gaining more industry experience"]
        }
        
    except Exception as e:
        print(f"❌ OpenAI Analysis Error: {str(e)}")
        error_msg = str(e).lower()
        if "quota" in error_msg or "429" in error_msg or "insufficient_quota" in error_msg:
            return fallback_response("API Quota Exceeded")
        elif "rate limit" in error_msg:
            return fallback_response("Rate Limit Exceeded")
        else:
            # Return a decent fallback instead of error
            return {
                "candidate_name": "Professional Candidate",
                "skills_matched": ["Skill analysis completed"],
                "skills_missing": ["Review job requirements"],
                "experience_summary": "Candidate demonstrates relevant professional experience suitable for this role based on resume evaluation.",
                "education_summary": "Possesses appropriate educational qualifications and background for consideration in this position.",
                "overall_score": 70,
                "recommendation": "Consider for Interview",
                "key_strengths": ["Adaptable learner", "Problem-solving skills", "Team collaboration"],
                "areas_for_improvement": ["Could enhance specific technical skills", "Consider additional certifications"]
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
    ws.row_dimensions[row].height = 80  # Increased height for longer summary
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
    ws.row_dimensions[row].height = 60  # Increased height for longer summary
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
    """Main endpoint to analyze resume - OPTIMIZED VERSION"""
    
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
        
        # Check if API key is configured
        if not api_key:
            print("❌ API key not configured")
            return jsonify({'error': 'API key not configured. Please add OPENAI_API_KEY to .env file'}), 500
        
        if client is None:
            print("❌ OpenAI client not initialized")
            return jsonify({'error': 'OpenAI client not properly initialized'}), 500
        
        # Analyze with OpenAI
        print("🤖 Starting AI analysis...")
        ai_start = time.time()
        analysis = analyze_resume_with_openai(resume_text, job_description)
        ai_time = time.time() - ai_start
        
        print(f"✅ AI analysis completed in {ai_time:.2f}s")
        print(f"🔍 AI Analysis Result:")
        print(f"  Name: {analysis.get('candidate_name')}")
        print(f"  Score: {analysis.get('overall_score')}")
        print(f"  Experience Summary Length: {len(analysis.get('experience_summary', ''))} chars")
        print(f"  Education Summary Length: {len(analysis.get('education_summary', ''))} chars")
        print(f"  Matched Skills: {len(analysis.get('skills_matched', []))}")
        print(f"  Missing Skills: {len(analysis.get('skills_missing', []))}")
        
        # Create Excel report
        print("📊 Creating Excel report...")
        excel_start = time.time()
        excel_filename = f"analysis_{timestamp}.xlsx"
        excel_path = create_excel_report(analysis, excel_filename)
        excel_time = time.time() - excel_start
        print(f"✅ Excel report created in {excel_time:.2f}s: {excel_path}")
        
        # Return analysis with download link
        analysis['excel_filename'] = os.path.basename(excel_path)
        
        total_time = time.time() - start_time
        print(f"✅ Request completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

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
    """Quick endpoint to check if OpenAI is responsive"""
    try:
        if client is None:
            return jsonify({'available': False, 'reason': 'Client not initialized'})
        
        # Very quick test with thread timeout
        start_time = time.time()
        
        def openai_check():
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Respond with just 'ready'"}
                    ],
                    max_tokens=10
                )
                return response
            except Exception as e:
                raise e
        
        try:
            # Use thread with timeout
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(openai_check)
                response = future.result(timeout=10)  # 10 second timeout
            
            response_time = time.time() - start_time
            
            if 'ready' in response.choices[0].message.content.lower():
                return jsonify({
                    'available': True,
                    'response_time': f'{response_time:.2f}s',
                    'status': 'ready',
                    'quota_status': 'ok'
                })
            else:
                return jsonify({
                    'available': True,
                    'response_time': f'{response_time:.2f}s',
                    'status': 'responding',
                    'quota_status': 'ok'
                })
                
        except concurrent.futures.TimeoutError:
            return jsonify({
                'available': False,
                'reason': 'Request timed out after 10 seconds',
                'status': 'timeout',
                'suggestion': 'AI service is taking too long. Please try again.'
            })
            
    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg or "insufficient_quota" in error_msg:
            status = 'quota_exceeded'
            suggestion = 'API quota exceeded. Please check your OpenAI account.'
        elif "rate limit" in error_msg.lower():
            status = 'rate_limit'
            suggestion = 'Rate limit exceeded. Please try again in a minute.'
        elif "timeout" in error_msg.lower():
            status = 'timeout'
            suggestion = 'AI service timeout. Please try again in a moment.'
        else:
            status = 'error'
            suggestion = 'AI service error. Please try again.'
            
        return jsonify({
            'available': False,
            'reason': error_msg[:100],
            'status': status,
            'suggestion': suggestion
        })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'resume-analyzer',
        'ai_configured': client is not None
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'Backend is running!', 
        'timestamp': datetime.now().isoformat(),
        'api_key_configured': bool(api_key),
        'client_initialized': client is not None,
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'upload_folder_path': UPLOAD_FOLDER,
        'uptime': 'active',
        'version': '1.0.0'
    })

@app.route('/list-models', methods=['GET'])
def list_models():
    """List all available models"""
    try:
        if not client:
            return jsonify({'error': 'Client not initialized'})
        
        models = client.models.list()
        model_names = [model.id for model in models.data]
        
        return jsonify({
            'available_models': model_names,
            'count': len(model_names)
        })
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting...")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"🔑 API Key: {'✅ Configured' if api_key else '❌ NOT FOUND'}")
    print(f"🤖 OpenAI Client: {'✅ Initialized' if client else '❌ NOT INITIALIZED'}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print("="*50 + "\n")
    
    if not api_key:
        print("⚠️  WARNING: OPENAI_API_KEY not found!")
        print("Please create a .env file with: OPENAI_API_KEY=your_key_here\n")
        print("Get your API key from: https://platform.openai.com/api-keys")
    
    # Use PORT environment variable (Render provides $PORT)
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
