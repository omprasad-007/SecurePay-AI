import React, { useMemo, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { getCurrentUser } from "../auth/sessionStore";
import { loginEnterprise } from "../services/authApi";

export default function EnterpriseLoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const existingUser = getCurrentUser();

  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [inviteToken, setInviteToken] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const redirectTo = useMemo(() => {
    const fromPath = location.state?.from?.pathname;
    if (typeof fromPath === "string" && fromPath.startsWith("/enterprise")) {
      return fromPath;
    }
    return "/enterprise/dashboard";
  }, [location.state]);

  if (existingUser) {
    return <Navigate to={redirectTo} replace />;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await loginEnterprise({
        email: email.trim(),
        fullName: fullName.trim() || null,
        organizationName: organizationName.trim() || null,
        inviteToken: inviteToken.trim() || null,
      });
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err.message || "Enterprise login failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="card p-8 w-full max-w-lg">
        <h1 className="text-2xl font-semibold mb-2">Enterprise Login</h1>
        <p className="text-sm text-muted mb-6">
          Sign in to the multi-tenant enterprise console. For first login, provide an organization name or invite token.
        </p>

        {error && <div className="text-sm text-red-500 mb-4">{error}</div>}

        <form className="space-y-4" onSubmit={handleSubmit}>
          <input
            className="w-full border rounded-xl px-4 py-3"
            type="email"
            placeholder="Work email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <input
            className="w-full border rounded-xl px-4 py-3"
            type="text"
            placeholder="Full name (optional)"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
          />
          <input
            className="w-full border rounded-xl px-4 py-3"
            type="text"
            placeholder="Organization name (required for first login)"
            value={organizationName}
            onChange={(event) => setOrganizationName(event.target.value)}
          />
          <input
            className="w-full border rounded-xl px-4 py-3"
            type="text"
            placeholder="Invite token (optional)"
            value={inviteToken}
            onChange={(event) => setInviteToken(event.target.value)}
          />
          <button className="btn-primary w-full" type="submit" disabled={submitting}>
            {submitting ? "Signing in..." : "Enter Enterprise Console"}
          </button>
        </form>

        <p className="text-sm text-muted mt-4">
          Need standard app login? <Link className="text-indigo-500" to="/login">Go to user login</Link>
        </p>
      </div>
    </div>
  );
}
