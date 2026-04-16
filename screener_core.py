import io, contextlib, os, json, warnings, requests, logging
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from textblob import TextBlob
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

_devnull = open(os.devnull, 'w')

def _silent(func, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(_devnull):
        return func(*args, **kwargs)

# ── CONFIG ──────────────────────────────────────────────────
CAPITAL        = 100_000
MIN_SCORE      = 12
MIN_PRICE      = 50
MIN_MKTCAP_CR  = 500
MIN_RR         = 2.0

TELEGRAM_TOKEN   = ""   # leave blank here — set in .streamlit/secrets.toml
TELEGRAM_CHAT_ID = ""

TRADE_LOG_FILE  = "trade_log.json"
EXIT_WATCH_FILE = "exit_watchlist.json"

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
}

# ── STOCK LISTS ──────────────────────────────────────────────
LARGE_CAP_STOCKS = [
    "HDFCBANK","ICICIBANK","SBIN","AXISBANK","KOTAKBANK","BAJFINANCE",
    "INDUSINDBK","BANDHANBNK","FEDERALBNK","CANBK","PNB","YESBANK",
    "TCS","INFY","WIPRO","HCLTECH","TECHM","LTI",
    "RELIANCE","ONGC","BPCL","IOC","GAIL","MGL",
    "HINDUNILVR","ITC","NESTLEIND","BRITANNIA","DABUR","GODREJCP",
    "SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","BIOCON","TORNTPHARM",
    "MARUTI","TATAMOTORS","M&M","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT",
    "LT","ULTRACEMCO","GRASIM","SHREECEM","AMBUJACEM","ACCIND",
    "JSWSTEEL","TATASTEEL","HINDALCO","VEDL","NATIONALUM","COALINDIA",
    "ADANIENT","ADANIPORTS","ADANIGREEN","ADANIPOWER","ADANITRANS",
    "BHARTIARTL","ASIANPAINT","TITAN","NTPC","POWERGRID","NHPC",
    "BAJAJFINSV","HDFCLIFE","SBILIFE","ICICIPRULI",
]

MID_CAP_STOCKS = [
    "PERSISTENT","LTIM","MPHASIS","COFORGE","KPITTECH","HEXAWARE",
    "OFSS","TATAELXSI","CYIENT","DIXON",
    "ZYDUSLIFE","GLENMARK","LUPIN","NATCOPHARM","GRANULES","AJANTPHARM",
    "APOLLOHOSP","MAXHEALTH","FORTIS","METROPOLIS","THYROCARE",
    "IRFC","JIOFIN","PNBHOUSING","CANFINHOME","MUTHOOTFIN","MANAPPURAM","CHOLAFIN",
    "TVSMOTOR","ASHOKLEY","SONACOMS","MOTHERSON","BOSCHLTD","BHARATFORG",
    "RVNL","IRCON","NBCC","HUDCO","BEL","HAL","COCHINSHIP","MAZAGON","BHEL",
    "TATAPOWER","CESC","SJVN","IREDA","WAAREEENER","INOXWIND","SUZLON",
    "IRCTC","INDHOTEL","VBL","MARICO","PIDILITIND","BERGEPAINT","KANSAINER",
    "ASTRAL","POLYCAB","HAVELLS","VOLTAS","BLUESTAR","CROMPTON","VGUARD",
    "SAIL","NMDC","MOIL","HINDZINC","DEEPAKNTR","AARTIIND","TATACHEM",
    "DMART","TRENT","TITAN","ZOMATO","NYKAA","PAYTM",
]

SMALL_CAP_STOCKS = [
    "DLF","GODREJPROP","PRESTIGE","BRIGADE","OBEROIRLTY","SOBHA",
    "UPL","PI","DHANUKA","RALLIS",
    "VARDHMAN","WELSPUN","TRIDENT","RAYMOND",
    "CONCOR","VRL","BLUEDART",
    "WESTLIFE","JUBLFOOD","DEVYANI",
    "DATAPATTNS","MTAR","SOLARINDS",
    "KAYNES","RAILVIKAS","FINEORG","GALAXYSURF","VINATIORGA","NOCIL",
]

WATCHLIST = list(dict.fromkeys(LARGE_CAP_STOCKS + MID_CAP_STOCKS + SMALL_CAP_STOCKS))

