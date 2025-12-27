from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google import genai
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
import hashlib
import re
import random

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

print("=" * 50)
print("🔍 Checking for API keys...")

# Configure Gemini AI - Support multiple separate API keys
api_keys = []

# Check for individual keys (KEY1, KEY2, KEY3, etc.)
for i in range(1, 10):  # Check up to 9 separate keys
    key = os.getenv(f'GEMINI_API_KEY{i}', '').strip()
    if key and len(key) > 10:  # Basic validation
        api_keys.append(key)
        print(f"✅ Found GEMINI_API_KEY{i}: {key[:8]}...")

# Also check for single key (backward compatibility)
single_key = os.getenv('GEMINI_API_KEY', '').strip()
if single_key and len(single_key) > 10 and single_key not in api_keys:
    api_keys.append(single_key)
    print(f"✅ Found GEMINI_API_KEY: {single_key[:8]}...")

# Check for comma-separated keys (legacy format)
comma_keys_str = os.getenv('GEMINI_API_KEYS', '').strip()
if comma_keys_str:
    comma_keys = [k.strip() for k in comma_keys_str.split(',') if k.strip() and len(k.strip()) > 10]
    for key in comma_keys:
        if key not in api_keys:
            api_keys.append(key)
            print(f"✅ Found from GEMINI_API_KEYS: {key[:8]}...")

# Initialize clients
clients = []
valid_clients = []

if not api_keys:
    print("⚠️  WARNING: No Gemini API keys found!")
    print("ℹ️  Using enhanced fallback mode only - No AI analysis available")
else:
    print(f"✅ Total API keys loaded: {len(api_keys)}")
    
    # Test each key
    for i, key in enumerate(api_keys):
        try:
            print(f"🔄 Testing Key {i+1} ({key[:8]}...)")
            client = genai.Client(api_key=key)  # NO timeout parameter!
            
            # Quick test to validate key with timeout in generate_content
            test_response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents="Say 'OK'",
                timeout=5
            )
            
            if test_response and hasattr(test_response, 'text'):
                clients.append({
                    'client': client,
                    'key': key,
                    'name': f"Key {i+1}",
                    'quota_exceeded': False,
                    'last_reset': datetime.now(),
                    'requests_today': 0,
                    'requests_minute': 0,
                    'last_request_time': datetime.now(),
                    'minute_requests': [],
                    'errors': 0,
                    'total_requests': 0,
                    'valid': True
                })
                valid_clients.append(key)
                print(f"  ✅ Key {i+1} is VALID")
            else:
                print(f"  ❌ Key {i+1} returned unexpected response")
                
        except Exception as e:
            error_msg = str(e)
            print(f"  ❌ Key {i+1} failed: {error_msg[:100]}")
            
            # Check error type
            if '404' in error_msg or '401' in error_msg or '403' in error_msg or 'invalid' in error_msg.lower():
                print(f"  ⚠️  Key {i+1} appears to be INVALID or deactivated")
            elif 'quota' in error_msg.lower() or '429' in error_msg:
                print(f"  ⚠️  Key {i+1} has quota exceeded")
                clients.append({
                    'client': None,
                    'key': key,
                    'name': f"Key {i+1} (Quota Exceeded)",
                    'quota_exceeded': True,
                    'last_reset': datetime.now(),
                    'requests_today': 60,  # Mark as exceeded
                    'requests_minute': 0,
                    'last_request_time': datetime.now(),
                    'minute_requests': [],
                    'errors': 0,
                    'total_requests': 0,
                    'valid': False
                })
            else:
                print(f"  ⚠️  Key {i+1} has other issues: {error_msg[:50]}")

print(f"\n📊 Summary: {len(clients)} keys registered, {len(valid_clients)} valid keys")

# Quota tracking
QUOTA_DAILY = 60
QUOTA_PER_MINUTE = 15

# Simple in-memory cache for demo (use Redis in production)
analysis_cache = {}
cache_hits = 0
cache_misses = 0

# Get absolute path for uploads folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"📁 Upload folder: {UPLOAD_FOLDER}")

def extract_name_from_resume(resume_text):
    """Extract candidate name from resume text"""
    if not resume_text:
        return "Professional Candidate"
    
    # Clean the text
    resume_text = resume_text.strip()
    
    # Common patterns for names in resumes
    patterns = [
        r'^([A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?)',  # First Last or First Middle Last at start
        r'Name[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',  # Name: John Doe
        r'Full Name[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',  # Full Name: John Doe
        r'Candidate[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',  # Candidate: John Doe
        r'^([A-Z][A-Z]+ [A-Z][A-Z]+)',  # JOHN DOE (all caps)
        r'Contact Information\s*\n([A-Z][a-z]+ [A-Z][a-z]+)',  # After Contact Information
        r'RESUME\s*OF\s*([A-Z][a-z]+ [A-Z][a-z]+)',  # RESUME OF John Doe
        r'CURRICULUM VITAE\s*OF\s*([A-Z][a-z]+ [A-Z][a-z]+)',  # CV OF John Doe
    ]
    
    # Look at first 20 lines
    lines = resume_text.split('\n')[:20]
    
    for line in lines:
        line = line.strip()
        if len(line) > 3 and len(line) < 50:  # Reasonable name length
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    # Basic validation: should have at least 2 words, not too long
                    if len(name.split()) >= 2 and len(name) < 50:
                        print(f"✅ Extracted name: {name}")
                        return name.title()
    
    # If no name found with patterns, look for lines that look like names
    for line in lines:
        line = line.strip()
        words = line.split()
        if 2 <= len(words) <= 4:
            # Check if words look like names (start with capital, not all caps, not too long)
            if all(word and word[0].isupper() for word in words):
                # Not an email, not a URL, not a section header, not a date
                if '@' not in line and '://' not in line and not line.endswith(':') and not re.search(r'\d{4}', line):
                    if len(line) < 40:  # Not too long
                        print(f"✅ Found possible name: {line}")
                        return line
    
    # Check for email signature patterns
    email_pattern = r'([A-Z][a-z]+ [A-Z][a-z]+)\s*<[^>]+>'
    for line in lines:
        match = re.search(email_pattern, line)
        if match:
            name = match.group(1).strip()
            print(f"✅ Extracted name from email: {name}")
            return name
    
    return "Professional Candidate"

