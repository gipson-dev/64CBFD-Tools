"""Closed register alias proof, both padders, faults and independent bindings."""
import csv,hashlib,json,struct,subprocess,sys
from dataclasses import replace
from tools.tests import game_actor_state_dispatch_1506045c_oracle as g
from tools.experiments import game_actor_state_dispatch_1506045c_match as p
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
SHA='592dd571ec252c522e1130a205e53701fde3d9432a7b9cd22bdf9f82b94608c3'
normalize=p.normalize
def static_proof(ws):
 assert ws[76]==0x01002825 and ws[131]==0x10A0001B
 edges={i:set()for i in range(199)}
 for i,w in enumerate(ws):
  op,rs,rt=w>>26,w>>21&31,w>>16&31
  if op==0 and w&63==8:edges[i].add(i+1);continue
  if op in(2,3):
   assert op==3;edges[i].add(i+1);edges[i+1].add(i+2);continue
  if op in(1,4,5,6,7,20,21,22,23):
   target=i+1+(((w&65535)^32768)-32768);likely=op in(20,21,22,23)or op==1 and rt&2
   edges[i].add(i+1);edges[i+1].add(target)
   always=op in(4,20)and rs==rt
   if not always:edges[i if likely else i+1].add(i+2)
  elif i==0 or i-1 not in range(199)or ws[i-1]>>26 not in(1,2,3,4,5,6,7,20,21,22,23)and not(ws[i-1]>>26==0 and ws[i-1]&63==8):
   if i+1<199:edges[i].add(i+1)
 reachable={0};pending=[0]
 while pending:
  for j in edges[pending.pop()]:
   assert 0<=j<199
   if j not in reachable:reachable.add(j);pending.append(j)
 pred={i:{j for j in reachable if i in edges[j]}for i in reachable};dom={i:({0}if i==0 else set(reachable))for i in reachable}
 while True:
  nxt={i:({0}if i==0 else{i}|set.intersection(*(dom[j]for j in pred[i])))for i in reachable}
  if nxt==dom:break
  dom=nxt
 assert 76 in dom[131]
 for i in range(77,131):
  w=ws[i];op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
  assert op not in(2,3)
  written=rd if op==0 and fn not in(8,12,13,17,19,24,25,26,27)else rt if op in(8,9,10,11,12,13,14,15,32,33,35,36,37)else None
  assert written not in(5,8),(i,hex(w),written)
 return dict(copy_word=76,branch_word=131,copy_dominates_branch=True,no_intervening_alias_register_writes=True,closed_one_word_change=True)
def assemble(text,label):
 s=p.out/(label+'.s');s.write_text(text);obj=s.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(s)],cwd=p.root/'conker',capture_output=True,check=True);return obj
def emit(raw,refs,label):
 text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+p.NAME+'\n.type '+p.NAME+',@function\n'+p.NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(i*4,[]):text+='.reloc ., '+kind+', '+name+'\n'
  text+='.word 0x%08X\n'%w
 return assemble(text+'.size '+p.NAME+',.-'+p.NAME+'\n',label)
def row():return dict(filename='game_83300',function=p.NAME,offset='0x20C',expected='0x10A0001B',replacement='0x1100001B',expected_relocations='-',replacement_relocations='-',note='Use the identical preserved overlay-byte register at the recursive gate',insert_after='',insert_after_relocations='',omit='false')
def padders(raw,refs):
 obj=emit(raw,refs,'target-raw');r=row();guard=p.out/'target-guards.csv'
 def guards(record):
  with guard.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=list(record));w.writeheader();w.writerow(record)
 guards(r);lines=(p.root/'conker/retail_layout.us.txt').read_text().splitlines();chosen=[l for l in lines[1:]if l.split(',')[1:3]==['game_83300',p.NAME]];assert len(chosen)==1;layout=p.out/'target-layout.csv';layout.write_text(lines[0]+'\n'+chosen[0]+'\n');asm=p.root/'conker/asm/nonmatchings/game_83300/func_1506045C.s'
 generic=lambda:pad_c_object.emit_padded_assembly(obj,layout,'game_83300',word_patches_path=guard)
 generated=lambda:pad_generated_object.emit_padded_assembly(obj,asm,filename='game_83300',word_patches_path=guard)
 a=assemble(generic(),'target-generic');b=assemble(generated(),'target-generated');assert p.payload(a)==p.payload(b)==normalize(raw,refs)
 stale=dict(r);stale['expected']='0x10A0001A';guards(stale);rejected=0
 for fn in(generic,generated):
  try:fn()
  except ValueError:rejected+=1
  else:raise AssertionError('Stale guard accepted')
 guards(r);assert rejected==2
 corruptions=0
 for i in range(199):
  wrong=bytearray(raw);wrong[4*i+3]^=1
  try:normalize(bytes(wrong),refs)
  except ValueError:corruptions+=1
  else:raise AssertionError(i)
 for offset,values in refs.items():
  wrong=dict(refs);wrong[offset]=[(kind,name+'_stale')for kind,name in values]
  try:normalize(raw,wrong)
  except ValueError:corruptions+=1
  else:raise AssertionError(offset)
 return dict(both_padders=True,stale_guard_rejections=2,word_and_binding_corruptions=corruptions)
