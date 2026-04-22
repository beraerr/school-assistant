from __future__ import annotations

import logging
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
os.environ.setdefault("DEBUG", "false")

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np
from sqlalchemy.orm import Session

from backend.app.core.database import Base, SessionLocal, engine, init_db
from backend.app.core.security import get_password_hash
from backend.app.models.attendance import Attendance
from backend.app.models.grade import Grade
from backend.app.models.risk_score import StudentRiskScore  # noqa: F401 — table registration
from backend.app.models.student import Student
from backend.app.models.teacher import Teacher
from backend.app.models.user import User, UserRole

CLASSES = ["9-A", "9-B", "10-A", "10-B"]
STUDENTS_PER_CLASS = 28   # 4 × 28 = 112 toplam; gerçekçi Türk sınıf büyüklüğü

SUBJECTS = [
    "Matematik",       # Mathematics
    "Türkçe",          # Turkish Language
    "İngilizce",       # English
    "Fen Bilgisi",     # Science
    "Tarih",           # History
    "Coğrafya",        # Geography
    "Kimya",           # Chemistry
    "Beden Eğitimi",   # Physical Education
]

SUBJECT_PASSING_GRADE = 50.0  # 0-100 ölçeğinde geçme notu

TODAY = date.today()
EXAM_DATES = [
    TODAY - timedelta(days=150),  # ~5 ay önce
    TODAY - timedelta(days=120),  # ~4 ay önce
    TODAY - timedelta(days=90),   # ~3 ay önce
    TODAY - timedelta(days=60),   # ~2 ay önce
    TODAY - timedelta(days=30),   # ~1 ay önce
    TODAY - timedelta(days=7),    # son hafta (en güncel)
]

SCHOOL_DAYS_WINDOW = 90   # devamsızlık kaydı için pencere (takvim günü)
SCHOOL_YEAR_DAYS   = 180  # yaklaşık okul yılı uzunluğu

RECENT_ABSENCE_WEIGHT = {"high": 0.70, "medium": 0.40, "low": 0.15}

TEACHER_NAMES = {
    "9-A":  "Ahmet Yıldırım",
    "9-B":  "Fatma Çelik",
    "10-A": "Murat Demir",
    "10-B": "Ayşe Kara",
}

MALE_FIRST = [
    "Ahmet", "Mehmet", "Ali", "Hasan", "Mustafa", "İbrahim", "Yusuf",
    "Ömer", "Can", "Ege", "Kaan", "Berk", "Emre", "Kerem", "Burak",
    "Serkan", "Tarık", "Ozan", "Arda", "Mert", "Furkan", "Umut",
    "Cem", "Berkay", "Alp", "Selim", "Onur", "Barış", "Doruk", "Tolga",
    "Erdem", "Sarp", "Uğur", "Caner", "Yiğit", "Alper", "Taner", "Koray",
    "Deniz", "Enver", "Gökhan", "Haluk", "İlker", "Levent", "Metin",
]
FEMALE_FIRST = [
    "Ayşe", "Fatma", "Zeynep", "Elif", "Selin", "Merve", "İrem",
    "Büşra", "Naz", "Eylül", "Dila", "Başak", "Ece", "Deniz", "Lara",
    "Pınar", "Ceren", "Tuğçe", "Yağmur", "Gizem", "Nil", "Şeyma",
    "Beren", "Esra", "Aslı", "Nazlı", "Damla", "Melis", "Rüya",
    "İpek", "Kübra", "Defne", "Hazal", "Özge", "Beliz", "Seda", "Cansu",
    "Hande", "Figen", "Gül", "Leyla", "Nuray", "Sibel", "Tuba",
]
SURNAMES = [
    "Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Arslan", "Yıldız",
    "Koç", "Aydın", "Öztürk", "Kılıç", "Çetin", "Doğan", "Kurt", "Aslan",
    "Bulut", "Şimşek", "Güneş", "Polat", "Erdoğan", "Tunç", "Akın", "Güler",
    "Çakır", "Kaplan", "Yavuz", "Ateş", "Özdemir", "Duman", "Keskin",
    "Karahan", "Tekin", "Özkan", "Acar", "Güven", "Korkmaz", "Yıldırım",
    "Çiftçi", "Bozkurt", "Kara", "Tok", "Sezer", "Aktaş", "Doğru",
    "Soylu", "Çakmak", "Demirci", "Ercan", "Fidan", "Gündüz",
]

