# ============================================================
# ⚠️ ARCHIVED / TIDAK DIPAKAI — jangan dijalankan atau dijadikan referensi
# ============================================================
# File ini adalah versi monolitik lama sebelum di-refactor jadi struktur
# Dashboard.py + pages/ + views/ + utils/. Tidak di-import dari mana pun
# (dikonfirmasi via grep) dan TIDAK di-maintain lagi:
#   - Path data di-hardcode ke D:\Dashboard\TASTI\... (bukan lewat
#     DASHBOARD_DATA_DIR seperti utils/data_loader.py).
#   - highlight_pct di file ini punya 3 cabang (nilai negatif = tanpa
#     styling), BEDA dari versi aktif di utils/styles.py yang cuma 2
#     cabang (negatif tetap merah). Jangan disalin ke tab manapun.
#   - Tidak ada guard clause untuk kolom master TMO yang hilang, tidak
#     seperti versi views/tab_tmo.py yang sudah diperbaiki.
# Kalau butuh referensi versi single-file, cek riwayat/backup terpisah,
# bukan dari isi file ini.
# ============================================================
# 📊 DASHBOARD SPAREPART — MULTI-SHEET VERSION (UPDATED 2026)
# ============================================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="Dashboard Sparepart",
    page_icon="🚗",
    layout="wide")

OBF_FACTOR = 1.0

kamus_bulan = {
    "January": "Januari", "February": "Februari", "March": "Maret",
    "April": "April", "May": "Mei", "June": "Juni",
    "July": "Juli", "August": "Agustus", "September": "September",
    "October": "Oktober", "November": "November", "December": "Desember"
}

list_bulan_standar = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

ORDER_DIR = Path(r"D:\Dashboard\TASTI\Order")
ORDER_SKIP_COLS = [
    "Partname", "Discount", "Item_Disc", "Scp_Disc", "Sales_Net",
    "DPP", "PPN", "Total_Amount", "Group_Part", "Group_Part_Desc",
    "No_PO_Customer", "SO_Status", "Qty_Invoice", 
    "Status_Invoice", "Time_to_TPOS", "Status_SO", "Stop_Sales",
]

SUPPLY_DIR = Path(r"D:\Dashboard\TASTI\Supply")
SUPPLY_SKIP_COLS = [
    "Partname", "Discount", "Item_Disc", "Scp_Disc", "Sales_Net",
    "DPP", "PPN", "Total_Amount", "Group_Part", "Group_Part_Desc",
    "No_PO_Customer", "Item_Disc_Desc", "Base_Disc", "No_Faktur_Pajak",
    "Due_Date", "Performa_Invoice", "Cust_NPWP", "Nomor_DA",
]

CUSTOMER_FILE = Path(r"D:\Dashboard\TASTI\Customer.xlsx")
CUSTOMER_COLS = ["Kode_Customer", "Jenis_Customer", "Kelas_Customer", "Cabang", "Kode_Area"]

TARGET_FILE = Path(r"D:\Dashboard\TASTI\Tgt_Cabang.xlsx")
TARGET_COLS = ["Tahun", "Bulan_Num", "Bulan", "Code_Cabang", "Cabang", "Target"]

TMO_FILE = Path(r"D:\Dashboard\TASTI\PnoTMO.xlsx")
TOPT_FILE = Path(r"D:\Dashboard\TASTI\PnoTOPT.xlsx")

