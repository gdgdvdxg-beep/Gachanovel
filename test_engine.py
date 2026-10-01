import random
import config, gamedata
from engine import Battle, calc_damage, Unit


def mk(atk, df, dtype="physical", res="dark"):
    return Unit(uid="x", name="x", side="player", max_hp=100, atk=atk, defense=df, dmg_type=dtype, resistance=res)


def test_damage_formula():
    assert calc_damage(mk(100, 0), mk(0, 100), 1.0, "physical")[0] == 50


def test_resistance_doubles_defense():
    d, res = calc_damage(mk(100, 0), mk(0, 100, res="physical"), 1.0, "physical")
    assert res and d == 33          # 100*100/(100+200)


def test_level_and_rank_growth():
    u = gamedata.build_player("klein", 100, 0, "p0")
    assert u.max_hp == round(270 * (1 + 0.03 * 99))
    u5 = gamedata.build_player("klein", 1, 5, "p0")
    assert abs(u5.atk - 45 * 1.05 ** 5) < 1e-9


def run(seed, team_ids=("klein", "lilen", "ainz"), enemy_ids=("skeleton", "fire_mage", "stone_guard"), lvl=1, elvl=1):
    rng = random.Random(seed)
    ps = [gamedata.build_player(c, lvl, 0, f"p{i}") for i, c in enumerate(team_ids)]
    es = gamedata.build_enemies(list(enemy_ids), elvl)
    b = Battle(ps, es, rng)
    n = 0
    while not b.finished:
        b.auto_act(); n += 1
        assert n < 500
    return b


def test_battles_finish_and_player_starts():
    wins = 0
    for s in range(200):
        b = run(s)
        wins += b.winner == "player"
    assert wins > 0


def test_first_turn_is_player():
    for s in range(50):
        rng = random.Random(s)
        b = Battle([gamedata.build_player("klein", 1, 0, "p0")], gamedata.build_enemies(["skeleton"], 1), rng)
        assert b.current is not None and b.current.side == "player"


def test_ult_needs_energy():
    b = run(1)
    u = gamedata.build_player("klein", 1, 0, "p0")
    bb = Battle([u], gamedata.build_enemies(["skeleton"], 1), random.Random(3))
    assert not bb.can_use(bb.current, 4)
    bb.current.energy = 120
    assert bb.can_use(bb.current, 4)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("OK", name)
    for label, kw in [("3 عاديين", {}), ("قائد+هيكل", dict(enemy_ids=("skeleton_captain", "skeleton"))),
                      ("الزعيم مستوى 1", dict(enemy_ids=("ancient_guardian",))),
                      ("الزعيم مستوى 3", dict(enemy_ids=("ancient_guardian",), elvl=3))]:
        w = sum(run(s, **kw).winner == "player" for s in range(300))
        print(f"{label}: فوز {w/3:.0f}%")
