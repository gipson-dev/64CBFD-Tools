"""Qualify the EEPROM write poller and its clock-alias guards."""
from pathlib import Path
import hashlib,os,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-eeprom-poller-151dcfd8-qualified'
BASE='#include <ultra64.h>\nextern OSMesgQueue *D_800E0A20;\nextern u8 D_800E0A24;\nextern u8 *D_800E0A28;\nextern s32 D_800E0A2C;\nextern u64 D_8002BD10;\nextern OSTimer D_80042A58;\nextern OSMesg D_80042A90;\nextern OSMesgQueue __osEepromTimerQ;\n/* Signed mode argument is qualified against retail; poller remains pending. */\ns32 func_151DCFD8();\n\n\n/* Non-matching placeholders for the text-only asm slice asm/20A3A0.s. */\n\n/* Drain pending EEPROM work, publish the request, then arm its timer. */\ns32 func_151DCEF0(OSMesgQueue *queue, s32 address, void *buffer, s32 length) {\n    while (func_151DCFD8(1) != 0) {\n    }\n    D_800E0A20 = queue;\n    D_800E0A24 = (u8)address;\n    D_800E0A28 = buffer;\n    D_800E0A2C = length;\n    return osSetTimer(&D_80042A58, (12000ULL * D_8002BD10) / 1000000ULL,\n               0, &__osEepromTimerQ, &D_80042A90);\n}\n\ns32 func_151DCFD8() {\n    return 0;\n}\n'
SELECTED='#include <ultra64.h>\nextern OSMesgQueue *D_800E0A20;\nextern u8 D_800E0A24;\nextern u8 *D_800E0A28;\nextern s32 D_800E0A2C;\nextern u64 D_8002BD10;\nextern OSTimer D_80042A58;\nextern OSMesg D_80042A90;\nextern OSMesgQueue __osEepromTimerQ;\n/* Poll a pending EEPROM write using the requested receive mode. */\ns32 func_151DCFD8(s32);\n\n\n/* EEPROM request setup and pending-write polling. */\n\n/* Drain pending EEPROM work, publish the request, then arm its timer. */\ns32 func_151DCEF0(OSMesgQueue *queue, s32 address, void *buffer, s32 length) {\n    while (func_151DCFD8(1) != 0) {\n    }\n    D_800E0A20 = queue;\n    D_800E0A24 = (u8)address;\n    D_800E0A28 = buffer;\n    D_800E0A2C = length;\n    return osSetTimer(&D_80042A58, (12000ULL * D_8002BD10) / 1000000ULL,\n               0, &__osEepromTimerQ, &D_80042A90);\n}\n\ns32 func_151DD4E0(OSMesgQueue *, u8, u8 *);\n\n/* Advance one pending EEPROM write after its timer message is received. */\ns32 func_151DCFD8(s32 mode) {\n    if (D_800E0A20 == NULL) return 0;\n    if (osRecvMesg(&__osEepromTimerQ, NULL, mode) != -1) {\n        if (D_800E0A2C <= 0) {\n            D_800E0A20 = NULL;\n            D_800E0A2C = 0;\n            return 0;\n        }\n        if (func_151DD4E0(D_800E0A20, D_800E0A24, D_800E0A28) != 0) {\n            D_800E0A20 = NULL;\n            D_800E0A2C = 0;\n            return 0;\n        }\n        D_800E0A2C -= 8;\n        D_800E0A24++;\n        D_800E0A28 += 8;\n        osSetTimer(&D_80042A58, (12000ULL * D_8002BD10) / 1000000ULL,\n                   0, &__osEepromTimerQ, &D_80042A90);\n        return 1;\n    }\n    return 0;\n}\n'
ROWS='generated_20A3A0,func_151DCFD8,0xd4,0x3C070000,0x3C070000,R_MIPS_HI16:D_8002BD10,R_MIPS_HI16:D_8002BD14,Use retail alias for low clock word,,,false\ngenerated_20A3A0,func_151DCFD8,0xd8,0x8CE70004,0x8CE70000,R_MIPS_LO16:D_8002BD10,R_MIPS_LO16:D_8002BD14,Use retail alias for low clock word,,,false\n'.encode()
GUARD_SHA='f95364aa4abc95ed7be354da0cd67973d68b53296bd1a6623dbf8ac764a4be51'
ROM_SHA='f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382'
def norm(b):return b.replace(b'\r\n',b'\n')
def digest(b):return hashlib.sha256(b).hexdigest()
def prepare():
 root=ROOT;out=OUT;out.mkdir(parents=True,exist_ok=True);name='func_151DCFD8'
 assert digest((root/'conker/conker.us.bin').read_bytes())==ROM_SHA
 live=norm((root/'conker/src/game/generated_20A3A0.c').read_bytes()).decode();assert live in (BASE,SELECTED)
 current=norm((root/'conker/retail_word_patches.us.csv').read_bytes())
 if digest(current)==GUARD_SHA:old=current
 else:assert current.endswith(ROWS) and digest(current[:-len(ROWS)])==GUARD_SHA;old=current[:-len(ROWS)]
 oldguards=out/'old-guards.csv';oldguards.write_bytes(old);newguards=out/'new-guards.csv';newguards.write_bytes(old+ROWS)
 before,bd=compile_owner(root,out,BASE,'before');after,ad=compile_owner(root,out,SELECTED,'after')
 assert same_functions(before,after,(name,))==1 and normalized_pools(before)==normalized_pools(after) and diagnostic_rows(bd)==diagnostic_rows(ad)
 asm=(root/'conker/asm/20A3A0.s').read_text();a=asm.index('glabel '+name);b=asm.index('endlabel '+name,a)+len('endlabel '+name)
 def assemble(text,label):
  s=out/(label+'.s');o=out/(label+'.o');s.write_text(text)
  r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o),str(s)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0,r.stderr;return o
 retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:b]+'\n.size '+name+',.-'+name+'\n','retail');truth=payload(retail,name);assert len(truth[0])==348
 gen=assemble(pg.emit_padded_assembly(after,root/'conker/asm/20A3A0.s',word_patches_path=newguards,filename='generated_20A3A0'),'generated')
 gb=assemble(pg.emit_padded_assembly(before,root/'conker/asm/20A3A0.s',word_patches_path=oldguards,filename='generated_20A3A0'),'generated-before')
 generic=assemble(pc.emit_padded_assembly(after,root/'conker/retail_layout.us.txt','generated_20A3A0',word_patches_path=newguards),'generic')
 cb=assemble(pc.emit_padded_assembly(before,root/'conker/retail_layout.us.txt','generated_20A3A0',word_patches_path=oldguards),'generic-before')
 assert payload(gen,name)==truth and payload(generic,name)==truth and same_functions(gb,gen,(name,))==1 and same_functions(cb,generic,(name,))==1
 return dict(before=before,after=after,retail=retail,generated=gen,generic=generic,installed=live==SELECTED and current==old+ROWS)
