import { useState } from 'react'
import { API_BASE } from '../App'

const STRATEGY_TEMPLATES = [
  { id: 'momentum', name: 'Momentum Scalper', icon: '🚀', desc: 'High-frequency follow for strong trend breakouts.' },
  { id: 'reversion', name: 'Mean Reversion', icon: '↔️', desc: 'Buy blood, sell euphoria. Target RSI extremes.' },
  { id: 'breakout', name: 'Volume Breakout', icon: '💥', desc: 'Enter when volume confirms key level breaches.' },
  { id: 'grid', name: 'Volatility Grid', icon: '📶', desc: 'Automatic buy/sell floors in ranging markets.' },
]

export default function StrategyPage() {
  const [selectedTemplate, setSelectedTemplate] = useState(STRATEGY_TEMPLATES[0])
  const [rules, setRules] = useState([
    { id: 1, type: 'ENTRY', condition: 'RSI < 30', value: '30', enabled: true },
    { id: 2, type: 'EXIT', condition: 'Take Profit', value: '+5%', enabled: true },
    { id: 3, type: 'EXIT', condition: 'Stop Loss', value: '-2%', enabled: true },
  ])
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    // Simulate API call to save strategy
    await new Promise(r => setTimeout(r, 1000))
    setSaving(false)
    alert('Strategy saved successfully!')
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Strategy Board</h1>
          <p className="text-sm opacity-50">Configure autonomous execution rules for your agents</p>
        </div>
        <button 
          onClick={handleSave}
          disabled={saving}
          className="btn-primary"
        >
          {saving ? 'Saving...' : '💾 Save Strategy'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Templates Sidebar */}
        <div className="space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-widest opacity-40">Library</h3>
          <div className="space-y-2">
            {STRATEGY_TEMPLATES.map(t => (
              <button
                key={t.id}
                onClick={() => setSelectedTemplate(t)}
                className={`w-full p-4 rounded-xl border text-left transition-all ${
                  selectedTemplate.id === t.id 
                    ? 'bg-blue-500/10 border-blue-500/50' 
                    : 'bg-white/5 border-white/5 hover:border-white/10'
                }`}
              >
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-xl">{t.icon}</span>
                  <span className="font-bold text-sm">{t.name}</span>
                </div>
                <p className="text-[10px] opacity-50">{t.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Rule Builder */}
        <div className="lg:col-span-2 space-y-6">
          <div className="card">
            <div className="flex justify-between items-center mb-6">
              <h3 className="font-bold flex items-center gap-2">
                <span>⚡</span> Execution Rules: {selectedTemplate.name}
              </h3>
              <button className="text-xs text-blue-400 font-bold">+ Add Rule</button>
            </div>

            <div className="space-y-3">
              {rules.map(rule => (
                <div key={rule.id} className="p-4 rounded-xl bg-white/5 border border-white/5 flex items-center justify-between group">
                  <div className="flex items-center gap-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${rule.type === 'ENTRY' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                      {rule.type}
                    </span>
                    <div>
                      <div className="text-sm font-medium">{rule.condition}</div>
                      <div className="text-[10px] opacity-40">Trigger at {rule.value}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <input type="checkbox" checked={rule.enabled} onChange={() => {}} className="accent-blue-500" />
                    <button className="opacity-0 group-hover:opacity-100 transition-opacity text-xs text-red-500/50 hover:text-red-500">Remove</button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Advanced Params */}
          <div className="card grid grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-xs font-bold opacity-50 uppercase">Max Slippage</label>
              <input type="text" defaultValue="0.5%" className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm" />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold opacity-50 uppercase">Position Size</label>
              <input type="text" defaultValue="10% Equity" className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
