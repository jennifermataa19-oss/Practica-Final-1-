import os
import re
import flet as ft

# --- Módulos de las prácticas 3 y 4 ------------------------------------------
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
from regex_parser import RegexParser, RegexSyntaxError
from thompson import ConstructorThompson


# =============================================================================
# FUNCIONES AUXILIARES (no dependen de la interfaz)
# =============================================================================
def formatear_conjunto(conjunto):
    """Devuelve un conjunto como texto ordenado: {q0, q1}."""
    return "{" + ", ".join(sorted(str(x) for x in conjunto)) + "}"


def clave_estado(nombre):
    """Orden natural: q2 antes que q10, y nombres raros al final sin romper el sort."""
    m = re.fullmatch(r"(\D*)(\d+)", str(nombre))
    if m:
        return (0, m.group(1), int(m.group(2)))
    return (1, str(nombre), 0)


def obtener_finales(automata):
    """Obtiene los estados de aceptación sin importar cómo se llame el atributo."""
    for attr in ("estados_aceptacion", "estados_finales", "finales"):
        if hasattr(automata, attr):
            return getattr(automata, attr)
    return set()


def con_scroll_horizontal(tabla):
    """Envuelve una tabla para que haga scroll horizontal sin romper el layout."""
    return ft.Row([tabla], scroll=ft.ScrollMode.AUTO)


def llenar_tabla_transiciones(
    tabla, auto, titulo_col="Estado", simbolos_extra=(), etiqueta_estado=None
):
    """
    Rellena un ft.DataTable con la tabla de transiciones de `auto`.
    - simbolos_extra: columnas adicionales (ej. 'λ' en Thompson).
    - etiqueta_estado: función opcional que devuelve el texto extra del estado.
    """
    finales = obtener_finales(auto)
    simbolos = sorted(set(auto.alfabeto) | set(simbolos_extra))

    tabla.columns = [ft.DataColumn(ft.Text(titulo_col))] + [
        ft.DataColumn(ft.Text(s)) for s in simbolos
    ]

    filas = []
    for est in sorted(auto.estados, key=clave_estado):
        prefijo = ""
        if est == auto.estado_inicial:
            prefijo += "→ "
        if est in finales:
            prefijo += "* "

        texto_estado = f"{prefijo}{est}"
        if etiqueta_estado:
            texto_estado += etiqueta_estado(est)

        celdas = [ft.DataCell(ft.Text(texto_estado))]
        for s in simbolos:
            destinos = auto.transiciones.get((est, s), set())
            celdas.append(
                ft.DataCell(ft.Text(formatear_conjunto(destinos) if destinos else "∅"))
            )
        filas.append(ft.DataRow(cells=celdas))

    tabla.rows = filas


def crear_tab(texto, icono, controles):
    """Crea una pestaña estándar: contenedor + columna con scroll vertical."""
    return ft.Tab(
        text=texto,
        icon=icono,
        content=ft.Container(
            padding=15,
            content=ft.Column(controles, spacing=15, scroll=ft.ScrollMode.AUTO),
        ),
    )