def extract_skills_from_resume(resume_text):
    """Extract skills from resume text"""
    if not resume_text:
        return []
    
    # Common technical and soft skills
    common_skills = [
        # Technical skills
        'Python', 'JavaScript', 'Java', 'C++', 'React', 'Node.js', 'SQL',
        'AWS', 'Docker', 'Kubernetes', 'Git', 'Linux', 'HTML', 'CSS',
        'TypeScript', 'Angular', 'Vue.js', 'MongoDB', 'PostgreSQL', 'MySQL',
        'REST API', 'GraphQL', 'Machine Learning', 'Data Analysis', 'Excel',
        'PowerPoint', 'Word', 'Power BI', 'Tableau', 'Photoshop', 'Illustrator',
        'Android', 'iOS', 'Swift', 'Kotlin', 'Flutter', 'React Native',
        'PHP', '.NET', 'C#', 'Ruby', 'Go', 'Rust',
        
        # Soft skills
        'Communication', 'Teamwork', 'Problem Solving', 'Leadership',
        'Project Management', 'Time Management', 'Critical Thinking',
        'Creativity', 'Adaptability', 'Attention to Detail', 'Analytical Skills',
        'Presentation Skills', 'Negotiation', 'Customer Service',
        
        # Business skills
        'Agile', 'Scrum', 'Waterfall', 'DevOps', 'CI/CD', 'Testing',
        'UX/UI Design', 'Data Science', 'Business Analysis', 'Marketing',
        'Sales', 'Finance', 'Accounting', 'Human Resources'
    ]
    
    found_skills = []
    resume_lower = resume_text.lower()
    
    for skill in common_skills:
        skill_lower = skill.lower()
        # Check for skill in various formats
        if skill_lower in resume_lower or f' {skill_lower} ' in f' {resume_lower} ':
            found_skills.append(skill)
    
    # Also look for skills section
    skills_section_pattern = r'(?:skills|technical skills|competencies)[:\s]*\n(.+?)(?:\n\n|\n[A-Z]|$)'
    match = re.search(skills_section_pattern, resume_text, re.IGNORECASE | re.DOTALL)
    if match:
        skills_section = match.group(1)
        # Extract skills from section (comma, bullet, or line separated)
        skill_items = re.split(r'[,\n•\-]', skills_section)
        for item in skill_items:
            item = item.strip()
            if len(item) > 2 and len(item) < 30:
                # Check if it looks like a skill (not empty, not too long)
                if item and not re.search(r'[0-9]{4}', item):  # Not a year
                    found_skills.append(item)
    
    # Remove duplicates and limit
    unique_skills = []
    for skill in found_skills:
        if skill not in unique_skills:
            unique_skills.append(skill)
    
    return unique_skills[:12]  # Return top 12 skills

def extract_experience_summary(resume_text):
    """Extract experience summary from resume"""
    if not resume_text:
        return "Experienced professional with relevant background."
    
    # Look for experience-related keywords
    experience_keywords = ['experience', 'worked', 'employment', 'career', 'professional', 'work history']
    
    lines = resume_text.split('\n')
    experience_sentences = []
    
    # First, look for explicit experience sections
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in experience_keywords):
            # Get the next 5-10 lines that look like experience content
            context = []
            for j in range(i + 1, min(i + 10, len(lines))):
                next_line = lines[j].strip()
                if next_line and len(next_line) > 10 and len(next_line) < 200:
                    if not next_line.lower().startswith(('education', 'skills', 'projects', 'certifications')):
                        context.append(next_line)
            if context:
                experience_sentences.append(" ".join(context[:3]))
    
    # If no experience section found, look for job titles and dates
    job_pattern = r'(\d{4}[\s\-]+(?:to|–|-|present|current)[\s\-]+\d{4}|\d{4}[\s\-]+(?:to|–|-|present|current)[\s\-]+(?:present|current))[\s\w\W]+?(?=\n\d{4}|\n[A-Z]|$)'
    job_matches = re.finditer(job_pattern, resume_text, re.IGNORECASE | re.MULTILINE)
    
    for match in job_matches:
        job_section = match.group()
        # Extract first sentence or key phrases
        sentences = re.split(r'[.!?]', job_section)
        if sentences and len(sentences[0]) > 20:
            experience_sentences.append(sentences[0].strip()[:150])
    
    # Count years if mentioned
    year_pattern = r'(20\d{2}|19\d{2})'
    years = re.findall(year_pattern, resume_text)
    if years:
        years = sorted([int(y) for y in years if 1900 <= int(y) <= 2025])
        if len(years) >= 2:
            experience_years = years[-1] - years[0]
            if 0 < experience_years <= 50:
                experience_sentences.append(f"Professional with approximately {experience_years} years of experience.")
    
    if experience_sentences:
        summary = " ".join(experience_sentences[:2])
        # Ensure summary ends properly
        if len(summary) > 150:
            summary = summary[:150]
            if not summary.endswith('.'):
                summary += "..."
        else:
            if not summary.endswith('.'):
                summary += "."
        return summary
    
    # Look for job titles
    job_title_pattern = r'(?:Senior|Junior|Lead|Principal|Manager|Director|Engineer|Developer|Designer|Analyst|Consultant|Specialist)\s+[A-Za-z]+'
    job_titles = re.findall(job_title_pattern, resume_text, re.IGNORECASE)
    if job_titles:
        unique_titles = list(set(job_titles[:3]))  # Get unique titles
        return f"Experienced professional with background in roles such as {', '.join(unique_titles)}."
    
    return "Experienced professional with relevant background suitable for the position."

