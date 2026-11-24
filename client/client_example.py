"""Cliente de ejemplo que usa RPCClient."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from client.rpc_client import RPCClient, RPCError, RPCConnectionError

HOST = "IP_PUBLICA_EC2"  # Sustituir por IP/DNS público de EC2 al desplegar
PORT = 5000


def main():
    rpc = RPCClient(HOST, PORT, timeout=5.0)

    try:
        print("sumar(4, 7)        =", rpc.call("sumar", 4, 7))
        print("multiplicar(3, 5)  =", rpc.call("multiplicar", 3, 5))
        print("potencia(2, 10)    =", rpc.call("potencia", 2, 10))
        print("factorial(10)      =", rpc.call("factorial", 10))
        print("es_primo(97)       =", rpc.call("es_primo", 97))
        print("invertir_cadena    =", rpc.call("invertir_cadena", "hola"))
        print("tarea_lenta(2)     =", rpc.call("tarea_lenta", 2))
    except RPCConnectionError as exc:
        print("Error de comunicación:", exc)
        return

    # Errores controlados
    for function, args in [("no_existe", ()), ("sumar", (1,)), ("dividir", (1, 0))]:
        try:
            rpc.call(function, *args)
        except RPCError as exc:
            print(f"{function}{args} -> {exc}")

    # Prueba de concurrencia: 3 tareas_lentas(2) en paralelo.
    # Con servidor secuencial tardaría ~6 s; con servidor concurrente ~2 s.
    start = time.time()
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda _: rpc.call("tarea_lenta", 2), range(3)))
    print(f"3 x tarea_lenta(2) en paralelo: {time.time() - start:.1f} s")


if __name__ == "__main__":
    main()
