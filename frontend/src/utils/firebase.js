// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth } from "firebase/auth";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyAZc5gw2WaUco6nis1ewuIjox8jfoy1U3U",
  authDomain: "capstone-60578.firebaseapp.com",
  projectId: "capstone-60578",
  storageBucket: "capstone-60578.firebasestorage.app",
  messagingSenderId: "257412586558",
  appId: "1:257412586558:web:93530129dd7494a935856f",
  measurementId: "G-ED3WXZKJ3H"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// Initialize Analytics only in the browser
if (typeof window !== "undefined") {
  getAnalytics(app);
}
