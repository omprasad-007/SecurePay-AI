import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "../utils/firebase";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    try {
      await signInWithEmailAndPassword(auth, email, password);
      navigate("/");
    } catch (err) {
      setError(err.message || "Login failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="card p-8 w-full max-w-md">
        <h1 className="text-2xl font-semibold mb-2">SecurePay AI Login</h1>
        <p className="text-sm text-muted mb-6">Access the fraud monitoring console.</p>
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
            Login
          </button>
        </form>
        <p className="text-sm text-muted mt-4">
          New here? <Link className="text-indigo-500" to="/signup">Create an account</Link>
        </p>
        <p className="text-sm text-muted mt-2">
          Enterprise workspace? <Link className="text-indigo-500" to="/enterprise/login">Login here</Link>
        </p>
      </div>
    </div>
  );
}
