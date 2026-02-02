from dataclasses import dataclass

@dataclass
class ApiKey:
    api_key: str
    guild_id: int
    smmo_id: int

@dataclass
class Staff:
    guild_id: int
    role_id: int