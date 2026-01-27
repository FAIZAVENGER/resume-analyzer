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
import hashlib
import random
import gc
import sys
import math
from typing import List, Dict, Tuple, Any
import spacy
import numpy as np

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure DeepSeek API
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')

# Advanced ATS Configuration
ATS_CONFIG = {
    'weights': {
        'skills_match': 0.35,      # 35% - Technical skills alignment
        'experience_relevance': 0.25,  # 25% - Experience fit
        'role_alignment': 0.20,    # 20% - Role and domain match
        'project_impact': 0.15,    # 15% - Project complexity and impact
        'resume_quality': 0.05     # 5% - Resume presentation
    },
    'thresholds': {
        'seniority_mismatch_penalty': 15,
        'vague_description_penalty': 10,
        'missing_required_skill': 8,
        'partial_skill_match': 0.5,
        'full_skill_match': 1.0
    },
    'domain_specific': {
        'vlsi': ['VLSI', 'ASIC', 'FPGA', 'Verilog', 'VHDL', 'SystemVerilog', 
                'RTL', 'Physical Design', 'Timing Analysis', 'Cadence', 
                'Synopsys', 'Mentor Graphics', 'CMOS', 'Digital Design',
                'Analog Design', 'Mixed Signal', 'PDK', 'Tapeout', 'DFT',
                'Formal Verification', 'Power Analysis', 'Floorplanning',
                'Place and Route', 'Clock Tree Synthesis'],
        'cs': ['Python', 'Java', 'C++', 'JavaScript', 'React', 'Node.js',
              'AWS', 'Docker', 'Kubernetes', 'Machine Learning', 'AI',
              'Data Structures', 'Algorithms', 'SQL', 'NoSQL', 'REST API',
              'Microservices', 'CI/CD', 'Git', 'Agile', 'Scrum',
              'TensorFlow', 'PyTorch', 'Computer Vision', 'NLP',
              'Cybersecurity', 'Networking', 'Operating Systems'],
        'general': ['Leadership', 'Communication', 'Teamwork', 'Problem Solving',
                   'Project Management', 'Analytical Skills', 'Critical Thinking']
    }
}

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

# Get absolute path for folders
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

# Cache for consistent scoring
score_cache = {}
cache_lock = threading.Lock()

# Batch processing configuration
MAX_CONCURRENT_REQUESTS = 3
MAX_BATCH_SIZE = 10
MAX_INDIVIDUAL_REPORTS = 10

# Rate limiting protection
MAX_RETRIES = 3
RETRY_DELAY_BASE = 3

# Memory optimization
service_running = True

# Initialize NLP for text processing
try:
    nlp = spacy.load("en_core_web_sm")
except:
    nlp = None

def update_activity():
    """Update last activity timestamp"""
    global last_activity_time
    last_activity_time = datetime.now()

def calculate_resume_hash(resume_text, job_description):
    """Calculate a hash for caching consistent scores"""
    content = f"{resume_text[:500]}{job_description[:500]}".encode('utf-8')
    return hashlib.md5(content).hexdigest()

def extract_required_skills(job_description: str) -> Dict[str, float]:
    """Extract required skills from job description with importance weighting"""
    skills = {}
    
    # Keywords that indicate required skills
    required_keywords = ['required', 'must have', 'essential', 'mandatory', 'need', 'required skills']
    preferred_keywords = ['preferred', 'nice to have', 'bonus', 'advantage']
    
    # Extract technical skills patterns
    technical_patterns = [
        r'(?:knowledge|experience|proficiency|expertise) in ([A-Za-z0-9+/#. ]+)',
        r'(?:familiarity|understanding) with ([A-Za-z0-9+/#. ]+)',
        r'(?:skills|technologies|tools):? ([A-Za-z0-9+/#., ]+)'
    ]
    
    for pattern in technical_patterns:
        matches = re.findall(pattern, job_description, re.IGNORECASE)
        for match in matches:
            # Split by commas, and, or
            skill_list = re.split(r'[,/&]|\band\b|\bor\b', match)
            for skill in skill_list:
                skill = skill.strip()
                if skill and len(skill) > 1:
                    # Check if it's required or preferred
                    context = job_description.lower()
                    start_pos = max(0, context.find(skill.lower()) - 100)
                    end_pos = min(len(context), context.find(skill.lower()) + 100)
                    context_window = context[start_pos:end_pos]
                    
                    importance = 0.5  # Default medium importance
                    if any(keyword in context_window for keyword in required_keywords):
                        importance = 1.0  # High importance for required
                    elif any(keyword in context_window for keyword in preferred_keywords):
                        importance = 0.3  # Lower importance for preferred
                    
                    skills[skill] = importance
    
    # Add domain-specific skills detection
    for domain, domain_skills in ATS_CONFIG['domain_specific'].items():
        for skill in domain_skills:
            if skill.lower() in job_description.lower():
                # Check if it's mentioned as a requirement
                if any(keyword in job_description.lower() for keyword in required_keywords):
                    skills[skill] = 1.0
                else:
                    skills[skill] = 0.5
    
    return skills

def extract_experience_details(resume_text: str) -> Dict[str, Any]:
    """Extract experience details from resume"""
    experience = {
        'total_years': 0,
        'seniority': 'entry',
        'relevant_experience_years': 0,
        'job_titles': [],
        'companies': [],
        'responsibilities': []
    }
    
    # Extract years of experience
    year_patterns = [
        r'(\d+)\+?\s*(?:years?|yrs?)(?:\s*of)?\s*(?:experience|exp)',
        r'(?:experience|exp)[:\s]*(\d+)\+?\s*(?:years?|yrs?)',
        r'(\d{4})\s*[-–]\s*(?:Present|\d{4})'  # Date ranges
    ]
    
    for pattern in year_patterns:
        matches = re.findall(pattern, resume_text, re.IGNORECASE)
        for match in matches:
            if match.isdigit():
                years = int(match)
                experience['total_years'] = max(experience['total_years'], years)
                break
    
    # Extract job titles
    title_patterns = [
        r'(?:Senior|Lead|Principal|Staff|Junior|Associate)?\s*'
        r'(?:Software|Hardware|VLSI|Design|Verification|Test|QA|System|Network|Data|AI|ML)?\s*'
        r'(?:Engineer|Developer|Architect|Scientist|Analyst|Specialist|Manager|Director)',
        r'(?:Intern|Trainee|Apprentice)'
    ]
    
    for pattern in title_patterns:
        matches = re.findall(pattern, resume_text, re.IGNORECASE)
        experience['job_titles'].extend(matches)
    
    # Determine seniority based on titles and years
    senior_keywords = ['Senior', 'Lead', 'Principal', 'Staff', 'Manager', 'Director', 'Head']
    entry_keywords = ['Intern', 'Trainee', 'Apprentice', 'Junior', 'Associate']
    
    senior_count = sum(1 for title in experience['job_titles'] 
                      if any(keyword in title for keyword in senior_keywords))
    entry_count = sum(1 for title in experience['job_titles']
                     if any(keyword in title for keyword in entry_keywords))
    
    if senior_count > 0 and experience['total_years'] >= 5:
        experience['seniority'] = 'senior'
    elif entry_count > 0 or experience['total_years'] < 2:
        experience['seniority'] = 'entry'
    else:
        experience['seniority'] = 'mid'
    
    return experience

