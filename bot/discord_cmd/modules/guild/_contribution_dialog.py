import discord

class ContributionModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.api_key = None
        self.add_item(discord.ui.InputText(label="API Key"))

    async def callback(self, interaction: discord.Interaction):
        self.api_key = self.children[0].value
        await interaction.response.send_message(content="Loading command.",delete_after=600)
        self.stop()