# ============================================================
# ⏱️ LEAD TIME & FULFILLMENT ENGINE — Link Order -> Actual (SO_No + Customer_No + Partnumber)
# ============================================================
"""
Order (SO_Date, kapan customer order) & Supply (Invoice_Date, kapan barang KELUAR GUDANG —
di-generate sistem logistik pihak ketiga H+1+, dan Qty-nya gak selalu 1:1 sama Order) itu
2 sistem terpisah yang jalan di waktu berbeda. Modul ini nyambungin keduanya PER BARIS lewat
SO_No+Customer_No+Partnumber, buat ngukur 2 metrik dari link yang sama:
  - Lead Time = Invoice_Date - SO_Date (berapa lama dari Order sampai barang keluar gudang)
  - Fulfillment Ratio = Qty_Actual / Qty_Order (seberapa penuh Qty yang dikirim vs dipesan)

Tantangan utama: Partnumber kadang disubstitusi (Order Partnumber A, disupply Partnumber B —
part-family sama, beda revisi/kode). Makanya ada fallback pass ke prefix 5-karakter Partnumber,
pola yang sama persis kayak df_7kp_prefix di data_loader.py buat kasus serupa.

Divalidasi manual sebelum dipakai: match rate Supply 2024+ ~99% (exact + prefix fallback).
Supply 2023 TIDAK BISA match SAMA SEKALI — bukan bug, murni karena data Order historis sebelum
2024 memang gak ada di sumber data ini (lihat ORDER_DIR min_year=2024 di data_loader.py).
Baris yang gak ketemu sama sekali (termasuk semua 2023) di-DROP dari hasil, bukan dipaksa isi
NaT — biar rata-rata/median Lead Time gak keracunan baris yang gak valid.
"""
import streamlit as st
import pandas as pd
import numpy as np

PREFIX_LEN = 5
STATUS_ORDER = ["Fulfill", "Fulfill Sebagian", "Belum Dikirim", "Hilang / Trace Data"]
STATUS_COLOR = {
    "Fulfill": "#10b981",
    "Fulfill Sebagian": "#f59e0b",
    "Belum Dikirim": "#3b82f6",
    "Hilang / Trace Data": "#ef4444",
}


@st.cache_data(show_spinner="Menghitung Lead Time Order -> Actual...")
def compute_order_actual_link(df_order, df_supply):
    """Return (matched_df, stats) — matched_df 1 baris per Supply yang berhasil di-link ke
    Order asalnya, stats berisi hitungan buat transparansi (berapa exact/prefix/unmatched)."""
    order = df_order[["SO_No", "Customer_No", "Partnumber", "SO_Date", "Qty"]].dropna(
        subset=["SO_No", "SO_Date"]
    ).copy()
    order["SO_No"] = order["SO_No"].astype(str).str.upper().str.strip()

    # Pass 1 lookup: SO_No+Customer_No+Partnumber PERSIS — kalau 1 SO punya beberapa baris
    # Partnumber yang sama (split qty), digabung jadi 1 (Order_Date = paling awal, Qty dijumlah).
    order_exact = order.groupby(["SO_No", "Customer_No", "Partnumber"], as_index=False).agg(
        Order_Date=("SO_Date", "min"), Qty_Order=("Qty", "sum"),
    )

    # Pass 2 lookup: fallback prefix 5-karakter Partnumber, per SO_No+Customer_No.
    order["Prefix"] = order["Partnumber"].str[:PREFIX_LEN]
    order_prefix = order.groupby(["SO_No", "Customer_No", "Prefix"], as_index=False).agg(
        Order_Date=("SO_Date", "min"), Qty_Order=("Qty", "sum"),
    )

    supply = df_supply[["SO_No", "Customer_No", "Partnumber", "Invoice_Date", "Cabang", "Qty"]].dropna(
        subset=["SO_No", "Invoice_Date"]
    ).rename(columns={"Qty": "Qty_Actual"}).copy()
    supply["SO_No"] = supply["SO_No"].astype(str).str.upper().str.strip()
    n_supply_total = len(supply)

    merged = supply.merge(order_exact, on=["SO_No", "Customer_No", "Partnumber"], how="left")
    merged["Match_Type"] = pd.NA
    merged.loc[merged["Order_Date"].notna(), "Match_Type"] = "Exact"

    need_fallback = merged["Order_Date"].isna()
    if need_fallback.any():
        fb = merged.loc[need_fallback, ["SO_No", "Customer_No", "Partnumber"]].copy()
        fb["Prefix"] = fb["Partnumber"].str[:PREFIX_LEN]
        fb = fb.merge(order_prefix, on=["SO_No", "Customer_No", "Prefix"], how="left")
        merged.loc[need_fallback, "Order_Date"] = fb["Order_Date"].values
        merged.loc[need_fallback, "Qty_Order"] = fb["Qty_Order"].values
        fallback_hit = need_fallback & merged["Order_Date"].notna()
        merged.loc[fallback_hit, "Match_Type"] = "Prefix"

    matched = merged[merged["Match_Type"].notna()].copy()
    matched["Lead_Time_Days"] = (matched["Invoice_Date"] - matched["Order_Date"]).dt.days
    matched["Tahun"] = matched["Invoice_Date"].dt.year
    matched["Bulan_Num"] = matched["Invoice_Date"].dt.month

    # Fulfillment_Ratio = seberapa besar Qty yang benar-benar dikirim dibanding yang dipesan.
    # <1 = partial (kurang stok), 1 = penuh, >1 = lebih (mis. pembulatan/kelebihan kirim).
    matched["Fulfillment_Ratio"] = matched["Qty_Actual"] / matched["Qty_Order"].replace(0, pd.NA)
    matched["Is_Partial"] = matched["Fulfillment_Ratio"] < 1

    # Lead time negatif = Actual "lebih dulu" dari Order tercatat (data quirk, mis. Order-nya
    # telat ke-input) — bukan lead time valid, dikeluarkan dari hasil biar gak nge-bias rata2.
    n_negative = int((matched["Lead_Time_Days"] < 0).sum())
    matched = matched[matched["Lead_Time_Days"] >= 0]

    stats = {
        "n_supply_total": n_supply_total,
        "n_matched": len(matched),
        "n_exact": int((matched["Match_Type"] == "Exact").sum()),
        "n_prefix": int((matched["Match_Type"] == "Prefix").sum()),
        "n_negative_excluded": n_negative,
        "n_unmatched": n_supply_total - len(matched) - n_negative,
    }
    return matched, stats


