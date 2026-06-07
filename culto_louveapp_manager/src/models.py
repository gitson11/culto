"""Modelos de dados (dataclasses) do Culto LouveApp Manager.

Representa boletins de culto, pessoas, escalas do LouveApp e resultados de importação.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class WorshipBulletin:
    """Representa um boletim de culto (uma linha da antiga Planilha1/CULTOS)."""

    id: Optional[int] = None
    date_text: str = ""
    dirigente: str = ""

    # Prelúdio
    preludio_musica: str = ""
    preludio_cantor: str = ""
    preludio_tom: str = ""

    # Música 1
    musica1: str = ""
    cantor1: str = ""
    tom1: str = ""
    ref1: str = ""
    texto1: str = ""

    # Música 2
    musica2: str = ""
    cantor2: str = ""
    tom2: str = ""
    ref2: str = ""
    texto2: str = ""

    # Música 3
    musica3: str = ""
    cantor3: str = ""
    tom3: str = ""
    ref3: str = ""
    texto3: str = ""

    # Oração / Louvor
    oracao_louvor: str = ""
    ref_louvor: str = ""
    texto_louvor: str = ""

    # Ofertas
    ofertas_ref: str = ""
    ofertas_texto: str = ""
    ofertas_oracao: str = ""

    # Música 4
    musica4: str = ""
    cantor4: str = ""
    tom4: str = ""

    # Música 5
    musica5: str = ""
    cantor5: str = ""
    tom5: str = ""

    # Intercessão
    oracao_intercessao: str = ""

    # Pregador
    pregador: str = ""

    # Santa Ceia - Pão
    musica_pao: str = ""
    cantor_pao: str = ""
    tom_pao: str = ""

    # Santa Ceia - Vinho
    musica_vinho: str = ""
    cantor_vinho: str = ""
    tom_vinho: str = ""

    # Santa Ceia - Extra
    musica_extra: str = ""
    cantor_extra: str = ""
    tom_extra: str = ""

    # Música Final
    musica_final: str = ""
    cantor_final: str = ""
    tom_final: str = ""

    # Metadados
    source: str = "manual"
    raw_json: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat(timespec="seconds")
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def has_ceia(self) -> bool:
        """Retorna True se o boletim tem dados de Santa Ceia."""
        return bool(self.musica_pao or self.musica_vinho or self.musica_extra)

    # Campos na ordem da tabela do banco
    DB_FIELDS: tuple[str, ...] = (
        "date_text", "dirigente",
        "preludio_musica", "preludio_cantor", "preludio_tom",
        "musica1", "cantor1", "tom1", "ref1", "texto1",
        "musica2", "cantor2", "tom2", "ref2", "texto2",
        "musica3", "cantor3", "tom3", "ref3", "texto3",
        "oracao_louvor", "ref_louvor", "texto_louvor",
        "ofertas_ref", "ofertas_texto", "ofertas_oracao",
        "musica4", "cantor4", "tom4",
        "musica5", "cantor5", "tom5",
        "oracao_intercessao", "pregador",
        "musica_pao", "cantor_pao", "tom_pao",
        "musica_vinho", "cantor_vinho", "tom_vinho",
        "musica_extra", "cantor_extra", "tom_extra",
        "musica_final", "cantor_final", "tom_final",
        "source", "raw_json", "created_at", "updated_at",
    )


@dataclass
class WorshipPerson:
    """Pessoa integrante do ministério de louvor."""

    id: Optional[int] = None
    name: str = ""
    active: int = 1
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat(timespec="seconds")


@dataclass
class LouveAppSchedule:
    """Escala importada do LouveApp."""

    id: Optional[int] = None
    category: str = ""
    title: str = ""
    date_text: str = ""
    time_text: str = ""
    ministry: str = ""
    role: str = ""
    person_name: str = ""
    people_text: str = ""
    raw_text: str = ""
    page_url: str = ""
    raw_json: str = ""
    imported_at: str = ""

    def __post_init__(self):
        if not self.imported_at:
            self.imported_at = datetime.now().isoformat(timespec="seconds")


@dataclass
class ImportResult:
    """Resultado de uma operação de importação."""

    source: str = ""
    status: str = "success"
    message: str = ""
    records_count: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "success"
