"""Capa cliente RPC.

Oculta a la aplicación: creación del mensaje, serialización, conexión TCP,
envío/recepción y tratamiento de errores. Para quien la usa, llamar a un
procedimiento remoto es tan simple como `rpc.call("sumar", 4, 7)`.
"""

from __future__ import annotations

import socket
from typing import Any

from common.protocol import send_json, recv_json


class RPCError(Exception):
    """El servidor respondió con status == 'error'."""

    def __init__(self, code: str, message: str | None = None):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}" if message else code)


class RPCConnectionError(Exception):
    """Fallo de comunicación (no se pudo conectar, se cortó la conexión...)."""


class RPCTimeoutError(RPCConnectionError):
    """Se agotó el tiempo de espera."""


class RPCClient:
    def __init__(self, host: str, port: int, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def call(self, function: str, *args: Any) -> Any:
        """Ejecuta un procedimiento remoto y devuelve su resultado."""
        request = {"function": function, "args": list(args)}

        try:
            # create_connection aplica el timeout también a la conexión;
            # además deja ese mismo timeout en el socket para send/recv.
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                send_json(sock, request)
                response = recv_json(sock)
        except socket.timeout as exc:
            raise RPCTimeoutError(
                f"Timeout ({self.timeout}s) llamando a '{function}'."
            ) from exc
        except (OSError, ConnectionError, ValueError) as exc:
            # OSError cubre ConnectionRefusedError, host inalcanzable, DNS...
            # ValueError cubre JSON inválido en la respuesta.
            raise RPCConnectionError(
                f"Fallo de comunicación con {self.host}:{self.port}: {exc}"
            ) from exc

        status = response.get("status")
        if status == "ok":
            return response.get("result")
        if status == "error":
            raise RPCError(response.get("error", "UNKNOWN_ERROR"), response.get("message"))
        raise RPCConnectionError(f"Respuesta con formato inesperado: {response!r}")
