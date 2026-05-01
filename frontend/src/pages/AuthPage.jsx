/**
 * AuthPage.jsx
 * ============
 * Authentication page with login and signup forms.
 * Supports email authentication (Gmail, Hotmail, etc.)
 * Includes 2FA verification via SMS.
 */
import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Mail, Lock, User, Eye, EyeOff, ArrowRight, CheckCircle, AlertCircle, Send, Smartphone, Shield } from 'lucide-react';

export default function AuthPage({ onSuccess }) {
  const {
    signup,
    login,
    verify2FA,
    forgotPassword,
    resendVerification,
    loading,
    error,
    clearError,
  } = useAuth();

  // View state: 'login' | 'signup' | 'forgot-password' | 'verify-pending' | '2fa-verify'
  const [view, setView] = useState('login');

  // Form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [subscribeNewsletter, setSubscribeNewsletter] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  // 2FA state
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [pending2FAEmail, setPending2FAEmail] = useState('');

  // Validation state
  const [validationErrors, setValidationErrors] = useState({});
  const [successMessage, setSuccessMessage] = useState('');

  // Password requirements
  const passwordRequirements = [
    { label: 'At least 8 characters', test: (p) => p.length >= 8 },
    { label: 'One uppercase letter', test: (p) => /[A-Z]/.test(p) },
    { label: 'One lowercase letter', test: (p) => /[a-z]/.test(p) },
    { label: 'One number', test: (p) => /[0-9]/.test(p) },
  ];

  // Validate form
  const validateForm = () => {
    const errors = {};

    if (!email) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = 'Invalid email format';
    }

    if (!password) {
      errors.password = 'Password is required';
    } else if (view === 'signup') {
      const failedReqs = passwordRequirements.filter((r) => !r.test(password));
      if (failedReqs.length > 0) {
        errors.password = 'Password does not meet requirements';
      }
    }

    if (view === 'signup' && password !== confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }
    
    if (view === 'signup' && phoneNumber && !/^\+[1-9]\d{1,14}$/.test(phoneNumber)) {
      errors.phoneNumber = 'Phone number must be in E.164 format (e.g., +1234567890)';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle form submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();
    setSuccessMessage('');

    if (!validateForm()) return;

    let result;

    if (view === 'signup') {
      result = await signup(email, password, confirmPassword, subscribeNewsletter, phoneNumber || null);
      if (result.success) {
        setSuccessMessage('Account created! Please check your email to verify your address.');
        setView('verify-pending');
      }
    } else if (view === 'login') {
      result = await login(email, password);
      if (result.success) {
        if (result.requires2FA) {
          // Show 2FA verification screen
          setPending2FAEmail(email);
          setView('2fa-verify');
          setSuccessMessage('A verification code has been sent to your phone.');
        } else if (onSuccess) {
          onSuccess(result.user);
        }
      }
    } else if (view === 'forgot-password') {
      result = await forgotPassword(email);
      if (result.success) {
        setSuccessMessage('If an account exists, a password reset email has been sent.');
      }
    }
  };

  // Handle 2FA verification
  const handle2FAVerify = async (e) => {
    e.preventDefault();
    clearError();
    
    if (!twoFactorCode || twoFactorCode.length !== 6) {
      setValidationErrors({ twoFactorCode: 'Please enter a 6-digit code' });
      return;
    }

    const result = await verify2FA(pending2FAEmail, twoFactorCode);
    if (result.success) {
      if (onSuccess) onSuccess(result.user);
    }
  };

  // Handle resend verification
  const handleResendVerification = async () => {
    const result = await resendVerification(email);
    if (result.success) {
      setSuccessMessage('Verification email sent! Check your inbox.');
    }
  };

  // Get password strength color
  const getPasswordStrength = () => {
    const passed = passwordRequirements.filter((r) => r.test(password)).length;
    if (passed <= 1) return { color: 'red', label: 'Weak' };
    if (passed <= 3) return { color: 'yellow', label: 'Medium' };
    return { color: 'green', label: 'Strong' };
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--bg-primary)' }}>
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4" style={{ background: 'var(--accent-blue)' }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white">AI Agent Trading</h1>
          <p className="text-gray-400 mt-2">
            {view === 'login' && 'Sign in to your account'}
            {view === 'signup' && 'Create your account'}
            {view === 'forgot-password' && 'Reset your password'}
            {view === 'verify-pending' && 'Verify your email'}
            {view === '2fa-verify' && 'Two-Factor Authentication'}
          </p>
        </div>

        {/* Form Card */}
        <div className="rounded-xl p-6" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
          {/* Error Alert */}
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Success Alert */}
          {successMessage && (
            <div className="mb-4 p-3 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
              <p className="text-green-400 text-sm">{successMessage}</p>
            </div>
          )}

          {/* 2FA Verification View */}
          {view === '2fa-verify' ? (
            <div className="py-4">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-purple-500/20 flex items-center justify-center">
                <Shield className="w-8 h-8 text-purple-400" />
              </div>
              <h3 className="text-lg font-semibold text-white text-center mb-2">Enter verification code</h3>
              <p className="text-gray-400 text-sm text-center mb-6">
                We sent a 6-digit code to your phone number
              </p>
              
              <form onSubmit={handle2FAVerify} className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">6-Digit Code</label>
                  <div className="relative">
                    <Smartphone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                    <input
                      type="text"
                      value={twoFactorCode}
                      onChange={(e) => {
                        const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                        setTwoFactorCode(value);
                        setValidationErrors({ ...validationErrors, twoFactorCode: null });
                      }}
                      placeholder="000000"
                      maxLength={6}
                      className="w-full pl-10 pr-4 py-3 rounded-lg text-white text-center text-2xl tracking-widest font-mono"
                      style={{
                        background: 'var(--bg-primary)',
                        border: validationErrors.twoFactorCode ? '1px solid #ef4444' : '1px solid var(--border)',
                      }}
                    />
                  </div>
                  {validationErrors.twoFactorCode && (
                    <p className="text-red-400 text-xs mt-1">{validationErrors.twoFactorCode}</p>
                  )}
                </div>
                
                <button
                  type="submit"
                  disabled={loading || twoFactorCode.length !== 6}
                  className="w-full py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition-colors"
                  style={{
                    background: loading || twoFactorCode.length !== 6 ? 'var(--gray-600)' : 'var(--accent-blue)',
                    color: 'white',
                  }}
                >
                  {loading ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      Verify <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
                
                <button
                  type="button"
                  onClick={() => {
                    setView('login');
                    setTwoFactorCode('');
                    setPending2FAEmail('');
                    clearError();
                    setSuccessMessage('');
                  }}
                  className="w-full text-gray-400 hover:text-white text-sm"
                >
                  Back to login
                </button>
              </form>
            </div>
          ) : view === 'verify-pending' ? (
            // Verify Pending View
            <div className="text-center py-4">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-blue-500/20 flex items-center justify-center">
                <Mail className="w-8 h-8 text-blue-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Check your email</h3>
              <p className="text-gray-400 text-sm mb-4">
                We sent a verification link to <span className="text-white">{email}</span>
              </p>
              <p className="text-gray-500 text-xs mb-4">
                Didn't receive the email? Check your spam folder or
              </p>
              <button
                onClick={handleResendVerification}
                disabled={loading}
                className="text-blue-400 hover:text-blue-300 text-sm font-medium"
              >
                Resend verification email
              </button>
              <button
                onClick={() => setView('login')}
                className="block mx-auto mt-4 text-gray-400 hover:text-white text-sm"
              >
                Back to login
              </button>
            </div>
          ) : (
            // Form
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email Field */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">Email Address</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      setValidationErrors({ ...validationErrors, email: null });
                    }}
                    placeholder="you@gmail.com"
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg text-white"
                    style={{
                      background: 'var(--bg-primary)',
                      border: validationErrors.email ? '1px solid #ef4444' : '1px solid var(--border)',
                    }}
                  />
                </div>
                {validationErrors.email && (
                  <p className="text-red-400 text-xs mt-1">{validationErrors.email}</p>
                )}
              </div>

              {/* Password Field */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      setValidationErrors({ ...validationErrors, password: null });
                    }}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-10 py-2.5 rounded-lg text-white"
                    style={{
                      background: 'var(--bg-primary)',
                      border: validationErrors.password ? '1px solid #ef4444' : '1px solid var(--border)',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {validationErrors.password && (
                  <p className="text-red-400 text-xs mt-1">{validationErrors.password}</p>
                )}

                {/* Password Requirements (signup only) */}
                {view === 'signup' && password && (
                  <div className="mt-2 space-y-1">
                    {passwordRequirements.map((req, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-xs">
                        {req.test(password) ? (
                          <CheckCircle className="w-4 h-4 text-green-400" />
                        ) : (
                          <div className="w-4 h-4 rounded-full border border-gray-600" />
                        )}
                        <span className={req.test(password) ? 'text-green-400' : 'text-gray-500'}>
                          {req.label}
                        </span>
                      </div>
                    ))}
                    {password && (
                      <div className="flex items-center gap-2 text-xs mt-2">
                        <span className="text-gray-500">Strength:</span>
                        <span style={{ color: getPasswordStrength().color }}>
                          {getPasswordStrength().label}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Confirm Password Field (signup only) */}
              {view === 'signup' && (
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Confirm Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      value={confirmPassword}
                      onChange={(e) => {
                        setConfirmPassword(e.target.value);
                        setValidationErrors({ ...validationErrors, confirmPassword: null });
                      }}
                      placeholder="••••••••"
                      className="w-full pl-10 pr-10 py-2.5 rounded-lg text-white"
                      style={{
                        background: 'var(--bg-primary)',
                        border: validationErrors.confirmPassword ? '1px solid #ef4444' : '1px solid var(--border)',
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
                    >
                      {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                  {validationErrors.confirmPassword && (
                    <p className="text-red-400 text-xs mt-1">{validationErrors.confirmPassword}</p>
                  )}
                </div>
              )}

              {/* Phone Number Field for 2FA (signup only) */}
              {view === 'signup' && (
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    Phone Number (optional - for 2FA)
                  </label>
                  <div className="relative">
                    <Smartphone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                    <input
                      type="tel"
                      value={phoneNumber}
                      onChange={(e) => {
                        setPhoneNumber(e.target.value);
                        setValidationErrors({ ...validationErrors, phoneNumber: null });
                      }}
                      placeholder="+1234567890"
                      className="w-full pl-10 pr-4 py-2.5 rounded-lg text-white"
                      style={{
                        background: 'var(--bg-primary)',
                        border: validationErrors.phoneNumber ? '1px solid #ef4444' : '1px solid var(--border)',
                      }}
                    />
                  </div>
                  {validationErrors.phoneNumber && (
                    <p className="text-red-400 text-xs mt-1">{validationErrors.phoneNumber}</p>
                  )}
                  <p className="text-gray-500 text-xs mt-1">
                    Enter in E.164 format (e.g., +1234567890). Used for 2FA login.
                  </p>
                </div>
              )}

              {/* Newsletter Checkbox (signup only) */}
              {view === 'signup' && (
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={subscribeNewsletter}
                    onChange={(e) => setSubscribeNewsletter(e.target.checked)}
                    className="w-4 h-4 rounded border-gray-600 bg-gray-700"
                  />
                  <span className="text-sm text-gray-400">
                    Subscribe to newsletter for trading updates
                  </span>
                </label>
              )}

              {/* Forgot Password Link (login only) */}
              {view === 'login' && (
                <button
                  type="button"
                  onClick={() => {
                    setView('forgot-password');
                    clearError();
                    setSuccessMessage('');
                  }}
                  className="text-sm text-blue-400 hover:text-blue-300"
                >
                  Forgot password?
                </button>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition-colors"
                style={{
                  background: loading ? 'var(--gray-600)' : 'var(--accent-blue)',
                  color: 'white',
                }}
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    {view === 'login' && (
                      <>
                        Sign In <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                    {view === 'signup' && (
                      <>
                        Create Account <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                    {view === 'forgot-password' && (
                      <>
                        Send Reset Link <Send className="w-4 h-4" />
                      </>
                    )}
                  </>
                )}
              </button>
            </form>
          )}

          {/* Switch View Links */}
          {view !== 'verify-pending' && view !== '2fa-verify' && (
            <div className="mt-6 text-center">
              {view === 'login' && (
                <p className="text-gray-400 text-sm">
                  Don't have an account?{' '}
                  <button
                    onClick={() => {
                      setView('signup');
                      clearError();
                      setSuccessMessage('');
                    }}
                    className="text-blue-400 hover:text-blue-300 font-medium"
                  >
                    Sign up
                  </button>
                </p>
              )}
              {view === 'signup' && (
                <p className="text-gray-400 text-sm">
                  Already have an account?{' '}
                  <button
                    onClick={() => {
                      setView('login');
                      clearError();
                      setSuccessMessage('');
                    }}
                    className="text-blue-400 hover:text-blue-300 font-medium"
                  >
                    Sign in
                  </button>
                </p>
              )}
              {view === 'forgot-password' && (
                <p className="text-gray-400 text-sm">
                  Remember your password?{' '}
                  <button
                    onClick={() => {
                      setView('login');
                      clearError();
                      setSuccessMessage('');
                    }}
                    className="text-blue-400 hover:text-blue-300 font-medium"
                  >
                    Sign in
                  </button>
                </p>
              )}
            </div>
          )}
        </div>

        {/* Terms */}
        {view === 'signup' && (
          <p className="mt-4 text-center text-xs text-gray-500">
            By creating an account, you agree to our{' '}
            <a href="#" className="text-gray-400 hover:text-white">Terms of Service</a>
            {' '}and{' '}
            <a href="#" className="text-gray-400 hover:text-white">Privacy Policy</a>
          </p>
        )}
      </div>
    </div>
  );
}