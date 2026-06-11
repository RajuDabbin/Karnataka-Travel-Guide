Karnataka Travel Guide

An AI-powered tourism recommendation and travel planning web application built using **Streamlit**, **Python**, **SQLite**, and **Google Gemini AI**.

The platform helps users discover tourist places across Karnataka with smart recommendations, travel planning, favorites management, analytics dashboards, and AI-generated itineraries.

---

Features

User Authentication

* User Signup & Login
* Secure Password Hashing
* Forgot Password with Email OTP Verification

---

Tourism Recommendation System

* Explore 300+ Karnataka tourist places
* Filter by:

  * District
  * Category
  * Best Travel Month
* Beautiful modern UI with responsive design

---

Favorites System

* Add places to favorites
* Personalized favorite collection
* Dynamic UI highlighting for saved places

---

AI Travel Planner

Generate personalized travel itineraries using **Google Gemini AI**.

Example:

* 3-Day Mysore Trip Plan
* Coorg Nature Tour
* Adventure Travel Planning

---

Analytics Dashboard

Interactive tourism analytics using Plotly:

* District-wise tourism places
* Best travel months visualization
* Modern chart dashboard

---

Admin Dashboard

Admin panel to:

* View registered users
* View favorites data
* Manage tourism insights

---

Technologies Used

* Python
* Streamlit
* SQLite
* Pandas
* Plotly
* Google Gemini AI
* HTML/CSS
* SMTP Email Service

---

Project Structure

```bash
Karnataka-Travel-Guide/
│
├── aiapp.py
├── tourism.db
├── karnataka_300_places.csv
├── requirements.txt
├── README.md
└── .streamlit/
    └── secrets.toml
```

---

Installation

Clone Repository

```bash
git clone https://github.com/yourusername/Karnataka-Travel-Guide.git
cd Karnataka-Travel-Guide
```

---

Create Virtual Environment

```bash
python -m venv venv
```

Activate environment:

### Windows

```bash
venv\Scripts\activate
```

### Linux / Mac

```bash
source venv/bin/activate
```

---

Install Dependencies

```bash
pip install -r requirements.txt
```

---

Configure Secrets

Create:

```bash
.streamlit/secrets.toml
```

Add:

```toml
GEMINI_API_KEY="your_gemini_api_key"
EMAIL_PASSWORD="your_email_app_password"
```

---Run Application

```bash
streamlit run aiapp.py
```

---

Deployment

This project can be deployed on:

* Streamlit Cloud
* Render
* Railway
* Hugging Face Spaces


Admin Credentials

```text
Username: admin_email
Password: admin_password
```

---

Developer

**Raju Dabbin**

---

Future Enhancements

* Hotel Booking Integration
* Weather Forecast API
* Nearby Restaurants
* AI Chatbot Assistant
* Live Navigation
* Multi-language Support

---


This project is developed for educational and portfolio purposes.
