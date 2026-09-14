FROM python:3.12-slim

WORKDIR /verify

COPY api/requirements.txt /verify/api-requirements.txt
RUN pip install --no-cache-dir -r /verify/api-requirements.txt

COPY api /verify/api
COPY verify/smoke.py /verify/smoke.py

ENV PYTHONPATH=/verify/api \
    API_URL=http://api:5000 \
    WEB_URL=http://web:80

CMD ["sh", "-c", "python -m pytest /verify/api/tests -q && python /verify/smoke.py"]
