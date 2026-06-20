const TYPE_LABEL = {
  win: 'Win streak',
  draw: 'Draw streak',
  loss: 'Loss streak',
}

const MAX_TICKS = 10

function PureStreakStrip({ type, length }) {
  const shown = Math.min(length, MAX_TICKS)
  const overflow = length - shown

  return (
    <div className={`strip strip--${type}`} aria-hidden="true">
      {Array.from({ length: shown }).map((_, i) => (
        <span key={i} className="tick" />
      ))}
      {overflow > 0 && <span className="tick-overflow">+{overflow}</span>}
    </div>
  )
}

// Points-lost streaks can mix losses and draws (e.g. L, D, L, D). The exact
// game-by-game order isn't in the API response, but the loss/draw *counts*
// can be recovered exactly from streak_length and points_dropped (loss
// costs 3 points, draw costs 2): losses = points_dropped - 2*length,
// draws = 3*length - points_dropped. A proportional two-colour bar shows
// that real mix honestly, without implying an order we don't have.
function PointsLostBar({ length, pointsDropped }) {
  const losses = Math.max(0, Math.min(length, pointsDropped - 2 * length))
  const draws = Math.max(0, length - losses)

  return (
    <div className="bar" aria-hidden="true">
      {losses > 0 && (
        <span className="bar-segment bar-segment--loss" style={{ flexGrow: losses }} />
      )}
      {draws > 0 && (
        <span className="bar-segment bar-segment--draw" style={{ flexGrow: draws }} />
      )}
    </div>
  )
}

export default function StreakCard({ streak, leagueName }) {
  const {
    team,
    crest_url,
    streak_type,
    streak_length,
    goals_for,
    goals_against,
    goal_difference,
    points_lost_streak,
    points_dropped,
    last_opponent,
    last_opponent_crest,
    match_date,
    league,
    is_stale,
  } = streak

  const isPointsLost = streak_type !== 'win' && points_lost_streak > 0 &&
    points_lost_streak !== streak_length

  const gdLabel = goal_difference > 0 ? `+${goal_difference}` : `${goal_difference}`

  return (
    <article className={`card card--${streak_type}`}>
      <header className="card-head">
        <div className="card-team">
          {crest_url ? (
            <img className="crest" src={crest_url} alt="" loading="lazy" />
          ) : (
            <span className="crest crest--placeholder" aria-hidden="true" />
          )}
          <h3 className="team-name">{team}</h3>
        </div>
        <span className="league-badge" title={leagueName}>{league}</span>
      </header>

      <div className="card-signature">
        <PureStreakStrip type={streak_type} length={streak_length} />
        <div className="signature-readout">
          <span className="streak-count">{streak_length}</span>
          <span className={`streak-label streak-label--${streak_type}`}>
            {TYPE_LABEL[streak_type] || streak_type}
          </span>
        </div>
      </div>

      {isPointsLost && (
        <div className="card-signature card-signature--secondary">
          <PointsLostBar length={points_lost_streak} pointsDropped={points_dropped} />
          <div className="signature-readout">
            <span className="streak-count streak-count--small">{points_lost_streak}</span>
            <span className="streak-label streak-label--points_lost">
              Points lost &middot; {points_dropped} pts dropped
            </span>
          </div>
        </div>
      )}

      <div className="card-stats">
        <span>GF {goals_for}</span>
        <span className="dot">&middot;</span>
        <span>GA {goals_against}</span>
        <span className="dot">&middot;</span>
        <span>GD {gdLabel}</span>
      </div>

      <footer className="card-foot">
        {last_opponent_crest ? (
          <img className="crest crest--small" src={last_opponent_crest} alt="" loading="lazy" />
        ) : (
          <span className="crest crest--small crest--placeholder" aria-hidden="true" />
        )}
        <span>vs {last_opponent}</span>
        <span className="card-date">{match_date}</span>
        {is_stale && (
          <span className="stale-badge" title="This league's data hasn't updated recently -- the source for it may be lagging">
            may be outdated
          </span>
        )}
      </footer>
    </article>
  )
}
