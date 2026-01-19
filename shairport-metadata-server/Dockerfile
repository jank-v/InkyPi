FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

EXPOSE 5000

ENV MQTT_HOST=localhost
ENV MQTT_PORT=1883
ENV TOPIC_PREFIX=shairport-sync
ENV HTTP_HOST=0.0.0.0
ENV HTTP_PORT=5000

CMD ["python", "server.py"]
