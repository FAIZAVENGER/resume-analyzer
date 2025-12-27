from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PyPDF2 import PdfReader
from docx import Document
import os
import json
import re
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

print("=" * 50)
print("🚀 Resume Analyzer Backend Starting...")
print("=" * 50)

# Try to load API key, but don't fail if not found
api_key = os.getenv('GEMINI_API_KEY', '').strip()
if api_key and len(api_key) > 10:
    print(f"✅ API Key loaded: {api_key[:10]}...")
    
    # Try to import and initialize Gemini only if key exists
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        # Test the client
        try:
            test_response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents="Say 'OK'"
            )
            if test_response and hasattr(test_response, 'text'):
                print("✅ Gemini API client initialized successfully!")
                GEMINI_AVAILABLE = True
            else:
                print("⚠️ Gemini API test failed")
                GEMINI_AVAILABLE = False
                client = None
        except Exception as e:
            print(f"⚠️ Gemini API test failed: {str(e)[:100]}")
            GEMINI_AVAILABLE = False
            client = None
            
    except ImportError:
        print("❌ 'google-generativeai' package not installed. Install with: pip install google-generativeai")
        GEMINI_AVAILABLE = False
        client = None
else:
    print("⚠️  No valid API key found. Running in TEXT ANALYSIS MODE only.")
    print("   To enable AI features, add: GEMINI_API_KEY=your_key_here")
    GEMINI_AVAILABLE = False
    client = None

# Get absolute path for uploads folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"📁 Upload folder: {UPLOAD_FOLDER}")
print("=" * 50 + "\n")

# ========== ENHANCED TEXT ANALYSIS FUNCTIONS ==========

def extract_name_from_resume(text):
    """Extract candidate name from resume text"""
    if not text:
        return "Professional Candidate"
    
    lines = text.split('\n')[:20]  # Check first 20 lines
    
    # Look for common patterns
    patterns = [
        r'^([A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?)',  # First Last
        r'Name[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',  # Name: John Doe
        r'Full Name[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',  # Full Name: John Doe
        r'^([A-Z][A-Z]+ [A-Z][A-Z]+)',  # JOHN DOE
        r'Contact Information\s*\n([A-Z][a-z]+ [A-Z][a-z]+)',
    ]
    
    for line in lines:
        line = line.strip()
        if 3 < len(line) < 50:  # Reasonable name length
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    if len(name.split()) >= 2:
                        return name.title()
    
    # Look for email patterns
    for line in lines:
        email_match = re.search(r'([A-Z][a-z]+ [A-Z][a-z]+)\s*<[^>]+>', line)
        if email_match:
            return email_match.group(1).strip().title()
    
    return "Professional Candidate"

def extract_skills_from_resume(text):
    """Extract skills from resume text"""
    common_skills = [
        'Python', 'JavaScript', 'Java', 'C++', 'React', 'Node.js', 'SQL',
        'AWS', 'Docker', 'Git', 'HTML', 'CSS', 'TypeScript', 'Angular',
        'Vue.js', 'MongoDB', 'PostgreSQL', 'MySQL', 'REST API', 'Linux',
        'Machine Learning', 'Data Analysis', 'Excel', 'PowerPoint', 'Word',
        'Communication', 'Teamwork', 'Problem Solving', 'Leadership',
        'Project Management', 'Time Management', 'Analytical Skills',
        'Agile', 'Scrum', 'DevOps', 'Testing', 'UX/UI Design'
    ]
    
    found_skills = []
    text_lower = text.lower()
    
    for skill in common_skills:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    
    # Look for skills section
    skills_match = re.search(r'(?:skills|technical skills|competencies)[:\s]*\n(.+?)(?:\n\n|\n[A-Z]|$)', 
                            text, re.IGNORECASE | re.DOTALL)
    if skills_match:
        skills_text = skills_match.group(1)
        # Split by common separators
        skill_items = re.split(r'[,\n•\-]', skills_text)
        for item in skill_items:
            item = item.strip()
            if 2 < len(item) < 30 and not re.search(r'\d{4}', item):
                found_skills.append(item)
    
    # Remove duplicates and limit
    unique_skills = []
    for skill in found_skills:
        if skill not in unique_skills:
            unique_skills.append(skill)
    
    return unique_skills[:10]

