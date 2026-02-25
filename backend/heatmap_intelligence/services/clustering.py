from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from ..schemas import DeviceAnomalyPoint, DeviceAnomalyResponse, FraudClusterRecord, FraudClustersResponse
from ..source_models import AuditSourceTransaction
from ..utils.geo import clamp, device_type_from_id


def _safe_cluster_labels(feature_rows: list[list[float]]) -> list[str]:
    if not feature_rows:
        return []

    try:
        from sklearn.cluster import KMeans

        clusters = max(1, min(4, len(feature_rows)))
        model = KMeans(n_clusters=clusters, n_init=10, random_state=42)
        labels = model.fit_predict(feature_rows)
        return [f"C{int(label)}" for label in labels]
    except Exception:
        labels = []
        for features in feature_rows:
            score = features[-1] * 100
            if score > 80:
                labels.append("C3")
            elif score > 60:
                labels.append("C2")
            elif score > 35:
                labels.append("C1")
            else:
                labels.append("C0")
        return labels


def build_device_anomaly_heatmap(rows: list[AuditSourceTransaction]) -> DeviceAnomalyResponse:
    by_device: dict[str, list[AuditSourceTransaction]] = defaultdict(list)
    by_ip: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        device_id = row.device_id or "unknown-device"
        by_device[device_id].append(row)
        if row.ip_address:
            by_ip[row.ip_address].add(device_id)

    points: list[DeviceAnomalyPoint] = []
    features: list[list[float]] = []

    for device_id, items in by_device.items():
        if not items:
            continue

        ordered = sorted(items, key=lambda row: row.transaction_datetime)
        start = ordered[0].transaction_datetime
        end = ordered[-1].transaction_datetime
        span_days = max(1.0, (end - start).total_seconds() / 86400)
        login_frequency = len(items) / span_days

        ten_min_windows = defaultdict(int)
        for row in ordered:
            minute_key = row.transaction_datetime.replace(minute=(row.transaction_datetime.minute // 10) * 10, second=0, microsecond=0)
            ten_min_windows[minute_key] += 1
        transaction_speed = max(ten_min_windows.values()) if ten_min_windows else 1

        unique_cities = {row.city for row in items if row.city}
        geo_mismatch_score = clamp((len(unique_cities) - 1) / 5.0, 0.0, 1.0)

        unique_ips = {row.ip_address for row in items if row.ip_address}
        ip_anomaly_score = clamp(len(unique_ips) / max(1, len(items)), 0.0, 1.0)

        transaction_risk = sum(float(row.risk_score or 0.0) for row in items) / (100.0 * max(1, len(items)))
        behavioral_risk = clamp((min(login_frequency / 12.0, 1.0) * 0.35) + (min(transaction_speed / 6.0, 1.0) * 0.35) + (geo_mismatch_score * 0.30), 0.0, 1.0)
        shared_ip_pressure = 0.0
        for ip in unique_ips:
            shared_ip_pressure = max(shared_ip_pressure, clamp((len(by_ip[ip]) - 1) / 6.0, 0.0, 1.0))
        network_risk = shared_ip_pressure
        historical_fraud_probability = clamp(sum(1 for row in items if float(row.risk_score or 0.0) > 60) / max(1, len(items)), 0.0, 1.0)

        anomaly_score = (
            0.35 * transaction_risk
            + 0.30 * behavioral_risk
            + 0.20 * network_risk
            + 0.15 * historical_fraud_probability
        )
        anomaly_pct = round(clamp(anomaly_score * 100, 0.0, 100.0), 2)

        if anomaly_pct > 80:
            anomaly_level = "Critical"
        elif anomaly_pct > 60:
            anomaly_level = "High"
        elif anomaly_pct > 30:
            anomaly_level = "Medium"
        else:
            anomaly_level = "Low"

        point = DeviceAnomalyPoint(
            device_id=device_id,
            device_type=device_type_from_id(device_id),
            transaction_count=len(items),
            login_frequency=round(login_frequency, 2),
            transaction_speed=round(float(transaction_speed), 2),
            geo_mismatch_score=round(geo_mismatch_score * 100, 2),
            ip_anomaly_score=round(ip_anomaly_score * 100, 2),
            anomaly_score=anomaly_pct,
            cluster_label="",
            anomaly_level=anomaly_level,
        )
        points.append(point)
        features.append(
            [
                min(login_frequency / 12.0, 1.0),
                min(transaction_speed / 8.0, 1.0),
                geo_mismatch_score,
                ip_anomaly_score,
                anomaly_score,
            ]
        )

    labels = _safe_cluster_labels(features)
    for idx, label in enumerate(labels):
        if idx < len(points):
            points[idx].cluster_label = label

    points.sort(key=lambda item: item.anomaly_score, reverse=True)
    return DeviceAnomalyResponse(
        devices=points,
        meta={
            "device_count": len(points),
            "critical_devices": sum(1 for item in points if item.anomaly_level == "Critical"),
        },
    )


def _connected_components(graph: dict[str, set[str]]) -> list[set[str]]:
    seen: set[str] = set()
    components: list[set[str]] = []
    for node in graph:
        if node in seen:
            continue
        stack = [node]
        comp: set[str] = set()
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            comp.add(current)
            stack.extend(graph.get(current, set()) - seen)
        components.append(comp)
    return components


def detect_fraud_clusters(rows: list[AuditSourceTransaction]) -> FraudClustersResponse:
    graph: dict[str, set[str]] = defaultdict(set)
    by_user: dict[str, list[AuditSourceTransaction]] = defaultdict(list)
    tx_by_user_account: dict[tuple[str, str], int] = defaultdict(int)

    for row in rows:
        user = f"user:{row.user_id}"
        by_user[row.user_id].append(row)
        if row.device_id:
            device = f"device:{row.device_id}"
            graph[user].add(device)
            graph[device].add(user)
        if row.ip_address:
            ip = f"ip:{row.ip_address}"
            graph[user].add(ip)
            graph[ip].add(user)
        if row.merchant_name:
            account = f"account:{row.merchant_name}"
            graph[user].add(account)
            graph[account].add(user)
            tx_by_user_account[(row.user_id, row.merchant_name)] += 1

    clusters: list[FraudClusterRecord] = []
    for index, component in enumerate(_connected_components(graph), start=1):
        users = sorted(item.split(":", 1)[1] for item in component if item.startswith("user:"))
        if len(users) < 2:
            continue
        devices = sorted(item.split(":", 1)[1] for item in component if item.startswith("device:"))
        ips = sorted(item.split(":", 1)[1] for item in component if item.startswith("ip:"))
        accounts = sorted(item.split(":", 1)[1] for item in component if item.startswith("account:"))

        component_rows = [row for user in users for row in by_user[user]]
        total_tx = max(1, len(component_rows))
        high_risk_ratio = sum(1 for row in component_rows if float(row.risk_score or 0.0) > 60) / total_tx

        shared_devices_metric = clamp(len(devices) / max(1, len(users)), 0.0, 1.0)
        shared_ips_metric = clamp(len(ips) / max(1, len(users)), 0.0, 1.0)
        shared_accounts_metric = clamp(len(accounts) / max(1, len(users)), 0.0, 1.0)

        sorted_times = sorted(row.transaction_datetime for row in component_rows)
        if len(sorted_times) >= 2:
            close_pairs = 0
            for pos in range(1, len(sorted_times)):
                if (sorted_times[pos] - sorted_times[pos - 1]).total_seconds() <= 3600:
                    close_pairs += 1
            time_proximity = clamp(close_pairs / max(1, len(sorted_times) - 1), 0.0, 1.0)
        else:
            time_proximity = 0.0

        ring_score = (
            20 * shared_devices_metric
            + 20 * shared_ips_metric
            + 25 * shared_accounts_metric
            + 15 * time_proximity
            + 20 * high_risk_ratio
        )
        ring_score = round(clamp(ring_score, 0.0, 100.0), 2)
        if ring_score < 40:
            continue

        clusters.append(
            FraudClusterRecord(
                cluster_id=f"cluster-{index}",
                cluster_size=len(component),
                users=users,
                shared_devices=devices,
                shared_ips=ips,
                shared_accounts=accounts,
                high_risk_ratio=round(high_risk_ratio * 100, 2),
                ring_risk_score=ring_score,
                summary=(
                    f"Connected user/device/ip/account network with {len(users)} users, "
                    f"{len(devices)} shared devices, {len(ips)} shared IPs."
                ),
                detected_at=datetime.utcnow(),
            )
        )

    clusters.sort(key=lambda item: item.ring_risk_score, reverse=True)
    return FraudClustersResponse(
        clusters=clusters,
        meta={
            "cluster_count": len(clusters),
            "high_severity_clusters": sum(1 for item in clusters if item.ring_risk_score > 70),
        },
    )
