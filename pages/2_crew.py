import streamlit as st
import pymysql
import folium
import time
from streamlit_folium import st_folium
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import requests
from streamlit_js_eval import streamlit_js_eval

# Get device location
def get_device_location():
    try:
        location = streamlit_js_eval(
            js_expressions='''new Promise((resolve) => {
                navigator.geolocation.getCurrentPosition(
                    (position) => resolve({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    }),
                    (error) => resolve(null),
                    {enableHighAccuracy: true, timeout: 10000, maximumAge: 0}
                );
            })''',
            key=f"get_location_{st.session_state.location_updates}",
            want_output=True
        )
        if location:
            st.session_state.device_location = location
            return location
        st.warning("⚠️ Location access denied or unavailable. Please check browser permissions.")
        return None
    except Exception as e:
        st.error(f"Error getting device location: {e}")
        return None

# Make the page wide and configure viewport
st.set_page_config(layout="wide")

# Viewport and full-width styling
st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        /* Remove all container padding */
        .main, .block-container, .stApp {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
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
        
        /* Remove Streamlit footer and header spacing */
        footer { visibility: hidden; }
        .st-emotion-cache-1avcm0n { display: none; }
        
        /* Ensure full viewport width */
        html, body, #root, .stApp {
            width: 100% !important;
            overflow-x: hidden !important;
        }
    </style>
""", unsafe_allow_html=True)

# OpenRouteService API Key
OPENROUTESERVICE_API_KEY = "5b3ce3597851110001cf62488b3cfccc385db49e8232a231f15a915c8e985f86b2b58d2c0f158e37"

# Initialize Session State for Persistence
if "crew_lat" not in st.session_state:
    st.session_state.crew_lat = None
    st.session_state.crew_lon = None
if "assigned_outage" not in st.session_state:
    st.session_state.assigned_outage = None
if "route_map" not in st.session_state:
    st.session_state.route_map = None
if "route_data" not in st.session_state:
    st.session_state.route_data = None
if "crew_id" not in st.session_state:
    st.session_state.crew_id = None
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 'dashboard'
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'device_location' not in st.session_state:
    st.session_state.device_location = None
if 'location_updates' not in st.session_state:
    st.session_state.location_updates = 0

# Mobile-friendly styling to match customer app
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
            
            /* Full viewport containment */
            html, body, #root, .stApp {
                width: 100% !important;
                min-height: 100vh;
                margin: 0 !important;
                padding: 0 !important;
                overflow-x: hidden !important;
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
                width: 100% !important;
                max-width: 100% !important;
            }
            
            .left-panel, .right-panel {
                padding: var(--spacing-md);
                background-color: var(--panel-bg);
                border-radius: var(--border-radius);
                box-shadow: var(--shadow);
                overflow-y: auto;
                box-sizing: border-box;
                width: 100% !important;
            }
            
            .left-panel {
                flex: 1;
                max-width: 400px;
            }
            
            .right-panel {
                flex: 2;
            }
            
            /* Map-specific fixes */
            .stMap > div {
                width: 100% !important;
                padding: 0 !important;
                margin: 0 !important;
            }
            
            .folium-map {
                width: 100% !important;
                min-width: 100% !important;
                height: var(--map-height) !important;
                margin: 0 !important;
                border-radius: var(--border-radius);
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
                    margin-bottom: 1rem !important;
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
                width: 100% !important;
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
            
            .logout-btn {
                position: absolute;
                top: 10px;
                right: 10px;
                z-index: 1001;
            }
            
            /* Location status indicator */
            .location-status {
                padding: 8px 12px;
                border-radius: 20px;
                font-size: 0.85em;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                margin-bottom: 10px;
            }
            
            .location-status.active {
                background-color: #d4edda;
                color: #155724;
            }
            
            .location-status.inactive {
                background-color: #f8d7da;
                color: #721c24;
            }
            
            .location-status-icon {
                font-size: 1.2em;
            }
        </style>
    """, unsafe_allow_html=True)

make_mobile_friendly()

# MySQL Database Connection
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



# Calculate Distance using Haversine formula (km)
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# Update Crew Location in Database
def update_crew_location(crew_id, latitude, longitude):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE Crew SET latitude = %s, longitude = %s WHERE id = %s", (latitude, longitude, crew_id))
    conn.commit()
    conn.close()
    st.session_state.location_updates += 1
    st.success("✅ GPS Location Updated!")

