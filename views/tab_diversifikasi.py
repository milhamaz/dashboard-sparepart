# ============================================================
# 🌈 TAB: DIVERSIFIKASI PRODUK (segmentasi customer berbasis komposisi kategori)
# ============================================================
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.matgroup_engine import compute_matgroup_link, MATGROUP_COLORS, MATGROUP_ORDER
from utils.customer_matgroup_engine import build_customer_category_profile
from utils.components import render_card, render_quadrant_chart, render_tile_filter, auto_table_height
from utils.styles import fmt_rp, fmt_rp_full

# Pola segmentasi rule-based yang sama dengan tab Segmentasi (SDM) — tapi sumbunya diganti
# ke sisi PRODUK: seberapa lebar kategori yang dibeli (Breadth) × seberapa besar
# ketergantungan ke 1 kategori terbesar (Top-1 Mat Group Concentration). Sumber risikonya
# kategori produk yang lesu, bukan customer yang lepas (Concentration Risk di Productivity).
_MIN_N_BARIS = 5      # customer dengan baris transaksi < ini masuk "Sample Kecil"
_X_THRESHOLD = 30.0   # Breadth (%) — ±3 dari 10 kategori tersedia
_Y_THRESHOLD = 80.0   # Top-1 Mat Group Concentration (%) — "80% revenue dari 1 kategori itu rawan"

_ARCHETYPE_ORDER = ["Portofolio Seimbang", "Lebar tapi Timpang", "Sempit Seimbang", "Terkonsentrasi Rawan", "Sample Kecil"]
_ARCHETYPE_META = {
    "Portofolio Seimbang": {
        "icon": "🟢", "color": "#10b981", "bg": "rgba(16,185,129,0.15)",
        "desc": "Breadth tinggi, Concentration rendah — belanja tersebar sehat di banyak kategori; paling tahan terhadap pelemahan satu kategori.",
    },
    "Lebar tapi Timpang": {
        "icon": "🔵", "color": "#2563eb", "bg": "rgba(37,99,235,0.15)",
        "desc": "Breadth tinggi, Concentration tinggi — membeli banyak kategori, namun revenue tetap didominasi satu kategori; kategori lainnya baru sebatas coba-coba.",
    },
    "Sempit Seimbang": {
        "icon": "🟡", "color": "#f59e0b", "bg": "rgba(245,158,11,0.15)",
        "desc": "Breadth rendah, Concentration rendah — hanya membeli sedikit kategori tapi porsinya berimbang; kandidat awal penawaran kategori baru.",
    },
    "Terkonsentrasi Rawan": {
        "icon": "🚨", "color": "#ef4444", "bg": "rgba(239,68,68,0.15)",
        "desc": "Breadth rendah, Concentration tinggi — mayoritas revenue bergantung pada satu kategori; paling rawan apabila kategori tersebut sedang lesu.",
    },
    "Sample Kecil": {
        "icon": "⚪", "color": "#94a3b8", "bg": "rgba(148,163,184,0.15)",
        "desc": f"Baris transaksi <{_MIN_N_BARIS} — Breadth dan Concentration terlalu mudah menyimpang sehingga belum dapat diklasifikasikan secara andal.",
    },
}


def _style_archetype(val):
    meta = _ARCHETYPE_META.get(val)
    if not meta:
        return ""
    return f'background-color: {meta["bg"]}; color: {meta["color"]}; font-weight: bold;'


def _classify(row):
    if row["N_Baris"] < _MIN_N_BARIS:
        return "Sample Kecil"
    breadth_high = row["Breadth"] >= _X_THRESHOLD
    conc_high = row["Top1_Share"] >= _Y_THRESHOLD
    if breadth_high and not conc_high:
        return "Portofolio Seimbang"
    if breadth_high and conc_high:
        return "Lebar tapi Timpang"
    if not breadth_high and conc_high:
        return "Terkonsentrasi Rawan"
    return "Sempit Seimbang"


