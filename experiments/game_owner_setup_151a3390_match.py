"""Literal instruction identity, nine bindings and both unchanged-guard padders."""
from pathlib import Path
import csv,hashlib,io,json,struct,subprocess,sys
from tools.experiments import game_owner_setup_151a3390_recovery as m
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_actor_classifier_candidates import sections
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc

def normalize(raw,refs):
 assert hashlib.sha256(raw).hexdigest()==m.PIN['raw_sha256']
 assert {str(k):v for k,v in refs.items()}=={k:[tuple(v)for v in values]for k,values in m.PIN['refs'].items()}
 return raw,refs

def assemble(text,label):
 p=m.OUT/(label+'.s');obj=p.with_suffix('.o');p.write_text(text)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(p)],cwd=m.ROOT/'conker',capture_output=True,text=True)
 assert q.returncode==0 and not q.stderr,q.stderr;return obj

def main():
 m.check_inputs();o,r=m.OUT,m.ROOT;raw,refs=payload(o/'qualified.o',m.NAME);normalize(raw,refs)
 asm=(m.FROZEN/'conker/asm/1D0840.s').read_text();body='glabel '+m.NAME+'\n'+asm.split('glabel '+m.NAME+'\n',1)[1].split('endlabel '+m.NAME,1)[0]
 reference=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+body+'.size '+m.NAME+', .-'+m.NAME+'\n','retail-reference')
 assert payload(reference,m.NAME)==(raw,refs) and bound_blob(raw,refs,m.symbols())==m.retail()
 guards=m.FROZEN/'conker/retail_word_patches.us.csv';old=guards.read_bytes()
 assert not any(row['function']==m.NAME for row in csv.DictReader(io.StringIO(old.decode())))
 (o/'proposed-guards.csv').write_bytes(old)
 emitters=lambda p:(lambda:pc.emit_padded_assembly(o/'qualified.o',r/'conker/retail_layout.us.txt','generated_1D0840',word_patches_path=p),lambda:pg.emit_padded_assembly(o/'qualified.o',r/'conker/asm/1D0840.s',filename='generated_1D0840',word_patches_path=p))
 for label,emit in zip(('layout','strict'),emitters(guards)):
  obj=assemble(emit(),label+'-fitted');assert payload(obj,m.NAME)==(raw,refs)
  baseline=m.FROZEN/'conker/build/src/game/generated_1D0840.c.o';assert same_functions(baseline,obj,(m.NAME,))==22 and normalized_pools(baseline)==normalized_pools(obj)
 corruptions=0
 for i in range(93):
  bad=bytearray(raw);bad[4*i+3]^=1
  try:normalize(bytes(bad),refs)
  except AssertionError:corruptions+=1
  else:raise AssertionError(('raw corruption accepted',i))
 for at,pairs in refs.items():
  try:normalize(raw,{**refs,at:[(kind,name+'_wrong')for kind,name in pairs]})
  except AssertionError:corruptions+=1
  else:raise AssertionError(('binding corruption accepted',at))
 header=next(csv.reader(io.StringIO(old.decode())));row=dict(filename='generated_1D0840',function=m.NAME,offset='0',expected='0x27BDFF69',replacement='0x27BDFF68',expected_relocations='-',replacement_relocations='-',note='Deliberately stale direct-match control',insert_after='',insert_after_relocations='',omit='false')
 stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n'if b'\r\n'in old else'\n').writerow(row)
 stale=o/'stale-guards.csv';stale.write_bytes(old+stream.getvalue().encode());negatives=0
 for emit in emitters(stale):
  try:emit()
  except ValueError:negatives+=1
  else:raise AssertionError('Stale CSV accepted')
 rebases=[]
 for index,delta in enumerate((0x17000,0x29004,0x3F100)):
  moved={name:value+delta*(i+1)for i,(name,value)in enumerate(m.symbols().items())};script=o/('rebase-%d.ld'%index);elf=script.with_suffix('.elf')
  script.write_text('SECTIONS { .text 0x151A3390 : { *(.text) } }\n'+'\n'.join('%s = 0x%X;'%(n,v)for n,v in moved.items()))
  q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',m.NAME,'-o',str(elf),str(reference)],capture_output=True,text=True);assert q.returncode==0,q.stderr
  assert sections(elf)['.text'][1][:372]==struct.pack('>93I',*bound_blob(raw,refs,moved));rebases.append(moved)
 report=dict(raw_words=93,normalized_words=93,frame=152,guards=0,insertions=0,omissions=0,raw_and_binding_corruptions=corruptions,real_CSV_negatives=negatives,independent_GNU_rebases=rebases,whole_owner_padders=2,neighbors_unchanged=22,pools_unchanged=True,source_installed=m.installed(),c_match_credit=0)
 (o/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');m.check_inputs();return report
if __name__=='__main__':print(json.dumps(main()),flush=True)
