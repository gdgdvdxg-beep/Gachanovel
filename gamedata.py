"""تحميل بيانات الشخصيات والأعداء وبناء وحدات القتال."""
import json
from pathlib import Path
import config
from engine import Unit

_DIR = Path(__file__).parent / "data"


def _load(name):
    return {x["id"]: x for x in json.loads((_DIR / name).read_text(encoding="utf-8"))}


CHARS = _load("characters.json")
ENEMIES = _load("enemies.json")


def stat_at(base: float, level: int) -> float:
    return base * (1 + config.LEVEL_GROWTH * (level - 1))


def build_player(char_id: str, level: int, rank: int, uid: str) -> Unit:
    c = CHARS[char_id]
    f = (1 + config.RANK_BONUS) ** rank
    return Unit(uid=uid, name=c["name"], side="player", char_id=char_id,
                max_hp=round(stat_at(c["hp"], level) * f), atk=stat_at(c["atk"], level) * f,
                defense=stat_at(c["def"], level) * f, dmg_type=c["dmg_type"], resistance=c["resistance"],
                max_energy=c["max_energy"], abilities=c["abilities"], rarity=c["rarity"], power=f,
                passive=c.get("passive", {}).get("id", ""))


def build_enemies(ids: list[str], level: int) -> list[Unit]:
    units, seen = [], {}
    for i in ids:
        seen[i] = seen.get(i, 0) + 1
    count = {}
    for n, eid in enumerate(ids):
        e = ENEMIES[eid]
        name = e["name"]
        if seen[eid] > 1:
            count[eid] = count.get(eid, 0) + 1
            name += " " + "أبجدهو"[count[eid] - 1]
        units.append(Unit(uid=f"e{n}", name=name, side="enemy", char_id=eid,
                          max_hp=round(stat_at(e["hp"], level)), atk=stat_at(e["atk"], level),
                          defense=stat_at(e["def"], level), dmg_type=e["dmg_type"], resistance=e["resistance"],
                          max_energy=e["max_energy"], abilities=e["abilities"], rarity=e["rarity"], ai=e["ai"]))
    return units


def enemies_by_tier(tier: str) -> list[str]:
    return [k for k, v in ENEMIES.items() if v["tier"] == tier]