def _build_diversification_df(cust_cat, attr):
    n_available = cust_cat["Mat_Group"].nunique()
    if n_available == 0:
        return pd.DataFrame(), 0

    per_cust = cust_cat.groupby("Customer_No").agg(
        Total_Actual=("Actual", "sum"), N_Kategori=("Mat_Group", "nunique"),
    )
    top1 = cust_cat.sort_values("Actual", ascending=False).drop_duplicates("Customer_No").set_index("Customer_No")
    per_cust["Top1_Cat"] = top1["Mat_Group"]
    per_cust["Top1_Share"] = top1["Actual"] / per_cust["Total_Actual"] * 100
    per_cust["Breadth"] = per_cust["N_Kategori"] / n_available * 100

    df = per_cust.reset_index().merge(attr, on="Customer_No", how="left")
    df["Customer"] = df["Customer_No"].astype(str) + " - " + df["Customer_Name"].astype(str)
    df["Archetype"] = df.apply(_classify, axis=1)
    return df, n_available


def _render_table_breakdown(selected_row, cust_cat):
    """Breakdown: komposisi belanja per kategori untuk customer yang dipilih."""
    cust_no = selected_row["Customer_No"]
    cust_name = selected_row["Customer_Name"]
    archetype = selected_row["Archetype"]
    meta = _ARCHETYPE_META.get(archetype, {})

    st.markdown(
        f"#### Breakdown Komposisi — {meta.get('icon', '')} {cust_no} - {cust_name}"
        f" <span style='color:{meta.get('color', '#94a3b8')};font-weight:bold'>({archetype})</span>",
        unsafe_allow_html=True,
    )

    cat_data = cust_cat[cust_cat["Customer_No"] == cust_no].copy()
    if cat_data.empty:
        st.info("Tidak ada data kategori untuk customer ini.")
        return

    total = cat_data["Actual"].sum()
    cat_data["Pct"] = cat_data["Actual"] / total * 100
    cat_data = cat_data.sort_values("Actual", ascending=False)

    ordered_cats = [m for m in MATGROUP_ORDER if m != "Unclassified" and m in cat_data["Mat_Group"].values]
    cat_data_ordered = cat_data.set_index("Mat_Group").reindex(ordered_cats).dropna(subset=["Actual"])

    col_chart, col_table = st.columns([1, 1])
    with col_chart:
        fig = go.Figure(go.Bar(
            x=cat_data_ordered["Pct"],
            y=cat_data_ordered.index,
            orientation="h",
            marker_color=[MATGROUP_COLORS.get(k, "#64748b") for k in cat_data_ordered.index],
            text=[f"{v:.1f}%" for v in cat_data_ordered["Pct"]],
            textposition="auto", textfont=dict(color="#f8fafc", size=13),
            hovertext=[
                f"<b>{k}</b><br>{fmt_rp_full(r['Actual'])}<br>{r['Pct']:.1f}%"
                for k, r in cat_data_ordered.iterrows()
            ],
            hovertemplate="%{hovertext}<extra></extra>",
        ))
        fig.update_layout(
            height=60 + len(cat_data_ordered) * 40,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title=dict(text="% dari Total Actual", font=dict(color="white", size=12)), tickfont=dict(color="white", size=11), gridcolor="#333333"),
            yaxis=dict(tickfont=dict(color="white", size=12), autorange="reversed"),
            margin=dict(l=10, r=20, t=5, b=5),
        )
        st.plotly_chart(fig, use_container_width=True, key="chart_divers_cust_breakdown")

    with col_table:
        display_bd = cat_data_ordered.reset_index().rename(columns={
            "Mat_Group": "Kategori", "Actual": "Total Actual", "Pct": "Kontribusi (%)",
        })[["Kategori", "Total Actual", "Kontribusi (%)"]]

        def _color_cat(val):
            c = MATGROUP_COLORS.get(val)
            return f"color: {c}; font-weight: bold;" if c else ""

        st.dataframe(
            display_bd.style
            .map(_color_cat, subset=["Kategori"])
            .format({"Total Actual": fmt_rp_full, "Kontribusi (%)": "{:.1f}%"}),
            use_container_width=True, hide_index=True,
            height=min(auto_table_height(len(display_bd)), 400),
        )
        st.caption(f"Total Actual: {fmt_rp_full(total)}")


