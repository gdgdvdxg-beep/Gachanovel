# بوت لعبة RPG غاتشا (ديسكورد)

بوت عربي بالكامل: سحب شخصيات، فريق من 4، قتال بالأدوار بأزرار، معارك عادية ومغامرات وزعيم يومي.

## التشغيل

1. ثبّت Python 3.10 أو أحدث، ثم:
   ```
   pip install -r requirements.txt
   ```
2. أنشئ بوتًا من https://discord.com/developers/applications :
   - من **Bot** انسخ **Token**.
   - من **OAuth2 → URL Generator** اختر النطاقين `bot` و `applications.commands` وادعُ البوت لسيرفرك.
3. ضع الرمز في متغير بيئة (أو في ملف `.env` بجانب `main.py`):
   ```
   DISCORD_TOKEN=رمز_البوت
   GUILD_ID=رقم_السيرفر      # اختياري: لتظهر الأوامر فورًا أثناء الاختبار
   ```
4. شغّل:
   ```
   python main.py
   ```

> إذا رفض ديسكورد الأسماء العربية للأوامر، غيّر `name="..."` في `cog.py` إلى أسماء إنجليزية.

## نظام الطاقة
- كل الشخصيات تبدأ المعركة بـ **50 طاقة** (`START_ENERGY` في `config.py`).
- الهجوم الأساسي يمنح **+30** (`"energy": 30`).
- القدرات الخاصة **تستهلك** طاقة (`"cost": 30`)، والنهائية تستهلك تكلفتها (الحد الأقصى للشخصية).
- كل قدرة لها `"kind"`: `basic` أو `special` أو `ult`. القدرة المختومة (`seal`) لا يمكنها إلا الأساسي.
- السلبيات معرّفة في `characters.json` (`passive`) وتعمل داخل `engine.py` بحسب `id`: `lucky_angel` و`ai_insight` و`lord_of_death`.

## الشخصيات الحالية
كلاين، ليلين، آينز (أسطوري) · ديميورغ (ملحمي) · أودري (فريد) · نابيرال (مميز) · ديريك (نادر) · براين (عادي).

## الأوامر
`/ابدأ` · `/سحب` · `/شخصياتي` · `/فريقي` · `/شخصية` · `/رصيدي` · `/معركة` · `/مغامرة` · `/الزعيم`

## الملفات
| الملف | وظيفته |
|---|---|
| `config.py` | كل الأرقام: النسب، التكاليف، المكافآت، المهل |
| `engine.py` | محرك القتال (بدون ديسكورد) |
| `data/characters.json` | الشخصيات وقدراتها |
| `data/enemies.json` | الأعداء والزعماء |
| `gamedata.py` | بناء الوحدات من البيانات (المستوى والرتبة) |
| `gacha.py` | السحب ونسبه |
| `db.py` | قاعدة SQLite |
| `session.py` | جلسة المعركة والمكافآت |
| `ui.py` / `cog.py` / `main.py` | واجهة ديسكورد والأوامر والتشغيل |
| `test_engine.py` / `test_flow.py` / `test_kits.py` | اختبارات: `python test_engine.py` و `python test_flow.py` و `python test_kits.py` |

## إضافة شخصية أو عدو
أضف عنصرًا في `data/characters.json` أو `data/enemies.json` بنفس شكل الموجود، بدون تعديل الكود.
أنواع التأثيرات المدعومة في `effects`:
`damage` (مع `ignore` و`splash`)، `damage_bonus_if_dot`, `shield`, `heal`, `heal_atk`, `def_mod`, `atk_mod`, `def_type_mod`, `ignore_def`,
`dmg_taken_reduce` (مع `dmg_types`)، `phys_immune`, `block_ult`, `block_buff`, `dot`, `delay`, `sleep`, `confuse`, `seal`,
`cleanse`, `cleanse_control`, `ult_boost`, `revive`, `energy_ally`. أضف `"on": "enemies"` لتطبيق تأثير على الأعداء ضمن قدرة موجهة للحلفاء.
أنواع الأهداف `target`: `enemy`, `enemy_plus`, `all_enemies`, `ally`, `all_allies`, `self`.

## قيم مبدئية تحتاج قرارك (في config.py)
تكلفة السحبة، مكافآت المعارك، XP لكل مستوى، مقدار رفع نسب السحب بعد الزعيم،
ما يحدث للنسخة الزائدة بعد الرتبة 5 (حاليًا تُعاد 5 مواد).
