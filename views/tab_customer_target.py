# ============================================================
# 📊 TAB: TARGET CUSTOMER
# ============================================================
import streamlit as st
import pandas as pd

from utils.data_loader import load_kelas_cabang, list_bulan_standar
from utils.target_engine import compute_customer_target
from utils.components import (
    render_card, render_bidirectional_barh_chart, render_styled_table, auto_table_height,
    hitung_aly, build_scope_title, scope_label_periode,
)
from utils.styles import fmt_rp_full as FMT_RP, highlight_pct as _highlight_ot

_BULAN_NUM = {b: i + 1 for i, b in enumerate(list_bulan_standar)}


def render(df_order_raw, df_supply_final, df_target, df_customer_master, pilih_tahun, pilih_bulan,
           pilih_jenis, pilih_kelas, pilih_area, pilih_cabang, cabang_list, fmt_rp):
    bulan_num_list = sorted(_BULAN_NUM[b] for b in pilih_bulan if b in _BULAN_NUM)
    if not bulan_num_list:
        st.info("Tidak ada Bulan yang dipilih di Filter General.")
        return

    df_kelas_cabang = load_kelas_cabang()
    customer_target = compute_customer_target(df_order_raw, df_target, df_kelas_cabang, pilih_tahun, bulan_num_list)
    if customer_target.empty:
        st.info("Tidak ada data Target/Order untuk filter yang dipilih.")
        return

    # Atribut Jenis/Kelas/Area — dari Customer Master, bukan dari transaksi, biar customer
    # yang 0 transaksi pun tetap kena filter dengan benar (konsisten dgn tab Reaktivasi).
    attr = df_customer_master.set_index("Kode_Customer")[["Nama_Customer", "Jenis_Customer", "Kelas_Customer", "Kode_Area"]]
    customer_target = customer_target.merge(attr, left_on="Customer_No", right_index=True, how="left")

    customer_target = customer_target[
        customer_target["Cabang"].isin(pilih_cabang)
        & customer_target["Jenis_Customer"].isin(pilih_jenis)
        & customer_target["Kelas_Customer"].isin(pilih_kelas)
        & customer_target["Kode_Area"].isin(pilih_area)
    ].copy()

    order_scope = df_order_raw[
        (df_order_raw["Tahun"] == pilih_tahun) & (df_order_raw["Bulan_Num"].isin(bulan_num_list))
    ]
    order_sum = order_scope.groupby("Customer_No")["Order"].sum()

    # Actual (Supply) — beda dari Order, cuma difilter Tahun berjalan (df_supply_final dari
    # render_top_filters() sudah termasuk 2 tahun sekaligus buat keperluan YoY di tab lain).
    if df_supply_final is not None and not df_supply_final.empty:
        actual_sum = df_supply_final[df_supply_final["Tahun"] == pilih_tahun].groupby("Customer_No")["Actual"].sum()
    else:
        actual_sum = None

    customer_target["Order"] = customer_target["Customer_No"].map(order_sum).fillna(0)
    customer_target["Actual"] = customer_target["Customer_No"].map(actual_sum).fillna(0) if actual_sum is not None else 0.0
    customer_target["O/T"] = customer_target.apply(lambda r: hitung_aly(r["Order"], r["Target_Customer"]), axis=1)
    customer_target["A/T"] = customer_target.apply(lambda r: hitung_aly(r["Actual"], r["Target_Customer"]), axis=1)
    customer_target = customer_target.sort_values("Target_Customer", ascending=False).reset_index(drop=True)

    if customer_target.empty:
        st.info("Tidak ada data Customer untuk filter yang dipilih.")
        return

    customer_capai = (customer_target["O/T"] >= 100).sum()
    customer_belum = len(customer_target) - customer_capai
    best_ot_row = customer_target.loc[customer_target["O/T"].idxmax()]
    best_at_row = customer_target.loc[customer_target["A/T"].idxmax()]

    title_ot = build_scope_title("CUSTOMER TERBAIK (O/T)", pilih_cabang, cabang_list, pilih_bulan, list_bulan_standar, pilih_tahun)
    title_at = build_scope_title("CUSTOMER TERBAIK (A/T)", pilih_cabang, cabang_list, pilih_bulan, list_bulan_standar, pilih_tahun)
    title_capai = build_scope_title("CUSTOMER CAPAI TARGET", pilih_cabang, cabang_list, pilih_bulan, list_bulan_standar, pilih_tahun)
    title_belum = build_scope_title("CUSTOMER BELUM CAPAI TARGET", pilih_cabang, cabang_list, pilih_bulan, list_bulan_standar, pilih_tahun)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("🥇", title_ot, best_ot_row["Nama_Customer"], f"{best_ot_row['O/T']:.1f}%", compact=True), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("🥇", title_at, best_at_row["Nama_Customer"], f"{best_at_row['A/T']:.1f}%", compact=True), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("✅", title_capai, f"{customer_capai}", f"dari {len(customer_target)} customer", compact=True), unsafe_allow_html=True)
    with c4:
        st.markdown(render_card("⚠️", title_belum, f"{customer_belum}", f"dari {len(customer_target)} customer", compact=True), unsafe_allow_html=True)

    # % Kontribusi Cabang/Nasional — dipakai cuma buat tooltip hover chart, sama pola kayak
    # tab_salesman_leaderboard.py, dihitung terpisah buat basis Order & basis Actual.
    cabang_totals_order = customer_target.groupby("Cabang")["Order"].sum()
    national_total_order = customer_target["Order"].sum()
    customer_target["Pct_Cabang_Order"] = (
        customer_target["Order"] / customer_target["Cabang"].map(cabang_totals_order).replace(0, pd.NA) * 100
    ).fillna(0.0)
    customer_target["Pct_Nasional_Order"] = (customer_target["Order"] / national_total_order * 100) if national_total_order > 0 else 0.0

    cabang_totals_actual = customer_target.groupby("Cabang")["Actual"].sum()
    national_total_actual = customer_target["Actual"].sum()
    customer_target["Pct_Cabang_Actual"] = (
        customer_target["Actual"] / customer_target["Cabang"].map(cabang_totals_actual).replace(0, pd.NA) * 100
    ).fillna(0.0)
    customer_target["Pct_Nasional_Actual"] = (customer_target["Actual"] / national_total_actual * 100) if national_total_actual > 0 else 0.0

    periode_tag = scope_label_periode(pilih_bulan, list_bulan_standar, pilih_tahun)
    chart_title = f"Top 10 Customer [{periode_tag}]" if periode_tag else "Top 10 Customer"
    st.markdown(f"#### {chart_title}")
    sort_basis = st.radio(
        "Urutkan Top 10 berdasarkan", ["Order (O/T)", "Supply (A/T)"], horizontal=True,
        key="target_customer_sort_basis",
    )
    sort_col = "O/T" if sort_basis == "Order (O/T)" else "A/T"
    top10 = customer_target.nlargest(10, sort_col)
    render_bidirectional_barh_chart(
        top10, "Nama_Customer", "O/T", "A/T", "O/T", "A/T",
        left_color="#f97316", right_color="#2563eb", value_fmt=lambda v: f"{v:.1f}%",
        key="chart_target_customer_top10", xaxis_title="% (O/T kiri • A/T kanan)",
        left_value_label="Pencapaian O/T", right_value_label="Pencapaian A/T",
        bar_text_size=10, label_size=11, axis_title_size=12, legend_size=11, gap_ratio=0.30,
        left_hover_extra=[
            ("Pct_Cabang_Order", "Kontribusi Cabang", lambda v: f"{v:.1f}%"),
            ("Pct_Nasional_Order", "Kontribusi Nasional", lambda v: f"{v:.1f}%"),
        ],
        right_hover_extra=[
            ("Pct_Cabang_Actual", "Kontribusi Cabang", lambda v: f"{v:.1f}%"),
            ("Pct_Nasional_Actual", "Kontribusi Nasional", lambda v: f"{v:.1f}%"),
        ],
    )

    st.markdown("#### Ranking Lengkap Target Customer")
    display = customer_target[["Nama_Customer", "Cabang", "Target_Customer", "Order", "Actual", "O/T", "A/T"]].copy()
    display = display.rename(columns={"Nama_Customer": "Customer", "Target_Customer": "Target"})

    render_styled_table(
        display, _highlight_ot, pct_cols=["O/T", "A/T"],
        fmt_dict={"Target": FMT_RP, "Order": FMT_RP, "Actual": FMT_RP, "O/T": "{:.2f}%", "A/T": "{:.2f}%"},
        height=min(auto_table_height(len(display)), 600),
    )
