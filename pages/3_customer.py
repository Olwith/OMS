import streamlit as st
import folium
import requests
import pymysql
from streamlit_folium import st_folium
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import time
import uuid

# Make the page wide
st.set_page_config(layout="wide")

# Optional: remove padding/margins even more with CSS
st.markdown(
    """
    <style>
        .main {
            padding-left: 0rem;
            padding-right: 0rem;
        }
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .stHeadingContainer {
            text-align: center;
        }
        .stMap {
            width: 100% !important;
            margin: 0 auto;
        }
    </style>
    """,
    unsafe_allow_html=True
)

OPENROUTESERVICE_API_KEY = "5b3ce3597851110001cf62488b3cfccc385db49e8232a231f15a915c8e985f86b2b58d2c0f158e37"

# Initialize session state for authentication and app data
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'meter_number' not in st.session_state:
    st.session_state.meter_number = None
if 'customer_id' not in st.session_state:
    st.session_state.customer_id = None
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 'home'
if 'assigned_crew_data' not in st.session_state:
    st.session_state.assigned_crew_data = None
if 'nearby_crews' not in st.session_state:
    st.session_state.nearby_crews = []
if 'notifications' not in st.session_state:
    st.session_state.notifications = []
if "outage_id" not in st.session_state:
    st.session_state.outage_id = None

# Database connection function
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

# Authentication function
def authenticate_user(meter_number):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM Customer WHERE meter_number = %s", (meter_number,))
        result = cursor.fetchone()
        if result:
            st.session_state.authenticated = True
            st.session_state.meter_number = meter_number
            st.session_state.customer_id = result[0]
            return True
        return False
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False
    finally:
        conn.close()

# Logout function
def logout():
    st.session_state.authenticated = False
    st.session_state.meter_number = None
    st.session_state.customer_id = None
    st.session_state.assigned_crew_data = None
    st.session_state.nearby_crews = []
    st.session_state.notifications = []
    st.session_state.active_tab = 'home'
    st.rerun()

