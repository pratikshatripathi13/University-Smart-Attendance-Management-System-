from django.urls import path
from .views import register, login_view, logout_view, enroll_face
from django.contrib import admin
...
urlpatterns = [
    path("register/", register, name="register"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("enroll-face/", enroll_face, name="enroll_face"),
    path("admin/", admin.site.urls),

]
