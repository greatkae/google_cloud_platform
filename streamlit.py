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
def load_payment_products():
    return pl.read_csv(
        "data/payment_products.csv",
        null_values=["null", "NULL", ""],
        schema_overrides={"TOTAL_UNITS": pl.Float64}
    )

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
    return pl.read_csv(
        "data/basket_size.csv", 
        try_parse_dates=True,
        schema_overrides={"TRANSACTION_SET_ID": pl.Utf8}
    )

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
    st.markdown("Excluding fuel products. Based on total sales revenue per week.")
    st.markdown("---")

    # ---- LOAD DATA ----
    sales = load_weekly_sales()
    stores = load_stores()

    # ---- ADD MONTH NAME AND STORE NAME ----
    month_map = {
        "01": "January", "02": "February", "03": "March",
        "04": "April", "05": "May", "06": "June",
        "07": "July", "08": "August", "09": "September",
        "10": "October", "11": "November", "12": "December"
    }

    sales = sales.with_columns(
        pl.col("WEEK").cast(pl.Utf8).str.slice(0, 7).alias("MONTH_KEY")
    ).with_columns(
        pl.col("MONTH_KEY").str.slice(5, 2).replace(month_map).alias("MONTH_NAME"),
        pl.col("MONTH_KEY").str.slice(0, 4).alias("YEAR")
    ).with_columns(
        (pl.col("MONTH_NAME") + " " + pl.col("YEAR")).alias("MONTH")
    )

    # Join store names
    stores = stores.with_columns(pl.col("STORE_ID").cast(pl.Utf8))
    sales = sales.with_columns(pl.col("STORE_ID").cast(pl.Utf8))
    sales = sales.join(
        stores.select(["STORE_ID", "STORE_NAME", "CITY", "STATE"]),
        on="STORE_ID",
        how="left"
    ).with_columns(
        (pl.col("CITY") + ", " + pl.col("STATE")).alias("STORE_LABEL")
    )

    # ---- FILTERS SIDEBAR ----
    st.sidebar.markdown("### Filters")

    months = sorted(sales["MONTH_KEY"].drop_nulls().unique().to_list())
    month_labels = []
    for m in months:
        year = m[:4]
        month_num = m[5:7]
        month_labels.append(month_map.get(month_num, month_num) + " " + year)

    month_lookup = dict(zip(month_labels, months))
    selected_month_labels = st.sidebar.multiselect(
        "Select Months", month_labels, 
        default=month_labels[-3:] if len(month_labels) >= 3 else month_labels
    )
    selected_months = [month_lookup[m] for m in selected_month_labels]

    # Store filter with city names
    store_options = (
        sales.select(["STORE_ID", "STORE_LABEL"])
        .unique()
        .sort("STORE_LABEL")
        .filter(pl.col("STORE_LABEL").is_not_null())
    )
    store_labels = store_options["STORE_LABEL"].to_list()
    store_ids = store_options["STORE_ID"].to_list()
    store_lookup = dict(zip(store_labels, store_ids))

    selected_store_labels = st.sidebar.multiselect(
        "Select Stores", store_labels,
        default=store_labels[:5]
    )
    selected_store_ids = [store_lookup[s] for s in selected_store_labels]

    # ---- FILTER DATA ----
    filtered = sales.filter(
        (pl.col("MONTH_KEY").is_in(selected_months)) &
        (pl.col("STORE_ID").is_in(selected_store_ids)) &
        (pl.col("NONSCAN_CATEGORY") != "FUEL") &
        (pl.col("CATEGORY") != "Fuel") &
        (~pl.col("POS_DESCRIPTION").str.to_uppercase().str.contains("FUEL")) &
        (~pl.col("POS_DESCRIPTION").str.to_uppercase().str.contains("DIESEL")) &
        (~pl.col("POS_DESCRIPTION").str.to_uppercase().str.contains("UNLEADED"))
    )

    # ---- TOP 5 PRODUCTS ----
    top5 = (
        filtered
        .group_by("POS_DESCRIPTION")
        .agg(pl.col("TOTAL_SALES").sum().alias("TOTAL_SALES"))
        .sort("TOTAL_SALES", descending=True)
        .head(5)
    )

    # ---- KPIs ----
    st.subheader("Key Performance Indicators")
    col1, col2, col3 = st.columns(3)
    total_sales = filtered["TOTAL_SALES"].sum()
    top_product = top5["POS_DESCRIPTION"][0] if len(top5) > 0 else "N/A"
    top_sales = top5["TOTAL_SALES"][0] if len(top5) > 0 else 0

    col1.metric("Total Sales (Selected Period)", f"${total_sales:,.2f}")
    col2.metric("Top Product", top_product)
    col3.metric("Top Product Sales", f"${top_sales:,.2f}")

    st.markdown("---")

    # ---- LAYOUT: TABS ----
    tab1, tab2 = st.tabs(["📊 Charts", "📋 Summary Table"])

    with tab1:
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Top 5 Products by Total Sales")
            fig1 = px.bar(
                top5.to_pandas(),
                x="TOTAL_SALES",
                y="POS_DESCRIPTION",
                orientation="h",
                title="Top 5 Products - Total Revenue",
                labels={"TOTAL_SALES": "Total Sales ($)", "POS_DESCRIPTION": "Product"},
                color="TOTAL_SALES",
                color_continuous_scale="Blues"
            )
            threshold = st.number_input(
                "Draw a sales threshold line ($)",
                min_value=0.0,
                value=float(top_sales * 0.5) if top_sales > 0 else 100.0,
                step=100.0
            )
            fig1.add_vline(x=threshold, line_dash="dash", line_color="red",
                          annotation_text=f"Threshold: ${threshold:,.0f}")
            st.plotly_chart(fig1, use_container_width=True)

        with col_b:
            st.subheader("Weekly Sales Trend - Top 5 Products")
            weekly_top5 = (
                filtered
                .filter(pl.col("POS_DESCRIPTION").is_in(top5["POS_DESCRIPTION"].to_list()))
                .group_by(["WEEK", "POS_DESCRIPTION"])
                .agg(pl.col("TOTAL_SALES").sum())
                .sort("WEEK")
            )
            fig2 = px.line(
                weekly_top5.to_pandas(),
                x="WEEK",
                y="TOTAL_SALES",
                color="POS_DESCRIPTION",
                title="Weekly Sales Trend",
                labels={"TOTAL_SALES": "Total Sales ($)", "WEEK": "Week", "POS_DESCRIPTION": "Product"}
            )
            st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.subheader("Top 5 Products Summary")
    from great_tables import GT, style, loc
    import pandas as pd

    gt_data = (
        filtered
        .filter(pl.col("POS_DESCRIPTION").is_in(top5["POS_DESCRIPTION"].to_list()))
        .group_by("POS_DESCRIPTION")
        .agg([
            pl.col("TOTAL_SALES").sum().alias("Total Sales ($)"),
            pl.col("TOTAL_UNITS").sum().alias("Total Units Sold"),
            pl.col("WEEK").n_unique().alias("Weeks Active")
        ])
        .sort("Total Sales ($)", descending=True)
        .to_pandas()
    )

    gt_data["Avg Weekly Sales ($)"] = (
        gt_data["Total Sales ($)"] / gt_data["Weeks Active"]
    ).round(2)

    gt_data["Total Sales ($)"] = gt_data["Total Sales ($)"].round(2)

    gt = (
        GT(gt_data)
        .tab_header(
            title="Top 5 Products Performance Summary",
            subtitle="Filtered by selected stores and months"
        )
        .cols_label(
            POS_DESCRIPTION="Product",
        )
        .fmt_currency(columns=["Total Sales ($)", "Avg Weekly Sales ($)"])
        .fmt_integer(columns=["Total Units Sold", "Weeks Active"])
        .tab_style(
            style=style.fill(color="#e8f4f8"),
            locations=loc.body(rows=[0])
        )
        .tab_style(
            style=style.text(weight="bold"),
            locations=loc.column_labels()
        )
        .tab_source_note("Source: Cstore Transaction Data")
    )

    st.html(gt.as_raw_html())

