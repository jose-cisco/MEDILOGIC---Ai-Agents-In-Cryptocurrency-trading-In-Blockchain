import { useAppMode } from '../contexts/AppModeContext'

const SIMULATION_BATTLE = {
  status: 'ACTIVE',
  token: 'SOL/USDC',
  round: 3,
  agents: {
    planner: { name: 'DeepSeek-V3', model: 'Planner', proposal: 'BUY', confidence: 0.88 },
    verifier: { name: 'Grok-4.20', model: 'Verifier', stance: 'CRITICAL', confidence: 0.92 },
  },
  logs: [
    { agent: 'Planner', msg: 'Momentum oscillators indicating oversold condition on 4H. Proposing BUY entry at $142.50.', timestamp: '11:10:02' },
    { agent: 'Verifier', msg: 'Counter-argument: 24h volatility is spiked. Order book depth on Binance shows heavy sell walls at $143. Check liquidity provider status.', timestamp: '11:10:05' },
    { agent: 'Planner', msg: 'RAG context confirms institutional positioning on JITO. Buy-side pressure remains dominant on-chain.', timestamp: '11:10:08' },
    { agent: 'Verifier', msg: 'PoT Consensus requirement: Adjust position size by -15% to account for slippage variance.', timestamp: '11:10:12' },
    { agent: 'Controller', msg: 'CONSENSUS REACHED: BUY approved with reduced size. Anchoring on-chain via ActivityLogger...', timestamp: '11:10:15' },
    { agent: 'Monitor', msg: 'POSITION ACTIVE: Initiating dynamic trailing stop at -1.5% distance. Volume monitoring active.', timestamp: '11:10:18' },
    { agent: 'Adjuster', msg: 'REACTION LOGIC SET: Early exit trigger primed if RSI(15m) > 82 or volume divergence > 20%.', timestamp: '11:10:22' },
  ],
}

const LIVE_TEST_BATTLE = {
  status: 'ACTIVE',
  token: 'ETH/USDC',
  round: 7,
  agents: {
    planner: { name: 'GLM-5.1', model: 'Planner', proposal: 'HOLD', confidence: 0.81 },
    verifier: { name: 'Grok-4.20', model: 'Verifier', stance: 'CAUTION', confidence: 0.89 },
  },
  logs: [
    { agent: 'Planner', msg: 'Live test scenario loaded from hardcoded mock state. Momentum has weakened after the morning breakout.', timestamp: '14:21:04' },
    { agent: 'Verifier', msg: 'Volatility remains elevated and liquidity is uneven across venues. Recommending defensive posture.', timestamp: '14:21:08' },
    { agent: 'Planner', msg: 'RAG-aligned historical pattern suggests patience until confirmation returns above intraday VWAP.', timestamp: '14:21:11' },
    { agent: 'Verifier', msg: 'PoT note: approve only as HOLD for live testing. No execution path should be inferred from this arena view.', timestamp: '14:21:14' },
    { agent: 'Controller', msg: 'CONSENSUS REACHED: HOLD maintained. Debate Arena remains intentionally mock-backed during live testing.', timestamp: '14:21:18' },
    { agent: 'Monitor', msg: 'MOCK OBSERVABILITY: Tracking price divergence and volume spikes without reading backend execution state.', timestamp: '14:21:22' },
    { agent: 'Adjuster', msg: 'MOCK REACTIVITY: Alert-only mode primed if spread widens above test thresholds.', timestamp: '14:21:27' },
  ],
}

