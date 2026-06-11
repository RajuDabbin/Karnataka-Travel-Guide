# 🌍 Karnataka Travel Guide & Smart Route Planner

An interactive, premium-themed full-stack travel assistant application designed to help explorers seamlessly navigate and plan journeys through Karnataka. Built with a responsive, sunlit-gold and tea-estate green aesthetic, the application scales dynamically across both desktop and mobile viewports.

Live Link: `https://your-app-name.streamlit.app`

---

## 🚀 Core Features

* **Smart Trip Generator:** Leverages coordinate mathematics to optimize driving routes across multiple user-selected destination districts, minimizing unnecessary back-and-forth travel distance.
* **Granular Cost Estimator Matrix:** Generates precise trip budget predictions covering accommodation tiers (Budget, Standard, Luxury), personalized food logs, and multiple transit modes (Own/Rental Bike, Own/Rental Car with driver parameters, or Public KSRTC lines).
* **Secure Authentication & Session Memory:** Integrated with a Supabase PostgreSQL backend and a client-side browser cookie management system to gracefully keep users logged in across application refreshes.
* **Interactive Tourism Map:** Powered by `streamlit-folium` and Marker Clusters to display regional attractions with color-coded category pins, responsive informational popups, and quick-launch directions mapping to Google Maps.
* **Community Feedback Portal:** Features a full review logging network allowing authenticated users to post star ratings, drop detailed trip notes, and suggest missing destinations straight to the administrator panel.
* **Comprehensive Admin Dashboard:** A secure, credentials-guarded dashboard view built exclusively for tracking registered user profiles, platform suggestion inputs, and system analytical metrics.

---

## 🛠️ Technology Stack

* **Frontend Framework:** [Streamlit](https://streamlit.io/) (with custom CSS responsive viewport overrides)
* **Session & State Extension:** `extra-streamlit-components` (Browser Cookie Handshaking)
* **Backend Database & Auth Engine:** [Supabase](https://supabase.com/) (PostgreSQL & GoTrue Auth)
* **Mapping Components:** Folium, Streamlit-Folium, OpenStreetMap (OSRM Data API)
* **AI Engine:** Google Gemini Pro (`google-genai` package for automated custom travel itineraries)
* **Analytics Rendering:** Plotly Express

---

## 📁 Repository Structure

```text
📁 KARNATAKA TRAVEL GUIDE/
│
├── 📁 .streamlit/
│   └── 📄 config.toml       # Custom performance and privacy UI configurations
│
├── 📁 static/
│   ├── 📄 cover.jpg         # Application entry cinematic assets
│   └── 📄 entry_banner.jpg  # Core visual identity banners
│
├── 📄 app.py                # Main Streamlit execution script & application router
├── 📄 requirements.txt      # Server pip package dependencies matrix
├── 📄 README.md             # Project documentation manual
└── 📄 karnataka_places_with_coordinates.csv  # Tourism location coordinates dataset
