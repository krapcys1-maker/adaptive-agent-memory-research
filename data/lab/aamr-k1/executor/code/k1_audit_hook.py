"""K1 v0.4 (W2, D11): audit hook for every process that builds stimuli or runs episodes. Proposed implementation, used by the tests.

Must be installed as the first statement of the process, before any harness import (install() refuses otherwise):

    import k1_audit_hook; k1_audit_hook.install(...)

Policy (all paths absolute; compared after abspath + normcase):
  read_files    exact data files the process may open for reading (each with sha256 frozen in L8)
  code_roots    directories whose code files (.py .pyc .pyd .dll) may be opened (Python install, harness scripts, BFCL package)
  run_dirs      directories the process may write to and read back (own records, response cache); never the checker's dir
  spawn_allow   programs the process may start with any arguments (only the user's Ollama app, restarted by the NIGHT gateway)
  spawn_exact   full command lines the process may start (the supervisor's worker command)
  net_allow     (host, port) pairs the process may connect to (the local Ollama server)

Stopped (one line "K1-AUDIT-VIOLATION: ..." on stderr, then os._exit(97), so the error cannot be caught):
  - opening any other file for reading, or any file for writing outside run_dirs;
  - copying, linking, symlinking or renaming a file unless the source is readable under the policy and the target is in
    run_dirs (otherwise a copy or hard link of the answers inside run_dirs would become readable);
  - starting any other process: subprocess, os.system, os.spawn*, os.startfile, multiprocessing / _winapi.CreateProcess;
  - any network connection or datagram outside net_allow;
  - loading a native library through ctypes other than kernel32 (ctypes itself loads kernel32 on import), or looking up
    by name a kernel32 function that opens files, starts processes or loads libraries (ctypes.dlsym; a foreign call
    itself raises no audit event on CPython 3.12, so the lookup is the only point of control).
mode="log" records instead of stopping (used to derive the allowlist and the event census of a legal run).

Threat model: accidental access to ground truth by K1 code or by an imported harness function, in the process that
builds prompts. Not a sandbox against deliberately hostile code. Code that runs at interpreter start-up before the hook
(site, .pth files, sitecustomize) is outside the hook; its files are hashed in L8 instead.
"""
from __future__ import annotations

import os
import sys

CODE_EXT = (".py", ".pyc", ".pyd", ".dll")
SPAWN_EVENTS = ("subprocess.Popen", "_winapi.CreateProcess", "os.system", "os.exec", "os.posix_spawn", "os.spawn",
                "os.startfile", "os.fork", "os.forkpty", "pty.spawn")
COPY_EVENTS = ("shutil.copyfile", "_winapi.CopyFile2", "os.link", "os.symlink", "os.rename", "shutil.copytree", "shutil.move")
NET_EVENTS = ("socket.connect", "socket.sendto", "socket.sendmsg")
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
VIOLATION_EXIT = 97
HARNESS_MODULES = ("experience_pilot_v0", "experience_xfer_v1", "aamr_night1", "aamr_night2", "bfcl_eval")
INSTALLED = False


def _norm(p) -> str:
    if isinstance(p, bytes):
        p = os.fsdecode(p)
    return os.path.normcase(os.path.abspath(os.fspath(p)))


def _program(cmd: str) -> str:
    """First token of a command line. On Windows the Popen audit event carries one string (list2cmdline), with the
    program quoted when its path has spaces (e.g. "...\\Ollama\\ollama app.exe")."""
    cmd = cmd.strip()
    if cmd.startswith('"'):
        end = cmd.find('"', 1)
        return cmd[1:end] if end > 0 else cmd[1:]
    return cmd.split()[0] if cmd else cmd


def _host(h) -> str:
    h = str(h).lower()
    return "127.0.0.1" if h in ("localhost", "127.0.0.1") else ("::1" if h in ("::1", "0:0:0:0:0:0:0:1") else h)


DLOPEN_ALLOW = ("kernel32",)          # ctypes/__init__.py loads kernel32 on import (GetLastError); nothing else is allowed
DENY_K32 = ("CreateProcessA", "CreateProcessW", "CreateFileA", "CreateFileW", "CreateFile2", "OpenFile", "_lopen", "_lcreat",
            "CopyFileA", "CopyFileW", "CopyFileExA", "CopyFileExW", "CopyFile2", "MoveFileA", "MoveFileW", "MoveFileExA", "MoveFileExW",
            "CreateHardLinkA", "CreateHardLinkW", "CreateSymbolicLinkA", "CreateSymbolicLinkW", "WinExec", "LoadLibraryA",
            "LoadLibraryW", "LoadLibraryExA", "LoadLibraryExW", "GetProcAddress", "ReplaceFileA", "ReplaceFileW")


