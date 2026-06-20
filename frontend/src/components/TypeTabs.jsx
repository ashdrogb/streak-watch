const TABS = [
  { value: 'all', label: 'All' },
  { value: 'win', label: 'Win' },
  { value: 'draw', label: 'Draw' },
  { value: 'loss', label: 'Loss' },
  { value: 'points_lost', label: 'Points lost' },
]

export default function TypeTabs({ active, onChange }) {
  return (
    <div className="type-tabs" role="tablist" aria-label="Filter by streak type">
      {TABS.map((tab) => (
        <button
          type="button"
          key={tab.value}
          role="tab"
          aria-selected={active === tab.value}
          className={`type-tab type-tab--${tab.value} ${active === tab.value ? 'type-tab-active' : ''}`}
          onClick={() => onChange(tab.value)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
