import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="담보 주식 수 대시보드", layout="wide")

# --- CSS: 디자인 미세 조정 ---
st.markdown("""
    <style>
    * { outline: none !important; }
    .stApp { background-color: #f8fbff; }
    [data-testid="stSidebar"] { background-color: #eef6ff; border-right: 1px solid #d1e3ff; }
    .main-title { font-size: 26px !important; font-weight: bold; color: #003366; margin-bottom: 20px; }
    
    [data-testid="stMetric"] { 
        background-color: #ffffff; 
        border: 1px solid #d1e3ff; 
        border-radius: 12px; 
        padding: 25px 20px !important; 
        box-shadow: 2px 4px 12px rgba(0,51,102,0.08); 
    }
    [data-testid="stMetricLabel"] { font-size: 14px !important; color: #555 !important; margin-bottom: 8px !important; }
    [data-testid="stMetricValue"] { font-size: 24px !important; color: #003366 !important; font-weight: 700 !important; }
    </style>
    <div class="main-title">담보 주식 수 대시보드</div>
    """, unsafe_allow_html=True)

# --- 사이드바 ---
st.sidebar.header("📌 설정 및 기간 선택")
bond_balance_usd = st.sidebar.number_input("채권 잔액 (USD)", min_value=0.0, value=59466710.0, step=1000.0)
st.sidebar.markdown(f"<div style='color: #0056b3; font-size: 18px; font-weight: bold; margin-top: -10px; margin-bottom: 15px;'>$ {bond_balance_usd:,.2f}</div>", unsafe_allow_html=True)

stock_symbol = st.sidebar.text_input("말레이시아 주식 티커", value="5238")

today = datetime.now()
default_start = today - timedelta(days=7)
date_range = st.sidebar.date_input("VWAP 계산 기간", value=(default_start, today))

full_ticker = f"{stock_symbol.zfill(4)}.KL" if not stock_symbol.endswith(".KL") else stock_symbol

try:
    # 데이터 다운로드 (충분한 기간 확보를 위해 1mo)
    raw_df = yf.download(full_ticker, period="1mo", interval="1d")
    fx_raw = yf.download("USDMYR=X", period="5d")
    
    if raw_df.empty:
        st.error("데이터를 불러오지 못했습니다.")
    else:
        df_all = raw_df.copy()
        if isinstance(df_all.columns, pd.MultiIndex):
            df_all.columns = df_all.columns.get_level_values(0)
        
        # 선택 기간 필터링
        mask = (df_all.index.date >= date_range[0]) & (df_all.index.date <= date_range[1])
        df = df_all.loc[mask].copy()

        try: default_fx = float(fx_raw['Close'].iloc[-1])
        except: default_fx = 4.4500
        input_fx = st.sidebar.number_input("적용 환율 (USD/MYR)", value=default_fx, format="%.4f")

        if not df.empty:
            # 1. VWAP (MYR) 계산
            vwap_val = (df['Close'] * df['Volume']).sum() / df['Volume'].sum()
            
            # 2. 담보 주식 수 (목표 비율 115% 기준 필요량)
            required_shares = (bond_balance_usd * input_fx * 1.15) / vwap_val
            
            # 3. Stock Price (선택 기간 마지막 날 종가)
            last_close_price = float(df['Close'].iloc[-1])
            
            # 4. 채권 대비 % (LTV) 계산 
            # 수식: (담보 주식 수 * 마지막 종가) / (채권 잔액 * 환율) * 100
            collateral_ratio = (int(required_shares) * last_close_price) / (bond_balance_usd * input_fx) * 100

            # --- 상단 지표 박스 섹션 (4열 구성) ---
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.metric("VWAP (MYR)", f"{vwap_val:.4f}")
            with m2: st.metric("담보 주식 수", f"{int(required_shares):,} 주")
            with m3: st.metric("Stock Price", f"{last_close_price:.3f}")
            with m4: st.metric("채권 대비 %", f"{collateral_ratio:.2f}%")

            st.markdown("<hr style='border: 0.5px solid #d1e3ff; margin: 30px 0;'>", unsafe_allow_html=True)

            # --- 차트 섹션 ---
            c_left, c_right = st.columns(2)
            date_labels = df.index.strftime('%y-%m-%d').tolist()

            def get_layout(title):
                return dict(
                    title=dict(text=title, font=dict(size=16, color='#004080')),
                    margin=dict(l=10, r=10, t=50, b=10), height=320,
                    plot_bgcolor='white', paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(tickformat='%y-%m-%d', type='category', gridcolor='#f0f5ff'),
                    yaxis=dict(gridcolor='#f0f5ff', autorange=True), showlegend=False
                )

            with c_left:
                fig_p = go.Figure(go.Scatter(x=date_labels, y=df['Close'], mode='lines+markers', line=dict(color='#0056b3', width=2.5)))
                fig_p.update_layout(get_layout("📈 Stock Price (MYR)"))
                st.plotly_chart(fig_p, use_container_width=True)

            with c_right:
                fig_v = go.Figure(go.Bar(x=date_labels, y=df['Volume'] / 1000000, marker_color='#66b2ff'))
                fig_v.update_layout(get_layout("📊 Trading Volume (Million)"))
                st.plotly_chart(fig_v, use_container_width=True)

            with st.expander("📝 상세 데이터 보기"):
                df_display = df[['Close', 'Volume']].copy()
                df_display.index = df_display.index.strftime('%y-%m-%d')
                st.dataframe(df_display.style.format("{:,.2f}"), use_container_width=True)

except Exception as e:
    st.error(f"데이터 로드 중 오류 발생: {e}")