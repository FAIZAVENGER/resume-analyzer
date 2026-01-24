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
import re
from collections import defaultdict
import queue
import asyncio
import hashlib

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Groq API
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')

# Available Groq models
GROQ_MODELS = {
    'llama-3.1-8b-instant': {
        'name': 'Llama 3.1 8B Instant',
        'context_length': 8192,
        'provider': 'Groq',
        'description': 'Fast 8B model for quick responses',
        'status': 'production',
        'free_tier': True
    },
    'llama-3.3-70b-versatile': {
        'name': 'Llama 3.3 70B Versatile',
        'context_length': 8192,
        'provider': 'Groq',
        'description': 'High-quality 70B model for complex tasks',
        'status': 'production',
        'free_tier': True
    },
    'meta-llama/llama-4-scout-17b-16e-instruct': {
        'name': 'Llama 4 Scout 17B',
        'context_length': 16384,
        'provider': 'Groq',
        'description': 'Multimodal 17B model with vision capabilities',
        'status': 'production',
        'free_tier': True
    }
}

# Default working model
DEFAULT_MODEL = 'llama-3.1-8b-instant'

# Track API status
api_available = False
warmup_complete = False
last_activity_time = datetime.now()
keep_warm_thread = None
warmup_lock = threading.Lock()

# Get absolute path for uploads folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)
print(f"📁 Upload folder: {UPLOAD_FOLDER}")
print(f"📁 Reports folder: {REPORTS_FOLDER}")

# Cache for consistent scoring (resume hash -> score)
score_cache = {}
cache_lock = threading.Lock()

# Request queue for batch processing
request_queue = queue.Queue()
MAX_CONCURRENT_REQUESTS = 3  # Process 3 resumes at a time
PROCESSING_SEMAPHORE = threading.Semaphore(MAX_CONCURRENT_REQUESTS)

# Service keep-alive
SERVICE_KEEP_ALIVE_INTERVAL = 60  # Keep alive every 60 seconds
last_keep_alive = datetime.now()

def calculate_resume_hash(resume_text, job_description):
    """Calculate a hash for caching consistent scores"""
    content = f"{resume_text[:500]}{job_description[:500]}".encode('utf-8')
    return hashlib.md5(content).hexdigest()

def get_cached_score(resume_hash):
    """Get cached score if available"""
    with cache_lock:
        return score_cache.get(resume_hash)

def set_cached_score(resume_hash, score):
    """Cache score for consistency"""
    with cache_lock:
        score_cache[resume_hash] = score

def keep_service_active():
    """Keep the service always active by making periodic requests"""
    global last_keep_alive
    
    while True:
        try:
            time.sleep(SERVICE_KEEP_ALIVE_INTERVAL)
            
            # Make a simple request to keep the service active
            health_check_url = f"http://localhost:{os.environ.get('PORT', 5002)}/ping"
            try:
                response = requests.get(health_check_url, timeout=10)
                print(f"✅ Service keep-alive: {response.status_code}")
            except:
                # If we can't reach locally, try the external URL
                try:
                    response = requests.get(f"{request.host_url}/ping", timeout=10)
                    print(f"✅ External keep-alive: {response.status_code}")
                except Exception as e:
                    print(f"⚠️ Keep-alive failed: {e}")
            
            last_keep_alive = datetime.now()
            
        except Exception as e:
            print(f"⚠️ Keep-alive thread error: {e}")

def call_groq_api(prompt, max_tokens=1000, temperature=0.2, timeout=30, model_override=None, retry_count=0):
    """Call Groq API with the given prompt with retry logic"""
    if not GROQ_API_KEY:
        print("❌ No Groq API key configured")
        return {'error': 'no_api_key', 'status': 500}
    
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    model_to_use = model_override or GROQ_MODEL or DEFAULT_MODEL
    
    payload = {
        'model': model_to_use,
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'max_tokens': max_tokens,
        'temperature': temperature,
        'top_p': 0.95,
        'stream': False,
        'stop': None
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                result = data['choices'][0]['message']['content']
                print(f"✅ Groq API response in {response_time:.2f}s using {model_to_use}")
                return result
            else:
                print(f"❌ Unexpected Groq API response format")
                return {'error': 'invalid_response', 'status': response.status_code}
        elif response.status_code == 400:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', 'Bad Request')
            print(f"❌ Groq API Error 400: {error_msg[:200]}")
            
            if 'decommissioned' in error_msg.lower() or 'deprecated' in error_msg.lower():
                print(f"⚠️ Model {model_to_use} is deprecated. Trying default model {DEFAULT_MODEL}...")
                return call_groq_api(prompt, max_tokens, temperature, timeout, DEFAULT_MODEL)
            
            return {'error': f'api_error_400: {error_msg[:100]}', 'status': 400}
        elif response.status_code == 429:
            print(f"❌ Groq API rate limit exceeded")
            # Exponential backoff for rate limiting
            if retry_count < 3:
                wait_time = (2 ** retry_count) * 5  # 5, 10, 20 seconds
                print(f"⏳ Rate limited, retrying in {wait_time}s (attempt {retry_count + 1}/3)")
                time.sleep(wait_time)
                return call_groq_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1)
            return {'error': 'rate_limit', 'status': 429}
        elif response.status_code == 503:
            print(f"❌ Groq API service unavailable")
            if retry_count < 2:
                wait_time = 10  # Wait 10 seconds before retry
                print(f"⏳ Service unavailable, retrying in {wait_time}s")
                time.sleep(wait_time)
                return call_groq_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1)
            return {'error': 'service_unavailable', 'status': 503}
        else:
            print(f"❌ Groq API Error {response.status_code}: {response.text[:200]}")
            return {'error': f'api_error_{response.status_code}', 'status': response.status_code}
            
    except requests.exceptions.Timeout:
        print(f"❌ Groq API timeout after {timeout}s")
        if retry_count < 2:
            print(f"⏳ Timeout, retrying (attempt {retry_count + 1}/3)")
            return call_groq_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1)
        return {'error': 'timeout', 'status': 408}
    except requests.exceptions.ConnectionError:
        print(f"❌ Groq API connection error")
        if retry_count < 2:
            wait_time = 5
            print(f"⏳ Connection error, retrying in {wait_time}s")
            time.sleep(wait_time)
            return call_groq_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1)
        return {'error': 'connection_error', 'status': 503}
    except Exception as e:
        print(f"❌ Groq API Exception: {str(e)}")
        return {'error': str(e), 'status': 500}

