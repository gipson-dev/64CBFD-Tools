"""Recover both wave vertex banks with a qualified private frame and roles."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pad
NAME='func_15179DB0';ENTRY=0x15179DB0;ROM=0x1A7260;SIZE=560
SOURCE='conker/src/game/generated_1A7260.c';BUILD='conker/build/game-wave-vertices-15179db0-screen'
RAW_SHA256='a54e86df64bbb89c3cb903f2d95b71f26c75b3156690c32d91b934c188507894'

def normalize(raw,refs):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=RAW_REFS:
        raise ValueError('Wave vertex raw body or named bindings changed')
    original=list(struct.unpack('>140I',raw));order=list(range(140))
    # Move the independent index-tail address before the integer conversion.
    order[58:79]=[78,*range(58,78)];w=[original[i] for i in order]
    nrefs={j*4:refs[i*4] for j,i in enumerate(order) if i*4 in refs}
    # The three pointer arrays never escape. Remove unused compiler frame
    # space, keeping every saved GPR/FPR at its retail offset and the incoming
    # argument at the same absolute address. Outgoing homes remain SP+0..0F.
    assert w[0]==0x27bdff70 and w[1]==0xafa40090 and w[139]==0x27bd0090
    w[0]=0x27bdff80;w[1]=0xafa40080;w[139]=0x27bd0080
    homes={36:0x80,37:0x84,38:0x78,39:0x7c,41:0x80,42:0x88,43:0x78,44:0x80,45:0x8c,46:0x88}
    for i,old in homes.items():
        assert w[i]>>21&31==29 and w[i]&65535==old and not nrefs.get(i*4)
        w[i]=w[i]&0xffff0000|(old-0x1c)
    # Named volatile roles only: opcodes, shifts, arithmetic, memory widths,
    # field offsets and all branch targets survive unchanged.
    for i,fields in ROLE_FIELDS.items():
        op=w[i]>>26
        allowed={'rs','rt','rd'} if op==0 else {'rt'} if op==17 else {'rs'} if op in (49,57) else {'rs','rt'}
        assert set(fields)<=allowed and (op!=17 or w[i]>>21&31==0)
        for name,value in fields.items():
            shift={'rs':21,'rt':16,'rd':11}[name];w[i]=w[i]&~(31<<shift)|value<<shift
    result=struct.pack('>140I',*w)
    from tools.tests.game_wave_vertices_15179db0_proof import qualify
    qualify(bound(raw,refs),bound(result,nrefs))
    return result,nrefs


def proposed(before):
    assert body(before,NAME)=='s32 func_15179DB0() {\n    return 0;\n}'
    return before.replace(body(before,NAME),SELECTED).replace('/* Non-matching placeholders',EXTRA+'\n/* Non-matching placeholders').replace('/* Non-matching placeholders for the text-only asm slice asm/1A7260.s. */','/* Recovered routines for the text-only asm slice asm/1A7260.s. */')

def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
    live=(root/SOURCE).read_text();installed='void '+NAME+'(' in live;before=(out/'production-baseline'/SOURCE).read_text() if installed else live
    proposal=proposed(before);assert not installed or proposal==live
    old,diags=compile_owner(root,out,before,'baseline');obj,new_diags=compile_owner(root,out,proposal,'selected');assert diags==new_diags==''
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);rom=(root/'conker/conker.us.bin').read_bytes();assert bound(normal,nrefs)==list(struct.unpack('>140I',rom[ROM:ROM+SIZE]))
    assert same_functions(old,obj,(NAME,))==10 and normalized_pools(old)==normalized_pools(obj) and len(payload(old,NAME)[0])==12
    for i in range(140):
        changed=bytearray(raw);changed[i*4+3]^=1
        try:normalize(bytes(changed),refs)
        except ValueError:pass
        else:raise AssertionError('Raw corruption accepted')
    try:normalize(raw,{**refs,200:[('R_MIPS_26','func_15047D61')]})
    except ValueError:pass
    else:raise AssertionError('Binding corruption accepted')
    original=(root/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));rows=[]
    for i,(a,b) in enumerate(zip(struct.unpack('>140I',raw),struct.unpack('>140I',normal))):
        if a!=b:
            rows.append(dict(filename='generated_1A7260',function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=relocations(refs.get(i*4,[])),replacement_relocations=relocations(nrefs.get(i*4,[])),note='Restore wave vertex private frame arrays and closed integer temporary roles',insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==72;existing=[r for r in csv.DictReader(io.StringIO(original.decode())) if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (out/'proposed-guards.csv').write_bytes(guards)
    asm=(root/'conker/asm/1A7260.s').read_text();a=asm.index('glabel '+NAME+'\n');z=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (out/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:z]+'\n.size '+NAME+',.-'+NAME+'\n')
    (out/'guarded.s').write_text(pad.emit_padded_assembly(obj,root/'conker/asm/1A7260.s',filename='generated_1A7260',word_patches_path=out/'proposed-guards.csv'))
    for label in ('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(label+'.o')),str(out/(label+'.s'))],cwd=root/'conker',capture_output=True,check=True);assert bound(*payload(out/(label+'.o'),NAME))==bound(normal,nrefs)
    words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0x0c000000|((ENTRY>>2)&0x3ffffff);calls=[i*4 for i,w in enumerate(words) if w==jal];pointers=[i*4 for i,w in enumerate(words) if w==ENTRY]
    assert calls==[0x1b1410] and pointers==[]
    report=dict(words=140,raw_frame=144,frame=128,guards=72,neighbors=10,installed=installed,raw_sha256=hashlib.sha256(raw).hexdigest(),corruption_controls=141,direct_callers=calls,literal_pointers=pointers)
    (out/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
EXTRA="""typedef struct { u32 owner; Vtx *first, *second; u32 retained0C[2]; } WaveBuffers15179DB0;
typedef struct { u8 retained00[0x18]; f32 step[2], phase[2], amplitude; u8 retained2C[0xC]; } WaveState15179DB0;
extern WaveBuffers15179DB0 D_800DDE80[];
extern WaveState15179DB0 D_8008D0B0[];
extern u8 D_800A7210[];
extern f32 D_800A7218;
f32 sinf(f32);

