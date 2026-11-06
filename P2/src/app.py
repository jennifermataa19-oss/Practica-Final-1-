import os
import flet as ft

from automata import Automata
from parser import AutomataParser
from exporter import AutomataExporter
from operaciones import OperacionesLenguaje
from cerradura_lambda import CerraduraLambdaSimulador
from eliminacion_lambda import EliminadorLambda
from afn_a_afd import ConvertidorSubconjuntos
from minimizacion_afd import MinimizadorAFD
from validador_lote import ValidadorLote
from eliminacion_estados import ConversorAutomataARegex
# Importaciones de la Práctica 4 (Ejercicio 2)
from regex_parser import RegexParser, RegexSyntaxError
from thompson import ConstructorThompson


def formatear_conjunto(conjunto):
    """Devuelve un conjunto como texto ordenado: {q0, q1}."""
    return "{" + ", ".join(sorted(str(x) for x in conjunto)) + "}"


def main(page: ft.Page):
    page.title = "Simulador de Autómatas Finitos y Expresiones Regulares - Práctica 3 & 4"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    automata_actual = Automata()
    automata_sin_lambda_convertido = None
    afd_convertido = None
    afd_minimo_convertido = None
    resultados_lote_actual = []
    nombre_archivo_lote_actual = ""
    afn_thompson_generado = None

    # -------------------------------------------------------------------------
    # COMPONENTES PESTAÑA DEFINICIÓN Y VISTAS GENERALES
    # -------------------------------------------------------------------------
    txt_status_carga = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    txt_definicion_formal = ft.Text("No hay autómata cargado.", size=14, selectable=True)
    data_table_transiciones = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Estado"))],
        rows=[],
    )

    input_cadena_simular = ft.TextField(label="Cadena a simular (ej. 0101)", width=300)
    txt_resultado_simulacion = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    list_pasos_simulacion = ft.ListView(expand=1, spacing=5, padding=10, auto_scroll=True, height=200)

    dropdown_estado_cerradura = ft.Dropdown(label="Seleccionar Estado", width=200, options=[])
    txt_resultado_cerradura = ft.Text("", size=15, weight=ft.FontWeight.BOLD)

    input_cadena_directa = ft.TextField(label="Cadena a simular en AFN-λ", width=300)
    txt_resultado_simulacion_directa = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    data_table_pasos_directos = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Paso")),
            ft.DataColumn(ft.Text("Símbolo")),
            ft.DataColumn(ft.Text("Activos (Antes CL)")),
            ft.DataColumn(ft.Text("Activos (Después CL)")),
            ft.DataColumn(ft.Text("Detalle")),
        ],
        rows=[],
    )

    # Componentes Sección 2.2
    txt_info_conversion_lambda = ft.Text("", size=14, selectable=True)
    txt_explicacion_paso_a_paso_22 = ft.Text("", size=13, selectable=True, font_family="Consolas")
    data_table_pasos_eliminacion = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Estado (q)")),
            ft.DataColumn(ft.Text("Símbolo (a)")),
            ft.DataColumn(ft.Text("1. CL(q)")),
            ft.DataColumn(ft.Text("2. δ(CL(q), a)")),
            ft.DataColumn(ft.Text("3. δ'(q, a) = CL(...)")),
        ],
        rows=[],
    )
    data_table_afn_sin_lambda = ft.DataTable(columns=[ft.DataColumn(ft.Text("Estado"))], rows=[])

    # Componentes Sección 2.3
    txt_info_afd = ft.Text("", size=14, selectable=True)
    txt_mapeo_subconjuntos = ft.Text("", size=13, selectable=True, font_family="Consolas")
    data_table_afd = ft.DataTable(columns=[ft.DataColumn(ft.Text("Estado AFD"))], rows=[])

    # Componentes Sección 2.4
    txt_info_minimizacion = ft.Text("", size=14, selectable=True)
    txt_particiones_historial = ft.Text("", size=13, selectable=True, font_family="Consolas")
    data_table_afd_minimo = ft.DataTable(columns=[ft.DataColumn(ft.Text("Clase"))], rows=[])

    # Componentes Sección 2.5
    txt_status_lote = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    data_table_lote = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Línea")),
            ft.DataColumn(ft.Text("Cadena")),
            ft.DataColumn(ft.Text("Resultado")),
            ft.DataColumn(ft.Text("Estados Activos Finales")),
        ],
        rows=[],
    )

    # -------------------------------------------------------------------------
    # COMPONENTES PRÁCTICA 4 (EJERCICIO 2: ER -> AFN-λ)
    # -------------------------------------------------------------------------
    input_regex = ft.TextField(
        label="Expresión Regular (ej. (a|b)*abb)",
        width=400,
        hint_text="Operadores válidos: |, +, *, (), ."
    )
    txt_status_regex = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    txt_pasos_thompson = ft.Text("", size=13, selectable=True, font_family="Consolas")
    data_table_thompson = ft.DataTable(columns=[ft.DataColumn(ft.Text("Estado"))], rows=[])
    btn_cargar_en_p3 = ft.ElevatedButton(
        "Cargar AFN-λ en la Práctica 3",
        icon=ft.icons.PLAY_FOR_WORK,
        disabled=True
    )

    input_cadena_op1 = ft.TextField(label="Cadena 1", width=200)
    input_cadena_op2 = ft.TextField(label="Cadena 2", width=200)
    txt_resultado_operacion = ft.Text("", size=15, selectable=True)

    # -------------------------------------------------------------------------
    # FUNCIONES AUXILIARES
    # -------------------------------------------------------------------------
    def obtener_finales(automata_target=None):
        target = automata_target if automata_target else automata_actual
        return getattr(
            target,
            "estados_aceptacion",
            getattr(target, "estados_finales", getattr(target, "finales", set())),
        )

    def actualizar_vistas_definicion():
        finales = obtener_finales()

        if not automata_actual.estados:
            txt_definicion_formal.value = "Autómata vacío."
            data_table_transiciones.columns = [ft.DataColumn(ft.Text("Estado"))]
            data_table_transiciones.rows = []
            dropdown_estado_cerradura.options = []
            dropdown_estado_cerradura.value = None
            page.update()
            return

        txt_definicion_formal.value = (
            "Definición Formal:\n"
            f"• Q = {formatear_conjunto(automata_actual.estados)}\n"
            f"• Σ = {formatear_conjunto(automata_actual.alfabeto)}\n"
            f"• q0 = {automata_actual.estado_inicial}\n"
            f"• F = {formatear_conjunto(finales)}"
        )

        alfabeto_ordenado = sorted(automata_actual.alfabeto)
        columnas = [ft.DataColumn(ft.Text("Estado"))] + [
            ft.DataColumn(ft.Text(simbolo)) for simbolo in alfabeto_ordenado
        ]

        filas = []
        for est in sorted(automata_actual.estados):
            prefijo = ""
            if est == automata_actual.estado_inicial:
                prefijo += "→ "
            if est in finales:
                prefijo += "* "

            celdas = [ft.DataCell(ft.Text(f"{prefijo}{est}"))]

            for simbolo in alfabeto_ordenado:
                destinos = automata_actual.transiciones.get((est, simbolo), set())
                texto = formatear_conjunto(destinos) if destinos else "∅"
                celdas.append(ft.DataCell(ft.Text(texto)))

            filas.append(ft.DataRow(cells=celdas))

        data_table_transiciones.columns = columnas
        data_table_transiciones.rows = filas

        estados_ordenados = sorted(automata_actual.estados)
        dropdown_estado_cerradura.options = [ft.dropdown.Option(est) for est in estados_ordenados]
        if estados_ordenados:
            dropdown_estado_cerradura.value = estados_ordenados[0]

        page.update()

    def limpiar_resultados():
        nonlocal resultados_lote_actual, nombre_archivo_lote_actual
        list_pasos_simulacion.controls.clear()
        txt_resultado_simulacion.value = ""
        txt_resultado_cerradura.value = ""
        txt_resultado_simulacion_directa.value = ""
        data_table_pasos_directos.rows = []
        txt_info_conversion_lambda.value = ""
        txt_explicacion_paso_a_paso_22.value = ""
        data_table_afn_sin_lambda.rows = []
        data_table_pasos_eliminacion.rows = []
        txt_info_afd.value = ""
        txt_mapeo_subconjuntos.value = ""
        data_table_afd.rows = []
        txt_info_minimizacion.value = ""
        txt_particiones_historial.value = ""
        data_table_afd_minimo.rows = []
        txt_status_lote.value = ""
        data_table_lote.rows = []
        btn_guardar_reporte_lote.disabled = True
        resultados_lote_actual = []
        nombre_archivo_lote_actual = ""

    # -------------------------------------------------------------------------
    # MANEJADORES DE PRÁCTICA 4: CONSTRUCCIÓN DE THOMPSON
    # -------------------------------------------------------------------------
    def ejecutar_construccion_thompson(e):
        nonlocal afn_thompson_generado
        patron = input_regex.value.strip() if input_regex.value else ""

        if not patron:
            txt_status_regex.value = "⚠️ Ingresa una expresión regular."
            txt_status_regex.color = ft.colors.ORANGE_400
            page.update()
            return

        try:
            # 1. Parsear la expresión regular
            ast, patron_formateado = RegexParser.parse(patron)

            # 2. Construir AFN-λ por Thompson
            constructor = ConstructorThompson()
            afn_thompson_generado, historial = constructor.construir(ast)

            txt_status_regex.value = (
                f"✅ Expresión VÁLIDA: '{patron}'\n"
                f"• Estados creados: {len(afn_thompson_generado.estados)}\n"
                f"• Alfabeto Σ: {formatear_conjunto(afn_thompson_generado.alfabeto)}\n"
                f"• Estado Inicial: {afn_thompson_generado.estado_inicial}\n"
                f"• Estado Final: {formatear_conjunto(afn_thompson_generado.estados_aceptacion)}"
            )
            txt_status_regex.color = ft.colors.GREEN_400

            # 3. Mostrar historial paso a paso de Thompson
            lineas = [f"=== CONSTRUCCIÓN DE THOMPSON PASO A PASO ==="]
            for i, paso in enumerate(historial, 1):
                lineas.append(f"Paso {i}: {paso['operacion']}")
                lineas.append(f"  • sub-inicial: {paso['estado_inicial']} | sub-final: {paso['estado_final']}")

            txt_pasos_thompson.value = "\n".join(lineas)

            # 4. Mostrar la tabla de transiciones del AFN-λ resultante
            alfabeto_ordenado = sorted(afn_thompson_generado.alfabeto.union({"λ"}))
            columnas = [ft.DataColumn(ft.Text("Estado"))] + [ft.DataColumn(ft.Text(s)) for s in alfabeto_ordenado]

            filas = []
            finales = afn_thompson_generado.estados_aceptacion
            for est in sorted(afn_thompson_generado.estados, key=lambda x: int(x[1:]) if x[1:].isdigit() else x):
                prefijo = ""
                if est == afn_thompson_generado.estado_inicial:
                    prefijo += "→ "
                if est in finales:
                    prefijo += "* "

                celdas = [ft.DataCell(ft.Text(f"{prefijo}{est}"))]
                for s in alfabeto_ordenado:
                    destinos = afn_thompson_generado.transiciones.get((est, s), set())
                    celdas.append(ft.DataCell(ft.Text(formatear_conjunto(destinos) if destinos else "∅")))

                filas.append(ft.DataRow(cells=celdas))

            data_table_thompson.columns = columnas
            data_table_thompson.rows = filas
            btn_cargar_en_p3.disabled = False

        except RegexSyntaxError as err:
            # Resaltar la posición exacta del error
            marcador = " " * err.posicion + "^"
            txt_status_regex.value = (
                f"❌ ERROR SINTÁCTICO en la posición {err.posicion}:\n"
                f"  {patron}\n"
                f"  {marcador}\n"
                f"Mensaje: {err.mensaje}"
            )
            txt_status_regex.color = ft.colors.RED_400
            txt_pasos_thompson.value = ""
            data_table_thompson.rows = []
            btn_cargar_en_p3.disabled = True
        except Exception as err:
            txt_status_regex.value = f"❌ Error insospechado: {err}"
            txt_status_regex.color = ft.colors.RED_400
            btn_cargar_en_p3.disabled = True

        page.update()

    def enviar_afn_thompson_a_p3(e):
        nonlocal automata_actual
        if not afn_thompson_generado:
            return

        automata_actual = afn_thompson_generado
        limpiar_resultados()
        actualizar_vistas_definicion()

        txt_status_carga.value = f"✅ AFN-λ de Thompson cargado exitosamente en el sistema general."
        txt_status_carga.color = ft.colors.GREEN_400
        tabs.selected_index = 0
        page.update()

    btn_cargar_en_p3.on_click = enviar_afn_thompson_a_p3

    # -------------------------------------------------------------------------
    # MANEJO DE ARCHIVOS Y REPORTES
    # -------------------------------------------------------------------------
    def resolver_ruta_archivo(nombre_archivo):
        rutas_directas = [
            os.path.join(UPLOAD_DIR, nombre_archivo),
            os.path.join("/app", "uploads", nombre_archivo),
            os.path.join(BASE_DIR, "src", "uploads", nombre_archivo),
            os.path.join(BASE_DIR, nombre_archivo),
        ]
        for ruta in rutas_directas:
            if os.path.exists(ruta):
                return ruta

        for root_dir in [UPLOAD_DIR, BASE_DIR]:
            if os.path.exists(root_dir):
                for root, _, files in os.walk(root_dir):
                    if nombre_archivo in files:
                        return os.path.join(root, nombre_archivo)
        return None

    def al_cargar_completado(e: ft.FilePickerUploadEvent):
        nonlocal automata_actual

        if e.error:
            txt_status_carga.value = f"❌ Error de transferencia: {e.error}"
            txt_status_carga.color = ft.colors.RED_400
            page.update()
            return

        if e.progress is not None and e.progress < 1:
            return

        ruta_servidor = resolver_ruta_archivo(e.file_name)

        try:
            if not ruta_servidor:
                raise FileNotFoundError(f"No se encontró el archivo '{e.file_name}' en el servidor.")

            if e.file_name.endswith((".jff", ".xml", ".json")):
                automata_actual = AutomataParser.cargar_desde_archivo(ruta_servidor)
                limpiar_resultados()
                actualizar_vistas_definicion()
                txt_status_carga.value = f"✅ Autómata cargado exitosamente: {e.file_name}"
                txt_status_carga.color = ft.colors.GREEN_400

            elif e.file_name.endswith(".txt"):
                procesar_lote_desde_txt(ruta_servidor, e.file_name)

        except Exception as err:
            txt_status_carga.value = f"❌ Error al procesar el archivo: {err}"
            txt_status_carga.color = ft.colors.RED_400

        page.update()

    def procesar_lote_desde_txt(ruta_servidor, nombre_archivo):
        nonlocal resultados_lote_actual, nombre_archivo_lote_actual

        if not automata_actual.estados:
            txt_status_lote.value = "⚠️ Primero carga un autómata antes de validar cadenas."
            txt_status_lote.color = ft.colors.ORANGE_400
            page.update()
            return

        with open(ruta_servidor, "r", encoding="utf-8") as f:
            contenido = f.read()

        nombre_archivo_lote_actual = nombre_archivo
        resultados_lote_actual = ValidadorLote.validar_cadenas_desde_texto(automata_actual, contenido)

        filas = []
        aceptadas = 0
        for res in resultados_lote_actual:
            color = ft.colors.GREEN_400 if res["es_aceptada"] else ft.colors.RED_400
            if res["es_aceptada"]:
                aceptadas += 1

            filas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(res["linea"]))),
                        ft.DataCell(ft.Text(res["cadena"])),
                        ft.DataCell(ft.Text(res["resultado"], color=color, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(res["estados_finales_alcanzados"])),
                    ]
                )
            )

        data_table_lote.rows = filas
        btn_guardar_reporte_lote.disabled = False

        txt_status_lote.value = (
            f"✅ Lote validado: {len(resultados_lote_actual)} cadenas procesadas. "
            f"({aceptadas} Aceptadas, {len(resultados_lote_actual) - aceptadas} Rechazadas)"
        )
        txt_status_lote.color = ft.colors.GREEN_400
        page.update()

    def generar_y_descargar_informe(e):
        if not resultados_lote_actual:
            txt_status_lote.value = "⚠️ No hay resultados de lote para exportar."
            txt_status_lote.color = ft.colors.ORANGE_400
            page.update()
            return

        try:
            nombre_informe = "informe_validacion_cadenas.txt"
            ruta_informe = os.path.join(UPLOAD_DIR, nombre_informe)

            contenido = ValidadorLote.generar_reporte_texto(nombre_archivo_lote_actual, resultados_lote_actual)

            with open(ruta_informe, "w", encoding="utf-8") as f:
                f.write(contenido)

            txt_status_lote.value = f"✅ Informe generado correctamente en: {ruta_informe}"
            txt_status_lote.color = ft.colors.GREEN_400
        except Exception as err:
            txt_status_lote.value = f"❌ Error al escribir el informe: {err}"
            txt_status_lote.color = ft.colors.RED_400

        page.update()

    btn_guardar_reporte_lote = ft.ElevatedButton(
        "Generar Informe (.txt)",
        icon=ft.icons.SUMMARIZE,
        on_click=generar_y_descargar_informe,
        disabled=True,
    )

    def al_seleccionar_archivo(e: ft.FilePickerResultEvent):
        if not e.files:
            return

        archivo = e.files[0]
        upload_url = page.get_upload_url(archivo.name, 600)

        txt_status_carga.value = f"⏳ Transfiriendo {archivo.name}..."
        txt_status_carga.color = ft.colors.BLUE_400
        page.update()

        file_picker_abrir.upload(
            [ft.FilePickerUploadFile(name=archivo.name, upload_url=upload_url, method="PUT")]
        )

    def al_guardar_archivo(e: ft.FilePickerResultEvent):
        if not e.path:
            return

        try:
            ruta_destino = e.path
            if ruta_destino.endswith(".json"):
                AutomataExporter.a_json(automata_actual, ruta_destino)
            elif ruta_destino.endswith(".jff") or ruta_destino.endswith(".xml"):
                AutomataExporter.a_jff_xml(automata_actual, ruta_destino)
            else:
                ruta_destino += ".json"
                AutomataExporter.a_json(automata_actual, ruta_destino)

            txt_status_carga.value = f"✅ Archivo guardado en: {ruta_destino}"
            txt_status_carga.color = ft.colors.GREEN_400
        except Exception as err:
            txt_status_carga.value = f"❌ Error al guardar archivo: {err}"
            txt_status_carga.color = ft.colors.RED_400

        page.update()

    file_picker_abrir = ft.FilePicker(on_result=al_seleccionar_archivo, on_upload=al_cargar_completado)
    file_picker_guardar = ft.FilePicker(on_result=al_guardar_archivo)

    page.overlay.append(file_picker_abrir)
    page.overlay.append(file_picker_guardar)

    # -------------------------------------------------------------------------
    # MANEJADORES DE EVENTOS PESTAÑAS 2.1 A 2.4
    # -------------------------------------------------------------------------
    def texto_de_paso(paso):
        if not isinstance(paso, dict):
            return str(paso)

        if paso.get("error"):
            return f"Paso {paso.get('paso', '?')}: ❌ {paso['error']}"

        numero = paso.get("paso", "?")
        simbolo = paso.get("simbolo")
        estados = formatear_conjunto(paso.get("estados_actuales", set()))

        if simbolo is None:
            return f"Paso {numero}: inicio → clausura-λ(q0) = {estados}"
        return f"Paso {numero}: símbolo '{simbolo}' → estados activos = {estados}"

    def ejecutar_simulacion(e):
        list_pasos_simulacion.controls.clear()
        cadena = input_cadena_simular.value.strip() if input_cadena_simular.value else ""

        if not automata_actual.estados or not automata_actual.estado_inicial:
            txt_resultado_simulacion.value = "⚠️ Primero carga o define un autómata."
            txt_resultado_simulacion.color = ft.colors.ORANGE_400
            page.update()
            return

        try:
            es_valida, traza = automata_actual.simular_paso_a_paso(cadena)
        except Exception as err:
            txt_resultado_simulacion.value = f"❌ Error durante la simulación: {err}"
            txt_resultado_simulacion.color = ft.colors.RED_400
            page.update()
            return

        for paso in traza:
            list_pasos_simulacion.controls.append(ft.Text(texto_de_paso(paso), size=13, font_family="Consolas"))

        if es_valida:
            txt_resultado_simulacion.value = f"🎉 ¡CADENA ACEPTADA! ('{cadena}')"
            txt_resultado_simulacion.color = ft.colors.GREEN_400
        else:
            txt_resultado_simulacion.value = f"🚫 CADENA RECHAZADA ('{cadena}')"
            txt_resultado_simulacion.color = ft.colors.RED_400

        page.update()

    def calcular_cerradura_individual(e):
        estado_sel = dropdown_estado_cerradura.value
        if not estado_sel:
            txt_resultado_cerradura.value = "⚠️ Selecciona un estado."
            txt_resultado_cerradura.color = ft.colors.ORANGE_400
            page.update()
            return

        try:
            cerradura = CerraduraLambdaSimulador.calcular_cerradura_estado(automata_actual, estado_sel)
            txt_resultado_cerradura.value = f"CL({estado_sel}) = {formatear_conjunto(cerradura)}"
            txt_resultado_cerradura.color = ft.colors.GREEN_400
        except Exception as err:
            txt_resultado_cerradura.value = f"❌ Error: {err}"
            txt_resultado_cerradura.color = ft.colors.RED_400

        page.update()

    def ejecutar_simulacion_directa(e):
        data_table_pasos_directos.rows = []
        cadena = input_cadena_directa.value.strip() if input_cadena_directa.value else ""

        if not automata_actual.estados or not automata_actual.estado_inicial:
            txt_resultado_simulacion_directa.value = "⚠️ Primero carga o define un autómata."
            txt_resultado_simulacion_directa.color = ft.colors.ORANGE_400
            page.update()
            return

        try:
            es_valida, historial = CerraduraLambdaSimulador.simular_directo_paso_a_paso(automata_actual, cadena)
        except Exception as err:
            txt_resultado_simulacion_directa.value = f"❌ Error durante la simulación: {err}"
            txt_resultado_simulacion_directa.color = ft.colors.RED_400
            page.update()
            return

        filas = []
        for paso in historial:
            filas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(paso.get("paso", "")))),
                        ft.DataCell(ft.Text(str(paso.get("simbolo", "")))),
                        ft.DataCell(ft.Text(str(paso.get("activos_antes", "")))),
                        ft.DataCell(ft.Text(str(paso.get("activos_despues", "")))),
                        ft.DataCell(ft.Text(str(paso.get("descripcion", "")))),
                    ]
                )
            )
        data_table_pasos_directos.rows = filas

        if es_valida:
            txt_resultado_simulacion_directa.value = f"🎉 ¡CADENA ACEPTADA DIRECTAMENTE! ('{cadena}')"
            txt_resultado_simulacion_directa.color = ft.colors.GREEN_400
        else:
            txt_resultado_simulacion_directa.value = f"🚫 CADENA RECHAZADA DIRECTAMENTE ('{cadena}')"
            txt_resultado_simulacion_directa.color = ft.colors.RED_400

        page.update()

    def ejecutar_eliminacion_lambda(e):
        nonlocal automata_sin_lambda_convertido
        data_table_afn_sin_lambda.rows = []
        data_table_pasos_eliminacion.rows = []

        if not automata_actual.estados:
            txt_info_conversion_lambda.value = "⚠️ Primero carga o define un autómata."
            txt_info_conversion_lambda.color = ft.colors.ORANGE_400
            page.update()
            return

        try:
            automata_sin_lambda_convertido, reporte = EliminadorLambda.eliminar_transiciones_lambda(automata_actual)
            finales = obtener_finales(automata_sin_lambda_convertido)

            txt_info_conversion_lambda.value = (
                f"✅ Conversión completada exitosamente:\n"
                f"• Q = {formatear_conjunto(automata_sin_lambda_convertido.estados)}\n"
                f"• Σ = {formatear_conjunto(automata_sin_lambda_convertido.alfabeto)}\n"
                f"• q0 = {automata_sin_lambda_convertido.estado_inicial}\n"
                f"• F' = {formatear_conjunto(finales)}"
            )
            txt_info_conversion_lambda.color = ft.colors.GREEN_400

            lineas_pasos = ["=== PASO 1: CERRADURAS LAMBDA CL(q) ==="]
            for q, cl in sorted(reporte["cerraduras_individuales"].items()):
                lineas_pasos.append(f"  • CL({q}) = {formatear_conjunto(cl)}")

            lineas_pasos.append("\n=== PASO 2: DETERMINACIÓN DE ESTADOS FINALES (F') ===")
            lineas_pasos.append(f"  Estados finales originales F = {formatear_conjunto(reporte['finales_originales'])}")

            for item in reporte["estados_finales_calculo"]:
                q = item["estado"]
                cl_str = formatear_conjunto(item["cl_q"])
                inter_str = formatear_conjunto(item["interseccion_F"]) if item["interseccion_F"] else "∅"
                veredicto = "✅ Pertenece a F'" if item["es_final"] else "❌ No pertenece a F'"
                lineas_pasos.append(f"  • CL({q}) = {cl_str} ∩ F = {inter_str}  --->  {veredicto}")

            lineas_pasos.append("\n=== PASO 3: CÁLCULO DE LA FUNCIÓN DE TRANSICIÓN δ'(q, a) ===")
            lineas_pasos.append("  Fórmula: δ'(q, a) = CL( δ( CL(q), a ) )")

            txt_explicacion_paso_a_paso_22.value = "\n".join(lineas_pasos)

            filas_desglose = []
            for item in reporte.get("transiciones_desglose", []):
                filas_desglose.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(item["estado"])),
                            ft.DataCell(ft.Text(item["simbolo"])),
                            ft.DataCell(ft.Text(formatear_conjunto(item["cl_origen"]))),
                            ft.DataCell(ft.Text(formatear_conjunto(item["alcanzables_directos"]) if item["alcanzables_directos"] else "∅")),
                            ft.DataCell(ft.Text(formatear_conjunto(item["resultado_cl"]) if item["resultado_cl"] else "∅")),
                        ]
                    )
                )
            data_table_pasos_eliminacion.rows = filas_desglose

            alfabeto_ordenado = sorted(automata_sin_lambda_convertido.alfabeto)
            columnas = [ft.DataColumn(ft.Text("Estado"))] + [ft.DataColumn(ft.Text(s)) for s in alfabeto_ordenado]

            filas_finales = []
            for est in sorted(automata_sin_lambda_convertido.estados):
                prefijo = ""
                if est == automata_sin_lambda_convertido.estado_inicial:
                    prefijo += "→ "
                if est in finales:
                    prefijo += "* "

                celdas = [ft.DataCell(ft.Text(f"{prefijo}{est}"))]
                for s in alfabeto_ordenado:
                    destinos = automata_sin_lambda_convertido.transiciones.get((est, s), set())
                    celdas.append(ft.DataCell(ft.Text(formatear_conjunto(destinos) if destinos else "∅")))

                filas_finales.append(ft.DataRow(cells=celdas))

            data_table_afn_sin_lambda.columns = columnas
            data_table_afn_sin_lambda.rows = filas_finales

        except Exception as err:
            txt_info_conversion_lambda.value = f"❌ Error durante la conversión: {err}"
            txt_info_conversion_lambda.color = ft.colors.RED_400

        page.update()

    def ejecutar_conversion_afd(e):
        nonlocal afd_convertido
        data_table_afd.rows = []

        if not automata_actual.estados:
            txt_info_afd.value = "⚠️ Primero carga o define un autómata."
            txt_info_afd.color = ft.colors.ORANGE_400
            page.update()
            return

        try:
            afd_convertido, _ = ConvertidorSubconjuntos.afn_a_afd(automata_actual)
            finales = obtener_finales(afd_convertido)

            txt_info_afd.value = (
                f"✅ Conversión a AFD completada exitosamente:\n"
                f"• Q' = {formatear_conjunto(afd_convertido.estados)}\n"
                f"• Σ = {formatear_conjunto(afd_convertido.alfabeto)}\n"
                f"• q0' = {afd_convertido.estado_inicial}\n"
                f"• F' = {formatear_conjunto(finales)}"
            )
            txt_info_afd.color = ft.colors.GREEN_400

            mapeo = getattr(afd_convertido, "mapeo_subconjuntos", {})
            lineas_mapeo = [f"{alias} = {formatear_conjunto(conj)}" for alias, conj in sorted(mapeo.items())]
            txt_mapeo_subconjuntos.value = "Equivalencia de subconjuntos:\n" + "\n".join(lineas_mapeo)

            alfabeto_ordenado = sorted(afd_convertido.alfabeto)
            columnas = [ft.DataColumn(ft.Text("Estado AFD"))] + [ft.DataColumn(ft.Text(s)) for s in alfabeto_ordenado]

            filas = []
            for est in sorted(afd_convertido.estados):
                prefijo = ""
                if est == afd_convertido.estado_inicial:
                    prefijo += "→ "
                if est in finales:
                    prefijo += "* "

                celdas = [ft.DataCell(ft.Text(f"{prefijo}{est}"))]
                for s in alfabeto_ordenado:
                    destinos = afd_convertido.transiciones.get((est, s), set())
                    celdas.append(ft.DataCell(ft.Text(formatear_conjunto(destinos) if destinos else "∅")))

                filas.append(ft.DataRow(cells=celdas))

            data_table_afd.columns = columnas
            data_table_afd.rows = filas
        except Exception as err:
            txt_info_afd.value = f"❌ Error durante la conversión a AFD: {err}"
            txt_info_afd.color = ft.colors.RED_400

        page.update()

    def ejecutar_minimizacion_afd(e):
        nonlocal afd_minimo_convertido
        data_table_afd_minimo.rows = []

        base_automata = afd_convertido if afd_convertido and afd_convertido.estados else automata_actual

        if not base_automata.estados:
            txt_info_minimizacion.value = "⚠️ Primero carga un autómata o conviértelo a AFD."
            txt_info_minimizacion.color = ft.colors.ORANGE_400
            page.update()
            return

        try:
            afd_minimo_convertido, reporte = MinimizadorAFD.minimizar(base_automata)
            finales = obtener_finales(afd_minimo_convertido)

            txt_info_minimizacion.value = (
                f"✅ Minimización completada exitosamente:\n"
                f"• Q_min = {formatear_conjunto(afd_minimo_convertido.estados)}\n"
                f"• Σ = {formatear_conjunto(afd_minimo_convertido.alfabeto)}\n"
                f"• q0_min = {afd_minimo_convertido.estado_inicial}\n"
                f"• F_min = {formatear_conjunto(finales)}"
            )
            txt_info_minimizacion.color = ft.colors.GREEN_400

            lineas = []
            lineas.append("Paso 1: Partición Inicial")
            lineas.append("  " + ",   ".join(reporte["p1_inicial"]))
            lineas.append(f"  {reporte['p1_nombre']}\n")

            for ronda in reporte["rondas"]:
                r_num = ronda["ronda_num"]
                p_nombre = ronda["particion_nombre"]
                lineas.append(f"Paso 2, ronda {r_num} (con {p_nombre})")

                for t_info in ronda["tablas_clases"]:
                    c_name = t_info["clase_analizada"]
                    if t_info.get("tiene_un_solo_estado"):
                        lineas.append(f"  {c_name} tiene un solo estado.")
                    else:
                        lineas.append(f"  La tabla de {c_name} es:")
                        lineas.append(f"    State | Transición | Clase en {p_nombre}")
                        for f in t_info["filas"]:
                            est = f["estado"]
                            t_str = " ".join([f"{k}:{v}" for k, v in f["trans_estados"].items()])
                            c_str = " ".join([f"{k}:{v}" for k, v in f["trans_clases"].items()])
                            lineas.append(f"    {est:5} | {t_str:10} | {c_str}")

                    lineas.append(f"  {t_info['mensaje']}\n")

            lineas.append(f"Paso 4: Autómata Simplificado ({reporte['particion_final_nombre']} = {ronda['particion_nombre']} y terminamos)")
            txt_particiones_historial.value = "\n".join(lineas)

            alfabeto_ordenado = sorted(afd_minimo_convertido.alfabeto)
            columnas = [ft.DataColumn(ft.Text("Clase"))] + [ft.DataColumn(ft.Text(s)) for s in alfabeto_ordenado]

            filas = []
            for est in sorted(afd_minimo_convertido.estados):
                prefijo = ""
                if est == afd_minimo_convertido.estado_inicial:
                    prefijo += "→ "
                if est in finales:
                    prefijo += "* "

                conj_str = formatear_conjunto(reporte["definicion_clases"][est])
                celdas = [ft.DataCell(ft.Text(f"{prefijo}{est} = {conj_str}"))]
                for s in alfabeto_ordenado:
                    destinos = afd_minimo_convertido.transiciones.get((est, s), set())
                    celdas.append(ft.DataCell(ft.Text(formatear_conjunto(destinos) if destinos else "∅")))

                filas.append(ft.DataRow(cells=celdas))

            data_table_afd_minimo.columns = columnas
            data_table_afd_minimo.rows = filas

        except Exception as err:
            txt_info_minimizacion.value = f"❌ Error durante la minimización: {err}"
            txt_info_minimizacion.color = ft.colors.RED_400

        page.update()

    def ejecutar_concatenacion(e):
        c1 = input_cadena_op1.value or ""
        c2 = input_cadena_op2.value or ""
        res = OperacionesLenguaje.concatenar_cadenas(c1, c2)
        txt_resultado_operacion.value = f"Resultado de Concatenación: '{res}'"
        page.update()

    def ejecutar_potencia(e):
        c1 = input_cadena_op1.value or ""
        try:
            n = int(input_cadena_op2.value) if input_cadena_op2.value else 1
            res = OperacionesLenguaje.potencia_cadena(c1, n)
            txt_resultado_operacion.value = f"Resultado de Potencia ('{c1}')^{n}: '{res}'"
        except ValueError:
            txt_resultado_operacion.value = "❌ Ingresa un número entero en Cadena 2 para la potencia."
        page.update()

    def ejecutar_reversa(e):
        c1 = input_cadena_op1.value or ""
        res = OperacionesLenguaje.inversa_cadena(c1)
        txt_resultado_operacion.value = f"Resultado de Inversa: '{res}'"
        page.update()

    # -------------------------------------------------------------------------
    # PESTAÑAS DE LA INTERFAZ
    # -------------------------------------------------------------------------
    tab_definicion = ft.Tab(
        text="Definición y Transiciones",
        icon=ft.icons.TABLE_CHART,
        content=ft.Container(
            padding=15,
            content=ft.Column(
                [
                    ft.Text("Estructura del Autómata", size=20, weight=ft.FontWeight.BOLD),
                    txt_definicion_formal,
                    ft.Divider(),
                    ft.Text("Tabla de Transiciones (δ)", size=16, weight=ft.FontWeight.BOLD),
                    ft.Column([data_table_transiciones], scroll=ft.ScrollMode.AUTO, expand=True),
                ],
                spacing=15,
            ),
        ),
    )

    tab_regex_thompson = ft.Tab(
        text="P4 Expresión Regular",
        icon=ft.icons.CODE,
        content=ft.Container(
            padding=15,
            content=ft.Column(
                [
                    ft.Text("P4 Ejercicio 2: De Expresión Regular a AFN-λ (Thompson)", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [
                            input_regex,
                            ft.ElevatedButton(
                                "Construir AFN-λ",
                                icon=ft.icons.AUTO_AWESOME,
                                on_click=ejecutar_construccion_thompson,
                            ),
                            btn_cargar_en_p3,
                        ],
                        spacing=15,
                    ),
                    txt_status_regex,
                    ft.Divider(),
                    ft.Text("Construcción del Autómata por Thompson Paso a Paso:", size=16, weight=ft.FontWeight.BOLD),
                    txt_pasos_thompson,
                    ft.Divider(),
                    ft.Text("Tabla de Transiciones del AFN-λ Resultante", size=16, weight=ft.FontWeight.BOLD),
                    ft.Column([data_table_thompson], scroll=ft.ScrollMode.AUTO, expand=True),
                ],
                spacing=15,
                scroll=ft.ScrollMode.AUTO,
            ),
        ),
    )

    tab_archivos = ft.Tab(
        text="Archivos",
        icon=ft.icons.FOLDER_OPEN,
        content=ft.Container(
            padding=15,
            content=ft.Column(
                [
                    ft.Text("Importación y Exportación de Archivos", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("Soporta autómatas (.jff, .json, .xml) y lotes de cadenas (.txt)"),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Cargar Autómata o Lote .txt",
                                icon=ft.icons.UPLOAD_FILE,
                                on_click=lambda _: file_picker_abrir.pick_files(
                                    allowed_extensions=["jff", "json", "xml", "txt"],
                                    allow_multiple=False,
                                ),
                            ),
                            ft.ElevatedButton(
                                "Guardar Autómata",
                                icon=ft.icons.SAVE,
                                on_click=lambda _: file_picker_guardar.save_file(
                                    allowed_extensions=["jff", "json", "xml"],
                                    file_name="automata.json",
                                ),
                            ),
                        ],
                        spacing=15,
                    ),
                    txt_status_carga,
                ],
                spacing=15,
            ),
        ),
    )

    tab_simulacion = ft.Tab(
        text="Simulación",
        icon=ft.icons.PLAY_ARROW,
        content=ft.Container(
            padding=15,
            content=ft.Column(
                [
                    ft.Text("Simulación Paso a Paso", size=20, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [
                            input_cadena_simular,
                            ft.ElevatedButton("Simular", icon=ft.icons.PLAY_ARROW, on_click=ejecutar_simulacion),
                        ],
                        spacing=15,
                    ),
                    txt_resultado_simulacion,
                    ft.Divider(),
                    ft.Text("Historial de Rastreo (Clausura-λ):", size=14, weight=ft.FontWeight.BOLD),
                    list_pasos_simulacion,
                ],
                spacing=15,
            ),
        ),
    )

    tab_cerradura_lambda = ft.Tab(
        text="2.1 Cerradura λ & Sim. Directa",
        icon=ft.icons.ACCOUNT_TREE,
        content=ft.Container(
            padding=15,
            content=ft.Column(
                [
                    ft.Text("2.1 Cerradura λ de un Estado", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [
                            dropdown_estado_cerradura,
                            ft.ElevatedButton(
                                "Calcular CL(s)",
                                icon=ft.icons.CALCULATE,
                                on_click=calcular_cerradura_individual,
                            ),
                        ],
                        spacing=15,
                    ),
                    txt_resultado_cerradura,
                    ft.Divider(),
                    ft.Text("Simulación Directa de AFN-λ (Sin conversión)", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [
                            input_cadena_directa,
                            ft.ElevatedButton(
                                "Simular AFN-λ",
                                icon=ft.icons.PLAY_ARROW,
                                on_click=ejecutar_simulacion_directa,
                            ),
                        ],
                        spacing=15,
                    ),
                    txt_resultado_simulacion_directa,
                    ft.Column([data_table_pasos_directos], scroll=ft.ScrollMode.AUTO, expand=True),
                ],
                spacing=15,
                scroll=ft.ScrollMode.AUTO,
            ),
        ),
    )

    tab_eliminacion_lambda = ft.Tab(
        text="2.2 AFN sin λ",
        icon=ft.icons.CLEANING_SERVICES,
        content=ft.Container(
            padding=15,
            content=ft.Column(
                [
                    ft.Text("2.2 Conversión de AFN-λ a AFN (Sin transiciones λ)", size=18, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("Convertir a AFN sin λ", icon=ft.icons.TRANSFORM, on_click=ejecutar_eliminacion_lambda),
                    txt_info_conversion_lambda,
                    ft.Divider(),
                    ft.Text("Procedimiento Detallado Paso a Paso:", size=16, weight=ft.FontWeight.BOLD),
                    txt_explicacion_paso_a_paso_22,
                    ft.Divider(),
                    ft.Text("Desglose Matrimonial de Transiciones: δ'(q, a) = CL(δ(CL(q), a))", size=16, weight=ft.FontWeight.BOLD),
                    ft.Column([data_table_pasos_eliminacion], scroll=ft.ScrollMode.AUTO, expand=True),
                    ft.Divider(),
                    ft.Text("Tabla de Transiciones Resultante (δ')", size=16, weight=ft.FontWeight.BOLD),
                    ft.Column([data_table_afn_sin_lambda], scroll=ft.ScrollMode.AUTO, expand=True),
                ],
                spacing=15,
                scroll=ft.ScrollMode.AUTO,
            ),
        ),
    )

    tab_conversion_afd = ft.Tab(
        text="2.3 AFN → AFD",
        icon=ft.icons.MERGE_TYPE,
        content=ft.Container(
            padding=15,
            content=ft.Column(
                [
                    ft.Text("2.3 Conversión de AFN a AFD (Construcción por Subconjuntos)", size=18, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("Convertir a AFD", icon=ft.icons.AUTO_FIX_HIGH, on_click=ejecutar_conversion_afd),
                    txt_info_afd,
                    ft.Divider(),
                    txt_mapeo_subconjuntos,
                    ft.Divider(),
                    ft.Text("Tabla de Transiciones del AFD Resultante", size=16, weight=ft.FontWeight.BOLD),
                    ft.Column([data_table_afd], scroll=ft.ScrollMode.AUTO, expand=True),
                ],
                spacing=15,
                scroll=ft.ScrollMode.AUTO,
            ),
        ),
    )

    tab_minimizacion_afd = ft.Tab(
        text="2.4 Minimizar AFD",
        icon=ft.icons.COMPRESS,
        content=ft.Container(
            padding=15,
            content=ft.Column(
                [
                    ft.Text("2.4 Minimización de AFD (Algoritmo de Partición)", size=18, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("Minimizar AFD", icon=ft.icons.COMPRESS, on_click=ejecutar_minimizacion_afd),
                    txt_info_minimizacion,
                    ft.Divider(),
                    txt_particiones_historial,
                    ft.Divider(),
                    ft.Text("Tabla de Transiciones del AFD Mínimo", size=16, weight=ft.FontWeight.BOLD),
                    ft.Column([data_table_afd_minimo], scroll=ft.ScrollMode.AUTO, expand=True),
                ],
                spacing=15,
                scroll=ft.ScrollMode.AUTO,
            ),
        ),
    )

    tab_lote_cadenas = ft.Tab(
        text="2.5 Validación en Lote",
        icon=ft.icons.CHECKLIST,
        content=ft.Container(
            padding=15,
            content=ft.Column(
                [
                    ft.Text("2.5 Validación de Varias Cadenas desde Archivo .txt", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Cargar Archivo .txt de Cadenas",
                                icon=ft.icons.UPLOAD_FILE,
                                on_click=lambda _: file_picker_abrir.pick_files(
                                    allowed_extensions=["txt"],
                                    allow_multiple=False,
                                ),
                            ),
                            btn_guardar_reporte_lote,
                        ],
                        spacing=15,
                    ),
                    txt_status_lote,
                    ft.Divider(),
                    ft.Text("Resultados de la Evaluación Masiva:", size=16, weight=ft.FontWeight.BOLD),
                    ft.Column([data_table_lote], scroll=ft.ScrollMode.AUTO, expand=True),
                ],
                spacing=15,
                scroll=ft.ScrollMode.AUTO,
            ),
        ),
    )

    tab_operaciones = ft.Tab(
        text="Operaciones",
        icon=ft.icons.CALCULATE,
        content=ft.Container(
            padding=15,
            content=ft.Column(
                [
                    ft.Text("Operaciones sobre Cadenas y Lenguajes", size=20, weight=ft.FontWeight.BOLD),
                    ft.Row([input_cadena_op1, input_cadena_op2], spacing=15),
                    ft.Row(
                        [
                            ft.ElevatedButton("Concatenar", on_click=ejecutar_concatenacion),
                            ft.ElevatedButton("Potencia", on_click=ejecutar_potencia),
                            ft.ElevatedButton("Inversa", on_click=ejecutar_reversa),
                        ],
                        spacing=10,
                    ),
                    ft.Divider(),
                    txt_resultado_operacion,
                ],
                spacing=15,
            ),
        ),
    )

    txt_status_ej3 = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    txt_resultado_regex_final = ft.Text("", size=16, weight=ft.FontWeight.BOLD, selectable=True)
    txt_historial_eliminacion = ft.Text("", size=13, selectable=True, font_family="Consolas")

    def ejecutar_conversion_a_regex(e):
        if not automata_actual.estados:
            txt_status_ej3.value = "⚠️ Primero carga o define un autómata en formato AFD."
            txt_status_ej3.color = ft.colors.ORANGE_400
            page.update()
            return

        es_puro, mensaje_verificacion = ConversorAutomataARegex.verificar_es_afd_puro(automata_actual)
        if not es_puro:
            txt_status_ej3.value = f"❌ El autómata no es un AFD determinista puro:\n  • {mensaje_verificacion}"
            txt_status_ej3.color = ft.colors.RED_400
            txt_resultado_regex_final.value = ""
            txt_historial_eliminacion.value = ""
            page.update()
            return

        try:
            regex_final, historial = ConversorAutomataARegex.convertir_a_regex(automata_actual)

            txt_status_ej3.value = f"✅ Verificación exitosa: {mensaje_verificacion}"
            txt_status_ej3.color = ft.colors.GREEN_400
            txt_resultado_regex_final.value = f"Exito! Expresión Regular resultante:\n  R = {regex_final}"

            lineas = ["=== HISTORIAL DE ELIMINACIÓN DE ESTADOS ==="]
            for h in historial:
                lineas.append(f"\nPaso {h['paso']}: Estado eliminado '{h['estado_eliminado']}'")
                lineas.append("  Matriz de transiciones parcial:")
                for u, destinos in h["matriz_antes"].items():
                    for v, expr in destinos.items():
                        if expr:
                            lineas.append(f"    R[{u}][{v}] = {expr}")

            txt_historial_eliminacion.value = "\n".join(lineas)

        except Exception as err:
            txt_status_ej3.value = f"❌ Error durante la conversión: {err}"
            txt_status_ej3.color = ft.colors.RED_400

        page.update()

    tab_automata_a_regex = ft.Tab(
        text="P4 Autómata → ER",
        icon=ft.icons.TRANSFORM,
        content=ft.Container(
            padding=15,
            content=ft.Column(
                [
                    ft.Text("P4 Ejercicio 3: De Autómata a Expresión Regular", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text("Importa un AFD, verifica su determinismo y obtén la expresión regular por eliminación de estados."),
                    ft.ElevatedButton(
                        "Verificar y Obtener ER",
                        icon=ft.icons.AUTO_FIX_HIGH,
                        on_click=ejecutar_conversion_a_regex,
                    ),
                    txt_status_ej3,
                    txt_resultado_regex_final,
                    ft.Divider(),
                    ft.Text("Desglose del Autómata Generalizado Paso a Paso:", size=16, weight=ft.FontWeight.BOLD),
                    txt_historial_eliminacion,
                ],
                spacing=15,
                scroll=ft.ScrollMode.AUTO,
            ),
        ),
    )

    tabs = ft.Tabs(
        selected_index=1,
        animation_duration=300,
        tabs=[
            tab_definicion,
            tab_regex_thompson,
            tab_automata_a_regex,  # <--- ¡Asegúrate de incluirla aquí en la lista!
            tab_archivos,
            tab_simulacion,
            tab_cerradura_lambda,
            tab_eliminacion_lambda,
            tab_conversion_afd,
            tab_minimizacion_afd,
            tab_lote_cadenas,
            tab_operaciones,
        ],
        expand=True,
    )

    page.add(tabs)
    actualizar_vistas_definicion()


if __name__ == "__main__":
    ft.app(
        target=main,
        view=ft.AppView.WEB_BROWSER,
        upload_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads")),
        host="0.0.0.0",
        port=8550,
    )