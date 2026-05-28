FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

WORKDIR /app

RUN apt-get update && apt-get install -y git build-essential

COPY gwen_api_server.py /app/gwen_api_server.py

# Install qwen_tts and specific requirements for Gwen
# Note: we use git to install if the package is not available in PyPI
RUN pip install --no-cache-dir fastapi uvicorn soundfile pydantic requests
RUN pip install --no-cache-dir git+https://github.com/ggroup-ai-lab/gwen-tts.git || pip install qwen_tts transformers accelerate flash-attn --no-build-isolation

EXPOSE 8104

CMD ["python3", "/app/gwen_api_server.py"]
