from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class JoinConf:
    guild_id: int
    msg: str
    groles: str
    vroles: str
    channel: int

@dataclass(slots=True, frozen=True)
class GuildStats:
    year: int
    month: int
    day: int
    time: int
    guild_id: int
    position: int
    experience: int
    season: int

@dataclass(slots=True, frozen=True)
class Requirements:
    guild_id: int
    days: int
    levels: int
    npc: int
    pvp: int
    steps: int

@dataclass(slots=True, frozen=True)
class Staff:
    guild_id: int
    role_id: int

@dataclass(slots=True, frozen=True)
class Server:
    guild_id: int
    server_id: int

@dataclass(slots=True, frozen=True)
class Rewards:
    guild_id: int
    gold: int
    x_days: int
    year: int
    month: int
    day: int

@dataclass(slots=True, frozen=True)
class SafeUser:
    smmo_id: int
    guild_id: int

@dataclass(slots=True, frozen=True)
class GainsLeaderboard:
    channel_id: int
    message_id: int
    server_id : int
    timeframe: str
    timestamp: int

@dataclass(slots=True, frozen=True)
class Raid:
    channel_id: int
    time: int
    duration: int
    role_id: int

@dataclass(slots=True, frozen=True)
class Task:
    channel_id: int
    guild_id: int
    role_id: int

@dataclass(slots=True, frozen=True)
class Season:
    id: int
    name: str
    starts_at: str
    ends_at: str


@dataclass(slots=True, frozen=True)
class CompleteLb:
    channel_id: int
    message_id: int
    guild_id: int
    timestamp: int
    category:str
    timeframe: str
    server_id: int

@dataclass(slots=True, frozen=True)
class MonitorSystem:
    server_id: int
    channel_id: int
    guild_id: int
    message_id:int
