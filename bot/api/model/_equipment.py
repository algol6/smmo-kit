from dataclasses import dataclass


@dataclass
class Equipment:
    item_id: int
    name: str
    item_type: str
    description: str
    stat1: str
    stat1modifier: int
    stat2: str
    stat2modifier: int
    stat3: str
    stat3modifier: int
