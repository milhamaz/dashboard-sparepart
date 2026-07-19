# ============================================================
# 🧬 TAB: KOMPOSISI KATEGORI (Mat Group — TGP/AVANZA/TMO/dst)
# ============================================================
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.matgroup_engine import compute_matgroup_link, MATGROUP_ORDER, MATGROUP_COLORS
from utils.components import (
    render_card, build_pivot, render_bidirectional_barh_chart, cleanup_selection,
    auto_table_height, TOTAL_ROW_STYLE, hitung_growth,
)
from utils.styles import fmt_rp, fmt_rp_full, fmt_pct, highlight_growth_pct

TOP_N_SUBJECT = 10

SUBJECT_DIMENSIONS = {"Cabang": "Cabang", "Salesman": "Salesman_Name", "Customer": "Customer_Label"}


def _prep_scope(df_supply, df_part_master):
    df, stats = compute_matgroup_link(df_supply, df_part_master, partnumber_col="Partnumber")
    df["Cabang"] = df["Cabang"].astype(str).str.strip()
    df["Salesman_Name"] = df["Salesman_Name"].astype(str).str.strip().str.upper()
    df["Customer_Name"] = df["Customer_Name"].astype(str).str.strip().str.upper()
    df["Customer_Label"] = df["Customer_No"].astype(str) + " - " + df["Customer_Name"]
    return df, stats


def _matgroup_totals(scope):
    totals = scope.groupby("Mat_Group")["Actual"].sum()
    totals = totals.reindex(MATGROUP_ORDER).dropna()
    return totals[totals > 0].sort_values(ascending=False)


def _render_komposisi_donut(totals):
    grand_total = totals.sum()
    colors = [MATGROUP_COLORS.get(k, "#64748b") for k in totals.index]
    hover = [
        f"<b>{k}</b><br>{fmt_rp_full(v)}<br>{(v / grand_total * 100):.1f}% dari total Actual"
        for k, v in totals.items()
    ]
    fig = go.Figure(go.Pie(
        labels=totals.index, values=totals.values, hole=0.55,
        marker=dict(colors=colors, line=dict(color="#0e1117", width=2)),
        textinfo="percent", textfont=dict(color="white", size=12),
        hovertext=hover, hovertemplate="%{hovertext}<extra></extra>",
        sort=False,
    ))
    fig.update_layout(
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="v", font=dict(color="white", size=12), yanchor="middle", y=0.5),
        margin=dict(l=10, r=10, t=20, b=20),
        annotations=[dict(
            text=f"<b>{fmt_rp(grand_total)}</b><br><span style='font-size:11px;color:#94a3b8;'>Total Actual</span>",
            x=0.5, y=0.5, font=dict(size=15, color="white"), showarrow=False,
        )],
    )
    st.plotly_chart(fig, use_container_width=True, key="chart_komposisi_donut")


def _render_komposisi_table(totals):
    grand_total = totals.sum()
    display = totals.rename("Actual").to_frame()
    display["Kontribusi (%)"] = display["Actual"] / grand_total * 100
    display.index.name = "Kategori Produk"
    display = display.reset_index()

    def _style_kategori(row):
        color = MATGROUP_COLORS.get(row["Kategori Produk"], "#64748b")
        return [f"border-left: 4px solid {color};", "", ""]

    st.dataframe(
        display.style.apply(_style_kategori, axis=1).format({"Actual": fmt_rp_full, "Kontribusi (%)": "{:.1f}%"}),
        use_container_width=True, hide_index=True,
        height=min(auto_table_height(len(display)), 420),
    )


