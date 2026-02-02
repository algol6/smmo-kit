from dataclasses import dataclass

@dataclass
class GuildLeaderboard:
    guild_id: int
    name: str
    background: str
    icon: str

@dataclass
class GuildSeasonLeaderboard:
    guild: GuildLeaderboard
    position: int
    experience: int

@dataclass
class Season:
    id: int
    name: str
    starts_at: str
    ends_at: str