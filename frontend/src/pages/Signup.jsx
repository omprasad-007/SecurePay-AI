import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createUserWithEmailAndPassword } from "firebase/auth";
import { auth } from "../utils/firebase";

export default function Signup() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    try {
      await createUserWithEmailAndPassword(auth, email, password);
      navigate("/");
    } catch (err) {
      setError(err.message || "Signup failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="card p-8 w-full max-w-md">
        <h1 className="text-2xl font-semibold mb-2">Create SecurePay AI Account</h1>
        <p className="text-sm text-muted mb-6">Enable fraud monitoring for your UPI system.</p>
        {error && <div className="text-sm text-red-500 mb-4">{error}</div>}
        <form className="space-y-4" onSubmit={handleSubmit}>
          <input
            className="w-full border rounded-xl px-4 py-3"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <input
            className="w-full border rounded-xl px-4 py-3"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          <button className="btn-primary w-full" type="submit">
            Sign Up
          </button>
        </form>
        <p className="text-sm text-muted mt-4">
          Already have an account? <Link className="text-indigo-500" to="/login">Login</Link>
        </p>
      </div>
    </div>
  );
}
