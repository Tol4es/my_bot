import re
import requests
from deep_translator import GoogleTranslator
from ..config import settings

UA_RE = re.compile(r"[а-щьюяєіїґА-ЩЬЮЯЄІЇҐ]")
_SIGN_CODES = {"aries","taurus","gemini","cancer","leo","virgo","libra","scorpio","sagittarius","capricorn","aquarius","pisces"}

def _tr_desc(text_en: str) -> str:
    if UA_RE.search(text_en or ""):
        return text_en or "Без опису."
    try:
        return GoogleTranslator(source="en", target="uk").translate(text_en or "") or "Без опису."
    except Exception:
        return text_en or "Без опису."

def _sanitize_sign(s: str) -> str:
    return re.sub(r'[^a-z]', '', (s or '').lower())

def fetch_horoscope(zodiac: str) -> str:
    sign = _sanitize_sign(zodiac)
    if sign not in _SIGN_CODES:
        return "Не вказано знак зодіаку."
    if not settings.ninjas_key:
        return "Не задано NINJAS_API_KEY. Додай ключ у змінну середовища."
    try:
        r = requests.get(
            "https://api.api-ninjas.com/v1/horoscope",
            params={"zodiac": sign},
            headers={"X-Api-Key": settings.ninjas_key, "Accept": "application/json"},
            timeout=12,
        )
        if r.status_code != 200:
            return f"Сервіс гороскопів недоступний (код {r.status_code}). Спробуй пізніше."
        raw_desc = (r.json().get("horoscope") or "").strip()
        if not raw_desc:
            return "Постачальник не повернув опис. Спробуй пізніше."
        ua_text = _tr_desc(raw_desc)
        return f"🌌 Гороскоп на сьогодні ({sign}):\n{ua_text}"
    except Exception as e:
        return f"Помилка запиту гороскопу: {e}"
