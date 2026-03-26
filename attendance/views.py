import csv
import io
import random
import string
from datetime import timedelta
import base64
import uuid
from django.core.files.base import ContentFile

from django.contrib import messages
from django.db import transaction

from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import transaction

from .models import Course, Enrollment, AttendanceSession, AttendanceRecord
from .forms import StartSessionForm, MarkAttendanceForm
from .face_utils import verify_faces

User = get_user_model()


# =========================
# UTIL
# =========================

def _generate_otp(length=6):
    return "".join(random.choices(string.digits, k=length))


# =========================
# DASHBOARD ROUTER
# =========================

@login_required
def dashboard(request):
    if request.user.role == "FACULTY":
        return redirect("faculty_dashboard")
    return redirect("student_dashboard")


# =========================
# FACULTY DASHBOARD
# =========================

@login_required
def faculty_dashboard(request):
    if request.user.role != "FACULTY":
        return HttpResponseForbidden("Faculty only")

    courses = Course.objects.filter(faculty=request.user)
    sessions = AttendanceSession.objects.filter(
        course__faculty=request.user
    ).order_by("-start_time")

    return render(request, "attendance/faculty_dashboard.html", {
        "courses": courses,
        "sessions": sessions
    })


# =========================
# START SESSION
# =========================

@login_required
def start_session(request):
    if request.user.role != "FACULTY":
        return HttpResponseForbidden("Faculty only")

    if request.method == "POST":
        form = StartSessionForm(request.POST, faculty=request.user)

        if form.is_valid():
            course_id = form.cleaned_data["course_id"]
            minutes = form.cleaned_data["minutes"]
            expected_count = form.cleaned_data.get("expected_count") or 0

            course = get_object_or_404(
                Course,
                id=course_id,
                faculty=request.user
            )

            AttendanceSession.objects.create(
                course=course,
                started_by=request.user,
                start_time=timezone.now(),
                end_time=timezone.now() + timedelta(minutes=minutes),
                otp=_generate_otp(),
                expected_count=expected_count,
                is_closed=False
            )

            return redirect("faculty_dashboard")
    else:
        form = StartSessionForm(faculty=request.user)

    return render(request, "attendance/start_session.html", {"form": form})


# =========================
# STUDENT DASHBOARD
# =========================

@login_required
def student_dashboard(request):
    if request.user.role != "STUDENT":
        return HttpResponseForbidden("Student only")

    enrollments = Enrollment.objects.filter(
        student=request.user
    ).select_related("course")

    course_ids = enrollments.values_list("course_id", flat=True)

    sessions = AttendanceSession.objects.filter(
        course_id__in=course_ids
    ).order_by("-start_time")

    return render(request, "attendance/student_dashboard.html", {
        "enrollments": enrollments,
        "sessions": sessions
    })


# =========================
# MARK ATTENDANCE
# =========================
@login_required
def mark_attendance(request, session_id):
    if request.user.role != "STUDENT":
        return HttpResponseForbidden("Student only")

    if not request.user.face_image:
        return redirect("/accounts/enroll-face/")

    session = get_object_or_404(AttendanceSession, id=session_id)

    if not Enrollment.objects.filter(course=session.course, student=request.user).exists():
        return HttpResponseForbidden("Not enrolled")

    if not session.is_active():
        return render(request, "attendance/mark_attendance.html", {
            "session": session,
            "form": MarkAttendanceForm(),
            "error": "Session not active."
        })

    if request.method == "POST":
        form = MarkAttendanceForm(request.POST)
        if form.is_valid():
            if form.cleaned_data["otp"] != session.otp:
                return render(request, "attendance/mark_attendance.html", {
                    "session": session,
                    "form": form,
                    "error": "Invalid OTP."
                })

            data_url = form.cleaned_data["selfie_data"]

            if "," in data_url:
                _, b64 = data_url.split(",", 1)
            else:
                b64 = data_url

            try:
                img_bytes = base64.b64decode(b64)
            except Exception:
                return render(request, "attendance/mark_attendance.html", {
                    "session": session,
                    "form": form,
                    "error": "Invalid camera image. Please capture again."
                })
            

            record, _ = AttendanceRecord.objects.update_or_create(
                session=session,
                student=request.user,
                defaults={"face_verified": False},
            )

            filename = f"capture_{request.user.username}_{uuid.uuid4().hex}.jpg"
            record.selfie.save(filename, ContentFile(img_bytes), save=True)

            ok, distance = verify_faces(request.user.face_image.path, record.selfie.path)
            record.face_verified = ok
            record.save()

            if not ok:
                if distance == -1.0:
                    err_msg = "No face detected. Ensure good lighting and look straight at camera."
                else:
                    err_msg = f"Face not matched (distance={distance:.3f}). Retake with better lighting."
                return render(request, "attendance/mark_attendance.html", {
                    "session": session,
                    "form": MarkAttendanceForm(),
                    "error": err_msg
                })
            

            return redirect("student_dashboard")
    else:
        form = MarkAttendanceForm()

    return render(request, "attendance/mark_attendance.html", {"session": session, "form": form})