SECTOR_MAP = {
    "HDFCBANK":"Banking","ICICIBANK":"Banking","SBIN":"Banking","AXISBANK":"Banking",
    "KOTAKBANK":"Banking","INDUSINDBK":"Banking","BANDHANBNK":"Banking","FEDERALBNK":"Banking",
    "CANBK":"Banking","PNB":"Banking","YESBANK":"Banking",
    "TATAPOWER":"Power","NHPC":"Power","NTPC":"Power","POWERGRID":"Power",
    "IREDA":"Power","WAAREEENER":"Power","INOXWIND":"Power","SUZLON":"Power",
    "CESC":"Power","SJVN":"Power","ADANIGREEN":"Power","ADANIPOWER":"Power","JSWENERGY":"Power",
    "TATASTEEL":"Metals","SAIL":"Metals","NATIONALUM":"Metals","VEDL":"Metals",
    "JSWSTEEL":"Metals","NMDC":"Metals","MOIL":"Metals","HINDALCO":"Metals","HINDZINC":"Metals",
    "RVNL":"Infra","IRCON":"Infra","NBCC":"Infra","HUDCO":"Infra",
    "RAILVIKAS":"Infra","LT":"Infra","HAL":"Infra","BEL":"Infra","BHEL":"Infra",
    "IRFC":"Finance","BAJFINANCE":"Finance","PNBHOUSING":"Finance","CANFINHOME":"Finance",
    "MUTHOOTFIN":"Finance","MANAPPURAM":"Finance","CHOLAFIN":"Finance",
    "BAJAJFINSV":"Finance","HDFCLIFE":"Finance","SBILIFE":"Finance","ICICIPRULI":"Finance",
    "BPCL":"Oil & Gas","ONGC":"Oil & Gas","GAIL":"Oil & Gas","IOC":"Oil & Gas",
    "RELIANCE":"Oil & Gas","MGL":"Oil & Gas",
    "TCS":"IT","INFY":"IT","WIPRO":"IT","HCLTECH":"IT","TECHM":"IT",
    "TATAELXSI":"IT","CYIENT":"IT","DIXON":"IT","PERSISTENT":"IT",
    "LTIM":"IT","MPHASIS":"IT","COFORGE":"IT","KPITTECH":"IT","HEXAWARE":"IT",
    "ASIANPAINT":"Paints","BERGEPAINT":"Paints","KANSAINER":"Paints",
    "MARICO":"FMCG","ITC":"FMCG","HINDUNILVR":"FMCG","NESTLEIND":"FMCG",
    "BRITANNIA":"FMCG","DABUR":"FMCG","GODREJCP":"FMCG",
    "IRCTC":"Travel","INDHOTEL":"Travel",
    "ASHOKLEY":"Auto","HEROMOTOCO":"Auto","BAJAJ-AUTO":"Auto","TVSMOTOR":"Auto",
    "MARUTI":"Auto","SONACOMS":"Auto","TATAMOTORS":"Auto",
    "M&M":"Auto","EICHERMOT":"Auto","BOSCHLTD":"Auto","BHARATFORG":"Auto","MOTHERSON":"Auto",
    "HAVELLS":"Cap Goods","POLYCAB":"Cap Goods","VOLTAS":"Cap Goods",
    "BLUESTAR":"Cap Goods","CROMPTON":"Cap Goods","VGUARD":"Cap Goods",
    "ZYDUSLIFE":"Pharma","SUNPHARMA":"Pharma","DRREDDY":"Pharma",
    "CIPLA":"Pharma","DIVISLAB":"Pharma","BIOCON":"Pharma","TORNTPHARM":"Pharma",
    "GLENMARK":"Pharma","LUPIN":"Pharma","NATCOPHARM":"Pharma","GRANULES":"Pharma","AJANTPHARM":"Pharma",
    "APOLLOHOSP":"Healthcare","MAXHEALTH":"Healthcare","FORTIS":"Healthcare","METROPOLIS":"Healthcare",
    "DEEPAKNTR":"Chemicals","AARTIIND":"Chemicals","PIDILITIND":"Chemicals",
    "FINEORG":"Chemicals","VINATIORGA":"Chemicals","NOCIL":"Chemicals",
    "GALAXYSURF":"Chemicals","TATACHEM":"Chemicals",
    "VBL":"Food","COALINDIA":"Mining","DMART":"Retail","TRENT":"Retail",
    "TITAN":"Jewellery","ASTRAL":"Pipes","ADANIENT":"Conglomerate",
    "ADANIPORTS":"Ports","BHARTIARTL":"Telecom",
    "ZOMATO":"Food Delivery","NYKAA":"Beauty","PAYTM":"Fintech",
    "DLF":"Real Estate","GODREJPROP":"Real Estate","PRESTIGE":"Real Estate",
    "UPL":"Agri","PI":"Agri","CONCOR":"Logistics","BLUEDART":"Logistics",
    "DATAPATTNS":"Defence","SOLARINDS":"Defence",
}

STOCK_PROFILES = {
    "LARGE_CAP":     {"mktcap_min":200_000,"mktcap_max":999_999_999,"rec_tf":"1W","sl_mult":2.0,"t1_mult":3.5,"t2_mult":6.0,"min_hold":15,"max_hold":90,"min_adx":20,"grace_days":3,"min_rr":2.0,"label":"Large Cap","note":"HDFC/Reliance/TCS scale.","type":"LARGE_CAP"},
    "UPPER_MID_CAP": {"mktcap_min":50_000, "mktcap_max":200_000,   "rec_tf":"1D","sl_mult":2.0,"t1_mult":3.5,"t2_mult":5.0,"min_hold":10,"max_hold":30,"min_adx":22,"grace_days":2,"min_rr":2.0,"label":"Upper Mid Cap","note":"Daily TF. Momentum-driven.","type":"UPPER_MID_CAP"},
    "MID_CAP":       {"mktcap_min":5_000,  "mktcap_max":50_000,    "rec_tf":"1D","sl_mult":2.0,"t1_mult":3.5,"t2_mult":5.0,"min_hold":7, "max_hold":21,"min_adx":22,"grace_days":2,"min_rr":2.0,"label":"Mid Cap","note":"Momentum-driven. Daily TF.","type":"MID_CAP"},
    "SMALL_CAP":     {"mktcap_min":500,    "mktcap_max":5_000,     "rec_tf":"1D","sl_mult":1.8,"t1_mult":3.0,"t2_mult":4.5,"min_hold":3, "max_hold":10,"min_adx":25,"grace_days":1,"min_rr":2.5,"label":"Small Cap","note":"Fast, volatile.","type":"SMALL_CAP"},
    "MICRO_CAP":     {"mktcap_min":0,      "mktcap_max":500,       "rec_tf":None,"sl_mult":None,"t1_mult":None,"t2_mult":None,"min_hold":0,"max_hold":0,"min_adx":999,"grace_days":0,"min_rr":999,"label":"Micro Cap","note":"Skip — manipulation risk.","type":"MICRO_CAP"},
}
PROFILE_ORDER = ["MICRO_CAP","SMALL_CAP","MID_CAP","UPPER_MID_CAP","LARGE_CAP"]

