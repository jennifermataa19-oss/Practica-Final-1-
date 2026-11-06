from typing import Dict, Set, Tuple, List, Any
from automata import Automata
from regex_parser import (
    RegexNode, SymbolNode, ConcatNode, UnionNode, KleeneNode, RegexParser
)


class SubAutomata:
    """Estructura intermedia para representar fragmentos de autómatas de Thompson."""
    def __init__(self, estado_inicial: str, estado_final: str, transiciones: Dict[Tuple[str, str], Set[str]], alfabeto: Set[str]):
        self.estado_inicial = estado_inicial
        self.estado_final = estado_final
        self.transiciones = transiciones
        self.alfabeto = alfabeto


class ConstructorThompson:
    """Módulo para convertir un AST de expresión regular a AFN-λ paso a paso."""

    def __init__(self):
        self.contador_estados = 0

    def _nuevo_estado(self) -> str:
        nombre = f"q{self.contador_estados}"
        self.contador_estados += 1
        return nombre

    def construir(self, ast: RegexNode) -> Tuple[Automata, List[Dict[str, Any]]]:
        """
        Genera el AFN-λ completo a partir del AST de una ER y registra los pasos intermedios.
        """
        self.contador_estados = 0
        pasos_historial = []

        sub_afn = self._evaluar_nodo(ast, pasos_historial)

        estados = {f"q{i}" for i in range(self.contador_estados)}
        
        afn_lambda = Automata(
            estados=estados,
            alfabeto=sub_afn.alfabeto,
            estado_inicial=sub_afn.estado_inicial,
            estados_aceptacion={sub_afn.estado_final},
            transiciones=sub_afn.transiciones
        )

        return afn_lambda, pasos_historial

    def _evaluar_nodo(self, nodo: RegexNode, historial: List[Dict[str, Any]]) -> SubAutomata:
        # 1. Caso Base: Símbolo o Lambda
        if isinstance(nodo, SymbolNode):
            q_in = self._nuevo_estado()
            q_out = self._nuevo_estado()
            simbolo = nodo.symbol

            alfabeto = set() if simbolo in ("λ", "ε", "lambda", "") else {simbolo}
            simbolo_trans = "λ" if simbolo in ("λ", "ε", "lambda", "") else simbolo
            trans = {(q_in, simbolo_trans): {q_out}}

            sub = SubAutomata(q_in, q_out, trans, alfabeto)
            historial.append({
                "tipo": "base",
                "operacion": f"Base: '{simbolo}'",
                "estado_inicial": q_in,
                "estado_final": q_out,
                "transiciones": trans
            })
            return sub

        # 2. Operación de Concatenación (A . B)
        elif isinstance(nodo, ConcatNode):
            sub_izq = self._evaluar_nodo(nodo.left, historial)
            sub_der = self._evaluar_nodo(nodo.right, historial)

            nuevas_trans = {}
            for k, v in sub_izq.transiciones.items():
                nuevas_trans[k] = set(v)
            for k, v in sub_der.transiciones.items():
                nuevas_trans[k] = set(v)

            # Transición lambda del final de A al inicial de B
            clave_lambda = (sub_izq.estado_final, "λ")
            nuevas_trans[clave_lambda] = nuevas_trans.get(clave_lambda, set()).union({sub_der.estado_inicial})

            alfabeto = sub_izq.alfabeto.union(sub_der.alfabeto)
            sub = SubAutomata(sub_izq.estado_inicial, sub_der.estado_final, nuevas_trans, alfabeto)

            historial.append({
                "tipo": "concatenacion",
                "operacion": f"Concatenación ({sub_izq.estado_inicial}..{sub_izq.estado_final} · {sub_der.estado_inicial}..{sub_der.estado_final})",
                "estado_inicial": sub.estado_inicial,
                "estado_final": sub.estado_final,
                "transiciones": nuevas_trans
            })
            return sub

        # 3. Operación de Unión (A | B)
        elif isinstance(nodo, UnionNode):
            sub_izq = self._evaluar_nodo(nodo.left, historial)
            sub_der = self._evaluar_nodo(nodo.right, historial)

            q_in = self._nuevo_estado()
            q_out = self._nuevo_estado()

            nuevas_trans = {}
            for k, v in sub_izq.transiciones.items():
                nuevas_trans[k] = set(v)
            for k, v in sub_der.transiciones.items():
                nuevas_trans[k] = set(v)

            # Lambda de q_in a los iniciales de A y B
            nuevas_trans[(q_in, "λ")] = {sub_izq.estado_inicial, sub_der.estado_inicial}

            # Lambda de los finales de A y B a q_out
            nuevas_trans[(sub_izq.estado_final, "λ")] = nuevas_trans.get((sub_izq.estado_final, "λ"), set()).union({q_out})
            nuevas_trans[(sub_der.estado_final, "λ")] = nuevas_trans.get((sub_der.estado_final, "λ"), set()).union({q_out})

            alfabeto = sub_izq.alfabeto.union(sub_der.alfabeto)
            sub = SubAutomata(q_in, q_out, nuevas_trans, alfabeto)

            historial.append({
                "tipo": "union",
                "operacion": "Unión ( | )",
                "estado_inicial": q_in,
                "estado_final": q_out,
                "transiciones": nuevas_trans
            })
            return sub

        # 4. Operación de Cerradura de Kleene (A*)
        elif isinstance(nodo, KleeneNode):
            sub_hijo = self._evaluar_nodo(nodo.child, historial)

            q_in = self._nuevo_estado()
            q_out = self._nuevo_estado()

            nuevas_trans = {}
            for k, v in sub_hijo.transiciones.items():
                nuevas_trans[k] = set(v)

            # Transiciones lambda de Kleene
            nuevas_trans[(q_in, "λ")] = {sub_hijo.estado_inicial, q_out}
            nuevas_trans[(sub_hijo.estado_final, "λ")] = nuevas_trans.get((sub_hijo.estado_final, "λ"), set()).union({sub_hijo.estado_inicial, q_out})

            sub = SubAutomata(q_in, q_out, nuevas_trans, sub_hijo.alfabeto)

            historial.append({
                "tipo": "kleene",
                "operacion": "Cerradura de Kleene (*)",
                "estado_inicial": q_in,
                "estado_final": q_out,
                "transiciones": nuevas_trans
            })
            return sub

        else:
            raise ValueError("Tipo de nodo AST no reconocido")