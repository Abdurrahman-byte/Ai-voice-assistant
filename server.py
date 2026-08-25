import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from livekit import api

load_dotenv()

app = FastAPI()

# 1. Restrict CORS to known frontend origin(s) instead of "*"
# Set ALLOWED_ORIGINS in .env as a comma-separated list, e.g.:
#   ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")


BACKEND_API_KEY = os.getenv("BACKEND_API_KEY")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/")
async def serve_index():
    return FileResponse("index.html")


@app.get("/api/get-token")
async def get_token(
    room_name: str = "abdul-room",
    x_api_key: str = Header(default=None),
):
    if not BACKEND_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: BACKEND_API_KEY is not set.",
        )
    if x_api_key != BACKEND_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized.")

    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL")

    if not api_key or not api_secret or not livekit_url:
        raise HTTPException(
            status_code=500,
            detail="Missing LiveKit API credentials in environment variables.",
        )

    identity = f"web-user-{uuid.uuid4().hex[:8]}"

    token = (
        api.AccessToken(api_key=api_key, api_secret=api_secret)
        .with_identity(identity)
        .with_name("Web User")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
    )

    return {"serverUrl": livekit_url, "token": token.to_jwt()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
