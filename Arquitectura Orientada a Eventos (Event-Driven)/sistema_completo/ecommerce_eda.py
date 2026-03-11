"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   SISTEMA COMPLETO E-COMMERCE — Arquitectura Orientada a Eventos           ║
║                                                                              ║
║   Este módulo integra TODOS los pilares en una simulación realista          ║
║   de un sistema de e-commerce donde el flujo de datos viaja desde           ║
║   la acción inicial (compra) hasta la ejecución de múltiples tareas        ║
║   secundarias de forma ASÍNCRONA y DESACOPLADA.                            ║
║                                                                              ║
║   FLUJO COMPLETO:                                                            ║
║                                                                              ║
║   [Cliente compra] ──→ PedidoCreado                                         ║
║                            │                                                 ║
║                    ┌───────┼───────────────────────┐                        ║
║                    ▼       ▼           ▼           ▼                        ║
║               📧 Email  📦 Stock  💳 Pagos   📊 Analytics                   ║
║                            │                                                 ║
║                            ▼                                                 ║
║                    PagoRealizado                                             ║
║                         │                                                    ║
║                  ┌──────┼──────────┐                                        ║
║                  ▼      ▼          ▼                                        ║
║             🧾 Factura  📧 Recibo  🚚 Envío                                ║
║                                    │                                         ║
║                                    ▼                                         ║
║                           EnvíoPreparado                                     ║
║                                    │                                         ║
║                              ┌─────┤                                        ║
║                              ▼     ▼                                        ║
║                         📧 Track  📊 Métricas                               ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import uuid
import time
from datetime import datetime, timezone
from collections import defaultdict
from typing import Callable

# Ajustar path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _01_evento_unidad_de_verdad.evento import Evento


# ══════════════════════════════════════════════════════════════════════════════
# BROKER CENTRAL DEL SISTEMA E-COMMERCE
# ══════════════════════════════════════════════════════════════════════════════

class EcommerceBroker:
    """Broker centralizado con persistencia, resiliencia y métricas."""

    def __init__(self):
        self._suscripciones: dict[str, list[tuple[str, Callable]]] = defaultdict(list)
        self._event_store: list[dict] = []
        self._dead_letter: list[dict] = []
        self._eventos_procesados: set[str] = set()

    def suscribir(self, event_type: str, nombre: str, handler: Callable):
        self._suscripciones[event_type].append((nombre, handler))

    def publicar(self, evento: Evento):
        # Persistir
        self._event_store.append(evento.to_dict())

        # Distribuir con aislamiento de fallos
        suscriptores = self._suscripciones.get(evento.event_type, [])
        for nombre, handler in suscriptores:
            try:
                handler(evento)
            except Exception as e:
                self._dead_letter.append({
                    "evento": evento.event_type,
                    "consumidor": nombre,
                    "error": str(e)
                })

    @property
    def total_eventos(self) -> int:
        return len(self._event_store)


# ══════════════════════════════════════════════════════════════════════════════
# MICROSERVICIOS DEL E-COMMERCE
# ══════════════════════════════════════════════════════════════════════════════

class ServicioPedidos:
    """Microservicio: Gestión de pedidos (EMISOR principal)."""

    def __init__(self, broker: EcommerceBroker):
        self._broker = broker

    def crear_pedido(self, cliente_id: str, productos: list, total: float):
        pedido_id = f"PED-{uuid.uuid4().hex[:6].upper()}"
        print(f"\n  🛒 [Servicio-Pedidos] Cliente {cliente_id} crea pedido {pedido_id}")

        evento = Evento(
            event_type="PedidoCreado",
            source="servicio-pedidos",
            payload={
                "pedido_id": pedido_id,
                "cliente_id": cliente_id,
                "productos": productos,
                "total": total,
            }
        )

        # Fire and Forget: publica y continúa
        self._broker.publicar(evento)
        return pedido_id


