"""Particle rise and idle-state recovery with a closed scheduling/return ledger."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_particle_display_151770c8_match import bound,SDK
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
NAME='func_1517685C';ENTRY=0x1517685C;ROM=0x1A3D0C;SIZE=808
SOURCE='conker/src/game/generated_1A20A0.c';BUILD='conker/build/game-particle-rise-1517685c-screen'
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();OUT=ROOT/BUILD
SELECTED='/* Start a nearby particle rising, idle its tilt, and steer it toward its target height. */\nvoid func_1517685C(Particle15175390 *record) {\n    s32 choice;\n    if (D_800DDF5C[record->slot] != 0) {\n        D_800DDF68[record->variant] = 1;\n        switch (record->state91) {\n            case 0:\n                if (func_150AD960((s32)D_800CC2D0.x, (s32)D_800CC2D0.z,\n                                 (s32)record->position[0], (s32)record->position[2]) < 400) {\n                    record->state91 = 1;\n                    record->fieldB4 = -1 - (func_150ADA20() & 3);\n                    record->tilt = -8.0f;\n                } else {\n                    if (record->tiltStep != 0.0f) {\n                        record->tilt += record->tiltStep;\n                        if (record->tiltStep < 0) {\n                            record->heading += record->angularRate;\n                        }\n                        if (record->tilt > 45.0f) {\n                            record->tiltStep = -5.0f;\n                        } else if (record->tiltStep < 0 && record->tilt > 25.0f) {\n                            if ((func_150ADA20() & 255) < 51) { record->tiltStep = 5.0f; }\n                        }\n                        if (record->tilt <= 10.0f) { record->tiltStep = 0; }\n                    } else {\n                        choice = func_150ADA20() & 255;\n                        if (choice < 25) {\n                            record->tiltStep = 5.0f;\n                            if (choice < 13) {\n                                record->angularRate = (s32)((u32)func_150ADA20() % 6U) - 3;\n                            } else {\n                                record->angularRate = 0;\n                            }\n                        }\n                    }\n                }\n                break;\n            case 1:\n                if (record->position[1] >= 300.0f + record->groundHeight) {\n                    record->state91 = 2;\n                    record->flags &= ~1;\n                    record->flags |= 4;\n                    record->targetHeight = (func_150ADA20() & 127) + (300.0f + record->groundHeight);\n                }\n                func_15175958(record);\n                break;\n            case 2:\n            case 3:\n            default:\n                if (record->position[1] < record->targetHeight) {\n                    record->fieldB4 = -1.5f;\n                } else if (record->tilt < 0.0f) {\n                    record->fieldB4 = 1.5f;\n                }\n                func_15175958(record);\n                break;\n        }\n    } else {\n        func_1516972C(record);\n    }\n}'
RAW_SHA256='f9a0b87ff7817b19e5d206ff37c857e7357ea789ebc2c0271a55095464467660'
RAW_REFS={20: [('R_MIPS_HI16', 'D_800DDF5C')], 28: [('R_MIPS_LO16', 'D_800DDF5C')], 44: [('R_MIPS_HI16', 'D_800DDF68')], 56: [('R_MIPS_LO16', 'D_800DDF68')], 108: [('R_MIPS_HI16', 'D_800CC2D0')], 112: [('R_MIPS_LO16', 'D_800CC2D0')], 164: [('R_MIPS_26', 'func_150AD960')], 184: [('R_MIPS_26', 'func_150ADA20')], 388: [('R_MIPS_26', 'func_150ADA20')], 464: [('R_MIPS_26', 'func_150ADA20')], 504: [('R_MIPS_26', 'func_150ADA20')], 624: [('R_MIPS_26', 'func_150ADA20')], 668: [('R_MIPS_26', 'func_15175958')], 764: [('R_MIPS_26', 'func_15175958')], 780: [('R_MIPS_26', 'func_1516972C')]}
ORDER=(0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 68, 72, 76, 80, 84, 88, 92, 96, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144, 148, 152, 156, 160, 164, 168, 172, 176, 180, 184, 188, 192, 196, 200, 204, 208, 212, 216, 220, 224, 228, 236, 240, 232, 244, 248, 252, 256, 264, 272, 268, 280, 276, 284, 288, 292, 296, 300, 304, 308, 312, 316, 320, 324, 328, 332, 336, 340, 260, 344, 348, 352, 356, 360, 364, 368, 372, 376, 380, 384, 388, 392, 396, 404, 400, 408, 412, 416, 420, 424, 428, 432, 436, 440, 444, 448, 452, 456, 460, 464, 468, 472, 548, 476, 480, 484, 488, 492, 496, 500, 504, 508, 512, 516, 520, 524, 528, 532, 536, 540, 544, 556, 552, 64, 560, 564, 568, 572, 576, 580, 584, 588, 592, 596, 600, 604, 608, 612, 616, 620, 624, 628, 632, 636, 640, 644, 648, 652, 656, 660, 664, 668, 672, 676, 680, 684, 688, 692, 696, 700, 704, 708, 712, 716, 720, 724, 728, 732, 736, 740, 744, 748, 752, 756, 760, 764, 768, 772, 776, 780, 784, 788, 792, 796, 800, 804)
FIELDS={40: {16: (25, 24)}, 48: {16: (24, 3)}, 52: {16: (25, 24)}, 56: {16: (24, 3)}, 76: {16: (1, 3)}, 180: {16: (12, 11)}, 188: {16: (12, 11)}, 192: {16: (13, 12)}, 196: {16: (14, 13)}, 200: {21: (14, 13), 16: (13, 12), 11: (15, 14)}, 204: {16: (15, 14)}, 236: {11: (18, 2)}, 244: {11: (18, 2)}, 264: {16: (4, 18)}, 268: {11: (18, 16)}, 280: {11: (4, 18), 6: (6, 4)}, 288: {16: (6, 4)}, 292: {16: (8, 6)}, 296: {16: (10, 8)}, 300: {16: (10, 8), 11: (8, 6), 6: (16, 10)}, 304: {16: (16, 10)}, 312: {11: (18, 16)}, 324: {16: (6, 4)}, 328: {11: (4, 18)}, 336: {16: (4, 18)}, 340: {16: (6, 4)}, 260: {11: (2, 6)}, 348: {16: (2, 6), 11: (6, 4)}, 396: {16: (24, 15)}, 400: {21: (24, 15)}, 520: {11: (25, 24)}, 524: {21: (25, 24), 16: (8, 25)}, 528: {16: (8, 25)}, 596: {16: (10, 9)}, 600: {16: (9, 8)}, 604: {16: (9, 8)}, 608: {21: (10, 9), 16: (11, 10)}, 612: {16: (11, 10)}, 616: {16: (12, 11)}, 620: {21: (12, 11), 16: (14, 13)}, 628: {16: (14, 13)}, 632: {16: (13, 12)}, 636: {16: (13, 12)}}
REPLACEMENTS={64: (604045313, 2411659292), 452: (0, 2411659292)}
EDGES={176: (232, 228), 320: (344, 336), 448: (788, 792), 496: (548, 548), 552: (788, 792)}
BRANCH_MODES={448: (0, 2)}

def validate(raw,refs):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=RAW_REFS:raise ValueError('Particle rise raw words or named bindings changed')

def normalize(raw,refs):
    validate(raw,refs);words=list(struct.unpack('>202I',raw));inverse={src:i*4 for i,src in enumerate(ORDER)};result=[];bindings={}
    for i,src in enumerate(ORDER):
        w=words[src//4]
        if src in REPLACEMENTS:assert w==REPLACEMENTS[src][0];w=REPLACEMENTS[src][1]
        op=w>>26;fmt=w>>21&31
        for shift,(old,new)in FIELDS.get(src,{}).items():
            fp=(op==17 and fmt in(16,20))or(op==17 and fmt in(0,4)and shift==11)or(op in(49,57)and shift==16)
            if fp:assert 0<=old<20 and 0<=new<20
            else:assert old in(*range(1,16),24,25)and new in(*range(1,16),24,25)
            assert w>>shift&31==old;w=w&~(31<<shift)|new<<shift
        if src in BRANCH_MODES:
            old,new=BRANCH_MODES[src];assert(old,new)==(0,2)and w>>16&31==old;w=w&~(31<<16)|new<<16
        op=w>>26
        if op in(1,4,5,6,7,20,21,22,23)or(op==17 and w>>21&31==8):
            target=src+4+4*(((words[src//4]&65535)^32768)-32768)
            if src in EDGES:assert target==EDGES[src][0];dest=EDGES[src][1]
            else:dest=inverse[target]
            w=w&0xffff0000|((dest-i*4-4)//4&65535)
        result.append(w)
        if src in refs:bindings[i*4]=refs[src]
    from tools.tests.game_particle_rise_1517685c_proof import prove
    prove(words,result,ORDER,refs,bindings)
    return struct.pack('>202I',*result),bindings

def proposed(before):
    assert body(before,NAME)=='s32 func_1517685C() {\n    return 0;\n}'and before.count('    f32 groundHeight, retainedCC;')==1
    return before.replace(body(before,NAME),SELECTED).replace('    f32 groundHeight, retainedCC;','    f32 groundHeight, tiltStep;')

def main():
    OUT.mkdir(parents=True,exist_ok=True);live=(ROOT/SOURCE).read_text();installed='void '+NAME+'(' in live
    before=(OUT/'production-baseline'/SOURCE).read_text()if installed else live;selected=proposed(before);assert not installed or selected==live
    old,d=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,selected,'selected');assert d==d2==''
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);rom=(ROOT/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>202I',rom,ROM));assert bound(normal,nrefs)==truth
    assert same_functions(old,obj,(NAME,))==8 and normalized_pools(old)==normalized_pools(obj)=={'.data':None,'.rodata':None}
    controls=0
    for i in range(202):
        bad=bytearray(raw);bad[i*4+3]^=1
        try:validate(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed word accepted')
    for pc,rows in refs.items():
        try:validate(raw,{**refs,pc:[(k,n+'_changed')for k,n in rows]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed binding accepted')
    original=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(original.decode())));rows=[];rel=lambda rs:';'.join(k+':'+n for k,n in rs)or'-'
    for i,(a,b)in enumerate(zip(struct.unpack('>202I',raw),struct.unpack('>202I',normal))):
        if a!=b or refs.get(i*4,[])!=nrefs.get(i*4,[]):rows.append(dict(filename='generated_1A20A0',function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=rel(refs.get(i*4,[])),replacement_relocations=rel(nrefs.get(i*4,[])),note='Restore particle rise closed scheduling allocation constant reuse and return paths',insert_after='',insert_after_relocations='',omit='false'))
    existing=[r for r in csv.DictReader(io.StringIO(original.decode()))if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n'if b'\r\n'in original else'\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (OUT/'proposed-guards.csv').write_bytes(guards)
    asm=(ROOT/'conker/asm/1A20A0.s').read_text();a=asm.index('glabel '+NAME+'\n');z=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (OUT/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:z]+'\n.size '+NAME+',.-'+NAME+'\n')
    (OUT/'guarded.s').write_text(pg.emit_padded_assembly(obj,ROOT/'conker/asm/1A20A0.s',filename='generated_1A20A0',word_patches_path=OUT/'proposed-guards.csv'))
    for label in('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(OUT/(label+'.o')),str(OUT/(label+'.s'))],cwd=ROOT/'conker',capture_output=True,check=True);assert bound(*payload(OUT/(label+'.o'),NAME))==truth
    frozen=OUT/'production-baseline/conker/build/src/game/generated_1A20A0.c.o';assert same_functions(frozen,OUT/'guarded.o',(NAME,))==8
    allwords=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0xc000000|((ENTRY>>2)&0x3ffffff);callers=[i*4 for i,w in enumerate(allwords)if w==jal];pointers=[i*4 for i,w in enumerate(allwords)if w==ENTRY];assert not callers and pointers==[0x230344]
    report=dict(raw_words=202,words=202,frame=32,guards=len(rows),neighbors=8,owner_functions=9,installed=installed,corruption_controls=controls,direct_callers=callers,registry_slots=[0x8008b884],raw_sha256=RAW_SHA256)
    (OUT/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
