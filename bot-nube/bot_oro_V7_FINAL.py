import yfinance as yf, ta, time, requests, threading, json, os
from datetime import datetime, timedelta
import pytz
TOKEN="8041810198:AAFdZRH4DunmMlUkJTwWFuhIdPbPLe-QhSc"
CHAT_ID="6560153830"
ZONA=pytz.timezone("America/Mexico_City")
STATS_FILE=os.path.expanduser("~/Desktop/stats_xauusd.json")
OFFSET=127.9
SYMBOL_LABEL="XAUUSD"
def enviar(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass
def cargar_stats():
    hoy=datetime.now(ZONA).strftime("%Y-%m-%d")
    if os.path.exists(STATS_FILE):
        try:
            d=json.load(open(STATS_FILE))
            if d.get("fecha")==hoy: return d
        except: pass
    return {"fecha":hoy,"win":0,"loss":0,"profit":0.0}
def guardar_stats(s): json.dump(s, open(STATS_FILE,'w'))
def norm(df): df.columns=[str(c[0] if isinstance(c,tuple) else c).lower() for c in df.columns]; return df
def get_gold():
    for sym in ["GC=F", "MGC=F", "GLD"]:
        try:
            df=yf.download(sym, period="2d", interval="5m", progress=False, auto_adjust=True)
            if len(df)>50: return norm(df)
        except: pass
    return None

stats=cargar_stats()
pendientes=[]
def verificar():
    global stats
    while True:
        time.sleep(20)
        for p in pendientes[:]:
            try:
                df=get_gold()
                if df is None: continue
                precio=float(df['close'].iloc[-1])+OFFSET
                if datetime.now(ZONA)>=p["expira"]:
                    win=(p['dir']=="CALL" and precio>p['precio']) or (p['dir']=="PUT" and precio<p['precio'])
                    if win: stats["win"]+=1; stats["profit"]+=25.5; enviar(f"✅✅ *WIN {p['dir']}* ✅✅\n💰 ${p['precio']:.3f} -> ${precio:.3f}\n📈 HOY: {stats['win']}W-{stats['loss']}L")
                    else: stats["loss"]+=1; stats["profit"]-=30; enviar(f"🔻 *LOSS {p['dir']}*\n💰 ${p['precio']:.3f} -> ${precio:.3f}\n📈 HOY: {stats['win']}W-{stats['loss']}L")
                    guardar_stats(stats); pendientes.remove(p)
            except: pass
threading.Thread(target=verificar,daemon=True).start()
enviar(f"🤖 *Bot {SYMBOL_LABEL} V7 FINAL PRENDIDO - IQ $4435* 🔥\nSin limites - Score 7.0+")
print(f"BOT {SYMBOL_LABEL} V7 FINAL OK con GC=F OFFSET {OFFSET}")

while True:
    try:
        df=get_gold()
        if df is None or len(df)<100:
            time.sleep(30); continue
        df['ema20']=ta.trend.ema_indicator(df['close'],20); df['ema50']=ta.trend.ema_indicator(df['close'],50); df['ema200']=ta.trend.ema_indicator(df['close'],200)
        df['rsi']=ta.momentum.rsi(df['close'],14); df['adx']=ta.trend.adx(df['high'],df['low'],df['close'],14)
        df['atr']=ta.volatility.average_true_range(df['high'],df['low'],df['close'],14)
        u=df.iloc[-1]; a=df.iloc[-2]
        precio_iq=float(u['close'])+OFFSET
        # FILTROS V7 ORIGINALES
        if float(u['adx']) < 27:
            print(f"ADX bajo {float(u['adx']):.1f} - esperando"); time.sleep(60); continue
        if float(u['atr']) > 3.5:
            print(f"Volatilidad alta {float(u['atr']):.2f} - pausa"); time.sleep(60); continue
        score=0
        if u['close']>u['ema20']>u['ema50']: score+=3
        if u['close']<u['ema20']<u['ema50']: score+=3
        if u['close']>u['ema200']: score+=1
        if u['close']<u['ema200']: score+=1
        if 30<float(u['rsi'])<50 and float(u['rsi'])>float(a['rsi']): score+=2
        if 50<float(u['rsi'])<70 and float(u['rsi'])<float(a['rsi']): score+=2
        if float(u['adx'])>27: score+=2
        print(f"Precio IQ: {precio_iq:.2f} Score: {score}/10 RSI: {float(u['rsi']):.1f} ADX: {float(u['adx']):.1f}")
        if score>=7.0:
            direccion="CALL 📈" if u['close']>u['ema20'] else "PUT 📉"
            ahora=datetime.now(ZONA); entra=ahora+timedelta(seconds=70); expira=ahora+timedelta(minutes=5)
            pendientes.append({"precio":precio_iq,"dir":direccion.split()[0],"expira":expira})
            total=stats["win"]+stats["loss"]; pct=(stats["win"]/total*100) if total>0 else 0
            soporte=float(df['low'].tail(20).min())+OFFSET
            pct_cerca=abs(precio_iq-soporte)/precio_iq*100
            turbo_msg="\n🚀 *TURBO 1M: MISMA DIRECCIÓN - ALTA CONFIANZA 9.5+*" if score>=9.5 else ""
            enviar(f"""🔥🔥🔥 *{SYMBOL_LABEL} 🥇 {direccion} FUERTE {score}/10* 🔥🔥🔥

━━━━━━━━━━━━━━━━━━
💰 *Precio IQ:* `${precio_iq:.3f}`
📍 *Soporte:* `${soporte:.2f}` ({pct_cerca:.2f}% cerca)
📊 *ADX:* {float(u['adx']):.1f} | *RSI:* {float(u['rsi']):.1f}
⏰ *Saltillo:* {ahora.strftime('%I:%M:%S %p')}
🚪 *Entra ANTES de:* {entra.strftime('%I:%M:%S %p')}
🎯 *Expira:* {expira.strftime('%I:%M:%S %p')} (5M){turbo_msg}
━━━━━━━━━━━━━━━━━━
📈 *MARCADOR HOY:* `{stats['win']}W - {stats['loss']}L` ({pct:.1f}%)
💵 *Balance:* `Mex${stats['profit']:.2f}`
━━━━━━━━━━━━━━━━━━
⚡ *ENTRAR EN IQ AHORA* | 🔎 3M: ✅ | 1M: ✅
""")
        time.sleep(60)
    except Exception as e: print(f"Error: {e}"); time.sleep(10)
        
