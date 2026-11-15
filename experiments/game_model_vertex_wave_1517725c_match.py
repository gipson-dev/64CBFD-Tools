"""Model vertex-wave recovery with explicit call-save and private-home normalization."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_particle_display_151770c8_match import bound,SDK
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
NAME='func_1517725C';ENTRY=0x1517725C;ROM=0x1A470C;SIZE=424;RAW_SIZE=416
SOURCE='conker/src/game/generated_1A20A0.c';BUILD='conker/build/game-model-vertex-wave-1517725c-screen'
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();OUT=ROOT/BUILD
SELECTED="/* Animate the selected model's paired vertex arcs and advance its phase. */\nvoid func_1517725C(u8 slot) {\n    VertexWave1517725C *state;\n    Vtx *vertices;\n    f32 angle;\n    f32 sine;\n    f32 cosine;\n    s32 x;\n    s32 y;\n    state = &D_8008D0B0[slot];\n    vertices = D_800DDE88[slot].model;\n    state->wave = func_150AD78C(state->phase * D_800A71AC) * state->amplitude;\n    angle = state->wave * D_800A71B0;\n    sine = func_150AD78C(angle);\n    cosine = func_150AD780(angle);\n    x = (s32)(state->outerRadius * cosine);\n    y = (s32)(state->outerRadius * sine);\n    vertices[10].v.ob[0] = -x;\n    vertices[11].v.ob[0] = -x;\n    vertices[17].v.ob[0] = x;\n    vertices[18].v.ob[0] = x;\n    vertices[17].v.ob[1] = y;\n    vertices[18].v.ob[1] = y;\n    vertices[10].v.ob[1] = y;\n    vertices[11].v.ob[1] = y;\n    state->wave = func_150AD78C((state->phase - 30.0f) * D_800A71B4) * state->amplitude;\n    angle = state->wave * D_800A71B8;\n    sine = func_150AD78C(angle);\n    cosine = func_150AD780(angle);\n    x = (s32)(state->innerRadius * cosine);\n    y = (s32)(state->innerRadius * sine);\n    vertices[14].v.ob[0] = -x;\n    vertices[19].v.ob[0] = x;\n    vertices[14].v.ob[1] = y;\n    vertices[19].v.ob[1] = y;\n    state->phase += state->speed;\n    if (state->phase >= 360.0f) { state->phase -= 360.0f; }\n}"
EXTRA='typedef struct {\n    u8 retained00[0x18];\n    f32 wave, speed, retained20, phase, amplitude, retained2C, outerRadius, innerRadius;\n} VertexWave1517725C;\nextern VertexWave1517725C D_8008D0B0[];\nextern f32 D_800A71AC, D_800A71B0, D_800A71B4, D_800A71B8;\nf32 func_150AD78C(f32);\nf32 func_150AD780(f32);\n'
RAW_SHA256='bba1d95ae2a05651dd5840ce6723b40eb55bf7875584b936c0d8d219c772c576'
RAW_REFS={76: [('R_MIPS_HI16', 'D_800DDE88')], 92: [('R_MIPS_LO16', 'D_800DDE88')], 36: [('R_MIPS_HI16', 'D_8008D0B0')], 40: [('R_MIPS_LO16', 'D_8008D0B0')], 52: [('R_MIPS_HI16', 'D_800A71AC')], 56: [('R_MIPS_LO16', 'D_800A71AC')], 88: [('R_MIPS_26', 'func_150AD78C')], 100: [('R_MIPS_HI16', 'D_800A71B0')], 112: [('R_MIPS_LO16', 'D_800A71B0')], 120: [('R_MIPS_26', 'func_150AD78C')], 132: [('R_MIPS_26', 'func_150AD780')], 172: [('R_MIPS_HI16', 'D_800A71B4')], 228: [('R_MIPS_LO16', 'D_800A71B4')], 240: [('R_MIPS_26', 'func_150AD78C')], 252: [('R_MIPS_HI16', 'D_800A71B8')], 264: [('R_MIPS_LO16', 'D_800A71B8')], 272: [('R_MIPS_26', 'func_150AD78C')], 284: [('R_MIPS_26', 'func_150AD780')]}
REPLACEMENTS={116: (1175065346, 1175065858), 124: (3886809124, 1174446854), 128: (3349938212, 3886022696), 136: (3886022688, 1174446854), 268: (1174934274, 1174934786), 276: (3886809124, 1174446854), 280: (3349938212, 3886022696), 288: (3886022688, 1174446854)}
HOMES={16: (28, 36), 20: (24, 32), 24: (20, 28), 144: (32, 40), 296: (32, 40), 384: (28, 36), 396: (28, 36), 400: (20, 28), 404: (24, 32)}
FIELDS={180: {16: (3, 10)}, 184: {16: (2, 13)}, 188: {16: (3, 10)}, 200: {16: (3, 10)}, 204: {16: (3, 10)}, 208: {16: (2, 13)}, 212: {16: (2, 13)}, 216: {16: (2, 13)}, 220: {16: (2, 13)}, 324: {16: (3, 24)}, 328: {16: (2, 9)}, 332: {16: (3, 24), 11: (12, 10)}, 336: {16: (12, 10)}, 340: {16: (3, 24)}, 344: {16: (2, 9)}, 348: {16: (2, 9)}}

def normalize(raw,refs):
    if len(raw)!=RAW_SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=RAW_REFS:raise ValueError('Vertex wave raw body or named bindings changed')
    w=list(struct.unpack('>104I',raw));assert w[0]==0x27bdffd0 and w[-1]==0x27bd0030
    # The two identical call-save windows carry angle in F20 instead of a
    # private slot. Sine is saved before the cosine call rather than its delay.
    # Both providers receive exactly the same F12. The cosine provider sees
    # the saved sine in both schedules; no public memory access intervenes.
    for base in (0x74,0x10c):
        assert [w[(base+k)//4] for k in (4,16)]==[0x0c000000,0x0c000000]
        assert refs[base+4]==[('R_MIPS_26','func_150AD78C')] and refs[base+16]==[('R_MIPS_26','func_150AD780')]
    for pc,(old,new) in REPLACEMENTS.items():assert w[pc//4]==old;w[pc//4]=new
    for pc,(old,new) in HOMES.items():
        assert w[pc//4]>>21&31==29 and w[pc//4]&65535==old
        w[pc//4]=w[pc//4]&0xffff0000|new
    for pc,changes in FIELDS.items():
        assert not refs.get(pc)
        for shift,(old,new) in changes.items():
            assert old in (2,3,12) and new in (9,10,13,24) and w[pc//4]>>shift&31==old
            w[pc//4]=w[pc//4]&~(31<<shift)|new<<shift
    result=[];bindings={}
    for i,word in enumerate(w):
        if i*4 in refs:bindings[len(result)*4]=refs[i*4]
        result.append(word)
        if i*4==0x18:result.append(0xf7b40010)
        if i*4==0x18c:result.append(0xd7b40010)
    assert len(result)==106 and result[7]==0xf7b40010 and result[0x194//4]==0xd7b40010
    assert result[0x180//4]==0x45020004 and 0x180+4+4*(result[0x180//4]&65535)==0x194
    # The new double save occupies 10..17; GPR saves 1C..27, sine 28..2B.
    assert not set(range(0x10,0x18))&set(range(0x1c,0x2c))
    return struct.pack('>106I',*result),bindings

def proposed(before):
    assert body(before,NAME)=='s32 func_1517725C() {\n    return 0;\n}'
    return before.replace(body(before,NAME),SELECTED).replace('/* Recovered routine',EXTRA+'\n/* Recovered routine',1)

def main():
    OUT.mkdir(parents=True,exist_ok=True);live=(ROOT/SOURCE).read_text();installed='void '+NAME+'(' in live
    before=(OUT/'production-baseline'/SOURCE).read_text() if installed else live
    selected=proposed(before);assert not installed or live==selected
    old,d=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,selected,'selected');assert d==d2==''
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);rom=(ROOT/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>106I',rom,ROM));assert bound(normal,nrefs)==truth
    assert same_functions(old,obj,(NAME,))==8 and normalized_pools(old)==normalized_pools(obj)=={'.data':None,'.rodata':None}
    controls=0
    for i in range(104):
        bad=bytearray(raw);bad[i*4+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed source word accepted')
    for pc,rs in refs.items():
        try:normalize(raw,{**refs,pc:[(k,n+'_changed')for k,n in rs]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed binding accepted')
    original=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));rows=[];nw=struct.unpack('>106I',normal);rel=lambda rs:';'.join(k+':'+n for k,n in rs) or '-'
    for i,a in enumerate(struct.unpack('>104I',raw)):
        pc=4*i;dst=i+(pc>0x18)+(pc>0x18c);b=nw[dst];insert={0x18:0xf7b40010,0x18c:0xd7b40010}.get(pc)
        if a!=b or insert:
            rows.append(dict(filename='generated_1A20A0',function=NAME,offset='0x%X'%pc,expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=rel(refs.get(pc,[])),replacement_relocations=rel(nrefs.get(dst*4,[])),note='Restore model wave saved float lifetime sine home and temporary allocation',insert_after='0x%08X'%insert if insert else '',insert_after_relocations='-'if insert else '',omit='false'))
    existing=[r for r in csv.DictReader(io.StringIO(original.decode()))if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in original else'\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (OUT/'proposed-guards.csv').write_bytes(guards)
    asm=(ROOT/'conker/asm/1A20A0.s').read_text();a=asm.index('glabel '+NAME+'\n');z=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (OUT/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:z]+'\n.size '+NAME+',.-'+NAME+'\n')
    (OUT/'guarded.s').write_text(pg.emit_padded_assembly(obj,ROOT/'conker/asm/1A20A0.s',filename='generated_1A20A0',word_patches_path=OUT/'proposed-guards.csv'))
    for label in ('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(OUT/(label+'.o')),str(OUT/(label+'.s'))],cwd=ROOT/'conker',capture_output=True,check=True)
        assert bound(*payload(OUT/(label+'.o'),NAME))==truth
    allwords=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0xc000000|((ENTRY>>2)&0x3ffffff);callers=[i*4 for i,w in enumerate(allwords)if w==jal];pointers=[i*4 for i,w in enumerate(allwords)if w==ENTRY];assert callers==[0x1b13e8] and not pointers
    report=dict(raw_words=104,words=106,frame=48,guards=len(rows),inserted_save_restore=2,neighbors=8,owner_functions=9,installed=installed,corruption_controls=controls,direct_callers=callers,registry_slots=[],raw_sha256=RAW_SHA256)
    (OUT/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
