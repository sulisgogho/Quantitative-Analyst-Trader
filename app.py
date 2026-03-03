import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Advanced Forex Dashboard", page_icon="📈", layout="wide")
st.title("📈 Advanced Performance Dashboard: Master Trader")
st.markdown("Dashboard ini menyajikan analisa mendalam (Quant Analysis) dari histori transaksi Master Trader.")

# --- MEMUAT & MEMBERSIHKAN DATA ---
@st.cache_data
def load_data():
    df = pd.read_csv('Sell and Buy.csv', sep=';')
    
    # Membersihkan kolom finansial
    cols_to_clean = ['Commission', 'Swap', 'Profit']
    for col in cols_to_clean:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    df['Net_Profit'] = df['Profit'] + df['Commission'] + df['Swap']
    
    # Membersihkan dan memformat kolom waktu (Time = Buka, Time.1 = Tutup)
    df_trades = df.dropna(subset=['Time.1', 'Time']).copy()
    df_trades['Time'] = pd.to_datetime(df_trades['Time'], format='%Y.%m.%d %H:%M:%S', errors='coerce')
    df_trades['Time.1'] = pd.to_datetime(df_trades['Time.1'], format='%Y.%m.%d %H:%M:%S', errors='coerce')
    df_trades = df_trades.dropna(subset=['Time', 'Time.1']).sort_values(by='Time.1').reset_index(drop=True)
    
    # Kalkulasi Kumulatif & Durasi
    df_trades['Cumulative_Profit'] = df_trades['Net_Profit'].cumsum()
    df_trades['Duration'] = df_trades['Time.1'] - df_trades['Time']
    df_trades['Month_Year'] = df_trades['Time.1'].dt.to_period('M').astype(str)
    
    return df_trades

try:
    df_trades = load_data()
except FileNotFoundError:
    st.error("File 'Sell and Buy.csv' tidak ditemukan! Letakkan di folder yang sama dengan app.py")
    st.stop()

# --- KALKULASI METRIK LANJUTAN ---
# 1. Pertumbuhan Dasar & Drawdown
cumulative = df_trades['Cumulative_Profit']
peaks = cumulative.cummax()
drawdowns = peaks - cumulative
max_drawdown = drawdowns.max()

final_growth = cumulative.iloc[-1]
total_trades = len(df_trades)
win_rate = (df_trades['Net_Profit'] > 0).mean() * 100

# 2. Profit Factor & Risk/Reward Ratio
gross_profit = df_trades[df_trades['Net_Profit'] > 0]['Net_Profit'].sum()
gross_loss = abs(df_trades[df_trades['Net_Profit'] < 0]['Net_Profit'].sum())
profit_factor = gross_profit / gross_loss if gross_loss != 0 else 0

avg_win = df_trades[df_trades['Net_Profit'] > 0]['Net_Profit'].mean()
avg_loss = abs(df_trades[df_trades['Net_Profit'] < 0]['Net_Profit'].mean())
rr_ratio = avg_win / avg_loss if avg_loss != 0 else 0

# 3. Streaks (Kemenangan/Kekalahan Beruntun)
df_trades['Win'] = (df_trades['Net_Profit'] > 0).astype(int)
df_trades['Loss'] = (df_trades['Net_Profit'] < 0).astype(int)
win_streaks = df_trades['Win'].groupby((df_trades['Win'] != df_trades['Win'].shift()).cumsum()).sum()
loss_streaks = df_trades['Loss'].groupby((df_trades['Loss'] != df_trades['Loss'].shift()).cumsum()).sum()
max_consecutive_wins = win_streaks.max()
max_consecutive_losses = loss_streaks.max()

# --- BAGIAN 1: KPI UTAMA ---
st.markdown("### 📊 Indikator Kinerja Utama (KPI)")
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Net Profit (Growth)", f"${final_growth:,.2f}")
kpi2.metric("Max Drawdown", f"-${max_drawdown:,.2f}", delta_color="inverse")
kpi3.metric("Profit Factor", f"{profit_factor:.2f}", "Sehat (> 1.5)" if profit_factor > 1.5 else "Perlu Evaluasi")
kpi4.metric("Win Rate", f"{win_rate:.1f}%")
kpi5.metric("R/R Ratio", f"1 : {rr_ratio:.2f}")