@st.cache_data
def load_and_process_data():
    def load_csvs(directory, prefix, min_year, skip_cols=None):
        dfs = []
        for file in sorted(directory.glob(f"{prefix}*.csv")):
            tahun = int(file.stem[1:3]) + 2000
            if tahun < min_year: continue
            try:
                df = pd.read_csv(file, low_memory=False, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(file, low_memory=False, encoding="latin-1")
            df.columns = df.columns.str.strip().str.replace(" ", "_")
            if skip_cols:
                df = df.drop(columns=[c for c in skip_cols if c in df.columns])
            dfs.append(df)
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    df_order = load_csvs(ORDER_DIR, "O", 2024, skip_cols=ORDER_SKIP_COLS)
    df_supply = load_csvs(SUPPLY_DIR, "S", 2023, skip_cols=SUPPLY_SKIP_COLS)

    df_customer = pd.read_excel(CUSTOMER_FILE, engine="openpyxl")
    df_customer.columns = df_customer.columns.str.strip().str.replace(" ", "_")
    df_customer = df_customer[CUSTOMER_COLS]
    df_customer["Kode_Customer"] = df_customer["Kode_Customer"].astype(str).str.upper().str.strip()

    df_target = pd.read_excel(TARGET_FILE, engine="openpyxl")
    df_target.columns = df_target.columns.str.strip().str.replace(" ", "_")
    df_target = df_target[TARGET_COLS]
    df_target["Target"] = df_target["Target"] * OBF_FACTOR

    # Helper: bersihkan nama kolom Excel (tangkap non-breaking space, tab, dll)
    clean_cols = lambda df: df.columns.str.strip().str.replace(r'\s+', '_', regex=True)

    df_tmo_lookup = pd.read_excel(TMO_FILE, engine="openpyxl")
    df_tmo_lookup.columns = clean_cols(df_tmo_lookup)
    df_tmo_lookup["Partnumber"] = df_tmo_lookup["Partnumber"].astype(str).str.strip()

    df_topt_lookup = pd.read_excel(TOPT_FILE, engine="openpyxl")
    df_topt_lookup.columns = clean_cols(df_topt_lookup)
    df_topt_lookup["Partnumber"] = df_topt_lookup["Partnumber"].astype(str).str.strip()

    df_order["Customer_No"] = df_order["Customer_No"].astype(str).str.upper().str.strip()
    df_order = pd.merge(df_order, df_customer, left_on="Customer_No", right_on="Kode_Customer", how="left").drop(columns=["Kode_Customer"])

    df_supply["Customer_No"] = df_supply["Customer_No"].astype(str).str.upper().str.strip()
    df_supply = pd.merge(df_supply, df_customer, left_on="Customer_No", right_on="Kode_Customer", how="left").drop(columns=["Kode_Customer"])

    # Olah Tanggal & Konversi ke Bahasa Indonesia
    df_order["SO_Date"] = pd.to_datetime(df_order["SO_Date"], dayfirst=True, errors="coerce")
    df_order = df_order.dropna(subset=["SO_Date"])
    df_order["Tahun"] = df_order["SO_Date"].dt.year
    df_order["Bulan_Num"] = df_order["SO_Date"].dt.month
    df_order["Bulan"] = df_order["SO_Date"].dt.strftime("%B").map(kamus_bulan).str.strip()
    df_order["Order"] = (df_order["Qty"] * df_order["Retail_Price"]) / 1.11 * OBF_FACTOR

    df_supply["Invoice_Date"] = pd.to_datetime(df_supply["Invoice_Date"], dayfirst=True, errors="coerce")
    df_supply = df_supply.dropna(subset=["Invoice_Date"])
    df_supply["Tahun"] = df_supply["Invoice_Date"].dt.year
    df_supply["Bulan_Num"] = df_supply["Invoice_Date"].dt.month
    df_supply["Bulan"] = df_supply["Invoice_Date"].dt.strftime("%B").map(kamus_bulan).str.strip()
    df_supply["Actual"] = (df_supply["Qty"] * df_supply["Retail_Price"]) / 1.11 * OBF_FACTOR

    df_target["Bulan"] = df_target["Bulan"].astype(str).str.strip().str.capitalize().map(kamus_bulan).fillna(df_target["Bulan"]).str.strip()

    df_order = pd.merge(df_order, df_target, on=["Tahun", "Bulan_Num", "Bulan", "Cabang"], how="left")
    df_supply = pd.merge(df_supply, df_target, on=["Tahun", "Bulan_Num", "Bulan", "Cabang"], how="left")

    for df in [df_order, df_supply]:
        if "SO_Type" not in df.columns:
            df["SO_Type"] = None
        df["SO_Type"] = df["SO_Type"].astype(str).str.strip().replace(["nan", "None", ""], None)
        
        if "Campaign_Code" in df.columns:
            mask_blank = df["SO_Type"].isna()
            mask_has_camp = df["Campaign_Code"].notna() & (df["Campaign_Code"].astype(str).str.strip() != "")
            df.loc[mask_blank & mask_has_camp, "SO_Type"] = "C"
            df.loc[mask_blank & ~mask_has_camp, "SO_Type"] = "3"
        else:
            df["SO_Type"] = df["SO_Type"].fillna("3")

    def find_pno_col(df):
        for col in ["Partnumber", "Part_No", "Part_Number", "PartNumber"]:
            if col in df.columns: return col
        return None

    pno_col_order, pno_col_supply = find_pno_col(df_order), find_pno_col(df_supply)
    if pno_col_order and pno_col_order != "Partnumber": df_order = df_order.rename(columns={pno_col_order: "Partnumber"})
    if pno_col_supply and pno_col_supply != "Partnumber": df_supply = df_supply.rename(columns={pno_col_supply: "Partnumber"})
    
    if "Partnumber" in df_order.columns: df_order["Partnumber"] = df_order["Partnumber"].astype(str).str.strip()
    if "Partnumber" in df_supply.columns: df_supply["Partnumber"] = df_supply["Partnumber"].astype(str).str.strip()

    return df_order, df_supply, df_target, df_tmo_lookup, df_topt_lookup

df_order, df_supply, df_target, df_tmo_lookup, df_topt_lookup = load_and_process_data()

# ============================================================
# SIDEBAR FILTER (GLOBAL)
# ============================================================
st.markdown(
    '<h1 style="color: white; text-align: center; font-size: 24px;">⚙️ Dashboard Sparepart 🔩</h1>', 
    unsafe_allow_html=True
)

st.sidebar.markdown("### 🎛️ Filter General")

tahun_list = sorted(df_order["Tahun"].dropna().unique())
pilih_tahun = st.sidebar.selectbox("📅 Tahun", tahun_list, index=len(tahun_list) - 1)
pilih_bulan = st.sidebar.multiselect("📆 Bulan", list_bulan_standar, default=list_bulan_standar)

area_list = sorted(df_order["Kode_Area"].dropna().unique())
pilih_area = st.sidebar.multiselect("🌐 Area Operation", area_list, default=area_list)

mask_base_order = (df_order["Tahun"] == pilih_tahun) & (df_order["Bulan"].isin(pilih_bulan)) & (df_order["Kode_Area"].isin(pilih_area))
mask_base_supply = (df_supply["Tahun"].isin([pilih_tahun, pilih_tahun - 1])) & (df_supply["Bulan"].isin(pilih_bulan)) & (df_supply["Kode_Area"].isin(pilih_area))

df_order_f1 = df_order[mask_base_order]
df_supply_f1 = df_supply[mask_base_supply]

cabang_list = sorted(df_order_f1["Cabang"].dropna().unique())
pilih_cabang = st.sidebar.multiselect("🏢 Cabang", cabang_list, default=cabang_list)

df_order_f2 = df_order_f1[df_order_f1["Cabang"].isin(pilih_cabang)]
df_supply_f2 = df_supply_f1[df_supply_f1["Cabang"].isin(pilih_cabang)]

jenis_list = sorted(df_order_f2["Jenis_Customer"].dropna().unique())
pilih_jenis = st.sidebar.multiselect("👤 Jenis Customer", jenis_list, default=jenis_list)

kelas_list = sorted(df_order_f2[df_order_f2["Jenis_Customer"].isin(pilih_jenis)]["Kelas_Customer"].dropna().unique())
pilih_kelas = st.sidebar.multiselect("⭐ Kelas Customer", kelas_list, default=kelas_list)

st.sidebar.divider()
st.sidebar.caption("✨ Built with Streamlit + Plotly | Updated (2026)")

mask_cust = lambda df: (df["Jenis_Customer"].isin(pilih_jenis)) & (df["Kelas_Customer"].isin(pilih_kelas))
df_order_final = df_order_f2[mask_cust(df_order_f2)].copy()
df_supply_final = df_supply_f2[mask_cust(df_supply_f2)].copy()

# ============================================================
# STYLES & HELPER
# ============================================================
def fmt_rp(val): return f"Rp {val / 1_000_000_000:,.2f} M".replace(",", "temp").replace(".", ",").replace("temp", ".")
def fmt_liter(val): return f"{val:,.0f}".replace(",", ".") + " L"

card_style = """
<style>
    .custom-card { background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 16px; }
    .card-title { color: #f59e0b; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
    .card-value { color: #f8fafc; font-size: 24px; font-weight: bold; }
    .card-sub { color: #f59e0b; font-size: 11px; margin-top: 4px; opacity: 0.85; }
    [data-testid="stSidebar"] label { font-size: 16px !important; color: #f8fafc !important; font-weight: 600 !important; }
    .stTabs [data-baseweb="tab"] { font-size: 18px !important; font-weight: 600 !important; }
</style>
"""
st.markdown(card_style, unsafe_allow_html=True)

# Tambah satu tab lagi bernama T-OPT
tab_performance, tab_tmo, tab_topt = st.tabs(["📊 Performance", "🛢️ TMO", "🔧 T-OPT"])

highlight_pct = lambda val: 'background-color: rgba(34, 197, 94, 0.1); color: #22c55e; font-weight: bold;' if val >= 100 else ('background-color: rgba(239, 68, 68, 0.1); color: #ef4444; font-weight: bold;' if val >= 0 else '')

# ████████████████████████████████████████████████████████████
# TAB 1: PERFORMANCE
# ████████████████████████████████████████████████████████████
with tab_performance:
    m_order = df_order_final.groupby(["Bulan_Num", "Bulan"])["Order"].sum().reset_index()
    m_actual = df_supply_final[df_supply_final["Tahun"] == pilih_tahun].groupby(["Bulan_Num", "Bulan"])["Actual"].sum().reset_index()
    m_lastyear = df_supply_final[df_supply_final["Tahun"] == pilih_tahun - 1].groupby(["Bulan_Num", "Bulan"])["Actual"].sum().reset_index().rename(columns={"Actual": "Last_Year"})
    
    df_target_filtered = df_target[(df_target["Tahun"] == pilih_tahun) & (df_target["Bulan"].isin(pilih_bulan)) & (df_target["Cabang"].isin(pilih_cabang))].copy()
    m_target = df_target_filtered.groupby(["Bulan_Num", "Bulan"])["Target"].sum().reset_index()

    monthly = m_lastyear.merge(m_target, on=["Bulan_Num", "Bulan"], how="outer")\
                        .merge(m_order, on=["Bulan_Num", "Bulan"], how="outer")\
                        .merge(m_actual, on=["Bulan_Num", "Bulan"], how="outer").fillna(0)
    monthly["Bulan_Num"] = monthly["Bulan_Num"].astype(int)
    monthly = monthly.sort_values("Bulan_Num")

    monthly["O/T"] = (monthly["Order"] / monthly["Target"] * 100).fillna(0).replace([float('inf'), -float('inf')], 0)
    monthly["A/T"] = (monthly["Actual"] / monthly["Target"] * 100).fillna(0).replace([float('inf'), -float('inf')], 0)
    monthly["A/LY"] = (monthly["Actual"] / monthly["Last_Year"] * 100).fillna(0).replace([float('inf'), -float('inf')], 0)

    total_order = monthly["Order"].sum()
    total_actual = monthly["Actual"].sum()
    total_ly = monthly["Last_Year"].sum()
    yoy_growth = ((total_actual / total_ly - 1) * 100) if total_ly > 0 else 0

    pembagi_order = (monthly["Order"] > 0).sum()
    pembagi_actual = (monthly["Actual"] > 0).sum()
    avg_order = (total_order / pembagi_order) if pembagi_order > 0 else 0
    avg_actual = (total_actual / pembagi_actual) if pembagi_actual > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f'<div class="custom-card"><div class="card-title">💰 Total Order</div><div class="card-value">{fmt_rp(total_order)}</div><div class="card-sub">Avg: {fmt_rp(avg_order)}/bln</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="custom-card"><div class="card-title">🚚 Total Actual</div><div class="card-value">{fmt_rp(total_actual)}</div><div class="card-sub">Avg: {fmt_rp(avg_actual)}/bln</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="custom-card"><div class="card-title">📅 Last Year</div><div class="card-value">{fmt_rp(total_ly)}</div><div class="card-sub">Tahun {pilih_tahun - 1}</div></div>', unsafe_allow_html=True)
    with col4:
        yoy_color = "#10b981" if yoy_growth >= 0 else "#ef4444"
        yoy_arrow = "▲" if yoy_growth >= 0 else "▼"
        st.markdown(f'<div class="custom-card"><div class="card-title">📈 YoY Growth</div><div class="card-value" style="color:{yoy_color}">{yoy_arrow} {yoy_growth:+.1f}%</div><div class="card-sub">Actual vs {pilih_tahun - 1}</div></div>', unsafe_allow_html=True)

    fig = go.Figure()
    format_rupiah_list = lambda series: [f"Rp{v:,.0f}".replace(",", ".") if pd.notnull(v) else "Rp0" for v in series]

    for data_col, name, thn_hover, color in [("Last_Year", f"Last Year ({pilih_tahun - 1})", pilih_tahun - 1, "#e11d48"), ("Target", "Target", pilih_tahun, "#f59e0b"), ("Order", "Order", pilih_tahun, "#2563eb"), ("Actual", "Actual", pilih_tahun, "#10b981")]:
        fig.add_trace(go.Bar(
            x=monthly["Bulan"], y=monthly[data_col], name=name, marker_color=color,
            customdata=format_rupiah_list(monthly[data_col]),
            hovertemplate=f"<b>%{{x}}:</b><br>%{{customdata}}<br><extra><b>{name if 'Last Year' in name else f'{name} ({thn_hover})'}</b></extra>",
            text=[f"{v / 1_000_000_000:,.2f}M" for v in monthly[data_col]],
            textposition="outside", textangle=-90, textfont=dict(size=14, color="#ffffff"),
        ))

    fig.update_layout(
        barmode="group", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=580, separators=",.",
        yaxis=dict(title=dict(text="Revenue (Rp)", font=dict(color="white", size=17)), tickfont=dict(color="white", size=15), gridcolor="#333333"),
        xaxis=dict(tickfont=dict(color="white", size=15), categoryorder="array", categoryarray=list_bulan_standar),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, font=dict(color="white", size=15)),
        hoverlabel=dict(bgcolor="#1e293b", font_color="white", font_size=13)
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 Detail Data"):
        display = monthly[["Bulan_Num", "Bulan", "Last_Year", "Target", "Order", "Actual", "O/T", "A/T", "A/LY"]].copy().rename(columns={"Bulan_Num": "Bulan Ke-", "Last_Year": "Last Year"})
        styled = display.style.map(highlight_pct, subset=['O/T', 'A/T', 'A/LY']).format({'O/T': '{:.2f}%', 'A/T': '{:.2f}%', 'A/LY': '{:.2f}%', 'Last Year': lambda x: f"Rp {x:,.0f}".replace(",", "."), 'Target': lambda x: f"Rp {x:,.0f}".replace(",", "."), 'Order': lambda x: f"Rp {x:,.0f}".replace(",", "."), 'Actual': lambda x: f"Rp {x:,.0f}".replace(",", "."), 'Bulan Ke-': '{:.0f}'})
        st.dataframe(styled, hide_index=True, use_container_width=True, height=460)


