import os
import re
import json
import time
import logging
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import pandas as pd
from werkzeug.utils import secure_filename
import pdfplumber
from docx import Document
import openai
from openai import OpenAI
import google.generativeai as genai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt'}
UPLOAD_FOLDER = Path('uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Initialize AI clients with enhanced fallback
ai_clients = []
enhanced_fallback_enabled = True
extraction_features = [
    "candidate_name_extraction",
    "skill_keyword_detection", 
    "experience_pattern_recognition",
    "education_qualification_scanning",
    "contact_info_extraction"
]

# Try to initialize OpenAI
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key:
    try:
        openai_client = OpenAI(api_key=openai_api_key)
        # Test the key
        test_response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        ai_clients.append({
            "name": "OpenAI GPT-3.5",
            "client": openai_client,
            "model": "gpt-3.5-turbo",
            "status": "valid",
            "requests_today": 0,
            "quota_exceeded": False,
            "last_reset": datetime.now()
        })
        logger.info("✅ OpenAI GPT-3.5 API initialized successfully")
    except Exception as e:
        logger.error(f"❌ OpenAI initialization failed: {e}")
        ai_clients.append({
            "name": "OpenAI GPT-3.5",
            "client": None,
            "model": "gpt-3.5-turbo",
            "status": "invalid",
            "error": str(e)
        })

# Try to initialize Google Gemini
gemini_api_key = os.getenv('GEMINI_API_KEY')
if gemini_api_key:
    try:
        genai.configure(api_key=gemini_api_key)
        gemini_client = genai.GenerativeModel('gemini-pro')
        # Test with a simple prompt
        response = gemini_client.generate_content("Hello")
        ai_clients.append({
            "name": "Google Gemini Pro",
            "client": gemini_client,
            "model": "gemini-pro",
            "status": "valid",
            "requests_today": 0,
            "quota_exceeded": False,
            "last_reset": datetime.now()
        })
        logger.info("✅ Google Gemini Pro API initialized successfully")
    except Exception as e:
        logger.error(f"❌ Google Gemini initialization failed: {e}")
        ai_clients.append({
            "name": "Google Gemini Pro",
            "client": None,
            "model": "gemini-pro",
            "status": "invalid",
            "error": str(e)
        })

logger.info(f"📊 Service Summary:")
logger.info(f"   AI Clients: {len([c for c in ai_clients if c['status'] == 'valid'])}/{len(ai_clients)} valid")
logger.info(f"   Enhanced Fallback: {'✅ Enabled' if enhanced_fallback_enabled else '❌ Disabled'}")
logger.info(f"   Extraction Features: {len(extraction_features)}")

def extract_text_from_file(file_path: str) -> str:
    """Extract text from various file formats with enhanced parsing."""
    text = ""
    file_ext = Path(file_path).suffix.lower()
    
    try:
        if file_ext == '.pdf':
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
        
        elif file_ext in ['.doc', '.docx']:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        
        elif file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        
        # Clean up text
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        raise
    
    return text.strip()

def extract_candidate_name(text: str) -> str:
    """Enhanced candidate name extraction from resume text."""
    # Look for common name patterns at the beginning of the text
    lines = text.strip().split('\n')
    
    # Check first few lines for name-like patterns
    for line in lines[:5]:
        line = line.strip()
        # Remove common resume headers
        clean_line = re.sub(r'(resume|curriculum vitae|cv|portfolio)', '', line, flags=re.IGNORECASE)
        clean_line = clean_line.strip()
        
        # Look for name patterns (2-3 words, capitalized, no special characters)
        if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}$', clean_line):
            return clean_line
        
        # Check for email or phone numbers that might precede name
        if '@' in line or re.search(r'\(\d{3}\)\s*\d{3}-\d{4}|\+\d{1,3}\s*\d{10}', line):
            continue
            
        # If line has reasonable length and looks like a name
        if 2 <= len(clean_line.split()) <= 4 and len(clean_line) <= 50:
            # Check if it contains common name indicators
            name_words = clean_line.split()
            if all(len(word) >= 2 for word in name_words):
                return clean_line
    
    # Fallback: Return first non-empty line that looks reasonable
    for line in lines:
        line = line.strip()
        if line and len(line) <= 100 and not any(word in line.lower() for word in ['objective', 'summary', 'experience', 'education']):
            return line.split('\n')[0] if '\n' in line else line
    
    return "Candidate"

