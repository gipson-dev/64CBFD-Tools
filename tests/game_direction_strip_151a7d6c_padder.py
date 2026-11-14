from pathlib import Path
import json,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-direction-strip-151a7d6c-screen';conker=root/'conker';name='func_151A7D6C';raw=out/'selected.o';guards=out/'proposed-guards.csv';symbols={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())};truth=(conker/'conker.us.bin').read_bytes()[0x1d521c:0x1d57f0]
texts={'generated':pg.emit_padded_assembly(raw,conker/'asm/1D4E00.s',filename='generated_1D4E00',word_patches_path=guards),'c':pc.emit_padded_assembly(raw,conker/'retail_layout.us.txt','generated_1D4E00',word_patches_path=guards)}
for label,text in texts.items():
 asm=out/(label+'-padded.s');obj=out/(label+'-padded.o');asm.write_text(text);subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(conker)),str(asm.relative_to(conker))],cwd=conker,capture_output=True,check=True)
 assert struct.pack('>373I',*bound_blob(*payload(obj,name),symbols))==truth and same_functions(conker/'build/src/game/generated_1D4E00.c.o',obj,(name,))==22
def link(obj,target,defs,label):
 _,fs,_=pg.parse_object(obj);offset=fs[name]['value'];script=out/(label+'.ld');elf=out/(label+'.elf');binary=out/(label+'.bin');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
 lines=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();names=[line.split()[-1] for line in lines if line.split()];assert set(names)<=set(defs),set(names)-set(defs)
 args=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,*[x for n in names for x in ('--defsym',n+'='+hex(defs[n]))],'-o',str(elf),str(obj)];p=subprocess.run(args,capture_output=True,text=True);assert p.returncode==0,p.stderr;subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
 return binary.read_bytes()[offset:offset+1492]
layouts=(0x15000000,0x17000000,0x19000000,0x1b000000)
for i,region in enumerate(layouts):
 target=region+0x1a7d6c
 defs=dict(symbols,D_80090D70=0x33007ffc+i*0x10000,D_800D2C9C=0x33018004+i*0x10000,D_800A4AC8=0x33027ff8+i*0x10000);defs.update({name:region+(address-0x15000000) for name,address in symbols.items() if name in ('func_151D5D60','func_15144B34','func_15142E24','func_15142B7C','func_15142C10','func_1513F4E4','func_15142FBC','func_15145548')})
 a=link(out/'retail.o',target,defs,f'link-{i}-retail')
 for label in texts:assert a==link(out/(label+'-padded.o'),target,defs,f'link-{i}-{label}')
installed='Gfx *func_151A7D6C(Gfx *output' in (conker/'src/game/generated_1D4E00.c').read_text()
report={'padders':2,'layouts':len(layouts),'gnu_links':12,'owner_neighbors':22,'installed':installed};(out/'pad-rebase.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
