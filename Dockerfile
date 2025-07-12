# Use uma imagem leve já com Python
FROM python:3.11-slim

# Instala dependências do SO que o Streamlit costuma precisar
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl && \
    rm -rf /var/lib/apt/lists/*

COPY classes.csv ./classes.csv

# Copie o requirements  (obrigatório conter streamlit)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

RUN mkdir -p /root/.streamlit
COPY .streamlit/config.toml /root/.streamlit/config.toml
# Copie o código da aplicação
WORKDIR /app
COPY . /app

# Ajustes de fuso e Streamlit
ENV TZ=America/Sao_Paulo \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
