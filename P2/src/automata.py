class Automata:
    def __init__(self):
        # Los 5 componentes de la quíntupla
        self.estados = set()               # Q: Conjunto de estados
        self.alfabeto = set()              # Σ: Alfabeto
        self.estado_inicial = None         # q0: Estado inicial
        self.estados_aceptacion = set()    # F: Conjunto de estados de aceptación
        self.transiciones = {}             # δ: Función de transición

    def agregar_estado(self, estado):
        self.estados.add(estado)

    def definir_estado_inicial(self, estado):
        if estado in self.estados:
            self.estado_inicial = estado

    def agregar_estado_aceptacion(self, estado):
        if estado in self.estados:
            self.estados_aceptacion.add(estado)

    def agregar_transicion(self, origen, simbolo, destino):
        """
        Guarda las transiciones. 
        Como es un AFND, un símbolo puede llevar a múltiples destinos.
        Estructura: { 'q0': { 'a': ['q1', 'q2'], 'lambda': ['q3'] } }
        """
        if origen not in self.transiciones:
            self.transiciones[origen] = {}
        if simbolo not in self.transiciones[origen]:
            self.transiciones[origen][simbolo] = set()
            
        self.transiciones[origen][simbolo].add(destino)
    def lambda_clausura(self, estados):
        """Calcula todos los estados alcanzables a través de transiciones lambda."""
        clausura = set(estados)
        pila = list(estados)
        
        while pila:
            estado = pila.pop()
            # Si el estado tiene transiciones y existe la transición 'lambda'
            if estado in self.transiciones and 'lambda' in self.transiciones[estado]:
                for destino in self.transiciones[estado]['lambda']:
                    if destino not in clausura:
                        clausura.add(destino)
                        pila.append(destino)
        return clausura

    def validar_cadena(self, cadena):
        """Valida una cadena siguiendo todos los caminos posibles (Simulación AFND)."""
        if self.estado_inicial is None:
            return False
            
        # Arrancamos en el estado inicial + cualquier lugar al que lleguemos con lambda
        estados_actuales = self.lambda_clausura({self.estado_inicial})
        
        for simbolo in cadena:
            siguientes_estados = set()
            for estado in estados_actuales:
                if estado in self.transiciones and simbolo in self.transiciones[estado]:
                    siguientes_estados.update(self.transiciones[estado][simbolo])
            
            # Aplicamos lambda clausura a los nuevos estados alcanzados
            estados_actuales = self.lambda_clausura(siguientes_estados)
            
            # Si nos quedamos sin estados válidos, el camino muere
            if not estados_actuales:
                return False
                
        # Es válida si al menos uno de los caminos terminó en un estado de aceptación
        return any(estado in self.estados_aceptacion for estado in estados_actuales)

    def simular_paso_a_paso(self, cadena):
        """Genera la traza completa del recorrido para la interfaz gráfica."""
        if self.estado_inicial is None:
            return False, []

        traza = []
        estados_actuales = self.lambda_clausura({self.estado_inicial})
        traza.append(("Inicio", list(estados_actuales)))
        
        for simbolo in cadena:
            siguientes_estados = set()
            for estado in estados_actuales:
                if estado in self.transiciones and simbolo in self.transiciones[estado]:
                    siguientes_estados.update(self.transiciones[estado][simbolo])
            
            estados_actuales = self.lambda_clausura(siguientes_estados)
            traza.append((f"Lee '{simbolo}'", list(estados_actuales)))
            
            if not estados_actuales:
                traza.append(("Camino muerto", []))
                break
                
        es_valida = any(estado in self.estados_aceptacion for estado in estados_actuales)
        return es_valida, traza