import React, { useMemo, useState } from "react";

const INTENTS = [
  {
    keywords: ["why", "flag", "flagged", "risk", "risky"],
    response:
      "This transaction shows unusual amount, device shift, or graph connections. The model combines anomaly, supervised, and graph risk to flag it."
  },
  {
    keywords: ["anomaly", "anomaly detection"],
    response:
      "Anomaly detection spots behavior that deviates from your historical patterns, like sudden high amounts or rapid transfers."
  },
  {
    keywords: ["reduce", "prevent", "fraud"],
    response:
      "Enable strong authentication, verify beneficiaries, limit transfer velocity, and monitor device/location changes."
  },
  {
    keywords: ["graph", "network"],
    response:
      "Graph analysis finds circular transfers, suspicious clusters, and high-centrality nodes that indicate mule networks."
  }
];

function getResponse(message, lastExplanation) {
  const lower = message.toLowerCase();
  const match = INTENTS.find((intent) => intent.keywords.some((word) => lower.includes(word)));
  const isFlagQuery = ["why", "flag", "flagged", "risk", "risky"].some((word) => lower.includes(word));
  if (match && isFlagQuery) {
    if (lastExplanation) {
      return `${match.response} Latest model note: ${lastExplanation}`;
    }
    return `${match.response} Score a transaction to get a live explanation.`;
  }
  if (match) return match.response;
  return "I can explain risk scores, anomaly detection, graph fraud, or prevention tips. Try asking 'Why flagged?'";
}

export default function AIAssistant() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    { role: "assistant", text: "Hi! I am SecurePay AI Assistant. Ask me about fraud scores or prevention." }
  ]);

  const handleSend = () => {
    if (!input.trim()) return;
    const userMessage = { role: "user", text: input.trim() };
    const lastExplanation = localStorage.getItem("securepay_last_explanation");
    const reply = { role: "assistant", text: getResponse(input, lastExplanation) };
    setMessages((prev) => [...prev, userMessage, reply]);
    setInput("");
  };

  const transcript = useMemo(() => messages.slice(-8), [messages]);

  return (
    <>
      {open && (
        <div className="card chat-panel p-4 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm font-semibold">AI Assistant</p>
              <p className="text-xs text-muted">Fraud explanations & tips</p>
            </div>
            <button className="btn-outline" onClick={() => setOpen(false)}>
              Close
            </button>
          </div>
          <div className="flex-1 overflow-y-auto space-y-3 text-sm">
            {transcript.map((msg, index) => (
              <div
                key={index}
                className={`p-3 rounded-xl ${
                  msg.role === "assistant" ? "bg-slate-100" : "bg-indigo-500 text-white"
                }`}
              >
                {msg.text}
              </div>
            ))}
          </div>
          <div className="mt-3 flex gap-2">
            <input
              className="flex-1 border rounded-xl px-3 py-2 text-sm"
              placeholder="Ask about fraud risk..."
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && handleSend()}
            />
            <button className="btn-primary" onClick={handleSend}>
              Send
            </button>
          </div>
        </div>
      )}
      <button className="btn-primary floating-btn" onClick={() => setOpen((prev) => !prev)}>
        {open ? "Hide" : "AI Assistant"}
      </button>
    </>
  );
}
