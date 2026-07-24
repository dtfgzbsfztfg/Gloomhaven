import json
import os
import discord
from discord import app_commands
from discord.ext import commands

with open("data/monsters.json", encoding="utf-8") as f:
    MONSTER_DATA = json.load(f)

from core.models import CombatEntity, EntityKind
from core.decks import MonsterAbilityDeck, suggest_target
from core.gridmap import GridMap

MONSTER_CHOICES = [
    app_commands.Choice(name=v["display_name"], value=k) for k, v in MONSTER_DATA.items()
]

TMP_MAP_DIR = "tmp_maps"
os.makedirs(TMP_MAP_DIR, exist_ok=True)


class CombatSession:
    """채널 하나당 진행 중인 전투 하나. 봇 재시작 시 초기화됨."""

    def __init__(self):
        self.entities: list[CombatEntity] = []
        self.round: int = 1
        self.turn_index: int = 0
        self.active: bool = False
        self.monster_decks: dict[str, MonsterAbilityDeck] = {}  # 몬스터 종류(표시이름) -> 덱
        self.map: GridMap | None = None

    def get_monster_deck(self, monster_type: str) -> MonsterAbilityDeck:
        if monster_type not in self.monster_decks:
            self.monster_decks[monster_type] = MonsterAbilityDeck(monster_type=monster_type)
        return self.monster_decks[monster_type]

    def sorted_order(self):
        # 이니셔티브 낮은 순서로 행동 (글룸헤이븐 룰)
        return sorted(self.entities, key=lambda e: e.initiative)

    def current(self):
        order = [e for e in self.sorted_order() if e.is_alive()]
        if not order:
            return None
        self.turn_index %= len(order)
        return order[self.turn_index]

    def advance(self):
        order = [e for e in self.sorted_order() if e.is_alive()]
        if not order:
            return None
        self.turn_index += 1
        if self.turn_index >= len(order):
            self.turn_index = 0
            self.round += 1
        return self.current()

    def find(self, name: str) -> CombatEntity | None:
        name_l = name.lower()
        matches = [e for e in self.entities if e.name.lower() == name_l]
        if not matches:
            matches = [e for e in self.entities if name_l in e.name.lower()]
        return matches[0] if matches else None


class CombatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions: dict[int, CombatSession] = {}  # channel_id -> session

    def get_session(self, channel_id: int) -> CombatSession:
        if channel_id not in self.sessions:
            self.sessions[channel_id] = CombatSession()
        return self.sessions[channel_id]

    combat_group = app_commands.Group(name="combat", description="전투 진행 관리")

    @combat_group.command(name="start", description="새 전투를 시작합니다 (기존 전투는 초기화)")
    async def start(self, interaction: discord.Interaction):
        self.sessions[interaction.channel_id] = CombatSession()
        session = self.sessions[interaction.channel_id]
        session.active = True
        await interaction.response.send_message(
            "⚔️ 전투 시작! `/combat add-character` 와 `/combat add-monster` 로 참가자를 등록하세요."
        )

    @combat_group.command(name="add-character", description="캐릭터를 전투에 등록합니다")
    async def add_character(
        self, interaction: discord.Interaction, name: str, initiative: int, hp: int
    ):
        session = self.get_session(interaction.channel_id)
        entity = CombatEntity(
            name=name,
            kind=EntityKind.CHARACTER,
            initiative=initiative,
            max_hp=hp,
            current_hp=hp,
            owner_id=interaction.user.id,
        )
        session.entities.append(entity)
        await interaction.response.send_message(f"➕ {name} (이니셔티브 {initiative}) 등록됨")

    @combat_group.command(name="add-monster", description="몬스터를 전투에 등록합니다")
    @app_commands.choices(monster=MONSTER_CHOICES)
    async def add_monster(
        self,
        interaction: discord.Interaction,
        monster: app_commands.Choice[str],
        level: int,
        initiative: int,
        elite: bool = False,
        number: int = 1,
    ):
        session = self.get_session(interaction.channel_id)
        data = MONSTER_DATA[monster.value]
        stat_block = data["elite" if elite else "normal"]
        idx = min(max(level, 1), 9) - 1
        hp = stat_block["hp_per_level"][idx]

        added_names = []
        for i in range(number):
            suffix = f" {i+1}" if number > 1 else ""
            tag = "엘리트" if elite else "일반"
            name = f"{data['display_name']}{suffix} ({tag} Lv{level})"
            entity = CombatEntity(
                name=name,
                kind=EntityKind.MONSTER,
                initiative=initiative,
                max_hp=hp,
                current_hp=hp,
                is_elite=elite,
            )
            session.entities.append(entity)
            added_names.append(name)

        await interaction.response.send_message(
            f"➕ 등록: {', '.join(added_names)} (HP {hp}, 이니셔티브 {initiative})"
        )

    @combat_group.command(name="order", description="현재 턴 순서를 봅니다")
    async def order(self, interaction: discord.Interaction):
        session = self.get_session(interaction.channel_id)
        if not session.entities:
            await interaction.response.send_message("등록된 참가자가 없어요.", ephemeral=True)
            return

        current = session.current()
        embed = discord.Embed(
            title=f"🔄 라운드 {session.round}",
            color=discord.Color.purple(),
        )
        lines = []
        for e in session.sorted_order():
            marker = "▶️ " if e is current else "　"
            dead = " 💀" if not e.is_alive() else ""
            lines.append(
                f"{marker}**[{e.initiative}]** {e.name} — HP {e.current_hp}/{e.max_hp}{dead}"
                f"\n　　상태: {e.status_summary()}"
            )
        embed.description = "\n".join(lines)
        await interaction.response.send_message(embed=embed)

    @combat_group.command(name="next", description="다음 턴으로 진행합니다")
    async def next_turn(self, interaction: discord.Interaction):
        session = self.get_session(interaction.channel_id)
        nxt = session.advance()
        if nxt is None:
            await interaction.response.send_message("전투 참가자가 없어요.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"➡️ 라운드 {session.round} · **{nxt.name}**의 턴 (HP {nxt.current_hp}/{nxt.max_hp}, 상태: {nxt.status_summary()})"
        )

    @combat_group.command(name="damage", description="대상에게 피해를 줍니다")
    async def damage(self, interaction: discord.Interaction, target: str, amount: int):
        session = self.get_session(interaction.channel_id)
        entity = session.find(target)
        if entity is None:
            await interaction.response.send_message(f"'{target}' 을(를) 찾을 수 없어요.", ephemeral=True)
            return
        dealt = entity.damage(amount)
        msg = f"💥 {entity.name}: -{dealt} → HP {entity.current_hp}/{entity.max_hp}"
        if not entity.is_alive():
            msg += " 💀 쓰러짐"
        await interaction.response.send_message(msg)

    @combat_group.command(name="heal", description="대상을 치유합니다")
    async def heal(self, interaction: discord.Interaction, target: str, amount: int):
        session = self.get_session(interaction.channel_id)
        entity = session.find(target)
        if entity is None:
            await interaction.response.send_message(f"'{target}' 을(를) 찾을 수 없어요.", ephemeral=True)
            return
        healed = entity.heal(amount)
        await interaction.response.send_message(
            f"❤️ {entity.name}: +{healed} → HP {entity.current_hp}/{entity.max_hp}"
        )

    @combat_group.command(name="status-add", description="상태이상을 부여합니다 (예: poison, strengthen)")
    async def status_add(self, interaction: discord.Interaction, target: str, status: str):
        session = self.get_session(interaction.channel_id)
        entity = session.find(target)
        if entity is None:
            await interaction.response.send_message(f"'{target}' 을(를) 찾을 수 없어요.", ephemeral=True)
            return
        entity.add_status(status.lower())
        await interaction.response.send_message(f"🔖 {entity.name} ← {status} 부여됨")

    @combat_group.command(name="status-remove", description="상태이상을 제거합니다")
    async def status_remove(self, interaction: discord.Interaction, target: str, status: str):
        session = self.get_session(interaction.channel_id)
        entity = session.find(target)
        if entity is None:
            await interaction.response.send_message(f"'{target}' 을(를) 찾을 수 없어요.", ephemeral=True)
            return
        removed = entity.remove_status(status.lower())
        msg = f"✅ {entity.name} ← {status} 제거됨" if removed else f"{entity.name}에게 {status} 상태가 없어요."
        await interaction.response.send_message(msg)

    @combat_group.command(name="remove", description="참가자를 전투에서 제거합니다")
    async def remove(self, interaction: discord.Interaction, target: str):
        session = self.get_session(interaction.channel_id)
        entity = session.find(target)
        if entity is None:
            await interaction.response.send_message(f"'{target}' 을(를) 찾을 수 없어요.", ephemeral=True)
            return
        session.entities.remove(entity)
        await interaction.response.send_message(f"🗑️ {entity.name} 제거됨")

    @combat_group.command(name="end", description="전투를 종료합니다")
    async def end(self, interaction: discord.Interaction):
        self.sessions[interaction.channel_id] = CombatSession()
        await interaction.response.send_message("🏁 전투 종료. 세션이 초기화되었습니다.")

    # --- 몬스터 능력카드 AI 보조 ---
    # 참고: 실제 카드북의 고유 텍스트는 저작권상 그대로 옮기지 않고,
    # 이니셔티브 난수 + 일반화된 행동패턴만 뽑아준다. 실제 효과는 카드북을 직접 참고하세요.
    @combat_group.command(name="monster-turn", description="몬스터 종류의 능력카드를 뽑아 이니셔티브/행동을 확인합니다")
    async def monster_turn(self, interaction: discord.Interaction, monster_type: str):
        session = self.get_session(interaction.channel_id)
        deck = session.get_monster_deck(monster_type)
        card_num, action = deck.draw_round_card()

        alive_chars = {
            e.name: e.current_hp
            for e in session.entities
            if e.kind == EntityKind.CHARACTER and e.is_alive()
        }
        target = suggest_target(alive_chars)

        embed = discord.Embed(title=f"👹 {monster_type} 능력카드", color=discord.Color.dark_red())
        embed.add_field(name="이니셔티브", value=str(card_num))
        embed.add_field(name="행동 패턴 (일반화됨)", value=action)
        embed.add_field(
            name="추천 타겟 (HP 최저)", value=target or "대상 없음", inline=False
        )
        embed.set_footer(text="정확한 효과 수치는 실제 몬스터 능력카드북을 참고하세요.")
        await interaction.response.send_message(embed=embed)

    # --- 그리드 맵 ---
    @combat_group.command(name="map-init", description="사각 그리드 맵을 생성합니다")
    async def map_init(self, interaction: discord.Interaction, cols: int, rows: int):
        session = self.get_session(interaction.channel_id)
        cols = max(2, min(20, cols))
        rows = max(2, min(20, rows))
        session.map = GridMap(cols=cols, rows=rows)
        await interaction.response.send_message(f"🗺️ {cols}x{rows} 맵 생성됨. `/combat map-place` 로 참가자를 배치하세요.")

    @combat_group.command(name="map-place", description="참가자를 맵 좌표에 배치합니다")
    async def map_place(self, interaction: discord.Interaction, target: str, x: int, y: int):
        session = self.get_session(interaction.channel_id)
        if session.map is None:
            await interaction.response.send_message("먼저 `/combat map-init` 으로 맵을 만들어주세요.", ephemeral=True)
            return
        entity = session.find(target)
        kind = "character"
        if entity is not None:
            kind = "monster_elite" if entity.is_elite else ("monster" if entity.kind == EntityKind.MONSTER else "character")
        session.map.place(target, x, y, kind=kind)
        await self._send_map(interaction, session, f"📍 {target} → ({x},{y})")

    @combat_group.command(name="map-move", description="참가자를 새 좌표로 이동시킵니다")
    async def map_move(self, interaction: discord.Interaction, target: str, x: int, y: int):
        await self.map_place.callback(self, interaction, target, x, y)

    @combat_group.command(name="map-obstacle", description="해당 좌표의 장애물/벽을 토글합니다")
    async def map_obstacle(self, interaction: discord.Interaction, x: int, y: int):
        session = self.get_session(interaction.channel_id)
        if session.map is None:
            await interaction.response.send_message("먼저 `/combat map-init` 으로 맵을 만들어주세요.", ephemeral=True)
            return
        added = session.map.toggle_obstacle(x, y)
        msg = f"🧱 ({x},{y}) 장애물 {'추가' if added else '제거'}됨"
        await self._send_map(interaction, session, msg)

    @combat_group.command(name="map-show", description="현재 맵 이미지를 보여줍니다")
    async def map_show(self, interaction: discord.Interaction):
        session = self.get_session(interaction.channel_id)
        if session.map is None:
            await interaction.response.send_message("먼저 `/combat map-init` 으로 맵을 만들어주세요.", ephemeral=True)
            return
        await self._send_map(interaction, session, "🗺️ 현재 맵")

    async def _send_map(self, interaction: discord.Interaction, session: "CombatSession", message: str):
        path = os.path.join(TMP_MAP_DIR, f"map_{interaction.channel_id}.png")
        session.map.render(path)
        await interaction.response.send_message(content=message, file=discord.File(path))


async def setup(bot: commands.Bot):
    await bot.add_cog(CombatCog(bot))
