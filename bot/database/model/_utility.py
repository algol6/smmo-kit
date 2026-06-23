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


@dataclass
class RoleMessage:
    server_id: int
    role_id: int
    channel_id: int
    text: str