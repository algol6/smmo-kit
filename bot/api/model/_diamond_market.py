from dataclasses import dataclass


@dataclass
class DiamondMarketSeller:
    id: int
    name: str


@dataclass
class DiamondMarketEntry:
    seller: DiamondMarketSeller
    diamond_amount_at_start: int
    diamonds_remaining: int
    price_per_diamond: int
    last_updated: str
    listing_created: str

    def __post_init__(self):
        self.seller = DiamondMarketSeller(**self.seller)
