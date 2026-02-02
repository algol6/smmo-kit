from dataclasses import dataclass


@dataclass
class Boss:
    id: int
    name: str
    avatar: str
    level: int
    god: bool
    strength: int
    defence: int
    dexterity: int
    current_hp: int
    max_hp: int
    enable_time: int
