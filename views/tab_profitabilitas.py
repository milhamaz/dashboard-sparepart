# ============================================================
# 📊 TAB: PROFITABILITAS PER KATEGORI PRODUK (Mat Group)
# ============================================================
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data_loader import list_bulan_standar
from utils.matgroup_engine import MATGROUP_ORDER, MATGROUP_COLORS
from utils.components import (
    render_card, render_waterfall_chart, cleanup_selection,
    auto_table_height, TOTAL_ROW_STYLE, hitung_growth,
)
from utils.styles import fmt_rp, fmt_rp_full, highlight_growth_pct


def _compute_radar_stats(scope, mg):
    """Hitung 5 metrik untuk 1 mat_group, dinormalisasi 0-100 terhadap semua mat_group."""
    groups = scope.groupby("Mat_Group")
    all_stats = pd.DataFrame({
        "Volume": groups["Qty"].sum(),
        "Revenue": groups["Actual"].sum(),
        "Margin": groups["Pct_Profit_Margin"].mean(),
        "Customers": groups["Customer_No"].nunique(),
        "Frekuensi": groups["Partnumber"].count(),
    }).fillna(0)

    if all_stats.empty or mg not in all_stats.index:
        return None, None

    maxes = all_stats.max()
    normed = (all_stats / maxes.replace(0, 1) * 100).fillna(0)
    return normed.loc[mg], all_stats.loc[mg]


def _render_radar(scope):
    """50:50 layout — kiri: radar chart (multi mat_group, maks 3), kanan: pivot tabel."""
    mg_in_scope = [m for m in MATGROUP_ORDER if m in scope["Mat_Group"].unique() and m != "Unclassified"]
    if not mg_in_scope:
        st.info("Tidak ada data Mat Group yang diklasifikasikan.")
        return

    default_mg = ["TGP"] if "TGP" in mg_in_scope else mg_in_scope[:1]
    ORDER_KEY = "profitabilitas_mg_order"
    PILLS_KEY = "profitabilitas_mg_pills"

    if ORDER_KEY not in st.session_state:
        st.session_state[ORDER_KEY] = list(default_mg)

    if PILLS_KEY in st.session_state:
        raw_sel = [m for m in (st.session_state[PILLS_KEY] or []) if m in mg_in_scope]
        prev_order = [m for m in st.session_state[ORDER_KEY] if m in mg_in_scope]
        added = [m for m in raw_sel if m not in prev_order]
        kept = [m for m in prev_order if m in raw_sel]
        order = kept + added
        if len(order) > 3:
            order = order[-3:]
            st.session_state[PILLS_KEY] = order
        st.session_state[ORDER_KEY] = order

    selected = st.pills(
        "Pilih Kategori Produk (maks 3)", mg_in_scope,
        selection_mode="multi", default=default_mg, key=PILLS_KEY,
    )

    pilih_mgs = [m for m in st.session_state.get(ORDER_KEY, default_mg) if m in (selected or [])]
    if not pilih_mgs:
        pilih_mgs = list(default_mg)

    col_radar, col_pivot = st.columns(2)

    with col_radar:
        st.markdown("##### Radar Profil Kategori")
        categories = ["Volume (Qty)", "Revenue", "Margin %", "Jumlah Customer", "Frekuensi Transaksi"]

        fig = go.Figure()
        captions = []
        for mg in pilih_mgs:
            normed, raw = _compute_radar_stats(scope, mg)
            if normed is None:
                continue
            values = normed.tolist() + [normed.tolist()[0]]
            color = MATGROUP_COLORS.get(mg, "#64748b")
            hex_c = color.lstrip("#")
            r_c, g_c, b_c = int(hex_c[0:2], 16), int(hex_c[2:4], 16), int(hex_c[4:6], 16)
            fill_rgba = f"rgba({r_c},{g_c},{b_c},0.15)"

            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                fill="toself",
                fillcolor=fill_rgba,
                line=dict(color=color, width=2),
                marker=dict(size=6, color=color),
                name=mg,
                hovertemplate=f"<b>{mg}</b> · %{{theta}}<br>Skor: %{{r:.1f}}/100<extra></extra>",
            ))
            captions.append(
                f"**{mg}** — Vol: {raw['Volume']:,.0f} | Rev: {fmt_rp(raw['Revenue'])} | "
                f"Margin: {raw['Margin']:.1f}% | Cust: {int(raw['Customers'])} | "
                f"Trx: {int(raw['Frekuensi']):,}".replace(",", ".")
            )

        if not fig.data:
            st.info("Tidak ada data.")
            return

        fig.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(color="#94a3b8", size=10), gridcolor="#333333"),
                angularaxis=dict(tickfont=dict(color="white", size=12), gridcolor="#333333"),
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            height=420,
            margin=dict(l=60, r=60, t=30, b=30),
            showlegend=len(pilih_mgs) > 1,
            legend=dict(font=dict(color="white", size=12), bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig, use_container_width=True, key="chart_radar_profitabilitas")

        for cap in captions:
            st.caption(cap)

    with col_pivot:
        st.markdown("##### Ringkasan Semua Kategori")
        summary = scope[scope["Mat_Group"] != "Unclassified"].groupby("Mat_Group").agg(
            Volume=("Qty", "sum"),
            Revenue=("Actual", "sum"),
            Transaksi=("Partnumber", "count"),
            Profit=("Profit", "sum"),
            Customers=("Customer_No", "nunique"),
        ).reindex([m for m in MATGROUP_ORDER if m != "Unclassified"]).dropna(how="all").fillna(0)
        summary["Margin %"] = np.where(summary["Revenue"] != 0, summary["Profit"] / summary["Revenue"] * 100, 0)
        summary = summary.sort_values("Profit", ascending=False)
        summary.index.name = "Kategori"

        def _highlight_selected(row):
            if row.name in pilih_mgs:
                return ['background-color: rgba(59,130,246,0.12)'] * len(row)
            return [''] * len(row)

        styled = summary.style.format({
            "Volume": "{:,.0f}", "Revenue": fmt_rp_full, "Transaksi": "{:,.0f}",
            "Profit": fmt_rp_full, "Customers": "{:,.0f}", "Margin %": "{:.1f}%",
        }).map(highlight_growth_pct, subset=["Margin %"]).apply(
            _highlight_selected, axis=1,
        ).set_properties(
            **{"text-align": "right", "font-size": "13px"}
        )
        st.dataframe(styled, use_container_width=True, height=min(auto_table_height(len(summary)), 420))