# Get Crew Location from Database
def get_crew_location(crew_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT latitude, longitude FROM Crew WHERE id = %s", (crew_id,))
    crew_location = cursor.fetchone()
    conn.close()
    return crew_location if crew_location else (None, None)

# Fetch Outage Location
def get_outage_location(outage_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT latitude, longitude FROM Customer 
        WHERE id = (SELECT customer_id FROM Outage WHERE id = %s)
    """, (outage_id,))
    outage_location = cursor.fetchone()
    conn.close()
    return outage_location if outage_location else (None, None)

# Fetch Nearby Incidents
def fetch_nearby_incidents(crew_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT latitude, longitude FROM Crew1 WHERE id = %s", (crew_id,))
    crew_location = cursor.fetchone()
    if not crew_location:
        conn.close()
        return []
    crew_lat, crew_lon = crew_location

    # Use session state for crew location or fallback to database
    crew_lat = st.session_state.crew_lat if st.session_state.crew_lat else crew_lat
    crew_lon = st.session_state.crew_lon if st.session_state.crew_lon else crew_lon

    cursor.execute("""
        SELECT o.id, c.latitude, c.longitude, o.description, o.status, o.assigned_crew_id, cr.name AS assigned_crew_name
        FROM Outage o
        JOIN Customer1 c ON o.customer_id = c.id
        LEFT JOIN Crew1 cr ON o.assigned_crew_id = cr.id
        WHERE o.status IN ('Pending', 'Assigned', 'In Progress')
    """)
    outages = cursor.fetchall()

    nearby_outages = []
    for outage in outages:
        outage_id, lat, lon, description, status, assigned_crew_id, assigned_crew_name = outage
        distance = calculate_distance(crew_lat, crew_lon, lat, lon)
        nearby_outages.append((outage_id, lat, lon, description, distance, assigned_crew_id, assigned_crew_name))

    nearby_outages.sort(key=lambda x: x[4])
    conn.close()
    return nearby_outages

# Assign Incident
def assign_incident(crew_id, outage_id, distance, eta):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        conn.begin()
        # 1. Get customer name for notification
        cursor.execute("""
            SELECT c.name
            FROM Customer c
            JOIN Outage o ON c.id = o.customer_id
            WHERE o.id = %s
        """, (outage_id,))
        customer_name = cursor.fetchone()[0]

        # 2. Assign the outage
        cursor.execute("""
            UPDATE Outage
            SET assigned_crew_id = %s, status = 'Assigned'
            WHERE id = %s
        """, (crew_id, outage_id))

        # 3. Create/update Task record
        cursor.execute("""
            INSERT INTO Task (crew_id, outage_id, distance, eta, status)
            VALUES (%s, %s, %s, %s, 'Assigned')
            ON DUPLICATE KEY UPDATE
            crew_id = VALUES(crew_id),
            distance = VALUES(distance),
            eta = VALUES(eta),
            status = VALUES(status)
        """, (crew_id, outage_id, distance, eta))
        conn.commit()
        st.success(f"✅ Task {outage_id} assigned successfully!")

        # 4. Send notification to crew
        send_notification_to_crew(
            crew_id,
            f"🚨 NEW TASK ASSIGNED\n"
            f"Outage ID: {outage_id}\n"
            f"Customer: {customer_name}\n"
            f"Distance: {distance:.1f} km\n"
            f"ETA: {eta:.0f} minutes"
        )
    except Exception as e:
        conn.rollback()
        st.error(f"❌ Error assigning task: {str(e)}")
    finally:
        conn.close()

# Enhanced notification sending function
def send_notification_to_crew(crew_id, message):
    """
    Send notification specifically to a crew member about their assigned tasks
    """
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # First verify this is actually a crew member
        cursor.execute("SELECT id FROM Crew1 WHERE id = %s", (crew_id,))
        if not cursor.fetchone():
            st.error("❌ Invalid crew ID")
            return False

        # Insert the crew-specific notification
        cursor.execute("""
            INSERT INTO Notification (user_id, message, status, notification_type)
            VALUES (%s, %s, 'unread', 'crew_assignment')
        """, (crew_id, message))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"❌ Error sending crew notification: {str(e)}")
        return False
    finally:
        conn.close()

def fetch_crew_notifications(crew_id):
    """
    Fetch only crew-specific notifications (not customer notifications)
    """
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, message, status, timestamp 
            FROM Notification 
            WHERE user_id = %s 
            AND notification_type = 'crew_assignment'
            ORDER BY timestamp DESC
            LIMIT 50
        """, (crew_id,))
        return cursor.fetchall()
    except Exception as e:
        st.error(f"❌ Error fetching crew notifications: {str(e)}")
        return []
    finally:
        conn.close()

def send_notification_to_customer(customer_id, message):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Notification (user_id, message, status, timestamp)
            VALUES (%s, %s, 'unread', NOW())
        """, (customer_id, message))
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"❌ Error sending customer notification: {str(e)}")
    finally:
        conn.close()



# Enhanced notification display
def show_notifications_tab():
    st.title("🔔 Notifications")
    
    # Get notifications from database
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, message, status, timestamp 
            FROM Notification 
            WHERE user_id = %s
            ORDER BY timestamp DESC
            LIMIT 20
        """, (st.session_state.crew_id,))
        notifications = cursor.fetchall()
        
        if not notifications:
            st.info("ℹ️ No notifications found")
            return
            
        for note in notifications:
            note_id, message, status, timestamp = note
            
            # Replace newlines with HTML breaks
            formatted_message = message.replace('\n', '<br>')
            
            st.markdown(f"""
                <div style="border-left: 4px solid {'#4285F4' if status == 'unread' else '#888'};
                            padding: 10px;
                            margin-bottom: 10px;
                            background-color: {'#f0f7ff' if status == 'unread' else '#f8f9fa'};
                            border-radius: 4px;">
                    <div style="font-weight: 500;">{formatted_message}</div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.8em;">
                        <span style="color: #666;">{timestamp.strftime('%Y-%m-%d %H:%M')}</span>
                        <span style="color: {'#1877f2' if status == 'unread' else '#666'};">
                            {'🆕 Unread' if status == 'unread' else '✔️ Read'}
                        </span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Mark as read when displayed
            if status == 'unread':
                try:
                    cursor.execute("""
                        UPDATE Notification 
                        SET status = 'read' 
                        WHERE id = %s
                    """, (note_id,))
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Error marking notification as read: {str(e)}")
                    
    except Exception as e:
        st.error(f"❌ Error loading notifications: {str(e)}")
    finally:
        conn.close()

# Resolve Task
def resolve_task(outage_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        conn.begin()
        # 1. Get customer ID and crew ID before updating
        cursor.execute("""
            SELECT o.customer_id, o.assigned_crew_id 
            FROM Outage o
            WHERE o.id = %s
        """, (outage_id,))
        result = cursor.fetchone()
        if not result:
            st.error("❌ Outage not found")
            return
        customer_id, crew_id = result

        # 2. Update Outage
        cursor.execute("""
            UPDATE Outage 
            SET status = 'Resolved',
                resolved_at = NOW() 
            WHERE id = %s
        """, (outage_id,))

        # 3. Update Task
        cursor.execute("""
            UPDATE Task 
            SET status = 'Resolved',
                resolved_at = NOW()
            WHERE outage_id = %s
        """, (outage_id,))

        # 4. Log resolved task into TaskHistory
        cursor.execute("""
            INSERT INTO TaskHistory (outage_id, crew_id, resolved_at)
            VALUES (%s, %s, NOW())
        """, (outage_id, crew_id))

        # 5. Update Crew status to 'Available'
        if crew_id:
            cursor.execute("""
                UPDATE Crew
                SET status = 'Available'
                WHERE id = %s
            """, (crew_id,))
            # Optionally update the crew's location to the outage location
            cursor.execute("""
                SELECT latitude, longitude 
                FROM Customer 
                WHERE id = %s
            """, (customer_id,))
            outage_location = cursor.fetchone()
            if outage_location:
                outage_lat, outage_lon = outage_location
                cursor.execute("""
                    UPDATE Crew1
                    SET latitude = %s, longitude = %s
                    WHERE id = %s
                """, (outage_lat, outage_lon, crew_id))
                st.session_state.crew_lat = outage_lat
                st.session_state.crew_lon = outage_lon

        conn.commit()

        st.success(f"✅ Task {outage_id} resolved successfully!")

        # 6. Notify customer
        send_notification_to_customer(
            customer_id,
            f"✅ Your outage #{outage_id} has been resolved\n"
            f"Thank you for your patience!"
        )

        # 7. Notify crew
        if crew_id:
            send_notification_to_crew(
                crew_id,
                f"✅ Task {outage_id} has been marked as resolved.\n"
                f"You are now available for new tasks."
            )

    except Exception as e:
        conn.rollback()
        st.error(f"❌ Error resolving task: {str(e)}")
    finally:
        conn.close()
    st.rerun()

#Fetch_assigned_tasks function
def fetch_assigned_tasks(crew_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                o.id, 
                c.latitude, 
                c.longitude, 
                o.description, 
                o.status,
                COALESCE(t.distance, 
                    (SELECT ST_Distance_Sphere(
                        POINT(c.latitude, c.longitude),
                        POINT(cr.latitude, cr.longitude)
                    )/1000 
                    FROM Crew cr 
                    WHERE cr.id = %s)
                ) as distance,
                COALESCE(t.eta, 
                    (SELECT ST_Distance_Sphere(
                        POINT(c.latitude, c.longitude),
                        POINT(cr.latitude, cr.longitude)
                    )/1000 * 2 
                    FROM Crew cr 
                    WHERE cr.id = %s)
                ) as eta
            FROM Outage o
            JOIN Customer c ON o.customer_id = c.id
            LEFT JOIN Task t ON o.id = t.outage_id
            WHERE o.assigned_crew_id = %s 
            AND o.status IN ('Assigned', 'In Progress', 'Resolved')
        """, (crew_id, crew_id, crew_id))
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Error fetching tasks: {e}")
        return []
    finally:
        conn.close()

