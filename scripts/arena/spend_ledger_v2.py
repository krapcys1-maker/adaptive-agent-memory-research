"""Spend ledger, version 2: a cap that refuses whenever it cannot read what was already spent.

Successor of ``scripts/arena/spend_ledger.py``. That file is frozen by experiment manifests
and stays byte-identical; every run that used it keeps it. New paid runs use this module
through ``scripts/flash_only_proxy_v2.py``. It reads version-1 lines, so one ledger file can
carry a budget across both versions.

What version 1 got wrong, and what this version does instead
------------------------------------------------------------
1. **A torn line vanished under a cap scope.** Version 1 replaced an unparseable line by
   ``{"usd": <largest earlier entry>, "torn": True}``, without a ``run_id``, and
   ``scoped_usd()`` counts only entries whose ``run_id`` starts with the scope, so under
   ``--cap-scope`` the torn call counted zero. With $1.00 recorded and a torn $2.50 line,
   ``check(1.9)`` under a $3.00 cap passed. Here any line that cannot be read completely and
   attributed to a run makes every authorisation fail: ``LedgerUnreadable``.
2. **An estimate stood in for a lost cost.** The largest earlier entry is a floor, not an
   upper bound. Here nothing is estimated: an unreadable ledger is a refusal until a person
   has looked at it.
3. **Authorisation was not atomic across processes.** Two proxies on one ledger could both
   pass the last slot before either recorded. Here ``check`` reads the ledger and appends a
   *reservation* under one file lock, and an open reservation counts as spent until
   ``record`` settles it. A process that dies between forwarding and recording leaves its
   reservation counted.
4. **A missing ledger was created silently.** A mistyped path started a budget at zero.
   Here a missing file is a refusal unless the caller asks for a new ledger explicitly.
5. **Unknown usage was priced at zero tokens.** Here a settlement whose usage the caller
   reports as not known (``usage_known`` not ``True``) is charged at least its reservation.

The rule of reading is fail-closed: every non-blank line must be a JSON object that is either
a version-1 record (``run_id`` a non-empty string, ``usd`` a finite non-negative number, no
``event`` key) or a version-2 event (``"v": 2``; ``reserve``, ``settle`` or ``charge``; the
same checks; a settlement names an open reservation of the same run exactly once), and a
non-empty file must end with a newline. Any other content raises ``LedgerUnreadable``, which
is a ``TotalCapReached``: the frozen proxy handler answers it with HTTP 402 and never forwards
the request. The file is never repaired, truncated or rewritten here.

Sums use ``Decimal`` from the decimal text of each amount, so a total does not depend on the
order of float additions.
"""

from __future__ import annotations

import json
import math
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from arena.spend_ledger import TotalCapReached

FORMAT = "spend-ledger-v2"
EVENTS = ("reserve", "settle", "charge")


class LedgerUnreadable(TotalCapReached):
    """The ledger cannot be read completely and attributed; no spend is authorised."""


