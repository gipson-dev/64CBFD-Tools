"""Private lifetime candidate and qualified complete-owner allocation capture."""
from pathlib import Path
import hashlib,json,os,re,struct,subprocess,sys
from tools.experiments import game_strip_update_151ad174_private_recovery as source
from tools.experiments import game_text_measurer_uopt_trace as trace
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=source.ROOT;PACKET=source.PACKET;NAME=source.NAME
QUALIFICATION=PACKET/'lifetime-final';FROZEN=PACKET/'lifetime-final-baseline'
OUT=Path(os.environ.get('CBFD_STRIP_UPDATE_LIFETIME_WORK',str(QUALIFICATION/'qualification-primary')))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
PIN=json.loads(Path(__file__).with_name('game_strip_update_151ad174_lifetime_manifest.json').read_text())
def check_inputs():
 inputs=json.loads((FROZEN/'fingerprints.json').read_text())['inputs'];assert len(inputs)==PIN['frozen_input_count']
 for name,h in inputs.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 assert source.STUB in(ROOT/source.SOURCE).read_text();return len(inputs)
def compile_and_check():
 check_inputs();OUT.mkdir(exist_ok=False);before=(source.FROZEN/source.SOURCE).read_text()
 a,diagnostics=source.compile_owner(ROOT,OUT,before,'baseline');assert not diagnostics
 b,diagnostics=source.compile_owner(ROOT,OUT,source.recover(before,PIN['body']),'owner');assert not diagnostics
 raw,refs=payload(b,NAME);assert len(raw)==1960 and hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']
 assert struct.unpack_from('>I',raw)[0]==0x27BDFCF8
 assert refs=={int(k):[tuple(v)for v in a]for k,a in PIN['refs'].items()}
 assert same_functions(a,b,(NAME,))==32 and normalized_pools(a)==normalized_pools(b)
 truth=(source.FROZEN/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SIZE]
 assert hashlib.sha256(truth).hexdigest()==source.PIN['retail_sha256']
 (OUT/'raw.bin').write_bytes(raw);(OUT/'retail.bin').write_bytes(truth);(OUT/'body.txt').write_text(PIN['body'])
 report=dict(raw_words=490,retail_words=494,frame=776,neighbors=32,pools_unchanged=True,source_installed=False,c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');check_inputs();return report
def allocation_facts(text):
 first='IN LOCAL OPTIMIZATION OF '+NAME;last='IN REEMISSION OF '+NAME
 assert text.count(first)==text.count(last)==1
 block=text[text.index(first):text.index(last)+len(last)];variables=trace.variable_expressions(block);constraints=trace.allocation_constraints(block)
 assert {v['storage']for v in variables}=={'M','P','R'}
 assert {v['procedure']for v in variables if v['storage']in('M','P')}=={870}
 registers=[v for v in variables if v['storage']=='R']
 assert len(registers)==2 and {(v['procedure'],v['offset'])for v in registers}=={(0,2),(0,32)}
 indexed={v['expression']:v for v in constraints};assert len(indexed)==len(constraints)
 amplitude=[v for v in variables if v['storage']=='M'and v['offset']==-528];assert len(amplitude)==1
 row=indexed[amplitude[0]['expression']];assert row['identity']==amplitude[0]['identity']and row['color']==30 and row['forbidden']==[24]
 return dict(variable_rows=len(variables),allocation_rows=len(constraints),amplitude=amplitude[0],amplitude_allocation=row,target_sha256=hashlib.sha256(block.encode()).hexdigest(),function_scoped_identity=True)

def capture_allocation():
 r=ROOT;p=PACKET;label='v43';mode=5;w=OUT/'allocation';w.mkdir(exist_ok=False);sha=lambda v:hashlib.sha256(v.read_bytes()).hexdigest();check_inputs();assert trace.compiler_fingerprints(r)==trace.COMPILERS
 normal=OUT/'owner.o';processed=OUT/'owner-processed.c';raw_source=OUT/'owner.c';pins={str(v.resolve()):sha(v)for v in(normal,processed,raw_source,Path(trace.__file__))}
 rel=lambda v:os.path.relpath(v,w);gdb=w/'capture.gdb';gdb.write_text(trace.debugger_script(r))
 args=[rel(r/'ido/ido5.3_recomp/cc'),'-c','-32','-G','0','-Xfullwarn','-Xcpluscomm','-signed','-nostdinc','-non_shared','-Wab,-r4300_mul','-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32','-woff','649,838']
 for include in('.', 'include','include/2.0L','include/2.0L/PR','include/libc','src/libultra/os','src/libultra/audio','src/libultra/io'):args+=['-I',rel(r/'conker'/include)]
 args+=['-O2','-g3','-mips2','-o32','-Wo,-zdbug:'+str(mode),'-o','trace.o',rel(processed)]
 q=subprocess.run(['gdb','-q','--nx','--batch','--iex','set auto-load off','-x',str(gdb),'--args',*args],cwd=w,capture_output=True,text=True);log=q.stdout+q.stderr;(w/'debugger.txt').write_text(log);assert q.returncode==0 and trace.EXIT_MARKER in log.splitlines(),log[-2000:]
 rel_c=lambda v:str(v.relative_to(r/'conker'))
 cmd=[sys.executable,str(r/'tools/asm-processor/asm_processor.py'),'-O2','-g3',rel_c(raw_source),'--post-process',rel_c(w/'trace.o'),'--assembler','mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include','--asm-prelude','include/asm_processor_prelude.inc']
 q=subprocess.run(cmd,cwd=r/'conker',capture_output=True,text=True);(w/'postprocess.txt').write_text(q.stdout+q.stderr);assert q.returncode==0 and not q.stderr,q.stdout+q.stderr
 assert same_functions(normal,w/'trace.o')==33 and normalized_pools(normal)==normalized_pools(w/'trace.o')and payload(normal,source.NAME)==payload(w/'trace.o',source.NAME)
 text=(w/'uoptlist').read_text();assert 'WHOLE UCODE TO UCODE OPTIMIZATION'in text
 assert log.splitlines().count('Allocate diagnostic stream buffer')==1 and 'Suppress diagnostic real-number printer' in log and 'Python Exception'not in log
 facts=allocation_facts(text)
 assert trace.compiler_fingerprints(r)==trace.COMPILERS
 for name,h in pins.items():assert sha(Path(name))==h,name
 check_inputs();report=dict(facts,compiler_sha256=trace.COMPILERS,inputs=pins,all_33_bodies_bindings_pools_identical=True,producer_and_driver_completed=True,debug_real_values_suppressed=True,source_installed=False,c_match_credit=0)
 (w/'capture-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
