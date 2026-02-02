import discord


class WorldbossUrlButton(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(discord.ui.Button(
            label='Go to all worldbosses',
            style=discord.ButtonStyle.primary,
            url='https://simple-mmo.com/battle/world-bosses'
        ))
    