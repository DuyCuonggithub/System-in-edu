# tư duy app 
# Udemy Analytics Dashboard  –  Streamlit App
# Pages: Overview  |  Best Courses  |  Price Tracker
# 
# Khởi động app:
# cd "C:/Dai_hoc_kinh_te/de_an/Udemy ( end )/project/Web"
# streamlit run Web.py



import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Udemy Analytics Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# INITIALIZATION & STATE
# ─────────────────────────────────────────────────────────────────────────────
load_dotenv(override=True)

# Pre-initialize session state defaults for filters
filter_keys = ["f_cat", "f_tier", "f_lvl", "f_rat", "f_pub", "f_price_type", "f_tracker_cat"]
for key in filter_keys:
    if key not in st.session_state:
        st.session_state[key] = "All"

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ---------- Font ---------- */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

html, body, [class*="css"], .stApp,
h1,h2,h3,h4,h5,h6,p,div,span,label,
button, .stMarkdown, .stDataFrame,
.stSelectbox, .stMultiSelect, .stRadio {
    font-family: 'Outfit', sans-serif !important;
}

/* ---------- Palette (50% White, 30% Purple, 20% Black) ---------- */
:root {
    --ud-white:    #FFFFFF; /* 50% - Main App Background */
    --ud-purple:   #A435F0; /* 30% - Sidebar & Headers */
    --ud-purple-l: #cf8bf7;
    --ud-purple-s: rgba(164, 53, 240, 0.08);
    --ud-black:    #1C1D1F; /* 20% - Text & Structure */
    --ud-grey-l:   #F7F9FA;
    --ud-border:   #E4E8EB;
    --ud-text:     #1C1D1F;
    --ud-muted:    #6A6F73;
    --shadow:      0 2px 8px rgba(0,0,0,0.08);
}

/* ---------- App background ---------- */
.stApp { 
    background: var(--ud-white) !important; 
    color: var(--ud-text) !important;
}

/* ---------- Sidebar (30% Accent Area) ---------- */
section[data-testid="stSidebar"] {
    background: var(--ud-purple) !important;
    border-right: none !important;
    min-width: 250px !important;
}

/* Ensure labels in sidebar are white for contrast */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .filter-lbl,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #FFFFFF !important;
}

/* Ensure text INSIDE input boxes/dropdowns is BLACK for visibility */
section[data-testid="stSidebar"] [data-baseweb="select"] div,
section[data-testid="stSidebar"] [data-baseweb="input"] input,
section[data-testid="stSidebar"] [data-baseweb="select"] * {
    color: #1C1D1F !important;
}

/* ---------- Sidebar logo ---------- */
.sb-logo {
    padding: 30px 24px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.2);
    margin-bottom: 10px;
}
.sb-logo .brand {
    font-size: 1.8rem; font-weight: 700;
    color: #FFFFFF !important;
    letter-spacing: -0.03em;
}

/* ---------- Nav buttons in sidebar (on Purple background) ---------- */
.stRadio [data-baseweb="radio"] { display: none; }
div[data-testid="stRadio"] > label { display: none !important; }
div[data-testid="stRadio"] > div {
    display: flex; flex-direction: column; gap: 8px; padding: 0 16px;
}
div[data-testid="stRadio"] > div > label {
    display: flex !important;
    align-items: center;
    padding: 12px 18px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.95rem;
    font-weight: 500;
    color: rgba(255,255,255,0.7) !important;
    transition: all 0.2s;
}
div[data-testid="stRadio"] > div > label:has(input:checked) {
    background: rgba(255,255,255,0.2) !important;
    color: #fff !important; font-weight: 600;
}
div[data-testid="stRadio"] > div > label:hover:not(:has(input:checked)) {
    background: rgba(255,255,255,0.1);
    color: #fff !important;
}

/* ---------- Page title strip ---------- */
.page-header {
    padding: 30px 0 24px;
    border-bottom: 1px solid var(--ud-border);
    margin-bottom: 30px;
}
.page-title {
    font-size: 2.2rem; font-weight: 700;
    color: var(--ud-black) !important;
}
.page-title span { color: var(--ud-purple) !important; }

/* ---------- Top KPI bar ---------- */
.kpi-bar {
    display: flex; gap: 16px;
    margin-bottom: 30px;
}
.kpi-item {
    flex: 1;
    padding: 24px;
    text-align: center;
    background: var(--ud-white);
    border: 1px solid var(--ud-border);
    border-radius: 12px;
    box-shadow: var(--shadow);
    transition: all 0.3s ease;
}
.kpi-item:hover { 
    border-color: var(--ud-purple);
    transform: translateY(-2px);
}
.kpi-val {
    font-size: 1.8rem; font-weight: 700;
    color: var(--ud-purple) !important;
}
.kpi-lbl {
    font-size: 0.75rem; text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--ud-muted) !important;
    margin-top: 8px;
}

/* ---------- Card wrapper ---------- */
.card {
    background: var(--ud-white);
    border: 1px solid var(--ud-border);
    border-radius: 12px;
    padding: 24px;
    box-shadow: var(--shadow);
    margin-bottom: 24px;
}
.sec-hdr {
    font-size: 1.2rem; font-weight: 600;
    color: var(--ud-black) !important;
    margin-bottom: 20px;
}

/* ---------- Category table styling ---------- */
.cat-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.cat-table th {
    background: var(--ud-black);
    color: #fff !important;
    padding: 12px 16px; text-align: left;
}
.cat-table tr td {
    padding: 12px 16px;
    border-bottom: 1px solid var(--ud-border);
}
.cat-table tr:nth-child(even) { background: var(--ud-grey-l); }
.cat-table tr:hover { background: var(--ud-purple-s); }
.cat-table .hi { color: var(--ud-purple) !important; font-weight: 600; }