def extract_skills_from_text(text: str, job_description: str) -> Dict[str, List[str]]:
    """Extract skills from resume text and compare with job description."""
    # Common skill keywords
    common_skills = {
        'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'go', 'rust', 'swift', 'kotlin'],
        'web': ['html', 'css', 'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'express', 'spring'],
        'databases': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'sqlite'],
        'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins'],
        'data': ['excel', 'tableau', 'power bi', 'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch'],
        'soft': ['communication', 'leadership', 'teamwork', 'problem solving', 'creativity', 'adaptability']
    }
    
    # Extract skills from resume
    resume_skills = []
    text_lower = text.lower()
    
    for category, skills in common_skills.items():
        for skill in skills:
            if skill in text_lower:
                resume_skills.append(skill.title())
    
    # Extract skills from job description
    job_skills = []
    job_lower = job_description.lower()
    
    for category, skills in common_skills.items():
        for skill in skills:
            if skill in job_lower:
                job_skills.append(skill.title())
    
    # Find matched and missing skills
    matched_skills = [skill for skill in job_skills if skill in resume_skills]
    missing_skills = [skill for skill in job_skills if skill not in resume_skills]
    
    # Remove duplicates
    matched_skills = list(dict.fromkeys(matched_skills))
    missing_skills = list(dict.fromkeys(missing_skills))
    
    return {
        'matched': matched_skills[:15],  # Limit to top 15
        'missing': missing_skills[:15]
    }

def analyze_with_ai(client_config: Dict, resume_text: str, job_description: str) -> Dict[str, Any]:
    """Analyze resume with AI service."""
    client = client_config['client']
    model = client_config['model']
    
    prompt = f"""
    Analyze this resume against the job description and provide a comprehensive analysis.
    
    RESUME:
    {resume_text[:3000]}  # Limit resume text
    
    JOB DESCRIPTION:
    {job_description[:2000]}  # Limit job description
    
    Please provide analysis in the following JSON format:
    {{
        "overall_score": 85,
        "recommendation": "Brief recommendation text",
        "skills_matched": ["Python", "React", "AWS"],
        "skills_missing": ["Kubernetes", "Docker"],
        "experience_summary": "Summary of candidate experience",
        "education_summary": "Summary of education",
        "key_strengths": ["Strength 1", "Strength 2"],
        "areas_for_improvement": ["Area 1", "Area 2"]
    }}
    
    Overall score should be 0-100 based on match quality.
    """
    
    try:
        if "gpt" in model:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a resume analysis expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            result_text = response.choices[0].message.content
            
        elif "gemini" in model:
            response = client.generate_content(prompt)
            result_text = response.text
        
        # Parse JSON from response
        try:
            # Find JSON in response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                # Fallback if no JSON found
                analysis = {
                    "overall_score": 75,
                    "recommendation": "AI analysis completed. Consider the following insights.",
                    "skills_matched": [],
                    "skills_missing": [],
                    "experience_summary": "Experience analyzed from resume.",
                    "education_summary": "Education background reviewed.",
                    "key_strengths": ["AI-powered analysis completed"],
                    "areas_for_improvement": ["Consider adding more specific skills mentioned in job description"]
                }
        except json.JSONDecodeError:
            # Fallback analysis
            analysis = create_enhanced_fallback_analysis(resume_text, job_description)
        
        client_config['requests_today'] += 1
        return analysis
        
    except Exception as e:
        logger.error(f"AI analysis error: {e}")
        raise

def create_enhanced_fallback_analysis(resume_text: str, job_description: str) -> Dict[str, Any]:
    """Create analysis using enhanced text parsing when AI is unavailable."""
    # Extract candidate name
    candidate_name = extract_candidate_name(resume_text)
    
    # Extract skills
    skills_result = extract_skills_from_text(resume_text, job_description)
    
    # Calculate score based on skill match
    total_skills = len(skills_result['matched']) + len(skills_result['missing'])
    if total_skills > 0:
        score = int((len(skills_result['matched']) / total_skills) * 100)
    else:
        score = 50  # Default score
    
    # Adjust score based on text length and quality
    if len(resume_text) > 500:
        score = min(score + 10, 95)
    
    # Create summaries
    experience_summary = extract_experience_summary(resume_text)
    education_summary = extract_education_summary(resume_text)
    
    return {
        "overall_score": score,
        "candidate_name": candidate_name,
        "recommendation": create_recommendation(score, skills_result),
        "skills_matched": skills_result['matched'],
        "skills_missing": skills_result['missing'],
        "experience_summary": experience_summary,
        "education_summary": education_summary,
        "key_strengths": extract_key_strengths(resume_text, skills_result['matched']),
        "areas_for_improvement": suggest_improvements(skills_result['missing']),
        "is_fallback": True,
        "fallback_reason": "Enhanced text analysis (no AI available)",
        "analysis_quality": "enhanced_fallback",
        "extracted_info": True
    }

