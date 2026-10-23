import os
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Digital Payment Fraud Shield",
    page_icon="🛡️",
    layout="wide"
)

# Đường dẫn file dữ liệu kết quả
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SUBMISSION_PATH = os.path.join(BASE_DIR, "submission_output.csv")
TRANSACTIONS_PATH = os.path.join(BASE_DIR, "01_data", "transactions.csv")


@st.cache_data
def load_data():
    if not os.path.exists(SUBMISSION_PATH):
        return None, None
    sub_df = pd.read_csv(SUBMISSION_PATH)
    tx_df = pd.read_csv(TRANSACTIONS_PATH) if os.path.exists(TRANSACTIONS_PATH) else None
    if tx_df is not None:
        full_df = sub_df.merge(tx_df, on='transaction_id', how='left')
    else:
        full_df = sub_df
    return sub_df, full_df


sub_df, full_df = load_data()

# HEADER
st.title("🛡️ Digital Payment Fraud Shield - Risk Monitoring Center")
st.caption("Festival Chuyển đổi số 2026 | Bảng B - Decision Support System")

if sub_df is None:
    st.error("⚠️ Chưa tìm thấy file `submission_output.csv`. Vui lòng chạy file `pipeline.py` trước để sinh kết quả.")
    st.stop()

# THANH ĐIỀU HƯỚNG BÊN TRÁI (SIDEBAR)
st.sidebar.header("🔍 Bộ Lọc Điều Tra")
selected_level = st.sidebar.multiselect(
    "Lọc theo cấp độ rủi ro (Risk Level):",
    options=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
    default=['CRITICAL', 'HIGH']
)
min_score = st.sidebar.slider("Ngưỡng điểm rủi ro tối thiểu (Risk Score):", 0.0, 1.0, 0.40, 0.05)
only_fraud = st.sidebar.checkbox("Chỉ hiện các giao dịch bị cảnh báo (predicted_fraud = 1)", value=True)

# Lọc dữ liệu theo điều kiện
filtered_df = full_df[
    (full_df['risk_level'].isin(selected_level)) &
    (full_df['risk_score'] >= min_score)
    ]
if only_fraud:
    filtered_df = filtered_df[filtered_df['predicted_fraud'] == 1]

# CÁC CHỈ SỐ TỔNG QUAN (METRICS ROW)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Tổng giao dịch", f"{len(sub_df):,}")
col2.metric("Số cảnh báo rủi ro",
            f"{sub_df['predicted_fraud'].sum():,} ({sub_df['predicted_fraud'].mean() * 100:.1f}%)")
critical_count = (sub_df['risk_level'] == 'CRITICAL').sum()
col3.metric("Mức CRITICAL (Nguy cấp)", f"{critical_count:,}", delta_color="inverse")
col4.metric("Thời gian xử lý / tx", f"{sub_df['processing_time_ms'].iloc[0]} ms")

st.markdown("---")

# BẢNG ĐIỀU TRA CHI TIẾT
st.subheader("📋 Danh Sách Giao Dịch Cần Ưu Tiên Rà Soát (Priority Queue)")
st.write(f"Đang hiển thị **{len(filtered_df)}** giao dịch phù hợp với bộ lọc:")

display_cols = ['priority_rank', 'transaction_id', 'risk_score', 'risk_level', 'alert_reason']
if 'amount' in filtered_df.columns:
    display_cols.insert(2, 'amount')
if 'customer_id' in filtered_df.columns:
    display_cols.insert(3, 'customer_id')

st.dataframe(
    filtered_df[display_cols].sort_values(by='priority_rank'),
    use_container_width=True,
    height=380
)

# CHI TIẾT VỤ VIỆC & HUMAN-IN-THE-LOOP FEEDBACK
st.markdown("---")
st.subheader("🕵️ Chi Tiết Vụ Việc & Quyết Định Của Chuyên Viên (Case Review)")

c_select, c_action = st.columns([2, 1])
with c_select:
    tx_to_inspect = st.selectbox(
        "Chọn Transaction ID để kiểm tra bằng chứng rủi ro:",
        options=filtered_df['transaction_id'].tolist() if len(filtered_df) > 0 else []
    )

if tx_to_inspect:
    case_data = filtered_df[filtered_df['transaction_id'] == tx_to_inspect].iloc[0]

    st.info(f"**Căn cứ cảnh báo (`alert_reason`):** {case_data['alert_reason']}")

    col_d1, col_d2, col_d3 = st.columns(3)
    col_d1.write(f"- **Điểm rủi ro (Risk Score):** `{case_data['risk_score']}`")
    col_d1.write(f"- **Cấp độ (Risk Level):** `{case_data['risk_level']}`")
    col_d2.write(f"- **Độ tin cậy mô hình:** `{case_data['confidence']}`")
    col_d2.write(f"- **Mô hình phụ trách:** `{case_data['model_name']}`")
    if 'amount' in case_data:
        col_d3.write(f"- **Số tiền:** `{case_data['amount']:,.0f} VND`")
    if 'channel' in case_data:
        col_d3.write(f"- **Kênh giao dịch:** `{case_data['channel']}`")

    with c_action:
        st.markdown("**Hành động của chuyên viên (Human-in-the-loop):**")
        action = st.radio("Quyết định rà soát:",
                          ["Duyệt giao dịch", "Yêu cầu KYC/SmartOTP", "Khóa thẻ / Chặn giao dịch"], key="action_radio")
        if st.button("Xác nhận xử lý case"):
            st.success(f"Đã ghi nhận quyết định '{action}' cho giao dịch {tx_to_inspect} vào Audit Log!")