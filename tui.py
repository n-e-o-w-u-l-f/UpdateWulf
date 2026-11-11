"""Small responsive ANSI menu for desktop and phone SSH terminals."""
import contextlib
import os
import secrets
import shutil
import sys


@contextlib.contextmanager
def keyboard():
    if os.name == "nt":
        yield
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            yield
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def key():
    if os.name == "nt":
        import msvcrt
        value = msvcrt.getwch()
        if value in ("\x00", "\xe0"):
            return {"H": "up", "P": "down", "K": "left", "M": "right"}.get(msvcrt.getwch(), "")
        return {"\r": "enter", " ": "space", "\x1b": "exit", "\x03": "exit"}.get(value, value)
    import select
    value = os.read(sys.stdin.fileno(), 1).decode("ascii", "ignore")
    if value == "\x1b":
        sequence = ""
        # Read bytes from the descriptor; TextIO buffering must not consume an
        # arrow suffix before select can see it.
        while select.select([sys.stdin], [], [], 0.08)[0]:
            sequence += os.read(sys.stdin.fileno(), 1).decode("ascii", "ignore")
            if len(sequence) == 2:
                break
        return {"[A": "up", "[B": "down", "[C": "right", "[D": "left"}.get(sequence, "exit")
    return {"\n": "enter", "\r": "enter", " ": "space", "\x03": "exit"}.get(value, value)


def menu(client, config):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise RuntimeError("interactive terminal required; use pc-mesh status/refresh/update over noninteractive SSH")
    fleet = client.request("/fleet")
    nodes = fleet["nodes"]
    selected = {config.get("id")} & {n["id"] for n in nodes}
    cursor, action_index, column, message = 0, 0, 0, ""
    actions = [("refresh", "Status aktualisieren"), ("install", "Pakete aktualisieren"), ("sync", "Git abgleichen")]
    from pc_mesh import fleet_line
    try:
        with keyboard():
            while True:
                width = max(28, shutil.get_terminal_size((80, 24)).columns)
                wide = width >= 78
                lines = ["PC-Mesh - Update Announce", message[:width],
                         "Pfeile: Wahl  SPACE: Auswahl", "ENTER: Start  ESC: Ende", ""]
                labels = []
                for i, node in enumerate(nodes):
                    marker = ">" if column == 0 and i == cursor else " "
                    checked = "X" if node["id"] in selected else " "
                    state = fleet_line(dict(fleet, nodes=[node])).removeprefix("[Updates] ")
                    labels.append("%s [%s] %s" % (marker, checked, state))
                if wide:
                    half = (width - 3) // 2
                    for i in range(max(len(labels), len(actions))):
                        left = labels[i][:half] if i < len(labels) else ""
                        right = ((">" if column == 1 and i == action_index else " ") + " [" + ("X" if i == action_index else " ") + "] " + actions[i][1]) if i < len(actions) else ""
                        lines.append(left.ljust(half) + " | " + right[:half])
                else:
                    lines += [label[:width] for label in labels]
                    lines.append("")
                    lines += [(">" if column == 1 and i == action_index else " ") + " [" + ("X" if i == action_index else " ") + "] " + text for i, (_, text) in enumerate(actions)]
                sys.stdout.write("\x1b[H\x1b[2J" + "\n".join(line[:width] for line in lines) + "\n")
                sys.stdout.flush()
                pressed = key()
                if pressed in ("exit", "q"):
                    return 0
                if pressed in ("left", "right", "\t"):
                    column = 1 - column
                elif pressed in ("up", "down"):
                    move = -1 if pressed == "up" else 1
                    if column == 0:
                        cursor = (cursor + move) % len(nodes)
                    else:
                        action_index = (action_index + move) % len(actions)
                elif pressed == "space" and column == 0:
                    identity = nodes[cursor]["id"]
                    selected.symmetric_difference_update({identity})
                elif pressed == "enter":
                    if not selected:
                        message = "Bitte mindestens ein System auswaehlen."
                        continue
                    try:
                        jobs = [client.request("/control", {"target": identity, "action": actions[action_index][0], "request_id": secrets.token_hex(12)}) for identity in sorted(selected)]
                        message = "%s Auftrag/Auftraege eingereiht." % len(jobs)
                        fleet = client.request("/fleet")
                    except Exception as e:
                        message = str(e)
    finally:
        print("\x1b[0m", end="", flush=True)
