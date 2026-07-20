# ============================================================
# 🧩 TAB: CROSS-SELL GAP (peluang kategori yang belum digarap per customer)
# ============================================================
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.matgroup_engine import compute_matgroup_link, MATGROUP_ORDER, MATGROUP_COLORS
from utils.customer_matgroup_engine import build_customer_category_profile
from utils.components import render_card, render_tile_filter, auto_table_height
from utils.styles import fmt_rp, fmt_rp_full

MIN_PEER_SIZE = 5  # peer group lebih kecil dari ini diskip — % adopsi dari 2-3 customer gampang menyesatkan


def _detect_gaps(cust_cat, attr, peer_cols, min_adoption_pct):
    """Deteksi gap: customer aktif yang TIDAK membeli kategori yang lazim dibeli
    (adopsi >= ambang) oleh peer sejenisnya. Return (gaps_df, adoption_df)."""
    active_cust = cust_cat.groupby("Customer_No")["Actual"].sum().rename("Total_Actual")
    members = attr[attr["Customer_No"].isin(active_cust.index)].copy()
    members["Peer_Group"] = members[peer_cols].astype(str).agg(" · ".join, axis=1)
    members = members.merge(active_cust, on="Customer_No")

    group_size = members.groupby("Peer_Group")["Customer_No"].nunique().rename("Group_Size")

    cc = cust_cat.merge(members[["Customer_No", "Peer_Group"]], on="Customer_No", how="inner")
    stats = cc.groupby(["Peer_Group", "Mat_Group"]).agg(
        N_Buyers=("Customer_No", "nunique"),
        Median_Spend=("Actual", "median"),
    ).reset_index()
    stats = stats.merge(group_size, on="Peer_Group")
    stats = stats[stats["Group_Size"] >= MIN_PEER_SIZE]
    stats["Adoption_Pct"] = stats["N_Buyers"] / stats["Group_Size"] * 100

    candidates = stats[stats["Adoption_Pct"] >= min_adoption_pct]
    if candidates.empty:
        return pd.DataFrame(), stats

    # Cartesian anggota group × kategori kandidat group itu, lalu buang pasangan yang
    # sudah dibeli — sisanya adalah gap.
    pairs = members.merge(candidates, on="Peer_Group")
    bought = set(zip(cust_cat["Customer_No"], cust_cat["Mat_Group"]))
    is_gap = [
        (c, m) not in bought
        for c, m in zip(pairs["Customer_No"], pairs["Mat_Group"])
    ]
    gaps = pairs[is_gap].copy()
    gaps = gaps.sort_values("Median_Spend", ascending=False).reset_index(drop=True)
    return gaps, stats


TOP_N_PARTS = 15


