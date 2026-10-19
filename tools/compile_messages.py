"""locale/*/LC_MESSAGES/*.po -> .mo (GNU gettext msgfmt o'rnatilmagan muhit uchun, oddiy satrlar; ko'plik shakllarsiz).

Ishlatish: python tools/compile_messages.py
"""

import ast
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_po(text):
    messages, msgid, msgstr, state = {}, None, None, None
    for raw in text.splitlines() + [""]:
        line = raw.strip()
        if line.startswith("msgid "):
            if msgid is not None:
                messages[msgid] = msgstr
            msgid, msgstr, state = ast.literal_eval(line[6:]), "", "id"
        elif line.startswith("msgstr "):
            msgstr, state = ast.literal_eval(line[7:]), "str"
        elif line.startswith('"'):
            if state == "id":
                msgid += ast.literal_eval(line)
            elif state == "str":
                msgstr += ast.literal_eval(line)
        elif not line and msgid is not None:
            messages[msgid] = msgstr
            msgid, state = None, None
    return {k: v for k, v in messages.items() if v or k == ""}


def write_mo(messages, path):
    keys = sorted(messages)
    ids = [k.encode("utf-8") for k in keys]
    strs = [messages[k].encode("utf-8") for k in keys]
    n = len(keys)
    key_start = 7 * 4 + 16 * n
    offsets, data = [], b""
    for s in ids:
        offsets.append((len(s), key_start + len(data)))
        data += s + b"\0"
    val_start = key_start + len(data)
    val_offsets, vdata = [], b""
    for s in strs:
        val_offsets.append((len(s), val_start + len(vdata)))
        vdata += s + b"\0"
    header = struct.pack("Iiiiiii", 0x950412DE, 0, n, 7 * 4, 7 * 4 + 8 * n, 0, 0)
    table = b"".join(struct.pack("ii", *o) for o in offsets) + b"".join(struct.pack("ii", *o) for o in val_offsets)
    path.write_bytes(header + table + data + vdata)


if __name__ == "__main__":
    for po in ROOT.glob("locale/*/LC_MESSAGES/*.po"):
        messages = parse_po(po.read_text(encoding="utf-8"))
        write_mo(messages, po.with_suffix(".mo"))
        print(f"{po.relative_to(ROOT)} -> .mo ({len(messages) - 1} ta tarjima)")
