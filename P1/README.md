# Práctica 1: Entorno Multicontenedor y Control de Versiones

## Descripción General
Este repositorio contiene la configuración del entorno de desarrollo multicontenedor utilizando Docker y Docker Compose, enfocado en el despliegue de aplicaciones desarrolladas en Python.

---

## Justificación de la Elección de Versiones de Python

Para la arquitectura del entorno Docker se seleccionaron tres versiones específicas del lenguaje Python:

* **Python 3.11:** Garantiza compatibilidad retroactiva y estabilidad con librerías legacy e infraestructuras de producción previas.
* **Python 3.12:** Se establece como la versión base estandarizada para el desarrollo del proyecto por su equilibrio entre rendimiento y madurez en el ecosistema.
* **Python 3.13:** Utilizada para pruebas de vanguardia, validando características recientes y evaluando el rendimiento en versiones modernas del intérprete.

---

## Estructura del Proyecto

```text
practica1-tc/
├── README.md
├── requirements.txt
├── docs/
│   └── 01-entorno.md
├── entorno/
│   ├── Dockerfile
│   ├── compose.yml
│   └── requirements.txt
└── evidencias/
    ├── git/
    └── docker/
