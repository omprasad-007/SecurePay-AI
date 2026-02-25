from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..cache import TTLCache
from ..config import settings
from ..database import get_db
from ..deps import HeatmapContext, enforce_rate_limit, require_roles
from ..repositories.heatmap_repository import (
    fetch_transactions,
    fetch_transactions_in_radius,
    replace_clusters,
    replace_predictive_zones,
    save_snapshot,
)
from ..schemas import (
    ComplianceReportResponse,
    DeviceAnomalyResponse,
    FraudClustersResponse,
    GeographicHeatmapResponse,
    HeatmapFilterQuery,
    HeatmapSummaryResponse,
    PredictiveRiskResponse,
    RealtimeStatusResponse,
    SARReportResponse,
    SuspiciousTransactionReportResponse,
    TimePatternResponse,
    ZoneDrilldownResponse,
)
from ..services import (
    build_compliance_export,
    build_compliance_report,
    build_device_anomaly_heatmap,
    build_geographic_heatmap,
    build_heatmap_summary,
    build_predictive_zones,
    build_realtime_status,
    build_sar_records,
    build_suspicious_transaction_report,
    build_time_pattern_heatmap,
    build_zone_drilldown,
    detect_fraud_clusters,
)
from ..utils import device_type_from_id, previous_period

router = APIRouter(prefix="/api/heatmap", tags=["heatmap-intelligence"])
cache = TTLCache(ttl_seconds=settings.cache_ttl_seconds, max_items=2048)


def _secure_context(
    role_ctx: HeatmapContext = Depends(require_roles("SUPER_ADMIN", "ORG_ADMIN", "ANALYST", "VIEWER")),
    _: HeatmapContext = Depends(enforce_rate_limit),
) -> HeatmapContext:
    return role_ctx


def _filter_rows_by_device(rows, device_type: str | None):
    if not device_type:
        return rows
    expected = device_type.strip().lower()
    return [row for row in rows if device_type_from_id(row.device_id).lower() == expected]


def _cache_key(endpoint: str, ctx: HeatmapContext, payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, default=str)
    return f"{endpoint}:{ctx.organization_id}:{ctx.user_id}:{body}"


def _compliance_bundle(
    *,
    filters: HeatmapFilterQuery,
    regulatory_amount_threshold: float,
    ctx: HeatmapContext,
    db: Session,
) -> tuple[ComplianceReportResponse, dict, dict]:
    rows = fetch_transactions(db, ctx, filters)
    rows = _filter_rows_by_device(rows, filters.device_type)
    clusters = detect_fraud_clusters(rows)
    compliance_report = build_compliance_report(
        rows=rows,
        clusters=clusters,
        regulatory_amount_threshold=regulatory_amount_threshold,
    )
    suspicious_report = build_suspicious_transaction_report(
        rows=rows,
        clusters_payload=clusters.model_dump(),
        regulatory_amount_threshold=regulatory_amount_threshold,
    )
    sar_report = build_sar_records(
        suspicious_report=suspicious_report,
        organization_id=ctx.organization_id,
    )
    return compliance_report, suspicious_report, sar_report


@router.get("/geographic", response_model=GeographicHeatmapResponse)
def geographic_heatmap(
    filters: HeatmapFilterQuery = Depends(),
    ctx: HeatmapContext = Depends(_secure_context),
    db: Session = Depends(get_db),
):
    key = _cache_key("geographic", ctx, filters.model_dump())
    cached = cache.get(key)
    if cached:
        return cached

    rows = fetch_transactions(db, ctx, filters)
    rows = _filter_rows_by_device(rows, filters.device_type)
    response = build_geographic_heatmap(rows)

    save_snapshot(
        db=db,
        ctx=ctx,
        start_date=filters.start_date,
        end_date=filters.end_date,
        layer_type="geographic",
        payload=response.model_dump(),
    )
    payload = response.model_dump()
    cache.set(key, payload)
    return payload


@router.get("/time-pattern", response_model=TimePatternResponse)
def time_pattern_heatmap(
    filters: HeatmapFilterQuery = Depends(),
    ctx: HeatmapContext = Depends(_secure_context),
    db: Session = Depends(get_db),
):
    key = _cache_key("time-pattern", ctx, filters.model_dump())
    cached = cache.get(key)
    if cached:
        return cached

    rows = fetch_transactions(db, ctx, filters)
    rows = _filter_rows_by_device(rows, filters.device_type)
    response = build_time_pattern_heatmap(rows)

    save_snapshot(
        db=db,
        ctx=ctx,
        start_date=filters.start_date,
        end_date=filters.end_date,
        layer_type="time-pattern",
        payload=response.model_dump(),
    )
    payload = response.model_dump()
    cache.set(key, payload)
    return payload


