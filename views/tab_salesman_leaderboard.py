# ============================================================
# 🏆 TAB: SALESMAN LEADERBOARD
# ============================================================
import streamlit as st
import pandas as pd

from utils.components import (
    render_card, render_growth_card, render_bidirectional_barh_chart, render_styled_table,
    auto_table_height, hitung_growth,
)
from utils.styles import fmt_rp_full as FMT_RP, highlight_growth_pct_fill as _highlight_growth_pct


def render(df_order_final, df_supply_final, pilih_tahun, fmt_rp):
    """Ranking Salesman berdasar Actual (realized) tahun berjalan, dibanding Last Year.
    Order (dari df_order_final, cuma tahun berjalan) dipakai buat kolom pelengkap, bukan
    dasar ranking — Actual dipilih karena itu revenue yang benar-benar ter-supply/invoice,
    konsisten dengan cara Performance/COGS tab bandingin YoY.
    """
    if df_supply_final is None or df_supply_final.empty:
        st.info("Tidak ada data Supply untuk filter yang dipilih.")
        return

    df_sup = df_supply_final.copy()
    df_sup["Salesman_Name"] = df_sup["Salesman_Name"].astype(str).str.strip().str.upper()

    sup_this = df_sup[df_sup["Tahun"] == pilih_tahun].groupby("Salesman_Name")["Actual"].sum()
    sup_ly = df_sup[df_sup["Tahun"] == pilih_tahun - 1].groupby("Salesman_Name")["Actual"].sum()

    leaderboard = sup_this.rename("Actual").to_frame().join(sup_ly.rename("Last_Year"), how="outer").fillna(0)
    leaderboard.index.name = "Salesman_Name"
    leaderboard = leaderboard.reset_index()
    leaderboard = leaderboard[leaderboard["Salesman_Name"].str.strip() != ""]
    leaderboard = leaderboard[leaderboard["Salesman_Name"] != "NAN"]

    if not df_order_final.empty:
        df_ord = df_order_final.copy()
        df_ord["Salesman_Name"] = df_ord["Salesman_Name"].astype(str).str.strip().str.upper()
        order_sum = df_ord.groupby("Salesman_Name")["Order"].sum()
        active_customers = df_ord.groupby("Salesman_Name")["Customer_No"].nunique()
        leaderboard = leaderboard.merge(order_sum.rename("Order"), on="Salesman_Name", how="left")
        leaderboard = leaderboard.merge(active_customers.rename("Active_Customers"), on="Salesman_Name", how="left")
    else:
        df_ord = pd.DataFrame(columns=["Salesman_Name", "Order", "Cabang"])
        leaderboard["Order"] = 0.0
        leaderboard["Active_Customers"] = 0
    leaderboard["Order"] = leaderboard["Order"].fillna(0)
    leaderboard["Active_Customers"] = leaderboard["Active_Customers"].fillna(0).astype(int)

    leaderboard["Growth (%)"] = leaderboard.apply(lambda r: hitung_growth(r["Actual"], r["Last_Year"]), axis=1)
    leaderboard = leaderboard.sort_values("Actual", ascending=False).reset_index(drop=True)

    if leaderboard.empty:
        st.info("Tidak ada data Salesman untuk filter yang dipilih.")
        return

    # ── %Kontribusi Nasional & Cabang — dipakai cuma buat tooltip hover chart, bukan
    # tabel. Cabang tiap Salesman diambil dari Cabang dengan Actual terbesar tahun berjalan
    # (beberapa nama Salesman ada yang tercatat di >1 Cabang, kemungkinan tabrakan nama).
    df_sup_year = df_sup[df_sup["Tahun"] == pilih_tahun]
    salesman_cabang = (
        df_sup_year.groupby(["Salesman_Name", "Cabang"])["Actual"].sum()
        .reset_index().sort_values("Actual", ascending=False)
        .drop_duplicates("Salesman_Name").set_index("Salesman_Name")["Cabang"]
    )
    cabang_totals = df_sup_year.groupby("Cabang")["Actual"].sum()
    national_total = df_sup_year["Actual"].sum()

    leaderboard["Cabang"] = leaderboard["Salesman_Name"].map(salesman_cabang)
    leaderboard["Cabang_Total"] = leaderboard["Cabang"].map(cabang_totals).fillna(0)
    leaderboard["Pct_Nasional"] = (leaderboard["Actual"] / national_total * 100) if national_total > 0 else 0.0
    leaderboard["Pct_Cabang"] = (leaderboard["Actual"] / leaderboard["Cabang_Total"].replace(0, pd.NA) * 100).fillna(0.0)

    # Sama seperti Pct_Nasional/Pct_Cabang di atas tapi buat Order — Cabang tetap pakai
    # pemetaan salesman_cabang dari Actual (single source of truth), cuma total pembaginya
    # yang diganti total Order supaya %kontribusi Order konsisten sama basis Order-nya sendiri.
    cabang_totals_order = df_ord.groupby("Cabang")["Order"].sum() if not df_ord.empty else pd.Series(dtype=float)
    national_total_order = df_ord["Order"].sum() if not df_ord.empty else 0.0

    leaderboard["Cabang_Total_Order"] = leaderboard["Cabang"].map(cabang_totals_order).fillna(0)
    leaderboard["Pct_Nasional_Order"] = (leaderboard["Order"] / national_total_order * 100) if national_total_order > 0 else 0.0
    leaderboard["Pct_Cabang_Order"] = (leaderboard["Order"] / leaderboard["Cabang_Total_Order"].replace(0, pd.NA) * 100).fillna(0.0)

    total_actual = leaderboard["Actual"].sum()
    total_ly = leaderboard["Last_Year"].sum()
    national_growth = hitung_growth(total_actual, total_ly)
    top_row = leaderboard.iloc[0]
    active_salesman = (leaderboard["Actual"] > 0).sum()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("🥇", "Top Salesman", top_row["Salesman_Name"], fmt_rp(top_row["Actual"])), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("👤", "Salesman Aktif", f"{active_salesman}", f"dari {len(leaderboard)} terdaftar"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("", "Total Actual", fmt_rp(total_actual), f"Avg: {fmt_rp(total_actual / active_salesman) if active_salesman else fmt_rp(0)}/salesman"), unsafe_allow_html=True)
    with c4:
        st.markdown(render_growth_card("", "YoY Growth Nasional", national_growth, f"Actual vs {pilih_tahun - 1}"), unsafe_allow_html=True)

    st.markdown("#### Top 10 Salesman — Order vs Actual")
    sort_basis = st.radio(
        "Urutkan Top 10 berdasarkan", ["Order", "Actual"], index=1, horizontal=True,
        key="salesman_leaderboard_sort_basis",
    )
    top10 = leaderboard.nlargest(10, sort_basis)
    render_bidirectional_barh_chart(
        top10, "Salesman_Name", "Order", "Actual", "Order", "Actual",
        left_color="#f97316", right_color="#2563eb", value_fmt=fmt_rp,
        key="chart_salesman_order_vs_actual", xaxis_title="Rp (Order kiri • Actual kanan)",
        left_hover_extra=[
            ("Pct_Nasional_Order", "% Kontribusi Nasional", lambda v: f"{v:.1f}%"),
            ("Pct_Cabang_Order", "% Kontribusi Cabang", lambda v: f"{v:.1f}%"),
        ],
        right_hover_extra=[
            ("Pct_Nasional", "% Kontribusi Nasional", lambda v: f"{v:.1f}%"),
            ("Pct_Cabang", "% Kontribusi Cabang", lambda v: f"{v:.1f}%"),
        ],
    )

    st.markdown("#### Ranking Lengkap Salesman")
    display = leaderboard[["Salesman_Name", "Actual", "Last_Year", "Growth (%)", "Order", "Active_Customers"]].copy()
    display.insert(0, "Rank", range(1, len(display) + 1))
    display = display.rename(columns={"Salesman_Name": "Salesman", "Last_Year": "Last Year", "Active_Customers": "Customer Aktif"})

    render_styled_table(
        display, _highlight_growth_pct, pct_cols=["Growth (%)"],
        fmt_dict={
            "Actual": FMT_RP, "Last Year": FMT_RP, "Order": FMT_RP,
            "Growth (%)": "{:.2f}%", "Customer Aktif": "{:,.0f}",
        },
        height=min(auto_table_height(len(display)), 600),
    )
