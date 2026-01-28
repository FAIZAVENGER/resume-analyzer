from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import json
import time
import hashlib
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
import traceback
import threading
import atexit
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import re

# Import our custom modules
from nlp_processor import NLPProcessor
from resume_parser import ResumeParser
from scoring_engine import ScoringEngine
from ai_engine import AIEngine

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

# CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
REPORTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
AI_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ai_models')
MAX_BATCH_SIZE = 20
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)
os.makedirs(AI_MODEL_PATH, exist_ok=True)

# Initialize AI Engine
print("🤖 Initializing AI Engine...")
try:
    nlp_processor = NLPProcessor()
    nlp_processor.initialize_model()
    resume_parser = ResumeParser()
    scoring_engine = ScoringEngine()
    ai_engine = AIEngine()
    print("✅ AI Engine initialized successfully!")
except Exception as e:
    print(f"❌ AI Engine initialization failed: {e}")
    raise

# Global variables
service_running = True
analysis_cache = {}  # Simple in-memory cache
skill_trends = {}    # In-memory skill tracking

# Background cleanup thread
def cleanup_old_files():
    """Clean up old uploaded files periodically"""
    while service_running:
        try:
            time.sleep(3600)  # Run every hour
            
            now = time.time()
            cutoff = now - (24 * 3600)  # 24 hours
            
            # Clean uploads folder
            for filename in os.listdir(UPLOAD_FOLDER):
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.isfile(filepath):
                    if os.path.getmtime(filepath) < cutoff:
                        os.remove(filepath)
                        print(f"🗑️ Cleaned up old file: {filename}")
            
            # Clean reports folder (keep for 7 days)
            report_cutoff = now - (7 * 24 * 3600)
            for filename in os.listdir(REPORTS_FOLDER):
                filepath = os.path.join(REPORTS_FOLDER, filename)
                if os.path.isfile(filepath):
                    if os.path.getmtime(filepath) < report_cutoff:
                        os.remove(filepath)
                        print(f"🗑️ Cleaned up old report: {filename}")
                        
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

def generate_analysis_id():
    """Generate unique analysis ID"""
    return str(uuid.uuid4())

def calculate_hash(content: str) -> str:
    """Calculate SHA-256 hash of content"""
    return hashlib.sha256(content.encode()).hexdigest()

def get_cached_analysis(resume_hash: str, job_hash: str) -> dict:
    """Get cached analysis if available"""
    cache_key = f"{resume_hash}:{job_hash}"
    
    # Check memory cache
    if cache_key in analysis_cache:
        cached_data = analysis_cache[cache_key]
        if datetime.now() < cached_data['expires']:
            return cached_data['analysis']
    
    return None

def set_cached_analysis(resume_hash: str, job_hash: str, analysis: dict):
    """Cache analysis result"""
    cache_key = f"{resume_hash}:{job_hash}"
    expires = datetime.now() + timedelta(hours=24)
    
    # Store in memory cache
    analysis_cache[cache_key] = {
        'analysis': analysis,
        'expires': expires
    }

def update_skill_trends(skills: list):
    """Update skill trends in memory"""
    for skill in skills:
        if skill in skill_trends:
            skill_trends[skill] += 1
        else:
            skill_trends[skill] = 1
    
    # Keep only top 100 skills to prevent memory bloat
    if len(skill_trends) > 100:
        # Sort by frequency and keep top 100
        top_skills = sorted(skill_trends.items(), key=lambda x: x[1], reverse=True)[:100]
        skill_trends.clear()
        skill_trends.update(dict(top_skills))

