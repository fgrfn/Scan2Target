"""Statistics API routes."""
import logging
from fastapi import APIRouter
from datetime import datetime, timedelta
from typing import Dict, List
from core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/overview")
async def get_statistics_overview():
    """
    Get comprehensive statistics overview.
    
    Returns:
    - Total scans (all time, today, this week, this month)
    - Success rate
    - Most used scanner
    - Most used target
    - Most used profile
    - Average scans per day
    - File size statistics
    """
    db = get_db()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Total scans
        cursor.execute("SELECT COUNT(*) as total FROM jobs WHERE job_type = 'scan'")
        total_scans = cursor.fetchone()['total']
        
        # Today's scans
        today = datetime.now().date()
        cursor.execute("""
            SELECT COUNT(*) as today 
            FROM jobs 
            WHERE job_type = 'scan' 
            AND date(created_at) = date('now')
        """)
        today_scans = cursor.fetchone()['today']
        
        # This week's scans
        cursor.execute("""
            SELECT COUNT(*) as week 
            FROM jobs 
            WHERE job_type = 'scan' 
            AND date(created_at) >= date('now', '-7 days')
        """)
        week_scans = cursor.fetchone()['week']
        
        # This month's scans
        cursor.execute("""
            SELECT COUNT(*) as month 
            FROM jobs 
            WHERE job_type = 'scan' 
            AND date(created_at) >= date('now', 'start of month')
        """)
        month_scans = cursor.fetchone()['month']
        
        # Success rate
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful
            FROM jobs 
            WHERE job_type = 'scan'
        """)
        success_data = cursor.fetchone()
        success_rate = (success_data['successful'] / success_data['total'] * 100) if success_data['total'] > 0 else 0
        
        # Most used scanner
        cursor.execute("""
            SELECT j.device_id, d.name, COUNT(*) as count 
            FROM jobs j
            LEFT JOIN devices d ON j.device_id = d.id
            WHERE j.job_type = 'scan' AND j.device_id IS NOT NULL
            GROUP BY j.device_id 
            ORDER BY count DESC 
            LIMIT 1
        """)
        most_used_scanner = cursor.fetchone()
        
        # Most used target
        cursor.execute("""
            SELECT j.target_id, t.name, COUNT(*) as count 
            FROM jobs j
            LEFT JOIN targets t ON j.target_id = t.id
            WHERE j.job_type = 'scan' AND j.target_id IS NOT NULL
            GROUP BY j.target_id 
            ORDER BY count DESC 
            LIMIT 1
        """)
        most_used_target = cursor.fetchone()
        
        # Daily average (based on days with actual activity or days since first scan)
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT date(created_at)) as active_days,
                julianday('now') - julianday(MIN(date(created_at))) + 1 as days_since_first
            FROM jobs 
            WHERE job_type = 'scan'
        """)
        avg_data = cursor.fetchone()
        
        # Use days since first scan if available, otherwise default to active days
        if avg_data['total'] > 0 and avg_data['days_since_first'] > 0:
            avg_per_day = avg_data['total'] / avg_data['days_since_first']
        elif avg_data['active_days'] > 0:
            avg_per_day = avg_data['total'] / avg_data['active_days']
        else:
            avg_per_day = 0
        
        return {
            "total_scans": total_scans,
            "today_scans": today_scans,
            "week_scans": week_scans,
            "month_scans": month_scans,
            "success_rate": round(success_rate, 1),
            "most_used_scanner": most_used_scanner['name'] if most_used_scanner and most_used_scanner['name'] else (most_used_scanner['device_id'] if most_used_scanner else None),
            "most_used_target": most_used_target['name'] if most_used_target and most_used_target['name'] else (most_used_target['target_id'] if most_used_target else None),
            "average_scans_per_day": round(avg_per_day, 1)
        }