@router.get("/device-anomaly", response_model=DeviceAnomalyResponse)
def device_anomaly_heatmap(
    filters: HeatmapFilterQuery = Depends(),
    ctx: HeatmapContext = Depends(_secure_context),
    db: Session = Depends(get_db),
):
    key = _cache_key("device-anomaly", ctx, filters.model_dump())
    cached = cache.get(key)
    if cached:
        return cached

    rows = fetch_transactions(db, ctx, filters)
    rows = _filter_rows_by_device(rows, filters.device_type)
    response = build_device_anomaly_heatmap(rows)

    save_snapshot(
        db=db,
        ctx=ctx,
        start_date=filters.start_date,
        end_date=filters.end_date,
        layer_type="device-anomaly",
        payload=response.model_dump(),
    )
    payload = response.model_dump()
    cache.set(key, payload)
    return payload


@router.get("/fraud-clusters", response_model=FraudClustersResponse)
def fraud_clusters(
    filters: HeatmapFilterQuery = Depends(),
    ctx: HeatmapContext = Depends(_secure_context),
    db: Session = Depends(get_db),
):
    key = _cache_key("fraud-clusters", ctx, filters.model_dump())
    cached = cache.get(key)
    if cached:
        return cached

    rows = fetch_transactions(db, ctx, filters)
    rows = _filter_rows_by_device(rows, filters.device_type)
    response = detect_fraud_clusters(rows)

    replace_clusters(db, ctx, [cluster.model_dump() for cluster in response.clusters])
    save_snapshot(
        db=db,
        ctx=ctx,
        start_date=filters.start_date,
        end_date=filters.end_date,
        layer_type="fraud-clusters",
        payload=response.model_dump(),
    )
    payload = response.model_dump()
    cache.set(key, payload)
    return payload


@router.get("/predictive-risk", response_model=PredictiveRiskResponse)
def predictive_risk(
    filters: HeatmapFilterQuery = Depends(),
    ctx: HeatmapContext = Depends(_secure_context),
    db: Session = Depends(get_db),
):
    key = _cache_key("predictive-risk", ctx, filters.model_dump())
    cached = cache.get(key)
    if cached:
        return cached

    rows = fetch_transactions(db, ctx, filters)
    rows = _filter_rows_by_device(rows, filters.device_type)
    response = build_predictive_zones(rows)

    replace_predictive_zones(
        db=db,
        ctx=ctx,
        start_date=filters.start_date,
        end_date=filters.end_date,
        zones=[zone.model_dump() for zone in response.zones],
    )
    save_snapshot(
        db=db,
        ctx=ctx,
        start_date=filters.start_date,
        end_date=filters.end_date,
        layer_type="predictive-risk",
        payload=response.model_dump(),
    )
    payload = response.model_dump()
    cache.set(key, payload)
    return payload


@router.get("/zone-drilldown", response_model=ZoneDrilldownResponse)
def zone_drilldown(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    start_date: date = Query(...),
    end_date: date = Query(...),
    radius_degrees: float = Query(default=0.25, gt=0, le=2.5),
    ctx: HeatmapContext = Depends(_secure_context),
    db: Session = Depends(get_db),
):
    key = _cache_key(
        "zone-drilldown",
        ctx,
        {
            "lat": lat,
            "lng": lng,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "radius_degrees": radius_degrees,
        },
    )
    cached = cache.get(key)
    if cached:
        return cached

    rows = fetch_transactions_in_radius(
        db=db,
        ctx=ctx,
        start_date=start_date,
        end_date=end_date,
        lat=lat,
        lng=lng,
        radius_degrees=radius_degrees,
        limit=3000,
    )
    response = build_zone_drilldown(rows, lat=lat, lng=lng)
    payload = response.model_dump()
    cache.set(key, payload)
    return payload


@router.get("/realtime-status", response_model=RealtimeStatusResponse)
def realtime_status(
    ctx: HeatmapContext = Depends(_secure_context),
    db: Session = Depends(get_db),
):
    key = _cache_key("realtime-status", ctx, {})
    cached = cache.get(key)
    if cached:
        return cached

    response = build_realtime_status(db, ctx)
    payload = response.model_dump()
    cache.set(key, payload)
    return payload


