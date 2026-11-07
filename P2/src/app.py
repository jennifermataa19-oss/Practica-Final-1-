"""
app.py — Simulador de Autómatas Finitos y Expresiones Regulares (P3 + P4)

Interfaz gráfica con aspecto de JFLAP:
  · barra de menús (Archivo, Entrada, Convertir, Ver, Operaciones, Ayuda)
  · barra de herramientas con iconos
  · pestañas de documento (cada conversión abre su propia pestaña)
  · dibujo del autómata (estados, transiciones, flechas) y vista lado a lado
    "original → resultado" en cada conversión

Toda la lógica (parser, conversiones, minimización, etc.) vive en los módulos
de siempre; este archivo solo se ocupa de la interfaz.
"""
import os
import traceback

import flet as ft

try:
    import flet.canvas as cv
except Exception:  # pragma: no cover - versiones de Flet sin canvas
    cv = None

from automata import Automata
from parser import AutomataParser
from exporter import AutomataExporter
from cerradura_lambda import CerraduraLambdaSimulador
from eliminacion_lambda import EliminadorLambda
from afn_a_afd import ConvertidorSubconjuntos
from minimizacion_afd import MinimizadorAFD
from validador_lote import ValidadorLote
from regex_parser import RegexParser, RegexSyntaxError
from thompson import ConstructorThompson
from eliminacion_estados import ConversorAutomataARegex
from operaciones_avanzadas import OperacionesAvanzadas

import visualizador as viz


# =============================================================================
# PALETA (aspecto JFLAP: gris claro, azul "Ocean", estados amarillos)
# =============================================================================
C = {
    "fondo": "#EEEEEE",
    "barra": "#F6F6F6",
    "tira": "#E4E4E4",
    "blanco": "#FFFFFF",
    "borde": "#B5B5B5",
    "borde_suave": "#D2D2D2",
    "texto": "#2B2B2B",
    "suave": "#6B6B6B",
    "acento": "#6382BF",
    "tab_sel": "#C8DDF2",
    "cabecera": "#EDF2F9",
    "transparente": "#00000000",
}

# colores con los que se resaltan estados en el dibujo
NARANJA = "#FFB347"   # estado(s) activo(s)
VERDE = "#7BD389"     # acepta
ROJO = "#F28B82"      # rechaza
AZUL = "#9EC9F5"      # cerradura λ

AVISOS = {
    "ok": ("#E8F5E9", "#2E7D32", ft.icons.CHECK_CIRCLE),
    "error": ("#FDECEA", "#C62828", ft.icons.ERROR_OUTLINE),
    "aviso": ("#FFF8E1", "#8A6D00", ft.icons.WARNING_AMBER),
    "info": ("#E3F2FD", "#1565C0", ft.icons.INFO_OUTLINE),
}

TIPOS = {
    "AFD": ("#E8F5E9", "#2E7D32"),
    "AFD incompleto": ("#FFF8E1", "#8A6D00"),
    "AFN": ("#E3F2FD", "#1565C0"),
    "AFN-λ": ("#F3E5F5", "#6A1B9A"),
}

NEGRITA = ft.FontWeight.BOLD
NORMAL = ft.FontWeight.NORMAL


# =============================================================================
# UTILIDADES (no dependen de la página)
# =============================================================================
def fmt(conjunto):
    """{q0, q1} ordenado; ∅ si está vacío."""
    if not conjunto:
        return "∅"
    return "{" + ", ".join(sorted((str(x) for x in conjunto), key=viz.clave_estado)) + "}"


def chip(texto, fondo, color, tam=11):
    return ft.Container(
        content=ft.Text(texto, size=tam, color=color, weight=NEGRITA),
        bgcolor=fondo,
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
        border_radius=10,
    )


def chip_tipo(auto):
    tipo = viz.tipo_automata(auto)
    fondo, color = TIPOS.get(tipo, ("#EEEEEE", "#555555"))
    return chip(tipo, fondo, color)


def aviso(tipo, texto, mono=False):
    fondo, color, icono = AVISOS[tipo]
    return ft.Container(
        bgcolor=fondo,
        border=ft.border.all(1, color),
        border_radius=3,
        padding=10,
        content=ft.Row(
            [
                ft.Icon(icono, color=color, size=20),
                ft.Text(
                    texto, color=color, size=13, selectable=True, expand=True,
                    font_family="Consolas" if mono else None,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            spacing=10,
        ),
    )


def boton(texto, icono=None, on_click=None, primario=False):
    estilo = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=3),
        bgcolor=C["acento"] if primario else "#F3F3F3",
        color="#FFFFFF" if primario else C["texto"],
        side=ft.BorderSide(1, C["acento"] if primario else "#A8A8A8"),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )
    return ft.ElevatedButton(texto, icon=icono, on_click=on_click, style=estilo)


