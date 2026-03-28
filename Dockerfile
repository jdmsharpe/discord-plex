FROM python:3.13-slim

WORKDIR /bot

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Run the bot
CMD ["python", "src/bot.py"]
