"""جلسة المعركة: تربط المحرك بالمكافآت وقاعدة البيانات (بدون اعتماد على ديسكورد)."""
import random
import config
import gamedata
from engine import Battle, unit_line

TITLES = {"normal": "⚔️ معركة عادية", "adventure": "🗺️ مغامرة", "boss": "👑 الزعيم اليومي"}


class BattleSession:
    def __init__(self, db, user_id: int, mode: str, players: list, waves: list, boss_wins: int, rng=None):
        self.db, self.user_id, self.mode = db, user_id, mode
        self.players, self.waves, self.boss_wins = players, waves, boss_wins
        self.rng = rng or random.Random()
        self.wave_idx = 0
        self.log: list[str] = []
        self.result: str | None = None       # win / lose
        self.summary: list[str] = []
        self._start_wave()

    @property
    def finished(self) -> bool:
        return self.result is not None

    @property
    def battle(self) -> Battle:
        return self._battle

    def _start_wave(self):
        self._battle = Battle(self.players, self.waves[self.wave_idx], self.rng)
        if self.mode == "adventure":
            self.log.append(f"🗺️ **الموجة {self.wave_idx + 1}/{len(self.waves)}**")
        self._sync()

    def _sync(self):
        """ينقل سجل المعركة ويتحقق من النهاية."""
        b = self._battle
        self.log += b.log
        b.log.clear()
        if b.finished:
            if b.winner == "player" and self.wave_idx + 1 < len(self.waves):
                self.wave_idx += 1
                self._start_wave()
            else:
                self._finish(b.winner == "player")

    def act(self, idx: int, target_uid=None):
        self._battle.act(idx, target_uid)
        self._sync()

    def auto_turn(self):
        self._battle.auto_act()
        self._sync()

    def _finish(self, won: bool):
        self.result = "win" if won else "lose"
        if not won:
            self.summary = ["💔 خسرت المعركة... لا مكافآت هذه المرة."]
        else:
            cfg = config.REWARDS[self.mode]
            mult = 1 + config.REWARD_BONUS_PER_BOSS_WIN * min(self.boss_wins, config.LUCK_MAX_WINS)
            mats = round(self.rng.randint(*cfg["materials"]) * mult)
            xp = round(cfg["xp"] * mult)
            self.db.add_materials(self.user_id, mats)
            self.summary = [f"🏆 **فزت!**", f"🎟️ +{mats} مواد سحب", f"⭐ +{xp} XP لكل شخصية في الفريق"]
            for p in self.players:
                level, gained = self.db.add_xp(self.user_id, p.char_id, xp)
                if gained:
                    self.summary.append(f"⬆️ {p.name} وصل إلى المستوى {level}")
            if self.mode == "boss":
                self.db.add_boss_win(self.user_id)
                self.summary.append("👑 ارتفع مستوى الأعداء والمكافآت، وزادت حظوظ السحب قليلًا.")
        self.log += self.summary

    def embed_data(self) -> dict:
        b = self._battle
        title = TITLES[self.mode]
        if self.mode == "adventure":
            title += f" — الموجة {self.wave_idx + 1}/{len(self.waves)}"
        cur = b.current
        return {
            "title": title,
            "description": "\n".join(self.log[-14:])[-3800:],
            "players": "\n".join(unit_line(u, u is cur) for u in b.players),
            "enemies": "\n".join(unit_line(u, u is cur) for u in b.enemies),
            "footer": f"الجولة {b.round}" + (f" — دور {cur.name}" if cur and not self.finished else ""),
            "result": self.result,
        }
