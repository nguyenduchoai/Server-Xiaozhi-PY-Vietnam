#!/usr/bin/env python3
"""
Gwen TTS - FastAPI Server
Wrapper matching OpenAI Audio API for Gwen TTS.
"""

import os
import sys
import io
import time
import logging

import torch
import soundfile as sf
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gwen-api")

app = FastAPI(title="Gwen TTS API", version="1.0.0")

# Global TTS instance
tts_engine = None

generation_config = dict(
    temperature=0.3,
    top_k=20,
    top_p=0.9,
    max_new_tokens=4096,
    repetition_penalty=2.0,
    subtalker_do_sample=True,
    subtalker_temperature=0.1,
    subtalker_top_k=20,
    subtalker_top_p=1.0,
)

class SynthesizeRequest(BaseModel):
    input: str = Field(..., description="Text to synthesize")
    voice: str = Field(default="gwen-vi", description="Speaker")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    response_format: str = Field(default="wav")
    model: str = Field(default="gwen-tts")

def get_tts():
    global tts_engine
    if tts_engine is None:
        try:
            from qwen_tts import Qwen3TTSModel
            logger.info("Initializing Gwen TTS Model from g-group-ai-lab/gwen-tts-0.6B...")
            tts_engine = Qwen3TTSModel.from_pretrained(
                "g-group-ai-lab/gwen-tts-0.6B",
                device_map="cuda:0" if torch.cuda.is_available() else "cpu",
                dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                attn_implementation="flash_attention_2" if torch.cuda.is_available() else "eager",
            )
            logger.info("✅ Gwen TTS loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Gwen TTS: {e}")
            raise e
    return tts_engine

@app.on_event("startup")
async def startup():
    try:
        # Preload the model
        get_tts()
    except Exception as e:
        logger.warning(f"⚠️ TTS will lazy-load on first request: {e}")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "gwen-tts"}

@app.post("/v1/audio/speech")
async def synthesize(req: SynthesizeRequest):
    """Synthesize audio compatible with OpenAI API"""
    try:
        engine = get_tts()
        start = time.time()
        
        wavs, sr = engine.generate_voice_clone(
            text=req.input,
            language="Vietnamese",
            ref_audio="", # Default empty clone reference
            ref_text="",
            **generation_config,
        )
        audio = wavs[0]

        buf = io.BytesIO()
        sf.write(buf, audio, sr, format="WAV")
        wav_bytes = buf.getvalue()

        elapsed = time.time() - start
        logger.info(f"Synthesized: {len(req.input)} chars in {elapsed:.2f}s")
        return Response(content=wav_bytes, media_type="audio/wav")

    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8104)
