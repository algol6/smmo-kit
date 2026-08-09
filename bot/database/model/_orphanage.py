from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class Orphanage:
    channel_id: int
    role_id: int
    tier: int
    active: int
    message_id: int
    server_id: int