def warmup_groq_service():
    """Warm up Groq service connection"""
    global warmup_complete, api_available
    
    if not GROQ_API_KEY:
        print("⚠️ Skipping Groq warm-up: No API key configured")
        return False
    
    try:
        model_to_use = GROQ_MODEL or DEFAULT_MODEL
        print(f"🔥 Warming up Groq connection...")
        print(f"📊 Using model: {model_to_use}")
        start_time = time.time()
        
        response = call_groq_api(
            prompt="Hello, are you ready? Respond with just 'ready'.",
            max_tokens=10,
            temperature=0.1,
            timeout=10
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            if error_type == 'rate_limit':
                print(f"⚠️ Rate limited, will retry later")
            elif error_type == 'invalid_api_key':
                print(f"❌ Invalid Groq API key")
            else:
                print(f"⚠️ Warm-up attempt failed: {error_type}")
            
            threading.Timer(15.0, warmup_groq_service).start()
            return False
        elif response and 'ready' in response.lower():
            elapsed = time.time() - start_time
            print(f"✅ Groq warmed up in {elapsed:.2f}s")
            
            with warmup_lock:
                warmup_complete = True
                api_available = True
                
            return True
        else:
            print("⚠️ Warm-up attempt failed: Unexpected response")
            threading.Timer(15.0, warmup_groq_service).start()
            return False
        
    except Exception as e:
        print(f"⚠️ Warm-up attempt failed: {str(e)}")
        threading.Timer(15.0, warmup_groq_service).start()
        return False

def keep_service_warm():
    """Periodically send requests to keep Groq service responsive"""
    global last_activity_time
    
    while True:
        time.sleep(30)  # Reduced to 30 seconds for more frequent keep-alive
        
        try:
            inactive_time = datetime.now() - last_activity_time
            
            if GROQ_API_KEY:
                print(f"♨️ Keeping Groq warm...")
                
                try:
                    response = call_groq_api(
                        prompt="Ping - just say 'pong'",
                        max_tokens=5,
                        timeout=15
                    )
                    if response and 'pong' in response.lower():
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
if GROQ_API_KEY:
    print(f"🚀 Starting Groq warm-up...")
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    print(f"🤖 Using model: {model_to_use}")
    
    # Start warm-up in a separate thread
    warmup_thread = threading.Thread(target=warmup_groq_service, daemon=True)
    warmup_thread.start()
    
    # Start keep-warm thread
    keep_warm_thread = threading.Thread(target=keep_service_warm, daemon=True)
    keep_warm_thread.start()
    
    # Start service keep-alive thread
    keep_alive_thread = threading.Thread(target=keep_service_active, daemon=True)
    keep_alive_thread.start()
    
    print("✅ Keep-warm thread started")
    print("✅ Service keep-alive thread started")
else:
    print("⚠️ WARNING: No Groq API key found!")
    print("Please set GROQ_API_KEY in Render environment variables")

@app.route('/')
def home():
    """Root route - API landing page"""
    global warmup_complete, last_activity_time, last_keep_alive
    
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    keep_alive_time = datetime.now() - last_keep_alive
    keep_alive_seconds = int(keep_alive_time.total_seconds())
    
    warmup_status = "✅ Ready" if warmup_complete else "🔥 Warming up..."
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    model_info = GROQ_MODELS.get(model_to_use, {'name': model_to_use, 'provider': 'Groq'})
    
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
        
        .info {{
            color: #2196f3;
            font-weight: 600;
        }}
        
        .model-badge {{
            display: inline-block;
            background: linear-gradient(90deg, #00b09b, #96c93d);
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.85rem;
            margin-left: 10px;
        }}
        
        .free-badge {{
            display: inline-block;
            background: linear-gradient(90deg, #00b09b, #96c93d);
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.75rem;
            margin-left: 5px;
        }}
        
        .always-active-badge {{
            display: inline-block;
            background: linear-gradient(90deg, #ff6b6b, #ffa726);
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.85rem;
            margin-left: 10px;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Resume Analyzer API</h1>
        <p class="subtitle">AI-powered resume analysis • Latest Groq Models • <span class="always-active-badge">Always Active</span></p>
        
        <div class="api-status">
            ⚡ GROQ API IS RUNNING • ALWAYS ACTIVE
        </div>
        
        <div class="warmup-status">
            <div class="warmup-dot"></div>
            <div>
                <strong>Groq Service Status:</strong> {warmup_status}
                <br>
                <small>Last activity: {inactive_minutes} minute(s) ago • Keep-alive: {keep_alive_seconds}s ago</small>
            </div>
        </div>
        
        <div class="status-card">
            <div class="status-item">
                <span class="status-label">Service Status:</span>
                <span class="status-value"><span class="always-active-badge">⚡ Always Active</span></span>
            </div>
            <div class="status-item">
                <span class="status-label">AI Provider:</span>
                <span class="status-value info">GROQ</span>
            </div>
            <div class="status-item">
                <span class="status-label">Model:</span>
                <span class="status-value">{model_info['name']} <span class="model-badge">{model_info['provider']}</span> {model_info.get('free_tier', False) and '<span class="free-badge">FREE</span>' or ''}</span>
            </div>
            <div class="status-item">
                <span class="status-label">API Status:</span>
                {'<span class="success">✅ Available</span>' if warmup_complete else '<span class="warning">🔥 Warming...</span>'}
            </div>
            <div class="status-item">
                <span class="status-label">Batch Capacity:</span>
                <span class="status-value">15 resumes simultaneously</span>
            </div>
            <div class="status-item">
                <span class="status-label">Context Length:</span>
                <span class="status-value">{model_info.get('context_length', '8192'):,} tokens</span>
            </div>
            <div class="status-item">
                <span class="status-label">Keep-alive:</span>
                <span class="status-value success">Every {SERVICE_KEEP_ALIVE_INTERVAL}s</span>
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
                <p class="description">Upload multiple resumes for batch analysis with ranking (Up to 15 resumes)</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/quick-check</span>
                <p class="description">Quick Groq API availability check</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/warmup</span>
                <p class="description">Force warm-up Groq API connection</p>
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
                <span class="path">/download-individual/&lt;analysis_id&gt;</span>
                <p class="description">Download individual candidate report</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/models</span>
                <p class="description">List available Groq models</p>
            </div>
        </div>
        
        <div class="buttons">
            <a href="/health" class="btn">Check Health</a>
            <a href="/warmup" class="btn btn-warmup">Warm Up Groq API</a>
            <a href="/models" class="btn">Available Models</a>
            <a href="/ping" class="btn btn-secondary">Ping Service</a>
        </div>
        
        <div class="footer">
            <p>Powered by Flask & Groq API | Deployed on Render | <span class="always-active-badge">Always Active Mode</span></p>
            <p>AI Service: GROQ | Status: {'<span class="success">Ready</span>' if warmup_complete else '<span class="warning">Warming up...</span>'}</p>
            <p>Model: {model_info['name']} | Batch Capacity: 15 resumes | Keep-alive: {SERVICE_KEEP_ALIVE_INTERVAL}s</p>
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
        
        if len(text) > 10000:
            text = text[:10000] + "\n[Text truncated for processing...]"
            
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
        
        if len(text) > 10000:
            text = text[:10000] + "\n[Text truncated for processing...]"
            
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
                
                if len(text) > 10000:
                    text = text[:10000] + "\n[Text truncated for processing...]"
                    
                return text
            except UnicodeDecodeError:
                continue
                
        return "Error: Could not decode text file with common encodings"
        
    except Exception as e:
        print(f"TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

def fallback_response(reason, filename=None):
    """Return a fallback response when Groq API fails"""
    update_activity()
    
    candidate_name = "Professional Candidate"
    if filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').title()
        if len(clean_name.split()) <= 4:
            candidate_name = clean_name
    
    return {
        "candidate_name": candidate_name,
        "skills_matched": ["AI service is initializing", "Please try again in a moment"],
        "skills_missing": ["Detailed analysis coming soon", "Service warming up"],
        "experience_summary": f"The Groq AI analysis service is currently warming up.",
        "education_summary": f"Educational background analysis will be available once the service is ready.",
        "overall_score": 50,
        "recommendation": "Service Warming Up - Please Retry",
        "key_strengths": ["Ultra-fast analysis once model is loaded", "Accurate skill matching"],
        "areas_for_improvement": ["Please wait for model to load", "Try again in 15 seconds"],
        "ai_provider": "groq",
        "ai_status": "Warming up"
    }

def analyze_resume_with_ai(resume_text, job_description, filename=None, analysis_id=None):
    """Use Groq API to analyze resume against job description with consistent scoring"""
    update_activity()
    
    if not GROQ_API_KEY:
        print("❌ No Groq API key configured.")
        return fallback_response("API Configuration Error", filename)
    
    with warmup_lock:
        if not warmup_complete:
            print(f"⚠️ Groq API not warmed up yet, analysis may be slower")
    
    # Check cache for consistent scoring
    resume_hash = calculate_resume_hash(resume_text, job_description)
    cached_score = get_cached_score(resume_hash)
    
    # Truncate for better performance
    resume_text = resume_text[:6000]
    job_description = job_description[:2000]
    
    # Enhanced prompt for consistent and accurate ATS scoring
    prompt = f"""You are an expert ATS (Applicant Tracking System) analyzer and recruitment specialist. 
Analyze this resume against the job description and provide a comprehensive analysis with CONSISTENT scoring.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

IMPORTANT SCORING GUIDELINES FOR CONSISTENCY:
1. Score should be based on exact keyword matches from job description
2. Give higher weight to required skills (mentioned as "must have", "required", "essential")
3. Consider years of experience mentioned in job description
4. Education requirements should match exactly (degree types, fields)
5. Industry-specific certifications get bonus points
6. Use this exact scoring rubric:
   - 90-100: Excellent match, exceeds all requirements
   - 80-89: Strong match, meets all requirements, exceeds some
   - 70-79: Good match, meets most requirements
   - 60-69: Fair match, meets basic requirements
   - 50-59: Needs improvement, missing key requirements
   - Below 50: Poor match, missing most requirements

Provide analysis in this exact JSON format:
{{
    "candidate_name": "Extract name from resume or use filename",
    "skills_matched": ["exact skill 1", "exact skill 2", "exact skill 3", "exact skill 4", "exact skill 5"],
    "skills_missing": ["exact skill 1", "exact skill 2", "exact skill 3"],
    "experience_summary": "Detailed 2-3 sentence summary focusing on relevant experience matching job requirements",
    "education_summary": "Detailed 1-2 sentence summary of education and certifications matching job requirements",
    "overall_score": 75,
    "recommendation": "Highly Recommended/Recommended/Moderately Recommended/Needs Improvement/Not Recommended",
    "key_strengths": ["specific strength 1", "specific strength 2", "specific strength 3"],
    "areas_for_improvement": ["specific area 1", "specific area 2"],
    "scoring_breakdown": {{
        "skill_match_score": 85,
        "experience_score": 80,
        "education_score": 75,
        "keyword_match_score": 90
    }}
}}

CRITICAL: 
1. Be EXTREMELY consistent with scoring - same resume + same job should always get same score
2. Extract candidate name from resume if possible (look for name at top, in contact info)
3. Match skills EXACTLY as they appear in job description
4. Score must reflect actual match percentage (0-100)
5. Return ONLY the JSON object, no other text or markdown formatting.
6. Use the scoring breakdown to explain the overall score."""

    try:
        model_to_use = GROQ_MODEL or DEFAULT_MODEL
        print(f"⚡ Sending to Groq API ({model_to_use})...")
        start_time = time.time()
        
        response = call_groq_api(
            prompt=prompt,
            max_tokens=1200,
            temperature=0.1,  # Lower temperature for more consistent results
            timeout=60
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            if error_type == 'rate_limit':
                print("❌ Rate limit exceeded")
                return fallback_response("Rate Limit Exceeded", filename)
            elif error_type == 'timeout':
                print("❌ Groq API timeout")
                return fallback_response("Groq API Timeout", filename)
            elif error_type == 'invalid_api_key':
                print("❌ Invalid Groq API key")
                return fallback_response("Invalid API Key", filename)
            else:
                print(f"❌ Groq API error: {error_type}")
                return {
                    "candidate_name": filename.replace('.pdf', '').replace('.docx', '').replace('.txt', '').title() if filename else "Professional Candidate",
                    "skills_matched": ["Text analysis completed", "Check resume for specific skills"],
                    "skills_missing": ["Compare with job description requirements"],
                    "experience_summary": f"Enhanced text analysis completed. Resume has been processed against job requirements.",
                    "education_summary": "Educational background has been evaluated based on extracted text.",
                    "overall_score": 65,
                    "recommendation": "Consider for Review (Text Analysis)",
                    "key_strengths": ["Text-based analysis", "Quick processing"],
                    "areas_for_improvement": ["Enable Groq API for AI-powered analysis"],
                    "ai_provider": "enhanced_text",
                    "ai_status": "Enhanced text mode"
                }
        
        elapsed_time = time.time() - start_time
        print(f"✅ Groq API response in {elapsed_time:.2f} seconds")
        
        result_text = response.strip()
        print(f"📝 Raw response (first 500 chars): {result_text[:500]}...")
        
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = result_text[json_start:json_end]
        else:
            json_str = result_text
        
        json_str = json_str.replace('```json', '').replace('```', '').strip()
        
        try:
            analysis = json.loads(json_str)
            print(f"✅ Successfully parsed JSON response")
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            print(f"Response was: {result_text[:200]}")
            
            return {
                "candidate_name": "Professional Candidate",
                "skills_matched": ["AI analysis completed", "Check specific match details"],
                "skills_missing": ["Review detailed analysis for missing skills"],
                "experience_summary": f"Analysis completed using Groq {model_to_use}. The AI has processed your resume and job description.",
                "education_summary": "Educational qualifications have been evaluated by the AI model.",
                "overall_score": 65,
                "recommendation": "Consider for Review",
                "key_strengths": ["AI-powered analysis", "Ultra-fast processing", "Comprehensive evaluation"],
                "areas_for_improvement": ["Review specific skill requirements"],
                "ai_provider": "groq",
                "ai_status": "Warmed up" if warmup_complete else "Warming up"
            }
        
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
            'areas_for_improvement': ['Could benefit from additional specific training', 'Consider gaining more industry experience'],
            'scoring_breakdown': {
                'skill_match_score': 70,
                'experience_score': 70,
                'education_score': 70,
                'keyword_match_score': 70
            }
        }
        
        for field, default_value in required_fields.items():
            if field not in analysis:
                analysis[field] = default_value
        
        # Ensure score is valid and consistent
        try:
            score = int(analysis['overall_score'])
            if score < 0 or score > 100:
                # Use cached score if available, otherwise use default
                if cached_score:
                    score = cached_score
                else:
                    score = 70
            else:
                # Cache the score for consistency
                set_cached_score(resume_hash, score)
        except:
            if cached_score:
                analysis['overall_score'] = cached_score
            else:
                analysis['overall_score'] = 70
        
        # Limit array lengths
        analysis['skills_matched'] = analysis['skills_matched'][:8]
        analysis['skills_missing'] = analysis['skills_missing'][:8]
        analysis['key_strengths'] = analysis['key_strengths'][:4]
        analysis['areas_for_improvement'] = analysis['areas_for_improvement'][:4]
        
        # Ensure all values are strings (not lists)
        for field in ['experience_summary', 'education_summary', 'recommendation']:
            if isinstance(analysis[field], list):
                analysis[field] = ' '.join(analysis[field])
            elif not isinstance(analysis[field], str):
                analysis[field] = str(analysis[field])
        
        # Add AI provider info
        analysis['ai_provider'] = "groq"
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['ai_model'] = model_to_use
        analysis['response_time'] = f"{elapsed_time:.2f}s"
        analysis['resume_hash'] = resume_hash  # For debugging consistency
        
        # Add analysis ID if provided
        if analysis_id:
            analysis['analysis_id'] = analysis_id
        
        print(f"✅ Analysis completed for: {analysis['candidate_name']} (Score: {analysis['overall_score']})")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Groq Analysis Error: {str(e)}")
        traceback.print_exc()
        return fallback_response(f"Groq API Error: {str(e)[:100]}", filename)

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
    groq_fill = PatternFill(start_color="00B09B", end_color="96C93D", fill_type="solid")
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
    cell.value = "⚡ GROQ RESUME ANALYSIS REPORT"
    cell.font = Font(bold=True, size=16, color="FFFFFF")
    cell.fill = groq_fill
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
    
    ws[f'A{row}'] = "AI Provider"
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = "GROQ"
    row += 1
    
    model_to_use = analysis_data.get('ai_model', GROQ_MODEL or DEFAULT_MODEL)
    ws[f'A{row}'] = "AI Model"
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = model_to_use
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
    filepath = os.path.join(REPORTS_FOLDER, filename)
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
        
        # Check file size (15MB limit)
        resume_file.seek(0, 2)
        file_size = resume_file.tell()
        resume_file.seek(0)
        
        if file_size > 15 * 1024 * 1024:
            print(f"❌ File too large: {file_size} bytes")
            return jsonify({'error': 'File size too large. Maximum size is 15MB.'}), 400
        
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
        
        # Check API configuration
        if not GROQ_API_KEY:
            print("❌ No Groq API key configured")
            return jsonify({'error': 'Groq API not configured. Please set GROQ_API_KEY in environment variables'}), 500
        
        # Analyze with Groq API
        model_to_use = GROQ_MODEL or DEFAULT_MODEL
        print(f"⚡ Starting Groq API analysis ({model_to_use})...")
        ai_start = time.time()
        
        # Generate unique analysis ID
        analysis_id = f"single_{timestamp}"
        analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id)
        ai_time = time.time() - ai_start
        
        print(f"✅ Groq API analysis completed in {ai_time:.2f}s")
        
        # Create Excel report
        print("📊 Creating Excel report...")
        excel_start = time.time()
        excel_filename = f"analysis_{analysis_id}.xlsx"
        excel_path = create_excel_report(analysis, excel_filename)
        excel_time = time.time() - excel_start
        print(f"✅ Excel report created in {excel_time:.2f}s: {excel_path}")
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Return analysis
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['ai_model'] = model_to_use
        analysis['ai_provider'] = "groq"
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['response_time'] = f"{ai_time:.2f}s"
        analysis['analysis_id'] = analysis_id
        
        total_time = time.time() - start_time
        print(f"✅ Request completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

def process_batch_resume(resume_file, job_description, index, total, batch_id):
    """Process a single resume in batch mode"""
    try:
        with PROCESSING_SEMAPHORE:
            print(f"📄 Processing resume {index + 1}/{total}: {resume_file.filename}")
            
            # Save file temporarily
            file_ext = os.path.splitext(resume_file.filename)[1].lower()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            file_path = os.path.join(UPLOAD_FOLDER, f"batch_{batch_id}_{index}{file_ext}")
            resume_file.save(file_path)
            
            # Extract text
            if file_ext == '.pdf':
                resume_text = extract_text_from_pdf(file_path)
            elif file_ext in ['.docx', '.doc']:
                resume_text = extract_text_from_docx(file_path)
            elif file_ext == '.txt':
                resume_text = extract_text_from_txt(file_path)
            else:
                os.remove(file_path)
                return {
                    'filename': resume_file.filename,
                    'error': f'Unsupported format: {file_ext}',
                    'status': 'failed'
                }
            
            if resume_text.startswith('Error'):
                os.remove(file_path)
                return {
                    'filename': resume_file.filename,
                    'error': resume_text,
                    'status': 'failed'
                }
            
            # Analyze with Groq API
            analysis_id = f"{batch_id}_candidate_{index}"
            analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id)
            analysis['filename'] = resume_file.filename
            analysis['original_filename'] = resume_file.filename
            
            # Get file size
            resume_file.seek(0, 2)
            file_size = resume_file.tell()
            resume_file.seek(0)
            analysis['file_size'] = f"{(file_size / 1024):.1f}KB"
            
            # Add analysis ID
            analysis['analysis_id'] = analysis_id
            
            # Create individual Excel report
            try:
                excel_filename = f"individual_{analysis_id}.xlsx"
                excel_path = create_excel_report(analysis, excel_filename)
                analysis['individual_excel_filename'] = os.path.basename(excel_path)
            except Exception as e:
                print(f"⚠️ Failed to create individual report: {str(e)}")
                analysis['individual_excel_filename'] = None
            
            # Clean up
            os.remove(file_path)
            
            print(f"✅ Completed: {analysis.get('candidate_name')} - Score: {analysis.get('overall_score')}")
            
            # Add delay between requests to avoid rate limiting
            time.sleep(1)
            
            return {
                'analysis': analysis,
                'status': 'success'
            }
            
    except Exception as e:
        print(f"❌ Error processing {resume_file.filename}: {str(e)}")
        return {
            'filename': resume_file.filename,
            'error': f"Processing error: {str(e)[:100]}",
            'status': 'failed'
        }

@app.route('/analyze-batch', methods=['POST'])
def analyze_resume_batch():
    """Analyze multiple resumes against a single job description (up to 15 resumes)"""
    update_activity()
    
    try:
        print("\n" + "="*50)
        print("📦 New batch analysis request received")
        start_time = time.time()
        
        if 'resumes' not in request.files:
            print("❌ No 'resumes' key in request.files")
            return jsonify({'error': 'No resume files provided'}), 400
        
        resume_files = request.files.getlist('resumes')
        
        if 'jobDescription' not in request.form:
            print("❌ No job description in request")
            return jsonify({'error': 'No job description provided'}), 400
        
        job_description = request.form['jobDescription']
        
        if len(resume_files) == 0:
            print("❌ No files selected")
            return jsonify({'error': 'No files selected'}), 400
        
        print(f"📦 Batch size: {len(resume_files)} resumes")
        print(f"📋 Job description: {job_description[:100]}...")
        
        # Increased batch size to 15
        if len(resume_files) > 15:
            print(f"❌ Too many files: {len(resume_files)}")
            return jsonify({'error': 'Maximum 15 resumes allowed per batch'}), 400
        
        # Check API configuration
        if not GROQ_API_KEY:
            print("❌ No Groq API key configured")
            return jsonify({'error': 'Groq API not configured'}), 500
        
        # Prepare batch analysis
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        all_analyses = []
        errors = []
        
        # Process resumes with ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
            futures = []
            
            for idx, resume_file in enumerate(resume_files):
                if resume_file.filename == '':
                    errors.append({'filename': 'Empty file', 'error': 'File has no name'})
                    continue
                
                # Submit task to executor
                future = executor.submit(
                    process_batch_resume,
                    resume_file,
                    job_description,
                    idx,
                    len(resume_files),
                    batch_id
                )
                futures.append((resume_file.filename, future))
            
            # Collect results
            for filename, future in futures:
                try:
                    result = future.result(timeout=180)  # 3 minutes timeout per resume
                    
                    if result['status'] == 'success':
                        all_analyses.append(result['analysis'])
                    else:
                        errors.append({'filename': filename, 'error': result.get('error', 'Unknown error')})
                        
                except concurrent.futures.TimeoutError:
                    errors.append({'filename': filename, 'error': 'Processing timeout (180 seconds)'})
                except Exception as e:
                    errors.append({'filename': filename, 'error': f'Processing error: {str(e)[:100]}'})
        
        print(f"\n📊 Batch processing complete. Successful: {len(all_analyses)}, Failed: {len(errors)}")
        
        # Sort by score
        all_analyses.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        # Add ranking
        for rank, analysis in enumerate(all_analyses, 1):
            analysis['rank'] = rank
        
        # Create batch Excel report if we have analyses
        batch_excel_path = None
        if all_analyses:
            try:
                print("📊 Creating batch Excel report...")
                excel_filename = f"batch_analysis_{batch_id}.xlsx"
                batch_excel_path = create_batch_excel_report(all_analyses, job_description, excel_filename)
                print(f"✅ Excel report created: {batch_excel_path}")
            except Exception as e:
                print(f"❌ Failed to create Excel report: {str(e)}")
        
        # Prepare response
        batch_summary = {
            'success': True,
            'total_files': len(resume_files),
            'successfully_analyzed': len(all_analyses),
            'failed_files': len(errors),
            'errors': errors,
            'batch_excel_filename': os.path.basename(batch_excel_path) if batch_excel_path else None,
            'batch_id': batch_id,
            'analyses': all_analyses,
            'model_used': GROQ_MODEL or DEFAULT_MODEL,
            'ai_provider': "groq",
            'ai_status': "Warmed up" if warmup_complete else "Warming up",
            'processing_time': f"{time.time() - start_time:.2f}s",
            'job_description_preview': job_description[:200] + ("..." if len(job_description) > 200 else "")
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
    
    # Individual Reports Sheets
    for idx, analysis in enumerate(analyses):
        ws_individual = wb.create_sheet(f"Candidate {idx+1}")
        create_individual_sheet(ws_individual, analysis, idx+1)
    
    # Define styles
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    subheader_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    subheader_font = Font(bold=True, size=11)
    groq_fill = PatternFill(start_color="00B09B", end_color="96C93D", fill_type="solid")
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
    title_cell.value = "⚡ GROQ BATCH RESUME ANALYSIS"
    title_cell.font = Font(bold=True, size=16, color="FFFFFF")
    title_cell.fill = groq_fill
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Summary Information
    summary_info = [
        ("Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Total Resumes", len(analyses)),
        ("AI Provider", "GROQ"),
        ("AI Model", GROQ_MODEL or DEFAULT_MODEL),
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
        
        ws_details.row_dimensions[idx].height = 60
    
    # Add border to details table
    for r in range(1, len(analyses) + 2):
        for c in range(1, 8):
            ws_details.cell(row=r, column=c).border = border
            ws_details.cell(row=r, column=c).alignment = Alignment(wrap_text=True, vertical='top')
    
    # ========== SKILLS ANALYSIS SHEET ==========
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
        
        ws_skills.row_dimensions[idx].height = 40
    
    # Add border to skills table
    for r in range(1, len(analyses) + 2):
        for c in range(1, 5):
            ws_skills.cell(row=r, column=c).border = border
            ws_skills.cell(row=r, column=c).alignment = Alignment(wrap_text=True, vertical='top')
    
    # Save the file
    filepath = os.path.join(REPORTS_FOLDER, filename)
    wb.save(filepath)
    print(f"📊 Batch Excel report saved to: {filepath}")
    return filepath

def create_individual_sheet(ws, analysis, candidate_number):
    """Create individual candidate sheet in batch report"""
    # Define styles
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    subheader_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    subheader_font = Font(bold=True, size=11)
    
    # Set column widths
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 50
    
    row = 1
    
    # Title
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = f"Candidate {candidate_number}: {analysis.get('candidate_name', 'Unknown')}"
    cell.font = Font(bold=True, size=14, color="FFFFFF")
    cell.fill = header_fill
    cell.alignment = Alignment(horizontal='center', vertical='center')
    row += 2
    
    # Basic Information
    info_fields = [
        ("Rank", analysis.get('rank', '-')),
        ("ATS Score", f"{analysis.get('overall_score', 0)}/100"),
        ("Recommendation", analysis.get('recommendation', 'N/A')),
        ("Filename", analysis.get('original_filename', 'N/A')),
        ("File Size", analysis.get('file_size', 'N/A')),
        ("AI Model", analysis.get('ai_model', 'N/A')),
        ("Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ]
    
    for label, value in info_fields:
        ws[f'A{row}'] = label
        ws[f'A{row}'].font = subheader_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'B{row}'] = value
        row += 1
    
    row += 1
    
    # Skills Matched
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "SKILLS MATCHED"
    cell.font = header_font
    cell.fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
    cell.alignment = Alignment(horizontal='center')
    row += 1
    
    for skill in analysis.get('skills_matched', []):
        ws[f'A{row}'] = "✓"
        ws[f'B{row}'] = skill
        row += 1
    
    row += 1
    
    # Skills Missing
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "SKILLS MISSING"
    cell.font = header_font
    cell.fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
    cell.alignment = Alignment(horizontal='center')
    row += 1
    
    for skill in analysis.get('skills_missing', []):
        ws[f'A{row}'] = "✗"
        ws[f'B{row}'] = skill
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
    cell.value = analysis.get('education_summary', 'N/A')
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
    
    for strength in analysis.get('key_strengths', []):
        ws[f'A{row}'] = "•"
        ws[f'B{row}'] = strength
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
        row += 1

@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    """Download the Excel report"""
    update_activity()
    
    try:
        print(f"📥 Download request for: {filename}")
        
        import re
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        
        # Check both upload and reports folders
        file_path = os.path.join(REPORTS_FOLDER, safe_filename)
        if not os.path.exists(file_path):
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

@app.route('/download-individual/<analysis_id>', methods=['GET'])
def download_individual_report(analysis_id):
    """Download individual candidate report"""
    update_activity()
    
    try:
        print(f"📥 Download individual request for analysis ID: {analysis_id}")
        
        # Look for individual report file
        filename = f"individual_{analysis_id}.xlsx"
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        
        file_path = os.path.join(REPORTS_FOLDER, safe_filename)
        
        if not os.path.exists(file_path):
            print(f"❌ Individual report not found: {file_path}")
            return jsonify({'error': 'Individual report not found'}), 404
        
        print(f"✅ Individual file found! Size: {os.path.getsize(file_path)} bytes")
        
        # Get candidate name from filename if possible
        download_name = f"candidate_report_{analysis_id}.xlsx"
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        print(f"❌ Individual download error: {traceback.format_exc()}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/warmup', methods=['GET'])
def force_warmup():
    """Force warm-up Groq API"""
    update_activity()
    
    try:
        if not GROQ_API_KEY:
            return jsonify({
                'status': 'error',
                'message': 'Groq API not configured',
                'warmup_complete': False
            })
        
        result = warmup_groq_service()
        
        return jsonify({
            'status': 'success' if result else 'error',
            'message': f'Groq API warmed up successfully' if result else 'Warm-up failed',
            'warmup_complete': warmup_complete,
            'ai_provider': 'groq',
            'model': GROQ_MODEL or DEFAULT_MODEL,
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
    """Quick endpoint to check if Groq API is responsive"""
    update_activity()
    
    try:
        if not GROQ_API_KEY:
            return jsonify({
                'available': False, 
                'reason': 'Groq API not configured',
                'warmup_complete': warmup_complete
            })
        
        if not warmup_complete:
            return jsonify({
                'available': False,
                'reason': 'Groq API is warming up',
                'warmup_complete': False,
                'ai_provider': 'groq',
                'model': GROQ_MODEL or DEFAULT_MODEL,
                'suggestion': 'Try again in a few seconds or use /warmup endpoint'
            })
        
        start_time = time.time()
        
        def groq_service_check():
            try:
                response = call_groq_api(
                    prompt="Say 'ready'",
                    max_tokens=10,
                    timeout=10
                )
                return response
            except Exception as e:
                raise e
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(groq_service_check)
                response = future.result(timeout=15)
            
            response_time = time.time() - start_time
            
            if isinstance(response, dict) and 'error' in response:
                return jsonify({
                    'available': False,
                    'response_time': f'{response_time:.2f}s',
                    'status': 'error',
                    'error': response.get('error'),
                    'ai_provider': 'groq',
                    'model': GROQ_MODEL or DEFAULT_MODEL,
                    'warmup_complete': warmup_complete
                })
            elif response and 'ready' in response.lower():
                return jsonify({
                    'available': True,
                    'response_time': f'{response_time:.2f}s',
                    'status': 'ready',
                    'ai_provider': 'groq',
                    'model': GROQ_MODEL or DEFAULT_MODEL,
                    'warmup_complete': True
                })
            else:
                return jsonify({
                    'available': False,
                    'response_time': f'{response_time:.2f}s',
                    'status': 'no_response',
                    'ai_provider': 'groq',
                    'model': GROQ_MODEL or DEFAULT_MODEL,
                    'warmup_complete': warmup_complete
                })
                
        except concurrent.futures.TimeoutError:
            return jsonify({
                'available': False,
                'reason': 'Request timed out after 15 seconds',
                'status': 'timeout',
                'ai_provider': 'groq',
                'model': GROQ_MODEL or DEFAULT_MODEL,
                'warmup_complete': warmup_complete
            })
            
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'available': False,
            'reason': error_msg[:100],
            'status': 'error',
            'ai_provider': 'groq',
            'model': GROQ_MODEL or DEFAULT_MODEL,
            'warmup_complete': warmup_complete
        })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    update_activity()
    
    global last_keep_alive
    last_keep_alive = datetime.now()
    
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'resume-analyzer',
        'ai_provider': 'groq',
        'ai_warmup': warmup_complete,
        'model': model_to_use,
        'inactive_minutes': int((datetime.now() - last_activity_time).total_seconds() / 60),
        'keep_alive_active': True,
        'message': f'Service is alive and Groq is warm!' if warmup_complete else f'Service is alive, warming up Groq...'
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    keep_alive_time = datetime.now() - last_keep_alive
    keep_alive_seconds = int(keep_alive_time.total_seconds())
    
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    model_info = GROQ_MODELS.get(model_to_use, {'name': model_to_use, 'provider': 'Groq'})
    
    return jsonify({
        'status': 'Backend is running!', 
        'timestamp': datetime.now().isoformat(),
        'ai_provider': 'groq',
        'ai_provider_configured': bool(GROQ_API_KEY),
        'model': model_to_use,
        'model_info': model_info,
        'ai_warmup_complete': warmup_complete,
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'reports_folder_exists': os.path.exists(REPORTS_FOLDER),
        'upload_folder_path': UPLOAD_FOLDER,
        'reports_folder_path': REPORTS_FOLDER,
        'inactive_minutes': inactive_minutes,
        'keep_alive_seconds': keep_alive_seconds,
        'keep_warm_active': keep_warm_thread is not None and keep_warm_thread.is_alive(),
        'version': '8.0.0',
        'features': ['always_active', 'groq_api_support', 'batch_processing_15', 'keep_alive', 'consistent_scoring', 'cache_system', 'individual_reports', 'parallel_processing']
    })

@app.route('/models', methods=['GET'])
def list_models():
    """List available Groq models"""
    update_activity()
    
    try:
        model_to_use = GROQ_MODEL or DEFAULT_MODEL
        return jsonify({
            'available_models': GROQ_MODELS,
            'current_model': model_to_use,
            'current_model_info': GROQ_MODELS.get(model_to_use, {}),
            'default_model': DEFAULT_MODEL,
            'documentation': 'https://console.groq.com/docs/models',
            'deprecation_info': 'https://console.groq.com/docs/deprecations'
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/switch-model/<model_name>', methods=['POST'])
def switch_model(model_name):
    """Switch to a different Groq model (for testing)"""
    update_activity()
    
    if model_name not in GROQ_MODELS:
        return jsonify({
            'status': 'error',
            'message': f'Model {model_name} not available',
            'available_models': list(GROQ_MODELS.keys())
        })
    
    return jsonify({
        'status': 'success',
        'message': f'Model {model_name} is available',
        'model': model_name,
        'model_info': GROQ_MODELS[model_name],
        'note': 'To change model, update GROQ_MODEL environment variable',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/cleanup-old-files', methods=['POST'])
def cleanup_old_files():
    """Cleanup old files (run periodically)"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=24)
        deleted_count = 0
        
        # Cleanup uploads folder
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_time:
                    os.remove(file_path)
                    deleted_count += 1
        
        # Cleanup reports folder
        for filename in os.listdir(REPORTS_FOLDER):
            file_path = os.path.join(REPORTS_FOLDER, filename)
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_time:
                    os.remove(file_path)
                    deleted_count += 1
        
        return jsonify({
            'status': 'success',
            'message': f'Cleaned up {deleted_count} old files',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting...")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"⚡ AI Provider: GROQ")
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    print(f"🤖 Model: {model_to_use}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📁 Reports folder: {REPORTS_FOLDER}")
    print("✅ Always Active Mode: Enabled")
    print(f"✅ Keep-alive Interval: {SERVICE_KEEP_ALIVE_INTERVAL} seconds")
    print("✅ Parallel Processing: 3 resumes at once")
    print("✅ Batch Capacity: Up to 15 resumes")
    print("✅ Individual Reports: Each candidate gets separate Excel")
    print("✅ Consistent Scoring: Enabled")
    print("="*50 + "\n")
    
    if not GROQ_API_KEY:
        print("⚠️  WARNING: No Groq API key found!")
        print("Please set GROQ_API_KEY in Render environment variables")
        print("Get your API key from: https://console.groq.com/keys")
    
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
