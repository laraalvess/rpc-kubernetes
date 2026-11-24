"""Servidor TCP concurrente (un hilo por conexión) que usa RPCServer."""

from __future__ import annotations

import socket
import threading

from common.protocol import send_json, recv_json
from server import procedures
from server.rpc_server import RPCServer, INVALID_REQUEST

HOST = "0.0.0.0"
PORT = 5000
CLIENT_TIMEOUT = 30.0  # si un cliente conecta y no envía nada, no lo esperamos para siempre


def build_rpc_server() -> RPCServer:
    """Crea el RPCServer y registra todos los procedimientos."""
    rpc = RPCServer()
    rpc.register("sumar", procedures.sumar)
    rpc.register("multiplicar", procedures.multiplicar)
    rpc.register("potencia", procedures.potencia)
    rpc.register("tarea_lenta", procedures.tarea_lenta)
    rpc.register("dividir", procedures.dividir)
    rpc.register("factorial", procedures.factorial)
    rpc.register("es_primo", procedures.es_primo)
    rpc.register("invertir_cadena", procedures.invertir_cadena)
    return rpc


def handle_client(client_socket: socket.socket, address, rpc: RPCServer) -> None:
    """Atiende una conexión: lee una petición, responde y cierra."""
    with client_socket:
        client_socket.settimeout(CLIENT_TIMEOUT)
        print(f"[{threading.current_thread().name}] Conexión desde {address}")
        try:
            try:
                request = recv_json(client_socket)
            except ConnectionError:
                raise  # el cliente se fue; no hay a quién responder
            except (ValueError, UnicodeDecodeError) as exc:
                # JSON mal formado o que no es un objeto
                send_json(client_socket, {
                    "status": "error",
                    "error": INVALID_REQUEST,
                    "message": str(exc),
                })
                return

            print(f"[{threading.current_thread().name}] Petición: {request}")
            response = rpc.dispatch(request)
            send_json(client_socket, response)
        except Exception as exc:
            print(f"Error atendiendo a {address}: {exc}")


def serve(server_socket: socket.socket, rpc: RPCServer) -> None:
    """Bucle principal: acepta conexiones y lanza un hilo por cada una."""
    while True:
        try:
            client_socket, address = server_socket.accept()
        except OSError:
            break  # socket cerrado -> salimos (útil en los tests)
        thread = threading.Thread(
            target=handle_client,
            args=(client_socket, address, rpc),
            daemon=True,
        )
        thread.start()


def create_server_socket(host: str = HOST, port: int = PORT) -> socket.socket:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen()
    return server_socket


def main():
    rpc = build_rpc_server()
    server_socket = create_server_socket()
    print(f"Servidor escuchando en {HOST}:{PORT}")
    try:
        serve(server_socket, rpc)
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server_socket.close()


if __name__ == "__main__":
    main()
