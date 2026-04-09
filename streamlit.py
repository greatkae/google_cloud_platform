# %%
# packages
# References:
# https://docs.streamlit.io/library/api-reference
# https://pola-rs.github.io/polars/py-polars/html/reference/index.html

import streamlit as st
import polars as pl
import plotly.express as px
import plotly.io as pio

pio.templates.default = "simple_white"

st.set_page_config(
    page_title="Cstore Dashboard",
    page_icon="🏪",
    layout="wide"
)

# %%
# ---- DATA LOADING WITH CACHING ----
@st.cache_data
def load_stores():
    return pl.read_csv("data/stores.csv")

@st.cache_data
def load_master_ctin():
    return pl.read_csv("data/master_ctin.csv")

@st.cache_data
def load_weekly_sales():
    return pl.read_csv("data/weekly_sales.csv", try_parse_dates=True)

@st.cache_data
def load_weekly_payments():
    return pl.read_csv("data/weekly_payments.csv", try_parse_dates=True)

@st.cache_data
def load_basket_size():
    return pl.read_csv("data/basket_size.csv", try_parse_dates=True)

# %%
# ---- SIDEBAR NAVIGATION ----
st.sidebar.title("🏪 Cstore Dashboard")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate to:",
    [
        "🏠 Home",
        "📦 Top 5 Products",
        "🥤 Packaged Beverages",
        "💳 Cash vs Credit",
        "🏘️ Demographics"
    ]
)

# %%
# ---- HOME PAGE ----
if page == "🏠 Home":
    st.title("🏪 Cstore Analytics Dashboard")
    st.markdown("---")
    st.markdown("""
    Welcome to the Cstore Analytics Dashboard.
    Use the sidebar to navigate between pages.

    | Page | Question |
    |------|----------|
    | 📦 Top Products | What are the top 5 weekly sellers (excluding fuel)? |
    | 🥤 Beverages | Which packaged beverage brands should be dropped? |
    | 💳 Cash vs Credit | How do cash and credit customers compare? |
    | 🏘️ Demographics | What does the customer area look like demographically? |
    """)
    st.info("👈 Select a page from the sidebar to get started.")

# %%
# ---- PAGE PLACEHOLDERS ----
elif page == "📦 Top 5 Products":
    st.title("📦 Top 5 Products by Weekly Sales")
    st.info("Coming soon...")

elif page == "🥤 Packaged Beverages":
    st.title("🥤 Packaged Beverage Brand Analysis")
    st.info("Coming soon...")

elif page == "💳 Cash vs Credit":
    st.title("💳 Cash vs Credit Customer Comparison")
    st.info("Coming soon...")

elif page == "🏘️ Demographics":
    st.title("🏘️ Customer Area Demographics")
    st.info("Coming soon...")