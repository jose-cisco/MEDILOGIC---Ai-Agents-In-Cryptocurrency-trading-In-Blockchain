import { createContext, useContext, useState } from 'react'

const AppModeContext = createContext()

export function AppModeProvider({ children }) {
  // default to backtesting simulation mode
  const [activeMode, setActiveMode] = useState('simulation') // 'live' or 'simulation'

  const toggleMode = () => {
    setActiveMode(prev => prev === 'live' ? 'simulation' : 'live')
  }

  const isSimulation = activeMode === 'simulation'
  const isLive = activeMode === 'live'

  return (
    <AppModeContext.Provider value={{ activeMode, toggleMode, isSimulation, isLive, setActiveMode }}>
      {children}
    </AppModeContext.Provider>
  )
}

export function useAppMode() {
  const context = useContext(AppModeContext)
  if (!context) {
    throw new Error('useAppMode must be used within an AppModeProvider')
  }
  return context
}
