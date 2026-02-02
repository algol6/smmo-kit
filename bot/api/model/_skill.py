from dataclasses import dataclass


@dataclass
class Skill:
    skill: str
    level: int
    exp: int
