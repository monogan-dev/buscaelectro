"""
Scraper para Homecenter Colombia.
Usa la búsqueda por texto del sitio (Next.js) con paginación.
"""

import requests
import warnings
import json
import math
import time
import random
from bs4 import BeautifulSoup
from db import guardar_productos

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO",
}

BASE_SEARCH = "https://www.homecenter.com.co/homecenter-co/search/"

PALABRAS_EXCLUIR = {
    "organizador", "accesorio", "repuesto", "filtro", "manguera",
    "soporte", "cubierta", "funda", "cesto", "canasta", "iman",
    "protector de voltaje", "regulador",
}

CATEGORIAS = {
    "neveras": [
        "nevera", "nevera samsung", "nevera lg", "nevera mabe",
        "nevera haceb", "nevera whirlpool", "nevera electrolux",
        "nevera indurama", "nevecon",
    ],
    "lavadoras": [
        "lavadora", "lavadora lg", "lavadora samsung",
        "lavadora whirlpool", "lavadora mabe", "lavadora electrolux",
    ],
    "televisores": [
        "televisor", "televisor samsung", "televisor lg",
        "televisor sony", "televisor tcl", "televisor hisense",
    ],
    "aires acondicionados": [
        "aire acondicionado", "aire acondicionado lg",
        "aire acondicionado samsung", "minisplit",
    ],
    "microondas": ["microondas", "microondas samsung", "microondas lg"],
    "estufas": ["estufa", "estufa mabe", "estufa haceb", "cocina gas"],
    "lavaplatos": ["lavaplatos", "lavavajillas"],
    "secadoras": ["secadora"],
}


def _extraer_pagina(html: str, categoria: str, termino: str) -> tuple[list[dict], int]:
    """Extrae productos y total de páginas del HTML de búsqueda."""
    soup = BeautifulSoup(html, "html.parser")
    nd = soup.find("script", id="__NEXT_DATA__")
    if not nd:
        return [], 1

    data = json.loads(nd.string)
    search_data = (
        data.get("props", {})
        .get("pageProps", {})
        .get("searchProps", {})
        .get("searchData", {})
    )

    paginacion = search_data.get("pagination", {})
    total = paginacion.get("count", 0)
    por_pagina = paginacion.get("perPage", 40) or 40
    total_paginas = math.ceil(total / por_pagina) if total else 1

    resultados = search_data.get("results", [])
    productos = []
    palabras_termino = termino.lower().split()

    for item in resultados:
        nombre = item.get("displayName", "")
        nombre_lower = nombre.lower()

        if not any(p in nombre_lower for p in palabras_termino):
            continue
        if any(ex in nombre_lower for ex in PALABRAS_EXCLUIR):
            continue

        precios = item.get("prices", [])
        precio_internet = next(
            (p["priceWithoutFormatting"] for p in precios if p.get("type") == "INTERNET"), 0
        )
        precio_normal = next(
            (p["priceWithoutFormatting"] for p in precios if p.get("type") == "NORMAL"), 0
        )
        precio = precio_internet or precio_normal
        if not precio:
            continue

        medias = item.get("mediaUrls") or []
        imagen = medias[0] if isinstance(medias, list) and medias and isinstance(medias[0], str) else ""

        sku_id = item.get("skuId", "")
        url = f"https://www.homecenter.com.co/homecenter-co/product/{sku_id}" if sku_id else ""

        prod = {
            "nombre": nombre,
            "precio": float(precio),
            "url": url,
            "imagen": imagen,
            "tienda": "Homecenter",
            "categoria": categoria,
        }
        if precio_normal and precio_internet and precio_internet < precio_normal:
            prod["precio_original"] = float(precio_normal)

        productos.append(prod)

    return productos, total_paginas


def scrape_termino(termino: str, categoria: str) -> list[dict]:
    """Recorre todas las páginas de búsqueda para un término."""
    productos = []
    pagina = 1

    while True:
        params = {"Ntt": termino}
        if pagina > 1:
            params["currentPage"] = pagina

        try:
            resp = requests.get(BASE_SEARCH, headers=HEADERS, params=params, timeout=20, verify=False)
            if resp.status_code != 200:
                break
        except requests.RequestException as e:
            print(f"    Error: {e}")
            break

        prods, total_paginas = _extraer_pagina(resp.text, categoria, termino)

        if not prods:
            break

        productos.extend(prods)
        pagina += 1
        if pagina > total_paginas:
            break

        time.sleep(random.uniform(0.8, 1.5))

    return productos


def scrape_todo():
    print("=== Iniciando scraper Homecenter ===")
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
