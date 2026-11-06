from typing import Dict, Set, Tuple, List, Any
from automata import Automata

# Mapeo de caracteres numéricos a subíndices Unicode
SUBINDICES = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def a_subindice(texto_o_num) -> str:
    """Convierte cualquier número o texto numérico a sus caracteres subíndices Unicode."""
    return str(texto_o_num).translate(SUBINDICES)


class MinimizadorAFD:
    """
    Módulo de Minimización de AFD implementando el método por rondas y clases 
    (X₀, X₁, X₂...) según el formato del M. en C. Gabriel Hurtado Avilés.
    """

    @staticmethod
    def obtener_estados_alcanzables(automata: Automata) -> Set[str]:
        """Elimina estados inalcanzables desde el estado inicial."""
        if not automata.estado_inicial:
            return set()

        visitados = {automata.estado_inicial}
        pila = [automata.estado_inicial]

        while pila:
            actual = pila.pop()
            for simbolo in sorted(automata.alfabeto):
                destinos = automata.transiciones.get((actual, simbolo), set())
                for dest in destinos:
                    if dest not in visitados:
                        visitados.add(dest)
                        pila.append(dest)

        return visitados

    @staticmethod
    def minimizar(automata_original: Automata) -> Tuple[Automata, Dict[str, Any]]:
        finales_originales = getattr(
            automata_original,
            "estados_aceptacion",
            getattr(automata_original, "estados_finales", getattr(automata_original, "finales", set())),
        )

        alcanzables = MinimizadorAFD.obtener_estados_alcanzables(automata_original)
        alfabeto = sorted(list(automata_original.alfabeto))

        finales = alcanzables.intersection(finales_originales)
        no_finales = alcanzables.difference(finales)

        # Contador global de índices de clase
        contador_clases = 0

        # Mapeo: tuple(estados) -> 'Xᵢ'
        mapeo_clases: Dict[Tuple[str, ...], str] = {}
        # Mapeo inverso: 'Xᵢ' -> set(estados)
        definicion_clases: Dict[str, Set[str]] = {}

        def registrar_clase(conjunto_estados: Set[str]) -> str:
            nonlocal contador_clases
            tup = tuple(sorted(list(conjunto_estados)))
            if tup not in mapeo_clases:
                nombre = f"X{a_subindice(contador_clases)}"
                contador_clases += 1
                mapeo_clases[tup] = nombre
                definicion_clases[nombre] = set(conjunto_estados)
            return mapeo_clases[tup]

        # ---------------------------------------------------------------------
        # PASO 1: Partición Inicial P₁ = {X₀, X₁}
        # ---------------------------------------------------------------------
        x0_name = registrar_clase(no_finales) if no_finales else None
        x1_name = registrar_clase(finales) if finales else None

        particion_actual = []
        if x0_name:
            particion_actual.append(x0_name)
        if x1_name:
            particion_actual.append(x1_name)

        rondas_reporte = []

        def obtener_clase_de_estado(estado: str, particion: List[str]) -> str:
            for c_name in particion:
                if estado in definicion_clases[c_name]:
                    return c_name
            return "?"

        # ---------------------------------------------------------------------
        # PASO 2: Rondas de Refinamiento
        # ---------------------------------------------------------------------
        numero_ronda = 1
        hubo_cambios = True

        while hubo_cambios:
            hubo_cambios = False
            nueva_particion = []

            p_nombre_actual = f"P{a_subindice(numero_ronda)}"
            p_nombre_siguiente = f"P{a_subindice(numero_ronda + 1)}"

            detalles_ronda = {
                "ronda_num": numero_ronda,
                "particion_nombre": p_nombre_actual,
                "tablas_clases": [],
                "siguiente_particion_nombre": p_nombre_siguiente
            }

            for c_name in particion_actual:
                estados_grupo = sorted(list(definicion_clases[c_name]))

                if len(estados_grupo) <= 1:
                    nueva_particion.append(c_name)
                    detalles_ronda["tablas_clases"].append({
                        "clase_analizada": c_name,
                        "tiene_un_solo_estado": True,
                        "mensaje": f"{c_name} tiene un solo estado: {{{', '.join(estados_grupo)}}}."
                    })
                    continue

                filas_tabla = []
                agrupacion_firmas: Dict[Tuple[str, ...], List[str]] = {}

                for est in estados_grupo:
                    trans_estados = {}
                    trans_clases = {}

                    for simb in alfabeto:
                        destinos = automata_original.transiciones.get((est, simb), set())
                        dest = sorted(list(destinos))[0] if destinos else "-"
                        trans_estados[simb] = dest
                        
                        clase_dest = obtener_clase_de_estado(dest, particion_actual) if dest != "-" else "-"
                        trans_clases[simb] = clase_dest

                    firma = tuple(trans_clases[simb] for simb in alfabeto)
                    if firma not in agrupacion_firmas:
                        agrupacion_firmas[firma] = []
                    agrupacion_firmas[firma].append(est)

                    filas_tabla.append({
                        "estado": est,
                        "trans_estados": trans_estados,
                        "trans_clases": trans_clases,
                        "firma": firma
                    })

                subgrupos = list(agrupacion_firmas.values())

                if len(subgrupos) == 1:
                    nueva_particion.append(c_name)
                    detalles_ronda["tablas_clases"].append({
                        "clase_analizada": c_name,
                        "tiene_un_solo_estado": False,
                        "se_divide": False,
                        "filas": filas_tabla,
                        "mensaje": f"Dentro de cada clase los renglones son iguales."
                    })
                else:
                    hubo_cambios = True
                    nuevas_clases_creadas = []
                    for subg in subgrupos:
                        nueva_c_name = registrar_clase(set(subg))
                        nuevas_clases_creadas.append(nueva_c_name)
                        nueva_particion.append(nueva_c_name)

                    detalles_ronda["tablas_clases"].append({
                        "clase_analizada": c_name,
                        "tiene_un_solo_estado": False,
                        "se_divide": True,
                        "filas": filas_tabla,
                        "subgrupos_creados": nuevas_clases_creadas,
                        "mensaje": f"Hay tipos de renglón distintos, así que {c_name} se divide en: " +
                                   ", ".join([f"{name} = {{{', '.join(sorted(list(definicion_clases[name])))}}}" for name in nuevas_clases_creadas])
                    })

            rondas_reporte.append(detalles_ronda)

            if not hubo_cambios:
                break

            particion_actual = nueva_particion
            numero_ronda += 1

            if numero_ronda > 50:
                break

        # ---------------------------------------------------------------------
        # PASO 4: Autómata Simplificado Resultante
        # ---------------------------------------------------------------------
        nuevos_estados = set(particion_actual)
        nuevo_inicial = ""
        nuevos_finales = set()
        nuevas_transiciones = {}

        for c_name in particion_actual:
            conj_estados = definicion_clases[c_name]
            
            if automata_original.estado_inicial in conj_estados:
                nuevo_inicial = c_name
            if bool(conj_estados.intersection(finales_originales)):
                nuevos_finales.add(c_name)

            rep = sorted(list(conj_estados))[0]
            for simb in alfabeto:
                destinos = automata_original.transiciones.get((rep, simb), set())
                if destinos:
                    dest_real = sorted(list(destinos))[0]
                    c_dest = obtener_clase_de_estado(dest_real, particion_actual)
                    nuevas_transiciones[(c_name, simb)] = {c_dest}

        afd_minimo = Automata(
            estados=nuevos_estados,
            alfabeto=set(alfabeto),
            estado_inicial=nuevo_inicial,
            estados_aceptacion=nuevos_finales,
            transiciones=nuevas_transiciones
        )

        setattr(afd_minimo, "mapeo_subconjuntos", definicion_clases)

        p1_nombre = f"P{a_subindice(1)}"
        reporte = {
            "p1_inicial": [
                f"{name} = {{{', '.join(sorted(list(definicion_clases[name])))}}}"
                for name in [x0_name, x1_name] if name
            ],
            "p1_nombre": f"{p1_nombre} = {{{', '.join([n for n in [x0_name, x1_name] if n])}}}",
            "rondas": rondas_reporte,
            "particion_final_nombre": f"P{a_subindice(numero_ronda)}",
            "definicion_clases": definicion_clases
        }

        return afd_minimo, reporte