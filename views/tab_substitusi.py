# ============================================================
# 🔁 TAB: SUBSTITUSI PARTNUMBER (lifecycle kode lama -> kode baru)
# ============================================================
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.substitusi_engine import (
    compute_substitution_families, STATUS_ORDER, STATUS_COLOR, TREND_ORDER, TREND_COLOR,
    TREND_BAND_PCT, CROSSOVER_WINDOW,
)
from utils.components import render_card, validate_lookup, auto_table_height
from utils.styles import fmt_rp, fmt_rp_full

FMT_QTY = lambda v: f"{v:,.0f}".replace(",", ".")


def _style_status(val):
    color = STATUS_COLOR.get(val)
    return f"color: {color}; font-weight: bold;" if color else ""


def _style_tren(val):
    color = TREND_COLOR.get(val)
    return f"color: {color}; font-weight: bold;" if color else ""


def _render_family_detail(monthly, family_row):
    """Line chart deret bulanan 1 keluarga: volume kode lama vs kode baru + total keluarga —
    di sinilah kelihatan kapan volume mulai pindah, dan apakah TOTAL-nya tetap/naik/turun
    setelah pergantian kode."""
    grp = monthly[monthly["Family"] == family_row["Family"]].sort_values("Periode")
    if grp.empty:
        st.info("Tidak ada deret bulanan untuk keluarga ini.")
        return

    labels = grp["Label"].tolist()
    total = (grp["Qty_Lama"] + grp["Qty_Baru"]).tolist()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=grp["Qty_Lama"], name="Kode Lama", mode="lines+markers",
        line=dict(color="#ef4444", width=2), marker=dict(size=6),
        hovertemplate="<b>%{x}</b><br>Kode Lama: %{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=labels, y=grp["Qty_Baru"], name="Kode Baru", mode="lines+markers",
        line=dict(color="#10b981", width=2), marker=dict(size=6),
        hovertemplate="<b>%{x}</b><br>Kode Baru: %{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=labels, y=total, name="Total Keluarga", mode="lines",
        line=dict(color="#94a3b8", width=1.5, dash="dot"),
        hovertemplate="<b>%{x}</b><br>Total: %{y:,.0f}<extra></extra>",
    ))
    if family_row["Crossover"] != "—" and family_row["Crossover"] in labels:
        fig.add_vline(
            x=labels.index(family_row["Crossover"]), line_dash="dash", line_color="#f59e0b", opacity=0.7,
        )
        fig.add_annotation(
            x=labels.index(family_row["Crossover"]), y=1, yref="paper", showarrow=False,
            text="Crossover", font=dict(color="#f59e0b", size=11), yanchor="bottom",
        )

    fig.update_layout(
        height=420,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", separators=",.",
        xaxis=dict(tickfont=dict(color="white", size=12)),
        yaxis=dict(title=dict(text="Qty per Bulan", font=dict(color="white", size=13)), tickfont=dict(color="white", size=12), gridcolor="#333333"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="white", size=13)),
        hoverlabel=dict(bgcolor="#1e293b", font_color="white", font_size=13),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True, key="chart_substitusi_detail")


