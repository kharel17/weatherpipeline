# Firebase configuration
import pyrebase

config = {
    "apiKey": "AIzaSyDjpOIgNm8P2pdOhJ1tJ2RMm_CDkHVrIGU",
    "authDomain": "name-417c5.firebaseapp.com",
    "databaseURL": "https://name-417c5-default-rtdb.asia-southeast1.firebasedatabase.app",
    "projectId": "name-417c5",
    "storageBucket": "name-417c5.firebasestorage.app",
    "messagingSenderId": "940303807138",
    "appId": "1:940303807138:web:69b88c3bfa525c74721dfb",
    "measurementId": "G-QRXLDN97PN"
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()