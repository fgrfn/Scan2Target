from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.database import get_db

router = APIRouter()
_auth = Depends(get_current_user)


@router.get("/overview")
def overview(_=_auth):
    with get_db().connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        ok    = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='completed'").fetchone()[0]
        fail  = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='failed'").fetchone()[0]
    return {"total": total, "successful": ok, "failed": fail,
            "success_rate": round(ok / total * 100, 1) if total else 0}


@router.get("/timeline")
def timeline(days: int = 30, _=_auth):
    with get_db().connection() as conn:
        rows = conn.execute("""
            SELECT substr(created_at,1,10) as date,
                   COUNT(*) as total,
                   SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as successful,
                   SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
            FROM jobs
            WHERE created_at >= datetime('now', ? || ' days')
            GROUP BY date ORDER BY date
        """, (f"-{days}",)).fetchall()
    return [dict(r) for r in rows]


@router.get("/scanners")
def by_scanner(_=_auth):
    with get_db().connection() as conn:
        rows = conn.execute("""
            SELECT device_id as scanner, COUNT(*) as total_scans,
                   ROUND(100.0*SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END)/COUNT(*),1) as success_rate
            FROM jobs WHERE device_id IS NOT NULL
            GROUP BY device_id ORDER BY total_scans DESC
        """).fetchall()
    return [dict(r) for r in rows]


@router.get("/targets")
def by_target(_=_auth):
    with get_db().connection() as conn:
        rows = conn.execute("""
            SELECT target_id as target, COUNT(*) as total_deliveries,
                   ROUND(100.0*SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END)/COUNT(*),1) as success_rate
            FROM jobs WHERE target_id IS NOT NULL
            GROUP BY target_id ORDER BY total_deliveries DESC
        """).fetchall()
    return [dict(r) for r in rows]


@router.get("/hourly")
def hourly(_=_auth):
    with get_db().connection() as conn:
        rows = conn.execute("""
            SELECT CAST(substr(created_at,12,2) AS INTEGER) as hour, COUNT(*) as count
            FROM jobs GROUP BY hour ORDER BY hour
        """).fetchall()
    return [dict(r) for r in rows]
