"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        ARQUITECTURA ORIENTADA A EVENTOS (EDA)                              ║
║        Ejecutor Principal de Demos                                          ║
║                                                                              ║
║  Este script ejecuta secuencialmente las demostraciones de los              ║
║  5 pilares de la EDA + la simulación completa del sistema e-commerce.       ║
║                                                                              ║
║  Uso:                                                                        ║
║      python ejecutar_demos.py          → Ejecutar TODAS las demos           ║
║      python ejecutar_demos.py 1        → Solo Pilar 1                       ║
║      python ejecutar_demos.py 1 3 5    → Pilares 1, 3 y 5                  ║
║      python ejecutar_demos.py sistema  → Solo la simulación completa        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import importlib

# Asegurar que el directorio raíz del proyecto esté en el path
RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

# Mapeo de módulos con sus nombres legibles de importación
# (los nombres de carpeta usan guiones bajos como prefijo para imports)
DEMOS = {
    "1": {
        "nombre": "Pilar 1: El Evento como Unidad de Verdad",
        "modulo": "_01_evento_unidad_de_verdad.evento",
        "funcion": "demo_evento_como_unidad_de_verdad"
    },
    "2": {
        "nombre": "Pilar 2: Roles y Responsabilidades de los Actores",
        "modulo": "_02_roles_y_responsabilidades.actores",
        "funcion": "demo_roles_y_responsabilidades"
    },
    "3": {
        "nombre": "Pilar 3: Mecanismos de Comunicación",
        "modulo": "_03_mecanismos_comunicacion.comunicacion",
        "funcion": "demo_mecanismos_comunicacion"
    },
    "4": {
        "nombre": "Pilar 4: Conceptos de Fiabilidad y Flujo",
        "modulo": "_04_fiabilidad_y_flujo.fiabilidad",
        "funcion": "demo_fiabilidad_y_flujo"
    },
    "5": {
        "nombre": "Pilar 5: Ventajas Operativas",
        "modulo": "_05_ventajas_operativas.ventajas",
        "funcion": "demo_ventajas_operativas"
    },
    "sistema": {
        "nombre": "Sistema Completo: E-Commerce con EDA",
        "modulo": "sistema_completo.ecommerce_eda",
        "funcion": "demo_sistema_completo"
    }
}


def ejecutar_demo(clave: str):
    """Importa y ejecuta una demo específica."""
    if clave not in DEMOS:
        print(f"  ❌ Demo '{clave}' no encontrada. Opciones: {list(DEMOS.keys())}")
        return

    demo = DEMOS[clave]
    print(f"\n{'▓' * 70}")
    print(f"  ▶ Ejecutando: {demo['nombre']}")
    print(f"{'▓' * 70}\n")

    try:
        modulo = importlib.import_module(demo["modulo"])
        funcion = getattr(modulo, demo["funcion"])
        funcion()
    except Exception as e:
        print(f"  ❌ Error ejecutando demo '{clave}': {e}")
        import traceback
        traceback.print_exc()


def mostrar_menu():
    """Muestra el menú de demos disponibles."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║              ARQUITECTURA ORIENTADA A EVENTOS (EDA)                        ║
║              Guía Interactiva con Código Funcional                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   Demos disponibles:                                                         ║
║                                                                              ║
║   [1] Pilar 1: El Evento como Unidad de Verdad                             ║
║       → Qué es un evento, estructura, inmutabilidad                         ║
║                                                                              ║
║   [2] Pilar 2: Roles y Responsabilidades                                    ║
║       → Emisor, Consumidor, Broker y su interacción                         ║
║                                                                              ║
║   [3] Pilar 3: Mecanismos de Comunicación                                   ║
║       → Pub/Sub vs Colas de Mensajería                                      ║
║                                                                              ║
║   [4] Pilar 4: Fiabilidad y Flujo                                           ║
║       → Persistencia, Idempotencia, Event Sourcing                          ║
║                                                                              ║
║   [5] Pilar 5: Ventajas Operativas                                          ║
║       → Escalabilidad Elástica y Resiliencia                                ║
║                                                                              ║
║   [sistema] Simulación Completa: E-Commerce con EDA                         ║
║       → Flujo completo de compra con 7 microservicios                       ║
║                                                                              ║
║   [todos] Ejecutar TODAS las demos secuencialmente                          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)


def main():
    args = sys.argv[1:]

    if not args:
        mostrar_menu()
        print("  Uso: python ejecutar_demos.py [1|2|3|4|5|sistema|todos]\n")

        try:
            opcion = input("  Selecciona una opción: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  ¡Hasta luego!")
            return

        if opcion == "todos":
            args = ["1", "2", "3", "4", "5", "sistema"]
        elif opcion:
            args = [opcion]
        else:
            args = ["todos"]

    if "todos" in args:
        args = ["1", "2", "3", "4", "5", "sistema"]

    for arg in args:
        ejecutar_demo(arg)
        if arg != args[-1]:
            print(f"\n{'░' * 70}")
            print(f"  Presiona Enter para continuar a la siguiente demo...")
            print(f"{'░' * 70}")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                break


if __name__ == "__main__":
    main()
