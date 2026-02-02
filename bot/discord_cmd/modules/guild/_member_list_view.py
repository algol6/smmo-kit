import discord
from bot.discord_cmd.helpers import helpers 

class MemberListView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    current_page: int = 1
    sep: int = 10

    async def on_timeout(self):
        self.disable_all_items()
        self.prev_button.style = discord.ButtonStyle.gray
        self.next_button.style = discord.ButtonStyle.gray
        self.first_button.style = discord.ButtonStyle.gray
        self.last_button.style = discord.ButtonStyle.gray
        self.member_button.style = discord.ButtonStyle.gray
        self.leader_button.style = discord.ButtonStyle.gray
        self.coleader_button.style = discord.ButtonStyle.gray
        self.officer_button.style = discord.ButtonStyle.gray

    async def send(self, ctx: discord.ApplicationContext):
        self.ctx = ctx
        self.type = "Member"
        self.message = await ctx.followup.send(view=self)
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
        emb = helpers.Embed(title=f"{self.name}'s {self.type}",
                            description=f"**Updated**: <t:{self.updated}:R>",
                            thumbnail=f"https://simple-mmo.com/img/icons/{self.icon}")
        if len(data) != 0:
            emb.add_field(name="", value="\n".join(data))
        else:
            emb.add_field(name="", value="No members (?)")
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
        self.current_page = int((len(self.data[self.type])) / self.sep) + 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Members", style=discord.ButtonStyle.primary)
    async def member_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.type = "Member"
        self.current_page = 1
        self.tier = 0
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Leader", style=discord.ButtonStyle.primary)
    async def leader_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.type = "Leader"
        self.current_page = 1
        self.tier = 0
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Co-leaders", style=discord.ButtonStyle.primary)
    async def coleader_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.type = "Co-leader"
        self.current_page = 1
        self.tier = 0
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Officers", style=discord.ButtonStyle.primary)
    async def officer_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.type = "Officer"
        self.current_page = 1
        self.tier = 0
        await self.update_message(self.get_current_page_data())