def create_excel_report(analysis_data: dict, filename: str = None) -> str:
    """Create Excel report from analysis data"""
    if not filename:
        filename = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    filepath = os.path.join(REPORTS_FOLDER, filename)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Resume Analysis"
    
    # Styles
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Column widths
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 50
    
    row = 1
    
    # Title
    ws.merge_cells(f'A{row}:B{row}')
    title_cell = ws[f'A{row}']
    title_cell.value = "AI Resume Analysis Report"
    title_cell.font = Font(bold=True, size=14, color="FFFFFF")
    title_cell.fill = PatternFill(start_color="2c3e50", end_color="2c3e50", fill_type="solid")
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    row += 2
    
    # Basic Information
    info_data = [
        ("Candidate Name", analysis_data.get('candidate_name', 'N/A')),
        ("Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("ATS Score", f"{analysis_data.get('overall_score', 0)}/100"),
        ("Grade", analysis_data.get('grade', 'N/A')),
        ("Recommendation", analysis_data.get('recommendation', 'N/A')),
        ("AI Engine", analysis_data.get('ai_engine', 'Self-Hosted AI')),
        ("Experience Level", analysis_data.get('experience_level', 'N/A')),
        ("Industry Fit", analysis_data.get('industry_fit', 'N/A'))
    ]
    
    for label, value in info_data:
        ws[f'A{row}'] = label
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'A{row}'].border = border
        ws[f'B{row}'] = value
        ws[f'B{row}'].border = border
        row += 1
    
    row += 1
    
    # Skills Matched
    ws.merge_cells(f'A{row}:B{row}')
    skills_header = ws[f'A{row}']
    skills_header.value = "SKILLS MATCHED"
    skills_header.font = header_font
    skills_header.fill = PatternFill(start_color="27ae60", end_color="27ae60", fill_type="solid")
    skills_header.alignment = Alignment(horizontal='center')
    skills_header.border = border
    row += 1
    
    skills_matched = analysis_data.get('skills_matched', [])
    if skills_matched:
        for i, skill in enumerate(skills_matched, 1):
            ws[f'A{row}'] = f"{i}."
            ws[f'A{row}'].border = border
            ws[f'B{row}'] = skill
            ws[f'B{row}'].border = border
            row += 1
    else:
        ws[f'A{row}'] = "No matched skills found"
        ws[f'A{row}'].border = border
        ws.merge_cells(f'A{row}:B{row}')
        row += 1
    
    row += 1
    
    # Skills Missing
    ws.merge_cells(f'A{row}:B{row}')
    missing_header = ws[f'A{row}']
    missing_header.value = "SKILLS MISSING"
    missing_header.font = header_font
    missing_header.fill = PatternFill(start_color="e74c3c", end_color="e74c3c", fill_type="solid")
    missing_header.alignment = Alignment(horizontal='center')
    missing_header.border = border
    row += 1
    
    skills_missing = analysis_data.get('skills_missing', [])
    if skills_missing:
        for i, skill in enumerate(skills_missing, 1):
            ws[f'A{row}'] = f"{i}."
            ws[f'A{row}'].border = border
            ws[f'B{row}'] = skill
            ws[f'B{row}'].border = border
            row += 1
    else:
        ws[f'A{row}'] = "All required skills are present!"
        ws[f'A{row}'].font = Font(color="27ae60")
        ws[f'A{row}'].border = border
        ws.merge_cells(f'A{row}:B{row}')
        row += 1
    
    row += 1
    
    # Experience Summary
    ws.merge_cells(f'A{row}:B{row}')
    exp_header = ws[f'A{row}']
    exp_header.value = "EXPERIENCE SUMMARY"
    exp_header.font = header_font
    exp_header.fill = PatternFill(start_color="3498db", end_color="3498db", fill_type="solid")
    exp_header.alignment = Alignment(horizontal='center')
    exp_header.border = border
    row += 1
    
    ws.merge_cells(f'A{row}:B{row}')
    exp_cell = ws[f'A{row}']
    exp_cell.value = analysis_data.get('experience_summary', 'N/A')
    exp_cell.alignment = Alignment(wrap_text=True, vertical='top')
    exp_cell.border = border
    ws.row_dimensions[row].height = 60
    row += 2
    
    # Education Summary
    ws.merge_cells(f'A{row}:B{row}')
    edu_header = ws[f'A{row}']
    edu_header.value = "EDUCATION SUMMARY"
    edu_header.font = header_font
    edu_header.fill = PatternFill(start_color="9b59b6", end_color="9b59b6", fill_type="solid")
    edu_header.alignment = Alignment(horizontal='center')
    edu_header.border = border
    row += 1
    
    ws.merge_cells(f'A{row}:B{row}')
    edu_cell = ws[f'A{row}']
    edu_cell.value = analysis_data.get('education_summary', 'N/A')
    edu_cell.alignment = Alignment(wrap_text=True, vertical='top')
    edu_cell.border = border
    ws.row_dimensions[row].height = 40
    row += 2
    
    # Key Strengths
    ws.merge_cells(f'A{row}:B{row}')
    strengths_header = ws[f'A{row}']
    strengths_header.value = "KEY STRENGTHS"
    strengths_header.font = header_font
    strengths_header.fill = PatternFill(start_color="2ecc71", end_color="2ecc71", fill_type="solid")
    strengths_header.alignment = Alignment(horizontal='center')
    strengths_header.border = border
    row += 1
    
    strengths = analysis_data.get('key_strengths', [])
    if strengths:
        for i, strength in enumerate(strengths, 1):
            ws[f'A{row}'] = f"{i}."
            ws[f'A{row}'].border = border
            ws[f'B{row}'] = strength
            ws[f'B{row}'].border = border
            row += 1
    else:
        ws[f'A{row}'] = "No strengths identified"
        ws[f'A{row}'].border = border
        ws.merge_cells(f'A{row}:B{row}')
        row += 1
    
    row += 1
    
    # Areas for Improvement
    ws.merge_cells(f'A{row}:B{row}')
    improvement_header = ws[f'A{row}']
    improvement_header.value = "AREAS FOR IMPROVEMENT"
    improvement_header.font = header_font
    improvement_header.fill = PatternFill(start_color="e67e22", end_color="e67e22", fill_type="solid")
    improvement_header.alignment = Alignment(horizontal='center')
    improvement_header.border = border
    row += 1
    
    improvements = analysis_data.get('areas_for_improvement', [])
    if improvements:
        for i, improvement in enumerate(improvements, 1):
            ws[f'A{row}'] = f"{i}."
            ws[f'A{row}'].border = border
            ws[f'B{row}'] = improvement
            ws[f'B{row}'].border = border
            row += 1
    else:
        ws[f'A{row}'] = "No significant areas for improvement"
        ws[f'A{row}'].font = Font(color="27ae60")
        ws[f'A{row}'].border = border
        ws.merge_cells(f'A{row}:B{row}')
        row += 1
    
    # Save workbook
    wb.save(filepath)
    return filepath

