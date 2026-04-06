#!/usr/bin/env python3
import json
import os
import signal
import subprocess
import tempfile
import threading
import time
import wave
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gtk4LayerShell", "1.0")

from gi.repository import Adw, Gio, GLib, Gtk, Gdk, Gtk4LayerShell
from vosk import KaldiRecognizer, Model

from harness_config import (
    CONFIG_FILE,
    PLAYBOOK_FILE,
    PROMPT_MEMORY_FILE,
    ROOT,
    append_log,
    build_runner_command,
    ensure_config,
    list_provider_names,
    load_config,
    set_provider,
)

APP_ID = "local.system.agent"
STATE_FILE = Path("/tmp/system-agent-state.json")
DOUBLE_TAP_WINDOW = 0.35
HOLD_GUARD_WINDOW = 0.9


def load_playbook_hints():
    if not PLAYBOOK_FILE.exists():
        return []
    try:
        data = json.loads(PLAYBOOK_FILE.read_text())
    except Exception:
        return []

    hints = []
    for lesson in data.get("lessons", [])[:4]:
        title = lesson.get("title", "Unnamed scenario")
        strategy = lesson.get("strategy", "")
        if strategy:
            hints.append(f"{title}: {strategy}")
    return hints


def normalize_prompt(text):
    return " ".join(text.strip().lower().split())


