from __future__ import annotations

import json
import re
from typing import Iterable, Optional

from src.models import LouveAppSchedule, now_text


DATE_PATTERNS = [
    re.compile(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b"),
    re.compile(
        r"\b(?:domingo|segunda(?:-feira)?|terca(?:-feira)?|terça(?:-feira)?|quarta(?:-feira)?|quinta(?:-feira)?|sexta(?:-feira)?|sabado|sábado),?\s+\d{1,2}\s+de\s+[a-zç]+",
        re.IGNORECASE,
    ),
    re.compile(r"\b\d{1,2}\s+de\s+[a-zç]+\b", re.IGNORECASE),
]

TIME_RE = re.compile(r"\b(?:[01]?\d|2[0-3])(?::\d{2}|h(?:\d{2})?)\b", re.IGNORECASE)

ROLE_TERMS = [
    "Ministro",
    "Dirigente",
    "Pregador",
    "Vocal",
    "Back vocal",
    "Teclado",
    "Piano",
    "Violao",
    "Violão",
    "Guitarra",
    "Baixo",
    "Bateria",
    "Midia",
    "Mídia",
    "Projecao",
    "Projeção",
    "Som",
    "Recepcao",
    "Recepção",
    "Intercessao",
    "Intercessão",
    "Ceia",
    "Leitura biblica",
    "Leitura bíblica",
    "Louvor",
    "Ofertorio",
    "Ofertório",
    "Santa Ceia",
]

MINISTRY_TERMS = [
    "Louvor",
    "Ministerio",
    "Ministério",
    "Culto",
    "Escala",
    "Agenda",
    "Evento",
    "Voluntarios",
    "Voluntários",
    "Servicos",
    "Serviços",
]


def clean_text(raw_text: str) -> str:
    lines = [" ".join(line.strip().split()) for line in (raw_text or "").splitlines()]
    return "\n".join([line for line in lines if line])


def find_first(patterns: Iterable[re.Pattern], text: str) -> str:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(0).strip()
    return ""


def find_time(text: str) -> str:
    match = TIME_RE.search(text)
    return match.group(0).strip() if match else ""


def find_term(text: str, terms: list[str]) -> str:
    normalized = text.casefold()
    for term in terms:
        if term.casefold() in normalized:
            return term
    return ""


def looks_like_person(line: str) -> bool:
    if not line or len(line) > 80:
        return False
    if find_first(DATE_PATTERNS, line) or find_time(line):
        return False
    if find_term(line, ROLE_TERMS + MINISTRY_TERMS):
        return False
    words = re.findall(r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+", line)
    return len(words) >= 2


def extract_person(text: str) -> str:
    for line in clean_text(text).splitlines():
        if ":" in line:
            left, right = [part.strip() for part in line.split(":", 1)]
            if find_term(left, ROLE_TERMS) and right:
                return right
        if " - " in line:
            left, right = [part.strip() for part in line.split(" - ", 1)]
            if find_term(right, ROLE_TERMS) and left:
                return left
        if looks_like_person(line):
            return line
    return ""


def extract_people_text(text: str) -> str:
    people = []
    for line in clean_text(text).splitlines():
        if looks_like_person(line):
            people.append(line)
    return "; ".join(dict.fromkeys(people))


def extract_title(text: str) -> str:
    for line in clean_text(text).splitlines():
        if 3 <= len(line) <= 90:
            return line
    return ""


def is_relevant_schedule_text(text: str) -> bool:
    if not text.strip():
        return False
    return bool(
        find_first(DATE_PATTERNS, text)
        or find_time(text)
        or find_term(text, ROLE_TERMS)
        or find_term(text, MINISTRY_TERMS)
        or extract_person(text)
    )


def parse_schedule_text(raw_text: str, page_url: str = "", category: str = "") -> Optional[LouveAppSchedule]:
    text = clean_text(raw_text)
    if not is_relevant_schedule_text(text):
        return None

    date_text = find_first(DATE_PATTERNS, text)
    time_text = find_time(text)
    role = find_term(text, ROLE_TERMS)
    ministry = find_term(text, MINISTRY_TERMS)
    person_name = extract_person(text)
    people_text = extract_people_text(text)
    title = extract_title(text)
    raw_json = json.dumps(
        {
            "category": category,
            "date_text": date_text,
            "time_text": time_text,
            "role": role,
            "ministry": ministry,
            "person_name": person_name,
            "page_url": page_url,
        },
        ensure_ascii=False,
    )
    return LouveAppSchedule(
        category=category,
        title=title,
        date_text=date_text,
        time_text=time_text,
        ministry=ministry,
        role=role,
        person_name=person_name,
        people_text=people_text,
        raw_text=text,
        page_url=page_url,
        raw_json=raw_json,
        imported_at=now_text(),
    )


def parse_body_fallback(raw_text: str, page_url: str = "", category: str = "fallback") -> list[LouveAppSchedule]:
    schedules: list[LouveAppSchedule] = []
    lines = clean_text(raw_text).splitlines()
    window: list[str] = []

    for line in lines:
        if is_relevant_schedule_text(line):
            window.append(line)
            if len(window) >= 4:
                schedule = parse_schedule_text("\n".join(window), page_url, category)
                if schedule:
                    schedules.append(schedule)
                window = []

    if window:
        schedule = parse_schedule_text("\n".join(window), page_url, category)
        if schedule:
            schedules.append(schedule)

    return dedupe_schedules(schedules)


def dedupe_schedules(schedules: Iterable[LouveAppSchedule]) -> list[LouveAppSchedule]:
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[LouveAppSchedule] = []
    for schedule in schedules:
        key = (
            schedule.raw_text.casefold(),
            schedule.page_url,
            schedule.date_text,
            schedule.person_name.casefold(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(schedule)
    return unique
