# Placeholders aceitos nos modelos de boletim

Coloque estes marcadores dentro dos arquivos `.docx` em `templates/`.

O sistema substitui os placeholders no corpo do documento, tabelas, cabeçalhos e rodapés.

## Dados gerais

```text
{{DATA}}
{{DIRIGENTE}}
{{PREGADOR}}
```

## Prelúdio

```text
{{PRELUDIO_MUSICA}}
{{PRELUDIO_CANTOR}}
{{PRELUDIO_TOM}}
```

## Louvor congregacional

```text
{{MUSICA1}}
{{CANTOR1}}
{{TOM1}}
{{REF1}}
{{TEXTO1}}

{{MUSICA2}}
{{CANTOR2}}
{{TOM2}}
{{REF2}}
{{TEXTO2}}

{{MUSICA3}}
{{CANTOR3}}
{{TOM3}}
{{REF3}}
{{TEXTO3}}
```

## Oração / leitura / transição

```text
{{ORACAO_LOUVOR}}
{{REF_LOUVOR}}
{{TEXTO_LOUVOR}}
```

## Ofertas

```text
{{OFERTAS_REF}}
{{OFERTAS_TEXTO}}
{{OFERTAS_ORACAO}}
```

## Músicas finais

```text
{{MUSICA4}}
{{CANTOR4}}
{{TOM4}}

{{MUSICA5}}
{{CANTOR5}}
{{TOM5}}
```

## Intercessão

```text
{{ORACAO_INTERCESSAO}}
```

## Santa Ceia

```text
{{MUSICA_PAO}}
{{CANTOR_PAO}}
{{TOM_PAO}}

{{MUSICA_VINHO}}
{{CANTOR_VINHO}}
{{TOM_VINHO}}

{{MUSICA_EXTRA}}
{{CANTOR_EXTRA}}
{{TOM_EXTRA}}

{{MUSICA_FINAL}}
{{CANTOR_FINAL}}
{{TOM_FINAL}}
```

## Observações

- Se algum campo estiver vazio no cadastro, o placeholder será substituído por texto vazio.
- Para mudar o visual do boletim, edite o arquivo `.docx` do modelo, não o código Python.
- Evite quebrar um placeholder manualmente com formatações internas diferentes, como `{{MU` em negrito e `SICA1}}` normal. O sistema tenta lidar com runs quebrados, mas placeholders contínuos são mais seguros.
