import discord
from discord import app_commands
from discord.ext import commands

from core.decks import AttackModifierDeck


class CardsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # (guild_id, character_name_lower) -> AttackModifierDeck
        self.decks: dict[tuple[int, str], AttackModifierDeck] = {}

    def get_deck(self, guild_id: int, name: str) -> AttackModifierDeck:
        key = (guild_id, name.lower())
        if key not in self.decks:
            self.decks[key] = AttackModifierDeck(owner_name=name)
        return self.decks[key]

    cards_group = app_commands.Group(name="cards", description="공격 수정 카드 덱 (Attack Modifier Deck)")

    @cards_group.command(name="draw", description="공격 수정 카드를 한 장 뽑습니다")
    async def draw(self, interaction: discord.Interaction, character: str):
        deck = self.get_deck(interaction.guild_id, character)
        card, reshuffled = deck.draw()

        color = discord.Color.light_grey()
        if "CRIT" in card:
            color = discord.Color.gold()
        elif "MISS" in card:
            color = discord.Color.dark_red()
        elif "BLESS" in card:
            color = discord.Color.blue()
        elif "CURSE" in card:
            color = discord.Color.dark_purple()

        embed = discord.Embed(title=f"🎴 {character} — {card}", color=color)
        embed.add_field(name="남은 카드 (드로우 더미)", value=str(len(deck.draw_pile)))
        if reshuffled:
            embed.add_field(name="⚠️", value="크리티컬/미스로 덱이 리셔플되었습니다", inline=False)
        await interaction.response.send_message(embed=embed)

    @cards_group.command(name="add-bless", description="덱에 축복(Bless) 카드를 추가합니다")
    async def add_bless(self, interaction: discord.Interaction, character: str):
        deck = self.get_deck(interaction.guild_id, character)
        deck.add_bless()
        await interaction.response.send_message(f"✨ {character} 덱에 축복 카드 추가됨")

    @cards_group.command(name="add-curse", description="덱에 저주(Curse) 카드를 추가합니다")
    async def add_curse(self, interaction: discord.Interaction, character: str):
        deck = self.get_deck(interaction.guild_id, character)
        deck.add_curse()
        await interaction.response.send_message(f"💀 {character} 덱에 저주 카드 추가됨")

    @cards_group.command(name="reset", description="덱을 기본 20장으로 리셋(재구성)합니다")
    async def reset(self, interaction: discord.Interaction, character: str):
        deck = self.get_deck(interaction.guild_id, character)
        deck.reshuffle_full()
        await interaction.response.send_message(f"🔄 {character} 덱 리셋 완료 ({len(deck.draw_pile)}장)")

    @cards_group.command(name="status", description="덱 상태(남은 카드/버림더미)를 봅니다")
    async def status(self, interaction: discord.Interaction, character: str):
        deck = self.get_deck(interaction.guild_id, character)
        embed = discord.Embed(title=f"🎴 {character}의 덱 상태", color=discord.Color.blurple())
        embed.add_field(name="드로우 더미", value=str(len(deck.draw_pile)))
        embed.add_field(name="버림 더미", value=str(len(deck.discard_pile)))
        embed.add_field(name="영구 제거된 카드", value=", ".join(deck.removed) or "-", inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CardsCog(bot))
