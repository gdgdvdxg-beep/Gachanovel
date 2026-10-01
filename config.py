"""إعدادات اللعبة — كل الأرقام هنا قابلة للتعديل بدون لمس الكود."""
import os

# ---------- التشغيل ----------
DB_PATH = os.environ.get("DB_PATH", "gacha.db")
GUILD_ID = os.environ.get("GUILD_ID")      # اختياري: لتسريع ظهور الأوامر في سيرفر الاختبار
TZ_OFFSET_HOURS = 0                        # فرق التوقيت عن UTC لتحديد بداية "اليوم" للزعيم اليومي
TURN_TIMEOUT = 60                          # ثواني الانتظار قبل أن يلعب البوت دور اللاعب تلقائيًا

# ---------- القتال ----------
START_ENERGY = 50                          # طاقة بداية المعركة لكل الشخصيات
MAX_ROUNDS = 50                            # أقصى عدد جولات قبل اعتبار المعركة خسارة
TEAM_SIZE = 4
RARITIES = ["common", "rare", "special", "unique", "epic", "legendary"]
RARITY_AR = {"common": "عادي", "rare": "نادر", "special": "مميز",
             "unique": "فريد", "epic": "ملحمي", "legendary": "أسطوري"}
RARITY_ICON = {"common": "⚪", "rare": "🔵", "special": "🟢",
               "unique": "🟣", "epic": "🟠", "legendary": "🟡"}
# مدة التعزيزات والإضعافات بالجولات حسب الندرة (القسم 10 من الوثيقة)
RARITY_DURATION = {"common": 1, "rare": 1, "special": 2, "unique": 2, "epic": 3, "legendary": 3}

# ---------- المستويات والرتب ----------
MAX_LEVEL = 100
LEVEL_GROWTH = 0.03        # +3% من قيمة المستوى 1 لكل مستوى
MAX_RANK = 5
RANK_BONUS = 0.05          # +5% مركّبة لكل رتبة (إحصائيات + قوة مهارات)

def xp_needed(level: int) -> int:
    """XP المطلوب للانتقال من level إلى level+1 (قيمة مبدئية)."""
    return 40 + 10 * level

# ---------- السحب ----------
BASE_RATES = {"common": 55.0, "rare": 26.0, "special": 12.0,
              "unique": 5.0, "epic": 1.4, "legendary": 0.6}
DRAW_COST = 10             # مواد السحب لكل سحبة (مبدئي)
START_MATERIALS = 100      # مواد السحب عند /ابدأ
OVERFLOW_REFUND = 5        # مواد تُعاد عند سحب نسخة زائدة بعد الرتبة الخامسة (مبدئي — القرار لم يُحسم)
LUCK_STEP = 0.5            # نقاط مئوية تُنقل من "عادي" للندرات الأعلى لكل هزيمة زعيم
LUCK_MAX_WINS = 10         # سقف تأثير هزائم الزعيم على النسب

# ---------- المعارك الدورية ----------
NORMAL_SLOT = 30 * 60
ADVENTURE_SLOT = 3 * 60 * 60
ENEMY_LEVEL_PER_BOSS_WIN = 3
REWARD_BONUS_PER_BOSS_WIN = 0.05
REWARDS = {   # مواد السحب (min, max) و XP لكل شخصية في الفريق (مبدئية)
    "normal":    {"materials": (1, 3),  "xp": 30},
    "adventure": {"materials": (4, 7),  "xp": 80},
    "boss":      {"materials": (8, 14), "xp": 150},
}
