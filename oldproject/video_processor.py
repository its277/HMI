# import cv2
# import numpy as np
# from ultralytics import YOLO
# from tracker import Sort
# # sperm_analyzer is not provided, assuming it exists and is correct
# # from sperm_analyzer import is_tail_bent
# import os
# import torch
# from torchvision.models import efficientnet_v2_l
# from torchvision import transforms
# import json
# import traceback

# # --- Constants ---
# MOTILITY_FRAME_WINDOW = 20
# MOTILITY_DISTANCE_THRESHOLD = 0.01
# BENT_TAIL_THRESHOLD = 0.95
# FONT = cv2.FONT_HERSHEY_SIMPLEX
# CONCENTRATION_MULTIPLIER = 5.476

# def get_video_nomenclature(cap):
#     """Extracts video metadata (nomenclature) from a cv2.VideoCapture object."""
#     try:
#         width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#         height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#         fps = round(cap.get(cv2.CAP_PROP_FPS), 2)
#         frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
#         # Ensure fps is not zero to avoid division by zero error
#         duration_seconds = round(frame_count / fps, 2) if fps > 0 else 0

#         return {
#             "resolution": f"{width}x{height}",
#             "frame_rate": fps,
#             "duration_seconds": duration_seconds
#         }
#     except Exception as e:
#         print(f"[WARNING] Could not extract video nomenclature: {e}")
#         # Return a default structure if metadata extraction fails
#         return {
#             "resolution": "N/A",
#             "frame_rate": "N/A",
#             "duration_seconds": "N/A"
#         }

# def process_video(video_path, model_path, output_path, json_output_path):
#     print("\n--- [START] Video Processing ---")
#     try:
#         # --- Initialization ---
#         model = YOLO(model_path)
#         print(f"[SUCCESS] YOLO Model loaded. Classes: {model.names}")

#         classifier_path = "models/efficientnetv2_l_sperm_morphology2.pth"
#         if not os.path.exists(classifier_path):
#             raise FileNotFoundError(f"Classifier model not found at path: {classifier_path}")

#         device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#         classifier = efficientnet_v2_l(weights=None)
#         classifier.classifier[1] = torch.nn.Linear(classifier.classifier[1].in_features, 2)
#         state_dict = torch.load(classifier_path, map_location=device)
#         classifier.load_state_dict(state_dict)
#         classifier.eval()
#         classifier.to(device)
#         print("[SUCCESS] Classifier model loaded.")

#         preprocess = transforms.Compose([transforms.ToPILImage(), transforms.Resize((224, 224)), transforms.ToTensor(), transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])])
#         tracker = Sort(max_age=5, min_hits=3, iou_threshold=0.3)

#         cap = cv2.VideoCapture(video_path)
#         # --- Get Nomenclature Data ---
#         nomenclature_data = get_video_nomenclature(cap)
#         width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#         out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), 15, (width, height))

#         # --- Main Processing Loop ---
#         tracked_sperms = {}
#         total_sperm_count, bent_tail_count, motile_sperm_count = 0, 0, 0
#         all_seen_ids, bent_ids, motile_ids = set(), set(), set()
#         frame_idx = 0

#         while True:
#             ret, frame = cap.read()
#             if not ret:
#                 break

#             results = model.predict(frame, verbose=False)

#             detections = []
#             if results[0].obb is not None and hasattr(results[0].obb, 'cls'):
#                 for i, obb in enumerate(results[0].obb):
#                     if int(obb.cls[0].cpu().numpy()) == 1:
#                         xyxy = obb.xyxy[0].cpu().numpy().astype(int)
#                         conf = obb.conf[0].cpu().numpy()
#                         detections.append([xyxy[0], xyxy[1], xyxy[2], xyxy[3], conf])

#             detections_np = np.array(detections) if detections else np.empty((0, 5))
#             tracked_objects = tracker.update(detections_np)

#             for obj in tracked_objects:
#                 x1, y1, x2, y2, obj_id = map(int, obj)
#                 if obj_id not in all_seen_ids:
#                     all_seen_ids.add(obj_id)
#                     total_sperm_count += 1
#                     morphology = "normal"
#                     patch = frame[y1:y2, x1:x2]
#                     if patch.size > 0:
#                         patch_tensor = preprocess(patch).unsqueeze(0).to(device)
#                         with torch.no_grad():
#                             output = classifier(patch_tensor)
#                             probabilities = torch.softmax(output, dim=1)
#                             if output.argmax(1).item() == 1 and probabilities[0][1].item() >= BENT_TAIL_THRESHOLD:
#                                 morphology = "bent_tail"
#                     if morphology == "bent_tail" and obj_id not in bent_ids:
#                         bent_ids.add(obj_id)
#                         bent_tail_count += 1
#                     tracked_sperms[obj_id] = {"positions": [], "is_bent": obj_id in bent_ids, "is_motile": False, "morphology": morphology}

