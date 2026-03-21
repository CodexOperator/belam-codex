# Observing Belam Live

## Quick Start

```bash
ssh ubuntu@<host>
bash ~/.openclaw/workspace/scripts/observe.sh
```

Or directly if already on the host:

```bash
tmux attach -t belam-observe -r
```

## What You See

The observation terminal shows the codex engine supermap and live operations.
Read-only — you can watch but not interfere.

## Detach

Press `Ctrl+B` then `D` to detach without killing the session.

## Restart the Session

If the session has died:

```bash
bash ~/.openclaw/workspace/scripts/observe_setup.sh
```

## Notes

- The session is named `belam-observe`
- The `-r` flag in `tmux attach` makes it read-only
- The session persists until the machine reboots or it's manually killed
