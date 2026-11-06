import flet as ft
from automata import Automata
from gestor_archivos import GestorArchivos

def main(page: ft.Page):
    page.title = "Simulador de Autómatas - Práctica 2"
    page.window_width = 900
    page.window_height = 700
    page.theme_mode = ft.ThemeMode.DARK

    # Instancia de nuestro núcleo
    aut = Automata()
    
    # Texto para mostrar el estado actual en la interfaz
    lbl_estado_aut = ft.Text("No hay autómata cargado", color=ft.colors.ORANGE_300)

    # --- MANEJADOR DE ARCHIVOS (PICKER) ---
    def archivo_seleccionado(e: ft.FilePickerResultEvent):
        nonlocal aut
        if e.files:
            ruta = e.files[0].path
            try:
                if ruta.endswith(".json"):
                    aut = GestorArchivos.cargar_json(ruta)
                elif ruta.endswith(".jff") or ruta.endswith(".xml"):
                    aut = GestorArchivos.cargar_jff_xml(ruta)
                
                lbl_estado_aut.value = f"¡Autómata cargado con éxito! Estados: {len(aut.estados)}, Alfabeto: {list(aut.alfabeto)}"
                lbl_estado_aut.color = ft.colors.GREEN_300
            except Exception as ex:
                lbl_estado_aut.value = f"Error al cargar el archivo: {str(ex)}"
                lbl_estado_aut.color = ft.colors.RED_300
            page.update()

    file_picker = ft.FilePicker(on_result=archivo_seleccionado)
    page.overlay.append(file_picker)

    # --- PESTAÑA 1: DEFINICIÓN / IMPORTACIÓN ---
    titulo_def = ft.Text("Definición y Carga de Autómatas", size=24, weight="bold")
    btn_cargar = ft.ElevatedButton(
        "Cargar Autómata (.json, .xml, .jff)", 
        icon=ft.icons.UPLOAD_FILE,
        on_click=lambda _: file_picker.pick_files(allow_multiple=False)
    )

    tab_definicion = ft.Tab(
        text="Definición e I/O",
        icon=ft.icons.ACCOUNT_TREE,
        content=ft.Column([
            titulo_def,
            btn_cargar,
            lbl_estado_aut,
        ], spacing=20, padding=20)
    )

    # --- PESTAÑA 2: SIMULADOR ---
    titulo_sim = ft.Text("Simulador de Cadenas", size=24, weight="bold")
    input_cadena = ft.TextField(label="Ingresa una cadena a validar", width=400)
    resultado_sim = ft.Text("", size=16, weight="bold")
    
    def ejecutar_simulacion(e):
        cadena = input_cadena.value
        es_valida, traza = aut.simular_paso_a_paso(cadena)
        
        if es_valida:
            resultado_sim.value = f"✔ Cadena VÁLIDA"
            resultado_sim.color = ft.colors.GREEN_400
        else:
            resultado_sim.value = f"✘ Cadena INVÁLIDA"
            resultado_sim.color = ft.colors.RED_400
        page.update()

    btn_simular = ft.ElevatedButton("Simular", icon=ft.icons.PLAY_ARROW, on_click=ejecutar_simulacion)

    tab_simulacion = ft.Tab(
        text="Simulador",
        icon=ft.icons.PLAY_CIRCLE_OUTLINE,
        content=ft.Column([
            titulo_sim,
            ft.Row([input_cadena, btn_simular]),
            resultado_sim,
        ], spacing=20, padding=20)
    )

    # --- LAYOUT GENERAL ---
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[tab_definicion, tab_simulacion],
        expand=1
    )

    page.add(tabs)

if __name__ == "__main__":
    ft.app(target=main, port=8550, host="0.0.0.0")