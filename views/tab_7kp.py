# ============================================================
# 🎯 TAB: 7 KEY PRODUCT (7KP) — Order Based
# ============================================================
import streamlit as st
import pandas as pd
from utils.data_loader import list_bulan_standar
from utils.components import render_card, auto_table_height, render_tile_filter, render_top_cabang_heatmap

def match_7kp(df, df_7kp_lookup, df_7kp_prefix):
    if df.empty or "Partnumber" not in df.columns:
        return pd.DataFrame(), 0, 0
    master_pnos = set(df_7kp_lookup["Partnumber"].unique())
    df_exact = df[df["Partnumber"].isin(master_pnos)].copy()
    df_exact = pd.merge(df_exact, df_7kp_lookup[["Partnumber", "Grup_Part_7KP"]], on="Partnumber", how="left")
    exact_count = len(df_exact)
    remaining = df[~df["Partnumber"].isin(master_pnos)].copy()
    prefix_count = 0
    if not remaining.empty and df_7kp_prefix is not None and not df_7kp_prefix.empty:
        prefix_grup = dict(zip(df_7kp_prefix["Prefix"], df_7kp_prefix["Grup_Part_7KP"]))
        remaining["Grup_Part_7KP"] = remaining["Partnumber"].apply(
            lambda pno: next((g for p, g in prefix_grup.items() if str(pno).startswith(p)), None))
        df_prefix = remaining[remaining["Grup_Part_7KP"].notna()]
        prefix_count = len(df_prefix)
    else:
        df_prefix = pd.DataFrame()
    return pd.concat([df_exact, df_prefix], ignore_index=True), exact_count, prefix_count


def render(df_order_final, df_supply_final, df_7kp_lookup, df_7kp_prefix, pilih_tahun, pilih_bulan, fmt_rp, highlight_pct):
    if df_7kp_lookup is None or df_7kp_lookup.empty or "Partnumber" not in df_7kp_lookup.columns:
        st.warning("Data master Pno7KP.xlsx belum siap atau kolom 'Partnumber' tidak ditemukan.")
        return

    df_ord_7kp, exact_count, prefix_count = match_7kp(df_order_final, df_7kp_lookup, df_7kp_prefix)
    if df_ord_7kp.empty:
        st.info("Tidak ada data 7KP untuk filter yang dipilih.")
        return

    list_grup = sorted(df_ord_7kp["Grup_Part_7KP"].dropna().unique().tolist())
    pilih_grup = render_tile_filter("🎯 Filter Grup Part 7KP", list_grup, key="7kp_grup_filter")
    df_ord_7kp = df_ord_7kp[df_ord_7kp["Grup_Part_7KP"].isin(pilih_grup)]
    if df_ord_7kp.empty:
        st.info("Tidak ada data untuk kategori yang dipilih.")
        return

    # ── Cards ──
    kategori_totals = df_ord_7kp.groupby("Grup_Part_7KP")["Order"].sum().sort_values(ascending=False)
    kategori_list = kategori_totals.index.tolist()
    for row_start in range(0, len(kategori_list), 4):
        row_items = kategori_list[row_start:row_start + 4]
        cols = st.columns(len(row_items))
        for col, kat in zip(cols, row_items):
            with col:
                st.markdown(
                    f'<div class="custom-card" style="padding:12px;">'
                    f'<div class="card-title" style="font-size:15px;">{kat}</div>'
                    f'<div class="card-value" style="font-size:18px;">{fmt_rp(kategori_totals[kat])}</div>'
                    f'</div>', unsafe_allow_html=True)

    # ── Pivot Table ──
    pivot = df_ord_7kp.groupby(["Grup_Part_7KP", "Bulan"])["Order"].sum().reset_index()
    pivot_table = pivot.pivot_table(index="Bulan", columns="Grup_Part_7KP", values="Order", aggfunc="sum").fillna(0)
    ordered_rows = [b for b in list_bulan_standar if b in pivot_table.index]
    pivot_table = pivot_table.reindex(ordered_rows)
    col_order = pivot_table.sum().sort_values(ascending=False).index.tolist()
    pivot_table = pivot_table[col_order]
    pivot_table.loc["TOTAL"] = pivot_table.sum()
    total_all = pivot_table.loc["TOTAL"].sum()
    komposisi = (pivot_table.loc["TOTAL"] / total_all * 100) if total_all > 0 else pivot_table.loc["TOTAL"] * 0
    pivot_table.loc["Komposisi (%)"] = komposisi
    pivot_table.index.name = "Program 7KP"

    display_table = pivot_table.copy()
    for col in display_table.columns:
        display_table.loc["Komposisi (%)", col] = round(komposisi[col], 1)

    styled_pivot = display_table.style.format(
        formatter=lambda x: f"{x:.1f}%", subset=pd.IndexSlice["Komposisi (%)", :]
    ).format(
        formatter=lambda x: f"Rp {x:,.0f}".replace(",", "."), subset=pd.IndexSlice[display_table.index[:-1], :]
    ).set_properties(**{'text-align': 'right', 'font-size': '13px'}
    ).set_properties(subset=pd.IndexSlice["TOTAL", :], **{
        'font-weight': 'bold', 'background-color': 'rgba(245, 158, 11, 0.15)', 'border-top': '2px solid #f59e0b'}
    ).set_properties(subset=pd.IndexSlice["Komposisi (%)", :], **{
        'font-style': 'italic', 'background-color': 'rgba(99, 102, 241, 0.1)', 'color': '#a5b4fc'})

    st.dataframe(styled_pivot, use_container_width=True, height=auto_table_height(len(display_table)))

    # ══════════════════════════════════════════════════════════
    # HEATMAP: Top 7 Cabang — MoM Growth Coloring (Revised)
    # ══════════════════════════════════════════════════════════
    st.markdown("#### Top 7 Cabang per Kategori")

    if "Cabang" not in df_ord_7kp.columns:
        st.info("Kolom 'Cabang' tidak ditemukan.")
        return

    pilih_heatmap_kat = st.selectbox("Pilih kategori:", kategori_list, key="7kp_heatmap_kat")
    df_kat = df_ord_7kp[df_ord_7kp["Grup_Part_7KP"] == pilih_heatmap_kat]
    if df_kat.empty:
        st.info(f"Tidak ada data untuk {pilih_heatmap_kat}.")
        return

    render_top_cabang_heatmap(df_kat, value_col="Order", key=f"heatmap_{pilih_heatmap_kat}")

    # Teks Keterangan Exact Match & Prefix Match
    if prefix_count > 0:
        st.markdown(
            f'<p style="font-size:10px; color:#64748b; margin-top:2px;">'
            f'<i>{exact_count:,} rows exact match + {prefix_count:,} rows via prefix matching</i></p>',
            unsafe_allow_html=True)