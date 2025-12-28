from typing import Optional, Dict, Any
from app.core.db import app_cursor
from app.core.security import hash_password, verify_password

def create_user(username: str, email: str, password: str) -> int:
    with app_cursor() as c:
        c.execute("INSERT INTO users(username, email, hashed_password, xp, level) VALUES(?,?,?,0,1)",
                  (username, email, hash_password(password)))
        return c.lastrowid

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with app_cursor() as c:
        c.execute("SELECT id, username, email, hashed_password, is_admin, xp, level FROM users WHERE username=?", (username,))
        row = c.fetchone()
    if not row: return None
    uid, u, e, h, admin, xp, lvl = row
    return {"id": uid, "username": u, "email": e, "hashed_password": h, "is_admin": bool(admin), "xp": xp or 0, "level": lvl or 1}

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with app_cursor() as c:
        c.execute("SELECT id, username, email, is_admin, xp, level FROM users WHERE id=?", (user_id,))
        row = c.fetchone()
    if not row: return None
    uid, u, e, admin, xp, lvl = row
    return {"id": uid, "username": u, "email": e, "is_admin": bool(admin), "xp": xp or 0, "level": lvl or 1}

def verify_user_password(username: str, password: str) -> Optional[Dict[str, Any]]:
    u = get_user_by_username(username)
    if not u: return None
    if not verify_password(password, u["hashed_password"]): return None
    return u

def get_auth_stats() -> dict:
    with app_cursor() as c:
        c.execute("SELECT COUNT(*), SUM(is_admin) FROM users")
        cnt, admins = c.fetchone()
    return {"total_users": cnt or 0, "total_admins": admins or 0}

def get_top_users(limit: int = 10) -> list[Dict[str, Any]]:
    with app_cursor() as c:
        c.execute("""
            SELECT username, xp, level 
            FROM users 
            ORDER BY xp DESC, level DESC 
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
    
    return [dict(r) for r in rows]

def add_xp(user_id: int, xp_amount: int) -> Dict[str, Any]:
    """
    Kullaniciya XP ekler ve level kontrolu yapar.
    """
    with app_cursor() as c:
        # Get current stats
        c.execute("SELECT xp, level FROM users WHERE id=?", (user_id,))
        row = c.fetchone()
        if not row:
            return {"new_level": 1, "xp_gained": 0, "level_up": False}
        
        current_xp = row[0] or 0
        current_level = row[1] or 1
        
        new_xp = current_xp + xp_amount
        # Level calculation: Simple 500 XP = 1 Level
        new_level = 1 + (new_xp // 500)
        
        c.execute("UPDATE users SET xp=?, level=? WHERE id=?", (new_xp, new_level, user_id))
        
    return {"new_level": new_level, "level_up": new_level > current_level, "total_xp": new_xp}

def get_all_students_stats() -> list[Dict[str, Any]]:
    """
    Returns list of all users with their aggregate stats.
    Only returns non-admin users (students).
    """
    with app_cursor() as c:
        c.execute("""
            SELECT 
                u.id, 
                u.username, 
                u.email, 
                u.level, 
                u.xp,
                COUNT(qa.id) as total_quizzes,
                AVG(qa.score) as avg_score
            FROM users u
            LEFT JOIN quiz_attempts qa ON u.id = qa.user_id
            WHERE u.is_admin = 0
            GROUP BY u.id
            ORDER BY u.level DESC, u.xp DESC
        """)
        rows = c.fetchall()
        
    stats = []
    for r in rows:
        stats.append({
            "id": r[0],
            "username": r[1],
            "email": r[2],
            "level": r[3] or 1,
            "xp": r[4] or 0,
            "total_quizzes": r[5] or 0,
            "avg_score": round(r[6] or 0, 1)
        })
    return stats


def get_student_details(user_id: int) -> Dict[str, Any]:
    """
    Returns detailed stats for a specific student:
    - User info
    - Weak topics (< 60% accuracy)
    - Recent quiz attempts (last 10)
    """
    with app_cursor() as c:
        # 1. User Info
        c.execute("SELECT id, username, email, level, xp FROM users WHERE id=?", (user_id,))
        user_row = c.fetchone()
        if not user_row:
            return None
            
        user_info = {
            "id": user_row[0],
            "username": user_row[1],
            "email": user_row[2],
            "level": user_row[3],
            "xp": user_row[4]
        }
        
        # 2. Topic Stats (for weak topics)
        c.execute("""
            SELECT topic, 
                   SUM(total_questions) as total_qs, 
                   SUM(correct_answers) as correct 
            FROM quiz_attempts 
            WHERE user_id=? 
            GROUP BY topic
        """, (user_id,))
        topic_rows = c.fetchall()
        
        weak_topics = []
        topic_stats = []
        for r in topic_rows:
            topic = r[0]
            total_qs = r[1] or 0
            correct = r[2] or 0
            
            # Accuracy calculation based on questions, not attempts
            accuracy = (correct / total_qs * 100) if total_qs > 0 else 0
            accuracy = min(accuracy, 100.0) # Cap at 100
            
            stat = {"topic": topic, "accuracy": round(accuracy, 1), "total": total_qs}
            topic_stats.append(stat)
            
            if accuracy < 60:
                weak_topics.append(stat)
                
        # 3. Recent Activity (Last 10)
        c.execute("""
            SELECT id, topic, difficulty, score, quiz_date 
            FROM quiz_attempts 
            WHERE user_id=? 
            ORDER BY quiz_date DESC 
            LIMIT 10
        """, (user_id,))
        recent_rows = c.fetchall()
        
        recent_activity = []
        for r in recent_rows:
            raw_score = r[3] if r[3] is not None else 0
            # Normalize score: if <= 1.0 assume ratio (0.8 -> 80), if > 1.0 assume percentage (80 -> 80)
            if raw_score <= 1.05: # 1.05 tolerance
                final_score = raw_score * 100
            else:
                final_score = raw_score
            
            # Cap at 100 just in case
            final_score = min(final_score, 100.0)

            recent_activity.append({
                "id": r[0],
                "topic": r[1],
                "difficulty": r[2],
                "score": round(final_score, 1),
                "date": r[4]
            })
            
    return {
        "user": user_info,
        "weak_topics": weak_topics,
        "recent_activity": recent_activity,
        "all_topics": topic_stats
    }
