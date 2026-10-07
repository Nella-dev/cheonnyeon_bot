"""천년 길드 봇 - 실행 진입점"""
from __future__ import annotations

import logging
import sys

import discord
from discord import app_commands
from discord.ext import commands

import config
import database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("eclipse")

COGS = [
    "cogs.setup",
    "cogs.announcement",
    "cogs.vote",
    "cogs.distribution",
    "cogs.management",
    "cogs.roster",
]


class EclipseBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self) -> None:
        await database.connect()
        log.info("데이터베이스 준비 완료 → %s", config.DB_PATH)

        for ext in COGS:
            try:
                await self.load_extension(ext)
                log.info("모듈 로드 완료: %s", ext)
            except Exception:
                log.exception("모듈 로드 실패: %s", ext)

        try:
            if config.GUILD_ID:
                guild = discord.Object(id=config.GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                log.info("서버(%s) 전용으로 명령어 %d개 동기화 완료", config.GUILD_ID, len(synced))
            else:
                synced = await self.tree.sync()
                log.info("전역 명령어 %d개 동기화 완료 (반영까지 최대 1시간)", len(synced))
        except Exception:
            log.exception("명령어 동기화 실패")

    async def on_ready(self) -> None:
        log.info("로그인 완료: %s (%s)", self.user, getattr(self.user, "id", "?"))
        log.info("참여 중인 서버: %d개", len(self.guilds))
        try:
            await self.change_presence(
                status=discord.Status.online,
                activity=discord.Game(name=f"{config.GAME_NAME} | /도움말"),
            )
        except Exception:
            log.exception("상태 메시지 설정 실패")

    async def close(self) -> None:
        await database.close()
        await super().close()


bot = EclipseBot()


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    import utils

    if isinstance(error, app_commands.CommandInvokeError):
        original = error.original
        if isinstance(original, app_commands.AppCommandError):
            error = original
        else:
            log.error("명령어 실행 중 오류 발생", exc_info=original)
            error = None

    if error is None:
        embed = utils.err_embed("오류가 발생했습니다", "잠시 후 다시 시도해 주세요. 계속되면 관리자에게 알려주세요.")
    elif isinstance(error, app_commands.MissingPermissions):
        embed = utils.err_embed("권한이 부족합니다", "이 명령어를 사용할 권한이 없습니다.")
    elif isinstance(error, app_commands.BotMissingPermissions):
        missing = ", ".join(error.missing_permissions)
        embed = utils.err_embed("봇 권한이 부족합니다", f"봇에게 다음 권한을 부여해 주세요: `{missing}`")
    elif isinstance(error, app_commands.CheckFailure):
        embed = utils.err_embed("사용할 수 없습니다", str(error) or "이 명령어를 사용할 권한이 없습니다.")
    elif isinstance(error, app_commands.CommandOnCooldown):
        embed = utils.err_embed("잠시만 기다려 주세요", f"{error.retry_after:.1f}초 후에 다시 시도해 주세요.")
    else:
        log.error("처리되지 않은 오류: %r", error)
        embed = utils.err_embed("오류가 발생했습니다", "잠시 후 다시 시도해 주세요.")

    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception:
        log.exception("오류 안내 메시지 전송 실패")


def main() -> None:
    if not config.TOKEN:
        print("=" * 60)
        print("DISCORD_TOKEN 이 설정되지 않았습니다.")
        print(".env.example 파일을 .env 로 복사한 뒤 봇 토큰을 채워 주세요.")
        print("=" * 60)
        sys.exit(1)
    bot.run(config.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
