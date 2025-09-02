FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Manila
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
WORKDIR /app
COPY requirements.txt .
COPY rss_live_updater.py .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "rss_live_updater.py"]
