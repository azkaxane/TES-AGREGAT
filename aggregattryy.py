import streamlit as st
import pandas as pd
import plotly.express as px
from lp_model import (
    solve_all_scenarios, 
    CostParams, 
    CapacityParams, 
    InitialConditions, 
    SupplyParams, 
    DemandScenario
)

# Konfigurasi Halaman
st.set_page_config(page_title="Sistem Optimasi Produksi", layout="wide")

st.title("🏭 Dashboard Perencanaan Agregat Produksi")
st.markdown("Aplikasi ini menggunakan **Linear Programming** untuk menentukan rencana produksi dengan biaya terendah berdasarkan berbagai skenario permintaan.")

# ==========================================
# SIDEBAR: PENGATURAN PARAMETER
# ==========================================
st.sidebar.header("⚙️ Pengaturan Parameter")

# Pilihan Strategi
strategy = st.sidebar.selectbox(
    "Pilih Strategi Produksi:",
    ["level", "chase", "mixed"],
    index=2,
    help="Level: Produksi stabil. Chase: Produksi ikuti demand. Mixed: Campuran."
)

with st.sidebar.expander("💰 Parameter Biaya"):
    c_reg = st.number_input("Biaya Reguler / Unit", value=10)
    c_ot = st.number_input("Biaya Lembur / Unit", value=15)
    c_rm = st.number_input("Biaya Bahan Baku / Unit", value=5)
    c_sub = st.number_input("Biaya Subkontrak / Unit", value=20)
    c_hire = st.number_input("Biaya Rekrutmen / Pekerja", value=50)
    c_fire = st.number_input("Biaya PHK / Pekerja", value=100)
    c_inv = st.number_input("Biaya Simpan (Inventory) / Unit", value=2)
    c_short = st.number_input("Biaya Penalti Kekurangan (Shortage) / Unit", value=30)

with st.sidebar.expander("🏭 Parameter Kapasitas & Pekerja"):
    worker_cap = st.number_input("Kapasitas Produksi / Pekerja", value=100)
    cap_max = st.number_input("Kapasitas Mesin Maksimal", value=2000)
    rm_per_unit = st.number_input("Kebutuhan Bahan Baku / Unit", value=1)

with st.sidebar.expander("📦 Kondisi Awal (Initial)"):
    i0 = st.number_input("Inventori Awal (Barang Jadi)", value=100)
    i0_rm = st.number_input("Inventori Awal (Bahan Baku)", value=500)
    w0 = st.number_input("Jumlah Pekerja Awal", value=10)

with st.sidebar.expander("🚚 Jadwal Kedatangan Bahan Baku"):
    st.write("Masukkan jumlah kedatangan (pisahkan dengan koma)")
    rm_arrival_input = st.text_input("Jadwal per Periode (T=6)", "500, 500, 500, 500, 500, 500")

# ==========================================
# MAIN PAGE: SKENARIO DEMAND
# ==========================================
st.subheader("📊 Skenario Permintaan (Demand)")
st.write("Masukkan nilai permintaan (demand) untuk 6 periode ke depan, dipisahkan dengan koma.")

col1, col2, col3 = st.columns(3)
with col1:
    d_opt = st.text_input("📈 Optimis (Prob: 20%)", "1500, 1600, 1700, 1800, 1900, 2000")
with col2:
    d_nor = st.text_input("➖ Normal (Prob: 60%)", "1000, 1050, 1100, 1150, 1200, 1250")
with col3:
    d_pes = st.text_input("📉 Pesimis (Prob: 20%)", "800, 800, 750, 750, 700, 700")

# ==========================================
# PROSES OPTIMASI
# ==========================================
if st.button("🚀 Jalankan Optimasi", type="primary"):
    with st.spinner("Sedang memproses perhitungan matematika..."):
        try:
            # 1. Parsing input teks menjadi List of Integers
            rm_arrive = [int(x.strip()) for x in rm_arrival_input.split(",")]
            d_opt_list = [int(x.strip()) for x in d_opt.split(",")]
            d_nor_list = [int(x.strip()) for x in d_nor.split(",")]
            d_pes_list = [int(x.strip()) for x in d_pes.split(",")]

            # 2. Inisiasi Dataclasses
            cost = CostParams(c_reg, c_ot, c_rm, c_sub, c_hire, c_fire, c_inv, c_short)
            cap = CapacityParams(worker_cap, cap_max, rm_per_unit)
            init = InitialConditions(i0, i0_rm, w0)
            sup = SupplyParams(rm_arrive)
            scenarios = [
                DemandScenario("Optimis", d_opt_list, 0.2),
                DemandScenario("Normal", d_nor_list, 0.6),
                DemandScenario("Pesimis", d_pes_list, 0.2)
            ]

            # 3. Jalankan Solver dari lp_model.py
            df_plan, df_cost = solve_all_scenarios(scenarios, cost, cap, init, sup, strategy)

            st.success(f"Optimasi Selesai! Strategi yang digunakan: {strategy.upper()}")

            # ==========================================
            # HASIL VISUALISASI DAN TABEL
            # ==========================================
            st.divider()
            
            # --- Ringkasan Biaya ---
            st.subheader("💵 Ringkasan Biaya Ekspektasi (Expected Cost)")
            st.dataframe(df_cost.style.format("{:,.2f}").highlight_min(color='lightgreen'), use_container_width=True)

            st.divider()

            # --- Visualisasi ---
            st.subheader("📈 Analisis Visual Rencana Produksi")
            
            # Berikan pilihan untuk melihat hasil dari skenario tertentu
            pilih_skenario = st.selectbox("Tampilkan Grafik Untuk Skenario:", ["Normal", "Optimis", "Pesimis"])
            
            # Filter Data berdasarkan skenario yang dipilih
            df_plot = df_plan[df_plan["Scenario"] == pilih_skenario].copy()

            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                # Grafik Produksi vs Demand
                fig1 = px.line(df_plot, x="Period", y=["Production", "Demand"], 
                               title=f"Produksi vs Permintaan ({pilih_skenario})",
                               markers=True, labels={"value": "Jumlah (Unit)", "variable": "Keterangan"})
                st.plotly_chart(fig1, use_container_width=True)

            with col_chart2:
                # Grafik Level Inventori
                fig2 = px.bar(df_plot, x="Period", y="Inventory", 
                              title=f"Level Inventori di Akhir Periode ({pilih_skenario})",
                              color_discrete_sequence=["#00b4d8"])
                st.plotly_chart(fig2, use_container_width=True)

            # --- Tabel Rencana Lengkap ---
            st.subheader("📝 Tabel Rencana Produksi Detail")
            st.dataframe(df_plan, use_container_width=True)

        except Exception as e:
            st.error(f"Terjadi kesalahan dalam pemrosesan data: {e}")
            st.warning("Pastikan input data yang dimasukkan (seperti koma pada demand) sudah benar dan berjumlah 6 periode.")