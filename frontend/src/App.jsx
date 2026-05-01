import { Routes, Route, NavLink, useLocation, useNavigate } from 'react-router-dom'
import TradingDashboard from './pages/TradingDashboard'
import BacktestPage from './pages/BacktestPage'
import AgentStatus from './pages/AgentStatus'
import KnowledgePage from './pages/KnowledgePage'
import SecurityPage from './pages/SecurityPage'
import GovernancePage from './pages/GovernancePage'
import PaymentsPage from './pages/PaymentsPage'
import RiskDashboardPage from './pages/RiskDashboardPage'
import EscrowDashboard from './pages/EscrowDashboard'
import AuthPage from './pages/AuthPage'
import NotificationsPage from './pages/NotificationsPage'
import { useTheme } from './contexts/ThemeContext'
import { useAppMode } from './contexts/AppModeContext'
import { useAuth } from './contexts/AuthContext'
import { User, LogOut, Mail, CheckCircle } from 'lucide-react'

import ConfigPage from './pages/ConfigPage'
import DebateArenaPage from './pages/DebateArenaPage'
import StrategyPage from './pages/StrategyPage'
import FAQPage from './pages/FAQPage'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

export { API_BASE }

export default function App() {
  const { isDark, toggleTheme } = useTheme()
  const { isSimulation, isLive, toggleMode } = useAppMode()
  const { user, isAuthenticated, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const navLinks = [
    { to: '/', label: 'Trading' }, // Points to Dashboard/Backtest based on mode
    { to: '/risk', label: 'Risk Dashboard' },
    { to: '/escrow', label: 'Escrow & Revenue' },
    { to: '/notifications', label: 'Notifications' },
    { to: '/strategy', label: 'Strategy' },
    { to: '/debate', label: 'Debate Arena' },
    { to: '/config', label: 'Config' },
    { to: '/security', label: 'Security' },
    { to: '/governance', label: 'Governance' },
    { to: '/knowledge', label: 'Knowledge' },
    { to: '/payments', label: 'Payments' },
    { to: '/faq', label: 'FAQ' },
  ]

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--bg-primary)' }}>
      {/* Sidebar */}
      <aside className="w-64 flex flex-col h-screen sticky top-0" style={{ background: 'var(--bg-secondary)', borderRight: '1px solid var(--border)' }}>
        <div className="p-4 sm:p-6" style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="flex items-center gap-3 mb-6">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center`} style={{ background: 'var(--accent-blue)' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
            </div>
            <span className="font-bold text-lg">AI Agent Trading</span>
          </div>

          {/* Mode Switcher */}
          <div className="flex rounded-lg p-1" style={{ background: 'rgba(0,0,0,0.1)' }}>
            <button
              onClick={() => { if (isLive) toggleMode() }}
              className={`flex-1 text-xs py-1.5 font-bold rounded-md transition-colors ${
                isSimulation 
                  ? 'text-emerald-500 bg-emerald-500/10' 
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
              style={isSimulation ? { border: '1px solid rgba(16, 185, 129, 0.3)' } : {}}
            >
              Simulation
            </button>
            <button
              onClick={() => { if (isSimulation) toggleMode() }}
              className={`flex-1 text-xs py-1.5 font-bold rounded-md transition-colors ${
                isLive 
                  ? 'text-red-500 bg-red-500/10' 
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
              style={isLive ? { border: '1px solid rgba(239, 68, 68, 0.3)' } : {}}
            >
              Live
            </button>
          </div>
          <div className="text-[10px] uppercase tracking-wider font-bold mt-2 text-center" style={{ color: isSimulation ? 'var(--accent-green)' : 'var(--accent-red)' }}>
            {isSimulation ? 'Free Local Models' : 'Real Capital Deployment'}
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
          {navLinks.map(link => {
            const isActive = location.pathname === link.to;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                className={`block px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? 'text-blue-500 bg-blue-500/10' : 'text-gray-600 dark:text-gray-400 hover:bg-black/5 dark:hover:bg-white/5'
                }`}
              >
                {link.label}
              </NavLink>
            )
          })}
        </nav>

        <div className="p-4" style={{ borderTop: '1px solid var(--border)' }}>
          {/* User Section */}
          {isAuthenticated && user ? (
            <div className="mb-3 p-3 rounded-lg" style={{ background: 'var(--bg-primary)' }}>
              <div className="flex items-center gap-2 mb-2">
                <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <User className="w-4 h-4 text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{user.email}</p>
                  <div className="flex items-center gap-1">
                    {user.email_verified ? (
                      <span className="text-xs text-green-400 flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" /> Verified
                      </span>
                    ) : (
                      <span className="text-xs text-yellow-400">Not verified</span>
                    )}
                  </div>
                </div>
              </div>
              {user.newsletter_subscribed && (
                <p className="text-xs text-gray-500 flex items-center gap-1">
                  <Mail className="w-3 h-3" /> Newsletter active
                </p>
              )}
              <button
                onClick={() => {
                  logout()
                  navigate('/')
                }}
                className="mt-2 w-full flex items-center justify-center gap-2 py-1.5 rounded text-xs text-red-400 hover:bg-red-500/10 transition-colors"
              >
                <LogOut className="w-3 h-3" />
                Sign Out
              </button>
            </div>
          ) : (
            <button
              onClick={() => navigate('/login')}
              className="w-full flex items-center justify-center gap-2 p-2 rounded-lg transition-colors bg-blue-500/10 text-blue-400 hover:bg-blue-500/20"
            >
              <User className="w-4 h-4" />
              <span className="text-sm font-medium">Sign In</span>
            </button>
          )}

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="w-full flex items-center justify-center gap-2 p-2 rounded-lg transition-colors hover:bg-black/5 dark:hover:bg-white/5 mt-2"
            style={{ border: '1px solid var(--border)' }}
          >
            {isDark ? (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent-yellow)" strokeWidth="2">
                  <circle cx="12" cy="12" r="5" />
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
                </svg>
                <span className="text-sm font-medium text-gray-400">Light Mode</span>
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent-purple)" strokeWidth="2">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
                <span className="text-sm font-medium text-gray-600">Dark Mode</span>
              </>
            )}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto w-full">
        {/* Global Banner for extra context outside Trading context */}
        {isSimulation && location.pathname !== '/' && (
          <div className="px-6 py-2 text-xs font-bold uppercase tracking-wider text-center" style={{ color: 'var(--accent-green)', background: 'rgba(16, 185, 129, 0.1)', borderBottom: '1px solid rgba(16, 185, 129, 0.2)' }}>
            Simulation Mode Active — Using free local models for analysis
          </div>
        )}
        {isLive && location.pathname !== '/' && (
          <div className="px-6 py-2 text-xs font-bold uppercase tracking-wider text-center" style={{ color: 'var(--accent-red)', background: 'rgba(239, 68, 68, 0.1)', borderBottom: '1px solid rgba(239, 68, 68, 0.2)' }}>
            Live Mode Active — Real funds and cloud analysis enabled
          </div>
        )}

        <div className="max-w-7xl mx-auto p-6">
          <Routes>
            <Route path="/login" element={<AuthPage onSuccess={() => navigate('/')} />} />
            <Route path="/" element={isSimulation ? <BacktestPage /> : <TradingDashboard />} />
            <Route path="/risk" element={<RiskDashboardPage />} />
            <Route path="/escrow" element={<EscrowDashboard />} />
            <Route path="/notifications" element={<NotificationsPage />} />
            <Route path="/strategy" element={<StrategyPage />} />
            <Route path="/debate" element={<DebateArenaPage />} />
            <Route path="/config" element={<ConfigPage />} />
            <Route path="/security" element={<SecurityPage />} />
            <Route path="/governance" element={<GovernancePage />} />
            <Route path="/knowledge" element={<KnowledgePage />} />
            <Route path="/payments" element={<PaymentsPage />} />
            <Route path="/faq" element={<FAQPage />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}