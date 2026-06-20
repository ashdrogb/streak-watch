// Turns the currently-filtered streaks array into a CSV string and
// triggers a browser download -- entirely client-side, since the data
// Dashboard.jsx already has in state *is* the filtered view (the filters
// are applied server-side in /api/streaks, this just exports what's
// already on screen).

const COLUMNS = [
  ['league_name', 'League'],
  ['league', 'League Code'],
  ['team', 'Team'],
  ['streak_type', 'Streak Type'],
  ['streak_length', 'Streak Length'],
  ['goals_for', 'GF'],
  ['goals_against', 'GA'],
  ['goal_difference', 'GD'],
  ['points_lost_streak', 'Points Lost Streak'],
  ['points_dropped', 'Points Dropped'],
  ['last_opponent', 'Last Opponent'],
  ['match_date', 'Match Date'],
  ['is_stale', 'Data May Be Outdated'],
]

function csvEscape(value) {
  const str = value === null || value === undefined ? '' : String(value)
  if (/[",\n]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`
  }
  return str
}

export function streaksToCSV(streaks) {
  const header = COLUMNS.map(([, label]) => csvEscape(label)).join(',')
  const rows = streaks.map((s) => COLUMNS.map(([key]) => csvEscape(s[key])).join(','))
  return [header, ...rows].join('\r\n')
}

export function downloadCSV(filename, csvText) {
  // A BOM helps Excel detect UTF-8 correctly (otherwise accented team
  // names like "Real Zaragoza" or "Köln" can render as mojibake).
  const blob = new Blob(['\ufeff' + csvText], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  URL.revokeObjectURL(url)
}
