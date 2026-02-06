import { useState } from 'react';
import { 
  Lock, Mail, Eye, EyeOff, AlertCircle, CheckCircle,
  Brain, Shield, Sparkles, ArrowRight, Loader
} from 'lucide-react';
import './Login.css';
import logoImage from './leadsoc.png';

const Login = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [shake, setShake] = useState(false);

  const VALID_CREDENTIALS = {
    email: 'Resugo@leadsoc.com',
    password: 'ResuGo#'
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1000));

    if (email === VALID_CREDENTIALS.email && password === VALID_CREDENTIALS.password) {
      // Store authentication in localStorage
      localStorage.setItem('isAuthenticated', 'true');
      localStorage.setItem('userEmail', email);
      
      // Success animation before login
      await new Promise(resolve => setTimeout(resolve, 500));
      onLogin();
    } else {
      setError('Invalid email or password. Please try again.');
      setShake(true);
      setTimeout(() => setShake(false), 500);
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      {/* Animated Background */}
      <div className="login-bg-grid"></div>
      <div className="login-bg-blur-1"></div>
      <div className="login-bg-blur-2"></div>
      <div className="login-bg-blur-3"></div>

      {/* Floating Particles */}
      <div className="particles">
        {[...Array(20)].map((_, i) => (
          <div key={i} className="particle" style={{
            left: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 3}s`,
            animationDuration: `${3 + Math.random() * 2}s`
          }}></div>
        ))}
      </div>

      {/* Login Card */}
      <div className={`login-card glass ${shake ? 'shake' : ''}`}>
        {/* Header */}
        <div className="login-header">
          <div className="login-logo-wrapper">
            <div className="login-logo-glow">
              <Brain className="login-logo-icon" />
            </div>
          </div>
          <h1 className="login-title">Welcome to ResuGo</h1>
          <p className="login-subtitle">AI-Powered Resume Analysis Platform</p>
          <div className="login-features">
            <span className="login-feature">
              <Sparkles size={14} />
              Groq AI
            </span>
            <span className="login-feature">
              <Shield size={14} />
              Secure Access
            </span>
          </div>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="login-form">
          {/* Email Input */}
          <div className="input-group">
            <label htmlFor="email" className="input-label">
              <Mail size={16} />
              Email Address
            </label>
            <div className="input-wrapper">
              <Mail className="input-icon" size={18} />
              <input
                id="email"
                type="email"
                className="input-field"
                placeholder="your.email@leadsoc.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
          </div>

          {/* Password Input */}
          <div className="input-group">
            <label htmlFor="password" className="input-label">
              <Lock size={16} />
              Password
            </label>
            <div className="input-wrapper">
              <Lock className="input-icon" size={18} />
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                className="input-field"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex="-1"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="error-message-login">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            className="login-button"
            disabled={loading || !email || !password}
          >
            {loading ? (
              <div className="button-loading">
                <Loader className="spinner" size={20} />
                <span>Authenticating...</span>
              </div>
            ) : (
              <div className="button-content">
                <span>Sign In</span>
                <ArrowRight size={20} />
              </div>
            )}
          </button>
        </form>

        {/* Footer */}
        <div className="login-footer">
          <div className="security-badge">
            <Shield size={14} />
            <span>Secure Authentication</span>
          </div>
        </div>
      </div>

      {/* Leadsoc Branding */}
      <div className="login-branding">
        <img src={logoImage} alt="LEADSOC" className="branding-logo" />
        <p className="branding-text">Partnering Your Success</p>
      </div>

      {/* Info Panel */}
      <div className="login-info-panel glass">
        <h3>Why ResuGo?</h3>
        <ul className="info-list">
          <li>
            <CheckCircle size={16} />
            <span>Groq AI-powered analysis</span>
          </li>
          <li>
            <CheckCircle size={16} />
            <span>Batch processing up to 10 resumes</span>
          </li>
          <li>
            <CheckCircle size={16} />
            <span>Detailed skills matching</span>
          </li>
          <li>
            <CheckCircle size={16} />
            <span>Comprehensive Excel reports</span>
          </li>
        </ul>
      </div>
    </div>
  );
};

export default Login;
