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
you configure a key and trigger a screenshot or explicitly run the model test.

## Install and run

1. Download or copy this repository onto your Windows 11 computer. Install
   **64-bit Python 3.12** from [python.org](https://www.python.org/downloads/)
   is recommended; CPython 3.11 through 3.14 are accepted. The Python launcher
   is optional. Setup tries the launcher, `python`/`python3`, and standard
   installation folders. No administrator access is needed to run Screenshotter.
2. Double-click **Setup.cmd**. It creates a local `.venv` and installs the app
   and its dependencies. Installation requires Internet access to PyPI.
3. Create a regular **project API key** in your [OpenAI API account](https://platform.openai.com/api-keys)
   and enable billing if necessary. Double-click **Configure.cmd** and paste
   the key into its masked field. Never put the key in the repository or chat.
   The app first tries **Windows Credential Manager** under `Screenshotter/OpenAI`.
   If that fails, it saves the key as plaintext in
   `%LOCALAPPDATA%\Screenshotter\api_key.txt`, as authorized for this app.
   The success message identifies text-file storage when used.
   Organization admin keys are for administration and cannot be used here.
   **Test key (no generation)** checks authentication and lists models without
   sending screenshots. **Test model (uses API)** explicitly generates a tiny
   test answer with a generated white pixel to check image and effort support;
   it incurs normal API usage, using the selected token budget. Neither test
   captures your desktop. Tests use the key currently typed in the field, or
   the selected saved/environment key if the field is blank. Save after a
   successful test to store the typed key.
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

The default model is **`gpt-6-astra`**, selected to prioritize answer quality,
with **Instant** reasoning (`reasoning.effort: "none"` in the API request),
a **16,384-token total output budget**, and a **300-second network timeout**.
The original concise-answer prompt stays unchanged. The token budget includes
internal reasoning, when enabled, as well as the spoken answer; it does not
instruct the model to produce a long answer. It is a maximum, not a guaranteed
allocation or charge. Instant requests no additional reasoning but does not
guarantee zero latency. The chosen model must support `none` reasoning; this
model-specific setting could not be validated with a live API key here.

The model ID is listed in [OpenAI's official SDK model
definitions](https://github.com/openai/openai-python/blob/main/src/openai/types/shared/chat_model.py).
Your API project must have access to it. This app cannot guarantee which models
your key can use, and the SDK listing alone does not establish comparative
benchmark results. The app reports denied model access instead of silently
switching to another model.

Configure.cmd exposes the model, reasoning effort, token budget (128–32,768),
and timeout (10–900 seconds). Explicit effort levels must be supported by the
selected model; `off` omits the reasoning parameter and uses model defaults
(it does not necessarily disable reasoning). `auto` uses high effort for
GPT-5/6 and o-series reasoning models and omits it for non-reasoning models
such as `gpt-4.1-mini`. Instant also omits it for GPT-4 and GPT-3.5 models,
which do not support reasoning-effort controls.
Quit and restart the app after changing model settings. API keys are reread
for every request, so replacing a saved key no longer requires a restart.
Non-secret settings are in
`%LOCALAPPDATA%\Screenshotter\settings.json`. The exact legacy defaults
(`gpt-4.1-mini`, 600 tokens, 60 seconds) migrate to the new defaults in 0.1.3;
customized settings are preserved. A saved text-file key takes priority, followed
by Credential Manager. `OPENAI_API_KEY` is used only if no saved key is available.
This prevents an old environment variable from overriding the key you enter in
Configure.cmd. Test results identify the key source without displaying its value.

Speech uses an installed Windows SAPI voice and Windows' default audio device.
Check Windows sound settings if muted or routed to headphones. It uses no paid
audio service. Volume follows normal Windows application/system sound controls.

Charges depend on the chosen model, image size, reasoning, and answer length.
The previous mini-model cost estimate does **not** apply to the new default.
Higher reasoning can cost substantially more and take longer, even when the
spoken answer is short. Current pricing could not be checked from the cloud
development environment; verify it for your chosen model before use. Each trigger
sends one image, with no previous conversation. Drag-selecting just the question
reduces unrelated content and often improves legibility. Check [current API
pricing](https://openai.com/api/pricing/) and [prepaid billing
terms](https://help.openai.com/en/articles/8264644-how-can-i-set-up-prepaid-billing)
before adding funds. Set billing controls in your OpenAI project. The output
token limit includes reasoning; it is not a dollar spending cap.

## Data and troubleshooting

- Images are encoded in memory and sent over HTTPS to
  `https://api.openai.com/v1/responses`; screenshots and answers are not written
  to disk by this app. The complete screenshot is transmitted when using `5`.
  The API request sets `store: false`, which does not override OpenAI's other
  applicable retention policies.
- The API key is never included in `settings.json` or logs. Credential Manager
  is tried first; if it fails, the key is stored in the separate plaintext file
  `%LOCALAPPDATA%\Screenshotter\api_key.txt`. If the file already exists, saves
  update it and reads prefer it over an older credential. You can also create
  this UTF-8 file manually with just the API key to use text-file storage directly.
  To remove saved keys, delete that file and remove `Screenshotter/OpenAI` from
  Windows Credential Manager → Windows Credentials → Generic Credentials.
- Tray status shows actionable errors for rejected keys, quota limits, missing
  model access, and connection failures. Logs in
  `%LOCALAPPDATA%\Screenshotter\app.log` contain timestamps and exception types,
  not screenshots, answers, keys, or raw API error bodies.
- **HTTP 401** means authentication failed. Test a regular project key in
  Configure.cmd; admin keys, revoked keys, and incomplete copies cannot work.
  Version 0.1.4 makes saved keys override stale environment variables and rereads
  them for every request. The metadata check needs Models read permission; actual
  requests also need Responses write permission. Model visibility does not prove
  inference permission or image/effort compatibility.
- **HTTP 400** means the request was rejected. Where the API supplies a known
  parameter, the app names it safely. For `reasoning.effort`, Instant's `none`
  value may be unsupported: choose a model supporting it or select a supported
  effort such as Low. Off omits the effort setting and uses the model's own
  defaults; it does not promise no reasoning. The app keeps your preference and
  does not silently downgrade models or change effort. Use **Test model** to
  reproduce this without capturing your screen. Share only the error text,
  never the key.
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
