"""Verificações determinísticas a partir dos padrões da empresa (padroes.yaml)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .modelo import COR_POR_BLOCO, COR_POR_CAMADA, Desenho

UNIDADES = {0: "sem unidade", 1: "polegadas", 2: "pés", 4: "milímetros", 5: "centímetros", 6: "metros"}


@dataclass
class Problema:
    codigo: str
    gravidade: str  # "erro" | "aviso"
    mensagem: str
    handle: str | None = None
    camada: str | None = None
    layout: str | None = None
    posicao: tuple[float, float] | None = None
    origem: str = "regra"  # "regra" | "ia"


def _de_entidade(ent, codigo, gravidade, mensagem) -> Problema:
    return Problema(codigo, gravidade, mensagem, ent.handle, ent.camada, ent.layout, ent.posicao)


def verificar(desenho: Desenho, padroes: dict) -> list[Problema]:
    problemas: list[Problema] = []
    problemas += _camadas(desenho, padroes.get("camadas", {}))
    problemas += _entidades(desenho, padroes.get("entidades", {}))
    problemas += _textos(desenho, padroes.get("textos", {}))
    problemas += _cotas(desenho, padroes.get("cotas", {}))
    problemas += _carimbo(desenho, padroes.get("carimbo", {}))
    problemas += _unidades(desenho, padroes.get("unidades"))
    return problemas


def _camadas(desenho: Desenho, cfg: dict) -> list[Problema]:
    problemas = []
    nomes = {c.nome for c in desenho.camadas}
    padrao = cfg.get("padrao_nome")
    excecoes = set(cfg.get("excecoes", ["0", "Defpoints"]))
    if padrao:
        regex = re.compile(padrao)
        for camada in desenho.camadas:
            if camada.nome not in excecoes and not regex.fullmatch(camada.nome):
                problemas.append(Problema(
                    "CAM01", "erro",
                    f"Camada '{camada.nome}' fora do padrão de nomenclatura ({padrao})",
                    camada=camada.nome,
                ))
    for obrigatoria in cfg.get("obrigatorias", []):
        if obrigatoria not in nomes:
            problemas.append(Problema("CAM02", "erro", f"Camada obrigatória '{obrigatoria}' não existe"))
    usadas = {e.camada for e in desenho.entidades}
    if cfg.get("avisar_vazias", False):
        for nome in sorted(nomes - usadas - excecoes):
            problemas.append(Problema("CAM03", "aviso", f"Camada '{nome}' não tem entidades (rode PURGE)", camada=nome))
    return problemas


def _entidades(desenho: Desenho, cfg: dict) -> list[Problema]:
    problemas = []
    for ent in desenho.entidades:
        if cfg.get("proibir_na_camada_0") and ent.camada == "0" and ent.tipo != "INSERT":
            problemas.append(_de_entidade(ent, "ENT01", "erro", f"{ent.tipo} desenhado na camada 0"))
        if cfg.get("cor_deve_ser_porcamada") and ent.cor not in (COR_POR_CAMADA, COR_POR_BLOCO):
            problemas.append(_de_entidade(
                ent, "ENT02", "aviso",
                f"{ent.tipo} com cor fixa ({ent.cor}) em vez de PorCamada",
            ))
    return problemas


def _textos(desenho: Desenho, cfg: dict) -> list[Problema]:
    problemas = []
    alturas = cfg.get("alturas_permitidas")
    tolerancia = cfg.get("tolerancia_altura", 0.01)
    estilos = cfg.get("estilos_permitidos")
    for ent in desenho.entidades:
        if ent.tipo not in ("TEXT", "MTEXT"):
            continue
        if alturas and ent.altura is not None and not any(abs(ent.altura - a) <= tolerancia for a in alturas):
            problemas.append(_de_entidade(
                ent, "TXT01", "aviso",
                f"Texto '{(ent.texto or '')[:40]}' com altura {ent.altura:g} (permitidas: {alturas})",
            ))
        if estilos and ent.estilo not in estilos:
            problemas.append(_de_entidade(ent, "TXT02", "aviso", f"Texto com estilo '{ent.estilo}' não permitido"))
    return problemas


def _cotas(desenho: Desenho, cfg: dict) -> list[Problema]:
    estilos = cfg.get("estilos_permitidos")
    if not estilos:
        return []
    return [
        _de_entidade(ent, "COT01", "erro", f"Cota com estilo '{ent.estilo}' não permitido (use {estilos})")
        for ent in desenho.entidades
        if ent.tipo == "DIMENSION" and ent.estilo not in estilos
    ]


def _carimbo(desenho: Desenho, cfg: dict) -> list[Problema]:
    bloco = cfg.get("bloco")
    if not bloco:
        return []
    carimbos = [e for e in desenho.entidades if e.tipo == "INSERT" and (e.bloco or "").upper() == bloco.upper()]
    if not carimbos:
        return [Problema("CAR01", "erro", f"Carimbo (bloco '{bloco}') não encontrado no desenho")]
    problemas = []
    for carimbo in carimbos:
        for tag in cfg.get("atributos_obrigatorios", []):
            valor = carimbo.atributos.get(tag, "").strip()
            if not valor:
                problemas.append(_de_entidade(carimbo, "CAR02", "erro", f"Carimbo sem o campo '{tag}' preenchido"))
    return problemas


def _unidades(desenho: Desenho, esperada: int | None) -> list[Problema]:
    if esperada is None or desenho.unidades == esperada:
        return []
    return [Problema(
        "UNI01", "erro",
        f"Unidade do desenho é {UNIDADES.get(desenho.unidades, desenho.unidades)}, "
        f"esperado {UNIDADES.get(esperada, esperada)}",
    )]
