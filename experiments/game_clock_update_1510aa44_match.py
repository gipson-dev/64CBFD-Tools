"""Clock hands and chime recovery with a closed caller-FPR permutation."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_particle_display_151770c8_match import bound
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
NAME='func_1510AA44';ENTRY=0x1510AA44;ROM=0x137EF4;SIZE=916
SOURCE='conker/src/game/generated_137ED0.c';BUILD='conker/build/game-clock-update-1510aa44-screen'
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();OUT=ROOT/BUILD;SDK={'cosf'}
SELECTED='/* Advance the clock hands and submit a pending chime when its second changes. */\nvoid func_1510AA44(u8 *state) {\n    s32 previousMinute, minute, second;\n    f32 hourAngle;\n\n    previousMinute = (*(s32 *)(state + 0x3C) / 3600) % 60;\n    if (*(s32 *)(state + 0x84) == 0 && D_800BE3E4 != 0) {\n        *(s32 *)(state + 0x84) = 1;\n        *(s32 *)(state + 0x3C) = ((u32)D_800BE3E4 * 180U) % 43200U;\n        *(s32 *)(state + 0x3C) *= 60;\n        previousMinute = (*(s32 *)(state + 0x3C) / 3600) % 60;\n    }\n    if (previousMinute < 0) previousMinute += 60;\n    *(s32 *)(state + 0x3C) = (s32)((u32)*(s32 *)(state + 0x3C) + (u32)D_800BE9E4);\n    if (*(s32 *)(state + 0x3C) >= 2592000) {\n        *(s32 *)(state + 0x3C) -= 2592000;\n    }\n    second = *(s32 *)(state + 0x3C) / 60;\n    minute = second / 60;\n    hourAngle = (f32)(second / 300) * 2.5f;\n    if (360.0f < hourAngle) *(s32 *)(state + 0x3C) = *(s32 *)(state + 0x3C) - 2592000;\n    minute %= 60;\n    if (minute < 0) minute += 60;\n    if (previousMinute != minute && minute / 15 != previousMinute / 15) {\n        if ((minute / 15 & 3) == 0) {\n            *(s32 *)(state + 0x7C) = (s32)(hourAngle / 30.0f);\n            if (*(s32 *)(state + 0x7C) == 0) *(s32 *)(state + 0x7C) = 12;\n        } else {\n            *(s32 *)(state + 0x7C) = 1;\n        }\n        *(s32 *)(state + 0x80) = -1;\n    }\n    if (*(s32 *)(state + 0x7C) != 0 && second != *(s32 *)(state + 0x80)) {\n        *(s32 *)(state + 0x80) = second;\n        *(s32 *)(state + 0x7C) = (s32)((u32)*(s32 *)(state + 0x7C) - 1U);\n        func_15114D24(state, 0x4CC, 32767, 200, 1000, 12);\n    }\n    *(f32 *)(state + 0x68) = 5.0f;\n    *(f32 *)(state + 0x108) = 5.0f;\n    *(f32 *)(state + 0xA8) = -hourAngle;\n    *(f32 *)(state + 8) = -((f32)minute * 6.0f);\n}'
RAW_SHA256='f826860b370a8b49ad9989c89cf76c646e34b7af6c716529066bc1ba92ff1e6c'
RAW_REFS={120: [('R_MIPS_HI16', 'D_800BE3E4')], 124: [('R_MIPS_LO16', 'D_800BE3E4')], 308: [('R_MIPS_HI16', 'D_800BE9E4')], 316: [('R_MIPS_LO16', 'D_800BE9E4')], 832: [('R_MIPS_26', 'func_15114D24')]}

FPRS={8:6,10:8,16:10,6:4,18:16,4:18}

def fp_fields(w):
    op,fmt,fn=w>>26,w>>21&31,w&63
    if op in(49,57):return (16,)
    if op==17 and fmt in(0,4):return (11,)
    if op==17 and fmt in(16,20):return (11,6)if fn in(7,32)else(11,16,6)
    return ()

def normalize(raw,refs):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=RAW_REFS:raise ValueError('Clock raw instructions or bindings changed')
    ws=list(struct.unpack('>229I',raw));normal=ws[:];pc=0x2b8;w=ws[pc//4]
    assert w>>26==20 and {w>>21&31,w>>16&31}=={2,13}
    normal[pc//4]=w&~(31<<21|31<<16)|(w>>16&31)<<21|(w>>21&31)<<16
    for pc in range(0x300,SIZE,4):
        w=ws[pc//4]
        for shift in fp_fields(w):
            old=ws[pc//4]>>shift&31;w=w&~(31<<shift)|FPRS.get(old,old)<<shift
        normal[pc//4]=w
    from tools.tests.game_clock_update_1510aa44_proof import prove
    prove(ws,normal,refs)
    return struct.pack('>229I',*normal),dict(refs)

def proposed(before):
    assert body(before,NAME)=='s32 func_1510AA44() {\n    return 0;\n}'
    return before.replace(body(before,NAME),'extern s32 D_800BE3E4;\n\n'+SELECTED).replace('/* Non-matching placeholders for the text-only asm slice asm/137ED0.s. */','/* Recovered routines for the text-only asm slice asm/137ED0.s. */')

def main():
    OUT.mkdir(parents=True,exist_ok=True);live=(ROOT/SOURCE).read_text();installed='void '+NAME+'('in live
    before=(OUT/'production-baseline'/SOURCE).read_text()if installed else live;candidate=proposed(before);assert not installed or candidate==live
    old,d=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,candidate,'selected');assert d==d2==''and same_functions(old,obj,(NAME,))==3 and normalized_pools(old)==normalized_pools(obj)
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);truth=struct.unpack_from('>229I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM);assert bound(normal,nrefs)==list(truth)
    controls=0
    for i in range(229):
        bad=bytearray(raw);bad[i*4+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed word accepted')
    for pc,rows in refs.items():
        try:normalize(raw,{**refs,pc:[(k,n+'_changed')for k,n in rows]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed binding accepted')
    original=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(original.decode())));rows=[]
    for i,(a,b)in enumerate(zip(struct.unpack('>229I',raw),struct.unpack('>229I',normal))):
        if a!=b:rows.append(dict(filename='generated_137ED0',function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',note='Normalize clock commutative equality and closed caller floating-register allocation',insert_after='',insert_after_relocations='',omit='false'));assert i*4 not in refs
    existing=[r for r in csv.DictReader(io.StringIO(original.decode()))if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n'if b'\r\n'in original else'\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (OUT/'proposed-guards.csv').write_bytes(guards)
    asm=(ROOT/'conker/asm/137ED0.s').read_text();start=asm.index('glabel '+NAME+'\n');end=asm.index('endlabel '+NAME,start)+len('endlabel '+NAME)
    (OUT/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[start:end]+'\n.size '+NAME+',.-'+NAME+'\n')
    (OUT/'guarded.s').write_text(pg.emit_padded_assembly(obj,ROOT/'conker/asm/137ED0.s',filename='generated_137ED0',word_patches_path=OUT/'proposed-guards.csv'))
    for label in('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(OUT/(label+'.o')),str(OUT/(label+'.s'))],cwd=ROOT/'conker',capture_output=True,check=True);assert bound(*payload(OUT/(label+'.o'),NAME))==list(truth)
    assert same_functions(OUT/'production-baseline/conker/build/src/game/generated_137ED0.c.o',OUT/'guarded.o',(NAME,))==3
    report=dict(raw_words=229,words=229,frame=64,guards=len(rows),inserted_nops=0,neighbors=3,corruption_controls=controls,installed=installed,raw_sha256=RAW_SHA256)
    (OUT/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
