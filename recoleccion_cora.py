"""
Recolección OAI-PMH del repositorio CORA (Repositori de Dades de Recerca).
Autor: Aramayo Pedro Mauricio Leandro - 3.er año, Ciencias de Datos e IA.

Descarga al menos 100 registros distintos con el verbo ListRecords (formato oai_dc),
sigue el resumptionToken para pasar de página, guarda los registros completos en XML
y arma un CSV con título, resumen, autores, palabras clave y fecha.
"""
import csv
import time
import xml.etree.ElementTree as ET

import requests

URL_BASE = "https://dataverse.csuc.cat/oai"
CANTIDAD_MINIMA = 100
ARCHIVO_XML = "cora_registros.xml"
ARCHIVO_CSV = "cora_registros.csv"
SEPARADOR = " | "  # separa varios autores o varias palabras clave en una misma celda

NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
    "dc": "http://purl.org/dc/elements/1.1/",
}
for prefijo, uri in NS.items():
    ET.register_namespace("" if prefijo == "oai" else prefijo, uri)
ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")


def pedir_pagina(parametros, intentos=3):
    """Hace una consulta OAI-PMH y devuelve el XML ya interpretado."""
    for intento in range(1, intentos + 1):
        try:
            respuesta = requests.get(URL_BASE, params=parametros, timeout=60)
            respuesta.raise_for_status()
            return ET.fromstring(respuesta.content)
        except (requests.RequestException, ET.ParseError) as error:
            if intento == intentos:
                raise
            print(f"  Error ({error}); reintento {intento} de {intentos - 1}...")
            time.sleep(3 * intento)


def valores(metadatos, campo):
    """Devuelve todos los valores de un campo Dublin Core (ej.: todos los dc:creator)."""
    return [e.text.strip() for e in metadatos.findall(f"dc:{campo}", NS) if e.text and e.text.strip()]


def recolectar(cantidad_minima=CANTIDAD_MINIMA):
    """Recorre ListRecords página por página hasta juntar la cantidad pedida."""
    registros = []          # elementos <record> completos
    vistos = set()          # identificadores ya guardados (para no repetir)
    parametros = {"verb": "ListRecords", "metadataPrefix": "oai_dc"}
    pagina = 0

    while len(registros) < cantidad_minima:
        pagina += 1
        raiz = pedir_pagina(parametros)
        error = raiz.find("oai:error", NS)
        if error is not None:
            raise RuntimeError(f"El repositorio respondió un error: {error.get('code')} - {error.text}")

        lista = raiz.find("oai:ListRecords", NS)
        for registro in lista.findall("oai:record", NS):
            cabecera = registro.find("oai:header", NS)
            identificador = cabecera.find("oai:identifier", NS).text
            # Los registros borrados vienen sin metadatos: se saltean.
            if cabecera.get("status") == "deleted" or identificador in vistos:
                continue
            vistos.add(identificador)
            registros.append(registro)

        token = lista.find("oai:resumptionToken", NS)
        print(f"Página {pagina}: llevo {len(registros)} registros distintos")
        if token is None or not (token.text or "").strip():
            print("No hay más páginas en el repositorio.")
            break
        # Para la página siguiente solo se envía el verbo y el resumptionToken.
        parametros = {"verb": "ListRecords", "resumptionToken": token.text.strip()}
        time.sleep(0.5)  # pausa corta para no saturar el servidor

    return registros[:cantidad_minima]


def guardar_xml(registros, archivo=ARCHIVO_XML):
    """Guarda los <record> completos (cabecera + todos los metadatos) en un solo XML."""
    raiz = ET.Element("registros", {"origen": URL_BASE, "cantidad": str(len(registros))})
    raiz.extend(registros)
    ET.indent(raiz)
    ET.ElementTree(raiz).write(archivo, encoding="utf-8", xml_declaration=True)


def registro_a_fila(registro):
    """Convierte un <record> en una fila del CSV con los cinco campos pedidos."""
    identificador = registro.find("oai:header/oai:identifier", NS).text
    dc = registro.find("oai:metadata/oai_dc:dc", NS)
    return {
        "identificador": identificador,
        "titulo": SEPARADOR.join(valores(dc, "title")),
        "resumen": SEPARADOR.join(valores(dc, "description")),
        "autores": SEPARADOR.join(valores(dc, "creator")),
        "palabras_clave": SEPARADOR.join(valores(dc, "subject")),
        "fecha": SEPARADOR.join(valores(dc, "date")),
    }


def guardar_csv(registros, archivo=ARCHIVO_CSV):
    filas = [registro_a_fila(r) for r in registros]
    with open(archivo, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        escritor.writeheader()
        escritor.writerows(filas)
    return filas


if __name__ == "__main__":
    registros = recolectar()
    guardar_xml(registros)
    filas = guardar_csv(registros)
    print(f"Total recolectado: {len(filas)} registros distintos")
    print(f"Archivos generados: {ARCHIVO_XML} y {ARCHIVO_CSV}")
