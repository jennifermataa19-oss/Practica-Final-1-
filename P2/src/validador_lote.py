from typing import List, Dict, Tuple, Any
from automata import Automata
from cerradura_lambda import CerraduraLambdaSimulador


class ValidadorLote:
    """Módulo para validar archivos de texto con cadenas masivas sobre un autómata."""

    @staticmethod
    def validar_cadenas_desde_texto(automata: Automata, contenido_texto: str) -> List[Dict[str, Any]]:
        """
        Toma el contenido de un archivo .txt con una cadena por línea y la evalúa.
        Retorna una lista con la información de cada cadena.
        """
        lineas = contenido_texto.splitlines()
        resultados = []

        for i, linea in enumerate(lineas, 1):
            cadena = linea.strip()
            
            # Si el archivo incluye cadenas vacías expresadas como lambda o epsilon
            cadena_evaluar = "" if cadena in {"λ", "ε", "lambda", "eps", "epsilon"} else cadena

            try:
                # Usamos la simulación directa con cerradura lambda para máxima compatibilidad
                es_aceptada, historial = CerraduraLambdaSimulador.simular_directo_paso_a_paso(
                    automata, cadena_evaluar
                )
                
                # Obtener conjunto de estados finales alcanzados
                ultimo_paso = historial[-1] if historial else {}
                activos_finales = ultimo_paso.get("activos_despues", "∅")

                resultados.append({
                    "linea": i,
                    "cadena": cadena if cadena != "" else "λ (cadena vacía)",
                    "cadena_real": cadena_evaluar,
                    "resultado": "ACEPTADA" if es_aceptada else "RECHAZADA",
                    "es_aceptada": es_aceptada,
                    "estados_finales_alcanzados": activos_finales
                })
            except Exception as err:
                resultados.append({
                    "linea": i,
                    "cadena": cadena,
                    "cadena_real": cadena_evaluar,
                    "resultado": f"ERROR: {err}",
                    "es_aceptada": False,
                    "estados_finales_alcanzados": "N/A"
                })

        return resultados

    @staticmethod
    def generar_reporte_texto(nombre_archivo_origen: str, resultados: List[Dict[str, Any]]) -> str:
        """Genera el contenido estructurado en texto plano para exportar el informe."""
        lineas_reporte = []
        lineas_reporte.append("==========================================================")
        lineas_reporte.append("       INFORME DE VALIDACIÓN EN LOTE DE CADENAS")
        lineas_reporte.append(f" Archivo origen: {nombre_archivo_origen}")
        lineas_reporte.append("==========================================================")
        lineas_reporte.append(f"{'Línea':<8} | {'Cadena':<25} | {'Resultado':<12} | {'Estados Activos Finales'}")
        lineas_reporte.append("-" * 75)

        aceptadas = 0
        rechazadas = 0

        for res in resultados:
            num = str(res["linea"])
            cad = res["cadena"]
            veredicto = res["resultado"]
            activos = res["estados_finales_alcanzados"]

            if res["es_aceptada"]:
                aceptadas += 1
            else:
                rechazadas += 1

            lineas_reporte.append(f"{num:<8} | {cad:<25} | {veredicto:<12} | {activos}")

        lineas_reporte.append("==========================================================")
        lineas_reporte.append(f" RESUMEN: Total: {len(resultados)} | Aceptadas: {aceptadas} | Rechazadas: {rechazadas}")
        lineas_reporte.append("==========================================================")

        return "\n".join(lineas_reporte)