# Mobile-friendly styling
def make_mobile_friendly():
    st.markdown("""
        <style>
            :root {
                --primary-color: #4285F4;
                --background-color: #ffffff;
                --text-color: #333333;
                --panel-bg: #f9f9f9;
                --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                --border-radius: 10px;
                --spacing-sm: clamp(0.5rem, 2vw, 0.75rem);
                --spacing-md: clamp(1rem, 3vw, 1.25rem);
                --font-size-base: clamp(14px, 2.5vw, 16px);
                --font-size-lg: clamp(16px, 3vw, 18px);
                --map-height: clamp(300px, 50vh, 500px);
            }
            @media (prefers-color-scheme: dark) {
                :root {
                    --background-color: #1a1a1a;
                    --text-color: #e0e0e0;
                    --panel-bg: #2a2a2a;
                }
            }
            html, body, .stApp {
                height: 100%;
                margin: 0;
                overflow-x: hidden;
                background-color: var(--background-color);
                color: var(--text-color);
                font-size: var(--font-size-base);
            }
            .dashboard-container {
                display: flex;
                flex-direction: row;
                gap: var(--spacing-md);
                padding: var(--spacing-md);
                height: 95vh;
                box-sizing: border-box;
            }
            .left-panel, .right-panel {
                padding: var(--spacing-md);
                background-color: var(--panel-bg);
                border-radius: var(--border-radius);
                box-shadow: var(--shadow);
                overflow-y: auto;
                box-sizing: border-box;
            }
            .left-panel {
                flex: 1;
                max-width: 400px;
            }
            .right-panel {
                flex: 2;
            }
            @media (max-width: 1024px) {
                .left-panel {
                    max-width: 100%;
                }
            }
            @media (max-width: 768px) {
                .dashboard-container {
                    flex-direction: column;
                    height: auto;
                }
                .left-panel, .right-panel {
                    max-width: 100%;
                }
                .folium-map {
                    height: 300px !important;
                    margin-bottom: 1rem;
                }
                .card, .notification, .message-bubble {
                    padding: 0.75rem !important;
                    margin-bottom: 0.5rem !important;
                }
                .notification.unread {
                    border-left: 3px solid #1877f2;
                    background-color: #f0f2f5;
                }
            }
            button, input, textarea {
                font-size: var(--font-size-lg) !important;
                padding: var(--spacing-sm) !important;
                border-radius: 5px;
                transition: all 0.2s ease;
            }
            button {
                background-color: var(--primary-color);
                color: white;
                border: none;
            }
            button:hover {
                background-color: #3267d6;
            }
            button:focus {
                outline: 2px solid var(--primary-color);
                outline-offset: 2px;
            }
            table {
                width: 100% !important;
                font-size: var(--font-size-base) !important;
                border-collapse: collapse;
            }
            .folium-map {
                width: 100% !important;
                height: var(--map-height) !important;
                border-radius: var(--border-radius);
            }
            .card {
                background-color: var(--panel-bg);
                padding: var(--spacing-sm);
                margin-bottom: var(--spacing-sm);
                border-radius: 8px;
                border: 1px solid #e0e0e0;
                transition: transform 0.2s ease;
            }
            .card:hover {
                transform: translateY(-2px);
            }
            .notification {
                border-left: 3px solid var(--primary-color);
                padding: var(--spacing-sm);
                background-color: var(--panel-bg);
                margin-bottom: var(--spacing-sm);
            }
            .message-bubble {
                padding: var(--spacing-sm);
                margin-bottom: var(--spacing-sm);
                border-radius: 8px;
                font-size: var(--font-size-base);
            }
            .message-bubble.user {
                background-color: #e3f2fd;
            }
            .message-bubble.crew {
                background-color: #f5f5f5;
            }
            ::-webkit-scrollbar {
                width: 8px;
            }
            ::-webkit-scrollbar-track {
                background: var(--panel-bg);
            }
            ::-webkit-scrollbar-thumb {
                background: var(--primary-color);
                border-radius: 4px;
            }
            .top-nav {
                display: flex;
                justify-content: space-around;
                background-color: #1877f2;
                color: white;
                padding: 12px 0;
                position: sticky;
                top: 0;
                z-index: 1000;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .top-nav-item {
                color: white;
                text-decoration: none;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 8px;
                transition: background-color 0.3s;
            }
            .top-nav-item:hover {
                background-color: #166fe5;
            }
            .top-nav-item.active {
                background-color: #166fe5;
                border-bottom: 3px solid white;
            }
            .stApp {
                padding-top: 0 !important;
            }
            .st-emotion-cache-1avcm0n {
                display: none;
            }
            .logout-btn {
                position: absolute;
                top: 10px;
                right: 10px;
                z-index: 1001;
            }
            .stHeadingContainer {
                text-align: center;
                margin-bottom: 1rem;
            }
            .stMap {
                width: 100% !important;
                margin: 0 auto;
            }
            .map-container {
                width: 100%;
                margin: 0 auto;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            /* Full-width map container */
            .stMap {
                width: 100% !important;
                padding: 0 !important;
                margin: 0 !important;
            }
            /* Folium map itself */
            .folium-map {
                width: 100% !important;
                min-width: 100% !important;
                margin: 0 !important;
                border-radius: 0 !important;
            }
            /* Ensure full viewport width */
            html, body, #root, .stApp {
                width: 100% !important;
                overflow-x: hidden !important;
            }
        </style>
    """, unsafe_allow_html=True)

