"""Procedimientos remotos de ejemplo proporcionados."""

from __future__ import annotations
import time


def sumar(a, b):
    return a + b


def multiplicar(a, b):
    return a * b


def potencia(a, b):
    return a ** b


def tarea_lenta(segundos):
    """Útil para comprobar posteriormente la concurrencia."""
    time.sleep(segundos)
    return segundos



# ---------------------------------------------------------------------------
# Procedimientos adicionales (aportados por el alumno)
# ---------------------------------------------------------------------------

def dividir(a, b):
    """División real. Si b == 0 lanza ZeroDivisionError (-> EXECUTION_ERROR)."""
    return a / b


def factorial(n):
    """Factorial de un entero >= 0."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        raise ValueError("n debe ser un entero >= 0")
    resultado = 1
    for i in range(2, n + 1):
        resultado *= i
    return resultado


def es_primo(n):
    """Devuelve True si n es primo."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise ValueError("n debe ser un entero")
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True


def invertir_cadena(texto):
    """Devuelve el texto al revés."""
    if not isinstance(texto, str):
        raise ValueError("texto debe ser un string")
    return texto[::-1]
