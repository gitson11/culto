from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

import customtkinter as ctk

from src.bulletin import generate_bulletin_by_date, generate_bulletin_docx
from src.config import DEBUG_DIR, OUTPUT_DIR
from src.database import Database
from src.exporters import (
    export_bulletins_csv,
    export_bulletins_xlsx,
    export_louveapp_schedules_csv,
    export_louveapp_schedules_xlsx,
)
from src.legacy_excel import import_legacy_bulletins, import_legacy_people, inspect_legacy_workbook
from src.logger import LOG_PATH, get_logger
from src.louveapp_browser import import_louveapp_schedules
from src.models import ImportResult, WorshipBulletin
from src.repertoire import generate_repertoire_by_date, generate_repertoire_docx


logger = get_logger(__name__)


BULLETIN_FIELD_SPECS = [
    ("date_text", "Data"),
    ("dirigente", "Dirigente"),
    ("preludio_musica", "Preludio"),
    ("preludio_cantor", "Cantor Preludio"),
    ("preludio_tom", "Tom Preludio"),
    ("musica1", "Musica 1"),
    ("cantor1", "Cantor 1"),
    ("tom1", "Tom 1"),
    ("ref1", "Ref 1"),
    ("texto1", "Texto 1"),
    ("musica2", "Musica 2"),
    ("cantor2", "Cantor 2"),
    ("tom2", "Tom 2"),
    ("ref2", "Ref 2"),
    ("texto2", "Texto 2"),
    ("musica3", "Musica 3"),
    ("cantor3", "Cantor 3"),
    ("tom3", "Tom 3"),
    ("ref3", "Ref 3"),
    ("texto3", "Texto 3"),
    ("oracao_louvor", "Oracao Louvor"),
    ("ref_louvor", "Ref Louvor"),
    ("texto_louvor", "Texto Louvor"),
    ("ofertas_ref", "Ofertas Ref"),
    ("ofertas_texto", "Ofertas Texto"),
    ("ofertas_oracao", "Ofertas Oracao"),
    ("musica4", "Musica 4"),
    ("cantor4", "Cantor 4"),
    ("tom4", "Tom 4"),
    ("musica5", "Musica 5"),
    ("cantor5", "Cantor 5"),
    ("tom5", "Tom 5"),
    ("oracao_intercessao", "Oracao Intercessao"),
    ("pregador", "Pregador"),
    ("musica_pao", "Musica Pao"),
    ("cantor_pao", "Cantor Pao"),
    ("tom_pao", "Tom Pao"),
    ("musica_vinho", "Musica Vinho"),
    ("cantor_vinho", "Cantor Vinho"),
    ("tom_vinho", "Tom Vinho"),
    ("musica_extra", "Musica Extra"),
    ("cantor_extra", "Cantor Extra"),
    ("tom_extra", "Tom Extra"),
    ("musica_final", "Musica Final"),
    ("cantor_final", "Cantor Final"),
    ("tom_final", "Tom Final"),
]

LONG_TEXT_FIELDS = {"texto1", "texto2", "texto3", "texto_louvor", "ofertas_texto"}
MUSIC_FIELD_NAMES = {
    "preludio_musica",
    "musica1",
    "musica2",
    "musica3",
    "musica4",
    "musica5",
    "musica_pao",
    "musica_vinho",
    "musica_extra",
    "musica_final",
}
MUSIC_TO_KEY_FIELD = {
    "preludio_musica": "preludio_tom",
    "musica1": "tom1",
    "musica2": "tom2",
    "musica3": "tom3",
    "musica4": "tom4",
    "musica5": "tom5",
    "musica_pao": "tom_pao",
    "musica_vinho": "tom_vinho",
    "musica_extra": "tom_extra",
    "musica_final": "tom_final",
}
MUSIC_TO_SINGER_FIELD = {
    "preludio_musica": "preludio_cantor",
    "musica1": "cantor1",
    "musica2": "cantor2",
    "musica3": "cantor3",
    "musica4": "cantor4",
    "musica5": "cantor5",
    "musica_pao": "cantor_pao",
    "musica_vinho": "cantor_vinho",
    "musica_extra": "cantor_extra",
    "musica_final": "cantor_final",
}


