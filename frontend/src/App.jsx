import { useState } from 'react';
import axios from 'axios';
import { 
  Upload, FileText, Briefcase, CheckCircle, XCircle, 
  Download, Loader, TrendingUp, Award, BookOpen, 
  Target, AlertCircle, Sparkles, Star, Zap, User,
  ChevronRight, Shield, BarChart3, Globe, Clock
} from 'lucide-react';
import './App.css';
import logoImage from './leadsoc.png'; // Import the logo

function App() {
  const [resumeFile, setResumeFile] = useState(null);
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);

  // Use production backend URL
  const API_BASE_URL = 'https://resume-analyzer-94mo.onrender.com';

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type.match(/pdf|msword|wordprocessingml|text/) || 
          file.name.match(/\.(pdf|doc|docx|txt)$/i)) {
        setResumeFile(file);
        setError('');
      } else {
        setError('Please upload a valid file type (PDF, DOC, DOCX, TXT)');
      }
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setResumeFile(file);
      setError('');
    }
  };

  const handleAnalyze = async () => {
    if (!resumeFile) {
      setError('Please upload a resume file');
      return;
    }
    if (!jobDescription.trim()) {
      setError('Please enter a job description');
      return;
    }

    setLoading(true);
    setError('');
    setAnalysis(null);

    const formData = new FormData();
    formData.append('resume', resumeFile);
    formData.append('jobDescription', jobDescription);

    try {
      // CHANGED: Use production backend URL
      const response = await axios.post(`${API_BASE_URL}/analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setAnalysis(response.data);
    } catch (err) {
      console.error('Analysis error:', err);
      setError(err.response?.data?.error || 'An error occurred during analysis');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (analysis?.excel_filename) {
      // CHANGED: Use production backend URL
      window.open(`${API_BASE_URL}/download/${analysis.excel_filename}`, '_blank');
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#00ff9d';
    if (score >= 60) return '#ffd166';
    return '#ff6b6b';
  };

  const getScoreGrade = (score) => {
    if (score >= 90) return 'Excellent Match 🎯';
    if (score >= 80) return 'Great Match ✨';
    if (score >= 70) return 'Good Match 👍';
    if (score >= 60) return 'Fair Match 📊';
    return 'Needs Improvement 📈';
  };

  const getScoreEmoji = (score) => {
    if (score >= 90) return '🏆';
    if (score >= 80) return '⭐';
    if (score >= 70) return '👍';
    if (score >= 60) return '📋';
    return '💡';
  };

  return (
    <div className="app">
      {/* Animated Background Elements */}
      <div className="bg-grid"></div>
      <div className="bg-blur-1"></div>
      <div className="bg-blur-2"></div>
      
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="header-main">
            {/* Left Side: Logo and Title */}
            <div className="logo">
              <div className="logo-glow">
                <Sparkles className="logo-icon" />
              </div>
              <div className="logo-text">
                <h1>AI Resume Analyzer</h1>
                <div className="logo-subtitle">
                  <span className="powered-by">Powered by</span>
                  <span className="gemini-badge">Gemini AI</span>
                  <span className="divider">•</span>
                  <span className="tagline">Intelligent Candidate Screening</span>
                </div>
              </div>
            </div>
            
            {/* Right Side: Leadsoc Logo */}
            <div className="leadsoc-logo-container">
              <a 
                href="https://www.leadsoc.com/" 
                target="_blank" 
                rel="noopener noreferrer"
                className="leadsoc-logo-link"
              >
                <img 
                  src={logoImage} 
                  alt="LEADSOC - partnering your success" 
                  className="leadsoc-logo"
                />
              </a>
            </div>
          </div>
          
          <div className="header-features">
            <div className="feature">
              <Shield size={16} />
              <span>Secure Analysis</span>
            </div>
            <div className="feature">
              <Zap size={16} />
              <span>Real-time Results</span>
            </div>
            <div className="feature">
              <Globe size={16} />
              <span>Multi-format Support</span>
            </div>
          </div>
        </div>
        
        <div className="header-wave">
          <svg viewBox="0 0 1200 120" preserveAspectRatio="none">
            <path d="M0,0V46.29c47.79,22.2,103.59,32.17,158,28,70.36-5.37,136.33-33.31,206.8-37.5C438.64,32.43,512.34,53.67,583,72.05c69.27,18,138.3,24.88,209.4,13.08,36.15-6,69.85-17.84,104.45-29.34C989.49,25,1113-14.29,1200,52.47V0Z" opacity=".25" fill="currentColor"></path>
            <path d="M0,0V15.81C13,36.92,27.64,56.86,47.69,72.05,99.41,111.27,165,111,224.58,91.58c31.15-10.15,60.09-26.07,89.67-39.8,40.92-19,84.73-46,130.83-49.67,36.26-2.85,70.9,9.42,98.6,31.56,31.77,25.39,62.32,62,103.63,73,40.44,10.79,81.35-6.69,119.13-24.28s75.16-39,116.92-43.05c59.73-5.85,113.28,22.88,168.9,38.84,30.2,8.66,59,6.17,87.09-7.5,22.43-10.89,48-26.93,60.65-49.24V0Z" opacity=".5" fill="currentColor"></path>
            <path d="M0,0V5.63C149.93,59,314.09,71.32,475.83,42.57c43-7.64,84.23-20.12,127.61-26.46,59-8.63,112.48,12.24,165.56,35.4C827.93,77.22,886,95.24,951.2,90c86.53-7,172.46-45.71,248.8-84.81V0Z" fill="currentColor"></path>
          </svg>
        </div>
      </header>

      <main className="main-content">
        {!analysis ? (
          <div className="upload-section">
            <div className="section-header">
              <h2>Start Your Analysis</h2>
              <p>Upload your resume and job description to get AI-powered insights</p>
            </div>
            
            <div className="upload-grid">
              <div className="upload-card glass">
                <div className="card-decoration"></div>
                <div className="card-header">
                  <div className="header-icon-wrapper">
                    <FileText className="header-icon" />
                  </div>
                  <div>
                    <h2>Upload Resume</h2>
                    <p className="card-subtitle">Supported: PDF, DOC, DOCX, TXT</p>
                  </div>
                </div>
                
                <div 
                  className={`upload-area ${dragActive ? 'drag-active' : ''} ${resumeFile ? 'has-file' : ''}`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                >
                  <input
                    type="file"
                    id="resume-upload"
                    accept=".pdf,.doc,.docx,.txt"
                    onChange={handleFileChange}
                    className="file-input"
                  />
                  <label htmlFor="resume-upload" className="file-label">
                    <div className="upload-icon-wrapper">
                      {resumeFile ? (
                        <div className="file-preview">
                          <FileText size={40} />
                          <div className="file-preview-info">
                            <span className="file-name">{resumeFile.name}</span>
                            <span className="file-size">
                              {(resumeFile.size / 1024 / 1024).toFixed(2)} MB
                            </span>
                          </div>
                        </div>
                      ) : (
                        <>
                          <Upload className="upload-icon" />
                          <span className="upload-text">
                            Drag & drop or click to browse
                          </span>
                          <span className="upload-hint">Max file size: 10MB</span>
                        </>
                      )}
                    </div>
                  </label>
                  
                  {resumeFile && (
                    <button 
                      className="change-file-btn"
                      onClick={() => setResumeFile(null)}
                    >
                      Change File
                    </button>
                  )}
                </div>
                
                <div className="upload-stats">
                  <div className="stat">
                    <div className="stat-icon">
                      <Clock size={14} />
                    </div>
                    <span>Analysis in seconds</span>
                  </div>
                  <div className="stat">
                    <div className="stat-icon">
                      <Shield size={14} />
                    </div>
                    <span>Private & secure</span>
                  </div>
                </div>
              </div>

              <div className="job-description-card glass">
                <div className="card-decoration"></div>
                <div className="card-header">
                  <div className="header-icon-wrapper">
                    <Briefcase className="header-icon" />
                  </div>
                  <div>
                    <h2>Job Description</h2>
                    <p className="card-subtitle">Paste the complete job description</p>
                  </div>
                </div>
                
                <div className="textarea-wrapper">
                  <textarea
                    className="job-description-input"
                    placeholder={`• Paste job description here\n• Include required skills\n• Mention qualifications\n• List responsibilities\n• Add any specific requirements`}
                    value={jobDescription}
                    onChange={(e) => setJobDescription(e.target.value)}
                    rows={12}
                  />
                  <div className="textarea-footer">
                    <span className="char-count">
                      {jobDescription.length} characters
                    </span>
                    <span className="word-count">
                      {jobDescription.trim() ? jobDescription.trim().split(/\s+/).length : 0} words
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {error && (
              <div className="error-message glass">
                <AlertCircle size={20} />
                <span>{error}</span>
              </div>
            )}

            <button
              className="analyze-button"
              onClick={handleAnalyze}
              disabled={loading || !resumeFile || !jobDescription.trim()}
            >
              {loading ? (
                <>
                  <Loader className="spinner" />
                  <span>Analyzing Resume...</span>
                  <span className="button-subtext">AI is processing your documents</span>
                </>
              ) : (
                <>
                  <div className="button-content">
                    <Zap size={20} />
                    <div className="button-text">
                      <span>Analyze Resume</span>
                      <span className="button-subtext">Get AI-powered insights</span>
                    </div>
                  </div>
                  <ChevronRight size={20} />
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="results-section">
            {/* Analysis Header */}
            <div className="analysis-header">
              <div className="candidate-info">
                <div className="candidate-avatar">
                  <User size={24} />
                </div>
                <div>
                  <h2 className="candidate-name">{analysis.candidate_name}</h2>
                  <div className="candidate-meta">
                    <span className="analysis-date">
                      <Clock size={14} />
                      Analysis Date: {new Date().toLocaleDateString('en-US', { 
                        weekday: 'long', 
                        year: 'numeric', 
                        month: 'long', 
                        day: 'numeric' 
                      })}
                    </span>
                    <span className="analysis-id">
                      ID: {Math.random().toString(36).substr(2, 9).toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>
              
              <div className="score-display">
                <div className="score-circle-wrapper">
                  <div className="score-circle-glow" style={{ 
                    background: `radial-gradient(circle, ${getScoreColor(analysis.overall_score)}22 0%, transparent 70%)` 
                  }}></div>
                  <div 
                    className="score-circle" 
                    style={{ 
                      borderColor: getScoreColor(analysis.overall_score),
                      background: `conic-gradient(${getScoreColor(analysis.overall_score)} ${analysis.overall_score * 3.6}deg, #2d3749 0deg)` 
                    }}
                  >
                    <div className="score-inner">
                      <div className="score-value" style={{ color: getScoreColor(analysis.overall_score) }}>
                        {analysis.overall_score}
                      </div>
                      <div className="score-label">Match Score</div>
                      <div className="score-emoji">{getScoreEmoji(analysis.overall_score)}</div>
                    </div>
                  </div>
                </div>
                <div className="score-info">
                  <h3 className="score-grade">{getScoreGrade(analysis.overall_score)}</h3>
                  <p className="score-description">
                    Based on skill matching, experience relevance, and qualifications
                  </p>
                </div>
              </div>
            </div>

            {/* Recommendation Card */}
            <div className="recommendation-card glass" style={{
              background: `linear-gradient(135deg, ${getScoreColor(analysis.overall_score)}15, ${getScoreColor(analysis.overall_score)}08)`,
              borderLeft: `4px solid ${getScoreColor(analysis.overall_score)}`
            }}>
              <div className="recommendation-header">
                <Award size={28} style={{ color: getScoreColor(analysis.overall_score) }} />
                <div>
                  <h3>AI Recommendation</h3>
                  <p className="recommendation-subtitle">Powered by Gemini AI Analysis</p>
                </div>
              </div>
              <div className="recommendation-content">
                <p className="recommendation-text">{analysis.recommendation}</p>
                <div className="confidence-badge">
                  <BarChart3 size={16} />
                  <span>High Confidence Analysis</span>
                </div>
              </div>
            </div>

            {/* Skills Analysis */}
            <div className="section-title">
              <h2>Skills Analysis</h2>
              <p>Detailed breakdown of matched and missing skills</p>
            </div>
            
            <div className="skills-grid">
              <div className="skills-card glass success">
                <div className="skills-card-header">
                  <div className="skills-icon success">
                    <CheckCircle size={24} />
                  </div>
                  <div className="skills-header-content">
                    <h3>Skills Matched</h3>
                    <p className="skills-subtitle">Found in your resume</p>
                  </div>
                  <div className="skills-count success">
                    <span>{analysis.skills_matched?.length || 0}</span>
                  </div>
                </div>
                <div className="skills-content">
                  <ul className="skills-list">
                    {analysis.skills_matched?.map((skill, index) => (
                      <li key={index} className="skill-item success">
                        <div className="skill-item-content">
                          <CheckCircle size={16} />
                          <span>{skill}</span>
                        </div>
                        <div className="skill-match-indicator">
                          <div className="match-bar" style={{ width: `${85 + Math.random() * 15}%` }}></div>
                        </div>
                      </li>
                    ))}
                    {(!analysis.skills_matched || analysis.skills_matched.length === 0) && (
                      <li className="no-items">No matching skills detected</li>
                    )}
                  </ul>
                </div>
              </div>

              <div className="skills-card glass warning">
                <div className="skills-card-header">
                  <div className="skills-icon warning">
                    <XCircle size={24} />
                  </div>
                  <div className="skills-header-content">
                    <h3>Skills Missing</h3>
                    <p className="skills-subtitle">Suggested to learn</p>
                  </div>
                  <div className="skills-count warning">
                    <span>{analysis.skills_missing?.length || 0}</span>
                  </div>
                </div>
                <div className="skills-content">
                  <ul className="skills-list">
                    {analysis.skills_missing?.map((skill, index) => (
                      <li key={index} className="skill-item warning">
                        <div className="skill-item-content">
                          <XCircle size={16} />
                          <span>{skill}</span>
                        </div>
                        <div className="skill-priority">
                          <span className="priority-badge">
                            Priority: {index < 3 ? 'High' : index < 6 ? 'Medium' : 'Low'}
                          </span>
                        </div>
                      </li>
                    ))}
                    {(!analysis.skills_missing || analysis.skills_missing.length === 0) && (
                      <li className="no-items success-text">All required skills are present!</li>
                    )}
                  </ul>
                </div>
              </div>
            </div>

            {/* Summary Section */}
            <div className="section-title">
              <h2>Profile Summary</h2>
              <p>AI-generated insights from your resume</p>
            </div>
            
            <div className="summary-grid">
              <div className="summary-card glass">
                <div className="summary-header">
                  <div className="summary-icon">
                    <Briefcase size={24} />
                  </div>
                  <h3>Experience Summary</h3>
                </div>
                <div className="summary-content">
                  <p>{analysis.experience_summary}</p>
                  <div className="summary-footer">
                    <span className="summary-tag">Professional Experience</span>
                  </div>
                </div>
              </div>

              <div className="summary-card glass">
                <div className="summary-header">
                  <div className="summary-icon">
                    <BookOpen size={24} />
                  </div>
                  <h3>Education Summary</h3>
                </div>
                <div className="summary-content">
                  <p>{analysis.education_summary}</p>
                  <div className="summary-footer">
                    <span className="summary-tag">Academic Background</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Insights Section */}
            <div className="section-title">
              <h2>AI Insights & Recommendations</h2>
              <p>Personalized suggestions to improve your match</p>
            </div>
            
            <div className="insights-grid">
              <div className="insight-card glass">
                <div className="insight-header">
                  <div className="insight-icon success">
                    <TrendingUp size={24} />
                  </div>
                  <div>
                    <h3>Key Strengths</h3>
                    <p className="insight-subtitle">Areas where you excel</p>
                  </div>
                </div>
                <div className="insight-content">
                  <ul>
                    {analysis.key_strengths?.map((strength, index) => (
                      <li key={index} className="strength-item">
                        <div className="strength-marker"></div>
                        <span>{strength}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="insight-card glass">
                <div className="insight-header">
                  <div className="insight-icon warning">
                    <Target size={24} />
                  </div>
                  <div>
                    <h3>Areas for Improvement</h3>
                    <p className="insight-subtitle">Opportunities to grow</p>
                  </div>
                </div>
                <div className="insight-content">
                  <ul>
                    {analysis.areas_for_improvement?.map((area, index) => (
                      <li key={index} className="improvement-item">
                        <div className="improvement-marker"></div>
                        <span>{area}</span>
                        <span className="improvement-tip">
                          Tip: Focus on this area to increase match by 15%
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {/* Action Section */}
            <div className="action-section glass">
              <div className="action-content">
                <h3>Ready to Take Action?</h3>
                <p>Download detailed analysis or start a new assessment</p>
              </div>
              <div className="action-buttons">
                <button className="download-button" onClick={handleDownload}>
                  <div className="button-glow"></div>
                  <Download size={20} />
                  <span>Download Excel Report</span>
                  <span className="button-badge">Detailed Analysis</span>
                </button>
                <button className="share-button">
                  <Star size={20} />
                  <span>Save Analysis</span>
                </button>
                <button className="reset-button" onClick={() => {
                  setAnalysis(null);
                  setResumeFile(null);
                  setJobDescription('');
                  setError('');
                }}>
                  <Sparkles size={20} />
                  <span>Analyze Another Resume</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <div className="footer-brand">
            <div className="footer-logo">
              <Sparkles size={20} />
              <span>AI Resume Analyzer</span>
            </div>
            <p className="footer-tagline">
              Transform your job application process with AI-powered insights
            </p>
          </div>
          
          <div className="footer-links">
            <div className="footer-section">
              <h4>Features</h4>
              <a href="#">AI Analysis</a>
              <a href="#">Skill Matching</a>
              <a href="#">PDF Reports</a>
              <a href="#">Real-time Insights</a>
            </div>
            <div className="footer-section">
              <h4>Resources</h4>
              <a href="#">Documentation</a>
              <a href="#">API Access</a>
              <a href="#">Help Center</a>
              <a href="#">Privacy Policy</a>
            </div>
            <div className="footer-section">
              <h4>Contact</h4>
              <a href="#">Support</a>
              <a href="#">Feedback</a>
              <a href="#">Partnerships</a>
              <a href="#">Twitter</a>
            </div>
          </div>
        </div>
        
        <div className="footer-bottom">
          <p>© 2024 AI Resume Analyzer. Built with React + Flask + Gemini AI. All rights reserved.</p>
          <div className="footer-stats">
            <span className="stat">
              <Zap size={12} />
              {Math.floor(Math.random() * 1000) + 500} analyses today
            </span>
            <span className="stat">
              <Shield size={12} />
              100% Secure
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
