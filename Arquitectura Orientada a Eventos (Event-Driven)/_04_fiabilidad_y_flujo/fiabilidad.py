"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          PILAR 4: CONCEPTOS DE FIABILIDAD Y FLUJO                          ║
║          Persistencia · Idempotencia · Event Sourcing                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

La EDA no solo es elegante: debe ser CONFIABLE.
¿Qué pasa si un servicio se cae? ¿Y si un evento se procesa dos veces?
¿Podemos reconstruir el estado del sistema?

    ┌──────────────────────────────────────────────────────────────────┐
    │  TRES PILARES DE FIABILIDAD:                                    │
    │                                                                  │
    │  1. PERSISTENCIA Y DURABILIDAD                                  │
    │     → Los eventos se almacenan en disco/DB antes de             │
    │       distribuirse. Si un consumidor está caído, el evento      │
    │       lo esperará en la cola.                                   │
    │                                                                  │
    │  2. IDEMPOTENCIA                                                │
    │     → Procesar el mismo evento 1 vez o 10 veces produce        │
    │       el MISMO resultado. No hay efectos colaterales.           │
    │                                                                  │
    │  3. EVENT SOURCING (Event Store)                                │
    │     → En lugar de guardar solo el estado actual, guardamos      │
    │       TODA la secuencia de eventos. El estado se RECONSTRUYE    │
    │       "reproduciendo" los eventos desde el inicio.              │
    └──────────────────────────────────────────────────────────────────┘
