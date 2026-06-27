FROM python:3.12-slim

WORKDIR /app

# Copy the Helix SDK into the Jarvis image. In a real Jarvis repo, copy only
# clients/python/helix_agent_client or install it from a package artifact.
COPY clients/python/helix_agent_client /tmp/helix_agent_client
RUN pip install --no-cache-dir /tmp/helix_agent_client

COPY docker/jarvis_agent_example.py /app/jarvis_agent_example.py

ENV HELIX_API_URL=http://api:8000

CMD ["python", "/app/jarvis_agent_example.py"]
