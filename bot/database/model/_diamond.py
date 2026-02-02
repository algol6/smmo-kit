from dataclasses import dataclass

@dataclass
class Diamond:
    role_id: int
    channel_id : int
    min_price: int
    last_min_price: str