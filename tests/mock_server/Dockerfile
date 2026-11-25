# Mock Tavily + Gemini server (test profile only).
FROM python:3.12.8-slim-bookworm
RUN pip install --no-cache-dir "fastapi==0.115.6" "uvicorn==0.34.0" \
    && useradd --create-home --uid 10001 mock
WORKDIR /srv
COPY tests/mock_server/ ./mock_server/
USER mock
EXPOSE 8099
CMD ["uvicorn", "mock_server.app:app", "--host", "0.0.0.0", "--port", "8099"]
