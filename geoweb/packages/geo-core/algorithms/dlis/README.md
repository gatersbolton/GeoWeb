# dlis

DLIS parsing and visualization service for GeoWeb.

- Reads `.dlis` files through `dlisio`.
- Inspects frames/channels and auto-detects amplitude (振幅), travel-time (走时), and angle candidates.
- Renders ATV-style amplitude/travel-time images plus a rose plot preview, with the amplitude view using inverted black/yellow tone mapping for better contrast.
- Saves preview PNG files and `npz` payloads with unified GeoWeb metadata.
- Designed to be reused by FastAPI routes and the ATV agent.