def extract_experience_summary(text):
    """Extract experience summary from resume"""
    # Look for experience keywords
    exp_keywords = ['experience', 'work history', 'employment', 'career']
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in exp_keywords):
            # Get next few lines
            context = []
            for j in range(i+1, min(i+6, len(lines))):
                context_line = lines[j].strip()
                if context_line and len(context_line) < 200:
                    context.append(context_line)
            if context:
                return " ".join(context[:3])[:200] + "..." if len(" ".join(context[:3])) > 200 else " ".join(context[:3])
    
    # Look for dates
    year_pattern = r'\b(20\d{2}|19\d{2})\b'
    years = re.findall(year_pattern, text)
    if years:
        years = sorted([int(y) for y in years])
        if len(years) >= 2:
            exp_years = years[-1] - years[0]
            if 0 < exp_years <= 50:
                return f"Professional with approximately {exp_years} years of experience."
    
    return "Experienced professional with relevant background."

def extract_education_summary(text):
    """Extract education summary from resume"""
    edu_keywords = ['education', 'university', 'college', 'degree', 'bachelor', 'master', 'phd']
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in edu_keywords):
            # Get this line and next few
            context = []
            for j in range(i, min(i+4, len(lines))):
                context_line = lines[j].strip()
                if context_line and len(context_line) < 150:
                    context.append(context_line)
            if context:
                return " ".join(context[:2])[:150] + "..." if len(" ".join(context[:2])) > 150 else " ".join(context[:2])
    
    return "Qualified candidate with appropriate educational background."

def calculate_score_based_on_text(resume_text, job_description):
    """Calculate match score based on text analysis"""
    base_score = 65
    
    # Extract skills
    resume_skills = extract_skills_from_resume(resume_text)
    
    # Check for experience keywords
    if any(word in resume_text.lower() for word in ['experience', 'worked', 'years', 'professional']):
        base_score += 10
    
    # Check for education keywords
    if any(word in resume_text.lower() for word in ['degree', 'university', 'college', 'bachelor', 'master']):
        base_score += 8
    
    # Check skills match with job description
    if job_description:
        job_desc_lower = job_description.lower()
        matched_skills = 0
        for skill in resume_skills:
            if skill.lower() in job_desc_lower:
                matched_skills += 1
        
        if matched_skills >= 5:
            base_score += 15
        elif matched_skills >= 3:
            base_score += 10
        elif matched_skills >= 1:
            base_score += 5
    
    # Cap the score
    return min(max(base_score, 50), 95)

def get_enhanced_text_analysis(resume_text, job_description):
    """Get comprehensive analysis using text extraction only"""
    candidate_name = extract_name_from_resume(resume_text)
    extracted_skills = extract_skills_from_resume(resume_text)
    experience_summary = extract_experience_summary(resume_text)
    education_summary = extract_education_summary(resume_text)
    overall_score = calculate_score_based_on_text(resume_text, job_description)
    
    # Determine skills matched based on job description
    skills_matched = []
    skills_missing = []
    
    if job_description:
        job_desc_lower = job_description.lower()
        for skill in extracted_skills:
            if skill.lower() in job_desc_lower:
                skills_matched.append(skill)
            else:
                skills_missing.append(skill)
    
    # If no skills matched, add some defaults
    if not skills_matched:
        skills_matched = ["Communication Skills", "Problem Solving", "Team Collaboration"]
    
    # Add some common missing skills
    if len(skills_missing) < 3:
        common_missing = ["Industry-specific certifications", "Advanced technical training", "Leadership experience"]
        skills_missing.extend(common_missing[:3])
    
    # Determine recommendation
    if overall_score >= 80:
        recommendation = "Recommended for Interview"
    elif overall_score >= 70:
        recommendation = "Consider for Interview"
    elif overall_score >= 60:
        recommendation = "Review Needed"
    else:
        recommendation = "Needs Improvement"
    
    return {
        "candidate_name": candidate_name,
        "skills_matched": skills_matched[:8],
        "skills_missing": skills_missing[:8],
        "experience_summary": experience_summary,
        "education_summary": education_summary,
        "overall_score": overall_score,
        "recommendation": recommendation,
        "key_strengths": skills_matched[:4] if skills_matched else ["Strong foundational skills", "Good communication"],
        "areas_for_improvement": skills_missing[:4] if skills_missing else ["Consider additional training", "Gain more experience"],
        "analysis_mode": "text_analysis",
        "ai_available": GEMINI_AVAILABLE
    }

