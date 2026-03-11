"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          PILAR 5: VENTAJAS OPERATIVAS                                      ║
║          Escalabilidad Elástica · Resiliencia · Aislamiento de Fallos      ║
╚══════════════════════════════════════════════════════════════════════════════╝

Una EDA no es solo un patrón de diseño: es una ESTRATEGIA OPERATIVA
que transforma la forma en que los sistemas crecen y resisten fallos.

    ┌──────────────────────────────────────────────────────────────────┐
    │  ESCALABILIDAD ELÁSTICA                                        │
    │  ─────────────────────                                         │
    │  Puedes añadir 10, 100 o 1000 consumidores sin tocar           │
    │  una sola línea de código del emisor.                          │
    │                                                                 │
    │  Antes: [Emisor] ──→ [Consumer A]                              │
    │  Ahora: [Emisor] ──→ [Consumer A]                              │
    │                   ──→ [Consumer B]  ← nuevo, sin cambios       │
    │                   ──→ [Consumer C]  ← nuevo, sin cambios       │
    │                                                                 │
    │  El emisor ni se entera. El broker se encarga.                 │
    ├──────────────────────────────────────────────────────────────────┤
    │  RESILIENCIA                                                    │
    │  ───────────                                                    │
    │  Si un consumidor falla, los demás siguen funcionando.         │
    │  El fallo está AISLADO. No se propaga.                         │
    │                                                                 │
    │  Monolito:   [A] → [B] → [C]  Si B falla → TODOS caen         │
    │  EDA:        [A] → Broker → [B] falla                          │
    │                           → [C] sigue OK ✓                    │
    │                           → [D] sigue OK ✓                    │
    └──────────────────────────────────────────────────────────────────┘