class ServicioEmail:
    """Microservicio: Notificaciones por email."""

    def __init__(self, broker: EcommerceBroker):
        broker.suscribir("PedidoCreado", "Email", self._confirmar_pedido)
        broker.suscribir("PagoRealizado", "Email", self._enviar_recibo)
        broker.suscribir("EnvioPreparado", "Email", self._enviar_tracking)

    def _confirmar_pedido(self, evento: Evento):
        p = evento.payload
        print(f"     📧 [Email] → Confirmación de pedido {p['pedido_id']} "
              f"enviada a cliente {p['cliente_id']}")

    def _enviar_recibo(self, evento: Evento):
        p = evento.payload
        print(f"     📧 [Email] → Recibo digital por ${p['monto']:.2f} "
              f"enviado al cliente")

    def _enviar_tracking(self, evento: Evento):
        p = evento.payload
        print(f"     📧 [Email] → Número de seguimiento: {p['tracking']} "
              f"enviado al cliente")


class ServicioInventario:
    """Microservicio: Gestión de inventario."""

    def __init__(self, broker: EcommerceBroker):
        self._broker = broker
        self._stock = {
            "LAPTOP-001": 50, "MOUSE-003": 200,
            "TECLADO-01": 150, "MONITOR-02": 75
        }
        broker.suscribir("PedidoCreado", "Inventario", self._reservar_stock)

    def _reservar_stock(self, evento: Evento):
        for prod in evento.payload.get("productos", []):
            sku = prod.get("sku", "?")
            qty = prod.get("cantidad", 0)
            anterior = self._stock.get(sku, 0)
            self._stock[sku] = max(0, anterior - qty)
            print(f"     📦 [Inventario] → {sku}: {anterior} → "
                  f"{self._stock[sku]} (reservados: {qty})")


class ServicioPagos:
    """Microservicio: Procesamiento de pagos."""

    def __init__(self, broker: EcommerceBroker):
        self._broker = broker
        broker.suscribir("PedidoCreado", "Pagos", self._procesar_pago)

    def _procesar_pago(self, evento: Evento):
        p = evento.payload
        print(f"     💳 [Pagos] → Procesando cobro de ${p['total']:.2f} "
              f"para pedido {p['pedido_id']}...")
        time.sleep(0.1)  # Simular latencia del gateway de pagos
        print(f"     💳 [Pagos] → Pago EXITOSO ✓")

        # Emitir nuevo evento: el pago fue realizado
        evento_pago = Evento(
            event_type="PagoRealizado",
            source="servicio-pagos",
            payload={
                "pedido_id": p["pedido_id"],
                "cliente_id": p["cliente_id"],
                "monto": p["total"],
                "metodo": "tarjeta_credito",
                "transaccion_id": f"TXN-{uuid.uuid4().hex[:8].upper()}"
            },
            correlation_id=evento.correlation_id
        )
        self._broker.publicar(evento_pago)


class ServicioFacturacion:
    """Microservicio: Generación de facturas."""

    def __init__(self, broker: EcommerceBroker):
        broker.suscribir("PagoRealizado", "Facturación", self._generar_factura)

    def _generar_factura(self, evento: Evento):
        p = evento.payload
        factura_id = f"FAC-{uuid.uuid4().hex[:6].upper()}"
        print(f"     🧾 [Facturación] → Factura {factura_id} generada "
              f"por ${p['monto']:.2f} (TXN: {p['transaccion_id']})")


class ServicioLogistica:
    """Microservicio: Preparación y seguimiento de envíos."""

    def __init__(self, broker: EcommerceBroker):
        self._broker = broker
        broker.suscribir("PagoRealizado", "Logística", self._preparar_envio)

    def _preparar_envio(self, evento: Evento):
        p = evento.payload
        tracking = f"TRACK-{uuid.uuid4().hex[:8].upper()}"
        print(f"     🚚 [Logística] → Envío preparado para pedido "
              f"{p['pedido_id']} (tracking: {tracking})")

        # Emitir nuevo evento
        evento_envio = Evento(
            event_type="EnvioPreparado",
            source="servicio-logistica",
            payload={
                "pedido_id": p["pedido_id"],
                "cliente_id": p["cliente_id"],
                "tracking": tracking,
                "estado": "en_preparacion"
            },
            correlation_id=evento.correlation_id
        )
        self._broker.publicar(evento_envio)


