from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import models
from .compliance import directive_states
from .db import Base, SessionLocal, engine, get_db
from .schemas import (
    AdBannerState,
    AdDirectiveOut,
    EngineAdStatusOut,
    EngineOut,
    ReleaseRequest,
    SbComplianceOut,
    ServiceBulletinOut,
    ShopVisitOut,
)
from .seed import seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(title="Fleet Compliance Portal", version="0.4.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/engines", response_model=list[EngineOut])
def list_engines(db: Session = Depends(get_db)):
    rows = db.scalars(select(models.Engine).order_by(models.Engine.serial)).all()
    return [EngineOut.from_orm_engine(e) for e in rows]


def _engine_or_404(engine_id: int, db: Session) -> models.Engine:
    e = db.get(models.Engine, engine_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Engine not found")
    return e


@app.get("/api/v1/engines/{engine_id}", response_model=EngineOut)
def get_engine(engine_id: int, db: Session = Depends(get_db)):
    return EngineOut.from_orm_engine(_engine_or_404(engine_id, db))


@app.get("/api/v1/engines/{engine_id}/sb-records", response_model=list[SbComplianceOut])
def list_engine_sb_records(engine_id: int, db: Session = Depends(get_db)):
    """Raw compliance records that have been logged against an engine (no applicability logic)."""
    _engine_or_404(engine_id, db)
    rows = db.scalars(
        select(models.SbCompliance)
        .options(selectinload(models.SbCompliance.service_bulletin))
        .where(models.SbCompliance.engine_id == engine_id)
    ).all()
    return [SbComplianceOut.from_orm_row(r) for r in rows]


@app.get("/api/v1/engines/{engine_id}/ad-status", response_model=EngineAdStatusOut)
def get_engine_ad_status(engine_id: int, db: Session = Depends(get_db)):
    """Airworthiness-directive state of an engine: applicable mandatory SBs still open."""
    e = _engine_or_404(engine_id, db)
    bulletins = db.scalars(
        select(models.ServiceBulletin).where(models.ServiceBulletin.family == e.family)
    ).all()
    recorded = {
        c.sb_id: c.status
        for c in db.scalars(
            select(models.SbCompliance).where(models.SbCompliance.engine_id == engine_id)
        ).all()
    }
    states = directive_states(e, list(bulletins), recorded)
    overdue = [s for s in states if s.overdue]
    if overdue:
        state = AdBannerState.RED
    elif states:
        state = AdBannerState.AMBER
    else:
        state = AdBannerState.GREEN
    return EngineAdStatusOut(
        engineId=e.id,
        serial=e.serial,
        csn=e.csn,
        state=state,
        overdueCount=len(overdue),
        dueSoonCount=len(states) - len(overdue),
        directives=[
            AdDirectiveOut(
                sbId=s.sb.id,
                sbNumber=s.sb.sb_number,
                adNumber=s.sb.related_ad_number,
                title=s.sb.title,
                complianceStatus=s.compliance_status,
                complianceDeadlineCycles=s.sb.compliance_deadline_cycles,
                cyclesRemaining=s.cycles_remaining,
                overdue=s.overdue,
            )
            for s in states
        ],
    )


@app.get("/api/v1/engines/{engine_id}/shop-visits", response_model=list[ShopVisitOut])
def list_engine_shop_visits(engine_id: int, db: Session = Depends(get_db)):
    _engine_or_404(engine_id, db)
    rows = db.scalars(
        select(models.ShopVisit)
        .options(selectinload(models.ShopVisit.engine))
        .where(models.ShopVisit.engine_id == engine_id)
        .order_by(models.ShopVisit.inducted_on.desc())
    ).all()
    return [ShopVisitOut.from_orm_sv(v) for v in rows]


@app.get("/api/v1/service-bulletins", response_model=list[ServiceBulletinOut])
def list_service_bulletins(family: str | None = None, db: Session = Depends(get_db)):
    q = select(models.ServiceBulletin).order_by(models.ServiceBulletin.sb_number)
    if family:
        q = q.where(models.ServiceBulletin.family == family)
    return [ServiceBulletinOut.from_orm_sb(s) for s in db.scalars(q).all()]


@app.get("/api/v1/service-bulletins/{sb_id}", response_model=ServiceBulletinOut)
def get_service_bulletin(sb_id: int, db: Session = Depends(get_db)):
    s = db.get(models.ServiceBulletin, sb_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Service bulletin not found")
    return ServiceBulletinOut.from_orm_sb(s)


@app.get("/api/v1/shop-visits", response_model=list[ShopVisitOut])
def list_shop_visits(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.ShopVisit)
        .options(selectinload(models.ShopVisit.engine))
        .order_by(models.ShopVisit.inducted_on.desc())
    ).all()
    return [ShopVisitOut.from_orm_sv(v) for v in rows]


def _shop_visit_or_404(visit_id: int, db: Session) -> models.ShopVisit:
    v = db.scalar(
        select(models.ShopVisit)
        .options(selectinload(models.ShopVisit.engine))
        .where(models.ShopVisit.id == visit_id)
    )
    if v is None:
        raise HTTPException(status_code=404, detail="Shop visit not found")
    return v


@app.get("/api/v1/shop-visits/{visit_id}", response_model=ShopVisitOut)
def get_shop_visit(visit_id: int, db: Session = Depends(get_db)):
    return ShopVisitOut.from_orm_sv(_shop_visit_or_404(visit_id, db))


@app.post("/api/v1/shop-visits/{visit_id}/release", response_model=ShopVisitOut)
def release_shop_visit(visit_id: int, body: ReleaseRequest, db: Session = Depends(get_db)):
    v = _shop_visit_or_404(visit_id, db)
    if v.status == models.ShopVisitStatus.RELEASED:
        raise HTTPException(status_code=409, detail="Shop visit already released")
    v.status = models.ShopVisitStatus.RELEASED
    v.released_at = datetime.now(timezone.utc).replace(tzinfo=None)
    v.released_by = body.releasedBy
    db.commit()
    db.refresh(v)
    return ShopVisitOut.from_orm_sv(v)
