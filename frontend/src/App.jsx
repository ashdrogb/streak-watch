import Dashboard from './components/Dashboard.jsx'

export default function App() {
  return (
    <div className="app">
      <div className="pitch-lines" aria-hidden="true" />

      <header className="hero">
        <div className="hero-eyebrow">
          <span className="hero-dot" />
          Live form across ten divisions
        </div>
        <h1 className="hero-title">STREAK&nbsp;WATCH</h1>
        <p className="hero-sub">
          Every team currently winning, drawing, losing, or quietly bleeding
          points across the Premier League down to Ligue&nbsp;2 &mdash; updated
          from completed matches, re-scanned every few minutes.
        </p>
      </header>

      <main>
        <Dashboard />
      </main>

      <footer className="site-foot">
        Data via football-data.org, OpenLigaDB and API-Football. Not affiliated
        with any league, club, or data provider.
      </footer>
    </div>
  )
}
