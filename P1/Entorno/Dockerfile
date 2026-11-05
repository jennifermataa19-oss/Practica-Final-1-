# Un solo Dockerfile para las tres versiones. El numero de version
# llega desde compose.yml como argumento de construccion.
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

# El entorno virtual va en /opt/venv, fuera de /app. Colocar
# /opt/venv/bin al principio del PATH equivale a activarlo.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Las dependencias antes que el codigo, para reutilizar la capa
# mientras requirements.txt no cambie.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Flet, al no encontrar escritorio, arranca como servidor web.
ENV FLET_FORCE_WEB_SERVER=true
ENV FLET_SERVER_PORT=8550

CMD ["python", "src/app.py"]