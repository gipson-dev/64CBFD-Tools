"""Check both private padding paths and relocations over four layouts."""
from pathlib import Path
import json,os,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-height-emitter-150e971c-durable';conker=root/'conker';name='func_150E971C'
raw=out/'snapshot.o';guards=out/'proposed-guards.csv';symbols={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())};truth=(conker/'conker.us.bin').read_bytes()[0x116bcc:0x116d38]
texts={'generated':pg.emit_padded_assembly(raw,conker/'asm/113D60.s',filename='generated_113D60',word_patches_path=guards,rodata_symbol='D_800A1350'),
       'c':pc.emit_padded_assembly(raw,conker/'retail_layout.us.txt','generated_113D60',word_patches_path=guards,rodata_symbol='D_800A1350')}
for label,text in texts.items():
 asm=out/(label+'-two-padded.s');obj=out/(label+'-two-padded.o');asm.write_text(text)
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(conker)),str(asm.relative_to(conker))],cwd=conker,capture_output=True,check=True)
 assert struct.pack('>91I',*bound_blob(*payload(obj,name),symbols))==truth and same_functions(conker/'build/src/game/generated_113D60.c.o',obj,(name,))==28
def link(obj,target,defs,label):
 _,fs,_=pg.parse_object(obj);offset=fs[name]['value'];script=out/(label+'.ld');elf=out/(label+'.elf');binary=out/(label+'.bin')
 script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
 lines=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();names=[line.split()[-1] for line in lines if line.split()];assert set(names)<=set(defs),set(names)-set(defs)
 args=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,*[x for n in names for x in ('--defsym',n+'='+hex(defs[n]))],'-o',str(elf),str(obj)]
 p=subprocess.run(args,capture_output=True,text=True);assert p.returncode==0,p.stderr
 subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
 return binary.read_bytes()[offset:offset+364]
layouts=(0x150e971c,0x170e971c,0x190e971c,0x1b0e971c)
for i,target in enumerate(layouts):
 defs=dict(symbols)
 a=link(out/'retail.o',target,defs,f'link-{i}-height-retail')
 for label in texts:assert a==link(out/(label+'-two-padded.o'),target,defs,f'link-{i}-height-{label}')
report={'padders':2,'layouts':len(layouts),'gnu_links':12,'owner_neighbors':28,'uncredited':True}
(out/'pad-rebase.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
