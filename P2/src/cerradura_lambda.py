from typing import Set, Dict, List, Tuple
from automata import Automata


class CerraduraLambdaSimulador:
    """Módulo para calcular la cerradura lambda y simular AFN-lambda directamente paso a paso."""

    @staticmethod
    def calcular_cerradura_estado(automata: Automata, estado: str) -> Set[str]:
        """Calcula la cerradura lambda CL(estado) para un único estado."""
        return CerraduraLambdaSimulador.calcular_cerradura_conjunto(automata, {estado})

    @staticmethod
    def calcular_cerradura_conjunto(automata: Automata, estados: Set[str]) -> Set[str]:
        """Calcula la cerradura lambda CL(S) para un conjunto de estados."""
        cerradura = set(estados)
        pila = list(estados)

        SIMBOLOS_LAMBDA = {"", "lambda", "λ", "ε", "eps", "epsilon"}

        while pila:
            actual = pila.pop()
            for lamb in SIMBOLOS_LAMBDA:
                destinos = automata.transiciones.get((actual, lamb), set())
                for dest in destinos:
                    if dest not in cerradura:
                        cerradura.add(dest)
                        pila.append(dest)

        return cerradura

    @staticmethod
    def simular_directo_paso_a_paso(
        automata: Automata, cadena: str
    ) -> Tuple[bool, List[Dict[str, str]]]:
        """Simula un AFN-lambda directamente mostrando estados activos antes y después de la cerradura lambda en cada paso."""
        historial_pasos = []

        if not automata.estado_inicial:
            return False, historial_pasos

        estados_iniciales_puros = {automata.estado_inicial}
        estados_actuales = CerraduraLambdaSimulador.calcular_cerradura_conjunto(
            automata, estados_iniciales_puros
        )

        historial_pasos.append(
            {
                "paso": 0,
                "simbolo": "ε (Inicio)",
                "activos_antes": f"{{{', '.join(sorted(estados_iniciales_puros))}}}",
                "activos_despues": f"{{{', '.join(sorted(estados_actuales))}}}",
                "descripcion": f"Estado inicial '{automata.estado_inicial}' + CL({automata.estado_inicial})"
            }
        )

        for i, simbolo in enumerate(cadena, 1):
            siguiente_conjunto_base = set()

            for est in estados_actuales:
                destinos = automata.transiciones.get((est, simbolo), set())
                siguiente_conjunto_base.update(destinos)

            siguiente_con_cerradura = CerraduraLambdaSimulador.calcular_cerradura_conjunto(
                automata, siguiente_conjunto_base
            )

            historial_pasos.append(
                {
                    "paso": i,
                    "simbolo": simbolo,
                    "activos_antes": f"{{{', '.join(sorted(siguiente_conjunto_base))}}}" if siguiente_conjunto_base else "∅",
                    "activos_despues": f"{{{', '.join(sorted(siguiente_con_cerradura))}}}" if siguiente_con_cerradura else "∅",
                    "descripcion": f"Lectura de '{simbolo}': base={sorted(list(siguiente_conjunto_base))} -> CL={sorted(list(siguiente_con_cerradura))}"
                }
            )

            estados_actuales = siguiente_con_cerradura

            if not estados_actuales:
                break

        finales = getattr(
            automata,
            "estados_aceptacion",
            getattr(automata, "estados_finales", getattr(automata, "finales", set())),
        )
        es_aceptada = bool(estados_actuales.intersection(finales))

        return es_aceptada, historial_pasos