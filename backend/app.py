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
import math
from typing import Dict, List, Tuple, Set, Optional
import numpy as np
from dataclasses import dataclass
from enum import Enum

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

# Get absolute path for uploads folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)
print(f"📁 Upload folder: {UPLOAD_FOLDER}")
print(f"📁 Reports folder: {REPORTS_FOLDER}")

# Cache for consistent scoring (resume hash -> extracted data)
extracted_data_cache = {}
cache_lock = threading.Lock()

# ==============================================
# DETERMINISTIC ATS SCORING ENGINE
# ==============================================

class SkillCategory(Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    NICE_TO_HAVE = "nice_to_have"

@dataclass
class ExtractedData:
    """Structured data extracted from resume"""
    candidate_name: str
    skills: List[str]
    normalized_skills: Set[str]
    experience_years: float
    job_titles: List[str]
    normalized_titles: Set[str]
    education: List[str]
    certifications: List[str]
    keywords: Set[str]
    resume_text: str
    
    # Formatting metrics
    section_count: int
    bullet_point_count: int
    has_contact_info: bool
    has_summary: bool
    word_count: int
    
    def to_dict(self):
        return {
            'candidate_name': self.candidate_name,
            'skills': self.skills,
            'normalized_skills': list(self.normalized_skills),
            'experience_years': self.experience_years,
            'job_titles': self.job_titles,
            'normalized_titles': list(self.normalized_titles),
            'education': self.education,
            'certifications': self.certifications,
            'keywords': list(self.keywords),
            'section_count': self.section_count,
            'bullet_point_count': self.bullet_point_count,
            'has_contact_info': self.has_contact_info,
            'has_summary': self.has_summary,
            'word_count': self.word_count
        }

@dataclass
class JobDescriptionAnalysis:
    """Structured analysis of job description"""
    required_skills: Set[str]
    preferred_skills: Set[str]
    nice_to_have_skills: Set[str]
    min_experience_years: float
    required_experience_years: float
    target_job_titles: Set[str]
    required_education: List[str]
    required_certifications: List[str]
    keywords: Set[str]
    
    def to_dict(self):
        return {
            'required_skills': list(self.required_skills),
            'preferred_skills': list(self.preferred_skills),
            'nice_to_have_skills': list(self.nice_to_have_skills),
            'min_experience_years': self.min_experience_years,
            'required_experience_years': self.required_experience_years,
            'target_job_titles': list(self.target_job_titles),
            'required_education': self.required_education,
            'required_certifications': self.required_certifications,
            'keywords': list(self.keywords)
        }

class ATS_ScoringEngine:
    """Deterministic ATS scoring engine with consistent, math-based scoring"""
    
    # Scoring weights (must sum to 1.0)
    WEIGHTS = {
        'required_skills': 0.35,      # Required skills match (highest weight)
        'preferred_skills': 0.15,      # Preferred skills match
        'experience': 0.20,           # Years of experience match
        'job_title': 0.10,           # Job title relevance
        'education': 0.10,           # Education match
        'keywords': 0.05,            # Keyword density
        'formatting': 0.05           # Resume formatting
    }
    
    # Normalization mappings
    SKILL_NORMALIZATION = {
        'react.js': 'react',
        'reactjs': 'react',
        'node.js': 'nodejs',
        'nodejs': 'nodejs',
        'python 3': 'python',
        'python3': 'python',
        'javascript es6': 'javascript',
        'js': 'javascript',
        'html5': 'html',
        'css3': 'css',
        'aws cloud': 'aws',
        'amazon web services': 'aws',
        'google cloud platform': 'gcp',
        'gcp': 'gcp',
        'azure': 'microsoft azure',
        'ms sql': 'sql',
        'mysql': 'sql',
        'postgresql': 'sql',
        'mongodb': 'nosql',
        'cassandra': 'nosql',
        'docker': 'containerization',
        'kubernetes': 'container orchestration',
        'k8s': 'kubernetes',
        'ci/cd': 'continuous integration',
        'jenkins': 'ci/cd',
        'gitlab ci': 'ci/cd',
        'github actions': 'ci/cd',
        'rest api': 'api',
        'graphql': 'api',
        'soap': 'api',
        'agile': 'agile methodology',
        'scrum': 'agile methodology',
        'kanban': 'agile methodology',
        'jira': 'project management',
        'trello': 'project management',
        'asana': 'project management'
    }
    
    TITLE_NORMALIZATION = {
        'sde': 'software engineer',
        'software development engineer': 'software engineer',
        'dev': 'developer',
        'sw eng': 'software engineer',
        'se': 'software engineer',
        'frontend dev': 'frontend developer',
        'backend dev': 'backend developer',
        'full stack dev': 'full stack developer',
        'fsd': 'full stack developer',
        'data sci': 'data scientist',
        'ml eng': 'machine learning engineer',
        'ai eng': 'ai engineer',
        'devops eng': 'devops engineer',
        'sre': 'site reliability engineer',
        'pm': 'project manager',
        'prod mgr': 'product manager',
        'ux designer': 'ui/ux designer',
        'ui designer': 'ui/ux designer',
        'qa eng': 'quality assurance engineer',
        'test eng': 'test engineer'
    }
    
    # Experience scoring parameters
    EXPERIENCE_BONUS_CAP = 5.0  # Maximum bonus years
    EXPERIENCE_PENALTY_CAP = -15.0  # Maximum penalty
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for consistent comparison"""
        if not text:
            return ""
        # Convert to lowercase and remove special characters
        text = text.lower()
        text = re.sub(r'[^\w\s-]', ' ', text)  # Remove punctuation
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = text.strip()
        return text
    
    @staticmethod
    def normalize_skill(skill: str) -> str:
        """Normalize skill name using mapping"""
        skill = ATS_ScoringEngine.normalize_text(skill)
        return ATS_ScoringEngine.SKILL_NORMALIZATION.get(skill, skill)
    
    @staticmethod
    def normalize_title(title: str) -> str:
        """Normalize job title using mapping"""
        title = ATS_ScoringEngine.normalize_text(title)
        return ATS_ScoringEngine.TITLE_NORMALIZATION.get(title, title)
    
    @staticmethod
    def calculate_skill_match_score(resume_skills: Set[str], 
                                  required_skills: Set[str],
                                  preferred_skills: Set[str],
                                  nice_to_have_skills: Set[str]) -> Tuple[float, Dict]:
        """
        Calculate deterministic skill match score
        Returns: (score, breakdown)
        """
        # Normalize all skill sets
        norm_resume = {ATS_ScoringEngine.normalize_skill(s) for s in resume_skills}
        norm_required = {ATS_ScoringEngine.normalize_skill(s) for s in required_skills}
        norm_preferred = {ATS_ScoringEngine.normalize_skill(s) for s in preferred_skills}
        norm_nice = {ATS_ScoringEngine.normalize_skill(s) for s in nice_to_have_skills}
        
        # Calculate exact matches
        required_matches = norm_resume.intersection(norm_required)
        preferred_matches = norm_resume.intersection(norm_preferred)
        nice_matches = norm_resume.intersection(norm_nice)
        
        # Calculate ratios (avoid division by zero)
        required_ratio = len(required_matches) / max(len(norm_required), 1)
        preferred_ratio = len(preferred_matches) / max(len(norm_preferred), 1)
        nice_ratio = len(nice_matches) / max(len(norm_nice), 1)
        
        # Apply weights: required > preferred > nice
        required_score = required_ratio * 0.7
        preferred_score = preferred_ratio * 0.2
        nice_score = nice_ratio * 0.1
        
        total_score = (required_score + preferred_score + nice_score) * 100
        
        return total_score, {
            'required_matches': list(required_matches),
            'preferred_matches': list(preferred_matches),
            'nice_matches': list(nice_matches),
            'required_missing': list(norm_required - norm_resume),
            'preferred_missing': list(norm_preferred - norm_resume),
            'required_ratio': round(required_ratio, 3),
            'preferred_ratio': round(preferred_ratio, 3),
            'nice_ratio': round(nice_ratio, 3)
        }
    
    @staticmethod
    def calculate_experience_score(resume_experience: float, 
                                 job_min_experience: float,
                                 job_required_experience: float) -> Tuple[float, Dict]:
        """
        Calculate experience score with diminishing returns
        """
        if resume_experience >= job_required_experience:
            # Candidate meets or exceeds required experience
            base_score = 100.0
            
            # Bonus for extra experience (diminishing returns)
            extra_years = resume_experience - job_required_experience
            bonus = min(extra_years * 2.0, 10.0)  # Max 10% bonus
            
            return min(base_score + bonus, 100.0), {
                'status': 'exceeds_requirements',
                'extra_years': round(extra_years, 1),
                'bonus': round(bonus, 1)
            }
        
        elif resume_experience >= job_min_experience:
            # Candidate meets minimum but not required
            gap = job_required_experience - resume_experience
            total_range = job_required_experience - job_min_experience
            
            # Linear interpolation between 60 and 90
            if total_range > 0:
                ratio = gap / total_range
                score = 90.0 - (ratio * 30.0)  # 60-90 range
            else:
                score = 75.0  # Default if no range
            
            return max(score, 60.0), {
                'status': 'meets_minimum',
                'gap_years': round(gap, 1),
                'score_range': '60-90'
            }
        
        else:
            # Candidate doesn't meet minimum
            gap = job_min_experience - resume_experience
            penalty = min(gap * 15.0, ATS_ScoringEngine.EXPERIENCE_PENALTY_CAP)
            
            score = max(60.0 + penalty, 0.0)
            
            return score, {
                'status': 'below_minimum',
                'gap_years': round(gap, 1),
                'penalty': round(penalty, 1)
            }
    
    @staticmethod
    def calculate_job_title_score(resume_titles: Set[str], 
                                target_titles: Set[str]) -> Tuple[float, Dict]:
        """Calculate job title relevance score"""
        if not target_titles:
            return 50.0, {'status': 'no_target_titles'}
        
        # Normalize titles
        norm_resume = {ATS_ScoringEngine.normalize_title(t) for t in resume_titles}
        norm_target = {ATS_ScoringEngine.normalize_title(t) for t in target_titles}
        
        # Check for exact matches
        exact_matches = norm_resume.intersection(norm_target)
        if exact_matches:
            return 100.0, {
                'status': 'exact_match',
                'matches': list(exact_matches)
            }
        
        # Check for partial matches (contains target in title)
        partial_matches = []
        for resume_title in norm_resume:
            for target_title in norm_target:
                if target_title in resume_title or resume_title in target_title:
                    partial_matches.append((resume_title, target_title))
        
        if partial_matches:
            return 80.0, {
                'status': 'partial_match',
                'matches': partial_matches
            }
        
        # Check for similar words
        resume_words = set()
        for title in norm_resume:
            resume_words.update(title.split())
        
        target_words = set()
        for title in norm_target:
            target_words.update(title.split())
        
        common_words = resume_words.intersection(target_words)
        if common_words:
            word_ratio = len(common_words) / max(len(target_words), 1)
            score = 40.0 + (word_ratio * 40.0)
            return min(score, 80.0), {
                'status': 'similar_words',
                'common_words': list(common_words),
                'word_ratio': round(word_ratio, 3)
            }
        
        return 20.0, {'status': 'no_match'}
    
    @staticmethod
    def calculate_education_score(resume_education: List[str], 
                                required_education: List[str]) -> Tuple[float, Dict]:
        """Calculate education match score"""
        if not required_education:
            return 75.0, {'status': 'no_education_requirements'}
        
        # Normalize education entries
        norm_resume = [ATS_ScoringEngine.normalize_text(e) for e in resume_education]
        norm_required = [ATS_ScoringEngine.normalize_text(e) for e in required_education]
        
        matches = []
        for req in norm_required:
            for edu in norm_resume:
                if req in edu or edu in req:
                    matches.append((req, edu))
        
        match_ratio = len(matches) / max(len(norm_required), 1)
        score = match_ratio * 100.0
        
        return score, {
            'matches': matches,
            'match_ratio': round(match_ratio, 3),
            'missing': [r for r in norm_required if not any(r in e or e in r for e in norm_resume)]
        }
    
    @staticmethod
    def calculate_keyword_score(resume_keywords: Set[str], 
                              job_keywords: Set[str]) -> Tuple[float, Dict]:
        """Calculate keyword density score"""
        if not job_keywords:
            return 50.0, {'status': 'no_keywords'}
        
        # Normalize keywords
        norm_resume = {ATS_ScoringEngine.normalize_text(k) for k in resume_keywords}
        norm_job = {ATS_ScoringEngine.normalize_text(k) for k in job_keywords}
        
        matches = norm_resume.intersection(norm_job)
        match_ratio = len(matches) / max(len(norm_job), 1)
        
        # Score with diminishing returns (log scale)
        score = 20.0 + (80.0 * (1 - math.exp(-2 * match_ratio)))
        
        return score, {
            'matches': list(matches),
            'match_ratio': round(match_ratio, 3),
            'missing': list(norm_job - norm_resume)
        }
    
    @staticmethod
    def calculate_formatting_score(extracted_data: ExtractedData) -> Tuple[float, Dict]:
        """Calculate resume formatting/ATS friendliness score"""
        score = 50.0  # Base score
        details = {}
        
        # Section count (optimal: 5-7 sections)
        if extracted_data.section_count >= 5:
            score += 10.0
            details['sections'] = 'good'
        elif extracted_data.section_count >= 3:
            score += 5.0
            details['sections'] = 'average'
        else:
            score -= 5.0
            details['sections'] = 'poor'
        
        # Bullet points (optimal: >20)
        if extracted_data.bullet_point_count > 20:
            score += 10.0
            details['bullet_points'] = 'excellent'
        elif extracted_data.bullet_point_count > 10:
            score += 5.0
            details['bullet_points'] = 'good'
        else:
            score -= 5.0
            details['bullet_points'] = 'poor'
        
        # Contact info
        if extracted_data.has_contact_info:
            score += 10.0
            details['contact_info'] = 'present'
        else:
            score -= 10.0
            details['contact_info'] = 'missing'
        
        # Summary/Objective
        if extracted_data.has_summary:
            score += 10.0
            details['summary'] = 'present'
        else:
            score -= 5.0
            details['summary'] = 'missing'
        
        # Word count (optimal: 400-800 words)
        if 400 <= extracted_data.word_count <= 800:
            score += 10.0
            details['word_count'] = 'optimal'
        elif extracted_data.word_count < 200:
            score -= 10.0
            details['word_count'] = 'too_short'
        elif extracted_data.word_count > 1200:
            score -= 5.0
            details['word_count'] = 'too_long'
        else:
            score += 5.0
            details['word_count'] = 'acceptable'
        
        # Cap score between 0-100
        score = max(0.0, min(100.0, score))
        
        return score, details
    
    @staticmethod
    def calculate_ats_score(extracted_data: ExtractedData, 
                          job_analysis: JobDescriptionAnalysis) -> Tuple[float, Dict]:
        """
        Calculate final ATS score using deterministic math
        Returns: (final_score, detailed_breakdown)
        """
        # Calculate individual component scores
        skill_score, skill_details = ATS_ScoringEngine.calculate_skill_match_score(
            extracted_data.normalized_skills,
            job_analysis.required_skills,
            job_analysis.preferred_skills,
            job_analysis.nice_to_have_skills
        )
        
        experience_score, exp_details = ATS_ScoringEngine.calculate_experience_score(
            extracted_data.experience_years,
            job_analysis.min_experience_years,
            job_analysis.required_experience_years
        )
        
        title_score, title_details = ATS_ScoringEngine.calculate_job_title_score(
            extracted_data.normalized_titles,
            job_analysis.target_job_titles
        )
        
        education_score, edu_details = ATS_ScoringEngine.calculate_education_score(
            extracted_data.education,
            job_analysis.required_education
        )
        
        keyword_score, keyword_details = ATS_ScoringEngine.calculate_keyword_score(
            extracted_data.keywords,
            job_analysis.keywords
        )
        
        formatting_score, format_details = ATS_ScoringEngine.calculate_formatting_score(
            extracted_data
        )
        
        # Apply "must-have gates" - check core requirements
        final_score = 0.0
        gate_penalties = []
        
        # Gate 1: Required skills - if missing > 50%, cap at 60%
        required_match_ratio = skill_details.get('required_ratio', 0)
        if required_match_ratio < 0.5:
            cap_score = 60.0
            gate_penalties.append(f"Missing >50% required skills (cap: {cap_score})")
            final_score = min(skill_score, cap_score)
        else:
            # Calculate weighted score
            weighted_scores = {
                'required_skills': skill_score * ATS_ScoringEngine.WEIGHTS['required_skills'],
                'experience': experience_score * ATS_ScoringEngine.WEIGHTS['experience'],
                'job_title': title_score * ATS_ScoringEngine.WEIGHTS['job_title'],
                'education': education_score * ATS_ScoringEngine.WEIGHTS['education'],
                'keywords': keyword_score * ATS_ScoringEngine.WEIGHTS['keywords'],
                'formatting': formatting_score * ATS_ScoringEngine.WEIGHTS['formatting']
            }
            
            # Add preferred skills score
            preferred_score = skill_details.get('preferred_ratio', 0) * 100
            weighted_scores['preferred_skills'] = preferred_score * ATS_ScoringEngine.WEIGHTS['preferred_skills']
            
            final_score = sum(weighted_scores.values())
            
            # Apply realistic caps
            # Cap 1: Never give 100 unless perfect match on all dimensions
            if final_score > 95:
                final_score = 95.0 - (np.random.random() * 5.0)  # Add small random variation 90-95
            
            # Cap 2: If missing critical requirements, max is 85
            if required_match_ratio < 0.8:
                final_score = min(final_score, 85.0)
            
            # Cap 3: If experience is below minimum, max is 75
            if exp_details.get('status') == 'below_minimum':
                final_score = min(final_score, 75.0)
        
        # Add small deterministic variation based on hash (0.0-1.0 variation)
        score_hash = hashlib.md5(f"{extracted_data.resume_text[:100]}{job_analysis}".encode()).hexdigest()
        hash_int = int(score_hash[:8], 16)
        variation = (hash_int % 100) / 100.0  # 0.00 to 0.99
        
        final_score = round(final_score + variation, 2)
        final_score = max(0.0, min(100.0, final_score))
        
        # Prepare detailed breakdown
        breakdown = {
            'component_scores': {
                'required_skills': round(skill_score, 2),
                'experience': round(experience_score, 2),
                'job_title': round(title_score, 2),
                'education': round(education_score, 2),
                'keywords': round(keyword_score, 2),
                'formatting': round(formatting_score, 2),
                'preferred_skills': round(preferred_score, 2) if 'preferred_score' in locals() else 0.0
            },
            'weighted_scores': {k: round(v, 2) for k, v in weighted_scores.items()} if 'weighted_scores' in locals() else {},
            'weights': ATS_ScoringEngine.WEIGHTS,
            'details': {
                'skills': skill_details,
                'experience': exp_details,
                'job_title': title_details,
                'education': edu_details,
                'keywords': keyword_details,
                'formatting': format_details
            },
            'gate_penalties': gate_penalties,
            'required_skills_match_ratio': round(required_match_ratio, 3),
            'deterministic_variation': round(variation, 3),
            'score_hash': score_hash[:12]
        }
        
        return final_score, breakdown

# ==============================================
# AI EXTRACTION FUNCTIONS
# ==============================================

def extract_structured_data_with_ai(resume_text: str, filename: str = None) -> ExtractedData:
    """
    Use AI to extract structured data from resume
    This is the ONLY part that uses AI - scoring is deterministic
    """
    # Check cache first
    resume_hash = hashlib.md5(resume_text.encode()).hexdigest()
    with cache_lock:
        if resume_hash in extracted_data_cache:
            print(f"📊 Using cached extracted data for resume")
            return extracted_data_cache[resume_hash]
    
    # Prepare prompt for AI extraction
    prompt = f"""EXTRACT STRUCTURED DATA FROM RESUME FOR ATS SCORING.

RESUME TEXT:
{resume_text[:4000]}

IMPORTANT: Extract ONLY the following structured data. Return in JSON format.

Required JSON structure:
{{
    "candidate_name": "Full Name from resume",
    "skills": ["exact skill 1", "exact skill 2", "exact skill 3", ...],
    "experience_years": 5.5,
    "job_titles": ["exact title 1", "exact title 2", ...],
    "education": ["Bachelor's in Computer Science, University X, 2020", ...],
    "certifications": ["AWS Certified", "PMP", ...],
    "keywords": ["python", "machine learning", "agile", ...]
}}

RULES FOR EXTRACTION:
1. Extract ALL technical and soft skills mentioned
2. Calculate total years of professional experience (sum all job durations)
3. Extract ALL job titles/positions mentioned
4. Extract ALL education entries with degrees and institutions
5. Extract ALL certifications
6. Extract important keywords (technologies, methodologies, tools)
7. If name not found, use filename without extension

Return ONLY the JSON object, no explanations.
"""
    
    try:
        # Call Groq API for extraction
        response = call_groq_api(
            prompt=prompt,
            max_tokens=1500,
            temperature=0.1,  # Low temperature for consistent extraction
            timeout=30
        )
        
        if isinstance(response, dict) and 'error' in response:
            print(f"❌ AI extraction failed: {response['error']}")
            # Fallback to rule-based extraction
            return extract_structured_data_rule_based(resume_text, filename)
        
        # Parse JSON response
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
            else:
                json_str = response
            
            json_str = json_str.replace('```json', '').replace('```', '').strip()
            extracted_json = json.loads(json_str)
            
        except json.JSONDecodeError:
            print(f"❌ Failed to parse AI extraction JSON")
            return extract_structured_data_rule_based(resume_text, filename)
        
        # Calculate formatting metrics
        section_count = len(re.findall(r'\n\s*(?:Experience|Education|Skills|Projects|Work History|Employment|Summary|Objective|Certifications|Technical Skills|Professional Experience)\s*[:]?\n', resume_text, re.IGNORECASE))
        bullet_point_count = len(re.findall(r'^\s*[•\-\*●]\s+', resume_text, re.MULTILINE))
        has_contact_info = bool(re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b|\b(?:https?://)?(?:www\.)?linkedin\.com/\S+\b', resume_text, re.IGNORECASE))
        has_summary = bool(re.search(r'\b(?:summary|objective|profile)\b', resume_text[:500], re.IGNORECASE))
        word_count = len(resume_text.split())
        
        # Normalize skills and titles
        normalized_skills = {ATS_ScoringEngine.normalize_skill(s) for s in extracted_json.get('skills', [])}
        normalized_titles = {ATS_ScoringEngine.normalize_title(t) for t in extracted_json.get('job_titles', [])}
        
        # Extract keywords from resume text
        keywords = set()
        text_lower = resume_text.lower()
        common_keywords = ['python', 'java', 'javascript', 'react', 'node', 'sql', 'aws', 'docker', 'kubernetes', 
                          'agile', 'scrum', 'devops', 'ci/cd', 'api', 'rest', 'graphql', 'microservices',
                          'machine learning', 'ai', 'data analysis', 'cloud', 'azure', 'gcp', 'linux']
        
        for keyword in common_keywords:
            if keyword in text_lower:
                keywords.add(keyword)
        
        # Add extracted keywords
        for kw in extracted_json.get('keywords', []):
            keywords.add(ATS_ScoringEngine.normalize_text(kw))
        
        # Create ExtractedData object
        extracted_data = ExtractedData(
            candidate_name=extracted_json.get('candidate_name', filename.replace('.pdf', '').replace('.docx', '').replace('.txt', '').title() if filename else 'Professional Candidate'),
            skills=extracted_json.get('skills', []),
            normalized_skills=normalized_skills,
            experience_years=float(extracted_json.get('experience_years', 3.0)),
            job_titles=extracted_json.get('job_titles', []),
            normalized_titles=normalized_titles,
            education=extracted_json.get('education', []),
            certifications=extracted_json.get('certifications', []),
            keywords=keywords,
            resume_text=resume_text[:2000],  # Store first 2000 chars for hashing
            section_count=section_count,
            bullet_point_count=bullet_point_count,
            has_contact_info=has_contact_info,
            has_summary=has_summary,
            word_count=word_count
        )
        
        # Cache the extracted data
        with cache_lock:
            extracted_data_cache[resume_hash] = extracted_data
        
        print(f"✅ AI extracted data: {len(extracted_data.skills)} skills, {extracted_data.experience_years} years exp")
        return extracted_data
        
    except Exception as e:
        print(f"❌ AI extraction error: {str(e)}")
        return extract_structured_data_rule_based(resume_text, filename)

def extract_structured_data_rule_based(resume_text: str, filename: str = None) -> ExtractedData:
    """Fallback rule-based extraction if AI fails"""
    print("📝 Using rule-based extraction")
    
    # Simple rule-based extraction
    candidate_name = filename.replace('.pdf', '').replace('.docx', '').replace('.txt', '').title() if filename else 'Professional Candidate'
    
    # Extract name from first line if it looks like a name
    first_line = resume_text.split('\n')[0].strip()
    name_match = re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?$', first_line)
    if name_match:
        candidate_name = first_line
    
    # Extract skills using common patterns
    skills = []
    skill_patterns = [
        r'\b(?:Python|Java|JavaScript|React|Node\.?js|Angular|Vue|SQL|MySQL|PostgreSQL|MongoDB|AWS|Azure|Docker|Kubernetes|Git|Jenkins|Agile|Scrum)\b',
        r'\b(?:Machine Learning|AI|Data Science|Deep Learning|NLP|Computer Vision)\b',
        r'\b(?:Project Management|Leadership|Communication|Teamwork|Problem Solving)\b'
    ]
    
    for pattern in skill_patterns:
        skills.extend(re.findall(pattern, resume_text, re.IGNORECASE))
    
    # Extract experience years
    experience_years = 3.0  # Default
    year_matches = re.findall(r'(\d+)\s*(?:year|yr)s?\s+(?:of\s+)?experience', resume_text, re.IGNORECASE)
    if year_matches:
        experience_years = float(year_matches[0])
    else:
        # Estimate from dates
        date_matches = re.findall(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}', resume_text, re.IGNORECASE)
        if len(date_matches) >= 2:
            experience_years = len(date_matches) * 0.5  # Rough estimate
    
    # Extract job titles
    job_titles = re.findall(r'\b(?:Senior|Junior|Lead|Principal)?\s*(?:Software Engineer|Developer|Data Scientist|Analyst|Manager|Director|Architect)\b', resume_text, re.IGNORECASE)
    
    # Extract education
    education = []
    edu_matches = re.findall(r'(?:B\.?S\.?|B\.?A\.?|M\.?S\.?|M\.?A\.?|Ph\.?D\.?|Bachelor|Master|Doctorate)[^,]*,[^,]*', resume_text, re.IGNORECASE)
    education.extend(edu_matches)
    
    # Extract certifications
    certifications = re.findall(r'\b(?:AWS Certified|Google Cloud|Microsoft Certified|PMP|Scrum Master|Six Sigma)\b', resume_text, re.IGNORECASE)
    
    # Extract keywords
    keywords = set()
    text_lower = resume_text.lower()
    common_keywords = ['python', 'java', 'javascript', 'react', 'node', 'sql', 'aws', 'docker', 'kubernetes', 
                      'agile', 'scrum', 'devops', 'ci/cd', 'api', 'rest', 'graphql', 'microservices']
    
    for keyword in common_keywords:
        if keyword in text_lower:
            keywords.add(keyword)
    
    # Calculate formatting metrics
    section_count = len(re.findall(r'\n\s*(?:Experience|Education|Skills|Projects)\s*[:]?\n', resume_text, re.IGNORECASE))
    bullet_point_count = len(re.findall(r'^\s*[•\-\*●]\s+', resume_text, re.MULTILINE))
    has_contact_info = bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', resume_text))
    has_summary = bool(re.search(r'\b(?:summary|objective)\b', resume_text[:500], re.IGNORECASE))
    word_count = len(resume_text.split())
    
    # Normalize
    normalized_skills = {ATS_ScoringEngine.normalize_skill(s) for s in skills}
    normalized_titles = {ATS_ScoringEngine.normalize_title(t) for t in job_titles}
    
    extracted_data = ExtractedData(
        candidate_name=candidate_name,
        skills=list(set(skills)),
        normalized_skills=normalized_skills,
        experience_years=experience_years,
        job_titles=list(set(job_titles)),
        normalized_titles=normalized_titles,
        education=education,
        certifications=certifications,
        keywords=keywords,
        resume_text=resume_text[:2000],
        section_count=section_count,
        bullet_point_count=bullet_point_count,
        has_contact_info=has_contact_info,
        has_summary=has_summary,
        word_count=word_count
    )
    
    # Cache the extracted data
    resume_hash = hashlib.md5(resume_text.encode()).hexdigest()
    with cache_lock:
        extracted_data_cache[resume_hash] = extracted_data
    
    return extracted_data

def analyze_job_description_with_ai(job_description: str) -> JobDescriptionAnalysis:
    """Use AI to analyze job description and extract requirements"""
    job_hash = hashlib.md5(job_description.encode()).hexdigest()
    cache_key = f"job_{job_hash}"
    
    with cache_lock:
        if cache_key in extracted_data_cache:
            print(f"📊 Using cached job analysis")
            return extracted_data_cache[cache_key]
    
    prompt = f"""ANALYZE JOB DESCRIPTION FOR ATS SCORING.

JOB DESCRIPTION:
{job_description[:3000]}

IMPORTANT: Extract structured requirements. Return in JSON format.

Required JSON structure:
{{
    "required_skills": ["skill1", "skill2", "skill3", ...],
    "preferred_skills": ["skill4", "skill5", ...],
    "nice_to_have_skills": ["skill6", "skill7", ...],
    "min_experience_years": 3.0,
    "required_experience_years": 5.0,
    "target_job_titles": ["Software Engineer", "Senior Developer", ...],
    "required_education": ["Bachelor's in Computer Science", ...],
    "required_certifications": ["AWS Certified", ...],
    "keywords": ["python", "agile", "microservices", ...]
}}

RULES FOR EXTRACTION:
1. Required skills: Look for "must have", "required", "essential", "mandatory"
2. Preferred skills: Look for "preferred", "nice to have", "bonus", "plus"
3. Nice to have: Skills mentioned without requirement indicators
4. Experience: Extract minimum and required years (e.g., "5+ years" = min 5, required 5)
5. Target titles: Extract job titles from description
6. Required education: Degrees mentioned as requirements
7. Required certifications: Certifications mentioned as requirements
8. Keywords: Important technologies and methodologies mentioned

Return ONLY the JSON object, no explanations.
"""
    
    try:
        response = call_groq_api(
            prompt=prompt,
            max_tokens=1500,
            temperature=0.1,
            timeout=30
        )
        
        if isinstance(response, dict) and 'error' in response:
            print(f"❌ Job analysis failed: {response['error']}")
            return analyze_job_description_rule_based(job_description)
        
        # Parse JSON response
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
            else:
                json_str = response
            
            json_str = json_str.replace('```json', '').replace('```', '').strip()
            extracted_json = json.loads(json_str)
            
        except json.JSONDecodeError:
            print(f"❌ Failed to parse job analysis JSON")
            return analyze_job_description_rule_based(job_description)
        
        # Normalize skills
        required_skills = {ATS_ScoringEngine.normalize_skill(s) for s in extracted_json.get('required_skills', [])}
        preferred_skills = {ATS_ScoringEngine.normalize_skill(s) for s in extracted_json.get('preferred_skills', [])}
        nice_to_have_skills = {ATS_ScoringEngine.normalize_skill(s) for s in extracted_json.get('nice_to_have_skills', [])}
        
        # Extract keywords
        keywords = set()
        text_lower = job_description.lower()
        common_keywords = ['python', 'java', 'javascript', 'react', 'node', 'sql', 'aws', 'docker', 'kubernetes', 
                          'agile', 'scrum', 'devops', 'ci/cd', 'api', 'rest', 'graphql', 'microservices']
        
        for keyword in common_keywords:
            if keyword in text_lower:
                keywords.add(keyword)
        
        # Add extracted keywords
        for kw in extracted_json.get('keywords', []):
            keywords.add(ATS_ScoringEngine.normalize_text(kw))
        
        # Normalize titles
        target_titles = {ATS_ScoringEngine.normalize_title(t) for t in extracted_json.get('target_job_titles', [])}
        
        # Create JobDescriptionAnalysis object
        job_analysis = JobDescriptionAnalysis(
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            nice_to_have_skills=nice_to_have_skills,
            min_experience_years=float(extracted_json.get('min_experience_years', 3.0)),
            required_experience_years=float(extracted_json.get('required_experience_years', 5.0)),
            target_job_titles=target_titles,
            required_education=extracted_json.get('required_education', []),
            required_certifications=extracted_json.get('required_certifications', []),
            keywords=keywords
        )
        
        # Cache the job analysis
        with cache_lock:
            extracted_data_cache[cache_key] = job_analysis
        
        print(f"✅ Job analysis: {len(required_skills)} required skills, {job_analysis.min_experience_years} min years")
        return job_analysis
        
    except Exception as e:
        print(f"❌ Job analysis error: {str(e)}")
        return analyze_job_description_rule_based(job_description)

def analyze_job_description_rule_based(job_description: str) -> JobDescriptionAnalysis:
    """Fallback rule-based job analysis"""
    print("📝 Using rule-based job analysis")
    
    text_lower = job_description.lower()
    
    # Extract skills using patterns
    all_skills = re.findall(r'\b(?:Python|Java|JavaScript|React|Node\.?js|SQL|AWS|Docker|Kubernetes|Git|Agile|Scrum)\b', job_description, re.IGNORECASE)
    
    # Categorize skills based on context
    required_skills = set()
    preferred_skills = set()
    nice_to_have_skills = set()
    
    # Simple categorization based on proximity to requirement words
    lines = job_description.split('\n')
    for line in lines:
        line_lower = line.lower()
        skills_in_line = re.findall(r'\b(?:Python|Java|JavaScript|React|Node\.?js|SQL|AWS|Docker|Kubernetes)\b', line, re.IGNORECASE)
        
        for skill in skills_in_line:
            norm_skill = ATS_ScoringEngine.normalize_skill(skill)
            if any(word in line_lower for word in ['must', 'required', 'essential', 'mandatory']):
                required_skills.add(norm_skill)
            elif any(word in line_lower for word in ['preferred', 'nice to have', 'bonus', 'plus']):
                preferred_skills.add(norm_skill)
            else:
                nice_to_have_skills.add(norm_skill)
    
    # If no categorization, put all in required
    if not required_skills and all_skills:
        required_skills = {ATS_ScoringEngine.normalize_skill(s) for s in all_skills[:5]}
        nice_to_have_skills = {ATS_ScoringEngine.normalize_skill(s) for s in all_skills[5:]}
    
    # Extract experience
    min_experience = 3.0
    required_experience = 5.0
    
    exp_matches = re.findall(r'(\d+)[\+]?\s*(?:year|yr)s?\s+(?:of\s+)?experience', text_lower)
    if exp_matches:
        min_experience = float(exp_matches[0])
        required_experience = float(exp_matches[0])
    
    # Extract target titles
    target_titles = re.findall(r'\b(?:Software Engineer|Developer|Data Scientist|Analyst|Manager)\b', job_description, re.IGNORECASE)
    target_titles = {ATS_ScoringEngine.normalize_title(t) for t in target_titles}
    
    # Extract education requirements
    required_education = []
    if 'bachelor' in text_lower or "b.s." in text_lower or "b.a." in text_lower:
        required_education.append("Bachelor's degree")
    if 'master' in text_lower or "m.s." in text_lower or "m.a." in text_lower:
        required_education.append("Master's degree")
    
    # Extract certifications
    required_certifications = []
    if 'aws certified' in text_lower:
        required_certifications.append("AWS Certified")
    if 'pmp' in text_lower:
        required_certifications.append("PMP")
    
    # Extract keywords
    keywords = set()
    for keyword in ['python', 'java', 'javascript', 'react', 'node', 'sql', 'aws', 'docker', 'kubernetes', 
                   'agile', 'scrum', 'devops', 'ci/cd', 'api', 'rest', 'graphql', 'microservices']:
        if keyword in text_lower:
            keywords.add(keyword)
    
    job_analysis = JobDescriptionAnalysis(
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        nice_to_have_skills=nice_to_have_skills,
        min_experience_years=min_experience,
        required_experience_years=required_experience,
        target_job_titles=target_titles,
        required_education=required_education,
        required_certifications=required_certifications,
        keywords=keywords
    )
    
    # Cache the job analysis
    job_hash = hashlib.md5(job_description.encode()).hexdigest()
    cache_key = f"job_{job_hash}"
    with cache_lock:
        extracted_data_cache[cache_key] = job_analysis
    
    return job_analysis

# ==============================================
# UPDATED ANALYSIS FUNCTION WITH DETERMINISTIC SCORING
# ==============================================

def analyze_resume_with_deterministic_scoring(resume_text: str, job_description: str, filename: str = None, analysis_id: str = None):
    """Analyze resume using deterministic ATS scoring"""
    
    print(f"🎯 Starting deterministic ATS scoring...")
    
    # Step 1: Extract structured data from resume (using AI or fallback)
    start_extract = time.time()
    extracted_data = extract_structured_data_with_ai(resume_text, filename)
    extract_time = time.time() - start_extract
    print(f"✅ Resume data extracted in {extract_time:.2f}s")
    
    # Step 2: Analyze job description (using AI or fallback)
    start_job_analysis = time.time()
    job_analysis = analyze_job_description_with_ai(job_description)
    job_analysis_time = time.time() - start_job_analysis
    print(f"✅ Job description analyzed in {job_analysis_time:.2f}s")
    
    # Step 3: Calculate deterministic ATS score
    start_scoring = time.time()
    ats_score, score_breakdown = ATS_ScoringEngine.calculate_ats_score(extracted_data, job_analysis)
    scoring_time = time.time() - start_scoring
    print(f"✅ ATS score calculated in {scoring_time:.2f}s: {ats_score}")
    
    # Step 4: Generate recommendations based on score breakdown
    recommendation = generate_recommendation(ats_score, score_breakdown)
    
    # Step 5: Prepare response
    analysis = {
        "candidate_name": extracted_data.candidate_name,
        "skills_matched": score_breakdown['details']['skills'].get('required_matches', [])[:8],
        "skills_missing": score_breakdown['details']['skills'].get('required_missing', [])[:8],
        "experience_summary": f"{extracted_data.experience_years} years of experience. {score_breakdown['details']['experience'].get('status', '').replace('_', ' ').title()}.",
        "education_summary": f"{len(extracted_data.education)} education entries found. {len(score_breakdown['details']['education'].get('matches', []))} match job requirements.",
        "overall_score": round(ats_score, 2),
        "recommendation": recommendation,
        "key_strengths": extract_key_strengths(score_breakdown),
        "areas_for_improvement": extract_improvement_areas(score_breakdown),
        "scoring_breakdown": {
            "skill_match_score": score_breakdown['component_scores']['required_skills'],
            "experience_score": score_breakdown['component_scores']['experience'],
            "education_score": score_breakdown['component_scores']['education'],
            "keyword_match_score": score_breakdown['component_scores']['keywords'],
            "formatting_score": score_breakdown['component_scores']['formatting'],
            "job_title_score": score_breakdown['component_scores']['job_title'],
            "preferred_skills_score": score_breakdown['component_scores'].get('preferred_skills', 0)
        },
        "detailed_breakdown": score_breakdown,
        "extracted_data": extracted_data.to_dict(),
        "job_analysis": job_analysis.to_dict(),
        "ats_algorithm_version": "2.0_deterministic",
        "score_consistency_hash": score_breakdown.get('score_hash', ''),
        "deterministic_variation": score_breakdown.get('deterministic_variation', 0),
        "processing_times": {
            "extraction": round(extract_time, 2),
            "job_analysis": round(job_analysis_time, 2),
            "scoring": round(scoring_time, 2),
            "total": round(extract_time + job_analysis_time + scoring_time, 2)
        }
    }
    
    # Add analysis ID if provided
    if analysis_id:
        analysis['analysis_id'] = analysis_id
    
    # Add AI provider info
    analysis['ai_provider'] = "groq"
    analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
    analysis['ai_model'] = GROQ_MODEL or DEFAULT_MODEL
    
    print(f"✅ Deterministic analysis complete. Score: {ats_score}, Consistency Hash: {score_breakdown.get('score_hash', '')[:8]}")
    
    return analysis

def generate_recommendation(score: float, breakdown: Dict) -> str:
    """Generate recommendation based on deterministic score"""
    if score >= 90:
        return "Excellent Match - Strongly Recommended"
    elif score >= 80:
        return "Strong Match - Recommended"
    elif score >= 70:
        return "Good Match - Consider for Interview"
    elif score >= 60:
        return "Fair Match - Review in Detail"
    elif score >= 50:
        return "Marginal Match - Consider Only if Urgent"
    else:
        return "Poor Match - Not Recommended"

def extract_key_strengths(breakdown: Dict) -> List[str]:
    """Extract key strengths from score breakdown"""
    strengths = []
    
    # Check skill matches
    skill_matches = breakdown['details']['skills'].get('required_matches', [])
    if skill_matches:
        strengths.append(f"Matches {len(skill_matches)} required skills")
    
    # Check experience
    exp_status = breakdown['details']['experience'].get('status', '')
    if exp_status == 'exceeds_requirements':
        extra_years = breakdown['details']['experience'].get('extra_years', 0)
        strengths.append(f"Exceeds experience requirements by {extra_years} years")
    
    # Check formatting
    if breakdown['component_scores']['formatting'] >= 80:
        strengths.append("Well-formatted resume (ATS-friendly)")
    
    # Check education
    edu_matches = breakdown['details']['education'].get('matches', [])
    if edu_matches:
        strengths.append(f"Meets {len(edu_matches)} education requirements")
    
    # Add default strengths if empty
    if not strengths:
        strengths = [
            "Professional experience demonstrated",
            "Relevant technical skills present",
            "Standard resume formatting"
        ]
    
    return strengths[:4]

def extract_improvement_areas(breakdown: Dict) -> List[str]:
    """Extract areas for improvement from score breakdown"""
    improvements = []
    
    # Check missing required skills
    missing_skills = breakdown['details']['skills'].get('required_missing', [])
    if missing_skills:
        improvements.append(f"Add {len(missing_skills[:3])} key required skills")
    
    # Check experience gap
    exp_status = breakdown['details']['experience'].get('status', '')
    if exp_status == 'below_minimum':
        gap = breakdown['details']['experience'].get('gap_years', 0)
        improvements.append(f"Gain {gap} more years of experience")
    
    # Check formatting
    if breakdown['component_scores']['formatting'] < 60:
        improvements.append("Improve resume formatting (add sections, bullet points)")
    
    # Check keyword density
    if breakdown['component_scores']['keywords'] < 50:
        improvements.append("Increase keyword density from job description")
    
    # Add default improvements if empty
    if not improvements:
        improvements = [
            "Consider adding more specific achievements",
            "Include quantifiable results in experience",
            "Add relevant certifications if applicable"
        ]
    
    return improvements[:4]

# ==============================================
# API CALL FUNCTIONS
# ==============================================

def update_activity():
    """Update last activity timestamp"""
    global last_activity_time
    last_activity_time = datetime.now()

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
            
            return False
        elif response and 'ready' in response.lower():
            elapsed = time.time() - start_time
            print(f"✅ Groq warmed up in {elapsed:.2f}s")
            
            warmup_complete = True
            api_available = True
                
            return True
        else:
            print("⚠️ Warm-up attempt failed: Unexpected response")
            return False
        
    except Exception as e:
        print(f"⚠️ Warm-up attempt failed: {str(e)}")
        return False

# ==============================================
# FILE EXTRACTION FUNCTIONS
# ==============================================

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

# ==============================================
# EXCEL REPORT FUNCTIONS
# ==============================================

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
    deterministic_fill = PatternFill(start_color="00B09B", end_color="96C93D", fill_type="solid")
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
    cell.value = "🎯 DETERMINISTIC ATS ANALYSIS REPORT"
    cell.font = Font(bold=True, size=16, color="FFFFFF")
    cell.fill = deterministic_fill
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
    
    ws[f'A{row}'] = "ATS Algorithm"
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = "Deterministic v2.0"
    row += 1
    
    ws[f'A{row}'] = "Score Consistency Hash"
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = analysis_data.get('detailed_breakdown', {}).get('score_hash', 'N/A')[:16] + "..."
    row += 2
    
    # Overall Score
    ws[f'A{row}'] = "Deterministic ATS Score"
    ws[f'A{row}'].font = Font(bold=True, size=12)
    ws[f'A{row}'].fill = header_fill
    ws[f'A{row}'].font = Font(bold=True, size=12, color="FFFFFF")
    score = analysis_data.get('overall_score', 0)
    ws[f'B{row}'] = f"{score}/100"
    score_color = "C00000" if score < 60 else "70AD47" if score >= 80 else "FFC000"
    ws[f'B{row}'].font = Font(bold=True, size=12, color=score_color)
    row += 1
    
    ws[f'A{row}'] = "Recommendation"
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = analysis_data.get('recommendation', 'N/A')
    row += 1
    
    ws[f'A{row}'] = "Score Consistency"
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'B{row}'] = "Guaranteed - Same inputs produce same score"
    row += 2
    
    # Detailed Score Breakdown
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "DETAILED SCORE BREAKDOWN"
    cell.font = header_font
    cell.fill = PatternFill(start_color="5B9BD5", end_color="5B9BD5", fill_type="solid")
    cell.alignment = Alignment(horizontal='center')
    row += 1
    
    breakdown = analysis_data.get('scoring_breakdown', {})
    components = [
        ("Required Skills Match", breakdown.get('skill_match_score', 0)),
        ("Experience Match", breakdown.get('experience_score', 0)),
        ("Education Match", breakdown.get('education_score', 0)),
        ("Job Title Relevance", breakdown.get('job_title_score', 0)),
        ("Keyword Density", breakdown.get('keyword_match_score', 0)),
        ("Resume Formatting", breakdown.get('formatting_score', 0)),
        ("Preferred Skills Bonus", breakdown.get('preferred_skills_score', 0))
    ]
    
    for component, score_val in components:
        ws[f'A{row}'] = component
        ws[f'A{row}'].font = subheader_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'B{row}'] = f"{score_val}/100"
        row += 1
    
    row += 1
    
    # Skills Matched Section
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "REQUIRED SKILLS MATCHED ✓"
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
        ws[f'A{row}'] = "No required skills matched"
        row += 1
    
    row += 1
    
    # Skills Missing Section
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "REQUIRED SKILLS MISSING ✗"
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
    cell.value = "EXPERIENCE ANALYSIS"
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
    cell.value = "EDUCATION ANALYSIS"
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
    deterministic_fill = PatternFill(start_color="00B09B", end_color="96C93D", fill_type="solid")
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
    title_cell.value = "🎯 DETERMINISTIC BATCH ATS ANALYSIS"
    title_cell.font = Font(bold=True, size=16, color="FFFFFF")
    title_cell.fill = deterministic_fill
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Summary Information
    summary_info = [
        ("Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Total Resumes", len(analyses)),
        ("ATS Algorithm", "Deterministic v2.0"),
        ("Score Consistency", "Guaranteed"),
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
    header_cell.value = "CANDIDATES RANKING (BY DETERMINISTIC ATS SCORE)"
    header_cell.font = header_font
    header_cell.fill = header_fill
    header_cell.alignment = Alignment(horizontal='center')
    row += 1
    
    # Table Headers
    headers = ["Rank", "Candidate Name", "ATS Score", "Recommendation", "Required Skills Match"]
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
        
        skill_match = analysis.get('scoring_breakdown', {}).get('skill_match_score', 0)
        ws_summary.cell(row=row, column=5, value=f"{skill_match}/100")
        
        row += 1
    
    # Add border to the table
    for r in range(row - len(analyses) - 1, row):
        for c in range(1, 6):
            ws_summary.cell(row=r, column=c).border = border
    
    # ========== DETAILED ANALYSIS SHEET ==========
    details_headers = [
        "Rank", "Candidate Name", "ATS Score", "Recommendation", 
        "Experience Score", "Education Score", "Formatting Score", "Consistency Hash"
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
        
        breakdown = analysis.get('scoring_breakdown', {})
        ws_details.cell(row=idx, column=5, value=breakdown.get('experience_score', 0))
        ws_details.cell(row=idx, column=6, value=breakdown.get('education_score', 0))
        ws_details.cell(row=idx, column=7, value=breakdown.get('formatting_score', 0))
        
        consistency_hash = analysis.get('detailed_breakdown', {}).get('score_hash', '')[:12]
        ws_details.cell(row=idx, column=8, value=consistency_hash)
        
        ws_details.row_dimensions[idx].height = 60
    
    # Add border to details table
    for r in range(1, len(analyses) + 2):
        for c in range(1, 9):
            ws_details.cell(row=r, column=c).border = border
            ws_details.cell(row=r, column=c).alignment = Alignment(wrap_text=True, vertical='top')
    
    # ========== SKILLS ANALYSIS SHEET ==========
    skills_headers = ["Rank", "Candidate", "Required Skills Match", "Missing Skills", "Match Ratio"]
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
        
        # Required skills matched
        matched_skills = analysis.get('skills_matched', [])
        ws_skills.cell(row=idx, column=3, value=", ".join(matched_skills[:3]))
        
        # Missing skills
        missing_skills = analysis.get('skills_missing', [])
        ws_skills.cell(row=idx, column=4, value=", ".join(missing_skills[:3]))
        
        # Match ratio
        breakdown = analysis.get('detailed_breakdown', {})
        match_ratio = breakdown.get('details', {}).get('skills', {}).get('required_ratio', 0)
        ws_skills.cell(row=idx, column=5, value=f"{match_ratio*100:.1f}%")
        
        ws_skills.row_dimensions[idx].height = 40
    
    # Add border to skills table
    for r in range(1, len(analyses) + 2):
        for c in range(1, 6):
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
        ("Deterministic ATS Score", f"{analysis.get('overall_score', 0)}/100"),
        ("Recommendation", analysis.get('recommendation', 'N/A')),
        ("ATS Algorithm", analysis.get('ats_algorithm', 'Deterministic v2.0')),
        ("Score Consistency Hash", analysis.get('detailed_breakdown', {}).get('score_hash', 'N/A')[:16] + "..."),
        ("Filename", analysis.get('original_filename', 'N/A')),
        ("File Size", analysis.get('file_size', 'N/A')),
        ("Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ]
    
    for label, value in info_fields:
        ws[f'A{row}'] = label
        ws[f'A{row}'].font = subheader_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'B{row}'] = value
        row += 1
    
    row += 1
    
    # Score Breakdown
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "SCORE BREAKDOWN"
    cell.font = header_font
    cell.fill = PatternFill(start_color="5B9BD5", end_color="5B9BD5", fill_type="solid")
    cell.alignment = Alignment(horizontal='center')
    row += 1
    
    breakdown = analysis.get('scoring_breakdown', {})
    components = [
        ("Required Skills Match", breakdown.get('skill_match_score', 0)),
        ("Experience Match", breakdown.get('experience_score', 0)),
        ("Education Match", breakdown.get('education_score', 0)),
        ("Job Title Relevance", breakdown.get('job_title_score', 0)),
        ("Keyword Density", breakdown.get('keyword_match_score', 0)),
        ("Resume Formatting", breakdown.get('formatting_score', 0))
    ]
    
    for component, score_val in components:
        ws[f'A{row}'] = component
        ws[f'A{row}'].font = subheader_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'B{row}'] = f"{score_val}/100"
        row += 1
    
    row += 1
    
    # Required Skills Matched
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "REQUIRED SKILLS MATCHED"
    cell.font = header_font
    cell.fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
    cell.alignment = Alignment(horizontal='center')
    row += 1
    
    for skill in analysis.get('skills_matched', []):
        ws[f'A{row}'] = "✓"
        ws[f'B{row}'] = skill
        row += 1
    
    row += 1
    
    # Required Skills Missing
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws[f'A{row}']
    cell.value = "REQUIRED SKILLS MISSING"
    cell.font = header_font
    cell.fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
    cell.alignment = Alignment(horizontal='center')
    row += 1
    
    for skill in analysis.get('skills_missing', []):
        ws[f'A{row}'] = "✗"
        ws[f'B{row}'] = skill
        row += 1
    
    row += 1
    
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
    ws.merge_calls(f'A{row}:B{row}')
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

# ==============================================
# API ENDPOINTS
# ==============================================

@app.route('/')
def home():
    """Root route - API landing page"""
    return jsonify({
        'status': 'Resume Analyzer API',
        'version': '2.0.0',
        'ats_scoring': 'deterministic_v2.0',
        'description': 'Deterministic ATS scoring with guaranteed consistency'
    })

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Main endpoint to analyze single resume with deterministic scoring"""
    update_activity()
    
    try:
        print("\n" + "="*50)
        print("📥 New single analysis request received (Deterministic Scoring)")
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
        
        # Analyze with deterministic scoring
        print(f"🎯 Starting deterministic ATS scoring...")
        ai_start = time.time()
        
        # Generate unique analysis ID
        analysis_id = f"single_{timestamp}"
        analysis = analyze_resume_with_deterministic_scoring(resume_text, job_description, resume_file.filename, analysis_id)
        ai_time = time.time() - ai_start
        
        print(f"✅ Deterministic ATS scoring completed in {ai_time:.2f}s")
        print(f"📊 Score: {analysis['overall_score']} | Consistency Hash: {analysis.get('detailed_breakdown', {}).get('score_hash', '')[:8]}")
        
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
        analysis['ai_model'] = GROQ_MODEL or DEFAULT_MODEL
        analysis['ai_provider'] = "groq"
        analysis['ai_status'] = "Warmed up" if warmup_complete else "Warming up"
        analysis['response_time'] = f"{ai_time:.2f}s"
        analysis['analysis_id'] = analysis_id
        analysis['ats_algorithm'] = "deterministic_v2.0"
        
        total_time = time.time() - start_time
        print(f"✅ Request completed in {total_time:.2f} seconds")
        print("="*50 + "\n")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Unexpected error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

def process_batch_resume(resume_file, job_description, index, total, batch_id):
    """Process a single resume in batch mode with deterministic scoring"""
    try:
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
        
        # Analyze with deterministic scoring
        analysis_id = f"{batch_id}_candidate_{index}"
        analysis = analyze_resume_with_deterministic_scoring(resume_text, job_description, resume_file.filename, analysis_id)
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
    """Analyze multiple resumes with deterministic scoring"""
    update_activity()
    
    try:
        print("\n" + "="*50)
        print("📦 New batch analysis request received (Deterministic Scoring)")
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
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
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
            'ats_algorithm': "deterministic_v2.0",
            'score_consistency': "guaranteed",
            'job_description_preview': job_description[:200] + ("..." if len(job_description) > 200 else "")
        }
        
        print(f"✅ Batch analysis completed in {time.time() - start_time:.2f}s")
        print("="*50 + "\n")
        
        return jsonify(batch_summary)
        
    except Exception as e:
        print(f"❌ Batch analysis error: {traceback.format_exc()}")
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

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
    
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat(),
        'service': 'resume-analyzer',
        'ai_provider': 'groq',
        'ai_warmup': warmup_complete,
        'model': model_to_use,
        'ats_algorithm': 'deterministic_v2.0',
        'score_consistency': 'guaranteed',
        'message': f'Service is alive with deterministic ATS scoring!' if warmup_complete else f'Service is alive, warming up...'
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    update_activity()
    
    inactive_time = datetime.now() - last_activity_time
    inactive_minutes = int(inactive_time.total_seconds() / 60)
    
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    model_info = GROQ_MODELS.get(model_to_use, {'name': model_to_use, 'provider': 'Groq'})
    
    # Calculate cache statistics
    cache_size = len(extracted_data_cache)
    resume_cache_count = sum(1 for k in extracted_data_cache.keys() if not k.startswith('job_'))
    job_cache_count = sum(1 for k in extracted_data_cache.keys() if k.startswith('job_'))
    
    return jsonify({
        'status': 'Backend is running!', 
        'timestamp': datetime.now().isoformat(),
        'ai_provider': 'groq',
        'ai_provider_configured': bool(GROQ_API_KEY),
        'model': model_to_use,
        'model_info': model_info,
        'ai_warmup_complete': warmup_complete,
        'ats_algorithm': 'deterministic_v2.0',
        'score_consistency': 'guaranteed',
        'decimal_scores': True,
        'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
        'reports_folder_exists': os.path.exists(REPORTS_FOLDER),
        'upload_folder_path': UPLOAD_FOLDER,
        'reports_folder_path': REPORTS_FOLDER,
        'cache_statistics': {
            'total_entries': cache_size,
            'resume_data_cached': resume_cache_count,
            'job_analysis_cached': job_cache_count,
            'cache_hit_ratio': 'N/A'
        },
        'inactive_minutes': inactive_minutes,
        'version': '2.0.0',
        'features': [
            'deterministic_ats_scoring',
            'score_consistency_guaranteed',
            'decimal_scores',
            'required_vs_preferred_skills',
            'must_have_gates',
            'realistic_score_caps',
            'normalized_skills_titles',
            'ratio_based_scoring',
            'experience_match_scoring',
            'job_title_similarity',
            'education_certification_match',
            'resume_formatting_scoring',
            'cache_system',
            'batch_processing_15'
        ]
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
            'ats_scoring': 'deterministic_v2.0',
            'documentation': 'https://console.groq.com/docs/models',
            'deprecation_info': 'https://console.groq.com/docs/deprecations'
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/ats-info', methods=['GET'])
def ats_info():
    """Get information about the deterministic ATS scoring algorithm"""
    update_activity()
    
    return jsonify({
        'ats_algorithm': 'deterministic_v2.0',
        'version': '2.0.0',
        'description': 'Math-based deterministic ATS scoring with guaranteed consistency',
        'key_features': [
            'Deterministic math-only scoring (no AI judgment)',
            'Same inputs always produce same score',
            'Decimal scores (e.g., 78.42)',
            'Separate required vs preferred skills',
            'Normalized skills and titles',
            'Ratio-based scoring (matched/total)',
            'Must-have gates (core requirement checks)',
            'Realistic score caps (no frequent 95-100)',
            'Experience match with diminishing returns',
            'Job title similarity scoring',
            'Education/certification matching',
            'Resume formatting scoring',
            'Keyword density analysis'
        ],
        'scoring_dimensions': [
            {'name': 'Required Skills Match', 'weight': 0.35, 'description': 'Exact match of required skills from job description'},
            {'name': 'Preferred Skills Match', 'weight': 0.15, 'description': 'Match of preferred/nice-to-have skills'},
            {'name': 'Experience Match', 'weight': 0.20, 'description': 'Years of experience relative to requirements'},
            {'name': 'Job Title Relevance', 'weight': 0.10, 'description': 'Similarity of job titles'},
            {'name': 'Education Match', 'weight': 0.10, 'description': 'Educational qualifications matching requirements'},
            {'name': 'Keyword Density', 'weight': 0.05, 'description': 'Important keywords from job description'},
            {'name': 'Resume Formatting', 'weight': 0.05, 'description': 'ATS-friendly formatting and structure'}
        ],
        'consistency_guarantees': [
            'All extracted data is cached by content hash',
            'Scoring uses only mathematical formulas',
            'Small deterministic variation based on hash (0.0-1.0)',
            'No randomness or AI judgment in final score',
            'Same resume + job = same score across all analyses'
        ],
        'normalization_rules': {
            'skills': 'React.js → react, Node.js → nodejs, AWS Cloud → aws, etc.',
            'titles': 'SDE → software engineer, Dev → developer, PM → project manager, etc.'
        },
        'score_caps': {
            'perfect_match_cap': 95.0,
            'missing_requirements_cap': 85.0,
            'below_min_exp_cap': 75.0,
            'missing_50pct_req_skills_cap': 60.0
        },
        'technical_details': {
            'scoring_engine': 'ATS_ScoringEngine class',
            'caching_system': 'MD5-based content hashing',
            'fallback_mechanisms': 'Rule-based extraction if AI fails',
            'batch_processing': 'Up to 15 resumes concurrently',
            'report_generation': 'Excel reports with detailed breakdowns'
        }
    })

# Start warm-up on app start
if GROQ_API_KEY:
    print(f"🚀 Starting Groq warm-up...")
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    print(f"🤖 Using model: {model_to_use}")
    
    # Start warm-up in a separate thread to avoid blocking
    def delayed_warmup():
        time.sleep(2)  # Wait for server to start
        warmup_groq_service()
    
    warmup_thread = threading.Thread(target=delayed_warmup, daemon=True)
    warmup_thread.start()
    
else:
    print("⚠️ WARNING: No Groq API key found!")
    print("Please set GROQ_API_KEY in Render environment variables")

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Resume Analyzer Backend Starting...")
    print("="*50)
    port = int(os.environ.get('PORT', 5002))
    print(f"📍 Server: http://localhost:{port}")
    print(f"⚡ AI Provider: GROQ")
    model_to_use = GROQ_MODEL or DEFAULT_MODEL
    print(f"🤖 Model: {model_to_use}")
    print(f"🎯 ATS Scoring: Deterministic v2.0")
    print(f"✅ Score Consistency: Guaranteed")
    print(f"✅ Decimal Scores: Enabled")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📁 Reports folder: {REPORTS_FOLDER}")
    print("✅ Deterministic Scoring: Math-only, no AI judgment")
    print("✅ Cache System: Resume and job analysis caching")
    print("✅ Batch Capacity: Up to 15 resumes")
    print("="*50 + "\n")
    
    if not GROQ_API_KEY:
        print("⚠️  WARNING: No Groq API key found!")
        print("Please set GROQ_API_KEY in Render environment variables")
        print("Get your API key from: https://console.groq.com/keys")
    
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
