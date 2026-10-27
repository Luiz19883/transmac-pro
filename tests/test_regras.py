from pathlib import Path

import ezdxf
import yaml

from autocad_ia.__main__ import main
from autocad_ia.extrator_dxf import extrair_dxf
from autocad_ia.regras import verificar

PADROES = yaml.safe_load((Path(__file__).parent.parent / "padroes.yaml").read_text(encoding="utf-8"))


def _criar_dxf(caminho: Path, carimbo_completo: bool = True) -> Path:
    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 5
    for nome in ("COT-COTAS", "TXT-TEXTOS", "CAR-CARIMBO", "ARQ-PAREDE", "parede velha"):
        doc.layers.add(nome)
    doc.styles.add("ROMANS", font="romans.shx")
    doc.dimstyles.new("COTA-1-50")
    msp = doc.modelspace()

    msp.add_line((0, 0), (500, 0), dxfattribs={"layer": "ARQ-PAREDE"})
    msp.add_line((0, 0), (0, 300), dxfattribs={"layer": "0"})  # ENT01
    msp.add_line((0, 300), (500, 300), dxfattribs={"layer": "ARQ-PAREDE", "color": 1})  # ENT02
    msp.add_text("SALA", height=2.5, dxfattribs={"layer": "TXT-TEXTOS", "style": "ROMANS"})
    msp.add_text("COZINHA", height=4, dxfattribs={"layer": "TXT-TEXTOS", "style": "ROMANS"})  # TXT01
    msp.add_text("BANHEIRO", height=2.5, dxfattribs={"layer": "TXT-TEXTOS", "style": "Standard"})  # TXT02
    msp.add_linear_dim(base=(0, -20), p1=(0, 0), p2=(500, 0), dimstyle="Standard",
                       dxfattribs={"layer": "COT-COTAS"}).render()  # COT01

    bloco = doc.blocks.new("CARIMBO")
    for i, tag in enumerate(PADROES["carimbo"]["atributos_obrigatorios"]):
        bloco.add_attdef(tag, (0, -i * 5), dxfattribs={"height": 2.5})
    valores = {tag: "X" for tag in PADROES["carimbo"]["atributos_obrigatorios"]}
    if not carimbo_completo:
        valores["ESCALA"] = ""
    msp.add_blockref("CARIMBO", (600, 0), dxfattribs={"layer": "CAR-CARIMBO"}).add_auto_attribs(valores)

    doc.saveas(caminho)
    return caminho


def test_extrai_entidades_do_dxf(tmp_path):
    desenho = extrair_dxf(_criar_dxf(tmp_path / "a.dxf"))
    tipos = {e.tipo for e in desenho.entidades}
    assert {"LINE", "TEXT", "INSERT", "DIMENSION"} <= tipos
    carimbo = next(e for e in desenho.entidades if e.bloco == "CARIMBO")
    assert carimbo.atributos["PROJETO"] == "X"
    assert desenho.unidades == 5


def test_regras_encontram_cada_problema(tmp_path):
    desenho = extrair_dxf(_criar_dxf(tmp_path / "a.dxf", carimbo_completo=False))
    codigos = {p.codigo for p in verificar(desenho, PADROES)}
    assert {"CAM01", "ENT01", "ENT02", "TXT01", "TXT02", "COT01", "CAR02"} <= codigos
    assert "UNI01" not in codigos
    assert "CAR01" not in codigos


def test_carimbo_ausente_e_unidade_errada(tmp_path):
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 6
    caminho = tmp_path / "b.dxf"
    doc.saveas(caminho)
    codigos = {p.codigo for p in verificar(extrair_dxf(caminho), PADROES)}
    assert {"CAR01", "UNI01", "CAM02"} <= codigos


def test_cli_sem_ia_gera_relatorio(tmp_path):
    caminho = _criar_dxf(tmp_path / "planta.dxf")
    padroes = Path(__file__).parent.parent / "padroes.yaml"
    codigo = main(["--dxf", str(caminho), "--padroes", str(padroes), "--sem-ia"])
    relatorio = (tmp_path / "planta_revisao.md").read_text(encoding="utf-8")
    assert codigo == 1  # há erros
    assert "ENT01" in relatorio and "COT01" in relatorio
