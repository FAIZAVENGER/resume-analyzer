import spacy
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from textblob import TextBlob
import re
from collections import Counter
import string
import json
import os
from typing import List, Dict, Tuple, Set, Optional
import numpy as np

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger')

class NLPProcessor:
    """Advanced NLP processor for resume analysis"""
    
    _nlp = None
    _stop_words = None
    _lemmatizer = None
    
    @classmethod
    def initialize_model(cls):
        """Initialize SpaCy model and NLTK components"""
        try:
            cls._nlp = spacy.load('en_core_web_md')
            print("✅ SpaCy model loaded successfully")
        except:
            print("⚠️ SpaCy model not found. Downloading...")
            os.system('python -m spacy download en_core_web_md')
            cls._nlp = spacy.load('en_core_web_md')
        
        cls._stop_words = set(stopwords.words('english'))
        cls._lemmatizer = WordNetLemmatizer()
        
        # Extended technical skills dictionary
        cls._technical_skills = cls._load_skills_dictionary()
        
    @classmethod
    def _load_skills_dictionary(cls):
        """Load comprehensive skills dictionary"""
        skills = {
            'programming': {
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'php',
                'swift', 'kotlin', 'go', 'rust', 'scala', 'r', 'matlab', 'perl', 'bash',
                'shell', 'powershell', 'html', 'css', 'sql', 'nosql', 'graphql', 'rest'
            },
            'frameworks': {
                'react', 'angular', 'vue', 'django', 'flask', 'spring', 'laravel', 'express',
                'node.js', 'asp.net', 'ruby on rails', 'tensorflow', 'pytorch', 'keras',
                'pandas', 'numpy', 'scikit-learn', 'docker', 'kubernetes', 'terraform',
                'ansible', 'jenkins', 'gitlab', 'github actions', 'aws', 'azure', 'gcp'
            },
            'databases': {
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'cassandra',
                'oracle', 'sql server', 'dynamodb', 'firebase', 'cosmosdb', 'snowflake'
            },
            'cloud': {
                'aws', 'amazon web services', 'azure', 'google cloud', 'gcp',
                'cloudformation', 's3', 'ec2', 'lambda', 'rds', 'vpc', 'iam',
                'kubernetes', 'docker', 'terraform', 'ansible', 'ci/cd', 'devops'
            },
            'tools': {
                'git', 'docker', 'jenkins', 'jira', 'confluence', 'slack', 'trello',
                'postman', 'swagger', 'figma', 'adobe xd', 'sketch', 'tableau',
                'power bi', 'excel', 'word', 'powerpoint', 'outlook'
            },
            'soft_skills': {
                'communication', 'leadership', 'teamwork', 'problem solving',
                'critical thinking', 'creativity', 'adaptability', 'time management',
                'project management', 'analytical skills', 'attention to detail',
                'collaboration', 'initiative', 'work ethic', 'professionalism'
            }
        }
        return skills
    
    @classmethod
    def extract_entities(cls, text: str) -> Dict:
        """Extract named entities from text using SpaCy"""
        if not cls._nlp:
            cls.initialize_model()
        
        doc = cls._nlp(text)
        
        entities = {
            'persons': [],
            'organizations': [],
            'dates': [],
            'locations': [],
            'emails': [],
            'phones': [],
            'urls': [],
            'education': [],
            'experience': [],
            'skills': []
        }
        
        # Extract SpaCy entities
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                entities['persons'].append(ent.text)
            elif ent.label_ == 'ORG':
                entities['organizations'].append(ent.text)
            elif ent.label_ == 'DATE':
                entities['dates'].append(ent.text)
            elif ent.label_ == 'GPE' or ent.label_ == 'LOC':
                entities['locations'].append(ent.text)
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities['emails'] = re.findall(email_pattern, text)
        
        # Extract phone numbers (international format)
        phone_pattern = r'(\+\d{1,3}[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b'
        entities['phones'] = re.findall(phone_pattern, text)
        
        # Extract URLs
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.\-?=%&+#]*'
        entities['urls'] = re.findall(url_pattern, text)
        
        # Extract education (degrees, universities)
        education_keywords = {
            'bachelor', 'bs', 'b.s.', 'b.a.', 'ba', 'master', 'ms', 'm.s.', 'm.a.', 'ma',
            'phd', 'doctorate', 'mba', 'associate', 'diploma', 'certificate', 'degree',
            'university', 'college', 'institute', 'school'
        }
        
        sentences = sent_tokenize(text)
        for sentence in sentences:
            lower_sentence = sentence.lower()
            if any(keyword in lower_sentence for keyword in education_keywords):
                entities['education'].append(sentence.strip())
        
        # Extract experience (job titles, durations)
        experience_patterns = [
            r'(\d+)\+?\s*(years?|yrs?)\s+experience',
            r'worked at\s+([A-Z][a-zA-Z\s&]+)',
            r'(\w+)\s+at\s+([A-Z][a-zA-Z\s&]+)',
            r'(\d{4})\s*[-–]\s*(present|\d{4})'
        ]
        
        for pattern in experience_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities['experience'].append(match.group())
        
        # Extract skills
        entities['skills'] = cls.extract_skills(text)
        
        return entities
    
    @classmethod
    def extract_skills(cls, text: str) -> List[str]:
        """Extract technical and soft skills from text"""
        if not cls._nlp:
            cls.initialize_model()
        
        text_lower = text.lower()
        found_skills = set()
        
        # Check for technical skills
        for category, skills in cls._technical_skills.items():
            for skill in skills:
                skill_pattern = r'\b' + re.escape(skill) + r'\b'
                if re.search(skill_pattern, text_lower):
                    found_skills.add(skill)
        
        # Use SpaCy for additional skill extraction
        doc = cls._nlp(text_lower)
        
        # Extract noun chunks that might be skills
        for chunk in doc.noun_chunks:
            chunk_text = chunk.text.lower().strip()
            if len(chunk_text.split()) <= 3:  # Skills are usually short phrases
                # Check if it contains skill indicators
                skill_indicators = {'skill', 'experience', 'knowledge', 'proficient', 'familiar'}
                if any(indicator in chunk_text for indicator in skill_indicators):
                    found_skills.add(chunk_text)
        
        # Extract verbs that might indicate skills (using POS tagging)
        for token in doc:
            if token.pos_ == 'VERB' and token.lemma_ not in cls._stop_words:
                # Common skill-related verbs
                skill_verbs = {'develop', 'design', 'implement', 'create', 'build', 
                              'manage', 'lead', 'analyze', 'optimize', 'deploy'}
                if token.lemma_ in skill_verbs:
                    found_skills.add(token.lemma_)
        
        return list(found_skills)
    
    @classmethod
    def extract_keywords(cls, text: str, top_n: int = 20) -> List[Tuple[str, float]]:
        """Extract important keywords with TF-IDF like scoring"""
        if not cls._nlp:
            cls.initialize_model()
        
        # Clean text
        text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Tokenize and remove stopwords
        tokens = [token for token in word_tokenize(text_clean) 
                 if token not in cls._stop_words and len(token) > 2]
        
        # Lemmatize
        tokens = [cls._lemmatizer.lemmatize(token) for token in tokens]
        
        # Count frequencies
        freq_dist = Counter(tokens)
        
        # Calculate TF-IDF like scores
        total_tokens = len(tokens)
        unique_tokens = len(freq_dist)
        
        scores = {}
        for word, freq in freq_dist.items():
            # TF (Term Frequency)
            tf = freq / total_tokens
            
            # Simple IDF approximation
            idf = np.log((unique_tokens + 1) / (freq + 1)) + 1
            
            # Score
            scores[word] = tf * idf
        
        # Return top N keywords
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    @classmethod
    def analyze_sentiment(cls, text: str) -> Dict:
        """Analyze sentiment of text"""
        blob = TextBlob(text)
        sentiment = blob.sentiment
        
        return {
            'polarity': sentiment.polarity,  # -1 to 1
            'subjectivity': sentiment.subjectivity,  # 0 to 1
            'sentiment': 'positive' if sentiment.polarity > 0.1 else 
                        'negative' if sentiment.polarity < -0.1 else 'neutral'
        }
    
    @classmethod
    def calculate_readability(cls, text: str) -> Dict:
        """Calculate readability scores"""
        sentences = sent_tokenize(text)
        words = word_tokenize(text)
        
        num_sentences = len(sentences)
        num_words = len(words)
        
        if num_sentences == 0:
            return {
                'flesch_reading_ease': 0,
                'flesch_kincaid_grade': 0,
                'avg_sentence_length': 0,
                'avg_word_length': 0
            }
        
        # Count syllables (approximate)
        syllable_count = 0
        for word in words:
            word_lower = word.lower()
            vowels = 'aeiouy'
            if word_lower:
                if word_lower[0] in vowels:
                    syllable_count += 1
                for index in range(1, len(word_lower)):
                    if word_lower[index] in vowels and word_lower[index-1] not in vowels:
                        syllable_count += 1
                if word_lower.endswith('e'):
                    syllable_count -= 1
                if word_lower.endswith('le') and len(word_lower) > 2 and word_lower[-3] not in vowels:
                    syllable_count += 1
                if syllable_count == 0:
                    syllable_count += 1
        
        # Flesch Reading Ease
        flesch_ease = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (syllable_count / num_words)
        
        # Flesch-Kincaid Grade Level
        flesch_grade = 0.39 * (num_words / num_sentences) + 11.8 * (syllable_count / num_words) - 15.59
        
        return {
            'flesch_reading_ease': max(0, min(100, flesch_ease)),
            'flesch_kincaid_grade': max(0, flesch_grade),
            'avg_sentence_length': num_words / num_sentences,
            'avg_word_length': sum(len(word) for word in words) / num_words
        }
    
    @classmethod
    def extract_sections(cls, text: str) -> Dict[str, str]:
        """Extract resume sections"""
        sections = {
            'contact': '',
            'summary': '',
            'experience': '',
            'education': '',
            'skills': '',
            'projects': '',
            'certifications': ''
        }
        
        # Common section headers
        section_patterns = {
            'contact': r'(?:contact|personal)\s*(?:information|details)?',
            'summary': r'(?:summary|profile|objective|about)\s*(?:me)?',
            'experience': r'(?:experience|work\s*experience|employment\s*history)',
            'education': r'(?:education|academic\s*background|qualifications)',
            'skills': r'(?:skills|technical\s*skills|competencies)',
            'projects': r'(?:projects|portfolio|work\s*portfolio)',
            'certifications': r'(?:certifications|certificates|licenses)'
        }
        
        lines = text.split('\n')
        current_section = None
        
        for line in lines:
            line_lower = line.strip().lower()
            
            # Check if this line starts a new section
            for section, pattern in section_patterns.items():
                if re.match(pattern, line_lower, re.IGNORECASE):
                    current_section = section
                    break
            
            # Add line to current section
            if current_section and line.strip():
                sections[current_section] += line + '\n'
        
        return sections
    
    @classmethod
    def calculate_text_quality(cls, text: str) -> Dict:
        """Calculate text quality metrics"""
        # Remove extra whitespace
        text_clean = re.sub(r'\s+', ' ', text.strip())
        
        # Calculate metrics
        word_count = len(text_clean.split())
        char_count = len(text_clean)
        sentence_count = len(sent_tokenize(text_clean))
        
        # Unique words
        words = text_clean.lower().split()
        unique_words = len(set(words))
        
        # Word diversity
        word_diversity = unique_words / max(1, word_count)
        
        # Grammar score (simplified)
        grammar_score = min(1.0, word_diversity * 2)  # Simplified
        
        # Keyword density
        keywords = cls.extract_keywords(text, top_n=10)
        keyword_density = len(keywords) / max(1, word_count)
        
        return {
            'word_count': word_count,
            'char_count': char_count,
            'sentence_count': sentence_count,
            'unique_words': unique_words,
            'word_diversity': word_diversity,
            'grammar_score': grammar_score,
            'keyword_density': keyword_density,
            'readability': cls.calculate_readability(text)
        }