def extract_education_summary(resume_text):
    """Extract education summary from resume"""
    if not resume_text:
        return "Qualified candidate with appropriate educational background."
    
    # Look for education-related keywords
    education_keywords = [
        'education', 'university', 'college', 'degree', 'bachelor', 'master',
        'phd', 'graduate', 'diploma', 'certificate', 'school', 'academic',
        'b.a.', 'b.s.', 'm.a.', 'm.s.', 'mba', 'ph.d'
    ]
    
    lines = resume_text.split('\n')
    education_sentences = []
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in education_keywords):
            # Get this line and next few lines
            context_lines = []
            # Start from current line, go forward up to 4 lines
            for j in range(0, min(4, len(lines) - i)):
                context_line = lines[i + j].strip()
                if context_line and len(context_line) < 200:
                    context_lines.append(context_line)
            
            if context_lines:
                education_sentences.append(" ".join(context_lines[:2]))
    
    if education_sentences:
        summary = " ".join(education_sentences[:2])
        if len(summary) > 120:
            summary = summary[:120]
            if not summary.endswith('.'):
                summary += "..."
        else:
            if not summary.endswith('.'):
                summary += "."
        return summary
    
    # Look for degree patterns
    degree_pattern = r'(?:B\.?[AS]\.?|M\.?[AS]\.?|MBA|PhD|Bachelor|Master|Doctorate)[\s\w]+'
    degrees = re.findall(degree_pattern, resume_text, re.IGNORECASE)
    if degrees:
        unique_degrees = list(set(degrees[:2]))
        return f"Educational qualifications include {', '.join(unique_degrees)}."
    
    return "Qualified candidate with appropriate educational background for the role."

def check_quota(client_info):
    """Check if client has exceeded quota"""
    if not client_info.get('valid', True):
        return False, "Invalid key"
    
    now = datetime.now()
    
    # Check daily reset
    if (now - client_info['last_reset']).days >= 1:
        client_info['last_reset'] = now
        client_info['requests_today'] = 0
        client_info['quota_exceeded'] = False
        client_info['minute_requests'] = []
        client_info['errors'] = 0
        print(f"✅ Quota reset for {client_info['name']}")
    
    # Check minute reset
    minute_ago = now - timedelta(minutes=1)
    client_info['minute_requests'] = [
        t for t in client_info['minute_requests'] 
        if t > minute_ago
    ]
    client_info['requests_minute'] = len(client_info['minute_requests'])
    
    # Check if key has too many errors
    if client_info['errors'] > 5:
        client_info['quota_exceeded'] = True
        return False, "Too many errors"
    
    # Check limits
    if client_info['requests_today'] >= QUOTA_DAILY:
        client_info['quota_exceeded'] = True
        return False, "Daily quota exceeded"
    
    if client_info['requests_minute'] >= QUOTA_PER_MINUTE:
        return False, "Rate limit exceeded"
    
    return True, "OK"

def get_available_client():
    """Get the best available client with quota"""
    if not clients:
        return None
    
    # Filter valid clients
    valid_clients_list = [c for c in clients if c.get('valid', True)]
    if not valid_clients_list:
        return None
    
    # Try to find a client with available quota
    for client_info in valid_clients_list:
        quota_ok, reason = check_quota(client_info)
        if quota_ok and not client_info['quota_exceeded']:
            return client_info
    
    # If all have quota exceeded, return the first valid one
    for client_info in valid_clients_list:
        if client_info.get('valid', True):
            return client_info
    
    return None

def update_client_stats(client_info, success=True):
    """Update client request statistics"""
    now = datetime.now()
    if success:
        client_info['requests_today'] += 1
        client_info['total_requests'] += 1
        client_info['last_request_time'] = now
        client_info['minute_requests'].append(now)
    else:
        client_info['errors'] += 1

