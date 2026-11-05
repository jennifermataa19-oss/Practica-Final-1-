import json
import xml.etree.ElementTree as ET
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
    # ... código anterior ...
        # 4. Reconstruimos transiciones
        for origen, trans in datos.get("transiciones", {}).items():
            for simbolo, destinos in trans.items():
                for destino in destinos:
                    aut.agregar_transicion(origen, simbolo, destino)
                    
        return aut
    @staticmethod
    def guardar_jff_xml(automata, ruta_archivo):
        # Crea la estructura base de JFLAP (.jff / .xml)
        root = ET.Element("structure")
        ET.SubElement(root, "type").text = "fa"
        automaton_node = ET.SubElement(root, "automaton")
        
        # JFLAP requiere IDs numéricos para los estados. Hacemos un mapeo.
        estados_lista = list(automata.estados)
        estado_a_id = {nombre: str(i) for i, nombre in enumerate(estados_lista)}
        
        # Guardar estados, estado inicial y de aceptación
        for nombre, id_num in estado_a_id.items():
            state_node = ET.SubElement(automaton_node, "state", id=id_num, name=nombre)
            if nombre == automata.estado_inicial:
                ET.SubElement(state_node, "initial")
            if nombre in automata.estados_aceptacion:
                ET.SubElement(state_node, "final")
                
        # Guardar transiciones
        for origen, trans in automata.transiciones.items():
            for simbolo, destinos in trans.items():
                for destino in destinos:
                    trans_node = ET.SubElement(automaton_node, "transition")
                    ET.SubElement(trans_node, "from").text = estado_a_id[origen]
                    ET.SubElement(trans_node, "to").text = estado_a_id[destino]
                    read_node = ET.SubElement(trans_node, "read")
                    # Transiciones lambda en JFLAP se dejan sin texto
                    if simbolo != "lambda":
                        read_node.text = simbolo

        tree = ET.ElementTree(root)
        tree.write(ruta_archivo, encoding="utf-8", xml_declaration=True)

    @staticmethod
    def cargar_jff_xml(ruta_archivo):
        tree = ET.parse(ruta_archivo)
        root = tree.getroot()
        automaton_node = root.find("automaton")
        
        aut = Automata()
        id_a_estado = {}
        
        # 1. Cargar estados
        for state in automaton_node.findall("state"):
            id_num = state.get("id")
            nombre = state.get("name")
            id_a_estado[id_num] = nombre
            aut.agregar_estado(nombre)
            
            if state.find("initial") is not None:
                aut.definir_estado_inicial(nombre)
            if state.find("final") is not None:
                aut.agregar_estado_aceptacion(nombre)
                
        # 2. Cargar transiciones y armar el alfabeto
        for trans in automaton_node.findall("transition"):
            origen = id_a_estado[trans.find("from").text]
            destino = id_a_estado[trans.find("to").text]
            read_node = trans.find("read")
            
            simbolo = read_node.text if read_node.text else "lambda"
            if simbolo != "lambda":
                aut.alfabeto.add(simbolo)
                
            aut.agregar_transicion(origen, simbolo, destino)
            
        return aut