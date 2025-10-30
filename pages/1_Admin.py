import streamlit as st
import pymysql  
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from sqlalchemy import create_engine
import geopandas as gpd
from zipfile import ZipFile
import os
import tempfile

# ✅ **Set Page Configuration (FIRST in your script)**
def set_page_config():
    st.set_page_config(
        layout="wide",
        page_title="Outage Management System",
        page_icon="⚡"
    )

# ✅ **Apply Full-Width Styling**
def apply_full_width_styles():
    st.markdown("""
        <style>
            /* Main container */
            .main .block-container {
                max-width: 100% !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            
            /* Maps */
            .stMap {
                width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            
            .folium-map {
                width: 100% !important;
                min-width: 100% !important;
            }
            
            /* Charts */
            .stPlotlyChart {
                width: 100% !important;
            }
            
            /* Dataframes */
            .stDataFrame {
                width: 100% !important;
            }
            
            /* Remove extra padding */
            .stApp {
                padding: 0 !important;
                margin: 0 !important;
            }
        </style>
    """, unsafe_allow_html=True)

# ✅ **SQLAlchemy Database Connection**
import streamlit as st
import pymysql

def connect_db():
    conn = pymysql.connect(
        host=st.secrets["mysql"]["host"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        port=st.secrets["mysql"]["port"],
        ssl={"ssl": {}}
    )
    return conn


# ✅ **Fetch Records from a Table**
def fetch_records(table_name):
    engine = connect_db()
    query = f"SELECT * FROM {table_name}"
    data = pd.read_sql_query(query, engine)
    return data

# ✅ **Fetch Customer Data**
def fetch_customer_data():
    engine = connect_db()
    query = "SELECT id, name, latitude, longitude FROM Customer"
    data = pd.read_sql_query(query, engine)
    return data

customers = fetch_customer_data()
print(customers.head())  # Verify the first few rows

# ✅ **Fetch Crew Data**
def fetch_crew_data():
    engine = connect_db()
    query = "SELECT id, name, latitude, longitude FROM Crew"
    data = pd.read_sql_query(query, engine)
    return data

# ✅ **Map Visualization for Customers**
def display_customer_map():
    st.subheader("🌍 View All Customer Locations")
    customers = fetch_customer_data()
    if not customers.empty:
        m = folium.Map(location=[-1.1018, 37.0144], zoom_start=10)
        for _, row in customers.iterrows():
            folium.Marker(
                [row["latitude"], row["longitude"]],
                popup=f"👤 Customer: {row['name']}",
                icon=folium.Icon(color="green")
            ).add_to(m)
        st_folium(m, width='100%', height=500)
    else:
        st.info("ℹ️ No customer locations found.")

# ✅ **Map Visualization for Crews**
def display_crew_map():
    st.subheader("👷 View All Crew Locations")
    crews = fetch_crew_data()
    if not crews.empty:
        m = folium.Map(location=[-1.1018, 37.0144], zoom_start=10)
        for _, row in crews.iterrows():
            folium.Marker(
                [row["latitude"], row["longitude"]],
                popup=f"👷 Crew: {row['name']}",
                icon=folium.Icon(color="blue")
            ).add_to(m)
        st_folium(m, width='100%', height=500)
    else:
        st.info("ℹ️ No crew locations found.")

# ✅ **Fetch Outages with Customer Details**
def fetch_outages():
    engine = connect_db()
    query = """
    SELECT o.id, c.meter_number, c.name AS customer_name, c.latitude, c.longitude, 
           o.description, o.status, o.assigned_crew_id, o.resolved_at, o.report_time
    FROM Outage o
    JOIN Customer c ON o.customer_id = c.id
    WHERE c.latitude IS NOT NULL AND c.longitude IS NOT NULL
    """
    data = pd.read_sql_query(query, engine)
    return data

# ✅ **Fetch Crew Details**
def fetch_crew():
    engine = connect_db()
    query = "SELECT id, name, latitude, longitude, status FROM Crew"
    data = pd.read_sql_query(query, engine)
    return data

# ✅ **Update Outage Status**
def update_outage_status(outage_id, new_status, assigned_crew_id):
    engine = connect_db()
    with engine.connect() as conn:
        try:
            if new_status == "Resolved":
                conn.execute("""
                    UPDATE Outage 
                    SET status = %s, assigned_crew_id = %s, resolved_at = NOW() 
                    WHERE id = %s
                """, (new_status, assigned_crew_id, outage_id))
            else:
                conn.execute("""
                    UPDATE Outage 
                    SET status = %s, assigned_crew_id = %s, resolved_at = NULL 
                    WHERE id = %s
                """, (new_status, assigned_crew_id, outage_id))
            conn.commit()
            st.success(f"✅ Outage {outage_id} updated to '{new_status}' and assigned to Crew {assigned_crew_id}")
        except Exception as e:
            conn.rollback()
            st.error(f"❌ Error updating outage status: {e}")

# ✅ **Send Notification**
def send_notification(user_id, message):
    engine = connect_db()
    with engine.connect() as conn:
        try:
            conn.execute("""
                INSERT INTO Notification (user_id, message, status) 
                VALUES (%s, %s, 'unread')
            """, (user_id, message))
            conn.commit()
        except Exception as e:
            st.error(f"❌ Error sending notification: {e}")

# ✅ **Delete a Record**
def delete_record(table_name, record_id):
    engine = connect_db()
    with engine.connect() as conn:
        try:
            conn.execute(f"DELETE FROM {table_name} WHERE id = %s", (record_id,))
            conn.commit()
            st.success(f"✅ Record {record_id} deleted successfully from {table_name}")
        except Exception as e:
            conn.rollback()
            st.error(f"❌ Error deleting record: {e}")

# ✅ **Edit a Record**
def edit_record(table_name, record_id, column, new_value):
    engine = connect_db()
    with engine.connect() as conn:
        try:
            conn.execute(f"UPDATE {table_name} SET {column} = %s WHERE id = %s", (new_value, record_id))
            conn.commit()
            st.success(f"✅ Record {record_id} updated in {table_name}")
        except Exception as e:
            conn.rollback()
            st.error(f"❌ Error editing record: {e}")

# Fetch Tasks
def fetch_tasks():
    engine = connect_db()
    query = """
    SELECT t.id, c.name AS crew_name, o.description AS outage_description, 
           t.distance, t.eta, t.status
    FROM Task t
    JOIN Crew1 c ON t.crew_id = c.id
    JOIN Outage o ON t.outage_id = o.id
    """
    data = pd.read_sql_query(query, engine)
    return data

# SLA Compliance Tracking
def fetch_sla_compliance(sla_threshold_hours=24):
    engine = connect_db()
    query = """
        SELECT id, customer_id, report_time, resolved_at, status,
               TIMESTAMPDIFF(HOUR, report_time, resolved_at) AS resolution_time_hours
        FROM Outage
        WHERE status = 'Resolved' AND resolved_at IS NOT NULL
    """
    data = pd.read_sql_query(query, engine)
    data["sla_compliant"] = data["resolution_time_hours"] <= sla_threshold_hours
    return data

# Fetch Messages
def fetch_messages(sender_id, receiver_id):
    engine = connect_db()
    query = """
    SELECT sender_id, message, timestamp
    FROM Chat
    WHERE (sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)
    ORDER BY timestamp ASC
    """
    data = pd.read_sql_query(query, engine, params=(sender_id, receiver_id, receiver_id, sender_id))
    return data

def send_mass_message(sender_id, message, recipient_group="all"):
    engine = connect_db()
    with engine.connect() as conn:
        try:
            if recipient_group == "all":
                recipients = conn.execute("SELECT id FROM User").fetchall()
            elif recipient_group == "customers":
                recipients = conn.execute("SELECT id FROM Customer").fetchall()
            elif recipient_group == "crews":
                recipients = conn.execute("SELECT id FROM Crew").fetchall()
            else:
                raise ValueError("Invalid recipient group specified.")
            
            for recipient_id in recipients:
                conn.execute("""
                    INSERT INTO Notification (user_id, message, status)
                    VALUES (%s, %s, 'unread')
                """, (recipient_id[0], message))
            
            conn.commit()
            st.success(f"✅ Mass message sent to {len(recipients)} recipients!")
        except Exception as e:
            conn.rollback()
            st.error(f"❌ Error sending mass message: {e}")

# Fetch Crew
def fetch_crew():
    engine = connect_db()
    query = "SELECT id, name, latitude, longitude, status FROM Crew"
    data = pd.read_sql_query(query, engine)
    return data

def update_crew_status(crew_id, new_status):
    engine = connect_db()
    with engine.connect() as conn:
        try:
            conn.execute("""
                UPDATE Crew1 
                SET status = %s 
                WHERE id = %s
            """, (new_status, crew_id))
            conn.commit()
            st.success(f"✅ Crew {crew_id} status updated to '{new_status}'")
        except Exception as e:
            conn.rollback()
            st.error(f"❌ Error updating crew status: {e}")

def get_active_crew_count():
    engine = connect_db()
    with engine.connect() as conn:
        try:
            result = conn.execute("""
                SELECT COUNT(*) 
                FROM Crew1 
                WHERE status != 'Available'
            """).fetchone()
            return result[0] if result else 0
        except Exception as e:
            st.error(f"❌ Error fetching active crew count: {e}")
            return 0

# Fetch Notifications 
def fetch_notifications():
    engine = connect_db()
    query = """
        SELECT id, user_id, message, status, timestamp
        FROM Notification
        ORDER BY timestamp DESC
    """
    data = pd.read_sql_query(query, engine)
    return data

def mark_notification_as_read(notification_id):
    engine = connect_db()
    with engine.connect() as conn:
        try:
            conn.execute("""
                UPDATE Notification 
                SET status = 'read' 
                WHERE id = %s
            """, (notification_id,))
            conn.commit()
            st.success(f"✅ Notification {notification_id} marked as read")
        except Exception as e:
            conn.rollback()
            st.error(f"❌ Error marking notification as read: {e}")

# ✅ **Map Visualization**
def display_map(data, entity_type):
    st.subheader(f"🌍 {entity_type.capitalize()} Locations")
    m = folium.Map(
        location=[-1.1018, 37.0144], 
        zoom_start=10,
        width='100%',
        height=500
    )
    for _, row in data.iterrows():
        folium.Marker(
            [row["latitude"], row["longitude"]],
            popup=f"{row['name']}",
            icon=folium.Icon(color="blue" if entity_type == "crew" else "green")
        ).add_to(m)
    st_folium(m, use_container_width=True)

def display_outage_heatmap():
    st.subheader("🔥 Outage Heatmap")
    outages = fetch_outages()
    if not outages.empty:
        valid_outages = outages.dropna(subset=["latitude", "longitude"])
        if not valid_outages.empty:
            m = folium.Map(location=[-1.1018, 37.0144], zoom_start=10)
            heat_data = [[row["latitude"], row["longitude"]] for _, row in valid_outages.iterrows()]
            folium.plugins.HeatMap(heat_data, radius=15).add_to(m)
            st_folium(m, width='100%', height=500)
        else:
            st.info("ℹ️ No valid outage locations found.")
    else:
        st.info("ℹ️ No outages found.")

# ✅ **Update Chart Display Functions**
def display_pie_chart(data, title):
    fig = px.pie(
        data, 
        names="Status", 
        values="Count", 
        title=title,
        width=1200
    )
    st.plotly_chart(fig, use_container_width=True)

def display_bar_chart(data, x, y, title):
    fig = px.bar(
        data,
        x=x,
        y=y,
        title=title,
        width=1200
    )
    st.plotly_chart(fig, use_container_width=True)

# ✅ **Update Dataframe Display**
def display_dataframe(df):
    st.dataframe(
        df,
        use_container_width=True,
        height=400
    )

def fetch_all_outage_history():
    engine = connect_db()
    query = """
        SELECT o.id AS outage_id, 
               c.meter_number, 
               c.name AS customer_name, 
               c.latitude, 
               c.longitude, 
               o.description, 
               o.status, 
               o.assigned_crew_id, 
               o.report_time, 
               o.resolved_at,
               TIMESTAMPDIFF(HOUR, o.report_time, COALESCE(o.resolved_at, NOW())) AS duration_hours
        FROM Outage o
        JOIN Customer c ON o.customer_id = c.id
        ORDER BY o.report_time DESC
    """
    data = pd.read_sql_query(query, engine)
    return data

def display_outage_history_per_customer():
    st.subheader("📊 Outage Counts Per Customer")
    outages = fetch_all_outage_history()
    if not outages.empty:
        outage_counts = outages.groupby('customer_name').size().reset_index(name='Total Outages')
        status_counts = outages.groupby(['customer_name', 'status']).size().unstack(fill_value=0)
        result_table = outage_counts.merge(status_counts, on='customer_name', how='left')
        if 'Resolved' in result_table.columns:
            result_table['Resolution Rate'] = (result_table['Resolved'] / result_table['Total Outages'] * 100).round(1).astype(str) + '%'
        else:
            result_table['Resolution Rate'] = '0%'
        result_table = result_table.sort_values('Total Outages', ascending=False)
        st.dataframe(
            result_table.style
            .background_gradient(subset=['Total Outages'], cmap='YlOrRd')
            .format({'Total Outages': '{:.0f}'}, precision=0),
            use_container_width=True,
            height=min(800, 45 * len(result_table))
        )
    else:
        st.info("ℹ️ No outage history found.")

# ✅ **Streamlit UI**
st.title("⚡ Admin Panel - Outage Management System")

# ✅ **Sidebar Menu**
menu = st.sidebar.radio("📌 Select Action", ["📋 View Outages", "👷 Manage Crew", "👥 Manage Customers", "📊 Analytics"])

# ✅ **View & Manage Outages**
if menu == "📋 View Outages":
    st.header("📋 Outage Reports")
    outages = fetch_outages()
    if not outages.empty:
        st.dataframe(outages)
        st.subheader("🛠 Update Outage Status")
        outage_id = st.number_input("Enter Outage ID:", min_value=1, step=1)
        new_status = st.selectbox("Select New Status:", ["Pending", "Assigned", "In Progress", "Resolved"])
        assigned_crew_id = st.number_input("Enter Crew ID to Assign:", min_value=1, step=1)
        if st.button("✅ Update Outage"):
            update_outage_status(outage_id, new_status, assigned_crew_id)
            send_notification(assigned_crew_id, f"You have been assigned to outage ID {outage_id}")
        st.subheader("❌ Delete Outage")
        delete_outage_id = st.number_input("Enter Outage ID to Delete:", min_value=1, step=1)
        if st.button("🗑 Delete Outage"):
            delete_record("Outage", delete_outage_id)
    else:
        st.info("ℹ️ No outages found.")

# ✅ **Manage Crew**
elif menu == "👷 Manage Crew":
    st.header("👷 Crew Management")
    crew = fetch_crew()
    if not crew.empty:
        st.dataframe(crew)
        st.subheader("✏️ Edit Crew Details")
        crew_id = st.number_input("Enter Crew ID:", min_value=1, step=1)
        column = st.selectbox("Select Field to Edit:", ["name", "latitude", "longitude", "status"])
        new_value = st.text_input("Enter New Value:")
        if st.button("✅ Update Crew"):
            edit_record("Crew", crew_id, column, new_value)
        st.subheader("❌ Delete Crew")
        delete_crew_id = st.number_input("Enter Crew ID to Delete:", min_value=1, step=1)
        if st.button("🗑 Delete Crew"):
            delete_record("Crew", delete_crew_id)
        display_map(crew, "crew")
    else:
        st.info("ℹ️ No crew members found.")

# ✅ **Manage Customers**
elif menu == "👥 Manage Customers":
    st.header("👥 Customer Management")
    customers = fetch_records("Customer")
    st.dataframe(customers)
    st.subheader("✏️ Edit Customer Details")
    customer_id = st.number_input("Enter Customer ID:", min_value=1, step=1)
    column = st.selectbox("Select Field to Edit:", ["meter_number", "name", "latitude", "longitude"])
    new_value = st.text_input("Enter New Value:")
    if st.button("✅ Update Customer"):
        edit_record("Customer", customer_id, column, new_value)
    st.subheader("❌ Delete Customer")
    delete_customer_id = st.number_input("Enter Customer ID to Delete:", min_value=1, step=1)
    if st.button("🗑 Delete Customer"):
        delete_record("Customer", delete_customer_id)
    st.subheader("🌍 View All Customer Locations")
    m = folium.Map(location=[-1.1018, 37.0144], zoom_start=10)
    for _, row in customers.iterrows():
        folium.Marker(
           [row["latitude"], row["longitude"]],
           popup=f"👤 Customer: {row['name']}<br>Meter Number: {row['meter_number']}<br>Coordinates: ({row['latitude']}, {row['longitude']})",
           icon=folium.Icon(icon="home", prefix="fa", color="green")
        ).add_to(m)
    st_folium(m, width=700, height=500)

# ✅ **Analytics Dashboard**
elif menu == "📊 Analytics":
    st.header("📊 Admin Dashboard - Analytics Overview")
    st.markdown("---")  # Separator for visual clarity

    # Fetch Data
    customers = fetch_records("Customer")
    crew = fetch_crew()
    outages = fetch_outages()

    # Section 1: Key Metrics
    st.subheader("📋 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Customers", len(customers))
    with col2:
        active_crews = len(crew[crew["status"] == "Available"]) if not crew.empty else 0
        st.metric("Active Crews", active_crews)
    with col3:
        assigned_crews = len(crew[crew["status"] == "Busy"]) if not crew.empty else 0
        st.metric("Assigned Crews", assigned_crews)
    with col4:
        total_outages = len(outages) if not outages.empty else 0
        st.metric("Total Outages", total_outages)
    
    col5, col6, col7 = st.columns(3)
    with col5:
        resolved_outages = len(outages[outages["status"] == "Resolved"]) if not outages.empty else 0
        st.metric("Resolved Outages", resolved_outages)
    with col6:
        pending_outages = len(outages[outages["status"] == "Pending"]) if not outages.empty else 0
        st.metric("Pending Outages", pending_outages)
    with col7:
        in_progress_outages = len(outages[outages["status"] == "In Progress"]) if not outages.empty else 0
        st.metric("In Progress Outages", in_progress_outages)
    st.markdown("---")

    # Section 2: Outage Visualizations
    st.subheader("📊 Outage Insights")
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("#### Outage Status Distribution")
        outage_status_counts = outages["status"].value_counts().reset_index()
        outage_status_counts.columns = ["Status", "Count"]
        if not outage_status_counts.empty:
            fig_status = px.pie(outage_status_counts, names="Status", values="Count", title="Outage Status Breakdown")
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("ℹ️ No outage status data available.")
    
    with col_right:
        st.markdown("#### Real-Time Active Outages Map")
        active_outages = outages[outages["status"].isin(["Pending", "Assigned", "In Progress"])]
        if not active_outages.empty:
            m_active = folium.Map(location=[-1.1018, 37.0144], zoom_start=10)
            for _, row in active_outages.iterrows():
                folium.Marker(
                    [row["latitude"], row["longitude"]],
                    popup=f"⚠️ Outage: {row['description']}",
                    icon=folium.Icon(color="red")
                ).add_to(m_active)
            st_folium(m_active, use_container_width=True, height=400)
        else:
            st.info("ℹ️ No active outages to display.")
    st.markdown("---")

    # Section 3: Crew and Outage Analysis
    st.subheader("👷 Crew and Outage Analysis")
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("#### Crew Workload Distribution")
        crew_workload = (
            outages[outages["assigned_crew_id"].notnull()]
            .groupby("assigned_crew_id")
            .size()
            .reset_index(name="Task Count")
        )
        if not crew_workload.empty:
            crew_workload = crew_workload.merge(crew[["id", "name"]], left_on="assigned_crew_id", right_on="id", how="left")
            crew_workload = crew_workload[["name", "Task Count"]]
            if not crew_workload.empty:
                fig_crew = px.bar(crew_workload, x="name", y="Task Count", title="Tasks Assigned to Each Crew")
                st.plotly_chart(fig_crew, use_container_width=True)
            else:
                st.info("ℹ️ No tasks assigned to crews yet.")
        else:
            st.info("ℹ️ No tasks assigned to crews yet.")
    
    with col_right:
        st.markdown("#### Outage Heatmap")
        valid_outages = outages.dropna(subset=["latitude", "longitude"])
        if not valid_outages.empty:
            m = folium.Map(location=[-1.1018, 37.0144], zoom_start=10)
            heat_data = [[row["latitude"], row["longitude"]] for _, row in valid_outages.iterrows()]
            folium.plugins.HeatMap(heat_data, radius=15).add_to(m)
            st_folium(m, use_container_width=True, height=400)
        else:
            st.info("ℹ️ No valid outage locations for heatmap.")
    st.markdown("---")

    # Section 4: Detailed Reports
    st.subheader("📈 Detailed Reports")
    with st.expander("⏳ SLA Compliance Report"):
        sla_threshold_hours = st.number_input("Enter SLA Threshold (in hours):", value=24, min_value=1)
        sla_data = fetch_sla_compliance(sla_threshold_hours)
        if not sla_data.empty:
            compliance_rate = sla_data["sla_compliant"].mean() * 100
            st.write(f"✅ Total Resolved Outages: {len(sla_data)}")
            st.write(f"✅ SLA Compliance Rate: {compliance_rate:.2f}%")
            st.dataframe(sla_data[["id", "customer_id", "resolution_time_hours", "sla_compliant"]], use_container_width=True)
        else:
            st.info("ℹ️ No resolved outages found.")

    with st.expander("⏱ Average Response Time"):
        resolved_outages_with_times = outages[outages["status"] == "Resolved"].copy()
        if not resolved_outages_with_times.empty and "resolved_at" in resolved_outages_with_times.columns:
            resolved_outages_with_times = resolved_outages_with_times.dropna(subset=["resolved_at"])
            resolved_outages_with_times["response_time"] = (
                pd.to_datetime(resolved_outages_with_times["resolved_at"]) -
                pd.to_datetime(resolved_outages_with_times["report_time"])
            ).dt.total_seconds() / 3600
            avg_response_time = resolved_outages_with_times["response_time"].mean()
            if pd.notnull(avg_response_time):
                st.write(f"⏰ Average Response Time: {avg_response_time:.2f} hours")
            else:
                st.info("ℹ️ No resolved outages with valid response times.")
        else:
            st.info("ℹ️ No resolved outages or 'resolved_at' data available.")

    with st.expander("⚡ Top Outage Causes"):
        top_causes = outages["description"].str.split(":").str[0].value_counts().reset_index()
        top_causes.columns = ["Cause", "Count"]
        if not top_causes.empty:
            fig_causes = px.bar(top_causes, x="Cause", y="Count", title="Frequent Outage Causes")
            st.plotly_chart(fig_causes, use_container_width=True)
        else:
            st.info("ℹ️ No outage causes data available.")

    # Section 5: Outage History
    st.subheader("📜 Outage History")
    display_outage_history_per_customer()