#                 tracked_sperms[obj_id]["positions"].append((frame_idx, (x1+x2)//2, (y1+y2)//2))
#                 if not tracked_sperms[obj_id]["is_motile"] and len(tracked_sperms[obj_id]["positions"]) > MOTILITY_FRAME_WINDOW:
#                     pos = tracked_sperms[obj_id]["positions"]
#                     distance = np.sqrt((pos[-1][1] - pos[0][1])**2 + (pos[-1][2] - pos[0][2])**2)
#                     if distance > MOTILITY_DISTANCE_THRESHOLD and obj_id not in motile_ids:
#                         tracked_sperms[obj_id]["is_motile"] = True
#                         motile_ids.add(obj_id)
#                         motile_sperm_count += 1
#                     pos.pop(0)

#                 color = (0, 255, 0)
#                 if tracked_sperms[obj_id]["is_bent"]: color = (0, 0, 255)
#                 if tracked_sperms[obj_id]["is_motile"]: color = (255, 0, 0)
#                 cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#                 cv2.putText(frame, f"ID:{obj_id}", (x1, y1 - 10), FONT, 0.5, color, 2)

#             cv2.putText(frame, f"Total: {total_sperm_count} Bent: {bent_tail_count} Motile: {motile_sperm_count}", (10, 30), FONT, 1, (255, 255, 255), 2)
#             out.write(frame)
#             frame_idx += 1

#         # --- Finalization ---
#         cap.release()
#         out.release()

#         total_sperm_concentration = round(total_sperm_count * CONCENTRATION_MULTIPLIER, 2)

#         report = {
#             "total_sperm_count": total_sperm_count,
#             "total_sperm_concentration_M_ml": total_sperm_concentration,
#             "bent_tail_sperm_count": bent_tail_count,
#             "motile_sperm_count": motile_sperm_count,
#             "output_video_path": output_path,
#             "output_video_url": f"/video/{os.path.basename(output_path)}",
#             "nomenclature": nomenclature_data  # --- Add nomenclature to the report
#         }

#         with open(json_output_path, 'w') as f:
#             json.dump(report, f, indent=4)
#         print("[SUCCESS] Analysis report saved.")
#         return report

#     except Exception as e:
#         print(f"\n\n!!!!!! [CRITICAL ERROR] IN process_video !!!!!!\nError: {e}")
#         traceback.print_exc()
#         raise e

import cv2
import numpy as np
from ultralytics import YOLO
from tracker import Sort
# sperm_analyzer is not provided, assuming it exists and is correct
# from sperm_analyzer import is_tail_bent
import os
import torch
from torchvision.models import efficientnet_v2_l
from torchvision import transforms
import json
import traceback
import imageio

# --- Constants ---
MOTILITY_FRAME_WINDOW = 20
MOTILITY_DISTANCE_THRESHOLD = 0.01
BENT_TAIL_THRESHOLD = 0.95
FONT = cv2.FONT_HERSHEY_SIMPLEX
CONCENTRATION_MULTIPLIER = 5.476

def get_video_nomenclature(cap):
    """Extracts video metadata (nomenclature) from a cv2.VideoCapture object."""
    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = round(cap.get(cv2.CAP_PROP_FPS), 2)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = round(frame_count / fps, 2) if fps > 0 else 0
        return {
            "resolution": f"{width}x{height}",
            "frame_rate": fps,
            "duration_seconds": duration_seconds
        }
    except Exception as e:
        print(f"[WARNING] Could not extract video nomenclature: {e}")
        return {"resolution": "N/A", "frame_rate": "N/A", "duration_seconds": "N/A"}