def analyze_resume_with_gemini(resume_text, job_description):
    """Use Gemini AI if available"""
    if not GEMINI_AVAILABLE or client is None:
        return get_enhanced_text_analysis(resume_text, job_description)
    
    try:
        prompt = f"""ANALYZE THIS RESUME:
{resume_text[:6000]}

FOR THIS JOB:
{job_description[:3000]}

Extract the candidate name from resume. Return ONLY JSON:
{{
    "candidate_name": "Name from resume or 'Professional Candidate'",
    "skills_matched": ["skills from resume matching job"],
    "skills_missing": ["important job skills not in resume"],
    "experience_summary": "brief experience summary",
    "education_summary": "brief education summary",
    "overall_score": 0-100 number,
    "recommendation": "Highly Recommended/Recommended/Consider/Not Recommended",
    "key_strengths": ["key strengths"],
    "areas_for_improvement": ["areas to improve"]
}}"""
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        
        result_text = response.text.strip()
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        analysis = json.loads(result_text)
        analysis['analysis_mode'] = "ai_analysis"
        analysis['ai_available'] = True
        
        return analysis
        
    except Exception as e:
        print(f"⚠️ Gemini analysis failed, using text analysis: {str(e)[:100]}")
        analysis = get_enhanced_text_analysis(resume_text, job_description)
        analysis['ai_error'] = str(e)[:100]
        return analysis

# ========== FLASK ROUTES ==========

