from dataclasses import dataclass


@dataclass
class User:
    discord_id: int
    smmo_id: int
    verification: str

@dataclass
class Track:
    smmo_id: int

@dataclass
class Valut:
    code:str
    year:int
    month:int
    day:int
    note:str

@dataclass
class ValutMsg:
    channel_id:int
    role_id:int
    status:int

@dataclass
class BestStats:
    smmo_id:int
    name:str
    category:str
    date:int
    levels:int
    steps:int
    npc:int
    pvp:int
    