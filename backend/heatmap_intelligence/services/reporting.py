from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import json
import os
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

from ..schemas import ComplianceReportResponse
from .risk_engine import compute_transaction_risk_scores

try:
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover - optional dependency fallback
    Fernet = None  # type: ignore


def _cluster_by_user(clusters_payload: dict[str, Any]) -> dict[str, str]:
    by_user: dict[str, str] = {}
    for cluster in clusters_payload.get("clusters", []):
        cluster_id = str(cluster.get("cluster_id") or "")
        for user_id in cluster.get("users", []):
            by_user[str(user_id)] = cluster_id
    return by_user


def build_suspicious_transaction_report(
    *,
    rows: list[Any],
    clusters_payload: dict[str, Any],
    regulatory_amount_threshold: float,
) -> dict[str, Any]:
    cluster_map = _cluster_by_user(clusters_payload)
    risk_feature_map = compute_transaction_risk_scores(
        rows=rows,
        cluster_by_user=cluster_map,
        regulatory_amount_threshold=regulatory_amount_threshold,
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        txn_features = risk_feature_map.get(row.transaction_id, {})
        risk_score = float(txn_features.get("final_risk", float(row.risk_score or 0.0)))
        cluster_id = txn_features.get("cluster_id") or cluster_map.get(str(row.user_id))
        amount = float(row.transaction_amount or 0.0)
        flagged = bool(txn_features.get("compliance_review")) or risk_score > 80 or bool(cluster_id) or amount >= regulatory_amount_threshold
        if not flagged:
            continue

        items.append(
            {
                "transaction_id": row.transaction_id,
                "user_details": {"user_id": row.user_id},
                "risk_score": round(risk_score, 2),
                "risk_reasons": list(row.risk_reasons or []),
                "geo_data": {
                    "city": row.city,
                    "state": row.state,
                    "country": row.country,
                    "lat": row.geo_latitude,
                    "lng": row.geo_longitude,
                },
                "device_fingerprint": row.device_id,
                "ml_probability": txn_features.get("ml_probability", round(float(row.risk_score or 0.0) / 100.0, 4)),
                "fraud_cluster_id": cluster_id,
                "amount": round(amount, 2),
                "timestamp": row.transaction_datetime.isoformat(),
                "feature_categories": {
                    "transaction": txn_features.get("transaction_features", {}),
                    "behavioral": txn_features.get("behavioral_features", {}),
                    "network": txn_features.get("network_features", {}),
                },
                "anomaly_score": txn_features.get("anomaly_score"),
                "rule_based_score": txn_features.get("rule_based_score"),
                "final_risk_level": txn_features.get("final_risk_level"),
            }
        )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "total_flagged": len(items),
        "transactions": items[:2000],
    }


def build_sar_records(
    *,
    suspicious_report: dict[str, Any],
    organization_id: str,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for item in suspicious_report.get("transactions", []):
        activity_types = []
        if float(item.get("risk_score", 0.0)) > 80:
            activity_types.append("HIGH_RISK_SCORE")
        if item.get("fraud_cluster_id"):
            activity_types.append("FRAUD_RING_LINK")
        if float(item.get("amount", 0.0)) > 100000:
            activity_types.append("REGULATORY_THRESHOLD_BREACH")
        if not activity_types:
            activity_types.append("SUSPICIOUS_PATTERN")

        narrative = (
            f"Transaction {item.get('transaction_id')} from account {item.get('user_details', {}).get('user_id')} "
            f"shows suspicious behavior due to {', '.join(activity_types)} with risk score {item.get('risk_score')}."
        )

        records.append(
            {
                "report_id": f"SAR-{uuid.uuid4().hex[:12].upper()}",
                "organization_id": organization_id,
                "subject_account": item.get("user_details", {}).get("user_id"),
                "suspicious_activity_type": activity_types,
                "narrative_summary": narrative,
                "transaction_details": [item],
                "risk_score": item.get("risk_score"),
                "compliance_status": "UNDER_REVIEW",
                "created_at": datetime.utcnow().isoformat(),
            }
        )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "total_reports": len(records),
        "reports": records[:1000],
    }


