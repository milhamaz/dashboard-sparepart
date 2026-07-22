# ============================================================
# 🧩 SHARED COMPONENTS — Fungsi-fungsi yang dipakai lintas tab
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils.data_loader import list_bulan_standar


PAGE_REGISTRY = [
    ("home", "🏠 Home", "Dashboard.py"),
    ("financial", "📦 Laporan Financial", "pages/01_Laporan_Financial.py"),
    ("sdm", "👥 SDM", "pages/02_SDM.py"),
    ("customer", "🤝 Customer", "pages/03_Customer.py"),
    ("marketing", "📢 Marketing Program", "pages/04_Marketing_Program.py"),
    ("partnumber", "📊 Analisa Partnumber", "pages/05_Analisa_Partnumber.py"),
]


def render_nav_bar(current_key):
    """Tombol pindah antar page (semua page selain current) + garis pembatas tebal di
    bawahnya, ditaruh di bawah judul tiap halaman. Pengganti nav sidebar bawaan Streamlit
    yang sekarang di-collapse default supaya layout konten lebih lebar.
    """
    others = [p for p in PAGE_REGISTRY if p[0] != current_key]
    cols = st.columns(len(others))
    for col, (key, label, path) in zip(cols, others):
        with col:
            if st.button(label, use_container_width=True, key=f"nav_{current_key}_{key}"):
                st.switch_page(path)
    st.markdown('<hr class="thick-divider">', unsafe_allow_html=True)


def render_footer():
    """Caption penutup halaman (dulu di sidebar) — dipindah ke bawah konten utama
    karena sidebar filter sudah dihapus."""
    st.divider()
    st.caption("Built with Streamlit + Plotly | Updated (2026)")
    st.caption("*Data isn't actual numbers, for display purposes only*")
    st.caption("*Created by Ilham (2026)*")


def render_tile_filter(label, options, key, format_func=None, show_select_all=True):
    """Filter tile (st.pills multi-select) dengan checkbox "Pilih Semua" opsional,
    supaya user tidak perlu klik satu-satu saat pilihannya banyak (7KP, Item D, TMO,
    Chemical, TGB, T-OPT, dst).

    Sengaja TIDAK pakai st.columns untuk baris label+toggle: filter ini sering dipanggil
    dari dalam st.columns milik pemanggil (mis. layout 2-kolom di tab_topt.py). Nested
    st.columns di dalam st.columns tidak selalu render proporsional — kolom sempit bisa
    bikin tombol/label overflow ke kolom tetangga. Checkbox tunggal (tanpa split kolom)
    menghindari masalah itu sepenuhnya, apapun lebar kolom pemanggilnya.

    Otomatis reset ke "semua terpilih" setiap kali daftar `options` berubah (mis. ganti
    Tahun/Bulan di sidebar) — tanpa ini Streamlit mempertahankan seleksi lama di
    session_state yang sudah tidak valid untuk daftar baru, sehingga filter tampak
    kosong dan tab tidak menampilkan data sama sekali saat dibuka.

    Uncheck "Pilih Semua" mengosongkan seleksi (bukan mempertahankan semua-terpilih) —
    supaya pilih 1-2 item dari opsi yang banyak (mis. cuma Cabang Jakarta dari 40+ cabang)
    tinggal uncheck lalu klik yang diinginkan, bukan uncheck satu-satu item yang tidak
    diinginkan. Pengosongan cuma terjadi SEKALI di momen transisi checked→unchecked
    (dilacak lewat `{key}_selectall_prev`), supaya klik pill berikutnya oleh user tidak
    ke-reset lagi di rerun selanjutnya selama checkbox tetap unchecked.

    show_select_all=False menyembunyikan checkbox-nya (mis. filter dengan opsi sedikit
    yang tidak butuh shortcut pilih-semua).
    """
    sig_key = f"{key}_sig"
    cb_key = f"{key}_selectall"
    prev_cb_key = f"{key}_selectall_prev"
    options_sig = tuple(options)
    if st.session_state.get(sig_key) != options_sig:
        st.session_state[key] = options
        if show_select_all:
            st.session_state[cb_key] = True
            st.session_state[prev_cb_key] = True
        st.session_state[sig_key] = options_sig

    if show_select_all:
        all_selected = st.checkbox(f"**{label}** — Pilih Semua", value=True, key=cb_key)
        was_selected = st.session_state.get(prev_cb_key, True)
        if all_selected:
            st.session_state[key] = options  # set sebelum st.pills() di bawah dibuat
        elif was_selected and not all_selected:
            st.session_state[key] = []  # transisi checked->unchecked: kosongkan sekali
        st.session_state[prev_cb_key] = all_selected
    else:
        st.markdown(f"**{label}**")

    kwargs = {"format_func": format_func} if format_func else {}
    return st.pills(label, options, selection_mode="multi", key=key, label_visibility="collapsed", **kwargs)


def render_top_cabang_heatmap(df, value_col, group_col="Cabang", month_col="Bulan", top_n=7, key="heatmap"):
    """Heatmap top-N Cabang berdasar `value_col`, dengan sel diwarnai growth MoM
    (dipakai di tab 7KP).
    """
    if group_col not in df.columns or df.empty:
        st.info("Tidak ada data untuk heatmap.")
        return

    top_names = df.groupby(group_col)[value_col].sum().nlargest(top_n).index.tolist()
    df_top = df[df[group_col].isin(top_names)]

    hp = df_top.groupby([group_col, month_col])[value_col].sum().reset_index()
    hp_pivot = hp.pivot_table(index=group_col, columns=month_col, values=value_col, aggfunc="sum").fillna(0)
    h_cols = [b for b in list_bulan_standar if b in hp_pivot.columns]
    hp_pivot = hp_pivot[h_cols]
    hp_pivot = hp_pivot.loc[hp_pivot.sum(axis=1).sort_values(ascending=False).index]

    names = hp_pivot.index.tolist()
    n_r, n_c = len(names), len(h_cols)
    if n_r == 0 or n_c == 0:
        st.info("Tidak ada data untuk heatmap.")
        return

    growth_z = np.full((n_r, n_c), 0.0)
    hover_texts = []
    for i, name in enumerate(names):
        row_hover = []
        for j, bln in enumerate(h_cols):
            val = hp_pivot.loc[name, bln]
            bln_idx = list_bulan_standar.index(bln) if bln in list_bulan_standar else -1
            prev_val = None
            if bln_idx > 0:
                prev_bln = list_bulan_standar[bln_idx - 1]
                if prev_bln in hp_pivot.columns:
                    prev_val = hp_pivot.loc[name, prev_bln]

            if prev_val is not None and prev_val > 0:
                mom = ((val / prev_val) - 1) * 100
            elif prev_val == 0 and val > 0:
                mom = 100.0
            else:
                mom = 0.0

            growth_z[i, j] = 0.0 if bln.lower() == "januari" else mom

            val_rp_full = f"Rp {val:,.0f}".replace(",", ".")
            mom_str = f"MoM: {'▲' if mom >= 0 else '▼'}{mom:+.1f}%" if bln.lower() != "januari" else "MoM: — (Awal Tahun)"
            row_hover.append(f"<b>{name}</b> — {bln}<br>{val_rp_full}<br>{mom_str}")
        hover_texts.append(row_hover)

    growth_clamped = np.clip(growth_z, -50, 50)

    fig = go.Figure(data=go.Heatmap(
        z=growth_clamped, x=h_cols, y=names,
        colorscale=[[0, "#0c1a3a"], [0.3, "#1e3a6e"], [0.5, "#2563eb"], [0.7, "#60a5fa"], [1, "#bfdbfe"]],
        zmid=0, showscale=False,
        hovertext=hover_texts,
        hovertemplate="%{hovertext}<extra></extra>",
    ))

    for i, name in enumerate(names):
        for j, bln in enumerate(h_cols):
            val = hp_pivot.loc[name, bln]
            g = growth_z[i, j]

            val_color = "#0f172a" if g > 20 else "#f1f5f9"
            val_disp = f"{val / 1_000:,.0f}".replace(",", ".")
            fig.add_annotation(
                x=bln, y=name, text=val_disp, showarrow=False,
                font=dict(size=13, color=val_color, family="monospace"),
                yshift=8,
            )

            if bln.lower() != "januari":
                arrow = "▲" if g >= 0 else "▼"
                if g > 20:
                    g_color = "#047857" if g >= 0 else "#b91c1c"
                else:
                    g_color = "#34d399" if g >= 0 else "#f87171"
                fig.add_annotation(
                    x=bln, y=name, text=f"{arrow}{g:+.0f}%", showarrow=False,
                    font=dict(size=9, color=g_color), yshift=-10,
                )

    fig.update_layout(
        height=70 + (n_r * 58),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(color="white", size=12), side="top"),
        yaxis=dict(tickfont=dict(color="white", size=12), autorange="reversed"),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    fig.add_annotation(
        text="<i>dalam Jutaan <br> x1000</i>", showarrow=False,
        xref="paper", yref="paper", x=-0.04, y=1.075,
        font=dict(size=10, color="#94a3b8"),
        xanchor="left",
    )

    st.plotly_chart(fig, use_container_width=True, key=key)
    st.markdown(
        '<p style="font-size:10px; color:#64748b; margin-top:-10px;">'
        'Gelap = turun dari bulan sebelumnya &nbsp;&nbsp; Terang = naik dari bulan sebelumnya &nbsp;&nbsp; Januari = baseline tahun berjalan</p>',
        unsafe_allow_html=True)


