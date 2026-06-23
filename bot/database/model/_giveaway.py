from dataclasses import dataclass

@dataclass
class Giveaway:
    id: int
    name: str
    description: str
    prize: str
    guild_only: bool
    time: int
    winners: int

class GiveawayParticipant:
    name: str
    discord_id: int
    smmo_id: int
    giveaway_id: int
    