# Utility functions
def calculate_distance(lat1, lon1, lat2, lon2):
    # Convert all inputs to float first
    lat1 = float(lat1)
    lon1 = float(lon1)
    lat2 = float(lat2)
    lon2 = float(lon2)
   
    R = 6371 # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def get_route(start_lat, start_lon, end_lat, end_lon):
    try:
        start_lat = float(start_lat)
        start_lon = float(start_lon)
        end_lat = float(end_lat)
        end_lon = float(end_lon)
    except (ValueError, TypeError):
        st.error("Invalid coordinates provided for routing.")
        return None, None, None
    if None in [start_lat, start_lon, end_lat, end_lon]:
        st.error("Missing coordinates for routing.")
        return None, None, None
    try:
        url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
        headers = {
            "Authorization": OPENROUTESERVICE_API_KEY,
            "Content-Type": "application/json"
        }
        body = {
            "coordinates": [[start_lon, start_lat], [end_lon, end_lat]],
            "preference": "shortest",
            "units": "km"
        }
        response = requests.post(url, json=body, headers=headers, timeout=10)
        if response.status_code == 200:
            route_data = response.json()
            if "features" in route_data and route_data["features"]:
                route = route_data["features"][0]
                coordinates = [[lat, lon] for lon, lat in route["geometry"]["coordinates"]]
                distance = route["properties"]["summary"]["distance"]
                duration = route["properties"]["summary"]["duration"] / 60
                return coordinates, distance, duration
            else:
                st.error("No route found by OpenRouteService.")
        elif response.status_code == 401:
            st.error("Invalid OpenRouteService API key.")
        elif response.status_code == 429:
            st.error("OpenRouteService rate limit exceeded.")
        else:
            st.error(f"OpenRouteService failed with status {response.status_code}: {response.text}")
        distance = calculate_distance(start_lat, start_lon, end_lat, end_lon)
        eta = distance * 2
        return None, distance, eta
    except requests.Timeout:
        st.error("OpenRouteService request timed out.")
        distance = calculate_distance(start_lat, start_lon, end_lat, end_lon)
        eta = distance * 2
        return None, distance, eta
    except Exception as e:
        st.error(f"OpenRouteService routing error: {str(e)}")
        distance = calculate_distance(start_lat, start_lon, end_lat, end_lon)
        eta = distance * 2
        return None, distance, eta

@st.cache_data(ttl=300)
def get_route_cached(start_lat, start_lon, end_lat, end_lon):
    return get_route(start_lat, start_lon, end_lat, end_lon)

def get_assigned_crew_with_eta():
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # Fetch customer's location
        cursor.execute("SELECT latitude, longitude FROM Customer WHERE meter_number = %s",
                      (st.session_state.meter_number,))
        customer_location = cursor.fetchone()
        if not customer_location or None in customer_location:
            st.error("Customer location not found or incomplete.")
            return None
        customer_lat, customer_lon = customer_location
        # Fetch the assigned crew and outage details
        cursor.execute("""
            SELECT c.id, c.name, c.latitude, c.longitude, o.id
            FROM Crew c
            JOIN Outage o ON c.id = o.assigned_crew_id
            JOIN Customer cu ON o.customer_id = cu.id
            WHERE cu.meter_number = %s AND o.status IN ('Assigned', 'In Progress')
        """, (st.session_state.meter_number,))
        crew = cursor.fetchone()
        if not crew:
            st.warning("No crew assigned yet.")
            return None
        crew_id, name, crew_lat, crew_lon, outage_id = crew
        # Store the outage_id in session state
        st.session_state.outage_id = outage_id
        _, distance, eta_minutes = get_route_cached(crew_lat, crew_lon, customer_lat, customer_lon)
        if eta_minutes is None:
            st.error("Unable to calculate ETA.")
            return None
        return crew_id, name, crew_lat, crew_lon, distance, eta_minutes
    except Exception as e:
        st.error(f"Error fetching assigned crew: {e}")
        return None
    finally:
        conn.close()

