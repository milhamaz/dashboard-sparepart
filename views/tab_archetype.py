# ============================================================
# 🧭 TAB: SEGMENTASI PRODUKTIVITAS (archetype Cabang/Salesman, rule-based)
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from utils.data_loader import list_bulan_standar
from utils.productivity_engine import compute_productivity_df
from utils.components import render_card, render_quadrant_chart, render_tile_filter, auto_table_height
from utils.styles import fmt_rp_full as FMT_RP

_KMEANS_MIN_N = 8  # minimal subjek non-Sample Kecil sebelum clustering dianggap bermakna

_BULAN_NUM = {b: i + 1 for i, b in enumerate(list_bulan_standar)}

# Sample kecil (<_MIN_N_CUSTOMER customer assigned) dikeluarkan dari 4 kuadran — Active Ratio
# & Top-1 Concentration gampang melenceng ke 0%/100% kalau basisnya cuma 1-2 customer,
# sama seperti alasan _MIN_N_CUSTOMER di tab_productivity.py.
_MIN_N_CUSTOMER = 5
_X_THRESHOLD = 50.0  # Active Ratio (%)
_Y_THRESHOLD = 50.0  # Top-1 Concentration (%)

_ARCHETYPE_ORDER = ["Portofolio Sehat", "Whale Hunter", "Rentan Ganda", "Perlu Follow-up", "Sample Kecil"]
# Warna disamakan persis dengan warna titik di Peta Segmentasi (render_quadrant_chart) —
# supaya archetype yang sama selalu punya identitas warna yang sama di manapun dia muncul
# (card ringkasan, chart, kolom tabel). "bg" = tint tipis warna yang sama (alpha 0.15) buat
# fill sel tabel, cukup kebaca teksnya tapi gak lebur ke background gelap halaman.
_ARCHETYPE_META = {
    "Portofolio Sehat": {
        "icon": "🟢", "color": "#10b981", "bg": "rgba(16,185,129,0.15)",
        "desc": "Active Ratio tinggi, Concentration rendah — portofolio digarap merata, tidak bergantung ke 1 akun.",
    },
    "Whale Hunter": {
        "icon": "🐋", "color": "#2563eb", "bg": "rgba(37,99,235,0.15)",
        "desc": "Active Ratio tinggi, Concentration tinggi — aktif ke portofolionya, tapi revenue mayoritas dari 1 customer besar.",
    },
    "Rentan Ganda": {
        "icon": "🚨", "color": "#ef4444", "bg": "rgba(239,68,68,0.15)",
        "desc": "Active Ratio rendah, Concentration tinggi — risiko tertinggi: sedikit yang digarap DAN revenue numpuk di 1 akun.",
    },
    "Perlu Follow-up": {
        "icon": "🟡", "color": "#f59e0b", "bg": "rgba(245,158,11,0.15)",
        "desc": "Active Ratio rendah, Concentration rendah — banyak akun di-assign tapi mayoritas dibiarkan tidak digarap.",
    },
    "Sample Kecil": {
        "icon": "⚪", "color": "#94a3b8", "bg": "rgba(148,163,184,0.15)",
        "desc": f"Assigned Customer <{_MIN_N_CUSTOMER} — Active Ratio & Top-1 Concentration terlalu gampang melenceng buat diklasifikasikan andal.",
    },
}


def _style_archetype(val):
    meta = _ARCHETYPE_META.get(val)
    if not meta:
        return ""
    return f'background-color: {meta["bg"]}; color: {meta["color"]}; font-weight: bold;'


def _classify(row):
    if row["Assigned_Customers"] < _MIN_N_CUSTOMER:
        return "Sample Kecil"
    active_high = row["Active_Ratio"] >= _X_THRESHOLD
    conc_high = row["Top1_Concentration"] >= _Y_THRESHOLD
    if active_high and not conc_high:
        return "Portofolio Sehat"
    if active_high and conc_high:
        return "Whale Hunter"
    if not active_high and conc_high:
        return "Rentan Ganda"
    return "Perlu Follow-up"


