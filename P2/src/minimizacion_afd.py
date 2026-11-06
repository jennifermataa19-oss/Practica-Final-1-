from typing import Dict, Set, Tuple, List, Any
from automata import Automata


class MinimizadorAFD:
    """Módulo para minimizar un AFD mediante el algoritmo de partición de estados equivalentes."""

    @staticmethod
    def obtener_estados_alcanzables(automata: Automata) -> Set[str]:
        """Elimina estados inalcanzables desde el estado inicial."""
        if not automata.estado_inicial:
            return set()

        visitados = {automata.estado_inicial}
        pila = [automata.estado_inicial]

        while pila:
            actual = pila.pop()
            for simbolo in automata.alfabeto:
                destinos = automata.transiciones.get((actual, simbolo), set())
                for dest in destinos:
                    if dest not in visitados:
                        visitados.add(dest)
                        pila.append(dest)

        return visitados

    @staticmethod
    def minimizar(automata_original: Automata) -> Tuple[Automata, Dict[str, Any]]:
        """
        Ejecuta la minimización del AFD.
        Retorna:
          - El AFD mínimo resultante.
          - Un reporte detallado con las particiones P0, P1, P2... para la UI.
        """
        finales_originales = getattr(
            automata_original,
            "estados_aceptacion",
            getattr(automata_original, "estados_finales", getattr(automata_original, "finales", set())),
        )

        # 1. Conservar solo estados alcanzables
        alcanzables = MinimizadorAFD.obtener_estados_alcanzables(automata_original)
        alfabeto = sorted(list(automata_original.alfabeto))

        finales_alcanzables = alcanzables.intersection(finales_originales)
        no_finales_alcanzables = alcanzables.difference(finales_alcanzables)

        # 2. Partición Inicial P0
        particion_actual = []
        if no_finales_alcanzables:
            particion_actual.append(sorted(list(no_finales_alcanzables)))
        if finales_alcanzables:
            particion_actual.append(sorted(list(finales_alcanzables)))

        historial_particiones = []
        historial_particiones.append({
            "iteracion": 0,
            "grupos": [list(g) for g in particion_actual],
            "descripcion": f"P0 (No Finales vs Finales)"
        })

        iteracion = 1
        mantenimiento_cambios = True

        # Map auxiliar: estado -> índice del grupo al que pertenece
        def obtener_indice_grupo(estado: str, particion: List[List[str]]) -> int:
            for idx, grupo in enumerate(particion):
                if estado in grupo:
                    return idx
            return -1

        # 3. Refinamiento iterativo de particiones
        while mantenimiento_cambios:
            nueva_particion = []
            mantenimiento_cambios = False

            for grupo in particion_actual:
                if len(grupo) <= 1:
                    nueva_particion.append(grupo)
                    continue

                # Agrupar por firma de transiciones
                subgrupos: Dict[Tuple[int, ...], List[str]] = {}
                for est in grupo:
                    firma = []
                    for simbolo in alfabeto:
                        destinos = automata_original.transiciones.get((est, simbolo), set())
                        dest = list(destinos)[0] if destinos else None
                        idx_dest = obtener_indice_grupo(dest, particion_actual) if dest else -1
                        firma.append(idx_dest)

                    firma_tuple = tuple(firma)
                    if firma_tuple not in subgrupos:
                        subgrupos[firma_tuple] = []
                    subgrupos[firma_tuple].append(est)

                lista_subgrupos = list(subgrupos.values())
                if len(lista_subgrupos) > 1:
                    mantenimiento_cambios = True

                nueva_particion.extend(lista_subgrupos)

            particion_actual = nueva_particion
            historial_particiones.append({
                "iteracion": iteracion,
                "grupos": [list(g) for g in particion_actual],
                "descripcion": f"P{iteracion}"
            })
            iteracion += 1

            if iteracion > 50:  # Salvaguarda de bucle infinito
                break

        # 4. Construcción del AFD Mínimo
        mapa_alias: Dict[Tuple[str, ...], str] = {}
        mapeo_detalle: Dict[str, Set[str]] = {}

        for idx, grupo in enumerate(sorted(particion_actual)):
            alias = f"M{idx}"
            grupo_tuple = tuple(sorted(grupo))
            mapa_alias[grupo_tuple] = alias
            mapeo_detalle[alias] = set(grupo)

        nuevos_estados = set(mapeo_detalle.keys())
        nuevos_finales = set()
        nuevo_inicial = ""

        # Determinar nuevo estado inicial y finales
        for alias, conjunto in mapeo_detalle.items():
            if automata_original.estado_inicial in conjunto:
                nuevo_inicial = alias
            if bool(conjunto.intersection(finales_originales)):
                nuevos_finales.add(alias)

        # Construir nuevas transiciones
        nuevas_transiciones = {}
        for alias, conjunto in mapeo_detalle.items():
            representante = sorted(list(conjunto))[0]
            for simbolo in alfabeto:
                destinos = automata_original.transiciones.get((representante, simbolo), set())
                if destinos:
                    dest_real = list(destinos)[0]
                    # Encontrar el alias del grupo destino
                    for alias_dest, conj_dest in mapeo_detalle.items():
                        if dest_real in conj_dest:
                            nuevas_transiciones[(alias, simbolo)] = {alias_dest}
                            break

        afd_minimo = Automata(
            estados=nuevos_estados,
            alfabeto=set(alfabeto),
            estado_inicial=nuevo_inicial,
            estados_aceptacion=nuevos_finales,
            transiciones=nuevas_transiciones
        )

        setattr(afd_minimo, "mapeo_subconjuntos", mapeo_detalle)

        reporte = {
            "estados_inalcanzables": list(set(automata_original.estados).difference(alcanzables)),
            "historial_particiones": historial_particiones,
            "mapeo_alias": mapeo_detalle
        }

        return afd_minimo, reporte