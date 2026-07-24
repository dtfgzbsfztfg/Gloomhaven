"""
글룸헤이븐 봇의 핵심 데이터 모델.
Character(영구 저장), CombatEntity/StatusEffect(전투 중 임시 상태)로 분리했다.
"""
from dataclasses import dataclass, field
from enum import Enum


class EntityKind(str, Enum):
    CHARACTER = "character"
    MONSTER = "monster"


# 상태이상 종류 - (지속형 / 즉시효과) 구분
PERSISTENT_CONDITIONS = {
    "poison", "wound", "immobilize", "disarm", "muddle",
    "strengthen", "bless", "curse", "invisible", "regenerate"
}


@dataclass
class StatusEffect:
    name: str  # 예: "poison", "strengthen"
    stacks: int = 1  # wound/poison 등은 중첩되지 않지만, 확장성 위해 카운트 필드 유지

    def __str__(self):
        return self.name if self.stacks <= 1 else f"{self.name}x{self.stacks}"


@dataclass
class Character:
    owner_id: int  # 디스코드 유저 ID
    guild_id: int
    name: str
    class_key: str  # data/classes.json 의 키
    level: int = 1
    max_hp: int = 10
    current_hp: int = 10
    exp: int = 0
    gold: int = 15
    perk_points: int = 0
    notes: str = ""
    id: int | None = None  # DB PK, 신규 생성 시 None

    def is_alive(self) -> bool:
        return self.current_hp > 0

    def heal(self, amount: int):
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    def damage(self, amount: int):
        self.current_hp = max(0, self.current_hp - amount)


@dataclass
class CombatEntity:
    """전투 세션 동안만 존재하는 참가자 (캐릭터든 몬스터든 공통 처리)."""
    name: str
    kind: EntityKind
    initiative: int
    max_hp: int
    current_hp: int
    statuses: dict[str, StatusEffect] = field(default_factory=dict)
    is_elite: bool = False
    owner_id: int | None = None  # 캐릭터인 경우 디스코드 유저 ID

    def add_status(self, status_name: str):
        if status_name in self.statuses:
            self.statuses[status_name].stacks += 1
        else:
            self.statuses[status_name] = StatusEffect(status_name)

    def remove_status(self, status_name: str) -> bool:
        return self.statuses.pop(status_name, None) is not None

    def damage(self, amount: int) -> int:
        """실제로 감소한 체력을 반환 (연출용)."""
        before = self.current_hp
        self.current_hp = max(0, self.current_hp - amount)
        return before - self.current_hp

    def heal(self, amount: int) -> int:
        before = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp - before

    def is_alive(self) -> bool:
        return self.current_hp > 0

    def status_summary(self) -> str:
        if not self.statuses:
            return "-"
        return ", ".join(str(s) for s in self.statuses.values())
