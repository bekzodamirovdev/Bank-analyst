FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://ollama.com/install.sh | sh

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p reports data logs

EXPOSE 5000 11434

RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Start Ollama service in background\n\
ollama serve &\n\
\n\
# Wait for Ollama to be ready\n\
echo "Waiting for Ollama to start..."\n\
sleep 10\n\
\n\
# Pull required LLM model\n\
ollama pull llama3.2 || true\n\
\n\
# Initialize database (only first run)\n\
python bank_analyst.py --setup || true\n\
\n\
# Start Flask web application\n\
exec python web_app.py\n\
' > /app/start.sh && chmod +x /app/start.sh

CMD ["./start.sh"]
