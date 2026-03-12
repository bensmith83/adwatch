# Security Policy

## Reporting a Vulnerability

Please report security vulnerabilities through GitHub's private vulnerability reporting:

**https://github.com/bensmith83/adwatch/security/advisories/new**

This keeps the report confidential until a fix is available. Please include steps to reproduce and any relevant details about your environment.

## Known Limitations

### No Authentication on the Dashboard

The web dashboard does not require authentication. By default, it binds to `127.0.0.1` (localhost only), so it is not reachable from other machines on the network.

If you use `--listen-network` or set `ADWATCH_HOST=0.0.0.0`, the dashboard becomes accessible to anyone on your network. Only do this on trusted networks. There is no built-in auth, rate limiting, or TLS.

### BLE is Passive and Read-Only

adwatch performs passive BLE scanning only — it does not connect to, pair with, or transmit to any device. The SQLite database and raw advertisement storage are local to the machine running adwatch.
