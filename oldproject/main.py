import os
import shutil
import uuid
import json
import traceback
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from video_processor import process_video
from fastapi.middleware.cors import CORSMiddleware
import config

app = FastAPI(title="Sperm Analysis API")

# --- CORS Middleware ---
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Directory Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")
OUTPUTS_DIR = os.path.join(STATIC_DIR, "outputs")
MODEL_PATH = os.path.join(BASE_DIR, "models", "best.pt")
REACT_BUILD_DIR = os.path.join(BASE_DIR, "..", "sperm-analysis-react", "build")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# --- API Endpoints ---

# --- NEW: Endpoint to serve thumbnails ---
@app.get("/thumbnail/{image_name}")
async def get_thumbnail(image_name: str):
    image_path = os.path.join(OUTPUTS_DIR, image_name)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(image_path, media_type="image/jpeg")

@app.get("/video/{video_name}")
async def get_video(video_name: str):
    video_path = os.path.join(OUTPUTS_DIR, video_name)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(video_path, media_type="video/mp4")

@app.get("/analysis/{json_name}")
async def get_analysis_json(json_name: str):
    json_path = os.path.join(OUTPUTS_DIR, json_name)
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Analysis JSON not found")
    return FileResponse(json_path, media_type="application/json")

# --- MODIFIED: History endpoint now includes thumbnail URL ---
@app.get("/history/")
async def get_history():
    history_items = []
    for filename in os.listdir(OUTPUTS_DIR):
        if filename.startswith("processed_") and filename.endswith(".mp4"):
            json_name = filename.replace(".mp4", ".json")
            json_path = os.path.join(OUTPUTS_DIR, json_name)
            
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r') as f:
                        data = json.load(f)
                    history_items.append({
                        "video_name": filename,
                        "json_name": json_name,
                        "thumbnail_url": data.get("thumbnail_url") # Get URL from JSON
                    })
                except (json.JSONDecodeError, KeyError):
                    # Handle cases where JSON is malformed or key is missing
                    print(f"[WARNING] Could not read or find thumbnail_url in {json_name}")
                    continue

    return sorted(history_items, key=lambda x: x["video_name"], reverse=True)

@app.post("/analyze/")
async def analyze_video_endpoint(file: UploadFile = File(...)):
    print("\n--- [API] Received request for /analyze/ ---")
    try:
        base_uuid = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        
        upload_filename = f"{base_uuid}{file_extension}"
        upload_path = os.path.join(UPLOADS_DIR, upload_filename)
        
        output_video_filename = f"processed_{base_uuid}.mp4"
        output_path = os.path.join(OUTPUTS_DIR, output_video_filename)
        
        output_json_filename = f"processed_{base_uuid}.json"
        output_json_path = os.path.join(OUTPUTS_DIR, output_json_filename)

        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        report = process_video(
            video_path=upload_path,
            model_path=MODEL_PATH,
            output_path=output_path,
            json_output_path=output_json_path
        )
        
        return JSONResponse(content=report)
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")

# --- Frontend Serving (Must be LAST) ---
app.mount("/static", StaticFiles(directory=os.path.join(REACT_BUILD_DIR, "static")), name="react-static")

@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    index_path = os.path.join(REACT_BUILD_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail=f"index.html not found. Path checked: {index_path}. Did you run 'npm run build'?")
    return FileResponse(index_path)
