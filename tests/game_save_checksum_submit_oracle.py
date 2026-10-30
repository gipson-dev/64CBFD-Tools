"""Checksum submission: original instructions, bounded providers and SDK32 C."""
from pathlib import Path
from dataclasses import dataclass
import csv,hashlib,io,itertools,json,random,re,struct,subprocess,sys
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
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
r=Path.cwd();o=r/'conker/build/game-save-checksum-submit-15007360-match';F='func_15007360';ENTRY=0x15007360;HELPER=0x151DCEF0
SYMS=dict(D_800BE2F0=0x800BE2F0,D_800BE2F2=0x800BE2F2,D_800BE2F3=0x800BE2F3,D_800BE2F4=0x800BE2F4,D_8002AC5C=0x8002AC5C,D_800BE900=0x800BE900,func_151DCEF0=HELPER)
u32=lambda v:v&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 first:int=17
 second:int=91
 pattern:int=0
 flag:int=0
 result:int=0x89ABCDEF
 effect:int=0
 phase:int=0
 seed:int=0

def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed)&255 for i in range(-1024,256)};block=s['D_800BE2F0']
 for base,length in ((block-8,128),(s['D_800BE900'],32),(s['D_8002AC5C'],1)):
  for i in range(length):m[base+i]=(i*13+c.seed)&255
 for i in range(112):m[block+i]=(0,255,i*7+c.seed,(1<<(i&7)),(i*37+c.seed)^0x80)[c.pattern%5]&255
 m[s['D_800BE2F2']]=c.first;m[s['D_800BE2F3']]=c.second;m[s['D_8002AC5C']]=c.flag
 return m

def checksum(m,s=SYMS):
 a=s['D_800BE2F0'];total=204+4*m[a+2]+8*m[a+3]
 for i in range(4,104):total+=(1<<(i%4))*m[a+i]
 return total&65535

def effect(m,c,s=SYMS):
 a=s['D_800BE2F0']
 if c.effect&1:m[s['D_8002AC5C']]=255
 if c.effect&2:put(m,a,0xF00D,2)
 if c.effect&4:
  for i in range(4,104):m[a+i]=(i*31+c.seed)&255

def reference(initial,c,s=SYMS):
 m=dict(initial);a=s['D_800BE2F0'];put(m,a,checksum(m,s),2);args=[];observations=[]
 if m[s['D_8002AC5C']]==0:
  args=[(s['func_151DCEF0'],(s['D_800BE900'],68,a,112))];observations=[bytes(m[a+i]for i in range(112))];effect(m,c,s)
 return m,args,observations

def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+256}

class Oracle(RayOracle):
 def __init__(self,words,memory,c=Case(),s=SYMS,entry=ENTRY,connected=None):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(0x12345678,),connected=connected);self.c=c;self.s=s;self.trace=[];self.observations=[]
 def execute(self,word):
  if word>>26==0 and word&63==4:
   rs,rt,rd=word>>21&31,word>>16&31,word>>11&31;self.r[rd]=u32(self.r[rt]<<(self.r[rs]&31));self.r[0]=0
  else:super().execute(word)
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
 def record_call(self,target):
  assert target==self.s['func_151DCEF0'],('unbounded target',hex(target));args=self.arguments(4);self.calls.append((target,args));self.events.append(('CALL',target,args));a=self.s['D_800BE2F0'];self.observations.append(bytes(self.memory[a+i]for i in range(112)))
 def hook(self,target):
  assert target==self.s['func_151DCEF0'];effect(self.memory,self.c,self.s)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=self.c.result

def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.observations,m.condition)

def cases():
 yield Case(first=255,second=255,pattern=1)
 yield Case(first=0,second=0,pattern=0,flag=1)
 for n in range(256):
  yield Case(first=n,second=255-n,pattern=n%5,flag=n&1,seed=n)
  yield Case(first=255-n,second=n,pattern=(n+1)%5,flag=0,effect=n&7,result=u32(n*0x1020304),phase=8,seed=n)
 for flag in range(256):yield Case(flag=flag,pattern=flag%5)
 for lane,byte in itertools.product(range(4),(0,1,127,128,255)):yield Case(first=lane,second=byte,pattern=4,seed=byte)
 for pattern,flag,result,eff,phase in itertools.product(range(5),(0,1),(0,1,0xFFFFFFFF,0x80000000),range(8),(0,8)):yield Case(pattern=pattern,flag=flag,result=result,effect=eff,phase=phase)
 rng=random.Random(0x15007360)
 for i in range(256):yield Case(rng.randrange(256),rng.randrange(256),i%5,rng.randrange(256)if i&1 else 0,rng.getrandbits(32),i&7,8*(i&1),rng.randrange(256))

