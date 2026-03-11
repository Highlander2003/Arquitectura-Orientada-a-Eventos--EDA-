"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          PILAR 1: EL EVENTO COMO UNIDAD DE VERDAD                          ║
║          Definición, estructura y naturaleza inmutable                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

Un EVENTO es un registro inmutable de algo que YA OCURRIÓ en el sistema.
No es una petición, no es un comando: es un HECHO consumado.

Ejemplo del mundo real:
    - "El usuario #4521 realizó una compra por $150.00"  ← EVENTO (hecho)
    - "Procesar el pago del usuario #4521"               ← COMANDO (orden)

La diferencia es fundamental: un evento no se puede rechazar ni modificar,
porque describe algo que ya pasó. Es la VERDAD del sistema en ese instante.

ESTRUCTURA DEL MENSAJE:
    ┌─────────────────────────────────────────┐
    │             ENCABEZADO (Header)          │
    │  ─────────────────────────────────────── │
    │  • event_id     → Identificador único    │
    │  • event_type   → Tipo/categoría         │
    │  • timestamp    → Cuándo ocurrió         │
    │  • source       → Quién lo generó        │
    │  • version      → Versión del esquema    │
    │  • correlation_id → Trazabilidad         │
    ├─────────────────────────────────────────┤
    │             CUERPO (Payload)             │
    │  ─────────────────────────────────────── │
    │  • Datos específicos del evento          │
    │  • El "qué pasó" con todo su detalle     │
    │  • Información necesaria para que los    │
    │    consumidores reaccionen               │
    └─────────────────────────────────────────┘
