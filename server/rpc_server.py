"""Servidor RPC: registro de procedimientos y dispatcher.

Esta clase NO sabe nada de sockets: recibe un diccionario (la petición)
y devuelve otro diccionario (la respuesta). Así la lógica RPC queda
separada de la comunicación y se puede probar sin red.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

# Códigos de error que puede devolver el servidor.
INVALID_REQUEST = "INVALID_REQUEST"
PROCEDURE_NOT_FOUND = "PROCEDURE_NOT_FOUND"
INVALID_ARGUMENTS = "INVALID_ARGUMENTS"
EXECUTION_ERROR = "EXECUTION_ERROR"


def _error(code: str, message: str | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {"status": "error", "error": code}
    if message:
        response["message"] = message
    return response


class RPCServer:
    def __init__(self):
        self._procedures: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, function: Callable[..., Any]) -> None:
        """Registra un procedimiento remoto con el nombre `name`."""
        if not isinstance(name, str) or not name:
            raise ValueError("El nombre del procedimiento debe ser un string no vacío.")
        if not callable(function):
            raise TypeError("El procedimiento debe ser invocable.")
        if name in self._procedures:
            raise ValueError(f"El procedimiento '{name}' ya está registrado.")
        self._procedures[name] = function

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        """Procesa una petición RPC y construye la respuesta."""
        # 1. Validar formato de la petición
        if not isinstance(request, dict):
            return _error(INVALID_REQUEST, "La petición debe ser un objeto JSON.")

        name = request.get("function")
        args = request.get("args", [])

        if not isinstance(name, str) or not name:
            return _error(INVALID_REQUEST, "Falta el campo 'function' (string).")
        if not isinstance(args, list):
            return _error(INVALID_REQUEST, "El campo 'args' debe ser una lista.")

        # 2. Buscar el procedimiento
        procedure = self._procedures.get(name)
        if procedure is None:
            return _error(PROCEDURE_NOT_FOUND, f"No existe el procedimiento '{name}'.")

        # 3. Comprobar que los argumentos encajan con la firma
        #    (así distinguimos "argumentos mal" de "la función petó por dentro")
        try:
            inspect.signature(procedure).bind(*args)
        except TypeError as exc:
            return _error(INVALID_ARGUMENTS, str(exc))

        # 4. Ejecutar
        try:
            result = procedure(*args)
        except Exception as exc:  # cualquier fallo del procedimiento
            return _error(EXECUTION_ERROR, f"{type(exc).__name__}: {exc}")

        # 5. El resultado debe poder viajar como JSON
        try:
            import json
            json.dumps(result)
        except (TypeError, ValueError):
            return _error(EXECUTION_ERROR, "El resultado no es serializable a JSON.")

        return {"status": "ok", "result": result}