def tarjeta(titulo, contenido, icono=None, extra=None, ancho=None, expand=None):
    cabecera = []
    if icono:
        cabecera.append(ft.Icon(icono, size=16, color=C["acento"]))
    cabecera.append(ft.Text(titulo, size=13, weight=NEGRITA, color=C["texto"]))
    cabecera.append(ft.Container(expand=True))
    cabecera.extend(extra or [])
    return ft.Container(
        bgcolor=C["blanco"],
        border=ft.border.all(1, C["borde_suave"]),
        border_radius=3,
        padding=12,
        width=ancho,
        expand=expand,
        content=ft.Column(
            [
                ft.Row(cabecera, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                ft.Divider(height=1, color=C["borde_suave"]),
                *contenido,
            ],
            spacing=10,
        ),
    )


def expansion(titulo, controles, abierto=False):
    return ft.Container(
        bgcolor=C["blanco"],
        border=ft.border.all(1, C["borde_suave"]),
        border_radius=3,
        content=ft.ExpansionTile(
            title=ft.Text(titulo, size=13, weight=NEGRITA),
            controls=[ft.Container(padding=ft.padding.all(10), content=c) for c in controles],
            initially_expanded=abierto,
        ),
    )


def mono(texto, altura=None):
    """Texto monoespaciado con scroll (para procedimientos paso a paso)."""
    return ft.Container(
        height=altura,
        bgcolor="#FAFAFA",
        border=ft.border.all(1, C["borde_suave"]),
        border_radius=3,
        padding=10,
        content=ft.Column(
            [ft.Row([ft.Text(texto, size=12, font_family="Consolas", selectable=True, no_wrap=True)],
                    scroll=ft.ScrollMode.AUTO)],
            scroll=ft.ScrollMode.AUTO,
        ),
    )


def tabla(columnas, filas):
    """Tabla simple. Cada celda es un str o un control de Flet."""
    cols = [ft.DataColumn(ft.Text(c, size=12, weight=NEGRITA)) for c in columnas]
    rows = []
    for fila in filas:
        celdas = [ft.DataCell(ft.Text(x, size=12) if isinstance(x, str) else x) for x in fila]
        rows.append(ft.DataRow(cells=celdas))
    return ft.Row(
        [ft.DataTable(
            columns=cols,
            rows=rows,
            border=ft.border.all(1, C["borde_suave"]),
            heading_row_color="#EAF0F8",
            column_spacing=26,
            horizontal_lines=ft.BorderSide(1, "#E4E4E4"),
        )],
        scroll=ft.ScrollMode.AUTO,
    )


def tabla_delta(auto, col0="Estado", etiqueta=None, extra=()):
    """Tabla de transiciones δ con marcas → (inicial) y * (aceptación)."""
    finales = viz.obtener_finales(auto)
    simbolos = sorted(set(auto.alfabeto) | set(extra))
    filas = []
    for est in sorted(auto.estados, key=viz.clave_estado):
        marca = ("→ " if est == auto.estado_inicial else "") + ("* " if est in finales else "")
        nombre = f"{marca}{est}" + (etiqueta(est) if etiqueta else "")
        fila = [ft.Text(nombre, size=12, weight=NEGRITA if est == auto.estado_inicial else NORMAL)]
        for s in simbolos:
            destinos = auto.transiciones.get((est, s), set())
            if destinos:
                fila.append(ft.Text(fmt(destinos), size=12))
            else:
                fila.append(ft.Text("∅", size=12, color="#AAAAAA"))
        filas.append(fila)
    return tabla([col0] + simbolos, filas)


def definicion(auto):
    """Definición formal (Q, Σ, q0, F) en filas etiquetadas."""
    datos = [
        ("Q", fmt(auto.estados)),
        ("Σ", fmt(auto.alfabeto)),
        ("q₀", str(auto.estado_inicial) if auto.estado_inicial else "—"),
        ("F", fmt(viz.obtener_finales(auto))),
    ]
    return ft.Column(
        [ft.Row([ft.Text(k, size=13, weight=NEGRITA, width=26),
                 ft.Text(v, size=13, selectable=True, expand=True)],
                vertical_alignment=ft.CrossAxisAlignment.START)
         for k, v in datos],
        spacing=6,
    )


def fichas_texto(textos, limite=300, fondo="#EAF0F8", color="#1F3B6B"):
    """Lista de cadenas como 'fichas' (se muestra λ para la cadena vacía)."""
    mostrados = list(textos)[:limite]
    fichas = [
        ft.Container(
            content=ft.Text(t if t != "" else "λ", size=12, font_family="Consolas", color=color),
            bgcolor=fondo,
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
            border_radius=3,
        )
        for t in mostrados
    ]
    if len(textos) > limite:
        fichas.append(ft.Text(f"… y {len(textos) - limite} más", size=12, color=C["suave"]))
    return ft.Row(fichas, wrap=True, spacing=6, run_spacing=6)


def punto_color(color, texto):
    return ft.Row(
        [ft.Container(width=16, height=16, bgcolor=color, border_radius=8,
                      border=ft.border.all(1, "#555555")),
         ft.Text(texto, size=13)],
        spacing=8,
    )


# =============================================================================
# DIBUJO EN CANVAS DE FLET
# =============================================================================
def _elementos(puntos):
    elementos = [cv.Path.MoveTo(puntos[0][0], puntos[0][1])]
    for x, y in puntos[1:]:
        elementos.append(cv.Path.LineTo(x, y))
    return elementos


def _forma_texto(p):
    estilo = ft.TextStyle(size=p["tam"], color=p["color"], weight=NEGRITA if p.get("neg") else NORMAL)
    try:
        return cv.Text(p["x"], p["y"], p["texto"], style=estilo,
                       alignment=ft.alignment.center, text_align=ft.TextAlign.CENTER)
    except TypeError:
        return cv.Text(p["x"], p["y"], p["texto"], style=estilo)


def a_formas(prims):
    """Convierte las primitivas de visualizador.py en formas del canvas de Flet."""
    formas = []
    relleno = ft.PaintingStyle.FILL
    trazo = ft.PaintingStyle.STROKE
    for p in prims:
        t = p["t"]
        if t == "circulo":
            if p["relleno"]:
                formas.append(cv.Circle(p["x"], p["y"], p["r"],
                                        paint=ft.Paint(color=p["relleno"], style=relleno)))
            if p["borde"]:
                formas.append(cv.Circle(p["x"], p["y"], p["r"],
                                        paint=ft.Paint(color=p["borde"], stroke_width=p["ancho"], style=trazo)))
        elif t == "linea":
            formas.append(cv.Path(_elementos(p["pts"]),
                                  paint=ft.Paint(color=p["color"], stroke_width=p["ancho"], style=trazo)))
        elif t == "poligono":
            elementos = _elementos(p["pts"] + [p["pts"][0]])
            if p["relleno"]:
                formas.append(cv.Path(elementos, paint=ft.Paint(color=p["relleno"], style=relleno)))
            if p["borde"] and p["ancho"]:
                formas.append(cv.Path(elementos,
                                      paint=ft.Paint(color=p["borde"], stroke_width=p["ancho"], style=trazo)))
        elif t == "texto":
            formas.append(_forma_texto(p))
    return formas


# =============================================================================
# SESIÓN Y DOCUMENTOS
# =============================================================================
class Sesion:
    """Todo el estado de la aplicación en un solo lugar."""

    def __init__(self):
        self.automata = Automata()
        self.zoom = 1.0
        self.docs = []
        self.activo = "automata"
        self.errores = {}

        # conversiones
        self.sin_lambda = None
        self.rep_lambda = None
        self.afd = None
        self.minimo = None
        self.min_base = None
        self.rep_min = None

        # simulación
        self.sim_cadena = ""
        self.sim = None
        self.sim_idx = 0
        self.cl_estado = None
        self.cl_res = None
        self.dir_cadena = ""
        self.dir_res = None

        # lote
        self.lote = None

        # práctica 4
        self.regex_txt = "(a|b)*abb"
        self.regex_res = None
        self.thompson = None
        self.thompson_pasos = ""
        self.er = None

        # operaciones
        self.ops_cadena = ""
        self.ops_res = None
        self.ops_alfabeto = "a, b"
        self.ops_n = "3"
        self.ops_cerr = None
        self.ops_msg = None


class Doc:
    def __init__(self, clave, titulo, icono, construir, cerrable=True):
        self.clave = clave
        self.titulo = titulo
        self.icono = icono
        self.construir = construir
        self.cerrable = cerrable


# =============================================================================
# APLICACIÓN
# =============================================================================
def main(page: ft.Page):
    page.title = "Simulador de Autómatas Finitos — estilo JFLAP"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=C["acento"])
    page.bgcolor = C["fondo"]
    page.padding = 0
    page.spacing = 0

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    st = Sesion()
    cache_diseno = {}

    # -------------------------------------------------------------------------
    # CONTROLES FIJOS: pestañas, cuerpo, barra de estado
    # -------------------------------------------------------------------------
    tira = ft.Row([], spacing=2, scroll=ft.ScrollMode.AUTO)
    cuerpo = ft.Container(expand=True, padding=12, bgcolor=C["fondo"])
    txt_estado = ft.Text("Listo.", size=12, color=C["suave"], expand=True)
    icono_estado = ft.Icon(ft.icons.INFO_OUTLINE, size=14, color=C["suave"])
    txt_info = ft.Text("", size=12, color=C["suave"])

    def estado(texto, nivel="info"):
        color = {"info": C["suave"], "ok": "#2E7D32", "aviso": "#8A6D00", "error": "#C62828"}[nivel]
        icono = {"info": ft.icons.INFO_OUTLINE, "ok": ft.icons.CHECK_CIRCLE,
                 "aviso": ft.icons.WARNING_AMBER, "error": ft.icons.ERROR_OUTLINE}[nivel]
        txt_estado.value = texto
        txt_estado.color = color
        icono_estado.name = icono
        icono_estado.color = color

    def info_derecha():
        a = st.automata
        if a.estados:
            txt_info.value = (f"{viz.tipo_automata(a)}  ·  {len(a.estados)} estados  ·  "
                              f"Σ = {fmt(a.alfabeto)}  ·  Zoom {int(round(st.zoom * 100))}%")
        else:
            txt_info.value = f"Sin autómata  ·  Zoom {int(round(st.zoom * 100))}%"

    # -------------------------------------------------------------------------
    # GESTIÓN DE DOCUMENTOS (pestañas)
    # -------------------------------------------------------------------------
    def ficha(d):
        sel = d.clave == st.activo
        partes = [
            ft.Icon(d.icono, size=15, color=C["acento"] if sel else C["suave"]),
            ft.Text(d.titulo, size=13, weight=NEGRITA if sel else NORMAL, color=C["texto"]),
        ]
        if d.cerrable:
            partes.append(ft.Container(
                content=ft.Icon(ft.icons.CLOSE, size=14, color=C["suave"]),
                padding=2, border_radius=8, tooltip="Cerrar pestaña",
                on_click=lambda e, c=d.clave: cerrar_doc(c),
            ))
        return ft.Container(
            content=ft.Row(partes, spacing=6, tight=True),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            bgcolor=C["tab_sel"] if sel else "#D9D9D9",
            border=ft.border.only(
                top=ft.BorderSide(3, C["acento"] if sel else C["transparente"]),
                left=ft.BorderSide(1, C["borde"]),
                right=ft.BorderSide(1, C["borde"]),
            ),
            on_click=lambda e, c=d.clave: ir_doc(c),
        )

    def refrescar():
        tira.controls = [ficha(d) for d in st.docs]
        doc = next((d for d in st.docs if d.clave == st.activo), st.docs[0])
        try:
            contenido = doc.construir()
        except Exception:
            traceback.print_exc()
            contenido = ft.Column(
                [aviso("error", "No se pudo dibujar esta vista.\n\n" + traceback.format_exc(), mono=True)],
                scroll=ft.ScrollMode.AUTO, expand=True,
            )
        cuerpo.content = contenido
        info_derecha()
        page.update()

    def abrir_doc(clave, titulo, icono, construir, cerrable=True):
        for d in st.docs:
            if d.clave == clave:
                d.titulo, d.icono, d.construir = titulo, icono, construir
                break
        else:
            st.docs.append(Doc(clave, titulo, icono, construir, cerrable))
        st.activo = clave
        refrescar()

    def ir_doc(clave):
        if any(d.clave == clave for d in st.docs):
            st.activo = clave
            refrescar()

    def cerrar_doc(clave, refrescar_ahora=True):
        st.docs = [d for d in st.docs if d.clave != clave or not d.cerrable]
        if st.activo == clave:
            st.activo = "automata"
        if refrescar_ahora:
            refrescar()

    def cerrar_actual():
        if st.activo != "automata":
            cerrar_doc(st.activo)

    # -------------------------------------------------------------------------
    # DIBUJO: panel con el grafo del autómata
    # -------------------------------------------------------------------------
    def diseno_de(auto):
        clave = id(auto)
        guardado = cache_diseno.get(clave)
        if guardado and guardado[0] is auto:
            return guardado[1]
        if len(cache_diseno) > 16:
            cache_diseno.clear()
        grafo = viz.disenar(auto)
        cache_diseno[clave] = (auto, grafo)
        return grafo

    def lienzo(auto, resaltados=None, altura=340):
        if cv is None:
            return ft.Container(height=altura, padding=20, content=ft.Text(
                "Esta versión de Flet no incluye 'canvas'; actualiza con: pip install -U flet",
                color=C["suave"]))
        if auto is None or not auto.estados:
            return ft.Container(height=altura, alignment=ft.alignment.center, bgcolor=C["blanco"],
                                content=ft.Text("Sin autómata", color=C["suave"]))
        prims, ancho, alto = viz.primitivas(diseno_de(auto), st.zoom, resaltados)
        lienzo_cv = cv.Canvas(a_formas(prims), width=ancho, height=alto)
        return ft.Container(
            height=altura,
            bgcolor=C["blanco"],
            content=ft.Column([ft.Row([lienzo_cv], scroll=ft.ScrollMode.AUTO)], scroll=ft.ScrollMode.AUTO),
        )

    def panel_grafo(titulo, auto, resaltados=None, altura=340, expand=None, extra=None):
        cabecera = [ft.Text(titulo, size=13, weight=NEGRITA, color=C["texto"])]
        if auto is not None and auto.estados:
            cabecera.append(chip_tipo(auto))
        cabecera.append(ft.Container(expand=True))
        if auto is not None and auto.estados:
            cabecera.append(ft.Text(f"{len(auto.estados)} estados", size=12, color=C["suave"]))
        cabecera.extend(extra or [])
        return ft.Container(
            expand=expand,
            bgcolor=C["blanco"],
            border=ft.border.all(1, C["borde"]),
            border_radius=3,
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(cabecera, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                        bgcolor=C["cabecera"], padding=ft.padding.symmetric(horizontal=10, vertical=6),
                        border=ft.border.only(bottom=ft.BorderSide(1, C["borde_suave"])),
                    ),
                    lienzo(auto, resaltados, altura),
                ],
                spacing=0,
            ),
        )

    def pedir_automata(que):
        return ft.Container(
            alignment=ft.alignment.center, expand=True,
            content=ft.Column(
                [ft.Icon(ft.icons.ACCOUNT_TREE, size=56, color="#B0B8C4"),
                 ft.Text(f"Para usar «{que}» primero abre un autómata.", size=15),
                 boton("Abrir autómata…", ft.icons.FOLDER_OPEN, lambda e: abrir_archivo(), primario=True)],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=14),
        )

    def requiere_automata(que):
        if st.automata.estados:
            return True
        estado(f"Abre primero un autómata para usar «{que}».", "aviso")
        ir_doc("automata")
        return False

    # =========================================================================
    # DOCUMENTO PRINCIPAL: el autómata
    # =========================================================================
    def doc_automata():
        a = st.automata
        if not a.estados:
            return ft.Container(
                alignment=ft.alignment.center, expand=True,
                content=ft.Column(
                    [ft.Icon(ft.icons.ACCOUNT_TREE, size=72, color="#B0B8C4"),
                     ft.Text("No hay ningún autómata abierto", size=20, weight=NEGRITA),
                     ft.Text("Abre un archivo de JFLAP (.jff), .json o .xml, o genera uno desde una expresión regular.",
                             size=13, color=C["suave"]),
                     ft.Row([boton("Abrir autómata…", ft.icons.FOLDER_OPEN, lambda e: abrir_archivo(), primario=True),
                             boton("Expresión regular → AFN-λ", ft.icons.CODE, lambda e: abrir_regex())],
                            alignment=ft.MainAxisAlignment.CENTER, spacing=10)],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=14),
            )
        izquierda = panel_grafo("Diagrama de estados", a, altura=500)
        derecha = ft.Column(
            [tarjeta("Definición formal", [definicion(a)], ft.icons.INFO_OUTLINE),
             tarjeta("Función de transición δ", [tabla_delta(a)], ft.icons.TABLE_CHART)],
            spacing=12, width=360,
        )
        return ft.Column(
            [ft.Row([ft.Container(izquierda, expand=True), derecha],
                    vertical_alignment=ft.CrossAxisAlignment.START, spacing=12)],
            scroll=ft.ScrollMode.AUTO, expand=True,
        )

    # =========================================================================
    # ENTRADA · PROBAR CADENA (paso a paso, con estados resaltados)
    # =========================================================================
    def simular():
        if not requiere_automata("Probar cadena"):
            return
        cadena = (st.sim_cadena or "").strip()
        try:
            ok, traza = st.automata.simular_paso_a_paso(cadena)
            st.sim = {"cadena": cadena, "ok": ok, "traza": traza}
            st.sim_idx = 0
            st.errores.pop("simular", None)
            estado(f"Cadena «{cadena or 'λ'}» {'ACEPTADA' if ok else 'RECHAZADA'}.", "ok" if ok else "error")
        except Exception as err:
            st.sim = None
            st.errores["simular"] = f"Error durante la simulación: {err}"
            estado(st.errores["simular"], "error")
        abrir_doc("simular", "Probar cadena", ft.icons.PLAY_ARROW, doc_simulacion)

    def mover_paso(delta=None, ir_a=None):
        if not st.sim:
            return
        ultimo = len(st.sim["traza"]) - 1
        nuevo = ir_a if ir_a is not None else st.sim_idx + delta
        st.sim_idx = max(0, min(ultimo, nuevo))
        refrescar()

    def doc_simulacion():
        a = st.automata
        if not a.estados:
            return pedir_automata("Probar cadena")

        campo = ft.TextField(
            label="Cadena de entrada", value=st.sim_cadena, width=340, dense=True,
            hint_text="Ej.: 0101   (vacío = cadena vacía λ)",
            on_change=lambda e: setattr(st, "sim_cadena", e.control.value),
            on_submit=lambda e: simular(),
        )
        controles = [campo, boton("Simular", ft.icons.PLAY_ARROW, lambda e: simular(), primario=True)]

        bloques = []
        resaltados = {}
        sim = st.sim

        if st.errores.get("simular"):
            bloques.append(aviso("error", st.errores["simular"]))

        if sim:
            traza = sim["traza"]
            idx = min(st.sim_idx, len(traza) - 1)
            ultimo = idx == len(traza) - 1
            finales = viz.obtener_finales(a)
            for s in traza[idx].get("estados_actuales", set()):
                if ultimo and sim["ok"] and s in finales:
                    resaltados[s] = VERDE
                elif ultimo and not sim["ok"]:
                    resaltados[s] = ROJO
                else:
                    resaltados[s] = NARANJA

            controles += [
                ft.Container(width=1, height=28, bgcolor=C["borde"]),
                ft.IconButton(ft.icons.FIRST_PAGE, tooltip="Primer paso", disabled=idx == 0,
                              on_click=lambda e: mover_paso(ir_a=0)),
                ft.IconButton(ft.icons.SKIP_PREVIOUS, tooltip="Paso anterior", disabled=idx == 0,
                              on_click=lambda e: mover_paso(delta=-1)),
                ft.Text(f"Paso {idx} de {len(traza) - 1}", size=13, weight=NEGRITA),
                ft.IconButton(ft.icons.SKIP_NEXT, tooltip="Paso siguiente", disabled=ultimo,
                              on_click=lambda e: mover_paso(delta=1)),
                ft.IconButton(ft.icons.LAST_PAGE, tooltip="Último paso", disabled=ultimo,
                              on_click=lambda e: mover_paso(ir_a=len(traza) - 1)),
            ]

            cadena = sim["cadena"]
            if cadena:
                cinta = []
                for i, ch in enumerate(cadena):
                    consumido = i < idx
                    actual = i == idx
                    cinta.append(ft.Container(
                        content=ft.Text(ch, size=15, font_family="Consolas", weight=NEGRITA),
                        width=34, height=34, alignment=ft.alignment.center,
                        bgcolor=C["tab_sel"] if consumido else C["blanco"],
                        border=ft.border.all(2 if actual else 1, C["acento"] if actual else C["borde"]),
                        border_radius=3,
                    ))
                cinta_ctl = ft.Row(cinta, wrap=True, spacing=4, run_spacing=4)
            else:
                cinta_ctl = ft.Text("λ  (cadena vacía)", size=14)

            if sim["ok"]:
                veredicto = aviso("ok", f"Cadena aceptada: «{cadena or 'λ'}»")
            else:
                veredicto = aviso("error", f"Cadena rechazada: «{cadena or 'λ'}»")

            filas = []
            for i, p in enumerate(traza):
                negrita = NEGRITA if i == idx else NORMAL
                color = C["acento"] if i == idx else C["texto"]
                if p.get("error"):
                    detalle = ft.Text(p["error"], size=12, color="#C62828", weight=negrita)
                else:
                    detalle = ft.Text(fmt(p.get("estados_actuales", set())), size=12, color=color, weight=negrita)
                simbolo = p.get("simbolo")
                filas.append([
                    ft.Text(str(p.get("paso", i)), size=12, color=color, weight=negrita),
                    ft.Text("—" if simbolo is None else str(simbolo), size=12, color=color, weight=negrita),
                    detalle,
                ])

            bloques += [
                veredicto,
                panel_grafo("Diagrama (estados activos resaltados)", a, resaltados, altura=360),
                tarjeta("Traza de ejecución",
                        [ft.Text("Cinta de entrada", size=12, color=C["suave"]), cinta_ctl,
                         tabla(["Paso", "Símbolo leído", "Estados activos (tras λ-clausura)"], filas)],
                        ft.icons.TABLE_CHART),
            ]
        else:
            bloques += [
                aviso("info", "Escribe una cadena y pulsa «Simular». Podrás recorrerla paso a paso y ver "
                              "cómo se iluminan los estados activos en el diagrama."),
                panel_grafo("Diagrama", a, None, altura=360),
            ]

        return ft.Column(
            [tarjeta("Entrada", [ft.Row(controles, spacing=8, wrap=True,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER)],
                     ft.icons.PLAY_ARROW),
             *bloques],
            spacing=12, scroll=ft.ScrollMode.AUTO, expand=True,
        )

    # =========================================================================
    # ENTRADA · CERRADURA λ Y SIMULACIÓN DIRECTA (2.1)
    # =========================================================================
    def calcular_cl():
        if not requiere_automata("Cerradura λ"):
            return
        q = st.cl_estado
        try:
            cierre = CerraduraLambdaSimulador.calcular_cerradura_estado(st.automata, q)
            st.cl_res = (q, set(cierre))
            st.errores.pop("cerradura", None)
            estado(f"CL({q}) = {fmt(cierre)}", "ok")
        except Exception as err:
            st.cl_res = None
            st.errores["cerradura"] = f"Error al calcular la cerradura: {err}"
            estado(st.errores["cerradura"], "error")
        abrir_doc("cerradura", "Cerradura λ", ft.icons.ACCOUNT_TREE, doc_cerradura)

    def simular_directo():
        if not requiere_automata("Simulación directa"):
            return
        cadena = (st.dir_cadena or "").strip()
        try:
            ok, historial = CerraduraLambdaSimulador.simular_directo_paso_a_paso(st.automata, cadena)
            st.dir_res = {"cadena": cadena, "ok": ok, "historial": historial}
            st.errores.pop("directa", None)
            estado(f"Simulación directa: «{cadena or 'λ'}» {'ACEPTADA' if ok else 'RECHAZADA'}.",
                   "ok" if ok else "error")
        except Exception as err:
            st.dir_res = None
            st.errores["directa"] = f"Error durante la simulación directa: {err}"
            estado(st.errores["directa"], "error")
        abrir_doc("cerradura", "Cerradura λ", ft.icons.ACCOUNT_TREE, doc_cerradura)

    def doc_cerradura():
        a = st.automata
        if not a.estados:
            return pedir_automata("Cerradura λ")
        estados = sorted(a.estados, key=viz.clave_estado)
        if st.cl_estado not in a.estados:
            st.cl_estado = estados[0]

        desplegable = ft.Dropdown(
            label="Estado", width=160, value=st.cl_estado,
            options=[ft.dropdown.Option(e) for e in estados],
            on_change=lambda e: setattr(st, "cl_estado", e.control.value),
        )
        bloque_cl = [ft.Row([desplegable, boton("Calcular CL(q)", ft.icons.CALCULATE,
                                                lambda e: calcular_cl(), primario=True)], spacing=10)]
        resaltados = {}
        if st.errores.get("cerradura"):
            bloque_cl.append(aviso("error", st.errores["cerradura"]))
        if st.cl_res and st.cl_res[0] in a.estados:
            q, cierre = st.cl_res
            resaltados = {s: AZUL for s in cierre}
            bloque_cl.append(aviso("ok", f"CL({q}) = {fmt(cierre)}"))

        filas = []
        for q in estados:
            try:
                filas.append([f"CL({q})", fmt(CerraduraLambdaSimulador.calcular_cerradura_estado(a, q))])
            except Exception:
                filas.append([f"CL({q})", "—"])

        campo = ft.TextField(
            label="Cadena a simular (sin convertir el AFN-λ)", value=st.dir_cadena, width=380, dense=True,
            on_change=lambda e: setattr(st, "dir_cadena", e.control.value),
            on_submit=lambda e: simular_directo(),
        )
        bloque_dir = [ft.Row([campo, boton("Simular AFN-λ", ft.icons.PLAY_ARROW,
                                           lambda e: simular_directo(), primario=True)], spacing=10, wrap=True)]
        if st.errores.get("directa"):
            bloque_dir.append(aviso("error", st.errores["directa"]))
        if st.dir_res:
            r = st.dir_res
            bloque_dir.append(aviso("ok" if r["ok"] else "error",
                                    f"Cadena {'aceptada' if r['ok'] else 'rechazada'}: «{r['cadena'] or 'λ'}»"))
            bloque_dir.append(tabla(
                ["Paso", "Símbolo", "Activos (antes de CL)", "Activos (después de CL)", "Detalle"],
                [[str(p.get("paso", "")), str(p.get("simbolo", "")), str(p.get("activos_antes", "")),
                  str(p.get("activos_despues", "")), str(p.get("descripcion", ""))] for p in r["historial"]]))

        return ft.Column(
            [panel_grafo("Diagrama (cerradura resaltada en azul)", a, resaltados, altura=340),
             ft.Row([ft.Container(tarjeta("2.1  Cerradura λ de un estado", bloque_cl, ft.icons.ACCOUNT_TREE), expand=1),
                     ft.Container(tarjeta("Cerraduras de todos los estados", [tabla(["Estado", "Cerradura"], filas)],
                                          ft.icons.TABLE_CHART), expand=1)],
                    vertical_alignment=ft.CrossAxisAlignment.START, spacing=12),
             tarjeta("Simulación directa de AFN-λ", bloque_dir, ft.icons.PLAY_ARROW)],
            spacing=12, scroll=ft.ScrollMode.AUTO, expand=True,
        )

    # =========================================================================
    # CONVERTIR · vista lado a lado "original → resultado"
    # =========================================================================
    def vista_conversion(titulo, origen, resultado, tit_origen, tit_resultado, extras, error=None):
        franja = ft.Row(
            [ft.Text(titulo, size=15, weight=NEGRITA),
             chip_tipo(origen), ft.Icon(ft.icons.ARROW_FORWARD, size=16, color=C["suave"]),
             chip_tipo(resultado) if resultado is not None else chip("—", "#EEEEEE", "#555555"),
             ft.Container(expand=True),
             ft.Text(f"{len(origen.estados)} estados  →  "
                     f"{len(resultado.estados) if resultado is not None else '—'} estados",
                     size=12, color=C["suave"])],
            spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        bloques = [franja]
        if error:
            bloques.append(aviso("error", error))
        if resultado is not None:
            bloques.append(ft.Row(
                [panel_grafo(tit_origen, origen, altura=330, expand=1),
                 ft.Icon(ft.icons.ARROW_FORWARD, size=28, color=C["acento"]),
                 panel_grafo(tit_resultado, resultado, altura=330, expand=1)],
                vertical_alignment=ft.CrossAxisAlignment.START, spacing=8))
            bloques.extend(extras)
        return ft.Column(bloques, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # ---- 2.2  AFN-λ → AFN -----------------------------------------------------
    def hacer_lambda():
        if not requiere_automata("AFN-λ → AFN"):
            return
        try:
            st.sin_lambda, st.rep_lambda = EliminadorLambda.eliminar_transiciones_lambda(st.automata)
            st.errores.pop("lambda", None)
            estado(f"AFN-λ → AFN completado ({len(st.sin_lambda.estados)} estados).", "ok")
        except Exception as err:
            st.sin_lambda, st.rep_lambda = None, None
            st.errores["lambda"] = f"Error durante la conversión: {err}"
            estado(st.errores["lambda"], "error")
        abrir_doc("lambda", "AFN-λ → AFN", ft.icons.CLEANING_SERVICES, doc_lambda)

    def texto_proc_lambda(rep):
        orden = lambda kv: viz.clave_estado(kv[0])
        lineas = ["PASO 1 · Cerraduras λ  CL(q)"]
        for q, cl in sorted(rep["cerraduras_individuales"].items(), key=orden):
            lineas.append(f"  CL({q}) = {fmt(cl)}")
        lineas.append("")
        lineas.append("PASO 2 · Estados finales  F' = { q | CL(q) ∩ F ≠ ∅ }")
        lineas.append(f"  F = {fmt(rep['finales_originales'])}")
        for it in rep["estados_finales_calculo"]:
            inter = fmt(it["interseccion_F"]) if it["interseccion_F"] else "∅"
            veredicto = "✔ está en F'" if it["es_final"] else "✘ no está en F'"
            lineas.append(f"  CL({it['estado']}) = {fmt(it['cl_q'])}  ∩ F = {inter}   →  {veredicto}")
        lineas.append("")
        lineas.append("PASO 3 · Transiciones  δ'(q, a) = CL( δ( CL(q), a ) )")
        return "\n".join(lineas)

    def doc_lambda():
        if not st.automata.estados:
            return pedir_automata("AFN-λ → AFN")
        if st.sin_lambda is None:
            return vista_conversion("Quitar transiciones λ", st.automata, None, "", "", [],
                                    error=st.errores.get("lambda", "Aún no se ha convertido."))
        nuevo, rep = st.sin_lambda, st.rep_lambda
        desglose = tabla(
            ["Estado q", "Símbolo a", "1. CL(q)", "2. δ(CL(q), a)", "3. δ'(q, a) = CL(…)"],
            [[it["estado"], it["simbolo"], fmt(it["cl_origen"]), fmt(it["alcanzables_directos"]),
              fmt(it["resultado_cl"])] for it in rep.get("transiciones_desglose", [])])
        extras = [
            tarjeta("Autómata resultante", [definicion(nuevo)], ft.icons.INFO_OUTLINE),
            tarjeta("Tabla de transiciones δ' (sin λ)", [tabla_delta(nuevo)], ft.icons.TABLE_CHART),
            expansion("Procedimiento paso a paso", [mono(texto_proc_lambda(rep))]),
            expansion("Desglose de cada transición  δ'(q, a)", [desglose]),
        ]
        return vista_conversion("Quitar transiciones λ", st.automata, nuevo,
                                "Original (AFN-λ)", "Resultado (AFN sin λ)", extras, st.errores.get("lambda"))

    # ---- 2.3  AFN → AFD -------------------------------------------------------
    def hacer_afd():
        if not requiere_automata("AFN → AFD"):
            return
        try:
            st.afd, _ = ConvertidorSubconjuntos.afn_a_afd(st.automata)
            st.minimo = None
            st.errores.pop("afd", None)
            estado(f"AFN → AFD completado ({len(st.afd.estados)} estados).", "ok")
        except Exception as err:
            st.afd = None
            st.errores["afd"] = f"Error durante la conversión a AFD: {err}"
            estado(st.errores["afd"], "error")
        abrir_doc("afd", "AFN → AFD", ft.icons.MERGE_TYPE, doc_afd)

    def doc_afd():
        if not st.automata.estados:
            return pedir_automata("AFN → AFD")
        if st.afd is None:
            return vista_conversion("Construcción por subconjuntos", st.automata, None, "", "", [],
                                    error=st.errores.get("afd", "Aún no se ha convertido."))
        afd = st.afd
        mapeo = getattr(afd, "mapeo_subconjuntos", {}) or {}
        extras = []
        if mapeo:
            extras.append(tarjeta(
                "Equivalencia de estados (subconjuntos del AFN)",
                [tabla(["Estado del AFD", "Subconjunto del AFN"],
                       [[str(alias), fmt(conj)] for alias, conj in
                        sorted(mapeo.items(), key=lambda kv: viz.clave_estado(kv[0]))])],
                ft.icons.MERGE_TYPE))
        extras += [
            tarjeta("Autómata resultante", [definicion(afd)], ft.icons.INFO_OUTLINE),
            tarjeta("Tabla de transiciones del AFD", [tabla_delta(afd, col0="Estado AFD")], ft.icons.TABLE_CHART),
        ]
        return vista_conversion("Construcción por subconjuntos", st.automata, afd,
                                "Original (AFN)", "Resultado (AFD)", extras, st.errores.get("afd"))

    # ---- 2.4  Minimización ----------------------------------------------------
    def hacer_min():
        if not requiere_automata("Minimizar AFD"):
            return
        base = st.afd if (st.afd is not None and st.afd.estados) else st.automata
        try:
            st.minimo, st.rep_min = MinimizadorAFD.minimizar(base)
            st.min_base = base
            st.errores.pop("min", None)
            estado(f"Minimización completada: {len(base.estados)} → {len(st.minimo.estados)} estados.", "ok")
        except Exception as err:
            st.minimo, st.rep_min, st.min_base = None, None, base
            st.errores["min"] = f"Error durante la minimización: {err}"
            estado(st.errores["min"], "error")
        abrir_doc("min", "Minimizar AFD", ft.icons.COMPRESS, doc_min)

    def texto_proc_min(rep):
        lineas = ["PASO 1 · Partición inicial", "  " + ",   ".join(rep["p1_inicial"]), f"  {rep['p1_nombre']}", ""]
        ultima = rep["p1_nombre"]
        for ronda in rep["rondas"]:
            p_nombre = ronda["particion_nombre"]
            ultima = p_nombre
            lineas.append(f"PASO 2 · Ronda {ronda['ronda_num']}  (con {p_nombre})")
            for t_info in ronda["tablas_clases"]:
                c_name = t_info["clase_analizada"]
                if t_info.get("tiene_un_solo_estado"):
                    lineas.append(f"  {c_name} tiene un solo estado.")
                else:
                    lineas.append(f"  Tabla de {c_name}:")
                    lineas.append(f"    {'Estado':<8}| {'Transición':<14}| Clase en {p_nombre}")
                    for f in t_info["filas"]:
                        t_str = " ".join(f"{k}:{v}" for k, v in f["trans_estados"].items())
                        c_str = " ".join(f"{k}:{v}" for k, v in f["trans_clases"].items())
                        lineas.append(f"    {str(f['estado']):<8}| {t_str:<14}| {c_str}")
                lineas.append(f"  {t_info['mensaje']}")
                lineas.append("")
        lineas.append(f"PASO 4 · Autómata simplificado ({rep['particion_final_nombre']} = {ultima}; no hay más cambios)")
        return "\n".join(lineas)

    def doc_min():
        if not st.automata.estados:
            return pedir_automata("Minimizar AFD")
        base = st.min_base or (st.afd if (st.afd is not None and st.afd.estados) else st.automata)
        if st.minimo is None:
            return vista_conversion("Minimización de AFD", base, None, "", "", [],
                                    error=st.errores.get("min", "Aún no se ha minimizado."))
        mini, rep = st.minimo, st.rep_min
        clases = rep["definicion_clases"]
        extras = [
            tarjeta("Clases de equivalencia",
                    [tabla(["Clase", "Estados que agrupa"],
                           [[str(k), fmt(v)] for k, v in sorted(clases.items(), key=lambda kv: viz.clave_estado(kv[0]))])],
                    ft.icons.COMPRESS),
            tarjeta("Autómata mínimo", [definicion(mini)], ft.icons.INFO_OUTLINE),
            tarjeta("Tabla de transiciones del AFD mínimo",
                    [tabla_delta(mini, col0="Clase", etiqueta=lambda est: f" = {fmt(clases[est])}")],
                    ft.icons.TABLE_CHART),
            expansion("Procedimiento paso a paso (algoritmo de particiones)", [mono(texto_proc_min(rep))]),
        ]
        origen = "Original (AFD)" if base is st.afd else "Original"
        return vista_conversion("Minimización de AFD", base, mini, origen, "Resultado (AFD mínimo)",
                                extras, st.errores.get("min"))

    # =========================================================================
    # ENTRADA · VALIDACIÓN EN LOTE (2.5)
    # =========================================================================
    def procesar_lote(ruta, nombre):
        if not st.automata.estados:
            estado("Abre primero un autómata antes de validar un lote de cadenas.", "aviso")
            ir_doc("automata")
            return
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
        resultados = ValidadorLote.validar_cadenas_desde_texto(st.automata, contenido)
        st.lote = {"nombre": nombre, "res": resultados, "msg": None}
        aceptadas = sum(1 for r in resultados if r["es_aceptada"])
        estado(f"Lote «{nombre}»: {len(resultados)} cadenas ({aceptadas} aceptadas).", "ok")
        abrir_doc("lote", "Validar lote", ft.icons.CHECKLIST, doc_lote)

    def informe_lote():
        if not st.lote:
            return
        try:
            ruta = os.path.join(UPLOAD_DIR, "informe_validacion_cadenas.txt")
            contenido = ValidadorLote.generar_reporte_texto(st.lote["nombre"], st.lote["res"])
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)
            st.lote["msg"] = ("ok", f"Informe generado en: {ruta}")
            estado("Informe del lote generado.", "ok")
        except Exception as err:
            st.lote["msg"] = ("error", f"Error al escribir el informe: {err}")
            estado(st.lote["msg"][1], "error")
        refrescar()

    def doc_lote():
        a = st.automata
        acciones = [boton("Cargar archivo .txt…", ft.icons.UPLOAD_FILE, lambda e: abrir_lote_txt(), primario=True)]
        if st.lote:
            acciones.append(boton("Generar informe (.txt)", ft.icons.SUMMARIZE, lambda e: informe_lote()))
        bloques = []
        if not a.estados:
            bloques.append(aviso("aviso", "Primero abre un autómata; después carga el archivo .txt con una cadena por línea."))
        else:
            bloques.append(aviso("info", "Carga un archivo .txt con una cadena por línea; se evaluará cada una contra el autómata actual."))
        if st.lote:
            res = st.lote["res"]
            ac = sum(1 for r in res if r["es_aceptada"])
            resumen = ft.Row(
                [chip(f"{len(res)} cadenas", "#EEEEEE", "#333333", 12),
                 chip(f"{ac} aceptadas", "#E8F5E9", "#2E7D32", 12),
                 chip(f"{len(res) - ac} rechazadas", "#FDECEA", "#C62828", 12),
                 ft.Text(f"Archivo: {st.lote['nombre']}", size=12, color=C["suave"])],
                spacing=8, wrap=True)
            filas = []
            for r in res:
                fondo, color = ("#E8F5E9", "#2E7D32") if r["es_aceptada"] else ("#FDECEA", "#C62828")
                filas.append([str(r["linea"]), r["cadena"] if r["cadena"] != "" else "λ",
                              chip(r["resultado"], fondo, color), str(r["estados_finales_alcanzados"])])
            msg = st.lote.get("msg")
            if msg:
                bloques.append(aviso(msg[0], msg[1]))
            bloques.append(tarjeta("Resultados", [resumen, tabla(["Línea", "Cadena", "Resultado", "Estados activos finales"], filas)],
                                   ft.icons.CHECKLIST))
        return ft.Column([tarjeta("Validación de varias cadenas", [ft.Row(acciones, spacing=10), *bloques],
                                  ft.icons.CHECKLIST)],
                         spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # =========================================================================
    # PRÁCTICA 4 · EXPRESIÓN REGULAR → AFN-λ (Thompson)
    # =========================================================================
    def hacer_thompson(patron=None):
        if patron is not None:
            st.regex_txt = patron
        patron = (st.regex_txt or "").strip()
        if not patron:
            st.regex_res = {"ok": False, "texto": "Escribe una expresión regular."}
            abrir_doc("regex", "ER → AFN-λ", ft.icons.CODE, doc_regex)
            return
        try:
            ast, _ = RegexParser.parse(patron)
            afn, historial = ConstructorThompson().construir(ast)
            st.thompson = afn
            lineas = ["CONSTRUCCIÓN DE THOMPSON PASO A PASO"]
            for i, paso in enumerate(historial, 1):
                lineas.append(f"Paso {i}: {paso['operacion']}")
                lineas.append(f"    sub-inicial: {paso['estado_inicial']}   sub-final: {paso['estado_final']}")
            st.thompson_pasos = "\n".join(lineas)
            st.regex_res = {"ok": True, "patron": patron}
            estado(f"AFN-λ construido para «{patron}» ({len(afn.estados)} estados).", "ok")
        except RegexSyntaxError as err:
            st.thompson = None
            marcador = " " * err.posicion + "^"
            st.regex_res = {"ok": False, "mono": True,
                            "texto": f"Error de sintaxis en la posición {err.posicion}:\n  {patron}\n  {marcador}\n{err.mensaje}"}
            estado("La expresión regular tiene un error de sintaxis.", "error")
        except Exception as err:
            st.thompson = None
            st.regex_res = {"ok": False, "texto": f"Error inesperado: {err}"}
            estado(f"Error inesperado: {err}", "error")
        abrir_doc("regex", "ER → AFN-λ", ft.icons.CODE, doc_regex)

    def usar_thompson():
        if st.thompson is None:
            return
        st.automata = st.thompson
        limpiar_derivados()
        estado("AFN-λ de Thompson cargado como autómata actual.", "ok")
        st.activo = "automata"
        refrescar()

    def doc_regex():
        campo = ft.TextField(
            label="Expresión regular", value=st.regex_txt, width=440, dense=True,
            hint_text="Operadores: |  +  *  ( )  .",
            on_change=lambda e: setattr(st, "regex_txt", e.control.value),
            on_submit=lambda e: hacer_thompson(),
        )
        ejemplos = ft.Row(
            [ft.Text("Ejemplos:", size=12, color=C["suave"])] +
            [ft.TextButton(ej, on_click=lambda e, x=ej: hacer_thompson(x)) for ej in ("(a|b)*abb", "a(b|c)*", "(0|1)*1", "ab*|c")],
            spacing=2, wrap=True)
        bloques = [tarjeta("Expresión regular",
                           [ft.Row([campo, boton("Construir AFN-λ", ft.icons.AUTO_AWESOME,
                                                 lambda e: hacer_thompson(), primario=True)], spacing=10, wrap=True),
                            ejemplos],
                           ft.icons.CODE)]
        r = st.regex_res
        if r and not r["ok"]:
            bloques.append(aviso("error", r["texto"], mono=r.get("mono", False)))
        if r and r["ok"] and st.thompson is not None:
            afn = st.thompson
            bloques.append(aviso("ok", f"Expresión válida: «{r['patron']}»"))
            bloques.append(panel_grafo(
                "AFN-λ resultante (Thompson)", afn, altura=380,
                extra=[boton("Usar como autómata actual", ft.icons.PLAY_FOR_WORK, lambda e: usar_thompson(), primario=True)]))
            bloques.append(tarjeta("Autómata resultante", [definicion(afn)], ft.icons.INFO_OUTLINE))
            bloques.append(expansion("Construcción paso a paso", [mono(st.thompson_pasos)]))
            bloques.append(expansion("Tabla de transiciones", [tabla_delta(afn, extra=("λ",))]))
        elif not r:
            bloques.append(aviso("info", "Escribe una expresión regular (por ejemplo (a|b)*abb) y pulsa «Construir AFN-λ»."))
        return ft.Column(bloques, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # =========================================================================
    # PRÁCTICA 4 · AUTÓMATA → EXPRESIÓN REGULAR
    # =========================================================================
    def hacer_er(auto=None):
        auto = auto if auto is not None else st.automata
        if not auto.estados:
            requiere_automata("Autómata → ER")
            return
        es_puro, mensaje = ConversorAutomataARegex.verificar_es_afd_puro(auto)
        er = {"auto": auto, "puro": es_puro, "msg": mensaje}
        if es_puro:
            try:
                regex, historial = ConversorAutomataARegex.convertir_a_regex(auto)
                lineas = ["HISTORIAL DE ELIMINACIÓN DE ESTADOS"]
                for h in historial:
                    lineas.append(f"\nPaso {h['paso']}: se elimina el estado '{h['estado_eliminado']}'")
                    lineas.append("  Matriz de expresiones antes de eliminarlo:")
                    for u, destinos in h["matriz_antes"].items():
                        for v, expr in destinos.items():
                            if expr:
                                lineas.append(f"    R[{u}][{v}] = {expr}")
                er.update(regex=regex, historial="\n".join(lineas))
                estado(f"Expresión regular obtenida: {regex}", "ok")
            except Exception as err:
                er["error"] = f"Error durante la conversión: {err}"
                estado(er["error"], "error")
        else:
            estado("El autómata no es un AFD determinista puro.", "error")
        st.er = er
        abrir_doc("aut2er", "Autómata → ER", ft.icons.TRANSFORM, doc_aut2er)

    def copiar(texto):
        try:
            page.set_clipboard(texto)
            estado("Copiado al portapapeles.", "ok")
        except Exception:
            estado("No se pudo copiar automáticamente; selecciona el texto y usa Ctrl+C.", "aviso")
        page.update()

    def doc_aut2er():
        if not st.automata.estados:
            return pedir_automata("Autómata → ER")
        er = st.er
        if er is None:
            return ft.Column([tarjeta("Autómata → expresión regular",
                                      [aviso("info", "Verifica que el autómata sea un AFD y obtén su expresión regular por eliminación de estados."),
                                       boton("Verificar y obtener ER", ft.icons.AUTO_FIX_HIGH, lambda e: hacer_er(), primario=True)],
                                      ft.icons.TRANSFORM)], spacing=12)
        auto = er["auto"]
        derecha = []
        if not er["puro"]:
            derecha.append(aviso("error", f"El autómata no es un AFD determinista puro.\n{er['msg']}"))
            acciones = [boton("Reintentar", ft.icons.REFRESH, lambda e: hacer_er(st.automata))]
            if st.afd is not None and st.afd.estados and auto is not st.afd:
                acciones.insert(0, boton("Usar el AFD convertido", ft.icons.MERGE_TYPE,
                                         lambda e: hacer_er(st.afd), primario=True))
            else:
                acciones.insert(0, boton("Convertir a AFD primero", ft.icons.MERGE_TYPE,
                                         lambda e: hacer_afd(), primario=True))
            derecha.append(ft.Row(acciones, spacing=10, wrap=True))
            derecha.append(ft.Text("Una ER solo se obtiene de un AFD: conviértelo en «Convertir → AFN → AFD» y vuelve aquí.",
                                   size=12, color=C["suave"]))
        elif er.get("error"):
            derecha.append(aviso("error", er["error"]))
        else:
            derecha.append(aviso("ok", er["msg"]))
            derecha.append(ft.Container(
                bgcolor="#F4F8FF", border=ft.border.all(1, C["acento"]), border_radius=3, padding=14,
                content=ft.Row(
                    [ft.Text("R =", size=18, weight=NEGRITA, color=C["acento"]),
                     ft.Text(er["regex"], size=18, font_family="Consolas", selectable=True, expand=True),
                     ft.IconButton(ft.icons.CONTENT_COPY, tooltip="Copiar expresión",
                                   on_click=lambda e, t=er["regex"]: copiar(t))],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)))
        bloques = [
            ft.Row([panel_grafo("Autómata de entrada", auto, altura=330, expand=1),
                    ft.Container(tarjeta("Expresión regular equivalente", derecha, ft.icons.TRANSFORM), expand=1)],
                   vertical_alignment=ft.CrossAxisAlignment.START, spacing=12),
        ]
        if er.get("historial"):
            bloques.append(expansion("Desglose de la eliminación de estados", [mono(er["historial"], altura=360)]))
        return ft.Column(bloques, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # =========================================================================
    # OPERACIONES AVANZADAS
    # =========================================================================
    def ops_calcular():
        cadena = (st.ops_cadena or "").strip()
        if not cadena:
            st.ops_msg = ("aviso", "Ingresa una cadena válida.")
            st.ops_res = None
        else:
            try:
                res = OperacionesAvanzadas.calcular_prefijos_sufijos_subcadenas(cadena)
                res["cadena"] = cadena
                st.ops_res = res
                st.ops_msg = ("ok", f"Análisis completado para «{cadena}» (n = {res['longitud_n']}).")
                estado(st.ops_msg[1], "ok")
            except Exception as err:
                st.ops_res = None
                st.ops_msg = ("error", f"Error: {err}")
                estado(st.ops_msg[1], "error")
        abrir_doc("ops", "Operaciones", ft.icons.CALCULATE, doc_ops)

    def ops_guardar():
        if not st.ops_res:
            st.ops_msg = ("aviso", "No hay resultados de subcadenas para exportar.")
        else:
            try:
                ruta = os.path.join(UPLOAD_DIR, "informe_subcadenas_prefijos.txt")
                contenido = OperacionesAvanzadas.generar_reporte_operaciones(st.ops_res)
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(contenido)
                st.ops_msg = ("ok", f"Informe guardado en: {ruta}")
            except Exception as err:
                st.ops_msg = ("error", f"Error al guardar archivo: {err}")
        refrescar()

    def ops_cerradura(positiva):
        try:
            n = int(st.ops_n) if (st.ops_n or "").strip() else 3
            st.ops_cerr = ("ok", OperacionesAvanzadas.generar_cerraduras(st.ops_alfabeto or "a, b", n, positiva))
        except ValueError as err:
            st.ops_cerr = ("error", str(err))
        except Exception as err:
            st.ops_cerr = ("error", f"Error inesperado: {err}")
        abrir_doc("ops", "Operaciones", ft.icons.CALCULATE, doc_ops)

    def doc_ops():
        campo = ft.TextField(label="Cadena de entrada (ej. abba)", value=st.ops_cadena, width=300, dense=True,
                             on_change=lambda e: setattr(st, "ops_cadena", e.control.value),
                             on_submit=lambda e: ops_calcular())
        bloque1 = [ft.Row([campo, boton("Calcular", ft.icons.PLAY_ARROW, lambda e: ops_calcular(), primario=True),
                           boton("Guardar reporte (.txt)", ft.icons.SAVE, lambda e: ops_guardar())],
                          spacing=10, wrap=True),
                   aviso("info", "Una cadena de longitud n tiene exactamente n + 1 prefijos (incluyendo λ) y, "
                                 "como máximo, n(n+1)/2 + 1 subcadenas distintas (incluyendo λ).")]
        if st.ops_msg:
            bloque1.append(aviso(*st.ops_msg))
        if st.ops_res:
            r = st.ops_res
            bloque1 += [
                ft.Text(f"Prefijos ({r['total_prefijos']})", size=13, weight=NEGRITA), fichas_texto(r["prefijos"]),
                ft.Text(f"Sufijos ({r['total_sufijos']})", size=13, weight=NEGRITA), fichas_texto(r["sufijos"]),
                ft.Text(f"Subcadenas ({r['total_subcadenas']})", size=13, weight=NEGRITA), fichas_texto(r["subcadenas"]),
            ]

        alfabeto = ft.TextField(label="Alfabeto Σ (ej. a, b)", value=st.ops_alfabeto, width=200, dense=True,
                                on_change=lambda e: setattr(st, "ops_alfabeto", e.control.value))
        longitud = ft.TextField(label="Longitud máxima n", value=st.ops_n, width=150, dense=True,
                                on_change=lambda e: setattr(st, "ops_n", e.control.value))
        bloque2 = [ft.Row([alfabeto, longitud,
                           boton("Σ*  (Kleene)", ft.icons.ALL_INCLUSIVE, lambda e: ops_cerradura(False), primario=True),
                           boton("Σ⁺  (Positiva)", ft.icons.ADD_CIRCLE, lambda e: ops_cerradura(True))],
                          spacing=10, wrap=True)]
        if st.ops_cerr:
            nivel, dato = st.ops_cerr
            if nivel == "error":
                bloque2.append(aviso("error", dato))
            else:
                bloque2.append(ft.Text(f"{dato['tipo']}  con  Σ = {dato['alfabeto']}  hasta  n = {dato['longitud_max']}"
                                       f"   ·   {dato['total']} cadenas", size=13, weight=NEGRITA))
                bloque2.append(fichas_texto(dato["cadenas"]))

        return ft.Column(
            [tarjeta("Subcadenas, prefijos y sufijos", bloque1, ft.icons.CALCULATE),
             tarjeta("Cerradura de Kleene (Σ*) y cerradura positiva (Σ⁺)", bloque2, ft.icons.ALL_INCLUSIVE)],
            spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # =========================================================================
    # ARCHIVOS
    # =========================================================================
    def limpiar_derivados():
        """Se llama al cambiar el autómata actual: descarta resultados del anterior."""
        st.sin_lambda = st.rep_lambda = st.afd = st.minimo = st.min_base = st.rep_min = None
        st.sim = None
        st.sim_idx = 0
        st.cl_res = None
        st.dir_res = None
        st.lote = None
        st.er = None
        st.errores.clear()
        cache_diseno.clear()
        for clave in ("lambda", "afd", "min", "aut2er"):
            cerrar_doc(clave, refrescar_ahora=False)

    def resolver_ruta_archivo(nombre):
        rutas = [
            os.path.join(UPLOAD_DIR, nombre),
            os.path.join("/app", "uploads", nombre),
            os.path.join(BASE_DIR, "src", "uploads", nombre),
            os.path.join(BASE_DIR, nombre),
        ]
        for ruta in rutas:
            if os.path.exists(ruta):
                return ruta
        for raiz in (UPLOAD_DIR, BASE_DIR):
            if os.path.exists(raiz):
                for r, _, archivos in os.walk(raiz):
                    if nombre in archivos:
                        return os.path.join(r, nombre)
        return None

    def al_cargar_completado(e: ft.FilePickerUploadEvent):
        """Flet llama a este evento varias veces (progreso); solo actuamos al 100 %."""
        if e.error:
            estado(f"Error de transferencia: {e.error}", "error")
            page.update()
            return
        if e.progress is not None and e.progress < 1:
            return
        try:
            ruta = resolver_ruta_archivo(e.file_name)
            if not ruta:
                raise FileNotFoundError(f"No se encontró el archivo '{e.file_name}' en el servidor.")
            nombre = e.file_name.lower()
            if nombre.endswith((".jff", ".xml", ".json")):
                st.automata = AutomataParser.cargar_desde_archivo(ruta)
                limpiar_derivados()
                st.activo = "automata"
                estado(f"Autómata cargado: {e.file_name}  ({viz.tipo_automata(st.automata)}, "
                       f"{len(st.automata.estados)} estados).", "ok")
                refrescar()
            elif nombre.endswith(".txt"):
                procesar_lote(ruta, e.file_name)
            else:
                raise ValueError("Formato no soportado (usa .jff, .xml, .json o .txt).")
        except Exception as err:
            traceback.print_exc()
            estado(f"Error al procesar el archivo: {err}", "error")
            page.update()

    def al_seleccionar_archivo(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        archivo = e.files[0]
        upload_url = page.get_upload_url(archivo.name, 600)
        estado(f"Transfiriendo {archivo.name}…", "info")
        page.update()
        fp_abrir.upload([ft.FilePickerUploadFile(name=archivo.name, upload_url=upload_url, method="PUT")])

    def al_guardar_archivo(e: ft.FilePickerResultEvent):
        if not e.path:
            return
        try:
            ruta = e.path
            if ruta.endswith(".json"):
                AutomataExporter.a_json(st.automata, ruta)
            elif ruta.endswith((".jff", ".xml")):
                AutomataExporter.a_jff_xml(st.automata, ruta)
            else:
                ruta += ".json"
                AutomataExporter.a_json(st.automata, ruta)
            estado(f"Archivo guardado en: {ruta}", "ok")
        except Exception as err:
            estado(f"Error al guardar archivo: {err}", "error")
        page.update()

    fp_abrir = ft.FilePicker(on_result=al_seleccionar_archivo, on_upload=al_cargar_completado)
    fp_guardar = ft.FilePicker(on_result=al_guardar_archivo)
    page.overlay.append(fp_abrir)
    page.overlay.append(fp_guardar)

    def abrir_archivo():
        fp_abrir.pick_files(allowed_extensions=["jff", "json", "xml"], allow_multiple=False)

    def abrir_lote_txt():
        fp_abrir.pick_files(allowed_extensions=["txt"], allow_multiple=False)

    def guardar_archivo():
        if not requiere_automata("Guardar autómata"):
            return
        fp_guardar.save_file(allowed_extensions=["jff", "json", "xml"], file_name="automata.json")

    def exportar_svg():
        if not requiere_automata("Exportar imagen"):
            return
        try:
            ruta = os.path.join(UPLOAD_DIR, "automata.svg")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(viz.a_svg(diseno_de(st.automata)))
            estado(f"Imagen SVG guardada en: {ruta}", "ok")
        except Exception as err:
            estado(f"No se pudo exportar la imagen: {err}", "error")
        page.update()

    # =========================================================================
    # VER · zoom
    # =========================================================================
    def cambiar_zoom(delta=None, fijo=None):
        nuevo = fijo if fijo is not None else st.zoom + delta
        st.zoom = round(max(0.5, min(2.5, nuevo)), 2)
        refrescar()

    # =========================================================================
    # AYUDA
    # =========================================================================
    def mostrar_dialogo(titulo, contenido):
        dlg = ft.AlertDialog(
            title=ft.Text(titulo, size=16, weight=NEGRITA),
            content=contenido,
            actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo(dlg))],
        )
        if hasattr(page, "open"):
            page.open(dlg)
        else:
            page.dialog = dlg
            dlg.open = True
            page.update()

    def cerrar_dialogo(dlg):
        dlg.open = False
        page.update()

    def ayuda_leyenda():
        mostrar_dialogo("Leyenda del dibujo", ft.Column(
            [punto_color(viz.COLOR_ESTADO, "Estado"),
             ft.Text("▷  Triángulo a la izquierda: estado inicial", size=13),
             ft.Text("◎  Doble círculo: estado de aceptación", size=13),
             ft.Text("→  Flecha con etiqueta: transición (símbolos separados por coma)", size=13),
             ft.Text("λ  Transición vacía (sin consumir símbolo)", size=13),
             ft.Divider(height=8),
             punto_color(NARANJA, "Estado activo durante la simulación"),
             punto_color(VERDE, "Estado de aceptación alcanzado (cadena aceptada)"),
             punto_color(ROJO, "Estados activos al rechazar la cadena"),
             punto_color(AZUL, "Cerradura λ del estado elegido")],
            tight=True, spacing=8, width=430))

    def ayuda_acerca():
        mostrar_dialogo("Acerca de", ft.Column(
            [ft.Text("Simulador de Autómatas Finitos y Expresiones Regulares", size=14, weight=NEGRITA),
             ft.Text("Prácticas 3 y 4 · Teoría de la Computación", size=13),
             ft.Text("Interfaz inspirada en JFLAP: menús, barra de herramientas y una pestaña por cada conversión.",
                     size=13, color=C["suave"])],
            tight=True, spacing=6, width=430))

    # =========================================================================
    # ACCIONES DE MENÚ (abren su pestaña)
    # =========================================================================
    def abrir_simulacion():
        abrir_doc("simular", "Probar cadena", ft.icons.PLAY_ARROW, doc_simulacion)

    def abrir_cerradura():
        abrir_doc("cerradura", "Cerradura λ", ft.icons.ACCOUNT_TREE, doc_cerradura)

    def abrir_lote():
        abrir_doc("lote", "Validar lote", ft.icons.CHECKLIST, doc_lote)

    def abrir_regex():
        abrir_doc("regex", "ER → AFN-λ", ft.icons.CODE, doc_regex)

    def abrir_aut2er():
        if not requiere_automata("Autómata → ER"):
            return
        hacer_er()

    def abrir_ops():
        abrir_doc("ops", "Operaciones", ft.icons.CALCULATE, doc_ops)

    # =========================================================================
    # BARRA DE MENÚS (estilo JFLAP) Y BARRA DE HERRAMIENTAS
    # =========================================================================
    def item(texto, icono, accion):
        return ft.MenuItemButton(
            content=ft.Text(texto, size=13),
            leading=ft.Icon(icono, size=18),
            on_click=lambda e, f=accion: f(),
        )

    def submenu(titulo, controles):
        return ft.SubmenuButton(content=ft.Text(titulo, size=13), controls=controles)

    menu = ft.MenuBar(
        expand=True,
        style=ft.MenuStyle(bgcolor=C["barra"], elevation=0),
        controls=[
            submenu("Archivo", [
                item("Abrir autómata…", ft.icons.FOLDER_OPEN, abrir_archivo),
                item("Guardar autómata…", ft.icons.SAVE, guardar_archivo),
                item("Exportar imagen (SVG)", ft.icons.IMAGE, exportar_svg),
                ft.Divider(height=1),
                item("Cerrar pestaña", ft.icons.CLOSE, cerrar_actual),
            ]),
            submenu("Entrada", [
                item("Probar cadena (paso a paso)", ft.icons.PLAY_ARROW, abrir_simulacion),
                item("Validar varias cadenas (.txt)", ft.icons.CHECKLIST, abrir_lote),
                item("Cerradura λ y simulación directa", ft.icons.ACCOUNT_TREE, abrir_cerradura),
            ]),
            submenu("Convertir", [
                item("AFN-λ → AFN (quitar transiciones λ)", ft.icons.CLEANING_SERVICES, hacer_lambda),
                item("AFN → AFD (subconjuntos)", ft.icons.MERGE_TYPE, hacer_afd),
                item("Minimizar AFD", ft.icons.COMPRESS, hacer_min),
                ft.Divider(height=1),
                item("Expresión regular → AFN-λ…", ft.icons.CODE, abrir_regex),
                item("Autómata → expresión regular", ft.icons.TRANSFORM, abrir_aut2er),
            ]),
            submenu("Ver", [
                item("Autómata actual", ft.icons.ACCOUNT_TREE, lambda: ir_doc("automata")),
                ft.Divider(height=1),
                item("Acercar", ft.icons.ZOOM_IN, lambda: cambiar_zoom(delta=0.15)),
                item("Alejar", ft.icons.ZOOM_OUT, lambda: cambiar_zoom(delta=-0.15)),
                item("Tamaño normal", ft.icons.REFRESH, lambda: cambiar_zoom(fijo=1.0)),
            ]),
            submenu("Operaciones", [
                item("Prefijos, sufijos y subcadenas / Σ* y Σ⁺…", ft.icons.CALCULATE, abrir_ops),
            ]),
            submenu("Ayuda", [
                item("Leyenda del dibujo", ft.icons.HELP_OUTLINE, ayuda_leyenda),
                item("Acerca de", ft.icons.INFO_OUTLINE, ayuda_acerca),
            ]),
        ],
    )

    def btn_barra(icono, tip, accion):
        return ft.IconButton(icon=icono, tooltip=tip, icon_size=20, icon_color=C["texto"],
                             on_click=lambda e, f=accion: f())

    def separador():
        return ft.Container(width=1, height=24, bgcolor=C["borde"], margin=ft.margin.symmetric(horizontal=4))

    barra_herramientas = ft.Row(
        [
            btn_barra(ft.icons.FOLDER_OPEN, "Abrir autómata", abrir_archivo),
            btn_barra(ft.icons.SAVE, "Guardar autómata", guardar_archivo),
            btn_barra(ft.icons.IMAGE, "Exportar imagen (SVG)", exportar_svg),
            separador(),
            btn_barra(ft.icons.PLAY_ARROW, "Probar cadena", abrir_simulacion),
            btn_barra(ft.icons.ACCOUNT_TREE, "Cerradura λ y simulación directa", abrir_cerradura),
            btn_barra(ft.icons.CHECKLIST, "Validar varias cadenas", abrir_lote),
            separador(),
            btn_barra(ft.icons.CLEANING_SERVICES, "AFN-λ → AFN", hacer_lambda),
            btn_barra(ft.icons.MERGE_TYPE, "AFN → AFD", hacer_afd),
            btn_barra(ft.icons.COMPRESS, "Minimizar AFD", hacer_min),
            separador(),
            btn_barra(ft.icons.CODE, "Expresión regular → AFN-λ", abrir_regex),
            btn_barra(ft.icons.TRANSFORM, "Autómata → expresión regular", abrir_aut2er),
            separador(),
            btn_barra(ft.icons.ZOOM_OUT, "Alejar", lambda: cambiar_zoom(delta=-0.15)),
            btn_barra(ft.icons.ZOOM_IN, "Acercar", lambda: cambiar_zoom(delta=0.15)),
        ],
        spacing=0, scroll=ft.ScrollMode.AUTO,
    )

    # =========================================================================
    # ARMADO DE LA VENTANA
    # =========================================================================
    st.docs.append(Doc("automata", "Autómata", ft.icons.ACCOUNT_TREE, doc_automata, cerrable=False))

    page.add(
        ft.Column(
            [
                ft.Container(
                    content=ft.Row([menu]),
                    bgcolor=C["barra"],
                    border=ft.border.only(bottom=ft.BorderSide(1, C["borde_suave"])),
                ),
                ft.Container(
                    content=barra_herramientas,
                    bgcolor=C["barra"], height=44, padding=ft.padding.symmetric(horizontal=6),
                    border=ft.border.only(bottom=ft.BorderSide(1, C["borde"])),
                ),
                ft.Container(
                    content=tira, bgcolor=C["tira"], padding=ft.padding.only(left=8, top=6),
                    border=ft.border.only(bottom=ft.BorderSide(1, C["borde"])),
                ),
                cuerpo,
                ft.Container(
                    content=ft.Row([icono_estado, txt_estado, txt_info], spacing=8,
                                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=C["barra"], padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    border=ft.border.only(top=ft.BorderSide(1, C["borde"])),
                ),
            ],
            spacing=0,
            expand=True,
        )
    )
    estado("Listo. Usa Archivo → Abrir autómata para empezar.")
    refrescar()


if __name__ == "__main__":
    ft.app(
        target=main,
        view=ft.AppView.WEB_BROWSER,
        upload_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads")),
        host="0.0.0.0",
        port=8550,
    )