def check_model(m,initial,c,s=SYMS):
 want,calls,obs=reference(initial,c,s);assert(public(m.memory),m.calls,m.observations)==(public(want),calls,obs),c
 sp=STACK+c.phase;put(want,sp-32+20,m.before[31]);
 if calls:
  for i in range(4):put(want,sp-32+4*i,0xB5000000+i)
  put(want,sp-32+24,c.result)
 assert m.memory==want,('private memory',c)
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30]==m.before[30]and m.f[20:]==m.saved_f

def guest_suite():
 images=[linked(o/p,'guest-'+str(i))for i,p in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];assert images[0]==images[2];visits=set();count=0
 for c in cases():
  initial=fixture(c);ms=[]
  for w in images:m=Oracle(w,initial,c).run();check_model(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]),c;visits.update(ms[0].visits);count+=1
 assert set(range(ENTRY,ENTRY+224,4))<=visits
 prefixes=delays=0
 for c in (Case(flag=1),Case(effect=7,result=0xFFFFFFFF,phase=8)):
  full=Oracle(images[0],fixture(c),c).run()
  for cut in range(full.root_accesses):
   ms=[]
   for w in images:
    m=Oracle(w,fixture(c),c);m.root_fault=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('missing access cut',cut))
    ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2])and(ms[0].current_pc,ms[0].delay_of)==(ms[1].current_pc,ms[1].delay_of);prefixes+=1;delays+=ms[0].delay_of is not None
 rebases=[]
 for j,(entry,base)in enumerate(((0x17007FFC,0x80017FFC),(0x2500FFFC,0x8001FFFC),(0x15008000,0x80028000))):
  s=dict(SYMS,D_800BE2F0=base,D_800BE2F2=base+2,D_800BE2F3=base+3,D_800BE2F4=base+4,D_8002AC5C=0x80060000+j*0x100,D_800BE900=0x80070000+j*0x100,func_151DCEF0=entry+0x10004);ps=[linked(o/p,'rebase-'+str(j)+'-'+str(i),entry,s)for i,p in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];assert ps[0]==ps[2]
  for c in itertools.islice(cases(),0,None,101):
   initial=fixture(c,s);ms=[]
   for w in ps:m=Oracle(w,initial,c,s,entry).run();check_model(m,initial,c,s);ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebases.append((j,c.seed))
 return dict(cases=count,executions=count*3,covered_words=56,access_prefix_cases=prefixes,delay_slot_cuts=delays,rebased_cases=len(rebases),GNU_rebase_layouts=3,raw_normalized_original_full_state_and_trace_equal=True,frame=32,RA_offset=20,result_offset=24,callback_pre_submit_block_observed=True,portable_fault_or_EEPROM_hardware_claim=False)

class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
 def __getitem__(self,pc):
  if pc==self.owner.window_end:raise WindowBoundary
  return super().__getitem__(pc)

def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();words=list(struct.unpack_from('>4I',rom,0x49B74));literal={int(a,16):int(w,16)for a,w in re.findall(r'/\*\s*[0-9A-F]+\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',(r/'conker/asm/48FD0.s').read_text())};assert words==[literal[0x1501C6C4+i*4]for i in range(4)]
 jal=struct.pack('>I',0x0C000000|((ENTRY>>2)&0x3FFFFFF));ptr=struct.pack('>I',ENTRY);assert [i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal]==[0x49B74];pointers=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==ptr]
 class Caller(Oracle):
  def record_call(self,target):
   if target==ENTRY:self.calls.append((target,()));self.events.append(('CALL',target,()))
   else:super().record_call(target)
 images=[linked(o/p,'caller-body-'+str(i))for i,p in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];count=0
 for c in itertools.islice(cases(),0,None,47):
  ms=[]
  for ws in images:
   m=Caller(words,fixture(c),c,entry=0x1501C6C4,connected={ENTRY+4*i:w for i,w in enumerate(ws)});m.window_end=0x1501C6EC;m.code=WindowCode(dict(m.code),m)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   want,calls,obs=reference(fixture(c),c);assert public(m.memory)==public(want)and m.calls==[(ENTRY,()),*calls]and m.observations==obs;ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
 asm=(r/'conker/asm/48FD0.s').read_text();parent=re.findall(r'^glabel (\S+)',asm[:asm.index('1501C6C4')],re.M)[-1];assert 's32 '+parent+'() {\n    return 0;\n}'in(r/'conker/src/game/generated_48FD0.c').read_text()
 return dict(parent=parent,window_words=4,window_VA='0x1501C6C4',window_ROM='0x49B74',cases=count,aligned_JALs=1,function_pointer_ROM_offsets=pointers,void_no_argument_contract=True,current_parent_still_stub=True,complete_parent_claimed=False)

