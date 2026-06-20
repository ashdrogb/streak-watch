export default function LeagueFilter({ leagues, selected, onToggle, onClear }) {
  return (
    <div className="league-filter" role="group" aria-label="Filter by league">
      <button
        type="button"
        className={`chip chip-reset ${selected.length === 0 ? 'chip-active' : ''}`}
        onClick={onClear}
      >
        All leagues
      </button>

      {leagues.map((lg) => {
        const active = selected.includes(lg.code)
        return (
          <button
            type="button"
            key={lg.code}
            className={`chip ${active ? 'chip-active' : ''}`}
            aria-pressed={active}
            onClick={() => onToggle(lg.code)}
          >
            <span className="chip-code">{lg.code}</span>
            {lg.name}
          </button>
        )
      })}
    </div>
  )
}
