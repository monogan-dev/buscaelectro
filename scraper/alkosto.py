"""
Scraper para Alkosto Colombia.
Usa la API de Algolia que Alkosto emplea internamente.
Sin límites artificiales — recorre todas las páginas disponibles.
"""

import requests
import time
import random
from db import guardar_productos

ALGOLIA_APP_ID = "QX5IPS1B1Q"
ALGOLIA_API_KEY = "7a8800d62203ee3a9ff1cdf74f99b268"
ALGOLIA_INDEX = "alkostoIndexAlgoliaPRD"
ALGOLIA_URL = f"https://{ALGOLIA_APP_ID.lower()}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"

HEADERS = {
    "X-Algolia-Application-Id": ALGOLIA_APP_ID,
    "X-Algolia-API-Key": ALGOLIA_API_KEY,
    "Content-Type": "application/json",
}

# Por cada categoría se hacen múltiples búsquedas (categoría general + marcas)
# para superar el límite de Algolia de ~1000 resultados por consulta.
CATEGORIAS = {
    "neveras": [
        "nevera", "nevera samsung", "nevera lg", "nevera mabe",
        "nevera haceb", "nevera challenger", "nevera whirlpool",
        "nevera electrolux", "nevera indurama", "nevera kalley",
        "nevera hisense", "nevera daewoo", "nevecón",
    ],
    "lavadoras": [
        "lavadora", "lavadora lg", "lavadora samsung", "lavadora whirlpool",
        "lavadora mabe", "lavadora challenger", "lavadora electrolux",
        "lavadora haceb", "lavadora kalley", "lavadora hisense",
    ],
    "televisores": [
        "televisor", "tv samsung", "tv lg", "tv tcl", "tv sony",
        "tv hisense", "tv kalley", "tv challenger", "tv hyundai",
        "tv philips", "tv daewoo", "tv coby",
    ],
    "aires acondicionados": [
        "aire acondicionado", "aire acondicionado lg", "aire acondicionado samsung",
        "aire acondicionado kalley", "aire acondicionado hisense",
        "minisplit", "aire acondicionado mirage", "aire acondicionado carrier",
    ],
    "microondas": [
        "microondas", "microondas samsung", "microondas lg",
        "microondas whirlpool", "microondas haceb", "microondas mabe",
    ],
    "estufas": [
        "estufa", "estufa haceb", "estufa mabe", "estufa challenger",
        "cocina a gas", "estufa electrolux", "estufa kalley",
        "estufa indurama", "horno",
    ],
    "lavaplatos": [
        "lavaplatos", "lavavajillas", "lavaplatos whirlpool",
        "lavavajillas mabe", "lavavajillas samsung",
    ],
    "secadoras": [
        "secadora", "secadora lg", "secadora samsung",
        "secadora whirlpool", "secadora mabe",
    ],
}


def scrape_termino(termino: str) -> list[dict]:
    """Recorre todas las páginas de Algolia para un término dado."""
    productos = []
    pagina = 0
    por_pagina = 40

    while True:
        body = {
            "query": termino,
            "hitsPerPage": por_pagina,
            "page": pagina,
            "attributesToRetrieve": [
                "name_text_es",
                "pricevalue_cop_double",
                "lowestprice_double",
                "url_es_string",
                "img-310wx310h_string",
            ],
        }

        try:
            resp = requests.post(ALGOLIA_URL, headers=HEADERS, json=body, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"    Error en página {pagina}: {e}")
            break

        hits = data.get("hits", [])
        total_paginas = data.get("nbPages", 1)

        for hit in hits:
            # discountprice_double es el precio con descuento (si hay oferta)
            # pricevalue_cop_double es el precio original (tachado)
            precio_original = hit.get("pricevalue_cop_double") or 0
            precio_descuento = hit.get("discountprice_double") or hit.get("lowestprice_double") or 0
            # Usar el precio más bajo disponible como precio de venta
            precio = precio_descuento if precio_descuento and precio_descuento < precio_original else precio_original
            nombre = hit.get("name_text_es", "")
            if not nombre or not precio:
                continue

            url = hit.get("url_es_string", "")
            if url and not url.startswith("http"):
                url = f"https://www.alkosto.com{url}"

            prod = {
                "nombre": nombre,
                "precio": float(precio),
                "url": url,
                "imagen": hit.get("img-310wx310h_string", ""),
                "tienda": "Alkosto",
                "categoria": "",  # se asigna en scrape_todo
            }
            # Guardar precio original solo si hay descuento real
            if precio_descuento and precio_descuento < precio_original:
                prod["precio_original"] = float(precio_original)
            productos.append(prod)

        pagina += 1
        if pagina >= total_paginas:
            break

        time.sleep(random.uniform(0.3, 0.8))

    return productos


def scrape_todo():
    print("=== Iniciando scraper Alkosto (Algolia) ===")
    total_global = 0

    for categoria, terminos in CATEGORIAS.items():
        print(f"\nCategoría: {categoria}")
        vistos = set()
        productos_cat = []

        for termino in terminos:
            prods = scrape_termino(termino)
            nuevos = [p for p in prods if p["nombre"] not in vistos]
            vistos.update(p["nombre"] for p in nuevos)
            for p in nuevos:
                p["categoria"] = categoria
            productos_cat.extend(nuevos)
            print(f"  '{termino}': {len(prods)} -> {len(nuevos)} nuevos (total cat: {len(productos_cat)})")
            time.sleep(random.uniform(0.5, 1.0))

        if productos_cat:
            guardar_productos(productos_cat)
            total_global += len(productos_cat)

    print(f"\n=== Finalizado. {total_global} productos únicos guardados. ===")


if __name__ == "__main__":
    scrape_todo()
