import React, { useMemo } from "react";

function forceLayout(nodes, links, width, height) {
  if (!nodes.length) return [];
  const centerX = width / 2;
  const centerY = height / 2;
  const positions = nodes.map((node, index) => ({
    ...node,
    x: centerX + Math.cos(index) * 90,
    y: centerY + Math.sin(index) * 70,
    vx: 0,
    vy: 0
  }));

  const nodeIndex = new Map(positions.map((node, idx) => [node.id, idx]));
  const iterations = 120;
  const repulsion = 2200;
  const linkDistance = 120;
  const linkStrength = 0.02;
  const centerForce = 0.01;
  const damping = 0.85;

  for (let iter = 0; iter < iterations; iter += 1) {
    for (let i = 0; i < positions.length; i += 1) {
      for (let j = i + 1; j < positions.length; j += 1) {
        const nodeA = positions[i];
        const nodeB = positions[j];
        const dx = nodeA.x - nodeB.x;
        const dy = nodeA.y - nodeB.y;
        const dist2 = dx * dx + dy * dy + 0.01;
        const force = repulsion / dist2;
        const fx = (dx / Math.sqrt(dist2)) * force;
        const fy = (dy / Math.sqrt(dist2)) * force;
        nodeA.vx += fx;
        nodeA.vy += fy;
        nodeB.vx -= fx;
        nodeB.vy -= fy;
      }
    }

    links.forEach((link) => {
      const sourceIndex = nodeIndex.get(link.source);
      const targetIndex = nodeIndex.get(link.target);
      if (sourceIndex == null || targetIndex == null) return;
      const source = positions[sourceIndex];
      const target = positions[targetIndex];
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const distance = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = (distance - linkDistance) * linkStrength;
      const fx = (dx / distance) * force;
      const fy = (dy / distance) * force;
      source.vx += fx;
      source.vy += fy;
      target.vx -= fx;
      target.vy -= fy;
    });

    positions.forEach((node) => {
      node.vx += (centerX - node.x) * centerForce;
      node.vy += (centerY - node.y) * centerForce;

      node.vx *= damping;
      node.vy *= damping;
      node.x += node.vx;
      node.y += node.vy;
    });
  }

  return positions.map(({ vx, vy, ...rest }) => rest);
}

export default function GraphView({ graph }) {
  const width = 360;
  const height = 280;

  const nodes = useMemo(
    () => forceLayout(graph?.nodes || [], graph?.links || [], width, height),
    [graph, width, height]
  );
  const links = graph?.links || [];

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Transaction Network</h3>
        <span className="text-sm text-muted">Graph-based fraud signals</span>
      </div>
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
        {links.map((link, index) => {
          const source = nodes.find((node) => node.id === link.source);
          const target = nodes.find((node) => node.id === link.target);
          if (!source || !target) return null;
          return (
            <line
              key={index}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke="rgba(148,163,184,0.5)"
              strokeWidth="1.2"
            />
          );
        })}
        {nodes.map((node) => (
          <g key={node.id}>
            <circle cx={node.x} cy={node.y} r="18" fill={node.flagged ? "#ef4444" : "#6366f1"} />
            <text x={node.x} y={node.y + 4} textAnchor="middle" fontSize="10" fill="#fff">
              {node.label}
            </text>
          </g>
        ))}
      </svg>
      <p className="text-xs text-muted mt-2">
        Force-directed layout shows suspicious clusters, cycles, and high-centrality entities.
      </p>
    </div>
  );
}