# ████████████████████████████████████████████████████████████
# TAB 2: TMO (DENGAN TAMBAHAN FILTER SO TYPE & KARTU CAMPAIGN)
# ████████████████████████████████████████████████████████████
with tab_tmo:
    tmo_cols = ["Partnumber", "Partname", "Liter", "Jenis"]

    df_ord_tmo_base = pd.merge(df_order_final, df_tmo_lookup[tmo_cols], on="Partnumber", how="inner") if "Partnumber" in df_order_final.columns else pd.DataFrame()
    if not df_ord_tmo_base.empty: df_ord_tmo_base["Volume"] = df_ord_tmo_base["Qty"] * df_ord_tmo_base["Liter"] * OBF_FACTOR

    df_sup_tmo_base = pd.merge(df_supply_final[df_supply_final["Tahun"] == pilih_tahun], df_tmo_lookup[tmo_cols], on="Partnumber", how="inner") if "Partnumber" in df_supply_final.columns else pd.DataFrame()
    if not df_sup_tmo_base.empty: df_sup_tmo_base["Volume"] = df_sup_tmo_base["Qty"] * df_sup_tmo_base["Liter"] * OBF_FACTOR

    df_ly_tmo_base = pd.merge(df_supply_final[df_supply_final["Tahun"] == pilih_tahun - 1], df_tmo_lookup[tmo_cols], on="Partnumber", how="inner") if "Partnumber" in df_supply_final.columns else pd.DataFrame()
    if not df_ly_tmo_base.empty: df_ly_tmo_base["Volume"] = df_ly_tmo_base["Qty"] * df_ly_tmo_base["Liter"] * OBF_FACTOR

    col_f_tmo1, col_f_tmo2 = st.columns(2)
    with col_f_tmo1:
        all_jenis = sorted(set((df_ord_tmo_base["Jenis"].dropna().unique().tolist() if len(df_ord_tmo_base) else []) + (df_sup_tmo_base["Jenis"].dropna().unique().tolist() if len(df_sup_tmo_base) else []) + (df_ly_tmo_base["Jenis"].dropna().unique().tolist() if len(df_ly_tmo_base) else [])))
        pilih_jenis_tmo = st.multiselect("🏷️ Filter Jenis TMO", all_jenis, default=all_jenis, key="tmo_jenis_filter")
        
    with col_f_tmo2:
        kamus_so_type = {"C": "SO Campaign (C)", "3": "SO Non Campaign (3)"}
        all_so_types = sorted(set((df_ord_tmo_base["SO_Type"].dropna().unique().tolist() if len(df_ord_tmo_base) else []) + (df_sup_tmo_base["SO_Type"].dropna().unique().tolist() if len(df_sup_tmo_base) else [])))
        pilih_so_type_raw = st.multiselect("🎁 Filter SO Type (Diskon)", all_so_types, default=all_so_types, format_func=lambda x: kamus_so_type.get(x, x), key="tmo_so_type_filter")

    def filter_tmo_data(df):
        if df.empty: return df
        mask = df["Jenis"].isin(pilih_jenis_tmo)
        if "SO_Type" in df.columns:
            mask = mask & df["SO_Type"].isin(pilih_so_type_raw)
        return df[mask]

    df_ord_tmo = filter_tmo_data(df_ord_tmo_base)
    df_sup_tmo = filter_tmo_data(df_sup_tmo_base)
    df_ly_tmo = filter_tmo_data(df_ly_tmo_base)

    def agg_tmo_total(df):
        if df.empty: return pd.DataFrame(columns=["Bulan_Num", "Bulan", "Volume"])
        return df.groupby(["Bulan_Num", "Bulan"])["Volume"].sum().reset_index()

    m_ord_tmo = agg_tmo_total(df_ord_tmo)
    m_sup_tmo = agg_tmo_total(df_sup_tmo)
    m_ly_tmo = agg_tmo_total(df_ly_tmo)

    total_vol_order = df_ord_tmo["Volume"].sum() if len(df_ord_tmo) else 0
    total_vol_supply = df_sup_tmo["Volume"].sum() if len(df_sup_tmo) else 0
    total_vol_ly = df_ly_tmo["Volume"].sum() if len(df_ly_tmo) else 0
    yoy_vol = ((total_vol_supply / total_vol_ly - 1) * 100) if total_vol_ly > 0 else 0

    pembagi_v_ord = (m_ord_tmo["Volume"] > 0).sum() if not m_ord_tmo.empty else 0
    pembagi_v_sup = (m_sup_tmo["Volume"] > 0).sum() if not m_sup_tmo.empty else 0
    avg_v_order = (total_vol_order / pembagi_v_ord) if pembagi_v_ord > 0 else 0
    avg_v_supply = (total_vol_supply / pembagi_v_sup) if pembagi_v_sup > 0 else 0

    vol_so_campaign = df_ord_tmo[df_ord_tmo["SO_Type"] == "C"]["Volume"].sum() if len(df_ord_tmo) else 0
    vol_so_non_campaign = df_ord_tmo[df_ord_tmo["SO_Type"] == "3"]["Volume"].sum() if len(df_ord_tmo) else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="custom-card"><div class="card-title">📦 Vol. Order</div><div class="card-value">{fmt_liter(total_vol_order)}</div><div class="card-sub">Avg: {fmt_liter(avg_v_order)}/bln</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="custom-card"><div class="card-title">🚚 Vol. Supply</div><div class="card-value">{fmt_liter(total_vol_supply)}</div><div class="card-sub">Avg: {fmt_liter(avg_v_supply)}/bln</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="custom-card"><div class="card-title">📅 Last Year</div><div class="card-value">{fmt_liter(total_vol_ly)}</div><div class="card-sub">Tahun {pilih_tahun - 1}</div></div>', unsafe_allow_html=True)
    with c4:
        yoy_vol_color = "#10b981" if yoy_vol >= 0 else "#ef4444"
        yoy_vol_arrow = "▲" if yoy_vol >= 0 else "▼"
        st.markdown(f'<div class="custom-card"><div class="card-title">📈 YoY Volume</div><div class="card-value" style="color:{yoy_vol_color}">{yoy_vol_arrow} {yoy_vol:+.1f}%</div><div class="card-sub">Supply vs {pilih_tahun - 1}</div></div>', unsafe_allow_html=True)

    c_sub1, c_sub2 = st.columns(2)
    with c_sub1: 
        st.markdown(f'<div class="custom-card" style="border-left: 5px solid #2563eb;"><div class="card-title">🎁 Vol. SO Campaign (Tipe C)</div><div class="card-value">{fmt_liter(vol_so_campaign)}</div><div class="card-sub">Total order dengan program diskon</div></div>', unsafe_allow_html=True)
    with c_sub2: 
        st.markdown(f'<div class="custom-card" style="border-left: 5px solid #f59e0b;"><div class="card-title">🛒 Vol. SO Non Campaign (Tipe 3)</div><div class="card-value">{fmt_liter(vol_so_non_campaign)}</div><div class="card-sub">Total order regular / normal price</div></div>', unsafe_allow_html=True)

    ly_vals = [m_ly_tmo[m_ly_tmo["Bulan"] == b]["Volume"].values[0] if len(m_ly_tmo[m_ly_tmo["Bulan"] == b]) else 0 for b in pilih_bulan]
    ord_vals = [m_ord_tmo[m_ord_tmo["Bulan"] == b]["Volume"].values[0] if len(m_ord_tmo[m_ord_tmo["Bulan"] == b]) else 0 for b in pilih_bulan]
    sup_vals = [m_sup_tmo[m_sup_tmo["Bulan"] == b]["Volume"].values[0] if len(m_sup_tmo[m_sup_tmo["Bulan"] == b]) else 0 for b in pilih_bulan]

    format_liter_list = lambda series: [f"{v:,.0f}".replace(",", ".") + " L" if v else "0 L" for v in series]
    fig_tmo = go.Figure()

    for vals, name, thn_hover, color in [(ly_vals, f"Last Year ({pilih_tahun - 1})", pilih_tahun - 1, "#e11d48"), (ord_vals, "Order", pilih_tahun, "#2563eb"), (sup_vals, "Supply", pilih_tahun, "#10b981")]:
        fig_tmo.add_trace(go.Bar(
            x=pilih_bulan, y=vals, name=name, marker_color=color,
            customdata=format_liter_list(vals),
            hovertemplate=f"<b>%{{x}}:</b><br>%{{customdata}}<br><extra><b>{name if 'Last Year' in name else f'{name} ({thn_hover})'}</b></extra>",
            text=[f"{v:,.0f}".replace(",", ".") for v in vals],
            textposition="outside", textangle=-90, textfont=dict(size=14, color="#ffffff"),
        ))

    fig_tmo.update_layout(
        barmode="group", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=580,
        yaxis=dict(title=dict(text="Volume (Liter)", font=dict(color="white", size=17)), tickfont=dict(color="white", size=15), gridcolor="#333333"),
        xaxis=dict(tickfont=dict(color="white", size=15), categoryorder="array", categoryarray=list_bulan_standar),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, font=dict(color="white", size=15)),
        hoverlabel=dict(bgcolor="#1e293b", font_color="white", font_size=13)
    )
    st.plotly_chart(fig_tmo, use_container_width=True)

    with st.expander("📋 Detail Volume TMO"):
        p_ly = m_ly_tmo.rename(columns={"Volume": "Last_Year"})
        p_ord = m_ord_tmo.rename(columns={"Volume": "Vol_Order"})
        p_sup = m_sup_tmo.rename(columns={"Volume": "Vol_Supply"})
        
        if not p_ord.empty or not p_sup.empty or not p_ly.empty:
            tmo_detail = p_ly.merge(p_ord, on=["Bulan_Num", "Bulan"], how="outer").merge(p_sup, on=["Bulan_Num", "Bulan"], how="outer").fillna(0)
            tmo_detail["Bulan_Num"] = tmo_detail["Bulan_Num"].astype(int)
            tmo_detail = tmo_detail[tmo_detail["Bulan"].isin(pilih_bulan)].sort_values("Bulan_Num")
            tmo_detail["A/LY"] = (tmo_detail["Vol_Supply"] / tmo_detail["Last_Year"] * 100).fillna(0).replace([float('inf'), -float('inf')], 0)

            tmo_display = tmo_detail.rename(columns={"Bulan_Num": "Bulan Ke-", "Last_Year": "Last Year (L)", "Vol_Order": "Order (L)", "Vol_Supply": "Supply (L)", "A/LY": "A/LY (%)"})
            styled_tmo = tmo_display.style.map(highlight_pct, subset=["A/LY (%)"]).format({"Bulan Ke-": "{:.0f}", "Last Year (L)": lambda x: f"{x:,.0f}".replace(",", "."), "Order (L)": lambda x: f"{x:,.0f}".replace(",", "."), "Supply (L)": lambda x: f"{x:,.0f}".replace(",", "."), "A/LY (%)": "{:.2f}%"})
            st.dataframe(styled_tmo, hide_index=True, use_container_width=True, height=460)
        else:
            st.info("Tidak ada data TMO untuk filter yang dipilih.")


