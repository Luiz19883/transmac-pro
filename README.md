# Revisor de desenhos AutoCAD com IA

Confere desenhos do AutoCAD em duas etapas:

1. **Regras da empresa** (`padroes.yaml`): nomenclatura e camadas obrigatórias,
   entidades na camada 0, cor fixa em vez de PorCamada, altura e estilo de texto,
   estilo de cota, carimbo com campos vazios e unidade do desenho.
2. **Claude**: aponta o que as regras fixas não pegam, como erros de ortografia,
   escala do carimbo que não bate com as cotas, notas contraditórias, conteúdo na
   camada errada e itens exigidos pelas normas descritas em `ia.instrucoes`.

O resultado é um relatório `<desenho>_revisao.md`. Com `--marcar`, cada problema
também ganha um círculo vermelho e uma nota na camada `REVISAO_IA` do próprio desenho.

## Instalação (Windows, com AutoCAD)

```bat
pip install -r requirements.txt
set ANTHROPIC_API_KEY=sk-ant-...
```

## Uso

```bat
:: revisa o desenho que está aberto no AutoCAD
python -m autocad_ia

:: abre um DWG, revisa e marca os problemas no desenho
python -m autocad_ia --dwg C:\obras\A01.dwg --marcar

:: só as regras, sem custo de IA
python -m autocad_ia --sem-ia

:: sem AutoCAD (qualquer sistema): revisa um DXF
python -m autocad_ia --dxf planta.dxf
```

O comando termina com código 1 quando há erros, então dá para usar em lote:

```bat
for %f in (C:\obras\*.dwg) do python -m autocad_ia --dwg "%f"
```

Para ir até um problema no AutoCAD, use o handle do relatório:
`(command "_zoom" "_object" (handent "2F1") "")`.

## Ajustando aos seus padrões

Edite o `padroes.yaml`. Qualquer seção pode ser removida para desligar a verificação.
Escreva as normas da empresa em texto livre em `ia.instrucoes`, porque é isso que a IA usa.

## Testes

```bash
pip install -r requirements.txt pytest
python -m pytest
```
