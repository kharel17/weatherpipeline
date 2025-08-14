import { app } from "./firebase-config.js";
import {
  getFirestore,
  collection,
  query,
  orderBy,
  limit,
  onSnapshot,
} from "https://www.gstatic.com/firebasejs/10.13.1/firebase-firestore.js";

const db = getFirestore(app);

// Listen for latest weather data (limit to 1, newest first)
const q = query(
  collection(db, "weather_data"),
  orderBy("time", "desc"),
  limit(1)
);

onSnapshot(q, (snapshot) => {
  snapshot.forEach((doc) => {
    const data = doc.data();
    document.getElementById("city").textContent = data.city;
    document.getElementById("temperature").textContent = data.temp + "°C";
    document.getElementById("humidity").textContent = data.humidity + "%";
    document.getElementById("time").textContent = new Date(
      data.time
    ).toLocaleString();
  });
});
