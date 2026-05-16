/**
 * Device Context
 * ==============
 * Manages device fingerprinting and ban detection for the frontend.
 * 
 * Generates a persistent device UUID (stored in localStorage) and
 * browser fingerprint hash. Sends these as headers on every API
 * request so the backend can track and ban abusive devices.
 * 
 * If the device is banned, displays a blocking overlay.
 */
import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const DeviceContext = createContext(null);

// ─── Device ID Generation ──────────────────────────────────────────────────

function getOrCreateDeviceId() {
  const STORAGE_KEY = 'ai_trading_device_id';
  let deviceId = localStorage.getItem(STORAGE_KEY);
  if (!deviceId) {
    // Generate a UUID v4
    deviceId = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
    localStorage.setItem(STORAGE_KEY, deviceId);
  }
  return deviceId;
}

// ─── Browser Fingerprint ───────────────────────────────────────────────────

async function generateFingerprint() {
  const components = [
    navigator.userAgent || '',
    screen.width + 'x' + screen.height || '',
    Intl.DateTimeFormat().resolvedOptions().timeZone || '',
    navigator.platform || '',
    navigator.language || '',
    (screen.colorDepth || 0).toString(),
    (new Date().getTimezoneOffset()).toString(),
  ];
  
  // Join and hash using SubtleCrypto
  const raw = components.join('|');
  const encoder = new TextEncoder();
  const data = encoder.encode(raw);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return hashHex.substring(0, 32); // First 32 chars (128 bits)
}

// ─── Provider ──────────────────────────────────────────────────────────────

export function DeviceProvider({ children }) {
  const [deviceId, setDeviceId] = useState('');
  const [fingerprint, setFingerprint] = useState('');
  const [isBanned, setIsBanned] = useState(false);
  const [banReason, setBanReason] = useState('');
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    async function init() {
      const id = getOrCreateDeviceId();
      const fp = await generateFingerprint();
      setDeviceId(id);
      setFingerprint(fp);
      setInitialized(true);
    }
    init();
  }, []);

  // Check device ban status on mount
  useEffect(() => {
    if (!deviceId || !fingerprint) return;
    
    async function checkBanStatus() {
      try {
        const token = localStorage.getItem('token');
        if (!token) return;
        
        const res = await fetch(
          `/api/v1/device/status?device_id=${encodeURIComponent(deviceId)}&fingerprint_hash=${encodeURIComponent(fingerprint)}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );
        
        if (res.status === 403) {
          const data = await res.json();
          setIsBanned(true);
          setBanReason(data.detail || 'Device banned');
          return;
        }
        
        if (res.ok) {
          const data = await res.json();
          if (data.banned) {
            setIsBanned(true);
            setBanReason(data.message || 'Device banned');
          }
        }
      } catch (err) {
        // Silently fail — don't block the app if ban check fails
        console.warn('Device ban check failed:', err);
      }
    }
    
    checkBanStatus();
  }, [deviceId, fingerprint]);

  // Register device with backend on login
  const registerDevice = useCallback(async () => {
    if (!deviceId || !fingerprint) return;
    
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      
      const res = await fetch('/api/v1/device/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          device_id: deviceId,
          fingerprint_hash: fingerprint,
          user_agent: navigator.userAgent,
          screen_resolution: `${screen.width}x${screen.height}`,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          platform: navigator.platform,
          language: navigator.language,
        }),
      });
      
      if (res.status === 403) {
        const data = await res.json();
        setIsBanned(true);
        setBanReason(data.detail || 'Device banned');
      }
    } catch (err) {
      console.warn('Device registration failed:', err);
    }
  }, [deviceId, fingerprint]);

  // Get headers to include in API requests
  const getDeviceHeaders = useCallback(() => {
    if (!deviceId || !fingerprint) return {};
    
    const email = localStorage.getItem('user_email') || '';
    return {
      'X-Device-ID': deviceId,
      'X-Device-Fingerprint': fingerprint,
      'X-User-Email': email,
    };
  }, [deviceId, fingerprint]);

  const value = {
    deviceId,
    fingerprint,
    isBanned,
    banReason,
    initialized,
    registerDevice,
    getDeviceHeaders,
  };

  return (
    <DeviceContext.Provider value={value}>
      {children}
      {/* Ban overlay */}
      {isBanned && (
        <div className="fixed inset-0 z-[9999] bg-black/90 flex items-center justify-center p-4">
          <div className="bg-gray-900 border-2 border-red-500 rounded-xl p-8 max-w-lg text-center">
            <div className="text-6xl mb-4">🚫</div>
            <h2 className="text-2xl font-bold text-red-400 mb-3">Device Banned</h2>
            <p className="text-gray-300 mb-4">
              This device has been blocked from the AI Agent Trading System.
            </p>
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 mb-4">
              <p className="text-red-400 text-sm">{banReason}</p>
            </div>
            <p className="text-gray-500 text-xs">
              If you believe this is an error, please contact support.
              Device ID: {deviceId.substring(0, 8)}...
            </p>
          </div>
        </div>
      )}
    </DeviceContext.Provider>
  );
}

export function useDevice() {
  const context = useContext(DeviceContext);
  if (!context) {
    throw new Error('useDevice must be used within a DeviceProvider');
  }
  return context;
}

export default DeviceContext;