def _rows_for_export(
    compliance_report: ComplianceReportResponse,
    suspicious_report: dict[str, Any],
    sar_report: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    by_tx = {item["transaction_id"]: item for item in suspicious_report.get("transactions", [])}
    by_sar_tx: dict[str, str] = {}
    for sar in sar_report.get("reports", []):
        for tx in sar.get("transaction_details", []):
            tx_id = str(tx.get("transaction_id") or "")
            if tx_id:
                by_sar_tx[tx_id] = sar.get("report_id", "")

    for item in compliance_report.transactions:
        suspicious = by_tx.get(item.transaction_id, {})
        records.append(
            {
                "transaction_id": item.transaction_id,
                "user_id": item.user_id,
                "risk_score": item.risk_score,
                "compliance_status": item.compliance_status,
                "cluster_id": item.cluster_id,
                "city": item.city,
                "country": item.country,
                "device_id": item.device_id,
                "ml_probability": suspicious.get("ml_probability"),
                "sar_report_id": by_sar_tx.get(item.transaction_id),
            }
        )
    return records


def _build_pdf_bytes(title: str, lines: list[str]) -> bytes:
    body = [title, *lines]
    escaped = "\\n".join(body).replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 10 Tf 48 760 Td ({escaped}) Tj ET"
    pdf = b"%PDF-1.4\n"
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n",
        f"4 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream\nendobj\n",
        "5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj.encode("utf-8")
    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode("utf-8")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode("utf-8")
    pdf += (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    ).encode("utf-8")
    return pdf


def _build_excel_bytes(rows: list[dict[str, Any]]) -> bytes:
    output = io.BytesIO()
    try:
        import openpyxl

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Compliance"
        headers = list(rows[0].keys()) if rows else ["transaction_id", "user_id", "risk_score"]
        sheet.append(headers)
        for row in rows:
            sheet.append([row.get(header) for header in headers])
        workbook.save(output)
        return output.getvalue()
    except Exception:
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        headers = list(rows[0].keys()) if rows else ["transaction_id", "user_id", "risk_score"]
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row.get(header) for header in headers])
        return csv_buffer.getvalue().encode("utf-8")


def _build_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=True, indent=2, default=str).encode("utf-8")


def _serialize_xml(payload: dict[str, Any]) -> bytes:
    root = ET.Element("compliance_export")
    meta = ET.SubElement(root, "meta")
    ET.SubElement(meta, "generated_at").text = datetime.utcnow().isoformat()

    for section_name in ("compliance_report", "suspicious_report", "sar_report"):
        section = ET.SubElement(root, section_name)
        section_payload = payload.get(section_name, {})
        section.text = json.dumps(section_payload, default=str)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _encrypt_xml(data: bytes, organization_id: str) -> bytes:
    configured_key = os.getenv("HEATMAP_XML_ENCRYPTION_KEY", "").strip()
    if Fernet is not None:
        if configured_key:
            key = configured_key.encode("utf-8")
        else:
            digest = hashlib.sha256(f"securepay:{organization_id}".encode("utf-8")).digest()
            key = base64.urlsafe_b64encode(digest)
        try:
            token = Fernet(key).encrypt(data)
            return token
        except Exception:
            pass

    # Fallback: sign + encode when Fernet/key is not available.
    secret = os.getenv("HEATMAP_XML_FALLBACK_SECRET", "securepay-heatmap")
    signature = hmac.new(secret.encode("utf-8"), data, hashlib.sha256).hexdigest().encode("utf-8")
    return base64.b64encode(signature + b"." + data)


def build_compliance_export(
    *,
    export_format: str,
    compliance_report: ComplianceReportResponse,
    suspicious_report: dict[str, Any],
    sar_report: dict[str, Any],
    organization_id: str,
) -> tuple[bytes, str, str]:
    normalized = export_format.strip().lower()
    rows = _rows_for_export(compliance_report, suspicious_report, sar_report)

    if normalized == "pdf":
        lines = [
            f"Total Transactions: {compliance_report.total_transactions}",
            f"Suspicious Transactions: {compliance_report.suspicious_transactions}",
            f"Fraud Rate: {compliance_report.fraud_rate}%",
            f"SAR Reports: {sar_report.get('total_reports', 0)}",
            f"Executive Summary: {compliance_report.executive_summary}",
        ]
        return _build_pdf_bytes("SecurePay AML Compliance Report", lines), "application/pdf", "compliance_report.pdf"

    if normalized in {"xlsx", "excel"}:
        return (
            _build_excel_bytes(rows),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "compliance_report.xlsx",
        )

    payload = {
        "compliance_report": compliance_report.model_dump(),
        "suspicious_report": suspicious_report,
        "sar_report": sar_report,
    }

    if normalized == "json":
        return _build_json_bytes(payload), "application/json", "compliance_report.json"

    if normalized in {"xml", "encrypted_xml"}:
        xml_raw = _serialize_xml(payload)
        encrypted = _encrypt_xml(xml_raw, organization_id)
        return encrypted, "application/octet-stream", "compliance_report_encrypted.xml"

    raise ValueError("Unsupported export format. Use pdf, excel, json, or encrypted_xml.")
