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
import random
from itertools import cycle
import gc
import sys
from typing import Dict, List, Tuple, Any

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure DeepSeek API
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')

# Available DeepSeek models
DEEPSEEK_MODELS = {
    'deepseek-chat': {
        'name': 'DeepSeek Chat',
        'context_length': 32768,
        'provider': 'DeepSeek',
        'description': 'General purpose chat model with 32K context',
        'status': 'production',
        'free_tier': False,
        'max_tokens': 8192
    },
    'deepseek-coder': {
        'name': 'DeepSeek Coder',
        'context_length': 16384,
        'provider': 'DeepSeek',
        'description': 'Specialized for coding tasks',
        'status': 'production',
        'free_tier': False,
        'max_tokens': 8192
    }
}

# Default working model
DEFAULT_MODEL = 'deepseek-chat'

# Track API status
warmup_complete = False
last_activity_time = datetime.now()

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

# Batch processing configuration
MAX_CONCURRENT_REQUESTS = 3  # Max concurrent requests to DeepSeek API
MAX_BATCH_SIZE = 10  # Maximum number of resumes per batch
MAX_INDIVIDUAL_REPORTS = 10  # Limit individual Excel reports

# Rate limiting protection
MAX_RETRIES = 3
RETRY_DELAY_BASE = 3

# Memory optimization
service_running = True

# Domain-specific keywords for VLSI and CS
VLSI_KEYWORDS = {
    'design': ['rtl', 'verilog', 'vhdl', 'systemverilog', 'digital design', 'asic', 'fpga', 'soc'],
    'verification': ['uvm', 'systemc', 'assertions', 'coverage', 'formal verification', 'testbench'],
    'backend': ['physical design', 'floorplan', 'placement', 'routing', 'timing analysis', 'drc', 'lvs'],
    'tools': ['cadence', 'synopsys', 'mentor graphics', 'vivado', 'quartus', 'innovus', 'icc2'],
    'skills': ['low power design', 'clock domain crossing', 'power integrity', 'signal integrity']
}

CS_KEYWORDS = {
    'programming': ['python', 'java', 'c++', 'javascript', 'typescript', 'go', 'rust', 'c#'],
    'web': ['react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring', 'express'],
    'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'ci/cd'],
    'databases': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch'],
    'ml_ai': ['machine learning', 'deep learning', 'tensorflow', 'pytorch', 'nlp', 'computer vision']
}

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

def extract_domain_specific_keywords(text: str) -> Dict[str, List[str]]:
    """Extract domain-specific keywords from text"""
    text_lower = text.lower()
    domains = {}
    
    # Check for VLSI keywords
    vlsi_matches = []
    for category, keywords in VLSI_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                vlsi_matches.append(keyword)
    if vlsi_matches:
        domains['VLSI'] = list(set(vlsi_matches))
    
    # Check for CS keywords
    cs_matches = []
    for category, keywords in CS_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                cs_matches.append(keyword)
    if cs_matches:
        domains['CS'] = list(set(cs_matches))
    
    return domains

def analyze_resume_structure(text: str) -> float:
    """Analyze resume structure quality"""
    sections = ['experience', 'education', 'skills', 'projects', 'summary']
    found_sections = 0
    
    for section in sections:
        if re.search(rf'\b{section}\b', text.lower()):
            found_sections += 1
    
    # Check for bullet points
    bullet_points = len(re.findall(r'[•\-*]\s', text))
    bullet_score = min(bullet_points / 10, 1.0)  # Max 1 point for good bullet usage
    
    # Check for quantified achievements
    quantified = len(re.findall(r'\d+%|\d+\s*(?:year|years|month|months)|increased|reduced|improved', text.lower()))
    quantified_score = min(quantified / 5, 1.0)  # Max 1 point for quantified achievements
    
    structure_score = (found_sections / len(sections) * 0.4) + (bullet_score * 0.3) + (quantified_score * 0.3)
    return round(structure_score * 100, 2)  # Convert to 0-100 scale

def call_deepseek_api(prompt, max_tokens=800, temperature=0.1, timeout=60, model_override=None, retry_count=0):
    """Call DeepSeek API with optimized settings"""
    if not DEEPSEEK_API_KEY:
        print(f"❌ No DeepSeek API key configured")
        return {'error': 'no_api_key', 'status': 500}
    
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    model_to_use = model_override or DEEPSEEK_MODEL or DEFAULT_MODEL
    
    # Optimized payload for batch processing
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
        'top_p': 0.9,
        'stream': False,
        'stop': None
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                result = data['choices'][0]['message']['content']
                print(f"✅ DeepSeek API response in {response_time:.2f}s using {model_to_use}")
                return result
            else:
                print(f"❌ Unexpected DeepSeek API response format")
                return {'error': 'invalid_response', 'status': response.status_code}
        
        # Handle specific error codes
        if response.status_code == 429:
            print(f"❌ Rate limit exceeded for DeepSeek API")
            
            if retry_count < MAX_RETRIES:
                wait_time = RETRY_DELAY_BASE ** (retry_count + 1) + random.uniform(5, 10)
                print(f"⏳ Rate limited, retrying in {wait_time:.1f}s (attempt {retry_count + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                return call_deepseek_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1)
            return {'error': 'rate_limit', 'status': 429}
        
        elif response.status_code == 503:
            print(f"❌ Service unavailable for DeepSeek API")
            
            if retry_count < 2:
                wait_time = 15 + random.uniform(5, 10)
                print(f"⏳ Service unavailable, retrying in {wait_time:.1f}s")
                time.sleep(wait_time)
                return call_deepseek_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1)
            return {'error': 'service_unavailable', 'status': 503}
        
        else:
            print(f"❌ DeepSeek API Error {response.status_code}: {response.text[:100]}")
            return {'error': f'api_error_{response.status_code}', 'status': response.status_code}
            
    except requests.exceptions.Timeout:
        print(f"❌ DeepSeek API timeout after {timeout}s")
        
        if retry_count < 2:
            wait_time = 10 + random.uniform(5, 10)
            print(f"⏳ Timeout, retrying in {wait_time:.1f}s (attempt {retry_count + 1}/3)")
            time.sleep(wait_time)
            return call_deepseek_api(prompt, max_tokens, temperature, timeout, model_override, retry_count + 1)
        return {'error': 'timeout', 'status': 408}
    
    except Exception as e:
        print(f"❌ DeepSeek API Exception: {str(e)}")
        return {'error': str(e), 'status': 500}

