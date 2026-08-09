export default function MetricCard({ label, value, delta }) {
  const hasDelta = delta !== null && delta !== undefined
  const isPositive = hasDelta && delta >= 0

  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {hasDelta && (
        <div className={`metric-delta ${isPositive ? 'positive' : 'negative'}`}>
          {isPositive ? '▲' : '▼'} {Math.abs(delta).toFixed(4)}
        </div>
      )}
    </div>
  )
}
