import streamlit as st
import pandas as pd
import altair as alt
import random
import datetime
from anomaly_detection import load_data, detect_anomalies
from alerting import trigger_alert_flow

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ONTAP System Manager",
    page_icon="💾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STATE MANAGEMENT ---
if 'view' not in st.session_state:
    st.session_state.view = 'list' # 'list' or 'detail'
if 'selected_vol' not in st.session_state:
    st.session_state.selected_vol = None

def navigate_to_detail(vol_name):
    st.session_state.selected_vol = vol_name
    st.session_state.view = 'detail'

def navigate_to_list():
    st.session_state.view = 'list'
    st.session_state.selected_vol = None

# --- CUSTOM CSS (EXACT REPLICA) ---
st.markdown("""
<style>
    /* Global Reset & Font */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #333;
        background-color: #F4F7F9;
    }
    
    /* REMOVE DEFAULT STREAMLIT ELEMENTS */
    header {visibility: hidden;}
    [data-testid="stSidebarNav"] {display: none;} /* Hide default styled menu */
    .block-container {
        padding-top: 50px; /* Space for fixed header */
        padding-left: 0rem;
        padding-right: 0rem;
        max-width: 100%;
    }

    /* --- TOP HEADER (NAVY BLUE) --- */
    .ontap-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 60px; /* Increased height to match screenshot */
        background-color: #041F42; /* Deep Navy */
        color: white;
        display: flex;
        align-items: center;
        padding: 0 15px;
        z-index: 999999; /* HIGHEST LEVEL to stay above sidebar */
        font-size: 14px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* RESTORE AND POSITION SIDEBAR TOGGLE */
    [data-testid="stSidebarCollapsedControl"] {
        visibility: visible !important;
        display: block !important;
        position: fixed;
        top: 15px;
        left: 15px;
        z-index: 1000000 !important; /* Above the header */
        color: white !important;
    }
    
    /* MOVE SIDEBAR CONTENT DOWN - Handled in main sidebar block */
    
    /* Ensure Sidebar Close button is accessible */
    [data-testid="stSidebar"] button[kind="header"] {
        visibility: visible !important;
        color: white !important;
    }

    .header-logo {
        font-weight: 600;
        font-size: 18px;
        margin-left: 45px; /* Space for the restored actual toggle */
        display: flex;
        align-items: center;
    }
    .header-logo span {
        display: none; /* Hide fake hamburger */
    }
    .header-search {
        flex-grow: 1;
        display: flex;
        justify-content: center;
    }
    .search-input {
        background-color: #021226;
        border: 1px solid #4A5C72;
        color: #ddd;
        padding: 8px 15px;
        width: 450px;
        border-radius: 3px;
        font-size: 13px;
    }
    .header-icons {
        display: flex;
        gap: 20px;
        margin-left: auto;
        font-size: 18px;
        opacity: 0.9;
        align-items: center;
    }

    /* --- SIDEBAR (NAVY BLUE) --- */
    [data-testid="stSidebar"] {
        background-color: #041F42;
        width: 260px !important;
        top: 60px !important; /* Start below header */
        height: calc(100vh - 60px) !important;
        padding-top: 10px;
        border-right: 1px solid #062650;
        z-index: 999998 !important; /* High z-index to ensure visibility, below header */
        box-shadow: 2px 0 5px rgba(0,0,0,0.1);
    }
    
    /* Ensure user content in sidebar is visible and scrollable if needed */
    [data-testid="stSidebarUserContent"] {
        padding-top: 20px;
        padding-bottom: 50px;
    }

    .sidebar-menu-item {
        color: #CBD5E0;
        padding: 12px 20px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        display: flex;
        justify-content: space-between;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .sidebar-menu-item:hover {
        background-color: #0B3266;
        color: white;
    }
    /* Expanded Group Style */
    .sidebar-menu-item.active {
        background-color: transparent;
        color: white;
    }
    
    .sidebar-subitem {
        color: #A0AEC0;
        padding: 10px 0px 10px 40px;
        font-size: 14px;
        cursor: pointer;
        display: block;
        text-decoration: none;
    }
    .sidebar-subitem:hover {
        color: white;
        background-color: #0B3266;
    }
    .sidebar-subitem.active {
        background-color: #2B4C7E; /* Lighter selection blue */
        color: white;
        border-right: 0px;
        font-weight: 600;
    }
    
    /* Fake Sidebar Button wrapper to trigger python logic */
    .stButton > button {
        width: 100%;
        border: none;
        text-align: left;
        background: transparent;
        color: inherit;
        padding: 0;
    }
    .stButton > button:hover {
        color: white;
        border: none;
        background: transparent;
    }
    .stButton > button:focus {
        color: white;
        border: none;
        background: transparent;
        box-shadow: none;
    }

    /* --- VOLUME TABLE STYLING --- */
    .main-canvas {
        margin-left: 20px;
        margin-right: 20px;
    }
    .vol-table-header {
        background-color: #FFFFFF;
        padding: 20px 30px;
        border-bottom: 1px solid #E2E8F0;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .vol-title {
        font-size: 24px;
        font-weight: 400;
        color: #2D3748;
    }
    
    /* Toolbar Config */
    .toolbar-container {
        padding: 15px 30px;
        background-color: white;
        border-bottom: 1px solid #EDF2F7;
        display: flex;
        align-items: center;
    }
    .btn-primary {
        background-color: #0067C5;
        color: white !important;
        padding: 8px 16px;
        border-radius: 3px;
        font-weight: 600;
        font-size: 13px;
        border: none;
        margin-right: 15px;
        cursor: pointer;
        display: inline-block;
        text-align: center;
    }
    .btn-text {
        color: #4A5568 !important;
        font-weight: 600;
        font-size: 13px;
        margin-right: 20px;
        cursor: pointer;
        background: none;
        border: none;
    }

    /* Table Grid */
    .table-header {
        display: grid; 
        grid-template-columns: 20px 2fr 1.5fr 1fr 3fr 1fr 1fr 1fr 0.5fr; 
        padding: 12px 30px; 
        background-color:#FAFCFE; 
        border-bottom:1px solid #E2E8F0; 
        font-weight:700; 
        font-size:12px; 
        color:#4A5568;
        align-items: center;
    }
    .table-row {
        display: grid; 
        grid-template-columns: 20px 2fr 1.5fr 1fr 3fr 1fr 1fr 1fr 0.5fr; 
        padding: 12px 30px; 
        background-color: white;
        border-bottom:1px solid #EDF2F7; 
        font-size:13px; 
        color:#2D3748;
        align-items: center;
        transition: background-color 0.2s;
    }
    .table-row:hover {
        background-color: #F7FAFC;
    }
    
    /* Detail View Styling */
    .detail-container {
        padding: 20px 30px;
    }

</style>
""", unsafe_allow_html=True)

