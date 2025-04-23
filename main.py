
from keep_alive import keep_alive
keep_alive()

import time
import pytz
import pandas as pd
import requests
from datetime import datetime
from telegram import Bot, ParseMode
from telegram.error import TelegramError

# === Telegram Ayarları ===
TOKEN = "7534683921:AAHVRAJpK6_gA-48kAcD_dz8ChYFeaaEF8o"
CHAT_ID = "923087333"
bot = Bot(token=TOKEN)

# === Coin Ayarları ===
SYMBOL = "BTCUSDT"
INTERVAL = "15m"
LIMIT = 100

# === Binance verisi çek ===
def get_klines(symbol=SYMBOL, interval=INTERVAL, limit=LIMIT):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["close"] = df["close"].astype(float)
    return df

# === Göstergeler Hesapla ===
def calculate_indicators(df):
    df["ema_9"] = df["close"].ewm(span=9).mean()
    df["ema_21"] = df["close"].ewm(span=21).mean()
    df["rsi"] = 100 - (100 / (1 + df["close"].pct_change().rolling(14).mean()))
    df["macd"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    df["adx"] = df["close"].diff().abs().rolling(14).mean()
    return df

# === Güçlü Sinyal Skoru Hesapla ===
def calculate_score(row):
    score = 0
    if row["rsi"] < 30:
        score += 2
    elif row["rsi"] > 70:
        score += 2

    if row["ema_9"] > row["ema_21"]:
        score += 2
    elif row["ema_9"] < row["ema_21"]:
        score += 2

    if row["macd"] > row["macd_signal"]:
        score += 2
    elif row["macd"] < row["macd_signal"]:
        score += 2

    if row["adx"] > 1.5:
        score += 2

    return score

# === Türkiye Saatini Al ===
def get_time():
    turkey_time = datetime.now(pytz.timezone("Europe/Istanbul"))
    return turkey_time.strftime("%d.%m.%Y • %H:%M")

# === Telegram Sinyal Gönder ve TP Takibi ===
def send_signal(signal, price, score):
    zaman = get_time()
    tp1 = round(price * 1.005, 2)
    tp2 = round(price * 1.01, 2)
    tp3 = round(price * 1.015, 2)
    tp4 = round(price * 1.02, 2)
    tp5 = round(price * 1.025, 2)

    msg = f"📊 *Ultra Ultimate 3.2 Sinyali*\n\n"           f"*Coin:* {SYMBOL}\n"           f"*Yön:* {signal}\n"           f"*Skor:* {score}/10\n"           f"*Giriş:* {price}\n"           f"*TP1:* {tp1}\n*TP2:* {tp2}\n*TP3:* {tp3}\n*TP4:* {tp4}\n*TP5:* {tp5}\n"           f"*Zaman:* {zaman}"

    sent = bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
    return sent.message_id, [tp1, tp2, tp3, tp4, tp5]

def update_message(message_id, price, tps, signal, score):
    check = ["⬜", "⬜", "⬜", "⬜", "⬜"]
    for i, tp in enumerate(tps):
        if (signal == "LONG" and price >= tp) or (signal == "SHORT" and price <= tp):
            check[i] = "✅"
    zaman = get_time()
    new_text = f"📊 *Ultra Ultimate 3.2 Sinyali*\n\n"                f"*Coin:* {SYMBOL}\n"                f"*Yön:* {signal}\n"                f"*Skor:* {score}/10\n"                f"*Güncel Fiyat:* {price}\n"                f"{check[0]} TP1: {tps[0]}\n{check[1]} TP2: {tps[1]}\n{check[2]} TP3: {tps[2]}\n"                f"{check[3]} TP4: {tps[3]}\n{check[4]} TP5: {tps[4]}\n"                f"*Zaman:* {zaman}"
    try:
        bot.edit_message_text(chat_id=CHAT_ID, message_id=message_id, text=new_text, parse_mode=ParseMode.MARKDOWN)
    except TelegramError as e:
        print("Telegram güncelleme hatası:", e)

# === Çalışma Döngüsü ===
def run_bot():
    while True:
        df = get_klines()
        df = calculate_indicators(df)
        row = df.iloc[-1]
        score = calculate_score(row)
        current_price = row["close"]

        if score >= 8:
            signal = "LONG" if row["ema_9"] > row["ema_21"] else "SHORT"
            message_id, tps = send_signal(signal, current_price, score)

            for _ in range(30):
                price = get_klines().iloc[-1]["close"]
                update_message(message_id, price, tps, signal, score)
                time.sleep(60)

        time.sleep(60)
run_bot()