def _amount(value: Any, where: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise LedgerUnreadable(f"{where}: usd must be a finite non-negative number, got {value!r}")
    return Decimal(repr(value)) if isinstance(value, float) else Decimal(value)


def _text(value: Any, where: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise LedgerUnreadable(f"{where}: {field} must be a non-empty string, got {value!r}")
    return value


class _State:
    """What the lines say: settled costs and open reservations, per run."""

    def __init__(self) -> None:
        self.settled: list[tuple[str, Decimal]] = []          # (run_id, usd) of legacy records, settlements and charges
        self.open: dict[str, tuple[str, Decimal]] = {}         # reservation id -> (run_id, usd)
        self.closed: set[str] = set()
        self.lines = 0

    def costs(self) -> list[tuple[str, Decimal]]:
        return self.settled + list(self.open.values())


def parse(text: str, name: str = "ledger") -> _State:
    """Read a whole ledger text or raise LedgerUnreadable. Pure: no file access."""
    state = _State()
    if text and not text.endswith("\n"):
        raise LedgerUnreadable(f"{name}: the last line has no newline (a torn write); refusing until it is inspected")
    for number, line in enumerate(text.split("\n")[:-1] if text else [], 1):
        if not line.strip():
            continue
        where = f"{name} line {number}"
        try:
            row = json.loads(line)
        except ValueError as error:
            raise LedgerUnreadable(f"{where}: not valid JSON ({error.msg})") from None
        if not isinstance(row, dict):
            raise LedgerUnreadable(f"{where}: not a JSON object")
        state.lines += 1
        if "event" not in row and "v" not in row:                         # a version-1 record
            run = _text(row.get("run_id"), where, "run_id")
            state.settled.append((run, _amount(row.get("usd"), where)))
            continue
        if row.get("v") != 2 or row.get("event") not in EVENTS:
            raise LedgerUnreadable(f"{where}: unknown record format (v={row.get('v')!r}, event={row.get('event')!r})")
        run = _text(row.get("run_id"), where, "run_id")
        usd = _amount(row.get("usd"), where)
        event = row["event"]
        if event == "charge":
            state.settled.append((run, usd))
            continue
        ident = _text(row.get("id"), where, "id")
        if event == "reserve":
            if ident in state.open or ident in state.closed:
                raise LedgerUnreadable(f"{where}: reservation id {ident!r} is used twice")
            state.open[ident] = (run, usd)
            continue
        if ident not in state.open:                                       # settle
            raise LedgerUnreadable(f"{where}: settlement of {ident!r}, which is not an open reservation")
        if state.open[ident][0] != run:
            raise LedgerUnreadable(f"{where}: settlement of {ident!r} under a different run_id")
        del state.open[ident]
        state.closed.add(ident)
        state.settled.append((run, usd))
    return state


class SpendLedgerV2:
    """A shared, append-only, fail-closed spend total with reservations.

    The constructor and every method that reads raise ``LedgerUnreadable`` (a
    ``TotalCapReached``) instead of guessing. ``check(reserve_usd)`` authorises one call
    and writes its reservation; ``record(usd, **detail)`` settles the cheapest open
    reservation of this instance, so that what stays open is never less than what is in
    flight. The attributes ``path``, ``run_id``, ``total_cap_usd`` and ``cap_scope`` and the
    methods ``check``, ``record``, ``total_usd``, ``scoped_usd``, ``by_run`` and ``summary``
    are those that ``arena.provider_proxy.ProxyState`` and the proxy entry points use.
    """

    def __init__(self, path: Path, total_cap_usd: float, run_id: str, cap_scope: str | None = None, *,
                 create: bool = False, lock_timeout_s: float = 10.0) -> None:
        if isinstance(total_cap_usd, bool) or not isinstance(total_cap_usd, (int, float)) \
                or not math.isfinite(total_cap_usd) or total_cap_usd <= 0:
            raise ValueError("total_cap_usd must be a positive finite number; version 2 has no uncapped mode")
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("run_id must be a non-empty string")
        if cap_scope is not None and (not isinstance(cap_scope, str) or not cap_scope):
            raise ValueError("cap_scope must be None or a non-empty string")
        if cap_scope is not None and not run_id.startswith(cap_scope):
            raise ValueError(f"run_id {run_id!r} is outside cap_scope {cap_scope!r}; its own spend would not be counted")
        self.path = Path(path)
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.total_cap_usd = float(total_cap_usd)
        self.run_id = run_id
        self.cap_scope = cap_scope
        self.lock_timeout_s = lock_timeout_s
        self._mine: dict[str, Decimal] = {}                    # open reservations written by this instance
        self._thread_lock = threading.Lock()
        if not self.path.exists():
            if not create:
                raise LedgerUnreadable(f"{self.path} does not exist; pass create=True (--new-ledger) to start a new budget")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._file_lock():
                if not self.path.exists():
                    self.path.touch()
        self._read()                                           # refuse at once, not at the first call

    # ------------------------------------------------------------------ locking and reading

    def _file_lock(self):
        ledger = self

        class _Lock:
            def __enter__(self_inner):
                deadline = time.monotonic() + ledger.lock_timeout_s
                while True:
                    try:
                        handle = os.open(ledger.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    except FileExistsError:
                        if time.monotonic() >= deadline:
                            raise LedgerUnreadable(
                                f"{ledger.lock_path} is held; another process is writing, or one died holding it. "
                                f"Refusing; remove the lock only after checking that no proxy uses this ledger") from None
                        time.sleep(0.01)
                        continue
                    os.write(handle, str(os.getpid()).encode())
                    os.close(handle)
                    return self_inner

            def __exit__(self_inner, *exc):
                try:
                    os.unlink(ledger.lock_path)
                except FileNotFoundError:
                    pass
                return False

        return _Lock()

    def _read_unlocked(self) -> _State:
        try:
            data = self.path.read_bytes()
        except OSError as error:
            raise LedgerUnreadable(f"{self.path}: cannot be read ({error})") from None
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise LedgerUnreadable(f"{self.path}: not UTF-8") from None
        return parse(text, str(self.path))

    def _read(self) -> _State:
        with self._file_lock():
            return self._read_unlocked()

    def _append(self, row: dict[str, Any]) -> None:
        line = json.dumps(row, sort_keys=True, allow_nan=False)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _scoped(self, state: _State) -> Decimal:
        return sum((usd for run, usd in state.costs() if self.cap_scope is None or run.startswith(self.cap_scope)), Decimal(0))

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    # ------------------------------------------------------------------ reading, as in version 1

    def total_usd(self, since_run: str | None = None) -> float:
        costs = self._read().costs()
        return float(round(sum((usd for run, usd in costs if since_run is None or run == since_run), Decimal(0)), 8))

    def scoped_usd(self) -> float:
        """What the cap counts: settled costs plus open reservations of the scope (all runs if unscoped)."""
        return float(round(self._scoped(self._read()), 8))

    def by_run(self) -> dict[str, float]:
        totals: dict[str, Decimal] = {}
        for run, usd in self._read().costs():
            totals[run] = totals.get(run, Decimal(0)) + usd
        return {run: float(round(value, 8)) for run, value in totals.items()}

    def open_reservations(self) -> int:
        return len(self._read().open)

    # ------------------------------------------------------------------ the cap

    def check(self, reserve_usd: float) -> str:
        """Authorise one call or raise TotalCapReached; on success the reservation is already on disk."""
        reserve = _amount(reserve_usd, "reserve_usd")
        with self._thread_lock, self._file_lock():
            spent = self._scoped(self._read_unlocked())
            cap = Decimal(repr(self.total_cap_usd))
            if spent + reserve > cap:
                scope = f"runs matching {self.cap_scope!r}" if self.cap_scope else "all runs"
                raise TotalCapReached(
                    f"${float(spent):.4f} spent or reserved across {scope}; the next call could cost up to "
                    f"${float(reserve):.4f} and the cap for this scope is ${self.total_cap_usd:.2f}. Stopping below it.")
            ident = f"{self.run_id}:{uuid.uuid4().hex}"
            self._append({"v": 2, "event": "reserve", "id": ident, "run_id": self.run_id, "usd": float(reserve),
                          "at": self._now(), "pid": os.getpid()})
            self._mine[ident] = reserve
            return ident

    def record(self, usd: float, **detail: Any) -> None:
        """Settle this instance's cheapest open reservation, or charge directly when none is open.

        A settlement whose usage is not reported as known is charged at least its reservation.
        """
        known = detail.get("usage_known") is True
        try:
            reported = _amount(usd, "usd")
        except LedgerUnreadable:
            reported, known = Decimal(0), False                # an unusable amount is an unknown cost
        extra = {k: v for k, v in detail.items() if k not in {"v", "event", "id", "run_id", "usd", "at"}}
        with self._thread_lock, self._file_lock():
            self._read_unlocked()                              # never append behind a line it cannot read
            if self._mine:
                ident = min(self._mine, key=lambda k: (self._mine[k], k))
                reserved = self._mine.pop(ident)
                charged = reported if known else max(reported, reserved)
                row = {"v": 2, "event": "settle", "id": ident, "run_id": self.run_id, "usd": float(charged),
                       "reported_usd": float(reported), "reserved_usd": float(reserved), "at": self._now(), **extra}
            else:
                row = {"v": 2, "event": "charge", "run_id": self.run_id, "usd": float(reported),
                       "reported_usd": float(reported), "at": self._now(), **extra}
            self._append(row)

    def summary(self) -> dict[str, Any]:
        state = self._read()
        return {
            "format": FORMAT,
            "path": str(self.path),
            "total_usd": float(round(sum((usd for _, usd in state.costs()), Decimal(0)), 8)),
            "scoped_usd": float(round(self._scoped(state), 8)),
            "cap_scope": self.cap_scope,
            "total_cap_usd": self.total_cap_usd,
            "open_reservations": len(state.open),
            "lines": state.lines,
        }