# Database interaction functions
def get_customer_id():
    if not st.session_state.meter_number:
        return None
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Customer WHERE meter_number = %s", (st.session_state.meter_number,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def report_outage(description):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # Insert the outage into the database
        cursor.execute("""
            INSERT INTO Outage (customer_id, description, report_time, status)
            VALUES ((SELECT id FROM Customer WHERE meter_number = %s), %s, NOW(), 'Pending')
        """, (st.session_state.meter_number, description))
        outage_id = cursor.lastrowid # Get the ID of the newly created outage
        conn.commit()
        # Assign the outage to the best crew
        assign_incident_to_best_crew(outage_id)
        # Store the outage_id in session state
        st.session_state.outage_id = outage_id
        st.success("Outage reported and assigned to the nearest crew!")
    except Exception as e:
        st.error(f"Error reporting outage: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def assign_incident_to_best_crew(outage_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT c.latitude, c.longitude
            FROM Outage o
            JOIN Customer c ON o.customer_id = c.id
            WHERE o.id = %s
        """, (outage_id,))
        customer_location = cursor.fetchone()
        if not customer_location:
            st.error("Customer location not found for this outage.")
            return
        customer_lat, customer_lon = customer_location
        cursor.execute("""
            SELECT c.id, c.name, c.latitude, c.longitude, COUNT(o.id) AS incident_count
            FROM Crew c
            LEFT JOIN Outage o ON c.id = o.assigned_crew_id
            GROUP BY c.id
        """)
        crews = cursor.fetchall()
        if not crews:
            st.error("No crews found in the database.")
            return
        best_crew = None
        min_distance = float('inf')
        eta_minutes = None
        for crew in crews:
            crew_id, name, crew_lat, crew_lon, incident_count = crew
            if incident_count >= 5 or crew_lat is None or crew_lon is None:
                continue
            _, distance, eta = get_route(crew_lat, crew_lon, customer_lat, customer_lon)
            if distance is not None and distance < min_distance:
                min_distance = distance
                eta_minutes = eta
                best_crew = (crew_id, name, crew_lat, crew_lon)
        if best_crew:
            crew_id, name, crew_lat, crew_lon = best_crew
            cursor.execute("""
                UPDATE Outage
                SET assigned_crew_id = %s, status = 'Assigned'
                WHERE id = %s
            """, (crew_id, outage_id))
            cursor.execute("SELECT customer_id FROM Outage WHERE id = %s", (outage_id,))
            customer_id = cursor.fetchone()
            if customer_id:
                customer_id = customer_id[0]
                message = (
                    f"Your outage (ID: {outage_id}) has been assigned to Crew {name} (ID: {crew_id}). "
                    f"Crew Location: Latitude={crew_lat}, Longitude={crew_lon} "
                    f"Distance to You: {min_distance:.2f} km "
                    f"ETA: {eta_minutes:.0f} minutes."
                )
                cursor.execute("""
                    INSERT INTO Notification (user_id, message, status)
                    VALUES (%s, %s, 'unread')
                """, (customer_id, message))
            conn.commit()
            st.success(f"Outage {outage_id} assigned to Crew {name} (ID: {crew_id}).")
        else:
            st.error("No available crew to assign to this outage.")
    except Exception as e:
        st.error(f"Error assigning crew: {e}")
        conn.rollback()
    finally:
        conn.close()

@st.cache_data(ttl=30) # Cache data for 30 seconds to reduce database load
def fetch_nearby_crews(customer_lat, customer_lon, max_distance=5):
    """Return crews within max_distance km"""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # First ensure customer coordinates are floats
        customer_lat = float(customer_lat)
        customer_lon = float(customer_lon)
       
        cursor.execute("""
            SELECT id, name, latitude, longitude
            FROM Crew
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """)
        nearby_crews = []
        for crew in cursor.fetchall():
            crew_id, name, lat, lon = crew
            try:
                distance = calculate_distance(customer_lat, customer_lon, float(lat), float(lon))
                if distance <= max_distance:
                    eta_minutes = distance * 2 # Approximate ETA (2 min per km)
                    nearby_crews.append((crew_id, name, lat, lon, distance, eta_minutes))
            except (TypeError, ValueError) as e:
                st.error(f"Skipping crew {crew_id}: {str(e)}")
                continue
       
        # Sort by distance
        return sorted(nearby_crews, key=lambda x: x[4])
    except Exception as e:
        st.error(f"Error fetching crews: {e}")
        return []
    finally:
        conn.close()

def get_customer_location():
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT latitude, longitude FROM Customer WHERE meter_number = %s",
                       (st.session_state.meter_number,))
        location = cursor.fetchone()
        return location if location else (None, None)
    finally:
        conn.close()

def display_interactive_map():
    # Ensure the map updates dynamically
    if "last_location_update" not in st.session_state:
        st.session_state.last_location_update = 0
    current_time = time.time()
    if current_time - st.session_state.last_location_update > 10: # Update every 10 seconds
        update_crew_locations() # Fetch updated crew locations
        st.session_state.last_location_update = current_time
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # Fetch customer's location
        cursor.execute("SELECT latitude, longitude FROM Customer WHERE meter_number = %s",
                      (st.session_state.meter_number,))
        customer_location = cursor.fetchone()
        if not customer_location or None in customer_location:
            st.error("Customer location not found or incomplete.")
            return
        customer_lat, customer_lon = customer_location
       
        # Create map with 100% width parameter
        m = folium.Map(
            location=[customer_lat, customer_lon],
            zoom_start=14,
            width='100%', # Critical for full width
            tiles='OpenStreetMap'
        )
       
        # Add customer's location marker
        folium.Marker(
            location=[customer_lat, customer_lon],
            popup="<b>Your Location</b>",
            icon=folium.Icon(color="red", icon="home")
        ).add_to(m)
       
        # Fetch assigned crew (if any)
        cursor.execute("""
            SELECT c.id, c.name, c.latitude, c.longitude
            FROM Crew c
            JOIN Outage o ON c.id = o.assigned_crew_id
            JOIN Customer cu ON o.customer_id = cu.id
            WHERE cu.meter_number = %s AND o.status IN ('Assigned', 'Pending')
        """, (st.session_state.meter_number,))
        assigned_crew = cursor.fetchone()
        if assigned_crew and None not in assigned_crew:
            crew_id, name, crew_lat, crew_lon = assigned_crew
            try:
                coordinates, distance, eta_minutes = get_route(crew_lat, crew_lon, customer_lat, customer_lon)
                popup_text = f"""
                    <b>Assigned Crew</b><br>
                    Name: {name or 'N/A'}<br>
                    ID: {crew_id or 'N/A'}<br>
                    Distance: {distance:.1f} km<br>
                    ETA: {eta_minutes:.0f} min
                """
            except:
                popup_text = f"""
                    <b>Assigned Crew</b><br>
                    Name: {name or 'N/A'}<br>
                    ID: {crew_id or 'N/A'}<br>
                    (Route calculation failed)
                """
            folium.Marker(
                location=[crew_lat, crew_lon],
                popup=popup_text,
                icon=folium.Icon(color="red", icon="truck") # Truck icon for assigned crew
            ).add_to(m)
            if coordinates and None not in [crew_lat, crew_lon, customer_lat, customer_lon]:
                folium.PolyLine(
                    locations=coordinates,
                    color="green", # Green for route line
                    weight=3
                ).add_to(m)
       
        # Fetch nearby crews
        cursor.execute("""
            SELECT id, name, latitude, longitude
            FROM Crew
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            AND (id != %s OR %s IS NULL)
            ORDER BY id
        """, (assigned_crew[0] if assigned_crew else None, assigned_crew[0] if assigned_crew else None))
        nearby_crews = cursor.fetchall()
        for crew in nearby_crews:
            crew_id, name, lat, lon = crew
            try:
                _, distance, eta_minutes = get_route(lat, lon, customer_lat, customer_lon)
                popup_text = f"""
                    <b>Nearby Crew</b><br>
                    Name: {name or 'N/A'}<br>
                    ID: {crew_id or 'N/A'}<br>
                    Distance: {distance:.1f} km<br>
                    ETA: {eta_minutes:.0f} min
                """
            except:
                popup_text = f"""
                    <b>Nearby Crew</b><br>
                    Name: {name or 'N/A'}<br>
                    ID: {crew_id or 'N/A'}
                """
            folium.Marker(
                location=[lat, lon],
                popup=popup_text,
                icon=folium.Icon(color="blue", icon="user") # User icon for nearby crews
            ).add_to(m)
       
        # Add legend
        legend_html = '''
        <div style="
            position: fixed !important;
            bottom: 50px !important; left: 50px !important;
            width: 160px !important;
            height: 110px !important;
            border: 2px solid grey !important;
            z-index: 99999 !important;
            font-size: 14px !important;
            background: white !important;
            padding: 10px !important;
            border-radius: 5px !important;
            opacity: 0.9 !important;
        ">
            <div style="font-weight: bold; margin-bottom: 5px;">Map Legend</div>
            <div style="margin-bottom: 2px;"><span style="color: red">■</span> Your Location</div>
            <div style="margin-bottom: 2px;"><span style="color: red">■</span> Assigned Crew</div>
            <div style="margin-bottom: 2px;"><span style="color: blue">■</span> Nearby Crews</div>
            <div style="margin-top: 5px; font-size: 12px; color: #555;">
                <span style="color: green">----</span> Route to Assigned Crew
            </div>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
       
        # Display map in a column layout with 100% width
        map_col, _ = st.columns([0.85, 0.15]) # Adjust ratios as needed
        with map_col:
            st_folium(
                m,
                width='100%', # Ensure full width
                height=500, # Fixed height for consistency
                returned_objects=[]
            )
    except Exception as e:
        st.error(f"Map Error: {str(e)}")
    finally:
        conn.close()

def update_crew_locations():
    """Fetch and update the latest locations of all crews."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, latitude, longitude
            FROM Crew
        """)
        crews = cursor.fetchall()
        for crew in crews:
            crew_id, lat, lon = crew
            if lat is not None and lon is not None:
                st.session_state[f"crew_{crew_id}_location"] = (lat, lon)
    except Exception as e:
        st.error(f"Error updating crew locations: {str(e)}")
    finally:
        conn.close()

def fetch_unread_notifications():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, message, timestamp FROM Notification
        WHERE user_id = %s AND status = 'unread'
        ORDER BY timestamp DESC
    """, (st.session_state.customer_id,))
    notifications = cursor.fetchall()
    conn.close()
    return notifications

