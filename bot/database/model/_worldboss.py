from dataclasses import dataclass


@dataclass
class WorldbossNotification:
        channel_id: int
        role_id: int
        seconds_before: int
        god: int
        boss_id: int

@dataclass
class WorldbossMessage:
        channel_id: int
        boss_id: int

@dataclass
class WorldBoss:
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