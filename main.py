import streamlit as st

st.set_page_config(page_title="Outage Management System", page_icon="⚡", layout="wide")

st.title("⚡ A GIS-Based Real-Time Outage Management System for Improved Service Reliability")

st.markdown("""
Welcome to the **Outage Management System** — choose your role from the sidebar:
- 🧭 **Admin Portal** — Manage outages, crews, and customers.
- 👷 **Crew Portal** — View and resolve assigned tasks in real-time.
- 👥 **Customer Portal** — Report outages and track resolution progress.
""")

st.info("Navigate using the sidebar ➡️ to access your section.")
