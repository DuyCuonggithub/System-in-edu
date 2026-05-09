# Udemy Analytics Web Design Skill (Front-end Guide)

This document defines the mandatory design standards and technical logic for the Udemy Analytics Dashboard. All future developments should strictly adhere to these specifications.

## 1. Visual Identity & Color System
The aesthetic follows the official Udemy brand with a premium "Dark Mode" focus.

### Color Distribution (50/30/20 Rule)
- **50% White (`#FFFFFF`)**: Used for the primary app background and main content surfaces. Provides a clean, airy feel.
- **30% Purple (`#A435F0`)**: Official Udemy Purple. Used for the sidebar, large headers, primary buttons, and significant UI markers.
- **20% Black (`#1C1D1F`)**: Used for high-contrast text, borders, and deep element accents to ensure structure and readability.

### Typography
- **Primary**: `Arial` or `Sans-serif` (Clean, modern, professional).
- **Secondary**: `Times New Roman` (Only for legal or citation scripts if necessary).

---

## 2. Component Design Library

### Cards & Surfaces
- **Background**: `#FFFFFF` (30% palette) or slightly transparent layers.
- **Shadow**: `rgba(0,0,0,0.15)` subtle drop shadow.
- **Corner Radius**: `12px` or `16px` for a modern, soft feel.

### KPI Metrics (KPI Bar)
```html
<div class="kpi-item">
    <div class="kpi-val" style="color: #A435F0;">[Value]</div>
    <div class="kpi-lbl" style="color: #1C1D1F;">[Label]</div>
</div>
```

### Charts (Plotly Standards)
- **Font Family**: Modern Sans-serif.
- **Background**: Transparent (`rgba(0,0,0,0)`).
- **Color Sequence**: Starting with Udemy Purple (`#A435F0`), followed by light purple tints.

---

## 3. Deals Reporting Logic
The "Deals & Price Drops" section is critical for tracking business value.

### Logic Flow
1. **Daily Comparison**: Compare `today_price` with `yesterday_price` from the `fct_price_history` table.
2. **Highlight Criteria**:
    - `Sale Price < Yesterday Price` (Flag as "Price Drop").
    - `Sale Price == Lowest History Price` (Flag as "All-Time Low").
3. **UI Element**: Use a `price-alert` component with a red left border or a purple notification badge.

---

## 4. Job Tracker Orchestration (Repetition Logic)
The "Tracker" job must run predictably to feed the Web UI.

- **Step 1**: `run_group.py` triggers `udemy_scraper.py` with the `--job tracker` flag.
- **Step 2**: Scraper extracts *only* prices to maximize speed and bypass blocks more efficiently.
- **Step 3**: Data is persisted to the Data Warehouse (PostgreSQL) via MinIO/dbt.
- **Repetition**: Should be scheduled via Cron or Airflow (Daily at 00:00 UTC).

## 5. Implementation in Streamlit
Use `st.markdown(..., unsafe_allow_html=True)` to override default Streamlit behavior and inject the 50/20/30 style via CSS.
