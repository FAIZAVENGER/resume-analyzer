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
  const [deepseekWarmup, setDeepseekWarmup] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  const [quotaInfo, setQuotaInfo] = useState(null);
  const [showQuotaPanel, setShowQuotaPanel] = useState(false);
  const [batchMode, setBatchMode] = useState(false);
  const [modelInfo, setModelInfo] = useState(null);
  const [serviceStatus, setServiceStatus] = useState({
    enhancedATS: true,
    validKeys: 0,
    totalKeys: 0
  });
  
  // View management for navigation
  const [currentView, setCurrentView] = useState('main'); // 'main', 'single-results', 'batch-results', 'candidate-detail'
  const [selectedCandidateIndex, setSelectedCandidateIndex] = useState(null);
  const [expandedATSBreakdown, setExpandedATSBreakdown] = useState(false);
  
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
        setServiceStatus({
          enhancedATS: healthResponse.data.features?.includes('enhanced_ats_scoring') || false,
          validKeys: healthResponse.data.ai_provider_configured ? 1 : 0,
          totalKeys: healthResponse.data.ai_provider_configured ? 1 : 0
        });
        
        setDeepseekWarmup(healthResponse.data.ai_warmup_complete || false);
        setModelInfo(healthResponse.data.model_info || { name: healthResponse.data.model });
        setBackendStatus('ready');
      }
      
      await forceDeepseekWarmup();
      
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

  const forceDeepseekWarmup = async () => {
    try {
      setAiStatus('warming');
      setLoadingMessage('Warming up DeepSeek API...');
      
      const response = await axios.get(`${API_BASE_URL}/warmup`, {
        timeout: 15000
      });
      
      if (response.data.warmup_complete) {
        setAiStatus('available');
        setDeepseekWarmup(true);
        console.log('✅ DeepSeek API warmed up successfully');
      } else {
        setAiStatus('warming');
        console.log('⚠️ DeepSeek API still warming up');
        
        setTimeout(() => checkDeepseekStatus(), 5000);
      }
      
      setLoadingMessage('');
      
    } catch (error) {
      console.log('⚠️ DeepSeek API warm-up failed:', error.message);
      setAiStatus('unavailable');
      
      setTimeout(() => checkDeepseekStatus(), 3000);
    }
  };

  const checkDeepseekStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/quick-check`, {
        timeout: 10000
      });
      
      if (response.data.available) {
        setAiStatus('available');
        setDeepseekWarmup(true);
        if (response.data.model) {
          setModelInfo(response.data.model_info || { name: response.data.model });
        }
      } else if (response.data.warmup_complete) {
        setAiStatus('available');
        setDeepseekWarmup(true);
      } else {
        setAiStatus('warming');
        setDeepseekWarmup(false);
      }
      
    } catch (error) {
      console.log('DeepSeek API status check failed:', error.message);
      setAiStatus('unavailable');
    }
  };

  const checkBackendHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`, {
        timeout: 8000
      });
      
      setBackendStatus('ready');
      setDeepseekWarmup(response.data.ai_warmup_complete || false);
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
        checkDeepseekStatus();
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
      // Allow up to 10 files
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
    setLoadingMessage('Starting enhanced ATS analysis...');

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

      if (aiStatus === 'available' && deepseekWarmup) {
        setLoadingMessage('Enhanced ATS analysis in progress...');
      } else {
        setLoadingMessage('Enhanced ATS analysis (Warming up DeepSeek)...');
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
      
      setLoadingMessage('Enhanced ATS analysis complete!');

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
        setError('Rate limit reached. DeepSeek API has limits. Please try again later.');
      } else if (err.response?.data?.error?.includes('quota') || err.response?.data?.error?.includes('rate limit')) {
        setError('DeepSeek API rate limit exceeded. Please wait a minute and try again.');
        setAiStatus('unavailable');
      } else {
        setError(err.response?.data?.error || 'An error occurred during enhanced ATS analysis. Please try again.');
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
    setLoadingMessage(`Starting enhanced ATS batch analysis of ${resumeFiles.length} resumes...`);

    const formData = new FormData();
    formData.append('jobDescription', job_description);
    
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

      setLoadingMessage('Uploading files for enhanced ATS batch processing...');
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
      setLoadingMessage('Enhanced ATS batch analysis complete!');

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
        setError('DeepSeek API rate limit reached. Please try again later or reduce batch size.');
      } else {
        setError(err.response?.data?.error || 'An error occurred during enhanced ATS batch analysis.');
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
      setError('No enhanced ATS analysis report available for download.');
    }
  };

  const handleBatchDownload = () => {
    if (batchAnalysis?.batch_excel_filename) {
      window.open(`${API_BASE_URL}/download/${batchAnalysis.batch_excel_filename}`, '_blank');
    } else {
      setError('No enhanced ATS batch analysis report available for download.');
    }
  };

  const handleIndividualDownload = (analysisId) => {
    if (analysisId) {
      window.open(`${API_BASE_URL}/download-individual/${analysisId}`, '_blank');
    } else {
      setError('No individual enhanced ATS report available for download.');
    }
  };

  const getScoreColor = (score) => {
    if (score >= 85) return '#00ff9d';
    if (score >= 75) return '#80ff80';
    if (score >= 65) return '#ffd166';
    if (score >= 55) return '#ff9d6d';
    return '#ff6b6b';
  };

  const getScoreGrade = (score) => {
    if (score >= 85) return 'Exceptional Match 🎯';
    if (score >= 75) return 'Strong Match ✨';
    if (score >= 65) return 'Good Match 👍';
    if (score >= 55) return 'Fair Match 📊';
    if (score >= 45) return 'Basic Match ⚠️';
    return 'Needs Improvement 📈';
  };

  const getDomainColor = (domain) => {
    switch(domain) {
      case 'VLSI': return '#ff6b6b';
      case 'CS/Software': return '#4ECDC4';
      default: return '#94a3b8';
    }
  };

  const getDomainIcon = (domain) => {
    switch(domain) {
      case 'VLSI': return <Cpu size={16} />;
      case 'CS/Software': return <Code size={16} />;
      default: return <Cpu size={16} />;
    }
  };

  const getSeniorityColor = (seniority) => {
    const seniorityLower = seniority?.toLowerCase() || '';
    if (seniorityLower.includes('senior') || seniorityLower.includes('lead')) return '#ff6b6b';
    if (seniorityLower.includes('mid') || seniorityLower.includes('intermediate')) return '#ffd166';
    if (seniorityLower.includes('junior') || seniorityLower.includes('entry')) return '#4ECDC4';
    return '#94a3b8';
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
        text: 'Checking DeepSeek...', 
        color: '#ffd166', 
        icon: <Brain size={16} />,
        bgColor: 'rgba(255, 209, 102, 0.1)'
      };
      case 'warming': return { 
        text: 'DeepSeek Warming', 
        color: '#ff9800', 
        icon: <Thermometer size={16} />,
        bgColor: 'rgba(255, 152, 0, 0.1)'
      };
      case 'available': return { 
        text: 'DeepSeek Ready 🧠', 
        color: '#00ff9d', 
        icon: <Brain size={16} />,
        bgColor: 'rgba(0, 255, 157, 0.1)'
      };
      case 'unavailable': return { 
        text: 'Enhanced ATS Mode', 
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
    setLoadingMessage('Forcing DeepSeek API warm-up...');
    
    try {
      await forceDeepseekWarmup();
      setLoadingMessage('');
    } catch (error) {
      console.log('Force warm-up failed:', error);
    } finally {
      setIsWarmingUp(false);
    }
  };

  const getModelDisplayName = (modelInfo) => {
    if (!modelInfo) return 'DeepSeek AI';
    if (typeof modelInfo === 'string') return modelInfo;
    return modelInfo.name || 'DeepSeek AI';
  };

  const getModelDescription = (modelInfo) => {
    if (!modelInfo || typeof modelInfo === 'string') return 'Enhanced ATS Scoring';
    return modelInfo.description || 'Enhanced ATS Scoring';
  };

  const renderATSBreakdown = (analysis) => {
    const breakdown = analysis?.ats_score_breakdown || analysis?.score_breakdown;
    if (!breakdown) return null;

    const categories = [
      { key: 'skills_match', name: 'Skills Match', max: 30, description: 'Required skills with evidence' },
      { key: 'experience_relevance', name: 'Experience Relevance', max: 25, description: 'Relevant years and domain expertise' },
      { key: 'role_alignment', name: 'Role Alignment', max: 20, description: 'Past roles vs target role match' },
      { key: 'projects_impact', name: 'Projects Impact', max: 15, description: 'Hands-on projects and outcomes' },
      { key: 'resume_quality', name: 'Resume Quality', max: 10, description: 'Structure, clarity, formatting' }
    ];

    return (
      <div className="ats-breakdown-container glass">
        <div className="ats-breakdown-header">
          <div className="breakdown-title">
            <BarChart4 size={24} />
            <h3>Enhanced ATS Score Breakdown</h3>
          </div>
          <button 
            className="expand-breakdown-btn"
            onClick={() => setExpandedATSBreakdown(!expandedATSBreakdown)}
          >
            {expandedATSBreakdown ? <Minus size={18} /> : <Plus size={18} />}
            <span>{expandedATSBreakdown ? 'Collapse' : 'Expand'}</span>
          </button>
        </div>
        
        <div className="ats-breakdown-grid">
          {categories.map((category) => {
            const catData = breakdown[category.key];
            if (!catData) return null;
            
            const score = catData.score || 0;
            const percentage = (score / category.max) * 100;
            const explanation = catData.explanation || '';
            
            return (
              <div key={category.key} className="ats-category-card">
                <div className="category-header">
                  <div className="category-name">
                    <h4>{category.name}</h4>
                    <span className="category-weight">Weight: {category.max}/100</span>
                  </div>
                  <div className="category-score" style={{ color: getScoreColor(score * (100/category.max)) }}>
                    {score.toFixed(1)}/{category.max}
                  </div>
                </div>
                
                <div className="category-progress">
                  <div 
                    className="progress-bar-fill"
                    style={{ 
                      width: `${percentage}%`,
                      background: getScoreColor(score * (100/category.max))
                    }}
                  ></div>
                </div>
                
                <div className="category-description">
                  <span className="description-text">{category.description}</span>
                  <div className="category-percentage" style={{ color: getScoreColor(score * (100/category.max)) }}>
                    {percentage.toFixed(0)}%
                  </div>
                </div>
                
                {expandedATSBreakdown && explanation && (
                  <div className="category-explanation">
                    <p>{explanation}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
        
        <div className="ats-total-score">
          <div className="total-score-label">Total ATS Score</div>
          <div className="total-score-value" style={{ color: getScoreColor(analysis?.ats_score || analysis?.overall_score) }}>
            {(analysis?.ats_score || analysis?.overall_score || 0).toFixed(1)}/100
          </div>
          <div className="total-score-grade" style={{ color: getScoreColor(analysis?.ats_score || analysis?.overall_score) }}>
            {getScoreGrade(analysis?.ats_score || analysis?.overall_score)}
          </div>
        </div>
      </div>
    );
  };

  const renderDomainInfo = (analysis) => {
    const domain = analysis?.primary_domain;
    const seniority = analysis?.seniority_level;
    const expertise = analysis?.domain_expertise;
    
    if (!domain && !seniority && !expertise) return null;
    
    return (
      <div className="domain-info-container glass">
        <div className="domain-info-header">
          <h3>Domain & Seniority Assessment</h3>
          <div className="domain-badge" style={{ 
            background: getDomainColor(domain) + '20',
            color: getDomainColor(domain),
            border: `1px solid ${getDomainColor(domain)}40`
          }}>
            {getDomainIcon(domain)}
            <span>{domain || 'General'}</span>
          </div>
        </div>
        
        <div className="domain-details">
          {seniority && seniority !== 'To be determined' && (
            <div className="domain-detail">
              <div className="detail-label">
                <User size={14} />
                <span>Seniority Level</span>
              </div>
              <div className="detail-value" style={{ color: getSeniorityColor(seniority) }}>
                {seniority}
              </div>
            </div>
          )}
          
          {expertise && expertise !== 'To be determined' && (
            <div className="domain-detail">
              <div className="detail-label">
                <Award size={14} />
                <span>Domain Expertise</span>
              </div>
              <div className="detail-value">
                {expertise}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Render functions for different views
  const renderMainView = () => (
    <div className="upload-section">
      <div className="section-header">
        <h2>Start Enhanced ATS Analysis</h2>
        <p>Upload resume(s) and job description for realistic ATS scoring</p>
        <div className="service-status">
          <span className="status-badge backend">
            {backendStatusInfo.icon} {backendStatusInfo.text}
          </span>
          <span className="status-badge ai">
            {aiStatusInfo.icon} {aiStatusInfo.text}
          </span>
          <span className="status-badge ats-enhanced">
            <BarChart4 size={14} /> Enhanced ATS
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
              <span>Enhanced ATS Scoring</span>
            </div>
            <div className="stat">
              <div className="stat-icon">
                <BarChart4 size={14} />
              </div>
              <span>Weighted Evaluation</span>
            </div>
            <div className="stat">
              <div className="stat-icon">
                <Cpu size={14} />
              </div>
              <span>Domain Detection</span>
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
              <p className="card-subtitle">Paste the complete job description for accurate ATS scoring</p>
            </div>
          </div>
          
          <div className="textarea-wrapper">
            <textarea
              className="job-description-input"
              placeholder={`• Paste job description here\n• Include required skills\n• Mention qualifications\n• List responsibilities\n• Add any specific requirements\n\n💡 Tip: Include domain-specific requirements for better scoring`}
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
              <h3>{batchMode ? 'Enhanced ATS Batch Analysis' : 'Enhanced ATS Analysis in Progress'}</h3>
            </div>
            
            <div className="progress-container">
              <div className="progress-bar" style={{ width: `${batchMode ? batchProgress : progress}%` }}></div>
            </div>
            
            <div className="loading-text">
              <span className="loading-message">{loadingMessage}</span>
              <span className="loading-subtext">
                {batchMode 
                  ? `Processing ${resumeFiles.length} resume(s) with enhanced ATS scoring...` 
                  : `Using enhanced weighted ATS evaluation...`}
              </span>
            </div>
            
            <div className="progress-stats">
              <span>{Math.round(batchMode ? batchProgress : progress)}%</span>
              <span>•</span>
              <span>Backend: {backendStatus === 'ready' ? 'Active' : 'Waking...'}</span>
              <span>•</span>
              <span>DeepSeek: {aiStatus === 'available' ? 'Ready 🧠' : 'Warming...'}</span>
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
              <BarChart4 size={14} />
              <span>Enhanced ATS scoring evaluates 5 weighted dimensions for realistic results</span>
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
              <BarChart4 size={20} />
              <div className="button-text">
                <span>{batchMode ? 'Enhanced ATS Batch Analysis' : 'Enhanced ATS Analysis'}</span>
                <span className="button-subtext">
                  {batchMode 
                    ? `${resumeFiles.length} resume(s) • Weighted ATS Scoring • Batch` 
                    : `Weighted ATS Scoring • Domain Detection`}
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
              <BarChart4 size={16} />
              <span>Enhanced ATS scoring across 5 weighted dimensions</span>
            </div>
            <div className="tip">
              <Cpu size={16} />
              <span>Domain detection for VLSI and CS/Software roles</span>
            </div>
            <div className="tip">
              <TrendingUp size={16} />
              <span>Candidates ranked by enhanced ATS score (0-100)</span>
            </div>
            <div className="tip">
              <Download size={16} />
              <span>Download detailed Excel report with ATS breakdown</span>
            </div>
          </>
        ) : (
          <>
            <div className="tip">
              <BarChart4 size={16} />
              <span>Skills Match (30), Experience (25), Role Alignment (20), Projects (15), Resume Quality (10)</span>
            </div>
            <div className="tip">
              <Cpu size={16} />
              <span>Domain-specific evaluation for VLSI and CS/Software</span>
            </div>
            <div className="tip">
              <User size={16} />
              <span>Seniority assessment and domain expertise level</span>
            </div>
            <div className="tip">
              <Brain size={16} />
              <span>Strict and realistic scoring like real ATS systems</span>
            </div>
          </>
        )}
      </div>
    </div>
  );

  const renderSingleAnalysisView = () => {
    if (!analysis) return null;

    const atsScore = analysis.ats_score || analysis.overall_score;
    const domain = analysis.primary_domain || 'General';
    const seniority = analysis.seniority_level;

    return (
      <div className="results-section">
        {/* Navigation Header */}
        <div className="navigation-header glass">
          <button onClick={navigateToMain} className="back-button">
            <ArrowLeft size={20} />
            <span>New Analysis</span>
          </button>
          <div className="navigation-title">
            <h2>🎯 Enhanced ATS Resume Analysis</h2>
            <p>{analysis.candidate_name} • {domain} Domain</p>
          </div>
          <div className="navigation-actions">
            <button className="download-report-btn" onClick={handleDownload}>
              <DownloadCloud size={18} />
              <span>Download Enhanced Report</span>
            </button>
          </div>
        </div>

        {/* Candidate Header */}
        <div className="analysis-header">
          <div className="candidate-info">
            <div className="candidate-avatar" style={{ background: getDomainColor(domain) + '20', color: getDomainColor(domain) }}>
              {getDomainIcon(domain)}
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
                <span className="domain-info" style={{ color: getDomainColor(domain) }}>
                  {getDomainIcon(domain)}
                  {domain}
                </span>
                {seniority && seniority !== 'To be determined' && (
                  <span className="seniority-info" style={{ color: getSeniorityColor(seniority) }}>
                    <User size={14} />
                    {seniority}
                  </span>
                )}
              </div>
            </div>
          </div>
          
          <div className="score-display">
            <div className="score-circle-wrapper">
              <div className="score-circle-glow" style={{ 
                background: `radial-gradient(circle, ${getScoreColor(atsScore)}22 0%, transparent 70%)` 
              }}></div>
              <div 
                className="score-circle" 
                style={{ 
                  borderColor: getScoreColor(atsScore),
                  background: `conic-gradient(${getScoreColor(atsScore)} ${atsScore * 3.6}deg, #2d3749 0deg)` 
                }}
              >
                <div className="score-inner">
                  <div className="score-value" style={{ color: getScoreColor(atsScore) }}>
                    {atsScore}
                  </div>
                  <div className="score-label">Enhanced ATS Score</div>
                </div>
              </div>
            </div>
            <div className="score-info">
              <h3 className="score-grade">{getScoreGrade(atsScore)}</h3>
              <p className="score-description">
                Based on weighted evaluation across 5 dimensions
              </p>
              <div className="score-meta">
                <span className="meta-item">
                  <Brain size={12} />
                  Response Time: {analysis.response_time || 'N/A'}
                </span>
                <span className="meta-item">
                  <Cpu size={12} />
                  Model: {analysis.ai_model || 'DeepSeek AI'}
                </span>
                <span className="meta-item">
                  <BarChart4 size={12} />
                  Weighted ATS Scoring
                </span>
              </div>
            </div>
        </div>
        </div>

        {/* ATS Breakdown */}
        {renderATSBreakdown(analysis)}

        {/* Domain Info */}
        {renderDomainInfo(analysis)}

        {/* Recommendation Card */}
        <div className="recommendation-card glass" style={{
          background: `linear-gradient(135deg, ${getScoreColor(atsScore)}15, ${getScoreColor(atsScore)}08)`,
          borderLeft: `4px solid ${getScoreColor(atsScore)}`
        }}>
          <div className="recommendation-header">
            <AwardIcon size={28} style={{ color: getScoreColor(atsScore) }} />
            <div>
              <h3>ATS Analysis Recommendation</h3>
              <p className="recommendation-subtitle">
                {analysis.ai_model || 'DeepSeek AI'} • Enhanced Weighted Evaluation
              </p>
            </div>
          </div>
          <div className="recommendation-content">
            <p className="recommendation-text">{analysis.recommendation}</p>
            <div className="confidence-badge">
              <BarChart4 size={16} />
              <span>Enhanced ATS Analysis</span>
            </div>
          </div>
        </div>

        {/* Overall Feedback */}
        {analysis.overall_feedback && (
          <div className="feedback-card glass">
            <div className="feedback-header">
              <MessageSquare size={24} />
              <h3>Overall ATS Feedback</h3>
            </div>
            <div className="feedback-content">
              <p>{analysis.overall_feedback}</p>
            </div>
          </div>
        )}

        {/* Skills Analysis */}
        <div className="section-title">
          <h2>Skills Analysis</h2>
          <p>Detailed breakdown of matched and missing skills with context</p>
        </div>
        
        <div className="skills-grid">
          <div className="skills-card glass success">
            <div className="skills-card-header">
              <div className="skills-icon success">
                <CheckCircle size={24} />
              </div>
              <div className="skills-header-content">
                <h3>Matched Skills</h3>
                <p className="skills-subtitle">Found in resume with evidence</p>
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
                <p className="skills-subtitle">Required skills not found or lacking evidence</p>
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
                  <li className="no-items success-text">All required skills are present with evidence!</li>
                )}
              </ul>
            </div>
          </div>
        </div>

        {/* Summary Section */}
        <div className="section-title">
          <h2>Profile Summary</h2>
          <p>Detailed insights extracted from resume</p>
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
                {analysis.domain_expertise && analysis.domain_expertise !== 'To be determined' && (
                  <span className="summary-tag" style={{ background: getDomainColor(domain) + '20', color: getDomainColor(domain) }}>
                    {analysis.domain_expertise} Expertise
                  </span>
                )}
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
          <h2>Strengths & Improvement Areas</h2>
          <p>Specific insights from ATS evaluation</p>
        </div>
        
        <div className="insights-grid">
          <div className="insight-card glass">
            <div className="insight-header">
              <div className="insight-icon success">
                <TrendingUp size={24} />
              </div>
              <div>
                <h3>Key Strengths</h3>
                <p className="insight-subtitle">Areas contributing to ATS score</p>
              </div>
            </div>
            <div className="insight-content">
              <div className="strengths-list">
                {analysis.key_strengths?.map((strength, index) => (
                  <div key={index} className="strength-item">
                    <CheckCircle size={16} className="strength-icon" />
                    <span className="strength-text">{strength}</span>
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
                <p className="insight-subtitle">Opportunities to increase ATS score</p>
              </div>
            </div>
            <div className="insight-content">
              <div className="improvements-list">
                {analysis.areas_for_improvement?.map((area, index) => (
                  <div key={index} className="improvement-item">
                    <AlertCircle size={16} className="improvement-icon" />
                    <span className="improvement-text">{area}</span>
                  </div>
                ))}
                {(!analysis.areas_for_improvement || analysis.areas_for_improvement.length === 0) && (
                  <div className="no-items success-text">No significant areas for improvement identified</div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* AI Analysis Details */}
        <div className="ai-details-card glass">
          <div className="ai-details-header">
            <Brain size={24} />
            <div>
              <h3>Enhanced ATS Analysis Details</h3>
              <p className="ai-details-subtitle">Technical information about this analysis</p>
            </div>
          </div>
          <div className="ai-details-content">
            <div className="ai-detail-item">
              <span className="detail-label">ATS Method:</span>
              <span className="detail-value">Weighted Evaluation (5 dimensions)</span>
            </div>
            <div className="ai-detail-item">
              <span className="detail-label">AI Provider:</span>
              <span className="detail-value">{analysis.ai_provider || 'DeepSeek'}</span>
            </div>
            <div className="ai-detail-item">
              <span className="detail-label">AI Model:</span>
              <span className="detail-value">{analysis.ai_model || 'DeepSeek AI'}</span>
            </div>
            <div className="ai-detail-item">
              <span className="detail-label">Response Time:</span>
              <span className="detail-value">{analysis.response_time || 'N/A'}</span>
            </div>
            <div className="ai-detail-item">
              <span className="detail-label">Analysis ID:</span>
              <span className="detail-value">{analysis.analysis_id || 'N/A'}</span>
            </div>
            <div className="ai-detail-item">
              <span className="detail-label">ATS Status:</span>
              <span className="detail-value" style={{ 
                color: analysis.ai_status === 'Warmed up' ? '#00ff9d' : '#ffd166' 
              }}>
                {analysis.ai_status || 'N/A'}
              </span>
            </div>
          </div>
        </div>

        {/* Action Section */}
        <div className="action-section glass">
          <div className="action-content">
            <h3>Enhanced ATS Analysis Complete</h3>
            <p>Download detailed Excel report with ATS breakdown or start a new analysis</p>
          </div>
          <div className="action-buttons">
            <button className="download-button" onClick={handleDownload}>
              <DownloadCloud size={20} />
              <span>Download Enhanced ATS Report</span>
            </button>
            <button className="reset-button" onClick={navigateToMain}>
              <RefreshCw size={20} />
              <span>New Enhanced ATS Analysis</span>
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
          <h2>🎯 Enhanced ATS Batch Analysis Results</h2>
          <p>{batchAnalysis?.successfully_analyzed || 0} resumes analyzed with weighted ATS scoring</p>
        </div>
        <div className="navigation-actions">
          <button className="download-report-btn" onClick={handleBatchDownload}>
            <DownloadCloud size={18} />
            <span>Download Full Enhanced Report</span>
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
        
        <div className="stat-card">
          <div className="stat-icon primary">
            <BarChart4 size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">Enhanced ATS</div>
            <div className="stat-label">Scoring Method</div>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon warning">
            <Cpu size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{batchAnalysis?.model_used || 'DeepSeek'}</div>
            <div className="stat-label">AI Model</div>
          </div>
        </div>
      </div>

      {/* Candidates Ranking */}
      <div className="section-title">
        <h2>Candidate Rankings</h2>
        <p>Sorted by Enhanced ATS Score (0-100) • Weighted Evaluation • Domain Detection</p>
      </div>
      
      <div className="batch-results-grid">
        {batchAnalysis?.analyses?.map((candidate, index) => {
          const atsScore = candidate.ats_score || candidate.overall_score;
          const domain = candidate.primary_domain || 'General';
          const seniority = candidate.seniority_level;
          
          return (
            <div key={index} className="batch-candidate-card glass">
              <div className="batch-card-header">
                <div className="candidate-rank">
                  <div className="rank-badge">#{candidate.rank}</div>
                  <div className="candidate-main-info">
                    <h3 className="candidate-name">{candidate.candidate_name}</h3>
                    <div className="candidate-meta">
                      <span className="file-info">{candidate.filename}</span>
                      <span className="file-size">{candidate.file_size}</span>
                      <span className="domain-tag" style={{ 
                        background: getDomainColor(domain) + '20',
                        color: getDomainColor(domain)
                      }}>
                        {getDomainIcon(domain)}
                        {domain}
                      </span>
                      {seniority && seniority !== 'To be determined' && (
                        <span className="seniority-tag" style={{ 
                          background: getSeniorityColor(seniority) + '20',
                          color: getSeniorityColor(seniority)
                        }}>
                          {seniority}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="candidate-score-display">
                  <div className="score-large" style={{ color: getScoreColor(atsScore) }}>
                    {atsScore}
                  </div>
                  <div className="score-label">ATS Score</div>
                  <div className="score-grade" style={{ color: getScoreColor(atsScore) }}>
                    {getScoreGrade(atsScore).split(' ')[0]}
                  </div>
                </div>
              </div>
              
              <div className="batch-card-content">
                <div className="recommendation-badge" style={{ 
                  background: getScoreColor(atsScore) + '20',
                  color: getScoreColor(atsScore),
                  border: `1px solid ${getScoreColor(atsScore)}40`
                }}>
                  {candidate.recommendation}
                </div>
                
                <div className="skills-preview">
                  <div className="skills-section">
                    <div className="skills-header">
                      <CheckCircle size={14} />
                      <span>Matched Skills ({candidate.skills_matched?.length || 0})</span>
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
                      <span>Missing Skills ({candidate.skills_missing?.length || 0})</span>
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
                
                <div className="experience-preview">
                  <p>{candidate.experience_summary?.substring(0, 120)}...</p>
                </div>
              </div>
              
              <div className="batch-card-footer">
                <button 
                  className="view-details-btn"
                  onClick={() => navigateToCandidateDetail(index)}
                >
                  View Full ATS Details
                  <ChevronRight size={16} />
                </button>
                {candidate.analysis_id && (
                  <button 
                    className="download-individual-btn"
                    onClick={() => handleIndividualDownload(candidate.analysis_id)}
                    title="Download enhanced ATS report"
                  >
                    <FileDown size={16} />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Action Buttons */}
      <div className="action-section glass">
        <div className="action-content">
          <h3>Enhanced ATS Batch Analysis Complete</h3>
          <p>Download comprehensive Excel report with detailed ATS breakdown for all candidates</p>
        </div>
        <div className="action-buttons">
          <button className="download-button" onClick={handleBatchDownload}>
            <DownloadCloud size={20} />
            <span>Download Full Enhanced ATS Report</span>
          </button>
          <button className="reset-button" onClick={navigateToMain}>
            <RefreshCw size={20} />
            <span>New Enhanced ATS Batch Analysis</span>
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

    const atsScore = candidate.ats_score || candidate.overall_score;
    const domain = candidate.primary_domain || 'General';
    const seniority = candidate.seniority_level;

    return (
      <div className="results-section">
        {/* Navigation Header */}
        <div className="navigation-header glass">
          <button onClick={navigateBack} className="back-button">
            <ArrowLeft size={20} />
            <span>Back to Rankings</span>
          </button>
          <div className="navigation-title">
            <h2>Enhanced ATS Candidate Details</h2>
            <p>Rank #{candidate.rank} • {candidate.candidate_name} • {domain}</p>
          </div>
          <div className="navigation-actions">
            {candidate.analysis_id && (
              <button 
                className="download-report-btn" 
                onClick={() => handleIndividualDownload(candidate.analysis_id)}
              >
                <FileDown size={18} />
                <span>Download Enhanced ATS Report</span>
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
            <div className="candidate-avatar" style={{ background: getDomainColor(domain) + '20', color: getDomainColor(domain) }}>
              {getDomainIcon(domain)}
            </div>
            <div>
              <h2 className="candidate-name">{candidate.candidate_name}</h2>
              <div className="candidate-meta">
                <span className="analysis-date">
                  <Clock size={14} />
                  Rank: #{candidate.rank} in batch
                </span>
                <span className="file-info">
                  <FileText size={14} />
                  {candidate.filename} • {candidate.file_size}
                </span>
                <span className="domain-info" style={{ color: getDomainColor(domain) }}>
                  {getDomainIcon(domain)}
                  {domain}
                </span>
                {seniority && seniority !== 'To be determined' && (
                  <span className="seniority-info" style={{ color: getSeniorityColor(seniority) }}>
                    <User size={14} />
                    {seniority}
                  </span>
                )}
              </div>
            </div>
          </div>
          
          <div className="score-display">
            <div className="score-circle-wrapper">
              <div className="score-circle-glow" style={{ 
                background: `radial-gradient(circle, ${getScoreColor(atsScore)}22 0%, transparent 70%)` 
              }}></div>
              <div 
                className="score-circle" 
                style={{ 
                  borderColor: getScoreColor(atsScore),
                  background: `conic-gradient(${getScoreColor(atsScore)} ${atsScore * 3.6}deg, #2d3749 0deg)` 
                }}
              >
                <div className="score-inner">
                  <div className="score-value" style={{ color: getScoreColor(atsScore) }}>
                    {atsScore}
                  </div>
                  <div className="score-label">Enhanced ATS Score</div>
                </div>
              </div>
            </div>
            <div className="score-info">
              <h3 className="score-grade">{getScoreGrade(atsScore)}</h3>
              <p className="score-description">
                Weighted evaluation across 5 ATS dimensions
              </p>
              <div className="score-meta">
                <span className="meta-item">
                  <Cpu size={12} />
                  Model: {candidate.ai_model || 'DeepSeek AI'}
                </span>
                <span className="meta-item">
                  <BarChart4 size={12} />
                  Enhanced ATS Scoring
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ATS Breakdown */}
        {renderATSBreakdown(candidate)}

        {/* Domain Info */}
        {renderDomainInfo(candidate)}

        {/* Recommendation Card */}
        <div className="recommendation-card glass" style={{
          background: `linear-gradient(135deg, ${getScoreColor(atsScore)}15, ${getScoreColor(atsScore)}08)`,
          borderLeft: `4px solid ${getScoreColor(atsScore)}`
        }}>
          <div className="recommendation-header">
            <AwardIcon size={28} style={{ color: getScoreColor(atsScore) }} />
            <div>
              <h3>Enhanced ATS Recommendation</h3>
              <p className="recommendation-subtitle">
                {candidate.ai_model || 'DeepSeek AI'} • Batch Processing • {domain} Domain
              </p>
            </div>
          </div>
          <div className="recommendation-content">
            <p className="recommendation-text">{candidate.recommendation}</p>
            <div className="confidence-badge">
              <BarChart4 size={16} />
              <span>Enhanced ATS Analysis</span>
            </div>
          </div>
        </div>

        {/* Overall Feedback */}
        {candidate.overall_feedback && (
          <div className="feedback-card glass">
            <div className="feedback-header">
              <MessageSquare size={24} />
              <h3>Overall ATS Feedback</h3>
            </div>
            <div className="feedback-content">
              <p>{candidate.overall_feedback}</p>
            </div>
          </div>
        )}

        {/* Skills Analysis */}
        <div className="section-title">
          <h2>Skills Analysis</h2>
          <p>Detailed breakdown of matched and missing skills with context</p>
        </div>
        
        <div className="skills-grid">
          <div className="skills-card glass success">
            <div className="skills-card-header">
              <div className="skills-icon success">
                <CheckCircle size={24} />
              </div>
              <div className="skills-header-content">
                <h3>Matched Skills</h3>
                <p className="skills-subtitle">Found in resume with evidence</p>
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
                <p className="skills-subtitle">Required skills not found or lacking evidence</p>
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
                  <li className="no-items success-text">All required skills are present with evidence!</li>
                )}
              </ul>
            </div>
          </div>
        </div>

        {/* Summary Section */}
        <div className="section-title">
          <h2>Profile Summary</h2>
          <p>Detailed insights extracted from resume</p>
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
              <p className="detailed-summary">{candidate.experience_summary || "No experience summary available."}</p>
              <div className="summary-footer">
                <span className="summary-tag">Professional Experience</span>
                {candidate.domain_expertise && candidate.domain_expertise !== 'To be determined' && (
                  <span className="summary-tag" style={{ background: getDomainColor(domain) + '20', color: getDomainColor(domain) }}>
                    {candidate.domain_expertise} Expertise
                  </span>
                )}
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
              <p className="detailed-summary">{candidate.education_summary || "No education summary available."}</p>
              <div className="summary-footer">
                <span className="summary-tag">Academic Background</span>
              </div>
            </div>
          </div>
        </div>

        {/* Insights Section */}
        <div className="section-title">
          <h2>Strengths & Improvement Areas</h2>
          <p>Specific insights from ATS evaluation</p>
        </div>
        
        <div className="insights-grid">
          <div className="insight-card glass">
            <div className="insight-header">
              <div className="insight-icon success">
                <TrendingUp size={24} />
              </div>
              <div>
                <h3>Key Strengths</h3>
                <p className="insight-subtitle">Areas contributing to ATS score</p>
              </div>
            </div>
            <div className="insight-content">
              <div className="strengths-list">
                {candidate.key_strengths?.map((strength, index) => (
                  <div key={index} className="strength-item">
                    <CheckCircle size={16} className="strength-icon" />
                    <span className="strength-text">{strength}</span>
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
                <p className="insight-subtitle">Opportunities to increase ATS score</p>
              </div>
            </div>
            <div className="insight-content">
              <div className="improvements-list">
                {candidate.areas_for_improvement?.map((area, index) => (
                  <div key={index} className="improvement-item">
                    <AlertCircle size={16} className="improvement-icon" />
                    <span className="improvement-text">{area}</span>
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
            <h3>Enhanced ATS Candidate Analysis Complete</h3>
            <p>Download enhanced ATS report or full batch report</p>
          </div>
          <div className="action-buttons">
            {candidate.analysis_id && (
              <button 
                className="download-button" 
                onClick={() => handleIndividualDownload(candidate.analysis_id)}
              >
                <FileDown size={20} />
                <span>Download Enhanced ATS Report</span>
              </button>
            )}
            <button className="download-button secondary" onClick={handleBatchDownload}>
              <DownloadCloud size={20} />
              <span>Download Full Enhanced ATS Batch Report</span>
            </button>
            <button className="reset-button" onClick={navigateBack}>
              <ArrowLeft size={20} />
              <span>Back to Enhanced ATS Rankings</span>
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
                <BarChart4 className="logo-icon" />
              </div>
              <div className="logo-text">
                <h1>Enhanced ATS Resume Analyzer</h1>
                <div className="logo-subtitle">
                  <span className="powered-by">Powered by</span>
                  <span className="deepseek-badge">🧠 DeepSeek</span>
                  <span className="divider">•</span>
                  <span className="tagline">Weighted ATS Scoring • Domain Detection • Up to 10 Resumes</span>
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
            
            {/* ATS Indicator */}
            <div className="feature ats-indicator">
              <BarChart4 size={16} />
              <span>Enhanced ATS</span>
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
                <span>{currentView === 'single-results' ? 'Single ATS Analysis' : 
                       currentView === 'batch-results' ? 'Batch ATS Results' : 
                       'Candidate ATS Details'}</span>
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
              title="Show enhanced ATS status"
            >
              <BarChart size={16} />
              <span>ATS Status</span>
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
                <BarChart4 size={20} />
                <h3>Enhanced ATS Service Status</h3>
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
                <div className="summary-label">DeepSeek API Status</div>
                <div className={`summary-value ${aiStatus === 'available' ? 'success' : aiStatus === 'warming' ? 'warning' : 'error'}`}>
                  {aiStatus === 'available' ? '🧠 Ready' : 
                   aiStatus === 'warming' ? '🔥 Warming' : 
                   '⚠️ Enhanced ATS Mode'}
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">ATS Scoring Method</div>
                <div className="summary-value success">
                  🎯 Weighted Evaluation
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">ATS Dimensions</div>
                <div className="summary-value">
                  📊 5 Weighted Categories
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Domain Support</div>
                <div className="summary-value info">
                  🌐 VLSI, CS/Software, General
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Seniority Assessment</div>
                <div className="summary-value">
                  👥 Junior, Mid, Senior, Lead
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Batch Capacity</div>
                <div className="summary-value success">
                  📈 Up to 10 resumes
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">AI Model</div>
                <div className="summary-value">
                  🤖 {getModelDisplayName(modelInfo)}
                </div>
              </div>
            </div>
            
            <div className="action-buttons-panel">
              <button 
                className="action-button refresh"
                onClick={checkBackendHealth}
              >
                <RefreshCw size={16} />
                Refresh ATS Status
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
                Force ATS Warm-up
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
                <span>DeepSeek: {aiStatus === 'available' ? 'Ready 🧠' : aiStatus === 'warming' ? 'Warming...' : 'Enhanced'}</span>
              </div>
              <div className="status-indicator active">
                <div className="indicator-dot" style={{ background: '#00ff9d', animation: 'pulse 1.5s infinite' }}></div>
                <span>ATS: Enhanced Weighted Scoring</span>
              </div>
              {modelInfo && (
                <div className="status-indicator active">
                  <div className="indicator-dot" style={{ background: '#00ff9d' }}></div>
                  <span>Model: {getModelDisplayName(modelInfo)}</span>
                </div>
              )}
              <div className="status-indicator active">
                <div className="indicator-dot" style={{ background: '#00ff9d' }}></div>
                <span>Mode: {currentView === 'single-results' ? 'Single ATS Analysis' : 
                              currentView === 'batch-results' ? 'Batch ATS Analysis' : 
                              currentView === 'candidate-detail' ? 'Candidate ATS Details' : 
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
                <span>Backend is waking up. Enhanced ATS analysis may be slower for the first request.</span>
              </div>
            )}
            
            {aiStatus === 'warming' && (
              <div className="wakeup-message">
                <Thermometer size={16} />
                <span>DeepSeek API is warming up. This ensures high-quality enhanced ATS responses.</span>
              </div>
            )}
            
            {batchMode && (
              <div className="multi-key-message">
                <BarChart4 size={16} />
                <span>Batch mode: Processing up to 10 resumes with enhanced weighted ATS scoring</span>
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
              <BarChart4 size={20} />
              <span>Enhanced ATS Resume Analyzer</span>
            </div>
            <p className="footer-tagline">
              Weighted ATS Scoring (5 dimensions) • Domain Detection • Seniority Assessment • Up to 10 resumes per batch
            </p>
          </div>
          
          <div className="footer-links">
            <div className="footer-section">
              <h4>ATS Features</h4>
              <a href="#">Weighted Scoring</a>
              <a href="#">Domain Detection</a>
              <a href="#">Seniority Assessment</a>
              <a href="#">Detailed Breakdown</a>
            </div>
            <div className="footer-section">
              <h4>Service</h4>
              <a href="#">Enhanced ATS</a>
              <a href="#">Domain Support</a>
              <a href="#">Excel Reports</a>
              <a href="#">Batch Processing</a>
            </div>
            <div className="footer-section">
              <h4>Navigation</h4>
              <a href="#" onClick={navigateToMain}>New ATS Analysis</a>
              {currentView !== 'main' && (
                <a href="#" onClick={navigateBack}>Go Back</a>
              )}
              <a href="#">Support</a>
              <a href="#">Documentation</a>
            </div>
          </div>
        </div>
        
        <div className="footer-bottom">
          <p>© 2024 Enhanced ATS Resume Analyzer. Built with React + Flask + DeepSeek AI. Weighted ATS Evaluation.</p>
          <div className="footer-stats">
            <span className="stat">
              <CloudLightning size={12} />
              Backend: {backendStatus === 'ready' ? 'Active' : 'Waking'}
            </span>
            <span className="stat">
              <BarChart4 size={12} />
              ATS: Enhanced Weighted
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
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
