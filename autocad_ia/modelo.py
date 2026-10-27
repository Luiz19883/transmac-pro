"""Representação neutra de um desenho, usada pelas regras e pela IA.

Os extratores (COM do AutoCAD ou DXF) convertem o desenho para estas
estruturas, assim as regras não dependem de onde os dados vieram.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

COR_POR_CAMADA = 256  # ByLayer
COR_POR_BLOCO = 0  # ByBlock


@dataclass
class Camada:
    nome: str
    cor: int
    tipo_linha: str
    espessura: int
    ligada: bool = True
    congelada: bool = False


@dataclass
class Entidade:
    handle: str
    tipo: str  # TEXT, MTEXT, INSERT, DIMENSION, LINE, ...
    camada: str
    cor: int
    layout: str
    posicao: tuple[float, float] | None = None
    texto: str | None = None
    altura: float | None = None
    estilo: str | None = None  # estilo de texto ou de cota
    bloco: str | None = None
    atributos: dict[str, str] = field(default_factory=dict)


@dataclass
class Desenho:
    arquivo: str
    unidades: int  # INSUNITS: 4 = mm, 5 = cm, 6 = m
    camadas: list[Camada]
    entidades: list[Entidade]

    def como_dict(self) -> dict:
        return asdict(self)
