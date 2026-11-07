import math
import os
import re
import flet as ft

# El dibujo de los autómatas usa flet.canvas (incluido en Flet >= 0.7).
try:
    import flet.canvas as cv

    CANVAS_DISPONIBLE = True
except Exception:  # pragma: no cover - versiones muy antiguas de Flet
    cv = None
    CANVAS_DISPONIBLE = False

# --- Módulos de las prácticas 3 y 4 ------------------------------------------
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


# =============================================================================
# PALETA
# =============================================================================
FONDO = "#0e121a"
BARRA = "#121722"
TARJETA = "#171d2a"
TARJETA_2 = "#1d2535"
LIENZO = "#0f1520"
BORDE = "#283044"
TEXTO = "#e8ebf2"
TENUE = "#8a94aa"
ACENTO = "#6c8dff"
VERDE = "#3ddc97"
ROJO = "#ff6b6b"
AMBAR = "#ffb84d"
MORADO = "#b794f6"
CODIGO = "#0b0f17"

# Colores del diagrama
C_ARISTA = "#8191b8"
C_NODO = "#1b2438"
C_NODO_INICIAL = "#243463"
C_NODO_FINAL = "#14312d"
C_ETIQUETA = "#d3dbf2"


def mezclar(color, fondo, t):
    """Mezcla dos colores #rrggbb (t = peso de `color`). Sirve para fondos tenues."""

    def rgb(h):
        h = h.lstrip("#")
        return [int(h[i:i + 2], 16) for i in (0, 2, 4)]

    a, b = rgb(color), rgb(fondo)
    return "#" + "".join(f"{round(x * t + y * (1 - t)):02x}" for x, y in zip(a, b))


COLOR_TIPO = {
    "AFD": VERDE,
    "AFD (parcial)": ACENTO,
    "AFN": AMBAR,
    "AFN-λ": MORADO,
}


# =============================================================================
# FUNCIONES AUXILIARES (no dependen de la interfaz)
# =============================================================================
SIMBOLOS_LAMBDA = {"λ", "ε", "Λ", "lambda", "Lambda", "", None}


def es_lambda(simbolo):
    return simbolo in SIMBOLOS_LAMBDA


def etiqueta_simbolo(simbolo):
    return "λ" if es_lambda(simbolo) else str(simbolo)


def _como_conjunto(destinos):
    if destinos is None:
        return set()
    if isinstance(destinos, (set, frozenset, list, tuple)):
        return set(destinos)
    return {destinos}


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


def clasificar_automata(auto):
    """Devuelve 'AFD', 'AFD (parcial)', 'AFN' o 'AFN-λ' (solo para mostrar una etiqueta)."""
    if auto is None or not auto.estados:
        return None
    tiene_lambda = False
    no_determinista = False
    for (_, simbolo), destinos in auto.transiciones.items():
        destinos = _como_conjunto(destinos)
        if not destinos:
            continue
        if es_lambda(simbolo):
            tiene_lambda = True
        elif len(destinos) > 1:
            no_determinista = True
    if tiene_lambda:
        return "AFN-λ"
    if no_determinista:
        return "AFN"
    simbolos = [s for s in auto.alfabeto if not es_lambda(s)]
    completo = all(
        _como_conjunto(auto.transiciones.get((e, s))) for e in auto.estados for s in simbolos
    )
    return "AFD" if completo else "AFD (parcial)"


def contar_transiciones(auto):
    return sum(len(_como_conjunto(d)) for d in auto.transiciones.values())


def con_scroll_horizontal(tabla):
    """Envuelve una tabla para que haga scroll horizontal sin romper el layout."""
    return ft.Row([tabla], scroll=ft.ScrollMode.AUTO)


def _destinos_de(auto, estado, simbolo):
    if simbolo == "λ":
        resultado = set()
        for k in SIMBOLOS_LAMBDA:
            resultado |= _como_conjunto(auto.transiciones.get((estado, k)))
        return resultado
    return _como_conjunto(auto.transiciones.get((estado, simbolo)))


def llenar_tabla_transiciones(
    tabla, auto, titulo_col="Estado", simbolos_extra=(), etiqueta_estado=None
):
    """
    Rellena un ft.DataTable con la tabla de transiciones de `auto`.
    - simbolos_extra: columnas adicionales (ej. 'λ' en Thompson).
    - etiqueta_estado: función opcional que devuelve texto extra para el estado.
    Si el autómata tiene transiciones λ se agrega la columna 'λ' automáticamente.
    """
    finales = obtener_finales(auto)
    simbolos = {etiqueta_simbolo(s) for s in set(auto.alfabeto) | set(simbolos_extra)}
    if any(
        es_lambda(s) and _como_conjunto(d) for (_, s), d in auto.transiciones.items()
    ):
        simbolos.add("λ")
    simbolos = sorted(simbolos, key=lambda x: (x == "λ", x))

    tabla.columns = [
        ft.DataColumn(ft.Text(titulo_col, weight=ft.FontWeight.BOLD, color=TEXTO))
    ] + [
        ft.DataColumn(ft.Text(s, weight=ft.FontWeight.BOLD, color=TEXTO)) for s in simbolos
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

        color_estado = VERDE if est in finales else (ACENTO if est == auto.estado_inicial else TEXTO)
        celdas = [
            ft.DataCell(
                ft.Text(texto_estado, size=13, weight=ft.FontWeight.BOLD, color=color_estado)
            )
        ]
        for s in simbolos:
            destinos = _destinos_de(auto, est, s)
            if destinos:
                celdas.append(ft.DataCell(ft.Text(formatear_conjunto(destinos), size=13)))
            else:
                celdas.append(ft.DataCell(ft.Text("∅", size=13, color=TENUE)))
        filas.append(ft.DataRow(cells=celdas))

    tabla.rows = filas


# =============================================================================
# COMPONENTES VISUALES REUTILIZABLES
# =============================================================================
def tarjeta(contenido, titulo_txt=None, subtitulo=None, icono=None, col=None):
    """Caja con borde y esquinas redondeadas; es la unidad básica de la interfaz."""
    cuerpo = []
    if titulo_txt:
        textos = [ft.Text(titulo_txt, size=15, weight=ft.FontWeight.BOLD, color=TEXTO)]
        if subtitulo:
            textos.append(ft.Text(subtitulo, size=12, color=TENUE))
        cabecera = []
        if icono:
            cabecera.append(ft.Icon(icono, size=18, color=ACENTO))
        cabecera.append(ft.Column(textos, spacing=2))
        cuerpo.append(ft.Row(cabecera, spacing=10))
    cuerpo.extend(contenido if isinstance(contenido, (list, tuple)) else [contenido])
    return ft.Container(
        content=ft.Column(cuerpo, spacing=14),
        bgcolor=TARJETA,
        border=ft.border.all(1, BORDE),
        border_radius=14,
        padding=18,
        col=col,
    )


def encabezado_vista(texto, descripcion):
    return ft.Column(
        [
            ft.Text(texto, size=26, weight=ft.FontWeight.BOLD, color=TEXTO),
            ft.Text(descripcion, size=13, color=TENUE),
        ],
        spacing=4,
    )


def ficha(texto, color=ACENTO):
    """Etiqueta pequeña tipo 'chip' (prefijos, sufijos, símbolos...)."""
    return ft.Container(
        content=ft.Text(texto, size=13, color=color, font_family="Consolas"),
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
        border_radius=8,
        bgcolor=mezclar(color, TARJETA, 0.14),
        border=ft.border.all(1, mezclar(color, TARJETA, 0.35)),
    )


def caja_codigo(control):
    """Fondo oscuro tipo terminal para textos de procedimiento."""
    return ft.Container(
        content=control,
        bgcolor=CODIGO,
        border=ft.border.all(1, BORDE),
        border_radius=10,
        padding=14,
    )


def nota(texto):
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.icons.INFO_OUTLINE, size=16, color=ACENTO),
                ft.Text(texto, size=12, color=TENUE, expand=True),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        bgcolor=TARJETA_2,
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )


def campo(label, width=None, value=None, hint_text=None):
    return ft.TextField(
        label=label,
        width=width,
        value=value,
        hint_text=hint_text,
        text_size=14,
        filled=True,
        bgcolor=TARJETA_2,
        border_radius=10,
        border_color=BORDE,
        focused_border_color=ACENTO,
        label_style=ft.TextStyle(color=TENUE),
        content_padding=ft.padding.symmetric(horizontal=14, vertical=12),
    )


def boton_primario(texto, icono, on_click=None, disabled=False):
    return ft.ElevatedButton(
        text=texto,
        icon=icono,
        on_click=on_click,
        disabled=disabled,
        style=ft.ButtonStyle(
            bgcolor={
                "disabled": "#2a3245",
                "hovered": mezclar(ACENTO, "#ffffff", 0.85),
                "": ACENTO,
            },
            color={"disabled": "#6b7488", "": "#0b1020"},
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=20, vertical=16),
            elevation=0,
        ),
    )


