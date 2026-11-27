"""Independent ordered reference for the private literal view quad screen."""
from pathlib import Path
import dataclasses,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests import game_axis_quad_vertices_150db2d8_guest as common
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments import game_view_quad_15149d18_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT;fn='func_15149D18';ENTRY=0x15149D18;TABLEX=0x800DD1D8;TABLEZ=0x800DD1E8
Case=common.Case;u32=common.u32;half=common.half;ACTOR=common.ACTOR;BACKEND=common.BACKEND;COPY=common.COPY;ALLOC=common.ALLOC;STACK=common.STACK
rom=common.rom;BUFFER=common.BUFFER;slot=common.slot;public=common.public;state=common.state
def symbols():return dict(common.symbols(),D_800DD1D8=TABLEX,D_800DD1E8=TABLEZ)
def fixture(c):
 m=common.fixture(c)
 for v in {half(c.view),1}:
  put(m,u32(TABLEX+4*v),c.axisX);put(m,u32(TABLEZ+4*v),c.axisZ)
 return m
def reference(initial,c,home=None,initial_fcsr=None):
 m=dict(initial);home=STACK+c.phase if home is None else home;frame=home-72;cur,first,fresh=frame+0x44,frame+0x40,frame+0x37;csr=c.rm if initial_fcsr is None else initial_fcsr;ops=[];calls=[]
 def calc(a,b,fn):
  nonlocal csr
  ops.append((fn,a,b,csr));v,flags=common.arithmetic(a,b,fn,csr&3);csr=(csr&~0x3F000)|flags;return v
 def convert(a):
  nonlocal csr
  ops.append((13,a,0,csr));v,flags=common.trunc(a);csr=(csr&~0x3F000)|flags;return v
 put(m,home+4,u32(c.view));calls.append((BACKEND,(ACTOR+0x100,u32(half(c.view)),64,cur,fresh)))
 if c.connected&4:
  p=read(m,common.slot(c));m[fresh]=0
  if not p:
   calls.append((ALLOC,(128,1,2,1)));p=common.BUFFER if c.success else 0;put(m,common.slot(c),p)
   if p:m[fresh]=1
  answer=u32(p+(0 if c.page else 64))if p else 0
 else:m[fresh]=c.fresh;answer=common.output(c)if c.success else 0
 put(m,cur,answer);common.effect(m,c,BACKEND,0,home);put(m,first,read(m,cur))
 if not read(m,cur):return common.public(m,c),calls,ops,csr,0
 if m[fresh]:
  address=common.slot(c,half(read(m,home+4)));template=ACTOR+0xC0
  for i in range(2):
   dest=u32(read(m,address)+i*64);calls.append((COPY,(dest,template,64)))
   for j in range(64):m[u32(dest+j)]=m[u32(template+j)]
   common.effect(m,c,COPY,i+1,home)
 view=half(read(m,home+4));width=read(m,ACTOR+0x2C)
 forward=calc(read(m,u32(TABLEX+4*view)),width,2);side=calc(read(m,u32(TABLEZ+4*view)),width,2)
 def pair(first_offset,second_offset,value):
  value=convert(value)&65535
  put(m,u32(read(m,cur)+first_offset),value,2);put(m,u32(read(m,cur)+second_offset),value,2)
 pair(0x30,0x00,calc(read(m,ACTOR+0x34),side,0))
 pair(0x12,0x02,read(m,ACTOR+0x38))
 pair(0x34,0x04,calc(read(m,ACTOR+0x3C),forward,1))
 pair(0x20,0x10,calc(read(m,ACTOR+0x34),side,1))
 pair(0x32,0x22,calc(read(m,ACTOR+0x38),read(m,ACTOR+0x30),0))
 pair(0x24,0x14,calc(read(m,ACTOR+0x3C),forward,0))
 return common.public(m,c),calls,ops,csr,read(m,first)
class Machine(common.Machine):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):super().__init__(words,c,memory=fixture(c)if memory is None else memory,entry=ENTRY if entry is None else entry,arguments=arguments,connected=connected)
def check(words,c):
 m=Machine(words,c).run();want=reference(m.initial,c);actual=common.observable(m)
 assert actual==want,dict(case=str(c),components=[a==b for a,b in zip(actual,want)],actual_FP=m.fp_operations,want_FP=want[2],actual_calls=m.calls,want_calls=want[1])
 assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]
 return m
def main():
 files=('original-target.o','selected-owner.o','normalized-target.o','qualified-owner/selected-generic.o','qualified-owner/selected-generated.o')
 streams=[bound_blob(*payload(o/f,fn),symbols())for f in files];assert all(w==streams[0]for w in streams)and len(streams[0])==107
 rows=common.cases();seen=set()
 for c in rows:
  models=[check(w,c)for w in streams];assert all(common.state(m)==common.state(models[0])for m in models[1:]);seen.update(x for x in models[0].visits if ENTRY<=x<ENTRY+428)
 prefixes=0
 for c in(Case(success=0),Case(),Case(fresh=0),Case(mutation=1,redirect=1),Case(connected=5,fresh=1)):
  full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in streams:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError('missing access fault')
    except AccessBoundary:models.append(m)
   assert all(common.state(m)==common.state(models[0])for m in models[1:]);prefixes+=1
 controls=[]
 for name,offset,value,c in[
  ('allocation-size',0x24,0x24060020,Case()),
  ('second-copy-page',0x7C,0x24840030,Case()),
  ('x-first-corner',0xDC,0xA5AB0002,Case()),
  ('lower-y-source',0xE0,0xC6120030,Case()),
  ('upper-y-sign',0x154,0x46083281,Case()),
  ('captured-return',0x194,0x8FA20044,Case(redirect=1))]:
  words=list(streams[0]);assert words[offset//4]!=value,(name,offset);words[offset//4]=value
  changed=Machine(words,c).run();assert common.observable(changed)!=reference(changed.initial,c),name;controls.append(dict(name=name,comparison_mismatch=True))
 missing=sorted(set(range(ENTRY,ENTRY+428,4))-seen);assert not missing,missing
 q=dict(cases_per_stream=len(rows),streams=len(streams),executed_words=len(seen),fault_prefix_quintuples=prefixes,all_literal_full_private_states_equal=True,independent_reference_public_memory_calls_ordered_FP_FCSR_pointer_return_equal=True,reference_private_stack_not_claimed=True,actual52word_backend_and11word_memcpy_connected=True,allocator_opaque=True,guest_aliases_and_private_redirects_not_portable_C=True,finite_FP_model_not_hardware=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0,qualification_remaining='native actual C, complete original caller, rebase/corruption, package/twin/production/docs/graph/commit gates')
 (o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
