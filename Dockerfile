FROM python:3.10-slim

RUN useradd -m -u 1000 user
WORKDIR /home/user/app

ENV HF_HOME=/home/user/.cache/huggingface
ENV TRANSFORMERS_CACHE=/home/user/.cache/huggingface/hub

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY benchmark_engine.py ./
COPY bootstrap.py ./
COPY catalog_engine.py ./
COPY catalog_viewmodels.py ./
COPY charts.py ./
COPY corpora.py ./
COPY data ./data
COPY diagnostics.py ./
COPY explainer.py ./
COPY model_registry.py ./
COPY openrouter.py ./
COPY pricing.py ./
COPY provenance.py ./
COPY scenario_engine.py ./
COPY scenario_viewmodels.py ./
COPY token_tax.py ./
COPY token_tax_ui.py ./
COPY tokenizer.py ./
COPY tokenizer_registry.py ./
COPY ui_feedback.py ./
COPY warm_tokenizers.py ./
COPY workbench_types.py ./

RUN mkdir -p /home/user/.cache/huggingface && chown -R user:user /home/user
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860
ENV PYTHONUNBUFFERED=1

USER user
RUN python warm_tokenizers.py
EXPOSE 7860

CMD ["python", "-u", "bootstrap.py"]
