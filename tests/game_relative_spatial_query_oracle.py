"""Relative spatial query: signed wrapping arithmetic, late offsets and role maps."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-relative-spatial-query-1510F720-match';F='func_1510F720';ENTRY=0x1510F720;ROM=0x13CBD0
HEAD=0x800DBE48;BASE=0x00200000;NODES=tuple(BASE+32*i for i in range(8));OUT=0x50000;SYMS=dict(D_800DBE48=HEAD)
u32=lambda n:n&0xFFFFFFFF;s32=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000;s16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 x:int=0
 z:int=0
 radius:int=1
 pattern:int=0
 shape:int=0
 empty:bool=False
 alias:int=0
 phase:int=0
def order(c):return tuple(range(8))if c.shape==0 or c.alias==3 else(4,1,6,0,7,2,5,3)
def output(c,s=SYMS):
 first=NODES[order(c)[0]]
 return(OUT,first+8,first+12,first+4,s['D_800DBE48'],STACK+c.phase-12)[c.alias]
def args(c,s=SYMS):return tuple(map(u32,(c.x,c.z,c.radius,output(c,s))))
def fixture(c,s=SYMS):
 memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x800)}
 for base,size in((BASE,0x180),(OUT,128),(s['D_800DBE48']-16,80)):
  for i in range(size):memory[u32(base+i)]=(i*13+0x5A)&255
 seq=order(c)
 for i,node in enumerate(NODES):
  rank=seq.index(i);nxt=NODES[seq[rank+1]]if rank<7 else 0;child=0
  if c.shape and c.alias!=3:
   selected={0:2,3:5}if c.shape==1 else{2:6,4:7}
   if rank in selected:child=NODES[seq[selected[rank]]]
  if c.alias==3:
   if i==0:nxt=NODES[2]
   if i==1:nxt=0
  if c.pattern==0:x=z=extent=0
  elif c.pattern==1:
   values=(0,1,-1,32767,-32768,128,-128,300);x=values[i];z=values[7-i];extent=(0,1,2,32767,32768,65535,5,10)[i]
  elif c.pattern==2:x=i*37-128;z=i*53+17;extent=i*10000&65535
  else:x=z=0;extent=65535
  for off,v in((4,nxt-node if nxt else 0),(6,extent),(8,x),(10,z),(12,child-node if child else 0)):put(memory,node+off,v,2)
 put(memory,s['D_800DBE48'],0 if c.empty else NODES[seq[0]])
 return memory
def reference(initial,c,s=SYMS,out=None):
 memory=dict(initial);node=read(memory,s['D_800DBE48']);cursor=output(c,s)if out is None else out;count=steps=0;found=[]
 while node:
  steps+=1;assert steps<=32,('unbounded fixture',c,hex(node))
  dx=s32(s16(read(memory,node+8,2))-s32(c.x));absolute=s32(-dx)if dx<0 else dx;limit=s32(s32(c.radius)+read(memory,node+6,2));inside=False
  if absolute<limit:
   dz=s32(s16(read(memory,node+10,2))-s32(c.z));absolute=s32(-dz)if dz<0 else dz;inside=absolute<limit
  if inside:
   child=s16(read(memory,node+12,2))
   if child:offset=child
   else:
    put(memory,cursor,node);cursor=u32(cursor+4);count+=1;found.append(node);offset=s16(read(memory,node+4,2))
  else:offset=s16(read(memory,node+4,2))
  node=u32(node+offset)if offset else 0
 return memory,count,found
def public(memory):return{a:v for a,v in memory.items()if not STACK-0x400<=a<STACK+0x800}
class RoleCode(faults.TrackedCode):
 def __getitem__(self,pc):
  word=super().__getitem__(pc);self.owner.observe_role(pc);return word
class Oracle(TimingOracle):
 def __init__(self,ws,m,c=Case(),entry=ENTRY,s=SYMS,raw=False,connected=None,track=True):
  self.c,self.syms,self.is_raw=c,s,raw;self.trace=[];self.roles=[];self.track_roles=track;self.cut=None;self.all_accesses=0
  super().__init__(ws,m,phase=c.phase,entry=entry,arguments=args(c,s),connected=connected)
  self.target_entry=ENTRY if connected and ENTRY in connected else entry;self.code=RoleCode(dict(self.code),self)
  if c.alias==5:
   assert output(c,s)==self.r[29]-12
   _,count,found=reference(m,c,s)
   # The three spill words are intentional output aliases, not ABI exemptions.
   for i,node in enumerate(found[:3]):self.before[16+i]=node
 def access(self):
  if self.own_instruction:
   if self.all_accesses==self.cut:raise faults.AccessBoundary
   self.all_accesses+=1
 def get(self,a,n):
  value=super().get(a,n)
  if self.own_instruction:self.trace.append(('R',a,n,value))
  return value
 def put(self,a,v,n):
  super().put(a,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',a,n,v&((1<<(8*n))-1)))
 def observe_role(self,pc):
  # Role observations compare only live logical values; they never rewrite code.
  if self.track_roles and self.target_entry<=pc<self.target_entry+224:
   index=(pc-self.target_entry)//4;registers=None
   if index in(13,48):registers=(16,17,6,18,2,3)if self.is_raw else(4,17,16,18,2,3)
   elif index==20:registers=(5,4)if self.is_raw else(6,5)
   elif index==25:registers=(5,4)if self.is_raw else(6,5)
   elif index==29:registers=(7,4)if self.is_raw else(7,5)
   elif index==33:registers=(4,)if self.is_raw else(5,)
   elif index==43:registers=(5,)if self.is_raw else(6,)
   if registers:self.roles.append((index,tuple(self.r[n]for n in registers)))
 def record_call(self,target):
  assert target==ENTRY,hex(target);a=self.arguments(4);self.calls.append((target,a));self.events.append(('CALL',target,a))
 def hook(self,target):raise AssertionError('Unbounded query provider: '+hex(target))
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];assembly,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def images(label='guest',entry=ENTRY,s=SYMS):return[linked(o/n,label+'-'+str(i),entry,s)for i,n in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))]
def state(q):return(q.r,q.f,q.memory,q.calls,q.events,q.trace,q.roles,q.hi,q.lo,q.condition)
def compare(c,ims,s=SYMS,entry=ENTRY):
 initial=fixture(c,s);want,count,found=reference(initial,c,s);ms=[]
 for i,ws in enumerate(ims):
  q=Oracle(ws,initial,c,entry,s,raw=i==1).run();assert(public(q.memory),q.r[2])==(public(want),count),(c,i,count,q.r[2]);assert[read(q.memory,output(c,s)+4*k)for k in range(count)]==found,c;ms.append(q)
 assert state(ms[0])==state(ms[2]),c
 assert(ms[0].memory,ms[0].trace,ms[0].roles,ms[0].calls,ms[0].r[16:24],ms[0].r[29],ms[0].r[31])==(ms[1].memory,ms[1].trace,ms[1].roles,ms[1].calls,ms[1].r[16:24],ms[1].r[29],ms[1].r[31]),c
 return ms[0]
def guest_suite():
 ims=images();assert ims[0]==ims[2]and len(ims[1])==56;count=0;visits=set();role_cuts=0
 values=(0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF);radii=(0,1,2,0xFFFFFFFF,0x7FFFFFFF,0x80000000,0xFFFF0001)
 for x,z,radius,pattern,shape,empty,phase in itertools.product(values,values,radii,range(4),range(3),(False,True),(0,8)):
  q=compare(Case(x,z,radius,pattern,shape,empty,phase=phase),ims);visits.update(q.visits);role_cuts+=len(q.roles);count+=1
  if count%2048==0:print('GUEST_CASES',count,flush=True)
 assert set(range(ENTRY,ENTRY+224,4))-{ENTRY+4*i for i in(37,42,47)}<=visits
 aliases=0
 for x,z,radius,pattern,shape,alias,phase in itertools.product((0,1,0xFFFFFFFF),(0,1,0xFFFFFFFF),(0,1,65536),(0,1,3),range(3),range(1,6),(0,8)):
  compare(Case(x,z,radius,pattern,shape,alias=alias,phase=phase),ims);aliases+=1
 cuts=delays=0
 for c in(Case(),Case(shape=1,pattern=3),Case(radius=65536,alias=3),Case(radius=0x7FFFFFFF,pattern=3)):
  full=compare(c,ims)
  for cut in range(full.all_accesses):
   ms=[]
   for ws in(ims[0],ims[2]):
    q=Oracle(ws,fixture(c),c);q.cut=cut
    try:q.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('access cut missing')
    ms.append(q)
   assert state(ms[0])==state(ms[1])and(ms[0].current_pc,ms[0].delay_of)==(ms[1].current_pc,ms[1].delay_of);cuts+=1;delays+=ms[0].delay_of is not None
 rebases=0
 for j,(entry,head)in enumerate(((0x17007FFC,0x90007FFC),(0x2500FFFC,0x90008000),(0x15008000,0x9020FFFC))):
  s=dict(D_800DBE48=head);im=images('rebase-'+str(j),entry,s)
  for x,radius,shape,alias in itertools.product((0,0x80000000),(1,65536),range(3),(0,3,4)):
   compare(Case(x,0,radius,3,shape,alias=alias),im,s,entry);rebases+=1
 return dict(cases=count,executions=count*3,reachable_words=53,slot_words=56,original_unreachable_words=[37,42,47],raw_ABI_memory_trace_and_live_roles_equal=True,normalized_complete_state_equal=True,logical_role_observations=role_cuts,guest_only_alias_cases=aliases,expected_saved_slot_alias_values_checked=True,access_prefix_cases=cuts,delay_slot_cuts=delays,rebased_cases=rebases,GNU_layouts=3,wrapped_signed32_arithmetic=True,unsigned_extent=True,late_ordinary_offset_read=True,private_raw_caller_saved_registers_not_claimed_equal=True)

def controls(body,native=False):
 changes={
 'missing_head':('u8 *node = D_800DBE48','u8 *node = NULL'),
 'signed_extent':('*(u16 *)(node + 6)','*(s16 *)(node + 6)'),
 'inclusive_x':('if (absX < limit &&','if (absX <= limit &&'),
 'inclusive_z':('absZ < limit))','absZ <= limit))'),
 'ignore_z':('absZ < limit))','(absZ | 1)))'),
 'wrong_x':('*(s16 *)(node + 8)','*(s16 *)(node + 10)'),
 'wrong_z':('*(s16 *)(node + 10)','*(s16 *)(node + 8)'),
 'no_abs_x':('absX = dx < 0 ? (s32)(0u - (u32)dx) : dx','absX = dx'),
 'no_abs_z':('absZ = dz < 0 ? (s32)(0u - (u32)dz) : dz','absZ = dz'),
 'double_extent':('*(u16 *)(node + 6)','(*(u16 *)(node + 6) * 2u)'),
 'child_field':('child = *(s16 *)(node + 12)','child = *(s16 *)(node + 4)'),
 'ordinary_field':('offset = *(s16 *)(node + 4)','offset = *(s16 *)(node + 12)'),
 'unsigned_child':('child = *(s16 *)(node + 12)','child = *(u16 *)(node + 12)'),
 'unsigned_ordinary':('offset = *(s16 *)(node + 4)','offset = *(u16 *)(node + 4)'),
 'emit_internal':('child = *(s16 *)(node + 12)','child = 0'),
 'count_step':('count++;','count += 2;'),
 'output_step':('*output++ = node;','*output = node;'),
 }
 result={}
 for name,(a,b)in changes.items():assert a in body,(name,a);result[name]=body.replace(a,b)
 if not native:
  old='                *output++ = node;\n                count++;\n                offset = *(s16 *)(node + 4);'
  new='                offset = *(s16 *)(node + 4);\n                *output++ = node;\n                count++;';assert old in body;result['early_ordinary']=body.replace(old,new)
 assert len(set(result.values()))==len(result)and body not in result.values();return result

def _native_suite(m):
 source=(m.o/'selected-semantic-input.c').read_text();head,body=source.split('/* Collect nearby leaf records',1);body='/* Collect nearby leaf records'+body;rows=[]
 for x,z,radius,pattern,shape,empty in itertools.product((0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF),(0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF),(0,1,2,0xFFFFFFFF,0x7FFFFFFF,0x80000000,0xFFFF0001),range(4),range(3),(False,True)):
  c=m.Case(x,z,radius,pattern,shape,empty);initial=m.fixture(c);_,count,found=m.reference(initial,c);fields=[]
  for node in m.NODES:fields.append([m.s16(m.read(initial,node+4,2)),m.read(initial,node+6,2),m.s16(m.read(initial,node+8,2)),m.s16(m.read(initial,node+10,2)),m.s16(m.read(initial,node+12,2))])
  array=lambda xs:'{'+','.join(map(str,xs))+'}';ids=[m.NODES.index(n)for n in found]+[-1]*(8-len(found))
  rows.append('{'+','.join(('0x%Xu'%m.u32(x),'0x%Xu'%m.u32(z),'0x%Xu'%m.u32(radius),str(-1 if empty else m.order(c)[0]),str(count),'{'+','.join(array(v)for v in fields)+'}',array(ids)))+'}')
 variants=dict(selected=body,**controls(body,True));pieces=[];names=[]
 for name,b in variants.items():n='candidate_'+name;names.append(n);pieces.append(b.replace(m.F,n))
 t=head+'\n'.join(pieces)+r'''
u8 *D_800DBE48;
typedef struct {u32 x,z,radius;s32 head,count,fields[8][5],found[8];} Row;
static const Row rows[]={ROWS};
static struct{u32 left[4];u8 bytes[131072];u32 right[4];} storage;
static struct{u32 left[4];u8*values[16];u32 right[4];} output;
static u8 before[0x180];
typedef char ABI[(sizeof(void*)==4&&sizeof(s16)==2&&sizeof(s32)==4)?1:-1];
static u8*node(s32 i){return i<0?(u8*)0:storage.bytes+i*32;}
static s32 id(u8*p){s32 i;if(!p)return -1;for(i=0;i<8;i++)if(p==node(i))return i;return -99;}
typedef s32(*Fn)(s32,s32,s32,u8**);
static int one(Fn fn,const Row*r){u32 i,j;u8*p;s32 count;
 for(i=0;i<4;i++){storage.left[i]=storage.right[i]=output.left[i]=output.right[i]=0xA5A5A5A5u;}
 for(i=0;i<0x180;i++)storage.bytes[i]=(u8)(i*13+0x5A);
 for(i=0;i<8;i++){p=node((s32)i);for(j=0;j<5;j++)*(u16*)(p+4+2*j)=(u16)r->fields[i][j];}
 for(i=0;i<0x180;i++)before[i]=storage.bytes[i];
 for(i=0;i<16;i++)output.values[i]=(u8*)(u32)0xA5A5A5A5u;
 D_800DBE48=node(r->head);count=fn((s32)r->x,(s32)r->z,(s32)r->radius,output.values);
 if(count!=r->count||D_800DBE48!=node(r->head))return 1;
 for(i=0;i<(u32)count;i++)if(id(output.values[i])!=r->found[i])return 2;
 for(;i<16;i++)if(output.values[i]!=(u8*)(u32)0xA5A5A5A5u)return 3;
 for(i=0;i<0x180;i++)if(storage.bytes[i]!=before[i])return 4;
 for(i=0;i<4;i++)if(storage.left[i]!=0xA5A5A5A5u||storage.right[i]!=0xA5A5A5A5u||output.left[i]!=0xA5A5A5A5u||output.right[i]!=0xA5A5A5A5u)return 5;
 return 0;
}
static int run(void){Fn fns[]={FUNCTIONS};u32 n,i;int rejected;
 for(n=0;n<sizeof(fns)/sizeof(fns[0]);n++){rejected=0;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){int e=one(fns[n],&rows[i]);if(!n&&e)return e;if(e){rejected=1;break;}}if(n&&!rejected)return 50+n;}return 0;}
'''
 t=t.replace('ROWS',',\n'.join(rows)).replace('FUNCTIONS',','.join(names))+m.START;path=m.o/'native-spatial-query.c';path.write_text(t);profiles={}
 for opt in('-O0','-O2','-O3'):
  binary=m.o/('native-spatial-query'+opt);q=subprocess.run(m.native_command(opt)+['-mstackrealign',str(path),'-o',str(binary)],capture_output=True,text=True);binary.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);assert q.returncode==0 and not q.stderr,(opt,q.stdout,q.stderr)
  q=subprocess.run([str(binary)],capture_output=True,timeout=60);assert q.returncode==0,(opt,q.returncode);profiles[opt]=dict(exit=0,UBSan=True)
 return dict(cases_per_profile=len(rows),profiles=profiles,compiled_controls=len(names)-1,all_effective=True,wrapped_signed32_values=True,unsigned_extent=True,signed_relative_offsets=True,real_allocated_backing_and_canaries=True,output_aliases_guest_only=True,invalid_unsigned_offset_controls_land_in_allocated_zero_sentinels=True)

def _compiled_controls(m):
 text=(m.o/'selected-semantic-input.c').read_text();head,body=text.split('/* Collect nearby leaf records',1);body='/* Collect nearby leaf records'+body;out={}
 cases=[m.Case(alias=3),m.Case(),m.Case(x=1),m.Case(z=1)]
 cases.extend(m.Case(x,z,radius,pattern,shape)for x,z,radius,pattern,shape in itertools.product((0,1,0xFFFFFFFF,32767,0xFFFF8000,0x80000000),(0,1,0xFFFFFFFF),(0,1,65536,0x7FFFFFFF),range(4),range(3)))
 for name,b in controls(body).items():
  obj,diag=m.compile_owner(m.r,m.o,head+b,'negative-'+name);assert not diag;ws=m.linked(obj,'negative-linked-'+name);witness=None
  for c in cases:
   initial=m.fixture(c)
   for node in m.NODES:
    for i in range(32):initial[node+65536+i]=0
   want,n,found=m.reference(initial,c);q=m.Oracle(ws,initial,c,track=False).run()
   if(m.public(q.memory),q.r[2])!=(m.public(want),n):witness=[c.x,c.z,c.radius,c.pattern,c.shape,c.alias];break
  assert witness is not None,('ineffective compiled control',name);out[name]=witness
 return dict(count=len(out),effective_IDO_controls=out,compile_or_oracle_errors_not_accepted=True,wrong_unsigned_offsets_have_mapped_zero_sentinels=True,late_ordinary_offset_alias_witness=True)

def _caller_suite(m):
 rom=(m.r/'conker/conker.us.bin').read_bytes();pointer=struct.pack('>I',m.ENTRY);jal=struct.pack('>I',0x0C000000|((m.ENTRY>>2)&0x3FFFFFF))
 assert[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal]==[0x1B3A10]and not[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==pointer]
 start=0x15186554;ends=(0x15186570,0x1518677C);ws=list(struct.unpack_from('>7I',rom,0x1B3A04));assert ws[3]==0x0C000000|((m.ENTRY>>2)&0x3FFFFFF)
 class Boundary(Exception):pass
 class Window(m.RoleCode):
  def __contains__(self,pc):return pc in ends or super().__contains__(pc)
  def __getitem__(self,pc):
   if pc in ends:self.owner.window_exit=pc;raise Boundary
   return super().__getitem__(pc)
 ims=m.images('caller');count=0;outcomes=set()
 for x,z,radius,pattern,shape,empty,phase in itertools.product((0,1,0x80000000),(0,1,0x80000000),(0,1,65536),range(4),range(3),(False,True),(0,8)):
  c=m.Case(x,z,radius,pattern,shape,empty,phase=phase);initial=m.fixture(c);sp=m.STACK+phase;out=sp+0x330
  for offset,value in((0x370,x),(0x374,z),(0x378,radius)):m.put(initial,sp+offset,value)
  want,n,found=m.reference(initial,c,out=out);ms=[]
  for i,body in enumerate(ims):
   q=m.Oracle(ws,initial,c,start,raw=i==1,connected={m.ENTRY+4*k:w for k,w in enumerate(body)});q.code=Window(dict(q.code),q)
   try:q.run()
   except Boundary:pass
   else:raise AssertionError('caller boundary missing')
   assert(m.public(q.memory),q.r[2],q.calls)==(m.public(want),n,[(m.ENTRY,tuple(map(m.u32,(x,z,radius,out))))]),c
   assert[m.read(q.memory,out+4*k)for k in range(n)]==found and q.window_exit==(ends[0]if n else ends[1]);ms.append(q);outcomes.add(q.window_exit)
  assert m.state(ms[0])==m.state(ms[2])
  assert(ms[0].memory,ms[0].trace,ms[0].roles,ms[0].r[8],ms[0].r[16:24],ms[0].r[29],ms[0].r[31])==(ms[1].memory,ms[1].trace,ms[1].roles,ms[1].r[8],ms[1].r[16:24],ms[1].r[29],ms[1].r[31]);count+=1
 assert outcomes==set(ends)
 return dict(cases=count,parent='func_1518652C',original_window_words=7,call='0x15186560',output_stack_offset=0x330,count_controls_original_branch=True,both_original_branch_exits=True,preceding_context_setup_and_remaining_parent_bounded=True,full_parent_or_gameplay_claimed=False)

def native_suite():
 import sys
 return _native_suite(sys.modules[__name__])
def compiled_controls():
 import sys
 return _compiled_controls(sys.modules[__name__])
def caller_suite():
 import sys
 return _caller_suite(sys.modules[__name__])