def _kmeans_label_map(cluster_df, cluster_labels):
    """Peta angka cluster (0..k-1) -> nama kategori rule-based paling dominan di cluster
    itu (majority vote) — supaya hasil K-Means gampang dibaca ("mirip kategori yang mana"),
    bukan 'Cluster 0/1/2/3' yang gak ada artinya sendiri buat orang yang gak baca kode ini.
    Kalau 2 cluster kebetulan sama-sama didominasi kategori yang sama, cluster berikutnya
    dikasih suffix angka biar tetap unik.
    """
    tmp = cluster_df.copy()
    tmp["_cluster"] = cluster_labels
    used = {}
    mapping = {}
    for c in sorted(tmp["_cluster"].unique()):
        dominant = tmp[tmp["_cluster"] == c]["Archetype"].value_counts().idxmax()
        used[dominant] = used.get(dominant, 0) + 1
        mapping[c] = dominant if used[dominant] == 1 else f"{dominant} #{used[dominant]}"
    return mapping


def _run_kmeans_validation(df, n_clusters=4):
    """K-Means (k=4, disamakan jumlahnya dengan kategori rule-based) di 4 fitur yang sama
    dipakai buat klasifikasi rule-based — dijalankan sebagai ANALISIS PEMBANDING, bukan
    pengganti (lihat Penjelasan di tab ini). Kalau clustering statistik murni sepakat besar
    dengan pembagian rule-based, itu bukti pembagian 50/50 di atas memang menangkap pola
    natural di data (bukan cuma aturan sepihak). Kalau banyak beda, itu sinyal ambang/fitur
    rule-based-nya perlu ditinjau ulang.

    random_state dikunci supaya hasil clustering konsisten tiap dashboard dibuka ulang
    (K-Means punya elemen random di inisialisasi centroid) — bukan berubah-ubah acak antar
    sesi yang bikin user bingung kenapa hasilnya beda padahal datanya sama.

    Return None kalau subjek non-Sample Kecil kurang dari _KMEANS_MIN_N — clustering pada
    sample terlalu kecil gampang menyesatkan (cluster bisa cuma nangkep 1-2 outlier).
    """
    cluster_df = df[df["Archetype"] != "Sample Kecil"].copy()
    if len(cluster_df) < _KMEANS_MIN_N:
        return None

    # log-transform Jumlah Customer & Actual (keduanya right-skewed — Cabang/Salesman besar
    # bisa berkali-kali lipat yang kecil) supaya gak mendominasi jarak antar-titik dan
    # clustering-nya menangkap pola PERILAKU, bukan cuma "besar vs kecil".
    features = pd.DataFrame({
        "log_customers": np.log(cluster_df["Assigned_Customers"]),
        "log_actual": np.log1p(cluster_df["Actual"]),
        "active_ratio": cluster_df["Active_Ratio"],
        "concentration": cluster_df["Top1_Concentration"],
    })
    scaled = StandardScaler().fit_transform(features)
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = km.fit_predict(scaled)

    label_map = _kmeans_label_map(cluster_df, labels)
    cluster_df["KMeans_Label"] = [label_map[c] for c in labels]

    agreement_rate = (cluster_df["Archetype"] == cluster_df["KMeans_Label"]).mean() * 100
    crosstab = pd.crosstab(cluster_df["Archetype"], cluster_df["KMeans_Label"])
    summary = cluster_df.groupby("KMeans_Label").agg(
        Jumlah_Anggota=("KMeans_Label", "size"),
        Rata2_Customer=("Assigned_Customers", "mean"),
        Rata2_Active_Ratio=("Active_Ratio", "mean"),
        Rata2_Concentration=("Top1_Concentration", "mean"),
        Rata2_Actual=("Actual", "mean"),
    ).reset_index()

    return {"agreement_rate": agreement_rate, "crosstab": crosstab, "summary": summary, "n": len(cluster_df)}


