# gui.py - Proyecto 01 · YALex Lexer Generator
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import tempfile
import threading

# ── colour palette (rojo · naranja · amarillo) ───────────────────────────────
BG      = "#1a0a00"   # fondo muy oscuro (marrón casi negro)
BG2     = "#2d1200"   # panel secundario
BG3     = "#4a2000"   # panel terciario / selección
FG      = "#ffe8cc"   # texto principal (crema cálido)
FG2     = "#c8a070"   # texto secundario (naranja pálido)
GREEN   = "#ff6b00"   # acento naranja (usado donde antes era verde)
YELLOW  = "#ffd060"   # amarillo dorado
RED     = "#ff2d2d"   # rojo error
BLUE    = "#ff8c00"   # naranja oscuro (botones principales)
CYAN    = "#ffb347"   # naranja claro (encabezados/acentos)
FONT    = ("Courier New", 11)
FONT_SM = ("Courier New", 10)
FONT_H  = ("Helvetica", 12, "bold")
FONT_T  = ("Helvetica", 20, "bold")

# ── app state ────────────────────────────────────────────────────────────────
class AppState:
    def __init__(self):
        self.yal_path    = None
        self.input_path  = None
        self.parsed      = None   # result of YalexParser.parse()
        self.nfa_list    = []     # [(nfa, token_name), ...]
        self.dfa_start   = None
        self.dfa_states  = []
        self.skip_tokens = set()
        self.diagram_img = None   # PIL ImageTk
        self.tmp_png     = os.path.join(tempfile.gettempdir(), "yalex_diagram.png")


# ── helpers ──────────────────────────────────────────────────────────────────
def styled_button(parent, text, cmd, color=BLUE, **kw):
    btn = tk.Button(
        parent, text=text, command=cmd,
        bg=color, fg=BG, font=("Helvetica", 10, "bold"),
        relief="flat", padx=10, pady=4,
        activebackground=FG2, activeforeground=BG,
        cursor="hand2", **kw
    )
    return btn


def styled_label(parent, text, color=FG2, font=FONT_SM, **kw):
    return tk.Label(parent, text=text, bg=BG, fg=color, font=font, **kw)


def styled_text(parent, height=20, width=60):
    frame = tk.Frame(parent, bg=BG3, bd=1)
    txt = tk.Text(
        frame, height=height, width=width,
        bg=BG2, fg=FG, font=FONT,
        insertbackground=FG, selectbackground=BG3,
        relief="flat", padx=6, pady=6,
        wrap="none"
    )
    vsb = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=txt.xview)
    txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    vsb.pack(side="right", fill="y")
    hsb.pack(side="bottom", fill="x")
    txt.pack(side="left", fill="both", expand=True)
    return frame, txt


