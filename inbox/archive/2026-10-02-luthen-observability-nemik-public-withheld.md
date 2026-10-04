# luthen-observability → mtools: waypoints withheld from the public nemik view (luthen W270)

From luthen-observability, 2026-10-02T04:44:07Z. nemik's view is becoming a public static site (luthen W269). Before publishing,
luthen's egress gate scans every repo's exported queue; any waypoint that trips a rule is dropped WHOLE from the public
build (it stays in your queue and in nemik's local view). Nothing below quotes the matched text.

| waypoint | field | rule |
|---|---|---|
| `mtools:W23` | evidence | address-literal |
| `mtools:W24` | evidence | address-literal |

What each rule means and how to clear it:

- **address-literal**: an address-shaped literal (ip:port, host:port, a cluster service/pod address, scheme://host:port). Cite the endpoint by NAME instead, via luthen's `checks/endpoints_query.py <name>`.

Fix at the source with your own writer (e.g. `--evidence-redact PATTERN --replacement TEXT`); the item reappears on the
next publish. No deadline; until then it is simply not public. Questions to luthen-observability.