def install(read_files=(), code_roots=(), run_dirs=(), spawn_allow=(), spawn_exact=(), net_allow=(), mode="enforce", log=None,
            census=None):
    global INSTALLED
    early = [m for m in HARNESS_MODULES if m in sys.modules]
    if early:
        raise RuntimeError("audit hook installed after harness import: " + ", ".join(early))
    rf = frozenset(_norm(p) for p in read_files)
    cr = tuple(_norm(p).rstrip("\\/") + os.sep for p in code_roots)
    rd = tuple(_norm(p).rstrip("\\/") + os.sep for p in run_dirs)
    sa = frozenset(_norm(p) for p in spawn_allow)
    se = frozenset(" ".join(str(c).split()) for c in spawn_exact)
    na = frozenset((_host(h), int(p)) for h, p in net_allow)
    if mode not in ("enforce", "log"):
        raise ValueError(mode)
    if mode == "log" and log is None:
        raise ValueError("log mode needs a list")
    pending = [0]          # CreateProcess calls admitted by a preceding allowed subprocess.Popen (its own payload is unreliable)

    def violation(msg):
        if mode == "log":
            log.append("VIOLATION " + msg)
            return
        os.write(2, ("K1-AUDIT-VIOLATION: " + msg + "\n").encode("utf-8", "replace"))
        os._exit(VIOLATION_EXIT)

    def readable(p: str) -> bool:
        return p in rf or p.startswith(rd) or (p.startswith(cr) and p.endswith(CODE_EXT))

    def spawn_ok(prog, cmdline) -> bool:
        if cmdline is not None and " ".join(str(cmdline).split()) in se:
            return True
        return prog is not None and _norm(prog) in sa

    def hook(event, args):
        if census is not None:
            census[event] = census.get(event, 0) + 1
        if event == "open":
            path, m, flags = args
            if path is None or isinstance(path, int):
                return
            p = _norm(path)
            write = (any(c in m for c in "wax+") if isinstance(m, str) else bool((flags or 0) & WRITE_FLAGS))
            if write:
                if not p.startswith(rd):
                    violation("write " + p)
                return
            if readable(p):
                if mode == "log" and not p.endswith(CODE_EXT):
                    log.append("read-allowed " + p)
                return
            violation("read " + p)
        elif event in COPY_EVENTS:
            src, dst = args[0], args[1]
            if not (isinstance(src, (str, bytes, os.PathLike)) and isinstance(dst, (str, bytes, os.PathLike))):
                violation(f"{event} {src!r} -> {dst!r}")
                return
            s, d = _norm(src), _norm(dst)
            if event == "os.symlink" and not os.path.isabs(os.fspath(src) if not isinstance(src, bytes) else os.fsdecode(src)):
                s = _norm(os.path.join(os.path.dirname(d), os.fspath(src)))
            if not (readable(s) and d.startswith(rd)):
                violation(f"{event} {s} -> {d}")
        elif event == "_winapi.CreateProcess":
            # On CPython 3.12/Windows the payload of this event is not a usable command line (observed: '\x02'), so it
            # is admitted only right after an allowed subprocess.Popen; multiprocessing and direct _winapi use stop.
            if pending[0] > 0:
                pending[0] -= 1
            else:
                violation(f"{event} without an allowed subprocess.Popen")
        elif event in SPAWN_EVENTS:
            prog, cmdline = None, None
            if event == "subprocess.Popen":
                exe, argv = args[0], args[1]
                cmdline = argv if isinstance(argv, str) else (" ".join(map(str, argv)) if isinstance(argv, (list, tuple)) else None)
                prog = exe if exe else (argv[0] if isinstance(argv, (list, tuple)) and argv else (_program(argv) if isinstance(argv, str) else None))
            if isinstance(prog, bytes):
                prog = os.fsdecode(prog)
            if not spawn_ok(prog, cmdline):
                violation(f"{event} {prog!r}")
            elif event == "subprocess.Popen":
                pending[0] += 1
        elif event in NET_EVENTS:
            addr = args[1] if len(args) > 1 else None
            ok = isinstance(addr, tuple) and len(addr) >= 2 and (_host(addr[0]), addr[1]) in na
            if not ok:
                violation(f"{event} {addr!r}")
        elif event == "ctypes.dlopen":
            name = os.path.basename(str(args[0] or "")).lower()
            if name.endswith(".dll"):
                name = name[:-4]
            if name not in DLOPEN_ALLOW:
                violation(f"{event} {args[0]!r}")
        elif event in ("ctypes.dlsym", "ctypes.dlsym/handle"):
            # a foreign-function CALL raises no audit event on CPython 3.12, but looking the function up by name does
            name = args[1] if len(args) > 1 else None
            if isinstance(name, bytes):
                name = name.decode("ascii", "replace")
            if not isinstance(name, str) or name in DENY_K32 or name.rstrip("AW") in {n.rstrip("AW") for n in DENY_K32}:
                violation(f"{event} {name!r} (file, process or library API through ctypes)")

    sys.addaudithook(hook)
    INSTALLED = True
    return hook