# --- DYNAMIC DATA AGGREGATION ---
def get_latest_metrics(df):
    """
    Aggregates the latest metrics for each volume from the AI dataframe.
    """
    if df.empty:
        return []
    
    # Get latest timestamp per volume
    latest = df.sort_values('Timestamp').groupby('Volume_Name').tail(1)
    
    fleet_data = []
    for _, row in latest.iterrows():
        # Mocking static attributes for UI fidelity (in a real app, this comes from ONTAP API)
        vol_name = row['Volume_Name']
        static_props = {
            'AZURETEST': {'SVM': 'USERDATA_SVM', 'Total': 10, 'Used': 6.81, 'Unit': 'TB'},
            'DESKTOPS':  {'SVM': 'EUC_SVM', 'Total': 2.11, 'Used': 1.73, 'Unit': 'TB'},
            'vol_vdi_boot': {'SVM': 'EUC_SVM', 'Total': 1, 'Used': 0.8, 'Unit': 'TB'},
            'vol_analytics_01': {'SVM': 'USERDATA_SVM', 'Total': 10, 'Used': 6.8, 'Unit': 'TB'}
        }
        # Default props if not in mock map
        props = static_props.get(vol_name, {'SVM': 'DATA_SVM', 'Total': 5, 'Used': 2.5, 'Unit': 'TB'})
        
        fleet_data.append({
            "Name": vol_name,
            "SVM": props['SVM'],
            "Status": "Online",
            "Total": props['Total'],
            "Used": props['Used'],
            "Unit": props['Unit'],
            "IOPS": f"{row['IOPS']:.0f}", 
            "Lat": round(row['Latency_ms'], 2),
            "Tput": round(row['Throughput_MB'], 2)
        })
    return fleet_data


