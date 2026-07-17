# ============================================================
# 🎨 SHARED STYLES & FORMATTERS
# ============================================================
import streamlit as st

def fmt_rp(val): 
    return f"Rp {val / 1_000_000_000:,.2f} M".replace(",", "temp").replace(".", ",").replace("temp", ".")

def fmt_liter(val): 
    return f"{val:,.0f}".replace(",", ".") + " L"

highlight_pct = lambda val: (
    'background-color: rgba(34, 197, 94, 0.1); color: #22c55e; font-weight: bold;' 
    if val >= 100 
    else 'background-color: rgba(239, 68, 68, 0.1); color: #ef4444; font-weight: bold;'
)

CARD_STYLE = """
<style>
    .custom-card { background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 16px; }
    .card-title { color: #f59e0b; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
    .card-value { color: #f8fafc; font-size: 24px; font-weight: bold; }
    .card-sub { color: #f59e0b; font-size: 11px; margin-top: 4px; opacity: 0.85; }
    [data-testid="stSidebar"] label { font-size: 16px !important; color: #f8fafc !important; font-weight: 600 !important; }
    .stTabs [data-baseweb="tab"] { font-size: 18px !important; font-weight: 600 !important; }
</style>
"""

def inject_styles():
    st.markdown(CARD_STYLE, unsafe_allow_html=True)