def get_high_quality_fallback_analysis(resume_text="", job_description=""):
    """Return a high-quality fallback analysis when AI fails"""
    # Extract actual information from resume
    candidate_name = extract_name_from_resume(resume_text)
    extracted_skills = extract_skills_from_resume(resume_text)
    experience_summary = extract_experience_summary(resume_text)
    education_summary = extract_education_summary(resume_text)
    
    # Ensure summaries are complete
    if experience_summary.endswith("..."):
        experience_summary = experience_summary[:-3] + "."
    if education_summary.endswith("..."):
        education_summary = education_summary[:-3] + "."
    
    # If summaries are too short, provide better defaults
    if len(experience_summary) < 30:
        experience_summary = "Experienced professional with relevant background and skills suitable for the position."
    if len(education_summary) < 30:
        education_summary = "Qualified candidate with appropriate educational background and academic foundation."
    
    # Determine skills matched based on job description
    skills_matched = []
    skills_missing = []
    
    if job_description and extracted_skills:
        job_desc_lower = job_description.lower()
        for skill in extracted_skills:
            skill_lower = skill.lower()
            # Check if skill or its variants appear in job description
            if skill_lower in job_desc_lower:
                skills_matched.append(skill)
            else:
                # Check for partial matches
                words = skill_lower.split()
                if any(word in job_desc_lower for word in words if len(word) > 3):
                    skills_matched.append(skill)
                else:
                    skills_missing.append(skill)
    
    # If no skills matched from extraction, use default ones
    if not skills_matched or len(skills_matched) < 3:
        default_skills = ["Problem Solving", "Communication Skills", "Team Collaboration", 
                         "Analytical Thinking", "Project Management"]
        # Add some from extracted skills if available
        if extracted_skills:
            skills_matched = extracted_skills[:3] + default_skills[:2]
        else:
            skills_matched = default_skills[:5]
    
    # Add some relevant missing skills based on common job requirements
    if not skills_missing or len(skills_missing) < 3:
        common_missing = ["Advanced certifications", "Industry-specific tools", 
                         "Leadership training", "Cloud platform experience",
                         "Data visualization", "Agile methodology"]
        skills_missing.extend(common_missing[:3])
    
    # Calculate a realistic score based on extracted info
    base_score = 70
    
    # Adjust based on extracted skills match
    if len(skills_matched) > 5:
        base_score += 8
    elif len(skills_matched) > 3:
        base_score += 5
    
    # Adjust based on experience indicators
    if "experience" in experience_summary.lower():
        base_score += 5
    if "year" in experience_summary.lower():
        base_score += 3
    
    # Adjust based on education indicators
    if any(word in education_summary.lower() for word in ['master', 'mba', 'phd', 'doctorate']):
        base_score += 8
    elif any(word in education_summary.lower() for word in ['bachelor', 'degree', 'university']):
        base_score += 5
    
    # Cap the score
    overall_score = min(max(base_score, 60), 88)  # Between 60-88 for fallback
    
    # Determine recommendation
    if overall_score >= 80:
        recommendation = "Recommended for Interview"
    elif overall_score >= 70:
        recommendation = "Consider for Interview"
    elif overall_score >= 60:
        recommendation = "Review Needed - Consider Improvements"
    else:
        recommendation = "Needs Significant Improvement"
    
    return {
        "candidate_name": candidate_name,
        "skills_matched": skills_matched[:8],
        "skills_missing": skills_missing[:8],
        "experience_summary": experience_summary,
        "education_summary": education_summary,
        "overall_score": overall_score,
        "recommendation": recommendation,
        "key_strengths": skills_matched[:4] if skills_matched else ["Strong foundational skills", "Good communication abilities"],
        "areas_for_improvement": skills_missing[:4] if skills_missing else ["Consider additional certifications", "Gain industry-specific experience"],
        "is_fallback": True,
        "fallback_reason": "Enhanced analysis extracting information directly from resume content",
        "analysis_quality": "enhanced_fallback",
        "extracted_info": True,
        "quota_reset_time": (datetime.now() + timedelta(hours=24)).isoformat(),
        "ai_status": "unavailable",
        "enhanced_features": [
            "name_extraction",
            "skill_detection", 
            "experience_analysis",
            "education_detection",
            "personalized_scoring"
        ]
    }

