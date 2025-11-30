"""Statistics API routes."""
from fastapi import APIRouter
from datetime import datetime, timedelta
from typing import Dict, List
from app.core.database import get_db

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
                SUM(CASE WHEN status = 'completed' AND message IS NULL THEN 1 ELSE 0 END) as successful
            FROM jobs 
            WHERE job_type = 'scan'
        """)
        success_data = cursor.fetchone()
        success_rate = (success_data['successful'] / success_data['total'] * 100) if success_data['total'] > 0 else 0
        
        # Most used scanner
        cursor.execute("""
            SELECT device_id, COUNT(*) as count 
            FROM jobs 
            WHERE job_type = 'scan' AND device_id IS NOT NULL
            GROUP BY device_id 
            ORDER BY count DESC 
            LIMIT 1
        """)
        most_used_scanner = cursor.fetchone()
        
        # Most used target
        cursor.execute("""
            SELECT target_id, COUNT(*) as count 
            FROM jobs 
            WHERE job_type = 'scan' AND target_id IS NOT NULL
            GROUP BY target_id 
            ORDER BY count DESC 
            LIMIT 1
        """)
        most_used_target = cursor.fetchone()
        
        # Daily average (last 30 days)
        cursor.execute("""
            SELECT COUNT(*) / 30.0 as avg_per_day
            FROM jobs 
            WHERE job_type = 'scan' 
            AND date(created_at) >= date('now', '-30 days')
        """)
        avg_per_day = cursor.fetchone()['avg_per_day']
        
        return {
            "total_scans": total_scans,
            "today_scans": today_scans,
            "week_scans": week_scans,
            "month_scans": month_scans,
            "success_rate": round(success_rate, 1),
            "most_used_scanner": most_used_scanner['device_id'] if most_used_scanner else None,
            "most_used_target": most_used_target['target_id'] if most_used_target else None,
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
                SUM(CASE WHEN status = 'completed' AND message IS NULL THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'failed' OR message IS NOT NULL THEN 1 ELSE 0 END) as failed
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
                device_id,
                COUNT(*) as total_scans,
                SUM(CASE WHEN status = 'completed' AND message IS NULL THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                MAX(created_at) as last_used
            FROM jobs 
            WHERE job_type = 'scan' AND device_id IS NOT NULL
            GROUP BY device_id
            ORDER BY total_scans DESC
        """)
        
        stats = []
        for row in cursor.fetchall():
            stats.append({
                "scanner": row['device_id'],
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
                target_id,
                COUNT(*) as total_deliveries,
                SUM(CASE WHEN status = 'completed' AND message IS NULL THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN message IS NOT NULL THEN 1 ELSE 0 END) as failed,
                MAX(created_at) as last_used
            FROM jobs 
            WHERE job_type = 'scan' AND target_id IS NOT NULL
            GROUP BY target_id
            ORDER BY total_deliveries DESC
        """)
        
        stats = []
        for row in cursor.fetchall():
            stats.append({
                "target": row['target_id'],
                "total_deliveries": row['total_deliveries'],
                "successful": row['successful'],
                "failed": row['failed'],
                "success_rate": round((row['successful'] / row['total_deliveries'] * 100), 1) if row['total_deliveries'] > 0 else 0,
                "last_used": row['last_used']
            })
        
        return stats


@router.get("/hourly")
async def get_hourly_distribution():
    """Get scan distribution by hour of day."""
    db = get_db()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                strftime('%H', created_at) as hour,
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