def _render_waterfall(scope):
    """Waterfall chart — kontribusi profit per mat_group."""
    profit_by_mg = scope[scope["Mat_Group"] != "Unclassified"].groupby("Mat_Group")["Profit"].sum()
    profit_by_mg = profit_by_mg.reindex([m for m in MATGROUP_ORDER if m != "Unclassified"]).dropna()
    profit_by_mg = profit_by_mg[profit_by_mg != 0].sort_values(ascending=False)

    if profit_by_mg.empty:
        st.info("Tidak ada data profit per kategori.")
        return

    labels = profit_by_mg.index.tolist() + ["Total"]
    values = profit_by_mg.values.tolist() + [profit_by_mg.sum()]
    measures = ["relative"] * len(profit_by_mg) + ["total"]

    render_waterfall_chart(labels, values, measures, fmt_rp_full, key="chart_waterfall_profitabilitas", yaxis_title="Profit (Rp)")
    st.caption("Kontribusi profit tiap kategori produk — bar hijau = profit positif, merah = negatif, biru = total akumulasi.")


def _render_bubble(scope):
    """Bubble chart — X: volume (qty), Y: margin %, size: revenue."""
    agg = scope[scope["Mat_Group"] != "Unclassified"].groupby("Mat_Group").agg(
        Volume=("Qty", "sum"),
        Revenue=("Actual", "sum"),
        Profit=("Profit", "sum"),
        Net_Sales=("Net_Sales", "sum"),
    ).reset_index()
    agg["Margin_Pct"] = np.where(agg["Net_Sales"] != 0, agg["Profit"] / agg["Net_Sales"] * 100, 0)
    agg = agg[agg["Revenue"] > 0]

    if agg.empty:
        st.info("Tidak ada data.")
        return

    max_size = agg["Revenue"].max()
    size_ref = (2.0 * max_size / (55.0 ** 2)) if max_size > 0 else 1.0

    fig = go.Figure()
    for _, row in agg.iterrows():
        color = MATGROUP_COLORS.get(row["Mat_Group"], "#64748b")
        fig.add_trace(go.Scatter(
            x=[row["Volume"]], y=[row["Margin_Pct"]], mode="markers+text",
            marker=dict(size=[row["Revenue"]], sizemode="area", sizeref=size_ref, sizemin=8,
                        color=color, line=dict(width=1, color="#0e1117"), opacity=0.85),
            text=[row["Mat_Group"]], textposition="top center",
            textfont=dict(color="white", size=11),
            hovertext=[
                f"<b>{row['Mat_Group']}</b><br>"
                f"Volume: {row['Volume']:,.0f} pcs<br>"
                f"Revenue: {fmt_rp_full(row['Revenue'])}<br>"
                f"Profit: {fmt_rp_full(row['Profit'])}<br>"
                f"Margin: {row['Margin_Pct']:.1f}%"
            ],
            hovertemplate="%{hovertext}<extra></extra>",
            showlegend=False,
        ))

    fig.update_layout(
        height=480,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title=dict(text="Volume (Qty)", font=dict(color="white", size=14)),
                   tickfont=dict(color="white", size=12), gridcolor="#333333"),
        yaxis=dict(title=dict(text="Profit Margin %", font=dict(color="white", size=14)),
                   tickfont=dict(color="white", size=12), gridcolor="#333333"),
        hoverlabel=dict(bgcolor="#1e293b", font_color="white", font_size=13),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig, use_container_width=True, key="chart_bubble_profitabilitas")
    st.caption("Ukuran bubble = revenue, posisi vertikal = margin %, posisi horizontal = volume qty.")


