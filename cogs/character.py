import json
import discord
from discord import app_commands
from discord.ext import commands

from core import database as db
from core.models import Character

with open("data/classes.json", encoding="utf-8") as f:
    CLASS_DATA = json.load(f)

CLASS_CHOICES = [
    app_commands.Choice(name=v["display_name"], value=k) for k, v in CLASS_DATA.items()
]


def hp_for(class_key: str, level: int) -> int:
    idx = min(level, 9) - 1
    return CLASS_DATA[class_key]["hp_by_level"][idx]


class CharacterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    character_group = app_commands.Group(name="character", description="캐릭터 관리")

    @character_group.command(name="create", description="새 캐릭터를 생성합니다")
    @app_commands.choices(job=CLASS_CHOICES)
    async def create(self, interaction: discord.Interaction, name: str, job: app_commands.Choice[str]):
        max_hp = hp_for(job.value, 1)
        char = Character(
            owner_id=interaction.user.id,
            guild_id=interaction.guild_id,
            name=name,
            class_key=job.value,
            level=1,
            max_hp=max_hp,
            current_hp=max_hp,
        )
        char.id = await db.create_character(char)

        embed = discord.Embed(
            title=f"✅ {name} 생성 완료",
            description=f"**{job.name}** · 레벨 1",
            color=discord.Color.green(),
        )
        embed.add_field(name="체력", value=f"{max_hp}/{max_hp}")
        embed.add_field(name="골드", value=str(char.gold))
        embed.add_field(name="손패 크기", value=str(CLASS_DATA[job.value]["hand_size"]))
        await interaction.response.send_message(embed=embed)

    @character_group.command(name="sheet", description="내 캐릭터 정보를 봅니다")
    async def sheet(self, interaction: discord.Interaction):
        row = await db.get_character_by_owner(interaction.user.id, interaction.guild_id)
        if row is None:
            await interaction.response.send_message(
                "캐릭터가 없어요. `/character create` 로 먼저 만들어주세요.", ephemeral=True
            )
            return

        class_display = CLASS_DATA[row["class_key"]]["display_name"]
        embed = discord.Embed(title=f"🗡️ {row['name']}", color=discord.Color.blue())
        embed.add_field(name="직업", value=class_display)
        embed.add_field(name="레벨", value=str(row["level"]))
        embed.add_field(name="체력", value=f"{row['current_hp']}/{row['max_hp']}")
        embed.add_field(name="경험치", value=str(row["exp"]))
        embed.add_field(name="골드", value=str(row["gold"]))
        embed.add_field(name="퍽 포인트", value=str(row["perk_points"]))
        if row["notes"]:
            embed.add_field(name="메모", value=row["notes"], inline=False)
        await interaction.response.send_message(embed=embed)

    @character_group.command(name="heal", description="체력을 회복합니다")
    async def heal(self, interaction: discord.Interaction, amount: int):
        row = await db.get_character_by_owner(interaction.user.id, interaction.guild_id)
        if row is None:
            await interaction.response.send_message("캐릭터가 없어요.", ephemeral=True)
            return
        new_hp = min(row["max_hp"], row["current_hp"] + amount)
        await db.update_hp(row["id"], new_hp)
        await interaction.response.send_message(f"❤️ {row['name']}: {new_hp}/{row['max_hp']}")

    @character_group.command(name="damage", description="피해를 입습니다")
    async def take_damage(self, interaction: discord.Interaction, amount: int):
        row = await db.get_character_by_owner(interaction.user.id, interaction.guild_id)
        if row is None:
            await interaction.response.send_message("캐릭터가 없어요.", ephemeral=True)
            return
        new_hp = max(0, row["current_hp"] - amount)
        await db.update_hp(row["id"], new_hp)
        msg = f"💥 {row['name']}: {new_hp}/{row['max_hp']}"
        if new_hp == 0:
            msg += "\n⚠️ 쓰러졌습니다! (Exhausted)"
        await interaction.response.send_message(msg)

    @character_group.command(name="levelup", description="레벨을 올립니다")
    async def levelup(self, interaction: discord.Interaction):
        row = await db.get_character_by_owner(interaction.user.id, interaction.guild_id)
        if row is None:
            await interaction.response.send_message("캐릭터가 없어요.", ephemeral=True)
            return
        new_level = min(9, row["level"] + 1)
        new_max_hp = hp_for(row["class_key"], new_level)
        hp_gain = new_max_hp - row["max_hp"]
        new_current = row["current_hp"] + max(0, hp_gain)
        new_perks = row["perk_points"] + 1
        await db.update_level(row["id"], new_level, new_max_hp, new_current, new_perks)
        await interaction.response.send_message(
            f"⭐ {row['name']} 레벨 {new_level}! 체력 {new_current}/{new_max_hp} · 퍽 포인트 {new_perks}"
        )

    @character_group.command(name="gold", description="골드를 더하거나 뺍니다 (음수 가능)")
    async def gold(self, interaction: discord.Interaction, amount: int):
        row = await db.get_character_by_owner(interaction.user.id, interaction.guild_id)
        if row is None:
            await interaction.response.send_message("캐릭터가 없어요.", ephemeral=True)
            return
        new_gold = max(0, row["gold"] + amount)
        await db.update_gold(row["id"], new_gold)
        await interaction.response.send_message(f"💰 {row['name']}: {new_gold} 골드")

    @app_commands.command(name="party", description="이 서버의 파티 전체를 봅니다")
    async def party(self, interaction: discord.Interaction):
        rows = await db.get_party(interaction.guild_id)
        if not rows:
            await interaction.response.send_message("아직 파티원이 없어요.", ephemeral=True)
            return
        embed = discord.Embed(title="🎒 파티 현황", color=discord.Color.gold())
        for row in rows:
            class_display = CLASS_DATA[row["class_key"]]["display_name"]
            embed.add_field(
                name=f"{row['name']} (Lv.{row['level']} {class_display})",
                value=f"HP {row['current_hp']}/{row['max_hp']} · 골드 {row['gold']}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CharacterCog(bot))
