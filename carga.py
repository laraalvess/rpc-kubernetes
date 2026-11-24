import sys
import time
import threading
from client.rpc_client import RPCClient

HOST = sys.argv[1]
PORT = int(sys.argv[2])
HILOS = int(sys.argv[3])
PETICIONES = int(sys.argv[4])

ok = 0
errores = 0
tiempos = []
candado = threading.Lock()


def trabajador():
    global ok, errores
    cliente = RPCClient(HOST, PORT)
    for _ in range(PETICIONES):
        inicio = time.time()
        try:
            correcto = cliente.call('sumar', 4, 7) == 11
        except Exception:
            correcto = False
        duracion = time.time() - inicio
        with candado:
            tiempos.append(duracion)
            if correcto:
                ok += 1
            else:
                errores += 1


inicio_total = time.time()
hilos = [threading.Thread(target=trabajador) for _ in range(HILOS)]
for h in hilos:
    h.start()
for h in hilos:
    h.join()
total = time.time() - inicio_total

print("Hilos:", HILOS, "| Peticiones por hilo:", PETICIONES)
print("Peticiones totales:", ok + errores)
print("Correctas:", ok, "| Errores:", errores)
print("Tiempo total: %.2f s" % total)
print("Peticiones por segundo: %.1f" % ((ok + errores) / total))
print("Tiempo medio por peticion: %.4f s" % (sum(tiempos) / len(tiempos)))
print("Tiempo maximo: %.4f s" % max(tiempos))
