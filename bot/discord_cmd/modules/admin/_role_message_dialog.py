import discord
from bot.database import Database

class RoleMessageModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="Message",placeholder="Insert '{user}' to mention a user.",style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        msg = self.children[0].value

        if not await Database.insert_role_message(interaction.guild_id,self.role.id,self.channel.id,msg):
            await interaction.followup.send("Message already set. Remove it before adding a new one.",ephemeral=True)
            
        self.stop()