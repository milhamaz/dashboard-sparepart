# ============================================================
# 🎯 TAB: TARGET SALESMAN
# ============================================================
import streamlit as st

from utils.data_loader import load_kelas_cabang, list_bulan_standar
from utils.target_engine import (
    compute_customer_target, compute_salesman_target, compute_salesman_order,
    compute_salesman_actual, compute_current_salesman,
)
from utils.components import render_card, render_bidirectional_barh_chart, render_styled_table, auto_table_height, hitung_aly
from utils.styles import fmt_rp_full as FMT_RP, highlight_pct as _highlight_pct

_BULAN_NUM = {b: i + 1 for i, b in enumerate(list_bulan_standar)}


def render(df_order_raw, df_supply_final, df_target, df_customer_master, pilih_tahun, pilih_bulan,
           pilih_jenis, pilih_kelas, pilih_area, pilih_cabang, fmt_rp):
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

    # current_salesman dihitung sekali, dipakai bareng buat Target & Order & Actual — biar
    # gak ngulang groupby+sort atas seluruh histori Order 3x per render.
    current_salesman = compute_current_salesman(df_order_scope, pilih_tahun, bulan_num_list)
    salesman_target = compute_salesman_target(customer_target, df_order_scope, pilih_tahun, bulan_num_list, current_salesman=current_salesman)
    salesman_target = salesman_target[salesman_target["Cabang"].isin(pilih_cabang)].copy()

    order_sum = compute_salesman_order(df_order_scope, pilih_tahun, bulan_num_list, current_salesman=current_salesman).set_index("Salesman_Code")["Order"]
    actual_sum = compute_salesman_actual(df_supply_final, pilih_tahun, bulan_num_list, current_salesman).set_index("Salesman_Code")["Actual"]
    salesman_target["Order"] = salesman_target["Salesman_Code"].map(order_sum).fillna(0)
    salesman_target["Actual"] = salesman_target["Salesman_Code"].map(actual_sum).fillna(0)
    salesman_target["O/T"] = salesman_target.apply(lambda r: hitung_aly(r["Order"], r["Target_Salesman"]), axis=1)
    salesman_target["A/T"] = salesman_target.apply(lambda r: hitung_aly(r["Actual"], r["Target_Salesman"]), axis=1)
    salesman_target = salesman_target.sort_values("Target_Salesman", ascending=False).reset_index(drop=True)

    if salesman_target.empty:
        st.info("Tidak ada data Salesman untuk filter yang dipilih.")
        return

    total_target = salesman_target["Target_Salesman"].sum()
    total_order = salesman_target["Order"].sum()
    total_actual = salesman_target["Actual"].sum()
    national_ot = (total_order / total_target * 100) if total_target > 0 else 0.0
    national_at = (total_actual / total_target * 100) if total_target > 0 else 0.0
    salesman_capai = (salesman_target["O/T"] >= 100).sum()
    best_ot_row = salesman_target.loc[salesman_target["O/T"].idxmax()]
    best_at_row = salesman_target.loc[salesman_target["A/T"].idxmax()]

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(render_card("", "ACHIEVEMENT ORDER", f"{national_ot:.1f}%", f"{fmt_rp(total_order)} / {fmt_rp(total_target)}"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("", "ACHIEVEMENT ACTUAL", f"{national_at:.1f}%", f"{fmt_rp(total_actual)} / {fmt_rp(total_target)}"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("✅", "Salesman Capai Target", f"{salesman_capai}", f"dari {len(salesman_target)} salesman"), unsafe_allow_html=True)
    with c4:
        st.markdown(render_card("🥇", "Salesman Terbaik (O/T)", best_ot_row["Salesman_Name"], f"{best_ot_row['O/T']:.1f}"), unsafe_allow_html=True)
    with c5:
        st.markdown(render_card("🥇", "Salesman Terbaik (A/T)", best_at_row["Salesman_Name"], f"{best_at_row['A/T']:.1f}"), unsafe_allow_html=True)

    st.markdown("#### Top 10 Salesman — O/T vs A/T")
    sort_basis = st.radio(
        "Urutkan Top 10 berdasarkan", ["Order (O/T)", "Actual (A/T)"], horizontal=True,
        key="target_salesman_sort_basis",
    )
    sort_col = "O/T" if sort_basis == "Order (O/T)" else "A/T"
    top10 = salesman_target.nlargest(10, sort_col)
    render_bidirectional_barh_chart(
        top10, "Salesman_Name", "O/T", "A/T", "O/T", "A/T",
        left_color="#f97316", right_color="#2563eb", value_fmt=lambda v: f"{v:.1f}%",
        key="chart_target_salesman_top10", xaxis_title="% (O/T kiri • A/T kanan)",
        left_value_label="Pencapaian O/T", right_value_label="Pencapaian A/T",
        left_hover_extra=[("Order", "Nilai Order", fmt_rp)],
        right_hover_extra=[("Actual", "Nilai Actual", fmt_rp)],
    )

    st.markdown("#### Ranking Lengkap Target Salesman")
    search_query = st.text_input(
        "Cari Salesman (kode/nama)", key="target_salesman_search_query",
        placeholder="Ketik kode atau nama salesman...",
    )
    table_source = salesman_target
    if search_query.strip():
        q = search_query.strip().upper()
        table_source = table_source[
            table_source["Salesman_Code"].astype(str).str.upper().str.contains(q, na=False)
            | table_source["Salesman_Name"].astype(str).str.upper().str.contains(q, na=False)
        ]

    display = table_source[["Salesman_Name", "Cabang", "Target_Salesman", "Order", "Actual", "O/T", "A/T"]].copy()
    display = display.rename(columns={"Salesman_Name": "Salesman", "Target_Salesman": "Target"})

    render_styled_table(
        display, _highlight_pct, pct_cols=["O/T", "A/T"],
        fmt_dict={"Target": FMT_RP, "Order": FMT_RP, "Actual": FMT_RP, "O/T": "{:.2f}%", "A/T": "{:.2f}%"},
        height=min(auto_table_height(len(display)), 600),
    )