def guard_suite():
 import tools.pad_generated_object as pad
 sys.modules.setdefault('pad_generated_object',pad)
 from tools.pad_c_object import emit_padded_assembly
 guards=json.loads((o/'new-guard-rows.json').read_text());before=(o/'before-conker_retail_word_patches.us.csv').read_bytes();assert len(guards)==9 and(o/'proposed-guards.csv').read_bytes().startswith(before)
 def write(rows,name):
  s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=tuple(guards[0]),lineterminator='\n');w.writerows(rows);p=o/name;p.write_bytes(before+s.getvalue().encode());return p
 count=0
 for i,row in enumerate(guards):
  rows=[dict(x)for x in guards];rows[i]['expected']='0x%08X'%(int(row['expected'],16)^1);p=write(rows,'negative-guard-'+str(i)+'.csv')
  try:emit_padded_assembly(o/'after-owner.o',r/'conker/retail_layout.us.txt','game_33990',word_patches_path=p)
  except ValueError:count+=1
  else:raise AssertionError(('accepted bad preimage',i))
 for i in range(3):
  rows=[dict(x)for x in guards];rows[i]['expected_relocations']='R_MIPS_LO16:func_15007360';p=write(rows,'negative-reloc-'+str(i)+'.csv')
  try:emit_padded_assembly(o/'after-owner.o',r/'conker/retail_layout.us.txt','game_33990',word_patches_path=p)
  except ValueError:count+=1
  else:raise AssertionError(('accepted bad binding',i))
 rows=[dict(x)for x in guards];rows[0]['function']='foreign';p=write(rows,'negative-function.csv')
 try:emit_padded_assembly(o/'after-owner.o',r/'conker/retail_layout.us.txt','game_33990',word_patches_path=p)
 except ValueError:count+=1
 else:raise AssertionError('accepted foreign function')
 assert emit_padded_assembly(o/'after-owner.o',r/'conker/retail_layout.us.txt','game_33990',word_patches_path=o/'proposed-guards.csv')==(o/'qualified-padded.s').read_text()
 # Each changed window is a closed permutation of pure integer operations.
 def dag(ws):
  regs=[0]+[('input',i)for i in range(1,32)]
  for w in ws:
   op,rs,rt,rd,fn,imm=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63,w&65535;a,b=regs[rs],regs[rt]
   if op==15:regs[rt]=imm<<16
   elif op==9:
    val=(imm^32768)-32768;regs[rt]=u32(a+val)if isinstance(a,int)else('add',a,val)
   elif op==12:regs[rt]=('and',a,imm)
   elif op==0 and fn==37:regs[rd]=a if b==0 else b if a==0 else('or',a,b)
   elif op==0 and fn==33:regs[rd]=('add',a,b)
   else:raise AssertionError(('non-closed operation',hex(w)))
  return regs
 for j,(entry,base)in enumerate(((ENTRY,SYMS['D_800BE2F0']),(0x17007FFC,0x80017FFC),(0x2500FFFC,0x8001FFFC),(0x15008000,0x80028000))):
  s=dict(SYMS,D_800BE2F0=base,D_800BE2F2=base+2,D_800BE2F3=base+3,D_800BE2F4=base+4,func_151DCEF0=entry+0x10004);a=linked(o/('original-'+F+'.o'),'guard-original-'+str(j),entry,s);b=linked(o/'selected-final.o','guard-raw-'+str(j),entry,s)
  for start,end in ((44,56),(72,80),(100,116)):
   left,right=a[start//4:end//4],b[start//4:end//4];assert sorted(left)==sorted(right)and dag(left)==dag(right),(j,start)
 return dict(guards=9,actual_padder_rejections=count,word_preimage_rejections=9,relocation_rejections=3,function_scope_rejections=1,closed_windows=[[44,56],[72,80],[100,116]],GNU_alias_layouts=4,all32_register_expression_DAGs_equal=True,operation_multisets_equal=True,memory_or_control_operations_in_guard_windows=0,insertions=0,omissions=0,inherited_prefix_preserved=True)

def controls(source):
 return dict(wrong_first_weight=source.replace('(checksum << 2)','(checksum << 1)'),wrong_second_weight=source.replace('D_800BE2F3 << 3','D_800BE2F3 << 2'),signed_seed=source.replace('checksum = D_800BE2F2;','checksum = (s8)D_800BE2F2;'),wrong_constant=source.replace('+ 0xCC','+ 0xCD'),wrong_shift_mask=source.replace('(index & 3)','(index & 7)'),short_loop=source.replace('index < 104','index < 100'),missing_checksum=source.replace('D_800BE2F0.checksum = checksum;','D_800BE2F0.checksum = 0;'),wrong_gate=source.replace('D_8002AC5C == 0','D_8002AC5C != 0'),wrong_command=source.replace('0x44, &D_800BE2F0','0x45, &D_800BE2F0'),wrong_length=source.replace('&D_800BE2F0, 0x70','&D_800BE2F0, 0x68'))

def compiled_controls():
 source=(o/'selected-semantic-input.c').read_text();rows={};corpus=list(cases())
 for name,body in controls(source).items():
  assert body!=source;obj,diag=compile_owner(r,o,body,'control-'+name);assert not diag;ws=linked(obj,'control-linked-'+name)
  for index,c in enumerate(corpus):
   m=Oracle(ws,fixture(c),c).run();want,calls,obs=reference(fixture(c),c)
   if(public(m.memory),m.calls,m.observations)!=(public(want),calls,obs):rows[name]=index;break
  else:raise AssertionError(('ineffective IDO control',name))
 return dict(count=len(rows),effective_IDO_controls=rows)

def native_source(source):
 head,body=source.split('/* Recompute',1);body='/* Recompute'+body
 text=head+'''static struct{u32 left[4];SaveBlock33990 block;u32 right[4];}actual,expected;
static OSMesgQueue queue;
static u8 disabled;static u32 mode,status,ordinal,error;
#define D_800BE2F0 actual.block
#define D_800BE2F2 actual.block.bytes[2]
#define D_800BE2F3 actual.block.bytes[3]
#define D_800BE900 queue
#define D_8002AC5C disabled
typedef char ABI[(sizeof(void*)==4 && sizeof(SaveBlock33990)==112 && sizeof(OSMesgQueue)==24)?1:-1];
__attribute__((noinline)) s32 func_151DCEF0(OSMesgQueue*q,s32 command,void*source,s32 length){u32 i;u8*p=(u8*)&actual,*e=(u8*)&expected;ordinal++;if(q!=&queue||command!=68||source!=&actual.block||length!=112)error=1;for(i=0;i<sizeof(actual);i++)if(p[i]!=e[i])error=2;
 if(mode&1)disabled=255;if(mode&2)actual.block.checksum=0xF00D;if(mode&4)for(i=4;i<104;i++)actual.block.bytes[i]=(u8)(i*31+status);return(s32)status;}
'''
 for name,b in dict(selected=body,**controls(body)).items():text+=b.replace('void '+F,'static void '+name)+'\n'
 text+='''typedef void(*Update)(void);
static int check(Update fn){u32 n,k,i,total,flag;u8*p=(u8*)&actual,*e=(u8*)&expected;
 for(n=0;n<65536;n++)for(k=0;k<8;k++){
  for(i=0;i<sizeof(actual);i++)p[i]=(u8)(i*13+n+k*17);
  actual.block.bytes[2]=(u8)n;actual.block.bytes[3]=(u8)(n>>8);flag=k&1?255:0;disabled=(u8)flag;mode=k;status=n*0x1020304u+k;ordinal=error=0;
  for(i=0;i<sizeof(actual);i++)e[i]=p[i];total=204+4*expected.block.bytes[2]+8*expected.block.bytes[3];for(i=4;i<104;i++)total+=(1u<<(i%4))*expected.block.bytes[i];expected.block.checksum=(u16)total;
  fn();if(error||ordinal!=(flag==0))return 0;
  if(flag==0){if(mode&2)expected.block.checksum=0xF00D;if(mode&4)for(i=4;i<104;i++)expected.block.bytes[i]=(u8)(i*31+status);}
  for(i=0;i<sizeof(actual);i++)if(p[i]!=e[i])return 0;if(disabled!=(flag==0&&(mode&1)?255:flag))return 0;
 }
 return 1;}
int run(void){if(!check(selected))return 1;
'''
 for i,name in enumerate(controls(body),2):text+='if(check('+name+'))return '+str(i)+';\n'
 return text+'return 0;}\n'+START

def native_suite():
 source=(o/'selected-semantic-input.c').read_text();profiles={}
 for opt in ('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]+'.c');p.write_text(native_source(source));binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-Wno-unused-but-set-variable','-mstackrealign',str(p),'-o',str(binary)],cwd=r,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);assert q.returncode==0,q.stdout+q.stderr;z=subprocess.run([str(binary)],timeout=60);assert z.returncode==0,(opt,z.returncode);profiles[opt]=dict(exit=0,UBSan=True,cases=524288)
 return dict(cases_per_profile=524288,all65536_seed_pairs=True,all_flag_bytes_via_guest=True,pre_provider_block_observed=True,negative_controls=len(controls(source)),profiles=profiles)

