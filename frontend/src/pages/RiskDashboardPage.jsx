import { useState, useEffect } from 'react'
import { API_BASE } from '../App'
import { useTheme } from '../contexts/ThemeContext'

export default function RiskDashboardPage() {
  const { isDark } = useTheme()
  const [metrics, setMetrics] = useState(null)
  const [calibration, setCalibration] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [periodDays, setPeriodDays] = useState(30)

  useEffect(() => {
    fetchMetrics()
    fetchCalibration()
  }, [periodDays])

  const fetchMetrics = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/trading/risk/metrics?period_days=${periodDays}`)
      if (!res.ok) throw new Error('Failed to fetch metrics')
      const data = await res.json()
      setMetrics(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchCalibration = async () => {
    try {
      const res = await fetch(`${API_BASE}/trading/risk/calibrate`)
      if (!res.ok) throw new Error('Failed to fetch calibration')
      const data = await res.json()
      setCalibration(data)
    } catch (err) {
      console.error('Calibration fetch error:', err)
    }
  }

  const levelColors = {
    low: { bg: 'rgba(16,185,129,0.15)', text: 'var(--accent-green)', border: 'var(--accent-green)' },
    moderate: { bg: 'rgba(59,130,246,0.15)', text: 'var(--accent-blue)', border: 'var(--accent-blue)' },
    high: { bg: 'rgba(234,179,8,0.15)', text: 'var(--accent-yellow)', border: 'var(--accent-yellow)' },
    critical: { bg: 'rgba(239,68,68,0.15)', text: 'var(--accent-red)', border: 'var(--accent-red)' },
  }

  const MetricCard = ({ title, value, unit, subtitle, color }) => (
    <div
      style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: '16px 20px',
      }}
    >
      <div style={{ color: 'var(--text-secondary)', fontSize: 12, marginBottom: 4 }}>{title}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: color || 'var(--text-primary)' }}>
        {value !== null && value !== undefined ? (typeof value === 'number' ? value.toFixed(2) : value) : 'N/A'}
        {unit && <span style={{ fontSize: 14, marginLeft: 4, opacity: 0.7 }}>{unit}</span>}
      </div>
      {subtitle && <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>{subtitle}</div>}
    </div>
  )

  const ScoreBar = ({ label, score, color }) => (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{label}</span>
        <span style={{ fontWeight: 600, fontSize: 13 }}>{(score || 0).toFixed(1)}</span>
      </div>
      <div style={{ height: 8, background: 'var(--bg-primary)', borderRadius: 4, overflow: 'hidden' }}>
        <div
          style={{
            width: `${Math.min(score || 0, 100)}%`,
            height: '100%',
            background: color,
            transition: 'width 0.5s ease',
          }}
        />
      </div>
    </div>
  )

  const WeightBar = ({ label, current, suggested, reasoning }) => (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontWeight: 500, fontSize: 13, textTransform: 'capitalize' }}>{label}</span>
        <span style={{ fontSize: 12 }}>
          {current.toFixed(0)}% → {suggested.toFixed(0)}%
        </span>
      </div>
      <div style={{ display: 'flex', height: 10, gap: 2 }}>
        <div style={{ flex: current, background: 'var(--accent-blue)', borderRadius: 4 }} />
        {suggested !== current && (
          <div style={{ flex: suggested - current, background: 'var(--accent-yellow)', borderRadius: 4 }} />
        )}
      </div>
      {reasoning && <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>{reasoning}</div>}
    </div>
  )

  if (loading && !metrics) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <div style={{ fontSize: 18, color: 'var(--text-secondary)' }}>Loading risk metrics...</div>
      </div>
    )
  }

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>
          ⚠️ Risk Dashboard
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Historical risk performance, metrics, and calibration suggestions
        </p>
      </div>

      {/* Period Selector */}
      <div style={{ marginBottom: 24, display: 'flex', gap: 8 }}>
        {[7, 30, 90].map((days) => (
          <button
            key={days}
            onClick={() => setPeriodDays(days)}
            style={{
              padding: '8px 16px',
              borderRadius: 8,
              border: periodDays === days ? '1px solid var(--accent-blue)' : '1px solid var(--border)',
              background: periodDays === days ? 'var(--accent-blue)' : 'var(--bg-secondary)',
              color: periodDays === days ? '#fff' : 'var(--text-primary)',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            {days} days
          </button>
        ))}
      </div>

      {error && (
        <div style={{ 
          background: 'rgba(239,68,68,0.1)', 
          border: '1px solid var(--accent-red)', 
          borderRadius: 8, 
          padding: 16, 
          marginBottom: 24 
        }}>
          <div style={{ color: 'var(--accent-red)', fontWeight: 600 }}>Error loading metrics</div>
          <div style={{ fontSize: 12, marginTop: 4 }}>{error}</div>
        </div>
      )}

      {/* Metrics Grid */}
      {metrics && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
            <MetricCard
              title="Total Trades"
              value={metrics.total_trades}
              subtitle={`${metrics.blocked_trades} blocked`}
            />
            <MetricCard
              title="Win Rate"
              value={metrics.win_rate * 100}
              unit="%"
              subtitle={`${metrics.winning_trades}W / ${metrics.losing_trades}L`}
              color={metrics.win_rate >= 0.5 ? 'var(--accent-green)' : 'var(--accent-red)'}
            />
            <MetricCard
              title="Avg Risk Score"
              value={metrics.avg_risk_score}
              subtitle="0-100 scale"
              color={metrics.avg_risk_score <= 25 ? 'var(--accent-green)' : metrics.avg_risk_score <= 50 ? 'var(--accent-blue)' : 'var(--accent-yellow)'}
            />
            <MetricCard
              title="Sharpe Ratio"
              value={metrics.sharpe_ratio}
              subtitle={metrics.sharpe_ratio ? (metrics.sharpe_ratio > 1 ? 'Good' : 'Needs improvement') : 'Insufficient data'}
              color={metrics.sharpe_ratio > 1 ? 'var(--accent-green)' : metrics.sharpe_ratio > 0 ? 'var(--accent-yellow)' : 'var(--accent-red)'}
            />
            <MetricCard
              title="Max Drawdown"
              value={metrics.max_drawdown * 100}
              unit="%"
              subtitle="Estimated peak-to-trough"
              color={metrics.max_drawdown < 0.1 ? 'var(--accent-green)' : metrics.max_drawdown < 0.25 ? 'var(--accent-yellow)' : 'var(--accent-red)'}
            />
            <MetricCard
              title="Avg Position"
              value={metrics.avg_position_multiplier * 100}
              unit="%"
              subtitle="Of requested size"
            />
          </div>

          {/* Win Rate by Risk Level */}
          <div style={{ 
            background: 'var(--bg-secondary)', 
            border: '1px solid var(--border)', 
            borderRadius: 12, 
            padding: 20, 
            marginBottom: 24 
          }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Win Rate by Risk Level</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
              {Object.entries(metrics.win_rate_by_level || {}).map(([level, rate]) => {
                const colors = levelColors[level] || levelColors.moderate
                return (
                  <div key={level} style={{ textAlign: 'center' }}>
                    <div
                      style={{
                        background: colors.bg,
                        border: `1px solid ${colors.border}`,
                        borderRadius: 8,
                        padding: '12px 8px',
                        marginBottom: 8,
                      }}
                    >
                      <div style={{ fontSize: 20, fontWeight: 700, color: colors.text }}>
                        {(rate * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div style={{ fontSize: 12, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                      {level}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </>
      )}

      {/* Calibration Suggestions */}
      {calibration && (
        <div style={{ 
          background: 'var(--bg-secondary)', 
          border: '1px solid var(--border)', 
          borderRadius: 12, 
          padding: 20,
          marginBottom: 24 
        }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Risk Calibration</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 12, marginBottom: 16 }}>
            Weight adjustments based on historical performance
          </p>

          {/* Average Component Scores */}
          {calibration.average_component_scores && (
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 12 }}>Average Component Scores</div>
              <ScoreBar label="Volatility" score={calibration.average_component_scores.volatility} color="var(--accent-blue)" />
              <ScoreBar label="Drawdown" score={calibration.average_component_scores.drawdown} color="var(--accent-purple)" />
              <ScoreBar label="Liquidity" score={calibration.average_component_scores.liquidity} color="var(--accent-yellow)" />
              <ScoreBar label="On-Chain" score={calibration.average_component_scores.onchain} color="var(--accent-red)" />
            </div>
          )}

          {/* Weight Suggestions */}
          <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 12 }}>Weight Adjustments</div>
          {calibration.current_weights && Object.entries(calibration.current_weights).map(([key, current]) => {
            const suggested = calibration.suggested_weights?.[key] || current
            const reasoning = calibration.reasoning?.find(r => r.toLowerCase().includes(key))
            return (
              <WeightBar
                key={key}
                label={key}
                current={current * 100}
                suggested={suggested * 100}
                reasoning={reasoning}
              />
            )
          })}

          {calibration.reasoning && calibration.reasoning.length > 0 && (
            <div style={{ 
              marginTop: 16, 
              padding: 12, 
              background: 'var(--bg-primary)', 
              borderRadius: 8,
              fontSize: 12 
            }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>Recommendations</div>
              {calibration.reasoning.map((r, i) => (
                <div key={i} style={{ marginBottom: 4, color: 'var(--text-secondary)' }}>
                  • {r}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Info Panel */}
      <div style={{ 
        background: 'var(--bg-secondary)', 
        border: '1px solid var(--border)', 
        borderRadius: 12, 
        padding: 20 
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>About Risk Assessment</h2>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          <p style={{ marginBottom: 12 }}>
            The risk engine evaluates trades on four factors: <strong>Volatility</strong> (30%), 
            <strong>Drawdown</strong> (25%), <strong>Liquidity</strong> (25%), and <strong>On-Chain</strong> (20%).
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8, marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ 
                width: 12, height: 12, borderRadius: 2, 
                background: 'var(--accent-green)' 
              }} />
              <span><strong>LOW (0-25):</strong> Execute normally</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ 
                width: 12, height: 12, borderRadius: 2, 
                background: 'var(--accent-blue)' 
              }} />
              <span><strong>MODERATE (26-50):</strong> Execute normally</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ 
                width: 12, height: 12, borderRadius: 2, 
                background: 'var(--accent-yellow)' 
              }} />
              <span><strong>HIGH (51-75):</strong> Position reduced 50%</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ 
                width: 12, height: 12, borderRadius: 2, 
                background: 'var(--accent-red)' 
              }} />
              <span><strong>CRITICAL (76-100):</strong> Trade blocked</span>
            </div>
          </div>
          <p>
            Historical risk assessments are stored in SQLite for calibration and analysis.
            Use these metrics to tune weights and improve detection accuracy.
          </p>
        </div>
      </div>
    </div>
  )
}