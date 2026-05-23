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

st.set_page_config(page_title="Sistem Optimasi Produksi", layout="wide")

st.title("🏭 Dashboard Perencanaan Agregat Produksi")

st.sidebar.header("⚙️ Pengaturan Parameter")
strategy = st.sidebar.selectbox("Pilih Strategi Produksi:", ["level", "chase", "mixed"], index=2)

with st.sidebar.expander("💰 Parameter Biaya"):
    c_reg = st.number_input("Biaya Reguler / Unit", value=10.0)
    c_ot = st.number_input("Biaya Lembur / Unit", value=15.0)
    c_rm = st.number_input("Biaya Bahan Baku / Unit", value=5.0)
    c_sub = st.number_input("Biaya Subkontrak / Unit", value=20.0)
    c_hire = st.number_input("Biaya Rekrutmen / Pekerja", value=50.0)
    c_fire = st.number_input("Biaya PHK / Pekerja", value=100.0)
    c_inv = st.number_input("Biaya Simpan / Unit", value=2.0)
    c_short = st.number_input("Biaya Penalti Kekurangan / Unit", value=30.0)

with st.sidebar.expander("🏭 Kapasitas & Pekerja"):
    worker_cap = st.number_input("Kapasitas / Pekerja", value=100.0)
    cap_max = st.number_input("Kapasitas Mesin Maksimal", value=2000.0)
    rm_per_unit = st.number_input("Kebutuhan Bahan Baku / Unit", value=1.0)

with st.sidebar.expander("📦 Kondisi Awal"):
    i0 = st.number_input("Inv Awal (Barang Jadi)", value=100.0)
    i0_rm = st.number_input("Inv Awal (Bahan Baku)", value=500.0)
    w0 = st.number_input("Jumlah Pekerja Awal", value=10.0)

rm_arrival_input = st.text_input("Jadwal Kedatangan Bahan Baku (6 periode)", "500, 500, 500, 500, 500, 500")

st.subheader("📊 Skenario Permintaan (Demand)")
col1, col2, col3 = st.columns(3)
d_opt = col1.text_input("Optimis (20%)", "1500, 1600, 1700, 1800, 1900, 2000")
d_nor = col2.text_input("Normal (60%)", "1000, 1050, 1100, 1150, 1200, 1250")
d_pes = col3.text_input("Pesimis (20%)", "800, 800, 750, 750, 700, 700")

if st.button("🚀 Jalankan Optimasi", type="primary"):
    with st.spinner("Menghitung..."):
        try:
            rm_arrive = [float(x.strip()) for x in rm_arrival_input.split(",")]
            scenarios = [
                DemandScenario("Optimis", [float(x.strip()) for x in d_opt.split(",")], 0.2),
                DemandScenario("Normal", [float(x.strip()) for x in d_nor.split(",")], 0.6),
                DemandScenario("Pesimis", [float(x.strip()) for x in d_pes.split(",")], 0.2)
            ]
            cost = CostParams(c_reg, c_ot, c_rm, c_sub, c_hire, c_fire, c_inv, c_short)
            cap = CapacityParams(worker_cap, cap_max, rm_per_unit)
            init = InitialConditions(i0, i0_rm, w0)
            sup = SupplyParams(rm_arrive)

            df_plan, df_cost = solve_all_scenarios(scenarios, cost, cap, init, sup, strategy)

            df_cost["Total Cost"] = pd.to_numeric(df_cost["Total Cost"])
            df_cost["Expected Cost"] = pd.to_numeric(df_cost["Expected Cost"])

            st.success(f"Optimasi Selesai! Strategi: {strategy.upper()}")
            st.subheader("💵 Ringkasan Biaya")
            st.dataframe(df_cost.style.format({"Total Cost": "{:,.2f}", "Expected Cost": "{:,.2f}"}), use_container_width=True)

            pilih_skenario = st.selectbox("Tampilkan Grafik Skenario:", ["Normal", "Optimis", "Pesimis"])
            df_plot = df_plan[df_plan["Scenario"] == pilih_skenario]

            c1, c2 = st.columns(2)
            c1.plotly_chart(px.line(df_plot, x="Period", y=["Production", "Demand"], title="Produksi vs Demand"), use_container_width=True)
            c2.plotly_chart(px.bar(df_plot, x="Period", y="Inventory", title="Level Inventori"), use_container_width=True)
            
            st.subheader("📝 Tabel Detail")
            st.dataframe(df_plan, use_container_width=True)
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")