def compute_split_order_rate(linked_df):
    """% Order (SO_No+Customer_No+Partnumber) yang penyelesaiannya butuh LEBIH DARI 1 baris
    pengiriman — beda dari Partial Fulfillment Rate yang dihitung per baris pengiriman (1 Order
    yang dipecah jadi 3x kirim bakal nyumbang 3 baris "partial" ke metrik itu, padahal cuma 1
    Order yang sebenarnya dipecah). Di sini dihitung per Order asal, jadi 1 Order yang dipecah
    cuma kehitung SEKALI, gak peduli jadi berapa kali kirim.

    Grouping-nya WAJIB ikut Partnumber (bukan cuma SO_No+Customer_No+Order_Date+Qty_Order) —
    1 SO biasa punya banyak baris Partnumber BERBEDA yang kebetulan sama-sama Qty 1 (part
    lain-lain dalam 1 nota beli), dan itu BUKAN order yang dipecah, itu emang barang yang
    beda-beda. Tanpa Partnumber di key, semua baris beda part itu keitung numplek jadi
    "1 order dipecah N kali" — false positive besar-besaran.

    Konsekuensi: buat baris yang ke-link lewat fallback prefix substitusi (~1% dari data,
    lihat compute_order_actual_link), Partnumber yang tercatat di sini adalah Partnumber di
    Supply (bukan Partnumber asli Order) — kalau 1 Order disubstitusi ke 2 Partnumber pengganti
    berbeda, itu bakal kehitung sebagai 2 Order terpisah, bukan 1 Order yang dipecah. Ini
    under-count kecil di kasus langka, jauh lebih aman daripada over-count seperti di atas."""
    per_order = linked_df.groupby(["SO_No", "Customer_No", "Partnumber"]).size()
    n_orders = len(per_order)
    n_split = int((per_order > 1).sum())
    split_rate = (n_split / n_orders * 100) if n_orders else 0.0
    return n_split, n_orders, split_rate


def summarize_by_cabang(linked_df):
    """Median/P90/Mean Lead Time + jumlah baris ke-link, per Cabang — sorted TERLAMA duluan
    (paling perlu perhatian) supaya konsisten sama pola card 'Kurang Produktif' di tab lain."""
    g = linked_df.groupby("Cabang")["Lead_Time_Days"]
    summary = g.agg(
        Median_Lead_Time="median",
        P90_Lead_Time=lambda s: s.quantile(0.9),
        Mean_Lead_Time="mean",
        N_Matched="count",
    ).reset_index()
    return summary.sort_values("Median_Lead_Time", ascending=False)


def summarize_fulfillment_by_cabang(linked_df):
    """Partial Fulfillment Rate (%) + Median Fulfillment Ratio, per Cabang — sorted PALING
    SERING KURANG duluan."""
    summary = linked_df.groupby("Cabang").agg(
        Partial_Rate=("Is_Partial", "mean"),
        Median_Ratio=("Fulfillment_Ratio", "median"),
        N_Matched=("Fulfillment_Ratio", "count"),
    ).reset_index()
    summary["Partial_Rate"] = summary["Partial_Rate"] * 100
    return summary.sort_values("Partial_Rate", ascending=False)


