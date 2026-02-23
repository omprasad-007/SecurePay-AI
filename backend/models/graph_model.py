from __future__ import annotations

import networkx as nx


def build_graph(history: list[dict]) -> nx.DiGraph:
    graph = nx.DiGraph()
    for tx in history:
        graph.add_edge(tx["userId"], tx["receiverId"], weight=tx.get("amount", 0))
    return graph


def detect_cycles(graph: nx.DiGraph, limit: int = 50) -> set[str]:
    suspicious = set()
    try:
        cycles = nx.simple_cycles(graph)
        count = 0
        for cycle in cycles:
            if len(cycle) <= 4:
                suspicious.update(cycle)
            count += 1
            if count >= limit:
                break
    except nx.NetworkXNoCycle:
        return suspicious
    return suspicious


def graph_risk_score(tx: dict, history: list[dict]) -> float:
    if len(history) < 3:
        return 20.0
    graph = build_graph(history)
    centrality = nx.degree_centrality(graph)
    cycles = detect_cycles(graph)

    user = tx["userId"]
    receiver = tx["receiverId"]
    risk = 0.0

    risk += centrality.get(user, 0.0) * 60
    risk += centrality.get(receiver, 0.0) * 40

    if user in cycles or receiver in cycles:
        risk += 35

    return float(max(0.0, min(100.0, risk)))


def graph_view(history: list[dict]) -> dict:
    graph = build_graph(history)
    centrality = nx.degree_centrality(graph)
    cycles = detect_cycles(graph)

    nodes = []
    for node in graph.nodes:
        flagged = centrality.get(node, 0) > 0.4 or node in cycles
        nodes.append({
            "id": node,
            "label": node.replace("USER", "U").replace("MERCH", "M"),
            "flagged": flagged,
        })

    links = []
    for source, target in graph.edges:
        links.append({"source": source, "target": target})

    return {"nodes": nodes, "links": links}
