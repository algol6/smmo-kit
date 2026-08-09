from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Location:
    id: int
    name: str
