import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Marine Engine Analytics", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    [data-testid="stMetric"] {
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 10px 20px;
        border-radius: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCTION: LOAD DATA ---
def load_data(source_type, source_data):
    try:
        if source_type == "File Upload":
            if source_data.name.endswith('.xlsx'):
                return pd.read_excel(source_data)
            else:
                return pd.read_csv(source_data)
        elif source_type == "Google Spreadsheet":
            if "docs.google.com" in source_data:
                url = source_data.replace('/edit#gid=', '/export?format=csv&gid=')
                if '/export' not in url:
                    url = url.split('/edit')[0] + '/export?format=csv'
                return pd.read_csv(url)
            else:
                st.error("Invalid Google Spreadsheet URL.")
                return None
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# --- HEADER ---
st.title("Marine Engine Operational Analytics")
st.text("System status monitoring and performance analysis dashboard.")
st.divider()

df_raw = None

with st.sidebar:
    st.subheader("Data Input")
    input_method = st.radio("Select Input Method:", ["File Upload", "Google Spreadsheet"])
    
    if input_method == "File Upload":
        source = st.file_uploader("Upload log file (XLSX or CSV)", type=['xlsx', 'csv'])
    else:
        source = st.text_input("Paste Spreadsheet URL:", placeholder="https://docs.google.com/spreadsheets/d/...")

    if source:
        df_raw = load_data(input_method, source)

    if df_raw is not None:
        # 1. Bersihkan baris yang benar-benar kosong
        df_raw = df_raw.dropna(subset=['DATE', 'TIME'])
        
        # 2. Perbaikan format Tanggal
        df_raw['DATE'] = pd.to_datetime(df_raw['DATE'], dayfirst=True, format='mixed')
        
        # 3. FIX DUPLICATE: Hapus baris jika DATE dan TIME nya sama persis
        # Ini akan mencegah error Narwhals DuplicateError
        df_raw = df_raw.drop_duplicates(subset=['DATE', 'TIME'], keep='first')
        
        min_dt = df_raw['DATE'].min().date()
        max_dt = df_raw['DATE'].max().date()

        st.divider()
        st.subheader("Time Filter")
        period_mode = st.selectbox("View Period", ["Custom Range", "Last 7 Days", "Full History"])
        
        if period_mode == "Last 7 Days":
            start_date = max_dt - timedelta(days=6)
            date_range = (start_date, max_dt)
        elif period_mode == "Full History":
            date_range = (min_dt, max_dt)
        else:
            date_range = st.date_input("Date Range", [min_dt, max_dt], min_value=min_dt, max_value=max_dt)

# --- MAIN CONTENT ---
if df_raw is not None:
    # Filter Data berdasarkan range
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        mask = (df_raw['DATE'].dt.date >= date_range[0]) & (df_raw['DATE'].dt.date <= date_range[1])
        df = df_raw.loc[mask].copy()
    else:
        df = df_raw.copy()

    # Identifikasi kolom mesin (Aset)
    exclude = ['DATE', 'TIME', 'ONLINE STATUS', 'OFFLINE STATUS', 'Label_Waktu']
    assets = [col for col in df.columns if col not in exclude and "STATUS" not in col.upper()]
    
    # Buat Label Waktu yang Unik
    df['Label_Waktu'] = df['DATE'].dt.strftime('%d-%m-%y') + " " + df['TIME'].astype(str)

    # Key Metrics
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("Total Monitored Units", len(assets))
    with col_m2:
        current_online = (df.iloc[-1][assets] == 'ONLINE').sum() if not df.empty else 0
        st.metric("Latest Online Units", current_online)
    with col_m3:
        total_slots = len(df) * len(assets)
        uptime_val = ((df[assets].astype(str).apply(lambda x: x.str.strip().str.upper()) == 'ONLINE').sum().sum() / total_slots) * 100 if total_slots > 0 else 0
        st.metric("Fleet Utilization", f"{uptime_val:.1f}%")

    st.write("")

    # Navigation Tabs
    t1, t2, t3 = st.tabs(["Status Heatmap", "Utilization Analysis", "Raw Data Log"])

    with t1:
        st.subheader("Operational Pattern Matrix")
        df_numeric = df.copy()
        for a in assets:
            df_numeric[a] = df[a].astype(str).str.strip().str.upper().map({'ONLINE': 1, 'OFFLINE': 0}).fillna(0)
        
        # Transpose untuk Heatmap
        df_hm = df_numeric.set_index('Label_Waktu')[assets].T
        
        fig_hm = px.imshow(
            df_hm,
            labels=dict(x="Timestamp", y="Machine Unit", color="Status"),
            color_continuous_scale=[[0, '#d63031'], [1, '#27ae60']],
            aspect="auto"
        )
        fig_hm.update_traces(xgap=2, ygap=2) 
        fig_hm.update_layout(coloraxis_showscale=False, height=500, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_hm, use_container_width=True, theme="streamlit")

    with t2:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Unit Utilization (%)")
            uptime_dict = {a: (df[a].astype(str).str.strip().str.upper() == 'ONLINE').sum() / len(df) * 100 for a in assets}
            df_up = pd.DataFrame(list(uptime_dict.items()), columns=['Unit', '%']).sort_values('%')
            fig_bar = px.bar(df_up, x='%', y='Unit', orientation='h', color_discrete_sequence=['#2ecc71'], text_auto='.1f')
            st.plotly_chart(fig_bar, use_container_width=True, theme="streamlit")
        with c2:
            st.subheader("Active Units Trend")
            df_count = pd.DataFrame({
                'Time': df['Label_Waktu'], 
                'Count': (df[assets].astype(str).apply(lambda x: x.str.strip().str.upper()) == 'ONLINE').sum(axis=1)
            })
            fig_line = px.line(df_count, x='Time', y='Count', color_discrete_sequence=['#0984e3'])
            st.plotly_chart(fig_line, use_container_width=True, theme="streamlit")

    with t3:
        st.subheader("Data Export Table")
        st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.write("Please provide data via file upload or spreadsheet URL in the sidebar.")