def _render_exposure_drilldown(selected_cat, rawan):
    """Drill-down: daftar customer Terkonsentrasi Rawan yang Top-1-nya = kategori terpilih."""
    customers = rawan[rawan["Top1_Cat"] == selected_cat].sort_values("Total_Actual", ascending=False)
    color = MATGROUP_COLORS.get(selected_cat, "#64748b")
    st.markdown(
        f"#### Customer Terkonsentrasi Rawan — Top-1: "
        f"<span style='color:{color};font-weight:bold'>{selected_cat}</span>",
        unsafe_allow_html=True,
    )
    customers["Top1_Actual"] = customers["Total_Actual"] * customers["Top1_Share"] / 100
    display_drill = customers[["Customer", "Cabang", "Kelas_Customer", "N_Kategori", "Top1_Share", "Top1_Actual", "Total_Actual"]].rename(columns={
        "Kelas_Customer": "Kelas", "N_Kategori": "Jml Kategori",
        "Top1_Share": "Konsentrasi Top-1 (%)", "Top1_Actual": "Actual Top-1",
        "Total_Actual": "Total Actual",
    })
    st.dataframe(
        display_drill.style.format({
            "Konsentrasi Top-1 (%)": "{:.1f}%", "Actual Top-1": fmt_rp_full,
            "Total Actual": fmt_rp_full, "Jml Kategori": "{:.0f}",
        }),
        use_container_width=True, hide_index=True,
        height=min(auto_table_height(len(display_drill)), 400),
    )
    st.caption(f"{len(customers)} customer bergantung ke {selected_cat}.")


