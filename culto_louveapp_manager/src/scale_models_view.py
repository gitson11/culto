from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from src.scale_models import ScaleModel, ScaleModelSlot
from src.scale_models_repository import ScaleModelRepository


SERVICE_TYPES = ["Culto comum", "Culto com ceia", "Culto de oracao", "Culto jovem", "Evento especial"]
VOICE_VALUES = ["", "soprano", "contralto", "tenor", "baritono", "baixo", "instrumentista"]


class ScaleModelsView:
    def __init__(self, parent: tk.Widget) -> None:
        self.parent = parent
        self.repo = ScaleModelRepository()
        self.current_model_id: int | None = None
        self.current_slot_id: int | None = None
        self.model_widgets: dict[str, tk.Widget] = {}
        self.slot_widgets: dict[str, tk.Widget] = {}
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.parent.grid_columnconfigure(0, weight=2)
        self.parent.grid_columnconfigure(1, weight=3)
        self.parent.grid_rowconfigure(0, weight=1)

        model_panel = ctk.CTkFrame(self.parent)
        model_panel.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        model_panel.grid_columnconfigure(1, weight=1)
        model_panel.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(model_panel, text="Modelo de escala", font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 8)
        )
        self._add_model_field(model_panel, 1, "name", "Nome", "entry")
        self._add_model_field(model_panel, 2, "service_type", "Tipo de culto", "combo")
        self._add_model_field(model_panel, 3, "description", "Descricao", "textbox")

        model_actions = ctk.CTkFrame(model_panel, fg_color="transparent")
        model_actions.grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        for text, command in (
            ("Novo", self.clear_model_form),
            ("Salvar", self.save_model),
            ("Editar", self.update_model),
            ("Excluir", self.delete_model),
        ):
            ctk.CTkButton(model_actions, text=text, width=85, command=command).pack(side="left", padx=4)

        search_bar = ctk.CTkFrame(model_panel, fg_color="transparent")
        search_bar.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=(8, 10))
        search_bar.grid_columnconfigure(0, weight=1)
        search_bar.grid_rowconfigure(1, weight=1)
        self.search_entry = ctk.CTkEntry(search_bar, placeholder_text="Buscar modelos")
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 6))
        ctk.CTkButton(search_bar, text="Buscar", width=90, command=self.refresh_models).grid(row=0, column=1, pady=(0, 6))
        self.models_tree = self._make_tree(
            search_bar,
            ("id", "name", "service_type", "active"),
            {"id": "ID", "name": "Modelo", "service_type": "Tipo", "active": "Ativo"},
            {"id": 50, "name": 180, "service_type": 140, "active": 70},
        )
        self.models_tree.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.models_tree.bind("<<TreeviewSelect>>", self.on_model_selected)

        slot_panel = ctk.CTkFrame(self.parent)
        slot_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        slot_panel.grid_columnconfigure(1, weight=1)
        slot_panel.grid_rowconfigure(7, weight=1)

        ctk.CTkLabel(slot_panel, text="Funcoes exigidas pelo modelo", font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 8)
        )
        self._add_slot_field(slot_panel, 1, "function_name", "Funcao", "entry")
        self._add_slot_field(slot_panel, 2, "quantity", "Quantidade", "entry")
        self._add_slot_field(slot_panel, 3, "desired_instruments", "Instrumentos desejados", "entry")
        self._add_slot_field(slot_panel, 4, "desired_voice", "Voz desejada", "combo")
        self._add_slot_field(slot_panel, 5, "sort_order", "Ordem", "entry")
        self._add_slot_field(slot_panel, 6, "notes", "Observacoes", "textbox")

        slot_actions = ctk.CTkFrame(slot_panel, fg_color="transparent")
        slot_actions.grid(row=7, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        for text, command in (
            ("Nova funcao", self.clear_slot_form),
            ("Adicionar", self.save_slot),
            ("Editar", self.update_slot),
            ("Excluir", self.delete_slot),
        ):
            ctk.CTkButton(slot_actions, text=text, width=105, command=command).pack(side="left", padx=4)

        self.slots_tree = self._make_tree(
            slot_panel,
            ("id", "function", "quantity", "instruments", "voice", "order"),
            {"id": "ID", "function": "Funcao", "quantity": "Qtd", "instruments": "Instrumentos", "voice": "Voz", "order": "Ordem"},
            {"id": 50, "function": 150, "quantity": 55, "instruments": 170, "voice": 110, "order": 60},
        )
        self.slots_tree.grid(row=8, column=0, columnspan=2, sticky="nsew", padx=10, pady=(6, 10))
        self.slots_tree.bind("<<TreeviewSelect>>", self.on_slot_selected)

    def _add_model_field(self, parent: tk.Widget, row: int, field: str, label: str, kind: str) -> None:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="w", padx=12, pady=4)
        if kind == "textbox":
            widget = ctk.CTkTextbox(parent, height=70, wrap="word")
        elif kind == "combo":
            widget = ctk.CTkComboBox(parent, values=SERVICE_TYPES, state="normal")
        else:
            widget = ctk.CTkEntry(parent)
        widget.grid(row=row, column=1, sticky="ew", padx=(0, 12), pady=4)
        self.model_widgets[field] = widget

    def _add_slot_field(self, parent: tk.Widget, row: int, field: str, label: str, kind: str) -> None:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="w", padx=12, pady=4)
        if kind == "textbox":
            widget = ctk.CTkTextbox(parent, height=70, wrap="word")
        elif kind == "combo":
            widget = ctk.CTkComboBox(parent, values=VOICE_VALUES, state="normal")
        else:
            widget = ctk.CTkEntry(parent)
        widget.grid(row=row, column=1, sticky="ew", padx=(0, 12), pady=4)
        self.slot_widgets[field] = widget

    def _make_tree(self, parent, columns, headings, widths) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths.get(column, 120), minwidth=40, stretch=True)
        return tree

    def _value(self, widget: tk.Widget) -> str:
        if isinstance(widget, ctk.CTkTextbox):
            return widget.get("1.0", "end").strip()
        return widget.get().strip()

    def _set_value(self, widget: tk.Widget, value: str) -> None:
        if isinstance(widget, ctk.CTkTextbox):
            widget.delete("1.0", "end")
            widget.insert("1.0", value or "")
        elif isinstance(widget, ctk.CTkComboBox):
            widget.set(value or "")
        else:
            widget.delete(0, "end")
            widget.insert(0, value or "")

    def refresh(self) -> None:
        self.repo.ensure_tables()
        self.refresh_models()
        self.refresh_slots()

    def refresh_models(self) -> None:
        for item in self.models_tree.get_children():
            self.models_tree.delete(item)
        for model in self.repo.list_models(self.search_entry.get() if hasattr(self, "search_entry") else ""):
            self.models_tree.insert("", "end", iid=str(model.id), values=(model.id, model.name, model.service_type, "Sim" if model.active else "Nao"))

    def refresh_slots(self) -> None:
        for item in self.slots_tree.get_children():
            self.slots_tree.delete(item)
        if not self.current_model_id:
            return
        for slot in self.repo.list_slots(self.current_model_id):
            self.slots_tree.insert(
                "",
                "end",
                iid=str(slot.id),
                values=(slot.id, slot.function_name, slot.quantity, slot.desired_instruments, slot.desired_voice, slot.sort_order),
            )

    def collect_model(self) -> ScaleModel:
        return ScaleModel(
            name=self._value(self.model_widgets["name"]),
            service_type=self._value(self.model_widgets["service_type"]),
            description=self._value(self.model_widgets["description"]),
            active=1,
        )

    def collect_slot(self) -> ScaleModelSlot:
        quantity_raw = self._value(self.slot_widgets["quantity"])
        order_raw = self._value(self.slot_widgets["sort_order"])
        return ScaleModelSlot(
            model_id=self.current_model_id,
            function_name=self._value(self.slot_widgets["function_name"]),
            quantity=int(quantity_raw) if quantity_raw.isdigit() else 1,
            desired_instruments=self._value(self.slot_widgets["desired_instruments"]),
            desired_voice=self._value(self.slot_widgets["desired_voice"]),
            notes=self._value(self.slot_widgets["notes"]),
            sort_order=int(order_raw) if order_raw.isdigit() else 0,
        )

    def save_model(self) -> None:
        try:
            self.current_model_id = self.repo.save_model(self.collect_model())
            self.refresh_models()
            self.refresh_slots()
            messagebox.showinfo("Modelo de escala", "Modelo salvo.")
        except Exception as exc:
            messagebox.showerror("Modelo de escala", str(exc))

    def update_model(self) -> None:
        if not self.current_model_id:
            messagebox.showwarning("Modelo de escala", "Selecione um modelo.")
            return
        try:
            self.repo.update_model(self.current_model_id, self.collect_model())
            self.refresh_models()
            messagebox.showinfo("Modelo de escala", "Modelo atualizado.")
        except Exception as exc:
            messagebox.showerror("Modelo de escala", str(exc))

    def delete_model(self) -> None:
        if not self.current_model_id:
            messagebox.showwarning("Modelo de escala", "Selecione um modelo.")
            return
        if not messagebox.askyesno("Modelo de escala", "Excluir este modelo e suas funcoes?"):
            return
        self.repo.delete_model(self.current_model_id)
        self.clear_model_form()
        self.refresh_models()
        self.refresh_slots()

    def save_slot(self) -> None:
        if not self.current_model_id:
            messagebox.showwarning("Funcao da escala", "Selecione um modelo primeiro.")
            return
        try:
            self.current_slot_id = self.repo.save_slot(self.collect_slot())
            self.refresh_slots()
            messagebox.showinfo("Funcao da escala", "Funcao adicionada.")
        except Exception as exc:
            messagebox.showerror("Funcao da escala", str(exc))

    def update_slot(self) -> None:
        if not self.current_slot_id:
            messagebox.showwarning("Funcao da escala", "Selecione uma funcao.")
            return
        try:
            self.repo.update_slot(self.current_slot_id, self.collect_slot())
            self.refresh_slots()
            messagebox.showinfo("Funcao da escala", "Funcao atualizada.")
        except Exception as exc:
            messagebox.showerror("Funcao da escala", str(exc))

    def delete_slot(self) -> None:
        if not self.current_slot_id:
            messagebox.showwarning("Funcao da escala", "Selecione uma funcao.")
            return
        self.repo.delete_slot(self.current_slot_id)
        self.clear_slot_form()
        self.refresh_slots()

    def on_model_selected(self, _event) -> None:
        selected = self.models_tree.selection()
        if not selected:
            return
        self.current_model_id = int(selected[0])
        model = self.repo.get_model(self.current_model_id)
        if model:
            self._set_value(self.model_widgets["name"], model.name)
            self._set_value(self.model_widgets["service_type"], model.service_type)
            self._set_value(self.model_widgets["description"], model.description)
        self.clear_slot_form()
        self.refresh_slots()

    def on_slot_selected(self, _event) -> None:
        selected = self.slots_tree.selection()
        if not selected:
            return
        self.current_slot_id = int(selected[0])
        slot = self.repo.get_slot(self.current_slot_id)
        if slot:
            self._set_value(self.slot_widgets["function_name"], slot.function_name)
            self._set_value(self.slot_widgets["quantity"], str(slot.quantity))
            self._set_value(self.slot_widgets["desired_instruments"], slot.desired_instruments)
            self._set_value(self.slot_widgets["desired_voice"], slot.desired_voice)
            self._set_value(self.slot_widgets["sort_order"], str(slot.sort_order))
            self._set_value(self.slot_widgets["notes"], slot.notes)

    def clear_model_form(self) -> None:
        self.current_model_id = None
        for widget in self.model_widgets.values():
            self._set_value(widget, "")
        self.clear_slot_form()
        self.refresh_slots()

    def clear_slot_form(self) -> None:
        self.current_slot_id = None
        for widget in self.slot_widgets.values():
            self._set_value(widget, "")
        self._set_value(self.slot_widgets["quantity"], "1")
        self._set_value(self.slot_widgets["sort_order"], "0")