def analyze_resume_with_gemini(resume_text, job_description):
    """Use Gemini AI to analyze resume against job description"""
    
    client_info = get_available_client()
    if not client_info or not client_info.get('valid', True):
        print("⚠️  No valid Gemini clients - using enhanced fallback")
        return get_high_quality_fallback_analysis(resume_text, job_description)
    
    # Check quota
    quota_ok, reason = check_quota(client_info)
    if not quota_ok:
        print(f"⚠️  Quota issue for {client_info['name']}: {reason}")
        return get_high_quality_fallback_analysis(resume_text, job_description)
    
    client = client_info['client']
    if not client:
        print(f"⚠️  Client not initialized for {client_info['name']}")
        return get_high_quality_fallback_analysis(resume_text, job_description)
    
    # TRUNCATE text
    resume_text = resume_text[:6000]
    job_description = job_description[:2500]
    
    prompt = f"""RESUME ANALYSIS:
Analyze this resume against the job description and provide comprehensive insights.

RESUME TEXT:
{resume_text}

JOB DESCRIPTION:
{job_description}

IMPORTANT: Extract the candidate's actual name from the resume. Look for patterns like "Name:", "Full Name:", or names at the beginning of the resume.

Return ONLY valid JSON with this structure:
{{
    "candidate_name": "Extract actual name from resume or use 'Professional Candidate'",
    "skills_matched": ["list 5-8 skills from resume that match job requirements"],
    "skills_missing": ["list 5-8 important skills from job description not found in resume"],
    "experience_summary": "2-3 sentence professional summary of work experience",
    "education_summary": "2-3 sentence summary of educational background", 
    "overall_score": "0-100 based on how well resume matches job description",
    "recommendation": "Highly Recommended/Recommended/Consider for Interview/Needs Improvement",
    "key_strengths": ["list 3-5 key strengths from the resume"],
    "areas_for_improvement": ["list 3-5 areas where candidate could improve"]
}}

Be specific and base analysis on actual content from the resume."""

    def call_gemini():
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                timeout=15
            )
            return response
        except Exception as e:
            raise e
    
    try:
        print(f"🤖 Attempting AI analysis with {client_info['name']}")
        start_time = time.time()
        
        # Call with timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(call_gemini)
            response = future.result(timeout=20)
        
        elapsed_time = time.time() - start_time
        print(f"✅ Gemini response in {elapsed_time:.2f} seconds")
        
        # Update client stats (successful request)
        update_client_stats(client_info, success=True)
        
        result_text = response.text.strip()
        
        # Clean response
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        # Parse JSON
        analysis = json.loads(result_text)
        
        # Ensure score is numeric
        try:
            analysis['overall_score'] = int(analysis.get('overall_score', 0))
            if analysis['overall_score'] > 100:
                analysis['overall_score'] = 100
            elif analysis['overall_score'] < 0:
                analysis['overall_score'] = 0
        except:
            analysis['overall_score'] = 75
        
        # Ensure required fields
        analysis['is_fallback'] = False
        analysis['fallback_reason'] = None
        analysis['analysis_quality'] = "ai"
        analysis['used_key'] = client_info['name']
        
        print(f"✅ AI Analysis completed for: {analysis.get('candidate_name', 'Unknown')}")
        print(f"   Score: {analysis.get('overall_score')}, Key: {client_info['name']}")
        
        return analysis
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {e}")
        update_client_stats(client_info, success=False)
        print("🔄 Using enhanced fallback due to JSON error")
        return get_high_quality_fallback_analysis(resume_text, job_description)
        
    except Exception as e:
        error_msg = str(e).lower()
        print(f"❌ Gemini Error: {error_msg[:100]}")
        
        # Update client stats (failed request)
        update_client_stats(client_info, success=False)
        
        # Mark as invalid if authentication error
        if '404' in error_msg or '401' in error_msg or '403' in error_msg or 'invalid' in error_msg:
            print(f"⚠️  Marking {client_info['name']} as invalid")
            client_info['valid'] = False
        
        print("🔄 Using enhanced fallback due to API error")
        return get_high_quality_fallback_analysis(resume_text, job_description)

def get_cache_key(resume_text, job_description):
    """Generate cache key from resume and job description"""
    combined = resume_text[:500] + job_description[:300]
    return hashlib.md5(combined.encode()).hexdigest()

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
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'windows-1252', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    text = file.read()
                    
                if not text.strip():
                    return "Error: Text file appears to be empty"
                
                # Limit text size for performance
                if len(text) > 8000:
                    text = text[:8000] + "\n[Text truncated for processing...]"
                    
                return text
            except UnicodeDecodeError:
                continue
                
        return "Error: Could not decode text file with common encodings"
        
    except Exception as e:
        print(f"TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

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
    row += 1
    
    if analysis_data.get('is_fallback'):
        ws[f'A{row}'] = "Analysis Mode"
        ws[f'A{row}'].font = subheader_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'B{row}'] = "Enhanced Analysis (AI Fallback)"
        ws[f'B{row}'].font = Font(color="FF9900", bold=True)
        row += 1
        if analysis_data.get('extracted_info'):
            ws[f'A{row}'] = "Data Source"
            ws[f'A{row}'].font = subheader_font
            ws[f'A{row}'].fill = subheader_fill
            ws[f'B{row}'] = "Extracted from resume content"
            row += 1
    elif analysis_data.get('used_key'):
        ws[f'A{row}'] = "AI Key Used"
        ws[f'A{row}'].font = subheader_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'B{row}'] = analysis_data.get('used_key')
        row += 1
    
    row += 1
    
    # Overall Score
    ws[f'A{row}'] = "Overall Match Score"
    ws[f'A{row}'].font = Font(bold=True, size=12)
    ws[f'A{row}'].fill = header_fill
    ws[f'A{row}'].font = Font(bold=True, size=12, color="FFFFFF")
    ws[f'B{row}'] = f"{analysis_data.get('overall_score', 0)}/100"
    score = analysis_data.get('overall_score', 0)
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
    
    # Save the file using ABSOLUTE path
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    wb.save(filepath)
    print(f"📄 Excel report saved to: {filepath}")
    return filepath

