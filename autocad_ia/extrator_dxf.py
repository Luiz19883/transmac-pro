"""Extrai um Desenho de um arquivo DXF com ezdxf (não precisa do AutoCAD)."""
from __future__ import annotations

from pathlib import Path

import ezdxf

from .modelo import CAMADA_REVISAO, Camada, Desenho, Entidade

_TIPOS_COTA = {"DIMENSION", "ARC_DIMENSION", "LARGE_RADIAL_DIMENSION"}


def _posicao(ent) -> tuple[float, float] | None:
    for atributo in ("insert", "start", "center", "defpoint"):
        if ent.dxf.hasattr(atributo):
            ponto = ent.dxf.get(atributo)
            return (round(ponto[0], 4), round(ponto[1], 4))
    return None


def _converter(ent, layout: str) -> Entidade:
    tipo = ent.dxftype()
    item = Entidade(
        handle=ent.dxf.handle,
        tipo=tipo,
        camada=ent.dxf.get("layer", "0"),
        cor=ent.dxf.get("color", 256),
        layout=layout,
        posicao=_posicao(ent),
    )
    if tipo == "TEXT":
        item.texto = ent.dxf.text
        item.altura = ent.dxf.get("height")
        item.estilo = ent.dxf.get("style", "Standard")
    elif tipo == "MTEXT":
        item.texto = ent.plain_text()
        item.altura = ent.dxf.get("char_height")
        item.estilo = ent.dxf.get("style", "Standard")
    elif tipo == "INSERT":
        item.bloco = ent.dxf.name
        item.atributos = {a.dxf.tag: a.dxf.text for a in ent.attribs}
    elif tipo in _TIPOS_COTA:
        item.tipo = "DIMENSION"
        item.estilo = ent.dxf.get("dimstyle", "Standard")
    return item


def extrair_dxf(caminho: str | Path) -> Desenho:
    doc = ezdxf.readfile(str(caminho))
    camadas = [
        Camada(
            nome=c.dxf.name,
            cor=abs(c.dxf.get("color", 7)),
            tipo_linha=c.dxf.get("linetype", "Continuous"),
            espessura=c.dxf.get("lineweight", -3),
            ligada=c.is_on(),
            congelada=c.is_frozen(),
        )
        for c in doc.layers
    ]
    entidades = [
        _converter(ent, layout.name)
        for layout in doc.layouts
        for ent in layout
        if ent.dxf.get("layer", "0") != CAMADA_REVISAO
    ]
    return Desenho(
        arquivo=str(caminho),
        unidades=doc.header.get("$INSUNITS", 0),
        camadas=camadas,
        entidades=entidades,
    )
