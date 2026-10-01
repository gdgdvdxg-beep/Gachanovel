"""واجهات ديسكورد: أزرار القتال واختيار الفريق."""
import discord
import config
import gamedata
from engine import needs_target

def _energy_tag(ab, unit) -> str:
    cost = ab.get("cost", unit.max_energy if ab.get("ult") else 0)
    if cost:
        return f" (-{cost}⚡)"
    if ab.get("energy"):
        return f" (+{ab['energy']}⚡)"
    return ""


COLORS = {None: discord.Color.blurple(), "win": discord.Color.green(), "lose": discord.Color.red()}


def battle_embed(session) -> discord.Embed:
    d = session.embed_data()
    e = discord.Embed(title=d["title"], description=d["description"], color=COLORS[d["result"]])
    e.add_field(name="🧑‍🤝‍🧑 فريقك", value=d["players"] or "—", inline=False)
    e.add_field(name="👹 الأعداء", value=d["enemies"] or "—", inline=False)
    e.set_footer(text=d["footer"])
    return e


class BattleView(discord.ui.View):
    """أزرار القدرات، ثم أزرار الأهداف عند الحاجة."""

    def __init__(self, session, owner_id: int, message=None):
        super().__init__(timeout=config.TURN_TIMEOUT)
        self.session, self.owner_id, self.message = session, owner_id, message
        self.mode, self.pending = "abilities", None
        self._build()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("هذه ليست معركتك.", ephemeral=True)
            return False
        return True

    def _build(self):
        self.clear_items()
        b = self.session.battle
        unit = b.current
        if self.session.finished or unit is None:
            return
        if self.mode == "abilities":
            for i, ab in enumerate(unit.abilities):
                label = ab["name"] + _energy_tag(ab, unit)
                btn = discord.ui.Button(
                    label=label[:80], disabled=not b.can_use(unit, i),
                    style=discord.ButtonStyle.danger if ab.get("ult") else discord.ButtonStyle.primary)
                btn.callback = self._ability_cb(i)
                self.add_item(btn)
        else:
            ab = unit.abilities[self.pending]
            style = discord.ButtonStyle.success if ab["target"] == "ally" else discord.ButtonStyle.secondary
            for t in b.valid_targets(unit, ab):
                btn = discord.ui.Button(label=t.name[:80], style=style)
                btn.callback = self._target_cb(t.uid)
                self.add_item(btn)
            back = discord.ui.Button(label="↩️ رجوع", style=discord.ButtonStyle.secondary)
            back.callback = self._back_cb
            self.add_item(back)

    def _ability_cb(self, idx):
        async def cb(interaction: discord.Interaction):
            unit = self.session.battle.current
            if unit is None or not self.session.battle.can_use(unit, idx):
                return await interaction.response.defer()
            if needs_target(unit.abilities[idx]):
                self.pending, self.mode = idx, "targets"
                self._build()
                return await interaction.response.edit_message(embed=battle_embed(self.session), view=self)
            await self._do(interaction, idx, None)
        return cb

    def _target_cb(self, uid):
        async def cb(interaction: discord.Interaction):
            await self._do(interaction, self.pending, uid)
        return cb

    async def _back_cb(self, interaction: discord.Interaction):
        self.mode, self.pending = "abilities", None
        self._build()
        await interaction.response.edit_message(embed=battle_embed(self.session), view=self)

    async def _do(self, interaction, idx, target_uid):
        self.session.act(idx, target_uid)
        self.mode, self.pending = "abilities", None
        self._build()
        if self.session.finished:
            self.stop()
            await interaction.response.edit_message(embed=battle_embed(self.session), view=None)
        else:
            await interaction.response.edit_message(embed=battle_embed(self.session), view=self)

    async def on_timeout(self):
        """انتهت المهلة: يلعب البوت دور اللاعب تلقائيًا ويكمل المعركة."""
        s = self.session
        if s.finished or self.message is None:
            return
        try:
            s.auto_turn()
            new_view = None if s.finished else BattleView(s, self.owner_id, self.message)
            await self.message.edit(embed=battle_embed(s), view=new_view)
        except discord.HTTPException:
            pass


class TeamView(discord.ui.View):
    def __init__(self, db, owner_id: int, owned_rows):
        super().__init__(timeout=120)
        self.db, self.owner_id = db, owner_id
        options = []
        for r in owned_rows[:25]:
            c = gamedata.CHARS[r["char_id"]]
            options.append(discord.SelectOption(
                label=c["name"], value=r["char_id"],
                description=f"{config.RARITY_AR[c['rarity']]} — مستوى {r['level']} — رتبة {r['rnk']}"))
        select = discord.ui.Select(placeholder=f"اختر حتى {config.TEAM_SIZE} شخصيات", min_values=1,
                                   max_values=min(config.TEAM_SIZE, len(options)), options=options)
        select.callback = self.on_select
        self.select = select
        self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("هذا ليس فريقك.", ephemeral=True)
            return False
        return True

    async def on_select(self, interaction: discord.Interaction):
        ids = list(self.select.values)
        self.db.set_team(self.owner_id, ids)
        names = "، ".join(gamedata.CHARS[i]["name"] for i in ids)
        await interaction.response.edit_message(content=f"✅ تم تحديث فريقك: {names}", view=None)
        self.stop()
