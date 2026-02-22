# Smart DNS Switcher

A lightweight Windows tool to automatically select the fastest DNS servers using Python and PyQt6.

## Features

- Monitors a list of public DNS servers and measures ping.
- Automatically sets the two DNS servers with the lowest ping (primary & secondary).
- Detects manual DNS changes and updates status.
- Real-time table showing DNS, ping, and status.
- Optimized for performance with parallel pinging and responsive GUI.

## Tech / Libraries

- Python 3.10+
- [PyQt6](https://pypi.org/project/PyQt6/) for GUI
- `concurrent.futures` for parallel ping
- `subprocess` for PowerShell commands
- `re` for parsing ping results

## How it Works

1. Pings multiple DNS servers in parallel.
2. Chooses the two fastest servers and sets them via PowerShell.
3. Updates a live table in GUI showing ping and status.
4. Monitors DNS for external changes and logs them.

## Installation & Usage

1. Install Python 3.10+ and PyQt6:

```bash
pip install PyQt6
```

2. Run the program as Administrator on Windows:

```bash
python dns_switcher.py
```

3. Click **Start Monitoring** to begin, **Stop Monitoring** to end.

## Notes

- Uses only public, safe DNS servers.
- No private data included.
- Works best on stable Wi-Fi or Ethernet connections.

## License

MIT License

---
Developed by the author with assistance from ChatGPT (OpenAI).