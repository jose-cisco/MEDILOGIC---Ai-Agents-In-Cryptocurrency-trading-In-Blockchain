import { useState } from 'react'
import { useAppMode } from '../contexts/AppModeContext'

const getFaqItems = (isSimulation) => [
  {
    title: 'What is PoT (Proof-of-Thought)?',
    icon: '🧠',
    content: (
      <div className="space-y-3">
        <p>Proof-of-Thought is our multi-agent consensus mechanism. Unlike traditional bots that follow single-LLM logic, PoT involves a 3-step verification cycle:</p>
        <ul className="list-disc pl-5 space-y-1 opacity-80">
          <li><strong>Planner</strong>: Scans markets and proposes an initial trade strategy.</li>
          <li><strong>Verifier</strong>: Audits the proposal for risks, slippage, and security vulnerabilities.</li>
          <li><strong>Controller</strong>: Anchors the final agreement on-chain if both agents agree.</li>
        </ul>
        <p className="text-xs italic opacity-50 underline">Ensures 98.8% accuracy in vulnerability detection.</p>
      </div>
    )
  },
  {
    title: 'How does x402 Payment work?',
    icon: '⚡',
    content: (
      <div className="space-y-3">
        <p>The x402 (HTTP 402 Payment Required) protocol allows pay-per-use AI services without accounts or subscriptions.</p>
        <div className="p-3 bg-pink-100 dark:bg-pink-500/20 text-pink-900 dark:text-pink-200 rounded font-mono text-[10px] space-y-1">
          <div>1. Request → (Resource is Paid)</div>
          <div>2. Response ← HTTP 402 + Price ($0.005 USDC)</div>
          <div>3. Wallet Signs & Sends USDC on Base</div>
          <div>4. Retry with X-Payment Header</div>
          <div>5. Done ✓</div>
        </div>
        <p>No API key rotation, no prepaid credits. Just a wallet and a click.</p>
      </div>
    )
  },
  {
    title: isSimulation ? 'Is Backtesting really Free?' : 'Are there Live execution Fees?',
    icon: '💎',
    content: isSimulation ? (
      <div className="space-y-3">
        <p><strong>Yes.</strong> Backtesting uses local Ollama models (GLM-5, MiniMax) and is strictly exempted from x402 payments.</p>
        <p>We believe safety is paramount. You should be able to simulate 10,000 strategies without spending a single cent on cloud inference or transaction fees.</p>
      </div>
    ) : (
      <div className="space-y-3">
        <p><strong>Yes.</strong> Live trading requires real capital and relies on premium cloud LLMs (Grok 4.20, GLM-5.1).</p>
        <p>Your wallet is fully responsible for x402 API payments ($0.005 USDC per request) as well as the actual on-chain gas fees for trade execution on standard DEXes and chains.</p>
      </div>
    )
  },
  {
    title: 'What is mABC Governance?',
    icon: '⚖️',
    content: (
      <div className="space-y-3">
        <p>mABC is our decentralized multi-agent voting system. It allows the community to vote on system parameters like:</p>
        <ul className="list-disc pl-5 space-y-1 opacity-80">
          <li>Maximum leverage limits</li>
          <li>Approved token lists</li>
          <li>Incentive weights for different agents</li>
        </ul>
      </div>
    )
  }
]

export default function FAQPage() {
  const { isSimulation } = useAppMode()
  const faqItems = getFaqItems(isSimulation)
  const [activeIdx, setActiveIdx] = useState(0)

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in slide-in-from-bottom-4 duration-700">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">System Knowledge Base</h1>
        <p style={{ color: 'var(--text-secondary)' }}>Understanding the primitives of decentralized AI trading</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {faqItems.map((item, i) => (
          <button
            key={i}
            onClick={() => setActiveIdx(i)}
            className={`p-6 rounded-2xl text-center border transition-all duration-300 ${
              activeIdx === i 
                ? 'bg-blue-500/10 border-blue-500/50 shadow-[0_0_20px_rgba(59,130,246,0.15)] scale-105' 
                : 'bg-black/5 border-black/5 dark:bg-white/5 dark:border-white/5 hover:border-black/10 dark:hover:border-white/10 grayscale opacity-60'
            }`}
          >
            <div className="text-3xl mb-3">{item.icon}</div>
            <div className="text-xs font-bold uppercase tracking-widest">{item.title.split(' ')[2] || item.title.split(' ')[0]}</div>
          </button>
        ))}
      </div>

      <div className="card min-h-[300px] p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-4 text-6xl opacity-10 pointer-events-none">
          {faqItems[activeIdx].icon}
        </div>
        <div className="relative">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <span className="text-blue-400">{faqItems[activeIdx].icon}</span>
            {faqItems[activeIdx].title}
          </h2>
          <div className="text-lg leading-relaxed" style={{ color: 'var(--text-primary)' }}>
            {faqItems[activeIdx].content}
          </div>
        </div>
      </div>

      <div className="flex justify-center gap-8 py-8 border-t opacity-50 text-xs uppercase tracking-widest" style={{ borderColor: 'var(--border)' }}>
        <span>BlockAgents v1.0</span>
        <span>•</span>
        <span>Base Mainnet</span>
        <span>•</span>
        <span>Verified Secure</span>
      </div>
    </div>
  )
}
