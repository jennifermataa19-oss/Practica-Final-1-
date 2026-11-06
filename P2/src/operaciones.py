class OperacionesLenguaje:
    @staticmethod
    def obtener_prefijos(cadena):
        """Devuelve el conjunto de todos los prefijos de una cadena."""
        return {cadena[:i] for i in range(len(cadena) + 1)}

    @staticmethod
    def obtener_sufijos(cadena):
        """Devuelve el conjunto de todos los sufijos de una cadena."""
        return {cadena[i:] for i in range(len(cadena) + 1)}

    @staticmethod
    def obtener_subcadenas(cadena):
        """Devuelve el conjunto de todas las subcadenas posibles."""
        subcadenas = set()
        n = len(cadena)
        for i in range(n + 1):
            for j in range(i, n + 1):
                subcadenas.add(cadena[i:j])
        return subcadenas

    @staticmethod
    def cerradura_kleene(lenguaje, n=3):
        """
        Genera una aproximación de la Cerradura de Kleene L* hasta longitud n combinaciones.
        Incluye la cadena vacía 'λ'.
        """
        resultado = {'λ'}
        actual = set(lenguaje) - {'λ', ''}
        
        for _ in range(1, n + 1):
            resultado.update(actual)
            siguiente = set()
            for w1 in actual:
                for w2 in lenguaje:
                    if w2 != 'λ' and w2 != '':
                        siguiente.add(w1 + w2)
            actual = siguiente

        return sorted(list(resultado), key=lambda x: (len(x), x))

    @staticmethod
    def cerradura_positiva(lenguaje, n=3):
        """
        Genera una aproximación de la Cerradura Positiva L+ (L* sin λ salvo si λ estaba en L).
        """
        kleene = set(OperacionesLenguaje.cerradura_kleene(lenguaje, n))
        if 'λ' not in lenguaje and '' not in lenguaje:
            kleene.discard('λ')
        return sorted(list(kleene), key=lambda x: (len(x), x))