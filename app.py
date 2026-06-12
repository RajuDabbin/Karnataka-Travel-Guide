import base64
import hashlib
import os
import random
import smtplib
import time
import urllib.parse
from email.mime.text import MIMEText
from math import atan2, cos, radians, sin, sqrt

import folium
import pandas as pd
import plotly.express as px
import requests
import sqlite3
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from matplotlib.pylab import normal
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from streamlit_cookies_controller import CookieController
from streamlit_folium import st_folium
from supabase import create_client
from folium.plugins import MarkerCluster

# ==========================================
# 1. ABSOLUTE TOP: INITIALIZE PAGE CONFIG (ONCE)
# ==========================================
st.set_page_config(
    page_title="Karnataka Travel Guide",
    page_icon="🌍",
    layout="wide",
    menu_items={
        "Get Help": "https://github.com/rajudabbin",
        "About": "# Karnataka Travel Guide\nOptimize routes, estimate budgets, and explore Karnataka tourism.",
    },
)

# Initialize Session States Safely
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None
if "page" not in st.session_state:
    st.session_state.page = "login"

# Inject Open Graph SEO configurations
components.html(
    """
    <script>
        const head = window.parent.document.head;
        function setMetaProperty(property, content) {
            let meta = head.querySelector(`meta[property="${property}"]`);
            if (!meta) {
                meta = window.parent.document.createElement('meta');
                meta.setAttribute('property', property);
                head.appendChild(meta);
            }
            meta.setAttribute('content', content);
        }
        setMetaProperty('og:title', 'Karnataka Travel Guide');
        setMetaProperty('og:description', 'Optimize your travel routes, estimate trip budgets, and explore the best of Karnataka tourism in one place.');
        setMetaProperty('og:type', 'website');
    </script>
    """,
    height=0,
    width=0,
)