def extract_experience_summary(text: str) -> str:
    """Extract experience summary from resume text."""
    # Look for experience-related sections
    exp_keywords = ['experience', 'work history', 'employment', 'career']
    text_lower = text.lower()
    
    for keyword in exp_keywords:
        if keyword in text_lower:
            # Find the section
            start_idx = text_lower.find(keyword)
            if start_idx != -1:
                # Take next 500 characters after the keyword
                section = text[start_idx:start_idx + 500]
                # Clean up the section
                section = re.sub(r'\s+', ' ', section)
                return f"Experience section detected: {section[:200]}..."
    
    # If no explicit experience section, look for date patterns
    date_pattern = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b'
    dates = re.findall(date_pattern, text, re.IGNORECASE)
    if dates:
        return f"Professional experience timeline detected with {len(dates)} date entries."
    
    return "Experience details extracted from resume content."

def extract_education_summary(text: str) -> str:
    """Extract education summary from resume text."""
    # Look for education-related sections
    edu_keywords = ['education', 'academic', 'qualifications', 'degree', 'university', 'college']
    text_lower = text.lower()
    
    for keyword in edu_keywords:
        if keyword in text_lower:
            start_idx = text_lower.find(keyword)
            if start_idx != -1:
                section = text[start_idx:start_idx + 300]
                section = re.sub(r'\s+', ' ', section)
                return f"Education background: {section[:150]}..."
    
    # Look for degree patterns
    degree_pattern = r'\b(?:B\.?S\.?|B\.?A\.?|M\.?S\.?|M\.?A\.?|Ph\.?D\.?|MBA)\b'
    degrees = re.findall(degree_pattern, text, re.IGNORECASE)
    if degrees:
        return f"Educational qualifications include: {', '.join(set(degrees))}"
    
    return "Education information analyzed from resume."

def extract_key_strengths(text: str, matched_skills: List[str]) -> List[str]:
    """Extract key strengths from resume."""
    strengths = []
    
    if matched_skills:
        strengths.append(f"Strong match with {len(matched_skills)} required skills")
    
    # Check for experience duration
    exp_pattern = r'(\d+)\s*(?:years?|yrs?)\s+.*?(?:experience|exp)'
    exp_matches = re.findall(exp_pattern, text, re.IGNORECASE)
    if exp_matches:
        years = max([int(m) for m in exp_matches if m.isdigit()], default=0)
        if years >= 3:
            strengths.append(f"Substantial professional experience ({years}+ years)")
    
    # Check for certifications
    cert_keywords = ['certified', 'certification', 'license', 'accredited']
    if any(keyword in text.lower() for keyword in cert_keywords):
        strengths.append("Professional certifications identified")
    
    # Add generic strengths if needed
    if len(strengths) < 2:
        strengths.append("Well-structured resume with clear sections")
        strengths.append("Relevant professional background")
    
    return strengths[:4]  # Limit to 4 strengths

def suggest_improvements(missing_skills: List[str]) -> List[str]:
    """Suggest improvements based on missing skills."""
    improvements = []
    
    if missing_skills:
        improvements.append(f"Consider adding {', '.join(missing_skills[:3])} skills")
    
    improvements.append("Quantify achievements with specific metrics")
    improvements.append("Highlight relevant projects and their impact")
    
    return improvements[:3]

def create_recommendation(score: int, skills_result: Dict) -> str:
    """Create recommendation based on score and skills."""
    if score >= 80:
        return f"Strong match! You have {len(skills_result['matched'])} of the required skills. Consider highlighting your experience with specific examples."
    elif score >= 60:
        return f"Good match with {len(skills_result['matched'])} skills. Consider adding {', '.join(skills_result['missing'][:2])} to improve your score."
    else:
        return f"Focus on developing {', '.join(skills_result['missing'][:3])} skills. Consider relevant courses or projects to strengthen your profile."

