import discord
from bot.api import SMMOApi
from bot.discord_cmd.helpers import helpers 

class EquipmentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    current_page: int = 0

    async def on_timeout(self):
        self.disable_all_items()
        self.remove_item(self.children)
        self.prev_button.style = discord.ButtonStyle.gray
        self.next_button.style = discord.ButtonStyle.gray


    async def send(self, ctx: discord.ApplicationContext):
        self.ctx = ctx
        self.message = await ctx.followup.send(view=self)
        await self.update_message(self.data[self.current_page])


    async def update_message(self, data):
        await self.update_buttons()
        try:
            await self.message.edit(embed=await self.create_embed(data), view=self)
        except discord.errors.Forbidden:
            await self.ctx.followup.send(content="Bot doesn't have the perms to see this channel, so the buttons of the message doesn't work.")

    async def update_buttons(self):
        if self.current_page == 0:
            self.prev_button.disabled = True
            self.prev_button.style = discord.ButtonStyle.gray
        else:
            self.prev_button.disabled = False
            self.prev_button.style = discord.ButtonStyle.primary

        if self.current_page == len(self.data) - 1:
            self.next_button.disabled = True
            self.next_button.style = discord.ButtonStyle.gray
        else:
            self.next_button.disabled = False
            self.next_button.style = discord.ButtonStyle.primary


    def get_hex_color(self, item):
        if item.rarity == "Celestial":
            return 0x00f6ff
        if item.rarity == "Legendary":
            return 0xf1c40f
        if item.rarity == "Epic":
            return 0x8e44ad
        if item.rarity == "Elite":
            return 0xc0392b
        if item.rarity == "Rare":
            return 0xe67e22
        if item.rarity == "Uncommon":
            return 0x2980b9
        if item.rarity == "Common":
            return 0x34495e


    async def create_embed(self, data):
        item = await SMMOApi.get_item_info(data.item_id)
        rarity_color = self.get_hex_color(item)
        desc = data.description
        if desc is not None:
            desc = "\n".join(desc.split("<br/>"))
            desc = "\n".join(desc.split("<Br/>"))
            desc = "**".join(desc.split("<strong>"))
            desc = "**".join(desc.split("</strong>"))
        emb = helpers.Embed(title=f"{self.user.name}'s equipment",
                            url=f"https://simple-mmo.com/user/view/{self.user.id}",
                            thumbnail=f"https://simple-mmo.com{item.image_url}",
                            color=rarity_color)
        emb.add_field(name=data.name, value=f"Type: {data.item_type}\n{desc}", inline=False)
        emb.set_footer(text=f"Page {self.current_page+1}/{len(self.data)}")
        a1 = []
        a1.append([data.stat1, item.stat1modifier])
        a1.append([data.stat2, item.stat2modifier])
        a1.append([data.stat3, item.stat3modifier])

        for k in a1:
            if k[0] == "def":
                k[0] = "Defence"
            elif k[0] == "crit":
                k[0] = "Critical chance"
            elif k[0] == "str":
                k[0] = "Strength"
            else:
                k[0] = None
        
        for k in a1:
            if k[0] is not None:
                emb.add_field(name=k[0],
                              value=f"{format(k[1],",d") if k[0] != "Critical chance" else f"{"{:.1f}".format(k[1]/10)}%"}"
                              f"{':crossed_swords:' if k[0] == 'Strength' else ':shield:' if k[0] == 'Defence' else ':exclamation:'}", 
                              inline=True)

        emb.add_field(name="Market value", value=f":coin:{item.market.low:,} - :coin:{item.market.high:,}", inline=False)

        return emb
    
            
    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def prev_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page -= 1
        if self.current_page < 0:
            self.current_page = len(self.data) - 1
            
        await self.update_message(self.data[self.current_page])

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page += 1
        try:
            await self.update_message(self.data[self.current_page])
        except IndexError:
            self.current_page = 0
            await self.update_message(self.data[self.current_page])
    