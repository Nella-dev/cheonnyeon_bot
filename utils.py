"""공용 유틸리티 - 임베드, 권한 체크, 채널 찾기, 페이지네이션"""
from __future__ import annotations

import datetime

import discord
from discord import app_commands

import config
import database


# ---------------------------------------------------------------- 시간
def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def parse_dt(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime.datetime):
        dt = value
    else:
        text = str(value).replace("Z", "+00:00")
        try:
            dt = datetime.datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def fmt_dt(value) -> str:
    dt = parse_dt(value)
    if dt is None:
        return "-"
    ts = int(dt.timestamp())
    return f"<t:{ts}:f> (<t:{ts}:R>)"


def fmt_date(value) -> str:
    dt = parse_dt(value)
    if dt is None:
        return "-"
    return f"<t:{int(dt.timestamp())}:D>"


# ---------------------------------------------------------------- 임베드
def build_embed(title=None, description=None, color=None) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=config.COLOR_MAIN if color is None else color,
    )
    embed.timestamp = utcnow()
    embed.set_footer(text=config.FOOTER)
    return embed


def ok_embed(title, description=None) -> discord.Embed:
    return build_embed(f"✅ {title}", description, config.COLOR_OK)


def err_embed(title, description=None) -> discord.Embed:
    return build_embed(f"❌ {title}", description, config.COLOR_ERR)


def warn_embed(title, description=None) -> discord.Embed:
    return build_embed(f"⚠️ {title}", description, config.COLOR_WARN)


def info_embed(title, description=None) -> discord.Embed:
    return build_embed(f"ℹ️ {title}", description, config.COLOR_INFO)


def gold_embed(title, description=None) -> discord.Embed:
    return build_embed(title, description, config.COLOR_GOLD)


# ---------------------------------------------------------------- 권한
def staff_only():
    """서버 관리 권한 또는 '운영진 역할'을 가진 사람만 통과시킵니다."""

    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage("서버 안에서만 사용할 수 있는 명령어입니다.")
        perms = interaction.user.guild_permissions
        if perms.administrator or perms.manage_guild:
            return True
        role_id = await database.get_setting(interaction.guild.id, "staff_role")
        try:
            role_id = int(role_id) if role_id else 0
        except (TypeError, ValueError):
            role_id = 0
        if role_id and any(r.id == role_id for r in getattr(interaction.user, "roles", [])):
            return True
        raise app_commands.CheckFailure(
            "천년 길드 운영진만 사용할 수 있는 명령어입니다. (서버 관리 권한 또는 운영진 역할 필요)"
        )

    return app_commands.check(predicate)


async def is_staff(member: discord.Member) -> bool:
    if member.guild is None:
        return False
    perms = member.guild_permissions
    if perms.administrator or perms.manage_guild:
        return True
    role_id = await database.get_setting(member.guild.id, "staff_role")
    try:
        role_id = int(role_id) if role_id else 0
    except (TypeError, ValueError):
        role_id = 0
    return bool(role_id) and any(r.id == role_id for r in member.roles)


# ---------------------------------------------------------------- 채널
async def resolve_channel(guild: discord.Guild, key: str):
    """settings 값 → 없으면 이름으로 찾기 → 없으면 None"""
    cid = await database.get_setting(guild.id, key)
    if cid:
        try:
            channel = guild.get_channel(int(cid))
        except (TypeError, ValueError):
            channel = None
        if channel is not None:
            return channel
    name = config.DEFAULT_CHANNELS.get(key)
    if not name:
        return None
    return discord.utils.get(guild.text_channels, name=name)


async def log_action(bot: discord.Client, guild: discord.Guild, embed: discord.Embed) -> None:
    channel = await resolve_channel(guild, "log_channel")
    if channel is None:
        return
    try:
        await channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass


def user_label(user) -> str:
    return f"{user.display_name} (`{user.id}`)"


# ---------------------------------------------------------------- 페이지네이션
class Pager(discord.ui.View):
    def __init__(self, pages, author_id: int, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.index = 0
        self.author_id = author_id
        self._sync()

    def _sync(self) -> None:
        self.prev.disabled = self.index <= 0
        self.next.disabled = self.index >= len(self.pages) - 1
        self.counter.label = f"{self.index + 1} / {len(self.pages)}"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "이 버튼은 명령어를 실행한 사람만 사용할 수 있습니다.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="◀ 이전", style=discord.ButtonStyle.secondary, row=0)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = max(0, self.index - 1)
        self._sync()
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)

    @discord.ui.button(label="1 / 1", style=discord.ButtonStyle.secondary, disabled=True, row=0)
    async def counter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

    @discord.ui.button(label="다음 ▶", style=discord.ButtonStyle.secondary, row=0)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = min(len(self.pages) - 1, self.index + 1)
        self._sync()
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)


def chunk(items, size: int):
    return [items[i:i + size] for i in range(0, len(items), size)]