def create_excel_report(analysis: Dict[str, Any], filename: str) -> str:
    """Create Excel report from analysis."""
    try:
        # Create DataFrames for different sections
        data = {
            'Metric': ['Overall Match Score', 'Skills Matched', 'Skills Missing'],
            'Value': [
                f"{analysis['overall_score']}/100",
                len(analysis.get('skills_matched', [])),
                len(analysis.get('skills_missing', []))
            ]
        }
        
        df_summary = pd.DataFrame(data)
        
        # Skills matched DataFrame
        if analysis.get('skills_matched'):
            df_matched = pd.DataFrame({
                'Matched Skills': analysis['skills_matched']
            })
        else:
            df_matched = pd.DataFrame({'Matched Skills': ['No skills matched']})
        
        # Skills missing DataFrame
        if analysis.get('skills_missing'):
            df_missing = pd.DataFrame({
                'Missing Skills': analysis['skills_missing'],
                'Priority': ['High' if i < 3 else 'Medium' if i < 6 else 'Low' 
                           for i in range(len(analysis['skills_missing']))]
            })
        else:
            df_missing = pd.DataFrame({'Missing Skills': ['All required skills present!'], 'Priority': ['N/A']})
        
        # Key insights DataFrame
        insights_data = {
            'Key Strengths': analysis.get('key_strengths', []) + [''] * (3 - len(analysis.get('key_strengths', []))),
            'Areas for Improvement': analysis.get('areas_for_improvement', []) + [''] * (3 - len(analysis.get('areas_for_improvement', [])))
        }
        df_insights = pd.DataFrame(insights_data)
        
        # Create Excel writer
        report_path = UPLOAD_FOLDER / filename
        with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            df_matched.to_excel(writer, sheet_name='Skills Matched', index=False)
            df_missing.to_excel(writer, sheet_name='Skills Missing', index=False)
            df_insights.to_excel(writer, sheet_name='Insights', index=False)
            
            # Summary sheet
            workbook = writer.book
            summary_sheet = writer.sheets['Summary']
            summary_sheet.column_dimensions['A'].width = 25
            summary_sheet.column_dimensions['B'].width = 25
            
            # Add analysis details
            summary_sheet['D1'] = 'Analysis Details'
            summary_sheet['D2'] = f"Candidate: {analysis.get('candidate_name', 'N/A')}"
            summary_sheet['D3'] = f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            summary_sheet['D4'] = f"Analysis Type: {'AI-Powered' if not analysis.get('is_fallback') else 'Enhanced Text Analysis'}"
            summary_sheet['D5'] = 'Recommendation:'
            summary_sheet['D6'] = analysis.get('recommendation', '')
        
        return str(report_path)
        
    except Exception as e:
        logger.error(f"Error creating Excel report: {e}")
        raise

