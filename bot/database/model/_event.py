from dataclasses import dataclass

@dataclass
class Event:
    id: int
    start_year: int
    start_month: int
    start_day: int
    start_time: int
    guild_id: int
    end_year: int
    end_month: int
    end_day: int
    end_time: int
    name: str
    description: str
    event_type: str
    guildies_only: bool
    message_id: int
    channel_id: int
    team_size: int

@dataclass
class EventStats:
    event_id: int
    smmo_id: int
    year: int
    month: int
    day: int
    time: int
    stats: int

@dataclass
class EventTeam:
    team: int
    smmo_id: int
    event_id: int
    guild_id: int


@dataclass
class EventLeaderboard:
    channel_id: int
    message_id: int
    event_id: int

@dataclass
class EventPartecipants:
    smmo_id: int
    name: str
    discord_id: int
    event_id: int
    team: str