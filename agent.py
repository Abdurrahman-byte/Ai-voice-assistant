import asyncio

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.agents.inference import TurnDetector
from livekit.plugins import elevenlabs, groq, silero

load_dotenv()


# 1. Define tools using function_tool
@function_tool
async def get_weather(location: str) -> str:
    """Look up the current weather for a given location."""
    return f"The weather in {location} is currently sunny and 72°F."


# 2. Load VAD once at worker startup (not per-job) to cut cold-start latency
def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    print(f"Connecting worker to room: {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # 3. Don't hang forever if nobody joins
    try:
        participant = await asyncio.wait_for(ctx.wait_for_participant(), timeout=30)
    except asyncio.TimeoutError:
        print("No participant joined within 30s, ending job.")
        return

    print(f"Participant joined: {participant.identity}")

    # 4. Define Agent instructions and register the tool function directly
    agent = Agent(
        instructions="You are a helpful voice assistant named AbdulGPT. Keep responses concise and conversational.",
        tools=[get_weather],
    )

    # 5. Create the session binding VAD, STT, LLM, TTS, and turn detection
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=groq.STT(model="whisper-large-v3"),
        llm=groq.LLM(model="openai/gpt-oss-120b"),
        tts=elevenlabs.TTS(
            model="eleven_multilingual_v2",
            voice=elevenlabs.Voice(
                id="21m00Tcm4TlvDq8ikWAM",
                name="Rachel"
            ),
        ),
        turn_detection=TurnDetector(),
    )

    # 6. Start session in the room attached to the agent
    await session.start(room=ctx.room, agent=agent)

    # 7. Trigger initial LLM-generated greeting 
    await session.generate_reply(
        instructions="Greet the user as AbdulGPT and ask how you can help."
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))