import { getFirestore, collection, getDocs } 
  from "https://www.gstatic.com/firebasejs/10.13.1/firebase-firestore.js";
import { app } from "./firebase-config.js";

const db = getFirestore(app);

// Fetch all weather data
async function fetchWeather() {
  const querySnapshot = await getDocs(collection(db, "weather_data"));
  querySnapshot.forEach(doc => {
    console.log(doc.id, " => ", doc.data());
  });
}

fetchWeather();