def rebases():
 asm=(p.root/'conker/asm/nonmatchings/game_83300/func_1506045C.s').read_text();reference=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm+'\n.size '+p.NAME+',.-'+p.NAME+'\n','original-reference')
 attrs=('ENTRY','QUERY','DISPATCH','FINAL','DISABLED','TICKS','MODE','CONTROL_PTR','TABLE','COUNTS');before={n:getattr(g,n)for n in attrs};runs=0
 def bind(path,s):raw,refs=p.payload(path);return g.bound_blob(raw,refs,s)
 try:
  for low in(0,0x7FFC,0x8000,0xFFFC):
   for i,n in enumerate(('ENTRY','QUERY','DISPATCH','FINAL')):setattr(g,n,0x1516045C+i*0x1000)
   for i,n in enumerate(('DISABLED','TICKS','MODE','CONTROL_PTR','TABLE')):setattr(g,n,0x80300000+i*0x10000+low)
   g.COUNTS={g.ENTRY:5,g.QUERY:1,g.DISPATCH:9,g.FINAL:5}
   s=dict(zip(('func_1506045C','func_15080738','func_15065A5C','func_150642AC','D_800C35EA','D_800BE9E4','D_800BE9F0','D_800CC284','D_800CBFA8'),[getattr(g,n)for n in attrs[:-1]]))
   for path in(p.out/'selected.o',p.out/'target-generic.o',reference):
    ws=bind(path,s)
    for c in(g.Case(),g.Case(controls=32,query=1,mutation=1),g.Case(overlay=0x89,flags=0x4000,mutation=28),g.Case(timer=65535,ticks=0x80000000),g.Case(identity=26,category=35)):
     m=g.Oracle(ws,g.fixture(c),c);m.run();g.check(m,c);runs+=1
 finally:
  for n,v in before.items():setattr(g,n,v)
 return dict(executions=runs,independent_symbol_sets=4,raw_normalized_original=True)
def faults():
 programs=(g.words(p.out/'selected.o'),struct.unpack_from('>199I',(p.root/'conker/conker.us.bin').read_bytes(),0x8D90C));pairs=0
 for c in(g.Case(),g.Case(controls=32,query=1,mutation=1),g.Case(overlay=0x89,flags=0x4000,mutation=4),g.Case(overlay=0x89,flags=0x4000,mutation=28)):
  complete=g.Oracle(programs[0],g.fixture(c),c);complete.run()
  for cut in range(complete.all_accesses):
   models=[]
   for ws in programs:
    m=g.Oracle(ws,g.fixture(c),c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Guest cut not reached')
    models.append(m)
   a,b=models;assert(a.memory,a.r,a.f,a.calls,a.trace,a.current_pc,a.delay_of)==(b.memory,b.r,b.f,b.calls,b.trace,b.current_pc,b.delay_of),(c,cut);pairs+=1
 return dict(exact_instruction_access_cut_pairs=pairs,portable_C_fault_semantics_qualified=False)
def main():
 raw,refs=p.payload(p.out/'selected.o');proof=static_proof(g.words(p.out/'selected.o'));result=dict(proof=proof,padders=padders(raw,refs),rebases=rebases(),faults=faults());(p.out/'boundaries.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