# --- LOAD AI DATA ---
@st.cache_data
def get_ai_data():
    return detect_anomalies(load_data('storage_data.csv'))

try:
    df_ai = get_ai_data()
except:
    df_ai = pd.DataFrame()

if not df_ai.empty:
    mock_fleet = get_latest_metrics(df_ai)
else:
    # Fallback if no data
    mock_fleet = []

# --- HEADER RENDER (Fixed) ---
st.markdown("""
<div class="ontap-header">
    <div class="header-logo">
        <span>☰</span>
        <img src="https://upload.wikimedia.org/wikipedia/commons/4/4b/NetApp_logo.svg" height="24" style="filter: brightness(0) invert(1); margin-right:12px;">
        ONTAP System Manager
    </div>
    <div class="header-search">
        <input type="text" class="search-input" placeholder="Search actions, objects, and pages &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 🔍">
    </div>
    <div class="header-icons">
        <span>❓</span>
        <span>&lt; &gt;</span>
        <span>👤</span>
        <span>⋮</span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR RENDER ---
with st.sidebar:
    st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-menu-item">DASHBOARD</div>', unsafe_allow_html=True)
    
    # Storage Group (Expanded)
    st.markdown('<div class="sidebar-menu-item active" style="display:flex; justify-content:space-between;">STORAGE <span>^</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subitem">Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subitem">Applications</div>', unsafe_allow_html=True)
    
    # Voltume Link (Button hack for state in streamlit)
    is_list = (st.session_state.view == 'list')
    active_class = "active" if is_list else ""
    
    # We use a button to trigger 'navigate_to_list'
    if st.button("Volumes", key="nav_vols"):
        navigate_to_list()
        st.rerun()
    
    # Visual checkmark/highlight via CSS if active is tricky with native buttons, 
    # so we rely on the button text or surrounding div.
    # Below is a markdown overlay to simulate the formatting
    st.markdown(f"""
    <style>
    div[data-testid="stSidebar"] button[kind="secondary"] {{
        background-color: {'#2B4C7E' if is_list else 'transparent'} !important;
        color: {'white' if is_list else '#A0AEC0'} !important;
        padding-left: 40px !important;
        text-align: left !important;
        font-weight: {'600' if is_list else '400'} !important;
        border-radius: 0 !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-subitem">LUNs</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subitem">NVMe Namespaces</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subitem">Shares</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subitem">Qtrees</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subitem">Quotas</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subitem">Storage VMs</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subitem">Tiers</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-menu-item">NETWORK <span>v</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-menu-item">EVENTS & JOBS <span>v</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-menu-item">PROTECTION <span>v</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-menu-item">HOSTS <span>v</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-menu-item">CLUSTER <span>v</span></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    use_email = st.checkbox("Enable Email Alerts", value=False)
    use_teams = st.checkbox("Enable Teams Alerts", value=False)
    
    st.markdown("---")
    # Simulation moved to Detail View


# --- MAIN CONTENT SWITCHER ---

if st.session_state.view == 'list':
    # === VIEW 1: VOLUMES LIST (Exact Replica) ===
    
    # 1. Page Title & Toolbar
    st.markdown("""
    <div class="vol-table-header">
        <div class="vol-title">Volumes</div>
        <div>
            <span style="color:#0067C5; font-size:14px; margin-right:20px; font-weight:600;">🔍 Search &nbsp;&nbsp;&nbsp; ⬇ Download &nbsp;&nbsp;&nbsp; 👁️ Show/Hide &nbsp;&nbsp;&nbsp; Y Filter</span>
        </div>
    </div>
    <div class="toolbar-container">
        <button class="btn-primary">+ Add</button>
        <button class="btn-text">⋮ More</button>
        <button class="btn-text">Delete</button>
        <button class="btn-text">Protect</button>
    </div>
    
    <div class="table-header">
        <div>□</div>
        <div>Name</div>
        <div>Storage VM</div>
        <div>Status</div>
        <div>Capacity (available | total)</div>
        <div>IOPS</div>
        <div>Latency (ms)</div>
        <div>Throughput</div>
        <div>Prot</div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Render Rows
    for i, vol in enumerate(mock_fleet):
        # Calculate Bar Width
        pct = (vol['Used'] / vol['Total']) * 100 if vol['Total'] > 0 else 0
        bar_color = "#007C30" if pct < 80 else "#E5AA00" # Green/Yellow
        if pct > 90: bar_color = "#C00"
        
        # We need a clickable area. 
        # Streamlit buttons are tricky in grids, so we use columns
        c_check, c_name, c_svm, c_status, c_cap, c_iops, c_lat, c_tput, c_prot = st.columns([0.2, 2, 1.5, 1, 3, 1, 1, 1, 0.5])
        
        with c_check: st.write("☐")
        with c_name:
            # Dropdown arrow + Name as button
            if st.button(f"﹀ {vol['Name']}", key=f"row_{i}"):
                navigate_to_detail(vol['Name'])
                st.rerun()
        with c_svm: st.write(vol['SVM'])
        with c_status: st.markdown('<span style="color:#007C30; font-weight:bold;">✅ Online</span>', unsafe_allow_html=True)
        with c_cap:
             st.markdown(f"""
            <div style="display:flex; align-items:center;">
                <div style="flex-grow:1; height:12px; background-color:#E2E8F0; margin-right:10px; border-radius:2px;">
                    <div style="width:{pct}%; height:100%; background-color:{bar_color}; border-radius:2px;"></div>
                </div>
                <div style="font-size:11px; width:80px; text-align:right;">{vol['Used']} / {vol['Total']} {vol['Unit']}</div>
            </div>
            """, unsafe_allow_html=True)
        with c_iops: st.write(vol['IOPS'])
        with c_lat: st.write(vol['Lat'])
        with c_tput: st.write(f"{vol['Tput']}")
        with c_prot: st.write("🛡️")
        
        st.markdown("<hr style='margin:0; padding:0; border-top: 1px solid #EDF2F7;'>", unsafe_allow_html=True)

elif st.session_state.view == 'detail':
    # === VIEW 2: DETAIL OVERVIEW (Reused) ===
    
    # Back Link
    if st.button("← Back to Volumes List"):
        navigate_to_list()
        st.rerun()

    vol_name = st.session_state.selected_vol
    
    # Header Layout with Simulation Box
    col_header, col_sim = st.columns([4, 1.2])
    
    with col_header:
        st.markdown(f'<div class="detail-container">', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="margin-bottom:20px;">
            <h2 style="margin:0; font-weight:400; color:#333;">{vol_name} <span style="font-size:16px; font-weight:normal; color:#666;">All Volumes</span></h2>
        </div>
        """, unsafe_allow_html=True)
        
    with col_sim:
        st.markdown("""
        <div style="background-color:#041F42; color:white; padding:12px; border-radius:4px; text-align:center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <div style="font-size:10px; font-weight:700; margin-bottom:8px; letter-spacing:1px;">SIMULATION</div>
        </div>
        """, unsafe_allow_html=True)
        
        from data_generator import inject_latency_spike, inject_normal_data
        from investigation import run_investigation
        from alerting import trigger_alert_flow
        
        # 1. Trigger Spike (Randomly picks scenario in backend)
        if st.button("⚠️ Trigger Latency Spike", key="sim_trigger_btn", use_container_width=True):
             with st.spinner("Injecting Anomaly..."):
                inject_latency_spike(vol_name, scenario="random")
                get_ai_data.clear() # Clear cache to fetch new spike
                
                # Fetch fresh data for AI Analysis
                df_fresh = get_ai_data()
                
                # Filter strictly to "Now" to avoid future timestamp confusion in reports
                # (Simulation might generate a batch, but we only want to report up to current moment)
                now = datetime.datetime.now()
                df_fresh['Timestamp'] = pd.to_datetime(df_fresh['Timestamp'])
                df_fresh = df_fresh[df_fresh['Timestamp'] <= now + datetime.timedelta(minutes=5)] # Small buffer
                
                vol_fresh_data = df_fresh[df_fresh['Volume_Name'] == vol_name]
                
                if not vol_fresh_data.empty:
                    # Get the spike data (last row)
                    latest_metrics = vol_fresh_data.iloc[-1].to_dict()
                    
                    # RUN AI INVESTIGATION
                    with st.spinner("AI Analyzing Behavior..."):
                        # Force High severity for simulation
                        result = run_investigation(vol_name, latest_metrics, "High", history_df=vol_fresh_data) 
                        
                        # Trigger Alerts (PDF generation happening here)
                        trigger_alert_flow(result, {'enable_email': True, 'enable_teams': True})
                        
                        # Store in session state for display
                        st.session_state['ai_result'] = result
                        st.session_state['ai_ack'] = False # New result not yet acknowledged
                
                st.toast(f"Anomaly Injected & AI Analyzed!", icon="🤖")
                st.rerun()

        # 2. Normalize (Fix it)
        if st.button("✅ Normalize Performance", key="sim_norm_btn", use_container_width=True):
             with st.spinner("Stabilizing..."):
                inject_normal_data(vol_name)
                # Clear AI result on normalization
                if 'ai_result' in st.session_state:
                    del st.session_state['ai_result']
                
                st.toast(f"Performance normalized for {vol_name}.", icon="✅")
                get_ai_data.clear() 
                st.rerun()
    
# AI result display removed per user request    
    st.markdown(f"""
    <div style="border-bottom:1px solid #ddd; margin-bottom:20px; font-size:14px; font-weight:600; color:#555;">
        <span style="border-bottom:3px solid #00609C; color:#333; padding:10px 15px; display:inline-block;">Overview</span>
        <span style="padding:10px 15px; display:inline-block; color:#666;">Snapshot Copies</span>
        <span style="padding:10px 15px; display:inline-block; color:#666;">SnapMirror</span>
        <span style="padding:10px 15px; display:inline-block; color:#666;">Explorer</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Cards
    col_d1, col_d2 = st.columns([1, 2])
    
    with col_d1:
        st.markdown("""
        <div style="background:white; padding:20px; border:1px solid #E2E8F0; border-radius:4px; height:200px;">
            <div style="color:#007C30; font-weight:bold; margin-bottom:15px;">✅ Online</div>
            <div style="color:#666; font-size:11px;">STYLE</div><div style="font-weight:600; margin-bottom:10px;">FlexGroup</div>
            <div style="color:#666; font-size:11px;">STORAGE VM</div><div style="font-weight:600; margin-bottom:10px;">USERDATA_SVM</div>
            <div style="color:#666; font-size:11px;">TIERING</div><div style="font-weight:600;">Auto</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_d2:
        st.markdown("""
        <div style="background:white; padding:20px; border:1px solid #E2E8F0; border-radius:4px; height:200px;">
             <h4 style="margin-top:0; color:#555;">Capacity</h4>
             <div style="height:15px; background:#eee; width:100%; margin-top:30px;"><div style="height:100%; width:70%; background:#007C30;"></div></div>
             <div style="display:flex; justify-content:space-between; margin-top:10px;">
                <b>70% Used</b>
                <span>7 TB / 10 TB</span>
             </div>
        </div>
        """, unsafe_allow_html=True)
        
    # AI Analysis & Extended Telemetry
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- PERFORMANCE CONTAINER ---
    st.markdown("""
    <div style="background:white; padding:20px; border:1px solid #E2E8F0; border-radius:4px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h4 style="margin:0; color:#555;">Performance</h4>
            <div style="background:#0067C5; color:white; padding:5px; border-radius:3px; cursor:pointer;">⬇</div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:12px; color:#666; margin-bottom:20px; border-bottom:1px solid #eee; padding-bottom:10px;">
             <span>Hour</span><span>Day</span><span>Week</span><span>Month</span><span style="font-weight:bold; color:#00609C; border-bottom:2px solid #00609C;">Year</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Helper to clean chart axis
    def make_chart(data, y_col, color, title, unit=""):
        base = alt.Chart(data).encode(x=alt.X('Timestamp:T', axis=None))
        
        # Visual Layers
        line = base.mark_line(color=color, strokeWidth=1.5).encode(
            y=alt.Y(y_col, axis=None)
        )
        area = base.mark_area(opacity=0.05, color=color).encode(
            y=alt.Y(y_col, axis=None)
        )
        
        # Interactive Layer: Invisible points to capture hover easily
        # Size 80 makes them large enough to hit without precision
        points = base.mark_circle(size=80, opacity=0).encode(
            y=alt.Y(y_col, axis=None),
            tooltip=[
                alt.Tooltip('Timestamp:T', title='Timestamp', format='%b %d, %Y %H:%M:%S'),
                alt.Tooltip(y_col, title=title, format='.2f')
            ]
        )
        
        return (area + line + points).properties(height=100, width='container')

    # Get Data
    vol_data = df_ai[df_ai['Volume_Name'] == vol_name]
    
    if not vol_data.empty:
        # Get Current Values (Last datapoint)
        curr = vol_data.iloc[-1]
        
        # 1. Latency Chart (Fixed Layering)
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:flex-end;">
            <div style="font-weight:600; color:#444;">Latency</div>
            <div style="font-size:20px; font-weight:600; color:#333;">{curr['Latency_ms']} <span style="font-size:14px; color:#666;">ms</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Robust Altair Chart Construction
        lat_chart = make_chart(vol_data, 'Latency_ms', '#0087F5', 'Latency')
        st.altair_chart(lat_chart, use_container_width=True)
        
        st.markdown("<hr style='margin:10px 0; border-top:1px solid #eee;'>", unsafe_allow_html=True)

        # 2. IOPS Chart
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:flex-end;">
            <div style="font-weight:600; color:#444;">IOPS</div>
            <div style="font-size:20px; font-weight:600; color:#333;">{curr['IOPS']/1000:.2f} <span style="font-size:14px; color:#666;">k</span></div>
        </div>
        """, unsafe_allow_html=True)
        iops_chart = make_chart(vol_data, 'IOPS', '#0087F5', 'IOPS')
        st.altair_chart(iops_chart, use_container_width=True)
        
        st.markdown("<hr style='margin:10px 0; border-top:1px solid #eee;'>", unsafe_allow_html=True)

        # 3. Throughput Chart
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:flex-end;">
            <div style="font-weight:600; color:#444;">Throughput</div>
            <div style="font-size:20px; font-weight:600; color:#333;">{curr['Throughput_MB']:.2f} <span style="font-size:14px; color:#666;">MB/s</span></div>
        </div>
        """, unsafe_allow_html=True)
        tput_chart = make_chart(vol_data, 'Throughput_MB', '#0087F5', 'Throughput')
        st.altair_chart(tput_chart, use_container_width=True)

    else:
        st.info("No telemetry data for this volume.")

    st.markdown("</div></div>", unsafe_allow_html=True)