def _render_growth_section(scope, pilih_tahun):
    ly = scope[scope["Tahun"] == pilih_tahun - 1].groupby("Mat_Group")["Actual"].sum()
    ty = scope[scope["Tahun"] == pilih_tahun].groupby("Mat_Group")["Actual"].sum()
    growth_df = pd.DataFrame({"Last_Year": ly, "This_Year": ty}).fillna(0)
    growth_df = growth_df[(growth_df["Last_Year"] > 0) | (growth_df["This_Year"] > 0)]
    if growth_df.empty:
        st.info("Tidak ada data untuk perbandingan Growth YoY pada scope ini.")
        return
    growth_df = growth_df.sort_values("This_Year", ascending=False).reset_index()
    growth_df["Growth"] = growth_df.apply(lambda r: hitung_growth(r["This_Year"], r["Last_Year"]), axis=1)

    render_bidirectional_barh_chart(
        growth_df, "Mat_Group", "Last_Year", "This_Year",
        left_name=str(pilih_tahun - 1), right_name=str(pilih_tahun),
        left_color="#64748b", right_color="#2563eb",
        value_fmt=fmt_rp, key="chart_komposisi_growth",
        left_value_label=f"Actual {pilih_tahun - 1}", right_value_label=f"Actual {pilih_tahun}",
    )

    display = growth_df.rename(columns={
        "Mat_Group": "Kategori Produk", "Last_Year": f"Actual {pilih_tahun - 1}",
        "This_Year": f"Actual {pilih_tahun}", "Growth": "Growth (%)",
    })
    st.dataframe(
        display.style.map(highlight_growth_pct, subset=["Growth (%)"]).format({
            f"Actual {pilih_tahun - 1}": fmt_rp_full, f"Actual {pilih_tahun}": fmt_rp_full, "Growth (%)": "{:.1f}%",
        }),
        use_container_width=True, hide_index=True,
        height=min(auto_table_height(len(display)), 420),
    )


def _render_subject_composition(scope):
    subject = st.radio(
        "Lihat Komposisi berdasarkan", list(SUBJECT_DIMENSIONS.keys()), horizontal=True, key="komposisi_subject",
    )
    subj_col = SUBJECT_DIMENSIONS[subject]

    top_subjects = scope.groupby(subj_col)["Actual"].sum().nlargest(TOP_N_SUBJECT).index.tolist()
    chart_scope = scope[scope[subj_col].isin(top_subjects)]
    pivot_pct = pd.crosstab(chart_scope[subj_col], chart_scope["Mat_Group"], values=chart_scope["Actual"], aggfunc="sum").fillna(0)
    pivot_pct = pivot_pct.reindex(columns=MATGROUP_ORDER).dropna(axis=1, how="all").fillna(0)
    pivot_pct = pivot_pct.loc[top_subjects]  # urut sesuai ranking Top N, bukan alfabetis
    pivot_pct_norm = pivot_pct.div(pivot_pct.sum(axis=1), axis=0) * 100

    fig = go.Figure()
    for kat in pivot_pct_norm.columns:
        hover_texts = [
            f"<b>{subj}</b> — {kat}<br>{pivot_pct_norm.loc[subj, kat]:.1f}% dari komposisi<br>{fmt_rp_full(pivot_pct.loc[subj, kat])}"
            for subj in pivot_pct_norm.index
        ]
        fig.add_trace(go.Bar(
            x=pivot_pct_norm[kat], y=pivot_pct_norm.index, orientation="h", name=kat,
            marker_color=MATGROUP_COLORS.get(kat, "#64748b"),
            hovertext=hover_texts, hovertemplate="%{hovertext}<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack",
        height=70 + (len(pivot_pct_norm) * 42),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title=dict(text="Komposisi (%)", font=dict(color="white", size=13)), tickfont=dict(color="white", size=11), gridcolor="#333333", range=[0, 100]),
        yaxis=dict(tickfont=dict(color="white", size=12), autorange="reversed"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="white", size=11)),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True, key="chart_komposisi_subject_stacked")
    st.caption(f"Top {TOP_N_SUBJECT} {subject} berdasarkan total Actual — tiap bar dinormalisasi ke 100% supaya komposisi antar-{subject.lower()} langsung terbanding, terlepas dari beda skala revenue-nya.")

    st.markdown(f"##### Tabel Lengkap Komposisi per {subject}")
    if subject == "Customer":
        search_query = st.text_input("Cari Customer", key="komposisi_search_customer", placeholder="Ketik kode atau nama customer...")
    else:
        search_query = ""

    full_scope = scope
    if search_query.strip():
        q = search_query.strip().upper()
        full_scope = full_scope[full_scope[subj_col].astype(str).str.upper().str.contains(q, na=False)]

    pivot = build_pivot(full_scope, subj_col, "Mat_Group", MATGROUP_ORDER, "Actual", "sum", sort_mode="total_desc")
    pivot.index.name = subject

    styled = pivot.style.format(fmt_rp_full).set_properties(
        **{"text-align": "right", "font-size": "13px"}
    ).set_properties(
        subset=pd.IndexSlice[:, "TOTAL"], **{"font-weight": "bold", "background-color": "rgba(245, 158, 11, 0.08)"}
    ).set_properties(
        subset=pd.IndexSlice["TOTAL", :], **TOTAL_ROW_STYLE
    )
    st.dataframe(styled, use_container_width=True, height=min(auto_table_height(len(pivot)), 600))


