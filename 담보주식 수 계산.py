import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="담보 주식 수 대시보드", layout="wide")

# --- CSS: 지표 박스 여백(Padding) 및 디자인 미세 조정 ---
st.markdown("""
    <style>
    * { outline: none !important; }
    .stApp { background-color: #f8fbff; }
    [data-testid="stSidebar"] { background-color: #eef6ff; border-right: 1px solid #d1e3ff; }
    .main-title { font-size: 26px !important; font-weight: bold; color: #003366; margin-bottom: 20px; }
    
    /* 요약 지표(Metric) 박스 크기 및 여백 확대 */
    [data-testid="stMetric"] { 
        background-color: #ffffff; 
        border: 1px solid #d1e3ff; 
        border-radius: 12px; 
        padding: 25px 20px !important; 
        box-shadow: 2px 4px 12px rgba(0,51,102,0.08); 
        transition: all 0.3s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 2px 6px 15px rgba(0,51,102,0.12);
    }
    
    [data-testid="stMetricLabel"] { font-size: 15px !important; color: #555 !important; margin-bottom: 10px !important; }
    [data-testid="stMetricValue"] { font-size: 28px !important; color: #003366 !important; font-weight: 700 !important; }

    input:focus { border-color: #0056b3 !important; box-shadow: none !important; }
    </style>
    <div class="main-title">담보 주식 수 대시보드</div>
    """, unsafe_allow_html=True)

# --- 사이드바 ---
st.sidebar.header("📌 설정 및 기간 선택")
bond_balance_usd = st.sidebar.number_input("채권 잔액 (USD)", min_value=0.0, value=59466710.0, step=1000.0)
st.sidebar.markdown(f"<div style='color: #0056b3; font-size: 19px; font-weight: bold; margin-top: -10px; margin-bottom: 15px;'>$ {bond_balance_usd:,.2f}</div>", unsafe_allow_html=True)

stock_symbol = st.sidebar.text_input("말레이시아 주식 티커", value="5238")

today = datetime.now()
default_start = today - timedelta(days=7)
date_range = st.sidebar.date_input("VWAP 계산 기간", value=(default_start, today))

full_ticker = f"{stock_symbol.zfill(4)}.KL" if not stock_symbol.endswith(".KL") else stock_symbol

try:
    raw_df = yf.download(full_ticker, period="1mo", interval="1d")
    fx_raw = yf.download("USDMYR=X", period="5d")
    
    if raw_df.empty:
        st.error("데이터를 불러오지 못했습니다.")
    else:
        df_all = raw_df.copy()
        if isinstance(df_all.columns, pd.MultiIndex):
            df_all.columns = df_all.columns.get_level_values(0)
        
        mask = (df_all.index.date >= date_range[0]) & (df_all.index.date <= date_range[1])
        df = df_all.loc[mask].copy()

        try: default_fx = float(fx_raw['Close'].iloc[-1])
        except: default_fx = 4.4500
        input_fx = st.sidebar.number_input("적용 환율 (USD/MYR)", value=default_fx, format="%.4f")

        if not df.empty:
            # VWAP 계산
            vwap_val = (df['Close'] * df['Volume']).sum() / df['Volume'].sum()
            
            # 필요 담보 주식 수 계산 (목표 비율 115%)
            required_shares = (bond_balance_usd * input_fx * 1.15) / vwap_val
            
            # 채권 대비 % 계산 (LTV)
            # 수식: (필요 주식 수 * VWAP) / (채권 잔액 * 환율) * 100
            collateral_ratio = (required_shares * vwap_val) / (bond_balance_usd * input_fx) * 100

            # --- 상단 지표 박스 섹션 ---
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("선택 기간 VWAP (MYR)", f"{vwap_val:.4f}")
            with m2: st.metric("필요 담보 주식 수", f"{int(required_shares):,} 주")
            with m3: st.metric("채권 대비 % (LTV)", f"{collateral_ratio:.1f}%")

            st.markdown("<hr style='border: 0.5px solid #d1e3ff; margin: 30px 0;'>", unsafe_allow_html=True)

            # --- 차트 섹션 ---
            c_left, c_right = st.columns(2)
            date_labels = df.index.strftime('%y-%m-%d').tolist()

            def get_layout():
                return dict(
                    margin=dict(l=10, r=10, t=50, b=10), height=320,
                    plot_bgcolor='white', paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(tickformat='%y-%m-%d', type='category', gridcolor='#f0f5ff', tickangle=0),
                    yaxis=dict(gridcolor='#f0f5ff', autorange=True), showlegend=False
                )

            with c_left:
                st.markdown("<span style='color: #004080; font-weight: bold; font-size: 17px;'>📈 Stock Price (MYR)</span>", unsafe_allow_html=True)
                fig_p = go.Figure(go.Scatter(x=date_labels, y=df['Close'], mode='lines+markers', line=dict(color='#0056b3', width=2.5)))
                fig_p.update_layout(get_layout())
                st.plotly_chart(fig_p, use_container_width=True)

            with c_right:
                st.markdown("<span style='color: #004080; font-weight: bold; font-size: 17px;'>📊 Trading Volume (Million)</span>", unsafe_allow_html=True)
                fig_v = go.Figure(go.Bar(x=date_labels, y=df['Volume'] / 1000000, marker_color='#66b2ff'))
                fig_v.update_layout(get_layout())
                fig_v.add_annotation(
                    xref="paper", yref="paper", x=1, y=1.12,
                    text="# of shares, million", showarrow=False, font=dict(size=13, color="#666")
                )
                st.plotly_chart(fig_v, use_container_width=True)

            with st.expander("📝 VWAP 상세 데이터 보기"):
                df_display = df[['Close', 'Volume']].copy()
                df_display.index = df_display.index.strftime('%y-%m-%d')
                st.dataframe(df_display.style.format("{:,.2f}"), use_container_width=True)

except Exception as e:
    st.error(f"데이터 로드 중 오류 발생: {e}")