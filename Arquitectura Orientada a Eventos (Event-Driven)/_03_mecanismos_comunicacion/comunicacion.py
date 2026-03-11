"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          PILAR 3: MECANISMOS DE COMUNICACIÓN                               ║
║          Pub/Sub (One-to-Many) vs Colas (Point-to-Point)                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

Existen DOS mecanismos fundamentales para distribuir eventos:

    ╔════════════════════════════════════════════════════════════════╗
    ║  1. PUB/SUB (Publicación / Suscripción)                      ║
    ║     → Modelo de DIFUSIÓN MASIVA (One-to-Many)                ║
    ║     → UN evento llega a TODOS los suscriptores               ║
    ║     → Cada suscriptor recibe su propia copia                 ║
    ║                                                               ║
    ║     Emisor ──→ [Tema/Topic] ──→ Suscriptor A                ║
    ║                              ──→ Suscriptor B                ║
    ║                              ──→ Suscriptor C                ║
    ║                                                               ║
    ║  Ejemplo: "PedidoCreado" → Email, Inventario, Analytics      ║
    ║           Todos necesitan saber, todos lo reciben.            ║
    ╠════════════════════════════════════════════════════════════════╣
    ║  2. COLA DE MENSAJERÍA (Point-to-Point)                      ║
    ║     → Modelo de COMPETENCIA (One-to-One)                     ║
    ║     → UN evento lo procesa SOLO UN consumidor                ║
    ║     → Los consumidores compiten por el mensaje               ║
    ║                                                               ║
    ║     Emisor ──→ [Cola] ──→ Worker A (toma mensaje 1)         ║
    ║                       ──→ Worker B (toma mensaje 2)         ║
    ║                       ──→ Worker C (toma mensaje 3)         ║
    ║                                                               ║
    ║  Ejemplo: "GenerarFacturaPDF" → Solo UN worker debe          ║
    ║           generar cada factura para evitar duplicados.        ║
    ╚════════════════════════════════════════════════════════════════╝

¿CUÁNDO USAR CADA UNO?

    Pub/Sub:  Cuando MÚLTIPLES servicios necesitan reaccionar al mismo evento.
    Cola:     Cuando UNA tarea debe ser procesada EXACTAMENTE POR UNO.
