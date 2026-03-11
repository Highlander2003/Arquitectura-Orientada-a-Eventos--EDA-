# Arquitectura Orientada a Eventos (Event-Driven Architecture)

## Guía Completa con Código Funcional en Python

> **Perspectiva**: Arquitecto de Soluciones Senior  
> **Tecnología**: Python 3.10+ (solo biblioteca estándar, sin dependencias externas)

---

## Visión General

Una **Arquitectura Orientada a Eventos (EDA)** es un patrón de diseño de software donde el flujo del programa es determinado por **eventos** — registros inmutables de hechos que ya ocurrieron en el sistema.

```
  [Acción del usuario] ──→ 📨 Evento
                                │
                      ┌─────────┼─────────┐
                      ▼         ▼         ▼
                   📧 Email  📦 Stock  📊 Analytics
                                │
                                ▼
                          📨 Nuevo Evento (cascada)
                                │
                          ┌─────┼─────┐
                          ▼     ▼     ▼
                       🧾 Fact. 🚚 Envío 📧 Recibo
```

**Una acción** desencadena **múltiples reacciones** de forma asíncrona, desacoplada y resiliente.

---

## Estructura del Proyecto

```
📁 Arquitectura Orientada a Eventos (Event-Driven)/
│
├── 📄 ejecutar_demos.py              ← Punto de entrada principal
├── 📄 requirements.txt
├── 📄 README.md
│
├── 📁 _01_evento_unidad_de_verdad/   ← Pilar 1: El Evento
│   ├── __init__.py
│   └── evento.py                      ← Clase Evento inmutable
│
├── 📁 _02_roles_y_responsabilidades/ ← Pilar 2: Los Actores
│   ├── __init__.py
│   └── actores.py                     ← Emisor, Consumidor, Broker
│
├── 📁 _03_mecanismos_comunicacion/   ← Pilar 3: Comunicación
│   ├── __init__.py
│   └── comunicacion.py                ← Pub/Sub vs Colas
│
├── 📁 _04_fiabilidad_y_flujo/        ← Pilar 4: Fiabilidad
│   ├── __init__.py
│   └── fiabilidad.py                  ← Persistencia, Idempotencia, Event Sourcing
│
├── 📁 _05_ventajas_operativas/       ← Pilar 5: Ventajas
│   ├── __init__.py
│   └── ventajas.py                    ← Escalabilidad y Resiliencia
│
└── 📁 sistema_completo/              ← Integración de todos los pilares
    ├── __init__.py
    └── ecommerce_eda.py               ← Simulación E-Commerce completa
```

---

## Cómo Ejecutar

```bash
# Ejecutar TODAS las demos secuencialmente
python ejecutar_demos.py todos

# Ejecutar un pilar específico
python ejecutar_demos.py 1        # Solo Pilar 1
python ejecutar_demos.py 3        # Solo Pilar 3
python ejecutar_demos.py 1 3 5    # Pilares 1, 3 y 5

# Ejecutar la simulación completa del e-commerce
python ejecutar_demos.py sistema

# Menú interactivo
python ejecutar_demos.py
```

---

## Los 5 Pilares de la EDA

### Pilar 1: El Evento como Unidad de Verdad

Un **evento** es un registro **inmutable** de algo que **ya ocurrió**. No es una petición ni un comando — es un **hecho consumado**.

```
┌─────────────────────────────────────────┐
│             ENCABEZADO (Header)          │
│  • event_id      → ID único              │
│  • event_type    → "PedidoCreado"        │
│  • timestamp     → Cuándo ocurrió        │
│  • source        → Quién lo generó       │
│  • correlation_id → Trazabilidad         │
├─────────────────────────────────────────┤
│             CUERPO (Payload)             │
│  • pedido_id, cliente_id, productos...   │
│  • Todo lo necesario para reaccionar     │
└─────────────────────────────────────────┘
```

**Archivo**: `_01_evento_unidad_de_verdad/evento.py`

---

### Pilar 2: Roles y Responsabilidades

```
  ┌──────────┐      ┌──────────────┐      ┌────────────┐
  │  EMISOR  │ ───→ │    BROKER    │ ───→ │ CONSUMIDOR │
  │(Producer)│      │(Event Broker)│      │ (Consumer) │
  └──────────┘      └──────────────┘      └────────────┘
```

| Actor | Responsabilidad |
|-------|----------------|
| **Emisor** | Detecta un suceso, publica el evento. NO conoce a los consumidores. |
| **Broker** | Recibe, persiste, enruta y distribuye eventos. |
| **Consumidor** | Se suscribe a tipos de eventos y reacciona con su lógica de negocio. |

**Principio clave**: El emisor NO conoce al consumidor. Solo el Broker los conecta.

