# ============================================================
# 🎯 TAB: KOMBO SERVIS — Dual-Track Marketing Incentive Program
# ============================================================
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.matgroup_engine import MATGROUP_COLORS
from utils.components import render_card, auto_table_height, cleanup_selection
from utils.styles import fmt_rp, fmt_rp_full

# ── Program constants ──────────────────────────────────────────

KOMBOS = {
    "Servis Ringan": ["TGP", "TMO"],
    "Servis Lengkap": ["TGP", "TMO", "CHEMICAL"],
    "Electrical Pack": ["TGP", "BUSI", "AC"],
    "Full House": ["TGP", "TMO", "CHEMICAL", "BUSI"],
}

MULTIPLIERS = {"TMO": 1.5, "CHEMICAL": 1.5, "BUSI": 1.5, "AC": 1.2}

KOMBO_TIERS = [(3, "Gold", 0.015), (2, "Silver", 0.010), (1, "Bronze", 0.005)]
DEFENDER_TIERS = [(15, "Gold", 0.005), (5, "Silver", 0.003), (0, "Bronze", 0.001)]

TIER_COLORS = {
    "Gold": "#b8860b", "Silver": "#6b7b8d", "Bronze": "#9c6644",
    "Tidak Qualify": "#3a3f47", "Disqualified": "#3a3f47",
}
TRACK_COLORS = {"Kombo": "#22c55e", "Defender": "#3b82f6"}

_Q = {"Q1": (1, 3), "Q2": (4, 6), "Q3": (7, 9), "Q4": (10, 12)}


# ── Helpers ────────────────────────────────────────────────────

def _q_filter(df, tahun, quarter):
    s, e = _Q[quarter]
    return df[(df["Tahun"] == tahun) & (df["Bulan_Num"].between(s, e))]


def _mult(mg):
    return MULTIPLIERS.get(mg, 1.0)


# ── Core computation ───────────────────────────────────────────

def _compute(order_q, supply_q, supply_ly):
    if supply_q.empty:
        return None

    sq = supply_q.copy()
    sq["_mult"] = sq["Mat_Group"].map(_mult)
    sq["_wns"] = sq["Net_Sales"] * sq["_mult"]

    cust_mg = sq.groupby("Customer_No")["Mat_Group"].nunique()
    kombo_cnos = set(cust_mg[cust_mg.between(1, 5)].index)
    defender_cnos = set(cust_mg[cust_mg >= 6].index)

    cust_agg = sq.groupby("Customer_No").agg(
        _wns=("_wns", "sum"), NS=("Net_Sales", "sum"),
        Cabang=("Cabang", "first"),
    )

    kombo_df = _calc_kombo(order_q, cust_agg, kombo_cnos)
    defender_df = _calc_defender(cust_agg, cust_mg, supply_ly, defender_cnos)

    return {
        "kombo": kombo_df, "defender": defender_df,
        "total_ns": sq["Net_Sales"].sum(),
        "total_profit": sq["Profit"].sum() if "Profit" in sq.columns else 0,
        "n_kombo": len(kombo_cnos), "n_defender": len(defender_cnos),
    }


def _calc_kombo(order_q, cust_agg, cnos):
    if not cnos:
        return pd.DataFrame()

    oq = order_q[order_q["Customer_No"].isin(cnos)]
    order_mgs = (
        oq.groupby("Customer_No")["Mat_Group"].apply(set)
        if not oq.empty else pd.Series(dtype=object)
    )

    rows = []
    for cno in cnos:
        mgs = order_mgs.get(cno, set())
        if not isinstance(mgs, set):
            mgs = set()

        completed = [k for k, reqs in KOMBOS.items() if all(m in mgs for m in reqs)]
        n = len(completed)

        tier, rate = "Tidak Qualify", 0.0
        for thresh, tname, trate in KOMBO_TIERS:
            if n >= thresh:
                tier, rate = tname, trate
                break

        agg = cust_agg.loc[cno] if cno in cust_agg.index else None
        rows.append({
            "Customer_No": cno,
            "Cabang": agg["Cabang"] if agg is not None else "",
            "N_MG": len(mgs),
            "Kombos": ", ".join(completed) if completed else "—",
            "N_Kombo": n, "Tier": tier, "Rate": rate,
            "NS": agg["NS"] if agg is not None else 0,
            "Reward": (agg["_wns"] if agg is not None else 0) * rate,
        })

    return pd.DataFrame(rows)