# Fetch Database Secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# SEO Search Metadata Headers
st.markdown(
    """
    <head>
        <title>Karnataka Travel Guide - Smart Route Planner & Cost Estimator</title>
        <meta name="description" content="Discover beautiful destinations in Karnataka. Plan smart road trips, calculate travel costs, check live weather, and explore local hotels.">
        <meta name="author" content="Raju Dabbin">
        <meta name="robots" content="index, follow">
    </head>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. UNIFIED COOKIE CONTROLLER INITIALIZATION
# ==========================================
controller = CookieController(key="auth")

# Give the async controller a tiny window to ensure browser handshakes complete
time.sleep(0.1)

def try_cookie_signin():
    """Intercepts active tokens from the browser on a fresh refresh or load."""
    if not st.session_state.logged_in:
        try:
            access = controller.get("sb_access_token")
            refresh = controller.get("sb_refresh_token")
            user_email = controller.get("sb_user_email")

            if access and refresh:
                res = supabase.auth.set_session(access, refresh)
                if res.user:
                    st.session_state.logged_in = True
                    st.session_state.user = (
                        user_email
                        if user_email
                        else res.user.user_metadata.get("username", res.user.email)
                    )
                    st.session_state.access_token = access
                    st.session_state.refresh_token = refresh
                    if st.session_state.page in ["login", "signup"]:
                        st.session_state.page = "home"
                    return True
        except Exception:
            try:
                controller.remove("sb_access_token")
                controller.remove("sb_refresh_token")
                controller.remove("sb_user_email")
            except:
                pass
    return False

def get_local_img_base64(image_path):
    """Converts a local image file to a base64 string for HTML rendering."""
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            encoded_string = base64.b64encode(img_file.read()).decode()
        ext = image_path.split(".")[-1]
        return f"data:image/{ext};base64,{encoded_string}"
    else:
        return "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800"

DEFAULT_IMAGE = "static/default.jpg"

def restore_session():
    try:
        session_response = supabase.auth.get_session()
        if session_response and session_response.session:
            session = session_response.session
            st.session_state.logged_in = True
            st.session_state.user = session.user.user_metadata.get("username", session.user.email)
            st.session_state.page = "home"
        else:
            st.session_state.logged_in = False
    except:
        st.session_state.logged_in = False

def init_supabase_session():
    try:
        session_response = supabase.auth.get_session()
        if session_response and session_response.session:
            session = session_response.session
            st.session_state.logged_in = True
            st.session_state.user = session.user.user_metadata.get("username", session.user.email)
            st.session_state.page = "home"
    except:
        pass

def sync_session():
    try:
        session = supabase.auth.get_session()
        if session and session.user:
            st.session_state.logged_in = True
            st.session_state.user = session.user.user_metadata.get("username", session.user.email)
            st.session_state.sb_session = {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token
            }
    except:
        pass

def get_osrm_route(origin_lat, origin_lon, dest_lat, dest_lon):
    url = f"http://router.project-osrm.org/route/v1/driving/{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=false"
    r = requests.get(url)
    data = r.json()
    try:
        route = data["routes"][0]
        distance_km = route["distance"] / 1000
        time_hr = route["duration"] / 3600
        return distance_km, time_hr
    except:
        return None, None

# NOTE: THE SECOND DUPLICATE ST.SET_PAGE_CONFIG CALL HAS BEEN REMOVED FROM THIS LOCATION TO PREVENT STATE RESET

# =========================================================================
# CENTRALIZED THEME INJECTION MAPPED ACCORDING TO YOUR DESIGN PREFERENCES
# =========================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght=300;400;500;600;700;800&display=swap');

/* GLOBAL APP THEME */
html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
}

:root {
    --tea-estate-green: #113224;      
    --coastal-ocean-blue: #0f2d4a;    
    --accent-gold: #f5b025;           
    --accent-sandstone: #dfc59f;      
    --text-cream: #f5e6d3;            
    --card-bg: rgba(11, 26, 36, 0.75); 
}

.stApp {
    background: linear-gradient(135deg, var(--tea-estate-green), var(--coastal-ocean-blue)) !important;
    color: #f1f5f9 !important;
    transition: 0.3s;
}

/* Hide default headers/footers */
header { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* TEXT COLORS & HEADINGS */
h1 { 
    color: #ffffff !important; 
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.6) !important;
}

h2, h3, h4, h5, h6 {
    color: var(--accent-sandstone) !important; 
    font-weight: 800 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
    text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.7) !important;
}

label[data-testid="stWidgetLabel"] p {
    color: var(--accent-sandstone) !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.6) !important;
}

/* HEADER ANCHOR LINK ICONS */
h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
    color: var(--accent-sandstone) !important; 
    opacity: 0.3;                             
    transition: opacity 0.3s ease !important;
}
h1:hover a, h2:hover a, h3:hover a {
    color: var(--accent-gold) !important;     
    opacity: 1 !important;
}

/* UNIFIED CARDS (HOME RECOMMENDED & TRIP GENERATOR ITINERARY) */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    background: var(--card-bg) !important;
    border: 2px solid var(--accent-sandstone) !important; 
    border-radius: 24px !important;
    box-shadow: 0px 10px 30px rgba(0, 0, 0, 0.45) !important;
    padding: 20px !important;
    transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
    transform: translateY(-5px) !important;
    border-color: var(--accent-gold) !important; 
    box-shadow: 0px 15px 35px rgba(245, 176, 37, 0.2) !important;
    background: linear-gradient(145deg, rgba(17, 50, 36, 0.85), rgba(15, 45, 74, 0.85)) !important;
}

/* =========================================================================
   STRICT STRUCTURAL INPUT UNIFICATION
   ========================================================================= */
div[data-testid="stTextInput"], div[data-baseweb="input"] {
    background: transparent !important;
    border: none !important;
    width: 100% !important;
    overflow: visible !important;
}

div[data-baseweb="base-input"] {
    border-radius: 12px !important;
    background-color: rgba(20, 26, 30, 0.85) !important; 
    border: 2px solid var(--accent-sandstone) !important; 
    box-shadow: inset 0px 2px 5px rgba(0, 0, 0, 0.5) !important;
    transition: all 0.3s ease-in-out !important;
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    height: 48px !important;            
    box-sizing: border-box !important;   
    padding: 0px 14px !important;        
}

div[data-testid="stTextInput"] [data-baseweb="input"] {
    display: flex !important;
    width: 100% !important;
}
div[data-testid="stTextInput"] [data-baseweb="base-input"] {
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
}
div[data-testid="stTextInput"] [data-baseweb="base-input"] > div:first-child {
    width: 100% !important;
    flex-grow: 1 !important;
}
div[data-testid="stTextInput"] input {
    width: 100% !important;
    margin-right: 0px !important;
    padding-right: 0px !important;
}

div[data-baseweb="base-input"]:hover, 
div[data-baseweb="base-input"]:focus-within {
    border-color: var(--accent-gold) !important; 
    box-shadow: 0px 0px 12px rgba(245, 176, 37, 0.3) !important;
    background-color: rgba(20, 26, 30, 0.92) !important;
}

div[data-baseweb="base-input"] input {
    color: var(--text-cream) !important; 
    font-family: 'Poppins', sans-serif !important;
    background-color: transparent !important;
    border: none !important;
    height: 100% !important;
    width: 100% !important;
    padding: 0px !important; 
    margin: 0px !important;
}

/* PASSWORD EYE ICON TOGGLE */
div[data-baseweb="base-input"] button {
    background-color: transparent !important;
    border: none !important;
    color: var(--accent-sandstone) !important;
    box-shadow: none !important;
    height: 100% !important;
    width: auto !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: 0 0 0 10px !important; 
}
div[data-baseweb="base-input"] button svg {
    fill: var(--accent-sandstone) !important; 
    width: 20px !important;
    height: 20px !important;
}
div[data-baseweb="base-input"] button:hover svg {
    fill: var(--accent-gold) !important; 
}

/* =========================================================================
   HOME PAGE & TRIP GENERATOR SELECT WIDGETS
   ========================================================================= */
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    border-radius: 12px !important;
    border: 2px solid #dfc59f !important; 
    box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.4) !important;
    background: transparent !important; 
    transition: all 0.3s ease-in-out !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:first-child {
    border-radius: 10px !important; 
    background: linear-gradient(135deg, #113224, #0f2d4a) !important; 
    transition: all 0.3s ease-in-out !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"]:hover, 
div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {
    border-color: #f5b025 !important; 
    box-shadow: 0px 0px 14px rgba(245, 176, 37, 0.4) !important;
}
div[data-testid="stSelectbox"] div[role="button"] span,
div[data-testid="stSelectbox"] div[role="button"] {
    color: #f5e6d3 !important; 
    font-family: 'Poppins', sans-serif !important;
    font-weight: 600 !important;
    font-size: 16px !important;
    background-color: transparent !important;
    background: transparent !important; 
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] svg {
    fill: #dfc59f !important; 
}

/* OPENED POPUP PORTAL DRAWER OPTIONS */
div[data-baseweb="popover"] ul {
    background-color: #0f2d4a !important; 
    border: 2px solid #dfc59f !important;
    border-radius: 12px !important;
    padding: 4px 0 !important;
}
div[data-baseweb="popover"] ul li {
    background-color: transparent !important;
    color: #f5e6d3 !important;
    font-family: 'Poppins', sans-serif !important;
    font-weight: 500 !important;
}
div[data-baseweb="popover"] ul li[aria-selected="true"],
div[data-baseweb="popover"] ul li:hover {
    background: linear-gradient(90deg, #113224, #1c4e79) !important; 
    color: #ffffff !important;
}

/* =========================================================================
   TRIP PLANNER SPECIALIZED COMPONENT OVERRIDES
   ========================================================================= */
/* DESTINATION DISTRICTS (st.multiselect layout) */
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div:first-child {
    border-radius: 10px !important;
    background: linear-gradient(135deg, #113224, #0f2d4a) !important; 
}
div[data-testid="stMultiSelect"] div[data-baseweb="select"] div[dir="aria-hidden"] {
    color: #dfc59f !important;
    opacity: 0.8 !important;
}
div[data-testid="stMultiSelect"] input {
    color: #f5e6d3 !important;
}

/* SLIDERS (st.slider full tracks) */
div[data-testid="stSlider"] [data-baseweb="slider"] > div > div:first-child {
    background: linear-gradient(90deg, #113224, #0f2d4a) !important; 
    height: 8px !important;
    border-radius: 4px !important;
}
div[data-testid="stSlider"] [data-baseweb="slider"] > div {
    background-color: rgba(20, 26, 30, 0.85) !important; 
    height: 8px !important;
    border-radius: 4px !important;
    border: none !important;
}
div[data-testid="stSlider"] [data-baseweb="slider"] + div div {
    color: #f5e6d3 !important; 
    font-family: 'Poppins', sans-serif !important;
    font-weight: 500 !important;
}
div[data-testid="stSlider"] [role="slider"] {
    background-color: var(--accent-gold) !important;
    border: 2px solid var(--accent-sandstone) !important;
    box-shadow: 0px 0px 8px rgba(0, 0, 0, 0.5) !important;
}

/* TRAVELERS (st.number_input setup) */
div[data-testid="stNumberInput"] div[data-baseweb="input"] {
    background: linear-gradient(135deg, #113224, #0f2d4a) !important; 
    border: 2px solid #dfc59f !important; 
    border-radius: 12px 0px 0px 12px !important; 
    box-shadow: inset 0px 2px 5px rgba(0, 0, 0, 0.5) !important;
}
div[data-testid="stNumberInput"] [data-baseweb="base-input"] {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
div[data-testid="stNumberInput"] input {
    color: #f5e6d3 !important; 
    font-family: 'Poppins', sans-serif !important;
    font-weight: 600 !important;
}
div[data-testid="stNumberInput"] button {
    background-color: rgba(20, 26, 30, 0.95) !important; 
    border: 2px solid #dfc59f !important;
    color: #dfc59f !important; 
    transition: all 0.2s ease !important;
}
div[data-testid="stNumberInput"] button:hover {
    background-color: #f5b025 !important; 
    color: #0f2d4a !important; 
    border-color: #f5b025 !important;
}

/* =========================================================================
   NAVIGATION & ACTIONS BUTTON LAYOUTS
   ========================================================================= */
.stButton > button, div[data-testid="stLinkButton"] a {
    width: 100% !important;
    height: 46px !important;
    background: rgba(255, 255, 255, 0.04) !important;
    backdrop-filter: blur(15px) !important;
    border: 2px solid var(--accent-sandstone) !important; 
    border-radius: 14px !important;
    color: var(--text-cream) !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    text-decoration: none !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: all 0.3s ease !important;
}
.stButton > button:hover, div[data-testid="stLinkButton"] a:hover {
    background: linear-gradient(135deg, #e59a1a, #c84b31) !important; 
    color: #ffffff !important;
    transform: translateY(-3px) !important;
    box-shadow: 0 12px 25px rgba(229, 154, 26, 0.3) !important;
    border: 2px solid rgba(255, 255, 255, 0.4) !important;
}
div[data-testid="column"]:last-child .stButton > button {
    background: rgba(200, 75, 49, 0.12) !important;
    border: 2px solid rgba(200, 75, 49, 0.35) !important;
}
div[data-testid="column"]:last-child .stButton > button:hover {
    background: linear-gradient(135deg, #c84b31, #851c1c) !important;
    box-shadow: 0 12px 25px rgba(200, 75, 49, 0.35) !important;
}

/* FOLIUM TOURISM MAP WIDTH FIX */
div[data-testid="stHtmlBlock"] iframe, 
div.element-container iframe[title="streamlit_folium.st_folium"] {
    width: 100% !important;
    border-radius: 20px !important;
    border: 2px solid var(--accent-sandstone) !important; 
    box-shadow: 0px 10px 30px rgba(0, 0, 0, 0.45) !important;
    background-color: #141a1e !important; 
}
div[data-testid="stHtmlBlock"] {
    width: 100% !important;
    max-width: 100% !important;
    overflow-x: hidden !important;
}

/* UTILITIES */
.block-container {
    max-width: 1600px;
    padding-top: 1.5rem;
    padding-left: 2rem;
    padding-right: 2rem;
}
.zoom-img { 
    transition: transform 0.4s ease; 
    border: 1px solid rgba(245, 176, 37, 0.1);
}
.zoom-img:hover { 
    transform: scale(1.03); 
    border-color: var(--accent-gold);
}
a { color: var(--accent-gold); font-weight: 600; text-decoration: none; }
a:hover { text-decoration: underline; color: #ffffff; }
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-thumb { background: var(--tea-estate-green); border-radius: 10px; }

/* =========================================================================
   MASTER VALUE TEXT SELECTION HIGHLIGHT FIX (HOME & TRIP GENERATOR)
   ========================================================================= */
div[data-testid="stSelectbox"] div[role="button"] span,
div[data-testid="stSelectbox"] div[role="button"],
div[data-testid="stSelectbox"] [data-testid="stMarkdownContainer"] p,
div[data-testid="stSelectbox"] div[data-baseweb="select"] [aria-selected="true"],
.stSelectbox div[data-baseweb="select"] > div,
div[data-baseweb="select"] div[title] {
    color: #f5e6d3 !important;                  
    font-family: 'Poppins', sans-serif !important;
    font-weight: 600 !important;
    font-size: 16px !important;
    -webkit-text-fill-color: #f5e6d3 !important; 
    opacity: 1 !important;                       
}

div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background-color: transparent !important;
}

/* =========================================================================
   MULTIPLE SELECTION CHIPS & STEPPER BUTTON CLEANUP
   ========================================================================= */
div[data-testid="stMultiSelect"] div[data-baseweb="select"] span,
div[data-testid="stMultiSelect"] div[data-baseweb="select"] div[role="button"],
div[data-testid="stMultiSelect"] [data-baseweb="select"] div {
    color: #f5e6d3 !important;  
    font-family: 'Poppins', sans-serif !important;
    font-weight: 600 !important;
    font-size: 16px !important;             
    -webkit-text-fill-color: #f5e6d3 !important; 
    opacity: 1 !important;
}

div[data-testid="stMultiSelect"] div[data-baseweb="select"] div[dir="aria-hidden"] {
    color: #dfc59f !important;                  
    -webkit-text-fill-color: #dfc59f !important;
    opacity: 0.7 !important;
}

/* =========================================================================
   BORDERLESS STEPPER BUTTON FIX (st.number_input)
   ========================================================================= */
div[data-testid="stNumberInput"] button {
    background-color: transparent !important;   
    background: transparent !important;
    border: none !important;                     
    border-left: none !important;
    border-right: none !important;
    border-top: none !important;
    border-bottom: none !important;
    color: #dfc59f !important; 
    box-shadow: none !important;
    transition: all 0.2s ease-in-out !important;
}

div[data-testid="stNumberInput"] button:hover {
    background: linear-gradient(135deg, #e59a1a, #c84b31) !important;
    background-color: linear-gradient(135deg, #e59a1a, #c84b31) !important;
    color: #f5b025 !important; 
    transform: scale(1.15) !important; 
    border: none !important;
}

div[data-testid="stNumberInput"] div[data-baseweb="input"] {
    border: 2px solid #dfc59f !important;
    border-radius: 12px !important; 
}

/* =========================================================================
   STRICT BORDER & TRANSITION STEPS FIX
   ========================================================================= */
div[data-testid="stMultiSelect"] div[data-baseweb="select"] {
    border-radius: 12px !important;
    border: 2px solid #dfc59f !important; 
    box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.4) !important;
    background: transparent !important;
    transition: all 0.3s ease-in-out !important;
}

div[data-testid="stMultiSelect"] div[data-baseweb="select"]:hover,
div[data-testid="stMultiSelect"] div[data-baseweb="select"]:focus-within {
    border-color: #f5b025 !important; 
    box-shadow: 0px 0px 14px rgba(245, 176, 37, 0.4) !important;
}

div[data-testid="stNumberInput"] {
    width: 100% !important;
}

div[data-testid="stNumberInput"] > div {
    border: 2px solid #dfc59f !important;       
    border-radius: 12px !important;              
    background: linear-gradient(135deg, #113224, #0f2d4a) !important; 
    box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.4) !important;
    height: 48px !important;                     
    display: flex !important;
    align-items: center !important;
    box-sizing: border-box !important;
    padding: 0px 14px !important;                
    transition: all 0.3s ease-in-out !important;
}

div[data-testid="stNumberInput"] > div:hover,
div[data-testid="stNumberInput"] > div:focus-within {
    border-color: #f5b025 !important;            
    box-shadow: 0px 0px 14px rgba(245, 176, 37, 0.4) !important;
}

div[data-testid="stNumberInput"] div[data-baseweb="input"],
div[data-testid="stNumberInput"] [data-baseweb="base-input"],
div[data-testid="stNumberInput"] [data-baseweb="input"] > div {
    background-color: transparent !important;
    background: transparent !important;
    border: none !important;                     
    outline: none !important;
    box-shadow: none !important;                 
    height: 100% !important;
}

/* =========================================================================
   REVIEWS & FEEDBACK PERFECT THEME FIX
   ========================================================================= */
div[data-testid="stForm"] div[data-testid="stTextArea"] textarea {
    min-height: 140px !important;
    height: 140px !important;
    color: #f5e6d3 !important; 
    background-color: rgba(15, 45, 74, 0.4) !important; 
    background: rgba(15, 45, 74, 0.4) !important;
    border: 2px solid #dfc59f !important; 
    border-radius: 12px !important;
    padding: 12px !important;
    opacity: 1 !important;
    visibility: visible !important;
    -webkit-text-fill-color: #f5e6d3 !important; 
}

div[data-testid="stForm"] div[data-testid="stTextArea"] [data-baseweb="base-input"],
div[data-testid="stForm"] div[data-testid="stTextArea"] > div {
    height: auto !important;
    min-height: 140px !important;
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

div[data-testid="stForm"] div[data-testid="stTextArea"] textarea::placeholder {
    color: rgba(223, 197, 159, 0.6) !important; 
}

div[data-testid="stForm"] button[type="submit"] {
    width: 100% !important;
    height: 46px !important;
    background: #113224 !important; 
    border: 2px solid #dfc59f !important; 
    border-radius: 14px !important;
    color: #f5e6d3 !important; 
    font-size: 15px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.3) !important;
}

div[data-testid="stForm"] button[type="submit"]:hover {
    background: linear-gradient(135deg, #e59a1a, #c84b31) !important; 
    color: #ffffff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(229, 154, 26, 0.3) !important;
    border-color: #ffffff !important;
}

div[data-testid="stExpander"] summary {
    background-color: rgba(17, 50, 36, 0.3) !important;
    border-radius: 12px !important;
    border: 1px solid rgba(223, 197, 159, 0.2) !important;
}
div[data-testid="stExpander"] summary:hover {
    border-color: #f5b025 !important;
}

/* =========================================================================
   STRICT FORM SUBMIT BUTTON UNIFICATION OVERRIDE
   ========================================================================= */
div[data-testid="stFormSubmitButton"] button, 
div[data-testid="stForm"] button[type="submit"] {
    width: 100% !important;
    height: 46px !important;
    background: #113224 !important; 
    background-color: #113224 !important;
    border: 2px solid var(--accent-sandstone) !important; 
    border-radius: 14px !important;
    color: var(--text-cream) !important; 
    -webkit-text-fill-color: var(--text-cream) !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: all 0.3s ease !important;
    box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.4) !important;
}

div[data-testid="stFormSubmitButton"] button:hover,
div[data-testid="stForm"] button[type="submit"]:hover {
    background: linear-gradient(135deg, #e59a1a, #c84b31) !important; 
    background-color: #e59a1a !important;
    color: #ffffff !important; 
    -webkit-text-fill-color: #ffffff !important;
    transform: translateY(-3px) !important; 
    box-shadow: 0 12px 25px rgba(229, 154, 26, 0.35) !important;
    border: 2px solid rgba(255, 255, 255, 0.5) !important;
}

/* =========================================================================
   STRICT REVIEWS TEXT AREA TRANSPARENCY & VISIBILITY OVERRIDE
   ========================================================================= */
div[data-testid="stForm"] div[data-testid="stTextArea"] textarea {
    min-height: 140px !important;
    height: 140px !important;
    background: transparent !important;
    background-color: transparent !important;
    color: #f5e6d3 !important;                    
    -webkit-text-fill-color: #f5e6d3 !important; 
    font-size: 16px !important;
    font-family: 'Poppins', sans-serif !important;
    font-weight: 500 !important;
    caret-color: #f5b025 !important;
    border: 2px solid #dfc59f !important;        
    border-radius: 12px !important;
    padding: 14px !important;
    opacity: 1 !important;
    visibility: visible !important;
    transition: all 0.3s ease-in-out !important;
}

div[data-testid="stForm"] div[data-testid="stTextArea"] textarea:focus,
div[data-testid="stForm"] div[data-testid="stTextArea"] textarea:active {
    color: #f5e6d3 !important;
    -webkit-text-fill-color: #f5e6d3 !important;
    border-color: #f5b025 !important;            
    box-shadow: 0px 0px 14px rgba(245, 176, 37, 0.3) !important;
    outline: none !important;
}

div[data-testid="stForm"] div[data-testid="stTextArea"],
div[data-testid="stForm"] div[data-testid="stTextArea"] [data-baseweb="base-input"],
div[data-testid="stForm"] div[data-testid="stTextArea"] > div {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

div[data-testid="stForm"] div[data-testid="stTextArea"] textarea::placeholder {
    color: rgba(245, 230, 211, 0.4) !important;
    -webkit-text-fill-color: rgba(245, 230, 211, 0.4) !important;
}

div[data-testid="stForm"] div[data-testid="stTextArea"] textarea {
    min-height: 140px !important;
    height: 140px !important;
    background: transparent !important;
    background-color: transparent !important;
    color: #f5e6d3 !important;
    -webkit-text-fill-color: #f5e6d3 !important;
    caret-color: #f5b025 !important;
    border: 2px solid #dfc59f !important;
    border-radius: 12px !important;
    padding: 14px !important;
    font-size: 16px !important;
}

/* =========================================================================
   SUGGESTION PANEL FORM INPUT FIELDS HIGHEST PRIORITY OVERRIDES
   ========================================================================= */
div[data-testid="stForm"] div[data-testid="stTextInput"] input,
div[data-testid="stForm"] div[data-testid="stTextInput"] [data-baseweb="base-input"] {
    background: transparent !important;
    background-color: transparent !important;
    color: #f5e6d3 !important;                    
    -webkit-text-fill-color: #f5e6d3 !important; 
    font-size: 16px !important;
    font-family: 'Poppins', sans-serif !important;
    font-weight: 500 !important;
    caret-color: #f5b025 !important;             
}

div[data-testid="stForm"] div[data-testid="stTextInput"] [data-baseweb="base-input"]:hover,
div[data-testid="stForm"] div[data-testid="stTextInput"] [data-baseweb="base-input"]:focus-within {
    background: transparent !important;
    background-color: transparent !important;
    border-color: #f5b025 !important;            
    box-shadow: 0px 0px 14px rgba(245, 176, 37, 0.3) !important;
}

div[data-testid="stForm"] div[data-testid="stTextInput"] input::placeholder {
    color: rgba(245, 230, 211, 0.2) !important;  
    -webkit-text-fill-color: rgba(245, 230, 211, 0.2) !important;
}

/* =========================================================================
   🌟 POWERFUL SMARTPHONE NAVIGATION & Dropdown VIEWPORT CONTROLLERS
   ========================================================================= */
@media screen and (max-width: 768px) {
    h1 {
        margin-top: -30px !important;     
        margin-bottom: 5px !important;     
        font-size: 22px !important;        
    }

    div[data-testid="stHorizontalBlock"]:has(button) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;        
        justify-content: center !important;
        gap: 5px !important;
    }

    div[data-testid="stHorizontalBlock"]:has(button) > div {
        min-width: calc(33.33% - 6px) !important; 
        max-width: calc(50% - 6px) !important;
        flex-grow: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    div[data-testid="stHorizontalBlock"]:has(button) button {
        height: 38px !important;             
        font-size: 11px !important;           
        padding: 0px 2px !important;          
        letter-spacing: -0.3px !important;    
        white-space: nowrap !important;       
        text-overflow: clip !important;
    }

    div[data-testid="stHorizontalBlock"]:has(button) button p::first-letter,
    div[data-testid="stHorizontalBlock"]:has(button) button span::first-letter {
        color: transparent !important;
        text-shadow: none !important;
        font-size: 0px !important;
        letter-spacing: -10px !important;
        margin-right: -4px !important; 
    }

    div[data-testid="stHorizontalBlock"]:has(button) > div:last-child {
        min-width: 70% !important;            
        max-width: 100% !important;
        margin-top: 5px !important;
    }

    div[data-testid="stHomeView"] div[data-testid="stHorizontalBlock"]:has(div[data-testid="stSelectbox"]),
    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stSelectbox"]) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important; 
        justify-content: space-between !important;
        gap: 6px !important;         
        width: 100% !important;
    }

    div[data-testid="stHomeView"] div[data-testid="stHorizontalBlock"]:has(div[data-testid="stSelectbox"]) > div,
    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stSelectbox"]) > div {
        min-width: calc(33.33% - 4px) !important;
        max-width: calc(33.33% - 4px) !important;
        flex-grow: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    div[data-testid="stSelectbox"] label[data-testid="stWidgetLabel"] p {
        font-size: 14px !important;
        text-align: center !important;
        letter-spacing: 0.5px !important;
        margin-bottom: 2px !important;
    }

    div[data-testid="stSelectbox"] div[data-baseweb="select"],
    div[data-testid="stSelectbox"] [data-baseweb="base-input"] {
        height: 34px !important;      
        min-height: 34px !important;  
    }
    
    div[data-testid="stSelectbox"] div[role="button"] {
        padding-top: 0px !important;
        padding-bottom: 0px !important;
        font-size: 10px !important;
        line-height: 30px !important;  
        height: 28px !important;
        min-height: 28px !important;
        display: flex !important;
        align-items: center !important;
    }

    div[data-testid="stSelectbox"] div[data-baseweb="select"] svg {
        width: 16px !important;
        height: 16px !important;
    }

    /* =========================================================================
       🧮 MOBILE TRIP GENERATOR SPECIFIC LAYOUT ALIGNMENTS
       ========================================================================= */
    div[data-testid="stHomeView"] -not-needed, 
    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stNumberInput"]),
    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMultiSelect"]) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        justify-content: space-between !important;
        gap: 8px !important;
        width: 100% !important;
        margin-bottom: 4px !important;
    }

    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stNumberInput"]) > div,
    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMultiSelect"]) > div {
        min-width: calc(50% - 4px) !important;
        max-width: calc(50% - 4px) !important;
        flex-grow: 1 !important;
    }

    div[data-testid="stMultiSelect"] div[data-baseweb="select"],
    div[data-testid="stNumberInput"] > div,
    div[data-testid="stSlider"] {
        height: 38px !important;
        min-height: 38px !important;
    }

    div[data-testid="stMultiSelect"] label p,
    div[data-testid="stNumberInput"] label p,
    div[data-testid="stSlider"] label p {
        font-size: 11px !important;
        white-space: nowrap !important;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* =========================================================================
       ➕ UNBREAKABLE NUMBER STEPPER BUTTON GLYPH RECOVERY
       ========================================================================= */
    div[data-testid="stNumberInput"] button {
        background: transparent !important;
        background-color: transparent !important;
        color: #dfc59f !important;           
        opacity: 1 !important;
        visibility: visible !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 32px !important;
        height: 100% !important;
        border: none !important;             
        box-shadow: none !important;
    }

    div[data-testid="stNumberInput"] button:hover {
        color: #f5b025 !important;           
        transform: scale(1.2) !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }

    div[data-testid="stNumberInput"] input {
        text-align: center !important;
        font-size: 15px !important;
        padding: 0px !important;
        height: 100% !important;
    }
    
    /* =========================================================================
       📏 PERFECT EQUALIZATION FOR TRIP PLANNER INPUT COMPONENT BOXES
       ========================================================================= */
    div[data-testid="stSelectbox"] div[data-baseweb="select"],
    div[data-testid="stMultiSelect"] div[data-baseweb="select"],
    div[data-testid="stNumberInput"] > div,
    div[data-testid="stFormSubmitButton"] button {
        height: 44px !important;       
        min-height: 44px !important;  
        box-sizing: border-box !important;
    }

    div[data-testid="stSelectbox"] div[role="button"] {
        line-height: 40px !important;   
        height: 40px !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
        display: flex !important;
        align-items: center !important;
    }

    div[data-testid="stMultiSelect"] div[role="button"] {
        padding-top: 2px !important;
        padding-bottom: 2px !important;
        min-height: 38px !important;
    }

    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stNumberInput"]) label p,
    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMultiSelect"]) label p {
        min-height: 36px !important;    
        display: flex !important;
        align-items: flex-end !important; 
        white-space: normal !important;   
        line-height: 1.2 !important;
        margin-bottom: 6px !important;
    }
    
    /* =========================================================================
       🎯 ISOLATED NO-COLLISION EQUALIZER (TRIP DURATION & TRAVELERS ROW ONLY)
       ========================================================================= */
    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stNumberInput"]) {
        display: flex !important;
        flex-direction: row !important;
        align-items: flex-start !important; 
        gap: 8px !important;
    }

    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stNumberInput"]) > div {
        min-width: calc(50% - 4px) !important;
        max-width: calc(50% - 4px) !important;
        margin: 0px !important;
        padding: 0px !important;
    }

    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stNumberInput"]) label {
        position: static !important;
        margin-bottom: 6px !important; 
        display: block !important;
    }

    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stNumberInput"]) label p {
        font-size: 11px !important;
        white-space: nowrap !important;
        margin: 0px !important;
        padding: 0px !important;
    }

    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stNumberInput"]) div[data-testid="stSlider"] > div:first-child {
        transform: translateY(11px) !important; 
        margin: 0px !important;
        padding: 0px !important;
    }

    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stNumberInput"]) div[data-testid="stSlider"] [data-baseweb="slider"] {
        margin: 0px !important;
        padding: 0px !important;
    }
    
    /* =========================================================================
       🚀 SLIDER BOTTOM CLEARANCE EQUALIZER (PREVENTS TEXT CLIPPING)
       ========================================================================= */
    div[data-testid="stSlider"] {
        margin-bottom: 24px !important; 
    }

    div[data-testid="stSlider"] + div {
        margin-top: 12px !important;
    }
    
    /* =========================================================================
       🎯 PERFECT MATRIX MATCH (STARTING DISTRICT & DESTINATION DISTRICTS)
       ========================================================================= */
    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMultiSelect"]) {
        display: flex !important;
        flex-direction: row !important;
        align-items: flex-end !important; 
        gap: 8px !important;
        width: 100% !important;
    }

    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMultiSelect"]) > div {
        min-width: calc(50% - 4px) !important;
        max-width: calc(50% - 4px) !important;
        flex-grow: 1 !important;
        margin: 0px !important;
        padding: 0px !important;
    }

    div[data-testid="stSelectbox"] div[data-baseweb="select"],
    div[data-testid="stMultiSelect"] div[data-baseweb="select"] {
        width: 100% !important;
        height: 44px !important;         
        min-height: 44px !important;
        box-sizing: border-box !important;
    }

    div[data-testid="stSelectbox"] div[role="button"] {
        padding: 0px 14px !important;    
        height: 40px !important;
        line-height: 40px !important;
        display: flex !important;
        align-items: center !important;
    }

    div[data-testid="stMultiSelect"] div[role="button"] {
        padding: 0px 14px !important;
        min-height: 40px !important;
        display: flex !important;
        align-items: center !important;
    }

    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMultiSelect"]) label {
        min-height: 36px !important;     
        display: flex !important;
        align-items: flex-end !important; 
        margin-bottom: 6px !important;
    }

    .block-container div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMultiSelect"]) label p {
        font-size: 11px !important;
        line-height: 1.2 !important;
        margin: 0px !important;
        padding: 0px !important;
        white-space: normal !important;   
    }
}   
    
@media (max-width: 768px) {
        div[class*="st-key-card_"] [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            display: flex !important;
        }
        
        div[class*="st-key-card_"] [data-testid="stHorizontalBlock"] > div,
        div[class*="st-key-card_"] [data-testid="stHorizontalBlock"] [data-testid="stColumn"] {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 100% !important;
            flex: 1 1 100% !important;
            display: block !important;
            margin-bottom: 15px !important;
        }
        
        div[class*="st-key-card_"] [data-testid="stHorizontalBlock"] img {
            display: block !important;
            margin: 0 auto !important;
            width: 100% !important;
            max-width: 340px !important;
            height: auto !important;
        }
    }
</style>
""", unsafe_allow_html=True)

