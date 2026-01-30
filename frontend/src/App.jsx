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
  FileX, Calendar, Mail, Phone, MapPin, Link,
  ThumbsUp, AlertOctagon, Lightbulb, GitBranch,
  Code, Database, Server, Terminal, Palette,
  Music, Camera, Video, Headphones, Mic,
  MessageSquare, Heart, Share2, Bookmark,
  Eye, EyeOff, Search, Settings, Bell,
  HelpCircle, Shield as ShieldIcon, Key,
  LogOut, UserPlus, UserCheck, UserX,
  Star as StarIcon, Heart as HeartIcon,
  Flag, Filter as FilterIcon, SortAsc,
  SortDesc, MoreHorizontal, MoreVertical,
  Maximize2, Minimize2, Plus, Minus,
  Edit, Trash2, Copy, Scissors, Type,
  Bold, Italic, Underline, List,
  Hash, Quote, Divide, Percent,
  DollarSign, Euro, Pound, Yen,
  Bitcoin, CreditCard, ShoppingCart,
  Package, Truck, Box, Warehouse,
  Building, Home as HomeIcon, Navigation,
  Compass, Map, Globe as GlobeIcon,
  Sunrise, Sunset, Moon, CloudSun,
  Umbrella, Wind, ThermometerSun,
  Droplets, Waves, Tree, Flower,
  Leaf, Bug, Fish, Bird, Cat,
  Dog, Rabbit, Cow, Pig, Egg,
  Apple, Carrot, Coffee as CoffeeIcon,
  Wine, Beer, Cake, Cookie, IceCream,
  Pizza, Hamburger, FrenchFries, Drumstick,
  EggFried, Soup, Milk, GlassWater,
  Citrus, Pepper, Salt, Sugar,
  Wheat, Croissant, Sandwich, Donut,
  Candy, Citrus as Lemon, Cherry,
  Strawberry, Grape, Watermelon, Peach,
  Pear, Banana, Avocado, Broccoli,
  Corn, Eggplant, Mushroom, Onion,
  Potato, Tomato, Pumpkin, Radish,
  HotPepper, Garlic, Basil, Sprout,
  Bone, Skull, Ghost, Smile, Frown,
  Meh, Laugh, Angry, Surprised
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
  const [currentView, setCurrentView] = useState('main');
  const [selectedCandidateIndex, setSelectedCandidateIndex] = useState(null);
  
  const API_BASE_URL = 'https://resume-analyzer-1-pevo.onrender.com';
  
  const keepAliveInterval = useRef(null);
  const backendWakeInterval = useRef(null);
  const warmupCheckInterval = useRef(null);

  // Navigation functions
  const navigateToSingleResults = () => {
    setCurrentView('single-results');
    window.scrollTo(0, 0);
  };

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
    setAnalysis(null);
    setBatchAnalysis(null);
    setResumeFile(null);
    setResumeFiles([]);
    setJobDescription('');
    window.scrollTo(0, 0);
  };

  const navigateBack = () => {
    if (currentView === 'candidate-detail') {
      setCurrentView('batch-results');
    } else if (currentView === 'batch-results' || currentView === 'single-results') {
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
        const availableKeys = healthResponse.data.available_keys || 0;
        setServiceStatus({
          enhancedFallback: healthResponse.data.ai_provider_configured || false,
          validKeys: availableKeys,
          totalKeys: 3
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
            console.log('Backend still starting...');
          });
      }, 3000);
    }
  };

  const forceGroqWarmup = async () => {
    if (groqWarmup) return;
    
    try {
      setAiStatus('warming');
      setLoadingMessage('Warming up Groq API...');
      
      const warmupResponse = await axios.get(`${API_BASE_URL}/warmup`, {
        timeout: 30000
      });
      
      if (warmupResponse.data.success) {
        setGroqWarmup(true);
        setAiStatus('available');
        setLoadingMessage('');
        console.log('✅ Groq API warm-up complete');
      }
    } catch (error) {
      console.log('Groq warm-up in progress or failed:', error.message);
      setAiStatus('checking');
      setLoadingMessage('');
    }
  };

  const setupPeriodicChecks = () => {
    if (keepAliveInterval.current) clearInterval(keepAliveInterval.current);
    if (backendWakeInterval.current) clearInterval(backendWakeInterval.current);
    if (warmupCheckInterval.current) clearInterval(warmupCheckInterval.current);

    keepAliveInterval.current = setInterval(() => {
      axios.get(`${API_BASE_URL}/ping`, { timeout: 5000 })
        .then(response => {
          if (response.data.ai_warmup) {
            setGroqWarmup(true);
            setAiStatus('available');
          }
        })
        .catch(() => {
          setBackendStatus('sleeping');
        });
    }, 60000);

    backendWakeInterval.current = setInterval(() => {
      axios.get(`${API_BASE_URL}/health`, { timeout: 5000 })
        .then(response => {
          setBackendStatus('ready');
          if (response.data.available_keys) {
            setServiceStatus(prev => ({
              ...prev,
              validKeys: response.data.available_keys
            }));
          }
        })
        .catch(() => {
          console.log('Health check failed, backend may be sleeping');
        });
    }, 120000);

    warmupCheckInterval.current = setInterval(() => {
      if (!groqWarmup) {
        forceGroqWarmup();
      }
    }, 180000);
  };

  const checkBackendHealth = async () => {
    try {
      setLoadingMessage('Checking service health...');
      const response = await axios.get(`${API_BASE_URL}/health`, {
        timeout: 10000
      });
      
      if (response.data) {
        const availableKeys = response.data.available_keys || 0;
        setServiceStatus({
          enhancedFallback: response.data.ai_provider_configured || false,
          validKeys: availableKeys,
          totalKeys: 3
        });
        setGroqWarmup(response.data.ai_warmup_complete || false);
        setBackendStatus('ready');
        setAiStatus(response.data.ai_warmup_complete ? 'available' : 'warming');
        setModelInfo(response.data.model_info || { name: response.data.model });
        setLoadingMessage('');
        
        console.log('✅ Health check complete', response.data);
      }
    } catch (error) {
      console.log('Health check failed:', error.message);
      setBackendStatus('sleeping');
      setLoadingMessage('');
    }
  };

  const handleSingleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setResumeFile(file);
      setError('');
    }
  };

  const handleMultipleFilesChange = (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 10) {
      setError('Maximum 10 resumes allowed at once');
      return;
    }
    setResumeFiles(files);
    setError('');
  };

  const handleJobDescriptionChange = (e) => {
    setJobDescription(e.target.value);
    setError('');
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
    
    const files = Array.from(e.dataTransfer.files);
    
    if (batchMode) {
      if (files.length > 10) {
        setError('Maximum 10 resumes allowed at once');
        return;
      }
      setResumeFiles(files);
    } else {
      if (files.length > 0) {
        setResumeFile(files[0]);
      }
    }
    setError('');
  };

  const handleSingleSubmit = async (e) => {
    e.preventDefault();
    
    if (!resumeFile || !jobDescription) {
      setError('Please provide both resume and job description');
      return;
    }

    setLoading(true);
    setError('');
    setProgress(0);
    setRetryCount(0);
    setLoadingMessage('Uploading resume and analyzing...');

    try {
      if (backendStatus !== 'ready') {
        setLoadingMessage('Waking up backend service...');
        await wakeUpBackend();
        await new Promise(resolve => setTimeout(resolve, 2000));
      }

      const formData = new FormData();
      formData.append('resume', resumeFile);
      formData.append('job_description', jobDescription);

      setProgress(20);
      setLoadingMessage('Processing with Groq AI...');

      const response = await axios.post(`${API_BASE_URL}/analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 120000,
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setProgress(Math.min(percentCompleted, 80));
        },
      });

      setProgress(100);
      setLoadingMessage('Analysis complete!');

      if (response.data.error) {
        throw new Error(response.data.error);
      }

      setAnalysis(response.data);
      navigateToSingleResults();
      
    } catch (err) {
      console.error('Analysis error:', err);
      
      if (err.code === 'ECONNABORTED' || err.message.includes('timeout')) {
        setError('Request timed out. The backend might be sleeping. Please try again.');
        setBackendStatus('sleeping');
      } else if (err.response?.status === 429) {
        setError('Rate limit reached. Please wait a moment and try again.');
      } else if (err.response?.status === 503) {
        setError('Service temporarily unavailable. The backend is waking up. Please wait...');
        setBackendStatus('waking');
        setTimeout(() => {
          setError('');
          handleSingleSubmit(e);
        }, 5000);
      } else {
        setError(err.response?.data?.error || err.message || 'An error occurred during analysis');
      }
    } finally {
      setLoading(false);
      setProgress(0);
      setLoadingMessage('');
    }
  };

  const handleBatchSubmit = async (e) => {
    e.preventDefault();
    
    if (resumeFiles.length === 0 || !jobDescription) {
      setError('Please provide resumes and job description');
      return;
    }

    if (resumeFiles.length > 10) {
      setError('Maximum 10 resumes allowed');
      return;
    }

    setBatchLoading(true);
    setError('');
    setBatchProgress(0);
    setLoadingMessage(`Processing ${resumeFiles.length} resumes with parallel processing...`);

    try {
      if (backendStatus !== 'ready') {
        setLoadingMessage('Waking up backend service...');
        await wakeUpBackend();
        await new Promise(resolve => setTimeout(resolve, 2000));
      }

      const formData = new FormData();
      resumeFiles.forEach((file, index) => {
        formData.append('resumes', file);
      });
      formData.append('job_description', jobDescription);

      setBatchProgress(10);
      setLoadingMessage(`Analyzing ${resumeFiles.length} resumes in parallel...`);

      const response = await axios.post(`${API_BASE_URL}/batch-analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 180000,
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setBatchProgress(Math.min(10 + percentCompleted * 0.8, 90));
        },
      });

      setBatchProgress(100);
      setLoadingMessage('Batch analysis complete!');

      if (response.data.error) {
        throw new Error(response.data.error);
      }

      setBatchAnalysis(response.data);
      navigateToBatchResults();
      
    } catch (err) {
      console.error('Batch analysis error:', err);
      
      if (err.code === 'ECONNABORTED' || err.message.includes('timeout')) {
        setError('Request timed out. Please try with fewer resumes or try again.');
        setBackendStatus('sleeping');
      } else if (err.response?.status === 429) {
        setError('Rate limit reached. Please wait a moment and try again.');
      } else if (err.response?.status === 503) {
        setError('Service temporarily unavailable. The backend is waking up. Please wait...');
        setBackendStatus('waking');
      } else {
        setError(err.response?.data?.error || err.message || 'An error occurred during batch analysis');
      }
    } finally {
      setBatchLoading(false);
      setBatchProgress(0);
      setLoadingMessage('');
    }
  };

  const handleIndividualDownload = async (analysisId) => {
    try {
      setLoadingMessage(`Preparing individual report...`);
      
      const response = await axios.get(`${API_BASE_URL}/download-individual/${analysisId}`, {
        responseType: 'blob',
        timeout: 30000
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `resume_analysis_${analysisId}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      setLoadingMessage('');
    } catch (error) {
      console.error('Download error:', error);
      setError('Failed to download individual report');
      setLoadingMessage('');
    }
  };

  const handleDownload = async () => {
    if (!analysis) return;
    
    try {
      setLoadingMessage('Preparing Excel report...');
      
      const response = await axios.get(
        `${API_BASE_URL}/download-individual/${analysis.analysis_id}`,
        {
          responseType: 'blob',
          timeout: 30000
        }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const timestamp = new Date().toISOString().split('T')[0];
      link.setAttribute('download', `resume_analysis_${timestamp}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      setLoadingMessage('');
    } catch (error) {
      console.error('Download error:', error);
      setError('Failed to download report. Please try again.');
      setLoadingMessage('');
    }
  };

  const handleBatchDownload = async () => {
    if (!batchAnalysis) return;
    
    try {
      setLoadingMessage('Preparing comprehensive batch Excel report...');
      
      const response = await axios.post(
        `${API_BASE_URL}/download-batch`,
        {
          analyses: batchAnalysis.analyses,
          job_description: jobDescription
        },
        {
          responseType: 'blob',
          timeout: 60000
        }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const timestamp = new Date().toISOString().split('T')[0];
      link.setAttribute('download', `batch_resume_analysis_${timestamp}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      setLoadingMessage('');
    } catch (error) {
      console.error('Batch download error:', error);
      setError('Failed to download batch report. Please try again.');
      setLoadingMessage('');
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#00ff9d';
    if (score >= 60) return '#ffd166';
    return '#ff6b9d';
  };

  const getScoreGrade = (score) => {
    if (score >= 90) return 'Excellent Match';
    if (score >= 80) return 'Strong Match';
    if (score >= 70) return 'Good Match';
    if (score >= 60) return 'Moderate Match';
    return 'Needs Improvement';
  };

  const getBackendStatusMessage = () => {
    switch(backendStatus) {
      case 'ready': return { 
        text: 'Backend Ready', 
        color: '#00ff9d', 
        icon: <Check size={16} />,
        bgColor: 'rgba(0, 255, 157, 0.1)'
      };
      case 'waking': return { 
        text: 'Backend Waking...', 
        color: '#ffd166', 
        icon: <Loader size={16} className="spinner" />,
        bgColor: 'rgba(255, 209, 102, 0.1)'
      };
      case 'sleeping': return { 
        text: 'Backend Sleeping', 
        color: '#ff6b9d', 
        icon: <AlertCircle size={16} />,
        bgColor: 'rgba(255, 107, 157, 0.1)'
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
      case 'available': return { 
        text: 'Groq Ready ⚡', 
        color: '#00ff9d', 
        icon: <Zap size={16} />,
        bgColor: 'rgba(0, 255, 157, 0.1)'
      };
      case 'warming': return { 
        text: 'Groq Warming...', 
        color: '#ffd166', 
        icon: <Thermometer size={16} />,
        bgColor: 'rgba(255, 209, 102, 0.1)'
      };
      case 'checking': return { 
        text: 'Checking Groq...', 
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

  const getAvailableKeysCount = () => {
    return serviceStatus.validKeys || 0;
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

  // UPDATED: Format summary without truncation - complete sentences
  const formatSummary = (text) => {
    if (!text) return "No summary available.";
    
    // Return the full text without truncation
    // Just ensure it ends with proper punctuation
    let result = text.trim();
    
    // Add period if doesn't end with punctuation
    if (!/[.!?]$/.test(result)) {
      result += '.';
    }
    
    return result;
  };

  // Render functions for different views
  const renderMainView = () => (
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
            <ZapIcon size={14} /> Parallel Processing
          </span>
          <span className="status-badge keys">
            <Key size={14} /> {getAvailableKeysCount()}/3 Keys
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
            <Users size={16} /> Multiple Resumes (Up to 10)
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
              <h3>{batchMode ? 'Upload Multiple Resumes' : 'Upload Resume'}</h3>
              <p>{batchMode ? 'PDF, DOCX, DOC, or TXT (Max 10 files)' : 'PDF, DOCX, DOC, or TXT'}</p>
            </div>
          </div>
          
          {batchMode ? (
            <div 
              className={`file-drop-zone ${dragActive ? 'drag-active' : ''} ${resumeFiles.length > 0 ? 'has-files' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => document.getElementById('multiple-file-input').click()}
            >
              <input
                id="multiple-file-input"
                type="file"
                accept=".pdf,.docx,.doc,.txt"
                onChange={handleMultipleFilesChange}
                multiple
                style={{ display: 'none' }}
              />
              {resumeFiles.length > 0 ? (
                <div className="files-selected">
                  <CheckCircle className="success-icon" size={48} />
                  <p className="files-count">{resumeFiles.length} {resumeFiles.length === 1 ? 'Resume' : 'Resumes'} Selected</p>
                  <div className="file-list">
                    {resumeFiles.map((file, index) => (
                      <div key={index} className="file-item">
                        <FileText size={14} />
                        <span>{file.name}</span>
                        <span className="file-size">
                          {(file.size / 1024).toFixed(1)} KB
                        </span>
                      </div>
                    ))}
                  </div>
                  <button className="change-files-btn" onClick={(e) => {
                    e.stopPropagation();
                    setResumeFiles([]);
                  }}>
                    <X size={16} /> Clear All
                  </button>
                </div>
              ) : (
                <div className="drop-zone-content">
                  <Upload className="upload-icon" size={48} />
                  <p className="drop-text">Drop resumes here or click to browse</p>
                  <p className="drop-hint">Support for PDF, DOCX, DOC, TXT (Max 10 files)</p>
                </div>
              )}
            </div>
          ) : (
            <div 
              className={`file-drop-zone ${dragActive ? 'drag-active' : ''} ${resumeFile ? 'has-file' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => document.getElementById('single-file-input').click()}
            >
              <input
                id="single-file-input"
                type="file"
                accept=".pdf,.docx,.doc,.txt"
                onChange={handleSingleFileChange}
                style={{ display: 'none' }}
              />
              {resumeFile ? (
                <div className="file-selected">
                  <CheckCircle className="success-icon" size={48} />
                  <p className="file-name">{resumeFile.name}</p>
                  <p className="file-size">{(resumeFile.size / 1024).toFixed(1)} KB</p>
                  <button className="change-file-btn" onClick={(e) => {
                    e.stopPropagation();
                    setResumeFile(null);
                  }}>
                    <X size={16} /> Remove
                  </button>
                </div>
              ) : (
                <div className="drop-zone-content">
                  <Upload className="upload-icon" size={48} />
                  <p className="drop-text">Drop resume here or click to browse</p>
                  <p className="drop-hint">Support for PDF, DOCX, DOC, TXT</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column - Job Description */}
        <div className="upload-card glass">
          <div className="card-decoration"></div>
          <div className="card-header">
            <div className="header-icon-wrapper">
              <Briefcase className="header-icon" />
            </div>
            <div>
              <h3>Job Description</h3>
              <p>Paste the complete job requirements</p>
            </div>
          </div>
          
          <textarea
            className="job-description-input"
            value={jobDescription}
            onChange={handleJobDescriptionChange}
            placeholder="Paste the job description here...&#10;&#10;Include:&#10;• Required skills and technologies&#10;• Experience requirements&#10;• Education qualifications&#10;• Job responsibilities&#10;• Any specific certifications"
            rows={12}
          />
          
          <div className="job-desc-info">
            <Info size={14} />
            <span>More detailed job descriptions lead to better analysis</span>
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <div className="submit-section">
        <button
          className={`analyze-button ${(batchMode ? (resumeFiles.length === 0 || !jobDescription) : (!resumeFile || !jobDescription)) ? 'disabled' : ''}`}
          onClick={batchMode ? handleBatchSubmit : handleSingleSubmit}
          disabled={batchMode ? (resumeFiles.length === 0 || !jobDescription || batchLoading) : (!resumeFile || !jobDescription || loading)}
        >
          {(loading || batchLoading) ? (
            <>
              <Loader className="spinner" size={20} />
              <span>{loadingMessage || 'Analyzing...'}</span>
            </>
          ) : (
            <>
              <Sparkles size={20} />
              <span>{batchMode ? `Analyze ${resumeFiles.length} Resume${resumeFiles.length !== 1 ? 's' : ''}` : 'Analyze Resume'}</span>
            </>
          )}
        </button>
        
        {(loading || batchLoading) && (
          <div className="progress-bar-container">
            <div 
              className="progress-bar-fill" 
              style={{ width: `${batchMode ? batchProgress : progress}%` }}
            ></div>
          </div>
        )}
      </div>

      {error && (
        <div className="error-message glass">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );

  const renderSingleResultsView = () => {
    if (!analysis) return null;

    return (
      <div className="results-section">
        {/* Navigation Header */}
        <div className="navigation-header glass">
          <button onClick={navigateToMain} className="back-button">
            <ArrowLeft size={20} />
            <span>New Analysis</span>
          </button>
          <div className="navigation-title">
            <h2>Analysis Results</h2>
            <p>Powered by Groq AI</p>
          </div>
          <div className="navigation-actions">
            <button className="download-report-btn" onClick={handleDownload}>
              <FileDown size={18} />
              <span>Download Report</span>
            </button>
          </div>
        </div>

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
                  {new Date().toLocaleDateString()}
                </span>
                <span className="file-info">
                  <FileText size={14} />
                  {analysis.filename} • {analysis.file_size}
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
                  <div className="score-label">ATS Score</div>
                </div>
              </div>
            </div>
            <div className="score-info">
              <h3 className="score-grade">{getScoreGrade(analysis.overall_score)}</h3>
              <p className="score-description">
                Based on skill matching and experience relevance
              </p>
              <div className="score-meta">
                <span className="meta-item">
                  <CheckCircle size={12} />
                  {analysis.skills_matched?.length || 0} skills matched
                </span>
                <span className="meta-item">
                  <XCircle size={12} />
                  {analysis.skills_missing?.length || 0} skills missing
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
            <AwardIcon size={28} style={{ color: getScoreColor(analysis.overall_score) }} />
            <div>
              <h3>Analysis Recommendation</h3>
              <p className="recommendation-subtitle">
                Powered by Groq AI
              </p>
            </div>
          </div>
          <div className="recommendation-content">
            <p className="recommendation-text">{analysis.recommendation}</p>
            <div className="confidence-badge">
              <Brain size={16} />
              <span>Groq AI Analysis</span>
            </div>
          </div>
        </div>

        {/* Skills Analysis - 5-8 skills each */}
        <div className="section-title">
          <h2>Skills Analysis (5-8 skills each)</h2>
          <p>Detailed breakdown of matched and missing skills</p>
        </div>
        
        <div className="skills-grid">
          <div className="skills-card glass success">
            <div className="skills-card-header">
              <div className="skills-icon success">
                <CheckCircle size={24} />
              </div>
              <div className="skills-header-content">
                <h3>Matched Skills</h3>
                <p className="skills-subtitle">Found in resume ({analysis.skills_matched?.length || 0} skills)</p>
              </div>
              <div className="skills-count success">
                <span>{analysis.skills_matched?.length || 0}</span>
              </div>
            </div>
            <div className="skills-content">
              <ul className="skills-list">
                {analysis.skills_matched?.slice(0, 8).map((skill, index) => (
                  <li key={index} className="skill-item success">
                    <div className="skill-item-content">
                      <CheckCircle size={16} />
                      <span>{skill}</span>
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
                <h3>Missing Skills</h3>
                <p className="skills-subtitle">Suggested to learn ({analysis.skills_missing?.length || 0} skills)</p>
              </div>
              <div className="skills-count warning">
                <span>{analysis.skills_missing?.length || 0}</span>
              </div>
            </div>
            <div className="skills-content">
              <ul className="skills-list">
                {analysis.skills_missing?.slice(0, 8).map((skill, index) => (
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

        {/* Summary Section with Concise 4-5 sentences */}
        <div className="section-title">
          <h2>Profile Summary (4-5 sentences each)</h2>
          <p>Key insights extracted from resume (medium length)</p>
        </div>
        
        <div className="summary-grid">
          <div className="summary-card glass">
            <div className="summary-header">
              <div className="summary-icon">
                <Briefcase size={20} />
              </div>
              <h3>Experience Summary</h3>
            </div>
            <div className="summary-content">
              <p className="summary-text">{formatSummary(analysis.experience_summary)}</p>
            </div>
          </div>

          <div className="summary-card glass">
            <div className="summary-header">
              <div className="summary-icon">
                <BookOpen size={20} />
              </div>
              <h3>Education Summary</h3>
            </div>
            <div className="summary-content">
              <p className="summary-text">{formatSummary(analysis.education_summary)}</p>
            </div>
          </div>
        </div>

        {/* Insights Section */}
        <div className="section-title">
          <h2>AI Insights (3 of each)</h2>
          <p>Groq AI-powered strengths and improvement suggestions</p>
        </div>
        
        <div className="insights-grid">
          <div className="insights-card glass success">
            <div className="insights-header">
              <div className="insights-icon success">
                <TrendingUp size={24} />
              </div>
              <h3>Key Strengths</h3>
              <p className="insights-count">{analysis.key_strengths?.length || 0} identified</p>
            </div>
            <div className="insights-content">
              <ul className="insights-list">
                {analysis.key_strengths?.slice(0, 3).map((strength, index) => (
                  <li key={index} className="insight-item success">
                    <div className="insight-number">{index + 1}</div>
                    <div className="insight-text">{strength}</div>
                  </li>
                ))}
                {(!analysis.key_strengths || analysis.key_strengths.length === 0) && (
                  <li className="no-items">No key strengths identified</li>
                )}
              </ul>
            </div>
          </div>

          <div className="insights-card glass warning">
            <div className="insights-header">
              <div className="insights-icon warning">
                <Target size={24} />
              </div>
              <h3>Areas for Improvement</h3>
              <p className="insights-count">{analysis.areas_for_improvement?.length || 0} suggested</p>
            </div>
            <div className="insights-content">
              <ul className="insights-list">
                {analysis.areas_for_improvement?.slice(0, 3).map((area, index) => (
                  <li key={index} className="insight-item warning">
                    <div className="insight-number">{index + 1}</div>
                    <div className="insight-text">{area}</div>
                  </li>
                ))}
                {(!analysis.areas_for_improvement || analysis.areas_for_improvement.length === 0) && (
                  <li className="no-items success-text">No significant areas for improvement!</li>
                )}
              </ul>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="action-section glass">
          <div className="action-content">
            <h3>Analysis Complete</h3>
            <p>Download the complete Excel report or start a new analysis</p>
          </div>
          <div className="action-buttons">
            <button className="download-button" onClick={handleDownload}>
              <Download size={20} />
              <span>Download Excel Report</span>
            </button>
            <button className="reset-button" onClick={navigateToMain}>
              <RefreshCw size={20} />
              <span>New Analysis</span>
            </button>
          </div>
        </div>
      </div>
    );
  };

  const renderBatchResultsView = () => {
    if (!batchAnalysis) return null;

    return (
      <div className="results-section">
        {/* Navigation Header */}
        <div className="navigation-header glass">
          <button onClick={navigateToMain} className="back-button">
            <ArrowLeft size={20} />
            <span>New Analysis</span>
          </button>
          <div className="navigation-title">
            <h2>Batch Analysis Results</h2>
            <p>{batchAnalysis.total_analyzed} Candidates Analyzed</p>
          </div>
          <div className="navigation-actions">
            <button className="download-report-btn" onClick={handleBatchDownload}>
              <FileDown size={18} />
              <span>Download Batch Report</span>
            </button>
          </div>
        </div>

        {/* Batch Stats */}
        <div className="batch-stats glass">
          <div className="stat-card">
            <div className="stat-icon">
              <Users size={24} />
            </div>
            <div className="stat-info">
              <div className="stat-value">{batchAnalysis.total_analyzed}</div>
              <div className="stat-label">Total Candidates</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">
              <TrendingUp size={24} />
            </div>
            <div className="stat-info">
              <div className="stat-value">{batchAnalysis.successful}</div>
              <div className="stat-label">Successful</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">
              <Clock size={24} />
            </div>
            <div className="stat-info">
              <div className="stat-value">{batchAnalysis.processing_time}</div>
              <div className="stat-label">Processing Time</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">
              <Brain size={24} />
            </div>
            <div className="stat-info">
              <div className="stat-value">Groq</div>
              <div className="stat-label">AI Model</div>
            </div>
          </div>
        </div>

        {/* Candidates List */}
        <div className="section-title">
          <h2>Candidate Rankings</h2>
          <p>Sorted by ATS score (highest to lowest)</p>
        </div>

        <div className="batch-candidates-grid">
          {batchAnalysis.analyses?.map((candidate, index) => (
            <div key={index} className="batch-candidate-card glass">
              <div className="batch-card-header">
                <div className="candidate-rank" style={{ 
                  background: getScoreColor(candidate.overall_score) + '20',
                  color: getScoreColor(candidate.overall_score)
                }}>
                  #{candidate.rank}
                </div>
                <div className="candidate-header-info">
                  <h3 className="candidate-card-name">{candidate.candidate_name}</h3>
                  <p className="candidate-card-file">{candidate.filename}</p>
                </div>
                <div className="candidate-score-display">
                  <div className="score-large" style={{ color: getScoreColor(candidate.overall_score) }}>
                    {candidate.overall_score}
                  </div>
                  <div className="score-label">ATS Score</div>
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
                
                <div className="concise-summary-section">
                  <h4>Experience Summary:</h4>
                  <p className="concise-text" style={{ fontSize: '0.9rem', lineHeight: '1.4' }}>
                    {formatSummary(candidate.experience_summary)}
                  </p>
                </div>
                
                <div className="skills-preview">
                  <div className="skills-section">
                    <div className="skills-header">
                      <CheckCircle size={14} />
                      <span>Matched Skills ({candidate.skills_matched?.length || 0})</span>
                    </div>
                    <div className="skills-list">
                      {candidate.skills_matched?.slice(0, 4).map((skill, idx) => (
                        <span key={idx} className="skill-tag success">{skill}</span>
                      ))}
                      {candidate.skills_matched?.length > 4 && (
                        <span className="more-skills">+{candidate.skills_matched.length - 4} more</span>
                      )}
                    </div>
                  </div>
                  
                  <div className="skills-section">
                    <div className="skills-header">
                      <XCircle size={14} />
                      <span>Missing Skills ({candidate.skills_missing?.length || 0})</span>
                    </div>
                    <div className="skills-list">
                      {candidate.skills_missing?.slice(0, 4).map((skill, idx) => (
                        <span key={idx} className="skill-tag error">{skill}</span>
                      ))}
                      {candidate.skills_missing?.length > 4 && (
                        <span className="more-skills">+{candidate.skills_missing.length - 4} more</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="batch-card-footer">
                <button 
                  className="view-details-btn"
                  onClick={() => navigateToCandidateDetail(index)}
                >
                  View Full Details
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
            <h3>Batch Analysis Complete</h3>
            <p>Download comprehensive Excel report with candidate analysis</p>
          </div>
          <div className="action-buttons">
            <button className="download-button" onClick={handleBatchDownload}>
              <DownloadCloud size={20} />
              <span>Download Batch Report</span>
            </button>
            <button className="reset-button" onClick={navigateToMain}>
              <RefreshCw size={20} />
              <span>New Batch Analysis</span>
            </button>
          </div>
        </div>
      </div>
    );
  };

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
            <h2>Candidate Details</h2>
            <p>Rank #{candidate.rank} • {candidate.candidate_name}</p>
          </div>
          <div className="navigation-actions">
            {candidate.analysis_id && (
              <button 
                className="download-report-btn" 
                onClick={() => handleIndividualDownload(candidate.analysis_id)}
              >
                <FileDown size={18} />
                <span>Download Report</span>
              </button>
            )}
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
                    {candidate.overall_score}
                  </div>
                  <div className="score-label">ATS Score</div>
                </div>
              </div>
            </div>
            <div className="score-info">
              <h3 className="score-grade">{getScoreGrade(candidate.overall_score)}</h3>
              <p className="score-description">
                Based on skill matching and experience relevance
              </p>
              <div className="score-meta">
                <span className="meta-item">
                  <CheckCircle size={12} />
                  {candidate.skills_matched?.length || 0} skills matched
                </span>
                <span className="meta-item">
                  <XCircle size={12} />
                  {candidate.skills_missing?.length || 0} skills missing
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Recommendation Card */}
        <div className="recommendation-card glass" style={{
          background: `linear-gradient(135deg, ${getScoreColor(candidate.overall_score)}15, ${getScoreColor(candidate.overall_score)}08)`,
          borderLeft: `4px solid ${getScoreColor(candidate.overall_score)}`
        }}>
          <div className="recommendation-header">
            <AwardIcon size={28} style={{ color: getScoreColor(candidate.overall_score) }} />
            <div>
              <h3>Analysis Recommendation</h3>
              <p className="recommendation-subtitle">
                Powered by Groq AI
              </p>
            </div>
          </div>
          <div className="recommendation-content">
            <p className="recommendation-text">{candidate.recommendation}</p>
            <div className="confidence-badge">
              <Brain size={16} />
              <span>Groq AI Analysis</span>
            </div>
          </div>
        </div>

        {/* Skills Analysis - 5-8 skills each */}
        <div className="section-title">
          <h2>Skills Analysis (5-8 skills each)</h2>
          <p>Detailed breakdown of matched and missing skills</p>
        </div>
        
        <div className="skills-grid">
          <div className="skills-card glass success">
            <div className="skills-card-header">
              <div className="skills-icon success">
                <CheckCircle size={24} />
              </div>
              <div className="skills-header-content">
                <h3>Matched Skills</h3>
                <p className="skills-subtitle">Found in resume ({candidate.skills_matched?.length || 0} skills)</p>
              </div>
              <div className="skills-count success">
                <span>{candidate.skills_matched?.length || 0}</span>
              </div>
            </div>
            <div className="skills-content">
              <ul className="skills-list">
                {candidate.skills_matched?.slice(0, 8).map((skill, index) => (
                  <li key={index} className="skill-item success">
                    <div className="skill-item-content">
                      <CheckCircle size={16} />
                      <span>{skill}</span>
                    </div>
                  </li>
                ))}
                {(!candidate.skills_matched || candidate.skills_matched.length === 0) && (
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
                <h3>Missing Skills</h3>
                <p className="skills-subtitle">Suggested to learn ({candidate.skills_missing?.length || 0} skills)</p>
              </div>
              <div className="skills-count warning">
                <span>{candidate.skills_missing?.length || 0}</span>
              </div>
            </div>
            <div className="skills-content">
              <ul className="skills-list">
                {candidate.skills_missing?.slice(0, 8).map((skill, index) => (
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

        {/* Summary Section with Concise 4-5 sentences */}
        <div className="section-title">
          <h2>Profile Summary (4-5 sentences each)</h2>
          <p>Key insights extracted from resume (medium length)</p>
        </div>
        
        <div className="summary-grid">
          <div className="summary-card glass">
            <div className="summary-header">
              <div className="summary-icon">
                <Briefcase size={20} />
              </div>
              <h3>Experience Summary</h3>
            </div>
            <div className="summary-content">
              <p className="summary-text">{formatSummary(candidate.experience_summary)}</p>
            </div>
          </div>

          <div className="summary-card glass">
            <div className="summary-header">
              <div className="summary-icon">
                <BookOpen size={20} />
              </div>
              <h3>Education Summary</h3>
            </div>
            <div className="summary-content">
              <p className="summary-text">{formatSummary(candidate.education_summary)}</p>
            </div>
          </div>
        </div>

        {/* Insights Section */}
        <div className="section-title">
          <h2>AI Insights (3 of each)</h2>
          <p>Groq AI-powered strengths and improvement suggestions</p>
        </div>
        
        <div className="insights-grid">
          <div className="insights-card glass success">
            <div className="insights-header">
              <div className="insights-icon success">
                <TrendingUp size={24} />
              </div>
              <h3>Key Strengths</h3>
              <p className="insights-count">{candidate.key_strengths?.length || 0} identified</p>
            </div>
            <div className="insights-content">
              <ul className="insights-list">
                {candidate.key_strengths?.slice(0, 3).map((strength, index) => (
                  <li key={index} className="insight-item success">
                    <div className="insight-number">{index + 1}</div>
                    <div className="insight-text">{strength}</div>
                  </li>
                ))}
                {(!candidate.key_strengths || candidate.key_strengths.length === 0) && (
                  <li className="no-items">No key strengths identified</li>
                )}
              </ul>
            </div>
          </div>

          <div className="insights-card glass warning">
            <div className="insights-header">
              <div className="insights-icon warning">
                <Target size={24} />
              </div>
              <h3>Areas for Improvement</h3>
              <p className="insights-count">{candidate.areas_for_improvement?.length || 0} suggested</p>
            </div>
            <div className="insights-content">
              <ul className="insights-list">
                {candidate.areas_for_improvement?.slice(0, 3).map((area, index) => (
                  <li key={index} className="insight-item warning">
                    <div className="insight-number">{index + 1}</div>
                    <div className="insight-text">{area}</div>
                  </li>
                ))}
                {(!candidate.areas_for_improvement || candidate.areas_for_improvement.length === 0) && (
                  <li className="no-items success-text">No significant areas for improvement!</li>
                )}
              </ul>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="action-section glass">
          <div className="action-content">
            <h3>Candidate Analysis Complete</h3>
            <p>Download individual report or go back to rankings</p>
          </div>
          <div className="action-buttons">
            {candidate.analysis_id && (
              <button className="download-button" onClick={() => handleIndividualDownload(candidate.analysis_id)}>
                <Download size={20} />
                <span>Download Report</span>
              </button>
            )}
            <button className="reset-button" onClick={navigateBack}>
              <ArrowLeft size={20} />
              <span>Back to Rankings</span>
            </button>
          </div>
        </div>
      </div>
    );
  };

  const renderCurrentView = () => {
    switch(currentView) {
      case 'single-results':
        return renderSingleResultsView();
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
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="logo-section" onClick={handleLeadsocClick} style={{ cursor: 'pointer' }}>
            <div className="logo-wrapper">
              <img 
                src={logoImage} 
                alt="Leadsoc Logo" 
                className="logo-image"
              />
            </div>
            <div className="brand-info">
              <h1 className="brand-name">AI Resume Analyzer (Groq)</h1>
              <p className="brand-tagline">
                Powered by Groq AI • Parallel Processing • 5-8 Skills Analysis
              </p>
            </div>
          </div>
          
          <button 
            className="quota-toggle"
            onClick={() => setShowQuotaPanel(!showQuotaPanel)}
          >
            <Activity size={20} />
            <span>System Status</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {showQuotaPanel && (
          <div className="quota-panel glass">
            <div className="panel-header">
              <h3>Groq System Status (3-Key Parallel)</h3>
              <button onClick={() => setShowQuotaPanel(false)} className="close-panel">
                <X size={20} />
              </button>
            </div>
            
            <div className="quota-summary">
              <div className="summary-item">
                <div className="summary-label">Backend</div>
                <div className="summary-value" style={{ color: backendStatus === 'ready' ? '#00ff9d' : '#ffd166' }}>
                  {backendStatus === 'ready' ? '🟢 Active' : '🟡 Waking'}
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Groq Status</div>
                <div className="summary-value" style={{ color: aiStatus === 'available' ? '#00ff9d' : '#ffd166' }}>
                  {aiStatus === 'available' ? '⚡ Ready' : aiStatus === 'warming' ? '🔥 Warming' : '⏳ Checking'}
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Available Keys</div>
                <div className="summary-value success">
                  🔑 {getAvailableKeysCount()}/3 active
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">AI Model</div>
                <div className="summary-value">
                  {getModelDisplayName(modelInfo)}
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Batch Capacity</div>
                <div className="summary-value success">
                  📊 Up to 10 resumes
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Skills Analysis</div>
                <div className="summary-value info">
                  ⚡ 5-8 skills each
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Performance</div>
                <div className="summary-value success">
                  🚀 ~10-15s for 10 resumes
                </div>
              </div>
            </div>
            
            <div className="key-distribution">
              <h4>Key Distribution Strategy</h4>
              <div className="distribution-grid">
                <div className="distribution-item">
                  <div className="distribution-key">🔑 Key 1</div>
                  <div className="distribution-resumes">Resumes: 1, 4, 7, 10</div>
                </div>
                <div className="distribution-item">
                  <div className="distribution-key">🔑 Key 2</div>
                  <div className="distribution-resumes">Resumes: 2, 5, 8</div>
                </div>
                <div className="distribution-item">
                  <div className="distribution-key">🔑 Key 3</div>
                  <div className="distribution-resumes">Resumes: 3, 6, 9</div>
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
                <div className="indicator-dot" style={{ background: '#00ff9d' }}></div>
                <span>Keys: {getAvailableKeysCount()}/3</span>
              </div>
              {modelInfo && (
                <div className="status-indicator active">
                  <div className="indicator-dot" style={{ background: '#00ff9d' }}></div>
                  <span>Model: {getModelDisplayName(modelInfo)}</span>
                </div>
              )}
              <div className="status-indicator active">
                <div className="indicator-dot" style={{ background: '#00ff9d' }}></div>
                <span>Skills: 5-8 each</span>
              </div>
              <div className="status-indicator active">
                <div className="indicator-dot" style={{ background: '#00ff9d' }}></div>
                <span>Mode: {currentView === 'single-results' ? 'Single' : 
                              currentView === 'batch-results' ? 'Batch' : 
                              currentView === 'candidate-detail' ? 'Details' : 
                              batchMode ? 'Batch' : 'Single'}</span>
              </div>
              {batchMode && (
                <div className="status-indicator active">
                  <div className="indicator-dot" style={{ background: '#ffd166' }}></div>
                  <span>Capacity: Up to 10 resumes</span>
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
                <span>Groq API is warming up. This ensures high-quality responses.</span>
              </div>
            )}
            
            {batchMode && getAvailableKeysCount() > 0 && (
              <div className="multi-key-message">
                <Zap size={16} />
                <span>Parallel mode: Processing {resumeFiles.length} resumes with {getAvailableKeysCount()} keys</span>
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
              <Brain size={20} />
              <span>AI Resume Analyzer (Groq)</span>
            </div>
            <p className="footer-tagline">
              Groq AI • 3-key parallel processing • 5-8 skills analysis • 4-5 sentence summaries
            </p>
          </div>
          
          <div className="footer-links">
            <div className="footer-section">
              <h4>Features</h4>
              <a href="#">Groq AI</a>
              <a href="#">5-8 Skills Analysis</a>
              <a href="#">4-5 Sentence Summaries</a>
              <a href="#">Parallel Processing</a>
            </div>
            <div className="footer-section">
              <h4>Service</h4>
              <a href="#">3-Key Parallel</a>
              <a href="#">Auto Warm-up</a>
              <a href="#">Health Checks</a>
              <a href="#">Status Monitor</a>
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
          <p>© 2024 AI Resume Analyzer. Built with React + Flask + Groq AI. 5-8 Skills Analysis Mode.</p>
          <div className="footer-stats">
            <span className="stat">
              <CloudLightning size={12} />
              Backend: {backendStatus === 'ready' ? 'Active' : 'Waking'}
            </span>
            <span className="stat">
              <Brain size={12} />
              Groq: {aiStatus === 'available' ? 'Ready ⚡' : 'Warming'}
            </span>
            <span className="stat">
              <Key size={12} />
              Keys: {getAvailableKeysCount()}/3
            </span>
            <span className="stat">
              <Cpu size={12} />
              Model: {modelInfo ? getModelDisplayName(modelInfo) : 'Loading...'}
            </span>
            {batchMode && (
              <span className="stat">
                <Activity size={12} />
                Batch: {resumeFiles.length} resumes
              </span>
            )}
            <span className="stat">
              <Target size={12} />
              Skills: 5-8 each
            </span>
            <span className="stat">
              <BookOpen size={12} />
              Summaries: 4-5 sentences
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
