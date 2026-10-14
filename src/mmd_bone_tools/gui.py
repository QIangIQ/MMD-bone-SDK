"""MMD Bone Tools desktop app (tkinter, no extra dependencies).

Three tabs mirror the command line: translate files or whole download
folders, convert bone names to another convention, and retarget a motion to
a model. Labels are in English and Japanese.
"""

from __future__ import annotations

import queue
import sys
import threading
import traceback
from pathlib import Path

from . import __version__, jobs
from . import dictionary as d

TITLE = f"MMD Bone Tools {__version__} / MMDボーンツール"
MODEL_TYPES = [("MMD model / モデル", "*.pmx *.pmd"), ("All files", "*.*")]
MOTION_TYPES = [("MMD motion / モーション", "*.vmd"), ("All files", "*.*")]
ANY_TYPES = [("MMD files", "*.pmx *.pmd *.vmd *.zip"), ("All files", "*.*")]
CONVENTION_LABELS = {
    "jp": "Japanese MMD / 日本語 (左腕)",
    "en": "English MMD / 英語 (arm_L)",
    "blender": "Blender (arm.L)",
    "unity": "Unity Humanoid (LeftUpperArm)",
    "vrm": "VRM 1.0 (leftUpperArm)",
    "mixamo": "Mixamo (mixamorig:LeftArm)",
}


def run_translate(paths, out_dir, style, rename, log) -> int:
    """Translate files, folders and zips; returns the number of files written."""
    out_root = Path(out_dir) if out_dir else None
    count = 0
    for raw in paths:
        p = Path(raw)
        base = out_root or (p.with_name(p.stem + "_en") if p.is_dir() or p.suffix.lower() == ".zip"
                            else p.parent)
        unpack = base / "_unpacked"
        for f, rel in jobs.collect([p], unpack):
            if unpack in f.parents:
                out = f
            elif p.is_file():
                out = jobs.default_out(f, "en", base)
            else:
                out = base / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            try:
                written, rep = jobs.translate_file(f, out, style=style, rename=rename)
            except Exception as e:  # keep going through a batch
                log(f"skipped {f.name}: {e}")
                continue
            count += 1
            log(f"wrote {written}")
            for line in jobs.report_lines(rep):
                log(line)
    log(f"done: {count} file(s) / 完了")
    return count


