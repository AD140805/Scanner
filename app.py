import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="🇮🇳 Indian Stock Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Telegram secrets (safe, not in code) ──
try:
    import screener_core as core
    core.TELEGRAM_TOKEN   = st.secrets.get("TELEGRAM_TOKEN", "")
    core.TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")
except Exception as e:
    st.error(f"Could not load screener_core: {e}")
    st.stop()

# ── CSS ──
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.4rem; font-weight: 700; }
.buy-box  { background:#1a3a2a; border-left:4px solid #26a69a; padding:12px 16px; border-radius:8px; }
.sell-box { background:#3a1a1a; border-left:4px solid #ef5350; padding:12px 16px; border-radius:8px; }
.hold-box { background:#2a2a1a; border-left:4px solid #f59e0b; padding:12px 16px; border-radius:8px; }
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ──
with st.sidebar:
    st.title("📈 Stock Screener")
    st.caption("Indian Markets · NSE/BSE")
    st.divider()
    page = st.radio("Navigate", ["🔍 Analyze Stock", "📊 Screener Scan", "📈 Chart", "📋 Trade Log"])
    st.divider()
    st.caption("Data: Yahoo Finance · Indicators: pandas-ta")

# ════════════════════════════════════════
# PAGE 1 — ANALYZE STOCK
# ════════════════════════════════════════
if page == "🔍 Analyze Stock":
    st.title("🔍 Analyze Stock")
    st.caption("Full technical + fundamental analysis for a single stock")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        symbol = st.text_input("Stock Symbol", value="IRCTC", placeholder="e.g. IRCTC, HDFCBANK, TCS")
    with col2:
        tf = st.selectbox("Timeframe", ["AUTO", "1D", "1W", "1h", "30m", "15m"])
    with col3:
        log_trade = st.checkbox("Log this trade", value=False)
        st.write("")
        run_btn = st.button("▶ Analyze", type="primary", use_container_width=True)

    if run_btn and symbol:
        with st.spinner(f"Analyzing {symbol.upper()}..."):
            tf_val = None if tf == "AUTO" else tf
            result = core.analyze_stock(symbol.strip(), tf=tf_val)

        if result is None:
            st.error("⛔ Could not analyze. Stock may be micro-cap, delisted, or has no data.")
        elif result.get("skipped"):
            st.warning(f"⛔ Skipped: {result.get('reason','')}")
        else:
            # ── ACTION BANNER ──
            action = result["action"]
            box_class = "buy-box" if "BUY" in action else ("sell-box" if "SELL" in action else "hold-box")
            st.markdown(f"""
            <div class="{box_class}">
                <h2 style="margin:0">{result['ticker']}  ·  {action}</h2>
                <p style="margin:4px 0 0">Grade: {result['grade']} — {result['grade_desc']}
                &nbsp;|&nbsp; Confidence: {result['confidence']}
                &nbsp;|&nbsp; Score: {result['score']}
                &nbsp;|&nbsp; TF: {result['tf']}</p>
            </div>
            """, unsafe_allow_html=True)
            st.write("")

            # ── KEY METRICS ──
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Price",    f"₹{result['price']}")
            m2.metric("Stop Loss",f"₹{result['stop_loss']}", delta=f"-{round(result['price']-result['stop_loss'],2)}", delta_color="inverse")
            m3.metric("Target 1", f"₹{result['target1']}", delta=f"+{round(result['target1']-result['price'],2)}")
            m4.metric("Target 2", f"₹{result['target2']}", delta=f"+{round(result['target2']-result['price'],2)}")
            m5.metric("R:R",      f"{result['rr']}x")
            m6.metric("ADX",      result['adx'])

            st.write("")
            c1, c2 = st.columns(2)

            with c1:
                st.subheader("📡 Signal Meter")
                st.text(result["meter_bar"])
                st.caption(result["meter_label"])
                st.divider()
                st.subheader("🧭 Regime")
                st.write(result["regime"])
                st.caption(result["regime_strategy"])
                st.write(f"**Burst:** {result['burst_signal']}")
                st.divider()
                st.subheader("🎯 Trade Plan")
                st.write(f"**Hold:** {result['hold_period']}")
                st.write(f"**Exit Rule:** {result['exit_rule']}")
                st.write(f"**SL Method:** {result['sl_method']}")

            with c2:
                st.subheader("📊 Indicators")
                ind_data = {
                    "RSI":         result["rsi"],
                    "MACD":        result["macd"],
                    "MACD Signal": result["macd_signal"],
                    "EMA 20":      result["ema20"],
                    "EMA 50":      result["ema50"],
                    "EMA 200":     result["ema200"],
                    "ATR":         result["atr"],
                    "VWAP":        result["vwap"],
                    "Support":     result["support"],
                    "Resistance":  result["resistance"],
                    "52W High":    result["w52_high"],
                    "52W Low":     result["w52_low"],
                    "BB Upper":    result["bb_upper"],
                    "BB Lower":    result["bb_lower"],
                }
                st.dataframe(pd.DataFrame(list(ind_data.items()), columns=["Indicator","Value"]),
                             hide_index=True, use_container_width=True)

            st.divider()
            c3, c4 = st.columns(2)
            with c3:
                st.subheader("✅ Signals")
                for sig in result["signals"]:
                    st.write(f"• {sig}")
                if result["align_fail"]:
                    st.caption("**Failed checks:** " + ", ".join(result["align_fail"]))

            with c4:
                st.subheader("📈 Fundamentals")
                fund = result["fund"]
                fund_data = {
                    "Sector":         fund.get("sector","—"),
                    "Market Cap (Cr)":fund.get("mktcap_cr","—"),
                    "P/E":            fund.get("pe","—"),
                    "P/B":            fund.get("pb","—"),
                    "D/E":            fund.get("de","—"),
                    "ROE %":          fund.get("roe","—"),
                    "Revenue Growth": fund.get("revenue_growth","—"),
                    "Profit Margin":  fund.get("profit_margin","—"),
                    "Next Earnings":  fund.get("next_earnings","—"),
                }
                st.dataframe(pd.DataFrame(list(fund_data.items()), columns=["Metric","Value"]),
                             hide_index=True, use_container_width=True)

            if result.get("headlines"):
                st.divider()
                st.subheader("📰 News Sentiment")
                for headline, score in result["headlines"][:5]:
                    color = "🟢" if score > 0 else ("🔴" if score < 0 else "⚪")
                    st.caption(f"{color} {headline}  ({score:+.2f})")

            if result.get("patterns"):
                st.info("📐 Patterns: " + ", ".join(result["patterns"]))

            if log_trade and "BUY" in action and result["score"] >= core.MIN_SCORE:
                core.save_trade_log(result)
                st.success("✅ Trade logged!")


# ════════════════════════════════════════
# PAGE 2 — SCREENER SCAN
# ════════════════════════════════════════
elif page == "📊 Screener Scan":
    st.title("📊 Screener Scan")
    st.caption("Scan multiple stocks and surface the best BUY opportunities")

    sectors = sorted(set(v for v in core.SECTOR_MAP.values()))

    col1, col2, col3, col4 = st.columns(4)
    with col1: top_n = st.number_input("Top N results", min_value=5, max_value=50, value=20)
    with col2: tf    = st.selectbox("Timeframe", ["AUTO","1D","1W"], key="sc_tf")
    with col3: sector= st.selectbox("Sector filter", ["ALL"] + sectors)
    with col4: grade = st.selectbox("Min Grade", ["A+","A","B+","B","C"], index=3)

    custom_symbols = st.text_area("Custom symbols (optional, comma-separated)",
                                   placeholder="e.g. IRCTC, ZOMATO, TITAN")

    run_scan = st.button("🚀 Run Scan", type="primary")

    if run_scan:
        if custom_symbols.strip():
            symbols = [s.strip().upper() for s in custom_symbols.split(",") if s.strip()]
        else:
            symbols = core.WATCHLIST

        sector_val = None if sector == "ALL" else sector
        tf_val     = None if tf == "AUTO" else tf

        progress = st.progress(0, text="Scanning stocks...")
        results_list = []

        for i, sym in enumerate(symbols):
            progress.progress((i+1)/len(symbols), text=f"Scanning {sym}...")
            try:
                r = core.analyze_stock(sym, tf=tf_val)
                if r and not r.get("skipped") and "BUY" in r.get("action",""):
                    if r.get("score",0) >= core.MIN_SCORE:
                        grade_rank = {"A+":5,"A":4,"B+":3,"B":2,"C":1}
                        if grade_rank.get(r.get("grade","C").strip(),0) >= grade_rank.get(grade,2):
                            if not sector_val or core.SECTOR_MAP.get(sym.upper(),"").lower() == sector_val.lower():
                                results_list.append(r)
            except: pass

        progress.empty()

        if not results_list:
            st.warning("No qualifying BUY signals found. Try lowering the grade filter or changing sector.")
        else:
            results_list.sort(key=lambda x: (-x.get("score",0), -x.get("rr",0)))
            results_list = results_list[:top_n]

            st.success(f"✅ Found {len(results_list)} BUY signals")

            rows = []
            for r in results_list:
                rows.append({
                    "Ticker":    r["ticker"],
                    "Grade":     r["grade"],
                    "Score":     r["score"],
                    "Price":     r["price"],
                    "SL":        r["stop_loss"],
                    "T1":        r["target1"],
                    "T2":        r["target2"],
                    "RR":        r["rr"],
                    "Regime":    r["regime"],
                    "Sector":    core.SECTOR_MAP.get(r["symbol"].upper(),"—"),
                    "Confidence":r["confidence"],
                })

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={
                             "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=25),
                             "RR":    st.column_config.NumberColumn("R:R", format="%.1fx"),
                         })


# ════════════════════════════════════════
# PAGE 3 — CHART
# ════════════════════════════════════════
elif page == "📈 Chart":
    st.title("📈 Chart")
    st.caption("Candlestick + EMA + Bollinger Bands + RSI + MACD")

    col1, col2 = st.columns([3, 1])
    with col1: chart_sym = st.text_input("Symbol", value="IRCTC", key="chart_sym")
    with col2: chart_tf  = st.selectbox("Timeframe", ["1D","1W","1h","30m","15m"], key="chart_tf")

    if st.button("📈 Load Chart", type="primary") and chart_sym:
        with st.spinner("Loading chart..."):
            fig = core.plot_chart(chart_sym.strip(), tf=chart_tf)
        if fig is None:
            st.error("⚠️ Not enough data for this symbol/timeframe.")
        else:
            st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════
# PAGE 4 — TRADE LOG
# ════════════════════════════════════════
elif page == "📋 Trade Log":
    st.title("📋 Trade Log")
    st.caption("Your logged BUY signals and outcomes")

    log = core.load_trade_log()
    if not log:
        st.info("No trades logged yet. Analyze a stock and tick 'Log this trade'.")
    else:
        df = pd.DataFrame(log)
        wins   = len(df[df["outcome"].str.contains("WIN",  na=False)])
        losses = len(df[df["outcome"].str.contains("LOSS", na=False)])
        total  = wins + losses
        rate   = round(wins/total*100, 1) if total > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Trades", len(df))
        m2.metric("Wins",   wins)
        m3.metric("Losses", losses)
        m4.metric("Win Rate", f"{rate}%")

        st.divider()
        st.dataframe(df, use_container_width=True, hide_index=True)

        if st.button("🔄 Update Outcomes"):
            with st.spinner("Checking live prices..."):
                import json, os, yfinance as yf
                updated = 0
                for trade in log:
                    if trade["outcome"] != "PENDING": continue
                    try:
                        cur = yf.Ticker(trade["ticker"]).fast_info.last_price
                        if cur >= trade["target1"]:    trade["outcome"] = "WIN ✅";  updated += 1
                        elif cur <= trade["stop_loss"]: trade["outcome"] = "LOSS ❌"; updated += 1
                    except: pass
                with open(core.TRADE_LOG_FILE, "w") as f: json.dump(log, f, indent=2)
            st.success(f"Updated {updated} trades.")
            st.rerun()