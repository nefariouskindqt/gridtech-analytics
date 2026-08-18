import streamlit as st
import pandas as pd
import plotly.express as px
import base64

# --- 1. Page configuration ---
st.set_page_config(
    page_title="GridTech Energy Analytics",
    page_icon="⚡",
    layout="wide"
)

# --- 2. Custom Background Function ---
def set_background(image_file):
    try:
        with open(image_file, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode()
        
        # Adds the background image with a dark tinted overlay for readability
        css = f"""
        <style>
        .stApp {{
            background: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), 
                        url("data:image/jpg;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        /* Make the top header transparent so it blends in */
        header[data-testid="stHeader"] {{
            background-color: transparent !important;
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Background image '{image_file}' not found. Please ensure it is uploaded to your GitHub repository.")

# Call the function with your image's exact file name
set_background("image_4a4d08.jpg")


# --- 3. Database Connection ---
# We use st.secrets to explicitly pass the exact Supabase connection string.
conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])

# Helper function to run SQL queries and return a Pandas DataFrame
def run_query(query):
    # ttl="10m" caches the data for 10 minutes so it doesn't overload your database
    return conn.query(query, ttl="10m")


# --- 4. Dashboard Header ---
st.title("⚡ GridTech Power & Sales Dashboard")
st.markdown("Real-time monitoring and business intelligence driven by PostgreSQL.")

st.divider()

# --- 5. Application Logic with Error Handling ---
# We wrap the app in a try-except block so Streamlit doesn't redact errors!
try:
    # --- Section A: Top-Level Business KPIs ---
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

    # --- Section B: Sales & Revenue Visualizations ---
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
        fig_prod.update_layout(yaxis=dict(autorange="reversed"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
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
        fig_city.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_city, use_container_width=True)

    st.divider()

    # --- Section C: Telemetry Time-Series Analysis ---
    st.subheader("🔋 IoT System Telemetry Monitor")

    # Get list of unique systems for the dropdown menu
    systems_query = "SELECT DISTINCT system_id FROM iot_telemetry ORDER BY system_id;"
    available_systems = run_query(systems_query)["system_id"].tolist()

    selected_system = st.selectbox("Select System ID:", available_systems)

    # Fetch time-series data for the selected system
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

    # Line Chart
    fig_telemetry = px.line(
        df_telemetry,
        x="timestamp",
        y="power_watts",
        title=f"Power Output (Watts) Over Time for {selected_system}",
        labels={"timestamp": "Time", "power_watts": "Calculated Power (W)"}
    )
    fig_telemetry.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_telemetry, use_container_width=True)

    # Raw Data Table
    with st.expander("View Recent Logs Data Table"):
        st.dataframe(df_telemetry.tail(100), use_container_width=True)

except Exception as e:
    # If the database connection fails, this will display the true error beautifully on the dashboard!
    st.error(f"🚨 **Database Connection Error:** {str(e)}")
    st.info("Please verify your Supabase database is active and the connection string is correct in your Streamlit secrets.")
