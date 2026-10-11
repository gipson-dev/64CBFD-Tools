"""Complete animation-bank scratch preparation, frame selection and PI packets."""
import json
import csv
import io
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x1502D824,0x5ACD4,191
FUNCTION,SOURCE='func_1502D824','conker/src/game/generated_58F80.c'
ORIGINAL='s32 func_1502D824() {\n    return 0;\n}'
DECLARATIONS='''void func_1505DFDC(u8 *);
void func_1000480C(s32, void *, u32);
s32 func_10004514(s32, void *, u32, s32);
'''
SYMBOLS=dict(func_1505DFDC=0x1505DFDC,func_1000480C=0x1000480C,func_10004514=0x10004514)
BASE='''void func_1502D824(u8 *node, u8 *actor, u8 *scratch) {
    s32 banks = 1;
    s32 bank;
    u8 *state;
    u8 *fields;
    s32 length;
    s32 wrap;
    s32 index;
    s32 stride;
    u32 address;
    u32 amount;
    u8 offset;
    f32 frame;
    f32 end;

    if (actor != NULL) {
        if (*(u16 *)(actor + 0x84) == 0xFFFF) {
            func_1505DFDC(actor);
        }
        node = *(u8 **)(actor + 0x2D0);
    }
    if (node != NULL) {
        if (*(s16 *)(node + 0x3C) > 0) {
            banks = 2;
        }
        state = node;
        for (bank = 0; bank != banks; bank++, state += 0x1D0) {
            length = state[0x45];
            fields = node + bank * 4;
            wrap = 0;
            if (length == 0) {
                node[0x38 + bank] = 0;
            } else if (*(u8 **)(fields + 0x28) != NULL) {
                frame = *(f32 *)(fields + 8);
                end = *(f32 *)(fields + 0x18);
                scratch = (u8 *)(((u32)scratch + 15) >> 4 << 4);
                amount = length * 2;
                index = (s32)frame;
                if (end <= (f32)index) {
                    index = (s32)(end - 1.0f);
                }
                stride = state[0x48] + 1;
                if (stride >= 2) {
                    if (end - 1.0f <= (f32)index) {
                        index = (s32)((end - 1.0f + (f32)(stride - 1)) / (f32)stride);
                    } else {
                        index /= stride;
                    }
                }
                address = (u32)*(u8 **)(fields + 0x28) + length * index;
                offset = address & 3;
                address -= offset;
                if (end <= frame + 1.0f) {
                    wrap = 1;
                    amount = length;
                } else {
                    node[0x38 + bank] = length;
                }
                amount += offset;
                *(u8 **)(fields + 0x30) = scratch + offset;
                if (amount < 0xC8U) {
                    func_1000480C(address, scratch, amount);
                } else {
                    func_10004514(address, scratch, (amount + 15) & ~15, 1);
                }
                scratch += amount;
                if (wrap != 0) {
                    address = (u32)*(u8 **)(fields + 0x28);
                    scratch = (u8 *)(((u32)scratch + 15) >> 4 << 4);
                    offset = address & 1;
                    amount = offset + length;
                    address -= offset;
                    if (amount < 0xC8U) {
                        func_1000480C(address, scratch, amount);
                    } else {
                        func_10004514(address, scratch, (amount + 15) & ~15, 1);
                    }
                    node[0x38 + bank] = (u32)(scratch + offset) - (u32)*(u8 **)(fields + 0x30);
                    scratch += amount;
                }
            }
        }
    }
}'''
SELECTED=BASE


def candidates():
    yield 'selected',SELECTED
    yield 'signed-amount',BASE.replace('u32 amount;', 's32 amount;')
    yield 'while-loop',BASE.replace('for (bank = 0; bank != banks; bank++, state += 0x1D0)',
        'for (bank = 0; bank < banks; bank++, state += 0x1D0)')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:raise ValueError('stale animation scratch owner')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+body)


def retire_superseded_submit_guards(before):
    lines=before.splitlines(keepends=True);removed=[]
    expected={0x6C:(0x020A1821,0x020A1021),0x70:(0x8C6B03E8,0x8C4B03E8),0x74:(0x8C6503E0,0x8C4503E0)}
    offsets=set(expected);reader=csv.DictReader(io.StringIO(before.decode('ascii')))
    for row in reader:
        if row['filename']!='generated_6C960' or row['function']!='func_1503F4B0':continue
        offset=int(row['offset'],0)
        if offset not in offsets:continue
        if offset not in expected:raise ValueError('duplicate superseded submit guard')
        if (int(row['expected'],0),int(row['replacement'],0))!=expected.pop(offset):
            raise ValueError('stale transform submit base guard')
        if tuple(row[k] for k in ('expected_relocations','replacement_relocations','insert_after','insert_after_relocations','omit'))!=('-', '-', '', '', 'false'):
            raise ValueError('unexpected transform submit guard operation')
        removed.append(reader.line_num-1)
    if expected or len(removed)!=3:raise ValueError('missing or duplicate superseded submit guards')
    return b''.join(line for i,line in enumerate(lines) if i not in removed)


def main():
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-animation-scratch-prepare';records=[]
    for name,body in candidates():
        meta,_=compile_candidate(root,out,name,body);records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