ABILITY_TIERS: List[Tuple] = [
    ("excellent",  0.12, 80, 95),  # %12 — pekiyi öğrenci
    ("good",       0.25, 65, 79),  # %25 — iyi öğrenci
    ("average",    0.33, 50, 64),  # %33 — ortalama
    ("struggling", 0.22, 36, 49),  # %22 — geride kalan
    ("at_risk",    0.08, 20, 35),  # %8  — başarısız risk grubunda
]

ABSENCE_DIST: List[Tuple] = [
    (0,  3,  0.42),   # %42 — mükemmel devam
    (4,  8,  0.31),   # %31 — normal
    (9,  14, 0.16),   # %16 — endişe verici
    (15, 19, 0.08),   # %8  — yüksek risk
    (20, 25, 0.03),   # %3  — kritik / edge case
]

TREND_DIST: List[Tuple] = [
    ("stable",    0.48),
    ("improving", 0.22),
    ("declining", 0.25),
    ("volatile",  0.05),
]

EDGE_PER_CLASS = ["dramatic_decline", "dramatic_rise"]
EDGE_EXTRA = {"9-A": "perfect", "9-B": "chronic_failure"}

def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, round(v, 1)))

def _wchoice(options: List[Tuple]) -> object:
    """Ağırlıklı rastgele seçim. options: [(value, weight), ...]"""
    vals = [o[0] for o in options]
    weights = [o[1] for o in options]
    return random.choices(vals, weights=weights, k=1)[0]

def _sample_absence() -> int:
    """Gerçekçi Türk okul devamsızlık dağılımından örnekle."""
    idx = random.choices(
        range(len(ABSENCE_DIST)),
        weights=[w for _, _, w in ABSENCE_DIST],
        k=1,
    )[0]
    lo, hi, _ = ABSENCE_DIST[idx]
    return random.randint(lo, hi)

def _absence_risk_tier(days: int) -> str:
    if days >= 12:
        return "high"
    if days >= 6:
        return "medium"
    return "low"

def _subject_affinities() -> Dict[str, float]:
    """
    Her öğrenci için ders başına ±bonus üretir.
    2 güçlü ders (+8 ile +15), 2 zayıf ders (-8 ile -15), kalanlar ±5.
    """
    subjects = SUBJECTS.copy()
    random.shuffle(subjects)
    affinities: Dict[str, float] = {}
    for s in subjects[:2]:
        affinities[s] = random.uniform(8, 15)    # güçlü ders
    for s in subjects[2:4]:
        affinities[s] = random.uniform(-15, -8)  # zayıf ders
    for s in subjects[4:]:
        affinities[s] = random.uniform(-5, 5)    # nötr
    return affinities

def _generate_grades(
    ability: float,
    trend: str,
    subject: str,
    affinities: Dict[str, float],
    noise: float = 7.0,
) -> Tuple[float, ...]:
    """
    6 sınav tarihi için not üretir.
    Generates 6 exam grades along the trend arc.

    improving : -15'ten başlar, +10'da biter (6 adımda)
    declining : +10'dan başlar, -14'te biter
    volatile  : yüksek gürültü
    stable    : ability etrafında normal dağılım
    """
    affinity = affinities.get(subject, 0.0)
    base = ability + affinity

    if trend == "improving":
        deltas = [-15, -10, -5, 0, 5, 10]
    elif trend == "declining":
        deltas = [10, 7, 3, -3, -8, -14]
    elif trend == "volatile":
        deltas = [random.gauss(0, 18) for _ in range(6)]
    else:  # stable
        deltas = [0.0] * 6

    return tuple(
        _clamp(base + d + random.gauss(0, noise))
        for d in deltas
    )

def _generate_grades_edge(edge_type: str) -> Tuple[float, ...]:
    """
    Kenar durum notları — 6 sınav dönemi için.
    Edge case grade sequences for 6 exam periods.
    """
    if edge_type == "perfect":
        return tuple(_clamp(random.gauss(92, 3)) for _ in range(6))

    elif edge_type == "chronic_failure":
        return tuple(_clamp(random.gauss(37, 7)) for _ in range(6))

    elif edge_type == "dramatic_decline":
        anchors = [82, 80, 65, 52, 37, 28]
        return tuple(_clamp(random.gauss(a, 5)) for a in anchors)

    elif edge_type == "dramatic_rise":
        anchors = [28, 33, 50, 63, 75, 83]
        return tuple(_clamp(random.gauss(a, 5)) for a in anchors)

    return tuple(_clamp(random.gauss(60, 10)) for _ in range(6))

