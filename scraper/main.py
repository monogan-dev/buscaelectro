"""
Punto de entrada principal.
Ejecuta todos los scrapers y programa actualizaciones periódicas.

Uso:
    python main.py scrape       # Ejecutar scrapers una vez
    python main.py buscar nevera  # Buscar productos en la BD
    python main.py stats         # Ver estadísticas
"""

import sys
from db import buscar_productos, obtener_estadisticas


def cmd_scrape():
    """Ejecuta todos los scrapers."""
    from alkosto import scrape_todo as alkosto_scrape
    from exito import scrape_todo as exito_scrape
    from ktronix import scrape_todo as ktronix_scrape
    from jumbo import scrape_todo as jumbo_scrape
    from homecenter import scrape_todo as homecenter_scrape
    from carulla import scrape_todo as carulla_scrape
    from olimpica import scrape_todo as olimpica_scrape
    from alkomprar import scrape_todo as alkomprar_scrape
    from easy import scrape_todo as easy_scrape

    print("Ejecutando scrapers...\n")
    for fn in [alkosto_scrape, exito_scrape, ktronix_scrape, jumbo_scrape,
               homecenter_scrape, carulla_scrape, olimpica_scrape,
               alkomprar_scrape, easy_scrape]:
        fn()
        print()


def cmd_buscar(termino: str):
    """Busca productos y muestra resultados en consola."""
    print(f"\nBuscando: '{termino}'\n")
    resultados = buscar_productos(termino, limite=10)

    if not resultados:
        print("No se encontraron productos.")
        return

    print(f"{'#':<3} {'Tienda':<12} {'Precio':>12}  Nombre")
    print("-" * 70)
    for i, p in enumerate(resultados, 1):
        precio = f"${p['precio']:,.0f}"
        nombre = p['nombre'][:45] + "..." if len(p['nombre']) > 45 else p['nombre']
        print(f"{i:<3} {p['tienda']:<12} {precio:>12}  {nombre}")

    print(f"\n{len(resultados)} resultados. Ordenados por precio (menor a mayor).")


def cmd_stats():
    """Muestra estadísticas de la base de datos."""
    stats = obtener_estadisticas()
    print(f"\n=== Estadísticas de la BD ===")
    print(f"Total productos:      {stats['total_productos']}")
    print(f"Última actualización: {stats['ultima_actualizacion'] or 'nunca'}")
    print(f"\nPor tienda:")
    for tienda, count in stats['por_tienda'].items():
        print(f"  {tienda:<15} {count}")
    print(f"\nPor categoría:")
    for cat, count in stats['por_categoria'].items():
        print(f"  {cat:<25} {count}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    comando = sys.argv[1]

    if comando == "scrape":
        cmd_scrape()
    elif comando == "buscar" and len(sys.argv) > 2:
        cmd_buscar(" ".join(sys.argv[2:]))
    elif comando == "stats":
        cmd_stats()
    else:
        print(__doc__)
