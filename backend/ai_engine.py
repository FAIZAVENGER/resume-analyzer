import json
import re
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime
from .nlp_processor import NLPProcessor
from .scoring_engine import ScoringEngine
from .resume_parser import ResumeParser

class AIEngine:
    """Main AI Engine that orchestrates all analysis"""
    
    def __init__(self):
        self.nlp = NLPProcessor()
        self.scoring = ScoringEngine()
        self.parser = ResumeParser()
        
        # Load predefined templates and patterns
        self._load_templates()
    
    def _load_templates(self):
        """Load analysis templates and patterns"""
        self.analysis_templates = {
            'summary': {
                'excellent': "Candidate demonstrates exceptional qualifications with strong alignment to job requirements.",
                'good': "Candidate shows good qualifications with relevant experience and skills.",
                'average': "Candidate has relevant background but could benefit from additional experience.",
                'needs_improvement': "Candidate needs to develop more relevant skills and experience."
            },
            'recommendations': {
                'hire': "Strongly recommend for immediate hiring consideration.",
                'interview': "Recommend for interview to assess cultural fit and soft skills.",
                'consider': "Consider for junior role or with additional training.",
                'reject': "Does not meet minimum requirements for this position."
            }
        }
    
    def analyze_resume(self, resume_text: str, job_description: str, filename: str = None) -> Dict:
        """Complete AI analysis of resume against job description"""
        
        print(f"🤖 Starting AI analysis for {filename or 'resume'}")
        
        # Parse resume
        resume_data = self.parser.analyze_resume(resume_text)
        
        # Calculate scores
        score_results = self.scoring.calculate_score(resume_data, job_description)
        
        # Generate comprehensive analysis
        analysis = self.generate_analysis(resume_data, score_results, filename)
        
        # Add metadata
        analysis['ai_engine'] = 'ResumeAnalyzer AI v2.0'
        analysis['analysis_timestamp'] = datetime.now().isoformat()
        analysis['model_version'] = '2.0.0'
        analysis['analysis_depth'] = 'comprehensive'
        
        print(f"✅ AI analysis complete: {analysis['candidate_name']} - Score: {analysis['overall_score']}")
        
        return analysis
    
    def analyze_batch(self, resumes: List[Dict], job_description: str) -> List[Dict]:
        """Analyze batch of resumes"""
        
        print(f"🤖 Starting batch analysis of {len(resumes)} resumes")
        
        all_analyses = []
        
        for i, resume_data in enumerate(resumes):
            try:
                analysis = self.analyze_resume(
                    resume_data.get('text', ''),
                    job_description,
                    resume_data.get('filename', f'resume_{i+1}')
                )
                all_analyses.append(analysis)
                
            except Exception as e:
                print(f"❌ Error analyzing resume {i+1}: {str(e)}")
                # Add fallback analysis
                all_analyses.append(self.generate_fallback_analysis(
                    resume_data.get('filename', f'resume_{i+1}'),
                    str(e)
                ))
        
        # Sort by score
        all_analyses.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        # Add ranking
        for rank, analysis in enumerate(all_analyses, 1):
            analysis['rank'] = rank
        
        return all_analyses
    
    def generate_analysis(self, resume_data: Dict, score_results: Dict, filename: str = None) -> Dict:
        """Generate comprehensive analysis report"""
        
        # Extract candidate name
        candidate_name = self.extract_candidate_name(resume_data, filename)
        
        # Generate summaries
        experience_summary = self.generate_experience_summary(resume_data)
        education_summary = self.generate_education_summary(resume_data)
        
        # Get strengths and improvements
        strengths = score_results.get('strength_areas', [])
        improvements = score_results.get('improvement_areas', [])
        
        # Get matched and missing skills
        matched_skills = score_results.get('matched_skills', [])[:5]
        missing_skills = score_results.get('missing_skills', [])[:5]
        
        # Generate personalized recommendation
        recommendation = self.generate_recommendation(score_results['overall_score'])
        
        # Calculate ATS score with confidence
        ats_score = score_results['overall_score']
        confidence = self.calculate_confidence(score_results['detailed_scores'])
        
        # Generate career advice
        career_advice = self.generate_career_advice(resume_data, score_results)
        
        # Generate industry insights
        industry_insights = self.generate_industry_insights(resume_data, score_results)
        
        # Compile final analysis
        analysis = {
            'candidate_name': candidate_name,
            'overall_score': ats_score,
            'score_confidence': confidence,
            'grade': score_results.get('grade', 'B'),
            'recommendation': recommendation,
            'experience_summary': experience_summary,
            'education_summary': education_summary,
            'skills_matched': matched_skills,
            'skills_missing': missing_skills,
            'key_strengths': strengths,
            'areas_for_improvement': improvements,
            'career_advice': career_advice,
            'industry_insights': industry_insights,
            'experience_level': score_results.get('experience_level', 'Mid'),
            'industry_fit': score_results.get('industry_fit', 'Good'),
            'detailed_scores': score_results.get('detailed_scores', {}),
            'resume_quality': self.assess_resume_quality(resume_data),
            'skill_gaps': self.identify_skill_gaps(matched_skills, missing_skills),
            'salary_expectations': self.estimate_salary_range(resume_data, score_results),
            'interview_prep': self.generate_interview_prep(resume_data, score_results)
        }
        
        return analysis
    
    def extract_candidate_name(self, resume_data: Dict, filename: str = None) -> str:
        """Extract candidate name from resume data"""
        
        # Try to get from personal info
        personal_info = resume_data.get('personal_info', {})
        name = personal_info.get('name', '')
        
        if name:
            return name.title()
        
        # Try to extract from filename
        if filename:
            # Remove extension and common words
            base_name = filename.split('.')[0]
            base_name = re.sub(r'[_-]', ' ', base_name)
            base_name = re.sub(r'\b(resume|cv|application)\b', '', base_name, flags=re.IGNORECASE)
            base_name = base_name.strip()
            
            if base_name and len(base_name.split()) <= 4:
                return base_name.title()
        
        # Fallback
        return 'Professional Candidate'
    
    def generate_experience_summary(self, resume_data: Dict) -> str:
        """Generate experience summary"""
        
        experiences = resume_data.get('experience', [])
        
        if not experiences:
            return "Limited professional experience. Consider highlighting projects, internships, or academic achievements."
        
        # Calculate total experience
        total_months = sum(exp.get('duration_months', 0) for exp in experiences)
        total_years = total_months / 12
        
        # Get most recent role
        latest_exp = experiences[0] if experiences else {}
        latest_role = latest_exp.get('title', '')
        latest_company = latest_exp.get('company', '')
        
        # Count unique companies
        companies = set(exp.get('company', '') for exp in experiences if exp.get('company'))
        
        if total_years >= 10:
            return f"Senior professional with {int(total_years)}+ years of experience across {len(companies)} organizations. Most recently as {latest_role} at {latest_company}."
        elif total_years >= 5:
            return f"Experienced professional with {int(total_years)}+ years in the industry. Current role: {latest_role} at {latest_company}."
        elif total_years >= 2:
            return f"Developing professional with {int(total_years)}+ years of experience. Currently serving as {latest_role} at {latest_company}."
        else:
            return f"Early-career professional with experience as {latest_role} at {latest_company}. Shows strong potential for growth."
    
    def generate_education_summary(self, resume_data: Dict) -> str:
        """Generate education summary"""
        
        education_list = resume_data.get('education', [])
        
        if not education_list:
            return "Education background not specified. Consider adding relevant educational qualifications."
        
        # Get highest degree
        degrees = []
        for edu in education_list:
            degree = edu.get('degree', '')
            if degree:
                degrees.append(degree)
        
        if degrees:
            highest_degree = max(degrees, key=lambda x: self._get_degree_level(x))
            
            # Get institution for highest degree
            for edu in education_list:
                if edu.get('degree', '') == highest_degree:
                    institution = edu.get('institution', '')
                    gpa = edu.get('gpa', '')
                    
                    summary = f"Holds a {highest_degree}"
                    if institution:
                        summary += f" from {institution}"
                    if gpa and float(gpa) >= 3.0:
                        summary += f" with a GPA of {gpa}"
                    summary += "."
                    
                    return summary
        
        return "Has completed relevant educational qualifications."
    
    def _get_degree_level(self, degree: str) -> int:
        """Get level of degree for comparison"""
        degree_lower = degree.lower()
        
        if 'phd' in degree_lower or 'doctorate' in degree_lower:
            return 5
        elif 'master' in degree_lower or 'mba' in degree_lower:
            return 4
        elif 'bachelor' in degree_lower or 'bs' in degree_lower or 'ba' in degree_lower:
            return 3
        elif 'associate' in degree_lower:
            return 2
        elif 'diploma' in degree_lower or 'certificate' in degree_lower:
            return 1
        else:
            return 0
    
    def generate_recommendation(self, score: float) -> str:
        """Generate personalized recommendation"""
        
        if score >= 85:
            return "Highly Recommended - Exceptional candidate with perfect skill alignment"
        elif score >= 75:
            return "Strongly Recommended - Excellent match with minor skill gaps"
        elif score >= 65:
            return "Recommended - Good overall fit with some development areas"
        elif score >= 55:
            return "Consider - Moderate match, evaluate based on specific needs"
        elif score >= 45:
            return "Consider with Training - Requires skill development but has potential"
        elif score >= 35:
            return "Needs Improvement - Significant skill gaps, consider for junior role"
        else:
            return "Not Recommended - Does not meet minimum requirements"
    
    def calculate_confidence(self, detailed_scores: Dict) -> float:
        """Calculate confidence in the analysis"""
        
        # Base confidence on score consistency
        scores = list(detailed_scores.values())
        
        if not scores:
            return 0.7
        
        mean_score = np.mean(scores)
        std_dev = np.std(scores)
        
        # High confidence if scores are consistent
        if std_dev < 0.15:
            confidence = 0.9
        elif std_dev < 0.25:
            confidence = 0.8
        else:
            confidence = 0.7
        
        # Adjust based on mean score
        confidence *= (0.8 + (mean_score * 0.2))
        
        return min(0.95, confidence)
    
    def generate_career_advice(self, resume_data: Dict, score_results: Dict) -> List[str]:
        """Generate personalized career advice"""
        
        advice = []
        
        # Based on experience level
        exp_level = score_results.get('experience_level', 'mid')
        
        if exp_level == 'entry':
            advice.append("Focus on building a strong portfolio with personal projects")
            advice.append("Consider internships or freelance work to gain practical experience")
            advice.append("Obtain relevant certifications to demonstrate commitment")
        elif exp_level == 'junior':
            advice.append("Seek mentorship opportunities to accelerate growth")
            advice.append("Take on more responsibility in current role")
            advice.append("Develop specialized skills in high-demand areas")
        elif exp_level == 'mid':
            advice.append("Consider leadership or mentorship roles")
            advice.append("Develop expertise in emerging technologies")
            advice.append("Build cross-functional collaboration experience")
        else:  # senior
            advice.append("Focus on strategic impact and business outcomes")
            advice.append("Develop thought leadership through speaking/writing")
            advice.append("Mentor junior team members to build leadership skills")
        
        # Based on skill gaps
        missing_skills = score_results.get('missing_skills', [])
        if missing_skills:
            advice.append(f"Prioritize learning: {', '.join(missing_skills[:3])}")
        
        # Based on industry fit
        industry_fit = score_results.get('industry_fit', '')
        if 'transferable' in industry_fit.lower():
            advice.append("Highlight transferable skills in applications")
        
        return advice[:5]  # Limit to top 5 advice points
    
    def generate_industry_insights(self, resume_data: Dict, score_results: Dict) -> Dict:
        """Generate industry-specific insights"""
        
        skills = resume_data.get('skills', [])
        
        # Categorize skills
        tech_skills = [s for s in skills if self._is_technical_skill(s)]
        soft_skills = [s for s in skills if self._is_soft_skill(s)]
        tool_skills = [s for s in skills if self._is_tool_skill(s)]
        
        # Industry demand analysis (simplified)
        high_demand = []
        moderate_demand = []
        
        # Check against in-demand skills
        in_demand_skills = {
            'python', 'javascript', 'aws', 'react', 'docker', 'kubernetes',
            'machine learning', 'data analysis', 'cloud computing', 'devops'
        }
        
        for skill in tech_skills:
            if skill in in_demand_skills:
                high_demand.append(skill)
            else:
                moderate_demand.append(skill)
        
        return {
            'high_demand_skills': high_demand[:5],
            'moderate_demand_skills': moderate_demand[:5],
            'technical_skills_count': len(tech_skills),
            'soft_skills_count': len(soft_skills),
            'tools_proficiency': len(tool_skills),
            'market_alignment': 'Strong' if len(high_demand) >= 3 else 'Moderate'
        }
    
    def _is_technical_skill(self, skill: str) -> bool:
        """Check if skill is technical"""
        technical_indicators = {'programming', 'development', 'engineering', 'analysis', 
                               'design', 'architecture', 'database', 'cloud', 'security'}
        skill_lower = skill.lower()
        return any(indicator in skill_lower for indicator in technical_indicators)
    
    def _is_soft_skill(self, skill: str) -> bool:
        """Check if skill is soft skill"""
        soft_indicators = {'communication', 'leadership', 'teamwork', 'problem solving',
                          'management', 'collaboration', 'adaptability', 'creativity'}
        skill_lower = skill.lower()
        return any(indicator in skill_lower for indicator in soft_indicators)
    
    def _is_tool_skill(self, skill: str) -> bool:
        """Check if skill is tool proficiency"""
        tool_indicators = {'git', 'docker', 'jenkins', 'jira', 'confluence', 'slack',
                          'postman', 'figma', 'tableau', 'excel', 'powerpoint'}
        skill_lower = skill.lower()
        return any(indicator in skill_lower for indicator in tool_indicators)
    
    def assess_resume_quality(self, resume_data: Dict) -> Dict:
        """Assess resume quality"""
        
        quality = resume_data.get('quality_metrics', {})
        sections = resume_data.get('sections', {})
        
        # Check for important sections
        important_sections = ['experience', 'education', 'skills']
        missing_sections = [s for s in important_sections if not sections.get(s)]
        
        # Word count assessment
        word_count = quality.get('word_count', 0)
        if 400 <= word_count <= 800:
            length_score = 'Optimal'
        elif word_count < 300:
            length_score = 'Too Short'
        else:
            length_score = 'Too Long'
        
        # Readability assessment
        readability = quality.get('readability', {})
        flesch_ease = readability.get('flesch_reading_ease', 0)
        if flesch_ease >= 60:
            readability_score = 'Excellent'
        elif flesch_ease >= 50:
            readability_score = 'Good'
        else:
            readability_score = 'Needs Improvement'
        
        return {
            'overall_quality': 'Good' if len(missing_sections) == 0 else 'Needs Improvement',
            'length_assessment': length_score,
            'readability': readability_score,
            'missing_sections': missing_sections,
            'word_count': word_count,
            'grammar_score': quality.get('grammar_score', 0),
            'keyword_density': quality.get('keyword_density', 0)
        }
    
    def identify_skill_gaps(self, matched_skills: List[str], missing_skills: List[str]) -> Dict:
        """Identify skill gaps and development path"""
        
        return {
            'critical_gaps': missing_skills[:3],
            'partial_gaps': missing_skills[3:6] if len(missing_skills) > 3 else [],
            'strengths': matched_skills[:5],
            'development_priority': 'High' if missing_skills else 'Medium',
            'time_to_close_gaps': self._estimate_time_to_close_gaps(missing_skills)
        }
    
    def _estimate_time_to_close_gaps(self, missing_skills: List[str]) -> str:
        """Estimate time to close skill gaps"""
        
        if not missing_skills:
            return 'No significant gaps identified'
        
        # Simple estimation based on number of skills
        num_skills = len(missing_skills)
        
        if num_skills <= 2:
            return '3-6 months with focused learning'
        elif num_skills <= 4:
            return '6-12 months with structured learning plan'
        else:
            return '12+ months - consider career transition or extensive training'
    
    def estimate_salary_range(self, resume_data: Dict, score_results: Dict) -> Dict:
        """Estimate salary range based on qualifications"""
        
        exp_level = score_results.get('experience_level', 'mid')
        industry_fit = score_results.get('industry_fit', 'Good')
        
        # Base salary ranges by experience level (in thousands)
        base_ranges = {
            'entry': (40, 65),
            'junior': (55, 85),
            'mid': (75, 120),
            'senior': (100, 180),
            'lead': (130, 220),
            'executive': (180, 350)
        }
        
        base_min, base_max = base_ranges.get(exp_level, (60, 100))
        
        # Adjust based on score
        score = score_results.get('overall_score', 50)
        adjustment_factor = score / 100
        
        adjusted_min = int(base_min * (0.8 + adjustment_factor * 0.4))
        adjusted_max = int(base_max * (0.8 + adjustment_factor * 0.4))
        
        # Adjust for industry fit
        if 'Excellent' in industry_fit:
            adjusted_min = int(adjusted_min * 1.1)
            adjusted_max = int(adjusted_max * 1.1)
        
        return {
            'range': f"${adjusted_min}K - ${adjusted_max}K",
            'currency': 'USD',
            'experience_level': exp_level.title(),
            'market_position': 'Competitive' if score >= 60 else 'Below Market',
            'negotiation_tips': self._generate_salary_tips(score, exp_level)
        }
    
    def _generate_salary_tips(self, score: float, exp_level: str) -> List[str]:
        """Generate salary negotiation tips"""
        
        tips = []
        
        if score >= 75:
            tips.append("You're in a strong position to negotiate above market rate")
            tips.append("Highlight your unique skills and accomplishments")
        elif score >= 60:
            tips.append("Research market rates for your experience level")
            tips.append("Be prepared to demonstrate your value")
        else:
            tips.append("Focus on skill development before salary negotiations")
            tips.append("Consider roles that offer growth opportunities")
        
        if exp_level in ['entry', 'junior']:
            tips.append("Prioritize learning opportunities over salary")
        elif exp_level in ['senior', 'lead']:
            tips.append("Emphasize leadership impact and business results")
        
        return tips
    
    def generate_interview_prep(self, resume_data: Dict, score_results: Dict) -> Dict:
        """Generate interview preparation guidance"""
        
        strengths = score_results.get('strength_areas', [])
        improvements = score_results.get('improvement_areas', [])
        matched_skills = score_results.get('matched_skills', [])
        
        # Generate likely questions
        likely_questions = []
        
        for skill in matched_skills[:3]:
            likely_questions.append(f"Describe your experience with {skill}")
        
        for strength in strengths[:2]:
            likely_questions.append(f"Can you give an example of when you demonstrated {strength.lower()}?")
        
        for improvement in improvements[:2]:
            likely_questions.append(f"How are you working to improve your {improvement.lower()}?")
        
        # Generate talking points
        talking_points = []
        
        experiences = resume_data.get('experience', [])
        if experiences:
            latest = experiences[0]
            talking_points.append(f"Highlight your role as {latest.get('title', '')} at {latest.get('company', '')}")
        
        projects = resume_data.get('projects', [])
        if projects:
            talking_points.append(f"Discuss your project: {projects[0].get('name', 'Recent Project')}")
        
        return {
            'likely_questions': likely_questions[:5],
            'talking_points': talking_points[:3],
            'strengths_to_highlight': strengths[:3],
            'weaknesses_to_address': improvements[:2],
            'research_topics': ['Company culture', 'Recent company news', 'Industry trends'],
            'follow_up_questions': [
                "What does success look like in this role?",
                "How does the team collaborate?",
                "What opportunities are there for professional development?"
            ]
        }
    
    def generate_fallback_analysis(self, filename: str, error: str = None) -> Dict:
        """Generate fallback analysis when main analysis fails"""
        
        return {
            'candidate_name': filename.split('.')[0].title(),
            'overall_score': 50,
            'grade': 'C',
            'recommendation': 'Analysis Incomplete - Manual Review Required',
            'experience_summary': 'Unable to extract experience details.',
            'education_summary': 'Educational background requires manual review.',
            'skills_matched': ['Basic analysis completed'],
            'skills_missing': ['Detailed analysis pending'],
            'key_strengths': ['Resume successfully processed'],
            'areas_for_improvement': ['Complete AI analysis unavailable'],
            'career_advice': ['Try re-uploading the resume', 'Check file format and content'],
            'ai_engine': 'ResumeAnalyzer AI (Fallback Mode)',
            'analysis_status': 'partial',
            'error_message': error or 'Unknown error'
        }
