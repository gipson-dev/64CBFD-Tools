"""Private attached-actor accumulator; production is intentionally unchanged."""
from pathlib import Path
import hashlib,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows,elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
PACKET=ROOT/'conker/build/game-next-150ba55c-private';BASE=PACKET/'baseline'
OUT=Path(os.environ.get('CBFD_ATTACHED_ACCUMULATOR_WORK',PACKET/'qualification-primary'))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
PIN=json.loads(Path(__file__).with_name('game_attached_accumulator_150ba55c_manifest.json').read_text())
NAME,SOURCE,ASM,ENTRY,ROM,SIZE=(PIN[k]for k in('name','source','asm','entry','rom','size'))
STUB='s32 func_150BA55C() {\n    return 0;\n}'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def inputs():
 assert sha(BASE/'fingerprints.json')==PIN['baseline_manifest_sha256']
 rows=json.loads((BASE/'fingerprints.json').read_text())['inputs'];assert len(rows)==1800
 for n,h in rows.items():assert sha(ROOT/n)==h,n
 return rows
def recover(before):
 assert before.count(STUB)==1
 return before.replace(STUB,PIN['declarations']+'\n'+PIN['body'])
def symbols():return{n:f[1]for _,n,f,_ in symbol_rows((BASE/'conker/build/conker.us.elf').read_bytes())}
def qualify():
 inputs();OUT.mkdir(parents=True,exist_ok=False);before=(BASE/SOURCE).read_text()
 a,ad=compile_owner(ROOT,OUT,before,'baseline');b,bd=compile_owner(ROOT,OUT,recover(before),'candidate');assert not ad and not bd,(ad,bd)
 assert same_functions(a,b,(NAME,))==5 and normalized_pools(a)==normalized_pools(b)
 raw,refs=payload(b,NAME);assert len(raw)==916 and hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']
 assert refs=={int(k):[tuple(v)for v in values]for k,values in PIN['refs'].items()}
 text=(BASE/ASM).read_text();fragment='glabel '+NAME+'\n'+text.split('glabel '+NAME+'\n')[1].split('endlabel '+NAME)[0]+'.size '+NAME+',.-'+NAME+'\n'
 assembly=OUT/'original.s';assembly.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(assembly.with_suffix('.o')),str(assembly)],cwd=ROOT/'conker',capture_output=True,text=True)
 assert not q.returncode and not q.stderr,(q.stdout,q.stderr)
 truth,trefs=payload(assembly.with_suffix('.o'),NAME);lookup=symbols();raw_words=bound_blob(raw,refs,lookup);retail_words=bound_blob(truth,trefs,lookup)
 assert struct.pack('>229I',*retail_words)==(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE]
 state=dict(raw_words=raw_words,retail_words=retail_words);(OUT/'state.json').write_text(json.dumps(state,indent=2)+'\n')
 (OUT/'proposed-owner.c').write_text(recover(before))
 report=dict(passes=True,raw_words=229,retail_words=229,raw_frame=280,retail_frame=264,bindings=39,neighbors_unchanged=5,pools_unchanged=True,source_installed=False,c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');inputs();return report
def state():inputs();return json.loads((OUT/'state.json').read_text())
def census():
 elf=(BASE/'conker/build/conker.us.elf').read_bytes();rom=(ROOT/'conker/conker.us.bin').read_bytes()
 jal=struct.pack('>I',0x0c000000|(ENTRY>>2&0x3ffffff));pointer=struct.pack('>I',ENTRY)
 calls=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal];pointers=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==pointer]
 assert calls==[] and pointers==[0x22f0f0],(calls,pointers)
 at=elf_slot_offset(elf,0x8008a630,4);assert elf[at:at+4]==pointer
 report=dict(passes=True,direct_jal_sites=0,rom_aligned_pointer_literals=['0x22f0f0'],callback_table='D_8008A4E8',index=0x52,actual_dispatcher='func_15149264',callback_return_ignored=True,source_installed=False,c_match_credit=0)
 (OUT/'census.json').write_text(json.dumps(report,indent=2)+'\n');return report
