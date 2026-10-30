"""Private lifetime descriptor qualification; raw packet bits and notification homes."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests import game_owner_effect_descriptor_oracle as base
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/'conker/build/game-owner-duration-descriptor-151AE7B0-match';F='func_151AE7B0';ENTRY=0x151AE7B0;ROM=0x1DBC60
CONSTANT=0x800A9D80;SYMS=dict(D_800A9D80=CONSTANT,func_1516962C=base.NOTIFY,func_1513418C=base.CREATE)
put,read,STACK=base.put,base.read,base.STACK
u32=base.u32;s16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case(base.Case):
 duration:int=90

def args(c):return tuple(map(u32,(c.owner,c.second,c.duration,c.selector,c.category)))
def fixture(c,s=SYMS):
 m=base.fixture(c);put(m,s['D_800A9D80'],c.first);put(m,STACK+c.phase+16,c.category);return m
def effect(m,c,s,home):
 if c.effect&1:
  put(m,c.owner+0x3B,read(m,c.owner+0x3B,1)^0x55,1);put(m,s['D_800A9D80'],0x40000000)
 if c.effect&2:put(m,home,base.ALTERNATE)
 if c.effect&4:
  for offset,value in((4,0x3F000000),(8,0xA5A5FFFF),(12,0x12340080),(16,0x80000000)):put(m,home+offset,value)
def reference(initial,c,s=SYMS,connected=False):
 m=dict(initial);home=STACK+c.phase;packets=[]
 for i,v in enumerate(args(c)[:4]):put(m,home+4*i,v)
 if not c.owner:return m,[],0,packets
 calls=[(s['func_1516962C'],(40,c.owner,17))]
 if connected:calls.append((base.DISPATCH,(40,home-88,17)))
 effect(m,c,s,home);owner=read(m,home);p=home-52
 put(m,p,0);put(m,p+4,0);identity=read(m,owner+0x3B,1);first=read(m,s['D_800A9D80']);second=read(m,home+4);duration=s16(read(m,home+8))
 put(m,p+8,identity,1);put(m,p+12,owner);put(m,p+16,1,1)
 for offset in(20,24,28):put(m,p+offset,0)
 put(m,p+32,first);put(m,p+36,second);put(m,p+40,duration if duration else 300,2)
 flags=6 if duration else 2
 for offset,value in((42,flags),(43,6),(44,255),(45,5)):put(m,p+offset,value,1)
 packets.append(base.data(m,p,48));selector=read(m,home+15,1);category=read(m,home+16)
 calls.append((s['func_1513418C'],(p,0,selector,category)))
 if not connected:return m,calls,base.OUTPUT if c.outcome else 0,packets
 calls.append((base.ALLOC,(40,category,88,1,selector,1)))
 if c.allocation_effect:put(m,owner+0x3B,read(m,owner+0x3B,1)^1,1)
 if not c.outcome:return m,calls,0,packets
 calls.append((base.COPY,(base.OUTPUT+16,p,48)))
 for i,v in enumerate(packets[0]):m[base.OUTPUT+16+i]=v
 if not read(m,owner)or read(m,owner+0x3B,1)!=identity:calls.append((base.DELETE,(base.OUTPUT,)));return m,calls,0,packets
 matrix=read(m,owner+0x1D4)
 if matrix and read(m,owner+0x74,1)&15!=15:
  calls.append((base.TRANSFORM,(base.OUTPUT+0x24,base.OUTPUT+0x40,matrix+64,base.OUTPUT)))
  for i in range(3):put(m,base.OUTPUT+0x40+4*i,0x3F800000+i*0x800000)
 else:put(m,base.OUTPUT+0x3A,flags|8,1)
 value=base.floating(first);put(m,base.OUTPUT+0x4C,base.bits(1.0/base.floating(base.bits(value+value))));put(m,base.OUTPUT+0x50,0)
 return m,calls,base.OUTPUT,packets

class Oracle(base.DescriptorOracle):
 def __init__(self,ws,m,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  super().__init__(ws,m,c,entry,s,connected)
  for i,v in enumerate(args(c)[:4]):self.r[4+i]=v
  put(self.memory,self.home+16,c.category);self.before=self.r[:]
 def record_call(self,t):
  counts={ENTRY:5,self.syms['func_1516962C']:3,base.DISPATCH:3,self.syms['func_1513418C']:4,base.ALLOC:6,base.COPY:3,base.DELETE:1,base.TRANSFORM:4}
  assert t in counts,hex(t);a=self.arguments(counts[t]);self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['func_1513418C']:self.packets.append(base.data(self.memory,a[0],48))
  if t==base.DISPATCH:self.notifications.append(base.data(self.memory,a[1],8))
 def hook(self,t):
  if t in(self.syms['func_1516962C'],base.DISPATCH):
   effect(self.memory,self.case,self.syms,self.home)
   for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
   self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True;self.r[2]=0x87654321
  else:super().hook(t)

def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def images(label='guest',entry=ENTRY,s=SYMS):return[linked(o/n,label+'-'+str(i),entry,s)for i,n in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))]
def state(q):return complete(q),q.trace,q.packets,q.notifications
def compare(c,ims,s=SYMS,entry=ENTRY,connected=False):
 initial=fixture(c,s);want=reference(initial,c,s,connected);ms=[]
 for ws in ims:
  q=Oracle(ws,initial,c,entry,s,base.helper_code((r/'conker/conker.us.bin').read_bytes())if connected else None).run()
  assert(base.public(q.memory),q.calls,q.r[2],q.packets)==(base.public(want[0]),want[1],want[2],want[3]),(c,q.calls,want[1],q.packets,want[3]);ms.append(q)
 assert state(ms[0])==state(ms[1])==state(ms[2]),c
 return ms[0]
def guest_suite():
 ims=images();assert ims[0]==ims[1]==ims[2];count=0;visits=set()
 for duration,selector,category,effect,outcome,phase,nil in itertools.product((0,1,90,300,0x7FFF,0x8000,0xFFFF,0xA5A5FFFF),(0,0xA5A500FF),(0,0x80000000),range(8),(False,True),(0,8),(False,True)):
  c=Case(owner=0 if nil else base.OWNER,duration=duration,selector=selector,category=category,effect=effect,outcome=outcome,phase=phase);visits.update(compare(c,ims).visits);count+=1
 for field,value in itertools.product(('identity','selector'),range(256)):compare(replace(Case(),**{field:0xA5A50000|value}),ims);count+=1
 for bits in(0,0x80000000,1,0x7F800000,0xFF800000,0x7FA12345,0x7FC12345,0xFFFFFFFF):compare(Case(first=bits,second=bits^0x80000000),ims);count+=1
 assert set(range(ENTRY,ENTRY+224,4))<=visits
 cuts=delays=0
 for c in(Case(owner=0),Case(duration=0,effect=7),Case(duration=0xFFFF,effect=3)):
  full=compare(c,ims)
  for cut in range(full.all_accesses):
   ms=[]
   for ws in(ims[0],ims[1]):
    q=Oracle(ws,fixture(c),c);q.cut=cut
    try:q.run()
    except base.faults.AccessBoundary:pass
    else:raise AssertionError('missing access cut')
    ms.append(q)
   assert state(ms[0])==state(ms[1])and(ms[0].current_pc,ms[0].delay_of)==(ms[1].current_pc,ms[1].delay_of);cuts+=1;delays+=ms[0].delay_of is not None
 rebases=0
 for j,(entry,constant)in enumerate(((0x17007FFC,0x90007FFC),(0x2500FFFC,0x90008000),(0x15008000,0x9020FFFC))):
  s=dict(D_800A9D80=constant,func_1516962C=entry+0x10000,func_1513418C=entry+0x20000);im=images('rebase-'+str(j),entry,s)
  for duration,effect,nil in itertools.product((0,1,0xFFFF),range(8),(False,True)):compare(Case(owner=0 if nil else base.OWNER,duration=duration,effect=effect),im,s,entry);rebases+=1
 return dict(cases=count,executions=count*3,covered_words=56,raw_C_exact=True,guards=0,all_packet_bytes=48,preserved_padding=list(base.PADDING),access_prefix_cases=cuts,delay_slot_cuts=delays,rebased_cases=rebases,GNU_layouts=3,full_modeled_state_and_trace_equal=True,home_mutations_guest_only=True,raw_float_bits=True)

def controls(body):
 changes={
 'notification_kind':('(40, owner, 17)','(40, owner, 18)'),
 'owner_identity':('owner[0x3B]','owner[0x3A]'),
 'attachment':('attachment = 1','attachment = 0'),
 'zero_prefix':('descriptor.zero4 = 0','descriptor.zero4 = 1'),
 'vector':('descriptor.vector[1] = 0.0f','descriptor.vector[1] = 1.0f'),
 'constant':('value20 = D_800A9D80','value20 = 0.0f'),
 'scale':('value24 = scale','value24 = 0.0f'),
 'signed_duration_test':('duration != 0','duration > 0'),
 'default_duration':('duration = 300','duration = 301'),
 'override_flags':('flags = 6','flags = 4'),
 'default_flags':('flags = 2','flags = 0'),
 'kind':('kind = 6','kind = 7'),
 'callback':('callback = -1','callback = 0'),
 'mode':('mode = 5','mode = 4'),
 'selector':('0, selector, category','0, selector ^ 1, category'),
 'category':('0, selector, category','0, selector, (s32)((u32)category + 1u)'),
 'result':('return created;','return created == NULL ? NULL : owner;'),
 }
 out={}
 for name,(a,b)in changes.items():assert a in body,(name,a);out[name]=body.replace(a,b)
 out['early_constant']=body.replace('    void *created;','    void *created;\n    f32 captured;').replace('    func_1516962C(40, owner, 17);','    captured = D_800A9D80;\n    func_1516962C(40, owner, 17);').replace('value20 = D_800A9D80','value20 = captured')
 assert len(set(out.values()))==len(out)and body not in out.values();return out

def _native_suite(m):
 text=(m.o/'selected-semantic-input.c').read_text();head,body=text.split('/* Notify the owner, then submit',1);body='/* Notify the owner, then submit'+body
 names=[];pieces=[]
 for name,source in dict(selected=body,**controls(body)).items():n='candidate_'+name;names.append(n);pieces.append(source.replace(m.F,n))
 t=head+'\n'.join(pieces)+r'''
f32 D_800A9D80;
static u8 owner[512],result[128];static u8 *wantedOwner;static s16 wantedDuration;static u8 wantedSelector;static s32 wantedCategory;static u32 wantedScale;
static u32 calls,error,mutation,outcome;static OwnerEffectDescriptor1D92F0 expected;
typedef void *(*Fn)(u8*,f32,s16,u8,s32);
typedef char ABI[(sizeof(void*)==4&&sizeof(OwnerEffectDescriptor1D92F0)==48&&__builtin_offsetof(OwnerEffectDescriptor1D92F0,duration)==40&&__builtin_offsetof(OwnerEffectDescriptor1D92F0,flags)==42)?1:-1];
static f32 real(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
void func_1516962C(s32 event,void*p,u8 kind){if(calls++!=0||event!=40||p!=wantedOwner||kind!=17)error=1;if(mutation){owner[0x3B]^=0x55;D_800A9D80=2.0f;}}
void *func_1513418C(void*p,s32 size,u8 selector,s32 category){u32 i;u8*a=p,*b=(u8*)&expected;
 if(calls++!=1||size||selector!=wantedSelector||category!=wantedCategory)error=1;
 expected.zero0=expected.zero4=0;expected.ownerIdentity=owner[0x3B];expected.owner=owner;expected.attachment=1;
 expected.vector[0]=expected.vector[1]=expected.vector[2]=0.0f;expected.value20=D_800A9D80;expected.value24=real(wantedScale);
 expected.duration=wantedDuration?wantedDuration:300;expected.flags=wantedDuration?6:2;expected.kind=6;expected.callback=-1;expected.mode=5;
 for(i=0;i<48;i++)if(!(i>=9&&i<12)&&!(i>=17&&i<20)&&i<46&&a[i]!=b[i])error=2;
 return outcome?result:NULL;
}
static const u32 floats[]={0,0x80000000,1,0x7F800000,0xFF800000,0x7FC12345,0x3F19999A,0x411CCCCD};
static const s32 categories[]={0,1,-1,(-2147483647-1),2147483647};
static int one(Fn fn,u32 d,u32 flags){u32 i;void*answer;
 for(i=0;i<512;i++)owner[i]=0x5A;for(i=0;i<128;i++)result[i]=0xA5;
 wantedDuration=(s16)d;wantedSelector=(u8)(d*37+flags);wantedCategory=categories[(d+flags)%5];wantedScale=floats[(d+3)%8];wantedOwner=(flags&1)?NULL:owner;
 owner[0x3B]=(u8)(d*17+flags);D_800A9D80=real(floats[d%8]);calls=error=0;mutation=(flags>>1)&1;outcome=(flags>>2)&1;
 answer=fn(wantedOwner,real(wantedScale),wantedDuration,wantedSelector,wantedCategory);
 if(error||calls!=((flags&1)?0:2)||answer!=(!(flags&1)&&outcome?result:NULL))return 1;
 for(i=0;i<128;i++)if(result[i]!=0xA5)return 2;
 for(i=0;i<512;i++)if(i!=0x3B&&owner[i]!=0x5A)return 3;
 return 0;
}
static int run(void){Fn fns[]={FUNCTIONS};u32 n,d,flags;int rejected;
 for(n=0;n<sizeof(fns)/sizeof(fns[0]);n++){
  rejected=0;
  if(!n){for(d=0;d<65536;d++)if(one(fns[n],d,(d>>2)&6))return 10;for(d=0;d<256;d++)for(flags=0;flags<8;flags++)if(one(fns[n],d,flags))return 11;}
  else{for(d=0;d<65536&&!rejected;d++)for(flags=0;flags<8;flags++)if(one(fns[n],d,flags)){rejected=1;break;}if(!rejected)return 50+n;}
 }return 0;}
'''
 t=t.replace('FUNCTIONS',','.join(names))+m.START;path=m.o/'native-duration-descriptor.c';path.write_text(t);profiles={}
 for opt in('-O0','-O2','-O3'):
  binary=m.o/('native-duration-descriptor'+opt);q=subprocess.run(m.native_command(opt)+['-mstackrealign',str(path),'-o',str(binary)],capture_output=True,text=True);binary.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);assert q.returncode==0 and not q.stderr,(opt,q.stdout,q.stderr)
  q=subprocess.run([str(binary)],capture_output=True,timeout=60);assert q.returncode==0,(opt,q.returncode);profiles[opt]=dict(exit=0,UBSan=True)
 return dict(cases_per_profile=65536+256*8,profiles=profiles,compiled_controls=len(names)-1,all_effective=True,all_65536_duration_representations=True,ABI='void*(u8*,f32,s16,u8,s32)',native_real_allocated_objects=True,object_canaries=True,indeterminate_padding_not_asserted=True,home_mutations_not_claimed_as_portable=True)

def _compiled_controls(m):
 text=(m.o/'selected-semantic-input.c').read_text();head,body=text.split('/* Notify the owner, then submit',1);body='/* Notify the owner, then submit'+body;out={}
 def view(memory,calls,value,packets):return m.base.public(memory),[(at,a[1:]if at==m.base.CREATE else a)for at,a in calls],value,[bytes(v for i,v in enumerate(p)if i not in m.base.PADDING)for p in packets]
 for name,source in controls(body).items():
  obj,diag=m.compile_owner(m.r,m.o,head+source,'negative-'+name);assert not diag;words=m.linked(obj,'negative-linked-'+name);witness=None
  for duration,effect in itertools.product((0,1,0xFFFF),(0,1,3,7)):
   c=m.Case(duration=duration,effect=effect);initial=m.fixture(c);want=m.reference(initial,c);q=m.Oracle(words,initial,c).run()
   if view(q.memory,q.calls,q.r[2],q.packets)!=view(*want):witness=[duration,effect];break
  assert witness is not None,('ineffective compiled control',name);out[name]=witness
 return dict(count=len(out),effective_IDO_controls=out,compile_or_oracle_failures_not_accepted=True)

def _caller_suite(m):
 rom=(m.r/'conker/conker.us.bin').read_bytes();start,end=0x15194440,0x15194460;ws=list(struct.unpack_from('>8I',rom,0x1C18F0));ims=m.images('caller')
 assert ws[-2]==0x0C000000|((m.ENTRY>>2)&0x3FFFFFF)
 class Boundary(Exception):pass
 class Window(m.base.faults.TrackedCode):
  def __contains__(self,pc):return pc==end or super().__contains__(pc)
  def __getitem__(self,pc):
   if pc==end:raise Boundary
   return super().__getitem__(pc)
 count=0
 for nil,effect,outcome,phase in itertools.product((False,True),range(8),(False,True),(0,8)):
  c=m.Case(owner=0 if nil else m.base.OWNER,second=0x3F19999A,duration=90,selector=255,category=1,effect=effect,outcome=outcome,phase=phase);initial=m.fixture(c);want=m.reference(initial,c);ms=[]
  for body in ims:
   q=m.Oracle(ws,initial,c,start,connected={m.ENTRY+4*i:w for i,w in enumerate(body)});q.r[16]=c.owner;q.before=q.r[:];q.code=Window(dict(q.code),q)
   try:q.run()
   except Boundary:pass
   else:raise AssertionError('caller window boundary absent')
   assert(m.base.public(q.memory),q.calls,q.r[2],q.packets)==(m.base.public(want[0]),[(m.ENTRY,m.args(c)),*want[1]],want[2],want[3]),c;ms.append(q)
  assert m.state(ms[0])==m.state(ms[1])==m.state(ms[2]);count+=1
 return dict(cases=count,parent='func_15194408',original_window_words=8,call='0x15194458',scale_bits='0x3F19999A',duration=90,selector=255,category=1,return_ignored=True,full_parent_claimed=False)

def _provider_suite(m):
 from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 rom=(m.r/'conker/conker.us.bin').read_bytes();elf=(m.o/'before-conker_build_conker.us.elf').read_bytes();identities={}
 for entry,offset,n in m.base.HELPERS:
  at=elf_slot_offset(elf,entry,n*4);assert elf[at:at+n*4]==rom[offset:offset+n*4];identities[hex(entry)]=dict(words=n,current_byte_exact=True)
 ims=m.images('providers');visits=set();count=0
 for duration,outcome,valid,matrix,kind,allocation,effect in itertools.product((0,90,0xFFFF),(False,True),(False,True),(False,True),(0,15),(False,True),(0,1,2,4)):
  c=m.Case(duration=duration,outcome=outcome,valid=valid,matrix=matrix,actor_type=kind,allocation_effect=allocation,effect=effect);q=m.compare(c,ims,connected=True);visits.update(q.visits);count+=1
 coverage=[sum(pc in visits for pc in range(entry,entry+n*4,4))for entry,offset,n in m.base.HELPERS];assert coverage==[15,74,11]
 return dict(cases=count,provider_identities=identities,loaded_original_helper_words=102,helper_coverage=coverage,visited_original_helper_words=sum(coverage),notify_constructor_memcpy_original=True,unvisited_helper_words=['0x15134234','0x15134284'],allocation_dispatch_delete_transform_are_bounded_hooks=True,full_parent_or_gameplay_claimed=False)

def native_suite():
 import sys
 return _native_suite(sys.modules[__name__])
def compiled_controls():
 import sys
 return _compiled_controls(sys.modules[__name__])
def caller_suite():
 import sys
 return _caller_suite(sys.modules[__name__])
def provider_suite():
 import sys
 return _provider_suite(sys.modules[__name__])
