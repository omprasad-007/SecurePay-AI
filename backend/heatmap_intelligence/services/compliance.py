from __future__ import annotations

from collections import Counter
from datetime import datetime

from ..schemas import ComplianceItem, ComplianceReportResponse
from ..source_models import AuditSourceTransaction
from .clustering import FraudClustersResponse


def build_compliance_report(
    rows: list[AuditSourceTransaction],
    clusters: FraudClustersResponse,
    regulatory_amount_threshold: float = 100000.0,
) -> ComplianceReportResponse:
    cluster_by_user: dict[str, str] = {}
    for cluster in clusters.clusters:
        for user_id in cluster.users:
            cluster_by_user[user_id] = cluster.cluster_id

    suspicious: list[ComplianceItem] = []
    top_accounts = Counter()
    for row in rows:
        risk = float(row.risk_score or 0.0)
        cluster_id = cluster_by_user.get(row.user_id)
        should_flag = risk > 80 or cluster_id is not None or float(row.transaction_amount or 0.0) >= regulatory_amount_threshold
        if not should_flag:
            continue

        status = "REVIEW_REQUIRED"
        if risk > 90 or cluster_id is not None:
            status = "SAR_CANDIDATE"

        suspicious.append(
            ComplianceItem(
                transaction_id=row.transaction_id,
                user_id=row.user_id,
                risk_score=round(risk, 2),
                risk_reasons=list(row.risk_reasons or []),
                city=row.city,
                country=row.country,
                device_id=row.device_id,
                cluster_id=cluster_id,
                compliance_status=status,
            )
        )
        top_accounts[row.user_id] += 1

    total = len(rows)
    suspicious_count = len(suspicious)
    fraud_rate = (suspicious_count / max(1, total)) * 100.0
    top_suspicious_accounts = [{"user_id": user_id, "count": count} for user_id, count in top_accounts.most_common(10)]

    summary = (
        f"Compliance scan processed {total} transactions; {suspicious_count} flagged "
        f"({fraud_rate:.1f}% rate) using risk threshold, fraud-ring membership, and regulatory amount rules."
    )

    return ComplianceReportResponse(
        report_generated_at=datetime.utcnow(),
        total_transactions=total,
        suspicious_transactions=suspicious_count,
        fraud_rate=round(fraud_rate, 2),
        top_suspicious_accounts=top_suspicious_accounts,
        transactions=suspicious[:1000],
        executive_summary=summary,
    )
