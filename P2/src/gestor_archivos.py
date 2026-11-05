import json
from automata import Automata

class GestorArchivos:
    @staticmethod
    def guardar_json(automata, ruta_archivo):
        # Convertimos los 'sets' (conjuntos) a listas porque JSON no soporta sets
        datos = {
            "estados": list(automata.estados),
            "alfabeto": list(automata.alfabeto),
            "estado_inicial": automata.estado_inicial,
            "estados_aceptacion": list(automata.estados_aceptacion),
            # Hacemos un diccionario anidado para las transiciones
            "transiciones": {
                origen: {simbolo: list(destinos) for simbolo, destinos in trans.items()}
                for origen, trans in automata.transiciones.items()
            }
        }
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=4)

    @staticmethod
    def cargar_json(ruta_archivo):
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        aut = Automata()
        # 1. Cargamos estados
        for e in datos.get("estados", []): 
            aut.agregar_estado(e)
        
        # 2. Cargamos alfabeto
        aut.alfabeto = set(datos.get("alfabeto", []))
        
        # 3. Estado inicial y de aceptación
        aut.definir_estado_inicial(datos.get("estado_inicial"))
        for e in datos.get("estados_aceptacion", []): 
            aut.agregar_estado_aceptacion(e)
        
        # 4. Reconstruimos transiciones
        for origen, trans in datos.get("transiciones", {}).items():
            for simbolo, destinos in trans.items():
                for destino in destinos:
                    aut.agregar_transicion(origen, simbolo, destino)
                    
        return aut