def warmup_deepseek_service():
    """Warm up DeepSeek service connection"""
    global warmup_complete
    
    if not DEEPSEEK_API_KEY:
        print("⚠️ Skipping DeepSeek warm-up: No API key configured")
        return False
    
    try:
        model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
        print(f"🔥 Warming up DeepSeek connection...")
        print(f"📊 Using model: {model_to_use}")
        
        start_time = time.time()
        
        response = call_deepseek_api(
            prompt="Hello, are you ready? Respond with just 'ready'.",
            max_tokens=10,
            temperature=0.1,
            timeout=15
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            print(f"  ⚠️ DeepSeek warm-up failed: {error_type}")
            return False
        elif response and 'ready' in response.lower():
            elapsed = time.time() - start_time
            print(f"✅ DeepSeek warmed up in {elapsed:.2f}s")
            warmup_complete = True
            return True
        else:
            print(f"  ⚠️ DeepSeek warm-up failed: Unexpected response")
            return False
        
    except Exception as e:
        print(f"⚠️ Warm-up attempt failed: {str(e)}")
        threading.Timer(30.0, warmup_deepseek_service).start()
        return False

def keep_service_warm():
    """Periodically send requests to keep DeepSeek service responsive"""
    global service_running
    
    while service_running:
        try:
            time.sleep(180)  # Check every 3 minutes
            
            if DEEPSEEK_API_KEY and warmup_complete:
                print(f"♨️ Keeping DeepSeek warm...")
                
                try:
                    response = call_deepseek_api(
                        prompt="Ping - just say 'pong'",
                        max_tokens=5,
                        timeout=20
                    )
                    if response and 'pong' in str(response).lower():
                        print(f"✅ DeepSeek keep-alive successful")
                    else:
                        print(f"⚠️ DeepSeek keep-alive got unexpected response")
                except Exception as e:
                    print(f"⚠️ DeepSeek keep-alive failed: {str(e)}")
                    
        except Exception as e:
            print(f"⚠️ Keep-warm thread error: {str(e)}")
            time.sleep(180)

# Text extraction functions
def extract_text_from_pdf(file_path):
    """Extract text from PDF file with error handling"""
    try:
        text = ""
        max_attempts = 2
        
        for attempt in range(max_attempts):
            try:
                reader = PdfReader(file_path)
                text = ""
                
                for page_num, page in enumerate(reader.pages[:4]):
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
                                text = ' '.join(words[:600])
                    except:
                        text = "Error: Could not extract text from PDF file"
        
        if not text.strip():
            return "Error: PDF appears to be empty or text could not be extracted"
        
        if len(text) > 2500:
            text = text[:2500] + "\n[Text truncated for optimal processing...]"
            
        return text
    except Exception as e:
        print(f"❌ PDF Error: {traceback.format_exc()}")
        return f"Error reading PDF: {str(e)[:100]}"

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs[:40] if paragraph.text.strip()])
        
        if not text.strip():
            return "Error: Document appears to be empty"
        
        if len(text) > 2500:
            text = text[:2500] + "\n[Text truncated for optimal processing...]"
            
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
                
                if len(text) > 2500:
                    text = text[:2500] + "\n[Text truncated for optimal processing...]"
                    
                return text
            except UnicodeDecodeError:
                continue
                
        return "Error: Could not decode text file with common encodings"
        
    except Exception as e:
        print(f"❌ TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

def analyze_ats_score_with_ai(resume_text, job_description, filename=None):
    """Enhanced ATS scoring with weighted evaluation"""
    
    # Extract domain information
    domains = extract_domain_specific_keywords(resume_text)
    primary_domain = "General"
    if 'VLSI' in domains:
        primary_domain = "VLSI"
    elif 'CS' in domains:
        primary_domain = "CS/Software"
    
    # Analyze resume structure
    structure_score = analyze_resume_structure(resume_text)
    
    # Enhanced prompt for comprehensive ATS evaluation
    prompt = f"""You are an expert ATS (Applicant Tracking System) analyst. Analyze this resume against the job description and provide a detailed, realistic ATS score out of 100.

JOB DESCRIPTION:
{job_description[:1000]}

RESUME (truncated):
{resume_text[:1500]}

RESUME STRUCTURE SCORE (0-100): {structure_score}
PRIMARY DOMAIN DETECTED: {primary_domain}

IMPORTANT: Be strict and realistic. Real ATS systems are critical and don't give high scores easily.
Perfect scores (90+) should only be given for exceptional, near-perfect matches.

EVALUATE THESE 5 DIMENSIONS WITH WEIGHTS:

1. SKILLS MATCH (Weight: 30/100)
- Focus on REQUIRED skills from job description
- Score based on evidence: mention + context (projects, responsibilities) = high score
- Mention without evidence = low score
- Partial/indirect usage = partial points
- Ignore "nice-to-have" or optional skills for this category
- For {primary_domain} roles, pay special attention to domain-specific skills

2. EXPERIENCE RELEVANCE (Weight: 25/100)
- How relevant is the candidate's experience to THIS specific role?
- Consider years of experience ONLY if relevant
- Seniority mismatch (junior for senior role, or vice versa) reduces score
- Domain-specific experience ({primary_domain}) gets bonus points
- Career progression matters

3. ROLE AND DOMAIN ALIGNMENT (Weight: 20/100)
- Compare past roles, responsibilities, projects with target role
- Direct domain alignment ({primary_domain}) scores highest
- Transferable skills from other domains score moderately
- Complete career switch with no related experience scores low

4. PROJECTS AND PRACTICAL IMPACT (Weight: 15/100)
- Hands-on projects with clear outcomes score high
- Ownership, complexity, and impact matter
- Tool-only mentions or vague descriptions score low
- Quantified achievements (improved X by Y%, reduced time/cost by Z) score bonus

5. RESUME QUALITY (Weight: 10/100)
- Clarity, structure, specificity
- Action verbs, quantified results
- Professional formatting
- Avoid vague descriptions, repetition
- Base score: {structure_score}/100 (already calculated)

CALCULATION INSTRUCTIONS:
1. Score each category out of its weight (e.g., Skills: 27/30 = 90% of category weight)
2. Sum all category scores for final ATS score (0-100)
3. Be DISTINCTIVE: Spread scores across range (0-100). Don't cluster around 70-80.
4. For {primary_domain} roles: Be extra strict with domain expertise.

OUTPUT FORMAT (JSON only):
{{
    "ats_score": 78,
    "score_breakdown": {{
        "skills_match": {{
            "score": 27,
            "max_score": 30,
            "explanation": "Detailed explanation of skills evaluation"
        }},
        "experience_relevance": {{
            "score": 20,
            "max_score": 25,
            "explanation": "Detailed explanation of experience evaluation"
        }},
        "role_alignment": {{
            "score": 16,
            "max_score": 20,
            "explanation": "Detailed explanation of role alignment"
        }},
        "projects_impact": {{
            "score": 12,
            "max_score": 15,
            "explanation": "Detailed explanation of projects evaluation"
        }},
        "resume_quality": {{
            "score": 8,
            "max_score": 10,
            "explanation": "Based on structure analysis"
        }}
    }},
    "primary_domain": "{primary_domain}",
    "overall_feedback": "Comprehensive feedback on overall match",
    "strengths": ["Strength 1", "Strength 2", "Strength 3"],
    "improvement_areas": ["Area 1", "Area 2", "Area 3"],
    "recommendation": "Strong Match / Consider / Needs Improvement / Reject",
    "seniority_assessment": "Junior / Mid-level / Senior / Lead",
    "domain_expertise_level": "Beginner / Intermediate / Advanced / Expert"
}}"""

    try:
        model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
        print(f"⚡ Sending to DeepSeek API for enhanced ATS scoring ({model_to_use})...")
        start_time = time.time()
        
        response = call_deepseek_api(
            prompt=prompt,
            max_tokens=1200,
            temperature=0.1,
            timeout=45
        )
        
        if isinstance(response, dict) and 'error' in response:
            print(f"❌ DeepSeek API error for ATS scoring: {response.get('error')}")
            return generate_fallback_ats_analysis(structure_score, primary_domain)
        
        elapsed_time = time.time() - start_time
        print(f"✅ Enhanced ATS scoring completed in {elapsed_time:.2f} seconds")
        
        result_text = response.strip()
        
        # Try to extract JSON
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = result_text[json_start:json_end]
        else:
            json_str = result_text
        
        json_str = json_str.replace('```json', '').replace('```', '').strip()
        
        try:
            ats_analysis = json.loads(json_str)
            
            # Validate and adjust scores
            total_score = 0
            for category in ['skills_match', 'experience_relevance', 'role_alignment', 'projects_impact', 'resume_quality']:
                if category in ats_analysis['score_breakdown']:
                    cat_data = ats_analysis['score_breakdown'][category]
                    # Ensure score doesn't exceed max
                    cat_data['score'] = min(cat_data['score'], cat_data['max_score'])
                    total_score += cat_data['score']
            
            # Ensure total score is realistic
            ats_analysis['ats_score'] = min(max(total_score, 0), 100)
            
            print(f"✅ Enhanced ATS analysis: Score {ats_analysis['ats_score']}/100 for {primary_domain}")
            
            return ats_analysis
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error in ATS scoring: {e}")
            print(f"Response was: {result_text[:200]}")
            return generate_fallback_ats_analysis(structure_score, primary_domain)
        
    except Exception as e:
        print(f"❌ Enhanced ATS analysis error: {str(e)}")
        return generate_fallback_ats_analysis(structure_score, primary_domain)

def generate_fallback_ats_analysis(structure_score, domain):
    """Generate fallback ATS analysis"""
    base_score = structure_score * 0.1  # Resume quality contributes 10%
    
    return {
        "ats_score": min(round(base_score + 40, 1), 85),  # Cap at 85 for fallback
        "score_breakdown": {
            "skills_match": {
                "score": round(base_score * 3, 1),
                "max_score": 30,
                "explanation": "Basic keyword matching (fallback mode)"
            },
            "experience_relevance": {
                "score": round(base_score * 2.5, 1),
                "max_score": 25,
                "explanation": "Limited experience analysis (fallback mode)"
            },
            "role_alignment": {
                "score": round(base_score * 2, 1),
                "max_score": 20,
                "explanation": "Basic role comparison (fallback mode)"
            },
            "projects_impact": {
                "score": round(base_score * 1.5, 1),
                "max_score": 15,
                "explanation": "Project analysis limited (fallback mode)"
            },
            "resume_quality": {
                "score": round(structure_score * 0.1, 1),
                "max_score": 10,
                "explanation": f"Structure score: {structure_score}/100"
            }
        },
        "primary_domain": domain,
        "overall_feedback": "Enhanced ATS analysis temporarily unavailable. Using fallback scoring.",
        "strengths": ["Resume processed successfully", f"{domain} domain detected"],
        "improvement_areas": ["Complete ATS analysis pending", "Try single file analysis for full evaluation"],
        "recommendation": "Needs Full ATS Analysis",
        "seniority_assessment": "To be determined",
        "domain_expertise_level": "To be determined"
    }

def analyze_resume_with_ai(resume_text, job_description, filename=None, analysis_id=None):
    """Use DeepSeek API to analyze resume against job description with enhanced ATS scoring"""
    
    if not DEEPSEEK_API_KEY:
        print(f"❌ No DeepSeek API key configured.")
        return generate_fallback_analysis(filename, "No API key available")
    
    # Optimize text length
    resume_text = resume_text[:2000]
    job_description = job_description[:1000]
    
    # Check cache for consistent scoring
    resume_hash = calculate_resume_hash(resume_text, job_description)
    cached_score = get_cached_score(resume_hash)
    
    # Get enhanced ATS scoring
    ats_analysis = analyze_ats_score_with_ai(resume_text, job_description, filename)
    
    # Extract domain keywords
    domains = extract_domain_specific_keywords(resume_text)
    primary_domain = "General"
    if 'VLSI' in domains:
        primary_domain = "VLSI"
    elif 'CS' in domains:
        primary_domain = "CS/Software"
    
    # Enhanced prompt for detailed analysis
    prompt = f"""Analyze this resume against the job description. Provide detailed, actionable insights.

JOB DESCRIPTION:
{job_description}

RESUME (truncated):
{resume_text}

ENHANCED ATS SCORE: {ats_analysis['ats_score']}/100
PRIMARY DOMAIN: {primary_domain}
SENIORITY: {ats_analysis.get('seniority_assessment', 'To be determined')}
DOMAIN EXPERTISE: {ats_analysis.get('domain_expertise_level', 'To be determined')}

Provide analysis in this JSON format only:
{{
    "candidate_name": "Extracted name or filename",
    "skills_matched": ["skill1 with context", "skill2 with context"],
    "skills_missing": ["required_skill1", "required_skill2"],
    "experience_summary": "Detailed 2-3 sentence summary of relevant experience",
    "education_summary": "Detailed education background summary",
    "overall_score": {ats_analysis['ats_score']},
    "recommendation": "{ats_analysis['recommendation']}",
    "key_strengths": ["Specific strength 1", "Specific strength 2", "Specific strength 3"],
    "areas_for_improvement": ["Specific area 1", "Specific area 2"],
    "ats_score_breakdown": {json.dumps(ats_analysis['score_breakdown'])},
    "primary_domain": "{primary_domain}",
    "seniority_level": "{ats_analysis.get('seniority_assessment', 'To be determined')}",
    "domain_expertise": "{ats_analysis.get('domain_expertise_level', 'To be determined')}",
    "overall_feedback": "{ats_analysis['overall_feedback']}",
    "strengths": {json.dumps(ats_analysis['strengths'])},
    "improvement_areas": {json.dumps(ats_analysis['improvement_areas'])}
}}"""

    try:
        model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
        print(f"⚡ Sending to DeepSeek API for detailed analysis ({model_to_use})...")
        start_time = time.time()
        
        response = call_deepseek_api(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.1,
            timeout=40
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            print(f"❌ DeepSeek API error: {error_type}")
            return generate_enhanced_fallback_analysis(filename, ats_analysis, primary_domain)
        
        elapsed_time = time.time() - start_time
        print(f"✅ Detailed analysis completed in {elapsed_time:.2f} seconds")
        
        result_text = response.strip()
        
        # Try to extract JSON
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = result_text[json_start:json_end]
        else:
            json_str = result_text
        
        json_str = json_str.replace('```json', '').replace('```', '').strip()
        
        try:
            analysis = json.loads(json_str)
            print(f"✅ Successfully parsed detailed analysis")
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            return generate_enhanced_fallback_analysis(filename, ats_analysis, primary_domain)
        
        # Merge ATS analysis with detailed analysis
        analysis['ats_score'] = ats_analysis['ats_score']
        analysis['ats_score_breakdown'] = ats_analysis['score_breakdown']
        analysis['primary_domain'] = primary_domain
        analysis['seniority_level'] = ats_analysis.get('seniority_assessment', 'To be determined')
        analysis['domain_expertise'] = ats_analysis.get('domain_expertise_level', 'To be determined')
        
        # Extract name from filename if candidate_name is default
        if analysis['candidate_name'] in ['Extracted name or filename', 'Professional Candidate'] and filename:
            base_name = os.path.splitext(filename)[0]
            clean_name = base_name.replace('-', ' ').replace('_', ' ').title()
            if len(clean_name.split()) <= 4:
                analysis['candidate_name'] = clean_name
        
        # Add metadata
        analysis['ai_provider'] = "deepseek"
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['ai_model'] = model_to_use
        analysis['response_time'] = f"{elapsed_time:.2f}s"
        
        # Add analysis ID if provided
        if analysis_id:
            analysis['analysis_id'] = analysis_id
        
        # Calculate and add score distribution
        analysis['score_distribution'] = {
            'skills': ats_analysis['score_breakdown']['skills_match']['score'],
            'experience': ats_analysis['score_breakdown']['experience_relevance']['score'],
            'role_alignment': ats_analysis['score_breakdown']['role_alignment']['score'],
            'projects': ats_analysis['score_breakdown']['projects_impact']['score'],
            'resume_quality': ats_analysis['score_breakdown']['resume_quality']['score']
        }
        
        print(f"✅ Enhanced analysis completed: {analysis['candidate_name']} (ATS Score: {analysis['ats_score']}/100)")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Enhanced analysis error: {str(e)}")
        return generate_enhanced_fallback_analysis(filename, ats_analysis, primary_domain)

def generate_enhanced_fallback_analysis(filename, ats_analysis, domain):
    """Generate enhanced fallback analysis"""
    candidate_name = "Professional Candidate"
    
    if filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').replace('resume', '').replace('cv', '').strip()
        if clean_name:
            parts = clean_name.split()
            if len(parts) >= 2 and len(parts) <= 4:
                candidate_name = ' '.join(part.title() for part in parts)
    
    return {
        "candidate_name": candidate_name,
        "skills_matched": ["ATS scoring completed", f"{domain} domain detected"],
        "skills_missing": ["Complete skill analysis pending"],
        "experience_summary": f"Candidate profile analyzed with enhanced ATS scoring.",
        "education_summary": "Educational background requires detailed analysis.",
        "overall_score": ats_analysis['ats_score'],
        "ats_score": ats_analysis['ats_score'],
        "recommendation": ats_analysis['recommendation'],
        "key_strengths": ats_analysis['strengths'],
        "areas_for_improvement": ats_analysis['improvement_areas'],
        "ats_score_breakdown": ats_analysis['score_breakdown'],
        "primary_domain": domain,
        "seniority_level": ats_analysis.get('seniority_assessment', 'To be determined'),
        "domain_expertise": ats_analysis.get('domain_expertise_level', 'To be determined'),
        "overall_feedback": ats_analysis['overall_feedback'],
        "strengths": ats_analysis['strengths'],
        "improvement_areas": ats_analysis['improvement_areas'],
        "score_distribution": {
            'skills': ats_analysis['score_breakdown']['skills_match']['score'],
            'experience': ats_analysis['score_breakdown']['experience_relevance']['score'],
            'role_alignment': ats_analysis['score_breakdown']['role_alignment']['score'],
            'projects': ats_analysis['score_breakdown']['projects_impact']['score'],
            'resume_quality': ats_analysis['score_breakdown']['resume_quality']['score']
        },
        "ai_provider": "deepseek",
        "ai_status": "Enhanced ATS Mode",
        "ai_model": DEEPSEEK_MODEL or DEFAULT_MODEL,
    }

def validate_analysis(analysis, filename):
    """Validate analysis data and fill missing fields"""
    required_fields = {
        'candidate_name': 'Professional Candidate',
        'skills_matched': ['ATS analysis completed'],
        'skills_missing': ['Compare with job description'],
        'experience_summary': 'Candidate demonstrates relevant experience.',
        'education_summary': 'Candidate has appropriate qualifications.',
        'overall_score': 70,
        'ats_score': 70,
        'recommendation': 'Consider for Interview',
        'key_strengths': ['Strong skills', 'Good communication'],
        'areas_for_improvement': ['Could benefit from training']
    }
    
    for field, default_value in required_fields.items():
        if field not in analysis:
            analysis[field] = default_value
    
    # Ensure ATS score matches overall score
    if 'ats_score' not in analysis:
        analysis['ats_score'] = analysis.get('overall_score', 70)
    
    # Add default ATS breakdown if missing
    if 'ats_score_breakdown' not in analysis:
        analysis['ats_score_breakdown'] = {
            'skills_match': {'score': 21, 'max_score': 30, 'explanation': 'Default scoring'},
            'experience_relevance': {'score': 17.5, 'max_score': 25, 'explanation': 'Default scoring'},
            'role_alignment': {'score': 14, 'max_score': 20, 'explanation': 'Default scoring'},
            'projects_impact': {'score': 10.5, 'max_score': 15, 'explanation': 'Default scoring'},
            'resume_quality': {'score': 7, 'max_score': 10, 'explanation': 'Default scoring'}
        }
    
    if 'score_distribution' not in analysis:
        analysis['score_distribution'] = {
            'skills': 21,
            'experience': 17.5,
            'role_alignment': 14,
            'projects': 10.5,
            'resume_quality': 7
        }
    
    if 'primary_domain' not in analysis:
        analysis['primary_domain'] = 'General'
    
    if 'seniority_level' not in analysis:
        analysis['seniority_level'] = 'To be determined'
    
    if 'domain_expertise' not in analysis:
        analysis['domain_expertise'] = 'To be determined'
    
    return analysis

def generate_fallback_analysis(filename, reason, partial_success=False):
    """Generate a better fallback analysis based on filename"""
    candidate_name = "Professional Candidate"
    
    if filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').replace('resume', '').replace('cv', '').strip()
        if clean_name:
            parts = clean_name.split()
            if len(parts) >= 2 and len(parts) <= 4:
                candidate_name = ' '.join(part.title() for part in parts)
    
    # Extract domain from filename
    domain = "General"
    filename_lower = filename.lower() if filename else ""
    if any(keyword in filename_lower for keyword in ['vlsi', 'asic', 'fpga', 'verilog', 'vhdl']):
        domain = "VLSI"
    elif any(keyword in filename_lower for keyword in ['software', 'developer', 'python', 'java', 'web']):
        domain = "CS/Software"
    
    if partial_success:
        return {
            "candidate_name": candidate_name,
            "skills_matched": ["Partial ATS analysis completed", f"{domain} domain detected"],
            "skills_missing": ["Full AI analysis pending"],
            "experience_summary": f"Basic analysis completed. Full DeepSeek AI analysis was interrupted.",
            "education_summary": "Educational background requires full AI analysis.",
            "overall_score": 55,
            "ats_score": 55,
            "recommendation": "Needs Full ATS Analysis",
            "key_strengths": ["File processed successfully", "Ready for detailed ATS analysis"],
            "areas_for_improvement": ["Complete ATS analysis pending"],
            "ats_score_breakdown": {
                'skills_match': {'score': 16.5, 'max_score': 30, 'explanation': 'Partial analysis'},
                'experience_relevance': {'score': 13.75, 'max_score': 25, 'explanation': 'Partial analysis'},
                'role_alignment': {'score': 11, 'max_score': 20, 'explanation': 'Partial analysis'},
                'projects_impact': {'score': 8.25, 'max_score': 15, 'explanation': 'Partial analysis'},
                'resume_quality': {'score': 5.5, 'max_score': 10, 'explanation': 'Partial analysis'}
            },
            "primary_domain": domain,
            "seniority_level": "To be determined",
            "domain_expertise": "To be determined",
            "score_distribution": {
                'skills': 16.5,
                'experience': 13.75,
                'role_alignment': 11,
                'projects': 8.25,
                'resume_quality': 5.5
            },
            "ai_provider": "deepseek",
            "ai_status": "Partial ATS Mode",
            "ai_model": DEEPSEEK_MODEL or DEFAULT_MODEL,
        }
    else:
        return {
            "candidate_name": candidate_name,
            "skills_matched": ["ATS service is initializing", "Please try again in a moment"],
            "skills_missing": ["Detailed ATS analysis coming soon"],
            "experience_summary": f"The enhanced ATS analysis service is currently warming up.",
            "education_summary": f"Educational background analysis will be available once the service is ready.",
            "overall_score": 50,
            "ats_score": 50,
            "recommendation": "Service Warming Up - Please Retry",
            "key_strengths": ["Enhanced ATS scoring once ready", "Accurate domain detection"],
            "areas_for_improvement": ["Please wait for ATS model to load"],
            "ats_score_breakdown": {
                'skills_match': {'score': 15, 'max_score': 30, 'explanation': 'Service warming up'},
                'experience_relevance': {'score': 12.5, 'max_score': 25, 'explanation': 'Service warming up'},
                'role_alignment': {'score': 10, 'max_score': 20, 'explanation': 'Service warming up'},
                'projects_impact': {'score': 7.5, 'max_score': 15, 'explanation': 'Service warming up'},
                'resume_quality': {'score': 5, 'max_score': 10, 'explanation': 'Service warming up'}
            },
            "primary_domain": domain,
            "seniority_level": "To be determined",
            "domain_expertise": "To be determined",
            "score_distribution": {
                'skills': 15,
                'experience': 12.5,
                'role_alignment': 10,
                'projects': 7.5,
                'resume_quality': 5
            },
            "ai_provider": "deepseek",
            "ai_status": "Warming up",
            "ai_model": DEEPSEEK_MODEL or DEFAULT_MODEL,
        }

def process_single_resume(args):
    """Process a single resume with intelligent error handling"""
    resume_file, job_description, index, total, batch_id = args
    
    try:
        print(f"📄 Processing resume {index + 1}/{total}: {resume_file.filename}")
        
        # Add delay based on index to avoid overwhelming API
        if index > 0:
            delay = 0.5 + (index % 3) * 0.3
            print(f"⏳ Adding {delay:.1f}s delay before processing resume {index + 1}...")
            time.sleep(delay)
        
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
        
        # Analyze with enhanced ATS scoring
        analysis_id = f"{batch_id}_resume_{index}"
        analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id)
        
        # Add file info
        analysis['filename'] = resume_file.filename
        analysis['original_filename'] = resume_file.filename
        
        # Get file size
        resume_file.seek(0, 2)
        file_size = resume_file.tell()
        resume_file.seek(0)
        analysis['file_size'] = f"{(file_size / 1024):.1f}KB"
        
        # Add metadata
        analysis['analysis_id'] = analysis_id
        analysis['processing_order'] = index + 1
        
        # Create individual Excel report
        try:
            if index < MAX_INDIVIDUAL_REPORTS:
                excel_filename = f"individual_{analysis_id}.xlsx"
                excel_path = create_excel_report(analysis, excel_filename)
                analysis['individual_excel_filename'] = os.path.basename(excel_path)
            else:
                analysis['individual_excel_filename'] = None
        except Exception as e:
            print(f"⚠️ Failed to create individual report: {str(e)}")
            analysis['individual_excel_filename'] = None
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        
        print(f"✅ Enhanced ATS analysis completed: {analysis.get('candidate_name')} - ATS Score: {analysis.get('ats_score', analysis.get('overall_score', 0))}/100")
        
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
    
    warmup_status = "✅ Ready" if warmup_complete else "🔥 Warming up..."
    model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enhanced ATS Resume Analyzer API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; padding: 0; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .ready { background: #d4edda; color: #155724; }
            .warming { background: #fff3cd; color: #856404; }
            .endpoint { background: #f8f9fa; padding: 10px; margin: 10px 0; border-left: 4px solid #007bff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Enhanced ATS Resume Analyzer API</h1>
            <p>AI-powered resume analysis with enhanced ATS scoring using DeepSeek API</p>
            
            <div class="status ''' + ('ready' if warmup_complete else 'warming') + '''">
                <strong>Status:</strong> ''' + warmup_status + '''
            </div>
            
            <p><strong>Model:</strong> ''' + model_to_use + '''</p>
            <p><strong>API Provider:</strong> DeepSeek</p>
            <p><strong>ATS Scoring:</strong> Enhanced weighted evaluation</p>
            <p><strong>Max Batch Size:</strong> ''' + str(MAX_BATCH_SIZE) + ''' resumes</p>
            <p><strong>Processing:</strong> Sequential with delays</p>
            <p><strong>Last Activity:</strong> ''' + str(inactive_minutes) + ''' minutes ago</p>
            
            <h2>📡 Endpoints</h2>
            <div class="endpoint">
                <strong>POST /analyze</strong> - Analyze single resume with enhanced ATS scoring
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
            
            <h2>🎯 Enhanced ATS Features</h2>
            <ul>
                <li>Weighted scoring across 5 dimensions</li>
                <li>Domain-specific evaluation (VLSI, CS)</li>
                <li>Strict and realistic scoring</li>
                <li>Seniority assessment</li>
                <li>Detailed score breakdown</li>
            </ul>
        </div>
    </body>
    </html>
    '''

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Main endpoint to analyze single resume with enhanced ATS scoring"""
    update_activity()
    
    try:
        print("\n" + "="*50)
        print("📥 New enhanced ATS analysis request received")
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
        if not DEEPSEEK_API_KEY:
            print("❌ No DeepSeek API key configured")
            return jsonify({'error': 'DeepSeek API not configured'}), 500
        
        # Analyze with enhanced ATS scoring
        model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
        print(f"⚡ Starting enhanced ATS analysis ({model_to_use})...")
        ai_start = time.time()
        
        analysis_id = f"single_{timestamp}"
        analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id)
        ai_time = time.time() - ai_start
        
        print(f"✅ Enhanced ATS analysis completed in {ai_time:.2f}s")
        
        # Create enhanced Excel report
        print("📊 Creating enhanced Excel report with ATS breakdown...")
        excel_start = time.time()
        excel_filename = f"enhanced_ats_analysis_{analysis_id}.xlsx"
        excel_path = create_excel_report(analysis, excel_filename)
        excel_time = time.time() - excel_start
        print(f"✅ Enhanced Excel report created in {excel_time:.2f}s: {excel_path}")
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Return enhanced analysis
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['ai_model'] = model_to_use
        analysis['ai_provider'] = "deepseek"
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['response_time'] = f"{ai_time:.2f}s"
        analysis['analysis_id'] = analysis_id
        
        total_time = time.time() - start_time
        print(f"✅ Enhanced ATS request completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/analyze-batch', methods=['POST'])
def analyze_resume_batch():
    """Analyze multiple resumes against a single job description with staggered processing"""
    update_activity()
    
    try:
        print("\n" + "="*50)
        print("📦 New enhanced ATS batch analysis request received")
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
        
        if len(resume_files) > MAX_BATCH_SIZE:
            print(f"❌ Too many files: {len(resume_files)} (max: {MAX_BATCH_SIZE})")
            return jsonify({'error': f'Maximum {MAX_BATCH_SIZE} resumes allowed per batch'}), 400
        
        # Check API configuration
        if not DEEPSEEK_API_KEY:
            print("❌ No DeepSeek API key configured")
            return jsonify({'error': 'DeepSeek API not configured'}), 500
        
        # Prepare batch analysis
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        
        # Process resumes sequentially with delays to avoid rate limits
        all_analyses = []
        errors = []
        
        print(f"🔄 Processing {len(resume_files)} resumes with enhanced ATS scoring...")
        
        for index, resume_file in enumerate(resume_files):
            if resume_file.filename == '':
                errors.append({
                    'filename': 'Empty file',
                    'error': 'File has no name',
                    'index': index
                })
                continue
            
            print(f"🔑 Processing resume {index + 1}/{len(resume_files)} with enhanced ATS scoring...")
            
            # Process the resume
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
            
            # Add delay between processing to avoid rate limits
            if index < len(resume_files) - 1:
                delay = 1.0 + random.uniform(0, 0.5)
                print(f"⏳ Adding {delay:.1f}s delay before next resume...")
                time.sleep(delay)
        
        print(f"\n📊 Enhanced ATS batch processing complete. Successful: {len(all_analyses)}, Failed: {len(errors)}")
        
        # Sort by ATS score
        all_analyses.sort(key=lambda x: x.get('ats_score', x.get('overall_score', 0)), reverse=True)
        
        # Add ranking
        for rank, analysis in enumerate(all_analyses, 1):
            analysis['rank'] = rank
        
        # Create batch Excel report
        batch_excel_path = None
        if all_analyses:
            try:
                print("📊 Creating enhanced batch Excel report with ATS breakdown...")
                excel_filename = f"enhanced_ats_batch_{batch_id}.xlsx"
                batch_excel_path = create_batch_excel_report(all_analyses, job_description, excel_filename)
                print(f"✅ Enhanced Excel report created: {batch_excel_path}")
            except Exception as e:
                print(f"❌ Failed to create enhanced Excel report: {str(e)}")
        
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
            'model_used': DEEPSEEK_MODEL or DEFAULT_MODEL,
            'ai_provider': "deepseek",
            'ai_status': "Warmed up" if warmup_complete else "Warming up",
            'processing_time': f"{time.time() - start_time:.2f}s",
            'job_description_preview': job_description[:200] + ("..." if len(job_description) > 200 else ""),
            'batch_size': len(resume_files),
            'max_batch_size': MAX_BATCH_SIZE,
            'processing_method': 'enhanced_ats_staggered',
            'scoring_method': 'weighted_ats_evaluation',
            'success_rate': f"{(len(all_analyses) / len(resume_files)) * 100:.1f}%" if resume_files else "0%"
        }
        
        print(f"✅ Enhanced ATS batch analysis completed in {time.time() - start_time:.2f}s")
        print("="*50 + "\n")
        
        return jsonify(batch_summary)
        
    except Exception as e:
        print(f"❌ Enhanced ATS batch analysis error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

def create_excel_report(analysis_data, filename="enhanced_ats_analysis_report.xlsx"):
    """Create an enhanced Excel report with ATS breakdown"""
    try:
        wb = Workbook()
        
        # Main Analysis Sheet
        ws = wb.active
        ws.title = "ATS Analysis"
        
        # Enhanced styles
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        subheader_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        subheader_font = Font(bold=True, color="FFFFFF", size=11)
        
        # Set column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 35
        ws.column_dimensions['C'].width = 40
        
        row = 1
        
        # Title
        ws.merge_cells(f'A{row}:C{row}')
        cell = ws[f'A{row}']
        cell.value = "🚀 ENHANCED ATS RESUME ANALYSIS REPORT"
        cell.font = Font(bold=True, size=16, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        row += 2
        
        # Candidate Information
        ws.merge_cells(f'A{row}:C{row}')
        cell = ws[f'A{row}']
        cell.value = "CANDIDATE INFORMATION"
        cell.font = subheader_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        info_fields = [
            ("Candidate Name", analysis_data.get('candidate_name', 'N/A')),
            ("Primary Domain", analysis_data.get('primary_domain', 'General')),
            ("Seniority Level", analysis_data.get('seniority_level', 'To be determined')),
            ("Domain Expertise", analysis_data.get('domain_expertise', 'To be determined')),
            ("Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("AI Model", analysis_data.get('ai_model', 'DeepSeek AI')),
            ("AI Provider", analysis_data.get('ai_provider', 'DeepSeek')),
            ("AI Status", analysis_data.get('ai_status', 'N/A')),
            ("Response Time", analysis_data.get('response_time', 'N/A')),
            ("Original Filename", analysis_data.get('original_filename', 'N/A'))
        ]
        
        for label, value in info_fields:
            ws[f'A{row}'] = label
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'B{row}'] = value
            if label == "Primary Domain":
                domain_cell = ws[f'B{row}']
                if value == "VLSI":
                    domain_cell.font = Font(color="FF6B6B", bold=True)
                elif value == "CS/Software":
                    domain_cell.font = Font(color="4ECDC4", bold=True)
            row += 1
        
        row += 1
        
        # ATS Score Summary
        ws.merge_cells(f'A{row}:C{row}')
        cell = ws[f'A{row}']
        cell.value = "🎯 ATS SCORE SUMMARY"
        cell.font = subheader_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        ats_score = analysis_data.get('ats_score', analysis_data.get('overall_score', 0))
        
        # Overall ATS Score
        ws.merge_cells(f'A{row}:C{row}')
        cell = ws[f'A{row}']
        cell.value = f"OVERALL ATS SCORE: {ats_score}/100"
        cell.font = Font(bold=True, size=14, color="1E3A8A")
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        # Recommendation
        ws.merge_cells(f'A{row}:C{row}')
        cell = ws[f'A{row}']
        cell.value = f"RECOMMENDATION: {analysis_data.get('recommendation', 'N/A')}"
        recommendation = analysis_data.get('recommendation', '').lower()
        if 'strong' in recommendation or 'recommended' in recommendation:
            cell.font = Font(bold=True, color="00B894")
        elif 'consider' in recommendation:
            cell.font = Font(bold=True, color="FDCB6E")
        else:
            cell.font = Font(bold=True, color="FF6B6B")
        cell.alignment = Alignment(horizontal='center')
        row += 2
        
        # Detailed ATS Breakdown
        ws.merge_cells(f'A{row}:C{row}')
        cell = ws[f'A{row}']
        cell.value = "📊 DETAILED ATS SCORE BREAKDOWN"
        cell.font = subheader_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        # ATS Breakdown Headers
        ws[f'A{row}'] = "Category"
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = "Score (Weight)"
        ws[f'B{row}'].font = Font(bold=True)
        ws[f'C{row}'] = "Explanation"
        ws[f'C{row}'].font = Font(bold=True)
        row += 1
        
        # ATS Categories
        ats_breakdown = analysis_data.get('ats_score_breakdown', {})
        categories = [
            ('Skills Match', 'skills_match', 30),
            ('Experience Relevance', 'experience_relevance', 25),
            ('Role Alignment', 'role_alignment', 20),
            ('Projects Impact', 'projects_impact', 15),
            ('Resume Quality', 'resume_quality', 10)
        ]
        
        for category_name, category_key, max_score in categories:
            if category_key in ats_breakdown:
                cat_data = ats_breakdown[category_key]
                score = cat_data.get('score', 0)
                explanation = cat_data.get('explanation', '')
                
                ws[f'A{row}'] = category_name
                ws[f'B{row}'] = f"{score}/{max_score}"
                ws[f'C{row}'] = explanation
                
                # Color code based on percentage
                percentage = (score / max_score) * 100
                if percentage >= 80:
                    ws[f'B{row}'].font = Font(color="00B894", bold=True)
                elif percentage >= 60:
                    ws[f'B{row}'].font = Font(color="FDCB6E", bold=True)
                else:
                    ws[f'B{row}'].font = Font(color="FF6B6B", bold=True)
                
                row += 1
        
        row += 1
        
        # Skills Analysis
        ws.merge_cells(f'A{row}:C{row}')
        cell = ws[f'A{row}']
        cell.value = "🛠️ SKILLS ANALYSIS"
        cell.font = subheader_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        # Skills Matched
        ws[f'A{row}'] = "Matched Skills"
        ws[f'A{row}'].font = Font(bold=True, color="00B894")
        row += 1
        
        skills_matched = analysis_data.get('skills_matched', [])
        if skills_matched:
            for i, skill in enumerate(skills_matched, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'B{row}'] = skill
                ws.row_dimensions[row].height = 20
                row += 1
        else:
            ws[f'A{row}'] = "No matching skills detected"
            row += 1
        
        row += 1
        
        # Skills Missing
        ws[f'A{row}'] = "Missing Skills"
        ws[f'A{row}'].font = Font(bold=True, color="FF6B6B")
        row += 1
        
        skills_missing = analysis_data.get('skills_missing', [])
        if skills_missing:
            for i, skill in enumerate(skills_missing, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'B{row}'] = skill
                ws.row_dimensions[row].height = 20
                row += 1
        else:
            ws[f'A{row}'] = "All required skills are present!"
            row += 1
        
        row += 1
        
        # Experience & Education Summary
        ws.merge_cells(f'A{row}:C{row}')
        cell = ws[f'A{row}']
        cell.value = "📈 PROFILE SUMMARY"
        cell.font = subheader_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        # Experience
        ws[f'A{row}'] = "Experience Summary"
        ws[f'A{row}'].font = Font(bold=True)
        row += 1
        
        ws.merge_cells(f'A{row}:C{row}')
        cell = ws[f'A{row}']
        cell.value = analysis_data.get('experience_summary', 'N/A')
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[row].height = 40
        row += 2
        
        # Education
        ws[f'A{row}'] = "Education Summary"
        ws[f'A{row}'].font = Font(bold=True)
        row += 1
        
        ws.merge_cells(f'A{row}:C{row}')
        cell = ws[f'A{row}']
        cell.value = analysis_data.get('education_summary', 'N/A')
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[row].height = 30
        row += 2
        
        # Strengths & Improvements
        ws.merge_cells(f'A{row}:C{row}')
        cell = ws[f'A{row}']
        cell.value = "💡 INSIGHTS & RECOMMENDATIONS"
        cell.font = subheader_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        # Key Strengths
        ws[f'A{row}'] = "Key Strengths"
        ws[f'A{row}'].font = Font(bold=True, color="00B894")
        row += 1
        
        key_strengths = analysis_data.get('key_strengths', [])
        if key_strengths:
            for i, strength in enumerate(key_strengths, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'B{row}'] = strength
                row += 1
        else:
            ws[f'A{row}'] = "No strengths identified"
            row += 1
        
        row += 1
        
        # Areas for Improvement
        ws[f'A{row}'] = "Areas for Improvement"
        ws[f'A{row}'].font = Font(bold=True, color="FF6B6B")
        row += 1
        
        areas_for_improvement = analysis_data.get('areas_for_improvement', [])
        if areas_for_improvement:
            for i, area in enumerate(areas_for_improvement, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'B{row}'] = area
                row += 1
        else:
            ws[f'A{row}'] = "No areas for improvement identified"
            row += 1
        
        row += 2
        
        # Overall Feedback
        ws.merge_cells(f'A{row}:C{row}')
        cell = ws[f'A{row}']
        cell.value = "📝 OVERALL FEEDBACK"
        cell.font = subheader_font
        cell.fill = subheader_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        ws.merge_cells(f'A{row}:C{row}')
        cell = ws[f'A{row}']
        cell.value = analysis_data.get('overall_feedback', analysis_data.get('recommendation', 'N/A'))
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[row].height = 40
        
        # Save the file
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📄 Enhanced ATS Excel report saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error creating enhanced Excel report: {str(e)}")
        # Return a fallback file path
        return os.path.join(REPORTS_FOLDER, f"enhanced_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

def create_batch_excel_report(analyses, job_description, filename="enhanced_ats_batch_analysis.xlsx"):
    """Create a comprehensive batch Excel report with enhanced ATS details"""
    try:
        wb = Workbook()
        
        # Summary Sheet
        ws_summary = wb.active
        ws_summary.title = "Batch Summary"
        
        # Enhanced styles
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        subheader_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        
        # Title
        ws_summary.merge_cells('A1:K1')
        title_cell = ws_summary['A1']
        title_cell.value = "🚀 ENHANCED ATS BATCH ANALYSIS REPORT"
        title_cell.font = Font(bold=True, size=16, color="FFFFFF")
        title_cell.fill = header_fill
        title_cell.alignment = Alignment(horizontal='center')
        
        # Summary Information
        ws_summary['A3'] = "Analysis Date"
        ws_summary['B3'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws_summary['A4'] = "Total Resumes"
        ws_summary['B4'] = len(analyses)
        ws_summary['A5'] = "AI Model"
        ws_summary['B5'] = DEEPSEEK_MODEL or DEFAULT_MODEL
        ws_summary['A6'] = "Processing Method"
        ws_summary['B6'] = "Enhanced ATS Staggered"
        ws_summary['A7'] = "Scoring Method"
        ws_summary['B7'] = "Weighted ATS Evaluation"
        ws_summary['A8'] = "Job Description"
        ws_summary['B8'] = job_description[:100] + ("..." if len(job_description) > 100 else "")
        
        # Candidates Ranking Table
        row = 10
        
        # Enhanced Headers
        headers = ["Rank", "Candidate", "ATS Score", "Domain", "Seniority", "Recommendation", 
                  "Skills Match", "Experience", "Role Align", "Projects", "Resume Quality"]
        
        for col, header in enumerate(headers, start=1):
            cell = ws_summary.cell(row=row, column=col)
            cell.value = header
            cell.font = header_font
            cell.fill = subheader_fill
            cell.alignment = Alignment(horizontal='center')
        
        row += 1
        
        for analysis in analyses:
            # Rank
            ws_summary.cell(row=row, column=1, value=analysis.get('rank', '-')).alignment = Alignment(horizontal='center')
            
            # Candidate Name
            candidate_cell = ws_summary.cell(row=row, column=2, value=analysis.get('candidate_name', 'Unknown'))
            
            # ATS Score with color coding
            ats_score = analysis.get('ats_score', analysis.get('overall_score', 0))
            score_cell = ws_summary.cell(row=row, column=3, value=ats_score)
            score_cell.alignment = Alignment(horizontal='center')
            if ats_score >= 80:
                score_cell.font = Font(color="00B894", bold=True)
            elif ats_score >= 60:
                score_cell.font = Font(color="FDCB6E", bold=True)
            else:
                score_cell.font = Font(color="FF6B6B", bold=True)
            
            # Domain
            domain_cell = ws_summary.cell(row=row, column=4, value=analysis.get('primary_domain', 'General'))
            domain_cell.alignment = Alignment(horizontal='center')
            if analysis.get('primary_domain') == 'VLSI':
                domain_cell.font = Font(color="FF6B6B", bold=True)
            elif analysis.get('primary_domain') == 'CS/Software':
                domain_cell.font = Font(color="4ECDC4", bold=True)
            
            # Seniority
            ws_summary.cell(row=row, column=5, value=analysis.get('seniority_level', 'N/A')).alignment = Alignment(horizontal='center')
            
            # Recommendation
            rec_cell = ws_summary.cell(row=row, column=6, value=analysis.get('recommendation', 'N/A'))
            rec_cell.alignment = Alignment(horizontal='center')
            rec_text = analysis.get('recommendation', '').lower()
            if 'strong' in rec_text or 'recommended' in rec_text:
                rec_cell.font = Font(color="00B894", bold=True)
            elif 'consider' in rec_text:
                rec_cell.font = Font(color="FDCB6E", bold=True)
            else:
                rec_cell.font = Font(color="FF6B6B", bold=True)
            
            # Detailed ATS Breakdown Scores
            breakdown = analysis.get('score_distribution', {})
            ws_summary.cell(row=row, column=7, value=breakdown.get('skills', 0)).alignment = Alignment(horizontal='center')
            ws_summary.cell(row=row, column=8, value=breakdown.get('experience', 0)).alignment = Alignment(horizontal='center')
            ws_summary.cell(row=row, column=9, value=breakdown.get('role_alignment', 0)).alignment = Alignment(horizontal='center')
            ws_summary.cell(row=row, column=10, value=breakdown.get('projects', 0)).alignment = Alignment(horizontal='center')
            ws_summary.cell(row=row, column=11, value=breakdown.get('resume_quality', 0)).alignment = Alignment(horizontal='center')
            
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
            adjusted_width = min(max_length + 2, 30)
            ws_summary.column_dimensions[column_letter].width = adjusted_width
        
        # Create individual candidate sheets
        for analysis in analyses[:5]:  # Limit to first 5 for performance
            try:
                candidate_name = analysis.get('candidate_name', f"Candidate_{analysis.get('rank', '0')}")
                # Clean sheet name
                sheet_name = re.sub(r'[^\w\s]', '', candidate_name)[:30]
                ws_candidate = wb.create_sheet(title=sheet_name)
                
                # Add candidate details
                ws_candidate['A1'] = f"Candidate: {candidate_name}"
                ws_candidate['A1'].font = Font(bold=True, size=14)
                ws_candidate['A2'] = f"ATS Score: {analysis.get('ats_score', 'N/A')}/100"
                ws_candidate['A2'].font = Font(bold=True, color="1E3A8A")
                ws_candidate['A3'] = f"Domain: {analysis.get('primary_domain', 'General')}"
                ws_candidate['A4'] = f"Seniority: {analysis.get('seniority_level', 'N/A')}"
                ws_candidate['A5'] = f"Recommendation: {analysis.get('recommendation', 'N/A')}"
                
            except Exception as e:
                print(f"⚠️ Failed to create sheet for candidate: {e}")
                continue
        
        # Save the file
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📊 Enhanced ATS batch Excel report saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error creating enhanced batch Excel report: {str(e)}")
        # Create a minimal file
        filepath = os.path.join(REPORTS_FOLDER, f"enhanced_batch_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb = Workbook()
        ws = wb.active
        ws['A1'] = "Enhanced ATS Batch Analysis Report"
        ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws['A3'] = f"Total Candidates: {len(analyses)}"
        wb.save(filepath)
        return filepath

@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    """Download the Excel report"""
    update_activity()
    
    try:
        print(f"📥 Download request for: {filename}")
        
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        
        # Check reports folder
        file_path = os.path.join(REPORTS_FOLDER, safe_filename)
        
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
        
        download_name = f"enhanced_ats_report_{analysis_id}.xlsx"
        
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
    """Force warm-up DeepSeek API"""
    update_activity()
    
    try:
        if not DEEPSEEK_API_KEY:
            return jsonify({
                'status': 'error',
                'message': 'DeepSeek API not configured',
                'warmup_complete': False
            })
        
        result = warmup_deepseek_service()
        
        return jsonify({
            'status': 'success' if result else 'error',
            'message': f'DeepSeek API warmed up successfully' if result else 'Warm-up failed',
            'warmup_complete': warmup_complete,
            'ai_provider': 'deepseek',
            'model': DEEPSEEK_MODEL or DEFAULT_MODEL,
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
    """Quick endpoint to check if DeepSeek API is responsive"""
    update_activity()
    
    try:
        if not DEEPSEEK_API_KEY:
            return jsonify({
                'available': False, 
                'reason': 'No DeepSeek API key configured',
                'warmup_complete': warmup_complete
            })
        
        if not warmup_complete:
            return jsonify({
                'available': False,
                'reason': 'DeepSeek API is warming up',
                'warmup_complete': False,
                'ai_provider': 'deepseek',
                'model': DEEPSEEK_MODEL or DEFAULT_MODEL
            })
        
        try:
            start_time = time.time()
            
            response = call_deepseek_api(
                prompt="Say 'ready'",
                max_tokens=10,
                timeout=15
            )
            
            response_time = time.time() - start_time
            
            if isinstance(response, dict) and 'error' in response:
                return jsonify({
                    'available': False,
                    'reason': response.get('error'),
                    'warmup_complete': warmup_complete
                })
            elif response and 'ready' in str(response).lower():
                return jsonify({
                    'available': True,
                    'response_time': f"{response_time:.2f}s",
                    'ai_provider': 'deepseek',
                    'model': DEEPSEEK_MODEL or DEFAULT_MODEL,
                    'warmup_complete': warmup_complete,
                    'max_batch_size': MAX_BATCH_SIZE,
                    'scoring_method': 'enhanced_weighted_ats'
                })
            else:
                return jsonify({
                    'available': False,
                    'reason': 'Unexpected response',
                    'warmup_complete': warmup_complete
                })
                
        except Exception as e:
            return jsonify({
                'available': False,
                'reason': str(e)[:100],
                'warmup_complete': warmup_complete
            })
            
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'available': False,
            'reason': error_msg[:100],
            'status': 'error',
            'ai_provider': 'deepseek',
            'model': DEEPSEEK_MODEL or DEFAULT_MODEL,
            'warmup_complete': warmup_complete
        })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    update_activity()
    
    model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'enhanced-ats-resume-analyzer',
        'ai_provider': 'deepseek',
        'ai_warmup': warmup_complete,
        'model': model_to_use,
        'inactive_minutes': int((datetime.now() - last_activity_time).total_seconds() / 60),
        'keep_alive_active': True,
        'max_batch_size': MAX_BATCH_SIZE,
        'scoring_method': 'enhanced_weighted_ats',
        'features': ['domain_detection', 'seniority_assessment', 'detailed_breakdown']
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
    
    return jsonify({
        'status': 'Service is running', 
        'timestamp': datetime.now().isoformat(),
        'ai_provider': 'deepseek',
        'ai_provider_configured': bool(DEEPSEEK_API_KEY),
        'model': model_to_use,
        'ai_warmup_complete': warmup_complete,
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'reports_folder_exists': os.path.exists(REPORTS_FOLDER),
        'inactive_minutes': inactive_minutes,
        'version': '20.0.0',
        'features': ['enhanced_ats_scoring', 'domain_detection', 'weighted_evaluation', 'seniority_assessment'],
        'scoring_method': 'weighted_ats_evaluation',
        'ats_dimensions': {
            'skills_match': 30,
            'experience_relevance': 25,
            'role_alignment': 20,
            'projects_impact': 15,
            'resume_quality': 10
        },
        'configuration': {
            'max_batch_size': MAX_BATCH_SIZE,
            'max_concurrent_requests': MAX_CONCURRENT_REQUESTS,
            'max_retries': MAX_RETRIES,
            'max_individual_reports': MAX_INDIVIDUAL_REPORTS
        },
        'processing_method': 'enhanced_ats_staggered_sequential',
        'domain_support': ['VLSI', 'CS/Software', 'General']
    })

def cleanup_on_exit():
    """Cleanup function called on exit"""
    global service_running
    service_running = False
    print("\n🛑 Shutting down enhanced ATS service...")
    
    # Clean up temporary files
    try:
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        print("✅ Cleaned up temporary files")
    except:
        pass

# Register cleanup function
atexit.register(cleanup_on_exit)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Enhanced ATS Resume Analyzer Backend Starting...")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"⚡ AI Provider: DeepSeek")
    model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
    print(f"🤖 Model: {model_to_use}")
    print(f"🔑 API Key: {'Configured' if DEEPSEEK_API_KEY else 'Not configured'}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📁 Reports folder: {REPORTS_FOLDER}")
    print(f"🎯 Enhanced ATS Scoring: Enabled")
    print(f"   • Skills Match: 30/100")
    print(f"   • Experience Relevance: 25/100")
    print(f"   • Role Alignment: 20/100")
    print(f"   • Projects Impact: 15/100")
    print(f"   • Resume Quality: 10/100")
    print(f"🌐 Domain Support: VLSI, CS/Software, General")
    print(f"👥 Seniority Assessment: Enabled")
    print(f"📊 Detailed Breakdown: Enabled")
    print(f"✅ Max Batch Size: {MAX_BATCH_SIZE} resumes")
    print(f"✅ Enhanced Excel Reports: Enabled")
    print("="*50 + "\n")
    
    if not DEEPSEEK_API_KEY:
        print("⚠️  WARNING: No DeepSeek API key found!")
        print("Please set DEEPSEEK_API_KEY in Render environment variables")
    
    # Enable garbage collection
    gc.enable()
    
    # Start warm-up in background
    if DEEPSEEK_API_KEY:
        warmup_thread = threading.Thread(target=warmup_deepseek_service, daemon=True)
        warmup_thread.start()
        
        # Start keep-warm thread
        keep_warm_thread = threading.Thread(target=keep_service_warm, daemon=True)
        keep_warm_thread.start()
        
        print("✅ Enhanced ATS background threads started")
    
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode, threaded=True)
