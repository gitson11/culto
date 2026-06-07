#!/usr/bin/env python3
"""Valida placeholders entre os modelos Word, o template HTML e o PHP."""

from pathlib import Path
from zipfile import ZipFile
import re
import sys

DOC_FILES = [
    "MODELO DE BOLETIM.docx",
    "MODELO DE BOLETIM CEIA.docx",
]

MAPPING = {
    "#DATA": "data_texto",
    "#DIRIGENTE": "dirigente",
    "#PBANDA": "dirigente",
    "#PREGADOR": "pregador",
    "#PRELUDIO": "preludio",
    "#PMUSICA": "preludio",
    "#PTOQUE": "tom_preludio",
    "#PTOM": "tom_preludio",
    "#REF": "ref",
    "#REF1": "ref",
    "#DBIB": "ref",
    "#TEXTO": "texto",
    "#MUSICA1": "musica1",
    "#CANTOR1": "cantor1",
    "#TOM1": "tom1",
    "#MUSICA2": "musica2",
    "#CANTOR2": "cantor2",
    "#TOM2": "tom2",
    "#MUSICA3": "musica3",
    "#CANTOR3": "cantor3",
    "#TOM3": "tom3",
    "#MUSICA": "musica_oferta",
    "#MUSICA_OFERTA": "musica_oferta",
    "#CANTOR5": "cantor_oferta",
    "#CANTOR_OFERTA": "cantor_oferta",
    "#TOM5": "tom_oferta",
    "#TOM_OFERTA": "tom_oferta",
    "#PAO": "musica_pao",
    "#VINHO": "musica_vinho",
    "#MUSICA_PAO": "musica_pao",
    "#MUSICA_VINHO": "musica_vinho",
    "#MUSICA_EXTRA": "musica_extra",
    "#MUSICA_FINAL": "musica_final",
    "#CANTOR_FINAL": "cantor_final",
    "#TOM_FINAL": "tom_final",
    "#ORACAO": "oracao",
    "#ORACAO1": "oracao",
    "#ORACAO_2": "oracao_2",
    "#OFERTAS_REF": "ofertas_ref",
    "#OFERTAS_TEXTO": "ofertas_texto",
    "#INTERCESSAO": "intercessao",
    "#LOUVOR": "musica_extra",
}


def extract_word_placeholders(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with ZipFile(path) as z:
        try:
            xml = z.read("word/document.xml").decode("utf-8")
        except KeyError:
            return set()
    return {f"#{token}" for token in re.findall(r"#([A-Z0-9_]+)", xml)}


def extract_template_fields(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = path.read_text(encoding="utf-8")
    return {match.strip() for match in re.findall(r"{{\s*([a-zA-Z0-9_]+)\s*}}", data)}


def extract_php_fields(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = path.read_text(encoding="utf-8")
    return set(match.strip() for match in re.findall(r"'{{\s*([a-zA-Z0-9_]+)\s*}}'\s*=>", data))


def main() -> None:
    root = Path(".")
    word_placeholders = set()
    for doc in DOC_FILES:
        word_placeholders.update(extract_word_placeholders(root / doc))

    template_fields = extract_template_fields(root / "backend/templates/boletim-template.html")
    php_fields = extract_php_fields(root / "backend/boletim.php")

    print("Placeholders do Word:")
    print(", ".join(sorted(word_placeholders)) or "  (nenhum)")
    print()

    print(f"Template (HTML) -> campos: {', '.join(sorted(template_fields))}")
    print(f"PHP -> campos: {', '.join(sorted(php_fields))}")
    print()

    unmapped = sorted(p for p in word_placeholders if p not in MAPPING)
    if unmapped:
        print("Placeholders sem mapeamento para um campo:")
        for placeholder in unmapped:
            print(f"  - {placeholder}")
        print()

    print("Cobertura dos mapeamentos:")
    for placeholder, field in sorted(MAPPING.items()):
        template_has = field in template_fields
        php_has = field in php_fields
        status = "[ok]" if template_has and php_has else "[miss]"
        print(f"  {status} {placeholder} -> {field} (template:{template_has} php:{php_has})")

    extras = sorted(f for f in template_fields if f not in MAPPING.values())
    if extras:
        print("\nCampos extras no template sem placeholder correspondente:")
        for field in extras:
            print(f"  - {field}")

    sys.exit(0)


if __name__ == "__main__":
    main()
