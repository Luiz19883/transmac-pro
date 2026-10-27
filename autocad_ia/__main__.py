"""Revisor de desenhos AutoCAD com IA.

Exemplos:
    python -m autocad_ia                         # revisa o desenho aberto no AutoCAD
    python -m autocad_ia --dwg C:\\obra\\A01.dwg   # abre e revisa um DWG
    python -m autocad_ia --dxf planta.dxf        # revisa um DXF sem AutoCAD
    python -m autocad_ia --sem-ia                # só as regras, sem chamar a IA
    python -m autocad_ia --marcar                # desenha círculos nos problemas
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

from .regras import verificar
from .relatorio import gerar_markdown

# padroes.yaml ao lado do pacote, para funcionar quando chamado de dentro do AutoCAD
PADROES_PADRAO = Path(__file__).resolve().parent.parent / "padroes.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="autocad_ia", description="Revisa desenhos AutoCAD com regras + IA.")
    origem = parser.add_mutually_exclusive_group()
    origem.add_argument("--dwg", help="abre este DWG no AutoCAD e revisa (Windows)")
    origem.add_argument("--dxf", help="revisa um arquivo DXF sem precisar do AutoCAD")
    parser.add_argument("--padroes", default=str(PADROES_PADRAO), help="arquivo de padrões da empresa")
    parser.add_argument("--saida", help="arquivo do relatório (padrão: <desenho>_revisao.md)")
    parser.add_argument("--sem-ia", action="store_true", help="não chama a IA, só as regras")
    parser.add_argument("--marcar", action="store_true", help="marca os problemas no desenho (camada REVISAO_IA)")
    parser.add_argument("--abrir", action="store_true", help="abre o relatório ao terminar (Windows)")
    args = parser.parse_args(argv)

    padroes = yaml.safe_load(Path(args.padroes).read_text(encoding="utf-8")) or {}

    doc = None
    if args.dxf:
        from .extrator_dxf import extrair_dxf
        desenho = extrair_dxf(args.dxf)
    else:
        from .extrator_autocad import conectar, extrair_autocad
        doc = conectar(args.dwg)
        print(f"Lendo {doc.Name} do AutoCAD...")
        desenho = extrair_autocad(doc)

    problemas = verificar(desenho, padroes)
    print(f"Regras: {len(problemas)} problema(s) em {len(desenho.entidades)} entidades.")

    resumo_ia = None
    if not args.sem_ia:
        from .revisor_ia import revisar
        print("Enviando para revisão da IA...")
        resumo_ia, da_ia = revisar(desenho, problemas, padroes.get("ia", {}).get("instrucoes", ""))
        problemas += da_ia
        print(f"IA: {len(da_ia)} apontamento(s).")

    saida = Path(args.saida or Path(desenho.arquivo).with_suffix("").as_posix() + "_revisao.md")
    saida.write_text(gerar_markdown(desenho, problemas, resumo_ia), encoding="utf-8")
    print(f"Relatório: {saida}")

    if args.marcar:
        if doc is None:
            print("--marcar só funciona com o AutoCAD (sem --dxf).", file=sys.stderr)
        else:
            from .extrator_autocad import marcar_problemas
            print(f"Marcados {marcar_problemas(doc, problemas)} problema(s) na camada REVISAO_IA.")

    if args.abrir and hasattr(os, "startfile"):
        os.startfile(saida)

    return 1 if any(p.gravidade == "erro" for p in problemas) else 0


if __name__ == "__main__":
    sys.exit(main())
