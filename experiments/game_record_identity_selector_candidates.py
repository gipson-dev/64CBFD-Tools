"""Recover the complete record identity selector and its retail restart quirk."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler
from tools.experiments import game_record_index_query_candidates as query

ENTRY, ROM, WORDS = 0x15083DA0, 0xB1250, 27
FUNCTION, SOURCE = 'func_15083DA0', 'conker/src/game/generated_AEB40.c'
ORIGINAL = 's32 func_15083DA0() {\n    return 0;\n}'
RECORD = query.RECORD
DECLARATIONS = query.DECLARATIONS
SYMBOLS = query.SYMBOLS
SELECTED = '''s32 func_15083DA0(void) {
    s32 identity = 1;
    s32 i;

    for (i = 0; i < D_800D2100; i++) {
        if (D_800D20FC[i].identity == identity) {
            identity++;
            i = 0;
        }
    }
    if (identity >= 0x100) {
        identity = 0xFF;
    }
    return identity;
}'''


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD=RECORD,DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        meta,words=compiler.compile_candidate(root,out,name,body,profile)
    meta['frame']=0 if words[0]>>16!=0x27BD else (-words[0])&65535
    return meta,words


def install(before,body=SELECTED):
    block=RECORD+'extern IndexRecord15083E0C *D_800D20FC;\n'
    original=ORIGINAL+'\n\n'+block
    if before.count(original)!=1:
        raise ValueError('stale record identity selector owner')
    return before.replace(original,block+'\n'+body+'\n')


def main():
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-record-identity-selector'; measurements=[]
    for name,body in (('selected',SELECTED),('unsigned-identity',SELECTED.replace('s32 identity','u32 identity')),
            ('restart-minus-one',SELECTED.replace('            i = 0;', '            i = -1;')),
            ('byte-identity',SELECTED.replace('s32 identity','u8 identity'))):
        meta,_=compile_candidate(root,out,name,body); measurements.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(measurements,indent=2)+'\n')


if __name__=='__main__': main()
