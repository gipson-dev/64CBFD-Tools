"""Recover the piece callback with pinned scheduling and register allocation."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pad
NAME='func_1517A1EC';ENTRY=0x1517A1EC;ROM=0x1A769C;SIZE=424
SOURCE='conker/src/game/generated_1A7260.c';BUILD='conker/build/game-piece-update-1517a1ec-screen'
RAW_SHA256='b95469be23c121cedc8691b358a7142df8998f2011425d1f285bee24989c7688'

def normalize(raw,refs):
    bindings={144:[('R_MIPS_26','func_150ADA20')],224:[('R_MIPS_26','func_150ADA20')],308:[('R_MIPS_HI16','D_800BE9E4')],312:[('R_MIPS_LO16','D_800BE9E4')],400:[('R_MIPS_26','func_1516972C')]}
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=bindings:
        raise ValueError('Piece callback raw body or bindings changed')
    w=list(struct.unpack('>106I',raw));assert w[73:77]==[0x948300A6,0x00004012,0x00A84821,0xA48900A4]
    # Restore the lifetime load after the completed Z-speed store. The two
    # ordinary-RAM fields occupy distinct halfwords at A6 and A4.
    w[73:77]=[w[74],w[75],w[76],w[73]]
    fields={81:{16:(12,11)},82:{16:(10,3)},83:{11:(11,10)},85:{21:(10,3),16:(11,10)},90:{16:(12,11)},92:{21:(12,11)},94:{16:(2,3)},95:{21:(2,3)},96:{21:(2,3),16:(13,12)},97:{16:(2,3),11:(14,13)},98:{21:(13,12),16:(14,13)}}
    # Coalesce the dead lifetime register with opacity, then place the
    # retirement byte in that dead opacity register. Temporary roles are
    # confined to these regions; frame, data offsets and branches stay fixed.
    for i,roles in fields.items():
        assert not refs.get(i*4)
        for shift,(old,new) in roles.items():
            assert w[i]>>shift&31==old
            w[i]=w[i]&~(31<<shift)|new<<shift
    return struct.pack('>106I',*w),dict(refs)

def proposed(before):
    assert body(before,NAME)=='s32 func_1517A1EC() {\n    return 0;\n}'
    assert before.count('    u8 retainedAC[4];')==1 and before.count('    u8 retainedB2;')==1
    return before.replace(body(before,NAME),SELECTED).replace('    u8 retainedAC[4];','    u16 motionMode;\n    u16 dampingRange;').replace('    u8 retainedB2;','    u8 retireNibbles;')

def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
    live=(root/SOURCE).read_text();installed='void '+NAME+'(' in live;before=(out/'production-baseline'/SOURCE).read_text() if installed else live
    proposal=proposed(before);assert not installed or proposal==live
    old,diags=compile_owner(root,out,before,'baseline');obj,new_diags=compile_owner(root,out,proposal,'selected');assert diags==new_diags==''
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);rom=(root/'conker/conker.us.bin').read_bytes();truth=rom[ROM:ROM+SIZE]
    assert bound_blob(normal,nrefs)==list(struct.unpack('>106I',truth))
    assert same_functions(old,obj,(NAME,))==10 and normalized_pools(old)==normalized_pools(obj) and len(payload(old,NAME)[0])==12
    for index in range(106):
        bad=bytearray(raw);bad[index*4+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:pass
        else:raise AssertionError('Raw corruption accepted')
    bad={**refs,144:[('R_MIPS_26','func_150ADA21')]}
    try:normalize(raw,bad)
    except ValueError:pass
    else:raise AssertionError('Binding corruption accepted')
    original=(root/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));rows=[]
    for i,(a,b) in enumerate(zip(struct.unpack('>106I',raw),struct.unpack('>106I',normal))):
        if a!=b:
            assert not refs.get(i*4)
            rows.append(dict(filename='generated_1A7260',function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',note='Restore piece callback lifetime-load schedule and private register roles',insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==15;existing=[r for r in csv.DictReader(io.StringIO(original.decode())) if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert existing==[];stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (out/'proposed-guards.csv').write_bytes(guards)
    assembly=(root/'conker/asm/1A7260.s').read_text();a=assembly.index('glabel '+NAME+'\n');z=assembly.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (out/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+assembly[a:z]+'\n.size '+NAME+',.-'+NAME+'\n')
    (out/'guarded.s').write_text(pad.emit_padded_assembly(obj,root/'conker/asm/1A7260.s',filename='generated_1A7260',word_patches_path=out/'proposed-guards.csv'))
    for label in ('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(label+'.o')),str(out/(label+'.s'))],cwd=root/'conker',capture_output=True,check=True)
        assert payload(out/(label+'.o'),NAME)==(normal,nrefs)
    words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0x0c000000|((ENTRY>>2)&0x3ffffff);calls=[i*4 for i,w in enumerate(words) if w==jal];pointers=[i*4 for i,w in enumerate(words) if w==ENTRY]
    assert calls==[] and pointers==[0x230108,0x2301d8,0x23117c]
    assert (root/'conker/asm/data/22FF90.rodata.s').read_text().count('.word '+NAME)==3
    report=dict(words=106,frame=24,guards=15,neighbors=10,installed=installed,raw_sha256=hashlib.sha256(raw).hexdigest(),corruption_controls=107,direct_callers=calls,literal_pointers=pointers,descriptor_indices=[8,12,89])
    (out/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
SELECTED="""/* Advance the piece, damp its horizontal motion, then fade and retire it. */
void func_1517A1EC(SettleFade1517A84C *record) {
    u32 step;
    u32 randomWord;
    s32 remaining;
    s32 opacity;
    s32 packed;
    s32 ticks;

    record->x += record->speedX;
    record->y -= record->speedY;
    record->z += record->speedZ;
    record->angleX += record->spinX;
    record->angleY += record->spinY;
    record->angleZ += record->spinZ;
    if (record->motionMode == 5) {
        record->speedY++;
    }
    if (record->timer < record->motionMode) {
        randomWord = (u32)func_150ADA20();
        step = randomWord % record->dampingRange;
        record->speedX += -(record->speedX < 0 ? -1 : 1) * step;
        randomWord = (u32)func_150ADA20();
        step = randomWord % record->dampingRange;
        record->speedZ += -(record->speedZ < 0 ? -1 : 1) * step;
    }
    ticks = D_800BE9E4;
    remaining = (s32)((u32)record->timer - (u32)ticks);
    if (remaining < 0) {
        remaining = 0;
        opacity = (s32)((u32)record->opacity - ((u32)ticks << 2));
        if (opacity < 0) {
            opacity = 0;
        }
        record->opacity = opacity;
    }
    record->timer = remaining;
    if (record->opacity == 0 ||
        ((packed = record->retireNibbles) != 0 &&
         (packed >> 4) == (packed & 15))) {
        func_1516972C(record);
    }
}"""

if __name__=='__main__':main()
