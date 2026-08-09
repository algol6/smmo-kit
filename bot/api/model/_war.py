from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class Guild_War:
    id: int
    name: str
    kills: int


@dataclass(slots=True, frozen=True)
class Wars:
    guild_1: Guild_War
    guild_2: Guild_War
    status: str
