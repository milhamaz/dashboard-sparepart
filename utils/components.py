# ============================================================
# 🧩 SHARED COMPONENTS — Fungsi-fungsi yang dipakai lintas tab
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils.data_loader import list_bulan_standar


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

    show_select_all=False menyembunyikan checkbox-nya (mis. filter dengan opsi sedikit
    yang tidak butuh shortcut pilih-semua).
    """
    sig_key = f"{key}_sig"
    cb_key = f"{key}_selectall"
    options_sig = tuple(options)
    if st.session_state.get(sig_key) != options_sig:
        st.session_state[key] = options
        if show_select_all:
            st.session_state[cb_key] = True
        st.session_state[sig_key] = options_sig

    if show_select_all:
        all_selected = st.checkbox(f"**{label}** — Pilih Semua", value=True, key=cb_key)
        if all_selected:
            st.session_state[key] = options  # set sebelum st.pills() di bawah dibuat
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

    hover_texts = []
    for name in names:
        row_hover = []
        for bln in h_cols:
            rev_str = f"Rp {rev_pivot.loc[name, bln]:,.0f}".replace(",", ".")
            rate = rate_pivot.loc[name, bln]
            row_hover.append(f"<b>{name}</b> — {bln}<br>{rev_str}<br>Burn Rate: {rate:.1f}%")
        hover_texts.append(row_hover)

    fig = go.Figure(data=go.Heatmap(
        z=z_clamped, x=h_cols, y=names,
        colorscale=[[0, "#3a2410"], [0.3, "#7c4a12"], [0.5, "#c2691a"], [0.7, "#f59e0b"], [1, "#fde68a"]],
        showscale=False,
        hovertext=hover_texts,
        hovertemplate="%{hovertext}<extra></extra>",
    ))

    for i, name in enumerate(names):
        for j, bln in enumerate(h_cols):
            rate = rate_pivot.loc[name, bln]
            val_color = "#1c1006" if rate > 50 else "#fff7ed"

            rev_disp = f"{rev_pivot.loc[name, bln] / 1_000:,.0f}".replace(",", ".")
            fig.add_annotation(
                x=bln, y=name, text=rev_disp, showarrow=False,
                font=dict(size=13, color=val_color, family="monospace"),
                yshift=8,
            )
            fig.add_annotation(
                x=bln, y=name, text=f"Burn {rate:.1f}%", showarrow=False,
                font=dict(size=9, color=val_color), yshift=-10,
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
        xref="paper", yref="paper", x=-0.06, y=1.075,
        font=dict(size=10, color="#94a3b8"),
        xanchor="left",
    )

    st.plotly_chart(fig, use_container_width=True, key=key)
    st.markdown(
        '<p style="font-size:10px; color:#64748b; margin-top:-10px;">'
        'Angka besar = Revenue Item D &nbsp;&nbsp; Warna sel & keterangan kecil = Burn Rate (%), semakin terang/pekat oranye semakin tinggi burn rate.</p>',
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
    SATU pivot table yang bisa switch dimensi + filter Area + search box (mode Customer/Salesman).

    `df` harus dataframe yang sudah difilter kategori/jenis oleh tab pemanggil, dan minimal
    punya kolom: Cabang, Kode_Area, Bulan, Bulan_Num, plus Customer_No/Customer_Name (mode
    Customer) atau Salesman_Name (mode Salesman) sesuai subj_options yang dipakai.
    fmt_cell: formatter angka di sel tabel (default ribuan biasa, bisa diisi fmt_rp/fmt_liter dst).
    subj_options: daftar dimensi yang bisa dipilih (default ["Cabang", "Customer"]).
    """
    if df is None or df.empty:
        st.info("Tidak ada data untuk breakdown.")
        return

    fmt_cell = fmt_cell or (lambda x: f"{x:,.0f}".replace(",", "."))
    subj_options = subj_options or ["Cabang", "Customer"]

    col1, col2 = st.columns(2)
    with col1:
        subj_dim = st.selectbox("Breakdown per", subj_options, key=f"breakdown_dim_{key_prefix}")
    with col2:
        area_options = sorted(df["Kode_Area"].dropna().unique().tolist()) if "Kode_Area" in df.columns else []
        area_key = f"breakdown_area_{key_prefix}"
        cleanup_selection(area_key, area_options)
        pilih_area = st.multiselect("Filter Area", area_options, key=area_key, placeholder="Semua (klik untuk filter)")

    df_scope = df[df["Kode_Area"].isin(pilih_area)] if pilih_area else df

    if subj_dim == "Cabang":
        subj_col = "Cabang"
    elif subj_dim == "Salesman":
        df_scope = df_scope.copy()
        df_scope["Salesman_Label"] = df_scope["Salesman_Name"].astype(str).str.strip().str.upper()
        subj_col = "Salesman_Label"
        search_kw = st.text_input("Cari Salesman", key=f"breakdown_search_{key_prefix}")
        if search_kw.strip():
            df_scope = df_scope[df_scope[subj_col].str.contains(search_kw.strip(), case=False, na=False)]
    else:
        df_scope = df_scope.copy()
        df_scope["Customer_Label"] = df_scope["Customer_No"].astype(str) + " - " + df_scope["Customer_Name"].astype(str).str.strip().str.upper()
        subj_col = "Customer_Label"
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


def render_card(icon, title, value, sub):
    """Return HTML string untuk metric card standar. `icon` boleh string kosong ""
    (card tanpa ikon) — tidak menyisakan spasi nyasar di depan title."""
    card_title = f"{icon} {title}" if icon else title
    return (
        f'<div class="custom-card">'
        f'<div class="card-title">{card_title}</div>'
        f'<div class="card-value">{value}</div>'
        f'<div class="card-sub">{sub}</div>'
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