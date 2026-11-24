# Documentación completa – Práctica 2: servidor RPC en Kubernetes

Sistemas Distribuidos · Autor/a: [nombre] · Docker Hub: `laraalvesss/rpc-server:1.0`

Se despliega el servidor RPC de la Práctica 1 (Python, TCP + JSON) en un **clúster Kubernetes de 3 nodos creado desde cero sobre EC2**, expuesto con un Service NodePort. Se comprueba el balanceo, el escalado, la autorreparación y el comportamiento bajo carga. El cliente de la Práctica 1 no se ha modificado.

## Contenido del repositorio

```
Archivos/
├── client/        rpc_client.py, client_example.py   (cliente de la Práctica 1)
├── common/        protocol.py                        (framing: 4 bytes + JSON UTF-8)
├── server/        server.py, rpc_server.py, procedures.py
├── Dockerfile
├── deployment.yaml      Deployment rpc-server (3 réplicas)
├── service.yaml         Service rpc-service (NodePort 30007)
└── carga.py             Generador de carga
evidencias/        Capturas numeradas (01–30)
resultados/        resultados_carga.csv y gráficas
README.md          Memoria resumida (3–5 páginas)
DOCUMENTACION_COMPLETA.md/.pdf   Este documento
```

## Infraestructura

| Nodo | Rol | IP privada |
|---|---|---|
| `k8s-control` | control-plane | 172.31.28.241 |
| `k8s-worker1.2` | worker | 172.31.22.26 |
| `k8s-worker2.2` | worker | 172.31.17.211 |

Tres instancias EC2 (us-east-1) con Ubuntu 26.04.1 LTS, disco de 28 GB (`df -h /` muestra 27 GB), Kubernetes v1.35.10, `containerd 2.2.2` y red de pods flannel.

![Sistema operativo y cgroup v2 del nodo](evidencias/01_so_ubuntu_cgroup.png)

## Diseño del sistema RPC

**Protocolo (`common/protocol.py`).** TCP con mensajes JSON en UTF-8 precedidos de una cabecera de 4 bytes (entero sin signo, orden de red) con la longitud. `_recv_exact` lee exactamente `n` bytes, lo que evita los problemas de fragmentación de TCP.

- Petición: `{"function": "sumar", "args": [4, 7]}`
- Respuesta correcta: `{"status": "ok", "result": 11}`
- Respuesta de error: `{"status": "error", "error": "CÓDIGO", "message": "..."}`

**Servidor.**
- `server/rpc_server.py`: clase `RPCServer` con registro explícito de procedimientos y un *dispatcher* que no conoce los sockets. Valida la petición, comprueba los argumentos con `inspect.signature(...).bind`, ejecuta y comprueba que el resultado sea serializable a JSON. Códigos de error: `INVALID_REQUEST`, `PROCEDURE_NOT_FOUND`, `INVALID_ARGUMENTS` y `EXECUTION_ERROR`.
- `server/server.py`: escucha en `0.0.0.0:5000`, atiende **cada conexión en un hilo** (`threading.Thread`, daemon) y aplica un timeout de 30 s a los clientes que conectan y no envían nada.
- `server/procedures.py`: `sumar`, `multiplicar`, `potencia`, `tarea_lenta`, `dividir`, `factorial`, `es_primo` e `invertir_cadena`.

**Cliente (`client/rpc_client.py`).** `RPCClient(host, puerto, timeout=5.0).call("función", *args)` abre una conexión por llamada y distingue `RPCError` (error devuelto por el servidor), `RPCConnectionError` y `RPCTimeoutError`. El cliente no se modifica respecto a la Práctica 1.

**Generador de carga (`carga.py`).** Un hilo por cliente simulado; cada hilo crea un `RPCClient` y hace `PETICIONES` llamadas a `sumar(4, 7)` comprobando que el resultado es 11. Los contadores se protegen con un `Lock`.

## 1. Creación del clúster

En el nodo de control se usan los scripts del profesor (`kub_install.sh`, `kub_reset.sh`):

```bash
mkdir -p ~/scripts_kubernetes && ls -l ~/scripts_kubernetes
```

![Scripts de instalación](evidencias/02_scripts_kubernetes.png)

El instalador deja el plano de control listo e imprime el comando `kubeadm join` para los workers.

![Instalación del control plane](evidencias/03_instalacion_control_plane.png)

```bash
kubectl get nodes -o wide
kubectl get pods -A
```

![Control plane Ready y pods del sistema](evidencias/04_control_plane_pods.png)

![Un solo nodo al terminar la instalación](evidencias/05_get_nodes_1_nodo.png)