def _calc_defender(cust_agg, cust_mg, supply_ly, cnos):
    if not cnos:
        return pd.DataFrame()

    ns_ly = (
        supply_ly[supply_ly["Customer_No"].isin(cnos)]
        .groupby("Customer_No")["Net_Sales"].sum()
        if supply_ly is not None and not supply_ly.empty
        else pd.Series(dtype=float)
    )

    rows = []
    for cno in cnos:
        if cno not in cust_agg.index:
            continue
        agg = cust_agg.loc[cno]
        mg_n = cust_mg.get(cno, 0)
        ns, wns, cab = agg["NS"], agg["_wns"], agg["Cabang"]

        if mg_n < 5:
            rows.append({"Customer_No": cno, "Cabang": cab, "N_MG": mg_n,
                         "Growth_Pct": None, "Tier": "Disqualified",
                         "Rate": 0.0, "NS": ns, "Reward": 0.0})
            continue

        ly = ns_ly.get(cno, 0)
        growth = ((ns / ly) - 1) * 100 if ly > 0 else (100.0 if ns > 0 else 0.0)

        tier, rate = "Disqualified", 0.0
        if growth >= 0:
            for thresh, tname, trate in DEFENDER_TIERS:
                if growth >= thresh:
                    tier, rate = tname, trate
                    break

        rows.append({"Customer_No": cno, "Cabang": cab, "N_MG": mg_n,
                     "Growth_Pct": growth, "Tier": tier, "Rate": rate,
                     "NS": ns, "Reward": wns * rate})

    return pd.DataFrame(rows)


# ── Visualizations ─────────────────────────────────────────────