def show_branding():
    st.markdown("""
        <div style="position: fixed; bottom: 10px; width: 100%; text-align: center; font-size: 14px; color: White; opacity: 0.8; z-index: 999;">
            By Raju Dabbin
        </div>
        """, unsafe_allow_html=True)

ADMIN_USER = st.secrets["ADMIN_USER"]
ADMIN_PASS = st.secrets["ADMIN_PASS"]

st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("user", "")
st.session_state.setdefault("page", "login")
st.session_state.setdefault("fav_cache", {})
st.session_state.setdefault("otp", None)
st.session_state.setdefault("reset_user", "")
st.session_state.setdefault("admin_logged", False)
st.session_state.setdefault("show_intro", True)
st.session_state.setdefault("weather_place", None)
st.session_state.setdefault("access_token", None)
st.session_state.setdefault("refresh_token", None)
st.session_state.setdefault("password_reset_flow", False)

@st.cache_data
def load_data():
    df = pd.read_csv("karnataka_places_with_coordinates.csv")
    df.columns = df.columns.str.strip()
    df["Image"] = df["Image"].astype(str).str.extract(r'(https?://[^"]+)')
    return df

df = load_data()

def map_link(place, district):
    q = urllib.parse.quote_plus(f"{place}, {district}, Karnataka")
    return f"https://www.google.com/maps/search/?api=1&query={q}"

