# ============================================================
# 📦 TAB: MOVING ANALYSIS (VFM/FM/Medium/SM/VSM/Dead)
# ============================================================
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.matgroup_engine import MATGROUP_ORDER, MATGROUP_COLORS
from utils.components import render_card, cleanup_selection, auto_table_height
from utils.styles import fmt_rp, fmt_rp_full

MOVING_RULES = [
    (range(10, 13), "VFM"),   # 10-12 bulan
    (range(7, 10),  "FM"),    # 7-9 bulan
    (range(4, 7),   "Medium"),# 4-6 bulan
    (range(2, 4),   "SM"),    # 2-3 bulan
    (range(1, 2),   "VSM"),   # 1 bulan
]

MOVING_ORDER = ["VFM", "FM", "Medium", "SM", "VSM", "Dead"]
MOVING_COLORS = {
    "VFM": "#10b981", "FM": "#3b82f6", "Medium": "#f59e0b",
    "SM": "#f97316", "VSM": "#ef4444", "Dead": "#64748b",
}
MOVING_LABELS = {
    "VFM": "Very Fast Moving (10-12 bln)",
    "FM": "Fast Moving (7-9 bln)",
    "Medium": "Medium (4-6 bln)",
    "SM": "Slow Moving (2-3 bln)",
    "VSM": "Very Slow Moving (1 bln)",
    "Dead": "Dead (0 bln)",
}


def _classify_moving(n_months):
    for rng, label in MOVING_RULES:
        if n_months in rng:
            return label
    return "Dead"


def _build_moving_df(scope, pilih_tahun):
    """Klasifikasi tiap Partnumber berdasarkan jumlah bulan muncul dalam 1 tahun."""
    yr = scope[scope["Tahun"] == pilih_tahun]
    if yr.empty:
        return pd.DataFrame()

    pno_stats = yr.groupby("Partnumber").agg(
        N_Bulan=("Bulan_Num", "nunique"),
        Total_Qty=("Qty", "sum"),
        Total_Revenue=("Actual", "sum"),
    ).reset_index()
    pno_stats["Moving"] = pno_stats["N_Bulan"].apply(_classify_moving)

    if "Mat_Group" in yr.columns:
        mg_map = yr.drop_duplicates("Partnumber").set_index("Partnumber")["Mat_Group"]
        pno_stats["Mat_Group"] = pno_stats["Partnumber"].map(mg_map).fillna("Unclassified")

    return pno_stats


def _render_summary_cards(moving_df):
    total_pno = len(moving_df)
    total_rev = moving_df["Total_Revenue"].sum()
    vfm_pct = (moving_df["Moving"] == "VFM").sum() / total_pno * 100 if total_pno else 0
    dead_pct = (moving_df["Moving"] == "Dead").sum() / total_pno * 100 if total_pno else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("", "Total Partnumber", f"{total_pno:,}".replace(",", "."), "Unik dalam periode ini"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("", "Total Revenue", fmt_rp(total_rev), "Dari seluruh partnumber"), unsafe_allow_html=True)
    with c3:
        color = "#10b981" if vfm_pct >= 20 else "#f59e0b"
        st.markdown(render_card("", "% Very Fast Moving", f'<span style="color:{color}">{vfm_pct:.1f}%</span>', "Partnumber aktif 10-12 bulan"), unsafe_allow_html=True)
    with c4:
        color = "#ef4444" if dead_pct >= 30 else "#f59e0b"
        st.markdown(render_card("", "% Dead Stock", f'<span style="color:{color}">{dead_pct:.1f}%</span>', "Partnumber tanpa transaksi"), unsafe_allow_html=True)


