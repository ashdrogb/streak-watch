import { useEffect, useMemo, useState } from 'react'
import { fetchLeagues, fetchStreaks } from '../api.js'
import { streaksToCSV, downloadCSV } from '../csv.js'
import LeagueFilter from './LeagueFilter.jsx'
import TypeTabs from './TypeTabs.jsx'
import StreakCard from './StreakCard.jsx'

export default function Dashboard() {
  const [leagues, setLeagues] = useState([])
  const [selectedLeagues, setSelectedLeagues] = useState([])
  const [activeType, setActiveType] = useState('all')
  const [minLength, setMinLength] = useState(1)

  const [streaks, setStreaks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchLeagues()
      .then(setLeagues)
      .catch(() => {
        /* the streaks call below will surface the same backend error */
      })
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetchStreaks({ leagues: selectedLeagues, type: activeType, minLength })
      .then((data) => {
        if (!cancelled) setStreaks(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [selectedLeagues, activeType, minLength])

  const leagueNameByCode = useMemo(() => {
    const map = {}
    leagues.forEach((lg) => {
      map[lg.code] = lg.name
    })
    return map
  }, [leagues])

  function toggleLeague(code) {
    setSelectedLeagues((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    )
  }

  function handleDownloadCSV() {
    if (streaks.length === 0) return

    const leaguePart = selectedLeagues.length ? selectedLeagues.join('-') : 'all-leagues'
    const typePart = activeType === 'all' ? 'all-types' : activeType
    const today = new Date().toISOString().slice(0, 10)

    downloadCSV(
      `streak-watch_${leaguePart}_${typePart}_min${minLength}_${today}.csv`,
      streaksToCSV(streaks)
    )
  }

  return (
    <section className="dashboard">
      <div className="controls">
        <LeagueFilter
          leagues={leagues}
          selected={selectedLeagues}
          onToggle={toggleLeague}
          onClear={() => setSelectedLeagues([])}
        />

        <div className="controls-row">
          <TypeTabs active={activeType} onChange={setActiveType} />

          <div className="controls-actions">
            <div className="min-length">
              <span className="min-length-label">Min streak</span>
              <button
                type="button"
                className="stepper-btn"
                onClick={() => setMinLength((n) => Math.max(1, n - 1))}
                aria-label="Decrease minimum streak length"
              >
                &minus;
              </button>
              <span className="min-length-value">{minLength}</span>
              <button
                type="button"
                className="stepper-btn"
                onClick={() => setMinLength((n) => Math.min(10, n + 1))}
                aria-label="Increase minimum streak length"
              >
                +
              </button>
            </div>

            <button
              type="button"
              className="csv-btn"
              onClick={handleDownloadCSV}
              disabled={streaks.length === 0}
              title={
                streaks.length === 0
                  ? 'No streaks to export with these filters'
                  : `Download ${streaks.length} row(s) as CSV`
              }
            >
              Download CSV
            </button>
          </div>
        </div>
      </div>

      {error && (
        <p className="state-message state-message--error">
          Couldn&rsquo;t load streaks: {error}
        </p>
      )}

      {!error && loading && (
        <p className="state-message">Scanning leagues&hellip;</p>
      )}

      {!error && !loading && streaks.length === 0 && (
        <p className="state-message">No streaks match these filters right now.</p>
      )}

      {!error && !loading && streaks.length > 0 && (
        <div className="grid">
          {streaks.map((s, i) => (
            <StreakCard
              key={`${s.league}-${s.team}-${i}`}
              streak={s}
              leagueName={leagueNameByCode[s.league] || s.league}
            />
          ))}
        </div>
      )}
    </section>
  )
}