def goibibo_hotel_link(place, district):
    query = urllib.parse.quote_plus(f"site:goibibo.com hotels near {place} {district}")
    return f"https://www.google.com/search?q={query}"

def is_fav(place):
    key = f"{st.session_state.user}_{place}"
    if key in st.session_state.fav_cache:
        return st.session_state.fav_cache[key]
    res = supabase.table("favorites") \
        .select("*") \
        .eq("username", st.session_state.user) \
        .eq("place", place) \
        .execute()
    result = len(res.data) > 0
    st.session_state.fav_cache[key] = result
    return result

def toggle_fav(place, district, category):
    if is_fav(place):
        supabase.table("favorites") \
            .delete() \
            .eq("username", st.session_state.user) \
            .eq("place", place) \
            .execute()
        st.session_state.fav_cache[f"{st.session_state.user}_{place}"] = False
    else:
        supabase.table("favorites").insert({
            "username": st.session_state.user,
            "place": place,
            "district": district,
            "category": category
        }).execute()
        st.session_state.fav_cache[f"{st.session_state.user}_{place}"] = True

def get_place_reviews(place):
    try:
        res = supabase.table("reviews").select("*").eq("place", place).execute()
        reviews = res.data
        if not reviews:
            return 0, []
        avg_rating = sum([r['rating'] for r in reviews]) / len(reviews)
        return round(avg_rating, 1), reviews
    except Exception as e:
        return 0, []

def submit_review(username, place, rating, feedback):
    try:
        existing = supabase.table("reviews").select("id").eq("username", username).eq("place", place).execute()
        if existing.data:
            supabase.table("reviews").update({
                "rating": rating,
                "feedback": feedback
            }).eq("id", existing.data[0]["id"]).execute()
        else:
            supabase.table("reviews").insert({
                "username": username,
                "place": place,
                "rating": rating,
                "feedback": feedback
            }).execute()
        return True
    except Exception as e:
        st.error(f"Error submitting review: {e}")
        return False

def send_email_otp(receiver_email, otp):
    sender_email = "rajudabbin@gmail.com"
    sender_password = st.secrets["EMAIL_PASSWORD"]
    subject = "Karnataka Travel Guide OTP"
    body = f"Your OTP for password reset is: {otp}"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email Error: {e}")
        return False

def intro_screen():
    st.markdown("""
    <style>
    @keyframes cinematicZoom {
        0% { transform: scale(0.92); opacity: 0; }
        100% { transform: scale(1); opacity: 1; }
    }
    .intro-wrapper {
        height: 100vh;
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 20px;
        box-sizing: border-box;
    }
    .animated-banner {
        max-width: 90%;
        max-height: 80vh;
        object-fit: contain;
        border-radius: 24px;
        border: 2px solid var(--accent-sandstone);
        box-shadow: 0 20px 50px rgba(0,0,0,0.6);
        animation: cinematicZoom 1.8s cubic-bezier(0.25, 1, 0.5, 1) forwards;
    }
    </style>
    <div class="intro-wrapper">
        <img class="animated-banner" src="app/static/cover.jpg" />
    </div>
    """, unsafe_allow_html=True)
    time.sleep(3)
    st.session_state.show_intro = False
    st.rerun()

API_KEY = st.secrets["GEMINI_API_KEY"]
try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    st.error(str(e))

