"""Particle state recovery with explicit unsigned rounding and checked guards."""
from pathlib import Path
import hashlib,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_particle_display_151770c8_match import bound,SDK
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
NAME='func_15176B84';ENTRY=0x15176B84;ROM=0x1A4034;SIZE=620
SOURCE='conker/src/game/generated_1A20A0.c';BUILD='conker/build/game-particle-state-15176b84-screen'
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();OUT=ROOT/BUILD
SELECTED='/* Fade and dispatch an active particle, selecting its state-dependent model. */\nvoid func_15176B84(Particle15175390 *record) {\n    s32 opacity;\n    u32 remainder;\n    f32 height;\n    if (((ModelRow15176B84 *)D_800DDE80)[record->variant][0] == NULL || D_800DDF78[record->variant] == 0) {\n        func_1516972C(record);\n        return;\n    }\n    opacity = record->stateF0;\n    if (record->stateF1 == 0) {\n        if (D_800DDF5C[record->slot] == 0) {\n            record->stateF1 = 1;\n        } else if (opacity != 255) {\n            opacity = (u32)opacity + ((u32)D_800BE9E4 << 2);\n            if (opacity >= 256) { opacity = 255; }\n            record->stateF0 = opacity;\n        }\n    } else {\n        if (opacity == 0) {\n            func_1516972C(record);\n            return;\n        }\n        opacity = (u32)opacity - ((u32)D_800BE9E4 << 2);\n        if (opacity < 0) { opacity = 0; }\n        record->stateF0 = opacity;\n    }\n    D_800DDF68[record->variant] = 1;\n    switch (record->state91) {\n        case 0:\n            if (func_150AD960((s32)D_800CC2D0.x, (s32)D_800CC2D0.z,\n                             (s32)record->position[0], (s32)record->position[2]) < 200) {\n                record->state91 = 2;\n                /* Keep retail rounding before restoring the unsigned magnitude. */\n                remainder = (u32)func_150ADA20() % (u32)record->verticalRange;\n                height = (s32)remainder;\n                if ((s32)remainder < 0) { height += 4294967296.0f; }\n                record->targetHeight = height + record->sourceY;\n                record->model = D_800DDE88[record->variant].model;\n            } else {\n                record->model = D_800DDE84[record->variant].model;\n            }\n            break;\n        case 4:\n            if (record->position[1] < record->groundHeight) {\n                func_1516972C(record);\n                return;\n            }\n            /* fall through */\n        case 2:\n        case 3:\n        default:\n            func_15175958(record);\n            break;\n    }\n}'
EXTRA='typedef struct { u8 retained00[0x14]; f32 x, y, z; } ActorPosition15176B84;\nextern ActorPosition15176B84 D_800CC2D0;\nextern u8 D_800DDF5C[], D_800DDF68[];\ntypedef Gfx *ModelRow15176B84[5];\nextern Model15174BF0 D_800DDE84[];\nvoid func_1516972C(void *);\ns32 func_150AD960(s32, s32, s32, s32);\n'
RAW_SHA256='48c966ca7c378cbbf975486add81e1d23296ca84f1f8c61ddc80f00edfc35be8'
RAW_REFS={20: [('R_MIPS_HI16', 'D_800DDE80')], 44: [('R_MIPS_LO16', 'D_800DDE80')], 24: [('R_MIPS_HI16', 'D_800DDF78')], 64: [('R_MIPS_LO16', 'D_800DDF78')], 76: [('R_MIPS_26', 'func_1516972C')], 116: [('R_MIPS_HI16', 'D_800DDF5C')], 128: [('R_MIPS_LO16', 'D_800DDF5C')], 160: [('R_MIPS_HI16', 'D_800BE9E4')], 164: [('R_MIPS_LO16', 'D_800BE9E4')], 212: [('R_MIPS_26', 'func_1516972C')], 208: [('R_MIPS_HI16', 'D_800BE9E4')], 228: [('R_MIPS_LO16', 'D_800BE9E4')], 260: [('R_MIPS_HI16', 'D_800DDF68')], 268: [('R_MIPS_LO16', 'D_800DDF68')], 320: [('R_MIPS_HI16', 'D_800CC2D0')], 324: [('R_MIPS_LO16', 'D_800CC2D0')], 376: [('R_MIPS_26', 'func_150AD960')], 396: [('R_MIPS_26', 'func_150ADA20')], 468: [('R_MIPS_HI16', 'D_800DDE88')], 504: [('R_MIPS_LO16', 'D_800DDE88')], 520: [('R_MIPS_HI16', 'D_800DDE84')], 540: [('R_MIPS_LO16', 'D_800DDE84')], 576: [('R_MIPS_26', 'func_1516972C')], 592: [('R_MIPS_26', 'func_15175958')]}

