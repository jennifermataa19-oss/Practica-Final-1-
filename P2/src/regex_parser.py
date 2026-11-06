from typing import List, Tuple, Any, Optional


class RegexSyntaxError(Exception):
    def __init__(self, mensaje: str, posicion: int):
        super().__init__(f"Error de sintaxis en la posición {posicion}: {mensaje}")
        self.mensaje = mensaje
        self.posicion = posicion


class RegexNode:
    """Nodo base del Árbol de Sintaxis Abstracta (AST)."""
    pass


class SymbolNode(RegexNode):
    def __init__(self, symbol: str):
        self.symbol = symbol

    def __repr__(self):
        return f"Symbol('{self.symbol}')"


class ConcatNode(RegexNode):
    def __init__(self, left: RegexNode, right: RegexNode):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Concat({self.left}, {self.right})"


class UnionNode(RegexNode):
    def __init__(self, left: RegexNode, right: RegexNode):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Union({self.left}, {self.right})"


class KleeneNode(RegexNode):
    def __init__(self, child: RegexNode):
        self.child = child

    def __repr__(self):
        return f"Kleene({self.child})"


class RegexParser:
    """
    Parser descendente recursivo para expresiones regulares.
    Precedencia de operadores (de menor a mayor):
      1. Unión (| o +)
      2. Concatenación (implícita o .)
      3. Cerradura de Kleene (*)
    """

    OPERADORES = {'*', '|', '+', '.', '(', ')'}

    @staticmethod
    def parse(pattern: str) -> Tuple[RegexNode, str]:
        """
        Analiza una cadena de expresión regular y retorna el AST.
        Lanza RegexSyntaxError indicando la posición exacta si está mal formada.
        """
        if not pattern:
            raise RegexSyntaxError("La expresión regular no puede estar vacía", 0)

        # 1. Insertar puntos de concatenación implícitos
        formatted_pattern, orig_indices = RegexParser._preprocesar_concatenacion(pattern)

        # 2. Tokenización y validación básica de paréntesis
        tokens = list(formatted_pattern)
        pos = 0

        def parse_expr(idx: int) -> Tuple[RegexNode, int]:
            node, next_idx = parse_concat(idx)

            while next_idx < len(tokens) and tokens[next_idx] in ('|', '+'):
                op_idx = next_idx
                next_idx += 1
                if next_idx >= len(tokens):
                    orig_pos = orig_indices[op_idx] if op_idx < len(orig_indices) else len(pattern)
                    raise RegexSyntaxError("Se esperaba un operando después del operador de unión", orig_pos)
                right, next_idx = parse_concat(next_idx)
                node = UnionNode(node, right)

            return node, next_idx

        def parse_concat(idx: int) -> Tuple[RegexNode, int]:
            node, next_idx = parse_star(idx)

            while (next_idx < len(tokens) and 
                   tokens[next_idx] not in ('|', '+', ')') and 
                   tokens[next_idx] != '.'):
                right, next_idx = parse_star(next_idx)
                node = ConcatNode(node, right)

            return node, next_idx

        def parse_star(idx: int) -> Tuple[RegexNode, int]:
            node, next_idx = parse_atom(idx)

            while next_idx < len(tokens) and tokens[next_idx] == '*':
                node = KleeneNode(node)
                next_idx += 1

            return node, next_idx

        def parse_atom(idx: int) -> Tuple[RegexNode, int]:
            if idx >= len(tokens):
                orig_pos = orig_indices[idx - 1] if idx - 1 < len(orig_indices) else len(pattern)
                raise RegexSyntaxError("Expresión incompleta", orig_pos)

            token = tokens[idx]
            orig_pos = orig_indices[idx]

            if token == '*':
                raise RegexSyntaxError("Operador '*' fuera de lugar (sin operando previo)", orig_pos)
            if token in ('|', '+'):
                raise RegexSyntaxError(f"Operador '{token}' fuera de lugar", orig_pos)
            if token == ')':
                raise RegexSyntaxError("Paréntesis de cierre ')' inesperado", orig_pos)

            if token == '(':
                node, next_idx = parse_expr(idx + 1)
                if next_idx >= len(tokens) or tokens[next_idx] != ')':
                    raise RegexSyntaxError("Paréntesis de apertura '(' sin cerrar", orig_pos)
                return node, next_idx + 1

            # Símbolo terminal (letra, dígito, lambda/epsilon)
            return SymbolNode(token), idx + 1

        ast, final_idx = parse_expr(0)
        if final_idx < len(tokens):
            orig_pos = orig_indices[final_idx]
            raise RegexSyntaxError(f"Carácter inesperado '{tokens[final_idx]}'", orig_pos)

        return ast, formatted_pattern

    @staticmethod
    def _preprocesar_concatenacion(pattern: str) -> Tuple[str, List[int]]:
        """Inserta concatenaciones explícitas y mantiene un mapa de índices originales."""
        resultado = []
        indices_originales = []

        for i in range(len(pattern)):
            c1 = pattern[i]
            resultado.append(c1)
            indices_originales.append(i)

            if i + 1 < len(pattern):
                c2 = pattern[i + 1]

                # Condición de concatenación implícita entre c1 y c2
                es_c1_fin = (c1 not in ('|', '+', '('))
                es_c2_inicio = (c2 not in ('|', '+', '*', ')'))

                if es_c1_fin and es_c2_inicio:
                    # Concatenación implícita detectada (no insertamos un caracter visible para mantener limpio el parser)
                    pass

        return "".join(resultado), indices_originales