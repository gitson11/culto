from __future__ import annotations

from dataclasses import dataclass

from src.database import Database
from src.models import WorshipPerson
from src.scale_models import ScaleModel, ScaleModelSlot
from src.scale_models_repository import ScaleModelRepository


@dataclass
class GeneratedScaleAssignment:
    function_name: str
    person_name: str
    reason: str
    warning: str = ""


@dataclass
class GeneratedScaleResult:
    model: ScaleModel
    assignments: list[GeneratedScaleAssignment]
    warnings: list[str]


def _tokens(value: str) -> set[str]:
    return {
        token.strip().casefold()
        for token in (value or "").replace(";", ",").replace("/", ",").split(",")
        if token.strip()
    }


def _contains_any(haystack: str, needles: set[str]) -> bool:
    text = (haystack or "").casefold()
    return any(needle and needle in text for needle in needles)


def _person_roles(person: WorshipPerson) -> str:
    return " ".join([person.primary_roles or "", person.secondary_roles or "", person.instruments or "", person.voice or ""])


def _score_person(person: WorshipPerson, slot: ScaleModelSlot, service_date: str = "") -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    function_tokens = _tokens(slot.function_name)
    instrument_tokens = _tokens(slot.desired_instruments)
    voice_tokens = _tokens(slot.desired_voice)
    role_text = _person_roles(person)

    if function_tokens and _contains_any(role_text, function_tokens):
        score += 50
        reasons.append("funcao compativel")
    if instrument_tokens and _contains_any(person.instruments, instrument_tokens):
        score += 40
        reasons.append("instrumento compativel")
    if voice_tokens and _contains_any(person.voice, voice_tokens):
        score += 30
        reasons.append("voz compativel")
    if service_date and _contains_any(person.availability, _tokens(service_date)):
        score += 15
        reasons.append("disponibilidade indicada")
    if (person.experience_level or "").casefold() in {"experiente", "lider"}:
        score += 8
        reasons.append("experiencia")
    if (person.status or "").casefold() == "treinamento":
        score -= 10
        reasons.append("em treinamento")

    return score, reasons


class ScaleGenerator:
    def __init__(self, database: Database | None = None, repository: ScaleModelRepository | None = None) -> None:
        self.database = database or Database()
        self.repository = repository or ScaleModelRepository()

    def generate(self, model_id: int, service_date: str = "") -> GeneratedScaleResult:
        model = self.repository.get_model(model_id)
        if not model:
            raise ValueError("Modelo de escala nao encontrado.")
        slots = self.repository.list_slots(model_id)
        if not slots:
            raise ValueError("Este modelo ainda nao possui funcoes cadastradas.")
        people = self.database.list_people(active_only=True)
        if not people:
            raise ValueError("Nao ha integrantes ativos cadastrados no ministerio.")

        assignments: list[GeneratedScaleAssignment] = []
        warnings: list[str] = []
        used_person_ids: set[int] = set()

        for slot in slots:
            quantity = max(1, int(slot.quantity or 1))
            for _index in range(quantity):
                chosen, score, reasons = self._choose_person(slot, people, used_person_ids, service_date)
                if chosen:
                    used_person_ids.add(chosen.id or -1)
                    warning = "" if score > 0 else "Baixa compatibilidade; revise manualmente."
                    if warning:
                        warnings.append(f"{slot.function_name}: {warning}")
                    assignments.append(
                        GeneratedScaleAssignment(
                            function_name=slot.function_name,
                            person_name=chosen.name,
                            reason=", ".join(reasons) if reasons else "melhor opcao disponivel",
                            warning=warning,
                        )
                    )
                else:
                    warning = "Nenhum integrante ativo disponivel para esta funcao."
                    warnings.append(f"{slot.function_name}: {warning}")
                    assignments.append(
                        GeneratedScaleAssignment(
                            function_name=slot.function_name,
                            person_name="",
                            reason="sem sugestao",
                            warning=warning,
                        )
                    )
        return GeneratedScaleResult(model=model, assignments=assignments, warnings=warnings)

    def _choose_person(
        self,
        slot: ScaleModelSlot,
        people: list[WorshipPerson],
        used_person_ids: set[int],
        service_date: str,
    ) -> tuple[WorshipPerson | None, int, list[str]]:
        ranked: list[tuple[int, str, WorshipPerson, list[str]]] = []
        for person in people:
            if person.id in used_person_ids:
                continue
            score, reasons = _score_person(person, slot, service_date)
            ranked.append((score, person.name.casefold(), person, reasons))
        if not ranked:
            return None, 0, []
        ranked.sort(key=lambda item: (-item[0], item[1]))
        score, _name, person, reasons = ranked[0]
        return person, score, reasons