def render(df_order_raw, df_order_final, df_supply_final, df_customer_master, pilih_tahun, pilih_bulan,
           pilih_jenis, pilih_kelas, pilih_area, pilih_cabang, fmt_rp):
    bulan_num_list = sorted(_BULAN_NUM[b] for b in pilih_bulan if b in _BULAN_NUM)
    if not bulan_num_list:
        st.info("Tidak ada Bulan yang dipilih di Filter General.")
        return

    subject = st.radio(
        "Lihat Segmentasi berdasarkan", ["Cabang", "Salesman"], horizontal=True, key="archetype_subject",
    )

    df, label_col, name_col = compute_productivity_df(
        df_order_raw, df_order_final, df_supply_final, df_customer_master,
        pilih_tahun, bulan_num_list, pilih_jenis, pilih_kelas, pilih_area, pilih_cabang, subject,
    )

    if df.empty:
        st.info("Tidak ada data untuk filter yang dipilih.")
        return

    df["Archetype"] = df.apply(_classify, axis=1)
    counts = df["Archetype"].value_counts()

    cols = st.columns(len(_ARCHETYPE_ORDER))
    for col, arch in zip(cols, _ARCHETYPE_ORDER):
        meta = _ARCHETYPE_META[arch]
        with col:
            st.markdown(
                render_card(
                    meta["icon"], arch, f"{int(counts.get(arch, 0))}", f"dari {len(df)} {subject.lower()}",
                    accent_color=meta["color"],
                ),
                unsafe_allow_html=True,
            )

    st.markdown(f"#### Peta Segmentasi — {subject}")
    n_excluded = int((df["Archetype"] == "Sample Kecil").sum())
    st.caption(
        "Sumbu X = Active Ratio (persentase customer assigned yang benar-benar ada transaksi), "
        "sumbu Y = Top-1 Concentration (persentase revenue dari 1 customer terbesar), "
        "besar bubble = Total Actual (revenue). Garis putus-putus = ambang 50%."
        + (f" {n_excluded} {subject.lower()} dengan sample kecil (<{_MIN_N_CUSTOMER} customer) tidak ditampilkan di chart ini, tapi tetap ada di tabel di bawah." if n_excluded else "")
    )

    chart_df = df[df["Archetype"] != "Sample Kecil"]

    chart_highlight = st.text_input(
        "🔍 Cari & Sorot di Peta", key="archetype_chart_highlight",
        placeholder=f"Ketik nama {subject.lower()} buat nyorot titiknya di peta di bawah...",
    )
    if chart_highlight.strip():
        n_match = int(chart_df[label_col].astype(str).str.upper().str.contains(chart_highlight.strip().upper(), na=False).sum())
        if n_match == 0:
            st.caption("Tidak ditemukan di peta — mungkin masuk kategori Sample Kecil (cek tabel di bawah), atau nama beda dari yang dicari.")
        else:
            st.caption(f"🎯 {n_match} titik disorot di peta (ring putih, sisanya dipudarkan).")

    render_quadrant_chart(
        chart_df, label_col, x_col="Active_Ratio", y_col="Top1_Concentration", size_col="Actual",
        category_col="Archetype",
        category_colors={a: _ARCHETYPE_META[a]["color"] for a in _ARCHETYPE_ORDER if a != "Sample Kecil"},
        x_title="Active Ratio (%)", y_title="Top-1 Concentration (%)", value_fmt=fmt_rp,
        key="chart_archetype_quadrant", x_threshold=_X_THRESHOLD, y_threshold=_Y_THRESHOLD,
        extra_hover_cols=[("Top1_Customer", "Top-1 Customer", lambda v: v)],
        highlight_query=chart_highlight,
    )

    st.markdown(f"#### Ranking Lengkap Segmentasi {subject}")
    archetype_options = [a for a in _ARCHETYPE_ORDER if a in df["Archetype"].unique()]
    col_filter, col_search = st.columns([1, 2])
    with col_filter:
        pilih_archetype = render_tile_filter("Filter Kategori Segmentasi", archetype_options, key="archetype_filter")
    with col_search:
        # st.checkbox (dipakai render_tile_filter buat "Pilih Semua") punya padding vertikal
        # lebih tinggi dari label teks biasa punya st.text_input — tanpa spacer ini, kotak
        # input kesannya "ngambang" lebih tinggi dari baris pills di sebelahnya.
        st.markdown('<div style="height:0.55rem"></div>', unsafe_allow_html=True)
        search_query = st.text_input(f"Cari {subject}", key="archetype_search_query", placeholder=f"Ketik nama {subject.lower()}...")

    table_source = df[df["Archetype"].isin(pilih_archetype)]
    if search_query.strip():
        q = search_query.strip().upper()
        table_source = table_source[table_source[label_col].astype(str).str.upper().str.contains(q, na=False)]

    display_cols = [name_col] + (["Cabang"] if subject == "Salesman" else []) + [
        "Assigned_Customers", "Active_Ratio", "Top1_Concentration", "Actual", "Archetype",
    ]
    display = table_source[display_cols].copy()
    display = display.rename(columns={
        name_col: subject, "Assigned_Customers": "Jumlah Customer",
        "Active_Ratio": "Active Ratio (%)", "Top1_Concentration": "Top-1 Concentration (%)",
        "Archetype": "Kategori Segmentasi",
    })

    st.dataframe(
        display.style
        .map(_style_archetype, subset=["Kategori Segmentasi"])
        .format({
            "Actual": FMT_RP, "Active Ratio (%)": "{:.1f}%", "Top-1 Concentration (%)": "{:.1f}%",
            "Jumlah Customer": "{:.0f}",
        }),
        use_container_width=True, hide_index=True,
        height=min(auto_table_height(len(display)), 600),
    )

    st.markdown("---")
    st.markdown("### Penjelasan")
    archetype_desc = "\n".join(f"  - **{_ARCHETYPE_META[a]['icon']} {a}**: {_ARCHETYPE_META[a]['desc']}" for a in _ARCHETYPE_ORDER)
    st.markdown(
        "- **Segmentasi** mengelompokkan tiap Cabang/Salesman ke satu kategori berdasarkan 2 sumbu — **Active Ratio** "
        "(seberapa besar portofolio assigned yang benar-benar digarap) dan **Top-1 Concentration** (seberapa besar "
        "ketergantungan ke 1 customer terbesar) — bukan cuma ranking linear satu angka Productivity, supaya subjek "
        "dengan strategi kerja yang beda (fokus banyak akun kecil vs fokus sedikit akun besar) tidak dibandingkan apel-ke-jeruk:\n"
        f"{archetype_desc}\n"
        "- Ambang 50%/50% dipakai sebagai titik awal — bisa disesuaikan begitu ada cukup histori buat lihat sebaran datanya.\n"
        "- **Ini segmentasi rule-based (aturan tetap), bukan hasil model statistik** — dipilih supaya kategori tiap "
        "subjek konsisten dari bulan ke bulan dan gampang dijelaskan ke siapapun. Lihat bagian **Validasi dengan "
        "K-Means** di bawah buat cek apakah pembagian ini masih mewakili pola data yang sebenarnya atau sudah bergeser."
    )

    with st.expander("🔬 Validasi dengan K-Means (Beta) — apakah kategori di atas mewakili pola data yang sebenarnya?"):
        st.caption(
            "K-Means di sini dijalankan dengan k=4 (disamakan dengan jumlah kategori rule-based di atas) pada 4 fitur "
            "yang sama — Jumlah Customer & Actual di-log-transform dulu (biar gak didominasi Cabang/Salesman besar), "
            "Active Ratio & Top-1 Concentration apa adanya — setelah distandardisasi. Subjek Sample Kecil dikecualikan, "
            "sama seperti di Peta Segmentasi. Tiap cluster hasil K-Means diberi nama = kategori rule-based paling "
            "dominan di anggotanya (majority vote), supaya hasilnya kebaca — bukan sekadar 'Cluster 0/1/2/3'."
        )

        kmeans_result = _run_kmeans_validation(df)
        if kmeans_result is None:
            st.info(f"Belum cukup data (minimal {_KMEANS_MIN_N} {subject.lower()} non-Sample Kecil) untuk menjalankan K-Means di scope filter ini.")
        else:
            st.markdown(
                render_card(
                    "🎯", "Tingkat Kesesuaian", f"{kmeans_result['agreement_rate']:.1f}%",
                    f"dari {kmeans_result['n']} {subject.lower()} — seberapa sering K-Means independen setuju dengan kategori rule-based",
                ),
                unsafe_allow_html=True,
            )

            st.markdown("##### Kategori Rule-Based vs Kategori K-Means")
            st.caption("Baris = kategori rule-based, kolom = kategori hasil K-Means. Sel diagonal (nama baris = nama kolom) berarti sepakat.")
            st.dataframe(kmeans_result["crosstab"], use_container_width=True)

            st.markdown("##### Karakteristik Rata-rata Tiap Cluster K-Means")
            summary_display = kmeans_result["summary"].rename(columns={
                "KMeans_Label": "Kategori K-Means", "Jumlah_Anggota": "Jumlah Anggota",
                "Rata2_Customer": "Rata-rata Jumlah Customer", "Rata2_Active_Ratio": "Rata-rata Active Ratio (%)",
                "Rata2_Concentration": "Rata-rata Top-1 Concentration (%)", "Rata2_Actual": "Rata-rata Actual",
            })
            st.dataframe(
                summary_display.style.format({
                    "Rata-rata Jumlah Customer": "{:.1f}", "Rata-rata Active Ratio (%)": "{:.1f}%",
                    "Rata-rata Top-1 Concentration (%)": "{:.1f}%", "Rata-rata Actual": FMT_RP,
                    "Jumlah Anggota": "{:.0f}",
                }),
                use_container_width=True, hide_index=True,
            )
