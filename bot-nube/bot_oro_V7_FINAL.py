import yfinance as yf, pandas as pd, pandas_ta as ta, time, requests, json, os
from datetime import datetime, timedelta
import pytz

TOKEN = "8041810198:AAFdZRH4DunmMlUkJTwWFuhIdPbPLe-QhSc"
CHAT_ID = "6560153830"
SYMBOL = "GC=F"
COOLDOWN = 300
ARCHIVO_CONTEO = "conteo_diario.json"

ultima_vela = None
ultimo_envio = 0
ultimo_heartbeat = time.time()

# --- CONTEO DIARIO ---
def cargar_conteo():
    if os.path.exists(ARCHIVO_CONTEO):
        try:
            with open(ARCHIVO_CONTEO, 'r') as f: return json.load(f)
        except: pass
    return {"fecha": datetime.now(pytz.timezone('America/Mexico_City')).strftime("%Y-%m-%d"), "ganadas": 0, "perdidas": 0}

def guardar_conteo(data):
    try:
        with open(ARCHIVO_CONTEO, 'w') as f: json.dump(data, f)
    except: pass

conteo = cargar_conteo()

def send_tg(msg):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

def get_precio():
    try:
        df = yf.download(SYMBOL, period="1d", interval="1m", progress=False)
        df.columns = df.columns.get_level_values(0) if isinstance(df.columns, pd.MultiIndex) else df.columns
        return float(df['Close'].iloc[-1])
    except: return None

def verificar(s,e,a):
    if not a: return "Error"
    return "✅ GANADA" if (a>e and s=="CALL") or (a<e and s=="PUT") else "❌ PERDIDA"

def es_hora_noticias():
    tz = pytz.timezone('America/Mexico_City')
    ahora = datetime.now(tz)
    h = ahora.hour + ahora.minute/60.0
    zonas = [(6.25, 6.75), (7.25, 7.75), (8.25, 8.75), (12.0, 12.5)] 
    for i,f in zonas:
        if i <= h <= f: return True, f"Noticia USD {int(i)}h"
    return False, ""

def crear_mensaje(senal, precio, adx, rsi, score, motivos, sop, res):
    tz = pytz.timezone('America/Mexico_City')
    ahora = datetime.now(tz)
    bloque = "🟩🟩🟩 C O M P R A 🟩🟩🟩\n      ⬆️⬆️⬆️ CALL ⬆️⬆️⬆️" if senal=="CALL" else "🟥🟥🟥 V E N T A 🟥🟥🟥\n      ⬇️⬇️⬇️ PUT ⬇️⬇️⬇️"
    apto_1m = "✅ SI" if adx>=24 and (rsi<=33 or rsi>=67) else "❌ NO"
    apto_3m = "✅ SI" if adx>=22 else "⚠️ SOLO 5M"
    nivel = sop if senal=="CALL" else res
    dist = abs(precio-nivel)/precio*100
    modo = "TENDENCIA" if adx>=22 else "LATERAL"
    return f"━━━━━━━━━━━━━━━━━━━━━━━\n🔥 XAUUSD 🥇 {score}/6 {modo} 🔥\n━━━━━━━━━━━━━━━━━━━━━━━\n{bloque}\n━━━━━━━━━━━━━━━━━━━━━━━\n\n💰 Precio: ${precio:.2f}\n📍 {'SOP' if senal=='CALL' else 'RES'} ${nivel:.2f} ({dist:.3f}% cerca)\n📊 ADX: {adx:.1f} | RSI: {rsi:.1f} | Score: {score}/6\n\n📝 {' | '.join(motivos)}\n\n⏰ {ahora.strftime('%I:%M:%S %p')} Saltillo\n🚪 Entra ANTES de: {(ahora+timedelta(seconds=70)).strftime('%I:%M:%S %p')}\n🎯 Expira: {(ahora+timedelta(minutes=5)).strftime('%I:%M:%S %p')} (5M)\n\n⏱️ 1M: {apto_1m} | 3M: {apto_3m} | 5M: ✅ PRINCIPAL\n📊 Hoy: {conteo['ganadas']}G - {conteo['perdidas']}P"