def render(df_supply_final, df_part_master, pilih_tahun):
    if df_supply_final is None or df_supply_final.empty:
        st.info("Tidak ada data Supply untuk filter yang dipilih.")
        return
    if df_part_master is None or df_part_master.empty:
        st.warning("Data master part_master.xlsx belum siap.")
        return

    linked, _ = compute_matgroup_link(df_supply_final, df_part_master, partnumber_col="Partnumber")
    linked_ty = linked[linked["Tahun"] == pilih_tahun]
    cust_cat, attr = build_customer_category_profile(linked_ty)
    if cust_cat.empty:
        st.info(f"Tidak ada transaksi terklasifikasi untuk tahun {pilih_tahun} pada scope ini.")
        return

    df, n_available = _build_diversification_df(cust_cat, attr)
    if df.empty:
        st.info("Tidak ada customer aktif pada scope ini.")
        return

    counts = df["Archetype"].value_counts()
    cols = st.columns(len(_ARCHETYPE_ORDER))
    for col, arch in zip(cols, _ARCHETYPE_ORDER):
        meta = _ARCHETYPE_META[arch]
        with col:
            st.markdown(
                render_card(meta["icon"], arch, f"{int(counts.get(arch, 0))}", f"dari {len(df)} customer aktif", accent_color=meta["color"]),
                unsafe_allow_html=True,
            )

    st.markdown(f"#### Peta Diversifikasi Customer — {pilih_tahun}")
    n_excluded = int((df["Archetype"] == "Sample Kecil").sum())
    st.caption(
        f"Sumbu X = Breadth (persentase dari {n_available} kategori tersedia yang dibeli), "
        "sumbu Y = Top-1 Mat Group Concentration (persentase revenue dari 1 kategori terbesar), "
        f"besar bubble = Total Actual. Garis putus-putus = ambang {_X_THRESHOLD:.0f}% / {_Y_THRESHOLD:.0f}%."
        + (f" {n_excluded} customer Sample Kecil tidak ditampilkan di peta, tapi tetap ada di tabel di bawah." if n_excluded else "")
    )

    chart_df = df[df["Archetype"] != "Sample Kecil"]
    chart_highlight = st.text_input(
        "🔍 Cari & Sorot di Peta", key="divers_chart_highlight",
        placeholder="Ketik kode/nama customer buat nyorot titiknya di peta di bawah...",
    )
    if chart_highlight.strip():
        n_match = int(chart_df["Customer"].astype(str).str.upper().str.contains(chart_highlight.strip().upper(), na=False).sum())
        if n_match == 0:
            st.caption("Tidak ditemukan di peta — mungkin masuk kategori Sample Kecil (cek tabel di bawah), atau nama beda dari yang dicari.")
        else:
            st.caption(f"🎯 {n_match} titik disorot di peta (ring putih, sisanya dipudarkan).")

    render_quadrant_chart(
        chart_df, "Customer", x_col="Breadth", y_col="Top1_Share", size_col="Total_Actual",
        category_col="Archetype",
        category_colors={a: _ARCHETYPE_META[a]["color"] for a in _ARCHETYPE_ORDER if a != "Sample Kecil"},
        x_title="Breadth (%)", y_title="Top-1 Concentration (%)", value_fmt=fmt_rp,
        key="chart_divers_quadrant", x_threshold=_X_THRESHOLD, y_threshold=_Y_THRESHOLD,
        extra_hover_cols=[
            ("Top1_Cat", "Kategori Top-1", lambda v: v),
            ("N_Kategori", "Jumlah Kategori", lambda v: f"{v:.0f}"),
        ],
        highlight_query=chart_highlight,
    )

    # ── Revenue terekspos per kategori: kalau kategori X lesu, berapa revenue customer
    # Terkonsentrasi Rawan yang ikut terancam ──
    rawan = df[df["Archetype"] == "Terkonsentrasi Rawan"]
    exposure_selected_cat = None
    if not rawan.empty:
        st.markdown("#### Revenue Terekspos per Kategori — dari Customer Terkonsentrasi Rawan")
        st.caption(
            "Total Actual customer **Terkonsentrasi Rawan**, dikelompokkan menurut kategori Top-1 mereka — "
            "apabila kategori ini melemah, revenue sebesar inilah yang paling terancam ikut hilang. "
            "**Klik bar** untuk drill-down sekaligus memfilter tabel di bawah."
        )
        exposure = rawan.groupby("Top1_Cat")["Total_Actual"].sum().sort_values(ascending=False)
        n_cust_per_cat = rawan.groupby("Top1_Cat")["Customer_No"].nunique()
        fig = go.Figure(go.Bar(
            x=exposure.values, y=exposure.index, orientation="h",
            marker_color=[MATGROUP_COLORS.get(k, "#64748b") for k in exposure.index],
            text=[fmt_rp(v) for v in exposure.values],
            textposition="auto", textfont=dict(color="#f8fafc", size=13),
            hovertext=[
                f"<b>{k}</b><br>{fmt_rp_full(v)}<br>{int(n_cust_per_cat.get(k, 0))} customer bergantung ke kategori ini"
                for k, v in exposure.items()
            ],
            hovertemplate="%{hovertext}<extra></extra>",
        ))
        fig.update_layout(
            height=70 + len(exposure) * 44,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title=dict(text="Total Actual Terekspos (Rp)", font=dict(color="white", size=13)), tickfont=dict(color="white", size=12), gridcolor="#333333"),
            yaxis=dict(tickfont=dict(color="white", size=12), autorange="reversed"),
            margin=dict(l=10, r=30, t=10, b=10),
        )
        exposure_event = st.plotly_chart(fig, use_container_width=True, key="chart_divers_exposure", on_select="rerun")

        sel_points = (exposure_event.selection.get("points", [])
                      if exposure_event and hasattr(exposure_event, "selection") else [])
        if sel_points:
            selected_cat = sel_points[0].get("y") or sel_points[0].get("label")
            if selected_cat and selected_cat in rawan["Top1_Cat"].values:
                exposure_selected_cat = selected_cat
                _render_exposure_drilldown(selected_cat, rawan)

    # ── Tabel lengkap ──
    title_suffix = ""
    if exposure_selected_cat:
        color = MATGROUP_COLORS.get(exposure_selected_cat, "#64748b")
        title_suffix = f" — <span style='color:{color};font-weight:bold'>Top-1: {exposure_selected_cat}</span>"
    st.markdown(f"#### Daftar Lengkap Diversifikasi Customer{title_suffix}", unsafe_allow_html=True)
    archetype_options = [a for a in _ARCHETYPE_ORDER if a in df["Archetype"].unique()]
    col_filter, col_search = st.columns([2, 1])
    with col_filter:
        pilih_archetype = render_tile_filter("Filter Kategori Segmentasi", archetype_options, key="divers_archetype_filter")
    with col_search:
        st.markdown('<div style="height:0.55rem"></div>', unsafe_allow_html=True)
        search_query = st.text_input("Cari Customer", key="divers_search_query", placeholder="Ketik kode atau nama customer...")

    table = df[df["Archetype"].isin(pilih_archetype)].copy()
    if exposure_selected_cat:
        table = table[table["Top1_Cat"] == exposure_selected_cat]
    if search_query.strip():
        q = search_query.strip().upper()
        table = table[table["Customer"].astype(str).str.upper().str.contains(q, na=False)]

    table = table.sort_values("Total_Actual", ascending=False).reset_index(drop=True)

    display = table.rename(columns={
        "Kelas_Customer": "Kelas", "N_Kategori": "Jumlah Kategori", "Breadth": "Breadth (%)",
        "Top1_Cat": "Kategori Top-1", "Top1_Share": "Top-1 Concentration (%)",
        "Total_Actual": "Total Actual", "Archetype": "Kategori Segmentasi",
    })[[
        "Customer", "Cabang", "Kelas", "Jumlah Kategori", "Breadth (%)", "Kategori Top-1",
        "Top-1 Concentration (%)", "Total Actual", "Kategori Segmentasi",
    ]]

    event = st.dataframe(
        display.style
        .map(_style_archetype, subset=["Kategori Segmentasi"])
        .format({
            "Breadth (%)": "{:.0f}%", "Top-1 Concentration (%)": "{:.1f}%",
            "Total Actual": fmt_rp_full, "Jumlah Kategori": "{:.0f}",
        }),
        use_container_width=True, hide_index=True,
        height=min(auto_table_height(len(display)), 600),
        on_select="rerun", selection_mode="single-row",
        key="divers_table_select",
    )
    st.caption(f"{len(display):,} customer ditampilkan — klik baris untuk breakdown komposisi.".replace(",", "."))

    sel_rows = event.selection.get("rows", []) if event and hasattr(event, "selection") else []
    if sel_rows:
        idx = sel_rows[0]
        sel = table.iloc[idx]
        st.markdown("---")
        _render_table_breakdown(sel, cust_cat)

    st.markdown("---")
    st.markdown("### Penjelasan")
    archetype_desc = "\n".join(f"  - **{_ARCHETYPE_META[a]['icon']} {a}**: {_ARCHETYPE_META[a]['desc']}" for a in _ARCHETYPE_ORDER)
    st.markdown(
        "- **Diversifikasi Produk** memakai pola segmentasi rule-based yang sama dengan tab **Segmentasi** di halaman "
        "SDM, namun sumbunya diganti ke sisi produk: **Breadth** (seberapa lebar kategori produk yang dibeli) dan "
        "**Top-1 Mat Group Concentration** (seberapa besar revenue customer bergantung pada satu kategori). Sumber "
        "risikonya adalah **kategori produk yang melemah** — pelengkap dari Concentration Risk di tab Productivity "
        "yang melihat ketergantungan pada satu customer:\n"
        f"{archetype_desc}\n"
        f"- Ambang {_X_THRESHOLD:.0f}% (Breadth) dan {_Y_THRESHOLD:.0f}% (Concentration) adalah titik awal yang dapat "
        "disesuaikan setelah tersedia cukup histori sebaran data yang sebenarnya.\n"
        "- Kategori **Unclassified** tidak diikutkan dalam perhitungan Breadth/Concentration, dan pasangan "
        "customer×kategori dengan net belanja ≤ 0 (retur melebihi pembelian) dianggap tidak membeli kategori itu.\n"
        f"- Scope data mengikuti **Filter General** dan tahun terpilih ({pilih_tahun}), basis **Actual (Supply)** — "
        "konsisten dengan tab Komposisi Kategori di halaman Analisa Partnumber."
    )
