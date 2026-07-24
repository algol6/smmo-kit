import discord
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.helpers.logger import logger
from bot.database import Database
from bot.api import SMMOApi



class DiasModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="Price below which the bot will ping",placeholder="Write full price here. ex. 3000000"))

        self.toggle = discord.ui.CheckboxGroup(
            required=False,
            min_values=0,
            max_values=1
        )

        self.toggle.add_option(
            label="Ping only for God World Bosses?",
            value="opt_in",
            default=False
        )

        self.add_item(self.toggle)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        checked_boxes = self.children[1].values

        # 3. Convert the result into a clean Python boolean
        wants_to = bool(checked_boxes and "opt_in" in checked_boxes)


class ConfigPings(discord.ui.View):
    def __init__(self,server_id:int):
        super().__init__(timeout=None)
        self.ch = None
        self.rl = None
        self.type = None
        self.sid = server_id
        self.conf = None
        self.val = None
        self.TEMPLATE = (
            "Diamond Pings:",
            "Monthly Rewards Pings:",
            "Orphanage Pings:",
            "Worldboss Pings:",
            "[<#{chid}>] Ping if under: {var:,} :coin:",
            "[<#{chid}>]",
            "[<#{chid}>] Tier {var}",
            "[<#{chid}>] Minutes before: {var}"
        )

        self.dias_btn = discord.ui.Button(
            custom_id="dias-btn",
            label="Set max price"
        )
        self.dias_btn.callback = self.dias_btn_callback

    async def load_conf(self):
        self.conf = [
            tuple(await Database.select_diamonds_sid(self.sid)),
            tuple(await Database.select_monthly_reward_sid(self.sid)),
            tuple(await Database.select_orphanage_sid(self.sid)),
            tuple(await Database.select_wb_notification_sid(self.sid))
        ]

    async def send(self, ctx:discord.ApplicationContext):
        await self.load_conf()
        await ctx.followup.send(embed=await self.create_embed(),view=self)

    def update_btn(self):
        self.confirm_button.disabled = self.ch is None or self.type is None or self.rl is None
        if self.conf is not None and self.type is not None:
            for x in self.conf[int(self.type)]:
                if x is None:
                    continue
                if self.ch == x.channel_id:
                    self.delete_button.disabled = False
                    break
                self.delete_button.disabled = True


    async def update_message(self, interaction:discord.Interaction):
        self.update_btn()
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)

    async def create_embed(self):
        emb = helpers.Embed(title="Configure Pings",description="")
        emb.add_field(
            name="Diamonds:",
            value="Ping when someone is selling in the diamond market with a cheap price.",
            inline=False
        )
        emb.add_field(
            name="Monthly Reward",
            value="Ping on when the monthly reward is redeemable.",
            inline=False
        )
        emb.add_field(
            name="Orphanage:",
            value="Ping when the orphanage buff is available.",
            inline=False
        )
        emb.add_field(
            name="Worldboss:",
            value="Ping When a world boss is about to be attackable.",
            inline=False
        )
        if self.conf is not None:
            for i,c in enumerate(self.conf):
                if c is None:
                    continue
                msg = "Not Found"
                match i:
                    case 0:
                        msg = self.TEMPLATE[i+(len(self.TEMPLATE)//2)].format(chid=c.channel_id,var=c.min_price)
                    case 1:
                        msg = self.TEMPLATE[i+(len(self.TEMPLATE)//2)].format(chid=c.channel_id)
                    case 2:
                        msg = self.TEMPLATE[i+(len(self.TEMPLATE)//2)].format(chid=c.channel_id,var=c.tier)
                    case 3:
                        msg = self.TEMPLATE[i+(len(self.TEMPLATE)//2)].format(chid=c.channel_id,var=helpers.formattime(c.seconds_before))
                emb.add_field(
                    name=self.TEMPLATE[i],
                    value=msg,
                    inline=False
                )

        return emb

    @discord.ui.select(
        row = 0,
        max_values=25,
        placeholder="Channel",
        select_type=discord.ComponentType.channel_select
    )
    async def select0_callback(self, select, interaction):
        await interaction.response.defer()
        self.ch = select.values
        await self.update_message(interaction)

    @discord.ui.select(
        row = 0,
        max_values=25,
        placeholder="Roles",
        select_type=discord.ComponentType.role_select
    )
    async def select_callback(self, select, interaction):
        await interaction.response.defer()
        self.rl = select.values
        await self.update_message(interaction)

    @discord.ui.select(
        row = 1,
        placeholder="Type",
        options=[
            discord.SelectOption(label="Diamond ping",value="0"),
            discord.SelectOption(label="Monthly Reward", value="1"),
            discord.SelectOption(label="Orphanage", value="2"),
            discord.SelectOption(label="Worldboss", value="3"),
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

        match self.type:
            case "0":
                pass
                # dias min price
            case "2":
                pass
                # orphanage tier
            case "3":
                pass
                # wb [time,god only?]
        if self.type == "Members Complete" and not self.get_item("cat-selection"):
            self.add_item(self.category_select)
        elif self.get_item("cat-selection"):
            self.remove_item(self.category_select)
        if self.type != "Members Complete":
            self.cat = None

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

    @discord.ui.button(label="Remove Ping", style=discord.ButtonStyle.red, disabled=True)
    async def delete_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(embed=helpers.Embed(title="Operation cancelled"),view=None)

    @discord.ui.button(label="Add Ping", style=discord.ButtonStyle.green,emoji="✔️",disabled=True)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()

        error = False
        for ch in self.ch:
            try:
                channel = await self.client.fetch_channel(self.ch.id)
                await channel.send(content="test message.", delete_after=1)
            except discord.Forbidden:
                return await interaction.followup.send(content="Bot doesn't have the perms to see/write the channel.", ephemeral=True)
            for rl in self.rl:
                match self.type:
                    case "0":
                        error = not await Database.insert_diamonds(rl.id,ch.id,self.val)
                    case "1":
                        error = not await Database.insert_monthly_reward(rl.id,ch.id)
                    case "2":
                        try:
                            msg = await channel.send(content="Orphanage")
                            error = not await Database.insert_orphanage(ch.id,msg.id,rl,self.val,False)
                        except:
                            error = True
                    case "3":
                        error = not await Database.insert_wb_notification(ch.id,rl.id,self.val[0],self.val[1])

        self.ch = None
        self.rl = None
        self.type = None
        self.conf = None
        self.val = None

        if error:
            await interaction.followup.send("Some channels might already had an identical ping already set.")
        else:
            await interaction.followup.send(content="Set up complete.", ephemeral=True)

        await self.update_message(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red,emoji="🗑️")
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(embed=helpers.Embed(title="Operation cancelled"),view=None)

    async def dias_btn_callback(self, interaction):
        pass
        #send modal
