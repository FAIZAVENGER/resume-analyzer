from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PyPDF2 import PdfReader
from docx import Document
import os
import json
import re
import requests
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

# Load API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip()
AI_ENABLED = False

if OPENAI_API_KEY and len(OPENAI_API_KEY) > 10:
    print(f"✅ OpenAI API Key found: {OPENAI_API_KEY[:10]}...")
    
    # Test OpenAI API
    try:
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Simple test request
        test_data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Say 'OK'"}],
            "max_tokens": 5
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=test_data,
            timeout=10
        )
        
        if response.status_code == 200:
            AI_ENABLED = True
            print("✅ OpenAI API is working!")
        else:
            print(f"❌ OpenAI test failed: HTTP {response.status_code}")
            print(f"Response: {response.text[:100]}")
            
    except Exception as e:
        print(f"❌ OpenAI connection error: {str(e)[:100]}")
else:
    print("⚠️  No OpenAI API key found")

# Get upload folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"📁 Upload folder: {UPLOAD_FOLDER}")

print("\n📊 Service Summary:")
print(f"   OpenAI AI: {'✅ Enabled' if AI_ENABLED else '⚠️ Disabled'}")
print(f"   Text Analysis: ✅ Always Available")
print("=" * 50 + "\n")

# ========== ENHANCED TEXT ANALYSIS ==========

def extract_name_from_resume(text):
    """Extract candidate name from resume"""
    if not text:
        return "Professional Candidate"
    
    lines = text.split('\n')[:20]
    
    patterns = [
        r'^([A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?)',
        r'Name[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
        r'Full Name[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
        r'Contact Information\s*\n([A-Z][a-z]+ [A-Z][a-z]+)',
    ]
    
    for line in lines:
        line = line.strip()
        if 3 < len(line) < 50:
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    if len(name.split()) >= 2:
                        return name.title()
    
    # Check for email signature
    for line in lines:
        email_match = re.search(r'([A-Z][a-z]+ [A-Z][a-z]+)\s*<[^>]+>', line)
        if email_match:
            return email_match.group(1).strip().title()
    
    return "Professional Candidate"

def extract_skills_from_resume(text):
    """Extract skills from resume"""
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
        skill_items = re.split(r'[,\n•\-]', skills_text)
        for item in skill_items:
            item = item.strip()
            if 2 < len(item) < 30 and not re.search(r'\d{4}', item):
                found_skills.append(item)
    
    # Remove duplicates
    unique_skills = []
    for skill in found_skills:
        if skill not in unique_skills:
            unique_skills.append(skill)
    
    return unique_skills[:10]

def extract_experience_summary(text):
    """Extract experience summary"""
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(word in line_lower for word in ['experience', 'work history', 'employment', 'professional']):
            context = []
            for j in range(i+1, min(i+6, len(lines))):
                context_line = lines[j].strip()
                if context_line and len(context_line) < 200:
                    context.append(context_line)
            if context:
                summary = " ".join(context[:3])
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                return summary
    
    # Look for years
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
    """Extract education summary"""
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(word in line_lower for word in ['education', 'university', 'college', 'degree', 'bachelor', 'master']):
            context = []
            for j in range(i, min(i+4, len(lines))):
                context_line = lines[j].strip()
                if context_line and len(context_line) < 150:
                    context.append(context_line)
            if context:
                summary = " ".join(context[:2])
                if len(summary) > 150:
                    summary = summary[:150] + "..."
                return summary
    
    return "Qualified candidate with appropriate educational background."

def calculate_match_score(resume_text, job_description):
    """Calculate match score between resume and job"""
    base_score = 65
    
    # Experience bonus
    if any(word in resume_text.lower() for word in ['experience', 'worked', 'years', 'professional']):
        base_score += 10
    
    # Education bonus
    if any(word in resume_text.lower() for word in ['degree', 'university', 'college', 'bachelor', 'master', 'phd']):
        base_score += 8
    
    # Skills match
    if job_description:
        skills = extract_skills_from_resume(resume_text)
        job_desc_lower = job_description.lower()
        matched = 0
        
        for skill in skills:
            if skill.lower() in job_desc_lower:
                matched += 1
        
        if matched >= 5:
            base_score += 15
        elif matched >= 3:
            base_score += 10
        elif matched >= 1:
            base_score += 5
    
    # Ensure score is within reasonable range
    return min(max(base_score, 50), 95)