@st.cache_data(show_spinner="Menghitung status fulfillment tiap Order...")
def compute_fulfillment_status(df_order, df_supply):
    """Klasifikasi TIAP BARIS ORDER (SO_No+Customer_No+Partnumber) ke salah satu dari 4 status:
    Fulfill, Fulfill Sebagian, Belum Dikirim, atau Hilang / Trace Data.

    Beda dari compute_order_actual_link() yang anchor dari sisi Supply (tiap baris Supply dicari
    Order asalnya), fungsi ini anchor dari sisi ORDER — supaya Order yang BELUM PERNAH ada
    Actual-nya sama sekali (bukan cuma partial) ikut kelihatan, bukan cuma yang sudah ke-link.

    Catatan akurasi: pencocokan Actual ke Order di sini HANYA exact match (SO_No+Customer_No+
    Partnumber persis) — tidak pakai fallback prefix substitusi seperti compute_order_actual_link().
    Ini sengaja disederhanakan: kasus substitusi cuma ~1% dari seluruh data (lihat validasi
    compute_order_actual_link), dan diperlukan supaya "1 baris Order = 1 Partnumber pasti" tetap
    terjaga (fallback prefix bisa menyatukan beberapa Order Partnumber berbeda yang kebetulan
    satu keluarga kode, sehingga sulit dipisah lagi per baris Order individual). Dampaknya:
    sebagian kecil Order yang sebenarnya sudah terkirim lewat produk substitusi bisa tampak
    seperti "Belum Dikirim"/"Hilang" di sini — bias ini kecil dan condong ke arah under-estimate
    fulfillment, bukan sebaliknya.

    Ambang "Hilang / Trace Data" dihitung dari P95 Lead Time histori pengiriman yang sudah
    tuntas (bukan angka tetap sembarangan) — Order yang belum ada Actual-nya sama sekali dan
    umurnya sudah melewati P95 tersebut dianggap di luar kewajaran waktu pengiriman normal.
    """
    order = df_order[["SO_No", "Customer_No", "Partnumber", "SO_Date", "Qty", "Cabang"]].dropna(
        subset=["SO_No", "SO_Date"]
    ).copy()
    for col in ("SO_No", "Customer_No", "Partnumber"):
        order[col] = order[col].astype(str).str.upper().str.strip()

    order_agg = order.groupby(["SO_No", "Customer_No", "Partnumber"], as_index=False).agg(
        Order_Date=("SO_Date", "min"), Qty_Order=("Qty", "sum"), Cabang=("Cabang", "first"),
    )

    supply = df_supply[["SO_No", "Customer_No", "Partnumber", "Qty"]].dropna(subset=["SO_No"]).copy()
    for col in ("SO_No", "Customer_No", "Partnumber"):
        supply[col] = supply[col].astype(str).str.upper().str.strip()
    supply_agg = supply.groupby(["SO_No", "Customer_No", "Partnumber"], as_index=False)["Qty"].sum()
    supply_agg = supply_agg.rename(columns={"Qty": "Qty_Actual"})

    merged = order_agg.merge(supply_agg, on=["SO_No", "Customer_No", "Partnumber"], how="left")
    merged["Qty_Actual"] = merged["Qty_Actual"].fillna(0)
    merged["Tahun"] = merged["Order_Date"].dt.year

    reference_date = max(df_order["SO_Date"].max(), df_supply["Invoice_Date"].max())
    umur_hari = (reference_date - merged["Order_Date"]).dt.days

    matched, _ = compute_order_actual_link(df_order, df_supply)
    lost_threshold = float(matched["Lead_Time_Days"].quantile(0.95)) if not matched.empty else 30.0

    conditions = [
        merged["Qty_Actual"] >= merged["Qty_Order"],
        merged["Qty_Actual"] > 0,
        umur_hari <= lost_threshold,
    ]
    merged["Status"] = np.select(conditions, STATUS_ORDER[:3], default=STATUS_ORDER[3])

    return merged, lost_threshold, reference_date


def summarize_fulfillment_by_partnumber(linked_df, min_n=5):
    """Partial Fulfillment Rate per Partnumber — buat nemuin part spesifik yang kroniknya
    kurang stok (actionable buat procurement). `min_n` = ambang minimum transaksi supaya
    Partnumber yang cuma muncul 1-2x gak nyasar ke ranking (sample kecil, gampang melenceng)."""
    summary = linked_df.groupby("Partnumber").agg(
        Partial_Rate=("Is_Partial", "mean"),
        Median_Ratio=("Fulfillment_Ratio", "median"),
        N_Matched=("Fulfillment_Ratio", "count"),
    ).reset_index()
    summary["Partial_Rate"] = summary["Partial_Rate"] * 100
    summary = summary[summary["N_Matched"] >= min_n]
    return summary.sort_values("Partial_Rate", ascending=False)