def render(df_supply, df_part_master):
    if df_supply is None or df_supply.empty:
        st.warning("Data Supply belum siap.")
        return
    if not validate_lookup(df_part_master, ["part_number", "part_number_substitusi", "part_name", "mat_group"], "part_master.xlsx"):
        return

    families, monthly = compute_substitution_families(df_supply, df_part_master)
    if families.empty:
        st.info("Tidak ada keluarga substitusi yang kode lamanya masih bertransaksi di window data Supply.")
        return

    n_selesai = int((families["Status"] == "Transisi Selesai").sum())
    n_berjalan = int((families["Status"] == "Transisi Berjalan").sum())
    n_belum = int((families["Status"] == "Belum Mulai").sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("🔁", "Keluarga Substitusi Terpantau", f"{len(families):,}".replace(",", "."), "kode lama masih bertransaksi di window data"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("✅", "Transisi Selesai", f"{n_selesai:,}".replace(",", "."), f"kode lama sudah berhenti di {CROSSOVER_WINDOW} bulan aktif terakhir", accent_color=STATUS_COLOR["Transisi Selesai"]), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("🔄", "Transisi Berjalan", f"{n_berjalan:,}".replace(",", "."), "kode lama & baru masih sama-sama jalan", accent_color=STATUS_COLOR["Transisi Berjalan"]), unsafe_allow_html=True)
    with c4:
        st.markdown(render_card("⏳", "Belum Mulai", f"{n_belum:,}".replace(",", "."), "kode baru belum ada transaksi sama sekali", accent_color=STATUS_COLOR["Belum Mulai"]), unsafe_allow_html=True)

    # ── Kesehatan volume pasca-crossover: pembeda "produk turun" vs "cuma ganti kode" ──
    crossed = families[families["Tren"] != "Belum Crossover"]
    n_naik = int((crossed["Tren"] == "Naik").sum())
    n_stabil = int((crossed["Tren"] == "Stabil").sum())
    n_turun = int((crossed["Tren"] == "Turun").sum())

    st.markdown("#### Kesehatan Volume Setelah Pergantian Kode")
    st.caption(
        f"Rata-rata volume bulanan keluarga (lama + baru digabung) pada {CROSSOVER_WINDOW} bulan SESUDAH crossover "
        f"dibanding {CROSSOVER_WINDOW} bulan SEBELUM-nya — **Turun di sini berarti produknya memang melemah**, "
        "bukan sekadar pindah kode; kalau cuma ganti kode, totalnya harusnya Stabil."
    )
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(render_card("📈", "Naik Setelah Ganti Kode", f"{n_naik:,}".replace(",", "."), f"total volume > +{TREND_BAND_PCT:.0f}%", accent_color=TREND_COLOR["Naik"]), unsafe_allow_html=True)
    with k2:
        st.markdown(render_card("➖", "Stabil (Hanya Ganti Kode)", f"{n_stabil:,}".replace(",", "."), f"total volume di dalam ±{TREND_BAND_PCT:.0f}%", accent_color=TREND_COLOR["Stabil"]), unsafe_allow_html=True)
    with k3:
        st.markdown(render_card("📉", "Turun Setelah Ganti Kode", f"{n_turun:,}".replace(",", "."), "produk memang melemah — perlu ditinjau", accent_color=TREND_COLOR["Turun"]), unsafe_allow_html=True)

    # ── Tabel keluarga + filter ──
    st.markdown("#### Daftar Keluarga Substitusi — diurutkan dari nilai terbesar")
    col_status, col_tren, col_search = st.columns([1.2, 1.2, 1.6])
    with col_status:
        pilih_status = st.pills(
            "Filter Status", STATUS_ORDER, selection_mode="multi", default=STATUS_ORDER,
            key="substitusi_status_filter",
        ) or []
    with col_tren:
        pilih_tren = st.pills(
            "Filter Tren Volume", TREND_ORDER, selection_mode="multi", default=TREND_ORDER,
            key="substitusi_tren_filter",
        ) or []
    with col_search:
        search_query = st.text_input(
            "Cari kode/nama part", key="substitusi_search", placeholder="Ketik Partnumber (lama/baru) atau nama part...",
        )

    table = families[families["Status"].isin(pilih_status) & families["Tren"].isin(pilih_tren)]
    if search_query.strip():
        q = search_query.strip().upper()
        table = table[
            table["Family"].astype(str).str.upper().str.contains(q, na=False)
            | table["Kode_Lama"].astype(str).str.upper().str.contains(q, na=False)
            | table["Part_Name"].astype(str).str.upper().str.contains(q, na=False)
        ]

    display = table.rename(columns={
        "Family": "Kode Baru", "Part_Name": "Nama Part", "Mat_Group": "Kategori",
        "Kode_Lama": "Kode Lama", "Qty_Lama_Total": "Qty Kode Lama",
        "Qty_Baru_Total": "Qty Kode Baru", "Actual_Total": "Total Actual",
        "Delta_Pct": "Δ Volume (%)", "Tren": "Tren Volume",
    })[[
        "Kode Baru", "Nama Part", "Kategori", "Kode Lama", "Status", "Crossover",
        "Qty Kode Lama", "Qty Kode Baru", "Total Actual", "Δ Volume (%)", "Tren Volume",
    ]].copy()
    # Δ di-pra-format ke string di sini (bukan lewat na_rep di Styler.format) — st.dataframe
    # merender sel null dari data Arrow sebagai "None" abu-abu dan MENGABAIKAN na_rep Styler,
    # jadi keluarga tanpa baseline crossover bakal nampil "None" mentah kalau dibiarkan float.
    display["Δ Volume (%)"] = display["Δ Volume (%)"].map(lambda v: "—" if pd.isna(v) else f"{v:+.1f}%")
    st.dataframe(
        display.style
        .map(_style_status, subset=["Status"])
        .map(_style_tren, subset=["Tren Volume"])
        .format({
            "Qty Kode Lama": FMT_QTY, "Qty Kode Baru": FMT_QTY, "Total Actual": fmt_rp_full,
        }),
        use_container_width=True, hide_index=True,
        height=min(auto_table_height(len(display)), 520),
    )
    st.caption(f"{len(display):,} dari {len(families):,} keluarga substitusi ditampilkan sesuai filter.".replace(",", "."))

    # ── Detail per keluarga ──
    st.markdown("#### Detail Migrasi Volume per Keluarga")
    if table.empty:
        st.info("Tidak ada keluarga yang lolos filter di atas untuk ditampilkan detailnya.")
    else:
        options = table["Family"].tolist()
        label_map = {
            row["Family"]: f'{row["Family"]} — {row["Part_Name"]} ({row["Status"]})'
            for _, row in table.iterrows()
        }
        pilih_family = st.selectbox(
            "Pilih keluarga substitusi", options, format_func=lambda f: label_map.get(f, f),
            key="substitusi_family_select",
        )
        family_row = table[table["Family"] == pilih_family].iloc[0]

        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.markdown(render_card("", "Kode Lama", family_row["Kode_Lama"], f'digantikan oleh {family_row["Family"]}'), unsafe_allow_html=True)
        with d2:
            st.markdown(render_card("", "Crossover", family_row["Crossover"], "bulan pertama kode baru menyalip kode lama"), unsafe_allow_html=True)
        with d3:
            delta_txt = "—" if pd.isna(family_row["Delta_Pct"]) or family_row["Delta_Pct"] is None else f'{family_row["Delta_Pct"]:+.1f}%'
            st.markdown(render_card("", "Δ Volume Sesudah vs Sebelum", delta_txt, f'{CROSSOVER_WINDOW} bulan sesudah vs sebelum crossover', accent_color=TREND_COLOR.get(family_row["Tren"])), unsafe_allow_html=True)
        with d4:
            st.markdown(render_card("", "Total Actual Keluarga", fmt_rp(family_row["Actual_Total"]), "kode lama + baru, seluruh window data"), unsafe_allow_html=True)

        _render_family_detail(monthly, family_row)

    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- **Keluarga Substitusi** menggabungkan kode lama dan kode penggantinya (dari kolom `part_number_substitusi` "
        "di `part_master.xlsx`) menjadi satu keluarga produk. Rantai substitusi bertingkat (A→B→C) digabung ke kode "
        "terminalnya, dan beberapa kode lama yang menunjuk ke pengganti yang sama otomatis menjadi satu keluarga.\n"
        "- Hanya keluarga yang **kode lamanya masih bertransaksi** di window data Supply yang dipantau di sini — "
        "substitusi yang sudah tuntas jauh sebelum window data dimulai tidak memiliki sinyal transisi yang dapat dilaporkan.\n"
        "- **Crossover** adalah bulan pertama volume kode baru menyalip kode lama. **Δ Volume** membandingkan rata-rata "
        f"volume bulanan total keluarga pada {CROSSOVER_WINDOW} bulan sesudah crossover terhadap {CROSSOVER_WINDOW} bulan "
        "sebelumnya — inilah pembeda antara **produk yang memang melemah** (Turun) dengan **produk yang hanya berganti "
        "kode** (Stabil/Naik), yang pada laporan per-Partnumber biasa akan sama-sama terlihat seperti penurunan.\n"
        f"- Ambang tren ±{TREND_BAND_PCT:.0f}% adalah titik awal yang dapat disesuaikan setelah pola historisnya "
        "terkumpul lebih banyak. **Baseline Kurang** berarti crossover-nya jatuh tepat di awal window data sehingga "
        "tidak ada bulan \"sebelum\" yang dapat dijadikan pembanding.\n"
        "- Volume dihitung dari **Qty Supply** (bukan Rupiah) agar perbandingan antar periode tidak terdistorsi "
        "perubahan harga; Total Actual tetap ditampilkan sebagai konteks nilai."
    )
