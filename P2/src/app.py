import flet as ft
from automata import Automata
from parser import AutomataParser
from exporter import AutomataExporter
from operaciones import OperacionesLenguaje

def main(page: ft.Page):
    page.title = "Simulador de Autómatas Finitos"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    # Estado global del autómata activo
    automata_actual = Automata()

    # File Pickers para cargar y guardar
    def al_seleccionar_archivo(e: ft.FilePickerResultEvent):
        nonlocal automata_actual
        if e.files and len(e.files) > 0:
            ruta = e.files[0].path
            try:
                automata_actual = AutomataParser.cargar_desde_archivo(ruta)
                actualizar_vistas_definicion()
                txt_status_carga.value = f"✅ Cargado exitosamente desde: {ruta}"
                txt_status_carga.color = ft.Colors.GREEN_400
            except Exception as err:
                txt_status_carga.value = f"❌ Error al cargar: {str(err)}"
                txt_status_carga.color = ft.Colors.RED_400
            page.update()

    def al_guardar_archivo(e: ft.FilePickerResultEvent):
        if e.path:
            ruta = e.path
            try:
                if ruta.endswith('.json'):
                    AutomataExporter.a_json(automata_actual, ruta)
                elif ruta.endswith('.jff'):
                    AutomataExporter.a_jff(automata_actual, ruta)
                else:
                    AutomataExporter.a_xml(automata_actual, ruta)
                txt_status_carga.value = f"✅ Guardado exitosamente en: {ruta}"
                txt_status_carga.color = ft.Colors.GREEN_400
            except Exception as err:
                txt_status_carga.value = f"❌ Error al guardar: {str(err)}"
                txt_status_carga.color = ft.Colors.RED_400
            page.update()

    file_picker_abrir = ft.FilePicker(on_result=al_seleccionar_archivo)
    file_picker_guardar = ft.FilePicker(on_result=al_guardar_archivo)
    page.overlay.append(file_picker_abrir)
    page.overlay.append(file_picker_guardar)
    page.update()

    # -------------------------------------------------------------
    # PESTAÑA 1: DEFINICIÓN INTERACTIVA (Punto 3.1)
    # -------------------------------------------------------------
    tf_alfabeto = ft.TextField(label="Alfabeto (separado por comas)", value="0, 1", expand=True)
    tf_estados = ft.TextField(label="Estados (separados por comas)", value="q0, q1", expand=True)
    tf_q0 = ft.TextField(label="Estado Inicial", value="q0", width=150)
    tf_finales = ft.TextField(label="Estados de Aceptación (por comas)", value="q1", expand=True)

    # Transición rápida
    tf_origen = ft.TextField(label="Origen", width=100)
    tf_simbolo = ft.TextField(label="Símbolo (vacio para λ)", width=120)
    tf_destino = ft.TextField(label="Destino", width=100)
    col_transiciones = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=200)

    def guardar_definicion_basica(e):
        nonlocal automata_actual
        alf = [x.strip() for x in tf_alfabeto.value.split(",") if x.strip()]
        est = [x.strip() for x in tf_estados.value.split(",") if x.strip()]
        fin = [x.strip() for x in tf_finales.value.split(",") if x.strip()]
        q0 = tf_q0.value.strip()

        automata_actual.alfabeto = set(alf)
        automata_actual.estados = set(est)
        automata_actual.estado_inicial = q0
        automata_actual.estados_aceptacion = set(fin)

        actualizar_vistas_definicion()
        page.update()

    def agregar_transicion_gui(e):
        try:
            o = tf_origen.value.strip()
            s = tf_simbolo.value.strip()
            d = tf_destino.value.strip()
            automata_actual.agregar_transicion(o, s, d)
            tf_origen.value = ""
            tf_simbolo.value = ""
            tf_destino.value = ""
            actualizar_vistas_definicion()
            page.update()
        except Exception as err:
            page.open(ft.SnackBar(ft.Text(f"Error: {str(err)}")))

    def actualizar_vistas_definicion():
        tf_alfabeto.value = ", ".join(sorted(automata_actual.alfabeto))
        tf_estados.value = ", ".join(sorted(automata_actual.estados))
        tf_q0.value = automata_actual.estado_inicial or ""
        tf_finales.value = ", ".join(sorted(automata_actual.estados_aceptacion))

        # Reconstruir lista visual de transiciones
        col_transiciones.controls.clear()
        for (o, s), destinos in automata_actual.transiciones.items():
            sym = s if s != "" else "λ"
            for d in destinos:
                col_transiciones.controls.append(
                    ft.Text(f"δ({o}, '{sym}') ➔ {d}", size=14)
                )

    tab_definicion = ft.Container(
        padding=10,
        content=ft.Column([
            ft.Text("Quíntupla del Autómata", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([tf_alfabeto, tf_estados]),
            ft.Row([tf_q0, tf_finales]),
            ft.ElevatedButton("Guardar Configuración Básica", on_click=guardar_definicion_basica),
            ft.Divider(),
            ft.Text("Agregar Transiciones", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([tf_origen, tf_simbolo, tf_destino, ft.ElevatedButton("Añadir", on_click=agregar_transicion_gui)]),
            ft.Text("Tabla de Transiciones Registradas:", weight=ft.FontWeight.BOLD),
            col_transiciones
        ])
    )

    # -------------------------------------------------------------
    # PESTAÑA 2: ARCHIVOS .jff / .json / .xml (Punto 3.2 y 3.4)
    # -------------------------------------------------------------
    txt_status_carga = ft.Text("", size=14)

    tab_archivos = ft.Container(
        padding=20,
        content=ft.Column([
            ft.Text("Importación y Exportación de Archivos", size=18, weight=ft.FontWeight.BOLD),
            ft.Text("Soporta formatos .jff (JFLAP), .json y .xml"),
            ft.Row([
                ft.ElevatedButton("Cargar Archivo", icon=ft.icons.UPLOAD_FILE, 
                                  on_click=lambda _: file_picker_abrir.pick_files(allowed_extensions=["jff", "json", "xml"])),
                ft.ElevatedButton("Guardar Archivo", icon=ft.icons.SAVE, 
                                  on_click=lambda _: file_picker_guardar.save_file(allowed_extensions=["jff", "json", "xml"]))
            ]),
            txt_status_carga
        ])
    )

    # -------------------------------------------------------------
    # PESTAÑA 3: SIMULACIÓN Y PASO A PASO (Punto 3.3)
    # -------------------------------------------------------------
    tf_cadena_simular = ft.TextField(label="Cadena a simular", expand=True)
    col_traza = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=300)
    txt_resultado_simulacion = ft.Text("", size=18, weight=ft.FontWeight.BOLD)

    def ejecutar_simulacion(e):
        col_traza.controls.clear()
        cadena = tf_cadena_simular.value.strip()
        valida, traza = automata_actual.simular_paso_a_paso(cadena)

        if valida:
            txt_resultado_simulacion.value = "ACEPTADA ✅"
            txt_resultado_simulacion.color = ft.Colors.GREEN_400
        else:
            txt_resultado_simulacion.value = "RECHAZADA ❌"
            txt_resultado_simulacion.color = ft.Colors.RED_400

        for t in traza:
            if 'error' in t:
                col_traza.controls.append(ft.Text(f"Error: {t['error']}", color=ft.Colors.RED))
            else:
                col_traza.controls.append(
                    ft.Container(
                        content=ft.Text(f"Paso {t['paso']}: {t['descripcion']}"),
                        padding=5,
                        border=ft.border.all(1, ft.Colors.OUTLINE)
                    )
                )
        page.update()

    tab_simulacion = ft.Container(
        padding=10,
        content=ft.Column([
            ft.Text("Simulación y Traza del Recorrido", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([tf_cadena_simular, ft.ElevatedButton("Simular", on_click=ejecutar_simulacion)]),
            txt_resultado_simulacion,
            ft.Divider(),
            ft.Text("Traza de Ejecución Paso a Paso:", weight=ft.FontWeight.BOLD),
            col_traza
        ])
    )

    # -------------------------------------------------------------
    # PESTAÑA 4: OPERACIONES DE LENGUAJES (Punto 3.4)
    # -------------------------------------------------------------
    tf_entrada_operacion = ft.TextField(label="Cadena o Lenguaje (ej. 'aba' o '0, 10')", expand=True)
    txt_res_prefijos = ft.Text("Prefijos: -")
    txt_res_sufijos = ft.Text("Sufijos: -")
    txt_res_subcadenas = ft.Text("Subcadenas: -")
    txt_res_kleene = ft.Text("Cerradura *: -")
    txt_res_positiva = ft.Text("Cerradura +: -")

    def calcular_operaciones(e):
        val = tf_entrada_operacion.value.strip()
        if not val:
            return
        
        # Para prefijos/sufijos/subcadenas usamos la primera palabra o la cadena completa
        cadena = val.split(",")[0].strip()
        pref = OperacionesLenguaje.obtener_prefijos(cadena)
        suf = OperacionesLenguaje.obtener_sufijos(cadena)
        sub = OperacionesLenguaje.obtener_subcadenas(cadena)

        txt_res_prefijos.value = f"Prefijos de '{cadena}': {sorted(list(pref))}"
        txt_res_sufijos.value = f"Sufijos de '{cadena}': {sorted(list(suf))}"
        txt_res_subcadenas.value = f"Subcadenas de '{cadena}': {sorted(list(sub))}"

        # Para cerraduras tratamos la entrada como un lenguaje/lista de cadenas
        lenguaje = [x.strip() for x in val.split(",") if x.strip()]
        kleene = OperacionesLenguaje.cerradura_kleene(lenguaje, n=2)
        positiva = OperacionesLenguaje.cerradura_positiva(lenguaje, n=2)

        txt_res_kleene.value = f"Cerradura Kleene L*: {kleene}"
        txt_res_positiva.value = f"Cerradura Positiva L+: {positiva}"
        page.update()

    tab_operaciones = ft.Container(
        padding=10,
        content=ft.Column([
            ft.Text("Operaciones sobre Cadenas y Lenguajes (Práctica 1)", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([tf_entrada_operacion, ft.ElevatedButton("Calcular", on_click=calcular_operaciones)]),
            ft.Divider(),
            txt_res_prefijos,
            txt_res_sufijos,
            txt_res_subcadenas,
            ft.Divider(),
            txt_res_kleene,
            txt_res_positiva
        ])
    )

    # Tabs de la aplicación
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="1. Definición", content=tab_definicion),
            ft.Tab(text="2. Archivos", content=tab_archivos),
            ft.Tab(text="3. Simulación", content=tab_simulacion),
            ft.Tab(text="4. Operaciones", content=tab_operaciones),
        ],
        expand=True
    )

    page.add(tabs)
# Al final de src/app.py
if __name__ == "__main__":
    ft.app(
        target=main,
        view=ft.AppView.WEB_BROWSER,
        host="0.0.0.0",
        port=8550
    )