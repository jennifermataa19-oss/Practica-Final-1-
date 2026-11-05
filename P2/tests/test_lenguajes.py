# tests/test_lenguajes.py
import sys
import os
import pytest

# Agregar el directorio raíz al path de Python para que encuentre 'src'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lenguajes import (
    obtener_prefijos, obtener_sufijos, obtener_subcadenas,
    generar_cerradura_kleene, generar_cerradura_positiva
)

def test_cadena_vacia():
    """Prueba el comportamiento con la cadena vacía (lambda)."""
    assert obtener_prefijos("") == [""]
    assert obtener_sufijos("") == [""]
    assert obtener_subcadenas("") == [""]

def test_alfabeto_un_solo_simbolo():
    """Prueba cerraduras de Kleene y positiva con un alfabeto de un solo símbolo."""
    alfabeto = {"a"}
    assert generar_cerradura_kleene(alfabeto, 2) == ["", "a", "aa"]
    assert generar_cerradura_positiva(alfabeto, 2) == ["a", "aa"]

def test_prefijos_y_sufijos_longitud_1():
    """Prueba prefijos y sufijos de una cadena de longitud 1."""
    cadena = "x"
    assert obtener_prefijos(cadena) == ["", "x"]
    assert obtener_sufijos(cadena) == ["x", ""] 

def test_diferencia_kleene_y_positiva_longitud_cero():
    """Prueba que la diferencia entre Sigma* y Sigma+ para n=0 es exactamente {lambda}."""
    alfabeto = {"a", "b"}
    kleene_0 = set(generar_cerradura_kleene(alfabeto, 0))
    positiva_0 = set(generar_cerradura_positiva(alfabeto, 0))
    
    diferencia = kleene_0 - positiva_0
    assert diferencia == {""}

def test_limite_cadenas_excedido():
    """Verifica que rechace combinaciones que superen las 200,000 cadenas."""
    alfabeto = {"a", "b", "c"}
    with pytest.raises(ValueError):
        generar_cerradura_kleene(alfabeto, 15)