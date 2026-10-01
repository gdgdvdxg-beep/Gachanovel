"""قاعدة البيانات (SQLite): اللاعبون والشخصيات التي يملكونها."""
import json
import sqlite3
import config


class Database:
    def __init__(self, path: str = config.DB_PATH):
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript("""
            CREATE TABLE IF NOT EXISTS players(
                user_id INTEGER PRIMARY KEY,
                materials INTEGER NOT NULL DEFAULT 0,
                team TEXT NOT NULL DEFAULT '[]',
                boss_wins INTEGER NOT NULL DEFAULT 0,
                last_normal_slot INTEGER NOT NULL DEFAULT -1,
                last_adv_slot INTEGER NOT NULL DEFAULT -1,
                last_boss_day TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS chars(
                user_id INTEGER NOT NULL,
                char_id TEXT NOT NULL,
                level INTEGER NOT NULL DEFAULT 1,
                xp INTEGER NOT NULL DEFAULT 0,
                rnk INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(user_id, char_id)
            );
        """)

    # ---- اللاعب ----
    def get_player(self, uid):
        return self.con.execute("SELECT * FROM players WHERE user_id=?", (uid,)).fetchone()

    def create_player(self, uid, materials):
        self.con.execute("INSERT OR IGNORE INTO players(user_id, materials) VALUES(?,?)", (uid, materials))
        self.con.commit()

    def add_materials(self, uid, n):
        self.con.execute("UPDATE players SET materials=materials+? WHERE user_id=?", (n, uid))
        self.con.commit()

    def spend_materials(self, uid, n) -> bool:
        cur = self.con.execute("UPDATE players SET materials=materials-? WHERE user_id=? AND materials>=?", (n, uid, n))
        self.con.commit()
        return cur.rowcount == 1

    def set_slot(self, uid, column, value):
        assert column in ("last_normal_slot", "last_adv_slot", "last_boss_day")
        self.con.execute(f"UPDATE players SET {column}=? WHERE user_id=?", (value, uid))
        self.con.commit()

    def add_boss_win(self, uid):
        self.con.execute("UPDATE players SET boss_wins=boss_wins+1 WHERE user_id=?", (uid,))
        self.con.commit()

    # ---- الشخصيات ----
    def get_chars(self, uid):
        return self.con.execute("SELECT * FROM chars WHERE user_id=? ORDER BY level DESC, rnk DESC", (uid,)).fetchall()

    def get_char(self, uid, cid):
        return self.con.execute("SELECT * FROM chars WHERE user_id=? AND char_id=?", (uid, cid)).fetchone()

    def add_char_copy(self, uid, cid) -> str:
        """يضيف نسخة: new (جديدة) / rank (رفعت الرتبة) / max (الرتبة القصوى مسبقًا)."""
        row = self.get_char(uid, cid)
        if row is None:
            self.con.execute("INSERT INTO chars(user_id, char_id) VALUES(?,?)", (uid, cid))
            team = self.get_team(uid)
            if len(team) < config.TEAM_SIZE:
                self.set_team(uid, team + [cid])
            self.con.commit()
            return "new"
        if row["rnk"] >= config.MAX_RANK:
            return "max"
        self.con.execute("UPDATE chars SET rnk=rnk+1 WHERE user_id=? AND char_id=?", (uid, cid))
        self.con.commit()
        return "rank"

    def add_xp(self, uid, cid, xp):
        """يعيد (المستوى الجديد, عدد المستويات المكتسبة)."""
        row = self.get_char(uid, cid)
        level, cur, gained = row["level"], row["xp"] + xp, 0
        while level < config.MAX_LEVEL and cur >= config.xp_needed(level):
            cur -= config.xp_needed(level)
            level += 1
            gained += 1
        if level >= config.MAX_LEVEL:
            cur = 0
        self.con.execute("UPDATE chars SET level=?, xp=? WHERE user_id=? AND char_id=?", (level, cur, uid, cid))
        self.con.commit()
        return level, gained

    # ---- الفريق ----
    def get_team(self, uid) -> list:
        row = self.get_player(uid)
        owned = {c["char_id"] for c in self.get_chars(uid)}
        return [c for c in json.loads(row["team"]) if c in owned][:config.TEAM_SIZE] if row else []

    def set_team(self, uid, ids):
        self.con.execute("UPDATE players SET team=? WHERE user_id=?", (json.dumps(ids[:config.TEAM_SIZE]), uid))
        self.con.commit()
