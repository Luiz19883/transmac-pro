"""Extrai um Desenho do AutoCAD aberto, via COM (somente Windows).

Requer: pip install pyautocad pywin32
"""
from __future__ import annotations

from .modelo import Camada, Desenho, Entidade

# ObjectName do COM -> tipo DXF
_TIPOS = {
    "AcDbText": "TEXT",
    "AcDbMText": "MTEXT",
    "AcDbBlockReference": "INSERT",
    "AcDbLine": "LINE",
    "AcDbPolyline": "LWPOLYLINE",
    "AcDbCircle": "CIRCLE",
    "AcDbArc": "ARC",
    "AcDbHatch": "HATCH",
}


def conectar(abrir: str | None = None):
    """Conecta ao AutoCAD em execução e devolve o documento ativo (ou abre um DWG)."""
    from pyautocad import Autocad

    acad = Autocad(create_if_not_exists=True)
    if abrir:
        return acad.app.Documents.Open(abrir)
    return acad.doc


def _posicao(obj) -> tuple[float, float] | None:
    for prop in ("InsertionPoint", "StartPoint", "Center", "TextPosition"):
        try:
            ponto = getattr(obj, prop)
            return (round(ponto[0], 4), round(ponto[1], 4))
        except Exception:
            continue
    return None


def _converter(obj, layout: str) -> Entidade:
    nome_obj = obj.ObjectName
    tipo = _TIPOS.get(nome_obj, "DIMENSION" if "Dimension" in nome_obj else nome_obj)
    item = Entidade(
        handle=obj.Handle,
        tipo=tipo,
        camada=obj.Layer,
        cor=obj.TrueColor.ColorIndex,
        layout=layout,
        posicao=_posicao(obj),
    )
    if tipo in ("TEXT", "MTEXT"):
        item.texto = obj.TextString
        item.altura = obj.Height
        item.estilo = obj.StyleName
    elif tipo == "INSERT":
        item.bloco = obj.EffectiveName
        if obj.HasAttributes:
            item.atributos = {a.TagString: a.TextString for a in obj.GetAttributes()}
    elif tipo == "DIMENSION":
        item.estilo = obj.StyleName
    return item


def extrair_autocad(doc) -> Desenho:
    camadas = [
        Camada(
            nome=c.Name,
            cor=c.TrueColor.ColorIndex,
            tipo_linha=c.Linetype,
            espessura=c.Lineweight,
            ligada=bool(c.LayerOn),
            congelada=bool(c.Freeze),
        )
        for c in doc.Layers
    ]
    entidades = []
    for layout in doc.Layouts:
        for obj in layout.Block:
            try:
                entidades.append(_converter(obj, layout.Name))
            except Exception as erro:  # entidades proxy/corrompidas não param a revisão
                print(f"Aviso: ignorando entidade {getattr(obj, 'Handle', '?')}: {erro}")
    return Desenho(
        arquivo=doc.FullName,
        unidades=doc.GetVariable("INSUNITS"),
        camadas=camadas,
        entidades=entidades,
    )


def marcar_problemas(doc, problemas, raio: float = 5.0, camada: str = "REVISAO_IA") -> int:
    """Desenha um círculo vermelho e uma nota em cada problema com posição conhecida."""
    from pyautocad import APoint

    if camada not in [c.Name for c in doc.Layers]:
        nova = doc.Layers.Add(camada)
        nova.color = 1  # vermelho
    espaco = doc.ModelSpace
    marcados = 0
    for p in problemas:
        if p.posicao is None or p.layout != "Model":
            continue
        centro = APoint(*p.posicao)
        circulo = espaco.AddCircle(centro, raio)
        circulo.Layer = camada
        nota = espaco.AddText(f"[{p.codigo}] {p.mensagem}"[:120], APoint(p.posicao[0] + raio, p.posicao[1] + raio), raio / 2)
        nota.Layer = camada
        marcados += 1
    doc.Regen(1)
    return marcados
