from dataclasses import dataclass


@dataclass
class OrphanageTier:
    key: str
    name: str


@dataclass
class OrphanageEntry:
    tier: OrphanageTier
    effects: list[str]
    current_value: int
    target_value: int
    target_remaining: int
    percentage: int
    goal_reached_at: None | str
    expires_in: None | str
    has_expired: bool
    is_active: bool
    in_progress: bool

    def __post_init__(self):
        self.tier = OrphanageTier(**self.tier)
