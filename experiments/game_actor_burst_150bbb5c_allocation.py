"""Owned-child actor-burst allocation diagnostics; no source/profile installation.

UOPT timing/real-number output is suppressed and cannot support numeric cost or
performance claims. Only scoped integer metadata and independently identical
emitted objects qualify these observations. Internal colors are not a universal
mapping to architectural registers.
"""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,re,shutil
from tools.experiments import game_actor_burst_150bbb5c_full as source
from tools.experiments import game_text_measurer_uopt_trace as uopt
from tools.experiments import game_text_measurer_ugen_nodes as ugen
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools

ROOT=source.ROOT
PACKET=ROOT/'conker/build/game-next-150bbb5c-physical-private'
FROZEN=PACKET/'baseline'
OUT=Path(os.environ.get('CBFD_ACTOR_BURST_150BBB5C_ALLOCATION_WORK',PACKET/'qualification-primary'))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
BASELINE_SHA256='b2c0b8bd84f146ac27192fe2f67824336c8f1c29619d27300eeafd2535dd2c94'
NAME = source.NAME
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()

def check_inputs():
 assert sha(FROZEN/'fingerprints.json')==BASELINE_SHA256
 pins=json.loads((FROZEN/'fingerprints.json').read_text())['inputs'];assert len(pins)==1879
 for name,digest in pins.items():assert sha(ROOT/name)==digest,name
 return len(pins)

def descriptor_record(text):
 begin=text.index('LOCAL OPTIMIZATION OF '+NAME)
 end=text.index('LOCAL OPTIMIZATION OF func_150BC488',begin)
 section=text[begin:end]
 chunks=re.split(r'(?m)(?=^>>>active<<<)',section)
 found=[]
 for block in chunks:
  match=re.match(r'^>>>active<<<\{(\d+\|\d+)\}\s+(\d+)\s+(-?\d+)\nconst------>\n\s*(\d+)\s+(-?\d+)\n',block)
  if match and (int(match[4]),int(match[5]))==(771,-124):
   parsed=uopt.allocation_constraints(block);assert len(parsed)==1
   found.append(dict(parsed[0],procedure=int(match[4]),stack_offset=int(match[5])))
 assert len(found)==1,('unique scoped descriptor constant required',len(found))
 return found[0]

def qualify():
 check_inputs();OUT.mkdir(parents=True,exist_ok=False)
 before=(FROZEN/source.SOURCE).read_text();body=source.recover(before)
 initial,diag=compile_owner(ROOT,OUT,before,'owner-before');assert not diag,diag
 def baseline(root,work,name,text):
  obj,diag=compile_owner(root,work,text,name);assert not diag,diag
  assert same_functions(initial,obj,(NAME,))==8
  assert normalized_pools(initial)==normalized_pools(obj)
  raw,refs=payload(obj,NAME)
  if text==body:
   assert hashlib.sha256(raw).hexdigest()==source.PIN['raw_sha256']and refs==source.refs(source.PIN['refs'])
  return dict(raw_sha256=hashlib.sha256(raw).hexdigest(),words=len(raw)//4,neighbors_unchanged=8),None
 reports={}
 profiles=dict(uopt.screen.PROFILES,owner=('-O2','-g3'))
 with patch.object(uopt.screen,'compile_candidate',baseline),patch.object(uopt.screen,'PROFILES',profiles):
  for mode in(5,6):reports['uopt'+str(mode)]=uopt.trace_uopt(ROOT,OUT,'uopt'+str(mode),body,mode)
  reports['ugen_full']=ugen.trace_nodes(ROOT,OUT,'ugen-full',body)
  reports['ugen_stub']=ugen.trace_nodes(ROOT,OUT,'ugen-stub',before)
 assert all(row['code_unchanged']for row in reports.values())
 record=descriptor_record((OUT/'uopt5/uoptlist').read_text())
 assert record['identity']=='43|1'and record['expression']==499 and record['color']==18
 assert record['forbidden']==[1,2,3,4,5,6,14,15,16,17]
 counts={name:sum(e['type_storage']>>5==3 and e['raw44']==80 for e in reports[name]['events'])for name in('ugen_full','ugen_stub')}
 assert counts==dict(ugen_full=3,ugen_stub=0)
 assert reports['ugen_full']['event_count']==296 and reports['ugen_stub']['event_count']==121
 raw,_=payload(OUT/'ugen-full/baseline.o',NAME);words=[int.from_bytes(raw[i:i+4],'big')for i in range(0,len(raw),4)]
 assert len(words)==591 and words[4]==0xAFB40090 and words[588]==0x8FB40090
 assert [(i*4,w)for i,w in enumerate(words)if w==0x27B401F4]==[(680,0x27B401F4),(1208,0x27B401F4)]
 assert sum(w==0x02802025 for w in words)==2
 report=dict(passes=True,descriptor_constant=record,ugen_event_counts={k:reports[k]['event_count']for k in counts},
  s4_register_nodes=counts,all_objects_unchanged=True,neighbors_unchanged=8,raw_sha256=source.PIN['raw_sha256'],
  raw_words=591,frame=624,full_normal_receipts_reused=True,source_installed=False,profile_installed=False,c_match_credit=0,
  compiler_fingerprints=ugen.compiler_fingerprints(ROOT),timing_cost_numbers_valid=False)
 (OUT/'allocation-report.json').write_text(json.dumps(report,indent=2)+'\n')
 check_inputs();return report

def rejection_controls():
 row=OUT/'uopt5';log=(row/'debugger.txt').read_text();results=[]
 forms=(('failed-driver',1,log,False),('missing-driver-exit',0,log.replace(uopt.EXIT_MARKER,''),False),
        ('changed-emitted-text',0,log,True))
 for label,code,record,mutate in forms:
  work=OUT/'controls'/label;work.mkdir(parents=True,exist_ok=False)
  for name in('baseline.o','trace.o','uoptlist'):shutil.copyfile(row/name,work/name)
  if mutate:
   path=work/'trace.o';blob=bytearray(path.read_bytes());raw,_=payload(path,NAME)
   at=blob.find(raw);assert at>=0 and blob.find(raw,at+1)<0
   blob[at+3]^=1;path.write_bytes(blob)
  try:uopt.validate_trace(ROOT,work,code,record)
  except ValueError:results.append(dict(label=label,rejected=True))
  else:raise AssertionError(('ineffective diagnostic rejection control',label))
 report=dict(passes=True,effective_controls=len(results),controls=results,source_installed=False,c_match_credit=0)
 (OUT/'diagnostic-controls.json').write_text(json.dumps(report,indent=2)+'\n');return report

def reused_semantic_receipts():
 check_inputs();old=ROOT/'conker/build/game-next-150bbb5c-trail-private';pins=json.loads((FROZEN/'fingerprints.json').read_text())['inputs']
 result={}
 for label in('primary','sibling'):
  row=json.loads((old/(label+'-suite.json')).read_text())
  assert row['passes']and row['tests']==5 and row['imported_tool_files']==341
  for name,meta in row['imports'].items():assert pins['tools/'+name]==meta['sha256']and sha(ROOT/'tools'/name)==meta['sha256'],name
  for name,digest in row['task_sha256'].items():assert pins['tools/'+name]==digest
  result[label]=dict(freshly_rerun=False,tests=5,imports=341,receipt_sha256=sha(old/(label+'-suite.json')))
 return result