En cada worker se comprueba que `net.ipv4.ip_forward = 1`, que `containerd` está activo y se anota el hostname y el `machine-id` (distintos en cada máquina):

```bash
sysctl net.ipv4.ip_forward
sudo systemctl is-active containerd
hostname; cat /etc/machine-id
```

![Preparación de los tres nodos](evidencias/06_preparacion_workers.png)

Unión de los workers al clúster:

```bash
sudo kubeadm join 172.31.28.241:6443 --token <TOKEN> --discovery-token-ca-cert-hash sha256:<HASH>
```

![kubeadm join en worker1 y worker2](evidencias/07_kubeadm_join_workers.png)

Resultado: tres nodos `Ready` y un pod de flannel y de kube-proxy por nodo.

![Clúster de 3 nodos](evidencias/08_cluster_3_nodos_pods.png)

![Clúster estable tras unos minutos](evidencias/09_cluster_estable.png)

## 2. Dockerización

`Archivos/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY common/ common/
COPY server/ server/
EXPOSE 5000
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "server.server"]
```

El servidor escucha en `0.0.0.0:5000` y atiende cada conexión en un hilo. Se comprueba que el código no tiene la IP ni el puerto fijados a `127.0.0.1`:

```bash
grep -n "bind\|0.0.0.0\|127.0.0.1\|localhost\|5000\|argv\|environ" server/server.py server/rpc_server.py
```

![Estructura de rpc-app, Dockerfile y comprobación del bind](evidencias/10_rpc_app_dockerfile.png)

```bash
sudo docker build -t laraalvesss/rpc-server:1.0 .
sudo docker images
```

![Construcción de la imagen (≈43 MB de contenido)](evidencias/11_docker_build_images.png)

## 3. Prueba local del contenedor

```bash
sudo docker run -d --name rpc-test -p 5000:5000 laraalvesss/rpc-server:1.0
sudo docker ps
python3 -c "from client.rpc_client import RPCClient; print(RPCClient('127.0.0.1', 5000).call('sumar', 4, 7))"   # 11
sudo docker logs rpc-test
```

![Contenedor en marcha, llamada correcta (11) y log de la petición](evidencias/12_docker_run_test_local.png)

## 4. Publicación de la imagen

Los nodos descargan la imagen sin autenticarse, por lo que el repositorio es público.

```bash
sudo docker login
sudo docker push laraalvesss/rpc-server:1.0
```

![Login y push a Docker Hub](evidencias/13_docker_login_push.png)

![Repositorio en Docker Hub](evidencias/14_dockerhub_repositorios.png)

![Tag 1.0 publicado](evidencias/15_dockerhub_tag_1_0.png)

## 5. Despliegue en Kubernetes