export default function DebateArenaPage() {
  const { isSimulation } = useAppMode()
  const activeBattle = isSimulation ? SIMULATION_BATTLE : LIVE_TEST_BATTLE

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-black/20 p-4 rounded-xl border border-white/5">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            ⚔️ Debate Arena 
            <span className={`text-[10px] px-2 py-0.5 rounded-full animate-pulse uppercase tracking-widest ${isSimulation ? 'bg-emerald-500/20 text-emerald-500' : 'bg-red-500/20 text-red-500'}`}>
              {isSimulation ? 'Simulated Battle' : 'Live Battle'}
            </span>
          </h1>
          <p className="text-sm opacity-50">Multi-Agent Consensus Verification (PoT) {isSimulation && <span className="text-emerald-500 font-bold ml-1">(Simulation Mode)</span>}</p>
          {!isSimulation && (
            <p className="text-xs text-red-300/80 mt-1">
              Live testing uses a hardcoded mock arena state and does not subscribe to backend debate data.
            </p>
          )}
        </div>
        <div className="text-right">
          <div className="text-sm font-bold text-blue-400">{activeBattle.token}</div>
          <div className="text-[10px] opacity-40 uppercase">Round {activeBattle.round} • Block #842,912</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 relative">
        {/* Battle Visualizer (Middle Sword Icon) */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10 hidden lg:block">
          <div className="w-16 h-16 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-2xl shadow-[0_0_50px_rgba(255,255,255,0.1)]">
            🆚
          </div>
        </div>

        {/* Planner Column */}
        <div className="card border-blue-500/20 overflow-hidden">
          <div className="bg-blue-500/10 p-4 border-b border-blue-500/20 flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500 flex items-center justify-center text-xl shadow-lg shadow-blue-500/20">🧠</div>
              <div>
                <div className="font-bold">Planner Agent</div>
                <div className="text-[10px] uppercase opacity-50">{activeBattle.agents.planner.name}</div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs font-bold text-blue-400 uppercase">Proposing: {activeBattle.agents.planner.proposal}</div>
              <div className="text-[10px] opacity-40">Confidence: {(activeBattle.agents.planner.confidence * 100)}%</div>
            </div>
          </div>
          <div className="h-[400px] bg-black/10 overflow-hidden relative">
             <div className="absolute inset-0 flex items-center justify-center opacity-5">
                <span className="text-8xl">PLAN</span>
             </div>
             <div className="relative p-6 space-y-4">
                <div className="p-3 rounded-lg bg-white/5 border border-white/5 text-sm italic">
                  "Evaluating macro liquidity profile... RAG suggests bullish sentiment in developer docs."
                </div>
                <div className="flex gap-2 flex-wrap">
                   {['MACRO_OSC', 'RSI_OVERSOLD', 'EMA_CROSS'].map(tag => (
                     <span key={tag} className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">{tag}</span>
                   ))}
                </div>
             </div>
          </div>
        </div>

        {/* Verifier Column */}
        <div className="card border-purple-500/20 overflow-hidden">
          <div className="bg-purple-500/10 p-4 border-b border-purple-500/20 flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500 flex items-center justify-center text-xl shadow-lg shadow-purple-500/20">🛡️</div>
              <div>
                <div className="font-bold">Verifier Agent</div>
                <div className="text-[10px] uppercase opacity-50">{activeBattle.agents.verifier.name}</div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs font-bold text-purple-400 uppercase">Stance: {activeBattle.agents.verifier.stance}</div>
              <div className="text-[10px] opacity-40">Verification: {(activeBattle.agents.verifier.confidence * 100)}%</div>
            </div>
          </div>
          <div className="h-[400px] bg-black/10 overflow-hidden relative">
             <div className="absolute inset-0 flex items-center justify-center opacity-5">
                <span className="text-8xl text-purple-500">VET</span>
             </div>
             <div className="relative p-6 space-y-4">
                <div className="p-3 rounded-lg bg-white/5 border border-white/5 text-sm italic">
                  "Detected anomalous slippage on Raydium. Recommending JUP aggregators for execution."
                </div>
                <div className="flex gap-2 flex-wrap">
                   {['SLIPPAGE_WARN', 'DEX_AUDIT', 'LIQUIDITY_CHECK'].map(tag => (
                     <span key={tag} className="text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">{tag}</span>
                   ))}
                </div>
             </div>
          </div>
        </div>
      </div>

      {/* Consensus Log / Timeline */}
      <div className="card">
        <h2 className="font-bold text-sm uppercase opacity-50 mb-4 tracking-widest">Multi-Agent Debate Timeline</h2>
        <div className="space-y-4">
          {activeBattle.logs.map((log, i) => (
            <div key={i} className="flex gap-4 items-start group">
              <div className="text-[10px] font-mono opacity-30 mt-1">{log.timestamp}</div>
              <div className={`text-[10px] px-2 py-0.5 rounded font-bold w-20 text-center ${
                log.agent === 'Planner' ? 'bg-blue-500/20 text-blue-400' : 
                log.agent === 'Verifier' ? 'bg-purple-500/20 text-purple-400' : 
                log.agent === 'Controller' ? 'bg-green-500/20 text-green-400' :
                log.agent === 'Monitor' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'
              }`}>
                {log.agent}
              </div>
              <div className="text-sm opacity-80 group-hover:opacity-100 transition-opacity">
                {log.msg}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