def calculate_skills_score(resume_text: str, required_skills: Dict[str, float]) -> Dict[str, Any]:
    """Calculate skills match score with context awareness"""
    if not required_skills:
        return {'score': 0, 'matched_skills': [], 'missing_skills': list(required_skills.keys())}
    
    matched_skills = []
    missing_skills = []
    context_verified = []
    tool_only_mentions = []
    
    total_weight = sum(required_skills.values())
    earned_weight = 0
    
    for skill, importance in required_skills.items():
        skill_lower = skill.lower()
        resume_lower = resume_text.lower()
        
        # Check if skill is mentioned
        if skill_lower in resume_lower:
            # Find context around the skill mention
            skill_pos = resume_lower.find(skill_lower)
            start_pos = max(0, skill_pos - 200)
            end_pos = min(len(resume_lower), skill_pos + len(skill) + 200)
            context = resume_lower[start_pos:end_pos]
            
            # Check for evidence of practical usage
            evidence_keywords = ['developed', 'implemented', 'designed', 'built',
                               'created', 'optimized', 'improved', 'managed',
                               'led', 'responsible for', 'experience with',
                               'proficient in', 'expertise in', 'hands-on']
            
            has_context = any(keyword in context for keyword in evidence_keywords)
            
            if has_context:
                # Full points for skills with context
                earned_weight += importance * ATS_CONFIG['thresholds']['full_skill_match']
                matched_skills.append(f"{skill} (verified with context)")
                context_verified.append(skill)
            else:
                # Partial points for skills without context
                earned_weight += importance * ATS_CONFIG['thresholds']['partial_skill_match']
                matched_skills.append(f"{skill} (mentioned)")
                tool_only_mentions.append(skill)
        else:
            missing_skills.append(skill)
            earned_weight += 0  # No points for missing skills
    
    # Calculate final score (0-100)
    if total_weight > 0:
        score = (earned_weight / total_weight) * 100 * ATS_CONFIG['weights']['skills_match']
    else:
        score = 0
    
    return {
        'score': round(score, 1),
        'matched_skills': matched_skills,
        'missing_skills': missing_skills,
        'context_verified': context_verified,
        'tool_only_mentions': tool_only_mentions,
        'total_required': len(required_skills),
        'matched_count': len(matched_skills)
    }