def _render_treemap(moving_df):
    """Treemap — size = revenue, color = moving category."""
    tree_data = moving_df[moving_df["Total_Revenue"] > 0].copy()
    if tree_data.empty:
        st.info("Tidak ada data revenue untuk treemap.")
        return

    cat_summary = tree_data.groupby("Moving").agg(
        Revenue=("Total_Revenue", "sum"),
        Count=("Partnumber", "count"),
    ).reindex(MOVING_ORDER).dropna()

    if cat_summary.empty:
        return

    labels, parents, values, colors, hover = [], [], [], [], []
    for cat in cat_summary.index:
        rev = cat_summary.loc[cat, "Revenue"]
        cnt = cat_summary.loc[cat, "Count"]
        cnt_fmt = f"{int(cnt):,}".replace(",", ".")
        labels.append(f"{cat} ({cnt_fmt} pno)")
        parents.append("")
        values.append(rev)
        colors.append(MOVING_COLORS.get(cat, "#64748b"))
        hover.append(f"<b>{MOVING_LABELS.get(cat, cat)}</b><br>{cnt_fmt} partnumber<br>{fmt_rp_full(rev)}")

    fig = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values,
        marker=dict(colors=colors, line=dict(color="#0e1117", width=2)),
        textinfo="label+percent root",
        texttemplate="%{label}<br>%{percentRoot:.2%}",
        textfont=dict(size=14, color="white"),
        hovertext=hover, hovertemplate="%{hovertext}<extra></extra>",
    ))
    fig.update_layout(
        height=450,
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig, use_container_width=True, key="chart_treemap_moving")
    st.caption("Ukuran kotak = proporsi revenue, warna = kategori moving.")


def _render_detail_table(moving_df):
    """Tabel detail per moving category."""
    summary = moving_df.groupby("Moving").agg(
        **{"Jumlah Partnumber": ("Partnumber", "count")},
        **{"Total Qty": ("Total_Qty", "sum")},
        **{"Total Revenue": ("Total_Revenue", "sum")},
    ).reindex(MOVING_ORDER).fillna(0)
    summary["% Partnumber"] = summary["Jumlah Partnumber"] / summary["Jumlah Partnumber"].sum() * 100
    summary["% Revenue"] = summary["Total Revenue"] / summary["Total Revenue"].sum() * 100
    summary.index.name = "Kategori Moving"

    styled = summary.style.format({
        "Jumlah Partnumber": "{:,.0f}",
        "Total Qty": "{:,.0f}",
        "Total Revenue": fmt_rp_full,
        "% Partnumber": "{:.1f}%",
        "% Revenue": "{:.1f}%",
    }).set_properties(**{"text-align": "right", "font-size": "13px"})
    st.dataframe(styled, use_container_width=True, height=auto_table_height(len(summary)))


def render(df_supply):
    if df_supply is None or df_supply.empty:
        st.warning("Data Supply belum siap.")
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
            default=str(tahun_terbaru), key="moving_tahun",
        )
    pilih_tahun = int(pilih_tahun_raw) if pilih_tahun_raw else tahun_terbaru

    cabang_options = sorted(df_supply["Cabang"].dropna().astype(str).str.strip().unique().tolist())
    cleanup_selection("moving_cabang", cabang_options)
    with col_cabang:
        pilih_cabang = st.multiselect("Filter Cabang", cabang_options, key="moving_cabang", placeholder="Semua (klik untuk filter)")

    scope = df_supply.copy()
    scope["Cabang"] = scope["Cabang"].astype(str).str.strip()
    if pilih_cabang:
        scope = scope[scope["Cabang"].isin(pilih_cabang)]

    moving_df = _build_moving_df(scope, pilih_tahun)
    if moving_df.empty:
        st.info(f"Tidak ada data Supply untuk tahun {pilih_tahun}.")
        return

    _render_summary_cards(moving_df)

    st.markdown("#### Distribusi Revenue per Kategori Moving (Treemap)")
    _render_treemap(moving_df)

    st.markdown("#### Ringkasan per Kategori Moving")
    _render_detail_table(moving_df)

    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- **Moving Analysis** mengklasifikasikan setiap Partnumber berdasarkan jumlah bulan "
        "di mana Partnumber tersebut memiliki transaksi (Supply/Actual) dalam 1 tahun:\n"
        "  - **VFM** (Very Fast Moving): aktif 10-12 bulan — produk inti yang selalu terjual\n"
        "  - **FM** (Fast Moving): aktif 7-9 bulan\n"
        "  - **Medium**: aktif 4-6 bulan\n"
        "  - **SM** (Slow Moving): aktif 2-3 bulan\n"
        "  - **VSM** (Very Slow Moving): aktif hanya 1 bulan\n"
        "  - **Dead**: tidak ada transaksi sama sekali dalam tahun yang dipilih\n"
        "- **Treemap** menunjukkan proporsi revenue tiap kategori — ukuran kotak sebanding "
        "dengan kontribusi revenue, sehingga terlihat berapa besar revenue yang datang dari "
        "produk yang aktif vs jarang terjual."
    )
