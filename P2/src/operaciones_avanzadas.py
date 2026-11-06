from typing import List, Dict, Any, Set
from itertools import product


class OperacionesAvanzadas:
    """Módulo para subcadenas, prefijos, sufijos, cerradura de Kleene y cerradura positiva."""

    @staticmethod
    def calcular_prefijos_sufijos_subcadenas(cadena: str) -> Dict[str, Any]:
        prefijos = set()
        sufijos = set()
        subcadenas = set()

        # Por convención formal, la cadena vacía (λ o ε) siempre es prefijo y sufijo de cualquier cadena
        prefijos.add("λ (cadena vacía)")
        sufijos.add("λ (cadena vacía)")
        subcadenas.add("λ (cadena vacía)")

        n = len(cadena)

        # Prefijos
        for i in range(1, n + 1):
            prefijos.add(cadena[:i])

        # Sufijos
        for i in range(n):
            sufijos.add(cadena[i:])

        # Subcadenas
        for i in range(n):
            for j in range(i + 1, n + 1):
                subcadenas.add(cadena[i:j])

        return {
            "longitud_n": n,
            "total_prefijos": len(prefijos),
            "prefijos": sorted(list(prefijos), key=lambda x: (len(x), x)),
            "total_sufijos": len(sufijos),
            "sufijos": sorted(list(sufijos), key=lambda x: (len(x), x)),
            "total_subcadenas": len(subcadenas),
            "subcadenas": sorted(list(subcadenas), key=lambda x: (len(x), x)),
            "explicacion_vacia": (
                "Convención adoptada: La cadena vacía (λ) se incluye formalmente entre los prefijos, "
                "sufijos y subcadenas, ya que cualquier cadena s se puede descomponer como s = λs = sλ."
            )
        }

    @staticmethod
    def generar_cerraduras(alfabeto_str: str, longitud_max: int, es_positiva: bool = False) -> Dict[str, Any]:
        # Limpiar alfabeto (separado por comas o espacios)
        simbolos = [s.strip() for s in alfabeto_str.replace(",", " ").split() if s.strip()]
        if not simbolos:
            raise ValueError("El alfabeto no puede estar vacío.")

        # Estimar crecimiento: suma de |Σ|^k desde k=0 (o k=1) hasta longitud_max
        total_estimado = sum(len(simbolos) ** k for k in range(0 if not es_positiva else 1, longitud_max + 1))

        if total_estimado > 200000:
            raise ValueError(
                f"⚠️ Límite excedido: La combinación generaría {total_estimado:,} cadenas, "
                f"lo cual supera el límite de seguridad de 200,000 cadenas (Crecimiento exponencial |Σ|^n)."
            )

        cadenas_generadas = []
        if not es_positiva:
            cadenas_generadas.append("λ (cadena vacía)")

        for k in range(1 if not es_positiva else 1, longitud_max + 1):
            for prod in product(simbolos, repeat=k):
                cadenas_generadas.append("".join(prod))

        return {
            "alfabeto": simbolos,
            "longitud_max": longitud_max,
            "tipo": "Σ⁺ (Cerradura Positiva)" if es_positiva else "Σ* (Cerradura de Kleene)",
            "total": len(cadenas_generadas),
            "cadenas": cadenas_generadas
        }

    @staticmethod
    def generar_reporte_operaciones(datos_ops: dict) -> str:
        lineas = []
        lineas.append("==========================================================")
        lineas.append("      INFORME TÉCNICO: SUBCADENAS, PREFIJOS Y SUFIJOS")
        lineas.append("==========================================================")
        lineas.append(f"Cadena analizada: '{datos_ops.get('cadena', '')}' (Longitud n = {datos_ops.get('longitud_n', 0)})")
        lineas.append(f"\n{datos_ops.get('explicacion_vacia', '')}")
        
        lineas.append(f"\n--- PREFIJOS (Total: {datos_ops.get('total_prefijos', 0)}) ---")
        lineas.append(", ".join(datos_ops.get('prefijos', [])))

        lineas.append(f"\n--- SUFIJOS (Total: {datos_ops.get('total_sufijos', 0)}) ---")
        lineas.append(", ".join(datos_ops.get('sufijos', [])))

        lineas.append(f"\n--- SUBCADENAS (Total: {datos_ops.get('total_subcadenas', 0)}) ---")
        lineas.append(", ".join(datos_ops.get('subcadenas', [])))
        lineas.append("==========================================================")
        return "\n".join(lineas)