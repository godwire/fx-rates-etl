import { useEffect, useMemo, useState } from 'react'
import { fetchMeta, fetchRates, refreshRates } from './api'
import MetricCard from './components/MetricCard'
import RatesChart from './components/RatesChart'

/** Turn [{date, base, currency, rate}, ...] into [{date, USD: 1.09, GBP: 0.87}, ...] for recharts. */
function pivotRates(rows) {
  const byDate = {}
  for (const row of rows) {
    if (!byDate[row.date]) byDate[row.date] = { date: row.date }
    byDate[row.date][row.currency] = row.rate
  }
  return Object.values(byDate).sort((a, b) => a.date.localeCompare(b.date))
}

export default function App() {
  const [meta, setMeta] = useState(null)
  const [base, setBase] = useState('')
  const [currencies, setCurrencies] = useState([])
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)

  // Initial load: fetch available bases/currencies, pick sensible defaults.
  useEffect(() => {
    fetchMeta()
      .then((m) => {
        if (!m || m.bases.length === 0) {
          setError('No data yet. Try clicking "Fetch latest rates" once the API is running.')
          return
        }
        setMeta(m)
        const defaultBase = m.bases[0]
        setBase(defaultBase)
        setCurrencies(m.currencies.filter((c) => c !== defaultBase).slice(0, 3))
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  // Re-fetch rates whenever the base or the selected currencies change.
  useEffect(() => {
    if (!base || currencies.length === 0) {
      setRows([])
      return
    }
    fetchRates(base, currencies)
      .then(setRows)
      .catch((e) => setError(e.message))
  }, [base, currencies])

  const chartData = useMemo(() => pivotRates(rows), [rows])

  const latestByCurrency = useMemo(() => {
    const dates = [...new Set(rows.map((r) => r.date))].sort()
    const latestDate = dates[dates.length - 1]
    const prevDate = dates[dates.length - 2]

    const result = {}
    for (const currency of currencies) {
      const latest = rows.find((r) => r.date === latestDate && r.currency === currency)
      const prev = rows.find((r) => r.date === prevDate && r.currency === currency)
      result[currency] = {
        value: latest ? latest.rate : null,
        delta: latest && prev ? latest.rate - prev.rate : null,
      }
    }
    return result
  }, [rows, currencies])

  async function handleRefresh() {
    setRefreshing(true)
    setError(null)
    try {
      await refreshRates()
      const [updatedMeta, updatedRows] = await Promise.all([
        fetchMeta(),
        fetchRates(base, currencies),
      ])
      setMeta(updatedMeta)
      setRows(updatedRows)
    } catch (e) {
      setError(e.message)
    } finally {
      setRefreshing(false)
    }
  }

  function toggleCurrency(currency) {
    setCurrencies((prev) =>
      prev.includes(currency) ? prev.filter((c) => c !== currency) : [...prev, currency],
    )
  }

  if (loading) {
    return <div className="center-message">Loading…</div>
  }

  if (error && !meta) {
    return (
      <div className="app">
        <div className="center-message error">{error}</div>
        <div className="center-message">
          <button className="refresh-btn" onClick={handleRefresh} disabled={refreshing}>
            {refreshing ? 'Fetching…' : '🔄 Fetch latest rates'}
          </button>
        </div>
      </div>
    )
  }

  if (!meta) return null

  return (
    <div className="app">
      <header>
        <h1>💱 FX Rates Dashboard</h1>
        <p className="subtitle">
          Live data from a small ETL pipeline —{' '}
          <a href="https://github.com/godwire/fx-rates-etl" target="_blank" rel="noreferrer">
            fx-rates-etl on GitHub
          </a>
        </p>
      </header>

      {error && <div className="banner error">{error}</div>}

      <div className="controls">
        <label>
          Base currency
          <select value={base} onChange={(e) => setBase(e.target.value)}>
            {meta.bases.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </label>

        <div className="currency-picker">
          <span>Currencies</span>
          <div className="chips">
            {meta.currencies
              .filter((c) => c !== base)
              .map((c) => (
                <button
                  key={c}
                  type="button"
                  className={`chip ${currencies.includes(c) ? 'active' : ''}`}
                  onClick={() => toggleCurrency(c)}
                >
                  {c}
                </button>
              ))}
          </div>
        </div>

        <button className="refresh-btn" onClick={handleRefresh} disabled={refreshing}>
          {refreshing ? 'Refreshing…' : '🔄 Fetch latest rates'}
        </button>
      </div>

      {currencies.length === 0 ? (
        <div className="center-message">Pick at least one currency to see the chart.</div>
      ) : (
        <>
          <div className="metrics">
            {currencies.map((currency) => (
              <MetricCard
                key={currency}
                label={`${base} → ${currency}`}
                value={
                  latestByCurrency[currency]?.value != null
                    ? latestByCurrency[currency].value.toFixed(4)
                    : '—'
                }
                delta={latestByCurrency[currency]?.delta ?? null}
              />
            ))}
          </div>

          <div className="chart-container">
            {chartData.length > 0 ? (
              <RatesChart data={chartData} currencies={currencies} />
            ) : (
              <div className="center-message">No data for this selection yet.</div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
