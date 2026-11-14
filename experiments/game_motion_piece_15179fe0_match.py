"""Recover the motion-piece constructor with pinned spill and store layout."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pad
NAME='func_15179FE0';ENTRY=0x15179FE0;ROM=0x1A7490;SIZE=524
SOURCE='conker/src/game/generated_1A7260.c';BUILD='conker/build/game-motion-piece-15179fe0-screen'
RAW_SHA256='fe39cd31d306fb8f88c08375ef6c8163e09348f9285aa571a841421a5adf0ee4'

def normalize(raw,refs):
    expected={56:[('R_MIPS_26','func_15167A68')],**{at:[('R_MIPS_26','func_150ADA20')] for at in (100,152,280,332,376,420)},440:[('R_MIPS_HI16','D_800A7220')],444:[('R_MIPS_LO16','D_800A7220')]}
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=expected:
        raise ValueError('Motion-piece raw body or named bindings changed')
    w=list(struct.unpack('>131I',raw));assert w[0]==0x27bdffc8
    # Both cached range/half pairs are unescaped private scalars. Their retail
    # homes are SP+28/+2C; frame, saves, outgoing arguments and incoming homes
    # stay fixed. These stores/loads retain their original values and order.
    homes={37:(0x2c,0x28),39:(0x30,0x2c),40:(0x30,0x2c),41:(0x2c,0x28),82:(0x2c,0x28),84:(0x30,0x2c),85:(0x30,0x2c),86:(0x2c,0x28),96:(0x30,0x2c),97:(0x2c,0x28)}
    for i,(old,new) in homes.items():
        assert not refs.get(i*4) and w[i]>>26 in (35,43) and w[i]>>21&31==29 and w[i]&65535==old
        w[i]=w[i]&0xffff0000|new
    # Exchange the nonoverlapping opacity-constant and damping-byte temporary
    # roles, then restore mode, damping load, retirement clear, opacity store.
    for i,old,new in ((113,12,14),(122,12,14),(124,14,12),(125,14,12)):
        assert w[i]>>16&31==old and not refs.get(i*4);w[i]=w[i]&~(31<<16)|new<<16
    assert w[121]>>26==40 and w[122]>>26==40 and w[123]>>26==41 and w[124]>>26==36
    w[121:125]=[w[123],w[124],w[121],w[122]]
    return struct.pack('>131I',*w),dict(refs)

def proposed(before):
    assert body(before,NAME)=='s32 func_15179FE0() {\n    return 0;\n}'
    return before.replace(body(before,NAME),SELECTED).replace('extern f32 D_800A7224, D_800A7228;','extern f32 D_800A7220, D_800A7224, D_800A7228;')

def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
    live=(root/SOURCE).read_text();installed='void '+NAME+'(' in live;before=(out/'production-baseline'/SOURCE).read_text() if installed else live
    proposal=proposed(before);assert not installed or proposal==live
    old,diags=compile_owner(root,out,before,'baseline');obj,new_diags=compile_owner(root,out,proposal,'selected');assert diags==new_diags==''
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);rom=(root/'conker/conker.us.bin').read_bytes();assert bound_blob(normal,nrefs)==list(struct.unpack('>131I',rom[ROM:ROM+SIZE]))
    assert same_functions(old,obj,(NAME,))==10 and normalized_pools(old)==normalized_pools(obj) and len(payload(old,NAME)[0])==12
    for i in range(131):
        changed=bytearray(raw);changed[i*4+3]^=1
        try:normalize(bytes(changed),refs)
        except ValueError:pass
        else:raise AssertionError('Raw corruption accepted')
    try:normalize(raw,{**refs,56:[('R_MIPS_26','func_15167A69')]})
    except ValueError:pass
    else:raise AssertionError('Binding corruption accepted')
    original=(root/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));rows=[]
    for i,(a,b) in enumerate(zip(struct.unpack('>131I',raw),struct.unpack('>131I',normal))):
        if a!=b:
            assert not refs.get(i*4)
            rows.append(dict(filename='generated_1A7260',function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',note='Preserve motion-piece cached-range spill homes and final initialization schedule',insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==16;existing=[r for r in csv.DictReader(io.StringIO(original.decode())) if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (out/'proposed-guards.csv').write_bytes(guards)
    asm=(root/'conker/asm/1A7260.s').read_text();a=asm.index('glabel '+NAME+'\n');z=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (out/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:z]+'\n.size '+NAME+',.-'+NAME+'\n')
    (out/'guarded.s').write_text(pad.emit_padded_assembly(obj,root/'conker/asm/1A7260.s',filename='generated_1A7260',word_patches_path=out/'proposed-guards.csv'))
    for label in ('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(label+'.o')),str(out/(label+'.s'))],cwd=root/'conker',capture_output=True,check=True);assert payload(out/(label+'.o'),NAME)==(normal,nrefs)
    words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0x0c000000|((ENTRY>>2)&0x3ffffff);calls=[i*4 for i,w in enumerate(words) if w==jal];pointers=[i*4 for i,w in enumerate(words) if w==ENTRY]
    assert calls==[0xf5124] and pointers==[]
    report=dict(words=131,frame=56,guards=16,neighbors=10,installed=installed,raw_sha256=hashlib.sha256(raw).hexdigest(),corruption_controls=132,direct_callers=calls,literal_pointers=pointers)
    (out/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
SELECTED="""/* Construct a moving piece with centered random velocity and signed spin. */
void func_15179FE0(u8 variant, s16 x, s16 y, s16 z, s8 verticalSpeed,
                  u16 lifetime, u16 mode, u8 movementRange, u8 spinRange,
                  u8 dampingRange, s32 category) {
    SettleFade1517A84C *record;

    record = func_15167A68(category, 0, 0xB8, 1, 255, 1);
    if (record != NULL) {
        record->x = x;
        record->y = y;
        record->z = z;
        record->speedY = verticalSpeed;
        record->speedX = (u32)func_150ADA20() % movementRange - (movementRange >> 1);
        record->speedZ = (u32)func_150ADA20() % movementRange - (movementRange >> 1);
        if (mode == 5) {
            record->x += record->speedX * 4;
            record->y -= record->speedY * 4;
            record->z += record->speedZ * 4;
        }
        record->angleX = 0;
        record->angleY = 0;
        record->angleZ = 0;
        record->spinX = (u32)func_150ADA20() % spinRange - (spinRange >> 1);
        record->spinY = (u32)func_150ADA20() % spinRange - (spinRange >> 1);
        record->spinZ = (u32)func_150ADA20() % spinRange - (spinRange >> 1);
        record->scale = ((func_150ADA20() & 127) + 140) * D_800A7220;
        record->timer = lifetime;
        record->variant = variant;
        record->motionMode = mode;
        record->retireNibbles = 0;
        record->opacity = 255;
        record->dampingRange = dampingRange;
    }
}"""

if __name__=='__main__':main()