# ── main application ─────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.state = AppState()
        self.title("Proyecto 01")
        self.configure(bg=BG)
        self.geometry("1200x760")
        self.minsize(900, 600)
        self._apply_style()
        self._build_header()
        self._build_notebook()
        self._build_status()

    # ── style ────────────────────────────────────────────────────────────────
    def _apply_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook",        background=BG,  borderwidth=0)
        style.configure("TNotebook.Tab",    background=BG2, foreground=FG2,
                        font=("Helvetica", 10, "bold"), padding=[14, 6])
        style.map("TNotebook.Tab",
                  background=[("selected", BG3)],
                  foreground=[("selected", GREEN)])
        style.configure("TScrollbar", background=BG3, troughcolor=BG, borderwidth=0)
        style.configure("Treeview", background=BG2, fieldbackground=BG2,
                        foreground=FG, font=FONT_SM, rowheight=22)
        style.configure("Treeview.Heading", background=BG3, foreground=GREEN,
                        font=("Helvetica", 10, "bold"))
        style.map("Treeview", background=[("selected", BG3)])
        style.configure("TCombobox", fieldbackground=BG2, background=BG2,
                        foreground=FG, font=FONT_SM)

    # ── header ────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg="#0d0500", height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙  Proyecto 01",
                 bg="#0d0500", fg=YELLOW, font=FONT_T).pack(side="left", padx=20)

    # ── notebook ─────────────────────────────────────────────────────────────
    def _build_notebook(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=(4, 0))
        self.nb = nb
        self._tab_editor()
        self._tab_diagram()
        self._tab_analysis()

    # ── status bar ───────────────────────────────────────────────────────────
    def _build_status(self):
        bar = tk.Frame(self, bg="#0d0500", height=24)
        bar.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="Listo.")
        tk.Label(bar, textvariable=self.status_var,
                 bg="#0d0500", fg=FG2, font=("Helvetica", 9),
                 anchor="w").pack(side="left", padx=10)

    def set_status(self, msg, color=FG2):
        self.status_var.set(msg)
        self.update_idletasks()

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 1 · EDITOR YAL
    # ════════════════════════════════════════════════════════════════════════
    def _tab_editor(self):
        tab = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab, text="  Editor YAL  ")

        # toolbar
        toolbar = tk.Frame(tab, bg=BG, pady=6)
        toolbar.pack(fill="x", padx=10)
        styled_button(toolbar, "📂  Cargar .yal", self.load_yal).pack(side="left", padx=4)
        styled_button(toolbar, "💾  Guardar .yal", self.save_yal, color=FG2).pack(side="left", padx=4)
        styled_button(toolbar, "▶  Generar Lexer", self.generate_lexer, color=GREEN).pack(side="left", padx=4)
        self.yal_path_label = styled_label(toolbar, "Sin archivo cargado")
        self.yal_path_label.pack(side="left", padx=12)

        # split: editor | parsed info
        pane = tk.Frame(tab, bg=BG)
        pane.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        # left – editor
        left = tk.Frame(pane, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))
        styled_label(left, "Archivo .yal", color=CYAN, font=FONT_H).pack(anchor="w")
        ef, self.yal_text = styled_text(left, height=30, width=55)
        ef.pack(fill="both", expand=True)

        # right – parsed output
        right = tk.Frame(pane, bg=BG, width=340)
        right.pack(side="right", fill="both", expand=False, padx=(4, 0))
        right.pack_propagate(False)
        styled_label(right, "Reglas Parseadas", color=CYAN, font=FONT_H).pack(anchor="w")
        rf, self.rules_text = styled_text(right, height=30, width=38)
        rf.pack(fill="both", expand=True)
        self.rules_text.config(state="disabled")

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 2 · DIAGRAM
    # ════════════════════════════════════════════════════════════════════════
    def _tab_diagram(self):
        tab = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab, text="  Diagrama  ")

        toolbar = tk.Frame(tab, bg=BG, pady=6)
        toolbar.pack(fill="x", padx=10)

        styled_label(toolbar, "Mostrar:").pack(side="left", padx=(0, 6))
        self.diag_var = tk.StringVar(value="DFA Completo")
        self.diag_combo = ttk.Combobox(toolbar, textvariable=self.diag_var,
                                        state="readonly", width=30)
        self.diag_combo.pack(side="left", padx=4)
        styled_button(toolbar, "⟳  Generar Diagrama", self.show_diagram, color=CYAN).pack(side="left", padx=8)
        styled_button(toolbar, "🔍  Zoom +", lambda: self._zoom(1.2), color=BG3).pack(side="left", padx=2)
        styled_button(toolbar, "🔍  Zoom -", lambda: self._zoom(0.8), color=BG3).pack(side="left", padx=2)

        # canvas with scrollbars
        canvas_frame = tk.Frame(tab, bg=BG2, relief="flat", bd=1)
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self.diag_canvas = tk.Canvas(canvas_frame, bg=BG2, highlightthickness=0)
        vbar = ttk.Scrollbar(canvas_frame, orient="vertical",   command=self.diag_canvas.yview)
        hbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.diag_canvas.xview)
        self.diag_canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        vbar.pack(side="right",  fill="y")
        hbar.pack(side="bottom", fill="x")
        self.diag_canvas.pack(fill="both", expand=True)

        self.diag_canvas.bind("<ButtonPress-1>",   self._drag_start)
        self.diag_canvas.bind("<B1-Motion>",       self._drag_move)

        self._diag_zoom = 1.0
        self._raw_img   = None
        self._diag_drag = (0, 0)

        styled_label(tab, "Genera el lexer primero (tab Editor), luego haz clic en Generar Diagrama.",
                     color=FG2).pack(pady=4)

    def _drag_start(self, e):
        self._diag_drag = (e.x, e.y)
        self.diag_canvas.scan_mark(e.x, e.y)

    def _drag_move(self, e):
        self.diag_canvas.scan_dragto(e.x, e.y, gain=1)

    def _zoom(self, factor):
        if self._raw_img is None:
            return
        self._diag_zoom *= factor
        self._render_diagram_image()

    def _render_diagram_image(self):
        if self._raw_img is None:
            return
        from PIL import ImageTk
        w = int(self._raw_img.width  * self._diag_zoom)
        h = int(self._raw_img.height * self._diag_zoom)
        resized = self._raw_img.resize((w, h))
        self.state.diagram_img = ImageTk.PhotoImage(resized)
        self.diag_canvas.delete("all")
        self.diag_canvas.create_image(0, 0, anchor="nw", image=self.state.diagram_img)
        self.diag_canvas.configure(scrollregion=(0, 0, w, h))

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 3 · ANÁLISIS LÉXICO
    # ════════════════════════════════════════════════════════════════════════
    def _tab_analysis(self):
        tab = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab, text="  Análisis Léxico  ")

        toolbar = tk.Frame(tab, bg=BG, pady=6)
        toolbar.pack(fill="x", padx=10)
        styled_button(toolbar, "📂  Cargar texto", self.load_input).pack(side="left", padx=4)
        styled_button(toolbar, "▶  Analizar",      self.analyze,    color=GREEN).pack(side="left", padx=4)
        styled_button(toolbar, "🗑  Limpiar",       self.clear_results, color=BG3).pack(side="left", padx=4)
        self.input_path_label = styled_label(toolbar, "Sin archivo de entrada")
        self.input_path_label.pack(side="left", padx=12)

        # top: input text
        top = tk.Frame(tab, bg=BG)
        top.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        left = tk.Frame(top, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))
        styled_label(left, "Texto de entrada", color=CYAN, font=FONT_H).pack(anchor="w")
        if2, self.input_text = styled_text(left, height=14, width=55)
        if2.pack(fill="both", expand=True)

        right = tk.Frame(top, bg=BG, width=340)
        right.pack(side="right", fill="both", expand=False, padx=(4, 0))
        right.pack_propagate(False)
        styled_label(right, "Errores", color=RED, font=FONT_H).pack(anchor="w")
        ef, self.err_text = styled_text(right, height=14, width=38)
        ef.pack(fill="both", expand=True)
        self.err_text.config(state="disabled")

        # bottom: tokens table
        bot = tk.Frame(tab, bg=BG)
        bot.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        styled_label(bot, "Tokens reconocidos", color=CYAN, font=FONT_H).pack(anchor="w")

        cols = ("token", "lexema", "línea", "col")
        tree_frame = tk.Frame(bot, bg=BG)
        tree_frame.pack(fill="both", expand=True)
        self.token_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=10)
        for c, w in zip(cols, (150, 250, 70, 70)):
            self.token_tree.heading(c, text=c.upper())
            self.token_tree.column(c, width=w, anchor="w")
        vsb2 = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.token_tree.yview)
        hsb2 = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.token_tree.xview)
        self.token_tree.configure(yscrollcommand=vsb2.set, xscrollcommand=hsb2.set)
        vsb2.pack(side="right", fill="y")
        hsb2.pack(side="bottom", fill="x")
        self.token_tree.pack(fill="both", expand=True)
        self.token_tree.tag_configure("even", background=BG2)
        self.token_tree.tag_configure("odd",  background="#262637")

    # ════════════════════════════════════════════════════════════════════════
    #  ACTIONS
    # ════════════════════════════════════════════════════════════════════════

    def load_yal(self):
        path = filedialog.askopenfilename(
            title="Cargar archivo .yal",
            filetypes=[("YALex files", "*.yal"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{e}")
            return
        self.state.yal_path = path
        self.yal_path_label.config(text=os.path.basename(path))
        self.yal_text.delete("1.0", "end")
        self.yal_text.insert("end", content)
        self.set_status(f"Archivo cargado: {path}")

    def save_yal(self):
        path = self.state.yal_path
        if not path:
            path = filedialog.asksaveasfilename(
                defaultextension=".yal",
                filetypes=[("YALex files", "*.yal"), ("All files", "*.*")]
            )
            if not path:
                return
            self.state.yal_path = path
        content = self.yal_text.get("1.0", "end-1c")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.set_status(f"Guardado: {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def generate_lexer(self):
        content = self.yal_text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("Aviso", "El editor está vacío. Carga o escribe un archivo .yal.")
            return

        # Save to temp file if no path
        if not self.state.yal_path:
            tmp = tempfile.NamedTemporaryFile(suffix=".yal", delete=False, mode="w", encoding="utf-8")
            tmp.write(content)
            tmp.close()
            yal_path = tmp.name
        else:
            # Write current editor content to file
            with open(self.state.yal_path, "w", encoding="utf-8") as f:
                f.write(content)
            yal_path = self.state.yal_path

        self.set_status("Parseando archivo .yal…")
        self.update_idletasks()

        try:
            from yal_parser import YalexParser
            from thompson import regex_to_nfa, State
            from nfa_to_dfa import nfa_to_dfa

            State.reset()
            parser = YalexParser(yal_path)
            result = parser.parse()
            self.state.parsed = result

            # Identify skip tokens (empty or comment actions)
            skip = set()
            nfa_list   = []
            token_names = []
            for rule in result["rules"]:
                action = rule.get("action", "").strip()
                # Determine token name from action
                tname = _extract_token_name(action, rule["regex"])
                rule["_token_name"] = tname
                if _is_skip_action(action):
                    skip.add(tname)
                try:
                    nfa = regex_to_nfa(rule["regex"])
                    nfa_list.append(nfa)
                    token_names.append(tname)
                except Exception as e:
                    self.set_status(f"Error en regex '{rule['regex'][:30]}': {e}", RED)
                    return

            self.state.nfa_list    = list(zip(nfa_list, token_names))
            self.state.skip_tokens = skip

            self.set_status("Construyendo DFA…")
            self.update_idletasks()

            dfa_start, dfa_states = nfa_to_dfa(nfa_list, token_names)
            self.state.dfa_start  = dfa_start
            self.state.dfa_states = dfa_states

            # Generate standalone lexer
            out_dir = os.path.dirname(yal_path) if self.state.yal_path else os.getcwd()
            lexer_out = os.path.join(out_dir, "generated_lexer.py")
            from lexer_runner import generate_standalone_lexer
            generate_standalone_lexer(dfa_start, dfa_states, list(skip), lexer_out)

            # Update parsed info panel
            self._update_rules_panel(result, token_names, dfa_states)

            # Update diagram combo
            options = ["DFA Completo"] + [f"NFA — regla {i+1}: {n}" for i, n in enumerate(token_names)]
            self.diag_combo["values"] = options
            self.diag_combo.current(0)

            n_states = len(dfa_states)
            self.set_status(
                f"✔  Lexer generado · {len(result['rules'])} reglas · {n_states} estados DFA · "
                f"Standalone: {lexer_out}"
            )
            messagebox.showinfo("Éxito", f"Lexer generado exitosamente.\n"
                                         f"• Reglas: {len(result['rules'])}\n"
                                         f"• Estados DFA: {n_states}\n"
                                         f"• Archivo: {lexer_out}")

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            messagebox.showerror("Error al generar lexer", f"{e}\n\n{tb[:600]}")
            self.set_status(f"Error: {e}")

    def _update_rules_panel(self, result, token_names, dfa_states):
        self.rules_text.config(state="normal")
        self.rules_text.delete("1.0", "end")
        lines = []
        lines.append(f"{'='*36}")
        lines.append(f"  LETS DEFINIDOS ({len(result['lets'])})")
        lines.append(f"{'='*36}")
        for k, v in result["lets"].items():
            lines.append(f"  {k} = {v[:40]}")
        lines.append("")
        lines.append(f"{'='*36}")
        lines.append(f"  REGLAS ({len(result['rules'])})")
        lines.append(f"{'='*36}")
        for i, (rule, tname) in enumerate(zip(result["rules"], token_names)):
            lines.append(f"\n[{i+1}] Token: {tname}")
            lines.append(f"     Regex: {rule['regex'][:50]}")
        lines.append("")
        lines.append(f"{'='*36}")
        lines.append(f"  DFA: {len(dfa_states)} estados")
        lines.append(f"{'='*36}")
        self.rules_text.insert("end", "\n".join(lines))
        self.rules_text.config(state="disabled")

    def show_diagram(self):
        if not self.state.dfa_start and not self.state.nfa_list:
            messagebox.showwarning("Aviso", "Genera el lexer primero.")
            return

        sel = self.diag_var.get()
        self.set_status("Generando diagrama…")
        self.update_idletasks()

        try:
            from diagram import generate_nfa_diagram, generate_dfa_diagram
            from PIL import Image

            png = self.state.tmp_png

            if sel == "DFA Completo":
                ok, err = generate_dfa_diagram(self.state.dfa_start, self.state.dfa_states, png)
            else:
                # Parse index from "NFA — regla N: NAME"
                try:
                    idx = int(sel.split("regla")[1].split(":")[0].strip()) - 1
                except:
                    idx = 0
                nfa, tname = self.state.nfa_list[idx]
                ok, err = generate_nfa_diagram(nfa, tname, png)

            if not ok:
                messagebox.showerror("Error Graphviz", f"No se pudo generar el diagrama:\n{err}")
                self.set_status("Error al generar diagrama.")
                return

            self._raw_img = Image.open(png)
            self._diag_zoom = 1.0
            self._render_diagram_image()
            self.nb.select(1)
            self.set_status("Diagrama generado.")

        except Exception as e:
            import traceback
            messagebox.showerror("Error", traceback.format_exc()[:800])

    def load_input(self):
        path = filedialog.askopenfilename(
            title="Cargar archivo de texto",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        self.state.input_path = path
        self.input_path_label.config(text=os.path.basename(path))
        self.input_text.delete("1.0", "end")
        self.input_text.insert("end", content)
        self.set_status(f"Texto cargado: {path}")

    def analyze(self):
        if not self.state.dfa_start:
            messagebox.showwarning("Aviso", "Genera el lexer primero (tab Editor).")
            return
        text = self.input_text.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showwarning("Aviso", "El texto de entrada está vacío.")
            return

        self.set_status("Analizando…")
        self.update_idletasks()

        try:
            from lexer_runner import run_lexer
            tokens, errors = run_lexer(self.state.dfa_start, text, self.state.skip_tokens)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.set_status(f"Error: {e}")
            return

        # Fill token tree
        for item in self.token_tree.get_children():
            self.token_tree.delete(item)
        for i, (tname, lexeme, ln, cl) in enumerate(tokens):
            tag = "even" if i % 2 == 0 else "odd"
            self.token_tree.insert("", "end", values=(tname, repr(lexeme), ln, cl), tags=(tag,))

        # Fill errors
        self.err_text.config(state="normal")
        self.err_text.delete("1.0", "end")
        if errors:
            for ln, cl, ch in errors:
                self.err_text.insert("end", f"Línea {ln}, col {cl}: carácter inesperado {repr(ch)}\n", "err")
            self.err_text.tag_configure("err", foreground=RED)
        else:
            self.err_text.insert("end", "Sin errores.\n", "ok")
            self.err_text.tag_configure("ok", foreground=GREEN)
        self.err_text.config(state="disabled")

        # Highlight errors in input text
        self.input_text.tag_remove("error_char", "1.0", "end")
        self.input_text.tag_configure("error_char", background="#3b1e2b", foreground=RED)
        for ln, cl, _ in errors:
            idx = f"{ln}.{cl - 1}"
            idx2 = f"{ln}.{cl}"
            self.input_text.tag_add("error_char", idx, idx2)

        self.nb.select(2)
        self.set_status(
            f"✔  Análisis completo · {len(tokens)} tokens · {len(errors)} errores"
        )

    def clear_results(self):
        for item in self.token_tree.get_children():
            self.token_tree.delete(item)
        self.err_text.config(state="normal")
        self.err_text.delete("1.0", "end")
        self.err_text.config(state="disabled")
        self.input_text.tag_remove("error_char", "1.0", "end")
        self.set_status("Resultados limpiados.")


# ── utility functions ────────────────────────────────────────────────────────
def _extract_token_name(action, regex):
    """Extract a meaningful token name from the rule action."""
    action = action.strip()
    if not action:
        return "_SKIP"
    # return TOKEN_NAME
    for kw in ("return ", "Return ", "RETURN "):
        if kw in action:
            rest = action[action.index(kw) + len(kw):].strip()
            name = rest.split()[0].rstrip(";)(,")
            return name if name else "_TOKEN"
    # If action looks like a comment only
    if action.startswith("/*") or action.startswith("(*") or action.startswith("#"):
        return "_SKIP"
    # Use action itself if short
    if len(action) <= 20:
        return action.replace(" ", "_").upper()
    return "_ACTION"


def _is_skip_action(action):
    action = action.strip()
    if not action:
        return True
    if action.startswith("/*") or action.startswith("(*") or action.startswith("#"):
        return True
    if action in ("return lexbuf", "skip", "/* skip */", "# skip"):
        return True
    return False


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
