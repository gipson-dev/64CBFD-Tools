"""Qualify the lazy loader's incoming-result lifetime and reduce its guards."""
import argparse
import csv
import hashlib
import io
import json
import struct
from pathlib import Path

from tools.experiments import game_third_resource_loader_candidates as original

ENTRY,ROM,WORDS=original.ENTRY,original.ROM,original.WORDS
FUNCTION,SOURCE,SYMBOLS=original.FUNCTION,original.SOURCE,original.SYMBOLS
ORIGINAL=original.ORIGINAL
SOURCE_SHA='f580435626504c2fda5ecf8b7fa7a87feaf4d1f2a1332be1118923a6492e5dcb'
GUARDS='conker/retail_word_patches.us.csv'
GUARDS_SHA='92679ed3e2a6439969298cd769daf69d41e9619c81360046094cf34f1ec3faf4'
QUALIFIED='''s32 func_1503D774(s32 identity, s32 loaded) {
    /* Ignore the incoming second word; reuse it as the result and status. */
    s32 output;
    struct124 **slot = &D_800D1C90[identity];

    if (*slot != NULL) {
        return 0;
    }

    loaded = (s32)func_1502B6BC(&output, 2, 0, 2, 0x11, identity);
    if (loaded == 0) {
        *slot = NULL;
        loaded = 2;
        goto done;
    }

    *slot = (struct124 *)loaded;
    *slot = *(struct124 **)loaded;
    loaded = 0;
done:
    return loaded;
}'''
OLD_BLOCK=b'''generated_6A3D0,func_1503D774,0x038,0x10000012,0x10000011,-,-,Adjust already-loaded exit across omitted result copy,,,false
generated_6A3D0,func_1503D774,0x050,0xAFA30020,0xAFA30024,-,-,Normalize lazy-loader result publication schedule,,,false
generated_6A3D0,func_1503D774,0x05C,0x8FA30020,0x14400004,-,-,Normalize lazy-loader result publication schedule,,,false
generated_6A3D0,func_1503D774,0x060,0x14400004,0x8FA30024,-,-,Normalize lazy-loader result publication schedule,,,false
generated_6A3D0,func_1503D774,0x064,0x00402025,0x00402025,-,-,Omit redundant lazy-loader result copy,,,true
generated_6A3D0,func_1503D774,0x074,0xAC640000,0xAC620000,-,-,Normalize lazy-loader result publication register,,,false
generated_6A3D0,func_1503D774,0x078,0x8C8A0000,0x8C4A0000,-,-,Normalize lazy-loader result publication register,,,false
'''
NEW_BLOCK=b'''generated_6A3D0,func_1503D774,0x038,0x10000012,0x10000011,-,-,Adjust lazy-loader cached exit across omitted status copy,,,false
generated_6A3D0,func_1503D774,0x06C,0x24040002,0x24020002,-,-,Normalize lazy-loader shared status to return register,,,false
generated_6A3D0,func_1503D774,0x078,0x00002025,0x00001025,-,-,Normalize lazy-loader shared status to return register,,,false
generated_6A3D0,func_1503D774,0x080,0x00801025,0x00801025,-,-,Omit redundant lazy-loader shared status copy,,,true
'''


def target_rows(data):
    return [row for row in csv.DictReader(io.StringIO(data.decode('ascii')))
        if row['filename']=='generated_6A3D0' and row['function']==FUNCTION]


def install(before):
    if before.count(ORIGINAL)!=1 or hashlib.sha256(before.encode('ascii')).hexdigest()!=SOURCE_SHA:
        raise ValueError('stale third-loader body or owner')
    return before.replace(ORIGINAL,QUALIFIED)


def install_guards(before):
    if hashlib.sha256(before).hexdigest()!=GUARDS_SHA or before.count(OLD_BLOCK)!=1:
        raise ValueError('stale third-loader guard block')
    after=before.replace(OLD_BLOCK,NEW_BLOCK)
    assert len(target_rows(before))==7 and len(target_rows(after))==4
    return after


def require_current_slot(root):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_actor_renderer_install_match import symbol_size_offset
    data=(root/'conker/build/conker.us.elf').read_bytes()
    start=elf_slot_offset(data,ENTRY,144);extent=symbol_size_offset(data,FUNCTION,ENTRY)
    retail=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+144]
    assert data[start:start+144]==retail
    assert struct.unpack_from('>I',data,extent)[0]==144


def historical_source(root):
    source=(root/SOURCE).read_text()
    if ORIGINAL in source: return source
    assert source.count(QUALIFIED)==1
    before=source.replace(QUALIFIED,ORIGINAL)
    assert hashlib.sha256(before.encode('ascii')).hexdigest()==SOURCE_SHA
    assert install(before)==source
    require_current_slot(root)
    return before


def historical_guards(root):
    current=(root/GUARDS).read_bytes()
    if OLD_BLOCK in current: return current
    assert current.count(NEW_BLOCK)==1 and len(target_rows(current))==4
    before=current.replace(NEW_BLOCK,OLD_BLOCK)
    assert hashlib.sha256(before).hexdigest()==GUARDS_SHA
    assert install_guards(before)==current
    assert (root/SOURCE).read_text()==install(historical_source(root))
    require_current_slot(root)
    return before


def compile_candidate(root,out,name,body=QUALIFIED,profile='owner'):
    return original.compile_candidate(root,out,name,body,profile)


def candidates():
    yield 'banked',ORIGINAL
    incoming=ORIGINAL.replace('    void *loaded;\n','').replace('loaded = func_1502B6BC',
        'arg1 = (s32)func_1502B6BC').replace('loaded == 0','arg1 == 0').replace(
        '(struct124 *)loaded','(struct124 *)arg1').replace('*(struct124 **)loaded','*(struct124 **)arg1')
    yield 'incoming-result',incoming
    yield 'incoming-status',QUALIFIED
    yield 'local-status',incoming.replace('    s32 output;','    s32 output;\n    s32 status;').replace(
        '        return 2;','        status = 2;\n        goto done;').replace(
        '    return 0;\n}','    status = 0;\ndone:\n    return status;\n}')
    yield 'inline-result',incoming.replace(
        '    arg1 = (s32)func_1502B6BC(&output, 2, 0, 2, 0x11, arg0);\n    if (arg1 == 0)',
        '    if ((arg1 = (s32)func_1502B6BC(&output, 2, 0, 2, 0x11, arg0)) == 0)')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='incoming-status');parser.add_argument('--profiles',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-third-resource-loader-lifetime';records=[]
    for name,body in candidates():
        if args.filter and args.filter not in name: continue
        for profile in ('owner','retail') if args.profiles else ('owner',):
            meta,words=compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta);print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