@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint."""
    valid_keys = len([c for c in ai_clients if c.get('status') == 'valid'])
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "ai_clients": len(ai_clients),
        "valid_keys": valid_keys,
        "enhanced_fallback": enhanced_fallback_enabled,
        "extraction_features": extraction_features if enhanced_fallback_enabled else []
    })

@app.route('/quick-check', methods=['GET'])
def quick_check():
    """Quick AI availability check."""
    # Check if any AI client is available and not exceeding quota
    available_clients = [
        c for c in ai_clients 
        if c.get('status') == 'valid' and not c.get('quota_exceeded', False)
    ]
    
    if available_clients:
        return jsonify({
            "available": True,
            "status": "ai_available",
            "clients_available": len(available_clients),
            "enhanced_fallback_available": enhanced_fallback_enabled
        })
    else:
        return jsonify({
            "available": False,
            "status": "enhanced_only",
            "enhanced_fallback_available": enhanced_fallback_enabled,
            "message": "Using enhanced text analysis"
        })

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get service statistics and quota status."""
    now = datetime.now()
    
    # Update client statuses
    for client in ai_clients:
        if client.get('last_reset'):
            # Reset daily counts if more than 24 hours have passed
            if now - client['last_reset'] > timedelta(hours=24):
                client['requests_today'] = 0
                client['quota_exceeded'] = False
                client['last_reset'] = now
    
    stats = {
        "timestamp": now.isoformat(),
        "overall": {
            "total_keys": len(ai_clients),
            "valid_keys": len([c for c in ai_clients if c.get('status') == 'valid']),
            "active_requests": sum(c.get('requests_today', 0) for c in ai_clients),
            "enhanced_fallback": {
                "enabled": enhanced_fallback_enabled,
                "extraction_features": extraction_features
            }
        },
        "clients": []
    }
    
    for client in ai_clients:
        client_info = {
            "name": client["name"],
            "status": client.get("status", "unknown"),
            "model": client.get("model", "unknown"),
            "requests_today": client.get("requests_today", 0),
            "quota_exceeded": client.get("quota_exceeded", False)
        }
        
        if client.get('last_reset'):
            time_since_reset = now - client['last_reset']
            hours_to_reset = max(0, 24 - time_since_reset.total_seconds() / 3600)
            client_info["hours_to_reset"] = round(hours_to_reset, 1)
        
        stats["clients"].append(client_info)
    
    return jsonify(stats)

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Main analysis endpoint."""
    start_time = time.time()
    
    # Check file in request
    if 'resume' not in request.files:
        return jsonify({"error": "No resume file provided"}), 400
    
    file = request.files['resume']
    job_description = request.form.get('jobDescription', '')
    
    if not job_description:
        return jsonify({"error": "Job description is required"}), 400
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Validate file
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}), 400
    
    # Save uploaded file
    filename = secure_filename(f"{int(time.time())}_{file.filename}")
    file_path = UPLOAD_FOLDER / filename
    file.save(file_path)
    
    try:
        # Extract text from resume
        resume_text = extract_text_from_file(str(file_path))
        if not resume_text or len(resume_text) < 50:
            return jsonify({"error": "Could not extract sufficient text from resume"}), 400
        
        # Try AI analysis first
        analysis_result = None
        ai_used = False
        fallback_reason = ""
        
        # Find available AI client
        available_clients = [
            c for c in ai_clients 
            if c.get('status') == 'valid' and not c.get('quota_exceeded', False)
        ]
        
        if available_clients:
            try:
                client_config = available_clients[0]  # Use first available
                logger.info(f"Using AI client: {client_config['name']}")
                analysis_result = analyze_with_ai(client_config, resume_text, job_description)
                ai_used = True
            except Exception as ai_error:
                logger.error(f"AI analysis failed: {ai_error}")
                fallback_reason = f"AI service error: {str(ai_error)}"
                # Mark client as possibly exceeding quota if it's a quota error
                if "quota" in str(ai_error).lower() or "429" in str(ai_error):
                    client_config['quota_exceeded'] = True
                    fallback_reason = "AI quota exceeded"
        
        # If AI failed or not available, use enhanced fallback
        if not analysis_result and enhanced_fallback_enabled:
            logger.info("Using enhanced fallback analysis")
            analysis_result = create_enhanced_fallback_analysis(resume_text, job_description)
            analysis_result['fallback_reason'] = fallback_reason or "Enhanced text analysis (AI unavailable)"
        
        if not analysis_result:
            return jsonify({"error": "Analysis failed. Please try again."}), 500
        
        # Add metadata
        analysis_result['analysis_time'] = round(time.time() - start_time, 2)
        analysis_result['is_fallback'] = not ai_used
        analysis_result['text_length'] = len(resume_text)
        
        # Ensure candidate name is present
        if not analysis_result.get('candidate_name'):
            analysis_result['candidate_name'] = extract_candidate_name(resume_text)
        
        # Create Excel report
        excel_filename = f"analysis_{int(time.time())}.xlsx"
        try:
            create_excel_report(analysis_result, excel_filename)
            analysis_result['excel_filename'] = excel_filename
            analysis_result['excel_url'] = f"/download/{excel_filename}"
        except Exception as e:
            logger.error(f"Excel report creation failed: {e}")
            # Continue without Excel report
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except:
            pass
        
        return jsonify(analysis_result)
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        # Clean up on error
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download analysis report."""
    file_path = UPLOAD_FOLDER / secure_filename(filename)
    
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    
    try:
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"resume_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({"error": "Download failed"}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup_files():
    """Clean up old files."""
    try:
        cutoff_time = time.time() - 3600  # 1 hour ago
        files_deleted = 0
        
        for file_path in UPLOAD_FOLDER.glob('*'):
            if file_path.is_file():
                file_age = time.time() - file_path.stat().st_mtime
                if file_age > 3600:  # Delete files older than 1 hour
                    file_path.unlink()
                    files_deleted += 1
        
        return jsonify({
            "message": f"Cleaned up {files_deleted} old files",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
