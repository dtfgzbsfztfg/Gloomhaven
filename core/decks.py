"""
카드 덱 관련 로직.

AttackModifierDeck: 글룸헤이븐 표준 공격 수정 카드 구성(20장)을 그대로 따른다.
    +0 x6, +1 x5, +2 x1, -1 x5, -2 x1, x2(크리티컬) x1, Null(빗나감) x1
    - 크리티컬/Null이 나오면 즉시 리셔플(재구성) 하는 것이 룰.
    - 축복(Bless)/저주(Curse) 카드를 얹으면 해당 카드는 뽑힌 후 덱에서 영구 제거된다.

MonsterAbilityDeck: 실제 게임의 몬스터별 고유 능력카드 텍스트를 그대로 옮기지 않고,
    "이니셔티브 + 행동 패턴"을 일반화한 제네릭 덱으로 구현했다 (저작권상 원문 카드 텍스트는 포함하지 않음).
    실제 카드북을 보며 진행하되, 이 봇은 이니셔티브 난수 생성 + 간단한 AI 타겟팅만 보조한다.
"""
import random
from dataclasses import dataclass, field


@dataclass
class AttackModifierDeck:
    owner_name: str
    draw_pile: list[str] = field(default_factory=list)
    discard_pile: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)  # 영구 제거된 축복/저주 등

    BASE_DECK = (
        ["+0"] * 6
        + ["+1"] * 5
        + ["+2"] * 1
        + ["-1"] * 5
        + ["-2"] * 1
        + ["x2 (CRIT)"] * 1
        + ["NULL (MISS)"] * 1
    )

    def __post_init__(self):
        if not self.draw_pile and not self.discard_pile:
            self.reshuffle_full()

    def reshuffle_full(self):
        """기본 20장 + 아직 안 뽑힌 bless/curse 를 모아 새로 섞는다."""
        pool = list(self.BASE_DECK) + [c for c in self.discard_pile if c in ("BLESS (x2)", "CURSE (NULL)")]
        pool += [c for c in self.draw_pile if c in ("BLESS (x2)", "CURSE (NULL)")]
        random.shuffle(pool)
        self.draw_pile = pool
        self.discard_pile = []

    def add_bless(self):
        self.draw_pile.append("BLESS (x2)")
        random.shuffle(self.draw_pile)

    def add_curse(self):
        self.draw_pile.append("CURSE (NULL)")
        random.shuffle(self.draw_pile)

    def draw(self) -> tuple[str, bool]:
        """카드 1장을 뽑는다. (카드이름, 셔플_발생여부) 반환."""
        if not self.draw_pile:
            self.draw_pile = self.discard_pile
            self.discard_pile = []
            random.shuffle(self.draw_pile)

        card = self.draw_pile.pop()
        reshuffled = False

        if card in ("BLESS (x2)", "CURSE (NULL)"):
            self.removed.append(card)  # 축복/저주는 뽑히면 영구 제거
        elif card in ("x2 (CRIT)", "NULL (MISS)"):
            self.discard_pile.append(card)
            # 룰: 크리티컬/Null이 나오면 즉시 리셔플
            self.draw_pile.extend(self.discard_pile)
            self.discard_pile = []
            random.shuffle(self.draw_pile)
            reshuffled = True
        else:
            self.discard_pile.append(card)

        return card, reshuffled

    def remaining_counts(self) -> dict:
        from collections import Counter
        return dict(Counter(self.draw_pile))


# --- 몬스터 능력(제네릭) ---

GENERIC_ACTIONS = [
    "이동 + 공격",
    "공격 + 이동",
    "강화된 공격 (+1)",
    "범위 공격",
    "이동 2배",
    "방어 태세 (실드 +1)",
    "재생",
    "이동만",
    "공격만 (고정 위치)",
    "그룹 전체 강화 부여",
]


@dataclass
class MonsterAbilityDeck:
    """몬스터 '종류' 하나당 하나씩 배정 (예: Bandit Guard 전체가 공유)."""
    monster_type: str
    draw_pile: list[int] = field(default_factory=lambda: list(range(1, 100, 2)))  # 홀수 카드 1~99 (표준 몬스터 덱 구성 일반화)
    discard_pile: list[int] = field(default_factory=list)

    def __post_init__(self):
        random.shuffle(self.draw_pile)

    def draw_round_card(self) -> tuple[int, str]:
        if not self.draw_pile:
            self.draw_pile = self.discard_pile
            self.discard_pile = []
            random.shuffle(self.draw_pile)
        card_num = self.draw_pile.pop()
        self.discard_pile.append(card_num)
        action = GENERIC_ACTIONS[card_num % len(GENERIC_ACTIONS)]
        return card_num, action


def suggest_target(attacker_hp_map: dict, prefer_lowest_hp: bool = True) -> str | None:
    """아주 단순한 타겟 선택 보조: HP가 가장 낮은 대상을 추천.
    attacker_hp_map: {name: current_hp} (죽지 않은 대상만 넘길 것)
    """
    if not attacker_hp_map:
        return None
    if prefer_lowest_hp:
        return min(attacker_hp_map, key=attacker_hp_map.get)
    return random.choice(list(attacker_hp_map.keys()))
