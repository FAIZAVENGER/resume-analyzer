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
  LogIn, KeyRound, Fingerprint, UserCog,
  MailCheck, LockKeyhole, Eye as EyeIcon,
  EyeOff as EyeOffIcon, AlertTriangle as AlertTriangleIcon,
  Target as TargetIcon, TrendingUp as TrendingUpIcon,
  BarChart as BarChartIcon
} from 'lucide-react';
import './App.css';
import logoImage from './leadsoc.png';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showLogin, setShowLogin] = useState(true);
  const [loginForm, setLoginForm] = useState({
    email: '',
    password: '',
    rememberMe: false
  });
  const [loginError, setLoginError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  
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
  const [backendStatus, setBackendStatus] = useState('ready');
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
    totalKeys: 5
  });
  
  // View management for navigation
  const [currentView, setCurrentView] = useState('main');
  const [selectedCandidateIndex, setSelectedCandidateIndex] = useState(null);
  
  const API_BASE_URL = 'https://resume-analyzer-1-pevo.onrender.com';
  
  const keepAliveInterval = useRef(null);
  const backendWakeInterval = useRef(null);
  const warmupCheckInterval = useRef(null);

  // Check for saved login on mount
  useEffect(() => {
    const savedLogin = localStorage.getItem('resugo_login');
    if (savedLogin) {
      try {
        const { email, rememberMe } = JSON.parse(savedLogin);
        if (rememberMe) {
          setIsLoggedIn(true);
          setShowLogin(false);
          initializeService();
        }
      } catch (err) {
        localStorage.removeItem('resugo_login');
      }
    }
  }, []);

  const handleLogin = (e) => {
    e.preventDefault();
    setLoginError('');
    setIsLoggingIn(true);
    
    // Simulate API call delay
    setTimeout(() => {
      if (loginForm.email === 'resugo@gmail.com' && loginForm.password === 'ResuGo#') {
        setIsLoggedIn(true);
        setShowLogin(false);
        
        // Save login if remember me is checked
        if (loginForm.rememberMe) {
          localStorage.setItem('resugo_login', JSON.stringify({
            email: loginForm.email,
            rememberMe: true
          }));
        }
        
        initializeService();
      } else {
        setLoginError('Invalid email or password. Please try again.');
        // Shake animation effect
        const loginFormElement = document.querySelector('.login-card');
        if (loginFormElement) {
          loginFormElement.classList.add('shake');
          setTimeout(() => {
            loginFormElement.classList.remove('shake');
          }, 500);
        }
      }
      setIsLoggingIn(false);
    }, 1500);
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setShowLogin(true);
    localStorage.removeItem('resugo_login');
    setLoginForm({
      email: '',
      password: '',
      rememberMe: false
    });
  };

  const handleForgotPassword = () => {
    setLoginError('Please contact administrator to reset your password.');
  };

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
  const initializeService = async () => {
    try {
      setIsWarmingUp(true);
      setBackendStatus('ready');
      setAiStatus('checking');
      
      // Immediately start health check without waiting
      checkBackendHealth();
      
      // Start periodic checks
      setupPeriodicChecks();
      
    } catch (err) {
      console.log('Service initialization error:', err.message);
      // Even if error, set backend as ready (will recover)
      setBackendStatus('ready');
      
      setTimeout(() => checkBackendHealth(), 3000);
    } finally {
      setIsWarmingUp(false);
    }
  };

  const wakeUpBackend = async () => {
    try {
      console.log('🔔 Ensuring backend is active...');
      setLoadingMessage('Ensuring backend is active...');
      
      // Try multiple endpoints
      const pingPromises = [
        axios.get(`${API_BASE_URL}/ping`, { timeout: 5000 }),
        axios.get(`${API_BASE_URL}/health`, { timeout: 8000 }),
        axios.get(`${API_BASE_URL}/quick-check`, { timeout: 8000 })
      ];
      
      await Promise.any(pingPromises);
      
      console.log('✅ Backend is responding');
      setBackendStatus('ready');
      setLoadingMessage('');
      
    } catch (error) {
      console.log('⚠️ Backend check failed, but service will continue...');
      setBackendStatus('ready');
      
      // Schedule another check
      setTimeout(() => {
        checkBackendHealth();
      }, 5000);
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
          setModelInfo({ name: response.data.model });
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

  // FIXED: Updated checkBackendHealth to properly count configured keys
  const checkBackendHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`, {
        timeout: 8000
      });
      
      setBackendStatus('ready');
      setGroqWarmup(response.data.ai_warmup_complete || false);
      
      // Extract model info properly
      if (response.data.model) {
        setModelInfo({ name: response.data.model });
      }
      
      if (response.data.ai_warmup_complete) {
        setAiStatus('available');
      } else {
        setAiStatus('warming');
      }
      
      // FIXED: Count configured keys properly from key_status array
      let configuredKeys = 0;
      if (response.data.key_status && Array.isArray(response.data.key_status)) {
        configuredKeys = response.data.key_status.filter(k => k.configured === true).length;
      } else {
        // Fallback to available_keys if key_status is not available
        configuredKeys = response.data.available_keys || 0;
      }
      
      // Update service status with correct key count
      setServiceStatus({
        enhancedFallback: response.data.ai_provider_configured || false,
        validKeys: configuredKeys,
        totalKeys: 5
      });
      
      console.log(`✅ Backend health check: ${configuredKeys}/5 keys configured`);
      
    } catch (error) {
      console.log('Backend health check failed:', error.message);
      setBackendStatus('ready');
      
      // Try again in 10 seconds
      setTimeout(() => checkBackendHealth(), 10000);
    }
  };

  const setupPeriodicChecks = () => {
    // Keep-alive ping every 2 minutes (increased frequency)
    backendWakeInterval.current = setInterval(() => {
      axios.get(`${API_BASE_URL}/ping`, { timeout: 5000 })
        .then(() => console.log('Keep-alive ping successful'))
        .catch(() => console.log('Keep-alive ping failed, but service continues'));
    }, 2 * 60 * 1000);
    
    // Health check every 30 seconds (increased frequency)
    warmupCheckInterval.current = setInterval(() => {
      checkBackendHealth();
    }, 30 * 1000);
    
    // Groq status check every minute if needed
    const statusCheckInterval = setInterval(() => {
      if (aiStatus === 'warming' || aiStatus === 'checking') {
        checkGroqStatus();
      }
    }, 60000);
    
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
      setResumeFiles(prev => [...prev, ...validFiles].slice(0, 10)); // Updated from 6 to 10
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
        setLoadingMessage('Groq AI analysis with granular scoring...');
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
        setError('Request timeout. Trying to reconnect...');
        setTimeout(() => checkBackendHealth(), 2000);
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

  // FIXED: Updated handleBatchAnalyze to handle large batches better
  const handleBatchAnalyze = async () => {
    if (resumeFiles.length === 0) {
      setError('Please upload at least one resume file');
      return;
    }
    if (!jobDescription.trim()) {
      setError('Please enter a job description');
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
          if (prev >= 90) return 90; // FIXED: Increased max to 90%
          return prev + Math.random() * 1.5;
        });
      }, 500);

      setLoadingMessage('Uploading files for batch processing...');
      setBatchProgress(10);

      const response = await axios.post(`${API_BASE_URL}/analyze-batch`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes timeout for large batches
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

      // Check for configured keys in response
      if (response.data.available_keys !== undefined) {
        setServiceStatus(prev => ({
          ...prev,
          validKeys: response.data.available_keys
        }));
      }

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
        setError('Batch analysis timeout. This may take longer for 10 resumes. Please try again with fewer files.');
        setTimeout(() => checkBackendHealth(), 2000);
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
      window.open(`${API_BASE_URL}/download-single/${analysisId}`, '_blank');
    } else {
      setError('No individual report available for download.');
    }
  };

  // FIXED: Updated getAvailableKeysCount to properly count configured keys
  const getAvailableKeysCount = () => {
    // First check from batch analysis if available
    if (batchAnalysis?.available_keys !== undefined) {
      return batchAnalysis.available_keys;
    }
    // Then check from service status
    if (serviceStatus.validKeys !== undefined) {
      return serviceStatus.validKeys;
    }
    // Then check from key_status in batch analysis if available
    if (batchAnalysis?.key_statistics) {
      const configured = batchAnalysis.key_statistics.filter(k => k.configured === true).length;
      return configured;
    }
    return 0;
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#00ff9d';
    if (score >= 60) return '#ffd166';
    return '#ff6b6b';
  };

  const getScoreGrade = (score) => {
    if (score >= 90) return 'Exceptional Match 🎯';
    if (score >= 80) return 'Very Good Match ✨';
    if (score >= 70) return 'Good Match 👍';
    if (score >= 60) return 'Fair Match 📊';
    return 'Needs Improvement 📈';
  };

  const getBackendStatusMessage = () => {
    return { 
      text: 'Backend Active', 
      color: '#00ff9d', 
      icon: <CloudLightning size={16} />,
      bgColor: 'rgba(0, 255, 157, 0.1)'
    };
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

  // Format score display with 1 decimal place
  const formatScore = (score) => {
    if (typeof score === 'number') {
      return score.toFixed(1);
    }
    return score || '0.0';
  };

  // Render Login Page
  const renderLoginPage = () => (
    <div className="login-container">
      {/* Animated Background */}
      <div className="login-bg">
        <div className="bg-particle"></div>
        <div className="bg-particle"></div>
        <div className="bg-particle"></div>
        <div className="bg-particle"></div>
        <div className="bg-particle"></div>
        <div className="bg-gradient"></div>
      </div>

      {/* Login Card */}
      <div className="login-card glass">
        <div className="login-card-decoration"></div>
        
        {/* Login Header */}
        <div className="login-header">
          <div className="login-logo">
            <div className="logo-glow-login">
              <Brain className="logo-icon" size={32} />
            </div>
            <div className="login-logo-text">
              <h1>ResuGo</h1>
              <p className="login-subtitle">
                <span className="groq-badge-login">⚡ Groq AI</span>
                <span className="divider">•</span>
                <span>Enterprise Access</span>
              </p>
            </div>
          </div>
          <p className="login-welcome">Welcome back! Please sign in to your account.</p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleLogin} className="login-form">
          <div className="input-group">
            <label htmlFor="email">
              <Mail size={18} />
              <span>Email Address</span>
            </label>
            <div className="input-wrapper">
              <input
                type="email"
                id="email"
                value={loginForm.email}
                onChange={(e) => setLoginForm({...loginForm, email: e.target.value})}
                placeholder="Enter your email"
                required
                className="login-input"
                autoComplete="username"
              />
              <div className="input-icon">
                <MailCheck size={20} />
              </div>
            </div>
          </div>

          <div className="input-group">
            <label htmlFor="password">
              <LockKeyhole size={18} />
              <span>Password</span>
            </label>
            <div className="input-wrapper">
              <input
                type={showPassword ? "text" : "password"}
                id="password"
                value={loginForm.password}
                onChange={(e) => setLoginForm({...loginForm, password: e.target.value})}
                placeholder="Enter your password"
                required
                className="login-input"
                autoComplete="current-password"
              />
              <div className="input-icon">
                <KeyRound size={20} />
              </div>
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOffIcon size={20} /> : <EyeIcon size={20} />}
              </button>
            </div>
          </div>

          <div className="login-options">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={loginForm.rememberMe}
                onChange={(e) => setLoginForm({...loginForm, rememberMe: e.target.checked})}
                className="checkbox-input"
              />
              <span className="checkbox-custom"></span>
              <span>Remember me</span>
            </label>
            <button
              type="button"
              className="forgot-password"
              onClick={handleForgotPassword}
            >
              Forgot password?
            </button>
          </div>

          {loginError && (
            <div className="login-error">
              <AlertTriangleIcon size={18} />
              <span>{loginError}</span>
            </div>
          )}

          <button
            type="submit"
            className="login-button"
            disabled={isLoggingIn}
          >
            {isLoggingIn ? (
              <>
                <Loader size={20} className="spinner" />
                <span>Signing in...</span>
              </>
            ) : (
              <>
                <LogIn size={20} />
                <span>Sign In to Dashboard</span>
              </>
            )}
          </button>

          <div className="login-divider">
            <span>Secure Access</span>
          </div>

          <div className="login-features">
            <div className="feature-item">
              <ShieldCheck size={16} />
              <span>Enterprise Security</span>
            </div>
            <div className="feature-item">
              <Brain size={16} />
              <span>Groq AI Powered</span>
            </div>
            <div className="feature-item">
              <Users size={16} />
              <span>Team Ready</span>
            </div>
            <div className="feature-item">
              <BarChart size={16} />
              <span>Advanced Analytics</span>
            </div>
          </div>

          {/* Demo Credentials */}
        </form>

        <div className="login-footer">
          <p>By signing in, you agree to our Terms of Service and Privacy Policy</p>
          <div className="security-info">
            <Shield size={14} />
            <span>Your data is encrypted and secure</span>
          </div>
        </div>
      </div>

      {/* Login Side Info */}
      <div className="login-side-info">
        <div className="side-info-content">
          <h2>Why ResuGo?</h2>
          <div className="benefits-list">
            <div className="benefit">
              <div className="benefit-icon">
                <Zap size={24} />
              </div>
              <div className="benefit-content">
                <h3>Lightning Fast Analysis</h3>
                <p>Powered by Groq's ultra-fast inference engine</p>
              </div>
            </div>
            <div className="benefit">
              <div className="benefit-icon">
                <Brain size={24} />
              </div>
              <div className="benefit-content">
                <h3>Advanced AI Insights</h3>
                <p>Comprehensive resume analysis with detailed skill matching</p>
              </div>
            </div>
            <div className="benefit">
              <div className="benefit-icon">
                <Users size={24} />
              </div>
              <div className="benefit-content">
                <h3>Batch Processing</h3>
                <p>Analyze multiple resumes simultaneously</p>
              </div>
            </div>
            <div className="benefit">
              <div className="benefit-icon">
                <BarChart3 size={24} />
              </div>
              <div className="benefit-content">
                <h3>Detailed Reports</h3>
                <p>Download comprehensive Excel reports with insights</p>
              </div>
            </div>
          </div>
          
          <div className="tech-stack">
            <span className="tech-label">Powered by:</span>
            <div className="tech-icons">
              <span className="tech-icon">⚡ Groq</span>
              <span className="tech-icon">🤖 AI</span>
              <span className="tech-icon">🔐 Secure</span>
              <span className="tech-icon">📊 Analytics</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // Render Main App if logged in
  const renderMainApp = () => {
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
              <ZapIcon size={14} /> Rate Limit Protection
            </span>
            <span className="status-badge keys">
              <Key size={14} /> {getAvailableKeysCount()}/5 Keys
            </span>
            {modelInfo && (
              <span className="status-badge model">
                <Cpu size={14} /> {getModelDisplayName(modelInfo)}
              </span>
            )}
            <span className="status-badge scoring">
              <TargetIcon size={14} /> Granular Scoring
            </span>
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
              <Users size={16} /> Multiple Resumes (Up to 10) {/* Updated from 6 to 10 */}
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
                <h2>{batchMode ? 'Upload Resumes' : 'Upload Resume'}</h2>
                <p className="card-subtitle">
                  {batchMode 
                    ? 'Upload multiple resumes (Max 10, 15MB each)' // Updated from 6 to 10
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
                        <span className="upload-hint">Max 10 files, 15MB each</span> {/* Updated from 6 to 10 */}
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
                <span>Rate Limit Protection</span>
              </div>
              <div className="stat">
                <div className="stat-icon">
                  <TargetIcon size={14} />
                </div>
                <span>Granular Scoring</span>
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
                onClick={checkBackendHealth}
              >
                <Activity size={16} />
                Refresh Status
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
                    ? `Processing ${resumeFiles.length} resume(s) with rate limit protection...` 
                    : `Using ${getModelDisplayName(modelInfo)} with granular scoring...`}
                </span>
              </div>
              
              <div className="progress-stats">
                <span>{Math.round(batchMode ? batchProgress : progress)}%</span>
                <span>•</span>
                <span>Backend: Always Active</span>
                <span>•</span>
                <span>Groq: {aiStatus === 'available' ? 'Ready ⚡' : 'Warming...'}</span>
                <span>•</span>
                <span>Keys: {getAvailableKeysCount()}/5</span>
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
                    <span>•</span>
                    <span>Rate Protection: Active</span>
                    <span>•</span>
                    <span>Max: 10 resumes</span> {/* Updated from 6 to 10 */}
                    <span>•</span>
                    <span>Scoring: Granular unique</span>
                  </>
                )}
              </div>
              
              <div className="loading-note info">
                <Info size={14} />
                <span>Rate limit protection ensures stable operation. Backend is always active.</span>
              </div>
            </div>
          </div>
        )}

        <button
          className="analyze-button"
          onClick={batchMode ? handleBatchAnalyze : handleAnalyze}
          disabled={loading || batchLoading || 
                   (batchMode ? resumeFiles.length === 0 : !resumeFile) || 
                   !jobDescription.trim()}
        >
          {(loading || batchLoading) ? (
            <div className="button-loading-content">
              <Loader className="spinner" />
              <span>{batchMode ? 'Analyzing Batch...' : 'Analyzing...'}</span>
            </div>
          ) : (
            <>
              <div className="button-content">
                <Brain size={20} />
                <div className="button-text">
                  <span>{batchMode ? 'Analyze Multiple Resumes' : 'Analyze Resume'}</span>
                  <span className="button-subtext">
                    {batchMode 
                      ? `${resumeFiles.length} resume(s) • Granular Scoring` 
                      : `${getModelDisplayName(modelInfo)} • Granular Scoring`}
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
                <span>Groq AI with enhanced granular scoring for precise analysis</span>
              </div>
              <div className="tip">
                <Activity size={16} />
                <span>Rate limit protection with staggered delays prevents API limits</span>
              </div>
              <div className="tip">
                <TargetIcon size={16} />
                <span>Unique granular scores for each candidate (e.g., 82.5, 76.3)</span>
              </div>
              <div className="tip">
                <Download size={16} />
                <span>Download comprehensive Excel report with candidate name & experience summary</span>
              </div>
            </>
          ) : (
            <>
              <div className="tip">
                <Brain size={16} />
                <span>Groq AI offers ultra-fast resume analysis with granular scoring</span>
              </div>
              <div className="tip">
                <TargetIcon size={16} />
                <span>Precise scoring: 1 decimal place, weighted factors, unique scores</span>
              </div>
              <div className="tip">
                <Activity size={16} />
                <span>Backend is always active with self-pinging</span>
              </div>
              <div className="tip">
                <Cpu size={16} />
                <span>Using: {getModelDisplayName(modelInfo)} with enhanced scoring</span>
              </div>
            </>
          )}
        </div>
      </div>
    );

    const renderSingleAnalysisView = () => {
      if (!analysis) return null;

      const score = analysis.overall_score || 0;
      const formattedScore = formatScore(score);

      return (
        <div className="results-section">
          {/* Navigation Header */}
          <div className="navigation-header glass">
            <button onClick={navigateToMain} className="back-button">
              <ArrowLeft size={20} />
              <span>New Analysis</span>
            </button>
            <div className="navigation-title">
              <h2>⚡ Resume Analysis Results</h2>
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
                  background: `radial-gradient(circle, ${getScoreColor(score)}22 0%, transparent 70%)` 
                }}></div>
                <div 
                  className="score-circle" 
                  style={{ 
                    borderColor: getScoreColor(score),
                    background: `conic-gradient(${getScoreColor(score)} ${score * 3.6}deg, #2d3749 0deg)` 
                  }}
                >
                  <div className="score-inner">
                    <div className="score-value" style={{ color: getScoreColor(score) }}>
                      {formattedScore}
                    </div>
                    <div className="score-label">ATS Score</div>
                  </div>
                </div>
              </div>
              <div className="score-info">
                <h3 className="score-grade">{getScoreGrade(score)}</h3>
                <p className="score-description">
                  Granular scoring with 1 decimal precision
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
                  <span className="meta-item">
                    <TargetIcon size={12} />
                    Score: {formattedScore}/100
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Recommendation Card */}
          <div className="recommendation-card glass" style={{
            background: `linear-gradient(135deg, ${getScoreColor(score)}15, ${getScoreColor(score)}08)`,
            borderLeft: `4px solid ${getScoreColor(score)}`
          }}>
            <div className="recommendation-header">
              <AwardIcon size={28} style={{ color: getScoreColor(score) }} />
              <div>
                <h3>Analysis Recommendation</h3>
                <p className="recommendation-subtitle">
                  Powered by Groq AI with granular scoring
                </p>
              </div>
            </div>
            <div className="recommendation-content">
              <p className="recommendation-text">{analysis.recommendation}</p>
              <div className="confidence-badge">
                <TargetIcon size={16} />
                <span>Granular Score: {formattedScore}/100</span>
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
            <h2>Profile Summary</h2>
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

          {/* Insights Section */}
          <div className="section-title">
            <h2>Insights & Recommendations</h2>
            <p>Key strengths and areas for improvement</p>
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
                  <h3>Areas for Improvement</h3>
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
              <p>Download the Excel report with granular scores or start a new analysis</p>
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
            <h2>⚡ Batch Analysis Results</h2>
            <p>{batchAnalysis?.successfully_analyzed || 0} resumes analyzed</p>
          </div>
          <div className="navigation-actions">
            <button className="download-report-btn" onClick={handleBatchDownload}>
              <DownloadCloud size={18} />
              <span>Download Batch Report</span>
            </button>
          </div>
        </div>

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
          
          {/* Scoring Stats */}
          {batchAnalysis?.scoring_quality && (
            <div className="stat-card">
              <div className="stat-icon scoring">
                <TargetIcon size={24} />
              </div>
              <div className="stat-content">
                <div className="stat-value">
                  {batchAnalysis.scoring_quality.unique_scores || 0}/{batchAnalysis.scoring_quality.total_candidates || 0}
                </div>
                <div className="stat-label">Unique Scores</div>
              </div>
            </div>
          )}
        </div>

        {/* Candidates Ranking */}
        <div className="section-title">
          <h2>Candidate Rankings</h2>
          <p>Sorted by ATS Score (Highest to Lowest) - Granular Scoring</p>
        </div>
        
        <div className="batch-results-grid">
          {batchAnalysis?.analyses?.map((candidate, index) => {
            const score = candidate.overall_score || 0;
            const formattedScore = formatScore(score);
            
            return (
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
                    <div className="score-large" style={{ color: getScoreColor(score) }}>
                      {formattedScore}
                    </div>
                    <div className="score-label">ATS Score</div>
                  </div>
                </div>
                
                <div className="batch-card-content">
                  <div className="recommendation-badge" style={{ 
                    background: getScoreColor(score) + '20',
                    color: getScoreColor(score),
                    border: `1px solid ${getScoreColor(score)}40`
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
                </div>
                
                <div className="batch-card-footer">
                  <button 
                    className="view-details-btn"
                    onClick={() => navigateToCandidateDetail(index)}
                  >
                    View Full Details
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Action Buttons */}
        <div className="action-section glass">
          <div className="action-content">
            <h3>Batch Analysis Complete</h3>
            <p>Download comprehensive Excel report with granular scoring and unique candidate analysis</p>
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

      const score = candidate.overall_score || 0;
      const formattedScore = formatScore(score);

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
                  {candidate.years_of_experience && (
                    <span className="experience-badge">
                      <Calendar size={14} />
                      {candidate.years_of_experience} experience
                    </span>
                  )}
                </div>
              </div>
            </div>
            
            <div className="score-display">
              <div className="score-circle-wrapper">
                <div className="score-circle-glow" style={{ 
                  background: `radial-gradient(circle, ${getScoreColor(score)}22 0%, transparent 70%)` 
                }}></div>
                <div 
                  className="score-circle" 
                  style={{ 
                    borderColor: getScoreColor(score),
                    background: `conic-gradient(${getScoreColor(score)} ${score * 3.6}deg, #2d3749 0deg)` 
                  }}
                >
                  <div className="score-inner">
                    <div className="score-value" style={{ color: getScoreColor(score) }}>
                      {formattedScore}
                    </div>
                    <div className="score-label">ATS Score</div>
                  </div>
                </div>
              </div>
              <div className="score-info">
                <h3 className="score-grade">{getScoreGrade(score)}</h3>
                <p className="score-description">
                  Granular scoring with 1 decimal precision
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
            background: `linear-gradient(135deg, ${getScoreColor(score)}15, ${getScoreColor(score)}08)`,
            borderLeft: `4px solid ${getScoreColor(score)}`
          }}>
            <div className="recommendation-header">
              <AwardIcon size={28} style={{ color: getScoreColor(score) }} />
              <div>
                <h3>Analysis Recommendation</h3>
                <p className="recommendation-subtitle">
                  Powered by Groq AI with granular scoring
                </p>
              </div>
            </div>
            <div className="recommendation-content">
              <p className="recommendation-text">{candidate.recommendation}</p>
              <div className="confidence-badge">
                <TargetIcon size={16} />
                <span>Granular Score: {formattedScore}/100</span>
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
            <h2>Profile Summary</h2>
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

          {/* Insights Section */}
          <div className="section-title">
            <h2>Insights & Recommendations</h2>
            <p>Key strengths and areas for improvement</p>
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
                  <h3>Areas for Improvement</h3>
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
              <p>Granular score: {formattedScore}/100 • Go back to rankings</p>
            </div>
            <div className="action-buttons">
              <button className="download-button" onClick={navigateBack}>
                <ArrowLeft size={20} />
                <span>Back to Rankings</span>
              </button>
            </div>
          </div>
        </div>
      );
    };

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
      <>
        <header className="header">
          <div className="header-content">
            <div className="header-main">
              {/* Logo and Title */}
              <div className="logo">
                <div className="logo-glow">
                  <Brain className="logo-icon" />
                </div>
                <div className="logo-text">
                  <h1>ResuGo</h1>
                  <div className="logo-subtitle">
                    <span className="powered-by">Powered by</span>
                    <span className="groq-badge">⚡ Groq</span>
                    <span className="divider">•</span>
                    <span className="tagline">Granular Scoring • Experience Summary • Years of Experience</span>
                  </div>
                </div>
              </div>
              
              {/* User Profile and Logout */}
              <div className="user-profile">
                <div className="user-info">
                  <div className="user-avatar">
                    <UserCog size={20} />
                  </div>
                  <div className="user-details">
                    <span className="user-name">ResuGo User</span>
                    <span className="user-email">{loginForm.email || 'resugo@gmail.com'}</span>
                  </div>
                </div>
                <button onClick={handleLogout} className="logout-btn">
                  <LogOut size={18} />
                  <span>Logout</span>
                </button>
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
              {/* Backend Status - Always Active */}
              <div 
                className="feature backend-status-indicator" 
                style={{ 
                  backgroundColor: backendStatusInfo.bgColor,
                  borderColor: `${backendStatusInfo.color}30`,
                  color: backendStatusInfo.color
                }}
              >
                {backendStatusInfo.icon}
                <span>Always Active</span>
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
              
              {/* Key Status - FIXED: Now shows correct count */}
              <div className="feature key-status">
                <Key size={16} />
                <span>{getAvailableKeysCount()}/5 Keys</span>
              </div>
              
              {/* Model Info */}
              {modelInfo && (
                <div className="feature model-info">
                  <Cpu size={16} />
                  <span>{getModelDisplayName(modelInfo)}</span>
                </div>
              )}
              
              {/* Rate Limit Protection */}
              <div className="feature rate-limit">
                <ShieldCheck size={16} />
                <span>Rate Protection</span>
              </div>
              
              {/* Scoring Feature */}
              <div className="feature scoring-feature">
                <TargetIcon size={16} />
                <span>Granular Scoring</span>
              </div>
              
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
          
        </header>

        <main className="main-content">
          {/* Status Panel */}
          {showQuotaPanel && (
            <div className="quota-status-panel glass">
              <div className="quota-panel-header">
                <div className="quota-title">
                  <Activity size={20} />
                  <h3>Groq Service Status (Rate Limit Protection)</h3>
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
                  <div className="summary-value success">
                    ✅ Always Active (No Sleeping)
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
                  <div className={`summary-value ${getAvailableKeysCount() >= 3 ? 'success' : getAvailableKeysCount() >= 2 ? 'warning' : 'error'}`}>
                    🔑 {getAvailableKeysCount()}/5 keys
                  </div>
                </div>
                <div className="summary-item">
                  <div className="summary-label">AI Model</div>
                  <div className="summary-value">
                    {getModelDisplayName(modelInfo)}
                  </div>
                </div>
                <div className="summary-item">
                  <div className="summary-label">Scoring Method</div>
                  <div className="summary-value success">
                    🎯 Granular unique scores (1 decimal)
                  </div>
                </div>
                <div className="summary-item">
                  <div className="summary-label">Rate Limit Protection</div>
                  <div className="summary-value success">
                    🛡️ ACTIVE (Max 100/min/key)
                  </div>
                </div>
                <div className="summary-item">
                  <div className="summary-label">Max Batch Size</div>
                  <div className="summary-value warning">
                    📁 10 resumes (Reduced from 20) {/* Updated from 6 to 10 */}
                  </div>
                </div>
                <div className="summary-item">
                  <div className="summary-label">Processing Method</div>
                  <div className="summary-value info">
                    ⏳ Sequential with delays
                  </div>
                </div>
                <div className="summary-item">
                  <div className="summary-label">Concurrent Users</div>
                  <div className="summary-value success">
                    👥 Multiple users supported
                  </div>
                </div>
              </div>
              
              <div className="scoring-explanation">
                <h4>🎯 Enhanced Granular Scoring:</h4>
                <ul>
                  <li>✅ Scores like 82.5, 76.3, 88.7 (NOT just multiples of 5)</li>
                  <li>✅ Unique scores for each candidate (no duplicates)</li>
                  <li>✅ 1 decimal place precision</li>
                  <li>✅ Weighted scoring: Skills (40%), Experience (30%), Education (20%), Years (10%)</li>
                  <li>✅ Deterministic variations based on resume content</li>
                  <li>✅ Ensures meaningful differentiation between candidates</li>
                </ul>
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
                <div className="status-indicator active">
                  <div className="indicator-dot" style={{ background: '#00ff9d' }}></div>
                  <span>Backend: Always Active</span>
                </div>
                <div className={`status-indicator ${aiStatus === 'available' ? 'active' : 'inactive'}`}>
                  <div className="indicator-dot"></div>
                  <span>Groq: {aiStatus === 'available' ? 'Ready ⚡' : aiStatus === 'warming' ? 'Warming...' : 'Enhanced'}</span>
                </div>
                <div className="status-indicator active">
                  <div className="indicator-dot" style={{ background: '#00ff9d' }}></div>
                  <span>Keys: {getAvailableKeysCount()}/5</span>
                </div>
                {modelInfo && (
                  <div className="status-indicator active">
                    <div className="indicator-dot" style={{ background: '#00ff9d' }}></div>
                    <span>Model: {getModelDisplayName(modelInfo)}</span>
                  </div>
                )}
                <div className="status-indicator active">
                  <div className="indicator-dot" style={{ background: '#00ff9d' }}></div>
                  <span>Excel: Name & Experience columns</span>
                </div>
                <div className="status-indicator active">
                  <div className="indicator-dot" style={{ background: '#ffd166' }}></div>
                  <span>Scoring: Granular unique</span>
                </div>
                <div className="status-indicator active">
                  <div className="indicator-dot" style={{ background: '#ffd166' }}></div>
                  <span>Rate Protection: ACTIVE</span>
                </div>
                <div className="status-indicator active">
                  <div className="indicator-dot" style={{ background: '#ffd166' }}></div>
                  <span>Mode: {currentView === 'single-results' ? 'Single' : 
                                currentView === 'batch-results' ? 'Batch' : 
                                currentView === 'candidate-detail' ? 'Details' : 
                                batchMode ? 'Batch' : 'Single'}</span>
                </div>
              </div>
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
                <span>ResuGo</span>
              </div>
              <p className="footer-tagline">
                Groq AI • 5-key with rate protection • Granular scoring • Experience summary • Years of experience
              </p>
            </div>
            
            <div className="footer-links">
              <div className="footer-section">
                <h4>Features</h4>
                <a href="#">Groq AI</a>
                <a href="#">Granular Scoring</a>
                <a href="#">Experience Summary</a>
                <a href="#">Years of Experience</a>
              </div>
              <div className="footer-section">
                <h4>Service</h4>
                <a href="#">Rate Limit Protection</a>
                <a href="#">5-Key Sequential</a>
                <a href="#">Excel Reports</a>
                <a href="#">Candidate Comparison</a>
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
            <p>© 2024 ResuGo. Built with React + Flask + Groq AI. Excel reports with candidate name & experience summary.</p>
            <div className="footer-stats">
              <span className="stat">
                <CloudLightning size={12} />
                Backend: Always Active
              </span>
              <span className="stat">
                <Brain size={12} />
                Groq: {aiStatus === 'available' ? 'Ready ⚡' : 'Warming'}
              </span>
              <span className="stat">
                <Key size={12} />
                Keys: {getAvailableKeysCount()}/5
              </span>
              <span className="stat">
                <Cpu size={12} />
                Model: {modelInfo ? getModelDisplayName(modelInfo) : 'Loading...'}
              </span>
              <span className="stat">
                <TargetIcon size={12} />
                Scoring: Granular unique
              </span>
              {batchMode && (
                <span className="stat">
                  <Activity size={12} />
                  Batch: {resumeFiles.length} resumes (Max 10) {/* Updated from 6 to 10 */}
                </span>
              )}
              <span className="stat">
                <BarChartIcon size={12} />
                Scores: 1 decimal precision
              </span>
              <span className="stat">
                <Briefcase size={12} />
                Experience: Summary included
              </span>
              <span className="stat">
                <Calendar size={12} />
                Years: Analysis included
              </span>
              <span className="stat">
                <Users size={12} />
                Multiple Users: Supported
              </span>
            </div>
          </div>
        </footer>
      </>
    );
  };

  return (
    <div className="app">
      {/* Animated Background Elements */}
      <div className="bg-grid"></div>
      <div className="bg-blur-1"></div>
      <div className="bg-blur-2"></div>
      
      {!isLoggedIn ? renderLoginPage() : renderMainApp()}
    </div>
  );
}

export default App;
