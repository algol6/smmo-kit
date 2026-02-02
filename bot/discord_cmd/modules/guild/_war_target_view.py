import discord
from bot.discord_cmd.helpers import helpers
from math import ceil
from datetime import timedelta

class WarTargetView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)


    current_page: int = 1
    sep: int = 10
    type: int = 0
       
    async def send(self, ctx: discord.ApplicationContext):
        self.ctx = ctx
        self.message = await ctx.followup.send(view=self)
        self.type = 0
        await self.update_message(self.data[self.type][:self.sep])

    async def update_message(self, data):
        await self.update_buttons()
        try:
            await self.message.edit(embed=await self.create_embed(data), view=self)
        except discord.errors.Forbidden:
            await self.ctx.followup.send(content="Bot doesn't have the perms to see this channel, so the buttons of the message doesn't work.")


    async def update_buttons(self):
        if self.current_page == 1:
            self.prev_button.disabled = True
            self.prev_button.style = discord.ButtonStyle.gray
            self.first_button.disabled = True
            self.first_button.style = discord.ButtonStyle.gray
        else:
            self.prev_button.disabled = False
            self.prev_button.style = discord.ButtonStyle.primary
            self.first_button.disabled = False
            self.first_button.style = discord.ButtonStyle.green

        if self.current_page == int(len(self.data[self.type])/self.sep) + 1:
            self.next_button.disabled = True
            self.next_button.style = discord.ButtonStyle.gray
            self.last_button.disabled = True
            self.last_button.style = discord.ButtonStyle.gray
        else:
            self.next_button.disabled = False
            self.next_button.style = discord.ButtonStyle.primary
            self.last_button.disabled = False
            self.last_button.style = discord.ButtonStyle.green

    def get_current_page_data(self):
        until_item = self.current_page * self.sep
        from_item = until_item - self.sep
        if self.current_page == 1:
            from_item = 0
            until_item = self.sep
        if self.current_page == int((len(self.data[self.type])) / self.sep) + 1:
            from_item = self.current_page * self.sep - self.sep
            until_item = len(self.data[self.type])
        return self.data[self.type][from_item:until_item]
    
    async def create_embed(self, data):
        emb = helpers.Embed(title=f"{self.guild_info.name}'s Attackable Members",
                                  description=f"Last Update: <t:{int(self.updated.timestamp())}:R>\nAttackable Members: {len(self.data[self.type])}",
                                  thumbnail=f"https://simple-mmo.com/img/icons/{self.guild_info.icon}")
        if self.updated.minute % 5 != 0:
            self.updated += timedelta(minutes=5-(self.updated.minute % 5))
    
        for user in data:
            percentage = 0.1 if user.membership else 0.05
            emb.add_field(name=f"{user.name} [{user.id}]", 
                          value=f"Lvl: {user.level:,}\nHP: {user.hp/user.max_hp:.0%} {":heart:" if user.hp/user.max_hp>=0.5 else ":broken_heart:"}{f"\nAttackable in: <t:{int((self.updated + timedelta(minutes=(ceil((0.5-(user.hp/user.max_hp))/percentage)*5))).timestamp())}:R>" if user.hp/user.max_hp<0.5 else ""}",
                          inline=False)
        emb.set_footer(text=f"Page {self.current_page}/{(len(self.data[self.type])) // self.sep + 1}")
        return emb
    
    @discord.ui.button(label="|<", style=discord.ButtonStyle.green)
    async def first_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        await self.update_message(self.get_current_page_data())
            

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def prev_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page -= 1
        await self.update_message(self.get_current_page_data())


    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page += 1
        await self.update_message(self.get_current_page_data())


    @discord.ui.button(label=">|", style=discord.ButtonStyle.green)
    async def last_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = int(len(self.data[self.type]) / self.sep) + 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Attackable", style=discord.ButtonStyle.blurple)
    async def attackable_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.type = 0
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="All", style=discord.ButtonStyle.blurple)
    async def all_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.type = 1
        await self.update_message(self.get_current_page_data())
