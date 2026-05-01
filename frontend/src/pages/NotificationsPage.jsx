/**
 * NotificationsPage.jsx
 * =====================
 * User notification preferences and notification history.
 * 
 * Features:
- Newsletter subscription management
- Activity notification preferences
- Account status checking
- Notification history viewing
 */
import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { 
  Bell, Mail, TrendingUp, TrendingDown, Shield, Settings, 
  CheckCircle, AlertCircle, Clock, Trash2, Send, RefreshCw,
  Newspaper, BarChart3, Lock, Calendar
} from 'lucide-react';

const API_BASE = '/api/v1';

export default function NotificationsPage() {
  const { user, isAuthenticated } = useAuth();
  
  // Preferences state
  const [preferences, setPreferences] = useState({
    newsletter_enabled: true,
    trading_updates: true,
    profit_alerts: true,
    security_alerts: true,
    system_updates: true,
    daily_summary: false,
    weekly_report: true,
  });
  
  // Notifications state
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  // Load preferences and notifications
  useEffect(() => {
    if (isAuthenticated && user?.email) {
      fetchPreferences();
      fetchNotifications();
    }
  }, [isAuthenticated, user]);

  const fetchPreferences = async () => {
    try {
      const response = await fetch(`${API_BASE}/notifications/preferences?email=${encodeURIComponent(user.email)}`);
      if (response.ok) {
        const data = await response.json();
        setPreferences(data);
      }
    } catch (err) {
      console.error('Failed to fetch preferences:', err);
    }
  };

  const fetchNotifications = async () => {
    try {
      const response = await fetch(`${API_BASE}/notifications/history?email=${encodeURIComponent(user.email)}&limit=20`);
      if (response.ok) {
        const data = await response.json();
        setNotifications(data.notifications || []);
        setUnreadCount(data.unread_count || 0);
      }
      setLoading(false);
    } catch (err) {
      setError('Failed to load notifications');
      setLoading(false);
    }
  };

  const updatePreferences = async () => {
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`${API_BASE}/notifications/preferences?email=${encodeURIComponent(user.email)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
      });

      const data = await response.json();
      
      if (response.ok) {
        setSuccess('Notification preferences updated successfully!');
        setTimeout(() => setSuccess(''), 3000);
      } else {
        setError(data.detail || 'Failed to update preferences');
      }
    } catch (err) {
      setError('Failed to update preferences');
    }

    setSaving(false);
  };

  const markAsRead = async (notificationId) => {
    try {
      await fetch(`${API_BASE}/notifications/mark-read?email=${encodeURIComponent(user.email)}&notification_id=${notificationId}`, {
        method: 'POST',
      });
      fetchNotifications();
    } catch (err) {
      console.error('Failed to mark as read:', err);
    }
  };

  const markAllAsRead = async () => {
    try {
      await fetch(`${API_BASE}/notifications/mark-all-read?email=${encodeURIComponent(user.email)}`, {
        method: 'POST',
      });
      fetchNotifications();
    } catch (err) {
      console.error('Failed to mark all as read:', err);
    }
  };

  const sendAccountStatus = async () => {
    try {
      await fetch(`${API_BASE}/notifications/send-account-status?email=${encodeURIComponent(user.email)}`, {
        method: 'POST',
      });
      setSuccess('Account status email sent! Check your inbox.');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError('Failed to send account status');
    }
  };

  const sendDailySummary = async () => {
    try {
      await fetch(`${API_BASE}/notifications/send-daily-summary?email=${encodeURIComponent(user.email)}`, {
        method: 'POST',
      });
      setSuccess('Daily summary email sent! Check your inbox.');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError('Failed to send daily summary');
    }
  };

  const togglePreference = (key) => {
    setPreferences(prev => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'profit':
        return <TrendingUp className="w-5 h-5 text-green-400" />;
      case 'loss':
        return <TrendingDown className="w-5 h-5 text-red-400" />;
      case 'security':
        return <Shield className="w-5 h-5 text-blue-400" />;
      case 'trade':
        return <BarChart3 className="w-5 h-5 text-purple-400" />;
      case 'newsletter':
        return <Newspaper className="w-5 h-5 text-yellow-400" />;
      default:
        return <Bell className="w-5 h-5 text-gray-400" />;
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="p-6">
        <div className="text-center py-12">
          <Bell className="w-16 h-16 mx-auto text-gray-500 mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Sign in to manage notifications</h2>
          <p className="text-gray-400">Please sign in to view and manage your notification preferences.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg text-gray-400">Loading notifications...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Notifications</h1>
          <p className="text-gray-400 mt-1">
            Manage your notification preferences and view your notification history
          </p>
        </div>
        <div className="flex items-center gap-4">
          {unreadCount > 0 && (
            <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-sm font-medium">
              {unreadCount} unread
            </span>
          )}
          <button
            onClick={fetchNotifications}
            className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Success/Error Alerts */}
      {success && (
        <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-400" />
          <p className="text-green-400">{success}</p>
        </div>
      )}
      
      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <p className="text-red-400">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Notification Preferences */}
        <div className="bg-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Notification Preferences
          </h2>
          
          <div className="space-y-4">
            {/* Newsletter */}
            <label className="flex items-center justify-between p-3 rounded-lg bg-gray-700/50 cursor-pointer hover:bg-gray-700">
              <div className="flex items-center gap-3">
                <Newspaper className="w-5 h-5 text-yellow-400" />
                <div>
                  <p className="font-medium text-white">Newsletter</p>
                  <p className="text-xs text-gray-400">Receive newsletter updates</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={preferences.newsletter_enabled}
                onChange={() => togglePreference('newsletter_enabled')}
                className="w-5 h-5 rounded"
              />
            </label>

            {/* Trading Updates */}
            <label className="flex items-center justify-between p-3 rounded-lg bg-gray-700/50 cursor-pointer hover:bg-gray-700">
              <div className="flex items-center gap-3">
                <BarChart3 className="w-5 h-5 text-purple-400" />
                <div>
                  <p className="font-medium text-white">Trading Updates</p>
                  <p className="text-xs text-gray-400">Trade execution notifications</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={preferences.trading_updates}
                onChange={() => togglePreference('trading_updates')}
                className="w-5 h-5 rounded"
              />
            </label>

            {/* Profit Alerts */}
            <label className="flex items-center justify-between p-3 rounded-lg bg-gray-700/50 cursor-pointer hover:bg-gray-700">
              <div className="flex items-center gap-3">
                <TrendingUp className="w-5 h-5 text-green-400" />
                <div>
                  <p className="font-medium text-white">Profit/Loss Alerts</p>
                  <p className="text-xs text-gray-400">Notifications on gains and losses</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={preferences.profit_alerts}
                onChange={() => togglePreference('profit_alerts')}
                className="w-5 h-5 rounded"
              />
            </label>

            {/* Security Alerts */}
            <label className="flex items-center justify-between p-3 rounded-lg bg-gray-700/50 cursor-pointer hover:bg-gray-700">
              <div className="flex items-center gap-3">
                <Shield className="w-5 h-5 text-blue-400" />
                <div>
                  <p className="font-medium text-white">Security Alerts</p>
                  <p className="text-xs text-gray-400">Account security notifications</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={preferences.security_alerts}
                onChange={() => togglePreference('security_alerts')}
                className="w-5 h-5 rounded"
              />
            </label>

            {/* System Updates */}
            <label className="flex items-center justify-between p-3 rounded-lg bg-gray-700/50 cursor-pointer hover:bg-gray-700">
              <div className="flex items-center gap-3">
                <Bell className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="font-medium text-white">System Updates</p>
                  <p className="text-xs text-gray-400">Maintenance and feature updates</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={preferences.system_updates}
                onChange={() => togglePreference('system_updates')}
                className="w-5 h-5 rounded"
              />
            </label>

            {/* Daily Summary */}
            <label className="flex items-center justify-between p-3 rounded-lg bg-gray-700/50 cursor-pointer hover:bg-gray-700">
              <div className="flex items-center gap-3">
                <Calendar className="w-5 h-5 text-orange-400" />
                <div>
                  <p className="font-medium text-white">Daily Summary</p>
                  <p className="text-xs text-gray-400">Daily trading summary email</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={preferences.daily_summary}
                onChange={() => togglePreference('daily_summary')}
                className="w-5 h-5 rounded"
              />
            </label>

            {/* Weekly Report */}
            <label className="flex items-center justify-between p-3 rounded-lg bg-gray-700/50 cursor-pointer hover:bg-gray-700">
              <div className="flex items-center gap-3">
                <BarChart3 className="w-5 h-5 text-cyan-400" />
                <div>
                  <p className="font-medium text-white">Weekly Report</p>
                  <p className="text-xs text-gray-400">Weekly performance report</p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={preferences.weekly_report}
                onChange={() => togglePreference('weekly_report')}
                className="w-5 h-5 rounded"
              />
            </label>
          </div>

          <button
            onClick={updatePreferences}
            disabled={saving}
            className="w-full mt-6 py-3 rounded-lg font-medium flex items-center justify-center gap-2"
            style={{
              background: saving ? 'var(--gray-600)' : 'var(--accent-blue)',
              color: 'white',
            }}
          >
            {saving ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>

        {/* Quick Actions */}
        <div className="bg-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Send className="w-5 h-5" />
            Quick Actions
          </h2>
          
          <div className="space-y-3">
            <button
              onClick={sendAccountStatus}
              className="w-full p-4 rounded-lg bg-gray-700/50 hover:bg-gray-700 flex items-center gap-3 transition-colors"
            >
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Lock className="w-5 h-5 text-blue-400" />
              </div>
              <div className="flex-1 text-left">
                <p className="font-medium text-white">Send Account Status</p>
                <p className="text-xs text-gray-400">Receive an email with your current account status</p>
              </div>
              <Send className="w-4 h-4 text-gray-400" />
            </button>

            <button
              onClick={sendDailySummary}
              className="w-full p-4 rounded-lg bg-gray-700/50 hover:bg-gray-700 flex items-center gap-3 transition-colors"
            >
              <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                <Calendar className="w-5 h-5 text-green-400" />
              </div>
              <div className="flex-1 text-left">
                <p className="font-medium text-white">Send Daily Summary</p>
                <p className="text-xs text-gray-400">Get your trading summary for today</p>
              </div>
              <Send className="w-4 h-4 text-gray-400" />
            </button>

            <button
              onClick={markAllAsRead}
              className="w-full p-4 rounded-lg bg-gray-700/50 hover:bg-gray-700 flex items-center gap-3 transition-colors"
            >
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-purple-400" />
              </div>
              <div className="flex-1 text-left">
                <p className="font-medium text-white">Mark All as Read</p>
                <p className="text-xs text-gray-400">Clear all unread notifications</p>
              </div>
            </button>
          </div>

          {/* Email Info */}
          <div className="mt-6 p-4 rounded-lg bg-gray-700/30">
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-blue-400" />
              <div>
                <p className="text-sm text-gray-400">Notifications sent to:</p>
                <p className="font-mono text-white">{user?.email}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Notification History */}
      <div className="bg-gray-800 rounded-xl p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Clock className="w-5 h-5" />
            Notification History
          </h2>
          {unreadCount > 0 && (
            <button
              onClick={markAllAsRead}
              className="text-sm text-blue-400 hover:text-blue-300"
            >
              Mark all as read
            </button>
          )}
        </div>

        {notifications.length === 0 ? (
          <div className="text-center py-8">
            <Bell className="w-12 h-12 mx-auto text-gray-500 mb-3" />
            <p className="text-gray-400">No notifications yet</p>
            <p className="text-gray-500 text-sm">Notifications will appear here as you trade</p>
          </div>
        ) : (
          <div className="space-y-3">
            {notifications.map((notification) => (
              <div
                key={notification.id}
                className={`p-4 rounded-lg flex items-start gap-3 transition-colors ${
                  notification.read ? 'bg-gray-700/30' : 'bg-gray-700/70'
                }`}
                onClick={() => !notification.read && markAsRead(notification.id)}
              >
                <div className="flex-shrink-0">
                  {getNotificationIcon(notification.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-white">{notification.title}</p>
                    {!notification.read && (
                      <span className="w-2 h-2 rounded-full bg-blue-500" />
                    )}
                  </div>
                  <p className="text-sm text-gray-400 mt-1">{notification.message}</p>
                  <p className="text-xs text-gray-500 mt-2">
                    {new Date(notification.timestamp).toLocaleString()}
                  </p>
                </div>
                {!notification.read && (
                  <button
                    onClick={() => markAsRead(notification.id)}
                    className="p-1 hover:bg-white/10 rounded"
                  >
                    <CheckCircle className="w-4 h-4 text-gray-400" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}