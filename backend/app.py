from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google import genai  # Correct import for new SDK
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

# Configure Gemini AI - NEW SYNTAX
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY not found in .env file!")
    print("Please create a .env file with: GEMINI_API_KEY=your_key_here")
    client = None
else:
    print(f"✅ API Key loaded: {api_key[:10]}...")
    # Create client with API key - NEW SYNTAX
    client = genai.Client(api_key=api_key)  

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

def analyze_resume_with_gemini(resume_text, job_description):
    """Use Gemini AI to analyze resume against job description"""
    
    # Check if client is initialized
    if client is None:
        print("❌ Gemini client not initialized. Check API key.")
        return {
            "candidate_name": "API Error",
            "skills_matched": [],
            "skills_missing": [],
            "experience_summary": "Gemini API not configured properly. Check your API key.",
            "education_summary": "Please ensure GEMINI_API_KEY is set in .env file",
            "overall_score": 0,
            "recommendation": "Configuration Error",
            "key_strengths": [],
            "areas_for_improvement": []
        }
    
    prompt = f"""
You are an expert HR recruiter. Analyze the following resume against the job description and provide a detailed analysis.

RESUME:
{resume_text[:10000]}

JOB DESCRIPTION:
{job_description[:5000]}

IMPORTANT: You MUST return ONLY valid JSON. Do not include any markdown formatting, code blocks, or additional text.

Return your analysis in this exact JSON format:
{{
    "candidate_name": "Extract candidate name from resume or use 'Unknown Candidate'",
    "skills_matched": ["skill1", "skill2", "skill3"],
    "skills_missing": ["skill4", "skill5"],
    "experience_summary": "Brief summary of candidate's relevant experience",
    "education_summary": "Brief summary of candidate's education",
    "overall_score": 85,
    "recommendation": "Brief recommendation (Highly Recommended/Recommended/Not Recommended)",
    "key_strengths": ["strength1", "strength2", "strength3"],
    "areas_for_improvement": ["area1", "area2"]
}}

Guidelines:
1. Extract the candidate's name from the resume. If not found, use "Unknown Candidate"
2. Overall score should be between 0-100 based on match percentage
3. Make skill lists specific and relevant
4. Keep summaries concise (1-2 sentences)
5. Recommendation should match the score
6. Return ONLY the JSON, nothing else
"""

    try:
        print("🤖 Sending request to Gemini AI...")
        
        # FIXED LINE: Changed from "gemini-1.5-pro" to "gemini-2.5-flash"
        response = client.models.generate_content(
            model="gemini-2.5-flash",  # ← CRITICAL FIX: Use working model
            contents=prompt
        )
        
        result_text = response.text.strip()
        
        print(f"📥 Received response length: {len(result_text)} characters")
        print(f"Response preview: {result_text[:200]}...")
        
        # Clean the response - remove markdown code blocks if present
        if '```json' in result_text:
            result_text = result_text.replace('```json', '').replace('```', '').strip()
        elif '```' in result_text:
            result_text = result_text.replace('```', '').strip()
        
        # Try to parse JSON
        analysis = json.loads(result_text)
        print("✅ Successfully parsed JSON response")
        
        # Ensure all required fields exist
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
                    analysis[field] = "Not available"
        
        return analysis
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parsing Error: {e}")
        print(f"Response was: {result_text[:500]}")
        
        # Create a fallback response
        return {
            "candidate_name": "AI Parse Error - Check Console",
            "skills_matched": ["Could not parse AI response"],
            "skills_missing": ["Please check the response format"],
            "experience_summary": f"Error parsing AI response. Please try again. Details: {str(e)[:100]}",
            "education_summary": "Please ensure your API key is valid and try again",
            "overall_score": 0,
            "recommendation": "Error - Please retry analysis",
            "key_strengths": ["AI response parsing failed"],
            "areas_for_improvement": ["Check backend logs for details"]
        }
    except Exception as e:
        print(f"❌ Gemini API Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        
        return {
            "candidate_name": "API Error",
            "skills_matched": [],
            "skills_missing": [],
            "experience_summary": f"API Error: {str(e)}",
            "education_summary": "Check your API key and try again",
            "overall_score": 0,
            "recommendation": "Error occurred during analysis",
            "key_strengths": [],
            "areas_for_improvement": ["Verify Gemini API configuration"]
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
    ws[f'B{row}'].font = Font(bold=True, size=12, color="C00000")
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
    
    # Save the file
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    wb.save(filepath)
    return filepath

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Main endpoint to analyze resume"""
    
    try:
        print("\n" + "="*50)
        print("📥 New analysis request received")
        
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
        
        # Save the uploaded file
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        file_path = os.path.join(UPLOAD_FOLDER, f"resume_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}")
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
        
        # Check if API key is configured
        if not api_key:
            print("❌ API key not configured")
            return jsonify({'error': 'API key not configured. Please add GEMINI_API_KEY to .env file'}), 500
        
        if client is None:
            print("❌ Gemini client not initialized")
            return jsonify({'error': 'Gemini AI client not properly initialized'}), 500
        
        # Analyze with Gemini AI
        print("🤖 Starting AI analysis...")
        analysis = analyze_resume_with_gemini(resume_text, job_description)
        
        print(f"✅ Analysis completed. Score: {analysis.get('overall_score', 0)}")
        
        # Create Excel report
        print("📊 Creating Excel report...")
        excel_path = create_excel_report(analysis)
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
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    return jsonify({'error': 'File not found'}), 404

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'Backend is running!', 
        'timestamp': datetime.now().isoformat(),
        'api_key_configured': bool(api_key),
        'client_initialized': client is not None
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting...")
    print("="*50)
    print(f"📍 Server: http://localhost:5001")
    print(f"🔑 API Key: {'✅ Configured' if api_key else '❌ NOT FOUND'}")
    print(f"🤖 Gemini Client: {'✅ Initialized' if client else '❌ NOT INITIALIZED'}")
    print(f"📁 Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print("="*50 + "\n")
    
    if not api_key:
        print("⚠️  WARNING: GEMINI_API_KEY not found!")
        print("Please create a .env file with: GEMINI_API_KEY=your_key_here\n")
        print("Get your API key from: https://makersuite.google.com/app/apikey")
    
    app.run(debug=True, port=5002)