import os, asyncio, html, tempfile, subprocess
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, BotCommand
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Запоминаем позицию пользователя в каждом разделе
USER_POS: dict[tuple[int, str], int] = {}

def make_nav_kb(kind: str, idx: int, total: int) -> InlineKeyboardMarkup:
    """kind: 'daily' | 'pensioners'"""
    prev_i = (idx - 1) % total
    next_i = (idx + 1) % total
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="⏮️ Пред.", callback_data=f"{kind}:nav:{prev_i}"),
            InlineKeyboardButton(text="⏭️ След.", callback_data=f"{kind}:nav:{next_i}"),
        ]]
    )
from rapidfuzz import fuzz
# --- robust imports for mods (Render/GitHub/Docker) ---
import sys, pathlib
BASE_DIR = pathlib.Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
MODS_DIR = BASE_DIR / "mods"
if MODS_DIR.exists() and str(MODS_DIR) not in sys.path:
    sys.path.insert(0, str(MODS_DIR))
try:
    # обычный путь: пакет mods/*
    from mods.tts_provider import tts_say
    from mods.stt_provider import stt_recognize, wav_duration_sec
except ModuleNotFoundError:
    # запасной путь: файлы лежат рядом
    from tts_provider import tts_say
    from stt_provider import stt_recognize, wav_duration_sec
# --- end robust imports ---
# твои рабочие модули (из бэкапа)
# === ENV ===
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise SystemExit("ERROR: TELEGRAM_BOT_TOKEN is not set")
dp = Dispatcher()  # ВАЖНО: объявлен ДО декораторов
# === MENU (только 2 кнопки) ===
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🎴 Daily"), KeyboardButton(text="🧓 Pensioners")]],
        resize_keyboard=True,
    )
# === CONTENT (Daily + Pensioners) ===
PHRASES = [  # Daily
    {"zh":"早晨！你食咗飯未呀？","yale":"zou2 san4! nei5 sik6 zo2 faan6 mei6 aa3?","ru":"Доброе утро! Ты уже ел(а)?"},
    {"zh":"今晚有冇時間？","yale":"gam1 maan5 jau5 mou5 si4 gaan3 aa3?","ru":"Ты сегодня вечером свободен(на)?"},
    {"zh":"呢啲點賣？","yale":"ni1 di1 dim2 maai6 aa3?","ru":"Сколько это стоит?"},
    {"zh":"可唔可以平啲？","yale":"ho2 m4 ho2 ji5 peng4 di1 aa3?","ru":"Можно подешевле?"},
    {"zh":"我用八達通得唔得？","yale":"ngo5 jung6 baat3 daat6 tung1 dak1 m4 dak1 aa3?","ru":"Можно оплатить Octopus-картой?"},
    {"zh":"唔該幫我影張相。","yale":"m4 goi1 bong1 ngo5 jing2 zoeng1 soeng2.","ru":"Сфотографируй меня, пожалуйста."},
    {"zh":"廁所喺邊度？","yale":"ci3 so2 hai2 bin1 dou6 aa3?","ru":"Где туалет?"},
]
FUN_PENSIONERS = [  # "гонконгские пенсионеры"
    {"zh":"你個假牙好型，我就鍾意呢款。","yale":"nei5 go3 gaa2 ngaa4 hou2 jing4, ngo5 zau6 zung1 ji3 ni1 fun2.","ru":"У тебя стильная вставная челюсть - как раз такие я и люблю."},
    {"zh":"年紀差四十年，我都唔介意。","yale":"nin4 gei2 caa1 sei3 sap6 nin4, ngo5 dou1 m4 gaai3 ji3.","ru":"Разница в сорок лет меня вообще не смущает."},
    {"zh":"我信一見轉數快嘅愛情。","yale":"ngo5 seon3 jat1 gin3 zyun3 sou3 faai3 ge3 oi3 cing4.","ru":"Я верю в любовь с первого банковского перевода (FPS)."},
    {"zh":"我鍾意你對眼，唔係你喺中環嗰層千呎靚樓，老實講。","yale":"ngo5 zung1 ji3 nei5 deoi3 ngaan5, m4 hai6 nei5 hai2 zung1 waan4 go2 cang4 cin1 cek3 leng3 lau2, lou5 sat6 gong2.","ru":"Мне нравятся твои глаза, а не квартира в Центре, честно."},
    {"zh":"我好鍾意你啲盆栽相，記得多啲傳畀我呀！","yale":"ngo5 hou2 zung1 ji3 nei5 di1 pun4 zoi1 soeng2, gei3 dak1 do1 di1 cyun4 bei2 ngo5 aa3!","ru":"Классные фото твоих растений - присылай ещё!"},
]
# === HELPERS ===
LAST_PROMPT: dict[int, str] = {}  # user_id -> last zh phrase
def card_text(title: str, p: dict) -> str:
    return (
        f"{title}\n\n"
        f"🈶 <b>{html.escape(p['zh'])}</b>\n"
        f"🔤 {html.escape(p['yale'])}\n"
        f"🇷🇺 {html.escape(p['ru'])}"
    )
def ogg_to_wav16k(src_path: str) -> str | None:
    fd, dst = tempfile.mkstemp(suffix=".wav"); os.close(fd)
    try:
        p = subprocess.run(
            ["ffmpeg","-y","-i",src_path,"-ar","16000","-ac","1",dst],
            capture_output=True
        )
        if p.returncode != 0 or not os.path.exists(dst) or os.path.getsize(dst) == 0:
            try: os.remove(dst)
            except: pass
            return None
        return dst
    except Exception:
        try: os.remove(dst)
        except: pass
        return None