def get_text_analysis(resume_text, job_description):
    """Get analysis using text extraction"""
    candidate_name = extract_name_from_resume(resume_text)
    extracted_skills = extract_skills_from_resume(resume_text)
    experience_summary = extract_experience_summary(resume_text)
    education_summary = extract_education_summary(resume_text)
    overall_score = calculate_match_score(resume_text, job_description)
    
    # Match skills with job
    skills_matched = []
    skills_missing = []
    
    if job_description:
        job_desc_lower = job_description.lower()
        for skill in extracted_skills:
            if skill.lower() in job_desc_lower:
                skills_matched.append(skill)
            else:
                skills_missing.append(skill)
    
    # Add defaults if needed
    if not skills_matched:
        skills_matched = ["Communication Skills", "Problem Solving", "Team Collaboration"]
    
    if len(skills_missing) < 3:
        skills_missing.extend(["Industry certifications", "Advanced training", "Leadership experience"])
    
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
        "areas_for_improvement": skills_missing[:4] if skills_missing else ["Additional training", "More experience"],
        "analysis_mode": "text_analysis",
        "ai_enabled": AI_ENABLED
    }

def analyze_with_openai(resume_text, job_description):
    """Analyze using OpenAI GPT"""
    if not AI_ENABLED:
        return get_text_analysis(resume_text, job_description)
    
    try:
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        prompt = f"""Analyze this resume against the job description:

RESUME:
{resume_text[:4000]}

JOB DESCRIPTION:
{job_description[:2000]}

Extract information and provide analysis. Return ONLY valid JSON with these exact fields:
{{
    "candidate_name": "Extract name from resume or use 'Professional Candidate'",
    "skills_matched": ["list skills from resume that match job requirements"],
    "skills_missing": ["list important job skills not found in resume"],
    "experience_summary": "Brief summary of work experience",
    "education_summary": "Brief summary of education",
    "overall_score": "Number between 0-100",
    "recommendation": "Highly Recommended/Recommended/Consider/Needs Improvement",
    "key_strengths": ["list 3-4 key strengths"],
    "areas_for_improvement": ["list 3-4 areas to improve"]
}}"""
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a professional resume analyzer. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 1500
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Clean response
            content = content.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON
            analysis = json.loads(content)
            
            # Ensure score is numeric
            try:
                analysis['overall_score'] = int(analysis['overall_score'])
                if analysis['overall_score'] > 100:
                    analysis['overall_score'] = 100
                elif analysis['overall_score'] < 0:
                    analysis['overall_score'] = 0
            except:
                analysis['overall_score'] = 75
            
            analysis['analysis_mode'] = "ai_analysis"
            analysis['ai_enabled'] = True
            
            print(f"✅ OpenAI analysis successful")
            return analysis
            
        else:
            print(f"❌ OpenAI API error: {response.status_code}")
            return get_text_analysis(resume_text, job_description)
            
    except Exception as e:
        print(f"❌ OpenAI error: {str(e)[:100]}")
        return get_text_analysis(resume_text, job_description)

# ========== FILE EXTRACTION ==========

def extract_text_from_pdf(file_path):
    """Extract text from PDF"""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        if not text.strip():
            return "Error: PDF appears to be empty"
        
        return text[:10000]  # Limit size
        
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def extract_text_from_docx(file_path):
    """Extract text from DOCX"""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
        
        if not text.strip():
            return "Error: Document appears to be empty"
        
        return text[:10000]  # Limit size
        
    except Exception as e:
        return f"Error reading DOCX: {str(e)}"

