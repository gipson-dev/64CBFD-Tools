"""State-9 actor start: signed pool indexing, pointer reloads and real ABI."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,re,struct,subprocess
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-actor-state9-start-15063404-match';F='func_15063404';ENTRY=0x15063404;POOL=0x800CC2D0;SPAWN=0x15083568;ANIMATE=0x1505E650;N1,N2,N3=0x51000,0x52000,0x53000
SYMS=dict(D_800CC2D0=POOL,func_15083568=SPAWN,func_1505E650=ANIMATE);u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 slot:int=0
 offset:int=0
 mode:int=0
 alias:int=0
 phase:int=0
 actor_at:int=0
 seed:int=0

def actor(c,pool=POOL):return c.actor_at or u32(pool+c.slot*812+c.offset)
def entry(c,pool=POOL):
 d=u32(actor(c,pool)-pool);d=(d^0x80000000)-0x80000000;i=abs(d)//812*(-1 if d<0 else 1);return u32(pool+i*812)
def nested(c,pool=POOL):
 a,e=actor(c,pool),entry(c,pool)
 return u32((N1,a+0xB,a+0x11,e+0x2A4,e+0x2F8,e+0x2FA,e+0x202)[c.alias])

def mutation(m,c,ordinal,pool=POOL,quiet=False):
 a,e=actor(c,pool),entry(c,pool)
 if ordinal<3:
  if c.mode&1:
   for at,val in ((0x8A,0xE0+ordinal),(0x89,0xC0+ordinal),(0x83,0xB0+ordinal)):m[u32(a+at)]=val
   put(m,u32(a+0x90),0x87654320+ordinal)
  if ordinal==1 and c.mode&2:put(m,u32(e+0x31C),N2)
  if ordinal==2 and c.mode&4:put(m,u32(e+0x31C),N3)
 elif c.mode&8 and not quiet:
  for at,val in ((0x8A,0x6D),(0x89,0x71),(0x83,0x93)):m[u32(a+at)]=val
  n=read(m,u32(e+0x31C));put(m,u32(n+0x24),0x1234,2);m[u32(n+0x11A)]=0xC7

def fixture(c,pool=POOL):
 m={u32(STACK+c.phase+i):(i*17+c.seed)&255 for i in range(-1536,1024)};a,e,n=actor(c,pool),entry(c,pool),nested(c,pool)
 def ensure(base):
  for i in range(-16,0x400):m.setdefault(u32(base+i),(i*13+c.seed)&255)
 for base in (a,e,n,N1,N2,N3):ensure(base)
 put(m,u32(e+0x31C),n);probe=dict(m)
 def future(base):
  ensure(base)
  for i in range(-16,0x400):probe.setdefault(u32(base+i),m[u32(base+i)])
 probe[u32(n+0x78)]=9;future(read(probe,u32(e+0x31C)))
 for ordinal in (1,2):mutation(probe,c,ordinal,pool);future(read(probe,u32(e+0x31C)))
 probe[u32(a+0x8A)]=20;probe[u32(a+0x89)]=0;probe[u32(a+0x83)]=0;n=read(probe,u32(e+0x31C));future(n);put(probe,u32(n+0x24),60,2);future(read(probe,u32(e+0x31C)))
 probe[u32(read(probe,u32(e+0x31C))+0x11A)]=2;future(read(probe,u32(e+0x31C)));return m

def observe(m,c,pool=POOL):
 a,e=actor(c,pool),entry(c,pool);n=read(m,u32(e+0x31C));candidates=(nested(c,pool),N1,N2,N3,n)
 return(n,tuple(m.get(u32(a+i))for i in(0x8A,0x89,0x83)),tuple((at,*(m.get(u32(at+i))for i in(0x24,0x25,0x78,0x11A)))for at in candidates))

def reference(initial,c,pool=POOL,quiet=False):
 m=dict(initial);a,e=actor(c,pool),entry(c,pool);m[u32(read(m,u32(e+0x31C))+0x78)]=9;calls=[];obs=[]
 for ordinal,request in ((1,29),(2,30)):
  calls.append((SPAWN,(a,request,0x3F800000,0)));obs.append(observe(m,c,pool));mutation(m,c,ordinal,pool)
 m[u32(a+0x8A)]=20;m[u32(a+0x89)]=0;m[u32(a+0x83)]=0;put(m,u32(read(m,u32(e+0x31C))+0x24),60,2);m[u32(read(m,u32(e+0x31C))+0x11A)]=2
 calls.append((ANIMATE,(a,127,0x3F800000,0,0,0,0)));obs.append(observe(m,c,pool));mutation(m,c,3,pool,quiet);return m,calls,obs
def public(m):return{a:b for a,b in m.items()if not STACK-1536<=a<STACK+1024}

class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry_at=ENTRY,pool=POOL,s=SYMS,connected=None,args=None,quiet=False,found=True):
  self.c,self.pool,self.s,self.quiet,self.found=c,pool,s,quiet,found;super().__init__(words,memory,phase=c.phase,entry=entry_at,arguments=args or(actor(c,pool),),connected=connected);self.trace=[];self.observations=[];self.ordinal=0
 def get(self,address,size):
  v=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,v))
  return v
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
 def record_call(self,target):
  sizes={self.s['func_15083568']:4,self.s['func_1505E650']:7,ENTRY:1,0x15063570:1,0x150634E4:1,0x1505EEF4:1};assert target in sizes,hex(target);args=self.arguments(sizes[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target in(self.s['func_15083568'],self.s['func_1505E650']):self.observations.append(observe(self.memory,self.c,self.pool))
 def hook(self,target):
  if target==self.s['func_15083568']:self.ordinal+=1;mutation(self.memory,self.c,self.ordinal,self.pool)
  elif target==self.s['func_1505E650']:mutation(self.memory,self.c,3,self.pool,self.quiet)
  else:assert target in(0x15063570,0x150634E4,0x1505EEF4)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678
  self.r[2]=(actor(self.c,self.pool)if self.found else 0)if target==0x1505EEF4 else N3 if target==self.s['func_15083568']else 0xDEADBEEF

def linked(obj,label,entry_at=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry_at+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.observations,m.condition)
def cases():
 for slot,mode,alias,phase in itertools.product(range(26),range(16),range(3),(0,8)):yield Case(slot=slot,mode=mode,alias=alias,phase=phase)
 for slot,offset,mode,alias,phase in itertools.product((-2,-1,0,1,25,26),(1,3,7,658,811),(0,7,15),(0,3,4,5,6),(0,8)):yield Case(slot,offset,mode,alias,phase)

def compare(c,images,pool=POOL,s=SYMS,entry_at=ENTRY,initial=None,connected=None,quiet=False):
 initial=fixture(c,pool)if initial is None else initial;want,calls,obs=reference(initial,c,pool,quiet);ms=[]
 for ws in images:
  m=Oracle(ws,initial,c,entry_at,pool,s,connected,quiet=quiet).run();normal=[(SPAWN if t==s['func_15083568']else ANIMATE if t==s['func_1505E650']else t,a)for t,a in m.calls];assert(public(m.memory),normal,m.observations)==(public(want),calls,obs),c;assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30]==m.before[30]and m.f[20:]==m.saved_f;ms.append(m)
 assert all(state(m)==state(ms[0])for m in ms[1:]),c;return ms[0]

def guest_suite():
 images=[linked(o/p,'guest-'+str(i))for i,p in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];assert images[0]==images[1]==images[2];visits=set();count=0
 for c in cases():visits.update(compare(c,images).visits);count+=1
 assert set(range(ENTRY,ENTRY+224,4))<=visits;cuts=delays=0
 for c in (Case(),Case(slot=25,mode=15),Case(alias=3),Case(alias=4),Case(slot=-1,offset=811)):
  full=compare(c,images)
  for cut in range(full.root_accesses):
   ms=[]
   for ws in images:
    m=Oracle(ws,fixture(c),c);m.root_fault=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('missing cut',cut))
    ms.append(m)
   assert all(state(m)==state(ms[0])and(m.current_pc,m.delay_of)==(ms[0].current_pc,ms[0].delay_of)for m in ms[1:]);cuts+=1;delays+=ms[0].delay_of is not None
 homes=0
 for c in (Case(actor_at=STACK-0x83),Case(phase=8,actor_at=STACK+8-0x83)):
  ms=[Oracle(ws,fixture(c),c).run()for ws in images];assert state(ms[0])==state(ms[1])==state(ms[2]);homes+=1
 rebased=0
 for j,(at,pool)in enumerate(((0x17007FFC,0x81007FFC),(0x2500FFFC,0x81008000),(0x15008000,0x8120FFFC))):
  s=dict(D_800CC2D0=pool,func_15083568=at+0x10004,func_1505E650=at+0x20008);ps=[linked(o/p,'rebase-'+str(j)+'-'+str(i),at,s)for i,p in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];assert ps[0]==ps[1]==ps[2]
  for slot,offset,mode,alias,phase in itertools.product((-1,0,25),(0,3),(0,7,15),(0,3,4),(0,8)):compare(Case(slot,offset,mode,alias,phase),ps,pool,s,at);rebased+=1
 return dict(cases=count,executions=count*3,covered_words=56,access_prefix_cases=cuts,delay_slot_cuts=delays,guest_only_stack_alias_cases=homes,rebased_cases=rebased,GNU_layouts=3,complete_state_and_trace_equal=True,alias_layouts=7,frame=48,RA_offset=36,entry_home=40,incoming_actor_home=48,signed_truncation_and_callback_reloads=True,native_invalid_indices_not_claimed=True)

def helper_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();ws=list(struct.unpack_from('>95I',rom,0x8BB00));old=(o/'before-conker_build_conker.us.elf').read_bytes();from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 at=elf_slot_offset(old,ANIMATE,380);assert old[at:at+380]==rom[0x8BB00:0x8BC7C];assert 'u8 *func_15083568(u8 *actor, s32 animation, f32 scale, s32 mode)'in(r/'conker/src/game/generated_AEB40.c').read_text()
 asm=(r/'conker/asm/nonmatchings/game_83300/func_1505E650.s').read_text();assert 'lhu        $a3, 0x4E($sp)'in asm and 'lw         $t9, 0x60($sp)'in asm
 images=[linked(o/p,'helper-target-'+str(i))for i,p in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];count=0;visits=set()
 for slot,mode,busy,phase in itertools.product((0,1,25),range(16),(0,1),(0,8)):
  c=Case(slot=slot,mode=mode,phase=phase);initial=fixture(c);initial[0x800C3638]=busy;initial[0x800C3654]=0;initial[actor(c)+4]=255;m=compare(c,images,initial=initial,connected={ANIMATE+4*i:w for i,w in enumerate(ws)},quiet=True);visits.update(pc for pc in m.visits if ANIMATE<=pc<ANIMATE+380);count+=1
 return dict(cases=count,original_and_retained_animation_words=95,visited_provider_words=len(visits),only_busy_and_invalid_actor_early_exit_routes=True,spawn_ABI='u8*(u8*,s32,f32,s32)',animate_ABI='void(pointer,u16,f32,f32,f32,f32,s32)',larger_provider_semantics_bounded=True,helper_matching_credit=0)

class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
 def __getitem__(self,pc):
  if pc==self.owner.window_end:raise WindowBoundary
  return super().__getitem__(pc)

def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();jal=struct.pack('>I',0x0C000000|((ENTRY>>2)&0x3FFFFFF));ptr=struct.pack('>I',ENTRY);assert[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal]==[0x93EBC,0xC6888];assert not[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==ptr]
 images=[linked(o/p,'caller-body-'+str(i))for i,p in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];count=0
 # Include the switch arm's enable/state gates and taken sibling route.
 start,end,offset=0x150669E0,0x15066A2C,0x93E90;window=list(struct.unpack_from('>19I',rom,offset));literal={int(a,16):int(w,16)for a,w in re.findall(r'/\*\s*[0-9A-F]+\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',(r/'conker/asm/90840.s').read_text())};assert window==[literal[start+4*i]for i in range(19)]
 for slot,mode,enabled,status,phase in itertools.product((0,25),(0,7,15),(0,1),(0,1,2,255),(0,8)):
  c=Case(slot=slot,mode=mode,phase=phase);initial=fixture(c);initial[0x800C3A58]=enabled;initial[read(initial,entry(c)+0x31C)+0x11A]=status;want,calls,obs=reference(initial,c)if enabled and status in(1,2)else(dict(initial),[(0x150634E4,(actor(c),))]if enabled else[],[]);ms=[]
  for ws in images:
   m=Oracle(window,initial,c,entry_at=start,connected={ENTRY+4*i:w for i,w in enumerate(ws)});m.r[16]=actor(c);m.window_end=end;m.code=WindowCode(dict(m.code),m)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('missing window boundary')
   expected_calls=[(ENTRY,(actor(c),)),*calls]if enabled and status in(1,2)else calls;assert(public(m.memory),m.calls,m.observations)==(public(want),expected_calls,obs);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
 # Complete original event dispatcher, with lookup/sibling providers bounded.
 parent=0x15097A8C;parent_words=struct.unpack_from('>2146I',rom,0xC4F3C);table=rom[0x242A10:0x242C48];assert len(table)==568
 routed=0
 for slot,mode,command,status,found,phase in itertools.product((0,25),(0,7,15),(0,108,143),(0,9,59,255),(False,True),(0,8)):
  c=Case(slot=slot,mode=mode,phase=phase);initial=fixture(c)
  for i,b in enumerate(table):initial[0x8009DF50+i]=b
  for i in range(32):initial[0x60000+i]=(i*13+0x5A)&255
  put(initial,0x60008,status);want=dict(initial);calls=[(0x1505EEF4,(17,))];obs=[];result=0
  if found and command==108:
   result=1
   if status==9:want,tail,obs=reference(want,c);calls.extend([(ENTRY,(actor(c),)),*tail])
   elif status==59:calls.append((0x15063570,(actor(c),)))
  ms=[]
  for ws in images:
   m=Oracle(parent_words,initial,c,entry_at=parent,connected={ENTRY+4*i:w for i,w in enumerate(ws)},args=(17,command,0x60000),found=found).run();assert(public(m.memory),m.calls,m.observations,m.r[2])==(public(want),calls,obs,result);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);routed+=1
 assert 's32 func_15097A8C() {\n    return 0;\n}'in(r/'conker/src/game/generated_C4DC0.c').read_text()
 return dict(aligned_JALs=2,function_pointer_literals=0,actor_update_window_words=19,actor_update_window_cases=count,full_original_dispatcher_words=2146,dispatcher_cases=routed,original_jump_table_entries=142,target_event=108,target_state=9,lookup_and_sibling_handlers_bounded=True,current_C_parents_not_equivalent=True,whole_parent_acceptance=False)

def controls(body):
 first='    func_15083568((u8 *)actor, 0x1D, 1.0f, 0);\n';second='    func_15083568((u8 *)actor, 0x1E, 1.0f, 0);\n';clears='    actor->disable_jump = 20;\n    actor->disable_run = 0;\n    actor->unk83 = 0;\n';tail='    *(s16 *)((u8 *)entry->unk31C + 0x24) = 60;\n    entry->unk31C->unk11A = 2;\n'
 return dict(wrong_state=body.replace('unk78 = 9','unk78 = 8'),wrong_first=body.replace('0x1D, 1.0f','0x1C, 1.0f'),wrong_second=body.replace('0x1E, 1.0f','0x1F, 1.0f'),first_scale=body.replace('0x1D, 1.0f','0x1D, 0.5f'),second_scale=body.replace('0x1E, 1.0f','0x1E, 0.5f'),last_request=body.replace('0x7F, 1.0f','0x7E, 1.0f'),last_scale=body.replace('0x7F, 1.0f','0x7F, 0.5f'),last_mode=body.replace('0.0f, 0);','0.0f, 1);'),missing_second=body.replace(second,''),reversed_requests=body.replace(first+second,second+first),jump=body.replace('disable_jump = 20','disable_jump = 21'),run_flag=body.replace('disable_run = 0','disable_run = 1'),byte83=body.replace('unk83 = 0','unk83 = 1'),timer=body.replace('+ 0x24) = 60','+ 0x24) = 61'),nested_state=body.replace('unk11A = 2','unk11A = 3'),early_clears=body.replace(clears,'').replace(first,clears+first),early_tail=body.replace(tail,'').replace(first,tail+first),cached_initial=body.replace('    entry->unk31C->unk78 = 9;','    struct126 *nested = entry->unk31C;\n    nested->unk78 = 9;').replace('((u8 *)entry->unk31C + 0x24)','((u8 *)nested + 0x24)').replace('    entry->unk31C->unk11A = 2;','    nested->unk11A = 2;'),use_return=body.replace(first,'    actor = (struct127 *)func_15083568((u8 *)actor, 0x1D, 1.0f, 0);\n'))

def compiled_controls():
 source=(o/'selected-semantic-input.c').read_text();rows={};corpus=[Case(),Case(mode=7),Case(mode=15),Case(alias=4),Case(slot=-1)]
 variants=controls(source);variants['unsigned_index']=source.replace('((s32)actor -\n        (s32)D_800CC2D0)','((u32)actor -\n        (u32)D_800CC2D0)');variants['cached_after_timer']=source.replace('    *(s16 *)((u8 *)entry->unk31C + 0x24) = 60;','    struct126 *nested = entry->unk31C;\n    *(s16 *)((u8 *)nested + 0x24) = 60;').replace('    entry->unk31C->unk11A = 2;','    nested->unk11A = 2;')
 # C89 declarations must precede statements in the IDO fixture.
 variants['cached_after_timer']=variants['cached_after_timer'].replace('    struct126 *nested = entry->unk31C;','    nested = entry->unk31C;').replace('void '+F+'(struct127 *actor) {','void '+F+'(struct127 *actor) {\n    struct126 *nested;')
 for name,body in variants.items():
  assert body!=source,name;obj,diag=compile_owner(r,o,body,'control-'+name);assert not diag;ws=linked(obj,'control-linked-'+name)
  for i,c in enumerate(corpus):
   initial=fixture(c);want,calls,obs=reference(initial,c)
   try:m=Oracle(ws,initial,c).run();bad=(public(m.memory),m.calls,m.observations)!=(public(want),calls,obs)
   except AssertionError as exc:
    assert 'unmapped'in str(exc),str(exc);bad=True
   if bad:rows[name]=i;break
  else:raise AssertionError(('ineffective IDO control',name))
 return dict(count=len(rows),effective_IDO_controls=rows,native_controls=len(controls(source)),guest_only_signed_and_timer_alias_controls=2)

def native_source(source):
 head,body=source.split('/* Set nested',1);body='/* Set nested'+body
 text=head+r'''
struct127 D_800CC2D0[26];
static u8 *n1,*n2,*n3,*expected;static struct127 *current;
static u32 error,spawns,animations,mode,observations[3][13];
typedef char ABI[(sizeof(void*)==4&&sizeof(s16)==2&&sizeof(s32)==4&&sizeof(f32)==4&&sizeof(struct127)==0x32C&&sizeof(struct126)<=0x400&&__builtin_offsetof(struct127,unk31C)==0x31C&&__builtin_offsetof(struct127,disable_jump)==0x8A&&__builtin_offsetof(struct127,disable_run)==0x89&&__builtin_offsetof(struct127,unk83)==0x83&&__builtin_offsetof(struct126,unk78)==0x78&&__builtin_offsetof(struct126,unk11A)==0x11A)?1:-1];
static void snapshot(u32*out,u8*a,u8*b,u8*c,u8*d){u32 i;u8*ns[3];ns[0]=b;ns[1]=c;ns[2]=d;out[0]=a[0x8A];out[1]=a[0x89];out[2]=a[0x83];out[3]=*(u32*)(void*)(a+0x31C);for(i=0;i<3;i++){out[4+i*3]=*(u16*)(void*)(ns[i]+0x24);out[5+i*3]=ns[i][0x78];out[6+i*3]=ns[i][0x11A];}}
static void check_snapshot(u32 ordinal){u32 i,actual[13];snapshot(actual,(u8*)current,n1,n2,n3);for(i=0;i<13;i++)if(actual[i]!=observations[ordinal][i])error=1;}
__attribute__((noinline,noclone)) u8 *func_15083568(u8*a,s32 request,f32 scale,s32 flags){u32 ordinal=spawns+1;if(a!=(u8*)current||request!=(ordinal==1?29:30)||scale!=1.0f||flags||ordinal>2)error=1;if(ordinal<=2)check_snapshot(ordinal-1);spawns++;
 if(mode&1){a[0x8A]=(u8)(0xE0+ordinal);a[0x89]=(u8)(0xC0+ordinal);a[0x83]=(u8)(0xB0+ordinal);*(u32*)(void*)(a+0x90)=0x87654320u+ordinal;}
 if(ordinal==1&&(mode&2))current->unk31C=(struct126*)(void*)n2;if(ordinal==2&&(mode&4))current->unk31C=(struct126*)(void*)n3;return n3;}
__attribute__((noinline,noclone)) void func_1505E650(u8*a,u16 request,f32 scale,f32 x,f32 y,f32 z,s32 flags){u8*n;if(a!=(u8*)current||request!=127||scale!=1.0f||x!=0.0f||y!=0.0f||z!=0.0f||flags||spawns!=2||animations++)error=1;check_snapshot(2);
 if(mode&8){a[0x8A]=0x6D;a[0x89]=0x71;a[0x83]=0x93;n=(u8*)current->unk31C;*(s16*)(void*)(n+0x24)=0x1234;n[0x11A]=0xC7;}}
'''
 for name,b in dict(selected=body,**controls(body)).items():text+=b.replace(F,name)+'\n'
 text+=r'''
typedef void(*Begin)(struct127*);
static u8*shadow(u32 n){return n==(u32)n1?expected+0x400:n==(u32)n2?expected+0x800:expected+0xC00;}
static int one(Begin fn,u32 slot,u32 pattern,u32 mutation,u32 bank){u32 i,ordinal;u8*a,*e,*e1,*e2,*e3,*n;current=&D_800CC2D0[slot];a=(u8*)current;e=expected;e1=e+0x400;e2=e+0x800;e3=e+0xC00;
 for(i=0;i<0x32C;i++)a[i]=(u8)(i*13+pattern);for(i=0;i<0x400;i++){n1[i]=(u8)(i*17+pattern);n2[i]=(u8)(i*23+pattern);n3[i]=(u8)(i*29+pattern);}
 current->unk31C=(struct126*)(void*)(bank?n2:n1);for(i=0;i<0x32C;i++)e[i]=a[i];for(i=0;i<0x400;i++){e1[i]=n1[i];e2[i]=n2[i];e3[i]=n3[i];}
 shadow(*(u32*)(void*)(e+0x31C))[0x78]=9;
 for(ordinal=1;ordinal<=2;ordinal++){snapshot(observations[ordinal-1],e,e1,e2,e3);if(mutation&1){e[0x8A]=(u8)(0xE0+ordinal);e[0x89]=(u8)(0xC0+ordinal);e[0x83]=(u8)(0xB0+ordinal);*(u32*)(void*)(e+0x90)=0x87654320u+ordinal;}if(ordinal==1&&(mutation&2))*(u32*)(void*)(e+0x31C)=(u32)n2;if(ordinal==2&&(mutation&4))*(u32*)(void*)(e+0x31C)=(u32)n3;}
 e[0x8A]=20;e[0x89]=0;e[0x83]=0;n=shadow(*(u32*)(void*)(e+0x31C));*(s16*)(void*)(n+0x24)=60;n[0x11A]=2;snapshot(observations[2],e,e1,e2,e3);
 if(mutation&8){e[0x8A]=0x6D;e[0x89]=0x71;e[0x83]=0x93;*(s16*)(void*)(n+0x24)=0x1234;n[0x11A]=0xC7;}
 mode=mutation;error=spawns=animations=0;fn(current);if(error||spawns!=2||animations!=1)return 0;
 for(i=0;i<0x32C;i++)if(a[i]!=e[i])return 0;for(i=0;i<0x400;i++)if(n1[i]!=e1[i]||n2[i]!=e2[i]||n3[i]!=e3[i])return 0;return 1;}
static int check(Begin fn,u32 full){u32 s,p,m,b;for(s=0;s<(full?26u:2u);s++)for(p=0;p<(full?256u:4u);p++)for(m=0;m<16;m++)for(b=0;b<2;b++)if(!one(fn,full?s:s*25,p,m,b))return 0;return 1;}
static void *allocate(u32 n){u32 p,end;__asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");end=p+n;__asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;}
int run(void){u8 *(*spawn)(u8*,s32,f32,s32)=func_15083568;void(*animate)(u8*,u16,f32,f32,f32,f32,s32)=func_1505E650;if(!spawn||!animate)return 97;n1=allocate(0x2400);if(!n1)return 97;n1=(u8*)(((u32)n1+15)&~15u);n2=n1+0x400;n3=n1+0x800;expected=n1+0xC00;if((u32)&D_800CC2D0[25]>0x7FFFFFFF)return 97;if(!check(selected,1))return 1;
'''
 for i,name in enumerate(controls(body),2):text+='if(check('+name+',0))return '+str(i)+';\n'
 return text+'return 0;}\n'+START

def native_suite():
 source=(o/'selected-semantic-input.c').read_text();profiles={}
 for opt in ('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]+'.c');p.write_text(native_source(source));binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=r,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);assert q.returncode==0,q.stdout+q.stderr;z=subprocess.run([str(binary)],timeout=60);assert z.returncode==0,(opt,z.returncode);profiles[opt]=dict(exit=0,UBSan=True,cases=212992)
 return dict(cases_per_profile=212992,SDK_layout_assertions=True,typed_provider_ABI=True,pre_provider_observations=True,native_controls=len(controls(source)),valid_array_and_typeless_nested_domains_only=True,profiles=profiles)
