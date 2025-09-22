import os, wave, contextlib, aiohttp
AZURE_KEY    = os.getenv("AZURE_SPEECH_KEY", "")
AZURE_REGION = os.getenv("AZURE_SPEECH_REGION", "westeurope")
LANG         = os.getenv("AZURE_STT_LANG", "zh-HK")  # кантонский по умолчанию
def wav_duration_sec(path: str) -> float:
    """
    Возвращает длительность wav-файла в секундах.
    """
    try:
        with contextlib.closing(wave.open(path, "rb")) as w:
            frames = w.getnframes()
            rate = w.getframerate()
            return frames / float(rate) if rate else 0.0
    except Exception:
        return 0.0
async def stt_recognize(wav_path: str, user_id: int | None = None) -> str | None:
    """
    Azure Speech Conversation endpoint (16 kHz, mono, PCM WAV).
    """
    if not (AZURE_KEY and AZURE_REGION):
        return None
    url = f"https://{AZURE_REGION}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language={LANG}"
    headers = {"Ocp-Apim-Subscription-Key": AZURE_KEY, "Content-Type": "audio/wav"}
    try:
        with open(wav_path, "rb") as f:
            data = f.read()
        async with aiohttp.ClientSession() as s:
            async with s.post(url, headers=headers, data=data) as r:
                if r.status != 200:
                    try:
                        body = await r.text()
                    except:
                        body = "<no text>"
                    print("[STT azure] HTTP", r.status, body)
                    return None
                try:
                    j = await r.json()
                    return j.get("DisplayText")
                except Exception as e:
                    print("[STT azure] JSON error:", e)
                    return None
    except Exception as e:
        print("[STT azure] Exception:", e)
        return None
