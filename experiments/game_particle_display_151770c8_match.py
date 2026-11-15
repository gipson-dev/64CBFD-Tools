"""Recover the particle display callback with four independent scheduling guards."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess
from tools import pad_generated_object as pg
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
NAME='func_151770C8';ENTRY=0x151770C8;ROM=0x1A4578;SIZE=404
SOURCE='conker/src/game/generated_1A20A0.c';BUILD='conker/build/game-particle-display-callback-151770c8-screen'
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();OUT=ROOT/BUILD
SDK={'guMtxF2L':0x150A7790}
RAW_SHA256='27857f7102944da3d881f3fb8b9c4a27ff9ef7dbf200ede920e4a902c5d54882'
RAW_REFS={76: [('R_MIPS_HI16', 'D_800D9C10')], 80: [('R_MIPS_LO16', 'D_800D9C10')], 28: [('R_MIPS_HI16', 'D_800D9B20')], 32: [('R_MIPS_LO16', 'D_800D9B20')], 44: [('R_MIPS_HI16', 'D_800D35E0')], 60: [('R_MIPS_LO16', 'D_800D35E0')], 68: [('R_MIPS_HI16', 'D_800D35E4')], 72: [('R_MIPS_LO16', 'D_800D35E4')], 112: [('R_MIPS_26', 'func_1510AEE0')], 188: [('R_MIPS_26', 'func_150A8050')], 200: [('R_MIPS_HI16', 'D_800BE9C0')], 204: [('R_MIPS_LO16', 'D_800BE9C0')], 240: [('R_MIPS_26', 'guMtxF2L')], 248: [('R_MIPS_HI16', 'D_800DDE80')], 252: [('R_MIPS_LO16', 'D_800DDE80')], 272: [('R_MIPS_HI16', 'D_800BE9C0')], 276: [('R_MIPS_LO16', 'D_800BE9C0')], 368: [('R_MIPS_26', 'func_15176DF0')]}
SELECTED='/* Cull the particle, build its state-zero matrix, and submit its model. */\nGfx *func_151770C8(Gfx *commands, Particle15175390 *record, s16 view) {\n    f32 matrix[4][4];\n    Gfx *packet;\n    if (!func_1510AEE0(D_800D9C10 + view * 64,\n                     record->position[0], record->position[1], record->position[2],\n                     D_800D9B20, 4000.0f, D_800D35E0, D_800D35E4, 0, 0)) {\n        switch (record->state91) {\n        case 0:\n            func_150A8050(matrix, record->tilt, record->heading, record->fieldB0);\n            matrix[3][0] = record->position[0];\n            matrix[3][1] = record->position[1];\n            matrix[3][2] = record->position[2];\n            guMtxF2L(matrix, (Mtx *)((u8 *)record + D_800BE9C0 * 64 + 16));\n            gSPMatrix(commands++, (u8 *)record + D_800BE9C0 * 64 + 16,\n                      G_MTX_MODELVIEW | G_MTX_LOAD | G_MTX_NOPUSH);\n            gSPSegment(commands++, 1, D_800DDE80[51]);\n            packet = commands++;\n            gSPDisplayList(packet, D_800DDE80[53]);\n            break;\n        case 1:\n        case 2:\n        case 3:\n        default:\n            commands = (Gfx *)func_15176DF0(commands, record, view);\n            break;\n        }\n    }\n    return commands;\n}'
EXTRA='extern f32 D_800D9B20, D_800D35E0, D_800D35E4;\nextern u8 D_800D9C10[], D_800BE9C0;\nextern Gfx *D_800DDE80[];\ns32 func_1510AEE0(void *, f32, f32, f32, f32, f32, f32, f32, f32 *, f32 *);\nvoid func_150A8050(f32 [4][4], f32, f32, f32);\n'

def bound(raw,refs):
    return bound_blob(raw,refs,{n:int(n.split('_')[1],16) if n.startswith(('func_','D_')) else SDK[n] for rows in refs.values() for k,n in rows})

def normalize(raw,refs):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=RAW_REFS:raise ValueError('Particle display source or named bindings changed')
    words=list(struct.unpack('>101I',raw))
    assert words[0]==0x27bdff70 and words[-1]==0x27bd0090
    # A0 already holds the final packet. The three following instructions
    # neither read nor write S1. Move only its independent cursor advance;
    # preserve w0 store -> table load -> w1 store and every named binding.
    assert words[0x144//4]==0x02202025
    assert words[0x14c//4:0x15c//4]==[0x26310008,0x3c18de00,0xac980000,0x8cb900d4]
    assert not any(pc in refs for pc in range(0x14c,0x15c,4))
    assert all((w>>21&31)!=17 and (w>>16&31)!=17 for w in words[0x150//4:0x15c//4])
    words[0x14c//4:0x15c//4]=words[0x150//4:0x15c//4]+words[0x14c//4:0x150//4]
    return struct.pack('>101I',*words),dict(refs)

def proposed(before):
    assert body(before,NAME)=='s32 func_151770C8() {\n    return 0;\n}'
    return before.replace(body(before,NAME),SELECTED).replace('/* Recovered routine',EXTRA+'\n/* Recovered routine',1)
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    live=(ROOT/SOURCE).read_text();installed='Gfx *'+NAME+'(' in live
    before=(OUT/'production-baseline'/SOURCE).read_text() if installed else live
    selected=proposed(before);assert not installed or selected==live
    old,diag=compile_owner(ROOT,OUT,before,'baseline');obj,diag2=compile_owner(ROOT,OUT,selected,'selected');assert diag==diag2==''
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs)
    rom=(ROOT/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>101I',rom,ROM));assert bound(normal,nrefs)==truth
    assert same_functions(old,obj,(NAME,))==8 and normalized_pools(old)==normalized_pools(obj)=={'.rodata':None,'.data':None}
    controls=0
    for i in range(101):
        bad=bytearray(raw);bad[i*4+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed raw word accepted')
    for pc,rows in refs.items():
        try:normalize(raw,{**refs,pc:[(k,n+'_changed') for k,n in rows]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed named binding accepted')
    original=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));rows=[]
    rel=lambda rs:';'.join(k+':'+n for k,n in rs) or '-'
    for i,(a,b) in enumerate(zip(struct.unpack('>101I',raw),struct.unpack('>101I',normal))):
        if a!=b or refs.get(i*4,[])!=nrefs.get(i*4,[]):
            rows.append(dict(filename='generated_1A20A0',function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=rel(refs.get(i*4,[])),replacement_relocations=rel(nrefs.get(i*4,[])),note='Restore independent final display-list cursor scheduling',insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==4
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
    words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0x0c000000|((ENTRY>>2)&0x3ffffff)
    callers=[i*4 for i,w in enumerate(words) if w==jal];assert callers==[];assert struct.unpack_from('>I',rom,0x23034c)[0]==ENTRY
    report=dict(words=101,frame=144,guards=4,neighbors=8,owner_functions=9,installed=installed,corruption_controls=controls,direct_callers=callers,registry_slots=[0x8008b88c],raw_sha256=hashlib.sha256(raw).hexdigest())
    (OUT/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