def _render_cards(res):
    k, d = res["kombo"], res["defender"]
    total_rw = (k["Reward"].sum() if not k.empty else 0) + (d["Reward"].sum() if not d.empty else 0)
    qualify_k = (k["Tier"] != "Tidak Qualify").sum() if not k.empty else 0
    qualify_d = (d["Tier"] != "Disqualified").sum() if not d.empty else 0
    n_total = res["n_kombo"] + res["n_defender"]
    pct_profit = total_rw / res["total_profit"] * 100 if res["total_profit"] else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_card("", "Total Pelanggan Aktif",
                                f"{n_total:,}".replace(",", "."),
                                f"Kombo: {res['n_kombo']} | Defender: {res['n_defender']}"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(render_card("", "Total Reward",
                                f'<span style="color:#b8860b">{fmt_rp(total_rw)}</span>',
                                f"{total_rw / res['total_ns'] * 100:.2f}% dari Net Sales" if res["total_ns"] else ""),
                    unsafe_allow_html=True)
    with c3:
        color = "#22c55e" if pct_profit <= 5 else "#f59e0b"
        st.markdown(render_card("", "% dari Profit",
                                f'<span style="color:{color}">{pct_profit:.1f}%</span>',
                                f"Profit: {fmt_rp(res['total_profit'])}"),
                    unsafe_allow_html=True)
    with c4:
        q_rate = (qualify_k + qualify_d) / n_total * 100 if n_total else 0
        st.markdown(render_card("", "Qualify Rate",
                                f"{q_rate:.0f}%",
                                f"{qualify_k + qualify_d:,} dari {n_total:,} customer".replace(",", ".")),
                    unsafe_allow_html=True)


def _render_sunburst(res):
    k, d = res["kombo"], res["defender"]
    k_tiers = k["Tier"].value_counts() if not k.empty else pd.Series(dtype=int)
    d_tiers = d["Tier"].value_counts() if not d.empty else pd.Series(dtype=int)

    k_rw = k.groupby("Tier")["Reward"].sum() if not k.empty else pd.Series(dtype=float)
    d_rw = d.groupby("Tier")["Reward"].sum() if not d.empty else pd.Series(dtype=float)

    n_total = res["n_kombo"] + res["n_defender"]
    ids, labels, parents, values, colors, hovers = [], [], [], [], [], []

    ids.append("root")
    labels.append(f"Total ({n_total})")
    parents.append("")
    values.append(n_total)
    colors.append("rgba(30,41,59,0.6)")
    hovers.append(f"<b>Program Kombo Servis</b><br>{n_total} pelanggan aktif")

    for track, cnos, tiers, rw, tier_list in [
        ("Kombo", res["n_kombo"], k_tiers, k_rw,
         ["Gold", "Silver", "Bronze", "Tidak Qualify"]),
        ("Defender", res["n_defender"], d_tiers, d_rw,
         ["Gold", "Silver", "Bronze", "Disqualified"]),
    ]:
        ids.append(track)
        labels.append(f"Jalur {track} ({cnos})")
        parents.append("root")
        values.append(cnos)
        colors.append(TRACK_COLORS[track])
        hovers.append(f"<b>Jalur {track}</b><br>{cnos} pelanggan")

        for t in tier_list:
            cnt = int(tiers.get(t, 0))
            rew = rw.get(t, 0)
            ids.append(f"{track}-{t}")
            labels.append(f"{t} ({cnt})")
            parents.append(track)
            values.append(cnt)
            colors.append(TIER_COLORS.get(t, "#3a3f47"))
            hovers.append(f"<b>{t}</b><br>{cnt} pelanggan<br>Reward: {fmt_rp(rew)}")

    fig = go.Figure(go.Sunburst(
        ids=ids, labels=labels, parents=parents, values=values,
        marker=dict(colors=colors, line=dict(color="#0e1117", width=1.5)),
        branchvalues="total",
        hovertext=hovers, hovertemplate="%{hovertext}<extra></extra>",
        textinfo="label", insidetextorientation="radial",
    ))
    fig.update_layout(
        height=420, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, key="chart_sunburst_kombo")


def _render_summary_table(res):
    k, d = res["kombo"], res["defender"]

    def _tier_counts(df, tiers, dq_label):
        if df.empty:
            return {t: 0 for t in tiers}, 0, 0
        vc = df["Tier"].value_counts()
        counts = {t: int(vc.get(t, 0)) for t in tiers}
        qualify = sum(v for t, v in counts.items() if t != dq_label)
        total_rw = df["Reward"].sum()
        return counts, qualify, total_rw

    k_counts, k_q, k_rw = _tier_counts(k, ["Gold", "Silver", "Bronze", "Tidak Qualify"], "Tidak Qualify")
    d_counts, d_q, d_rw = _tier_counts(d, ["Gold", "Silver", "Bronze", "Disqualified"], "Disqualified")

    rows = [
        {"Track": "Jalur Kombo", "Pelanggan": res["n_kombo"],
         "Gold": k_counts["Gold"], "Silver": k_counts["Silver"], "Bronze": k_counts["Bronze"],
         "Tidak Qualify": k_counts["Tidak Qualify"], "Total Reward": k_rw},
        {"Track": "Jalur Defender", "Pelanggan": res["n_defender"],
         "Gold": d_counts["Gold"], "Silver": d_counts["Silver"], "Bronze": d_counts["Bronze"],
         "Tidak Qualify": d_counts["Disqualified"], "Total Reward": d_rw},
    ]
    summary = pd.DataFrame(rows).set_index("Track")

    styled = summary.style.format({
        "Pelanggan": "{:,.0f}", "Gold": "{:,.0f}", "Silver": "{:,.0f}",
        "Bronze": "{:,.0f}", "Tidak Qualify": "{:,.0f}", "Total Reward": fmt_rp_full,
    }).set_properties(**{"text-align": "right", "font-size": "13px"})
    st.dataframe(styled, use_container_width=True, height=auto_table_height(2))

    st.markdown("##### Popularitas Kombo")
    if not k.empty and "Kombos" in k.columns:
        kombo_counts = {}
        for combos in k["Kombos"]:
            if combos == "—":
                continue
            for c in combos.split(", "):
                kombo_counts[c] = kombo_counts.get(c, 0) + 1
        if kombo_counts:
            kc_df = pd.DataFrame([
                {"Kombo": kn, "Komponen": " + ".join(KOMBOS[kn]), "Customer Selesai": cnt}
                for kn, cnt in sorted(kombo_counts.items(), key=lambda x: -x[1])
            ]).set_index("Kombo")
            st.dataframe(kc_df, use_container_width=True, height=auto_table_height(len(kc_df)))


def _render_cabang_chart(res):
    k, d = res["kombo"], res["defender"]
    k_cab = k.groupby("Cabang")["Reward"].sum() if not k.empty else pd.Series(dtype=float)
    d_cab = d.groupby("Cabang")["Reward"].sum() if not d.empty else pd.Series(dtype=float)

    cab = pd.DataFrame({"Kombo": k_cab, "Defender": d_cab}).fillna(0)
    cab["Total"] = cab["Kombo"] + cab["Defender"]
    cab = cab[cab["Total"] > 0].sort_values("Total", ascending=True).tail(15)

    if cab.empty:
        st.info("Tidak ada data reward per cabang.")
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Jalur Kombo", x=cab["Kombo"], y=cab.index, orientation="h",
        marker_color=TRACK_COLORS["Kombo"], marker_line=dict(width=0),
        hovertemplate="<b>%{y}</b><br>Kombo: %{x:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Jalur Defender", x=cab["Defender"], y=cab.index, orientation="h",
        marker_color=TRACK_COLORS["Defender"], marker_line=dict(width=0),
        hovertemplate="<b>%{y}</b><br>Defender: %{x:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        barmode="stack",
        height=max(350, len(cab) * 28 + 80),
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Total Reward (Rp)", gridcolor="#333333",
                   tickfont=dict(color="white"), title_font=dict(color="white")),
        yaxis=dict(tickfont=dict(color="white"), gridcolor="#333333"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    font=dict(color="white"), bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True, key="chart_cabang_kombo")


