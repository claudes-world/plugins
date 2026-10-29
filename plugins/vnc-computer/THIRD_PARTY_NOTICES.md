# Third-party notices

Nothing is vendored. All code in this plugin is independently written and MIT
licensed (see `LICENSE`):

- The RFB client (`vnclib/rfb.py`) implements the public RFB protocol as
  specified in RFC 6143 and the community RFB specification (rfbproto). Apple
  Remote Desktop authentication (security type 30) follows the publicly
  documented Diffie-Hellman + MD5 + AES-128 exchange. No code was copied from
  any VNC implementation.
- DES and AES-128 (`vnclib/crypto.py`) are written from FIPS 46-3 and FIPS 197
  and are verified against their published test vectors.
- The MCP stdio protocol handling in `server.py` is a minimal independent
  implementation of the Model Context Protocol JSON-RPC messages.

Optional or host-provided software that the plugin uses but does not bundle or
relicense:

- Pillow (MIT-CMU licence), optional, from the system or installed into the
  plugin-local `.venv` by `bin/setup`.
- Xvfb (X.Org, MIT/X11 licence), x11vnc (GPL-2.0) and Google Chrome
  (Google Chrome terms of service), used only by `bin/test-rig` for local
  testing and invoked as separate host programs.