def nav():
    is_admin_user = False
    if st.session_state.get("logged_in") and st.session_state.get("access_token"):
        try:
            sb_auth_check = supabase.auth.get_user(st.session_state.access_token)
            if sb_auth_check and sb_auth_check.user:
                user_email = str(sb_auth_check.user.email).strip().lower()
                admin_lookup = supabase.table("users").select("phone").eq("email", user_email).execute()
                if admin_lookup.data and len(admin_lookup.data) > 0:
                    user_phone = str(admin_lookup.data[0]["phone"]).strip()
                    if user_email == "rajudabbin@gmail.com" and user_phone == "9663402766":
                        is_admin_user = True
        except:
            pass

    st.markdown("""
        <iframe id="responsive-check" style="display:none;" srcdoc="
        <script>
            const isMobile = window.innerWidth <= 768;
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: isMobile}, '*');
        </script>
        "></iframe>
    """, unsafe_allow_html=True)
    
    is_mobile = st.session_state.get("viewport_mobile", False)

    text_home = "Home" if is_mobile else "🏠 Home"
    text_trip = "Trip" if is_mobile else "🚗 Trip Planner"
    text_favs = "Favs" if is_mobile else "🤍 Favorites"
    text_dash = "Dash" if is_mobile else "📊 Dashboard"
    text_maps = "Map" if is_mobile else "🗺 Map"
    text_out  = "Logout" if is_mobile else "🚪 Logout"
    
    if is_admin_user:
        text_action = "🛡 Admin"
    else:
        text_action = "📣 Review" if is_mobile else "📣 Review & Suggest"

    if is_mobile:
        c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 1, 1, 1, 1, 1, 1])
    else:
        c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 1, 1, 1, 1, 1, 1.3])

    with c1:
        if st.button(text_home, use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
    with c2:
        if st.button(text_trip, use_container_width=True):
            st.session_state.page = "trip"
            st.rerun()
    with c3:
        if st.button(text_favs, use_container_width=True):
            st.session_state.page = "fav"
            st.rerun()
    with c4:
        if st.button(text_dash, use_container_width=True):
            st.session_state.page = "dash"
            st.rerun()
    with c5:
        if st.button(text_maps, use_container_width=True):
            st.session_state.page = "map"
            st.rerun()
                
    with c6:
        if st.button(text_out, use_container_width=True):
            try:
                supabase.auth.sign_out()
            except:
                pass
            
            # --- SAFELY REMOVE COOKIES ONLY IF THEY EXIST ---
            cookies = controller.getAll()
            if cookies:
                if "sb_access_token" in cookies:
                    controller.remove("sb_access_token")
                if "sb_refresh_token" in cookies:
                    controller.remove("sb_refresh_token")
                if "sb_user_email" in cookies:
                    controller.remove("sb_user_email")
            
            st.session_state.clear()
            st.session_state.user = ""
            st.session_state.page = "login"
            st.rerun()
            
    with c7:
        if st.button(text_action, use_container_width=True):
            if is_admin_user:
                st.session_state.page = "admin"
            else:
                st.session_state.page = "review_suggestion"
            st.rerun()

def send_suggestion_email(username, overall_rating, place, district, app_feedback, place_notes):
    sender_email = "rajudabbin@gmail.com"
    sender_password = st.secrets["EMAIL_PASSWORD"]
    
    if place == "None (App Feedback Only)":
        subject = f"⭐ New App Rating received from {username}!"
    else:
        subject = f"🚨 New Place Suggestion & Rating from {username}!"
    
    body = f"""
    Hello Raju,
    
    You have received new feedback on your platform:
    
    👤 Submitted By: {username}
    ⭐ Platform Rating: {overall_rating} / 5 Stars
    💬 App Feedback Notes: {app_feedback}
    
    --------------------------------------------------
    📍 SUGGESTED PLACE INFORMATION:
    --------------------------------------------------
    🏛 Destination Name: {place}
    🗺 District Location: {district}
    📝 User Notes About This Place: {place_notes}
    
    This feedback entry has been logged securely and is accessible inside your Admin Panel.
    """
    
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = sender_email
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, sender_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        return False

def user_suggestion_panel():
    nav()
    st.markdown("""
    <div style='padding:30px; border-radius:25px; background:linear-gradient(135deg, rgba(17, 50, 36, 0.6), rgba(15, 45, 74, 0.6)); border: 2px solid var(--accent-sandstone); margin-bottom:30px; color:white; box-shadow:0 10px 40px rgba(0,0,0,0.4); text-align: center;'>
        <h1 style='font-size:42px; color: var(--accent-gold) !important;'>📣 Platform Reviews & Suggestions</h1>
        <p style='font-size:16px; color: var(--text-cream); margin: 0;'>Rate our app and optionally suggest new missing places to help us expand!</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form(key="global_suggestion_form", clear_on_submit=True):
        st.markdown("<p style='font-size:18px; font-weight:700; color:#f5b025; margin-bottom:2px;'>⭐ Rate Your Overall Platform Experience</p>", unsafe_allow_html=True)
        app_rating = st.selectbox("How would you rate this Travel Guide App?", options=[5, 4, 3, 2, 1], format_func=lambda x: "⭐" * x)
        
        st.markdown("<p style='font-size:14px; font-weight:700; color:#dfc59f; margin-bottom:2px;'>YOUR APP FEEDBACK / EXPERIENCE:</p>", unsafe_allow_html=True)
        app_feedback = st.text_area(label="App Feedback Input Area", label_visibility="collapsed", placeholder="Tell us what you think about the app, features, or design...", key="app_feed_box")

        st.markdown("<hr style='margin: 25px 0; border-color: rgba(223, 197, 159, 0.2);'>", unsafe_allow_html=True)
        
        st.markdown("<p style='font-size:18px; font-weight:700; color:#f5b025; margin-bottom:2px;'>🗺 Suggest a Missing Tourist Spot (Optional)</p>", unsafe_allow_html=True)
        st.caption("Leave this section blank if you do not have a specific tourist place to add.")
        
        s_place = st.text_input("Place Name", placeholder="Suggest a place to add")
        s_district = st.selectbox("District Location", options=["None / Just App Review"] + sorted(list(district_hq.keys())))
        
        st.markdown("<p style='font-size:14px; font-weight:700; color:#dfc59f; margin-bottom:2px;'>WRITE SOMETHING ABOUT THIS PLACE:</p>", unsafe_allow_html=True)
        s_notes = st.text_area(label="Suggestion Details Input Area", label_visibility="collapsed", placeholder="Tell us why we should add it, nearby landmarks, road conditions, or the best time to visit...")
        
        submit_suggestion = st.form_submit_button("Submit Review & Feedback")
        
        if submit_suggestion:
            try:
                final_place = s_place.strip() if s_place.strip() else "None (App Feedback Only)"
                final_district = s_district if s_district != "None / Just App Review" else "N/A"
                final_notes = s_notes.strip() if s_notes.strip() else "N/A"
                final_app_feed = app_feedback.strip() if app_feedback.strip() else "No typed review text left."

                supabase.table("platform_suggestions").insert({
                    "username": st.session_state.user,
                    "overall_rating": app_rating,
                    "suggested_place_name": final_place,
                    "district": final_district,
                    "category": "N/A", 
                    "additional_notes": f"App Feedback: {final_app_feed} | Place Info: {final_notes}"
                }).execute()
                
                send_suggestion_email(st.session_state.user, app_rating, final_place, final_district, final_app_feed, final_notes)
                st.success("🎉 Thank you! Your review and feedback have been sent successfully.")
               
                st.session_state.page = "home"
                st.rerun()
            except Exception as e:
                st.error(f"Submission Error: {e}")

def login():
    st.markdown("""
    <div style="width:100%; border-radius:24px; overflow:hidden; border: 1px solid rgba(245, 176, 37, 0.25); box-shadow:0 15px 45px rgba(0,0,0,0.45); margin-bottom:3rem;">
        <img src="app/static/entry_banner.jpg" style="width:100%; max-height:350px; object-fit:cover; display:block;" />
    </div>
    """, unsafe_allow_html=True)

    login_input = st.text_input("Email Address or Phone Number")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if not login_input or not password:
            st.warning("Please fill in all credentials.")
            return

        target_email = login_input.strip()
        try:
            if "@" not in target_email:
                user_lookup = supabase.table("users").select("email").eq("phone", target_email).execute()
                if user_lookup.data and len(user_lookup.data) > 0:
                    target_email = user_lookup.data[0]["email"]
                else:
                    st.error("No account found matching this phone number.")
                    return

            res = supabase.auth.sign_in_with_password({"email": target_email, "password": password})
            if res.user:
                st.session_state.logged_in = True
                current_username = res.user.user_metadata.get("username", res.user.email)
                st.session_state.user = current_username
                
                if res.session:
                    st.session_state.access_token = res.session.access_token
                    st.session_state.refresh_token = res.session.refresh_token
                    
                    controller.set("sb_access_token", res.session.access_token)
                    controller.set("sb_refresh_token", res.session.refresh_token)
                    controller.set("sb_user_email", current_username)

                st.session_state.page = "home"
                st.success("Login Successful!")
                st.rerun()
                
        except Exception as e:
            st.error("Invalid credentials or email address is not verified yet.")
        
    st.markdown("---")
    if st.button("Go to Signup"):
        st.session_state.page = "signup"
        st.rerun()
    if st.button("Forgot Password"):
        st.session_state.page = "forgot"
        st.rerun()

def get_user():
    try:
        return supabase.auth.get_user()
    except:
        return None
    
def signup():
    st.markdown("""
    <div style="width:100%; border-radius:24px; overflow:hidden; border: 1px solid rgba(245, 176, 37, 0.25); box-shadow:0 15px 45px rgba(0,0,0,0.45); margin-bottom:3rem;">
        <img src="app/static/entry_banner.jpg" style="width:100%; max-height:350px; object-fit:cover; display:block;" />
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<h2>📝 Create Account</h2>", unsafe_allow_html=True)
    username = st.text_input("Username")
    email = st.text_input("Email Address")
    phone = st.text_input("Phone Number")
    password = st.text_input("Password", type="password")

    if st.button("Create Account"):
        if not username or not email or not phone or not password:
            st.warning("Please fill in all fields")
            return
        
        cleaned_phone = phone.strip()
        if not cleaned_phone.isdigit() or len(cleaned_phone) != 10:
            st.error("Invalid Phone Number! It must contain exactly 10 numbers (no spaces, letters, or country codes like +91).")
            return
            
        try:
            phone_check = supabase.table("users").select("username").eq("phone", cleaned_phone).execute()
            if phone_check.data and len(phone_check.data) > 0:
                st.error("This phone number is already registered with another account!")
                return 

            res = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": {"username": username}}
            })
            
            supabase_admin.table("users").insert({
                "username": username,
                "email": email,
                "phone": cleaned_phone
            }).execute()

            st.success("Account created successfully! Check your email inbox.")
         
            st.session_state.page = "login"
            st.rerun()
        except Exception as e:
            st.error(f"Signup session failed: {str(e)}")

    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

