class Automata:
    def __init__(self, estados=None, alfabeto=None, estado_inicial=None, estados_aceptacion=None, transiciones=None):
        """
        Representación de un Autómata Finito.
        - estados (Q): set de nombres de estados (ej. {'q0', 'q1'})
        - alfabeto (Sigma): set de símbolos (ej. {'0', '1'})
        - estado_inicial (q0): str (ej. 'q0')
        - estados_aceptacion (F): set de estados de aceptación (ej. {'q1'})
        - transiciones (delta): dict de la forma {(origen, simbolo): {destino1, destino2, ...}}
        """
        self.estados = set(estados) if estados else set()
        self.alfabeto = set(alfabeto) if alfabeto else set()
        self.estado_inicial = estado_inicial
        self.estados_aceptacion = set(estados_aceptacion) if estados_aceptacion else set()
        self.transiciones = transiciones if transiciones is not None else {}

    def agregar_estado(self, estado, es_inicial=False, es_aceptacion=False):
        """Añade un estado al autómata."""
        self.estados.add(estado)
        if es_inicial:
            self.estado_inicial = estado
        if es_aceptacion:
            self.estados_aceptacion.add(estado)

    def agregar_transicion(self, origen, simbolo, destino):
        """
        Añade una transición delta(origen, simbolo) -> destino.
        Soporta AFN al guardar los destinos en un conjunto (set).
        """
        if origen not in self.estados or destino not in self.estados:
            raise ValueError("Los estados de origen y destino deben existir en el autómata.")
        if simbolo != 'λ' and simbolo != '' and simbolo not in self.alfabeto:
            raise ValueError(f"El símbolo '{simbolo}' no pertenece al alfabeto.")

        clave = (origen, simbolo)
        if clave not in self.transiciones:
            self.transiciones[clave] = set()
        self.transiciones[clave].add(destino)

    def obtener_transicion(self, origen, simbolo):
        """Retorna el conjunto de estados destino para un origen y símbolo dados."""
        return self.transiciones.get((origen, simbolo), set())

    def es_afn(self):
        """Determina si el autómata es no determinista (AFN o AFN-λ)."""
        for (origen, simbolo), destinos in self.transiciones.items():
            if simbolo in ('λ', '') or len(destinos) > 1:
                return True
        return False

    def clausura_lambda(self, estados):
        """Calcula la clausura lambda para un conjunto de estados."""
        stack = list(estados)
        clausura = set(estados)
        
        while stack:
            actual = stack.pop()
            # Buscar transiciones con lambda o cadena vacía
            destinos_lambda = self.obtener_transicion(actual, 'λ').union(self.obtener_transicion(actual, ''))
            for dest in destinos_lambda:
                if dest not in clausura:
                    clausura.add(dest)
                    stack.append(dest)
        return clausura

    def simular_paso_a_paso(self, cadena):
        """
        Simula el procesamiento de una cadena paso a paso.
        Retorna:
          - es_valida (bool): True si la cadena es aceptada.
          - traza (list of dicts): Registro detallado de cada paso para la interfaz gráfica.
        """
        estados_actuales = self.clausura_lambda({self.estado_inicial})
        traza = [{
            'paso': 0,
            'simbolo': None,
            'estados_actuales': set(estados_actuales),
            'descripcion': f"Inicio en estado inicial con clausura-λ: {estados_actuales}"
        }]

        for i, simbolo in enumerate(cadena):
            if simbolo not in self.alfabeto:
                traza.append({
                    'paso': i + 1,
                    'simbolo': simbolo,
                    'estados_actuales': set(),
                    'error': f"Símbolo '{simbolo}' fuera del alfabeto."
                })
                return False, traza

            proximos_estados = set()
            for est in estados_actuales:
                alcanzables = self.obtener_transicion(est, simbolo)
                proximos_estados.update(alcanzables)

            # Aplicar clausura lambda a los estados alcanzados
            estados_actuales = self.clausura_lambda(proximos_estados)
            
            traza.append({
                'paso': i + 1,
                'simbolo': simbolo,
                'estados_actuales': set(estados_actuales),
                'descripcion': f"Símbolo '{simbolo}' -> Estados alcanzados: {estados_actuales}"
            })

            # Si nos quedamos sin estados activos, la cadena se rechaza tempranamente
            if not estados_actuales:
                break

        # Es válida si al menos uno de los estados finales pertenece al conjunto de aceptación
        es_valida = bool(estados_actuales.intersection(self.estados_aceptacion))
        return es_valida, traza