def fetch_all_notifications():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, message, timestamp, status FROM Notification
        WHERE user_id = %s
        ORDER BY timestamp DESC
    """, (st.session_state.customer_id,))
    notifications = cursor.fetchall()
    conn.close()
    return notifications

def mark_notifications_as_read():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE Notification SET status = 'read' WHERE user_id = %s",
                   (st.session_state.customer_id,))
    conn.commit()
    conn.close()

def fetch_chat_history():
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT sender_id, receiver_id, message, timestamp
            FROM Chat
            WHERE sender_id = %s OR receiver_id = %s
            ORDER BY timestamp ASC
        """, (st.session_state.customer_id, st.session_state.customer_id))
        chat_history = cursor.fetchall()
        return chat_history
    except Exception as e:
        st.error(f"Error fetching chat history: {e}")
        return []
    finally:
        conn.close()

def send_message(recipient_id, message):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # Check if the same message already exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM Chat
            WHERE sender_id = %s AND receiver_id = %s AND message = %s
        """, (st.session_state.customer_id, recipient_id, message))
        count = cursor.fetchone()[0]
        if count > 0:
            st.warning("This message has already been sent.")
            return
       
        # Insert the message into the Chat table
        cursor.execute("""
            INSERT INTO Chat (sender_id, receiver_id, message, timestamp)
            VALUES (%s, %s, %s, NOW())
        """, (st.session_state.customer_id, recipient_id, message))
        conn.commit()
        st.success("Message sent!")
    except Exception as e:
        st.error(f"Error sending message: {e}")
        conn.rollback()
    finally:
        conn.close()

# Function Definition
def fetch_chat_history():
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT sender_id, receiver_id, message, timestamp
            FROM Chat
            WHERE sender_id = %s OR receiver_id = %s
            ORDER BY timestamp ASC
        """, (st.session_state.customer_id, st.session_state.customer_id))
        chat_history = cursor.fetchall()
        return chat_history
    except Exception as e:
        st.error(f"Error fetching chat history: {e}")
        return []
    finally:
        conn.close()

