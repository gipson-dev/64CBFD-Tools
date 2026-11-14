"""Compare both owner padders and original assembly under four rebases."""
from pathlib import Path
import json, re, struct, subprocess, sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-effect-dispatch-150b3ab0-durable';conker=root/'conker'
name='func_150B3AB0'; raw=out/'candidate-12.o';orig=(conker/'asm/E0F60.s').read_text()
symbols={r[1]:r[2][1] for r in symbol_rows((out/'frozen/conker/build/conker.us.elf').read_bytes())}
truth=(conker/'conker.us.bin').read_bytes()[0xe0f60:0xe10bc]
match=re.search(r'^glabel '+name+r'\n.*?^endlabel '+name+r'\s*$',orig,re.M|re.S);assert match
texts={'retail':'.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+match.group()+'\n.size '+name+',.-'+name+'\n',
       'generated':pg.emit_padded_assembly(raw,conker/'asm/E0F60.s',filename='generated_E0F60',word_patches_path=conker/'retail_word_patches.us.csv'),
       'c':pc.emit_padded_assembly(raw,conker/'retail_layout.us.txt','generated_E0F60',word_patches_path=conker/'retail_word_patches.us.csv')}
for label,text in texts.items():
 asm=out/(label+'-check.s');obj=out/(label+'-check.o');asm.write_text(text)
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(conker)),str(asm.relative_to(conker))],cwd=conker,capture_output=True,check=True)
 assert struct.pack('>87I',*bound_blob(*payload(obj,name),symbols))==truth
 if label!='retail':assert same_functions(conker/'build/src/game/generated_E0F60.c.o',obj,(name,))==1
def link(obj,target,defs,label):
 _,fs,_=pg.parse_object(obj);offset=fs[name]['value'];script=out/(label+'.ld');elf=out/(label+'.elf');binary=out/(label+'.bin')
 script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
 lines=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines();names=[line.split()[-1] for line in lines if line.split()];assert set(names)<=set(defs),set(names)-set(defs)
 args=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,*[x for n in names for x in ('--defsym',n+'='+hex(defs[n]))],'-o',str(elf),str(obj)]
 p=subprocess.run(args,capture_output=True,text=True);assert p.returncode==0,p.stderr
 subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
 return binary.read_bytes()[offset:offset+348]
layouts=((0x150b3ab0,0x800a7ffc),(0x170b3ab0,0x8010fff0),(0x190b3ab0,0x80218000),(0x1b0b3ab0,0x8031fffc))
for i,(target,base) in enumerate(layouts):
 defs=dict(symbols)
 for j,n in enumerate(('D_800BE9E8','D_800DBFF0','D_8009FBC0')):defs[n]=base+4*j
 for j,n in enumerate(('func_1512D748','func_15143134','func_150ADA20','func_1514C858','func_151D8868','func_151D3FF4')):defs[n]=(target&0xf0000000)|0x01000000|j*0x100
 a=link(out/'retail-check.o',target,defs,f'link-{i}-retail')
 for label in ('generated','c'):assert a==link(out/(label+'-check.o'),target,defs,f'link-{i}-{label}')
report={'padders':2,'layouts':len(layouts),'gnu_links':len(layouts)*3,'neighbors_unchanged':1,'uncredited':True}
(out/'pad-rebase-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
