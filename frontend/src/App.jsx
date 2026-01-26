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
  Wifi, WifiOff, Activity, Thermometer, ListOrdered,
  BarChart4, Filter, Cpu, Zap as ZapIcon, Bolt,
  PlayCircle, PauseCircle, Circle, ShieldAlert,
  BatteryFull, BatteryMedium, BatteryLow, Signal,
  Cloud, CloudOff, CloudLightning, CloudRain,
  ArrowLeft, ChevronLeft, Home, Grid, Folder,
  FileSpreadsheet, ClipboardList, Award as AwardIcon,
  FileX, Calculator, Hash, Percent, Target as TargetIcon,
  PieChart, BarChart2, Layers, CheckSquare,
  XSquare, AlertOctagon, GitMerge, GitBranch,
  GitCommit, GitPullRequest, GitCompare, GitMergeIcon
} from 'lucide-react';
import './App.css';
import logoImage from './leadsoc.png';

function App() {
  const [resumeFile, setResumeFile] = useState(null);
  const [resumeFiles, setResumeFiles] = useState([]);
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [batchLoading, setBatchLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [batchAnalysis, setBatchAnalysis] = useState(null);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [batchProgress, setBatchProgress] = useState(0);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [aiStatus, setAiStatus] = useState('idle');
  const [backendStatus, setBackendStatus] = useState('checking');
  const [groqWarmup, setGroqWarmup] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  const [quotaInfo, setQuotaInfo] = useState(null);
  const [showQuotaPanel, setShowQuotaPanel] = useState(false);
  const [batchMode, setBatchMode] = useState(false);
  const [modelInfo, setModelInfo] = useState(null);
  const [serviceStatus, setServiceStatus] = useState({
    enhancedFallback: true,
    validKeys: 0,
    totalKeys: 0
  });
  
  // View management for navigation
  const [currentView, setCurrentView] = useState('main'); // 'main', 'batch-results', 'candidate-detail'
  const [selectedCandidateIndex, setSelectedCandidateIndex] = useState(null);
  
  const API_BASE_URL = 'https://resume-analyzer-1-pevo.onrender.com';
  
  const keepAliveInterval = useRef(null);
  const backendWakeInterval = useRef(null);
  const warmupCheckInterval = useRef(null);

  // Navigation functions
  const navigateToBatchResults = () => {
    setCurrentView('batch-results');
    window.scrollTo(0, 0);
  };

  const navigateToCandidateDetail = (index) => {
    setSelectedCandidateIndex(index);
    setCurrentView('candidate-detail');
    window.scrollTo(0, 0);
  };

  const navigateToMain = () => {
    setCurrentView('main');
    window.scrollTo(0, 0);
  };

  const navigateBack = () => {
    if (currentView === 'candidate-detail') {
      setCurrentView('batch-results');
    } else if (currentView === 'batch-results') {
      setCurrentView('main');
    }
    window.scrollTo(0, 0);
  };

  // Initialize service on mount
  useEffect(() => {
    initializeService();
    
    return () => {
      if (keepAliveInterval.current) {
        clearInterval(keepAliveInterval.current);
      }
      if (backendWakeInterval.current) {
        clearInterval(backendWakeInterval.current);
      }
      if (warmupCheckInterval.current) {
        clearInterval(warmupCheckInterval.current);
      }
    };
  }, []);

  const initializeService = async () => {
    try {
      setIsWarmingUp(true);
      setBackendStatus('waking');
      setAiStatus('checking');
      
      await wakeUpBackend();
      
      const healthResponse = await axios.get(`${API_BASE_URL}/health`, {
        timeout: 10000
      }).catch(() => null);
      
      if (healthResponse?.data) {
        setServiceStatus({
          enhancedFallback: healthResponse.data.client_initialized || false,
          validKeys: healthResponse.data.client_initialized ? 1 : 0,
          totalKeys: healthResponse.data.api_key_configured ? 1 : 0
        });
        
        setGroqWarmup(healthResponse.data.ai_warmup_complete || false);
        setModelInfo(healthResponse.data.model_info || { name: healthResponse.data.model });
        setBackendStatus('ready');
      }
      
      await forceGroqWarmup();
      
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
      console.log('🔔 Waking up backend...');
      setLoadingMessage('Waking up backend...');
      
      const pingPromises = [
        axios.get(`${API_BASE_URL}/ping`, { timeout: 8000 }),
        axios.get(`${API_BASE_URL}/health`, { timeout: 10000 })
      ];
      
      await Promise.allSettled(pingPromises);
      
      console.log('✅ Backend is responding');
      setBackendStatus('ready');
      setLoadingMessage('');
      
    } catch (error) {
      console.log('⚠️ Backend is waking up...');
      setBackendStatus('waking');
      
      setTimeout(() => {
        axios.get(`${API_BASE_URL}/ping`, { timeout: 15000 })
          .then(() => {
            setBackendStatus('ready');
            console.log('✅ Backend fully awake');
          })
          .catch(() => {
            setBackendStatus('sleeping');
            console.log('❌ Backend still sleeping');
          });
      }, 3000);
    }
  };

  const forceGroqWarmup = async () => {
    try {
      setAiStatus('warming');
      setLoadingMessage('Warming up Groq API...');
      
      const response = await axios.get(`${API_BASE_URL}/warmup`, {
        timeout: 15000
      });
      
      if (response.data.warmup_complete) {
        setAiStatus('available');
        setGroqWarmup(true);
        console.log('✅ Groq API warmed up successfully');
      } else {
        setAiStatus('warming');
        console.log('⚠️ Groq API still warming up');
        
        setTimeout(() => checkGroqStatus(), 5000);
      }
      
      setLoadingMessage('');
      
    } catch (error) {
      console.log('⚠️ Groq API warm-up failed:', error.message);
      setAiStatus('unavailable');
      
      setTimeout(() => checkGroqStatus(), 3000);
    }
  };

  const checkGroqStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/quick-check`, {
        timeout: 10000
      });
      
      if (response.data.available) {
        setAiStatus('available');
        setGroqWarmup(true);
        if (response.data.model) {
          setModelInfo(response.data.model_info || { name: response.data.model });
        }
      } else if (response.data.warmup_complete) {
        setAiStatus('available');
        setGroqWarmup(true);
      } else {
        setAiStatus('warming');
        setGroqWarmup(false);
      }
      
    } catch (error) {
      console.log('Groq API status check failed:', error.message);
      setAiStatus('unavailable');
    }
  };

  const checkBackendHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`, {
        timeout: 8000
      });
      
      setBackendStatus('ready');
      setGroqWarmup(response.data.ai_warmup_complete || false);
      if (response.data.model_info || response.data.model) {
        setModelInfo(response.data.model_info || { name: response.data.model });
      }
      
      if (response.data.ai_warmup_complete) {
        setAiStatus('available');
      } else {
        setAiStatus('warming');
      }
      
    } catch (error) {
      console.log('Backend health check failed:', error.message);
      setBackendStatus('sleeping');
    }
  };

  const setupPeriodicChecks = () => {
    backendWakeInterval.current = setInterval(() => {
      axios.get(`${API_BASE_URL}/ping`, { timeout: 5000 })
        .then(() => console.log('Keep-alive ping successful'))
        .catch(() => console.log('Keep-alive ping failed'));
    }, 3 * 60 * 1000);
    
    warmupCheckInterval.current = setInterval(() => {
      checkBackendHealth();
    }, 60 * 1000);
    
    const statusCheckInterval = setInterval(() => {
      if (aiStatus === 'warming' || aiStatus === 'checking') {
        checkGroqStatus();
      }
    }, 30000);
    
    keepAliveInterval.current = statusCheckInterval;
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
        if (batchMode) {
          handleBatchFileChange({ target: { files: [file] } });
        } else {
          setResumeFile(file);
          setError('');
        }
      } else {
        setError('Please upload a valid file type (PDF, DOC, DOCX, TXT)');
      }
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 15 * 1024 * 1024) {
        setError('File size too large. Maximum size is 15MB.');
        return;
      }
      setResumeFile(file);
      setError('');
    }
  };

  const handleBatchFileChange = (e) => {
    const files = Array.from(e.target.files);
    
    const validFiles = [];
    const errors = [];
    
    files.forEach(file => {
      if (file.size > 15 * 1024 * 1024) {
        errors.push(`${file.name}: File size too large (max 15MB)`);
      } else if (!file.name.match(/\.(pdf|doc|docx|txt)$/i)) {
        errors.push(`${file.name}: Invalid file type (PDF, DOC, DOCX, TXT only)`);
      } else {
        validFiles.push(file);
      }
    });
    
    if (errors.length > 0) {
      setError(errors.join('. '));
    }
    
    if (validFiles.length > 0) {
      // Allow up to 15 files
      setResumeFiles(prev => [...prev, ...validFiles].slice(0, 15));
      setError('');
    }
  };

  const handleBatchDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files);
      handleBatchFileChange({ target: { files } });
    }
  };

  const removeResumeFile = (index) => {
    setResumeFiles(prev => prev.filter((_, i) => i !== index));
  };

  const clearBatchFiles = () => {
    setResumeFiles([]);
    setBatchAnalysis(null);
    setError('');
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

    if (backendStatus !== 'ready') {
      setError('Backend is warming up. Please wait a moment...');
      await wakeUpBackend();
      return;
    }

    setLoading(true);
    setError('');
    setAnalysis(null);
    setBatchAnalysis(null);
    setProgress(0);
    setLoadingMessage('Starting deterministic ATS analysis...');

    const formData = new FormData();
    formData.append('resume', resumeFile);
    formData.append('jobDescription', jobDescription);

    let progressInterval;

    try {
      progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 85) return 85;
          return prev + Math.random() * 5;
        });
      }, 500);

      setLoadingMessage('AI data extraction (Groq)...');
      setProgress(20);

      setLoadingMessage('Job requirement analysis...');
      setProgress(40);

      setLoadingMessage('Deterministic ATS scoring...');
      setProgress(60);

      const response = await axios.post(`${API_BASE_URL}/analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 60000,
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setProgress(60 + percentCompleted * 0.3);
            setLoadingMessage(percentCompleted < 50 ? 'Uploading file...' : 'Processing...');
          }
        }
      });

      clearInterval(progressInterval);
      setProgress(95);
      
      setLoadingMessage('Deterministic analysis complete!');

      await new Promise(resolve => setTimeout(resolve, 500));
      
      setAnalysis(response.data);
      setProgress(100);

      await checkBackendHealth();

      setTimeout(() => {
        setProgress(0);
        setLoadingMessage('');
      }, 800);

    } catch (err) {
      if (progressInterval) clearInterval(progressInterval);
      
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Request timeout. The backend might be waking up. Please try again in 30 seconds.');
        setBackendStatus('sleeping');
        wakeUpBackend();
      } else if (err.response?.status === 429) {
        setError('Rate limit reached. Groq API has limits. Please try again later.');
      } else if (err.response?.data?.error?.includes('quota') || err.response?.data?.error?.includes('rate limit')) {
        setError('Groq API rate limit exceeded. Please wait a minute and try again.');
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

  const handleBatchAnalyze = async () => {
    if (resumeFiles.length === 0) {
      setError('Please upload at least one resume file');
      return;
    }
    if (!jobDescription.trim()) {
      setError('Please enter a job description');
      return;
    }

    if (backendStatus !== 'ready') {
      setError('Backend is warming up. Please wait a moment...');
      await wakeUpBackend();
      return;
    }

    setBatchLoading(true);
    setError('');
    setAnalysis(null);
    setBatchAnalysis(null);
    setBatchProgress(0);
    setLoadingMessage(`Starting deterministic batch analysis of ${resumeFiles.length} resumes...`);

    const formData = new FormData();
    formData.append('jobDescription', jobDescription);
    
    resumeFiles.forEach((file, index) => {
      formData.append('resumes', file);
    });

    let progressInterval;

    try {
      progressInterval = setInterval(() => {
        setBatchProgress(prev => {
          if (prev >= 85) return 85;
          return prev + Math.random() * 3;
        });
      }, 500);

      setLoadingMessage('Uploading files...');
      setBatchProgress(10);

      const response = await axios.post(`${API_BASE_URL}/analyze-batch`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes for batch processing
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setBatchProgress(10 + percentCompleted * 0.3);
            setLoadingMessage(`Uploading ${resumeFiles.length} files...`);
          }
        }
      });

      clearInterval(progressInterval);
      setBatchProgress(95);
      setLoadingMessage('Deterministic batch analysis complete!');

      await new Promise(resolve => setTimeout(resolve, 800));
      
      setBatchAnalysis(response.data);
      setBatchProgress(100);
      navigateToBatchResults();

      setTimeout(() => {
        setBatchProgress(0);
        setLoadingMessage('');
      }, 800);

    } catch (err) {
      if (progressInterval) clearInterval(progressInterval);
      
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Batch analysis timeout. The backend might be waking up. Please try again.');
        setBackendStatus('sleeping');
        wakeUpBackend();
      } else if (err.response?.status === 429) {
        setError('Groq API rate limit reached. Please try again later.');
      } else {
        setError(err.response?.data?.error || 'An error occurred during batch analysis.');
      }
      
      setBatchProgress(0);
      setLoadingMessage('');
    } finally {
      setBatchLoading(false);
    }
  };

  const handleDownload = () => {
    if (analysis?.excel_filename) {
      window.open(`${API_BASE_URL}/download/${analysis.excel_filename}`, '_blank');
    } else {
      setError('No analysis report available for download.');
    }
  };

  const handleBatchDownload = () => {
    if (batchAnalysis?.batch_excel_filename) {
      window.open(`${API_BASE_URL}/download/${batchAnalysis.batch_excel_filename}`, '_blank');
    } else {
      setError('No batch analysis report available for download.');
    }
  };

  const handleIndividualDownload = (analysisId) => {
    if (analysisId) {
      window.open(`${API_BASE_URL}/download-individual/${analysisId}`, '_blank');
    } else {
      setError('No individual report available for download.');
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

  const getBackendStatusMessage = () => {
    switch(backendStatus) {
      case 'ready': return { 
        text: 'Backend Active', 
        color: '#00ff9d', 
        icon: <CloudLightning size={16} />,
        bgColor: 'rgba(0, 255, 157, 0.1)'
      };
      case 'waking': return { 
        text: 'Backend Waking', 
        color: '#ffd166', 
        icon: <CloudRain size={16} />,
        bgColor: 'rgba(255, 209, 102, 0.1)'
      };
      case 'sleeping': return { 
        text: 'Backend Sleeping', 
        color: '#ff6b6b', 
        icon: <CloudOff size={16} />,
        bgColor: 'rgba(255, 107, 107, 0.1)'
      };
      default: return { 
        text: 'Checking...', 
        color: '#94a3b8', 
        icon: <Loader size={16} className="spinner" />,
        bgColor: 'rgba(148, 163, 184, 0.1)'
      };
    }
  };

  const getAiStatusMessage = () => {
    switch(aiStatus) {
      case 'checking': return { 
        text: 'Checking Groq...', 
        color: '#ffd166', 
        icon: <Bolt size={16} />,
        bgColor: 'rgba(255, 209, 102, 0.1)'
      };
      case 'warming': return { 
        text: 'Groq Warming', 
        color: '#ff9800', 
        icon: <Thermometer size={16} />,
        bgColor: 'rgba(255, 152, 0, 0.1)'
      };
      case 'available': return { 
        text: 'Groq Ready ⚡', 
        color: '#00ff9d', 
        icon: <ZapIcon size={16} />,
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

  const backendStatusInfo = getBackendStatusMessage();
  const aiStatusInfo = getAiStatusMessage();

  const handleLeadsocClick = (e) => {
    e.preventDefault();
    setIsNavigating(true);
    
    setTimeout(() => {
      window.open('https://www.leadsoc.com/', '_blank');
      setIsNavigating(false);
    }, 100);
  };

  const handleForceWarmup = async () => {
    setIsWarmingUp(true);
    setLoadingMessage('Forcing Groq API warm-up...');
    
    try {
      await forceGroqWarmup();
      setLoadingMessage('');
    } catch (error) {
      console.log('Force warm-up failed:', error);
    } finally {
      setIsWarmingUp(false);
    }
  };

  const getModelDisplayName = (modelInfo) => {
    if (!modelInfo) return 'Groq AI';
    if (typeof modelInfo === 'string') return modelInfo;
    return modelInfo.name || 'Groq AI';
  };

  const getModelDescription = (modelInfo) => {
    if (!modelInfo || typeof modelInfo === 'string') return 'Ultra-fast inference';
    return modelInfo.description || 'Groq ultra-fast inference';
  };

  // Render score breakdown component
  const renderScoreBreakdown = (analysis) => {
    if (!analysis?.scoring_breakdown) return null;
    
    const breakdown = analysis.scoring_breakdown;
    const weights = analysis.detailed_breakdown?.weights || {
      'required_skills': 0.35,
      'preferred_skills': 0.15,
      'experience': 0.20,
      'job_title': 0.10,
      'education': 0.10,
      'keywords': 0.05,
      'formatting': 0.05
    };
    
    const components = [
      { name: 'Required Skills', score: breakdown.skill_match_score, weight: weights.required_skills, color: '#00ff9d' },
      { name: 'Experience Match', score: breakdown.experience_score, weight: weights.experience, color: '#ffd166' },
      { name: 'Education Match', score: breakdown.education_score, weight: weights.education, color: '#a78bfa' },
      { name: 'Job Title', score: breakdown.job_title_score, weight: weights.job_title, color: '#60a5fa' },
      { name: 'Keywords', score: breakdown.keyword_match_score, weight: weights.keywords, color: '#f472b6' },
      { name: 'Formatting', score: breakdown.formatting_score, weight: weights.formatting, color: '#34d399' },
      { name: 'Preferred Skills', score: breakdown.preferred_skills_score || 0, weight: weights.preferred_skills, color: '#fbbf24' }
    ];
    
    return (
      <div className="score-breakdown glass">
        <h3>🎯 Deterministic Score Breakdown</h3>
        <div className="breakdown-grid">
          {components.map((comp, index) => (
            <div key={index} className="breakdown-item">
              <div className="breakdown-header">
                <span className="breakdown-name">{comp.name}</span>
                <span className="breakdown-weight">({(comp.weight * 100).toFixed(0)}%)</span>
              </div>
              <div className="breakdown-bar">
                <div 
                  className="breakdown-fill" 
                  style={{ 
                    width: `${comp.score}%`,
                    backgroundColor: comp.color
                  }}
                ></div>
              </div>
              <div className="breakdown-score">
                <span style={{ color: comp.color, fontWeight: 'bold' }}>
                  {comp.score.toFixed(1)}
                </span>
                <span>/100</span>
              </div>
            </div>
          ))}
        </div>
        <div className="breakdown-footer">
          <div className="consistency-info">
            <Hash size={14} />
            <span>Consistency Hash: {analysis.detailed_breakdown?.score_hash?.substring(0, 12)}...</span>
          </div>
          <div className="algorithm-info">
            <Calculator size={14} />
            <span>Algorithm: Deterministic v2.0</span>
          </div>
        </div>
      </div>
    );
  };

  // Render consistency info component
  const renderConsistencyInfo = (analysis) => {
    if (!analysis?.detailed_breakdown) return null;
    
    const details = analysis.detailed_breakdown;
    
    return (
      <div className="consistency-card glass">
        <div className="consistency-header">
          <GitMerge size={20} />
          <h3>Score Consistency Guarantee</h3>
        </div>
        <div className="consistency-content">
          <div className="consistency-item">
            <CheckCircle size={16} className="success" />
            <span>Same inputs always produce same score</span>
          </div>
          <div className="consistency-item">
            <Calculator size={16} className="info" />
            <span>Math-based scoring (no AI judgment)</span>
          </div>
          <div className="consistency-item">
            <Percent size={16} className="info" />
            <span>Decimal scores: {analysis.overall_score.toFixed(2)}</span>
          </div>
          <div className="consistency-item">
            <Hash size={16} className="info" />
            <span>Deterministic variation: {details.deterministic_variation?.toFixed(3) || '0.000'}</span>
          </div>
        </div>
      </div>
    );
  };

  // Render main view
  const renderMainView = () => (
    <div className="upload-section">
      <div className="section-header">
        <h2>Start Your Analysis</h2>
        <p>Upload resume(s) and job description for deterministic ATS scoring</p>
        <div className="service-status">
          <span className="status-badge backend">
            {backendStatusInfo.icon} {backendStatusInfo.text}
          </span>
          <span className="status-badge ai">
            {aiStatusInfo.icon} {aiStatusInfo.text}
          </span>
          <span className="status-badge always-active">
            <ZapIcon size={14} /> Always Active
          </span>
          <span className="status-badge deterministic">
            <Calculator size={14} /> Deterministic Scoring
          </span>
          {modelInfo && (
            <span className="status-badge model">
              <Cpu size={14} /> {getModelDisplayName(modelInfo)}
            </span>
          )}
        </div>
        
        {/* Batch Mode Toggle */}
        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem', justifyContent: 'center' }}>
          <button
            className={`mode-toggle ${!batchMode ? 'active' : ''}`}
            onClick={() => {
              setBatchMode(false);
              setResumeFiles([]);
            }}
            style={{
              padding: '0.75rem 1.5rem',
              background: !batchMode ? 'var(--primary)' : 'rgba(255,255,255,0.1)',
              color: 'white',
              border: 'none',
              borderRadius: '12px',
              cursor: 'pointer',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            <User size={16} /> Single Resume
          </button>
          <button
            className={`mode-toggle ${batchMode ? 'active' : ''}`}
            onClick={() => {
              setBatchMode(true);
              setResumeFile(null);
            }}
            style={{
              padding: '0.75rem 1.5rem',
              background: batchMode ? 'var(--primary)' : 'rgba(255,255,255,0.1)',
              color: 'white',
              border: 'none',
              borderRadius: '12px',
              cursor: 'pointer',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            <Users size={16} /> Multiple Resumes (Up to 15)
          </button>
        </div>
      </div>
      
      <div className="upload-grid">
        {/* Left Column - File Upload */}
        <div className="upload-card glass">
          <div className="card-decoration"></div>
          <div className="card-header">
            <div className="header-icon-wrapper">
              {batchMode ? <Users className="header-icon" /> : <FileText className="header-icon" />}
            </div>
            <div>
              <h2>{batchMode ? 'Upload Resumes (Batch)' : 'Upload Resume'}</h2>
              <p className="card-subtitle">
                {batchMode 
                  ? 'Upload multiple resumes (Max 15, 15MB each)' 
                  : 'Supported: PDF, DOC, DOCX, TXT (Max 15MB)'}
              </p>
            </div>
          </div>
          
          {!batchMode ? (
            // Single file upload
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
                      <span className="upload-hint">Max file size: 15MB</span>
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
          ) : (
            // Batch file upload
            <div 
              className={`upload-area ${dragActive ? 'drag-active' : ''} ${resumeFiles.length > 0 ? 'has-file' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleBatchDrop}
            >
              <input
                type="file"
                id="batch-resume-upload"
                accept=".pdf,.doc,.docx,.txt"
                onChange={handleBatchFileChange}
                className="file-input"
                multiple
              />
              <label htmlFor="batch-resume-upload" className="file-label">
                <div className="upload-icon-wrapper">
                  {resumeFiles.length > 0 ? (
                    <div style={{ width: '100%' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                        <Users size={40} />
                        <div style={{ textAlign: 'left' }}>
                          <span className="file-name">{resumeFiles.length} resume(s) selected</span>
                          <span className="file-size">
                            Total: {(resumeFiles.reduce((acc, file) => acc + file.size, 0) / 1024 / 1024).toFixed(2)} MB
                          </span>
                        </div>
                      </div>
                      
                      <div className="batch-file-list">
                        {resumeFiles.map((file, index) => (
                          <div key={index} className="batch-file-item">
                            <div className="batch-file-info">
                              <FileText size={14} />
                              <span className="batch-file-name">{file.name}</span>
                              <span className="batch-file-size">
                                {(file.size / 1024).toFixed(1)}KB
                              </span>
                            </div>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                removeResumeFile(index);
                              }}
                              className="remove-file-btn"
                            >
                              <X size={14} />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <>
                      <Upload className="upload-icon" />
                      <span className="upload-text">
                        Drag & drop multiple files or click to browse
                      </span>
                      <span className="upload-hint">Max 15 files, 15MB each</span>
                    </>
                  )}
                </div>
              </label>
              
              {resumeFiles.length > 0 && (
                <button 
                  className="change-file-btn"
                  onClick={clearBatchFiles}
                  style={{ background: '#ff6b6b' }}
                >
                  Clear All Files
                </button>
              )}
            </div>
          )}
          
          <div className="upload-stats">
            <div className="stat">
              <div className="stat-icon">
                <Calculator size={14} />
              </div>
              <span>Deterministic ATS scoring</span>
            </div>
            <div className="stat">
              <div className="stat-icon">
                <ZapIcon size={14} />
              </div>
              <span>Guaranteed score consistency</span>
            </div>
            <div className="stat">
              <div className="stat-icon">
                <Cpu size={14} />
              </div>
              <span>{getModelDisplayName(modelInfo)}</span>
            </div>
          </div>
        </div>

        {/* Right Column - Job Description */}
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
          {error.includes('warming up') && (
            <button 
              className="error-action-button"
              onClick={wakeUpBackend}
            >
              <Activity size={16} />
              Wake Backend
            </button>
          )}
        </div>
      )}

      {/* Loading Progress Bar */}
      {(loading || batchLoading) && (
        <div className="loading-section glass">
          <div className="loading-container">
            <div className="loading-header">
              <Loader className="spinner" />
              <h3>{batchMode ? 'Deterministic Batch Analysis' : 'Deterministic ATS Analysis'}</h3>
            </div>
            
            <div className="progress-container">
              <div className="progress-bar" style={{ width: `${batchMode ? batchProgress : progress}%` }}></div>
            </div>
            
            <div className="loading-text">
              <span className="loading-message">{loadingMessage}</span>
              <span className="loading-subtext">
                {batchMode 
                  ? `Processing ${resumeFiles.length} resume(s) with deterministic scoring...` 
                  : `Using deterministic ATS algorithm v2.0...`}
              </span>
            </div>
            
            <div className="progress-stats">
              <span>{Math.round(batchMode ? batchProgress : progress)}%</span>
              <span>•</span>
              <span>Backend: {backendStatus === 'ready' ? 'Active' : 'Waking...'}</span>
              <span>•</span>
              <span>Groq: {aiStatus === 'available' ? 'Ready ⚡' : 'Warming...'}</span>
              <span>•</span>
              <span>Scoring: Deterministic</span>
            </div>
            
            <div className="loading-note info">
              <Calculator size={14} />
              <span>Deterministic scoring guarantees same inputs produce same score</span>
            </div>
          </div>
        </div>
      )}

      <button
        className="analyze-button"
        onClick={batchMode ? handleBatchAnalyze : handleAnalyze}
        disabled={loading || batchLoading || 
                 (batchMode ? resumeFiles.length === 0 : !resumeFile) || 
                 !jobDescription.trim() || 
                 backendStatus === 'sleeping'}
      >
        {(loading || batchLoading) ? (
          <div className="button-loading-content">
            <Loader className="spinner" />
            <span>{batchMode ? 'Analyzing Batch...' : 'Analyzing...'}</span>
          </div>
        ) : backendStatus === 'sleeping' ? (
          <div className="button-waking-content">
            <Activity className="spinner" />
            <span>Waking Backend...</span>
          </div>
        ) : (
          <>
            <div className="button-content">
              <Calculator size={20} />
              <div className="button-text">
                <span>{batchMode ? 'Analyze Multiple Resumes' : 'Analyze Resume'}</span>
                <span className="button-subtext">
                  {batchMode 
                    ? `${resumeFiles.length} resume(s) • Deterministic Scoring` 
                    : `Deterministic ATS Scoring • Guaranteed Consistency`}
                </span>
              </div>
            </div>
            <ChevronRight size={20} />
          </>
        )}
      </button>

      {/* Tips Section */}
      <div className="tips-section">
        {batchMode ? (
          <>
            <div className="tip">
              <Calculator size={16} />
              <span>Deterministic ATS scoring guarantees consistent results</span>
            </div>
            <div className="tip">
              <TrendingUp size={16} />
              <span>Candidates ranked by deterministic score from highest to lowest</span>
            </div>
            <div className="tip">
              <Download size={16} />
              <span>Download comprehensive Excel report with detailed breakdowns</span>
            </div>
            <div className="tip">
              <Hash size={16} />
              <span>Score consistency hash ensures reproducibility</span>
            </div>
          </>
        ) : (
          <>
            <div className="tip">
              <Calculator size={16} />
              <span>Deterministic scoring: same inputs = same score every time</span>
            </div>
            <div className="tip">
              <Percent size={16} />
              <span>Decimal scores (e.g., 78.42) for precise comparisons</span>
            </div>
            <div className="tip">
              <GitMerge size={16} />
              <span>Score consistency guaranteed by mathematical formulas</span>
            </div>
            <div className="tip">
              <Cpu size={16} />
              <span>AI used only for data extraction, not scoring</span>
            </div>
          </>
        )}
      </div>
    </div>
  );

  // Render batch results view
  const renderBatchResultsView = () => (
    <div className="results-section">
      {/* Navigation Header */}
      <div className="navigation-header glass">
        <button onClick={navigateToMain} className="back-button">
          <ArrowLeft size={20} />
          <span>Back to Analysis</span>
        </button>
        <div className="navigation-title">
          <h2>🎯 Deterministic Batch Analysis Results</h2>
          <p>{batchAnalysis?.successfully_analyzed || 0} resumes analyzed with guaranteed consistency</p>
        </div>
        <div className="navigation-actions">
          <button className="download-report-btn" onClick={handleBatchDownload}>
            <DownloadCloud size={18} />
            <span>Download Full Report</span>
          </button>
        </div>
      </div>

      {/* Batch Stats */}
      <div className="batch-stats-container glass">
        <div className="stat-card">
          <div className="stat-icon success">
            <Check size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{batchAnalysis?.successfully_analyzed || 0}</div>
            <div className="stat-label">Successful</div>
          </div>
        </div>
        
        {batchAnalysis?.failed_files > 0 && (
          <div className="stat-card">
            <div className="stat-icon error">
              <X size={24} />
            </div>
            <div className="stat-content">
              <div className="stat-value">{batchAnalysis?.failed_files || 0}</div>
              <div className="stat-label">Failed</div>
            </div>
          </div>
        )}
        
        <div className="stat-card">
          <div className="stat-icon info">
            <Users size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{batchAnalysis?.total_files || 0}</div>
            <div className="stat-label">Total Files</div>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon deterministic">
            <Calculator size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">v2.0</div>
            <div className="stat-label">ATS Algorithm</div>
          </div>
        </div>
      </div>

      {/* Candidates Ranking */}
      <div className="section-title">
        <h2>Candidate Rankings</h2>
        <p>Sorted by Deterministic ATS Score (Highest to Lowest) - Guaranteed Consistency</p>
      </div>
      
      <div className="batch-results-grid">
        {batchAnalysis?.analyses?.map((candidate, index) => (
          <div key={index} className="batch-candidate-card glass">
            <div className="batch-card-header">
              <div className="candidate-rank">
                <div className="rank-badge">#{candidate.rank}</div>
                <div className="candidate-main-info">
                  <h3 className="candidate-name">{candidate.candidate_name}</h3>
                  <div className="candidate-meta">
                    <span className="file-info">{candidate.filename}</span>
                    <span className="file-size">{candidate.file_size}</span>
                  </div>
                </div>
              </div>
              <div className="candidate-score-display">
                <div className="score-large" style={{ color: getScoreColor(candidate.overall_score) }}>
                  {candidate.overall_score.toFixed(1)}
                </div>
                <div className="score-label">Deterministic ATS Score</div>
              </div>
            </div>
            
            <div className="batch-card-content">
              <div className="recommendation-badge" style={{ 
                background: getScoreColor(candidate.overall_score) + '20',
                color: getScoreColor(candidate.overall_score),
                border: `1px solid ${getScoreColor(candidate.overall_score)}40`
              }}>
                {candidate.recommendation}
              </div>
              
              <div className="skills-preview">
                <div className="skills-section">
                  <div className="skills-header">
                    <CheckCircle size={14} />
                    <span>Required Skills Matched ({candidate.skills_matched?.length || 0})</span>
                  </div>
                  <div className="skills-list">
                    {candidate.skills_matched?.slice(0, 2).map((skill, idx) => (
                      <span key={idx} className="skill-tag success">{skill}</span>
                    ))}
                    {candidate.skills_matched?.length > 2 && (
                      <span className="more-skills">+{candidate.skills_matched.length - 2} more</span>
                    )}
                  </div>
                </div>
                
                <div className="skills-section">
                  <div className="skills-header">
                    <XCircle size={14} />
                    <span>Required Skills Missing ({candidate.skills_missing?.length || 0})</span>
                  </div>
                  <div className="skills-list">
                    {candidate.skills_missing?.slice(0, 2).map((skill, idx) => (
                      <span key={idx} className="skill-tag error">{skill}</span>
                    ))}
                    {candidate.skills_missing?.length > 2 && (
                      <span className="more-skills">+{candidate.skills_missing.length - 2} more</span>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="consistency-preview">
                <div className="consistency-badge">
                  <Hash size={12} />
                  <span>Consistency: {candidate.detailed_breakdown?.score_hash?.substring(0, 8)}...</span>
                </div>
              </div>
            </div>
            
            <div className="batch-card-footer">
              <button 
                className="view-details-btn"
                onClick={() => navigateToCandidateDetail(index)}
              >
                View Deterministic Analysis
                <ChevronRight size={16} />
              </button>
              {candidate.analysis_id && (
                <button 
                  className="download-individual-btn"
                  onClick={() => handleIndividualDownload(candidate.analysis_id)}
                  title="Download individual report"
                >
                  <FileDown size={16} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Action Buttons */}
      <div className="action-section glass">
        <div className="action-content">
          <h3>Deterministic Batch Analysis Complete</h3>
          <p>All scores are mathematically calculated for guaranteed consistency</p>
        </div>
        <div className="action-buttons">
          <button className="download-button" onClick={handleBatchDownload}>
            <DownloadCloud size={20} />
            <span>Download Full Batch Report</span>
          </button>
          <button className="reset-button" onClick={navigateToMain}>
            <RefreshCw size={20} />
            <span>New Batch Analysis</span>
          </button>
        </div>
      </div>
    </div>
  );

  // Render candidate detail view
  const renderCandidateDetailView = () => {
    const candidate = batchAnalysis?.analyses?.[selectedCandidateIndex];
    
    if (!candidate) {
      return (
        <div className="error-message glass">
          <AlertCircle size={20} />
          <span>Candidate not found</span>
          <button onClick={navigateBack} className="back-button">
            <ArrowLeft size={16} />
            Go Back
          </button>
        </div>
      );
    }

    return (
      <div className="results-section">
        {/* Navigation Header */}
        <div className="navigation-header glass">
          <button onClick={navigateBack} className="back-button">
            <ArrowLeft size={20} />
            <span>Back to Rankings</span>
          </button>
          <div className="navigation-title">
            <h2>Deterministic ATS Analysis</h2>
            <p>Rank #{candidate.rank} • {candidate.candidate_name}</p>
          </div>
          <div className="navigation-actions">
            {candidate.analysis_id && (
              <button 
                className="download-report-btn" 
                onClick={() => handleIndividualDownload(candidate.analysis_id)}
              >
                <FileDown size={18} />
                <span>Download Individual Report</span>
              </button>
            )}
            <button 
              className="download-report-btn secondary" 
              onClick={handleBatchDownload}
            >
              <DownloadCloud size={18} />
              <span>Download Full Batch</span>
            </button>
          </div>
        </div>

        {/* Candidate Header */}
        <div className="analysis-header">
          <div className="candidate-info">
            <div className="candidate-avatar">
              <User size={24} />
            </div>
            <div>
              <h2 className="candidate-name">{candidate.candidate_name}</h2>
              <div className="candidate-meta">
                <span className="analysis-date">
                  <Clock size={14} />
                  Rank: #{candidate.rank}
                </span>
                <span className="file-info">
                  <FileText size={14} />
                  {candidate.filename} • {candidate.file_size}
                </span>
              </div>
            </div>
          </div>
          
          <div className="score-display">
            <div className="score-circle-wrapper">
              <div className="score-circle-glow" style={{ 
                background: `radial-gradient(circle, ${getScoreColor(candidate.overall_score)}22 0%, transparent 70%)` 
              }}></div>
              <div 
                className="score-circle" 
                style={{ 
                  borderColor: getScoreColor(candidate.overall_score),
                  background: `conic-gradient(${getScoreColor(candidate.overall_score)} ${candidate.overall_score * 3.6}deg, #2d3749 0deg)` 
                }}
              >
                <div className="score-inner">
                  <div className="score-value" style={{ color: getScoreColor(candidate.overall_score) }}>
                    {candidate.overall_score.toFixed(1)}
                  </div>
                  <div className="score-label">Deterministic ATS Score</div>
                </div>
              </div>
            </div>
            <div className="score-info">
              <h3 className="score-grade">{getScoreGrade(candidate.overall_score)}</h3>
              <p className="score-description">
                Math-based scoring with guaranteed consistency
              </p>
              <div className="score-meta">
                <span className="meta-item">
                  <Calculator size={12} />
                  Algorithm: Deterministic v2.0
                </span>
                <span className="meta-item">
                  <Hash size={12} />
                  Consistency Hash: {candidate.detailed_breakdown?.score_hash?.substring(0, 8)}...
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Score Breakdown */}
        {renderScoreBreakdown(candidate)}
        
        {/* Consistency Info */}
        {renderConsistencyInfo(candidate)}

        {/* Recommendation Card */}
        <div className="recommendation-card glass" style={{
          background: `linear-gradient(135deg, ${getScoreColor(candidate.overall_score)}15, ${getScoreColor(candidate.overall_score)}08)`,
          borderLeft: `4px solid ${getScoreColor(candidate.overall_score)}`
        }}>
          <div className="recommendation-header">
            <AwardIcon size={28} style={{ color: getScoreColor(candidate.overall_score) }} />
            <div>
              <h3>Deterministic Analysis Recommendation</h3>
              <p className="recommendation-subtitle">
                Based on mathematical scoring formulas • Guaranteed consistency
              </p>
            </div>
          </div>
          <div className="recommendation-content">
            <p className="recommendation-text">{candidate.recommendation}</p>
            <div className="confidence-badge">
              <Calculator size={16} />
              <span>Deterministic ATS Scoring</span>
            </div>
          </div>
        </div>

        {/* Skills Analysis */}
        <div className="section-title">
          <h2>Skills Analysis</h2>
          <p>Required skills matching based on deterministic comparison</p>
        </div>
        
        <div className="skills-grid">
          <div className="skills-card glass success">
            <div className="skills-card-header">
              <div className="skills-icon success">
                <CheckCircle size={24} />
              </div>
              <div className="skills-header-content">
                <h3>Required Skills Matched</h3>
                <p className="skills-subtitle">Found in resume (deterministic match)</p>
              </div>
              <div className="skills-count success">
                <span>{candidate.skills_matched?.length || 0}</span>
              </div>
            </div>
            <div className="skills-content">
              <ul className="skills-list">
                {candidate.skills_matched?.map((skill, index) => (
                  <li key={index} className="skill-item success">
                    <div className="skill-item-content">
                      <CheckCircle size={16} />
                      <span>{skill}</span>
                    </div>
                  </li>
                ))}
                {(!candidate.skills_matched || candidate.skills_matched.length === 0) && (
                  <li className="no-items">No required skills matched</li>
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
                <h3>Required Skills Missing</h3>
                <p className="skills-subtitle">Not found in resume (deterministic comparison)</p>
              </div>
              <div className="skills-count warning">
                <span>{candidate.skills_missing?.length || 0}</span>
              </div>
            </div>
            <div className="skills-content">
              <ul className="skills-list">
                {candidate.skills_missing?.map((skill, index) => (
                  <li key={index} className="skill-item warning">
                    <div className="skill-item-content">
                      <XCircle size={16} />
                      <span>{skill}</span>
                    </div>
                  </li>
                ))}
                {(!candidate.skills_missing || candidate.skills_missing.length === 0) && (
                  <li className="no-items success-text">All required skills are present!</li>
                )}
              </ul>
            </div>
          </div>
        </div>

        {/* Summary Section */}
        <div className="section-title">
          <h2>Profile Summary</h2>
          <p>Deterministic analysis of resume content</p>
        </div>
        
        <div className="summary-grid">
          <div className="summary-card glass">
            <div className="summary-header">
              <div className="summary-icon">
                <Briefcase size={24} />
              </div>
              <h3>Experience Analysis</h3>
            </div>
            <div className="summary-content">
              <p className="detailed-summary">{candidate.experience_summary || "No experience summary available."}</p>
              <div className="summary-footer">
                <span className="summary-tag">Deterministic Experience Match</span>
              </div>
            </div>
          </div>

          <div className="summary-card glass">
            <div className="summary-header">
              <div className="summary-icon">
                <BookOpen size={24} />
              </div>
              <h3>Education Analysis</h3>
            </div>
            <div className="summary-content">
              <p className="detailed-summary">{candidate.education_summary || "No education summary available."}</p>
              <div className="summary-footer">
                <span className="summary-tag">Deterministic Education Match</span>
              </div>
            </div>
          </div>
        </div>

        {/* Action Section */}
        <div className="action-section glass">
          <div className="action-content">
            <h3>Deterministic Analysis Complete</h3>
            <p>All scores are mathematically calculated for guaranteed consistency</p>
          </div>
          <div className="action-buttons">
            {candidate.analysis_id && (
              <button 
                className="download-button" 
                onClick={() => handleIndividualDownload(candidate.analysis_id)}
              >
                <FileDown size={20} />
                <span>Download Individual Report</span>
              </button>
            )}
            <button className="download-button secondary" onClick={handleBatchDownload}>
              <DownloadCloud size={20} />
              <span>Download Full Batch Report</span>
            </button>
            <button className="reset-button" onClick={navigateBack}>
              <ArrowLeft size={20} />
              <span>Back to Rankings</span>
            </button>
          </div>
        </div>
      </div>
    );
  };

  // Render single analysis view
  const renderSingleAnalysisView = () => (
    <div className="results-section">
      <div className="navigation-header glass">
        <button onClick={() => {
          setAnalysis(null);
          setCurrentView('main');
        }} className="back-button">
          <ArrowLeft size={20} />
          <span>Back to Analysis</span>
        </button>
        <div className="navigation-title">
          <h2>🎯 Deterministic ATS Analysis Results</h2>
          <p>{analysis.candidate_name} • Score Consistency Guaranteed</p>
        </div>
        <div className="navigation-actions">
          <button className="download-report-btn" onClick={handleDownload}>
            <DownloadCloud size={18} />
            <span>Download Report</span>
          </button>
        </div>
      </div>

      {/* Candidate Header */}
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
                Deterministic ATS Analysis
              </span>
              <span className="algorithm-info">
                <Calculator size={14} />
                Algorithm: v2.0 • Guaranteed Consistency
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
                  {analysis.overall_score.toFixed(1)}
                </div>
                <div className="score-label">Deterministic ATS Score</div>
              </div>
            </div>
          </div>
          <div className="score-info">
            <h3 className="score-grade">{getScoreGrade(analysis.overall_score)}</h3>
            <p className="score-description">
              Math-based scoring • Same inputs = Same score every time
            </p>
            <div className="score-meta">
              <span className="meta-item">
                <Calculator size={12} />
                Algorithm: Deterministic v2.0
              </span>
              <span className="meta-item">
                <Hash size={12} />
                Consistency Hash: {analysis.detailed_breakdown?.score_hash?.substring(0, 8)}...
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Score Breakdown */}
      {renderScoreBreakdown(analysis)}
      
      {/* Consistency Info */}
      {renderConsistencyInfo(analysis)}

      {/* Recommendation Card */}
      <div className="recommendation-card glass" style={{
        background: `linear-gradient(135deg, ${getScoreColor(analysis.overall_score)}15, ${getScoreColor(analysis.overall_score)}08)`,
        borderLeft: `4px solid ${getScoreColor(analysis.overall_score)}`
      }}>
        <div className="recommendation-header">
          <AwardIcon size={28} style={{ color: getScoreColor(analysis.overall_score) }} />
          <div>
            <h3>Deterministic Analysis Recommendation</h3>
            <p className="recommendation-subtitle">
              Based on mathematical scoring formulas • Guaranteed consistency
            </p>
          </div>
        </div>
        <div className="recommendation-content">
          <p className="recommendation-text">{analysis.recommendation}</p>
          <div className="confidence-badge">
            <Calculator size={16} />
            <span>Deterministic ATS Scoring</span>
          </div>
        </div>
      </div>

      {/* Skills Analysis */}
      <div className="section-title">
        <h2>Skills Analysis</h2>
        <p>Required skills matching based on deterministic comparison</p>
      </div>
      
      <div className="skills-grid">
        <div className="skills-card glass success">
          <div className="skills-card-header">
            <div className="skills-icon success">
              <CheckCircle size={24} />
            </div>
            <div className="skills-header-content">
              <h3>Required Skills Matched</h3>
              <p className="skills-subtitle">Found in resume (deterministic match)</p>
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
                </li>
              ))}
              {(!analysis.skills_matched || analysis.skills_matched.length === 0) && (
                <li className="no-items">No required skills matched</li>
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
              <h3>Required Skills Missing</h3>
              <p className="skills-subtitle">Not found in resume (deterministic comparison)</p>
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
        <p>Deterministic analysis of resume content</p>
      </div>
      
      <div className="summary-grid">
        <div className="summary-card glass">
          <div className="summary-header">
            <div className="summary-icon">
              <Briefcase size={24} />
            </div>
            <h3>Experience Analysis</h3>
          </div>
          <div className="summary-content">
            <p className="detailed-summary">{analysis.experience_summary || "No experience summary available."}</p>
            <div className="summary-footer">
              <span className="summary-tag">Deterministic Experience Match</span>
            </div>
          </div>
        </div>

        <div className="summary-card glass">
          <div className="summary-header">
            <div className="summary-icon">
              <BookOpen size={24} />
            </div>
            <h3>Education Analysis</h3>
          </div>
          <div className="summary-content">
            <p className="detailed-summary">{analysis.education_summary || "No education summary available."}</p>
            <div className="summary-footer">
              <span className="summary-tag">Deterministic Education Match</span>
            </div>
          </div>
        </div>
      </div>

      {/* Insights Section */}
      <div className="section-title">
        <h2>Insights & Recommendations</h2>
        <p>Based on deterministic scoring analysis</p>
      </div>
      
      <div className="insights-grid">
        <div className="insight-card glass">
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
              <p className="insight-subtitle">Opportunities to improve ATS score</p>
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
          <h3>Deterministic Analysis Complete</h3>
          <p>All scores are mathematically calculated for guaranteed consistency</p>
        </div>
        <div className="action-buttons">
          <button className="download-button" onClick={handleDownload}>
            <DownloadCloud size={20} />
            <span>Download Detailed Report</span>
          </button>
          <button className="reset-button" onClick={() => {
            setAnalysis(null);
            setCurrentView('main');
          }}>
            <RefreshCw size={20} />
            <span>New Analysis</span>
          </button>
        </div>
      </div>
    </div>
  );

  // Main render function
  const renderCurrentView = () => {
    if (analysis && !batchAnalysis) {
      return renderSingleAnalysisView();
    }

    switch (currentView) {
      case 'batch-results':
        return renderBatchResultsView();
      case 'candidate-detail':
        return renderCandidateDetailView();
      default:
        return renderMainView();
    }
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
                <Calculator className="logo-icon" />
              </div>
              <div className="logo-text">
                <h1>Deterministic ATS Analyzer</h1>
                <div className="logo-subtitle">
                  <span className="powered-by">Powered by</span>
                  <span className="groq-badge">⚡ Groq</span>
                  <span className="divider">•</span>
                  <span className="tagline">Math-based • Consistent • Reliable</span>
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
            {/* Backend Status */}
            <div 
              className="feature backend-status-indicator" 
              style={{ 
                backgroundColor: backendStatusInfo.bgColor,
                borderColor: `${backendStatusInfo.color}30`,
                color: backendStatusInfo.color
              }}
            >
              {backendStatusInfo.icon}
              <span>{backendStatusInfo.text}</span>
              {backendStatus === 'waking' && <Loader size={12} className="pulse-spinner" />}
            </div>
            
            {/* AI Status */}
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
              {aiStatus === 'warming' && <Loader size={12} className="pulse-spinner" />}
            </div>
            
            {/* Deterministic Scoring Badge */}
            <div className="feature deterministic-badge">
              <Calculator size={16} />
              <span>Deterministic Scoring</span>
            </div>
            
            {/* Model Info */}
            {modelInfo && (
              <div className="feature model-info">
                <Cpu size={16} />
                <span>{getModelDisplayName(modelInfo)}</span>
              </div>
            )}
            
            {/* Navigation Indicator */}
            {currentView !== 'main' && (
              <div className="feature nav-indicator">
                <Grid size={16} />
                <span>{currentView === 'batch-results' ? 'Batch Results' : 'Candidate Details'}</span>
              </div>
            )}
            
            {/* Warm-up Button */}
            {aiStatus !== 'available' && (
              <button 
                className="feature warmup-button"
                onClick={handleForceWarmup}
                disabled={isWarmingUp}
              >
                {isWarmingUp ? (
                  <Loader size={16} className="spinner" />
                ) : (
                  <Thermometer size={16} />
                )}
                <span>Warm Up AI</span>
              </button>
            )}
            
            {/* Quota Status Toggle */}
            <button 
              className="feature quota-toggle"
              onClick={() => setShowQuotaPanel(!showQuotaPanel)}
              title="Show service status"
            >
              <BarChart size={16} />
              <span>Service Status</span>
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
        {/* Status Panel */}
        {showQuotaPanel && (
          <div className="quota-status-panel glass">
            <div className="quota-panel-header">
              <div className="quota-title">
                <Activity size={20} />
                <h3>Service Status</h3>
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
                <div className="summary-label">Backend Status</div>
                <div className={`summary-value ${backendStatus === 'ready' ? 'success' : backendStatus === 'waking' ? 'warning' : 'error'}`}>
                  {backendStatus === 'ready' ? '✅ Active' : 
                   backendStatus === 'waking' ? '🔥 Waking Up' : 
                   '💤 Sleeping'}
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Groq API Status</div>
                <div className={`summary-value ${aiStatus === 'available' ? 'success' : aiStatus === 'warming' ? 'warning' : 'error'}`}>
                  {aiStatus === 'available' ? '⚡ Ready' : 
                   aiStatus === 'warming' ? '🔥 Warming' : 
                   '⚠️ Enhanced Mode'}
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">ATS Algorithm</div>
                <div className="summary-value deterministic">
                  🎯 Deterministic v2.0
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Score Consistency</div>
                <div className="summary-value success">
                  ✅ Guaranteed
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Batch Capacity</div>
                <div className="summary-value info">
                  📊 Up to 15 resumes
                </div>
              </div>
            </div>
            
            <div className="action-buttons-panel">
              <button 
                className="action-button refresh"
                onClick={checkBackendHealth}
              >
                <RefreshCw size={16} />
                Refresh Status
              </button>
              <button 
                className="action-button warmup"
                onClick={handleForceWarmup}
                disabled={isWarmingUp}
              >
                {isWarmingUp ? (
                  <Loader size={16} className="spinner" />
                ) : (
                  <Thermometer size={16} />
                )}
                Force Warm-up
              </button>
            </div>
          </div>
        )}

        {/* Status Banner */}
        <div className="top-notice-bar glass">
          <div className="notice-content">
            <div className="status-indicators">
              <div className={`status-indicator ${backendStatus === 'ready' ? 'active' : 'inactive'}`}>
                <div className="indicator-dot"></div>
                <span>Backend: {backendStatus === 'ready' ? 'Active' : 'Waking'}</span>
              </div>
              <div className={`status-indicator ${aiStatus === 'available' ? 'active' : 'inactive'}`}>
                <div className="indicator-dot"></div>
                <span>Groq: {aiStatus === 'available' ? 'Ready ⚡' : aiStatus === 'warming' ? 'Warming...' : 'Enhanced'}</span>
              </div>
              <div className="status-indicator active">
                <div className="indicator-dot" style={{ background: '#00ff9d', animation: 'pulse 1.5s infinite' }}></div>
                <span>ATS: Deterministic v2.0</span>
              </div>
              <div className="status-indicator active">
                <div className="indicator-dot" style={{ background: '#00ff9d' }}></div>
                <span>Consistency: Guaranteed</span>
              </div>
            </div>
            
            {backendStatus !== 'ready' && (
              <div className="wakeup-message">
                <AlertCircle size={16} />
                <span>Backend is waking up. Analysis may be slower for the first request.</span>
              </div>
            )}
            
            {aiStatus === 'warming' && (
              <div className="wakeup-message">
                <Thermometer size={16} />
                <span>Groq API is warming up. This ensures ultra-fast responses.</span>
              </div>
            )}
          </div>
        </div>

        {/* Render Current View */}
        {renderCurrentView()}
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <div className="footer-brand">
            <div className="footer-logo">
              <Calculator size={20} />
              <span>Deterministic ATS Analyzer</span>
            </div>
            <p className="footer-tagline">
              Math-based ATS scoring with guaranteed consistency • Same inputs = Same score every time • Up to 15 resumes per batch
            </p>
          </div>
          
          <div className="footer-links">
            <div className="footer-section">
              <h4>Features</h4>
              <a href="#">Deterministic Scoring</a>
              <a href="#">Guaranteed Consistency</a>
              <a href="#">Decimal Scores</a>
              <a href="#">Excel Reports</a>
            </div>
            <div className="footer-section">
              <h4>Scoring</h4>
              <a href="#">Required Skills</a>
              <a href="#">Experience Match</a>
              <a href="#">Education Match</a>
              <a href="#">Formatting Score</a>
            </div>
            <div className="footer-section">
              <h4>Navigation</h4>
              <a href="#" onClick={navigateToMain}>New Analysis</a>
              {currentView !== 'main' && (
                <a href="#" onClick={navigateBack}>Go Back</a>
              )}
              <a href="#">Support</a>
              <a href="#">Documentation</a>
            </div>
          </div>
        </div>
        
        <div className="footer-bottom">
          <p>© 2024 Deterministic ATS Analyzer. Built with React + Flask + Groq API. Math-based Scoring.</p>
          <div className="footer-stats">
            <span className="stat">
              <CloudLightning size={12} />
              Backend: {backendStatus === 'ready' ? 'Active' : 'Waking'}
            </span>
            <span className="stat">
              <Calculator size={12} />
              ATS: Deterministic v2.0
            </span>
            <span className="stat">
              <Hash size={12} />
              Consistency: Guaranteed
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
