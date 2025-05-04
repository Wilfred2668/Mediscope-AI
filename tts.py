import edge_tts
import asyncio

async def generate_tts(text, filename="static/audio.mp3"):
    communicate = edge_tts.Communicate(text, voice="en-US-AnaNeural")
    await communicate.save(filename)

def speak_text(text, filename="static/audio.mp3"):
    asyncio.run(generate_tts(text, filename))
