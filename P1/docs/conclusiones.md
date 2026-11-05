# Conclusiones

El desarrollo e implementación de esta práctica permitió consolidar la relación directa entre la **Teoría de Autómatas y Lenguajes Formales** y el desarrollo de software estructurado, modular y portable en entornos de producción.

1. **Modularidad y Separación de Responsabilidades:**  
   La separación explícita entre el núcleo algorítmico matemático (`src/lenguajes.py`) y la capa de presentación e interfaz interactiva (`src/app.py`) demostró ser una arquitectura sólida. Esta abstracción no solo facilitó la integración con el *framework* Flet, sino que permitió someter la lógica formal a pruebas automatizadas sin depender de elementos del estado visual.

2. **Portabilidad y Verificación Multiversión mediante Contenedores:**  
   La orquestación de entornos aislados con Docker e imágenes de Python en versiones 3.11, 3.12 y 3.13 garantizó un entorno de ejecución homogéneo e independiente del sistema operativo anfitrión. La ejecución exitosa de la suite de pruebas unitarias (`pytest`) con un resultado de **5 passed** en las tres versiones confirmó que el comportamiento algorítmico es determinista y no presenta incompatibilidades por regresiones ni cambios en el intérprete de Python.

3. **Validez Formal del Modelo de Estado Finito:**  
   La simulación del Autómata Finito Determinista (AFD) dentro de la aplicación demostró la precisión con la que un modelo matemático responde ante cadenas de entrada arbitrarias. La identificación del estado pozo ($q_5$) ante secuencias no aceptadas confirmó la importancia de definir transiciones explícitas para preservar las propiedades de determinismo y asegurar la correctitud del reconocimiento de lenguajes.