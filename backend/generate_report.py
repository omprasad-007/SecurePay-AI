from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import List


def generate_csv(transactions: List[dict]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "userId",
        "receiverId",
        "amount",
        "timestamp",
        "risk_level",
        "final_score",
    ])
    for tx in transactions:
        writer.writerow([
            tx.get("id"),
            tx.get("userId"),
            tx.get("receiverId"),
            tx.get("amount"),
            tx.get("timestamp"),
            tx.get("risk_level") or tx.get("riskLevel"),
            tx.get("finalScore") or tx.get("final_score"),
        ])
    return output.getvalue()


def weekly_summary(transactions: List[dict]) -> dict:
    total = len(transactions)
    high = len([tx for tx in transactions if (tx.get("risk_level") or tx.get("riskLevel")) in {"HIGH", "CRITICAL", "High"}])
    fraud_rate = round((high / total) * 100, 2) if total else 0
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_transactions": total,
        "high_risk": high,
        "fraud_rate": fraud_rate,
    }


def generate_pdf_summary(summary: dict) -> bytes:
    lines = [
        "SecurePay AI Weekly Fraud Summary",
        f"Generated: {summary.get('generated_at')}",
        f"Total Transactions: {summary.get('total_transactions')}",
        f"High Risk Count: {summary.get('high_risk')}",
        f"Fraud Rate: {summary.get('fraud_rate')}%",
    ]
    content = "\n".join(lines)
    escaped = content.replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 50 750 Td ({escaped}) Tj ET"
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