# =========================
# CLOSE SESSION
# =========================
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from .models import Enrollment, AttendanceSession, AttendanceRecord

@login_required
def close_session(request, session_id):
    if request.user.role != "FACULTY":
        return HttpResponseForbidden("Faculty only")

    session = get_object_or_404(
        AttendanceSession,
        id=session_id,
        course__faculty=request.user
    )

    session.is_closed = True
    session.save()

    enrolled = Enrollment.objects.filter(course=session.course).select_related("student")

    verified_qs = AttendanceRecord.objects.filter(
        session=session,
        face_verified=True
    ).select_related("student")

    present_ids = set(verified_qs.values_list("student_id", flat=True))

    present_students = [r.student for r in verified_qs]
    absentees = [e.student for e in enrolled if e.student_id not in present_ids]

    present_count = len(present_students)
    absent_count = len(absentees)
    total_enrolled = enrolled.count()

    mismatch_note = ""
    if session.expected_count and present_count != session.expected_count:
        mismatch_note = f"WARNING: Expected count={session.expected_count}, Verified marked={present_count}"

    return render(request, "attendance/close_summary.html", {
        "session": session,
        "present_students": present_students,
        "absentees": absentees,
        "present_count": present_count,
        "absent_count": absent_count,
        "total_enrolled": total_enrolled,
        "mismatch_note": mismatch_note,
        "session_date": session.start_time.date(),
        "day_name": session.start_time.strftime("%A"),
    })
    
# =========================
# CSV IMPORT
# =========================

@login_required
def import_data(request):
    if request.user.role != "FACULTY":
        return HttpResponseForbidden("Faculty only")

    User = get_user_model()

    if request.method != "POST":
        return render(request, "attendance/import_data.html")

    mode = request.POST.get("mode")
    f = request.FILES.get("csv_file")

    if not f:
        return render(request, "attendance/import_data.html", {"message": "Please choose a CSV file.", "ok": False})

    raw = f.read()

    text = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        return render(request, "attendance/import_data.html", {"message": "CSV encoding not supported. Save CSV as UTF-8.", "ok": False})

    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        return render(request, "attendance/import_data.html", {"message": "CSV seems empty / invalid.", "ok": False})

    try:
        with transaction.atomic():
            if mode == "students":
                required = {"username", "email", "password", "name"}
                cols = set([c.strip().lower() for c in reader.fieldnames])

                if not required.issubset(cols):
                    return render(request, "attendance/import_data.html", {
                        "message": "Students CSV must have columns: username,email,password,name",
                        "ok": False
                    })

                created = 0
                updated = 0

                for row in reader:
                    username = (row.get("username") or "").strip()
                    email = (row.get("email") or "").strip()
                    password = (row.get("password") or "").strip()
                    name = (row.get("name") or "").strip()

                    if not username or not password:
                        continue

                    user = User.objects.filter(username=username).first()

                    if user is None:
                        user = User.objects.create_user(username=username, email=email, password=password)
                        created += 1
                    else:
                        updated += 1
                        if email:
                            user.email = email

                    user.role = "STUDENT"
                    if name:
                        user.first_name = name
                    user.save()

                return render(request, "attendance/import_data.html", {
                    "message": f"Students imported: created={created}, updated={updated}. Now upload Enrollment CSV.",
                    "ok": True
                })

            elif mode == "enrollments":
                required = {"course_code", "section", "username", "course_name"}
                cols = set([c.strip().lower() for c in reader.fieldnames])

                if not required.issubset(cols):
                    return render(request, "attendance/import_data.html", {
                        "message": "Enrollment CSV must have columns: course_code,section,course_name,username",
                        "ok": False
                    })

                created_courses = 0
                created_enrollments = 0
                skipped = 0

                for row in reader:
                    code = (row.get("course_code") or "").strip()
                    section = (row.get("section") or "").strip()
                    course_name = (row.get("course_name") or "").strip()
                    username = (row.get("username") or "").strip()

                    if not code or not section or not username:
                        skipped += 1
                        continue

                    student = User.objects.filter(username=username).first()
                    if student is None:
                        skipped += 1
                        continue

                    course = Course.objects.filter(code=code, section=section, faculty=request.user).first()
                    if course is None:
                        course = Course.objects.create(
                            code=code,
                            section=section,
                            name=course_name or code,
                            faculty=request.user
                        )
                        created_courses += 1

                    obj, created_flag = Enrollment.objects.get_or_create(course=course, student=student)
                    if created_flag:
                        created_enrollments += 1

                return render(request, "attendance/import_data.html", {
                    "message": f"Enrollments imported: courses_created={created_courses}, enrollments_created={created_enrollments}, skipped={skipped}.",
                    "ok": True
                })

            else:
                return render(request, "attendance/import_data.html", {"message": "Invalid import mode.", "ok": False})

    except Exception as e:
        return render(request, "attendance/import_data.html", {"message": f"Import failed: {e}", "ok": False})
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from collections import defaultdict
@login_required
def history_view(request):
    if request.user.role != "FACULTY":
        return HttpResponseForbidden("Faculty only")

    date_str = request.GET.get("date")
    if date_str:
        try:
            target_date = timezone.datetime.fromisoformat(date_str).date()
        except Exception:
            target_date = timezone.localdate()
    else:
        target_date = timezone.localdate()

    sessions = AttendanceSession.objects.filter(
        course__faculty=request.user,
        start_time__date=target_date
    ).select_related("course").order_by("-start_time")

    rows = []
    for s in sessions:
        present = AttendanceRecord.objects.filter(session=s, face_verified=True).count()
        enrolled = Enrollment.objects.filter(course=s.course).count()
        rows.append({
            "session": s,
            "present": present,
            "absent": max(enrolled - present, 0),
            "enrolled": enrolled
        })

    return render(request, "attendance/history.html", {
        "title": "History",
        "nav": "history",
        "target_date": target_date,
        "rows": rows
    })