elif page == "🥤 Packaged Beverages":
    st.title("🥤 Packaged Beverage Brand Analysis")
    st.markdown("Identify which beverage brands to keep or drop based on sales performance.")
    st.markdown("---")

    # ---- LOAD DATA ----
    sales = load_weekly_sales()
    stores = load_stores()

    # ---- ADD MONTH AND STORE LABELS ----
    month_map = {
        "01": "January", "02": "February", "03": "March",
        "04": "April", "05": "May", "06": "June",
        "07": "July", "08": "August", "09": "September",
        "10": "October", "11": "November", "12": "December"
    }

    sales = sales.with_columns(
        pl.col("WEEK").cast(pl.Utf8).str.slice(0, 7).alias("MONTH_KEY")
    ).with_columns(
        pl.col("MONTH_KEY").str.slice(5, 2).replace(month_map).alias("MONTH_NAME"),
        pl.col("MONTH_KEY").str.slice(0, 4).alias("YEAR")
    ).with_columns(
        (pl.col("MONTH_NAME") + " " + pl.col("YEAR")).alias("MONTH")
    )

    stores = stores.with_columns(pl.col("STORE_ID").cast(pl.Utf8))
    sales = sales.with_columns(pl.col("STORE_ID").cast(pl.Utf8))
    sales = sales.join(
        stores.select(["STORE_ID", "STORE_NAME", "CITY", "STATE"]),
        on="STORE_ID",
        how="left"
    ).with_columns(
        (pl.col("CITY") + ", " + pl.col("STATE")).alias("STORE_LABEL")
    )

    # ---- FILTER TO PACKAGED BEVERAGES ONLY ----
    beverages = sales.filter(pl.col("CATEGORY") == "Packaged Beverages")

    # ---- SIDEBAR FILTERS ----
    st.sidebar.markdown("### Filters")

    months = sorted(beverages["MONTH_KEY"].drop_nulls().unique().to_list())
    month_labels = []
    for m in months:
        year = m[:4]
        month_num = m[5:7]
        month_labels.append(month_map.get(month_num, month_num) + " " + year)

    month_lookup = dict(zip(month_labels, months))
    selected_month_labels = st.sidebar.multiselect(
        "Select Months", month_labels,
        default=month_labels[-3:] if len(month_labels) >= 3 else month_labels,
        key="bev_months"
    )
    selected_months = [month_lookup[m] for m in selected_month_labels]

    store_options = (
        beverages.select(["STORE_ID", "STORE_LABEL"])
        .unique()
        .sort("STORE_LABEL")
        .filter(pl.col("STORE_LABEL").is_not_null())
    )
    store_labels = store_options["STORE_LABEL"].to_list()
    store_ids = store_options["STORE_ID"].to_list()
    store_lookup = dict(zip(store_labels, store_ids))

    selected_store_labels = st.sidebar.multiselect(
        "Select Stores", store_labels,
        default=store_labels[:5],
        key="bev_stores"
    )
    selected_store_ids = [store_lookup[s] for s in selected_store_labels]

    # Subcategory filter
    subcategories = sorted(beverages["SUBCATEGORY"].drop_nulls().unique().to_list())
    selected_subcats = st.sidebar.multiselect(
        "Select Subcategories", subcategories,
        default=subcategories,
        key="bev_subcats"
    )

    # ---- APPLY FILTERS ----
    filtered = beverages.filter(
        (pl.col("MONTH_KEY").is_in(selected_months)) &
        (pl.col("STORE_ID").is_in(selected_store_ids)) &
        (pl.col("SUBCATEGORY").is_in(selected_subcats))
    )

    # ---- BRAND AGGREGATION ----
    brand_sales = (
        filtered
        .group_by("BRAND")
        .agg([
            pl.col("TOTAL_SALES").sum().alias("TOTAL_SALES"),
            pl.col("TOTAL_UNITS").sum().alias("TOTAL_UNITS"),
        ])
        .sort("TOTAL_SALES", descending=True)
        .filter(pl.col("BRAND").is_not_null())
    )

    # ---- KPIs ----
    st.subheader("Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    total_bev_sales = filtered["TOTAL_SALES"].sum()
    num_brands = brand_sales.height
    top_brand = brand_sales["BRAND"][0] if num_brands > 0 else "N/A"
    bottom_brand = brand_sales["BRAND"][-1] if num_brands > 0 else "N/A"

    col1.metric("Total Beverage Sales", f"${total_bev_sales:,.2f}")
    col2.metric("Total Brands", num_brands)
    col3.metric("Top Brand", top_brand)
    col4.metric("Lowest Performing Brand", bottom_brand)

    st.markdown("---")

    # ---- TABS ----
    tab1, tab2 = st.tabs(["📊 Charts", "📋 Brand Details"])

    with tab1:
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Top 10 Brands by Sales")
            top10_brands = brand_sales.head(10)
            fig1 = px.bar(
                top10_brands.to_pandas(),
                x="TOTAL_SALES",
                y="BRAND",
                orientation="h",
                title="Top 10 Beverage Brands",
                labels={"TOTAL_SALES": "Total Sales ($)", "BRAND": "Brand"},
                color="TOTAL_SALES",
                color_continuous_scale="Teal"
            )
            # User threshold line
            drop_threshold = st.number_input(
                "Mark brands to consider dropping (sales below $)",
                min_value=0.0,
                value=float(brand_sales["TOTAL_SALES"].mean()) if num_brands > 0 else 100.0,
                step=50.0,
                key="bev_threshold"
            )
            fig1.add_vline(x=drop_threshold, line_dash="dash", line_color="red",
                          annotation_text="Drop threshold")
            st.plotly_chart(fig1, use_container_width=True)

        with col_b:
            st.subheader("Sales by Subcategory Over Time")
            weekly_subcat = (
                filtered
                .group_by(["WEEK", "SUBCATEGORY"])
                .agg(pl.col("TOTAL_SALES").sum())
                .sort("WEEK")
                .filter(pl.col("SUBCATEGORY").is_not_null())
            )
            fig2 = px.line(
                weekly_subcat.to_pandas(),
                x="WEEK",
                y="TOTAL_SALES",
                color="SUBCATEGORY",
                title="Beverage Subcategory Trends",
                labels={"TOTAL_SALES": "Total Sales ($)", "WEEK": "Week"}
            )
            st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.subheader("Brand Performance Details")

        with st.expander("🔴 Brands to Consider Dropping", expanded=True):
            drop_candidates = brand_sales.filter(
                pl.col("TOTAL_SALES") < drop_threshold
            ).sort("TOTAL_SALES")
            if drop_candidates.height > 0:
                st.dataframe(drop_candidates.to_pandas(), use_container_width=True)
            else:
                st.info("No brands fall below the threshold.")

        with st.expander("✅ All Brands Summary", expanded=False):
            st.dataframe(brand_sales.to_pandas(), use_container_width=True)

elif page == "💳 Cash vs Credit":
    st.title("💳 Cash vs Credit Customer Comparison")
    st.markdown("Compare purchasing behavior between cash and credit customers.")
    st.markdown("---")

    # ---- LOAD DATA ----
    payments = load_weekly_payments()
    basket = load_basket_size()
    stores = load_stores()

    # ---- ADD MONTH AND STORE LABELS ----
    month_map = {
        "01": "January", "02": "February", "03": "March",
        "04": "April", "05": "May", "06": "June",
        "07": "July", "08": "August", "09": "September",
        "10": "October", "11": "November", "12": "December"
    }

    payments = payments.with_columns(
        pl.col("WEEK").cast(pl.Utf8).str.slice(0, 7).alias("MONTH_KEY")
    ).with_columns(
        pl.col("MONTH_KEY").str.slice(5, 2).replace(month_map).alias("MONTH_NAME"),
        pl.col("MONTH_KEY").str.slice(0, 4).alias("YEAR")
    ).with_columns(
        (pl.col("MONTH_NAME") + " " + pl.col("YEAR")).alias("MONTH")
    )

    stores = stores.with_columns(pl.col("STORE_ID").cast(pl.Utf8))
    payments = payments.with_columns(pl.col("STORE_ID").cast(pl.Utf8))
    payments = payments.join(
        stores.select(["STORE_ID", "CITY", "STATE"]),
        on="STORE_ID",
        how="left"
    ).with_columns(
        (pl.col("CITY") + ", " + pl.col("STATE")).alias("STORE_LABEL")
    )

    basket = basket.with_columns(
        pl.col("WEEK").cast(pl.Utf8).str.slice(0, 7).alias("MONTH_KEY"),
        pl.col("STORE_ID").cast(pl.Utf8)
    )

    # ---- SIMPLIFY PAYMENT TYPES INTO CASH VS CREDIT ----
    payments = payments.with_columns(
        pl.when(pl.col("PAYMENT_TYPE") == "CASH")
            .then(pl.lit("Cash"))
        .when(pl.col("PAYMENT_TYPE").is_in(["CREDIT", "DEBIT", "CARD", "FLEET", "GIFT CARD"]))
            .then(pl.lit("Credit/Card"))
        .otherwise(pl.lit("Other"))
        .alias("PAYMENT_GROUP")
    )

    basket = basket.with_columns(
        pl.when(pl.col("PAYMENT_TYPE") == "CASH")
            .then(pl.lit("Cash"))
        .when(pl.col("PAYMENT_TYPE").is_in(["CREDIT", "DEBIT", "CARD", "FLEET", "GIFT CARD"]))
            .then(pl.lit("Credit/Card"))
        .otherwise(pl.lit("Other"))
        .alias("PAYMENT_GROUP")
    )

    # ---- SIDEBAR FILTERS ----
    st.sidebar.markdown("### Filters")

    months = sorted(payments["MONTH_KEY"].drop_nulls().unique().to_list())
    month_labels = []
    for m in months:
        year = m[:4]
        month_num = m[5:7]
        month_labels.append(month_map.get(month_num, month_num) + " " + year)

    month_lookup = dict(zip(month_labels, months))
    selected_month_labels = st.sidebar.multiselect(
        "Select Months", month_labels,
        default=month_labels[-3:] if len(month_labels) >= 3 else month_labels,
        key="cc_months"
    )
    selected_months = [month_lookup[m] for m in selected_month_labels]

    store_options = (
        payments.select(["STORE_ID", "STORE_LABEL"])
        .unique()
        .sort("STORE_LABEL")
        .filter(pl.col("STORE_LABEL").is_not_null())
    )
    store_labels = store_options["STORE_LABEL"].to_list()
    store_ids = store_options["STORE_ID"].to_list()
    store_lookup = dict(zip(store_labels, store_ids))

    selected_store_labels = st.sidebar.multiselect(
        "Select Stores", store_labels,
        default=store_labels[:5],
        key="cc_stores"
    )
    selected_store_ids = [store_lookup[s] for s in selected_store_labels]

    payment_groups = st.sidebar.multiselect(
        "Payment Groups",
        ["Cash", "Credit/Card", "Other"],
        default=["Cash", "Credit/Card"],
        key="cc_groups"
    )

    # ---- APPLY FILTERS ----
    filtered_pay = payments.filter(
        (pl.col("MONTH_KEY").is_in(selected_months)) &
        (pl.col("STORE_ID").is_in(selected_store_ids)) &
        (pl.col("PAYMENT_GROUP").is_in(payment_groups))
    )

    filtered_basket = basket.filter(
        (pl.col("MONTH_KEY").is_in(selected_months)) &
        (pl.col("STORE_ID").is_in(selected_store_ids)) &
        (pl.col("PAYMENT_GROUP").is_in(payment_groups))
    )

    # ---- AGGREGATIONS ----
    pay_summary = (
        filtered_pay
        .group_by("PAYMENT_GROUP")
        .agg([
            pl.col("TRANSACTION_COUNT").sum().alias("Total Transactions"),
            pl.col("TOTAL_AMOUNT").sum().alias("Total Sales ($)"),
            pl.col("AVG_AMOUNT").mean().alias("Avg Transaction ($)")
        ])
        .sort("Total Sales ($)", descending=True)
    )

    basket_summary = (
        filtered_basket
        .group_by("PAYMENT_GROUP")
        .agg([
            pl.col("ITEM_COUNT").mean().alias("Avg Items per Transaction"),
            pl.col("TOTAL_AMOUNT").mean().alias("Avg Spend per Transaction ($)")
        ])
    )

    # ---- KPIs ----
    st.subheader("Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)

    cash_data = pay_summary.filter(pl.col("PAYMENT_GROUP") == "Cash")
    card_data = pay_summary.filter(pl.col("PAYMENT_GROUP") == "Credit/Card")

    cash_total = cash_data["Total Sales ($)"][0] if cash_data.height > 0 else 0
    card_total = card_data["Total Sales ($)"][0] if card_data.height > 0 else 0
    cash_txns = cash_data["Total Transactions"][0] if cash_data.height > 0 else 0
    card_txns = card_data["Total Transactions"][0] if card_data.height > 0 else 0

    col1.metric("Cash Total Sales", f"${cash_total:,.2f}")
    col2.metric("Credit/Card Total Sales", f"${card_total:,.2f}")
    col3.metric("Cash Transactions", f"{cash_txns:,}")
    col4.metric("Credit/Card Transactions", f"{card_txns:,}")

    st.markdown("---")

    # ---- TABS ----
    tab1, tab2 = st.tabs(["📊 Charts", "📋 Summary Table"])

    with tab1:
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Total Sales by Payment Type Over Time")
            weekly_pay = (
                filtered_pay
                .group_by(["WEEK", "PAYMENT_GROUP"])
                .agg(pl.col("TOTAL_AMOUNT").sum().alias("TOTAL_AMOUNT"))
                .sort("WEEK")
            )
            fig1 = px.line(
                weekly_pay.to_pandas(),
                x="WEEK",
                y="TOTAL_AMOUNT",
                color="PAYMENT_GROUP",
                title="Weekly Sales by Payment Type",
                labels={"TOTAL_AMOUNT": "Total Sales ($)", "WEEK": "Week", "PAYMENT_GROUP": "Payment Type"},
                color_discrete_map={"Cash": "#2196F3", "Credit/Card": "#FF9800", "Other": "#9E9E9E"}
            )
            # User threshold line
            sales_line = st.number_input(
                "Draw a weekly sales target line ($)",
                min_value=0.0,
                value=5000.0,
                step=500.0,
                key="cc_line"
            )
            fig1.add_hline(y=sales_line, line_dash="dash", line_color="red",
                          annotation_text=f"Target: ${sales_line:,.0f}")
            st.plotly_chart(fig1, use_container_width=True)

        with col_b:
            st.subheader("Total Items per Transaction")
            weekly_basket = (
                filtered_basket
                .group_by(["WEEK", "PAYMENT_GROUP"])
                .agg(pl.col("ITEM_COUNT").mean().alias("AVG_ITEMS"))
                .sort("WEEK")
            )
            fig2 = px.line(
                weekly_basket.to_pandas(),
                x="WEEK",
                y="AVG_ITEMS",
                color="PAYMENT_GROUP",
                title="Avg Items per Transaction by Payment Type",
                labels={"AVG_ITEMS": "Avg Items", "WEEK": "Week", "PAYMENT_GROUP": "Payment Type"},
                color_discrete_map={"Cash": "#2196F3", "Credit/Card": "#FF9800", "Other": "#9E9E9E"}
            )
            st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.subheader("Payment Type Summary")

    with st.expander("Total Sales & Transactions", expanded=True):
        st.dataframe(pay_summary.to_pandas(), use_container_width=True)

    with st.expander("Basket Size Comparison", expanded=True):
        st.dataframe(basket_summary.to_pandas(), use_container_width=True)

    st.markdown("---")
    st.subheader("🛒 Top Products by Payment Type")

    pay_prods = load_payment_products()

    pay_prods = pay_prods.with_columns(
        pl.when(pl.col("PAYMENT_TYPE") == "CASH")
            .then(pl.lit("Cash"))
        .when(pl.col("PAYMENT_TYPE").is_in(["CREDIT", "DEBIT", "CARD", "FLEET", "GIFT CARD"]))
            .then(pl.lit("Credit/Card"))
        .otherwise(pl.lit("Other"))
        .alias("PAYMENT_GROUP")
    ).filter(pl.col("PAYMENT_GROUP").is_in(payment_groups))

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Most Purchased Products - Cash")
        cash_prods = (
            pay_prods
            .filter(pl.col("PAYMENT_GROUP") == "Cash")
            .group_by("POS_DESCRIPTION")
            .agg([
                pl.col("PURCHASE_COUNT").sum().alias("PURCHASE_COUNT"),
                pl.col("TOTAL_SALES").sum().alias("TOTAL_SALES")
            ])
            .sort("PURCHASE_COUNT", descending=True)
            .head(10)
        )
        fig3 = px.bar(
            cash_prods.to_pandas(),
            x="PURCHASE_COUNT",
            y="POS_DESCRIPTION",
            orientation="h",
            title="Top 10 Products - Cash Customers",
            labels={"PURCHASE_COUNT": "Purchase Count", "POS_DESCRIPTION": "Product"},
            color="PURCHASE_COUNT",
            color_continuous_scale="Blues"
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col_b:
        st.subheader("Most Purchased Products - Credit/Card")
        card_prods = (
            pay_prods
            .filter(pl.col("PAYMENT_GROUP") == "Credit/Card")
            .group_by("POS_DESCRIPTION")
            .agg([
                pl.col("PURCHASE_COUNT").sum().alias("PURCHASE_COUNT"),
                pl.col("TOTAL_SALES").sum().alias("TOTAL_SALES")
            ])
            .sort("PURCHASE_COUNT", descending=True)
            .head(10)
        )
        fig4 = px.bar(
            card_prods.to_pandas(),
            x="PURCHASE_COUNT",
            y="POS_DESCRIPTION",
            orientation="h",
            title="Top 10 Products - Credit/Card Customers",
            labels={"PURCHASE_COUNT": "Purchase Count", "POS_DESCRIPTION": "Product"},
            color="PURCHASE_COUNT",
            color_continuous_scale="Oranges"
        )
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")
    st.subheader("📊 Product Comparison Summary")
    from great_tables import GT, style, loc
    import pandas as pd

    top_cash = cash_prods.head(5).to_pandas()
    top_cash["Payment Type"] = "Cash"
    top_card = card_prods.head(5).to_pandas()
    top_card["Payment Type"] = "Credit/Card"
    combined = pd.concat([top_cash, top_card])

    gt = (
        GT(combined)
        .tab_header(
            title="Top 5 Products by Payment Type",
            subtitle="Ranked by purchase count"
        )
        .cols_label(
            POS_DESCRIPTION="Product",
            PURCHASE_COUNT="Purchase Count",
            TOTAL_SALES="Total Sales ($)"
        )
        .fmt_currency(columns=["TOTAL_SALES"])
        .fmt_integer(columns=["PURCHASE_COUNT"])
        .tab_style(
            style=style.text(weight="bold"),
            locations=loc.column_labels()
        )
        .tab_source_note("Source: Cstore Transaction Data")
    )
    st.html(gt.as_raw_html())

elif page == "🏘️ Demographics":
    st.title("🏘️ Customer Area Demographics")
    st.markdown("Explore demographic data around store locations using the US Census API.")
    st.markdown("---")

    import requests
    import os

    CENSUS_API_KEY = "5159cc733693fa9a402f05f78d94f4fba196b73f"

    # ---- LOAD STORES ----
    stores = load_stores()
    stores = stores.with_columns(pl.col("STORE_ID").cast(pl.Utf8))

    # ---- SIDEBAR FILTERS ----
    st.sidebar.markdown("### Filters")

    store_options = (
        stores
        .filter(pl.col("CITY").is_not_null())
        .with_columns((pl.col("CITY") + ", " + pl.col("STATE")).alias("STORE_LABEL"))
        .select(["STORE_ID", "STORE_LABEL", "ZIP_CODE", "LATITUDE", "LONGITUDE"])
        .unique()
        .sort("STORE_LABEL")
    )

    store_labels = store_options["STORE_LABEL"].to_list()
    selected_store_label = st.sidebar.selectbox("Select a Store", store_labels, key="demo_store")

    selected_store = store_options.filter(
        (pl.col("STORE_LABEL") == selected_store_label)
    ).head(1)

    zip_code = selected_store["ZIP_CODE"][0] if selected_store.height > 0 else None

    # ---- FETCH CENSUS DATA ----
    @st.cache_data
    def get_census_data(zip_code, api_key):
        variables = {
            "B01003_001E": "Total Population",
            "B19013_001E": "Median Household Income",
            "B15003_022E": "Bachelor's Degree",
            "B15003_023E": "Master's Degree",
            "B23025_005E": "Unemployed",
            "B23025_002E": "Labor Force",
            "B25077_001E": "Median Home Value",
            "B01002_001E": "Median Age",
            "B11001_001E": "Total Households",
            "B17001_002E": "Below Poverty Level",
            "B08301_010E": "Public Transit Commuters",
            "B25003_002E": "Owner Occupied Housing",
        }

        var_string = ",".join(variables.keys())
        url = (
            f"https://api.census.gov/data/2022/acs/acs5"
            f"?get={var_string}"
            f"&for=zip%20code%20tabulation%20area:{zip_code}"
            f"&key={api_key}"
        )

        try:
            response = requests.get(url)
            data = response.json()
            if len(data) < 2:
                return None
            headers = data[0]
            values = data[1]
            result = {}
            for i, key in enumerate(variables.keys()):
                label = variables[key]
                val = values[i]
                try:
                    result[label] = float(val) if val not in [None, "-1", "-666666666"] else None
                except:
                    result[label] = None
            return result
        except Exception as e:
            st.error(f"Census API error: {e}")
            return None

    # ---- DISPLAY DEMOGRAPHICS ----
    if zip_code:
        st.subheader(f"Demographics for ZIP Code: {zip_code}")
        st.caption(f"Store: {selected_store_label} | Source: US Census ACS 5-Year Estimates (2022)")

        with st.spinner("Fetching Census data..."):
            demo_data = get_census_data(zip_code, CENSUS_API_KEY)

        if demo_data:
            # ---- KPIs ----
            st.subheader("Key Demographics")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Population", f"{int(demo_data.get('Total Population', 0) or 0):,}")
            col2.metric("Median Age", f"{demo_data.get('Median Age', 'N/A')}")
            col3.metric("Median Household Income", f"${int(demo_data.get('Median Household Income', 0) or 0):,}")
            col4.metric("Median Home Value", f"${int(demo_data.get('Median Home Value', 0) or 0):,}")

            st.markdown("---")

            # ---- TABS ----
            tab1, tab2 = st.tabs(["📊 Charts", "📋 Full Details"])

            with tab1:
                col_a, col_b = st.columns(2)

                with col_a:
                    st.subheader("Economic Indicators")
                    econ_data = {
                        "Metric": ["Median Income", "Median Home Value", "Below Poverty"],
                        "Value": [
                            demo_data.get("Median Household Income") or 0,
                            demo_data.get("Median Home Value") or 0,
                            demo_data.get("Below Poverty Level") or 0,
                        ]
                    }
                    import pandas as pd
                    fig1 = px.bar(
                        pd.DataFrame(econ_data),
                        x="Metric",
                        y="Value",
                        title="Economic Indicators",
                        color="Metric",
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    st.plotly_chart(fig1, use_container_width=True)

                with col_b:
                    st.subheader("Population Breakdown")
                    pop_data = {
                        "Category": [
                            "Total Households",
                            "Owner Occupied",
                            "Labor Force",
                            "Unemployed",
                            "Public Transit"
                        ],
                        "Count": [
                            demo_data.get("Total Households") or 0,
                            demo_data.get("Owner Occupied Housing") or 0,
                            demo_data.get("Labor Force") or 0,
                            demo_data.get("Unemployed") or 0,
                            demo_data.get("Public Transit Commuters") or 0,
                        ]
                    }
                    fig2 = px.bar(
                        pd.DataFrame(pop_data),
                        x="Category",
                        y="Count",
                        title="Population & Housing Breakdown",
                        color="Category",
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    st.plotly_chart(fig2, use_container_width=True)

            with tab2:
                st.subheader("Full Demographics Table")
                with st.expander("View All Variables", expanded=True):
                    demo_df = pd.DataFrame([
                        {"Demographic Variable": k, "Value": v}
                        for k, v in demo_data.items()
                    ])
                    st.dataframe(demo_df, use_container_width=True)

                with st.expander("Education Breakdown", expanded=False):
                    edu_data = {
                        "Degree": ["Bachelor's", "Master's"],
                        "Count": [
                            demo_data.get("Bachelor's Degree") or 0,
                            demo_data.get("Master's Degree") or 0,
                        ]
                    }
                    fig3 = px.pie(
                        pd.DataFrame(edu_data),
                        names="Degree",
                        values="Count",
                        title="Education Level Distribution"
                    )
                    st.plotly_chart(fig3, use_container_width=True)
        else:
            st.warning("No Census data found for this ZIP code. Try selecting a different store.")
    else:
        st.warning("No ZIP code found for selected store.")