from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.orm import Session

from ..deps import HeatmapContext
from ..models import FraudCluster, FraudHeatmapSnapshot, HeatmapAlert, PredictiveRiskZone
from ..schemas import HeatmapFilterQuery
from ..source_models import AuditSourceTransaction
from ..utils.geo import to_datetime_bounds


def fetch_transactions(db: Session, ctx: HeatmapContext, filters: HeatmapFilterQuery) -> list[AuditSourceTransaction]:
    start_dt, end_dt = to_datetime_bounds(filters.start_date, filters.end_date)
    query = select(AuditSourceTransaction).where(
        AuditSourceTransaction.organization_id == ctx.organization_id,
        AuditSourceTransaction.transaction_datetime >= start_dt,
        AuditSourceTransaction.transaction_datetime <= end_dt,
    )

    if filters.risk_level:
        query = query.where(AuditSourceTransaction.risk_level.ilike(filters.risk_level))
    if filters.min_amount is not None:
        query = query.where(AuditSourceTransaction.transaction_amount >= filters.min_amount)
    if filters.max_amount is not None:
        query = query.where(AuditSourceTransaction.transaction_amount <= filters.max_amount)
    if filters.user_segment:
        query = query.where(AuditSourceTransaction.user_id == filters.user_segment)

    rows = db.execute(query.order_by(desc(AuditSourceTransaction.transaction_datetime)).limit(filters.limit)).scalars().all()
    return rows


def fetch_transactions_in_radius(
    db: Session,
    ctx: HeatmapContext,
    start_date: date,
    end_date: date,
    lat: float,
    lng: float,
    radius_degrees: float = 0.25,
    limit: int = 1500,
) -> list[AuditSourceTransaction]:
    start_dt, end_dt = to_datetime_bounds(start_date, end_date)
    return db.execute(
        select(AuditSourceTransaction)
        .where(
            AuditSourceTransaction.organization_id == ctx.organization_id,
            AuditSourceTransaction.transaction_datetime >= start_dt,
            AuditSourceTransaction.transaction_datetime <= end_dt,
            AuditSourceTransaction.geo_latitude.is_not(None),
            AuditSourceTransaction.geo_longitude.is_not(None),
            AuditSourceTransaction.geo_latitude >= lat - radius_degrees,
            AuditSourceTransaction.geo_latitude <= lat + radius_degrees,
            AuditSourceTransaction.geo_longitude >= lng - radius_degrees,
            AuditSourceTransaction.geo_longitude <= lng + radius_degrees,
        )
        .order_by(desc(AuditSourceTransaction.transaction_datetime))
        .limit(limit)
    ).scalars().all()


def fetch_hourly_high_risk_counts(
    db: Session,
    ctx: HeatmapContext,
    hours: int = 2,
) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    rows = db.execute(
        select(
            func.strftime("%Y-%m-%d %H:00:00", AuditSourceTransaction.transaction_datetime).label("hour_key"),
            func.count(AuditSourceTransaction.id).label("total"),
            func.sum(case((AuditSourceTransaction.risk_score > 60, 1), else_=0)).label("high_risk"),
            func.avg(AuditSourceTransaction.risk_score).label("avg_risk"),
        )
        .where(
            AuditSourceTransaction.organization_id == ctx.organization_id,
            AuditSourceTransaction.transaction_datetime >= cutoff,
        )
        .group_by("hour_key")
        .order_by(desc("hour_key"))
    ).all()

    return [
        {
            "hour_key": row.hour_key,
            "total": int(row.total or 0),
            "high_risk": int(row.high_risk or 0),
            "avg_risk": round(float(row.avg_risk or 0.0), 2),
        }
        for row in rows
    ]


def save_snapshot(
    db: Session,
    ctx: HeatmapContext,
    start_date: date,
    end_date: date,
    layer_type: str,
    payload: dict,
) -> FraudHeatmapSnapshot:
    snapshot = FraudHeatmapSnapshot(
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        start_date=start_date,
        end_date=end_date,
        layer_type=layer_type,
        payload=payload,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def replace_clusters(db: Session, ctx: HeatmapContext, clusters: list[dict]) -> list[FraudCluster]:
    db.query(FraudCluster).filter(FraudCluster.organization_id == ctx.organization_id).delete()

    saved = []
    for cluster in clusters:
        row = FraudCluster(
            organization_id=ctx.organization_id,
            cluster_id=cluster["cluster_id"],
            users=cluster["users"],
            shared_devices=cluster["shared_devices"],
            shared_ips=cluster["shared_ips"],
            shared_accounts=cluster["shared_accounts"],
            ring_risk_score=cluster["ring_risk_score"],
            cluster_size=cluster["cluster_size"],
            summary=cluster.get("summary"),
        )
        db.add(row)
        saved.append(row)
    db.commit()
    for row in saved:
        db.refresh(row)
    return saved


def replace_predictive_zones(
    db: Session,
    ctx: HeatmapContext,
    start_date: date,
    end_date: date,
    zones: list[dict],
) -> list[PredictiveRiskZone]:
    db.query(PredictiveRiskZone).filter(
        PredictiveRiskZone.organization_id == ctx.organization_id,
        PredictiveRiskZone.user_id == ctx.user_id,
        PredictiveRiskZone.window_start == start_date,
        PredictiveRiskZone.window_end == end_date,
    ).delete()

    created = []
    for zone in zones:
        row = PredictiveRiskZone(
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            city=zone.get("city"),
            state=zone.get("state"),
            country=zone.get("country"),
            geo_latitude=zone.get("geo_latitude"),
            geo_longitude=zone.get("geo_longitude"),
            historical_density=zone.get("historical_density", 0.0),
            growth_rate=zone.get("growth_rate", 0.0),
            transaction_growth_velocity=zone.get("transaction_growth_velocity", 0.0),
            predicted_risk_score=zone.get("predicted_risk_score", 0.0),
            label=zone.get("label", "Monitor"),
            window_start=start_date,
            window_end=end_date,
        )
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return created


def create_heatmap_alert(
    db: Session,
    ctx: HeatmapContext,
    alert_type: str,
    severity: str,
    message: str,
    trigger_payload: dict,
) -> HeatmapAlert:
    row = HeatmapAlert(
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        alert_type=alert_type,
        severity=severity,
        message=message,
        trigger_payload=trigger_payload,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def latest_alert_by_type(
    db: Session,
    ctx: HeatmapContext,
    alert_type: str,
    within_minutes: int = 30,
) -> HeatmapAlert | None:
    cutoff = datetime.utcnow() - timedelta(minutes=within_minutes)
    return db.execute(
        select(HeatmapAlert).where(
            HeatmapAlert.organization_id == ctx.organization_id,
            HeatmapAlert.alert_type == alert_type,
            HeatmapAlert.created_at >= cutoff,
        )
    ).scalar_one_or_none()


def list_recent_alerts(db: Session, ctx: HeatmapContext, limit: int = 20) -> list[HeatmapAlert]:
    return db.execute(
        select(HeatmapAlert)
        .where(HeatmapAlert.organization_id == ctx.organization_id)
        .order_by(desc(HeatmapAlert.created_at))
        .limit(limit)
    ).scalars().all()
