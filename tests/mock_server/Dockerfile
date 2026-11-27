# Mock Tavily, Gemini, Slack and HubSpot server (test profile only).
FROM python:3.12.15-slim-bookworm
# Debian security updates at build time: CI's image scan fails on fixable critical CVEs.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "fastapi==0.115.6" "uvicorn==0.34.0" \
    && useradd --create-home --uid 10001 mock
WORKDIR /srv
COPY tests/mock_server/ ./mock_server/
USER mock
EXPOSE 8099
CMD ["uvicorn", "mock_server.app:app", "--host", "0.0.0.0", "--port", "8099"]
