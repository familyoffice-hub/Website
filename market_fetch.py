# -*- coding: utf-8 -*-
"""
Ambil data Index Bursa (Yahoo Finance) + Currency (open.er-api.com) dari sisi server
(GitHub Actions, bebas CORS), lalu tulis ke market.json. Dibaca oleh ticker website.
Tidak butuh API key. Hanya commit bila ada perubahan data.
"""
import json, os, time, urllib.parse, urllib.request

INDICES = [
    ("^JKSE", "IHSG"), ("^GSPC", "S&P 500"), ("^NDX", "NASDAQ 100"), ("^DJI", "DJIA"),
    ("^FTSE", "FTSE 100"), ("^N225", "NIKKEI 225"), ("^GDAXI", "DAX 40"), ("^STOXX50E", "STOXX 50"),
    ("^FCHI", "CAC 40"), ("^HSI", "HSI"), ("000001.SS", "SHANGHAI"), ("^KS11", "KOSPI"),
    ("^TWII", "TAIWAN"), ("^NSEI", "NIFTY 50"), ("^BSESN", "SENSEX"), ("^STI", "STI"),
    ("^KLSE", "KLCI"), ("^SET.BK", "SET"), ("PSEI.PS", "PSEi"),
]
FX = [("USD/IDR", "USD", "IDR"), ("EUR/USD", "EUR", "USD"),
      ("USD/JPY", "USD", "JPY"), ("GBP/USD", "GBP", "USD")]

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_index(sym):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(sym) + "?interval=1d&range=2d")
    for attempt in range(3):
        try:
            m = get_json(url)["chart"]["result"][0]["meta"]
            price = m.get("regularMarketPrice")
            prev = m.get("chartPreviousClose") or m.get("previousClose")
            chg = round((price - prev) / prev * 100, 2) if (price and prev) else None
            return (round(price, 2) if price else None), chg
        except Exception as e:
            if attempt == 2:
                print("  [!] gagal", sym, "->", e)
            time.sleep(2)
    return None, None


def fetch_fx():
    try:
        rates = get_json("https://open.er-api.com/v6/latest/USD").get("rates", {})
    except Exception as e:
        print("  [!] FX gagal:", e); rates = {}
    out = []
    for pair, base, quote in FX:
        if base == "USD":
            v = rates.get(quote)
        elif quote == "USD":
            v = (1 / rates[base]) if rates.get(base) else None
        else:
            v = (rates[quote] / rates[base]) if (rates.get(quote) and rates.get(base)) else None
        out.append({"pair": pair, "price": (round(v, 4) if v else None)})
    return out


def main():
    indices = []
    for sym, label in INDICES:
        p, c = fetch_index(sym)
        indices.append({"s": label, "price": p, "chg": c})
        print(f"  {label:12s} {p} ({c})")
        time.sleep(0.3)
    fx = fetch_fx()

    new_core = {"indices": indices, "fx": fx}

    old = None
    if os.path.exists("market.json"):
        try:
            old = json.load(open("market.json", encoding="utf-8"))
        except Exception:
            old = None
    if old and {"indices": old.get("indices"), "fx": old.get("fx")} == new_core:
        print("[i] Data sama dengan sebelumnya -> tidak menulis ulang (tidak ada commit).")
        return

    out = {"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **new_core}
    with open("market.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    ok = sum(1 for x in indices if x["price"] is not None)
    print(f"[i] market.json diperbarui: {ok}/{len(indices)} index, {len(fx)} currency.")


if __name__ == "__main__":
    main()
