from typing import Dict, Set, Tuple, List, Any
from automata import Automata


class ConversorAutomataARegex:
    """Módulo para convertir un AFD a Expresión Regular mediante Eliminación de Estados."""

    @staticmethod
    def verificar_es_afd_puro(automata: Automata) -> Tuple[bool, str]:
        """
        Verifica si el autómata es un AFD determinista puro:
        - No debe tener transiciones lambda ('λ', 'ε').
        - Cada estado debe tener exactamente una transición por cada símbolo del alfabeto.
        Retorna (True, "") o (False, mensaje_error).
        """
        # 1. Comprobar transiciones lambda
        for (est, simb), destinos in automata.transiciones.items():
            if simb in {"λ", "ε", "lambda", ""}:
                return False, f"El estado '{est}' tiene una transición lambda ('{simb}'), lo cual invalida el determinismo estricto."

        # 2. Comprobar determinismo completo (transiciones exactas)
        alfabeto = sorted(list(automata.alfabeto))
        for est in sorted(automata.estados):
            for simb in alfabeto:
                destinos = automata.transiciones.get((est, simb), set())
                if len(destinos) != 1:
                    return False, f"El estado '{est}' con el símbolo '{simbolo}' tiene {len(destinos)} destinos (debe ser exactamente 1)."

        return True, "El autómata es un AFD determinista puro válido."

    @staticmethod
    def convertir_a_regex(automata: Automata) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Aplica el algoritmo de eliminación de estados para obtener la Expresión Regular.
        Retorna la expresión final y el historial de pasos con los autómatas generalizados.
        """
        # 1. Crear un AFD equivalente con un ÚNICO estado inicial nuevo (sin entradas previas)
        # y un ÚNICO estado final sumidero (sin salidas, uniendo todos los de aceptación previos con lambda).
        
        estados = set(automata.estados)
        transiciones = dict(automata.transiciones)
        alfabeto = set(automata.alfabeto)

        q_in_viejo = automata.estado_inicial
        finales_viejos = getattr(automata, "estados_aceptacion", getattr(automata, "estados_finales", getattr(automata, "finales", set())))

        q_inicio_nuevo = "q_start_gen"
        q_fin_nuevo = "q_accept_gen"

        while q_inicio_nuevo in estados:
            q_inicio_nuevo += "_"
        while q_fin_nuevo in estados:
            q_fin_nuevo += "_"

        estados.add(q_inicio_nuevo)
        estados.add(q_fin_nuevo)

        # Transición lambda del nuevo inicial al viejo inicial
        transiciones[(q_inicio_nuevo, "λ")] = {q_in_viejo}

        # Transiciones lambda de los viejos finales al nuevo final
        for f in finales_viejos:
            transiciones[(f, "λ")] = transiciones.get((f, "λ"), set()).union({q_fin_nuevo})

        # Historial para la interfaz
        historial_pasos = []

        # 2. Estados a eliminar (todos excepto el nuevo inicio y el nuevo final)
        estados_a_eliminar = sorted([st for st in estados if st not in {q_inicio_nuevo, q_fin_nuevo}])

        # Estructura de expresiones regulares entre pares de estados: R[qi][qj] = "regex"
        # Para simplificar, convertimos las transiciones en un diccionario anidado de expresiones string.
        regex_matriz: Dict[str, Dict[str, str]] = {s1: {s2: "" for s2 in estados} for s1 in estados}

        for (u, s), dests in transiciones.items():
            for v in dests:
                simb_str = f"({s})" if s not in {"λ", "ε", ""} and len(s) > 1 else s
                if simb_str in {"λ", "ε", ""}:
                    simb_str = "ε"
                
                if regex_matriz[u][v]:
                    regex_matriz[u][v] += f"|{simb_str}"
                else:
                    regex_matriz[u][v] = simb_str

        # Función auxiliar para envolver en paréntesis si es necesario
        def envolver(r: str) -> str:
            if not r or r == "ε":
                return r
            if "|" in r:
                return f"({r})"
            return r

        # 3. Proceso de Eliminación de Estados
        for idx, q_elim in enumerate(estados_a_eliminar, 1):
            # Guardar estado antes de eliminar para el reporte
            historial_pasos.append({
                "paso": idx,
                "estado_eliminado": q_elim,
                "matriz_antes": {k: dict(v) for k, v in regex_matriz.items()}
            })

            # Estados predecesores y sucesores de q_elim (que no sean q_elim mismo)
            predecesores = [s for s in estados if s != q_elim and regex_matriz[s][q_elim]]
            sucesores = [s for s in estados if s != q_elim and regex_matriz[q_elim][s]]

            # Bucle propio en q_elim (R_kk)
            r_kk = regex_matriz[q_elim][q_elim]
            loop_str = ""
            if r_kk:
                if r_kk == "ε":
                    loop_str = ""
                else:
                    loop_str = f"({r_kk})*"

            for p in predecesores:
                for s in sucesores:
                    r_pk = regex_matriz[p][q_elim]
                    r_ks = regex_matriz[q_elim][s]

                    # Construir nueva expresión: r_pk . (r_kk)* . r_ks
                    partes = []
                    if r_pk and r_pk != "ε":
                        partes.append(envolver(r_pk))
                    if loop_str:
                        partes.append(loop_str)
                    if r_ks and r_ks != "ε":
                        partes.append(envolver(r_ks))

                    camino_nuevo = "".join(partes) if partes else "ε"

                    # Combinar con transición existente entre p y s
                    if regex_matriz[p][s]:
                        regex_matriz[p][s] += f"|{camino_nuevo}"
                    else:
                        regex_matriz[p][s] = camino_nuevo

            # Eliminar filas y columnas de q_elim de la matriz
            for st in estados:
                regex_matriz[st][q_elim] = ""
                regex_matriz[q_elim][st] = ""

        # La expresión final está en R[q_inicio_nuevo][q_fin_nuevo]
        regex_final = regex_matriz[q_inicio_nuevo][q_fin_nuevo]
        
        # Limpieza estética de épsilons sobrantes
        regex_final = regex_final.replace("ε", "")

        return regex_final if regex_final else "ε", historial_pasos