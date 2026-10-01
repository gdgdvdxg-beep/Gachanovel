"""أوامر السلاش."""
import random
import time
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

import config
import gacha
import gamedata
from session import BattleSession
from ui import BattleView, TeamView, battle_embed


def today_str() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=config.TZ_OFFSET_HOURS)).strftime("%Y-%m-%d")


def fmt_wait(seconds: int) -> str:
    m = max(1, seconds // 60)
    return f"{m // 60} ساعة و{m % 60} دقيقة" if m >= 60 else f"{m} دقيقة"


class GachaCog(commands.Cog):
    def __init__(self, bot, db):
        self.bot, self.db = bot, db

    # ---------- أدوات ----------
    async def _player(self, interaction):
        p = self.db.get_player(interaction.user.id)
        if p is None:
            await interaction.response.send_message("ابدأ أولًا بالأمر `/ابدأ`.", ephemeral=True)
        return p

    def _enemy_level(self, p) -> int:
        return 1 + p["boss_wins"] * config.ENEMY_LEVEL_PER_BOSS_WIN

    def _team_units(self, uid):
        units = []
        for i, cid in enumerate(self.db.get_team(uid)):
            row = self.db.get_char(uid, cid)
            units.append(gamedata.build_player(cid, row["level"], row["rnk"], f"p{i}"))
        return units

    async def _launch(self, interaction, session):
        view = BattleView(session, interaction.user.id)
        await interaction.response.send_message(embed=battle_embed(session), view=view)
        view.message = await interaction.original_response()

    async def _ready(self, interaction):
        """يعيد (اللاعب, الفريق) أو None بعد إرسال رسالة الخطأ."""
        p = await self._player(interaction)
        if p is None:
            return None
        team = self._team_units(interaction.user.id)
        if not team:
            await interaction.response.send_message("ليس لديك فريق! اسحب شخصيات بالأمر `/سحب` أولًا.", ephemeral=True)
            return None
        return p, team

    # ---------- الأوامر ----------
    @app_commands.command(name="ابدأ", description="ابدأ رحلتك واحصل على مواد السحب الأولى")
    async def start(self, interaction: discord.Interaction):
        if self.db.get_player(interaction.user.id):
            return await interaction.response.send_message("أنت مسجّل مسبقًا. جرّب `/سحب`.", ephemeral=True)
        self.db.create_player(interaction.user.id, config.START_MATERIALS)
        await interaction.response.send_message(
            f"🎉 أهلًا بك! حصلت على **{config.START_MATERIALS}** 🎟️ مواد سحب.\n"
            f"كل سحبة تكلف {config.DRAW_COST}. ابدأ بالأمر `/سحب`.")

    @app_commands.command(name="رصيدي", description="مواد السحب وتقدمك")
    async def profile(self, interaction: discord.Interaction):
        p = await self._player(interaction)
        if p is None:
            return
        rates = gacha.effective_rates(p["boss_wins"])
        e = discord.Embed(title="📋 ملفك", color=discord.Color.gold())
        e.add_field(name="🎟️ مواد السحب", value=str(p["materials"]))
        e.add_field(name="👑 هزائم الزعيم", value=str(p["boss_wins"]))
        e.add_field(name="👹 مستوى الأعداء", value=str(self._enemy_level(p)))
        e.add_field(name="🎰 نسبة الأسطوري الحالية", value=f"{rates['legendary']:.2f}%")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="سحب", description="اسحب شخصيات بمواد السحب")
    @app_commands.describe(count="عدد السحبات")
    @app_commands.choices(count=[app_commands.Choice(name="سحبة واحدة", value=1),
                                 app_commands.Choice(name="10 سحبات", value=10)])
    async def draw(self, interaction: discord.Interaction, count: app_commands.Choice[int]):
        p = await self._player(interaction)
        if p is None:
            return
        n, uid = count.value, interaction.user.id
        cost = n * config.DRAW_COST
        if not self.db.spend_materials(uid, cost):
            return await interaction.response.send_message(
                f"تحتاج **{cost}** 🎟️ وعندك {p['materials']} فقط.", ephemeral=True)
        lines, refund = [], 0
        for _ in range(n):
            cid = gacha.roll(random.Random(), p["boss_wins"])
            c = gamedata.CHARS[cid]
            res = self.db.add_char_copy(uid, cid)
            icon = config.RARITY_ICON[c["rarity"]]
            tag = {"new": "🆕 جديدة", "rank": "⬆️ ارتفعت الرتبة", "max": f"♻️ نسخة زائدة (+{config.OVERFLOW_REFUND}🎟️)"}[res]
            if res == "max":
                refund += config.OVERFLOW_REFUND
            lines.append(f"{icon} **{c['name']}** ({config.RARITY_AR[c['rarity']]}) — {tag}")
        if refund:
            self.db.add_materials(uid, refund)
        e = discord.Embed(title=f"🎰 نتيجة السحب ×{n}", description="\n".join(lines), color=discord.Color.purple())
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="شخصياتي", description="اعرض الشخصيات التي تملكها")
    async def my_chars(self, interaction: discord.Interaction):
        if await self._player(interaction) is None:
            return
        uid = interaction.user.id
        rows = self.db.get_chars(uid)
        team = self.db.get_team(uid)
        if not rows:
            return await interaction.response.send_message("لا تملك شخصيات بعد. جرّب `/سحب`.", ephemeral=True)
        lines = []
        for r in rows:
            c = gamedata.CHARS[r["char_id"]]
            mark = "⭐" if r["char_id"] in team else "▫️"
            lines.append(f"{mark} {config.RARITY_ICON[c['rarity']]} **{c['name']}** — مستوى {r['level']}/{config.MAX_LEVEL}"
                         f" — رتبة {r['rnk']}/{config.MAX_RANK} — XP {r['xp']}/{config.xp_needed(r['level'])}")
        await interaction.response.send_message(embed=discord.Embed(
            title="🧑‍🤝‍🧑 شخصياتك (⭐ = في الفريق)", description="\n".join(lines), color=discord.Color.blue()))

    @app_commands.command(name="فريقي", description="اعرض فريقك أو غيّره")
    async def team(self, interaction: discord.Interaction):
        if await self._player(interaction) is None:
            return
        uid = interaction.user.id
        rows = self.db.get_chars(uid)
        if not rows:
            return await interaction.response.send_message("لا تملك شخصيات بعد. جرّب `/سحب`.", ephemeral=True)
        cur = "، ".join(gamedata.CHARS[c]["name"] for c in self.db.get_team(uid)) or "—"
        await interaction.response.send_message(f"👥 فريقك الحالي: {cur}\nاختر فريقًا جديدًا من القائمة:",
                                                view=TeamView(self.db, uid, rows), ephemeral=True)

    @app_commands.command(name="شخصية", description="تفاصيل شخصية وقدراتها")
    @app_commands.describe(character="اسم الشخصية")
    async def char_info(self, interaction: discord.Interaction, character: str):
        c = gamedata.CHARS.get(character)
        if c is None:
            return await interaction.response.send_message("لم أجد هذه الشخصية.", ephemeral=True)
        e = discord.Embed(title=f"{config.RARITY_ICON[c['rarity']]} {c['name']} — {c['world']}",
                          description=f"{config.RARITY_AR[c['rarity']]} — {c['role']}", color=discord.Color.gold())
        from engine import TYPE_ICONS, TYPE_NAMES
        e.add_field(name="الإحصائيات (المستوى 1)", inline=False, value=(
            f"❤️ {c['hp']}  ⚔️ {c['atk']}  🛡️ {c['def']}  ⚡ {c['max_energy']}\n"
            f"الضرر: {TYPE_ICONS[c['dmg_type']]} {TYPE_NAMES[c['dmg_type']]} — "
            f"المقاومة: {TYPE_ICONS[c['resistance']]} {TYPE_NAMES[c['resistance']]}"))
        if c.get("passive"):
            e.add_field(name=f"✨ سلبية: {c['passive']['name']}", value=c["passive"]["desc"], inline=False)
        for i, ab in enumerate(c["abilities"], 1):
            cost = ab.get("cost", c["max_energy"] if ab.get("ult") else 0)
            tag = f"-{cost}⚡" if cost else (f"+{ab['energy']}⚡" if ab.get("energy") else "")
            e.add_field(name=f"{i}. {ab['name']}  {tag}".strip(), value=ab["desc"], inline=False)
        await interaction.response.send_message(embed=e)

    @char_info.autocomplete("character")
    async def char_ac(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=c["name"], value=cid)
                for cid, c in gamedata.CHARS.items() if current in c["name"]][:25]

    # ---------- المعارك ----------
    @app_commands.command(name="معركة", description="معركة عادية (تتجدد كل 30 دقيقة)")
    async def battle(self, interaction: discord.Interaction):
        ready = await self._ready(interaction)
        if ready is None:
            return
        p, team = ready
        now = int(time.time())
        slot = now // config.NORMAL_SLOT
        if p["last_normal_slot"] == slot:
            wait = (slot + 1) * config.NORMAL_SLOT - now
            return await interaction.response.send_message(
                f"⏳ خضت معركة هذه الفترة. المعركة التالية بعد {fmt_wait(wait)}.", ephemeral=True)
        self.db.set_slot(interaction.user.id, "last_normal_slot", slot)
        rng = random.Random(slot)                        # أعداء الفترة نفسها لكل اللاعبين
        ids = [rng.choice(gamedata.enemies_by_tier("normal")) for _ in range(3)]
        enemies = gamedata.build_enemies(ids, self._enemy_level(p))
        await self._launch(interaction, BattleSession(
            self.db, interaction.user.id, "normal", team, [enemies], p["boss_wins"]))

    @app_commands.command(name="مغامرة", description="سلسلة تحديات تنتهي بزعيم صغير (تتجدد كل 3 ساعات)")
    async def adventure(self, interaction: discord.Interaction):
        ready = await self._ready(interaction)
        if ready is None:
            return
        p, team = ready
        now = int(time.time())
        slot = now // config.ADVENTURE_SLOT
        if p["last_adv_slot"] == slot:
            wait = (slot + 1) * config.ADVENTURE_SLOT - now
            return await interaction.response.send_message(
                f"⏳ خضت مغامرة هذه الفترة. المغامرة التالية بعد {fmt_wait(wait)}.", ephemeral=True)
        self.db.set_slot(interaction.user.id, "last_adv_slot", slot)
        rng = random.Random(slot + 7)
        normal = gamedata.enemies_by_tier("normal")
        lvl = self._enemy_level(p) + 1
        waves = [gamedata.build_enemies([rng.choice(normal) for _ in range(2)], lvl),
                 gamedata.build_enemies([rng.choice(normal) for _ in range(3)], lvl),
                 gamedata.build_enemies([rng.choice(gamedata.enemies_by_tier("miniboss")), rng.choice(normal)], lvl + 1)]
        await self._launch(interaction, BattleSession(
            self.db, interaction.user.id, "adventure", team, waves, p["boss_wins"]))

    @app_commands.command(name="الزعيم", description="الزعيم اليومي — مرة واحدة كل يوم")
    async def boss(self, interaction: discord.Interaction):
        ready = await self._ready(interaction)
        if ready is None:
            return
        p, team = ready
        if p["last_boss_day"] == today_str():
            return await interaction.response.send_message("👑 واجهت الزعيم اليوم. عد غدًا!", ephemeral=True)
        self.db.set_slot(interaction.user.id, "last_boss_day", today_str())
        boss_id = gamedata.enemies_by_tier("boss")[0]
        enemies = gamedata.build_enemies([boss_id], self._enemy_level(p) + 2)
        await self._launch(interaction, BattleSession(
            self.db, interaction.user.id, "boss", team, [enemies], p["boss_wins"]))
