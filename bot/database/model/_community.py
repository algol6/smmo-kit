from dataclasses import dataclass


@dataclass
class Market:
    id: int
    title: str
    description: str
    category: int
    price: str
    author_id: int
    author_smmo_id: int
    author_name: str
    time: int

@dataclass
class MarketNotice:
    channel_id: int

@dataclass
class MarketNoticeItem:
    item_id: int
    message_id: int
    time: int