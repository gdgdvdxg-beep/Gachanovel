"""محرك القتال — منطق خالص بدون أي اعتماد على ديسكورد، ليسهل اختباره."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
import config

TYPE_NAMES = {"physical": "جسدي", "fire": "ناري", "mystic": "غامض", "dark": "مظلم"}
TYPE_ICONS = {"physical": "⚔️", "fire": "🔥", "mystic": "🔮", "dark": "🌑"}


@dataclass
class Effect:
    kind: str            # shield, def_mod, atk_mod, ignore_def, def_type_mod, dmg_taken_reduce,
                         # phys_immune, block_ult, block_buff, dot
    id: str
    source: str
    applied_round: int
    expires_round: int
    value: float = 0.0
    amount: float = 0.0
    types: tuple = ()
    dmg_type: str = ""

    @property
    def is_buff(self) -> bool:
        if self.kind in ("shield", "ignore_def", "def_type_mod", "dmg_taken_reduce", "phys_immune"):
            return True
        if self.kind in ("def_mod", "atk_mod"):
            return self.value > 0
        return False

    @property
    def icon(self) -> str:
        if self.kind == "def_mod":
            return "🔰" if self.value > 0 else "🔻"
        if self.kind == "atk_mod":
            return "💪" if self.value > 0 else "📉"
        return {"shield": "🛡️", "ignore_def": "🎯", "def_type_mod": "🌀", "dmg_taken_reduce": "🧱",
                "phys_immune": "✨", "block_ult": "⛔", "block_buff": "🚫", "dot": "☠️",
                "sleep": "💤", "confuse": "😵", "seal": "🔒"}.get(self.kind, "•")


@dataclass
class Unit:
    uid: str
    name: str
    side: str                      # "player" أو "enemy"
    max_hp: int
    atk: float
    defense: float
    dmg_type: str
    resistance: str
    max_energy: int = 0
    abilities: list = field(default_factory=list)
    rarity: str = "common"
    power: float = 1.0             # مضاعف قوة المهارات (من الرتب)
    ai: str = "random"             # random أو simple
    char_id: str = ""
    hp: float = -1
    energy: int = 0
    effects: list = field(default_factory=list)
    ult_boost: float = 0.0
    delayed_next: bool = False
    passive: str = ""

    def __post_init__(self):
        if self.hp < 0:
            self.hp = self.max_hp

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def dur(self) -> int:
        return config.RARITY_DURATION.get(self.rarity, 1)

    def reset(self):
        self.effects = []
        self.ult_boost = 0.0
        self.delayed_next = False
        self.energy = min(config.START_ENERGY, self.max_energy)   # كل الشخصيات تبدأ بـ 50 طاقة


def needs_target(ab: dict) -> bool:
    return ab["target"] in ("enemy", "enemy_plus", "ally")


def effective_atk(u: Unit) -> float:
    return u.atk * max(0.0, 1 + sum(e.value for e in u.effects if e.kind == "atk_mod"))


def effective_def(t: Unit, dtype: str, ignore: float = 0.0) -> float:
    mod = 0.0
    for e in t.effects:
        if e.kind == "def_mod":
            mod += e.value
        elif e.kind == "def_type_mod" and dtype in e.types:
            mod += e.value
    if dtype == t.resistance:
        mod += 1.0                                   # المقاومة: +100% دفاع لهذه الضربة فقط
    return t.defense * max(0.0, 1 + mod) * (1 - ignore)


def calc_damage(att: Unit, tgt: Unit, mult: float, dtype: str, ignore: float = 0.0):
    """الضرر = الهجوم × 100 ÷ (100 + الدفاع). يعيد (الضرر, هل طابقت المقاومة)."""
    raw = effective_atk(att) * mult * att.power
    dmg = raw * 100 / (100 + effective_def(tgt, dtype, ignore))
    red = sum(e.value for e in tgt.effects
              if e.kind == "dmg_taken_reduce" and dtype in (e.types or (e.dmg_type,)))
    dmg *= max(0.1, 1 - red)
    return max(1, round(dmg)), dtype == tgt.resistance


class Battle:
    def __init__(self, players: list[Unit], enemies: list[Unit], rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.players, self.enemies = players, enemies
        self.units = players + enemies
        for u in self.units:
            u.reset()
        self.round = 0
        self.queue: list[Unit] = []
        self.current: Unit | None = None
        self.log: list[str] = []
        self.winner: str | None = None
        self.advance()

    # ---------- أدوات ----------
    @property
    def finished(self) -> bool:
        return self.winner is not None

    def say(self, text: str):
        self.log.append(text)

    def foes(self, u: Unit):
        return [x for x in self.units if x.side != u.side and x.alive]

    def allies(self, u: Unit):
        return [x for x in self.units if x.side == u.side and x.alive]

    def unit_by_id(self, uid: str):
        return next((u for u in self.units if u.uid == uid), None)

    def can_use(self, u: Unit, idx: int) -> bool:
        ab = u.abilities[idx]
        if ab.get("kind", "basic") != "basic" and any(e.kind == "seal" for e in u.effects):
            return False                                  # مختوم: الهجوم الأساسي فقط
        if ab.get("ult"):
            cost = ab.get("cost", u.max_energy)
            return u.energy >= cost > 0 and not any(e.kind == "block_ult" for e in u.effects)
        return u.energy >= ab.get("cost", 0)              # القدرات الخاصة تستهلك طاقة

    def valid_targets(self, u: Unit, ab: dict):
        if ab["target"] in ("enemy", "enemy_plus"):
            return self.foes(u)
        if ab["target"] == "ally":
            return self.allies(u)
        return []

    # ---------- سير المعركة ----------
    def _check_end(self) -> bool:
        if not any(u.alive for u in self.players):
            self.winner = "enemy"
        elif not any(u.alive for u in self.enemies):
            self.winner = "player"
        return self.winner is not None

    def _new_round(self):
        for u in self.units:                          # انتهاء التأثيرات التي انقضت مدتها
            u.effects = [e for e in u.effects if e.expires_round > self.round]
        self.round += 1
        if self.round > config.MAX_ROUNDS:
            self.winner = "enemy"
            self.say("⌛ طال القتال أكثر من اللازم... انتهت المعركة بالخسارة.")
            return
        alive = [u for u in self.units if u.alive]
        self.rng.shuffle(alive)
        delayed = [u for u in alive if u.delayed_next]
        for u in delayed:
            u.delayed_next = False
        order = [u for u in alive if u not in delayed] + delayed
        if self.round == 1:                           # اللاعب يبدأ دائمًا أول دور
            first = self.rng.choice([u for u in order if u.side == "player"])
            order.remove(first)
            order.insert(0, first)
        self.queue = order
        self.say(f"━━ **الجولة {self.round}** ━━")

    def _start_turn(self, u: Unit):
        for e in [e for e in u.effects if e.kind == "dot" and e.applied_round < self.round]:
            dmg = max(1, round(e.amount * 100 / (100 + effective_def(u, e.dmg_type))))
            self.say(f"☠️ **{u.name}** يتلقى ضررًا مؤجلًا")
            self.hit(None, u, dmg, e.dmg_type)
            if not u.alive:
                return

    def advance(self):
        """يشغّل الأدوار حتى ينتظر دور لاعب أو تنتهي المعركة."""
        while self.winner is None:
            if self._check_end():
                return
            if not self.queue:
                self._new_round()
                if self.winner:
                    return
            u = self.queue.pop(0)
            if not u.alive:
                continue
            self.current = u
            self._start_turn(u)
            if not u.alive or self._check_end():
                self.current = None
                continue
            sleeping = [e for e in u.effects if e.kind == "sleep"]
            if sleeping:
                u.effects.remove(sleeping[0])
                self.say(f"💤 **{u.name}** نائم ويفوّت دوره")
                self.current = None
                continue
            confused = [e for e in u.effects if e.kind == "confuse"]
            if confused:
                u.effects.remove(confused[0])
                self._confused_attack(u)
                self.current = None
                continue
            if u.side == "player":
                return
            self._enemy_act(u)
            self.current = None

    def act(self, idx: int, target_uid: str | None = None):
        u = self.current
        if u is None or u.side != "player" or self.finished:
            raise ValueError("ليس دور لاعب الآن")
        if not self.can_use(u, idx):
            raise ValueError("لا يمكن استخدام هذه القدرة الآن")
        self.use_ability(u, idx, self.unit_by_id(target_uid) if target_uid else None)
        self.current = None
        self.advance()

    def auto_act(self):
        """قدرة تلقائية للاعب (عند انتهاء المهلة): النهائية إن أمكن، وإلا عشوائي."""
        u = self.current
        usable = [i for i in range(len(u.abilities)) if self.can_use(u, i)]
        ults = [i for i in usable if u.abilities[i].get("ult")]
        idx = ults[0] if ults else self.rng.choice(usable)
        self.act(idx, None)

    def _confused_attack(self, u: Unit):
        mates = [x for x in self.allies(u) if x is not u]
        if not mates:
            self.say(f"😵 **{u.name}** مرتبك ولم يجد من يهاجمه")
            return
        victim = self.rng.choice(mates)
        self.say(f"😵 **{u.name}** مرتبك ويهاجم حليفه!")
        self.use_ability(u, 0, None, forced=[victim])

    def _enemy_act(self, u: Unit):
        usable = [i for i in range(len(u.abilities)) if self.can_use(u, i)]
        if not usable:
            return
        ults = [i for i in usable if u.abilities[i].get("ult")]
        idx = ults[0] if (u.ai == "simple" and ults) else self.rng.choice(usable)
        ab = u.abilities[idx]
        chosen = None
        cands = self.valid_targets(u, ab)
        if cands:
            chosen = min(cands, key=lambda x: x.hp / x.max_hp) if u.ai == "simple" else self.rng.choice(cands)
        self.use_ability(u, idx, chosen)

    # ---------- القدرات ----------
    def resolve_targets(self, c: Unit, ab: dict, chosen):
        t, foes, allies = ab["target"], self.foes(c), self.allies(c)
        if t == "self":
            return [c]
        if t == "all_enemies":
            return foes
        if t == "all_allies":
            return allies
        if t in ("enemy", "enemy_plus"):
            first = chosen if chosen in foes else self.rng.choice(foes)
            res = [first]
            if t == "enemy_plus":
                others = [f for f in foes if f is not first]
                if others:
                    res.append(self.rng.choice(others))
            return res
        return [chosen if chosen in allies else c]    # ally

    def use_ability(self, c: Unit, idx: int, chosen=None, forced=None):
        ab = c.abilities[idx]
        boost = 0.0
        cost = ab.get("cost", c.max_energy if ab.get("ult") else 0)
        if cost:
            c.energy = max(0, c.energy - cost)
        if ab.get("ult"):
            boost, c.ult_boost = c.ult_boost, 0.0
        if ab.get("energy") and c.max_energy:
            c.energy = min(c.max_energy, c.energy + ab["energy"])
        self.say(f"{'🌟' if ab.get('ult') else '▶️'} **{c.name}** يستخدم **{ab['name']}**")
        targets = forced if forced is not None else self.resolve_targets(c, ab, chosen)
        for t in targets:
            for spec in ab["effects"]:
                if spec["type"] in ("ult_boost", "revive") or spec.get("on"):
                    continue
                if not t.alive:
                    break
                self._apply(c, t, spec, ab, boost)
        for spec in ab["effects"]:                    # تأثيرات موجهة لمجموعة محددة (on)
            grp = spec.get("on")
            if grp in ("enemies", "allies"):
                for t in (self.foes(c) if grp == "enemies" else self.allies(c)):
                    self._apply(c, t, spec, ab, boost)
        for spec in ab["effects"]:                    # تأثيرات على المستخدم مرة واحدة
            if spec["type"] == "ult_boost":
                c.ult_boost = spec["pct"]
                self.say(f"  ↳ ✨ **{c.name}** تزداد قوة نهائيته القادمة {int(spec['pct']*100)}%")
            elif spec["type"] == "revive":
                dead = [u for u in self.units if u.side == c.side and not u.alive]
                if dead:
                    r = dead[0]
                    r.hp = max(1, round(r.max_hp * spec["pct"]))
                    r.effects = []
                    self.say(f"  ↳ 🔆 **{r.name}** عاد إلى الحياة ({int(r.hp)}/{r.max_hp})")

    def add_effect(self, t: Unit, eff: Effect) -> bool:
        if eff.is_buff and any(e.kind == "block_buff" for e in t.effects):
            self.say(f"  ↳ 🚫 **{t.name}** لا يستطيع تلقي التعزيزات")
            return False
        t.effects = [e for e in t.effects if not (e.id == eff.id and e.source == eff.source and e.kind == eff.kind)]
        t.effects.append(eff)
        return True

    def _apply(self, c: Unit, t: Unit, spec: dict, ab: dict, boost: float):
        k = spec["type"]
        d = c.dur if spec.get("dur", "R") == "R" else int(spec["dur"])
        mk = lambda kind, **kw: Effect(kind=kind, id=spec.get("id", ab["name"]), source=c.uid,
                                       applied_round=self.round, expires_round=self.round + d, **kw)
        dtype = spec.get("dmg_type", c.dmg_type)
        if k == "damage":
            ign = sum(e.value for e in c.effects if e.kind == "ignore_def") + spec.get("ignore", 0.0)
            if c.passive == "ai_insight" and t.hp < 0.5 * t.max_hp:
                ign += 0.30                          # سلبية ليلين: تجاهل 30% من دفاع الأعداء دون 50% صحة
            ign = min(0.9, ign)
            dmg, res = calc_damage(c, t, spec["mult"] * (1 + boost), dtype, ign)
            self.hit(c, t, dmg, dtype, res)
            if spec.get("splash"):                   # تتفرع إلى عدو آخر بنسبة من الضرر
                others = [f for f in self.foes(c) if f is not t]
                if others:
                    o = self.rng.choice(others)
                    d2, r2 = calc_damage(c, o, spec["mult"] * spec["splash"] * (1 + boost), dtype, ign)
                    self.say(f"  ↳ ⚡ تتفرع إلى **{o.name}**")
                    self.hit(c, o, d2, dtype, r2)
        elif k == "damage_bonus_if_dot":
            if any(e.kind == "dot" and e.id == spec["dot_id"] for e in t.effects):
                dmg = max(1, round(effective_atk(c) * spec["mult"] * c.power))
                self.hit(c, t, dmg, dtype, False, "ضرر إضافي يتجاهل الدفاع")
        elif k == "shield":
            amt = round(spec["pct_max_hp"] * c.max_hp * c.power)
            if self.add_effect(t, mk("shield", amount=amt)):
                self.say(f"  ↳ 🛡️ **{t.name}** يحصل على درع ({amt})")
        elif k == "heal":
            amt = round(spec["pct_max_hp"] * c.max_hp * c.power)
            t.hp = min(t.max_hp, t.hp + amt)
            self.say(f"  ↳ 💚 **{t.name}** يُشفى {amt} ({int(t.hp)}/{t.max_hp})")
        elif k in ("def_mod", "atk_mod"):
            if self.add_effect(t, mk(k, value=spec["pct"])):
                word = "يرتفع" if spec["pct"] > 0 else "ينخفض"
                what = "دفاع" if k == "def_mod" else "هجوم"
                self.say(f"  ↳ {mk(k, value=spec['pct']).icon} {what} **{t.name}** {word} {abs(int(spec['pct']*100))}%")
        elif k == "def_type_mod":
            if self.add_effect(t, mk(k, value=spec["pct"], types=tuple(spec["types"]))):
                self.say(f"  ↳ 🌀 **{t.name}** دفاع إضافي {int(spec['pct']*100)}% ضد "
                         + "، ".join(TYPE_NAMES[x] for x in spec["types"]))
        elif k == "ignore_def":
            if self.add_effect(t, mk(k, value=spec["pct"])):
                self.say(f"  ↳ 🎯 هجمات **{t.name}** تتجاهل {int(spec['pct']*100)}% من الدفاع")
        elif k == "dmg_taken_reduce":
            types = tuple(spec.get("dmg_types") or [spec["dmg_type"]])
            if self.add_effect(t, mk(k, value=spec["pct"], dmg_type=types[0], types=types)):
                self.say(f"  ↳ 🧱 **{t.name}** يتلقى ضررًا {'، '.join(TYPE_NAMES[x] for x in types)} أقل بنسبة {int(spec['pct']*100)}%")
        elif k == "heal_atk":
            amt = max(1, round(effective_atk(c) * spec["mult"] * c.power))
            t.hp = min(t.max_hp, t.hp + amt)
            self.say(f"  ↳ 💚 **{t.name}** يُشفى {amt} ({int(t.hp)}/{t.max_hp})")
        elif k == "cleanse":
            if any(not e.is_buff for e in t.effects):
                t.effects = [e for e in t.effects if e.is_buff]
                self.say(f"  ↳ ✨ تمت إزالة التأثيرات السلبية عن **{t.name}**")
        elif k == "cleanse_control":
            if any(e.kind in ("sleep", "confuse") for e in t.effects):
                t.effects = [e for e in t.effects if e.kind not in ("sleep", "confuse")]
                self.say(f"  ↳ ✨ تحرر **{t.name}** من التحكم")
        elif k in ("sleep", "confuse", "seal"):
            if k != "seal" and self._immune(t):
                self.say(f"  ↳ 🛡️ **{t.name}** محصّن ضد هذا التأثير")
            elif self.add_effect(t, mk(k)):
                msg = {"sleep": "💤 نام", "confuse": "😵 ارتبك", "seal": "🔒 قدراته الخاصة ونهايته مختومة"}[k]
                self.say(f"  ↳ **{t.name}** {msg}")
        elif k == "phys_immune":
            if self.add_effect(t, mk(k)):
                self.say(f"  ↳ ✨ **{t.name}** محمي من أول هجوم جسدي")
        elif k == "block_ult":
            if self.add_effect(t, mk(k)):
                self.say(f"  ↳ ⛔ **{t.name}** لا يستطيع استخدام النهائية")
        elif k == "block_buff":
            if self.add_effect(t, mk(k)):
                self.say(f"  ↳ 🚫 **{t.name}** ممنوع من التعزيزات")
        elif k == "dot":
            amt = effective_atk(c) * spec["mult"] * c.power
            if self.add_effect(t, mk(k, amount=amt, dmg_type=dtype)):
                self.say(f"  ↳ ☠️ **{t.name}** عليه ضرر مؤجل كل جولة")
        elif k == "delay":
            if self._immune(t):
                self.say(f"  ↳ 🛡️ **{t.name}** محصّن ضد التأخير")
            elif self.rng.random() < spec["chance"]:
                if t in self.queue:
                    self.queue.remove(t)
                    self.queue.append(t)
                else:
                    t.delayed_next = True
                self.say(f"  ↳ ⏳ تأخر دور **{t.name}**")
        elif k == "energy_ally":
            t.energy = min(t.max_energy, t.energy + spec["amount"])

    @staticmethod
    def _immune(t: Unit) -> bool:
        return t.passive == "lord_of_death"            # سلبية آينز: محصّن من التحكم

    def _on_death(self, dead: Unit):
        for u in self.units:                           # سلبية آينز عند موت أي عدو
            if u.alive and u.passive == "lord_of_death" and u.side != dead.side:
                heal = round(u.max_hp * 0.15)
                u.hp = min(u.max_hp, u.hp + heal)
                u.energy = min(u.max_energy, u.energy + 20)
                self.say(f"  ↳ ☠️ **{u.name}** يستعيد {heal} صحة و20 طاقة")

    def hit(self, src, t: Unit, dmg: int, dtype: str, resisted: bool = False, note: str = ""):
        if dtype == "physical":
            imm = [e for e in t.effects if e.kind == "phys_immune"]
            if imm:
                t.effects.remove(imm[0])
                self.say(f"  ↳ ✨ **{t.name}** تجاهل الهجوم الجسدي بالكامل")
                return 0
        if any(u.alive and u.passive == "lucky_angel" and u.side == t.side for u in self.units):
            dmg = max(1, round(dmg * 0.9))             # سلبية كلاين: -10% ضرر على الفريق
        absorbed = 0
        for e in [e for e in t.effects if e.kind == "shield"]:
            take = min(e.amount, dmg)
            e.amount -= take
            dmg -= take
            absorbed += take
            if e.amount <= 0:
                t.effects.remove(e)
            if dmg <= 0:
                break
        t.hp = max(0, t.hp - dmg)
        txt = f"  ↳ **{t.name}**: -{int(dmg)} ❤️ ({int(t.hp)}/{t.max_hp})"
        if absorbed:
            txt += f" 🛡️ امتص {int(absorbed)}"
        if resisted:
            txt += " 🌀 مقاومة"
        if note:
            txt += f" — {note}"
        self.say(txt)
        if t.hp > 0 and dtype == "physical" and dmg > 0:
            sl = [e for e in t.effects if e.kind == "sleep"]
            if sl:
                t.effects.remove(sl[0])
                self.say(f"  ↳ ⏰ استيقظ **{t.name}**")
        if t.hp <= 0:
            t.effects = []
            self.say(f"  💀 سقط **{t.name}**")
            self._on_death(t)
        return dmg


def unit_line(u: Unit, current: bool = False, round_no: int = 0) -> str:
    if not u.alive:
        return f"💀 ~~{u.name}~~"
    icons = "".join(e.icon for e in u.effects)
    en = f" ⚡ {u.energy}/{u.max_energy}" if u.max_energy else ""
    return f"{'▶️ ' if current else ''}**{u.name}** ❤️ {int(u.hp)}/{u.max_hp}{en} {icons}".strip()