def forgot():
    st.markdown("""
    <div style="width:100%; border-radius:24px; overflow:hidden; border: 1px solid rgba(245, 176, 37, 0.25); box-shadow:0 15px 45px rgba(0,0,0,0.45); margin-bottom:3rem;">
        <img src="app/static/entry_banner.jpg" style="width:100%; max-height:350px; object-fit:cover; display:block;" />
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<h2>🔑 Reset via Email OTP</h2>", unsafe_allow_html=True)
    
    if "reset_email" not in st.session_state:
        st.session_state.reset_email = None
    if "otp_sent" not in st.session_state:
        st.session_state.otp_sent = False

    if not st.session_state.otp_sent:
        recovery_input = st.text_input("Enter Email Address or 10-digit Phone Number")
        if st.button("Send Verification Code", use_container_width=True):
            if not recovery_input:
                st.warning("Please enter your email or phone number.")
                return
                
            target_email = recovery_input.strip()
            if "@" not in target_email:
                if len(target_email) != 10 or not target_email.isdigit():
                    st.error("Please enter a valid email or 10-digit phone number.")
                    return
                
                user_lookup = supabase.table("users").select("email").eq("phone", target_email).execute()
                if user_lookup.data and len(user_lookup.data) > 0:
                    target_email = user_lookup.data[0]["email"]
                else:
                    st.error("No account found matching this phone number.")
                    return
            
            try:
                supabase.auth.reset_password_for_email(target_email)
                st.session_state.reset_email = target_email
                st.session_state.otp_sent = True
                st.success(f"A 6-digit recovery OTP has been dispatched to your email inbox!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to send OTP: {str(e)}")

        st.markdown("---")
        if st.button("⬅ Back to Login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()
    else:
        st.info(f"Verifying account linked to email: {st.session_state.reset_email}")
        otp_code = st.text_input("Enter 6-Digit Verification Token", max_chars=6)
        if st.button("Verify Code", use_container_width=True):
            if not otp_code or len(otp_code) != 6:
                st.warning("Please enter a valid 6-digit token.")
                return
                
            try:
                res = supabase.auth.verify_otp({
                    "email": st.session_state.reset_email,
                    "token": otp_code.strip(),
                    "type": "recovery"
                })
                if res.session:
                    st.success("OTP Verified Successfully")
                    st.session_state.access_token = res.session.access_token
                    st.session_state.refresh_token = res.session.refresh_token
                    st.session_state.password_reset_flow = True
                    st.session_state.otp_sent = False
                    st.session_state.page = "reset"
                    st.rerun()
                else:
                    st.error("Invalid or expired code. Please verify the code from your inbox.")
            except Exception as e:
                st.error(f"Verification failed: {str(e)}")
                
        if st.button("🔄 Resend Code", use_container_width=False):
            st.session_state.otp_sent = False
            st.rerun()

def reset_password():
    st.title("Reset Password")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Update Password"):
        if new_password != confirm_password:
            st.error("Passwords do not match")
            return
        try:
            supabase.auth.set_session(st.session_state.access_token, st.session_state.refresh_token)
            supabase.auth.update_user({"password": new_password})
            try:
                supabase.auth.sign_out()
            except:
                pass

            st.session_state.logged_in = False
            st.session_state.user = ""
            st.session_state.access_token = None
            st.session_state.refresh_token = None
            st.session_state.password_reset_flow = False
            st.success("Password updated successfully. Please login with your new password.")
          
            st.session_state.page = "login"
            st.rerun()
        except Exception as e:
            st.error(str(e))
            
def home():
    nav()
    st.markdown("""
    <div style="width: 100%; border-radius: 24px; overflow: hidden; border: 1px solid rgba(245, 176, 37, 0.25); box-shadow: 0 15px 45px rgba(0,0,0,0.45); margin-bottom: 2.5rem;">
        <img src="app/static/entry_banner.jpg" style="width: 100%; max-height: 350px; object-fit: cover; display: block;" />
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"<h1>Welcome {st.session_state.user}</h1>", unsafe_allow_html=True)
    month_order = ["January","February","March","April","May","June","July","August","September","October","November","December"]

    # Unified layout deployment: Streamlit's columns wrapper will now render 
    # horizontally on desktop AND mobile viewports due to the injected CSS rule.
    col_layout = st.columns([1, 1, 1])
    with col_layout[0]:
        district = st.selectbox("District", ["All"] + sorted(df["District"].unique()))
    with col_layout[1]:
        category = st.selectbox("Category", ["All"] + sorted(df["Category"].unique()))
    with col_layout[2]:
        month = st.selectbox("Month", ["All"] + month_order)
        
    temp = df.copy()
    if district != "All":
        temp = temp[temp["District"] == district]
    if category != "All":
        temp = temp[temp["Category"] == category]
    if month != "All":
        temp["score"] = temp["Best_Month"].apply(lambda x: 10 if x == month else 1)
        temp = temp.sort_values("score", ascending=False)

    st.markdown("<h2>Recommended Places</h2>", unsafe_allow_html=True)

    # =========================================================================
    # RECOMMENDED PLACES LOOP WITH RESPONSIVE 2X2 BUTTON MATRIX FOR MOBILE
    # =========================================================================
    for idx, r in temp.head(20).iterrows():
        fav = is_fav(r["Place"])
        icon = "❤️" if fav else "🤍"
        
        avg_rating, total_reviews = get_place_reviews(r["Place"])
        star_display = "⭐" * int(round(avg_rating)) if avg_rating > 0 else "No ratings yet"
        rating_text = f"|  {avg_rating} / 5 ({len(total_reviews)} reviews)" if avg_rating > 0 else ""

        # Injecting only the target-specific media queries for responsive mobile scaling layout
        st.markdown(f"""
            <style>
            @media screen and (max-width: 768px) {{
                div#card_wrapper_{idx} > div[data-testid="stHorizontalBlock"] {{
                    display: flex !important;
                    flex-direction: column !important;
                    gap: 12px !important;
                }}
                div#card_wrapper_{idx} > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
                    min-width: 100% !important;
                    max-width: 100% !important;
                    width: 100% !important;
                    padding: 0 !important;
                    margin: 0 !important;
                }}
                div#card_wrapper_{idx} > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1) {{ order: 1 !important; }}
                div#card_wrapper_{idx} > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {{ order: 2 !important; }}
                div#card_wrapper_{idx} > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) {{ order: 3 !important; }}
                
                div#card_wrapper_{idx} img.zoom-img {{
                    width: 100% !important;
                    max-height: 230px !important;
                    object-fit: cover !important;
                    border-radius: 16px !important;
                }}
                div#card_wrapper_{idx} h3 {{
                    word-break: break-word !important;
                    white-space: normal !important;
                    font-size: 24px !important;
                    margin-top: 6px !important;
                }}
                div#card_wrapper_{idx} > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {{
                    display: grid !important;
                    grid-template-columns: repeat(2, 1fr) !important;
                    gap: 10px !important;
                    width: 100% !important;
                    margin-top: 10px !important;
                }}
                div#card_wrapper_{idx} div[data-testid="column"]:last-child > div {{
                    width: 100% !important;
                }}
            }}
            </style>
        """, unsafe_allow_html=True)

        # Build card container with a clean, standard layout tracking wrapper ID
        st.markdown(f'<div id="card_wrapper_{idx}">', unsafe_allow_html=True)
        
        # Enforce standard native theme boundaries (border=True handles alignment cleanly)
        with st.container(border=True, key=f"card_container_block_{idx}"):
            col_img, col_txt, col_btn = st.columns([1.2, 3.1, 0.7], gap="small")

            with col_img:
                st.markdown(f"""
                    <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%;">
                        <img src="{str(r['Image']).strip() if pd.notna(r['Image']) else DEFAULT_IMAGE}" 
                            class="zoom-img" 
                            style="width: 320px; height: 220px; object-fit: cover; border-radius: 16px;" 
                            onerror="this.onerror=null; this.src='{DEFAULT_IMAGE}';" />
                    </div>
                    """, unsafe_allow_html=True)

            with col_txt:
                st.markdown(f"### {icon} {r['Place']}")
                st.markdown(f"<span style='color: #f5b025; font-weight: bold;'>{star_display}</span> <span style='color: #dfc59f; font-size: 14px;'>{rating_text}</span>", unsafe_allow_html=True)
                st.write(r['Short_Description'])
                st.markdown(f"📍 **District:** {r['District']}   |   🏕 **Category:** {r['Category']}   |   ☀️ **Best Month:** {r['Best_Month']}")
                st.markdown(f"<div style='text-align: center; margin-top: 15px;'><a href='{map_link(r['Place'], r['District'])}' target='_blank' style='font-size: 16px; font-weight: 700; color: #f5b025;'>📌 Open in Google Maps</a></div>", unsafe_allow_html=True)

            with col_btn:
                hotel_url = goibibo_hotel_link(r["Place"], r["District"])
                photo_url = google_images_link(r["Place"], r["District"])

                st.markdown(
                    """
                    <style>
                    .responsive-grid {
                        display: flex;
                        flex-direction: column;
                        gap: 10px;
                        width: 100%;
                    }
                    @media (max-width: 768px) {
                        .responsive-grid {
                            flex-direction: row;
                            flex-wrap: wrap;
                        }
                        .responsive-grid > div {
                            flex: 1 1 calc(50% - 5px) !important;
                            min-width: calc(50% - 5px);
                        }
                    }
                    </style>
                    """,
                    unsafe_allow_html=True
                )

                with st.container(border=False):
                    st.markdown('<div class="responsive-grid">', unsafe_allow_html=True)
                    
                    if st.button("✓ Added" if fav else "+ Favorite", key=f"btn_fav_{idx}", use_container_width=True):
                        toggle_fav(r["Place"], r["District"], r["Category"])
                        st.rerun()
                        
                    if st.button("🌦 Weather", key=f"btn_weather_{idx}", use_container_width=True):
                        st.session_state.weather_place = None if st.session_state.weather_place == r["Place"] else r["Place"]
                        st.rerun()

                    st.link_button("🏨 Hotels", hotel_url, use_container_width=True)
                    st.link_button("📸 Photos", photo_url, use_container_width=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        
            # Weather display accordion section
            if st.session_state.weather_place == r["Place"]:
                weather = get_weather(r["Latitude"], r["Longitude"])
                if weather:
                    st.markdown(f"""
                        <div style="margin-top:10px; padding:15px; border-radius:15px; background:rgba(245,176,37,0.1); border:2px solid var(--accent-gold); font-size:18px; font-weight:600;">
                            🌡 Temperature: {weather['temp']} °C<br>
                            💧 Humidity: {weather['humidity']}%<br>
                            ☁ Condition: {weather['desc'].title()}
                        </div>
                        """, unsafe_allow_html=True)

            # Community feedback expandable review blocks
            with st.expander("💬 Reviews & Leave Feedback", expanded=False):
                st.markdown("<p style='font-size:16px; font-weight:700; color:#f5b025; margin-top:5px; margin-bottom:5px;'>⭐ Share Your Experience</p>", unsafe_allow_html=True)
                
                with st.form(key=f"review_form_{idx}", clear_on_submit=True):
                    star_score = st.selectbox(
                        "SELECT RATING:", 
                        options=[5, 4, 3, 2, 1], 
                        format_func=lambda x: "⭐" * x,
                        key=f"star_sel_{idx}"
                    )
                    
                    st.markdown("<p style='font-size:14px; font-weight:700; color:#dfc59f; margin-bottom:2px;'>WRITE YOUR DETAILED REVIEW:</p>", unsafe_allow_html=True)
                    user_feedback = st.text_area(
                        label="Review Text Input Block Area",
                        label_visibility="collapsed", 
                        placeholder="Tell us about your trip experience, road conditions, amenities...", 
                        key=f"feed_{idx}"
                    )
                    
                    submit_btn = st.form_submit_button("Submit Review")
                    
                    if submit_btn:
                        if submit_review(st.session_state.user, r["Place"], star_score, user_feedback):
                            st.success("Thank you for your rating!")
                            st.rerun()

                if total_reviews:
                    st.markdown("<hr style='margin: 15px 0; border-color: rgba(223, 197, 159, 0.2);'>", unsafe_allow_html=True)
                    st.markdown("<p style='font-weight:700; color:var(--accent-sandstone); margin-bottom:10px;'>Recent Community Feedback:</p>", unsafe_allow_html=True)
                    for rev in total_reviews[:5]:
                        stars = "⭐" * rev['rating']
                        st.markdown(f"""
                            <div style="background: rgba(255,255,255,0.03); padding: 12px; border-radius: 12px; margin-bottom: 10px; border: 1px solid rgba(223, 197, 159, 0.15);">
                                <strong style="color:var(--accent-gold);">{rev['username']}</strong> <span style="font-size:13px; color:#dfc59f; margin-left:6px;">{stars}</span>
                                <p style="margin: 6px 0 0 0; font-size:14px; line-height:1.5; color:#f5e6d3;">{rev['feedback'] if rev['feedback'] else 'No written review left.'}</p>
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.caption("No written reviews yet. Be the first to add yours!")
        st.markdown('</div>', unsafe_allow_html=True)
        
def google_images_link(place, district):
    query = urllib.parse.quote_plus(f"{place} {district} Karnataka")
    return f"https://www.google.com/search?q={query}&tbm=isch"
 
def get_weather(lat, lon):
    API_KEY = st.secrets["OPENWEATHER_API"]
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    try:
        data = requests.get(url).json()
        return {
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "desc": data["weather"][0]["description"]
        }
    except:
        return None
 
def generate_itinerary_pdf(user_query, ai_response):
    pdf_file = "itinerary.pdf"
    doc = SimpleDocTemplate(pdf_file)
    styles = getSampleStyleSheet()
    content = []
    title = Paragraph("Karnataka Travel Guide - Travel Itinerary", styles["Title"])
    content.append(title)
    content.append(Spacer(1, 20))
    content.append(Paragraph(f"<b>User Request:</b><br/>{user_query}", styles["BodyText"]))
    content.append(Spacer(1, 10))
    content.append(Paragraph(f"<b>AI Travel Plan:</b><br/>{ai_response}", styles["BodyText"]))
    doc.build(content)
    return pdf_file

def favorites():
    nav()
    st.markdown("<h2>Favorites</h2>", unsafe_allow_html=True)
    
    try:
        res = supabase.table("favorites") \
            .select("*") \
            .eq("username", st.session_state.user) \
            .execute()
        favs = res.data
    except Exception as e:
        st.error(f"Error loading favorites: {e}")
        favs = []

    if not favs:
        st.info("No favorites added yet. Head back to Home to save some tourist spots!")
        return

    for f in favs:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #113224, #0f2d4a) !important; 
                    border: 2px solid var(--accent-sandstone); 
                    padding: 20px; 
                    border-radius: 24px; 
                    margin-bottom: 15px;
                    box-shadow: 0px 4px 15px rgba(0,0,0,0.3);">
            <div style="font-size: 24px; font-weight: 700; color: #ffffff; margin-bottom: 5px;">❤️ {f['place']}</div>
            <p style="margin: 0; color: var(--accent-sandstone); font-weight: 500;">📍 {f['district']} | 🏕 {f['category']}</p>
        </div>
        """, unsafe_allow_html=True)

def tourism_map():
    nav()
    st.markdown("<h2>🗺 Karnataka Tourism Map</h2>", unsafe_allow_html=True)
    map_df = df.dropna(subset=["Latitude", "Longitude"])
    m = folium.Map(location=[15.3173, 75.7139], zoom_start=7)
    cluster = MarkerCluster().add_to(m)

    marker_colors = ["red","blue","green","purple","orange","darkred","lightred","beige","darkblue","darkgreen","cadetblue","darkpurple","pink","lightblue","lightgreen","gray","black"]
    categories = sorted(df["Category"].unique())
    category_colors = {cat: marker_colors[i % len(marker_colors)] for i, cat in enumerate(categories)}
    
    for _, row in map_df.iterrows():
        img_url = str(row['Image']).strip() if pd.notna(row['Image']) else DEFAULT_IMAGE
        popup_html = f"""
        <div style='width:250px'>
            <h4>{row['Place']}</h4>
            <img src="{img_url}" width="220" onerror="this.onerror=null; this.src='{DEFAULT_IMAGE}';">
            <p><b>District:</b> {row['District']}</p>
            <p>{row['Short_Description'][:120]}...</p>
            <a href="{map_link(row['Place'], row['District'])}" target="_blank">Open in Google Maps</a>
        </div>
        """
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row["Place"],
            icon=folium.Icon(color=category_colors[row["Category"]])
        ).add_to(cluster)

    st_folium(m, use_container_width=True, height=700)