@router.get("/summary", response_model=HeatmapSummaryResponse)
def heatmap_summary(
    filters: HeatmapFilterQuery = Depends(),
    ctx: HeatmapContext = Depends(_secure_context),
    db: Session = Depends(get_db),
):
    key = _cache_key("summary", ctx, filters.model_dump())
    cached = cache.get(key)
    if cached:
        return cached

    current_rows = fetch_transactions(db, ctx, filters)
    current_rows = _filter_rows_by_device(current_rows, filters.device_type)

    prev_start, prev_end = previous_period(filters.start_date, filters.end_date)
    previous_filters = filters.model_copy(update={"start_date": prev_start, "end_date": prev_end})
    previous_rows = fetch_transactions(db, ctx, previous_filters)
    previous_rows = _filter_rows_by_device(previous_rows, filters.device_type)

    device_heatmap = build_device_anomaly_heatmap(current_rows)
    clusters = detect_fraud_clusters(current_rows)
    response = build_heatmap_summary(
        start_date=filters.start_date,
        end_date=filters.end_date,
        current_rows=current_rows,
        previous_rows=previous_rows,
        device_heatmap=device_heatmap,
        clusters=clusters,
    )
    save_snapshot(
        db=db,
        ctx=ctx,
        start_date=filters.start_date,
        end_date=filters.end_date,
        layer_type="summary",
        payload=response.model_dump(),
    )
    payload = response.model_dump()
    cache.set(key, payload)
    return payload


@router.get("/compliance-report", response_model=ComplianceReportResponse)
def compliance_report(
    filters: HeatmapFilterQuery = Depends(),
    regulatory_amount_threshold: float = Query(default=100000.0, gt=0),
    ctx: HeatmapContext = Depends(_secure_context),
    db: Session = Depends(get_db),
):
    key = _cache_key(
        "compliance-report",
        ctx,
        {**filters.model_dump(), "regulatory_amount_threshold": regulatory_amount_threshold},
    )
    cached = cache.get(key)
    if cached:
        return cached

    compliance, _, _ = _compliance_bundle(
        filters=filters,
        regulatory_amount_threshold=regulatory_amount_threshold,
        ctx=ctx,
        db=db,
    )
    payload = compliance.model_dump()
    cache.set(key, payload)
    return payload


@router.get("/suspicious-transactions-report", response_model=SuspiciousTransactionReportResponse)
def suspicious_transactions_report(
    filters: HeatmapFilterQuery = Depends(),
    regulatory_amount_threshold: float = Query(default=100000.0, gt=0),
    ctx: HeatmapContext = Depends(_secure_context),
    db: Session = Depends(get_db),
):
    key = _cache_key(
        "suspicious-transactions-report",
        ctx,
        {**filters.model_dump(), "regulatory_amount_threshold": regulatory_amount_threshold},
    )
    cached = cache.get(key)
    if cached:
        return cached

    _, suspicious, _ = _compliance_bundle(
        filters=filters,
        regulatory_amount_threshold=regulatory_amount_threshold,
        ctx=ctx,
        db=db,
    )
    cache.set(key, suspicious)
    return suspicious


@router.get("/sar", response_model=SARReportResponse)
def sar_report(
    filters: HeatmapFilterQuery = Depends(),
    regulatory_amount_threshold: float = Query(default=100000.0, gt=0),
    ctx: HeatmapContext = Depends(_secure_context),
    db: Session = Depends(get_db),
):
    key = _cache_key(
        "sar",
        ctx,
        {**filters.model_dump(), "regulatory_amount_threshold": regulatory_amount_threshold},
    )
    cached = cache.get(key)
    if cached:
        return cached

    _, _, sar = _compliance_bundle(
        filters=filters,
        regulatory_amount_threshold=regulatory_amount_threshold,
        ctx=ctx,
        db=db,
    )
    cache.set(key, sar)
    return sar


@router.get("/compliance-report/export")
def export_compliance_report(
    filters: HeatmapFilterQuery = Depends(),
    export_format: str = Query(default="json", pattern="^(pdf|excel|xlsx|json|xml|encrypted_xml)$"),
    regulatory_amount_threshold: float = Query(default=100000.0, gt=0),
    ctx: HeatmapContext = Depends(_secure_context),
    db: Session = Depends(get_db),
):
    compliance, suspicious, sar = _compliance_bundle(
        filters=filters,
        regulatory_amount_threshold=regulatory_amount_threshold,
        ctx=ctx,
        db=db,
    )
    data, content_type, filename = build_compliance_export(
        export_format=export_format,
        compliance_report=compliance,
        suspicious_report=suspicious,
        sar_report=sar,
        organization_id=ctx.organization_id,
    )
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=data, media_type=content_type, headers=headers)