def get_stock_profile(mktcap_cr, price):
    if price < MIN_PRICE or mktcap_cr is None:
        return {**STOCK_PROFILES["MICRO_CAP"]}
    for ptype in PROFILE_ORDER:
        p = STOCK_PROFILES[ptype]
        if p["mktcap_min"] <= mktcap_cr <= p["mktcap_max"]:
            return {**p, "type": ptype}
    return {**STOCK_PROFILES["MID_CAP"], "type": "MID_CAP"}

def get_nse_session():
    s = requests.Session()
    s.headers.update(NSE_HEADERS)
    try: s.get("https://www.nseindia.com", timeout=8)
    except: pass
    return s

def resolve_ticker(symbol):
    if symbol.startswith("^"): return symbol
    symbol = symbol.strip().upper().replace("&", "%26")
    if symbol.endswith(".NS") or symbol.endswith(".BO"): return symbol
    try:
        t = yf.Ticker(symbol + ".NS")
        if t.fast_info.last_price and t.fast_info.last_price > 0: return symbol + ".NS"
    except: pass
    return symbol + ".BO"

def supertrend(df, period=10, multiplier=3.0):
    hl2 = (df["High"] + df["Low"]) / 2
    atr = ta.atr(df["High"], df["Low"], df["Close"], length=period)
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr
    direction = pd.Series(index=df.index, dtype=float)
    direction.iloc[0] = 1
    for i in range(1, len(df)):
        if   df["Close"].iloc[i] > upper.iloc[i-1]: direction.iloc[i] =  1
        elif df["Close"].iloc[i] < lower.iloc[i-1]: direction.iloc[i] = -1
        else: direction.iloc[i] = direction.iloc[i-1]
    return direction

def support_resistance(df, window=20):
    r = df["Close"].tail(window)
    return round(r.min(), 2), round(r.max(), 2)

def get_news_sentiment(ticker_obj):
    try:
        news = ticker_obj.news
        if not news: return 0.0, []
        scores, headlines = [], []
        for item in news[:8]:
            title = item.get("content", {}).get("title", "") or item.get("title", "")
            if title:
                sc = TextBlob(title).sentiment.polarity
                scores.append(sc)
                headlines.append((title[:80], round(sc, 2)))
        return (round(np.mean(scores), 3) if scores else 0.0), headlines
    except: return 0.0, []

