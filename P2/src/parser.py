import xml.etree.ElementTree as ET
import json
from automata import Automata

class AutomataParser:
    @staticmethod
    def cargar_desde_archivo(ruta_archivo):
        """Detecta el formato por la extensión y llama al parser correspondiente."""
        if ruta_archivo.endswith('.jff') or ruta_archivo.endswith('.xml'):
            return AutomataParser.desde_jff_xml(ruta_archivo)
        elif ruta_archivo.endswith('.json'):
            return AutomataParser.desde_json(ruta_archivo)
        else:
            raise ValueError("Formato de archivo no soportado. Debe ser .jff, .xml o .json")

    @staticmethod
    def desde_jff_xml(ruta_archivo):
        """
        Lee archivos en formato JFLAP (.jff) o estructuras XML genéricas.
        Estructura típica JFLAP: <structure><type>fa</type><automaton>...
        """
        tree = ET.parse(ruta_archivo)
        root = tree.getroot()

        # Si el XML envuelve el autómata dentro de <automaton>
        automaton_node = root.find('automaton') if root.find('automaton') is not None else root

        estados = set()
        estado_inicial = None
        estados_aceptacion = set()
        mapa_id_nombre = {}  # Para mapear id interno de JFLAP al nombre del estado

        # 1. Extraer estados
        for state_node in automaton_node.findall('state'):
            s_id = state_node.get('id')
            s_name = state_node.get('name', f"q{s_id}")
            
            estados.add(s_name)
            mapa_id_nombre[s_id] = s_name

            if state_node.find('initial') is not None:
                estado_inicial = s_name
            if state_node.find('final') is not None:
                estados_aceptacion.add(s_name)

        # 2. Extraer transiciones y construir alfabeto
        alfabeto = set()
        transiciones = {}

        for trans_node in automaton_node.findall('transition'):
            from_id = trans_node.find('from').text
            to_id = trans_node.find('to').text
            read_node = trans_node.find('read')
            
            simbolo = read_node.text if (read_node is not None and read_node.text) else ''

            origen = mapa_id_nombre.get(from_id)
            destino = mapa_id_nombre.get(to_id)

            if simbolo != '' and simbolo != 'λ':
                alfabeto.add(simbolo)

            clave = (origen, simbolo)
            if clave not in transiciones:
                transiciones[clave] = set()
            transiciones[clave].add(destino)

        return Automata(
            estados=estados,
            alfabeto=alfabeto,
            estado_inicial=estado_inicial,
            estados_aceptacion=estados_aceptacion,
            transiciones=transiciones
        )

    @staticmethod
    def desde_json(ruta_archivo):
        """
        Lee un autómata representado en formato JSON estructurado.
        Formato esperado:
        {
            "estados": ["q0", "q1"],
            "alfabeto": ["0", "1"],
            "estado_inicial": "q0",
            "estados_aceptacion": ["q1"],
            "transiciones": [
                {"origen": "q0", "simbolo": "0", "destino": "q1"}
            ]
        }
        """
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            data = json.load(f)

        estados = set(data.get('estados', []))
        alfabeto = set(data.get('alfabeto', []))
        estado_inicial = data.get('estado_inicial')
        estados_aceptacion = set(data.get('estados_aceptacion', []))
        
        transiciones = {}
        for t in data.get('transiciones', []):
            origen = t['origen']
            simbolo = t['simbolo']
            destino = t['destino']

            clave = (origen, simbolo)
            if clave not in transiciones:
                transiciones[clave] = set()
            transiciones[clave].add(destino)

        return Automata(
            estados=estados,
            alfabeto=alfabeto,
            estado_inicial=estado_inicial,
            estados_aceptacion=estados_aceptacion,
            transiciones=transiciones
        )