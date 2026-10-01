import asyncio
import os
import discord
from discord.ext import commands

import config
from cog import GachaCog
from db import Database

try:                                   # اختياري: قراءة ملف .env إن وُجدت المكتبة
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class GachaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.db = Database()

    async def setup_hook(self):
        await self.add_cog(GachaCog(self, self.db))
        if config.GUILD_ID:                                   # مزامنة فورية في سيرفر الاختبار
            guild = discord.Object(id=int(config.GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:                                                 # عالميًا (قد يتأخر ظهور الأوامر قليلًا)
            await self.tree.sync()

    async def on_ready(self):
        print(f"✅ البوت يعمل باسم {self.user}")


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("ضع رمز البوت في المتغير DISCORD_TOKEN (انظر README.md)")
    GachaBot().run(token)
