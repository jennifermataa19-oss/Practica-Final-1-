# src/lenguajes.py
import itertools

def obtener_prefijos(cadena: str) -> list[str]:
    """Calcula todos los prefijos de una cadena, incluyendo la cadena vacía."""
    return [cadena[:i] for i in range(len(cadena) + 1)]

def obtener_sufijos(cadena: str) -> list[str]:
    """Calcula todos los sufijos de una cadena, incluyendo la cadena vacía."""
    return [cadena[i:] for i in range(len(cadena) + 1)]

def obtener_subcadenas(cadena: str) -> list[str]:
    """Calcula todas las subcadenas distintas de una cadena."""
    subcadenas = {""}
    n = len(cadena)
    for i in range(n):
        for j in range(i + 1, n + 1):
            subcadenas.add(cadena[i:j])
    return sorted(list(subcadenas), key=lambda x: (len(x), x))

def generar_cerradura_kleene(alfabeto: set[str], n_max: int) -> list[str]:
    """Genera la cerradura de Kleene (Sigma*) hasta la longitud n_max."""
    # Validación del límite de 200,000 cadenas (Operación 2)
    k = len(alfabeto)
    total_estimado = sum(k**i for i in range(n_max + 1)) if k > 0 else 1
    if total_estimado > 200000:
        raise ValueError(f"Rechazado: La combinación de |Σ|={k} y n={n_max} generaría {total_estimado:,} cadenas (Límite: 200,000).")

    cadenas = []
    for i in range(n_max + 1):
        for p in itertools.product(sorted(list(alfabeto)), repeat=i):
            cadenas.append("".join(p))
    return cadenas

def generar_cerradura_positiva(alfabeto: set[str], n_max: int) -> list[str]:
    """Genera la cerradura positiva (Sigma+) hasta la longitud n_max."""
    cadenas_kleene = generar_cerradura_kleene(alfabeto, n_max)
    return [w for w in cadenas_kleene if w != ""]