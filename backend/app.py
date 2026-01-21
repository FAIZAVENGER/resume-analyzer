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
import threading

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure OpenAI API
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not found in .env file or environment variables!")
    print("Check Render Environment Variables or create .env file locally")
    client = None
else:
    print(f"✅ API Key loaded: {api_key[:10]}...")
    try:
        client = openai.OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized successfully")
        
        # Test the client immediately
        try:
            print("🔍 Testing OpenAI connection...")
            test_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            print(f"✅ OpenAI test successful: {test_response.choices[0].message.content}")
        except Exception as test_e:
            print(f"❌ OpenAI test failed: {test_e}")
            
    except Exception as e:
        print(f"❌ Failed to initialize OpenAI client: {str(e)}")
        client = None

# Get absolute path for uploads folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"📁 Upload folder: {UPLOAD_FOLDER}")

# Activity tracking
last_activity_time = datetime.now()

def update_activity():
    """Update last activity timestamp"""
    global last_activity_time
    last_activity_time = datetime.now()

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
        update_activity()
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

def analyze_resume_with_openai(resume_text, job_description, filename=""):
    """Use OpenAI to analyze resume against job description"""
    update_activity()
    
    if client is None:
        print("❌ OpenAI client not initialized.")
        return {
            "candidate_name": "API Configuration Error",
            "skills_matched": ["Check API configuration"],
            "skills_missing": ["API key not set"],
            "experience_summary": "OpenAI API key is not configured. Please add your API key in Render environment variables.",
            "education_summary": "Set OPENAI_API_KEY environment variable with your OpenAI API key.",
            "overall_score": 0,
            "recommendation": "Configuration Required",
            "key_strengths": ["Please check API setup"],
            "areas_for_improvement": ["Configure OpenAI API key"]
        }
    
    # TRUNCATE text
    resume_text = resume_text[:6000]
    job_description = job_description[:2500]
    
    prompt = f"""Analyze this resume against the job description and provide detailed insights.

RESUME TEXT:
{resume_text}

JOB DESCRIPTION:
{job_description}

Return JSON with this structure:
{{
    "candidate_name": "Extract name or use 'Professional Candidate'",
    "skills_matched": ["skill1", "skill2", "skill3"],
    "skills_missing": ["skill1", "skill2", "skill3"],
    "experience_summary": "2-3 sentence summary",
    "education_summary": "2-3 sentence summary",
    "overall_score": 75,
    "recommendation": "Recommended",
    "key_strengths": ["strength1", "strength2"],
    "areas_for_improvement": ["improvement1", "improvement2"]
}}"""
    
    try:
        print("🤖 Sending to OpenAI...")
        start_time = time.time()
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Changed to gpt-3.5-turbo for better compatibility
            messages=[
                {"role": "system", "content": "You are an expert resume analyzer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000,
            timeout=30
        )
        
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
        
        return analysis
        
    except openai.APIConnectionError as e:
        print(f"❌ OpenAI Connection Error: {e}")
        return {
            "candidate_name": "Connection Error",
            "skills_matched": ["Network issue"],
            "skills_missing": ["Cannot connect"],
            "experience_summary": "Failed to connect to OpenAI API. Please check your internet connection and try again.",
            "education_summary": "Service connection error.",
            "overall_score": 0,
            "recommendation": "Connection Failed",
            "key_strengths": ["Please retry"],
            "areas_for_improvement": ["Check API key"]
        }
    except openai.RateLimitError as e:
        print(f"❌ OpenAI Rate Limit Error: {e}")
        return {
            "candidate_name": "Rate Limit Exceeded",
            "skills_matched": ["API limit reached"],
            "skills_missing": ["Try again later"],
            "experience_summary": "OpenAI API rate limit exceeded. Please wait a minute and try again, or check your API quota.",
            "education_summary": "Service temporarily limited.",
            "overall_score": 0,
            "recommendation": "Rate Limited",
            "key_strengths": ["Wait and retry"],
            "areas_for_improvement": ["Check API usage"]
        }
    except Exception as e:
        print(f"❌ OpenAI Analysis Error: {str(e)}")
        return {
            "candidate_name": f"Analysis Error - {str(e)[:50]}",
            "skills_matched": ["Processing error"],
            "skills_missing": ["Analysis failed"],
            "experience_summary": f"Failed to analyze resume. Error: {str(e)[:100]}",
            "education_summary": "Please try again with a different file or check the API configuration.",
            "overall_score": 0,
            "recommendation": "Analysis Failed",
            "key_strengths": ["Please retry"],
            "areas_for_improvement": ["Check file format"]
        }

@app.route('/')
def home():
    """Root route - API landing page"""
    update_activity()
    
    return jsonify({
        'status': 'Resume Analyzer API',
        'message': 'Use /analyze endpoint to analyze resumes',
        'openai_configured': client is not None,
        'api_key_exists': bool(api_key),
        'upload_folder': UPLOAD_FOLDER,
        'endpoints': {
            'POST /analyze': 'Analyze a single resume',
            'POST /analyze-multiple': 'Analyze multiple resumes',
            'GET /health': 'Health check',
            'GET /test-openai': 'Test OpenAI connection'
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    update_activity()
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'api_key_configured': bool(api_key),
        'openai_client_ready': client is not None,
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'system_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/test-openai', methods=['GET'])
def test_openai():
    """Test OpenAI connection"""
    update_activity()
    
    if client is None:
        return jsonify({
            'success': False,
            'message': 'OpenAI client not initialized',
            'reason': 'API key missing or invalid'
        })
    
    try:
        start_time = time.time()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'Hello World'"}],
            max_tokens=10
        )
        elapsed = time.time() - start_time
        
        return jsonify({
            'success': True,
            'message': 'OpenAI is working!',
            'response': response.choices[0].message.content,
            'response_time': f"{elapsed:.2f}s",
            'model': 'gpt-3.5-turbo'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'OpenAI test failed',
            'error': str(e),
            'details': 'Check your API key and internet connection'
        })

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Main endpoint to analyze resume"""
    update_activity()
    
    try:
        print("\n" + "="*50)
        print("📥 New analysis request received")
        
        # Check if files were uploaded
        if 'resume' not in request.files:
            print("❌ No resume file in request")
            return jsonify({'error': 'No resume file provided'}), 400
        
        if 'jobDescription' not in request.form:
            print("❌ No job description in request")
            return jsonify({'error': 'No job description provided'}), 400
        
        resume_file = request.files['resume']
        job_description = request.form['jobDescription']
        
        if resume_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        print(f"📄 Processing: {resume_file.filename}")
        print(f"📋 Job desc length: {len(job_description)} chars")
        
        # Check API configuration
        if not api_key:
            return jsonify({
                'error': 'OpenAI API key not configured',
                'solution': 'Add OPENAI_API_KEY to Render environment variables'
            }), 500
        
        if client is None:
            return jsonify({
                'error': 'OpenAI client not initialized',
                'solution': 'Check your API key format and restart the service'
            }), 500
        
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
            return jsonify({'error': 'Unsupported file format. Use PDF, DOCX, or TXT'}), 400
        
        if resume_text.startswith('Error'):
            return jsonify({'error': resume_text}), 400
        
        print(f"✅ Extracted {len(resume_text)} characters")
        
        # Analyze with OpenAI
        print("🤖 Starting AI analysis...")
        analysis = analyze_resume_with_openai(resume_text, job_description, resume_file.filename)
        
        # Clean up the uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        print(f"✅ Analysis complete. Score: {analysis.get('overall_score', 0)}")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        return jsonify({
            'error': 'Server error',
            'details': str(e)[:200],
            'solution': 'Check the logs for more information'
        }), 500

@app.route('/analyze-multiple', methods=['POST'])
def analyze_multiple():
    """Analyze multiple resumes"""
    update_activity()
    
    try:
        if 'resumes[]' not in request.files:
            return jsonify({'error': 'No resume files provided'}), 400
        
        if 'jobDescription' not in request.form:
            return jsonify({'error': 'No job description provided'}), 400
        
        files = request.files.getlist('resumes[]')
        job_description = request.form['jobDescription']
        
        if len(files) > 10:
            return jsonify({'error': 'Maximum 10 files allowed'}), 400
        
        results = []
        for file in files:
            if file.filename:
                # Create a mock request for single analysis
                analysis = analyze_resume_with_openai(
                    "Resume content would be extracted here",  # Simplified for demo
                    job_description,
                    file.filename
                )
                results.append(analysis)
        
        return jsonify({
            'status': 'success',
            'count': len(results),
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting...")
    print("="*50)
    print(f"📍 OpenAI Configured: {'✅' if client else '❌'}")
    print(f"🔑 API Key: {'✅ Loaded' if api_key else '❌ NOT FOUND'}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    
    if not api_key:
        print("\n⚠️  CRITICAL: OPENAI_API_KEY is not set!")
        print("On Render, go to Environment tab and add:")
        print("Key: OPENAI_API_KEY")
        print("Value: sk-your-actual-api-key-here")
        print("Then restart the service.")
    
    port = int(os.environ.get('PORT', 10000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