# ████████████████████████████████████████████████████████████
# TAB 3: T-OPT (NEW GENERATED SHEET)
# ████████████████████████████████████████████████████████████
with tab_topt:
    topt_cols = ["Partnumber", "Partname", "Step", "Kategori"]

    # Diagnostic: kalau kolom ga ketemu, tampilkan nama kolom asli dari Excel
    missing_topt = [c for c in topt_cols if c not in df_topt_lookup.columns]
    if missing_topt:
        st.error(f"⚠️ PnoTOPT.xlsx: kolom {missing_topt} tidak ditemukan. Kolom yang terdeteksi: {df_topt_lookup.columns.tolist()}")
        st.stop()

    # 1. Gabungkan dengan file Master Lookup
    df_ord_topt_base = pd.merge(df_order_final, df_topt_lookup[topt_cols], on="Partnumber", how="inner") if "Partnumber" in df_order_final.columns else pd.DataFrame()
    df_sup_topt_base = pd.merge(df_supply_final[df_supply_final["Tahun"] == pilih_tahun], df_topt_lookup[topt_cols], on="Partnumber", how="inner") if "Partnumber" in df_supply_final.columns else pd.DataFrame()
    df_ly_topt_base = pd.merge(df_supply_final[df_supply_final["Tahun"] == pilih_tahun - 1], df_topt_lookup[topt_cols], on="Partnumber", how="inner") if "Partnumber" in df_supply_final.columns else pd.DataFrame()

    # 2. KOMPONEN FILTER INTERN TAB T-OPT (Step & Kategori)
    col_f_topt1, col_f_topt2 = st.columns([1, 3])
    
    with col_f_topt1:
        all_step = sorted(set(
            (df_ord_topt_base["Step"].dropna().unique().tolist() if len(df_ord_topt_base) else []) +
            (df_sup_topt_base["Step"].dropna().unique().tolist() if len(df_sup_topt_base) else []) +
            (df_ly_topt_base["Step"].dropna().unique().tolist() if len(df_ly_topt_base) else [])
        ))
        pilih_step = st.multiselect("🪜 Filter Step", all_step, default=all_step, key="topt_step_filter")
        
    with col_f_topt2:
        all_kategori = sorted(set(
            (df_ord_topt_base["Kategori"].dropna().unique().tolist() if len(df_ord_topt_base) else []) +
            (df_sup_topt_base["Kategori"].dropna().unique().tolist() if len(df_sup_topt_base) else []) +
            (df_ly_topt_base["Kategori"].dropna().unique().tolist() if len(df_ly_topt_base) else [])
        ))
        pilih_kategori = st.multiselect("🗂️ Filter Kategori", all_kategori, default=all_kategori, key="topt_kategori_filter")

    # 3. Fungsi Eksekusi Filter Internal ke Kedua Data sekaligus
    def filter_topt_data(df):
        if df.empty: return df
        return df[df["Step"].isin(pilih_step) & df["Kategori"].isin(pilih_kategori)]

    df_ord_topt = filter_topt_data(df_ord_topt_base)
    df_sup_topt = filter_topt_data(df_sup_topt_base)
    df_ly_topt = filter_topt_data(df_ly_topt_base)

    # 4. Agregasi data bulanan (Nilai Berbasis Rupiah Revenue)
    m_ord_topt = df_ord_topt.groupby(["Bulan_Num", "Bulan"])["Order"].sum().reset_index() if not df_ord_topt.empty else pd.DataFrame(columns=["Bulan_Num", "Bulan", "Order"])
    m_sup_topt = df_sup_topt.groupby(["Bulan_Num", "Bulan"])["Actual"].sum().reset_index() if not df_sup_topt.empty else pd.DataFrame(columns=["Bulan_Num", "Bulan", "Actual"])
    m_ly_topt = df_ly_topt.groupby(["Bulan_Num", "Bulan"])["Actual"].sum().reset_index().rename(columns={"Actual": "Last_Year"}) if not df_ly_topt.empty else pd.DataFrame(columns=["Bulan_Num", "Bulan", "Last_Year"])

    # 5. Nilai Total untuk Card Metrik
    total_topt_order = df_ord_topt["Order"].sum() if len(df_ord_topt) else 0
    total_topt_actual = df_sup_topt["Actual"].sum() if len(df_sup_topt) else 0
    total_topt_ly = df_ly_topt["Actual"].sum() if len(df_ly_topt) else 0

    # 🛠️ Logika Tricky Penanganan Growth yang Bolong-bolong
    if total_topt_ly == 0 and total_topt_actual > 0:
        topt_growth = 100.0  # Set otomatis 100% jika tahun lalu ga ada orderan
    elif total_topt_ly == 0 and total_topt_actual == 0:
        topt_growth = 0.0
    else:
        topt_growth = ((total_topt_actual / total_topt_ly) - 1) * 100

    pembagi_topt_ord = (m_ord_topt["Order"] > 0).sum() if not m_ord_topt.empty else 0
    pembagi_topt_sup = (m_sup_topt["Actual"] > 0).sum() if not m_sup_topt.empty else 0
    avg_topt_order = (total_topt_order / pembagi_topt_ord) if pembagi_topt_ord > 0 else 0
    avg_topt_actual = (total_topt_actual / pembagi_topt_sup) if pembagi_topt_sup > 0 else 0

    # 6. Menampilkan Card Performance ala Request-an
    ct1, ct2, ct3, ct4 = st.columns(4)
    with ct1: st.markdown(f'<div class="custom-card"><div class="card-title">💰 Order Actual</div><div class="card-value">{fmt_rp(total_topt_order)}</div><div class="card-sub">Avg: {fmt_rp(avg_topt_order)}/bln</div></div>', unsafe_allow_html=True)
    with ct2: st.markdown(f'<div class="custom-card"><div class="card-title">🚚 Supply Actual</div><div class="card-value">{fmt_rp(total_topt_actual)}</div><div class="card-sub">Avg: {fmt_rp(avg_topt_actual)}/bln</div></div>', unsafe_allow_html=True)
    with ct3: st.markdown(f'<div class="custom-card"><div class="card-title">📅 Last Year</div><div class="card-value">{fmt_rp(total_topt_ly)}</div><div class="card-sub">Tahun {pilih_tahun - 1}</div></div>', unsafe_allow_html=True)
    with ct4:
        topt_yoy_color = "#10b981" if topt_growth >= 0 else "#ef4444"
        topt_yoy_arrow = "▲" if topt_growth >= 0 else "▼"
        st.markdown(f'<div class="custom-card"><div class="card-title">📈 Growth</div><div class="card-value" style="color:{topt_yoy_color}">{topt_yoy_arrow} {topt_growth:+.1f}%</div><div class="card-sub">Supply vs {pilih_tahun - 1}</div></div>', unsafe_allow_html=True)

    # 7. Grafik Bar T-OPT
    topt_ly_vals = [m_ly_topt[m_ly_topt["Bulan"] == b]["Last_Year"].values[0] if len(m_ly_topt[m_ly_topt["Bulan"] == b]) else 0 for b in pilih_bulan]
    topt_ord_vals = [m_ord_topt[m_ord_topt["Bulan"] == b]["Order"].values[0] if len(m_ord_topt[m_ord_topt["Bulan"] == b]) else 0 for b in pilih_bulan]
    topt_sup_vals = [m_sup_topt[m_sup_topt["Bulan"] == b]["Actual"].values[0] if len(m_sup_topt[m_sup_topt["Bulan"] == b]) else 0 for b in pilih_bulan]

    format_topt_rp_list = lambda series: [f"Rp{v:,.0f}".replace(",", ".") if v else "Rp0" for v in series]
    fig_topt = go.Figure()

    for vals, name, thn_hover, color in [(topt_ly_vals, f"Last Year ({pilih_tahun - 1})", pilih_tahun - 1, "#e11d48"), (topt_ord_vals, "Order", pilih_tahun, "#2563eb"), (topt_sup_vals, "Supply", pilih_tahun, "#10b981")]:
        fig_topt.add_trace(go.Bar(
            x=pilih_bulan, y=vals, name=name, marker_color=color,
            customdata=format_topt_rp_list(vals),
            hovertemplate=f"<b>%{{x}}:</b><br>%{{customdata}}<br><extra><b>{name if 'Last Year' in name else f'{name} ({thn_hover})'}</b></extra>",
            text=[f"{v / 1_000_000:,.1f}M" if v else "0M" for v in vals],
            textposition="outside", textangle=-90, textfont=dict(size=14, color="#ffffff"),
        ))

    fig_topt.update_layout(
        barmode="group", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=580, separators=",.",
        yaxis=dict(title=dict(text="Revenue (Rp)", font=dict(color="white", size=17)), tickfont=dict(color="white", size=15), gridcolor="#333333"),
        xaxis=dict(tickfont=dict(color="white", size=15), categoryorder="array", categoryarray=list_bulan_standar),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, font=dict(color="white", size=15)),
        hoverlabel=dict(bgcolor="#1e293b", font_color="white", font_size=13)
    )
    st.plotly_chart(fig_topt, use_container_width=True)

    # 8. Tabel Detail Data T-OPT dengan styling
    with st.expander("📋 Detail Data T-OPT"):
        if not m_ord_topt.empty or not m_sup_topt.empty or not m_ly_topt.empty:
            topt_detail = m_ly_topt.merge(m_ord_topt, on=["Bulan_Num", "Bulan"], how="outer").merge(m_sup_topt, on=["Bulan_Num", "Bulan"], how="outer").fillna(0)
            topt_detail["Bulan_Num"] = topt_detail["Bulan_Num"].astype(int)
            topt_detail = topt_detail[topt_detail["Bulan"].isin(pilih_bulan)].sort_values("Bulan_Num")
            
            # Logika growth baris bulanan agar aman dari pembagian dengan 0
            def hitung_growth_row(row):
                ly = row["Last_Year"]
                act = row["Actual"]
                if ly == 0 and act > 0: return 100.0
                if ly == 0 and act == 0: return 0.0
                return ((act / ly) - 1) * 100

            topt_detail["Growth (%)"] = topt_detail.apply(hitung_growth_row, axis=1)

            topt_display = topt_detail.rename(columns={"Bulan_Num": "Bulan Ke-", "Last_Year": "Last Year", "Order": "Order Actual", "Actual": "Supply Actual"})
            styled_topt = topt_display.style.map(highlight_pct, subset=["Growth (%)"]).format({
                "Bulan Ke-": "{:.0f}", 
                "Last Year": lambda x: f"Rp {x:,.0f}".replace(",", "."), 
                "Order Actual": lambda x: f"Rp {x:,.0f}".replace(",", "."), 
                "Supply Actual": lambda x: f"Rp {x:,.0f}".replace(",", "."), 
                "Growth (%)": "{:.2f}%"
            })
            st.dataframe(styled_topt, hide_index=True, use_container_width=True, height=460)
        else:
            st.info("Tidak ada data T-OPT untuk filter yang dipilih.")