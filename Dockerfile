# Dockerfile

FROM python:3.11-slim

COPY requirements.txt /requirements.txt

RUN pip install --no-cache-dir -r /requirements.txt

COPY reviewer.py /reviewer.py
COPY reviewer-instructions.md /reviewer-instructions.md


ENTRYPOINT ["python", "/reviewer.py"]