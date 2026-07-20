# ============================================================
# 🎨 SHARED STYLES & FORMATTERS
# ============================================================
import streamlit as st

def fmt_rp(val):
    return f"Rp {val / 1_000_000_000:,.2f} M".replace(",", "temp").replace(".", ",").replace("temp", ".")

def fmt_rp_full(val):
    """Rp penuh tanpa pembulatan ke Miliar (mis. 'Rp 1.234.567') — dipakai buat kolom tabel
    detail (Target/Order/Actual per baris) di banyak tab, beda dari fmt_rp() di atas yang
    khusus buat card ringkasan nasional (dibulatkan ke M biar angka gede tetap ringkas)."""
    return f"Rp {val:,.0f}".replace(",", ".")

def fmt_liter(val):
    return f"{val:,.0f}".replace(",", ".") + " L"

def fmt_pct(val):
    return f"{val:.1f}%".replace(".", ",")

highlight_pct = lambda val: (
    'background-color: rgba(34, 197, 94, 0.1); color: #22c55e; font-weight: bold;'
    if val >= 100
    else 'background-color: rgba(239, 68, 68, 0.1); color: #ef4444; font-weight: bold;'
)

def highlight_growth_pct(val):
    """Hijau kalau growth >=0%, merah kalau minus — beda dari highlight_pct di atas
    (threshold 100%, buat rasio Achievement/O-T/A-T) karena growth YoY center-nya di 0%."""
    color = "#10b981" if val >= 0 else "#ef4444"
    return f"color: {color}; font-weight: bold;"

highlight_growth_pct_fill = lambda val: (
    'background-color: rgba(34, 197, 94, 0.1); color: #22c55e; font-weight: bold;'
    if val >= 0
    else 'background-color: rgba(239, 68, 68, 0.1); color: #ef4444; font-weight: bold;'
)

# Fill merah kalau ketergantungan ke 1 customer >=50% dari total revenue subjek (dipakai
# tab Productivity) — threshold beda dari highlight_pct di atas (center 100%, buat Achievement).
highlight_concentration_pct = lambda val: (
    'background-color: rgba(239, 68, 68, 0.15); color: #ef4444; font-weight: bold;'
    if val >= 50
    else 'background-color: rgba(34, 197, 94, 0.08); color: #22c55e;'
)

# Fill hijau kalau Burn Rate <=3% (masih terkendali), merah kalau lebih (dipakai tab Item
# D) — kebalikan dari highlight_pct/highlight_concentration_pct: di sini MAKIN KECIL makin
# bagus (burn = uang "terbakar" dari diskon, bukan capaian yang mau dimaksimalkan). Ambang
# 3% masih percobaan awal (belum ada baseline historis), gampang diubah kalau perlu.
highlight_burn_rate_pct = lambda val: (
    'background-color: rgba(239, 68, 68, 0.1); color: #ef4444; font-weight: bold;'
    if val > 3
    else 'background-color: rgba(34, 197, 94, 0.1); color: #22c55e; font-weight: bold;'
)

CARD_STYLE = """
<style>
    .custom-card { background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 16px; }
    .card-title { color: #f59e0b; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
    .card-value { color: #f8fafc; font-size: 24px; font-weight: bold; }
    /* Varian card value sedikit lebih kecil — dipakai tab dengan card yang value-nya
       nama/teks panjang (mis. Target Customer di layar lebar), supaya tidak overflow/
       terlalu dominan, tapi tetap cukup besar biar bentuk card gak terasa kosong/jelek */
    .custom-card.card-compact .card-value { font-size: 22px; }
    .card-sub { color: #f59e0b; font-size: 11px; margin-top: 4px; opacity: 0.85; }
    [data-testid="stSidebar"] label { font-size: 16px !important; color: #f8fafc !important; font-weight: 600 !important; }
    .stTabs [data-baseweb="tab"] { font-size: 18px !important; font-weight: 600 !important; }
    .thick-divider { border: none; border-top: 4px solid #f59e0b; margin: 4px 0 20px 0; opacity: 1; }

    /* Judul tiap halaman ketutup jarak kosong bawaan Streamlit (~96px) di atas block-container */
    .stMainBlockContainer, .block-container {
        padding-top: 3rem !important;
    }

    /* Filter General — panel oranye transparan (30% opacity), pembeda dari expander/filter per-tab lain */
    [class*="st-key-general_filter_panel"] [data-testid="stExpander"] {
        background-color: rgba(245, 158, 11, 0.30);
        border: 1px solid rgba(245, 158, 11, 0.55);
        border-radius: 14px;
    }
    [class*="st-key-genfilter_tile_"] {
        background-color: rgba(255, 255, 255, 0.55);
        border: 1px solid rgba(180, 83, 9, 0.30);
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 0;
    }
    /* Gap antar baris tile (Tahun/Bulan → Area/Jenis/Kelas → Cabang) dipersempit dari
       default Streamlit 16px — dulu terasa terlalu lebar ditumpuk dengan margin tile */
    [class*="st-key-general_filter_panel"] [data-testid="stExpanderDetails"] > [data-testid="stVerticalBlock"] {
        gap: 0.625rem !important;
    }

    /* Filter General — pill/checkbox accent merah bawaan Streamlit diganti hijau tua
       (condong hitam) supaya tidak nyaru dengan background oranye panel */
    [class*="st-key-general_filter_panel"] button[data-variant="pills"][data-selected="true"] {
        color: #14532d !important;
        background-color: rgba(20, 83, 45, 0.22) !important;
        border-color: #14532d !important;
    }
    [class*="st-key-general_filter_panel"] [data-testid="stCheckbox"] label[data-selected="true"] > div:first-of-type {
        background-color: #14532d !important;
        border-color: #14532d !important;
    }

    /* Tab Pacing (Laporan Financial) punya filter Tahun/Bulan/Area/Cabang sendiri yang
       tumpang tindih dan tidak nyambung ke Filter General — panel general di-hide selama
       tab ini aktif. data-key="1" = tab ke-2 (0-indexed) di urutan tab Laporan Financial;
       discoped ke suffix "_financial" (lihat utils/filters.py) supaya tidak ikut nge-hide
       panel general di halaman lain yang urutan tab-nya beda (mis. Marketing Program). */
    .stMainBlockContainer:has([data-testid="stTab"][data-key="1"][aria-selected="true"]) [class*="st-key-general_filter_panel_financial"] {
        display: none;
    }
</style>
"""

def inject_styles():
    st.markdown(CARD_STYLE, unsafe_allow_html=True)