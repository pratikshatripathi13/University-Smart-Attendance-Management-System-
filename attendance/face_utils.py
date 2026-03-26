import os
try:
    from deepface import DeepFace
except Exception:
    DeepFace = None
try:
    import cv2
except Exception:
    cv2 = None


def verify_faces(img1_path, img2_path):
    if DeepFace is None:
        return False
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
            enforce_detection=True
        )

        verified = bool(result.get("verified", False))
        distance = float(result.get("distance", 999.0))

        # FaceNet typical threshold is around 0.40 but can be up to 0.90 for low-quality webcams
        # We'll use 0.90 to be very lenient and avoid false negatives with generic webcams
        if not verified and distance < 0.90:
            verified = True

        return verified, distance

    except ValueError as e:
        if "face could not be detected" in str(e).lower() or "could not be detected" in str(e).lower():
            return False, -1.0
        return False, 999.0
    except Exception:
        return False, 999.0