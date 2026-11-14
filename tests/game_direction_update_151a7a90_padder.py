from pathlib import Path
import json,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-direction-update-151a7a90-screen';conker=root/'conker';name='func_151A7A90';raw=out/'selected.o';guards=out/'proposed-guards.csv';symbols={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())};truth=(conker/'conker.us.bin').read_bytes()[0x1d4f40:0x1d521c]
texts={'generated':pg.emit_padded_assembly(raw,conker/'asm/1D4E00.s',filename='generated_1D4E00',word_patches_path=guards),'c':pc.emit_padded_assembly(raw,conker/'retail_layout.us.txt','generated_1D4E00',word_patches_path=guards)}
for label,text in texts.items():
 asm=out/(label+'-padded.s');obj=out/(label+'-padded.o');asm.write_text(text);subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(conker)),str(asm.relative_to(conker))],cwd=conker,capture_output=True,check=True)
 assert struct.pack('>183I',*bound_blob(*payload(obj,name),symbols))==truth and same_functions(conker/'build/src/game/generated_1D4E00.c.o',obj,(name,))==22
def link(obj,target,defs,label):
 _,fs,_=pg.parse_object(obj);offset=fs[name]['value'];script=out/(label+'.ld');elf=out/(label+'.elf');binary=out/(label+'.bin');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
 lines=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();names=[line.split()[-1] for line in lines if line.split()];assert set(names)<=set(defs),set(names)-set(defs)
 args=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,*[x for n in names for x in ('--defsym',n+'='+hex(defs[n]))],'-o',str(elf),str(obj)];p=subprocess.run(args,capture_output=True,text=True);assert p.returncode==0,p.stderr;subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
 return binary.read_bytes()[offset:offset+732]
layouts=(0x15000000,0x17000000,0x19000000,0x1b000000)
for i,region in enumerate(layouts):
 target=region+0x1a7a90
 defs=dict(symbols,func_151A8340=region+0x1A8340,func_150ADA68=region+0xADA68,func_151450B4=region+0x1450B4,func_1516972C=region+0x16972C,D_800BE9E4=0x33007FFC+i*0x10000,D_800BE9A4=0x33018004+i*0x10000,D_8008F940=0x33027FF8+i*0x10000,D_8008F948=0x33038008+i*0x10000)
 a=link(out/'retail.o',target,defs,f'link-{i}-retail')
 for label in texts:assert a==link(out/(label+'-padded.o'),target,defs,f'link-{i}-{label}')
installed='void func_151A7A90(struct102 *record' in (conker/'src/game/generated_1D4E00.c').read_text()
report={'padders':2,'layouts':len(layouts),'gnu_links':12,'owner_neighbors':22,'installed':installed};(out/'pad-rebase.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
