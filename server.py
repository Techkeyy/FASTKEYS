"""
FASTKEYS Backend API Server
Provides endpoints for audio upload, verification, and end-to-end music analysis.
"""
import os
import shutil
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import engine

app = FastAPI(title="FASTKEYS API", description="Keyboardist Emergency Song-Learning Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve web frontend
STATIC_DIR = os.path.join(os.path.dirname(__file__), "web")
os.makedirs(STATIC_DIR, exist_ok=True)

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "FASTKEYS Analysis API",
        "ai_core": "Spotify Basic Pitch Neural Network (Apache 2.0)",
        "dsp_core": "Krumhansl-Schmuckler CQT Chromagram + Diatonic Degree Mapping"
    }

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".wav", ".ogg", ".mp3", ".flac", ".oga"]:
        raise HTTPException(status_code=400, detail="Unsupported audio format. Supported: .wav, .ogg, .mp3, .flac")
    
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name
        shutil.copyfileobj(file.file, tmp)
        
    try:
        # Convert the complete upload to 22050 Hz mono. Long-song chunking
        # happens inside the analysis engine; truncating here would make full
        # duration synchronization impossible.
        converted_wav = tmp_path + "_converted.wav"
        ffmpeg_cmd = f'ffmpeg -i "{tmp_path}" -ar 22050 -ac 1 "{converted_wav}" -y -loglevel error'
        code = os.system(ffmpeg_cmd)
        target_path = converted_wav if code == 0 and os.path.exists(converted_wav) else tmp_path
        
        result = engine.analyze_audio_file(target_path)
        result['filename'] = file.filename
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        # Cleanup temp files
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(tmp_path + "_converted.wav"):
                os.remove(tmp_path + "_converted.wav")
        except Exception:
            pass

# Serve static frontend files
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
