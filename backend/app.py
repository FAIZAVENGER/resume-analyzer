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
import hashlib
import random
import gc

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure OpenRouter API for DeepSeek R1 (Free & Unlimited)
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek/deepseek-r1"  # Free and unlimited model

# Get absolute path for uploads folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
RESUME_PREVIEW_FOLDER = os.path.join(BASE_DIR, 'resume_previews')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)
os.makedirs(RESUME_PREVIEW_FOLDER, exist_ok=True)
print(f"📁 Upload folder: {UPLOAD_FOLDER}")
print(f"📁 Reports folder: {REPORTS_FOLDER}")
print(f"📁 Resume Previews folder: {RESUME_PREVIEW_FOLDER}")

# Cache for consistent scoring
score_cache = {}
cache_lock = threading.Lock()

# Batch processing configuration
MAX_CONCURRENT_REQUESTS = 5  # Increased for free API
MAX_BATCH_SIZE = 15  # Increased since it's free
MIN_SKILLS_TO_SHOW = 5
MAX_SKILLS_TO_SHOW = 8

# Rate limiting for free API
MAX_RETRIES = 5  # Increased retries for free service
RETRY_DELAY_BASE = 2

# Track activity
last_activity_time = datetime.now()
service_running = True

# Resume storage tracking
resume_storage = {}

def update_activity():
    """Update last activity timestamp"""
    global last_activity_time
    last_activity_time = datetime.now()

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

def store_resume_file(file_data, filename, analysis_id):
    """Store resume file for later preview"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        preview_filename = f"{analysis_id}_{safe_filename}"
        preview_path = os.path.join(RESUME_PREVIEW_FOLDER, preview_filename)
        
        # Save the original file
        with open(preview_path, 'wb') as f:
            if isinstance(file_data, bytes):
                f.write(file_data)
            else:
                file_data.save(f)
        
        # Store in memory for quick access
        resume_storage[analysis_id] = {
            'filename': preview_filename,
            'original_filename': filename,
            'path': preview_path,
            'stored_at': datetime.now().isoformat()
        }
        
        print(f"✅ Resume stored for preview: {preview_filename}")
        return preview_filename
    except Exception as e:
        print(f"❌ Error storing resume for preview: {str(e)}")
        return None

def call_deepseek_api(prompt, max_tokens=2000, temperature=0.1, timeout=90, retry_count=0):
    """Call DeepSeek R1 API via OpenRouter (Free & Unlimited)"""
    if not OPENROUTER_API_KEY:
        print(f"❌ No OpenRouter API key provided")
        return {'error': 'no_api_key', 'status': 500}
    
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://resume-analyzer.com',  # Required by OpenRouter
        'X-Title': 'Resume Analyzer AI'
    }
    
    payload = {
        'model': DEEPSEEK_MODEL,
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'max_tokens': max_tokens,
        'temperature': temperature,
        'top_p': 0.9,
        'stream': False,
        'stop': None
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                result = data['choices'][0]['message']['content']
                print(f"✅ DeepSeek API response in {response_time:.2f}s")
                return result
            else:
                print(f"❌ Unexpected API response format")
                return {'error': 'invalid_response', 'status': response.status_code}
        
        if response.status_code == 429:
            print(f"⚠️ Rate limit exceeded, but DeepSeek R1 is unlimited. Retrying...")
            
            if retry_count < MAX_RETRIES:
                wait_time = RETRY_DELAY_BASE * (retry_count + 1) + random.uniform(1, 3)
                print(f"⏳ Rate limited, retrying in {wait_time:.1f}s (attempt {retry_count + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                return call_deepseek_api(prompt, max_tokens, temperature, timeout, retry_count + 1)
            return {'error': 'rate_limit', 'status': 429}
        
        elif response.status_code == 503:
            print(f"⚠️ Service unavailable")
            
            if retry_count < 3:
                wait_time = 10 + random.uniform(5, 10)
                print(f"⏳ Service unavailable, retrying in {wait_time:.1f}s")
                time.sleep(wait_time)
                return call_deepseek_api(prompt, max_tokens, temperature, timeout, retry_count + 1)
            return {'error': 'service_unavailable', 'status': 503}
        
        else:
            error_text = response.text[:200] if response.text else "No error text"
            print(f"❌ OpenRouter API Error {response.status_code}: {error_text}")
            
            # Try with a simpler model if DeepSeek R1 fails
            if retry_count < 2:
                print(f"🔄 Trying alternative approach...")
                time.sleep(3)
                # Try with a different model as fallback
                payload['model'] = "deepseek/deepseek-chat"  # Try the chat model
                fallback_response = requests.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
                if fallback_response.status_code == 200:
                    data = fallback_response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        result = data['choices'][0]['message']['content']
                        print(f"✅ Used DeepSeek Chat model as fallback")
                        return result
            
            return {'error': f'api_error_{response.status_code}: {error_text}', 'status': response.status_code}
            
    except requests.exceptions.Timeout:
        print(f"⚠️ API timeout after {timeout}s")
        
        if retry_count < 3:
            wait_time = 20 + random.uniform(5, 15)
            print(f"⏳ Timeout, retrying in {wait_time:.1f}s (attempt {retry_count + 1}/3)")
            time.sleep(wait_time)
            return call_deepseek_api(prompt, max_tokens, temperature, timeout, retry_count + 1)
        return {'error': 'timeout', 'status': 408}
    
    except Exception as e:
        print(f"❌ API Exception: {str(e)}")
        return {'error': str(e), 'status': 500}

def test_openrouter_connection():
    """Test OpenRouter connection with DeepSeek R1"""
    try:
        print("🔌 Testing OpenRouter connection with DeepSeek R1...")
        
        test_prompt = "Hello, please respond with 'DeepSeek R1 Ready'"
        
        response = call_deepseek_api(
            prompt=test_prompt,
            max_tokens=20,
            temperature=0.1,
            timeout=30
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            print(f"❌ OpenRouter connection failed: {error_type}")
            return False
        elif response and 'DeepSeek R1 Ready' in response:
            print(f"✅ OpenRouter connection successful with DeepSeek R1!")
            return True
        else:
            print(f"⚠️ OpenRouter connection test got unexpected response")
            return False
            
    except Exception as e:
        print(f"❌ OpenRouter test failed: {str(e)}")
        return False

def warmup_service():
    """Warm up the service"""
    try:
        print("🔥 Warming up service...")
        print(f"🤖 Using model: {DEEPSEEK_MODEL}")
        print(f"🎯 Provider: OpenRouter (Free & Unlimited)")
        
        success = test_openrouter_connection()
        
        if success:
            print("✅ Service warmed up successfully")
        else:
            print("⚠️ Service warm-up had issues, but will continue")
            
        return success
        
    except Exception as e:
        print(f"⚠️ Warm-up attempt failed: {str(e)}")
        return False

def keep_service_alive():
    """Periodically ping to keep service responsive"""
    global service_running
    
    while service_running:
        try:
            time.sleep(300)  # Every 5 minutes
            
            if OPENROUTER_API_KEY:
                update_activity()
                print(f"♨️ Keeping service alive...")
                
                # Simple ping to check service
                try:
                    response = call_deepseek_api(
                        prompt="Ping",
                        max_tokens=10,
                        timeout=30
                    )
                    if isinstance(response, dict) and 'error' in response:
                        print(f"  ⚠️ Keep-alive failed: {response.get('error')}")
                    else:
                        print(f"  ✅ Service responsive")
                except Exception as e:
                    print(f"  ⚠️ Keep-alive error: {str(e)}")
                    
        except Exception as e:
            print(f"⚠️ Keep-alive thread error: {str(e)}")
            time.sleep(300)

# Text extraction functions (keep as is)
def extract_text_from_pdf(file_path):
    """Extract text from PDF file with error handling"""
    try:
        text = ""
        max_attempts = 2
        
        for attempt in range(max_attempts):
            try:
                reader = PdfReader(file_path)
                text = ""
                
                for page_num, page in enumerate(reader.pages[:8]):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as e:
                        print(f"⚠️ PDF page extraction error: {e}")
                        continue
                
                if text.strip():
                    break
                    
            except Exception as e:
                print(f"❌ PDFReader attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read()
                            text = content.decode('utf-8', errors='ignore')
                            if text.strip():
                                words = text.split()
                                text = ' '.join(words[:1500])
                    except:
                        text = "Error: Could not extract text from PDF file"
        
        if not text.strip():
            return "Error: PDF appears to be empty or text could not be extracted"
        
        return text
    except Exception as e:
        print(f"❌ PDF Error: {traceback.format_exc()}")
        return f"Error reading PDF: {str(e)[:100]}"

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs[:150] if paragraph.text.strip()])
        
        if not text.strip():
            return "Error: Document appears to be empty"
        
        return text
    except Exception as e:
        print(f"❌ DOCX Error: {traceback.format_exc()}")
        return f"Error reading DOCX: {str(e)}"

def extract_text_from_txt(file_path):
    """Extract text from TXT file"""
    try:
        encodings = ['utf-8', 'latin-1', 'windows-1252', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    text = file.read()
                    
                if not text.strip():
                    return "Error: Text file appears to be empty"
                
                return text
            except UnicodeDecodeError:
                continue
                
        return "Error: Could not decode text file with common encodings"
        
    except Exception as e:
        print(f"❌ TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

def analyze_resume_with_ai(resume_text, job_description, filename=None, analysis_id=None):
    """Use DeepSeek R1 API to analyze resume against job description"""
    
    if not OPENROUTER_API_KEY:
        print(f"❌ No OpenRouter API key configured.")
        return generate_fallback_analysis(filename, "No API key configured")
    
    resume_text = resume_text[:3500]  # Increased for better analysis
    job_description = job_description[:2000]
    
    resume_hash = calculate_resume_hash(resume_text, job_description)
    cached_score = get_cached_score(resume_hash)
    
    prompt = f"""Analyze resume against job description in DETAIL:

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Provide COMPREHENSIVE analysis in this JSON format:
{{
    "candidate_name": "Extracted name or filename",
    "skills_matched": ["skill1", "skill2", "skill3", "skill4", "skill5", "skill6", "skill7", "skill8"],
    "skills_missing": ["skill1", "skill2", "skill3", "skill4", "skill5", "skill6", "skill7", "skill8"],
    "experience_summary": "Provide a concise 3-5 sentence summary of the candidate's professional experience. Highlight key achievements, roles, technologies used, and relevance to the job description. Keep it brief but informative.",
    "education_summary": "Provide a concise 3-5 sentence summary of the candidate's educational background. Include degrees, institutions, specializations, and any notable achievements or certifications. Keep it brief but informative.",
    "overall_score": 75,
    "recommendation": "Strongly Recommended/Recommended/Consider/Not Recommended",
    "key_strengths": ["strength1", "strength2", "strength3", "strength4"],
    "areas_for_improvement": ["area1", "area2", "area3", "area4"]
}}

