import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Upload, FileText, Briefcase, CheckCircle, XCircle, 
  Download, Loader, TrendingUp, Award, BookOpen, 
  Target, AlertCircle, Sparkles, Star, Zap, User,
  ChevronRight, Shield, BarChart3, Globe, Clock,
  AlertTriangle, BatteryCharging, Brain, Rocket,
  RefreshCw, Check, X, ExternalLink, BarChart,
  Battery, Crown, Users, Coffee, ShieldCheck,
  Lock, DownloadCloud, Edit3, FileDown, Info
} from 'lucide-react';
import './App.css';
import logoImage from './leadsoc.png';

function App() {
  const [resumeFile, setResumeFile] = useState(null);
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [aiStatus, setAiStatus] = useState('idle');
  const [retryCount, setRetryCount] = useState(0);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  const [quotaInfo, setQuotaInfo] = useState(null);
  const [quotaResetTime, setQuotaResetTime] = useState(null);
  const [showQuotaPanel, setShowQuotaPanel] = useState(false);
  const [serviceStatus, setServiceStatus] = useState({
    enhancedFallback: true,
    validKeys: 0,
    totalKeys: 0
  });

  // UPDATED: Use your Render backend URL
  const API_BASE_URL = 'https://resume-analyzer-1-pevo.onrender.com';
  
  const keepAliveInterval = useRef(null);

  // Check AI status on mount and keep service awake
  useEffect(() => {
    initializeService();
    
    // Cleanup on unmount
    return () => {
      if (keepAliveInterval.current) {
        clearInterval(keepAliveInterval.current);
      }
    };
  }, []);

  const initializeService = async () => {
    try {
      setIsWarmingUp(true);
      setAiStatus('checking');
      
      // First, ping the backend to wake it up
      setLoadingMessage('Initializing service...');
      const pingResponse = await axios.get(`${API_BASE_URL}/ping`, {
        timeout: 15000
      }).catch(() => {
        console.log('Initial ping failed - backend might be sleeping');
        return null;
      });
      
      if (pingResponse?.data) {
        setServiceStatus({
          enhancedFallback: pingResponse.data.enhanced_fallback || true,
          validKeys: pingResponse.data.valid_keys || 0,
          totalKeys: pingResponse.data.total_keys || 0
        });
      }
      
      // Wait a moment for backend to fully wake up
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Check AI status
      await checkAIAvailability();
      
      // Check quota status
      await checkQuotaStatus();
      
      // Set up keep-alive every 4 minutes
      keepAliveInterval.current = setInterval(() => {
        axios.get(`${API_BASE_URL}/ping`, { timeout: 5000 })
          .then(() => console.log('Keep-alive ping successful'))
          .catch(() => console.log('Keep-alive ping failed'));
      }, 4 * 60 * 1000);
      
    } catch (err) {
      console.log('Service initialization error:', err.message);
    } finally {
      setIsWarmingUp(false);
    }
  };

  const checkAIAvailability = async (retries = 2) => {
    for (let i = 0; i < retries; i++) {
      try {
        setAiStatus('checking');
        setLoadingMessage(`Checking OpenAI service... (Attempt ${i + 1}/${retries})`);
        
        const response = await axios.get(`${API_BASE_URL}/quick-check`, {
          timeout: 15000
        });
        
        if (response.data.available) {
          setAiStatus('available');
          setLoadingMessage('');
          setRetryCount(0);
          return true;
        } else {
          if (response.data.status === 'quota_exceeded' || response.data.status === 'rate_limit') {
            setAiStatus('unavailable');
            setLoadingMessage('OpenAI quota/rate limit reached. Using enhanced analysis...');
            return false;
          }
        }
        
        if (i < retries - 1) {
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
        
      } catch (err) {
        console.log(`OpenAI check attempt ${i + 1} failed:`, err.message);
        
        if (err.code === 'ECONNABORTED') {
          setLoadingMessage('Backend is waking up... This may take 30-60 seconds');
        }
        
        if (i < retries - 1) {
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
      }
    }
    
    setAiStatus('unavailable');
    setRetryCount(prev => prev + 1);
    return false;
  };

  const checkQuotaStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      setQuotaInfo({
        overall: {
          total_keys: response.data.api_key_configured ? 1 : 0,
          valid_keys: response.data.client_initialized ? 1 : 0
        },
        enhanced_fallback: {
          enabled: true,
          extraction_features: ['Name Extraction', 'Skill Detection', 'Experience Analysis', 'Education Detection']
        }
      });
      
      if (response.data.client_initialized) {
        setServiceStatus(prev => ({
          ...prev,
          enhancedFallback: true,
          extractionFeatures: ['Name Extraction', 'Skill Detection', 'Experience Analysis', 'Education Detection']
        }));
      }
    } catch (error) {
      console.log('Failed to get quota status:', error);
    }
  };

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
      if (file.size > 10 * 1024 * 1024) {
        setError('File size too large. Maximum size is 10MB.');
        return;
      }
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
    setProgress(0);
    setLoadingMessage('Starting analysis...');

    const formData = new FormData();
    formData.append('resume', resumeFile);
    formData.append('jobDescription', jobDescription);

    let progressInterval;

    try {
      // Start progress simulation
      progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 85) return 85;
          return prev + Math.random() * 3;
        });
      }, 500);

      // Update loading message based on service status
      if (aiStatus === 'available' && serviceStatus.validKeys > 0) {
        setLoadingMessage('Using OpenAI AI analysis...');
      } else {
        setLoadingMessage('Using enhanced analysis...');
      }
      setProgress(20);

      // Upload file
      setLoadingMessage('Uploading and processing resume...');
      setProgress(30);

      const response = await axios.post(`${API_BASE_URL}/analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 90000, // 90 seconds
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setProgress(30 + percentCompleted * 0.4);
            setLoadingMessage(percentCompleted < 50 ? 'Uploading file...' : 'Extracting text from resume...');
          }
        }
      });

      clearInterval(progressInterval);
      setProgress(95);
      
      setLoadingMessage('AI analysis complete!');

      await new Promise(resolve => setTimeout(resolve, 800));
      
      setAnalysis(response.data);
      setProgress(100);

      // Update quota status
      await checkQuotaStatus();

      setTimeout(() => {
        setProgress(0);
        setLoadingMessage('');
      }, 1000);

    } catch (err) {
      if (progressInterval) clearInterval(progressInterval);
      
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Request timeout. The backend might be waking up. Please try again in 30 seconds.');
      } else if (err.response?.status === 429) {
        setError('Rate limit reached. Enhanced analysis is still available.');
      } else if (err.response?.data?.error?.includes('quota') || err.response?.data?.error?.includes('rate limit')) {
        setError('OpenAI service quota/rate limit exceeded. Enhanced analysis will extract information from your resume.');
        setAiStatus('unavailable');
      } else {
        setError(err.response?.data?.error || 'An error occurred during analysis. Please try again.');
      }
      
      setProgress(0);
      setLoadingMessage('');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (analysis?.excel_filename) {
      window.open(`${API_BASE_URL}/download/${analysis.excel_filename}`, '_blank');
    } else {
      setError('No analysis report available for download.');
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

  const getAiStatusMessage = () => {
    switch(aiStatus) {
      case 'checking': return { 
        text: 'Checking OpenAI...', 
        color: '#ffd166', 
        icon: <BatteryCharging size={16} />,
        bgColor: 'rgba(255, 209, 102, 0.1)'
      };
      case 'available': return { 
        text: 'OpenAI Ready', 
        color: '#00ff9d', 
        icon: <Check size={16} />,
        bgColor: 'rgba(0, 255, 157, 0.1)'
      };
      case 'unavailable': return { 
        text: 'Enhanced Analysis', 
        color: '#ffd166', 
        icon: <Info size={16} />,
        bgColor: 'rgba(255, 209, 102, 0.1)'
      };
      default: return { 
        text: 'AI Status', 
        color: '#94a3b8', 
        icon: <Brain size={16} />,
        bgColor: 'rgba(148, 163, 184, 0.1)'
      };
    }
  };

  const aiStatusInfo = getAiStatusMessage();

  const handleLeadsocClick = (e) => {
    e.preventDefault();
    setIsNavigating(true);
    
    setTimeout(() => {
      window.open('https://www.leadsoc.com/', '_blank');
      setIsNavigating(false);
    }, 100);
  };

  const formatTimeRemaining = (minutes) => {
    if (minutes > 60) {
      const hours = Math.floor(minutes / 60);
      const mins = minutes % 60;
      return `${hours}h ${mins}m`;
    }
    return `${minutes}m`;
  };

  const getEnhancedFallbackMessage = () => {
    if (!serviceStatus.enhancedFallback) return null;
    
    return (
      <div className="enhanced-fallback-info glass">
        <div className="info-header">
          <Sparkles size={20} />
          <h4>Enhanced Fallback Active</h4>
        </div>
        <p className="info-description">
          Even without AI, we extract information directly from your resume:
        </p>
        <ul className="feature-list">
          <li><Check size={14} /> Extract candidate name from resume</li>
          <li><Check size={14} /> Detect skills and experience</li>
          <li><Check size={14} /> Analyze education background</li>
          <li><Check size={14} /> Provide personalized scoring</li>
        </ul>
      </div>
    );
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
            {/* Logo and Title */}
            <div className="logo">
              <div className="logo-glow">
                <Sparkles className="logo-icon" />
              </div>
              <div className="logo-text">
                <h1>AI Resume Analyzer</h1>
                <div className="logo-subtitle">
                  <span className="powered-by">Powered by</span>
                  <span className="openai-badge">OpenAI</span>
                  <span className="divider">•</span>
                  <span className="tagline">Intelligent Candidate Screening</span>
                </div>
              </div>
            </div>
            
            {/* Leadsoc Logo */}
            <div className="leadsoc-logo-container">
              <button
                onClick={handleLeadsocClick}
                className="leadsoc-logo-link"
                disabled={isNavigating}
                title="Visit LEADSOC - Partnering Your Success"
              >
                {isNavigating ? (
                  <div className="leadsoc-loading">
                    <Loader size={20} className="spinner" />
                    <span>Opening...</span>
                  </div>
                ) : (
                  <>
                    <img 
                      src={logoImage} 
                      alt="LEADSOC - partnering your success" 
                      className="leadsoc-logo"
                    />
                    <ExternalLink size={14} className="external-link-icon" />
                  </>
                )}
              </button>
            </div>
          </div>
          
          <div className="header-features">
            <div className="feature">
              <ShieldCheck size={16} />
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
            <div 
              className="feature ai-status-indicator" 
              style={{ 
                backgroundColor: aiStatusInfo.bgColor,
                borderColor: `${aiStatusInfo.color}30`,
                color: aiStatusInfo.color
              }}
            >
              {aiStatusInfo.icon}
              <span>{aiStatusInfo.text}</span>
              {isWarmingUp && <Loader size={12} className="pulse-spinner" />}
            </div>
            
            {/* Enhanced Fallback Indicator */}
            {serviceStatus.enhancedFallback && (
              <div className="feature enhanced-fallback">
                <Sparkles size={16} />
                <span>Enhanced Analysis</span>
              </div>
            )}
            
            {/* Quota Status Toggle */}
            <button 
              className="feature quota-toggle"
              onClick={() => setShowQuotaPanel(!showQuotaPanel)}
              title="Show quota status"
            >
              <BarChart size={16} />
              <span>Quota Status</span>
            </button>
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
        {/* Quota Status Panel */}
        {showQuotaPanel && quotaInfo && (
          <div className="quota-status-panel glass">
            <div className="quota-panel-header">
              <div className="quota-title">
                <BarChart size={20} />
                <h3>OpenAI Service Status</h3>
              </div>
              <button 
                className="close-quota"
                onClick={() => setShowQuotaPanel(false)}
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="quota-summary">
              <div className="summary-item">
                <div className="summary-label">API Key Status</div>
                <div className="summary-value">{quotaInfo.overall?.valid_keys > 0 ? '✅ Configured' : '❌ Missing'}</div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Client Status</div>
                <div className={`summary-value ${quotaInfo.overall?.valid_keys > 0 ? 'success' : 'warning'}`}>
                  {quotaInfo.overall?.valid_keys > 0 ? '✅ Initialized' : '❌ Not Ready'}
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Enhanced Fallback</div>
                <div className="summary-value success">
                  ✅ Active
                </div>
              </div>
            </div>
            
            {serviceStatus.enhancedFallback && (
              <div className="enhanced-fallback-card success">
                <div className="fallback-header">
                  <Sparkles size={20} />
                  <h4>Enhanced Fallback Active</h4>
                </div>
                <p className="fallback-description">
                  Even without OpenAI, we extract information directly from resumes:
                </p>
                <div className="fallback-features">
                  <div className="feature-badge">
                    <Check size={14} />
                    <span>Name Extraction</span>
                  </div>
                  <div className="feature-badge">
                    <Check size={14} />
                    <span>Skill Detection</span>
                  </div>
                  <div className="feature-badge">
                    <Check size={14} />
                    <span>Experience Analysis</span>
                  </div>
                  <div className="feature-badge">
                    <Check size={14} />
                    <span>Education Detection</span>
                  </div>
                </div>
              </div>
            )}
            
            {quotaInfo.overall?.valid_keys === 0 && (
              <div className="quota-warning-banner warning">
                <AlertTriangle size={18} />
                <div className="warning-content">
                  <strong>No valid OpenAI API key configured</strong>
                  <p>Enhanced analysis is extracting information directly from resumes. Add valid OpenAI API key for AI analysis.</p>
                </div>
              </div>
            )}
            
            <div className="quota-tips">
              <h4>Usage Tips:</h4>
              <ul>
                <li>✅ OpenAI API key is required for AI-powered analysis</li>
                <li>✅ Enhanced analysis works without OpenAI API key</li>
                <li>✅ Get OpenAI API key from platform.openai.com</li>
                <li>✅ Add key to .env file as OPENAI_API_KEY=your_key</li>
              </ul>
            </div>
          </div>
        )}

        {/* Enhanced Fallback Info */}
        {!analysis && serviceStatus.enhancedFallback && (
          <div className="top-notice-bar glass">
            <div className="notice-content">
              <Sparkles size={18} />
              <div>
                <strong>Enhanced Analysis Mode Active</strong>
                <p>We extract information directly from your resume for accurate analysis</p>
              </div>
            </div>
          </div>
        )}

        {!analysis ? (
          <div className="upload-section">
            <div className="section-header">
              <h2>Start Your Analysis</h2>
              <p>Upload your resume and job description to get detailed insights</p>
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
                    <p className="card-subtitle">Supported: PDF, DOC, DOCX, TXT (Max 10MB)</p>
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
                  <div className="stat">
                    <div className="stat-icon">
                      <Sparkles size={14} />
                    </div>
                    <span>Enhanced extraction</span>
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

            {/* Loading Progress Bar */}
            {loading && (
              <div className="loading-section glass">
                <div className="loading-container">
                  <div className="loading-header">
                    <Loader className="spinner" />
                    <h3>Analysis in Progress</h3>
                  </div>
                  
                  <div className="progress-container">
                    <div className="progress-bar" style={{ width: `${progress}%` }}></div>
                  </div>
                  
                  <div className="loading-text">
                    <span className="loading-message">{loadingMessage}</span>
                    <span className="loading-subtext">
                      {progress < 30 ? 'Initializing...' : 
                       progress < 60 ? 'Processing document...' : 
                       progress < 85 ? 'Analyzing content...' : 
                       'Finalizing results...'}
                    </span>
                  </div>
                  
                  <div className="progress-stats">
                    <span>{Math.round(progress)}%</span>
                    <span>•</span>
                    <span>Estimated time: {progress > 80 ? '10s' : progress > 50 ? '30s' : '45s'}</span>
                  </div>
                  
                  {aiStatus === 'unavailable' && (
                    <div className="loading-note info">
                      <Info size={14} />
                      <span>Using enhanced analysis (extracts info from your resume)</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            <button
              className="analyze-button"
              onClick={handleAnalyze}
              disabled={loading || !resumeFile || !jobDescription.trim()}
            >
              {loading ? (
                <div className="button-loading-content">
                  <Loader className="spinner" />
                  <span>Analyzing...</span>
                </div>
              ) : (
                <>
                  <div className="button-content">
                    <Zap size={20} />
                    <div className="button-text">
                      <span>Analyze Resume</span>
                      <span className="button-subtext">
                        {aiStatus === 'available' ? 'OpenAI AI-powered insights' : 'Enhanced analysis'}
                      </span>
                    </div>
                  </div>
                  <ChevronRight size={20} />
                </>
              )}
            </button>

            {/* Tips Section */}
            <div className="tips-section">
              <div className="tip">
                <Sparkles size={16} />
                <span>Make sure your name is clearly visible at the top of your resume</span>
              </div>
              <div className="tip">
                <Shield size={16} />
                <span>Your resume is processed securely and not stored permanently</span>
              </div>
              <div className="tip">
                <Info size={16} />
                <span>Even without OpenAI, we extract information directly from your resume content</span>
              </div>
            </div>
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
                    <span className="ai-badge">
                      <Brain size={12} />
                      OpenAI-Powered Analysis
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
                  <h3>Analysis Recommendation</h3>
                  <p className="recommendation-subtitle">
                    OpenAI-Powered Analysis
                  </p>
                </div>
              </div>
              <div className="recommendation-content">
                <p className="recommendation-text">{analysis.recommendation}</p>
                <div className="confidence-badge">
                  <Brain size={16} />
                  <span>OpenAI AI-Powered Analysis</span>
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
              <p>Insights extracted from your resume</p>
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
                  <p className="detailed-summary">{analysis.experience_summary || "No experience summary available."}</p>
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
                  <p className="detailed-summary">{analysis.education_summary || "No education summary available."}</p>
                  <div className="summary-footer">
                    <span className="summary-tag">Academic Background</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Insights Section */}
            <div className="section-title">
              <h2>Insights & Recommendations</h2>
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
                <button 
                  className="download-button" 
                  onClick={handleDownload}
                  disabled={!analysis?.excel_filename}
                >
                  <div className="button-glow"></div>
                  <DownloadCloud size={20} />
                  <span>Download Excel Report</span>
                  <span className="button-badge">Detailed</span>
                </button>
                <button className="reset-button" onClick={() => {
                  setAnalysis(null);
                  setResumeFile(null);
                  setJobDescription('');
                  setError('');
                  setProgress(0);
                  setLoadingMessage('');
                  setRetryCount(0);
                  setShowQuotaPanel(false);
                  initializeService();
                }}>
                  <RefreshCw size={20} />
                  <span>Analyze Another</span>
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
              Transform your job application process with intelligent insights
            </p>
          </div>
          
          <div className="footer-links">
            <div className="footer-section">
              <h4>Features</h4>
              <a href="#">OpenAI Analysis</a>
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
          <p>© 2024 AI Resume Analyzer. Built with React + Flask + OpenAI. All rights reserved.</p>
          <div className="footer-stats">
            <span className="stat">
              <Zap size={12} />
              Service: {aiStatus === 'available' ? 'OpenAI Ready' : 'Enhanced Mode'}
            </span>
            <span className="stat">
              <Shield size={12} />
              100% Secure
            </span>
            <span className="stat">
              <Sparkles size={12} />
              Enhanced Fallback: ✅ Active
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