"""

import uuid
import json
from datetime import datetime, timezone


class Evento:
    """
    Clase base inmutable que representa un evento en el sistema.

    Un evento tiene dos partes fundamentales:
    1. ENCABEZADO (Header): Metadatos que contextualizan el evento.
       - ¿Quién lo generó? ¿Cuándo? ¿De qué tipo es?
    2. CUERPO (Payload): La carga útil con los datos del suceso.
       - ¿Qué pasó exactamente? ¿Con qué datos?

    INMUTABILIDAD: Una vez creado, un evento NO se modifica.
    Si algo cambió, se crea un NUEVO evento que refleja ese cambio.
    """

    def __init__(self, event_type: str, source: str, payload: dict,
                 version: str = "1.0", correlation_id: str = None):
        # ══════════════════════════════════════════════════════════════
        # ENCABEZADO (Header) — Metadatos del evento
        # ══════════════════════════════════════════════════════════════
        self._event_id = str(uuid.uuid4())  # ID único e irrepetible
        self._event_type = event_type        # Ej: "PedidoCreado", "PagoRealizado"
        self._timestamp = datetime.now(timezone.utc).isoformat()  # Momento exacto
        self._source = source                # Servicio que lo originó
        self._version = version              # Versión del esquema del evento
        self._correlation_id = correlation_id or str(uuid.uuid4())  # Para trazabilidad

        # ══════════════════════════════════════════════════════════════
        # CUERPO (Payload) — Los datos del suceso
        # ══════════════════════════════════════════════════════════════
        self._payload = dict(payload)  # Copia defensiva para inmutabilidad

    # ─── Propiedades de solo lectura (garantizan inmutabilidad) ───────

    @property
    def event_id(self) -> str:
        return self._event_id

    @property
    def event_type(self) -> str:
        return self._event_type

    @property
    def timestamp(self) -> str:
        return self._timestamp

    @property
    def source(self) -> str:
        return self._source

    @property
    def version(self) -> str:
        return self._version

    @property
    def correlation_id(self) -> str:
        return self._correlation_id

    @property
    def payload(self) -> dict:
        return dict(self._payload)  # Devuelve copia, no la referencia original

    # ─── Representaciones ─────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serializa el evento completo a un diccionario."""
        return {
            "header": {
                "event_id": self._event_id,
                "event_type": self._event_type,
                "timestamp": self._timestamp,
                "source": self._source,
                "version": self._version,
                "correlation_id": self._correlation_id,
            },
            "body": self._payload
        }

    def to_json(self) -> str:
        """Serializa el evento a JSON (formato de transporte estándar)."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def __repr__(self) -> str:
        return (f"Evento(type={self._event_type}, id={self._event_id[:8]}..., "
                f"source={self._source})")

    def __str__(self) -> str:
        return self.to_json()


# ══════════════════════════════════════════════════════════════════════════════
# EVENTOS ESPECÍFICOS DEL DOMINIO
# Cada tipo de evento hereda de Evento y define su estructura de payload
# ══════════════════════════════════════════════════════════════════════════════

class PedidoCreado(Evento):
    """Evento: Un nuevo pedido fue creado en el sistema."""

    def __init__(self, pedido_id: str, cliente_id: str,
                 productos: list, total: float, **kwargs):
        super().__init__(
            event_type="PedidoCreado",
            source="servicio-pedidos",
            payload={
                "pedido_id": pedido_id,
                "cliente_id": cliente_id,
                "productos": productos,
                "total": total,
                "moneda": "USD"
            },
            **kwargs
        )


class PagoRealizado(Evento):
    """Evento: Un pago fue procesado exitosamente."""

    def __init__(self, pedido_id: str, monto: float,
                 metodo_pago: str, **kwargs):
        super().__init__(
            event_type="PagoRealizado",
            source="servicio-pagos",
            payload={
                "pedido_id": pedido_id,
                "monto": monto,
                "metodo_pago": metodo_pago,
                "estado": "completado"
            },
            **kwargs
        )


class InventarioActualizado(Evento):
    """Evento: El inventario fue modificado tras un pedido."""

    def __init__(self, producto_id: str, cantidad_anterior: int,
                 cantidad_nueva: int, razon: str, **kwargs):
        super().__init__(
            event_type="InventarioActualizado",
            source="servicio-inventario",
            payload={
                "producto_id": producto_id,
                "cantidad_anterior": cantidad_anterior,
                "cantidad_nueva": cantidad_nueva,
                "razon": razon
            },
            **kwargs
        )


# ══════════════════════════════════════════════════════════════════════════════
# DEMOSTRACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def demo_evento_como_unidad_de_verdad():
    """
    Demuestra la creación de eventos inmutables y su estructura.
    """
    print("=" * 70)
    print("  PILAR 1: EL EVENTO COMO UNIDAD DE VERDAD")
    print("=" * 70)

    # ─── Crear un evento de dominio ──────────────────────────────────
    evento = PedidoCreado(
        pedido_id="PED-2025-001",
        cliente_id="CLI-4521",
        productos=[
            {"sku": "LAPTOP-001", "nombre": "Laptop Pro 15", "cantidad": 1, "precio": 1200.00},
            {"sku": "MOUSE-003", "nombre": "Mouse Ergonómico", "cantidad": 2, "precio": 45.00}
        ],
        total=1290.00
    )

    print("\n📦 Evento creado: Pedido Nuevo")
    print("-" * 50)
    print(f"  Tipo:           {evento.event_type}")
    print(f"  ID:             {evento.event_id}")
    print(f"  Timestamp:      {evento.timestamp}")
    print(f"  Origen:         {evento.source}")
    print(f"  Versión:        {evento.version}")
    print(f"  Correlation ID: {evento.correlation_id}")
    print(f"\n  Payload (Cuerpo):")
    for clave, valor in evento.payload.items():
        print(f"    {clave}: {valor}")

    # ─── Demostrar inmutabilidad ─────────────────────────────────────
    print("\n🔒 DEMOSTRACIÓN DE INMUTABILIDAD:")
    print("-" * 50)

    try:
        evento.event_type = "EventoModificado"
    except AttributeError:
        print("  ✓ No se puede modificar event_type → El evento es inmutable")

    payload_copia = evento.payload
    payload_copia["total"] = 0.00  # Modificar la copia
    print(f"  ✓ Payload original intacto → total = {evento.payload['total']}")
    print(f"    (La copia modificada tiene total = {payload_copia['total']})")

    # ─── Evento como JSON (formato de transporte) ────────────────────
    print("\n📨 EVENTO SERIALIZADO (JSON - formato de transporte):")
    print("-" * 50)
    print(evento.to_json())

    # ─── Cadena de eventos (la historia del sistema) ─────────────────
    print("\n📜 CADENA DE EVENTOS (Historia del Pedido PED-2025-001):")
    print("-" * 50)

    correlation = evento.correlation_id

    eventos_cadena = [
        evento,
        PagoRealizado(
            pedido_id="PED-2025-001",
            monto=1290.00,
            metodo_pago="tarjeta_credito",
            correlation_id=correlation
        ),
        InventarioActualizado(
            producto_id="LAPTOP-001",
            cantidad_anterior=50,
            cantidad_nueva=49,
            razon="Venta PED-2025-001",
            correlation_id=correlation
        ),
        InventarioActualizado(
            producto_id="MOUSE-003",
            cantidad_anterior=200,
            cantidad_nueva=198,
            razon="Venta PED-2025-001",
            correlation_id=correlation
        ),
    ]

    for i, ev in enumerate(eventos_cadena, 1):
        print(f"  {i}. [{ev.event_type}] desde '{ev.source}' "
              f"@ {ev.timestamp[:19]}")

    print(f"\n  → Todos comparten correlation_id: {correlation[:8]}...")
    print("    (Esto permite rastrear todo el flujo de un pedido)")

    print("\n" + "=" * 70)
    print("  CONCEPTO CLAVE: Un evento es un HECHO INMUTABLE.")
    print("  No se negocia, no se rechaza, no se modifica.")
    print("  Si algo cambió, se emite un NUEVO evento.")
    print("=" * 70)

    return eventos_cadena


if __name__ == "__main__":
    demo_evento_como_unidad_de_verdad()
