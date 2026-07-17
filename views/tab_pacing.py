# ============================================================
# 📈 TAB: PACING CHART (STAGING HARIAN)
# ============================================================
import calendar
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.components import render_card
from utils.data_loader import list_bulan_standar


def fmt_rupiah(v):
    """'Rp 1.234.567' — titik sebagai separator ribuan, tanpa desimal."""
    if v is None or pd.isna(v):
        v = 0
    return f"Rp {v:,.0f}".replace(",", ".")


def render(df_order, df_target, df_kalkerja):
    if df_order is None or df_order.empty:
        st.warning("Data Order belum siap.")
        return

    tahun_list = sorted(df_order["Tahun"].dropna().unique().tolist())
    if not tahun_list:
        st.warning("Data Order belum siap.")
        return
    tahun_terbaru = tahun_list[-1]

    # ── Filter baris 1: Tahun, Bulan, Area (opsional) — di atas chart, bukan sidebar ──
    col_tahun, col_bulan, col_area = st.columns(3)

    with col_tahun:
        tahun_options = [str(t) for t in tahun_list]
        pilih_tahun_raw = st.pills(
            "Pilih Tahun", tahun_options, selection_mode="single",
            default=str(tahun_terbaru), key="pacing_tahun",
        )
    pilih_tahun = int(pilih_tahun_raw) if pilih_tahun_raw else tahun_terbaru

    # Default bulan = bulan terakhir yang ada data order di tahun terpilih
    df_tahun_ini = df_order[df_order["Tahun"] == pilih_tahun]
    bulan_num_terakhir = int(df_tahun_ini["Bulan_Num"].max()) if not df_tahun_ini.empty else 1
    bulan_default = list_bulan_standar[bulan_num_terakhir - 1]

    with col_bulan:
        pilih_bulan_raw = st.pills(
            "Pilih Bulan", list_bulan_standar, selection_mode="single",
            default=bulan_default, key="pacing_bulan",
        )
    pilih_bulan = pilih_bulan_raw if pilih_bulan_raw else bulan_default
    bulan_num = list_bulan_standar.index(pilih_bulan) + 1

    area_options = sorted(df_order["Kode_Area"].dropna().unique().tolist())
    with col_area:
        pilih_area = st.pills(
            "Filter Area (opsional)", area_options, selection_mode="single", key="pacing_area",
        )

    # ── Filter baris 2: Cabang — "Semua Cabang" = kumulatif seluruh cabang (default) ──
    cabang_scope = df_order[df_order["Kode_Area"] == pilih_area] if pilih_area else df_order
    cabang_options = ["Semua Cabang"] + sorted(cabang_scope["Cabang"].dropna().unique().tolist())
    cabang_key = "pacing_cabang"
    if st.session_state.get(cabang_key) not in cabang_options:
        st.session_state[cabang_key] = cabang_options[0]
    pilih_cabang = st.selectbox("Pilih Cabang", cabang_options, key=cabang_key)

    # ── Siapkan data bulan terpilih ──
    df_month = df_order[(df_order["Tahun"] == pilih_tahun) & (df_order["Bulan_Num"] == bulan_num)]
    df_target_month = df_target[(df_target["Tahun"] == pilih_tahun) & (df_target["Bulan_Num"] == bulan_num)]
    if pilih_cabang != "Semua Cabang":
        df_month = df_month[df_month["Cabang"] == pilih_cabang]
        df_target_month = df_target_month[df_target_month["Cabang"] == pilih_cabang]

    target_bulan = df_target_month["Target"].sum()
    if target_bulan <= 0:
        st.warning(f"Target belum tersedia untuk {pilih_cabang} di {pilih_bulan} {pilih_tahun}.")
        return

    row_kalkerja = df_kalkerja[(df_kalkerja["Tahun"] == pilih_tahun) & (df_kalkerja["Bulan_Num"] == bulan_num)]
    if row_kalkerja.empty or row_kalkerja["Hari_Kerja"].iloc[0] <= 0:
        st.warning(f"Data hari kerja belum tersedia untuk {pilih_bulan} {pilih_tahun}.")
        return
    hari_kerja = float(row_kalkerja["Hari_Kerja"].iloc[0])
    staging_per_hari = target_bulan / hari_kerja

    days_in_month = calendar.monthrange(pilih_tahun, bulan_num)[1]
    hari_list = list(range(1, days_in_month + 1))

    today = date.today()
    if (pilih_tahun, bulan_num) > (today.year, today.month):
        last_valid_day = 0  # bulan di masa depan, belum ada data sama sekali
    elif (pilih_tahun, bulan_num) == (today.year, today.month):
        last_valid_day = today.day  # bulan berjalan, baru berjalan sampai hari ini
    else:
        last_valid_day = days_in_month  # bulan sudah lewat, data lengkap sebulan penuh

    # ── Staging kumulatif: Senin-Jumat penuh, Sabtu setengah, Minggu libur ──
    staging_kumulatif = []
    akumulasi = 0.0
    for day in hari_list:
        dow = date(pilih_tahun, bulan_num, day).weekday()
        if dow == 6:
            increment = 0.0
        elif dow == 5:
            increment = staging_per_hari * 0.5
        else:
            increment = staging_per_hari
        akumulasi += increment
        staging_kumulatif.append(akumulasi)

    # ── Actual harian & kumulatif ──
    daily_order = df_month.groupby(df_month["SO_Date"].dt.day)["Order"].sum()

    daily_values, actual_kumulatif = [], []
    akumulasi = 0.0
    for day in hari_list:
        if day > last_valid_day:
            daily_values.append(None)
            actual_kumulatif.append(None)
            continue
        val = float(daily_order.get(day, 0.0))
        akumulasi += val
        daily_values.append(val)
        actual_kumulatif.append(akumulasi)

    total_order = df_month["Order"].sum()
    achievement = (total_order / target_bulan * 100) if target_bulan else 0.0

    # ── Card Metrics ──
    ach_color = "#10b981" if achievement >= 100 else "#ef4444"
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(render_card("", "Target Bulan", fmt_rupiah(target_bulan), f"{pilih_bulan} {pilih_tahun}"), unsafe_allow_html=True)
    with col2:
        st.markdown(render_card("", "Total Order", fmt_rupiah(total_order), pilih_cabang), unsafe_allow_html=True)
    with col3:
        st.markdown(render_card("", "Achievement", f'<span style="color:{ach_color}">{achievement:.1f}%</span>', "Total Order vs Target"), unsafe_allow_html=True)
    with col4:
        st.markdown(render_card("", "Hari Kerja", f"{hari_kerja:g} hari", f"Staging: {fmt_rupiah(staging_per_hari)}/hari"), unsafe_allow_html=True)

    # ── Chart ──
    bar_colors = []
    for val, stg in zip(actual_kumulatif, staging_kumulatif):
        if val is None:
            bar_colors.append("rgba(0,0,0,0)")
        elif val >= stg:
            bar_colors.append("#10b981")
        else:
            bar_colors.append("#ef4444")

    actual_hover = [fmt_rupiah(v) if v is not None else "" for v in actual_kumulatif]
    staging_hover = [fmt_rupiah(v) for v in staging_kumulatif]
    daily_hover = [fmt_rupiah(v) if v is not None else "" for v in daily_values]
    daily_plot = [(-v if v is not None else None) for v in daily_values]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=hari_list, y=actual_kumulatif, name="Actual Kumulatif",
        marker_color=bar_colors, marker_line_width=0,
        customdata=actual_hover,
        hovertemplate="<b>Tanggal %{x}</b><br>Kumulatif: %{customdata}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=hari_list, y=staging_kumulatif, name="Staging",
        mode="lines", line=dict(color="rgba(226,232,240,0.7)", dash="dash", width=2),
        customdata=staging_hover,
        hovertemplate="<b>Tanggal %{x}</b><br>Staging: %{customdata}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        x=hari_list, y=daily_plot, name="Order Harian",
        marker_color="#38bdf8", opacity=0.45, marker_line_width=0,
        customdata=daily_hover,
        hovertemplate="<b>Tanggal %{x}</b><br>Order Harian: %{customdata}<extra></extra>",
    ))

    fig.add_hline(
        y=target_bulan, line_dash="dash", line_color="#f59e0b", line_width=2,
        annotation_text=f"Target: {fmt_rupiah(target_bulan)}",
        annotation_font_color="#f59e0b", annotation_position="top left",
    )

    fig.update_layout(
        barmode="overlay", height=600,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title=dict(text="Tanggal", font=dict(color="white", size=14)),
            tickfont=dict(color="white", size=12), tickmode="linear", dtick=1,
            gridcolor="#222",
        ),
        yaxis=dict(
            title=dict(text="Kumulatif Order (Rp)", font=dict(color="white", size=14)),
            tickfont=dict(color="white", size=12), gridcolor="#333333",
            zeroline=True, zerolinecolor="#666", zerolinewidth=2,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="center", x=0.5, font=dict(color="white", size=13)),
        hoverlabel=dict(bgcolor="#1e293b", font_color="white", font_size=13),
        margin=dict(t=70, b=40, l=60, r=40),
    )

    st.plotly_chart(fig, use_container_width=True)

    if df_month.empty:
        st.info(f"Belum ada order untuk {pilih_cabang} di {pilih_bulan} {pilih_tahun}.")
