"""Revisão do desenho com Claude: o que regras fixas não pegam.

Exemplos: erros de ortografia, escala do carimbo incoerente com as cotas,
nomes de camada que "parecem" certos mas estão no lugar errado, notas
contraditórias, itens exigidos por norma que estão faltando.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Literal

import anthropic
from pydantic import BaseModel

from .modelo import Desenho
from .regras import UNIDADES, Problema

MODELO = "claude-opus-5-5"

SISTEMA = """Você é um revisor sênior de desenhos técnicos de AutoCAD.
Recebe um resumo estruturado de um desenho (camadas, textos, blocos, cotas) e
os problemas já encontrados por regras automáticas. Seu trabalho é encontrar o
que as regras NÃO pegaram: erros de ortografia e digitação nos textos, dados do
carimbo incoerentes entre si ou com o desenho (escala, unidade, data, revisão),
notas contraditórias, conteúdo em camada semanticamente errada (ex.: texto de
cota numa camada de alvenaria), e itens exigidos pelas normas da empresa que
estão ausentes. Não repita os problemas já listados pelas regras.
Cite os handles das entidades envolvidas sempre que houver. Seja específico e
objetivo; se o desenho estiver bom, devolva poucos ou nenhum apontamento."""


class Apontamento(BaseModel):
    codigo: str  # prefixo IA, ex.: IA-ORT (ortografia), IA-CAR (carimbo)
    gravidade: Literal["erro", "aviso"]
    mensagem: str
    handles: list[str]


class Revisao(BaseModel):
    resumo: str
    apontamentos: list[Apontamento]


def resumir(desenho: Desenho, problemas: list[Problema]) -> dict:
    """Monta um resumo compacto: textos repetidos viram uma linha só com todos os handles."""
    textos: dict[tuple, list[str]] = defaultdict(list)
    blocos = []
    estilos_cota = Counter()
    por_camada = Counter()
    for ent in desenho.entidades:
        por_camada[(ent.camada, ent.tipo)] += 1
        if ent.texto:
            textos[(ent.texto.strip(), ent.camada, ent.altura)].append(ent.handle)
        elif ent.tipo == "INSERT" and ent.atributos:
            blocos.append({"handle": ent.handle, "bloco": ent.bloco, "camada": ent.camada, "atributos": ent.atributos})
        elif ent.tipo == "DIMENSION":
            estilos_cota[ent.estilo] += 1
    return {
        "arquivo": desenho.arquivo,
        "unidade": UNIDADES.get(desenho.unidades, desenho.unidades),
        "camadas": [{"nome": c.nome, "cor": c.cor, "tipo_linha": c.tipo_linha} for c in desenho.camadas],
        "contagem_por_camada": [{"camada": c, "tipo": t, "qtd": n} for (c, t), n in sorted(por_camada.items())],
        "textos": [
            {"texto": t, "camada": c, "altura": a, "handles": h}
            for (t, c, a), h in textos.items()
        ],
        "blocos_com_atributos": blocos,
        "estilos_de_cota": dict(estilos_cota),
        "problemas_das_regras": dict(Counter(f"{p.codigo}: {p.mensagem}" for p in problemas)),
    }


def revisar(desenho: Desenho, problemas: list[Problema], instrucoes: str = "") -> tuple[str, list[Problema]]:
    resumo = resumir(desenho, problemas)
    pedido = (
        f"Normas e padrões da empresa:\n{instrucoes or '(não informadas)'}\n\n"
        f"Resumo do desenho (JSON):\n{json.dumps(resumo, ensure_ascii=False)}"
    )
    client = anthropic.Anthropic()
    resposta = client.beta.messages.parse(
        model=MODELO,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        # Se o modelo recusar o pedido, a API repete com um modelo reserva.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SISTEMA,
        messages=[{"role": "user", "content": pedido}],
        output_format=Revisao,
    )
    if resposta.stop_reason == "refusal":
        return "A IA não concluiu a revisão (recusa).", []
    if resposta.stop_reason == "max_tokens" or resposta.parsed_output is None:
        return "A resposta da IA foi cortada; tente um desenho menor ou divida por layout.", []

    revisao = resposta.parsed_output
    por_handle = {e.handle: e for e in desenho.entidades}
    novos = []
    for ap in revisao.apontamentos:
        entidades = [por_handle[h] for h in ap.handles if h in por_handle]
        if not entidades:
            novos.append(Problema(ap.codigo, ap.gravidade, ap.mensagem, origem="ia"))
        for ent in entidades:
            novos.append(Problema(ap.codigo, ap.gravidade, ap.mensagem, ent.handle, ent.camada, ent.layout, ent.posicao, origem="ia"))
    return revisao.resumo, novos
