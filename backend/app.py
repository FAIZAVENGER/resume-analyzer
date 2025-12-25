from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google import genai
from PyPDF2 import PdfReader
from docx import Document
import os
import json
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Gemini AI
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY not found in .env file!")
    client = None
else:
    print(f"✅ API Key loaded: {api_key[:10]}...")
    client = genai.Client(api_key=api_key)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
<html>
<head>
    <title>Resume Analyzer API</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 40px; text-align: center; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #333; }
        .status { color: green; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Resume Analyzer API</h1>
        <p class="status">Status: Running</p>
        <p>API Endpoints:</p>
        <ul>
            <li>POST /analyze - Analyze a resume</li>
            <li>GET /health - Health check</li>
            <li>GET /download/{filename} - Download Excel report</li>
        </ul>
    </div>
</body>
</html>
    '''

def extract_text_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text if text.strip() else "Error: PDF appears to be empty"
    except Exception as e:
        print(f"PDF Error: {traceback.format_exc()}")
        return f"Error reading PDF: {str(e)}"

def extract_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text if text.strip() else "Error: Document appears to be empty"
    except Exception as e:
        print(f"DOCX Error: {traceback.format_exc()}")
        return f"Error reading DOCX: {str(e)}"

def extract_text_from_txt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        return text if text.strip() else "Error: Text file appears to be empty"
    except Exception as e:
        print(f"TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

def analyze_resume_with_gemini(resume_text, job_description):
    if client is None:
        return {
            "candidate_name": "API Error",
            "skills_matched": [],
            "skills_missing": [],
            "experience_summary": "Gemini API not configured",
            "education_summary": "Check API key",
            "overall_score": 0,
            "recommendation": "Configuration Error",
            "key_strengths": [],
            "areas_for_improvement": []
        }
    
    prompt = f"""CRITICAL INSTRUCTIONS:
1. Analyze ONLY the provided resume text
2. Extract ALL information EXACTLY from the resume
3. DO NOT use any external knowledge or assumptions
4. If information is missing, say it's missing

RESUME TO ANALYZE:
{resume_text[:8000]}

JOB DESCRIPTION:
{job_description[:4000]}

EXTRACT THE CANDIDATE NAME: Look for name patterns at the beginning of the resume.
If no clear name found, use "Candidate"

Return ONLY this JSON format with data FROM THE RESUME:
{{
    "candidate_name": "Extract from resume or 'Candidate'",
    "skills_matched": ["skill from resume", "another skill from resume"],
    "skills_missing": ["skill from job not in resume"],
    "experience_summary": "Summary based ONLY on resume experience section",
    "education_summary": "Summary based ONLY on resume education section",
    "overall_score": 75,
    "recommendation": "Based on match percentage",
    "key_strengths": ["strength evident in resume"],
    "areas_for_improvement": ["gap in resume compared to job"]
}}"""

    try:
        print("🤖 Sending to Gemini AI...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
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
        return {
            "candidate_name": "Parse Error",
            "skills_matched": ["JSON parsing failed"],
            "skills_missing": [],
            "experience_summary": "Error parsing AI response",
            "education_summary": "Please try again",
            "overall_score": 0,
            "recommendation": "Error - Retry analysis",
            "key_strengths": [],
            "areas_for_improvement": []
        }
    except Exception as e:
        print(f"❌ Gemini Error: {str(e)}")
        return {
            "candidate_name": "API Error",
            "skills_matched": [],
            "skills_missing": [],
            "experience_summary": f"API Error: {str(e)}",
            "education_summary": "Check API configuration",
            "overall_score": 0,
            "recommendation": "Error occurred",
            "key_strengths": [],
            "areas_for_improvement": []
        }

def create_excel_report(analysis_data, filename="resume_analysis_report.xlsx"):
    """Create Excel report using the ACTUAL analysis data"""
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Resume Analysis"
    
    # Styles
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    subheader_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                    top=Side(style='thin'), bottom=Side(style='thin'))
    
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 60
    
    row = 1
    
    # Title
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "AI RESUME ANALYSIS REPORT"
    cell.font = Font(bold=True, size=16, color="FFFFFF")
    cell.fill = PatternFill(start_color="203864", end_color="203864", fill_type="solid")
    cell.alignment = Alignment(horizontal='center', vertical='center')
    row += 2
    
    # Candidate Info - USING ACTUAL DATA
    ws[f'A{row}'] = "Candidate Name"
    ws[f'A{row}'].font = Font(bold=True)
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = analysis_data.get('candidate_name', 'Not Specified')
    row += 1
    
    ws[f'A{row}'] = "Analysis Date"
    ws[f'A{row}'].font = Font(bold=True)
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row += 1
    
    ws[f'A{row}'] = "Overall Match Score"
    ws[f'A{row}'].font = Font(bold=True)
    ws[f'A{row}'].fill = subheader_fill
    score = analysis_data.get('overall_score', 0)
    ws[f'B{row}'] = f"{score}/100"
    ws[f'B{row}'].font = Font(bold=True, color="FF0000" if score < 60 else "00AA00" if score > 80 else "FF9900")
    row += 1
    
    ws[f'A{row}'] = "Recommendation"
    ws[f'A{row}'].font = Font(bold=True)
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = analysis_data.get('recommendation', 'Not Available')
    row += 2
    
    # Skills Matched - USING ACTUAL DATA
    ws.merge_cells(f'A{row}:B{row}')
    ws[f'A{row}'] = "✓ SKILLS MATCHED (Found in Resume)"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    skills = analysis_data.get('skills_matched', [])
    if skills:
        for i, skill in enumerate(skills, 1):
            ws[f'A{row}'] = f"{i}."
            ws[f'B{row}'] = skill
            row += 1
    else:
        ws[f'A{row}'] = "No specific matched skills identified"
        row += 1
    
    row += 1
    
    # Skills Missing - USING ACTUAL DATA
    ws.merge_cells(f'A{row}:B{row}')
    ws[f'A{row}'] = "✗ SKILLS MISSING (Job Requirements)"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    missing = analysis_data.get('skills_missing', [])
    if missing:
        for i, skill in enumerate(missing, 1):
            ws[f'A{row}'] = f"{i}."
            ws[f'B{row}'] = skill
            row += 1
    else:
        ws[f'A{row}'] = "All key skills are present in resume"
        row += 1
    
    row += 1
    
    # Experience Summary - USING ACTUAL DATA
    ws.merge_cells(f'A{row}:B{row}')
    ws[f'A{row}'] = "EXPERIENCE SUMMARY"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = header_fill
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    ws.merge_cells(f'A{row}:B{row}')
    ws[f'A{row}'] = analysis_data.get('experience_summary', 'No experience information found')
    ws[f'A{row}'].alignment = Alignment(wrap_text=True, vertical='top')
    ws.row_dimensions[row].height = 40
    row += 2
    
    # Education Summary - USING ACTUAL DATA
    ws.merge_cells(f'A{row}:B{row}')
    ws[f'A{row}'] = "EDUCATION SUMMARY"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = header_fill
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    ws.merge_cells(f'A{row}:B{row}')
    ws[f'A{row}'] = analysis_data.get('education_summary', 'No education information found')
    ws[f'A{row}'].alignment = Alignment(wrap_text=True, vertical='top')
    ws.row_dimensions[row].height = 40
    row += 2
    
    # Key Strengths - USING ACTUAL DATA
    ws.merge_cells(f'A{row}:B{row}')
    ws[f'A{row}'] = "KEY STRENGTHS"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = PatternFill(start_color="00B050", end_color="00B050", fill_type="solid")
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    strengths = analysis_data.get('key_strengths', [])
    if strengths:
        for strength in strengths:
            ws[f'A{row}'] = "•"
            ws[f'B{row}'] = strength
            row += 1
    else:
        ws[f'A{row}'] = "Key strengths analysis not available"
        row += 1
    
    row += 1
    
    # Areas for Improvement - USING ACTUAL DATA
    ws.merge_cells(f'A{row}:B{row}')
    ws[f'A{row}'] = "AREAS FOR IMPROVEMENT"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    improvements = analysis_data.get('areas_for_improvement', [])
    if improvements:
        for area in improvements:
            ws[f'A{row}'] = "•"
            ws[f'B{row}'] = area
            row += 1
    else:
        ws[f'A{row}'] = "No specific improvement areas identified"
        row += 1
    
    # Apply borders
    for r in ws.iter_rows(min_row=1, max_row=row, min_col=1, max_col=2):
        for cell in r:
            cell.border = border
    
    # Save file
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    wb.save(filepath)
    print(f"📄 Excel report saved: {filepath}")
    return filepath

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    try:
        print("\n" + "="*50)
        print("📥 New analysis request received")
        
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
        print(f"💾 File saved: {resume_file.filename}")
        
        # Extract text
        print(f"📖 Extracting text from {file_ext}...")
        if file_ext == '.pdf':
            resume_text = extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            resume_text = extract_text_from_docx(file_path)
        elif file_ext == '.txt':
            resume_text = extract_text_from_txt(file_path)
        else:
            return jsonify({'error': 'Unsupported file format. Use PDF, DOCX, or TXT'}), 400
        
        if resume_text.startswith('Error'):
            return jsonify({'error': resume_text}), 500
        
        print(f"✅ Extracted {len(resume_text)} characters")
        
        # Check API
        if not api_key or client is None:
            return jsonify({'error': 'AI service not configured'}), 500
        
        # Analyze with AI
        print("🤖 Analyzing with Gemini AI...")
        analysis = analyze_resume_with_gemini(resume_text, job_description)
        
        # DEBUG: Show what AI returned
        print(f"🔍 AI Analysis Result:")
        print(f"  Name: {analysis.get('candidate_name')}")
        print(f"  Score: {analysis.get('overall_score')}")
        print(f"  Matched Skills: {len(analysis.get('skills_matched', []))}")
        print(f"  Missing Skills: {len(analysis.get('skills_missing', []))}")
        
        # Create unique Excel filename
        excel_filename = f"analysis_{timestamp}.xlsx"
        excel_path = create_excel_report(analysis, excel_filename)
        
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['timestamp'] = timestamp
        
        print("✅ Analysis completed successfully")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Error in /analyze: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    return jsonify({'error': 'File not found'}), 404

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'Backend is running!', 
        'timestamp': datetime.now().isoformat(),
        'api_key_configured': bool(api_key),
        'client_initialized': client is not None,
        'service': 'Resume Analyzer API'
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting...")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"🔑 API Key: {'✅ Configured' if api_key else '❌ NOT FOUND'}")
    print(f"🤖 Gemini Client: {'✅ Initialized' if client else '❌ NOT INITIALIZED'}")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