class ServicioAnalytics:
    """Microservicio: Métricas y analíticas en tiempo real."""

    def __init__(self, broker: EcommerceBroker):
        self._metricas = {
            "total_pedidos": 0,
            "ingresos_totales": 0.0,
            "total_envios": 0
        }
        broker.suscribir("PedidoCreado", "Analytics", self._registrar_pedido)
        broker.suscribir("PagoRealizado", "Analytics", self._registrar_ingreso)
        broker.suscribir("EnvioPreparado", "Analytics", self._registrar_envio)

    def _registrar_pedido(self, evento: Evento):
        self._metricas["total_pedidos"] += 1
        print(f"     📊 [Analytics] → Pedido #{self._metricas['total_pedidos']} "
              f"registrado")

    def _registrar_ingreso(self, evento: Evento):
        monto = evento.payload.get("monto", 0)
        self._metricas["ingresos_totales"] += monto
        print(f"     📊 [Analytics] → Ingreso acumulado: "
              f"${self._metricas['ingresos_totales']:.2f}")

    def _registrar_envio(self, evento: Evento):
        self._metricas["total_envios"] += 1
        print(f"     📊 [Analytics] → Envíos en preparación: "
              f"{self._metricas['total_envios']}")

    @property
    def dashboard(self) -> dict:
        return dict(self._metricas)


# ══════════════════════════════════════════════════════════════════════════════
# SIMULACIÓN COMPLETA
# ══════════════════════════════════════════════════════════════════════════════

def demo_sistema_completo():
    """
    Ejecuta una simulación completa del flujo de un e-commerce
    utilizando todos los conceptos de la EDA.
    """
    print("=" * 70)
    print("  SISTEMA COMPLETO: E-COMMERCE CON EDA")
    print("  Flujo de la acción inicial a múltiples tareas asíncronas")
    print("=" * 70)

    # ─── Inicializar infraestructura ─────────────────────────────────
    print("\n  🏗️  Inicializando microservicios...")
    broker = EcommerceBroker()

    # Los consumidores se suscriben (orden irrelevante)
    email_svc = ServicioEmail(broker)
    inventario_svc = ServicioInventario(broker)
    pagos_svc = ServicioPagos(broker)
    facturacion_svc = ServicioFacturacion(broker)
    logistica_svc = ServicioLogistica(broker)
    analytics_svc = ServicioAnalytics(broker)

    pedidos_svc = ServicioPedidos(broker)
    print("  ✓ 7 microservicios inicializados\n")

    # ─── Simular compra ──────────────────────────────────────────────
    print("━" * 70)
    print("  🚀 SIMULACIÓN: Un cliente realiza una compra")
    print("━" * 70)

    pedido_id = pedidos_svc.crear_pedido(
        cliente_id="CLI-7890",
        productos=[
            {"sku": "LAPTOP-001", "nombre": "Laptop Pro 15", "cantidad": 1, "precio": 1200.00},
            {"sku": "MOUSE-003", "nombre": "Mouse Ergonómico", "cantidad": 2, "precio": 45.00}
        ],
        total=1290.00
    )

    # ─── Resultado final ─────────────────────────────────────────────
    print("\n" + "━" * 70)
    print("  📊 RESULTADO FINAL")
    print("━" * 70)
    print(f"  Total de eventos generados: {broker.total_eventos}")
    print(f"\n  Dashboard de Analytics:")
    for k, v in analytics_svc.dashboard.items():
        valor = f"${v:.2f}" if isinstance(v, float) else v
        print(f"     {k}: {valor}")

    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  FLUJO EJECUTADO (cascada de eventos):

  ACCIÓN INICIAL                    EVENTOS GENERADOS
  ─────────────                     ─────────────────
  Cliente compra ──→ 📨 PedidoCreado
                        ├──→ 📧 Email: confirmación de pedido
                        ├──→ 📦 Inventario: stock reservado
                        ├──→ 📊 Analytics: pedido registrado
                        └──→ 💳 Pagos: cobra al cliente
                                  │
                                  └──→ 📨 PagoRealizado
                                          ├──→ 📧 Email: recibo digital
                                          ├──→ 📊 Analytics: ingreso registrado
                                          ├──→ 🧾 Facturación: factura generada
                                          └──→ 🚚 Logística: envío preparado
                                                     │
                                                     └──→ 📨 EnvioPreparado
                                                             ├──→ 📧 Email: tracking enviado
                                                             └──→ 📊 Analytics: envío registrado

  UNA acción del cliente desencadenó {broker.total_eventos} eventos
  procesados por 6 servicios independientes, cada uno con su propia
  lógica de negocio, sin acoplamiento directo entre ellos.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)


if __name__ == "__main__":
    demo_sistema_completo()
