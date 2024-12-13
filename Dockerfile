FROM python:3.12

WORKDIR /app
COPY . ./

RUN pip install --no-cache-dir -r requirements.lock
CMD python -m src.main --webapp