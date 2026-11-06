import os
import flet as ft

from automata import Automata
from parser import AutomataParser
from exporter import AutomataExporter
from operaciones import OperacionesLenguaje
from cerradura_lambda import CerraduraLambdaSimulador


def main(page: ft.Page):
    page.title = "Simulador de Autómatas Finitos - Práctica 3"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    # Carpeta unificada en la raíz del proyecto para alojar las subidas
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Autómata activo en la sesión
    automata_actual = Automata()

    # -------------------------------------------------------------------------
    # COMPONENTES DE INTERFAZ (TODAS LAS PESTAÑAS)
    # -------------------------------------------------------------------------
    # Pestaña 1: Definición y Transiciones
    txt_status_carga = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    txt_definicion_formal = ft.Text(
        "No hay autómata cargado.", size=14, selectable=True
    )
    data_table_transiciones = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Estado"))],
        rows=[]
    )

    # Pestaña 2: Simulación Estándar
    input_cadena_simular = ft.TextField(
        label="Cadena a simular (ej. 0101)", width=300
    )
    txt_resultado_simulacion = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    list_pasos_simulacion = ft.ListView(
        expand=1, spacing=5, padding=10, auto_scroll=True, height=200
    )

    # Pestaña 3: Sección 2.1 - Cerradura Lambda & Simulación Directa AFN-λ
    dropdown_estado_cerradura = ft.Dropdown(
        label="Seleccionar Estado", width=200, options=[]
    )
    txt_resultado_cerradura = ft.Text("", size=15, weight=ft.FontWeight.BOLD)

    input_cadena_directa = ft.TextField(
        label="Cadena a simular en AFN-λ", width=300
    )
    txt_resultado_simulacion_directa = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    data_table_pasos_directos = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Paso")),
            ft.DataColumn(ft.Text("Símbolo")),
            ft.DataColumn(ft.Text("Activos (Antes CL)")),
            ft.DataColumn(ft.Text("Activos (Después CL)")),
            ft.DataColumn(ft.Text("Detalle")),
        ],
        rows=[]
    )

    # Pestaña 4: Operaciones sobre Lenguajes
    input_cadena_op1 = ft.TextField(label="Cadena 1", width=200)
    input_cadena_op2 = ft.TextField(label="Cadena 2", width=200)
    txt_resultado_operacion = ft.Text("", size=15, selectable=True)

    # -------------------------------------------------------------------------
    # FUNCIONES AUXILIARES DE ACTUALIZACIÓN
    # -------------------------------------------------------------------------
    
    def actualizar_vistas_definicion():
        """Actualiza la tabla de transiciones, la definición formal y controles."""
        # Detectamos el atributo de estados finales/aceptación
        finales = getattr(
            automata_actual,
            "estados_aceptacion",
            getattr(automata_actual, "estados_finales", getattr(automata_actual, "finales", set())),
        )

        if not automata_actual.estados:
            txt_definicion_formal.value = "Autómata vacío."
            data_table_transiciones.columns = [ft.DataColumn(ft.Text("Estado"))]
            data_table_transiciones.rows = []
            dropdown_estado_cerradura.options = []
            dropdown_estado_cerradura.value = None
            page.update()
            return

        # Definición formal (Q, Σ, δ, q0, F)
        q_str = f"Q = {{{', '.join(sorted(automata_actual.estados))}}}"
        alphabet_str = f"Σ = {{{', '.join(sorted(automata_actual.alfabeto))}}}"
        q0_str = f"q0 = {automata_actual.estado_inicial}"
        f_str = f"F = {{{', '.join(sorted(finales))}}}"

        txt_definicion_formal.value = (
            f"Definición Formal:\n• {q_str}\n• {alphabet_str}\n• {q0_str}\n• {f_str}"
        )

        # Construcción de la Data Table de transiciones
        alfabeto_ordenado = sorted(list(automata_actual.alfabeto))
        columnas = [ft.DataColumn(ft.Text("Estado"))] + [
            ft.DataColumn(ft.Text(simbolo)) for simbolo in alfabeto_ordenado
        ]

        filas = []
        for est in sorted(automata_actual.estados):
            celdas = []
            prefix = ""
            if est == automata_actual.estado_inicial:
                prefix += "→ "
            if est in finales:
                prefix += "* "

            celdas.append(ft.DataCell(ft.Text(f"{prefix}{est}")))

            for simbolo in alfabeto_ordenado:
                # Búsqueda usando la tupla (est, simbolo) que usa tu clase Automata
                destinos = automata_actual.transiciones.get((est, simbolo), set())
                print(repr(est), repr(simbolo), destinos)
                destinos_str = (
                    "{" + ", ".join(sorted(destinos)) + "}" if destinos else "∅"
                )
                celdas.append(ft.DataCell(ft.Text(destinos_str)))

            filas.append(ft.DataRow(cells=celdas))

        data_table_transiciones.columns = columnas
        data_table_transiciones.rows = filas

        # Actualizar opciones del dropdown de estados para Cerradura Lambda (Sec. 2.1)
        dropdown_estado_cerradura.options = [
            ft.dropdown.Option(est) for est in sorted(automata_actual.estados)
        ]
        if automata_actual.estados:
            dropdown_estado_cerradura.value = sorted(list(automata_actual.estados))[0]
        print("TRANSICIONES:", automata_actual.transiciones)
        data_table_transiciones.update()
        page.update()
    # -------------------------------------------------------------------------
    # BUSCADOR Y MANEJO DE ARCHIVOS SUBIDOS (WEB UPLOADS)
    # -------------------------------------------------------------------------
    def resolver_ruta_archivo(nombre_archivo):
        """Ubica el archivo subido dentro de la carpeta uploads o subdirectorios."""
        rutas_directas = [
            os.path.join(UPLOAD_DIR, nombre_archivo),
            os.path.join(BASE_DIR, "uploads", nombre_archivo),
            os.path.join("/app", "uploads", nombre_archivo),
            os.path.join(BASE_DIR, "src", "uploads", nombre_archivo),
            os.path.join(BASE_DIR, nombre_archivo),
        ]
        for r in rutas_directas:
            if os.path.exists(r):
                return r

        # Búsqueda recursiva
        for root_dir in [UPLOAD_DIR, BASE_DIR]:
            if os.path.exists(root_dir):
                for root, _, files in os.walk(root_dir):
                    if nombre_archivo in files:
                        return os.path.join(root, nombre_archivo)
        return None

    def al_cargar_completado(e: ft.FilePickerUploadEvent):
        """Se ejecuta cuando Flet confirma que la subida HTTP finalizó."""
        nonlocal automata_actual
        if e.error:
            txt_status_carga.value = f"❌ Error de transferencia: {e.error}"
            txt_status_carga.color = ft.colors.RED_400
            page.update()
            return

        ruta_servidor = resolver_ruta_archivo(e.file_name)

        try:
            if not ruta_servidor:
                raise FileNotFoundError(
                    f"No se encontró el archivo '{e.file_name}' en el servidor."
                )

            automata_actual = AutomataParser.cargar_desde_archivo(ruta_servidor)
            actualizar_vistas_definicion()
            txt_status_carga.value = f"✅ Autómata cargado exitosamente: {e.file_name}"
            txt_status_carga.color = ft.colors.GREEN_400
        except Exception as err:
            txt_status_carga.value = f"❌ Error al procesar el archivo: {str(err)}"
            txt_status_carga.color = ft.colors.RED_400

        page.update()

    def al_seleccionar_archivo(e: ft.FilePickerResultEvent):
        """Dispara el upload usando PUT (el estándar de subida en Flet Web)."""
        if not e.files or len(e.files) == 0:
            return

        archivo = e.files[0]
        upload_url = page.get_upload_url(archivo.name, 600)

        txt_status_carga.value = f"⏳ Transfiriendo {archivo.name}..."
        txt_status_carga.color = ft.colors.BLUE_400
        page.update()

        file_picker_abrir.upload(
            [
                ft.FilePickerUploadFile(
                    name=archivo.name,
                    upload_url=upload_url,
                    method="PUT",
                )
            ]
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
            txt_status_carga.value = f"❌ Error al guardar archivo: {str(err)}"
            txt_status_carga.color = ft.colors.RED_400

        page.update()

    file_picker_abrir = ft.FilePicker(
        on_result=al_seleccionar_archivo,
        on_upload=al_cargar_completado
    )
    file_picker_guardar = ft.FilePicker(on_result=al_guardar_archivo)

    page.overlay.append(file_picker_abrir)
    page.overlay.append(file_picker_guardar)

    # -------------------------------------------------------------------------
    # MANEJADORES DE EVENTOS DE BOTONES
    # -------------------------------------------------------------------------
    def ejecutar_simulacion(e):
        list_pasos_simulacion.controls.clear()
        cadena = input_cadena_simular.value.strip() if input_cadena_simular.value else ""

        if not automata_actual.estados:
            txt_resultado_simulacion.value = "⚠️ Primero carga o define un autómata."
            txt_resultado_simulacion.color = ft.colors.ORANGE_400
            page.update()
            return

        es_valida, historial_pasos = automata_actual.simular_paso_a_paso(cadena)

        for paso in historial_pasos:
            list_pasos_simulacion.controls.append(
                ft.Text(paso, size=13, font_family="Consolas")
            )

        if es_valida:
            txt_resultado_simulacion.value = f"🎉 ¡CADENA ACEPTADA! ('{cadena}')"
            txt_resultado_simulacion.color = ft.colors.GREEN_400
        else:
            txt_resultado_simulacion.value = f"🚫 CADENA RECHAZADA ('{cadena}')"
            txt_resultado_simulacion.color = ft.colors.RED_400

        page.update()

    def calcular_cerradura_individual(e):
        """Calcula CL(estado) para el estado elegido en la Sección 2.1."""
        estado_sel = dropdown_estado_cerradura.value
        if not estado_sel:
            txt_resultado_cerradura.value = "⚠️ Selecciona un estado."
            txt_resultado_cerradura.color = ft.colors.ORANGE_400
            page.update()
            return

        cerradura = CerraduraLambdaSimulador.calcular_cerradura_estado(
            automata_actual, estado_sel
        )
        txt_resultado_cerradura.value = f"CL({estado_sel}) = {{{', '.join(sorted(cerradura))}}}"
        txt_resultado_cerradura.color = ft.colors.GREEN_400
        page.update()

    def ejecutar_simulacion_directa(e):
        """Ejecuta la simulación directa de AFN-lambda para la Sección 2.1."""
        data_table_pasos_directos.rows.clear()
        cadena = input_cadena_directa.value.strip() if input_cadena_directa.value else ""

        if not automata_actual.estados:
            txt_resultado_simulacion_directa.value = "⚠️ Primero carga o define un autómata."
            txt_resultado_simulacion_directa.color = ft.colors.ORANGE_400
            page.update()
            return

        es_valida, historial = CerraduraLambdaSimulador.simular_directo_paso_a_paso(
            automata_actual, cadena
        )

        filas = []
        for paso in historial:
            filas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(paso["paso"]))),
                        ft.DataCell(ft.Text(paso["simbolo"])),
                        ft.DataCell(ft.Text(paso["activos_antes"])),
                        ft.DataCell(ft.Text(paso["activos_despues"])),
                        ft.DataCell(ft.Text(paso["descripcion"])),
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
                    ft.Column([data_table_transiciones], scroll=ft.ScrollMode.AUTO, expand=True)
                ],
                spacing=15
            )
        )
    )

    tab_archivos = ft.Tab(
        text="Archivos",
        icon=ft.icons.FOLDER_OPEN,
        content=ft.Container(
            padding=15,
            content=ft.Column(
                [
                    ft.Text("Importación y Exportación de Archivos", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("Soporta formatos .jff (JFLAP), .json y .xml"),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Cargar Archivo",
                                icon=ft.icons.UPLOAD_FILE,
                                on_click=lambda _: file_picker_abrir.pick_files(
                                    allowed_extensions=["jff", "json", "xml"],
                                    allow_multiple=False
                                )
                            ),
                            ft.ElevatedButton(
                                "Guardar Archivo",
                                icon=ft.icons.SAVE,
                                on_click=lambda _: file_picker_guardar.save_file(
                                    allowed_extensions=["jff", "json", "xml"],
                                    file_name="automata.json"
                                )
                            ),
                        ],
                        spacing=15
                    ),
                    txt_status_carga
                ],
                spacing=15
            )
        )
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
                            ft.ElevatedButton(
                                "Simular",
                                icon=ft.icons.PLAY_ARROW,
                                on_click=ejecutar_simulacion
                            )
                        ],
                        spacing=15
                    ),
                    txt_resultado_simulacion,
                    ft.Divider(),
                    ft.Text("Historial de Rastreo (Clausura-λ):", size=14, weight=ft.FontWeight.BOLD),
                    list_pasos_simulacion
                ],
                spacing=15
            )
        )
    )

    # Pestaña para la Sección 2.1
    tab_cerradura_lambda = ft.Tab(
        text="Cerradura λ & Sim. Directa",
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
                                on_click=calcular_cerradura_individual
                            )
                        ],
                        spacing=15
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
                                on_click=ejecutar_simulacion_directa
                            )
                        ],
                        spacing=15
                    ),
                    txt_resultado_simulacion_directa,
                    ft.Column([data_table_pasos_directos], scroll=ft.ScrollMode.AUTO, expand=True)
                ],
                spacing=15,
                scroll=ft.ScrollMode.AUTO
            )
        )
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
                        spacing=10
                    ),
                    ft.Divider(),
                    txt_resultado_operacion
                ],
                spacing=15
            )
        )
    )

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            tab_definicion,
            tab_archivos,
            tab_simulacion,
            tab_cerradura_lambda,
            tab_operaciones
        ],
        expand=True
    )

    page.add(tabs)
    actualizar_vistas_definicion()


if __name__ == "__main__":
    ft.app(
        target=main,
        view=ft.AppView.WEB_BROWSER,
        upload_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads")),
        host="0.0.0.0",
        port=8550
    )