def boton_secundario(texto, icono, on_click=None, disabled=False):
    return ft.OutlinedButton(
        text=texto,
        icon=icono,
        on_click=on_click,
        disabled=disabled,
        style=ft.ButtonStyle(
            color={"disabled": "#5d667a", "": TEXTO},
            side=ft.BorderSide(1, BORDE),
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=18, vertical=16),
        ),
    )


def estilo_tabla(tabla):
    tabla.border = ft.border.all(1, BORDE)
    tabla.border_radius = 10
    tabla.heading_row_color = TARJETA_2
    tabla.divider_thickness = 0.6
    tabla.column_spacing = 28
    return tabla


def bloque_fichas(titulo_txt, elementos, color, total=None, col=None):
    """Tarjeta con una lista de cadenas mostradas como fichas."""
    elementos = [str(x) if str(x) != "" else "λ" for x in elementos]
    if len(elementos) > 250:
        # Demasiadas fichas harían lenta la pantalla: se muestra como texto corrido.
        cuerpo = caja_codigo(
            ft.Text(", ".join(elementos), size=12, selectable=True, font_family="Consolas")
        )
    else:
        cuerpo = ft.Row(
            [ficha(x, color) for x in elementos], wrap=True, spacing=6, run_spacing=6
        )
    total = len(elementos) if total is None else total
    return tarjeta([cuerpo], f"{titulo_txt} ({total})", col=col)


# =============================================================================
# DIAGRAMA DE AUTÓMATAS (solo visualización)
# =============================================================================
def _unitario(vx, vy):
    d = math.hypot(vx, vy) or 1.0
    return vx / d, vy / d


def _punto_en_borde(centro, hacia, radio):
    ux, uy = _unitario(hacia[0] - centro[0], hacia[1] - centro[1])
    return (centro[0] + ux * radio, centro[1] + uy * radio)


def geometria_diagrama(auto):
    """
    Calcula dónde va cada estado y cada flecha (sin depender de Flet).
    Los estados se ordenan por capas (BFS desde el estado inicial), de izquierda a derecha.
    Devuelve (primitivas, etiquetas, ancho, alto, desplazamiento_x, desplazamiento_y).
    """
    estados = sorted(auto.estados, key=clave_estado)
    conjunto = set(estados)
    finales = set(obtener_finales(auto))
    inicial = auto.estado_inicial

    # Aristas agrupadas: (origen, destino) -> símbolos
    aristas = {}
    for (origen, simbolo), destinos in auto.transiciones.items():
        for destino in _como_conjunto(destinos):
            if origen in conjunto and destino in conjunto:
                aristas.setdefault((origen, destino), set()).add(etiqueta_simbolo(simbolo))

    sucesores = {e: [] for e in estados}
    predecesores = {e: [] for e in estados}
    for (o, d) in aristas:
        if o != d:
            sucesores[o].append(d)
            predecesores[d].append(o)

    # Capas por BFS
    capa = {}
    if inicial in conjunto:
        capa[inicial] = 0
        cola = [inicial]
        while cola:
            u = cola.pop(0)
            for v in sorted(sucesores[u], key=clave_estado):
                if v not in capa:
                    capa[v] = capa[u] + 1
                    cola.append(v)
    capa_sueltos = (max(capa.values()) if capa else -1) + 1
    for e in estados:
        if e not in capa:
            capa[e] = capa_sueltos  # estados inalcanzables, al final
    n_capas = max(capa.values()) + 1
    capas = [[] for _ in range(n_capas)]
    for e in estados:
        capas[capa[e]].append(e)

    # Tamaños según la longitud de los nombres
    max_nombre = max(len(str(e)) for e in estados)
    radio = min(42.0, max(24.0, 4.6 * max_nombre + 8))
    fuente = 14 if max_nombre <= 3 else 12 if max_nombre <= 5 else 11 if max_nombre <= 7 else 10
    sep_x = 2 * radio + 92
    sep_y = 2 * radio + 54

    # Posiciones: cada capa centrada verticalmente, ordenada por el promedio de sus predecesores
    ypos = {}

    def promedio_pred(e, k):
        ys = [ypos[p] for p in predecesores[e] if capa[p] == k - 1 and p in ypos]
        return (sum(ys) / len(ys) if ys else 1e9, clave_estado(e))

    for k, lista in enumerate(capas):
        if k > 0:
            lista.sort(key=lambda e, k=k: promedio_pred(e, k))
        for i, e in enumerate(lista):
            ypos[e] = (i - (len(lista) - 1) / 2) * sep_y
    pos = {e: (capa[e] * sep_x, ypos[e]) for e in estados}
    indice = {e: capas[capa[e]].index(e) for e in estados}

    def radio_ext(e):
        return radio + (5 if e in finales else 0)

    def altura_curva(o, d):
        salto = abs(capa[d] - capa[o])
        if (d, o) in aristas:
            return 42.0
        if capa[d] < capa[o]:
            return min(150.0, 46.0 + 16.0 * salto)
        if capa[d] == capa[o]:
            sep = abs(indice[d] - indice[o])
            return 0.0 if sep == 1 else min(120.0, 36.0 * sep)
        if salto > 1:
            return min(130.0, 28.0 + 14.0 * salto)
        return 0.0

    prims = []
    etiquetas = []
    lim = [math.inf, math.inf, -math.inf, -math.inf]  # minx, miny, maxx, maxy

    def abarcar(x, y, mx=0.0, my=None):
        my = mx if my is None else my
        lim[0] = min(lim[0], x - mx)
        lim[1] = min(lim[1], y - my)
        lim[2] = max(lim[2], x + mx)
        lim[3] = max(lim[3], y + my)

    def poner_etiqueta(x, y, texto):
        etiquetas.append((x, y, texto))
        abarcar(x, y, (len(texto) * 7.0 + 12) / 2, 9)

    # Estados
    for e in estados:
        x, y = pos[e]
        prims.append(("estado", x, y, radio, e == inicial, e in finales, str(e), fuente))
        abarcar(x, y, radio_ext(e) + 2)
        if e == inicial:
            prims.append(("inicial", (x - radio_ext(e) - 1, y)))
            abarcar(x - radio_ext(e) - 42, y)

    # Transiciones
    orden = sorted(aristas.items(), key=lambda kv: (clave_estado(kv[0][0]), clave_estado(kv[0][1])))
    for (o, d), simbolos in orden:
        texto = ",".join(sorted(simbolos, key=lambda s: (s == "λ", s)))
        ro, rd = radio_ext(o), radio_ext(d)

        if o == d:  # bucle sobre el mismo estado
            x, y = pos[o]
            # El bucle va hacia el lado con menos aristas verticales (arriba por defecto)
            arriba = sum(
                1 for n in capas[capa[o]]
                if n != o and indice[n] < indice[o] and ((o, n) in aristas or (n, o) in aristas)
            )
            abajo = sum(
                1 for n in capas[capa[o]]
                if n != o and indice[n] > indice[o] and ((o, n) in aristas or (n, o) in aristas)
            )
            s = 1.0 if arriba > abajo else -1.0
            a = (x - 0.5 * ro, y + s * 0.866 * ro)
            b = (x + 0.5 * ro, y + s * 0.866 * ro)
            c1 = (x - 36, y + s * (ro + 46))
            c2 = (x + 36, y + s * (ro + 46))
            ux, uy = _unitario(b[0] - c2[0], b[1] - c2[1])
            fin = (b[0] - ux * 6, b[1] - uy * 6)
            prims.append(("cubica", a, c1, c2, fin))
            prims.append(("flecha", b, (ux, uy)))
            cima = y + s * (0.9665 * ro + 34.5)
            abarcar(x, cima + s * 14, 20)
            poner_etiqueta(x, cima + s * 12, texto)
            continue

        (x0, y0), (x1, y1) = pos[o], pos[d]
        vx, vy = x1 - x0, y1 - y0
        dist = math.hypot(vx, vy) or 1.0
        nx, ny = -vy / dist, vx / dist
        h = altura_curva(o, d)
        cx, cy = (x0 + x1) / 2 + nx * h, (y0 + y1) / 2 + ny * h
        ini = _punto_en_borde(pos[o], (cx, cy), ro)
        tip = _punto_en_borde(pos[d], (cx, cy), rd + 1)
        ux, uy = _unitario(tip[0] - cx, tip[1] - cy)
        fin = (tip[0] - ux * 6, tip[1] - uy * 6)

        if h == 0:
            prims.append(("linea", ini, fin))
            medio = ((ini[0] + fin[0]) / 2, (ini[1] + fin[1]) / 2)
            if ny > 0.001:
                signo = -1.0
            elif ny < -0.001:
                signo = 1.0
            else:
                signo = 1.0 if nx < 0 else -1.0
        else:
            prims.append(("cuadratica", ini, (cx, cy), fin))
            medio = (
                0.25 * ini[0] + 0.5 * cx + 0.25 * fin[0],
                0.25 * ini[1] + 0.5 * cy + 0.25 * fin[1],
            )
            signo = 1.0 if h > 0 else -1.0
        prims.append(("flecha", tip, (ux, uy)))
        abarcar(ini[0], ini[1])
        abarcar(tip[0], tip[1])
        poner_etiqueta(medio[0] + nx * signo * 12, medio[1] + ny * signo * 12, texto)

    margen = 30.0
    ancho_real = lim[2] - lim[0]
    alto_real = lim[3] - lim[1]
    ancho = max(560.0, ancho_real + 2 * margen)
    alto = max(260.0, alto_real + 2 * margen)
    ox = (ancho - ancho_real) / 2 - lim[0]
    oy = (alto - alto_real) / 2 - lim[1]
    return prims, etiquetas, ancho, alto, ox, oy


