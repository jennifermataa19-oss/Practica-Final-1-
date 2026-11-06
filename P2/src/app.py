import os
import flet as ft

from automata import Automata
from parser import AutomataParser
from exporter import AutomataExporter
from operaciones import OperacionesLenguaje
from cerradura_lambda import CerraduraLambdaSimulador
from eliminacion_lambda import EliminadorLambda


def formatear_conjunto(conjunto):
    """Devuelve un conjunto como texto ordenado: {q0, q1}."""
    return "{" + ", ".join(sorted(str(x) for x in conjunto)) + "}"


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
    automata_sin_lambda_convertido = None

    # -------------------------------------------------------------------------
    # COMPONENTES DE INTERFAZ
    # -------------------------------------------------------------------------
    # Pestaña 1: Definición y Transiciones
    txt_status_carga = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    txt_definicion_formal = ft.Text(
        "No hay autómata cargado.", size=14, selectable=True
    )
    data_table_transiciones = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Estado"))],
        rows=[],
    )

    # Pestaña 3: Simulación estándar
    input_cadena_simular = ft.TextField(
        label="Cadena a simular (ej. 0101)", width=300
    )
    txt_resultado_simulacion = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    list_pasos_simulacion = ft.ListView(
        expand=1, spacing=5, padding=10, auto_scroll=True, height=200
    )

    # Pestaña 4: Sección 2.1 - Cerradura λ y simulación directa AFN-λ
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
        rows=[],
    )

    # Pestaña 5: Sección 2.2 - Eliminación de transiciones λ
    txt_info_conversion_lambda = ft.Text("", size=14, selectable=True)
    data_table_afn_sin_lambda = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Estado"))],
        rows=[],
    )

    # Pestaña 6: Operaciones sobre lenguajes
    input_cadena_op1 = ft.TextField(label="Cadena 1", width=200)
    input_cadena_op2 = ft.TextField(label="Cadena 2", width=200)
    txt_resultado_operacion = ft.Text("", size=15, selectable=True)

    # -------------------------------------------------------------------------
    # FUNCIONES AUXILIARES
    # -------------------------------------------------------------------------
    def obtener_finales(automata_target=None):
        """Obtiene el conjunto de estados de aceptación sin importar el nombre del atributo."""
        target = automata_target if automata_target else automata_actual
        return getattr(
            target,
            "estados_aceptacion",
            getattr(
                target,
                "estados_finales",
                getattr(target, "finales", set()),
            ),
        )

    def actualizar_vistas_definicion():
        """Actualiza la definición formal, la tabla de transiciones y el dropdown."""
        finales = obtener_finales()

        if not automata_actual.estados:
            txt_definicion_formal.value = "Autómata vacío."
            data_table_transiciones.columns = [ft.DataColumn(ft.Text("Estado"))]
            data_table_transiciones.rows = []
            dropdown_estado_cerradura.options = []
            dropdown_estado_cerradura.value = None
            page.update()
            return

        # Definición formal (Q, Σ, q0, F)
        txt_definicion_formal.value = (
            "Definición Formal:\n"
            f"• Q = {formatear_conjunto(automata_actual.estados)}\n"
            f"• Σ = {formatear_conjunto(automata_actual.alfabeto)}\n"
            f"• q0 = {automata_actual.estado_inicial}\n"
            f"• F = {formatear_conjunto(finales)}"
        )

        # Tabla de transiciones
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

        # Dropdown de estados para la cerradura λ
        estados_ordenados = sorted(automata_actual.estados)
        dropdown_estado_cerradura.options = [
            ft.dropdown.Option(est) for est in estados_ordenados
        ]
        if estados_ordenados:
            dropdown_estado_cerradura.value = estados_ordenados[0]

        page.update()

    def limpiar_resultados():
        """Limpia resultados de simulaciones previas al cargar un autómata nuevo."""
        list_pasos_simulacion.controls.clear()
        txt_resultado_simulacion.value = ""
        txt_resultado_cerradura.value = ""
        txt_resultado_simulacion_directa.value = ""
        data_table_pasos_directos.rows = []
        txt_info_conversion_lambda.value = ""
        data_table_afn_sin_lambda.rows = []

    # -------------------------------------------------------------------------
    # MANEJO DE ARCHIVOS (WEB UPLOADS)
    # -------------------------------------------------------------------------
    def resolver_ruta_archivo(nombre_archivo):
        """Ubica el archivo subido dentro de la carpeta uploads o subdirectorios."""
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
        """Se ejecuta cuando Flet confirma el progreso/final de la subida."""
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
                raise FileNotFoundError(
                    f"No se encontró el archivo '{e.file_name}' en el servidor."
                )

            automata_actual = AutomataParser.cargar_desde_archivo(ruta_servidor)
            limpiar_resultados()
            actualizar_vistas_definicion()
            txt_status_carga.value = f"✅ Autómata cargado exitosamente: {e.file_name}"
            txt_status_carga.color = ft.colors.GREEN_400
        except Exception as err:
            txt_status_carga.value = f"❌ Error al procesar el archivo: {err}"
            txt_status_carga.color = ft.colors.RED_400

        page.update()

    def al_seleccionar_archivo(e: ft.FilePickerResultEvent):
        """Dispara la subida del archivo elegido (PUT, estándar de Flet Web)."""
        if not e.files:
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
            txt_status_carga.value = f"❌ Error al guardar archivo: {err}"
            txt_status_carga.color = ft.colors.RED_400

        page.update()

    file_picker_abrir = ft.FilePicker(
        on_result=al_seleccionar_archivo,
        on_upload=al_cargar_completado,
    )
    file_picker_guardar = ft.FilePicker(on_result=al_guardar_archivo)

    page.overlay.append(file_picker_abrir)
    page.overlay.append(file_picker_guardar)

    # -------------------------------------------------------------------------
    # MANEJADORES DE EVENTOS
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

    def calcular_cerradura_individual(e):
        """Calcula CL(estado) para el estado elegido (Sección 2.1)."""
        estado_sel = dropdown_estado_cerradura.value
        if not estado_sel:
            txt_resultado_cerradura.value = "⚠️ Selecciona un estado."
            txt_resultado_cerradura.color = ft.colors.ORANGE_400
            page.update()
            return

        try:
            cerradura = CerraduraLambdaSimulador.calcular_cerradura_estado(
                automata_actual, estado_sel
            )
            txt_resultado_cerradura.value = (
                f"CL({estado_sel}) = {formatear_conjunto(cerradura)}"
            )
            txt_resultado_cerradura.color = ft.colors.GREEN_400
        except Exception as err:
            txt_resultado_cerradura.value = f"❌ Error: {err}"
            txt_resultado_cerradura.color = ft.colors.RED_400

        page.update()

    def ejecutar_simulacion_directa(e):
        """Simulación directa de AFN-λ sin convertir (Sección 2.1)."""
        data_table_pasos_directos.rows = []
        cadena = input_cadena_directa.value.strip() if input_cadena_directa.value else ""

        if not automata_actual.estados or not automata_actual.estado_inicial:
            txt_resultado_simulacion_directa.value = "⚠️ Primero carga o define un autómata."
            txt_resultado_simulacion_directa.color = ft.colors.ORANGE_400
            page.update()
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
        """Conversión de AFN-λ a AFN equivalente sin λ (Sección 2.2)."""
        nonlocal automata_sin_lambda_convertido
        data_table_afn_sin_lambda.rows = []

        if not automata_actual.estados:
            txt_info_conversion_lambda.value = "⚠️ Primero carga o define un autómata."
            txt_info_conversion_lambda.color = ft.colors.ORANGE_400
            page.update()
            return

        try:
            automata_sin_lambda_convertido, _ = EliminadorLambda.eliminar_transiciones_lambda(
                automata_actual
            )

            finales = obtener_finales(automata_sin_lambda_convertido)

            txt_info_conversion_lambda.value = (
                f"✅ Conversión completada exitosamente:\n"
                f"• Q = {formatear_conjunto(automata_sin_lambda_convertido.estados)}\n"
                f"• Σ = {formatear_conjunto(automata_sin_lambda_convertido.alfabeto)}\n"
                f"• q0 = {automata_sin_lambda_convertido.estado_inicial}\n"
                f"• F = {formatear_conjunto(finales)}"
            )
            txt_info_conversion_lambda.color = ft.colors.GREEN_400

            alfabeto_ordenado = sorted(automata_sin_lambda_convertido.alfabeto)
            columnas = [ft.DataColumn(ft.Text("Estado"))] + [
                ft.DataColumn(ft.Text(s)) for s in alfabeto_ordenado
            ]

            filas = []
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

                filas.append(ft.DataRow(cells=celdas))

            data_table_afn_sin_lambda.columns = columnas
            data_table_afn_sin_lambda.rows = filas
        except Exception as err:
            txt_info_conversion_lambda.value = f"❌ Error durante la conversión: {err}"
            txt_info_conversion_lambda.color = ft.colors.RED_400

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
                    ft.Column(
                        [data_table_transiciones],
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
                ],
                spacing=15,
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
                    ft.Text("Soporta formatos .jff (JFLAP), .json y .xml"),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Cargar Archivo",
                                icon=ft.icons.UPLOAD_FILE,
                                on_click=lambda _: file_picker_abrir.pick_files(
                                    allowed_extensions=["jff", "json", "xml"],
                                    allow_multiple=False,
                                ),
                            ),
                            ft.ElevatedButton(
                                "Guardar Archivo",
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
                            ft.ElevatedButton(
                                "Simular",
                                icon=ft.icons.PLAY_ARROW,
                                on_click=ejecutar_simulacion,
                            ),
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
                    ft.Column(
                        [data_table_pasos_directos],
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
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
                    ft.ElevatedButton(
                        "Convertir a AFN sin λ",
                        icon=ft.icons.TRANSFORM,
                        on_click=ejecutar_eliminacion_lambda,
                    ),
                    txt_info_conversion_lambda,
                    ft.Divider(),
                    ft.Text("Tabla de Transiciones del AFN resultante (δ')", size=16, weight=ft.FontWeight.BOLD),
                    ft.Column(
                        [data_table_afn_sin_lambda],
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
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

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            tab_definicion,
            tab_archivos,
            tab_simulacion,
            tab_cerradura_lambda,
            tab_eliminacion_lambda,
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