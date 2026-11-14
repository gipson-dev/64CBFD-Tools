"""Recover the settling burst-piece factory and pin one low-half stack load."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pad
NAME='func_1517A644';ENTRY=0x1517A644;ROM=0x1A7AF4;SIZE=520
SOURCE='conker/src/game/generated_1A7260.c';BUILD='conker/build/game-burst-piece-1517a644-screen'
RAW_SHA256='afc60ae7eb1e5888a8387fdd138857ec6b6c5c38948892dc914ab6b20281dbb5'

def normalize(raw,refs):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256:
        raise ValueError('Burst-piece raw body changed')
    expected={80:'func_15167A68',176:'func_1510E82C',240:'func_150ADA20',280:'func_150ADA20',352:'func_150ADA20',412:'func_150ADA20',448:'func_150ADA20'}
    bindings={at:[('R_MIPS_26',name)] for at,name in expected.items()}
    bindings.update({308:[('R_MIPS_HI16','D_800A7224')],312:[('R_MIPS_LO16','D_800A7224')],320:[('R_MIPS_HI16','D_800A7228')],332:[('R_MIPS_LO16','D_800A7228')]})
    if refs!=bindings:raise ValueError('Burst-piece named bindings changed')
    words=list(struct.unpack('>130I',raw));assert words[58]==0x8FAD0070 and words[61]==0xA60D0094
    # T5's loaded value is consumed only by the 16-bit store, then overwritten
    # before its next read. The four-byte incoming home is mapped in the o32 ABI.
    assert words[101]==0x01836823
    words[58]=0x87AD0072
    return struct.pack('>130I',*words),dict(refs)

def proposed(before):
    old='s32 func_1517A644(f32 size, u8 kind, s16 x, s16 y, s32 z) {\n    return 0;\n}'
    assert body(before,NAME)==old and before.count('    u8 retainedA8[8];')==1
    return before.replace(old,SELECTED).replace('    u8 retainedA8[8];','    f32 scale;\n    u8 retainedAC[4];').replace('    u8 retained9F;','    u8 variant;').replace('    u8 opacity;','    u8 opacity;\n    u8 retainedB4[4];').replace('s32 func_150ADA20(void);','s32 func_150ADA20(void);\n'+DECLS)

def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
    live=(root/SOURCE).read_text();installed='void '+NAME+'(' in live
    before=(out/'production-baseline'/SOURCE).read_text() if installed else live
    proposal=proposed(before);assert not installed or proposal==live
    old,diags=compile_owner(root,out,before,'baseline');obj,new_diags=compile_owner(root,out,proposal,'selected');assert diags==new_diags==''
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs)
    truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE]
    assert bound_blob(normal,nrefs)==list(struct.unpack('>130I',truth))
    assert same_functions(old,obj,(NAME,))==10 and normalized_pools(old)==normalized_pools(obj)
    assert len(payload(old,NAME)[0])==28
    for index in range(130):
        corrupted=bytearray(raw);corrupted[index*4+3]^=1
        try:normalize(bytes(corrupted),refs)
        except ValueError:pass
        else:raise AssertionError('Raw corruption accepted')
    corrupted={**refs,80:[('R_MIPS_26','func_15167A69')]}
    try:normalize(raw,corrupted)
    except ValueError:pass
    else:raise AssertionError('Binding corruption accepted')
    original=(root/'conker/retail_word_patches.us.csv').read_bytes();rows=list(csv.DictReader(io.StringIO(original.decode())));existing=[r for r in rows if r['function']==NAME]
    row=dict(filename='generated_1A7260',function=NAME,offset='0xE8',expected='0x8FAD0070',replacement='0x87AD0072',expected_relocations='-',replacement_relocations='-',note='Preserve the original signed low-half load from the fifth argument home',insert_after='',insert_after_relocations='',omit='false')
    if installed:assert existing==[row];guards=original
    else:
        assert existing==[];stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=next(csv.reader(io.StringIO(original.decode()))),lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerow(row);guards=original+stream.getvalue().encode()
    (out/'proposed-guards.csv').write_bytes(guards)
    assembly=(root/'conker/asm/1A7260.s').read_text();a=assembly.index('glabel '+NAME+'\n');z=assembly.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (out/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+assembly[a:z]+'\n.size '+NAME+',.-'+NAME+'\n')
    (out/'guarded.s').write_text(pad.emit_padded_assembly(obj,root/'conker/asm/1A7260.s',filename='generated_1A7260',word_patches_path=out/'proposed-guards.csv'))
    for label in ('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(label+'.o')),str(out/(label+'.s'))],cwd=root/'conker',capture_output=True,check=True)
        assert payload(out/(label+'.o'),NAME)==(normal,nrefs)
    rom=(root/'conker/conker.us.bin').read_bytes();words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0x0c000000|((ENTRY>>2)&0x3ffffff)
    calls=[i*4 for i,w in enumerate(words) if w==jal];pointers=[i*4 for i,w in enumerate(words) if w==ENTRY];assert calls==[0x1a7fe4] and pointers==[]
    report=dict(words=130,frame=96,guards=1,neighbors=10,installed=installed,raw_sha256=hashlib.sha256(raw).hexdigest(),corruption_controls=131,direct_callers=calls,literal_pointers=pointers)
    (out/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
DECLS="""void *func_15167A68(s32, s32, s32, s32, u8, u8);
void func_1510E82C(s32, s32, f32 *, s32, s32, s32, f32, f32, f32, f32, u16, s32);
extern f32 D_800A7224, D_800A7228;
"""
SELECTED="""/* Allocate and initialize one settling burst piece, including its random spin. */
void func_1517A644(f32 size, u8 kind, s16 x, s16 y, s32 z) {
    SettleFade1517A84C *record;
    s32 range;
    f32 height;
    s32 halfSize;

    range = size;
    if (range != 0) {
        record = func_15167A68(9, 0, 0xB8, 1, 255, 1);
        if (record != NULL) {
            func_1510E82C(0, 0, &height, 0, 0, 0, (f32)x, (f32)y,
                          (f32)(s16)z, (f32)y, 0, 0);
            record->y = record->floorY = (s16)(s32)(height + 3.0f);
            record->x = x;
            record->z = (s16)z;
            record->angleX = 90;
            record->angleY = (u32)func_150ADA20() % 360;
            record->angleZ = 0;
            record->speedX = 0;
            record->speedZ = 0;
            record->variant = kind;
            record->scale = (s32)((u32)func_150ADA20() % 80 + 100) * D_800A7224;
            record->speedY = (s16)(s32)(size * D_800A7228);
            record->spinX = (u32)func_150ADA20() % range - (halfSize = size * 0.5f);
            record->spinY = (u32)func_150ADA20() % range - halfSize;
            record->spinZ = (u32)func_150ADA20() % range - halfSize;
            record->timer = 0;
            record->opacity = 255;
        }
    }
}"""

if __name__=='__main__':main()
