import { useState, useEffect } from 'react'
import { API_BASE } from '../App'
import { useAppMode } from '../contexts/AppModeContext'

const SIMULATION_EXCHANGES = [
  { name: 'Backtest Engine', sub: 'Local Sandbox', type: 'Simulation' },
  { name: 'Paper Gateway', sub: 'Mock Broker', type: 'Paper Trading' },
  { name: 'Replay Feed', sub: 'Historical Data', type: 'Market Data' },
]

const LIVE_EXCHANGES = [
  { name: 'Binance', sub: 'Primary CEX', type: 'Execution' },
  { name: 'Bybit', sub: 'Derivatives', type: 'Execution' },
  { name: 'Base Router', sub: 'On-Chain', type: 'DEX Routing' },
]

export default function ConfigPage() {
  const { isSimulation } = useAppMode()
  const [traders, setTraders] = useState([])
  const [loading, setLoading] = useState(true)
  const [aiModels, setAiModels] = useState([])
  const exchanges = isSimulation ? SIMULATION_EXCHANGES : LIVE_EXCHANGES

  // Dynamically load aiModels based on mode
  useEffect(() => {
    if (isSimulation) {
      setAiModels([
        { name: 'GLM 5.1 Reasoning', id: 'glm-5.1', enabled: true, icon: '🧠', provider: 'Ollama', price: 'Zero-Cost Local' },
        { name: 'GLM 5 Reasoning', id: 'glm-5', enabled: true, icon: '🧠', provider: 'Ollama', price: 'Zero-Cost Local' },
        { name: 'Grok 4.20 Multi-Agent', id: 'grok-4.20', enabled: true, icon: '🛡️', provider: 'Ollama', price: 'Zero-Cost Local' },
        { name: 'MiniMax M2.7', id: 'minimax-m2.7', enabled: true, icon: '🪐', provider: 'Ollama', price: 'Zero-Cost Local' },
        { name: 'DeepSeek R1', id: 'deepseek-r1', enabled: true, icon: '🔵', provider: 'Ollama', price: 'Zero-Cost Local' },
        { name: 'Llama 3 (70B)', id: 'llama-3', enabled: true, icon: '🦙', provider: 'Ollama', price: 'Zero-Cost Local' },
        { name: 'Mistral Large', id: 'mistral-large', enabled: true, icon: '🌪️', provider: 'Ollama', price: 'Zero-Cost Local' },
      ])
    } else {
      fetch(`${API_BASE}/payments/providers/openrouter`)
        .then(res => res.json())
        .then(data => {
          if (data && Array.isArray(data.models)) {
            const dynamicModels = data.models.map(m => ({
              name: m.label,
              id: m.id,
              enabled: true,
              icon: m.id.includes('grok') ? '🛡️' : (m.id.includes('minimax') ? '🪐' : '🧠'),
              provider: 'OpenRouter',
              price: m.pricing ? `Dynamic Rate: $${(m.pricing.prompt * 1000000).toFixed(2)}/1M` : 'Provide API Key for live quotes'
            }))
            setAiModels(dynamicModels)
          } else {
            setAiModels([{ name: 'OpenRouter System', id: 'fallback', enabled: false, icon: '⚠', provider: 'OpenRouter', price: 'Provider response unavailable' }])
          }
        })
        .catch(() => {
          setAiModels([{ name: 'OpenRouter System', id: 'err', enabled: false, icon: '⚠', provider: 'OpenRouter', price: 'Dynamic Pricing Offline' }])
        })
    }
  }, [isSimulation])

  const fetchTraders = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/traders/`)
      const data = await res.json()
      setTraders(Array.isArray(data) ? data : [])
    } catch (e) {
      console.error('Failed to fetch traders', e)
      setTraders([])
    }
    setLoading(false)
  }

  // Simulate active dynamic changes to trader bots
  useEffect(() => {
    const ticker = setInterval(() => {
      setTraders(prev => prev.map(t => {
        if (t.status === 'RUNNING') {
          const currentPnl = parseFloat(t.pnl?.toString().replace('%', '')) || 0
          const shift = (Math.random() * 0.4) - 0.2 // small tick delta
          const baseEq = parseFloat(t.equity) || 10000
          
          let nextPnl = currentPnl + shift
          const sign = nextPnl >= 0 ? '+' : ''
          const pnlUsd = (baseEq * (nextPnl / 100)).toFixed(2)
          const newEq = (baseEq + parseFloat(pnlUsd)).toFixed(2)

          return {
            ...t,
            pnl: `${sign}${nextPnl.toFixed(2)}%`,
            pnl_usd: `${nextPnl >= 0 ? '+' : ''}${pnlUsd}`,
            equity: newEq
          }
        }
        return t
      }))
    }, 2500)
    return () => clearInterval(ticker)
  }, [])

  useEffect(() => {
    fetchTraders()
  }, [])

  const isOccupied = (modelId) => {
    if (!modelId) return false
    return traders.some(t => {
      if (t.status !== 'RUNNING' || !t.model) return false
      // normalize ids to catch 'z-ai/glm-5.1' matching 'glm-5.1'
      const tId = t.model.toLowerCase().replace(/[^a-z0-9]/g, '')
      const mId = modelId.toLowerCase().replace(/[^a-z0-9]/g, '').replace('zai','').replace('xai','')
      return tId.includes(mId)
    })
  }

  const toggleTrader = async (id, currentStatus) => {
    const newStatus = currentStatus === 'RUNNING' ? 'STOPPED' : 'RUNNING'
    await fetch(`${API_BASE}/traders/${id}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    })
    fetchTraders()
  }

  const deleteTrader = async (id) => {
    if (window.confirm('Delete trader instance?')) {
      await fetch(`${API_BASE}/traders/${id}`, { method: 'DELETE' })
      fetchTraders()
    }
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-yellow-500 flex items-center justify-center text-black text-xl shadow-lg shadow-yellow-500/20">🤖</div>
          <div>
            <h1 className="text-2xl font-bold">AI Traders <span className="text-xs bg-yellow-500/10 text-yellow-500 px-2 py-0.5 rounded ml-2">{traders.filter(t => t.status === 'RUNNING').length} Active</span></h1>
            <p className="text-sm opacity-50">Manage your autonomous trading bot fleet {isSimulation && <span className="text-emerald-500 font-bold ml-2">(Simulation Mode)</span>}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary text-xs">+ AI Models</button>
          <button className="btn-secondary text-xs">+ Exchanges</button>
          <button className="btn-primary text-xs flex items-center gap-2"><span>➕</span> Create Trader</button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column: AI Models */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-blue-400">🧠</span>
            <h2 className="font-bold uppercase tracking-wider text-xs opacity-70">AI Models</h2>
          </div>
          <div className="card space-y-2 p-4 max-h-[500px] overflow-y-auto">
            {aiModels.map(model => {
              const occupied = isOccupied(model.id)
              return (
              <div key={model.id} className="flex justify-between items-center p-3 rounded-lg hover:bg-white/5 transition-colors group">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded bg-white/5 flex items-center justify-center grayscale group-hover:grayscale-0 transition-all text-xl">
                    {model.icon}
                  </div>
                  <div className="flex-1">
                    <div className="font-bold text-sm flex gap-2 items-center">
                      {model.name}
                      <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${model.provider === 'OpenRouter' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'}`}>
                        {model.provider}
                      </span>
                    </div>
                    <div className="flex gap-3 mt-1 items-center">
                      <div className="text-[10px] font-mono opacity-40 truncate max-w-[150px]">{model.id}</div>
                      <div className="text-[10px] opacity-60 font-medium tracking-wide">{model.price}</div>
                    </div>
                  </div>
                </div>
                <div className={`px-2 py-1 flex items-center gap-1.5 rounded text-[9px] font-bold uppercase tracking-wider transition-all ${occupied ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-green-500/10 text-green-400 border border-green-500/20'}`}>
                  {occupied ? '🔴 Occupied' : '🟢 Vacant'}
                </div>
              </div>
            )})}
          </div>
        </div>

        {/* Right Column: Exchanges */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-yellow-400">🏛️</span>
            <h2 className="font-bold uppercase tracking-wider text-xs opacity-70">Exchanges</h2>
          </div>
          <div className="card space-y-2 p-4">
            {exchanges.map((ex, i) => (
              <div key={i} className="flex justify-between items-center p-3 rounded-lg hover:bg-white/5 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center font-bold text-xs ring-1 ring-white/10">
                    {ex.name[0]}
                  </div>
                  <div>
                    <div className="font-bold text-sm">{ex.name} <span className="font-normal opacity-50 ml-1">- {ex.sub}</span></div>
                    <div className="text-[10px] opacity-40">{ex.type} • Enabled</div>
                  </div>
                </div>
                <div className="w-2 h-2 rounded-full bg-green-500 shadow-lg shadow-green-500/40"></div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Section: Current Traders */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-purple-400">👥</span>
          <h2 className="font-bold uppercase tracking-wider text-xs opacity-70">Current Traders</h2>
        </div>
        <div className="space-y-3">
          {loading ? (
            <div className="text-center py-12 opacity-50">Loading bot instances...</div>
          ) : (
            traders.map(t => (
              <div key={t.id} className="card p-4 flex justify-between items-center group hover:border-blue-500/30 transition-all">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded bg-white/5 flex items-center justify-center text-xl">
                    {/* Placeholder for bot avatar */}
                    <span>👨‍🚀</span>
                  </div>
                  <div>
                    <h3 className="font-bold flex items-center gap-2">{t.name} <span className="text-[10px] bg-green-500/10 text-green-400 px-2 py-0.5 rounded-full">{t.status}</span></h3>
                    <div className="text-xs opacity-60 flex items-center gap-3 mt-1">
                      <span className="font-bold truncate max-w-[150px]">{t.model}</span>
                      <span className="opacity-40">•</span>
                      <span className="text-blue-400 font-medium truncate max-w-[150px]">{t.exchange}</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-6">
                  {t.status === 'RUNNING' && (
                    <div className="flex gap-4 text-xs font-mono uppercase">
                      <div><span className="opacity-40">Uptime:</span> {t.uptime}</div>
                      <div className="text-green-400 font-bold">{t.pnl}</div>
                    </div>
                  )}
                  
                  <div className="flex items-center gap-2">
                    <button className="btn-secondary py-1 text-[10px] px-2">📊 View</button>
                    <button className="btn-secondary py-1 text-[10px] px-2 opacity-30 group-hover:opacity-100 transition-opacity">✏️ Edit</button>
                    <button 
                      onClick={() => toggleTrader(t.id, t.status)}
                      className={`py-1 text-[10px] px-2 rounded font-bold transition-all ${t.status === 'RUNNING' ? 'text-red-400 hover:bg-red-500/10' : 'text-green-400 hover:bg-green-500/10'}`}
                    >
                      {t.status === 'RUNNING' ? 'Stop' : 'Start'}
                    </button>
                    <button onClick={() => deleteTrader(t.id)} className="text-[10px] text-red-500/30 hover:text-red-500 transition-colors p-2">🗑️</button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
