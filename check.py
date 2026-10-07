#!/usr/bin/env python3
"""실행 전 환경 점검 스크립트 (파이썬 3.10+ 필요)"""
import os
import sys

REQUIRED = 10


def main() -> int:
    print("=" * 58)
    print(" 천년 길드 봇 - 실행 전 점검")
    print("=" * 58)

    ok = True

    v = sys.version_info
    print(f"[1] 파이썬 버전: {v.major}.{v.minor}.{v.micro}", end="  ")
    if v.major == 3 and v.minor >= REQUIRED:
        print("✅")
    else:
        print(f"❌ (3.{REQUIRED} 이상 필요)")
        ok = False

    print("[2] 필수 패키지 확인", end="  ")
    missing = []
    for name, module in [("discord.py", "discord"), ("aiosqlite", "aiosqlite"), ("python-dotenv", "dotenv")]:
        try:
            __import__(module)
        except ImportError:
            missing.append(name)
    if missing:
        print(f"❌ 누락: {', '.join(missing)}")
        print("    → pip install -r requirements.txt")
        ok = False
    else:
        print("✅")

    print("[3] .env 파일 확인", end="  ")
    if not os.path.exists(".env"):
        print("❌ 없음")
        print("    → .env.example 을 .env 로 복사한 뒤 토큰을 채워 주세요.")
        ok = False
    else:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        token = (os.getenv("DISCORD_TOKEN") or "").strip()
        if not token or "여기에" in token:
            print("❌ 토큰이 비어 있습니다")
            ok = False
        else:
            print(f"✅ (토큰 길이 {len(token)})")

    print("[4] 봇 파일 확인", end="  ")
    needed = ["bot.py", "config.py", "database.py", "utils.py", "cogs"]
    lack = [n for n in needed if not os.path.exists(n)]
    print("❌ 누락: " + ", ".join(lack) if lack else "✅")
    if lack:
        ok = False

    print("-" * 58)
    print(" 결과:", "모두 정상입니다. `python bot.py` 로 실행하세요." if ok else "위 문제를 먼저 해결해 주세요.")
    print("=" * 58)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