"""

import sys
import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _01_evento_unidad_de_verdad.evento import Evento


# ══════════════════════════════════════════════════════════════════════════════
# 1. PERSISTENCIA Y DURABILIDAD
# ══════════════════════════════════════════════════════════════════════════════

class BrokerPersistente:
    """
    Broker con persistencia: los eventos sobreviven a caídas del sistema.

    ¿POR QUÉ ES NECESARIO?
    ────────────────────────────────────────────────────────
    Sin persistencia:
        Emisor → Broker (en memoria) → Consumidor CAÍDO
                         ↓
                  Evento PERDIDO para siempre ❌

    Con persistencia:
        Emisor → Broker → [Disco/DB] → Consumidor CAÍDO
                                ↓
                  Consumidor se recupera → Lee el evento ✓
    ────────────────────────────────────────────────────────

    Tecnologías reales:
    - Apache Kafka: retiene eventos en disco por días/semanas
    - RabbitMQ con persistencia activada
    - Amazon SQS: retiene mensajes hasta 14 días
    """

    def __init__(self, archivo_log: str = None):
        self._archivo_log = archivo_log
        self._eventos: list[dict] = []
        self._consumidores_caidos: set[str] = set()
        self._pendientes_entrega: dict[str, list[Evento]] = {}

    def publicar(self, evento: Evento):
        """Persiste el evento ANTES de intentar distribuirlo."""
        evento_dict = evento.to_dict()
        self._eventos.append(evento_dict)

        # Persistir en archivo (simula escritura a disco)
        if self._archivo_log:
            with open(self._archivo_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(evento_dict, ensure_ascii=False) + "\n")

        print(f"  💾 Broker: Evento '{evento.event_type}' persistido "
              f"(total: {len(self._eventos)})")

        return evento_dict

    def simular_caida_consumidor(self, nombre_consumidor: str):
        """Simula que un consumidor se cae."""
        self._consumidores_caidos.add(nombre_consumidor)
        print(f"  💥 Consumidor '{nombre_consumidor}' se ha CAÍDO")

    def simular_recuperacion(self, nombre_consumidor: str):
        """El consumidor se recupera y recibe los eventos pendientes."""
        if nombre_consumidor in self._consumidores_caidos:
            self._consumidores_caidos.remove(nombre_consumidor)
            pendientes = self._pendientes_entrega.get(nombre_consumidor, [])
            print(f"  ✅ Consumidor '{nombre_consumidor}' RECUPERADO. "
                  f"Eventos pendientes: {len(pendientes)}")
            return pendientes
        return []

    def entregar(self, nombre_consumidor: str, evento: Evento) -> bool:
        """Intenta entregar un evento a un consumidor."""
        if nombre_consumidor in self._consumidores_caidos:
            if nombre_consumidor not in self._pendientes_entrega:
                self._pendientes_entrega[nombre_consumidor] = []
            self._pendientes_entrega[nombre_consumidor].append(evento)
            print(f"  ⏳ Evento guardado en cola de pendientes para "
                  f"'{nombre_consumidor}'")
            return False
        return True

    @property
    def total_persistidos(self) -> int:
        return len(self._eventos)


# ══════════════════════════════════════════════════════════════════════════════
# 2. IDEMPOTENCIA
# ══════════════════════════════════════════════════════════════════════════════

class ProcesadorIdempotente:
    """
    Procesador que garantiza IDEMPOTENCIA.

    ¿QUÉ ES IDEMPOTENCIA?
    ────────────────────────────────────────────────────────
    Una operación es idempotente si ejecutarla 1 vez o N veces
    produce el MISMO resultado sin efectos colaterales.

    Ejemplo IDEMPOTENTE:
        "Establecer el precio del producto #5 a $100"
        → 1 vez: precio = $100
        → 3 veces: precio = $100 (mismo resultado ✓)

    Ejemplo NO IDEMPOTENTE:
        "Sumar $10 al saldo del usuario"
        → 1 vez: saldo = $110
        → 3 veces: saldo = $130 (¡efecto acumulativo! ❌)

    ¿POR QUÉ ES NECESARIO EN EDA?
    Porque los mensajes pueden llegar DUPLICADOS:
    - Reintentos por timeout de red
    - Rebalanceo de particiones en Kafka
    - At-least-once delivery (entrega al menos una vez)
    ────────────────────────────────────────────────────────

    ESTRATEGIA: Almacenar el ID de cada evento procesado.
    Si el ID ya existe, se ignora el duplicado.
    """

    def __init__(self, nombre: str):
        self.nombre = nombre
        self._eventos_procesados: set[str] = set()  # IDs ya procesados
        self._resultados: dict[str, str] = {}
        self.total_intentos = 0
        self.total_procesados_reales = 0
        self.total_duplicados_ignorados = 0

    def procesar(self, evento: Evento) -> bool:
        """
        Procesa un evento de forma idempotente.
        Si ya fue procesado antes (mismo event_id), lo ignora.
        """
        self.total_intentos += 1

        # Verificar si ya procesamos este evento
        if evento.event_id in self._eventos_procesados:
            self.total_duplicados_ignorados += 1
            print(f"  🔄 [{self.nombre}] Evento {evento.event_id[:8]}... "
                  f"YA PROCESADO → Ignorando duplicado")
            return False

        # Procesar por primera vez
        self._eventos_procesados.add(evento.event_id)
        self.total_procesados_reales += 1

        resultado = f"Procesado: {evento.event_type} @ {datetime.now(timezone.utc).isoformat()}"
        self._resultados[evento.event_id] = resultado

        print(f"  ✅ [{self.nombre}] Evento {evento.event_id[:8]}... "
              f"procesado por PRIMERA VEZ")
        return True

    def estadisticas(self) -> dict:
        return {
            "intentos_totales": self.total_intentos,
            "procesados_reales": self.total_procesados_reales,
            "duplicados_ignorados": self.total_duplicados_ignorados
        }


# ══════════════════════════════════════════════════════════════════════════════
# 3. EVENT STORE / EVENT SOURCING
# ══════════════════════════════════════════════════════════════════════════════

class EventStore:
    """
    Event Store: almacena el HISTORIAL COMPLETO de eventos.

    ¿QUÉ ES EVENT SOURCING?
    ────────────────────────────────────────────────────────
    En lugar de guardar solo el ESTADO ACTUAL de una entidad,
    guardamos TODOS LOS EVENTOS que la modificaron.

    Estado actual = Replay de todos los eventos desde el inicio.

    Modelo TRADICIONAL (CRUD):
        Base de datos: { cuenta: "001", saldo: 150 }
        → Solo sabemos el saldo actual
        → ¿Cómo llegamos a 150? No lo sabemos

    Modelo EVENT SOURCING:
        Event Store:
          1. CuentaCreada     → saldo = 0
          2. DepósitoRealizado → saldo = 200
          3. RetiroRealizado   → saldo = 150
        → Sabemos el estado actual Y toda la historia
        → Podemos "viajar en el tiempo"
    ────────────────────────────────────────────────────────

    Ventajas:
    - Auditoría completa (quién hizo qué y cuándo)
    - Debug de incidentes (reproducir lo que pasó)
    - Reconstruir estados pasados
    - Crear nuevas "vistas" reproduciendo eventos
    """

    def __init__(self):
        self._streams: dict[str, list[dict]] = {}

    def append(self, stream_id: str, evento: Evento):
        """Añade un evento al stream (secuencia) de una entidad."""
        if stream_id not in self._streams:
            self._streams[stream_id] = []

        entrada = {
            "secuencia": len(self._streams[stream_id]) + 1,
            "evento": evento.to_dict(),
            "almacenado_en": datetime.now(timezone.utc).isoformat()
        }
        self._streams[stream_id].append(entrada)

    def get_stream(self, stream_id: str) -> list[dict]:
        """Obtiene todos los eventos de un stream."""
        return self._streams.get(stream_id, [])

    def replay(self, stream_id: str, estado_inicial: dict = None) -> dict:
        """
        REPLAY: Reconstruye el estado actual reproduciendo
        todos los eventos desde el inicio.

        Este es el corazón del Event Sourcing.
        """
        estado = estado_inicial or {}
        eventos = self.get_stream(stream_id)

        for entrada in eventos:
            body = entrada["evento"]["body"]
            event_type = entrada["evento"]["header"]["event_type"]

            # Aplicar cada evento al estado
            if event_type == "CuentaCreada":
                estado = {
                    "cuenta_id": body["cuenta_id"],
                    "titular": body["titular"],
                    "saldo": 0.0,
                    "estado": "activa"
                }
            elif event_type == "DepositoRealizado":
                estado["saldo"] = estado.get("saldo", 0) + body["monto"]
            elif event_type == "RetiroRealizado":
                estado["saldo"] = estado.get("saldo", 0) - body["monto"]
            elif event_type == "CuentaBloqueada":
                estado["estado"] = "bloqueada"

        return estado

    def replay_hasta(self, stream_id: str, secuencia: int) -> dict:
        """
        Replay PARCIAL: reconstruye el estado hasta un punto
        específico en el tiempo. ¡Viaje en el tiempo!
        """
        estado = {}
        eventos = self.get_stream(stream_id)

        for entrada in eventos:
            if entrada["secuencia"] > secuencia:
                break

            body = entrada["evento"]["body"]
            event_type = entrada["evento"]["header"]["event_type"]

            if event_type == "CuentaCreada":
                estado = {
                    "cuenta_id": body["cuenta_id"],
                    "titular": body["titular"],
                    "saldo": 0.0,
                    "estado": "activa"
                }
            elif event_type == "DepositoRealizado":
                estado["saldo"] = estado.get("saldo", 0) + body["monto"]
            elif event_type == "RetiroRealizado":
                estado["saldo"] = estado.get("saldo", 0) - body["monto"]
            elif event_type == "CuentaBloqueada":
                estado["estado"] = "bloqueada"

        return estado

    @property
    def total_streams(self) -> int:
        return len(self._streams)

    @property
    def total_eventos(self) -> int:
        return sum(len(s) for s in self._streams.values())


# ══════════════════════════════════════════════════════════════════════════════
# DEMOSTRACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def demo_fiabilidad_y_flujo():
    """
    Demuestra los tres mecanismos de fiabilidad: Persistencia,
    Idempotencia y Event Sourcing.
    """
    print("=" * 70)
    print("  PILAR 4: CONCEPTOS DE FIABILIDAD Y FLUJO")
    print("=" * 70)

    # ═══════════════════════════════════════════════════════════════════
    #  DEMO 1: PERSISTENCIA — Eventos sobreviven a caídas
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "─" * 70)
    print("  DEMO 1: PERSISTENCIA Y DURABILIDAD")
    print("  Los eventos no se pierden aunque un consumidor se caiga")
    print("─" * 70)

    broker = BrokerPersistente()

    # Publicar un evento
    evento1 = Evento("PedidoCreado", "servicio-pedidos",
                      {"pedido_id": "PED-001", "total": 250.00})
    broker.publicar(evento1)

    # Simular que el consumidor de email se cae
    broker.simular_caida_consumidor("Servicio-Email")

    # Publicar más eventos mientras el consumidor está caído
    evento2 = Evento("PedidoCreado", "servicio-pedidos",
                      {"pedido_id": "PED-002", "total": 175.50})
    broker.publicar(evento2)
    broker.entregar("Servicio-Email", evento2)

    evento3 = Evento("PagoRealizado", "servicio-pagos",
                      {"pedido_id": "PED-001", "monto": 250.00})
    broker.publicar(evento3)
    broker.entregar("Servicio-Email", evento3)

    print(f"\n  📊 Eventos persistidos en el broker: {broker.total_persistidos}")

    # El consumidor se recupera
    pendientes = broker.simular_recuperacion("Servicio-Email")
    print(f"  📨 Eventos entregados tras recuperación: {len(pendientes)}")
    for ev in pendientes:
        print(f"     → {ev.event_type}: {ev.payload}")

    # ═══════════════════════════════════════════════════════════════════
    #  DEMO 2: IDEMPOTENCIA — Mismo evento procesado N veces = 1 vez
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "─" * 70)
    print("  DEMO 2: IDEMPOTENCIA")
    print("  Procesar el mismo evento N veces = procesarlo 1 vez")
    print("─" * 70)

    procesador = ProcesadorIdempotente("Servicio-Pagos")
    evento_pago = Evento("ProcesarPago", "gateway-pagos",
                          {"pedido_id": "PED-001", "monto": 100.00})

    print(f"\n  Enviando el MISMO evento 5 veces (simulando reintentos):")
    for i in range(1, 6):
        print(f"\n  Intento {i}:")
        procesador.procesar(evento_pago)

    stats = procesador.estadisticas()
    print(f"\n  📊 ESTADÍSTICAS DE IDEMPOTENCIA:")
    print(f"     Intentos totales:        {stats['intentos_totales']}")
    print(f"     Procesados realmente:    {stats['procesados_reales']}")
    print(f"     Duplicados ignorados:    {stats['duplicados_ignorados']}")
    print(f"\n  ✓ El pago se cobró UNA sola vez, aunque llegó 5 veces")

    # ═══════════════════════════════════════════════════════════════════
    #  DEMO 3: EVENT SOURCING — Reconstruir estados desde eventos
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "─" * 70)
    print("  DEMO 3: EVENT SOURCING (Event Store)")
    print("  Reconstruir el estado completo desde el historial de eventos")
    print("─" * 70)

    store = EventStore()
    cuenta_id = "CUENTA-001"

    # Simular la vida de una cuenta bancaria mediante eventos
    eventos_cuenta = [
        Evento("CuentaCreada", "servicio-cuentas",
               {"cuenta_id": cuenta_id, "titular": "María García"}),
        Evento("DepositoRealizado", "servicio-transacciones",
               {"cuenta_id": cuenta_id, "monto": 1000.00, "concepto": "Nómina enero"}),
        Evento("RetiroRealizado", "servicio-transacciones",
               {"cuenta_id": cuenta_id, "monto": 200.00, "concepto": "Compra supermercado"}),
        Evento("DepositoRealizado", "servicio-transacciones",
               {"cuenta_id": cuenta_id, "monto": 500.00, "concepto": "Nómina febrero"}),
        Evento("RetiroRealizado", "servicio-transacciones",
               {"cuenta_id": cuenta_id, "monto": 150.00, "concepto": "Pago servicios"}),
        Evento("CuentaBloqueada", "servicio-seguridad",
               {"cuenta_id": cuenta_id, "razon": "Actividad sospechosa"}),
    ]

    print(f"\n  📝 Almacenando {len(eventos_cuenta)} eventos en el Event Store:")
    for ev in eventos_cuenta:
        store.append(cuenta_id, ev)
        print(f"     #{store.get_stream(cuenta_id)[-1]['secuencia']} "
              f"- {ev.event_type}: {ev.payload}")

    # Replay: reconstruir estado actual
    print(f"\n  🔄 REPLAY COMPLETO → Estado actual:")
    estado_actual = store.replay(cuenta_id)
    for clave, valor in estado_actual.items():
        print(f"     {clave}: {valor}")

    # Replay parcial: viaje en el tiempo
    print(f"\n  ⏰ VIAJE EN EL TIEMPO → Estado después del evento #3:")
    estado_pasado = store.replay_hasta(cuenta_id, 3)
    for clave, valor in estado_pasado.items():
        print(f"     {clave}: {valor}")

    print(f"\n  ⏰ VIAJE EN EL TIEMPO → Estado después del evento #4:")
    estado_medio = store.replay_hasta(cuenta_id, 4)
    for clave, valor in estado_medio.items():
        print(f"     {clave}: {valor}")

    # Resumen
    print("\n" + "=" * 70)
    print("  RESUMEN DE FIABILIDAD")
    print("=" * 70)
    print("""
    ┌──────────────────────┬───────────────────────────────────────┐
    │ Concepto             │ Garantía                              │
    ├──────────────────────┼───────────────────────────────────────┤
    │ PERSISTENCIA         │ Un evento NUNCA se pierde, incluso   │
    │                      │ si el consumidor está caído.          │
    ├──────────────────────┼───────────────────────────────────────┤
    │ IDEMPOTENCIA         │ Procesar el mismo evento N veces     │
    │                      │ produce el MISMO resultado.           │
    ├──────────────────────┼───────────────────────────────────────┤
    │ EVENT SOURCING       │ El historial completo permite        │
    │                      │ reconstruir cualquier estado pasado.  │
    └──────────────────────┴───────────────────────────────────────┘
    """)

    return store


if __name__ == "__main__":
    demo_fiabilidad_y_flujo()
