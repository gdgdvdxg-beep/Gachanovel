"""نظام السحب: النسب الأساسية + تأثير هزائم الزعيم اليومي."""
import random
import config
import gamedata


def effective_rates(boss_wins: int) -> dict:
    """تنقل النسب قليلًا من العادي إلى الندرات الأعلى بحسب هزائم الزعيم (بسقف)."""
    rates = dict(config.BASE_RATES)
    shift = min(boss_wins, config.LUCK_MAX_WINS) * config.LUCK_STEP
    shift = min(shift, rates["common"])
    others = {k: v for k, v in rates.items() if k != "common"}
    total = sum(others.values())
    rates["common"] -= shift
    for k, v in others.items():
        rates[k] += shift * v / total
    return rates


def pool_by_rarity() -> dict:
    pool = {r: [] for r in config.RARITIES}
    for cid, c in gamedata.CHARS.items():
        pool[c["rarity"]].append(cid)
    return pool


def roll(rng: random.Random, boss_wins: int = 0) -> str:
    """يسحب شخصية. الندرات التي لا توجد فيها شخصيات بعد تُستبعد وتُعاد موازنة النسب."""
    pool = pool_by_rarity()
    rates = {r: w for r, w in effective_rates(boss_wins).items() if pool[r]}
    rarity = rng.choices(list(rates), weights=list(rates.values()))[0]
    return rng.choice(pool[rarity])