def analizar():
    df_5m = yf.download(SYMBOL, period="5d", interval="5m", progress=False)
    df_15m = yf.download(SYMBOL, period="5d", interval="15m", progress=False)
    df_5m.columns = df_5m.columns.get_level_values(0) if isinstance(df_5m.columns, pd.MultiIndex) else df_5m.columns
    df_15m.columns = df_15m.columns.get_level_values(0) if isinstance(df_15m.columns, pd.MultiIndex) else df_15m.columns
    if len(df_5m)<200: return None,0,0,"",[],0,0,0
    df_5m['EMA9']=ta.ema(df_5m['Close'],9); df_5m['EMA21']=ta.ema(df_5m['Close'],21); df_5m['EMA50']=ta.ema(df_5m['Close'],50)
    df_5m['RSI']=ta.rsi(df_5m['Close'],14)
    bb=ta.bbands(df_5m['Close'],20,2); df_5m['BB_L']=bb.iloc[:,0]; df_5m['BB_U']=bb.iloc[:,2]
    adx_df=ta.adx(df_5m['High'],df_5m['Low'],df_5m['Close'],14); df_5m=pd.concat([df_5m,adx_df],axis=1)
    df_5m['SOP']=df_5m['Low'].rolling(25).min(); df_5m['RES']=df_5m['High'].rolling(25).max(); df_5m['ATR']=ta.atr(df_5m['High'],df_5m['Low'],df_5m['Close'],14)
    df_15m['EMA21']=ta.ema(df_15m['Close'],21); df_15m['EMA50']=ta.ema(df_15m['Close'],50)
    last=df_5m.iloc[-1]; last15=df_15m.iloc[-1]
    if (last['ATR']/last['Close']*100) < 0.03: return None,last['Close'],last['ADX_14'],last['RSI'],str(df_5m.index[-1]),[],0,last['SOP'],last['RES']
    if last['ADX_14'] < 22:
        sc=0; sp=0; mot=["LATERAL"]
        if last['Close'] <= last['BB_L']*1.003 and last['RSI'] <= 38: sc+=2; mot.append(f"BB_Suelo RSI{last['RSI']:.0f}")
        if abs(last['Close']-last['SOP'])/last['Close']*100 < 0.22: sc+=1; mot.append("SOP cerca")
        if last['Close'] >= last['BB_U']*0.997 and last['RSI'] >= 62: sp+=2; mot.append(f"BB_Techo RSI{last['RSI']:.0f}")
        if abs(last['Close']-last['RES'])/last['Close']*100 < 0.22: sp+=1; mot.append("RES cerca")
        if sc>=3: return "CALL",last['Close'],last['ADX_14'],last['RSI'],str(df_5m.index[-1]),mot,sc,last['SOP'],last['RES']
        if sp>=3: return "PUT",last['Close'],last['ADX_14'],last['RSI'],str(df_5m.index[-1]),mot,sp,last['SOP'],last['RES']
        return None,last['Close'],last['ADX_14'],last['RSI'],str(df_5m.index[-1]),mot,0,last['SOP'],last['RES']
    sc=0; sp=0; mot=[]
    if last['Close']>last15['EMA21'] and last15['EMA21']>last15['EMA50']: sc+=1; mot.append("Tend ALC")
    elif last['Close']<last15['EMA21'] and last15['EMA21']<last15['EMA50']: sp+=1; mot.append("Tend BAJ")
    else: return None,last['Close'],last['ADX_14'],last['RSI'],str(df_5m.index[-1]),[],0,last['SOP'],last['RES']
    if last['EMA9']>last['EMA21']>last['EMA50']: sc+=1; mot.append("EMAs CALL")
    elif last['EMA9']<last['EMA21']<last['EMA50']: sp+=1; mot.append("EMAs PUT")
    else: return None,last['Close'],last['ADX_14'],last['RSI'],str(df_5m.index[-1]),[],0,last['SOP'],last['RES']
    if last['ADX_14']>=22 and last['DMP_14']>last['DMN_14']: sc+=1; mot.append(f"ADX {last['ADX_14']:.1f}")
    elif last['ADX_14']>=22 and last['DMN_14']>last['DMP_14']: sp+=1; mot.append(f"ADX {last['ADX_14']:.1f}")
    else: return None,last['Close'],last['ADX_14'],last['RSI'],str(df_5m.index[-1]),[],0,last['SOP'],last['RES']
    if 38<=last['RSI']<=58 and sc>0: sc+=1; mot.append(f"RSI {last['RSI']:.0f}")
    elif 42<=last['RSI']<=62 and sp>0: sp+=1; mot.append(f"RSI {last['RSI']:.0f}")
    if abs(last['Close']-last['SOP'])/last['Close']*100<0.25 and sc>sp: sc+=1; mot.append("SOP")
    elif abs(last['Close']-last['RES'])/last['Close']*100<0.25 and sp>sc: sp+=1; mot.append("RES")
    if sc>=4: return "CALL",last['Close'],last['ADX_14'],last['RSI'],str(df_5m.index[-1]),mot,sc,last['SOP'],last['RES']
    elif sp>=4: return "PUT",last['Close'],last['ADX_14'],last['RSI'],str(df_5m.index[-1]),mot,sp,last['SOP'],last['RES']
    else: return None,last['Close'],last['ADX_14'],last['RSI'],str(df_5m.index[-1]),mot,0,last['SOP'],last['RES']

