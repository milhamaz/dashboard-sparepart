# ============================================================
# 🧮 CUSTOMER × MAT GROUP ENGINE — profil belanja kategori per customer
# ============================================================
"""
Dipakai bareng oleh tab Cross-sell Gap dan tab Diversifikasi Produk (halaman Customer) —
satu fungsi assembly supaya definisi "customer membeli kategori X" (exclude Unclassified,
net Actual > 0) gak double-maintained di dua tempat dan gampang drift kalau salah satu
diubah tanpa yang lain ikut. Pola yang sama dengan productivity_engine.py di halaman SDM.
"""
import pandas as pd
import streamlit as st


@st.cache_data(show_spinner="Menyusun profil kategori per customer...")
def build_customer_category_profile(df_linked_ty):
    """Return (cust_cat, attr).

    cust_cat — long df per Customer_No × Mat_Group dengan net Actual > 0 (pasangan yang
    net-nya <= 0, retur melebihi pembelian, dianggap TIDAK membeli kategori itu). Kategori
    Unclassified dikecualikan — bukan kategori produk sungguhan untuk dianalisis/ditawarkan.

    attr — atribut per customer (Customer_Name, Cabang, Kelas_Customer, Kode_Area) +
    N_Baris (jumlah baris transaksi, semua kategori termasuk Unclassified) buat ambang
    "Sample Kecil" di tab pemanggil.
    """
    cols = ["Customer_No", "Mat_Group", "Actual"]
    if df_linked_ty is None or df_linked_ty.empty:
        return pd.DataFrame(columns=cols), pd.DataFrame()

    scope = df_linked_ty[df_linked_ty["Mat_Group"] != "Unclassified"]
    cust_cat = scope.groupby(["Customer_No", "Mat_Group"])["Actual"].sum().reset_index()
    cust_cat = cust_cat[cust_cat["Actual"] > 0]

    attr = (
        df_linked_ty.dropna(subset=["Customer_No"])
        .drop_duplicates("Customer_No")
        [["Customer_No", "Customer_Name", "Cabang", "Kelas_Customer", "Kode_Area"]]
        .copy()
    )
    attr["Customer_Name"] = attr["Customer_Name"].astype(str).str.strip().str.upper()
    n_baris = df_linked_ty.groupby("Customer_No").size()
    attr["N_Baris"] = attr["Customer_No"].map(n_baris).fillna(0).astype(int)
    return cust_cat, attr