/* ---------- Alert box ---------- */
.price-alert {
    background: #FFFAEB;
    border-left: 4px solid #E6B400;
    border-radius: 8px;
    padding: 20px; margin: 20px 0;
}
.price-alert .at { font-weight: 700; color: #1C1D1F !important; }
.price-alert .ab { color: var(--ud-muted) !important; }

/* ---------- Email form ---------- */
.email-box {
    background: var(--ud-grey-l);
    border: 1px solid var(--ud-border);
    border-radius: 12px; padding: 30px; margin-top: 20px;
}

/* ---------- Buttons ---------- */
.stButton > button {
    background: var(--ud-purple) !important;
    color: #fff !important; border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 10px 28px !important;
}
.stButton > button:hover { 
    background: #8b2ed9 !important;
}

/* Form Inputs */
div[data-baseweb="input"] {
    background: var(--ud-white) !important;
    border: 1px solid var(--ud-border) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid var(--ud-border) !important; }
.stTabs [data-baseweb="tab"] {
    font-size: 0.95rem; padding: 10px 24px;
    color: var(--ud-muted) !important;
}
.stTabs [aria-selected="true"] {
    color: var(--ud-purple) !important;
    border-bottom: 3px solid var(--ud-purple) !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# DB CONNECTION
# ─────────────────────────────────────────────────────────────────────────────
DB_USER = os.getenv("DB_USER", "user_dw")
DB_PASS = os.getenv("DB_PASS", "password_dw")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "udemy_dw")

@st.cache_resource(show_spinner=False)
def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

try:
    engine = get_engine()
    with engine.connect() as _c:
        _c.execute(text("SELECT 1"))
except Exception as e:
    st.error(f"Cannot connect to Data Warehouse: {e}")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def load_courses_main():
    """Latest snapshot per course from stg_courses + instructor name."""
    sql = """
    WITH latest AS (
        SELECT DISTINCT ON (course_id)
            course_id, title, category, language, level,
            rating, num_students, num_reviews,
            list_price, sale_price, duration_hours,
            course_url, scraped_at,
            rating_1, rating_2, rating_3, rating_4, rating_5
        FROM public_staging.stg_courses
        WHERE title IS NOT NULL
        ORDER BY course_id,
                 CASE WHEN num_students IS NOT NULL AND num_students != 'NaN'
                      THEN 0 ELSE 1 END,
                 scraped_at DESC
    )
    SELECT l.*,
           i.instructor_name
    FROM latest l
    LEFT JOIN public_staging.stg_instructors i USING (course_id)
    LIMIT 5000
    """
    df = pd.read_sql(sql, engine)
    for col in ["rating","num_students","num_reviews","list_price","sale_price","duration_hours"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["num_students"] = df["num_students"].fillna(0)
    df["num_reviews"]  = df["num_reviews"].fillna(0)
    df["rating"]       = df["rating"].fillna(0)
    df["sale_price"]   = df["sale_price"].fillna(0)
    df["list_price"]   = df["list_price"].fillna(0)
    df["duration_hours"] = df["duration_hours"].fillna(0)
    # estimated revenue = students * sale_price (approximation)
    df["est_revenue"]  = df["num_students"] * df["sale_price"]
    # pct review
    df["pct_review"]   = df.apply(
        lambda r: round(r["num_reviews"] / r["num_students"] * 100, 2)
        if r["num_students"] > 0 else 0, axis=1
    )
    # price tier
    def price_tier(p):
        if p <= 0:          return "Free"
        if p < 400_000:     return "Low Price (< 400K)"
        if p < 800_000:     return "Mid Price (400K - 800K)"
        if p < 1_500_000:   return "High Price (800K - 1.5M)"
        return "Very High Price (> 1.5M)"
    df["price_tier"] = df["sale_price"].apply(price_tier)
    # duration tier
    def dur_tier(h):
        if h <= 0:   return "Unknown"
        if h <= 3:   return "Very Short (<= 3h)"
        if h <= 8:   return "Short (3h - 8h)"
        if h <= 15:  return "Medium (8h - 15h)"
        if h <= 24:  return "Long (15h - 24h)"
        return "Very Long (> 24h)"
    df["duration_tier"] = df["duration_hours"].apply(dur_tier)
    # rating tier
    def rat_tier(r):
        if r <= 0:  return "No Rating"
        if r >= 4:  return "Good (4 - 5)"
        if r >= 3:  return "Fair (3 - 3.9)"
        return "Poor (under 3)"
    df["rating_tier"] = df["rating"].apply(rat_tier)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_price_history():
    sql = """
    SELECT f.course_id, f.title, f.course_url,
           f.list_price, f.sale_price,
           f.recorded_at::TEXT AS recorded_at,
           f.discount_percentage, f.is_lowest_price_ever,
           c.category_name as category
    FROM public_marts.fct_price_history f
    LEFT JOIN public_marts.dim_course d ON CAST(f.course_id AS TEXT) = CAST(d.course_id AS TEXT)
    LEFT JOIN public_marts.dim_category c ON CAST(d.category_id AS TEXT) = CAST(c.category_id AS TEXT)
    WHERE f.title IS NOT NULL
    ORDER BY f.course_id, f.recorded_at
    LIMIT 5000
    """
    df = pd.read_sql(sql, engine)
    df["recorded_at"]  = pd.to_datetime(df["recorded_at"], format="mixed")
    df["sale_price"]   = pd.to_numeric(df["sale_price"], errors="coerce").fillna(0)
    df["list_price"]   = pd.to_numeric(df["list_price"], errors="coerce").fillna(0)
    df["discount_percentage"] = pd.to_numeric(df["discount_percentage"], errors="coerce").fillna(0)
    return df





# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
CHART_COLORS = ["#A435F0", "#cf8bf7", "#1C1D1F", "#6A6F73", "#e1b5f9",
                "#5c2d99", "#F7F9FA"]

def fmt_k(val):
    if val >= 1_000_000: return f"{val/1_000_000:.2f}M"
    if val >= 1_000:     return f"{val/1_000:.1f}K"
    return str(int(val))

def fmt_vnd(val):
    if val <= 0: return "Free"
    if val >= 1_000_000_000: return f"{val/1_000_000_000:.2f}T d"
    if val >= 1_000_000:     return f"{val/1_000_000:.0f}M d"
    return f"{int(val):,} d"

def fmt_bn(val):
    """Format as 'Xbn' for revenue (billion VND)."""
    if val <= 0: return "0"
    if val >= 1_000_000_000_000: return f"{val/1_000_000_000_000:.2f}T d"
    if val >= 1_000_000_000:     return f"{val/1_000_000_000:.1f}B d"
    if val >= 1_000_000:         return f"{val/1_000_000:.0f}M d"
    return f"{int(val):,}"

def make_plot(fig):
    fig.update_layout(
        font_family="Outfit",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#1C1D1F",
        margin=dict(l=0, r=0, t=30, b=0),
    )
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# SMTP CONFIG (from .env — no UI input needed)
# ─────────────────────────────────────────────────────────────────────────────
SMTP_HOST   = os.getenv("SMTP_HOST",   "smtp.gmail.com")
SMTP_PORT   = int(os.getenv("SMTP_PORT",   "587"))
SMTP_SENDER = os.getenv("SMTP_SENDER",  "")
SMTP_PASS   = os.getenv("SMTP_PASSWORD", "")


def send_price_drop_email(to_email: str,
                          course_title: str,
                          list_price: float,
                          sale_price: float,
                          yest_price: float,
                          course_url: str,
                          is_lowest: bool) -> tuple:
    """
    Gui email canh bao giam gia theo mau trong anh:
    - Tieu de do: GIAM GIA + ten khoa hoc
    - Bang: Khoa hoc / Gia goc / Gia hien tai / Ly do
    - Nut CTA tim: MUA NGAY KEO LO
    Chi goi ham nay khi da biet khoa hoc dang giam gia.
    """
    if not SMTP_SENDER or not SMTP_PASS:
        return False, "Chua cau hinh SMTP_SENDER / SMTP_PASSWORD trong file .env"
    try:
        # Tinh % giam
        drop_pct = 0
        if yest_price and yest_price > 0:
            drop_pct = round((yest_price - sale_price) / yest_price * 100, 1)
        elif list_price and list_price > 0:
            drop_pct = round((list_price - sale_price) / list_price * 100, 1)

        # Ly do bao
        reasons = []
        if yest_price and sale_price < yest_price:
            reasons.append("Dang giam gia")
        if is_lowest:
            reasons.append("Re nhat lich su")
        reason_str = ", ".join(reasons) if reasons else "Co bien dong gia"

        # Format gia
        def vnd(v):
            if v <= 0: return "Mien phi"
            return f"{int(v):,}d"

        subject = f"GIAM GIA: {course_title} gia chi con {vnd(sale_price)}"

        # HTML body — theo mau trong anh
        html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f0f0f0;font-family:'Times New Roman',Times,serif;">

<table width="100%" cellpadding="0" cellspacing="0" bgcolor="#f0f0f0">
<tr><td align="center" style="padding:30px 10px;">

  <!-- Card -->
  <table width="480" cellpadding="0" cellspacing="0"
         style="background:#ffffff;border-radius:16px;
                box-shadow:0 4px 24px rgba(0,0,0,.13);overflow:hidden;">

    <!-- Header purple -->
    <tr>
      <td style="background:linear-gradient(135deg,#A435F0,#cf8bf7);
                 padding:28px 32px 22px;text-align:center;">
        <div style="font-size:1.7rem;font-weight:800;color:#fff;
                    letter-spacing:-.01em;">🎓 Udemy Price Tracker thông báo!</div>
        <div style="color:rgba(255,255,255,.85);font-size:.95rem;margin-top:8px;">
          Khóa học bạn đang theo dõi vừa có biến động giá hấp dẫn:
        </div>
      </td>
    </tr>

    <!-- Body -->
    <tr>
      <td style="padding:28px 32px;">

        <!-- Info table -->
        <table width="100%" cellpadding="0" cellspacing="0"
               style="border-collapse:collapse;border-radius:10px;overflow:hidden;
                      border:1px solid #e8e0f5;">
          <tr>
            <td style="background:#f5f0ff;padding:12px 16px;
                       font-weight:700;color:#4a1d96;width:38%;">
              Khoa hoc:
            </td>
            <td style="background:#f5f0ff;padding:12px 16px;color:#1a1a2e;
                       font-weight:600;">
              {course_title}
            </td>
          </tr>
          <tr>
            <td style="background:#fff;padding:12px 16px;
                       font-weight:700;color:#4a1d96;">
              Gia goc:
            </td>
            <td style="background:#fff;padding:12px 16px;color:#888;
                       text-decoration:line-through;">
              {vnd(list_price)}
            </td>
          </tr>
          <tr>
            <td style="background:#f5f0ff;padding:12px 16px;
                       font-weight:700;color:#4a1d96;">
              Gia hien tai:
            </td>
            <td style="background:#f5f0ff;padding:12px 16px;
                       font-weight:800;font-size:1.3rem;color:#7b2ff7;">
              {vnd(sale_price)}
            </td>
          </tr>
          <tr>
            <td style="background:#fff;padding:12px 16px;
                       font-weight:700;color:#4a1d96;">
              Ly do bao:
            </td>
            <td style="background:#fff;padding:12px 16px;
                       color:#22c55e;font-weight:700;">
              {reason_str}
            </td>
          </tr>
        </table>

        <!-- CTA button -->
        <table width="100%" cellpadding="0" cellspacing="0"
               style="margin-top:24px;">
          <tr>
            <td align="center">
              <a href="{course_url}"
                 target="_blank"
                 style="display:inline-block;
                        background:linear-gradient(90deg,#a855f7,#7b2ff7);
                        color:#ffffff;
                        font-family:'Times New Roman',Times,serif;
                        font-size:1rem;font-weight:800;
                        text-decoration:none;
                        padding:14px 36px;
                        border-radius:50px;
                        letter-spacing:.04em;
                        box-shadow:0 4px 14px rgba(123,47,247,.4);">
                MUA NGAY KEO LO &rarr;
              </a>
            </td>
          </tr>
        </table>

        <!-- Footer note -->
        <p style="margin-top:24px;font-size:.78rem;color:#aaa;
                  border-top:1px solid #ede8fa;padding-top:14px;">
          Email nay duoc gui tu he thong Udemy Price Tracker.<br/>
          Ban nhan duoc vi khoa hoc ban dang theo doi co bien dong gia.
        </p>

      </td>
    </tr>

  </table>

</td></tr>
</table>

</body></html>
"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Udemy Price Tracker <{SMTP_SENDER}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as srv:
            srv.starttls()
            srv.login(SMTP_SENDER, SMTP_PASS)
            srv.sendmail(SMTP_SENDER, to_email, msg.as_string())

        return True, "Email da duoc gui thanh cong!"

    except Exception as e:
        return False, f"Khong the gui email: {e}"



# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────
with st.spinner("Loading data..."):
    df_raw     = load_courses_main()
    df_tracker = load_price_history()


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo
    st.markdown("""
    <div class="sb-logo">
        <div class="brand">🎓 Udemy</div>
        <div style="font-size:.7rem;color:rgba(255,255,255,0.6);margin-top:2px;">Analytics Dashboard</div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation
    page = st.radio(
        "nav",
        ["Overview", "Best Courses", "Price Tracker"],
        label_visibility="collapsed",
        key="main_nav",
    )

    st.markdown("<hr style='margin:10px 0;border-color:#e6e0f5;'>", unsafe_allow_html=True)

    # ── Filters (visible for Overview & Best Courses) ──
    if page not in ["Price Tracker"]:
        st.markdown('<div class="filter-lbl">Category</div>', unsafe_allow_html=True)
        cats_all = ["All"] + sorted(df_raw["category"].dropna().unique().tolist())
        sel_cat = st.selectbox("cat", cats_all, label_visibility="collapsed", key="f_cat")

        st.markdown('<div class="filter-lbl">Price Tier</div>', unsafe_allow_html=True)
        tier_order = ["All","Free","Low Price (< 400K)","Mid Price (400K - 800K)",
                      "High Price (800K - 1.5M)","Very High Price (> 1.5M)"]
        sel_tier = st.selectbox("tier", tier_order, label_visibility="collapsed", key="f_tier")

        st.markdown('<div class="filter-lbl">Level</div>', unsafe_allow_html=True)
        lvls_all = ["All"] + sorted(df_raw["level"].dropna().unique().tolist())
        sel_lvl = st.selectbox("lvl", lvls_all, label_visibility="collapsed", key="f_lvl")

        st.markdown('<div class="filter-lbl">Rating</div>', unsafe_allow_html=True)
        rat_opts = ["All","Good (4 - 5)","Fair (3 - 3.9)","Poor (under 3)","No Rating"]
        sel_rat = st.selectbox("rat", rat_opts, label_visibility="collapsed", key="f_rat")

        if page == "Best Courses":
            st.markdown('<div class="filter-lbl">Published Time</div>', unsafe_allow_html=True)
            pub_opts = ["All","Last 1 Year","Last 2 Years","Older"]
            sel_pub = st.selectbox("pub", pub_opts, label_visibility="collapsed", key="f_pub")
    else:
        # Price Tracker page filters
        st.markdown('<div class="filter-lbl">Category (Group 2)</div>', unsafe_allow_html=True)
        t_cats = ["All", "Programming Languages", "Database Design & Development", 
                  "Software Testing", "No-Code Development"]
        sel_t_cat = st.selectbox("t_cat", t_cats, label_visibility="collapsed", key="f_tracker_cat")

        st.markdown('<div class="filter-lbl">Price Type</div>', unsafe_allow_html=True)
        sel_price_type = st.selectbox(
            "price_type", ["All", "Free", "Paid"],
            label_visibility="collapsed", key="f_price_type"
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:.78rem;color:rgba(255,255,255,0.6);padding:8px 4px;border-top:1px solid rgba(255,255,255,0.2);">
            Email canh bao duoc gui tu tai khoan he thong.<br/>
            Chi can nhap Gmail nguoi nhan va nhan <strong>Gui</strong>.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='margin:10px 0;border-color:#e6e0f5;'>", unsafe_allow_html=True)
    st.caption(f"Updated: {datetime.now().strftime('%d/%m/%Y %H:%M')}")


# ─────────────────────────────────────────────────────────────────────────────
# APPLY FILTERS
# ─────────────────────────────────────────────────────────────────────────────
def apply_filters(df):
    if page == "Price Tracker":
        return df
    d = df.copy()
    if sel_cat  != "All": d = d[d["category"]    == sel_cat]
    if sel_tier != "All": d = d[d["price_tier"]  == sel_tier]
    if sel_lvl  != "All": d = d[d["level"]       == sel_lvl]
    if sel_rat  != "All": d = d[d["rating_tier"] == sel_rat]
    return d

df = apply_filters(df_raw) if page != "Price Tracker" else df_raw


# ═══════════════════════════════════════════════════════════
# PAGE ① — OVERVIEW
# ═══════════════════════════════════════════════════════════
if page == "Overview":

    # ── Header ──
    st.markdown("""
    <div class="page-header">
        <div class="page-title">Development Course Dashboard &nbsp;|&nbsp;
            <span>Overview</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI metrics ──
    # deduplicate per course
    df_uniq = df.drop_duplicates("course_id")
    total_courses    = df_uniq["course_id"].nunique()
    total_enroll     = df_uniq["num_students"].sum()
    total_revenue    = df_uniq["est_revenue"].sum()
    avg_price        = df_uniq[df_uniq["sale_price"] > 0]["sale_price"].mean() or 0
    pct_review_avg   = df_uniq[df_uniq["num_students"] > 0]["pct_review"].mean() or 0
    avg_rating       = df_uniq[df_uniq["rating"] > 0]["rating"].mean() or 0

    st.markdown(f"""
    <div class="kpi-bar">
        <div class="kpi-item">
            <div class="kpi-val accent">{fmt_k(total_courses)}</div>
            <div class="kpi-lbl">Total Courses</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-val accent">{fmt_k(total_enroll)}</div>
            <div class="kpi-lbl">Total Enrollments</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-val accent">{fmt_bn(total_revenue)}</div>
            <div class="kpi-lbl">Est. Total Revenue</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-val">{fmt_vnd(avg_price)}</div>
            <div class="kpi-lbl">Avg Price</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-val">{pct_review_avg:.2f}%</div>
            <div class="kpi-lbl">% Review</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-val">{avg_rating:.2f}</div>
            <div class="kpi-lbl">Avg Rating Score</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Row 2: Category table + Price chart ──
    col_left, col_right = st.columns([6, 4], gap="medium")

    with col_left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="sec-hdr">Sales Performance of Category</div>',
                    unsafe_allow_html=True)

        cat_agg = (df_uniq.groupby("category")
                          .agg(
                              total_courses=("course_id", "nunique"),
                              total_enroll=("num_students", "sum"),
                              total_instructors=("instructor_name", "nunique"),
                              total_revenue=("est_revenue", "sum"),
                          )
                          .reset_index()
                          .sort_values("total_enroll", ascending=False))

        rows_html = ""
        for _, r in cat_agg.iterrows():
            rows_html += f"""
            <tr>
                <td>{r['category']}</td>
                <td class="hi">{int(r['total_courses']):,}</td>
                <td class="hi">{fmt_k(r['total_enroll'])}</td>
                <td>{int(r['total_instructors']):,}</td>
                <td class="hi">{fmt_bn(r['total_revenue'])}</td>
            </tr>"""

        st.markdown(f"""
        <table class="cat-table">
            <thead>
                <tr>
                    <th>Category</th>
                    <th>Total Courses</th>
                    <th>Total Enrollments</th>
                    <th>Total Instructors</th>
                    <th>Total Revenue</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="sec-hdr">Total Courses by Price</div>',
                    unsafe_allow_html=True)
        price_tier_order = ["Free","Low Price (< 400K)","Mid Price (400K - 800K)",
                            "High Price (800K - 1.5M)","Very High Price (> 1.5M)"]
        price_cnt = (df_uniq.groupby("price_tier")["course_id"]
                             .nunique().reset_index(name="count"))
        # keep defined order
        price_cnt["price_tier"] = pd.Categorical(
            price_cnt["price_tier"], categories=price_tier_order, ordered=True)
        price_cnt = price_cnt.sort_values("price_tier")

        fig_price = go.Figure(go.Bar(
            x=price_cnt["count"],
            y=price_cnt["price_tier"],
            orientation="h",
            marker_color=["#cf8bf7", "#e1b5f9", "#FFFFFF", "#A435F0", "#5c2d99"],
            text=price_cnt["count"].apply(fmt_k),
            textposition="outside",
            textfont=dict(family="Outfit", size=11, color="#FFFFFF"),
        ))
        fig_price.update_layout(
            height=260,
            font_family="Outfit",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#1C1D1F",
            margin=dict(l=0,r=60,t=10,b=0),
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig_price, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Row 3: Level donut + Rating donut + Duration bar ──
    c1, c2, c3 = st.columns(3, gap="medium")

    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="sec-hdr">Total Courses by Level</div>',
                    unsafe_allow_html=True)
        lvl_cnt = (df_uniq.dropna(subset=["level"])
                           .groupby("level")["course_id"]
                           .nunique().reset_index(name="count"))
        fig_lvl = px.pie(
            lvl_cnt, names="level", values="count", hole=0.48,
            color_discrete_sequence=["#A435F0","#cf8bf7","#e1b5f9","#FFFFFF","#5c2d99"],
        )
        fig_lvl.update_traces(
            textfont_family="Outfit",
            textinfo="percent+label",
            textfont_size=10,
        )
        fig_lvl.update_layout(
            height=270, showlegend=True,
            font_family="Outfit",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#1C1D1F",
            margin=dict(l=0,r=0,t=10,b=0),
            legend=dict(orientation="h", y=-0.15, font_size=9),
        )
        st.plotly_chart(fig_lvl, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="sec-hdr">Total Courses by Rating</div>',
                    unsafe_allow_html=True)
        rat_cnt = (df_uniq[df_uniq["rating_tier"] != "No Rating"]
                   .groupby("rating_tier")["course_id"]
                   .nunique().reset_index(name="count"))
        fig_rat = px.pie(
            rat_cnt, names="rating_tier", values="count", hole=0.48,
            color_discrete_sequence=["#A435F0","#cf8bf7","#c0392b"],
        )
        fig_rat.update_traces(
            textfont_family="Outfit",
            textinfo="percent+label",
            textfont_size=10,
        )
        fig_rat.update_layout(
            height=270, showlegend=True,
            font_family="Outfit",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#1C1D1F",
            margin=dict(l=0,r=0,t=10,b=0),
            legend=dict(orientation="h", y=-0.15, font_size=9),
        )
        st.plotly_chart(fig_rat, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="sec-hdr">Total Courses by Duration</div>',
                    unsafe_allow_html=True)
        dur_order = ["Very Short (<= 3h)","Short (3h - 8h)","Medium (8h - 15h)",
                     "Long (15h - 24h)","Very Long (> 24h)","Unknown"]
        dur_cnt = (df_uniq.groupby("duration_tier")["course_id"]
                          .nunique().reset_index(name="count"))
        dur_cnt["duration_tier"] = pd.Categorical(
            dur_cnt["duration_tier"], categories=dur_order, ordered=True)
        dur_cnt = dur_cnt[dur_cnt["duration_tier"] != "Unknown"].sort_values("duration_tier")

        fig_dur = go.Figure(go.Bar(
            x=dur_cnt["count"],
            y=dur_cnt["duration_tier"],
            orientation="h",
            marker_color=["#8b44d9","#9e5de0","#b07fe8","#c4a8e8","#d4b8f5"],
            text=dur_cnt["count"].apply(fmt_k),
            textposition="outside",
            textfont=dict(family="Times New Roman", size=11),
        ))
        fig_dur.update_layout(
            height=260,
            font_family="Times New Roman",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0,r=50,t=10,b=0),
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig_dur, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# PAGE ② — BEST COURSES
# ═══════════════════════════════════════════════════════════
elif page == "Best Courses":

    st.markdown("""
    <div class="page-header">
        <div class="page-title">Development Course Dashboard &nbsp;|&nbsp;
            <span>Best Courses</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_best = df.drop_duplicates("course_id").copy()

    # published time filter
    if "sel_pub" in dir() or True:
        sel_pub_val = st.session_state.get("f_pub", "All")
        if sel_pub_val == "Last 1 Year":
            df_best = df_best  # can't filter without published_date data
        # (published_date mostly NULL in raw data — skip gracefully)

    # Sort by total enrollments desc
    df_best = df_best.sort_values("num_students", ascending=False)

    # Build display table
    display = df_best[[
        "title","num_students","est_revenue","rating","pct_review",
        "list_price","level","category","course_url","instructor_name"
    ]].copy()

    display.columns = [
        "Course","Total Subscribers","Total Revenue","Rating",
        "% Review","List Price","Level","Category","Course URL","Instructor"
    ]
    display["Total Subscribers"] = display["Total Subscribers"].apply(
        lambda v: fmt_k(v) if v > 0 else "0")
    display["Total Revenue"] = display["Total Revenue"].apply(fmt_bn)
    display["Rating"] = display["Rating"].apply(
        lambda v: f"{v:.2f}" if v > 0 else "-")
    display["% Review"] = display["% Review"].apply(
        lambda v: f"{v:.2f}%" if v > 0 else "-")
    display["List Price"] = display["List Price"].apply(
        lambda v: f"{int(v):,}" if v > 0 else "Free")

    # Metric strip
    df_u = df.drop_duplicates("course_id")
    tc  = df_u["course_id"].nunique()
    te  = df_u["num_students"].sum()
    tr  = df_u["est_revenue"].sum()
    ar  = df_u[df_u["rating"] > 0]["rating"].mean() or 0

    st.markdown(f"""
    <div class="kpi-bar">
        <div class="kpi-item">
            <div class="kpi-val accent">{fmt_k(tc)}</div>
            <div class="kpi-lbl">Total Courses (filtered)</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-val accent">{fmt_k(te)}</div>
            <div class="kpi-lbl">Total Enrollments</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-val accent">{fmt_bn(tr)}</div>
            <div class="kpi-lbl">Est. Revenue</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-val">{ar:.2f} ⭐</div>
            <div class="kpi-lbl">Avg Rating</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Search box
    search_q = st.text_input(
        "Search course...", placeholder="Type course name or keyword...",
        key="best_search")
    if search_q:
        display = display[
            display["Course"].str.contains(search_q, case=False, na=False)
        ]

    st.info(f"Showing {len(display):,} courses")

    st.dataframe(
        display.reset_index(drop=True),
        width="stretch",
        height=560,
    )




# ═══════════════════════════════════════════════════════════
# PAGE ④ — PRICE TRACKER
# ═══════════════════════════════════════════════════════════
elif page == "Price Tracker":
    st.markdown("""
    <div class="page-header">
        <div class="page-title">Price Tracker &nbsp;|&nbsp;
            <span>Daily Price Monitor</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if df_tracker.empty:
        st.warning("No price tracker data yet. Please run the tracker scraper first.")
        st.stop()

    # Filter courses by Free/Paid status and Category
    df_tracker_filtered = df_tracker.copy()
    
    # 1. Price Type Filter
    if sel_price_type == "Free":
        df_tracker_filtered = df_tracker_filtered[df_tracker_filtered["list_price"] <= 0]
    elif sel_price_type == "Paid":
        df_tracker_filtered = df_tracker_filtered[df_tracker_filtered["list_price"] > 0]
        
    # 2. Category Filter
    if sel_t_cat != "All":
        df_tracker_filtered = df_tracker_filtered[df_tracker_filtered["category"] == sel_t_cat]

    st.markdown('<div class="sec-hdr">Select Course to Monitor</div>',
                unsafe_allow_html=True)
                
    # --- Price Drop Filter Toggle ---
    show_only_drops = st.toggle("🔥 Chỉ hiển thị các khóa học đang Đợt Sale (Giảm giá so với hôm qua)", value=False)
    
    if show_only_drops:
        # Lọc nhanh các course_id đang có sale_price hôm nay < hôm qua
        drop_cids = []
        temp_df = df_tracker_filtered[df_tracker_filtered["sale_price"] > 0].sort_values("recorded_at")
        for cid, group in temp_df.groupby("course_id"):
            if len(group) >= 2 and group.iloc[-1]["sale_price"] < group.iloc[-2]["sale_price"]:
                drop_cids.append(cid)
                
        df_tracker_filtered = df_tracker_filtered[df_tracker_filtered["course_id"].isin(drop_cids)]
        
        if df_tracker_filtered.empty:
            st.info("Hiện nhóm này Không có khóa học nào đang giảm giá hôm nay!")
            st.stop()

    # Course selector based on dynamic filtered dataframe
    course_opts = (df_tracker_filtered.drop_duplicates("course_id")
                                     .sort_values("title")[["course_id","title"]]
                                     .values.tolist())
    
    if not course_opts:
        st.info(f"No {sel_price_type.lower()} courses found in tracker data.")
        st.stop()
        
    title_map = {f"{t}  (ID: {cid})": cid for cid, t in course_opts}

    sel_label     = st.selectbox("course_sel", list(title_map.keys()),
                                 label_visibility="collapsed", key="tracker_sel")
    sel_course_id = title_map[sel_label]

    df_sel = df_tracker[df_tracker["course_id"] == sel_course_id].sort_values("recorded_at")

    if df_sel.empty:
        st.warning("No data for this course.")
        st.stop()

    latest    = df_sel.iloc[-1]
    cur_p     = latest["sale_price"]
    list_p    = latest["list_price"]
    disc_pct  = latest["discount_percentage"]
    is_lowest = latest["is_lowest_price_ever"]

    df_nz = df_sel[df_sel["sale_price"] > 0]
    yest_price = df_nz.iloc[-2]["sale_price"] if len(df_nz) >= 2 else None

    # Custom logic defined by user: (Yesterday - Today) / Yesterday (Chuẩn toán học hệ số giảm)
    if yest_price and cur_p > 0 and cur_p < yest_price:
        display_disc = ((yest_price - cur_p) / yest_price) * 100
    else:
        display_disc = disc_pct

    # KPI
    st.markdown(f"""
    <div class="kpi-bar">
        <div class="kpi-item">
            <div class="kpi-val accent">{fmt_vnd(cur_p)}</div>
            <div class="kpi-lbl">Current Price</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-val">{fmt_vnd(list_p)}</div>
            <div class="kpi-lbl">Original Price</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-val">{display_disc:.1f}%</div>
            <div class="kpi-lbl">Discount</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-val">{fmt_vnd(yest_price) if yest_price else 'N/A'}</div>
            <div class="kpi-lbl">Yesterday Price</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-val">{'YES' if is_lowest else 'No'}</div>
            <div class="kpi-lbl">All-Time Low?</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Alerts
    price_dropped = (yest_price and cur_p > 0 and cur_p < yest_price)
    if is_lowest and cur_p > 0:
        st.markdown("""
        <div class="price-alert">
            <div class="at">🎯 All-Time Low Price!</div>
            <div class="ab">This is the lowest price ever recorded for this course.</div>
        </div>""", unsafe_allow_html=True)

    if price_dropped:
        diff = yest_price - cur_p
        st.markdown(f"""
        <div class="price-alert">
            <div class="at">🔔 Price dropped since yesterday!</div>
            <div class="ab">
                Yesterday: <strong>{fmt_vnd(yest_price)}</strong> &rarr;
                Today: <strong>{fmt_vnd(cur_p)}</strong>
                &nbsp;(-{fmt_vnd(diff)})
            </div>
        </div>""", unsafe_allow_html=True)

    # Chart
    col_ch, col_tbl = st.columns([6, 4], gap="medium")

    with col_ch:
        st.markdown('<div class="sec-hdr">Price History Chart</div>',
                    unsafe_allow_html=True)
        chart_df = df_sel[df_sel["sale_price"] > 0] if df_sel[df_sel["sale_price"] > 0].shape[0] > 1 else df_sel
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=chart_df["recorded_at"], y=chart_df["list_price"],
            mode="lines", name="Original Price",
            line=dict(color="#949494", width=1.5, dash="dot"),
        ))
        fig_line.add_trace(go.Scatter(
            x=chart_df["recorded_at"], y=chart_df["sale_price"],
            mode="lines+markers", name="Sale Price",
            line=dict(color="#A435F0", width=2.5),
            marker=dict(size=7, color="#A435F0"),
            fill="tozeroy", fillcolor="rgba(164, 53, 240, 0.1)",
        ))
        lowest_pts = chart_df[chart_df["is_lowest_price_ever"]]
        if not lowest_pts.empty:
            fig_line.add_trace(go.Scatter(
                x=lowest_pts["recorded_at"], y=lowest_pts["sale_price"],
                mode="markers", name="All-Time Low",
                marker=dict(size=12, color="#c0392b", symbol="star"),
            ))
        fig_line.update_layout(
            height=340, hovermode="x unified",
            font_family="Outfit",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#1C1D1F",
            legend=dict(orientation="h", y=-0.2),
            yaxis=dict(gridcolor="rgba(0,0,0,0.05)", title="Price (VND)"),
            xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
            margin=dict(l=0,r=0,t=10,b=0),
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with col_tbl:
        st.markdown('<div class="sec-hdr">Price History Table</div>',
                    unsafe_allow_html=True)
        # Format the date column for the table display only
        hist_df = df_sel.copy()
        if not hist_df.empty:
            hist_df["recorded_at"] = pd.to_datetime(hist_df["recorded_at"]).dt.date
            
            # --- Custom Drop % Logic (Yesterday vs Today) over all rows ---
            hist_df["prev_price"] = hist_df["sale_price"].shift(1)
            def convert_disc(row):
                if pd.notna(row["prev_price"]) and row["sale_price"] > 0 and row["prev_price"] > row["sale_price"]:
                    return round(((row["prev_price"] - row["sale_price"]) / row["prev_price"]) * 100, 1)
                return round(row["discount_percentage"], 1)
                
            hist_df["discount_percentage"] = hist_df.apply(convert_disc, axis=1)
            
        hist = (hist_df[["recorded_at","list_price","sale_price",
                         "discount_percentage","is_lowest_price_ever"]]
                .rename(columns={
                    "recorded_at": "Date",
                    "list_price": "Original (VND)",
                    "sale_price": "Sale (VND)",
                    "discount_percentage": "Disc %",
                    "is_lowest_price_ever": "Low?",
                })
                .sort_values("Date", ascending=False))
        st.dataframe(hist.reset_index(drop=True),
                     width="stretch", height=320)

    # ── Email alert form ──
    st.markdown("---")
    st.markdown('<div class="sec-hdr">📧 Gui canh bao gia qua Email</div>',
                unsafe_allow_html=True)

    # Xac dinh trang thai giam gia
    can_send = price_dropped or (is_lowest and cur_p > 0)

    with st.container():
        st.markdown('<div class="email-box">', unsafe_allow_html=True)

        # Hien thi thong tin khoa hoc
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.markdown(f"**Khoa hoc:** {latest['title']}")
            st.markdown(f"**Gia hien tai:** {fmt_vnd(cur_p)}")
        with col_info2:
            st.markdown(f"**Gia goc:** {fmt_vnd(list_p)}")
            if yest_price:
                st.markdown(f"**Gia hom qua:** {fmt_vnd(yest_price)}")

        st.markdown("<br>", unsafe_allow_html=True)

        # Nut gui chi hien khi co giam gia
        if not can_send:
            st.markdown("""
            <div style="background:#fff8e6;border:1px solid #f5d76e;border-radius:8px;
                        padding:12px 16px;margin-bottom:10px;">
                <span style="font-weight:700;color:#b7791f;">⚠️ Khong co giam gia</span><br/>
                <span style="color:#7a5200;font-size:.88rem;">
                    Email chi co the gui khi khoa hoc dang giam gia so voi hom qua
                    hoac dang o muc gia thap nhat lich su.
                </span>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Hien thi ly do co the gui
            reasons_ui = []
            if price_dropped and yest_price:
                drop = yest_price - cur_p
                drop_pct_val = round(drop / yest_price * 100, 1)
                reasons_ui.append(f"Giam {fmt_vnd(drop)} ({drop_pct_val}%) so voi hom qua")
            if is_lowest:
                reasons_ui.append("Day gia thap nhat lich su")

            st.markdown(f"""
            <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;
                        padding:10px 14px;margin-bottom:12px;">
                <span style="font-weight:700;color:#166534;">✅ Du dieu kien gui canh bao</span><br/>
                <span style="color:#14532d;font-size:.88rem;">{' · '.join(reasons_ui)}</span>
            </div>
            """, unsafe_allow_html=True)

            col_e1, col_e2 = st.columns([3, 1])
            with col_e1:
                recipient = st.text_input(
                    "Nhap Gmail nguoi nhan canh bao:",
                    placeholder="example@gmail.com",
                    key="rec_email",
                )
            with col_e2:
                st.markdown("<br>", unsafe_allow_html=True)
                send_btn = st.button("📤 Gui Email", key="send_btn")

            if send_btn:
                if not recipient or "@" not in recipient:
                    st.error("Vui long nhap dia chi Gmail hop le.")
                elif not SMTP_SENDER or not SMTP_PASS or SMTP_PASS == "your_app_password_here":
                    st.error(
                        "SMTP chua duoc cau hinh. Mo file Web/.env va dien "
                        "SMTP_SENDER + SMTP_PASSWORD (Google App Password)."
                    )
                else:
                    with st.spinner("Dang gui email..."):
                        ok, msg_r = send_price_drop_email(
                            to_email=recipient,
                            course_title=latest["title"],
                            list_price=list_p,
                            sale_price=cur_p,
                            yest_price=yest_price if yest_price else list_p,
                            course_url=latest["course_url"],
                            is_lowest=bool(is_lowest),
                        )
                    if ok:
                        st.toast(f"Email sent successfully to {recipient}!", icon="🚀")
                        st.balloons()
                    else:
                        st.error(f"❌ {msg_r}")

        st.markdown("</div>", unsafe_allow_html=True)
