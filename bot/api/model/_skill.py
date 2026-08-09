from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Skill:
    skill: str
    level: int
    exp: int
