# ============================================================
# 🏷️ TAB: ITEM D (Program Diskon Bulanan)
# ============================================================
import streamlit as st
import pandas as pd
from utils.components import (
    compute_item_d_burn, hitung_aly, render_card, render_styled_table, append_total_row,
    trim_future_months, render_tile_filter, render_burn_rate_heatmap,
)
from utils.styles import highlight_burn_rate_pct, fmt_rp_full


def render(df_order_final, df_supply_final, df_dprog_lookup, pilih_tahun, pilih_bulan, fmt_rp):
    if df_dprog_lookup is None or df_dprog_lookup.empty or "Partnumber" not in df_dprog_lookup.columns:
        st.warning("Data master PnoDProg.xlsx belum siap atau kolom 'Partnumber' tidak ditemukan.")
        return

    if "Partnumber" not in df_order_final.columns or "SO_Date" not in df_order_final.columns:
        st.warning("Kolom Partnumber atau SO_Date tidak ditemukan di data order.")
        return

    df_ord_dprog = compute_item_d_burn(df_order_final, df_dprog_lookup)
    if df_ord_dprog.empty:
        st.info("Tidak ada transaksi yang jatuh dalam periode program Item D.")
        return

    # ── Filter periode (tile, default = semua periode) ──
    all_periods = df_ord_dprog.groupby(["StartDate", "EndDate"]).size().reset_index(name="count")
    all_periods["Label"] = all_periods.apply(lambda r: f"{r['StartDate'].strftime('%d %b')} – {r['EndDate'].strftime('%d %b %Y')}", axis=1)
    period_labels = all_periods["Label"].tolist()

    pilih_periode = render_tile_filter("📅 Filter Periode Item D", period_labels, key="dprog_period_filter")

    selected_periods = all_periods[all_periods["Label"].isin(pilih_periode)]
    mask_period = pd.Series(False, index=df_ord_dprog.index)
    for _, row in selected_periods.iterrows():
        mask_period = mask_period | ((df_ord_dprog["StartDate"] == row["StartDate"]) & (df_ord_dprog["EndDate"] == row["EndDate"]))
    df_ord_dprog = df_ord_dprog[mask_period]

    # ── Metrics ──
    total_revenue = df_ord_dprog["Revenue"].sum()
    total_burn = df_ord_dprog["Burn"].sum()
    total_transactions = len(df_ord_dprog)
    discounted_transactions = df_ord_dprog["Is_Discounted"].sum()
    pct_discounted = (discounted_transactions / total_transactions * 100) if total_transactions > 0 else 0
    burn_rate = (total_burn / total_revenue * 100) if total_revenue > 0 else 0

    # Cards
    ct1, ct2, ct3, ct4, ct5 = st.columns(5)
    with ct1: st.markdown(render_card("", "Revenue Item D", fmt_rp(total_revenue), f"{total_transactions:,.0f} transaksi"), unsafe_allow_html=True)
    with ct2: st.markdown(render_card("", "Total Burn (Diskon)", fmt_rp(total_burn), f"{discounted_transactions:,.0f} rows pakai diskon"), unsafe_allow_html=True)
    with ct3: st.markdown(render_card("", "Burn Rate", f"{burn_rate:.2f}%", "Burn / Revenue Item D"), unsafe_allow_html=True)
    with ct4: st.markdown(render_card("", "Hit Rate Diskon", f"{pct_discounted:.1f}%", "Transaksi yang pakai Scp_Disc"), unsafe_allow_html=True)
    with ct5:
        avg_disc = df_ord_dprog[df_ord_dprog["Is_Discounted"]]["Scp_Disc"].mean() if discounted_transactions > 0 else 0
        st.markdown(render_card("", "Avg Scp Disc", f"{avg_disc:.1f}%", "Rata-rata diskon yang diminta"), unsafe_allow_html=True)

    # ── Tabel Detail Item D per Bulan (visual utama) ──
    st.markdown("#### Detail Item D per Bulan")

    m_rev = df_ord_dprog.groupby(["Bulan_Num", "Bulan"])["Revenue"].sum().reset_index()
    m_burn = df_ord_dprog.groupby(["Bulan_Num", "Bulan"])["Burn"].sum().reset_index()

    if not m_rev.empty or not m_burn.empty:
        detail = m_rev.merge(m_burn, on=["Bulan_Num", "Bulan"], how="outer").fillna(0)
        detail["Bulan_Num"] = detail["Bulan_Num"].astype(int)
        detail = detail[detail["Bulan"].isin(pilih_bulan)].sort_values("Bulan_Num")
        detail = trim_future_months(detail, data_cols=["Revenue", "Burn"])
        detail["Burn Rate (%)"] = (detail["Burn"] / detail["Revenue"] * 100).fillna(0).replace([float('inf'), -float('inf')], 0)

        display = detail.drop(columns=["Bulan_Num"]).rename(columns={"Revenue": "Revenue (Rp)", "Burn": "Burn (Rp)"})

        rev_sum = display["Revenue (Rp)"].sum()
        burn_sum = display["Burn (Rp)"].sum()
        display = append_total_row(display, {
            "Bulan": "TOTAL",
            "Revenue (Rp)": rev_sum,
            "Burn (Rp)": burn_sum,
            "Burn Rate (%)": hitung_aly(burn_sum, rev_sum),
        })

        render_styled_table(
            display, highlight_burn_rate_pct, pct_cols=["Burn Rate (%)"],
            fmt_dict={
                "Revenue (Rp)": fmt_rp_full,
                "Burn (Rp)": fmt_rp_full,
                "Burn Rate (%)": "{:.2f}%",
            },
            has_total_row=True,
        )
    else:
        st.info("Tidak ada data Item D untuk filter yang dipilih.")

    # ══════════════════════════════════════════════════════════
    # HEATMAP: Top 7 Cabang (Revenue Item D tertinggi) — Burn Rate (%)
    # ══════════════════════════════════════════════════════════
    st.markdown("#### Top 7 Cabang — Burn Rate Item D (%)")
    render_burn_rate_heatmap(df_ord_dprog, revenue_col="Revenue", burn_col="Burn", key="heatmap_dprog")