#Update_task_status function
def update_task_status(outage_id, new_status, distance):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        conn.begin()
        
        # 1. Update Outage
        cursor.execute("""
            UPDATE Outage 
            SET status = %s 
            WHERE id = %s
        """, (new_status, outage_id))
        
        # 2. Update Task (with all columns)
        cursor.execute("""
            UPDATE Task 
            SET status = %s,
                distance = %s,
                eta = %s,
                updated_at = NOW()
            WHERE outage_id = %s
        """, (new_status, distance, calculate_eta(distance), outage_id))
        
        # 3. Update Crew status if starting task
        if new_status == "In Progress":
            cursor.execute("""
                UPDATE Crew
                SET status = 'Busy'
                WHERE id = %s
            """, (st.session_state.crew_id,))
        
        conn.commit()
        st.success(f"✅ Task {outage_id} updated to {new_status}!")
        
    except Exception as e:
        conn.rollback()
        st.error(f"❌ Error updating task: {str(e)}")
    finally:
        conn.close()
    st.rerun()
#Update task Distance
def update_task_distance(outage_id, distance, eta):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Task 
            SET distance = %s, 
                eta = %s
            WHERE outage_id = %s
        """, (distance, eta, outage_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Error updating task distance: {e}")
    finally:
        conn.close()

# Update Crew Status
def update_crew_status(crew_id, new_status):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Crew 
            SET status = %s 
            WHERE id = %s
        """, (new_status, crew_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"❌ Error updating crew status: {e}")
    finally:
        conn.close()