def render(df_supply):
    if df_supply is None or df_supply.empty:
        st.warning("Data Supply belum siap.")
        return
    if "Mat_Group" not in df_supply.columns:
        st.warning("Kolom Mat_Group belum tersedia — jalankan ulang converter Parquet.")
        return

    tahun_list = sorted(df_supply["Tahun"].dropna().unique().tolist())
    if not tahun_list:
        st.info("Belum ada data Supply.")
        return
    tahun_terbaru = tahun_list[-1]

    col_tahun, col_cabang = st.columns([1, 2])
    with col_tahun:
        pilih_tahun_raw = st.pills(
            "Pilih Tahun", [str(t) for t in tahun_list], selection_mode="single",
            default=str(tahun_terbaru), key="profitabilitas_tahun",
        )
    pilih_tahun = int(pilih_tahun_raw) if pilih_tahun_raw else tahun_terbaru

    cabang_options = sorted(df_supply["Cabang"].dropna().astype(str).str.strip().unique().tolist())
    cleanup_selection("profitabilitas_cabang", cabang_options)
    with col_cabang:
        pilih_cabang = st.multiselect("Filter Cabang", cabang_options, key="profitabilitas_cabang", placeholder="Semua (klik untuk filter)")

    scope = df_supply[df_supply["Tahun"] == pilih_tahun]
    if pilih_cabang:
        scope = scope[scope["Cabang"].astype(str).str.strip().isin(pilih_cabang)]

    if scope.empty:
        st.info(f"Tidak ada data Supply untuk tahun {pilih_tahun}.")
        return

    _render_radar(scope)

    st.markdown("#### Kontribusi Profit per Kategori Produk (Waterfall)")
    _render_waterfall(scope)

    st.markdown("#### Volume vs Margin per Kategori Produk (Bubble)")
    _render_bubble(scope)
