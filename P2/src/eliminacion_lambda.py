from typing import Dict, Set, Tuple
from automata import Automata
from cerradura_lambda import CerraduraLambdaSimulador


class EliminadorLambda:
    """Módulo para convertir un AFN-λ en un AFN equivalente sin transiciones λ."""

    @staticmethod
    def eliminar_transiciones_lambda(automata_original: Automata) -> Tuple[Automata, Dict[str, Dict[str, Set[str]]]]:
        """
        Transforma un AFN-λ en un AFN sin λ.
        Retorna:
          - El nuevo autómata (AFN sin λ).
          - Un diccionario con la memoria del proceso paso a paso para la UI.
        """
        # Detectar el conjunto de estados finales del autómata original
        finales_originales = getattr(
            automata_original,
            "estados_aceptacion",
            getattr(automata_original, "estados_finales", getattr(automata_original, "finales", set())),
        )

        nuevos_estados = set(automata_original.estados)
        nuevo_alfabeto = set(automata_original.alfabeto)  # Alfabeto sin λ
        nuevo_inicial = automata_original.estado_inicial
        nuevos_finales = set()
        nuevas_transiciones = {}

        # Memoria para reporte/interfaz paso a paso
        detalles_conversion = {}

        # 1. Determinar nuevos estados de aceptación
        for q in nuevos_estados:
            cl_q = CerraduraLambdaSimulador.calcular_cerradura_estado(automata_original, q)
            if bool(cl_q.intersection(finales_originales)):
                nuevos_finales.add(q)

        # 2. Calcular la nueva función de transición δ'(q, a) = CL(δ(CL(q), a))
        for q in sorted(nuevos_estados):
            detalles_conversion[q] = {}
            cl_q = CerraduraLambdaSimulador.calcular_cerradura_estado(automata_original, q)

            for simbolo in sorted(nuevo_alfabeto):
                # Paso A: Alcanzables leyendo 'simbolo' desde CL(q)
                alcanzables_directos = set()
                for est_cl in cl_q:
                    destinos = automata_original.transiciones.get((est_cl, simbolo), set())
                    alcanzables_directos.update(destinos)

                # Paso B: Cerradura Lambda del conjunto alcanzado
                cl_alcanzados = CerraduraLambdaSimulador.calcular_cerradura_conjunto(
                    automata_original, alcanzables_directos
                )

                if cl_alcanzados:
                    nuevas_transiciones[(q, simbolo)] = cl_alcanzados

                detalles_conversion[q][simbolo] = {
                    "cl_origen": cl_q,
                    "alcanzables_directos": alcanzables_directos,
                    "resultado_cl": cl_alcanzados
                }

        nuevo_automata = Automata(
            estados=nuevos_estados,
            alfabeto=nuevo_alfabeto,
            estado_inicial=nuevo_inicial,
            estados_aceptacion=nuevos_finales,
            transiciones=nuevas_transiciones
        )

        return nuevo_automata, detalles_conversion