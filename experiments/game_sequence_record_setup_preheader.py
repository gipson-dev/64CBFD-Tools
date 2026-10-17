"""Resolve the second prefill address without reopening the qualified frame fit."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_sequence_record_setup_frame as frame

BUILD = 'conker/build/game-sequence-record-setup-preheader'


def second_expression(body, expression):
    return frame.block_change(body,
        '    D_800C363A[slot] = header->activeCount;',
        '    D_800C35F0[slot]',
        lambda text: frame.change(text, 'bundle[cursor]', expression, 2))


def forms():
    body = frame.PREHEADER
    yield 'unsigned-cursor', frame.change(body, '    s32 cursor;', '    u32 cursor;')
    yield 'second-index', second_expression(body, 'bundle[i + 1]')
    yield 'second-pointer', second_expression(body, '(bundle + 1)[i]')
    yield 'second-byte-base', second_expression(body,
        '((SequenceDescriptor49D30 *)((u8 *)bundle + 8))[i]')
    def steps(text):
        text = frame.change(text, '            cursor++;\n', '')
        return frame.change(text, '; i++) {', '; i++, cursor++) {')
    yield 'second-step-cursor', frame.block_change(body,
        '    D_800C363A[slot] = header->activeCount;', '    D_800C35F0[slot]', steps)
    def post_cursor(text):
        text = frame.change(text, '            cursor++;\n', '')
        return frame.change(text, '= bundle[cursor].data;', '= bundle[cursor++].data;')
    yield 'second-post-cursor', frame.block_change(body,
        '    D_800C363A[slot] = header->activeCount;', '    D_800C35F0[slot]', post_cursor)
    def post_index(text):
        text = frame.change(text, '            cursor++;\n', '')
        text = frame.change(text, 'D_800C3868[slot][i] =', 'D_800C3868[slot][i++] =')
        return frame.change(text, '; i++) {', '; cursor++) {')
    yield 'second-post-index', frame.block_change(body,
        '    D_800C363A[slot] = header->activeCount;', '    D_800C35F0[slot]', post_index)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    for label, body in forms():
        if args.filter and args.filter not in label:
            continue
        row = frame.run(root, root / BUILD, label, body)
        print(json.dumps({key:row[key] for key in ('label','words','frame',
            'differences','raw_sha256','save_words_match','stack_offsets')}), flush=True)
