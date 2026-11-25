"""
Genera los 100 documentos de prueba para el indexador Lucene (20 por formato:
.doc, .docx, .pdf, .txt y .html). El contenido es real: título, autores, palabras
clave, fecha y resumen de registros recolectados de CORA con recoleccion_cora.py.
Requiere python-docx y LibreOffice (para convertir a .doc y .pdf).
"""
import html
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from docx import Document

import recoleccion_cora as cora

CARPETA = Path("documentos_prueba")
FORMATOS = ["doc", "docx", "pdf", "txt", "html"]
LARGO_MINIMO_RESUMEN = 400


def texto_plano(fila):
    return (f"{fila['titulo']}\n\n"
            f"Autores: {fila['autores']}\n"
            f"Palabras clave: {fila['palabras_clave']}\n"
            f"Fecha: {fila['fecha']}\n"
            f"Identificador: {fila['identificador']}\n\n"
            f"{fila['resumen']}\n")


def crear_docx(fila, ruta):
    doc = Document()
    doc.core_properties.author = "Aramayo Pedro Mauricio Leandro (TP4, datos de CORA)"
    doc.core_properties.title = fila["titulo"][:250]
    doc.core_properties.comments = ""
    doc.core_properties.created = datetime.now()
    doc.core_properties.modified = datetime.now()
    doc.add_heading(fila["titulo"], level=1)
    for etiqueta, campo in [("Autores", "autores"), ("Palabras clave", "palabras_clave"),
                            ("Fecha", "fecha"), ("Identificador", "identificador")]:
        doc.add_paragraph(f"{etiqueta}: {fila[campo]}")
    for parrafo in fila["resumen"].split("\n"):
        if parrafo.strip():
            doc.add_paragraph(parrafo.strip())
    doc.save(ruta)


def crear_html(fila, ruta):
    e = html.escape
    parrafos = "".join(f"<p>{e(p.strip())}</p>" for p in fila["resumen"].split("\n") if p.strip())
    ruta.write_text(
        f"<!DOCTYPE html>\n<html lang=\"en\">\n<head><meta charset=\"utf-8\"><title>{e(fila['titulo'])}</title></head>\n"
        f"<body>\n<h1>{e(fila['titulo'])}</h1>\n<p><b>Autores:</b> {e(fila['autores'])}</p>\n"
        f"<p><b>Palabras clave:</b> {e(fila['palabras_clave'])}</p>\n<p><b>Fecha:</b> {e(fila['fecha'])}</p>\n"
        f"<p><b>Identificador:</b> {e(fila['identificador'])}</p>\n{parrafos}\n</body>\n</html>\n",
        encoding="utf-8")


def convertir_con_libreoffice(docx, formato, carpeta_destino):
    filtro = {"doc": "doc:MS Word 97", "pdf": "pdf:writer_pdf_Export"}[formato]
    subprocess.run(["soffice", "--headless", "--convert-to", filtro, "--outdir", str(carpeta_destino), str(docx)],
                   check=True, capture_output=True)


def main():
    registros = cora.recolectar(300)
    filas = [cora.registro_a_fila(r) for r in registros]
    filas = [f for f in filas if len(f["resumen"]) >= LARGO_MINIMO_RESUMEN][:100]
    assert len(filas) == 100, f"Solo hay {len(filas)} registros con resumen largo"

    shutil.rmtree(CARPETA, ignore_errors=True)
    CARPETA.mkdir()
    temporal = Path(tempfile.mkdtemp())
    for numero, fila in enumerate(filas, start=1):
        formato = FORMATOS[(numero - 1) % len(FORMATOS)]
        nombre = f"doc_{numero:03d}"
        destino = CARPETA / f"{nombre}.{formato}"
        if formato == "txt":
            destino.write_text(texto_plano(fila), encoding="utf-8")
        elif formato == "html":
            crear_html(fila, destino)
        elif formato == "docx":
            crear_docx(fila, destino)
        else:
            base = temporal / f"{nombre}.docx"
            crear_docx(fila, base)
            convertir_con_libreoffice(base, formato, CARPETA)
    print(f"Generados {len(list(CARPETA.iterdir()))} documentos en {CARPETA}/")


if __name__ == "__main__":
    main()
