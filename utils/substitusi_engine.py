# ============================================================
# 🔁 SUBSTITUSI ENGINE — Lifecycle kode lama -> kode baru (part_master.xlsx)
# ============================================================
"""
part_number_substitusi di part_master.xlsx adalah catatan histori "kode lama -> kode baru"
(12 ribu+ link, semuanya menunjuk ke kode yang juga terdaftar sebagai part_number sendiri).
Modul ini mengubah catatan pasif itu jadi laporan lifecycle:

  - KELUARGA SUBSTITUSI: rantai kode digabung ke kode TERMINAL-nya (A->B->C jadi satu
    keluarga "C" beranggota A & B sebagai kode lama) — beberapa kode lama yang menunjuk
    ke kode baru yang sama otomatis tergabung ke satu keluarga.
  - CROSSOVER: bulan pertama volume kode baru menyalip kode lama — "kapan volume mulai
    pindah".
  - KESEHATAN VOLUME: rata-rata volume bulanan keluarga SESUDAH crossover dibanding
    SEBELUM-nya — pembeda antara "produk yang memang lagi turun" vs "produk yang cuma
    ganti kode doang, sebenarnya stabil".

Hanya keluarga yang kode lamanya masih bertransaksi di window data Supply yang dipantau —
substitusi yang sudah tuntas jauh sebelum window data dimulai tidak ada sinyal transisi
yang bisa dilaporkan.
"""
import numpy as np
import pandas as pd
import streamlit as st

TREND_BAND_PCT = 20.0   # ±% : perubahan volume sesudah vs sebelum crossover di dalam band ini = "Stabil"
CROSSOVER_WINDOW = 3    # bulan — jendela pembanding sebelum/sesudah crossover & penentu status transisi

STATUS_ORDER = ["Transisi Berjalan", "Transisi Selesai", "Belum Mulai"]
STATUS_COLOR = {"Transisi Selesai": "#10b981", "Transisi Berjalan": "#f59e0b", "Belum Mulai": "#3b82f6"}
TREND_ORDER = ["Naik", "Stabil", "Turun", "Baseline Kurang", "Belum Crossover"]
TREND_COLOR = {
    "Naik": "#10b981", "Stabil": "#94a3b8", "Turun": "#ef4444",
    "Baseline Kurang": "#64748b", "Belum Crossover": "#64748b",
}

_BULAN_ABBR = ["JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGS", "SEP", "OKT", "NOV", "DES"]


def periode_label(tahun, bulan_num):
    return f"{_BULAN_ABBR[int(bulan_num) - 1]}'{str(int(tahun))[2:]}"


def _terminal_map(links):
    """Peta setiap kode (lama maupun baru) -> kode terminal keluarganya, dengan rantai
    substitusi diikuti sampai ujung (A->B->C: A dan B sama-sama dipetakan ke C). Guard
    `seen` menghentikan loop kalau ada rantai melingkar di data (A->B->A) — kode terakhir
    sebelum berputar yang dipakai sebagai terminal."""
    next_code = dict(zip(links["part_number"], links["part_number_substitusi"]))
    cache = {}

    def terminal(code):
        if code in cache:
            return cache[code]
        path, seen = [], set()
        cur = code
        while cur in next_code and cur not in seen:
            seen.add(cur)
            path.append(cur)
            cur = next_code[cur]
            if cur in cache:
                cur = cache[cur]
                break
        for p in path:
            cache[p] = cur
        cache[code] = cur
        return cur

    fam = {}
    for old, new in next_code.items():
        fam[old] = terminal(old)
        fam[new] = terminal(new)
    return fam