def _texto_canvas(x, y, valor, size, color, negrita=False):
    """Texto centrado en (x, y) dentro del canvas."""
    estilo = ft.TextStyle(
        size=size,
        color=color,
        weight=ft.FontWeight.BOLD if negrita else ft.FontWeight.W_500,
    )
    try:
        return cv.Text(x, y, valor, style=estilo, alignment=ft.alignment.center)
    except TypeError:  # versiones sin 'alignment': centrado aproximado
        ancho = len(valor) * size * 0.58
        return cv.Text(x - ancho / 2, y - size * 0.6, valor, style=estilo)


def _flecha_canvas(punta, direccion, color, largo=11.0, semiancho=4.8):
    ux, uy = direccion
    bx, by = punta[0] - ux * largo, punta[1] - uy * largo
    px, py = -uy, ux
    return cv.Path(
        elements=[
            cv.Path.MoveTo(punta[0], punta[1]),
            cv.Path.LineTo(bx + px * semiancho, by + py * semiancho),
            cv.Path.LineTo(bx - px * semiancho, by - py * semiancho),
            cv.Path.Close(),
        ],
        paint=ft.Paint(color=color, style=ft.PaintingStyle.FILL),
    )


def construir_shapes(prims, etiquetas, ox, oy):
    """Convierte la geometría calculada en figuras de flet.canvas."""
    trazo = ft.Paint(color=C_ARISTA, stroke_width=1.8, style=ft.PaintingStyle.STROKE)
    trazo_inicial = ft.Paint(color=ACENTO, stroke_width=2.2, style=ft.PaintingStyle.STROKE)

    def P(p):
        return (p[0] + ox, p[1] + oy)

    capa_aristas, capa_nodos, capa_flechas, capa_texto = [], [], [], []

    for p in prims:
        tipo = p[0]
        if tipo == "linea":
            a, b = P(p[1]), P(p[2])
            capa_aristas.append(cv.Line(a[0], a[1], b[0], b[1], paint=trazo))
        elif tipo == "cuadratica":
            a, c, b = P(p[1]), P(p[2]), P(p[3])
            capa_aristas.append(
                cv.Path(
                    elements=[
                        cv.Path.MoveTo(a[0], a[1]),
                        cv.Path.QuadraticTo(c[0], c[1], b[0], b[1], 1),
                    ],
                    paint=trazo,
                )
            )
        elif tipo == "cubica":
            a, c1, c2, b = P(p[1]), P(p[2]), P(p[3]), P(p[4])
            capa_aristas.append(
                cv.Path(
                    elements=[
                        cv.Path.MoveTo(a[0], a[1]),
                        cv.Path.CubicTo(c1[0], c1[1], c2[0], c2[1], b[0], b[1]),
                    ],
                    paint=trazo,
                )
            )
        elif tipo == "flecha":
            capa_flechas.append(_flecha_canvas(P(p[1]), p[2], C_ARISTA))
        elif tipo == "inicial":
            punta = P(p[1])
            capa_aristas.append(
                cv.Line(punta[0] - 40, punta[1], punta[0] - 6, punta[1], paint=trazo_inicial)
            )
            capa_flechas.append(_flecha_canvas(punta, (1.0, 0.0), ACENTO))
        elif tipo == "estado":
            _, x, y, r, es_ini, es_fin, nombre, fuente = p
            x, y = x + ox, y + oy
            relleno = C_NODO_INICIAL if es_ini else (C_NODO_FINAL if es_fin else C_NODO)
            borde = VERDE if es_fin else ACENTO
            capa_nodos.append(cv.Circle(x, y, r, paint=ft.Paint(color=relleno, style=ft.PaintingStyle.FILL)))
            capa_nodos.append(
                cv.Circle(x, y, r, paint=ft.Paint(color=borde, stroke_width=2.2, style=ft.PaintingStyle.STROKE))
            )
            if es_fin:
                capa_nodos.append(
                    cv.Circle(
                        x, y, r + 5,
                        paint=ft.Paint(color=borde, stroke_width=2.0, style=ft.PaintingStyle.STROKE),
                    )
                )
            capa_nodos.append(_texto_canvas(x, y, nombre, fuente, TEXTO, True))

    fondo_etiqueta = ft.Paint(color=LIENZO, style=ft.PaintingStyle.FILL)
    for (x, y, texto) in etiquetas:
        x, y = x + ox, y + oy
        ancho = len(texto) * 7.0 + 12
        capa_texto.append(
            cv.Rect(x - ancho / 2, y - 9, ancho, 18, border_radius=ft.border_radius.all(5), paint=fondo_etiqueta)
        )
        capa_texto.append(_texto_canvas(x, y, texto, 12, C_ETIQUETA))

    return capa_aristas + capa_nodos + capa_flechas + capa_texto


