from dataclasses import dataclass

@dataclass
class GuildStats:
    year: int
    month: int
    day: int
    time: int
    guild_id: int
    position: int
    experience: int
    season: int

@dataclass
class Requirements:
    guild_id: int
    days: int
    levels: int
    npc: int
    pvp: int
    steps: int

@dataclass
class Staff:
    guild_id: int
    role_id: int

@dataclass
class Server:
    guild_id: int
    server_id: int

@dataclass
class Rewards:
    guild_id: int
    gold: int
    x_days: int
    year: int
    month: int
    day: int

@dataclass
class SafeUser:
    smmo_id: int
    guild_id: int

@dataclass
class GainsLeaderboard:
    channel_id: int
    message_id: int

@dataclass
class Raid:
    channel_id: int
    time: int
    duration: int
    role_id: int

@dataclass
class Task:
    channel_id: int
    guild_id: int
    role_id: int