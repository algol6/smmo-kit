from dataclasses import dataclass

@dataclass
class Leaderboard:
    channel_id: int
    message_id: int
    guild_id: int
    date: str