def record_prompt_usage(prompt):
    normalized = normalize_prompt(prompt)
    if len(normalized) < 8:
        return

    try:
        data = json.loads(PROMPT_MEMORY_FILE.read_text()) if PROMPT_MEMORY_FILE.exists() else {"prompts": []}
    except Exception:
        data = {"prompts": []}

    prompts = data.setdefault("prompts", [])
    for item in prompts:
        if item.get("normalized") == normalized:
            item["count"] = int(item.get("count", 0)) + 1
            item["last_used"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            item["example"] = prompt.strip()[:240]
            break
    else:
        prompts.append(
            {
                "normalized": normalized,
                "example": prompt.strip()[:240],
                "count": 1,
                "last_used": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )

    prompts.sort(key=lambda item: (int(item.get("count", 0)), item.get("last_used", "")), reverse=True)
    data["prompts"] = prompts[:40]
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    PROMPT_MEMORY_FILE.write_text(json.dumps(data, indent=2))


class SystemAgentWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="System Agent")
        self.set_default_size(680, 124)
        self.set_hide_on_close(False)
        self.set_decorated(False)
        self.set_resizable(False)

        self.model = None
        self.config = load_config()
        self.recorder_process = None
        self.recording_path = None
        self.codex_process = None
        self.voice_mode = False

        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.ON_DEMAND)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, True)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.TOP, 96)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.LEFT, 420)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.RIGHT, 420)
        Gtk4LayerShell.set_namespace(self, "system-agent-overlay")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)

        chrome_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        chrome_row.set_halign(Gtk.Align.END)

        self.close_button = Gtk.Button(label="×")
        self.close_button.add_css_class("flat")
        self.close_button.add_css_class("close-chip")
        self.close_button.connect("clicked", self.on_close_clicked)
        self.close_button.set_size_request(28, 28)
        chrome_row.append(self.close_button)
        outer.append(chrome_row)

        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.prompt_view = Gtk.TextView()
        self.prompt_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.prompt_view.set_top_margin(12)
        self.prompt_view.set_bottom_margin(12)
        self.prompt_view.set_left_margin(14)
        self.prompt_view.set_right_margin(14)
        self.prompt_view.set_size_request(-1, 72)

        frame = Gtk.Frame()
        frame.set_child(self.prompt_view)
        frame.set_hexpand(True)
        frame.add_css_class("prompt-shell")
        input_row.append(frame)

        self.send_button = Gtk.Button(label="Send")
        self.send_button.add_css_class("send-chip")
        self.send_button.connect("clicked", self.on_send_clicked)
        self.send_button.set_size_request(68, 40)
        input_row.append(self.send_button)

        outer.append(input_row)

        self.set_content(outer)
        self._install_css()
        self._install_key_controller()

    def _install_css(self):
        css = Gtk.CssProvider()
        css.load_from_data(
            b"""
            window {
              background: rgba(10, 14, 20, 0.76);
              border-radius: 24px;
            }
            .prompt-shell {
              background: rgba(22, 29, 38, 0.92);
              border: 1px solid rgba(154, 173, 193, 0.18);
              border-radius: 22px;
              box-shadow: 0 18px 40px rgba(0, 0, 0, 0.32);
            }
            textview {
              background: transparent;
              color: #eef4fb;
              border-radius: 22px;
              font-size: 16px;
              caret-color: #eef4fb;
            }
            textview text {
              background: transparent;
            }
            .send-chip, .close-chip {
              border-radius: 999px;
              min-height: 0;
              min-width: 0;
            }
            .send-chip {
              background: #eef4fb;
              color: #0c1117;
              font-weight: 700;
              padding: 0 14px;
            }
            .close-chip {
              background: rgba(238, 244, 251, 0.08);
              color: #c8d3df;
              font-size: 18px;
              padding: 0;
            }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _install_key_controller(self):
        controller = Gtk.EventControllerKey.new()
        controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(controller)

    def on_key_pressed(self, _controller, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Escape:
            self.close_overlay()
            return True
        if keyval == Gdk.KEY_Return:
            self.on_send_clicked(None)
            return True
        return False

    def close_overlay(self):
        if self.recorder_process is not None:
            self.stop_recording(submit=False)
        self.hide()
        self.set_status("Ready")

    def on_close_clicked(self, _button):
        self.close_overlay()

    def set_status(self, message):
        if self.voice_mode:
            self.send_button.set_label("Listening")
        elif message == "Running…":
            self.send_button.set_label("Running")
        else:
            self.send_button.set_label("Send")
        self.send_button.set_sensitive(message not in {"Running…", "Transcribing…", "Listening while Super is held…"})

    def get_prompt_text(self):
        buffer_ = self.prompt_view.get_buffer()
        start, end = buffer_.get_bounds()
        return buffer_.get_text(start, end, True).strip()

    def set_prompt_text(self, text):
        self.prompt_view.get_buffer().set_text(text)

    def present_text_overlay(self):
        self.voice_mode = False
        self.config = load_config()
        self.close_button.set_visible(True)
        self.set_status("Ready")
        self.send_button.set_visible(True)
        self.present()
        self.prompt_view.grab_focus()

    def present_voice_overlay(self):
        self.voice_mode = True
        self.config = load_config()
        self.close_button.set_visible(True)
        self.send_button.set_visible(False)
        self.present()
        self.prompt_view.grab_focus()
        if self.recorder_process is None:
            self.start_recording()

    def ensure_vosk_model(self):
        if self.model is None:
            model_dir = Path(
                self.config.get("voice", {}).get(
                    "model_dir", str(ROOT / "vosk-model-small-en-us-0.15")
                )
            ).expanduser()
            self.model = Model(str(model_dir))
        return self.model

    def start_recording(self):
        fd, path = tempfile.mkstemp(prefix="system-agent-", suffix=".wav")
        os.close(fd)
        self.recording_path = path
        cmd = ["pw-record", "--rate", "16000", "--channels", "1", "--format", "s16", path]
        self.recorder_process = subprocess.Popen(cmd)
        self.set_status("Listening while Super is held…")

    def stop_recording(self, submit=True):
        if self.recorder_process is None:
            return
        self.recorder_process.send_signal(signal.SIGINT)
        self.recorder_process.wait(timeout=10)
        self.recorder_process = None
        self.set_status("Transcribing…")
        threading.Thread(target=self._transcribe_recording, args=(submit,), daemon=True).start()

    def _transcribe_recording(self, submit):
        try:
            model = self.ensure_vosk_model()
            with wave.open(self.recording_path, "rb") as wf:
                rec = KaldiRecognizer(model, wf.getframerate())
                parts = []
                while True:
                    data = wf.readframes(4000)
                    if not data:
                        break
                    if rec.AcceptWaveform(data):
                        parts.append(json.loads(rec.Result()).get("text", ""))
                parts.append(json.loads(rec.FinalResult()).get("text", ""))
            text = " ".join(part for part in parts if part).strip()
            GLib.idle_add(self._finish_transcription, text, submit)
        except Exception as err:
            GLib.idle_add(self.set_status, f"Transcription failed: {err}")
        finally:
            if self.recording_path and os.path.exists(self.recording_path):
                os.unlink(self.recording_path)
            self.recording_path = None

    def _finish_transcription(self, text, submit):
        current = self.get_prompt_text()
        combined = f"{current}\n{text}".strip() if current else text
        self.set_prompt_text(combined)
        if submit and combined:
            self.run_prompt(combined)
        else:
            self.set_status("Voice ready" if text else "No speech detected")

    def on_send_clicked(self, _button):
        prompt = self.get_prompt_text()
        if not prompt:
            self.set_status("Enter a prompt first")
            return
        self.run_prompt(prompt)

    def run_prompt(self, prompt):
        if self.codex_process and self.codex_process.poll() is None:
            self.set_status("Agent already running")
            return
        record_prompt_usage(prompt)
        self.hide()
        self.set_status("Running…")
        threading.Thread(target=self._run_codex, args=(prompt,), daemon=True).start()

    def _build_system_prompt(self, user_prompt):
        self.config = load_config()
        playbook_hints = load_playbook_hints()
        working_root = Path(self.config.get("working_root", str(Path.home()))).expanduser()
        instructions = list(self.config.get("system_instructions", []))
        instructions.append(f"Working root: {working_root}.")
        if playbook_hints:
            instructions.append("Local learned playbook hints:")
            instructions.extend(f"- {hint}" for hint in playbook_hints)
        instructions.extend(["User request follows.", user_prompt])
        return "\n".join(instructions)

    def _run_codex(self, user_prompt):
        prompt = self._build_system_prompt(user_prompt)
        cmd = build_runner_command(prompt, training=False)
        try:
            append_log(
                "runner",
                {
                    "prompt": user_prompt,
                    "provider": self.config.get("provider", "custom"),
                    "command": cmd,
                    "config_file": str(CONFIG_FILE),
                },
            )
            self.codex_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            self.codex_process.wait()
            GLib.idle_add(self.set_status, "Ready")
            GLib.idle_add(self.set_prompt_text, "")
        except Exception as err:
            GLib.idle_add(self.set_status, f"Failed: {err}")
            append_log(
                "runner-error",
                {
                    "prompt": user_prompt,
                    "provider": self.config.get("provider", "custom"),
                    "command": cmd,
                    "error": str(err),
                    "config_file": str(CONFIG_FILE),
                },
            )
        finally:
            self.codex_process = None


class SystemAgentApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.window = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.hold()

    def do_activate(self):
        if self.window is None:
            self.window = SystemAgentWindow(self)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        background = "--background" in args
        show = "--show" in args
        voice = "--voice-start" in args
        voice_stop = "--voice-stop-submit" in args

        if self.window is None:
            self.window = SystemAgentWindow(self)

        if show or (not background and not voice and not voice_stop):
            self.window.present_text_overlay()
        elif voice:
            self.window.present_voice_overlay()
        elif voice_stop:
            self.window.stop_recording(submit=True)
        return 0


def read_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def write_state(data):
    STATE_FILE.write_text(json.dumps(data))


def handle_tap_trigger():
    state = read_state()
    now = time.time()
    last_hold = state.get("last_hold", 0)
    if now - last_hold < HOLD_GUARD_WINDOW:
        state["last_tap"] = 0
        write_state(state)
        return 0

    last_tap = state.get("last_tap", 0)
    if now - last_tap < DOUBLE_TAP_WINDOW:
        state["last_tap"] = 0
        write_state(state)
        subprocess.run([str(ROOT / "system-agent"), "--show"], check=False)
        return 0

    state["last_tap"] = now
    write_state(state)
    return 0


def handle_voice_trigger_start():
    state = read_state()
    state["last_hold"] = time.time()
    write_state(state)
    subprocess.run([str(ROOT / "system-agent"), "--voice-start"], check=False)
    return 0


def handle_voice_trigger_stop():
    subprocess.run([str(ROOT / "system-agent"), "--voice-stop-submit"], check=False)
    return 0


def main():
    args = os.sys.argv[1:]
    ensure_config()
    if "--init-config" in args:
        print(CONFIG_FILE)
        raise SystemExit(0)
    if "--list-providers" in args:
        for name in list_provider_names():
            print(name)
        raise SystemExit(0)
    if "--set-provider" in args:
        try:
            name = args[args.index("--set-provider") + 1]
        except Exception:
            raise SystemExit("missing provider name")
        config = set_provider(name)
        print(json.dumps(config, indent=2))
        raise SystemExit(0)
    if "--print-config" in args:
        print(json.dumps(load_config(), indent=2))
        raise SystemExit(0)
    if "--tap" in args:
        raise SystemExit(handle_tap_trigger())
    if "--voice-trigger-start" in args:
        raise SystemExit(handle_voice_trigger_start())
    if "--voice-trigger-stop" in args:
        raise SystemExit(handle_voice_trigger_stop())
    app = SystemAgentApp()
    app.run(None)


if __name__ == "__main__":
    main()
