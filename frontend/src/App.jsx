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
  Cloud, CloudOff, CloudLightning, CloudRain
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
  
  // UPDATED: Point to your backend with Groq
  const API_BASE_URL = 'https://resume-analyzer-1-pevo.onrender.com';
  
  const keepAliveInterval = useRef(null);
  const backendWakeInterval = useRef(null);
  const warmupCheckInterval = useRef(null);

  // Initialize service on mount
  useEffect(() => {
    initializeService();
    
    // Cleanup on unmount
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
      
      // Start backend wake-up sequence
      await wakeUpBackend();
      
      // Check backend health
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
      
      // Force Groq warm-up
      await forceGroqWarmup();
      
      // Set up periodic checks
      setupPeriodicChecks();
      
    } catch (err) {
      console.log('Service initialization error:', err.message);
      setBackendStatus('sleeping');
      
      // Retry after 5 seconds
      setTimeout(() => initializeService(), 5000);
    } finally {
      setIsWarmingUp(false);
    }
  };

  const wakeUpBackend = async () => {
    try {
      console.log('🔔 Waking up backend...');
      setLoadingMessage('Waking up backend...');
      
      // Send multiple pings to ensure backend wakes up
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
      
      // Send a longer timeout request to fully wake it
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
        
        // Check status again in 5 seconds
        setTimeout(() => checkGroqStatus(), 5000);
      }
      
      setLoadingMessage('');
      
    } catch (error) {
      console.log('⚠️ Groq API warm-up failed:', error.message);
      setAiStatus('unavailable');
      
      // Check status in background
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
      
      // Update AI status based on warmup
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
    // Keep backend alive every 3 minutes
    backendWakeInterval.current = setInterval(() => {
      axios.get(`${API_BASE_URL}/ping`, { timeout: 5000 })
        .then(() => console.log('Keep-alive ping successful'))
        .catch(() => console.log('Keep-alive ping failed'));
    }, 3 * 60 * 1000);
    
    // Check backend health every minute
    warmupCheckInterval.current = setInterval(() => {
      checkBackendHealth();
    }, 60 * 1000);
    
    // Check Groq status every 30 seconds when warming
    const statusCheckInterval = setInterval(() => {
      if (aiStatus === 'warming' || aiStatus === 'checking') {
        checkGroqStatus();
      }
    }, 30000);
    
    // Clean up this interval when component unmounts
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
      if (file.size > 10 * 1024 * 1024) {
        setError('File size too large. Maximum size is 10MB.');
        return;
      }
      setResumeFile(file);
      setError('');
    }
  };

  const handleBatchFileChange = (e) => {
    const files = Array.from(e.target.files);
    
    // Check each file
    const validFiles = [];
    const errors = [];
    
    files.forEach(file => {
      if (file.size > 10 * 1024 * 1024) {
        errors.push(`${file.name}: File size too large (max 10MB)`);
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
      setResumeFiles(prev => [...prev, ...validFiles].slice(0, 20)); // Max 20 files
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

    // Check backend status before starting
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
          return prev + Math.random() * 5; // Groq is faster
        });
      }, 500);

      // Update loading message based on service status
      if (aiStatus === 'available' && groqWarmup) {
        setLoadingMessage('Groq AI analysis (Ultra-fast)...');
      } else {
        setLoadingMessage('Enhanced analysis (Warming up Groq)...');
      }
      setProgress(20);

      // Upload file
      setLoadingMessage('Uploading and processing resume...');
      setProgress(30);

      const response = await axios.post(`${API_BASE_URL}/analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 60000, // 60 seconds (Groq is faster)
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

      await new Promise(resolve => setTimeout(resolve, 500)); // Shorter delay for Groq
      
      setAnalysis(response.data);
      setProgress(100);

      // Update status
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
    setLoadingMessage(`Starting batch analysis of ${resumeFiles.length} resumes...`);

    const formData = new FormData();
    formData.append('jobDescription', jobDescription);
    
    // Add all resume files
    resumeFiles.forEach((file, index) => {
      formData.append('resumes', file);
    });

    let progressInterval;

    try {
      // Start progress simulation
      progressInterval = setInterval(() => {
        setBatchProgress(prev => {
          if (prev >= 85) return 85;
          return prev + Math.random() * 3; // Faster for Groq
        });
      }, 500);

      setLoadingMessage('Uploading files...');
      setBatchProgress(10);

      const response = await axios.post(`${API_BASE_URL}/analyze-batch`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 120000, // 2 minutes for batch processing (Groq is faster)
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
      setLoadingMessage('Batch analysis complete!');

      await new Promise(resolve => setTimeout(resolve, 800));
      
      setBatchAnalysis(response.data);
      setBatchProgress(100);

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
                <ZapIcon className="logo-icon" />
              </div>
              <div className="logo-text">
                <h1>AI Resume Analyzer</h1>
                <div className="logo-subtitle">
                  <span className="powered-by">Powered by</span>
                  <span className="groq-badge">⚡ Groq</span>
                  <span className="divider">•</span>
                  <span className="tagline">Ultra-fast • Always Active</span>
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
            
            {/* Model Info */}
            {modelInfo && (
              <div className="feature model-info">
                <Cpu size={16} />
                <span>{getModelDisplayName(modelInfo)}</span>
              </div>
            )}
            
            {/* Enhanced Fallback Indicator */}
            {serviceStatus.enhancedFallback && (
              <div className="feature enhanced-fallback">
                <Sparkles size={16} />
                <span>Enhanced Analysis</span>
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
                <div className="summary-label">AI Model</div>
                <div className="summary-value">
                  {getModelDisplayName(modelInfo)}
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Speed</div>
                <div className="summary-value success">
                  ⚡ Ultra-fast
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
              <button 
                className="action-button ping"
                onClick={wakeUpBackend}
              >
                <Activity size={16} />
                Wake Backend
              </button>
            </div>
            
            <div className="status-info">
              <div className="info-item">
                <span className="info-label">Service Mode:</span>
                <span className="info-value">Always Active (Keeps Groq warm)</span>
              </div>
              <div className="info-item">
                <span className="info-label">AI Provider:</span>
                <span className="info-value">Groq API (Ultra-fast inference)</span>
              </div>
              <div className="info-item">
                <span className="info-label">Auto Warm-up:</span>
                <span className="info-value">Every 60 seconds when inactive</span>
              </div>
              <div className="info-item">
                <span className="info-label">Keep-alive:</span>
                <span className="info-value">Pings every 3 minutes</span>
              </div>
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
              {modelInfo && (
                <div className="status-indicator active">
                  <div className="indicator-dot" style={{ background: '#00ff9d' }}></div>
                  <span>Model: {getModelDisplayName(modelInfo)}</span>
                </div>
              )}
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

        {!analysis && !batchAnalysis ? (
          <div className="upload-section">
            <div className="section-header">
              <h2>Start Your Analysis</h2>
              <p>Upload resume(s) and job description to get detailed insights</p>
              <div className="service-status">
                <span className="status-badge backend">
                  {backendStatusInfo.icon} {backendStatusInfo.text}
                </span>
                <span className="status-badge ai">
                  {aiStatusInfo.icon} {aiStatusInfo.text}
                </span>
                <span className="status-badge always-active">
                  <ZapIcon size={14} /> Ultra-fast
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
                  <Users size={16} /> Multiple Resumes (Batch)
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
                        ? 'Upload multiple resumes (Max 20, 10MB each)' 
                        : 'Supported: PDF, DOC, DOCX, TXT (Max 10MB)'}
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
                            <span className="upload-hint">Max 20 files, 10MB each</span>
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
                      <ZapIcon size={14} />
                    </div>
                    <span>Ultra-fast Groq analysis</span>
                  </div>
                  <div className="stat">
                    <div className="stat-icon">
                      <Cpu size={14} />
                    </div>
                    <span>{getModelDisplayName(modelInfo)}</span>
                  </div>
                  <div className="stat">
                    <div className="stat-icon">
                      <Activity size={14} />
                    </div>
                    <span>Always Active backend</span>
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
                    <h3>{batchMode ? 'Batch Analysis in Progress' : 'Analysis in Progress'}</h3>
                  </div>
                  
                  <div className="progress-container">
                    <div className="progress-bar" style={{ width: `${batchMode ? batchProgress : progress}%` }}></div>
                  </div>
                  
                  <div className="loading-text">
                    <span className="loading-message">{loadingMessage}</span>
                    <span className="loading-subtext">
                      {batchMode 
                        ? `Processing ${resumeFiles.length} resume(s) with ${getModelDisplayName(modelInfo)}...` 
                        : `Using ${getModelDisplayName(modelInfo)} (Ultra-fast)...`}
                    </span>
                  </div>
                  
                  <div className="progress-stats">
                    <span>{Math.round(batchMode ? batchProgress : progress)}%</span>
                    <span>•</span>
                    <span>Backend: {backendStatus === 'ready' ? 'Active' : 'Waking...'}</span>
                    <span>•</span>
                    <span>Groq: {aiStatus === 'available' ? 'Ready ⚡' : 'Warming...'}</span>
                    {modelInfo && (
                      <>
                        <span>•</span>
                        <span>Model: {getModelDisplayName(modelInfo)}</span>
                      </>
                    )}
                  </div>
                  
                  <div className="loading-note info">
                    <Info size={14} />
                    <span>Groq API offers ultra-fast inference for quick responses</span>
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
                    <ZapIcon size={20} />
                    <div className="button-text">
                      <span>{batchMode ? 'Analyze Multiple Resumes' : 'Analyze Resume'}</span>
                      <span className="button-subtext">
                        {batchMode 
                          ? `${resumeFiles.length} resume(s) • ${getModelDisplayName(modelInfo)}` 
                          : `${getModelDisplayName(modelInfo)} • Ultra-fast`}
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
                    <ZapIcon size={16} />
                    <span>Groq API provides ultra-fast batch processing</span>
                  </div>
                  <div className="tip">
                    <TrendingUp size={16} />
                    <span>Candidates will be ranked by ATS score from highest to lowest</span>
                  </div>
                  <div className="tip">
                    <Download size={16} />
                    <span>Download comprehensive Excel report with all candidate data</span>
                  </div>
                  <div className="tip">
                    <Cpu size={16} />
                    <span>Using: {getModelDisplayName(modelInfo)}</span>
                  </div>
                </>
              ) : (
                <>
                  <div className="tip">
                    <ZapIcon size={16} />
                    <span>Groq API offers ultra-fast responses (typically &lt;1s)</span>
                  </div>
                  <div className="tip">
                    <Thermometer size={16} />
                    <span>Groq API automatically warms up when idle</span>
                  </div>
                  <div className="tip">
                    <Activity size={16} />
                    <span>Backend stays awake with automatic pings every 3 minutes</span>
                  </div>
                  <div className="tip">
                    <Cpu size={16} />
                    <span>Using: {getModelDisplayName(modelInfo)}</span>
                  </div>
                </>
              )}
            </div>
          </div>
        ) : batchAnalysis ? (
          // BATCH RESULTS DISPLAY
          <div className="results-section">
            <div className="analysis-header" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                <h2 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
                  ⚡ Batch Analysis Results
                </h2>
                <div style={{ display: 'flex', gap: '1rem' }}>
                  <button
                    className="download-button"
                    style={{ minWidth: 'auto', padding: '0.75rem 1.5rem' }}
                    onClick={handleBatchDownload}
                  >
                    <DownloadCloud size={18} />
                    Download Full Report
                  </button>
                  <button
                    className="reset-button"
                    style={{ minWidth: 'auto', padding: '0.75rem 1.5rem' }}
                    onClick={() => {
                      setBatchAnalysis(null);
                      setResumeFiles([]);
                      setBatchMode(true);
                      setError('');
                    }}
                  >
                    <RefreshCw size={18} />
                    New Batch
                  </button>
                </div>
              </div>
              
              <div className="batch-stats">
                <div className="stat-badge stat-success">
                  <Check size={16} />
                  <span>{batchAnalysis.successfully_analyzed} Successful</span>
                </div>
                {batchAnalysis.failed_files > 0 && (
                  <div className="stat-badge stat-error">
                    <X size={16} />
                    <span>{batchAnalysis.failed_files} Failed</span>
                  </div>
                )}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
                  <Users size={16} />
                  <span>Processed {batchAnalysis.total_files} resumes</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
                  <Cpu size={16} />
                  <span>{getModelDisplayName(batchAnalysis.model_used)}</span>
                </div>
              </div>
              
              {batchAnalysis.errors.length > 0 && (
                <div style={{ 
                  marginTop: '1rem',
                  background: 'rgba(255, 107, 107, 0.1)',
                  padding: '1rem',
                  borderRadius: '12px',
                  border: '1px solid rgba(255, 107, 107, 0.3)',
                  width: '100%'
                }}>
                  <h4 style={{ color: '#ff6b6b', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <AlertCircle size={16} />
                    Errors ({batchAnalysis.errors.length})
                  </h4>
                  <ul style={{ listStyle: 'none', fontSize: '0.9rem' }}>
                    {batchAnalysis.errors.map((error, idx) => (
                      <li key={idx} style={{ marginBottom: '0.25rem', color: 'var(--text-secondary)' }}>
                        • {error.filename}: {error.error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Batch Results Grid */}
            <div className="section-title">
              <h2>Candidate Rankings</h2>
              <p>Sorted by ATS Score (Highest to Lowest)</p>
            </div>
            
            <div className="batch-results-grid">
              {batchAnalysis.analyses.map((candidate, index) => (
                <div key={index} className="batch-candidate-card glass">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                        <div className="rank-badge">
                          #{candidate.rank}
                        </div>
                        <h3 style={{ fontSize: '1.3rem', color: 'var(--text-primary)' }}>
                          {candidate.candidate_name}
                        </h3>
                      </div>
                      <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1rem' }}>
                        {candidate.filename} • {candidate.file_size}
                      </div>
                    </div>
                    
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ 
                        fontSize: '2.5rem', 
                        fontWeight: 800,
                        color: getScoreColor(candidate.overall_score),
                        lineHeight: 1
                      }}>
                        {candidate.overall_score}
                      </div>
                      <div style={{ 
                        fontSize: '0.85rem', 
                        color: 'var(--text-secondary)',
                        marginTop: '0.25rem'
                      }}>
                        ATS Score
                      </div>
                    </div>
                  </div>
                  
                  <div style={{ margin: '1rem 0' }}>
                    <div style={{ 
                      display: 'inline-block',
                      padding: '0.25rem 0.75rem',
                      background: getScoreColor(candidate.overall_score) + '20',
                      color: getScoreColor(candidate.overall_score),
                      borderRadius: '12px',
                      fontSize: '0.9rem',
                      fontWeight: 600,
                      border: `1px solid ${getScoreColor(candidate.overall_score)}40`
                    }}>
                      {candidate.recommendation}
                    </div>
                  </div>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1rem' }}>
                    <div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                        ✅ Matched Skills ({candidate.skills_matched?.length || 0})
                      </div>
                      <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                        {candidate.skills_matched?.slice(0, 3).map((skill, idx) => (
                          <div key={idx} style={{ marginBottom: '0.25rem' }}>• {skill}</div>
                        ))}
                        {candidate.skills_matched?.length > 3 && (
                          <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                            +{candidate.skills_matched.length - 3} more
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                        ❌ Missing Skills ({candidate.skills_missing?.length || 0})
                      </div>
                      <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                        {candidate.skills_missing?.slice(0, 3).map((skill, idx) => (
                          <div key={idx} style={{ marginBottom: '0.25rem' }}>• {skill}</div>
                        ))}
                        {candidate.skills_missing?.length > 3 && (
                          <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                            +{candidate.skills_missing.length - 3} more
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div style={{ 
                    marginTop: '1rem', 
                    paddingTop: '1rem', 
                    borderTop: '1px solid var(--border)',
                    fontSize: '0.85rem',
                    color: 'var(--text-secondary)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ maxWidth: '70%' }}>Experience: {candidate.experience_summary?.substring(0, 60)}...</span>
                      <button
                        onClick={() => {
                          setAnalysis(candidate);
                          setBatchAnalysis(null);
                        }}
                        style={{
                          background: 'transparent',
                          border: '1px solid var(--primary)',
                          color: 'var(--primary)',
                          padding: '0.25rem 0.75rem',
                          borderRadius: '8px',
                          fontSize: '0.8rem',
                          cursor: 'pointer',
                          whiteSpace: 'nowrap'
                        }}
                      >
                        View Details
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Action Section */}
            <div className="action-section glass">
              <div className="action-content">
                <h3>Batch Analysis Complete</h3>
                <p>Download comprehensive Excel report with all candidate details</p>
              </div>
              <div className="action-buttons">
                <button 
                  className="download-button" 
                  onClick={handleBatchDownload}
                >
                  <div className="button-glow"></div>
                  <DownloadCloud size={20} />
                  <span>Download Excel Report</span>
                  <span className="button-badge">Detailed</span>
                </button>
                <button className="reset-button" onClick={() => {
                  setBatchAnalysis(null);
                  setResumeFiles([]);
                  setBatchMode(true);
                  setJobDescription('');
                  setError('');
                  initializeService();
                }}>
                  <RefreshCw size={20} />
                  <span>New Batch Analysis</span>
                </button>
                <button className="share-button" onClick={() => {
                  setBatchAnalysis(null);
                  setBatchMode(false);
                  setResumeFile(null);
                  setResumeFiles([]);
                  setJobDescription('');
                  setError('');
                }}>
                  <User size={20} />
                  <span>Single Resume Mode</span>
                </button>
              </div>
            </div>
          </div>
        ) : (
          // SINGLE RESULT DISPLAY
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
                      <ZapIcon size={12} />
                      {analysis.ai_status === 'Warmed up' ? `${analysis.ai_model} (Ultra-fast)` : 'Enhanced Analysis'}
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
                  <div className="score-meta">
                    <span className="meta-item">
                      <ZapIcon size={12} />
                      Response: {analysis.response_time || 'Ultra-fast'}
                    </span>
                    <span className="meta-item">
                      <Cpu size={12} />
                      Model: {analysis.ai_model}
                    </span>
                  </div>
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
                    {analysis.ai_status === 'Warmed up' ? `${analysis.ai_model} (Groq Ultra-fast)` : 'Enhanced Analysis'}
                  </p>
                </div>
              </div>
              <div className="recommendation-content">
                <p className="recommendation-text">{analysis.recommendation}</p>
                <div className="confidence-badge">
                  <ZapIcon size={16} />
                  <span>{analysis.ai_status === 'Warmed up' ? 'Groq AI' : 'Enhanced Analysis'}</span>
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
                    <h3>Candidate's Skills</h3>
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
                  <span>New Analysis</span>
                </button>
                <button className="share-button" onClick={() => {
                  setAnalysis(null);
                  setBatchMode(true);
                  setResumeFiles([]);
                  setJobDescription('');
                  setError('');
                }}>
                  <Users size={20} />
                  <span>Batch Mode</span>
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
              <ZapIcon size={20} />
              <span>AI Resume Analyzer</span>
            </div>
            <p className="footer-tagline">
              Groq API offers ultra-fast inference for instant responses
            </p>
          </div>
          
          <div className="footer-links">
            <div className="footer-section">
              <h4>Features</h4>
              <a href="#">Ultra-fast AI</a>
              <a href="#">Groq API</a>
              <a href="#">Batch Processing</a>
              <a href="#">Excel Reports</a>
            </div>
            <div className="footer-section">
              <h4>Service</h4>
              <a href="#">Auto Warm-up</a>
              <a href="#">Keep-alive</a>
              <a href="#">Health Checks</a>
              <a href="#">Status Monitor</a>
            </div>
            <div className="footer-section">
              <h4>Contact</h4>
              <a href="#">Support</a>
              <a href="#">Feedback</a>
              <a href="#">Partnerships</a>
              <a href="#">Documentation</a>
            </div>
          </div>
        </div>
        
        <div className="footer-bottom">
          <p>© 2024 AI Resume Analyzer. Built with React + Flask + Groq API. Ultra-fast Mode.</p>
          <div className="footer-stats">
            <span className="stat">
              <CloudLightning size={12} />
              Backend: {backendStatus === 'ready' ? 'Active' : 'Waking'}
            </span>
            <span className="stat">
              <ZapIcon size={12} />
              Groq: {aiStatus === 'available' ? 'Ready ⚡' : 'Warming'}
            </span>
            <span className="stat">
              <Cpu size={12} />
              Model: {modelInfo ? getModelDisplayName(modelInfo) : 'Loading...'}
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
