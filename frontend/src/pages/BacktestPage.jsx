import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts'
import { API_BASE } from '../App'
import { useTheme } from '../contexts/ThemeContext'
import TradingViewWidget from '../components/TradingViewWidget'

// ── Backtest model options (Strictly FREE local models via Ollama) ──────────
const BACKTEST_MODELS = [
  { id: 'glm-5.1', name: 'GLM-5.1 Reasoning', provider: 'Ollama', desc: 'Free local reasoning — Planning & Analysis' },
  { id: 'glm-5',   name: 'GLM-5 Reasoning',   provider: 'Ollama', desc: 'Free local reasoning — Technical Design' },
  { id: 'minimax-m2.7', name: 'MiniMax M2.7', provider: 'Ollama', desc: 'Free local agentic model — Tools & Logic' },
]

function BacktestRagPanel({ ragMeta }) {
  const [open, setOpen] = useState(false)
  if (!ragMeta || !ragMeta.result_count) return null
  return (
    <div
      style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border)',
        borderRadius: 10,
        marginTop: 12,
        padding: '10px 14px',
      }}
    >
      <button
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: 'var(--accent-green)',
          fontWeight: 600,
          fontSize: 13,
          padding: 0,
        }}
      >
        <span>📚 RAG Context (Backtest)</span>
        <span
          style={{
            background: 'var(--accent-green)',
            color: '#fff',
            borderRadius: 99,
            fontSize: 10,
            padding: '1px 7px',
          }}
        >
          {ragMeta.result_count} passages
        </span>
        <span style={{ marginLeft: 'auto', fontSize: 10 }}>
          {open ? '▲ collapse' : '▼ expand'}
        </span>
      </button>

      {open && (
        <div style={{ marginTop: 10, fontSize: 12 }}>
          {ragMeta.rrf_scores && ragMeta.rrf_scores.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <div style={{ color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 4 }}>
                RRF Fusion Scores (top passages)
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {ragMeta.rrf_scores.slice(0, 8).map((s, i) => (
                  <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                    <div style={{
                      width: 28, height: 50, background: 'var(--bg-primary)',
                      borderRadius: 4, position: 'relative', overflow: 'hidden',
                    }}>
                      <div style={{
                        position: 'absolute', bottom: 0, width: '100%',
                        background: 'var(--accent-green)', height: `${Math.min(s * 2000, 100)}%`,
                        transition: 'height 0.5s ease',
                      }} />
                    </div>
                    <span style={{ color: 'var(--text-secondary)' }}>{s.toFixed(3)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {ragMeta.sources && ragMeta.sources.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Sources: </span>
              {ragMeta.sources.map((s, i) => (
                <span key={i} style={{
                  background: 'var(--bg-primary)', border: '1px solid var(--border)',
                  borderRadius: 99, padding: '1px 8px', marginRight: 4, fontSize: 11,
                }}>
                  {s}
                </span>
              ))}
            </div>
          )}

          {ragMeta.summary && (
            <div style={{
              background: 'var(--bg-primary)', borderRadius: 8, padding: '8px 12px',
              borderLeft: '3px solid var(--accent-green)',
            }}>
              <div style={{ color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 4 }}>
                RAG Synthesis (Ollama)
              </div>
              <div style={{ color: 'var(--text-primary)', lineHeight: 1.6 }}>
                {ragMeta.summary}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function BacktestPage() {
  const { isDark } = useTheme()
  const [strategy, setStrategy] = useState('')
  const [tokenPair, setTokenPair] = useState('ETH/USDT')
  const [chain, setChain] = useState('ethereum')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [capital, setCapital] = useState('10000')
  const [mode, setMode] = useState('llm')
  const [backtestModel, setBacktestModel] = useState('glm-5') // Default: GLM-5 (Ollama)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [ragMeta, setRagMeta] = useState(null)
  const [error, setError] = useState('')

  const selectedModel = BACKTEST_MODELS.find(m => m.id === backtestModel)

  const runBacktest = async () => {
    setLoading(true)
    setError('')
    setResult(null)
    setRagMeta(null)
    try {
      const endpoint = mode === 'llm'
        ? `${API_BASE}/backtest/run`
        : `${API_BASE}/backtest/run-rules?token_pair=${encodeURIComponent(tokenPair)}&start_date=${startDate}&end_date=${endDate}&initial_capital=${capital}`

      const options = mode === 'llm' ? {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy: strategy || 'Momentum trading with RSI, MACD, and SMA crossover signals',
          token_pair: tokenPair,
          start_date: startDate,
          end_date: endDate,
          initial_capital: parseFloat(capital),
          chain: chain, // Use selected chain (ethereum, bitcoin, or solana)
          backtest_model: backtestModel, // Pass selected model to backend
        }),
      } : {}

      const res = await fetch(endpoint, options)
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || 'Backtest failed')
      }
      const data = await res.json()
      setResult(data)
      // Extract RAG metadata surfaced in backtest response
      if (data.rag_metadata) setRagMeta(data.rag_metadata)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  const portfolioData = result?.trades
    ? result.trades
        .filter(t => t.portfolio_value > 0)
        .map(t => ({ date: t.date.slice(5), value: t.portfolio_value, action: t.action }))
    : []

  const tradeActions = result?.trades
    ? result.trades
        .filter(t => t.action !== 'hold')
        .map(t => ({
          date: t.date.slice(5),
          amount: t.amount_usd,
          action: t.action,
          fill: t.action === 'buy' ? '#10b981' : '#ef4444',
        }))
    : []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Backtesting Engine</h1>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Test strategies with GLM-5 or GLM-5.1 (Ollama) + Hybrid RAG before live trading
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider"
               style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981', border: '1px solid rgba(16,185,129,0.3)' }}>
            🛡️ Zero-Cost Simulation Mode
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium"
               style={{ background: 'rgba(16,185,129,0.1)', color: '#10b981', border: '1px solid rgba(16,185,129,0.2)' }}>
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            x402 Payment Exempt — Backtesting is simulation, not real capital
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium"
               style={{ background: 'rgba(59,130,246,0.1)', color: '#3b82f6', border: '1px solid rgba(59,130,246,0.2)' }}>
            📚 Hybrid RAG (Semantic + BM25) — same as live trading
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium"
               style={{ background: 'rgba(16,185,129,0.1)', color: '#10b981', border: '1px solid rgba(16,185,129,0.2)' }}>
            🦙 Ollama only — GLM-5 or GLM-5.1 (free, local)
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="card space-y-4">
          <h2 className="font-semibold">Configuration</h2>

          <div>
            <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>Mode</label>
            <select value={mode} onChange={e => setMode(e.target.value)}>
              <option value="llm">LLM-Driven</option>
              <option value="rules">Rules-Based</option>
            </select>
          </div>

          {mode === 'llm' && (
            <div>
              <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>
                LLM Model
              </label>
              <select 
                value={backtestModel} 
                onChange={e => setBacktestModel(e.target.value)}
                className="w-full"
              >
                {BACKTEST_MODELS.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.name} ({opt.provider})
                  </option>
                ))}
              </select>
              <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                {selectedModel?.desc}
              </div>
              <div className="text-xs mt-1 p-1.5 rounded" 
                   style={{ background: 'rgba(16,185,129,0.1)', color: 'var(--accent-green)' }}>
                🆓 Free — runs locally with Ollama
              </div>
            </div>
          )}

          <div>
            <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>Token Pair</label>
            <select value={tokenPair} onChange={e => setTokenPair(e.target.value)}>
              <option>ETH/USDT</option>
              <option>SOL/USDT</option>
              <option>BTC/USDT</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>Chain</label>
            <select value={chain} onChange={e => setChain(e.target.value)}>
              <option value="ethereum">Ethereum</option>
              <option value="bitcoin">Bitcoin</option>
              <option value="solana">Solana</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>Start Date & Time</label>
            <input type="datetime-local" value={startDate} onChange={e => setStartDate(e.target.value)} className="w-full" />
          </div>

          <div>
            <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>End Date & Time</label>
            <input type="datetime-local" value={endDate} onChange={e => setEndDate(e.target.value)} className="w-full" />
          </div>

          <div>
            <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>Initial Capital ($)</label>
            <input type="number" value={capital} onChange={e => setCapital(e.target.value)} />
          </div>

          {mode === 'llm' && (
            <div>
              <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>Strategy Prompt</label>
              <textarea
                rows={3}
                value={strategy}
                onChange={e => setStrategy(e.target.value)}
                placeholder="e.g., Momentum trading using RSI oversold signals with MACD confirmation..."
              />
            </div>
          )}

          <button onClick={runBacktest} disabled={loading} className="btn-primary w-full">
            {loading ? 'Running Backtest...' : 'Run Backtest'}
          </button>

          {error && (
            <div className="text-sm p-2 rounded" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--accent-red)' }}>
              {error}
            </div>
          )}
        </div>

        <div className="lg:col-span-3 space-y-6">
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div className="px-6 py-4 flex items-center justify-between border-b" style={{ borderColor: 'var(--border)' }}>
              <h2 className="font-semibold text-lg flex items-center gap-2">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-green)" strokeWidth="2">
                  <path d="M3 3v18h18M7 16l4-4 4 4 5-6" />
                </svg>
                Symbol Price Action
              </h2>
              <span className="text-xs px-2 py-1 rounded" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border)' }}>
                {tokenPair}
              </span>
            </div>
            <div style={{ height: "450px", width: "100%", background: 'var(--bg-primary)' }}>
              <TradingViewWidget symbol={tokenPair} theme={isDark ? 'dark' : 'light'} />
            </div>
          </div>

          {result && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {[
                  { label: 'Total Return', value: `${result.total_return_pct.toFixed(2)}%`, positive: result.total_return_pct > 0 },
                  { label: 'Sharpe Ratio', value: result.sharpe_ratio.toFixed(2), positive: result.sharpe_ratio > 1 },
                  { label: 'Max Drawdown', value: `${result.max_drawdown_pct.toFixed(2)}%`, positive: result.max_drawdown_pct < 20 },
                  { label: 'Win Rate', value: `${result.win_rate.toFixed(1)}%`, positive: result.win_rate > 50 },
                  { label: 'Total Trades', value: result.total_trades, positive: true },
                ].map((m, i) => (
                  <div key={i} className="card text-center">
                    <div className="text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>{m.label}</div>
                    <div className={`text-xl font-bold ${m.positive ? 'metric-positive' : 'metric-negative'}`}>
                      {m.value}
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="card">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Initial Capital</div>
                      <div className="text-lg font-bold">${result.initial_capital.toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Final Capital</div>
                      <div className={`text-lg font-bold ${result.final_capital > result.initial_capital ? 'metric-positive' : 'metric-negative'}`}>
                        ${result.final_capital.toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
                <div className="card">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Win/loss</div>
                      <div>
                        <span className="metric-positive">{result.winning_trades ?? 0}</span> /{' '}
                        <span className="metric-negative">{result.losing_trades ?? 0}</span>
                      </div>
                    </div>
                    <div>
                      <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Strategy</div>
                      <div className="text-sm font-medium truncate">{result.strategy || (mode === 'llm' ? 'LLM' : 'Rules')}</div>
                    </div>
                  </div>
                </div>
              </div>

              {portfolioData.length > 0 && (
                <div className="card">
                  <h3 className="font-semibold mb-4">Portfolio Value Over Time</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={portfolioData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                      <XAxis dataKey="date" stroke="#9ca3af" fontSize={11} />
                      <YAxis stroke="#9ca3af" fontSize={11} tickFormatter={v => `$${(v / 1000).toFixed(1)}k`} />
                      <Tooltip
                        contentStyle={{ background: '#1e2235', border: '1px solid #2a2d3e', borderRadius: 8 }}
                        labelStyle={{ color: '#9ca3af' }}
                        formatter={(v) => [`$${v.toFixed(2)}`, 'Portfolio']}
                      />
                      <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {tradeActions.length > 0 && (
                <div className="card">
                  <h3 className="font-semibold mb-4">Trade Actions</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={tradeActions}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                      <XAxis dataKey="date" stroke="#9ca3af" fontSize={11} />
                      <YAxis stroke="#9ca3af" fontSize={11} tickFormatter={v => `$${v.toFixed(0)}`} />
                      <Tooltip
                        contentStyle={{ background: '#1e2235', border: '1px solid #2a2d3e', borderRadius: 8 }}
                      />
                      <Bar dataKey="amount" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              <div className="card">
                <h3 className="font-semibold mb-4">Trade Log</h3>
                <div className="overflow-x-auto max-h-96 overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0" style={{ background: 'var(--bg-card)' }}>
                      <tr style={{ borderBottom: '1px solid var(--border)' }}>
                        <th className="text-left pb-2 font-medium" style={{ color: 'var(--text-secondary)' }}>Date</th>
                        <th className="text-left pb-2 font-medium" style={{ color: 'var(--text-secondary)' }}>Action</th>
                        <th className="text-left pb-2 font-medium" style={{ color: 'var(--text-secondary)' }}>Amount</th>
                        <th className="text-left pb-2 font-medium" style={{ color: 'var(--text-secondary)' }}>Price</th>
                        <th className="text-left pb-2 font-medium" style={{ color: 'var(--text-secondary)' }}>Confidence</th>
                        <th className="text-left pb-2 font-medium" style={{ color: 'var(--text-secondary)' }}>Portfolio</th>
                        <th className="text-left pb-2 font-medium" style={{ color: 'var(--text-secondary)' }}>Reasoning</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.trades?.filter(t => t.action !== 'hold').map((t, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                          <td className="py-1.5">{t.date}</td>
                          <td className={t.action === 'buy' ? 'metric-positive' : 'metric-negative'}>
                            {t.action.toUpperCase()}
                          </td>
                          <td>${t.amount_usd?.toFixed(2)}</td>
                          <td>${t.price?.toFixed(2)}</td>
                          <td>{((t.confidence || 0) * 100).toFixed(0)}%</td>
                          <td>${t.portfolio_value?.toFixed(2)}</td>
                          <td className="max-w-48 truncate text-xs" style={{ color: 'var(--text-secondary)' }}>{t.reasoning}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* RAG Context Panel — same hybrid RAG as live trading */}
              <BacktestRagPanel ragMeta={ragMeta} />
            </>
          )}

          {!result && !loading && (
            <div className="card text-center py-16">
              <div className="text-4xl mb-4" style={{ color: 'var(--accent-blue)' }}>
                <svg className="mx-auto w-16 h-16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M3 3v18h18M7 16l4-4 4 4 5-6" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold mb-2">Ready to Backtest</h3>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Configure your strategy and run a backtest to see results here
              </p>
              <p className="text-xs mt-2" style={{ color: 'var(--text-secondary)' }}>
                Uses {selectedModel?.name || 'GLM-5'} + Hybrid RAG (same knowledge base as live trading)
              </p>
            </div>
          )}

          {loading && (
            <div className="card text-center py-16">
              <div className="animate-pulse text-lg font-semibold" style={{ color: 'var(--accent-blue)' }}>
                Running backtest with {selectedModel?.name || 'GLM-5'} + Hybrid RAG...
              </div>
              <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>
                Analyzing historical data with RAG-enhanced context and generating trading decisions
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}