**Archivo**: `_02_roles_y_responsabilidades/actores.py`

---

### Pilar 3: Mecanismos de Comunicación

| Mecanismo | Modelo | Entrega | Caso de Uso |
|-----------|--------|---------|-------------|
| **Pub/Sub** | One-to-Many | Todos los suscriptores reciben copia | Notificar a múltiples servicios |
| **Cola** | Point-to-Point | Solo un worker procesa cada mensaje | Distribuir tareas sin duplicar |

```
Pub/Sub:   Emisor → [Topic] → Suscriptor A, B, C (todos reciben)
Cola:      Emisor → [Cola]  → Worker A toma msg 1, B toma msg 2...
```

**Archivo**: `_03_mecanismos_comunicacion/comunicacion.py`

---

### Pilar 4: Fiabilidad y Flujo

| Concepto | Garantía |
|----------|----------|
| **Persistencia** | Los eventos se almacenan en disco antes de distribuirse. Si un consumidor cae, el evento lo espera. |
| **Idempotencia** | Procesar el mismo evento N veces = procesarlo 1 vez. Sin efectos colaterales. |
| **Event Sourcing** | Se almacena el historial completo de eventos. El estado actual se reconstruye mediante "replay". |

**Archivo**: `_04_fiabilidad_y_flujo/fiabilidad.py`

---

### Pilar 5: Ventajas Operativas

| Ventaja | Descripción |
|---------|-------------|
| **Escalabilidad Elástica** | Añadir 100 consumidores nuevos sin cambiar una línea del emisor. |
| **Resiliencia** | Si un consumidor falla, los demás siguen funcionando. El fallo está aislado. |
| **Dead Letter Queue** | Los mensajes fallidos se almacenan para reprocesamiento posterior. |

```
Monolito:  [A] → [B] → [C]  → Si B falla → TODOS caen
EDA:       [A] → Broker → [B] falla
                        → [C] sigue OK ✓
                        → [D] sigue OK ✓
```

**Archivo**: `_05_ventajas_operativas/ventajas.py`

---

## Sistema Completo: E-Commerce

La simulación integra **7 microservicios independientes** que se comunican exclusivamente mediante eventos:

```
  Cliente compra ──→ 📨 PedidoCreado
                        ├──→ 📧 Email: confirmación
                        ├──→ 📦 Inventario: reserva stock
                        ├──→ 📊 Analytics: registra pedido
                        └──→ 💳 Pagos: procesa cobro
                                  └──→ 📨 PagoRealizado
                                          ├──→ 📧 Email: recibo
                                          ├──→ 📊 Analytics: ingreso
                                          ├──→ 🧾 Facturación: genera PDF
                                          └──→ 🚚 Logística: prepara envío
                                                     └──→ 📨 EnvioPreparado
                                                             ├──→ 📧 Email: tracking
                                                             └──→ 📊 Analytics: métricas
```

**1 acción** → **3 eventos** → **6 servicios** → **12 operaciones** — todo desacoplado.

**Archivo**: `sistema_completo/ecommerce_eda.py`

---

## Tecnologías EDA en Producción

| Componente | Tecnologías |
|------------|-------------|
| **Event Broker** | Apache Kafka, RabbitMQ, Amazon EventBridge |
| **Pub/Sub** | Google Pub/Sub, AWS SNS, Azure Event Grid |
| **Colas** | Amazon SQS, Azure Service Bus, RabbitMQ Queues |
| **Event Store** | EventStoreDB, Apache Kafka (log compactado) |
| **Streaming** | Apache Kafka Streams, Apache Flink, AWS Kinesis |

---

## Conceptos Clave Resumidos

```
┌──────────────────────────┬────────────────────────────────────────────────┐
│ Concepto                  │ En una frase                                  │
├──────────────────────────┼────────────────────────────────────────────────┤
│ Evento                    │ Hecho inmutable que ya ocurrió                │
│ Emisor (Producer)         │ Publica eventos sin conocer consumidores      │
│ Consumidor (Consumer)     │ Reacciona a eventos con lógica propia         │
│ Broker                    │ Intermediario que persiste y distribuye        │
│ Pub/Sub                   │ Un evento → múltiples receptores              │
│ Cola (Queue)              │ Un mensaje → un solo procesador               │
│ Persistencia              │ Los eventos sobreviven a caídas               │
│ Idempotencia              │ Mismo evento N veces = mismo resultado        │
│ Event Sourcing            │ Estado = replay de todos los eventos          │
│ Escalabilidad elástica    │ Crecer sin modificar emisores                 │
│ Resiliencia               │ Fallos aislados, no propagados                │
└──────────────────────────┴────────────────────────────────────────────────┘
```
