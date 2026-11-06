import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

class AutomataExporter:
    @staticmethod
    def a_json(automata, ruta_archivo):
        """Exporta el autómata a formato JSON."""
        transiciones_list = []
        for (origen, simbolo), destinos in automata.transiciones.items():
            for dest in destinos:
                transiciones_list.append({
                    "origen": origen,
                    "simbolo": simbolo,
                    "destino": dest
                })

        data = {
            "estados": list(automata.estados),
            "alfabeto": list(automata.alfabeto),
            "estado_inicial": automata.estado_inicial,
            "estados_aceptacion": list(automata.estados_aceptacion),
            "transiciones": transiciones_list
        }

        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def a_jff(automata, ruta_archivo):
        """Exporta el autómata al formato XML nativo de JFLAP (.jff)."""
        structure = ET.Element('structure')
        type_elem = ET.SubElement(structure, 'type')
        type_elem.text = 'fa'
        automaton = ET.SubElement(structure, 'automaton')

        mapa_id = {estado: str(i) for i, estado in enumerate(sorted(automata.estados))}

        # Generar nodos <state>
        for estado, id_str in mapa_id.items():
            state_elem = ET.SubElement(automaton, 'state', id=id_str, name=estado)
            if estado == automata.estado_inicial:
                ET.SubElement(state_elem, 'initial')
            if estado in automata.estados_aceptacion:
                ET.SubElement(state_elem, 'final')

        # Generar nodos <transition>
        for (origen, simbolo), destinos in automata.transiciones.items():
            for dest in destinos:
                trans_elem = ET.SubElement(automaton, 'transition')
                ET.SubElement(trans_elem, 'from').text = mapa_id[origen]
                ET.SubElement(trans_elem, 'to').text = mapa_id[dest]
                read_elem = ET.SubElement(trans_elem, 'read')
                read_elem.text = simbolo if simbolo != 'λ' else ''

        # Formatear el XML bonito (pretty print)
        xml_str = minidom.parseString(ET.tostring(structure)).toprettyxml(indent="  ")
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(xml_str)

    @staticmethod
    def a_xml(automata, ruta_archivo):
        """Exporta a XML estructurado genérico."""
        # Se puede reutilizar el formato JFLAP por estándar de la práctica
        AutomataExporter.a_jff(automata, ruta_archivo)