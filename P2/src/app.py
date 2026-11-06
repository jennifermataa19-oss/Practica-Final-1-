import os
import flet as ft

from automata import Automata
from parser import AutomataParser
from exporter import AutomataExporter
from operaciones import OperacionesLenguaje


def main(page: ft.Page):
    page.title = "Simulador de Autómatas Finitos - Práctica 2"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    # Carpeta unificada en la raíz del proyecto para alojar las subidas
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Autómata activo en la sesión
    automata_actual = Automata()

    # -------------------------------------------------------------------------
    # COMPONENTES DE INTERFAZ
    # -------------------------------------------------------------------------
    txt_status_carga = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    txt_definicion_formal = ft.Text(
        "No hay autómata cargado.", size=14, selectable=True
    )
    data_table_transiciones = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Estado"))],
        rows=[]
    )

    # Componentes para simulación paso a paso
    input_cadena_simular = ft.TextField(
        label="Cadena a simular (ej. 0101)", width=300
    )
    txt_resultado_simulacion = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    list_pasos_simulacion = ft.ListView(
        expand=1, spacing=5, padding=10, auto_scroll=True, height=200
    )

    # Componentes para operaciones sobre lenguajes
    input_cadena_op1 = ft.TextField(label="Cadena 1", width=200)
    input_cadena_op2 = ft.TextField(label="Cadena 2", width=200)
    txt_resultado_operacion = ft.Text("", size=15, selectable=True)

    # -------------------------------------------------------------------------
    # FUNCIONES AUXILIARES DE ACTUALIZACIÓN
    # -------------------------------------------------------------------------
    def actualizar_vistas_definicion():
        """Actualiza la tabla de transiciones y la definición formal en pantalla."""
        if not automata_actual.estados:
            txt_definicion_formal.value = "Autómata vacío."
            data_table_transiciones.columns = [ft.DataColumn(ft.Text("Estado"))]
            data_table_transiciones.rows = []
            page.update()
            return

        # Definición formal (Q, Σ, δ, q0, F)
        q_str = f"Q = {{{', '.join(sorted(automata_actual.estados))}}}"
        alphabet_str = f"Σ = {{{', '.join(sorted(automata_actual.alfabeto))}}}"
        q0_str = f"q0 = {automata_actual.estado_inicial}"
        f_str = f"F = {{{', '.join(sorted(automata_actual.estados_finales))}}}"

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
            if est in automata_actual.estados_finales:
                prefix += "* "

            celdas.append(ft.DataCell(ft.Text(f"{prefix}{est}")))

            for simbolo in alfabeto_ordenado:
                destinos = automata_actual.transiciones.get(est, {}).get(simbolo, set())
                destinos_str = (
                    "{" + ", ".join(sorted(destinos)) + "}" if destinos else "∅"
                )
                celdas.append(ft.DataCell(ft.Text(destinos_str)))

            filas.append(ft.DataRow(cells=celdas))

        data_table_transiciones.columns = columnas
        data_table_transiciones.rows = filas
        page.update()

    # -------------------------------------------------------------------------
    # BUSCADOR DE ARCHIVOS SUBIDOS EN EL CONTENEDOR
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

        # Búsqueda recursiva dentro de la estructura del proyecto
        for root_dir in [UPLOAD_DIR, BASE_DIR]:
            if os.path.exists(root_dir):
                for root, _, files in os.walk(root_dir):
                    if nombre_archivo in files:
                        return os.path.join(root, nombre_archivo)
        return None

    # -------------------------------------------------------------------------
    # MANEJO DE ARCHIVOS (WEB UPLOADS)
    # -------------------------------------------------------------------------
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
        """Genera el upload usando POST explícito para evitar 'Invalid request'."""
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
                    method="POST",
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
    # EVENTOS DE BOTONES
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
        tabs=[tab_definicion, tab_archivos, tab_simulacion, tab_operaciones],
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