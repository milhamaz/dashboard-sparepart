# ============================================================
# 🎁 TAB: GEBYUR (TMO Campaign + Budget Linkage Item D)
# ============================================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import list_bulan_standar
from utils.components import compute_item_d_burn, hitung_avg, render_card, render_tile_filter, auto_table_height, TOTAL_ROW_STYLE


def render(df_order_final, df_tmo_lookup, df_dprog_lookup, pilih_bulan, fmt_rp, fmt_liter):
    if df_tmo_lookup is None or df_tmo_lookup.empty:
        st.warning("Data master TMO belum siap.")
        return

    tmo_cols = ["Partnumber", "Partname", "Liter", "Jenis"]

    # ── Order TMO + SO_Type == "C" + Campaign_Code tidak blank (definisi "Gebyur") ──
    df_ord_gebyur_base = pd.merge(df_order_final, df_tmo_lookup[tmo_cols], on="Partnumber", how="inner") if "Partnumber" in df_order_final.columns else pd.DataFrame()

    if df_ord_gebyur_base.empty:
        st.info("Tidak ada data Gebyur untuk filter yang dipilih.")
        return

    mask_campaign = (
        (df_ord_gebyur_base["SO_Type"] == "C") &
        (df_ord_gebyur_base["Campaign_Code"].notna()) &
        (df_ord_gebyur_base["Campaign_Code"].astype(str).str.strip() != "")
    ) if "Campaign_Code" in df_ord_gebyur_base.columns else (df_ord_gebyur_base["SO_Type"] == "C")
    df_ord_gebyur_base = df_ord_gebyur_base[mask_campaign].copy()

    if df_ord_gebyur_base.empty:
        st.info("Tidak ada transaksi Gebyur (SO Type C + Campaign Code) untuk filter yang dipilih.")
        return

    df_ord_gebyur_base["Volume"] = df_ord_gebyur_base["Qty"] * df_ord_gebyur_base["Liter"]
    df_ord_gebyur_base["Revenue"] = df_ord_gebyur_base["Order"]  # sudah dihitung di data_loader

    # ── Filter Jenis TMO (tile) ──
    all_jenis = sorted(df_ord_gebyur_base["Jenis"].dropna().unique().tolist())
    pilih_jenis = render_tile_filter("🏷️ Filter Jenis TMO (Gebyur)", all_jenis, key="gebyur_jenis_filter")

    df_ord_gebyur = df_ord_gebyur_base[df_ord_gebyur_base["Jenis"].isin(pilih_jenis) & df_ord_gebyur_base["Bulan"].isin(pilih_bulan)]
    if df_ord_gebyur.empty:
        st.info("Tidak ada data untuk kombinasi filter yang dipilih.")
        return

    # ── Metrics ──
    total_vol = df_ord_gebyur["Volume"].sum()
    total_revenue = df_ord_gebyur["Revenue"].sum()
    m_ord_vol = df_ord_gebyur.groupby(["Bulan_Num", "Bulan"])["Volume"].sum().reset_index()
    avg_vol = hitung_avg(total_vol, m_ord_vol, "Volume")

    # ── Budget 1% untuk Item D ──
    budget_item_d = total_revenue * 0.01

    # ── Hitung Actual Burn Item D ──
    df_d_matched = compute_item_d_burn(df_order_final, df_dprog_lookup)
    actual_burn_d = df_d_matched["Burn"].sum() if not df_d_matched.empty else 0

    sisa_budget = budget_item_d - actual_burn_d

    # ── Cards Row 1: Volume & Revenue (murni Order, tanpa Supply/Actual/Last Year) ──
    c1, c2 = st.columns(2)
    with c1: st.markdown(render_card("", "Vol. Order Gebyur", fmt_liter(total_vol), f"Avg: {fmt_liter(avg_vol)}/bln"), unsafe_allow_html=True)
    with c2: st.markdown(render_card("", "Revenue Gebyur", fmt_rp(total_revenue), "Basis kalkulasi 1%"), unsafe_allow_html=True)

    # ── Cards Row 2: Budget Linkage → Item D ──
    st.markdown("#### Budget Linkage → Item D")
    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown(f'<div class="custom-card" style="border-left: 5px solid #f59e0b;"><div class="card-title">Budget 1% Gebyur</div><div class="card-value">{fmt_rp(budget_item_d)}</div><div class="card-sub">1% × Revenue Gebyur</div></div>', unsafe_allow_html=True)
    with b2:
        st.markdown(f'<div class="custom-card" style="border-left: 5px solid #ef4444;"><div class="card-title">Actual Burn Item D</div><div class="card-value">{fmt_rp(actual_burn_d)}</div><div class="card-sub">Σ Qty × Price × Scp_Disc</div></div>', unsafe_allow_html=True)
    with b3:
        sisa_color = "#10b981" if sisa_budget >= 0 else "#ef4444"
        sisa_label = "Sisa Budget" if sisa_budget >= 0 else "Deficit"
        st.markdown(f'<div class="custom-card" style="border-left: 5px solid {sisa_color};"><div class="card-title">{sisa_label}</div><div class="card-value" style="color:{sisa_color}">{fmt_rp(abs(sisa_budget))}</div><div class="card-sub">Budget - Burn</div></div>', unsafe_allow_html=True)

    if "Cabang" not in df_ord_gebyur.columns:
        st.info("Kolom 'Cabang' tidak ditemukan.")
        return

    # ══════════════════════════════════════════════════════════
    # TABEL: Volume Gebyur per Cabang x Bulan
    # ══════════════════════════════════════════════════════════
    st.markdown("#### Volume Gebyur per Cabang (Liter)")

    pivot = df_ord_gebyur.groupby(["Cabang", "Bulan"])["Volume"].sum().reset_index()
    pivot_table = pivot.pivot_table(index="Cabang", columns="Bulan", values="Volume", aggfunc="sum").fillna(0)
    month_cols = [b for b in list_bulan_standar if b in pivot_table.columns]  # cuma bulan yang benar-benar ada datanya
    pivot_table = pivot_table[month_cols]
    pivot_table = pivot_table.sort_index()  # Cabang alfabetis
    pivot_table.loc["TOTAL"] = pivot_table.sum()
    pivot_table.index.name = "Cabang"

    styled_pivot = pivot_table.style.format(
        lambda x: f"{x:,.0f}".replace(",", ".")
    ).set_properties(**{'text-align': 'right', 'font-size': '13px'}
    ).set_properties(subset=pd.IndexSlice["TOTAL", :], **TOTAL_ROW_STYLE)

    st.dataframe(styled_pivot, use_container_width=True, height=auto_table_height(len(pivot_table)))

    # ══════════════════════════════════════════════════════════
    # BAR CHART HORIZONTAL: Top 7 Cabang — Volume Gebyur
    # ══════════════════════════════════════════════════════════
    st.markdown("#### Top 7 Cabang — Volume Gebyur")

    cab_totals = df_ord_gebyur.groupby("Cabang").agg(Volume=("Volume", "sum"), Revenue=("Revenue", "sum")).reset_index()
    top7 = cab_totals.sort_values("Volume", ascending=False).head(7)

    hover_texts = []
    for row in top7.itertuples():
        vol_str = f"{row.Volume:,.0f}".replace(",", ".")
        rev_str = f"Rp {row.Revenue:,.0f}".replace(",", ".")
        hover_texts.append(f"<b>{row.Cabang}</b><br>Volume: {vol_str} L<br>Revenue: {rev_str}")

    fig_cab = go.Figure(go.Bar(
        x=top7["Volume"], y=top7["Cabang"], orientation="h",
        marker_color="#2563eb",
        text=[f"{v:,.0f} L".replace(",", ".") for v in top7["Volume"]],
        textposition="auto",  # otomatis di dalam bar kalau muat, di luar kalau tidak
        textfont=dict(color="#f8fafc", size=13),
        hovertext=hover_texts,
        hovertemplate="%{hovertext}<extra></extra>",
    ))
    fig_cab.update_layout(
        height=70 + (len(top7) * 58),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title=dict(text="Volume (Liter)", font=dict(color="white", size=14)), tickfont=dict(color="white", size=12), gridcolor="#333333"),
        yaxis=dict(tickfont=dict(color="white", size=13), autorange="reversed"),
        margin=dict(l=10, r=30, t=20, b=10),
        showlegend=False,
    )
    st.plotly_chart(fig_cab, use_container_width=True, key="chart_gebyur_cabang")
