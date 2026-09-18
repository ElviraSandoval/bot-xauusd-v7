import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time
import requests
from datetime import datetime, timedelta
import pytz

TOKEN = "8041810198:AAFdZRH4DunmMlUkJTwWFuhIdPbPLe-QhSc"
CHAT_ID = "6560153830"
SYMBOL = "GC=F"
COOLDOWN = 300

ultima_vela = None
ultimo_envio = 0

def send_tg(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"Error TG: {e}")

def crear_mensaje_pro(senal, precio, adx, rsi, score, motivos, soporte):
    tz = pytz.timezone('America/Mexico_City')
    ahora = datetime.now(tz)
    entra_antes = (ahora + timedelta(seconds=70)).strftime("%I:%M:%S %p")
    expira = (ahora + timedelta(minutes=5)).strftime("%I:%M:%S %p")
    hora_saltillo = ahora.strftime("%I:%M:%S %p")
    if senal == "CALL":
        bloque = "🟩🟩🟩 C O M P R A 🟩🟩🟩\n      ⬆️⬆️⬆️ CALL ⬆️⬆️⬆️\n🟩🟩🟩 C O M P R A 🟩🟩🟩"
    else:
        bloque = "🟥🟥🟥 V E N T A 🟥🟥🟥\n      ⬇️⬇️⬇️ PUT ⬇️⬇️⬇️\n🟥🟥🟥 V E N T A 🟥🟥🟥"
    dist_soporte = abs(precio - soporte) / precio * 100
    msg = f"━━━━━━━━━━━━━━━━━━━━━━━\n🔥 XAUUSD 🥇 {score}/4 FUERTE 🔥\n━━━━━━━━━━━━━━━━━━━━━━━\n{bloque}\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"💰 Precio: ${precio:.2f}\n📍 Soporte: ${soporte:.2f} ({dist_soporte:.2f}% cerca)\n📊 ADX: {adx:.1f} | RSI: {rsi:.1f}\n⭐ Calidad: {score}/4\n\n"
    msg += f"📝 Motivos: " + " | ".join(motivos) + f"\n\n⏰ Saltillo: {hora_saltillo}\n🚪 Entra ANTES de: {entra_antes}\n🎯 Expira: {expira} (5M)"
    return msg

def analizar():
    df_5m = yf.download(SYMBOL, period="2d", interval="5m", progress=False)
    df_15m = yf.download(SYMBOL, period="5d", interval="15m", progress=False)
    df_5m.columns = df_5m.columns.get_level_values(0) if isinstance(df_5m.columns, pd.MultiIndex) else df_5m.columns
    df_15m.columns = df_15m.columns.get_level_values(0) if isinstance(df_15m.columns, pd.MultiIndex) else df_15m.columns

    df_5m['EMA9'] = ta.ema(df_5m['Close'], length=9)
    df_5m['EMA21'] = ta.ema(df_5m['Close'], length=21)
    df_5m['EMA50'] = ta.ema(df_5m['Close'], length=50)
    df_5m['RSI'] = ta.rsi(df_5m['Close'], length=14)
    
    # --- CORRECCION DEL ERROR BBU ---
    bb = ta.bbands(df_5m['Close'], length=20, std=2)
    # Esto agarra las columnas sin importar como se llamen
    df_5m['BB_LOW'] = bb.iloc[:,0]
    df_5m['BB_MID'] = bb.iloc[:,1]
    df_5m['BB_UP'] = bb.iloc[:,2]
    # --- FIN CORRECCION ---

    adx_df = ta.adx(df_5m['High'], df_5m['Low'], df_5m['Close'], length=14)
    df_5m = pd.concat([df_5m, adx_df], axis=1)
    df_5m['SOPORTE'] = df_5m['Low'].rolling(20).min()
    df_15m['EMA21'] = ta.ema(df_15m['Close'], length=21)
    
    last = df_5m.iloc[-1]
    last_15 = df_15m.iloc[-1]
    hora_vela = str(df_5m.index[-1])
    score_call = 0
    score_put = 0
    motivos = []

    if last['Close'] > last_15['EMA21']:
        score_call += 1
        motivos.append("Tendencia 15M Alcista")
    else:
        score_put += 1
        motivos.append("Tendencia 15M Bajista")

    if last['EMA9'] > last['EMA21'] > last['EMA50']:
        score_call += 1
        motivos.append("EMAs CALL")
    elif last['EMA9'] < last['EMA21'] < last['EMA50']:
        score_put += 1
        motivos.append("EMAs PUT")

    if last['ADX_14'] > 18:
        if last['DMP_14'] > last['DMN_14']:
            score_call += 1
            motivos.append(f"ADX {last['ADX_14']:.1f} + DI+")
        else:
            score_put += 1
            motivos.append(f"ADX {last['ADX_14']:.1f} + DI-")

    if last['RSI'] < 38 and last['Close'] <= last['BB_LOW']:
        score_call += 2
        motivos.append(f"RSI {last['RSI']:.1f} + Rebote BB")
    elif last['RSI'] > 62 and last['Close'] >= last['BB_UP']:
        score_put += 2
        motivos.append(f"RSI {last['RSI']:.1f} + Rechazo BB")
    
    soporte = last['SOPORTE']
    if score_call >= 3:
        return "CALL", last['Close'], last['ADX_14'], last['RSI'], hora_vela, motivos, score_call, soporte
    elif score_put >= 3:
        return "PUT", last['Close'], last['ADX_14'], last['RSI'], hora_vela, motivos, score_put, soporte
    else:
        return None, last['Close'], last['ADX_14'], last['RSI'], hora_vela, motivos, 0, soporte

print("BOT V10.1 PRO INICIADO - ERROR BBU CORREGIDO")

while True:
    try:
        senal, precio, adx, rsi, hora_vela, motivos, score, soporte = analizar()
        ahora = time.time()
        print(f"{datetime.now().strftime('%H:%M:%S')} | {precio:.2f} | ADX {adx:.1f} | Score {score}")
        if hora_vela == ultima_vela or (ahora - ultimo_envio < COOLDOWN):
            time.sleep(10)
            continue
        if senal:
            msg = crear_mensaje_pro(senal, precio, adx, rsi, score, motivos, soporte)
            send_tg(msg)
            print(f"!!! SEÑAL {senal} ENVIADA !!!")
            ultima_vela = hora_vela
            ultimo_envio = ahora
            time.sleep(COOLDOWN)
        else:
            time.sleep(15)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(20)