@router.get("/timeline")
async def get_scan_timeline(days: int = 30):
    """
    Get scan activity timeline.
    
    Args:
        days: Number of days to include (default: 30)
    
    Returns:
        Daily scan counts for the specified period
    """
    db = get_db()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                date(created_at) as date,
                COUNT(*) as count,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM jobs 
            WHERE job_type = 'scan'
            AND date(created_at) >= date('now', ? || ' days')
            GROUP BY date(created_at)
            ORDER BY date(created_at) DESC
        """, (f'-{days}',))
        
        timeline = []
        for row in cursor.fetchall():
            timeline.append({
                "date": row['date'],
                "total": row['count'],
                "successful": row['successful'],
                "failed": row['failed']
            })
        
        return timeline


@router.get("/scanners")
async def get_scanner_statistics():
    """Get usage statistics per scanner."""
    db = get_db()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                j.device_id,
                COALESCE(d.name, j.device_id) as scanner_name,
                COUNT(*) as total_scans,
                SUM(CASE WHEN j.status = 'completed' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN j.status = 'failed' THEN 1 ELSE 0 END) as failed,
                MAX(j.created_at) as last_used
            FROM jobs j
            LEFT JOIN devices d ON j.device_id = d.id
            WHERE j.job_type = 'scan' AND j.device_id IS NOT NULL
            GROUP BY j.device_id
            ORDER BY total_scans DESC
        """)
        
        stats = []
        for row in cursor.fetchall():
            stats.append({
                "scanner": row['scanner_name'],
                "total_scans": row['total_scans'],
                "successful": row['successful'],
                "failed": row['failed'],
                "success_rate": round((row['successful'] / row['total_scans'] * 100), 1) if row['total_scans'] > 0 else 0,
                "last_used": row['last_used']
            })
        
        return stats


@router.get("/targets")
async def get_target_statistics():
    """Get usage statistics per target."""
    db = get_db()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                j.target_id,
                COALESCE(t.name, j.target_id) as target_name,
                COUNT(*) as total_deliveries,
                SUM(CASE WHEN j.status = 'completed' AND j.message IS NULL THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN j.status = 'completed' AND j.message IS NOT NULL THEN 1 ELSE 0 END) as delivery_failed,
                SUM(CASE WHEN j.status = 'failed' THEN 1 ELSE 0 END) as failed,
                MAX(j.created_at) as last_used
            FROM jobs j
            LEFT JOIN targets t ON j.target_id = t.id
            WHERE j.job_type = 'scan' AND j.target_id IS NOT NULL
            GROUP BY j.target_id
            ORDER BY total_deliveries DESC
        """)
        
        stats = []
        for row in cursor.fetchall():
            stats.append({
                "target": row['target_name'],
                "total_deliveries": row['total_deliveries'],
                "successful": row['successful'],
                "delivery_failed": row['delivery_failed'],
                "failed": row['failed'],
                "success_rate": round((row['successful'] / row['total_deliveries'] * 100), 1) if row['total_deliveries'] > 0 else 0,
                "last_used": row['last_used']
            })
        
        return stats


@router.get("/hourly")
async def get_hourly_distribution():
    """Get scan distribution by hour of day (in local time)."""
    db = get_db()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # SQLite stores times as UTC, so we need to convert to local time
        # Using 'localtime' modifier to convert from UTC to local time
        cursor.execute("""
            SELECT 
                strftime('%H', created_at, 'localtime') as hour,
                COUNT(*) as count
            FROM jobs 
            WHERE job_type = 'scan'
            GROUP BY hour
            ORDER BY hour
        """)
        
        hourly = {}
        for row in cursor.fetchall():
            hourly[int(row['hour'])] = row['count']
        
        # Fill in missing hours with 0
        result = []
        for h in range(24):
            result.append({
                "hour": h,
                "count": hourly.get(h, 0)
            })
        
        return result


@router.delete("/targets/{target_name}")
async def delete_target_statistics(target_name: str):
    """
    Delete all job statistics for a specific target.
    This removes all delivery history for the target but keeps scan files.
    
    The target_name can be either:
    - An actual target name (e.g., "Unraid")
    - A target_id (e.g., "target_1764518509353")
    """
    from fastapi import HTTPException
    from pathlib import Path
    db = get_db()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Find all jobs that match either by target name or target_id
            cursor.execute("""
                SELECT j.id, j.file_path
                FROM jobs j
                LEFT JOIN targets t ON j.target_id = t.id
                WHERE j.job_type = 'scan' 
                AND (t.name = ? OR j.target_id = ?)
            """, (target_name, target_name))
            
            jobs_to_delete = cursor.fetchall()
            
            # Delete associated scan files
            for job in jobs_to_delete:
                if job['file_path']:
                    file_path = Path(job['file_path'])
                    if file_path.exists():
                        try:
                            file_path.unlink()
                            logger.debug(f"✓ Deleted scan file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Warning: Failed to delete file {file_path}: {e}")
            
            # Delete jobs from database
            cursor.execute("""
                DELETE FROM jobs 
                WHERE job_type = 'scan' 
                AND id IN (
                    SELECT j.id 
                    FROM jobs j
                    LEFT JOIN targets t ON j.target_id = t.id
                    WHERE t.name = ? OR j.target_id = ?
                )
            """, (target_name, target_name))
            
            deleted_count = cursor.rowcount
            
            return {
                "status": "success",
                "message": f"Deleted {deleted_count} job entries for target '{target_name}'",
                "deleted_count": deleted_count
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