def _render_near_miss(order_q, res):
    k = res["kombo"]
    if k.empty:
        return
    kombo_cnos = set(k["Customer_No"])
    oq = order_q[order_q["Customer_No"].isin(kombo_cnos)]
    if oq.empty:
        return
    order_mgs = oq.groupby("Customer_No")["Mat_Group"].apply(set)

    cab_map = dict(zip(k["Customer_No"], k["Cabang"]))
    ns_map = dict(zip(k["Customer_No"], k["NS"]))

    near = []
    for cno in kombo_cnos:
        mgs = order_mgs.get(cno, set())
        if not isinstance(mgs, set):
            mgs = set()
        for kname, kreqs in KOMBOS.items():
            kreqs_set = set(kreqs)
            if kreqs_set.issubset(mgs):
                continue
            missing = kreqs_set - mgs
            if len(missing) == 1:
                near.append({
                    "Customer_No": cno, "Cabang": cab_map.get(cno, ""),
                    "Kombo Target": kname, "Kurang": list(missing)[0],
                    "NS": ns_map.get(cno, 0),
                })

    if not near:
        return

    nm = pd.DataFrame(near)

    st.markdown("#### Potensi Konversi — Selangkah dari Kombo")
    st.caption("Customer yang hanya kurang 1 kategori untuk menyelesaikan kombo. "
               "Prioritas push oleh salesman.")

    summary = nm.groupby("Kurang").agg(
        **{"Jumlah Customer": ("Customer_No", "nunique")},
        **{"Kombo Target": ("Kombo Target", lambda x: ", ".join(sorted(set(x))))},
        **{"Total NS Customer": ("NS", "sum")},
    ).sort_values("Jumlah Customer", ascending=False)

    styled = summary.style.format({"Total NS Customer": fmt_rp_full}).set_properties(
        **{"text-align": "right", "font-size": "13px"},
    )
    st.dataframe(styled, use_container_width=True, height=auto_table_height(len(summary)))


def _render_detail_table(df, track):
    if df.empty:
        st.info(f"Tidak ada data {track}.")
        return

    if track == "Kombo":
        cols = ["Customer_No", "Cabang", "N_MG", "Kombos", "N_Kombo", "Tier", "NS", "Reward"]
        col_labels = {
            "Customer_No": "Customer", "N_MG": "Jml Kategori", "N_Kombo": "Jml Kombo",
            "Kombos": "Kombo Selesai",
        }
        sort_col = "Reward"
    else:
        cols = ["Customer_No", "Cabang", "N_MG", "Growth_Pct", "Tier", "NS", "Reward"]
        col_labels = {
            "Customer_No": "Customer", "N_MG": "Jml Kategori", "Growth_Pct": "Growth YoY %",
        }
        sort_col = "Reward"

    show = df[cols].copy()
    show = show.rename(columns=col_labels)
    show = show.sort_values(sort_col, ascending=False)

    fmt = {"NS": fmt_rp_full, "Reward": fmt_rp_full}
    if "Growth YoY %" in show.columns:
        fmt["Growth YoY %"] = "{:.1f}%"

    styled = show.style.format(fmt, na_rep="—").set_properties(
        **{"text-align": "right", "font-size": "13px"},
    )
    st.dataframe(styled, use_container_width=True,
                 height=auto_table_height(min(len(show), 20)))


def _render_rules():
    st.markdown("---")
    st.markdown("### Rule of the Game")
    st.markdown(
        "**Periode:** Per kuartal (3 bulan)\n\n"
        "**Jalur Kombo** — customer dengan 1–5 kategori produk:\n"
        "- Kualifikasi: data **Order** — semua komponen kombo harus dipesan dalam 1 kuartal\n"
        "- Reward: dihitung dari **Actual** (Net Sales invoice) × Rate × Multiplier\n"
        "- Paket: Servis Ringan (TGP+TMO), Servis Lengkap (+Chemical), "
        "Electrical Pack (TGP+Busi+AC), Full House (TGP+TMO+Chemical+Busi)\n"
        "- Tier: Bronze (1 kombo, 0,5%), Silver (2 kombo, 1,0%), Gold (3+ kombo, 1,5%)\n\n"
        "**Jalur Defender** — customer dengan 6+ kategori produk:\n"
        "- Wajib mempertahankan ≥5 kategori dalam kuartal berjalan\n"
        "- Tier berdasar pertumbuhan Net Sales YoY: "
        "Bronze (≥0%, 0,1%), Silver (≥5%, 0,3%), Gold (≥15%, 0,5%)\n"
        "- Pertumbuhan negatif = tidak qualify\n\n"
        "**Multiplier per Kategori:** TMO / Chemical / Busi = 1,5×  —  AC = 1,2×  —  "
        "Lainnya = 1,0× (cap 2,0×, review tiap semester)\n\n"
        "**Formula:** Reward = Σ (Net Sales per baris invoice × Reward Rate × Multiplier)\n\n"
        "**Pencairan:** Credit Note yang berlaku sebagai potongan invoice di kuartal berikutnya"
    )