def helper_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();ws=struct.unpack_from('>58I',rom,0x20A3A0);asm=(r/'conker/asm/20A3A0.s').read_text();literal={int(a,16):int(w,16)for a,w in re.findall(r'/\*\s*[0-9A-F]+\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',asm)};assert list(ws)==[literal[HELPER+4*i]for i in range(58)]
 images=[linked(o/p,'helper-body-'+str(i))for i,p in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];POLL,MUL,DIV,TIMER=0x151DCFD8,0x10026968,0x10026868,0x10024A40
 # Resolve provider entrypoints from the original instruction words, independently of names.
 actual_calls={((HELPER+4*i+4)&0xF0000000)|((w&0x3FFFFFF)<<2)for i,w in enumerate(ws)if w>>26==3};assert actual_calls=={POLL,MUL,DIV,TIMER},[hex(x)for x in actual_calls]
 class HelperOracle(Oracle):
  def __init__(self,*args,busy=0,**kwargs):super().__init__(*args,**kwargs);self.remaining=busy;self.polls=0;self.timer_args=[]
  def record_call(self,target):
   if target==HELPER:return super().record_call(target)
   assert target in actual_calls
   args=self.arguments(8)if target==TIMER else self.arguments(4)if target in(MUL,DIV)else self.arguments(1)
   self.calls.append((target,args));self.events.append(('CALL',target,args))
   if target==TIMER:self.timer_args.append((args[0],*args[2:]))
  def hook(self,target):
   args=self.calls[-1][1];high=None
   if target==POLL:
    assert args==(1,);self.polls+=1;result=1 if self.remaining else 0;self.remaining=max(0,self.remaining-1)
   elif target in(MUL,DIV):
    left=(args[0]<<32)|args[1];right=(args[2]<<32)|args[3];v=(left*right)&0xFFFFFFFFFFFFFFFF if target==MUL else left//right;high,result=v>>32,v&0xFFFFFFFF
   else:assert target==TIMER;result=self.c.result
   for i in range(4):self.put(self.r[29]+4*i,0xB6000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA6000000+reg
   self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011;self.r[2]=high if high is not None else result
   if high is not None:self.r[3]=result
 count=0;visits=set()
 for ticks,busy,ret,phase in itertools.product((0,1,12345,0xFFFFFFFF,0x8000000000000000,0xFFFFFFFFFFFFFFFF),(0,3),(0,0xFFFFFFFF),(0,8)):
  c=Case(first=255,second=128,pattern=1,result=ret,phase=phase);initial=fixture(c)
  for base,size in ((0x800E0A20,16),(0x8002BD10,8)):initial.update({base+i:0xA5 for i in range(size)})
  put(initial,0x8002BD10,ticks,8);want,_,obs=reference(initial,c)
  for at,value,n in ((0x800E0A20,SYMS['D_800BE900'],4),(0x800E0A24,68,1),(0x800E0A28,SYMS['D_800BE2F0'],4),(0x800E0A2C,112,4)):put(want,at,value,n)
  deadline=((ticks*12000)&0xFFFFFFFFFFFFFFFF)//1000000;timer=(0x80042A58,deadline>>32,deadline&0xFFFFFFFF,0,0,0x80042A78,0x80042A90);ms=[]
  for image in images:
   m=HelperOracle(image,initial,c,connected={HELPER+4*i:w for i,w in enumerate(ws)},busy=busy).run();assert public(m.memory)==public(want)and m.observations==obs and m.polls==busy+1 and m.timer_args==[timer],(ticks,busy,m.timer_args,timer);ms.append(m);visits.update(pc for pc in m.visits if HELPER<=pc<HELPER+232)
  assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
 assert visits==set(range(HELPER,HELPER+232,4)),[hex(x)for x in set(range(HELPER,HELPER+232,4))-visits]
 assert 's32 func_151DCEF0() {\n    return 0;\n}'in(r/'conker/src/game/generated_20A3A0.c').read_text()
 return dict(cases=count,original_helper_words=58,helper_covered_words=58,request_fields_and_timer_ABI_checked=True,poll_scripts=[0,3],bounded_providers=['func_151DCFD8','__ll_mul','__ull_div','osSetTimer'],current_helper_still_stub=True,helper_matching_credit=0,EEPROM_hardware_acceptance=False)
