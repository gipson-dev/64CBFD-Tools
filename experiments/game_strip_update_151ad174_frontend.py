"""Capture normal CFE/UOPT streams in a newly owned compiler process only."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,subprocess,sys
from tools.experiments import game_text_measurer_frontend_trace as front
from tools.experiments import game_text_measurer_ugen_nodes as trace
from tools.experiments import game_strip_update_151ad174_private_recovery as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=source.ROOT;PACKET=source.PACKET;NAME=source.NAME
QUALIFICATION=PACKET/'frontend-final';FROZEN=PACKET/'frontend-final-baseline'
OUT=Path(__import__('os').environ.get('CBFD_STRIP_UPDATE_FRONT_WORK',str(QUALIFICATION/'qualification-primary')))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
PIN=json.loads(Path(__file__).with_name('game_strip_update_151ad174_frontend_manifest.json').read_text())
def check_inputs():
 record=json.loads((FROZEN/'fingerprints.json').read_text())['inputs'];assert len(record)==PIN['frozen_input_count']
 for name,h in record.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 source.check_inputs();return len(record)
def capture(label):
 r=ROOT;p=PACKET;assert label in PIN['variants'];check_inputs()
 w=OUT/label;w.mkdir(parents=True,exist_ok=False);sha=lambda v:hashlib.sha256(v.read_bytes()).hexdigest()
 expected=dict(trace.qualified.COMPILERS,ugen=trace.UGEN_SHA256,cfe=front.CFE_SHA256);assert front.compiler_fingerprints(r)==expected
 helpers={str(Path(m.__file__).resolve()):sha(Path(m.__file__))for m in(front,trace,trace.qualified)}
 original=(source.FROZEN/source.SOURCE).read_text()
 reference,diagnostics=source.compile_owner(ROOT,w,original,'reference');assert not diagnostics
 normal,diagnostics=source.compile_owner(ROOT,w,source.recover(original,PIN['variants'][label]['body']),'baseline');assert not diagnostics
 assert same_functions(reference,normal,(NAME,))==32 and normalized_pools(reference)==normalized_pools(normal)
 raw=payload(normal,NAME);assert hashlib.sha256(raw[0]).hexdigest()==PIN['variants'][label]['raw_sha256'] and len(raw[0])==4*PIN['variants'][label]['words']
 processed=w/'baseline-processed.c';raw_source=w/'baseline.c';before_inputs={str(v.relative_to(r)):sha(v)for v in(normal,processed,raw_source)}
 script=front.debugger_script(r,w);gdb=w/'capture.gdb';gdb.write_text(script)
 rel=lambda v:str(v.relative_to(r/'conker'))
 args=[str(r/'ido/ido5.3_recomp/cc'),'-c','-32','-G','0','-Xfullwarn','-Xcpluscomm','-signed','-nostdinc','-non_shared','-Wab,-r4300_mul','-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32','-woff','649,838']
 for include in('.', 'include','include/2.0L','include/2.0L/PR','include/libc','src/libultra/os','src/libultra/audio','src/libultra/io'):args+=['-I',include]
 args+=['-O2','-g3','-mips2','-o32','-o',rel(w/'trace.o'),rel(processed)]
 command=['gdb','-q','--nx','--batch','--iex','set auto-load off','-x',str(gdb),'--args',*args]
 run=subprocess.run(command,cwd=r/'conker',capture_output=True,text=True);log=run.stdout+run.stderr;(w/'debugger.txt').write_text(log)
 assert run.returncode==0,log[-2500:]
 events=log.splitlines();assert trace.qualified.EXIT_MARKER in events and trace.CHILD_EXIT in events
 assert events.count(trace.INSTALLED)==events.count(trace.REMOVED)==1
 assert len([s for s in events if s.startswith(trace.PREFIX)])>0
 for token in(front.PREFIX,front.OPTIMIZER_PREFIX,front.TABLE_PREFIX):assert len([s for s in events if s.startswith(token)])==1,token
 capture=json.loads(next(s[len(front.PREFIX):]for s in events if s.startswith(front.PREFIX)))
 optimizer=json.loads(next(s[len(front.OPTIMIZER_PREFIX):]for s in events if s.startswith(front.OPTIMIZER_PREFIX)))
 tables=json.loads(next(s[len(front.TABLE_PREFIX):]for s in events if s.startswith(front.TABLE_PREFIX)))
 assert capture['producer_exits']==[0]and optimizer['producer_exits']==[0]
 assert capture['optimizer_output']==optimizer['input']and optimizer['input']in optimizer['argv']
 assert capture['sha256']==sha(w/'frontend.ucode')and capture['bytes']==(w/'frontend.ucode').stat().st_size
 assert optimizer['sha256']==sha(w/'optimizer.ucode')and optimizer['bytes']==(w/'optimizer.ucode').stat().st_size
 assert tables==dict(descriptors=sha(w/'ucode-table.json'),types=sha(w/'ucode-types.json'))
 assert events.index(next(s for s in events if s.startswith(front.PREFIX)))<events.index(next(s for s in events if s.startswith(front.OPTIMIZER_PREFIX)))<events.index(trace.INSTALLED)<events.index(trace.CHILD_EXIT)<events.index(trace.REMOVED)<events.index(trace.qualified.EXIT_MARKER)
 processor=[sys.executable,str(r/'tools/asm-processor/asm_processor.py'),'-O2','-g3',rel(raw_source),'--post-process',rel(w/'trace.o'),'--assembler','mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include','--asm-prelude','include/asm_processor_prelude.inc']
 run=subprocess.run(processor,cwd=r/'conker',capture_output=True,text=True);(w/'postprocess.txt').write_text(run.stdout+run.stderr);assert run.returncode==0 and not run.stderr
 assert same_functions(normal,w/'trace.o')==33 and normalized_pools(normal)==normalized_pools(w/'trace.o')and payload(w/'trace.o','func_151AD174')==raw
 table=json.loads((w/'ucode-table.json').read_text());types=json.loads((w/'ucode-types.json').read_text());counts={}
 for stage in('frontend','optimizer'):
  records=front.decode_ucode((w/(stage+'.ucode')).read_bytes(),table,types);(w/(stage+'-records.json')).write_text(json.dumps(records,indent=2)+'\n');counts[stage]=dict(records=len(records),opcodes=dict(Counter(v['name']for v in records)))
 assert front.compiler_fingerprints(r)==expected
 for name,h in{**helpers,**before_inputs}.items():assert sha(r/name)==h,name
 check_inputs();report=dict(label=label,compiler_sha256=expected,helper_sha256=helpers,inputs=before_inputs,producer_and_driver_completed=True,table_capture_count=1,unchanged_owner_neighbors=32,all_33_owner_bodies_bindings_and_pools_identical=True,streams=counts,source_installed=False,c_match_credit=0)
 (w/'capture-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(label=label,frontend_records=counts['frontend']['records'],optimizer_records=counts['optimizer']['records'],owner_functions_unchanged=33,source_installed=False,c_match_credit=0)),flush=True)

 return report

def layout(label):
 work=OUT/label;lines=(work/'baseline.c').read_text().splitlines();line=next(i for i,v in enumerate(lines,1)if v.strip()=='last = r->count - 1;');answer={}
 for phase in('frontend','optimizer'):
  rows=json.loads((work/(phase+'-records.json')).read_text());where=None;markers=[]
  for row in rows:
   if row['name']=='loc':where=row['words'][1]
   if where==line and row['name']=='str'and row['storage']=='M'and row['dtype']=='J':markers.append(row)
  if phase=='frontend':assert len(markers)==1;procedure=markers[0]['block']
  at=[i for i,row in enumerate(rows)if row['name']=='ent'and row['block']==procedure];assert len(at)==1
  end=next(i for i in range(at[0]+1,len(rows))if rows[i]['name']=='end');target=rows[at[0]:end+1];definitions=[row for row in target if row['name']=='def'and row['storage']=='M'];assert len(definitions)==1
  accesses=[{k:v[k]for k in('name','storage','dtype','length','offset','block')}for v in target if v['storage']=='M'and v['name']!='def']
  answer[phase]=dict(procedure=procedure,records=len(target),M_bytes=definitions[0]['length'],M_accesses=accesses)
 (work/'target-layout.json').write_text(json.dumps(answer,indent=2)+'\n');return answer
if __name__=='__main__':
 for label in PIN['variants']:capture(label);layout(label)
