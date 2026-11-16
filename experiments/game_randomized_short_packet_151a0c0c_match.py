"""Complete particle request, source-provenance schedule and exact gates."""
from pathlib import Path
from unittest.mock import patch
import csv,hashlib,io,json,os,struct,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
OUT=ROOT/'conker/build/game-randomized-short-packet-151a0c0c-private/proof-2489'
FROZEN=OUT.parent/'production-baseline'
NAME='func_151A0C0C'
SOURCE='conker/src/game/generated_1CC440.c'
ENTRY,ROM,SIZE=0x151A0C0C,0x1CE0BC,564
PIN=json.loads(Path(__file__).with_name('game_randomized_short_packet_151a0c0c_manifest.json').read_text())
assert len(PIN['order'])==141 and sorted(row['source']for row in PIN['order']if row['kind']=='instruction')==list(range(0,560,4))

def recover(before,prior=False):
 stub='s32 func_151A0C0C() {\n    return 0;\n}';assert before.count(stub)==1
 return before.replace(stub,PIN['prior_declarations'if prior else'declarations']+'\n'+PIN['prior_source'if prior else'source'])

def check_inputs():
 before=(FROZEN/SOURCE).read_text();live=(ROOT/SOURCE).read_text();installed=live==recover(before);assert installed or live==before
 record=json.loads((FROZEN/'fingerprints.json').read_text());plan=json.loads((OUT/'adoption-plan.json').read_text())if installed else{}
 if installed:assert set(plan)=={SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_1CC440.c.o','conker/build/conker.us.elf'}
 for n,h in record['inputs'].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==plan.get(n,h),n
 return installed

def compile_and_check():
 OUT.mkdir(parents=True,exist_ok=True);installed=check_inputs();before=(FROZEN/SOURCE).read_text()
 baseline,diagnostics=compile_owner(ROOT,OUT,before,'baseline');assert not diagnostics
 for prior,label in((False,'qualified'),(True,'prior')):
  obj,diagnostics=compile_owner(ROOT,OUT,recover(before,prior),label);assert not diagnostics
  assert same_functions(baseline,obj,(NAME,))==38
  assert normalized_pools(baseline)['.data']==normalized_pools(obj)['.data']
  if not prior:assert normalized_pools(baseline)==normalized_pools(obj)
 raw,refs=payload(OUT/'qualified.o',NAME);assert hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']
 assert {str(k):v for k,v in refs.items()}=={k:[tuple(v)for v in rows]for k,rows in PIN['raw_refs'].items()}
 (OUT/'proposed-owner.c').write_text(recover(before));check_inputs();return installed

def fields(w):
 op,fn,fmt=w>>26,w&63,w>>21&31
 if op==0:shifts=(11,)if fn in(16,18)else(21,)if fn==8 else(16,11)if fn in(0,2,3)else(21,16,11)if fn in(33,35,36,37,42,43)else(21,16)if fn in(25,27)else None
 elif op==17:shifts=(16,)if fmt in(0,4)else()
 elif op==3:shifts=()
 elif op==15:shifts=(16,)
 elif op in(49,53,57,61):shifts=(21,)
 elif op in(4,5,9,10,11,12,13,32,33,35,36,37,40,41,43):shifts=(21,16)
 else:shifts=None
 assert shifts is not None,hex(w)
 return sum(31<<shift for shift in shifts if w>>shift&31 not in(0,29,31))
def key(w,refs):
 mask=fields(w);branch=w>>26 in(4,5)
 return w&~(mask|(65535 if branch else 0)),tuple(refs)
def project(raw,refs,pin):
 if hashlib.sha256(raw).hexdigest()!=pin['raw_sha256']or{str(k):v for k,v in refs.items()}!={k:[tuple(v)for v in rows]for k,rows in pin['raw_refs'].items()}:raise ValueError('Compiler words or bindings changed')
 words=list(struct.unpack('>140I',raw));out=[];bindings={}
 for row in pin['order']:
  at=row['source'];w=words[at//4]
  if row['kind']=='split-result-copy':
   assert w>>26==9 and w&65535==250
   producer=row['producer']//4;v=out[producer];assert v>>26==9 and v&65535==250
   src=v>>16&31;dest=row['destination'];assert src not in(0,29,31) and dest not in(0,29,31)
   # No intervening instruction changes the produced register before its copy.
   assert producer<len(out) and len(out)-producer==4
   for item in out[producer+1:]:
    op,fmt,fn=item>>26,item>>21&31,item&63
    changed=(item>>11&31,)if op==0 and fn in(0,2,3,33,35,36,37,42,43,16,18)else(item>>16&31,)if op in(9,10,11,12,13,15,32,33,35,36,37)or(op==17 and fmt==0)else()
    assert src not in changed,('split-result value killed before copy',src,hex(item))
   w=(src<<21)|(dest<<11)|37
  else:
   assert row['kind']=='instruction';mask=fields(w);assert row['operands']&~mask==0
   w=(w&~mask)|row['operands']
   if row.get('target')is not None:
    assert w>>26 in(4,5);delta=row['target']-(4*len(out)+4);assert delta%4==0;w=(w&0xFFFF0000)|((delta//4)&65535)
   if at in refs:bindings[4*len(out)]=refs[at]
  out.append(w)
 copies=[row for row in pin['order']if row['kind']=='split-result-copy'];assert len(copies)==1
 copy=copies[0];origin=copy['source']//4;reg=words[origin]>>16&31
 consumers=[i for i in range(origin+1,len(words))if words[i]>>26==41 and words[i]>>21&31==29 and words[i]>>16&31==reg and words[i]&65535 in(108,110)]
 assert len(consumers)==2 and {words[i]&65535 for i in consumers}=={108,110}
 for item in words[origin+1:max(consumers)+1]:
  op,fmt,fn=item>>26,item>>21&31,item&63;assert op not in(3,4,5)
  changed=(item>>11&31,)if op==0 and fn in(0,2,3,33,35,36,37,42,43,16,18)else(item>>16&31,)if op in(9,10,11,12,13,15,32,33,35,36,37)or(op==17 and fmt==0)else()
  assert reg not in changed,('source result killed before packet consumers',reg,hex(item))
 projected=[i for i,row in enumerate(pin['order'])if row['kind']=='instruction'and row['source']//4 in consumers]
 assert len(projected)==2 and all(out[i]>>26==41 and out[i]>>16&31==copy['destination']for i in projected)
 return struct.pack('>141I',*out),bindings

def normalize(raw,refs):
 normal,bindings=project(raw,refs,PIN)
 assert hashlib.sha256(normal).hexdigest()==PIN['normal_sha256']
 assert {str(k):v for k,v in bindings.items()}=={k:[tuple(v)for v in rows]for k,rows in PIN['normal_refs'].items()}
 return normal,bindings

def symbols():return{name:int(name.split('_',1)[1],16)for rows in PIN['normal_refs'].values()for kind,name in rows}

def programs():
 syms=symbols();raw,refs=payload(OUT/'qualified.o',NAME);normal,bindings=normalize(raw,refs)
 prior,prefs=payload(OUT/'prior.o',NAME)
 return dict(retail=(list(struct.unpack_from('>141I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)),None),prior=(bound_blob(prior,prefs,{**syms,'.rodata':0x80400000}),sections(OUT/'prior.o')['.rodata'][1]),candidate=(bound_blob(raw,refs,syms),sections(OUT/'qualified.o')['.rodata'][1]),guarded=(bound_blob(normal,bindings,syms),sections(OUT/'baseline.o')['.rodata'][1]))

def assemble(label,text):
 path=OUT/(label+'.s');obj=path.with_suffix('.o');path.write_text(text)
 p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=ROOT/'conker',capture_output=True,text=True);assert p.returncode==0 and not p.stderr,p.stderr;return obj

def main():
 installed=compile_and_check();raw,refs=payload(OUT/'qualified.o',NAME);normal,nrefs=normalize(raw,refs);syms=symbols();truth=programs()['retail'][0]
 assert bound_blob(normal,nrefs,syms)==truth
 from tools.tests import game_randomized_short_packet_151a0c0c_proof as proof
 literals={syms['D_800A8D14']:0x43FB8000,syms['D_800A8D18']:0x44484000}
 assert proof.prove(bound_blob(raw,refs,syms),truth,literals,literals)['whole_function']
 negative=0
 for i in range(140):
  changed=bytearray(raw);changed[4*i+3]^=1
  try:normalize(bytes(changed),refs)
  except ValueError:negative+=1
  else:raise AssertionError(('changed word accepted',i))
 for at,rows in refs.items():
  try:normalize(raw,{**refs,at:[(kind,name+'_bad')for kind,name in rows]})
  except ValueError:negative+=1
  else:raise AssertionError(('changed binding accepted',at))
 before=(FROZEN/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(before.decode())))
 assert not any(row['function']==NAME for row in csv.DictReader(io.StringIO(before.decode())))
 rw=struct.unpack('>140I',raw);nw=struct.unpack('>141I',normal);rows=[]
 reloc=lambda values:';'.join(kind+':'+name for kind,name in values)or'-'
 for i,w in enumerate(rw):
  at=4*i;target=4*(i if i<90 else i+1);insert=i==89
  rows.append(dict(filename='generated_1CC440',function=NAME,offset='0x%X'%at,expected='0x%08X'%w,replacement='0x%08X'%nw[target//4],expected_relocations=reloc(refs.get(at,[])),replacement_relocations=reloc(nrefs.get(target,[])),note='Preserve proved particle packet allocation and schedule; one split-result copy',insert_after='0x%08X'%nw[90]if insert else'',insert_after_relocations='-'if insert else'',omit='false'))
 stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n'if b'\r\n'in before else'\n').writerows(rows)
 guards=OUT/'proposed-guards.csv';guards.write_bytes(before+stream.getvalue().encode());padded=[]
 for label,text in(('layout',pc.emit_padded_assembly(OUT/'qualified.o',ROOT/'conker/retail_layout.us.txt','generated_1CC440',word_patches_path=guards)),('strict',pg.emit_padded_assembly(OUT/'qualified.o',ROOT/'conker/asm/1CC440.s',filename='generated_1CC440',word_patches_path=guards))):
  obj=assemble(label,text);assert payload(obj,NAME)==(normal,nrefs)
  assert same_functions(FROZEN/'conker/build/src/game/generated_1CC440.c.o',obj,(NAME,))==38
  assert normalized_pools(obj)==normalized_pools(FROZEN/'conker/build/src/game/generated_1CC440.c.o');padded.append(obj)
 rebases=[]
 for ordinal,base in enumerate((syms['D_800A8D14'],0x800AFFFC,0x80117FFC)):
  moved={name:value+(ordinal+1)*(i+1)*0x10000 for i,(name,value)in enumerate(sorted(syms.items()))};moved['D_800A8D14']=base;moved['D_800A8D18']=base+4
  a,b=bound_blob(raw,refs,moved),bound_blob(normal,nrefs,moved)
  for obj in padded:assert bound_blob(*payload(obj,NAME),moved)==b
  literals={base:0x43FB8000,base+4:0x44484000}
  with patch.multiple(proof,RNG=moved['func_150ADA20'],FLOAT=moved['func_150ADA68'],SINE=moved['func_151423D8'],SUBMIT=moved['func_15167D84']):assert proof.prove(a,b,literals,literals)['whole_function']
  rebases.append(base)
 check_inputs();report=dict(raw_words=140,normalized_words=141,frame=128,word_guards=140,inserted_words=1,omitted_words=0,all_source_operations_retained_once=True,split_result_copy_source=0x16C,corruption_controls=negative,padders=2,independent_rebases=rebases,neighbors_unchanged=38,pools_unchanged=True,source_installed=installed,c_match_credit=int(installed))
 (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
