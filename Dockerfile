FROM python:3.12-slim
WORKDIR /app
COPY common/ common/
COPY server/ server/
EXPOSE 5000
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "server.server"]