# Function Call
chat_history = fetch_chat_history()

# Login form (only shown when not authenticated)
if not st.session_state.authenticated:
    st.title("Customer Portal Login")
    with st.form("login_form"):
        meter_number = st.text_input("Enter Your Meter Number:",
                                   placeholder="e.g., METER-123456",
                                   key="login_meter_number")
        login_button = st.form_submit_button("Login")
        if login_button:
            if authenticate_user(meter_number):
                st.success("Login successful! Loading your dashboard...")
                # Get customer location first
                customer_lat, customer_lon = get_customer_location()
                # Initialize session state variables with proper arguments
                st.session_state.assigned_crew_data = get_assigned_crew_with_eta()
                st.session_state.nearby_crews = fetch_nearby_crews(customer_lat, customer_lon) # Pass coordinates here
                st.session_state.notifications = fetch_unread_notifications()
                st.rerun()
        else:
            st.error("Invalid meter number. Please try again.")
    st.stop()

# Apply styling after authentication
make_mobile_friendly()

# Logout button
st.button("Logout", on_click=logout, key="logout_btn",
          help="Click to logout",
          use_container_width=False,
          type="primary")

# Navigation bar
cols = st.columns(3)
with cols[0]:
    if st.button("Home", key="home_button"):
        st.session_state.active_tab = 'home'
