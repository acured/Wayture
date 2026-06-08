"""
blob_tool.py — Azure Blob Storage 交互式浏览器

用法: python blob_tool.py [container] [prefix]
默认: container=data

操作:
  ↑/↓        选择
  Enter       进入目录
  Backspace   返回上级
  d           下载选中文件到 debug_output/
  q           退出
"""
from __future__ import annotations

import os
import sys
import tty
import termios
from pathlib import Path

STORAGE_ACCOUNT = "wayturestorage"
DEFAULT_CONTAINER = "data"
DOWNLOAD_DIR = Path(__file__).resolve().parent / "debug_output"


def _read_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            seq = sys.stdin.read(2)
            if seq == "[A":
                return "up"
            if seq == "[B":
                return "down"
            return "quit"
        if ch == "\r":
            return "enter"
        if ch == "\x7f" or ch == "\x08":
            return "backspace"
        if ch == "\x03":
            return "quit"
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _fmt_size(n):
    if n < 1024:
        return f"{n} B"
    if n < 1048576:
        return f"{n / 1024:.1f} KB"
    if n < 1073741824:
        return f"{n / 1048576:.1f} MB"
    return f"{n / 1073741824:.1f} GB"


class BlobBrowser:
    def __init__(self, container: str, prefix: str = ""):
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        cred = DefaultAzureCredential()
        svc = BlobServiceClient(
            f"https://{STORAGE_ACCOUNT}.blob.core.windows.net", credential=cred
        )
        self.cc = svc.get_container_client(container)
        self.container = container
        self.prefix = prefix
        self.cur = 0
        self.scroll = 0
        self.items: list[tuple] = []
        self.status = ""

    def _load(self):
        dirs, files = [], []
        for item in self.cc.walk_blobs(
            name_starts_with=self.prefix or None, delimiter="/"
        ):
            if hasattr(item, "size"):
                mt = (
                    item.last_modified.strftime("%m-%d %H:%M")
                    if item.last_modified
                    else ""
                )
                files.append(("file", item.name, item.size, mt, item.last_modified))
            else:
                dirs.append(("dir", item.name, 0, "", None))
        dirs.sort(key=lambda x: x[1])
        files.sort(key=lambda x: (x[4] or ""), reverse=True)
        dirs = [(k, n, s, m) for k, n, s, m, _ in dirs]
        files = [(k, n, s, m) for k, n, s, m, _ in files]
        self.items = dirs + files
        self.cur = 0
        self.scroll = 0
        self.status = f"{len(dirs)} dirs, {len(files)} files"

    def _render(self):
        cols, rows = os.get_terminal_size()
        print("\033[2J\033[H", end="")

        path = self.prefix or "/"
        print(
            f" \033[1;36mBlob Browser\033[0m  "
            f"{self.container}\033[90m:{path}\033[0m"
        )
        print(f"\033[90m{'─' * (cols - 1)}\033[0m")

        if not self.items:
            print("  (empty)")
            print(
                f"\n\033[90m {self.status}  "
                f"[Backspace] back  [q] quit\033[0m",
                end="",
                flush=True,
            )
            return

        usable = rows - 4
        if usable < 1:
            usable = 1
        if self.cur < self.scroll:
            self.scroll = self.cur
        if self.cur >= self.scroll + usable:
            self.scroll = self.cur - usable + 1

        end = min(self.scroll + usable, len(self.items))
        for i in range(self.scroll, end):
            kind, name, size, mt = self.items[i]
            short = name[len(self.prefix):] if self.prefix else name
            if kind == "dir":
                label = f"[DIR] {short}"
                detail = ""
            else:
                label = f"      {short}"
                detail = f"{_fmt_size(size):>10}  {mt}"

            if i == self.cur:
                line = f"> {label}  {detail}".ljust(cols - 1)
                print(f"\033[7m{line}\033[0m")
            else:
                print(f"  {label}  \033[90m{detail}\033[0m")

        pos = f"  {self.cur + 1}/{len(self.items)}" if len(self.items) > usable else ""
        print(
            f"\033[{rows};1H\033[90m {self.status}{pos}"
            f"  [↑↓ Enter Backspace d q]\033[0m",
            end="",
            flush=True,
        )

    def _enter(self):
        if not self.items:
            return
        kind, name, size, mt = self.items[self.cur]
        if kind == "dir":
            self.prefix = name
            self._load()
        else:
            self.status = f"{name}  {_fmt_size(size)}  {mt}"

    def _back(self):
        if not self.prefix:
            return
        parts = self.prefix.rstrip("/").rsplit("/", 1)
        self.prefix = (parts[0] + "/") if len(parts) > 1 else ""
        self._load()

    def _download(self):
        if not self.items:
            return
        kind, name, *_ = self.items[self.cur]
        if kind == "dir":
            self.status = "select a file to download"
            return
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        local = DOWNLOAD_DIR / name.replace("/", "_")
        self.status = f"downloading {name}..."
        self._render()
        try:
            data = self.cc.get_blob_client(name).download_blob().readall()
            local.write_bytes(data)
            self.status = f"saved {local.name} ({_fmt_size(len(data))})"
        except Exception as e:
            self.status = f"download failed: {e}"

    def run(self):
        self._load()
        while True:
            self._render()
            key = _read_key()
            if key in ("q", "quit"):
                print("\033[2J\033[H", end="")
                break
            elif key == "up" and self.cur > 0:
                self.cur -= 1
            elif key == "down" and self.cur < len(self.items) - 1:
                self.cur += 1
            elif key == "enter":
                self._enter()
            elif key == "backspace":
                self._back()
            elif key == "d":
                self._download()


if __name__ == "__main__":
    container = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONTAINER
    prefix = sys.argv[2] if len(sys.argv) > 2 else ""
    BlobBrowser(container, prefix).run()