# ── Main render ────────────────────────────────────────────────

def render(df_order, df_supply):
    if df_supply is None or df_supply.empty:
        st.warning("Data Supply belum siap.")
        return
    if "Mat_Group" not in df_supply.columns:
        st.warning("Kolom Mat_Group belum tersedia — jalankan ulang converter Parquet.")
        return

    # ── Filters ──
    tahun_list = sorted(df_supply["Tahun"].dropna().unique().tolist())
    if not tahun_list:
        st.info("Belum ada data.")
        return
    tahun_terbaru = tahun_list[-1]

    col_t, col_q, col_c = st.columns([1, 1, 2])
    with col_t:
        pilih_tahun_raw = st.pills(
            "Tahun", [str(t) for t in tahun_list], selection_mode="single",
            default=str(tahun_terbaru), key="kombo_tahun",
        )
    pilih_tahun = int(pilih_tahun_raw) if pilih_tahun_raw else tahun_terbaru

    avail_months = df_supply[df_supply["Tahun"] == pilih_tahun]["Bulan_Num"].unique()
    avail_q = [q for q, (s, e) in _Q.items() if any(m in avail_months for m in range(s, e + 1))]
    if not avail_q:
        st.info(f"Tidak ada data untuk tahun {pilih_tahun}.")
        return

    with col_q:
        pilih_q = st.pills(
            "Quarter", avail_q, selection_mode="single",
            default=avail_q[-1], key="kombo_quarter",
        )
    if not pilih_q:
        pilih_q = avail_q[-1]

    cabang_options = sorted(df_supply["Cabang"].dropna().astype(str).str.strip().unique().tolist())
    cleanup_selection("kombo_cabang", cabang_options)
    with col_c:
        pilih_cabang = st.multiselect(
            "Filter Cabang", cabang_options, key="kombo_cabang",
            placeholder="Semua (klik untuk filter)",
        )

    # ── Prepare data ──
    supply_q = _q_filter(df_supply, pilih_tahun, pilih_q)
    order_q = _q_filter(df_order, pilih_tahun, pilih_q) if "Mat_Group" in df_order.columns else pd.DataFrame()
    supply_ly = _q_filter(df_supply, pilih_tahun - 1, pilih_q)

    if pilih_cabang:
        supply_q = supply_q[supply_q["Cabang"].astype(str).str.strip().isin(pilih_cabang)]
        if not order_q.empty:
            order_q = order_q[order_q["Cabang"].astype(str).str.strip().isin(pilih_cabang)]
        supply_ly = supply_ly[supply_ly["Cabang"].astype(str).str.strip().isin(pilih_cabang)]

    if supply_q.empty:
        st.info(f"Tidak ada data Supply untuk {pilih_q} {pilih_tahun}.")
        return

    # ── Compute ──
    res = _compute(order_q, supply_q, supply_ly)
    if res is None:
        st.info("Tidak ada data untuk dihitung.")
        return

    # ── Cards ──
    _render_cards(res)

    # ── Sunburst + Summary ──
    col_sun, col_sum = st.columns(2)
    with col_sun:
        st.markdown("##### Distribusi Customer per Track & Tier")
        _render_sunburst(res)
    with col_sum:
        st.markdown("##### Ringkasan Program")
        _render_summary_table(res)

    # ── Reward per Cabang ──
    st.markdown("#### Reward per Cabang (Top 15)")
    _render_cabang_chart(res)

    # ── Near-miss (Kombo) ──
    if not order_q.empty:
        _render_near_miss(order_q, res)

    # ── Detail tables ──
    with st.expander("📋 Detail Jalur Kombo"):
        _render_detail_table(res["kombo"], "Kombo")
    with st.expander("📋 Detail Jalur Defender"):
        _render_detail_table(res["defender"], "Defender")

    # ── Rules ──
    _render_rules()
