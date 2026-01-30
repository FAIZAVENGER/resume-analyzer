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
  Meh, Laugh, Angry, surprised
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
      setResumeFiles(prev => [...prev, ...validFiles].slice(0, 10));
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
    setLoadingMessage('Starting analysis...');

    const formData = new FormData();
    formData.append('resume', resumeFile);
    formData.append('jobDescription', job_description);

    let progressInterval;

    try {
      progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 85) return 85;
          return prev + Math.random() * 5;
        });
      }, 500);

      if (aiStatus === 'available' && groqWarmup) {
        setLoadingMessage('Groq AI analysis...');
      } else {
        setLoadingMessage('Enhanced analysis (Warming up Groq)...');
      }
      setProgress(20);

      setLoadingMessage('Uploading and processing resume...');
      setProgress(30);

      const response = await axios.post(`${API_BASE_URL}/analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 60000,
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

      await new Promise(resolve => setTimeout(resolve, 500));
      
      setAnalysis(response.data);
      setProgress(100);
      navigateToSingleResults();

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
    
    resumeFiles.forEach((file, index) => {
      formData.append('resumes', file);
    });

    let progressInterval;

    try {
      progressInterval = setInterval(() => {
        setBatchProgress(prev => {
          if (prev >= 85) return 85;
          return prev + Math.random() * 2;
        });
      }, 500);

      setLoadingMessage('Uploading files for batch processing...');
      setBatchProgress(10);

      const response = await axios.post(`${API_BASE_URL}/analyze-batch`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000,
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
        setError('Groq API rate limit reached. Please try again later or reduce batch size.');
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
        icon: <Brain size={16} />,
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
        icon: <Brain size={16} />,
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

  // Format summary to max 5 lines
  const formatSummary = (text) => {
    if (!text) return "No summary available.";
    
    // Split into sentences
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
    
    // Take only 4-5 sentences
    const limitedSentences = sentences.slice(0, 5);
    
    // Join with periods and ensure proper ending
    let result = limitedSentences.join('. ') + '.';
    
    // If still too long, truncate
    if (result.length > 400) {
      result = result.substring(0, 397) + '...';
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
              <h2>{batchMode ? 'Upload Resumes (Batch)' : 'Upload Resume'}</h2>
              <p className="card-subtitle">
                {batchMode 
                  ? 'Upload multiple resumes (Max 10, 15MB each)' 
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
                      <span className="upload-hint">Max 10 files, 15MB each</span>
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
                <Brain size={14} />
              </div>
              <span>Groq AI analysis</span>
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
              <span>Parallel Processing</span>
            </div>
            <div className="stat">
              <div className="stat-icon">
                <Users size={14} />
              </div>
              <span>Up to 10 resumes</span>
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

      {(loading || batchLoading) && (
        <div className="loading-section glass">
          <div className="loading-container">
            <div className="loading-header">
              <Loader className="spinner" />
              <h3>{batchMode ? 'Batch Analysis' : 'Analysis in Progress'}</h3>
            </div>
            
            <div className="progress-container">
              <div className="progress-bar" style={{ width: `${batchMode ? batchProgress : progress}%` }}></div>
            </div>
            
            <div className="loading-text">
              <span className="loading-message">{loadingMessage}</span>
              <span className="loading-subtext">
                {batchMode 
                  ? `Processing ${resumeFiles.length} resume(s) with ${getAvailableKeysCount()} keys...` 
                  : `Using ${getModelDisplayName(modelInfo)}...`}
              </span>
            </div>
            
            <div className="progress-stats">
              <span>{Math.round(batchMode ? batchProgress : progress)}%</span>
              <span>•</span>
              <span>Backend: {backendStatus === 'ready' ? 'Active' : 'Waking...'}</span>
              <span>•</span>
              <span>Groq: {aiStatus === 'available' ? 'Ready ⚡' : 'Warming...'}</span>
              <span>•</span>
              <span>Keys: {getAvailableKeysCount()}/3</span>
              {modelInfo && (
                <>
                  <span>•</span>
                  <span>Model: {getModelDisplayName(modelInfo)}</span>
                </>
              )}
              {batchMode && (
                <>
                  <span>•</span>
                  <span>Batch Size: {resumeFiles.length}</span>
                </>
              )}
            </div>
            
            <div className="loading-note info">
              <Info size={14} />
              <span>Groq AI offers 128K context length for comprehensive resume analysis</span>
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
              <Brain size={20} />
              <div className="button-text">
                <span>{batchMode ? 'Analyze Multiple Resumes' : 'Analyze Resume'}</span>
                <span className="button-subtext">
                  {batchMode 
                    ? `${resumeFiles.length} resume(s) • ${getAvailableKeysCount()} keys • ~${Math.ceil(resumeFiles.length/3)}s` 
                    : `${getModelDisplayName(modelInfo)} • Single`}
                </span>
              </div>
            </div>
            <ChevronRight size={20} />
          </>
        )}
      </button>

      <div className="tips-section">
        {batchMode ? (
          <>
            <div className="tip">
              <Brain size={16} />
              <span>Groq AI with 128K context length for comprehensive analysis</span>
            </div>
            <div className="tip">
              <Activity size={16} />
              <span>Process up to 10 resumes in parallel with {getAvailableKeysCount()} API keys</span>
            </div>
            <div className="tip">
              <Zap size={16} />
              <span>~10-15 seconds for 10 resumes (Round-robin parallel processing)</span>
            </div>
            <div className="tip">
              <Download size={16} />
              <span>Download comprehensive Excel report with all candidate data</span>
            </div>
          </>
        ) : (
          <>
            <div className="tip">
              <Brain size={16} />
              <span>Groq AI offers ultra-fast resume analysis</span>
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
  );

  const renderSingleAnalysisView = () => {
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
            <h2>⚡ Resume Analysis Results (Groq)</h2>
            <p>{analysis.candidate_name}</p>
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
                  {new Date().toLocaleDateString('en-US', { 
                    weekday: 'long', 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric' 
                  })}
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
                Based on skill matching, experience relevance, and qualifications
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
                <Briefcase size={24} />
              </div>
              <h3>Experience Summary</h3>
            </div>
            <div className="summary-content">
              <p className="concise-summary" style={{ fontSize: '0.95rem', lineHeight: '1.5' }}>
                {formatSummary(analysis.experience_summary)}
              </p>
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
              <p className="concise-summary" style={{ fontSize: '0.95rem', lineHeight: '1.5' }}>
                {formatSummary(analysis.education_summary)}
              </p>
            </div>
          </div>
        </div>

        {/* Insights Section - Only 3 items each */}
        <div className="section-title">
          <h2>Insights & Recommendations (3 items each)</h2>
          <p>Key strengths and areas for improvement</p>
        </div>
        
        <div className="insights-grid">
          <div className="insight-card glass">
            <div className="insight-header">
              <div className="insight-icon success">
                <TrendingUp size={24} />
              </div>
              <div>
                <h3>Key Strengths (3)</h3>
                <p className="insight-subtitle">Areas where candidate excels</p>
              </div>
            </div>
            <div className="insight-content">
              <div className="strengths-list">
                {analysis.key_strengths?.slice(0, 3).map((strength, index) => (
                  <div key={index} className="strength-item">
                    <CheckCircle size={16} className="strength-icon" />
                    <span className="strength-text" style={{ fontSize: '0.9rem' }}>{strength}</span>
                  </div>
                ))}
                {(!analysis.key_strengths || analysis.key_strengths.length === 0) && (
                  <div className="no-items">No strengths identified</div>
                )}
              </div>
            </div>
          </div>

          <div className="insight-card glass">
            <div className="insight-header">
              <div className="insight-icon warning">
                <Target size={24} />
              </div>
              <div>
                <h3>Areas for Improvement (3)</h3>
                <p className="insight-subtitle">Opportunities to grow</p>
              </div>
            </div>
            <div className="insight-content">
              <div className="improvements-list">
                {analysis.areas_for_improvement?.slice(0, 3).map((area, index) => (
                  <div key={index} className="improvement-item">
                    <AlertCircle size={16} className="improvement-icon" />
                    <span className="improvement-text" style={{ fontSize: '0.9rem' }}>{area}</span>
                  </div>
                ))}
                {(!analysis.areas_for_improvement || analysis.areas_for_improvement.length === 0) && (
                  <div className="no-items success-text">No areas for improvement identified</div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Action Section */}
        <div className="action-section glass">
          <div className="action-content">
            <h3>Analysis Complete</h3>
            <p>Download the simplified Excel report or start a new analysis</p>
          </div>
          <div className="action-buttons">
            <button className="download-button" onClick={handleDownload}>
              <DownloadCloud size={20} />
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

  const renderBatchResultsView = () => (
    <div className="results-section">
      {/* Navigation Header */}
      <div className="navigation-header glass">
        <button onClick={navigateToMain} className="back-button">
          <ArrowLeft size={20} />
          <span>Back to Analysis</span>
        </button>
        <div className="navigation-title">
          <h2>⚡ Batch Analysis Results (Groq Parallel)</h2>
          <p>{batchAnalysis?.successfully_analyzed || 0} resumes analyzed</p>
        </div>
        <div className="navigation-actions">
          <button className="download-report-btn" onClick={handleBatchDownload}>
            <DownloadCloud size={18} />
            <span>Download Batch Report</span>
          </button>
        </div>
      </div>

      {/* Stats - SIMPLIFIED: Removed detailed stats as requested */}
      <div className="multi-key-stats-container glass">
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
          <div className="stat-icon success">
            <Zap size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{batchAnalysis?.available_keys || 0}</div>
            <div className="stat-label">Keys Used</div>
          </div>
        </div>
      </div>

      {/* Candidates Ranking */}
      <div className="section-title">
        <h2>Candidate Rankings (5-8 skills analysis each)</h2>
        <p>Sorted by ATS Score (Highest to Lowest)</p>
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
                  </div>
                </div>
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
          <p>Download simplified Excel report with candidate analysis</p>
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
                <Briefcase size={24} />
              </div>
              <h3>Experience Summary</h3>
            </div>
            <div className="summary-content">
              <p className="concise-summary" style={{ fontSize: '0.95rem', lineHeight: '1.5' }}>
                {formatSummary(candidate.experience_summary)}
              </p>
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
              <p className="concise-summary" style={{ fontSize: '0.95rem', lineHeight: '1.5' }}>
                {formatSummary(candidate.education_summary)}
              </p>
            </div>
          </div>
        </div>

        {/* Insights Section - Only 3 items each */}
        <div className="section-title">
          <h2>Insights & Recommendations (3 items each)</h2>
          <p>Key strengths and areas for improvement</p>
        </div>
        
        <div className="insights-grid">
          <div className="insight-card glass">
            <div className="insight-header">
              <div className="insight-icon success">
                <TrendingUp size={24} />
              </div>
              <div>
                <h3>Key Strengths (3)</h3>
                <p className="insight-subtitle">Areas where candidate excels</p>
              </div>
            </div>
            <div className="insight-content">
              <div className="strengths-list">
                {candidate.key_strengths?.slice(0, 3).map((strength, index) => (
                  <div key={index} className="strength-item">
                    <CheckCircle size={16} className="strength-icon" />
                    <span className="strength-text" style={{ fontSize: '0.9rem' }}>{strength}</span>
                  </div>
                ))}
                {(!candidate.key_strengths || candidate.key_strengths.length === 0) && (
                  <div className="no-items">No strengths identified</div>
                )}
              </div>
            </div>
          </div>

          <div className="insight-card glass">
            <div className="insight-header">
              <div className="insight-icon warning">
                <Target size={24} />
              </div>
              <div>
                <h3>Areas for Improvement (3)</h3>
                <p className="insight-subtitle">Opportunities to grow</p>
              </div>
            </div>
            <div className="insight-content">
              <div className="improvements-list">
                {candidate.areas_for_improvement?.slice(0, 3).map((area, index) => (
                  <div key={index} className="improvement-item">
                    <AlertCircle size={16} className="improvement-icon" />
                    <span className="improvement-text" style={{ fontSize: '0.9rem' }}>{area}</span>
                  </div>
                ))}
                {(!candidate.areas_for_improvement || candidate.areas_for_improvement.length === 0) && (
                  <div className="no-items success-text">No areas for improvement identified</div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Action Section */}
        <div className="action-section glass">
          <div className="action-content">
            <h3>Candidate Analysis Complete</h3>
            <p>Download individual report or go back to rankings</p>
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
            <button className="reset-button" onClick={navigateBack}>
              <ArrowLeft size={20} />
              <span>Back to Rankings</span>
            </button>
          </div>
        </div>
      </div>
    );
  };

  // Main render function
  const renderCurrentView = () => {
    switch (currentView) {
      case 'single-results':
        return renderSingleAnalysisView();
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
                <Brain className="logo-icon" />
              </div>
              <div className="logo-text">
                <h1>AI Resume Analyzer (Groq)</h1>
                <div className="logo-subtitle">
                  <span className="powered-by">Powered by</span>
                  <span className="groq-badge">⚡ Groq</span>
                  <span className="divider">•</span>
                  <span className="tagline">5-8 Skills Analysis • 4-5 Sentence Summaries</span>
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
            
            {/* Key Status */}
            <div className="feature key-status">
              <Key size={16} />
              <span>{getAvailableKeysCount()}/3 Keys</span>
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
                <span>{currentView === 'single-results' ? 'Single Analysis' : 
                       currentView === 'batch-results' ? 'Batch Results' : 
                       'Candidate Details'}</span>
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
                <h3>Groq Service Status</h3>
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
                <div className="summary-label">Available Keys</div>
                <div className={`summary-value ${getAvailableKeysCount() >= 2 ? 'success' : getAvailableKeysCount() === 1 ? 'warning' : 'error'}`}>
                  🔑 {getAvailableKeysCount()}/3 keys
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
