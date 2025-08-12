# ... (other imports)
import os
import sys
import codecs
import sys
import logging
import requests
from datetime import datetime, timedelta, UTC
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for

if sys.platform == "win32":
    if hasattr(sys.stdout, 'detach'):
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    if hasattr(sys.stderr, 'detach'):
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
        
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from models.database import init_database, WeatherRecord, get_database_stats
    from etl.pipeline import WeatherETLPipeline
    from models.forecast import ForecastManager, quick_forecast, STATSMODELS_AVAILABLE
    from utils.helpers import validate_coordinates, get_location_name, categorize_air_quality
    from models.user import User
except ImportError as e:
    print(f"Import error: {e}")
    print("Please make sure you're running from the project root directory")
    print("Or install the modules: pip install -e .")
    sys.exit(1)

from flask_dance.contrib.google import make_google_blueprint, google

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'weather-insight-dev-key-2025')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///data/weather_data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Google OAuth config (replace with your credentials)
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

google_bp = make_google_blueprint(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    scope=["profile", "email"],
    redirect_url="/login/google/authorized"
)
app.register_blueprint(google_bp, url_prefix="/login")

# Initialize database
init_database(app.config['SQLALCHEMY_DATABASE_URI'])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_LOCATIONS = {
    'kathmandu': {'lat': 27.7, 'lon': 85.3, 'name': 'Kathmandu, Nepal'},
    'new_york': {'lat': 40.71, 'lon': -74.01, 'name': 'New York, USA'},
    'london': {'lat': 51.51, 'lon': -0.13, 'name': 'London, UK'},
    'tokyo': {'lat': 35.69, 'lon': 139.69, 'name': 'Tokyo, Japan'},
    'sydney': {'lat': -33.87, 'lon': 151.21, 'name': 'Sydney, Australia'}
}

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/login/google/authorized")
def google_authorized():
    if not google.authorized:
        flash("Google login failed.", "error")
        return redirect(url_for("login"))
    resp = google.get("/oauth2/v2/userinfo")
    if resp.ok:
        info = resp.json()
        from models.database import db_session
        user = db_session.query(User).filter_by(email=info["email"]).first()
        if not user:
            user = User(
                email=info["email"],
                name=info.get("name"),
                profile_pic=info.get("picture"),
                google_id=info.get("id"),
            )
            db_session.add(user)
            db_session.commit()
        session["user_id"] = user.id
        session["user_name"] = user.name
        session["user_email"] = user.email
        session["profile_pic"] = user.profile_pic
        flash("Logged in successfully!", "success")
        return redirect(url_for("index"))
    flash("Failed to fetch user info from Google.", "error")
    return redirect(url_for("login"))

# ... rest of your existing routes ...