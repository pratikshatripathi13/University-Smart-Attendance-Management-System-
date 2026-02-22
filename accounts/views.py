from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
try:
    from deepface import DeepFace
except Exception:
    DeepFace = None
from .forms import RegisterForm, FaceEnrollForm


from django.contrib.auth import login

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = "STUDENT"
            user.save()
            login(request, user)
            return redirect("/accounts/enroll-face/")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})



def login_view(request):
    role = request.GET.get("role", "student")
    page_title = "Faculty Login" if role == "faculty" else "Student Login"
    subtitle = (
        "Login to manage attendance sessions and view reports."
        if role == "faculty"
        else "Login to mark attendance during an active faculty session. If it’s your first login, you’ll enroll your face once."
    )

    error = None

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=username, password=password)

        if user is None:
            error = "Invalid username or password"
        else:
            if role == "faculty" and user.role != "FACULTY":
                error = "This account is not a faculty account"
            elif role == "student" and user.role != "STUDENT":
                error = "This account is not a student account"
            else:
                login(request, user)

                if user.role == "STUDENT" and not user.face_image:
                    return redirect("/accounts/enroll-face/")

                return redirect("/attendance/dashboard/")

    return render(request, "accounts/login.html", {
        "role": role,
        "page_title": page_title,
        "subtitle": subtitle,
        "error": error
    })


def logout_view(request):
    logout(request)
    return redirect("/accounts/login/")


@login_required
def enroll_face(request):
    if request.user.role != "STUDENT":
        return redirect("/attendance/dashboard/")

    if request.user.face_image:
        return redirect("/attendance/dashboard/")

    error = None

    if request.method == "POST":
        form = FaceEnrollForm(request.POST, request.FILES)
        if form.is_valid():
            request.user.face_image = form.cleaned_data["face_image"]
            request.user.save()

            try:
                DeepFace.extract_faces(
                    img_path=request.user.face_image.path,
                    detector_backend="opencv",
                    enforce_detection=True
                )
            except Exception:
                request.user.face_image.delete(save=True)
                error = "No clear face detected. Upload a clear front face photo."

            if not error:
                return redirect("/attendance/dashboard/")
    else:
        form = FaceEnrollForm()

    return render(request, "accounts/enroll_face.html", {"form": form, "error": error})
        
