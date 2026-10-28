FROM python:3.12-alpine

WORKDIR /app
COPY sticker_app.py /app/sticker_app.py

ENV PORT=8000

EXPOSE 8000

CMD ["python", "/app/sticker_app.py"]