def _render_breakdown(selected_row, linked_ty, df_part_master, attr, peer_cols):
    """Breakdown detail: siapa peer-nya, dan top partnumber yang dibeli peer di kategori gap."""
    cust_no = selected_row["Customer_No"]
    cust_name = selected_row["Customer_Name"]
    mat_group = selected_row["Mat_Group"]
    peer_group = selected_row["Peer_Group"]

    members = attr[attr["Customer_No"].isin(linked_ty["Customer_No"].unique())].copy()
    members["Peer_Group"] = members[peer_cols].astype(str).agg(" · ".join, axis=1)
    peers_in_group = members[members["Peer_Group"] == peer_group]

    peer_txn = linked_ty[
        (linked_ty["Customer_No"].isin(peers_in_group["Customer_No"]))
        & (linked_ty["Mat_Group"] == mat_group)
        & (linked_ty["Customer_No"] != cust_no)
    ]
    if peer_txn.empty:
        st.info("Tidak ada data transaksi peer untuk breakdown ini.")
        return

    color = MATGROUP_COLORS.get(mat_group, "#64748b")
    st.markdown(
        f"#### Breakdown Peer — <span style='color:{color};font-weight:bold'>{mat_group}</span>"
        f" untuk {cust_no} - {cust_name}",
        unsafe_allow_html=True,
    )

    col_peer, col_part = st.columns(2)

    with col_peer:
        st.markdown("##### Peer yang Membeli Kategori Ini")
        peer_summary = (
            peer_txn.groupby("Customer_No")
            .agg(Total_Actual=("Actual", "sum"), N_Transaksi=("Actual", "size"))
            .reset_index()
        )
        peer_summary = peer_summary.merge(
            peers_in_group[["Customer_No", "Customer_Name", "Cabang"]], on="Customer_No", how="left",
        )
        peer_summary["Customer"] = peer_summary["Customer_No"].astype(str) + " - " + peer_summary["Customer_Name"].astype(str)
        peer_summary = peer_summary.sort_values("Total_Actual", ascending=False)
        st.dataframe(
            peer_summary[["Customer", "Cabang", "N_Transaksi", "Total_Actual"]]
            .rename(columns={"N_Transaksi": "Jml Transaksi", "Total_Actual": "Total Belanja"})
            .style.format({"Total Belanja": fmt_rp_full}),
            use_container_width=True, hide_index=True,
            height=min(auto_table_height(len(peer_summary)), 400),
        )
        st.caption(f"{len(peer_summary)} peer membeli {mat_group}.")

    with col_part:
        st.markdown(f"##### Top {TOP_N_PARTS} Partnumber di Peer")
        pno_col = "Partnumber"
        part_agg = (
            peer_txn.groupby(pno_col)
            .agg(
                N_Peer_Beli=("Customer_No", "nunique"),
                Total_Qty=("Qty", "sum"),
                Median_Qty=("Qty", "median"),
                Min_Qty=("Qty", "min"),
                Max_Qty=("Qty", "max"),
                Total_Actual=("Actual", "sum"),
            )
            .reset_index()
            .sort_values("N_Peer_Beli", ascending=False)
            .head(TOP_N_PARTS)
        )
        pm = df_part_master.rename(columns={"part_number": pno_col, "part_name": "Part_Name"})
        part_agg = part_agg.merge(pm[[pno_col, "Part_Name"]], on=pno_col, how="left")
        part_agg["Part_Name"] = part_agg["Part_Name"].fillna("-")
        part_agg["Range Qty"] = (
            part_agg["Min_Qty"].astype(int).astype(str) + " – " + part_agg["Max_Qty"].astype(int).astype(str)
        )
        display_parts = part_agg.rename(columns={
            pno_col: "Partnumber", "N_Peer_Beli": "Peer Beli",
            "Median_Qty": "Median Qty", "Total_Actual": "Total Belanja",
        })[["Partnumber", "Part_Name", "Peer Beli", "Median Qty", "Range Qty", "Total Belanja"]]
        st.dataframe(
            display_parts.style.format({"Median Qty": "{:.0f}", "Total Belanja": fmt_rp_full}),
            use_container_width=True, hide_index=True,
            height=min(auto_table_height(len(display_parts)), 400),
        )
        st.caption(f"Diurutkan dari partnumber yang dibeli peer terbanyak.")


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

    col_peer, col_ambang = st.columns([1, 2])
    with col_peer:
        peer_mode = st.radio(
            "Definisi peer (customer sejenis)", ["Kelas Customer", "Kelas + Area"],
            horizontal=True, key="crosssell_peer_mode",
        )
    with col_ambang:
        min_adoption = st.slider(
            "Ambang kelaziman kategori di peer (%)", min_value=20, max_value=90, value=50, step=5,
            key="crosssell_min_adoption",
            help="Kategori dianggap 'lazim' bagi sebuah peer group kalau minimal sekian persen anggotanya membeli kategori itu — gap hanya dicari pada kategori yang lazim.",
        )

    peer_cols_list = ["Kelas_Customer"] if peer_mode == "Kelas Customer" else ["Kelas_Customer", "Kode_Area"]
    gaps, stats = _detect_gaps(cust_cat, attr, peer_cols_list, min_adoption)

    if gaps.empty:
        st.success(
            f"Tidak ada gap cross-sell pada ambang {min_adoption}% — semua customer aktif sudah membeli "
            "kategori-kategori yang lazim di peer group-nya (atau peer group-nya terlalu kecil untuk dinilai)."
        )
        return

    n_cust_gap = gaps["Customer_No"].nunique()
    n_active = cust_cat["Customer_No"].nunique()
    total_potensi = gaps["Median_Spend"].sum()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(render_card("🧩", "Customer dengan Peluang", f"{n_cust_gap:,}".replace(",", "."), f"dari {n_active:,} customer aktif {pilih_tahun}".replace(",", ".")), unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("🎯", "Total Pasangan Peluang", f"{len(gaps):,}".replace(",", "."), "kombinasi customer × kategori yang belum digarap"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_card("💡", "Indikasi Ukuran Peluang", fmt_rp(total_potensi), "jumlah median belanja peer — indikasi kasar, bukan forecast"), unsafe_allow_html=True)

    # ── Kategori dengan peluang terbanyak ──
    st.markdown("#### Kategori dengan Peluang Terbanyak")
    per_cat = gaps.groupby("Mat_Group").agg(
        N_Gap=("Customer_No", "nunique"), Potensi=("Median_Spend", "sum"),
    ).reindex([m for m in MATGROUP_ORDER if m != "Unclassified"]).dropna(how="all").fillna(0)
    per_cat = per_cat.sort_values("N_Gap", ascending=False)
    fig = go.Figure(go.Bar(
        x=per_cat["N_Gap"], y=per_cat.index, orientation="h",
        marker_color=[MATGROUP_COLORS.get(k, "#64748b") for k in per_cat.index],
        text=[f"{int(v):,}".replace(",", ".") for v in per_cat["N_Gap"]],
        textposition="auto", textfont=dict(color="#f8fafc", size=13),
        hovertext=[
            f"<b>{k}</b><br>{int(r['N_Gap']):,} customer belum digarap".replace(",", ".")
            + f"<br>Indikasi peluang: {fmt_rp_full(r['Potensi'])}"
            for k, r in per_cat.iterrows()
        ],
        hovertemplate="%{hovertext}<extra></extra>",
    ))
    fig.update_layout(
        height=70 + len(per_cat) * 44,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title=dict(text="Jumlah Customer dengan Gap", font=dict(color="white", size=13)), tickfont=dict(color="white", size=12), gridcolor="#333333"),
        yaxis=dict(tickfont=dict(color="white", size=12), autorange="reversed"),
        margin=dict(l=10, r=30, t=10, b=10),
    )
    st.plotly_chart(fig, use_container_width=True, key="chart_crosssell_per_kategori")

    # ── Daftar peluang ──
    st.markdown("#### Daftar Peluang Cross-sell — diurutkan dari indikasi peluang terbesar")
    kategori_options = [m for m in MATGROUP_ORDER if m in gaps["Mat_Group"].unique()]
    col_kat, col_search = st.columns([2, 1])
    with col_kat:
        pilih_kategori = render_tile_filter("Filter Kategori", kategori_options, key="crosssell_kategori_filter")
    with col_search:
        st.markdown('<div style="height:0.55rem"></div>', unsafe_allow_html=True)
        search_query = st.text_input(
            "Cari Customer (kode/nama)", key="crosssell_search", placeholder="Ketik kode atau nama customer...",
        )

    table = gaps[gaps["Mat_Group"].isin(pilih_kategori)].copy().reset_index(drop=True)
    table["Customer"] = table["Customer_No"].astype(str) + " - " + table["Customer_Name"].astype(str)
    if search_query.strip():
        q = search_query.strip().upper()
        table = table[table["Customer"].str.upper().str.contains(q, na=False)].reset_index(drop=True)

    if table.empty:
        st.info("Tidak ada peluang untuk kombinasi filter/pencarian ini.")
    else:
        table["Peer_Buyers"] = (
            table["N_Buyers"].astype(int).astype(str) + " dari " + table["Group_Size"].astype(int).astype(str)
        )
        display = table.rename(columns={
            "Mat_Group": "Kategori Peluang", "Peer_Group": "Peer Group",
            "Adoption_Pct": "% Peer yang Beli", "Peer_Buyers": "Peer Pembeli",
            "Median_Spend": "Median Belanja Peer", "Total_Actual": "Total Actual Customer",
        })[[
            "Customer", "Cabang", "Peer Group", "Kategori Peluang", "% Peer yang Beli",
            "Peer Pembeli", "Median Belanja Peer", "Total Actual Customer",
        ]]

        def _style_kategori(val):
            color = MATGROUP_COLORS.get(val)
            return f"color: {color}; font-weight: bold;" if color else ""

        event = st.dataframe(
            display.style
            .map(_style_kategori, subset=["Kategori Peluang"])
            .format({
                "% Peer yang Beli": "{:.0f}%", "Median Belanja Peer": fmt_rp_full,
                "Total Actual Customer": fmt_rp_full,
            }),
            use_container_width=True, hide_index=True,
            height=min(auto_table_height(len(display)), 600),
            on_select="rerun", selection_mode="single-row",
            key="crosssell_table_select",
        )
        st.caption(f"{len(display):,} pasangan peluang ditampilkan sesuai filter — klik baris untuk breakdown detail.".replace(",", "."))

        sel_rows = event.selection.get("rows", []) if event and hasattr(event, "selection") else []
        if sel_rows:
            idx = sel_rows[0]
            sel = table.iloc[idx]
            st.markdown("---")
            _render_breakdown(sel, linked_ty, df_part_master, attr, peer_cols_list)

    st.markdown("---")
    st.markdown("### Penjelasan")
    st.markdown(
        "- **Cross-sell Gap** mencari customer aktif yang **belum membeli kategori produk yang lazim dibeli oleh "
        "peer-nya** (customer dengan Kelas — dan opsional Area — yang sama). Ini mengubah profil komposisi kategori "
        "dari insight pasif menjadi daftar tindak lanjut yang konkret untuk tim sales.\n"
        f"- Peer group dengan anggota kurang dari **{MIN_PEER_SIZE} customer aktif** tidak dinilai — persentase adopsi "
        "dari kelompok sekecil itu terlalu mudah menyimpang.\n"
        "- **Median Belanja Peer** adalah median belanja tahunan customer peer yang membeli kategori tersebut — dipakai "
        "sebagai **indikasi urutan prioritas** peluang, bukan proyeksi nilai yang pasti tercapai.\n"
        "- Kategori **Unclassified** tidak diikutkan (bukan kategori produk yang bisa ditawarkan), dan customer yang "
        "net belanjanya di suatu kategori ≤ 0 (retur melebihi pembelian) diperlakukan sebagai belum membeli kategori itu.\n"
        f"- Scope data mengikuti **Filter General** dan tahun terpilih ({pilih_tahun}), basis **Actual (Supply)**."
    )
