from pathlib import Path
import json,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-associated-update-1511473c-screen';conker=root/'conker';name='func_1511473C';raw=out/'selected.o';guards=out/'proposed-guards.csv';symbols={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())};truth=(conker/'conker.us.bin').read_bytes()[0x141bec:0x141d58]
texts={'generated':pg.emit_padded_assembly(raw,conker/'asm/13D350.s',filename='generated_13D350',word_patches_path=guards),'c':pc.emit_padded_assembly(raw,conker/'retail_layout.us.txt','generated_13D350',word_patches_path=guards)}
for label,text in texts.items():
 asm=out/(label+'-padded.s');obj=out/(label+'-padded.o');asm.write_text(text);subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(conker)),str(asm.relative_to(conker))],cwd=conker,capture_output=True,check=True)
 assert struct.pack('>91I',*bound_blob(*payload(obj,name),symbols))==truth and same_functions(conker/'build/src/game/generated_13D350.c.o',obj,(name,))==33
def link(obj,target,defs,label):
 _,fs,_=pg.parse_object(obj);offset=fs[name]['value'];script=out/(label+'.ld');elf=out/(label+'.elf');binary=out/(label+'.bin');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
 lines=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();names=[line.split()[-1] for line in lines if line.split()];assert set(names)<=set(defs),set(names)-set(defs)
 args=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,*[x for n in names for x in ('--defsym',n+'='+hex(defs[n]))],'-o',str(elf),str(obj)];p=subprocess.run(args,capture_output=True,text=True);assert p.returncode==0,p.stderr;subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
 return binary.read_bytes()[offset:offset+364]
layouts=(0x15000000,0x17000000,0x19000000,0x1b000000)
for i,region in enumerate(layouts):
 target=region+0x11473c
 defs=dict(symbols,func_15114348=region+0x114348,D_800DBEF0=0x80107ffc+i*0x20000,D_800DBEF4=0x80108000+i*0x20000,D_800A2F60=0x80117ffc+i*0x20000,D_800CC2D0=0x80118000+i*0x20000,D_800CBDA0=0x8010fffc+i*0x20000)
 a=link(out/'retail.o',target,defs,f'link-{i}-retail')
 for label in texts:assert a==link(out/(label+'-padded.o'),target,defs,f'link-{i}-{label}')
report={'padders':2,'layouts':len(layouts),'gnu_links':12,'owner_neighbors':33,'uncredited':True};(out/'pad-rebase.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