def _generate_name(sex: str, used: set) -> str:
    pool = MALE_FIRST if sex == "M" else FEMALE_FIRST
    for _ in range(400):
        name = f"{random.choice(pool)} {random.choice(SURNAMES)}"
        if name not in used:
            used.add(name)
            return name
    name = f"Öğrenci {len(used) + 1}"
    used.add(name)
    return name

def _school_days_in_window() -> List[date]:
    """Son SCHOOL_DAYS_WINDOW takvim gününün hafta içi günlerini döndürür."""
    days = []
    for offset in range(SCHOOL_DAYS_WINDOW):
        d = TODAY - timedelta(days=offset)
        if d.weekday() < 5:   # Pzt–Cum
            days.append(d)
    return days

def _attendance_records(
    student_id: int,
    total_absences: int,
    school_days: List[date],
    risk_tier: str = "low",
) -> List[dict]:
    """
    Yıllık devamsızlığı pencereye dağıtır.
    Yüksek-risk öğrencilerin devamsızlıkları son 30 güne yoğunlaşır,
    böylece backend risk endpoint'i doğru tespit eder.
    """
    cutoff = TODAY - timedelta(days=30)
    recent_days = [d for d in school_days if d >= cutoff]
    older_days  = [d for d in school_days if d < cutoff]

    total_window = round(total_absences * len(school_days) / SCHOOL_YEAR_DAYS)
    total_window = min(total_window, len(school_days))

    recent_weight = RECENT_ABSENCE_WEIGHT.get(risk_tier, 0.30)
    recent_abs = min(round(total_window * recent_weight), len(recent_days))
    older_abs  = min(total_window - recent_abs, len(older_days))

    absent_set = (
        set(random.sample(recent_days, recent_abs))
        | set(random.sample(older_days,  older_abs))
    )

    return [
        {
            "student_id": student_id,
            "date": d,
            "status": "absent" if d in absent_set else "present",
        }
        for d in school_days
    ]

