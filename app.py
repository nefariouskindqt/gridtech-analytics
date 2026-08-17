import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px

# Page configuration
st.set_page_config(
    page_title="GridTech Energy Analytics",
    page_icon="⚡",
    layout="wide"
)

# 1. Database Connection Helper using Streamlit Secrets (Updated for Supabase)
@st.cache_resource
def get_connection():
    # Supabase uses a single URI connection string
    return psycopg2.connect(st.secrets["DATABASE_URL"])

conn = get_connection()

# Helper function to run SQL queries into DataFrames
def run_query(query):
    with conn.cursor() as cur:
        return pd.read_sql(query, conn)

# --- Dashboard Header ---
st.title("⚡ GridTech Power & Sales Dashboard")
st.markdown("Real-time monitoring and business intelligence driven by PostgreSQL.")

st.divider()

# --- Section 1: Top-Level Business KPIs ---
st.subheader("📊 Business Overview")

kpi_query = """
SELECT 
    COUNT(DISTINCT so.order_id) AS total_orders,
    COUNT(DISTINCT so.customer_id) AS total_active_customers,
    SUM(oi.quantity * p.unit_price) AS total_revenue
FROM sales_orders so
JOIN order_items oi ON so.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id;
"""
df_kpi = run_query(kpi_query)

col1, col2, col3 = st.columns(3)
col1.metric("Total Orders Placed", f"{df_kpi['total_orders'][0]:,}")
col2.metric("Active Customers", f"{df_kpi['total_active_customers'][0]:,}")
col3.metric("Gross Revenue", f"₱{df_kpi['total_revenue'][0]:,.2f}")

st.divider()

# --- Section 2: Sales & Revenue Visualizations ---
st.subheader("📈 Product & Regional Analytics")

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    top_products_query = """
    SELECT 
        p.product_name,
        SUM(oi.quantity * p.unit_price) AS revenue
    FROM products p
    JOIN order_items oi ON p.product_id = oi.product_id
    GROUP BY p.product_name
    ORDER BY revenue DESC
    LIMIT 7;
    """
    df_top_prod = run_query(top_products_query)
    
    fig_prod = px.bar(
        df_top_prod,
        x="revenue",
        y="product_name",
        orientation="h",
        title="Top 7 Revenue-Generating Products",
        labels={"revenue": "Revenue (PHP)", "product_name": "Product"},
        color="revenue",
        color_continuous_scale="Blues"
    )
    fig_prod.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_prod, use_container_width=True)

with chart_col2:
    city_query = """
    SELECT 
        city,
        COUNT(customer_id) AS total_clients
    FROM customers
    GROUP BY city
    ORDER BY total_clients DESC;
    """
    df_cities = run_query(city_query)
    
    fig_city = px.pie(
        df_cities,
        values="total_clients",
        names="city",
        title="Customer Distribution by City",
        hole=0.4
    )
    st.plotly_chart(fig_city, use_container_width=True)

st.divider()

# --- Section 3: Telemetry Time-Series Analysis ---
st.subheader("🔋 IoT System Telemetry Monitor")

systems_query = "SELECT DISTINCT system_id FROM iot_telemetry ORDER BY system_id;"
available_systems = run_query(systems_query)["system_id"].tolist()

selected_system = st.selectbox("Select System ID:", available_systems)

telemetry_query = f"""
SELECT 
    timestamp,
    voltage_v,
    current_a,
    (voltage_v * current_a) AS power_watts,
    panel_temp_c,
    status_code
FROM iot_telemetry
WHERE system_id = '{selected_system}'
ORDER BY timestamp ASC;
"""
df_telemetry = run_query(telemetry_query)

fig_telemetry = px.line(
    df_telemetry,
    x="timestamp",
    y="power_watts",
    title=f"Power Output (Watts) Over Time for {selected_system}",
    labels={"timestamp": "Time", "power_watts": "Calculated Power (W)"}
)
st.plotly_chart(fig_telemetry, use_container_width=True)

with st.expander("View Recent Logs Data Table"):
    st.dataframe(df_telemetry.tail(100), use_container_width=True)
