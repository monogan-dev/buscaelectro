"""
Scraper para Éxito Colombia.
Usa la API de catálogo VTEX con búsqueda por texto completo (ft=).
Sin límites artificiales — recorre todos los resultados disponibles.
"""

import requests
import time
import random
from db import guardar_productos

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

API_BASE = "https://www.exito.com/api/catalog_system/pub/products/search"

# Palabras en el nombre que delatan accesorios, no el electrodoméstico en sí
PALABRAS_EXCLUIR = {
    "organizador", "abrazadera", "repuesto", "manguera", "soporte",
    "accesorio", "jabón", "detergente", "cubierta", "funda",
    "cesto", "canasta", "iman", "imán", "adorno", "decoracion",
    "decoración", "protector de voltaje", "regulador",
}

CATEGORIAS = {
    "neveras": [
        "nevera", "nevera samsung", "nevera lg", "nevera mabe",
        "nevera haceb", "nevera challenger", "nevera whirlpool",
        "nevera electrolux", "nevera indurama", "nevecón",
        "nevera hisense", "refrigerador",
    ],
    "lavadoras": [
        "lavadora", "lavadora lg", "lavadora samsung", "lavadora whirlpool",
        "lavadora mabe", "lavadora challenger", "lavadora electrolux",
        "lavadora haceb", "lavadora hisense",
    ],
    "televisores": [
        "televisor", "televisor samsung", "televisor lg", "televisor tcl",
        "televisor sony", "televisor hisense", "televisor kalley",
        "smart tv",
    ],
    "aires acondicionados": [
        "aire acondicionado", "aire acondicionado lg", "aire acondicionado samsung",
        "aire acondicionado hisense", "minisplit",
    ],
    "microondas": [
        "microondas", "microondas samsung", "microondas lg",
        "microondas whirlpool", "microondas haceb",
    ],
    "estufas": [
        "estufa", "estufa haceb", "estufa mabe", "estufa challenger",
        "cocina a gas", "estufa electrolux", "estufa indurama",
    ],
    "lavaplatos": [
        "lavavajillas", "lavaplatos",
    ],
    "secadoras": [
        "secadora", "secadora lg", "secadora samsung", "secadora whirlpool",
    ],
}


def scrape_termino(termino: str, categoria: str) -> list[dict]:
    """Recorre todos los resultados de Éxito para un término dado."""
    productos = []
    desde = 0
    por_pagina = 50

    while True:
        params = {
            "ft": termino,
            "_from": desde,
            "_to": desde + por_pagina - 1,
        }

        try:
            resp = requests.get(API_BASE, headers=HEADERS, params=params, timeout=15)
            if resp.status_code not in (200, 206):
                break
            items = resp.json()
        except (requests.RequestException, ValueError) as e:
            print(f"    Error: {e}")
            break

        if not items:
            break

        for item in items:
            nombre = item.get("productName", "")
            nombre_lower = nombre.lower()
            termino_lower = termino.lower()

            # El nombre debe contener el término buscado
            # Para "televisor samsung" basta con que tenga "televisor" o "samsung"
            palabras_termino = termino_lower.split()
            if not any(p in nombre_lower for p in palabras_termino):
                continue

            # Excluir accesorios
            if any(ex in nombre_lower for ex in PALABRAS_EXCLUIR):
                continue

            try:
                seller = item.get("items", [{}])[0].get("sellers", [{}])[0]
                oferta = seller.get("commertialOffer", {})
                precio = oferta.get("Price", 0)          # precio real de venta
                precio_lista = oferta.get("ListPrice", 0)  # precio original (antes del descuento)
                disponible = oferta.get("IsAvailable", False)

                if not precio or not disponible:
                    continue

                imagen = ""
                imagenes = item.get("items", [{}])[0].get("images", [])
                if imagenes:
                    imagen = imagenes[0].get("imageUrl", "")

                link = item.get("linkText", "")
                prod = {
                    "nombre": nombre,
                    "precio": float(precio),
                    "url": f"https://www.exito.com/{link}/p" if link else "",
                    "imagen": imagen,
                    "tienda": "Éxito",
                    "categoria": categoria,
                }
                # Guardar precio original solo si hay descuento real
                if precio_lista and precio_lista > precio:
                    prod["precio_original"] = float(precio_lista)
                productos.append(prod)
            except (IndexError, KeyError, ValueError):
                continue

        if len(items) < por_pagina:
            break  # última página

        desde += por_pagina
        time.sleep(random.uniform(0.5, 1.0))

    return productos


def scrape_todo():
    print("=== Iniciando scraper Éxito ===")
    total_global = 0

    for categoria, terminos in CATEGORIAS.items():
        print(f"\nCategoría: {categoria}")
        vistos = set()
        productos_cat = []

        for termino in terminos:
            prods = scrape_termino(termino, categoria)
            nuevos = [p for p in prods if p["nombre"] not in vistos]
            vistos.update(p["nombre"] for p in nuevos)
            productos_cat.extend(nuevos)
            print(f"  '{termino}': {len(prods)} -> {len(nuevos)} nuevos (total cat: {len(productos_cat)})")
            time.sleep(random.uniform(0.5, 1.0))

        if productos_cat:
            guardar_productos(productos_cat)
            total_global += len(productos_cat)

    print(f"\n=== Finalizado. {total_global} productos únicos guardados. ===")


if __name__ == "__main__":
    scrape_todo()
