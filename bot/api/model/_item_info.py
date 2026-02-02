from dataclasses import dataclass


@dataclass
class ItemMarketData:
    low: int
    high: int


@dataclass
class ItemInfo:
    id: int
    name: str
    item_type: str
    image_url: str
    description: str
    equipable: str
    level: int
    rarity: str
    value: int
    stat1: str
    stat1modifier: int
    stat2: str
    stat2modifier: int
    stat3: str
    stat3modifier: int
    custom_item: bool
    tradable: bool
    locked: bool
    circulation: int
    market: ItemMarketData

    def __post_init__(self):
        self.market = ItemMarketData(**self.market)
