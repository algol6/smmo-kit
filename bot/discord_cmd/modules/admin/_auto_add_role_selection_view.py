import discord
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.helpers.logger import logger
from bot.database import Database
from bot.api import SMMOApi


class WelcomeModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="Welcome Message (optional)",placeholder="Leave empty if you don't want to set any message", required=False,style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = AddRolesView()
        view.author_id = self.author_id
        view.welc_msg = self.children[0].value
        await view.send(interaction)

class AddRolesView(discord.ui.View):
    def __init__(self):
        self.guildmates = []
        self.visitators = []
        self.channel = None
        super().__init__(timeout=None)

    async def send(self, ctx:discord.Interaction):
        await ctx.followup.send(embed=await self.create_embed(),view=self)
        
    async def update_message(self):
        self.update_btn()
        await self.message.edit(embed=await self.create_embed(), view=self)

    def update_btn(self):
        self.confirm_button.disabled = len(self.guildmates) == 0 or len(self.visitators) == 0 or self.channel is None

    async def create_embed(self):
        emb = helpers.Embed(title=f"Joining Settings",description="Bot Require *Manage Roles* perms to do this. Since those aren't included by default you need to add manually")
        
        if len(self.guildmates) == 0:
            msg = "No roles selected yet"
        else:
            msg = "\n".join(f"<@&{x}>" for x in self.guildmates)
        emb.add_field(name="Guildmates Roles:",
                    value=msg,
                    inline=False
                    )
        if len(self.visitators) == 0:
            msg = "No roles selected yet"
        else:
            msg = "\n".join(f"<@&{x}>" for x in self.visitators)
        emb.add_field(name="Visitators Roles:",
                    value=msg,
                    inline=False
                    )

        if self.welc_msg != "":
            emb.add_field(name="Welcome Message:",
                        value=self.welc_msg,
                        inline=False
                        )
        if self.channel is not None:
            emb.add_field(name="Channel:",
                        value=f"<#{self.channel.id}>",
                        inline=False
                        )
        return emb

    
    @discord.ui.select(
        row = 0,
        placeholder="Guildmates",
        select_type=discord.ComponentType.role_select,
        max_values = 25
    )
    async def select1_callback(self, select, interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.followup.send(content="You don't have permission to press this button.", ephemeral=True)
        for val in select.values:
            if val.id in self.guildmates:
                continue
            self.guildmates.append(val.id)
        await self.update_message()

    @discord.ui.select(
        row = 1,
        placeholder="Visitators",
        select_type=discord.ComponentType.role_select,
        max_values = 25
    )
    async def select2_callback(self, select, interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.followup.send(content="You don't have permission to press this button.", ephemeral=True)
        for val in select.values:
            if val.id in self.visitators:
                continue
            self.visitators.append(val.id)
        await self.update_message()
    @discord.ui.select(
        row = 2,
        placeholder="Channel",
        select_type=discord.ComponentType.channel_select
    )
    async def select3_callback(self, select, interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.followup.send(content="You don't have permission to press this button.", ephemeral=True)
        self.channel = select.values[0]
        await self.update_message()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red,emoji="🗑️")
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        if interaction.user.id != self.author_id:
            return await interaction.followup.send(content="You don't have permission to press this button.", ephemeral=True)
        await self.message.delete()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green,emoji="✔️",disabled=True)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()

        join_roles_g = ":".join(str(x) for x in self.guildmates)
        join_roles_v = ":".join(str(x) for x in self.visitators)
        await Database.insert_join_roles(interaction.guild_id,self.welc_msg,join_roles_g,join_roles_v,self.channel.id)
        await self.message.delete()
        await interaction.followup.send(content="Set up complete.", ephemeral=True)

