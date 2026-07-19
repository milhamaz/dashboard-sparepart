# ============================================================
# 🔧 TAB: T-OPT
# ============================================================
import streamlit as st
from utils.components import (
    validate_lookup, render_tile_filter, merge_lookup_triplet, aggregate_monthly,
    render_trend_cards, render_trend_chart_and_table, render_value_breakdown,
)
from utils.styles import fmt_rp_full


def render(df_order_final, df_supply_final, df_topt_lookup, pilih_tahun, pilih_bulan, fmt_rp, highlight_pct):
    if not validate_lookup(df_topt_lookup, ["Partnumber", "Partname", "Step", "Kategori"], "PnoTOPT.xlsx"):
        return

    topt_cols = ["Partnumber", "Partname", "Step", "Kategori"]
    df_ord_base, df_sup_base, df_ly_base = merge_lookup_triplet(df_order_final, df_supply_final, df_topt_lookup, topt_cols, pilih_tahun)

    col_f_topt1, col_f_topt2 = st.columns([1, 3])

    with col_f_topt1:
        all_step = sorted(set(
            (df_ord_base["Step"].dropna().unique().tolist() if len(df_ord_base) else []) +
            (df_sup_base["Step"].dropna().unique().tolist() if len(df_sup_base) else []) +
            (df_ly_base["Step"].dropna().unique().tolist() if len(df_ly_base) else [])
        ))
        pilih_step = render_tile_filter("🪜 Filter Step", all_step, key="topt_step_filter")

    with col_f_topt2:
        all_kategori = sorted(set(
            (df_ord_base["Kategori"].dropna().unique().tolist() if len(df_ord_base) else []) +
            (df_sup_base["Kategori"].dropna().unique().tolist() if len(df_sup_base) else []) +
            (df_ly_base["Kategori"].dropna().unique().tolist() if len(df_ly_base) else [])
        ))
        pilih_kategori = render_tile_filter("🗂️ Filter Kategori", all_kategori, key="topt_kategori_filter")

    def filter_topt_data(df):
        if df.empty: return df
        return df[df["Step"].isin(pilih_step) & df["Kategori"].isin(pilih_kategori)]

    df_ord_topt = filter_topt_data(df_ord_base)
    df_sup_topt = filter_topt_data(df_sup_base)
    df_ly_topt = filter_topt_data(df_ly_base)

    m_ord = aggregate_monthly(df_ord_topt, "Order")
    m_sup = aggregate_monthly(df_sup_topt, "Actual")
    m_ly = aggregate_monthly(df_ly_topt, "Actual", out_col="Last_Year")

    render_trend_cards(
        m_ly, m_ord, m_sup, pilih_tahun,
        card_titles={"order": "Order", "supply": "Actual", "ly": "Last Year", "growth": "Growth"},
        fmt_card=fmt_rp,
    )

    format_topt_rp_hover = lambda v: f"Rp{v:,.0f}".replace(",", ".") if v else "Rp0"
    format_topt_rp_text = lambda v: (
        f"Rp {v / 1_000_000_000:,.2f} M" if v >= 1_000_000_000 else (
            f"Rp {v / 1_000_000:,.0f} JT" if v >= 1_000_000 else (
                f"Rp {v / 1_000:,.0f} RB" if v >= 1_000 else "Rp 0"
            )
        )
    )

    render_trend_chart_and_table(
        m_ly, m_ord, m_sup, pilih_tahun, pilih_bulan,
        hover_fmt=format_topt_rp_hover, text_fmt=format_topt_rp_text, yaxis_title="Revenue (Rp)",
        detail_labels={
            "expander_title": "Detail Data T-OPT (Rupiah)",
            "ly": "Last Year", "order": "Order", "supply": "Actual",
            "cell_fmt": fmt_rp_full,
            "no_data": "Tidak ada data T-OPT untuk filter yang dipilih.",
        },
        highlight_pct=highlight_pct,
    )

    st.markdown("#### Breakdown T-OPT per Cabang/Customer")
    render_value_breakdown(df_ord_topt, "Order", key_prefix="topt", fmt_cell=fmt_rp_full)
