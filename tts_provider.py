import os, tempfile
import edge_tts
VOICE = os.getenv("TTS_VOICE", "zh-HK-HiuMaanNeural")
async def tts_say(text: str, user_id: int | None = None) -> str | None:
    """
    Синтез речи через edge-tts. Возвращает путь к mp3 или None.
    """
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp.close()
        comm = edge_tts.Communicate(text, voice=VOICE)
        await comm.save(tmp.name)
        return tmp.name if os.path.getsize(tmp.name) > 0 else None
    except Exception as e:
        print("[TTS edge] error:", e)
        return None
