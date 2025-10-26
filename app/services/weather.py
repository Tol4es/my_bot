import requests
from ..config import settings

def fetch_weather(city: str) -> str:
    if not settings.owm_key:
        return "Не задано OWM_API_KEY. Додай ключ OpenWeather у змінну середовища."
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params = {"q": city, "appid": settings.owm_key, "units": "metric", "lang": "uk"},
            timeout = 10,
        )
        if r.status_code != 200:
            return f"Не вдалось отримати погоду для «{city}». Код: {r.status_code}"
        data = r.json()
        name = data.get("name", city)
        main = (data.get("weather", [{}])[0].get("description") or "").capitalize()
        t = data.get("main", {}).get("temp")
        feels = data.get("main", {}).get("feels_like")
        hum = data.get("main", {}).get("humidity")
        wind = data.get("wind", {}).get("speed")
        return (
            f"⛅ Погода в {name}: {main}\n"
            f"🌡️ Темп: {t}°С (відчувається як {feels}°C)\n"
            f"💧 Вологість: {hum}%\n"
            f"💨 Вітер: {wind} м/с"
        )
    except Exception as e:
        return f"Помилка запиту погоди: {e}"