def create_batch_excel_report(analyses: list, job_description: str, filename: str = None) -> str:
    """Create Excel report for batch analysis"""
    if not filename:
        filename = f"batch_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    filepath = os.path.join(REPORTS_FOLDER, filename)
    
    wb = Workbook()
    
    # Summary Sheet
    ws_summary = wb.active
    ws_summary.title = "Summary"
    
    # Title
    ws_summary.merge_cells('A1:H1')
    title_cell = ws_summary['A1']
    title_cell.value = "Batch Resume Analysis Report"
    title_cell.font = Font(bold=True, size=16, color="FFFFFF")
    title_cell.fill = PatternFill(start_color="2c3e50", end_color="2c3e50", fill_type="solid")
    title_cell.alignment = Alignment(horizontal='center')
    
    # Summary Information
    ws_summary['A3'] = "Analysis Date"
    ws_summary['B3'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws_summary['A4'] = "Total Resumes"
    ws_summary['B4'] = len(analyses)
    ws_summary['A5'] = "Job Description"
    ws_summary['B5'] = job_description[:100] + ("..." if len(job_description) > 100 else "")
    ws_summary['A6'] = "AI Engine"
    ws_summary['B6'] = "Self-Hosted AI v2.0"
    
    # Candidates Ranking Table
    row = 8
    headers = ["Rank", "Candidate", "Score", "Grade", "Recommendation", "Matched Skills", "Missing Skills", "Experience"]
    
    for col, header in enumerate(headers, start=1):
        cell = ws_summary.cell(row=row, column=col)
        cell.value = header
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="3498db", end_color="3498db", fill_type="solid")
        cell.alignment = Alignment(horizontal='center')
    
    row += 1
    
    for analysis in analyses:
        ws_summary.cell(row=row, column=1, value=analysis.get('rank', '-'))
        ws_summary.cell(row=row, column=2, value=analysis.get('candidate_name', 'Unknown'))
        ws_summary.cell(row=row, column=3, value=analysis.get('overall_score', 0))
        ws_summary.cell(row=row, column=4, value=analysis.get('grade', 'N/A'))
        ws_summary.cell(row=row, column=5, value=analysis.get('recommendation', 'N/A'))
        
        matched = analysis.get('skills_matched', [])
        ws_summary.cell(row=row, column=6, value=", ".join(matched[:3]) if matched else "N/A")
        
        missing = analysis.get('skills_missing', [])
        ws_summary.cell(row=row, column=7, value=", ".join(missing[:3]) if missing else "All matched")
        
        exp = analysis.get('experience_summary', '')
        ws_summary.cell(row=row, column=8, value=exp[:50] + ("..." if len(exp) > 50 else ""))
        
        row += 1
    
    # Create individual sheets for top candidates
    for i, analysis in enumerate(analyses[:5], 1):  # Top 5 candidates
        ws = wb.create_sheet(title=f"Candidate_{i}")
        
        # Add analysis data
        ws['A1'] = "Candidate Name"
        ws['B1'] = analysis.get('candidate_name', 'N/A')
        ws['A2'] = "Score"
        ws['B2'] = analysis.get('overall_score', 0)
        ws['A3'] = "Grade"
        ws['B3'] = analysis.get('grade', 'N/A')
        ws['A4'] = "Recommendation"
        ws['B4'] = analysis.get('recommendation', 'N/A')
        
        # Add skills
        ws['A6'] = "Matched Skills"
        row = 6
        for skill in analysis.get('skills_matched', []):
            ws.cell(row=row, column=2, value=skill)
            row += 1
        
        ws['A10'] = "Missing Skills"
        row = 10
        for skill in analysis.get('skills_missing', []):
            ws.cell(row=row, column=2, value=skill)
            row += 1
        
        # Add summaries
        ws['A15'] = "Experience Summary"
        ws['B15'] = analysis.get('experience_summary', 'N/A')
        ws['A16'] = "Education Summary"
        ws['B16'] = analysis.get('education_summary', 'N/A')
    
    # Save workbook
    wb.save(filepath)
    return filepath

