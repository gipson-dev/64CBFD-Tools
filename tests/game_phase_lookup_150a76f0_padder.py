"""Both padders and four code layouts for the register-protocol assembly."""
from pathlib import Path
import csv,json,os,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments import game_phase_lookup_150a76f0_restoration as source
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();conker=root/'conker';out=root/source.BUILD;name=source.FUNCTION
texts={'generated':pg.emit_padded_assembly(out/'selected.o',conker/'asm/D4450.s',filename='generated_D4450',word_patches_path=out/'proposed-guards.csv')}
try:pc.emit_padded_assembly(out/'selected.o',conker/'retail_layout.us.txt','generated_D4450',word_patches_path=out/'proposed-guards.csv')
except ValueError as error:
 owner_failure=str(error)
 try:pc.emit_padded_assembly(out/'baseline.o',conker/'retail_layout.us.txt','generated_D4450',word_patches_path=out/'proposed-guards.csv')
 except ValueError as previous:assert str(previous)==owner_failure
 else:raise AssertionError('Strict-owner failure is not pre-existing')
 assert owner_failure=="function mismatch for generated_D4450: missing=[], extra=['D_150A75BC', 'D_150A75F0', 'D_150A760C', 'D_150A7624', 'D_150A763C', 'D_150A7654']"
else:raise AssertionError('Expected the recorded legacy label inventory')
# Isolate the identical compiled target payload; do not relax either padder's
# function-inventory check or rewrite the six unrelated global jump labels.
raw,refs=payload(out/'selected.o',name);assert refs=={} and len(raw)==116
assembly='.text\n.set noat\n.set noreorder\n.globl '+name+'\n.type '+name+',@function\n'+name+':\n'+''.join('.word 0x%08X\n'%w for w in struct.unpack('>29I',raw))+'.size '+name+',.-'+name+'\n'
(out/'isolated.s').write_text(assembly);subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(out/'isolated.o'),str(out/'isolated.s')],capture_output=True,check=True);assert payload(out/'isolated.o',name)==(raw,refs)
with (conker/'retail_layout.us.txt').open() as stream:reader=csv.DictReader(stream);fields=reader.fieldnames;rows=[r for r in reader if r['filename']=='generated_D4450' and r['function']==name]
assert len(rows)==1
with (out/'isolated-layout.csv').open('w',newline='') as stream:writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
texts['c']=pc.emit_padded_assembly(out/'isolated.o',out/'isolated-layout.csv','generated_D4450',word_patches_path=out/'proposed-guards.csv')
for label,text in texts.items():
 (out/(label+'-padded.s')).write_text(text);subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(label+'-padded.o')),str(out/(label+'-padded.s'))],cwd=conker,capture_output=True,check=True)
 if label=='generated':assert same_functions(conker/'build/src/game/generated_D4450.c.o',out/(label+'-padded.o'),(name,))==18
def link(obj,target,label):
 _,functions,_=pg.parse_object(obj);offset=functions[name]['value'];script=out/(label+'.ld');elf=out/(label+'.elf');binary=out/(label+'.bin');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
 undefined=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout;assert not undefined.strip(),undefined
 q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
 subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True);return binary.read_bytes()[offset:offset+128]
truth=(conker/'conker.us.bin').read_bytes()[source.ROM:source.ROM+128]
for i,region in enumerate((0x15000000,0x25000000,0x65000000,0x95000000)):
 target=region+0xa76f0;retail=link(out/'retail.o',target,f'rebase-{i}-retail');assert retail==truth
 for label in texts:assert link(out/(label+'-padded.o'),target,f'rebase-{i}-{label}')==retail
report=dict(padders=2,layouts=4,gnu_links=12,body_words=29,alignment_words=3,owner_neighbors=18,bindings=0,strict_full_owner_failure=owner_failure,strict_target_passes=True);(out/'padder-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
