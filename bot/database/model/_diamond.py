from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class Diamond:
    role_id: int
    channel_id : int
    min_price: int
    last_min_price: str
    server_id:int