"""

import sys
import os
import threading
import time
import queue
from typing import Callable
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _01_evento_unidad_de_verdad.evento import Evento, PedidoCreado


# ══════════════════════════════════════════════════════════════════════════════
# PATRÓN PUB/SUB (Publicación / Suscripción) — One-to-Many
# ══════════════════════════════════════════════════════════════════════════════

class TopicPubSub:
    """
    Un TOPIC (Tema) en el patrón Pub/Sub.

    Comportamiento:
    - Cada mensaje publicado se COPIA a TODOS los suscriptores.
    - Si hay 5 suscriptores, se entregan 5 copias del mismo evento.
    - Cada suscriptor procesa el evento de forma independiente.

    Tecnologías reales: Kafka Topics, AWS SNS, Google Pub/Sub Topics
    """

    def __init__(self, nombre: str):
        self.nombre = nombre
        self._suscriptores: list[tuple[str, Callable]] = []
        self._historial: list[Evento] = []

    def suscribir(self, nombre_consumidor: str, callback: Callable):
        """Un consumidor se suscribe al topic."""
        self._suscriptores.append((nombre_consumidor, callback))

    def publicar(self, evento: Evento):
        """
        Publica un evento: TODOS los suscriptores reciben una copia.
        Esto es DIFUSIÓN MASIVA (fan-out).
        """
        self._historial.append(evento)
        print(f"\n  📡 Topic [{self.nombre}]: Difundiendo '{evento.event_type}' "
              f"a {len(self._suscriptores)} suscriptores")

        for nombre, callback in self._suscriptores:
            callback(evento)

    @property
    def total_suscriptores(self) -> int:
        return len(self._suscriptores)


# ══════════════════════════════════════════════════════════════════════════════
# PATRÓN COLA DE MENSAJERÍA (Point-to-Point) — One-to-One
# ══════════════════════════════════════════════════════════════════════════════

class ColaMensajeria:
    """
    Una COLA de mensajería para procesamiento Point-to-Point.

    Comportamiento:
    - Los mensajes se encolan y los WORKERS COMPITEN por ellos.
    - Cada mensaje es procesado por EXACTAMENTE UN worker.
    - Garantiza que una tarea NO se ejecute más de una vez.
    - Si un worker falla, el mensaje vuelve a la cola.

    Tecnologías reales: RabbitMQ Queues, AWS SQS, Azure Service Bus Queues

    Diferencia clave con Pub/Sub:
    ┌───────────────────────────────────────────────────────────┐
    │  Pub/Sub: 1 mensaje → N copias → N consumidores          │
    │  Cola:    1 mensaje → 1 entrega → 1 worker               │
    └───────────────────────────────────────────────────────────┘
    """

    def __init__(self, nombre: str):
        self.nombre = nombre
        self._cola: queue.Queue = queue.Queue()
        self._workers: list[tuple[str, Callable]] = []
        self._procesados: int = 0
        self._activo = False

    def encolar(self, evento: Evento):
        """Añade un evento a la cola para ser procesado."""
        self._cola.put(evento)
        print(f"  📥 Cola [{self.nombre}]: Mensaje encolado "
              f"(pendientes: {self._cola.qsize()})")

    def registrar_worker(self, nombre: str, callback: Callable):
        """Registra un worker que competirá por los mensajes."""
        self._workers.append((nombre, callback))

    def procesar_todos(self):
        """
        Procesa todos los mensajes de la cola.
        Cada mensaje es tomado por UN SOLO worker (round-robin).
        """
        if not self._workers:
            print(f"  ⚠ Cola [{self.nombre}]: No hay workers registrados")
            return

        worker_idx = 0
        while not self._cola.empty():
            evento = self._cola.get()
            nombre_worker, callback = self._workers[worker_idx % len(self._workers)]

            print(f"  ⚙️  Cola [{self.nombre}]: Worker '{nombre_worker}' "
                  f"toma el mensaje")
            callback(evento)

            self._cola.task_done()
            self._procesados += 1
            worker_idx += 1

    @property
    def mensajes_pendientes(self) -> int:
        return self._cola.qsize()


# ══════════════════════════════════════════════════════════════════════════════
# DEMOSTRACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def demo_mecanismos_comunicacion():
    """
    Demuestra la diferencia entre Pub/Sub y Colas de Mensajería.
    """
    print("=" * 70)
    print("  PILAR 3: MECANISMOS DE COMUNICACIÓN")
    print("=" * 70)

    # ═══════════════════════════════════════════════════════════════════
    #  DEMO 1: PUB/SUB — Un evento, múltiples consumidores
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "─" * 70)
    print("  DEMO 1: PUB/SUB (Publicación / Suscripción)")
    print("  Un evento → Todos los suscriptores lo reciben")
    print("─" * 70)

    topic_pedidos = TopicPubSub("pedidos-creados")

    # Tres servicios se suscriben al mismo topic
    topic_pedidos.suscribir("Servicio-Email", lambda e:
        print(f"     📧 [Email] Enviando confirmación para "
              f"pedido {e.payload.get('pedido_id')}"))

    topic_pedidos.suscribir("Servicio-Inventario", lambda e:
        print(f"     📦 [Inventario] Reservando stock para "
              f"{len(e.payload.get('productos', []))} productos"))

    topic_pedidos.suscribir("Servicio-Analytics", lambda e:
        print(f"     📊 [Analytics] Registrando venta de "
              f"${e.payload.get('total', 0):.2f}"))

    print(f"\n  Suscriptores registrados: {topic_pedidos.total_suscriptores}")

    # Publicar UN evento → los TRES lo reciben
    evento = PedidoCreado(
        pedido_id="PED-001",
        cliente_id="CLI-100",
        productos=[
            {"sku": "A1", "nombre": "Producto A", "cantidad": 2, "precio": 25.00},
            {"sku": "B2", "nombre": "Producto B", "cantidad": 1, "precio": 50.00},
        ],
        total=100.00
    )
    topic_pedidos.publicar(evento)

    print(f"\n  ✓ Resultado: 1 evento publicado → "
          f"{topic_pedidos.total_suscriptores} servicios notificados")

    # ═══════════════════════════════════════════════════════════════════
    #  DEMO 2: COLA — Cada mensaje procesado por exactamente un worker
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "─" * 70)
    print("  DEMO 2: COLA DE MENSAJERÍA (Point-to-Point)")
    print("  Cada mensaje → Solo UN worker lo procesa")
    print("─" * 70)

    cola_facturas = ColaMensajeria("generar-facturas")

    # Registrar 3 workers que compiten por los mensajes
    cola_facturas.registrar_worker("Worker-PDF-1", lambda e:
        print(f"     🖨️  [Worker-PDF-1] Generando factura para "
              f"pedido {e.payload.get('pedido_id')}"))

    cola_facturas.registrar_worker("Worker-PDF-2", lambda e:
        print(f"     🖨️  [Worker-PDF-2] Generando factura para "
              f"pedido {e.payload.get('pedido_id')}"))

    cola_facturas.registrar_worker("Worker-PDF-3", lambda e:
        print(f"     🖨️  [Worker-PDF-3] Generando factura para "
              f"pedido {e.payload.get('pedido_id')}"))

    # Encolar 6 eventos → se reparten entre los 3 workers
    print(f"\n  Encolando 6 tareas de generación de facturas...")
    for i in range(1, 7):
        ev = Evento(
            event_type="GenerarFactura",
            source="servicio-facturacion",
            payload={"pedido_id": f"PED-{i:03d}", "formato": "PDF"}
        )
        cola_facturas.encolar(ev)

    print(f"\n  Procesando cola ({cola_facturas.mensajes_pendientes} pendientes)...")
    print()
    cola_facturas.procesar_todos()

    print(f"\n  ✓ Resultado: 6 mensajes procesados → cada uno por UN SOLO worker")
    print(f"    Ningún pedido fue facturado más de una vez")

    # ═══════════════════════════════════════════════════════════════════
    #  COMPARATIVA VISUAL
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  COMPARATIVA: PUB/SUB vs COLA")
    print("=" * 70)
    print("""
    ┌─────────────────────┬──────────────────────────────────────────┐
    │   Característica     │ Pub/Sub           │ Cola (P2P)          │
    ├─────────────────────┼───────────────────┼─────────────────────┤
    │ Distribución         │ One-to-Many       │ One-to-One          │
    │ Copias del mensaje   │ N (una por susc.) │ 1 (un solo worker)  │
    │ Consumidores         │ Independientes    │ Competidores        │
    │ Caso de uso          │ Notificar a todos │ Distribuir trabajo  │
    │ Ejemplo              │ "Pedido creado"   │ "Generar factura"   │
    │                      │  → Email           │  → Solo un worker   │
    │                      │  → Inventario      │    lo procesa       │
    │                      │  → Analytics       │                     │
    └─────────────────────┴───────────────────┴─────────────────────┘

    REGLA DE ORO:
    • ¿Varios servicios deben SABER que algo ocurrió? → Pub/Sub
    • ¿Una TAREA debe ejecutarse exactamente una vez? → Cola
    """)


if __name__ == "__main__":
    demo_mecanismos_comunicacion()