def extract_text_from_txt(file_path):
    """Extract text from TXT"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        
        if not text.strip():
            return "Error: Text file appears to be empty"
        
        return text[:10000]  # Limit size
        
    except Exception as e:
        return f"Error reading TXT: {str(e)}"

# ========== EXCEL REPORT ==========

def create_excel_report(analysis_data, filename):
    """Create beautiful Excel report"""
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
    mode_text = "AI Analysis (OpenAI)" if mode == "ai_analysis" else "Text Analysis"
    mode_color = "70AD47" if mode == "ai_analysis" else "FF9900"
    ws[f'B{row}'] = mode_text
    ws[f'B{row}'].font = Font(color=mode_color, bold=True)
    row += 2
    
    # Score
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
    return filepath

# ========== FLASK ROUTES ==========

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
<html>
<head>
    <title>Resume Analyzer</title>
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
            font-weight: 600;
        }
        
        .success { color: #27ae60; }
        .warning { color: #f39c12; }
        .info { color: #3498db; }
        
        .features {
            text-align: left;
            margin: 30px 0;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
        }
        
        .feature-item {
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid #e9ecef;
        }
        
        .feature-item:last-child {
            border-bottom: none;
        }
        
        .endpoints {
            text-align: left;
            margin: 30px 0;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
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
        }
        
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        
        .footer {
            margin-top: 40px;
            color: #7f8c8d;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 Resume Analyzer</h1>
        <p class="subtitle">Professional Resume Analysis with OpenAI</p>
        
        <div class="api-status">
            ✅ SERVICE IS LIVE
        </div>
        
        <div class="status-card">
            <div class="status-item">
                <span class="status-label">Service Status:</span>
                <span class="status-value success">Online</span>
            </div>
            <div class="status-item">
                <span class="status-label">OpenAI AI:</span>
                <span class="status-value ''' + ('success' if AI_ENABLED else 'warning') + '''">
                    ''' + ('✅ Enabled' if AI_ENABLED else '⚠️ Add OpenAI Key') + '''
                </span>
            </div>
            <div class="status-item">
                <span class="status-label">Text Analysis:</span>
                <span class="status-value success">✅ Always Available</span>
            </div>
        </div>
        
        <div class="features">
            <h3>✨ Features:</h3>
            <div class="feature-item">✅ Resume Upload (PDF, DOCX, TXT)</div>
            <div class="feature-item">✅ AI-Powered Analysis ''' + ('(Enabled)' if AI_ENABLED else '(Add OPENAI_API_KEY)') + '''</div>
            <div class="feature-item">✅ Enhanced Text Analysis</div>
            <div class="feature-item">✅ Skill Matching & Scoring</div>
            <div class="feature-item">✅ Professional Excel Reports</div>
            <div class="feature-item">✅ Candidate Name Extraction</div>
        </div>
        
        ''' + ('''
        <div style="background: #e8f5e8; border: 2px solid #4CAF50; border-radius: 10px; padding: 20px; margin: 20px 0;">
            <h3 style="color: #2e7d32; margin-top: 0;">✅ OpenAI is Ready!</h3>
            <p>Your OpenAI API key is working perfectly.</p>
            <p>Upload resumes for AI-powered analysis.</p>
        </div>
        ''' if AI_ENABLED else '''
        <div style="background: #fff3cd; border: 2px solid #ffc107; border-radius: 10px; padding: 20px; margin: 20px 0;">
            <h3 style="color: #856404; margin-top: 0;">🔑 Add OpenAI API Key</h3>
            <p>To enable AI analysis, add your OpenAI API key:</p>
            <ol style="text-align: left; margin: 10px 20px;">
                <li>Get key from: <a href="https://platform.openai.com/api-keys" target="_blank">OpenAI Platform</a></li>
                <li>In Render dashboard, go to Environment</li>
                <li>Add variable: <code>OPENAI_API_KEY=your_key_here</code></li>
                <li>Redeploy the application</li>
            </ol>
            <p><strong>Note:</strong> Text analysis works perfectly even without AI!</p>
        </div>
        ''') + '''
        
        <div class="endpoints">
            <h3>📡 API Endpoints:</h3>
            <div class="endpoint">
                <span class="method">POST</span>
                <span>/analyze</span>
                <p>Upload resume with job description</p>
            </div>
            <div class="endpoint">
                <span class="method">GET</span>
                <span>/health</span>
                <p>Check service status</p>
            </div>
            <div class="endpoint">
                <span class="method">GET</span>
                <span>/test</span>
                <p>Test with sample data</p>
            </div>
        </div>
        
        <div style="margin-top: 30px;">
            <a href="/health" class="btn">Check Health</a>
            <a href="/test" class="btn">Test Analysis</a>
        </div>
        
        <div class="footer">
            <p>Powered by Flask & OpenAI | Deployed on Render</p>
            <p>Visit: <a href="https://resume-analyzer-1-pevo.onrender.com">https://resume-analyzer-1-pevo.onrender.com</a></p>
        </div>
    </div>
</body>
</html>
    '''

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Main analysis endpoint"""
    try:
        print("\n" + "="*50)
        print("📥 New analysis request")
        
        if 'resume' not in request.files:
            return jsonify({'error': 'No resume file provided'}), 400
        
        if 'jobDescription' not in request.form:
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
            return jsonify({'error': 'File too large (max 10MB)'}), 400
        
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
            return jsonify({'error': resume_text}), 500
        
        print(f"✅ Extracted {len(resume_text)} characters")
        
        # Analyze
        print(f"🤖 Analyzing with {'OpenAI' if AI_ENABLED else 'Text Analysis'}...")
        analysis = analyze_with_openai(resume_text, job_description)
        
        # Create Excel report
        print("📊 Creating Excel report...")
        excel_filename = f"analysis_{timestamp}.xlsx"
        excel_path = create_excel_report(analysis, excel_filename)
        
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['success'] = True
        
        print(f"✅ Analysis complete. Score: {analysis.get('overall_score')}")
        print(f"  Name: {analysis.get('candidate_name')}")
        print(f"  Mode: {analysis.get('analysis_mode')}")
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
    """Health endpoint"""
    return jsonify({
        'status': 'Running',
        'timestamp': datetime.now().isoformat(),
        'openai_enabled': AI_ENABLED,
        'text_analysis': 'always_available',
        'upload_folder': UPLOAD_FOLDER,
        'service_url': 'https://resume-analyzer-1-pevo.onrender.com'
    })

