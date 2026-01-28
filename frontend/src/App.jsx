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
  Eye, EyeOff, Search, Settings, Bell,
  HelpCircle, Shield as ShieldIcon, Key,
  LogOut, UserPlus, UserCheck, UserX,
  Star as StarIcon, Heart as HeartIcon,
  Flag, Filter as FilterIcon, SortAsc,
  SortDesc, MoreHorizontal, MoreVertical,
  Maximize2, Minimize2, Plus, Minus,
  Edit, Trash2, Copy, Scissors, Type,
  Bold, Italic, Underline, List,
  FileImage, File, FileText as FileTextIcon,
  Maximize, Minimize, X as CloseIcon,
  ChevronDown, ChevronUp, ExternalLink as ExternalLinkIcon,
  FileCode, FileArchive, FileVideo, FileAudio,
  FileCheck, FileWarning, FileQuestion, FileMinus,
  FilePlus, FileSlash, FileSearch, FileDigit,
  FileJson, FileXml, FileType, FileOutput,
  Download as DownloadIcon,
  ExternalLink as ExternalLinkIcon2
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
  
  // Resume Preview State
  const [showResumePreview, setShowResumePreview] = useState(false);
  const [resumePreviewContent, setResumePreviewContent] = useState(null);
  const [resumePreviewLoading, setResumePreviewLoading] = useState(false);
  const [previewMode, setPreviewMode] = useState('pdf'); // 'pdf' or 'original'
  
  const API_BASE_URL = 'https://resume-analyzer-1-pevo.onrender.com';
  
  const keepAliveInterval = useRef(null);
  const backendWakeInterval = useRef(null);
  const warmupCheckInterval = useRef(null);
  const iframeRef = useRef(null);

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
    setShowResumePreview(false);
    setResumePreviewContent(null);
    window.scrollTo(0, 0);
  };

  const navigateBack = () => {
    if (currentView === 'candidate-detail') {
      setCurrentView('batch-results');
    } else if (currentView === 'batch-results' || currentView === 'single-results') {
      setCurrentView('main');
    }
    setShowResumePreview(false);
    setResumePreviewContent(null);
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

  // Resume Preview Functions
  const fetchResumePreview = async (analysisId, candidateName, hasPdfPreview = true) => {
    try {
      setResumePreviewLoading(true);
      setShowResumePreview(true);
      setPreviewMode(hasPdfPreview ? 'pdf' : 'original');
      
      // For PDF preview, we'll use an iframe
      if (hasPdfPreview) {
        const previewUrl = `${API_BASE_URL}/resume-preview/${analysisId}`;
        setResumePreviewContent({
          type: 'pdf',
          url: previewUrl,
          filename: `${candidateName}_resume_preview.pdf`,
          candidateName: candidateName
        });
      } else {
        // For non-PDF files, we'll download and handle based on type
        const response = await axios.get(`${API_BASE_URL}/resume-preview/${analysisId}`, {
          responseType: 'blob',
          timeout: 30000
        });
        
        const blob = new Blob([response.data]);
        const url = URL.createObjectURL(blob);
        const filename = response.headers['content-disposition'] 
          ? response.headers['content-disposition'].split('filename=')[1].replace(/"/g, '')
          : `${candidateName}_resume`;
        
        setResumePreviewContent({
          type: 'download',
          url: url,
          filename: filename,
          candidateName: candidateName,
          blob: blob
        });
      }
      
      setResumePreviewLoading(false);
      
    } catch (error) {
      console.log('Error fetching resume preview:', error);
      setResumePreviewContent({
        type: 'error',
        message: 'Failed to load resume preview. The file may have expired or is not available.',
        candidateName: candidateName
      });
      setResumePreviewLoading(false);
    }
  };

  const downloadOriginalResume = async (analysisId, candidateName) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/resume-original/${analysisId}`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data]);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = response.headers['content-disposition'] 
        ? response.headers['content-disposition'].split('filename=')[1].replace(/"/g, '')
        : `${candidateName}_original_resume`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
    } catch (error) {
      console.log('Error downloading original resume:', error);
      setError('Failed to download original resume.');
    }
  };

  const closeResumePreview = () => {
    setShowResumePreview(false);
    setResumePreviewContent(null);
    // Clean up blob URLs
    if (resumePreviewContent?.type === 'download' && resumePreviewContent.url) {
      URL.revokeObjectURL(resumePreviewContent.url);
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

  // Get file icon based on file extension
  const getFileIcon = (filename) => {
    if (!filename) return <File size={20} />;
    
    const ext = filename.split('.').pop().toLowerCase();
    switch(ext) {
      case 'pdf':
        return <File size={20} />;
      case 'doc':
      case 'docx':
        return <FileTextIcon size={20} />;
      case 'txt':
        return <FileCode size={20} />;
      default:
        return <File size={20} />;
    }
  };

  // Get file type display name
  const getFileTypeDisplay = (filename) => {
    if (!filename) return 'File';
    
    const ext = filename.split('.').pop().toLowerCase();
    switch(ext) {
      case 'pdf':
        return 'PDF Document';
      case 'doc':
        return 'Word Document';
      case 'docx':
        return 'Word Document';
      case 'txt':
        return 'Text File';
      default:
        return 'Document';
    }
  };

  // Render Resume Preview Modal
  const renderResumePreviewModal = () => {
    if (!showResumePreview) return null;
    
    return (
      <div className="resume-preview-modal-overlay" onClick={closeResumePreview}>
        <div className="resume-preview-modal glass" onClick={(e) => e.stopPropagation()}>
          <div className="resume-preview-header">
            <div className="preview-title">
              <FileText size={20} />
              <div>
                <h3>Resume Preview</h3>
                <p className="preview-subtitle">
                  {resumePreviewContent?.candidateName || 'Candidate'}
                  {previewMode === 'pdf' ? ' • PDF Preview' : ' • Original File'}
                </p>
              </div>
            </div>
            <div className="preview-actions">
              {resumePreviewContent?.type === 'pdf' && (
                <button 
                  className="preview-action-btn"
                  onClick={() => window.open(resumePreviewContent.url, '_blank')}
                  title="Open in new tab"
                >
                  <ExternalLinkIcon2 size={18} />
                </button>
              )}
              {resumePreviewContent?.type === 'download' && (
                <button 
                  className="preview-action-btn"
                  onClick={() => {
                    const link = document.createElement('a');
                    link.href = resumePreviewContent.url;
                    link.download = resumePreviewContent.filename;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                  }}
                  title="Download file"
                >
                  <DownloadIcon size={18} />
                </button>
              )}
              <button onClick={closeResumePreview} className="close-preview-btn">
                <CloseIcon size={20} />
              </button>
            </div>
          </div>
          
          <div className="resume-preview-content">
            {resumePreviewLoading ? (
              <div className="preview-loading">
                <Loader size={32} className="spinner" />
                <p>Loading resume preview...</p>
              </div>
            ) : resumePreviewContent?.type === 'error' ? (
              <div className="preview-error">
                <AlertCircle size={48} />
                <h4>Unable to Load Resume</h4>
                <p>{resumePreviewContent.message}</p>
                <button onClick={closeResumePreview} className="close-btn">
                  Close
                </button>
              </div>
            ) : resumePreviewContent?.type === 'pdf' ? (
              <div className="pdf-preview-container">
                <iframe
                  ref={iframeRef}
                  src={resumePreviewContent.url}
                  title={`Resume Preview: ${resumePreviewContent.candidateName}`}
                  className="pdf-preview-frame"
                  sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
                />
                <div className="pdf-preview-note">
                  <Info size={14} />
                  <span>
                    PDF preview embedded. For better viewing, you can 
                    <button 
                      className="inline-link"
                      onClick={() => window.open(resumePreviewContent.url, '_blank')}
                    >
                      open in new tab
                    </button>
                    .
                  </span>
                </div>
              </div>
            ) : resumePreviewContent?.type === 'download' ? (
              <div className="download-preview-container">
                <div className="download-preview-info">
                  <File size={48} />
                  <h4>Original File Preview</h4>
                  <p>This file type cannot be previewed directly in the browser.</p>
                  <p className="file-info">
                    <strong>Filename:</strong> {resumePreviewContent.filename}
                  </p>
                  <div className="download-actions">
                    <button 
                      className="download-btn primary"
                      onClick={() => {
                        const link = document.createElement('a');
                        link.href = resumePreviewContent.url;
                        link.download = resumePreviewContent.filename;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                      }}
                    >
                      <DownloadIcon size={18} />
                      Download Original File
                    </button>
                    <button 
                      className="download-btn secondary"
                      onClick={closeResumePreview}
                    >
                      Close
                    </button>
                  </div>
                </div>
              </div>
            ) : null}
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
                <Eye size={14} />
              </div>
              <span>PDF Preview</span>
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
              <span>All resumes are automatically converted to PDF for easy preview</span>
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
                    : `${getModelDisplayName(modelInfo)} • PDF Preview`}
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
              <Eye size={16} />
              <span>All resumes are automatically converted to PDF for easy preview</span>
            </div>
            <div className="tip">
              <Zap size={16} />
              <span>~10-15 seconds for 10 resumes (Round-robin parallel processing)</span>
            </div>
            <div className="tip">
              <File size={16} />
              <span>View original resume structure in PDF format directly in browser</span>
            </div>
          </>
        ) : (
          <>
            <div className="tip">
              <Brain size={16} />
              <span>Groq AI offers ultra-fast resume analysis</span>
            </div>
            <div className="tip">
              <Eye size={16} />
              <span>PDF preview shows the exact original resume structure and formatting</span>
            </div>
            <div className="tip">
              <Activity size={16} />
              <span>Backend stays awake with automatic pings every 3 minutes</span>
            </div>
            <div className="tip">
              <File size={16} />
              <span>DOC/DOCX/TXT files are automatically converted to PDF for perfect preview</span>
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
        {/* Resume Preview Modal */}
        {renderResumePreviewModal()}
        
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
              <span>Download Detailed Report</span>
            </button>
          </div>
        </div>

        {/* Candidate Header with Resume Preview Button */}
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
                <span className="file-info">
                  <Cpu size={14} />
                  Model: {analysis.ai_model || 'Groq AI'}
                </span>
                {analysis.resume_stored && (
                  <div className="resume-actions">
                    <button 
                      className="view-resume-btn"
                      onClick={() => fetchResumePreview(
                        analysis.analysis_id, 
                        analysis.candidate_name, 
                        analysis.has_pdf_preview
                      )}
                    >
                      <Eye size={14} />
                      {analysis.has_pdf_preview ? 'View PDF Preview' : 'View Resume'}
                    </button>
                    <button 
                      className="download-original-btn"
                      onClick={() => downloadOriginalResume(analysis.analysis_id, analysis.candidate_name)}
                      title="Download original file"
                    >
                      <DownloadIcon size={14} />
                    </button>
                  </div>
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
                  <Brain size={12} />
                  Response Time: {analysis.response_time || 'N/A'}
                </span>
                <span className="meta-item">
                  <Key size={12} />
                  {analysis.key_used || 'Groq API'}
                </span>
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

        {/* Resume Preview Card */}
        {analysis.resume_stored && (
          <div className="resume-preview-card glass">
            <div className="resume-preview-card-header">
              <div className="preview-card-title">
                <FileText size={24} />
                <div>
                  <h3>Original Resume Preview</h3>
                  <p className="preview-card-subtitle">
                    View the exact original resume structure and formatting
                  </p>
                </div>
              </div>
              <div className="preview-card-badges">
                {analysis.has_pdf_preview && (
                  <span className="preview-badge pdf">
                    <File size={14} />
                    PDF Preview Available
                  </span>
                )}
                <span className="preview-badge stored">
                  <FileCheck size={14} />
                  Original Stored
                </span>
              </div>
            </div>
            
            <div className="resume-preview-card-content">
              <div className="resume-file-details">
                <div className="file-detail">
                  <span className="detail-label">Original File:</span>
                  <span className="detail-value">
                    <FileTextIcon size={14} />
                    {analysis.resume_original_filename || analysis.filename}
                  </span>
                </div>
                <div className="file-detail">
                  <span className="detail-label">File Size:</span>
                  <span className="detail-value">{analysis.file_size}</span>
                </div>
                <div className="file-detail">
                  <span className="detail-label">File Type:</span>
                  <span className="detail-value">
                    {getFileTypeDisplay(analysis.resume_original_filename || analysis.filename)}
                  </span>
                </div>
                <div className="file-detail">
                  <span className="detail-label">Preview Type:</span>
                  <span className="detail-value">
                    {analysis.has_pdf_preview ? 'PDF (Converted for perfect viewing)' : 'Original Format'}
                  </span>
                </div>
              </div>
              
              <div className="resume-preview-actions">
                <button 
                  className="preview-action-btn primary"
                  onClick={() => fetchResumePreview(
                    analysis.analysis_id, 
                    analysis.candidate_name, 
                    analysis.has_pdf_preview
                  )}
                >
                  <Eye size={18} />
                  <span>
                    {analysis.has_pdf_preview ? 'View PDF Preview' : 'Preview Original File'}
                  </span>
                </button>
                <button 
                  className="preview-action-btn secondary"
                  onClick={() => downloadOriginalResume(analysis.analysis_id, analysis.candidate_name)}
                >
                  <DownloadIcon size={18} />
                  <span>Download Original</span>
                </button>
                {analysis.has_pdf_preview && (
                  <button 
                    className="preview-action-btn outline"
                    onClick={() => window.open(`${API_BASE_URL}/resume-preview/${analysis.analysis_id}`, '_blank')}
                  >
                    <ExternalLinkIcon2 size={18} />
                    <span>Open PDF in New Tab</span>
                  </button>
                )}
              </div>
              
              <div className="resume-preview-note">
                <Info size={14} />
                <span>
                  {analysis.has_pdf_preview 
                    ? 'Non-PDF files (DOC/DOCX/TXT) are automatically converted to PDF to preserve original formatting and structure for perfect preview.'
                    : 'PDF files are displayed directly. Original formatting and structure are preserved.'}
                </span>
              </div>
            </div>
          </div>
        )}

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
                {analysis.ai_model || 'Groq AI'} • {analysis.key_used || 'Groq API'}
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

        {/* Skills Analysis - Now showing 5-8 skills each */}
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

        {/* Summary Section with Detailed 5-7 sentences */}
        <div className="section-title">
          <h2>Detailed Profile Summary</h2>
          <p>Comprehensive insights extracted from resume</p>
        </div>
        
        <div className="summary-grid">
          <div className="summary-card glass">
            <div className="summary-header">
              <div className="summary-icon">
                <Briefcase size={24} />
              </div>
              <h3>Experience Summary (5-7 sentences)</h3>
            </div>
            <div className="summary-content">
              <p className="detailed-summary" style={{ fontSize: '1rem', lineHeight: '1.6' }}>
                {analysis.experience_summary || "No experience summary available."}
              </p>
            </div>
          </div>

          <div className="summary-card glass">
            <div className="summary-header">
              <div className="summary-icon">
                <BookOpen size={24} />
              </div>
              <h3>Education Summary (5-7 sentences)</h3>
            </div>
            <div className="summary-content">
              <p className="detailed-summary" style={{ fontSize: '1rem', lineHeight: '1.6' }}>
                {analysis.education_summary || "No education summary available."}
              </p>
            </div>
          </div>
        </div>

        {/* Insights Section - Now showing 6 items each */}
        <div className="section-title">
          <h2>Insights & Recommendations (6 items each)</h2>
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
                <p className="insight-subtitle">Areas where candidate excels</p>
              </div>
            </div>
            <div className="insight-content">
              <div className="strengths-list">
                {analysis.key_strengths?.slice(0, 6).map((strength, index) => (
                  <div key={index} className="strength-item">
                    <CheckCircle size={16} className="strength-icon" />
                    <span className="strength-text" style={{ fontSize: '0.95rem' }}>{strength}</span>
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
                {analysis.areas_for_improvement?.slice(0, 6).map((area, index) => (
                  <div key={index} className="improvement-item">
                    <AlertCircle size={16} className="improvement-icon" />
                    <span className="improvement-text" style={{ fontSize: '0.95rem' }}>{area}</span>
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
            <p>Download the detailed Excel report or start a new analysis</p>
          </div>
          <div className="action-buttons">
            <button className="download-button" onClick={handleDownload}>
              <DownloadCloud size={20} />
              <span>Download Detailed Excel Report</span>
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
        {/* Resume Preview Modal */}
        {renderResumePreviewModal()}
        
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
              <span>Download Full Detailed Report</span>
            </button>
          </div>
        </div>

        {/* Key Statistics */}
        {batchAnalysis?.key_statistics && (
          <div className="key-stats-container glass">
            <div className="key-stats-header">
              <Key size={20} />
              <h3>API Key Usage Statistics</h3>
            </div>
            <div className="key-stats-grid">
              {batchAnalysis.key_statistics.map((keyStat, index) => (
                <div key={index} className="key-stat-card">
                  <div className="key-stat-header">
                    <div className={`key-status-indicator ${keyStat.status === 'available' ? 'available' : 'cooling'}`}>
                      {keyStat.status === 'available' ? '✅' : '🔄'}
                    </div>
                    <span className="key-name">{keyStat.key}</span>
                  </div>
                  <div className="key-stat-content">
                    <div className="key-usage">
                      <span className="usage-label">Used:</span>
                      <span className="usage-value">{keyStat.used} resumes</span>
                    </div>
                    <div className="key-status">
                      <span className="status-label">Status:</span>
                      <span className={`status-value ${keyStat.status}`}>
                        {keyStat.status === 'available' ? 'Available' : 'Cooling'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
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
            <div className="stat-icon primary">
              <File size={24} />
            </div>
            <div className="stat-content">
              <div className="stat-value">
                {batchAnalysis?.analyses?.filter(a => a.has_pdf_preview).length || 0}
              </div>
              <div className="stat-label">PDF Preview</div>
            </div>
          </div>
          
          <div className="stat-card">
            <div className="stat-icon success">
              <Eye size={24} />
            </div>
            <div className="stat-content">
              <div className="stat-value">
                {batchAnalysis?.analyses?.filter(a => a.resume_stored).length || 0}
              </div>
              <div className="stat-label">Resumes Stored</div>
            </div>
          </div>
          
          <div className="stat-card">
            <div className="stat-icon warning">
              <Brain size={24} />
            </div>
            <div className="stat-content">
              <div className="stat-value">Groq</div>
              <div className="stat-label">AI Provider</div>
            </div>
          </div>
        </div>

        {/* Performance Info */}
        {batchAnalysis?.performance && (
          <div className="performance-info glass">
            <div className="performance-header">
              <Activity size={20} />
              <h3>Performance Metrics</h3>
            </div>
            <div className="performance-content">
              <div className="performance-item">
                <span className="performance-label">Processing Time:</span>
                <span className="performance-value">{batchAnalysis.processing_time}</span>
              </div>
              <div className="performance-item">
                <span className="performance-label">Processing Method:</span>
                <span className="performance-value">{batchAnalysis.processing_method === 'round_robin_parallel' ? 'Round-robin Parallel' : batchAnalysis.processing_method}</span>
              </div>
              {batchAnalysis.performance && (
                <div className="performance-item">
                  <span className="performance-label">Speed:</span>
                  <span className="performance-value">{batchAnalysis.performance}</span>
                </div>
              )}
              {batchAnalysis.success_rate && (
                <div className="performance-item">
                  <span className="performance-label">Success Rate:</span>
                  <span className="performance-value">{batchAnalysis.success_rate}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Candidates Ranking */}
        <div className="section-title">
          <h2>Candidate Rankings (5-8 skills analysis each)</h2>
          <p>Sorted by ATS Score (Highest to Lowest) • Groq Parallel Processing</p>
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
                      <span className="file-info">
                        <FileText size={12} />
                        {candidate.filename}
                      </span>
                      <span className="file-size">{candidate.file_size}</span>
                      {candidate.key_used && (
                        <span className="key-used">
                          <Key size={12} />
                          {candidate.key_used}
                        </span>
                      )}
                      {candidate.resume_stored && (
                        <div className="resume-preview-badges">
                          {candidate.has_pdf_preview && (
                            <span className="preview-badge mini pdf">
                              <File size={10} />
                              PDF
                            </span>
                          )}
                        </div>
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
                
                {candidate.resume_stored && (
                  <div className="resume-preview-mini">
                    <div className="resume-mini-header">
                      <FileText size={14} />
                      <span>Resume Available</span>
                    </div>
                    <div className="resume-mini-actions">
                      <button 
                        className="view-resume-btn mini"
                        onClick={() => fetchResumePreview(
                          candidate.analysis_id, 
                          candidate.candidate_name, 
                          candidate.has_pdf_preview
                        )}
                      >
                        <Eye size={12} />
                        {candidate.has_pdf_preview ? 'PDF Preview' : 'View'}
                      </button>
                      <button 
                        className="download-original-btn mini"
                        onClick={() => downloadOriginalResume(candidate.analysis_id, candidate.candidate_name)}
                        title="Download original file"
                      >
                        <DownloadIcon size={12} />
                      </button>
                    </div>
                  </div>
                )}
              </div>
              
              <div className="batch-card-footer">
                <button 
                  className="view-details-btn"
                  onClick={() => navigateToCandidateDetail(index)}
                >
                  View Full Details (5-8 skills each)
                  <ChevronRight size={16} />
                </button>
                {candidate.analysis_id && (
                  <button 
                    className="download-individual-btn"
                    onClick={() => handleIndividualDownload(candidate.analysis_id)}
                    title="Download individual detailed report"
                  >
                    <FileDown size={16} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Resume Preview Info */}
        {batchAnalysis?.analyses?.some(a => a.resume_stored) && (
          <div className="resume-preview-info glass">
            <div className="resume-preview-info-header">
              <File size={20} />
              <h3>Resume Preview Information</h3>
            </div>
            <div className="resume-preview-info-content">
              <p>
                <Info size={16} />
                <span>
                  {batchAnalysis.analyses.filter(a => a.has_pdf_preview).length} out of {batchAnalysis.analyses.length} resumes have PDF preview available.
                  Non-PDF files (DOC/DOCX/TXT) are automatically converted to PDF to preserve original formatting.
                  Click "PDF Preview" on any candidate card to view the exact original resume structure.
                </span>
              </p>
              <div className="preview-stats">
                <div className="preview-stat">
                  <div className="stat-value">{batchAnalysis.analyses.filter(a => a.has_pdf_preview).length}</div>
                  <div className="stat-label">PDF Preview</div>
                </div>
                <div className="preview-stat">
                  <div className="stat-value">{batchAnalysis.analyses.filter(a => a.resume_stored).length}</div>
                  <div className="stat-label">Original Stored</div>
                </div>
                <div className="preview-stat">
                  <div className="stat-value">1 hour</div>
                  <div className="stat-label">Retention</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="action-section glass">
          <div className="action-content">
            <h3>Batch Analysis Complete</h3>
            <p>Download comprehensive Excel report with detailed candidate analysis (5-8 skills each)</p>
          </div>
          <div className="action-buttons">
            <button className="download-button" onClick={handleBatchDownload}>
              <DownloadCloud size={20} />
              <span>Download Full Detailed Batch Report</span>
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
        {/* Resume Preview Modal */}
        {renderResumePreviewModal()}
        
        {/* Navigation Header */}
        <div className="navigation-header glass">
          <button onClick={navigateBack} className="back-button">
            <ArrowLeft size={20} />
            <span>Back to Rankings</span>
          </button>
          <div className="navigation-title">
            <h2>Candidate Details (5-8 skills analysis)</h2>
            <p>Rank #{candidate.rank} • {candidate.candidate_name}</p>
          </div>
          <div className="navigation-actions">
            {candidate.analysis_id && (
              <button 
                className="download-report-btn" 
                onClick={() => handleIndividualDownload(candidate.analysis_id)}
              >
                <FileDown size={18} />
                <span>Download Individual Detailed Report</span>
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

        {/* Candidate Header with Resume Preview */}
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
                {candidate.key_used && (
                  <span className="key-info">
                    <Key size={14} />
                    {candidate.key_used}
                  </span>
                )}
                {candidate.resume_stored && (
                  <div className="resume-actions">
                    <button 
                      className="view-resume-btn"
                      onClick={() => fetchResumePreview(
                        candidate.analysis_id, 
                        candidate.candidate_name, 
                        candidate.has_pdf_preview
                      )}
                    >
                      <Eye size={14} />
                      {candidate.has_pdf_preview ? 'View PDF Preview' : 'View Resume'}
                    </button>
                    <button 
                      className="download-original-btn"
                      onClick={() => downloadOriginalResume(candidate.analysis_id, candidate.candidate_name)}
                      title="Download original file"
                    >
                      <DownloadIcon size={14} />
                    </button>
                  </div>
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
                Based on skill matching, experience relevance, and qualifications
              </p>
              <div className="score-meta">
                <span className="meta-item">
                  <Cpu size={12} />
                  Model: {candidate.ai_model || 'Groq AI'}
                </span>
                <span className="meta-item">
                  <Key size={12} />
                  {candidate.key_used || 'Groq API'}
                </span>
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

        {/* Resume Preview Card */}
        {candidate.resume_stored && (
          <div className="resume-preview-card glass">
            <div className="resume-preview-card-header">
              <div className="preview-card-title">
                <FileText size={24} />
                <div>
                  <h3>Original Resume Preview</h3>
                  <p className="preview-card-subtitle">
                    View the exact original resume structure and formatting
                  </p>
                </div>
              </div>
              <div className="preview-card-badges">
                {candidate.has_pdf_preview && (
                  <span className="preview-badge pdf">
                    <File size={14} />
                    PDF Preview Available
                  </span>
                )}
                <span className="preview-badge stored">
                  <FileCheck size={14} />
                  Original Stored
                </span>
              </div>
            </div>
            
            <div className="resume-preview-card-content">
              <div className="resume-file-details">
                <div className="file-detail">
                  <span className="detail-label">Original File:</span>
                  <span className="detail-value">
                    <FileTextIcon size={14} />
                    {candidate.resume_original_filename || candidate.filename}
                  </span>
                </div>
                <div className="file-detail">
                  <span className="detail-label">File Size:</span>
                  <span className="detail-value">{candidate.file_size}</span>
                </div>
                <div className="file-detail">
                  <span className="detail-label">File Type:</span>
                  <span className="detail-value">
                    {getFileTypeDisplay(candidate.resume_original_filename || candidate.filename)}
                  </span>
                </div>
                <div className="file-detail">
                  <span className="detail-label">Preview Type:</span>
                  <span className="detail-value">
                    {candidate.has_pdf_preview ? 'PDF (Converted for perfect viewing)' : 'Original Format'}
                  </span>
                </div>
              </div>
              
              <div className="resume-preview-actions">
                <button 
                  className="preview-action-btn primary"
                  onClick={() => fetchResumePreview(
                    candidate.analysis_id, 
                    candidate.candidate_name, 
                    candidate.has_pdf_preview
                  )}
                >
                  <Eye size={18} />
                  <span>
                    {candidate.has_pdf_preview ? 'View PDF Preview' : 'Preview Original File'}
                  </span>
                </button>
                <button 
                  className="preview-action-btn secondary"
                  onClick={() => downloadOriginalResume(candidate.analysis_id, candidate.candidate_name)}
                >
                  <DownloadIcon size={18} />
                  <span>Download Original</span>
                </button>
                {candidate.has_pdf_preview && (
                  <button 
                    className="preview-action-btn outline"
                    onClick={() => window.open(`${API_BASE_URL}/resume-preview/${candidate.analysis_id}`, '_blank')}
                  >
                    <ExternalLinkIcon2 size={18} />
                    <span>Open PDF in New Tab</span>
                  </button>
                )}
              </div>
              
              <div className="resume-preview-note">
                <Info size={14} />
                <span>
                  {candidate.has_pdf_preview 
                    ? 'Non-PDF files (DOC/DOCX/TXT) are automatically converted to PDF to preserve original formatting and structure for perfect preview.'
                    : 'PDF files are displayed directly. Original formatting and structure are preserved.'}
                </span>
              </div>
            </div>
          </div>
        )}

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
                {candidate.ai_model || 'Groq AI'} • {candidate.key_used || 'Groq API'}
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

        {/* Summary Section */}
        <div className="section-title">
          <h2>Detailed Profile Summary</h2>
          <p>Comprehensive insights extracted from resume</p>
        </div>
        
        <div className="summary-grid">
          <div className="summary-card glass">
            <div className="summary-header">
              <div className="summary-icon">
                <Briefcase size={24} />
              </div>
              <h3>Experience Summary (5-7 sentences)</h3>
            </div>
            <div className="summary-content">
              <p className="detailed-summary" style={{ fontSize: '1rem', lineHeight: '1.6' }}>
                {candidate.experience_summary || "No experience summary available."}
              </p>
            </div>
          </div>

          <div className="summary-card glass">
            <div className="summary-header">
              <div className="summary-icon">
                <BookOpen size={24} />
              </div>
              <h3>Education Summary (5-7 sentences)</h3>
            </div>
            <div className="summary-content">
              <p className="detailed-summary" style={{ fontSize: '1rem', lineHeight: '1.6' }}>
                {candidate.education_summary || "No education summary available."}
              </p>
            </div>
          </div>
        </div>

        {/* Insights Section */}
        <div className="section-title">
          <h2>Insights & Recommendations (6 items each)</h2>
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
                <p className="insight-subtitle">Areas where candidate excels</p>
              </div>
            </div>
            <div className="insight-content">
              <div className="strengths-list">
                {candidate.key_strengths?.slice(0, 6).map((strength, index) => (
                  <div key={index} className="strength-item">
                    <CheckCircle size={16} className="strength-icon" />
                    <span className="strength-text" style={{ fontSize: '0.95rem' }}>{strength}</span>
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
                {candidate.areas_for_improvement?.slice(0, 6).map((area, index) => (
                  <div key={index} className="improvement-item">
                    <AlertCircle size={16} className="improvement-icon" />
                    <span className="improvement-text" style={{ fontSize: '0.95rem' }}>{area}</span>
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
            <p>Download individual detailed report or return to batch results</p>
          </div>
          <div className="action-buttons">
            {candidate.analysis_id && (
              <button 
                className="download-button" 
                onClick={() => handleIndividualDownload(candidate.analysis_id)}
              >
                <FileDown size={20} />
                <span>Download Individual Detailed Report</span>
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
    <div className="App">
      <header className="header glass">
        <div className="header-left">
          <div className="logo">
            <img src={logoImage} alt="LeadSOC Logo" className="logo-img" />
            <div className="logo-text">
              <span className="logo-title">LeadSOC</span>
              <span className="logo-subtitle">Resume Analyzer Pro</span>
            </div>
          </div>
        </div>
        
        <div className="header-center">
          <div className="nav-breadcrumbs">
            {currentView === 'main' && (
              <span className="nav-item active">
                <Home size={16} />
                <span>Upload</span>
              </span>
            )}
            {(currentView === 'single-results' || currentView === 'batch-results') && (
              <>
                <span className="nav-item" onClick={navigateToMain}>
                  <Home size={16} />
                  <span>Upload</span>
                </span>
                <ChevronRight size={16} className="breadcrumb-separator" />
                <span className="nav-item active">
                  {currentView === 'single-results' ? (
                    <>
                      <FileText size={16} />
                      <span>Results</span>
                    </>
                  ) : (
                    <>
                      <Users size={16} />
                      <span>Batch Results</span>
                    </>
                  )}
                </span>
              </>
            )}
            {currentView === 'candidate-detail' && (
              <>
                <span className="nav-item" onClick={navigateToMain}>
                  <Home size={16} />
                  <span>Upload</span>
                </span>
                <ChevronRight size={16} className="breadcrumb-separator" />
                <span className="nav-item" onClick={navigateToBatchResults}>
                  <Users size={16} />
                  <span>Batch Results</span>
                </span>
                <ChevronRight size={16} className="breadcrumb-separator" />
                <span className="nav-item active">
                  <User size={16} />
                  <span>Candidate Details</span>
                </span>
              </>
            )}
          </div>
        </div>
        
        <div className="header-right">
          <div className="service-info">
            {isWarmingUp && (
              <div className="warming-up-indicator">
                <Activity className="spinner" size={14} />
                <span>Warming up...</span>
              </div>
            )}
            <div className="ai-model-info">
              <Brain size={14} />
              <span>{getModelDisplayName(modelInfo) || 'Groq AI'}</span>
            </div>
            <div className="batch-info" style={{ display: 'flex', gap: '0.5rem' }}>
              <Users size={14} />
              <span>Batch: {MAX_BATCH_SIZE}</span>
            </div>
            <div className="view-mode">
              {currentView === 'single-results' && (
                <span className="view-badge">
                  <FileText size={12} /> Single
                </span>
              )}
              {(currentView === 'batch-results' || currentView === 'candidate-detail') && (
                <span className="view-badge batch">
                  <Users size={12} /> Batch
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="main-content">
        {renderCurrentView()}
      </main>

      <footer className="footer">
        <div className="footer-content">
          <div className="footer-section">
            <div className="footer-logo">
              <img src={logoImage} alt="LeadSOC" className="footer-logo-img" />
              <span className="footer-logo-text">LeadSOC</span>
            </div>
            <p className="footer-tagline">AI-Powered Resume Analysis Platform</p>
            <div className="footer-status">
              <span className="footer-status-item">
                <span className="status-dot" style={{ 
                  backgroundColor: backendStatus === 'ready' ? '#00ff9d' : 
                                 backendStatus === 'waking' ? '#ffd166' : '#ff6b6b' 
                }}></span>
                <span>Backend: {backendStatus === 'ready' ? 'Active' : 
                               backendStatus === 'waking' ? 'Waking' : 'Sleeping'}</span>
              </span>
              <span className="footer-status-item">
                <span className="status-dot" style={{ 
                  backgroundColor: aiStatus === 'available' ? '#00ff9d' : 
                                 aiStatus === 'warming' ? '#ffd166' : '#ff6b6b' 
                }}></span>
                <span>Groq AI: {aiStatus === 'available' ? 'Ready' : 
                               aiStatus === 'warming' ? 'Warming' : 'Checking'}</span>
              </span>
              <span className="footer-status-item">
                <span className="status-dot" style={{ backgroundColor: '#00ff9d' }}></span>
                <span>PDF Preview: Active</span>
              </span>
            </div>
          </div>
          
          <div className="footer-section">
            <h4>Features</h4>
            <ul className="footer-links">
              <li>5-8 Skills Analysis</li>
              <li>Detailed 5-7 Sentence Summaries</li>
              <li>Batch Processing (10 resumes)</li>
              <li>Original Resume PDF Preview</li>
              <li>Parallel Processing with 3 Keys</li>
              <li>1 Hour Resume Retention</li>
            </ul>
          </div>
          
          <div className="footer-section">
            <h4>Powered By</h4>
            <div className="tech-stack">
              <div className="tech-item">
                <Brain size={14} />
                <span>Groq AI</span>
              </div>
              <div className="tech-item">
                <Cpu size={14} />
                <span>{getModelDisplayName(modelInfo)}</span>
              </div>
              <div className="tech-item">
                <Key size={14} />
                <span>3 API Keys</span>
              </div>
              <div className="tech-item">
                <Zap size={14} />
                <span>Parallel Processing</span>
              </div>
            </div>
          </div>
          
          <div className="footer-section">
            <h4>Quick Links</h4>
            <div className="footer-actions">
              <button onClick={navigateToMain} className="footer-button">
                <Home size={14} />
                <span>New Analysis</span>
              </button>
              {currentView === 'single-results' && analysis && (
                <button onClick={handleDownload} className="footer-button">
                  <DownloadCloud size={14} />
                  <span>Download Report</span>
                </button>
              )}
              {(currentView === 'batch-results' || currentView === 'candidate-detail') && batchAnalysis && (
                <button onClick={handleBatchDownload} className="footer-button">
                  <FileSpreadsheet size={14} />
                  <span>Download Batch Report</span>
                </button>
              )}
              <button onClick={() => window.open('https://www.leadsoc.com/', '_blank')} className="footer-button">
                <ExternalLinkIcon2 size={14} />
                <span>Visit LeadSOC</span>
              </button>
            </div>
          </div>
        </div>
        
        <div className="footer-bottom">
          <div className="footer-copyright">
            <span>© {new Date().getFullYear()} LeadSOC Resume Analyzer Pro</span>
            <span className="version">v2.4.0 • Groq Parallel • PDF Preview</span>
          </div>
          <div className="footer-stats">
            <span className="footer-stat">
              <FileText size={12} />
              <span>{analysis || batchAnalysis ? 'Analyzed' : 'Ready'}</span>
            </span>
            <span className="footer-stat">
              <Cpu size={12} />
              <span>{getModelDisplayName(modelInfo)}</span>
            </span>
            <span className="footer-stat">
              <Key size={12} />
              <span>Keys: {getAvailableKeysCount()}/3</span>
            </span>
          </div>
        </div>
      </footer>

      {/* Debug Panel (only show in development) */}
      {process.env.NODE_ENV === 'development' && (
        <div className="debug-panel glass">
          <div className="debug-header">
            <Settings size={14} />
            <span>Debug Info</span>
          </div>
          <div className="debug-content">
            <div className="debug-item">
              <span>View:</span>
              <span>{currentView}</span>
            </div>
            <div className="debug-item">
              <span>Backend:</span>
              <span>{backendStatus}</span>
            </div>
            <div className="debug-item">
              <span>AI Status:</span>
              <span>{aiStatus}</span>
            </div>
            <div className="debug-item">
              <span>Warmup:</span>
              <span>{groqWarmup ? 'Yes' : 'No'}</span>
            </div>
            <div className="debug-item">
              <span>API Keys:</span>
              <span>{getAvailableKeysCount()}/3</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