def dashboard():
    nav()
    st.markdown("<h2>Dashboard</h2>", unsafe_allow_html=True)
    dist = df.groupby("District").size().reset_index(name="Count")

    month_order = ["January","February","March","April","May","June","July","August","September","October","November","December"]
    mon = df["Best_Month"].value_counts().reindex(month_order).fillna(0).reset_index()
    mon.columns = ["Best_Month", "Count"]

    st.plotly_chart(
        px.bar(dist, x="District", y="Count", title="District Wise Tourism Places").update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white'
        ),
        use_container_width=True
    )
    
    st.plotly_chart(
        px.pie(mon, names="Best_Month", values="Count", title="Best Travel Months").update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white'
        ),
        use_container_width=True
    )

def admin_panel():
    nav()
    st.markdown("""
    <div style='padding:30px; border-radius:25px; background:linear-gradient(135deg, rgba(17, 50, 36, 0.6), rgba(15, 45, 74, 0.6)); border: 2px solid var(--accent-sandstone); margin-bottom:30px; color:white; box-shadow:0 10px 40px rgba(0,0,0,0.4); text-align: center;'>
        <h1 style='font-size:45px; color: var(--accent-gold) !important;'>🔐 Admin Dashboard</h1>
        <p style='font-size:18px; color: var(--text-cream); margin: 0;'>Manage users, favorites, and tourism analytics</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.get("admin_logged", False):
        st.markdown("<h2>Admin Authentication Required</h2>", unsafe_allow_html=True)
        admin_user = st.text_input("Admin Username", key="admin_user_input")
        admin_pass = st.text_input("Admin Password", type="password", key="admin_pass_input")

        if st.button("Login as Admin"):
            if admin_user == ADMIN_USER and admin_pass == ADMIN_PASS:
                st.session_state.admin_logged = True
                st.success("Admin Login Successful!")
                st.rerun()
            else:
                st.error("Invalid Admin Credentials")
        return

    st.success("🔒 Authenticated as Administrator")
    if st.button("🔒 Lock Admin Panel", use_container_width=False):
        st.session_state.admin_logged = False
        st.rerun()

    st.markdown("---")
    st.subheader("👥 Registered User Profiles")
    try:
        users_resp = supabase.table("users").select("*").execute()
        if users_resp.data:
            users_df = pd.DataFrame(users_resp.data)
            st.dataframe(users_df, use_container_width=True)
        else:
            st.info("No registered records inside your public 'users' tracking table yet.")
    except Exception as e:
        st.error(f"Failed to load user records from database: {e}")

    st.subheader("⭐ Favorites Data Records")
    try:
        favs_resp = supabase.table("favorites").select("*").execute()
        if favs_resp.data:
            st.dataframe(pd.DataFrame(favs_resp.data), use_container_width=True)
        else:
            st.info("No saved records currently exist inside table 'favorites'.")
    except Exception as e:
        st.error(f"Database Query Error (favorites): {e}")
        
    st.subheader("💬 Community Ratings & Feedback Logs")
    try:
        reviews_resp = supabase.table("reviews").select("*").order("created_at", desc=True).execute()
        
        if reviews_resp.data:
            reviews_df = pd.DataFrame(reviews_resp.data)
            if not reviews_df.empty and "created_at" in reviews_df.columns:
                reviews_df["created_at"] = pd.to_datetime(reviews_df["created_at"]).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(reviews_df, use_container_width=True)
        else:
            st.info("No reviews or feedback have been submitted by your users yet.")
    except Exception as e:
        st.error(f"Failed to load user reviews from database: {e}")

    st.subheader("📣 User-Submitted Platform Reviews & New Place Suggestions")
    try:
        sug_resp = supabase.table("platform_suggestions").select("*").order("created_at", desc=True).execute()
        if sug_resp.data:
            st.dataframe(pd.DataFrame(sug_resp.data), use_container_width=True)
        else:
            st.info("No system addition recommendations or platform rating logs recorded yet.")
    except Exception as e:
        st.error(f"Failed to query suggestion system tables: {e}")
    
district_hq = {
    "Bagalkot": [16.1813, 75.6967],
    "Ballari": [15.1394, 76.9214],
    "Belagavi": [15.8497, 74.4977],
    "Bengaluru Rural": [13.2118, 77.7126],
    "Bengaluru Urban": [12.9716, 77.5946],
    "Bidar": [17.9120, 77.5188],
    "Chamarajanagar": [11.9261, 76.9437],
    "Chikkaballapur": [13.4325, 77.7275],
    "Chikkamagaluru": [13.3161, 75.7720],
    "Chitradurga": [14.2251, 76.3996],
    "Dakshina Kannada": [12.8703, 74.8826],
    "Davanagere": [14.4644, 75.9218],
    "Dharwad": [15.4589, 75.0078],
    "Gadag": [15.4277, 75.6310],
    "Hassan": [13.0063, 76.1026],
    "Haveri": [14.7957, 75.4014],
    "Kalaburagi": [17.3291, 76.8343],
    "Kodagu": [12.4244, 75.7382],
    "Kolar": [13.1367, 78.1292],
    "Koppal": [15.3466, 76.1554],
    "Mandya": [12.5218, 76.8951],
    "Mysuru": [12.2958, 76.6394],
    "Raichur": [16.2120, 77.3556],
    "Ramanagara": [12.7153, 77.2813],
    "Shivamogga": [13.9299, 75.5681],
    "Tumakuru": [13.3392, 77.1140],
    "Udupi": [13.3409, 74.7421],
    "Uttara Kannada": [14.8095, 74.6111],
    "Vijayapura": [16.8302, 75.7100],
    "Yadgir": [16.7686, 77.1377]
}

def calculate_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    km = 6371 * c
    return km

def optimize_district_route(start_district, destination_districts):
    route = []
    remaining = destination_districts.copy()
    current = start_district
    while remaining:
        current_row = df[df["District"] == current].iloc[0]
        nearest = None
        min_dist = float("inf")
        for district in remaining:
            target_row = df[df["District"] == district].iloc[0]
            dist = calculate_distance(current_row["Latitude"], current_row["Longitude"], target_row["Latitude"], target_row["Longitude"])
            if dist < min_dist:
                min_dist = dist
                nearest = district
        route.append(nearest)
        remaining.remove(nearest)
        current = nearest
    return route

def sort_places_by_distance(district_places):
    if len(district_places) <= 1:
        return district_places
    ordered = []
    remaining = district_places.copy()
    current = remaining.iloc[0]
    ordered.append(current)
    remaining = remaining.iloc[1:]
    while len(remaining):
        nearest_idx = None
        nearest_dist = float("inf")
        for idx, row in remaining.iterrows():
            dist = calculate_distance(current["Latitude"], current["Longitude"], row["Latitude"], row["Longitude"])
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_idx = idx
        current = remaining.loc[nearest_idx]
        ordered.append(current)
        remaining = remaining.drop(nearest_idx)
    return pd.DataFrame(ordered)

def trip_generator():
    nav()
    st.markdown("""
    <div style='padding:30px; border-radius:25px; background:linear-gradient(135deg, rgba(17, 50, 36, 0.6), rgba(15, 45, 74, 0.6)); border: 2px solid var(--accent-sandstone); margin-bottom:30px; color:white; box-shadow:0 10px 40px rgba(0,0,0,0.4); text-align: center;'>
        <h1 style="font-size:45px; color: var(--accent-gold) !important; font-weight: 800; margin-bottom: 5px;">🚗 Smart Trip Planner</h1>
        <p style="color: #cbd5e1; font-size: 16px; margin-top: 0px;">Generate Road Trips & Estimate Budgets</p>
    </div>
    """, unsafe_allow_html=True)

    districts = sorted(df["District"].unique())

    # --- ROW 1: CORE LOCATIONS ---
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        start_city = st.selectbox("📍 Starting District", districts)
    with row1_col2:
        destination_districts = st.multiselect("🎯 Destination Districts", [d for d in districts if d != start_city])

    # --- ROW 2: PARAMETERS ---
    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        days = st.slider("Trip Duration (Days)", 1, 10, 3)
    with row2_col2:
        travelers = st.number_input("Travelers", min_value=1, max_value=20, value=2)
        
    places_per_day = st.slider("Places Per Day", 1, 5, 3)
    hotel_type = st.selectbox("🏨 Hotel Type", ["Budget (₹1000/day)", "Standard (₹2500/day)", "Luxury (₹5000/day)"])
    travel_mode = st.selectbox("🛣 Travel Mode", ["Own Bike", "Own Car", "Rental Bike", "Rental Car", "Public Transport"])
    
    vehicle_type = None
    driver_type = None
    if travel_mode in ["Own Car", "Rental Car"]:
        vehicle_type = st.selectbox("🚗 Vehicle Type", ["4+1 Seater", "6+1 Seater"])
        driver_type = st.selectbox("👨 Driver", ["Self Drive", "With Driver"])
    
    trip_type = st.selectbox("🎯 Trip Type", ["Mixed", "Family", "Adventure", "Pilgrimage", "Nature", "Beach", "Trekking", "Wildlife"])
    
    public_type = None
    if travel_mode == "Public Transport":
        public_type = st.selectbox("Public Transport Type", ["KSRTC Bus", "Train"])
    
    if st.button("✨ Generate Trip", use_container_width=True):
        if not destination_districts:
            st.warning("Please select destination districts")
            st.stop()
            
        route = optimize_district_route(start_city, destination_districts)
        st.success(f"📍 Start: {start_city}\n\n🚗 Route: " + " ➜ ".join(route))

        total_places = days * places_per_day
        trip_places = []

        if trip_type == "Family": priority_keywords = "Pilgrimage|Temple|Beach|Waterfall|Heritage|Palace|Fort"
        elif trip_type == "Adventure": priority_keywords = "Adventure|Waterfall|Hill|Trek"
        elif trip_type == "Pilgrimage": priority_keywords = "Temple|Pilgrimage|Religious|Historical"
        elif trip_type == "Nature": priority_keywords = "Waterfall|Lake|Hill|Garden"
        elif trip_type == "Beach": priority_keywords = "Beach|Island|Coast"
        elif trip_type == "Trekking": priority_keywords = "Trek|Hill|Peak|Mountain"
        elif trip_type == "Wildlife": priority_keywords = "Wildlife|Sanctuary|National Park|Forest|Zoo"
        else: priority_keywords = ""

        places_per_district = max(1, total_places // len(route))

        for district in route:
            district_places = df[df["District"] == district].copy()
            if district_places.empty:
                continue

            if priority_keywords:
                priority = district_places[district_places["Category"].str.contains(priority_keywords, case=False, na=False)]
                others = district_places.drop(priority.index)
                priority = sort_places_by_distance(priority)
                others = sort_places_by_distance(others)
                district_places = pd.concat([priority, others])
            else:
                district_places = sort_places_by_distance(district_places)

            district_places = district_places.head(places_per_district)
            trip_places.extend(district_places.to_dict("records"))

        trip_places = trip_places[:total_places]
        
        if len(trip_places) < total_places:
            remaining = total_places - len(trip_places)
            extra_places = df[(df["District"].isin(route)) & (~df["Place"].isin([p["Place"] for p in trip_places]))]
            extra_places = sort_places_by_distance(extra_places)
            trip_places.extend(extra_places.head(remaining).to_dict("records"))
        
        trip_distance = 0
        route_points = []
        start_lat, start_lon = district_hq[start_city]
        route_points.append({"Place": start_city + " HQ", "Latitude": start_lat, "Longitude": start_lon})

        for p in trip_places:
            route_points.append({"Place": p["Place"], "Latitude": p["Latitude"], "Longitude": p["Longitude"]})
        route_points.append({"Place": start_city + " HQ", "Latitude": start_lat, "Longitude": start_lon})
        
        for i in range(len(route_points)-1):
            p1 = route_points[i]
            p2 = route_points[i+1]
            dist = calculate_distance(p1["Latitude"], p1["Longitude"], p2["Latitude"], p2["Longitude"])
            trip_distance += dist * 1.30

        if not trip_places:
            st.error("No places found for selected route")
            st.stop()

        st.success(f"🛣 Complete Trip Distance: {trip_distance:.1f} km")    
        st.markdown("<h2>🚗 Complete Route</h2>", unsafe_allow_html=True)
        st.write(f"🏠 {start_city} HQ")

        for i in range(len(trip_places)):
            if i == 0:
                dist = calculate_distance(start_lat, start_lon, trip_places[i]["Latitude"], trip_places[i]["Longitude"]) * 1.30
            else:
                dist = calculate_distance(trip_places[i-1]["Latitude"], trip_places[i-1]["Longitude"], trip_places[i]["Latitude"], trip_places[i]["Longitude"]) * 1.30
            st.write(f"➡️ {trip_places[i]['Place']} ({trip_places[i]['District']}) - {dist:.1f} km")

        last_dist = calculate_distance(trip_places[-1]["Latitude"], trip_places[-1]["Longitude"], start_lat, start_lon) * 1.30
        st.write(f"🏠 Return to {start_city} HQ - {last_dist:.1f} km")
        st.markdown("<h2>🗺 Smart Road Trip Plan</h2>", unsafe_allow_html=True)

        cols_per_row = 3
        for day in range(days):
            st.markdown(f'<div style="padding:15px; border-radius:18px; background:linear-gradient(135deg, rgba(17, 50, 36, 0.4), rgba(15, 45, 74, 0.4)); border: 2px solid var(--accent-sandstone); color:white; margin-top:20px; margin-bottom:15px; text-align:center; font-size:22px; font-weight:800; text-transform: uppercase; letter-spacing: 1.5px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);">📅 Day {day+1}</div>', unsafe_allow_html=True)
            start = day * places_per_day
            end = start + places_per_day
            today_places = trip_places[start:end]

            for i in range(0, len(today_places), cols_per_row):
                row_places = today_places[i:i + cols_per_row]
                cols = st.columns(cols_per_row)
                for col, place in zip(cols, row_places):
                    with col:
                        img_url = str(place["Image"]).strip() if pd.notna(place["Image"]) else DEFAULT_IMAGE
                        with st.container(border=True):
                            st.markdown(f"""
                                <img src="{img_url}" 
                                     class="zoom-img" 
                                     style="width:100%; height:260px; object-fit:cover; border-radius:15px;" 
                                     onerror="this.onerror=null; this.src='{DEFAULT_IMAGE}';">
                                """, unsafe_allow_html=True)
                            st.markdown(f'<h3 style="text-align:center;color:white;font-size:22px !important;margin-top:12px !important;">{place["Place"]}</h3><p style="text-align:center;margin-bottom:4px;"><strong>📍 District:</strong> {place["District"]}</p><p style="text-align:center;font-size:14px;margin:0;"><strong>Category:</strong> {place["Category"]}</p>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("<h2>💰 Trip Cost Estimator</h2>", unsafe_allow_html=True)

        hotel_rate = 1000 if "Budget" in hotel_type else (2500 if "Standard" in hotel_type else 5000)
        hotel_cost = days * hotel_rate
        food_cost = days * travelers * 500

        if travel_mode == "Own Bike":
            bikes_required = max(1, (travelers + 1) // 2)
            transport_cost = int(trip_distance * 3 * bikes_required)
        elif travel_mode == "Own Car":
            capacity = (5 if vehicle_type == "4+1 Seater" else 7) if driver_type == "Self Drive" else (4 if vehicle_type == "4+1 Seater" else 6)
            cars_required = max(1, (travelers + capacity - 1) // capacity)
            transport_cost = int(trip_distance * 6.5 * cars_required)
        elif travel_mode == "Rental Bike":
            bikes_required = max(1, (travelers + 1) // 2)
            transport_cost = int((days * 500 * bikes_required) + (trip_distance * 3 * bikes_required))
        elif travel_mode == "Rental Car":
            capacity = (5 if vehicle_type == "4+1 Seater" else 7) if driver_type == "Self Drive" else (4 if vehicle_type == "4+1 Seater" else 6)
            rental_per_day = 2000 if vehicle_type == "4+1 Seater" else 3000
            cars_required = max(1, (travelers + capacity - 1) // capacity)
            transport_cost = int((days * rental_per_day * cars_required) + (trip_distance * 6.5 * cars_required))
        else:
            transport_cost = int(trip_distance * 1.5 * travelers)

        total_cost = hotel_cost + food_cost + transport_cost
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #113224, #0f2d4a) !important; border: 2px solid #dfc59f; border-radius: 16px; padding: 15px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                <p style="color: #dfc59f; margin: 0; font-size: 14px; font-weight: 700; text-transform: uppercase;">🏨 Hotel</p>
                <h2 style="color: #f5b025 !important; margin: 5px 0 0 0; font-size: 28px; font-weight: 800; text-shadow: none !important;">₹{hotel_cost:,}</h2>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #113224, #0f2d4a) !important; border: 2px solid #dfc59f; border-radius: 16px; padding: 15px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                <p style="color: #dfc59f; margin: 0; font-size: 14px; font-weight: 700; text-transform: uppercase;">🍽 Food</p>
                <h2 style="color: #f5b025 !important; margin: 5px 0 0 0; font-size: 28px; font-weight: 800; text-shadow: none !important;">₹{food_cost:,}</h2>
            </div>
            """, unsafe_allow_html=True)
            
        with c3:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #113224, #0f2d4a) !important; border: 2px solid #dfc59f; border-radius: 16px; padding: 15px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                <p style="color: #dfc59f; margin: 0; font-size: 14px; font-weight: 700; text-transform: uppercase;">🚗 Transport</p>
                <h2 style="color: #f5b025 !important; margin: 5px 0 0 0; font-size: 28px; font-weight: 800; text-shadow: none !important;">₹{transport_cost:,}</h2>
            </div>
            """, unsafe_allow_html=True)
            
        with c4:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #113224, #0f2d4a) !important; border: 2px solid #dfc59f; border-radius: 16px; padding: 15px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                <p style="color: #dfc59f; margin: 0; font-size: 14px; font-weight: 700; text-transform: uppercase;">💵 Total</p>
                <h2 style="color: #f5b025 !important; margin: 5px 0 0 0; font-size: 28px; font-weight: 800; text-shadow: none !important;">₹{total_cost:,}</h2>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.success(f"Estimated Budget Required: ₹{total_cost:,}")

        user_summary_places = [p["Place"] for p in trip_places]
        st.markdown("<h2>📋 Trip Summary</h2>", unsafe_allow_html=True)
        
        summary_html = f"""
        <div style="background-color: linear-gradient(135deg, #113224, #0f2d4a) !important; border: 2px solid #dfc59f; border-radius: 16px; padding: 20px; box-shadow: 0px 10px 25px rgba(0,0,0,0.4); margin-bottom: 25px;">
            <div style="font-family: 'Poppins', monospace; font-size: 16px; font-weight: 600; line-height: 1.8; color: #f5e6d3 !important;">
                <div>Starting District : {start_city}</div>
                <div>Trip Duration     : {days} Days</div>
                <div>Travelers         : {travelers}</div>
                <div>Travel Mode       : {travel_mode}</div>
                <div>Places Covered    : {len(user_summary_places)}</div>
                <div style="margin-top: 5px; color: #f5b025 !important;">Estimated Budget  : ₹{total_cost:,}</div>
            </div>
        </div>
        """
        st.markdown(summary_html, unsafe_allow_html=True)

# =========================================================================
# APPLICATION ROUTING MATRICES (CLEAN & FIXED)
# =========================================================================
if st.session_state.get("show_intro", True):
    intro_screen()
    st.stop()   

# 1. Execute runtime cookie verification step before rendering anything
try_cookie_signin()

# 2. Enforce Login boundary if still unauthenticated
if not st.session_state.logged_in and st.session_state.page not in ["login", "signup", "forgot", "reset"]:
    st.session_state.page = "login"

# 3. Master Page Renderer Switch
if st.session_state.page == "login":
    login()
    show_branding()
elif st.session_state.page == "signup":
    signup()
    show_branding()
elif st.session_state.page == "forgot":
    forgot()
    show_branding()
elif st.session_state.page == "reset":
    reset_password()
    show_branding()
elif st.session_state.page == "home":
    home()   
elif st.session_state.page == "trip":
    trip_generator()
elif st.session_state.page == "fav":
    favorites()
    show_branding()
elif st.session_state.page == "dash":
    dashboard()
    show_branding()
elif st.session_state.page == "map":
    tourism_map()
    show_branding()
elif st.session_state.page == "admin":
    admin_panel()
    show_branding()
elif st.session_state.page == "review_suggestion":
    user_suggestion_panel()
    show_branding()
