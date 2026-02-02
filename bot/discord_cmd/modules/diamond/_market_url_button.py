from discord.ui import Button,View
from discord import ButtonStyle

class MarketUrlButton(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(Button(
            label='Go to market',
            style=ButtonStyle.primary,
            url='https://simple-mmo.com/diamond-market'
        ))
