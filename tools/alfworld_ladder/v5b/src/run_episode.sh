#!/bin/bash
# Measurement command of the ALFWorld ladder for the autonomous lab (domain command-run, mode batch).
# Called from Windows as: wsl.exe -d Ubuntu -e bash <this file> {batch} {out}   ({batch}/{out} are Windows paths).
# Use -e (no shell): with "--" the WSL login shell strips the backslashes of Windows paths.
#
# - Starts the vLLM server if none is up, runs agent.py on the batch, then stops the server IT started
#   (by process group), so the GPU is free again for the lab's GPU gate. A server it did not start is left alone.
# - A detached watchdog stops exactly this run's agent and server (by PID) if this script is killed,
#   e.g. when the lab kills the wsl.exe tree on a timeout or a stop.
# - `timeout` caps the whole batch even if this script is orphaned.
set -u
B=$(wslpath -u "$1") || exit 2; O=$(wslpath -u "$2") || exit 2
[ -f "$B" ] || { echo "batch file not found: $1 -> $B"; exit 2; }
HERE=$(dirname "$(readlink -f "$0")")
cd ~/test-a-feasibility || exit 2
ME=$$
PIDS=/tmp/ladder-run.$ME.pids
: > "$PIDS"
setsid bash -c "while kill -0 $ME 2>/dev/null; do sleep 5; done; while read -r k p; do if [ \"\$k\" = grp ]; then kill -- -\$p; else kill \$p; fi; done < $PIDS 2>/dev/null; rm -f $PIDS" >/dev/null 2>&1 < /dev/null &
SRV=""
up() { curl -s -m 3 http://127.0.0.1:8001/v1/models | grep -q Qwen; }
if ! up; then
  echo "starting vLLM"
  setsid bash "$HERE/vllm_serve.sh" > "$HERE/../data/vllm_last.log" 2>&1 < /dev/null &
  SRV=$!
  echo "grp $SRV" >> "$PIDS"
  ok=0
  for i in $(seq 1 120); do sleep 5; if up; then ok=1; break; fi; kill -0 "$SRV" 2>/dev/null || break; done
  [ $ok = 1 ] || { echo "vLLM did not start (see data/vllm_last.log)"; kill -- -"$SRV" 2>/dev/null; exit 3; }
fi
echo "vLLM up; running $(wc -l < "$B") jobs"
timeout --kill-after=30 "${LADDER_BATCH_TIMEOUT:-43200}" .venv/bin/python "$HERE/agent.py" \
  --batch "$B" --out "$O" --parallel "${LADDER_PARALLEL:-24}" &
AG=$!
echo "pid $AG" >> "$PIDS"
wait "$AG"; rc=$?
if [ -n "$SRV" ]; then
  kill -- -"$SRV" 2>/dev/null
  # wait until the whole server process group is gone, so the GPU is free for the next batch / the lab's gate
  for i in $(seq 1 60); do pgrep -g "$SRV" >/dev/null 2>&1 || break; sleep 1; done
  pgrep -g "$SRV" >/dev/null 2>&1 && { kill -9 -- -"$SRV" 2>/dev/null; sleep 3; }
fi
echo "done rc=$rc results=$(cat "$O" 2>/dev/null | wc -l)"
exit $rc
