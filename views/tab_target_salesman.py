# ============================================================
# 🎯 TAB: TARGET SALESMAN
# ============================================================
import streamlit as st

from utils.data_loader import load_kelas_cabang, list_bulan_standar
from utils.target_engine import compute_customer_target, compute_salesman_target, compute_salesman_order, compute_current_salesman
from utils.components import render_card, render_topn_barh_chart, render_styled_table, auto_table_height, hitung_aly
from utils.styles import fmt_rp_full as FMT_RP, highlight_achievement_pct as _highlight_ot

_BULAN_NUM = {b: i + 1 for i, b in enumerate(list_bulan_standar)}


def render(df_order_raw, df_target, df_customer_master, pilih_tahun, pilih_bulan,
           pilih_jenis, pilih_kelas, pilih_area, pilih_cabang, fmt_rp):
    st.caption(
        "Target per Salesman diturunkan dari Target Cabang (Tgt_Cabang.xlsx), dipecah "
        "proporsional ke tiap Customer_No berbasis **Order** (bukan Actual/Supply — Supply "
        "itu eksekusi logistik pihak ketiga, kurang murni cerminan performa sales), pakai "
        "window trailing 12 bulan yang di-recompute tiap ganti bulan. Kalau ada customer "
        "yang di-oper ke Salesman lain (resign/pindah cabang/staff baru pegang customer "
        "eksisting), Target-nya otomatis ikut pindah — gak perlu deteksi manual."
    )

    bulan_num_list = sorted(_BULAN_NUM[b] for b in pilih_bulan if b in _BULAN_NUM)
    if not bulan_num_list:
        st.info("Tidak ada Bulan yang dipilih di Filter General.")
        return

    # Batasi populasi Customer sesuai Jenis/Kelas/Area di Filter General SEBELUM masuk ke
    # cascade — konsisten dengan tab Target Customer, dan supaya ganti Jenis/Kelas/Area di
    # Filter General beneran ngefek ke tab ini juga (sebelumnya cuma Cabang yang kepakai).
    allowed_customers = df_customer_master[
        df_customer_master["Jenis_Customer"].isin(pilih_jenis)
        & df_customer_master["Kelas_Customer"].isin(pilih_kelas)
        & df_customer_master["Kode_Area"].isin(pilih_area)
    ]["Kode_Customer"]
    df_order_scope = df_order_raw[df_order_raw["Customer_No"].isin(allowed_customers)]

    df_kelas_cabang = load_kelas_cabang()
    customer_target = compute_customer_target(df_order_scope, df_target, df_kelas_cabang, pilih_tahun, bulan_num_list)
    if customer_target.empty:
        st.info("Tidak ada data Target/Order untuk filter yang dipilih.")
        return

    # current_salesman dihitung sekali, dipakai bareng buat Target & Order — biar gak
    # ngulang groupby+sort atas seluruh histori Order 2x per render.
    current_salesman = compute_current_salesman(df_order_scope, pilih_tahun, bulan_num_list)
    salesman_target = compute_salesman_target(customer_target, df_order_scope, pilih_tahun, bulan_num_list, current_salesman=current_salesman)
    salesman_target = salesman_target[salesman_target["Cabang"].isin(pilih_cabang)].copy()

    order_sum = compute_salesman_order(df_order_scope, pilih_tahun, bulan_num_list, current_salesman=current_salesman).set_index("Salesman_Code")["Order"]
    salesman_target["Order"] = salesman_target["Salesman_Code"].map(order_sum).fillna(0)
    salesman_target["Achievement (%)"] = salesman_target.apply(
        lambda r: hitung_aly(r["Order"], r["Target_Salesman"]), axis=1
    )
    salesman_target = salesman_target.sort_values("Target_Salesman", ascending=False).reset_index(drop=True)

    if salesman_target.empty:
        st.info("Tidak ada data Salesman untuk filter yang dipilih.")
        return

    total_target = salesman_target["Target_Salesman"].sum()
    total_order = salesman_target["Order"].sum()
    national_ot = (total_order / total_target * 100) if total_target > 0 else 0.0
    salesman_capai = (salesman_target["Achievement (%)"] >= 100).sum()
    best_row = salesman_target.loc[salesman_target["Achievement (%)"].idxmax()]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("", "Achievement Nasional (O/T)", f"{national_ot:.1f}%", f"{fmt_rp(total_order)} / {fmt_rp(total_target)}"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("✅", "Salesman Capai Target", f"{salesman_capai}", f"dari {len(salesman_target)} salesman"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("🥇", "Salesman Terbaik (%O/T)", best_row["Salesman_Name"], f"{best_row['Achievement (%)']:.1f}%"), unsafe_allow_html=True)
    with c4:
        st.markdown(render_card("", "Total Target", fmt_rp(total_target), f"Total Order: {fmt_rp(total_order)}"), unsafe_allow_html=True)

    st.markdown("#### Top 10 Salesman — %O/T")
    top10 = salesman_target.nlargest(10, "Achievement (%)")
    render_topn_barh_chart(
        top10, "Salesman_Name", "Achievement (%)", top_n=10, color="#f97316",
        value_fmt=lambda v: f"{v:.1f}%", xaxis_title="%O/T", key="chart_target_salesman_top10",
    )

    st.markdown("#### Ranking Lengkap Target Salesman")
    display = salesman_target[["Salesman_Name", "Cabang", "Target_Salesman", "Order", "Achievement (%)"]].copy()
    display.insert(0, "Rank", range(1, len(display) + 1))
    display = display.rename(columns={"Salesman_Name": "Salesman", "Target_Salesman": "Target"})

    render_styled_table(
        display, _highlight_ot, pct_cols=["Achievement (%)"],
        fmt_dict={"Target": FMT_RP, "Order": FMT_RP, "Achievement (%)": "{:.2f}%"},
        height=min(auto_table_height(len(display)), 600),
    )
