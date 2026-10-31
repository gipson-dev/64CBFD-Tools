"""Message receive: frame, signed prefixes, real ring helpers and Init wrapper."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess,hashlib
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments import game_ring_message_receive_match as source
r=Path.cwd();o=r/source.BUILD
F,OWNER,ENTRY,ROM='func_15043CA4','game_70200',0x15043CA4,0x71154
READ,SKIP,COPY=0x15043AC8,0x15043B70,0x10022EC0
QUEUE,RING,OTHER,OUTPUT=0x220000,0x230000,0x240000,0x250000
SYMS=dict(func_15043AC8=READ,func_15043B70=SKIP)
signed=lambda x:(x&0xFFFFFFFF)-0x100000000 if x&0x80000000 else x&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 size:int=16
 cursor:int=15
 length:int=5
 limit:int=3
 empty:bool=False
 phase:int=0
 mode:int=0
 alias:bool=False
 queue:int=QUEUE
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,256)}
 for base,size in((c.queue-16,64),(RING-16,128),(OTHER-16,128),(OUTPUT-16,128)):
  m.update({base+i:(i*13+base//4096)&255 for i in range(size)})
 for i,b in enumerate(struct.pack('>I',c.length&0xFFFFFFFF)):
  put(m,RING+(c.cursor+i)%c.size,b,1)
 put(m,c.queue,RING);put(m,c.queue+4,c.size);put(m,c.queue+8,c.cursor)
 put(m,c.queue+12,c.cursor if c.empty else(c.cursor+4+(c.length&31))%c.size)
 return m
def output(c):return c.queue+12 if c.alias else OUTPUT
def effects(m,c):
 if c.mode&1:put(m,c.queue,OTHER);put(m,c.queue+4,32)
 if c.mode&2:put(m,c.queue+12,0x12345678)
def reference(initial,c):
 m=dict(initial);transfers=[];cursor=read(m,c.queue+8);message=0
 if cursor==read(m,c.queue+12):return m,transfers,0
 def transfer(dest,n,cursor):
  ring,size=read(m,c.queue),read(m,c.queue+4)
  for i in range(n):put(m,dest+i,read(m,ring+(cursor+i)%size,1),1)
  return(cursor+n)%size if n else cursor
 header=STACK+c.phase-8
 cursor=transfer(header,4,cursor);message=read(m,header);effects(m,c)
 limit=signed(c.limit)
 if limit<signed(message):
  limit=signed((limit-1)&0xFFFFFFFF);assert limit>=0
  cursor=transfer(output(c),limit,cursor);put(m,output(c)+limit,0,1)
  cursor=(cursor+message-limit)%read(m,c.queue+4)
 elif message:cursor=transfer(output(c),message,cursor)
 put(m,c.queue+8,cursor)
 return m,transfers,message
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+256}
class TransferStop(Exception):pass
class Oracle(TimingOracle):
 def __init__(self,w,m,c=Case(),entry=ENTRY,s=SYMS,connected=None,stop=None):
  self.c,self.s,self.trace,self.transfer_reads,self.stop=c,s,[],0,stop
  super().__init__(w,m,phase=c.phase,entry=entry,arguments=(c.queue,output(c),c.limit&0xFFFFFFFF),connected=connected)
  self.code=TrackedCode(dict(self.code),self);self.current_pc=entry;self.delay_of=None
  self.root_entry,self.root_size,self.root_accesses,self.root_fault=entry,len(w)*4,0,None
  self.hi=self.lo=0
 def access(self):
  if self.own_instruction and self.root_entry<=self.current_pc<self.root_entry+self.root_size:
   if self.root_accesses==self.root_fault:raise AccessBoundary
   self.root_accesses+=1
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  n=5 if t==self.s['func_15043AC8']else 4 if t==self.s['func_15043B70']else 3 if t==COPY or t==ENTRY else None
  assert n is not None,hex(t)
  args=tuple(self.arguments(n));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==self.s['func_15043AC8']:
   self.transfer_reads+=1
   if self.transfer_reads==self.stop:raise TransferStop
 def hook(self,t):
  args=self.calls[-1][1]
  if t==self.s['func_15043AC8']:
   ring,size,cursor,dest,n=args;assert n<=64 and size>0
   for i in range(n):put(self.memory,dest+i,read(self.memory,ring+(cursor+i)%size,1),1)
   value=(cursor+n)%size if n else cursor
   if self.transfer_reads==1:effects(self.memory,self.c)
  elif t==self.s['func_15043B70']:
   ring,size,cursor,n=args;assert n<=64 and size>0;value=(cursor+n)%size if n else cursor
  elif t==COPY:
   dest,src,n=args;assert n<=128
   for i in range(n):put(self.memory,dest+i,read(self.memory,src+i,1),1)
   value=dest
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value
  self.hi,self.lo=0xA5000010,0xA5000011
def normalized(raw,bindings):
 assert len(raw)==232
 words=list(struct.unpack('>58I',raw))
 for row in json.loads((o/'new-guard-rows.json').read_text()):
  at=int(row['offset'],0);assert at not in bindings and words[at//4]==int(row['expected'],0)
  words[at//4]=int(row['replacement'],0)
 return struct.pack('>58I',*words),bindings
def linked(obj,label,entry=ENTRY,s=SYMS,normalize=False):
 text,fs,rs=parse_object(obj);info=fs[F]
 if normalize:
  at,size=info['value'],info['size'];text,rs=normalized(text[at:at+size],{p-at:v for p,v in rs.items()if at<=p<at+size});info=dict(info,value=0,size=len(text))
 asm,unknown=emit_function(text,info,rs,F,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>58I',sections(p.with_suffix('.elf'))['.text'][1][:232]))
def images(label,entry=ENTRY,s=SYMS):
 names=('original-func_15043CA4.o','selected-final.o','qualified-padded.o','make-shadow/src/game_70200.c.o')
 roots=[linked(o/n,label+'-'+str(i),entry,s,i==1)for i,n in enumerate(names)]
 assert all(x==roots[0]for x in roots)
 return roots,linked(o/'selected-final.o',label+'-raw',entry,s)
def cases():
 for size in(5,7,16,32):
  for cursor,length,limit,empty,phase,mode in itertools.product((0,size-1,size),sorted({0,1,max(0,size-5)}),range(1,5),(False,True),(0,8),(0,3)):
   if length>size-5:continue
   yield Case(size,cursor,length,limit,empty,phase,mode)
def compare(roots,c,entry=ENTRY,s=SYMS,connected=None):
 words,raw=roots;initial=fixture(c);wanted,_,answer=reference(initial,c)
 models=[Oracle(w,initial,c,entry,s,connected).run()for w in words]
 for m in models:assert public(m.memory)==public(wanted)and m.r[2]==answer,(c,'state/return')
 for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace
 plain=Oracle(raw,initial,c,entry,s,connected).run()
 assert plain.memory==models[0].memory and plain.r[2]==answer and plain.calls==models[0].calls and plain.trace==models[0].trace
 for reg in(*range(16,24),28,29,30,31):assert plain.r[reg]==models[0].r[reg]
 return models[0]
def guest_suite():
 count=cuts=delays=prefixes=aliases=0;seen=set()
 for j,entry in enumerate((ENTRY,0x17007FFC,0x2500FFFC)):
  s=SYMS if not j else dict(func_15043AC8=entry+0x10000,func_15043B70=entry+0x20000)
  roots=images('receive-rebase-'+str(j),entry,s)
  for c in cases():
   m=compare(roots,c,entry,s);seen.update(p-entry for p in m.visits if entry<=p<entry+232);count+=1
  if not j:
   for length,limit,phase in itertools.product((0,1,4),(1,2,4,5),(0,8)):
    compare(roots,Case(16,15,length,limit,False,phase,3,True));aliases+=1
   for c in(Case(),Case(empty=True),Case(length=0),Case(limit=9)):
    initial=fixture(c);good=Oracle(roots[0][0],initial,c).run()
    for cut in range(good.root_accesses):
     models=[]
     for w in roots[0]:
      m=Oracle(w,initial,c);m.root_fault=cut
      try:m.run()
      except AccessBoundary:pass
      else:raise AssertionError('Ineffective prefix cut')
      models.append(m)
     for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and(m.current_pc,m.delay_of)==(models[0].current_pc,models[0].delay_of)
     cuts+=1;delays+=models[0].delay_of is not None
   for length,limit in itertools.product((0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,-1,-2147483648,1,2147483647)):
    c=Case(length=length,limit=limit);initial=fixture(c)
    # A bounded header provider publishes arbitrary words. Stop at the first
    # payload submission, before an invalid huge/negative native copy.
    class Prefix(Oracle):
     def hook(self,t):
      if t==READ and self.transfer_reads==1:
       args=self.calls[-1][1];put(self.memory,args[3],length);self.r[2]=4;return
      return super().hook(t)
    all_models=[]
    for w in(*roots[0],roots[1]):
     m=Prefix(w,initial,c,stop=2)
     try:m.run()
     except TransferStop:pass
     all_models.append(m)
    for m in all_models[1:]:assert m.memory==all_models[0].memory and m.calls==all_models[0].calls and m.r[2]==all_models[0].r[2]
    if all_models[0].transfer_reads==2:prefixes+=1
 assert set(range(0,232,4))-seen=={0x48},sorted(set(range(0,232,4))-seen)
 return dict(cases=count,normalized_executions=count*4,raw_executions=count,retail_body_words=58,slot_words=59,alignment_words=1,reachable_words=57,unreachable_offsets=['0x48'],independent_rebases=3,aliases=aliases,access_prefix_cases=cuts,branch_delay_cuts=delays,bounded_signed_payload_prefixes=prefixes,raw_public_state_return_and_trace_equal=True,raw_temporary_register_difference=True,invalid_huge_copy_native_claim=False)
def connected_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();delta=ENTRY-ROM;code={}
 for address,length,offset in((READ,168,READ-delta),(SKIP,72,SKIP-delta),(COPY,44,0x22EC0)):
  code.update({address+4*i:w for i,w in enumerate(struct.unpack_from('>%dI'%(length//4),rom,offset))})
 roots=images('receive-connected');count=0
 for c in cases():
  if c.mode:continue
  compare(roots,c,connected=code);count+=1
 return dict(cases=count,normalized_executions=count*4,raw_executions=count,original_ring_reader_words=42,original_skipper_words=18,original_memcpy_words=11,actual_header_payload_skip_paths=True,whole_owner_byte_identity_reuses_existing_transfer_qualification=True,producer_or_gameplay_claim=False)
def caller_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();at=0x126E8
 # Bound the wrapper by its next retail entry. Its final alignment word is
 # harmless because execution returns through the original JR before it.
 words=list(struct.unpack_from('>12I',rom,at));roots=images('receive-init-wrapper')
 count=0
 for c in itertools.product((0,1,5),(1,3,9),(False,True),(0,8)):
  c=Case(16,15,c[0],c[1],c[2],c[3],queue=0x800427A0);initial=fixture(c)
  class Caller(Oracle):
   def record_call(self,t):
    if t==ENTRY:
     args=tuple(self.arguments(3));assert args==(c.queue,output(c),c.limit&0xFFFFFFFF)
     self.calls.append((t,args));self.events.append(('CALL',t,args))
    else:super().record_call(t)
  models=[]
  for body in(*roots[0],roots[1]):
   m=Caller(words,initial,c,0x100126E8,connected={ENTRY+4*i:w for i,w in enumerate(body)})
   m.r[4],m.r[5]=output(c),c.limit&0xFFFFFFFF
   m.run();models.append(m)
  for m in models[1:]:assert public(m.memory)==public(models[0].memory)and m.r[2]==models[0].r[2]and m.calls==models[0].calls
  count+=1
 return dict(cases=count,normalized_executions=count*4,raw_executions=count,original_wrapper_slot_words=12,original_fixed_queue_address=True,original_arg_move_and_call_delay_slot_executed=True,original_wrapper_executed_without_argument_redirection=True)

from tools.experiments import game_ring_buffer_transfers as transfers
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
START=START.replace("void _start(void)","__attribute__((force_align_arg_pointer)) void _start(void)")
PREAMBLE=r'''
static u8 firstRing[64],secondRing[64],linear[96],expectedLinear[96];
static struct105 state;
static unsigned calls,skips,effects,failed;
static u8 *dest;
static unsigned lengthValue,limitValue,firstSize,firstCursor,headerCursor,newSize;
void *memcpy(void *destination,const void *source,u32 n) {
 u8 *d=destination;const u8 *s=source;void *answer=destination;
 while(n--)*d++=*s++;
 return answer;
}
'''
WRAPPERS=r'''
s32 func_15043AC8(u8 *ring,s32 size,s32 cursor,u8 *out,s32 count) {
 s32 result;unsigned expectedCount;
 ++calls;
 expectedCount=calls==1?4:limitValue<lengthValue?limitValue-1:lengthValue;
 if((unsigned)count!=expectedCount)failed=1;
 if(calls==1) {
  if(ring!=firstRing||(unsigned)size!=firstSize||(unsigned)cursor!=firstCursor||out==dest)failed=1;
 } else if(ring!=(u8 *)state.unk0||(unsigned)size!=newSize||(unsigned)cursor!=headerCursor||out!=dest)failed=1;
 result=read_impl(ring,size,cursor,out,count);
 if(calls==1) {
  if(effects&1){state.unk0=(s32)secondRing;state.unk4=32;}
  if(effects&2)state.unkC=0x12345678;
 }
 return result;
}
s32 func_15043B70(s32 ring,s32 size,s32 cursor,s32 count) {
 ++skips;
 if(ring!=state.unk0||size!=state.unk4||
    (unsigned)cursor!=(headerCursor+limitValue-1)%newSize||
    (unsigned)count!=lengthValue-(limitValue-1))failed=1;
 return skip_impl(ring,size,cursor,count);
}
'''
HARNESS=r'''
static int checkCase(unsigned cap,unsigned start,unsigned length,unsigned limit,unsigned mode,unsigned align,int alias) {
 struct105 wanted;unsigned i,copied,final;u32 header=length;u8 *out;u8 *bytes=(u8 *)&header;
 u8 *source;calls=skips=failed=0;effects=mode;
 for(i=0;i<64;i++){firstRing[i]=(u8)(i*13+0xA5);secondRing[i]=(u8)(i*17+0x59);}
 for(i=0;i<4;i++)firstRing[(start+i)%cap]=bytes[i];
 for(i=0;i<96;i++)linear[i]=expectedLinear[i]=(u8)(i*29+0x71);
 state.unk0=(s32)firstRing;state.unk4=(s32)cap;state.unk8=(s32)start;state.unkC=(s32)((start+4+length)%cap);wanted=state;
 out=alias?(u8 *)&state.unkC:linear+16+align;dest=out;
 lengthValue=length;limitValue=limit;firstSize=cap;firstCursor=start;headerCursor=(start+4)%cap;newSize=mode&1?32:cap;
 if(mode&1){wanted.unk0=(s32)secondRing;wanted.unk4=32;}
 if(mode&2)wanted.unkC=0x12345678;
 source=mode&1?secondRing:firstRing;
 copied=limit<length?limit-1:length;
 for(i=0;i<copied;i++) {
  u8 value=source[(headerCursor+i)%newSize];
  if(alias)((u8 *)&wanted.unkC)[i]=value;else expectedLinear[16+align+i]=value;
 }
 if(limit<length) {
  if(alias)((u8 *)&wanted.unkC)[copied]=0;else expectedLinear[16+align+copied]=0;
 }
 final=length?(headerCursor+length)%newSize:headerCursor;wanted.unk8=(s32)final;
 if((u32)func_15043CA4(&state,out,(s32)limit)!=length||failed)return 1;
 if(calls!=(length||limit<length?2u:1u)||skips!=(limit<length))return 1;
 for(i=0;i<sizeof(state);i++)if(((u8 *)&state)[i]!=((u8 *)&wanted)[i])return 1;
 for(i=0;i<96;i++)if(linear[i]!=expectedLinear[i])return 1;
 return 0;
}
static int run(void) {
 static const unsigned capacities[4]={5,7,16,32};
 static const u32 words[8]={0,1,7,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu,0x87654321u,0xFFFFFFFEu};
 unsigned k,cap,start,length,limit,mode,align,i,j,z;struct105 old;
 for(k=0;k<4;k++) {
  cap=capacities[k];
  for(start=0;start<=cap;start++)for(length=0;length<=cap-5;length++)
   for(limit=0;limit<=length+2;limit++) {
    if(!limit&&length)continue;
    for(mode=0;mode<4;mode++)for(align=0;align<2;align++)
     if(checkCase(cap,start,length,limit,mode,align,0))return 1;
   }
 }
 for(k=0;k<2;k++) {
  cap=k?32:16;
  for(i=0;i<3;i++)for(length=0;length<=4;length++)for(limit=0;limit<=6;limit++) {
   if(!limit&&length)continue;
   for(mode=0;mode<4;mode++)if(checkCase(cap,i==0?0:i==1?cap-1:cap,length,limit,mode,0,1))return 1;
  }
 }
 for(i=0;i<8;i++)for(j=0;j<8;j++)for(z=0;z<8;z++) {
  state.unk0=0;state.unk4=(s32)words[i];state.unk8=state.unkC=(s32)words[j];old=state;calls=skips=failed=0;
  if(func_15043CA4(&state,(u8 *)0,(s32)words[z])!=0||calls||skips||failed)return 1;
  if(state.unk0!=old.unk0||state.unk4!=old.unk4||state.unk8!=old.unk8||state.unkC!=old.unkC)return 1;
 }
 return 0;
}
'''
def native_suite():
 selected=source.HEADERS+source.SELECTED;at=selected.index('/* Receive one')
 headers,body=selected[:at],selected[at:]
 from tools.experiments.game_remaining_donor_candidates import body as extract
 before=(r/source.BUILD/'before-conker_src_game_70200.c').read_text()
 helper=transfers.SELECTED['func_15043AC8'].replace('func_15043AC8(','read_impl(',1)+'\n'+extract(before,'func_15043B70').replace('func_15043B70(','skip_impl(',1)
 controls={
  'invert-empty':body.replace('queue->unk8 == queue->unkC','queue->unk8 != queue->unkC'),
  'short-header':body.replace('(u8 *)&messageLength, 4','(u8 *)&messageLength, 3'),
  'wrong-truncation-boundary':body.replace('capacity < messageLength','capacity + 1 < messageLength'),
  'no-terminator-reserve':body.replace('capacity = (s32)((u32)capacity - 1);','capacity = capacity;'),
  'wrong-terminator-position':body.replace('output[capacity] = 0','output[0] = 0'),
  'skip-one-too-few':body.replace('(u32)messageLength - (u32)capacity','(u32)messageLength - (u32)capacity - 1'),
  'wrong-return-length':body.replace('return messageLength;','return capacity;'),
  'missing-publication':body.replace('queue->unk8 = cursor;','queue->unk8 = queue->unk8;'),
 }
 assert all(text!=body for text in controls.values());results=[]
 jobs=[('positive-'+opt,opt,body,False)for opt in('-O0','-O2','-O3')]
 jobs.extend((name,'-O2',text,True)for name,text in controls.items())
 for name,opt,text,control in jobs:
  p=o/('native-'+name);p.with_suffix('.c').write_text(headers+PREAMBLE+helper+WRAPPERS+text+HARNESS+START)
  q=subprocess.run(native_command(opt)+['-o',str(p),str(p.with_suffix('.c'))],capture_output=True,text=True);assert q.returncode==0,(name,q.stdout,q.stderr)
  q=subprocess.run([str(p)],capture_output=True);assert q.returncode==(1 if control else 0),(name,q.returncode,q.stderr)
  results.append(dict(name=name,optimization=opt,control=control,exit=q.returncode))
 count=sum((cap+1)*sum(3 if n==0 else n+2 for n in range(cap-4))*8 for cap in(5,7,16,32))+2*3*(7+4*6)*4+512
 return dict(positive_cases_each=count,profiles=['O0','O2','O3'],effective_controls=8,controls_exit_by_semantic_mismatch=True,UBSan_trapping=True,
             real_existing_read_and_skip_C=True,all_valid_ring_positions_and_truncation_sizes=True,
             queue_field_reload_mutations=True,output_aliases_write_cursor=True,empty_unbacked_word_cases=512,
             invalid_nonempty_negative_or_huge_copy_native_claim=False,host_header_order_not_guest_wire_claim=True,results=results)
