import React, { useEffect, useState } from "react";
import { getOrganization, updateFraudThreshold } from "../services/organizationApi";

export default function EnterpriseOrganizationPage() {
  const [organization, setOrganization] = useState(null);
  const [threshold, setThreshold] = useState(70);
  const [error, setError] = useState("");

  const loadOrganization = async () => {
    try {
      const data = await getOrganization();
      const org = Array.isArray(data) ? data[0] : data;
      setOrganization(org || null);
      setThreshold(Number(org?.fraud_threshold || 70));
    } catch (err) {
      setError(err.message || "Failed to load organization");
    }
  };

  useEffect(() => {
    loadOrganization();
  }, []);

  const saveThreshold = async () => {
    try {
      const updated = await updateFraudThreshold(threshold);
      setOrganization(updated);
      setThreshold(Number(updated.fraud_threshold || threshold));
      setError("");
    } catch (err) {
      setError(err.message || "Failed to update threshold");
    }
  };

  return (
    <div className="space-y-4">
      <div className="card p-6">
        <h2 className="text-xl font-semibold">Organization Settings</h2>
        {organization && (
          <div className="mt-3 text-sm text-muted">
            <p>Name: {organization.name}</p>
            <p>Slug: {organization.slug}</p>
          </div>
        )}
      </div>

      <div className="card p-6">
        <label className="text-sm text-muted">Fraud Threshold</label>
        <div className="flex gap-3 mt-2">
          <input
            type="number"
            min={0}
            max={100}
            className="border rounded-xl px-3 py-2"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
          />
          <button className="btn-primary" onClick={saveThreshold}>Save</button>
        </div>
      </div>

      {error && <div className="text-sm text-red-500">{error}</div>}
    </div>
  );
}
