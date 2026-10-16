# Screenshotter for Windows 11

Press **5** to send a screenshot to the OpenAI API and hear the answer through
Windows' default audio output. Press **Shift+5**, then click and drag, to send
only a selected rectangle. The prompt is exactly:

> answer these attached questions accurately and concisely.

Chrome stays in front. Capture and requests do not open windows, draw an overlay,
flash the screen, change the clipboard, or show notifications. Selection uses the
normal mouse cursor with **no visible rectangle**; drag from one corner to the
opposite corner and release. The selection's left-click press and release are
blocked from reaching the app underneath. Normal cursor movement and any hover
effects in the underlying application still occur. The program cannot freeze
animations or prevent other applications from changing their own contents.

This version uses the **OpenAI API**, not the ChatGPT desktop app. Requests do
not appear in your ChatGPT history. No ChatGPT subscription is required; API
billing is separate. The program does not include an API key or spend money until
you configure a key and trigger a screenshot.

## Install and run

1. Download or copy this repository onto your Windows 11 computer. Install
   **64-bit Python 3.12** from [python.org](https://www.python.org/downloads/)
   is recommended; CPython 3.11 through 3.14 are accepted. The Python launcher
   is optional. Setup tries the launcher, `python`/`python3`, and standard
   installation folders. No administrator access is needed to run Screenshotter.
2. Double-click **Setup.cmd**. It creates a local `.venv` and installs the app
   and its dependencies. Installation requires Internet access to PyPI.
3. Create an API key in your [OpenAI API account](https://platform.openai.com/api-keys)
   and enable billing if necessary. Double-click **Configure.cmd** and paste
   the key into its masked field. Never put the key in the repository or chat.
   The key is saved for your Windows user in **Windows Credential Manager** under
   `Screenshotter/OpenAI`.
4. Double-click **Start.cmd**. A small camera icon appears in the system tray
   (possibly under Windows' hidden-icons arrow). You can close the settings
   window and leave Chrome in front. Open the tray menu to see readiness or
   request errors. No console window stays open.
5. Try **Shift+5** on a small test question. Drag from its top-left to its
   bottom-right corner, release, and wait for the spoken answer. Test with
   non-sensitive content first to confirm your intended selection boundaries.

The desktop app does not need to be open. Once started, normal capture and
speech require no interaction with the tray, settings, or another window.
The launcher itself may briefly open a command window when you manually start
the app; hotkey requests do not.

## Controls

| Control | Action |
| --- | --- |
| `5` (top number row) | Capture the complete virtual desktop, including all monitors |
| `Shift+5` | Arm a selection; left-click, drag, and release to capture it |
| `Escape` during selection | Cancel without sending; if dragging, release the mouse to finish cancellation |
| `Ctrl+Alt+P` | Pause/resume screenshot hotkeys |
| `Ctrl+Alt+S` | Stop the answer currently being spoken |
| Tray menu → Quit | Unregister hotkeys, stop speech, and shut down |

**While enabled, 5 and Shift+5 are reserved by the app.** Use Ctrl+Alt+P to
type `5` or `%` normally. The numeric keypad 5 is not bound. Shortcut conflicts
are reported in tray status. Escape is only registered during selection, which
expires after 20 seconds. Screenshots smaller than four pixels on either side
are rejected. Captures while another request or answer is active are ignored;
there is no request backlog and no automatic retry.

Stop speaking only stops audio already playing; it does not cancel a pending
API request. Quit suppresses any later speech. A network request already in
progress must finish or time out before the process exits; it may already be
billable. The timeout applies to network operations, not a guaranteed total
request deadline. Starting a second copy reports that
the app is already running.

## Settings, audio, and costs

The default model is `gpt-4.1-mini`, with a 600-output-token limit and a
60-second network timeout. Configure.cmd allows a different vision-capable
Responses API model and answer limit. Quit and restart the app after saving
changes. For advanced settings, `%LOCALAPPDATA%\Screenshotter\settings.json`
contains the non-secret model, token limit, and timeout (10–180 seconds).
The optional `OPENAI_API_KEY` environment variable overrides a stored key.

Speech uses an installed Windows SAPI voice and Windows' default audio device.
Check Windows sound settings if muted or routed to headphones. It uses no paid
audio service. Volume follows normal Windows application/system sound controls.

Charges depend on the chosen model, image size, and answer length. Each trigger
sends one image, with no previous conversation. Drag-selecting just the question
reduces unrelated content and often improves legibility. Check [current API
pricing](https://openai.com/api/pricing/) and [prepaid billing
terms](https://help.openai.com/en/articles/8264644-how-can-i-set-up-prepaid-billing)
before adding funds. Set billing controls in your OpenAI project. The answer
token limit bounds answer length; it is not a dollar spending cap.

## Data and troubleshooting

- Images are encoded in memory and sent over HTTPS to
  `https://api.openai.com/v1/responses`; screenshots and answers are not written
  to disk by this app. The complete screenshot is transmitted when using `5`.
  The API request sets `store: false`, which does not override OpenAI's other
  applicable retention policies.
- Credentials are not included in settings files or logs. Credential Manager
  protects a saved key for your Windows user; other software running as that
  user may still access it. To remove it, use Windows Credential Manager →
  Windows Credentials → Generic Credentials → `Screenshotter/OpenAI`.
- Tray status shows actionable errors for rejected keys, quota limits, missing
  model access, and connection failures. Logs in
  `%LOCALAPPDATA%\Screenshotter\app.log` contain timestamps and exception types,
  not screenshots, answers, keys, or raw API error bodies.
- If Configure.cmd reports that Windows cannot save credentials, update to
  version 0.1.2 or later and rerun Setup.cmd. Earlier versions passed bytes to
  a Windows credential function that requires text. New versions distinguish
  Credential Manager failures from settings-folder write failures and show
  safe numeric error codes. Saving settings does not contact the API or
  validate your billing or API key online.
- An answer exceeding the token limit is not spoken as if complete. Select fewer
  questions or increase the limit in Configure.cmd. API refusals and empty
  responses also produce an error status.
- Protected video, DRM content, secure desktops, and some fullscreen games may
  not be capturable or accept hotkeys. Use the normal Windows desktop. This app
  does not bypass Windows security or content protection.
- If Setup.cmd cannot find Python, check `python --version` or `py --version`
  in a new terminal. It needs **64-bit CPython 3.11–3.14**; installing the `py`
  launcher is not required. For a custom location, open a terminal in the
  extracted app folder and run `Setup.cmd "D:\YourPython\python.exe"` with the
  actual path. If you previously created a broken or incompatible `.venv`,
  remove only this app's `.venv` folder and run Setup.cmd again. Run the following in a terminal
  to see startup errors if a tray icon never appears:

  ```bat
  .venv\Scripts\python.exe -m screenshotter
  ```

## Development and verification

```sh
python -m venv .venv
# Windows: .venv\Scripts\python.exe -m pip install -e .
# Linux/macOS: .venv/bin/python -m pip install -e .
python -m pip install -e .
python -m unittest discover -s tests -v
```

The automated tests run on Linux with simulated screenshots and a local HTTP
server. They verify real PNG generation, selection coordinates, API request and
response handling, prompt preservation, concurrency, and error recovery. They
do not contact OpenAI or incur API charges.

Windows hotkeys, physical capture, Credential Manager, tray behavior, and SAPI
audio require a Windows machine. The cloud development machine runs Linux;
those integrations and live API access have **not** been validated here.
Before relying on the app, perform these local smoke checks:

1. With Chrome in front, request a known question with 5. Confirm Chrome retains
   focus, no overlay/window appears, and the correct answer plays.
2. Try forward and reverse Shift+5 drags, including a second monitor with
   different DPI scaling. Confirm only the intended region was submitted
   (the automated capture tests cover coordinate math).
3. Cancel a selection with Escape, both before and during a drag. Confirm it
   sends nothing and the underlying page did not receive a click.
4. Pause with Ctrl+Alt+P and confirm normal `5`/`%` typing. Resume, request an
   answer, and stop speech with Ctrl+Alt+S.
5. Disconnect the network, trigger a request, and confirm an error appears in
   tray status without switching focus. Reconnect and try again. Quit and
   restart to verify credentials persist and shortcuts are released.
