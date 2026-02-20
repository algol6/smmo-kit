from dataclasses import dataclass

@dataclass
class Orphanage:
    channel_id: int
    role_id: int
    tier: int
    active: int
    message_id: int
