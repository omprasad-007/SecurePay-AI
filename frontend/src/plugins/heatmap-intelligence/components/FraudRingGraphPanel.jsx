import React, { useMemo } from "react";

function nodeColor(type) {
  if (type === "cluster") return "#ef4444";
  if (type === "device") return "#22c55e";
  return "#3b82f6";
}

export default function FraudRingGraphPanel({ graph }) {
  const { nodes, edges } = graph || { nodes: [], edges: [] };

  const layout = useMemo(() => {
    const width = 760;
    const height = 280;
    const centerX = width / 2;
    const centerY = height / 2;
    const clusterNodes = nodes.filter((node) => node.type === "cluster");
    const otherNodes = nodes.filter((node) => node.type !== "cluster");

    const positioned = [];
    clusterNodes.forEach((node, index) => {
      const angle = (Math.PI * 2 * index) / Math.max(1, clusterNodes.length);
      positioned.push({
        ...node,
        x: centerX + Math.cos(angle) * 80,
        y: centerY + Math.sin(angle) * 80,
      });
    });

    otherNodes.forEach((node, index) => {
      const angle = (Math.PI * 2 * index) / Math.max(1, otherNodes.length);
      positioned.push({
        ...node,
        x: centerX + Math.cos(angle) * 130,
        y: centerY + Math.sin(angle) * 130,
      });
    });

    const byId = Object.fromEntries(positioned.map((node) => [node.id, node]));
    return { width, height, nodes: positioned, edges, byId };
  }, [edges, nodes]);

  return (
    <section className="hmi-panel">
      <h2 className="hmi-title">Fraud Ring Visualization</h2>
      <p className="hmi-subtitle">Graph links of suspicious accounts, shared devices, and detected fraud clusters.</p>
      {!nodes?.length && <p className="text-muted" style={{ marginTop: "0.75rem" }}>No fraud ring graph for selected filters.</p>}
      {!!nodes?.length && (
        <div style={{ marginTop: "0.8rem", overflowX: "auto" }}>
          <svg width={layout.width} height={layout.height} style={{ borderRadius: 12, background: "rgba(15,23,42,0.22)" }}>
            {layout.edges.map((edge, index) => {
              const source = layout.byId[edge.source];
              const target = layout.byId[edge.target];
              if (!source || !target) return null;
              return (
                <line
                  key={`${edge.source}-${edge.target}-${index}`}
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke="rgba(148,163,184,0.55)"
                  strokeWidth="1.2"
                />
              );
            })}
            {layout.nodes.map((node) => (
              <g key={node.id}>
                <circle cx={node.x} cy={node.y} r={node.type === "cluster" ? 9 : 6} fill={nodeColor(node.type)} />
                <text
                  x={node.x + 10}
                  y={node.y + 3}
                  fontSize="10"
                  fill="rgba(226,232,240,0.92)"
                  style={{ pointerEvents: "none" }}
                >
                  {node.id.replace(/^cluster:|^user:|^device:/, "")}
                </text>
              </g>
            ))}
          </svg>
        </div>
      )}
    </section>
  );
}
