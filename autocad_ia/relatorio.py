"""Gera o relatório da revisão em Markdown."""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from .modelo import Desenho
from .regras import Problema


def gerar_markdown(desenho: Desenho, problemas: list[Problema], resumo_ia: str | None) -> str:
    erros = sum(p.gravidade == "erro" for p in problemas)
    avisos = len(problemas) - erros
    linhas = [
        f"# Revisão de desenho: {desenho.arquivo}",
        "",
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M} · {len(desenho.entidades)} entidades · "
        f"{len(desenho.camadas)} camadas",
        "",
        f"**{erros} erro(s), {avisos} aviso(s)**",
        "",
    ]
    if resumo_ia:
        linhas += ["## Parecer da IA", "", resumo_ia, ""]

    linhas += ["## Resumo por código", "", "| Código | Gravidade | Ocorrências |", "|---|---|---|"]
    contagem = Counter((p.codigo, p.gravidade) for p in problemas)
    for (codigo, gravidade), n in sorted(contagem.items()):
        linhas.append(f"| {codigo} | {gravidade} | {n} |")

    linhas += ["", "## Detalhes", "", "| Código | Mensagem | Camada | Handle | Posição | Origem |", "|---|---|---|---|---|---|"]
    for p in sorted(problemas, key=lambda p: (p.gravidade != "erro", p.codigo)):
        posicao = f"{p.posicao[0]:g}, {p.posicao[1]:g}" if p.posicao else ""
        mensagem = p.mensagem.replace("|", "\\|")
        linhas.append(f"| {p.codigo} | {mensagem} | {p.camada or ''} | {p.handle or ''} | {posicao} | {p.origem} |")
    linhas.append("")
    linhas.append("Dica: no AutoCAD, localize uma entidade pelo handle com `(command \"_zoom\" \"_object\" (handent \"HANDLE\") \"\")`.")
    return "\n".join(linhas) + "\n"
