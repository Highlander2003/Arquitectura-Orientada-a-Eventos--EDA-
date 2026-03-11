"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          PILAR 2: ROLES Y RESPONSABILIDADES DE LOS ACTORES                 ║
║          Emisor (Producer) · Consumidor (Consumer) · Broker                ║
╚══════════════════════════════════════════════════════════════════════════════╝

En una EDA existen tres actores fundamentales con responsabilidades
claramente separadas. Esta separación es lo que permite el DESACOPLAMIENTO:

    ┌──────────┐      ┌──────────────┐      ┌────────────┐
    │  EMISOR  │ ───→ │    BROKER    │ ───→ │ CONSUMIDOR │
    │(Producer)│      │(Event Broker)│      │ (Consumer) │
    └──────────┘      └──────────────┘      └────────────┘
         │                   │                     │
         │ "Algo pasó,      │ "Lo guardo,         │ "Me interesa
         │  lo publico"     │  lo enruto,         │  este tipo,
         │                  │  lo distribuyo"      │  reacciono"
         │                  │                      │
         └── NO sabe ───────┴─── quién consume ───┘

    PRINCIPIO CLAVE: El emisor NO conoce al consumidor.
    El consumidor NO conoce al emisor.
    Solo el Broker los conecta.
"""

import sys
import os
import threading
import time
from typing import Callable
from collections import defaultdict

# Importar el módulo de eventos del Pilar 1
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _01_evento_unidad_de_verdad.evento import Evento, PedidoCreado, PagoRealizado


# ══════════════════════════════════════════════════════════════════════════════
# GESTOR DE EVENTOS (EVENT BROKER)
# ══════════════════════════════════════════════════════════════════════════════

class EventBroker:
    """
    El BROKER es el corazón logístico de la arquitectura.

    Responsabilidades:
    ┌──────────────────────────────────────────────────────────────────┐
    │ 1. RECIBIR eventos de cualquier emisor                         │
    │ 2. PERSISTIR el evento (garantizar que no se pierda)           │
    │ 3. ENRUTAR el evento a los consumidores suscritos              │
    │ 4. DISTRIBUIR de forma ordenada y confiable                    │
    │ 5. CONFIRMAR la entrega (acknowledgment)                       │
    └──────────────────────────────────────────────────────────────────┘

    Analogía: Es como el sistema postal.
    - Tú (emisor) dejas una carta en el buzón.
    - El correo (broker) la clasifica, la transporta y la entrega.
    - Tú NO necesitas saber dónde vive el destinatario.
    - El destinatario NO necesita saber quién la envió para leerla.

    En producción, este rol lo cumplen tecnologías como:
    - Apache Kafka
    - RabbitMQ
    - Amazon SNS/SQS
    - Azure Event Hub
    - Google Pub/Sub
    """

    def __init__(self, nombre: str = "EventBroker-Principal"):
        self.nombre = nombre
        self._suscripciones: dict[str, list[Callable]] = defaultdict(list)
        self._eventos_publicados: list[Evento] = []
        self._lock = threading.Lock()

    def suscribir(self, event_type: str, callback: Callable):
        """
        Registra un consumidor (callback) para un tipo de evento.
        El consumidor NO sabe quién emitirá el evento.
        """
        with self._lock:
            self._suscripciones[event_type].append(callback)

    def publicar(self, evento: Evento):
        """
        Recibe un evento de un emisor y lo distribuye a todos
        los consumidores suscritos a ese tipo de evento.

        Flujo interno:
        1. Recibir el evento
        2. Persistirlo en el log interno
        3. Buscar los consumidores suscritos a ese event_type
        4. Entregar el evento a cada uno
        """
        with self._lock:
            # Paso 1 y 2: Recibir y persistir
            self._eventos_publicados.append(evento)

            # Paso 3: Buscar suscriptores
            suscriptores = self._suscripciones.get(evento.event_type, [])

            if not suscriptores:
                print(f"  ⚠ Broker: Evento '{evento.event_type}' recibido "
                      f"pero sin suscriptores")
                return

            # Paso 4: Distribuir a cada consumidor
            print(f"\n  📬 Broker: Distribuyendo '{evento.event_type}' "
                  f"a {len(suscriptores)} consumidor(es)...")

            for callback in suscriptores:
                try:
                    callback(evento)
                except Exception as e:
                    print(f"  ❌ Broker: Error al entregar a consumidor: {e}")

    @property
    def total_eventos(self) -> int:
        return len(self._eventos_publicados)

    @property
    def tipos_suscritos(self) -> list[str]:
        return list(self._suscripciones.keys())


# ══════════════════════════════════════════════════════════════════════════════
# EMISOR (PRODUCER)
# ══════════════════════════════════════════════════════════════════════════════

class Emisor:
    """
    El EMISOR (Producer) tiene UNA SOLA responsabilidad:
    Detectar que algo ocurrió y publicar el evento correspondiente.

    ┌──────────────────────────────────────────────────────────────────┐
    │  PRINCIPIO FUNDAMENTAL DEL EMISOR:                             │
    │                                                                 │
    │  "Dispara y olvida" (Fire and Forget)                          │
    │                                                                 │
    │  • El emisor PUBLICA el evento y CONTINÚA su trabajo.          │
    │  • NO espera respuesta.                                        │
    │  • NO sabe cuántos consumidores hay.                           │
    │  • NO sabe qué harán con el evento.                            │
    │  • NO le importa si fallan o no.                               │
    │                                                                 │
    │  ¿Por qué? Porque si el emisor conociera a los consumidores,  │
    │  estaríamos de vuelta en una arquitectura acoplada.            │
    └──────────────────────────────────────────────────────────────────┘
    """

    def __init__(self, nombre_servicio: str, broker: EventBroker):
        self.nombre_servicio = nombre_servicio
        self._broker = broker  # Solo conoce al broker, NO a los consumidores

    def emitir(self, evento: Evento):
        """
        Publica un evento en el broker.
        El emisor NO sabe ni le importa quién lo recibirá.
        """
        print(f"\n  📤 Emisor [{self.nombre_servicio}]: "
              f"Publicando '{evento.event_type}'")
        self._broker.publicar(evento)


# ══════════════════════════════════════════════════════════════════════════════
# CONSUMIDOR (CONSUMER)
# ══════════════════════════════════════════════════════════════════════════════

class Consumidor:
    """
    El CONSUMIDOR (Consumer) reacciona ante eventos que le interesan.

    ┌──────────────────────────────────────────────────────────────────┐
    │  CARACTERÍSTICAS DEL CONSUMIDOR:                               │
    │                                                                 │
    │  • Se SUSCRIBE a tipos de eventos específicos.                 │
    │  • Contiene LÓGICA DE NEGOCIO desacoplada.                     │
    │  • NO sabe quién emitió el evento.                             │
    │  • Puede ser añadido o removido sin afectar al emisor.         │
    │  • Procesa el evento según SU propia lógica.                   │
    │                                                                 │
    │  Ejemplo: Ante un "PedidoCreado", un consumidor envía email,  │
    │  otro actualiza inventario, otro notifica al almacén.          │
    │  Cada uno con su lógica independiente.                         │
    └──────────────────────────────────────────────────────────────────┘
    """

    def __init__(self, nombre: str, broker: EventBroker):
        self.nombre = nombre
        self._broker = broker

    def suscribirse(self, event_type: str, handler: Callable = None):
        """
        Se suscribe a un tipo de evento en el broker.
        Opcionalmente recibe un handler personalizado.
        """
        callback = handler or self._handler_por_defecto
        self._broker.suscribir(event_type, callback)
        print(f"  👂 Consumidor [{self.nombre}]: "
              f"Suscrito a '{event_type}'")

    def _handler_por_defecto(self, evento: Evento):
        """Handler genérico que muestra el evento recibido."""
        print(f"     → [{self.nombre}] recibió '{evento.event_type}' "
              f"(ID: {evento.event_id[:8]}...)")


# ═══════════════════════════════════════════════════════════════════════
# CONSUMIDORES ESPECIALIZADOS (Lógica de negocio desacoplada)
# ═══════════════════════════════════════════════════════════════════════

class ConsumidorEmail(Consumidor):
    """Consumidor que envía notificaciones por email."""

    def __init__(self, broker: EventBroker):
        super().__init__("Servicio-Email", broker)
        self.suscribirse("PedidoCreado", self._enviar_confirmacion)
        self.suscribirse("PagoRealizado", self._enviar_recibo)

    def _enviar_confirmacion(self, evento: Evento):
        cliente = evento.payload.get("cliente_id", "desconocido")
        pedido = evento.payload.get("pedido_id", "N/A")
        print(f"     📧 [{self.nombre}] → Enviando email de confirmación "
              f"al cliente {cliente} por pedido {pedido}")

    def _enviar_recibo(self, evento: Evento):
        monto = evento.payload.get("monto", 0)
        print(f"     📧 [{self.nombre}] → Enviando recibo digital "
              f"por ${monto:.2f}")


class ConsumidorInventario(Consumidor):
    """Consumidor que gestiona el inventario."""

    def __init__(self, broker: EventBroker):
        super().__init__("Servicio-Inventario", broker)
        self.suscribirse("PedidoCreado", self._reservar_stock)

    def _reservar_stock(self, evento: Evento):
        productos = evento.payload.get("productos", [])
        for producto in productos:
            print(f"     📦 [{self.nombre}] → Reservando {producto.get('cantidad', 0)}x "
                  f"'{producto.get('nombre', '?')}' del inventario")


class ConsumidorAnalytics(Consumidor):
    """Consumidor que registra métricas y analíticas."""

    def __init__(self, broker: EventBroker):
        super().__init__("Servicio-Analytics", broker)
        self.suscribirse("PedidoCreado", self._registrar_venta)
        self.suscribirse("PagoRealizado", self._registrar_ingreso)

    def _registrar_venta(self, evento: Evento):
        total = evento.payload.get("total", 0)
        print(f"     📊 [{self.nombre}] → Registrando nueva venta: ${total:.2f}")

    def _registrar_ingreso(self, evento: Evento):
        metodo = evento.payload.get("metodo_pago", "desconocido")
        print(f"     📊 [{self.nombre}] → Métricas: pago via '{metodo}'")


# ══════════════════════════════════════════════════════════════════════════════
# DEMOSTRACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def demo_roles_y_responsabilidades():
    """
    Demuestra cómo interactúan los tres actores:
    Emisor → Broker → Consumidores
    """
    print("=" * 70)
    print("  PILAR 2: ROLES Y RESPONSABILIDADES DE LOS ACTORES")
    print("=" * 70)

    # ─── 1. Crear el Broker (el intermediario central) ───────────────
    print("\n🏗️  PASO 1: Inicializar el Event Broker")
    print("-" * 50)
    broker = EventBroker("EcommerceBroker")
    print(f"  ✓ Broker '{broker.nombre}' inicializado")

    # ─── 2. Crear y registrar Consumidores ───────────────────────────
    print("\n🏗️  PASO 2: Registrar Consumidores (se suscriben a eventos)")
    print("-" * 50)
    email_svc = ConsumidorEmail(broker)
    inventario_svc = ConsumidorInventario(broker)
    analytics_svc = ConsumidorAnalytics(broker)

    print(f"\n  Tipos de eventos con suscriptores: {broker.tipos_suscritos}")

    # ─── 3. Crear Emisor ─────────────────────────────────────────────
    print("\n🏗️  PASO 3: El Emisor publica eventos (sin conocer consumidores)")
    print("-" * 50)
    emisor = Emisor("servicio-pedidos", broker)

    # ─── 4. Simular el flujo completo ────────────────────────────────
    print("\n🚀 FLUJO COMPLETO: Un cliente crea un pedido")
    print("=" * 50)

    # El emisor detecta que se creó un pedido y emite el evento
    evento_pedido = PedidoCreado(
        pedido_id="PED-2025-042",
        cliente_id="CLI-7890",
        productos=[
            {"sku": "TECLADO-01", "nombre": "Teclado Mecánico", "cantidad": 1, "precio": 89.99},
            {"sku": "MONITOR-02", "nombre": "Monitor 27\"", "cantidad": 1, "precio": 350.00}
        ],
        total=439.99
    )

    # FIRE AND FORGET: El emisor publica y sigue su camino
    emisor.emitir(evento_pedido)

    print("\n" + "-" * 50)
    print("  ↑ Observa: El emisor publicó UN evento y TRES consumidores")
    print("  reaccionaron, cada uno con su propia lógica de negocio.")
    print("  El emisor NO sabe que existen estos consumidores.")

    # ─── 5. Segundo evento (Pago) ────────────────────────────────────
    print("\n\n🚀 SEGUNDO EVENTO: El pago se procesa")
    print("=" * 50)

    emisor_pagos = Emisor("servicio-pagos", broker)
    evento_pago = PagoRealizado(
        pedido_id="PED-2025-042",
        monto=439.99,
        metodo_pago="tarjeta_credito",
        correlation_id=evento_pedido.correlation_id
    )
    emisor_pagos.emitir(evento_pago)

    # ─── Resumen ─────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"  RESUMEN: {broker.total_eventos} eventos procesados por el Broker")
    print("=" * 70)
    print("""
  DIAGRAMA DEL FLUJO EJECUTADO:

  [servicio-pedidos]                    [servicio-pagos]
        │                                      │
        ▼                                      ▼
  PedidoCreado ──→ ┌────────────┐ ←── PagoRealizado
                   │   BROKER   │
                   └─────┬──────┘
                    ╱    │    ╲
                   ╱     │     ╲
                  ▼      ▼      ▼
            📧 Email  📦 Stock  📊 Analytics
            (envía    (reserva  (registra
             correo)   items)    métricas)

  → Ningún servicio conoce directamente a otro.
  → El Broker es el único punto de contacto.
  → Se pueden añadir nuevos consumidores SIN tocar los emisores.
    """)


if __name__ == "__main__":
    demo_roles_y_responsabilidades()