class CultoLouveAppManager(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")

        self.db = Database()
        self.worker_queue: queue.Queue = queue.Queue()
        self.current_bulletin_id: Optional[int] = None
        self.current_person_id: Optional[int] = None
        self.bulletin_widgets: dict[str, tk.Widget] = {}
        self.schedule_combo_values: dict[str, dict[str, str]] = {}
        self.selected_schedule: Optional[dict[str, str]] = None
        self.schedule_song_choices: dict[str, dict[str, str]] = {}

        self.title("Culto LouveApp Manager")
        self.geometry("1280x820")
        self.minsize(1100, 720)
        self._configure_ttk()
        self._build_layout()
        self.refresh_all()
        self.after(300, self._poll_worker_queue)

    def _configure_ttk(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_layout(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(header, text="Culto LouveApp Manager", font=("Segoe UI", 22, "bold")).pack(side="left")
        ctk.CTkButton(header, text="Atualizar", width=110, command=self.refresh_all).pack(side="right")

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)
        for tab_name in (
            "Dashboard",
            "Boletins",
            "Importar LouveApp",
            "Importar Excel Legado",
            "Pessoas do Louvor",
            "Exportacoes",
            "Debug/Logs",
        ):
            self.tabs.add(tab_name)

        self._build_dashboard_tab()
        self._build_bulletins_tab()
        self._build_louveapp_tab()
        self._build_legacy_tab()
        self._build_people_tab()
        self._build_exports_tab()
        self._build_logs_tab()

    def _build_dashboard_tab(self) -> None:
        tab = self.tabs.tab("Dashboard")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(tab, text="Resumo operacional", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 8)
        )
        metrics = ctk.CTkFrame(tab)
        metrics.grid(row=1, column=0, sticky="nsew", padx=16, pady=12)
        metrics.grid_columnconfigure((0, 1), weight=1)

        self.dashboard_labels: dict[str, ctk.CTkLabel] = {}
        labels = [
            ("bulletins", "Total de boletins"),
            ("people", "Pessoas do louvor ativas"),
            ("schedules", "Escalas LouveApp importadas"),
            ("last_bulletin", "Ultimo boletim cadastrado"),
            ("last_import", "Ultima importacao"),
        ]
        for index, (key, label) in enumerate(labels):
            row = index // 2
            column = index % 2
            item = ctk.CTkFrame(metrics, fg_color="transparent")
            item.grid(row=row, column=column, sticky="ew", padx=12, pady=10)
            ctk.CTkLabel(item, text=label, font=("Segoe UI", 12, "bold")).pack(anchor="w")
            value_label = ctk.CTkLabel(item, text="-", anchor="w", justify="left")
            value_label.pack(anchor="w", fill="x")
            self.dashboard_labels[key] = value_label

    def _build_bulletins_tab(self) -> None:
        tab = self.tabs.tab("Boletins")
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(0, weight=1)

        form_panel = ctk.CTkFrame(tab)
        form_panel.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        form_panel.grid_columnconfigure(0, weight=1)
        form_panel.grid_rowconfigure(2, weight=1)

        button_bar = ctk.CTkFrame(form_panel, fg_color="transparent")
        button_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        for text, command in (
            ("Novo", self._new_bulletin),
            ("Salvar", self._save_bulletin),
            ("Editar", self._edit_bulletin),
            ("Excluir", self._delete_bulletin),
            ("Limpar", self._clear_bulletin_form),
            ("Gerar Boletim", self._generate_bulletin_from_selection),
            ("Gerar Repertorio", self._generate_repertoire_from_selection),
        ):
            ctk.CTkButton(button_bar, text=text, width=112, command=command).pack(side="left", padx=4)

        schedule_bar = ctk.CTkFrame(form_panel, fg_color="transparent")
        schedule_bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        schedule_bar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(schedule_bar, text="Escala LouveApp").grid(row=0, column=0, sticky="w", padx=(4, 8))
        self.bulletin_schedule_combo = ctk.CTkComboBox(
            schedule_bar,
            values=["Sem escala selecionada"],
            state="readonly",
            command=self._on_bulletin_schedule_selected,
        )
        self.bulletin_schedule_combo.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.bulletin_schedule_combo.set("Sem escala selecionada")
        ctk.CTkButton(schedule_bar, text="Limpar escala", width=110, command=self._clear_selected_schedule).grid(
            row=0, column=2, padx=(0, 8)
        )
        self.schedule_hint_label = ctk.CTkLabel(schedule_bar, text="Musicas livres para preenchimento manual.")
        self.schedule_hint_label.grid(row=0, column=3, sticky="w")

        scroll = ctk.CTkScrollableFrame(form_panel)
        scroll.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        scroll.grid_columnconfigure(1, weight=1)

        for row_index, (field_name, label) in enumerate(BULLETIN_FIELD_SPECS):
            ctk.CTkLabel(scroll, text=label).grid(row=row_index, column=0, sticky="w", padx=(4, 10), pady=4)
            if field_name in LONG_TEXT_FIELDS:
                widget = ctk.CTkTextbox(scroll, height=70, wrap="word")
            elif field_name in MUSIC_FIELD_NAMES:
                widget = ctk.CTkComboBox(
                    scroll,
                    values=[],
                    state="normal",
                    command=lambda choice, field=field_name: self._apply_song_choice(field, choice),
                )
            else:
                widget = ctk.CTkEntry(scroll)
            widget.grid(row=row_index, column=1, sticky="ew", padx=(0, 4), pady=4)
            self.bulletin_widgets[field_name] = widget

        list_panel = ctk.CTkFrame(tab)
        list_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        list_panel.grid_columnconfigure(0, weight=1)
        list_panel.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(list_panel, text="Boletins cadastrados", font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 4)
        )
        search_bar = ctk.CTkFrame(list_panel, fg_color="transparent")
        search_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=6)
        search_bar.grid_columnconfigure(0, weight=1)
        self.bulletin_search_entry = ctk.CTkEntry(search_bar, placeholder_text="Pesquisar por data")
        self.bulletin_search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(search_bar, text="Pesquisar por Data", width=150, command=self._search_bulletins).grid(
            row=0, column=1
        )

        tree_frame, self.bulletins_tree = self._make_tree(
            list_panel,
            ("id", "date", "dirigente", "pregador", "source"),
            {"id": "ID", "date": "Data", "dirigente": "Dirigente", "pregador": "Pregador", "source": "Origem"},
            {"id": 50, "date": 95, "dirigente": 130, "pregador": 130, "source": 90},
        )
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(4, 10))
        self.bulletins_tree.bind("<<TreeviewSelect>>", self._on_bulletin_selected)

    def _build_louveapp_tab(self) -> None:
        tab = self.tabs.tab("Importar LouveApp")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        controls = ctk.CTkFrame(tab)
        controls.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        controls.grid_columnconfigure(3, weight=1)
        self.clear_louveapp_var = tk.BooleanVar(value=False)
        self.louveapp_import_button = ctk.CTkButton(
            controls,
            text="Importar escalas do LouveApp",
            width=220,
            command=self._start_louveapp_import,
        )
        self.louveapp_import_button.grid(row=0, column=0, padx=8, pady=8)
        ctk.CTkCheckBox(
            controls,
            text="Limpar importacao anterior antes de salvar",
            variable=self.clear_louveapp_var,
        ).grid(row=0, column=1, padx=8, pady=8)
        ctk.CTkButton(controls, text="Exportar escalas", width=140, command=self._export_schedules_xlsx).grid(
            row=0, column=2, padx=8, pady=8
        )
        self.louveapp_status_label = ctk.CTkLabel(controls, text="Pronto.", anchor="w")
        self.louveapp_status_label.grid(row=0, column=3, sticky="ew", padx=8)

        search_bar = ctk.CTkFrame(tab, fg_color="transparent")
        search_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        search_bar.grid_columnconfigure(0, weight=1)
        self.schedule_search_entry = ctk.CTkEntry(search_bar, placeholder_text="Buscar em escalas importadas")
        self.schedule_search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(search_bar, text="Buscar", width=100, command=self._refresh_schedules).grid(row=0, column=1)

        tree_frame, self.schedules_tree = self._make_tree(
            tab,
            ("id", "date", "time", "ministry", "role", "person", "title"),
            {
                "id": "ID",
                "date": "Data",
                "time": "Hora",
                "ministry": "Ministerio",
                "role": "Funcao",
                "person": "Pessoa",
                "title": "Titulo",
            },
            {"id": 50, "date": 90, "time": 70, "ministry": 120, "role": 120, "person": 150, "title": 260},
        )
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(4, 12))

    def _build_legacy_tab(self) -> None:
        tab = self.tabs.tab("Importar Excel Legado")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        controls = ctk.CTkFrame(tab)
        controls.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        controls.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            controls,
            text="Selecionar BOLETIM_VBA_CORRIGIDO.xlsm",
            width=260,
            command=self._select_legacy_file,
        ).grid(row=0, column=0, padx=8, pady=8)
        self.legacy_path_var = tk.StringVar(value="")
        ctk.CTkEntry(controls, textvariable=self.legacy_path_var).grid(row=0, column=1, sticky="ew", padx=8)

        actions = ctk.CTkFrame(tab, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        for text, command in (
            ("Inspecionar arquivo", self._inspect_legacy_file),
            ("Importar boletins", self._import_legacy_bulletins),
            ("Importar pessoas do louvor", self._import_legacy_people),
        ):
            ctk.CTkButton(actions, text=text, width=190, command=command).pack(side="left", padx=4)

        self.legacy_summary = ctk.CTkTextbox(tab, wrap="word")
        self.legacy_summary.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _build_people_tab(self) -> None:
        tab = self.tabs.tab("Pessoas do Louvor")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        controls = ctk.CTkFrame(tab)
        controls.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        controls.grid_columnconfigure(0, weight=1)
        self.person_name_entry = ctk.CTkEntry(controls, placeholder_text="Nome")
        self.person_name_entry.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ctk.CTkButton(controls, text="Adicionar", width=110, command=self._add_person).grid(row=0, column=1, padx=4)
        ctk.CTkButton(controls, text="Editar", width=100, command=self._edit_person).grid(row=0, column=2, padx=4)
        ctk.CTkButton(controls, text="Inativar", width=100, command=self._inactivate_person).grid(row=0, column=3, padx=4)

        search_bar = ctk.CTkFrame(tab, fg_color="transparent")
        search_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        search_bar.grid_columnconfigure(0, weight=1)
        self.person_search_entry = ctk.CTkEntry(search_bar, placeholder_text="Buscar nome")
        self.person_search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(search_bar, text="Buscar", width=100, command=self._refresh_people).grid(row=0, column=1)

        tree_frame, self.people_tree = self._make_tree(
            tab,
            ("id", "name", "active"),
            {"id": "ID", "name": "Nome", "active": "Ativo"},
            {"id": 60, "name": 420, "active": 80},
        )
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.people_tree.bind("<<TreeviewSelect>>", self._on_person_selected)

    def _build_exports_tab(self) -> None:
        tab = self.tabs.tab("Exportacoes")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)

        data_exports = ctk.CTkFrame(tab)
        data_exports.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        ctk.CTkLabel(data_exports, text="Arquivos de dados", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=12, pady=12)
        for text, command in (
            ("Exportar boletins para Excel", self._export_bulletins_xlsx),
            ("Exportar boletins para CSV", self._export_bulletins_csv),
            ("Exportar escalas LouveApp para Excel", self._export_schedules_xlsx),
            ("Exportar escalas LouveApp para CSV", self._export_schedules_csv),
        ):
            ctk.CTkButton(data_exports, text=text, command=command).pack(fill="x", padx=12, pady=6)

        doc_exports = ctk.CTkFrame(tab)
        doc_exports.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        ctk.CTkLabel(doc_exports, text="Documentos DOCX", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=12, pady=12)
        self.doc_date_entry = ctk.CTkEntry(doc_exports, placeholder_text="Data para gerar por busca")
        self.doc_date_entry.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkButton(doc_exports, text="Gerar boletim DOCX", command=self._generate_bulletin_by_date_input).pack(
            fill="x", padx=12, pady=6
        )
        ctk.CTkButton(doc_exports, text="Gerar repertorio DOCX", command=self._generate_repertoire_by_date_input).pack(
            fill="x", padx=12, pady=6
        )
        ctk.CTkButton(doc_exports, text="Abrir pasta output", command=lambda: self._open_folder(OUTPUT_DIR)).pack(
            fill="x", padx=12, pady=(20, 6)
        )

    def _build_logs_tab(self) -> None:
        tab = self.tabs.tab("Debug/Logs")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        for text, command in (
            ("Mostrar ultimos logs", self._refresh_logs),
            ("Abrir pasta data/debug", lambda: self._open_folder(DEBUG_DIR)),
            ("Abrir pasta output", lambda: self._open_folder(OUTPUT_DIR)),
        ):
            ctk.CTkButton(controls, text=text, width=170, command=command).pack(side="left", padx=4)
        self.logs_text = ctk.CTkTextbox(tab, wrap="word")
        self.logs_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _make_tree(
        self,
        parent: tk.Widget,
        columns: tuple[str, ...],
        headings: dict[str, str],
        widths: dict[str, int],
    ) -> tuple[ctk.CTkFrame, ttk.Treeview]:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths.get(column, 120), minwidth=40, stretch=True)
        return frame, tree

    def refresh_all(self) -> None:
        self._refresh_dashboard()
        self._refresh_bulletins()
        self._refresh_people()
        self._refresh_schedules()
        self._refresh_bulletin_schedule_options()
        self._refresh_logs()

    def _refresh_dashboard(self) -> None:
        stats = self.db.get_dashboard_stats()
        self.dashboard_labels["bulletins"].configure(text=str(stats["bulletins"]))
        self.dashboard_labels["people"].configure(text=str(stats["people"]))
        self.dashboard_labels["schedules"].configure(text=str(stats["schedules"]))
        last_bulletin = stats["last_bulletin"]
        if last_bulletin:
            self.dashboard_labels["last_bulletin"].configure(
                text=f"{last_bulletin.get('date_text') or '-'} | {last_bulletin.get('dirigente') or '-'} | {last_bulletin.get('pregador') or '-'}"
            )
        else:
            self.dashboard_labels["last_bulletin"].configure(text="-")
        last_import = stats["last_import"]
        if last_import:
            self.dashboard_labels["last_import"].configure(
                text=f"{last_import.get('created_at')} | {last_import.get('source')} | {last_import.get('status')}\n{last_import.get('message')}"
            )
        else:
            self.dashboard_labels["last_import"].configure(text="-")

    def _widget_value(self, widget: tk.Widget) -> str:
        if isinstance(widget, ctk.CTkTextbox):
            return widget.get("1.0", "end").strip()
        return widget.get().strip()

    def _set_widget_value(self, widget: tk.Widget, value: str) -> None:
        if isinstance(widget, ctk.CTkTextbox):
            widget.delete("1.0", "end")
            widget.insert("1.0", value or "")
        elif isinstance(widget, ctk.CTkComboBox):
            widget.set(value or "")
        else:
            widget.delete(0, "end")
            widget.insert(0, value or "")

    def _collect_bulletin_form(self) -> WorshipBulletin:
        values = {field: self._widget_value(widget) for field, widget in self.bulletin_widgets.items()}
        bulletin = WorshipBulletin(**values, source="manual")
        schedule_meta = self._selected_schedule_meta()
        if schedule_meta:
            bulletin.raw_json = json.dumps({"louveapp_schedule": schedule_meta}, ensure_ascii=False)
        return bulletin

    def _load_bulletin_into_form(self, bulletin: WorshipBulletin) -> None:
        self.current_bulletin_id = bulletin.id
        for field, widget in self.bulletin_widgets.items():
            self._set_widget_value(widget, getattr(bulletin, field, ""))
        self._load_schedule_from_bulletin(bulletin)

    def _clear_bulletin_form(self) -> None:
        self.current_bulletin_id = None
        for widget in self.bulletin_widgets.values():
            self._set_widget_value(widget, "")
        self._clear_selected_schedule()

    def _refresh_bulletin_schedule_options(self) -> None:
        if not hasattr(self, "bulletin_schedule_combo"):
            return
        summaries = self.db.list_louveapp_schedule_summaries()
        self.schedule_combo_values = {"Sem escala selecionada": {}}
        values = ["Sem escala selecionada"]
        for summary in summaries:
            label = summary["label"]
            values.append(label)
            self.schedule_combo_values[label] = summary
        self.bulletin_schedule_combo.configure(values=values)
        if self.selected_schedule:
            selected_id = self.selected_schedule.get("external_id", "")
            matching_label = self._schedule_label_by_external_id(selected_id)
            if matching_label:
                self.bulletin_schedule_combo.set(matching_label)
            else:
                self._clear_selected_schedule()
        elif self.bulletin_schedule_combo.get() not in values:
            self.bulletin_schedule_combo.set("Sem escala selecionada")

    def _on_bulletin_schedule_selected(self, label: str) -> None:
        summary = self.schedule_combo_values.get(label) or {}
        if not summary:
            self.selected_schedule = None
            self._set_song_choices([])
            self.schedule_hint_label.configure(text="Musicas livres para preenchimento manual.")
            return
        self.selected_schedule = summary
        songs = self.db.list_louveapp_schedule_songs(summary["external_id"])
        self._set_song_choices(songs)
        self.schedule_hint_label.configure(
            text=f"{len(songs)} musica(s) disponivel(is) para escolher nos campos do boletim."
        )

    def _clear_selected_schedule(self) -> None:
        if hasattr(self, "bulletin_schedule_combo"):
            self.bulletin_schedule_combo.set("Sem escala selecionada")
        self.selected_schedule = None
        self._set_song_choices([])
        if hasattr(self, "schedule_hint_label"):
            self.schedule_hint_label.configure(text="Musicas livres para preenchimento manual.")

    def _set_song_choices(self, songs: list[dict[str, str]]) -> None:
        self.schedule_song_choices = {song["display"]: song for song in songs}
        values = list(self.schedule_song_choices.keys())
        for field in MUSIC_FIELD_NAMES:
            widget = self.bulletin_widgets.get(field)
            if isinstance(widget, ctk.CTkComboBox):
                widget.configure(values=values)

    def _apply_song_choice(self, field_name: str, choice: str) -> None:
        song = self.schedule_song_choices.get(choice)
        if not song:
            return
        widget = self.bulletin_widgets.get(field_name)
        if isinstance(widget, ctk.CTkComboBox):
            widget.set(song["title"])
        key_field = MUSIC_TO_KEY_FIELD.get(field_name)
        if key_field and song.get("key"):
            key_widget = self.bulletin_widgets.get(key_field)
            if key_widget:
                self._set_widget_value(key_widget, song["key"])
        singer_field = MUSIC_TO_SINGER_FIELD.get(field_name)
        if singer_field and song.get("artist"):
            singer_widget = self.bulletin_widgets.get(singer_field)
            if singer_widget:
                self._set_widget_value(singer_widget, song["artist"])

    def _selected_schedule_meta(self) -> Optional[dict[str, str]]:
        if not self.selected_schedule:
            return None
        return {
            "external_id": self.selected_schedule.get("external_id", ""),
            "title": self.selected_schedule.get("title", ""),
            "date_text": self.selected_schedule.get("date_text", ""),
            "time_text": self.selected_schedule.get("time_text", ""),
            "ministry": self.selected_schedule.get("ministry", ""),
        }

    def _schedule_label_by_external_id(self, external_id: str) -> str:
        for label, summary in self.schedule_combo_values.items():
            if summary.get("external_id") == external_id:
                return label
        return ""

    def _load_schedule_from_bulletin(self, bulletin: WorshipBulletin) -> None:
        try:
            payload = json.loads(bulletin.raw_json or "{}")
        except json.JSONDecodeError:
            self._clear_selected_schedule()
            return
        schedule = payload.get("louveapp_schedule") if isinstance(payload, dict) else None
        if not isinstance(schedule, dict):
            self._clear_selected_schedule()
            return
        external_id = str(schedule.get("external_id") or "")
        self._refresh_bulletin_schedule_options()
        label = self._schedule_label_by_external_id(external_id)
        if label:
            self.bulletin_schedule_combo.set(label)
            self._on_bulletin_schedule_selected(label)
        else:
            self.selected_schedule = {key: str(value or "") for key, value in schedule.items()}
            self._set_song_choices([])
            self.schedule_hint_label.configure(text="Escala vinculada nao esta mais na importacao atual.")

    def _new_bulletin(self) -> None:
        self._clear_bulletin_form()
        self.tabs.set("Boletins")

    def _save_bulletin(self) -> None:
        self._run_action(
            "Salvar boletim",
            lambda: self._save_bulletin_inner(),
        )

    def _save_bulletin_inner(self) -> str:
        bulletin = self._collect_bulletin_form()
        if not bulletin.date_text:
            raise ValueError("Informe a data do boletim.")
        bulletin_id = self.db.insert_bulletin(bulletin)
        self.current_bulletin_id = bulletin_id
        self._refresh_bulletins()
        self._refresh_dashboard()
        return f"Boletim salvo com ID {bulletin_id}."

    def _edit_bulletin(self) -> None:
        self._run_action("Editar boletim", self._edit_bulletin_inner)

    def _edit_bulletin_inner(self) -> str:
        if not self.current_bulletin_id:
            raise ValueError("Selecione um boletim para editar.")
        bulletin = self._collect_bulletin_form()
        if not bulletin.date_text:
            raise ValueError("Informe a data do boletim.")
        self.db.update_bulletin(self.current_bulletin_id, bulletin)
        self._refresh_bulletins()
        self._refresh_dashboard()
        return "Boletim atualizado."

    def _delete_bulletin(self) -> None:
        if not self.current_bulletin_id:
            messagebox.showwarning("Excluir boletim", "Selecione um boletim para excluir.")
            return
        if not messagebox.askyesno("Confirmar exclusao", "Deseja excluir este boletim?"):
            return
        self._run_action("Excluir boletim", self._delete_bulletin_inner)

    def _delete_bulletin_inner(self) -> str:
        if not self.current_bulletin_id:
            raise ValueError("Nenhum boletim selecionado.")
        self.db.delete_bulletin(self.current_bulletin_id)
        self._clear_bulletin_form()
        self._refresh_bulletins()
        self._refresh_dashboard()
        return "Boletim excluido."

    def _search_bulletins(self) -> None:
        self._refresh_bulletins(self.bulletin_search_entry.get())

    def _refresh_bulletins(self, date_search: str = "") -> None:
        for item in self.bulletins_tree.get_children():
            self.bulletins_tree.delete(item)
        bulletins = self.db.find_bulletins_by_date(date_search) if date_search.strip() else self.db.list_bulletins()
        for bulletin in bulletins:
            self.bulletins_tree.insert(
                "",
                "end",
                iid=str(bulletin.id),
                values=(bulletin.id, bulletin.date_text, bulletin.dirigente, bulletin.pregador, bulletin.source),
            )

    def _on_bulletin_selected(self, _event: tk.Event) -> None:
        selected = self.bulletins_tree.selection()
        if not selected:
            return
        bulletin = self.db.get_bulletin(int(selected[0]))
        if bulletin:
            self._load_bulletin_into_form(bulletin)

    def _generate_bulletin_from_selection(self) -> None:
        self._run_action("Gerar boletim", self._generate_bulletin_from_selection_inner)

    def _generate_bulletin_from_selection_inner(self) -> str:
        if not self.current_bulletin_id:
            date_text = self._widget_value(self.bulletin_widgets["date_text"])
            if not date_text:
                raise ValueError("Selecione um boletim ou informe uma data.")
            path = generate_bulletin_by_date(date_text)
        else:
            path = generate_bulletin_docx(self.current_bulletin_id)
        return f"Boletim gerado: {path}"

    def _generate_repertoire_from_selection(self) -> None:
        self._run_action("Gerar repertorio", self._generate_repertoire_from_selection_inner)

    def _generate_repertoire_from_selection_inner(self) -> str:
        if not self.current_bulletin_id:
            date_text = self._widget_value(self.bulletin_widgets["date_text"])
            if not date_text:
                raise ValueError("Selecione um boletim ou informe uma data.")
            path = generate_repertoire_by_date(date_text)
        else:
            path = generate_repertoire_docx(self.current_bulletin_id)
        return f"Repertorio gerado: {path}"

    def _start_louveapp_import(self) -> None:
        clear_existing = bool(self.clear_louveapp_var.get())
        if clear_existing and not messagebox.askyesno(
            "Limpar importacao",
            "Deseja apagar as escalas LouveApp ja importadas antes de salvar a nova importacao?",
        ):
            return
        self.louveapp_import_button.configure(state="disabled")
        self.louveapp_status_label.configure(text="Iniciando importacao...")

        def worker() -> None:
            def progress(message: str) -> None:
                self.worker_queue.put(("louveapp_status", message))

            result = import_louveapp_schedules(progress=progress, clear_existing=clear_existing)
            self.worker_queue.put(("louveapp_done", result))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_worker_queue(self) -> None:
        try:
            while True:
                event_name, payload = self.worker_queue.get_nowait()
                if event_name == "louveapp_status":
                    self.louveapp_status_label.configure(text=str(payload))
                elif event_name == "louveapp_done":
                    self._finish_louveapp_import(payload)
        except queue.Empty:
            pass
        self.after(300, self._poll_worker_queue)

    def _finish_louveapp_import(self, result: ImportResult) -> None:
        self.louveapp_import_button.configure(state="normal")
        self.louveapp_status_label.configure(text=result.message)
        self._refresh_schedules()
        self._refresh_bulletin_schedule_options()
        self._refresh_dashboard()
        if result.status == "success":
            messagebox.showinfo("Importar LouveApp", result.message)
        elif result.status == "warning":
            messagebox.showwarning("Importar LouveApp", result.message)
        else:
            messagebox.showerror("Importar LouveApp", result.message)

    def _refresh_schedules(self) -> None:
        search = self.schedule_search_entry.get() if hasattr(self, "schedule_search_entry") else ""
        for item in self.schedules_tree.get_children():
            self.schedules_tree.delete(item)
        for schedule in self.db.list_louveapp_schedules(search):
            self.schedules_tree.insert(
                "",
                "end",
                iid=str(schedule.id),
                values=(
                    schedule.id,
                    schedule.date_text,
                    schedule.time_text,
                    schedule.ministry,
                    schedule.role,
                    schedule.person_name,
                    schedule.title,
                ),
            )

    def _select_legacy_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Selecionar BOLETIM_VBA_CORRIGIDO.xlsm",
            filetypes=[("Excel com macros", "*.xlsm"), ("Todos os arquivos", "*.*")],
        )
        if file_path:
            self.legacy_path_var.set(file_path)

    def _legacy_path_or_none(self) -> Optional[Path]:
        value = self.legacy_path_var.get().strip()
        return Path(value) if value else None

    def _append_legacy_summary(self, text: str) -> None:
        self.legacy_summary.delete("1.0", "end")
        self.legacy_summary.insert("1.0", text)

    def _inspect_legacy_file(self) -> None:
        self._run_action("Inspecionar XLSM", self._inspect_legacy_file_inner, show_success=False)

    def _inspect_legacy_file_inner(self) -> str:
        summary = inspect_legacy_workbook(self._legacy_path_or_none())
        text = json.dumps(summary, ensure_ascii=False, indent=2)
        self._append_legacy_summary(text)
        return "Arquivo inspecionado."

    def _import_legacy_bulletins(self) -> None:
        self._run_action("Importar boletins XLSM", self._import_legacy_bulletins_inner)

    def _import_legacy_bulletins_inner(self) -> str:
        result = import_legacy_bulletins(self._legacy_path_or_none(), self.db)
        self._append_legacy_summary(result.message)
        self._refresh_bulletins()
        self._refresh_dashboard()
        if result.status != "success":
            raise RuntimeError(result.message)
        return result.message

    def _import_legacy_people(self) -> None:
        self._run_action("Importar pessoas XLSM", self._import_legacy_people_inner)

    def _import_legacy_people_inner(self) -> str:
        result = import_legacy_people(self._legacy_path_or_none(), self.db)
        self._append_legacy_summary(result.message)
        self._refresh_people()
        self._refresh_dashboard()
        if result.status != "success":
            raise RuntimeError(result.message)
        return result.message

    def _add_person(self) -> None:
        self._run_action("Adicionar pessoa", self._add_person_inner)

    def _add_person_inner(self) -> str:
        name = self.person_name_entry.get().strip()
        if not name:
            raise ValueError("Informe o nome.")
        person_id = self.db.save_person(name)
        self.person_name_entry.delete(0, "end")
        self._refresh_people()
        self._refresh_dashboard()
        return f"Pessoa salva com ID {person_id}."

    def _edit_person(self) -> None:
        self._run_action("Editar pessoa", self._edit_person_inner)

    def _edit_person_inner(self) -> str:
        if not self.current_person_id:
            raise ValueError("Selecione uma pessoa.")
        name = self.person_name_entry.get().strip()
        if not name:
            raise ValueError("Informe o nome.")
        self.db.update_person(self.current_person_id, name, 1)
        self._refresh_people()
        self._refresh_dashboard()
        return "Pessoa atualizada."

    def _inactivate_person(self) -> None:
        if not self.current_person_id:
            messagebox.showwarning("Inativar pessoa", "Selecione uma pessoa.")
            return
        if not messagebox.askyesno("Confirmar", "Deseja inativar esta pessoa?"):
            return
        self._run_action("Inativar pessoa", self._inactivate_person_inner)

    def _inactivate_person_inner(self) -> str:
        if not self.current_person_id:
            raise ValueError("Selecione uma pessoa.")
        self.db.inactivate_person(self.current_person_id)
        self.current_person_id = None
        self.person_name_entry.delete(0, "end")
        self._refresh_people()
        self._refresh_dashboard()
        return "Pessoa inativada."

    def _refresh_people(self) -> None:
        search = self.person_search_entry.get() if hasattr(self, "person_search_entry") else ""
        for item in self.people_tree.get_children():
            self.people_tree.delete(item)
        for person in self.db.list_people(search):
            self.people_tree.insert(
                "",
                "end",
                iid=str(person.id),
                values=(person.id, person.name, "Sim" if person.active else "Nao"),
            )

    def _on_person_selected(self, _event: tk.Event) -> None:
        selected = self.people_tree.selection()
        if not selected:
            return
        person_id = int(selected[0])
        self.current_person_id = person_id
        values = self.people_tree.item(selected[0], "values")
        self.person_name_entry.delete(0, "end")
        self.person_name_entry.insert(0, values[1])

    def _export_bulletins_xlsx(self) -> None:
        self._run_action("Exportar boletins Excel", lambda: f"Arquivo gerado: {export_bulletins_xlsx()}")

    def _export_bulletins_csv(self) -> None:
        self._run_action("Exportar boletins CSV", lambda: f"Arquivo gerado: {export_bulletins_csv()}")

    def _export_schedules_xlsx(self) -> None:
        self._run_action("Exportar escalas Excel", lambda: f"Arquivo gerado: {export_louveapp_schedules_xlsx()}")

    def _export_schedules_csv(self) -> None:
        self._run_action("Exportar escalas CSV", lambda: f"Arquivo gerado: {export_louveapp_schedules_csv()}")

    def _generate_bulletin_by_date_input(self) -> None:
        self._run_action("Gerar boletim por data", self._generate_bulletin_by_date_input_inner)

    def _generate_bulletin_by_date_input_inner(self) -> str:
        date_text = self.doc_date_entry.get().strip()
        if not date_text:
            raise ValueError("Informe a data.")
        return f"Boletim gerado: {generate_bulletin_by_date(date_text)}"

    def _generate_repertoire_by_date_input(self) -> None:
        self._run_action("Gerar repertorio por data", self._generate_repertoire_by_date_input_inner)

    def _generate_repertoire_by_date_input_inner(self) -> str:
        date_text = self.doc_date_entry.get().strip()
        if not date_text:
            raise ValueError("Informe a data.")
        return f"Repertorio gerado: {generate_repertoire_by_date(date_text)}"

    def _refresh_logs(self) -> None:
        self.logs_text.delete("1.0", "end")
        if not LOG_PATH.exists():
            self.logs_text.insert("1.0", "Nenhum log gerado ainda.")
            return
        lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        self.logs_text.insert("1.0", "\n".join(lines[-300:]))

    def _open_folder(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            logger.exception("Falha ao abrir pasta")
            messagebox.showerror("Abrir pasta", f"Nao foi possivel abrir a pasta: {exc}")

    def _run_action(self, title: str, action: Callable[[], str], show_success: bool = True) -> None:
        try:
            message = action()
            self._refresh_logs()
            if show_success:
                messagebox.showinfo(title, message)
        except Exception as exc:
            logger.exception("Erro na acao: %s", title)
            self._refresh_logs()
            messagebox.showerror(title, str(exc))
