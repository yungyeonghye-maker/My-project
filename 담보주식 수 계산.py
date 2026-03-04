# --- 사이드바에 현재 보유 주식 수 입력칸 추가 ---
st.sidebar.markdown("---")
current_shares = st.sidebar.number_input("현재 담보 설정 주식 수", min_value=0, value=25000000)

# --- 기존 계산 로직 아래에 추가 ---
if not df.empty:
    vwap_val = (df['Close'] * df['Volume']).sum() / df['Volume'].sum()
    
    # 목표 주식 수 (115% 기준)
    target_shares_115 = (bond_balance_usd * input_fx * 1.15) / vwap_val
    
    # 현재 담보 비율 계산 (현재가 기준)
    current_price = df['Close'].iloc[-1]
    current_collateral_ratio = (current_shares * current_price) / (bond_balance_usd * input_fx)
    
    # 메트릭 표시
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("현재 담보 비율", f"{current_collateral_ratio*100:.1f}%")
    with m2: st.metric("선택 기간 VWAP", f"{vwap_val:.4f}")
    with m3: st.metric("목표 주식 수 (115%)", f"{int(target_shares_115):,} 주")

    # --- 리밸런싱 가이드 섹션 ---
    st.markdown("### 🔄 Revaluation 가이드")
    
    diff = int(target_shares_115 - current_shares)
    
    if current_collateral_ratio > 1.25:
        st.success(f"✅ **담보 과다 상태 (125% 초과)**: 약 **{abs(diff):,} 주**를 반환받아 115% 수준으로 맞출 수 있습니다.")
    elif current_collateral_ratio < 1.00:
        st.error(f"⚠️ **담보 부족 상태 (100% 미만)**: 약 **{diff:,} 주**를 추가 설정하여 115% 수준을 유지해야 합니다.")
    else:
        st.info("ℹ️ **유지 상태**: 현재 담보 비율이 관리 범위 내(100%~125%)에 있습니다.")