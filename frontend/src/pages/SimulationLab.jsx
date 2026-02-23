import React, { useState } from "react";
import { apiFetch } from "../utils/api";
import { createTransaction } from "../utils/fraudUtils";
import { getDeviceFingerprint } from "../utils/deviceFingerprint";
import RiskBreakdownPanel from "../components/RiskBreakdownPanel.jsx";

const attacks = ["Account Takeover", "Bot Attack", "Money Mule Ring", "Velocity Attack"];

function attackConfig(type, amount) {
  if (type === "Account Takeover") return { multiplier: 1.3, receiverId: "RISKY001" };
  if (type === "Bot Attack") return { multiplier: 0.7, receiverId: "MERCH7" };
  if (type === "Money Mule Ring") return { multiplier: 1.4, receiverId: "MERCH99" };
  return { multiplier: 1.2, receiverId: "MERCH5" };
}

export default function SimulationLab() {
  const [attack, setAttack] = useState(attacks[0]);
  const [amount, setAmount] = useState(4000);
  const [deviceId, setDeviceId] = useState("LAB-DEVICE-1");
  const [timestamp, setTimestamp] = useState(new Date().toISOString().slice(0, 16));
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const runSimulation = async () => {
    setError("");
    const config = attackConfig(attack, amount);
    const fingerprint = await getDeviceFingerprint();
    const simulated = createTransaction({
      amount: Number(amount) * config.multiplier,
      receiverId: config.receiverId,
      deviceId,
      timestamp: new Date(timestamp).toISOString(),
      merchant: attack
    });

    try {
      const response = await apiFetch("/predict", {
        method: "POST",
        body: JSON.stringify({
          transaction: {
            ...simulated,
            deviceFingerprint: fingerprint.fingerprint
          },
          history: [],
          device_context: { ipRisk: fingerprint.ipRisk }
        })
      });
      setResult(response);
    } catch (err) {
      setError(err.message || "Simulation failed");
    }
  };

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-4">Transaction Simulation Lab</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="text-sm text-muted">Attack Type</label>
            <select className="w-full border rounded-xl px-4 py-3" value={attack} onChange={(e) => setAttack(e.target.value)}>
              {attacks.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm text-muted">Amount</label>
            <input className="w-full border rounded-xl px-4 py-3" type="range" min="100" max="25000" value={amount} onChange={(e) => setAmount(e.target.value)} />
            <div className="text-sm mt-1">₹{Number(amount).toLocaleString()}</div>
          </div>
          <div>
            <label className="text-sm text-muted">Time Override</label>
            <input className="w-full border rounded-xl px-4 py-3" type="datetime-local" value={timestamp} onChange={(e) => setTimestamp(e.target.value)} />
          </div>
          <div>
            <label className="text-sm text-muted">Device Override</label>
            <input className="w-full border rounded-xl px-4 py-3" value={deviceId} onChange={(e) => setDeviceId(e.target.value)} />
          </div>
        </div>
        <button className="btn-primary mt-4" onClick={runSimulation}>Run Simulation</button>
        {error && <p className="text-sm text-red-500 mt-3">{error}</p>}
      </div>

      {result && (
        <RiskBreakdownPanel
          adaptiveScore={result.adaptive_score}
          adaptiveRiskLevel={result.adaptive_risk_level}
          decisionAction={result.decision_action}
          riskDrivers={result.risk_drivers || []}
        />
      )}
    </div>
  );
}
