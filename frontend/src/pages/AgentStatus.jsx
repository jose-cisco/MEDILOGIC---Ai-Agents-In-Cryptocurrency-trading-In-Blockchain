import { useState, useEffect } from 'react'
import { API_BASE } from '../App'

export default function AgentStatus() {
  const [agents, setAgents] = useState([])
  const [blockchain, setBlockchain] = useState(null)
  const [system, setSystem] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const [agentsRes, chainRes, sysRes] = await Promise.all([
          fetch(`${API_BASE}/status/agents`),
          fetch(`${API_BASE}/status/blockchain`),
          fetch(`${API_BASE}/status/system`),
        ])
        setAgents((await agentsRes.json()).agents || [])
        setBlockchain(await chainRes.json())
        setSystem((await sysRes.json()))
      } catch (e) {
        setAgents([])
      }
      setLoading(false)
    }
    fetchStatus()
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="text-center py-16">Loading system status...</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Agent & System Status</h1>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          BlockAgents framework: Identity Registry, Bill Registry, Incentive Management, Verification Agent, Consensus Agreement
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {agents.map((agent, i) => (
          <div key={i} className="card">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold">{agent.agent_name}</h3>
              <span className="text-xs px-2 py-0.5 rounded metric-positive" style={{ background: 'rgba(16,185,129,0.1)' }}>
                {agent.status}
              </span>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-secondary)' }}>Total Decisions</span>
                <span className="font-medium">{agent.total_decisions}</span>
              </div>
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-secondary)' }}>Successful</span>
                <span className="font-medium metric-positive">{agent.successful_trades}</span>
              </div>
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-secondary)' }}>Success Rate</span>
                <span className="font-medium">
                  {agent.total_decisions > 0 ? ((agent.successful_trades / agent.total_decisions) * 100).toFixed(1) : 0}%
                </span>
              </div>
              {agent.last_action && (
                <div className="pt-2 border-t" style={{ borderColor: 'var(--border)' }}>
                  <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Last Action</div>
                  <div className="text-xs">{agent.last_action}</div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {blockchain && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="card">
            <h3 className="font-semibold mb-3">Ethereum</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-secondary)' }}>Connected</span>
                <span className={blockchain.ethereum?.connected ? 'metric-positive' : 'metric-negative'}>
                  {blockchain.ethereum?.connected ? 'Yes' : 'No'}
                </span>
              </div>
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-secondary)' }}>Block Number</span>
                <span>{blockchain.ethereum?.block_number?.toLocaleString() || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-secondary)' }}>Gas Price</span>
                <span>{blockchain.ethereum?.gas_price_gwei?.toFixed(1) || '-'} Gwei</span>
              </div>
            </div>
          </div>
          <div className="card">
            <h3 className="font-semibold mb-3">Solana</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-secondary)' }}>Connected</span>
                <span className={blockchain.solana?.connected ? 'metric-positive' : 'metric-negative'}>
                  {blockchain.solana?.connected ? 'Yes' : 'No'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {system && (
        <div className="card">
          <h3 className="font-semibold mb-4">System Information</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>LLM</div>
              <div className="font-medium">{system.llm}</div>
            </div>
            <div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Framework</div>
              <div className="font-medium">{system.framework}</div>
            </div>
            <div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Consensus</div>
              <div className="font-medium">{system.consensus}</div>
            </div>
            <div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Governance</div>
              <div className="font-medium">{system.governance}</div>
            </div>
            <div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Security</div>
              <div className="font-medium">{system.security}</div>
            </div>
            <div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Vector DB</div>
              <div className="font-medium">{system.vector_db}</div>
            </div>
          </div>

          {/* x402 Payment Protocol Status */}
          {system.x402_payment && (
            <div className="mt-4 pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
              <div className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
                x402 Payment Protocol
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div>
                  <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Enabled</div>
                  <span className={system.x402_payment.enabled ? 'metric-positive' : ''}>
                    {system.x402_payment.enabled ? 'Yes' : 'No'}
                  </span>
                </div>
                <div>
                  <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Network</div>
                  <span>{system.x402_payment.testnet ? 'Testnet' : 'Mainnet'}</span>
                </div>
                <div>
                  <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Chain ID</div>
                  <span>{system.x402_payment.chain_id}</span>
                </div>
                <div>
                  <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Backtest Exempt</div>
                  <span className="metric-positive">
                    ✓ {system.x402_payment.backtest_exempt_reason?.split('—')[0] || 'Yes'}
                  </span>
                </div>
              </div>
              {system.x402_payment.pricing_usd && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {Object.entries(system.x402_payment.pricing_usd).map(([resource, price]) => (
                    <span key={resource} className="text-xs px-2 py-1 rounded"
                      style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
                      {resource}: ${price}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="mt-4 pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
            <div className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Features</div>
            <div className="flex flex-wrap gap-2">
              {system.features?.map((f, i) => (
                <span key={i} className="text-xs px-2 py-1 rounded" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
                  {f}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}