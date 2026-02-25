import React, { useEffect, useState } from "react";
import { inviteUser, getUsers } from "../services/usersApi";

export default function EnterpriseAdminPanelPage() {
  const [users, setUsers] = useState([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("ANALYST");
  const [inviteToken, setInviteToken] = useState("");
  const [error, setError] = useState("");

  const refresh = async () => {
    try {
      const list = await getUsers();
      setUsers(list || []);
    } catch (err) {
      setError(err.message || "Failed to load users");
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const submitInvite = async () => {
    setError("");
    try {
      const response = await inviteUser({ email, role });
      setInviteToken(response.invite_token);
      setEmail("");
      await refresh();
    } catch (err) {
      setError(err.message || "Invite failed");
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Admin Panel</h2>
      <div className="card p-4 grid gap-3 md:grid-cols-3">
        <input className="border rounded-xl px-3 py-2" placeholder="member@email.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        <select className="border rounded-xl px-3 py-2" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="ORG_ADMIN">ORG_ADMIN</option>
          <option value="ANALYST">ANALYST</option>
          <option value="VIEWER">VIEWER</option>
        </select>
        <button className="btn-primary" onClick={submitInvite}>Invite User</button>
      </div>

      {inviteToken && <div className="card p-4 text-sm">Invite Token: <code>{inviteToken}</code></div>}
      {error && <div className="text-red-500 text-sm">{error}</div>}

      <div className="card p-4">
        <h3 className="font-semibold mb-3">Organization Members</h3>
        <ul className="space-y-2 text-sm">
          {users.map((user) => (
            <li key={user.id} className="flex items-center justify-between border-b border-slate-200/30 pb-2">
              <span>{user.email}</span>
              <span className="badge badge-medium">{user.role}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
