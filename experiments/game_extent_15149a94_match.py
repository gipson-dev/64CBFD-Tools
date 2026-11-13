"""Prepare and verify the direct 15149A94 callback under the retail owner profile."""
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
OUT=ROOT/'conker/build/game-extent-callback-15149a94-qualified'
STUB='s32 func_15149A94() {\n    return 0;\n}'
CANDIDATE='extern f32 D_800A578C, D_800A5790;\n/* Advance both actor extents and dispatch the associated effect states. */\ns32 func_15149A94(u8 *actor) {\n    u8 *params = actor + 0x110;\n    s32 complete = 1;\n    if (!(actor[0x74] & 2)) {\n        *(f32 *)(actor + 0x2C) += (*(f32 *)(params + 8) - *(f32 *)(actor + 0x2C)) * *(f32 *)(params + 0x44);\n        if (*(f32 *)(params + 8) * D_800A578C < *(f32 *)(actor + 0x2C)) {\n            actor[0x74] |= 2;\n        } else {\n            complete = 0;\n        }\n    }\n    if (!(actor[0x74] & 8)) {\n        *(f32 *)(actor + 0x30) += (*(f32 *)(params + 0x20) - *(f32 *)(actor + 0x30)) * *(f32 *)(params + 0x44);\n        if (*(f32 *)(params + 0x20) * D_800A5790 < *(f32 *)(actor + 0x30)) {\n            actor[0x74] |= 8;\n        } else {\n            complete = 0;\n        }\n    }\n    if (complete) {\n        func_1513F680((struct171 *)actor, actor[0x70], 13, actor[0x72], actor[0x73]);\n    }\n    if (*(s16 *)(actor + 0x1C) < 5) {\n        func_1513F680((struct171 *)actor, actor[0x70], actor[0x158], actor[0x72], actor[0x73]);\n        *(s16 *)(actor + 0x1C) = 100;\n        *(u32 *)(actor + 0x58) &= ~1;\n    }\n    return 1;\n}'
BASE_SHA='8ddad279ba3f29e40f2c396bf968da17cc71b19afaf06636de5e34a8c30b2f39'
SELECTED_SHA='ffb9bbb8fb303770c0bf56f929ab660a29f5b9ff326a0e9991416aeee9fb8cc4'
ROM_SHA='f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382'
def norm(b):return b.replace(b'\r\n',b'\n')
def digest(b):return hashlib.sha256(b).hexdigest()
def prepare():
 OUT.mkdir(parents=True,exist_ok=True);root=ROOT;out=OUT;name='func_15149A94'
 assert digest((root/'conker/conker.us.bin').read_bytes())==ROM_SHA
 live=norm((root/'conker/src/game/generated_176A00.c').read_bytes()).decode()
 h=digest(live.encode());assert h in (BASE_SHA,SELECTED_SHA),h
 before_source=live if h==BASE_SHA else live.replace(CANDIDATE,STUB,1)
 after_source=before_source.replace(STUB,CANDIDATE,1)
 assert digest(before_source.encode())==BASE_SHA and digest(after_source.encode())==SELECTED_SHA
 before,bd=compile_owner(root,out,before_source,'before');after,ad=compile_owner(root,out,after_source,'after')
 assert same_functions(before,after,(name,))==35 and normalized_pools(before)==normalized_pools(after) and diagnostic_rows(bd)==diagnostic_rows(ad)
 asm=(root/'conker/asm/176A00.s').read_text();start=asm.index('glabel '+name);end=asm.index('endlabel '+name,start)+len('endlabel '+name)
 def assemble(text,label):
  s=out/(label+'.s');o=out/(label+'.o');s.write_text(text)
  r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o),str(s)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0,r.stderr;return o
 retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[start:end]+'\n.size '+name+',.-'+name+'\n','retail')
 truth=payload(retail,name);assert payload(after,name)==truth and len(truth[0])==352
 guards=root/'conker/retail_word_patches.us.csv'
 gen=assemble(pg.emit_padded_assembly(after,root/'conker/asm/176A00.s',word_patches_path=guards,filename='generated_176A00'),'generated')
 gb=assemble(pg.emit_padded_assembly(before,root/'conker/asm/176A00.s',word_patches_path=guards,filename='generated_176A00'),'generated-before')
 generic=assemble(pc.emit_padded_assembly(after,root/'conker/retail_layout.us.txt','generated_176A00',word_patches_path=guards),'generic')
 cb=assemble(pc.emit_padded_assembly(before,root/'conker/retail_layout.us.txt','generated_176A00',word_patches_path=guards),'generic-before')
 assert payload(gen,name)==truth and payload(generic,name)==truth and same_functions(gb,gen,(name,))==35 and same_functions(cb,generic,(name,))==35
 return dict(before=before,after=after,retail=retail,generated=gen,generic=generic,installed=h==SELECTED_SHA)