def fetch_nearby_customers(crew_id, radius_km=5):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # Get crew's current location
        cursor.execute("SELECT latitude, longitude FROM Crew1 WHERE id = %s", (crew_id,))
        crew_location = cursor.fetchone()
        if not crew_location:
            return []
        crew_lat, crew_lon = crew_location

        # Fetch all customers
        cursor.execute("SELECT id, name, latitude, longitude FROM Customer1")
        customers = cursor.fetchall()

        # Calculate distances and filter nearby customers
        nearby_customers = []
        for customer in customers:
            customer_id, name, lat, lon = customer
            distance = calculate_distance(crew_lat, crew_lon, lat, lon)
            if distance <= radius_km:
                nearby_customers.append((customer_id, name, lat, lon, distance))

        # Sort by distance
        nearby_customers.sort(key=lambda x: x[4])
        return nearby_customers
    except Exception as e:
        st.error(f"Error fetching nearby customers: {e}")
        return []
    finally:
        conn.close()
# Send Message
def send_message(sender_id, receiver_id, message):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Chat (sender_id, receiver_id, message, timestamp)
        VALUES (%s, %s, %s, NOW())
    """, (sender_id, receiver_id, message))
    conn.commit()
    conn.close()
    st.success("✅ Message sent!")

# Fetch Chat History
def fetch_chat_history(crew_id, customer_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sender_id, receiver_id, message, timestamp 
        FROM Chat
        WHERE (sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)
        ORDER BY timestamp DESC
    """, (crew_id, customer_id, customer_id, crew_id))
    chat_history = cursor.fetchall()
    conn.close()
    return chat_history

