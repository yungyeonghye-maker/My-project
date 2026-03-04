import streamlit as st
import yfinance as yf
import pandas as pd
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
    <div class="main-title">담보 주식 수 관리 대시보드</div>
    """, unsafe_allow_html=True)

# --- 사이드바 ---
st.sidebar.header("📌 설정 및 기간 선택")
bond_balance_usd = st.sidebar.number_input("채권 잔액 (USD)", min_value=0.0, value=59466710.0, step=1000.0)
st.sidebar.markdown(f"<div style='color: #0056b3; font-size: 18px; font-weight: bold; margin-top: -10px; margin-bottom: 15px;'>$ {bond_balance_usd:,.2f}</div>", unsafe_allow_html=True)

stock_symbol = st.sidebar.text_input("말레이시아 주식 티커", value="5238")

today = datetime.now()
# 1. 예치 VWAP 기간 설정
st.sidebar.subheader("📅 예치 VWAP 기간")
deposit_date_range = st.sidebar.date_input("예치용 시작/종료일", value=(today - timedelta(days=7), today), key='deposit_date')

# 2. 평가 VWAP 기간 설정
st.sidebar.subheader("📅 평가 VWAP 기간")
eval_date_range = st.sidebar.date_input("평가용 시작/종료일", value=(today - timedelta(days=1), today), key='eval_date')

full_ticker = f"{stock_symbol.zfill(4)}.KL" if not stock_symbol.endswith(".KL") else stock_symbol

def calculate_vwap(data, date_range):
    """특정 기간의 5일 가중평균(VWAP) 계산 함수"""
    mask = (data.index.date >= date_range[0]) & (data.index.date <= date_range[1])
    target_df = data.loc[mask].copy()
    if target_df.empty:
        return 0
    vwap = (target_df['Close'] * target_df['Volume']).sum() / target_df['Volume'].sum()
    return vwap

try:
    # 데이터 다운로드 (충분한 기간 확보를 위해 3mo)
    raw_df = yf.download(full_ticker, period="3mo", interval="1d")
    fx_raw = yf.download("USDMYR=X", period="5d")
    
    if raw_df.empty:
        st.error("데이터를 불러오지 못했습니다.")
    else:
        df_all = raw_df.copy()
        if isinstance(df_all.columns, pd.MultiIndex):
            df_all.columns = df_all.columns.get_level_values(0)
        
        # 환율 설정
        try: default_fx = float(fx_raw['Close'].iloc[-1])
        except: default_fx = 4.4500
        input_fx = st.sidebar.number_input("적용 환율 (USD/MYR)", value=default_fx, format="%.4f")

        # --- 핵심 로직 계산 ---
        
        # 1. 예치 VWAP (MYR)
        deposit_vwap = calculate_vwap(df_all, deposit_date_range)
        
        # 2. 평가 VWAP (MYR)
        eval_vwap = calculate_vwap(df_all, eval_date_range)
        
        if deposit_vwap > 0 and eval_vwap > 0:
            # 3. 담보 주식 수 = (채권 잔액 * 환율 * 115%) / 예치 VWAP
            required_shares = (bond_balance_usd * input_fx * 1.15) / deposit_vwap
            
            # 4. 채권 대비 % (LTV) = (담보 주식 수 * 평가 VWAP) / (채권 잔액 * 환율) * 100
            collateral_ratio = (required_shares * eval_vwap) / (bond_balance_usd * input_fx) * 100

            # --- 상단 지표 박스 섹션 ---
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.metric("예치 VWAP (MYR)", f"{deposit_vwap:.4f}")
            with m2: st.metric("담보 주식 수", f"{int(required_shares):,} 주")
            with m3: st.metric("평가 VWAP (MYR)", f"{eval_vwap:.4f}")
            with m4: st.metric("채권 대비 %", f"{collateral_ratio:.2f}%")

            st.markdown("<hr style='border: 0.5px solid #d1e3ff; margin: 30px 0;'>", unsafe_allow_html=True)
            
            # 차트가 삭제된 자리에 상세 데이터 테이블만 배치
            st.subheader("📋 데이터 요약 정보")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**[예치 기간 데이터]**")
                mask_dep = (df_all.index.date >= deposit_date_range[0]) & (df_all.index.date <= deposit_date_range[1])
                st.dataframe(df_all.loc[mask_dep, ['Close', 'Volume']].style.format("{:,.2f}"), use_container_width=True)
            with col_b:
                st.write("**[평가 기간 데이터]**")
                mask_eval = (df_all.index.date >= eval_date_range[0]) & (df_all.index.date <= eval_date_range[1])
                st.dataframe(df_all.loc[mask_eval, ['Close', 'Volume']].style.format("{:,.2f}"), use_container_width=True)

        else:
            st.warning("선택한 기간에 해당하는 주식 데이터가 없습니다. 날짜를 조정해 주세요.")

except Exception as e:
    st.error(f"데이터 로드 중 오류 발생: {e}")