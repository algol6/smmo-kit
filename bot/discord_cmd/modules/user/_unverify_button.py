import discord
from bot.database import Database
from bot.discord_cmd.helpers import helpers 

class UnverifyButton(discord.ui.View):

    async def send(self, ctx: discord.ApplicationContext):
        self.emb = helpers.Embed(title="Unlink profile?", description="Profile can be linked again with the command `/user verify`.")
        self.message = await ctx.followup.send(embed=self.emb, view=self)


    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await Database.delete_user(self.user_id)
        self.disable_all_items()
        await interaction.response.edit_message(embed=helpers.Embed(title="Profile unlinked"),view=self)
        
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancell_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        self.disable_all_items()
        await interaction.response.edit_message(embed=helpers.Embed(title="Operation cancelled"),view=self)

