from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class GuildLeaderboard:
    guild_id: int
    name: str
    background: str
    icon: str

@dataclass(slots=True, frozen=True)
class GuildSeasonLeaderboard:
    guild: GuildLeaderboard
    position: int
    experience: int

@dataclass(slots=True, frozen=True)
class Season:
    id: int
    name: str
    starts_at: str
    ends_at: str