def main(argv=None) -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError:
        print("tkinter is not available; use the mmdbt command instead", file=sys.stderr)
        return 1

    root = tk.Tk()
    root.title(TITLE)
    root.minsize(720, 520)
    events: queue.Queue = queue.Queue()

    def log(msg: str) -> None:
        events.put(msg)

    def pump() -> None:
        while not events.empty():
            item = events.get_nowait()
            if callable(item):
                item()
                continue
            output.configure(state="normal")
            output.insert("end", item + "\n")
            output.see("end")
            output.configure(state="disabled")
        root.after(100, pump)

    busy = tk.BooleanVar(value=False)

    def background(fn, *args) -> None:
        if busy.get():
            return
        busy.set(True)

        def work():
            try:
                fn(*args)
            except Exception as e:
                log(f"error: {e}")
                log(traceback.format_exc(limit=2))
            finally:
                events.put(lambda: busy.set(False))

        threading.Thread(target=work, daemon=True).start()

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=False, padx=8, pady=8)

    def file_row(parent, row, label, var, types, save=False, folder=False):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(parent, textvariable=var, width=60).grid(row=row, column=1, sticky="ew", padx=4)

        def browse():
            if folder:
                v = filedialog.askdirectory()
            elif save:
                v = filedialog.asksaveasfilename(filetypes=types)
            else:
                v = filedialog.askopenfilename(filetypes=types)
            if v:
                var.set(v)

        ttk.Button(parent, text="…", width=3, command=browse).grid(row=row, column=2, padx=4)

    # --- Translate tab
    tab = ttk.Frame(nb, padding=8)
    tab.columnconfigure(1, weight=1)
    nb.add(tab, text="Translate / 翻訳")
    sources = tk.Listbox(tab, height=5)
    sources.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4)
    for p in argv or []:
        sources.insert("end", p)
    btns = ttk.Frame(tab)
    btns.grid(row=0, column=2, sticky="n")

    def add_files():
        for f in filedialog.askopenfilenames(filetypes=ANY_TYPES):
            sources.insert("end", f)

    def add_folder():
        f = filedialog.askdirectory()
        if f:
            sources.insert("end", f)

    ttk.Button(btns, text="Add files / ファイル", command=add_files).pack(fill="x", pady=1)
    ttk.Button(btns, text="Add folder / フォルダ", command=add_folder).pack(fill="x", pady=1)
    ttk.Button(btns, text="Clear / クリア", command=lambda: sources.delete(0, "end")).pack(fill="x", pady=1)
    t_out = tk.StringVar()
    file_row(tab, 1, "Output folder / 出力先", t_out, None, folder=True)
    ttk.Label(tab, text="(empty: next to each input / 空欄: 元ファイルの隣)").grid(
        row=2, column=1, sticky="w", padx=4)
    t_style = tk.StringVar(value="en")
    t_rename = tk.BooleanVar(value=False)
    opts = ttk.Frame(tab)
    opts.grid(row=3, column=0, columnspan=3, sticky="w", pady=4)
    ttk.Radiobutton(opts, text="MMD English (arm_L)", variable=t_style, value="en").pack(side="left")
    ttk.Radiobutton(opts, text="Blender (arm.L)", variable=t_style, value="blender").pack(side="left")
    ttk.Checkbutton(opts, text="Replace Japanese names in models / モデルの日本語名を置き換える",
                    variable=t_rename).pack(side="left", padx=12)

    def do_translate():
        paths = list(sources.get(0, "end"))
        if not paths:
            messagebox.showinfo(TITLE, "Add files or a folder first.\nファイルかフォルダを追加してください。")
            return
        background(run_translate, paths, t_out.get() or None, t_style.get(), t_rename.get(), log)

    ttk.Button(tab, text="Translate / 翻訳する", command=do_translate).grid(
        row=4, column=0, columnspan=3, pady=6)

    # --- Convert tab
    tab = ttk.Frame(nb, padding=8)
    tab.columnconfigure(1, weight=1)
    nb.add(tab, text="Convert / 変換")
    c_in, c_out = tk.StringVar(), tk.StringVar()
    file_row(tab, 0, "Model or motion / 入力", c_in, ANY_TYPES)
    ttk.Label(tab, text="Convert to / 変換先").grid(row=1, column=0, sticky="w", padx=4)
    c_to = ttk.Combobox(tab, state="readonly", values=list(CONVENTION_LABELS.values()))
    c_to.current(1)
    c_to.grid(row=1, column=1, sticky="w", padx=4, pady=3)
    file_row(tab, 2, "Save as / 保存先 (optional)", c_out, ANY_TYPES, save=True)

    def do_convert():
        if not c_in.get():
            return
        to = list(CONVENTION_LABELS)[c_to.current()]

        def work():
            out, rep = jobs.convert_file(c_in.get(), to, c_out.get() or None)
            log(f"wrote {out}")
            for line in jobs.report_lines(rep):
                log(line)

        background(work)

    ttk.Button(tab, text="Convert / 変換する", command=do_convert).grid(row=3, column=0, columnspan=3, pady=6)

    # --- Retarget tab
    tab = ttk.Frame(nb, padding=8)
    tab.columnconfigure(1, weight=1)
    nb.add(tab, text="Retarget / リターゲット")
    r_motion, r_model, r_source, r_out = (tk.StringVar() for _ in range(4))
    r_scale = tk.StringVar()
    file_row(tab, 0, "Motion / モーション (.vmd)", r_motion, MOTION_TYPES)
    file_row(tab, 1, "Target model / 対象モデル", r_model, MODEL_TYPES)
    file_row(tab, 2, "Original model / 元モデル (optional)", r_source, MODEL_TYPES)
    ttk.Label(tab, text="Scale / 倍率 (optional)").grid(row=3, column=0, sticky="w", padx=4)
    ttk.Entry(tab, textvariable=r_scale, width=10).grid(row=3, column=1, sticky="w", padx=4, pady=3)
    file_row(tab, 4, "Save as / 保存先 (optional)", r_out, MOTION_TYPES, save=True)

    def do_retarget():
        if not (r_motion.get() and r_model.get()):
            messagebox.showinfo(
                TITLE, "Pick a motion and a target model.\nモーションと対象モデルを選んでください。")
            return
        try:
            scale = float(r_scale.get()) if r_scale.get().strip() else None
        except ValueError:
            messagebox.showerror(TITLE, "Scale must be a number. / 倍率は数値で入力してください。")
            return

        def work():
            out, rep = jobs.retarget_file(r_motion.get(), r_model.get(), r_out.get() or None,
                                          source_model=r_source.get() or None, scale=scale)
            log(f"wrote {out}")
            for line in jobs.report_lines(rep):
                log(line)

        background(work)

    ttk.Button(tab, text="Retarget / リターゲットする", command=do_retarget).grid(
        row=5, column=0, columnspan=3, pady=6)

    # --- Lookup tab
    tab = ttk.Frame(nb, padding=8)
    nb.add(tab, text="Bone lookup / ボーン検索")
    l_name = tk.StringVar()
    ttk.Label(tab, text="Bone name / ボーン名").grid(row=0, column=0, sticky="w", padx=4)
    entry = ttk.Entry(tab, textvariable=l_name, width=30)
    entry.grid(row=0, column=1, sticky="w", padx=4)

    def do_lookup(_event=None):
        name = l_name.get().strip()
        if not name:
            return
        e = d.lookup(name)
        if e is None:
            from .translate import translate_bone
            log(f"{name}: not a standard bone; English: {translate_bone(name).result}")
            return
        log(f"{name} ({e.id}): " + ", ".join(
            f"{c}={d.convert(name, c) or '-'}" for c in d.CONVENTIONS))

    entry.bind("<Return>", do_lookup)
    ttk.Button(tab, text="Look up / 検索", command=do_lookup).grid(row=0, column=2, padx=4)

    # --- shared log
    frame = ttk.Frame(root, padding=(8, 0, 8, 8))
    frame.pack(fill="both", expand=True)
    output = tk.Text(frame, height=14, state="disabled", wrap="word")
    scroll = ttk.Scrollbar(frame, command=output.yview)
    output.configure(yscrollcommand=scroll.set)
    output.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    log(f"{TITLE}  -  {len(d.BONES)} standard bones, conventions: {', '.join(d.CONVENTIONS)}")

    root.after(100, pump)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
