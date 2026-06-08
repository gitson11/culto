from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from src.scale_generator import ScaleGenerator
from src.scale_models_repository import ScaleModelRepository


class ScaleGeneratorView:
    def __init__(self, parent: tk.Widget) -> None:
        self.parent = parent
        self.repository = ScaleModelRepository()
        self.generator = ScaleGenerator(repository=self.repository)
        self.model_lookup: dict[str, int] = {}
        self._build()
        self.refresh_models()

    def _build(self) -> None:
        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_rowconfigure(2, weight=1)

        controls = ctk.CTkFrame(self.parent)
        controls.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        controls.grid_columnconfigure(1, weight=1)
        controls.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(controls, text="Modelo").grid(row=0, column=0, sticky="w", padx=(10, 6), pady=10)
        self.model_combo = ctk.CTkComboBox(controls, values=[], state="readonly")
        self.model_combo.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=10)

        ctk.CTkLabel(controls, text="Data / periodo").grid(row=0, column=2, sticky="w", padx=(10, 6), pady=10)
        self.service_date_entry = ctk.CTkEntry(controls, placeholder_text="Ex.: domingo noite, 16/06/2026")
        self.service_date_entry.grid(row=0, column=3, sticky="ew", padx=(0, 12), pady=10)

        ctk.CTkButton(controls, text="Atualizar modelos", width=145, command=self.refresh_models).grid(row=0, column=4, padx=(0, 8), pady=10)
        ctk.CTkButton(controls, text="Gerar escala", width=130, command=self.generate_scale).grid(row=0, column=5, padx=(0, 10), pady=10)

        help_text = (
            "A escala sugerida considera integrantes ativos, funcoes, instrumentos, voz, disponibilidade e nivel de experiencia. "
            "Revise manualmente antes de publicar ou enviar."
        )
        ctk.CTkLabel(self.parent, text=help_text, anchor="w", justify="left").grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))

        tree_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(4, 8))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        self.result_tree = ttk.Treeview(
            tree_frame,
            columns=("function", "person", "reason", "warning"),
            show="headings",
            selectmode="browse",
        )
        headings = {"function": "Funcao", "person": "Integrante sugerido", "reason": "Motivo", "warning": "Aviso"}
        widths = {"function": 170, "person": 190, "reason": 350, "warning": 300}
        for column in ("function", "person", "reason", "warning"):
            self.result_tree.heading(column, text=headings[column])
            self.result_tree.column(column, width=widths[column], minwidth=80, stretch=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=scrollbar.set)
        self.result_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        footer = ctk.CTkFrame(self.parent)
        footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(footer, text="Avisos da geracao", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        self.warnings_text = ctk.CTkTextbox(footer, height=90, wrap="word")
        self.warnings_text.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

    def refresh_models(self) -> None:
        self.model_lookup.clear()
        models = self.repository.list_models()
        labels: list[str] = []
        for model in models:
            if not model.id:
                continue
            label = f"{model.name} — {model.service_type}" if model.service_type else model.name
            labels.append(label)
            self.model_lookup[label] = model.id
        values = labels or ["Nenhum modelo cadastrado"]
        self.model_combo.configure(values=values)
        self.model_combo.set(values[0])

    def generate_scale(self) -> None:
        label = self.model_combo.get().strip()
        model_id = self.model_lookup.get(label)
        if not model_id:
            messagebox.showwarning("Gerar escala", "Cadastre e selecione um modelo de escala primeiro.")
            return
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.warnings_text.delete("1.0", "end")
        try:
            result = self.generator.generate(model_id, self.service_date_entry.get().strip())
            for assignment in result.assignments:
                self.result_tree.insert(
                    "",
                    "end",
                    values=(assignment.function_name, assignment.person_name, assignment.reason, assignment.warning),
                )
            if result.warnings:
                self.warnings_text.insert("1.0", "\n".join(f"- {warning}" for warning in result.warnings))
            else:
                self.warnings_text.insert("1.0", "Nenhum aviso. Revise a escala antes de publicar.")
        except Exception as exc:
            messagebox.showerror("Gerar escala", str(exc))
