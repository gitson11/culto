from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from src.generated_scale_exporters import export_saved_scale_docx, export_saved_scale_xlsx
from src.generated_scales_repository import GeneratedScalesRepository
from src.scale_generator import GeneratedScaleResult, ScaleGenerator
from src.scale_models_repository import ScaleModelRepository


class ScaleGeneratorView:
    def __init__(self, parent: tk.Widget) -> None:
        self.parent = parent
        self.repository = ScaleModelRepository()
        self.saved_repository = GeneratedScalesRepository()
        self.generator = ScaleGenerator(repository=self.repository)
        self.model_lookup: dict[str, int] = {}
        self.current_result: GeneratedScaleResult | None = None
        self.current_saved_scale_id: int | None = None
        self.current_assignment_id: int | None = None
        self._build()
        self.refresh_models()
        self.refresh_saved_scales()

    def _build(self) -> None:
        self.parent.grid_columnconfigure(0, weight=3)
        self.parent.grid_columnconfigure(1, weight=2)
        self.parent.grid_rowconfigure(2, weight=1)

        controls = ctk.CTkFrame(self.parent)
        controls.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 6))
        controls.grid_columnconfigure(1, weight=1)
        controls.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(controls, text="Modelo").grid(row=0, column=0, sticky="w", padx=(10, 6), pady=10)
        self.model_combo = ctk.CTkComboBox(controls, values=[], state="readonly")
        self.model_combo.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=10)

        ctk.CTkLabel(controls, text="Data / periodo").grid(row=0, column=2, sticky="w", padx=(10, 6), pady=10)
        self.service_date_entry = ctk.CTkEntry(controls, placeholder_text="Ex.: domingo noite, 16/06/2026")
        self.service_date_entry.grid(row=0, column=3, sticky="ew", padx=(0, 12), pady=10)

        ctk.CTkButton(controls, text="Atualizar", width=95, command=self.refresh_all).grid(row=0, column=4, padx=(0, 8), pady=10)
        ctk.CTkButton(controls, text="Gerar", width=90, command=self.generate_scale).grid(row=0, column=5, padx=(0, 8), pady=10)
        ctk.CTkButton(controls, text="Salvar", width=90, command=self.save_current_scale).grid(row=0, column=6, padx=(0, 8), pady=10)
        ctk.CTkButton(controls, text="WhatsApp", width=105, command=self.copy_current_whatsapp_text).grid(row=0, column=7, padx=(0, 8), pady=10)
        ctk.CTkButton(controls, text="Excel", width=80, command=self.export_current_xlsx).grid(row=0, column=8, padx=(0, 8), pady=10)
        ctk.CTkButton(controls, text="Word", width=80, command=self.export_current_docx).grid(row=0, column=9, padx=(0, 10), pady=10)

        help_text = "Gere a escala, salve como rascunho, ajuste manualmente as linhas e exporte somente depois da revisao."
        ctk.CTkLabel(self.parent, text=help_text, anchor="w", justify="left").grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 6)
        )

        result_panel = ctk.CTkFrame(self.parent)
        result_panel.grid(row=2, column=0, sticky="nsew", padx=(12, 6), pady=(4, 8))
        result_panel.grid_columnconfigure(0, weight=1)
        result_panel.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(result_panel, text="Escala sugerida / salva", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(8, 4)
        )
        self.result_tree = ttk.Treeview(
            result_panel,
            columns=("function", "person", "reason", "warning"),
            show="headings",
            selectmode="browse",
        )
        headings = {"function": "Funcao", "person": "Integrante", "reason": "Motivo", "warning": "Aviso"}
        widths = {"function": 150, "person": 170, "reason": 280, "warning": 230}
        for column in ("function", "person", "reason", "warning"):
            self.result_tree.heading(column, text=headings[column])
            self.result_tree.column(column, width=widths[column], minwidth=80, stretch=True)
        scrollbar = ttk.Scrollbar(result_panel, orient="vertical", command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=scrollbar.set)
        self.result_tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 10), padx=(0, 10))
        self.result_tree.bind("<<TreeviewSelect>>", self.on_assignment_selected)

        saved_panel = ctk.CTkFrame(self.parent)
        saved_panel.grid(row=2, column=1, sticky="nsew", padx=(6, 12), pady=(4, 8))
        saved_panel.grid_columnconfigure(0, weight=1)
        saved_panel.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(saved_panel, text="Escalas salvas", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(8, 4)
        )
        self.saved_tree = ttk.Treeview(saved_panel, columns=("id", "title", "status"), show="headings", selectmode="browse")
        self.saved_tree.heading("id", text="ID")
        self.saved_tree.heading("title", text="Escala")
        self.saved_tree.heading("status", text="Status")
        self.saved_tree.column("id", width=45, minwidth=40, stretch=False)
        self.saved_tree.column("title", width=250, minwidth=150, stretch=True)
        self.saved_tree.column("status", width=85, minwidth=70, stretch=False)
        self.saved_tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.saved_tree.bind("<<TreeviewSelect>>", self.on_saved_scale_selected)
        saved_actions = ctk.CTkFrame(saved_panel, fg_color="transparent")
        saved_actions.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        ctk.CTkButton(saved_actions, text="Copiar", width=75, command=self.copy_saved_whatsapp_text).pack(side="left", padx=3)
        ctk.CTkButton(saved_actions, text="Excel", width=75, command=self.export_current_xlsx).pack(side="left", padx=3)
        ctk.CTkButton(saved_actions, text="Word", width=75, command=self.export_current_docx).pack(side="left", padx=3)
        ctk.CTkButton(saved_actions, text="Excluir", width=75, command=self.delete_saved_scale).pack(side="left", padx=3)

        edit_panel = ctk.CTkFrame(self.parent)
        edit_panel.grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 8))
        edit_panel.grid_columnconfigure(1, weight=1)
        edit_panel.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(edit_panel, text="Funcao").grid(row=0, column=0, sticky="w", padx=(10, 6), pady=(8, 4))
        self.edit_function_entry = ctk.CTkEntry(edit_panel)
        self.edit_function_entry.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(8, 4))
        ctk.CTkLabel(edit_panel, text="Integrante").grid(row=0, column=2, sticky="w", padx=(10, 6), pady=(8, 4))
        self.edit_person_entry = ctk.CTkEntry(edit_panel)
        self.edit_person_entry.grid(row=0, column=3, sticky="ew", padx=(0, 12), pady=(8, 4))
        ctk.CTkLabel(edit_panel, text="Motivo").grid(row=1, column=0, sticky="w", padx=(10, 6), pady=4)
        self.edit_reason_entry = ctk.CTkEntry(edit_panel)
        self.edit_reason_entry.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=4)
        ctk.CTkLabel(edit_panel, text="Aviso").grid(row=1, column=2, sticky="w", padx=(10, 6), pady=4)
        self.edit_warning_entry = ctk.CTkEntry(edit_panel)
        self.edit_warning_entry.grid(row=1, column=3, sticky="ew", padx=(0, 12), pady=4)
        edit_actions = ctk.CTkFrame(edit_panel, fg_color="transparent")
        edit_actions.grid(row=2, column=0, columnspan=4, sticky="ew", padx=8, pady=(6, 8))
        ctk.CTkButton(edit_actions, text="Adicionar linha", width=120, command=self.add_assignment).pack(side="left", padx=4)
        ctk.CTkButton(edit_actions, text="Editar linha", width=110, command=self.update_assignment).pack(side="left", padx=4)
        ctk.CTkButton(edit_actions, text="Remover linha", width=120, command=self.delete_assignment).pack(side="left", padx=4)
        ctk.CTkButton(edit_actions, text="Limpar campos", width=120, command=self.clear_assignment_form).pack(side="left", padx=4)

        footer = ctk.CTkFrame(self.parent)
        footer.grid(row=4, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(footer, text="Avisos / texto para WhatsApp", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        self.warnings_text = ctk.CTkTextbox(footer, height=110, wrap="word")
        self.warnings_text.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

    def refresh_all(self) -> None:
        self.refresh_models()
        self.refresh_saved_scales()

    def refresh_models(self) -> None:
        self.model_lookup.clear()
        labels: list[str] = []
        for model in self.repository.list_models():
            if not model.id:
                continue
            label = f"{model.name} - {model.service_type}" if model.service_type else model.name
            labels.append(label)
            self.model_lookup[label] = model.id
        values = labels or ["Nenhum modelo cadastrado"]
        self.model_combo.configure(values=values)
        self.model_combo.set(values[0])

    def refresh_saved_scales(self) -> None:
        self.saved_repository.ensure_tables()
        for item in self.saved_tree.get_children():
            self.saved_tree.delete(item)
        for scale in self.saved_repository.list_scales():
            self.saved_tree.insert("", "end", iid=str(scale.id), values=(scale.id, scale.title, scale.status))

    def generate_scale(self) -> None:
        label = self.model_combo.get().strip()
        model_id = self.model_lookup.get(label)
        if not model_id:
            messagebox.showwarning("Gerar escala", "Cadastre e selecione um modelo de escala primeiro.")
            return
        self.clear_result_tree()
        self.warnings_text.delete("1.0", "end")
        try:
            self.current_result = self.generator.generate(model_id, self.service_date_entry.get().strip())
            self.current_saved_scale_id = None
            self.current_assignment_id = None
            self.insert_assignments_into_result_tree(self.current_result.assignments)
            if self.current_result.warnings:
                self.warnings_text.insert("1.0", "\n".join(f"- {warning}" for warning in self.current_result.warnings))
            else:
                self.warnings_text.insert("1.0", "Nenhum aviso. Revise a escala antes de publicar.")
        except Exception as exc:
            messagebox.showerror("Gerar escala", str(exc))

    def save_current_scale(self) -> None:
        if not self.current_result:
            messagebox.showwarning("Salvar escala", "Gere uma escala antes de salvar.")
            return
        try:
            self.current_saved_scale_id = self.saved_repository.save_generated_scale(
                self.current_result,
                service_date=self.service_date_entry.get().strip(),
                notes=self.warnings_text.get("1.0", "end").strip(),
            )
            self.refresh_saved_scales()
            self.load_saved_scale(self.current_saved_scale_id)
            messagebox.showinfo("Salvar escala", f"Escala salva com ID {self.current_saved_scale_id}.")
        except Exception as exc:
            messagebox.showerror("Salvar escala", str(exc))

    def on_saved_scale_selected(self, _event) -> None:
        selected = self.saved_tree.selection()
        if selected:
            self.load_saved_scale(int(selected[0]))

    def load_saved_scale(self, scale_id: int) -> None:
        self.current_saved_scale_id = scale_id
        self.current_result = None
        self.current_assignment_id = None
        self.clear_result_tree()
        for row in self.saved_repository.get_assignment_rows(scale_id):
            self.result_tree.insert("", "end", iid=str(row.id), values=(row.function_name, row.person_name, row.reason, row.warning))
        self.clear_assignment_form()
        self.warnings_text.delete("1.0", "end")
        self.warnings_text.insert("1.0", self.saved_repository.build_whatsapp_text(scale_id))

    def on_assignment_selected(self, _event) -> None:
        selected = self.result_tree.selection()
        if not selected:
            return
        try:
            self.current_assignment_id = int(selected[0])
        except ValueError:
            self.current_assignment_id = None
        values = self.result_tree.item(selected[0], "values")
        self._set_entry(self.edit_function_entry, values[0] if len(values) > 0 else "")
        self._set_entry(self.edit_person_entry, values[1] if len(values) > 1 else "")
        self._set_entry(self.edit_reason_entry, values[2] if len(values) > 2 else "")
        self._set_entry(self.edit_warning_entry, values[3] if len(values) > 3 else "")

    def add_assignment(self) -> None:
        if not self.current_saved_scale_id:
            messagebox.showwarning("Adicionar linha", "Salve ou selecione uma escala antes de editar.")
            return
        function_name, person_name, reason, warning = self._assignment_form_values()
        if not function_name:
            messagebox.showwarning("Adicionar linha", "Informe a funcao.")
            return
        self.saved_repository.add_assignment(self.current_saved_scale_id, function_name, person_name, reason or "adicionado manualmente", warning)
        self.load_saved_scale(self.current_saved_scale_id)

    def update_assignment(self) -> None:
        if not self.current_saved_scale_id or not self.current_assignment_id:
            messagebox.showwarning("Editar linha", "Selecione uma linha de uma escala salva.")
            return
        function_name, person_name, reason, warning = self._assignment_form_values()
        if not function_name:
            messagebox.showwarning("Editar linha", "Informe a funcao.")
            return
        self.saved_repository.update_assignment(self.current_assignment_id, function_name, person_name, reason or "ajuste manual", warning)
        self.load_saved_scale(self.current_saved_scale_id)

    def delete_assignment(self) -> None:
        if not self.current_saved_scale_id or not self.current_assignment_id:
            messagebox.showwarning("Remover linha", "Selecione uma linha de uma escala salva.")
            return
        if not messagebox.askyesno("Remover linha", "Deseja remover esta linha da escala?"):
            return
        self.saved_repository.delete_assignment(self.current_assignment_id)
        self.load_saved_scale(self.current_saved_scale_id)

    def delete_saved_scale(self) -> None:
        selected_id = self._selected_saved_scale_id()
        if not selected_id:
            messagebox.showwarning("Excluir escala", "Selecione uma escala salva.")
            return
        if not messagebox.askyesno("Excluir escala", "Deseja excluir esta escala salva?"):
            return
        self.saved_repository.delete_scale(selected_id)
        self.current_saved_scale_id = None
        self.current_assignment_id = None
        self.refresh_saved_scales()
        self.clear_result_tree()
        self.clear_assignment_form()
        self.warnings_text.delete("1.0", "end")

    def copy_current_whatsapp_text(self) -> None:
        if self.current_saved_scale_id:
            text = self.saved_repository.build_whatsapp_text(self.current_saved_scale_id)
        elif self.current_result:
            text = self._build_unsaved_whatsapp_text()
        else:
            messagebox.showwarning("Copiar WhatsApp", "Gere ou selecione uma escala primeiro.")
            return
        self._copy_to_clipboard(text)

    def copy_saved_whatsapp_text(self) -> None:
        selected_id = self._selected_saved_scale_id()
        if not selected_id:
            messagebox.showwarning("Copiar WhatsApp", "Selecione uma escala salva.")
            return
        self._copy_to_clipboard(self.saved_repository.build_whatsapp_text(selected_id))

    def export_current_xlsx(self) -> None:
        selected_id = self._selected_saved_scale_id()
        if not selected_id:
            messagebox.showwarning("Exportar Excel", "Salve ou selecione uma escala antes de exportar.")
            return
        try:
            path = export_saved_scale_xlsx(selected_id)
            messagebox.showinfo("Exportar Excel", f"Arquivo gerado: {path}")
        except Exception as exc:
            messagebox.showerror("Exportar Excel", str(exc))

    def export_current_docx(self) -> None:
        selected_id = self._selected_saved_scale_id()
        if not selected_id:
            messagebox.showwarning("Exportar Word", "Salve ou selecione uma escala antes de exportar.")
            return
        try:
            path = export_saved_scale_docx(selected_id)
            messagebox.showinfo("Exportar Word", f"Arquivo gerado: {path}")
        except Exception as exc:
            messagebox.showerror("Exportar Word", str(exc))

    def _selected_saved_scale_id(self) -> int | None:
        selected = self.saved_tree.selection()
        return int(selected[0]) if selected else self.current_saved_scale_id

    def _assignment_form_values(self) -> tuple[str, str, str, str]:
        return (
            self.edit_function_entry.get().strip(),
            self.edit_person_entry.get().strip(),
            self.edit_reason_entry.get().strip(),
            self.edit_warning_entry.get().strip(),
        )

    def clear_assignment_form(self) -> None:
        self.current_assignment_id = None
        for entry in (self.edit_function_entry, self.edit_person_entry, self.edit_reason_entry, self.edit_warning_entry):
            self._set_entry(entry, "")

    def _set_entry(self, entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, value or "")

    def _build_unsaved_whatsapp_text(self) -> str:
        if not self.current_result:
            return ""
        service_date = self.service_date_entry.get().strip()
        title = f"{self.current_result.model.name} - {service_date}" if service_date else self.current_result.model.name
        lines = [f"*{title.upper()}*", ""]
        if service_date:
            lines.append(f"*Data/periodo:* {service_date}")
        lines.append(f"*Modelo:* {self.current_result.model.name}")
        lines.append("")
        lines.append("*Equipe escalada:*")
        for assignment in self.current_result.assignments:
            person = assignment.person_name or "A definir"
            lines.append(f"- *{assignment.function_name}:* {person}")
        warnings = [assignment for assignment in self.current_result.assignments if assignment.warning]
        if warnings:
            lines.append("")
            lines.append("*Avisos para revisao:*")
            for assignment in warnings:
                lines.append(f"- {assignment.function_name}: {assignment.warning}")
        lines.append("")
        lines.append("_Revise a escala antes de publicar._")
        return "\n".join(lines)

    def _copy_to_clipboard(self, text: str) -> None:
        self.parent.clipboard_clear()
        self.parent.clipboard_append(text)
        self.warnings_text.delete("1.0", "end")
        self.warnings_text.insert("1.0", text)
        messagebox.showinfo("Copiar WhatsApp", "Texto copiado para a area de transferencia.")

    def clear_result_tree(self) -> None:
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

    def insert_assignments_into_result_tree(self, assignments) -> None:
        for index, assignment in enumerate(assignments, start=1):
            self.result_tree.insert(
                "",
                "end",
                iid=f"preview-{index}",
                values=(assignment.function_name, assignment.person_name, assignment.reason, assignment.warning),
            )
