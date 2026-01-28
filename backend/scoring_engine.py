import re
import math
from typing import Dict, List, Tuple, Set
import numpy as np
from datetime import datetime
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import jellyfish
from .nlp_processor import NLPProcessor

class ScoringEngine:
    """Advanced scoring engine for resume-job matching"""
    
    def __init__(self):
        self.nlp = NLPProcessor()
        
        # Enhanced scoring weights
        self.weights = {
            'skills_match': 0.35,      # Technical and soft skills
            'experience_relevance': 0.25, # Work experience match
            'education_match': 0.15,    # Education level and field
            'keyword_similarity': 0.10, # Overall text similarity
            'certifications': 0.05,     # Relevant certifications
            'projects_match': 0.05,     # Project relevance
            'formatting_score': 0.03,   # Resume quality
            'seniority_match': 0.02     # Experience level match
        }
        
        # Industry-specific keywords database
        self.industry_keywords = self._load_industry_keywords()
    
    def _load_industry_keywords(self) -> Dict[str, List[str]]:
        """Load industry-specific keywords"""
        return {
            'software_engineering': [
                'software development', 'backend', 'frontend', 'full stack', 'api', 'microservices',
                'agile', 'scrum', 'devops', 'ci/cd', 'testing', 'debugging', 'code review',
                'version control', 'git', 'architecture', 'design patterns', 'algorithms',
                'data structures', 'optimization', 'performance', 'scalability', 'security'
            ],
            'data_science': [
                'machine learning', 'deep learning', 'ai', 'data analysis', 'statistics',
                'python', 'r', 'sql', 'pandas', 'numpy', 'tensorflow', 'pytorch', 'scikit-learn',
                'data visualization', 'tableau', 'power bi', 'big data', 'hadoop', 'spark',
                'etl', 'data mining', 'predictive modeling', 'natural language processing'
            ],
            'cloud_devops': [
                'aws', 'azure', 'google cloud', 'docker', 'kubernetes', 'terraform',
                'ansible', 'jenkins', 'github actions', 'ci/cd', 'infrastructure as code',
                'monitoring', 'logging', 'security', 'networking', 'load balancing',
                'auto-scaling', 'containerization', 'orchestration', 'serverless'
            ],
            'product_management': [
                'product strategy', 'roadmap', 'user stories', 'agile', 'scrum',
                'market research', 'competitive analysis', 'user experience', 'ui/ux',
                'metrics', 'kpis', 'a/b testing', 'customer development', 'prioritization',
                'stakeholder management', 'requirements gathering', 'product launch'
            ],
            'marketing': [
                'digital marketing', 'seo', 'sem', 'social media', 'content marketing',
                'email marketing', 'analytics', 'google analytics', 'campaign management',
                'brand management', 'market research', 'crm', 'salesforce', 'hubspot',
                'conversion optimization', 'lead generation', 'customer acquisition'
            ]
        }
    
    def calculate_score(self, resume_data: Dict, job_description: str) -> Dict:
        """Calculate comprehensive matching score"""
        
        # Parse job description
        job_analysis = self.analyze_job_description(job_description)
        
        # Calculate individual scores
        scores = {
            'skills_match': self.calculate_skills_score(resume_data, job_analysis),
            'experience_relevance': self.calculate_experience_score(resume_data, job_analysis),
            'education_match': self.calculate_education_score(resume_data, job_analysis),
            'keyword_similarity': self.calculate_keyword_similarity(resume_data, job_description),
            'certifications': self.calculate_certifications_score(resume_data, job_analysis),
            'projects_match': self.calculate_projects_score(resume_data, job_analysis),
            'formatting_score': self.calculate_formatting_score(resume_data),
            'seniority_match': self.calculate_seniority_score(resume_data, job_analysis)
        }
        
        # Calculate weighted total score
        total_score = sum(score * self.weights[category] 
                         for category, score in scores.items())
        
        # Apply curve for more realistic distribution
        total_score = self.apply_scoring_curve(total_score)
        
        # Calculate grade and recommendation
        grade, recommendation = self.get_grade_and_recommendation(total_score)
        
        # Find missing skills
        missing_skills = self.identify_missing_skills(resume_data, job_analysis)
        
        # Find matched skills
        matched_skills = self.identify_matched_skills(resume_data, job_analysis)
        
        return {
            'overall_score': round(total_score),
            'grade': grade,
            'recommendation': recommendation,
            'detailed_scores': scores,
            'missing_skills': missing_skills,
            'matched_skills': matched_skills,
            'strength_areas': self.identify_strengths(scores),
            'improvement_areas': self.identify_improvements(scores, missing_skills),
            'industry_fit': self.assess_industry_fit(resume_data, job_analysis),
            'experience_level': self.determine_experience_level(resume_data)
        }
    
    def analyze_job_description(self, job_description: str) -> Dict:
        """Analyze job description to extract requirements"""
        
        # Extract skills from job description
        job_skills = self.nlp.extract_skills(job_description)
        
        # Extract keywords
        job_keywords = self.nlp.extract_keywords(job_description, top_n=30)
        
        # Extract requirements patterns
        requirements = self.extract_requirements(job_description)
        
        # Determine industry
        industry = self.detect_industry(job_description)
        
        # Determine experience level
        experience_level = self.detect_experience_level(job_description)
        
        # Extract education requirements
        education_req = self.extract_education_requirements(job_description)
        
        return {
            'skills': job_skills,
            'keywords': [kw[0] for kw in job_keywords],
            'requirements': requirements,
            'industry': industry,
            'experience_level': experience_level,
            'education_requirements': education_req,
            'raw_text': job_description
        }
    
    def calculate_skills_score(self, resume_data: Dict, job_analysis: Dict) -> float:
        """Calculate skills matching score with advanced algorithms"""
        
        resume_skills = set(resume_data.get('skills', []))
        job_skills = set(job_analysis.get('skills', []))
        
        if not job_skills:
            return 0.7  # Default if no skills specified
        
        # Calculate exact matches
        exact_matches = resume_skills.intersection(job_skills)
        
        # Calculate partial matches using string similarity
        partial_matches = 0
        for job_skill in job_skills:
            for resume_skill in resume_skills:
                similarity = self.calculate_string_similarity(job_skill, resume_skill)
                if similarity > 0.7:  # Threshold for partial match
                    partial_matches += similarity
                    break
        
        # Calculate skill category matches
        category_matches = self.calculate_category_matches(resume_skills, job_skills)
        
        total_possible = len(job_skills)
        
        if total_possible == 0:
            return 0.0
        
        # Weighted score
        exact_score = len(exact_matches) / total_possible
        partial_score = (partial_matches / total_possible) * 0.7  # Weight partial matches
        category_score = category_matches * 0.3
        
        return min(1.0, exact_score + partial_score + category_score)
    
    def calculate_experience_score(self, resume_data: Dict, job_analysis: Dict) -> float:
        """Calculate experience relevance score"""
        
        experiences = resume_data.get('experience', [])
        if not experiences:
            return 0.2  # Minimal score for no experience
        
        # Extract job requirements
        job_exp = job_analysis.get('requirements', {}).get('experience_years', 0)
        job_industries = job_analysis.get('industry', [])
        job_titles = self.extract_job_titles(job_analysis['raw_text'])
        
        total_score = 0
        max_possible = len(experiences) * 3  # 3 criteria per experience
        
        for exp in experiences:
            exp_score = 0
            
            # Title relevance
            title = exp.get('title', '').lower()
            for job_title in job_titles:
                if self.calculate_string_similarity(title, job_title) > 0.6:
                    exp_score += 1
                    break
            
            # Industry relevance
            company = exp.get('company', '').lower()
            if any(industry in company for industry in job_industries):
                exp_score += 1
            
            # Duration relevance
            duration = exp.get('duration_months', 0)
            if duration >= job_exp * 12:  # Convert years to months
                exp_score += 1
            
            total_score += exp_score
        
        return min(1.0, total_score / max_possible)
    
    def calculate_education_score(self, resume_data: Dict, job_analysis: Dict) -> float:
        """Calculate education match score"""
        
        education_list = resume_data.get('education', [])
        edu_requirements = job_analysis.get('education_requirements', {})
        
        if not education_list:
            return 0.1  # Minimal score for no education
        
        # Check for degree requirements
        required_degree = edu_requirements.get('degree', '')
        required_field = edu_requirements.get('field', '')
        
        best_match_score = 0
        
        for edu in education_list:
            score = 0
            degree = edu.get('degree', '').lower()
            institution = edu.get('institution', '').lower()
            
            # Degree match
            if required_degree and required_degree in degree:
                score += 0.5
            
            # Field match
            if required_field and required_field in degree:
                score += 0.3
            
            # Institution prestige (simplified)
            if any(prestige in institution for prestige in ['university', 'college', 'institute']):
                score += 0.2
            
            best_match_score = max(best_match_score, score)
        
        return best_match_score
    
    def calculate_keyword_similarity(self, resume_data: Dict, job_description: str) -> float:
        """Calculate keyword similarity using TF-IDF and cosine similarity"""
        
        resume_text = resume_data.get('raw_text', '')
        
        # Create TF-IDF vectors
        vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        try:
            tfidf_matrix = vectorizer.fit_transform([resume_text, job_description])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # Apply sigmoid function for better distribution
            similarity = 1 / (1 + math.exp(-10 * (similarity - 0.5)))
            
            return min(1.0, similarity)
            
        except:
            return 0.5  # Default score
    
    def calculate_certifications_score(self, resume_data: Dict, job_analysis: Dict) -> float:
        """Calculate certifications match score"""
        
        certifications = resume_data.get('certifications', [])
        if not certifications:
            return 0.2  # Some credit for no certifications
        
        job_skills = set(job_analysis.get('skills', []))
        
        match_count = 0
        for cert in certifications:
            cert_name = cert.get('name', '').lower()
            
            # Check if certification matches job skills
            for skill in job_skills:
                if skill in cert_name or cert_name in skill:
                    match_count += 1
                    break
        
        total_certs = len(certifications)
        
        if total_certs == 0:
            return 0.0
        
        return min(1.0, match_count / total_certs)
    
    def calculate_projects_score(self, resume_data: Dict, job_analysis: Dict) -> float:
        """Calculate projects relevance score"""
        
        projects = resume_data.get('projects', [])
        if not projects:
            return 0.2  # Some credit for no projects
        
        job_skills = set(job_analysis.get('skills', []))
        
        total_score = 0
        
        for project in projects:
            project_score = 0
            techs = project.get('technologies', [])
            description = project.get('description', '').lower()
            
            # Technology match
            tech_matches = len(set(techs).intersection(job_skills))
            project_score += min(1.0, tech_matches / max(1, len(techs)))
            
            # Keyword match in description
            for skill in job_skills:
                if skill in description:
                    project_score += 0.1
            
            total_score += min(1.0, project_score)
        
        return min(1.0, total_score / len(projects))
    
    def calculate_formatting_score(self, resume_data: Dict) -> float:
        """Calculate resume formatting and quality score"""
        
        quality = resume_data.get('quality_metrics', {})
        
        score = 0
        
        # Word count score (optimal: 400-800 words)
        word_count = quality.get('word_count', 0)
        if 400 <= word_count <= 800:
            score += 0.3
        elif 300 <= word_count <= 1000:
            score += 0.2
        else:
            score += 0.1
        
        # Readability score
        readability = quality.get('readability', {})
        flesch_ease = readability.get('flesch_reading_ease', 0)
        if flesch_ease >= 60:  # Standard readability
            score += 0.3
        elif flesch_ease >= 50:
            score += 0.2
        else:
            score += 0.1
        
        # Structure score (sections present)
        sections = resume_data.get('sections', {})
        important_sections = ['experience', 'education', 'skills']
        present_sections = sum(1 for section in important_sections if sections.get(section))
        score += (present_sections / len(important_sections)) * 0.4
        
        return min(1.0, score)
    
    def calculate_seniority_score(self, resume_data: Dict, job_analysis: Dict) -> float:
        """Calculate experience level match score"""
        
        required_level = job_analysis.get('experience_level', 'mid')
        resume_level = self.determine_experience_level(resume_data)
        
        level_values = {
            'entry': 1,
            'junior': 2,
            'mid': 3,
            'senior': 4,
            'lead': 5,
            'executive': 6
        }
        
        req_value = level_values.get(required_level, 3)
        res_value = level_values.get(resume_level, 2)
        
        # Calculate match (closer is better)
        diff = abs(req_value - res_value)
        
        if diff == 0:
            return 1.0
        elif diff == 1:
            return 0.7
        elif diff == 2:
            return 0.4
        else:
            return 0.1
    
    def calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using multiple algorithms"""
        
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()
        
        if str1 == str2:
            return 1.0
        
        # Jaro-Winkler similarity
        jaro_winkler = jellyfish.jaro_winkler_similarity(str1, str2)
        
        # Levenshtein similarity (normalized)
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            levenshtein = 0
        else:
            levenshtein = 1 - (jellyfish.levenshtein_distance(str1, str2) / max_len)
        
        # Token set similarity
        tokens1 = set(str1.split())
        tokens2 = set(str2.split())
        if tokens1 and tokens2:
            token_similarity = len(tokens1.intersection(tokens2)) / len(tokens1.union(tokens2))
        else:
            token_similarity = 0
        
        # Weighted average
        return (jaro_winkler * 0.5 + levenshtein * 0.3 + token_similarity * 0.2)
    
    def calculate_category_matches(self, resume_skills: Set[str], job_skills: Set[str]) -> float:
        """Calculate skill category matches"""
        
        categories = self.nlp._technical_skills
        
        resume_categories = set()
        job_categories = set()
        
        # Map skills to categories
        for skill in resume_skills:
            for category, skills in categories.items():
                if skill in skills:
                    resume_categories.add(category)
                    break
        
        for skill in job_skills:
            for category, skills in categories.items():
                if skill in skills:
                    job_categories.add(category)
                    break
        
        if not job_categories:
            return 0.0
        
        return len(resume_categories.intersection(job_categories)) / len(job_categories)
    
    def extract_requirements(self, job_description: str) -> Dict:
        """Extract specific requirements from job description"""
        
        requirements = {
            'experience_years': 0,
            'education_level': '',
            'skills_required': [],
            'certifications': []
        }
        
        # Extract years of experience
        exp_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'experience\s*(?:of\s*)?(\d+)\+?\s*years?',
            r'(\d+)\s*-\s*(\d+)\s*years?\s*experience'
        ]
        
        for pattern in exp_patterns:
            match = re.search(pattern, job_description, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 2:
                        requirements['experience_years'] = int(match.group(2))
                    else:
                        requirements['experience_years'] = int(match.group(1))
                    break
                except:
                    pass
        
        # Extract education level
        edu_patterns = [
            r'bachelor[\'’]?s?\s*(?:degree|in)',
            r'master[\'’]?s?\s*(?:degree|in)',
            r'ph\.?d\.?\s*(?:degree|in)?',
            r'high school|diploma|associate'
        ]
        
        for pattern in edu_patterns:
            if re.search(pattern, job_description, re.IGNORECASE):
                requirements['education_level'] = pattern.split()[0]
                break
        
        return requirements
    
    def detect_industry(self, job_description: str) -> List[str]:
        """Detect industry from job description"""
        
        industries = []
        desc_lower = job_description.lower()
        
        for industry, keywords in self.industry_keywords.items():
            keyword_count = sum(1 for keyword in keywords if keyword in desc_lower)
            if keyword_count >= 3:  # Threshold for industry detection
                industries.append(industry)
        
        return industries if industries else ['general']
    
    def detect_experience_level(self, job_description: str) -> str:
        """Detect required experience level"""
        
        desc_lower = job_description.lower()
        
        level_keywords = {
            'entry': ['entry level', 'junior', 'trainee', 'graduate', 'fresher'],
            'mid': ['mid-level', 'experienced', '3-5 years', '5+ years'],
            'senior': ['senior', 'lead', 'principal', '10+ years'],
            'executive': ['director', 'vp', 'cto', 'head of', 'executive']
        }
        
        for level, keywords in level_keywords.items():
            for keyword in keywords:
                if keyword in desc_lower:
                    return level
        
        return 'mid'  # Default
    
    def extract_education_requirements(self, job_description: str) -> Dict:
        """Extract education requirements"""
        
        requirements = {
            'degree': '',
            'field': '',
            'required': False
        }
        
        # Check for degree requirements
        degree_patterns = {
            'bachelor': r'bachelor[\'’]?s?\s*(?:degree|in)\s*([\w\s]+)',
            'master': r'master[\'’]?s?\s*(?:degree|in)\s*([\w\s]+)',
            'phd': r'ph\.?d\.?\s*(?:in|degree in)?\s*([\w\s]+)'
        }
        
        for degree_type, pattern in degree_patterns.items():
            match = re.search(pattern, job_description, re.IGNORECASE)
            if match:
                requirements['degree'] = degree_type
                requirements['field'] = match.group(1).strip()
                requirements['required'] = True
                break
        
        return requirements
    
    def extract_job_titles(self, job_description: str) -> List[str]:
        """Extract job titles from description"""
        
        titles = []
        
        # Common title patterns
        title_patterns = [
            r'([A-Z][\w\s&]+(?:Manager|Engineer|Developer|Analyst|Specialist|Director|Lead|Head))',
            r'position[:\s]+([^\n]+)',
            r'role[:\s]+([^\n]+)',
            r'looking for\s+([^\n]+)'
        ]
        
        for pattern in title_patterns:
            matches = re.findall(pattern, job_description, re.IGNORECASE)
            titles.extend([match.strip() for match in matches])
        
        return list(set(titles))
    
    def apply_scoring_curve(self, score: float) -> float:
        """Apply curve to make scores more realistic"""
        
        # Sigmoid curve adjustment
        adjusted = 1 / (1 + math.exp(-8 * (score - 0.5)))
        
        # Ensure reasonable distribution
        if adjusted < 0.3:
            return adjusted * 0.8  # Lower scores get slightly reduced
        elif adjusted > 0.8:
            return 0.8 + (adjusted - 0.8) * 0.5  # Very high scores capped
        else:
            return adjusted
    
    def get_grade_and_recommendation(self, score: float) -> Tuple[str, str]:
        """Get grade and recommendation based on score"""
        
        if score >= 85:
            return 'A+', 'Highly Recommended - Excellent Match'
        elif score >= 75:
            return 'A', 'Strongly Recommended - Very Good Match'
        elif score >= 65:
            return 'B+', 'Recommended - Good Match'
        elif score >= 55:
            return 'B', 'Consider - Moderate Match'
        elif score >= 45:
            return 'C+', 'Consider with Reservations - Fair Match'
        elif score >= 35:
            return 'C', 'Needs Improvement - Weak Match'
        else:
            return 'D', 'Not Recommended - Poor Match'
    
    def identify_missing_skills(self, resume_data: Dict, job_analysis: Dict) -> List[str]:
        """Identify skills missing from resume"""
        
        resume_skills = set(resume_data.get('skills', []))
        job_skills = set(job_analysis.get('skills', []))
        
        missing = job_skills - resume_skills
        
        # Also check for partial matches
        partial_missing = []
        for job_skill in job_skills:
            found = False
            for resume_skill in resume_skills:
                if self.calculate_string_similarity(job_skill, resume_skill) > 0.6:
                    found = True
                    break
            if not found and job_skill not in missing:
                partial_missing.append(job_skill)
        
        return list(missing) + partial_missing[:5]  # Return top missing skills
    
    def identify_matched_skills(self, resume_data: Dict, job_analysis: Dict) -> List[str]:
        """Identify skills that match job requirements"""
        
        resume_skills = set(resume_data.get('skills', []))
        job_skills = set(job_analysis.get('skills', []))
        
        exact_matches = resume_skills.intersection(job_skills)
        
        # Also include partial matches
        partial_matches = set()
        for resume_skill in resume_skills:
            for job_skill in job_skills:
                if self.calculate_string_similarity(resume_skill, job_skill) > 0.7:
                    partial_matches.add(resume_skill)
                    break
        
        all_matches = exact_matches.union(partial_matches)
        return list(all_matches)[:10]  # Return top matches
    
    def identify_strengths(self, scores: Dict) -> List[str]:
        """Identify strength areas based on scores"""
        
        strengths = []
        
        if scores['skills_match'] >= 0.7:
            strengths.append('Strong technical skills match')
        if scores['experience_relevance'] >= 0.7:
            strengths.append('Relevant work experience')
        if scores['education_match'] >= 0.7:
            strengths.append('Strong educational background')
        if scores['keyword_similarity'] >= 0.7:
            strengths.append('Good keyword alignment')
        if scores['formatting_score'] >= 0.7:
            strengths.append('Well-formatted resume')
        
        return strengths if strengths else ['Solid overall profile']
    
    def identify_improvements(self, scores: Dict, missing_skills: List) -> List[str]:
        """Identify areas for improvement"""
        
        improvements = []
        
        if scores['skills_match'] < 0.5:
            improvements.append('Add more relevant technical skills')
        if scores['experience_relevance'] < 0.5:
            improvements.append('Highlight more relevant experience')
        if scores['education_match'] < 0.5:
            improvements.append('Consider additional education or certifications')
        
        if missing_skills:
            improvements.append(f'Learn missing skills: {", ".join(missing_skills[:3])}')
        
        return improvements if improvements else ['Continue professional development']
    
    def assess_industry_fit(self, resume_data: Dict, job_analysis: Dict) -> str:
        """Assess industry fit"""
        
        job_industries = job_analysis.get('industry', ['general'])
        resume_skills = set(resume_data.get('skills', []))
        
        # Count industry-specific skills
        industry_skill_counts = {}
        
        for industry, keywords in self.industry_keywords.items():
            count = sum(1 for keyword in keywords if any(skill in keyword for skill in resume_skills))
            industry_skill_counts[industry] = count
        
        # Find best matching industry
        best_industry = max(industry_skill_counts.items(), key=lambda x: x[1])
        
        if best_industry[1] >= 5:
            return 'Excellent industry fit'
        elif best_industry[1] >= 3:
            return 'Good industry fit'
        else:
            return 'General fit - transferable skills'
    
    def determine_experience_level(self, resume_data: Dict) -> str:
        """Determine experience level from resume"""
        
        experiences = resume_data.get('experience', [])
        
        if not experiences:
            return 'entry'
        
        # Calculate total experience in months
        total_months = sum(exp.get('duration_months', 0) for exp in experiences)
        total_years = total_months / 12
        
        if total_years >= 10:
            return 'senior'
        elif total_years >= 5:
            return 'mid'
        elif total_years >= 2:
            return 'junior'
        else:
            return 'entry'
