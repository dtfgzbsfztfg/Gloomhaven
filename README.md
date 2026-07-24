# 글룸헤이븐 디스코드 봇 (v2)

캐릭터 관리, 전투(이니셔티브/HP/상태이상), 캠페인·시나리오 트래킹,
공격 수정 카드 덱, 몬스터 능력카드 AI 보조, 그리드 맵 이미지까지 담은 종합 버전입니다.

## 설치

```bash
cd gloomhaven-bot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # DISCORD_TOKEN 값 채워넣기
python bot.py
```

디스코드 개발자 포털(https://discord.com/developers/applications)에서 봇을 만들고,
**OAuth2 URL Generator**에서 `bot`, `applications.commands` 스코프와
`Send Messages`, `Embed Links` 권한을 체크해 서버에 초대하세요.
슬래시 명령어가 바로 안 보이면 디스코드 클라이언트를 재시작하거나 몇 분 기다려주세요.

## 명령어

### 캐릭터
| 명령어 | 설명 |
|---|---|
| `/character create <이름> <직업>` | 캐릭터 생성 |
| `/character sheet` | 내 캐릭터 시트 보기 |
| `/character heal <양>` / `/character damage <양>` | 체력 증감 |
| `/character levelup` | 레벨업 (체력/퍽 포인트 자동 반영) |
| `/character gold <양>` | 골드 증감 (음수 가능) |
| `/party` | 서버 파티 전체 현황 |

### 전투
| 명령어 | 설명 |
|---|---|
| `/combat start` | 새 전투 시작 (채널 단위) |
| `/combat add-character <이름> <이니셔티브> <hp>` | 캐릭터 참전 등록 |
| `/combat add-monster <몬스터> <레벨> <이니셔티브> [엘리트] [마릿수]` | 몬스터 등록 |
| `/combat order` | 현재 턴 순서 + 상태 표시 |
| `/combat next` | 다음 턴으로 진행 (라운드 자동 증가) |
| `/combat damage <대상> <양>` / `/combat heal <대상> <양>` | 전투 중 HP 조정 |
| `/combat status-add <대상> <상태이상>` / `status-remove` | poison, strengthen 등 상태이상 부여/제거 |
| `/combat remove <대상>` | 참가자 제거 |
| `/combat end` | 전투 종료 |

### 캠페인
| 명령어 | 설명 |
|---|---|
| `/campaign status` | 진행 중 시나리오, 번영도, 평판, 클리어 수 요약 |
| `/campaign scenario-start <번호> <이름>` | 시나리오 시작 |
| `/campaign scenario-complete` | 현재 시나리오 클리어 처리 |
| `/campaign scenario-list` | 클리어한 시나리오 전체 목록 |
| `/campaign prosperity <증감>` / `/campaign reputation <증감>` | 번영도/평판 조정 (음수 가능) |
| `/campaign achievement-add <내용>` | 도시/거리 이벤트 결과나 업적 기록 |
| `/campaign achievement-list` | 기록된 업적/이벤트 목록 |

### 공격 수정 카드 덱 (Attack Modifier Deck)
표준 20장 구성(+0×6, +1×5, +2×1, -1×5, -2×1, 크리티컬×1, 미스×1)을 그대로 반영했고,
크리티컬/미스가 나오면 게임 룰대로 자동 리셔플됩니다.

| 명령어 | 설명 |
|---|---|
| `/cards draw <캐릭터>` | 카드 한 장 드로우 |
| `/cards add-bless <캐릭터>` / `/cards add-curse <캐릭터>` | 축복/저주 카드 추가 (뽑히면 영구 제거) |
| `/cards reset <캐릭터>` | 덱을 기본 20장으로 재구성 |
| `/cards status <캐릭터>` | 드로우/버림 더미 상태 확인 |

### 몬스터 능력카드 AI 보조
> 실제 카드북의 고유 텍스트·수치는 저작권상 그대로 옮기지 않았습니다. 이 기능은 **이니셔티브 난수 생성 + 일반화된 행동 패턴 + 최저 HP 타겟 추천**만 제공하니, 실제 효과는 보유하신 몬스터 능력카드북을 참고해 진행해주세요.

| 명령어 | 설명 |
|---|---|
| `/combat monster-turn <몬스터종류>` | 해당 몬스터 종류의 능력카드를 뽑아 이니셔티브/행동/추천 타겟 표시 |

### 그리드 맵
글룸헤이븐 실제 타일은 육각형이지만, 봇 운용 편의를 위해 사각 그리드로 단순화했습니다.

| 명령어 | 설명 |
|---|---|
| `/combat map-init <가로> <세로>` | 맵 생성 |
| `/combat map-place <대상> <x> <y>` | 참가자 배치 (전투 참가자면 색상 자동 구분) |
| `/combat map-move <대상> <x> <y>` | 참가자 이동 (place와 동일) |
| `/combat map-obstacle <x> <y>` | 해당 칸 장애물/벽 토글 |
| `/combat map-show` | 현재 맵 이미지 전송 |

## Railway 배포

1. **GitHub에 푸시**: 이 프로젝트를 GitHub 레포로 올리세요 (`.gitignore`에 `.env`, `venv/`, `gloomhaven.db`가 이미 제외되어 있어요). Railway는 GitHub 레포에서 바로 빌드/배포합니다.
2. **Railway 프로젝트 생성**: [railway.com](https://railway.com) → New Project → Deploy from GitHub repo → 이 레포 선택.
   Nixpacks가 `requirements.txt`를 보고 Python 환경을 자동 인식하고, `railway.json`에 지정된 시작 명령(`python bot.py`)으로 실행됩니다.
3. **환경변수 설정**: Railway 대시보드의 서비스 → **Variables** 탭에서 추가하세요 (로컬 `.env` 파일은 자동으로 올라가지 않으니 반드시 여기서 등록해야 해요).
   - `DISCORD_TOKEN` = 봇 토큰
   - `DB_PATH` = `/data/gloomhaven.db` (아래 볼륨 설정과 짝을 이룹니다)
4. **영구 볼륨 추가** (캐릭터/캠페인 데이터가 재배포 후에도 남도록): 서비스 → **Volumes** → Add Volume → 마운트 경로를 `/data`로 지정. Railway는 서비스당 볼륨 1개만 지원하니 DB 파일 하나만 여기 저장하면 충분해요.
5. **HTTP 포트 관련**: 이 봇은 웹서버가 아니라 디스코드에 계속 연결만 유지하는 워커 프로세스예요. Railway가 "포트가 열려있지 않다"는 경고를 띄워도 정상 동작하는 데는 문제없어요 (별도 Public Domain 생성 안 해도 됩니다).
6. **배포 확인**: Deployments 탭에서 로그를 보고 `✅ Logged in as ...` 메시지가 뜨면 정상 작동 중인 거예요.

> 참고: `tmp_maps/`(그리드 맵 PNG 임시 저장)는 휘발성 파일시스템에 저장돼도 무방해요 — 매번 새로 렌더링하니까 재배포로 지워져도 문제없습니다. 오직 `gloomhaven.db`만 볼륨에 저장하면 됩니다.

## 구조



```
gloomhaven-bot/
  bot.py                # 진입점, 확장 로딩, 슬래시 명령 동기화
  Procfile               # Railway/Heroku 시작 명령
  railway.json             # Nixpacks 빌드 + 시작 명령 명시
  core/
    models.py            # Character(영구), CombatEntity/StatusEffect(전투 중 임시)
    database.py           # SQLite 저장소 (DB_PATH 환경변수로 볼륨 경로 지정 가능)
    decks.py                # AttackModifierDeck, MonsterAbilityDeck(제네릭), 타겟 추천
    gridmap.py                # GridMap 상태 + PIL 렌더링
  cogs/
    character.py            # /character, /party
    combat.py                 # /combat (전투, 몬스터 AI 보조, 맵)
    campaign.py                # /campaign
    cards.py                     # /cards
  data/
    classes.json               # 직업별 레벨당 체력/손패 크기
    monsters.json                # 몬스터 레벨별 체력 (일반/엘리트)
  tmp_maps/                        # 맵 이미지 렌더링 임시 저장 (자동 생성, git에는 안 올려도 됨)
```

## 알려진 제한사항

- **전투/맵/카드덱 상태는 메모리에만 저장**됩니다 — 봇 재시작 시 초기화돼요. 캐릭터 정보와 캠페인 진행(시나리오/번영도/평판/업적)은 SQLite에 영속화됩니다.
- **몬스터 능력카드는 원문 텍스트가 아닌 일반화된 버전**입니다 (저작권 때문에 실제 카드북 문구를 그대로 옮기지 않았어요). 이니셔티브 난수와 대략적인 행동 패턴, 타겟 추천만 제공하니 정확한 효과는 실물 카드북을 참고해주세요.
- **그리드 맵은 사각형으로 단순화**했습니다. 실제 게임은 육각 타일이라 정확한 사거리/이동경로 계산과는 차이가 있을 수 있어요 — 대략적인 배치/거리 파악용으로 써주세요.
- 직업/몬스터 수치는 대표적인 값 몇 개만 넣어뒀어요. 실제 매뉴얼과 다를 수 있으니 `data/*.json` 파일만 고치면 코드 변경 없이 정확한 수치로 맞출 수 있습니다.
- 아이템 상점/인벤토리, 클래스별 고유 카드(수동으로 카드 텍스트를 직접 관리하는 부분)는 아직 없어요.

## 다음 단계 아이디어

1. **전투/맵 상태 영속화** — 봇 재시작에도 진행 중인 전투가 유지되도록 SQLite/JSON에 저장
2. **아이템 상점 & 인벤토리** — 도시 이벤트에서 구매한 아이템 관리
3. **개인화된 클래스 카드 목록** — 실제 카드 이름/효과를 직접 입력해두고 손패 관리 (저작권 있는 원문은 사용자가 직접 입력하는 방식으로)
4. **육각 그리드로 업그레이드** — 더 정확한 사거리/이동 계산

필요하신 부분부터 말씀해주시면 이어서 만들게요.