Manifiestos (`deployment.yaml` y `service.yaml`): 3 réplicas con la etiqueta `app=rpc-server` y un Service NodePort que publica el puerto 5000 del pod en el 30007 de todos los nodos.

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl rollout status deployment/rpc-server
kubectl get pods -o wide
kubectl get svc rpc-service
```

![Aplicación de los manifiestos: 3 pods Running repartidos entre workers y servicio NodePort 5000:30007](evidencias/16_apply_deployment_service.png)

## 6. Acceso desde el cliente

Desde el control plane, contra la IP de cada worker y el NodePort:

```bash
python3 -c "from client.rpc_client import RPCClient; print(RPCClient('172.31.22.26', 30007).call('sumar', 4, 7))"
python3 -c "from client.rpc_client import RPCClient; print(RPCClient('172.31.17.211', 30007).call('sumar', 4, 7))"
kubectl logs -l app=rpc-server --tail=5 --prefix
```

![Respuesta 11 desde ambos workers y logs de los pods](evidencias/17_prueba_nodeport_logs.png)

Desde un PC externo (Windows, Python 3.14.7) contra la IP pública del nodo; requiere abrir el puerto 30007/TCP en el grupo de seguridad:

```powershell
python -c "from client.rpc_client import RPCClient; print(RPCClient('IP_PUBLICA_EC2', 30007).call('sumar', 4, 7))"
```

![Llamada desde fuera de AWS](evidencias/18_prueba_cliente_externo_windows.png)

## 7. Escalado y balanceo

```bash
kubectl scale deployment rpc-server --replicas=6
kubectl rollout status deployment/rpc-server
kubectl get pods -l app=rpc-server -o wide
```

![Escalado a 6 réplicas](evidencias/19_scale_6_replicas.png)

Diez llamadas seguidas; los logs muestran que las atienden pods distintos:

```bash
for i in 1 2 3 4 5 6 7 8 9 10; do python3 -c "from client.rpc_client import RPCClient; print(RPCClient('172.31.22.26', 30007).call('sumar', 4, 7))"; done
kubectl logs -l app=rpc-server --tail=3 --prefix | grep Petición
```

![Balanceo entre pods](evidencias/20_balanceo_10_llamadas.png)

Reducción a 2 réplicas (los pods sobrantes pasan a `Terminating`) y vuelta a 3:

![Escalado a 2 réplicas](evidencias/21_scale_2_replicas.png)

![Vuelta a 3 réplicas y uso de disco](evidencias/22_scale_3_replicas_df.png)

![Disco de los workers (27 GB, ≈15 % usado)](evidencias/24_disco_workers.png)

## 8. Prueba de carga

`carga.py` lanza `HILOS` hilos que hacen `PETICIONES` llamadas a `sumar(4, 7)` cada uno, y comprueba que el resultado sea 11. Muestra peticiones correctas y erróneas, tiempo total, peticiones por segundo y tiempo medio y máximo por petición.

```bash
python3 carga.py 172.31.22.26 30007 <HILOS> <PETICIONES_POR_HILO>
```

Reparto de peticiones por pod tras la prueba:

```bash
for p in $(kubectl get pods -l app=rpc-server -o name); do echo $p; kubectl logs $p | grep -c Petición; done
```

![Pruebas con 3 réplicas: 10×20, 50×20 y 100×50, y peticiones atendidas por cada pod](evidencias/23_carga_3_replicas_3_pruebas.png)

Misma carga con una sola réplica (`kubectl scale deployment rpc-server --replicas=1`):

![100×50 con 1 réplica](evidencias/25_carga_1_replica.png)

Carga sostenida 100×500 (50 000 peticiones), repetida:

![100×500, dos terminales](evidencias/26_carga_100x500_dos_terminales.png)

![100×500, repetición](evidencias/27_carga_100x500_repeticion.png)

## 9. Tolerancia a fallos

Se borra un pod mientras se ejecuta una carga de 150 000 peticiones (100×1500) y Kubernetes lo recrea:

```bash
kubectl delete pod $(kubectl get pods -l app=rpc-server -o name | head -1 | cut -d/ -f2)
python3 carga.py 172.31.22.26 30007 100 1500
```

![Borrado del pod e inicio de la prueba](evidencias/28_delete_pod_durante_carga.png)

![Resultado: 3 pods de nuevo Running (uno nuevo) y 273 errores en 150 000](evidencias/29_resultado_con_fallo_pod.png)

![Escalado final a 6 réplicas](evidencias/30_escalado_final_6.png)

## 10. Resultados

| Esc. | Réplicas | Hilos × pet. | Total | Errores | Tiempo (s) | Pet./s | Media (ms) | Máx (s) |
|---|---|---|---|---|---|---|---|---|
| A1 | 3 | 10 × 20 | 200 | 0 | 0,08 | 2 501,0 | 3,7 | 0,0091 |
| A2 | 3 | 50 × 20 | 1 000 | 0 | 0,41 | 2 465,9 | 16,9 | 0,0451 |
| A3 | 3 | 100 × 50 | 5 000 | 0 | 1,81 | 2 763,9 | 32,5 | 0,0976 |
| B1 | 1 | 100 × 50 | 5 000 | 0 | 2,98 | 1 675,2 | 58,2 | 0,0783 |
| C1 | 3 | 100 × 500 | 50 000 | 0 | 42,09 | 1 188,0 | 74,1 | 4,1353 |
| C2 | 3 | 100 × 500 | 50 000 | 0 | 28,61 | 1 747,5 | 48,5 | 2,1786 |
| C3 | 3 | 100 × 500 | 50 000 | 0 | 21,30 | 2 347,4 | 35,3 | 3,0954 |
| D1 | 3 | 100 × 1500 | 150 000 | **273** | 131,71 | 1 138,9 | 41,0 | 5,0045 |

![Rendimiento y latencia por escenario](resultados/grafica_rendimiento.png)

- Con 3 réplicas en lugar de 1 (100×50) el caudal sube de 1 675 a 2 764 peticiones/s (+65 %) y la latencia media baja de 58,2 a 32,5 ms.
- El reparto entre pods es homogéneo (≈2 000 peticiones cada uno).
- En D1 se pierden 273 peticiones (0,18 %); el máximo de 5,0045 s coincide con el timeout de 5 s del cliente.
- Los resultados varían entre repeticiones (C1–C3), y el generador de carga se ejecuta en un nodo del propio clúster.

La versión resumida (diseño, configuración, prueba de carga y resultados en 4 páginas) está en [README.md](README.md).
