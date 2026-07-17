# ============================================================
# 🔋 TAB: TGB (Quantity Unit Base)
# ============================================================
import streamlit as st
from utils.components import (
    validate_lookup, render_tile_filter, merge_lookup_triplet, aggregate_monthly,
    render_trend_cards, render_trend_chart_and_table, render_value_breakdown,
)


def render(df_order_final, df_supply_final, df_TGB_lookup, pilih_tahun, pilih_bulan, highlight_pct):
    TGB_cols = ["Partnumber", "Kategori"]
    if not validate_lookup(df_TGB_lookup, TGB_cols, "PnoTGB.xlsx"):
        return

    df_ord_base, df_sup_base, df_ly_base = merge_lookup_triplet(df_order_final, df_supply_final, df_TGB_lookup, TGB_cols, pilih_tahun)

    if not df_ord_base.empty:
        df_ord_base["Order"] = df_ord_base["Qty"]
    if not df_sup_base.empty:
        df_sup_base["Actual"] = df_sup_base["Qty"]
    if not df_ly_base.empty:
        df_ly_base["Actual"] = df_ly_base["Qty"]

    list_TGB_categories = sorted(set(
        (df_ord_base["Kategori"].dropna().unique().tolist() if len(df_ord_base) else []) +
        (df_sup_base["Kategori"].dropna().unique().tolist() if len(df_sup_base) else []) +
        (df_ly_base["Kategori"].dropna().unique().tolist() if len(df_ly_base) else [])
    ))
    pilih_TGB_category = render_tile_filter("🔋 Filter Kategori TGB", list_TGB_categories, key="TGB_category_filter")

    def filter_TGB_data(df):
        if df.empty: return df
        return df[df["Kategori"].isin(pilih_TGB_category)]

    df_ord_TGB = filter_TGB_data(df_ord_base)
    df_sup_TGB = filter_TGB_data(df_sup_base)
    df_ly_TGB = filter_TGB_data(df_ly_base)

    def fmt_pcs(val):
        return f"{val:,.0f}".replace(",", ".") + " Pcs"

    m_ord = aggregate_monthly(df_ord_TGB, "Order")
    m_sup = aggregate_monthly(df_sup_TGB, "Actual")
    m_ly = aggregate_monthly(df_ly_TGB, "Actual", out_col="Last_Year")

    render_trend_cards(
        m_ly, m_ord, m_sup, pilih_tahun,
        card_titles={"order": "Total Order", "supply": "Total Actual Supply", "ly": "Last Year Qty", "growth": "Growth"},
        fmt_card=fmt_pcs,
    )

    pcs_text = lambda v: f"{v:,.0f}".replace(",", ".") if v else ""
    pcs_hover = lambda v: f"{v:,.0f}".replace(",", ".") + " Pcs"

    render_trend_chart_and_table(
        m_ly, m_ord, m_sup, pilih_tahun, pilih_bulan,
        hover_fmt=pcs_hover, text_fmt=pcs_text, yaxis_title="Kuantitas (Pcs)",
        detail_labels={
            "expander_title": "Detail Data TGB (Pcs)",
            "ly": "Last Year (Pcs)", "order": "Order (Pcs)", "supply": "Supply (Pcs)",
            "cell_fmt": lambda x: f"{x:,.0f}".replace(",", "."),
            "no_data": "Tidak ada data TGB untuk filter yang dipilih.",
        },
        highlight_pct=highlight_pct,
        text_size=13,
    )

    st.markdown("#### Breakdown TGB per Cabang/Customer")
    render_value_breakdown(df_ord_TGB, "Order", key_prefix="tgb", fmt_cell=lambda x: f"{x:,.0f}".replace(",", "."))
