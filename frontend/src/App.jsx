import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Upload, FileText, Briefcase, CheckCircle, XCircle, 
  Download, Loader, TrendingUp, Award, BookOpen, 
  Target, AlertCircle, Sparkles, Star, Zap, User,
  ChevronRight, BarChart3, Clock, Brain, Rocket,
  RefreshCw, Check, X, ExternalLink, BarChart,
  Users, Coffee, DownloadCloud, Info,
  Activity, Thermometer, Cpu, Zap as ZapIcon,
  ArrowLeft, Home, Grid, FileSpreadsheet,
  Calendar, Mail, Phone, MapPin, ThumbsUp,
  AlertTriangle, Lightbulb, Code, Database,
  Server, Terminal, Percent, PieChart, Layers,
  Target as TargetIcon, CircuitBoard, Microchip,
  Code2, Binary, Workflow, Network, LineChart,
  GitMerge, Wrench, Settings, Tool, Hammer,
  Ruler, Building, Factory, Home as HomeIcon,
  CreditCard, DollarSign, Euro, Pound, Coins,
  TrendingDown, ArrowUp, ArrowDown, ArrowRight,
  RotateCcw, RotateCw, Repeat, Sliders,
  Bell, BellOff, Volume2, Headphones, Mic,
  Camera, Film, Music, Play, Pause,
  Maximize2, Minimize, Type, Bold, Italic,
  Palette, Droplet, Sun, Moon, Heart,
  Bookmark, Tag, Folder, FolderOpen,
  Save, Printer, Share, Copy, Paste,
  Clipboard, Edit, Pencil, Brush, Calculator,
  Infinity, Sigma, Plus, Minus, Multiply,
  Equal, ChevronUp, ChevronDown, ChevronLeft,
  CornerUpLeft, CornerUpRight, Expand, Shrink,
  Trash, Archive, Inbox, Package, Box,
  Cube, Circle, Square, Triangle, Crosshair,
  Wifi, Bluetooth, Battery, BatteryCharging,
  BatteryFull, BatteryMedium, BatteryLow,
  Monitor, Smartphone, Tablet, Laptop,
  MessageSquare, Send, Paperclip, Link2,
  Smile, Frown, Meh, Trophy, Medal,
  QuestionMark, HelpCircle, Cloud, CloudOff,
  CloudRain, CloudLightning, Wind, Umbrella,
  Sunrise, Sunset, Watch, Timer, Hourglass,
  Video, Headphones as HeadphonesIcon, Speaker,
  MessageCircle, UserCheck, UserPlus, UserMinus,
  UserCircle, UserSquare, Heartbeat, Flag,
  Radio, Power, Wind as WindIcon,
  Thermometer as ThermometerIcon, CalendarDays,
  Battery as BatteryIcon, Cpu as CpuIcon,
  HardDrive, Router, Tv, RadioTower,
  Satellite, Antenna, Voicemail, MailOpen,
  GitBranch, GitPullRequest, GitCommit,
  BarChart2, Activity as ActivityIcon,
  FileCode, FileImage, FileVideo, FileAudio,
  FileDigit, FileSearch, FolderPlus, FolderMinus,
  FolderTree, FilePlus, FileMinus, FileCheck,
  FolderSync, FolderSearch, FolderKey, FolderLock,
  SaveAll, Share2, ClipboardCheck, ClipboardCopy,
  ClipboardX, Scissors, Cut, Edit2, PenTool,
  PencilLine, Highlighter, Marker, Feather,
  AtSign, Hash, Pi, RootSquare, Function,
  Braces, Brackets, Parentheses, Divide,
  NotEqual, GreaterThan, LessThan, ChevronsUp,
  ChevronsDown, ChevronsLeft, ChevronsRight,
  ArrowUpCircle, ArrowDownCircle, ArrowLeftCircle,
  ArrowRightCircle, ArrowUpLeft, ArrowUpRight,
  ArrowDownLeft, ArrowDownRight, CornerDownLeft,
  CornerDownRight, CornerLeftUp, CornerLeftDown,
  CornerRightUp, CornerRightDown, Move, RotateCw as RotateCwIcon,
  RotateCcw as RotateCcwIcon, Repeat as RepeatIcon,
  RefreshCcw, Undo, Redo, History, Trash2,
  ArchiveRestore, Inbox as InboxIcon, Outbox,
  Cuboid, Cylinder, Cone, Pyramid, Sphere,
  Diameter, Radius, Hexagon, Octagon, Pentagon,
  Scan, QrCode, Barcode, Hdmi, Plug,
  PlugZap, Motherboard, MemoryStick, Database as DatabaseIcon,
  MonitorSmartphone, Desktop, PhoneCall, PhoneForwarded,
  PhoneIncoming, PhoneMissed, PhoneOff, PhoneOutgoing,
  Paperclip as PaperclipIcon, Unlink, Tag as TagIcon,
  UserX, Users as UsersIcon, Frown as FrownIcon,
  Laugh, Angry, Surprised, Confused, Star as StarIcon,
  ThumbsDown, Award as AwardIcon, Crown, Flag as FlagIcon,
  Bookmark as BookmarkIcon, Bell as BellIcon,
  AlertOctagon, XSquare, CheckSquare, Radio as RadioIcon,
  ToggleLeft, ToggleRight, Toggle, PowerOff,
  CloudSnow, CloudDrizzle, CloudFog, Droplets,
  Thermometer as ThermometerIcon2, Watch as WatchIcon,
  Battery as BatteryIcon2, Wifi as WifiIcon,
  Bluetooth as BluetoothIcon, Nfc, Radio as RadioIcon2,
  Tv as TvIcon, Monitor as MonitorIcon, Camera as CameraIcon,
  Video as VideoIcon, Headphones as HeadphonesIcon2,
  Mic as MicIcon, Phone as PhoneIcon, Mail as MailIcon,
  MessageSquare as MessageSquareIcon, Send as SendIcon,
  AtSign as AtSignIcon, Hash as HashIcon, User as UserIcon,
  Smile as SmileIcon, Heart as HeartIcon, ThumbsUp as ThumbsUpIcon,
  Trophy as TrophyIcon, Medal as MedalIcon, Crown as CrownIcon,
  AlertTriangle as AlertTriangleIcon, AlertCircle as AlertCircleIcon,
  CheckCircle as CheckCircleIcon, XCircle as XCircleIcon,
  PlusCircle, MinusCircle, XSquare as XSquareIcon,
  CheckSquare as CheckSquareIcon, Radio as RadioIcon3,
  ToggleLeft as ToggleLeftIcon, ToggleRight as ToggleRightIcon,
  Power as PowerIcon, Moon as MoonIcon, Sun as SunIcon,
  Cloud as CloudIcon, CloudRain as CloudRainIcon,
  CloudLightning as CloudLightningIcon, Wind as WindIcon2,
  Calendar as CalendarIcon, Clock as ClockIcon,
  Battery as BatteryIcon3, Wifi as WifiIcon2,
  Bluetooth as BluetoothIcon2, Monitor as MonitorIcon2,
  Smartphone as SmartphoneIcon, Tablet as TabletIcon,
  Laptop as LaptopIcon, Camera as CameraIcon2,
  Video as VideoIcon2, Headphones as HeadphonesIcon3,
  Mic as MicIcon2, Phone as PhoneIcon2, Mail as MailIcon2,
  MessageSquare as MessageSquareIcon2, Send as SendIcon2,
  AtSign as AtSignIcon2, Hash as HashIcon2, User as UserIcon2,
  Smile as SmileIcon2, Heart as HeartIcon2, ThumbsUp as ThumbsUpIcon2,
  Award as AwardIcon2, Crown as CrownIcon2, AlertTriangle as AlertTriangleIcon2,
  AlertCircle as AlertCircleIcon2, CheckCircle as CheckCircleIcon2,
  XCircle as XCircleIcon2, X as XIcon, PlusCircle as PlusCircleIcon,
  MinusCircle as MinusCircleIcon, CheckSquare as CheckSquareIcon2,
  Radio as RadioIcon4, ToggleLeft as ToggleLeftIcon2,
  ToggleRight as ToggleRightIcon2, Power as PowerIcon2,
  Moon as MoonIcon2, Sun as SunIcon2, Cloud as CloudIcon2,
  CloudRain as CloudRainIcon2, CloudLightning as CloudLightningIcon2,
  Wind as WindIcon3, Calendar as CalendarIcon2, Clock as ClockIcon2,
  Battery as BatteryIcon4, Wifi as WifiIcon3,
  Bluetooth as BluetoothIcon3, Monitor as MonitorIcon3,
  Smartphone as SmartphoneIcon2, Laptop as LaptopIcon2,
  Camera as CameraIcon3, Video as VideoIcon3,
  Headphones as HeadphonesIcon4, Mic as MicIcon3,
  Phone as PhoneIcon3, Mail as MailIcon3,
  MessageSquare as MessageSquareIcon3, Send as SendIcon3,
  AtSign as AtSignIcon3, User as UserIcon3,
  Smile as SmileIcon3, Heart as HeartIcon3,
  ThumbsUp as ThumbsUpIcon3, Award as AwardIcon3,
  Crown as CrownIcon3, AlertCircle as AlertCircleIcon3,
  CheckCircle as CheckCircleIcon3, XCircle as XCircleIcon3,
  PlusCircle as PlusCircleIcon2, MinusCircle as MinusCircleIcon2,
  CheckSquare as CheckSquareIcon3, Radio as RadioIcon5,
  ToggleLeft as ToggleLeftIcon3, ToggleRight as ToggleRightIcon3,
  Power as PowerIcon3, Moon as MoonIcon3, Sun as SunIcon3,
  Cloud as CloudIcon3, CloudRain as CloudRainIcon3,
  CloudLightning as CloudLightningIcon3, Wind as WindIcon4,
  Calendar as CalendarIcon3, Clock as ClockIcon3,
  Battery as BatteryIcon5, Wifi as WifiIcon4,
  Bluetooth as BluetoothIcon4, Monitor as MonitorIcon4,
  Smartphone as SmartphoneIcon3, Laptop as LaptopIcon3,
  Camera as CameraIcon4, Video as VideoIcon4,
  Headphones as HeadphonesIcon5, Mic as MicIcon4,
  Phone as PhoneIcon4, Mail as MailIcon4,
  MessageSquare as MessageSquareIcon4, Send as SendIcon4,
  User as UserIcon4, Smile as SmileIcon4,
  Heart as HeartIcon4, ThumbsUp as ThumbsUpIcon4,
  Award as AwardIcon4, Crown as CrownIcon4,
  AlertCircle as AlertCircleIcon4, CheckCircle as CheckCircleIcon4,
  XCircle as XCircleIcon4, PlusCircle as PlusCircleIcon3,
  MinusCircle as MinusCircleIcon3, CheckSquare as CheckSquareIcon4,
  Radio as RadioIcon6, ToggleLeft as ToggleLeftIcon4,
  ToggleRight as ToggleRightIcon4, Power as PowerIcon4,
  Moon as MoonIcon4, Sun as SunIcon4, Cloud as CloudIcon4,
  CloudRain as CloudRainIcon4, CloudLightning as CloudLightningIcon4,
  Wind as WindIcon5, Calendar as CalendarIcon4, Clock as ClockIcon4,
  Battery as BatteryIcon6, Wifi as WifiIcon5,
  Bluetooth as BluetoothIcon5, Monitor as MonitorIcon5,
  Smartphone as SmartphoneIcon4, Laptop as LaptopIcon4,
  Camera as CameraIcon5, Video as VideoIcon5,
  Headphones as HeadphonesIcon6, Mic as MicIcon5,
  Phone as PhoneIcon5, Mail as MailIcon5,
  MessageSquare as MessageSquareIcon5, Send as SendIcon5,
  User as UserIcon5, Smile as SmileIcon5,
  Heart as HeartIcon5, ThumbsUp as ThumbsUpIcon5,
  Award as AwardIcon5, Crown as CrownIcon5,
  AlertCircle as AlertCircleIcon5, CheckCircle as CheckCircleIcon5,
  XCircle as XCircleIcon5, PlusCircle as PlusCircleIcon4,
  MinusCircle as MinusCircleIcon4, CheckSquare as CheckSquareIcon5,
  Radio as RadioIcon7, ToggleLeft as ToggleLeftIcon5,
  ToggleRight as ToggleRightIcon5, Power as PowerIcon5,
  Moon as MoonIcon5, Sun as SunIcon5, Cloud as CloudIcon5,
  CloudRain as CloudRainIcon5, CloudLightning as CloudLightningIcon5,
  Wind as WindIcon6, Calendar as CalendarIcon5, Clock as ClockIcon5,
  Battery as BatteryIcon7, Wifi as WifiIcon6,
  Bluetooth as BluetoothIcon6, Monitor as MonitorIcon6,
  Smartphone as SmartphoneIcon5, Laptop as LaptopIcon5,
  Camera as CameraIcon6, Video as VideoIcon6,
  Headphones as HeadphonesIcon7, Mic as MicIcon6,
  Phone as PhoneIcon6, Mail as MailIcon6,
  MessageSquare as MessageSquareIcon6, Send as SendIcon6,
  User as UserIcon6, Smile as SmileIcon6,
  Heart as HeartIcon6, ThumbsUp as ThumbsUpIcon6,
  Award as AwardIcon6, Crown as CrownIcon6,
  AlertCircle as AlertCircleIcon6, CheckCircle as CheckCircleIcon6,
  XCircle as XCircleIcon6, PlusCircle as PlusCircleIcon5,
  MinusCircle as MinusCircleIcon5, CheckSquare as CheckSquareIcon6,
  Radio as RadioIcon8, ToggleLeft as ToggleLeftIcon6,
  ToggleRight as ToggleRightIcon6, Power as PowerIcon6,
  Moon as MoonIcon6, Sun as SunIcon6, Cloud as CloudIcon6,
  CloudRain as CloudRainIcon6, CloudLightning as CloudLightningIcon6,
  Wind as WindIcon7, Calendar as CalendarIcon6, Clock as ClockIcon6,
  Battery as BatteryIcon8, Wifi as WifiIcon7,
  Bluetooth as BluetoothIcon7, Monitor as MonitorIcon7,
  Smartphone as SmartphoneIcon6, Laptop as LaptopIcon6,
  Camera as CameraIcon7, Video as VideoIcon7,
  Headphones as HeadphonesIcon8, Mic as MicIcon7,
  Phone as PhoneIcon7, Mail as MailIcon7,
  MessageSquare as MessageSquareIcon7, Send as SendIcon7,
  User as UserIcon7, Smile as SmileIcon7,
  Heart as HeartIcon7, ThumbsUp as ThumbsUpIcon7,
  Award as AwardIcon7, Crown as CrownIcon7,
  AlertCircle as AlertCircleIcon7, CheckCircle as CheckCircleIcon7,
  XCircle as XCircleIcon7, PlusCircle as PlusCircleIcon6,
  MinusCircle as MinusCircleIcon6, CheckSquare as CheckSquareIcon7,
  Radio as RadioIcon9, ToggleLeft as ToggleLeftIcon7,
  ToggleRight as ToggleRightIcon7, Power as PowerIcon7,
  Moon as MoonIcon7, Sun as SunIcon7, Cloud as CloudIcon7,
  CloudRain as CloudRainIcon7, CloudLightning as CloudLightningIcon7,
  Wind as WindIcon8, Calendar as CalendarIcon7, Clock as ClockIcon7,
  Battery as BatteryIcon9, Wifi as WifiIcon8,
  Bluetooth as BluetoothIcon8, Monitor as MonitorIcon8,
  Smartphone as SmartphoneIcon7, Laptop as LaptopIcon7,
  Camera as CameraIcon8, Video as VideoIcon8,
  Headphones as HeadphonesIcon9, Mic as MicIcon8,
  Phone as PhoneIcon8, Mail as MailIcon8,
  MessageSquare as MessageSquareIcon8, Send as SendIcon8,
  User as UserIcon8, Smile as SmileIcon8,
  Heart as HeartIcon8, ThumbsUp as ThumbsUpIcon8,
  Award as AwardIcon8, Crown as CrownIcon8,
  AlertCircle as AlertCircleIcon8, CheckCircle as CheckCircleIcon8,
  XCircle as XCircleIcon8, PlusCircle as PlusCircleIcon7,
  MinusCircle as MinusCircleIcon7, CheckSquare as CheckSquareIcon8,
  Radio as RadioIcon10, ToggleLeft as ToggleLeftIcon8,
  ToggleRight as ToggleRightIcon8, Power as PowerIcon8,
  Moon as MoonIcon8, Sun as SunIcon8, Cloud as CloudIcon8,
  CloudRain as CloudRainIcon8, CloudLightning as CloudLightningIcon8
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
  const [showQuotaPanel, setShowQuotaPanel] = useState(false);
  const [batchMode, setBatchMode] = useState(false);
  const [modelInfo, setModelInfo] = useState(null);
  const [serviceStatus, setServiceStatus] = useState({
    enhancedFallback: true,
    validKeys: 0,
    totalKeys: 0
  });
  
  // View management
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
        setServiceStatus({
          enhancedFallback: healthResponse.data.client_initialized || false,
          validKeys: healthResponse.data.client_initialized ? 1 : 0,
          totalKeys: healthResponse.data.api_key_configured ? 1 : 0
        });
        
        setDeepseekWarmup(healthResponse.data.ai_warmup_complete || false);
        setModelInfo(healthResponse.data.model_info || { 
          name: healthResponse.data.model,
          ats_configuration: healthResponse.data.ats_configuration 
        });
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
        setModelInfo(response.data.model_info || { 
          name: response.data.model,
          ats_configuration: response.data.ats_configuration 
        });
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
    setLoadingMessage('Starting advanced ATS analysis...');

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
        setLoadingMessage('Advanced ATS + DeepSeek AI analysis...');
      } else {
        setLoadingMessage('Weighted Multi-Dimensional ATS analysis...');
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
      
      setLoadingMessage('Advanced ATS analysis complete!');

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
    setLoadingMessage(`Starting batch ATS analysis of ${resumeFiles.length} resumes...`);

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
      setLoadingMessage('Batch ATS analysis complete!');

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
    if (score >= 85) return '#00ff9d'; // Excellent - Bright Green
    if (score >= 75) return '#4cd964'; // Very Good - Green
    if (score >= 65) return '#ffd166'; // Good - Yellow
    if (score >= 55) return '#ff9a3c'; // Fair - Orange
    if (score >= 45) return '#ff6b6b'; // Poor - Red
    return '#ff4757'; // Very Poor - Dark Red
  };

  const getScoreGrade = (score) => {
    if (score >= 90) return 'Exceptional Match 🎯';
    if (score >= 85) return 'Strong Match ✨';
    if (score >= 75) return 'Good Match 👍';
    if (score >= 65) return 'Fair Match 📊';
    if (score >= 55) return 'Borderline 🤔';
    if (score >= 45) return 'Weak Match ⚠️';
    return 'Poor Match ❌';
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
        text: 'Advanced ATS Only', 
        color: '#ffd166', 
        icon: <BarChart3 size={16} />,
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

  const getATSBreakdownComponent = (analysis) => {
    if (!analysis?.ats_score_breakdown) return null;
    
    const breakdown = analysis.ats_score_breakdown;
    const components = [
      { key: 'skills_match', label: 'Skills Match', icon: <CheckCircle size={20} /> },
      { key: 'experience_relevance', label: 'Experience', icon: <Briefcase size={20} /> },
      { key: 'role_alignment', label: 'Role Alignment', icon: <Target size={20} /> },
      { key: 'project_impact', label: 'Project Impact', icon: <Rocket size={20} /> },
      { key: 'resume_quality', label: 'Resume Quality', icon: <FileText size={20} /> }
    ];
    
    return components.map(comp => {
      const component = breakdown[comp.key];
      if (!component) return null;
      
      const score = component.score || 0;
      const weight = (component.weight || 0) * 100;
      const maxScore = weight; // Maximum possible score for this component
      const percentage = maxScore > 0 ? (score / maxScore) * 100 : 0;
      
      return {
        ...comp,
        score: score.toFixed(1),
        weight: `${weight.toFixed(0)}%`,
        percentage: percentage.toFixed(0),
        color: getScoreColor(percentage),
        details: component.details || {}
      };
    }).filter(Boolean);
  };

  const renderATSScoreRadar = (analysis) => {
    if (!analysis?.ats_score_breakdown) return null;
    
    const breakdown = getATSBreakdownComponent(analysis);
    if (!breakdown || breakdown.length === 0) return null;
    
    return (
      <div className="ats-radar-chart">
        <div className="radar-grid">
          {breakdown.map((comp, index) => {
            const angle = (index * 72) * (Math.PI / 180); // 72 degrees between 5 components
            const radius = 80; // Base radius
            const valueRadius = radius * (parseInt(comp.percentage) / 100);
            
            const x = 100 + Math.cos(angle) * radius;
            const y = 100 + Math.sin(angle) * radius;
            const valueX = 100 + Math.cos(angle) * valueRadius;
            const valueY = 100 + Math.sin(angle) * valueRadius;
            
            return (
              <g key={comp.key}>
                {/* Grid line */}
                <line 
                  x1="100" y1="100" 
                  x2={x} y2={y} 
                  stroke="rgba(255, 255, 255, 0.1)" 
                  strokeWidth="1"
                />
                {/* Value point */}
                <circle 
                  cx={valueX} 
                  cy={valueY} 
                  r="4" 
                  fill={comp.color}
                  stroke="#fff"
                  strokeWidth="1.5"
                />
                {/* Component label */}
                <text 
                  x={x + (Math.cos(angle) * 20)} 
                  y={y + (Math.sin(angle) * 20)} 
                  textAnchor="middle"
                  fill="#fff"
                  fontSize="10"
                  fontWeight="600"
                >
                  {comp.label}
                </text>
                {/* Score label */}
                <text 
                  x={valueX} 
                  y={valueY - 8} 
                  textAnchor="middle"
                  fill={comp.color}
                  fontSize="9"
                  fontWeight="700"
                >
                  {comp.score}
                </text>
              </g>
            );
          })}
          
          {/* Connect value points */}
          <polygon 
            points={breakdown.map((comp, index) => {
              const angle = (index * 72) * (Math.PI / 180);
              const radius = 80 * (parseInt(comp.percentage) / 100);
              const x = 100 + Math.cos(angle) * radius;
              const y = 100 + Math.sin(angle) * radius;
              return `${x},${y}`;
            }).join(' ')}
            fill="rgba(0, 255, 157, 0.1)"
            stroke="#00ff9d"
            strokeWidth="1.5"
            strokeOpacity="0.7"
          />
        </div>
      </div>
    );
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
    if (!modelInfo) return 'Advanced ATS Algorithm';
    if (typeof modelInfo === 'string') return modelInfo;
    return modelInfo.name || 'Advanced ATS Algorithm';
  };

  // Render functions for different views
  const renderMainView = () => (
    <div className="upload-section">
      <div className="section-header">
        <h2>Advanced ATS Resume Analysis</h2>
        <p>Weighted Multi-Dimensional Scoring with VLSI/CS Domain Expertise</p>
        <div className="service-status">
          <span className="status-badge backend">
            {backendStatusInfo.icon} {backendStatusInfo.text}
          </span>
          <span className="status-badge ai">
            {aiStatusInfo.icon} {aiStatusInfo.text}
          </span>
          <span className="status-badge always-active">
            <ZapIcon size={14} /> Advanced ATS Scoring
          </span>
          {modelInfo?.ats_configuration && (
            <span className="status-badge model">
              <Cpu size={14} /> {modelInfo.ats_configuration.method.replace(/_/g, ' ').toUpperCase()}
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
              <span>Advanced ATS Scoring</span>
            </div>
            <div className="stat">
              <div className="stat-icon">
                <Cpu size={14} />
              </div>
              <span>Weighted Multi-Dimensional</span>
            </div>
            <div className="stat">
              <div className="stat-icon">
                <Activity size={14} />
              </div>
              <span>VLSI/CS Domain Focus</span>
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

      {/* Loading Progress Bar */}
      {(loading || batchLoading) && (
        <div className="loading-section glass">
          <div className="loading-container">
            <div className="loading-header">
              <Loader className="spinner" />
              <h3>{batchMode ? 'Batch ATS Analysis' : 'Advanced ATS Analysis'}</h3>
            </div>
            
            <div className="progress-container">
              <div className="progress-bar" style={{ width: `${batchMode ? batchProgress : progress}%` }}></div>
            </div>
            
            <div className="loading-text">
              <span className="loading-message">{loadingMessage}</span>
              <span className="loading-subtext">
                {batchMode 
                  ? `Processing ${resumeFiles.length} resume(s) with Weighted Multi-Dimensional ATS...` 
                  : `Using Advanced ATS Algorithm...`}
              </span>
            </div>
            
            <div className="progress-stats">
              <span>{Math.round(batchMode ? batchProgress : progress)}%</span>
              <span>•</span>
              <span>Backend: {backendStatus === 'ready' ? 'Active' : 'Waking...'}</span>
              <span>•</span>
              <span>ATS: {aiStatus === 'available' ? 'Enhanced 🧠' : 'Advanced Only'}</span>
              {modelInfo?.ats_configuration && (
                <>
                  <span>•</span>
                  <span>Method: {modelInfo.ats_configuration.method.replace(/_/g, ' ')}</span>
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
              <span>Advanced Weighted ATS Scoring evaluates 5 dimensions: Skills, Experience, Role, Projects, Resume</span>
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
                    ? `${resumeFiles.length} resume(s) • Advanced ATS • Batch` 
                    : `Advanced ATS • Weighted Scoring`}
                </span>
              </div>
            </div>
            <ChevronRight size={20} />
          </>
        )}
      </button>

      {/* ATS Scoring Explanation */}
      <div className="ats-explanation glass">
        <div className="explanation-header">
          <BarChart3 size={24} />
          <h3>Advanced ATS Scoring System</h3>
        </div>
        <div className="explanation-content">
          <div className="scoring-grid">
            <div className="scoring-component">
              <div className="component-header">
                <div className="component-icon" style={{ background: 'rgba(0, 255, 157, 0.1)' }}>
                  <CheckCircle size={20} color="#00ff9d" />
                </div>
                <div className="component-title">
                  <h4>Skills Match (35%)</h4>
                  <p>Context-aware skill verification</p>
                </div>
              </div>
              <ul className="component-features">
                <li>✓ Required skills detection</li>
                <li>✓ Context verification</li>
                <li>✓ Partial skill scoring</li>
                <li>✓ Tool vs experience distinction</li>
              </ul>
            </div>
            
            <div className="scoring-component">
              <div className="component-header">
                <div className="component-icon" style={{ background: 'rgba(255, 209, 102, 0.1)' }}>
                  <Briefcase size={20} color="#ffd166" />
                </div>
                <div className="component-title">
                  <h4>Experience (25%)</h4>
                  <p>Seniority and relevance alignment</p>
                </div>
              </div>
              <ul className="component-features">
                <li>✓ Years of experience</li>
                <li>✓ Seniority matching</li>
                <li>✓ Domain relevance</li>
                <li>✓ Industry alignment</li>
              </ul>
            </div>
            
            <div className="scoring-component">
              <div className="component-header">
                <div className="component-icon" style={{ background: 'rgba(255, 107, 107, 0.1)' }}>
                  <Target size={20} color="#ff6b6b" />
                </div>
                <div className="component-title">
                  <h4>Role Alignment (20%)</h4>
                  <p>VLSI/CS domain expertise</p>
                </div>
              </div>
              <ul className="component-features">
                <li>✓ Responsibility matching</li>
                <li>✓ Domain-specific skills</li>
                <li>✓ Project relevance</li>
                <li>✓ Career path alignment</li>
              </ul>
            </div>
            
            <div className="scoring-component">
              <div className="component-header">
                <div className="component-icon" style={{ background: 'rgba(147, 51, 234, 0.1)' }}>
                  <Rocket size={20} color="#9333ea" />
                </div>
                <div className="component-title">
                  <h4>Project Impact (15%)</h4>
                  <p>Complexity and measurable results</p>
                </div>
              </div>
              <ul className="component-features">
                <li>✓ Project complexity</li>
                <li>✓ Quantifiable achievements</li>
                <li>✓ Leadership evidence</li>
                <li>✓ Technical depth</li>
              </ul>
            </div>
            
            <div className="scoring-component">
              <div className="component-header">
                <div className="component-icon" style={{ background: 'rgba(59, 130, 246, 0.1)' }}>
                  <FileText size={20} color="#3b82f6" />
                </div>
                <div className="component-title">
                  <h4>Resume Quality (5%)</h4>
                  <p>Structure and presentation</p>
                </div>
              </div>
              <ul className="component-features">
                <li>✓ Professional structure</li>
                <li>✓ Action-oriented language</li>
                <li>✓ Quantifiable metrics</li>
                <li>✓ Clarity and conciseness</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Tips Section */}
      <div className="tips-section">
        {batchMode ? (
          <>
            <div className="tip">
              <Brain size={16} />
              <span>Advanced Weighted ATS Scoring across 5 dimensions</span>
            </div>
            <div className="tip">
              <Activity size={16} />
              <span>Process up to 10 resumes in a single batch with ranked results</span>
            </div>
            <div className="tip">
              <TrendingUp size={16} />
              <span>Candidates ranked by comprehensive ATS score with detailed breakdown</span>
            </div>
            <div className="tip">
              <Download size={16} />
              <span>Download comprehensive Excel reports with ATS score breakdowns</span>
            </div>
          </>
        ) : (
          <>
            <div className="tip">
              <Brain size={16} />
              <span>Weighted Multi-Dimensional ATS Scoring (35-25-20-15-5)</span>
            </div>
            <div className="tip">
              <CircuitBoard size={16} />
              <span>VLSI/CS domain expertise detection and evaluation</span>
            </div>
            <div className="tip">
              <Activity size={16} />
              <span>Context-aware skill matching with verification</span>
            </div>
            <div className="tip">
              <Target size={16} />
              <span>Seniority alignment and role relevance assessment</span>
            </div>
          </>
        )}
      </div>
    </div>
  );

  const renderSingleAnalysisView = () => {
    if (!analysis) return null;

    const breakdown = getATSBreakdownComponent(analysis);

    return (
      <div className="results-section">
        {/* Navigation Header */}
        <div className="navigation-header glass">
          <button onClick={navigateToMain} className="back-button">
            <ArrowLeft size={20} />
            <span>New Analysis</span>
          </button>
          <div className="navigation-title">
            <h2>🧠 Advanced ATS Analysis Results</h2>
            <p>{analysis.candidate_name} • {analysis.scoring_method?.replace(/_/g, ' ').toUpperCase() || 'ADVANCED ATS'}</p>
          </div>
          <div className="navigation-actions">
            <button className="download-report-btn" onClick={handleDownload}>
              <DownloadCloud size={18} />
              <span>Download ATS Report</span>
            </button>
          </div>
        </div>

        {/* Candidate Header with ATS Score */}
        <div className="analysis-header">
          <div className="candidate-info">
            <div className="candidate-avatar">
              <User size={24} />
            </div>
            <div>
              <h2 className="candidate-name">{analysis.candidate_name}</h2>
              <div className="candidate-meta">
                <span className="analysis-date">
                  <Calendar size={14} />
                  {new Date().toLocaleDateString('en-US', { 
                    weekday: 'long', 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric' 
                  })}
                </span>
                <span className="file-info">
                  <Cpu size={14} />
                  Scoring: {analysis.scoring_method?.replace(/_/g, ' ') || 'Advanced Weighted ATS'}
                </span>
                {analysis.scoring_version && (
                  <span className="file-info">
                    <Code size={14} />
                    Version: {analysis.scoring_version}
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
                  <div className="score-label">ATS SCORE</div>
                </div>
              </div>
            </div>
            <div className="score-info">
              <h3 className="score-grade">{getScoreGrade(analysis.overall_score)}</h3>
              <p className="score-description">
                Based on weighted multi-dimensional evaluation across 5 key areas
              </p>
              <div className="score-meta">
                <span className="meta-item">
                  <Brain size={12} />
                  Method: {analysis.scoring_method?.replace(/_/g, ' ') || 'Advanced ATS'}
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

        {/* ATS Score Breakdown */}
        <div className="section-title">
          <h2>ATS Score Breakdown</h2>
          <p>Weighted Multi-Dimensional Evaluation</p>
        </div>
        
        {breakdown && breakdown.length > 0 && (
          <div className="ats-breakdown-container glass">
            <div className="breakdown-header">
              <div className="breakdown-title">
                <BarChart3 size={24} />
                <div>
                  <h3>Component Scores</h3>
                  <p className="breakdown-subtitle">Weighted evaluation across 5 dimensions</p>
                </div>
              </div>
              <div className="breakdown-total">
                <span className="total-label">Total ATS Score</span>
                <span className="total-value" style={{ color: getScoreColor(analysis.overall_score) }}>
                  {analysis.overall_score}/100
                </span>
              </div>
            </div>
            
            <div className="breakdown-content">
              <div className="breakdown-grid">
                {breakdown.map((component, index) => (
                  <div key={component.key} className="breakdown-item">
                    <div className="breakdown-item-header">
                      <div className="component-icon-wrapper" style={{ color: component.color }}>
                        {component.icon}
                      </div>
                      <div className="component-info">
                        <h4 className="component-name">{component.label}</h4>
                        <span className="component-weight">Weight: {component.weight}</span>
                      </div>
                      <div className="component-score" style={{ color: component.color }}>
                        <span className="score-value">{component.score}</span>
                        <span className="score-max">/{component.weight.replace('%', '')}</span>
                      </div>
                    </div>
                    
                    <div className="progress-bar-container">
                      <div 
                        className="progress-bar-fill" 
                        style={{ 
                          width: `${component.percentage}%`,
                          background: component.color
                        }}
                      ></div>
                      <div className="progress-label">{component.percentage}% of weight achieved</div>
                    </div>
                    
                    <div className="component-details">
                      {component.key === 'skills_match' && component.details && (
                        <div className="detail-stats">
                          <span className="stat">
                            <CheckCircle size={12} />
                            {component.details.matched_skills?.length || 0} matched
                          </span>
                          <span className="stat">
                            <XCircle size={12} />
                            {component.details.missing_skills?.length || 0} missing
                          </span>
                          {component.details.context_verified && (
                            <span className="stat">
                              <CheckCircle size={12} />
                              {component.details.context_verified} verified with context
                            </span>
                          )}
                        </div>
                      )}
                      
                      {component.key === 'experience_relevance' && component.details && (
                        <div className="detail-stats">
                          {component.details.actual_years && (
                            <span className="stat">
                              <Briefcase size={12} />
                              {component.details.actual_years} years experience
                            </span>
                          )}
                          {component.details.seniority_match && (
                            <span className="stat success">
                              <CheckCircle size={12} />
                              Seniority match
                            </span>
                          )}
                          {component.details.bonuses && component.details.bonuses.length > 0 && (
                            <span className="stat info">
                              <Award size={12} />
                              {component.details.bonuses.length} bonuses
                            </span>
                          )}
                        </div>
                      )}
                      
                      {component.key === 'project_impact' && component.details && (
                        <div className="detail-stats">
                          <span className="stat">
                            <Rocket size={12} />
                            {component.details.project_count || 0} projects
                          </span>
                          {component.details.has_star_format && (
                            <span className="stat success">
                              <Star size={12} />
                              STAR format
                            </span>
                          )}
                          {component.details.quality_score && (
                            <span className="stat">
                              <TrendingUp size={12} />
                              Quality: {component.details.quality_score}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Radar Chart Visualization */}
              <div className="radar-container">
                <div className="radar-header">
                  <Target size={20} />
                  <h4>ATS Score Radar</h4>
                </div>
                <div className="radar-chart-wrapper">
                  <svg width="200" height="200" viewBox="0 0 200 200" className="radar-svg">
                    {/* Background circles */}
                    <circle cx="100" cy="100" r="80" fill="rgba(255,255,255,0.02)" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
                    <circle cx="100" cy="100" r="60" fill="rgba(255,255,255,0.02)" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
                    <circle cx="100" cy="100" r="40" fill="rgba(255,255,255,0.02)" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
                    <circle cx="100" cy="100" r="20" fill="rgba(255,255,255,0.02)" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
                    
                    {/* Radar plot */}
                    {renderATSScoreRadar(analysis)}
                    
                    {/* Center point */}
                    <circle cx="100" cy="100" r="3" fill="#fff" />
                  </svg>
                  <div className="radar-legend">
                    {breakdown.map((comp, index) => (
                      <div key={comp.key} className="legend-item">
                        <div className="legend-color" style={{ background: comp.color }}></div>
                        <span className="legend-label">{comp.label}</span>
                        <span className="legend-value" style={{ color: comp.color }}>{comp.score}</span>
                      </div>
                    ))}
                  </div>
                </div>
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
            <Award size={28} style={{ color: getScoreColor(analysis.overall_score) }} />
            <div>
              <h3>ATS Recommendation</h3>
              <p className="recommendation-subtitle">
                {analysis.ai_model || 'Advanced ATS Algorithm'} • Weighted Multi-Dimensional Scoring
              </p>
            </div>
          </div>
          <div className="recommendation-content">
            <p className="recommendation-text">{analysis.recommendation}</p>
            <div className="confidence-badge">
              <Brain size={16} />
              <span>Advanced ATS Analysis</span>
            </div>
          </div>
        </div>

        {/* Skills Analysis */}
        <div className="section-title">
          <h2>Skills Analysis</h2>
          <p>Detailed breakdown of matched and missing skills with context verification</p>
        </div>
        
        <div className="skills-grid">
          <div className="skills-card glass success">
            <div className="skills-card-header">
              <div className="skills-icon success">
                <CheckCircle size={24} />
              </div>
              <div className="skills-header-content">
                <h3>Matched Skills</h3>
                <p className="skills-subtitle">Verified with practical context</p>
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
                    {skill.includes('(verified with context)') && (
                      <span className="skill-badge verified">Verified</span>
                    )}
                    {skill.includes('(mentioned)') && (
                      <span className="skill-badge mentioned">Mentioned</span>
                    )}
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
                <p className="skills-subtitle">Required but not found in resume</p>
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
                    <span className="skill-badge missing">Missing</span>
                  </li>
                ))}
                {(!analysis.skills_missing || analysis.skills_missing.length === 0) && (
                  <li className="no-items success-text">All required skills are present!</li>
                )}
              </ul>
            </div>
          </div>
        </div>

        {/* Domain Expertise */}
        {(analysis.ats_score_breakdown?.role_alignment?.details?.matches || 
          analysis.ats_score_breakdown?.role_alignment?.details?.mismatches) && (
          <>
            <div className="section-title">
              <h2>Domain Expertise</h2>
              <p>VLSI and Computer Science domain assessment</p>
            </div>
            
            <div className="domain-expertise-container glass">
              <div className="domain-header">
                <CircuitBoard size={24} />
                <div>
                  <h3>Technical Domain Assessment</h3>
                  <p className="domain-subtitle">Specialized evaluation for VLSI and CS roles</p>
                </div>
              </div>
              
              <div className="domain-content">
                {analysis.ats_score_breakdown.role_alignment.details.matches && 
                 analysis.ats_score_breakdown.role_alignment.details.matches.length > 0 && (
                  <div className="domain-section success">
                    <div className="domain-section-header">
                      <CheckCircle size={18} />
                      <h4>Domain Strengths</h4>
                    </div>
                    <div className="domain-list">
                      {analysis.ats_score_breakdown.role_alignment.details.matches.map((match, index) => (
                        <div key={index} className="domain-item">
                          <span className="domain-text">{match}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {analysis.ats_score_breakdown.role_alignment.details.mismatches && 
                 analysis.ats_score_breakdown.role_alignment.details.mismatches.length > 0 && (
                  <div className="domain-section warning">
                    <div className="domain-section-header">
                      <AlertCircle size={18} />
                      <h4>Domain Gaps</h4>
                    </div>
                    <div className="domain-list">
                      {analysis.ats_score_breakdown.role_alignment.details.mismatches.map((mismatch, index) => (
                        <div key={index} className="domain-item">
                          <span className="domain-text">{mismatch}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {analysis.ats_score_breakdown.experience_relevance?.details?.bonuses && 
                 analysis.ats_score_breakdown.experience_relevance.details.bonuses.length > 0 && (
                  <div className="domain-section info">
                    <div className="domain-section-header">
                      <Award size={18} />
                      <h4>Experience Bonuses</h4>
                    </div>
                    <div className="domain-list">
                      {analysis.ats_score_breakdown.experience_relevance.details.bonuses.map((bonus, index) => (
                        <div key={index} className="domain-item">
                          <span className="domain-text">{bonus}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* Summary Section */}
        <div className="section-title">
          <h2>Profile Summary</h2>
          <p>Comprehensive assessment based on weighted ATS evaluation</p>
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
              {analysis.ats_score_breakdown?.experience_relevance?.details && (
                <div className="summary-footer">
                  <span className="summary-tag">
                    <Target size={14} />
                    {analysis.ats_score_breakdown.experience_relevance.details.actual_years || 0} years experience
                  </span>
                  <span className="summary-tag">
                    <TrendingUp size={14} />
                    {analysis.ats_score_breakdown.experience_relevance.details.seniority_match ? 'Seniority match' : 'Seniority mismatch'}
                  </span>
                </div>
              )}
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
              <p className="detailed-summary">{analysis.education_summary || "Educational background requires analysis."}</p>
              {analysis.ats_score_breakdown?.resume_quality?.details && (
                <div className="summary-footer">
                  <span className="summary-tag">
                    <FileText size={14} />
                    {analysis.ats_score_breakdown.resume_quality.details.sections_found || 0} sections found
                  </span>
                  <span className="summary-tag">
                    <BarChart3 size={14} />
                    {analysis.ats_score_breakdown.resume_quality.details.metrics_count || 0} metrics
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Insights Section */}
        <div className="section-title">
          <h2>Insights & Recommendations</h2>
          <p>Personalized suggestions based on ATS score analysis</p>
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
                <p className="insight-subtitle">Opportunities to improve ATS score</p>
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
              <h3>Analysis Details</h3>
              <p className="ai-details-subtitle">Technical information about this ATS analysis</p>
            </div>
          </div>
          <div className="ai-details-content">
            <div className="ai-detail-item">
              <span className="detail-label">Scoring Method:</span>
              <span className="detail-value">{analysis.scoring_method?.replace(/_/g, ' ') || 'Advanced Weighted ATS'}</span>
            </div>
            <div className="ai-detail-item">
              <span className="detail-label">Scoring Version:</span>
              <span className="detail-value">{analysis.scoring_version || '2.0'}</span>
            </div>
            <div className="ai-detail-item">
              <span className="detail-label">AI Provider:</span>
              <span className="detail-value">{analysis.ai_provider || 'Advanced ATS Algorithm'}</span>
            </div>
            <div className="ai-detail-item">
              <span className="detail-label">AI Model:</span>
              <span className="detail-value">{analysis.ai_model || 'Advanced ATS Algorithm'}</span>
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
              <span className="detail-label">AI Status:</span>
              <span className="detail-value" style={{ 
                color: analysis.ai_status?.includes('Warmed') ? '#00ff9d' : '#ffd166' 
              }}>
                {analysis.ai_status || 'N/A'}
              </span>
            </div>
          </div>
        </div>

        {/* Action Section */}
        <div className="action-section glass">
          <div className="action-content">
            <h3>Advanced ATS Analysis Complete</h3>
            <p>Download detailed Excel report with ATS score breakdown or start a new analysis</p>
          </div>
          <div className="action-buttons">
            <button className="download-button" onClick={handleDownload}>
              <DownloadCloud size={20} />
              <span>Download ATS Report</span>
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
          <h2>🧠 Batch ATS Analysis Results</h2>
          <p>{batchAnalysis?.successfully_analyzed || 0} resumes analyzed with Weighted Multi-Dimensional ATS</p>
        </div>
        <div className="navigation-actions">
          <button className="download-report-btn" onClick={handleBatchDownload}>
            <DownloadCloud size={18} />
            <span>Download Full ATS Report</span>
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
            <BarChart3 size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">Advanced ATS</div>
            <div className="stat-label">Scoring Method</div>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon warning">
            <Brain size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{batchAnalysis?.ai_provider?.includes('ats') ? 'ATS + AI' : 'Advanced ATS'}</div>
            <div className="stat-label">AI Provider</div>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(147, 51, 234, 0.1)', color: '#9333ea' }}>
            <CircuitBoard size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">VLSI/CS</div>
            <div className="stat-label">Domain Focus</div>
          </div>
        </div>
      </div>

      {/* ATS Scoring Summary */}
      {batchAnalysis?.analyses && batchAnalysis.analyses.length > 0 && (
        <div className="ats-summary-container glass">
          <div className="ats-summary-header">
            <PieChart size={24} />
            <div>
              <h3>Batch ATS Score Distribution</h3>
              <p className="summary-subtitle">Weighted Multi-Dimensional scoring across all candidates</p>
            </div>
          </div>
          
          <div className="score-distribution">
            <div className="distribution-row">
              <span className="distribution-label">Excellent (85-100)</span>
              <div className="distribution-bar">
                <div 
                  className="distribution-fill excellent"
                  style={{ 
                    width: `${(batchAnalysis.analyses.filter(a => a.overall_score >= 85).length / batchAnalysis.analyses.length) * 100}%`
                  }}
                ></div>
              </div>
              <span className="distribution-count">
                {batchAnalysis.analyses.filter(a => a.overall_score >= 85).length}
              </span>
            </div>
            
            <div className="distribution-row">
              <span className="distribution-label">Good (75-84)</span>
              <div className="distribution-bar">
                <div 
                  className="distribution-fill good"
                  style={{ 
                    width: `${(batchAnalysis.analyses.filter(a => a.overall_score >= 75 && a.overall_score < 85).length / batchAnalysis.analyses.length) * 100}%`
                  }}
                ></div>
              </div>
              <span className="distribution-count">
                {batchAnalysis.analyses.filter(a => a.overall_score >= 75 && a.overall_score < 85).length}
              </span>
            </div>
            
            <div className="distribution-row">
              <span className="distribution-label">Fair (65-74)</span>
              <div className="distribution-bar">
                <div 
                  className="distribution-fill fair"
                  style={{ 
                    width: `${(batchAnalysis.analyses.filter(a => a.overall_score >= 65 && a.overall_score < 75).length / batchAnalysis.analyses.length) * 100}%`
                  }}
                ></div>
              </div>
              <span className="distribution-count">
                {batchAnalysis.analyses.filter(a => a.overall_score >= 65 && a.overall_score < 75).length}
              </span>
            </div>
            
            <div className="distribution-row">
              <span className="distribution-label">Borderline (55-64)</span>
              <div className="distribution-bar">
                <div 
                  className="distribution-fill borderline"
                  style={{ 
                    width: `${(batchAnalysis.analyses.filter(a => a.overall_score >= 55 && a.overall_score < 65).length / batchAnalysis.analyses.length) * 100}%`
                  }}
                ></div>
              </div>
              <span className="distribution-count">
                {batchAnalysis.analyses.filter(a => a.overall_score >= 55 && a.overall_score < 65).length}
              </span>
            </div>
            
            <div className="distribution-row">
              <span className="distribution-label">Weak (0-54)</span>
              <div className="distribution-bar">
                <div 
                  className="distribution-fill weak"
                  style={{ 
                    width: `${(batchAnalysis.analyses.filter(a => a.overall_score < 55).length / batchAnalysis.analyses.length) * 100}%`
                  }}
                ></div>
              </div>
              <span className="distribution-count">
                {batchAnalysis.analyses.filter(a => a.overall_score < 55).length}
              </span>
            </div>
          </div>
          
          <div className="summary-stats">
            <div className="summary-stat">
              <span className="stat-label">Average ATS Score</span>
              <span className="stat-value" style={{ color: getScoreColor(batchAnalysis.analyses.reduce((acc, a) => acc + a.overall_score, 0) / batchAnalysis.analyses.length) }}>
                {(batchAnalysis.analyses.reduce((acc, a) => acc + a.overall_score, 0) / batchAnalysis.analyses.length).toFixed(1)}
              </span>
            </div>
            <div className="summary-stat">
              <span className="stat-label">Highest Score</span>
              <span className="stat-value" style={{ color: getScoreColor(Math.max(...batchAnalysis.analyses.map(a => a.overall_score))) }}>
                {Math.max(...batchAnalysis.analyses.map(a => a.overall_score)).toFixed(1)}
              </span>
            </div>
            <div className="summary-stat">
              <span className="stat-label">Lowest Score</span>
              <span className="stat-value" style={{ color: getScoreColor(Math.min(...batchAnalysis.analyses.map(a => a.overall_score))) }}>
                {Math.min(...batchAnalysis.analyses.map(a => a.overall_score)).toFixed(1)}
              </span>
            </div>
            <div className="summary-stat">
              <span className="stat-label">Score Range</span>
              <span className="stat-value">
                {(Math.max(...batchAnalysis.analyses.map(a => a.overall_score)) - Math.min(...batchAnalysis.analyses.map(a => a.overall_score))).toFixed(1)}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Candidates Ranking */}
      <div className="section-title">
        <h2>Candidate Rankings</h2>
        <p>Sorted by ATS Score (Highest to Lowest) • Weighted Multi-Dimensional ATS</p>
      </div>
      
      <div className="batch-results-grid">
        {batchAnalysis?.analyses?.map((candidate, index) => {
          const breakdown = getATSBreakdownComponent(candidate);
          
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
                      {candidate.scoring_method && (
                        <span className="scoring-method">
                          <Cpu size={12} />
                          {candidate.scoring_method.replace(/_/g, ' ')}
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
                
                {/* ATS Component Scores */}
                {breakdown && breakdown.length > 0 && (
                  <div className="ats-components-preview">
                    <div className="components-grid">
                      {breakdown.slice(0, 3).map((comp, idx) => (
                        <div key={idx} className="component-preview">
                          <div className="component-name">{comp.label}</div>
                          <div className="component-score" style={{ color: comp.color }}>
                            {comp.score}<span className="component-weight">/{comp.weight.replace('%', '')}</span>
                          </div>
                          <div className="component-progress">
                            <div 
                              className="component-progress-fill" 
                              style={{ 
                                width: `${comp.percentage}%`,
                                background: comp.color
                              }}
                            ></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                <div className="skills-preview">
                  <div className="skills-section">
                    <div className="skills-header">
                      <CheckCircle size={14} />
                      <span>Matched Skills ({candidate.skills_matched?.length || 0})</span>
                    </div>
                    <div className="skills-list">
                      {candidate.skills_matched?.slice(0, 3).map((skill, idx) => (
                        <span key={idx} className="skill-tag success">{skill.replace(' (verified with context)', '').replace(' (mentioned)', '')}</span>
                      ))}
                      {candidate.skills_matched?.length > 3 && (
                        <span className="more-skills">+{candidate.skills_matched.length - 3} more</span>
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
                  View ATS Breakdown
                  <ChevronRight size={16} />
                </button>
                {candidate.analysis_id && (
                  <button 
                    className="download-individual-btn"
                    onClick={() => handleIndividualDownload(candidate.analysis_id)}
                    title="Download individual ATS report"
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
          <h3>Batch ATS Analysis Complete</h3>
          <p>Download comprehensive Excel report with detailed ATS score breakdowns</p>
        </div>
        <div className="action-buttons">
          <button className="download-button" onClick={handleBatchDownload}>
            <DownloadCloud size={20} />
            <span>Download Full ATS Report</span>
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

    const breakdown = getATSBreakdownComponent(candidate);

    return (
      <div className="results-section">
        {/* Navigation Header */}
        <div className="navigation-header glass">
          <button onClick={navigateBack} className="back-button">
            <ArrowLeft size={20} />
            <span>Back to Rankings</span>
          </button>
          <div className="navigation-title">
            <h2>Candidate ATS Details</h2>
            <p>Rank #{candidate.rank} • {candidate.candidate_name} • {candidate.scoring_method?.replace(/_/g, ' ').toUpperCase() || 'ADVANCED ATS'}</p>
          </div>
          <div className="navigation-actions">
            {candidate.analysis_id && (
              <button 
                className="download-report-btn" 
                onClick={() => handleIndividualDownload(candidate.analysis_id)}
              >
                <FileDown size={18} />
                <span>Download ATS Report</span>
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
                  <Calendar size={14} />
                  Rank: #{candidate.rank}
                </span>
                <span className="file-info">
                  <FileText size={14} />
                  {candidate.filename} • {candidate.file_size}
                </span>
                {candidate.scoring_method && (
                  <span className="file-info">
                    <Cpu size={14} />
                    {candidate.scoring_method.replace(/_/g, ' ')}
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
                  <div className="score-label">ATS SCORE</div>
                </div>
              </div>
            </div>
            <div className="score-info">
              <h3 className="score-grade">{getScoreGrade(candidate.overall_score)}</h3>
              <p className="score-description">
                Based on weighted multi-dimensional evaluation
              </p>
              <div className="score-meta">
                <span className="meta-item">
                  <BarChart3 size={12} />
                  Method: {candidate.scoring_method?.replace(/_/g, ' ') || 'Advanced ATS'}
                </span>
                <span className="meta-item">
                  <Brain size={12} />
                  Provider: {candidate.ai_provider || 'Advanced ATS Algorithm'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ATS Score Breakdown */}
        {breakdown && breakdown.length > 0 && (
          <div className="ats-breakdown-container glass">
            <div className="breakdown-header">
              <div className="breakdown-title">
                <BarChart3 size={24} />
                <div>
                  <h3>ATS Score Breakdown</h3>
                  <p className="breakdown-subtitle">Weighted evaluation across 5 dimensions</p>
                </div>
              </div>
              <div className="breakdown-total">
                <span className="total-label">Total ATS Score</span>
                <span className="total-value" style={{ color: getScoreColor(candidate.overall_score) }}>
                  {candidate.overall_score}/100
                </span>
              </div>
            </div>
            
            <div className="breakdown-content">
              <div className="breakdown-grid">
                {breakdown.map((component, index) => (
                  <div key={component.key} className="breakdown-item">
                    <div className="breakdown-item-header">
                      <div className="component-icon-wrapper" style={{ color: component.color }}>
                        {component.icon}
                      </div>
                      <div className="component-info">
                        <h4 className="component-name">{component.label}</h4>
                        <span className="component-weight">Weight: {component.weight}</span>
                      </div>
                      <div className="component-score" style={{ color: component.color }}>
                        <span className="score-value">{component.score}</span>
                        <span className="score-max">/{component.weight.replace('%', '')}</span>
                      </div>
                    </div>
                    
                    <div className="progress-bar-container">
                      <div 
                        className="progress-bar-fill" 
                        style={{ 
                          width: `${component.percentage}%`,
                          background: component.color
                        }}
                      ></div>
                      <div className="progress-label">{component.percentage}% of weight achieved</div>
                    </div>
                  </div>
                ))}
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
            <Award size={28} style={{ color: getScoreColor(candidate.overall_score) }} />
            <div>
              <h3>ATS Recommendation</h3>
              <p className="recommendation-subtitle">
                {candidate.ai_model || 'Advanced ATS Algorithm'} • Batch Processing
              </p>
            </div>
          </div>
          <div className="recommendation-content">
            <p className="recommendation-text">{candidate.recommendation}</p>
            <div className="confidence-badge">
              <Brain size={16} />
              <span>Advanced ATS Analysis</span>
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
                <p className="skills-subtitle">Found in resume</p>
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
                <p className="skills-subtitle">Suggested to learn</p>
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
          <p>Insights extracted from resume</p>
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

        {/* Action Section */}
        <div className="action-section glass">
          <div className="action-content">
            <h3>Candidate ATS Analysis Complete</h3>
            <p>Download individual report or full batch report</p>
          </div>
          <div className="action-buttons">
            {candidate.analysis_id && (
              <button 
                className="download-button" 
                onClick={() => handleIndividualDownload(candidate.analysis_id)}
              >
                <FileDown size={20} />
                <span>Download ATS Report</span>
              </button>
            )}
            <button className="download-button secondary" onClick={handleBatchDownload}>
              <DownloadCloud size={20} />
              <span>Download Full Batch</span>
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

  const backendStatusInfoMsg = getBackendStatusMessage();
  const aiStatusInfoMsg = getAiStatusMessage();

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
                <h1>Advanced ATS Resume Analyzer</h1>
                <div className="logo-subtitle">
                  <span className="powered-by">Powered by</span>
                  <span className="deepseek-badge">🧠 DeepSeek + Advanced ATS</span>
                  <span className="divider">•</span>
                  <span className="tagline">Weighted Multi-Dimensional • VLSI/CS Focus • Up to 10 Resumes</span>
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
                backgroundColor: backendStatusInfoMsg.bgColor,
                borderColor: `${backendStatusInfoMsg.color}30`,
                color: backendStatusInfoMsg.color
              }}
            >
              {backendStatusInfoMsg.icon}
              <span>{backendStatusInfoMsg.text}</span>
              {backendStatus === 'waking' && <Loader size={12} className="pulse-spinner" />}
            </div>
            
            {/* AI Status */}
            <div 
              className="feature ai-status-indicator" 
              style={{ 
                backgroundColor: aiStatusInfoMsg.bgColor,
                borderColor: `${aiStatusInfoMsg.color}30`,
                color: aiStatusInfoMsg.color
              }}
            >
              {aiStatusInfoMsg.icon}
              <span>{aiStatusInfoMsg.text}</span>
              {aiStatus === 'warming' && <Loader size={12} className="pulse-spinner" />}
            </div>
            
            {/* ATS Method */}
            {modelInfo?.ats_configuration && (
              <div className="feature model-info">
                <BarChart3 size={16} />
                <span>{modelInfo.ats_configuration.method.replace(/_/g, ' ').toUpperCase()}</span>
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
              title="Show service status"
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
                <Activity size={20} />
                <h3>Advanced ATS Service Status</h3>
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
                <div className="summary-label">ATS Scoring</div>
                <div className={`summary-value ${aiStatus === 'available' ? 'success' : aiStatus === 'warming' ? 'warning' : 'error'}`}>
                  {aiStatus === 'available' ? '🧠 Enhanced' : 
                   aiStatus === 'warming' ? '🔥 Warming' : 
                   '⚡ Advanced ATS'}
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Scoring Method</div>
                <div className="summary-value">
                  {modelInfo?.ats_configuration?.method?.replace(/_/g, ' ').toUpperCase() || 'WEIGHTED ATS'}
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Batch Capacity</div>
                <div className="summary-value success">
                  📊 Up to 10 resumes
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Domains</div>
                <div className="summary-value info">
                  🔬 VLSI/CS Focus
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Scoring Dimensions</div>
                <div className="summary-value">
                  📈 5 Weighted Areas
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
                <span>ATS: {aiStatus === 'available' ? 'Enhanced 🧠' : aiStatus === 'warming' ? 'Warming...' : 'Advanced ⚡'}</span>
              </div>
              {modelInfo?.ats_configuration && (
                <div className="status-indicator active">
                  <div className="indicator-dot" style={{ background: '#00ff9d' }}></div>
                  <span>Method: {modelInfo.ats_configuration.method.replace(/_/g, ' ')}</span>
                </div>
              )}
              <div className="status-indicator active">
                <div className="indicator-dot" style={{ background: '#00ff9d', animation: 'pulse 1.5s infinite' }}></div>
                <span>Mode: {currentView === 'single-results' ? 'Single ATS' : 
                              currentView === 'batch-results' ? 'Batch ATS' : 
                              currentView === 'candidate-detail' ? 'Candidate Details' : 
                              batchMode ? 'Batch' : 'Single'}</span>
              </div>
              {batchMode && (
                <div className="status-indicator active">
                  <div className="indicator-dot" style={{ background: '#ffd166' }}></div>
                  <span>Capacity: Up to 10 resumes</span>
                </div>
              )}
              <div className="status-indicator active">
                <div className="indicator-dot" style={{ background: '#9333ea' }}></div>
                <span>Domains: VLSI/CS Focus</span>
              </div>
            </div>
            
            {backendStatus !== 'ready' && (
              <div className="wakeup-message">
                <AlertCircle size={16} />
                <span>Backend is waking up. ATS analysis may be slower for the first request.</span>
              </div>
            )}
            
            {aiStatus === 'warming' && (
              <div className="wakeup-message">
                <Thermometer size={16} />
                <span>DeepSeek API is warming up for enhanced ATS scoring.</span>
              </div>
            )}
            
            {batchMode && (
              <div className="multi-key-message">
                <Brain size={16} />
                <span>Batch mode: Processing up to 10 resumes with Advanced Weighted ATS</span>
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
              <span>Advanced ATS Resume Analyzer</span>
            </div>
            <p className="footer-tagline">
              Weighted Multi-Dimensional ATS Scoring • VLSI/CS Domain Expertise • Up to 10 resumes per batch
            </p>
          </div>
          
          <div className="footer-links">
            <div className="footer-section">
              <h4>ATS Features</h4>
              <a href="#">Weighted Scoring</a>
              <a href="#">VLSI/CS Focus</a>
              <a href="#">Context Verification</a>
              <a href="#">Domain Expertise</a>
            </div>
            <div className="footer-section">
              <h4>Service</h4>
              <a href="#">Advanced ATS</a>
              <a href="#">Batch Processing</a>
              <a href="#">Excel Reports</a>
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
          <p>© 2024 Advanced ATS Resume Analyzer. Built with React + Flask + Advanced Weighted ATS Algorithm.</p>
          <div className="footer-stats">
            <span className="stat">
              <CloudLightning size={12} />
              Backend: {backendStatus === 'ready' ? 'Active' : 'Waking'}
            </span>
            <span className="stat">
              <Brain size={12} />
              ATS: {aiStatus === 'available' ? 'Enhanced 🧠' : 'Advanced ⚡'}
            </span>
            <span className="stat">
              <BarChart3 size={12} />
              Method: {modelInfo?.ats_configuration?.method?.replace(/_/g, ' ') || 'Weighted ATS'}
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