# =============================================================================
# APLICACIÓN
# =============================================================================
def main(page: ft.Page):
    page.title = "Simulador de Autómatas Finitos y Expresiones Regulares - Práctica 3 & 4"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # -------------------------------------------------------------------------
    # ESTADO DE LA SESIÓN
    # -------------------------------------------------------------------------
    automata_actual = Automata()
    automata_sin_lambda_convertido = None
    afd_convertido = None
    afd_minimo_convertido = None
    afn_thompson_generado = None
    resultados_lote_actual = []
    nombre_archivo_lote_actual = ""

    # -------------------------------------------------------------------------
    # COMPONENTES: Definición y archivos
    # -------------------------------------------------------------------------
    txt_status_carga = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    txt_definicion_formal = ft.Text("No hay autómata cargado.", size=14, selectable=True)
    data_table_transiciones = ft.DataTable(columns=[ft.DataColumn(ft.Text("Estado"))], rows=[])

    # -------------------------------------------------------------------------
    # COMPONENTES: Simulación estándar
    # -------------------------------------------------------------------------
    input_cadena_simular = ft.TextField(label="Cadena a simular (ej. 0101)", width=300)
    txt_resultado_simulacion = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    list_pasos_simulacion = ft.ListView(spacing=5, padding=10, auto_scroll=True, height=250)

    # -------------------------------------------------------------------------
    # COMPONENTES: 2.1 Cerradura λ y simulación directa
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # COMPONENTES: 2.2 AFN-λ → AFN
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # COMPONENTES: 2.3 AFN → AFD
    # -------------------------------------------------------------------------
    txt_info_afd = ft.Text("", size=14, selectable=True)
    txt_mapeo_subconjuntos = ft.Text("", size=13, selectable=True, font_family="Consolas")
    data_table_afd = ft.DataTable(columns=[ft.DataColumn(ft.Text("Estado AFD"))], rows=[])

    # -------------------------------------------------------------------------
    # COMPONENTES: 2.4 Minimización
    # -------------------------------------------------------------------------
    txt_info_minimizacion = ft.Text("", size=14, selectable=True)
    txt_particiones_historial = ft.Text("", size=13, selectable=True, font_family="Consolas")
    data_table_afd_minimo = ft.DataTable(columns=[ft.DataColumn(ft.Text("Clase"))], rows=[])

    # -------------------------------------------------------------------------
    # COMPONENTES: 2.5 Validación en lote
    # -------------------------------------------------------------------------
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
    btn_guardar_reporte_lote = ft.ElevatedButton(
        "Generar Informe (.txt)", icon=ft.icons.SUMMARIZE, disabled=True
    )

    # -------------------------------------------------------------------------
    # COMPONENTES: P4 ER → AFN-λ (Thompson)
    # -------------------------------------------------------------------------
    input_regex = ft.TextField(
        label="Expresión Regular (ej. (a|b)*abb)",
        width=400,
        hint_text="Operadores válidos: |, +, *, (), .",
    )
    txt_status_regex = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    txt_pasos_thompson = ft.Text("", size=13, selectable=True, font_family="Consolas")
    data_table_thompson = ft.DataTable(columns=[ft.DataColumn(ft.Text("Estado"))], rows=[])
    btn_cargar_en_p3 = ft.ElevatedButton(
        "Cargar AFN-λ en la Práctica 3", icon=ft.icons.PLAY_FOR_WORK, disabled=True
    )

    # -------------------------------------------------------------------------
    # COMPONENTES: P4 Autómata → ER
    # -------------------------------------------------------------------------
    txt_status_ej3 = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    txt_resultado_regex_final = ft.Text("", size=16, weight=ft.FontWeight.BOLD, selectable=True)
    txt_historial_eliminacion = ft.Text("", size=13, selectable=True, font_family="Consolas")

    # -------------------------------------------------------------------------
    # COMPONENTES: Operaciones sobre cadenas
    # -------------------------------------------------------------------------
    input_cadena_op1 = ft.TextField(label="Cadena 1", width=200)
    input_cadena_op2 = ft.TextField(label="Cadena 2", width=200)
    txt_resultado_operacion = ft.Text("", size=15, selectable=True)

    # =========================================================================
    # ACTUALIZACIÓN DE VISTAS
    # =========================================================================
    def actualizar_vistas_definicion():
        if not automata_actual.estados:
            txt_definicion_formal.value = "Autómata vacío."
            data_table_transiciones.columns = [ft.DataColumn(ft.Text("Estado"))]
            data_table_transiciones.rows = []
            dropdown_estado_cerradura.options = []
            dropdown_estado_cerradura.value = None
            page.update()
            return

        finales = obtener_finales(automata_actual)
        txt_definicion_formal.value = (
            "Definición Formal:\n"
            f"• Q = {formatear_conjunto(automata_actual.estados)}\n"
            f"• Σ = {formatear_conjunto(automata_actual.alfabeto)}\n"
            f"• q0 = {automata_actual.estado_inicial}\n"
            f"• F = {formatear_conjunto(finales)}"
        )

        llenar_tabla_transiciones(data_table_transiciones, automata_actual)

        estados_ordenados = sorted(automata_actual.estados, key=clave_estado)
        dropdown_estado_cerradura.options = [ft.dropdown.Option(e) for e in estados_ordenados]
        dropdown_estado_cerradura.value = estados_ordenados[0]

        page.update()

    def limpiar_resultados():
        """Borra resultados de la sesión anterior (se llama al cargar un autómata nuevo)."""
        nonlocal automata_sin_lambda_convertido, afd_convertido, afd_minimo_convertido
        nonlocal resultados_lote_actual, nombre_archivo_lote_actual

        # Importante: si no se resetean, la minimización usaría el AFD del autómata anterior
        automata_sin_lambda_convertido = None
        afd_convertido = None
        afd_minimo_convertido = None
        resultados_lote_actual = []
        nombre_archivo_lote_actual = ""

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
        txt_status_ej3.value = ""
        txt_resultado_regex_final.value = ""
        txt_historial_eliminacion.value = ""

    def avisar_sin_automata(control):
        control.value = "⚠️ Primero carga o define un autómata."
        control.color = ft.colors.ORANGE_400
        page.update()

    # =========================================================================
    # ARCHIVOS: carga, guardado y lote
    # =========================================================================
    def resolver_ruta_archivo(nombre_archivo):
        rutas = [
            os.path.join(UPLOAD_DIR, nombre_archivo),
            os.path.join("/app", "uploads", nombre_archivo),
            os.path.join(BASE_DIR, "src", "uploads", nombre_archivo),
            os.path.join(BASE_DIR, nombre_archivo),
        ]
        for ruta in rutas:
            if os.path.exists(ruta):
                return ruta

        for root_dir in (UPLOAD_DIR, BASE_DIR):
            if os.path.exists(root_dir):
                for root, _, files in os.walk(root_dir):
                    if nombre_archivo in files:
                        return os.path.join(root, nombre_archivo)
        return None

    def procesar_lote_desde_txt(ruta_servidor, nombre_archivo):
        nonlocal resultados_lote_actual, nombre_archivo_lote_actual

        if not automata_actual.estados:
            txt_status_lote.value = "⚠️ Primero carga un autómata antes de validar cadenas."
            txt_status_lote.color = ft.colors.ORANGE_400
            txt_status_carga.value = txt_status_lote.value
            txt_status_carga.color = ft.colors.ORANGE_400
            return

        with open(ruta_servidor, "r", encoding="utf-8") as f:
            contenido = f.read()

        nombre_archivo_lote_actual = nombre_archivo
        resultados_lote_actual = ValidadorLote.validar_cadenas_desde_texto(
            automata_actual, contenido
        )

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
            f"✅ Lote validado: {len(resultados_lote_actual)} cadenas procesadas "
            f"({aceptadas} aceptadas, {len(resultados_lote_actual) - aceptadas} rechazadas)"
        )
        txt_status_lote.color = ft.colors.GREEN_400
        txt_status_carga.value = f"✅ Lote cargado: {nombre_archivo}"
        txt_status_carga.color = ft.colors.GREEN_400

    def al_cargar_completado(e: ft.FilePickerUploadEvent):
        """Flet llama a este evento varias veces (progreso); solo actuamos al 100 %."""
        nonlocal automata_actual

        if e.error:
            txt_status_carga.value = f"❌ Error de transferencia: {e.error}"
            txt_status_carga.color = ft.colors.RED_400
            page.update()
            return

        if e.progress is not None and e.progress < 1:
            return

        try:
            ruta_servidor = resolver_ruta_archivo(e.file_name)
            if not ruta_servidor:
                raise FileNotFoundError(f"No se encontró el archivo '{e.file_name}' en el servidor.")

            nombre = e.file_name.lower()
            if nombre.endswith((".jff", ".xml", ".json")):
                automata_actual = AutomataParser.cargar_desde_archivo(ruta_servidor)
                limpiar_resultados()
                actualizar_vistas_definicion()
                txt_status_carga.value = f"✅ Autómata cargado exitosamente: {e.file_name}"
                txt_status_carga.color = ft.colors.GREEN_400
            elif nombre.endswith(".txt"):
                procesar_lote_desde_txt(ruta_servidor, e.file_name)
            else:
                raise ValueError("Formato no soportado (usa .jff, .xml, .json o .txt).")
        except Exception as err:
            txt_status_carga.value = f"❌ Error al procesar el archivo: {err}"
            txt_status_carga.color = ft.colors.RED_400

        page.update()

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
            ruta = e.path
            if ruta.endswith(".json"):
                AutomataExporter.a_json(automata_actual, ruta)
            elif ruta.endswith((".jff", ".xml")):
                AutomataExporter.a_jff_xml(automata_actual, ruta)
            else:
                ruta += ".json"
                AutomataExporter.a_json(automata_actual, ruta)

            txt_status_carga.value = f"✅ Archivo guardado en: {ruta}"
            txt_status_carga.color = ft.colors.GREEN_400
        except Exception as err:
            txt_status_carga.value = f"❌ Error al guardar archivo: {err}"
            txt_status_carga.color = ft.colors.RED_400

        page.update()

    def generar_informe_lote(e):
        if not resultados_lote_actual:
            txt_status_lote.value = "⚠️ No hay resultados de lote para exportar."
            txt_status_lote.color = ft.colors.ORANGE_400
            page.update()
            return

        try:
            ruta_informe = os.path.join(UPLOAD_DIR, "informe_validacion_cadenas.txt")
            contenido = ValidadorLote.generar_reporte_texto(
                nombre_archivo_lote_actual, resultados_lote_actual
            )
            with open(ruta_informe, "w", encoding="utf-8") as f:
                f.write(contenido)

            txt_status_lote.value = f"✅ Informe generado correctamente en: {ruta_informe}"
            txt_status_lote.color = ft.colors.GREEN_400
        except Exception as err:
            txt_status_lote.value = f"❌ Error al escribir el informe: {err}"
            txt_status_lote.color = ft.colors.RED_400

        page.update()

    btn_guardar_reporte_lote.on_click = generar_informe_lote

    file_picker_abrir = ft.FilePicker(on_result=al_seleccionar_archivo, on_upload=al_cargar_completado)
    file_picker_guardar = ft.FilePicker(on_result=al_guardar_archivo)
    page.overlay.append(file_picker_abrir)
    page.overlay.append(file_picker_guardar)

    # =========================================================================
    # SIMULACIÓN ESTÁNDAR
    # =========================================================================
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
        cadena = (input_cadena_simular.value or "").strip()

        if not automata_actual.estados or not automata_actual.estado_inicial:
            avisar_sin_automata(txt_resultado_simulacion)
            return

        try:
            es_valida, traza = automata_actual.simular_paso_a_paso(cadena)
        except Exception as err:
            txt_resultado_simulacion.value = f"❌ Error durante la simulación: {err}"
            txt_resultado_simulacion.color = ft.colors.RED_400
            page.update()
            return

        for paso in traza:
            list_pasos_simulacion.controls.append(
                ft.Text(texto_de_paso(paso), size=13, font_family="Consolas")
            )

        if es_valida:
            txt_resultado_simulacion.value = f"🎉 ¡CADENA ACEPTADA! ('{cadena}')"
            txt_resultado_simulacion.color = ft.colors.GREEN_400
        else:
            txt_resultado_simulacion.value = f"🚫 CADENA RECHAZADA ('{cadena}')"
            txt_resultado_simulacion.color = ft.colors.RED_400
        page.update()

    # =========================================================================
    # 2.1 CERRADURA λ Y SIMULACIÓN DIRECTA
    # =========================================================================
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
        cadena = (input_cadena_directa.value or "").strip()

        if not automata_actual.estados or not automata_actual.estado_inicial:
            avisar_sin_automata(txt_resultado_simulacion_directa)
            return

        try:
            es_valida, historial = CerraduraLambdaSimulador.simular_directo_paso_a_paso(
                automata_actual, cadena
            )
        except Exception as err:
            txt_resultado_simulacion_directa.value = f"❌ Error durante la simulación: {err}"
            txt_resultado_simulacion_directa.color = ft.colors.RED_400
            page.update()
            return

        data_table_pasos_directos.rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(p.get("paso", "")))),
                    ft.DataCell(ft.Text(str(p.get("simbolo", "")))),
                    ft.DataCell(ft.Text(str(p.get("activos_antes", "")))),
                    ft.DataCell(ft.Text(str(p.get("activos_despues", "")))),
                    ft.DataCell(ft.Text(str(p.get("descripcion", "")))),
                ]
            )
            for p in historial
        ]

        if es_valida:
            txt_resultado_simulacion_directa.value = f"🎉 ¡CADENA ACEPTADA DIRECTAMENTE! ('{cadena}')"
            txt_resultado_simulacion_directa.color = ft.colors.GREEN_400
        else:
            txt_resultado_simulacion_directa.value = f"🚫 CADENA RECHAZADA DIRECTAMENTE ('{cadena}')"
            txt_resultado_simulacion_directa.color = ft.colors.RED_400
        page.update()

    # =========================================================================
    # 2.2 ELIMINACIÓN DE TRANSICIONES λ
    # =========================================================================
    def ejecutar_eliminacion_lambda(e):
        nonlocal automata_sin_lambda_convertido
        data_table_afn_sin_lambda.rows = []
        data_table_pasos_eliminacion.rows = []

        if not automata_actual.estados:
            avisar_sin_automata(txt_info_conversion_lambda)
            return

        try:
            automata_sin_lambda_convertido, reporte = EliminadorLambda.eliminar_transiciones_lambda(
                automata_actual
            )
            nuevo = automata_sin_lambda_convertido

            txt_info_conversion_lambda.value = (
                "✅ Conversión completada exitosamente:\n"
                f"• Q = {formatear_conjunto(nuevo.estados)}\n"
                f"• Σ = {formatear_conjunto(nuevo.alfabeto)}\n"
                f"• q0 = {nuevo.estado_inicial}\n"
                f"• F' = {formatear_conjunto(obtener_finales(nuevo))}"
            )
            txt_info_conversion_lambda.color = ft.colors.GREEN_400

            lineas = ["=== PASO 1: CERRADURAS LAMBDA CL(q) ==="]
            for q, cl in sorted(reporte["cerraduras_individuales"].items(), key=lambda kv: clave_estado(kv[0])):
                lineas.append(f"  • CL({q}) = {formatear_conjunto(cl)}")

            lineas.append("\n=== PASO 2: DETERMINACIÓN DE ESTADOS FINALES (F') ===")
            lineas.append(f"  Estados finales originales F = {formatear_conjunto(reporte['finales_originales'])}")
            for item in reporte["estados_finales_calculo"]:
                q = item["estado"]
                inter = formatear_conjunto(item["interseccion_F"]) if item["interseccion_F"] else "∅"
                veredicto = "✅ Pertenece a F'" if item["es_final"] else "❌ No pertenece a F'"
                lineas.append(f"  • CL({q}) = {formatear_conjunto(item['cl_q'])} ∩ F = {inter}  --->  {veredicto}")

            lineas.append("\n=== PASO 3: CÁLCULO DE LA FUNCIÓN DE TRANSICIÓN δ'(q, a) ===")
            lineas.append("  Fórmula: δ'(q, a) = CL( δ( CL(q), a ) )")
            txt_explicacion_paso_a_paso_22.value = "\n".join(lineas)

            data_table_pasos_eliminacion.rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(item["estado"])),
                        ft.DataCell(ft.Text(item["simbolo"])),
                        ft.DataCell(ft.Text(formatear_conjunto(item["cl_origen"]))),
                        ft.DataCell(ft.Text(formatear_conjunto(item["alcanzables_directos"]) if item["alcanzables_directos"] else "∅")),
                        ft.DataCell(ft.Text(formatear_conjunto(item["resultado_cl"]) if item["resultado_cl"] else "∅")),
                    ]
                )
                for item in reporte.get("transiciones_desglose", [])
            ]

            llenar_tabla_transiciones(data_table_afn_sin_lambda, nuevo)

        except Exception as err:
            txt_info_conversion_lambda.value = f"❌ Error durante la conversión: {err}"
            txt_info_conversion_lambda.color = ft.colors.RED_400
        page.update()

    # =========================================================================
    # 2.3 AFN → AFD
    # =========================================================================
    def ejecutar_conversion_afd(e):
        nonlocal afd_convertido
        data_table_afd.rows = []

        if not automata_actual.estados:
            avisar_sin_automata(txt_info_afd)
            return

        try:
            afd_convertido, _ = ConvertidorSubconjuntos.afn_a_afd(automata_actual)

            txt_info_afd.value = (
                "✅ Conversión a AFD completada exitosamente:\n"
                f"• Q' = {formatear_conjunto(afd_convertido.estados)}\n"
                f"• Σ = {formatear_conjunto(afd_convertido.alfabeto)}\n"
                f"• q0' = {afd_convertido.estado_inicial}\n"
                f"• F' = {formatear_conjunto(obtener_finales(afd_convertido))}"
            )
            txt_info_afd.color = ft.colors.GREEN_400

            mapeo = getattr(afd_convertido, "mapeo_subconjuntos", {})
            lineas = [f"{alias} = {formatear_conjunto(conj)}" for alias, conj in sorted(mapeo.items())]
            txt_mapeo_subconjuntos.value = "Equivalencia de subconjuntos:\n" + "\n".join(lineas)

            llenar_tabla_transiciones(data_table_afd, afd_convertido, titulo_col="Estado AFD")
        except Exception as err:
            txt_info_afd.value = f"❌ Error durante la conversión a AFD: {err}"
            txt_info_afd.color = ft.colors.RED_400
        page.update()

    # =========================================================================
    # 2.4 MINIMIZACIÓN
    # =========================================================================
    def ejecutar_minimizacion_afd(e):
        nonlocal afd_minimo_convertido
        data_table_afd_minimo.rows = []

        base = afd_convertido if (afd_convertido and afd_convertido.estados) else automata_actual
        if not base.estados:
            txt_info_minimizacion.value = "⚠️ Primero carga un autómata o conviértelo a AFD."
            txt_info_minimizacion.color = ft.colors.ORANGE_400
            page.update()
            return

        try:
            afd_minimo_convertido, reporte = MinimizadorAFD.minimizar(base)

            txt_info_minimizacion.value = (
                "✅ Minimización completada exitosamente:\n"
                f"• Q_min = {formatear_conjunto(afd_minimo_convertido.estados)}\n"
                f"• Σ = {formatear_conjunto(afd_minimo_convertido.alfabeto)}\n"
                f"• q0_min = {afd_minimo_convertido.estado_inicial}\n"
                f"• F_min = {formatear_conjunto(obtener_finales(afd_minimo_convertido))}"
            )
            txt_info_minimizacion.color = ft.colors.GREEN_400

            lineas = ["Paso 1: Partición Inicial", "  " + ",   ".join(reporte["p1_inicial"]), f"  {reporte['p1_nombre']}\n"]

            ultima_particion = reporte["p1_nombre"]
            for ronda in reporte["rondas"]:
                p_nombre = ronda["particion_nombre"]
                ultima_particion = p_nombre
                lineas.append(f"Paso 2, ronda {ronda['ronda_num']} (con {p_nombre})")

                for t_info in ronda["tablas_clases"]:
                    c_name = t_info["clase_analizada"]
                    if t_info.get("tiene_un_solo_estado"):
                        lineas.append(f"  {c_name} tiene un solo estado.")
                    else:
                        lineas.append(f"  La tabla de {c_name} es:")
                        lineas.append(f"    State | Transición | Clase en {p_nombre}")
                        for f in t_info["filas"]:
                            t_str = " ".join(f"{k}:{v}" for k, v in f["trans_estados"].items())
                            c_str = " ".join(f"{k}:{v}" for k, v in f["trans_clases"].items())
                            lineas.append(f"    {f['estado']:5} | {t_str:10} | {c_str}")
                    lineas.append(f"  {t_info['mensaje']}\n")

            lineas.append(
                f"Paso 4: Autómata Simplificado ({reporte['particion_final_nombre']} = {ultima_particion} y terminamos)"
            )
            txt_particiones_historial.value = "\n".join(lineas)

            definicion = reporte["definicion_clases"]
            llenar_tabla_transiciones(
                data_table_afd_minimo,
                afd_minimo_convertido,
                titulo_col="Clase",
                etiqueta_estado=lambda est: f" = {formatear_conjunto(definicion[est])}",
            )
        except Exception as err:
            txt_info_minimizacion.value = f"❌ Error durante la minimización: {err}"
            txt_info_minimizacion.color = ft.colors.RED_400
        page.update()

    # =========================================================================
    # P4 · ER → AFN-λ (THOMPSON)
    # =========================================================================
    def ejecutar_construccion_thompson(e):
        nonlocal afn_thompson_generado
        patron = (input_regex.value or "").strip()

        if not patron:
            txt_status_regex.value = "⚠️ Ingresa una expresión regular."
            txt_status_regex.color = ft.colors.ORANGE_400
            page.update()
            return

        try:
            ast, _patron_formateado = RegexParser.parse(patron)
            afn_thompson_generado, historial = ConstructorThompson().construir(ast)
            afn = afn_thompson_generado

            txt_status_regex.value = (
                f"✅ Expresión VÁLIDA: '{patron}'\n"
                f"• Estados creados: {len(afn.estados)}\n"
                f"• Alfabeto Σ: {formatear_conjunto(afn.alfabeto)}\n"
                f"• Estado Inicial: {afn.estado_inicial}\n"
                f"• Estado Final: {formatear_conjunto(afn.estados_aceptacion)}"
            )
            txt_status_regex.color = ft.colors.GREEN_400

            lineas = ["=== CONSTRUCCIÓN DE THOMPSON PASO A PASO ==="]
            for i, paso in enumerate(historial, 1):
                lineas.append(f"Paso {i}: {paso['operacion']}")
                lineas.append(f"  • sub-inicial: {paso['estado_inicial']} | sub-final: {paso['estado_final']}")
            txt_pasos_thompson.value = "\n".join(lineas)

            llenar_tabla_transiciones(data_table_thompson, afn, simbolos_extra=("λ",))
            btn_cargar_en_p3.disabled = False

        except RegexSyntaxError as err:
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
            txt_status_regex.value = f"❌ Error inesperado: {err}"
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

        txt_status_carga.value = "✅ AFN-λ de Thompson cargado exitosamente en el sistema general."
        txt_status_carga.color = ft.colors.GREEN_400
        tabs.selected_index = 0
        page.update()

    btn_cargar_en_p3.on_click = enviar_afn_thompson_a_p3

    # =========================================================================
    # P4 · AUTÓMATA → ER
    # =========================================================================
    def ejecutar_conversion_a_regex(e):
        if not automata_actual.estados:
            avisar_sin_automata(txt_status_ej3)
            return

        es_puro, mensaje = ConversorAutomataARegex.verificar_es_afd_puro(automata_actual)
        if not es_puro:
            txt_status_ej3.value = f"❌ El autómata no es un AFD determinista puro:\n  • {mensaje}"
            txt_status_ej3.color = ft.colors.RED_400
            txt_resultado_regex_final.value = ""
            txt_historial_eliminacion.value = ""
            page.update()
            return

        try:
            regex_final, historial = ConversorAutomataARegex.convertir_a_regex(automata_actual)

            txt_status_ej3.value = f"✅ Verificación exitosa: {mensaje}"
            txt_status_ej3.color = ft.colors.GREEN_400
            txt_resultado_regex_final.value = f"Éxito! Expresión Regular resultante:\n  R = {regex_final}"

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

    # =========================================================================
    # OPERACIONES SOBRE CADENAS
    # =========================================================================
    def ejecutar_concatenacion(e):
        res = OperacionesLenguaje.concatenar_cadenas(input_cadena_op1.value or "", input_cadena_op2.value or "")
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
        res = OperacionesLenguaje.inversa_cadena(input_cadena_op1.value or "")
        txt_resultado_operacion.value = f"Resultado de Inversa: '{res}'"
        page.update()

    # =========================================================================
    # PESTAÑAS
    # =========================================================================
    def titulo(texto, size=16):
        return ft.Text(texto, size=size, weight=ft.FontWeight.BOLD)

    tab_definicion = crear_tab(
        "Definición y Transiciones", ft.icons.TABLE_CHART,
        [
            titulo("Estructura del Autómata", 20),
            txt_definicion_formal,
            ft.Divider(),
            titulo("Tabla de Transiciones (δ)"),
            con_scroll_horizontal(data_table_transiciones),
        ],
    )

    tab_archivos = crear_tab(
        "Archivos", ft.icons.FOLDER_OPEN,
        [
            titulo("Importación y Exportación de Archivos", 20),
            ft.Text("Soporta autómatas (.jff, .json, .xml) y lotes de cadenas (.txt)"),
            ft.Row(
                [
                    ft.ElevatedButton(
                        "Cargar Autómata o Lote .txt",
                        icon=ft.icons.UPLOAD_FILE,
                        on_click=lambda _: file_picker_abrir.pick_files(
                            allowed_extensions=["jff", "json", "xml", "txt"], allow_multiple=False
                        ),
                    ),
                    ft.ElevatedButton(
                        "Guardar Autómata",
                        icon=ft.icons.SAVE,
                        on_click=lambda _: file_picker_guardar.save_file(
                            allowed_extensions=["jff", "json", "xml"], file_name="automata.json"
                        ),
                    ),
                ],
                spacing=15,
            ),
            txt_status_carga,
        ],
    )

    tab_simulacion = crear_tab(
        "Simulación", ft.icons.PLAY_ARROW,
        [
            titulo("Simulación Paso a Paso", 20),
            ft.Row(
                [input_cadena_simular, ft.ElevatedButton("Simular", icon=ft.icons.PLAY_ARROW, on_click=ejecutar_simulacion)],
                spacing=15,
            ),
            txt_resultado_simulacion,
            ft.Divider(),
            titulo("Historial de Rastreo (Clausura-λ):", 14),
            list_pasos_simulacion,
        ],
    )

    tab_cerradura_lambda = crear_tab(
        "2.1 Cerradura λ & Sim. Directa", ft.icons.ACCOUNT_TREE,
        [
            titulo("2.1 Cerradura λ de un Estado", 18),
            ft.Row(
                [dropdown_estado_cerradura, ft.ElevatedButton("Calcular CL(s)", icon=ft.icons.CALCULATE, on_click=calcular_cerradura_individual)],
                spacing=15,
            ),
            txt_resultado_cerradura,
            ft.Divider(),
            titulo("Simulación Directa de AFN-λ (Sin conversión)", 18),
            ft.Row(
                [input_cadena_directa, ft.ElevatedButton("Simular AFN-λ", icon=ft.icons.PLAY_ARROW, on_click=ejecutar_simulacion_directa)],
                spacing=15,
            ),
            txt_resultado_simulacion_directa,
            con_scroll_horizontal(data_table_pasos_directos),
        ],
    )

    tab_eliminacion_lambda = crear_tab(
        "2.2 AFN sin λ", ft.icons.CLEANING_SERVICES,
        [
            titulo("2.2 Conversión de AFN-λ a AFN (Sin transiciones λ)", 18),
            ft.ElevatedButton("Convertir a AFN sin λ", icon=ft.icons.TRANSFORM, on_click=ejecutar_eliminacion_lambda),
            txt_info_conversion_lambda,
            ft.Divider(),
            titulo("Procedimiento Detallado Paso a Paso:"),
            txt_explicacion_paso_a_paso_22,
            ft.Divider(),
            titulo("Desglose de Transiciones: δ'(q, a) = CL(δ(CL(q), a))"),
            con_scroll_horizontal(data_table_pasos_eliminacion),
            ft.Divider(),
            titulo("Tabla de Transiciones Resultante (δ')"),
            con_scroll_horizontal(data_table_afn_sin_lambda),
        ],
    )

    tab_conversion_afd = crear_tab(
        "2.3 AFN → AFD", ft.icons.MERGE_TYPE,
        [
            titulo("2.3 Conversión de AFN a AFD (Construcción por Subconjuntos)", 18),
            ft.ElevatedButton("Convertir a AFD", icon=ft.icons.AUTO_FIX_HIGH, on_click=ejecutar_conversion_afd),
            txt_info_afd,
            ft.Divider(),
            txt_mapeo_subconjuntos,
            ft.Divider(),
            titulo("Tabla de Transiciones del AFD Resultante"),
            con_scroll_horizontal(data_table_afd),
        ],
    )

    tab_minimizacion_afd = crear_tab(
        "2.4 Minimizar AFD", ft.icons.COMPRESS,
        [
            titulo("2.4 Minimización de AFD (Algoritmo de Partición)", 18),
            ft.ElevatedButton("Minimizar AFD", icon=ft.icons.COMPRESS, on_click=ejecutar_minimizacion_afd),
            txt_info_minimizacion,
            ft.Divider(),
            txt_particiones_historial,
            ft.Divider(),
            titulo("Tabla de Transiciones del AFD Mínimo"),
            con_scroll_horizontal(data_table_afd_minimo),
        ],
    )

    tab_lote_cadenas = crear_tab(
        "2.5 Validación en Lote", ft.icons.CHECKLIST,
        [
            titulo("2.5 Validación de Varias Cadenas desde Archivo .txt", 18),
            ft.Row(
                [
                    ft.ElevatedButton(
                        "Cargar Archivo .txt de Cadenas",
                        icon=ft.icons.UPLOAD_FILE,
                        on_click=lambda _: file_picker_abrir.pick_files(
                            allowed_extensions=["txt"], allow_multiple=False
                        ),
                    ),
                    btn_guardar_reporte_lote,
                ],
                spacing=15,
            ),
            txt_status_lote,
            ft.Divider(),
            titulo("Resultados de la Evaluación Masiva:"),
            con_scroll_horizontal(data_table_lote),
        ],
    )

    tab_regex_thompson = crear_tab(
        "P4 Expresión Regular", ft.icons.CODE,
        [
            titulo("P4 Ejercicio 2: De Expresión Regular a AFN-λ (Thompson)", 18),
            ft.Row(
                [
                    input_regex,
                    ft.ElevatedButton("Construir AFN-λ", icon=ft.icons.AUTO_AWESOME, on_click=ejecutar_construccion_thompson),
                    btn_cargar_en_p3,
                ],
                spacing=15,
            ),
            txt_status_regex,
            ft.Divider(),
            titulo("Construcción del Autómata por Thompson Paso a Paso:"),
            txt_pasos_thompson,
            ft.Divider(),
            titulo("Tabla de Transiciones del AFN-λ Resultante"),
            con_scroll_horizontal(data_table_thompson),
        ],
    )

    tab_automata_a_regex = crear_tab(
        "P4 Autómata → ER", ft.icons.TRANSFORM,
        [
            titulo("P4 Ejercicio 3: De Autómata a Expresión Regular", 18),
            ft.Text("Importa un AFD, verifica su determinismo y obtén la expresión regular por eliminación de estados."),
            ft.ElevatedButton("Verificar y Obtener ER", icon=ft.icons.AUTO_FIX_HIGH, on_click=ejecutar_conversion_a_regex),
            txt_status_ej3,
            txt_resultado_regex_final,
            ft.Divider(),
            titulo("Desglose del Autómata Generalizado Paso a Paso:"),
            txt_historial_eliminacion,
        ],
    )

    tab_operaciones = crear_tab(
        "Operaciones", ft.icons.CALCULATE,
        [
            titulo("Operaciones sobre Cadenas y Lenguajes", 20),
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
    )

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        expand=True,
        tabs=[
            # Práctica 3
            tab_definicion,
            tab_archivos,
            tab_simulacion,
            tab_cerradura_lambda,
            tab_eliminacion_lambda,
            tab_conversion_afd,
            tab_minimizacion_afd,
            tab_lote_cadenas,
            # Práctica 4
            tab_regex_thompson,
            tab_automata_a_regex,
            # Extra
            tab_operaciones,
        ],
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