with cols[1]:
    if st.button("Messages", key="messages_button"):
        st.session_state.active_tab = 'messages'
with cols[2]:
    if st.button("Notifications", key="notifications_button"):
        st.session_state.active_tab = 'notifications'

# Main app content
if st.session_state.active_tab == 'home':
    st.title("Outage Reporting Portal")
    with st.expander("Report New Outage", expanded=False):
        with st.form("outage_form"):
            outage_desc = st.text_area(
                "Describe the issue:",
                placeholder="e.g., No power in entire building since 2PM"
            )
            report_button = st.form_submit_button("Report Outage")
            if report_button:
                if outage_desc.strip():
                    report_outage(outage_desc)
                    customer_lat, customer_lon = get_customer_location()
                    st.session_state.assigned_crew_data = get_assigned_crew_with_eta()
                    st.session_state.nearby_crews = fetch_nearby_crews(customer_lat, customer_lon) # Pass coordinates here
                    st.session_state.notifications = fetch_unread_notifications()
                    st.rerun()
                else:
                    st.warning("Please enter a description of the outage")

    st.header("Your Crew")
    if st.session_state.outage_id:
        # Fetch the outage status
        conn = connect_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT status
                FROM Outage
                WHERE id = %s
            """, (st.session_state.outage_id,))
            outage_status = cursor.fetchone()[0]
            # Display crew details only if the outage is not resolved
            if outage_status in ['Assigned', 'In Progress']:
                if st.session_state.assigned_crew_data:
                    crew_id, name, crew_lat, crew_lon, distance, eta_minutes = st.session_state.assigned_crew_data
                    st.markdown(f"""
                        <div class="card">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 1.5em;"></span>
                                <div>
                                    <div style="font-weight: 600; font-size: 1.1em;">{name}</div>
                                    <div style="font-size: 0.9em;">Crew ID: {crew_id}</div>
                                </div>
                            </div>
                            <div style="margin-top: 0.8rem;">
                                <div style="display: flex; justify-content: space-between;">
                                    <span>Distance</span>
                                    <span><strong>{distance:.1f} km</strong></span>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span>ETA</span>
                                    <span><strong>{eta_minutes:.0f} min</strong></span>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("No crew assigned yet.")
            else:
                # Display a message if the outage is resolved
                st.success("The outage has been resolved. No crew is currently assigned.")
        except Exception as e:
            st.error(f"Error fetching outage status: {str(e)}")
        finally:
            conn.close()
    else:
        st.info("No active outage found.")

    st.header("Live Outage Map")
    with st.container():
        display_interactive_map()

    with st.expander("Available Crews", expanded=True):
        customer_lat, customer_lon = get_customer_location()
        if None in [customer_lat, customer_lon]:
            st.error("Your location is not set - cannot find nearby crews")
        else:
            nearby_crews = fetch_nearby_crews(customer_lat, customer_lon)
       
            if not nearby_crews:
                st.warning("""
                No crews found within 5km.
                This could mean:
                - No crews are currently available
                - Your location isn't set correctly
                - All crews are already assigned
                """)
            else:
                for crew in nearby_crews:
                    crew_id, name, lat, lon, distance, eta = crew
                    st.markdown(f"""
                    <div class="card">
                        <div style="display: flex; justify-content: space-between;">
                            <span><strong>{name}</strong></span>
                            <span>ID: {crew_id}</span>
                        </div>
                        <div style="margin-top: 10px;">
                            <div>Distance: {distance:.1f} km</div>
                            <div>Approx. ETA: {eta:.0f} minutes</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

elif st.session_state.active_tab == 'messages':
    st.title("Messages")
   
    # Get all available crews (assigned + nearby)
    assigned_crew_data = st.session_state.assigned_crew_data
    assigned_crew_id = assigned_crew_data[0] if assigned_crew_data else None
    assigned_crew_name = assigned_crew_data[1] if assigned_crew_data else None
   
    customer_lat, customer_lon = get_customer_location()
    nearby_crews = fetch_nearby_crews(customer_lat, customer_lon) if None not in [customer_lat, customer_lon] else []
   
    # Create list of available recipients
    recipient_options = []
    recipient_mapping = {}
   
    # Add assigned crew if available
    if assigned_crew_id:
        display_name = f"Assigned Crew: {assigned_crew_name} (ID: {assigned_crew_id})"
        recipient_options.append(display_name)
        recipient_mapping[display_name] = assigned_crew_id
   
    # Add nearby crews
    for crew in nearby_crews:
        crew_id, name, _, _, _, _ = crew
        if assigned_crew_id and crew_id == assigned_crew_id:
            continue
        display_name = f"Nearby Crew: {name} (ID: {crew_id})"
        recipient_options.append(display_name)
        recipient_mapping[display_name] = crew_id
   
    # Display chat interface
    col1, col2 = st.columns([2, 1])
   
    with col1:
        st.subheader("Conversation History")
        if not chat_history:
            st.info("No messages yet. Start a conversation!")
        else:
            # Group messages by conversation
            conversations = {}
            for msg in chat_history:
                # Determine the other party's ID based on who sent the message
                other_party_id = msg[1] if msg[0] == st.session_state.customer_id else msg[0]
   
                # Initialize the conversation entry if it doesn't exist
                if other_party_id not in conversations:
                    conversations[other_party_id] = {
                    'name': f"Crew {other_party_id}", # You may want to fetch the actual name from the database
                    'messages': []
                    }
   
                # Add the message to the conversation
                sender_name = "You" if msg[0] == st.session_state.customer_id else f"Crew {msg[0]}"
                conversations[other_party_id]['messages'].append({
                    'sender': sender_name,
                    'message': msg[2],
                    'timestamp': msg[3]
                })
           
            # Display each conversation
            for crew_id, conv in conversations.items():
                with st.expander(f"Chat with {conv['name']}", expanded=True):
                    for msg in conv['messages']:
                        is_user = msg['sender'] == "You"
                        st.markdown(f"""
                            <div class="message-bubble {'user' if is_user else 'crew'}">
                                <div style="font-weight: 500;">{msg['sender']}</div>
                                <div>{msg['message']}</div>
                                <div style="font-size: 0.8em; color: #666; text-align: right;">
                                    {msg['timestamp'].strftime('%Y-%m-%d %H:%M')}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
   
    with col2:
        st.subheader("New Message")
        with st.form("new_message_form", clear_on_submit=True):
            if not recipient_options:
                st.warning("No crews available to message")
            else:
                recipient = st.selectbox(
                    "Select recipient:",
                    options=recipient_options,
                    index=0
                )
               
                message_text = st.text_area(
                    "Your message:",
                    key="new_message",
                    max_chars=500
                )
                st.caption(f"{len(message_text)}/500 characters")
                if "last_sent_message" not in st.session_state:
                    st.session_state.last_sent_message = None
                if st.form_submit_button("Send"):
                    if not message_text.strip():
                         st.error("Please enter a message")
                    else:
                        recipient_id = recipient_mapping.get(recipient)
                        if recipient_id:
                        # Generate a unique message ID
                            message_id = str(uuid.uuid4())
                            if st.session_state.last_sent_message != message_id:
                                send_message(recipient_id, message_text)
                                st.session_state.last_sent_message = message_id # Mark as sent
                                time.sleep(1)
                                st.rerun()
                        else:
                            st.error("Could not determine recipient")

elif st.session_state.active_tab == 'notifications':
    st.title("Notifications")
    if st.session_state.customer_id:
        notifications = fetch_all_notifications()
        if notifications:
            for note in notifications:
                note_id, message, timestamp, status = note
                st.markdown(f"""
                    <div class="notification {'unread' if status == 'unread' else ''}">
                        <div style="font-weight: 500;">{message}</div>
                        <div style="font-size: 0.8em; color: #666;">{timestamp}</div>
                    </div>
                """, unsafe_allow_html=True)
            mark_notifications_as_read()
        else:
            st.info("No notifications yet")