@app.route('/test', methods=['GET'])
def test_analysis():
    """Test endpoint with sample data"""
    sample_resume = """John Smith
Software Engineer
(123) 456-7890 | john.smith@email.com | LinkedIn: linkedin.com/in/johnsmith

PROFESSIONAL SUMMARY
Experienced software engineer with 5+ years in full-stack development. 
Specialized in Python, React, and cloud technologies.

WORK EXPERIENCE
Senior Software Engineer, Tech Innovations Inc.
January 2020 - Present
- Led development of customer-facing web applications using React and Python
- Implemented RESTful APIs serving 10,000+ daily requests
- Reduced server costs by 30% through AWS optimization
- Mentored 3 junior developers

Software Developer, Digital Solutions Corp.
June 2017 - December 2019
- Developed and maintained e-commerce platforms
- Integrated payment gateways and shipping APIs
- Improved application performance by 40%

EDUCATION
Bachelor of Science in Computer Science
University of Technology, 2013-2017
GPA: 3.8/4.0

SKILLS
Programming: Python, JavaScript, TypeScript, Java
Frameworks: React, Node.js, Flask, Django
Databases: MySQL, PostgreSQL, MongoDB
Cloud: AWS (EC2, S3, Lambda), Docker, Kubernetes
Tools: Git, Jenkins, Jira, Postman"""

    sample_job = """Software Engineer Position

We are looking for a skilled Software Engineer to join our team.

Requirements:
- 3+ years of software development experience
- Strong proficiency in Python and JavaScript
- Experience with React or similar frontend frameworks
- Knowledge of REST API development
- Familiarity with cloud platforms (AWS preferred)
- Experience with databases (SQL and NoSQL)
- Strong problem-solving skills
- Good communication and teamwork abilities

Nice to have:
- Experience with Docker and Kubernetes
- Knowledge of CI/CD pipelines
- Understanding of microservices architecture
- Previous experience in agile development"""

    analysis = analyze_with_openai(sample_resume, sample_job)
    
    return jsonify({
        'test': 'success',
        'analysis': analysis,
        'note': 'This is a test analysis using sample resume and job description'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    
    print(f"\n🌐 Server starting on port {port}")
    print(f"🤖 OpenAI: {'✅ ENABLED' if AI_ENABLED else '⚠️ DISABLED (Add OPENAI_API_KEY)'}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print("="*50)
    print("\n✅ Service is ready!")
    print(f"   URL: https://resume-analyzer-1-pevo.onrender.com")
    print("\n📝 Test endpoints:")
    print(f"   • /test - Test analysis with sample data")
    print(f"   • /health - Check service status")
    print("="*50)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
