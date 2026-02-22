from django.contrib.admin import AdminSite
from django.urls import path
from django.template.response import TemplateResponse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
import csv

from attendance.models import Course, Enrollment

User = get_user_model()


class SmartCampusAdminSite(AdminSite):
    site_header = "University Smart Attendance - Admin"
    site_title = "Smart Attendance Admin"
    index_title = "Administration"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("import-students/", self.admin_view(self.import_students_view), name="import_students"),
            path("import-enrollments/", self.admin_view(self.import_enrollments_view), name="import_enrollments"),
        ]
        return custom + urls

    def import_students_view(self, request):
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            if not csv_file:
                messages.error(request, "Please choose a CSV file.")
            else:
                decoded = csv_file.read().decode("utf-8").splitlines()
                reader = csv.DictReader(decoded)

                created = 0
                skipped = 0

                with transaction.atomic():
                    for row in reader:
                        username = (row.get("username") or "").strip()
                        email = (row.get("email") or "").strip()
                        password = (row.get("password") or "").strip()

                        if not username or not password:
                            skipped += 1
                            continue

                        if User.objects.filter(username=username).exists():
                            skipped += 1
                            continue

                        User.objects.create_user(
                            username=username,
                            email=email,
                            password=password,
                            role="STUDENT",
                        )
                        created += 1

                messages.success(request, f"Students created: {created}. Skipped: {skipped}.")
        ctx = dict(self.each_context(request))
        return TemplateResponse(request, "admin/import_students.html", ctx)

    def import_enrollments_view(self, request):
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            if not csv_file:
                messages.error(request, "Please choose a CSV file.")
            else:
                decoded = csv_file.read().decode("utf-8").splitlines()
                reader = csv.DictReader(decoded)

                created = 0
                skipped = 0

                with transaction.atomic():
                    for row in reader:
                        course_code = (row.get("course_code") or "").strip()
                        section = (row.get("section") or "").strip()
                        username = (row.get("username") or "").strip()

                        if not course_code or not section or not username:
                            skipped += 1
                            continue

                        try:
                            course = Course.objects.get(code=course_code, section=section)
                            student = User.objects.get(username=username)
                        except Exception:
                            skipped += 1
                            continue

                        if getattr(student, "role", "") != "STUDENT":
                            skipped += 1
                            continue

                        _, was_created = Enrollment.objects.get_or_create(course=course, student=student)
                        if was_created:
                            created += 1
                        else:
                            skipped += 1

                messages.success(request, f"Enrollments created: {created}. Skipped: {skipped}.")
        ctx = dict(self.each_context(request))
        return TemplateResponse(request, "admin/import_enrollments.html", ctx)


admin_site = SmartCampusAdminSite(name="smartcampus_admin")