class PanelDiagrama:
    """Tarjeta que dibuja un autómata (solo visualización) y muestra su tipo: AFD, AFN, AFN-λ."""

    def __init__(self, titulo_panel, col=None):
        self.objeto = None  # último autómata dibujado (se compara por identidad)
        self.txt_badge = ft.Text("", size=11, weight=ft.FontWeight.BOLD)
        self.badge = ft.Container(
            content=self.txt_badge,
            padding=ft.padding.symmetric(horizontal=10, vertical=3),
            border_radius=20,
            visible=False,
        )
        self.txt_meta = ft.Text("", size=12, color=TENUE)
        self.zona = ft.Container(
            content=self._vacio(),
            bgcolor=LIENZO,
            border=ft.border.all(1, BORDE),
            border_radius=12,
            padding=10,
            alignment=ft.alignment.center,
        )
        cabecera = ft.Row(
            [
                ft.Icon(ft.icons.ACCOUNT_TREE, size=18, color=ACENTO),
                ft.Text(titulo_panel, size=15, weight=ft.FontWeight.BOLD, color=TEXTO),
                self.badge,
                ft.Container(expand=True),
                self.txt_meta,
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.card = ft.Container(
            content=ft.Column([cabecera, self.zona, self._leyenda()], spacing=12),
            bgcolor=TARJETA,
            border=ft.border.all(1, BORDE),
            border_radius=14,
            padding=18,
            col=col,
        )

    @staticmethod
    def _vacio(mensaje="Carga o genera un autómata para verlo aquí."):
        return ft.Container(
            height=150,
            alignment=ft.alignment.center,
            content=ft.Column(
                [
                    ft.Icon(ft.icons.ACCOUNT_TREE, size=34, color="#3a4560"),
                    ft.Text(mensaje, size=13, color=TENUE),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
        )

    @staticmethod
    def _leyenda():
        def item(relleno, borde, texto, aro=False):
            marca = ft.Container(
                width=14,
                height=14,
                border_radius=7,
                bgcolor=relleno,
                border=ft.border.all(2, borde),
            )
            if aro:
                marca = ft.Container(
                    content=marca,
                    padding=2,
                    border_radius=10,
                    border=ft.border.all(1.5, borde),
                )
            return ft.Row([marca, ft.Text(texto, size=11, color=TENUE)], spacing=6)

        return ft.Row(
            [
                item(C_NODO_INICIAL, ACENTO, "Estado inicial (flecha de entrada)"),
                item(C_NODO_FINAL, VERDE, "Estado final (doble aro)", aro=True),
                ft.Text("λ = transición vacía", size=11, color=TENUE),
            ],
            spacing=20,
            wrap=True,
            run_spacing=6,
        )

    def limpiar(self):
        self.objeto = None
        self.badge.visible = False
        self.txt_meta.value = ""
        self.zona.content = self._vacio()

    def mostrar(self, auto):
        self.limpiar()
        self.objeto = auto
        if auto is None or not auto.estados:
            return

        tipo = clasificar_automata(auto)
        color = COLOR_TIPO.get(tipo, ACENTO)
        self.txt_badge.value = tipo
        self.txt_badge.color = color
        self.badge.bgcolor = mezclar(color, TARJETA, 0.16)
        self.badge.visible = True
        self.txt_meta.value = f"{len(auto.estados)} estados, {contar_transiciones(auto)} transiciones"

        if not CANVAS_DISPONIBLE:
            self.zona.content = self._vacio(
                "Tu versión de Flet no incluye flet.canvas. Actualiza con: pip install -U flet"
            )
            return
        try:
            prims, etiquetas, ancho, alto, ox, oy = geometria_diagrama(auto)
            shapes = construir_shapes(prims, etiquetas, ox, oy)
            lienzo = cv.Canvas(shapes=shapes, width=ancho, height=alto)
            self.zona.content = ft.Row(
                [lienzo], scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.CENTER
            )
        except Exception as err:
            self.zona.content = self._vacio(f"No se pudo dibujar el autómata: {err}")


# =============================================================================
# APLICACIÓN
# =============================================================================
def main(page: ft.Page):
    page.title = "Simulador de Autómatas Finitos y Expresiones Regulares - P3 & P4"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ACENTO)
    page.dark_theme = ft.Theme(color_scheme_seed=ACENTO)
    page.bgcolor = FONDO
    page.padding = 0
    page.spacing = 0

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
    resultado_op1_actual = {}
    vista_actual = "editor"

    # -------------------------------------------------------------------------
    # COMPONENTES: Definición y archivos
    # -------------------------------------------------------------------------
    txt_status_carga = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    txt_definicion_formal = ft.Text(
        "No hay autómata cargado.", size=14, selectable=True, color=TEXTO
    )
    data_table_transiciones = estilo_tabla(
        ft.DataTable(columns=[ft.DataColumn(ft.Text("Estado"))], rows=[])
    )

    # -------------------------------------------------------------------------
    # COMPONENTES: Simulación estándar
    # -------------------------------------------------------------------------
    input_cadena_simular = campo("Cadena a simular (ej. 0101)", width=300)
    txt_resultado_simulacion = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    list_pasos_simulacion = ft.ListView(spacing=5, padding=10, auto_scroll=True, height=250)

    # -------------------------------------------------------------------------
    # COMPONENTES: 2.1 Cerradura λ y simulación directa
    # -------------------------------------------------------------------------
    dropdown_estado_cerradura = ft.Dropdown(
        label="Seleccionar estado",
        width=200,
        options=[],
        border_radius=10,
        border_color=BORDE,
        focused_border_color=ACENTO,
        filled=True,
        bgcolor=TARJETA_2,
        text_size=14,
    )
    txt_resultado_cerradura = ft.Text("", size=15, weight=ft.FontWeight.BOLD)
    input_cadena_directa = campo("Cadena a simular en AFN-λ", width=300)
    txt_resultado_simulacion_directa = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    data_table_pasos_directos = estilo_tabla(
        ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Paso")),
                ft.DataColumn(ft.Text("Símbolo")),
                ft.DataColumn(ft.Text("Activos (Antes CL)")),
                ft.DataColumn(ft.Text("Activos (Después CL)")),
                ft.DataColumn(ft.Text("Detalle")),
            ],
            rows=[],
        )
    )

    # -------------------------------------------------------------------------
    # COMPONENTES: 2.2 AFN-λ → AFN
    # -------------------------------------------------------------------------
    txt_info_conversion_lambda = ft.Text("", size=14, selectable=True)
    txt_explicacion_paso_a_paso_22 = ft.Text("", size=13, selectable=True, font_family="Consolas")
    data_table_pasos_eliminacion = estilo_tabla(
        ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Estado (q)")),
                ft.DataColumn(ft.Text("Símbolo (a)")),
                ft.DataColumn(ft.Text("1. CL(q)")),
                ft.DataColumn(ft.Text("2. δ(CL(q), a)")),
                ft.DataColumn(ft.Text("3. δ'(q, a) = CL(...)")),
            ],
            rows=[],
        )
    )
    data_table_afn_sin_lambda = estilo_tabla(
        ft.DataTable(columns=[ft.DataColumn(ft.Text("Estado"))], rows=[])
    )

    # -------------------------------------------------------------------------
    # COMPONENTES: 2.3 AFN → AFD
    # -------------------------------------------------------------------------
    txt_info_afd = ft.Text("", size=14, selectable=True)
    txt_mapeo_subconjuntos = ft.Text("", size=13, selectable=True, font_family="Consolas")
    data_table_afd = estilo_tabla(
        ft.DataTable(columns=[ft.DataColumn(ft.Text("Estado AFD"))], rows=[])
    )

    # -------------------------------------------------------------------------
    # COMPONENTES: 2.4 Minimización
    # -------------------------------------------------------------------------
    txt_info_minimizacion = ft.Text("", size=14, selectable=True)
    txt_particiones_historial = ft.Text("", size=13, selectable=True, font_family="Consolas")
    data_table_afd_minimo = estilo_tabla(
        ft.DataTable(columns=[ft.DataColumn(ft.Text("Clase"))], rows=[])
    )

    # -------------------------------------------------------------------------
    # COMPONENTES: 2.5 Validación en lote
    # -------------------------------------------------------------------------
    txt_status_lote = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    data_table_lote = estilo_tabla(
        ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Línea")),
                ft.DataColumn(ft.Text("Cadena")),
                ft.DataColumn(ft.Text("Resultado")),
                ft.DataColumn(ft.Text("Estados Activos Finales")),
            ],
            rows=[],
        )
    )
    btn_guardar_reporte_lote = boton_secundario(
        "Generar informe (.txt)", ft.icons.SUMMARIZE, disabled=True
    )

    # -------------------------------------------------------------------------
    # COMPONENTES: P4 ER → AFN-λ (Thompson)
    # -------------------------------------------------------------------------
    input_regex = campo(
        "Expresión regular (ej. (a|b)*abb)",
        width=400,
        hint_text="Operadores válidos: |, +, *, (), .",
    )
    txt_status_regex = ft.Text(
        "", size=14, weight=ft.FontWeight.BOLD, font_family="Consolas", selectable=True
    )
    txt_pasos_thompson = ft.Text("", size=13, selectable=True, font_family="Consolas")
    data_table_thompson = estilo_tabla(
        ft.DataTable(columns=[ft.DataColumn(ft.Text("Estado"))], rows=[])
    )
    btn_cargar_en_p3 = boton_secundario(
        "Cargar AFN-λ en el simulador", ft.icons.PLAY_FOR_WORK, disabled=True
    )

    # -------------------------------------------------------------------------
    # COMPONENTES: P4 Autómata → ER
    # -------------------------------------------------------------------------
    txt_status_ej3 = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    txt_resultado_regex_final = ft.Text(
        "", size=16, weight=ft.FontWeight.BOLD, selectable=True, font_family="Consolas"
    )
    txt_historial_eliminacion = ft.Text("", size=13, selectable=True, font_family="Consolas")

    # -------------------------------------------------------------------------
    # COMPONENTES: Operaciones avanzadas
    # -------------------------------------------------------------------------
    input_cadena_ops = campo("Cadena de entrada (ej. abba)", width=300)
    txt_status_ops = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    col_resultado_ops = ft.Column(spacing=16)

    input_alfabeto_cerradura = campo("Alfabeto Σ (ej. a, b)", width=200, value="a, b")
    input_longitud_max = campo("Longitud máxima (n)", width=170, value="3")
    col_resultado_cerradura = ft.Column(spacing=16)

    # -------------------------------------------------------------------------
    # COMPONENTES: paneles de diagrama (solo visualización)
    # -------------------------------------------------------------------------
    mitad = {"xs": 12, "xl": 6}
    panel_def = PanelDiagrama("Diagrama del autómata")
    panel_sim = PanelDiagrama("Diagrama del autómata")
    panel_cl = PanelDiagrama("Diagrama del autómata")
    panel_22_orig = PanelDiagrama("Original", col=mitad)
    panel_22_res = PanelDiagrama("Resultado", col=mitad)
    panel_23_orig = PanelDiagrama("Original", col=mitad)
    panel_23_res = PanelDiagrama("Resultado", col=mitad)
    panel_24_orig = PanelDiagrama("Original", col=mitad)
    panel_24_res = PanelDiagrama("Resultado", col=mitad)
    panel_thompson = PanelDiagrama("AFN-λ generado")
    panel_er = PanelDiagrama("Diagrama del autómata")

    # Paneles que siempre muestran el autómata cargado (se redibujan al entrar a la vista)
    paneles_por_vista = {
        "editor": [panel_def],
        "simulacion": [panel_sim],
        "cerradura": [panel_cl],
        "lambda": [panel_22_orig],
        "afd": [panel_23_orig],
        "a_regex": [panel_er],
    }

    def sincronizar_paneles():
        for panel in paneles_por_vista.get(vista_actual, []):
            if panel.objeto is not automata_actual:
                panel.mostrar(automata_actual)

    # =========================================================================
    # ACTUALIZACIÓN DE VISTAS
    # =========================================================================
    def actualizar_resumen_superior():
        try:
            tipo = clasificar_automata(automata_actual)
        except Exception:
            tipo = None
        if not tipo:
            txt_resumen.value = "Sin autómata"
            punto_resumen.bgcolor = TENUE
        else:
            txt_resumen.value = f"{tipo}, {len(automata_actual.estados)} estados"
            punto_resumen.bgcolor = COLOR_TIPO.get(tipo, ACENTO)

    def actualizar_vistas_definicion():
        if not automata_actual.estados:
            txt_definicion_formal.value = "Autómata vacío."
            data_table_transiciones.columns = [ft.DataColumn(ft.Text("Estado"))]
            data_table_transiciones.rows = []
            dropdown_estado_cerradura.options = []
            dropdown_estado_cerradura.value = None
            sincronizar_paneles()
            actualizar_resumen_superior()
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
        dropdown_estado_cerradura.options = [ft.dropdown.Option(est) for est in estados_ordenados]
        dropdown_estado_cerradura.value = estados_ordenados[0]

        sincronizar_paneles()
        actualizar_resumen_superior()
        page.update()

    def limpiar_resultados():
        """Borra resultados de la sesión anterior (se llama al cargar un autómata nuevo)."""
        nonlocal automata_sin_lambda_convertido, afd_convertido, afd_minimo_convertido
        nonlocal resultados_lote_actual, nombre_archivo_lote_actual

        # Si no se resetean, la minimización usaría el AFD del autómata anterior
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
        for panel in (panel_22_res, panel_23_res, panel_24_orig, panel_24_res):
            panel.limpiar()

    def avisar_sin_automata(control):
        control.value = "⚠️ Primero carga o define un autómata."
        control.color = AMBAR
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
            txt_status_lote.color = AMBAR
            txt_status_carga.value = txt_status_lote.value
            txt_status_carga.color = AMBAR
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
            color = VERDE if res["es_aceptada"] else ROJO
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
        txt_status_lote.color = VERDE
        txt_status_carga.value = f"✅ Lote cargado: {nombre_archivo}"
        txt_status_carga.color = VERDE

    def al_cargar_completado(e: ft.FilePickerUploadEvent):
        """Flet llama a este evento varias veces (progreso); solo actuamos al 100 %."""
        nonlocal automata_actual

        if e.error:
            txt_status_carga.value = f"❌ Error de transferencia: {e.error}"
            txt_status_carga.color = ROJO
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
                txt_status_carga.color = VERDE
            elif nombre.endswith(".txt"):
                procesar_lote_desde_txt(ruta_servidor, e.file_name)
            else:
                raise ValueError("Formato no soportado (usa .jff, .xml, .json o .txt).")
        except Exception as err:
            txt_status_carga.value = f"❌ Error al procesar el archivo: {err}"
            txt_status_carga.color = ROJO

        page.update()

    def al_seleccionar_archivo(e: ft.FilePickerResultEvent):
        if not e.files:
            return

        archivo = e.files[0]
        upload_url = page.get_upload_url(archivo.name, 600)

        txt_status_carga.value = f"⏳ Transfiriendo {archivo.name}..."
        txt_status_carga.color = ACENTO
        page.update()

        file_picker_abrir.upload(
            [ft.FilePickerUploadFile(name=archivo.name, upload_url=upload_url, method="PUT")]
        )

    def al_guardar_archivo(e: ft.FilePickerResultEvent):
        try:
            nombre_sugerido = "automata_exportado.json"
            ruta_temporal = os.path.join(UPLOAD_DIR, nombre_sugerido)

            # Generar el archivo temporalmente en el servidor
            AutomataExporter.a_json(automata_actual, ruta_temporal)

            if e.path:
                # Modo Escritorio / Local
                ruta_destino = e.path
                if ruta_destino.endswith((".jff", ".xml")):
                    AutomataExporter.a_jff_xml(automata_actual, ruta_destino)
                else:
                    if not ruta_destino.endswith(".json"):
                        ruta_destino += ".json"
                    AutomataExporter.a_json(automata_actual, ruta_destino)
                txt_status_carga.value = f"✅ Archivo guardado en: {ruta_destino}"
            else:
                # Modo Web (Navegador): Fuerza la descarga directa al equipo
                url_descarga = page.get_upload_url(nombre_sugerido, 600)
                page.launch_url(url_descarga)
                txt_status_carga.value = "✅ Archivo descargado en tu navegador exitosamente."

            txt_status_carga.color = VERDE
        except Exception as err:
            txt_status_carga.value = f"❌ Error al guardar archivo: {err}"
            txt_status_carga.color = ROJO

        page.update()

    def generar_informe_lote(e):
        if not resultados_lote_actual:
            txt_status_lote.value = "⚠️ No hay resultados de lote para exportar."
            txt_status_lote.color = AMBAR
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
            txt_status_lote.color = VERDE
        except Exception as err:
            txt_status_lote.value = f"❌ Error al escribir el informe: {err}"
            txt_status_lote.color = ROJO

        page.update()

    btn_guardar_reporte_lote.on_click = generar_informe_lote

    file_picker_abrir = ft.FilePicker(on_result=al_seleccionar_archivo, on_upload=al_cargar_completado)
    file_picker_guardar = ft.FilePicker(on_result=al_guardar_archivo)
    page.overlay.append(file_picker_abrir)
    page.overlay.append(file_picker_guardar)

    def abrir_dialogo_abrir(_=None):
        file_picker_abrir.pick_files(
            allowed_extensions=["jff", "json", "xml", "txt"], allow_multiple=False
        )

    def abrir_dialogo_lote(_=None):
        file_picker_abrir.pick_files(allowed_extensions=["txt"], allow_multiple=False)

    def abrir_dialogo_guardar(_=None):
        file_picker_guardar.save_file(
            allowed_extensions=["jff", "json", "xml"], file_name="automata.json"
        )

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
            txt_resultado_simulacion.color = ROJO
            page.update()
            return

        for paso in traza:
            list_pasos_simulacion.controls.append(
                ft.Text(texto_de_paso(paso), size=13, font_family="Consolas")
            )

        if es_valida:
            txt_resultado_simulacion.value = f"🎉 ¡CADENA ACEPTADA! ('{cadena}')"
            txt_resultado_simulacion.color = VERDE
        else:
            txt_resultado_simulacion.value = f"🚫 CADENA RECHAZADA ('{cadena}')"
            txt_resultado_simulacion.color = ROJO
        page.update()

    # =========================================================================
    # 2.1 CERRADURA λ Y SIMULACIÓN DIRECTA
    # =========================================================================
    def calcular_cerradura_individual(e):
        estado_sel = dropdown_estado_cerradura.value
        if not estado_sel:
            txt_resultado_cerradura.value = "⚠️ Selecciona un estado."
            txt_resultado_cerradura.color = AMBAR
            page.update()
            return

        try:
            cerradura = CerraduraLambdaSimulador.calcular_cerradura_estado(automata_actual, estado_sel)
            txt_resultado_cerradura.value = f"CL({estado_sel}) = {formatear_conjunto(cerradura)}"
            txt_resultado_cerradura.color = VERDE
        except Exception as err:
            txt_resultado_cerradura.value = f"❌ Error: {err}"
            txt_resultado_cerradura.color = ROJO
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
            txt_resultado_simulacion_directa.color = ROJO
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
            txt_resultado_simulacion_directa.color = VERDE
        else:
            txt_resultado_simulacion_directa.value = f"🚫 CADENA RECHAZADA DIRECTAMENTE ('{cadena}')"
            txt_resultado_simulacion_directa.color = ROJO
        page.update()

    # =========================================================================
    # 2.2 ELIMINACIÓN DE TRANSICIONES λ
    # =========================================================================
    def ejecutar_eliminacion_lambda(e):
        nonlocal automata_sin_lambda_convertido
        data_table_afn_sin_lambda.rows = []
        data_table_pasos_eliminacion.rows = []
        panel_22_res.limpiar()

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
            txt_info_conversion_lambda.color = VERDE

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

            panel_22_orig.mostrar(automata_actual)
            panel_22_res.mostrar(nuevo)

        except Exception as err:
            txt_info_conversion_lambda.value = f"❌ Error durante la conversión: {err}"
            txt_info_conversion_lambda.color = ROJO
        page.update()

    # =========================================================================
    # 2.3 AFN → AFD
    # =========================================================================
    def ejecutar_conversion_afd(e):
        nonlocal afd_convertido
        data_table_afd.rows = []
        panel_23_res.limpiar()

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
            txt_info_afd.color = VERDE

            mapeo = getattr(afd_convertido, "mapeo_subconjuntos", {})
            lineas = [f"{alias} = {formatear_conjunto(conj)}" for alias, conj in sorted(mapeo.items())]
            txt_mapeo_subconjuntos.value = "Equivalencia de subconjuntos:\n" + "\n".join(lineas)

            llenar_tabla_transiciones(data_table_afd, afd_convertido, titulo_col="Estado AFD")

            panel_23_orig.mostrar(automata_actual)
            panel_23_res.mostrar(afd_convertido)
        except Exception as err:
            txt_info_afd.value = f"❌ Error durante la conversión a AFD: {err}"
            txt_info_afd.color = ROJO
        page.update()

    # =========================================================================
    # 2.4 MINIMIZACIÓN
    # =========================================================================
    def ejecutar_minimizacion_afd(e):
        nonlocal afd_minimo_convertido
        data_table_afd_minimo.rows = []
        panel_24_res.limpiar()

        base = afd_convertido if (afd_convertido and afd_convertido.estados) else automata_actual
        if not base.estados:
            txt_info_minimizacion.value = "⚠️ Primero carga un autómata o conviértelo a AFD."
            txt_info_minimizacion.color = AMBAR
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
            txt_info_minimizacion.color = VERDE

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

            panel_24_orig.mostrar(base)
            panel_24_res.mostrar(afd_minimo_convertido)
        except Exception as err:
            txt_info_minimizacion.value = f"❌ Error durante la minimización: {err}"
            txt_info_minimizacion.color = ROJO
        page.update()

    # =========================================================================
    # P4 · ER → AFN-λ (THOMPSON)
    # =========================================================================
    def ejecutar_construccion_thompson(e):
        nonlocal afn_thompson_generado
        patron = (input_regex.value or "").strip()

        if not patron:
            txt_status_regex.value = "⚠️ Ingresa una expresión regular."
            txt_status_regex.color = AMBAR
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
            txt_status_regex.color = VERDE

            lineas = ["=== CONSTRUCCIÓN DE THOMPSON PASO A PASO ==="]
            for i, paso in enumerate(historial, 1):
                lineas.append(f"Paso {i}: {paso['operacion']}")
                lineas.append(f"  • sub-inicial: {paso['estado_inicial']} | sub-final: {paso['estado_final']}")
            txt_pasos_thompson.value = "\n".join(lineas)

            llenar_tabla_transiciones(data_table_thompson, afn, simbolos_extra=("λ",))
            panel_thompson.mostrar(afn)
            btn_cargar_en_p3.disabled = False

        except RegexSyntaxError as err:
            marcador = " " * err.posicion + "^"
            txt_status_regex.value = (
                f"❌ ERROR SINTÁCTICO en la posición {err.posicion}:\n"
                f"  {patron}\n"
                f"  {marcador}\n"
                f"Mensaje: {err.mensaje}"
            )
            txt_status_regex.color = ROJO
            txt_pasos_thompson.value = ""
            data_table_thompson.rows = []
            panel_thompson.limpiar()
            btn_cargar_en_p3.disabled = True
        except Exception as err:
            txt_status_regex.value = f"❌ Error inesperado: {err}"
            txt_status_regex.color = ROJO
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
        txt_status_carga.color = VERDE
        ir_a("editor")

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
            txt_status_ej3.color = ROJO
            txt_resultado_regex_final.value = ""
            txt_historial_eliminacion.value = ""
            page.update()
            return

        try:
            regex_final, historial = ConversorAutomataARegex.convertir_a_regex(automata_actual)

            txt_status_ej3.value = f"✅ Verificación exitosa: {mensaje}"
            txt_status_ej3.color = VERDE
            txt_resultado_regex_final.value = f"Éxito! Expresión Regular resultante:\n  R = {regex_final}"
            txt_resultado_regex_final.color = VERDE

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
            txt_status_ej3.color = ROJO
        page.update()

    # =========================================================================
    # OPERACIONES AVANZADAS
    # =========================================================================
    def ejecutar_operacion_prefijos(e):
        nonlocal resultado_op1_actual
        cadena = (input_cadena_ops.value or "").strip()

        if not cadena:
            txt_status_ops.value = "⚠️ Ingresa una cadena válida."
            txt_status_ops.color = AMBAR
            page.update()
            return

        try:
            res = OperacionesAvanzadas.calcular_prefijos_sufijos_subcadenas(cadena)
            res["cadena"] = cadena
            resultado_op1_actual = res

            txt_status_ops.value = f"✅ Análisis completado para '{cadena}' (n = {res['longitud_n']})"
            txt_status_ops.color = VERDE

            col_resultado_ops.controls = [
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            nota("Una cadena de longitud n tiene exactamente (n + 1) prefijos (incluyendo λ)."),
                            col={"xs": 12, "lg": 6},
                        ),
                        ft.Container(
                            nota("Una cadena de longitud n tiene como máximo (n(n+1)/2 + 1) subcadenas distintas (incluyendo λ)."),
                            col={"xs": 12, "lg": 6},
                        ),
                    ],
                    spacing=12,
                    run_spacing=12,
                ),
                ft.ResponsiveRow(
                    [
                        bloque_fichas("Prefijos", res["prefijos"], ACENTO, res["total_prefijos"], col={"xs": 12, "lg": 6}),
                        bloque_fichas("Sufijos", res["sufijos"], MORADO, res["total_sufijos"], col={"xs": 12, "lg": 6}),
                        bloque_fichas("Subcadenas", res["subcadenas"], VERDE, res["total_subcadenas"], col=12),
                    ],
                    spacing=16,
                    run_spacing=16,
                ),
            ]
        except Exception as err:
            txt_status_ops.value = f"❌ Error: {err}"
            txt_status_ops.color = ROJO
        page.update()

    def guardar_informe_operaciones(e):
        if not resultado_op1_actual:
            txt_status_ops.value = "⚠️ No hay resultados de subcadenas para exportar."
            txt_status_ops.color = AMBAR
            page.update()
            return

        try:
            ruta_informe = os.path.join(UPLOAD_DIR, "informe_subcadenas_prefijos.txt")
            contenido = OperacionesAvanzadas.generar_reporte_operaciones(resultado_op1_actual)
            with open(ruta_informe, "w", encoding="utf-8") as f:
                f.write(contenido)

            txt_status_ops.value = f"✅ Informe guardado en: {ruta_informe}"
            txt_status_ops.color = VERDE
        except Exception as err:
            txt_status_ops.value = f"❌ Error al guardar archivo: {err}"
            txt_status_ops.color = ROJO
        page.update()

    def ejecutar_cerradura(es_positiva: bool):
        alfabeto = input_alfabeto_cerradura.value or "a, b"
        try:
            n = int(input_longitud_max.value) if input_longitud_max.value else 3
            res = OperacionesAvanzadas.generar_cerraduras(alfabeto, n, es_positiva)

            col_resultado_cerradura.controls = [
                ft.Row(
                    [
                        ficha(f"{res['tipo']}", MORADO),
                        ficha(f"Σ = {res['alfabeto']}", ACENTO),
                        ficha(f"hasta n = {res['longitud_max']}", AMBAR),
                        ficha(f"{res['total']} cadenas generadas", VERDE),
                    ],
                    wrap=True,
                    spacing=8,
                    run_spacing=8,
                ),
                bloque_fichas("Elementos", res["cadenas"], VERDE, res["total"]),
            ]
        except ValueError as err:
            col_resultado_cerradura.controls = [ft.Text(f"❌ {err}", color=ROJO)]
        except Exception as err:
            col_resultado_cerradura.controls = [ft.Text(f"❌ Error inesperado: {err}", color=ROJO)]
        page.update()

    # =========================================================================
    # VISTAS
    # =========================================================================
    def construir_vista(controles):
        return ft.Column(controles, spacing=18, scroll=ft.ScrollMode.AUTO, expand=True, visible=False)

    def fila_botones(*controles):
        return ft.Row(list(controles), spacing=12, wrap=True, run_spacing=12)

    def pareja(*tarjetas):
        return ft.ResponsiveRow(list(tarjetas), spacing=16, run_spacing=16)

    vistas = {
        # ---------------------------------------------------------------- Autómata
        "editor": construir_vista(
            [
                encabezado_vista(
                    "Autómata",
                    "Diagrama, definición formal y tabla de transiciones del autómata cargado.",
                ),
                panel_def.card,
                pareja(
                    tarjeta(
                        [txt_definicion_formal],
                        "Definición formal",
                        icono=ft.icons.FUNCTIONS,
                        col={"xs": 12, "lg": 4},
                    ),
                    tarjeta(
                        [con_scroll_horizontal(data_table_transiciones)],
                        "Tabla de transiciones (δ)",
                        icono=ft.icons.TABLE_CHART,
                        col={"xs": 12, "lg": 8},
                    ),
                ),
            ]
        ),
        # ---------------------------------------------------------------- Archivos
        "archivos": construir_vista(
            [
                encabezado_vista(
                    "Archivos",
                    "Importa autómatas (.jff, .json, .xml) o lotes de cadenas (.txt) y exporta el autómata actual.",
                ),
                pareja(
                    tarjeta(
                        [
                            ft.Text(
                                "Soporta autómatas (.jff, .json, .xml) y lotes de cadenas (.txt).",
                                size=13,
                                color=TENUE,
                            ),
                            fila_botones(
                                boton_primario(
                                    "Cargar autómata o lote .txt",
                                    ft.icons.UPLOAD_FILE,
                                    on_click=lambda _: abrir_dialogo_abrir(),
                                )
                            ),
                        ],
                        "Importar",
                        icono=ft.icons.UPLOAD_FILE,
                        col={"xs": 12, "lg": 6},
                    ),
                    tarjeta(
                        [
                            ft.Text(
                                "Guarda el autómata actual como .json, .jff o .xml.",
                                size=13,
                                color=TENUE,
                            ),
                            fila_botones(
                                boton_secundario(
                                    "Guardar autómata",
                                    ft.icons.SAVE,
                                    on_click=lambda _: abrir_dialogo_guardar(),
                                )
                            ),
                        ],
                        "Exportar",
                        icono=ft.icons.SAVE,
                        col={"xs": 12, "lg": 6},
                    ),
                ),
                tarjeta([txt_status_carga], "Estado"),
            ]
        ),
        # -------------------------------------------------------------- Simulación
        "simulacion": construir_vista(
            [
                encabezado_vista(
                    "Simulación paso a paso",
                    "Escribe una cadena y observa cómo cambian los estados activos símbolo a símbolo.",
                ),
                tarjeta(
                    [
                        fila_botones(
                            input_cadena_simular,
                            boton_primario("Simular", ft.icons.PLAY_ARROW, on_click=ejecutar_simulacion),
                        ),
                        txt_resultado_simulacion,
                    ],
                    "Cadena de entrada",
                    icono=ft.icons.PLAY_ARROW,
                ),
                panel_sim.card,
                tarjeta(
                    [caja_codigo(list_pasos_simulacion)],
                    "Historial de rastreo (clausura-λ)",
                    icono=ft.icons.CHECKLIST,
                ),
            ]
        ),
        # ------------------------------------------------------- 2.1 Cerradura λ
        "cerradura": construir_vista(
            [
                encabezado_vista(
                    "Cerradura λ y simulación directa",
                    "Calcula la cerradura-λ de un estado y simula un AFN-λ sin convertirlo.",
                ),
                panel_cl.card,
                pareja(
                    tarjeta(
                        [
                            fila_botones(
                                dropdown_estado_cerradura,
                                boton_primario(
                                    "Calcular CL(s)",
                                    ft.icons.CALCULATE,
                                    on_click=calcular_cerradura_individual,
                                ),
                            ),
                            txt_resultado_cerradura,
                        ],
                        "Cerradura λ de un estado",
                        icono=ft.icons.CALCULATE,
                        col={"xs": 12, "lg": 5},
                    ),
                    tarjeta(
                        [
                            fila_botones(
                                input_cadena_directa,
                                boton_primario(
                                    "Simular AFN-λ",
                                    ft.icons.PLAY_ARROW,
                                    on_click=ejecutar_simulacion_directa,
                                ),
                            ),
                            txt_resultado_simulacion_directa,
                        ],
                        "Simulación directa de AFN-λ",
                        "Sin conversión previa",
                        icono=ft.icons.PLAY_ARROW,
                        col={"xs": 12, "lg": 7},
                    ),
                ),
                tarjeta(
                    [con_scroll_horizontal(data_table_pasos_directos)],
                    "Pasos de la simulación directa",
                    icono=ft.icons.TABLE_CHART,
                ),
            ]
        ),
        # ------------------------------------------------------- 2.2 AFN-λ → AFN
        "lambda": construir_vista(
            [
                encabezado_vista(
                    "AFN-λ a AFN",
                    "Elimina las transiciones λ y compara el autómata original con el resultado.",
                ),
                tarjeta(
                    [
                        fila_botones(
                            boton_primario(
                                "Convertir a AFN sin λ",
                                ft.icons.TRANSFORM,
                                on_click=ejecutar_eliminacion_lambda,
                            )
                        ),
                        txt_info_conversion_lambda,
                    ],
                    "Conversión",
                    icono=ft.icons.CLEANING_SERVICES,
                ),
                pareja(panel_22_orig.card, panel_22_res.card),
                tarjeta(
                    [caja_codigo(txt_explicacion_paso_a_paso_22)],
                    "Procedimiento detallado",
                    icono=ft.icons.CHECKLIST,
                ),
                tarjeta(
                    [con_scroll_horizontal(data_table_pasos_eliminacion)],
                    "Desglose de transiciones",
                    "δ'(q, a) = CL(δ(CL(q), a))",
                    icono=ft.icons.TABLE_CHART,
                ),
                tarjeta(
                    [con_scroll_horizontal(data_table_afn_sin_lambda)],
                    "Tabla de transiciones resultante (δ')",
                    icono=ft.icons.TABLE_CHART,
                ),
            ]
        ),
        # ----------------------------------------------------------- 2.3 AFN → AFD
        "afd": construir_vista(
            [
                encabezado_vista(
                    "AFN a AFD",
                    "Construcción por subconjuntos: cada estado del AFD agrupa estados del AFN.",
                ),
                tarjeta(
                    [
                        fila_botones(
                            boton_primario(
                                "Convertir a AFD",
                                ft.icons.AUTO_FIX_HIGH,
                                on_click=ejecutar_conversion_afd,
                            )
                        ),
                        txt_info_afd,
                    ],
                    "Conversión",
                    icono=ft.icons.MERGE_TYPE,
                ),
                pareja(panel_23_orig.card, panel_23_res.card),
                tarjeta(
                    [caja_codigo(txt_mapeo_subconjuntos)],
                    "Equivalencia de subconjuntos",
                    icono=ft.icons.CHECKLIST,
                ),
                tarjeta(
                    [con_scroll_horizontal(data_table_afd)],
                    "Tabla de transiciones del AFD resultante",
                    icono=ft.icons.TABLE_CHART,
                ),
            ]
        ),
        # -------------------------------------------------------- 2.4 Minimización
        "minimizar": construir_vista(
            [
                encabezado_vista(
                    "Minimizar AFD",
                    "Algoritmo de partición: une los estados equivalentes del AFD.",
                ),
                tarjeta(
                    [
                        fila_botones(
                            boton_primario(
                                "Minimizar AFD",
                                ft.icons.COMPRESS,
                                on_click=ejecutar_minimizacion_afd,
                            )
                        ),
                        txt_info_minimizacion,
                    ],
                    "Minimización",
                    icono=ft.icons.COMPRESS,
                ),
                pareja(panel_24_orig.card, panel_24_res.card),
                tarjeta(
                    [caja_codigo(txt_particiones_historial)],
                    "Historial de particiones",
                    icono=ft.icons.CHECKLIST,
                ),
                tarjeta(
                    [con_scroll_horizontal(data_table_afd_minimo)],
                    "Tabla de transiciones del AFD mínimo",
                    icono=ft.icons.TABLE_CHART,
                ),
            ]
        ),
        # ------------------------------------------------------ 2.5 Lote de cadenas
        "lote": construir_vista(
            [
                encabezado_vista(
                    "Validación en lote",
                    "Evalúa muchas cadenas de un archivo .txt contra el autómata cargado.",
                ),
                tarjeta(
                    [
                        fila_botones(
                            boton_primario(
                                "Cargar archivo .txt de cadenas",
                                ft.icons.UPLOAD_FILE,
                                on_click=lambda _: abrir_dialogo_lote(),
                            ),
                            btn_guardar_reporte_lote,
                        ),
                        txt_status_lote,
                    ],
                    "Archivo de cadenas",
                    icono=ft.icons.CHECKLIST,
                ),
                tarjeta(
                    [con_scroll_horizontal(data_table_lote)],
                    "Resultados de la evaluación masiva",
                    icono=ft.icons.TABLE_CHART,
                ),
            ]
        ),
        # ----------------------------------------------------------- P4 Thompson
        "thompson": construir_vista(
            [
                encabezado_vista(
                    "Expresión regular a AFN-λ",
                    "Construcción de Thompson. Operadores válidos: |, +, *, paréntesis y punto.",
                ),
                tarjeta(
                    [
                        fila_botones(
                            input_regex,
                            boton_primario(
                                "Construir AFN-λ",
                                ft.icons.AUTO_AWESOME,
                                on_click=ejecutar_construccion_thompson,
                            ),
                            btn_cargar_en_p3,
                        ),
                        txt_status_regex,
                    ],
                    "Expresión regular",
                    icono=ft.icons.CODE,
                ),
                panel_thompson.card,
                tarjeta(
                    [caja_codigo(txt_pasos_thompson)],
                    "Construcción paso a paso",
                    icono=ft.icons.CHECKLIST,
                ),
                tarjeta(
                    [con_scroll_horizontal(data_table_thompson)],
                    "Tabla de transiciones del AFN-λ",
                    icono=ft.icons.TABLE_CHART,
                ),
            ]
        ),
        # ------------------------------------------------------ P4 Autómata → ER
        "a_regex": construir_vista(
            [
                encabezado_vista(
                    "Autómata a expresión regular",
                    "Importa un AFD, verifica su determinismo y obtén la expresión regular por eliminación de estados.",
                ),
                panel_er.card,
                tarjeta(
                    [
                        fila_botones(
                            boton_primario(
                                "Verificar y obtener ER",
                                ft.icons.AUTO_FIX_HIGH,
                                on_click=ejecutar_conversion_a_regex,
                            )
                        ),
                        txt_status_ej3,
                    ],
                    "Verificación",
                    icono=ft.icons.TRANSFORM,
                ),
                tarjeta([caja_codigo(txt_resultado_regex_final)], "Resultado", icono=ft.icons.CODE),
                tarjeta(
                    [caja_codigo(txt_historial_eliminacion)],
                    "Desglose del autómata generalizado",
                    icono=ft.icons.CHECKLIST,
                ),
            ]
        ),
        # ---------------------------------------------------- Operaciones avanzadas
        "operaciones": construir_vista(
            [
                encabezado_vista(
                    "Operaciones avanzadas",
                    "Prefijos, sufijos y subcadenas de una cadena, y cerraduras sobre un alfabeto.",
                ),
                tarjeta(
                    [
                        fila_botones(
                            input_cadena_ops,
                            boton_primario("Calcular", ft.icons.PLAY_ARROW, on_click=ejecutar_operacion_prefijos),
                            boton_secundario(
                                "Guardar reporte (.txt)",
                                ft.icons.SAVE,
                                on_click=guardar_informe_operaciones,
                            ),
                        ),
                        txt_status_ops,
                        col_resultado_ops,
                    ],
                    "Subcadenas, prefijos y sufijos",
                    icono=ft.icons.CALCULATE,
                ),
                tarjeta(
                    [
                        fila_botones(input_alfabeto_cerradura, input_longitud_max),
                        fila_botones(
                            boton_primario(
                                "Calcular Σ* (Kleene)",
                                ft.icons.ALL_INCLUSIVE,
                                on_click=lambda _: ejecutar_cerradura(False),
                            ),
                            boton_secundario(
                                "Calcular Σ⁺ (positiva)",
                                ft.icons.ADD_CIRCLE,
                                on_click=lambda _: ejecutar_cerradura(True),
                            ),
                        ),
                        col_resultado_cerradura,
                    ],
                    "Cerradura de Kleene (Σ*) y cerradura positiva (Σ⁺)",
                    icono=ft.icons.ALL_INCLUSIVE,
                ),
            ]
        ),
    }

    # =========================================================================
    # BARRA SUPERIOR (menú minimalista, al estilo de JFLAP)
    # =========================================================================
    txt_resumen = ft.Text("Sin autómata", size=12, color=TEXTO, weight=ft.FontWeight.W_500)
    punto_resumen = ft.Container(width=8, height=8, border_radius=4, bgcolor=TENUE)

    def ir_a(vista_id):
        nonlocal vista_actual
        vista_actual = vista_id
        for vid, columna in vistas.items():
            columna.visible = vid == vista_id
        resaltar_menu(vista_id)
        sincronizar_paneles()
        page.update()

    MENUS = [
        ("Autómata", "editor"),
        (
            "Archivo",
            [
                ("Abrir autómata o lote…", ft.icons.UPLOAD_FILE, abrir_dialogo_abrir),
                ("Guardar autómata…", ft.icons.SAVE, abrir_dialogo_guardar),
                ("Panel de archivos", ft.icons.FOLDER_OPEN, "archivos"),
            ],
        ),
        (
            "Simular",
            [
                ("Simulación paso a paso", ft.icons.PLAY_ARROW, "simulacion"),
                ("Cerradura λ y simulación directa", ft.icons.ACCOUNT_TREE, "cerradura"),
                ("Validación en lote", ft.icons.CHECKLIST, "lote"),
            ],
        ),
        (
            "Convertir",
            [
                ("AFN-λ a AFN", ft.icons.CLEANING_SERVICES, "lambda"),
                ("AFN a AFD", ft.icons.MERGE_TYPE, "afd"),
                ("Minimizar AFD", ft.icons.COMPRESS, "minimizar"),
            ],
        ),
        (
            "Expresión regular",
            [
                ("ER a AFN-λ (Thompson)", ft.icons.CODE, "thompson"),
                ("Autómata a ER", ft.icons.TRANSFORM, "a_regex"),
            ],
        ),
        ("Herramientas", [("Operaciones avanzadas", ft.icons.CALCULATE, "operaciones")]),
    ]

    refs_menu = {}  # grupo -> (contenedor, texto)
    grupo_de_vista = {}

    def resaltar_menu(vista_id):
        activo = grupo_de_vista.get(vista_id)
        for grupo, (contenedor, texto) in refs_menu.items():
            es_activo = grupo == activo
            contenedor.bgcolor = TARJETA_2 if es_activo else None
            texto.color = TEXTO if es_activo else TENUE

    def crear_elemento_menu(grupo, destino):
        texto = ft.Text(grupo, size=13, weight=ft.FontWeight.W_500, color=TENUE)
        if isinstance(destino, str):  # acceso directo a una vista
            grupo_de_vista[destino] = grupo
            contenedor = ft.Container(
                content=texto,
                padding=ft.padding.symmetric(horizontal=12, vertical=9),
                border_radius=8,
                ink=True,
                on_click=lambda _, v=destino: ir_a(v),
            )
            refs_menu[grupo] = (contenedor, texto)
            return contenedor

        contenedor = ft.Container(
            content=ft.Row(
                [texto, ft.Icon(ft.icons.ARROW_DROP_DOWN, size=18, color=TENUE)],
                spacing=2,
                tight=True,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=9),
            border_radius=8,
        )
        refs_menu[grupo] = (contenedor, texto)

        elementos = []
        for texto_item, icono, accion in destino:
            if isinstance(accion, str):
                grupo_de_vista[accion] = grupo
                al_pulsar = lambda _, v=accion: ir_a(v)
            else:
                al_pulsar = lambda _, f=accion: f()
            elementos.append(ft.PopupMenuItem(text=texto_item, icon=icono, on_click=al_pulsar))
        return ft.PopupMenuButton(content=contenedor, items=elementos)

    elementos_barra = [
        ft.Container(
            content=ft.Icon(ft.icons.HUB, size=18, color="#0b1020"),
            width=30,
            height=30,
            border_radius=9,
            bgcolor=ACENTO,
            alignment=ft.alignment.center,
        ),
        ft.Text("Autómatas", size=15, weight=ft.FontWeight.BOLD, color=TEXTO),
        ft.Container(width=14),
    ]
    for grupo, destino in MENUS:
        elementos_barra.append(crear_elemento_menu(grupo, destino))
    elementos_barra += [
        ft.Container(expand=True),
        ft.Container(
            content=ft.Row([punto_resumen, txt_resumen], spacing=8, tight=True),
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            border_radius=20,
            bgcolor=TARJETA_2,
            border=ft.border.all(1, BORDE),
        ),
        ft.IconButton(
            icon=ft.icons.FOLDER_OPEN,
            icon_size=20,
            icon_color=TENUE,
            tooltip="Abrir autómata o lote",
            on_click=abrir_dialogo_abrir,
        ),
        ft.IconButton(
            icon=ft.icons.SAVE,
            icon_size=20,
            icon_color=TENUE,
            tooltip="Guardar autómata",
            on_click=abrir_dialogo_guardar,
        ),
    ]

    barra_superior = ft.Container(
        content=ft.Row(elementos_barra, spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=58,
        bgcolor=BARRA,
        padding=ft.padding.symmetric(horizontal=18),
        border=ft.border.only(bottom=ft.BorderSide(1, BORDE)),
    )

    zona_contenido = ft.Container(
        content=ft.Column(list(vistas.values()), spacing=0, expand=True),
        expand=True,
        padding=ft.padding.symmetric(horizontal=28, vertical=22),
    )

    vistas["editor"].visible = True
    resaltar_menu("editor")

    page.add(ft.Column([barra_superior, zona_contenido], spacing=0, expand=True))
    actualizar_vistas_definicion()


if __name__ == "__main__":
    ft.app(
        target=main,
        view=ft.AppView.WEB_BROWSER,
        upload_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads")),
        host="0.0.0.0",
        port=8550,
    )