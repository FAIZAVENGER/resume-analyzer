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
  EyeOff as EyeOffIcon, AlertTriangle as AlertTriangleIcon
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
    totalKeys: 3
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
    
    // Remove any trailing ellipsis or incomplete text
    let cleanText = text.trim();
    
    // If text ends with ellipsis or incomplete sentence, find the last complete sentence
    if (cleanText.includes('...') || !cleanText.endsWith('.') || cleanText.endsWith('..')) {
      // Split by sentences
      const sentences = cleanText.split(/[.!?]+/).filter(s => s.trim().length > 0);
      
      // Take only complete sentences (4-5 sentences)
      const completeSentences = sentences.slice(0, 5);
      
      // Join with periods and ensure proper ending
      cleanText = completeSentences.join('. ') + '.';
    }
    
    // Ensure proper sentence endings
    if (!cleanText.endsWith('.') && !cleanText.endsWith('!') && !cleanText.endsWith('?')) {
      cleanText = cleanText + '.';
    }
    
    return cleanText;
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
          <div className="section-title-container">
            <div className="section-title-icon">
              <Rocket size={28} />
            </div>
            <div>
              <h2>Start Your Analysis</h2>
              <p>Upload resume(s) and job description to get detailed insights</p>
              
              {/* Status Indicators */}
              <div className="status-indicators-container">
                <div className="status-indicator" style={{ 
                  backgroundColor: backendStatusInfo.bgColor,
                  color: backendStatusInfo.color,
                  borderColor: backendStatusInfo.color + '40'
                }}>
                  <div className="status-icon-wrapper">
                    {backendStatusInfo.icon}
                  </div>
                  <span className="status-text">{backendStatusInfo.text}</span>
                </div>
                
                <div className="status-indicator" style={{ 
                  backgroundColor: aiStatusInfo.bgColor,
                  color: aiStatusInfo.color,
                  borderColor: aiStatusInfo.color + '40'
                }}>
                  <div className="status-icon-wrapper">
                    {aiStatusInfo.icon}
                  </div>
                  <span className="status-text">{aiStatusInfo.text}</span>
                </div>
                
                <div className="status-indicator" style={{ 
                  backgroundColor: aiStatus === 'available' ? 'rgba(0, 255, 157, 0.1)' : 'rgba(255, 209, 102, 0.1)',
                  color: aiStatus === 'available' ? '#00ff9d' : '#ffd166',
                  borderColor: aiStatus === 'available' ? '#00ff9d40' : '#ffd16640'
                }}>
                  <div className="status-icon-wrapper">
                    <Key size={16} />
                  </div>
                  <span className="status-text">Keys: {getAvailableKeysCount()}/3</span>
                </div>
              </div>
            </div>
          </div>
          
          {/* Batch Mode Toggle */}
          <div className="mode-toggle-container">
            <button
              className={`mode-toggle ${!batchMode ? 'active' : ''}`}
              onClick={() => {
                setBatchMode(false);
                setResumeFiles([]);
              }}
            >
              <div className="mode-toggle-content">
                <User size={18} />
                <div className="mode-toggle-text">
                  <span className="mode-title">Single Resume</span>
                  <span className="mode-subtitle">Individual analysis</span>
                </div>
              </div>
              {!batchMode && (
                <div className="mode-active-indicator">
                  <Check size={16} />
                </div>
              )}
            </button>
            
            <button
              className={`mode-toggle ${batchMode ? 'active' : ''}`}
              onClick={() => {
                setBatchMode(true);
                setResumeFile(null);
              }}
            >
              <div className="mode-toggle-content">
                <Users size={18} />
                <div className="mode-toggle-text">
                  <span className="mode-title">Multiple Resumes</span>
                  <span className="mode-subtitle">Up to 10 files</span>
                </div>
              </div>
              {batchMode && (
                <div className="mode-active-indicator">
                  <Check size={16} />
                </div>
              )}
            </button>
          </div>
        </div>
        
        <div className="upload-grid">
          {/* Left Column - File Upload */}
          <div className="upload-card glass">
            <div className="upload-card-decoration"></div>
            <div className="card-header">
              <div className="header-icon-wrapper">
                <div className="icon-background" style={{ 
                  background: batchMode 
                    ? 'linear-gradient(135deg, #8b5cf6, #7c3aed)' 
                    : 'linear-gradient(135deg, #3b82f6, #1d4ed8)' 
                }}>
                  {batchMode ? <Users className="header-icon" /> : <FileText className="header-icon" />}
                </div>
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
                style={{
                  background: dragActive 
                    ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(29, 78, 216, 0.1))' 
                    : resumeFile 
                      ? 'linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(21, 128, 61, 0.05))' 
                      : 'linear-gradient(135deg, rgba(59, 130, 246, 0.05), rgba(29, 78, 216, 0.02))'
                }}
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
                        <div className="file-preview-icon">
                          <FileText size={40} />
                        </div>
                        <div className="file-preview-info">
                          <span className="file-name">{resumeFile.name}</span>
                          <span className="file-size">
                            {(resumeFile.size / 1024 / 1024).toFixed(2)} MB
                          </span>
                          <span className="file-type">
                            {resumeFile.type || 'Resume file'}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="upload-icon-circle">
                          <Upload className="upload-icon" />
                        </div>
                        <span className="upload-text">
                          Drag & drop or click to browse
                        </span>
                        <span className="upload-hint">Max file size: 15MB</span>
                        <div className="file-types-hint">
                          <span className="file-type-tag">PDF</span>
                          <span className="file-type-tag">DOC</span>
                          <span className="file-type-tag">DOCX</span>
                          <span className="file-type-tag">TXT</span>
                        </div>
                      </>
                    )}
                  </div>
                </label>
                
                {resumeFile && (
                  <button 
                    className="change-file-btn"
                    onClick={() => setResumeFile(null)}
                  >
                    <RefreshCw size={14} />
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
                style={{
                  background: dragActive 
                    ? 'linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(124, 58, 237, 0.1))' 
                    : resumeFiles.length > 0 
                      ? 'linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(21, 128, 61, 0.05))' 
                      : 'linear-gradient(135deg, rgba(139, 92, 246, 0.05), rgba(124, 58, 237, 0.02))'
                }}
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
                      <div className="batch-upload-preview">
                        <div className="batch-header">
                          <div className="batch-icon-circle">
                            <Users size={32} />
                          </div>
                          <div className="batch-info">
                            <span className="batch-count">{resumeFiles.length} resume(s) selected</span>
                            <span className="batch-size">
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
                        
                        {resumeFiles.length < 10 && (
                          <div className="add-more-files">
                            <Plus size={16} />
                            <span>Click to add more files (max 10)</span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <>
                        <div className="upload-icon-circle">
                          <Upload className="upload-icon" />
                        </div>
                        <span className="upload-text">
                          Drag & drop multiple files or click to browse
                        </span>
                        <span className="upload-hint">Max 10 files, 15MB each</span>
                        <div className="file-types-hint">
                          <span className="file-type-tag">PDF</span>
                          <span className="file-type-tag">DOC</span>
                          <span className="file-type-tag">DOCX</span>
                          <span className="file-type-tag">TXT</span>
                        </div>
                      </>
                    )}
                  </div>
                </label>
                
                {resumeFiles.length > 0 && (
                  <button 
                    className="change-file-btn"
                    onClick={clearBatchFiles}
                    style={{ background: 'linear-gradient(135deg, #ef4444, #dc2626)' }}
                  >
                    <Trash2 size={14} />
                    Clear All Files
                  </button>
                )}
              </div>
            )}
            
            <div className="upload-stats">
              <div className="stat" style={{ 
                background: aiStatus === 'available' 
                  ? 'linear-gradient(135deg, rgba(0, 255, 157, 0.1), rgba(0, 255, 157, 0.05))' 
                  : 'linear-gradient(135deg, rgba(255, 209, 102, 0.1), rgba(255, 209, 102, 0.05))'
              }}>
                <div className="stat-icon" style={{ 
                  color: aiStatus === 'available' ? '#00ff9d' : '#ffd166'
                }}>
                  <Brain size={16} />
                </div>
                <div className="stat-content">
                  <span className="stat-title">Groq AI analysis</span>
                  <span className="stat-subtitle">{getModelDisplayName(modelInfo)}</span>
                </div>
              </div>
              <div className="stat" style={{ 
                background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(29, 78, 216, 0.05))' 
              }}>
                <div className="stat-icon" style={{ color: '#3b82f6' }}>
                  <Activity size={16} />
                </div>
                <div className="stat-content">
                  <span className="stat-title">Rate Limit Protection</span>
                  <span className="stat-subtitle">Auto-retry system</span>
                </div>
              </div>
              <div className="stat" style={{ 
                background: batchMode 
                  ? 'linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(124, 58, 237, 0.05))' 
                  : 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(29, 78, 216, 0.05))'
              }}>
                <div className="stat-icon" style={{ 
                  color: batchMode ? '#8b5cf6' : '#3b82f6'
                }}>
                  <Users size={16} />
                </div>
                <div className="stat-content">
                  <span className="stat-title">
                    {batchMode ? 'Up to 10 resumes' : 'Single resume'}
                  </span>
                  <span className="stat-subtitle">
                    {batchMode ? 'Batch processing' : 'Individual analysis'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Job Description */}
          <div className="job-description-card glass">
            <div className="job-card-decoration"></div>
            <div className="card-header">
              <div className="header-icon-wrapper">
                <div className="icon-background" style={{ 
                  background: 'linear-gradient(135deg, #f59e0b, #d97706)' 
                }}>
                  <Briefcase className="header-icon" />
                </div>
              </div>
              <div>
                <h2>Job Description</h2>
                <p className="card-subtitle">Paste the complete job description</p>
              </div>
            </div>
            
            <div className="textarea-wrapper">
              <div className="textarea-header">
                <div className="textarea-header-stats">
                  <span className="stat-item">
                    <Target size={14} />
                    Required skills
                  </span>
                  <span className="stat-item">
                    <Award size={14} />
                    Qualifications
                  </span>
                  <span className="stat-item">
                    <ListOrdered size={14} />
                    Responsibilities
                  </span>
                </div>
              </div>
              
              <textarea
                className="job-description-input"
                placeholder={`• Paste job description here\n• Include required skills\n• Mention qualifications\n• List responsibilities\n• Add any specific requirements`}
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                rows={12}
              />
              
              <div className="textarea-footer">
                <div className="textarea-stats">
                  <span className="char-stat">
                    <Type size={14} />
                    {jobDescription.length} characters
                  </span>
                  <span className="word-stat">
                    <Hash size={14} />
                    {jobDescription.trim() ? jobDescription.trim().split(/\s+/).length : 0} words
                  </span>
                </div>
                
                {jobDescription.length > 500 && (
                  <div className="textarea-quality" style={{ 
                    background: jobDescription.length > 1000 
                      ? 'linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(21, 128, 61, 0.05))' 
                      : 'linear-gradient(135deg, rgba(251, 191, 36, 0.1), rgba(245, 158, 11, 0.05))',
                    color: jobDescription.length > 1000 ? '#22c55e' : '#fbbf24'
                  }}>
                    <CheckCircle size={14} />
                    <span>
                      {jobDescription.length > 1000 ? 'Excellent detail' : 'Good detail'}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="error-message glass">
            <div className="error-icon">
              <AlertCircle size={24} />
            </div>
            <div className="error-content">
              <span className="error-title">Analysis Error</span>
              <span className="error-text">{error}</span>
            </div>
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
                <div className="loading-icon">
                  <Loader className="spinner" size={28} />
                </div>
                <div className="loading-title">
                  <h3>{batchMode ? 'Batch Analysis' : 'Analysis in Progress'}</h3>
                  <p className="loading-subtitle">
                    {batchMode 
                      ? `Processing ${resumeFiles.length} resume(s) with Groq AI` 
                      : `Analyzing resume with ${getModelDisplayName(modelInfo)}`}
                  </p>
                </div>
              </div>
              
              <div className="progress-container">
                <div className="progress-bar" style={{ width: `${batchMode ? batchProgress : progress}%` }}></div>
              </div>
              
              <div className="loading-text">
                <span className="loading-message">{loadingMessage}</span>
                <span className="loading-percentage">
                  {Math.round(batchMode ? batchProgress : progress)}%
                </span>
              </div>
              
              <div className="progress-stats">
                <div className="progress-stat">
                  <span className="stat-label">Backend</span>
                  <span className="stat-value" style={{ 
                    color: backendStatus === 'ready' ? '#00ff9d' : '#ffd166'
                  }}>
                    {backendStatus === 'ready' ? 'Active' : 'Waking...'}
                  </span>
                </div>
                <div className="progress-stat">
                  <span className="stat-label">Groq AI</span>
                  <span className="stat-value" style={{ 
                    color: aiStatus === 'available' ? '#00ff9d' : '#ffd166'
                  }}>
                    {aiStatus === 'available' ? 'Ready ⚡' : 'Warming...'}
                  </span>
                </div>
                <div className="progress-stat">
                  <span className="stat-label">Keys</span>
                  <span className="stat-value" style={{ 
                    color: getAvailableKeysCount() === 3 ? '#00ff9d' : '#ffd166'
                  }}>
                    {getAvailableKeysCount()}/3
                  </span>
                </div>
                {modelInfo && (
                  <div className="progress-stat">
                    <span className="stat-label">Model</span>
                    <span className="stat-value">{getModelDisplayName(modelInfo)}</span>
                  </div>
                )}
                {batchMode && (
                  <div className="progress-stat">
                    <span className="stat-label">Batch Size</span>
                    <span className="stat-value">{resumeFiles.length}</span>
                  </div>
                )}
              </div>
              
              <div className="loading-note info">
                <Info size={16} />
                <span>Processing resumes with AI analysis. This may take a moment...</span>
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
                <div className="button-icon-wrapper">
                  <Brain size={24} />
                </div>
                <div className="button-text">
                  <span className="button-main-text">
                    {batchMode ? 'Analyze Multiple Resumes' : 'Analyze Resume'}
                  </span>
                  <span className="button-subtext">
                    {batchMode 
                      ? `${resumeFiles.length} resume(s) • Groq AI` 
                      : `${getModelDisplayName(modelInfo)} • Single`}
                  </span>
                </div>
              </div>
              <div className="button-arrow">
                <ChevronRight size={24} />
              </div>
            </>
          )}
        </button>

        <div className="tips-section">
          {batchMode ? (
            <>
              <div className="tip" style={{ 
                background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(124, 58, 237, 0.05))'
              }}>
                <Brain size={18} />
                <div className="tip-content">
                  <span className="tip-title">Batch AI Analysis</span>
                  <span className="tip-text">Groq AI with 128K context length for comprehensive batch analysis</span>
                </div>
              </div>
              <div className="tip" style={{ 
                background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(29, 78, 216, 0.05))'
              }}>
                <Users size={18} />
                <div className="tip-content">
                  <span className="tip-title">Parallel Processing</span>
                  <span className="tip-text">Analyze multiple resumes simultaneously for efficient screening</span>
                </div>
              </div>
              <div className="tip" style={{ 
                background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(21, 128, 61, 0.05))'
              }}>
                <Download size={18} />
                <div className="tip-content">
                  <span className="tip-title">Comprehensive Report</span>
                  <span className="tip-text">Download Excel report with candidate name & experience summary</span>
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="tip" style={{ 
                background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(29, 78, 216, 0.05))'
              }}>
                <Brain size={18} />
                <div className="tip-content">
                  <span className="tip-title">Groq AI Analysis</span>
                  <span className="tip-text">Ultra-fast resume analysis with detailed skill matching</span>
                </div>
              </div>
              <div className="tip" style={{ 
                background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(21, 128, 61, 0.05))'
              }}>
                <Activity size={18} />
                <div className="tip-content">
                  <span className="tip-title">Auto Keep-alive</span>
                  <span className="tip-text">Backend stays awake with automatic pings every 3 minutes</span>
                </div>
              </div>
              <div className="tip" style={{ 
                background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(217, 119, 6, 0.05))'
              }}>
                <Cpu size={18} />
                <div className="tip-content">
                  <span className="tip-title">Model Info</span>
                  <span className="tip-text">Using: {getModelDisplayName(modelInfo)}</span>
                </div>
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
              <h2>ResuGo Analysis Results</h2>
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
            <p>Key insights extracted from resume</p>
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
            <h2>ResuGo Batch Analysis Results</h2>
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
        <div className="stats-container glass">
          <div className="stat-card">
            <div className="stat-icon success">
              <Check size={24} />
            </div>
            <div className="stat-content">
              <div className="stat-value">{batchAnalysis?.successfully_analyzed || 0}</div>
              <div className="stat-label">Analyzed</div>
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
              <div className="stat-label">Total</div>
            </div>
          </div>
        </div>

        {/* Candidates Ranking */}
        <div className="section-title">
          <h2>Candidate Rankings</h2>
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
          ))}
        </div>

        {/* Action Buttons */}
        <div className="action-section glass">
          <div className="action-content">
            <h3>Batch Analysis Complete</h3>
            <p>Download comprehensive Excel report with candidate analysis including candidate name and experience summary</p>
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
            <p>Key insights extracted from resume</p>
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
              <p>Go back to rankings or download the full batch report</p>
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
                    <span className="tagline">Advanced AI Resume Analysis</span>
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
            
            {/* REMOVED: Status indicators from header */}
          </div>
          
        </header>

        <main className="main-content">
          {/* REMOVED: Status Panel */}
          {/* REMOVED: Status Banner */}

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
                Groq AI • Advanced AI Resume Analysis
              </p>
            </div>
            
            <div className="footer-links">
              <div className="footer-section">
                <h4>Features</h4>
                <a href="#">Groq AI</a>
                <a href="#">Skills Analysis</a>
                <a href="#">Experience Summary</a>
                <a href="#">Years of Experience</a>
              </div>
              <div className="footer-section">
                <h4>Service</h4>
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
            <p>© 2026 ResuGo. Built with React + Flask + Groq AI. Excel reports with candidate name & experience summary.</p>
            <div className="footer-stats">
              <span className="stat">
                <Brain size={12} />
                Groq AI Analysis
              </span>
              <span className="stat">
                <Target size={12} />
                Skills Analysis
              </span>
              <span className="stat">
                <Briefcase size={12} />
                Experience Summary
              </span>
              <span className="stat">
                <Calendar size={12} />
                Years of Experience
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
