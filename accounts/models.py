from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    STUDENT = "STUDENT"
    FACULTY = "FACULTY"

    ROLE_CHOICES = [
        (STUDENT, "Student"),
        (FACULTY, "Faculty"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=STUDENT)
    parent_email = models.EmailField(blank=True, null=True)
    face_image = models.ImageField(upload_to="faces/", blank=True, null=True)