def process_video(video_path, model_path, output_path, json_output_path):
    print("\n--- [START] Video Processing ---")
    try:
        # --- Initialization ---
        model = YOLO(model_path)
        classifier_path = "models/efficientnetv2_l_sperm_morphology2.pth"
        if not os.path.exists(classifier_path):
            raise FileNotFoundError(f"Classifier model not found at path: {classifier_path}")

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        classifier = efficientnet_v2_l(weights=None)
        classifier.classifier[1] = torch.nn.Linear(classifier.classifier[1].in_features, 2)
        classifier.load_state_dict(torch.load(classifier_path, map_location=device))
        classifier.eval()
        classifier.to(device)

        preprocess = transforms.Compose([transforms.ToPILImage(), transforms.Resize((224, 224)), transforms.ToTensor(), transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])])
        tracker = Sort(max_age=5, min_hits=3, iou_threshold=0.3)
        cap = cv2.VideoCapture(video_path)
        
        nomenclature_data = get_video_nomenclature(cap)
        
        # --- NEW: Thumbnail Generation ---
        thumbnail_path = output_path.replace(".mp4", ".jpg")
        ret, first_frame = cap.read()
        if ret:
            cv2.imwrite(thumbnail_path, first_frame)
            print(f"[SUCCESS] Thumbnail saved to: {thumbnail_path}")
        else:
            thumbnail_path = None # Handle case where video has no frames
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Reset video capture to the beginning
        
        out = imageio.get_writer(output_path, fps=15, codec='libx264', output_params=['-pix_fmt', 'yuv420p'])

        # --- Main Processing Loop ---
        tracked_sperms = {}
        total_sperm_count, bent_tail_count, motile_sperm_count = 0, 0, 0
        all_seen_ids, bent_ids, motile_ids = set(), set(), set()
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            results = model.predict(frame, verbose=False)
            detections = []
            if results[0].obb is not None and hasattr(results[0].obb, 'cls'):
                for i, obb in enumerate(results[0].obb):
                    if int(obb.cls[0].cpu().numpy()) == 1:
                        xyxy = obb.xyxy[0].cpu().numpy().astype(int)
                        conf = obb.conf[0].cpu().numpy()
                        detections.append([xyxy[0], xyxy[1], xyxy[2], xyxy[3], conf])

            detections_np = np.array(detections) if detections else np.empty((0, 5))
            tracked_objects = tracker.update(detections_np)

            for obj in tracked_objects:
                x1, y1, x2, y2, obj_id = map(int, obj)
                if obj_id not in all_seen_ids:
                    all_seen_ids.add(obj_id)
                    total_sperm_count += 1
                    morphology = "normal"
                    patch = frame[y1:y2, x1:x2]
                    if patch.size > 0:
                        patch_tensor = preprocess(patch).unsqueeze(0).to(device)
                        with torch.no_grad():
                            output = classifier(patch_tensor)
                            probabilities = torch.softmax(output, dim=1)
                            if output.argmax(1).item() == 1 and probabilities[0][1].item() >= BENT_TAIL_THRESHOLD:
                                morphology = "bent_tail"
                    if morphology == "bent_tail" and obj_id not in bent_ids:
                        bent_ids.add(obj_id)
                        bent_tail_count += 1
                    tracked_sperms[obj_id] = {"positions": [], "is_bent": obj_id in bent_ids, "is_motile": False, "morphology": morphology}

                tracked_sperms[obj_id]["positions"].append((frame_idx, (x1+x2)//2, (y1+y2)//2))
                if not tracked_sperms[obj_id]["is_motile"] and len(tracked_sperms[obj_id]["positions"]) > MOTILITY_FRAME_WINDOW:
                    pos = tracked_sperms[obj_id]["positions"]
                    distance = np.sqrt((pos[-1][1] - pos[0][1])**2 + (pos[-1][2] - pos[0][2])**2)
                    if distance > MOTILITY_DISTANCE_THRESHOLD and obj_id not in motile_ids:
                        tracked_sperms[obj_id]["is_motile"] = True
                        motile_ids.add(obj_id)
                        motile_sperm_count += 1
                    pos.pop(0)

                color = (0, 255, 0)
                if tracked_sperms[obj_id]["is_bent"]: color = (0, 0, 255)
                if tracked_sperms[obj_id]["is_motile"]: color = (255, 0, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"ID:{obj_id}", (x1, y1 - 10), FONT, 0.5, color, 2)

            cv2.putText(frame, f"Total: {total_sperm_count} Bent: {bent_tail_count} Motile: {motile_sperm_count}", (10, 30), FONT, 1, (255, 255, 255), 2)
            out.append_data(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            frame_idx += 1

        # --- Finalization ---
        cap.release()
        out.close()

        total_sperm_concentration = round(total_sperm_count * CONCENTRATION_MULTIPLIER, 2)

        report = {
            "total_sperm_count": total_sperm_count,
            "total_sperm_concentration_M_ml": total_sperm_concentration,
            "bent_tail_sperm_count": bent_tail_count,
            "motile_sperm_count": motile_sperm_count,
            "output_video_path": output_path,
            "output_video_url": f"/video/{os.path.basename(output_path)}",
            "nomenclature": nomenclature_data,
            # --- NEW: Add thumbnail URL to the report ---
            "thumbnail_url": f"/thumbnail/{os.path.basename(thumbnail_path)}" if thumbnail_path else None
        }

        with open(json_output_path, 'w') as f:
            json.dump(report, f, indent=4)
        print("[SUCCESS] Analysis report saved.")
        return report

    except Exception as e:
        print(f"\n\n!!!!!! [CRITICAL ERROR] IN process_video !!!!!!\nError: {e}")
        traceback.print_exc()
        raise e