"""
SELECTED="""/* Deform both vertex banks from their phases, then advance each wave once. */
void func_15179DB0(u8 index) {
    Vtx *vertices[2];
    f32 *phases[2];
    f32 *steps[2];
    WaveState15179DB0 *state;
    s16 displacement;
    s32 edge;
    s32 i;
    s32 j;
    f32 factor;

    state = &D_8008D0B0[index];
    vertices[1] = D_800DDE80[index].first;
    vertices[0] = D_800DDE80[index].second;
    phases[0] = &state->phase[0];
    phases[1] = &state->phase[1];
    steps[0] = &state->step[0];
    steps[1] = &state->step[1];
    factor = D_800A7218;
    for (i = 0; i < 2; i++) {
        displacement = (s32)(sinf(*phases[i] * factor) * state->amplitude);
        vertices[i][2].v.ob[0] = displacement;
        vertices[i][3].v.ob[0] = displacement;
        edge = -(displacement >> 1);
        for (j = 0; j < 7; j++) {
            vertices[i][D_800A7210[j]].v.ob[0] = edge;
        }
        vertices[i][6].v.ob[0] = edge + 18;
        vertices[i][8].v.ob[0] = edge - 18;
        *phases[i] += *steps[i];
        if (*phases[i] >= 360.0f) {
            *phases[i] -= 360.0f;
        }
    }
}"""
RAW_REFS={64: [('R_MIPS_HI16', 'D_800DDE80')], 76: [('R_MIPS_LO16', 'D_800DDE80')], 72: [('R_MIPS_HI16', 'D_8008D0B0')], 84: [('R_MIPS_LO16', 'D_8008D0B0')], 100: [('R_MIPS_HI16', 'D_800A7218')], 112: [('R_MIPS_LO16', 'D_800A7218')], 136: [('R_MIPS_HI16', 'D_800A7210')], 160: [('R_MIPS_LO16', 'D_800A7210')], 200: [('R_MIPS_26', 'sinf')], 216: [('R_MIPS_HI16', 'D_800A7210')], 280: [('R_MIPS_LO16', 'D_800A7210')], 224: [('R_MIPS_HI16', 'D_800A7210')], 304: [('R_MIPS_LO16', 'D_800A7210')], 288: [('R_MIPS_HI16', 'D_800A7210')], 328: [('R_MIPS_LO16', 'D_800A7210')]}
ROLE_FIELDS={54: {'rt': 15}, 56: {'rt': 13}, 62: {'rt': 3}, 64: {'rt': 3}, 68: {'rd': 11}, 69: {'rt': 11}, 71: {'rs': 15, 'rt': 15}, 72: {'rt': 14}, 73: {'rt': 9}, 74: {'rt': 15, 'rd': 24}, 75: {'rs': 14, 'rt': 24, 'rd': 25}, 76: {'rs': 25}, 77: {'rs': 9, 'rt': 9}, 78: {'rt': 8}, 79: {'rt': 9, 'rd': 10}, 80: {'rs': 8, 'rt': 10, 'rd': 11}, 81: {'rs': 11}, 82: {'rs': 13, 'rt': 13}, 83: {'rt': 12}, 84: {'rt': 13, 'rd': 15}, 85: {'rs': 12, 'rt': 15, 'rd': 14}, 86: {'rs': 14}, 87: {'rt': 25}, 88: {'rt': 24}, 89: {'rt': 25, 'rd': 9}, 90: {'rs': 24, 'rt': 9, 'rd': 8}, 91: {'rs': 8}, 92: {'rt': 11}, 93: {'rt': 10}, 94: {'rt': 11, 'rd': 13}, 95: {'rs': 10, 'rt': 13, 'rd': 12}, 96: {'rs': 12}, 97: {'rt': 14}, 98: {'rt': 15}, 99: {'rt': 13}, 100: {'rt': 14, 'rd': 25}, 101: {'rs': 15, 'rt': 25, 'rd': 24}, 102: {'rs': 24}, 103: {'rt': 8}, 104: {'rt': 9}, 105: {'rt': 14}, 106: {'rt': 8, 'rd': 11}, 107: {'rs': 9, 'rt': 11, 'rd': 10}, 108: {'rs': 10}, 109: {'rt': 12}, 110: {'rs': 12, 'rt': 13}, 111: {'rt': 15}, 112: {'rs': 15, 'rt': 14}, 114: {'rt': 25}, 116: {'rs': 25}}
def bound(raw,refs,symbols=None):
    symbols=symbols or {n:0x15047d60 if n=='sinf' else int(n.split('_')[1],16) for rows in refs.values() for _,n in rows}
    return bound_blob(raw,refs,symbols)
def relocations(rows):return ';'.join(kind+':'+name for kind,name in rows) or '-'
if __name__=='__main__':main()