print("BOT V14 CON CONTEO INICIADO")
send_tg(f"✅ Bot V14 iniciado\n📊 Hoy: {conteo['ganadas']}G - {conteo['perdidas']}P")

while True:
    try:
        tz = pytz.timezone('America/Mexico_City')
        ahora_dt = datetime.now(tz)
        # Reset conteo diario a medianoche
        fecha_hoy = ahora_dt.strftime("%Y-%m-%d")
        if conteo['fecha'] != fecha_hoy:
            if conteo['ganadas']+conteo['perdidas']>0:
                total=conteo['ganadas']+conteo['perdidas']
                eff=conteo['ganadas']/total*100 if total>0 else 0
                send_tg(f"📊 RESUMEN {conteo['fecha']}\n✅ Ganadas: {conteo['ganadas']}\n❌ Perdidas: {conteo['perdidas']}\n📈 Efectividad: {eff:.1f}%")
            conteo = {"fecha": fecha_hoy, "ganadas": 0, "perdidas": 0}
            guardar_conteo(conteo)

        peligro, detalle = es_hora_noticias()
        if peligro:
            if time.time() - ultimo_heartbeat > 1800:
                send_tg(f"⏸️ Pausa por {detalle}")
                ultimo_heartbeat = time.time()
            time.sleep(60); continue

        senal,precio,adx,rsi,hora,mot,score,sop,res=analizar()
        ahora_t=time.time()
        print(f"{ahora_dt.strftime('%H:%M:%S')} | ${precio:.2f} ADX {adx:.1f} Score {score} Hoy {conteo['ganadas']}G-{conteo['perdidas']}P")

        if ahora_t - ultimo_heartbeat > 1800 and not senal:
            send_tg(f"🔎 Sigo buscando... ADX {adx:.1f} RSI {rsi:.1f}\n📊 Hoy: {conteo['ganadas']}G - {conteo['perdidas']}P")
            ultimo_heartbeat = ahora_t

        if hora==ultima_vela or (ahora_t-ultimo_envio<COOLDOWN): time.sleep(15); continue
        
        if senal:
            send_tg(crear_mensaje(senal,precio,adx,rsi,score,mot,sop,res))
            ent=precio
            time.sleep(75); p1=get_precio(); 
            if p1: send_tg(f"⏱️ 1M {senal} ${ent:.2f}->${p1:.2f} : {verificar(senal,ent,p1)}")
            time.sleep(115); p3=get_precio();
            if p3: send_tg(f"⏱️ 3M {senal} ${ent:.2f}->${p3:.2f} : {verificar(senal,ent,p3)}")
            time.sleep(125); p5=get_precio();
            if p5:
                res_final = verificar(senal,ent,p5)
                send_tg(f"🏁 5M FINAL {senal} ${ent:.2f}->${p5:.2f} : {res_final}")
                # CONTEO
                if "GANADA" in res_final: conteo['ganadas'] += 1
                else: conteo['perdidas'] += 1
                guardar_conteo(conteo)
                send_tg(f"📊 Actual Hoy: {conteo['ganadas']}G - {conteo['perdidas']}P")
            ultima_vela=hora; ultimo_envio=time.time(); ultimo_heartbeat=time.time()
        else:
            time.sleep(15)
    except Exception as e:
        print(f"Error {e}"); time.sleep(20)
