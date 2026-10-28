FROM python:3.12-alpine

WORKDIR /app
COPY sticker_app.py index.html /app/

ENV PORT=8000

EXPOSE 8000

CMD ["python", "/app/sticker_app.py"]