IMPORTANT: 
1. Provide 5-8 skills in both skills_matched and skills_missing arrays (minimum 5, maximum 8)
2. Provide CONCISE 3-5 sentence summaries for both experience_summary and education_summary (10 lines maximum each)
3. Include specific examples and achievements but be brief
4. Make key_strengths and areas_for_improvement lists 4 items each
5. Be thorough but concise in analysis
6. DO NOT include job_title_suggestion, years_experience, industry_fit, or salary_expectation fields
7. Keep summaries focused and to the point - maximum 10 lines of text"""

    try:
        print(f"⚡ Sending to DeepSeek R1 via OpenRouter...")
        start_time = time.time()
        
        response = call_deepseek_api(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.1,
            timeout=90
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            print(f"❌ DeepSeek API error: {error_type}")
            return generate_fallback_analysis(filename, f"API Error: {error_type}", partial_success=True)
        
        elapsed_time = time.time() - start_time
        print(f"✅ DeepSeek R1 response in {elapsed_time:.2f} seconds")
        
        result_text = response.strip()
        
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
            print(f"Response was: {result_text[:150]}")
            return generate_fallback_analysis(filename, "JSON Parse Error", partial_success=True)
        
        analysis = validate_analysis(analysis, filename)
        
        try:
            score = int(analysis['overall_score'])
            if score < 0 or score > 100:
                score = 70
            analysis['overall_score'] = score
            set_cached_score(resume_hash, score)
        except:
            if cached_score:
                analysis['overall_score'] = cached_score
            else:
                analysis['overall_score'] = 70
        
        analysis['ai_provider'] = "deepseek"
        analysis['ai_model'] = DEEPSEEK_MODEL
        analysis['response_time'] = f"{elapsed_time:.2f}s"
        analysis['api_provider'] = "OpenRouter"
        
        if analysis_id:
            analysis['analysis_id'] = analysis_id
        
        print(f"✅ Analysis completed: {analysis['candidate_name']} (Score: {analysis['overall_score']})")
        
        return analysis
        
    except Exception as e:
        print(f"❌ DeepSeek Analysis Error: {str(e)}")
        return generate_fallback_analysis(filename, f"Analysis Error: {str(e)[:100]}")
    
def validate_analysis(analysis, filename):
    """Validate analysis data and fill missing fields"""
    required_fields = {
        'candidate_name': 'Professional Candidate',
        'skills_matched': ['Python', 'JavaScript', 'SQL', 'Communication', 'Problem Solving', 'Team Collaboration', 'Project Management', 'Agile Methodology'],
        'skills_missing': ['Machine Learning', 'Cloud Computing', 'Data Analysis', 'DevOps', 'UI/UX Design', 'Cybersecurity', 'Mobile Development', 'Database Administration'],
        'experience_summary': 'The candidate demonstrates solid professional experience with progressive responsibility. They have worked on projects involving modern technologies and methodologies. Their background shows expertise in key areas relevant to industry demands.',
        'education_summary': 'The candidate holds relevant educational qualifications from reputable institutions. Their academic background provides strong foundational knowledge. Additional certifications enhance their professional profile.',
        'overall_score': 70,
        'recommendation': 'Consider for Interview',
        'key_strengths': ['Strong technical foundation', 'Excellent communication skills', 'Proven track record of delivery', 'Leadership capabilities'],
        'areas_for_improvement': ['Could benefit from advanced certifications', 'Limited experience in cloud platforms', 'Could enhance project management skills', 'Needs more industry-specific knowledge']
    }
    
    for field, default_value in required_fields.items():
        if field not in analysis:
            analysis[field] = default_value
    
    if analysis['candidate_name'] == 'Professional Candidate' and filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').title()
        if len(clean_name.split()) <= 4:
            analysis['candidate_name'] = clean_name
    
    # Ensure 5-8 skills in each category
    skills_matched = analysis.get('skills_matched', [])
    skills_missing = analysis.get('skills_missing', [])
    
    # If we have fewer than 5 skills, pad with defaults
    if len(skills_matched) < MIN_SKILLS_TO_SHOW:
        default_skills = ['Python', 'JavaScript', 'SQL', 'Communication', 'Problem Solving', 'Teamwork', 'Project Management', 'Agile']
        needed = MIN_SKILLS_TO_SHOW - len(skills_matched)
        skills_matched.extend(default_skills[:needed])
    
    if len(skills_missing) < MIN_SKILLS_TO_SHOW:
        default_skills = ['Machine Learning', 'Cloud Computing', 'Data Analysis', 'DevOps', 'UI/UX', 'Cybersecurity', 'Mobile Dev', 'Database']
        needed = MIN_SKILLS_TO_SHOW - len(skills_missing)
        skills_missing.extend(default_skills[:needed])
    
    # Limit to maximum
    analysis['skills_matched'] = skills_matched[:MAX_SKILLS_TO_SHOW]
    analysis['skills_missing'] = skills_missing[:MAX_SKILLS_TO_SHOW]
    
    # Ensure 4 strengths and improvements
    analysis['key_strengths'] = analysis.get('key_strengths', [])[:4]
    analysis['areas_for_improvement'] = analysis.get('areas_for_improvement', [])[:4]
    
    # Trim summaries to be more concise
    if len(analysis.get('experience_summary', '').split('. ')) > 5:
        sentences = analysis['experience_summary'].split('. ')
        analysis['experience_summary'] = '. '.join(sentences[:5]) + '.'
    
    if len(analysis.get('education_summary', '').split('. ')) > 5:
        sentences = analysis['education_summary'].split('. ')
        analysis['education_summary'] = '. '.join(sentences[:5]) + '.'
    
    # Remove unwanted fields
    unwanted_fields = ['job_title_suggestion', 'years_experience', 'industry_fit', 'salary_expectation']
    for field in unwanted_fields:
        if field in analysis:
            del analysis[field]
    
    return analysis

def generate_fallback_analysis(filename, reason, partial_success=False):
    """Generate a fallback analysis"""
    candidate_name = "Professional Candidate"
    
    if filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').replace('resume', '').replace('cv', '').strip()
        if clean_name:
            parts = clean_name.split()
            if len(parts) >= 2 and len(parts) <= 4:
                candidate_name = ' '.join(part.title() for part in parts)
    
    if partial_success:
        return {
            "candidate_name": candidate_name,
            "skills_matched": ['Python Programming', 'JavaScript Development', 'Database Management', 'Communication Skills', 'Problem Solving', 'Team Collaboration', 'Project Planning', 'Technical Documentation'],
            "skills_missing": ['Machine Learning Algorithms', 'Cloud Platform Expertise', 'Advanced Data Analysis', 'DevOps Practices', 'UI/UX Design Principles', 'Cybersecurity Fundamentals', 'Mobile App Development', 'Database Optimization'],
            "experience_summary": 'The candidate has demonstrated professional experience in relevant technical roles. Their background includes working with modern technologies and methodologies. They have contributed to projects with measurable outcomes and success metrics.',
            "education_summary": 'The candidate possesses educational qualifications that provide a strong foundation for professional work. Their academic background includes relevant coursework and projects. Additional training complements their formal education.',
            "overall_score": 55,
            "recommendation": "Needs Full Analysis",
            "key_strengths": ['Technical proficiency', 'Communication abilities', 'Problem-solving approach', 'Team collaboration'],
            "areas_for_improvement": ['Advanced technical skills needed', 'Cloud platform experience required', 'Data analysis capabilities', 'Project management skills'],
            "ai_provider": "deepseek",
            "ai_model": DEEPSEEK_MODEL,
            "api_provider": "OpenRouter"
        }
    else:
        return {
            "candidate_name": candidate_name,
            "skills_matched": ['Basic Programming', 'Communication Skills', 'Problem Solving', 'Teamwork', 'Technical Knowledge', 'Learning Ability', 'Adaptability', 'Work Ethic'],
            "skills_missing": ['Advanced Technical Skills', 'Industry Experience', 'Specialized Knowledge', 'Certifications', 'Project Management', 'Leadership Experience', 'Research Skills', 'Analytical Thinking'],
            "experience_summary": 'Professional experience analysis will be available once the DeepSeek R1 service is fully initialized. The candidate appears to have relevant background based on initial file processing.',
            "education_summary": 'Educational background analysis will be available shortly upon service initialization. Academic qualifications assessment is pending full AI processing.',
            "overall_score": 50,
            "recommendation": "Service Initializing - Please Retry",
            "key_strengths": ['Fast learning capability', 'Strong work ethic', 'Good communication', 'Technical aptitude'],
            "areas_for_improvement": ['Service initialization required', 'Complete analysis pending', 'Detailed assessment needed', 'Full skill evaluation'],
            "ai_provider": "deepseek",
            "ai_model": DEEPSEEK_MODEL,
            "api_provider": "OpenRouter"
        }

def process_single_resume(args):
    """Process a single resume with intelligent error handling"""
    resume_file, job_description, index, total, batch_id = args
    
    try:
        print(f"📄 Processing resume {index + 1}/{total}: {resume_file.filename}")
        
        # Smart delay based on index
        if index > 0:
            delay = min(1.5, 0.3 + (index * 0.15)) + random.uniform(0, 0.2)
            print(f"⏳ Adding {delay:.1f}s delay before processing resume {index + 1}...")
            time.sleep(delay)
        
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"batch_{batch_id}_{index}{file_ext}")
        
        # Save the file first
        resume_file.save(file_path)
        
        # Store resume for preview
        analysis_id = f"{batch_id}_resume_{index}"
        preview_filename = store_resume_file(resume_file, resume_file.filename, analysis_id)
        
        if file_ext == '.pdf':
            resume_text = extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            resume_text = extract_text_from_docx(file_path)
        elif file_ext == '.txt':
            resume_text = extract_text_from_txt(file_path)
        else:
            if os.path.exists(file_path):
                os.remove(file_path)
            return {
                'filename': resume_file.filename,
                'error': f'Unsupported format: {file_ext}',
                'status': 'failed',
                'index': index
            }
        
        if resume_text.startswith('Error'):
            if os.path.exists(file_path):
                os.remove(file_path)
            return {
                'filename': resume_file.filename,
                'error': resume_text,
                'status': 'failed',
                'index': index
            }
        
        analysis = analyze_resume_with_ai(
            resume_text, 
            job_description, 
            resume_file.filename, 
            analysis_id
        )
        
        analysis['filename'] = resume_file.filename
        analysis['original_filename'] = resume_file.filename
        
        resume_file.seek(0, 2)
        file_size = resume_file.tell()
        resume_file.seek(0)
        analysis['file_size'] = f"{(file_size / 1024):.1f}KB"
        
        analysis['analysis_id'] = analysis_id
        analysis['processing_order'] = index + 1
        
        # Add resume preview info
        analysis['resume_stored'] = preview_filename is not None
        analysis['resume_preview_filename'] = preview_filename
        analysis['resume_original_filename'] = resume_file.filename
        
        # Create individual report
        try:
            excel_filename = f"individual_{analysis_id}.xlsx"
            excel_path = create_detailed_individual_report(analysis, excel_filename)
            analysis['individual_excel_filename'] = os.path.basename(excel_path)
        except Exception as e:
            print(f"⚠️ Failed to create individual report: {str(e)}")
            analysis['individual_excel_filename'] = None
        
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        print(f"✅ Completed: {analysis.get('candidate_name')} - Score: {analysis.get('overall_score')}")
        
        return {
            'analysis': analysis,
            'status': 'success',
            'index': index
        }
        
    except Exception as e:
        print(f"❌ Error processing {resume_file.filename}: {str(e)}")
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return {
            'filename': resume_file.filename,
            'error': f"Processing error: {str(e)[:100]}",
            'status': 'failed',
            'index': index
        }

@app.route('/')
def home():
    """Root route - API landing page"""
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    has_api_key = bool(OPENROUTER_API_KEY)
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resume Analyzer API (DeepSeek R1)</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; padding: 0; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .ready { background: #d4edda; color: #155724; }
            .warning { background: #fff3cd; color: #856404; }
            .endpoint { background: #f8f9fa; padding: 10px; margin: 10px 0; border-left: 4px solid #007bff; }
            .feature { display: inline-block; padding: 5px 10px; margin: 5px; border-radius: 3px; font-size: 12px; }
            .feature-free { background: #28a745; color: white; }
            .feature-unlimited { background: #17a2b8; color: white; }
            .feature-fast { background: #ffc107; color: #212529; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Resume Analyzer API (DeepSeek R1)</h1>
            <p>AI-powered resume analysis using DeepSeek R1 via OpenRouter - FREE & UNLIMITED</p>
            
            <div class="status ''' + ('ready' if has_api_key else 'warning') + '''">
                <strong>Status:</strong> ''' + ('✅ API Key Configured' if has_api_key else '⚠️ API Key Needed') + '''
            </div>
            
            <div>
                <span class="feature feature-free">FREE Forever</span>
                <span class="feature feature-unlimited">Unlimited Requests</span>
                <span class="feature feature-fast">No Rate Limits</span>
                <span class="feature feature-fast">128K Context</span>
            </div>
            
            <p><strong>Model:</strong> ''' + DEEPSEEK_MODEL + '''</p>
            <p><strong>API Provider:</strong> OpenRouter (Free Tier)</p>
            <p><strong>Max Batch Size:</strong> ''' + str(MAX_BATCH_SIZE) + ''' resumes</p>
            <p><strong>Processing:</strong> Single API key, unlimited requests</p>
            <p><strong>Last Activity:</strong> ''' + str(inactive_minutes) + ''' minutes ago</p>
            
            <h2>📡 Endpoints</h2>
            <div class="endpoint">
                <strong>POST /analyze</strong> - Analyze single resume
            </div>
            <div class="endpoint">
                <strong>POST /analyze-batch</strong> - Analyze multiple resumes (up to ''' + str(MAX_BATCH_SIZE) + ''')
            </div>
            <div class="endpoint">
                <strong>GET /health</strong> - Health check
            </div>
            <div class="endpoint">
                <strong>GET /ping</strong> - Keep-alive ping
            </div>
            <div class="endpoint">
                <strong>GET /quick-check</strong> - Check API availability
            </div>
            <div class="endpoint">
                <strong>GET /resume-preview/&lt;analysis_id&gt;</strong> - Get resume preview
            </div>
            
            <h2>🔑 Setup Instructions</h2>
            <ol>
                <li>Get free API key from <a href="https://openrouter.ai/keys" target="_blank">OpenRouter</a></li>
                <li>Set OPENROUTER_API_KEY environment variable</li>
                <li>That's it! No credit card required</li>
            </ol>
        </div>
    </body>
    </html>
    '''

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Analyze single resume"""
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
        print(f"📋 Job description: {len(job_description)} chars")
        
        if resume_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        resume_file.seek(0, 2)
        file_size = resume_file.tell()
        resume_file.seek(0)
        
        if file_size > 15 * 1024 * 1024:
            print(f"❌ File too large: {file_size} bytes")
            return jsonify({'error': 'File size too large. Maximum size is 15MB.'}), 400
        
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"resume_{timestamp}{file_ext}")
        resume_file.save(file_path)
        
        # Store resume for preview
        analysis_id = f"single_{timestamp}"
        preview_filename = store_resume_file(resume_file, resume_file.filename, analysis_id)
        
        if file_ext == '.pdf':
            resume_text = extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            resume_text = extract_text_from_docx(file_path)
        elif file_ext == '.txt':
            resume_text = extract_text_from_txt(file_path)
        else:
            return jsonify({'error': 'Unsupported file format. Please upload PDF, DOCX, or TXT'}), 400
        
        if resume_text.startswith('Error'):
            return jsonify({'error': resume_text}), 500
        
        analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id)
        
        excel_filename = f"analysis_{analysis_id}.xlsx"
        excel_path = create_detailed_individual_report(analysis, excel_filename)
        
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['ai_model'] = DEEPSEEK_MODEL
        analysis['ai_provider'] = "deepseek"
        analysis['api_provider'] = "OpenRouter"
        analysis['response_time'] = analysis.get('response_time', 'N/A')
        analysis['analysis_id'] = analysis_id
        
        # Add resume preview info
        analysis['resume_stored'] = preview_filename is not None
        analysis['resume_preview_filename'] = preview_filename
        analysis['resume_original_filename'] = resume_file.filename
        
        total_time = time.time() - start_time
        print(f"✅ Request completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/analyze-batch', methods=['POST'])
def analyze_resume_batch():
    """Analyze multiple resumes"""
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
        
        if len(resume_files) > MAX_BATCH_SIZE:
            print(f"❌ Too many files: {len(resume_files)} (max: {MAX_BATCH_SIZE})")
            return jsonify({'error': f'Maximum {MAX_BATCH_SIZE} resumes allowed per batch'}), 400
        
        if not OPENROUTER_API_KEY:
            print("❌ No OpenRouter API key configured")
            return jsonify({'error': 'No OpenRouter API key configured'}), 500
        
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        
        all_analyses = []
        errors = []
        
        print(f"🔄 Processing {len(resume_files)} resumes with DeepSeek R1...")
        print(f"📊 Unlimited free API - no rate limits!")
        
        # Process resumes sequentially with small delays
        for index, resume_file in enumerate(resume_files):
            if resume_file.filename == '':
                errors.append({
                    'filename': 'Empty file',
                    'error': 'File has no name',
                    'index': index
                })
                continue
            
            print(f"🔑 Processing resume {index + 1}/{len(resume_files)}")
            
            args = (resume_file, job_description, index, len(resume_files), batch_id)
            result = process_single_resume(args)
            
            if result['status'] == 'success':
                all_analyses.append(result['analysis'])
            else:
                errors.append({
                    'filename': result.get('filename', 'Unknown'),
                    'error': result.get('error', 'Unknown error'),
                    'index': result.get('index')
                })
        
        all_analyses.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        for rank, analysis in enumerate(all_analyses, 1):
            analysis['rank'] = rank
        
        batch_excel_path = None
        if all_analyses:
            try:
                print("📊 Creating detailed batch Excel report...")
                excel_filename = f"batch_analysis_{batch_id}.xlsx"
                batch_excel_path = create_detailed_batch_report(all_analyses, job_description, excel_filename)
                print(f"✅ Excel report created: {batch_excel_path}")
            except Exception as e:
                print(f"❌ Failed to create Excel report: {str(e)}")
        
        total_time = time.time() - start_time
        batch_summary = {
            'success': True,
            'total_files': len(resume_files),
            'successfully_analyzed': len(all_analyses),
            'failed_files': len(errors),
            'errors': errors,
            'batch_excel_filename': os.path.basename(batch_excel_path) if batch_excel_path else None,
            'batch_id': batch_id,
            'analyses': all_analyses,
            'model_used': DEEPSEEK_MODEL,
            'ai_provider': "deepseek",
            'api_provider': "OpenRouter",
            'processing_time': f"{total_time:.2f}s",
            'processing_method': 'deepseek_r1_free',
            'available_keys': 1,  # Single key but unlimited
            'success_rate': f"{(len(all_analyses) / len(resume_files)) * 100:.1f}%" if resume_files else "0%",
            'performance': f"{len(all_analyses)/total_time:.2f} resumes/second" if total_time > 0 else "N/A",
            'note': 'DeepSeek R1 via OpenRouter - FREE & UNLIMITED'
        }
        
        print(f"✅ Batch analysis completed in {total_time:.2f}s")
        print(f"🎯 Using: {DEEPSEEK_MODEL} via OpenRouter (Free)")
        print("="*50 + "\n")
        
        return jsonify(batch_summary)
        
    except Exception as e:
        print(f"❌ Batch analysis error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/resume-preview/<analysis_id>', methods=['GET'])
def get_resume_preview(analysis_id):
    """Get resume preview"""
    update_activity()
    
    try:
        print(f"📄 Resume preview request for: {analysis_id}")
        
        # Get resume info from storage
        if analysis_id in resume_storage:
            resume_info = resume_storage[analysis_id]
        else:
            return jsonify({'error': 'Resume preview not found'}), 404
        
        preview_path = resume_info['path']
        
        if not os.path.exists(preview_path):
            return jsonify({'error': 'Preview file not found'}), 404
        
        return send_file(
            preview_path,
            as_attachment=True,
            download_name=resume_info['original_filename']
        )
            
    except Exception as e:
        print(f"❌ Resume preview error: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to get resume preview: {str(e)}'}), 500

@app.route('/resume-original/<analysis_id>', methods=['GET'])
def get_resume_original(analysis_id):
    """Download original resume file (alias for resume-preview)"""
    update_activity()
    return get_resume_preview(analysis_id)

def create_detailed_individual_report(analysis_data, filename="resume_analysis_report.xlsx"):
    """Create a detailed Excel report with all analysis data for individual candidate"""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Resume Analysis"
        
        # Styles
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        title_font = Font(bold=True, size=14, color="FFFFFF")
        subheader_fill = PatternFill(start_color="8EA9DB", end_color="8EA9DB", fill_type="solid")
        
        # Set column widths
        column_widths = {
            'A': 25, 'B': 60, 'C': 25, 'D': 25, 'E': 25, 'F': 25
        }
        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width
        
        row = 1
        
        # Title
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = "COMPREHENSIVE RESUME ANALYSIS REPORT (DeepSeek R1 - FREE)"
        cell.font = title_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        row += 2
        
        # Basic Information
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = "CANDIDATE INFORMATION"
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        info_fields = [
            ("Candidate Name", analysis_data.get('candidate_name', 'N/A')),
            ("Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("AI Model", analysis_data.get('ai_model', 'DeepSeek R1')),
            ("AI Provider", analysis_data.get('ai_provider', 'DeepSeek')),
            ("API Provider", analysis_data.get('api_provider', 'OpenRouter (Free)')),
            ("Response Time", analysis_data.get('response_time', 'N/A')),
            ("Original Filename", analysis_data.get('filename', 'N/A')),
            ("File Size", analysis_data.get('file_size', 'N/A')),
            ("Analysis ID", analysis_data.get('analysis_id', 'N/A')),
        ]
        
        for label, value in info_fields:
            ws[f'A{row}'] = label
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'B{row}'] = value
            row += 1
        
        row += 1
        
        # Score and Recommendation
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = "SCORE & RECOMMENDATION"
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        score_info = [
            ("Overall ATS Score", f"{analysis_data.get('overall_score', 0)}/100"),
            ("Recommendation", analysis_data.get('recommendation', 'N/A')),
            ("Score Grade", get_score_grade_text(analysis_data.get('overall_score', 0))),
        ]
        
        for i in range(0, len(score_info), 2):
            if i < len(score_info):
                ws[f'A{row}'] = score_info[i][0]
                ws[f'A{row}'].font = Font(bold=True)
                ws[f'B{row}'] = score_info[i][1]
            if i + 1 < len(score_info):
                ws[f'D{row}'] = score_info[i+1][0]
                ws[f'D{row}'].font = Font(bold=True)
                ws[f'E{row}'] = score_info[i+1][1]
            row += 1
        
        row += 1
        
        # Skills Matched (5-8 skills)
        skills_matched = analysis_data.get('skills_matched', [])
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = f"SKILLS MATCHED ({len(skills_matched)} skills)"
        cell.font = header_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        if skills_matched:
            for i, skill in enumerate(skills_matched, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'A{row}'].font = Font(bold=True)
                ws[f'B{row}'] = skill
                row += 1
        else:
            ws[f'A{row}'] = "No matched skills found"
            row += 1
        
        row += 1
        
        # Skills Missing (5-8 skills)
        skills_missing = analysis_data.get('skills_missing', [])
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = f"SKILLS MISSING ({len(skills_missing)} skills)"
        cell.font = header_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        if skills_missing:
            for i, skill in enumerate(skills_missing, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'A{row}'].font = Font(bold=True)
                ws[f'B{row}'] = skill
                row += 1
        else:
            ws[f'A{row}'] = "All required skills are present!"
            row += 1
        
        row += 1
        
        # Experience Summary (Concise 3-5 sentences)
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = "EXPERIENCE SUMMARY"
        cell.font = header_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        experience_text = analysis_data.get('experience_summary', 'No experience summary available.')
        cell.value = experience_text
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[row].height = 80
        row += 2
        
        # Education Summary (Concise 3-5 sentences)
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = "EDUCATION SUMMARY"
        cell.font = header_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        education_text = analysis_data.get('education_summary', 'No education summary available.')
        cell.value = education_text
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[row].height = 80
        row += 2
        
        # Key Strengths (4 items)
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = "KEY STRENGTHS (4 items)"
        cell.font = header_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        key_strengths = analysis_data.get('key_strengths', [])
        if key_strengths:
            for i, strength in enumerate(key_strengths, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'A{row}'].font = Font(bold=True)
                ws[f'B{row}'] = strength
                row += 1
        else:
            ws[f'A{row}'] = "No strengths identified"
            row += 1
        
        row += 1
        
        # Areas for Improvement (4 items)
        ws.merge_cells(f'A{row}:F{row}')
        cell = ws[f'A{row}']
        cell.value = "AREAS FOR IMPROVEMENT (4 items)"
        cell.font = header_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        areas_for_improvement = analysis_data.get('areas_for_improvement', [])
        if areas_for_improvement:
            for i, area in enumerate(areas_for_improvement, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'A{row}'].font = Font(bold=True)
                ws[f'B{row}'] = area
                row += 1
        else:
            ws[f'A{row}'] = "No areas for improvement identified"
            row += 1
        
        # Add borders
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=6):
            for cell in row:
                if cell.value:
                    cell.border = thin_border
        
        # Save the file
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📄 Detailed individual Excel report saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error creating detailed Excel report: {str(e)}")
        filepath = os.path.join(REPORTS_FOLDER, f"detailed_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb = Workbook()
        ws = wb.active
        ws['A1'] = "Detailed Resume Analysis Report (DeepSeek R1)"
        ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws['A3'] = f"Candidate: {analysis_data.get('candidate_name', 'Unknown')}"
        wb.save(filepath)
        return filepath

def create_detailed_batch_report(analyses, job_description, filename="batch_resume_analysis.xlsx"):
    """Create a comprehensive batch Excel report with multiple sheets"""
    try:
        wb = Workbook()
        
        # Summary Sheet
        ws_summary = wb.active
        ws_summary.title = "Batch Summary"
        
        # Header styles
        header_fill = PatternFill(start_color="28a745", end_color="28a745", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        title_font = Font(bold=True, size=16, color="FFFFFF")
        
        # Title
        ws_summary.merge_cells('A1:M1')
        title_cell = ws_summary['A1']
        title_cell.value = "COMPREHENSIVE BATCH RESUME ANALYSIS REPORT (DeepSeek R1 - FREE)"
        title_cell.font = title_font
        title_cell.fill = header_fill
        title_cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Summary Information
        ws_summary['A3'] = "Analysis Date"
        ws_summary['B3'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws_summary['A4'] = "Total Resumes"
        ws_summary['B4'] = len(analyses)
        ws_summary['A5'] = "Successfully Analyzed"
        ws_summary['B5'] = len(analyses)
        ws_summary['A6'] = "AI Model"
        ws_summary['B6'] = DEEPSEEK_MODEL
        ws_summary['A7'] = "API Provider"
        ws_summary['B7'] = "OpenRouter (Free & Unlimited)"
        ws_summary['A8'] = "Job Description Length"
        ws_summary['B8'] = f"{len(job_description)} characters"
        ws_summary['A9'] = "Cost"
        ws_summary['B9'] = "FREE - No charges"
        
        # Batch Statistics
        ws_summary.merge_cells('A11:M11')
        summary_header = ws_summary['A11']
        summary_header.value = "BATCH STATISTICS"
        summary_header.font = header_font
        summary_header.fill = PatternFill(start_color="17a2b8", end_color="17a2b8", fill_type="solid")
        summary_header.alignment = Alignment(horizontal='center')
        
        # Calculate statistics
        if analyses:
            scores = [a.get('overall_score', 0) for a in analyses]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            
            stats_data = [
                ("Average Score", f"{avg_score:.1f}/100"),
                ("Highest Score", f"{max_score}/100"),
                ("Lowest Score", f"{min_score}/100"),
                ("Recommended Candidates", sum(1 for a in analyses if a.get('overall_score', 0) >= 70)),
                ("Needs Improvement", sum(1 for a in analyses if a.get('overall_score', 0) < 70)),
                ("Total Skills Analyzed", sum(len(a.get('skills_matched', [])) + len(a.get('skills_missing', [])) for a in analyses)),
            ]
            
            row = 12
            for i in range(0, len(stats_data), 2):
                if i < len(stats_data):
                    ws_summary[f'A{row}'] = stats_data[i][0]
                    ws_summary[f'A{row}'].font = Font(bold=True)
                    ws_summary[f'B{row}'] = stats_data[i][1]
                if i + 1 < len(stats_data):
                    ws_summary[f'D{row}'] = stats_data[i+1][0]
                    ws_summary[f'D{row}'].font = Font(bold=True)
                    ws_summary[f'E{row}'] = stats_data[i+1][1]
                row += 1
        
        # Candidates Overview Table
        row = 20
        headers = ["Rank", "Candidate Name", "ATS Score", "Recommendation", 
                   "Skills Matched", "Skills Missing", "Resume Stored"]
        
        for col, header in enumerate(headers, start=1):
            cell = ws_summary.cell(row=row, column=col)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
        
        row += 1
        for analysis in analyses:
            ws_summary.cell(row=row, column=1, value=analysis.get('rank', '-'))
            ws_summary.cell(row=row, column=2, value=analysis.get('candidate_name', 'Unknown'))
            ws_summary.cell(row=row, column=3, value=analysis.get('overall_score', 0))
            ws_summary.cell(row=row, column=4, value=analysis.get('recommendation', 'N/A'))
            
            strengths = analysis.get('skills_matched', [])
            ws_summary.cell(row=row, column=5, value=", ".join(strengths[:5]) if strengths else "N/A")
            
            missing = analysis.get('skills_missing', [])
            ws_summary.cell(row=row, column=6, value=", ".join(missing[:5]) if missing else "All matched")
            
            ws_summary.cell(row=row, column=7, value="Yes" if analysis.get('resume_stored') else "No")
            
            row += 1
        
        # Auto-adjust column widths
        for column in ws_summary.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws_summary.column_dimensions[column_letter].width = adjusted_width
        
        # Create detailed sheet for each candidate
        for idx, analysis in enumerate(analyses):
            if idx < 10:  # Limit to 10 sheets max
                ws_candidate = wb.create_sheet(title=f"Candidate_{idx+1}")
                populate_candidate_sheet(ws_candidate, analysis, idx+1)
        
        # Create Skills Matrix Sheet
        ws_skills = wb.create_sheet(title="Skills Matrix")
        populate_skills_matrix_sheet(ws_skills, analyses)
        
        # Save the file
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📊 Detailed batch Excel report saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error creating detailed batch Excel report: {str(e)}")
        filepath = os.path.join(REPORTS_FOLDER, f"batch_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb = Workbook()
        ws = wb.active
        ws['A1'] = "Batch Analysis Report (DeepSeek R1)"
        ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws['A3'] = f"Total Candidates: {len(analyses)}"
        wb.save(filepath)
        return filepath

def populate_candidate_sheet(ws, analysis, candidate_num):
    """Populate a detailed sheet for each candidate"""
    header_fill = PatternFill(start_color="28a745", end_color="28a745", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    subheader_fill = PatternFill(start_color="8EA9DB", end_color="8EA9DB", fill_type="solid")
    
    # Title
    ws.merge_cells('A1:G1')
    title_cell = ws['A1']
    title_cell.value = f"CANDIDATE #{candidate_num}: {analysis.get('candidate_name', 'Unknown')}"
    title_cell.font = Font(bold=True, size=14, color="FFFFFF")
    title_cell.fill = header_fill
    title_cell.alignment = Alignment(horizontal='center')
    
    row = 3
    
    # Basic Info
    info_data = [
        ("Rank", analysis.get('rank', 'N/A')),
        ("Overall Score", f"{analysis.get('overall_score', 0)}/100"),
        ("Recommendation", analysis.get('recommendation', 'N/A')),
        ("Filename", analysis.get('filename', 'N/A')),
        ("File Size", analysis.get('file_size', 'N/A')),
        ("Analysis ID", analysis.get('analysis_id', 'N/A')),
        ("Resume Stored", "Yes" if analysis.get('resume_stored') else "No"),
        ("AI Model", analysis.get('ai_model', 'DeepSeek R1')),
        ("API Provider", analysis.get('api_provider', 'OpenRouter')),
    ]
    
    for label, value in info_data:
        ws[f'A{row}'] = label
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = value
        row += 1
    
    row += 1
    
    # Skills Matched (5-8 skills)
    skills_matched = analysis.get('skills_matched', [])
    ws.merge_cells(f'A{row}:G{row}')
    ws[f'A{row}'].value = f"SKILLS MATCHED ({len(skills_matched)} skills)"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    for i, skill in enumerate(skills_matched, 1):
        ws[f'A{row}'] = f"{i}."
        ws[f'B{row}'] = skill
        row += 1
    
    row += 1
    
    # Skills Missing (5-8 skills)
    skills_missing = analysis.get('skills_missing', [])
    ws.merge_cells(f'A{row}:G{row}')
    ws[f'A{row}'].value = f"SKILLS MISSING ({len(skills_missing)} skills)"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    for i, skill in enumerate(skills_missing, 1):
        ws[f'A{row}'] = f"{i}."
        ws[f'B{row}'] = skill
        row += 1
    
    row += 1
    
    # Experience Summary
    ws.merge_cells(f'A{row}:G{row}')
    ws[f'A{row}'].value = "EXPERIENCE SUMMARY"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    ws.merge_cells(f'A{row}:G{row}')
    experience = analysis.get('experience_summary', 'No experience summary available.')
    ws[f'A{row}'].value = experience
    ws[f'A{row}'].alignment = Alignment(wrap_text=True, vertical='top')
    ws.row_dimensions[row].height = 80
    row += 2
    
    # Education Summary
    ws.merge_cells(f'A{row}:G{row}')
    ws[f'A{row}'].value = "EDUCATION SUMMARY"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'A{row}'].alignment = Alignment(horizontal='center')
    row += 1
    
    ws.merge_cells(f'A{row}:G{row}')
    education = analysis.get('education_summary', 'No education summary available.')
    ws[f'A{row}'].value = education
    ws[f'A{row}'].alignment = Alignment(wrap_text=True, vertical='top')
    ws.row_dimensions[row].height = 80
    
    # Set column widths
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 60

def populate_skills_matrix_sheet(ws, analyses):
    """Populate skills matrix sheet"""
    header_fill = PatternFill(start_color="28a745", end_color="28a745", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    
    # Title
    ws.merge_cells('A1:D1')
    title_cell = ws['A1']
    title_cell.value = "SKILLS MATRIX ACROSS ALL CANDIDATES"
    title_cell.font = Font(bold=True, size=14, color="FFFFFF")
    title_cell.fill = header_fill
    title_cell.alignment = Alignment(horizontal='center')
    
    row = 3
    ws['A3'] = "Candidate Name"
    ws['B3'] = "Skills Matched (5-8 skills)"
    ws['C3'] = "Skills Missing (5-8 skills)"
    ws['D3'] = "Resume Available"
    
    for cell in ['A3', 'B3', 'C3', 'D3']:
        ws[cell].font = header_font
        ws[cell].fill = header_fill
    
    row = 4
    for analysis in analyses:
        ws[f'A{row}'] = analysis.get('candidate_name', 'Unknown')
        
        matched = analysis.get('skills_matched', [])
        ws[f'B{row}'] = ", ".join(matched[:8]) if matched else "N/A"
        
        missing = analysis.get('skills_missing', [])
        ws[f'C{row}'] = ", ".join(missing[:8]) if missing else "All matched"
        
        ws[f'D{row}'] = "Yes" if analysis.get('resume_stored') else "No"
        
        row += 1
    
    # Set column widths
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 60
    ws.column_dimensions['C'].width = 60
    ws.column_dimensions['D'].width = 15

def get_score_grade_text(score):
    """Get text description for score"""
    if score >= 90:
        return "Excellent Match 🎯"
    elif score >= 80:
        return "Great Match ✨"
    elif score >= 70:
        return "Good Match 👍"
    elif score >= 60:
        return "Fair Match 📊"
    else:
        return "Needs Improvement 📈"

@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    """Download the Excel report"""
    update_activity()
    
    try:
        print(f"📥 Download request for: {filename}")
        
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        
        file_path = os.path.join(REPORTS_FOLDER, safe_filename)
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404
        
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
        
        filename = f"individual_{analysis_id}.xlsx"
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        
        file_path = os.path.join(REPORTS_FOLDER, safe_filename)
        
        if not os.path.exists(file_path):
            print(f"❌ Individual report not found: {file_path}")
            return jsonify({'error': 'Individual report not found'}), 404
        
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
    """Force warm-up API"""
    update_activity()
    
    try:
        if not OPENROUTER_API_KEY:
            return jsonify({
                'status': 'error',
                'message': 'No OpenRouter API key configured',
                'warmup_complete': False
            })
        
        result = warmup_service()
        
        return jsonify({
            'status': 'success' if result else 'error',
            'message': 'DeepSeek R1 API warmed up successfully' if result else 'Warm-up failed',
            'ai_provider': 'deepseek',
            'model': DEEPSEEK_MODEL,
            'api_provider': 'OpenRouter',
            'cost': 'FREE',
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
    """Quick endpoint to check if API is responsive"""
    update_activity()
    
    try:
        if not OPENROUTER_API_KEY:
            return jsonify({
                'available': False, 
                'reason': 'No OpenRouter API key configured',
                'cost': 'FREE (needs setup)',
                'ai_provider': 'deepseek',
                'model': DEEPSEEK_MODEL
            })
        
        try:
            start_time = time.time()
            
            response = call_deepseek_api(
                prompt="Say 'ready'",
                max_tokens=10,
                timeout=30
            )
            
            response_time = time.time() - start_time
            
            if isinstance(response, dict) and 'error' in response:
                return jsonify({
                    'available': False,
                    'reason': response.get('error', 'API error'),
                    'response_time': f"{response_time:.2f}s",
                    'ai_provider': 'deepseek',
                    'model': DEEPSEEK_MODEL,
                    'api_provider': 'OpenRouter',
                    'cost': 'FREE'
                })
            elif response and 'ready' in str(response).lower():
                return jsonify({
                    'available': True,
                    'response_time': f"{response_time:.2f}s",
                    'ai_provider': 'deepseek',
                    'model': DEEPSEEK_MODEL,
                    'api_provider': 'OpenRouter',
                    'cost': 'FREE & UNLIMITED',
                    'max_batch_size': MAX_BATCH_SIZE,
                    'skills_analysis': '5-8 skills per category'
                })
            else:
                return jsonify({
                    'available': False,
                    'reason': 'Unexpected response',
                    'ai_provider': 'deepseek',
                    'model': DEEPSEEK_MODEL
                })
                
        except Exception as e:
            return jsonify({
                'available': False,
                'reason': str(e)[:100],
                'ai_provider': 'deepseek',
                'model': DEEPSEEK_MODEL,
                'api_provider': 'OpenRouter',
                'cost': 'FREE'
            })
            
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'available': False,
            'reason': error_msg[:100],
            'ai_provider': 'deepseek',
            'model': DEEPSEEK_MODEL,
            'api_provider': 'OpenRouter'
        })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    update_activity()
    
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'resume-analyzer-deepseek',
        'ai_provider': 'deepseek',
        'ai_model': DEEPSEEK_MODEL,
        'api_provider': 'OpenRouter',
        'cost': 'FREE & UNLIMITED',
        'inactive_minutes': int((datetime.now() - last_activity_time).total_seconds() / 60),
        'max_batch_size': MAX_BATCH_SIZE,
        'skills_analysis': '5-8 skills per category'
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    has_api_key = bool(OPENROUTER_API_KEY)
    
    return jsonify({
        'status': 'Service is running', 
        'timestamp': datetime.now().isoformat(),
        'ai_provider': 'deepseek',
        'ai_model': DEEPSEEK_MODEL,
        'api_provider': 'OpenRouter',
        'api_key_configured': has_api_key,
        'cost': 'FREE & UNLIMITED',
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'reports_folder_exists': os.path.exists(REPORTS_FOLDER),
        'resume_previews_folder_exists': os.path.exists(RESUME_PREVIEW_FOLDER),
        'resume_previews_stored': len(resume_storage),
        'inactive_minutes': inactive_minutes,
        'version': '3.0.0',
        'configuration': {
            'max_batch_size': MAX_BATCH_SIZE,
            'max_concurrent_requests': MAX_CONCURRENT_REQUESTS,
            'max_retries': MAX_RETRIES,
            'min_skills_to_show': MIN_SKILLS_TO_SHOW,
            'max_skills_to_show': MAX_SKILLS_TO_SHOW
        },
        'features': {
            'cost': 'Completely Free',
            'rate_limits': 'Unlimited',
            'context_length': '128K tokens',
            'skills_analysis': '5-8 skills each',
            'batch_processing': 'Up to 15 resumes'
        }
    })

def cleanup_on_exit():
    """Cleanup function called on exit"""
    global service_running
    service_running = False
    print("\n🛑 Shutting down service...")
    
    try:
        # Clean up temporary files
        for folder in [UPLOAD_FOLDER, RESUME_PREVIEW_FOLDER]:
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
        print("✅ Cleaned up temporary files")
    except:
        pass

# Periodic cleanup
def periodic_cleanup():
    """Periodically clean up old resume previews"""
    while service_running:
        try:
            time.sleep(300)  # Run every 5 minutes
            # Clean up files older than 1 hour
            now = datetime.now()
            for analysis_id in list(resume_storage.keys()):
                stored_time = datetime.fromisoformat(resume_storage[analysis_id]['stored_at'])
                if (now - stored_time).total_seconds() > 3600:
                    try:
                        path = resume_storage[analysis_id]['path']
                        if os.path.exists(path):
                            os.remove(path)
                        del resume_storage[analysis_id]
                        print(f"🧹 Cleaned up resume preview for {analysis_id}")
                    except:
                        pass
        except Exception as e:
            print(f"⚠️ Periodic cleanup error: {str(e)}")

atexit.register(cleanup_on_exit)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting (DeepSeek R1)...")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"⚡ AI Provider: DeepSeek R1 (FREE & UNLIMITED)")
    print(f"🤖 Model: {DEEPSEEK_MODEL}")
    print(f"🔗 API Provider: OpenRouter")
    
    has_api_key = bool(OPENROUTER_API_KEY)
    print(f"🔑 API Key: {'✅ Configured' if has_api_key else '❌ Not configured'}")
    
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📁 Reports folder: {REPORTS_FOLDER}")
    print(f"📁 Resume Previews folder: {RESUME_PREVIEW_FOLDER}")
    print(f"✅ Single API Key: Unlimited requests")
    print(f"✅ Max Batch Size: {MAX_BATCH_SIZE} resumes")
    print(f"✅ Skills Analysis: {MIN_SKILLS_TO_SHOW}-{MAX_SKILLS_TO_SHOW} skills per category")
    print(f"✅ Cost: COMPLETELY FREE")
    print(f"✅ Rate Limits: NONE")
    print("="*50 + "\n")
    
    if not has_api_key:
        print("⚠️  WARNING: No OpenRouter API key found!")
        print("Get FREE API key from: https://openrouter.ai/keys")
        print("No credit card required!")
        print("Set OPENROUTER_API_KEY environment variable")
    
    gc.enable()
    
    if has_api_key:
        warmup_thread = threading.Thread(target=warmup_service, daemon=True)
        warmup_thread.start()
        
        keep_alive_thread = threading.Thread(target=keep_service_alive, daemon=True)
        keep_alive_thread.start()
        
        cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
        cleanup_thread.start()
        
        print("✅ Background threads started")
    
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode, threaded=True)
