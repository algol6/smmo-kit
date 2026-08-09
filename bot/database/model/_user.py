from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class User:
    discord_id: int
    smmo_id: int
    verification: str

@dataclass(slots=True, frozen=True)
class Track:
    smmo_id: int

@dataclass(slots=True, frozen=True)
class Valut:
    code:str
    year:int
    month:int
    day:int
    note:str

@dataclass(slots=True, frozen=True)
class ValutMsg:
    channel_id:int
    role_id:int
    status:int
    message_id: int
    code: str
    server_id: int

@dataclass(slots=True, frozen=True)
class BestStats:
    smmo_id:int
    name:str
    category:str
    date:int
    levels:int
    steps:int
    npc:int
    pvp:int
