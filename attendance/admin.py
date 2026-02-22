import csv
from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import render, redirect
from django.urls import path

from .models import Course, Enrollment, AttendanceSession, AttendanceRecord

User = get_user_model()


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField()


class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "section", "name", "faculty")
    search_fields = ("code", "section", "name")
    list_filter = ("section", "faculty")


class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("course", "student")
    search_fields = ("course__code", "course__section", "student__username")


class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("course", "start_time", "end_time", "otp", "is_closed")
    list_filter = ("is_closed", "course")


class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("session", "student", "marked_at", "face_verified")
    list_filter = ("face_verified", "session__course")
    search_fields = ("student__username",)


class SmartCampusAdminSite(admin.AdminSite):
    site_header = "Smart Campus Admin"
    site_title = "Smart Campus"
    index_title = "Administration"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("import-students/", self.admin_view(self.import_students), name="import_students"),
            path("import-enrollments/", self.admin_view(self.import_enrollments), name="import_enrollments"),
        ]
        return custom + urls

    def import_students(self, request):
        if request.method == "POST":
            form = CSVUploadForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]
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

                messages.success(request, f"Imported: {created} students | Skipped: {skipped}")
                return redirect("/admin/")

        else:
            form = CSVUploadForm()

        return render(request, "admin/import_students.html", {"form": form})

    def import_enrollments(self, request):
        if request.method == "POST":
            form = CSVUploadForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]
                decoded = csv_file.read().decode("utf-8").splitlines()
                reader = csv.DictReader(decoded)

                created = 0
                skipped = 0

                with transaction.atomic():
                    for row in reader:
                        code = (row.get("course_code") or "").strip()
                        section = (row.get("section") or "").strip()
                        username = (row.get("username") or "").strip()

                        if not code or not section or not username:
                            skipped += 1
                            continue

                        try:
                            course = Course.objects.get(code=code, section=section)
                            student = User.objects.get(username=username)
                            Enrollment.objects.get_or_create(course=course, student=student)
                            created += 1
                        except Exception:
                            skipped += 1

                messages.success(request, f"Imported: {created} enrollments | Skipped: {skipped}")
                return redirect("/admin/")

        else:
            form = CSVUploadForm()

        return render(request, "admin/import_enrollments.html", {"form": form})


smart_admin_site = SmartCampusAdminSite(name="smart_admin")

smart_admin_site.register(Course, CourseAdmin)
smart_admin_site.register(Enrollment, EnrollmentAdmin)
smart_admin_site.register(AttendanceSession, AttendanceSessionAdmin)
smart_admin_site.register(AttendanceRecord, AttendanceRecordAdmin)