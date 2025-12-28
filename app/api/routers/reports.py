
from fastapi import APIRouter, Depends, HTTPException, Response
from app.api.deps import get_current_user, on_start_app_db
from app.domain.repositories.users_repo import get_student_details
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os

router = APIRouter(prefix="/reports", tags=["reports"])

# Register a font that supports Turkish characters if possible
# Since we can't easily guarantee a font file exists in a specific path on Windows without knowing the system,
# we will try to safe basic fonts or use a bundled one.
# For now, we will use 'Helvetica' which has limited TR support, or try to register Arial if available.
# A better approach is to rely on standard fonts but encode properly.
# ReportLab's standard fonts (Helvetica) don't support UTF-8 chars like 'ğ', 'ş' well without explicit encoding.
# We will try to load Arial from standard Windows fonts.

FONT_PATH = "C:\\Windows\\Fonts\\arial.ttf"
try:
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont('Arial', FONT_PATH))
        START_FONT = 'Arial'
    else:
        START_FONT = 'Helvetica' # Fallback
except:
    START_FONT = 'Helvetica'

@router.get("/student/{user_id}/pdf")
def generate_student_report_pdf(
    user_id: int,
    current_user: dict = Depends(get_current_user), # Any admin or the user themselves could potentially download
):
    """
    Generates a PDF report card for the student.
    """
    # 1. Security Check: Only Admin or the User themselves
    if not current_user["is_admin"] and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # 2. Fetch Data
    details = get_student_details(user_id)
    if not details:
        raise HTTPException(status_code=404, detail="Student not found")

    user = details["user"]
    weak_topics = details["weak_topics"]
    recent = details["recent_activity"]
    all_topics = details["all_topics"]

    # 3. Generate PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # --- HEADER ---
    p.setFillColor(colors.darkblue)
    p.rect(0, height - 100, width, 100, fill=1)
    
    p.setFillColor(colors.white)
    p.setFont(START_FONT, 24)
    p.drawString(50, height - 60, "ÖĞRENCİ KARNESİ")
    
    p.setFont(START_FONT, 14)
    p.drawString(50, height - 85, f"AI-Powered Learning System")

    # --- STUDENT INFO ---
    p.setFillColor(colors.black)
    p.setFont(START_FONT, 16)
    p.drawString(50, height - 150, f"Öğrenci: {user['username']}")
    
    p.setFont(START_FONT, 12)
    p.drawString(50, height - 170, f"E-posta: {user['email']}")
    p.drawString(50, height - 190, f"Seviye: {user['level']}  |  XP: {user['xp']}")

    # --- SUMMARY STATS ---
    # Calculate average score derived from all topics roughly or recent
    # Let's use the one from details if available, otherwise calc from topics
    total_q = sum(t['total'] for t in all_topics)
    total_acc = sum(t['accuracy'] * t['total'] for t in all_topics) / total_q if total_q > 0 else 0
    
    p.setStrokeColor(colors.lightgrey)
    p.rect(50, height - 260, 500, 50, fill=0)
    
    p.setFont(START_FONT, 12)
    p.drawString(70, height - 240, "Genel Ortalama")
    p.setFont(START_FONT, 20)
    
    if total_acc >= 70: p.setFillColor(colors.green)
    elif total_acc >= 50: p.setFillColor(colors.orange)
    else: p.setFillColor(colors.red)
        
    p.drawString(200, height - 240, f"%{total_acc:.1f}")
    
    p.setFillColor(colors.black)
    p.setFont(START_FONT, 12)
    p.drawString(350, height - 240, f"Çözülen Soru: {total_q}")

    # --- WEAK TOPICS ---
    y = height - 320
    p.setFont(START_FONT, 14)
    p.drawString(50, y, "Geliştirilmesi Gereken Konular")
    y -= 30
    
    if weak_topics:
        p.setFont(START_FONT, 12)
        p.setFillColor(colors.red)
        for t in weak_topics:
            p.drawString(70, y, f"• {t['topic']} (Başarı: %{t['accuracy']})")
            y -= 20
    else:
        p.setFont(START_FONT, 12)
        p.setFillColor(colors.green)
        p.drawString(70, y, "Harika! Şu an kritik bir zayıf konu bulunmuyor.")
        y -= 20

    # --- RECENT ACTIVITY ---
    y -= 30
    p.setFillColor(colors.black)
    p.setFont(START_FONT, 14)
    p.drawString(50, y, "Son Aktiviteler")
    y -= 20
    
    # Table Header
    p.setFont(START_FONT, 10)
    p.setFillColor(colors.grey)
    p.drawString(50, y, "Tarih")
    p.drawString(200, y, "Konu")
    p.drawString(400, y, "Seviye")
    p.drawString(500, y, "Puan")
    y -= 10
    p.line(50, y, 550, y)
    y -= 20
    
    p.setFillColor(colors.black)
    for r in recent:
        if y < 50: # New page if needed, simplified for now
            break
        p.drawString(50, y, r['date'][:10])
        p.drawString(200, y, r['topic'][:25])
        p.drawString(400, y, r['difficulty'])
        
        score = r['score']
        if score >= 70: p.setFillColor(colors.green)
        elif score >= 50: p.setFillColor(colors.orange)
        else: p.setFillColor(colors.red)
        p.drawString(500, y, str(score))
        
        p.setFillColor(colors.black)
        y -= 20

    # --- FOOTER ---
    p.setFont(START_FONT, 10)
    p.setFillColor(colors.grey)
    p.drawString(50, 30, "Bu belge yapay zeka tarafından oluşturulmuştur.")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return Response(content=buffer.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=report_{user['username']}.pdf"})
