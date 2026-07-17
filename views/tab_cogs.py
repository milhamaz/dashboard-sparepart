# ============================================================
# 🧮 TAB: COGS & PROFIT (Estimasi)
# ============================================================
import streamlit as st

from utils.components import (
    append_total_row, cleanup_selection, render_card, render_styled_table, render_value_breakdown,
)

FMT_RP = lambda x: f"Rp {x:,.0f}".replace(",", ".")


def _highlight_profit_pct(val):
    """Hijau kalau margin >=0%, merah kalau minus — beda dari highlight_pct standar
    (utils/styles.py) yang threshold-nya di 100% buat rasio A/LY, bukan cocok buat margin."""
    color = "#10b981" if val >= 0 else "#ef4444"
    return f"color: {color}; font-weight: bold;"


def render(df_supply):
    if df_supply is None or df_supply.empty:
        st.warning("Data Supply belum siap.")
        return
    if "Profit" not in df_supply.columns:
        st.warning("Kolom Profit belum tersedia — cek konfigurasi COGS di utils/data_loader.py.")
        return

    st.caption(
        "Estimasi COGS & Profit — data pembelian TASTI ke Toyota (Modal asli) tidak bisa ditarik "
        "bulk, jadi di-estimasi: **Net Sales** pakai Discount asli (TASTI → Customer), **COGS** pakai "
        "simulasi diskon Toyota → TASTI (TMO = fixed 44%, selain itu = Discount asli + margin acak "
        "sesuai Cabang/Kelas Cabang). **Profit = Net Sales − COGS**, bisa minus (terutama TMO kalau "
        "diskon customer melebihi 44%). **% Profit** = Profit/Gross Sales, **% Profit Margin** = Profit/Net Sales."
    )

    tahun_list = sorted(df_supply["Tahun"].dropna().unique().tolist())
    if not tahun_list:
        st.info("Belum ada data Supply.")
        return
    tahun_terbaru = tahun_list[-1]

    col_tahun, col_area = st.columns(2)
    with col_tahun:
        tahun_options = [str(t) for t in tahun_list]
        pilih_tahun_raw = st.pills(
            "Pilih Tahun", tahun_options, selection_mode="single",
            default=str(tahun_terbaru), key="cogs_tahun",
        )
    pilih_tahun = int(pilih_tahun_raw) if pilih_tahun_raw else tahun_terbaru

    area_options = sorted(df_supply["Kode_Area"].dropna().unique().tolist())
    area_key = "cogs_area"
    cleanup_selection(area_key, area_options)
    with col_area:
        pilih_area = st.pills("Filter Area (slicer)", area_options, selection_mode="multi", key=area_key) or []

    df_scope = df_supply[df_supply["Tahun"] == pilih_tahun]
    if pilih_area:
        df_scope = df_scope[df_scope["Kode_Area"].isin(pilih_area)]

    if df_scope.empty:
        st.info(f"Tidak ada data untuk tahun {pilih_tahun}.")
        return

    # ── Card Metrics Nasional ──
    total_gross = df_scope["Actual"].sum()
    total_net = df_scope["Net_Sales"].sum()
    total_cogs = df_scope["COGS"].sum()
    total_profit = df_scope["Profit"].sum()
    pct_profit = (total_profit / total_gross * 100) if total_gross else 0
    pct_profit_margin = (total_profit / total_net * 100) if total_net else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("", "Net Sales", FMT_RP(total_net), f"Gross Sales: {FMT_RP(total_gross)}"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("", "COGS (Estimasi)", FMT_RP(total_cogs), "Simulasi diskon Toyota → TASTI"), unsafe_allow_html=True)
    with c3:
        profit_color = "#10b981" if total_profit >= 0 else "#ef4444"
        st.markdown(render_card("", "Profit", f'<span style="color:{profit_color}">{FMT_RP(total_profit)}</span>', f"Tahun {pilih_tahun}"), unsafe_allow_html=True)
    with c4:
        margin_color = "#10b981" if pct_profit_margin >= 0 else "#ef4444"
        st.markdown(render_card("", "% Profit Margin", f'<span style="color:{margin_color}">{pct_profit_margin:.2f}%</span>', f"% Profit (vs Gross): {pct_profit:.2f}%"), unsafe_allow_html=True)

    # ── Ringkasan P&L per Cabang ──
    st.markdown("#### Ringkasan Profit per Cabang")
    summary = df_scope.groupby("Cabang").agg(
        Gross_Sales=("Actual", "sum"), Net_Sales=("Net_Sales", "sum"),
        COGS=("COGS", "sum"), Profit=("Profit", "sum"),
    ).reset_index()
    summary["Pct_Gross_Profit"] = (summary["Profit"] / summary["Gross_Sales"] * 100).replace([float("inf"), -float("inf")], 0).fillna(0)
    summary["Pct_GPM"] = (summary["Profit"] / summary["Net_Sales"] * 100).replace([float("inf"), -float("inf")], 0).fillna(0)
    summary = summary.sort_values("Profit", ascending=False)

    display = summary.rename(columns={
        "Gross_Sales": "Gross Sales", "Net_Sales": "Net Sales",
        "Pct_Gross_Profit": "% Gross Profit", "Pct_GPM": "% GPM",
    })
    display = append_total_row(display, {
        "Cabang": "TOTAL",
        "Gross Sales": total_gross, "Net Sales": total_net, "COGS": total_cogs, "Profit": total_profit,
        "% Gross Profit": pct_profit, "% GPM": pct_profit_margin,
    })

    render_styled_table(
        display, _highlight_profit_pct, pct_cols=["% Gross Profit", "% GPM"],
        fmt_dict={
            "Gross Sales": FMT_RP, "Net Sales": FMT_RP, "COGS": FMT_RP, "Profit": FMT_RP,
            "% Gross Profit": "{:.2f}%", "% GPM": "{:.2f}%",
        },
        has_total_row=True,
    )

    # ── Breakdown per Cabang/Customer/Salesman ──
    st.markdown("#### Breakdown Profit per Cabang/Customer/Salesman")
    render_value_breakdown(df_scope, "Profit", key_prefix="cogs", fmt_cell=FMT_RP, subj_options=["Cabang", "Customer", "Salesman"])
