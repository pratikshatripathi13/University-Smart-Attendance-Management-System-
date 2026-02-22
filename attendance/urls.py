from django.urls import path
from .views import dashboard, faculty_dashboard, start_session, student_dashboard, mark_attendance, close_session
from django.urls import path
from .views import import_data
from .views import history_view, analytics_view, faculty_manual_mark





from django.urls import path
from .views import dashboard, faculty_dashboard, start_session, student_dashboard, mark_attendance, close_session, import_data

urlpatterns = [
    path("dashboard/", dashboard, name="dashboard"),
    path("faculty/", faculty_dashboard, name="faculty_dashboard"),
    path("faculty/start-session/", start_session, name="start_session"),
    path("faculty/close-session/<int:session_id>/", close_session, name="close_session"),
    path("student/", student_dashboard, name="student_dashboard"),
    path("student/mark/<int:session_id>/", mark_attendance, name="mark_attendance"),

    path("faculty/import-data/", import_data, name="import_data"),
]
from django.urls import path

urlpatterns = [
    path("dashboard/", dashboard, name="dashboard"),

    path("faculty/", faculty_dashboard, name="faculty_dashboard"),
    path("faculty/start-session/", start_session, name="start_session"),
    path("faculty/close-session/<int:session_id>/", close_session, name="close_session"),
    path("faculty/import-data/", import_data, name="import_data"),
     path("faculty/history/", history_view, name="faculty_history"),
    path("faculty/analytics/", analytics_view, name="faculty_analytics"),
    path("faculty/manual-mark/<int:session_id>/", faculty_manual_mark, name="faculty_manual_mark"),

    path("student/", student_dashboard, name="student_dashboard"),
    path("student/mark/<int:session_id>/", mark_attendance, name="mark_attendance"),
]