"""Recover the piece renderer with pinned alpha-cache addressing and tail scheduling."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pad
NAME='func_1517A3A0';ENTRY=0x1517A3A0;ROM=0x1A7850;SIZE=676
SOURCE='conker/src/game/generated_1A7260.c';BUILD='conker/build/game-piece-renderer-1517a3a0-screen'
RAW_SHA256='27ceee2eaaddc6b7785ebda289d4ee96e80cc7ce584ff471c2603d26f0e1218c'

def normalize(raw,refs):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=RAW_REFS:
        raise ValueError('Piece renderer raw body or named bindings changed')
    w=list(struct.unpack('>169I',raw));assert w[0]==0x27bdffa8
    before=w[:];oldrefs=dict(refs)
    # Keep the matrix command and alpha test, replacing the compiler's reused
    # cache address (LUI/ADDIU/LH/SH) by two direct symbolic LUI+access pairs.
    # The alpha cache is disjoint ordinary RAM. The address temporary is dead
    # at the material-state call; all public reads, writes and branches survive.
    order=[111,112,113,114,115,116,117,109,119,120,121,122,124,123,125,118,127,128,126,130,129,131,132,133,134,135,136,137,138,109,139]
    assert len(order)==31
    w[109:140]=[before[i] for i in order]
    nrefs={i:v for i,v in oldrefs.items() if not 109*4<=i<140*4}
    for j,i in enumerate(order,109):
        if i*4 in oldrefs:nrefs[j*4]=oldrefs[i*4]
    def rt(i,old,new):
        assert w[i]>>16&31==old;w[i]=w[i]&~(31<<16)|new<<16
    def rs(i,old,new):
        assert w[i]>>21&31==old;w[i]=w[i]&~(31<<21)|new<<21
    rt(116,4,25);rt(121,25,24)
    assert w[122]==0x84980000 and w[139]==0xa48c0000
    w[122]=0x87390000;w[139]=0xa42c0000
    rt(138,4,1)
    nrefs[122*4]=oldrefs[110*4];nrefs[139*4]=oldrefs[110*4]
    assert w[125]&65535==12;w[125]=w[125]&0xffff0000|14
    for i in (126,140):
        assert w[i]&65535==0x57;w[i]=w[i]&0xffff0000|0x43
    # Closed temporary-role substitutions in the mode word and terminal list.
    assert w[155]>>11&31==13;w[155]=w[155]&~(31<<11)|24<<11
    rs(157,13,24);rt(158,24,9);rs(159,24,9);rt(159,24,9)
    rt(160,15,10);rt(161,15,10);rt(162,24,9)
    return struct.pack('>169I',*w),nrefs


def proposed(before):
    assert body(before,NAME)=='s32 func_1517A3A0() {\n    return 0;\n}'
    return before.replace(body(before,NAME),SELECTED).replace('/* Non-matching placeholders',EXTRA+'\n/* Non-matching placeholders')

def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
    live=(root/SOURCE).read_text();installed='Gfx *'+NAME+'(' in live;before=(out/'production-baseline'/SOURCE).read_text() if installed else live
    proposal=proposed(before);assert not installed or proposal==live
    old,diags=compile_owner(root,out,before,'baseline');obj,new_diags=compile_owner(root,out,proposal,'selected');assert diags==new_diags==''
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);rom=(root/'conker/conker.us.bin').read_bytes();assert bound_blob(normal,nrefs)==list(struct.unpack('>169I',rom[ROM:ROM+SIZE]))
    assert same_functions(old,obj,(NAME,))==10 and normalized_pools(old)==normalized_pools(obj) and len(payload(old,NAME)[0])==12
    for i in range(169):
        changed=bytearray(raw);changed[i*4+3]^=1
        try:normalize(bytes(changed),refs)
        except ValueError:pass
        else:raise AssertionError('Raw corruption accepted')
    try:normalize(raw,{**refs,168:[('R_MIPS_26','func_1510AEE1')]})
    except ValueError:pass
    else:raise AssertionError('Binding corruption accepted')
    original=(root/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));rows=[]
    for i,(a,b) in enumerate(zip(struct.unpack('>169I',raw),struct.unpack('>169I',normal))):
        if a!=b:
            rows.append(dict(filename='generated_1A7260',function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=relocations(refs.get(i*4,[])),replacement_relocations=relocations(nrefs.get(i*4,[])),note='Restore piece-renderer alpha address pairs private sync home and tail scheduling',insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==38;existing=[r for r in csv.DictReader(io.StringIO(original.decode())) if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (out/'proposed-guards.csv').write_bytes(guards)
    asm=(root/'conker/asm/1A7260.s').read_text();a=asm.index('glabel '+NAME+'\n');z=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (out/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:z]+'\n.size '+NAME+',.-'+NAME+'\n')
    (out/'guarded.s').write_text(pad.emit_padded_assembly(obj,root/'conker/asm/1A7260.s',filename='generated_1A7260',word_patches_path=out/'proposed-guards.csv'))
    for label in ('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(label+'.o')),str(out/(label+'.s'))],cwd=root/'conker',capture_output=True,check=True);assert bound_blob(*payload(out/(label+'.o'),NAME))==bound_blob(normal,nrefs)
    words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0x0c000000|((ENTRY>>2)&0x3ffffff);calls=[i*4 for i,w in enumerate(words) if w==jal];pointers=[i*4 for i,w in enumerate(words) if w==ENTRY]
    assert calls==[] and pointers==[0x230110,0x230144,0x2301e0,0x231184]
    report=dict(words=169,frame=88,guards=38,neighbors=10,installed=installed,raw_sha256=hashlib.sha256(raw).hexdigest(),corruption_controls=170,direct_callers=calls,literal_pointers=pointers)
    (out/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
EXTRA='extern f32 D_800D9B20, D_800D9B1C, D_800D35E0, D_800D35E4;\nextern u8 D_800D9C10[], D_800BE9C0;\nextern u32 D_800D2C9C;\nextern Gfx D_8008CDF0[];\ns32 func_1510AEE0(void *, f32, f32, f32, f32, f32, f32, f32, f32 *, f32 *);\nvoid func_15043D90(Mtx *, f32, f32, f32, f32, f32, f32, f32, f32, f32);\nGfx *func_15142FBC(Gfx *, u32, u32, u8 *);\ns32 func_1517A9A8(s32, volatile s32);\n\n'
SELECTED='/* Cull each view, mark retirement visibility, and draw the transformed piece. */\nGfx *func_1517A3A0(Gfx *commands, SettleFade1517A84C *record, s16 view) {\n    u8 sync;\n\n    if (record->retained00[0] != 12 && record->retained00[0] != 89 &&\n        func_1510AEE0(D_800D9C10 + view * 64, record->x, record->y, record->z,\n                      D_800D9B20, D_800D9B1C, D_800D35E0, D_800D35E4, 0, 0)) {\n        if (record->retained00[0] == 8 && (record->retireNibbles & (1 << view))) {\n            record->retireNibbles |= 16 << view;\n        }\n        return commands;\n    }\n    if (record->retained00[0] != 9) {\n        record->retireNibbles |= 1 << view;\n    }\n    commands = (Gfx *)func_1517A9A8((s32)commands, record->variant);\n    func_15043D90((Mtx *)((u8 *)record + D_800BE9C0 * 64 + 16),\n                  record->angleX, record->angleY, record->angleZ,\n                  record->scale, record->scale, record->scale,\n                  record->x, record->y, record->z);\n    gSPMatrix(commands++, (u8 *)record + D_800BE9C0 * 64 + 16,\n              G_MTX_MODELVIEW | G_MTX_LOAD | G_MTX_NOPUSH);\n    if (record->opacity != D_800DD450) {\n        gDPPipeSync(commands++);\n        gDPSetPrimColor(commands++, 0, 0, 0, 0, 0, record->opacity);\n        D_800DD450 = record->opacity;\n    }\n    sync = 0;\n    commands = func_15142FBC(commands, D_800D2C9C | 0x80000 | 0x2CA0,\n                            record->retained00[0] == 8 || record->retained00[0] == 9 ? 0x5049D8 : 0x504240, &sync);\n    gSPDisplayList(commands++, D_8008CDF0);\n    return commands;\n}'
RAW_REFS={124: [('R_MIPS_HI16', 'D_800D9C10')], 128: [('R_MIPS_LO16', 'D_800D9C10')], 80: [('R_MIPS_HI16', 'D_800D9B20')], 84: [('R_MIPS_LO16', 'D_800D9B20')], 88: [('R_MIPS_HI16', 'D_800D9B1C')], 92: [('R_MIPS_LO16', 'D_800D9B1C')], 100: [('R_MIPS_HI16', 'D_800D35E0')], 104: [('R_MIPS_LO16', 'D_800D35E0')], 108: [('R_MIPS_HI16', 'D_800D35E4')], 120: [('R_MIPS_LO16', 'D_800D35E4')], 168: [('R_MIPS_26', 'func_1510AEE0')], 284: [('R_MIPS_26', 'func_1517A9A8')], 344: [('R_MIPS_HI16', 'D_800BE9C0')], 348: [('R_MIPS_LO16', 'D_800BE9C0')], 428: [('R_MIPS_26', 'func_15043D90')], 436: [('R_MIPS_HI16', 'D_800DD450')], 440: [('R_MIPS_LO16', 'D_800DD450')], 460: [('R_MIPS_HI16', 'D_800BE9C0')], 464: [('R_MIPS_LO16', 'D_800BE9C0')], 472: [('R_MIPS_HI16', 'D_800D2C9C')], 608: [('R_MIPS_LO16', 'D_800D2C9C')], 624: [('R_MIPS_26', 'func_15142FBC')], 632: [('R_MIPS_HI16', 'D_8008CDF0')], 636: [('R_MIPS_LO16', 'D_8008CDF0')]}
def relocations(rows):return ';'.join(kind+':'+name for kind,name in rows) or '-'
if __name__=='__main__':main()