async def send_card(m: Message, header: str, p: dict, kb: InlineKeyboardMarkup | None = None):
    """Отправить карточку с TTS. Сохранить промпт для последующей проверки."""
    LAST_PROMPT[m.from_user.id] = p["zh"]
    txt = card_text(header, p)
    audio = await tts_say(p["zh"])
    if audio:
        try:
            await m.answer_audio(FSInputFile(audio), caption=txt, parse_mode="HTML", reply_markup=kb)
        finally:
            try: os.remove(audio)
            except: pass
    else:
        await m.answer(txt, parse_mode="HTML", reply_markup=kb)
    await m.answer("🎤 Пришли голосовое, чтобы получить оценку (или набери /say).")
# === HANDLERS ===
@dp.message(CommandStart())
async def cmd_start(m: Message):
    await m.answer("👋 Бот готов. Выбирай режим ниже.", reply_markup=main_menu())
@dp.message(F.text == "🎴 Daily")
@dp.message(Command("daily"))
async def cmd_daily(m: Message):
    i = USER_POS.get((m.from_user.id, "daily"), 0)
    i = max(0, min(i, len(PHRASES) - 1))
    kb = make_nav_kb("daily", i, len(PHRASES))
    await send_card(m, "🎴 Daily", PHRASES[i], kb)
@dp.message(F.text == "🧓 Pensioners")
@dp.message(Command("pensioners"))
async def cmd_pensioners(m: Message):
    i = USER_POS.get((m.from_user.id, "pensioners"), 0)
    i = max(0, min(i, len(FUN_PENSIONERS) - 1))
    kb = make_nav_kb("pensioners", i, len(FUN_PENSIONERS))
    await send_card(m, "🧓 Pensioners", FUN_PENSIONERS[i], kb)
@dp.callback_query(F.data.startswith("daily:nav:"))
async def cb_daily_nav(cb):
    try:
        _, _, idx = cb.data.split(":")
        i = int(idx)
    except Exception:
        await cb.answer()
        return
    USER_POS[(cb.from_user.id, "daily")] = i
    kb = make_nav_kb("daily", i, len(PHRASES))
    # Отправляем НОВУЮ карточку (редактировать аудио неудобно)
    await send_card(cb.message, "🎴 Daily", PHRASES[i], kb)
    await cb.answer()
@dp.callback_query(F.data.startswith("pensioners:nav:"))
async def cb_pensioners_nav(cb):
    try:
        _, _, idx = cb.data.split(":")
        i = int(idx)
    except Exception:
        await cb.answer()
        return
    USER_POS[(cb.from_user.id, "pensioners")] = i
    kb = make_nav_kb("pensioners", i, len(FUN_PENSIONERS))
    await send_card(cb.message, "🧓 Pensioners", FUN_PENSIONERS[i], kb)
    await cb.answer()
@dp.message(Command("say"))
async def cmd_say(m: Message):
    ref = LAST_PROMPT.get(m.from_user.id) or PHRASES[0]["zh"]
    LAST_PROMPT[m.from_user.id] = ref
    await m.answer(
        "🎙️ Скажи фразу и отправь <b>голосовое сообщение</b>.\n"
        "Эталон:\n"
        f"<b>{html.escape(ref)}</b>",
        parse_mode="HTML"
    )
@dp.message(F.voice | F.audio)
async def on_voice(m: Message, bot: Bot):
    # 1) скачать файл
    tgfile = await bot.get_file((m.voice or m.audio).file_id)
    fd_src, path_src = tempfile.mkstemp(suffix=".ogg"); os.close(fd_src)
    await bot.download(tgfile, destination=path_src)
    # 2) конверт в wav16k
    wav = ogg_to_wav16k(path_src)
    try:
        os.remove(path_src)
    except Exception:
        pass
    if not wav:
        await m.answer("⚠️ Не удалось обработать аудио (ffmpeg).")
        return
    # 3) контроль длины, распознавание
    dur = wav_duration_sec(wav)
    if dur < 0.6:
        await m.answer("🔈 Запись слишком короткая (<0.6 с). Скажи 1-3 секунды и пришли ещё раз.")
        try: os.remove(wav)
        except: pass
        return
    text = await stt_recognize(wav, m.from_user.id)
    try: os.remove(wav)
    except: pass
    if not text:
        await m.answer("🤷 Не удалось распознать речь. Попробуй ближе к микрофону, без шума.")
        return
    # 4) сравнение с эталоном
    ref = LAST_PROMPT.get(m.from_user.id) or PHRASES[0]["zh"]
    score = int(fuzz.ratio(text, ref))
    body = (
        "🧪 <b>Проверка произношения</b>\n"
        f"🗣️ Ты сказал: <code>{html.escape(text)}</code>\n"
        f"🎯 Эталон: <b>{html.escape(ref)}</b>\n"
        f"📊 Совпадение: <b>{score}%</b>"
    )
    await m.answer(body, parse_mode="HTML")
# === MAIN ===
async def main():
    bot = Bot(TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([
        BotCommand(command="daily",       description="Daily phrases"),
        BotCommand(command="pensioners",  description="Funny seniors"),
        BotCommand(command="say",         description="Speak & get score"),
    ])
    print("[INFO] Bot started.")
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())