def send_telegram(msg, token="", chat_id=""):
    tok = token or TELEGRAM_TOKEN
    cid = chat_id or TELEGRAM_CHAT_ID
    if not tok or not cid: return
    try:
        requests.get(f"https://api.telegram.org/bot{tok}/sendMessage",
                     params={"chat_id": cid, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except: pass

def get_deep_fundamentals(ticker_obj, symbol):
    result = {}
    try:
        info = ticker_obj.info
        for k, v in [("pe","trailingPE"),("fwdpe","forwardPE"),("pb","priceToBook"),
                     ("de","debtToEquity"),("beta","beta")]:
            result[k] = info.get(v)
        for k, v, m in [("roe","returnOnEquity",100),("profit_margin","profitMargins",100),
                        ("revenue_growth","revenueGrowth",100),("earnings_growth","earningsGrowth",100),
                        ("div_yield","dividendYield",100)]:
            raw = info.get(v)
            result[k] = round(raw*m,1) if raw else None
        mc = info.get("marketCap")
        result["mktcap_cr"] = round(mc/1e7, 0) if mc else None
        result["sector"]    = info.get("sector", SECTOR_MAP.get(symbol.upper(), "Other"))
        result["industry"]  = info.get("industry", "")
        try:
            cal = ticker_obj.calendar
            result["next_earnings"] = str(cal.columns[0].date()) if cal is not None and not cal.empty else "N/A"
        except: result["next_earnings"] = "N/A"
    except: pass
    return result

def passes_quality_prefilter(fund, price, profile):
    reasons = []; passed = True
    if profile["type"] == "MICRO_CAP": return False, ["Micro Cap — skip manipulation risk"]
    if price < MIN_PRICE:
        passed = False; reasons.append(f"Price ₹{price} < ₹{MIN_PRICE}")
    if fund.get("mktcap_cr") and fund["mktcap_cr"] < MIN_MKTCAP_CR:
        passed = False; reasons.append(f"Mkt Cap ₹{fund['mktcap_cr']:.0f}Cr too small")
    if fund.get("revenue_growth") and fund["revenue_growth"] < -10:
        passed = False; reasons.append(f"Revenue declining {fund['revenue_growth']}%")
    if fund.get("de") and fund["de"] > 300:
        passed = False; reasons.append(f"D/E {fund['de']} — dangerously leveraged")
    return passed, reasons

def passes_trend_filter(price, ema200_v):
    if ema200_v is None: return True, "EMA200 N/A"
    if price > ema200_v: return True,  f"✅ Above EMA200 ₹{round(ema200_v,2)}"
    return False, f"❌ Below EMA200 ₹{round(ema200_v,2)}"

def passes_volume_filter(vol):
    avg_vol = vol.tail(20).mean(); ratio = round(vol.iloc[-1]/avg_vol, 2)
    if vol.iloc[-1] >= avg_vol * 0.9: return True,  f"✅ Volume {ratio}x avg"
    return False, f"❌ Volume {ratio}x avg — weak"

def passes_adx_filter(adx_val, profile):
    min_adx = profile.get("min_adx", 25)
    if adx_val >= min_adx: return True,  f"✅ ADX {round(adx_val,1)} ≥ {min_adx}"
    return False, f"❌ ADX {round(adx_val,1)} < {min_adx}"

def signals_are_aligned(macd_val, macd_s_val, st_val, ema20_v, ema50_v,
                         price, rsi_val, adx_val, obv_trend, profile, regime_data=None):
    if regime_data is None: regime_data = {}
    thresholds = {"LARGE_CAP":4,"UPPER_MID_CAP":5,"MID_CAP":5,"SMALL_CAP":6}
    required   = thresholds.get(profile["type"], 5)
    if "CHOPPY" in regime_data.get("regime","") or "RANGING" in regime_data.get("regime",""):
        required = max(required - 1, 3)
    checks = {
        "MACD Bullish"       : macd_val > macd_s_val,
        "Supertrend Bullish" : st_val == 1,
        "Above EMA20"        : price > ema20_v if ema20_v else True,
        "Above EMA50"        : price > ema50_v if ema50_v else True,
        "RSI not overbought" : rsi_val < 72,
        "ADX Trending"       : adx_val >= profile.get("min_adx", 25),
        "OBV Bullish"        : obv_trend > 0,
    }
    passed = sum(checks.values())
    failed = [k for k, v in checks.items() if not v]
    return passed >= required, passed, failed, len(checks)

def compute_smart_stop_loss(price, atr_val, support, action, profile, fund=None):
    beta     = (fund.get("beta") or 1.0) if fund else 1.0
    beta_adj = min(max(beta, 0.8), 1.8)
    sl_mult  = round(profile.get("sl_mult", 2.0) * beta_adj, 2)
    if action == "BUY":
        atr_sl     = round(price - sl_mult * atr_val, 2)
        support_sl = round(support * 0.97, 2)
        sl = max(atr_sl, support_sl)
        method = f"{'ATR' if atr_sl > support_sl else 'Support'} ({sl_mult}x)"
        return sl, method
    return round(price - sl_mult * atr_val, 2), f"ATR ({sl_mult}x)"

def compute_targets(price, atr_val, profile, regime_data, burst_data):
    base_t1 = profile["t1_mult"]; base_t2 = profile["t2_mult"]
    hold_min = profile["min_hold"]; hold_max = profile["max_hold"]
    if "TRENDING_UP" in regime_data["regime"]:
        t1, t2 = base_t1, base_t2
        hold   = f"{hold_min}–{hold_max} days"
        exit_rule = "Exit when price closes below EMA20 OR Supertrend flips"
    elif "CHOPPY" in regime_data["regime"] or "RANGING" in regime_data["regime"]:
        t1, t2 = round(base_t1*0.6,1), round(base_t2*0.6,1)
        hold   = f"{max(2,hold_min//2)}–{hold_max//2} days"
        exit_rule = "Book T1 immediately. Don't hold in choppy market."
    elif burst_data.get("burst"):
        t1, t2 = round(base_t1*0.8,1), round(base_t2*0.8,1)
        hold   = "2–5 days (burst trade)"
        exit_rule = "Exit when RSI > 68 or momentum flattens"
    else:
        t1, t2 = round(base_t1*0.85,1), round(base_t2*0.85,1)
        hold   = f"{hold_min}–{int(hold_max*0.75)} days"
        exit_rule = "Exit when MACD histogram turns negative"
    return (round(price + t1*atr_val, 2), round(price + t2*atr_val, 2),
            t1, t2, hold, exit_rule)

def detect_market_regime(df):
    close = df["Close"]; high = df["High"]; low = df["Low"]
    adx_df  = ta.adx(high, low, close, 14)
    adx_val = adx_df["ADX_14"].iloc[-1] if adx_df is not None else 0
    ema200  = ta.ema(close, 200)
    price   = close.iloc[-1]
    n = 14; tr_sum = 0
    for i in range(1, n+1):
        tr_sum += max(high.iloc[-i]-low.iloc[-i],
                      abs(high.iloc[-i]-close.iloc[-i-1]),
                      abs(low.iloc[-i]-close.iloc[-i-1]))
    hh = high.tail(n+1).max(); ll = low.tail(n+1).min()
    chop = round(100*np.log10(tr_sum/max(hh-ll,0.01))/np.log10(n),1) if hh > ll else 50
    momentum_20 = round((close.iloc[-1]-close.iloc[-20])/close.iloc[-20]*100,2) if len(close)>=20 else 0
    returns = close.pct_change().dropna(); vol_20 = round(returns.tail(20).std()*100,2)
    ema200_v = ema200.iloc[-1] if ema200 is not None else None
    if   adx_val >= 25 and chop < 50 and momentum_20 > 2:
        regime="TRENDING_UP 🚀"; strategy="Momentum: hold full period"
    elif adx_val >= 25 and chop < 50 and momentum_20 < -2:
        regime="TRENDING_DOWN 📉"; strategy="Avoid BUY. SELL only."
    elif chop >= 61.8:
        regime="CHOPPY 〰️"; strategy="Quick scalps 2–5 days"
    elif 50 <= chop < 61.8 and adx_val >= 20:
        regime="WEAK TREND ➡️"; strategy="Short swing 5–10 days"
    else:
        regime="RANGING ↔️"; strategy="Wait for breakout"
    return {"regime":regime,"strategy":strategy,"adx":round(adx_val,1),
            "chop":chop,"momentum":momentum_20,"volatility":vol_20,
            "above_ema200": ema200_v is not None and price > ema200_v}

def detect_momentum_burst(df):
    close = df["Close"]; vol = df["Volume"]; high = df["High"]; low = df["Low"]
    if len(df) < 10: return {"burst":False,"squeeze":False,"signal":"Normal"}
    change_3d = round((close.iloc[-1]-close.iloc[-3])/close.iloc[-3]*100,2)
    avg_vol   = vol.tail(20).mean(); vol_ratio = round(vol.iloc[-1]/avg_vol,2)
    rsi = ta.rsi(close,14)
    rsi_now = rsi.iloc[-1] if rsi is not None else 50
    rsi_3d  = rsi.iloc[-3] if rsi is not None else 50
    rsi_accel = round(rsi_now-rsi_3d,1)
    atr = ta.atr(high,low,close,14)
    atr_now = atr.iloc[-1] if atr is not None else 0
    atr_10d = atr.tail(10).mean() if atr is not None else 0
    atr_ratio = round(atr_now/atr_10d,2) if atr_10d > 0 else 1
    burst   = (change_3d > 1.5 and vol_ratio > 1.3 and rsi_accel > 5 and rsi_now < 65)
    squeeze = atr_ratio < 0.8
    return {"burst":burst,"squeeze":squeeze,"change_3d":change_3d,
            "vol_ratio":vol_ratio,"rsi_accel":rsi_accel,"atr_ratio":atr_ratio,
            "signal":"⚡ MOMENTUM BURST!" if burst else ("🔄 SQUEEZE SETUP" if squeeze else "Normal")}

def grade_signal(score, gates_passed, align_count, regime_data, burst_data, rr, fund, profile):
    pts = 0
    if score >= 15: pts += 3
    elif score >= 12: pts += 2
    elif score >= 8:  pts += 1
    if align_count >= 6: pts += 3
    elif align_count >= 5: pts += 2
    elif align_count >= 4: pts += 1
    if "TRENDING_UP"  in regime_data["regime"]: pts += 3
    elif "WEAK TREND" in regime_data["regime"]: pts += 2
    elif "CHOPPY"     in regime_data["regime"]: pts += 1
    if burst_data.get("burst"): pts += 2
    if rr >= 3.0: pts += 2
    elif rr >= 2.0: pts += 1
    if fund.get("roe") and fund["roe"] > 15: pts += 1
    if fund.get("revenue_growth") and fund["revenue_growth"] > 10: pts += 1
    if profile["type"] == "LARGE_CAP": pts += 1
    if   pts >= 12: grade,desc,size = "A+ 🏆","Exceptional — Full size",100
    elif pts >= 9:  grade,desc,size = "A  ✅","Strong — Full size",100
    elif pts >= 7:  grade,desc,size = "B+ 🟡","Good — 75% size",75
    elif pts >= 5:  grade,desc,size = "B  🟡","Moderate — 50% size",50
    else:           grade,desc,size = "C  ⚠️","Weak — 25% or skip",25
    return {"grade":grade,"desc":desc,"size_pct":size,"points":pts}

def signal_meter(score, max_score=35):
    filled = max(0, min(20, score))
    bar    = "🟩"*filled + "⬜"*(20-filled)
    if   score >= 18: label = "VERY STRONG BUY 🔥🔥"
    elif score >= 12: label = "STRONG BUY 🔥"
    elif score >= 8:  label = "GOOD BUY ✅"
    elif score >= -4: label = "NEUTRAL — HOLD 🟡"
    elif score >= -8: label = "SELL ❌"
    else:             label = "STRONG SELL 🔴"
    return bar, label

# ── MAIN ANALYSIS FUNCTION ──────────────────────────────────
def analyze_stock(symbol, tf=None, capital=CAPITAL):
    """Returns a dict with full analysis result, or None if skipped."""
    import sys as _sys
    ticker_str = resolve_ticker(symbol)
    ticker_obj = yf.Ticker(ticker_str)
    fund       = get_deep_fundamentals(ticker_obj, symbol)
    try:    price_now = ticker_obj.fast_info.last_price or 0
    except: price_now = 0
    profile = get_stock_profile(fund.get("mktcap_cr"), price_now)
    if profile["type"] == "MICRO_CAP":
        return None
    if tf is None: tf = profile["rec_tf"]
    tf_map = {"15m":("5d","15m"),"30m":("10d","30m"),"1h":("30d","1h"),
              "1D":("1y","1d"),"1W":("3y","1wk")}
    period, interval = tf_map.get(tf, ("1y","1d"))
    try:
        df = ticker_obj.history(period=period, interval=interval, auto_adjust=True)
    except: return None
    if df.empty or len(df) < 30: return None

    close=df["Close"]; high=df["High"]; low=df["Low"]; vol=df["Volume"]
    price = round(close.iloc[-1], 2)

    _old_stderr = _sys.stderr; _sys.stderr = _devnull
    prefilter_ok, prefilter_reasons = passes_quality_prefilter(fund, price, profile)
    if not prefilter_ok:
        _sys.stderr = _old_stderr
        return {"skipped": True, "reason": "; ".join(prefilter_reasons), "ticker": ticker_str}

    rsi     = ta.rsi(close, 14)
    macd_df = ta.macd(close, 12, 26, 9)
    macd    = macd_df["MACD_12_26_9"]  if macd_df is not None else pd.Series(0, index=df.index)
    macd_sig= macd_df["MACDs_12_26_9"] if macd_df is not None else pd.Series(0, index=df.index)
    bb      = ta.bbands(close, 20, 2)
    ema20   = ta.ema(close, 20); ema50 = ta.ema(close, 50); ema200 = ta.ema(close, 200)
    adx_df  = ta.adx(high, low, close, 14)
    adx_val = adx_df["ADX_14"].iloc[-1] if adx_df is not None else 0
    stoch   = ta.stoch(high, low, close)
    stoch_k = stoch["STOCHk_14_3_3"].iloc[-1] if stoch is not None else 50
    obv     = ta.obv(close, vol)
    atr     = ta.atr(high, low, close, 14)
    vwap    = (close*vol).cumsum()/vol.cumsum()
    st_dir  = supertrend(df)
    psar    = ta.psar(high, low, close)
    try:    ichi = ta.ichimoku(high, low, close)[0]
    except: ichi = None
    try:    cdl  = _silent(ta.cdl_pattern, df["Open"], high, low, close, name="all")
    except: cdl  = None

    rsi_val    = round(rsi.iloc[-1], 2)   if rsi  is not None else 50
    macd_val   = round(macd.iloc[-1], 4)
    macd_s_val = round(macd_sig.iloc[-1], 4)
    bb_up = bb_lo = None
    if bb is not None:
        bbu = [c for c in bb.columns if c.startswith("BBU")]
        bbl = [c for c in bb.columns if c.startswith("BBL")]
        bb_up = round(bb[bbu[0]].iloc[-1], 2) if bbu else None
        bb_lo = round(bb[bbl[0]].iloc[-1], 2) if bbl else None
    ema20_v  = round(ema20.iloc[-1],  2) if ema20  is not None else None
    ema50_v  = round(ema50.iloc[-1],  2) if ema50  is not None else None
    ema200_v = round(ema200.iloc[-1], 2) if ema200 is not None else None
    atr_val  = round(atr.iloc[-1],    2) if atr    is not None else price*0.02
    st_val   = st_dir.iloc[-1]
    vwap_val = round(vwap.iloc[-1], 2)
    support, resistance = support_resistance(df)
    obv_trend = (obv.iloc[-1]-obv.iloc[-5])/(abs(obv.iloc[-5])+1)

    lookback     = min(252, len(close))
    w52_high     = round(high.tail(lookback).max(), 2)
    w52_low      = round(low.tail(lookback).min(),  2)
    pct_from_52h = round((price-w52_high)/w52_high*100, 1)
    avg_vol    = vol.tail(20).mean()
    vol_spike  = vol.iloc[-1] > 1.5*avg_vol

    regime_data = detect_market_regime(df)
    burst_data  = detect_momentum_burst(df)
    _sys.stderr = _old_stderr

    score = 0; signals = []
    if rsi_val < 35:   score += 2; signals.append(f"RSI {rsi_val} Oversold ✅")
    elif rsi_val > 65: score -= 2; signals.append(f"RSI {rsi_val} Overbought ❌")
    else:                           signals.append(f"RSI {rsi_val} Neutral")
    try:
        ld = min(14, len(close)-1)
        if close.iloc[-1] < close.iloc[-ld] and rsi.iloc[-1] > rsi.iloc[-ld]:
            score += 3; signals.append("RSI Bullish Divergence ✅")
        elif close.iloc[-1] > close.iloc[-ld] and rsi.iloc[-1] < rsi.iloc[-ld]:
            score -= 3; signals.append("RSI Bearish Divergence ❌")
    except: pass
    if macd_val > macd_s_val: score += 2; signals.append("MACD Bullish ✅")
    else:                      score -= 2; signals.append("MACD Bearish ❌")
    if bb_lo and price <= bb_lo:   score += 2; signals.append("At BB Lower ✅")
    elif bb_up and price >= bb_up: score -= 2; signals.append("At BB Upper ❌")
    if ema20_v and ema50_v and ema200_v:
        if price > ema20_v > ema50_v > ema200_v:    score += 4; signals.append("EMA Stack Bullish ✅✅")
        elif price > ema20_v and price > ema50_v:    score += 2; signals.append("Above EMA20/50 ✅")
        elif price < ema20_v < ema50_v < ema200_v:   score -= 4; signals.append("EMA Stack Bearish ❌❌")
        elif price < ema20_v and price < ema50_v:    score -= 2; signals.append("Below EMA20/50 ❌")
    if st_val == 1: score += 2; signals.append("Supertrend Bullish ✅")
    else:           score -= 2; signals.append("Supertrend Bearish ❌")
    if stoch_k < 25:  score += 1; signals.append("Stoch Oversold ✅")
    elif stoch_k > 75: score -= 1; signals.append("Stoch Overbought ❌")
    os5  = (obv.iloc[-1]-obv.iloc[-5]) /(abs(obv.iloc[-5])+1)
    os10 = (obv.iloc[-1]-obv.iloc[-10])/(abs(obv.iloc[-10])+1)
    if os5 > 0 and os10 > 0 and vol_spike: score += 3; signals.append("OBV + Vol Spike ✅")
    elif os5 > 0 and os10 > 0:              score += 1; signals.append("OBV Rising ✅")
    elif os5 < 0 and os10 < 0:              score -= 2; signals.append("OBV Falling ❌")
    if "TRENDING_UP"   in regime_data["regime"]: score += 2; signals.append("Regime: Trending Up ✅")
    elif "TRENDING_DOWN" in regime_data["regime"]: score -= 3; signals.append("Regime: Trending Down ❌")
    elif "CHOPPY"        in regime_data["regime"]: score -= 1; signals.append("Regime: Choppy ⚠️")
    if burst_data.get("burst"): score += 3; signals.append("Momentum Burst ⚡")

    if score >= MIN_SCORE: action = "BUY 🚀"
    elif score <= -8:      action = "STRONG SELL 🔴"
    elif score <= -4:      action = "SELL ❌"
    else:                  action = "HOLD / WATCH 🟡"

    sl, sl_method = compute_smart_stop_loss(price, atr_val, support, "BUY", profile, fund)
    target1, target2, t1m, t2m, hold_period, exit_rule = compute_targets(
        price, atr_val, profile, regime_data, burst_data)
    rr = round((target1-price)/max(price-sl, 0.01), 2)
    align_ok, align_count, align_fail, align_req = signals_are_aligned(
        macd_val, macd_s_val, st_val, ema20_v, ema50_v,
        price, rsi_val, adx_val, obv_trend, profile, regime_data)
    trend_ok, trend_msg = passes_trend_filter(price, ema200_v)
    vol_ok,   vol_msg   = passes_volume_filter(vol)
    adx_ok,   adx_msg   = passes_adx_filter(adx_val, profile)
    gates_passed = sum([trend_ok, vol_ok, adx_ok, align_ok])
    grade_info = grade_signal(score, gates_passed, align_count, regime_data, burst_data, rr, fund, profile)
    bar, meter_label = signal_meter(score)
    confidence = "HIGH" if score >= MIN_SCORE and align_ok and rr >= profile["min_rr"] else \
                 "MEDIUM" if score >= MIN_SCORE else "LOW"
    _, headlines = get_news_sentiment(ticker_obj)
    pattern_names = []
    if cdl is not None:
        pattern_names = [p.replace("CDL_","").title() for p in cdl.columns if cdl[p].iloc[-1] != 0]

    return {
        "ticker": ticker_str, "symbol": symbol,
        "price": price, "action": action, "score": score,
        "stop_loss": sl, "sl_method": sl_method,
        "target1": target1, "target2": target2, "rr": rr,
        "confidence": confidence, "grade": grade_info["grade"],
        "grade_desc": grade_info["desc"], "grade_points": grade_info["points"],
        "stock_type": profile["type"], "profile": profile,
        "regime": regime_data["regime"], "regime_strategy": regime_data["strategy"],
        "burst_signal": burst_data["signal"],
        "signals": signals, "align_ok": align_ok,
        "align_count": align_count, "align_fail": align_fail, "align_req": align_req,
        "trend_msg": trend_msg, "vol_msg": vol_msg, "adx_msg": adx_msg,
        "w52_high": w52_high, "w52_low": w52_low, "pct_from_52h": pct_from_52h,
        "support": support, "resistance": resistance,
        "ema20": ema20_v, "ema50": ema50_v, "ema200": ema200_v,
        "rsi": rsi_val, "adx": adx_val, "atr": atr_val,
        "macd": macd_val, "macd_signal": macd_s_val,
        "vwap": vwap_val, "vol_spike": vol_spike,
        "bb_upper": bb_up, "bb_lower": bb_lo,
        "hold_period": hold_period, "exit_rule": exit_rule,
        "fund": fund, "headlines": headlines, "patterns": pattern_names,
        "meter_bar": bar, "meter_label": meter_label, "tf": tf,
    }

# ── CHART FUNCTION (returns fig instead of fig.show()) ──────
def plot_chart(symbol, tf="1D"):
    tf_map = {"15m":("5d","15m"),"30m":("10d","30m"),"1h":("30d","1h"),
              "1D":("1y","1d"),"1W":("3y","1wk")}
    period, interval = tf_map.get(tf, ("1y","1d"))
    ticker_str = resolve_ticker(symbol)
    df = yf.Ticker(ticker_str).history(period=period, interval=interval, auto_adjust=True)
    if df.empty or len(df) < 30: return None
    close=df["Close"]; vol=df["Volume"]
    ema20=ta.ema(close,20); ema50=ta.ema(close,50); ema200=ta.ema(close,200)
    bb=ta.bbands(close,20,2); rsi=ta.rsi(close,14); macd_df=ta.macd(close,12,26,9)
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True,
                        row_heights=[0.5,0.15,0.2,0.15], vertical_spacing=0.03,
                        subplot_titles=(f"{ticker_str} — {tf}", "Volume","RSI","MACD"))
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"],
                                  low=df["Low"], close=close, name="OHLC",
                                  increasing_line_color="#26a69a",
                                  decreasing_line_color="#ef5350"), row=1, col=1)
    for ema, color, name in [(ema20,"#f59e0b","EMA20"),(ema50,"#3b82f6","EMA50"),(ema200,"#ec4899","EMA200")]:
        if ema is not None:
            fig.add_trace(go.Scatter(x=df.index, y=ema, name=name,
                                      line=dict(color=color, width=1.2)), row=1, col=1)
    if bb is not None:
        bbu=[c for c in bb.columns if c.startswith("BBU")]
        bbl=[c for c in bb.columns if c.startswith("BBL")]
        if bbu and bbl:
            fig.add_trace(go.Scatter(x=df.index, y=bb[bbu[0]], name="BB Upper",
                line=dict(color="rgba(150,150,255,0.5)",dash="dot",width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=bb[bbl[0]], name="BB Lower",
                line=dict(color="rgba(150,150,255,0.5)",dash="dot",width=1),
                fill="tonexty", fillcolor="rgba(150,150,255,0.04)"), row=1, col=1)
    colors = ["#26a69a" if c >= o else "#ef5350" for c,o in zip(df["Close"],df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=vol, name="Volume",
                          marker_color=colors, opacity=0.7), row=2, col=1)
    if rsi is not None:
        fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI",
                                  line=dict(color="#a78bfa",width=1.5)), row=3, col=1)
        fig.add_hline(y=70, line=dict(color="red",   dash="dash", width=1), row=3, col=1)
        fig.add_hline(y=30, line=dict(color="green", dash="dash", width=1), row=3, col=1)
    if macd_df is not None:
        ml=macd_df["MACD_12_26_9"]; ms=macd_df["MACDs_12_26_9"]; mh=macd_df["MACDh_12_26_9"]
        hc = ["#26a69a" if v >= 0 else "#ef5350" for v in mh.fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=mh, name="MACD Hist",
                              marker_color=hc, opacity=0.6), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=ml, name="MACD",
                                  line=dict(color="#3b82f6",width=1.5)), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=ms, name="Signal",
                                  line=dict(color="#f59e0b",width=1.2)), row=4, col=1)
    fig.update_layout(height=800, template="plotly_dark",
                      xaxis_rangeslider_visible=False,
                      paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e",
                      margin=dict(l=50, r=30, t=60, b=30))
    return fig

