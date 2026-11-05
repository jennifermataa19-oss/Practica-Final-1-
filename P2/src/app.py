import flet as ft
from lenguajes import (
    obtener_prefijos, obtener_sufijos, obtener_subcadenas,
    generar_cerradura_kleene, generar_cerradura_positiva
)

def main(page: ft.Page):
    page.title = "Operaciones sobre Lenguajes y Autómatas"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 15
    page.scroll = ft.ScrollMode.AUTO

    # Entradas Izquierda
    txt_alfabeto = ft.TextField(label="Ingrese el alfabeto separado por comas (ej: a,b,c)", value="a,b,c", width=340, dense=True)
    txt_nmax = ft.TextField(label="Ingrese el número máximo de combinaciones", value="3", width=340, dense=True)
    txt_l1 = ft.TextField(label="Ingrese las cadenas del primer lenguaje separadas por comas", value="ba,aaaaaaaaa,baa,b,ccc,aa", width=340, dense=True)
    txt_l2 = ft.TextField(label="Ingrese las cadenas del segundo lenguaje separadas por comas", value="aa,bababa,aaa,baaa,ccc,aaaaababa,bbbbbb", width=340, dense=True)
    txt_pot_l = ft.TextField(label="Ingrese la potencia del lenguaje", value="3", width=340, dense=True)

    # Autómata Derecha
    txt_estados = ft.TextField(label="Ingrese los estados separados por comas (ej: 0,1,2)", value="0,1,2,3,4,5", width=340, dense=True)
    txt_est_init = ft.TextField(label="Ingrese el estado inicial", value="0", width=340, dense=True)
    txt_est_acept = ft.TextField(label="Ingrese los estados de aceptación separados por comas (ej: 2,3)", value="4", width=340, dense=True)

    # Transiciones
    t0_a = ft.TextField(label="0: a ->", value="5", width=95, dense=True)
    t0_b = ft.TextField(label="0: b ->", value="2", width=95, dense=True)
    t0_c = ft.TextField(label="0: c ->", value="5", width=95, dense=True)

    t4_a = ft.TextField(label="4: a ->", value="5", width=95, dense=True)
    t4_b = ft.TextField(label="4: b ->", value="5", width=95, dense=True)
    t4_c = ft.TextField(label="4: c ->", value="5", width=95, dense=True)

    t5_a = ft.TextField(label="5: a ->", value="5", width=95, dense=True)
    t5_b = ft.TextField(label="5: b ->", value="5", width=95, dense=True)
    t5_c = ft.TextField(label="5: c ->", value="5", width=95, dense=True)

    txt_cad_validar = ft.TextField(label="Ingrese la cadena a validar", value="abbbacbcbcbcba", width=340, dense=True)
    txt_resultado = ft.Text(value="", size=13, color="greenAccent", selectable=True)

    def op_kleene(e):
        alf = {x.strip() for x in txt_alfabeto.value.split(",") if x.strip()}
        try:
            res = generar_cerradura_kleene(alf, int(txt_nmax.value or 0))
            txt_resultado.value = f"Cerradura de Kleene: {res}"
        except Exception as err:
            txt_resultado.value = f"Error: {str(err)}"
        page.update()

    def op_positiva(e):
        alf = {x.strip() for x in txt_alfabeto.value.split(",") if x.strip()}
        try:
            res = generar_cerradura_positiva(alf, int(txt_nmax.value or 0))
            txt_resultado.value = f"Clausura Positiva: {res}"
        except Exception as err:
            txt_resultado.value = f"Error: {str(err)}"
        page.update()

    def op_concat_l(e):
        l1 = {x.strip() for x in txt_l1.value.split(",") if x.strip()}
        l2 = {x.strip() for x in txt_l2.value.split(",") if x.strip()}
        res = sorted(list({u + v for u in l1 for v in l2}))
        txt_resultado.value = f"Concatenar lenguajes: {res}"
        page.update()

    def op_potencia_l(e):
        l1 = {x.strip() for x in txt_l1.value.split(",") if x.strip()}
        k = int(txt_pot_l.value or 1)
        res = l1.copy()
        for _ in range(k - 1):
            res = {u + v for u in res for v in l1}
        txt_resultado.value = f"Potenciar lenguaje (L1^{k}): {sorted(list(res))}"
        page.update()

    def op_reflexion_l(e):
        l1 = {x.strip() for x in txt_l1.value.split(",") if x.strip()}
        res = sorted(list({w[::-1] for w in l1}))
        txt_resultado.value = f"Reflexión del lenguaje (L1^R): {res}"
        page.update()

    def op_union_l(e):
        l1 = {x.strip() for x in txt_l1.value.split(",") if x.strip()}
        l2 = {x.strip() for x in txt_l2.value.split(",") if x.strip()}
        txt_resultado.value = f"Unión de lenguajes: {sorted(list(l1.union(l2)))}"
        page.update()

    def op_inter_l(e):
        l1 = {x.strip() for x in txt_l1.value.split(",") if x.strip()}
        l2 = {x.strip() for x in txt_l2.value.split(",") if x.strip()}
        txt_resultado.value = f"Intersección de lenguajes: {sorted(list(l1.intersection(l2)))}"
        page.update()

    def op_dif_l(e):
        l1 = {x.strip() for x in txt_l1.value.split(",") if x.strip()}
        l2 = {x.strip() for x in txt_l2.value.split(",") if x.strip()}
        txt_resultado.value = f"Diferencia de lenguajes: {sorted(list(l1.difference(l2)))}"
        page.update()

    def validar_cadena_af(e):
        estado_actual = txt_est_init.value.strip()
        aceptacion = {x.strip() for x in txt_est_acept.value.split(",") if x.strip()}
        cadena = txt_cad_validar.value.strip()

        trans = {
            "0": {"a": t0_a.value.strip(), "b": t0_b.value.strip(), "c": t0_c.value.strip()},
            "4": {"a": t4_a.value.strip(), "b": t4_b.value.strip(), "c": t4_c.value.strip()},
            "5": {"a": t5_a.value.strip(), "b": t5_b.value.strip(), "c": t5_c.value.strip()}
        }

        for sim in cadena:
            if estado_actual in trans and sim in trans[estado_actual]:
                estado_actual = trans[estado_actual][sim]
            else:
                estado_actual = "5"

        valida = estado_actual in aceptacion
        txt_resultado.value = f"Validación de Cadena '{cadena}': {'ACEPTADA' if valida else 'RECHAZADA (Termina en estado ' + estado_actual + ')'}"
        page.update()

    col_botones = ft.Column([
        ft.ElevatedButton("Cerradura de Kleene", on_click=op_kleene, width=200),
        ft.ElevatedButton("Clausura Positiva", on_click=op_positiva, width=200),
        ft.ElevatedButton("Concatenar lenguajes", on_click=op_concat_l, width=200),
        ft.ElevatedButton("Potenciar lenguaje", on_click=op_potencia_l, width=200),
        ft.ElevatedButton("Reflexión del lenguaje", on_click=op_reflexion_l, width=200),
        ft.ElevatedButton("Unión de lenguajes", on_click=op_union_l, width=200),
        ft.ElevatedButton("Intersección de lenguajes", on_click=op_inter_l, width=200),
        ft.ElevatedButton("Diferencia de lenguajes", on_click=op_dif_l, width=200),
        ft.ElevatedButton("Definir Autómata", on_click=validar_cadena_af, width=200),
    ], spacing=6, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    col_izquierda = ft.Column([txt_alfabeto, txt_nmax, txt_l1, txt_l2, txt_pot_l], spacing=10)

    col_derecha = ft.Column([
        txt_estados, txt_est_init, txt_est_acept,
        ft.Text("Definir Transiciones", weight=ft.FontWeight.BOLD),
        ft.Row([t0_a, t0_b, t0_c], spacing=5),
        ft.Row([t4_a, t4_b, t4_c], spacing=5),
        ft.Row([t5_a, t5_b, t5_c], spacing=5),
        txt_cad_validar,
        ft.Container(height=5),
        ft.ElevatedButton("Validar Cadena", on_click=validar_cadena_af, width=200)
    ], spacing=6)

    page.add(
        ft.Row([col_izquierda, col_botones, col_derecha], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START),
        ft.Divider(),
        txt_resultado
    )

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550, host="0.0.0.0")