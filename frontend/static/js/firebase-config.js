// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getFirestore } from "firebase/firestore";
//TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyAnu26JMc-wAUdBg3dPGe4M-v0oWZsG_FA",
  authDomain: "weather-app-2a7aa.firebaseapp.com",
  projectId: "weather-app-2a7aa",
  storageBucket: "weather-app-2a7aa.firebasestorage.app",
  messagingSenderId: "870604441409",
  appId: "1:870604441409:web:e1b44107310dd4711403c0",
  measurementId: "G-XM1D5MT6W5"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);