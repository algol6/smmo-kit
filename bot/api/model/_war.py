from dataclasses import dataclass

@dataclass
class Guild_War:
    id: int
    name: str
    kills: int


@dataclass
class Wars:
    guild_1: Guild_War
    guild_2: Guild_War
    status: str

