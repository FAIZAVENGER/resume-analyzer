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
  Meh, Laugh, Angry, Surprised,
  // New icons
  Cpu as CpuIcon, Database as DatabaseIcon,
  Server as ServerIcon, Terminal as TerminalIcon,
  BrainCircuit, Microchip, HardDrive, Layers,
  Network, ShieldCheck as ShieldCheckIcon,
  Lock as LockIcon, Key as KeyIcon,
  Users as UsersIcon, PieChart, BarChart as BarChartIcon,
  LineChart, Activity as ActivityIcon,
  TrendingUp as TrendingUpIcon, ZapOff,
  Cloud as CloudIcon, Database as DatabaseIcon2,
  Bot, Sparkles as SparklesIcon, Target as TargetIcon,
  Settings as SettingsIcon, Bell as BellIcon,
  HelpCircle as HelpCircleIcon, Wifi as WifiIcon,
  Shield as ShieldOffIcon, Download as DownloadIcon,
  Upload as UploadIcon, File as FileIcon,
  Folder as FolderIcon, Home as HomeIcon2,
  Mail as MailIcon, Phone as PhoneIcon,
  MapPin as MapPinIcon, Link as LinkIcon,
  ExternalLink as ExternalLinkIcon,
  ChevronDown, ChevronUp, Menu, X as XIcon,
  Plus as PlusIcon, Minus as MinusIcon,
  Edit as EditIcon, Trash2 as TrashIcon,
  Copy as CopyIcon, Scissors as ScissorsIcon,
  Type as TypeIcon, Bold as BoldIcon,
  Italic as ItalicIcon, Underline as UnderlineIcon,
  List as ListIcon, Hash as HashIcon,
  Quote as QuoteIcon, Divide as DivideIcon,
  Percent as PercentIcon, DollarSign as DollarIcon,
  Euro as EuroIcon, Pound as PoundIcon,
  Yen as YenIcon, Bitcoin as BitcoinIcon,
  CreditCard as CreditCardIcon, ShoppingCart as CartIcon,
  Package as PackageIcon, Truck as TruckIcon,
  Box as BoxIcon, Warehouse as WarehouseIcon,
  Building as BuildingIcon, Navigation as NavigationIcon,
  Compass as CompassIcon, Map as MapIcon,
  Globe as GlobeIcon2, Sunrise as SunriseIcon,
  Sunset as SunsetIcon, Moon as MoonIcon,
  CloudSun as CloudSunIcon, Umbrella as UmbrellaIcon,
  Wind as WindIcon, ThermometerSun as ThermometerIcon,
  Droplets as DropletsIcon, Waves as WavesIcon,
  Tree as TreeIcon, Flower as FlowerIcon,
  Leaf as LeafIcon, Bug as BugIcon,
  Fish as FishIcon, Bird as BirdIcon,
  Cat as CatIcon, Dog as DogIcon,
  Rabbit as RabbitIcon, Cow as CowIcon,
  Pig as PigIcon, Egg as EggIcon,
  Apple as AppleIcon, Carrot as CarrotIcon,
  Coffee as CoffeeIcon2, Wine as WineIcon,
  Beer as BeerIcon, Cake as CakeIcon,
  Cookie as CookieIcon, IceCream as IceCreamIcon,
  Pizza as PizzaIcon, Hamburger as HamburgerIcon,
  FrenchFries as FriesIcon, Drumstick as DrumstickIcon,
  EggFried as FriedEggIcon, Soup as SoupIcon,
  Milk as MilkIcon, GlassWater as WaterIcon,
  Citrus as CitrusIcon, Pepper as PepperIcon,
  Salt as SaltIcon, Sugar as SugarIcon,
  Wheat as WheatIcon, Croissant as CroissantIcon,
  Sandwich as SandwichIcon, Donut as DonutIcon,
  Candy as CandyIcon, Lemon as LemonIcon,
  Cherry as CherryIcon, Strawberry as StrawberryIcon,
  Grape as GrapeIcon, Watermelon as WatermelonIcon,
  Peach as PeachIcon, Pear as PearIcon,
  Banana as BananaIcon, Avocado as AvocadoIcon,
  Broccoli as BroccoliIcon, Corn as CornIcon,
  Eggplant as EggplantIcon, Mushroom as MushroomIcon,
  Onion as OnionIcon, Potato as PotatoIcon,
  Tomato as TomatoIcon, Pumpkin as PumpkinIcon,
  Radish as RadishIcon, HotPepper as PepperHotIcon,
  Garlic as GarlicIcon, Basil as BasilIcon,
  Sprout as SproutIcon, Bone as BoneIcon,
  Skull as SkullIcon, Ghost as GhostIcon,
  Smile as SmileIcon, Frown as FrownIcon,
  Meh as MehIcon, Laugh as LaughIcon,
  Angry as AngryIcon, Heart as HeartIcon2,
  Star as StarIcon2, Flag as FlagIcon,
  Music as MusicIcon, Camera as CameraIcon,
  Video as VideoIcon, Headphones as HeadphonesIcon,
  Mic as MicIcon, MessageSquare as MessageIcon,
  Bookmark as BookmarkIcon, Eye as EyeIcon,
  EyeOff as EyeOffIcon, Search as SearchIcon,
  Bell as BellIcon2, Settings as SettingsIcon2,
  Key as KeyIcon2, LogOut as LogOutIcon,
  UserPlus as UserPlusIcon, UserCheck as UserCheckIcon,
  UserX as UserXIcon, ThumbsUp as ThumbsUpIcon,
  AlertOctagon as AlertOctagonIcon, Lightbulb as LightbulbIcon,
  GitBranch as GitBranchIcon, Palette as PaletteIcon,
  Code as CodeIcon, Database as DatabaseIcon3,
  Server as ServerIcon2, Terminal as TerminalIcon2
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
  const [retryCount, setRetryCount] = useState(0);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  const [showServicePanel, setShowServicePanel] = useState(false);
  const [batchMode, setBatchMode] = useState(false);
  const [modelInfo, setModelInfo] = useState(null);
  const [serviceStatus, setServiceStatus] = useState({
    aiEngine: 'Self-Hosted AI',
    nlpModel: 'SpaCy + Custom',
    batchCapacity: 20
  });
  
  // View management for navigation
  const [currentView, setCurrentView] = useState('main'); // 'main', 'single-results', 'batch-results', 'candidate-detail'
  const [selectedCandidateIndex, setSelectedCandidateIndex] = useState(null);
  
  const API_BASE_URL = 'http://localhost:5002'; // Update this to your backend URL
  
  const keepAliveInterval = useRef(null);
  const backendWakeInterval = useRef(null);
  const statusCheckInterval = useRef(null);

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
      if (statusCheckInterval.current) {
        clearInterval(statusCheckInterval.current);
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
          aiEngine: healthResponse.data.ai_engine || 'Self-Hosted AI',
          nlpModel: healthResponse.data.nlp_model || 'SpaCy + Custom',
          batchCapacity: healthResponse.data.max_batch_size || 20,
          database: healthResponse.data.database || 'connected',
          version: healthResponse.data.version || '2.0.0'
        });
        
        setBackendStatus('ready');
        setAiStatus('available');
        
        if (healthResponse.data.ai_engine) {
          setModelInfo({
            name: healthResponse.data.ai_engine,
            description: 'Self-Hosted AI Engine'
          });
        }
      } else {
        // If health check fails, still set defaults
        setBackendStatus('ready');
        setAiStatus('available');
        setModelInfo({
          name: 'ResumeAnalyzer AI',
          description: 'Self-Hosted NLP Engine'
        });
      }
      
      setupPeriodicChecks();
      
    } catch (err) {
      console.log('Service initialization error:', err.message);
      setBackendStatus('sleeping');
      setAiStatus('checking');
      
      setTimeout(() => initializeService(), 5000);
    } finally {
      setIsWarmingUp(false);
    }
  };

  const wakeUpBackend = async () => {
    try {
      console.log('🔔 Connecting to backend...');
      setLoadingMessage('Connecting to backend...');
      
      const healthResponse = await axios.get(`${API_BASE_URL}/health`, {
        timeout: 10000
      });
      
      if (healthResponse.data.status === 'healthy') {
        console.log('✅ Backend is healthy and responding');
        setBackendStatus('ready');
        setAiStatus('available');
        setLoadingMessage('');
        
        // Update service status with backend info
        setServiceStatus(prev => ({
          ...prev,
          aiEngine: healthResponse.data.ai_engine || 'Self-Hosted AI',
          nlpModel: healthResponse.data.nlp_model || 'SpaCy + Custom',
          batchCapacity: healthResponse.data.max_batch_size || 20,
          version: healthResponse.data.version || '2.0.0'
        }));
        
        return true;
      } else {
        console.log('⚠️ Backend not fully healthy');
        setBackendStatus('waking');
        return false;
      }
      
    } catch (error) {
      console.log('⚠️ Backend connection failed:', error.message);
      setBackendStatus('sleeping');
      setAiStatus('checking');
      setLoadingMessage('Backend connection failed. Retrying...');
      
      // Retry after delay
      setTimeout(() => {
        axios.get(`${API_BASE_URL}/health`, { timeout: 15000 })
          .then(() => {
            setBackendStatus('ready');
            setAiStatus('available');
            console.log('✅ Backend connection established');
          })
          .catch(() => {
            console.log('❌ Backend still unavailable');
          });
      }, 3000);
      
      return false;
    }
  };

  const checkBackendHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`, {
        timeout: 8000
      });
      
      if (response.data.status === 'healthy') {
        setBackendStatus('ready');
        setAiStatus('available');
        
        // Update model info if available
        if (response.data.ai_engine) {
          setModelInfo({
            name: response.data.ai_engine,
            description: 'Self-Hosted AI Engine'
          });
        }
        
        return true;
      } else {
        setBackendStatus('waking');
        return false;
      }
      
    } catch (error) {
      console.log('Backend health check failed:', error.message);
      setBackendStatus('sleeping');
      return false;
    }
  };

  const setupPeriodicChecks = () => {
    // Keep-alive ping every 5 minutes
    backendWakeInterval.current = setInterval(() => {
      axios.get(`${API_BASE_URL}/health`, { timeout: 5000 })
        .then(() => console.log('✅ Keep-alive ping successful'))
        .catch(() => console.log('⚠️ Keep-alive ping failed'));
    }, 5 * 60 * 1000);
    
    // Status check every 30 seconds
    statusCheckInterval.current = setInterval(() => {
      if (backendStatus !== 'ready' || aiStatus !== 'available') {
        checkBackendHealth();
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
      // Allow up to 20 files (self-hosted backend supports more)
      setResumeFiles(prev => [...prev, ...validFiles].slice(0, 20));
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
      setError('Backend is connecting. Please wait a moment...');
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

      setLoadingMessage('Self-Hosted AI analysis...');
      setProgress(20);

      setLoadingMessage('Uploading and processing resume...');
      setProgress(30);

      const response = await axios.post(`${API_BASE_URL}/analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 120000, // 2 minutes for self-hosted AI
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
        setError('Request timeout. The backend might be processing. Please try again in 30 seconds.');
        setBackendStatus('sleeping');
        wakeUpBackend();
      } else if (err.response?.status === 429) {
        setError('Rate limit reached. Please try again later.');
      } else if (err.response?.data?.error?.includes('quota') || err.response?.data?.error?.includes('rate limit')) {
        setError('Processing limit reached. Please wait a minute and try again.');
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
      setError('Backend is connecting. Please wait a moment...');
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
        setError('Batch analysis timeout. The backend might be processing. Please try again.');
        setBackendStatus('sleeping');
        wakeUpBackend();
      } else if (err.response?.status === 429) {
        setError('Processing limit reached. Please try again later or reduce batch size.');
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
        text: 'Backend Connecting', 
        color: '#ffd166', 
        icon: <CloudRain size={16} />,
        bgColor: 'rgba(255, 209, 102, 0.1)'
      };
      case 'sleeping': return { 
        text: 'Backend Offline', 
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
        text: 'Checking AI Engine...', 
        color: '#ffd166', 
        icon: <Brain size={16} />,
        bgColor: 'rgba(255, 209, 102, 0.1)'
      };
      case 'available': return { 
        text: 'AI Engine Ready 🤖', 
        color: '#00ff9d', 
        icon: <BrainCircuit size={16} />,
        bgColor: 'rgba(0, 255, 157, 0.1)'
      };
      case 'unavailable': return { 
        text: 'AI Engine Offline', 
        color: '#ff6b6b', 
        icon: <Brain size={16} />,
        bgColor: 'rgba(255, 107, 107, 0.1)'
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

  const handleForceReconnect = async () => {
    setIsWarmingUp(true);
    setLoadingMessage('Reconnecting to backend...');
    
    try {
      await wakeUpBackend();
      setLoadingMessage('');
    } catch (error) {
      console.log('Reconnection failed:', error);
    } finally {
      setIsWarmingUp(false);
    }
  };

  const getModelDisplayName = (modelInfo) => {
    if (!modelInfo) return 'Self-Hosted AI';
    if (typeof modelInfo === 'string') return modelInfo;
    return modelInfo.name || 'Self-Hosted AI';
  };

  const getModelDescription = (modelInfo) => {
    if (!modelInfo || typeof modelInfo === 'string') return 'Custom NLP Engine';
    return modelInfo.description || 'Custom NLP Engine';
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
            <ZapIcon size={14} /> Self-Hosted
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
            <Users size={16} /> Multiple Resumes (Up to {serviceStatus.batchCapacity})
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
                  ? `Upload multiple resumes (Max ${serviceStatus.batchCapacity}, 15MB each)` 
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
                      <span className="upload-hint">Max {serviceStatus.batchCapacity} files, 15MB each</span>
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
                <BrainCircuit size={14} />
              </div>
              <span>Self-Hosted AI analysis</span>
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
              <span>Advanced NLP Processing</span>
            </div>
            <div className="stat">
              <div className="stat-icon">
                <Database size={14} />
              </div>
              <span>Multi-factor Scoring</span>
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
          {error.includes('connecting') && (
            <button 
              className="error-action-button"
              onClick={handleForceReconnect}
            >
              <Activity size={16} />
              Reconnect
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
              <h3>{batchMode ? 'Batch Analysis' : 'Analysis in Progress'}</h3>
            </div>
            
            <div className="progress-container">
              <div className="progress-bar" style={{ width: `${batchMode ? batchProgress : progress}%` }}></div>
            </div>
            
            <div className="loading-text">
              <span className="loading-message">{loadingMessage}</span>
              <span className="loading-subtext">
                {batchMode 
                  ? `Processing ${resumeFiles.length} resume(s) with ${getModelDisplayName(modelInfo)}...` 
                  : `Using ${getModelDisplayName(modelInfo)}...`}
              </span>
            </div>
            
            <div className="progress-stats">
              <span>{Math.round(batchMode ? batchProgress : progress)}%</span>
              <span>•</span>
              <span>Backend: {backendStatus === 'ready' ? 'Active' : 'Connecting...'}</span>
              <span>•</span>
              <span>AI Engine: {aiStatus === 'available' ? 'Ready 🤖' : 'Checking...'}</span>
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
              <span>Self-Hosted AI with advanced NLP processing and multi-factor scoring</span>
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
            <span>Reconnecting...</span>
          </div>
        ) : (
          <>
            <div className="button-content">
              <BrainCircuit size={20} />
              <div className="button-text">
                <span>{batchMode ? 'Analyze Multiple Resumes' : 'Analyze Resume'}</span>
                <span className="button-subtext">
                  {batchMode 
                    ? `${resumeFiles.length} resume(s) • ${getModelDisplayName(modelInfo)} • Batch` 
                    : `${getModelDisplayName(modelInfo)} • Single`}
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
              <BrainCircuit size={16} />
              <span>Self-Hosted AI with advanced NLP processing</span>
            </div>
            <div className="tip">
              <Activity size={16} />
              <span>Process up to {serviceStatus.batchCapacity} resumes in a single batch</span>
            </div>
            <div className="tip">
              <TrendingUp size={16} />
              <span>Candidates will be ranked by ATS score from highest to lowest</span>
            </div>
            <div className="tip">
              <Download size={16} />
              <span>Download comprehensive Excel report with all candidate data</span>
            </div>
          </>
        ) : (
          <>
            <div className="tip">
              <BrainCircuit size={16} />
              <span>Self-Hosted AI - No external API dependencies</span>
            </div>
            <div className="tip">
              <Database size={16} />
              <span>Multi-factor scoring with 8 different dimensions</span>
            </div>
            <div className="tip">
              <Activity size={16} />
              <span>Advanced NLP with SpaCy + custom algorithms</span>
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
            <h2>🤖 Resume Analysis Results</h2>
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
                <span className="file-info">
                  <Cpu size={14} />
                  AI Engine: {analysis.ai_engine || 'Self-Hosted AI'}
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
                  <BrainCircuit size={12} />
                  Processing Time: {analysis.processing_time || 'N/A'}
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
                {analysis.ai_engine || 'Self-Hosted AI'} • Multi-factor Scoring
              </p>
            </div>
          </div>
          <div className="recommendation-content">
            <p className="recommendation-text">{analysis.recommendation}</p>
            <div className="confidence-badge">
              <BrainCircuit size={16} />
              <span>Self-Hosted AI Analysis</span>
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

        {/* Insights Section - Clean Version without bullet points */}
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
                <p className="insight-subtitle">Opportunities to grow</p>
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

        {/* Additional Insights from Self-Hosted AI */}
        {analysis.career_advice && analysis.career_advice.length > 0 && (
          <>
            <div className="section-title">
              <h2>Career Advice</h2>
              <p>Personalized recommendations for professional growth</p>
            </div>
            
            <div className="career-advice-grid">
              {analysis.career_advice.slice(0, 4).map((advice, index) => (
                <div key={index} className="career-advice-card glass">
                  <div className="advice-header">
                    <Lightbulb size={20} />
                    <h4>Recommendation {index + 1}</h4>
                  </div>
                  <p className="advice-text">{advice}</p>
                </div>
              ))}
            </div>
          </>
        )}

        {/* AI Analysis Details */}
        <div className="ai-details-card glass">
          <div className="ai-details-header">
            <BrainCircuit size={24} />
            <div>
              <h3>AI Analysis Details</h3>
              <p className="ai-details-subtitle">Technical information about this analysis</p>
            </div>
          </div>
          <div className="ai-details-content">
            <div className="ai-detail-item">
              <span className="detail-label">AI Engine:</span>
              <span className="detail-value">{analysis.ai_engine || 'Self-Hosted AI'}</span>
            </div>
            <div className="ai-detail-item">
              <span className="detail-label">Model Version:</span>
              <span className="detail-value">{analysis.model_version || '2.0.0'}</span>
            </div>
            <div className="ai-detail-item">
              <span className="detail-label">Processing Time:</span>
              <span className="detail-value">{analysis.processing_time || 'N/A'}</span>
            </div>
            <div className="ai-detail-item">
              <span className="detail-label">Analysis ID:</span>
              <span className="detail-value">{analysis.analysis_id || 'N/A'}</span>
            </div>
            <div className="ai-detail-item">
              <span className="detail-label">Analysis Depth:</span>
              <span className="detail-value" style={{ color: '#00ff9d' }}>
                {analysis.analysis_depth || 'Comprehensive'}
              </span>
            </div>
            {analysis.cached && (
              <div className="ai-detail-item">
                <span className="detail-label">Cache Status:</span>
                <span className="detail-value" style={{ color: '#ffd166' }}>
                  Served from cache
                </span>
              </div>
            )}
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
          <h2>🤖 Batch Analysis Results</h2>
          <p>{batchAnalysis?.successfully_analyzed || 0} resumes analyzed</p>
        </div>
        <div className="navigation-actions">
          <button className="download-report-btn" onClick={handleBatchDownload}>
            <DownloadCloud size={18} />
            <span>Download Full Report</span>
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
            <Cpu size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{batchAnalysis?.ai_engine || 'Self-Hosted AI'}</div>
            <div className="stat-label">AI Engine</div>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon warning">
            <Activity size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{batchAnalysis?.processing_time || 'N/A'}</div>
            <div className="stat-label">Processing Time</div>
          </div>
        </div>
      </div>

      {/* Candidates Ranking */}
      <div className="section-title">
        <h2>Candidate Rankings</h2>
        <p>Sorted by ATS Score (Highest to Lowest) • Self-Hosted AI Processing</p>
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
          <p>Download comprehensive Excel report with all candidate details</p>
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
                  AI Engine: {candidate.ai_engine || 'Self-Hosted AI'}
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
                {candidate.ai_engine || 'Self-Hosted AI'} • Batch Processing
              </p>
            </div>
          </div>
          <div className="recommendation-content">
            <p className="recommendation-text">{candidate.recommendation}</p>
            <div className="confidence-badge">
              <BrainCircuit size={16} />
              <span>Self-Hosted AI Analysis</span>
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

        {/* Insights Section - Clean Version without bullet points */}
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
                <p className="insight-subtitle">Areas where candidate excels</p>
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
                <p className="insight-subtitle">Opportunities to grow</p>
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
            <h3>Candidate Analysis Complete</h3>
            <p>Download individual report or full batch report</p>
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
                <BrainCircuit className="logo-icon" />
              </div>
              <div className="logo-text">
                <h1>Self-Hosted Resume Analyzer</h1>
                <div className="logo-subtitle">
                  <span className="powered-by">Powered by</span>
                  <span className="ai-badge">🤖 Self-Hosted AI</span>
                  <span className="divider">•</span>
                  <span className="tagline">Advanced NLP • No API Limits • Complete Privacy</span>
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
              {aiStatus === 'checking' && <Loader size={12} className="pulse-spinner" />}
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
            
            {/* Reconnect Button */}
            {backendStatus !== 'ready' && (
              <button 
                className="feature reconnect-button"
                onClick={handleForceReconnect}
                disabled={isWarmingUp}
              >
                {isWarmingUp ? (
                  <Loader size={16} className="spinner" />
                ) : (
                  <Activity size={16} />
                )}
                <span>Reconnect</span>
              </button>
            )}
            
            {/* Service Status Toggle */}
            <button 
              className="feature service-toggle"
              onClick={() => setShowServicePanel(!showServicePanel)}
              title="Show service status"
            >
              <Server size={16} />
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
        {/* Service Panel */}
        {showServicePanel && (
          <div className="service-status-panel glass">
            <div className="service-panel-header">
              <div className="service-title">
                <Server size={20} />
                <h3>Self-Hosted Service Status</h3>
              </div>
              <button 
                className="close-service"
                onClick={() => setShowServicePanel(false)}
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="service-summary">
              <div className="summary-item">
                <div className="summary-label">Backend Status</div>
                <div className={`summary-value ${backendStatus === 'ready' ? 'success' : backendStatus === 'waking' ? 'warning' : 'error'}`}>
                  {backendStatus === 'ready' ? '✅ Active' : 
                   backendStatus === 'waking' ? '🔥 Connecting' : 
                   '💤 Offline'}
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">AI Engine Status</div>
                <div className={`summary-value ${aiStatus === 'available' ? 'success' : aiStatus === 'checking' ? 'warning' : 'error'}`}>
                  {aiStatus === 'available' ? '🤖 Ready' : 
                   aiStatus === 'checking' ? '🔍 Checking' : 
                   '⚠️ Offline'}
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">AI Engine</div>
                <div className="summary-value">
                  {serviceStatus.aiEngine}
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">NLP Model</div>
                <div className="summary-value">
                  {serviceStatus.nlpModel}
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Batch Capacity</div>
                <div className="summary-value success">
                  📊 Up to {serviceStatus.batchCapacity} resumes
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Processing Method</div>
                <div className="summary-value info">
                  ⚡ Advanced Multi-factor
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-label">Version</div>
                <div className="summary-value">
                  🏷️ {serviceStatus.version || '2.0.0'}
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
                className="action-button reconnect"
                onClick={handleForceReconnect}
                disabled={isWarmingUp}
              >
                {isWarmingUp ? (
                  <Loader size={16} className="spinner" />
                ) : (
                  <Activity size={16} />
                )}
                Reconnect
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
                <span>Backend: {backendStatus === 'ready' ? 'Active' : 'Connecting'}</span>
              </div>
              <div className={`status-indicator ${aiStatus === 'available' ? 'active' : 'inactive'}`}>
                <div className="indicator-dot"></div>
                <span>AI Engine: {aiStatus === 'available' ? 'Ready 🤖' : aiStatus === 'checking' ? 'Checking...' : 'Offline'}</span>
              </div>
              {modelInfo && (
                <div className="status-indicator active">
                  <div className="indicator-dot" style={{ background: '#00ff9d' }}></div>
                  <span>Engine: {getModelDisplayName(modelInfo)}</span>
                </div>
              )}
              <div className="status-indicator active">
                <div className="indicator-dot" style={{ background: '#00ff9d', animation: 'pulse 1.5s infinite' }}></div>
                <span>Mode: {currentView === 'single-results' ? 'Single Analysis' : 
                              currentView === 'batch-results' ? 'Batch Analysis' : 
                              currentView === 'candidate-detail' ? 'Candidate Details' : 
                              batchMode ? 'Batch' : 'Single'}</span>
              </div>
              {batchMode && (
                <div className="status-indicator active">
                  <div className="indicator-dot" style={{ background: '#ffd166' }}></div>
                  <span>Capacity: Up to {serviceStatus.batchCapacity} resumes</span>
                </div>
              )}
            </div>
            
            {backendStatus !== 'ready' && (
              <div className="connection-message">
                <AlertCircle size={16} />
                <span>Backend is connecting. Analysis may be slower for the first request.</span>
              </div>
            )}
            
            {batchMode && (
              <div className="batch-message">
                <BrainCircuit size={16} />
                <span>Batch mode: Processing up to {serviceStatus.batchCapacity} resumes with Self-Hosted AI</span>
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
              <BrainCircuit size={20} />
              <span>Self-Hosted Resume Analyzer</span>
            </div>
            <p className="footer-tagline">
              Advanced NLP with SpaCy • No API Limits • Complete Data Privacy • Multi-factor Scoring
            </p>
          </div>
          
          <div className="footer-links">
            <div className="footer-section">
              <h4>Features</h4>
              <a href="#">Self-Hosted AI</a>
              <a href="#">Advanced NLP</a>
              <a href="#">Batch Processing</a>
              <a href="#">Excel Reports</a>
            </div>
            <div className="footer-section">
              <h4>Service</h4>
              <a href="#">No API Limits</a>
              <a href="#">Data Privacy</a>
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
          <p>© 2024 Self-Hosted Resume Analyzer. Built with React + Flask + Custom AI. No External APIs.</p>
          <div className="footer-stats">
            <span className="stat">
              <Server size={12} />
              Backend: {backendStatus === 'ready' ? 'Active' : 'Connecting'}
            </span>
            <span className="stat">
              <BrainCircuit size={12} />
              AI Engine: {aiStatus === 'available' ? 'Ready 🤖' : 'Checking'}
            </span>
            <span className="stat">
              <Cpu size={12} />
              Engine: {modelInfo ? getModelDisplayName(modelInfo) : 'Self-Hosted AI'}
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
