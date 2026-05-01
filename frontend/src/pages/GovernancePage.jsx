import { useState, useEffect } from 'react'
import { API_BASE } from '../App'

export default function GovernancePage() {
  const [status, setStatus] = useState(null)
  const [logs, setLogs] = useState([])
  const [proposals, setProposals] = useState([])
  const [voters, setVoters] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('proposals')
  
  // Create Proposal state
  const [showCreate, setShowCreate] = useState(false)
  const [newProposal, setNewProposal] = useState({ title: '', description: '', proposer: '0xAgent_1' })
  
  // Voter info
  const [myVoterId, setMyVoterId] = useState('0xAgent_1')

  const fetchData = async () => {
    try {
      const [statusRes, logsRes, propRes, voterRes] = await Promise.all([
        fetch(`${API_BASE}/governance/status`),
        fetch(`${API_BASE}/governance/logs?limit=20`),
        fetch(`${API_BASE}/mabc/proposals`),
        fetch(`${API_BASE}/mabc/voters`),
      ])
      
      setStatus(await statusRes.json())
      const logsData = await logsRes.json()
      setLogs(logsData.logs || [])
      
      const propData = await propRes.json()
      // Ensure we handle both array and object responses
      setProposals(Array.isArray(propData) ? propData : (propData.proposals || []))
      
      const voterData = await voterRes.json()
      setVoters(voterData.voters || [])
    } catch (e) {
      console.error('Failed to fetch governance data', e)
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleVote = async (proposalId, supportValue) => {
    try {
      const res = await fetch(`${API_BASE}/mabc/proposals/${proposalId}/vote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          voter: myVoterId,
          proposal_id: proposalId,
          support: supportValue,
          reason: "Manual vote via Governance Dashboard"
        })
      })
      if (res.ok) {
        alert('Vote cast successfully!')
        fetchData()
      } else {
        const err = await res.json()
        alert(`Failed to vote: ${err.detail}`)
      }
    } catch (e) {
      alert('Vote error: ' + e.message)
    }
  }

  const handleCreateProposal = async () => {
    try {
      const res = await fetch(`${API_BASE}/mabc/proposals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newProposal)
      })
      if (res.ok) {
        setShowCreate(false)
        setNewProposal({ title: '', description: '', proposer: '0xAgent_1' })
        fetchData()
      } else {
        const err = await res.json()
        alert(`Failed: ${err.detail}`)
      }
    } catch (e) {
      alert('Error: ' + e.message)
    }
  }

  if (loading) return <div className="text-center py-16 text-accent-blue font-mono">📡 Connecting to mABC Governance Nodes...</div>

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold mb-1">Agent Governance (mABC DAO)</h1>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            Policy-as-Code • Proof-of-Thought (PoT) Consensus • Multi-Agent Blockchain Coordination
          </p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <span>➕</span> New Proposal
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Sidebar Status */}
        <div className="space-y-4">
          <div className="card space-y-4">
            <h2 className="font-semibold text-lg flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-accent-green"></span>
              DAO Status
            </h2>
            <div className="space-y-3 text-sm font-mono">
              <div className="flex justify-between items-center p-2 rounded" style={{ background: 'var(--bg-secondary)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Policy</span>
                <span className={status?.enabled ? 'text-accent-green font-bold' : 'text-accent-red font-bold'}>
                  {status?.enabled ? 'ENFORCED' : 'OFF'}
                </span>
              </div>
              <div className="flex justify-between items-center p-2 rounded" style={{ background: 'var(--bg-secondary)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Quorum</span>
                <span className="font-bold">{status?.multisig_threshold || 1}/N</span>
              </div>
              <div className="flex justify-between items-center p-2 rounded" style={{ background: 'var(--bg-secondary)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Voters</span>
                <span className="font-bold">{voters.length}</span>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold mb-3 text-sm">Identity</h3>
            <div className="space-y-2">
              <input 
                type="text" 
                value={myVoterId} 
                onChange={(e) => setMyVoterId(e.target.value)}
                className="w-full text-xs font-mono p-2 rounded" 
                placeholder="Voter Agent ID..."
                style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
              />
              <p className="text-[10px] opacity-50 italic text-center">Simulating wallet: {myVoterId}</p>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="md:col-span-3 space-y-6">
          <div className="flex gap-4 border-b border-border mb-4">
            <button 
              onClick={() => setActiveTab('proposals')}
              className={`pb-2 text-sm font-bold transition-all ${activeTab === 'proposals' ? 'text-accent-blue border-b-2 border-accent-blue' : 'opacity-40'}`}
            >
              📜 ACTIVE PROPOSALS
            </button>
            <button 
              onClick={() => setActiveTab('logs')}
              className={`pb-2 text-sm font-bold transition-all ${activeTab === 'logs' ? 'text-accent-blue border-b-2 border-accent-blue' : 'opacity-40'}`}
            >
              📋 COMPLIANCE LOGS
            </button>
          </div>

          {activeTab === 'proposals' && (
            <div className="space-y-4">
              {proposals.length === 0 ? (
                <div className="text-center py-20 card opacity-40 italic">
                  No active proposals in the mABC voting queue.
                </div>
              ) : (
                proposals.map((prop) => (
                  <div key={prop.id} className="card border-l-4 border-accent-blue transition-all hover:bg-opacity-80">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <div className="text-[10px] font-mono opacity-50 mb-1 uppercase">Proposal #{prop.id} • {prop.state}</div>
                        <h3 className="font-bold text-lg">{prop.title}</h3>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => handleVote(prop.id, 1)} className="btn-secondary py-1 text-xs hover:bg-accent-green hover:text-white transition-colors">👍 VOTES: {prop.for_votes || 0}</button>
                        <button onClick={() => handleVote(prop.id, 0)} className="btn-secondary py-1 text-xs hover:bg-accent-red hover:text-white transition-colors">👎 AGAINST: {prop.against_votes || 0}</button>
                      </div>
                    </div>
                    <p className="text-sm opacity-80 mb-4 bg-black bg-opacity-10 p-3 rounded">{prop.description}</p>
                    <div className="flex justify-between items-center text-xs opacity-50 font-mono">
                      <span>Proposer: {prop.proposer}</span>
                      <span>Target: {prop.target_contract || 'Global Policy'}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
              {logs.length === 0 ? (
                <div className="text-center py-12 opacity-50 italic">No governance events recorded yet.</div>
              ) : (
                logs.slice().reverse().map((log, i) => (
                  <div key={i} className="card border-l-4" style={{ borderColor: log.approved ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${log.approved ? 'bg-accent-green bg-opacity-10 text-accent-green' : 'bg-accent-red bg-opacity-10 text-accent-red'}`}>
                          {log.approved ? 'COMPLIANT' : 'VIOLATION'}
                        </span>
                        <span className="text-[10px] font-mono opacity-30">{log.event_hash.slice(0, 16)}...</span>
                      </div>
                      <span className="text-[10px] opacity-50 font-mono">{new Date(log.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mb-2">
                      <div className="text-xs">
                        <span className="opacity-40">Action:</span> <span className="font-bold">{log.action} {log.token_pair}</span>
                      </div>
                      <div className="text-xs">
                        <span className="opacity-40">Chain:</span> <span className="font-bold">{log.chain}</span>
                      </div>
                    </div>
                    <div className="text-xs p-2 rounded italic opacity-70 italic bg-black bg-opacity-5">
                      "{log.reasoning}"
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Create Proposal Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-80 backdrop-blur-sm">
          <div className="card w-full max-w-lg space-y-4 animate-in fade-in zoom-in duration-200">
            <div className="flex justify-between items-center border-b border-border pb-3">
              <h2 className="text-xl font-bold">New Governance Proposal</h2>
              <button onClick={() => setShowCreate(false)} className="text-2xl hover:text-accent-red transition-colors">✕</button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-bold uppercase mb-1 block opacity-50">Proposal Title</label>
                <input 
                  type="text" 
                  value={newProposal.title}
                  onChange={(e) => setNewProposal({...newProposal, title: e.target.value})}
                  className="w-full font-bold" 
                  placeholder="e.g. Increase Max Position size to $5000"
                />
              </div>
              <div>
                <label className="text-xs font-bold uppercase mb-1 block opacity-50">Detailed Rationale</label>
                <textarea 
                  rows={4}
                  value={newProposal.description}
                  onChange={(e) => setNewProposal({...newProposal, description: e.target.value})}
                  className="w-full text-sm" 
                  placeholder="Why should the agents vote for this? Explain the market context..."
                />
              </div>
              <button onClick={handleCreateProposal} className="btn-primary w-full py-3 shadow-lg shadow-blue-500/20">
                🚀 BROADCAST PROPOSAL TO NETWORK
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
