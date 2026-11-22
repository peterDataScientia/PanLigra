# PanLigra v1.0.1 — Desktop Window Hotfix

This update fixes the Windows desktop launch experience.

- Removes the visible Command Prompt console from `PanLigra.exe`.
- Opens PanLigra in a standalone Microsoft Edge app-mode window when Edge is available, without a browser address bar.
- Falls back to the default browser if Microsoft Edge is not installed.
- Stores frozen-app startup diagnostics at `%LOCALAPPDATA%\PanLigra\panligra-desktop.log`.
- Retains the scientific workflow, PLIP analysis, Streamlit UI, and Windows installer.

PanLigra still runs a **local-only Streamlit service** on the user's computer; Edge app-mode is the window frontend rather than a native GUI framework. No internet server is required to access the local UI.

The Windows CI build and local server smoke test must succeed before publishing. Manual installation and scientific export acceptance tests on an end-user PC are still recommended.

To update, run the new `PanLigra-Setup.exe`; it installs in the existing per-user PanLigra application directory.
