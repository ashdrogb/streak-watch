"""
Plain dataclasses shared across the backend. Nothing here talks to a
network or a provider -- it's pure data shape.
"""
from dataclasses import dataclass


@dataclass
class Match:
    """One finished match, already normalised from whichever provider
    fetched it (football-data.org / OpenLigaDB / API-Football all end up
    looking like this)."""

    league: str          # our internal league code, e.g. "PD"
    date: str            # ISO-8601 date, "2026-05-10"
    home_team: str
    home_team_id: int
    home_crest: str
    home_score: int
    away_team: str
    away_team_id: int
    away_crest: str
    away_score: int


@dataclass
class TeamStreak:
    """A team's currently active streak, plus the goal and points context
    that goes with it -- this is what /api/streaks returns."""

    league: str
    team: str
    team_id: int
    crest_url: str

    streak_type: str          # "win" | "draw" | "loss"
    streak_length: int

    # Goals scored/conceded across the matches that make up streak_length.
    goals_for: int
    goals_against: int
    goal_difference: int

    # Independent of streak_type: how many of the most recent matches in a
    # row failed to produce a win, and how many points that run cost
    # relative to winning every one of them (loss = -3, draw = -2). This is
    # 0 whenever streak_type == "win", and can be longer than streak_length
    # when recent form alternates between draws and losses.
    points_lost_streak: int
    points_dropped: int

    last_opponent: str
    last_opponent_crest: str
    match_date: str


@dataclass
class LossStreakAlert:
    """Used by the (optional, not wired into the API) alerts/ package for
    threshold-based notifications, e.g. 'team X has now lost 5 in a row'."""

    league: str
    team: str
    loss_streak: int
    last_result: str
    last_opponent: str
    match_date: str
    alert_triggered: bool


@dataclass
class SentAlert:
    """Records that an alert was already sent, so a notifier can avoid
    sending the same one twice."""

    league: str
    team: str
    streak_length: int
    sent_at: str
