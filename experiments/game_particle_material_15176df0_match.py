"""Particle material renderer source and declared private-layout/copy normalization."""
from pathlib import Path
import csv,io,json,os,subprocess
from tools import pad_generated_object as pg
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_particle_display_151770c8_match import bound,SDK
from tools.tests.game_owner_pool import normalized_pools
NAME='func_15176DF0';ENTRY=0x15176DF0;ROM=0x1A42A0;SIZE=728;RAW_SIZE=724
SOURCE='conker/src/game/generated_1A20A0.c';BUILD='conker/build/game-particle-material-renderer-15176df0-screen'
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();OUT=ROOT/BUILD
SELECTED='/* Compose and scale the particle matrix, approach its surface shade, and draw. */\nGfx *func_15176DF0(Gfx *commands, Particle15175390 *record, s16 view) {\n    u8 sync;\n    f32 tilt[4][4];\n    f32 matrix[4][4];\n    s32 value;\n    s32 target;\n    s32 color[3];\n    if (D_800DDE80[record->variant * 5] == NULL || D_800DDF78[record->variant] == 0) {\n        return commands;\n    }\n    func_150A8050(matrix, 0.0f, record->heading, 0.0f);\n    func_150A8050(tilt, record->tilt, 0.0f, record->fieldB0);\n    func_150A7A48(tilt, matrix, matrix);\n    matrix[3][0] = record->position[0];\n    matrix[3][1] = record->position[1];\n    matrix[3][2] = record->position[2];\n    matrix[0][0] *= record->scale;\n    matrix[0][1] *= record->scale;\n    matrix[0][2] *= record->scale;\n    matrix[1][0] *= record->scale;\n    matrix[1][1] *= record->scale;\n    matrix[1][2] *= record->scale;\n    matrix[2][0] *= record->scale;\n    matrix[2][1] *= record->scale;\n    matrix[2][2] *= record->scale;\n    guMtxF2L(matrix, (Mtx *)((u8 *)record + D_800BE9C0 * 64 + 16));\n    gSPMatrix(commands++, (u8 *)record + D_800BE9C0 * 64 + 16,\n              G_MTX_MODELVIEW | G_MTX_LOAD | G_MTX_NOPUSH);\n    gSPSegment(commands++, 1, record->model);\n    gDPPipeSync(commands++);\n    value = record->surfaceKind;\n    target = D_800A7170[(record->surfaceFlags >> 5) & 3];\n    if (value != target) {\n        if (value < target) {\n            value = (u32)value + ((u32)D_800BE9E4 << 2);\n            if (value > target) { value = target; }\n        } else {\n            value = (u32)value - ((u32)D_800BE9E4 << 2);\n            if (value < 0) { value = 0; }\n        }\n        record->surfaceKind = value;\n    }\n    color[0] = color[1] = color[2] = value;\n    sync = 0;\n    commands = func_15142FBC(commands, 0x82CA0, 0x504A50, &sync);\n    gDPSetEnvColor(commands++, color[0], color[1], color[2], record->stateF0);\n    gSPDisplayList(commands++, D_800DDE8C[record->variant * 5]);\n    return commands;\n}'
EXTRA='extern s32 D_800DDF78[], D_800BE9E4;\nextern Gfx *D_800DDE8C[];\nvoid func_150A7A48(f32 [4][4], f32 [4][4], f32 [4][4]);\nGfx *func_15142FBC(Gfx *, u32, u32, u8 *);\n'
import hashlib,struct
from collections import Counter
RAW_SHA256='c8c9605fe8db5638f32ca47c83578287e4e4c97b78fd81b6440882eb0de685fd'
RAW_REFS={32: [('R_MIPS_HI16', 'D_800DDE80')], 56: [('R_MIPS_LO16', 'D_800DDE80')], 36: [('R_MIPS_HI16', 'D_800DDF78')], 76: [('R_MIPS_LO16', 'D_800DDF78')], 116: [('R_MIPS_26', 'func_150A8050')], 136: [('R_MIPS_26', 'func_150A8050')], 152: [('R_MIPS_26', 'func_150A7A48')], 168: [('R_MIPS_HI16', 'D_800BE9C0')], 184: [('R_MIPS_LO16', 'D_800BE9C0')], 348: [('R_MIPS_26', 'guMtxF2L')], 372: [('R_MIPS_HI16', 'D_800BE9C0')], 376: [('R_MIPS_LO16', 'D_800BE9C0')], 452: [('R_MIPS_HI16', 'D_800A7170')], 472: [('R_MIPS_LO16', 'D_800A7170')], 504: [('R_MIPS_HI16', 'D_800BE9E4')], 508: [('R_MIPS_LO16', 'D_800BE9E4')], 500: [('R_MIPS_HI16', 'D_800BE9E4')], 540: [('R_MIPS_LO16', 'D_800BE9E4')], 592: [('R_MIPS_26', 'func_15142FBC')], 672: [('R_MIPS_HI16', 'D_800DDE8C')], 696: [('R_MIPS_LO16', 'D_800DDE8C')]}
HOMES={572: (68, 76), 576: (64, 72), 580: (215, 51), 588: (215, 51), 596: (72, 80), 608: (64, 72), 612: (72, 80), 616: (68, 76)}
ORDER=(0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64, 68, 72, 76, 80, 84, 88, 92, 96, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144, 148, 152, 156, 160, 164, 168, 172, 176, 180, 184, 188, 192, 196, 200, 204, 208, 212, 216, 220, 224, 228, 232, 236, 240, 244, 248, 252, 256, 260, 264, 268, 272, 276, 280, 284, 288, 292, 296, 300, 304, 308, 312, 316, 320, 324, 328, 332, 336, 340, 344, 348, 352, 356, 360, 364, 368, 372, 376, 380, 384, 388, 392, 396, 400, 404, 408, 412, 416, 420, 424, 428, 432, 436, 440, 444, 448, 452, 456, 460, 464, 468, 472, 476, 480, 484, 488, 492, 496, 500, 504, 508, 512, 516, 520, 524, 528, 532, 536, 540, 544, 548, 552, 556, 560, 564, -1, 572, 576, 568, 580, 584, 588, 592, 596, 600, 604, 608, 612, 616, 620, 624, 628, 632, 636, 640, 644, 648, 652, 656, 660, 664, 668, 672, 676, 680, 684, 688, 692, 696, 700, 704, 708, 712, 716, 720)
FIELDS={32: {16: (24, 15)}, 36: {16: (9, 25)}, 48: {11: (15, 14)}, 52: {21: (24, 15), 16: (15, 14), 11: (24, 15)}, 56: {21: (24, 15), 16: (24, 15)}, 60: {11: (25, 24)}, 64: {21: (9, 25), 16: (25, 24), 11: (9, 25)}, 68: {21: (24, 15)}, 76: {21: (9, 25), 16: (9, 25)}, 80: {21: (9, 25)}, 168: {16: (10, 9)}, 184: {21: (10, 9), 16: (10, 9)}, 196: {16: (10, 9), 11: (11, 10)}, 200: {16: (11, 10)}, 356: {16: (12, 11)}, 360: {21: (12, 11), 16: (12, 11)}, 368: {16: (12, 11)}, 372: {16: (13, 12)}, 376: {21: (13, 12), 16: (13, 12)}, 388: {16: (13, 12), 11: (14, 13)}, 392: {16: (14, 13), 11: (15, 14)}, 396: {21: (15, 14), 16: (24, 15)}, 400: {16: (24, 15)}, 404: {16: (25, 24)}, 408: {21: (25, 24), 16: (25, 24)}, 412: {16: (25, 24)}, 416: {16: (9, 25)}, 428: {16: (9, 25)}, 432: {16: (10, 9)}, 436: {16: (10, 9)}, 448: {16: (11, 10)}, 460: {16: (11, 10), 11: (12, 11)}, 464: {21: (12, 11), 16: (13, 12)}, 468: {16: (13, 12)}, 500: {16: (24, 15)}, 504: {16: (14, 13)}, 508: {21: (14, 13), 16: (14, 13)}, 512: {16: (14, 13), 11: (15, 14)}, 516: {16: (15, 14)}, 540: {21: (24, 15), 16: (24, 15)}, 544: {16: (24, 15), 11: (25, 24)}, 548: {16: (25, 24)}, 596: {16: (2, 8)}, 600: {16: (9, 25)}, 604: {16: (9, 25)}, 608: {16: (14, 13)}, 612: {16: (10, 9)}, 616: {16: (25, 24)}, 620: {16: (14, 13), 11: (15, 14)}, 624: {21: (10, 9), 16: (11, 10)}, 628: {16: (14, 13)}, 632: {16: (11, 10), 11: (12, 11)}, 636: {21: (25, 24), 16: (9, 25)}, 640: {16: (9, 25), 11: (10, 9)}, 644: {21: (12, 11), 16: (15, 14), 11: (24, 15)}, 648: {21: (24, 15), 16: (10, 9), 11: (11, 10)}, 652: {21: (11, 10), 16: (14, 13), 11: (12, 11)}, 656: {16: (12, 11)}, 660: {16: (15, 14)}, 664: {16: (15, 14)}, 668: {16: (25, 24)}, 672: {16: (10, 15)}, 680: {16: (25, 24), 11: (9, 25)}, 684: {21: (9, 25), 16: (25, 24), 11: (9, 25)}, 688: {16: (9, 25), 11: (24, 25)}, 692: {21: (10, 15), 16: (24, 25), 11: (10, 15)}, 696: {21: (10, 15), 16: (10, 15)}, 700: {16: (10, 15)}}
EDGES={484: 568, 524: 568, 552: 568}
TEMP=set(range(1,16))|{24,25}
def normalize(raw,refs):
    if len(raw)!=724 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=RAW_REFS:raise ValueError('Material renderer source or named bindings changed')
    original=list(struct.unpack('>181I',raw));words=original[:]
    assert words[0]==0x27bdff28 and words[-1]==0x27bd00d8
    assert len(ORDER)==182 and sorted(x for x in ORDER if x>=0)==list(range(0,724,4)) and ORDER.count(-1)==1
    # RGB components and the one-byte sync flag move between disjoint private
    # objects. Both 64-byte matrices, saved registers and frame are unchanged.
    for pc,(old,new) in HOMES.items():
        w=words[pc//4];assert w>>21&31==29 and w&65535==old
        assert w>>26 in (35,43) and (old,new) in ((0x40,0x48),(0x44,0x4c),(0x48,0x50)) or w>>26 in (9,40) and (old,new)==(0xd7,0x33)
        words[pc//4]=w&0xffff0000|new
    for pc,changes in FIELDS.items():
        w=words[pc//4]
        for shift,(old,new) in changes.items():
            assert old in TEMP and new in TEMP and w>>shift&31==old
            w=w&~(31<<shift)|new<<shift
        words[pc//4]=w
    # A full-word blue snapshot is written in the material-call delay slot.
    # Reintroduce the compiler-folded copy, not another data read or operation.
    assert original[0x254//4]==0xafa20048 and FIELDS[0x254][16]==(2,8)
    copy=(2<<21)|(8<<11)|37
    inverse={src:4*i for i,src in enumerate(ORDER) if src>=0};result=[];bindings={}
    assert ORDER[0x238//4]==-1 and set(EDGES)=={0x1e4,0x20c,0x228}
    for i,src in enumerate(ORDER):
        if src<0:result.append(copy);continue
        w=words[src//4];op=w>>26
        if op in (1,4,5,6,7,20,21,22,23):
            target=src+4+4*(((original[src//4]&65535)^32768)-32768)
            w=w&0xffff0000|((EDGES.get(src,inverse[target])-4*i-4)//4&65535)
        result.append(w)
        if src in refs:bindings[4*i]=refs[src]
    assert Counter(r for rows in refs.values() for r in rows)==Counter(r for rows in bindings.values() for r in rows)
    from tools.tests.game_configurable_particle_15175390_normalization_proof import key
    assert Counter(map(key,words))+Counter([key(copy)])==Counter(map(key,result)), 'Non-copy operation inventory changed'
    assert result[0x238//4]==0x00404025 and result[0x258//4]==0xafa80050
    # All shade joins enter the copy; none can enter its straight-line live
    # interval before the blue store in the material-call delay slot.
    targets=set()
    for pc,w in enumerate(result):
        if w>>26 in (1,4,5,6,7,20,21,22,23):targets.add(pc*4+4+4*(((w&65535)^32768)-32768))
    assert not targets.intersection(range(0x23c,0x25c,4))
    return struct.pack('>182I',*result),bindings

def proposed(before):
    assert body(before,NAME)=='s32 func_15176DF0() {\n    return 0;\n}'
    return before.replace(body(before,NAME),SELECTED).replace('/* Recovered routine',EXTRA+'\n/* Recovered routine',1)

def main():
    OUT.mkdir(parents=True,exist_ok=True);live=(ROOT/SOURCE).read_text();installed='Gfx *'+NAME+'(' in live
    before=(OUT/'production-baseline'/SOURCE).read_text() if installed else live
    selected=proposed(before);assert not installed or selected==live
    old,diag=compile_owner(ROOT,OUT,before,'baseline');obj,diag2=compile_owner(ROOT,OUT,selected,'selected');assert diag==diag2==''
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);rom=(ROOT/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>182I',rom,ROM));assert bound(normal,nrefs)==truth
    assert same_functions(old,obj,(NAME,))==8 and normalized_pools(old)==normalized_pools(obj)=={'.rodata':None,'.data':None}
    controls=0
    for i in range(181):
        bad=bytearray(raw);bad[i*4+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed raw word accepted')
    for pc,rows in refs.items():
        try:normalize(raw,{**refs,pc:[(k,n+'_changed') for k,n in rows]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed named binding accepted')
    original=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));rows=[];rel=lambda rs:';'.join(k+':'+n for k,n in rs) or '-'
    normal_words=struct.unpack('>182I',normal)
    for i,a in enumerate(struct.unpack('>181I',raw)):
        dst=i+(i*4>0x234);b=normal_words[dst];insert='0x%08X'%normal_words[0x238//4] if i*4==0x234 else ''
        if a!=b or refs.get(i*4,[])!=nrefs.get(dst*4,[]) or insert:
            rows.append(dict(filename='generated_1A20A0',function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=rel(refs.get(i*4,[])),replacement_relocations=rel(nrefs.get(dst*4,[])),note='Restore particle material private colors sync home temporary allocation and folded blue copy',insert_after=insert,insert_after_relocations='-' if insert else '',omit='false'))
    assert sum(bool(r['insert_after']) for r in rows)==1
    existing=[r for r in csv.DictReader(io.StringIO(original.decode())) if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (OUT/'proposed-guards.csv').write_bytes(guards)
    asm=(ROOT/'conker/asm/1A20A0.s').read_text();a=asm.index('glabel '+NAME+'\n');z=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (OUT/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:z]+'\n.size '+NAME+',.-'+NAME+'\n')
    (OUT/'guarded.s').write_text(pg.emit_padded_assembly(obj,ROOT/'conker/asm/1A20A0.s',filename='generated_1A20A0',word_patches_path=OUT/'proposed-guards.csv'))
    for label in ('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(OUT/(label+'.o')),str(OUT/(label+'.s'))],cwd=ROOT/'conker',capture_output=True,check=True)
        assert bound(*payload(OUT/(label+'.o'),NAME))==truth
    allwords=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0x0c000000|((ENTRY>>2)&0x3ffffff);callers=[i*4 for i,w in enumerate(allwords) if w==jal];pointers=[i*4 for i,w in enumerate(allwords) if w==ENTRY]
    assert callers==[0x1a46e8] and pointers==[0x230178,0x230380,0x2303b4,0x2303e8,0x23041c,0x230450,0x230d40,0x230d74]
    report=dict(raw_words=181,words=182,frame=216,guards=len(rows),inserted_copy=1,neighbors=8,owner_functions=9,installed=installed,corruption_controls=controls,direct_callers=callers,registry_slots=[0x8008b4a8+p-0x22ff68 for p in pointers],raw_sha256=RAW_SHA256)
    (OUT/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
