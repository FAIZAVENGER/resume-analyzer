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
  MessageSquare, Eye, EyeOff, Search, Settings,
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
  Meh, Laugh, Angry, Surprised,
  Users as UsersIcon,
  Cpu as CpuIcon,
  ZapOff,
  Server as ServerIcon,
  Network,
  GitPullRequest,
  Layers,
  PieChart,
  Activity as ActivityIcon,
  Target as TargetIcon
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
  
  // Multi-user states
  const [queueStatus, setQueueStatus] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [batchId, setBatchId] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [checkingQueue, setCheckingQueue] = useState(false);
  
  // View management for navigation
  const [currentView, setCurrentView] = useState('main');
  const [selectedCandidateIndex, setSelectedCandidateIndex] = useState(null);
  
  const API_BASE_URL = 'https://resume-analyzer-1-pevo.onrender.com';
  
  const keepAliveInterval = useRef(null);
  const backendWakeInterval = useRef(null);
  const warmupCheckInterval = useRef(null);
  const queueCheckInterval = useRef(null);

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
    setQueueStatus(null);
    setBatchId(null);
    setSessionId(null);
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
      if (queueCheckInterval.current) {
        clearInterval(queueCheckInterval.current);
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
        
        // Get system status for multi-user info
        checkSystemStatus();
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

  const checkSystemStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/system-status`, {
        timeout: 8000
      });
      
      if (response.data) {
        setSystemStatus(response.data);
        console.log('✅ System status updated');
      }
    } catch (error) {
      console.log('System status check failed:', error.message);
    }
  };

  const checkQueueStatus = async (batchIdToCheck) => {
    if (!batchIdToCheck) return;
    
    try {
      setCheckingQueue(true);
      const response = await axios.get(`${API_BASE_URL}/queue-status/${batchIdToCheck}`, {
        timeout: 8000
      });
      
      if (response.data) {
        setQueueStatus(response.data);
        
        // If batch is complete, navigate to results
        if (response.data.success && response.data.analyses) {
          setBatchAnalysis(response.data);
          setCurrentView('batch-results');
          setCheckingQueue(false);
          
          // Clear queue check interval
          if (queueCheckInterval.current) {
            clearInterval(queueCheckInterval.current);
          }
        }
      }
    } catch (error) {
      console.log('Queue status check failed:', error.message);
    } finally {
      setCheckingQueue(false);
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
    
    // Check system status every 2 minutes
    setInterval(() => {
      checkSystemStatus();
    }, 120000);
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
      setResumeFiles(prev => [...prev, ...validFiles].slice(0, 8)); // Max 8 resumes
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
    setQueueStatus(null);
    setBatchId(null);
    setSessionId(null);
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
    formData.append('jobDescription', jobDescription);

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
      await checkSystemStatus();

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
        setError('Rate limit reached. Please try again later or use batch mode with queue.');
      } else if (err.response?.data?.error?.includes('quota') || err.response?.data?.error?.includes('rate limit')) {
        setError('Rate limit exceeded. Please wait a minute and try again.');
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
      
      if (response.data.success) {
        setLoadingMessage('Batch submitted to queue! Checking status...');
        setBatchId(response.data.batch_id);
        setSessionId(response.data.session_id);
        setQueueStatus(response.data);
        
        // Start checking queue status
        if (queueCheckInterval.current) {
          clearInterval(queueCheckInterval.current);
        }
        
        queueCheckInterval.current = setInterval(() => {
          checkQueueStatus(response.data.batch_id);
        }, 10000); // Check every 10 seconds
        
        // Check immediately
        setTimeout(() => {
          checkQueueStatus(response.data.batch_id);
        }, 2000);
      } else {
        setError(response.data.error || 'Failed to submit batch to queue');
      }
      
      setBatchProgress(100);

    } catch (err) {
      if (progressInterval) clearInterval(progressInterval);
      
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Batch analysis timeout. The backend might be waking up. Please try again.');
        setBackendStatus('sleeping');
        wakeUpBackend();
      } else if (err.response?.status === 429) {
        setError('Rate limit reached. Please try again later or reduce batch size.');
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
      window.open(`${API_BASE_URL}/download-single/${analysisId}`, '_blank');
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

  // Format summary to show complete sentences
  const formatSummary = (text) => {
    if (!text) return "No summary available.";
    
    let cleanText = text.trim();
    
    if (cleanText.includes('...') || !cleanText.endsWith('.') || cleanText.endsWith('..')) {
      const sentences = cleanText.split(/[.!?]+/).filter(s => s.trim().length > 0);
      const completeSentences = sentences.slice(0, 5);
      cleanText = completeSentences.join('. ') + '.';
    }
    
    if (!cleanText.endsWith('.') && !cleanText.endsWith('!') && !cleanText.endsWith('?')) {
      cleanText = cleanText + '.';
    }
    
    return cleanText;
  };

  // Multi-user queue status rendering
  const renderQueueStatus = () => {
    if (!queueStatus || !batchId) return null;
    
    return (
      <div className="queue-status-container glass">
        <div className="queue-status-header">
          <Activity size={24} />
          <h3>Batch Queue Status</h3>
        </div>
        
        <div className="queue-status-content">
          <div className="queue-info-grid">
            <div className="queue-info-item">
              <span className="queue-label">Batch ID:</span>
              <span className="queue-value">{batchId}</span>
            </div>
            <div className="queue-info-item">
              <span className="queue-label">Session:</span>
              <span className="queue-value">{sessionId}</span>
            </div>
            <div className="queue-info-item">
              <span className="queue-label">Queue Position:</span>
              <span className="queue-value">#{queueStatus.queue_position || 'Unknown'}</span>
            </div>
            <div className="queue-info-item">
              <span className="queue-label">Estimated Wait:</span>
              <span className="queue-value">{queueStatus.estimated_wait_minutes || 'Unknown'} minutes</span>
            </div>
            {systemStatus && (
              <>
                <div className="queue-info-item">
                  <span className="queue-label">Active Users:</span>
                  <span className="queue-value">{systemStatus.queue_status?.active_users || 0}/{systemStatus.multi_user_capacity?.max_concurrent_users || 5}</span>
                </div>
                <div className="queue-info-item">
                  <span className="queue-label">Queue Size:</span>
                  <span className="queue-value">{systemStatus.queue_status?.queue_size || 0} batches</span>
                </div>
              </>
            )}
          </div>
          
          {checkingQueue ? (
            <div className="queue-checking">
              <Loader size={16} className="spinner" />
              <span>Checking queue status...</span>
            </div>
          ) : (
            <button 
              className="refresh-queue-btn"
              onClick={() => checkQueueStatus(batchId)}
            >
              <RefreshCw size={16} />
              Refresh Status
            </button>
          )}
          
          <div className="queue-note">
            <Info size={14} />
            <span>Your batch is being processed in the enhanced multi-user queue. Results will appear here automatically.</span>
          </div>
        </div>
      </div>
    );
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
            <UsersIcon size={14} /> Multi-User Ready
          </span>
          <span className="status-badge keys">
            <Key size={14} /> {getAvailableKeysCount()}/3 Keys
          </span>
          {modelInfo && (
            <span className="status-badge model">
              <CpuIcon size={14} /> {getModelDisplayName(modelInfo)}
            </span>
          )}
          {systemStatus && (
            <span className="status-badge capacity">
              <Users size={14} /> {systemStatus.queue_status?.active_users || 0}/5 Users
            </span>
          )}
        </div>
        
        {/* Multi-User Capacity Info */}
        {systemStatus && (
          <div className="multi-user-info glass" style={{
            background: 'rgba(0, 123, 255, 0.1)',
            border: '1px solid rgba(0, 123, 255, 0.3)',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            marginTop: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <Users size={16} color="#007bff" />
            <span style={{ fontSize: '0.9rem' }}>
              <strong>Enhanced Multi-User System:</strong> Supports 5 users simultaneously × 8 resumes each
            </span>
          </div>
        )}
        
        {/* Batch Mode Toggle */}
        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem', justifyContent: 'center' }}>
          <button
            className={`mode-toggle ${!batchMode ? 'active' : ''}`}
            onClick={() => {
              setBatchMode(false);
              setResumeFiles([]);
              setQueueStatus(null);
              setBatchId(null);
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
            <Users size={16} /> Multiple Resumes (Up to 8)
          </button>
        </div>
      </div>
      
      {/* Queue Status Display */}
      {queueStatus && renderQueueStatus()}
      
      <div className="upload-grid">
        {/* Left Column - File Upload */}
        <div className="upload-card glass">
          <div className="card-decoration"></div>
          <div className="card-header">
            <div className="header-icon-wrapper">
              {batchMode ? <Users className="header-icon" /> : <FileText className="header-icon" />}
            </div>
            <div>
              <h2>{batchMode ? 'Upload Resumes (Multi-User)' : 'Upload Resume'}</h2>
              <p className="card-subtitle">
                {batchMode 
                  ? 'Upload multiple resumes (Max 8 per user, 15MB each)' 
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
                      <span className="upload-hint">Max 8 files, 15MB each</span>
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
                <CpuIcon size={14} />
              </div>
              <span>{getModelDisplayName(modelInfo)}</span>
            </div>
            <div className="stat">
              <div className="stat-icon">
                <UsersIcon size={14} />
              </div>
              <span>Multi-User Ready</span>
            </div>
            <div className="stat">
              <div className="stat-icon">
                <ActivityIcon size={14} />
              </div>
              <span>Queue System</span>
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
              <h3>{batchMode ? 'Multi-User Batch Analysis' : 'Analysis in Progress'}</h3>
            </div>
            
            <div className="progress-container">
              <div className="progress-bar" style={{ width: `${batchMode ? batchProgress : progress}%` }}></div>
            </div>
            
            <div className="loading-text">
              <span className="loading-message">{loadingMessage}</span>
              <span className="loading-subtext">
                {batchMode 
                  ? `Processing ${resumeFiles.length} resume(s) with enhanced multi-user system...` 
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
              {batchMode && systemStatus && (
                <>
                  <span>•</span>
                  <span>Active Users: {systemStatus.queue_status?.active_users || 0}/5</span>
                  <span>•</span>
                  <span>Queue: {systemStatus.queue_status?.queue_size || 0} batches</span>
                </>
              )}
            </div>
            
            <div className="loading-note info">
              <Info size={14} />
              <span>Enhanced multi-user system ensures stable operation for 5 users simultaneously.</span>
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
                 backendStatus === 'sleeping' ||
                 (batchMode && queueStatus)}
      >
        {(loading || batchLoading) ? (
          <div className="button-loading-content">
            <Loader className="spinner" />
            <span>{batchMode ? 'Submitting to Queue...' : 'Analyzing...'}</span>
          </div>
        ) : backendStatus === 'sleeping' ? (
          <div className="button-waking-content">
            <Activity className="spinner" />
            <span>Waking Backend...</span>
          </div>
        ) : batchMode && queueStatus ? (
          <div className="button-queue-content">
            <ActivityIcon size={20} />
            <div className="button-text">
              <span>Already in Queue</span>
              <span className="button-subtext">
                Position: #{queueStatus.queue_position} • Check status above
              </span>
            </div>
          </div>
        ) : (
          <>
            <div className="button-content">
              <Brain size={20} />
              <div className="button-text">
                <span>{batchMode ? 'Analyze Multiple Resumes' : 'Analyze Resume'}</span>
                <span className="button-subtext">
                  {batchMode 
                    ? `${resumeFiles.length} resume(s) • Multi-User Queue • Enhanced System` 
                    : `${getModelDisplayName(modelInfo)} • Single • Immediate`}
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
              <UsersIcon size={16} />
              <span>Enhanced multi-user system supports 5 users simultaneously</span>
            </div>
            <div className="tip">
              <ActivityIcon size={16} />
              <span>Queue-based processing with automatic load balancing</span>
            </div>
            <div className="tip">
              <ShieldCheck size={16} />
              <span>Advanced rate limit protection with token tracking</span>
            </div>
            <div className="tip">
              <Download size={16} />
              <span>Download comprehensive Excel reports with candidate analysis</span>
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
              <span>Backend stays awake with automatic pings</span>
            </div>
            <div className="tip">
              <CpuIcon size={16} />
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
            <h2>⚡ Resume Analysis Results (Enhanced Multi-User)</h2>
            <p>{analysis.candidate_name}</p>
          </div>
          <div className="navigation-actions">
            <button className="download-report-btn" onClick={() => handleIndividualDownload(analysis.analysis_id)}>
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
                {analysis.years_of_experience && (
                  <span className="experience-badge">
                    <Calendar size={14} />
                    {analysis.years_of_experience} experience
                  </span>
                )}
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
                Powered by Enhanced Groq AI
              </p>
            </div>
          </div>
          <div className="recommendation-content">
            <p className="recommendation-text">{analysis.recommendation}</p>
            <div className="confidence-badge">
              <Brain size={16} />
              <span>Enhanced Multi-User Analysis</span>
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

        {/* Summary Section with Complete 4-5 sentences */}
        <div className="section-title">
          <h2>Profile Summary (4-5 complete sentences each)</h2>
          <p>Key insights extracted from resume (no truncation)</p>
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
              <p className="complete-summary" style={{ fontSize: '0.95rem', lineHeight: '1.5' }}>
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
              <p className="complete-summary" style={{ fontSize: '0.95rem', lineHeight: '1.5' }}>
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
            <p>Download the Excel report or start a new analysis</p>
          </div>
          <div className="action-buttons">
            <button className="download-button" onClick={() => handleIndividualDownload(analysis.analysis_id)}>
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
          <h2>⚡ Batch Analysis Results (Enhanced Multi-User)</h2>
          <p>{batchAnalysis?.successfully_analyzed || 0} resumes analyzed</p>
        </div>
        <div className="navigation-actions">
          <button className="download-report-btn" onClick={handleBatchDownload}>
            <DownloadCloud size={18} />
            <span>Download Batch Report</span>
          </button>
        </div>
      </div>

      {/* Multi-User System Info */}
      {batchAnalysis?.processing_method === 'enhanced_multi_user_parallel' && (
        <div className="multi-user-info-card glass" style={{
          background: 'rgba(0, 123, 255, 0.1)',
          border: '1px solid rgba(0, 123, 255, 0.3)',
          padding: '1rem',
          borderRadius: '12px',
          marginBottom: '1.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Users size={24} color="#007bff" />
            <div>
              <h4 style={{ margin: 0, color: '#007bff' }}>Enhanced Multi-User System Active</h4>
              <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.9rem', opacity: 0.9 }}>
                Parallel processing with load balancing • Session: {batchAnalysis.session_id} • 
                {batchAnalysis.user_capacity ? ` ${batchAnalysis.user_capacity}` : ''}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Stats */}
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
            <CpuIcon size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{getAvailableKeysCount()}</div>
            <div className="stat-label">Keys Active</div>
          </div>
        </div>
      </div>

      {/* System Status Info */}
      {systemStatus && (
        <div className="system-status-info glass" style={{ marginBottom: '1.5rem' }}>
          <h4>System Status</h4>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <div style={{
              padding: '0.75rem',
              background: 'rgba(0, 255, 157, 0.1)',
              borderRadius: '8px',
              flex: 1,
              minWidth: '150px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <Users size={16} color="#00ff9d" />
                <strong>Active Users</strong>
              </div>
              <div style={{ fontSize: '0.85rem' }}>
                <div>{systemStatus.queue_status?.active_users || 0}/{systemStatus.multi_user_capacity?.max_concurrent_users || 5}</div>
                <div>Capacity: {systemStatus.multi_user_capacity?.total_concurrent_capacity || 40} resumes</div>
              </div>
            </div>
            
            <div style={{
              padding: '0.75rem',
              background: 'rgba(255, 209, 102, 0.1)',
              borderRadius: '8px',
              flex: 1,
              minWidth: '150px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <ActivityIcon size={16} color="#ffd166" />
                <strong>Queue Status</strong>
              </div>
              <div style={{ fontSize: '0.85rem' }}>
                <div>Queue: {systemStatus.queue_status?.queue_size || 0} batches</div>
                <div>Processes: {systemStatus.queue_status?.concurrent_processes || 0}/{systemStatus.queue_status?.max_concurrent_processes || 20}</div>
              </div>
            </div>
            
            <div style={{
              padding: '0.75rem',
              background: 'rgba(0, 123, 255, 0.1)',
              borderRadius: '8px',
              flex: 1,
              minWidth: '150px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <ShieldCheck size={16} color="#007bff" />
                <strong>Rate Limits</strong>
              </div>
              <div style={{ fontSize: '0.85rem' }}>
                <div>Requests: {systemStatus.global_rate_limit?.requests_this_minute || 0}/{systemStatus.global_rate_limit?.max_requests_per_minute || 600}</div>
                <div>Tokens: {(systemStatus.global_rate_limit?.tokens_this_minute || 0).toLocaleString()}/{systemStatus.global_rate_limit?.max_tokens_per_minute?.toLocaleString() || '500k'}</div>
              </div>
            </div>
          </div>
        </div>
      )}

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
                    {candidate.years_of_experience && (
                      <span className="experience-info">
                        <Calendar size={12} />
                        {candidate.years_of_experience}
                      </span>
                    )}
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
              
              <div className="complete-summary-section">
                <h4>Experience Summary:</h4>
                <p className="complete-text" style={{ fontSize: '0.9rem', lineHeight: '1.4' }}>
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
              
              <div className="batch-card-actions">
                <button 
                  className="view-details-btn"
                  onClick={() => navigateToCandidateDetail(index)}
                >
                  <Eye size={16} />
                  View Details
                </button>
                <button 
                  className="download-individual-btn"
                  onClick={() => handleIndividualDownload(candidate.analysis_id)}
                >
                  <DownloadCloud size={16} />
                  Download Report
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Errors Section */}
      {batchAnalysis?.errors && batchAnalysis.errors.length > 0 && (
        <div className="errors-section glass">
          <div className="section-title">
            <AlertOctagon size={24} />
            <h2>Processing Errors</h2>
          </div>
          <div className="errors-list">
            {batchAnalysis.errors.map((error, index) => (
              <div key={index} className="error-item">
                <XCircle size={16} />
                <div className="error-details">
                  <span className="error-filename">{error.filename}</span>
                  <span className="error-message">{error.error}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Section */}
      <div className="action-section glass">
        <div className="action-content">
          <h3>Batch Analysis Complete</h3>
          <p>Download the comprehensive Excel report or start a new analysis</p>
        </div>
        <div className="action-buttons">
          <button className="download-button" onClick={handleBatchDownload}>
            <DownloadCloud size={20} />
            <span>Download Batch Report</span>
          </button>
          <button className="reset-button" onClick={navigateToMain}>
            <RefreshCw size={20} />
            <span>New Analysis</span>
          </button>
        </div>
      </div>
    </div>
  );

  const renderCandidateDetailView = () => {
    if (!batchAnalysis || selectedCandidateIndex === null) return null;
    
    const candidate = batchAnalysis.analyses[selectedCandidateIndex];
    
    return (
      <div className="results-section">
        {/* Navigation Header */}
        <div className="navigation-header glass">
          <button onClick={() => navigateBack()} className="back-button">
            <ArrowLeft size={20} />
            <span>Back to Batch</span>
          </button>
          <div className="navigation-title">
            <h2>⚡ Candidate Details - {candidate.candidate_name}</h2>
            <p>Rank #{candidate.rank} • Batch Session: {batchAnalysis.session_id}</p>
          </div>
          <div className="navigation-actions">
            <button className="download-report-btn" onClick={() => handleIndividualDownload(candidate.analysis_id)}>
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
              <h2 className="candidate-name">{candidate.candidate_name}</h2>
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
                {candidate.years_of_experience && (
                  <span className="experience-badge">
                    <Calendar size={14} />
                    {candidate.years_of_experience} experience
                  </span>
                )}
                <span className="rank-badge">
                  <AwardIcon size={14} />
                  Rank #{candidate.rank} of {batchAnalysis.analyses.length}
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
                Based on skill matching, experience relevance, and qualifications
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

        {/* Multi-User Context */}
        <div className="multi-user-context glass" style={{
          background: 'rgba(0, 123, 255, 0.1)',
          border: '1px solid rgba(0, 123, 255, 0.3)',
          padding: '1rem',
          borderRadius: '12px',
          marginBottom: '1.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <ActivityIcon size={20} color="#007bff" />
            <div>
              <h4 style={{ margin: 0, color: '#007bff' }}>Enhanced Multi-User Analysis</h4>
              <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.9rem', opacity: 0.9 }}>
                Processed in batch session: {batchAnalysis.session_id} • 
                Key used: {candidate.key_used || 'N/A'} • 
                Processing order: {candidate.processing_order || 'N/A'}
              </p>
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
                Powered by Enhanced Groq AI
              </p>
            </div>
          </div>
          <div className="recommendation-content">
            <p className="recommendation-text">{candidate.recommendation}</p>
            <div className="confidence-badge">
              <Brain size={16} />
              <span>Enhanced Multi-User Analysis</span>
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

        {/* Summary Section with Complete 4-5 sentences */}
        <div className="section-title">
          <h2>Profile Summary (4-5 complete sentences each)</h2>
          <p>Key insights extracted from resume (no truncation)</p>
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
              <p className="complete-summary" style={{ fontSize: '0.95rem', lineHeight: '1.5' }}>
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
              <p className="complete-summary" style={{ fontSize: '0.95rem', lineHeight: '1.5' }}>
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

        {/* Technical Details */}
        <div className="technical-details glass">
          <div className="section-title">
            <Settings size={20} />
            <h2>Technical Details</h2>
          </div>
          <div className="technical-grid">
            <div className="technical-item">
              <span className="technical-label">File Name:</span>
              <span className="technical-value">{candidate.filename}</span>
            </div>
            <div className="technical-item">
              <span className="technical-label">File Size:</span>
              <span className="technical-value">{candidate.file_size || 'N/A'}</span>
            </div>
            <div className="technical-item">
              <span className="technical-label">AI Provider:</span>
              <span className="technical-value">{candidate.ai_provider || 'Groq'}</span>
            </div>
            <div className="technical-item">
              <span className="technical-label">AI Model:</span>
              <span className="technical-value">{candidate.ai_model || modelInfo?.name || 'Groq'}</span>
            </div>
            <div className="technical-item">
              <span className="technical-label">Key Used:</span>
              <span className="technical-value">{candidate.key_used || 'N/A'}</span>
            </div>
            <div className="technical-item">
              <span className="technical-label">Processing Order:</span>
              <span className="technical-value">{candidate.processing_order || 'N/A'}</span>
            </div>
            {candidate.response_time && (
              <div className="technical-item">
                <span className="technical-label">Response Time:</span>
                <span className="technical-value">{candidate.response_time}</span>
              </div>
            )}
          </div>
        </div>

        {/* Action Section */}
        <div className="action-section glass">
          <div className="action-content">
            <h3>Candidate Analysis Complete</h3>
            <p>Download the individual report or return to batch view</p>
          </div>
          <div className="action-buttons">
            <button className="download-button" onClick={() => handleIndividualDownload(candidate.analysis_id)}>
              <DownloadCloud size={20} />
              <span>Download Individual Report</span>
            </button>
            <button className="back-button" onClick={() => navigateBack()}>
              <ArrowLeft size={20} />
              <span>Back to Batch</span>
            </button>
          </div>
        </div>
      </div>
    );
  };

  // Main render function
  return (
    <div className="app-container">
      {/* Header */}
      <header className="header glass">
        <div className="header-content">
          <div className="logo-section">
            <div className="logo" onClick={navigateToMain}>
              <img src={logoImage} alt="LeadSOC Logo" className="logo-image" />
              <div className="logo-text">
                <h1>LeadSOC Resume Analyzer</h1>
                <p className="tagline">Enhanced Multi-User AI Analysis</p>
              </div>
            </div>
          </div>
          
          <div className="header-actions">
            <div className="status-indicators">
              <div className="status-indicator" style={{ background: backendStatusInfo.bgColor, color: backendStatusInfo.color }}>
                {backendStatusInfo.icon}
                <span className="status-text">{backendStatusInfo.text}</span>
              </div>
              <div className="status-indicator" style={{ background: aiStatusInfo.bgColor, color: aiStatusInfo.color }}>
                {aiStatusInfo.icon}
                <span className="status-text">{aiStatusInfo.text}</span>
              </div>
              <div className="status-indicator" style={{ background: 'rgba(0, 123, 255, 0.1)', color: '#007bff' }}>
                <UsersIcon size={14} />
                <span className="status-text">
                  {systemStatus ? `${systemStatus.queue_status?.active_users || 0}/5 Users` : 'Multi-User'}
                </span>
              </div>
            </div>
            
            <button 
              className={`warmup-btn ${isWarmingUp ? 'warming' : ''}`}
              onClick={handleForceWarmup}
              disabled={isWarmingUp}
            >
              {isWarmingUp ? (
                <Loader size={16} className="spinner" />
              ) : (
                <Thermometer size={16} />
              )}
              <span>{isWarmingUp ? 'Warming...' : 'Warm Up'}</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {currentView === 'main' && renderMainView()}
        {currentView === 'single-results' && renderSingleAnalysisView()}
        {currentView === 'batch-results' && renderBatchResultsView()}
        {currentView === 'candidate-detail' && renderCandidateDetailView()}
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <div className="footer-section">
            <div className="footer-logo">
              <img src={logoImage} alt="LeadSOC Logo" className="footer-logo-image" />
              <span className="footer-logo-text">LeadSOC</span>
            </div>
            <p className="footer-description">
              Enhanced multi-user resume analyzer powered by Groq AI. 
              Supports 5 users simultaneously with 8 resumes each.
            </p>
          </div>
          
          <div className="footer-section">
            <h4>Features</h4>
            <ul>
              <li>5-8 skills analysis per candidate</li>
              <li>Complete sentence summaries</li>
              <li>Enhanced multi-user queue</li>
              <li>Excel report downloads</li>
              <li>Session-based processing</li>
            </ul>
          </div>
          
          <div className="footer-section">
            <h4>System Info</h4>
            <div className="system-info">
              <div className="info-item">
                <CpuIcon size={14} />
                <span>{getModelDisplayName(modelInfo)}</span>
              </div>
              <div className="info-item">
                <UsersIcon size={14} />
                <span>{systemStatus ? `${systemStatus.queue_status?.active_users || 0}/5 Active Users` : 'Multi-User Ready'}</span>
              </div>
              <div className="info-item">
                <Key size={14} />
                <span>{getAvailableKeysCount()}/3 API Keys</span>
              </div>
              <div className="info-item">
                <ActivityIcon size={14} />
                <span>{systemStatus?.queue_status?.queue_size || 0} in Queue</span>
              </div>
            </div>
          </div>
          
          <div className="footer-section">
            <h4>Powered By</h4>
            <div className="powered-by">
              <div className="tech-badge">
                <Brain size={14} />
                <span>Groq AI</span>
              </div>
              <div className="tech-badge">
                <CpuIcon size={14} />
                <span>Llama 3.3 70B</span>
              </div>
              <div className="tech-badge">
                <UsersIcon size={14} />
                <span>Multi-User System</span>
              </div>
              <div className="tech-badge">
                <ShieldCheck size={14} />
                <span>Enhanced Rate Limiting</span>
              </div>
            </div>
          </div>
        </div>
        
        <div className="footer-bottom">
          <p>
            © {new Date().getFullYear()} LeadSOC Resume Analyzer (Enhanced Multi-User Edition) • 
            Supports {MAX_CONCURRENT_USERS} users × {MAX_RESUMES_PER_USER} resumes simultaneously
          </p>
          <p className="footer-note">
            This system uses enhanced multi-user processing with parallel execution and load balancing.
          </p>
        </div>
      </footer>
    </div>
  );
}

// Constants for multi-user configuration (matching app.py)
const MAX_CONCURRENT_USERS = 5;
const MAX_RESUMES_PER_USER = 8;

export default App;
