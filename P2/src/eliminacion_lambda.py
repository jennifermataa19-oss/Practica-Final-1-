from typing import Dict, Set, Tuple, Any
from automata import Automata
from cerradura_lambda import CerraduraLambdaSimulador


class EliminadorLambda:
    """Módulo para convertir un AFN-λ en un AFN equivalente sin transiciones λ."""

    @staticmethod
    def eliminar_transiciones_lambda(automata_original: Automata) -> Tuple[Automata, Dict[str, Any]]:
        """
        Transforma un AFN-λ en un AFN sin λ.
        Retorna:
          - El nuevo autómata (AFN sin λ).
          - Un diccionario detallado con el paso a paso estructurado para la UI/reportes.
        """
        finales_originales = getattr(
            automata_original,
            "estados_aceptacion",
            getattr(automata_original, "estados_finales", getattr(automata_original, "finales", set())),
        )

        nuevos_estados = set(automata_original.estados)
        nuevo_alfabeto = set(automata_original.alfabeto)  # Alfabeto puros (sin λ)
        nuevo_inicial = automata_original.estado_inicial
        nuevos_finales = set()
        nuevas_transiciones = {}

        reporte_pasos = {
            "cerraduras_individuales": {},
            "finales_originales": finales_originales,
            "estados_finales_calculo": [],
            "transiciones_desglose": []
        }

        # ---------------------------------------------------------------------
        # PASO 1 & 2: Cerraduras Lambda individuales y Nuevos Estados Finales (F')
        # ---------------------------------------------------------------------
        for q in sorted(nuevos_estados):
            cl_q = CerraduraLambdaSimulador.calcular_cerradura_estado(automata_original, q)
            reporte_pasos["cerraduras_individuales"][q] = cl_q

            interseccion = cl_q.intersection(finales_originales)
            es_final = bool(interseccion)
            if es_final:
                nuevos_finales.add(q)

            reporte_pasos["estados_finales_calculo"].append({
                "estado": q,
                "cl_q": cl_q,
                "interseccion_F": interseccion,
                "es_final": es_final
            })

        # ---------------------------------------------------------------------
        # PASO 3: Nueva Función de Transición δ'(q, a) = CL(δ(CL(q), a))
        # ---------------------------------------------------------------------
        for q in sorted(nuevos_estados):
            cl_q = reporte_pasos["cerraduras_individuales"][q]

            for simbolo in sorted(nuevo_alfabeto):
                # Subpaso 3.1: Alcanzables directos leyendo 'simbolo' desde CL(q)
                alcanzables_directos = set()
                for est_cl in cl_q:
                    destinos = automata_original.transiciones.get((est_cl, simbolo), set())
                    alcanzables_directos.update(destinos)

                # Subpaso 3.2: Cerradura Lambda del conjunto alcanzado
                cl_alcanzados = CerraduraLambdaSimulador.calcular_cerradura_conjunto(
                    automata_original, alcanzables_directos
                )

                if cl_alcanzados:
                    nuevas_transiciones[(q, simbolo)] = cl_alcanzados

                reporte_pasos["transiciones_desglose"].append({
                    "estado": q,
                    "simbolo": simbolo,
                    "cl_origen": cl_q,
                    "alcanzables_directos": alcanzables_directos,
                    "resultado_cl": cl_alcanzados
                })

        nuevo_automata = Automata(
            estados=nuevos_estados,
            alfabeto=nuevo_alfabeto,
            estado_inicial=nuevo_inicial,
            estados_aceptacion=nuevos_finales,
            transiciones=nuevas_transiciones
        )

        return nuevo_automata, reporte_pasos