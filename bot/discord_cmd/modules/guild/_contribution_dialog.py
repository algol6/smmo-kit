import discord
from bot.api import SMMOApi
from bot.discord_cmd.modules.guild._contribution_view import ContributionView

class ContributionModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.api_key = None
        self.add_item(discord.ui.InputText(label="API Key"))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.api_key = self.children[0].value
        await interaction.followup.send(content="Loading command.",delete_after=600)
        self.stop()

        user = await SMMOApi.get_me(self.api_key)
        if user is None:
            return await interaction.respond("API Key not valid.")
        data = [[],[],[],[],[],[],[],[]]
        print("Do not turn off, contribution ongoing")
        for member in await SMMOApi.get_guild_members(user.guild["id"]):
            contr = await SMMOApi.get_guild_member_contribution(user.guild["id"], member.user_id, self.api_key)
            if contr is None:
                continue
            data[0].append({"name":member.name,"id":member.user_id,"stats":contr.power_points_deposited})
            data[1].append({"name":member.name,"id":member.user_id,"stats":contr.gold_deposited})
            data[2].append({"name":member.name,"id":member.user_id,"stats":contr.pve_exp, "count":contr.pve_kills})
            data[3].append({"name":member.name,"id":member.user_id,"stats":contr.pvp_exp, "count":contr.pvp_kills})
            data[4].append({"name":member.name,"id":member.user_id,"stats":contr.steps_experience, "count":contr.steps_taken})
            data[5].append({"name":member.name,"id":member.user_id,"stats":contr.nodes_experience, "count":contr.nodes_gathered})
            data[6].append({"name":member.name,"id":member.user_id,"stats":contr.tax_contribution["guild_bank"]})
            data[7].append({"name":member.name,"id":member.user_id,"stats":contr.tax_contribution["sanctuary"]})

        print("Contribution data fetched.")

        data = [sorted(x, key=lambda item: -item["stats"]) for x in data]
        contribution_view = ContributionView()
        contribution_view.data = data
        return await contribution_view.send(interaction)