# Urutan hue kategorikal tetap (fixed order, gak di-cycle acak) — dipetakan ke kategori
# terurut besar->kecil tiap render, konsisten dengan konvensi "assign categorical hues in
# fixed order" dari skill dataviz.
_CATEGORICAL_HUES = ["#3987e5", "#008300", "#d55181", "#c98500", "#199e70", "#d95926", "#9085e9", "#e66767"]


def _lighten_hex(hex_color, factor):
    """Blend warna hex ke arah putih sebesar `factor` (0=asli, 1=putih penuh) — dipakai
    buat kasih anak node treemap tint lebih terang dari warna induknya, bukan hue baru."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def _interp_colorscale_rgb(colorscale, t):
    """Interpolasi RGB linear dari colorscale Plotly (list [posisi 0-1, hex]) di posisi
    `t` (0-1) — dipakai buat tau warna PERSIS yang bakal dirender di suatu titik z,
    supaya kontras teks bisa dihitung dari warna asli, bukan cuma nebak lewat threshold."""
    t = max(0.0, min(1.0, t))
    for (p0, c0), (p1, c1) in zip(colorscale[:-1], colorscale[1:]):
        if p0 <= t <= p1:
            ratio = (t - p0) / (p1 - p0) if p1 > p0 else 0.0
            c0, c1 = c0.lstrip("#"), c1.lstrip("#")
            r0, g0, b0 = int(c0[0:2], 16), int(c0[2:4], 16), int(c0[4:6], 16)
            r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
            return r0 + (r1 - r0) * ratio, g0 + (g1 - g0) * ratio, b0 + (b1 - b0) * ratio
    c = colorscale[-1][1].lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _contrast_ink(r, g, b, dark="#1c1006", light="#fff7ed"):
    """Pilih teks gelap/terang berdasar luminance PERSEPSI dari warna background (r,g,b) —
    dinamis mengikuti warna asli, bukan nebak dari posisi/threshold nilai data."""
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return dark if luminance > 150 else light


def render_category_cabang_treemap(df, category_col, value_col, group_col="Cabang", top_n=5, key="treemap"):
    """Treemap 2 level: kategori (root) -> Top-N Cabang kontributor + "Lainnya" (sisa
    Cabang di luar Top-N, insight Pareto — seberapa terkonsentrasi kontribusi tiap
    kategori ke segelintir Cabang). Warna kategori pakai hue kategorikal tetap (urutan
    besar->kecil), anak node cuma tint lebih terang dari induknya (bukan hue terpisah,
    karena Cabang di sini bukan identitas mandiri, cuma breakdown magnitude 1 kategori).

    Return: dict {kategori: pct_top_n} — %kontribusi Top-N terhadap total kategori itu,
    dipakai pemanggil buat kalimat insight Pareto ringkas.
    """
    if category_col not in df.columns or group_col not in df.columns or df.empty:
        st.info("Tidak ada data untuk treemap.")
        return {}

    kategori_totals = df.groupby(category_col)[value_col].sum().sort_values(ascending=False)
    kategori_list = kategori_totals.index.tolist()
    if not kategori_list:
        st.info("Tidak ada data untuk treemap.")
        return {}

    kategori_color = {kat: _CATEGORICAL_HUES[i % len(_CATEGORICAL_HUES)] for i, kat in enumerate(kategori_list)}

    ids, labels, parents, values, colors, hover = [], [], [], [], [], []
    pct_top_n = {}

    for kat in kategori_list:
        total = kategori_totals[kat]
        ids.append(kat)
        labels.append(kat)
        parents.append("")
        values.append(total)
        colors.append(kategori_color[kat])
        hover.append(f"<b>{kat}</b><br>Total: Rp {total:,.0f}".replace(",", "."))

        cabang_totals = df[df[category_col] == kat].groupby(group_col)[value_col].sum().sort_values(ascending=False)
        top = cabang_totals.head(top_n)
        rest = cabang_totals.iloc[top_n:].sum()
        pct_top_n[kat] = (top.sum() / total * 100) if total > 0 else 0.0

        child_color = _lighten_hex(kategori_color[kat], 0.45)
        for cabang, val in top.items():
            pct = (val / total * 100) if total > 0 else 0.0
            ids.append(f"{kat}::{cabang}")
            labels.append(cabang)
            parents.append(kat)
            values.append(val)
            colors.append(child_color)
            hover.append(f"<b>{cabang}</b> — {kat}<br>Rp {val:,.0f}".replace(",", ".") + f"<br>{pct:.1f}% dari {kat}")

        if rest > 0:
            sisa_n = max(len(cabang_totals) - top_n, 0)
            pct_rest = (rest / total * 100) if total > 0 else 0.0
            ids.append(f"{kat}::Lainnya")
            labels.append("Lainnya")
            parents.append(kat)
            values.append(rest)
            colors.append(_lighten_hex(kategori_color[kat], 0.75))
            hover.append(f"<b>Lainnya</b> ({sisa_n} Cabang) — {kat}<br>Rp {rest:,.0f}".replace(",", ".") + f"<br>{pct_rest:.1f}% dari {kat}")

    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues="total",
        marker=dict(colors=colors, line=dict(width=2, color="#0e1117")),
        textfont=dict(color="#0f172a", size=13),
        hovertext=hover, hovertemplate="%{hovertext}<extra></extra>",
    ))
    fig.update_layout(
        height=480,
        margin=dict(l=4, r=4, t=10, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, key=key)
    return pct_top_n


def render_burn_rate_heatmap(df, revenue_col="Revenue", burn_col="Burn", group_col="Cabang", month_col="Bulan", top_n=7, key="heatmap"):
    """Heatmap top-N Cabang (ranking berdasar total `revenue_col`). Angka besar di tiap
    sel = Revenue (informasi utama, sama seperti render_top_cabang_heatmap), dengan Burn
    Rate (%) = burn_col/revenue_col ditampilkan sebagai keterangan kecil di bawahnya.

    Warna sel = gradasi oranye tunggal berdasar BESARAN Burn Rate (bukan growth MoM
    hijau/merah seperti render_top_cabang_heatmap()). Karena bukan metrik growth, tidak
    ada bulan yang perlu dikunci ke warna netral (termasuk Januari, yang di versi growth
    butuh baseline bulan sebelumnya).
    """
    if group_col not in df.columns or df.empty:
        st.info("Tidak ada data untuk heatmap.")
        return

    top_names = df.groupby(group_col)[revenue_col].sum().nlargest(top_n).index.tolist()
    df_top = df[df[group_col].isin(top_names)]

    agg = df_top.groupby([group_col, month_col])[[revenue_col, burn_col]].sum().reset_index()
    agg["Burn_Rate"] = (agg[burn_col] / agg[revenue_col] * 100).fillna(0).replace([np.inf, -np.inf], 0)

    rev_pivot = agg.pivot_table(index=group_col, columns=month_col, values=revenue_col, aggfunc="sum").fillna(0)
    rate_pivot = agg.pivot_table(index=group_col, columns=month_col, values="Burn_Rate", aggfunc="sum").fillna(0)

    h_cols = [b for b in list_bulan_standar if b in rev_pivot.columns]
    rev_pivot, rate_pivot = rev_pivot[h_cols], rate_pivot[h_cols]

    order_idx = [c for c in df_top.groupby(group_col)[revenue_col].sum().sort_values(ascending=False).index if c in rev_pivot.index]
    rev_pivot, rate_pivot = rev_pivot.loc[order_idx], rate_pivot.loc[order_idx]

    names = rev_pivot.index.tolist()
    n_r, n_c = len(names), len(h_cols)
    if n_r == 0 or n_c == 0:
        st.info("Tidak ada data untuk heatmap.")
        return

    z_clamped = np.clip(rate_pivot.values, 0, 100)
    BURN_COLORSCALE = [[0, "#3a2410"], [0.3, "#7c4a12"], [0.5, "#c2691a"], [0.7, "#f59e0b"], [1, "#fde68a"]]
    BURN_RATE_THRESHOLD = 3  # % — sama ambang dipakai highlight_burn_rate_pct di utils/styles.py

    hover_texts = []
    for name in names:
        row_hover = []
        for bln in h_cols:
            rev_str = f"Rp {rev_pivot.loc[name, bln]:,.0f}".replace(",", ".")
            rate = rate_pivot.loc[name, bln]
            row_hover.append(f"<b>{name}</b> — {bln}<br>{rev_str}<br>Burn Rate: {rate:.1f}%")
        hover_texts.append(row_hover)

    # zmin/zmax eksplisit — tanpa ini Plotly auto-scale warna ke rentang MIN-MAX data asli
    # (bukan 0-100 kayak diasumsikan kode di bawah), bikin warna sel gak konsisten antar
    # render kalau rentang Burn Rate aktualnya sempit (mis. semua di bawah 10%).
    fig = go.Figure(data=go.Heatmap(
        z=z_clamped, x=h_cols, y=names, zmin=0, zmax=100,
        colorscale=BURN_COLORSCALE,
        showscale=False,
        hovertext=hover_texts,
        hovertemplate="%{hovertext}<extra></extra>",
    ))

    for i, name in enumerate(names):
        for j, bln in enumerate(h_cols):
            rate = rate_pivot.loc[name, bln]
            # Kontras teks dihitung dari warna BACKGROUND ASLI di titik ini (bukan nebak
            # dari threshold rate), jadi selalu kebaca walau warnanya oren pekat atau
            # nyaris putih di ujung skala.
            r, g, b = _interp_colorscale_rgb(BURN_COLORSCALE, rate / 100)
            val_color = _contrast_ink(r, g, b)

            rev_disp = f"{rev_pivot.loc[name, bln] / 1_000:,.0f}".replace(",", ".")
            fig.add_annotation(
                x=bln, y=name, text=rev_disp, showarrow=False,
                font=dict(size=13, color=val_color, family="monospace"),
                yshift=8,
            )
            # Subtitle Burn Rate% dikasih warna semantik (bukan cuma kontras) — hijau kalau
            # masih di bawah ambang 3%, merah kalau lewat, konsisten sama highlight tabel.
            burn_text_color = "#ef4444" if rate > BURN_RATE_THRESHOLD else "#10b981"
            fig.add_annotation(
                x=bln, y=name, text=f"Burn {rate:.1f}%", showarrow=False,
                font=dict(size=9, color=burn_text_color), yshift=-10,
            )

    fig.update_layout(
        height=70 + (n_r * 58),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(color="white", size=12), side="top"),
        yaxis=dict(tickfont=dict(color="white", size=12), autorange="reversed"),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    fig.add_annotation(
        text="<i>dalam Jutaan <br> x1000</i>", showarrow=False,
        xref="paper", yref="paper", x=-0.04, y=1.075,
        font=dict(size=10, color="#94a3b8"),
        xanchor="left",
    )

    st.plotly_chart(fig, use_container_width=True, key=key)
    st.markdown(
        '<p style="font-size:10px; color:#64748b; margin-top:-10px;">'
        'Angka besar = Revenue Item D, warna sel = besaran Burn Rate (semakin terang/pekat oranye '
        f'semakin tinggi) &nbsp;&nbsp; Teks Burn Rate: <span style="color:#10b981">hijau</span> ≤{BURN_RATE_THRESHOLD}%, '
        '<span style="color:#ef4444">merah</span> di atas itu.</p>',
        unsafe_allow_html=True)


def cleanup_selection(key, valid_options):
    """Intersect seleksi yang sudah ada di session_state[key] dengan `valid_options`
    yang baru (cross-filter dari filter LAIN bisa mempersempit opsi kapan saja).
    Cuma menulis balik ke session_state kalau memang ada perubahan (`valid != current`)
    — penting supaya tidak memicu efek berantai/rerun yang tidak perlu. Kalau hasil
    intersect-nya kosong, itu tetap valid (artinya "semua", bukan error).
    """
    current = st.session_state.get(key, [])
    valid = [v for v in current if v in valid_options]
    if valid != current:
        st.session_state[key] = valid
    return valid


@st.cache_data(show_spinner=False)
def build_pivot(data, subj_col, time_col, time_order, value_col, aggfunc, sort_mode="total_desc"):
    """Pivot 2 dimensi dengan margin TOTAL baris & kolom, kolom di-reindex ke seluruh
    `time_order` (kuartal/bulan yang belum ada datanya tetap tampil dengan nilai 0).

    pandas pivot_table(margins=True) menghitung margin dengan menjalankan ulang
    `aggfunc` pada subset data mentah yang bersangkutan — BUKAN menjumlahkan nilai sel
    yang sudah teragregasi. Ini krusial untuk Kelebaran (aggfunc="nunique"): TOTAL harus
    berupa unique count dari gabungan datanya (partnumber bisa overlap antar
    Area/Cabang/Salesman/Customer atau periode), bukan hasil sum dari nunique per
    baris/kolom. Sudah diverifikasi lewat percobaan manual sebelum dipakai di sini.

    sort_mode="alpha" mengurutkan baris A-Z (Cabang/Salesman/Customer_No). Selain itu
    default "total_desc" mengurutkan berdasar nilai TOTAL menurun (dipakai Area).
    """
    full_cols = time_order + ["TOTAL"]
    d = data.dropna(subset=[subj_col, time_col, value_col])
    if d.empty:
        return pd.DataFrame(0, index=["TOTAL"], columns=full_cols)

    pivot = pd.pivot_table(
        d, index=subj_col, columns=time_col, values=value_col,
        aggfunc=aggfunc, margins=True, margins_name="TOTAL", fill_value=0,
    )
    pivot = pivot.reindex(columns=full_cols, fill_value=0)
    subject_rows = pivot.drop(index="TOTAL")
    if sort_mode == "alpha":
        row_order = sorted(subject_rows.index.tolist()) + ["TOTAL"]
    else:
        row_order = subject_rows["TOTAL"].sort_values(ascending=False).index.tolist() + ["TOTAL"]
    pivot = pivot.loc[row_order]
    return pivot


@st.cache_data(show_spinner=False)
def classify_claim_goodwill(df_supply):
    """Split df_supply jadi df_claim & df_goodwill berdasar Qty minus & pola Invoice_No.

    Claim = retur karena defect/cacat (Qty < 0, Invoice_No TIDAK mengandung "G-RJUL").
    Goodwill = retur defect ringan yang tetap masuk inventory cabang (Qty < 0, Invoice_No
    mengandung "G-RJUL"). Value Rupiah pakai kolom Actual yang sudah ada (Qty×Retail_Price/1.11
    dari data_loader.py), di-abs() karena Qty aslinya minus untuk baris retur.
    """
    invoice_upper = df_supply["Invoice_No"].astype(str).str.upper()
    is_return = df_supply["Qty"] < 0
    is_goodwill = is_return & invoice_upper.str.contains("G-RJUL", na=False)
    is_claim = is_return & ~invoice_upper.str.contains("G-RJUL", na=False)

    df_claim = df_supply[is_claim].copy()
    df_claim["Claim_Value"] = df_claim["Actual"].abs()

    df_goodwill = df_supply[is_goodwill].copy()
    df_goodwill["Goodwill_Qty"] = df_goodwill["Qty"].abs()
    df_goodwill["Goodwill_Value"] = df_goodwill["Actual"].abs()

    return df_claim, df_goodwill


@st.cache_data(show_spinner=False)
def compute_customer_yoy(df_supply_final, pilih_tahun):
    """Bandingkan Actual per Customer_No antara pilih_tahun vs pilih_tahun-1, dipakai bareng
    oleh tab Retention/Churn & Alert Penurunan di page Customer.

    `df_supply_final` sudah termasuk 2 tahun (current + LY) — bawaan dari render_top_filters()
    (utils/filters.py) — dan sudah difilter Bulan/Area/Cabang/Jenis/Kelas dari Filter General,
    jadi retention di sini otomatis ikut scope bulan yang dipilih (mis. kalau user cuma pilih
    Q1, perbandingannya jadi "Q1 tahun ini vs Q1 tahun lalu", bukan setahun penuh).

    Return DataFrame per Customer_No dengan kolom Customer_Name, Cabang, Last_Year, This_Year,
    Pct_Change, dan Status (Churned/New/Retained) — Pct_Change/Status dihitung dari Last_Year
    vs This_Year, bukan revenue absolut, jadi konsisten dipakai untuk kedua tab.
    """
    cols = ["Customer_No", "Customer_Name", "Cabang", "Last_Year", "This_Year", "Pct_Change", "Status"]
    if df_supply_final is None or df_supply_final.empty:
        return pd.DataFrame(columns=cols)

    df = df_supply_final.copy()
    df["Customer_No"] = df["Customer_No"].astype(str).str.upper().str.strip()
    df["Customer_Name"] = df["Customer_Name"].astype(str).str.strip().str.upper()

    agg = df.groupby(["Customer_No", "Tahun"])["Actual"].sum().reset_index()
    pivot = agg.pivot(index="Customer_No", columns="Tahun", values="Actual").fillna(0)
    pivot = pivot.rename(columns={pilih_tahun - 1: "Last_Year", pilih_tahun: "This_Year"})
    for col in ("Last_Year", "This_Year"):
        if col not in pivot.columns:
            pivot[col] = 0.0
    pivot = pivot[["Last_Year", "This_Year"]].reset_index()

    lookup = df.drop_duplicates("Customer_No")[["Customer_No", "Customer_Name", "Cabang"]]
    result = pivot.merge(lookup, on="Customer_No", how="left")

    result["Pct_Change"] = np.where(
        result["Last_Year"] > 0,
        (result["This_Year"] - result["Last_Year"]) / result["Last_Year"] * 100,
        np.where(result["This_Year"] > 0, 100.0, 0.0),
    )
    result["Status"] = np.select(
        [
            (result["Last_Year"] > 0) & (result["This_Year"] <= 0),
            (result["Last_Year"] <= 0) & (result["This_Year"] > 0),
            (result["Last_Year"] > 0) & (result["This_Year"] > 0),
        ],
        ["Churned", "New", "Retained"],
        default="Tidak Aktif",
    )
    return result[cols]


@st.cache_data(show_spinner=False)
def compute_reactivation_candidates(df_customer_master, df_supply_raw, pilih_jenis, pilih_kelas,
                                     pilih_area, pilih_cabang, reference_date, grace_period_days=365):
    """Cari customer berstatus AKTIF di master (Customer.xlsx) tapi sudah `grace_period_days`
    (default 365 = 12 bulan) tanpa transaksi Supply sama sekali, dihitung dari transaksi
    TERAKHIR (`Last_Transaction`) sampai `reference_date` — beda dari 'Churned' di tab Retention
    yang kalender-tahun-based, ini murni rolling window dari tanggal transaksi terakhir.

    `reference_date` WAJIB dioper eksplisit oleh pemanggil (bukan pd.Timestamp.now() dipanggil
    di dalam sini) — fungsi ini di-cache, dan st.cache_data cuma nge-invalidate kalau ARGUMENNYA
    berubah. Kalau "sekarang" dipanggil di dalam fungsi yang di-cache, hasil dormant/tidaknya
    customer bakal kebeku di tanggal cache pertama kali diisi sampai file data berubah — bisa
    telat ngedeteksi customer yang baru lewat 12 bulan kalau kebetulan gak ada perubahan data
    sama sekali di hari itu. Pemanggil cukup oper `pd.Timestamp.now().normalize()` — itu otomatis
    beda tiap hari kalender, jadi cache-nya refresh sendiri harian tanpa perlu di-clear manual.

    `df_supply_raw` sengaja data MENTAH (semua tahun yang ke-load, TANPA filter Bulan/Tahun) —
    grace period ini gak terikat scope Tahun di Filter General, karena "sudah berapa lama sejak
    transaksi terakhir" itu pertanyaan yang gak ada hubungannya sama Tahun mana yang lagi dipilih.
    """
    cols = ["Kode_Customer", "Nama_Customer", "Cabang", "Jenis_Customer", "Kelas_Customer", "Last_Transaction"]
    if df_customer_master is None or df_customer_master.empty:
        return pd.DataFrame(columns=cols)

    scope = df_customer_master[
        (df_customer_master["Status"] == "AKTIF")
        & df_customer_master["Jenis_Customer"].isin(pilih_jenis)
        & df_customer_master["Kelas_Customer"].isin(pilih_kelas)
        & df_customer_master["Kode_Area"].isin(pilih_area)
        & df_customer_master["Cabang"].isin(pilih_cabang)
    ].copy()
    if scope.empty:
        return pd.DataFrame(columns=cols)

    if df_supply_raw is not None and not df_supply_raw.empty:
        raw = df_supply_raw.copy()
        raw["Customer_No"] = raw["Customer_No"].astype(str).str.upper().str.strip()
        last_trans = raw.groupby("Customer_No")["Invoice_Date"].max()
        scope["Last_Transaction"] = scope["Kode_Customer"].map(last_trans)
    else:
        scope["Last_Transaction"] = pd.NaT

    is_dormant = scope["Last_Transaction"].isna() | (
        (reference_date - scope["Last_Transaction"]).dt.days >= grace_period_days
    )
    candidates = scope[is_dormant].copy()
    if candidates.empty:
        return pd.DataFrame(columns=cols)

    candidates = candidates.sort_values("Last_Transaction", ascending=False, na_position="last")
    return candidates[cols]


@st.cache_data(show_spinner=False)
def compute_odom_status(df_order_final, df_kalkerja, pilih_tahun, pilih_bulan, ambang_bulanan=30_000_000, ambang_hari_aktif=50.0):
    """ODOM (One Million One Day) — customer sehat kalau Order-nya rutin ≥Rp1 juta/hari
    (~Rp30 juta/bulan). Basisnya ORDER (bukan Actual/Supply), dan scope Bulan/Tahun ikut
    Filter General (kalau user pilih beberapa Bulan sekaligus, ambang bulanan & Hari Kerja
    ikut dikali/dijumlah sesuai jumlah Bulan yang dipilih, bukan cuma 1 bulan).

    Status:
      - Belum ODOM: total Order di scope ini < ambang bulanan (dikali jumlah Bulan dipilih).
      - ODOM Bolong-bolong: lolos ambang total, tapi hari aktifnya (hari ada Order >0)
        kurang dari `ambang_hari_aktif`% dibanding Hari Kerja di scope ini — order numpuk
        di sedikit hari, bukan rutin harian.
      - ODOM Lancar: lolos ambang total DAN hari aktifnya cukup tersebar.
    """
    cols = ["Customer_No", "Customer_Name", "Cabang", "Total_Order", "Hari_Aktif", "Hari_Kerja", "Rasio_Aktif", "Status"]
    if df_order_final is None or df_order_final.empty:
        return pd.DataFrame(columns=cols)

    df = df_order_final.copy()
    df["Customer_No"] = df["Customer_No"].astype(str).str.upper().str.strip()
    df["Customer_Name"] = df["Customer_Name"].astype(str).str.strip().str.upper()
    df["Tanggal"] = df["SO_Date"].dt.date

    total_order = df.groupby("Customer_No")["Order"].sum()
    # Hari Aktif cuma dihitung dari baris yang Order-nya beneran positif — baris retur/qty 0
    # (ada meski kecil jumlahnya di data) gak boleh ikut dianggap "hari order" sungguhan,
    # soalnya bisa nge-gelembungin Rasio_Aktif customer yang order-nya jarang tapi punya
    # beberapa baris retur tersebar di banyak tanggal.
    hari_aktif = df[df["Order"] > 0].groupby("Customer_No")["Tanggal"].nunique()
    lookup = df.drop_duplicates("Customer_No")[["Customer_No", "Customer_Name", "Cabang"]]

    hari_kerja_scope = df_kalkerja[(df_kalkerja["Tahun"] == pilih_tahun) & (df_kalkerja["Bulan"].isin(pilih_bulan))]
    hari_kerja_total = hari_kerja_scope["Hari_Kerja"].sum()
    n_bulan = len(pilih_bulan) if pilih_bulan else 1

    result = lookup.copy()
    result["Total_Order"] = result["Customer_No"].map(total_order).fillna(0)
    result["Hari_Aktif"] = result["Customer_No"].map(hari_aktif).fillna(0).astype(int)
    result["Hari_Kerja"] = hari_kerja_total
    result["Rasio_Aktif"] = np.where(hari_kerja_total > 0, result["Hari_Aktif"] / hari_kerja_total * 100, 0.0)

    ambang_total = ambang_bulanan * n_bulan
    result["Status"] = np.select(
        [
            result["Total_Order"] < ambang_total,
            result["Rasio_Aktif"] < ambang_hari_aktif,
        ],
        ["Belum ODOM", "ODOM Bolong-bolong"],
        default="ODOM Lancar",
    )
    return result[cols]


def render_topn_barh_chart(df, label_col, value_col, top_n, color, value_fmt, xaxis_title, key, extra_hover_cols=None):
    """Horizontal bar chart Top-N (mis. Top 10 Salesman/Cabang berdasar 1 metrik), sorted
    menurun. Pola sama dipakai di beberapa tempat (dulu ditulis langsung di tab_gebyur.py
    buat Top 7 Cabang) — diekstrak ke sini supaya Salesman Leaderboard & Cabang Scorecard
    bisa pakai chart yang konsisten tanpa duplikasi.

    `extra_hover_cols` opsional: list of (kolom, label, formatter) yang ditambahkan sebagai
    baris tambahan di tooltip hover saja (mis. %Kontribusi Nasional/Cabang di Salesman
    Leaderboard) — tidak mengubah teks yang tampil permanen di atas bar.
    """
    top = df.nlargest(top_n, value_col)
    if top.empty:
        st.info("Tidak ada data untuk chart.")
        return

    def _hovertext(row):
        lines = [f"<b>{row[label_col]}</b>", value_fmt(row[value_col])]
        if extra_hover_cols:
            lines += [f"{label}: {fmt(row[col])}" for col, label, fmt in extra_hover_cols]
        return "<br>".join(lines)

    fig = go.Figure(go.Bar(
        x=top[value_col], y=top[label_col], orientation="h",
        marker_color=color,
        text=[value_fmt(v) for v in top[value_col]],
        textposition="auto",
        textfont=dict(color="#f8fafc", size=13),
        hovertext=[_hovertext(row) for _, row in top.iterrows()],
        hovertemplate="%{hovertext}<extra></extra>",
    ))
    fig.update_layout(
        height=70 + (len(top) * 48),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title=dict(text=xaxis_title, font=dict(color="white", size=14)), tickfont=dict(color="white", size=12), gridcolor="#333333"),
        yaxis=dict(tickfont=dict(color="white", size=13), autorange="reversed"),
        margin=dict(l=10, r=30, t=20, b=10),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def render_bidirectional_barh_chart(df, label_col, left_col, right_col, left_name, right_name,
                                     left_color, right_color, value_fmt, key,
                                     xaxis_title=None, left_hover_extra=None, right_hover_extra=None,
                                     left_value_label=None, right_value_label=None,
                                     bar_text_size=12, label_size=12, axis_title_size=14, legend_size=13,
                                     gap_ratio=0.16):
    """Bar chart horizontal 2 arah dari titik tengah 0 — 1 metrik ke kiri (mis. Order), metrik
    lain ke kanan (mis. Actual), berbagi 1 sumbu magnitude yang sama (dicerminkan, bukan
    dual-axis) supaya 2 metrik per kategori langsung kebandingin panjang bar-nya. `df` sudah
    harus dalam urutan tampil yang diinginkan (mis. hasil nlargest) — fungsi ini tidak
    mengurutkan ulang.

    `left_value_label`/`right_value_label` opsional — kalau diisi, baris ke-2 hover jadi
    "{label}: {value}" (mis. "Pencapaian O/T: 105.3%") alih-alih cuma angka polos tanpa
    keterangan. Default None mempertahankan perilaku lama (dipakai tab_salesman_leaderboard.py).

    `bar_text_size`/`label_size`/`axis_title_size`/`legend_size` opsional — default =
    ukuran lama (12/12/14/13), tapi bisa disetel per-pemanggil (mis. Target Customer di
    layar lebar). Sengaja pakai default agar tab lain yang belum oper argumen ini
    (Salesman Leaderboard, Komposisi Growth) tetap persis seperti semula.

    `gap_ratio` opsional (default 0.16) — lebar ruang kosong di tengah (tempat nama kategori
    ditaruh di antara 2 bar), sebagai proporsi dari nilai bar terbesar. Dinaikin kalau nama
    kategori panjang butuh lebih banyak ruang biar gak numpuk ke bar-nya (mis. nama Customer).
    """
    if df.empty:
        st.info("Tidak ada data untuk chart.")
        return

    raw_max = max(df[left_col].max(), df[right_col].max())
    raw_max = raw_max if raw_max > 0 else 1.0
    # Gap kosong di tengah (sekitar sumbu 0) — bukan buat spacing kosmetik, tapi reserved
    # space biar nama kategori (mis. Salesman) bisa ditaruh di tengah row, di antara 2 bar,
    # alih-alih numpuk di y-axis kiri seperti bar chart 1 arah biasa.
    gap = raw_max * gap_ratio
    outer_max = raw_max * 1.15 + gap

    def _hovertext(row, col, extra_cols, value_label):
        main_line = f"{value_label}: {value_fmt(row[col])}" if value_label else value_fmt(row[col])
        lines = [f"<b>{row[label_col]}</b>", main_line]
        if extra_cols:
            lines += [f"{label}: {fmt(row[c])}" for c, label, fmt in extra_cols]
        return "<br>".join(lines)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=-df[left_col], y=df[label_col], base=-gap, orientation="h", name=left_name,
        marker_color=left_color,
        text=[value_fmt(v) for v in df[left_col]],
        textposition="auto", textfont=dict(color="#f8fafc", size=bar_text_size),
        hovertext=[_hovertext(row, left_col, left_hover_extra, left_value_label) for _, row in df.iterrows()],
        hovertemplate="%{hovertext}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=df[right_col], y=df[label_col], base=gap, orientation="h", name=right_name,
        marker_color=right_color,
        text=[value_fmt(v) for v in df[right_col]],
        textposition="auto", textfont=dict(color="#f8fafc", size=bar_text_size),
        hovertext=[_hovertext(row, right_col, right_hover_extra, right_value_label) for _, row in df.iterrows()],
        hovertemplate="%{hovertext}<extra></extra>",
    ))

    for _, row in df.iterrows():
        fig.add_annotation(
            x=0, y=row[label_col], xref="x", yref="y", xanchor="center", yanchor="middle",
            text=f"<b>{row[label_col]}</b>", showarrow=False,
            font=dict(color="#f8fafc", size=label_size),
        )

    fig.update_layout(
        barmode="overlay",
        height=70 + (len(df) * 48),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title=dict(text=xaxis_title, font=dict(color="white", size=axis_title_size)) if xaxis_title else None,
            showticklabels=False, showgrid=False, zeroline=False,
            range=[-outer_max, outer_max],
        ),
        yaxis=dict(showticklabels=False, autorange="reversed"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="white", size=legend_size)),
        hoverlabel=dict(bgcolor="#1e293b", font_color="white", font_size=13),
        margin=dict(l=10, r=30, t=50, b=10),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def render_bubble_chart(df, label_col, x_col, y_col, size_col, risk_col, x_title, y_title,
                         value_fmt, risk_threshold=50, key="bubble", extra_hover_cols=None):
    """Scatter/bubble chart — posisi (x,y) + ukuran bubble (magnitude ke-3) + warna status
    (risiko, 2 kategori tetap: merah kalau `risk_col` >= `risk_threshold`, biru kalau tidak).
    Dipakai tab Productivity: x=Jumlah Customer, y=Productivity/Customer, size=Total Revenue,
    warna=Concentration Risk — biar pengelompokan alami ("pemburu paus" vs "penyebar rata")
    kelihatan tanpa perlu clustering statistik beneran.

    Sengaja TANPA label teks permanen di tiap titik (banyak subjek = numpuk/gak kebaca) —
    identitas tiap titik cuma lewat hover, sesuai kaidah "jangan angka di tiap titik".

    `extra_hover_cols` opsional: list of (kolom, label, formatter) yang ditambahkan sebagai
    baris tambahan di tooltip hover — pola sama dengan render_topn_barh_chart (mis. nama
    customer di balik Top-1 Concentration, biar gak cuma keliatan angka %-nya doang).
    """
    if df.empty:
        st.info("Tidak ada data untuk chart.")
        return

    is_risk = df[risk_col] >= risk_threshold
    colors = np.where(is_risk, "#ef4444", "#2563eb")

    max_size = df[size_col].max()
    size_ref = (2.0 * max_size / (55.0 ** 2)) if max_size > 0 else 1.0

    def _hover_row(row):
        lines = [
            f"<b>{row[label_col]}</b>",
            f"{x_title}: {row[x_col]:,.0f}".replace(",", "."),
            f"{y_title}: {value_fmt(row[y_col])}",
            f"Total: {value_fmt(row[size_col])}",
            f"Top-1 Concentration: {row[risk_col]:.1f}%",
        ]
        if extra_hover_cols:
            lines += [f"{label}: {fmt(row[col])}" for col, label, fmt in extra_hover_cols]
        return "<br>".join(lines)

    hover_text = [_hover_row(row) for _, row in df.iterrows()]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x_col], y=df[y_col], mode="markers",
        marker=dict(
            size=df[size_col], sizemode="area", sizeref=size_ref, sizemin=4,
            color=colors, line=dict(width=1, color="#0e1117"), opacity=0.85,
        ),
        hovertext=hover_text, hovertemplate="%{hovertext}<extra></extra>",
        showlegend=False,
    ))
    # Trace kosong cuma buat munculin legend warna (marker size asli di atas gak dikasih
    # legend karena showlegend=False — kalau diaktifkan, legend-nya ikut2an gede sesuai
    # ukuran bubble rata-rata, bukan swatch kecil biasa).
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, color="#2563eb"), name="Normal", showlegend=True))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, color="#ef4444"), name=f"Concentration Risk (≥{risk_threshold:.0f}%)", showlegend=True))

    fig.update_layout(
        height=520,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title=dict(text=x_title, font=dict(color="white", size=14)), tickfont=dict(color="white", size=12), gridcolor="#333333"),
        yaxis=dict(title=dict(text=y_title, font=dict(color="white", size=14)), tickfont=dict(color="white", size=12), gridcolor="#333333"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="white", size=12)),
        hoverlabel=dict(bgcolor="#1e293b", font_color="white", font_size=13),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def _hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def render_quadrant_chart(df, label_col, x_col, y_col, size_col, category_col, category_colors,
                           x_title, y_title, value_fmt, key, x_threshold=50, y_threshold=50,
                           extra_hover_cols=None, highlight_query=None):
    """Scatter kuadran: posisi (x,y) dibagi 4 area oleh garis putus-putus di x_threshold/
    y_threshold, warna titik = kategori (`category_col`, lookup `category_colors`), ukuran
    bubble = magnitude ke-3 (`size_col`). Beda dari render_bubble_chart yang cuma binary
    risk (2 warna tetap) — di sini kategori bisa lebih dari 2, dipakai buat segmentasi/
    archetype rule-based (mis. tab Segmentasi Productivity).

    Satu trace per kategori (bukan 1 trace + warna manual) supaya legend otomatis
    menunjukkan nama archetype-nya, bukan swatch generik yang perlu trace kosong tambahan
    kayak render_bubble_chart.

    `highlight_query` opsional — kalau diisi, titik yang label-nya (`label_col`) cocok
    (substring, case-insensitive) tetap solid + dikasih ring putih tebal, sisanya
    di-fade ke alpha rendah (WARNA kategori-nya tetap, cuma pudar) supaya titik yang
    dicari tetap gampang ditemukan di tengah bubble lain. Opacity per-titik di-encode
    langsung di string rgba() marker.color (bukan marker.opacity array) karena
    marker.opacity per-titik gak konsisten didukung di semua versi Plotly untuk
    Scatter 2D — rgba() alpha channel jauh lebih pasti kerja.
    """
    if df.empty:
        st.info("Tidak ada data untuk chart.")
        return

    max_size = df[size_col].max()
    size_ref = (2.0 * max_size / (55.0 ** 2)) if max_size > 0 else 1.0
    query = highlight_query.strip().upper() if highlight_query else ""

    def _hover_row(row):
        lines = [
            f"<b>{row[label_col]}</b>",
            f"{row[category_col]}",
            f"{x_title}: {row[x_col]:.1f}",
            f"{y_title}: {row[y_col]:.1f}",
            f"Total: {value_fmt(row[size_col])}",
        ]
        if extra_hover_cols:
            lines += [f"{label}: {fmt(row[col])}" for col, label, fmt in extra_hover_cols]
        return "<br>".join(lines)

    fig = go.Figure()
    for cat, color in category_colors.items():
        sub = df[df[category_col] == cat]
        if sub.empty:
            continue
        hover_text = [_hover_row(row) for _, row in sub.iterrows()]
        if query:
            is_match = sub[label_col].astype(str).str.upper().str.contains(query, na=False)
            marker_colors = [color if m else _hex_to_rgba(color, 0.12) for m in is_match]
            line_widths = [3 if m else 1 for m in is_match]
            line_colors = ["#ffffff" if m else "#0e1117" for m in is_match]
            trace_opacity = 1.0
        else:
            marker_colors = color
            line_widths = 1
            line_colors = "#0e1117"
            trace_opacity = 0.85
        fig.add_trace(go.Scatter(
            x=sub[x_col], y=sub[y_col], mode="markers", name=cat,
            marker=dict(
                size=sub[size_col], sizemode="area", sizeref=size_ref, sizemin=4,
                color=marker_colors, line=dict(width=line_widths, color=line_colors), opacity=trace_opacity,
            ),
            hovertext=hover_text, hovertemplate="%{hovertext}<extra></extra>",
            showlegend=True,
        ))

    fig.add_vline(x=x_threshold, line_dash="dash", line_color="#64748b", opacity=0.6)
    fig.add_hline(y=y_threshold, line_dash="dash", line_color="#64748b", opacity=0.6)

    fig.update_layout(
        height=520,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title=dict(text=x_title, font=dict(color="white", size=14)), tickfont=dict(color="white", size=12), gridcolor="#333333"),
        yaxis=dict(title=dict(text=y_title, font=dict(color="white", size=14)), tickfont=dict(color="white", size=12), gridcolor="#333333"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="white", size=12)),
        hoverlabel=dict(bgcolor="#1e293b", font_color="white", font_size=13),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def render_waterfall_chart(labels, values, measures, value_fmt, key, yaxis_title=None):
    """Waterfall chart generik — jembatan dari 1 titik awal ke titik akhir lewat serangkaian
    kontribusi naik/turun (mis. YoY: Last Year -> +Retained -> +New -> -Churned -> =This Year).

    `measures` ikutin semantik native Plotly Waterfall: "absolute" (bar penuh dari 0, titik
    awal), "relative" (kontribusi naik/turun, ditumpuk dari running total sebelumnya oleh
    Plotly), "total" (bar penuh dari 0 lagi, titik akhir/subtotal — value HARUS dihitung
    sendiri oleh pemanggil, Plotly tidak auto-sum untuk measure ini).
    """
    text = [value_fmt(v) for v in values]
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=labels, y=values,
        text=text, textposition="outside",
        textfont=dict(color="#f8fafc", size=13),
        connector=dict(line=dict(color="#475569", width=1, dash="dot")),
        increasing=dict(marker=dict(color="#10b981")),
        decreasing=dict(marker=dict(color="#ef4444")),
        totals=dict(marker=dict(color="#2563eb")),
        hovertext=[f"<b>{l}</b><br>{value_fmt(v)}" for l, v in zip(labels, values)],
        hovertemplate="%{hovertext}<extra></extra>",
    ))
    fig.update_layout(
        height=480,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(
            title=dict(text=yaxis_title, font=dict(color="white", size=14)) if yaxis_title else None,
            tickfont=dict(color="white", size=12), gridcolor="#333333",
        ),
        xaxis=dict(tickfont=dict(color="white", size=13)),
        showlegend=False,
        margin=dict(l=10, r=10, t=30, b=10),
        hoverlabel=dict(bgcolor="#1e293b", font_color="white", font_size=13),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def render_qty_heatmap(df, value_col, group_col="Cabang", month_col="Bulan", key="heatmap"):
    """Heatmap SEMUA Cabang (tidak dibatasi top-N) untuk 1 metrik Qty, pakai skema warna
    oranye single-hue yang sama seperti render_burn_rate_heatmap — biar konsisten secara
    visual dengan heatmap Burn Rate Item D, meski di sini cuma 1 angka Qty per sel (tidak
    ada konsep "burn rate").
    """
    if group_col not in df.columns or df.empty:
        st.info("Tidak ada data untuk heatmap.")
        return

    agg = df.groupby([group_col, month_col])[value_col].sum().reset_index()
    pivot = agg.pivot_table(index=group_col, columns=month_col, values=value_col, aggfunc="sum").fillna(0)

    h_cols = [b for b in list_bulan_standar if b in pivot.columns]
    pivot = pivot[h_cols]

    order_idx = df.groupby(group_col)[value_col].sum().sort_values(ascending=False).index.tolist()
    order_idx = [c for c in order_idx if c in pivot.index]
    pivot = pivot.loc[order_idx]

    names = pivot.index.tolist()
    n_r, n_c = len(names), len(h_cols)
    if n_r == 0 or n_c == 0:
        st.info("Tidak ada data untuk heatmap.")
        return

    max_val = pivot.values.max() or 1

    hover_texts = []
    for name in names:
        row_hover = []
        for bln in h_cols:
            val = pivot.loc[name, bln]
            qty_str = f"{val:,.0f}".replace(",", ".")
            row_hover.append(f"<b>{name}</b> — {bln}<br>Qty: {qty_str}")
        hover_texts.append(row_hover)

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=h_cols, y=names, zmin=0, zmax=max_val,
        colorscale=[[0, "#3a2410"], [0.3, "#7c4a12"], [0.5, "#c2691a"], [0.7, "#f59e0b"], [1, "#fde68a"]],
        showscale=False,
        hovertext=hover_texts,
        hovertemplate="%{hovertext}<extra></extra>",
    ))

    for i, name in enumerate(names):
        for j, bln in enumerate(h_cols):
            val = pivot.loc[name, bln]
            intensity_pct = (val / max_val * 100) if max_val else 0
            val_color = "#1c1006" if intensity_pct > 50 else "#fff7ed"
            val_disp = f"{val:,.0f}".replace(",", ".")
            fig.add_annotation(
                x=bln, y=name, text=val_disp, showarrow=False,
                font=dict(size=12, color=val_color, family="monospace"),
            )

    fig.update_layout(
        height=70 + (n_r * 42),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(color="white", size=12), side="top"),
        yaxis=dict(tickfont=dict(color="white", size=12), autorange="reversed"),
        margin=dict(l=10, r=10, t=30, b=10),
    )

    st.plotly_chart(fig, use_container_width=True, key=key)
    st.markdown(
        '<p style="font-size:10px; color:#64748b; margin-top:-10px;">'
        'Warna sel = intensitas Qty relatif terhadap cabang/bulan lain (semakin terang/pekat oranye = semakin tinggi).</p>',
        unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def compute_item_d_burn(df_order, df_dprog_lookup):
    """Match Order rows ke program Item D (PnoDProg) berdasar Partnumber + tanggal jatuh
    dalam StartDate-EndDate program, lalu hitung Revenue & Burn per baris.

    Dipakai bareng oleh tab Item D (progress program) dan tab Gebyur (budget linkage 1%)
    — sebelumnya logic ini duplikat persis di kedua file, jadi diekstrak ke sini biar
    rumus Burn cuma perlu diubah di satu tempat kalau nanti berubah.
    """
    if df_dprog_lookup is None or df_dprog_lookup.empty or "Partnumber" not in df_dprog_lookup.columns:
        return pd.DataFrame()
    if "Partnumber" not in df_order.columns or "SO_Date" not in df_order.columns:
        return pd.DataFrame()

    dprog_pnos = set(df_dprog_lookup["Partnumber"].unique())
    df_candidates = df_order[df_order["Partnumber"].isin(dprog_pnos)].copy()
    if df_candidates.empty:
        return pd.DataFrame()

    df_matched = pd.merge(df_candidates, df_dprog_lookup, on="Partnumber", how="inner")
    df_matched = df_matched[
        (df_matched["SO_Date"] >= df_matched["StartDate"]) &
        (df_matched["SO_Date"] <= df_matched["EndDate"])
    ].copy()
    if df_matched.empty:
        return df_matched

    df_matched["Revenue"] = df_matched["Order"]
    df_matched["Burn"] = np.where(
        df_matched["Scp_Disc"] != 0,
        df_matched["Qty"] * df_matched["Retail_Price"] * df_matched["Scp_Disc"] / 100,
        0,
    )
    df_matched["Is_Discounted"] = df_matched["Scp_Disc"] != 0
    return df_matched


@st.cache_data(show_spinner=False)
def merge_lookup_triplet(df_order_final, df_supply_final, df_lookup, lookup_cols, pilih_tahun):
    """Merge Order (tahun berjalan) & Supply (tahun ini + tahun lalu) dengan 1 lookup master
    berdasar Partnumber — pola yang dipakai bareng oleh tab TMO/Chemical/TGB/T-OPT, sebelumnya
    ditulis ulang 3x di tiap file dengan cuma beda nama variabel.

    Return (df_ord, df_sup, df_ly) — masing-masing DataFrame kosong kalau kolom Partnumber
    tidak ada di sisi order/supply.
    """
    lookup = df_lookup[lookup_cols]

    df_ord = pd.merge(df_order_final, lookup, on="Partnumber", how="inner") if "Partnumber" in df_order_final.columns else pd.DataFrame()

    if "Partnumber" in df_supply_final.columns:
        df_sup = pd.merge(df_supply_final[df_supply_final["Tahun"] == pilih_tahun], lookup, on="Partnumber", how="inner")
        df_ly = pd.merge(df_supply_final[df_supply_final["Tahun"] == pilih_tahun - 1], lookup, on="Partnumber", how="inner")
    else:
        df_sup, df_ly = pd.DataFrame(), pd.DataFrame()

    return df_ord, df_sup, df_ly


@st.cache_data(show_spinner=False)
def aggregate_monthly(df, value_col, out_col=None):
    """Groupby Bulan_Num/Bulan, sum `value_col`, di-rename ke `out_col` kalau beda nama.
    Aman untuk df kosong (return DataFrame kosong dengan kolom yang tetap konsisten)."""
    out_col = out_col or value_col
    if df.empty:
        return pd.DataFrame(columns=["Bulan_Num", "Bulan", out_col])
    result = df.groupby(["Bulan_Num", "Bulan"])[value_col].sum().reset_index()
    if out_col != value_col:
        result = result.rename(columns={value_col: out_col})
    return result


def render_trend_cards(m_ly, m_ord, m_sup, pilih_tahun, card_titles, fmt_card):
    """Render 4 card standar (Order, Supply, Last Year, Growth) dari hasil aggregate_monthly().

    m_ly/m_ord/m_sup: masing2 punya kolom value "Last_Year"/"Order"/"Actual".
    card_titles: dict {"order","supply","ly","growth"} buat title tiap card.
    Return (total_order, total_supply, total_ly) biar tab pemanggil bisa pakai buat
    card tambahan (mis. split SO Campaign di TMO) tanpa hitung ulang.
    """
    total_order = m_ord["Order"].sum() if not m_ord.empty else 0
    total_supply = m_sup["Actual"].sum() if not m_sup.empty else 0
    total_ly = m_ly["Last_Year"].sum() if not m_ly.empty else 0
    growth = hitung_growth(total_supply, total_ly)
    avg_order = hitung_avg(total_order, m_ord, "Order")
    avg_supply = hitung_avg(total_supply, m_sup, "Actual")

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(render_card("", card_titles["order"], fmt_card(total_order), f"Avg: {fmt_card(avg_order)}/bln"), unsafe_allow_html=True)
    with c2: st.markdown(render_card("", card_titles["supply"], fmt_card(total_supply), f"Avg: {fmt_card(avg_supply)}/bln"), unsafe_allow_html=True)
    with c3: st.markdown(render_card("", card_titles["ly"], fmt_card(total_ly), f"Tahun {pilih_tahun - 1}"), unsafe_allow_html=True)
    with c4: st.markdown(render_growth_card("", card_titles.get("growth", "Growth"), growth, f"Supply vs {pilih_tahun - 1}"), unsafe_allow_html=True)

    return total_order, total_supply, total_ly


def render_trend_chart_and_table(m_ly, m_ord, m_sup, pilih_tahun, pilih_bulan, hover_fmt, text_fmt, yaxis_title, detail_labels, highlight_pct, text_size=14):
    """Render bar chart 3-series (LY/Order/Supply) + expander detail tabel bulanan dengan
    A/LY% — pola yang sama dipakai TMO/Chemical/TGB/T-OPT, cuma beda label & formatter.

    detail_labels perlu key: expander_title, ly, order, supply, cell_fmt, no_data.
    """
    ly_vals = [m_ly[m_ly["Bulan"] == b]["Last_Year"].values[0] if len(m_ly[m_ly["Bulan"] == b]) else 0 for b in pilih_bulan]
    ord_vals = [m_ord[m_ord["Bulan"] == b]["Order"].values[0] if len(m_ord[m_ord["Bulan"] == b]) else 0 for b in pilih_bulan]
    sup_vals = [m_sup[m_sup["Bulan"] == b]["Actual"].values[0] if len(m_sup[m_sup["Bulan"] == b]) else 0 for b in pilih_bulan]

    fig = render_bar_chart(
        pilih_bulan,
        [
            {"values": ly_vals, "name": f"Last Year ({pilih_tahun - 1})", "color": "#e11d48", "hover_fmt": hover_fmt, "text_fmt": text_fmt, "text_size": text_size},
            {"values": ord_vals, "name": "Order", "color": "#2563eb", "hover_fmt": hover_fmt, "text_fmt": text_fmt, "text_size": text_size},
            {"values": sup_vals, "name": "Supply", "color": "#10b981", "hover_fmt": hover_fmt, "text_fmt": text_fmt, "text_size": text_size},
        ],
        yaxis_title=yaxis_title, height=580,
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander(detail_labels.get("expander_title", "Detail Data")):
        if not m_ord.empty or not m_sup.empty or not m_ly.empty:
            detail = m_ly.merge(m_ord, on=["Bulan_Num", "Bulan"], how="outer").merge(m_sup, on=["Bulan_Num", "Bulan"], how="outer").fillna(0)
            detail["Bulan_Num"] = detail["Bulan_Num"].astype(int)
            detail = detail[detail["Bulan"].isin(pilih_bulan)].sort_values("Bulan_Num")
            detail = trim_future_months(detail, data_cols=["Order", "Actual"])
            detail["A/LY (%)"] = detail.apply(lambda row: hitung_aly(row["Actual"], row["Last_Year"]), axis=1)

            display = detail.drop(columns=["Bulan_Num"]).rename(columns={
                "Last_Year": detail_labels["ly"], "Order": detail_labels["order"], "Actual": detail_labels["supply"],
            })

            ly_sum = display[detail_labels["ly"]].sum()
            ord_sum = display[detail_labels["order"]].sum()
            sup_sum = display[detail_labels["supply"]].sum()
            display = append_total_row(display, {
                "Bulan": "TOTAL",
                detail_labels["ly"]: ly_sum,
                detail_labels["order"]: ord_sum,
                detail_labels["supply"]: sup_sum,
                "A/LY (%)": hitung_aly(sup_sum, ly_sum),
            })

            cell_fmt = detail_labels["cell_fmt"]
            render_styled_table(
                display, highlight_pct, pct_cols=["A/LY (%)"],
                fmt_dict={detail_labels["ly"]: cell_fmt, detail_labels["order"]: cell_fmt, detail_labels["supply"]: cell_fmt, "A/LY (%)": "{:.2f}%"},
                has_total_row=True,
            )
        else:
            st.info(detail_labels.get("no_data", "Tidak ada data untuk filter yang dipilih."))


def render_value_breakdown(df, value_col, key_prefix, fmt_cell=None, subj_options=None):
    """Breakdown 1 value_col (Volume/Order/Qty/Profit) per Cabang/Customer/Salesman, dalam
    SATU pivot table yang bisa switch dimensi + search box (mode Customer/Salesman).

    `df` harus dataframe yang sudah difilter kategori/jenis oleh tab pemanggil, dan minimal
    punya kolom: Cabang, Bulan, Bulan_Num, plus Customer_No/Customer_Name (mode
    Customer) atau Salesman_Name (mode Salesman) sesuai subj_options yang dipakai.
    fmt_cell: formatter angka di sel tabel (default ribuan biasa, bisa diisi fmt_rp/fmt_liter dst).
    subj_options: daftar dimensi yang bisa dipilih (default ["Cabang", "Customer"]).

    Tidak ada filter Area di sini (sengaja dihapus) — Area sudah bisa difilter dari Filter
    General di atas tab, jadi tidak perlu duplikat kontrolnya di tiap breakdown.
    """
    if df is None or df.empty:
        st.info("Tidak ada data untuk breakdown.")
        return

    fmt_cell = fmt_cell or (lambda x: f"{x:,.0f}".replace(",", "."))
    subj_options = subj_options or ["Cabang", "Customer"]

    col1, col2 = st.columns(2)
    with col1:
        subj_dim = st.selectbox("Breakdown per", subj_options, key=f"breakdown_dim_{key_prefix}")

    df_scope = df

    if subj_dim == "Cabang":
        subj_col = "Cabang"
    elif subj_dim == "Material Group":
        subj_col = "Mat_Group"
    elif subj_dim == "Salesman":
        df_scope = df_scope.copy()
        df_scope["Salesman_Label"] = df_scope["Salesman_Name"].astype(str).str.strip().str.upper()
        subj_col = "Salesman_Label"
        with col2:
            search_kw = st.text_input("Cari Salesman", key=f"breakdown_search_{key_prefix}")
        if search_kw.strip():
            df_scope = df_scope[df_scope[subj_col].str.contains(search_kw.strip(), case=False, na=False)]
    else:
        df_scope = df_scope.copy()
        df_scope["Customer_Label"] = df_scope["Customer_No"].astype(str) + " - " + df_scope["Customer_Name"].astype(str).str.strip().str.upper()
        subj_col = "Customer_Label"
        with col2:
            search_kw = st.text_input("Cari Customer (nama/kode)", key=f"breakdown_search_{key_prefix}")
        if search_kw.strip():
            df_scope = df_scope[df_scope[subj_col].str.contains(search_kw.strip(), case=False, na=False)]

    if df_scope.empty:
        st.info("Tidak ada data untuk kombinasi filter/pencarian ini.")
        return

    pivot = build_pivot(df_scope, subj_col, "Bulan", list_bulan_standar, value_col, "sum")
    styled = pivot.style.format(fmt_cell).set_properties(
        **{'text-align': 'right', 'font-size': '13px'}
    ).set_properties(
        subset=pd.IndexSlice[:, "TOTAL"], **{'font-weight': 'bold', 'background-color': 'rgba(245, 158, 11, 0.08)'}
    ).set_properties(
        subset=pd.IndexSlice["TOTAL", :], **TOTAL_ROW_STYLE
    )
    st.dataframe(styled, use_container_width=True, height=min(auto_table_height(len(pivot)), 600))


def validate_lookup(df, required_cols, file_label):
    """Cek data master lookup sudah siap (tidak kosong & semua kolom wajib ada).

    Dipakai di awal render() tiap tab sebelum merge ke df_order/df_supply, supaya
    kolom master yang hilang/berubah nama menampilkan st.warning yang jelas alih-alih
    KeyError mentah saat proses merge/filter.
    """
    if df is None or df.empty:
        st.warning(f"Data master {file_label} belum siap atau kosong.")
        return False
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.warning(
            f"{file_label}: kolom {missing} tidak ditemukan. "
            f"Kolom yang terdeteksi: {df.columns.tolist()}"
        )
        return False
    return True


def render_bar_chart(x, bars, yaxis_title, height=580):
    """Bangun grouped bar chart standar dashboard (dipakai di semua tab).

    x: list kategori sumbu-x (nama bulan).
    bars: list of dict, tiap dict menerima key:
        values    : list nilai y (wajib)
        name      : label legend & hover (wajib)
        color     : warna marker (wajib)
        hover_fmt : callable(v) -> str, dipakai sebagai customdata pada hover
                    (opsional; kalau tidak diisi pakai mode `hover_unit`)
        hover_unit: suffix string untuk hover sederhana tanpa customdata,
                    mis. " Pcs" atau " L" (opsional, default "")
        text_fmt  : callable(v) -> str untuk label di atas bar
                    (opsional, default format ribuan biasa)
        text_size : ukuran font label di atas bar (opsional, default 14)
    """
    fig = go.Figure()
    for b in bars:
        values = b["values"]
        text_fmt = b.get("text_fmt", lambda v: f"{v:,.0f}".replace(",", "."))
        trace_kwargs = dict(
            x=x, y=values, name=b["name"], marker_color=b["color"],
            text=[text_fmt(v) for v in values],
            textposition="outside", textangle=-90,
            textfont=dict(size=b.get("text_size", 14), color="#ffffff"),
        )
        hover_fmt = b.get("hover_fmt")
        if hover_fmt:
            trace_kwargs["customdata"] = [hover_fmt(v) for v in values]
            trace_kwargs["hovertemplate"] = (
                f"<b>%{{x}}:</b><br>%{{customdata}}<br><extra><b>{b['name']}</b></extra>"
            )
        else:
            unit = b.get("hover_unit", "")
            trace_kwargs["hovertemplate"] = (
                f"<b>%{{x}}:</b><br>%{{y:,.0f}}{unit}<br><extra><b>{b['name']}</b></extra>"
            )
        fig.add_trace(go.Bar(**trace_kwargs))

    fig.update_layout(
        barmode="group", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=height, separators=",.",
        yaxis=dict(title=dict(text=yaxis_title, font=dict(color="white", size=17)), tickfont=dict(color="white", size=15), gridcolor="#333333"),
        xaxis=dict(tickfont=dict(color="white", size=15), categoryorder="array", categoryarray=list_bulan_standar),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, font=dict(color="white", size=15)),
        hoverlabel=dict(bgcolor="#1e293b", font_color="white", font_size=13),
    )
    return fig


TOTAL_ROW_STYLE = {
    'font-weight': 'bold',
    'background-color': 'rgba(245, 158, 11, 0.15)',
    'border-top': '2px solid #f59e0b',
}


def append_total_row(display_df, totals):
    """Tambahkan baris TOTAL di akhir tabel detail bulanan.

    `totals` adalah dict {nama_kolom: nilai} untuk baris TOTAL — kolom yang tidak
    disebutkan otomatis kosong (NaN), dirender blank lewat na_rep di render_styled_table.
    """
    total_row = {col: totals.get(col) for col in display_df.columns}
    return pd.concat([display_df, pd.DataFrame([total_row])], ignore_index=True)


def trim_future_months(detail_df, data_cols, month_col="Bulan_Num"):
    """Buang baris bulan yang berada SETELAH bulan terakhir yang punya data (!= 0)
    di salah satu `data_cols`.

    Dipakai supaya bulan yang belum terjadi di tahun berjalan (mis. pilih tahun 2026
    yang baru sampai Juni) tidak ikut tampil kosong — bulan-bulan itu biasanya muncul
    karena outer-merge dengan Last Year yang datanya sudah penuh 12 bulan. Kalau tidak
    ada satupun bulan dengan data, dataframe dikembalikan apa adanya (fallback ke pesan
    "tidak ada data" di tab tetap jalan seperti biasa).
    """
    has_data = (detail_df[data_cols] != 0).any(axis=1)
    if not has_data.any():
        return detail_df
    cutoff = detail_df.loc[has_data, month_col].max()
    return detail_df[detail_df[month_col] <= cutoff]


def auto_table_height(n_rows, row_px=35, header_px=38, padding=3):
    """Hitung tinggi st.dataframe supaya semua baris (termasuk TOTAL) tampil penuh
    tanpa perlu scroll saat expander dibuka, dan tanpa sisa ruang kosong di bawahnya
    ketika baris lebih sedikit (mis. filter bulan cuma Jan-Jun).
    """
    return header_px + row_px * n_rows + padding


def render_styled_table(display_df, highlight_pct, pct_cols, fmt_dict, height=None, has_total_row=False):
    """Render tabel detail dengan styling highlight_pct + format kolom standar.

    has_total_row=True menyorot baris terakhir seperti baris TOTAL di tab_7kp.py
    (bold, background amber, border atas) — pakai bareng append_total_row().

    height=None (default) menghitung tinggi otomatis dari jumlah baris lewat
    auto_table_height(), supaya baris TOTAL selalu terlihat penuh tanpa scroll.
    """
    styled = display_df.style.map(highlight_pct, subset=pct_cols).format(fmt_dict, na_rep="")
    if has_total_row and len(display_df):
        styled = styled.set_properties(subset=pd.IndexSlice[display_df.index[-1:], :], **TOTAL_ROW_STYLE)
    if height is None:
        height = auto_table_height(len(display_df))
    st.dataframe(styled, hide_index=True, use_container_width=True, height=height)


def hitung_growth(actual, last_year):
    """Hitung persentase growth (perubahan YoY).
    Contoh: actual=107, last_year=100 → return +7.0
    """
    if last_year == 0 and actual > 0:
        return 100.0
    if last_year == 0:
        return 0.0
    return ((actual / last_year) - 1) * 100


def hitung_aly(actual, last_year):
    """Hitung persentase pencapaian A/LY (Actual vs Last Year).
    Contoh: actual=107, last_year=100 → return 107.0
    """
    if last_year == 0 and actual > 0:
        return 100.0
    if last_year == 0:
        return 0.0
    return (actual / last_year) * 100


def hitung_avg(total, monthly_df, col_name):
    """Hitung rata-rata hanya dari bulan yang punya nilai > 0."""
    pembagi = (monthly_df[col_name] > 0).sum() if not monthly_df.empty else 0
    return (total / pembagi) if pembagi > 0 else 0


def scope_label_cabang(pilih_cabang, all_cabang_list):
    """Tag [NASIONAL]/[nama Cabang] buat judul card yang scope-nya ikut Filter General:
    semua opsi Cabang dipilih -> "NASIONAL", cuma 1 Cabang dipilih -> nama Cabang itu
    (uppercase), 2+ tapi bukan semua -> None (tag disembunyikan, ambigu buat ditampilkan)."""
    if not all_cabang_list or set(pilih_cabang) >= set(all_cabang_list):
        return "NASIONAL"
    if len(pilih_cabang) == 1:
        return str(pilih_cabang[0]).upper()
    return None


def scope_label_periode(pilih_bulan, all_bulan_list, pilih_tahun):
    """Tag [Tahun]/[nama Bulan] buat judul card: semua opsi Bulan dipilih -> Tahun terpilih,
    cuma 1 Bulan dipilih -> nama Bulan itu (uppercase), 2+ tapi bukan semua -> None (skip)."""
    if not all_bulan_list or set(pilih_bulan) >= set(all_bulan_list):
        return str(pilih_tahun)
    if len(pilih_bulan) == 1:
        return str(pilih_bulan[0]).upper()
    return None


def build_scope_title(base_title, pilih_cabang, all_cabang_list, pilih_bulan, all_bulan_list, pilih_tahun):
    """Gabung title dasar dengan tag Cabang/Periode sesuai scope Filter General yang lagi
    aktif (tanpa tanda kurung, cuma dipisah spasi). Tag yang None (2+ dipilih tapi bukan
    semua opsi) otomatis diskip, bukan ikut nampilin 'None' di judul."""
    tags = [t for t in (
        scope_label_cabang(pilih_cabang, all_cabang_list),
        scope_label_periode(pilih_bulan, all_bulan_list, pilih_tahun),
    ) if t]
    return f"{base_title} {' '.join(tags)}" if tags else base_title


def render_card(icon, title, value, sub, accent_color=None, compact=False):
    """Return HTML string untuk metric card standar. `icon` boleh string kosong ""
    (card tanpa ikon) — tidak menyisakan spasi nyasar di depan title.

    `accent_color` opsional (hex, mis. "#10b981") — kasih strip warna di kiri card +
    warna title/sub ikut accent itu (bukan amber default di CSS class), dipakai buat
    card yang perlu dibedakan visual per kategori (mis. archetype Segmentasi). Default
    None = tampilan lama persis, gak ada perubahan buat card lain yang sudah ada.

    `compact=True` mengecilkan font value (24px -> 19px lewat class .card-compact di
    styles.py) — buat tab dengan value berupa teks/nama panjang yang di layar lebar terasa
    terlalu dominan (mis. Target Customer). Default False = tampilan lama.
    """
    card_title = f"{icon} {title}" if icon else title
    card_class = "custom-card card-compact" if compact else "custom-card"
    card_style = f' style="border-left: 4px solid {accent_color};"' if accent_color else ""
    text_style = f' style="color:{accent_color};"' if accent_color else ""
    return (
        f'<div class="{card_class}"{card_style}>'
        f'<div class="card-title"{text_style}>{card_title}</div>'
        f'<div class="card-value">{value}</div>'
        f'<div class="card-sub"{text_style}>{sub}</div>'
        f'</div>'
    )


def render_growth_card(icon, title, growth, sub):
    """Return HTML string untuk growth card dengan warna otomatis. `icon` boleh
    string kosong "" (card tanpa ikon)."""
    color = "#10b981" if growth >= 0 else "#ef4444"
    arrow = "▲" if growth >= 0 else "▼"
    card_title = f"{icon} {title}" if icon else title
    return (
        f'<div class="custom-card">'
        f'<div class="card-title">{card_title}</div>'
        f'<div class="card-value" style="color:{color}">{arrow} {growth:+.1f}%</div>'
        f'<div class="card-sub">{sub}</div>'
        f'</div>'
    )