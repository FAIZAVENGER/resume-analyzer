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
  Lock, DownloadCloud, Edit3, FileDown, Info,
  Wifi, WifiOff, Activity, Thermometer, Eye,
  ChevronDown, ChevronUp, FileSpreadsheet, Filter,
  SortAsc, SortDesc, Search, Mail, Phone, MapPin,
  Calendar, Award as AwardIcon, Briefcase as BriefcaseIcon,
  GraduationCap, Languages, Code, Server, Database,
  Cloud, GitBranch, Cpu, Shield as ShieldIcon,
  MessageSquare, Globe as GlobeIcon, Users as UsersIcon,
  BarChart as BarChartIcon, PieChart, LineChart,
  Download as DownloadIcon, FileX, CheckSquare,
  XSquare, AlertTriangle as AlertTriangleIcon,
  Info as InfoIcon, HelpCircle, ThumbsUp, ThumbsDown,
  Star as StarIcon, Heart, Flag, Award as AwardIcon2,
  Trophy, Medal, Target as TargetIcon, Crosshair,
  TrendingUp as TrendingUpIcon, TrendingDown,
  DollarSign, CreditCard, ShoppingCart, Package,
  Truck, Home, Building, Factory, Store, Bank,
  Car, Bike, Plane, Ship, Train, Music, Film,
  Camera, Video, Headphones, Mic, Volume2,
  Play, Stop, Pause, SkipBack, SkipForward,
  Repeat, Shuffle, Music as MusicIcon, Film as FilmIcon,
  Tv, Radio, Smartphone, Tablet, Laptop, Monitor,
  Printer, Scanner, Mouse, Keyboard, HardDrive,
  Cpu as CpuIcon, Server as ServerIcon, Database as DatabaseIcon,
  Cloud as CloudIcon, GitBranch as GitBranchIcon,
  Code as CodeIcon, Terminal, Command, Hash, Type,
  Bold, Italic, Underline, Strikethrough, Link,
  Image, Video as VideoIcon, Camera as CameraIcon,
  Mic as MicIcon, Headphones as HeadphonesIcon,
  Volume2 as Volume2Icon, Bell, BellOff, Eye as EyeIcon,
  EyeOff, Lock as LockIcon, Unlock, Key, Fingerprint,
  UserCheck, UserPlus, UserMinus, UserX, Users as UsersIcon2,
  User as UserIcon
} from 'lucide-react';
import './App.css';
import logoImage from './leadsoc.png';

