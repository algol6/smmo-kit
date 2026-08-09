from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class ApiKey:
    api_key: str
    guild_id: int
    smmo_id: int

@dataclass(slots=True, frozen=True)
class Staff:
    guild_id: int
    role_id: int


@dataclass(slots=True, frozen=True)
class RoleMessage:
    server_id: int
    role_id: int
    channel_id: int
    text: str
