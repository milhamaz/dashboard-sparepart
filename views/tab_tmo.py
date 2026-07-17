# ============================================================
# 🛢️ TAB: TMO
# ============================================================
import streamlit as st
from utils.components import (
    validate_lookup, render_tile_filter, merge_lookup_triplet, aggregate_monthly,
    render_trend_cards, render_trend_chart_and_table, render_value_breakdown,
)


def render(df_order_final, df_supply_final, df_tmo_lookup, pilih_tahun, pilih_bulan, fmt_liter, highlight_pct):
    if not validate_lookup(df_tmo_lookup, ["Partnumber", "Partname", "Liter", "Jenis"], "PnoTMO.xlsx"):
        return

    tmo_cols = ["Partnumber", "Partname", "Liter", "Jenis"]
    df_ord_base, df_sup_base, df_ly_base = merge_lookup_triplet(df_order_final, df_supply_final, df_tmo_lookup, tmo_cols, pilih_tahun)
    for df in (df_ord_base, df_sup_base, df_ly_base):
        if not df.empty:
            df["Volume"] = df["Qty"] * df["Liter"]

    col_f_tmo1, col_f_tmo2 = st.columns(2)
    with col_f_tmo1:
        all_jenis = sorted(set(
            (df_ord_base["Jenis"].dropna().unique().tolist() if len(df_ord_base) else []) +
            (df_sup_base["Jenis"].dropna().unique().tolist() if len(df_sup_base) else []) +
            (df_ly_base["Jenis"].dropna().unique().tolist() if len(df_ly_base) else [])
        ))
        pilih_jenis_tmo = render_tile_filter("🏷️ Filter Jenis TMO", all_jenis, key="tmo_jenis_filter")

    with col_f_tmo2:
        kamus_so_type = {"C": "SO Campaign (C)", "3": "SO Non Campaign (3)"}
        all_so_types = sorted(set(
            (df_ord_base["SO_Type"].dropna().unique().tolist() if len(df_ord_base) else []) +
            (df_sup_base["SO_Type"].dropna().unique().tolist() if len(df_sup_base) else [])
        ))
        pilih_so_type_raw = render_tile_filter("🎁 Filter SO Type (Diskon)", all_so_types, key="tmo_so_type_filter", format_func=lambda x: kamus_so_type.get(x, x))

    def filter_tmo_data(df):
        if df.empty: return df
        mask = df["Jenis"].isin(pilih_jenis_tmo)
        if "SO_Type" in df.columns:
            mask = mask & df["SO_Type"].isin(pilih_so_type_raw)
        return df[mask]

    df_ord_tmo = filter_tmo_data(df_ord_base)
    df_sup_tmo = filter_tmo_data(df_sup_base)
    df_ly_tmo = filter_tmo_data(df_ly_base)

    m_ord = aggregate_monthly(df_ord_tmo, "Volume", out_col="Order")
    m_sup = aggregate_monthly(df_sup_tmo, "Volume", out_col="Actual")
    m_ly = aggregate_monthly(df_ly_tmo, "Volume", out_col="Last_Year")

    render_trend_cards(
        m_ly, m_ord, m_sup, pilih_tahun,
        card_titles={"order": "Vol. Order", "supply": "Vol. Supply", "ly": "Last Year", "growth": "YoY Volume"},
        fmt_card=fmt_liter,
    )

    vol_so_campaign = df_ord_tmo[df_ord_tmo["SO_Type"] == "C"]["Volume"].sum() if len(df_ord_tmo) else 0
    vol_so_non_campaign = df_ord_tmo[df_ord_tmo["SO_Type"] == "3"]["Volume"].sum() if len(df_ord_tmo) else 0

    c_sub1, c_sub2 = st.columns(2)
    with c_sub1:
        st.markdown(f'<div class="custom-card" style="border-left: 5px solid #2563eb;"><div class="card-title">Vol. SO Campaign (Tipe C)</div><div class="card-value">{fmt_liter(vol_so_campaign)}</div><div class="card-sub">Total order dengan program diskon</div></div>', unsafe_allow_html=True)
    with c_sub2:
        st.markdown(f'<div class="custom-card" style="border-left: 5px solid #f59e0b;"><div class="card-title">Vol. SO Non Campaign (Tipe 3)</div><div class="card-value">{fmt_liter(vol_so_non_campaign)}</div><div class="card-sub">Total order regular / normal price</div></div>', unsafe_allow_html=True)

    format_liter_hover = lambda v: f"{v:,.0f}".replace(",", ".") + " L" if v else "0 L"
    format_liter_text = lambda v: f"{v:,.0f}".replace(",", ".")

    render_trend_chart_and_table(
        m_ly, m_ord, m_sup, pilih_tahun, pilih_bulan,
        hover_fmt=format_liter_hover, text_fmt=format_liter_text, yaxis_title="Volume (Liter)",
        detail_labels={
            "expander_title": "Detail Volume TMO (Liter)",
            "ly": "Last Year (L)", "order": "Order (L)", "supply": "Supply (L)",
            "cell_fmt": lambda x: f"{x:,.0f}".replace(",", "."),
            "no_data": "Tidak ada data TMO untuk filter yang dipilih.",
        },
        highlight_pct=highlight_pct,
    )

    st.markdown("#### Breakdown Volume TMO per Cabang/Customer")
    render_value_breakdown(df_ord_tmo, "Volume", key_prefix="tmo", fmt_cell=lambda x: f"{x:,.0f}".replace(",", "."))
