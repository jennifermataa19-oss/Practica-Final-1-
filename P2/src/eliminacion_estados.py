import copy

class EliminadorEstados:
    """
    Clase para convertir un Autómata Finito (AFN/AFD) a una Expresión Regular
    mediante el algoritmo de eliminación de estados (Método de Arden).
    """

    @staticmethod
    def _purificar_automata(automata):
        """
        Prepara el autómata para el algoritmo:
        1. Crea un único estado inicial 'qi' que no recibe entradas.
        2. Crea un único estado final 'qf' que no tiene salidas.
        3. Normaliza las transiciones para que el algoritmo pueda operar de forma segura.
        """
        # Copia profunda para no alterar la estructura del autómata original
        auto = copy.deepcopy(automata)

        nuevo_inicio = "q_init_puro"
        nuevo_final = "q_final_puro"

        # Asegurar nombres únicos para los estados puros
        mientras_exista = lambda nombre: nombre in auto.estados
        idx = 0
        tmp_init = nuevo_inicio
        tmp_final = nuevo_final
        while mientras_exista(tmp_init) or mientras_exista(tmp_final):
            idx += 1
            tmp_init = f"{nuevo_inicio}_{idx}"
            tmp_final = f"{nuevo_final}_{idx}"
        
        nuevo_inicio = tmp_init
        nuevo_final = tmp_final

        # Inicializar grafo de Expresión Regular: grafo[u][v] = expresion
        grafo = {e: {} for e in auto.estados}
        grafo[nuevo_inicio] = {}
        grafo[nuevo_final] = {}

        # Mapear transiciones existentes agrupando símbolos
        for (origen, simbolo), destinos in auto.transiciones.items():
            simbolo_str = "E" if simbolo in ["λ", "epsilon", "E", "eps", ""] else str(simbolo)
            for dest in destinos:
                if dest not in grafo[origen]:
                    grafo[origen][dest] = []
                grafo[origen][dest].append(simbolo_str)

        # Unir transiciones paralelas con operador OR (|)
        for u in grafo:
            for v in grafo[u]:
                simbolos = grafo[u][v]
                if len(simbolos) == 1:
                    grafo[u][v] = simbolos[0]
                else:
                    grafo[u][v] = f"({'|'.join(simbolos)})"

        # Conectar el nuevo estado inicial puro al estado inicial original con λ (E)
        if auto.estado_inicial:
            grafo[nuevo_inicio][auto.estado_inicial] = "E"

        # Conectar todos los estados de aceptación originales al nuevo estado final puro con λ (E)
        finales = getattr(auto, "estados_aceptacion", getattr(auto, "estados_finales", getattr(auto, "finales", set())))
        for f in finales:
            grafo[f][nuevo_final] = "E"

        todos_los_estados = set(grafo.keys())
        return grafo, nuevo_inicio, nuevo_final, todos_los_estados

    @classmethod
    def convertir_a_er(cls, automata):
        """
        Ejecuta el algoritmo de eliminación de estados y retorna la ER resultante
        junto con el historial de pasos para mostrarlo en la interfaz.
        """
        grafo, q_init, q_final, estados = cls._purificar_automata(automata)
        pasos = []
        
        # Estados que se deben eliminar (todos excepto el inicial y final puros)
        estados_a_eliminar = [e for e in estados if e not in (q_init, q_final)]

        pasos.append({
            "accion": "Purificación del Autómata",
            "descripcion": f"Se agregaron los estados aislados '{q_init}' y '{q_final}' con transiciones λ."
        })

        # Algoritmo de eliminación de estados
        for q_k in estados_a_eliminar:
            # Encontrar predecesores (u -> q_k) y sucesores (q_k -> v)
            predecesores = [u for u in grafo if q_k in grafo[u] and u != q_k]
            sucesores = [v for v in grafo[q_k] if v != q_k]
            
            # Auto-bucle en q_k (q_k -> q_k)
            bucle_k = grafo[q_k].get(q_k, None)

            for u in predecesores:
                for v in sucesores:
                    p_uq = grafo[u][q_k]
                    p_qv = grafo[q_k][v]

                    # Construir la nueva expresión regular simplificada
                    # L = P_uq + (Bucle_k)* + P_qv
                    exp_bucle = ""
                    if bucle_k:
                        if len(bucle_k) == 1 or (bucle_k.startswith("(") and bucle_k.endswith(")")):
                            exp_bucle = f"{bucle_k}*"
                        else:
                            exp_bucle = f"({bucle_k})*"

                    exp_p_uq = "" if p_uq == "E" else p_uq
                    exp_p_qv = "" if p_qv == "E" else p_qv

                    # Concatenar términos
                    nueva_exp = f"{exp_p_uq}{exp_bucle}{exp_p_qv}"
                    if nueva_exp == "":
                        nueva_exp = "E"

                    # Combinar con transición previa u -> v si ya existía
                    if v in grafo[u]:
                        prev_exp = grafo[u][v]
                        grafo[u][v] = f"({prev_exp}|{nueva_exp})"
                    else:
                        grafo[u][v] = nueva_exp

            # Eliminar q_k del grafo
            del grafo[q_k]
            for u in grafo:
                if q_k in grafo[u]:
                    del grafo[u][q_k]

            pasos.append({
                "accion": f"Eliminado estado '{q_k}'",
                "descripcion": f"Se eliminó el estado '{q_k}' y se actualizaron las rutas entre sus predecesores y sucesores."
            })

        # Expresión regular final entre q_init y q_final
        er_final = grafo.get(q_init, {}).get(q_final, "∅")
        
        # Limpieza básica de caracteres epsilon redundantes
        er_final = er_final.replace("E", "")
        if not er_final:
            er_final = "λ"

        return {
            "expresion_regular": er_final,
            "pasos": pasos
        }