function App() {
  const [resumeFiles, setResumeFiles] = useState([]);
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [batchResults, setBatchResults] = useState(null);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [aiStatus, setAiStatus] = useState('idle');
  const [backendStatus, setBackendStatus] = useState('checking');
  const [openaiWarmup, setOpenaiWarmup] = useState(false);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [showQuotaPanel, setShowQuotaPanel] = useState(false);
  const [analysisMode, setAnalysisMode] = useState('batch'); // 'single' or 'batch'
  
  const API_BASE_URL = 'https://resume-analyzer-1-pevo.onrender.com';
  
  const keepAliveInterval = useRef(null);
  const backendWakeInterval = useRef(null);

  useEffect(() => {
    initializeService();
    
    return () => {
      if (keepAliveInterval.current) clearInterval(keepAliveInterval.current);
      if (backendWakeInterval.current) clearInterval(backendWakeInterval.current);
    };
  }, []);

  const initializeService = async () => {
    try {
      setIsWarmingUp(true);
      setBackendStatus('waking');
      
      await wakeUpBackend();
      
      const healthResponse = await axios.get(`${API_BASE_URL}/health`, {
        timeout: 10000
      }).catch(() => null);
      
      if (healthResponse?.data) {
        setOpenaiWarmup(healthResponse.data.openai_warmup_complete || false);
        setBackendStatus('ready');
      }
      
      await forceOpenAIWarmup();
      setupPeriodicChecks();
      
    } catch (err) {
      console.log('Service initialization error:', err.message);
      setBackendStatus('sleeping');
      setTimeout(() => initializeService(), 5000);
    } finally {
      setIsWarmingUp(false);
    }
  };

  const wakeUpBackend = async () => {
    try {
      setLoadingMessage('Waking up backend service...');
      await axios.get(`${API_BASE_URL}/ping`, { timeout: 8000 });
      setBackendStatus('ready');
      setLoadingMessage('');
    } catch (error) {
      setBackendStatus('waking');
      setTimeout(() => {
        axios.get(`${API_BASE_URL}/ping`, { timeout: 15000 })
          .then(() => setBackendStatus('ready'))
          .catch(() => setBackendStatus('sleeping'));
      }, 3000);
    }
  };

  const forceOpenAIWarmup = async () => {
    try {
      setAiStatus('warming');
      const response = await axios.get(`${API_BASE_URL}/warmup`, {
        timeout: 15000
      });
      
      if (response.data.warmup_complete) {
        setAiStatus('available');
        setOpenaiWarmup(true);
      }
    } catch (error) {
      setAiStatus('unavailable');
    }
  };

  const setupPeriodicChecks = () => {
    backendWakeInterval.current = setInterval(() => {
      axios.get(`${API_BASE_URL}/ping`, { timeout: 5000 })
        .catch(() => console.log('Keep-alive ping failed'));
    }, 3 * 60 * 1000);
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
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files);
      const validFiles = files.filter(file => 
        file.type.match(/pdf|msword|wordprocessingml|text/) || 
        file.name.match(/\.(pdf|doc|docx|txt)$/i)
      );
      
      if (validFiles.length !== files.length) {
        setError('Some files were invalid. Only PDF, DOC, DOCX, TXT allowed.');
      } else {
        setError('');
      }
      
      if (validFiles.length > 15) {
        setError('Maximum 15 resumes allowed');
        setResumeFiles(validFiles.slice(0, 15));
      } else {
        setResumeFiles(validFiles);
      }
    }
  };

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    
    if (analysisMode === 'single' && files.length > 1) {
      setError('Single mode: Please select only one resume');
      setResumeFiles(files.slice(0, 1));
    } else if (analysisMode === 'batch' && files.length > 15) {
      setError('Maximum 15 resumes allowed');
      setResumeFiles(files.slice(0, 15));
    } else {
      setResumeFiles(files);
      setError('');
    }
  };

  const removeFile = (index) => {
    setResumeFiles(files => files.filter((_, i) => i !== index));
  };

  const handleAnalyze = async () => {
    if (resumeFiles.length === 0) {
      setError('Please upload at least one resume');
      return;
    }
    if (!jobDescription.trim()) {
      setError('Please enter a job description');
      return;
    }

    if (backendStatus !== 'ready') {
      setError('Backend is warming up. Please wait...');
      await wakeUpBackend();
      return;
    }

    setLoading(true);
    setError('');
    setBatchResults(null);
    setSelectedCandidate(null);
    setProgress(0);
    setLoadingMessage(analysisMode === 'batch' ? 'Starting batch analysis...' : 'Starting analysis...');

    const formData = new FormData();
    
    if (analysisMode === 'batch') {
      resumeFiles.forEach(file => {
        formData.append('resumes', file);
      });
    } else {
      formData.append('resume', resumeFiles[0]);
    }
    
    formData.append('jobDescription', jobDescription);

    let progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 85) return 85;
        return prev + Math.random() * 2;
      });
    }, 800);

    try {
      setLoadingMessage(analysisMode === 'batch' ? 
        `Analyzing ${resumeFiles.length} resumes...` : 
        'Analyzing resume...');
      setProgress(20);

      const endpoint = analysisMode === 'batch' ? '/analyze-batch' : '/analyze-single';
      const response = await axios.post(`${API_BASE_URL}${endpoint}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 180000,
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setProgress(20 + percentCompleted * 0.3);
          }
        }
      });

      clearInterval(progressInterval);
      setProgress(95);
      
      setLoadingMessage('Analysis complete!');
      await new Promise(resolve => setTimeout(resolve, 800));
      
      if (analysisMode === 'batch') {
        setBatchResults(response.data);
      } else {
        // For single analysis, wrap it in batch format for consistency
        setBatchResults({
          success: true,
          total_resumes: 1,
          analyses: [response.data],
          excel_filename: response.data.excel_filename,
          processing_time: 'Fast'
        });
      }
      
      setProgress(100);

      setTimeout(() => {
        setProgress(0);
        setLoadingMessage('');
      }, 1000);

    } catch (err) {
      if (progressInterval) clearInterval(progressInterval);
      
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Request timeout. Please try with fewer resumes or try again.');
      } else {
        setError(err.response?.data?.error || 'Analysis failed. Please try again.');
      }
      
      setProgress(0);
      setLoadingMessage('');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadExcel = () => {
    if (batchResults?.excel_filename) {
      window.open(`${API_BASE_URL}/download/${batchResults.excel_filename}`, '_blank');
    }
  };

  const handleDownloadCSV = () => {
    if (batchResults?.csv_filename) {
      window.open(`${API_BASE_URL}/download/${batchResults.csv_filename}`, '_blank');
    }
  };

  const handleViewDetails = (candidate) => {
    setSelectedCandidate(candidate);
  };

  const handleCloseDetails = () => {
    setSelectedCandidate(null);
  };

  const handleReset = () => {
    setBatchResults(null);
    setSelectedCandidate(null);
    setResumeFiles([]);
    setJobDescription('');
    setError('');
    setProgress(0);
    setLoadingMessage('');
    setAnalysisMode('batch');
    initializeService();
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

  const toggleAnalysisMode = () => {
    setAnalysisMode(mode => mode === 'batch' ? 'single' : 'batch');
    setResumeFiles([]);
    setError('');
  };

  return (
    <div className="app">
      <div className="bg-grid"></div>
      <div className="bg-blur-1"></div>
      <div className="bg-blur-2"></div>
      
      <header className="header">
        <div className="header-content">
          <div className="header-main">
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
                  <span className="tagline">Batch & Single Analysis</span>
                </div>
              </div>
            </div>
            
            <div className="leadsoc-logo-container">
              <button
                onClick={(e) => {
                  e.preventDefault();
                  window.open('https://www.leadsoc.com/', '_blank');
                }}
                className="leadsoc-logo-link"
              >
                <img 
                  src={logoImage} 
                  alt="LEADSOC" 
                  className="leadsoc-logo"
                />
                <ExternalLink size={14} className="external-link-icon" />
              </button>
            </div>
          </div>
          
          <div className="header-features">
            <div className={`feature ${analysisMode === 'batch' ? 'active' : ''}`} onClick={() => setAnalysisMode('batch')}>
              <Users size={16} />
              <span>Batch Mode</span>
            </div>
            <div className={`feature ${analysisMode === 'single' ? 'active' : ''}`} onClick={() => setAnalysisMode('single')}>
              <User size={16} />
              <span>Single Mode</span>
            </div>
            <div className="feature">
              <BarChart3 size={16} />
              <span>Smart Ranking</span>
            </div>
            <div className="feature">
              <FileSpreadsheet size={16} />
              <span>Excel & CSV Export</span>
            </div>
          </div>
        </div>
        
        <div className="header-wave">
          <svg viewBox="0 0 1200 120" preserveAspectRatio="none">
            <path d="M0,0V46.29c47.79,22.2,103.59,32.17,158,28,70.36-5.37,136.33-33.31,206.8-37.5C438.64,32.43,512.34,53.67,583,72.05c69.27,18,138.3,24.88,209.4,13.08,36.15-6,69.85-17.84,104.45-29.34C989.49,25,1113-14.29,1200,52.47V0Z" opacity=".25" fill="currentColor"></path>
          </svg>
        </div>
      </header>

      <main className="main-content">
        {!batchResults ? (
          <div className="upload-section">
            <div className="section-header">
              <h2>{analysisMode === 'batch' ? 'Upload Multiple Resumes' : 'Upload Single Resume'}</h2>
              <p>
                {analysisMode === 'batch' 
                  ? 'Analyze up to 15 resumes simultaneously and get ranked results' 
                  : 'Analyze a single resume with detailed insights'}
              </p>
              
              <div className="mode-toggle">
                <button 
                  className={`toggle-btn ${analysisMode === 'batch' ? 'active' : ''}`}
                  onClick={() => setAnalysisMode('batch')}
                >
                  <Users size={18} />
                  <span>Batch Analysis</span>
                  <span className="badge">1-15 resumes</span>
                </button>
                <button 
                  className={`toggle-btn ${analysisMode === 'single' ? 'active' : ''}`}
                  onClick={() => setAnalysisMode('single')}
                >
                  <User size={18} />
                  <span>Single Analysis</span>
                  <span className="badge">1 resume</span>
                </button>
              </div>
            </div>
            
            <div className="upload-grid">
              <div className="upload-card glass">
                <div className="card-header">
                  <div className="header-icon-wrapper">
                    <FileText className="header-icon" />
                  </div>
                  <div>
                    <h2>Upload {analysisMode === 'batch' ? 'Resumes' : 'Resume'}</h2>
                    <p className="card-subtitle">
                      {analysisMode === 'batch' 
                        ? 'Select 1-15 resumes (PDF, DOC, DOCX, TXT)' 
                        : 'Select one resume (PDF, DOC, DOCX, TXT)'}
                    </p>
                  </div>
                </div>
                
                <div 
                  className={`upload-area ${dragActive ? 'drag-active' : ''} ${resumeFiles.length > 0 ? 'has-file' : ''}`}
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
                    multiple={analysisMode === 'batch'}
                  />
                  <label htmlFor="resume-upload" className="file-label">
                    <div className="upload-icon-wrapper">
                      {resumeFiles.length > 0 ? (
                        <div className="files-preview">
                          <FileText size={40} />
                          <div className="files-count">
                            <span className="count-number">{resumeFiles.length}</span>
                            <span className="count-label">
                              {analysisMode === 'batch' 
                                ? `resume${resumeFiles.length !== 1 ? 's' : ''} selected` 
                                : 'resume selected'}
                            </span>
                          </div>
                        </div>
                      ) : (
                        <>
                          <Upload className="upload-icon" />
                          <span className="upload-text">
                            {analysisMode === 'batch' 
                              ? 'Drag & drop resumes or click to browse' 
                              : 'Drag & drop resume or click to browse'}
                          </span>
                          <span className="upload-hint">
                            {analysisMode === 'batch' 
                              ? 'Select 1-15 resumes • Max 10MB each' 
                              : 'Max file size: 10MB'}
                          </span>
                        </>
                      )}
                    </div>
                  </label>
                </div>
                
                {resumeFiles.length > 0 && (
                  <div className="files-list">
                    {resumeFiles.map((file, index) => (
                      <div key={index} className="file-item">
                        <FileText size={16} />
                        <span className="file-name">{file.name}</span>
                        <span className="file-size">{(file.size / 1024).toFixed(1)} KB</span>
                        <button 
                          className="remove-file"
                          onClick={() => removeFile(index)}
                        >
                          <X size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                
                <div className="mode-instructions">
                  {analysisMode === 'batch' ? (
                    <>
                      <div className="instruction">
                        <Check size={16} />
                        <span>Upload multiple resumes (PDF/DOC/DOCX/TXT)</span>
                      </div>
                      <div className="instruction">
                        <Check size={16} />
                        <span>Resumes are ranked by match score</span>
                      </div>
                      <div className="instruction">
                        <Check size={16} />
                        <span>Download comprehensive Excel report</span>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="instruction">
                        <Check size={16} />
                        <span>Upload a single resume for detailed analysis</span>
                      </div>
                      <div className="instruction">
                        <Check size={16} />
                        <span>Get comprehensive skills analysis</span>
                      </div>
                      <div className="instruction">
                        <Check size={16} />
                        <span>Receive detailed improvement suggestions</span>
                      </div>
                    </>
                  )}
                </div>
              </div>

              <div className="job-description-card glass">
                <div className="card-header">
                  <div className="header-icon-wrapper">
                    <Briefcase className="header-icon" />
                  </div>
                  <div>
                    <h2>Job Description</h2>
                    <p className="card-subtitle">Enter complete job requirements</p>
                  </div>
                </div>
                
                <div className="textarea-wrapper">
                  <textarea
                    className="job-description-input"
                    placeholder="• Job title and role\n• Required skills and qualifications\n• Responsibilities and duties\n• Experience requirements\n• Education requirements\n• Any specific certifications needed"
                    value={jobDescription}
                    onChange={(e) => setJobDescription(e.target.value)}
                    rows={12}
                  />
                  <div className="textarea-footer">
                    <span className="char-count">{jobDescription.length} characters</span>
                    <span className="word-count">
                      {jobDescription.trim() ? jobDescription.trim().split(/\s+/).length : 0} words
                    </span>
                  </div>
                </div>
                
                <div className="job-description-tips">
                  <h4>💡 Tips for better analysis:</h4>
                  <ul>
                    <li>Be specific about required skills</li>
                    <li>Include years of experience needed</li>
                    <li>Mention required education level</li>
                    <li>List key responsibilities</li>
                    <li>Add any preferred certifications</li>
                  </ul>
                </div>
              </div>
            </div>

            {error && (
              <div className="error-message glass">
                <AlertCircle size={20} />
                <span>{error}</span>
              </div>
            )}

            {loading && (
              <div className="loading-section glass">
                <div className="loading-container">
                  <div className="loading-header">
                    <Loader className="spinner" />
                    <h3>{analysisMode === 'batch' ? 'Batch Analysis in Progress' : 'Analysis in Progress'}</h3>
                  </div>
                  
                  <div className="progress-container">
                    <div className="progress-bar" style={{ width: `${progress}%` }}></div>
                  </div>
                  
                  <div className="loading-text">
                    <span className="loading-message">{loadingMessage}</span>
                    <span className="loading-subtext">
                      {analysisMode === 'batch' 
                        ? `Processing ${resumeFiles.length} resumes...` 
                        : 'Analyzing resume with AI...'}
                    </span>
                  </div>
                  
                  <div className="progress-stats">
                    <span>{Math.round(progress)}%</span>
                    <span className="divider">•</span>
                    <span>{analysisMode === 'batch' ? 'Batch Mode' : 'Single Mode'}</span>
                    <span className="divider">•</span>
                    <span>OpenAI: {aiStatus === 'available' ? 'Ready' : 'Processing'}</span>
                  </div>
                </div>
              </div>
            )}

            <button
              className="analyze-button"
              onClick={handleAnalyze}
              disabled={loading || resumeFiles.length === 0 || !jobDescription.trim()}
            >
              {loading ? (
                <div className="button-loading-content">
                  <Loader className="spinner" />
                  <span>
                    {analysisMode === 'batch' 
                      ? `Analyzing ${resumeFiles.length} resumes...` 
                      : 'Analyzing resume...'}
                  </span>
                </div>
              ) : (
                <>
                  <div className="button-content">
                    <Zap size={20} />
                    <div className="button-text">
                      <span>
                        {analysisMode === 'batch' 
                          ? `Analyze ${resumeFiles.length} Resume${resumeFiles.length !== 1 ? 's' : ''}` 
                          : 'Analyze Resume'}
                      </span>
                      <span className="button-subtext">
                        {analysisMode === 'batch' ? 'Get ranked results' : 'Get detailed insights'}
                      </span>
                    </div>
                  </div>
                  <ChevronRight size={20} />
                </>
              )}
            </button>
            
            <div className="analysis-features">
              <div className="feature-card">
                <div className="feature-icon">
                  <Brain size={24} />
                </div>
                <h4>AI-Powered Analysis</h4>
                <p>OpenAI analyzes skills, experience, and education match</p>
              </div>
              
              <div className="feature-card">
                <div className="feature-icon">
                  <BarChart3 size={24} />
                </div>
                <h4>Smart Ranking</h4>
                <p>Candidates sorted by match score from highest to lowest</p>
              </div>
              
              <div className="feature-card">
                <div className="feature-icon">
                  <DownloadCloud size={24} />
                </div>
                <h4>Export Reports</h4>
                <p>Download Excel and CSV reports for all candidates</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="results-section">
            {!selectedCandidate ? (
              <>
                <div className="results-header">
                  <div className="results-title">
                    <h2>Analysis Results</h2>
                    <p>
                      {batchResults.total_resumes === 1 
                        ? 'Single resume analyzed' 
                        : `${batchResults.total_resumes} candidates analyzed • Ranked by match score`}
                    </p>
                  </div>
                  <div className="results-actions">
                    {batchResults.excel_filename && (
                      <button className="action-btn download" onClick={handleDownloadExcel}>
                        <DownloadIcon size={16} />
                        Download Excel
                      </button>
                    )}
                    {batchResults.csv_filename && (
                      <button className="action-btn csv" onClick={handleDownloadCSV}>
                        <FileSpreadsheet size={16} />
                        Download CSV
                      </button>
                    )}
                  </div>
                </div>

                <div className="candidates-table glass">
                  <div className="table-header">
                    <div className="th rank">Rank</div>
                    <div className="th name">Candidate Name</div>
                    <div className="th score">Score</div>
                    <div className="th recommendation">Recommendation</div>
                    <div className="th action">Details</div>
                  </div>
                  
                  {batchResults.analyses.map((candidate, index) => (
                    <div key={index} className="table-row">
                      <div className="td rank">
                        <span className="rank-badge">{index + 1}</span>
                      </div>
                      <div className="td name">
                        <UserIcon size={16} />
                        <div className="candidate-info">
                          <span className="candidate-name">{candidate.candidate_name}</span>
                          <span className="candidate-file">{candidate.filename}</span>
                        </div>
                      </div>
                      <div className="td score">
                        <div 
                          className="score-badge"
                          style={{ 
                            background: `${getScoreColor(candidate.overall_score)}20`,
                            color: getScoreColor(candidate.overall_score),
                            borderColor: getScoreColor(candidate.overall_score)
                          }}
                        >
                          {candidate.overall_score}
                        </div>
                        <span className="score-label">{getScoreGrade(candidate.overall_score)}</span>
                      </div>
                      <div className="td recommendation">
                        <span className={`rec-badge ${candidate.recommendation?.includes('Highly') ? 'success' : 
                                          candidate.recommendation?.includes('Recommended') ? 'good' : 
                                          candidate.recommendation?.includes('Moderately') ? 'warning' : 'danger'}`}>
                          {candidate.recommendation}
                        </span>
                      </div>
                      <div className="td action">
                        <button 
                          className="view-details-btn"
                          onClick={() => handleViewDetails(candidate)}
                        >
                          <EyeIcon size={16} />
                          View Details
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="results-summary glass">
                  <div className="summary-stats">
                    <div className="stat">
                      <div className="stat-value">{batchResults.total_resumes}</div>
                      <div className="stat-label">Total Resumes</div>
                    </div>
                    <div className="stat">
                      <div className="stat-value">
                        {Math.round(batchResults.analyses.reduce((acc, curr) => acc + curr.overall_score, 0) / batchResults.analyses.length)}/100
                      </div>
                      <div className="stat-label">Average Score</div>
                    </div>
                    <div className="stat">
                      <div className="stat-value">
                        {batchResults.analyses.filter(c => c.overall_score >= 80).length}
                      </div>
                      <div className="stat-label">Top Candidates (80+)</div>
                    </div>
                    <div className="stat">
                      <div className="stat-value">
                        {batchResults.analyses.filter(c => c.overall_score >= 60).length}
                      </div>
                      <div className="stat-label">Qualified (60+)</div>
                    </div>
                  </div>
                </div>

                <div className="action-section glass">
                  <div className="action-content">
                    <h3>Ready to Take Action?</h3>
                    <p>Download reports or analyze another batch</p>
                  </div>
                  <div className="action-buttons">
                    {batchResults.excel_filename && (
                      <button className="download-button" onClick={handleDownloadExcel}>
                        <DownloadCloud size={20} />
                        <span>Download Excel Report</span>
                      </button>
                    )}
                    {batchResults.csv_filename && (
                      <button className="csv-button" onClick={handleDownloadCSV}>
                        <FileSpreadsheet size={20} />
                        <span>Download CSV Summary</span>
                      </button>
                    )}
                    <button className="reset-button" onClick={handleReset}>
                      <RefreshCw size={20} />
                      <span>Analyze Another</span>
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="candidate-detail">
                <div className="detail-header">
                  <button className="back-btn" onClick={handleCloseDetails}>
                    <ChevronRight size={20} style={{ transform: 'rotate(180deg)' }} />
                    Back to Results
                  </button>
                  <div className="detail-title">
                    <h2>{selectedCandidate.candidate_name}</h2>
                    <p className="detail-subtitle">Detailed analysis report</p>
                  </div>
                </div>

                <div className="detail-overview glass">
                  <div className="overview-score">
                    <div className="score-circle-wrapper">
                      <div 
                        className="score-circle" 
                        style={{ 
                          borderColor: getScoreColor(selectedCandidate.overall_score),
                          background: `conic-gradient(${getScoreColor(selectedCandidate.overall_score)} ${selectedCandidate.overall_score * 3.6}deg, #2d3749 0deg)` 
                        }}
                      >
                        <div className="score-inner">
                          <div className="score-value" style={{ color: getScoreColor(selectedCandidate.overall_score) }}>
                            {selectedCandidate.overall_score}
                          </div>
                          <div className="score-label">Match Score</div>
                        </div>
                      </div>
                    </div>
                    <div className="score-info">
                      <h3>{getScoreGrade(selectedCandidate.overall_score)}</h3>
                      <p className="recommendation-text">
                        <strong>Recommendation:</strong> {selectedCandidate.recommendation}
                      </p>
                      <div className="score-meta">
                        <span className="meta-item">
                          <FileText size={12} />
                          {selectedCandidate.filename}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="section-title">
                  <h3>Skills Analysis</h3>
                  <p>Matched and missing skills comparison</p>
                </div>
                
                <div className="skills-grid">
                  <div className="skills-card glass success">
                    <div className="skills-card-header">
                      <div className="skills-icon success">
                        <CheckCircle size={24} />
                      </div>
                      <div>
                        <h3>Skills Matched</h3>
                        <p className="skills-subtitle">Found in resume</p>
                      </div>
                      <div className="skills-count success">
                        <span>{selectedCandidate.skills_matched?.length || 0}</span>
                      </div>
                    </div>
                    <div className="skills-content">
                      <ul className="skills-list">
                        {selectedCandidate.skills_matched?.map((skill, i) => (
                          <li key={i} className="skill-item success">
                            <CheckCircle size={16} />
                            <span>{skill}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="skills-card glass warning">
                    <div className="skills-card-header">
                      <div className="skills-icon warning">
                        <XCircle size={24} />
                      </div>
                      <div>
                        <h3>Skills Missing</h3>
                        <p className="skills-subtitle">Suggested to learn</p>
                      </div>
                      <div className="skills-count warning">
                        <span>{selectedCandidate.skills_missing?.length || 0}</span>
                      </div>
                    </div>
                    <div className="skills-content">
                      <ul className="skills-list">
                        {selectedCandidate.skills_missing?.map((skill, i) => (
                          <li key={i} className="skill-item warning">
                            <XCircle size={16} />
                            <span>{skill}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="section-title">
                  <h3>Profile Summary</h3>
                  <p>Detailed insights from the resume</p>
                </div>
                
                <div className="summary-grid">
                  <div className="summary-card glass">
                    <div className="summary-header">
                      <div className="summary-icon">
                        <BriefcaseIcon size={24} />
                      </div>
                      <h3>Experience Summary</h3>
                    </div>
                    <div className="summary-content">
                      <p className="detailed-summary">{selectedCandidate.experience_summary}</p>
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
                      <p className="detailed-summary">{selectedCandidate.education_summary}</p>
                    </div>
                  </div>
                </div>

                <div className="section-title">
                  <h3>Insights & Recommendations</h3>
                  <p>Personalized suggestions for improvement</p>
                </div>
                
                <div className="insights-grid">
                  <div className="insight-card glass success">
                    <div className="insight-header">
                      <div className="insight-icon success">
                        <TrendingUp size={24} />
                      </div>
                      <div>
                        <h3>Key Strengths</h3>
                        <p className="insight-subtitle">Areas where candidate excels</p>
                      </div>
                    </div>
                    <div className="insight-content">
                      <ul>
                        {selectedCandidate.key_strengths?.map((strength, i) => (
                          <li key={i} className="strength-item">
                            <div className="strength-marker"></div>
                            <span>{strength}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="insight-card glass warning">
                    <div className="insight-header">
                      <div className="insight-icon warning">
                        <TargetIcon size={24} />
                      </div>
                      <div>
                        <h3>Areas for Improvement</h3>
                        <p className="insight-subtitle">Opportunities to grow</p>
                      </div>
                    </div>
                    <div className="insight-content">
                      <ul>
                        {selectedCandidate.areas_for_improvement?.map((area, i) => (
                          <li key={i} className="improvement-item">
                            <div className="improvement-marker"></div>
                            <span>{area}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="detail-actions">
                  <button className="back-to-results" onClick={handleCloseDetails}>
                    <ChevronRight size={16} style={{ transform: 'rotate(180deg)' }} />
                    Back to All Candidates
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="footer">
        <div className="footer-content">
          <div className="footer-brand">
            <div className="footer-logo">
              <Sparkles size={20} />
              <span>AI Resume Analyzer</span>
            </div>
            <p className="footer-tagline">
              Analyze single or multiple resumes with AI-powered insights
            </p>
          </div>
          
          <div className="footer-links">
            <div className="footer-section">
              <h4>Features</h4>
              <a href="#" onClick={(e) => { e.preventDefault(); setAnalysisMode('batch'); }}>Batch Analysis</a>
              <a href="#" onClick={(e) => { e.preventDefault(); setAnalysisMode('single'); }}>Single Analysis</a>
              <a href="#">Skill Matching</a>
              <a href="#">Export Reports</a>
            </div>
            <div className="footer-section">
              <h4>Support</h4>
              <a href="#">Documentation</a>
              <a href="#">FAQs</a>
              <a href="#">Contact</a>
              <a href="#">Feedback</a>
            </div>
          </div>
        </div>
        
        <div className="footer-bottom">
          <p>© 2024 AI Resume Analyzer • Built with React + Flask + OpenAI</p>
          <div className="footer-stats">
            <span className="stat">
              <Activity size={12} />
              Backend: {backendStatus === 'ready' ? 'Active' : 'Waking'}
            </span>
            <span className="stat">
              <Brain size={12} />
              AI: {aiStatus === 'available' ? 'Ready' : 'Processing'}
            </span>
            <span className="stat">
              <Users size={12} />
              Mode: {analysisMode === 'batch' ? 'Batch' : 'Single'}
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