WINDOW={436: (1182810272, 1182810784), 440: (73465860, 94568453), 444: (1174409222, 2249064658), 448: (1149325312, 1149337600), 452: (0, 0), 456: (1175064576, 1175474816), 460: (2248999122, 2249064658)}
FIELDS={308: {16: (6, 8)}, 416: {11: (3, 13)}, 420: {16: (3, 13)}, 464: {16: (14, 15)}, 468: {16: (24, 25)}, 472: {16: (13, 14), 11: (16, 18)}, 476: {16: (14, 15), 11: (15, 24)}, 480: {21: (15, 24), 16: (14, 15), 11: (15, 24)}, 484: {11: (16, 18), 6: (18, 4)}, 488: {16: (15, 24), 11: (15, 24)}, 492: {21: (24, 25), 16: (15, 24), 11: (24, 25)}, 496: {16: (0, 4), 11: (18, 10), 6: (4, 6)}, 500: {16: (4, 6)}, 504: {21: (24, 25), 16: (24, 25)}, 512: {16: (24, 25)}, 516: {16: (25, 8)}, 520: {16: (9, 10)}, 524: {16: (25, 8), 11: (8, 9)}, 528: {21: (8, 9), 16: (25, 8), 11: (8, 9)}, 532: {16: (8, 9), 11: (8, 9)}, 536: {21: (9, 10), 16: (8, 9), 11: (9, 10)}, 540: {21: (9, 10), 16: (9, 10)}, 548: {16: (9, 10)}, 552: {16: (6, 8)}, 556: {16: (8, 16)}, 560: {16: (8, 16), 11: (6, 8)}}
def normalize(raw,refs):
    validate(raw,refs);w=list(struct.unpack('>155I',raw));original=w[:]
    # Restore the two-path conversion join and its duplicated signed-halfword
    # load. The symbolic proof checks the complete public events and live model
    # address through the height store for both signs of the remainder.
    for pc,(old,new) in WINDOW.items():assert w[pc//4]==old;w[pc//4]=new
    for pc,changes in FIELDS.items():
        word=original[pc//4];op=word>>26;fmt=word>>21&31
        for shift,(old,new) in changes.items():
            floating_field=(op==17 and fmt in (16,20))or(op==17 and fmt in (0,4)and shift==11)or(op in (49,57)and shift==16)
            if floating_field:assert 0<=old<20 and 0<=new<20
            else:assert old in (*range(1,16),24,25)and new in (*range(1,16),24,25)
            assert w[pc//4]>>shift&31==old
            w[pc//4]=w[pc//4]&~(31<<shift)|new<<shift
    from tools.tests.game_particle_state_15176b84_proof import prove
    prove(original,w)
    return struct.pack('>155I',*w),dict(refs)

def validate(raw,refs):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=RAW_REFS:raise ValueError('Particle state body or named bindings changed')
    words=struct.unpack('>155I',raw);assert words[0]==0x27bdffe0 and words[-4:]==(0x8fb00018,0x27bd0020,0x03e00008,0)

def proposed(before):
    assert body(before,NAME)=='s32 func_15176B84() {\n    return 0;\n}' and before.count('    f32 fieldE0, retainedE4;')==1
    return before.replace(body(before,NAME),SELECTED).replace('    f32 fieldE0, retainedE4;','    f32 fieldE0, targetHeight;').replace('/* Recovered routine',EXTRA+'\n/* Recovered routine',1)

def main():
    OUT.mkdir(parents=True,exist_ok=True);live=(ROOT/SOURCE).read_text();installed='void '+NAME+'(' in live
    before=(OUT/'production-baseline'/SOURCE).read_text()if installed else live;selected=proposed(before);assert not installed or live==selected
    old,d=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,selected,'selected');assert d==d2==''
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);rom=(ROOT/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>155I',rom,ROM));assert bound(normal,nrefs)==truth
    assert same_functions(old,obj,(NAME,))==8 and normalized_pools(old)==normalized_pools(obj)=={'.data':None,'.rodata':None}
    controls=0
    for i in range(155):
        bad=bytearray(raw);bad[i*4+3]^=1
        try:validate(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed source word accepted')
    for pc,rs in refs.items():
        try:validate(raw,{**refs,pc:[(k,n+'_changed')for k,n in rs]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed named binding accepted')
    import csv,io
    original=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(original.decode())));rows=[];rel=lambda rs:';'.join(k+':'+n for k,n in rs)or'-'
    for i,(old,new)in enumerate(zip(struct.unpack('>155I',raw),struct.unpack('>155I',normal))):
        if old!=new:rows.append(dict(filename='generated_1A20A0',function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%old,replacement='0x%08X'%new,expected_relocations=rel(refs.get(i*4,[])),replacement_relocations=rel(refs.get(i*4,[])),note='Restore explicit unsigned height rounding CFG and closed temporary register lifetimes',insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==32
    existing=[r for r in csv.DictReader(io.StringIO(original.decode()))if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n'if b'\r\n'in original else'\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (OUT/'proposed-guards.csv').write_bytes(guards)
    asm=(ROOT/'conker/asm/1A20A0.s').read_text();a=asm.index('glabel '+NAME+'\n');z=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (OUT/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:z]+'\n.size '+NAME+',.-'+NAME+'\n')
    (OUT/'guarded.s').write_text(pg.emit_padded_assembly(obj,ROOT/'conker/asm/1A20A0.s',filename='generated_1A20A0',word_patches_path=OUT/'proposed-guards.csv'))
    for label in ('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(OUT/(label+'.o')),str(OUT/(label+'.s'))],cwd=ROOT/'conker',capture_output=True,check=True)
        assert bound(*payload(OUT/(label+'.o'),NAME))==truth
    frozen=OUT/'production-baseline/conker/build/src/game/generated_1A20A0.c.o';assert same_functions(frozen,OUT/'guarded.o',(NAME,))==8 and normalized_pools(frozen)==normalized_pools(OUT/'guarded.o')
    allwords=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0xc000000|((ENTRY>>2)&0x3ffffff);callers=[i*4 for i,w in enumerate(allwords)if w==jal];pointers=[i*4 for i,w in enumerate(allwords)if w==ENTRY]
    assert not callers and pointers==[0x2303ac,0x2303e0,0x230414,0x230448]
    report=dict(raw_words=155,words=155,frame=32,guards=32,neighbors=8,owner_functions=9,installed=installed,corruption_controls=controls,direct_callers=callers,registry_slots=[0x8008b4a8+p-0x22ff68 for p in pointers],raw_sha256=RAW_SHA256)
    (OUT/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
