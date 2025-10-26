import time
import requests
from typing import Dict, Any, Optional, List

ISO_TO_MONO = {"USD": 840, "EUR": 978, "PLN": 985, "UAH": 980}
FX_SUPPORTED = ["USD", "EUR", "PLN"]
_CCY_EMOJI = {"USD": "💵", "EUR": "💶", "PLN": "🇵🇱"}
FX_CACHE_TTL = 180
_FX_CACHE: dict = {"mono": {"ts": 0.0, "data": {}}}


def _fetch_monobank_all() -> Optional[List[Dict[str, Any]]]:
    try:
        r = requests.get("https://api.monobank.ua/bank/currency", timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _format_fx_response(city_label: str, data: Dict[str, tuple], order: List[str], ts: float) -> str:
    age = int(time.time() - ts)
    lines = [f"💱 Курс ({city_label}) — Monobank, ~{age}с тому:"]
    for code in order:
        buy, sell = data.get(code, (None, None))
        emoji = _CCY_EMOJI.get(code, "💱")
        if buy is None and sell is None:
            lines.append(f"{emoji} {code}: немає даних")
        elif buy is not None and sell is not None:
            lines.append(f"{emoji} {code}: 🟢 купівля ~ {buy:.2f} | 🔵 продаж ~ {sell:.2f}")
        elif buy is not None:
            lines.append(f"{emoji} {code}: 🟢 купівля ~ {buy:.2f}")
        else:
            lines.append(f"{emoji} {code}: 🔵 продаж ~ {sell:.2f}")
    return "\n".join(lines)


# -------- helpers --------

def _mid(x: Optional[float], y: Optional[float]) -> Optional[float]:
    """Середина між buy/sell. Якщо є лише одне значення — повертаємо його.
    Якщо немає жодного — None (не рахуємо)."""
    if x is not None and y is not None:
        return (x + y) / 2.0
    return x if x is not None else y


def _pair_mid(pairs: Dict[tuple, Dict[str, float]], a: int, b: int) -> Optional[float]:
    """Середина або cross для пари (a,b)."""
    p = pairs.get((a, b), {})
    return _mid(p.get("buy"), p.get("sell")) or p.get("rate") or p.get("cross")


def _direct_pair(pairs: Dict[tuple, Dict[str, float]], code_iso: str) -> tuple[Optional[float], Optional[float]]:
    """Повертає (buy, sell) або (x, x) із cross для code/UAH, або (None,None)."""
    A = ISO_TO_MONO[code_iso]
    UAH = ISO_TO_MONO["UAH"]
    p = pairs.get((A, UAH))
    if p and (p.get("buy") is not None or p.get("sell") is not None):
        return p.get("buy"), p.get("sell")
    if p and p.get("cross") is not None:
        x = p["cross"]
        return x, x
    return None, None


def _via_cross_pln(pairs: Dict[tuple, Dict[str, float]]) -> Optional[tuple[float, float]]:
    """Оцінимо PLN/UAH через USD/UAH або EUR/UAH, якщо прямої пари нема."""
    PLN = ISO_TO_MONO["PLN"]; USD = ISO_TO_MONO["USD"]; EUR = ISO_TO_MONO["EUR"]; UAH = ISO_TO_MONO["UAH"]

    usd_mid = _pair_mid(pairs, USD, UAH)
    if usd_mid:
        p_pln_usd = pairs.get((PLN, USD), {})
        if p_pln_usd.get("cross"):
            val = p_pln_usd["cross"] * usd_mid
            return val, val
        p_usd_pln = pairs.get((USD, PLN), {})
        if p_usd_pln.get("cross") and p_usd_pln["cross"] > 0:
            val = (1.0 / p_usd_pln["cross"]) * usd_mid
            return val, val

    eur_mid = _pair_mid(pairs, EUR, UAH)
    if eur_mid:
        p_pln_eur = pairs.get((PLN, EUR), {})
        if p_pln_eur.get("cross"):
            val = p_pln_eur["cross"] * eur_mid
            return val, val
        p_eur_pln = pairs.get((EUR, PLN), {})
        if p_eur_pln.get("cross") and p_eur_pln["cross"] > 0:
            val = (1.0 / p_eur_pln["cross"]) * eur_mid
            return val, val

    return None


# -------- main --------

def parse_monobank(codes: List[str]) -> str:
    want = [c.upper() for c in codes if c.upper() in FX_SUPPORTED]
    if not want:
        return "Не обрано валют."

    # кеш
    now = time.time()
    cache = _FX_CACHE.get("mono", {})
    have = cache.get("data", {})
    if cache and now - cache.get("ts", 0) <= FX_CACHE_TTL and all(c in have for c in want):
        return _format_fx_response("🇺🇦 банки", have, want, cache.get("ts", 0))

    payload = _fetch_monobank_all()
    if not payload:
        if have:
            return _format_fx_response("🇺🇦 банки (кеш)", have, want, cache.get("ts", 0))
        return "Курси тимчасово недоступні."

    # розпарсимо всі пари
    pairs: Dict[tuple, Dict[str, float]] = {}
    for row in payload:
        a = row.get("currencyCodeA"); b = row.get("currencyCodeB")
        if not a or not b:
            continue
        pairs[(a, b)] = {
            "buy": row.get("rateBuy"),
            "sell": row.get("rateSell"),
            "cross": row.get("rateCross"),
        }

    out: Dict[str, tuple] = {}

    # USD, EUR напряму
    for c in ["USD", "EUR"]:
        b, s = _direct_pair(pairs, c)
        if b is None and s is None:
            # інверсія через cross, якщо є UAH->A
            A = ISO_TO_MONO[c]; UAH = ISO_TO_MONO["UAH"]
            rev = pairs.get((UAH, A), {})
            x = rev.get("cross")
            if x and x > 0:
                val = 1.0 / x
                b = b or val
                s = s or val
        if b is not None or s is not None:
            out[c] = (b, s)

    # PLN напряму або через кроси
    b, s = _direct_pair(pairs, "PLN")
    if b is None and s is None:
        via = _via_cross_pln(pairs)
        if via:
            b, s = via
    if b is not None or s is not None:          # ← додаємо лише якщо є дані
        out["PLN"] = (b, s)

    # кешуємо та відповідаємо
    if not out and have:
        return _format_fx_response("🇺🇦 банки (кеш)", have, want, cache.get("ts", 0))

    _FX_CACHE["mono"] = {"ts": now, "data": out}
    return _format_fx_response("🇺🇦 банки", out, want, now)
