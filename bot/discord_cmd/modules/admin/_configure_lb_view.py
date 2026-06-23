import discord
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.helpers.logger import logger
from bot.database import Database
from bot.api import SMMOApi


class ConfigLB(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.category_select = discord.ui.Select(
            custom_id="cat-selection",
            row=3,
            placeholder="Choose a category...",
            options=[
                discord.SelectOption(label="LEVELS"),
                discord.SelectOption(label="NPC"),
                discord.SelectOption(label="PVP"),
                discord.SelectOption(label="STEPS")
            ]
        )
        self.category_select.callback = self.select3_callback

        self.ch = None
        self.tf = None
        self.type = None
        self.cat = None

    async def send(self, ctx:discord.ApplicationContext):
        await ctx.followup.send(embed=await self.create_embed(),view=self)

    def update_btn(self):
        if self.type != "Members Complete":
            self.confirm_button.disabled = self.tf is None or self.type is None or self.ch is None
        else:
            self.confirm_button.disabled = self.tf is None or self.type is None or self.cat is not None or self.ch is None

    async def update_message(self, interaction:discord.Interaction):
        self.update_btn()
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)

    async def create_embed(self):
        emb = helpers.Embed(title="Configure Leaderboard",description="")
        emb.add_field(
            name="Guild",
            value="Set the guilds leaderboards. It Show the top 25 guilds with their gains",
            inline=False
        )
        emb.add_field(
            name="Members General",
            value="Set a leaderboard for the top members of the guild. It Show the top 5 players in each category (Npc Kills, Pvp Kills, Steps and Levels Gained).",
            inline=False
        )
        emb.add_field(
            name="Members Complete",
            value="Set a leaderboard to show all members of one category. Multiple leaderboards can be set in the same channel to show all of the categories.",
            inline=False
        )

        return emb

    @discord.ui.select(
        row = 0,
        placeholder="Channel",
        select_type=discord.ComponentType.channel_select
    )
    async def select0_callback(self, select, interaction):
        await interaction.response.defer()
        self.ch = select.values[0]
        await self.update_message(interaction)

    @discord.ui.select(
        row = 1,
        placeholder="Type",
        options=[
            discord.SelectOption(label="Guild"),
            discord.SelectOption(label="Members General"),
            discord.SelectOption(label="Members Complete")
        ]
    )
    async def select1_callback(self, select, interaction):
        await interaction.response.defer()
        selected_value = self.select1_callback.values[0]
        if selected_value is None:
            return
        for option in self.select1_callback.options:
            option.default = option.value == selected_value
        self.type = selected_value
        if self.type == "Members Complete" and not self.get_item("cat-selection"):
            self.add_item(self.category_select)
        elif self.get_item("cat-selection"):
            self.cat = None
            self.remove_item(self.category_select)
        await self.update_message(interaction)

    @discord.ui.select(
        row = 2,
        placeholder="Timeframe",
        options=[
            discord.SelectOption(label="Daily"),
            discord.SelectOption(label="In-Game Weekly"),
            discord.SelectOption(label="In-Game Monthly")
        ]
    )
    async def select2_callback(self, select, interaction):
        await interaction.response.defer()
        selected_value = self.select2_callback.values[0]
        if selected_value is None:
            return
        for option in self.select2_callback.options:
            option.default = option.value == selected_value
        self.tf = selected_value
        await self.update_message(interaction)


    async def select3_callback(self, interaction):
        await interaction.response.defer()
        selected_value = self.select3_callback.values[0]
        if selected_value is None:
            return
        for option in self.select3_callback.options:
            option.default = option.value == selected_value
        self.cat = selected_value
        await self.update_message(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red,emoji="🗑️")
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(embed=helpers.Embed(title="Operation cancelled"),view=None)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green,emoji="✔️",disabled=True)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()

        try:
            channel = await self.client.fetch_channel(self.ch.id)
            await channel.send(content="test message.", delete_after=1)
        except discord.Forbidden:
            return await interaction.followup.send(content="Bot doesn't have the perms to see/write the channel.", ephemeral=True)
        message = await channel.send(content="The member lb will be setted here.")
        timestamp = int(helpers.get_date_game(self.tf).timestamp())
        error = False
        match self.type:
            case "Guild":
                error = not await Database.insert_gains_leaderboard(channel.id, message.id)
            case "Members General":
                error = not await Database.insert_lb(channel.id, message.id, await Database.select_server(interaction.guild_id),helpers.get_current_date_game().strftime("%d/%m/%Y"))
            case "Members Complete":
                error = not await Database.insert_cmp_lb(channel.id,message.id,await Database.select_server(interaction.guild_id),timestamp,self.cat,self.tf)

        self.tf = None
        self.type = None
        self.cat = None
        self.ch = None

        if error:
            await helpers.send(interaction,content="Already set")
            await message.delete()
        else:
            await interaction.followup.send(content="Set up complete.", ephemeral=True)

        await self.update_message(interaction)
