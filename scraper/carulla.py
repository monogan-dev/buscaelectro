"""
Scraper para Carulla Colombia. VTEX API (igual que Éxito/Jumbo).
"""

import requests, warnings, time, random
from db import guardar_productos

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

API_BASE = "https://www.carulla.com/api/catalog_system/pub/products/search"

PALABRAS_EXCLUIR = {
    "organizador", "abrazadera", "repuesto", "manguera", "soporte",
    "accesorio", "cubierta", "funda", "cesto", "canasta",
    "iman", "imán", "adorno", "protector de voltaje",
}

CATEGORIAS = {
    "neveras": ["nevera", "nevera samsung", "nevera lg", "nevera mabe", "nevera haceb", "nevera whirlpool", "nevera electrolux", "nevera indurama", "nevecon"],
    "lavadoras": ["lavadora", "lavadora lg", "lavadora samsung", "lavadora whirlpool", "lavadora mabe"],
    "televisores": ["televisor", "televisor samsung", "televisor lg", "televisor sony", "televisor tcl"],
    "aires acondicionados": ["aire acondicionado", "aire acondicionado lg", "aire acondicionado samsung"],
    "microondas": ["microondas", "microondas samsung", "microondas lg"],
    "estufas": ["estufa", "estufa mabe", "estufa haceb", "cocina a gas"],
    "lavaplatos": ["lavavajillas", "lavaplatos"],
    "secadoras": ["secadora"],
}


def scrape_termino(termino: str, categoria: str) -> list[dict]:
    productos = []
    desde = 0
    por_pagina = 50

    while True:
        try:
            resp = requests.get(API_BASE, headers=HEADERS,
                params={"ft": termino, "_from": desde, "_to": desde + por_pagina - 1},
                timeout=15, verify=False)
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
            if not any(p in nombre_lower for p in termino.lower().split()):
                continue
            if any(ex in nombre_lower for ex in PALABRAS_EXCLUIR):
                continue
            try:
                seller = item.get("items", [{}])[0].get("sellers", [{}])[0]
                oferta = seller.get("commertialOffer", {})
                precio = oferta.get("Price", 0)
                precio_lista = oferta.get("ListPrice", 0)
                if not precio or not oferta.get("IsAvailable", False):
                    continue
                imagenes = item.get("items", [{}])[0].get("images", [])
                prod = {
                    "nombre": nombre,
                    "precio": float(precio),
                    "url": f"https://www.carulla.com/{item.get('linkText','')}/p",
                    "imagen": imagenes[0].get("imageUrl", "") if imagenes else "",
                    "tienda": "Carulla",
                    "categoria": categoria,
                }
                if precio_lista and precio_lista > precio:
                    prod["precio_original"] = float(precio_lista)
                productos.append(prod)
            except (IndexError, KeyError, ValueError):
                continue

        if len(items) < por_pagina:
            break
        desde += por_pagina
        time.sleep(random.uniform(0.5, 1.0))

    return productos


def scrape_todo():
    print("=== Iniciando scraper Carulla ===")
    total_global = 0

    for categoria, terminos in CATEGORIAS.items():
        print(f"\nCategoria: {categoria}")
        vistos = set()
        productos_cat = []

        for termino in terminos:
            prods = scrape_termino(termino, categoria)
            nuevos = [p for p in prods if p["nombre"] not in vistos]
            vistos.update(p["nombre"] for p in nuevos)
            productos_cat.extend(nuevos)
            print(f"  '{termino}': {len(prods)} -> {len(nuevos)} nuevos (total: {len(productos_cat)})")
            time.sleep(random.uniform(0.5, 1.0))

        if productos_cat:
            guardar_productos(productos_cat)
            total_global += len(productos_cat)

    print(f"\n=== Finalizado. {total_global} productos guardados. ===")


if __name__ == "__main__":
    scrape_todo()
