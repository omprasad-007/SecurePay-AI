from __future__ import annotations

from datetime import datetime, timezone


def generate_markdown_report(summary: dict, insights: dict, patterns: list[str]) -> str:
    lines = [
        "# Excel Intelligence Report",
        "",
        "## Executive Summary",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Total Transactions: {summary.get('total_transactions', 0)}",
        f"Fraud Percentage: {summary.get('fraud_percentage', 0)}%",
        "",
        "## Risk Analysis",
        f"High Risk Count: {summary.get('high_risk_count', 0)}",
        f"Most Risky Merchant: {summary.get('most_risky_merchant', 'N/A')}",
        f"Peak Fraud Hour: {summary.get('peak_fraud_hour', 'N/A')}",
        "",
        "## System Performance Summary",
        "- Existing ML pipeline + adaptive risk evaluated uploaded records.",
        "- Decision engine mapped each record to LOW/MEDIUM/HIGH/CRITICAL.",
        "",
        "## Fraud Pattern Observations",
    ]

    if patterns:
        lines.extend([f"- {item}" for item in patterns])
    else:
        lines.append("- No dominant patterns detected.")

    lines.extend([
        "",
        "## Compliance Notes",
        "- Upload endpoint enforces file-size, file-type, and sanitization checks.",
        "- Invalid rows are logged to invalid_rows.json.",
        "",
        "## Dataset Insights",
        f"- Unique users: {insights.get('unique_users', 0)}",
        f"- Total volume: {insights.get('total_volume', 0)}",
        f"- Merchant categories: {insights.get('merchant_categories', 0)}",
    ])
    return "\n".join(lines)