def calculate_experience_score(resume_text: str, job_description: str, 
                              experience_details: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate experience relevance score"""
    score = 0
    penalties = []
    bonuses = []
    
    # Extract job requirements
    jd_lower = job_description.lower()
    
    # Check for required years
    required_years = 0
    year_matches = re.findall(r'(\d+)\+?\s*(?:years?|yrs?)(?:\s*of)?\s*(?:experience|exp)', jd_lower)
    if year_matches:
        required_years = max(int(match) for match in year_matches)
    
    # Years of experience match
    actual_years = experience_details['total_years']
    if required_years > 0:
        if actual_years >= required_years:
            # Bonus for exceeding requirements (up to 20% extra)
            excess_bonus = min((actual_years - required_years) * 2, 20)
            score += 20 + excess_bonus  # Base 20 for meeting + bonus
            bonuses.append(f"Exceeds required {required_years} years by {actual_years - required_years} years")
        else:
            # Penalty for insufficient experience
            penalty = min((required_years - actual_years) * 5, 20)
            score += max(0, 20 - penalty)
            penalties.append(f"Missing {required_years - actual_years} years of required experience")
    else:
        score += 20  # Default if no years specified
    
    # Seniority alignment
    jd_seniority = 'mid'  # Default
    if 'senior' in jd_lower or 'lead' in jd_lower or 'principal' in jd_lower:
        jd_seniority = 'senior'
    elif 'junior' in jd_lower or 'entry' in jd_lower or 'associate' in jd_lower:
        jd_seniority = 'entry'
    
    candidate_seniority = experience_details['seniority']
    
    if candidate_seniority == 'senior' and jd_seniority == 'entry':
        penalty = ATS_CONFIG['thresholds']['seniority_mismatch_penalty']
        score -= penalty
        penalties.append(f"Senior candidate applying for entry-level role (-{penalty} points)")
    elif candidate_seniority == 'entry' and jd_seniority == 'senior':
        penalty = ATS_CONFIG['thresholds']['seniority_mismatch_penalty']
        score -= penalty
        penalties.append(f"Entry-level candidate applying for senior role (-{penalty} points)")
    else:
        score += 10  # Good seniority match
    
    # Industry/domain experience match
    domain_score = 0
    domains = ['VLSI', 'software', 'hardware', 'cloud', 'AI/ML', 'data', 'web']
    for domain in domains:
        if domain.lower() in jd_lower and domain.lower() in resume_text.lower():
            domain_score += 5
    
    score += min(domain_score, 15)
    if domain_score > 0:
        bonuses.append(f"Relevant {domain} experience")
    
    # Apply weight
    final_score = min(score, 100) * ATS_CONFIG['weights']['experience_relevance']
    
    return {
        'score': round(final_score, 1),
        'penalties': penalties,
        'bonuses': bonuses,
        'actual_years': actual_years,
        'required_years': required_years,
        'seniority_match': candidate_seniority == jd_seniority
    }

def calculate_role_alignment_score(resume_text: str, job_description: str) -> Dict[str, Any]:
    """Calculate role and domain alignment score"""
    score = 0
    matches = []
    mismatches = []
    
    # Extract key responsibilities from job description
    jd_lower = job_description.lower()
    resume_lower = resume_text.lower()
    
    # Common responsibility keywords
    responsibility_patterns = [
        r'responsible for ([^\.]+)',
        r'duties include ([^\.]+)',
        r'will (?:be|have to) ([^\.]+)',
        r'must (?:be able to )?([^\.]+)'
    ]
    
    jd_responsibilities = []
    for pattern in responsibility_patterns:
        matches_found = re.findall(pattern, jd_lower)
        jd_responsibilities.extend(matches_found)
    
    # Check for matching responsibilities in resume
    matched_responsibilities = 0
    for resp in jd_responsibilities:
        # Extract key terms from responsibility
        key_terms = re.findall(r'\b[a-z]{4,}\b', resp)
        for term in key_terms:
            if term in resume_lower and len(term) > 3:
                # Check if term is in similar context
                term_pos = resume_lower.find(term)
                start = max(0, term_pos - 50)
                end = min(len(resume_lower), term_pos + len(term) + 50)
                context = resume_lower[start:end]
                
                # Look for action verbs around the term
                action_verbs = ['developed', 'created', 'built', 'implemented',
                              'managed', 'led', 'optimized', 'improved',
                              'designed', 'architected', 'tested', 'deployed']
                
                if any(verb in context for verb in action_verbs):
                    matched_responsibilities += 1
                    matches.append(f"Matched responsibility: {term}")
                    break
    
    # Calculate score based on responsibility match
    if jd_responsibilities:
        responsibility_score = (matched_responsibilities / len(jd_responsibilities)) * 40
    else:
        responsibility_score = 20  # Default if no explicit responsibilities
    
    score += responsibility_score
    
    # Domain-specific alignment (VLSI/CS focus)
    domain_score = 0
    
    # VLSI domain check
    vlsi_keywords = ATS_CONFIG['domain_specific']['vlsi']
    vlsi_in_jd = sum(1 for keyword in vlsi_keywords if keyword.lower() in jd_lower)
    vlsi_in_resume = sum(1 for keyword in vlsi_keywords if keyword.lower() in resume_lower)
    
    if vlsi_in_jd > 0:
        if vlsi_in_resume > 0:
            domain_score += min(vlsi_in_resume * 2, 20)
            matches.append(f"VLSI domain match: {vlsi_in_resume} skills")
        else:
            mismatches.append("VLSI domain mismatch - no relevant experience")
            domain_score -= 10
    
    # CS domain check
    cs_keywords = ATS_CONFIG['domain_specific']['cs']
    cs_in_jd = sum(1 for keyword in cs_keywords if keyword.lower() in jd_lower)
    cs_in_resume = sum(1 for keyword in cs_keywords if keyword.lower() in resume_lower)
    
    if cs_in_jd > 0:
        if cs_in_resume > 0:
            domain_score += min(cs_in_resume * 1.5, 15)
            matches.append(f"CS domain match: {cs_in_resume} skills")
        else:
            mismatches.append("CS domain mismatch - no relevant experience")
            domain_score -= 10
    
    score += domain_score
    
    # General domain alignment
    general_keywords = ATS_CONFIG['domain_specific']['general']
    general_match = sum(1 for keyword in general_keywords if keyword.lower() in resume_lower)
    score += min(general_match * 3, 15)
    
    # Apply weight
    final_score = min(score, 100) * ATS_CONFIG['weights']['role_alignment']
    
    return {
        'score': round(final_score, 1),
        'matches': matches,
        'mismatches': mismatches,
        'responsibilities_matched': matched_responsibilities,
        'total_responsibilities': len(jd_responsibilities) if jd_responsibilities else 0
    }

def calculate_project_impact_score(resume_text: str) -> Dict[str, Any]:
    """Calculate project complexity and impact score"""
    score = 0
    project_details = []
    
    # Find project sections
    project_sections = re.findall(r'(?:project|experience|work)[:\s]*([^•\n]+(?:•[^•\n]+)*)', 
                                 resume_text, re.IGNORECASE)
    
    if not project_sections:
        # Try alternative patterns
        project_sections = re.findall(r'\b(?:developed|created|built|implemented|designed)[^\.]+\.', 
                                     resume_text, re.IGNORECASE)
    
    project_count = len(project_sections)
    
    # Score based on project count
    if project_count >= 5:
        score += 25
    elif project_count >= 3:
        score += 20
    elif project_count >= 1:
        score += 15
    else:
        score += 5
    
    # Analyze project quality indicators
    quality_indicators = {
        'impact_keywords': ['increased', 'decreased', 'improved', 'optimized',
                          'reduced', 'saved', 'scaled', 'achieved'],
        'complexity_keywords': ['architecture', 'system design', 'large-scale',
                              'distributed', 'microservices', 'algorithm',
                              'optimization', 'performance'],
        'ownership_keywords': ['led', 'managed', 'owned', 'spearheaded',
                             'initiated', 'founded', 'directed'],
        'metrics_keywords': ['%', 'times', 'x', 'users', 'revenue', 'efficiency',
                           'performance', 'throughput', 'latency']
    }
    
    quality_score = 0
    for section in project_sections:
        section_lower = section.lower()
        
        # Check for impact
        impact_count = sum(1 for keyword in quality_indicators['impact_keywords'] 
                         if keyword in section_lower)
        quality_score += impact_count * 2
        
        # Check for complexity
        complexity_count = sum(1 for keyword in quality_indicators['complexity_keywords']
                             if keyword in section_lower)
        quality_score += complexity_count * 3
        
        # Check for ownership
        ownership_count = sum(1 for keyword in quality_indicators['ownership_keywords']
                            if keyword in section_lower)
        quality_score += ownership_count * 4
        
        # Check for metrics
        metrics_count = sum(1 for keyword in quality_indicators['metrics_keywords']
                          if keyword in section_lower)
        quality_score += metrics_count * 5
        
        # Store project details
        project_details.append({
            'description': section[:200] + '...' if len(section) > 200 else section,
            'impact_score': impact_count,
            'complexity_score': complexity_count,
            'ownership_score': ownership_count,
            'metrics_score': metrics_count
        })
    
    # Cap quality score
    quality_score = min(quality_score, 40)
    score += quality_score
    
    # Check for STAR format (Situation, Task, Action, Result)
    star_patterns = ['challenge', 'action', 'result', 'achieved', 'outcome']
    star_count = sum(1 for pattern in star_patterns 
                    if pattern in resume_text.lower())
    score += min(star_count * 3, 15)
    
    # Apply weight
    final_score = min(score, 100) * ATS_CONFIG['weights']['project_impact']
    
    return {
        'score': round(final_score, 1),
        'project_count': project_count,
        'project_details': project_details[:3],  # Limit to top 3
        'quality_score': quality_score,
        'has_star_format': star_count >= 3
    }

def calculate_resume_quality_score(resume_text: str) -> Dict[str, Any]:
    """Calculate resume quality and presentation score"""
    score = 100  # Start with perfect score
    issues = []
    strengths = []
    
    # Check for length
    word_count = len(resume_text.split())
    if word_count < 200:
        score -= 20
        issues.append("Resume too short (less than 200 words)")
    elif word_count > 1000:
        score -= 10
        issues.append("Resume too long (over 1000 words)")
    else:
        strengths.append("Good resume length")
    
    # Check for structure
    sections = ['experience', 'education', 'skills', 'projects', 'summary']
    found_sections = sum(1 for section in sections if section in resume_text.lower())
    
    if found_sections >= 4:
        score += 10
        strengths.append("Well-structured with key sections")
    elif found_sections >= 2:
        score += 5
    else:
        score -= 15
        issues.append("Missing key resume sections")
    
    # Check for repetition
    words = resume_text.lower().split()
    word_freq = {}
    for word in words:
        if len(word) > 4:  # Only count meaningful words
            word_freq[word] = word_freq.get(word, 0) + 1
    
    repetitive_words = [word for word, count in word_freq.items() if count > 5]
    if repetitive_words:
        score -= len(repetitive_words) * 3
        issues.append(f"Repetitive words: {', '.join(repetitive_words[:3])}")
    
    # Check for vague descriptions
    vague_patterns = ['responsible for', 'duties included', 'worked on',
                     'assisted with', 'helped with', 'participated in']
    vague_count = sum(1 for pattern in vague_patterns 
                     if pattern in resume_text.lower())
    
    if vague_count > 3:
        score -= vague_count * 4
        issues.append(f"Too many vague descriptions ({vague_count} found)")
    
    # Check for action verbs (strength)
    action_verbs = ['developed', 'created', 'built', 'implemented',
                   'managed', 'led', 'optimized', 'improved',
                   'designed', 'architected', 'increased', 'decreased',
                   'saved', 'reduced', 'achieved', 'delivered']
    
    action_verb_count = sum(1 for verb in action_verbs 
                           if verb in resume_text.lower())
    
    if action_verb_count >= 8:
        score += 15
        strengths.append(f"Strong action-oriented language ({action_verb_count} action verbs)")
    elif action_verb_count >= 4:
        score += 8
        strengths.append("Good use of action verbs")
    
    # Check for metrics and quantifiable achievements
    metric_patterns = [r'\d+%', r'\$\d+', r'\d+x', r'\d+\.?\d*\s*(?:times|users|customers)',
                      r'increased by \d+', r'reduced by \d+', r'saved \$\d+']
    
    metric_count = 0
    for pattern in metric_patterns:
        metric_count += len(re.findall(pattern, resume_text, re.IGNORECASE))
    
    if metric_count >= 3:
        score += 20
        strengths.append(f"Quantifiable achievements ({metric_count} metrics)")
    elif metric_count >= 1:
        score += 10
        strengths.append("Some quantifiable achievements")
    else:
        score -= 10
        issues.append("No quantifiable achievements found")
    
    # Ensure score is within bounds
    score = max(0, min(100, score))
    
    # Apply weight
    final_score = score * ATS_CONFIG['weights']['resume_quality']
    
    return {
        'score': round(final_score, 1),
        'issues': issues,
        'strengths': strengths,
        'word_count': word_count,
        'sections_found': found_sections,
        'action_verbs': action_verb_count,
        'metrics_count': metric_count
    }

def calculate_ats_score(resume_text: str, job_description: str) -> Dict[str, Any]:
    """Calculate comprehensive ATS score with detailed breakdown"""
    
    print("🧠 Starting advanced ATS scoring...")
    
    # Extract required skills from job description
    required_skills = extract_required_skills(job_description)
    print(f"📋 Extracted {len(required_skills)} required skills")
    
    # Extract experience details
    experience_details = extract_experience_details(resume_text)
    print(f"⏳ Experience: {experience_details['total_years']} years, {experience_details['seniority']} level")
    
    # Calculate all component scores
    skills_analysis = calculate_skills_score(resume_text, required_skills)
    experience_analysis = calculate_experience_score(resume_text, job_description, experience_details)
    role_analysis = calculate_role_alignment_score(resume_text, job_description)
    project_analysis = calculate_project_impact_score(resume_text)
    resume_analysis = calculate_resume_quality_score(resume_text)
    
    # Calculate total ATS score
    total_score = (
        skills_analysis['score'] +
        experience_analysis['score'] +
        role_analysis['score'] +
        project_analysis['score'] +
        resume_analysis['score']
    )
    
    # Add small random variation to avoid clustering (0-2 points)
    random_variation = random.uniform(0, 2)
    total_score += random_variation
    
    # Ensure score is between 0-100
    total_score = max(0, min(100, total_score))
    
    # Determine recommendation
    if total_score >= 85:
        recommendation = "Strongly Recommended 🎯"
        recommendation_reason = "Exceptional match with job requirements"
    elif total_score >= 70:
        recommendation = "Recommended 👍"
        recommendation_reason = "Good match with most requirements"
    elif total_score >= 60:
        recommendation = "Consider 📊"
        recommendation_reason = "Moderate match, needs evaluation"
    elif total_score >= 50:
        recommendation = "Borderline 🤔"
        recommendation_reason = "Partial match, significant gaps"
    else:
        recommendation = "Not Recommended ❌"
        recommendation_reason = "Poor match with job requirements"
    
    # Prepare detailed breakdown
    breakdown = {
        'skills_match': {
            'score': round(skills_analysis['score'], 1),
            'weight': ATS_CONFIG['weights']['skills_match'],
            'details': {
                'matched_skills': skills_analysis['matched_skills'][:5],
                'missing_skills': skills_analysis['missing_skills'][:5],
                'context_verified': len(skills_analysis['context_verified']),
                'tool_only_mentions': skills_analysis['tool_only_mentions']
            }
        },
        'experience_relevance': {
            'score': round(experience_analysis['score'], 1),
            'weight': ATS_CONFIG['weights']['experience_relevance'],
            'details': experience_analysis
        },
        'role_alignment': {
            'score': round(role_analysis['score'], 1),
            'weight': ATS_CONFIG['weights']['role_alignment'],
            'details': role_analysis
        },
        'project_impact': {
            'score': round(project_analysis['score'], 1),
            'weight': ATS_CONFIG['weights']['project_impact'],
            'details': project_analysis
        },
        'resume_quality': {
            'score': round(resume_analysis['score'], 1),
            'weight': ATS_CONFIG['weights']['resume_quality'],
            'details': resume_analysis
        }
    }
    
    # Generate key strengths and areas for improvement
    key_strengths = []
    areas_for_improvement = []
    
    # Add strengths based on high-scoring components
    if skills_analysis['score'] > 25:
        key_strengths.append(f"Strong skills match ({skills_analysis['matched_count']}/{skills_analysis['total_required']})")
    if experience_analysis['score'] > 15:
        key_strengths.append("Relevant experience")
    if role_analysis['score'] > 15:
        key_strengths.append("Good role alignment")
    if project_analysis['project_count'] >= 3:
        key_strengths.append(f"Substantial project experience ({project_analysis['project_count']} projects)")
    
    # Add improvement areas
    if skills_analysis['missing_skills']:
        areas_for_improvement.append(f"Missing {len(skills_analysis['missing_skills'])} required skills")
    if experience_analysis.get('penalties'):
        areas_for_improvement.extend(experience_analysis['penalties'])
    if role_analysis.get('mismatches'):
        areas_for_improvement.extend(role_analysis['mismatches'])
    if resume_analysis['issues']:
        areas_for_improvement.extend(resume_analysis['issues'][:3])
    
    # Ensure we have at least some strengths/improvements
    if not key_strengths:
        key_strengths = ["Resume shows technical competency", "Clear career progression"]
    if not areas_for_improvement:
        areas_for_improvement = ["Could benefit from more quantifiable achievements", 
                               "Consider adding more project details"]
    
    result = {
        'overall_score': round(total_score, 1),
        'recommendation': recommendation,
        'recommendation_reason': recommendation_reason,
        'score_breakdown': breakdown,
        'key_strengths': key_strengths[:4],
        'areas_for_improvement': areas_for_improvement[:4],
        'skills_matched': skills_analysis['matched_skills'][:8],
        'skills_missing': skills_analysis['missing_skills'][:8],
        'experience_summary': f"{experience_details['total_years']} years experience, {experience_details['seniority']} level",
        'education_summary': "Review education section for degree relevance",
        'scoring_method': 'advanced_weighted_ats',
        'weights_applied': ATS_CONFIG['weights'],
        'timestamp': datetime.now().isoformat()
    }
    
    print(f"✅ ATS Scoring Complete: {total_score:.1f}/100 ({recommendation})")
    return result

def call_deepseek_api(prompt, max_tokens=600, temperature=0.1, timeout=45, model_override=None, retry_count=0):
    """Call DeepSeek API with optimized settings"""
    if not DEEPSEEK_API_KEY:
        print(f"❌ No DeepSeek API key configured")
        return {'error': 'no_api_key', 'status': 500}
    
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    model_to_use = model_override or DEEPSEEK_MODEL or DEFAULT_MODEL
    
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

def analyze_resume_with_ai(resume_text, job_description, filename=None, analysis_id=None):
    """Use DeepSeek API to analyze resume against job description with advanced ATS scoring"""
    
    # First, calculate advanced ATS score
    print("🔍 Calculating advanced ATS score...")
    ats_result = calculate_ats_score(resume_text, job_description)
    
    if not DEEPSEEK_API_KEY:
        print(f"❌ No DeepSeek API key configured. Using ATS score only.")
        # Enhance ATS result with basic info
        base_name = os.path.splitext(filename)[0] if filename else "Candidate"
        clean_name = base_name.replace('-', ' ').replace('_', ' ').title()
        
        result = {
            "candidate_name": clean_name if len(clean_name.split()) <= 4 else "Professional Candidate",
            "skills_matched": ats_result['skills_matched'][:5],
            "skills_missing": ats_result['skills_missing'][:5],
            "experience_summary": ats_result['experience_summary'],
            "education_summary": "Educational background requires analysis",
            "overall_score": ats_result['overall_score'],
            "recommendation": ats_result['recommendation'],
            "key_strengths": ats_result['key_strengths'],
            "areas_for_improvement": ats_result['areas_for_improvement'],
            "ats_score_breakdown": ats_result['score_breakdown'],
            "ai_provider": "ats_only",
            "ai_status": "ATS Scoring Only",
            "ai_model": "Advanced ATS Algorithm"
        }
        return result
    
    # Optimize text length
    resume_text = resume_text[:1800]
    job_description = job_description[:800]
    
    # Create detailed prompt for AI analysis
    prompt = f"""You are an expert ATS (Applicant Tracking System) analyst specializing in VLSI and Computer Science domains.

JOB DESCRIPTION:
{job_description}

CANDIDATE RESUME (truncated):
{resume_text}

BASIC ATS SCORE CALCULATION:
Overall Score: {ats_result['overall_score']}/100
Recommendation: {ats_result['recommendation']}
Reason: {ats_result['recommendation_reason']}

SCORE BREAKDOWN:
1. Skills Match: {ats_result['score_breakdown']['skills_match']['score']}/35
   - Matched Skills: {', '.join(ats_result['skills_matched'][:3]) if ats_result['skills_matched'] else 'None'}
   - Missing Skills: {', '.join(ats_result['skills_missing'][:3]) if ats_result['skills_missing'] else 'None'}

2. Experience Relevance: {ats_result['score_breakdown']['experience_relevance']['score']}/25
   - {ats_result['experience_summary']}

3. Role Alignment: {ats_result['score_breakdown']['role_alignment']['score']}/20

4. Project Impact: {ats_result['score_breakdown']['project_impact']['score']}/15

5. Resume Quality: {ats_result['score_breakdown']['resume_quality']['score']}/5

YOUR TASK:
Provide expert analysis focusing on:
1. Validate and explain the ATS score breakdown
2. Identify domain-specific strengths (VLSI/CS focus)
3. Provide detailed recommendations for improvement
4. Assess cultural and team fit indicators
5. Predict interview performance

Provide analysis in this JSON format only:
{{
    "candidate_name": "Extracted name or filename",
    "ats_score_validation": {{
        "score_accuracy": "accurate/underestimated/overestimated",
        "key_findings": ["finding1", "finding2"],
        "domain_expertise": "VLSI/CS/General",
        "seniority_assessment": "Entry/Mid/Senior"
    }},
    "detailed_analysis": {{
        "technical_depth": "Brief assessment",
        "project_complexity": "Brief assessment",
        "achievement_impact": "Brief assessment",
        "growth_potential": "Brief assessment"
    }},
    "interview_recommendations": ["rec1", "rec2"],
    "improvement_roadmap": ["step1", "step2"],
    "final_ats_score": {ats_result['overall_score']},
    "final_recommendation": "{ats_result['recommendation']}",
    "confidence_level": "high/medium/low"
}}"""

    try:
        model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
        print(f"⚡ Sending to DeepSeek API for expert analysis ({model_to_use})...")
        start_time = time.time()
        
        response = call_deepseek_api(
            prompt=prompt,
            max_tokens=800,
            temperature=0.2,
            timeout=40
        )
        
        if isinstance(response, dict) and 'error' in response:
            error_type = response.get('error')
            print(f"❌ DeepSeek API error: {error_type}")
            # Return ATS result only
            return enhance_ats_result_with_basics(ats_result, filename, "AI Analysis Failed")
        
        elapsed_time = time.time() - start_time
        print(f"✅ DeepSeek API expert analysis in {elapsed_time:.2f} seconds")
        
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
            ai_analysis = json.loads(json_str)
            print(f"✅ Successfully parsed AI analysis")
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            print(f"Response was: {result_text[:150]}")
            return enhance_ats_result_with_basics(ats_result, filename, "JSON Parse Error")
        
        # Merge ATS result with AI analysis
        final_result = merge_ats_and_ai_results(ats_result, ai_analysis, filename)
        
        # Add metadata
        final_result['ai_provider'] = "deepseek"
        final_result['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        final_result['ai_model'] = model_to_use
        final_result['response_time'] = f"{elapsed_time:.2f}s"
        final_result['analysis_id'] = analysis_id
        final_result['scoring_method'] = 'advanced_weighted_ats'
        final_result['scoring_version'] = '2.0'
        
        print(f"✅ Final analysis complete: {final_result['candidate_name']} (Score: {final_result['overall_score']})")
        
        return final_result
        
    except Exception as e:
        print(f"❌ DeepSeek Analysis Error: {str(e)}")
        return enhance_ats_result_with_basics(ats_result, filename, f"Analysis Error: {str(e)[:100]}")

def enhance_ats_result_with_basics(ats_result, filename, error_message=None):
    """Enhance ATS result with basic candidate information"""
    candidate_name = "Professional Candidate"
    
    if filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').replace('resume', '').replace('cv', '').strip()
        if clean_name:
            parts = clean_name.split()
            if len(parts) >= 2 and len(parts) <= 4:
                candidate_name = ' '.join(part.title() for part in parts)
    
    result = {
        "candidate_name": candidate_name,
        "skills_matched": ats_result['skills_matched'][:5],
        "skills_missing": ats_result['skills_missing'][:5],
        "experience_summary": ats_result['experience_summary'],
        "education_summary": "Educational background requires full analysis",
        "overall_score": ats_result['overall_score'],
        "recommendation": ats_result['recommendation'],
        "key_strengths": ats_result['key_strengths'],
        "areas_for_improvement": ats_result['areas_for_improvement'],
        "ats_score_breakdown": ats_result['score_breakdown'],
        "ai_provider": "ats_algorithm",
        "ai_status": "ATS Only - " + (error_message if error_message else "Success"),
        "ai_model": "Advanced ATS Algorithm",
        "response_time": "N/A",
        "scoring_method": 'advanced_weighted_ats',
        "scoring_version": '2.0'
    }
    
    return result

def merge_ats_and_ai_results(ats_result, ai_analysis, filename):
    """Merge ATS scoring with AI analysis"""
    candidate_name = "Professional Candidate"
    
    if filename:
        base_name = os.path.splitext(filename)[0]
        clean_name = base_name.replace('-', ' ').replace('_', ' ').replace('resume', '').replace('cv', '').strip()
        if clean_name:
            parts = clean_name.split()
            if len(parts) >= 2 and len(parts) <= 4:
                candidate_name = ' '.join(part.title() for part in parts)
    
    # Use AI's final score if provided and reasonable, otherwise use ATS score
    final_score = ats_result['overall_score']
    if 'final_ats_score' in ai_analysis and isinstance(ai_analysis['final_ats_score'], (int, float)):
        ai_score = float(ai_analysis['final_ats_score'])
        # Only use AI score if it's within 15 points of ATS score (to prevent outliers)
        if abs(ai_score - final_score) <= 15:
            final_score = (final_score * 0.7) + (ai_score * 0.3)  # Weighted average
    
    result = {
        "candidate_name": candidate_name,
        "skills_matched": ats_result['skills_matched'][:6],
        "skills_missing": ats_result['skills_missing'][:6],
        "experience_summary": ats_result['experience_summary'],
        "education_summary": "Assessed through AI analysis",
        "overall_score": round(final_score, 1),
        "recommendation": ai_analysis.get('final_recommendation', ats_result['recommendation']),
        "key_strengths": ats_result['key_strengths'][:3] + ai_analysis.get('ats_score_validation', {}).get('key_findings', [])[:2],
        "areas_for_improvement": ats_result['areas_for_improvement'][:3] + ai_analysis.get('improvement_roadmap', [])[:2],
        "ats_score_breakdown": ats_result['score_breakdown'],
        "ai_analysis": ai_analysis,
        "scoring_method": 'hybrid_ats_ai',
        "scoring_version": '2.1'
    }
    
    # Ensure arrays aren't empty
    if not result['key_strengths']:
        result['key_strengths'] = ["Technical competency", "Relevant background"]
    if not result['areas_for_improvement']:
        result['areas_for_improvement'] = ["Could add more quantifiable achievements", "Consider expanding project details"]
    
    return result

# Text extraction functions (keep the same as before)
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
        
        if len(text) > 2000:
            text = text[:2000] + "\n[Text truncated for optimal processing...]"
            
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
        
        if len(text) > 2000:
            text = text[:2000] + "\n[Text truncated for optimal processing...]"
            
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
                
                if len(text) > 2000:
                    text = text[:2000] + "\n[Text truncated for optimal processing...]"
                    
                return text
            except UnicodeDecodeError:
                continue
                
        return "Error: Could not decode text file with common encodings"
        
    except Exception as e:
        print(f"❌ TXT Error: {traceback.format_exc()}")
        return f"Error reading TXT: {str(e)}"

def process_single_resume(args):
    """Process a single resume with intelligent error handling"""
    resume_file, job_description, index, total, batch_id = args
    
    try:
        print(f"📄 Processing resume {index + 1}/{total}: {resume_file.filename}")
        
        # Add delay based on index
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
        
        # Analyze with advanced ATS + DeepSeek API
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

# Flask routes (keep the same structure but updated for new scoring)
@app.route('/')
def home():
    """Root route - API landing page"""
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    warmup_status = "✅ Ready" if warmup_complete else "🔥 Warming up..."
    model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Advanced Resume Analyzer API</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; padding: 0; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #333; }}
            .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .ready {{ background: #d4edda; color: #155724; }}
            .warming {{ background: #fff3cd; color: #856404; }}
            .endpoint {{ background: #f8f9fa; padding: 10px; margin: 10px 0; border-left: 4px solid #007bff; }}
            .feature-list {{ list-style: none; padding: 0; }}
            .feature-list li {{ padding: 5px 0; }}
            .feature-list li:before {{ content: "✅ "; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Advanced Resume Analyzer API</h1>
            <p>AI-powered resume analysis with weighted ATS scoring</p>
            
            <div class="status {'ready' if warmup_complete else 'warming'}">
                <strong>Status:</strong> {warmup_status}
            </div>
            
            <p><strong>Model:</strong> {model_to_use}</p>
            <p><strong>API Provider:</strong> DeepSeek + Advanced ATS Algorithm</p>
            <p><strong>Max Batch Size:</strong> {MAX_BATCH_SIZE} resumes</p>
            <p><strong>ATS Scoring:</strong> Weighted Multi-Dimensional</p>
            
            <h2>📊 Advanced ATS Scoring Features</h2>
            <ul class="feature-list">
                <li>Weighted scoring across 5 dimensions</li>
                <li>VLSI and CS domain expertise detection</li>
                <li>Context-aware skill matching</li>
                <li>Seniority alignment assessment</li>
                <li>Project impact evaluation</li>
                <li>Resume quality analysis</li>
                <li>Realistic score distribution (0-100)</li>
                <li>Detailed score breakdown</li>
            </ul>
            
            <h2>📡 Endpoints</h2>
            <div class="endpoint">
                <strong>POST /analyze</strong> - Analyze single resume with advanced ATS
            </div>
            <div class="endpoint">
                <strong>POST /analyze-batch</strong> - Analyze multiple resumes (up to {MAX_BATCH_SIZE})
            </div>
            <div class="endpoint">
                <strong>GET /health</strong> - Health check with ATS configuration
            </div>
            <div class="endpoint">
                <strong>GET /ping</strong> - Keep-alive ping
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Main endpoint to analyze single resume with advanced ATS"""
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
        
        # Check file size
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
        
        # Analyze with Advanced ATS + DeepSeek API
        model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
        print(f"⚡ Starting Advanced ATS + DeepSeek API analysis ({model_to_use})...")
        ai_start = time.time()
        
        analysis_id = f"single_{timestamp}"
        analysis = analyze_resume_with_ai(resume_text, job_description, resume_file.filename, analysis_id)
        ai_time = time.time() - ai_start
        
        print(f"✅ Advanced ATS analysis completed in {ai_time:.2f}s")
        
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
        analysis['ai_provider'] = "deepseek_advanced_ats"
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['response_time'] = f"{ai_time:.2f}s"
        analysis['analysis_id'] = analysis_id
        analysis['scoring_method'] = 'advanced_weighted_ats'
        
        total_time = time.time() - start_time
        print(f"✅ Request completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

@app.route('/analyze-batch', methods=['POST'])
def analyze_resume_batch():
    """Analyze multiple resumes with advanced ATS scoring"""
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
        
        if len(resume_files) > MAX_BATCH_SIZE:
            print(f"❌ Too many files: {len(resume_files)} (max: {MAX_BATCH_SIZE})")
            return jsonify({'error': f'Maximum {MAX_BATCH_SIZE} resumes allowed per batch'}), 400
        
        # Check API configuration
        if not DEEPSEEK_API_KEY:
            print("❌ No DeepSeek API key configured")
            return jsonify({'error': 'DeepSeek API not configured'}), 500
        
        # Prepare batch analysis
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        
        # Process resumes sequentially
        all_analyses = []
        errors = []
        
        print(f"🔄 Processing {len(resume_files)} resumes sequentially...")
        
        for index, resume_file in enumerate(resume_files):
            if resume_file.filename == '':
                errors.append({
                    'filename': 'Empty file',
                    'error': 'File has no name',
                    'index': index
                })
                continue
            
            print(f"🔑 Processing resume {index + 1}/{len(resume_files)}")
            
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
            
            # Add delay between processing
            if index < len(resume_files) - 1:
                delay = 1.0 + random.uniform(0, 0.5)
                print(f"⏳ Adding {delay:.1f}s delay before next resume...")
                time.sleep(delay)
        
        print(f"\n📊 Batch processing complete. Successful: {len(all_analyses)}, Failed: {len(errors)}")
        
        # Sort by score
        all_analyses.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        # Add ranking
        for rank, analysis in enumerate(all_analyses, 1):
            analysis['rank'] = rank
        
        # Create batch Excel report
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
            'model_used': DEEPSEEK_MODEL or DEFAULT_MODEL,
            'ai_provider': "deepseek_advanced_ats",
            'ai_status': "Warmed up" if warmup_complete else "Warming up",
            'processing_time': f"{time.time() - start_time:.2f}s",
            'job_description_preview': job_description[:200] + ("..." if len(job_description) > 200 else ""),
            'batch_size': len(resume_files),
            'max_batch_size': MAX_BATCH_SIZE,
            'processing_method': 'staggered_sequential',
            'success_rate': f"{(len(all_analyses) / len(resume_files)) * 100:.1f}%" if resume_files else "0%",
            'scoring_method': 'advanced_weighted_ats'
        }
        
        print(f"✅ Batch analysis completed in {time.time() - start_time:.2f}s")
        print("="*50 + "\n")
        
        return jsonify(batch_summary)
        
    except Exception as e:
        print(f"❌ Batch analysis error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

def create_excel_report(analysis_data, filename="resume_analysis_report.xlsx"):
    """Create an Excel report with detailed ATS breakdown"""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "ATS Analysis"
        
        # Styles
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        section_fill = PatternFill(start_color="E8F4FD", end_color="E8F4FD", fill_type="solid")
        section_font = Font(bold=True, color="2E5984", size=11)
        
        # Column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 50
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 20
        
        row = 1
        
        # Title
        ws.merge_cells(f'A{row}:D{row}')
        cell = ws[f'A{row}']
        cell.value = "ADVANCED ATS RESUME ANALYSIS REPORT"
        cell.font = Font(bold=True, size=16, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        row += 2
        
        # Candidate Information
        ws[f'A{row}'] = "Candidate Name"
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = analysis_data.get('candidate_name', 'N/A')
        ws[f'C{row}'] = "ATS Score"
        ws[f'C{row}'].font = Font(bold=True)
        ws[f'D{row}'] = analysis_data.get('overall_score', 0)
        ws[f'D{row}'].font = Font(bold=True, size=14)
        
        # Color code score
        score = analysis_data.get('overall_score', 0)
        if score >= 80:
            ws[f'D{row}'].font = Font(bold=True, size=14, color="00B050")  # Green
        elif score >= 60:
            ws[f'D{row}'].font = Font(bold=True, size=14, color="FFC000")  # Orange
        else:
            ws[f'D{row}'].font = Font(bold=True, size=14, color="FF0000")  # Red
        
        row += 1
        
        ws[f'A{row}'] = "Analysis Date"
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws[f'C{row}'] = "Recommendation"
        ws[f'C{row}'].font = Font(bold=True)
        ws[f'D{row}'] = analysis_data.get('recommendation', 'N/A')
        row += 1
        
        ws[f'A{row}'] = "AI Model"
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = analysis_data.get('ai_model', 'Advanced ATS Algorithm')
        ws[f'C{row}'] = "Scoring Method"
        ws[f'C{row}'].font = Font(bold=True)
        ws[f'D{row}'] = analysis_data.get('scoring_method', 'advanced_weighted_ats').replace('_', ' ').title()
        row += 2
        
        # ATS Score Breakdown Section
        ws.merge_cells(f'A{row}:D{row}')
        cell = ws[f'A{row}']
        cell.value = "ATS SCORE BREAKDOWN (Weighted Multi-Dimensional)"
        cell.font = section_font
        cell.fill = section_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        # Add breakdown headers
        ws[f'A{row}'] = "Component"
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = "Description"
        ws[f'B{row}'].font = Font(bold=True)
        ws[f'C{row}'] = "Score"
        ws[f'C{row}'].font = Font(bold=True)
        ws[f'D{row}'] = "Weight"
        ws[f'D{row}'].font = Font(bold=True)
        row += 1
        
        # Add breakdown details
        breakdown = analysis_data.get('ats_score_breakdown', {})
        components = [
            ('skills_match', 'Skills Match', 'Technical skills alignment with context verification'),
            ('experience_relevance', 'Experience Relevance', 'Years and seniority alignment'),
            ('role_alignment', 'Role Alignment', 'Domain and responsibility match'),
            ('project_impact', 'Project Impact', 'Complexity and measurable achievements'),
            ('resume_quality', 'Resume Quality', 'Structure, clarity, and presentation')
        ]
        
        for component_key, component_name, description in components:
            if component_key in breakdown:
                component = breakdown[component_key]
                ws[f'A{row}'] = component_name
                ws[f'B{row}'] = description
                ws[f'C{row}'] = component.get('score', 0)
                ws[f'D{row}'] = f"{component.get('weight', 0)*100:.0f}%"
                row += 1
        
        row += 1
        
        # Skills Analysis
        ws.merge_cells(f'A{row}:D{row}')
        cell = ws[f'A{row}']
        cell.value = "SKILLS ANALYSIS"
        cell.font = section_font
        cell.fill = section_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        # Matched Skills
        ws[f'A{row}'] = "Matched Skills"
        ws[f'A{row}'].font = Font(bold=True, color="00B050")
        row += 1
        
        skills_matched = analysis_data.get('skills_matched', [])
        if skills_matched:
            for i, skill in enumerate(skills_matched[:10], 1):
                ws[f'B{row}'] = f"{i}. {skill}"
                row += 1
        else:
            ws[f'B{row}'] = "No matched skills detected"
            row += 1
        
        row += 1
        
        # Missing Skills
        ws[f'A{row}'] = "Missing Skills"
        ws[f'A{row}'].font = Font(bold=True, color="FF0000")
        row += 1
        
        skills_missing = analysis_data.get('skills_missing', [])
        if skills_missing:
            for i, skill in enumerate(skills_missing[:10], 1):
                ws[f'B{row}'] = f"{i}. {skill}"
                row += 1
        else:
            ws[f'B{row}'] = "All required skills are present!"
            row += 1
        
        row += 2
        
        # Key Strengths
        ws.merge_cells(f'A{row}:D{row}')
        cell = ws[f'A{row}']
        cell.value = "KEY STRENGTHS"
        cell.font = section_font
        cell.fill = section_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        strengths = analysis_data.get('key_strengths', [])
        if strengths:
            for i, strength in enumerate(strengths, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'B{row}'] = strength
                ws.merge_cells(f'B{row}:D{row}')
                row += 1
        else:
            ws[f'A{row}'] = "No specific strengths identified"
            ws.merge_cells(f'A{row}:D{row}')
            row += 1
        
        row += 1
        
        # Areas for Improvement
        ws.merge_cells(f'A{row}:D{row}')
        cell = ws[f'A{row}']
        cell.value = "AREAS FOR IMPROVEMENT"
        cell.font = section_font
        cell.fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        improvements = analysis_data.get('areas_for_improvement', [])
        if improvements:
            for i, improvement in enumerate(improvements, 1):
                ws[f'A{row}'] = f"{i}."
                ws[f'B{row}'] = improvement
                ws.merge_cells(f'B{row}:D{row}')
                row += 1
        else:
            ws[f'A{row}'] = "No specific areas for improvement identified"
            ws.merge_cells(f'A{row}:D{row}')
            row += 1
        
        row += 2
        
        # Summary
        ws.merge_cells(f'A{row}:D{row}')
        cell = ws[f'A{row}']
        cell.value = "SUMMARY"
        cell.font = section_font
        cell.fill = section_fill
        cell.alignment = Alignment(horizontal='center')
        row += 1
        
        ws.merge_cells(f'A{row}:D{row}')
        cell = ws[f'A{row}']
        cell.value = analysis_data.get('experience_summary', 'No experience summary available.')
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[row].height = 40
        row += 1
        
        ws.merge_cells(f'A{row}:D{row}')
        cell = ws[f'A{row}']
        cell.value = analysis_data.get('education_summary', 'No education summary available.')
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[row].height = 30
        
        # Save the file
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📄 Excel report saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error creating Excel report: {str(e)}")
        return os.path.join(REPORTS_FOLDER, f"fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

def create_batch_excel_report(analyses, job_description, filename="batch_resume_analysis.xlsx"):
    """Create a comprehensive batch Excel report with ATS details"""
    try:
        wb = Workbook()
        
        # Summary Sheet
        ws_summary = wb.active
        ws_summary.title = "Batch Summary"
        
        # Header styles
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        section_fill = PatternFill(start_color="E8F4FD", end_color="E8F4FD", fill_type="solid")
        
        # Title
        ws_summary.merge_cells('A1:H1')
        title_cell = ws_summary['A1']
        title_cell.value = "BATCH ATS RESUME ANALYSIS REPORT"
        title_cell.font = Font(bold=True, size=16, color="FFFFFF")
        title_cell.fill = header_fill
        title_cell.alignment = Alignment(horizontal='center')
        
        # Summary Information
        ws_summary['A3'] = "Analysis Date"
        ws_summary['B3'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws_summary['A4'] = "Total Resumes"
        ws_summary['B4'] = len(analyses)
        ws_summary['A5'] = "AI Model"
        ws_summary['B5'] = analyses[0].get('ai_model', 'Advanced ATS Algorithm') if analyses else 'N/A'
        ws_summary['A6'] = "Scoring Method"
        ws_summary['B6'] = "Weighted Multi-Dimensional ATS"
        ws_summary['A7'] = "Success Rate"
        success_rate = f"{(len(analyses) / len(analyses)) * 100:.1f}%" if analyses else "100%"
        ws_summary['B7'] = success_rate
        ws_summary['A8'] = "Job Description Preview"
        ws_summary['B8'] = job_description[:200] + ("..." if len(job_description) > 200 else "")
        ws_summary['B8'].alignment = Alignment(wrap_text=True)
        ws_summary.row_dimensions[8].height = 40
        
        # Candidates Ranking Table
        row = 10
        headers = ["Rank", "Candidate Name", "ATS Score", "Recommendation", "Skills Match", "Experience", "Role Alignment", "Project Impact"]
        for col, header in enumerate(headers, start=1):
            cell = ws_summary.cell(row=row, column=col)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
        
        row += 1
        for analysis in analyses:
            breakdown = analysis.get('ats_score_breakdown', {})
            
            ws_summary.cell(row=row, column=1, value=analysis.get('rank', '-'))
            ws_summary.cell(row=row, column=2, value=analysis.get('candidate_name', 'Unknown'))
            
            # Color code ATS score
            score_cell = ws_summary.cell(row=row, column=3, value=analysis.get('overall_score', 0))
            score = analysis.get('overall_score', 0)
            if score >= 80:
                score_cell.font = Font(bold=True, color="00B050")
            elif score >= 60:
                score_cell.font = Font(bold=True, color="FFC000")
            else:
                score_cell.font = Font(bold=True, color="FF0000")
            
            ws_summary.cell(row=row, column=4, value=analysis.get('recommendation', 'N/A'))
            
            # Component scores
            ws_summary.cell(row=row, column=5, value=breakdown.get('skills_match', {}).get('score', 0))
            ws_summary.cell(row=row, column=6, value=breakdown.get('experience_relevance', {}).get('score', 0))
            ws_summary.cell(row=row, column=7, value=breakdown.get('role_alignment', {}).get('score', 0))
            ws_summary.cell(row=row, column=8, value=breakdown.get('project_impact', {}).get('score', 0))
            
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
            adjusted_width = min(max_length + 2, 40)
            ws_summary.column_dimensions[column_letter].width = adjusted_width
        
        # Create individual candidate sheets
        for i, analysis in enumerate(analyses[:5]):  # Limit to first 5 for performance
            ws_candidate = wb.create_sheet(title=f"Candidate {i+1}")
            
            # Candidate header
            ws_candidate.merge_cells('A1:D1')
            title_cell = ws_candidate['A1']
            title_cell.value = f"CANDIDATE: {analysis.get('candidate_name', 'Unknown')}"
            title_cell.font = Font(bold=True, size=14)
            title_cell.alignment = Alignment(horizontal='center')
            
            # Basic info
            ws_candidate['A3'] = "ATS Score"
            ws_candidate['B3'] = analysis.get('overall_score', 0)
            ws_candidate['A4'] = "Rank"
            ws_candidate['B4'] = analysis.get('rank', i+1)
            ws_candidate['A5'] = "Recommendation"
            ws_candidate['B5'] = analysis.get('recommendation', 'N/A')
            
            # Skills
            ws_candidate['A7'] = "Matched Skills"
            ws_candidate['A7'].font = Font(bold=True)
            row = 8
            for skill in analysis.get('skills_matched', [])[:5]:
                ws_candidate[f'A{row}'] = f"• {skill}"
                row += 1
            
            ws_candidate['C7'] = "Missing Skills"
            ws_candidate['C7'].font = Font(bold=True)
            row = 8
            for skill in analysis.get('skills_missing', [])[:5]:
                ws_candidate[f'C{row}'] = f"• {skill}"
                row += 1
        
        # Save the file
        filepath = os.path.join(REPORTS_FOLDER, filename)
        wb.save(filepath)
        print(f"📊 Batch Excel report saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error creating batch Excel report: {str(e)}")
        filepath = os.path.join(REPORTS_FOLDER, f"batch_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb = Workbook()
        ws = wb.active
        ws['A1'] = "Batch Analysis Report"
        ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws['A3'] = f"Total Candidates: {len(analyses)}"
        wb.save(filepath)
        return filepath

# Keep the rest of the Flask routes (download, health, ping, warmup, etc.) the same as before
# Only change the health endpoint to include ATS configuration

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with ATS configuration"""
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
    
    return jsonify({
        'status': 'Service is running', 
        'timestamp': datetime.now().isoformat(),
        'ai_provider': 'deepseek_advanced_ats',
        'ai_provider_configured': bool(DEEPSEEK_API_KEY),
        'model': model_to_use,
        'ai_warmup_complete': warmup_complete,
        'ats_configuration': {
            'method': 'weighted_multi_dimensional',
            'version': '2.0',
            'weights': ATS_CONFIG['weights'],
            'domains_supported': ['VLSI', 'CS', 'General'],
            'features': ['context_aware_scoring', 'seniority_alignment', 'project_impact', 'resume_quality']
        },
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'reports_folder_exists': os.path.exists(REPORTS_FOLDER),
        'inactive_minutes': inactive_minutes,
        'version': '2.0.0',
        'optimizations': ['advanced_ats_scoring', 'domain_specific', 'weighted_evaluation', 'context_aware'],
        'configuration': {
            'max_batch_size': MAX_BATCH_SIZE,
            'max_concurrent_requests': MAX_CONCURRENT_REQUESTS,
            'max_retries': MAX_RETRIES,
            'max_individual_reports': MAX_INDIVIDUAL_REPORTS
        },
        'processing_method': 'staggered_sequential_with_advanced_ats'
    })

# The rest of the Flask routes remain the same...
# Keep all the existing routes: /download, /download-individual, /warmup, /quick-check, /ping
# Only update the home and health endpoints as shown above

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
            time.sleep(180)
            
            if DEEPSEEK_API_KEY and warmup_complete:
                print(f"♨️ Keeping DeepSeek warm...")
                
                try:
                    response = call_deepseek_api(
                        prompt="Ping - just say 'pong'",
                        max_tokens=5,
                        timeout=20
                    )
                    if response and 'pong' in str(response).lower():
                        print(f"  ✅ DeepSeek keep-alive successful")
                    else:
                        print(f"  ⚠️ DeepSeek keep-alive got unexpected response")
                except Exception as e:
                    print(f"  ⚠️ DeepSeek keep-alive failed: {str(e)}")
                    
        except Exception as e:
            print(f"⚠️ Keep-warm thread error: {str(e)}")
            time.sleep(180)

def cleanup_on_exit():
    """Cleanup function called on exit"""
    global service_running
    service_running = False
    print("\n🛑 Shutting down service...")
    
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
    print("🚀 Advanced Resume Analyzer Backend Starting...")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"⚡ AI Provider: DeepSeek + Advanced ATS Algorithm")
    model_to_use = DEEPSEEK_MODEL or DEFAULT_MODEL
    print(f"🤖 Model: {model_to_use}")
    print(f"🔑 API Key: {'Configured' if DEEPSEEK_API_KEY else 'Not configured'}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📁 Reports folder: {REPORTS_FOLDER}")
    print(f"✅ Advanced ATS Scoring: Enabled")
    print(f"✅ Weighted Multi-Dimensional: {ATS_CONFIG['weights']}")
    print(f"✅ VLSI/CS Domain Expertise: Enabled")
    print(f"✅ Context-Aware Skill Matching: Enabled")
    print(f"✅ Max Batch Size: {MAX_BATCH_SIZE} resumes")
    print("="*50 + "\n")
    
    if not DEEPSEEK_API_KEY:
        print("⚠️  WARNING: No DeepSeek API key found!")
        print("Please set DEEPSEEK_API_KEY in Render environment variables")
        print("ATS scoring will work without AI enhancement")
    
    # Enable garbage collection
    gc.enable()
    
    # Start warm-up in background
    if DEEPSEEK_API_KEY:
        warmup_thread = threading.Thread(target=warmup_deepseek_service, daemon=True)
        warmup_thread.start()
        
        # Start keep-warm thread
        keep_warm_thread = threading.Thread(target=keep_service_warm, daemon=True)
        keep_warm_thread.start()
        
        print("✅ Background threads started")
    
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode, threaded=True)
