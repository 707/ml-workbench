FROM python:3.10-slim

RUN useradd -m -u 1000 user
WORKDIR /home/user/app

ENV HF_HOME=/home/user/.cache/huggingface

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY bootstrap.py ./
COPY data ./data
COPY warm_tokenizers.py ./
COPY workbench ./workbench

RUN mkdir -p /home/user/.cache/huggingface && chown -R user:user /home/user
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860
ENV PYTHONUNBUFFERED=1

USER user
RUN python warm_tokenizers.py
EXPOSE 7860

CMD ["python", "-u", "bootstrap.py"]
