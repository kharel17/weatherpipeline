# Firebase configuration
import pyrebase

config = {
    "apiKey": "AIzaSyAnu26JMc-wAUdBg3dPGe4M-v0oWZsG_FA",
    "authDomain": "weather-app-2a7aa.firebaseapp.com",
    "databaseURL": "https://name-417c5-default-rtdb.asia-southeast1.firebasedatabase.app",
    "projectId": "weather-app-2a7aa",
    "storageBucket": "weather-app-2a7aa.firebasestorage.app",
    "messagingSenderId": "870604441409",
    "appId": "1:870604441409:web:e1b44107310dd4711403c0",
    "measurementId": "G-XM1D5MT6W5"
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()