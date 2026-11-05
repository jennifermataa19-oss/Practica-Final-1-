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