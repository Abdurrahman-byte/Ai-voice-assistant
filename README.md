AbdulGPT — LiveKit Voice Agent

A voice assistant built with [LiveKit Agents](https://docs.livekit.io/agents/). A browser client connects to a LiveKit room, a Python worker (`agent.py`) joins as an AI participant and handles STT → LLM → TTS, and a small FastAPI server (`server.py`) issues the access tokens the browser needs to connect.

 Project structure

```
.
├── agent.py       # LiveKit worker: voice pipeline (VAD, STT, LLM, TTS, tools)
├── server.py      # FastAPI backend: serves the frontend + issues room tokens
├── index.html     # Browser client: connects to the room, streams mic audio
└── .env           # Secrets and config (not committed)
```

## How it fits together

1. `index.html` calls `GET /api/get-token` on `server.py`, sending an API key.
2. `server.py` verifies the key, mints a LiveKit access token with a server-generated identity, and returns it along with the LiveKit server URL.
3. The browser uses that token to connect directly to LiveKit and publish microphone audio.
4. `agent.py` runs as a separate worker process, is dispatched into the room, and handles the conversation: Silero VAD for voice activity, Groq Whisper for STT, Groq Llama 3.3 for the LLM, and ElevenLabs for TTS.

Prerequisites

- Python 3.9+
- A [LiveKit](https://livekit.io) project (Cloud or self-hosted) — API key, API secret, and server URL
- API keys for [Groq](https://console.groq.com) and [ElevenLabs](https://elevenlabs.io)

Setup

**1. Install dependencies**

```bash
pip install "livekit-agents[silero,groq,elevenlabs]" livekit-plugins-turn-detector fastapi uvicorn python-dotenv
```

**2. Download the turn-detector model files** (one-time; also re-run this when building a Docker image for deployment):

```bash
python -m livekit.agents download-files
```

**3. Create a `.env` file** in the project root:

```env
# LiveKit
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret

# Groq (STT + LLM)
GROQ_API_KEY=your-groq-api-key

# ElevenLabs (TTS)
ELEVENLABS_API_KEY=your-elevenlabs-api-key

# Backend server
BACKEND_API_KEY=some-long-random-string
ALLOWED_ORIGINS=http://localhost:8000
```

**4. Set the matching API key in `index.html`**

Open `index.html` and replace:

```js
const BACKEND_API_KEY = "REPLACE_WITH_YOUR_BACKEND_API_KEY";
```

with the same value you put in `BACKEND_API_KEY` in `.env`. If you're not running the server on `127.0.0.1:8000`, also update `BACKEND_URL` in the same file.

> ⚠️ This key lives in client-side JS, so anyone can read it via browser dev tools. It's a minimal gate to stop casual/automated abuse of the token endpoint — not real authentication. Before letting other people use this, replace it with proper login/session-based auth.

Running it

**Start the backend** (serves `index.html` and issues tokens):

```bash
python server.py
```
Runs at `http://127.0.0.1:8000`.

**Start the agent worker** (in a separate terminal):

```bash
python agent.py dev
```

**Open the app**: visit `http://127.0.0.1:8000` in your browser and click **Start Conversation**. Grant microphone access when prompted.

Configuration notes

- **CORS**: `server.py` only allows origins listed in `ALLOWED_ORIGINS` (comma-separated). Add your deployed frontend's origin here before going live.
- **VAD prewarming**: `agent.py` loads the Silero VAD model once at worker startup (`prewarm_fnc`) rather than per-call, to reduce per-job latency.
- **Turn detection**: uses LiveKit's `MultilingualModel` turn detector alongside VAD for more reliable end-of-turn detection.
- **Identity**: user identities are generated server-side (`web-user-<random>`) rather than trusted from the client, to prevent identity spoofing/collisions.

Deploying

Before deploying beyond local testing:

- Serve both frontend and backend over **HTTPS** — browsers block microphone access on non-localhost HTTP origins.
- Pin `ALLOWED_ORIGINS` to your real frontend domain(s).
- Replace the shared `BACKEND_API_KEY` gate with real user authentication.
- Pin the LiveKit client SDK version in `index.html` and consider adding a Subresource Integrity (`integrity=`) hash, or self-host the SDK file, so a compromised CDN can't inject arbitrary JS.
- Turn off `reload=True` in `server.py`'s `uvicorn.run(...)` call — it's for local dev only.

Troubleshooting

- **"Missing LiveKit API credentials"**: check `.env` has `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` set and that `server.py` is loading it (`load_dotenv()` runs at import time, so restart the server after editing `.env`).
- **401 Unauthorized from `/api/get-token`**: the `x-api-key` header sent by `index.html` doesn't match `BACKEND_API_KEY` in `.env`.
- **No audio / "Microphone permission denied"**: check browser mic permissions for the site, and confirm you're on HTTPS or `localhost`.
- **Agent never joins the room**: confirm `agent.py` is running (`python agent.py dev`) and connected to the same LiveKit project as `server.py`.