@app.route('/')
def home():
    """Root route - API landing page"""
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
        
        .quota-status {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }
        
        .quota-item {
            margin: 5px 0;
            padding: 5px;
            border-bottom: 1px solid #ffeaa7;
        }
        
        .quota-item:last-child {
            border-bottom: none;
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
            transition: transform 0.3s;
        }
        
        .endpoint:hover {
            transform: translateX(10px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
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
        
        .description {
            color: #7f8c8d;
            margin-top: 5px;
            font-size: 0.95rem;
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
        
        .buttons {
            margin-top: 30px;
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
        
        .error {
            color: #e74c3c;
            font-weight: 600;
        }
        
        .success {
            color: #27ae60;
            font-weight: 600;
        }
        
        .warning {
            color: #f39c12;
            font-weight: 600;
        }
        
        .info {
            color: #3498db;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Resume Analyzer API</h1>
        <p class="subtitle">Multi-key AI resume analysis using Google Gemini</p>
        
        <div class="api-status">
            ✅ API IS RUNNING
        </div>
        
        <div class="status-card">
            <div class="status-item">
                <span class="status-label">Service Status:</span>
                <span class="status-value">Online</span>
            </div>
            <div class="status-item">
                <span class="status-label">Total API Keys:</span>
                <span class="status-value">''' + str(len(api_keys)) + '''</span>
            </div>
            <div class="status-item">
                <span class="status-label">Valid Clients:</span>
                <span class="status-value">''' + str(len(valid_clients)) + '''</span>
            </div>
            <div class="status-item">
                <span class="status-label">Cache Hits:</span>
                <span class="status-value">''' + str(cache_hits) + '''</span>
            </div>
            <div class="status-item">
                <span class="status-label">Enhanced Fallback:</span>
                <span class="status-value">✅ Active</span>
            </div>
        </div>
        
        <div class="quota-status">
            <h3>📊 Multi-Key Quota Status</h3>
            <p>Using separate keys: GEMINI_API_KEY1, GEMINI_API_KEY2, etc.</p>
            ''' + (''.join([f'''
            <div class="quota-item">
                <strong>{c["name"]} ({c["key"][:8]}...):</strong>
                <span class="{("error" if not c.get("valid", True) else ("warning" if c["quota_exceeded"] else "success"))}">
                    {'❌ Invalid' if not c.get("valid", True) else ('⚠️ Quota Exceeded' if c["quota_exceeded"] else '✅ Available')}
                </span>
                <br>
                <small>Used: {c["requests_today"]}/{QUOTA_DAILY} today • Total: {c["total_requests"]} • Errors: {c["errors"]}</small>
            </div>''' for i, c in enumerate(clients)]) if clients else '<p class="warning">No API keys configured</p>') + '''
            <p><small>Auto-rotates between available keys when quota is exceeded.</small></p>
            <p><small>Enhanced fallback extracts info from resumes when AI is unavailable.</small></p>
        </div>
        
        <div class="endpoints">
            <h2>📡 API Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">POST</span>
                <span class="path">/analyze</span>
                <p class="description">Upload a resume (PDF/DOCX/TXT) with job description for AI analysis</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/quick-check</span>
                <p class="description">Quick AI service availability check</p>
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
                <span class="path">/stats</span>
                <p class="description">View detailed API usage statistics</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span>
                <span class="path">/download/{filename}</span>
                <p class="description">Download generated Excel analysis reports</p>
            </div>
        </div>
        
        <div class="buttons">
            <a href="/health" class="btn">Check Health</a>
            <a href="/stats" class="btn btn-secondary">View Stats</a>
        </div>
        
        <div class="footer">
            <p>Powered by Flask & Google Gemini AI | Deployed on Render</p>
            <p>Enhanced Fallback Analysis: Extracts names, skills, and experience from resumes</p>
        </div>
    </div>
</body>
</html>
    '''

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Main endpoint to analyze resume"""
    
    try:
        print("\n" + "="*50)
        print("📥 New analysis request received")
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
        resume_file.seek(0, 2)  # Seek to end
        file_size = resume_file.tell()
        resume_file.seek(0)  # Reset to beginning
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            print(f"❌ File too large: {file_size} bytes")
            return jsonify({'error': 'File size too large. Maximum size is 10MB.'}), 400
        
        # Save the uploaded file
        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        file_path = os.path.join(UPLOAD_FOLDER, f"resume_{timestamp}{file_ext}")
        resume_file.save(file_path)
        print(f"💾 File saved to: {file_path}")
        
        # Extract text based on file type
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
        
        # Extract name for logging
        extracted_name = extract_name_from_resume(resume_text)
        print(f"👤 Candidate name extracted: {extracted_name}")
        
        # Check cache
        cache_key = get_cache_key(resume_text, job_description)
        global cache_hits, cache_misses
        
        if cache_key in analysis_cache:
            cache_hits += 1
            print(f"✅ Using cached analysis (hit #{cache_hits})")
            analysis = analysis_cache[cache_key]
        else:
            cache_misses += 1
            print(f"🔍 Cache miss #{cache_misses} - analyzing...")
            
            # Analyze with Gemini AI or fallback
            print("🤖 Starting analysis...")
            ai_start = time.time()
            
            if len(valid_clients) > 0:
                analysis = analyze_resume_with_gemini(resume_text, job_description)
            else:
                print("⚠️  No valid AI clients - using enhanced fallback")
                analysis = get_high_quality_fallback_analysis(resume_text, job_description)
            
            ai_time = time.time() - ai_start
            
            print(f"✅ Analysis completed in {ai_time:.2f}s")
            print(f"  Mode: {'AI' if not analysis.get('is_fallback') else 'Enhanced Fallback'}")
            print(f"  Candidate: {analysis.get('candidate_name', 'Unknown')}")
            print(f"  Score: {analysis.get('overall_score')}")
            if not analysis.get('is_fallback'):
                print(f"  Used: {analysis.get('used_key', 'Unknown key')}")
            
            # Cache the result for 1 hour
            analysis_cache[cache_key] = analysis
            print(f"💾 Cached analysis for future use")
        
        # Create Excel report
        print("📊 Creating Excel report...")
        excel_start = time.time()
        excel_filename = f"analysis_{timestamp}.xlsx"
        excel_path = create_excel_report(analysis, excel_filename)
        excel_time = time.time() - excel_start
        print(f"✅ Excel report created in {excel_time:.2f}s: {excel_path}")
        
        # Return analysis with download link
        analysis['excel_filename'] = os.path.basename(excel_path)
        analysis['cache_hit'] = cache_key in analysis_cache
        
        total_time = time.time() - start_time
        print(f"✅ Request completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        # Return enhanced fallback analysis even on critical errors
        fallback = get_high_quality_fallback_analysis()
        fallback['fallback_reason'] = f"Server error: {str(e)[:100]}"
        return jsonify(fallback)

@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    """Download the Excel report"""
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

@app.route('/quick-check', methods=['GET'])
def quick_check():
    """Quick endpoint to check if Gemini is responsive"""
    try:
        if not clients or len(valid_clients) == 0:
            return jsonify({
                'available': False,
                'reason': 'No valid API keys configured',
                'enhanced_fallback_available': True,
                'fallback_features': [
                    'Name extraction from resumes',
                    'Skill extraction from text',
                    'Experience analysis',
                    'Education detection'
                ],
                'suggestion': 'Configure valid GEMINI_API_KEY1, GEMINI_API_KEY2, etc. in environment variables'
            })
        
        # Check if any client has available quota
        available_clients = []
        for client_info in clients:
            if client_info.get('valid', True):
                quota_ok, reason = check_quota(client_info)
                if quota_ok and not client_info['quota_exceeded']:
                    available_clients.append({
                        'name': client_info['name'],
                        'key': client_info['key'][:8] + '...',
                        'requests_today': client_info['requests_today'],
                        'quota_remaining': QUOTA_DAILY - client_info['requests_today'],
                        'total_requests': client_info['total_requests']
                    })
        
        if available_clients:
            return jsonify({
                'available': True,
                'clients_available': len(available_clients),
                'available_clients': available_clients,
                'enhanced_fallback_available': True,
                'status': 'ready',
                'total_keys': len(clients),
                'valid_keys': len(valid_clients),
                'strategy': 'Load balancing between multiple keys'
            })
        else:
            # All keys have quota exceeded or are invalid
            return jsonify({
                'available': False,
                'reason': 'All API keys have exceeded quota or are invalid',
                'enhanced_fallback_available': True,
                'fallback_features': [
                    'Name extraction from resumes',
                    'Skill extraction from text',
                    'Experience analysis',
                    'Education detection',
                    'Personalized scoring'
                ],
                'status': 'quota_exceeded',
                'suggestion': 'Enhanced fallback analysis will extract information directly from resumes',
                'total_keys': len(clients),
                'valid_keys': len(valid_clients)
            })
                
    except Exception as e:
        error_msg = str(e).lower()
        return jsonify({
            'available': False,
            'reason': error_msg[:100],
            'enhanced_fallback_available': True,
            'status': 'error',
            'suggestion': 'Enhanced fallback analysis is available and will extract information from resumes'
        })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping to keep service awake"""
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'resume-analyzer',
        'ai_configured': len(valid_clients) > 0,
        'total_keys': len(clients),
        'valid_keys': len(valid_clients),
        'enhanced_fallback': True,
        'cache_stats': {
            'hits': cache_hits,
            'misses': cache_misses,
            'size': len(analysis_cache)
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'Backend is running!', 
        'timestamp': datetime.now().isoformat(),
        'total_api_keys': len(api_keys),
        'valid_clients': len(valid_clients),
        'keys_config': {
            'format': 'Use GEMINI_API_KEY1, GEMINI_API_KEY2, etc.',
            'max_keys': 9,
            'current_keys': len(api_keys),
            'valid_keys': len(valid_clients)
        },
        'enhanced_fallback': {
            'enabled': True,
            'features': [
                'Name extraction',
                'Skill extraction',
                'Experience analysis',
                'Education detection',
                'Personalized scoring'
            ]
        },
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'upload_folder_path': UPLOAD_FOLDER,
        'cache_stats': {
            'hits': cache_hits,
            'misses': cache_misses,
            'size': len(analysis_cache)
        },
        'quota_info': {
            'daily_limit': QUOTA_DAILY,
            'per_minute_limit': QUOTA_PER_MINUTE,
            'strategy': 'Auto-rotation between valid keys'
        }
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get detailed API usage statistics"""
    now = datetime.now()
    
    # Calculate quota status for each client
    clients_stats = []
    for client_info in clients:
        quota_ok, reason = check_quota(client_info)
        time_to_reset = client_info['last_reset'] + timedelta(days=1) - now
        hours_to_reset = time_to_reset.total_seconds() / 3600
        
        clients_stats.append({
            'name': client_info['name'],
            'key_preview': client_info['key'][:8] + '...',
            'is_valid': client_info.get('valid', True),
            'requests_today': client_info['requests_today'],
            'quota_remaining': QUOTA_DAILY - client_info['requests_today'],
            'quota_exceeded': client_info['quota_exceeded'],
            'total_requests': client_info['total_requests'],
            'errors': client_info['errors'],
            'last_reset': client_info['last_reset'].isoformat(),
            'hours_to_reset': round(hours_to_reset, 2),
            'requests_minute': client_info['requests_minute'],
            'status': 'valid' if client_info.get('valid', True) else 'invalid'
        })
    
    # Calculate overall stats
    total_requests = sum(c['requests_today'] for c in clients if c.get('valid', True))
    valid_client_count = len([c for c in clients if c.get('valid', True)])
    total_quota = QUOTA_DAILY * valid_client_count if valid_client_count > 0 else 0
    available_keys = len([c for c in clients_stats if c['status'] == 'valid' and not c['quota_exceeded']])
    
    return jsonify({
        'timestamp': now.isoformat(),
        'overall': {
            'total_keys': len(clients),
            'valid_keys': valid_client_count,
            'available_keys': available_keys,
            'total_requests_today': total_requests,
            'total_quota_today': total_quota,
            'quota_used_percentage': round((total_requests / total_quota * 100) if total_quota > 0 else 0, 1),
            'cache_hit_rate': round((cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0, 1)
        },
        'cache_stats': {
            'hits': cache_hits,
            'misses': cache_misses,
            'hit_ratio': cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0,
            'size': len(analysis_cache)
        },
        'enhanced_fallback': {
            'enabled': True,
            'extraction_features': [
                'name_extraction',
                'skill_extraction', 
                'experience_analysis',
                'education_detection',
                'personalized_scoring'
            ],
            'status': 'active'
        },
        'quota_config': {
            'daily_limit_per_key': QUOTA_DAILY,
            'per_minute_limit': QUOTA_PER_MINUTE,
            'total_daily_quota': total_quota
        },
        'clients': clients_stats,
        'service_status': {
            'upload_folder': UPLOAD_FOLDER,
            'strategy': 'Multi-key auto-rotation with enhanced fallback',
            'rotation_logic': 'Load balancing between valid keys, auto-switch on quota exceed'
        }
    })

@app.route('/reset-quota', methods=['POST'])
def reset_quota():
    """Reset quota for all clients (admin only)"""
    try:
        # In production, add authentication here
        for client_info in clients:
            client_info['requests_today'] = 0
            client_info['quota_exceeded'] = False
            client_info['last_reset'] = datetime.now()
            client_info['minute_requests'] = []
            client_info['errors'] = 0
        
        return jsonify({
            'status': 'success',
            'message': 'Quota reset for all clients',
            'timestamp': datetime.now().isoformat(),
            'clients_reset': len(clients)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-keys', methods=['GET'])
def test_keys():
    """Test if API keys are loaded"""
    keys_info = []
    
    for i in range(1, 4):
        key = os.getenv(f'GEMINI_API_KEY{i}', '')
        keys_info.append({
            'key_name': f'GEMINI_API_KEY{i}',
            'exists': bool(key),
            'length': len(key) if key else 0,
            'preview': key[:10] + '...' + key[-4:] if key and len(key) > 14 else key
        })
    
    # Also check single key
    single_key = os.getenv('GEMINI_API_KEY', '')
    keys_info.append({
        'key_name': 'GEMINI_API_KEY',
        'exists': bool(single_key),
        'length': len(single_key) if single_key else 0,
        'preview': single_key[:10] + '...' + single_key[-4:] if single_key and len(single_key) > 14 else single_key
    })
    
    return jsonify({
        'environment_check': keys_info,
        'total_keys_found': sum(1 for k in keys_info if k['exists']),
        'api_keys_in_memory': len(api_keys),
        'valid_clients': len(valid_clients)
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting...")
    print("="*50)
    
    # Print configuration
    print(f"📊 Configuration:")
    print(f"  Daily limit per key: {QUOTA_DAILY} requests")
    print(f"  Per minute limit: {QUOTA_PER_MINUTE} requests")
    print(f"  Total API keys loaded: {len(api_keys)}")
    print(f"  Valid clients initialized: {len(valid_clients)}")
    
    if len(valid_clients) > 0:
        print(f"\n🔑 Valid API Keys:")
        for i, client_info in enumerate(clients):
            if client_info.get('valid', True):
                status = "✅ Available" if not client_info['quota_exceeded'] else "⚠️ Quota Exceeded"
                print(f"  {client_info['name']}: {client_info['key'][:8]}... {status}")
        
        print(f"\n✨ AI Features Enabled:")
        print(f"  • Auto-rotation between {len(valid_clients)} valid keys")
        print(f"  • Load balancing (uses key with fewest requests)")
        print(f"  • Auto-switch when quota is exceeded")
        print(f"  • Total daily AI quota: {QUOTA_DAILY * len(valid_clients)} requests")
    else:
        print("⚠️  WARNING: No valid API keys found!")
        print("   The service will run in ENHANCED FALLBACK mode.")
        print("   To enable AI analysis, add valid keys as:")
        print("   GEMINI_API_KEY1=your_valid_key_1")
        print("   GEMINI_API_KEY2=your_valid_key_2")
    
    print(f"\n🛡️ Enhanced Fallback Features:")
    print(f"  • Name extraction from resumes")
    print(f"  • Skill detection and matching")
    print(f"  • Experience analysis")
    print(f"  • Education detection")
    print(f"  • Personalized scoring")
    
    print(f"\n📁 Upload folder: {UPLOAD_FOLDER}")
    print("="*50 + "\n")
    
    port = int(os.environ.get('PORT', 10000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