# Send Notification to Crew
def send_notification_to_crew(crew_id, message):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Notification (user_id, message, status)
            VALUES (%s, %s, 'unread')
        """, (crew_id, message))
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"❌ Error sending notification: {e}")
    finally:
        conn.close()

# Notify Customer Task Resolved
def notify_customer_task_resolved(outage_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT customer_id FROM Outage WHERE id = %s", (outage_id,))
        customer_result = cursor.fetchone()
        if not customer_result:
            st.error(f"❌ Outage ID {outage_id} not found.")
            return
        customer_id = customer_result[0]
        cursor.execute("""
            INSERT INTO Notification (user_id, message, status)
            VALUES (%s, %s, 'unread')
        """, (customer_id, f"✅ Your outage (ID: {outage_id}) has been resolved."))
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"❌ Error sending notification: {e}")
    finally:
        conn.close()
def fetch_all_notifications(user_id):
    """Fetch both read and unread notifications"""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, message, status, priority, created_at 
            FROM Notification 
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 50
        """, (user_id,))
        return cursor.fetchall()
    except Exception as e:
        st.error(f"❌ Error fetching notifications: {str(e)}")
        return []
    finally:
        conn.close()

def mark_notification_as_read(notification_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Notification 
            SET status = 'read' 
            WHERE id = %s
        """, (notification_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"❌ Error marking notification as read: {str(e)}")
    finally:
        conn.close()

def mark_all_notifications_as_read(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Notification 
            SET status = 'read' 
            WHERE user_id = %s AND status = 'unread'
        """, (user_id,))
        conn.commit()
        st.session_state.notifications = []  # Clear session notifications
    except Exception as e:
        conn.rollback()
        st.error(f"❌ Error marking notifications as read: {str(e)}")
    finally:
        conn.close()

