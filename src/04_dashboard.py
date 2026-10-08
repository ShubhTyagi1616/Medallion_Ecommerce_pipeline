import os
import io
import requests
import polars as pl
import pandas as pd
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="DataVinci E-Commerce Dashboard", layout="wide")
st.title("🛍️ E-Commerce Performance Dashboard")
st.markdown("This dashboard visualises the Gold Layer data to answer key business questions.")

# --- DATABRICKS CONNECTION ---
load_dotenv()
DATABRICKS_URL = os.getenv("DATABRICKS_INSTANCE_URL").rstrip('/')
TOKEN = os.getenv("DATABRICKS_PAT_TOKEN")

CATALOG = "remote_ecommerce_medallion_pipeline"
SCHEMA = "medallion"
GOLD_VOLUME = "gold_aggregated_data"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# --- DATA FETCHING (CACHED FOR SPEED) ---
@st.cache_data
def load_gold_data(filename):
    gold_path = f"/Volumes/{CATALOG}/{SCHEMA}/{GOLD_VOLUME}/{filename}"
    get_endpoint = f"{DATABRICKS_URL}/api/2.0/fs/files{gold_path}"
    
    response = requests.get(get_endpoint, headers=HEADERS)
    if response.status_code == 200:
        parquet_bytes = io.BytesIO(response.content)
        return pl.read_parquet(parquet_bytes).to_pandas()
    else:
        st.error(f"Failed to fetch {filename} from Databricks: {response.text}")
        return pd.DataFrame()

with st.spinner("Fetching Gold Layer data from Databricks..."):
    df_dist = load_gold_data("Gold_Transaction_Distribution.parquet")
    df_time = load_gold_data("Gold_Revenue_Over_Time.parquet")
    df_cat = load_gold_data("Gold_Category_Revenue.parquet")
    df_cust = load_gold_data("Gold_Customer_Behavior.parquet")

if not df_dist.empty and not df_time.empty and not df_cat.empty and not df_cust.empty:
    
    # --- VISUALISATION 1: Transaction Amount Distribution (UPGRADED) ---
    st.header("a. Distribution of Transaction Amounts")
    
    # Adding a marginal violin plot creates a highly professional, dual-layered visualization
    fig_dist = px.histogram(
        df_dist, 
        x="TransactionTotal", 
        nbins=120,
        marginal="violin", 
        title="Frequency & Density of Transaction Values",
        labels={"TransactionTotal": "Transaction Value (£)"},
        color_discrete_sequence=["#00FFAA"], # Neon accent for dark mode
        opacity=0.85
    )
    # Focus the view to exclude extreme outliers that flatten the chart
    fig_dist.update_xaxes(range=[0, df_dist['TransactionTotal'].quantile(0.95)]) 
    fig_dist.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_dist, use_container_width=True)
    st.caption("Interpretation: The histogram displays transaction volume, while the top violin plot highlights data density and probability distribution, confirming a high-volume, lower-ticket retail model.")

    st.markdown("---")

    # --- VISUALISATION 2: Revenue Over Time ---
    st.header("b. Total Transaction Amount Over Time")
    fig_time = px.line(
        df_time, 
        x="Date", 
        y="DailyRevenue", 
        title="Daily Revenue Trend",
        labels={"DailyRevenue": "Total Revenue (£)", "Date": "Transaction Date"},
        color_discrete_sequence=["#00BFFF"] # Deep Sky Blue
    )
    fig_time.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_time, use_container_width=True)
    st.caption("Interpretation: Revenue experiences distinct peaks, indicating potential seasonal trends, marketing campaign successes, or specific high-volume wholesale purchase days.")

    st.markdown("---")
    
    col1, col2 = st.columns(2)

    with col1:
        # --- VISUALISATION 3: Category Revenue ---
        st.header("c. Revenue by Category")
        fig_cat = px.bar(
            df_cat.head(10), 
            x="CategoryRevenue", 
            y="Category", 
            orientation='h',
            title="Top 10 Product Categories by Revenue",
            labels={"CategoryRevenue": "Total Revenue (£)", "Category": "Product Category"},
            color="CategoryRevenue",
            color_continuous_scale="Viridis" # Creates a nice heat-mapped bar chart
        )
        fig_cat.update_layout(yaxis={'categoryorder':'total ascending'}, template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_cat, use_container_width=True)
        st.caption("Interpretation: This chart immediately identifies the core product lines driving the company's financial success.")

    with col2:
        # --- VISUALISATION 4: Customer Behavior ---
        st.header("d. Customer Purchasing Behavior")
        fig_cust = px.scatter(
            df_cust, 
            x="TotalOrders", 
            y="TotalSpend", 
            title="Customer Lifetime Value vs. Order Frequency",
            labels={"TotalOrders": "Number of Orders Made", "TotalSpend": "Total Spend (£)"},
            opacity=0.7,
            color="AvgOrderValue",
            color_continuous_scale="Plasma" # Vibrant dark-mode friendly scale
        )
        fig_cust.update_xaxes(range=[0, df_cust['TotalOrders'].quantile(0.99)])
        fig_cust.update_yaxes(range=[0, df_cust['TotalSpend'].quantile(0.99)])
        fig_cust.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_cust, use_container_width=True)
        st.caption("Interpretation: The cluster in the bottom-left represents regular consumers. The trailing outliers represent wholesale/B2B clients placing high-value, frequent orders.")