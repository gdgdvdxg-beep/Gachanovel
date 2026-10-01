"""اختبار تكامل بدون ديسكورد: قاعدة البيانات + السحب + الجلسة."""
import random
import config, gamedata, gacha
from db import Database
from session import BattleSession


def test_rates_sum_and_luck():
    base = gacha.effective_rates(0)
    assert abs(sum(base.values()) - 100) < 1e-9
    lucky = gacha.effective_rates(10)
    assert abs(sum(lucky.values()) - 100) < 1e-9
    assert lucky["legendary"] > base["legendary"] and lucky["common"] < base["common"]
    capped = gacha.effective_rates(999)
    assert capped == lucky


def test_db_ranks_and_team():
    db = Database(":memory:")
    db.create_player(1, 100)
    assert db.add_char_copy(1, "klein") == "new"
    for _ in range(5):
        assert db.add_char_copy(1, "klein") == "rank"
    assert db.get_char(1, "klein")["rnk"] == 5
    assert db.add_char_copy(1, "klein") == "max"
    assert db.get_team(1) == ["klein"]
    assert db.spend_materials(1, 100) and not db.spend_materials(1, 1)


def test_xp_levels():
    db = Database(":memory:")
    db.create_player(1, 0); db.add_char_copy(1, "lilen")
    lvl, gained = db.add_xp(1, "lilen", 50)          # المطلوب من 1 إلى 2 = 50
    assert (lvl, gained) == (2, 1)
    lvl, gained = db.add_xp(1, "lilen", 10_000_000)
    assert lvl == config.MAX_LEVEL


def test_session_adventure_and_rewards():
    db = Database(":memory:")
    db.create_player(7, 0)
    for c in ("klein", "lilen", "ainz"):
        db.add_char_copy(7, c)
    rng = random.Random(1)
    players = [gamedata.build_player(c, 1, 0, f"p{i}") for i, c in enumerate(db.get_team(7))]
    waves = [gamedata.build_enemies(["skeleton", "skeleton"], 1),
             gamedata.build_enemies(["fire_mage", "stone_guard", "skeleton"], 1),
             gamedata.build_enemies(["skeleton_captain", "skeleton"], 1)]
    s = BattleSession(db, 7, "adventure", players, waves, 0, rng)
    n = 0
    while not s.finished:
        s.auto_turn(); n += 1
        assert n < 1000
    assert s.result in ("win", "lose")
    if s.result == "win":
        assert db.get_player(7)["materials"] > 0


def test_roll_only_available_rarities():
    rng = random.Random(3)
    assert {gacha.roll(rng) for _ in range(50)} <= set(gamedata.CHARS)


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("OK", n)
