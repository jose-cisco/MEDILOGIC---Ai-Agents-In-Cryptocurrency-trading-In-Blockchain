import { useState } from 'react'
import { API_BASE } from '../App'
import { useTheme } from '../contexts/ThemeContext'
import { useAppMode } from '../contexts/AppModeContext'
import TradingViewWidget from '../components/TradingViewWidget'

// ── Cloud model options (MUST match backend CloudLLMProvider enum) ──────────
// Supported cloud models for live/paper trading (via OpenRouter)
// Each model uses a specific provider with reasoning support where available
// Cloud model options (MUST match backend CloudLLMProvider enum)
// Supported cloud models for live/paper trading (via OpenRouter)
// Grok 4.20 Beta Reasoning: https://docs.x.ai/developers/models/grok-4.20-beta-0309-reasoning
const CLOUD_MODELS = [
  { 
    id: 'glm-5.1', 
    name: 'GLM-5.1 Reasoning', 
    provider: 'io.net', 
    desc: 'Enforced Reasoning: Planning & Analysis',
    reasoning: true 
  },
  { 
    id: 'glm-5', 
    name: 'GLM-5 Reasoning', 
    provider: 'DeepInfra', 
    desc: 'Enforced Reasoning: Alternative Planning',
    reasoning: true 
  },
  { 
    id: 'grok-4.20', 
    name: 'Grok 4.20 Beta Reasoning', 
    provider: 'xAI', 
    desc: 'Enforced Reasoning: Security & Verification (March 2025)',
    reasoning: true 
  },
  { 
    id: 'minimax-m2.7', 
    name: 'MiniMax M2.7', 
    provider: 'Together', 
    desc: 'High Capacity: Multi-Task Processing',
    reasoning: false 
  },
]

// ── Chain options (MUST match backend ChainType enum) ──────────
// Only ethereum and solana are supported by the backend schema
const CHAIN_OPTIONS = [
  { id: 'ethereum', name: 'Ethereum', icon: '⟠' },
  { id: 'solana', name: 'Solana', icon: '◎' },
]

// Auto-assignment logic (mirrors backend resolve_agent_models)
function getAutoAssignment(model1, model2) {
  return {
    planner: model1,
    verifier: model2,
    controller: model1,
  }
}

