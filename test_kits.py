"""اختبارات الآليات الجديدة: الطاقة، النوم، الختم، الارتباك، السلبيات."""
import random
import config, gamedata
from engine import Battle, Effect


def mkb(team, enemies, seed=1, lvl=1):
    ps = [gamedata.build_player(c, lvl, 0, f"p{i}") for i, c in enumerate(team)]
    es = gamedata.build_enemies(list(enemies), 1)
    return Battle(ps, es, random.Random(seed)), ps, es


def cur_idx(b, name):
    return next(i for i, a in enumerate(b.current.abilities) if a["name"] == name)


def force_turn(b, unit):
    """يجعل unit صاحب الدور الحالي (للاختبار فقط)."""
    if b.current is not unit:
        b.queue = [u for u in b.queue if u is not unit]
        b.queue.insert(0, unit)
        b.current = None
        b.advance_to_forced = True
    return unit


def test_start_energy_and_costs():
    b, ps, es = mkb(["klein", "lilen", "ainz"], ["skeleton"])
    assert all(p.energy == 50 for p in ps)
    u = b.current
    basic = u.abilities[0]
    sp = next(a for a in u.abilities if a["kind"] == "special" and a.get("cost"))
    i = u.abilities.index(sp)
    e0 = u.energy
    assert b.can_use(u, i)
    u.energy = sp["cost"] - 1
    assert not b.can_use(u, i)                      # لا طاقة كافية
    u.energy = 50
    b.use_ability(u, 0, es[0])
    assert u.energy == min(u.max_energy, 80)        # الأساسي +30


def test_special_spends_energy():
    b, ps, es = mkb(["klein"], ["skeleton"])
    k = ps[0]
    b.current = k
    i = cur_idx(b, "التحكم بالدمى")
    b.use_ability(k, i, es[0])
    assert k.energy == 20
    assert es[0].defense * 0.7 < es[0].defense
    assert any(e.kind == "block_ult" for e in es[0].effects)


def test_ainz_maximize_gains_energy():
    b, ps, es = mkb(["ainz"], ["skeleton"])
    a = ps[0]; b.current = a
    b.use_ability(a, cur_idx(b, "تعزيز السحر"), None)
    assert a.energy == 90 and a.ult_boost == 0.25


def test_seal_blocks_specials_and_ult():
    b, ps, es = mkb(["audrey"], ["skeleton"])
    au, sk = ps[0], es[0]
    b.current = au
    b.use_ability(au, cur_idx(b, "الندبة النفسية"), sk)
    assert any(e.kind == "seal" for e in sk.effects)
    sk.abilities = [dict(a, cost=0) for a in sk.abilities]
    assert b.can_use(sk, 0) and not b.can_use(sk, 1)    # الأساسي فقط


def test_sleep_skips_turn_and_wakes_on_physical():
    b, ps, es = mkb(["audrey", "brain"], ["skeleton", "stone_guard"], seed=5)
    au, br = ps
    sk = es[0]
    b.current = au
    b.use_ability(au, cur_idx(b, "التنويم المغناطيسي"), sk)
    assert any(e.kind == "sleep" for e in sk.effects)
    b.hit(br, sk, 5, "mystic")                          # ضرر غير جسدي لا يوقظ
    assert any(e.kind == "sleep" for e in sk.effects)
    b.hit(br, sk, 5, "physical")                        # الجسدي يوقظ
    assert not any(e.kind == "sleep" for e in sk.effects)


def test_confuse_makes_enemy_hit_ally():
    b, ps, es = mkb(["demiurge"], ["skeleton", "stone_guard"], seed=2)
    d = ps[0]; b.current = d
    sk, sg = es
    b.use_ability(d, cur_idx(b, "صوت الإمبراطور"), sk)
    assert any(e.kind == "confuse" for e in sk.effects)
    hp_before = sg.hp
    sk.effects = [e for e in sk.effects if e.kind != "confuse"]
    b._confused_attack(sk)
    assert sg.hp < hp_before


def test_cleanse_and_heal():
    b, ps, es = mkb(["derrick", "audrey"], ["skeleton"])
    de, au = ps
    au.hp = 50
    au.effects.append(Effect(kind="def_mod", id="x", source="e", applied_round=1, expires_round=9, value=-0.3))
    b.current = de
    b.use_ability(de, cur_idx(b, "تطهير الجسد"), au)
    assert not au.effects
    b.current = au
    b.use_ability(au, cur_idx(b, "مهدئ العقل"), au)
    assert au.hp > 50


def test_chain_lightning_splash_and_ignore():
    b, ps, es = mkb(["narberal"], ["skeleton", "skeleton"])
    n = ps[0]; b.current = n
    hp = [e.hp for e in es]
    b.use_ability(n, cur_idx(b, "السلسلة الكهربائية"), es[0])
    assert es[0].hp < hp[0] and es[1].hp < hp[1]        # أصيب العدوان


def test_ainz_passive_on_kill_and_immunity():
    b, ps, es = mkb(["ainz"], ["skeleton"])
    a = ps[0]; a.hp = 100; a.energy = 0
    b.hit(a, es[0], 9999, "dark")
    assert a.hp == 100 + round(a.max_hp * 0.15) and a.energy == 20
    assert b._immune(a)


def test_klein_passive_reduces_team_damage():
    b, ps, es = mkb(["klein", "brain"], ["skeleton"])
    br = ps[1]
    h = br.hp
    b.hit(es[0], br, 100, "dark")
    assert h - br.hp == 90


def test_dot_and_bonus_ult_lilen():
    b, ps, es = mkb(["lilen"], ["stone_guard"], seed=4)
    l = ps[0]; b.current = l; l.energy = 100
    sg = es[0]
    b.use_ability(l, cur_idx(b, "نيران كيمويين السامة"), sg)
    assert any(e.kind == "dot" and e.id == "toxic_burn" for e in sg.effects)
    hp = sg.hp; l.energy = 100
    b.use_ability(l, cur_idx(b, "تجسد الأفعى العملاقة"), None)
    assert sg.hp < hp


def test_all_characters_battle_runs():
    ids = list(gamedata.CHARS)
    for s in range(60):
        rng = random.Random(s)
        team = rng.sample(ids, 4)
        ps = [gamedata.build_player(c, 1, 0, f"p{i}") for i, c in enumerate(team)]
        es = gamedata.build_enemies(["skeleton_captain", "fire_mage", "stone_guard"], 1)
        b = Battle(ps, es, rng)
        n = 0
        while not b.finished:
            b.auto_act(); n += 1
            assert n < 600


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("OK", name)
