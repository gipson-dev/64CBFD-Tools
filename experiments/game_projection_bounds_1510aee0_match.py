"""Ordered point projection with checked scheduling, roles and four pipeline NOPs."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
NAME='func_1510AEE0';ENTRY=0x1510AEE0;ROM=0x138390;SIZE=400;BODY_SIZE=388
SOURCE='conker/src/game/generated_137ED0.c';BUILD='conker/build/game-projection-bounds-1510aee0-match'
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();OUT=ROOT/BUILD;SDK={'cosf'}
RAW_SHA256='5e16ac6bf09f1d80c3a699f5b2f61e17b42d1fbf620813804c781226c6f884f5'
SELECTED='''s32 func_1510AEE0(f32 matrix[4][4], f32 x, f32 y, volatile f32 z,
                  f32 nearPlane, f32 farPlane, f32 xScale, f32 yScale,
                  f32 *xResult, f32 *volatile yResult) {
    f32 depth, horizontal, component; volatile f32 vertical;
    depth = matrix[0][2] * x;
    depth += matrix[1][2] * y;
    depth += matrix[2][2] * z;
    depth = -(matrix[3][2] + depth);
    if (depth < nearPlane) return 1;
    if (farPlane < depth) return 1;
    horizontal = matrix[0][0] * x;
    horizontal += matrix[1][0] * y;
    horizontal += matrix[2][0] * z;
    horizontal = fabsf(matrix[3][0] + horizontal) * xScale;
    if (depth < horizontal) return 1;
    component = matrix[0][1] * x;
    component += matrix[1][1] * y;
    component += matrix[2][1] * z;
    vertical = fabsf(matrix[3][1] + component) * yScale;
    if (depth < vertical) return 1;
    if (xResult != 0) *xResult = 1.0f - horizontal / depth;
    xResult = yResult;
    if (xResult != 0) *xResult = 1.0f - vertical / depth;
    return 0;
}'''
LEDGER={'order': [0, 1, 2, 3, 4, 5, 7, 19, 9, 6, 10, 8, 11, 12, 15, 13, 14, 16, 17, 18, 24, 20, 25, 22, 23, 21, 45, 26, 27, 28, 29, 30, 31, 33, 50, 35, 32, 36, 34, 37, 38, 40, 39, 41, 42, 43, 44, 68, 46, 70, 48, 49, 47, 51, 55, 53, 78, 56, 52, 57, 54, 58, 59, 61, 60, 62, 63, 64, 65, 66, 67, None, 69, None, 71, 72, 73, 74, 75, 76, 77, None, 79, 80, 81, 84, 82, 83, 87, 85, 86, None, 88, 89, 90, 91, 92], 'replaced': [96, 200], 'fields': {'20': {'16': [6, 8]}, '28': {'6': [2, 6]}, '36': {'6': [8, 10], '11': [6, 8]}, '24': {'16': [10, 8]}, '40': {'6': [2, 4], '11': [2, 6], '16': [8, 10]}, '32': {'16': [4, 6]}, '44': {'6': [6, 10], '11': [10, 8], '16': [4, 6]}, '48': {'16': [8, 6]}, '60': {'6': [2, 8], '11': [2, 4], '16': [6, 10]}, '52': {'16': [10, 4]}, '56': {'16': [4, 10]}, '64': {'11': [8, 6], '16': [2, 8]}, '72': {'16': [10, 4]}, '84': {'11': [4, 10]}, '124': {'16': [8, 4]}, '132': {'6': [16, 8]}, '140': {'11': [8, 4]}, '144': {'6': [16, 6], '11': [16, 8]}, '136': {'16': [6, 8]}, '148': {'6': [8, 10], '16': [6, 8]}, '152': {'16': [10, 8]}, '160': {'6': [16, 4], '11': [16, 6], '16': [8, 10]}, '156': {'16': [4, 6]}, '164': {'6': [0, 16], '11': [10, 8], '16': [16, 4]}, '168': {'11': [0, 16]}, '172': {'16': [4, 6]}, '188': {'16': [6, 10]}, '204': {'16': [8, 4]}, '212': {'6': [18, 8], '11': [6, 10]}, '224': {'6': [10, 6], '11': [8, 4]}, '228': {'6': [18, 10], '11': [18, 8], '16': [10, 6]}, '216': {'16': [6, 8]}, '232': {'6': [8, 6], '16': [6, 8]}, '236': {'16': [10, 8]}, '244': {'6': [18, 4], '11': [18, 10], '16': [8, 6]}, '240': {'16': [4, 10]}, '248': {'6': [0, 18], '11': [10, 8], '16': [18, 4]}, '252': {'11': [0, 18]}, '256': {'16': [4, 10]}, '300': {'6': [4, 10]}, '308': {'11': [10, 4]}, '316': {'11': [10, 4], '16': [4, 10]}, '336': {'16': [10, 4]}, '348': {'6': [4, 10], '11': [10, 4]}, '352': {'16': [4, 10]}}, 'edges': {'80': [100, 100], '88': [364, 380], '104': [124, 128], '112': [364, 380], '184': [204, 208], '192': [364, 380], '276': [292, 304], '284': [364, 380], '292': [328, 340], '328': [364, 380]}, 'modes': {'80': [17, 2, 17, 0], '184': [17, 2, 17, 0]}, 'raw_words': 93, 'normalized_words': 97, 'inserted_nops': 4}

def bound(raw,refs):
    assert not refs;return list(struct.unpack('>%dI'%(len(raw)//4),raw))

def normalize(raw,refs):
    if len(raw)!=372 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs:raise ValueError('Projection raw instructions or bindings changed')
    # Consume every raw word once. Only the two unreachable duplicate lowering
    # words become NOPs; the four None entries are explicit pipeline NOPs.
    # The ordered symbolic execution below independently checks the closed map.
    assert sorted(i for i in LEDGER['order']if i is not None)==list(range(93))
    assert LEDGER['order'].count(None)==4 and LEDGER['replaced']==[0x60,0xC8]
    a=bound(raw,refs);result=[]
    for i,src in enumerate(LEDGER['order']):
        if src is None:result.append(0);continue
        pc=src*4;w=0 if pc in LEDGER['replaced']else a[src]
        for shift,(old,new)in LEDGER['fields'].get(str(pc),{}).items():
            shift=int(shift);assert w>>shift&31==old;w=w&~(31<<shift)|new<<shift
        if str(pc)in LEDGER['modes']:
            op,rt,no,nr=LEDGER['modes'][str(pc)];assert w>>26==op and w>>16&31==rt;w=w&~(63<<26|31<<16)|no<<26|nr<<16
        if str(pc)in LEDGER['edges']:
            old,dest=LEDGER['edges'][str(pc)];assert pc+4+4*(((a[src]&65535)^32768)-32768)==old;w=w&0xffff0000|((dest-i*4-4)//4&65535)
        result.append(w)
    from tools.tests.game_projection_bounds_1510aee0_proof import prove
    prove(a,result)
    return struct.pack('>97I',*result),{}

def proposed(before):
    assert body(before,NAME)=='s32 func_1510AEE0() {\n    return 0;\n}'
    return before.replace(body(before,NAME),'f32 fabsf(f32);\n#pragma intrinsic (fabsf)\n\n/* Reject points outside the supplied depth and scaled projection bounds. */\n'+SELECTED)

def main():
    OUT.mkdir(parents=True,exist_ok=True);live=(ROOT/SOURCE).read_text();installed='s32 func_1510AEE0(f32 matrix' in live
    before=(OUT/'production-baseline'/SOURCE).read_text()if installed else live;candidate=proposed(before);assert not installed or candidate==live
    old,d=compile_owner(ROOT,OUT,before,'baseline');assert not d
    obj,d=compile_owner(ROOT,OUT,candidate,'selected');assert not d and same_functions(old,obj,(NAME,))==3 and normalized_pools(old)==normalized_pools(obj)
    raw,refs=payload(obj,NAME);normal,_=normalize(raw,refs);rom=(ROOT/'conker/conker.us.bin').read_bytes();assert normal+b'\0'*12==rom[ROM:ROM+SIZE]
    controls=0
    for i in range(93):
        changed=bytearray(raw);changed[i*4+3]^=1
        try:normalize(bytes(changed),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed raw word accepted')
    try:normalize(raw,{0:[('R_MIPS_HI16','wrong')]})
    except ValueError:controls+=1
    else:raise AssertionError('Unexpected binding accepted')
    original=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(original.decode())));ws=bound(normal,{});beforews=bound(raw,{});rows=[];dest=0
    for i,expected in enumerate(beforews):
        replacement=ws[dest];dest+=1;insert=dest<len(ws)and LEDGER['order'][dest]is None
        if insert:assert ws[dest]==0;dest+=1
        if expected!=replacement or insert:rows.append(dict(filename='generated_137ED0',function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',note='Restore ordered projection roles scheduling branch-delay copies and pipeline NOPs',insert_after='0x00000000'if insert else'',insert_after_relocations='',omit='false'))
    assert dest==97 and sum(bool(r['insert_after'])for r in rows)==4
    existing=[r for r in csv.DictReader(io.StringIO(original.decode()))if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n'if b'\r\n'in original else'\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (OUT/'proposed-guards.csv').write_bytes(guards)
    asm=(ROOT/'conker/asm/137ED0.s').read_text();start=asm.index('glabel '+NAME+'\n');end=asm.index('endlabel '+NAME,start)+len('endlabel '+NAME)
    (OUT/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[start:end]+'\n.size '+NAME+',.-'+NAME+'\n.space 12,0\n')
    (OUT/'guarded.s').write_text(pg.emit_padded_assembly(obj,ROOT/'conker/asm/137ED0.s',filename='generated_137ED0',word_patches_path=OUT/'proposed-guards.csv'))
    for label in('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(OUT/(label+'.o')),str(OUT/(label+'.s'))],cwd=ROOT/'conker',capture_output=True,check=True);assert payload(OUT/(label+'.o'),NAME)==(normal,{})
    assert same_functions(OUT/'production-baseline/conker/build/src/game/generated_137ED0.c.o',OUT/'guarded.o',(NAME,))==3
    report=dict(raw_words=93,body_words=97,slot_words=100,frame=16,guards=len(rows),inserted_nops=4,neighbors=3,corruption_controls=controls,installed=installed,raw_sha256=RAW_SHA256)
    (OUT/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