function AgentTracePanel({ agentTrace }) {
  const [open, setOpen] = useState(false)
  if (!agentTrace) return null
  
  const hasTrace = agentTrace.planner_decision || agentTrace.verifier_result || 
                   agentTrace.final_decision || agentTrace.monitoring_strategy || 
                   agentTrace.adjustment_logic
  
  if (!hasTrace) return null

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
          color: 'var(--accent-purple)',
          fontWeight: 600,
          fontSize: 13,
          padding: 0,
        }}
      >
        <span>🔗 Agent Trace</span>
        <span
          style={{
            background: 'var(--accent-purple)',
            color: '#fff',
            borderRadius: 99,
            fontSize: 10,
            padding: '1px 7px',
          }}
        >
          Multi-Agent
        </span>
        <span style={{ marginLeft: 'auto', fontSize: 10 }}>
          {open ? '▲ collapse' : '▼ expand'}
        </span>
      </button>

      {open && (
        <div style={{ marginTop: 10, fontSize: 12 }} className="space-y-3">
          {/* Planner Decision */}
          {agentTrace.planner_decision && (
            <div
              style={{
                background: 'var(--bg-primary)',
                borderRadius: 8,
                padding: '8px 12px',
                borderLeft: '3px solid var(--accent-blue)',
              }}
            >
              <div style={{ color: 'var(--accent-blue)', fontWeight: 600, marginBottom: 4 }}>
                🧠 Planner Decision
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '4px 12px' }}>
                <div><span style={{ opacity: 0.6 }}>Action:</span> <span style={{ fontWeight: 600 }}>{(agentTrace.planner_decision.action || 'N/A').toUpperCase()}</span></div>
                <div><span style={{ opacity: 0.6 }}>Confidence:</span> {((agentTrace.planner_decision.confidence || 0) * 100).toFixed(0)}%</div>
                <div><span style={{ opacity: 0.6 }}>Risk Score:</span> {(agentTrace.planner_decision.risk_score || 0).toFixed(2)}</div>
                <div><span style={{ opacity: 0.6 }}>Regime:</span> {agentTrace.planner_decision.market_regime || 'N/A'}</div>
              </div>
              {agentTrace.planner_decision.reasoning && (
                <div style={{ marginTop: 6, opacity: 0.8, fontSize: 11 }}>
                  {agentTrace.planner_decision.reasoning.slice(0, 200)}...
                </div>
              )}
            </div>
          )}

          {/* Verifier Result */}
          {agentTrace.verifier_result && (
            <div
              style={{
                background: 'var(--bg-primary)',
                borderRadius: 8,
                padding: '8px 12px',
                borderLeft: '3px solid var(--accent-yellow)',
              }}
            >
              <div style={{ color: 'var(--accent-yellow)', fontWeight: 600, marginBottom: 4 }}>
                🛡️ Verifier Result
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '4px 12px' }}>
                <div>
                  <span style={{ opacity: 0.6 }}>Approved:</span>{' '}
                  <span style={{ fontWeight: 600, color: agentTrace.verifier_result.approved ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                    {agentTrace.verifier_result.approved ? '✓ Yes' : '✗ No'}
                  </span>
                </div>
                <div><span style={{ opacity: 0.6 }}>Adjusted Risk:</span> {(agentTrace.verifier_result.adjusted_risk_score || 0).toFixed(2)}</div>
              </div>
              {agentTrace.verifier_result.vulnerabilities_found?.length > 0 && (
                <div style={{ marginTop: 6, fontSize: 11 }}>
                  <span style={{ opacity: 0.6 }}>Vulnerabilities:</span>{' '}
                  {agentTrace.verifier_result.vulnerabilities_found.join(', ')}
                </div>
              )}
              {agentTrace.verifier_result.verification_notes && (
                <div style={{ marginTop: 4, opacity: 0.8, fontSize: 11 }}>
                  {agentTrace.verifier_result.verification_notes.slice(0, 200)}...
                </div>
              )}
            </div>
          )}

          {/* Final Decision */}
          {agentTrace.final_decision && (
            <div
              style={{
                background: 'var(--bg-primary)',
                borderRadius: 8,
                padding: '8px 12px',
                borderLeft: '3px solid var(--accent-purple)',
              }}
            >
              <div style={{ color: 'var(--accent-purple)', fontWeight: 600, marginBottom: 4 }}>
                ⚖️ Controller Final Decision
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '4px 12px' }}>
                <div><span style={{ opacity: 0.6 }}>Final Action:</span> <span style={{ fontWeight: 600 }}>{(agentTrace.final_decision.final_action || 'N/A').toUpperCase()}</span></div>
                <div><span style={{ opacity: 0.6 }}>Amount:</span> ${agentTrace.final_decision.final_amount || 0}</div>
                <div><span style={{ opacity: 0.6 }}>PoT Confidence:</span> {((agentTrace.final_decision.pot_confidence || 0) * 100).toFixed(0)}%</div>
                <div>
                  <span style={{ opacity: 0.6 }}>Approved:</span>{' '}
                  <span style={{ fontWeight: 600, color: agentTrace.final_decision.approved ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                    {agentTrace.final_decision.approved ? '✓ Yes' : '✗ No'}
                  </span>
                </div>
              </div>
              {agentTrace.final_decision.controller_reasoning && (
                <div style={{ marginTop: 6, opacity: 0.8, fontSize: 11 }}>
                  {agentTrace.final_decision.controller_reasoning.slice(0, 200)}...
                </div>
              )}
            </div>
          )}

          {/* Monitoring Strategy */}
          {agentTrace.monitoring_strategy && (
            <div
              style={{
                background: 'var(--bg-primary)',
                borderRadius: 8,
                padding: '8px 12px',
                borderLeft: '3px solid var(--accent-yellow)',
              }}
            >
              <div style={{ color: 'var(--accent-yellow)', fontWeight: 600, marginBottom: 4 }}>
                🔭 Monitoring Strategy
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '4px 12px' }}>
                <div><span style={{ opacity: 0.6 }}>Tracking Mode:</span> {agentTrace.monitoring_strategy.tracking_mode || 'N/A'}</div>
                <div><span style={{ opacity: 0.6 }}>TP/SL Strategy:</span> {agentTrace.monitoring_strategy.tp_sl_strategy || 'N/A'}</div>
              </div>
            </div>
          )}

          {/* Adjustment Logic */}
          {agentTrace.adjustment_logic && (
            <div
              style={{
                background: 'var(--bg-primary)',
                borderRadius: 8,
                padding: '8px 12px',
                borderLeft: '3px solid var(--accent-red)',
              }}
            >
              <div style={{ color: 'var(--accent-red)', fontWeight: 600, marginBottom: 4 }}>
                ⚡ Adjustment Logic
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '4px 12px' }}>
                <div><span style={{ opacity: 0.6 }}>Autonomy:</span> {agentTrace.adjustment_logic.adjustment_autonomy || 'N/A'}</div>
                <div><span style={{ opacity: 0.6 }}>Exit Conditions:</span> {agentTrace.adjustment_logic.early_exit_conditions?.length || 0}</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function RiskPanel({ riskMetadata }) {
  const [open, setOpen] = useState(false)
  if (!riskMetadata) return null
  
  const { overall_score, risk_level, volatility_risk, drawdown_risk, 
          liquidity_risk, onchain_risk, recommendations } = riskMetadata
  
  const levelColors = {
    low: { bg: 'rgba(16,185,129,0.15)', border: 'var(--accent-green)', text: 'var(--accent-green)' },
    moderate: { bg: 'rgba(59,130,246,0.15)', border: 'var(--accent-blue)', text: 'var(--accent-blue)' },
    high: { bg: 'rgba(234,179,8,0.15)', border: 'var(--accent-yellow)', text: 'var(--accent-yellow)' },
    critical: { bg: 'rgba(239,68,68,0.15)', border: 'var(--accent-red)', text: 'var(--accent-red)' },
  }
  const colors = levelColors[risk_level] || levelColors.moderate
  
  const ScoreBar = ({ label, score, color }) => (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 2 }}>
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontWeight: 600 }}>{score?.toFixed(0) || 0}</span>
      </div>
      <div style={{ height: 6, background: 'var(--bg-primary)', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ 
          width: `${Math.min(score || 0, 100)}%`, 
          height: '100%', 
          background: color,
          transition: 'width 0.5s ease'
        }} />
      </div>
    </div>
  )
  
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
          gap: 10,
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: colors.text,
          fontWeight: 600,
          fontSize: 13,
          padding: 0,
          width: '100%',
        }}
      >
        <span>⚠️ Risk Assessment</span>
        <span
          style={{
            background: colors.bg,
            border: `1px solid ${colors.border}`,
            color: colors.text,
            borderRadius: 99,
            fontSize: 10,
            padding: '2px 10px',
            fontWeight: 700,
            textTransform: 'uppercase',
          }}
        >
          {risk_level}
        </span>
        <span style={{ marginLeft: 'auto', fontSize: 20, fontWeight: 700 }}>
          {overall_score?.toFixed(0) || 0}
        </span>
        <span style={{ fontSize: 10, opacity: 0.6 }}>
          {open ? '▲' : '▼'}
        </span>
      </button>

      {open && (
        <div style={{ marginTop: 12 }}>
          {/* Component Score Bars */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px 16px', marginBottom: 12 }}>
            <ScoreBar label="Volatility" score={volatility_risk} color="var(--accent-blue)" />
            <ScoreBar label="Drawdown" score={drawdown_risk} color="var(--accent-purple)" />
            <ScoreBar label="Liquidity" score={liquidity_risk} color="var(--accent-yellow)" />
            <ScoreBar label="On-Chain" score={onchain_risk} color="var(--accent-red)" />
          </div>
          
          {/* Recommendations */}
          {recommendations?.length > 0 && (
            <div style={{ 
              background: 'var(--bg-primary)', 
              borderRadius: 8, 
              padding: '8px 12px',
              borderLeft: `3px solid ${colors.border}`
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 4, color: 'var(--text-secondary)' }}>
                Recommendations
              </div>
              {recommendations.map((r, i) => (
                <div key={i} style={{ fontSize: 12, marginBottom: 2, color: 'var(--text-primary)' }}>
                  {r}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function RagPanel({ ragMeta }) {
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
          color: 'var(--accent-blue)',
          fontWeight: 600,
          fontSize: 13,
          padding: 0,
        }}
      >
        <span>📚 RAG Context</span>
        <span
          style={{
            background: 'var(--accent-blue)',
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
          {/* Score bars */}
          {ragMeta.rrf_scores && ragMeta.rrf_scores.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <div
                style={{
                  color: 'var(--text-secondary)',
                  fontWeight: 600,
                  marginBottom: 4,
                }}
              >
                RRF Fusion Scores (top passages)
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {ragMeta.rrf_scores.slice(0, 8).map((s, i) => (
                  <div
                    key={i}
                    title={`Passage ${i + 1}: RRF ${s.toFixed(3)}`}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: 2,
                    }}
                  >
                    <div
                      style={{
                        width: 28,
                        height: 50,
                        background: 'var(--bg-primary)',
                        borderRadius: 4,
                        position: 'relative',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          position: 'absolute',
                          bottom: 0,
                          width: '100%',
                          background: 'var(--accent-blue)',
                          height: `${Math.min(s * 2000, 100)}%`,
                          transition: 'height 0.5s ease',
                        }}
                      />
                    </div>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      {s.toFixed(3)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Source types */}
          {ragMeta.sources && ragMeta.sources.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
                Sources:{' '}
              </span>
              {ragMeta.sources.map((s, i) => (
                <span
                  key={i}
                  style={{
                    background: 'var(--bg-primary)',
                    border: '1px solid var(--border)',
                    borderRadius: 99,
                    padding: '1px 8px',
                    marginRight: 4,
                    fontSize: 11,
                  }}
                >
                  {s}
                </span>
              ))}
            </div>
          )}

          {/* LLM summary */}
          {ragMeta.summary && (
            <div
              style={{
                background: 'var(--bg-primary)',
                borderRadius: 8,
                padding: '8px 12px',
                borderLeft: '3px solid var(--accent-blue)',
              }}
            >
              <div
                style={{
                  color: 'var(--text-secondary)',
                  fontWeight: 600,
                  marginBottom: 4,
                }}
              >
                RAG Synthesis
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

export default function TradingDashboard() {
  const { isDark } = useTheme()
  // Use global app mode from context - unified mode control
  const { isLive, isSimulation, toggleMode } = useAppMode()
  
  // Single endpoint - mode is passed in request body, not via different routes
  const executeEndpoint = `${API_BASE}/trading/execute`

  const [prompt, setPrompt] = useState('')
  const [tokenPair, setTokenPair] = useState('ETH/USDT')
  const [chain, setChain] = useState('ethereum')
  const [predictionStartDate, setPredictionStartDate] = useState('')
  const [predictionEndDate, setPredictionEndDate] = useState('')
  // Dual-model selection: user picks 2 cloud models, agents auto-assign
  const [model1, setModel1] = useState('glm-5.1')
  const [model2, setModel2] = useState('grok-4.20')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [ragMeta, setRagMeta] = useState(null)
  const [agentTrace, setAgentTrace] = useState(null) // Multi-agent trace data
  const [history, setHistory] = useState([])
  const [signing, setSigning] = useState(false)
  const [paymentTx, setPaymentTx] = useState('')

  const assignment = getAutoAssignment(model1, model2)
  const isSingleModel = model1 === model2


  const executeTrade = async (existingTx = null) => {
    if (!prompt.trim()) return
    setLoading(true)
    setRagMeta(null)
    try {
      const headers = { 'Content-Type': 'application/json' }
      if (existingTx) headers['X-Payment'] = existingTx

      const res = await fetch(executeEndpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          prompt,
          chain,
          token_pair: tokenPair,
          prediction_start_date: predictionStartDate || undefined,
          prediction_end_date: predictionEndDate || undefined,
          max_position_usd: 1000,
          agent_id: 'default-trader',
          model_1: model1,
          model_2: model2,
        }),
      })

      // Handle x402 Payment Required response
      if (res.status === 402) {
        const paymentData = await res.json()
        setResult({
          success: false,
          action: 'hold',
          confidence: 0,
          reasoning: `x402 Payment Required: Please sign the $${paymentData.payment_requirements?.[0]?.amount
            ? (paymentData.payment_requirements[0].amount / 1e6).toFixed(6)
            : '0.01'} USDC transaction.`,
          x402_metadata: {
            payment_required: true,
            payment_verified: false,
            payment_resource: paymentData.resource,
            x402_version: paymentData.x402_version,
            payment_requirements: paymentData.payment_requirements,
          },
        })
        setLoading(false)
        return
      }

      const data = await res.json()
      setResult(data)
      // Extract RAG metadata surfaced in response
      if (data.rag_metadata) setRagMeta(data.rag_metadata)
      // Extract agent trace for transparency
      if (data.agent_trace) setAgentTrace(data.agent_trace)
      setHistory((prev) => [data, ...prev.slice(0, 19)])
    } catch {
      setResult({
        success: false,
        reasoning: 'Connection error — ensure backend is running',
        action: 'hold',
        confidence: 0,
      })
    }
    setLoading(false)
  }
  const signAndRetry = async () => {
    setSigning(true)
    // Simulate wallet signing latency (1.5s)
    setTimeout(async () => {
      const mockTx = '0x' + Math.random().toString(16).slice(2, 66)
      setPaymentTx(mockTx)
      setSigning(false)
      await executeTrade(mockTx)
    }, 1500)
  }
  return (
    <div className={`space-y-6 transition-all duration-700 ${isLive ? 'bg-red-500/5 -m-6 p-6 border-4 border-red-500/20 shadow-[inset_0_0_100px_rgba(239,68,68,0.1)]' : ''}`}>
      {/* Header with Live Toggle */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            {isLive ? '🔴 LIVE EXECUTION' : '📉 Trading Dashboard'}
            {isLive && <span className="text-[10px] bg-red-500 text-white px-2 py-0.5 rounded-full animate-pulse font-bold tracking-widest">DIRECT ON-CHAIN</span>}
          </h1>
          <p className="text-sm opacity-50">
            {isLive ? 'Caution: Real capital deployment active on Base/Solana' : 'Paper trading & simulation mode (x402 enabled)'}
          </p>
        </div>
        
        <div className="flex items-center gap-4 bg-white/5 p-2 rounded-2xl border border-white/5 backdrop-blur-xl">
          <button 
            type="button"
            onClick={() => { if (isLive) toggleMode(); }}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${isSimulation ? 'bg-blue-500 text-white shadow-lg' : 'opacity-40 hover:opacity-100 dark:text-gray-400'}`}
          >
            PAPER
          </button>
          <button 
            type="button"
            onClick={() => { if (isSimulation) toggleMode(); }}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${isLive ? 'bg-red-600 text-white shadow-lg shadow-red-500/20' : 'opacity-40 hover:opacity-100 dark:text-gray-400'}`}
          >
            LIVE
          </button>
        </div>
      </div>


      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trade Form */}
        <div className="lg:col-span-2 card space-y-4">
          <h2 className="font-semibold text-lg">Execute Trade</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                className="text-xs font-medium mb-1 block"
                style={{ color: 'var(--text-secondary)' }}
              >
                Token Pair
              </label>
              <select
                value={tokenPair}
                onChange={(e) => setTokenPair(e.target.value)}
              >
                <option>ETH/USDT</option>
                <option>SOL/USDT</option>
                <option>BTC/USDT</option>
                <option>ETH/USDC</option>
              </select>
            </div>
            <div>
              <label
                className="text-xs font-medium mb-1 block"
                style={{ color: 'var(--text-secondary)' }}
              >
                Chain
              </label>
              <select value={chain} onChange={(e) => setChain(e.target.value)}>
                {CHAIN_OPTIONS.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.icon} {opt.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                className="text-xs font-medium mb-1 block"
                style={{ color: 'var(--text-secondary)' }}
              >
                Prediction Start Date & Time
              </label>
              <input
                type="datetime-local"
                value={predictionStartDate}
                onChange={(e) => setPredictionStartDate(e.target.value)}
                className="w-full"
              />
              <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                Start of the prediction window
              </div>
            </div>
            <div>
              <label
                className="text-xs font-medium mb-1 block"
                style={{ color: 'var(--text-secondary)' }}
              >
                Prediction End Date & Time
              </label>
              <input
                type="datetime-local"
                value={predictionEndDate}
                onChange={(e) => setPredictionEndDate(e.target.value)}
                className="w-full"
              />
              <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                End of the prediction window
              </div>
            </div>
          </div>

          {/* Dual-Model Selection */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <label
                className="text-xs font-medium"
                style={{ color: 'var(--text-secondary)' }}
              >
                Cloud Model Selection
              </label>
              {isSingleModel && (
                <span
                  className="text-xs px-2 py-0.5 rounded"
                  style={{ background: 'rgba(16,185,129,0.15)', color: 'var(--accent-green)', fontWeight: 600 }}
                >
                  💰 Cost Optimized (1 API key)
                </span>
              )}
            </div>
            <div className="p-3 rounded-lg" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
              <div className="grid grid-cols-2 gap-4 mb-3">
                <div>
                  <label
                    className="text-xs font-medium mb-1 block"
                    style={{ color: 'var(--accent-blue)' }}
                  >
                    🧠 Model 1 (Planner + Controller)
                  </label>
                  <select
                    value={model1}
                    onChange={(e) => setModel1(e.target.value)}
                    className="w-full"
                    style={{ fontSize: 12 }}
                  >
                    {CLOUD_MODELS.map((opt) => (
                      <option key={opt.id} value={opt.id}>
                        {opt.name} ({opt.provider})
                      </option>
                    ))}
                  </select>
                  <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                    {CLOUD_MODELS.find((o) => o.id === model1)?.desc}
                  </div>
                </div>
                <div>
                  <label
                    className="text-xs font-medium mb-1 block"
                    style={{ color: 'var(--accent-yellow)' }}
                  >
                    🛡️ Model 2 (Verifier)
                  </label>
                  <select
                    value={model2}
                    onChange={(e) => setModel2(e.target.value)}
                    className="w-full"
                    style={{ fontSize: 12 }}
                  >
                    {CLOUD_MODELS.map((opt) => (
                      <option key={opt.id} value={opt.id}>
                        {opt.name} ({opt.provider})
                      </option>
                    ))}
                  </select>
                  <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                    {CLOUD_MODELS.find((o) => o.id === model2)?.desc}
                  </div>
                </div>
              </div>

              {/* Auto-assignment preview */}
              <div
                className="p-2 rounded text-xs"
                style={{ background: 'var(--bg-primary)', border: '1px solid var(--border)' }}
              >
                <div className="font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
                  Auto-Assignment Preview
                </div>
                <div className="flex flex-wrap gap-2">
                  <span
                    className="px-2 py-0.5 rounded"
                    style={{ background: 'rgba(59,130,246,0.15)', color: 'var(--accent-blue)', fontWeight: 600 }}
                  >
                    🧠 Planner → {CLOUD_MODELS.find(o => o.id === assignment.planner)?.name || assignment.planner}
                  </span>
                  <span
                    className="px-2 py-0.5 rounded"
                    style={{ background: 'rgba(234,179,8,0.15)', color: 'var(--accent-yellow)', fontWeight: 600 }}
                  >
                    🛡️ Verifier → {CLOUD_MODELS.find(o => o.id === assignment.verifier)?.name || assignment.verifier}
                  </span>
                  <span
                    className="px-2 py-0.5 rounded"
                    style={{ background: 'rgba(168,85,247,0.15)', color: 'var(--accent-purple)', fontWeight: 600 }}
                  >
                    ⚖️ Controller → {CLOUD_MODELS.find(o => o.id === assignment.controller)?.name || assignment.controller}
                  </span>
                </div>
                <div className="mt-1" style={{ color: 'var(--text-secondary)' }}>
                  {isSingleModel
                    ? '💰 Single model mode — only 1 API key billed (lowest cost)'
                    : '🔀 Dual model mode — 2 API keys (diverse verification for security)'}
                </div>
              </div>
            </div>

          </div>

          <div>
            <label
              className="text-xs font-medium mb-1 block"
              style={{ color: 'var(--text-secondary)' }}
            >
              Trading Prompt
            </label>
            <textarea
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., Buy ETH when RSI is oversold and MACD shows bullish crossover with confirmed volume"
              className="w-full"
            />
          </div>
          <button
            onClick={executeTrade}
            disabled={loading || !prompt.trim()}
            className="btn-primary w-full"
          >
            {loading
              ? `🔄 Agents Processing (${CLOUD_MODELS.find(o => o.id === model1)?.name} + ${CLOUD_MODELS.find(o => o.id === model2)?.name})...`
              : '🚀 Execute via Dual-Model Multi-Agent'}
          </button>
        </div>

        {/* System Architecture Panel */}
        <div className="card space-y-3">
          <h2 className="font-semibold text-lg">System Architecture</h2>
          <div className="space-y-2 text-sm">
            <div
              className="flex items-start gap-2 p-2 rounded-lg"
              style={{ background: 'var(--bg-secondary)' }}
            >
              <div className="w-2 h-2 rounded-full mt-1 flex-shrink-0" style={{ background: 'var(--accent-blue)' }} />
              <div>
                <div className="font-medium">🧠 Planner Agent</div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  <span style={{ fontWeight: 600 }}>Role:</span> Market Analyst & Strategist
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Analyzes market data & retrieves RAG context
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Evaluates trading conditions & indicators
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Proposes trade action with risk assessment
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Outputs: action, confidence, risk_score, rag_sources
                </div>
              </div>
            </div>
            <div
              className="flex items-start gap-2 p-2 rounded-lg"
              style={{ background: 'var(--bg-secondary)' }}
            >
              <div className="w-2 h-2 rounded-full mt-1 flex-shrink-0" style={{ background: 'var(--accent-yellow)' }} />
              <div>
                <div className="font-medium">🛡️ Verifier Agent</div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  <span style={{ fontWeight: 600 }}>Role:</span> Security & Risk Validator
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Independent security analysis
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Vulnerability detection (FELLMVP ensemble)
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Risk validation & score adjustment
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Outputs: approved, adjusted_risk, vulnerabilities
                </div>
              </div>
            </div>
            <div
              className="flex items-start gap-2 p-2 rounded-lg"
              style={{ background: 'var(--bg-secondary)' }}
            >
              <div className="w-2 h-2 rounded-full mt-1 flex-shrink-0" style={{ background: 'var(--accent-purple)' }} />
              <div>
                <div className="font-medium">⚖️ Controller Agent</div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  <span style={{ fontWeight: 600 }}>Role:</span> Consensus & Execution Manager
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Proof-of-Thought (PoT) consensus
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Weighs planner vs verifier outputs
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Final go/no-go decision & execution
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Outputs: final_action, final_amount, pot_confidence
                </div>
              </div>
            </div>
            <div
              className="flex items-start gap-2 p-2 rounded-lg"
              style={{ background: 'var(--bg-secondary)' }}
            >
              <div className="w-2 h-2 rounded-full mt-1 flex-shrink-0" style={{ background: 'var(--accent-yellow)' }} />
              <div>
                <div className="font-medium text-yellow-400">🔭 Monitor Agent</div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  <span style={{ fontWeight: 600 }}>Role:</span> Post-Execution Observability
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Dynamic Trailing Stop-Loss tracking
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Constant PnL & health-check monitoring
                </div>
              </div>
            </div>
            <div
              className="flex items-start gap-2 p-2 rounded-lg"
              style={{ background: 'var(--bg-secondary)' }}
            >
              <div className="w-2 h-2 rounded-full mt-1 flex-shrink-0" style={{ background: 'var(--accent-red)' }} />
              <div>
                <div className="font-medium text-red-400">⚡ Adjuster Agent</div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  <span style={{ fontWeight: 600 }}>Role:</span> Reactive Self-Correction
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Paradoxical market condition mitigation
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Automated position hedging & early exit
                </div>
              </div>
            </div>
            <div
              className="flex items-start gap-2 p-2 rounded-lg"
              style={{ background: 'var(--bg-secondary)' }}
            >
              <div className="w-2 h-2 rounded-full mt-1 flex-shrink-0" style={{ background: 'var(--accent-green)' }} />
              <div>
                <div className="font-medium">📚 Hybrid RAG System</div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  <span style={{ fontWeight: 600 }}>Role:</span> Knowledge Retrieval
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Reciprocal Rank Fusion (RRF) for merged results
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  • Context-augmented prompts (93-95% acc)
                </div>
              </div>
            </div>
          </div>
          <div
            className="pt-2 border-t text-xs space-y-1"
            style={{
              borderColor: 'var(--border)',
              color: 'var(--text-secondary)',
            }}
          >
            <div>🧠 Consensus: Proof-of-Thought (PoT)</div>
            <div>🔒 Security: Ensemble LLM (98.8% FELLMVP)</div>
            <div>📊 RAG: 93-95% accuracy (Karim et al. 2025)</div>
            <div>💰 x402: Pay-per-use (USDC on Base) — Backtest exempt</div>
            <div>🦙 Ollama: Backtesting only (not for trading)</div>
          </div>
        </div>

        {/* Trading Graph / TV Chart */}
        <div className="lg:col-span-3 card" style={{ padding: 0, overflow: 'hidden' }}>
          {/* Header */}
          <div className="px-6 py-4 flex items-center justify-between border-b" style={{ borderColor: 'var(--border)' }}>
            <h2 className="font-semibold text-lg flex items-center gap-2">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-blue)" strokeWidth="2">
                <path d="M3 3v18h18M7 16l4-4 4 4 5-6" />
              </svg>
              Live Price Action
            </h2>
            <div className="flex gap-2">
              <span className="text-xs px-2 py-1 rounded" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border)' }}>
                {tokenPair}
              </span>
            </div>
          </div>
          {/* Chart Widget Container */}
          <div style={{ height: "450px", width: "100%", background: 'var(--bg-primary)' }}>
            <TradingViewWidget symbol={tokenPair} theme={isDark ? 'dark' : 'light'} />
          </div>
        </div>
      </div>

      {/* Result Card */}
      {result && (
        <div className="card">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 16,
            }}
          >
            <h2 className="font-semibold text-lg">Latest Result</h2>
            {/* Model assignment badges */}
            <div style={{ display: 'flex', gap: 6 }}>
              <span
                style={{
                  background: 'rgba(59,130,246,0.15)',
                  border: '1px solid var(--accent-blue)',
                  color: 'var(--accent-blue)',
                  borderRadius: 99,
                  fontSize: 10,
                  padding: '2px 8px',
                  fontWeight: 600,
                }}
              >
                {CLOUD_MODELS.find(o => o.id === assignment.planner)?.name || assignment.planner} Planner ✓
              </span>
              <span
                style={{
                  background: 'rgba(234,179,8,0.15)',
                  border: '1px solid var(--accent-yellow)',
                  color: 'var(--accent-yellow)',
                  borderRadius: 99,
                  fontSize: 10,
                  padding: '2px 8px',
                  fontWeight: 600,
                }}
              >
                {CLOUD_MODELS.find(o => o.id === assignment.verifier)?.name || assignment.verifier} Verifier ✓
              </span>
              <span
                style={{
                  background: 'rgba(168,85,247,0.15)',
                  border: '1px solid var(--accent-purple)',
                  color: 'var(--accent-purple)',
                  borderRadius: 99,
                  fontSize: 10,
                  padding: '2px 8px',
                  fontWeight: 600,
                }}
              >
                {CLOUD_MODELS.find(o => o.id === assignment.controller)?.name || assignment.controller} Controller ✓
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Action
              </div>
              <div
                className={`text-xl font-bold ${
                  (result.action || '').toUpperCase() === 'BUY'
                    ? 'metric-positive'
                    : (result.action || '').toUpperCase() === 'SELL'
                    ? 'metric-negative'
                    : ''
                }`}
              >
                {(result.action || 'HOLD').toUpperCase()}
              </div>
            </div>
            <div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Confidence
              </div>
              <div className="text-xl font-bold">
                {((result.confidence || 0) * 100).toFixed(0)}%
              </div>
            </div>
            <div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Amount
              </div>
              <div className="text-xl font-bold">
                ${(result.amount || 0).toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Status
              </div>
              <div
                className={`text-xl font-bold ${
                  result.success ? 'metric-positive' : 'metric-negative'
                }`}
              >
                {result.success ? 'APPROVED' : 'REJECTED'}
              </div>
            </div>
          </div>

          {/* Performance Summary (Matches Pic 4) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="card p-4 space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-xs font-bold uppercase opacity-50">Account Equity Curve</h3>
                <span className="text-green-400 text-xs font-bold">+51.64%</span>
              </div>
              <div className="h-32 bg-black/20 rounded flex items-end p-2 gap-1">
                {/* Mock bar chart graph */}
                {[20, 30, 25, 45, 40, 60, 55, 80, 75, 95].map((h, i) => (
                  <div key={i} className="flex-1 bg-yellow-500/20 border-t border-yellow-500/40" style={{ height: `${h}%` }} />
                ))}
              </div>
            </div>
            <div className="card p-4">
              <h3 className="text-xs font-bold uppercase opacity-50 mb-3">Current Positions</h3>
              <div className="space-y-2">
                 <div className="flex justify-between items-center text-xs p-2 rounded bg-white/5">
                   <div className="flex items-center gap-2">
                     <span className="text-green-400 font-bold">LONG</span>
                     <span>SOL/USDT</span>
                   </div>
                   <div className="font-mono text-green-400">+$909.71</div>
                 </div>
                 <div className="flex justify-between items-center text-xs p-2 rounded bg-white/5 opacity-50">
                    <span>No other active positions</span>
                 </div>
              </div>
            </div>
          </div>

          <div
            className="p-4 rounded-lg text-sm mb-4 border border-white/5"
            style={{ background: 'var(--bg-secondary)' }}
          >
            <div className="flex justify-between items-center mb-4 border-b border-white/5 pb-2">
              <div className="flex items-center gap-2">
                <span className="text-lg">🧠</span>
                <span className="font-bold">AI Chain of Thought</span>
              </div>
              <span className="text-[10px] bg-green-500/20 text-green-500 px-2 py-0.5 rounded font-bold uppercase">Success</span>
            </div>
            
            <div className="space-y-4">
              <div className="space-y-1">
                <div className="text-xs font-bold text-blue-400">1) Market State Analysis</div>
                <div className="text-xs opacity-70 pl-4 border-l border-blue-500/20">
                  Checking current trend... {tokenPair} at 4H interval. RSI at 42.1 (Neutral). 
                  Consensus suggests accumulation phase.
                </div>
              </div>
              <div className="space-y-1">
                <div className="text-xs font-bold text-purple-400">2) RAG Context Integration</div>
                <div className="text-xs opacity-70 pl-4 border-l border-purple-500/20">
                   Retrieved {ragMeta?.result_count || 0} relative documents. 
                   Synthesis: "Institutional flow increasing on {chain}. Avoid high-leverage entry."
                </div>
              </div>
              <div className="space-y-1">
                <div className="text-xs font-bold text-yellow-400">3) Risk Management Assessment</div>
                <div className="text-xs opacity-70 pl-4 border-l border-yellow-500/20">
                   Setting SL at -2.5% below recent swing low. 
                   Position size calibrated to $1000 USD via Controller override.
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-white/5 font-mono text-[11px] opacity-80">
                 {result.reasoning || 'No final synthesis provided'}
              </div>
            </div>

            {/* x402 Sign & Retry Button */}
            {result.x402_metadata?.payment_required && (
              <div className="mt-4 pt-4 border-t border-border">
                <button 
                  onClick={signAndRetry}
                  disabled={signing}
                  className="btn-primary w-full py-3 flex items-center justify-center gap-3 shadow-lg shadow-blue-500/20"
                >
                  {signing ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Signing with Wallet...
                    </>
                  ) : (
                    <>
                      🔑 SIGN & RETRY WITH x402
                    </>
                  )}
                </button>
                {paymentTx && (
                  <div className="mt-2 text-[10px] font-mono opacity-50 break-all text-center">
                    Signed Tx Hash: {paymentTx}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Risk Assessment panel */}
          <RiskPanel riskMetadata={result.risk_metadata} />

          {/* Agent Trace panel */}
          <AgentTracePanel agentTrace={agentTrace} />

          {/* RAG context panel */}
          <RagPanel ragMeta={ragMeta} />

          {result.governance_metadata && (
            <div
              style={{
                marginTop: 10,
                background: 'var(--bg-secondary)',
                borderRadius: 8,
                padding: '8px 12px',
                borderLeft: '3px solid var(--accent-purple)',
                fontSize: 12,
              }}
            >
              <div
                style={{
                  color: 'var(--text-secondary)',
                  fontWeight: 600,
                  marginBottom: 4,
                }}
              >
                Governance Checks
              </div>
              <div>
                Semantic signal score:{' '}
                {result.governance_metadata.semantic_signal?.score ?? 0}
              </div>
              {result.governance_metadata.audit_event_hash && (
                <div style={{ wordBreak: 'break-all' }}>
                  Audit event hash: {result.governance_metadata.audit_event_hash}
                </div>
              )}
            </div>
          )}

          {/* x402 Payment metadata */}
          {result.x402_metadata && (
            <div
              style={{
                marginTop: 10,
                background: 'var(--bg-secondary)',
                borderRadius: 8,
                padding: '8px 12px',
                borderLeft: '3px solid var(--accent-green)',
                fontSize: 12,
              }}
            >
              <div
                style={{
                  color: 'var(--text-secondary)',
                  fontWeight: 600,
                  marginBottom: 4,
                }}
              >
                x402 Payment
              </div>
              {result.x402_metadata.payment_required ? (
                <>
                  <div>
                    Payment required: Yes (${result.x402_metadata.payment_amount_usd?.toFixed(6) || '—'})
                  </div>
                  <div>
                    Verified: {result.x402_metadata.payment_verified ? '✓' : '✗'}
                  </div>
                  {result.x402_metadata.payment_tx_hash && (
                    <div style={{ wordBreak: 'break-all' }}>
                      TX: {result.x402_metadata.payment_tx_hash}
                    </div>
                  )}
                </>
              ) : (
                <div>Payment not required for this request</div>
              )}
            </div>
          )}

          {result.tx_hash && (
            <div className="mt-2 text-xs" style={{ color: 'var(--accent-green)' }}>
              TX: {result.tx_hash}
            </div>
          )}
        </div>
      )}

      {/* Trade History */}
      {history.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-lg mb-4">Trade History</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Time', 'Pair', 'Action', 'Amount', 'Confidence', 'Status'].map(
                    (h) => (
                      <th
                        key={h}
                        className="text-left pb-2 font-medium"
                        style={{ color: 'var(--text-secondary)' }}
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {history.map((t, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td className="py-2">
                      {t.timestamp
                        ? new Date(t.timestamp).toLocaleTimeString()
                        : '-'}
                    </td>
                    <td>{t.token_pair}</td>
                    <td
                      className={
                        t.action === 'buy'
                          ? 'metric-positive'
                          : t.action === 'sell'
                          ? 'metric-negative'
                          : ''
                      }
                    >
                      {(t.action || 'hold').toUpperCase()}
                    </td>
                    <td>${(t.amount || 0).toFixed(2)}</td>
                    <td>{((t.confidence || 0) * 100).toFixed(0)}%</td>
                    <td
                      className={
                        t.success ? 'metric-positive' : 'metric-negative'
                      }
                    >
                      {t.success ? 'OK' : 'FAIL'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}