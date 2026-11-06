from typing import Dict, Set, Tuple, List
from automata import Automata
from cerradura_lambda import CerraduraLambdaSimulador


class ConvertidorSubconjuntos:
    """Módulo para convertir un AFN / AFN-λ a un AFD equivalente usando el algoritmo de subconjuntos."""

    @staticmethod
    def afn_a_afd(automata_original: Automata) -> Tuple[Automata, List[Dict[str, str]]]:
        """
        Convierte un AFN / AFN-lambda a un AFD equivalente.
        Retorna:
          - El nuevo autómata (AFD).
          - Historial de pasos de la construcción de subconjuntos para la UI.
        """
        finales_originales = getattr(
            automata_original,
            "estados_aceptacion",
            getattr(automata_original, "estados_finales", getattr(automata_original, "finales", set())),
        )

        alfabeto = sorted(list(automata_original.alfabeto))
        historial_pasos = []

        # 1. Estado inicial del AFD = CL(q0)
        q0_cl = CerraduraLambdaSimulador.calcular_cerradura_estado(
            automata_original, automata_original.estado_inicial
        )
        
        # Representación congelada para usar en conjuntos y diccionarios
        q0_key = tuple(sorted(list(q0_cl)))

        # Mapeo de subconjuntos a nombres legibles (P0, P1, P2... o {q0,q1})
        mapa_conjuntos: Dict[Tuple[str, ...], str] = {}
        
        def obtener_nombre_estado(conjunto_tuple: Tuple[str, ...]) -> str:
            if conjunto_tuple not in mapa_conjuntos:
                nombre = f"S{len(mapa_conjuntos)}"
                mapa_conjuntos[conjunto_tuple] = nombre
            return mapa_conjuntos[conjunto_tuple]

        estado_inicial_afd = obtener_nombre_estado(q0_key)

        pendientes = [q0_key]
        visitados = set()

        nuevas_transiciones = {}
        estados_afd = set()
        finales_afd = set()
        detalles_mapeo = {}

        while pendientes:
            actual_key = pendientes.pop(0)
            if actual_key in visitados:
                continue

            visitados.add(actual_key)
            nombre_actual = obtener_nombre_estado(actual_key)
            estados_afd.add(nombre_actual)
            conjunto_actual_set = set(actual_key)

            # Verificar si es final
            if bool(conjunto_actual_set.intersection(finales_originales)):
                finales_afd.add(nombre_actual)

            detalles_mapeo[nombre_actual] = conjunto_actual_set

            for simbolo in alfabeto:
                alcanzables = set()
                for est in conjunto_actual_set:
                    destinos = automata_original.transiciones.get((est, simbolo), set())
                    alcanzables.update(destinos)

                cl_alcanzables = CerraduraLambdaSimulador.calcular_cerradura_conjunto(
                    automata_original, alcanzables
                )

                dest_key = tuple(sorted(list(cl_alcanzables)))

                if cl_alcanzables:
                    nombre_dest = obtener_nombre_estado(dest_key)
                    nuevas_transiciones[(nombre_actual, simbolo)] = {nombre_dest}

                    if dest_key not in visitados:
                        pendientes.append(dest_key)

                    historial_pasos.append(
                        {
                            "origen_alias": nombre_actual,
                            "origen_conjunto": f"{{{', '.join(actual_key)}}}",
                            "simbolo": simbolo,
                            "destino_conjunto": f"{{{', '.join(dest_key)}}}",
                            "destino_alias": nombre_dest,
                        }
                    )
                else:
                    historial_pasos.append(
                        {
                            "origen_alias": nombre_actual,
                            "origen_conjunto": f"{{{', '.join(actual_key)}}}",
                            "simbolo": simbolo,
                            "destino_conjunto": "∅",
                            "destino_alias": "∅",
                        }
                    )

        afd_resultado = Automata(
            estados=estados_afd,
            alfabeto=set(alfabeto),
            estado_inicial=estado_inicial_afd,
            estados_aceptacion=finales_afd,
            transiciones=nuevas_transiciones,
        )

        # Inyectar el mapeo de alias en el autómata para consultas de la UI
        setattr(afd_resultado, "mapeo_subconjuntos", detalles_mapeo)

        return afd_resultado, historial_pasos