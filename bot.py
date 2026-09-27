import asyncio
import logging
import os
import sqlite3

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [8377218647]  # buni o'zingizning Telegram ID'ingizga almashtiring
DB_PATH = "movies.db"
PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS movies (
        code TEXT PRIMARY KEY,
        file_id TEXT NOT NULL,
        title TEXT
    )
""")
conn.commit()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("Salom! 🎬\n\nKino kodini yuboring, men sizga kinoni topib beraman.\nMasalan: <code>101</code>", parse_mode="HTML")

@dp.message(Command("help"))
async def help_handler(message: Message):
    text = ("🎬 <b>Kino bot qo'llanmasi</b>\n\nFoydalanuvchi uchun:\n— Kino kodini yuboring (masalan: 101), bot videoni yuboradi.\n")
    if is_admin(message.from_user.id):
        text += ("\nAdmin uchun:\n— Video xabarga <b>reply</b> qilib <code>/add kod</code> yozing — kino saqlanadi.\n— <code>/delete kod</code> — kinoni o'chiradi.\n— <code>/list</code> — barcha kodlar ro'yxati.\n")
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("add"))
async def add_movie(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("Bu buyruq faqat adminlar uchun.")
    if not message.reply_to_message or not message.reply_to_message.video:
        return await message.answer("Video xabariga <b>reply</b> qilib <code>/add kod</code> deb yozing.\nMasalan: video xabarga reply qilib '/add 101'", parse_mode="HTML")
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        return await message.answer("Kodni kiriting, masalan: /add 101")
    code = args[1].strip()
    file_id = message.reply_to_message.video.file_id
    title = message.reply_to_message.caption or ""
    cursor.execute("INSERT OR REPLACE INTO movies (code, file_id, title) VALUES (?, ?, ?)", (code, file_id, title))
    conn.commit()
    await message.answer(f"✅ Kino saqlandi. Kod: <b>{code}</b>", parse_mode="HTML")

@dp.message(Command("delete"))
async def delete_movie(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("Bu buyruq faqat adminlar uchun.")
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        return await message.answer("Kodni kiriting, masalan: /delete 101")
    code = args[1].strip()
    cursor.execute("DELETE FROM movies WHERE code = ?", (code,))
    conn.commit()
    await message.answer(f"🗑 {code} kodli kino o'chirildi (agar mavjud bo'lsa).")

@dp.message(Command("list"))
async def list_movies(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("Bu buyruq faqat adminlar uchun.")
    cursor.execute("SELECT code, title FROM movies ORDER BY code")
    rows = cursor.fetchall()
    if not rows:
        return await message.answer("Hozircha hech qanday kino saqlanmagan.")
    lines = [f"• <b>{code}</b> — {title or 'nomsiz'}" for code, title in rows]
    await message.answer("🎬 Saqlangan kinolar:\n\n" + "\n".join(lines), parse_mode="HTML")

@dp.message(F.text)
async def get_movie(message: Message):
    code = message.text.strip()
    cursor.execute("SELECT file_id, title FROM movies WHERE code = ?", (code,))
    row = cursor.fetchone()
    if row:
        file_id, title = row
        caption = title if title else f"Kino kodi: {code}"
        await message.answer_video(file_id, caption=caption)
    else:
        await message.answer("❌ Bunday kod topilmadi. Kodni tekshirib qaytadan yuboring.")

async def handle_ping(request):
    return web.Response(text="Bot ishlayapti ✅")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
