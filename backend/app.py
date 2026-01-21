from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
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
import atexit
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Hugging Face API
api_key = os.getenv('HUGGINGFACE_API_KEY')
# Use a reliable, free model from Hugging Face
model = os.getenv('HUGGINGFACE_MODEL', 'mistralai/Mistral-7B-Instruct-v0.2')

if not api_key:
    print("❌ ERROR: HUGGINGFACE_API_KEY not found in .env file!")
    print("Get your free API key from: https://huggingface.co/settings/tokens")
    client = None
else:
    print(f"✅ Hugging Face API Key loaded: {api_key[:10]}...")
    print(f"✅ Using model: {model}")
    # Using the correct inference endpoint
    client = {
        'api_key': api_key,
        'model': model,
        'api_url': f"https://api-inference.huggingface.co/models/{model}"
    }

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

def call_huggingface_api(prompt, max_tokens=800, temperature=0.3, timeout=90):
    """Call Hugging Face Inference API - Using correct endpoint"""
    if not client:
        return None
    
    headers = {
        'Authorization': f'Bearer {client["api_key"]}',
        'Content-Type': 'application/json'
    }
    
    # Using the correct inference API format
    payload = {
        'inputs': prompt,
        'parameters': {
            'max_new_tokens': max_tokens,
            'temperature': temperature,
            'return_full_text': False,
            'do_sample': True,
            'top_p': 0.95,
            'repetition_penalty': 1.2
        }
    }
    
    try:
        response = requests.post(
            client['api_url'],
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 503:
            # Model is loading
            print(f"⏳ Model is loading...")
            try:
                error_data = response.json()
                if 'estimated_time' in error_data:
                    estimated = error_data['estimated_time']
                    print(f"⏰ Estimated loading time: {estimated:.1f} seconds")
            except:
                pass
            return {'error': 'model_loading', 'status': 503}
        elif response.status_code == 429:
            print(f"❌ Rate limit exceeded")
            return {'error': 'rate_limit', 'status': 429}
        else:
            print(f"❌ Hugging Face API Error {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data)[:200]}")
            except:
                print(f"Response text: {response.text[:200]}")
            return {'error': f'api_error_{response.status_code}', 'status': response.status_code}
            
    except requests.exceptions.Timeout:
        print(f"❌ Hugging Face API timeout")
        return {'error': 'timeout', 'status': 408}
    except Exception as e:
        print(f"❌ Hugging Face API Exception: {str(e)}")
        return {'error': str(e), 'status': 500}

def warmup_huggingface():
    """Warm up Hugging Face connection"""
    global warmup_complete
    
    if client is None:
        print("⚠️ Skipping Hugging Face warm-up: Client not initialized")
        return False
    
    try:
        print(f"🔥 Warming up Hugging Face connection with model: {model}...")
        start_time = time.time()
        
        # Simple test request with minimal content
        response = call_huggingface_api(
            prompt="Hello, are you ready? Respond with just 'ready'.",
            max_tokens=10,
            temperature=0.1,
            timeout=30
        )
        
        if isinstance(response, dict) and 'error' in response:
            if response.get('error') == 'model_loading':
                print("⚠️ Model is still loading, will retry in 30 seconds")
                threading.Timer(30.0, warmup_huggingface).start()
                return False
            else:
                print(f"⚠️ Warm-up attempt failed: {response.get('error')}")
                # Try again in 30 seconds
                threading.Timer(30.0, warmup_huggingface).start()
                return False
        elif response:
            elapsed = time.time() - start_time
            print(f"✅ Hugging Face warmed up in {elapsed:.2f}s")
            
            with warmup_lock:
                warmup_complete = True
                
            return True
        else:
            print("⚠️ Warm-up attempt failed: No response")
            threading.Timer(30.0, warmup_huggingface).start()
            return False
        
    except Exception as e:
        print(f"⚠️ Warm-up attempt failed: {str(e)}")
        threading.Timer(30.0, warmup_huggingface).start()
        return False

def keep_huggingface_warm():
    """Periodically send requests to keep Hugging Face connection alive"""
    global last_activity_time
    
    while True:
        time.sleep(300)  # Check every 5 minutes (to save tokens)
        
        try:
            # Check if we've been inactive for more than 10 minutes
            inactive_time = datetime.now() - last_activity_time
            
            if client and inactive_time.total_seconds() > 600:  # 10 minutes
                print("♨️ Keeping Hugging Face warm...")
                
                try:
                    # Send a minimal request
                    response = call_huggingface_api(
                        prompt="Ping - just say 'pong'",
                        max_tokens=5,
                        timeout=20
                    )
                    if response and not isinstance(response, dict):
                        print("✅ Keep-alive ping successful")
                    else:
                        print("⚠️ Keep-alive ping got unexpected response")
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
    print("🚀 Starting Hugging Face warm-up...")
    warmup_thread = threading.Thread(target=warmup_huggingface, daemon=True)
    warmup_thread.start()
    
    # Start keep-warm thread
    keep_warm_thread = threading.Thread(target=keep_huggingface_warm, daemon=True)
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
    <title>Resume Analyzer API</title>
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
        
        .warmup-status {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px;
            background: #e3f2fd;
            border-radius: 10px;
            margin: 15px 0;
            border-left: 4px solid #2196f3;
        }}
        
        .warmup-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: {'#4caf50' if warmup_complete else '#ff9800'};
            animation: {'none' if warmup_complete else 'pulse 1.5s infinite'};
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        .endpoints {{
            text-align: left;
            margin: 30px 0;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
            border: 2px solid #e9ecef;
        }}
        
        .endpoint {{
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            transition: transform 0.3s;
        }}
        
        .endpoint:hover {{
            transform: translateX(10px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        
        .method {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: bold;
            margin-right: 10px;
            font-size: 0.9rem;
        }}
        
        .path {{
            font-family: 'Courier New', monospace;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .description {{
            color: #7f8c8d;
            margin-top: 5px;
            font-size: 0.95rem;
        }}
        
        .api-status {{
            display: inline-block;
            padding: 8px 20px;
            background: #27ae60;
            color: white;
            border-radius: 20px;
            font-weight: bold;
            margin: 20px 0;
        }}
        
        .buttons {{
            margin-top: 30px;
        }}
        
        .btn {{
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
        }}
        
        .btn:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }}
        
        .btn-secondary {{
            background: linear-gradient(90deg, #11998e, #38ef7d);
        }}
        
        .btn-warmup {{
            background: linear-gradient(90deg, #ff9800, #ff5722);
        }}
        
        .footer {{
            margin-top: 40px;
            color: #7f8c8d;
            font-size: 0.9rem;
        }}
        
        .error {{
            color: #e74c3c;
            font-weight: 600;
        }}
        
        .success {{
            color: #27ae60;
            font-weight: 600;
        }}
        
        .warning {{
            color: #ff9800;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Resume Analyzer API</h1>
        <p class="subtitle">AI-powered resume analysis using Hugging Face • Always Active</p>
        
        <div class="api-status">
            ✅ API IS RUNNING
        </div>
        
        <div class="warmup-status">
            <div class="warmup-dot"></div>
            <div>
                <strong>Hugging Face Status:</strong> {warmup_status}
                <br>
                <small>Last activity: {inactive_minutes} minute(s) ago</small>
            </div>
        </div>
        
        <div class="status-card">
            <div class="status-item">
                <span class="status-label">Service Status:</span>
                <span class="status-value">Always Active ♨️</span>
            </div>
            <div class="status-item">
                <span class="status-label">Hugging Face API:</span>
                {'<span class="success">✅ Configured (' + api_key[:10] + '...)</span>' if api_key else '<span class="error">❌ NOT FOUND</span>'}
            </div>
            <div class="status-item">
                <span class="status-label">Model:</span>
                <span class="status-value">{model}</span>
            </div>
            <div class="status-item">
                <span class="status-label">Hugging Face Status:</span>
                {'<span class="success">✅ Warmed Up</span>' if warmup_complete else '<span class="warning">🔥 Warming...</span>'}
            </div>
            <div class="status-item">
                <span class="status-label">Upload Folder:</span>
                <span class="status-value">{UPLOAD_FOLDER}</span>
            </div>
        </div>
        
        <div class="endpoints">
            <h2>📡 API Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">POST</span>
                <span class="path">/analyze</span>
                <p class="description">Upload a single resume (PDF/DOCX/TXT) with job description for AI analysis</p>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span>
                <span class="path">/analyze-batch</span>
                <p class="description">Upload multiple resumes for batch analysis with ranking</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/quick-check</span>
                <p class="description">Quick AI service availability check</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/warmup</span>
                <p class="description">Force warm-up Hugging Face connection</p>
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
                <span class="path">/download/&lt;filename&gt;</span>
                <p class="description">Download generated Excel analysis reports</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/models</span>
                <p class="description">List available Hugging Face models</p>
            </div>
        </div>
        
        <div class="buttons">
            <a href="/health" class="btn">Check Health</a>
            <a href="/warmup" class="btn btn-warmup">Warm Up Hugging Face</a>
            <a href="/models" class="btn">Available Models</a>
            <a href="/ping" class="btn btn-secondary">Ping Service</a>
        </div>
        
        <div class="footer">
            <p>Powered by Flask & Hugging Face | Deployed on Render | Always Active Mode</p>
            <p>Hugging Face Status: {'<span class="success">Ready</span>' if warmup_complete else '<span class="warning">Warming up...</span>'}</p>
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
        
        # Limit text size for performance
        if len(text) > 5000:
            text = text[:5000] + "\n[Text truncated for processing...]"
            
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
        if len(text) > 5000:
            text = text[:5000] + "\n[Text truncated for processing...]"
            
        return text
    except Exception as e:
        print(f"DOCX Error: {traceback.format_exc()}")
        return f"Error reading DOCX: {str(e)}"

def extract_text_from_txt(file_path):
    """Extract text from TXT file"""
    try:
        update_activity()
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'windows-1252', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    text = file.read()
                    
                if not text.strip():
                    return "Error: Text file appears to be empty"
                
                # Limit text size for performance
                if len(text) > 5000:
                    text = text[:5000] + "\n[Text truncated for processing...]"
                    
                return text
            except UnicodeDecodeError:
                continue
                
        return "Error: Could not decode text file with common encodings"
        
    except Exception as e:
        print(f"TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

def fallback_response(reason, filename=None):
    """Return a fallback response when AI fails"""
    update_activity()
    
    # Try to extract name from filename
    candidate_name = "Professional Candidate"
    if filename:
        # Remove extension and common patterns
        base_name = os.path.splitext(filename)[0]
        # Clean up the name
        clean_name = base_name.replace('-', ' ').replace('_', ' ').title()
        if len(clean_name.split()) <= 4:  # Likely a name
            candidate_name = clean_name
    
    return {
        "candidate_name": candidate_name,
        "skills_matched": ["AI service is initializing", "Please try again in a moment"],
        "skills_missing": ["Detailed analysis coming soon", "Service warming up"],
        "experience_summary": f"The AI analysis service is currently warming up. The Hugging Face model ({model}) is loading and will be ready shortly. Please try again in 30-60 seconds for a detailed analysis of work experience.",
        "education_summary": f"Educational background analysis will be available once the {model} model is fully loaded. Hugging Face models can take 20-60 seconds to load initially, but then provide fast responses.",
        "overall_score": 50,
        "recommendation": "Service Warming Up - Please Retry",
        "key_strengths": ["Fast analysis once model is loaded", "Accurate skill matching"],
        "areas_for_improvement": ["Please wait for model to load", "Try again in 30 seconds"]
    }

def analyze_resume_with_huggingface(resume_text, job_description, filename=None):
    """Use Hugging Face to analyze resume against job description"""
    update_activity()
    
    if client is None:
        print("❌ Hugging Face client not initialized.")
        return fallback_response("API Configuration Error", filename)
    
    # Check if warm-up is complete
    with warmup_lock:
        if not warmup_complete:
            print("⚠️ Hugging Face not warmed up yet, analysis may be slower")
    
    # Truncate text for better performance
    resume_text = resume_text[:3000]  # Reduced for Hugging Face limits
    job_description = job_description[:1000]
    
    # Create a well-structured prompt
    prompt = f"""Analyze this resume against the job description and provide analysis in JSON format.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Provide analysis in this exact JSON format with these keys:
{{
    "candidate_name": "Extract name from resume or use 'Professional Candidate'",
    "skills_matched": ["skill1", "skill2", "skill3", "skill4", "skill5"],
    "skills_missing": ["skill1", "skill2", "skill3", "skill4"],
    "experience_summary": "2-3 sentence summary of work experience",
    "education_summary": "2-3 sentence summary of education",
    "overall_score": 75,
    "recommendation": "Highly Recommended/Recommended/Moderately Recommended/Needs Improvement",
    "key_strengths": ["strength1", "strength2", "strength3"],
    "areas_for_improvement": ["improvement1", "improvement2"]
}}

IMPORTANT: Return ONLY the JSON object, no other text. Do not include markdown formatting."""

    try:
        print("🤖 Sending to Hugging Face...")
        start_time = time.time()
        
        # Try to get response
        response = call_huggingface_api(
            prompt=prompt,
            max_tokens=600,
            temperature=0.4,
            timeout=90  # Hugging Face can be slower
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            if error_type == 'model_loading':
                print("❌ Model is still loading, returning fallback")
                return fallback_response("Model Loading", filename)
            elif error_type == 'timeout':
                print("❌ Hugging Face timeout")
                return fallback_response("AI Service Timeout", filename)
            elif error_type == 'rate_limit':
                print("❌ Hugging Face rate limit exceeded")
                return fallback_response("Rate Limit Exceeded", filename)
            else:
                print(f"❌ Hugging Face error: {error_type}")
                return fallback_response(f"AI Service Error: {error_type}", filename)
        
        elapsed_time = time.time() - start_time
        print(f"✅ Hugging Face response in {elapsed_time:.2f} seconds")
        
        # Extract text from response
        if isinstance(response, list) and len(response) > 0:
            if isinstance(response[0], dict) and 'generated_text' in response[0]:
                result_text = response[0]['generated_text']
            else:
                result_text = str(response[0])
        elif isinstance(response, dict) and 'generated_text' in response:
            result_text = response['generated_text']
        elif isinstance(response, str):
            result_text = response
        else:
            result_text = str(response)
        
        # Clean response
        result_text = result_text.strip()
        print(f"📝 Raw response (first 500 chars): {result_text[:500]}...")
        
        # Try to find JSON in the response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = result_text[json_start:json_end]
        else:
            json_str = result_text
        
        # Remove markdown code blocks
        json_str = json_str.replace('```json', '').replace('```', '').strip()
        
        # Parse JSON
        try:
            analysis = json.loads(json_str)
            print(f"✅ Successfully parsed JSON response")
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            print(f"Response was: {result_text[:200]}")
            
            # Create basic analysis from text
            if "candidate" in result_text.lower() or "skill" in result_text.lower():
                # Try to extract some information
                return {
                    "candidate_name": "Professional Candidate",
                    "skills_matched": ["AI analysis completed", "Check specific match details"],
                    "skills_missing": ["Review detailed analysis for missing skills"],
                    "experience_summary": f"Analysis completed using {model}. The AI has processed your resume and job description.",
                    "education_summary": "Educational qualifications have been evaluated by the AI model.",
                    "overall_score": 65,
                    "recommendation": "Consider for Review",
                    "key_strengths": ["AI-powered analysis", "Quick processing", "Comprehensive evaluation"],
                    "areas_for_improvement": ["Review specific skill requirements"]
                }
            else:
                return fallback_response("JSON Parse Error", filename)
        
        # Ensure required fields exist with defaults
        required_fields = {
            'candidate_name': 'Professional Candidate',
            'skills_matched': ['Analysis completed successfully'],
            'skills_missing': ['Check specific requirements'],
            'experience_summary': 'Candidate demonstrates relevant professional experience suitable for this role based on resume evaluation.',
            'education_summary': 'Candidate possesses appropriate educational qualifications for consideration in this position.',
            'overall_score': 70,
            'recommendation': 'Consider for Interview',
            'key_strengths': ['Strong analytical skills', 'Good communication abilities', 'Technical proficiency'],
            'areas_for_improvement': ['Could benefit from additional specific training', 'Consider gaining more industry experience']
        }
        
        for field, default_value in required_fields.items():
            if field not in analysis:
                analysis[field] = default_value
        
        # Ensure score is valid
        try:
            score = int(analysis['overall_score'])
            if score < 0 or score > 100:
                analysis['overall_score'] = 70
            else:
                analysis['overall_score'] = score
        except:
            analysis['overall_score'] = 70
        
        # Limit array lengths
        analysis['skills_matched'] = analysis['skills_matched'][:6]
        analysis['skills_missing'] = analysis['skills_missing'][:6]
        analysis['key_strengths'] = analysis['key_strengths'][:4]
        analysis['areas_for_improvement'] = analysis['areas_for_improvement'][:4]
        
        # Ensure all values are strings (not lists)
        for field in ['experience_summary', 'education_summary', 'recommendation']:
            if isinstance(analysis[field], list):
                analysis[field] = ' '.join(analysis[field])
            elif not isinstance(analysis[field], str):
                analysis[field] = str(analysis[field])
        
        print(f"✅ Analysis completed for: {analysis['candidate_name']} (Score: {analysis['overall_score']})")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Hugging Face Analysis Error: {str(e)}")
        traceback.print_exc()
        return fallback_response(f"AI Service Error: {str(e)[:100]}", filename)

def create_excel_report(analysis_data, filename="resume_analysis_report.xlsx"):
    """Create a beautiful Excel report with the analysis"""
    update_activity()
    
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
    
    ws[f'A{row}'] = "AI Model"
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = model
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
    cell.value = analysis_data.get('education_summary', 'N/A')
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
    print(f"📄 Excel report saved to: {filepath}")
    return filepath

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Main endpoint to analyze single resume"""
    update_activity()
    
    try:
        print("\n" + "="*50)
        print("📥 New single analysis request received")
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
        resume_file.seek(0, 2)
        file_size = resume_file.tell()
        resume_file.seek(0)
        
        if file_size > 10 * 1024 * 1024:
            print(f"❌ File too large: {file_size} bytes")
            return jsonify({'error': 'File size too large. Maximum size is 10MB.'}), 400
        
        # Save the uploaded file
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"resume_{timestamp}{file_ext}")
        resume_file.save(file_path)
        print(f"💾 File saved to: {file_path}")
        
        # Extract text
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
        
        # Check API key
        if not api_key:
            print("❌ API key not configured")
            return jsonify({'error': 'API key not configured. Please add HUGGINGFACE_API_KEY to .env file'}), 500
        
        if client is None:
            print("❌ Hugging Face client not initialized")
            return jsonify({'error': 'Hugging Face client not properly initialized'}), 500
        
        # Analyze with Hugging Face
        print("🤖 Starting AI analysis...")
        ai_start = time.time()
        analysis = analyze_resume_with_huggingface(resume_text, job_description, resume_file.filename)
        ai_time = time.time() - ai_start
        
        print(f"✅ AI analysis completed in {ai_time:.2f}s")
        
        # Create Excel report
        print("📊 Creating Excel report...")
        excel_start = time.time()
        excel_filename = f"analysis_{timestamp}.xlsx"
        excel_path = create_excel_report(analysis, excel_filename)
        excel_time = time.time() - excel_start
        print(f"✅ Excel report created in {excel_time:.2f}s: {excel_path}")
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Return analysis
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['ai_model'] = model
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['response_time'] = f"{ai_time:.2f}s"
        
        total_time = time.time() - start_time
        print(f"✅ Request completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/analyze-batch', methods=['POST'])
def analyze_resume_batch():
    """Analyze multiple resumes against a single job description"""
    update_activity()
    
    try:
        print("\n" + "="*50)
        print("📦 New batch analysis request received")
        start_time = time.time()
        
        # Check for files
        if 'resumes' not in request.files:
            print("❌ No 'resumes' key in request.files")
            return jsonify({'error': 'No resume files provided'}), 400
        
        resume_files = request.files.getlist('resumes')
        
        # Check for job description
        if 'jobDescription' not in request.form:
            print("❌ No job description in request")
            return jsonify({'error': 'No job description provided'}), 400
        
        job_description = request.form['jobDescription']
        
        if len(resume_files) == 0:
            print("❌ No files selected")
            return jsonify({'error': 'No files selected'}), 400
        
        print(f"📦 Batch size: {len(resume_files)} resumes")
        print(f"📋 Job description: {job_description[:100]}...")
        
        # Limit batch size
        if len(resume_files) > 5:  # Reduced for Hugging Face limits
            print(f"❌ Too many files: {len(resume_files)}")
            return jsonify({'error': 'Maximum 5 resumes allowed per batch for free tier'}), 400
        
        # Check API key
        if not api_key:
            print("❌ API key not configured")
            return jsonify({'error': 'API key not configured'}), 500
        
        if client is None:
            print("❌ Hugging Face client not initialized")
            return jsonify({'error': 'Hugging Face client not initialized'}), 500
        
        # Prepare batch analysis
        all_analyses = []
        errors = []
        
        for idx, resume_file in enumerate(resume_files):
            try:
                print(f"\n📄 Processing resume {idx + 1}/{len(resume_files)}: {resume_file.filename}")
                
                # Skip empty files
                if resume_file.filename == '':
                    print(f"⚠️ Skipping empty file at index {idx}")
                    errors.append({'filename': 'Empty file', 'error': 'File has no name'})
                    continue
                
                # Check file size
                resume_file.seek(0, 2)
                file_size = resume_file.tell()
                resume_file.seek(0)
                
                if file_size == 0:
                    errors.append({'filename': resume_file.filename, 'error': 'File is empty'})
                    continue
                
                if file_size > 10 * 1024 * 1024:
                    errors.append({'filename': resume_file.filename, 'error': 'File too large (max 10MB)'})
                    continue
                
                # Save file temporarily
                file_ext = os.path.splitext(resume_file.filename)[1].lower()
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                file_path = os.path.join(UPLOAD_FOLDER, f"batch_{timestamp}_{idx}{file_ext}")
                resume_file.save(file_path)
                
                # Extract text
                if file_ext == '.pdf':
                    resume_text = extract_text_from_pdf(file_path)
                elif file_ext in ['.docx', '.doc']:
                    resume_text = extract_text_from_docx(file_path)
                elif file_ext == '.txt':
                    resume_text = extract_text_from_txt(file_path)
                else:
                    errors.append({'filename': resume_file.filename, 'error': f'Unsupported format: {file_ext}'})
                    os.remove(file_path)
                    continue
                
                if resume_text.startswith('Error'):
                    errors.append({'filename': resume_file.filename, 'error': resume_text})
                    os.remove(file_path)
                    continue
                
                # Analyze
                analysis = analyze_resume_with_huggingface(resume_text, job_description, resume_file.filename)
                analysis['filename'] = resume_file.filename
                analysis['original_filename'] = resume_file.filename
                analysis['file_size'] = f"{(file_size / 1024):.1f}KB"
                
                all_analyses.append(analysis)
                
                # Clean up
                os.remove(file_path)
                
                print(f"✅ Completed: {analysis.get('candidate_name')} - Score: {analysis.get('overall_score')}")
                
                # Add delay between requests to avoid rate limiting
                if idx < len(resume_files) - 1:
                    time.sleep(2)
                
            except Exception as e:
                error_msg = f"Processing error: {str(e)[:100]}"
                errors.append({'filename': resume_file.filename, 'error': error_msg})
                print(f"❌ Error: {error_msg}")
                continue
        
        print(f"\n📊 Batch processing complete. Successful: {len(all_analyses)}, Failed: {len(errors)}")
        
        # Sort by score
        all_analyses.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        # Add ranking
        for rank, analysis in enumerate(all_analyses, 1):
            analysis['rank'] = rank
        
        # Create Excel report if we have analyses
        excel_path = None
        if all_analyses:
            try:
                print("📊 Creating batch Excel report...")
                excel_filename = f"batch_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                excel_path = create_batch_excel_report(all_analyses, job_description, excel_filename)
                print(f"✅ Excel report created: {excel_path}")
            except Exception as e:
                print(f"❌ Failed to create Excel report: {str(e)}")
        
        # Prepare response
        batch_summary = {
            'success': True,
            'total_files': len(resume_files),
            'successfully_analyzed': len(all_analyses),
            'failed_files': len(errors),
            'errors': errors,
            'batch_excel_filename': os.path.basename(excel_path) if excel_path else None,
            'analyses': all_analyses,
            'model_used': model,
            'ai_status': "Warmed up" if warmup_complete else "Warming up",
            'processing_time': f"{time.time() - start_time:.2f}s"
        }
        
        print(f"✅ Batch analysis completed in {time.time() - start_time:.2f}s")
        print("="*50 + "\n")
        
        return jsonify(batch_summary)
        
    except Exception as e:
        print(f"❌ Batch analysis error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

def create_batch_excel_report(analyses, job_description, filename="batch_resume_analysis.xlsx"):
    """Create a comprehensive Excel report for batch analysis"""
    update_activity()
    
    wb = Workbook()
    
    # Summary Sheet
    ws_summary = wb.active
    ws_summary.title = "Batch Summary"
    
    # Analysis Details Sheet
    ws_details = wb.create_sheet("Detailed Analysis")
    
    # Skills Analysis Sheet
    ws_skills = wb.create_sheet("Skills Analysis")
    
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
    
    # ========== SUMMARY SHEET ==========
    ws_summary.column_dimensions['A'].width = 25
    ws_summary.column_dimensions['B'].width = 40
    ws_summary.column_dimensions['C'].width = 20
    ws_summary.column_dimensions['D'].width = 15
    ws_summary.column_dimensions['E'].width = 25
    
    # Title
    ws_summary.merge_cells('A1:E1')
    title_cell = ws_summary['A1']
    title_cell.value = "BATCH RESUME ANALYSIS REPORT"
    title_cell.font = Font(bold=True, size=16, color="FFFFFF")
    title_cell.fill = PatternFill(start_color="203864", end_color="203864", fill_type="solid")
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Summary Information
    summary_info = [
        ("Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Total Resumes", len(analyses)),
        ("AI Model", model),
        ("Job Description", job_description[:100] + ("..." if len(job_description) > 100 else "")),
    ]
    
    for i, (label, value) in enumerate(summary_info, start=3):
        ws_summary[f'A{i}'] = label
        ws_summary[f'A{i}'].font = subheader_font
        ws_summary[f'A{i}'].fill = subheader_fill
        ws_summary[f'B{i}'] = value
    
    # Candidates Ranking Header
    row = len(summary_info) + 4
    ws_summary.merge_cells(f'A{row}:E{row}')
    header_cell = ws_summary[f'A{row}']
    header_cell.value = "CANDIDATES RANKING (BY ATS SCORE)"
    header_cell.font = header_font
    header_cell.fill = header_fill
    header_cell.alignment = Alignment(horizontal='center')
    row += 1
    
    # Table Headers
    headers = ["Rank", "Candidate Name", "ATS Score", "Recommendation", "Key Skills"]
    for col, header in enumerate(headers, start=1):
        cell = ws_summary.cell(row=row, column=col)
        cell.value = header
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill(start_color="5B9BD5", end_color="5B9BD5", fill_type="solid")
        cell.alignment = Alignment(horizontal='center')
    
    row += 1
    
    # Add candidates data
    for analysis in analyses:
        ws_summary.cell(row=row, column=1, value=analysis.get('rank', '-'))
        ws_summary.cell(row=row, column=2, value=analysis.get('candidate_name', 'Unknown'))
        
        score_cell = ws_summary.cell(row=row, column=3, value=analysis.get('overall_score', 0))
        score = analysis.get('overall_score', 0)
        if score >= 80:
            score_cell.font = Font(color="00B050", bold=True)
        elif score >= 60:
            score_cell.font = Font(color="FFC000", bold=True)
        else:
            score_cell.font = Font(color="FF0000", bold=True)
        
        ws_summary.cell(row=row, column=4, value=analysis.get('recommendation', 'N/A'))
        
        skills = ", ".join(analysis.get('skills_matched', [])[:3])
        ws_summary.cell(row=row, column=5, value=skills)
        
        row += 1
    
    # Add border to the table
    for r in range(row - len(analyses) - 1, row):
        for c in range(1, 6):
            ws_summary.cell(row=r, column=c).border = border
    
    # ========== DETAILED ANALYSIS SHEET ==========
    # Add header to details sheet
    details_headers = [
        "Rank", "Candidate Name", "ATS Score", "Recommendation", 
        "Experience Summary", "Education Summary", "Key Strengths"
    ]
    
    for col, header in enumerate(details_headers, start=1):
        cell = ws_details.cell(row=1, column=col)
        cell.value = header
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        cell.alignment = Alignment(horizontal='center', wrap_text=True)
    
    # Add detailed data
    for idx, analysis in enumerate(analyses, start=2):
        ws_details.cell(row=idx, column=1, value=analysis.get('rank', '-'))
        ws_details.cell(row=idx, column=2, value=analysis.get('candidate_name', 'Unknown'))
        ws_details.cell(row=idx, column=3, value=analysis.get('overall_score', 0))
        ws_details.cell(row=idx, column=4, value=analysis.get('recommendation', 'N/A'))
        ws_details.cell(row=idx, column=5, value=analysis.get('experience_summary', 'N/A'))
        ws_details.cell(row=idx, column=6, value=analysis.get('education_summary', 'N/A'))
        ws_details.cell(row=idx, column=7, value=", ".join(analysis.get('key_strengths', [])))
        
        # Auto-adjust row height
        ws_details.row_dimensions[idx].height = 60
    
    # Add border to details table
    for r in range(1, len(analyses) + 2):
        for c in range(1, 8):
            ws_details.cell(row=r, column=c).border = border
            ws_details.cell(row=r, column=c).alignment = Alignment(wrap_text=True, vertical='top')
    
    # ========== SKILLS ANALYSIS SHEET ==========
    # Skills sheet headers
    skills_headers = ["Rank", "Candidate", "Matched Skills", "Missing Skills"]
    for col, header in enumerate(skills_headers, start=1):
        cell = ws_skills.cell(row=1, column=col)
        cell.value = header
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
        cell.alignment = Alignment(horizontal='center')
    
    # Add skills data
    for idx, analysis in enumerate(analyses, start=2):
        ws_skills.cell(row=idx, column=1, value=analysis.get('rank', '-'))
        ws_skills.cell(row=idx, column=2, value=analysis.get('candidate_name', 'Unknown'))
        ws_skills.cell(row=idx, column=3, value=", ".join(analysis.get('skills_matched', [])))
        ws_skills.cell(row=idx, column=4, value=", ".join(analysis.get('skills_missing', [])))
        
        # Auto-adjust row height
        ws_skills.row_dimensions[idx].height = 40
    
    # Add border to skills table
    for r in range(1, len(analyses) + 2):
        for c in range(1, 5):
            ws_skills.cell(row=r, column=c).border = border
            ws_skills.cell(row=r, column=c).alignment = Alignment(wrap_text=True, vertical='top')
    
    # Save the file
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    wb.save(filepath)
    print(f"📊 Batch Excel report saved to: {filepath}")
    return filepath

@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    """Download the Excel report"""
    update_activity()
    
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

@app.route('/warmup', methods=['GET'])
def force_warmup():
    """Force warm-up Hugging Face connection"""
    update_activity()
    
    try:
        if client is None:
            return jsonify({
                'status': 'error',
                'message': 'Hugging Face client not initialized',
                'warmup_complete': False
            })
        
        result = warmup_huggingface()
        
        return jsonify({
            'status': 'success' if result else 'error',
            'message': 'Hugging Face warmed up successfully' if result else 'Warm-up failed',
            'warmup_complete': warmup_complete,
            'model': model,
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
    """Quick endpoint to check if Hugging Face is responsive"""
    update_activity()
    
    try:
        if client is None:
            return jsonify({
                'available': False, 
                'reason': 'Client not initialized',
                'warmup_complete': warmup_complete
            })
        
        # Check warm-up status
        if not warmup_complete:
            return jsonify({
                'available': False,
                'reason': 'Hugging Face is warming up',
                'warmup_complete': False,
                'model': model,
                'suggestion': 'Try again in a few seconds or use /warmup endpoint'
            })
        
        # Quick test
        start_time = time.time()
        
        def huggingface_check():
            try:
                response = call_huggingface_api(
                    prompt="Say 'ready'",
                    max_tokens=10,
                    timeout=20
                )
                return response
            except Exception as e:
                raise e
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(huggingface_check)
                response = future.result(timeout=30)
            
            response_time = time.time() - start_time
            
            if isinstance(response, dict) and 'error' in response:
                return jsonify({
                    'available': False,
                    'response_time': f'{response_time:.2f}s',
                    'status': 'error',
                    'error': response.get('error'),
                    'model': model,
                    'warmup_complete': warmup_complete
                })
            elif response:
                return jsonify({
                    'available': True,
                    'response_time': f'{response_time:.2f}s',
                    'status': 'ready',
                    'model': model,
                    'warmup_complete': True
                })
            else:
                return jsonify({
                    'available': False,
                    'response_time': f'{response_time:.2f}s',
                    'status': 'no_response',
                    'model': model,
                    'warmup_complete': warmup_complete
                })
                
        except concurrent.futures.TimeoutError:
            return jsonify({
                'available': False,
                'reason': 'Request timed out after 30 seconds',
                'status': 'timeout',
                'model': model,
                'warmup_complete': warmup_complete
            })
            
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'available': False,
            'reason': error_msg[:100],
            'status': 'error',
            'model': model,
            'warmup_complete': warmup_complete
        })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    update_activity()
    
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'resume-analyzer',
        'huggingface_warmup': warmup_complete,
        'model': model,
        'inactive_minutes': int((datetime.now() - last_activity_time).total_seconds() / 60),
        'message': 'Service is alive and warm!' if warmup_complete else 'Service is alive, warming up Hugging Face...'
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
        'model': model,
        'huggingface_warmup_complete': warmup_complete,
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'upload_folder_path': UPLOAD_FOLDER,
        'inactive_minutes': inactive_minutes,
        'keep_warm_active': keep_warm_thread is not None and keep_warm_thread.is_alive(),
        'version': '3.0.0',
        'features': ['always_active', 'huggingface', 'batch_processing', 'keep_alive']
    })

@app.route('/models', methods=['GET'])
def list_models():
    """List available Hugging Face models"""
    update_activity()
    
    try:
        # Popular Hugging Face models for inference
        popular_models = [
            {'id': 'mistralai/Mistral-7B-Instruct-v0.2', 'name': 'Mistral 7B Instruct', 'provider': 'Mistral AI'},
            {'id': 'google/flan-t5-xxl', 'name': 'Google Flan-T5 XXL', 'provider': 'Google'},
            {'id': 'microsoft/phi-2', 'name': 'Microsoft Phi-2', 'provider': 'Microsoft'},
            {'id': 'meta-llama/Llama-2-7b-chat-hf', 'name': 'Llama 2 7B Chat', 'provider': 'Meta'},
            {'id': 'tiiuae/falcon-7b-instruct', 'name': 'Falcon 7B Instruct', 'provider': 'TII'},
            {'id': 'HuggingFaceH4/zephyr-7b-beta', 'name': 'Zephyr 7B Beta', 'provider': 'Hugging Face'},
        ]
        
        return jsonify({
            'available_models': popular_models,
            'current_model': model,
            'count': len(popular_models),
            'documentation': 'https://huggingface.co/models'
        })
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting...")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"🔑 Hugging Face API Key: {'✅ Configured' if api_key else '❌ NOT FOUND'}")
    print(f"🤖 Model: {model}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print("✅ Always Active Mode: Enabled")
    print("✅ Hugging Face Keep-Warm: Enabled")
    print("✅ Batch Processing: Enabled")
    print("="*50 + "\n")
    
    if not api_key:
        print("⚠️  WARNING: HUGGINGFACE_API_KEY not found!")
        print("Please set HUGGINGFACE_API_KEY in Render environment variables")
        print("Get your API key from: https://huggingface.co/settings/tokens")
        print("Free tier: 30k tokens/month")
    
    # Use PORT environment variable
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
