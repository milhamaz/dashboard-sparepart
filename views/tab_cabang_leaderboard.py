# ============================================================
# 🏆 TAB: CABANG LEADERBOARD
# ============================================================
import streamlit as st
import pandas as pd

from utils.components import (
    render_card, render_growth_card, render_bidirectional_barh_chart, render_styled_table,
    auto_table_height, hitung_growth,
)
from utils.styles import fmt_rp_full as FMT_RP, highlight_growth_pct_fill as _highlight_growth_pct


def render(df_order_final, df_supply_final, pilih_tahun, fmt_rp):
    """Ranking Cabang berdasar Actual (realized) tahun berjalan, dibanding Last Year — layout
    persis tab_salesman_leaderboard.py, cuma grouping-nya per Cabang. Beda dari Salesman:
    Cabang gak punya "induk" grouping di atasnya selain Nasional, jadi cuma ada %Kontribusi
    Nasional di hover chart (gak ada versi "vs Cabang sendiri" kayak Salesman Leaderboard).
    """
    if df_supply_final is None or df_supply_final.empty:
        st.info("Tidak ada data Supply untuk filter yang dipilih.")
        return

    df_sup = df_supply_final.copy()

    sup_this = df_sup[df_sup["Tahun"] == pilih_tahun].groupby("Cabang")["Actual"].sum()
    sup_ly = df_sup[df_sup["Tahun"] == pilih_tahun - 1].groupby("Cabang")["Actual"].sum()

    leaderboard = sup_this.rename("Actual").to_frame().join(sup_ly.rename("Last_Year"), how="outer").fillna(0)
    leaderboard.index.name = "Cabang"
    leaderboard = leaderboard.reset_index()
    leaderboard = leaderboard[leaderboard["Cabang"].astype(str).str.strip() != ""]

    if not df_order_final.empty:
        df_ord = df_order_final.copy()
        order_sum = df_ord.groupby("Cabang")["Order"].sum()
        active_customers = df_ord.groupby("Cabang")["Customer_No"].nunique()
        leaderboard = leaderboard.merge(order_sum.rename("Order"), on="Cabang", how="left")
        leaderboard = leaderboard.merge(active_customers.rename("Active_Customers"), on="Cabang", how="left")
    else:
        df_ord = pd.DataFrame(columns=["Cabang", "Order"])
        leaderboard["Order"] = 0.0
        leaderboard["Active_Customers"] = 0
    leaderboard["Order"] = leaderboard["Order"].fillna(0)
    leaderboard["Active_Customers"] = leaderboard["Active_Customers"].fillna(0).astype(int)

    leaderboard["Growth (%)"] = leaderboard.apply(lambda r: hitung_growth(r["Actual"], r["Last_Year"]), axis=1)
    leaderboard = leaderboard.sort_values("Actual", ascending=False).reset_index(drop=True)

    if leaderboard.empty:
        st.info("Tidak ada data Cabang untuk filter yang dipilih.")
        return

    # %Kontribusi Nasional — dipakai cuma buat tooltip hover chart, bukan tabel.
    total_actual = leaderboard["Actual"].sum()
    total_order = leaderboard["Order"].sum()
    leaderboard["Pct_Nasional"] = (leaderboard["Actual"] / total_actual * 100) if total_actual > 0 else 0.0
    leaderboard["Pct_Nasional_Order"] = (leaderboard["Order"] / total_order * 100) if total_order > 0 else 0.0

    total_ly = leaderboard["Last_Year"].sum()
    national_growth = hitung_growth(total_actual, total_ly)
    top_row = leaderboard.iloc[0]
    active_cabang = (leaderboard["Actual"] > 0).sum()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("🥇", "Top Cabang", top_row["Cabang"], fmt_rp(top_row["Actual"])), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("🏢", "Cabang Aktif", f"{active_cabang}", f"dari {len(leaderboard)} terdaftar"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("", "Total Actual", fmt_rp(total_actual), f"Avg: {fmt_rp(total_actual / active_cabang) if active_cabang else fmt_rp(0)}/cabang"), unsafe_allow_html=True)
    with c4:
        st.markdown(render_growth_card("", "YoY Growth Nasional", national_growth, f"Actual vs {pilih_tahun - 1}"), unsafe_allow_html=True)

    st.markdown("#### Top 10 Cabang — Order vs Actual")
    sort_basis = st.radio(
        "Urutkan Top 10 berdasarkan", ["Order", "Actual"], index=1, horizontal=True,
        key="cabang_leaderboard_sort_basis",
    )
    top10 = leaderboard.nlargest(10, sort_basis)
    render_bidirectional_barh_chart(
        top10, "Cabang", "Order", "Actual", "Order", "Actual",
        left_color="#f97316", right_color="#2563eb", value_fmt=fmt_rp,
        key="chart_cabang_leaderboard_order_vs_actual", xaxis_title="Rp (Order kiri • Actual kanan)",
        left_hover_extra=[("Pct_Nasional_Order", "% Kontribusi Nasional", lambda v: f"{v:.1f}%")],
        right_hover_extra=[("Pct_Nasional", "% Kontribusi Nasional", lambda v: f"{v:.1f}%")],
    )

    st.markdown("#### Ranking Lengkap Cabang")
    display = leaderboard[["Cabang", "Actual", "Last_Year", "Growth (%)", "Order", "Active_Customers"]].copy()
    display.insert(0, "Rank", range(1, len(display) + 1))
    display = display.rename(columns={"Last_Year": "Last Year", "Active_Customers": "Customer Aktif"})

    render_styled_table(
        display, _highlight_growth_pct, pct_cols=["Growth (%)"],
        fmt_dict={
            "Actual": FMT_RP, "Last Year": FMT_RP, "Order": FMT_RP,
            "Growth (%)": "{:.2f}%", "Customer Aktif": "{:,.0f}",
        },
        height=min(auto_table_height(len(display)), 600),
    )