@app.route('/')
def home():
    """Home route"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Self-Hosted Resume Analyzer AI</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                max-width: 800px;
                margin: 50px auto;
                padding: 40px;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            h1 {
                font-size: 3em;
                margin-bottom: 20px;
            }
            .status {
                background: rgba(255, 255, 255, 0.2);
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }
            .endpoint {
                background: rgba(255, 255, 255, 0.1);
                padding: 15px;
                margin: 10px 0;
                border-radius: 8px;
                border-left: 4px solid #00ff9d;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Self-Hosted Resume Analyzer AI</h1>
            <p>Complete AI-powered resume analysis without external APIs</p>
            
            <div class="status">
                <strong>Status:</strong> ✅ Operational<br>
                <strong>AI Engine:</strong> Self-Hosted AI v2.0<br>
                <strong>NLP Model:</strong> SpaCy + Custom Algorithms<br>
                <strong>Scoring:</strong> Advanced Multi-factor Analysis<br>
                <strong>Batch Capacity:</strong> Up to 20 resumes<br>
                <strong>Database:</strong> Not Required (Memory Cached)
            </div>
            
            <h2>📡 API Endpoints</h2>
            <div class="endpoint">
                <strong>POST /analyze</strong> - Analyze single resume
            </div>
            <div class="endpoint">
                <strong>POST /analyze-batch</strong> - Analyze multiple resumes
            </div>
            <div class="endpoint">
                <strong>GET /health</strong> - Health check
            </div>
            <div class="endpoint">
                <strong>GET /stats</strong> - Statistics
            </div>
            <div class="endpoint">
                <strong>GET /download/{filename}</strong> - Download reports
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Analyze single resume"""
    try:
        start_time = time.time()
        
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
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': 'File size too large. Maximum size is 15MB.'}), 400
        
        # Save uploaded file
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"resume_{timestamp}{file_ext}")
        resume_file.save(file_path)
        
        # Parse resume
        resume_text = resume_parser.parse_file(file_path)
        if isinstance(resume_text, str) and resume_text.startswith('Error'):
            return jsonify({'error': resume_text}), 500
        
        # Check cache
        resume_hash = calculate_hash(resume_text['raw_text'])
        job_hash = calculate_hash(job_description)
        cached = get_cached_analysis(resume_hash, job_hash)
        
        if cached:
            print("✅ Serving from cache")
            analysis = cached
        else:
            # Perform AI analysis
            analysis = ai_engine.analyze_resume(
                resume_text['raw_text'],
                job_description,
                resume_file.filename
            )
            
            # Add filename and job description
            analysis['filename'] = resume_file.filename
            analysis['job_description'] = job_description[:500] + ("..." if len(job_description) > 500 else "")
            
            # Cache the result
            set_cached_analysis(resume_hash, job_hash, analysis)
            
            # Update skill trends
            if 'skills' in resume_text:
                update_skill_trends(resume_text['skills'])
        
        # Create Excel report
        excel_filename = f"analysis_{timestamp}.xlsx"
        excel_path = create_excel_report(analysis, excel_filename)
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['analysis_id'] = generate_analysis_id()
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        analysis['processing_time'] = f"{processing_time:.2f}s"
        analysis['cached'] = cached is not None
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Analysis error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/analyze-batch', methods=['POST'])
def analyze_resume_batch():
    """Analyze multiple resumes"""
    try:
        start_time = time.time()
        
        if 'resumes' not in request.files:
            return jsonify({'error': 'No resume files provided'}), 400
        
        if 'jobDescription' not in request.form:
            return jsonify({'error': 'No job description provided'}), 400
        
        resume_files = request.files.getlist('resumes')
        job_description = request.form['jobDescription']
        
        if len(resume_files) == 0:
            return jsonify({'error': 'No files selected'}), 400
        
        if len(resume_files) > MAX_BATCH_SIZE:
            return jsonify({'error': f'Maximum {MAX_BATCH_SIZE} resumes allowed per batch'}), 400
        
        print(f"📦 Processing batch of {len(resume_files)} resumes")
        
        all_analyses = []
        errors = []
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        
        for index, resume_file in enumerate(resume_files):
            try:
                if resume_file.filename == '':
                    errors.append({
                        'filename': 'Empty file',
                        'error': 'File has no name',
                        'index': index
                    })
                    continue
                
                print(f"🔑 Processing {index + 1}/{len(resume_files)}: {resume_file.filename}")
                
                # Save file
                file_ext = os.path.splitext(resume_file.filename)[1].lower()
                file_path = os.path.join(UPLOAD_FOLDER, f"batch_{batch_id}_{index}{file_ext}")
                resume_file.save(file_path)
                
                # Parse resume
                resume_text = resume_parser.parse_file(file_path)
                if isinstance(resume_text, str) and resume_text.startswith('Error'):
                    errors.append({
                        'filename': resume_file.filename,
                        'error': resume_text,
                        'index': index
                    })
                    continue
                
                # Perform analysis
                analysis = ai_engine.analyze_resume(
                    resume_text['raw_text'],
                    job_description,
                    resume_file.filename
                )
                
                # Add metadata
                analysis['filename'] = resume_file.filename
                analysis['job_description'] = job_description[:200] + ("..." if len(job_description) > 200 else "")
                analysis['analysis_id'] = f"{batch_id}_resume_{index}"
                analysis['processing_order'] = index + 1
                
                # Get file size
                resume_file.seek(0, 2)
                file_size = resume_file.tell()
                resume_file.seek(0)
                analysis['file_size'] = f"{(file_size / 1024):.1f}KB"
                
                all_analyses.append(analysis)
                
                # Update skill trends
                if 'skills' in resume_text:
                    update_skill_trends(resume_text['skills'])
                
                # Clean up
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # Small delay to prevent resource exhaustion
                if index < len(resume_files) - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                errors.append({
                    'filename': resume_file.filename,
                    'error': str(e)[:100],
                    'index': index
                })
                print(f"❌ Error processing {resume_file.filename}: {e}")
        
        # Sort by score
        all_analyses.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        # Add ranking
        for rank, analysis in enumerate(all_analyses, 1):
            analysis['rank'] = rank
        
        # Create batch Excel report
        batch_excel_path = None
        if all_analyses:
            excel_filename = f"batch_{batch_id}.xlsx"
            batch_excel_path = create_batch_excel_report(all_analyses, job_description, excel_filename)
        
        # Prepare response
        response = {
            'success': True,
            'batch_id': batch_id,
            'total_files': len(resume_files),
            'successfully_analyzed': len(all_analyses),
            'failed_files': len(errors),
            'errors': errors,
            'batch_excel_filename': os.path.basename(batch_excel_path) if batch_excel_path else None,
            'analyses': all_analyses,
            'processing_time': f"{time.time() - start_time:.2f}s",
            'ai_engine': 'Self-Hosted AI v2.0',
            'max_batch_size': MAX_BATCH_SIZE,
            'success_rate': f"{(len(all_analyses) / len(resume_files)) * 100:.1f}%" if resume_files else "0%"
        }
        
        print(f"✅ Batch analysis completed in {time.time() - start_time:.2f}s")
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Batch analysis error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    """Download Excel report"""
    try:
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        file_path = os.path.join(REPORTS_FOLDER, safe_filename)
        
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
    """Health check endpoint"""
    try:
        # Check directories
        dirs_ok = all(os.path.exists(d) for d in [
            UPLOAD_FOLDER,
            REPORTS_FOLDER,
            AI_MODEL_PATH
        ])
        
        # Check NLP model
        nlp_ok = nlp_processor._nlp is not None
        
        # Cache stats
        cache_size = len(analysis_cache)
        skill_trends_size = len(skill_trends)
        
        return jsonify({
            'status': 'healthy',
            'directories': 'ok' if dirs_ok else 'error',
            'nlp_model': 'loaded' if nlp_ok else 'error',
            'ai_engine': 'operational',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0',
            'max_batch_size': MAX_BATCH_SIZE,
            'cache_size': cache_size,
            'skill_trends_size': skill_trends_size,
            'memory_cache': 'active',
            'database': 'not_required'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/stats', methods=['GET'])
def get_statistics():
    """Get statistics"""
    try:
        # Get popular skills
        popular_skills = sorted(skill_trends.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return jsonify({
            'cache_size': len(analysis_cache),
            'skill_trends_size': len(skill_trends),
            'popular_skills': [
                {'skill': skill, 'frequency': freq}
                for skill, freq in popular_skills
            ],
            'system_time': datetime.now().isoformat(),
            'ai_engine': 'Self-Hosted AI v2.0',
            'max_batch_size': MAX_BATCH_SIZE
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear-cache', methods=['POST'])
def clear_cache():
    """Clear cache"""
    try:
        analysis_cache.clear()
        skill_trends.clear()
        
        return jsonify({
            'success': True,
            'message': 'Cache cleared',
            'cache_cleared': True,
            'skill_trends_cleared': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def cleanup_on_exit():
    """Cleanup on exit"""
    global service_running
    service_running = False
    print("\n🛑 Shutting down service...")

# Register cleanup
atexit.register(cleanup_on_exit)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Self-Hosted Resume Analyzer AI")
    print("="*50)
    print(f"🤖 AI Engine: Self-Hosted AI v2.0")
    print(f"🧠 NLP Model: SpaCy + Custom Algorithms")
    print(f"📊 Scoring: Advanced Multi-factor Analysis")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📁 Reports folder: {REPORTS_FOLDER}")
    print(f"📦 Max batch size: {MAX_BATCH_SIZE}")
    print(f"⚡ Cache: In-Memory (24 hours)")
    print(f"💾 Database: Not Required")
    print("="*50)
    
    port = int(os.environ.get('PORT', 5002))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
