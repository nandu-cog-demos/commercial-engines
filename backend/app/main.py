from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import models
from .compliance import blocking_sbs, compliance_rows, overdue_mandatory_count
from .db import Base, SessionLocal, engine, get_db
from .schemas import (
    EngineComplianceRow,
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


def _all_sbs(db: Session) -> list[models.ServiceBulletin]:
    return list(db.scalars(select(models.ServiceBulletin)).all())


@app.get("/api/v1/engines", response_model=list[EngineOut])
def list_engines(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.Engine)
        .options(selectinload(models.Engine.compliance))
        .order_by(models.Engine.serial)
    ).all()
    sbs = _all_sbs(db)
    return [
        EngineOut.from_orm_engine(e, overdue_mandatory_count(compliance_rows(e, sbs)))
        for e in rows
    ]


def _engine_or_404(engine_id: int, db: Session) -> models.Engine:
    e = db.get(models.Engine, engine_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Engine not found")
    return e


def _engine_compliance(engine: models.Engine, db: Session) -> list[EngineComplianceRow]:
    return compliance_rows(engine, _all_sbs(db))


@app.get("/api/v1/engines/{engine_id}", response_model=EngineOut)
def get_engine(engine_id: int, db: Session = Depends(get_db)):
    return EngineOut.from_orm_engine(_engine_or_404(engine_id, db))


@app.get("/api/v1/engines/{engine_id}/compliance", response_model=list[EngineComplianceRow])
def get_engine_compliance(engine_id: int, db: Session = Depends(get_db)):
    """One row per SB applicable to the engine (family + serial range), with overdue flag."""
    return _engine_compliance(_engine_or_404(engine_id, db), db)


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
    blockers = blocking_sbs(_engine_compliance(v.engine, db))
    if blockers:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Release blocked by overdue mandatory SBs",
                "blockingSbs": [b.model_dump() for b in blockers],
            },
        )
    v.status = models.ShopVisitStatus.RELEASED
    v.released_at = datetime.now(timezone.utc).replace(tzinfo=None)
    v.released_by = body.releasedBy
    db.commit()
    db.refresh(v)
    return ShopVisitOut.from_orm_sv(v)