st.markdown("---")

# --- BAGIAN 2: GRAFIK SALDO KUMULATIF ---
st.markdown("### 📈 Grafik Pertumbuhan Akun (Cumulative Profit)")
fig_growth = px.line(df_trades, x='Time.1', y='Cumulative_Profit', 
                     labels={'Time.1': 'Waktu (Close Trade)', 'Cumulative_Profit': 'Saldo ($)'},
                     template="plotly_white")
fig_growth.update_traces(line=dict(color='#1f77b4', width=2))
st.plotly_chart(fig_growth, use_container_width=True)

# --- BAGIAN 3: ANALISA KEDALAMAN (BAR & PIE CHART) ---
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("#### 🥇 Profit Berdasarkan Simbol (Pair Valas)")
    # Hitung profit per simbol
    symbol_perf = df_trades.groupby('Symbol')['Net_Profit'].sum().reset_index().sort_values('Net_Profit', ascending=True)
    fig_symbol = px.bar(symbol_perf, x='Net_Profit', y='Symbol', orientation='h',
                        color='Net_Profit', color_continuous_scale='Viridis',
                        labels={'Net_Profit': 'Total Profit ($)', 'Symbol': 'Pair'})
    st.plotly_chart(fig_symbol, use_container_width=True)

with col_chart2:
    st.markdown("#### 🟢 Buy vs 🔴 Sell Performance")
    # Hitung total profit berdasarkan tipe transaksi
    type_perf = df_trades.groupby('Type')['Net_Profit'].sum().reset_index()
    # Ganti nilai negatif menjadi 0 untuk pie chart jika ada total loss, atau gunakan bar chart jika negatif
    # Menggunakan Bar Chart agar lebih aman jika salah satu arah (Sell) bernilai minus secara keseluruhan
    fig_type = px.bar(type_perf, x='Type', y='Net_Profit', color='Type',
                      color_discrete_map={'Buy': '#2ca02c', 'Sell': '#d62728'},
                      labels={'Net_Profit': 'Total Profit ($)', 'Type': 'Tipe Transaksi'})
    st.plotly_chart(fig_type, use_container_width=True)

# --- BAGIAN 4: PERFORMA BULANAN & PSIKOLOGI TRADING ---
col_chart3, col_chart4 = st.columns(2)

with col_chart3:
    st.markdown("#### 📅 Kinerja Per Bulan (2024)")
    monthly_perf = df_trades.groupby('Month_Year')['Net_Profit'].sum().reset_index()
    fig_month = px.bar(monthly_perf, x='Month_Year', y='Net_Profit', text_auto='.2s',
                       labels={'Month_Year': 'Bulan', 'Net_Profit': 'Profit ($)'},
                       color='Net_Profit', color_continuous_scale='Blues')
    st.plotly_chart(fig_month, use_container_width=True)

with col_chart4:
    st.markdown("#### 🧠 Analisa Psikologi & Durasi")
    st.info(f"⏱️ **Rata-rata Menahan Posisi (Hold Time):** {df_trades['Duration'].mean().round('s')}")
    st.success(f"🔥 **Kemenangan Beruntun Terbanyak (Max Win Streak):** {int(max_consecutive_wins)} kali berturut-turut")
    st.error(f"💔 **Kekalahan Beruntun Terparah (Max Loss Streak):** {int(max_consecutive_losses)} kali berturut-turut")
    st.warning(f"💵 **Rata-rata Menang (Avg Win):** ${avg_win:.2f} | **Rata-rata Kalah (Avg Loss):** ${avg_loss:.2f}")

# --- BAGIAN 5: TABEL RAW DATA ---
st.markdown("---")
with st.expander("Tampilkan Rekam Jejak Detail (Tabel Data)"):
    st.dataframe(df_trades[['Time', 'Time.1', 'Type', 'Symbol', 'Volume', 'Net_Profit', 'Duration']].sort_values('Time.1', ascending=False), use_container_width=True)