"""
Actualizador automático de precios.
Ejecuta todos los scrapers y registra el resultado.

Uso:
    python actualizar.py              # Ejecutar una vez
    python actualizar.py --programar  # Correr cada 12 horas indefinidamente
"""

import sys
import time
import logging
from datetime import datetime
from pathlib import Path

# Agregar scraper al path
sys.path.insert(0, str(Path(__file__).parent / "scraper"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler("actualizaciones.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

INTERVALO_HORAS = 12


def actualizar():
    """Ejecuta todos los scrapers y registra estadísticas."""
    from alkosto import scrape_todo as alkosto_scrape
    from exito import scrape_todo as exito_scrape
    from ktronix import scrape_todo as ktronix_scrape
    from jumbo import scrape_todo as jumbo_scrape
    from homecenter import scrape_todo as homecenter_scrape
    from db import obtener_estadisticas

    inicio = datetime.now()
    log.info("=== Iniciando actualizacion de precios ===")

    from carulla import scrape_todo as carulla_scrape
    from olimpica import scrape_todo as olimpica_scrape
    from alkomprar import scrape_todo as alkomprar_scrape
    from easy import scrape_todo as easy_scrape

    for nombre, fn in [("Alkosto", alkosto_scrape), ("Exito", exito_scrape),
                       ("Ktronix", ktronix_scrape), ("Jumbo", jumbo_scrape),
                       ("Homecenter", homecenter_scrape), ("Carulla", carulla_scrape),
                       ("Olimpica", olimpica_scrape), ("Alkomprar", alkomprar_scrape),
                       ("Easy", easy_scrape)]:
        try:
            fn()
        except Exception as e:
            log.error(f"Error en {nombre}: {e}")

    stats = obtener_estadisticas()
    duracion = (datetime.now() - inicio).seconds // 60

    log.info(
        f"=== Actualización completada en {duracion} min. "
        f"Total: {stats['total_productos']} productos ==="
    )
    return stats


def programar():
    """Ejecuta el actualizador cada INTERVALO_HORAS horas."""
    log.info(f"Modo programado: actualizando cada {INTERVALO_HORAS} horas.")
    while True:
        actualizar()
        proxima = datetime.now().replace(microsecond=0)
        log.info(f"Próxima actualización en {INTERVALO_HORAS} horas.")
        time.sleep(INTERVALO_HORAS * 3600)


if __name__ == "__main__":
    if "--programar" in sys.argv:
        programar()
    else:
        actualizar()