# ── SCREENER ─────────────────────────────────────────────────
def run_screener(symbols=None, tf=None, top_n=20, capital=CAPITAL,
                 sector_filter=None, min_grade="B"):
    if symbols is None: symbols = WATCHLIST
    if sector_filter:
        symbols = [s for s in symbols if SECTOR_MAP.get(s.upper(),"").lower() == sector_filter.lower()]
    grade_rank = {"A+":5,"A":4,"B+":3,"B":2,"C":1}
    min_pts    = grade_rank.get(min_grade.strip(), 2)
    results    = []
    for sym in symbols:
        try:
            r = analyze_stock(sym, tf=tf, capital=capital)
            if r and not r.get("skipped") and "BUY" in r.get("action",""):
                if r.get("score", 0) >= MIN_SCORE:
                    gpts = grade_rank.get(r.get("grade","C").strip(), 0)
                    if gpts >= min_pts:
                        results.append(r)
        except: pass
    results.sort(key=lambda x: (-x.get("score",0), -x.get("rr",0)))
    return results[:top_n]

# ── TRADE LOG ────────────────────────────────────────────────
def save_trade_log(result):
    log = []
    if os.path.exists(TRADE_LOG_FILE):
        try:
            with open(TRADE_LOG_FILE, "r") as f: log = json.load(f)
        except: pass
    log.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ticker": result["ticker"], "price": result["price"],
        "action": result["action"], "stop_loss": result["stop_loss"],
        "target1": result["target1"], "target2": result["target2"],
        "score": result["score"], "confidence": result["confidence"],
        "grade": result.get("grade","—"), "stock_type": result.get("stock_type","—"),
        "outcome": "PENDING"
    })
    with open(TRADE_LOG_FILE, "w") as f: json.dump(log, f, indent=2)

def load_trade_log():
    if not os.path.exists(TRADE_LOG_FILE): return []
    try:
        with open(TRADE_LOG_FILE, "r") as f: return json.load(f)
    except: return []