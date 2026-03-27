FROM python:3.10-slim

RUN useradd -m -u 1000 user
WORKDIR /home/user/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY bootstrap.py ./
COPY charts.py ./
COPY corpora.py ./
COPY model_registry.py ./
COPY openrouter.py ./
COPY pricing.py ./
COPY provenance.py ./
COPY token_tax.py ./
COPY token_tax_ui.py ./
COPY tokenizer.py ./

ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860
ENV PYTHONUNBUFFERED=1

USER user
EXPOSE 7860

CMD ["python", "-u", "bootstrap.py"]