def render(df_supply, df_part_master):
    if df_supply is None or df_supply.empty:
        st.warning("Data Supply belum siap.")
        return
    if df_part_master is None or df_part_master.empty:
        st.warning("Data master part_master.xlsx belum siap.")
        return

    df, stats = _prep_scope(df_supply, df_part_master)

    tahun_list = sorted(df["Tahun"].dropna().unique().tolist())
    if not tahun_list:
        st.info("Belum ada data Supply.")
        return
    tahun_terbaru = tahun_list[-1]

    col_tahun, col_cabang = st.columns([1, 2])
    with col_tahun:
        tahun_options = [str(t) for t in tahun_list]
        pilih_tahun_raw = st.pills(
            "Pilih Tahun", tahun_options, selection_mode="single",
            default=str(tahun_terbaru), key="komposisi_tahun",
        )
    pilih_tahun = int(pilih_tahun_raw) if pilih_tahun_raw else tahun_terbaru

    cabang_options = sorted(df["Cabang"].dropna().unique().tolist())
    cleanup_selection("komposisi_cabang", cabang_options)
    with col_cabang:
        pilih_cabang = st.multiselect("Filter Cabang", cabang_options, key="komposisi_cabang", placeholder="Semua (klik untuk filter)")

    scope_all_years = df[df["Tahun"].isin([pilih_tahun, pilih_tahun - 1])]
    if pilih_cabang:
        scope_all_years = scope_all_years[scope_all_years["Cabang"].isin(pilih_cabang)]

    scope = scope_all_years[scope_all_years["Tahun"] == pilih_tahun]
    if scope.empty:
        st.info(f"Tidak ada data Supply untuk tahun {pilih_tahun}.")
        return

    totals = _matgroup_totals(scope)
    if totals.empty:
        st.info("Tidak ada Actual > 0 pada scope ini.")
        return

    kategori_dominan = totals.idxmax()
    pct_dominan = totals.max() / totals.sum() * 100
    ly_total = scope_all_years.loc[scope_all_years["Tahun"] == pilih_tahun - 1, "Actual"].sum()
    ty_total = totals.sum()
    growth_nasional = hitung_growth(ty_total, ly_total)
    unclassified_pct = (scope["Mat_Group"] == "Unclassified").sum() / len(scope) * 100 if len(scope) else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("💰", "Total Actual", fmt_rp(ty_total), f"Tahun {pilih_tahun}"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("🏆", "Kategori Dominan", kategori_dominan, f"{pct_dominan:.1f}% dari total Actual", accent_color=MATGROUP_COLORS.get(kategori_dominan)), unsafe_allow_html=True)
    with c3:
        growth_color = "#10b981" if growth_nasional >= 0 else "#ef4444"
        st.markdown(
            f'<div class="custom-card"><div class="card-title">Growth YoY Nasional</div>'
            f'<div class="card-value" style="color:{growth_color}">{growth_nasional:+.1f}%</div>'
            f'<div class="card-sub">Actual {pilih_tahun} vs {pilih_tahun - 1}</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(render_card("❔", "Baris Belum Terklasifikasi", fmt_pct(unclassified_pct), "dari total baris Actual di scope ini"), unsafe_allow_html=True)

    st.markdown("#### Komposisi Revenue per Kategori Produk")
    col_donut, col_table = st.columns([1, 1])
    with col_donut:
        _render_komposisi_donut(totals)
    with col_table:
        _render_komposisi_table(totals)

    st.markdown("#### Growth YoY per Kategori Produk")
    _render_growth_section(scope_all_years, pilih_tahun)

    st.markdown(f"#### Komposisi per Subjek — {pilih_tahun}")
    _render_subject_composition(scope)

    match_rate = (stats["n_total"] - stats["n_unclassified"]) / stats["n_total"] * 100 if stats["n_total"] else 0
    with st.expander(f"Rincian tingkat kecocokan Partnumber ke Kategori Produk — {match_rate:.1f}% berhasil diklasifikasikan"):
        st.markdown(
            f"- Total baris data Actual: **{stats['n_total']:,}**\n"
            f"- Kecocokan lewat kode pengganti (`part_number_substitusi`): **{stats['n_substitusi']:,}**\n"
            f"- Kecocokan persis (`part_number`): **{stats['n_exact']:,}**\n"
            f"- Kecocokan lewat pendekatan prefix (kandidat substitusi produk): **{stats['n_prefix']:,}**\n"
            f"- Tidak berhasil diklasifikasikan (masuk kategori **Unclassified**): **{stats['n_unclassified']:,}**"
        )

    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- **Kategori Produk (Mat Group)** mengelompokkan setiap Partnumber ke dalam salah satu kategori material "
        "(TGP, AVANZA, TOOLS & TGA, DYNA/ARPI, AC, TGB, TMO, CHEMICAL, T-OPT, atau BUSI) berdasarkan `part_master.xlsx`, "
        "sehingga revenue yang selama ini hanya dapat dilihat per Cabang/Salesman/Customer/waktu kini juga dapat "
        "dipecah berdasarkan jenis produk yang terjual.\n"
        "- **Unclassified** adalah Partnumber yang belum berhasil dicocokkan ke kategori manapun (baik lewat kecocokan "
        "persis, kode pengganti, maupun pendekatan prefix). Baris ini tetap dihitung dalam Total Actual agar angka tetap "
        "sesuai dengan tab lain, hanya kategorinya yang belum diketahui.\n"
        "- **Growth YoY per Kategori Produk** membandingkan Actual tahun yang dipilih dengan tahun sebelumnya, per "
        "kategori — mengikuti periode satu tahun penuh, tidak terikat pada filter Bulan tertentu.\n"
        "- **Komposisi per Subjek** menampilkan proporsi kategori produk untuk Top "
        f"{TOP_N_SUBJECT} Cabang/Salesman/Customer dengan Actual terbesar. Setiap bar dinormalisasi ke 100% agar "
        "komposisi antar-subjek dapat dibandingkan langsung, terlepas dari perbedaan skala revenue masing-masing — "
        "tabel di bawahnya menampilkan nilai Rupiah aktual untuk seluruh subjek pada scope yang dipilih, dapat dicari "
        "lewat kotak pencarian saat dimensi Customer aktif.\n"
        "- Data pada tab ini bersumber dari **Actual (Supply)**, konsisten dengan metrik revenue yang digunakan pada "
        "tab-tab lain di halaman ini."
    )
