"""
Scraper para Alkomprar Colombia.
Usa el mismo Algolia que Alkosto/Ktronix, solo cambia el índice.
"""

import requests, time, random
from db import guardar_productos

ALGOLIA_APP_ID = "QX5IPS1B1Q"
ALGOLIA_API_KEY = "7a8800d62203ee3a9ff1cdf74f99b268"
ALGOLIA_INDEX  = "alkomprarIndexAlgoliaPRD"
ALGOLIA_URL    = f"https://{ALGOLIA_APP_ID.lower()}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"

HEADERS = {
    "X-Algolia-Application-Id": ALGOLIA_APP_ID,
    "X-Algolia-API-Key": ALGOLIA_API_KEY,
    "Content-Type": "application/json",
}

CATEGORIAS = {
    "neveras":              ["nevera","nevera samsung","nevera lg","nevera mabe","nevera haceb","nevera whirlpool","nevera electrolux","nevecon"],
    "lavadoras":            ["lavadora","lavadora lg","lavadora samsung","lavadora whirlpool","lavadora mabe"],
    "televisores":          ["televisor","tv samsung","tv lg","tv tcl","tv sony","tv hisense","tv kalley"],
    "aires acondicionados": ["aire acondicionado","aire acondicionado lg","aire acondicionado samsung","minisplit"],
    "microondas":           ["microondas","microondas samsung","microondas lg"],
    "estufas":              ["estufa","estufa mabe","estufa haceb","cocina a gas"],
    "lavaplatos":           ["lavaplatos","lavavajillas"],
    "secadoras":            ["secadora"],
}


def scrape_termino(termino: str) -> list[dict]:
    productos, pagina, por_pagina = [], 0, 40
    while True:
        body = {"query": termino, "hitsPerPage": por_pagina, "page": pagina,
                "attributesToRetrieve": ["name_text_es","pricevalue_cop_double","discountprice_double","lowestprice_double","url_es_string","img-310wx310h_string"]}
        try:
            resp = requests.post(ALGOLIA_URL, headers=HEADERS, json=body, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"    Error: {e}"); break

        hits = data.get("hits", [])
        total_paginas = data.get("nbPages", 1)

        for hit in hits:
            precio_original = hit.get("pricevalue_cop_double") or 0
            precio_desc = hit.get("discountprice_double") or hit.get("lowestprice_double") or 0
            precio = precio_desc if precio_desc and precio_desc < precio_original else precio_original
            nombre = hit.get("name_text_es", "")
            if not nombre or not precio: continue
            url = hit.get("url_es_string", "")
            if url and not url.startswith("http"):
                url = f"https://www.alkomprar.com{url}"
            prod = {"nombre": nombre, "precio": float(precio), "url": url,
                    "imagen": hit.get("img-310wx310h_string", ""), "tienda": "Alkomprar", "categoria": ""}
            if precio_desc and precio_desc < precio_original:
                prod["precio_original"] = float(precio_original)
            productos.append(prod)

        pagina += 1
        if pagina >= total_paginas: break
        time.sleep(random.uniform(0.3, 0.7))
    return productos


def scrape_todo():
    print("=== Iniciando scraper Alkomprar (Algolia) ===")
    total_global = 0
    for categoria, terminos in CATEGORIAS.items():
        print(f"\nCategoria: {categoria}")
        vistos, productos_cat = set(), []
        for termino in terminos:
            prods = scrape_termino(termino)
            nuevos = [p for p in prods if p["nombre"] not in vistos]
            vistos.update(p["nombre"] for p in nuevos)
            for p in nuevos: p["categoria"] = categoria
            productos_cat.extend(nuevos)
            print(f"  '{termino}': {len(prods)} -> {len(nuevos)} nuevos (total: {len(productos_cat)})")
            time.sleep(random.uniform(0.3, 0.7))
        if productos_cat:
            guardar_productos(productos_cat)
            total_global += len(productos_cat)
    print(f"\n=== Finalizado. {total_global} productos guardados. ===")

if __name__ == "__main__":
    scrape_todo()
