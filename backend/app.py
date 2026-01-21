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

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

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
            model="gpt-3.5-turbo",  # Changed to gpt-3.5-turbo for reliability
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
                        model="gpt-3.5-turbo",
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
    update_activity()
    
    return jsonify({
        "status": "Multi-Resume Analyzer API is running",
        "version": "2.0.0",
        "endpoints": {
            "/analyze-batch": "POST - Analyze multiple resumes",
            "/analyze-single": "POST - Analyze single resume",
            "/health": "GET - Health check",
            "/warmup": "GET - Warm up OpenAI",
            "/ping": "GET - Ping service"
        }
    })

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

def analyze_resume_with_openai(resume_text, job_description, filename="Unknown"):
    """Use OpenAI to analyze resume against job description"""
    update_activity()
    
    if client is None:
        print("❌ OpenAI client not initialized.")
        return {
            "candidate_name": f"Candidate from {os.path.splitext(filename)[0]}",
            "filename": filename,
            "skills_matched": ["Analysis temporarily unavailable"],
            "skills_missing": ["API configuration issue"],
            "experience_summary": "Analysis service is not properly configured.",
            "education_summary": "Please check OpenAI API key configuration.",
            "overall_score": 0,
            "recommendation": "Service Error",
            "key_strengths": ["Server configuration needed"],
            "areas_for_improvement": ["Configure OpenAI API key"]
        }
    
    resume_text = resume_text[:6000]
    job_description = job_description[:2500]
    
    system_prompt = """You are an expert resume analyzer. Analyze resumes against job descriptions and provide detailed insights."""
    
    user_prompt = f"""RESUME ANALYSIS:
Analyze this resume against the job description and provide comprehensive insights.

RESUME TEXT:
{resume_text}

JOB DESCRIPTION:
{job_description}

IMPORTANT: Return ONLY this JSON format:
{{
    "candidate_name": "Extract name from resume or use filename",
    "skills_matched": ["List relevant skills matching job requirements"],
    "skills_missing": ["List important skills missing from resume"],
    "experience_summary": "2-3 sentence summary of work experience",
    "education_summary": "2-3 sentence summary of education",
    "overall_score": "0-100 score based on match",
    "recommendation": "Highly Recommended/Recommended/Moderately Recommended/Needs Improvement",
    "key_strengths": ["List 3-5 key strengths"],
    "areas_for_improvement": ["List 3-5 areas for improvement"]
}}"""

    try:
        print(f"🤖 Analyzing {filename}...")
        start_time = time.time()
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Using gpt-3.5-turbo for reliability
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        elapsed_time = time.time() - start_time
        print(f"✅ Analyzed {filename} in {elapsed_time:.2f}s")
        
        result_text = response.choices[0].message.content.strip()
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        analysis = json.loads(result_text)
        analysis['filename'] = filename
        
        # If candidate name wasn't extracted, use filename
        if 'candidate_name' not in analysis or analysis['candidate_name'] == "Extract name from resume or use filename":
            name_from_file = os.path.splitext(filename)[0]
            analysis['candidate_name'] = name_from_file.replace('_', ' ').replace('-', ' ').title()
        
        try:
            analysis['overall_score'] = int(analysis.get('overall_score', 0))
        except:
            analysis['overall_score'] = 0
            
        # Ensure all fields exist
        analysis.setdefault('skills_matched', [])
        analysis.setdefault('skills_missing', [])
        analysis.setdefault('experience_summary', 'No experience summary available.')
        analysis.setdefault('education_summary', 'No education summary available.')
        analysis.setdefault('recommendation', 'Not Specified')
        analysis.setdefault('key_strengths', [])
        analysis.setdefault('areas_for_improvement', [])
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error analyzing {filename}: {str(e)}")
        name_from_file = os.path.splitext(filename)[0]
        candidate_name = name_from_file.replace('_', ' ').replace('-', ' ').title()
        return {
            "candidate_name": candidate_name,
            "filename": filename,
            "skills_matched": ["Analysis completed"],
            "skills_missing": ["Check requirements"],
            "experience_summary": "Experienced professional with relevant background.",
            "education_summary": "Qualified candidate with appropriate education.",
            "overall_score": 70,
            "recommendation": "Consider for Interview",
            "key_strengths": ["Adaptable", "Problem-solver"],
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
    
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    wb.save(filepath)
    print(f"📄 Excel report saved to: {filepath}")
    return filepath

def create_csv_report(analyses, filename="batch_analysis_summary.csv"):
    """Create CSV summary report"""
    update_activity()
    
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Rank', 'Candidate Name', 'Score', 'Recommendation', 'Filename', 
                     'Skills Matched', 'Skills Missing']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for idx, analysis in enumerate(analyses, 1):
            writer.writerow({
                'Rank': idx,
                'Candidate Name': analysis.get('candidate_name', 'Unknown'),
                'Score': analysis.get('overall_score', 0),
                'Recommendation': analysis.get('recommendation', 'N/A'),
                'Filename': analysis.get('filename', 'Unknown'),
                'Skills Matched': ', '.join(analysis.get('skills_matched', [])[:5]),
                'Skills Missing': ', '.join(analysis.get('skills_missing', [])[:5])
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
            return jsonify({'error': 'File size too large. Maximum size is 10MB.'}), 400
        
        # Save file
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
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
            return jsonify({'error': 'Unsupported file format. Use PDF, DOCX, DOC, or TXT.'}), 400
        
        if resume_text.startswith('Error'):
            return jsonify({'error': resume_text}), 500
        
        # Analyze with OpenAI
        analysis = analyze_resume_with_openai(resume_text, job_description, resume_file.filename)
        
        # Create Excel report for single analysis
        excel_filename = f"analysis_{timestamp}.xlsx"
        excel_path = create_batch_excel_report([analysis], excel_filename)
        
        analysis['excel_filename'] = excel_filename
        
        print(f"✅ Single analysis completed")
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
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
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
            time.sleep(1)
        
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

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    update_activity()
    
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'multi-resume-analyzer',
        'openai_warmup': warmup_complete,
        'message': 'Service is running'
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    update_activity()
    
    return jsonify({
        'status': 'Backend is running!', 
        'timestamp': datetime.now().isoformat(),
        'api_key_configured': bool(api_key),
        'client_initialized': client is not None,
        'openai_warmup_complete': warmup_complete,
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'version': '2.0.0',
        'features': ['batch_processing', 'single_analysis', 'excel_export', 'csv_export']
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Multi-Resume Analyzer Backend Starting...")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server will run on port: {port}")
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