@app.route('/')
def home():
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
        
        .warning-card {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
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
        
        .api-status {
            display: inline-block;
            padding: 8px 20px;
            background: #27ae60;
            color: white;
            border-radius: 20px;
            font-weight: bold;
            margin: 20px 0;
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
        
        .error { color: #e74c3c; }
        .success { color: #27ae60; }
        .warning { color: #f39c12; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 Resume Analyzer API</h1>
        <p class="subtitle">Smart resume analysis with or without AI</p>
        
        <div class="api-status">
            ✅ SERVICE IS RUNNING
        </div>
        
        <div class="status-card">
            <div class="status-item">
                <span class="status-label">Service Status:</span>
                <span class="status-value">Online</span>
            </div>
            <div class="status-item">
                <span class="status-label">AI Mode:</span>
                <span class="''' + ('success' if GEMINI_AVAILABLE else 'warning') + '''">
                    ''' + ('✅ AI Enabled' if GEMINI_AVAILABLE else '⚠️ Text Analysis Only') + '''
                </span>
            </div>
            <div class="status-item">
                <span class="status-label">Upload Folder:</span>
                <span class="status-value">Ready</span>
            </div>
        </div>
        
        ''' + ('''
        <div class="warning-card">
            <h3>⚠️ No Valid API Key Found</h3>
            <p>The service is running in <strong>TEXT ANALYSIS MODE</strong>.</p>
            <p>You can still upload resumes and get analysis based on:</p>
            <ul style="text-align: left; margin: 10px 20px;">
                <li>Name extraction</li>
                <li>Skill detection</li>
                <li>Experience analysis</li>
                <li>Education detection</li>
                <li>Basic scoring</li>
            </ul>
            <p><strong>To enable AI analysis:</strong></p>
            <ol style="text-align: left; margin: 10px 20px;">
                <li>Get a FREE API key from: <a href="https://aistudio.google.com/app/apikey" target="_blank">Google AI Studio</a></li>
                <li>Add it as environment variable: <code>GEMINI_API_KEY=your_key_here</code></li>
                <li>Redeploy your app</li>
            </ol>
        </div>
        ''' if not GEMINI_AVAILABLE else '') + '''
        
        <div class="endpoints">
            <h2>📡 API Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">POST</span>
                <span class="path">/analyze</span>
                <p class="description">Upload resume (PDF/DOCX/TXT) with job description</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/health</span>
                <p class="description">Check service status</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/test-key</span>
                <p class="description">Test your API key configuration</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/download/{filename}</span>
                <p class="description">Download Excel reports</p>
            </div>
        </div>
        
        <div class="buttons">
            <a href="/health" class="btn">Check Health</a>
            <a href="/test-key" class="btn btn-secondary">Test API Key</a>
        </div>
        
        <div class="footer">
            <p>Powered by Flask | Enhanced Text Analysis + Optional Gemini AI</p>
            <p>Works perfectly even without API keys!</p>
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
            return "Error: PDF appears to be empty"
        
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

def create_excel_report(analysis_data, filename="resume_analysis_report.xlsx"):
    """Create Excel report"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Resume Analysis"
    
    # Styles
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
    
    # Column widths
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
    
    # Candidate Info
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
    
    ws[f'A{row}'] = "Analysis Mode"
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    mode = analysis_data.get('analysis_mode', 'text_analysis')
    ws[f'B{row}'] = "AI Analysis" if mode == "ai_analysis" else "Text Analysis"
    ws[f'B{row}'].font = Font(color="FF9900" if mode == "text_analysis" else "70AD47", bold=True)
    row += 2
    
    # Score
    ws[f'A{row}'] = "Overall Match Score"
    ws[f'A{row}'].font = Font(bold=True, size=12)
    ws[f'A{row}'].fill = header_fill
    ws[f'A{row}'].font = Font(bold=True, size=12, color="FFFFFF")
    score = analysis_data.get('overall_score', 0)
    ws[f'B{row}'] = f"{score}/100"
    if score < 60:
        score_color = "C00000"
    elif score >= 80:
        score_color = "70AD47"
    else:
        score_color = "FFC000"
    ws[f'B{row}'].font = Font(bold=True, size=12, color=score_color)
    row += 1
    
    ws[f'A{row}'] = "Recommendation"
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = analysis_data.get('recommendation', 'N/A')
    row += 2
    
    # Skills Matched
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "SKILLS MATCHED ✓"
    cell.font = header_font
    cell.fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
    cell.alignment = Alignment(horizontal='center')
    row += 1
    
    for i, skill in enumerate(analysis_data.get('skills_matched', [])[:8], 1):
        ws[f'A{row}'] = f"{i}."
        ws[f'B{row}'] = skill
        ws[f'B{row}'].alignment = Alignment(wrap_text=True)
        row += 1
    
    row += 1
    
    # Skills Missing
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "SKILLS MISSING ✗"
    cell.font = header_font
    cell.fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
    cell.alignment = Alignment(horizontal='center')
    row += 1
    
    for i, skill in enumerate(analysis_data.get('skills_missing', [])[:8], 1):
        ws[f'A{row}'] = f"{i}."
        ws[f'B{row}'] = skill
        ws[f'B{row}'].alignment = Alignment(wrap_text=True)
        row += 1
    
    row += 1
    
    # Experience
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
    
    # Education
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
    
    # Strengths
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
    
    # Improvements
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
    
    # Apply borders
    for row_cells in ws.iter_rows(min_row=1, max_row=row, min_col=1, max_col=2):
        for cell in row_cells:
            cell.border = border
    
    # Save file
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    wb.save(filepath)
    print(f"📄 Excel report saved: {filepath}")
    return filepath

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Main endpoint to analyze resume"""
    try:
        print("\n" + "="*50)
        print("📥 New analysis request received")
        
        if 'resume' not in request.files:
            print("❌ No resume file")
            return jsonify({'error': 'No resume file provided'}), 400
        
        if 'jobDescription' not in request.form:
            print("❌ No job description")
            return jsonify({'error': 'No job description provided'}), 400
        
        resume_file = request.files['resume']
        job_description = request.form['jobDescription']
        
        if resume_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file size
        resume_file.seek(0, 2)
        file_size = resume_file.tell()
        resume_file.seek(0)
        
        if file_size > 10 * 1024 * 1024:
            return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 400
        
        # Save file
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"resume_{timestamp}{file_ext}")
        resume_file.save(file_path)
        print(f"💾 File saved: {file_path}")
        
        # Extract text
        print(f"📖 Extracting text...")
        if file_ext == '.pdf':
            resume_text = extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            resume_text = extract_text_from_docx(file_path)
        elif file_ext == '.txt':
            resume_text = extract_text_from_txt(file_path)
        else:
            return jsonify({'error': 'Unsupported file format. Use PDF, DOCX, or TXT'}), 400
        
        if resume_text.startswith('Error'):
            print(f"❌ Text extraction error")
            return jsonify({'error': resume_text}), 500
        
        print(f"✅ Extracted {len(resume_text)} characters")
        
        # Analyze
        print(f"🤖 Analyzing...")
        if GEMINI_AVAILABLE and client:
            analysis = analyze_resume_with_gemini(resume_text, job_description)
        else:
            analysis = get_enhanced_text_analysis(resume_text, job_description)
        
        # Create Excel report
        print("📊 Creating Excel report...")
        excel_filename = f"analysis_{timestamp}.xlsx"
        excel_path = create_excel_report(analysis, excel_filename)
        
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['success'] = True
        
        print(f"✅ Analysis completed. Score: {analysis.get('overall_score')}")
        print(f"  Name: {analysis.get('candidate_name')}")
        print(f"  Mode: {analysis.get('analysis_mode', 'text_analysis')}")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    """Download Excel report"""
    try:
        import re
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=safe_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        'status': 'Running',
        'timestamp': datetime.now().isoformat(),
        'ai_available': GEMINI_AVAILABLE,
        'upload_folder': UPLOAD_FOLDER,
        'mode': 'text_analysis_only' if not GEMINI_AVAILABLE else 'ai_enabled'
    })

@app.route('/test-key', methods=['GET'])
def test_key():
    """Test API key"""
    if not api_key:
        return jsonify({
            'status': 'no_key',
            'message': 'No API key configured',
            'instructions': 'Add GEMINI_API_KEY environment variable',
            'get_key_url': 'https://aistudio.google.com/app/apikey'
        })
    
    if GEMINI_AVAILABLE:
        return jsonify({
            'status': 'valid',
            'message': 'API key is valid and working',
            'key_preview': api_key[:10] + '...'
        })
    else:
        return jsonify({
            'status': 'invalid',
            'message': 'API key is invalid or not working',
            'key_preview': api_key[:10] + '...',
            'troubleshooting': [
                '1. Get a new key from: https://aistudio.google.com/app/apikey',
                '2. Make sure Gemini API is enabled in Google Cloud Console',
                '3. Check billing is enabled for your project'
            ]
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    
    print(f"\n🌐 Server starting on port {port}")
    print(f"📊 Mode: {'AI Enabled' if GEMINI_AVAILABLE else 'Text Analysis Only'}")
    print(f"📁 Uploads: {UPLOAD_FOLDER}")
    print("="*50)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
