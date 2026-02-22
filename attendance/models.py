from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class Course(models.Model):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=120)
    section = models.CharField(max_length=20)
    faculty = models.ForeignKey(User, on_delete=models.CASCADE, related_name="courses")

    def __str__(self):
        return f"{self.code}-{self.section} {self.name}"

class Enrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")

    class Meta:
        unique_together = ("course", "student")

class AttendanceSession(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sessions")
    started_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="started_sessions")
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField()
    otp = models.CharField(max_length=10)
    is_closed = models.BooleanField(default=False)
    expected_count = models.PositiveIntegerField(default=0)

    def is_active(self):
        now = timezone.now()
        return (not self.is_closed) and (self.start_time <= now <= self.end_time)

   

class AttendanceRecord(models.Model):
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="records")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendance_records")
    marked_at = models.DateTimeField(default=timezone.now)
    selfie = models.ImageField(upload_to="selfies/", null=True, blank=True)
    face_verified = models.BooleanField(default=False)

    class Meta:
        unique_together = ("session", "student")
