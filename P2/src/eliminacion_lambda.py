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
          - Un diccionario detallado con la memoria del proceso paso a paso para la UI/reportes.
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
            "estados_finales_calculo": [],
            "transiciones_desglose": []
        }

        # 1. Determinar nuevos estados de aceptación
        for q in sorted(nuevos_estados):
            cl_q = CerraduraLambdaSimulador.calcular_cerradura_estado(automata_original, q)
            reporte_pasos["cerraduras_individuales"][q] = cl_q
            
            es_final = bool(cl_q.intersection(finales_originales))
            if es_final:
                nuevos_finales.add(q)
            
            reporte_pasos["estados_finales_calculo"].append({
                "estado": q,
                "cl_q": cl_q,
                "interseccion_F": cl_q.intersection(finales_originales),
                "es_final": es_final
            })

        # 2. Calcular la nueva función de transición δ'(q, a) = CL(δ(CL(q), a))
        for q in sorted(nuevos_estados):
            cl_q = reporte_pasos["cerraduras_individuales"][q]

            for simbolo in sorted(nuevo_alfabeto):
                # Subpaso A: Alcanzables leyendo 'simbolo' desde CL(q)
                alcanzables_directos = set()
                for est_cl in cl_q:
                    destinos = automata_original.transiciones.get((est_cl, simbolo), set())
                    alcanzables_directos.update(destinos)

                # Subpaso B: Cerradura Lambda del conjunto alcanzado
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