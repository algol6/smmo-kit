from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class MonthlyRewards:
    role_id: int
    channel_id: int
    server_id: int
