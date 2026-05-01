import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const ThemeContext = createContext()

/**
 * Determines if it's currently nighttime based on local time or timezone
 * Nighttime is considered 6 PM (18:00) to 6 AM (06:00)
 * @param {string} timezone - Optional timezone string (e.g., 'Asia/Bangkok')
 * @returns {Promise<boolean>} true if nighttime, false if daytime
 */
async function isNighttimeWithTimezone(timezone) {
  // Try to get from API for accurate timezone detection
  try {
    const response = await fetch(`/api/v1/auth/timezone?tz=${encodeURIComponent(timezone || 'UTC')}`)
    const data = await response.json()
    return !data.is_daytime
  } catch (error) {
    // Fallback to local calculation
    return isNighttime()
  }
}

/**
 * Determines if it's currently nighttime based on local time
 * Nighttime is considered 6 PM (18:00) to 6 AM (06:00)
 * @returns {boolean} true if nighttime, false if daytime
 */
function isNighttime() {
  const hour = new Date().getHours()
  // Nighttime: 6 PM (18:00) to 6 AM (06:00)
  return hour >= 18 || hour < 6
}

export function ThemeProvider({ children }) {
  const [isDark, setIsDark] = useState(() => {
    // Initialize based on current time
    return isNighttime()
  })
  
  const [autoTheme, setAutoTheme] = useState(() => {
    const saved = localStorage.getItem('autoTheme')
    return saved !== 'false' // Default to auto theme
  })
  
  const [timezone, setTimezone] = useState(() => {
    return localStorage.getItem('userTimezone') || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
  })

  // Apply theme to document root
  useEffect(() => {
    const root = document.documentElement
    if (isDark) {
      root.classList.add('dark')
      root.classList.remove('light')
    } else {
      root.classList.add('light')
      root.classList.remove('dark')
    }
    localStorage.setItem('theme', isDark ? 'dark' : 'light')
  }, [isDark])

  // Auto theme switching based on time of day
  useEffect(() => {
    if (!autoTheme) return
    
    const updateThemeByTime = async () => {
      const shouldBeDark = await isNighttimeWithTimezone(timezone)
      setIsDark(prevIsDark => {
        if (prevIsDark !== shouldBeDark) {
          return shouldBeDark
        }
        return prevIsDark
      })
    }

    // Check immediately
    updateThemeByTime()

    // Check every minute
    const interval = setInterval(updateThemeByTime, 60000)

    return () => clearInterval(interval)
  }, [autoTheme, timezone])

  // Listen for timezone changes from user profile
  useEffect(() => {
    const handleTimezoneUpdate = (event) => {
      if (event.detail?.timezone) {
        setTimezone(event.detail.timezone)
        localStorage.setItem('userTimezone', event.detail.timezone)
      }
    }
    
    window.addEventListener('timezoneUpdate', handleTimezoneUpdate)
    return () => window.removeEventListener('timezoneUpdate', handleTimezoneUpdate)
  }, [])

  // Manual toggle function
  const toggleTheme = useCallback(() => {
    // When manually toggling, disable auto theme
    if (autoTheme) {
      setAutoTheme(false)
      localStorage.setItem('autoTheme', 'false')
    }
    setIsDark(prev => !prev)
  }, [autoTheme])

  // Enable automatic theme switching
  const enableAutoTheme = useCallback(() => {
    setAutoTheme(true)
    localStorage.setItem('autoTheme', 'true')
  }, [])

  // Disable automatic theme switching
  const disableAutoTheme = useCallback(() => {
    setAutoTheme(false)
    localStorage.setItem('autoTheme', 'false')
  }, [])

  // Set user's timezone
  const setUserTimezone = useCallback((tz) => {
    setTimezone(tz)
    localStorage.setItem('userTimezone', tz)
    // Dispatch event for other components
    window.dispatchEvent(new CustomEvent('timezoneUpdate', { detail: { timezone: tz } }))
  }, [])

  // Get current theme name
  const theme = isDark ? 'dark' : 'light'

  return (
    <ThemeContext.Provider value={{ 
      isDark, 
      theme, 
      toggleTheme,
      autoTheme,
      enableAutoTheme,
      disableAutoTheme,
      timezone,
      setUserTimezone
    }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

export default ThemeContext