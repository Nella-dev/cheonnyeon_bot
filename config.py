"""천년 길드 디스코드 봇 - 기본 설정"""
from __future__ import annotations

import os


def _int(value, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- 기본 정보
TOKEN = (os.getenv("MTU1NzUxNTI0NTIzOTUzMzY0OA.GsZxDB.fajGr-ut26xxakRQ6aIhoCa5Zp2XXOlARe0g3w") or "").strip()
GUILD_ID = _int(os.getenv("GUILD_ID"), 0)
DB_PATH = os.getenv("DB_PATH", "data/eclipse.db")

GAME_NAME = "이클립스: 더어웨이크닝"
GUILD_NAME = "천년"
FOOTER = f"{GUILD_NAME} · {GAME_NAME}"

# ---------------------------------------------------------------- 색상
COLOR_MAIN = 0x7B5CFF
COLOR_OK = 0x3BA55D
COLOR_WARN = 0xFAA61A
COLOR_ERR = 0xED4245
COLOR_INFO = 0x5865F2
COLOR_GOLD = 0xF1C40F

# ---------------------------------------------------------------- 카테고리 / 채널
CATEGORY_NOTICE = "📢 천년 공지"
CATEGORY_OPS = "🛡️ 천년 운영"
CATEGORY_MEMBER = "📋 천년 길드원"

CH_NOTICE = "📢-공지사항"
CH_WELCOME = "👋-환영합니다"
CH_VOTE = "🗳️-길드-투표"
CH_LOOT = "💰-분배-기록"
CH_MANAGE = "🛡️-길드-관리"
CH_ROSTER = "📋-길드원-목록"
CH_LOG = "🧾-봇-로그"

# 채널 이름을 바꿔도 설정값(settings 테이블)이 우선입니다.
DEFAULT_CHANNELS = {
    "notice_channel": CH_NOTICE,
    "vote_channel": CH_VOTE,
    "loot_channel": CH_LOOT,
    "manage_channel": CH_MANAGE,
    "roster_channel": CH_ROSTER,
    "log_channel": CH_LOG,
}

# ---------------------------------------------------------------- 길드 규칙
DEFAULT_RANKS = [
    "길드마스터",
    "부길드마스터",
    "정예길드원",
    "길드원",
]

# 직업은 자유 입력입니다. 자주 쓰는 값은 여기서 자동완성 후보로 쓰입니다.
DEFAULT_JOBS = [
    "파이터",
    "레인저",
    "소서리스",
    "어쌔신",
]

VOTE_MAX_OPTIONS = 10
ROSTER_PAGE_SIZE = 10
