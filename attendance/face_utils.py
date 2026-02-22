import os
from deepface import DeepFace


def verify_faces(img1_path, img2_path):
    if not img1_path or not os.path.exists(img1_path) or os.path.getsize(img1_path) == 0:
        return False, 999.0

    if not img2_path or not os.path.exists(img2_path) or os.path.getsize(img2_path) == 0:
        return False, 999.0

    try:
        result = DeepFace.verify(
            img1_path=img1_path,
            img2_path=img2_path,
            model_name="Facenet",          # Faster than VGG
            detector_backend="opencv",     # Lightweight
            enforce_detection=False
        )

        return bool(result.get("verified", False)), float(result.get("distance", 999.0))

    except Exception:
        return False, 999.0