@login_required
def analytics_view(request):
    if request.user.role != "FACULTY":
        return HttpResponseForbidden("Faculty only")

    sessions = AttendanceSession.objects.filter(course__faculty=request.user).select_related("course")

    by_course = defaultdict(lambda: {"total_sessions": 0, "total_present": 0, "total_enrolled": 0})
    for s in sessions:
        present = AttendanceRecord.objects.filter(session=s, face_verified=True).count()
        enrolled = Enrollment.objects.filter(course=s.course).count()
        by_course[str(s.course)]["total_sessions"] += 1
        by_course[str(s.course)]["total_present"] += present
        by_course[str(s.course)]["total_enrolled"] += enrolled

    course_cards = []
    for k, v in by_course.items():
        avg = 0
        if v["total_sessions"] > 0 and v["total_enrolled"] > 0:
            avg = round((v["total_present"] / (v["total_sessions"] * v["total_enrolled"])) * 100, 1)
        course_cards.append({"course": k, **v, "avg_percent": avg})

    course_cards.sort(key=lambda x: x["avg_percent"], reverse=True)

    return render(request, "attendance/analytics.html", {
        "title": "Analytics",
        "nav": "analytics",
        "course_cards": course_cards
    })

from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
@require_http_methods(["GET", "POST"])
def faculty_manual_mark(request, session_id):
    if request.user.role != "FACULTY":
        return HttpResponseForbidden("Faculty only")

    session = get_object_or_404(
        AttendanceSession,
        id=session_id,
        course__faculty=request.user
    )

    enrolled = Enrollment.objects.filter(course=session.course).select_related("student").order_by("student__username")

    if request.method == "POST":
        present_ids = request.POST.getlist("present_ids")
        present_ids = set(int(x) for x in present_ids if x.isdigit())

        for e in enrolled:
            AttendanceRecord.objects.update_or_create(
                session=session,
                student=e.student,
                defaults={
                    "face_verified": (e.student_id in present_ids),
                }
            )

        return redirect("close_session", session_id=session.id)

    verified_ids = set(
        AttendanceRecord.objects.filter(session=session, face_verified=True)
        .values_list("student_id", flat=True)
    )

    return render(request, "attendance/manual_mark.html", {
        "session": session,
        "enrolled": enrolled,
        "verified_ids": verified_ids
    })
