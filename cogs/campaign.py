import discord
from discord import app_commands
from discord.ext import commands

from core import database as db


class CampaignCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    campaign_group = app_commands.Group(name="campaign", description="캠페인 진행 관리")

    @campaign_group.command(name="status", description="캠페인 현재 상태를 봅니다")
    async def status(self, interaction: discord.Interaction):
        state = await db.get_campaign_state(interaction.guild_id)
        completed = await db.get_completed_scenarios(interaction.guild_id)
        achievements = await db.get_achievements(interaction.guild_id)

        embed = discord.Embed(title="📜 캠페인 현황", color=discord.Color.dark_gold())
        if state["current_scenario_num"]:
            embed.add_field(
                name="진행 중인 시나리오",
                value=f"#{state['current_scenario_num']} {state['current_scenario_name']}",
                inline=False,
            )
        else:
            embed.add_field(name="진행 중인 시나리오", value="없음", inline=False)

        embed.add_field(name="번영도 (Prosperity)", value=str(state["prosperity"]))
        embed.add_field(name="평판 (Reputation)", value=str(state["reputation"]))
        embed.add_field(name="클리어한 시나리오", value=str(len(completed)))
        embed.add_field(name="달성한 업적/이벤트", value=str(len(achievements)))
        if state["notes"]:
            embed.add_field(name="메모", value=state["notes"], inline=False)
        await interaction.response.send_message(embed=embed)

    @campaign_group.command(name="scenario-start", description="새 시나리오를 시작합니다")
    async def scenario_start(self, interaction: discord.Interaction, number: int, name: str):
        await db.set_current_scenario(interaction.guild_id, number, name)
        await interaction.response.send_message(f"📖 시나리오 #{number} **{name}** 시작!")

    @campaign_group.command(name="scenario-complete", description="현재 시나리오를 클리어 처리합니다")
    async def scenario_complete(self, interaction: discord.Interaction):
        state = await db.get_campaign_state(interaction.guild_id)
        if not state["current_scenario_name"]:
            await interaction.response.send_message("진행 중인 시나리오가 없어요.", ephemeral=True)
            return
        await db.complete_scenario(
            interaction.guild_id, state["current_scenario_num"], state["current_scenario_name"]
        )
        await db.set_current_scenario(interaction.guild_id, None, None)
        await interaction.response.send_message(
            f"🏆 시나리오 #{state['current_scenario_num']} **{state['current_scenario_name']}** 클리어!"
        )

    @campaign_group.command(name="scenario-list", description="클리어한 시나리오 목록을 봅니다")
    async def scenario_list(self, interaction: discord.Interaction):
        rows = await db.get_completed_scenarios(interaction.guild_id)
        if not rows:
            await interaction.response.send_message("아직 클리어한 시나리오가 없어요.", ephemeral=True)
            return
        lines = [f"#{r['scenario_num']} {r['scenario_name']}" for r in rows]
        embed = discord.Embed(
            title=f"✅ 클리어한 시나리오 ({len(rows)})",
            description="\n".join(lines),
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @campaign_group.command(name="prosperity", description="번영도를 증감합니다 (음수 가능)")
    async def prosperity(self, interaction: discord.Interaction, amount: int):
        new_val = await db.adjust_prosperity(interaction.guild_id, amount)
        await interaction.response.send_message(f"🏙️ 번영도: {new_val}")

    @campaign_group.command(name="reputation", description="평판을 증감합니다 (음수 가능, -20~20)")
    async def reputation(self, interaction: discord.Interaction, amount: int):
        new_val = await db.adjust_reputation(interaction.guild_id, amount)
        await interaction.response.send_message(f"⚖️ 평판: {new_val}")

    @campaign_group.command(name="achievement-add", description="업적/도시·거리 이벤트 결과를 기록합니다")
    async def achievement_add(self, interaction: discord.Interaction, text: str):
        await db.add_achievement(interaction.guild_id, text)
        await interaction.response.send_message(f"🔖 기록됨: {text}")

    @campaign_group.command(name="achievement-list", description="기록된 업적/이벤트 목록을 봅니다")
    async def achievement_list(self, interaction: discord.Interaction):
        rows = await db.get_achievements(interaction.guild_id)
        if not rows:
            await interaction.response.send_message("기록된 업적이 없어요.", ephemeral=True)
            return
        lines = [f"• {r['text']}" for r in rows]
        embed = discord.Embed(
            title=f"🗒️ 업적/이벤트 기록 ({len(rows)})",
            description="\n".join(lines)[:4000],
            color=discord.Color.teal(),
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CampaignCog(bot))
