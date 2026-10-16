"""Explicitly opened local settings window; never opened during capture."""

from __future__ import annotations

import sys


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("Screenshotter requires Windows 11.")

    import os
    import tkinter as tk
    from tkinter import messagebox, ttk

    from screenshotter.errors import UserError
    from screenshotter.settings import Settings, load_settings, save_key, save_settings, saved_key

    root = tk.Tk()
    root.title("Screenshotter settings")
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=22)
    frame.grid()
    try:
        settings = load_settings()
    except UserError:
        settings = Settings()
    try:
        has_key = bool(saved_key())
    except UserError:
        has_key = False

    ttk.Label(frame, text="Background screenshot questions", font=("Segoe UI", 14)).grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))
    ttk.Label(frame, text="OpenAI API key").grid(row=1, column=0, sticky="w", padx=(0, 15))
    key = tk.StringVar()
    entry = ttk.Entry(frame, textvariable=key, show="•", width=48)
    entry.grid(row=1, column=1)
    entry.focus_set()
    hint = "A saved key exists. Leave blank to keep it." if has_key else "Stored in Windows Credential Manager, not a text file."
    ttk.Label(frame, text=hint).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 14))
    ttk.Label(frame, text="Vision model").grid(row=3, column=0, sticky="w")
    model = tk.StringVar(value=settings.model)
    ttk.Entry(frame, textvariable=model, width=48).grid(row=3, column=1)
    ttk.Label(frame, text="Maximum answer tokens").grid(row=4, column=0, sticky="w", pady=10)
    tokens = tk.StringVar(value=str(settings.max_output_tokens))
    ttk.Spinbox(frame, from_=128, to=2000, textvariable=tokens, width=12).grid(row=4, column=1, sticky="w")
    ttk.Label(frame, text=(
        "Uses separate API billing; no ChatGPT subscription integration.\n"
        "5 sends all monitors; Shift+5 sends only your drag selection.\n"
        "Images stay in memory locally and are sent to OpenAI.\n"
        "No notifications, overlays, clipboard changes, or app switching."
    )).grid(row=5, column=0, columnspan=2, sticky="w", pady=12)
    if os.environ.get("OPENAI_API_KEY"):
        ttk.Label(frame, text="OPENAI_API_KEY is set and takes precedence over the saved key.").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(0, 10))

    def save():
        try:
            try:
                limit = int(tokens.get())
            except ValueError:
                raise UserError("Enter a whole number for the answer length.") from None
            updated = Settings(model.get().strip(), limit, settings.timeout_seconds)
            updated.validate()
            if key.get().strip():
                save_key(key.get())
            elif not has_key and not os.environ.get("OPENAI_API_KEY"):
                raise UserError("Enter your API key first.")
            save_settings(updated)
        except Exception as exc:
            text = str(exc) if isinstance(exc, UserError) else "Windows could not save settings or credentials."
            messagebox.showerror("Cannot save", text, parent=root)
            return
        key.set("")
        messagebox.showinfo("Saved", "Settings saved. Quit Screenshotter if running, then run Start.cmd.", parent=root)
        root.destroy()

    ttk.Button(frame, text="Save settings", command=save).grid(row=7, column=1, sticky="e")
    root.mainloop()


if __name__ == "__main__":
    main()
