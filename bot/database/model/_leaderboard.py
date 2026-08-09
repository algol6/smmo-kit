from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class Leaderboard:
    channel_id: int
    message_id: int
    guild_id: int
    server_id: int
    timeframe: str
    timestamp: int