def seed(db: Session) -> None:
    random.seed(42)
    np.random.seed(42)

    print("  Mevcut veri temizleniyor / Clearing existing data…")
    for model in [Attendance, Grade, Student, Teacher, User]:
        db.query(model).delete()
    db.commit()

    print("  Öğretmenler oluşturuluyor / Creating teachers…")
    teacher_users: Dict[str, User] = {}

    for cls, tname in TEACHER_NAMES.items():
        t = Teacher(name=tname, class_name=cls)
        db.add(t)
        db.flush()

        u = User(
            username=f"teacher_{cls.lower().replace('-', '')}",
            password_hash=get_password_hash("teacher123"),
            role=UserRole.TEACHER,
            related_id=t.id,
            related_class=cls,
        )
        db.add(u)
        teacher_users[cls] = u

    db.add(User(
        username="principal",
        password_hash=get_password_hash("admin123"),
        role=UserRole.PRINCIPAL,
    ))
    db.flush()

    print("  Öğrenciler, notlar, devamsızlık, kullanıcılar oluşturuluyor…")
    school_days = _school_days_in_window()
    used_names: set = set()
    student_idx = 0

    edge_counts: Dict[str, int] = {}
    tier_counts: Dict[str, int] = {}

    for cls in CLASSES:
        edge_queue: List[str] = list(EDGE_PER_CLASS)  # her sınıfa 2 tane
        if cls in EDGE_EXTRA:
            edge_queue.append(EDGE_EXTRA[cls])

        for slot in range(STUDENTS_PER_CLASS):
            student_idx += 1

            edge_type = edge_queue[slot] if slot < len(edge_queue) else ""

            sex = "M" if student_idx % 2 == 0 else "F"

            if edge_type == "perfect":
                ability, trend, absence_days = 93.0, "stable", 0

            elif edge_type == "chronic_failure":
                ability = random.uniform(22, 32)
                trend   = "declining"
                absence_days = random.randint(12, 18)

            elif edge_type == "dramatic_decline":
                ability = 78.0
                trend   = "stable"   # kendi not üretim fonksiyonu kullanılacak
                absence_days = random.randint(16, 22)

            elif edge_type == "dramatic_rise":
                ability = 32.0
                trend   = "stable"
                absence_days = random.randint(1, 5)

            else:
                tier_label = str(_wchoice([(t[0], t[1]) for t in ABILITY_TIERS]))
                tier = next(t for t in ABILITY_TIERS if t[0] == tier_label)
                ability = random.uniform(tier[2], tier[3])
                trend   = str(_wchoice(TREND_DIST))
                absence_days = _sample_absence()
                tier_counts[tier_label] = tier_counts.get(tier_label, 0) + 1

            affinities   = _subject_affinities()
            risk_tier    = _absence_risk_tier(absence_days)

            if edge_type:
                edge_counts[edge_type] = edge_counts.get(edge_type, 0) + 1

            name = _generate_name(sex, used_names)
            student = Student(
                name=name,
                class_name=cls,
                total_absences=absence_days,
            )
            db.add(student)
            db.flush()

            for subject in SUBJECTS:
                if edge_type in ("perfect", "chronic_failure",
                                 "dramatic_decline", "dramatic_rise"):
                    grades_tuple = _generate_grades_edge(edge_type)
                else:
                    grades_tuple = _generate_grades(ability, trend, subject, affinities)

                for exam_date, grade_val in zip(EXAM_DATES, grades_tuple):
                    db.add(Grade(
                        student_id=student.id,
                        subject=subject,
                        grade=grade_val,
                        date=exam_date,
                    ))

            for rec in _attendance_records(student.id, absence_days, school_days, risk_tier):
                db.add(Attendance(**rec))

            idx = student_idx
            parent_user = User(
                username=f"parent{idx}",
                password_hash=get_password_hash("parent123"),
                role=UserRole.PARENT,
                related_id=student.id,
            )
            db.add(parent_user)
            db.flush()

            db.add(User(
                username=f"student{idx}",
                password_hash=get_password_hash("student123"),
                role=UserRole.STUDENT,
                related_id=student.id,
            ))

            student.parent_id = parent_user.id

        db.commit()
        print(f"    {cls}: {STUDENTS_PER_CLASS} öğrenci kaydedildi.")

    n_students = db.query(Student).count()
    n_grades   = db.query(Grade).count()
    n_attend   = db.query(Attendance).count()
    n_users    = db.query(User).count()

    print()
    print("  Seed tamamlandı / Seed complete")
    print(f"     Öğrenci    : {n_students}")
    print(f"     Not kaydı  : {n_grades}")
    print(f"     Devamsızlık: {n_attend}")
    print(f"     Kullanıcı  : {n_users}")
    print()
    print("  ── Kenar durumlar / Edge cases ──────────────────────────")
    for et, cnt in sorted(edge_counts.items()):
        print(f"     {et:<22}: {cnt} öğrenci")
    print()
    print("  ── Normal öğrenci yetenek dağılımı ──────────────────────")
    for label, cnt in sorted(tier_counts.items()):
        print(f"     {label:<12}: {cnt} öğrenci")
    print()
    print("  ── Demo giriş bilgileri / Demo credentials ──────────────")
    print("  principal                 : admin123")
    for cls, u in teacher_users.items():
        print(f"  {u.username:<25} : teacher123   ({cls})")
    print(f"  parent1 … parent{n_students:<3}       : parent123")
    print(f"  student1 … student{n_students:<3}     : student123")
    print()
    print("  ── Örnek chatbot sorguları ───────────────────────────────")
    print('  • "9-A sınıfının matematik notları geçen aya göre nasıl değişti?"')
    print('  • "Son sınavda 50 altında notu olan öğrenciler kimler?"')
    print('  • "En yüksek devamsızlığa sahip 5 öğrenciyi listele"')
    print('  • "Hangi öğrencilerin matematik notu düşüyor?"')

def main() -> None:
    print(f"Database: {os.getenv('DATABASE_URL', '(settings.py default)')}")
    print("Şema başlatılıyor / Initialising schema…")
    init_db()
    db = SessionLocal()
    try:
        seed(db)
    except Exception as exc:
        db.rollback()
        print(f"\nHATA: Seed başarısız / Seed failed: {exc}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
