"""Screen semantic C forms for the ring message writer func_15043BB8."""

import itertools
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler


ENTRY, ROM, WORDS = 0x15043BB8, 0x71068, 59
FUNCTION = "func_15043BB8"
SYMBOLS = {"func_15043A20": 0x15043A20}
RECORD = """typedef struct {
    u8 *ring;
    s32 capacity;
    s32 readCursor;
    s32 writeCursor;
} RingQueue15043BB8;
"""
DECLARATIONS = """s32 func_15043A20(u8 *, s32, s32, u8 *, s32);
"""

SELECTED = """s32 func_15043BB8(RingQueue15043BB8 *queue, u8 *input, s32 length) {
    s32 cursor;

    if (length == 0 || input == 0) {
        return 0;
    }
    length += 4;
    length = (length + 3) & ~3;
    cursor = queue->writeCursor;
    if (cursor < queue->readCursor) {
        if (cursor + length >= queue->readCursor) {
            return 1;
        }
    } else if (cursor + length - queue->capacity >= queue->readCursor) {
        return 1;
    }
    length -= 4;
    cursor = func_15043A20(queue->ring, queue->capacity, cursor,
                          (u8 *)&length, 4);
    cursor = func_15043A20(queue->ring, queue->capacity, cursor,
                          input, length);
    queue->writeCursor = cursor;
    return 0;
}"""

POSITIVE_BODY = """s32 func_15043BB8(RingQueue15043BB8 *queue, u8 *input, s32 length) {
    s32 cursor;

    if (length != 0 && input != 0) {
        length += 4;
        length = (length + 3) & ~3;
        cursor = queue->writeCursor;
        if (cursor < queue->readCursor) {
            if (cursor + length >= queue->readCursor) {
                return 1;
            }
        } else if (cursor + length - queue->capacity >= queue->readCursor) {
            return 1;
        }
        length -= 4;
        cursor = func_15043A20(queue->ring, queue->capacity, cursor,
                              (u8 *)&length, 4);
        cursor = func_15043A20(queue->ring, queue->capacity, cursor,
                              input, length);
        queue->writeCursor = cursor;
    }
    return 0;
}"""


def candidates():
    yield "positive-body", POSITIVE_BODY
    yield "positive-body-unsigned-align", POSITIVE_BODY.replace(
        "length = (length + 3) & ~3;",
        "length = (s32)(((u32)length + 3U) & ~3U);")
    yield "early-return", SELECTED
    yield "unsigned-align", SELECTED.replace(
        "length = (length + 3) & ~3;",
        "length = (s32)(((u32)length + 3U) & ~3U);")
    yield "nested-entry", SELECTED.replace(
        "    if (length == 0 || input == 0) {\n        return 0;\n    }",
        "    if (length != 0) {\n        if (input == 0) {\n            return 0;\n        }\n    } else {\n        return 0;\n    }")
    yield "combined-fit", SELECTED.replace(
        "    if (cursor < queue->readCursor) {\n"
        "        if (cursor + length >= queue->readCursor) {\n"
        "            return 1;\n"
        "        }\n"
        "    } else if (cursor + length - queue->capacity >= queue->readCursor) {\n"
        "        return 1;\n"
        "    }",
        "    if ((cursor < queue->readCursor &&\n"
        "         cursor + length >= queue->readCursor) ||\n"
        "        (cursor >= queue->readCursor &&\n"
        "         cursor + length - queue->capacity >= queue->readCursor)) {\n"
        "        return 1;\n"
        "    }")
    yield "direct-write", SELECTED.replace(
        "    cursor = func_15043A20(queue->ring, queue->capacity, cursor,\n"
        "                          input, length);\n"
        "    queue->writeCursor = cursor;",
        "    queue->writeCursor = func_15043A20(\n"
        "        queue->ring, queue->capacity, cursor, input, length);")
    yield "nested-calls", SELECTED.replace(
        "    cursor = func_15043A20(queue->ring, queue->capacity, cursor,\n"
        "                          (u8 *)&length, 4);\n"
        "    cursor = func_15043A20(queue->ring, queue->capacity, cursor,\n"
        "                          input, length);\n"
        "    queue->writeCursor = cursor;",
        "    queue->writeCursor = func_15043A20(\n"
        "        queue->ring, queue->capacity,\n"
        "        func_15043A20(queue->ring, queue->capacity, cursor,\n"
        "                       (u8 *)&length, 4), input, length);")
    yield "reload-write", SELECTED.replace(
        "    cursor = queue->writeCursor;", "    cursor = queue->writeCursor;").replace(
        "cursor + length", "queue->writeCursor + length")


def compile_candidate(root, output, name, body):
    output.mkdir(parents=True, exist_ok=True)
    with patch.multiple(
            compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        record, words = compiler.compile_candidate(
            root, output, name, body, "o2g3")
    retail = struct.unpack_from(
        ">%dI" % WORDS, (root / "conker/conker.us.bin").read_bytes(), ROM)
    record["differences"] = sum(
        left != right for left, right in
        itertools.zip_longest(words, retail, fillvalue=0))
    return record


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / "conker/build/game-ring-message-send-15043BB8-match"
    records = []
    for name, body in candidates():
        record = compile_candidate(root, output, name, body)
        records.append(record)
        print(name, record["body_words"], hex(record["frame"]),
              record["differences"], flush=True)
    (output / "candidate-measurements.json").write_text(
        json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