# Fetch Unread Notifications
def fetch_unread_notifications(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, message, timestamp 
            FROM Notification 
            WHERE user_id = %s AND status = 'unread'
            ORDER BY timestamp DESC
        """, (user_id,))
        notifications = cursor.fetchall()
        return notifications
    except Exception as e:
        st.error(f"❌ Error fetching notifications: {e}")
        return []
    finally:
        conn.close()

# Calculate ETA
def calculate_eta(distance_km, speed_kmh=30):
    if speed_kmh <= 0:
        return 0
    time_hours = distance_km / speed_kmh
    eta_minutes = round(time_hours * 60, 2)
    return eta_minutes

# Get Route from OpenRouteService API
def get_route(start_lat, start_lon, end_lat, end_lon):
    """
    Calculate the shortest route using OpenRouteService API.
    Returns: (coordinates, distance in km, ETA in minutes)
    """
    try:
        start_lat = float(start_lat)
        start_lon = float(start_lon)
        end_lat = float(end_lat)
        end_lon = float(end_lon)
    except (ValueError, TypeError):
        st.error("⚠️ Invalid coordinates provided for routing.")
        return None, None, None

    if None in [start_lat, start_lon, end_lat, end_lon]:
        st.error("⚠️ Missing coordinates for routing.")
        return None, None, None

    try:
        url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
        headers = {
            "Authorization": OPENROUTESERVICE_API_KEY,
            "Content-Type": "application/json"
        }
        body = {
            "coordinates": [[start_lon, start_lat], [end_lon, end_lat]],
            "preference": "shortest",  # Prioritize shortest distance
            "units": "km"
        }
        response = requests.post(url, json=body, headers=headers, timeout=10)
        if response.status_code == 200:
            route_data = response.json()
            if "features" in route_data and route_data["features"]:
                route = route_data["features"][0]
                coordinates = route["geometry"]["coordinates"]  # [lon, lat]
                # Convert to [lat, lon] for compatibility with Folium
                coordinates = [[lat, lon] for lon, lat in coordinates]
                distance = route["properties"]["summary"]["distance"]
                duration = route["properties"]["summary"]["duration"] / 60  # Convert seconds to minutes
                return coordinates, distance, duration
            else:
                st.error("⚠️ No route found by OpenRouteService.")
        elif response.status_code == 401:
            st.error("❌ Invalid OpenRouteService API key.")
        elif response.status_code == 429:
            st.error("❌ OpenRouteService rate limit exceeded.")
        else:
            st.error(f"⚠️ OpenRouteService failed with status {response.status_code}: {response.text}")
        # Fallback to Haversine if ORS fails
        distance = calculate_distance(start_lat, start_lon, end_lat, end_lon)
        eta = calculate_eta(distance)  # Use the existing calculate_eta function
        return None, distance, eta
    except requests.Timeout:
        st.error("⚠️ OpenRouteService request timed out.")
        distance = calculate_distance(start_lat, start_lon, end_lat, end_lon)
        eta = calculate_eta(distance)
        return None, distance, eta
    except Exception as e:
        st.error(f"⚠️ OpenRouteService routing error: {str(e)}")
        distance = calculate_distance(start_lat, start_lon, end_lat, end_lon)
        eta = calculate_eta(distance)
        return None, distance, eta

# Authentication function
def authenticate_crew(crew_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM Crew1 WHERE id = %s", (crew_id,))
        result = cursor.fetchone()
        if result:
            st.session_state.authenticated = True
            st.session_state.crew_id = crew_id
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
    st.session_state.crew_id = None
    st.session_state.active_tab = 'dashboard'
    st.rerun()

# Auto-update location every 30 seconds
if st.session_state.authenticated:
    if "last_location_update" not in st.session_state:
        st.session_state.last_location_update = 0
    current_time = time.time()
    if current_time - st.session_state.last_location_update > 30:  # 30 seconds
        location = get_device_location()
        if location:
            update_crew_location(
                st.session_state.crew_id,
                location['latitude'],
                location['longitude']
            )
            st.session_state.last_location_update = current_time
            st.session_state.crew_lat = location['latitude']
            st.session_state.crew_lon = location['longitude']

# Login form (only shown when not authenticated)
if not st.session_state.authenticated:
    st.title("🔒 Crew Portal Login")
    with st.form("login_form"):
        crew_id = st.number_input("Enter Your Crew ID:", 
                                min_value=1, step=1,
                                key="login_crew_id")
        login_button = st.form_submit_button("Login")
        if login_button:
            if authenticate_crew(crew_id):
                st.success("Login successful! Loading your dashboard...")
                st.rerun()
            else:
                st.error("Invalid crew ID. Please try again.")
    st.stop()

# Logout button
st.button("🚪 Logout", on_click=logout, key="logout_btn", 
          help="Click to logout", 
          use_container_width=False,
          type="primary")

# Navigation bar
cols = st.columns(3)
with cols[0]:
    if st.button("📊 Dashboard", key="dashboard_button"):
        st.session_state.active_tab = 'dashboard'
with cols[1]:
    if st.button("💬 Messages", key="messages_button"):
        st.session_state.active_tab = 'messages'
with cols[2]:
    if st.button("🔔 Notifications", key="notifications_button"):
        st.session_state.active_tab = 'notifications'

# Main app content
if st.session_state.active_tab == 'dashboard':
    st.title("👷 Crew Dashboard")
    
    # Get crew location and tasks
    crew_lat, crew_lon = get_crew_location(st.session_state.crew_id)
    assigned_tasks = fetch_assigned_tasks(st.session_state.crew_id)
    nearby_incidents = fetch_nearby_incidents(st.session_state.crew_id)
    
    # Location status and manual update section
    # Location Services Section
    # Location Services Section
    with st.expander("📍 Location Services", expanded=True):
        if st.session_state.device_location:
            st.markdown(f"""
                <div class="location-status active">
                    <span class="location-status-icon">📍</span>
                    <span>GPS Active: {st.session_state.device_location['latitude']:.6f}, {st.session_state.device_location['longitude']:.6f}</span>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="location-status inactive">
                    <span class="location-status-icon">⚠️</span>
                    <span>GPS Inactive: Location access denied or unavailable</span>
                </div>
            """, unsafe_allow_html=True)

    # Manual Location Update Section (Moved Outside)
    with st.expander("Manual Location Update (if GPS is unavailable)", expanded=False):
        manual_lat = st.number_input("Enter Latitude:", 
                                    value=st.session_state.crew_lat if st.session_state.crew_lat else 0.0, 
                                    format="%.6f")
        manual_lon = st.number_input("Enter Longitude:", 
                                    value=st.session_state.crew_lon if st.session_state.crew_lon else 0.0, 
                                    format="%.6f")
        if st.button("Update Manual Location"):
            update_crew_location(st.session_state.crew_id, manual_lat, manual_lon)
            st.session_state.crew_lat = manual_lat
            st.session_state.crew_lon = manual_lon
            st.success(f"📍 Updated location: Latitude: {manual_lat}, Longitude: {manual_lon}")
            st.rerun()

    # Map Visualization
    st.header("🌍 Live Outage Map")

    # Default location if GPS is unavailable
    DEFAULT_LAT = -1.1029  # Juja Town latitude
    DEFAULT_LON = 37.0144  # Juja Town longitude

    # Use session state for crew location or fallback to default
    crew_lat = st.session_state.crew_lat if st.session_state.crew_lat else DEFAULT_LAT
    crew_lon = st.session_state.crew_lon if st.session_state.crew_lon else DEFAULT_LON

    if crew_lat and crew_lon:
        # Create map with fallback/default location
        m = folium.Map(
            location=[crew_lat, crew_lon],
            zoom_start=12,
            width='100%',
            tiles='OpenStreetMap'
        )

        # Add crew location marker
        folium.Marker(
            [crew_lat, crew_lon],
            popup="📍 Your Location" if st.session_state.device_location else "📍 Default Location",
            icon=folium.Icon(color="blue", icon="user")
        ).add_to(m)

        # Add nearby incidents
        for incident in nearby_incidents:
            outage_id, lat, lon, description, distance, assigned_crew_id, assigned_crew_name = incident
            if assigned_crew_id:
                if assigned_crew_id == st.session_state.crew_id:
                    icon_color = "green"
                    popup_text = f"✅ Your Task {outage_id}<br>Distance: {distance:.1f} km"
                    # Add routing line for assigned tasks
                    route_coords, route_distance, route_eta = get_route(crew_lat, crew_lon, lat, lon)
                    if route_coords:
                        folium.PolyLine(
                            route_coords,
                            color="green",
                            weight=3,
                            opacity=0.7,
                            popup=f"Route to Outage {outage_id}<br>Distance: {route_distance:.1f} km<br>ETA: {route_eta:.0f} min"
                        ).add_to(m)
                else:
                    icon_color = "orange"
                    popup_text = f"⚠️ Assigned to Crew {assigned_crew_name}<br>Distance: {distance:.1f} km"
            else:
                icon_color = "red"
                popup_text = f"⚠️ Unassigned Outage {outage_id}<br>Distance: {distance:.1f} km"
            folium.Marker(
                [lat, lon],
                popup=popup_text,
                icon=folium.Icon(color=icon_color, icon="bolt" if assigned_crew_id else "warning-sign")
            ).add_to(m)

        # Display map
        st_folium(m, width='100%', height=500)
    else:
        st.warning("⚠️ Unable to determine your location. Please update your location manually.")

    # Task Management Section
    st.header("📋 Your Tasks")
    assigned_tasks = fetch_assigned_tasks(st.session_state.crew_id)
    if assigned_tasks:
        for task in assigned_tasks:
            outage_id, lat, lon, description, status, distance, eta = task
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    status_emoji = {
                        'Assigned': '📝',
                        'In Progress': '🛠️',
                        'Resolved': '✅'
                    }
                    st.markdown(f"""
                        <div style="padding: 10px; border-radius: 8px; 
                                    background-color: #f8f9fa; margin-bottom: 10px;
                                    border-left: 4px solid {'#4285F4' if status == 'Assigned' else 
                                                            '#FFA500' if status == 'In Progress' else 
                                                            '#0F9D58'};">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 1.5em;">{status_emoji.get(status, 'ℹ️')}</span>
                                <div>
                                    <div style="font-weight: 600;">Outage ID: {outage_id}</div>
                                    <div style="font-size: 0.9em; color: #555;">{description}</div>
                                </div>
                            </div>
                            <div style="margin-top: 8px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                                <div>
                                    <span style="font-size: 0.8em;">📍 Distance</span>
                                    <div style="font-weight: 600;">{distance:.1f} km</div>
                                </div>
                                <div>
                                    <span style="font-size: 0.8em;">⏱️ ETA</span>
                                    <div style="font-weight: 600;">{eta:.0f} min</div>
                                </div>
                                <div>
                                    <span style="font-size: 0.8em;">Status</span>
                                    <div style="font-weight: 600;">{status}</div>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if status == "Assigned":
                        if st.button(f"🚀 Start", key=f"start_{outage_id}"):
                            update_task_status(outage_id, "In Progress", distance)
                            st.rerun()
                    elif status == "In Progress":
                        if st.button(f"✅ Resolve", key=f"resolve_{outage_id}"):
                            resolve_task(outage_id)
                            st.rerun()
    else:
        st.info("ℹ️ No tasks currently assigned to you")

    # Nearby Incidents Section
    st.header("⚠️ Nearby Incidents")
    if nearby_incidents:
        filtered_incidents = [
            incident for incident in nearby_incidents 
            if not incident[5] or incident[5] == st.session_state.crew_id
        ]
        if not filtered_incidents:
            st.info("ℹ️ All nearby incidents have been assigned")
        else:
            for incident in filtered_incidents[:5]:  # Show only top 5 nearest
                outage_id, lat, lon, description, distance, assigned_crew_id, assigned_crew_name = incident
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"""
                            <div style="padding: 10px; border-radius: 8px; 
                                        background-color: #fff3cd; margin-bottom: 10px;">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <span style="font-size: 1.5em;">⚠️</span>
                                    <div>
                                        <div style="font-weight: 600;">Outage ID: {outage_id}</div>
                                        <div style="font-size: 0.9em; color: #555;">{description}</div>
                                    </div>
                                </div>
                                <div style="margin-top: 8px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                                    <div>
                                        <span style="font-size: 0.8em;">📍 Distance</span>
                                        <div style="font-weight: 600;">{distance:.1f} km</div>
                                    </div>
                                    <div>
                                        <span style="font-size: 0.8em;">⏱️ ETA</span>
                                        <div style="font-weight: 600;">{calculate_eta(distance):.0f} min</div>
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        if not assigned_crew_id:
                            if st.button(f"Assign to Me", key=f"assign_{outage_id}"):
                                eta = calculate_eta(distance)
                                assign_incident(st.session_state.crew_id, outage_id, distance, eta)
                                st.rerun()
                        elif assigned_crew_id == st.session_state.crew_id:
                            st.markdown(f"""
                                <div style="background-color: #d4edda; padding: 8px; 
                                            border-radius: 4px; text-align: center;">
                                    ✅ Assigned to You
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                                <div style="background-color: #f8d7da; padding: 8px; 
                                            border-radius: 4px; text-align: center;">
                                   ⚠️ Assigned
                              </div>
                            """, unsafe_allow_html=True)
    else:
        st.info("ℹ️ No nearby incidents found. Please check your location or the database.")
    # Nearby Customers Section
    st.header("👥 Nearby Customers")
    nearby_customers = fetch_nearby_customers(st.session_state.crew_id, radius_km=5)

    if nearby_customers:
        for customer in nearby_customers[:5]:  # Show only top 5 nearest
            customer_id, name, lat, lon, distance = customer
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"""
                        <div style="padding: 10px; border-radius: 8px; 
                                    background-color: #e9f7ef; margin-bottom: 10px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 1.5em;">👤</span>
                                <div>
                                    <div style="font-weight: 600;">Customer ID: {customer_id}</div>
                                    <div style="font-size: 0.9em; color: #555;">{name}</div>
                                </div>
                            </div>
                            <div style="margin-top: 8px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                                <div>
                                    <span style="font-size: 0.8em;">📍 Distance</span>
                                    <div style="font-weight: 600;">{distance:.1f} km</div>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                        <div style="background-color: #d4edda; padding: 8px; 
                                    border-radius: 4px; text-align: center;">
                            ✅ Nearby
                        </div>
                    """, unsafe_allow_html=True)

        # Add nearby customers to the map
        for customer in nearby_customers:
            _, _, lat, lon, distance = customer
            folium.Marker(
                [lat, lon],
                popup=f"👤 Customer<br>Distance: {distance:.1f} km",
                icon=folium.Icon(color="purple", icon="user")
            ).add_to(m)

    else:
        st.info("ℹ️ No nearby customers found within 5 km.")
elif st.session_state.active_tab == 'messages':
    st.title("💬 Messages")
    # Get customer ID from assigned tasks
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT customer_id 
        FROM Outage 
        WHERE assigned_crew_id = %s
    """, (st.session_state.crew_id,))
    customer_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    if customer_ids:
        selected_customer = st.selectbox("Select Customer", customer_ids)
        # Display chat history
        chat_history = fetch_chat_history(st.session_state.crew_id, selected_customer)
        if chat_history:
            for msg in reversed(chat_history):
                sender, receiver, message, timestamp = msg
                sender_type = "You" if sender == st.session_state.crew_id else "Customer"
                st.markdown(f"""
                    <div class="message-bubble {'user' if sender_type == 'You' else 'crew'}">
                        <div style="font-weight: 500;">{sender_type}</div>
                        <div>{message}</div>
                        <div style="font-size: 0.8em; color: #666; text-align: right;">{timestamp}</div>
                    </div>
                """, unsafe_allow_html=True)
        # Send message form
        with st.form("send_message_form"):
            message_text = st.text_area("Type your message:")
            if st.form_submit_button("📤 Send"):
                if message_text.strip():
                    send_message(st.session_state.crew_id, selected_customer, message_text)
                    st.rerun()
                else:
                    st.warning("Please enter a message")
    else:
        st.info("ℹ️ No customers to message yet")

elif st.session_state.active_tab == 'notifications':
    show_notifications_tab()
                   