"""

import sys
import os
import threading
import time
import random
from typing import Callable
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _01_evento_unidad_de_verdad.evento import Evento


# ══════════════════════════════════════════════════════════════════════════════
# BROKER CON ESCALABILIDAD Y RESILIENCIA
# ══════════════════════════════════════════════════════════════════════════════

class BrokerElastico:
    """
    Broker que demuestra escalabilidad elástica y resiliencia.

    ESCALABILIDAD ELÁSTICA:
    - Los consumidores se registran y des-registran dinámicamente.
    - El emisor NUNCA cambia, sin importar cuántos consumidores haya.
    - El broker distribuye automáticamente a todos los suscritos.

    RESILIENCIA:
    - Si un consumidor falla, el broker captura el error.
    - Los demás consumidores NO se ven afectados.
    - El evento fallido se almacena en una Dead Letter Queue (DLQ).
    """

    def __init__(self, nombre: str):
        self.nombre = nombre
        self._suscripciones: dict[str, list[tuple[str, Callable]]] = defaultdict(list)
        self._dead_letter_queue: list[dict] = []
        self._metricas = {
            "eventos_publicados": 0,
            "entregas_exitosas": 0,
            "entregas_fallidas": 0,
            "consumidores_activos": 0
        }

    def suscribir(self, event_type: str, nombre: str, callback: Callable):
        """Añade un consumidor dinámicamente — escalabilidad elástica."""
        self._suscripciones[event_type].append((nombre, callback))
        self._metricas["consumidores_activos"] += 1
        return len(self._suscripciones[event_type])

    def desuscribir(self, event_type: str, nombre: str):
        """Remueve un consumidor dinámicamente."""
        subs = self._suscripciones[event_type]
        self._suscripciones[event_type] = [
            (n, cb) for n, cb in subs if n != nombre
        ]
        self._metricas["consumidores_activos"] -= 1

    def publicar(self, evento: Evento) -> dict:
        """
        Publica un evento con AISLAMIENTO DE FALLOS.
        Si un consumidor falla, los demás NO se afectan.
        """
        self._metricas["eventos_publicados"] += 1
        suscriptores = self._suscripciones.get(evento.event_type, [])
        resultados = {"exitosos": [], "fallidos": []}

        for nombre, callback in suscriptores:
            try:
                callback(evento)
                resultados["exitosos"].append(nombre)
                self._metricas["entregas_exitosas"] += 1
            except Exception as e:
                # ─── AISLAMIENTO DE FALLOS ────────────────────────
                # El error se captura. Los demás consumidores
                # NO se ven afectados.
                resultados["fallidos"].append(nombre)
                self._metricas["entregas_fallidas"] += 1
                self._dead_letter_queue.append({
                    "evento": evento.to_dict(),
                    "consumidor": nombre,
                    "error": str(e)
                })
                print(f"     ❌ [{nombre}] FALLÓ: {e}")
                print(f"        → Evento enviado a Dead Letter Queue")

        return resultados

    @property
    def metricas(self) -> dict:
        return dict(self._metricas)

    @property
    def dead_letter_count(self) -> int:
        return len(self._dead_letter_queue)


# ══════════════════════════════════════════════════════════════════════════════
# DEMOSTRACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def demo_ventajas_operativas():
    """
    Demuestra las ventajas operativas: escalabilidad y resiliencia.
    """
    print("=" * 70)
    print("  PILAR 5: VENTAJAS OPERATIVAS")
    print("=" * 70)

    broker = BrokerElastico("BrokerPrincipal")

    # ═══════════════════════════════════════════════════════════════════
    #  DEMO 1: ESCALABILIDAD ELÁSTICA
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "─" * 70)
    print("  DEMO 1: ESCALABILIDAD ELÁSTICA")
    print("  Añadir consumidores SIN modificar el emisor")
    print("─" * 70)

    # Fase 1: Solo 1 consumidor
    print("\n  📌 FASE 1: Un solo consumidor")
    broker.suscribir("CompraRealizada", "Email-v1",
                     lambda e: print(f"     📧 [Email-v1] Confirmación enviada"))

    evento = Evento("CompraRealizada", "tienda",
                     {"producto": "Laptop", "precio": 999.99})
    broker.publicar(evento)

    # Fase 2: Añadir 2 más sin tocar al emisor
    print(f"\n  📌 FASE 2: Añadimos 2 consumidores más (el emisor NO cambia)")
    broker.suscribir("CompraRealizada", "Inventario-v1",
                     lambda e: print(f"     📦 [Inventario] Stock actualizado"))
    broker.suscribir("CompraRealizada", "Analytics-v1",
                     lambda e: print(f"     📊 [Analytics] Venta registrada"))

    # El MISMO emisor, MISMO código, publica IGUAL
    evento2 = Evento("CompraRealizada", "tienda",
                      {"producto": "Teclado", "precio": 79.99})
    print(f"\n  Emisor publica (mismo código que antes):")
    broker.publicar(evento2)

    # Fase 3: Añadir aún más
    print(f"\n  📌 FASE 3: Añadimos 2 consumidores MÁS")
    broker.suscribir("CompraRealizada", "Recomendaciones",
                     lambda e: print(f"     🎯 [Recomendaciones] Perfil actualizado"))
    broker.suscribir("CompraRealizada", "Logística",
                     lambda e: print(f"     🚚 [Logística] Envío programado"))

    evento3 = Evento("CompraRealizada", "tienda",
                      {"producto": "Monitor", "precio": 450.00})
    print(f"\n  Emisor publica (MISMO código, CERO cambios):")
    broker.publicar(evento3)

    metricas = broker.metricas
    print(f"\n  📊 MÉTRICAS DE ESCALABILIDAD:")
    print(f"     Consumidores activos:   {metricas['consumidores_activos']}")
    print(f"     Eventos publicados:     {metricas['eventos_publicados']}")
    print(f"     Entregas exitosas:      {metricas['entregas_exitosas']}")
    print(f"     Cambios en el emisor:   0 (CERO)")

    # ═══════════════════════════════════════════════════════════════════
    #  DEMO 2: RESILIENCIA — Aislamiento de fallos
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "─" * 70)
    print("  DEMO 2: RESILIENCIA — Aislamiento de Fallos")
    print("  Un consumidor falla → Los demás siguen funcionando")
    print("─" * 70)

    broker_resiliente = BrokerElastico("BrokerResiliente")

    # Registrar 4 consumidores, uno de ellos fallará
    broker_resiliente.suscribir("PedidoPagado", "Email",
        lambda e: print(f"     📧 [Email] Recibo enviado ✓"))

    broker_resiliente.suscribir("PedidoPagado", "Inventario",
        lambda e: print(f"     📦 [Inventario] Stock descontado ✓"))

    # Este consumidor FALLA intencionalmente
    def consumidor_con_error(evento):
        raise ConnectionError("Servicio de facturación no disponible")

    broker_resiliente.suscribir("PedidoPagado", "Facturación",
                                 consumidor_con_error)

    broker_resiliente.suscribir("PedidoPagado", "Logística",
        lambda e: print(f"     🚚 [Logística] Envío programado ✓"))

    print("\n  Publicando evento (Facturación va a FALLAR):\n")
    resultado = broker_resiliente.publicar(
        Evento("PedidoPagado", "pagos",
               {"pedido_id": "PED-500", "monto": 299.99})
    )

    print(f"\n  📊 RESULTADO DEL AISLAMIENTO:")
    print(f"     ✅ Consumidores exitosos: {resultado['exitosos']}")
    print(f"     ❌ Consumidores fallidos:  {resultado['fallidos']}")
    print(f"     📭 Dead Letter Queue:     {broker_resiliente.dead_letter_count} evento(s)")

    # ═══════════════════════════════════════════════════════════════════
    #  COMPARATIVA: MONOLITO vs EDA
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  COMPARATIVA: MONOLITO vs EDA")
    print("=" * 70)
    print("""
    MONOLITO (Arquitectura Acoplada):
    ┌─────────────────────────────────────────────────────┐
    │  procesar_pedido():                                 │
    │    cobrar_pago()          ← Si falla, TODO falla    │
    │    actualizar_inventario()← acoplamiento directo    │
    │    enviar_email()         ← cambios requieren       │
    │    generar_factura()      ← redeployar TODO         │
    │    notificar_logistica()                             │
    │                                                      │
    │  Añadir analytics → MODIFICAR procesar_pedido()     │
    │  Si email falla   → SE PIERDE el pedido             │
    └─────────────────────────────────────────────────────┘

    EDA (Arquitectura Orientada a Eventos):
    ┌─────────────────────────────────────────────────────┐
    │  [Servicio Pedidos]                                  │
    │    → Emite "PedidoCreado" y CONTINÚA                │
    │                                                      │
    │  [Broker]                                            │
    │    → 📧 Email: recibe y procesa independientemente   │
    │    → 📦 Inventario: procesa independientemente       │
    │    → 🧾 Facturación: FALLA → Dead Letter Queue      │
    │    → 🚚 Logística: procesa independientemente       │
    │    → 📊 Analytics: ← AÑADIDO sin tocar el emisor    │
    │                                                      │
    │  Añadir analytics → SUSCRIBIR al topic. ✓           │
    │  Si email falla   → Los demás siguen OK. ✓          │
    └─────────────────────────────────────────────────────┘

    RESUMEN DE VENTAJAS:
    ┌────────────────────┬───────────────┬───────────────────┐
    │ Aspecto            │ Monolito      │ EDA               │
    ├────────────────────┼───────────────┼───────────────────┤
    │ Escalar            │ Todo o nada   │ Por servicio      │
    │ Añadir feature     │ Redeployar    │ Suscribir nuevo   │
    │ Fallo parcial      │ Fallo total   │ Fallo aislado     │
    │ Acoplamiento       │ Alto          │ Mínimo            │
    │ Deploy independ.   │ No            │ Sí                │
    └────────────────────┴───────────────┴───────────────────┘
    """)


if __name__ == "__main__":
    demo_ventajas_operativas()