@st.cache_data(show_spinner="Menyusun histori substitusi Partnumber...")
def compute_substitution_families(df_supply, df_part_master):
    """Return (families_df, monthly_df).

    families_df — 1 baris per keluarga substitusi yang kode lamanya masih bertransaksi di
    window data: kode terminal, nama part, mat_group, daftar kode lama, status transisi,
    periode crossover, rata-rata volume bulanan sebelum/sesudah crossover, delta %, tren.

    monthly_df — deret bulanan per keluarga (long): Family, Periode (Tahun*100+Bulan_Num),
    Label, Qty_Lama, Qty_Baru, Actual_Lama, Actual_Baru — bahan chart detail per keluarga.
    """
    empty = pd.DataFrame(), pd.DataFrame()
    if df_supply is None or df_supply.empty or df_part_master is None or df_part_master.empty:
        return empty

    links = df_part_master.dropna(subset=["part_number_substitusi"])[
        ["part_number", "part_number_substitusi"]
    ].drop_duplicates()
    if links.empty:
        return empty

    fam_map = _terminal_map(links)
    fam_series = pd.Series(fam_map)

    sup = df_supply[["Partnumber", "Tahun", "Bulan_Num", "Qty", "Actual"]].copy()
    sup = sup[sup["Partnumber"].isin(fam_series.index)]
    if sup.empty:
        return empty

    sup["Family"] = sup["Partnumber"].map(fam_series)
    sup["Role"] = np.where(sup["Partnumber"] == sup["Family"], "Baru", "Lama")

    # Hanya keluarga yang kode LAMA-nya masih muncul di window data — sisanya (cuma kode
    # baru yang jalan) tidak ada transisi yang bisa dipantau dari data ini.
    fam_with_old = sup.loc[sup["Role"] == "Lama", "Family"].unique()
    sup = sup[sup["Family"].isin(fam_with_old)]
    if sup.empty:
        return empty

    agg = sup.groupby(["Family", "Role", "Tahun", "Bulan_Num"]).agg(
        Qty=("Qty", "sum"), Actual=("Actual", "sum"),
    ).reset_index()
    agg["Periode"] = agg["Tahun"].astype(int) * 100 + agg["Bulan_Num"].astype(int)

    wide = agg.pivot_table(
        index=["Family", "Periode", "Tahun", "Bulan_Num"], columns="Role",
        values=["Qty", "Actual"], aggfunc="sum", fill_value=0,
    )
    wide.columns = [f"{v}_{r}" for v, r in wide.columns]
    for col in ("Qty_Lama", "Qty_Baru", "Actual_Lama", "Actual_Baru"):
        if col not in wide.columns:
            wide[col] = 0.0
    monthly = wide.reset_index().sort_values(["Family", "Periode"])
    monthly["Label"] = [periode_label(t, b) for t, b in zip(monthly["Tahun"], monthly["Bulan_Num"])]

    # ── Ringkasan per keluarga ──
    pm_name = df_part_master.drop_duplicates("part_number").set_index("part_number")
    old_codes = (
        links.assign(Family=links["part_number"].map(fam_map))
        .groupby("Family")["part_number"].agg(lambda s: ", ".join(sorted(s.unique())))
    )

    rows = []
    for family, grp in monthly.groupby("Family"):
        grp = grp.sort_values("Periode")
        qty_lama, qty_baru = grp["Qty_Lama"].to_numpy(), grp["Qty_Baru"].to_numpy()
        total_family = qty_lama + qty_baru

        # Crossover: bulan pertama kode baru punya volume DAN menyalip kode lama
        cross_mask = (qty_baru > 0) & (qty_baru >= qty_lama)
        cross_idx = int(np.argmax(cross_mask)) if cross_mask.any() else None
        crossover_label = grp["Label"].iloc[cross_idx] if cross_idx is not None else None

        # Status transisi: dilihat dari CROSSOVER_WINDOW bulan terakhir yang ada volumenya
        active = grp[total_family > 0]
        tail = active.tail(CROSSOVER_WINDOW)
        if qty_baru.sum() <= 0:
            status = "Belum Mulai"
        elif tail["Qty_Lama"].sum() <= 0:
            status = "Transisi Selesai"
        else:
            status = "Transisi Berjalan"

        # Kesehatan volume: rata-rata volume bulanan keluarga sebelum vs sesudah crossover.
        # "Baseline Kurang" = crossover-nya terjadi (label Crossover tetap terisi) tapi jatuh
        # tepat di/awal window data, jadi tidak ada bulan "sebelum" yang bisa dibandingkan —
        # beda dari "Belum Crossover" yang memang kode barunya belum pernah menyalip.
        avg_before = avg_after = delta_pct = None
        if cross_idx is None:
            trend = "Belum Crossover"
        else:
            before = total_family[max(0, cross_idx - CROSSOVER_WINDOW):cross_idx]
            if len(before) == 0 or before.mean() <= 0:
                trend = "Baseline Kurang"
            else:
                after = total_family[cross_idx:cross_idx + CROSSOVER_WINDOW]
                avg_before = float(before.mean())
                avg_after = float(after.mean())
                delta_pct = (avg_after - avg_before) / avg_before * 100
                if delta_pct > TREND_BAND_PCT:
                    trend = "Naik"
                elif delta_pct < -TREND_BAND_PCT:
                    trend = "Turun"
                else:
                    trend = "Stabil"

        rows.append({
            "Family": family,
            "Part_Name": pm_name["part_name"].get(family, "-"),
            "Mat_Group": pm_name["mat_group"].get(family, "-"),
            "Kode_Lama": old_codes.get(family, "-"),
            "Status": status,
            "Crossover": crossover_label or "—",
            "Qty_Lama_Total": float(qty_lama.sum()),
            "Qty_Baru_Total": float(qty_baru.sum()),
            "Actual_Total": float(grp["Actual_Lama"].sum() + grp["Actual_Baru"].sum()),
            "Avg_Before": avg_before,
            "Avg_After": avg_after,
            "Delta_Pct": delta_pct,
            "Tren": trend,
        })

    families = pd.DataFrame(rows).sort_values("Actual_Total", ascending=False).reset_index(drop=True)
    return families, monthly
