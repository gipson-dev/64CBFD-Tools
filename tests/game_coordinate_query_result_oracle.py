"""Float ABI and closed local-slot relocation; providers remain bounded."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,math,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-coordinate-query-result-match';F='func_1510F648';ENTRY=0x1510F648;ACTOR=0x30000
SYMS=dict(func_1510F800=0x1510F800,func_150A64C8=0x150A64C8,func_150A44F0=0x150A44F0,func_150A43E0=0x150A43E0,D_800D3830=0x800D3830,D_800D3300=0x800D3300,D_800A2D98=0x800A2D98)
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:(n^0x80000000)-0x80000000
s16=lambda n:((n&65535)^32768)-32768
def trunc(word):
 v=floating(word);return math.trunc(v)&0xFFFFFFFF if math.isfinite(v)and -(2**31)<=v<2**31 else 0x80000000
@dataclass(frozen=True)
class Case:
 x:int=0x47C35040
 y:int=0xBFCCCCCD
 z:int=0xC7000080
 height:int=0x80000001
 fallback:int=0x7FC12345
 token:int=0x80000001
 verdict:int=1
 mutation:int=0
 phase:int=0
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,512)};m.update({ACTOR+i:(i*29+0x59)&255 for i in range(512)});m.update({s['D_800D3830']+i:(i*13+0x33)&255 for i in range(128)});put(m,s['D_800D3300'],c.height);put(m,s['D_800A2D98'],c.fallback);return m
def effects(m,c,stage,s=SYMS,out=None):
 if stage==0 and c.mutation==1:put(m,s['D_800D3300'],0x80000001);put(m,s['D_800A2D98'],0x3F800000)
 if stage==1:put(m,out,c.token)
 if stage==2:
  put(m,s['D_800D3830'],c.token^0x13579BDF)
  if c.mutation==2:put(m,out,c.token^0x5A5A5A5A)
 if stage==3 and c.mutation:
  put(m,s['D_800D3300'],0x7FFFFFFF if c.mutation==1 else 0xFFFFFE00);put(m,s['D_800A2D98'],0xBFC00000 if c.mutation==1 else 0x80000000)
def reference(initial,c,s=SYMS):
 m=dict(initial);out=STACK+c.phase-8;effects(m,c,0,s);x,z,y=map(trunc,(c.x,c.z,c.y));calls=[(s['func_1510F800'],(2,)),(s['func_150A64C8'],(u32(s16(x)),u32(s16(z)),out,y))];effects(m,c,1,s,out);calls.append((s['func_150A44F0'],(c.token,s['D_800D3830'],0)));effects(m,c,2,s,out);calls.append((s['func_150A43E0'],(x,z,read(m,out),s['D_800D3830'])));effects(m,c,3,s,out)
 result=bits(floating(bits(float(signed(read(m,s['D_800D3300'])))))*(1./256.))if c.verdict else read(m,s['D_800A2D98']);return m,calls,result
def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+512}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None,raw=False):
  self.raw=raw;self.actual_calls=[];self.output=None;super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(0,0,c.z));self.f[12]=c.x;self.f[14]=c.y
 def mapped(self,p):
  if not self.raw:return p
  home=STACK+self.case.phase
  for offset in(-24,-20,-12):
   if home+offset<=p<home+offset+4:return p+4
  return p
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==13:
   prior=self.own_instruction;self.own_instruction=True;self.dispatched_word=w
   try:self.f[w>>6&31]=trunc(self.f[w>>11&31])
   finally:self.own_instruction=prior
  else:super().execute(w)
 def record_call(self,t):
  counts={self.syms['func_1510F800']:1,self.syms['func_150A64C8']:4,self.syms['func_150A44F0']:3,self.syms['func_150A43E0']:4,ENTRY:3};assert t in counts,hex(t)
  if t==ENTRY:a=(self.f[12],self.f[14],self.r[6])
  else:a=tuple(self.arguments(counts[t]))
  self.actual_calls.append((t,a));canonical=list(a)
  if t==self.syms['func_150A64C8']:self.output=a[2];canonical[2]=self.mapped(a[2])
  a=tuple(canonical);self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  s=self.syms;stage=[s[n]for n in('func_1510F800','func_150A64C8','func_150A44F0','func_150A43E0')].index(t);c=self.case;assert self.r[29]==STACK+c.phase-48;assert read(self.memory,self.r[29]+20)==getattr(self,'expected_target_ra',self.before[31]);effects(self.memory,c,stage,s,self.output)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=c.verdict if stage==3 else 0xDEADBEEF
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
PATTERNS=((0x80000000,0,1),(bits(-1.99),bits(1.99),bits(-270.5)),(bits(32768.5),bits(-32769.5),bits(65535.5)),(bits(2147483520.),bits(-2147483648.),bits(-65537.)),(0x7FC12345,0x7F800000,0xFF800000),(bits(100000.5),bits(-1.6),bits(-32768.5)))
def cases():
 for p,h,f,t,v,mu,phase in itertools.product(PATTERNS,(0,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0x80000000,0x3F123456,0x7FC54321),(0,0x80000001),(0,1,0xFFFFFFFF),range(3),(0,8)):yield Case(*p,h,f,t,v,mu,phase)
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo)
def verify(m,initial,c,s=SYMS):
 want,calls,result=reference(initial,c,s);assert(public(m.memory),m.calls,m.f[0])==(public(want),calls,result),(c,m.calls,calls,hex(m.f[0]),hex(result))
def raw_registers(m):
 regs=m.r[:]
 # The only live pointer changed by the local relocation is query argument A2.
 # Restrict its mapping to the interval after address formation and through
 # the query call's delay slot; all other register values remain literal.
 if m.raw and ENTRY+0x2C<=m.current_pc<=ENTRY+0x64 and regs[6]==STACK+m.case.phase-12:regs[6]+=4
 return regs
def raw_observable(m):return(raw_registers(m),m.f,public(m.memory),m.calls,[(e[0],m.mapped(e[1]),*e[2:]) if e[0] in ('R','W') else e for e in m.events],[(op,m.mapped(p),n,v)for op,p,n,v in m.trace],m.hi,m.lo)
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]and programs[0]!=programs[2];count=0;visited=set()
 for c in cases():
  initial=fixture(c);machines=[]
  for i,words in enumerate(programs):m=Oracle(words,initial,c,raw=i==2).run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1]);assert raw_observable(machines[0])==raw_observable(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+216,4));print(dict(cases=count,covered_words=len(visited)),flush=True)
 prefixes=0
 for c in(Case(verdict=0),Case(),Case(mutation=2,phase=8)):
  initial=fixture(c);full=Oracle(programs[0],initial,c).run()
  for cut in range(full.all_accesses):
   machines=[]
   for i,words in enumerate(programs):
    m=Oracle(words,initial,c,raw=i==2);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access boundary',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1]);assert raw_observable(machines[0])==raw_observable(machines[2]);prefixes+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s={n:(0x10007000+k*0x10000+i*0x1000)for i,n in enumerate(('func_1510F800','func_150A64C8','func_150A44F0','func_150A43E0'))};s.update(D_800D3830=0x80007FF0+k*0x100000,D_800D3300=0x80018004+k*0x100000,D_800A2D98=0x8002FFF0+k*0x100000);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)]
  for v,mu,phase,p in itertools.product((0,1),range(3),(0,8),PATTERNS[:4]):
   c=Case(*p,verdict=v,mutation=mu,phase=phase);initial=fixture(c,s)
   for i,words in enumerate(ps):verify(Oracle(words,initial,c,s,entry,raw=i==2).run(),initial,c,s)
   rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();caller_count=0;window=list(struct.unpack_from('>5I',rom,0x85EE8))
 for p,v,mu,phase in itertools.product(PATTERNS[:4],(0,1),range(3),(0,8)):
  c=Case(*p,verdict=v,mutation=mu,phase=phase);initial=fixture(c)
  for j,b in enumerate(p):put(initial,ACTOR+20+4*j,b)
  want,calls,result=reference(initial,c);put(want,ACTOR+0x118,result)
  for i,words in enumerate(programs):
   connected=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));connected[0x15058A4C]=0;m=Oracle(window,initial,c,entry=0x15058A38,connected=connected,raw=i==2);m.r[16]=ACTOR;m.before=m.r[:];m.expected_target_ra=0x15058A48;m.code=WindowCode(m.code,m);m.code.ends=(0x15058A4C,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing float caller boundary')
   assert(public(m.memory),m.calls)==(public(want),[(ENTRY,(c.x,c.y,c.z))]+calls)
  caller_count+=1
 sparse=0
 for verdict in(0,1):
  c=Case(verdict=verdict,mutation=0);initial=fixture(c);absent=SYMS['D_800D3300']if verdict==0 else SYMS['D_800A2D98']
  for i in range(4):del initial[absent+i]
  for i,words in enumerate(programs):verify(Oracle(words,initial,c,raw=i==2).run(),initial,c)
  sparse+=1
 window2=list(struct.unpack_from('>10I',rom,0x143654));caller2=0
 for xyz,verdict,mutation,phase in itertools.product(((-32768,-1,32767),(0,0,0),(123,456,-789)),(0,1),(0,2),(0,8)):
  c=Case(*[bits(float(n))for n in xyz],verdict=verdict,mutation=mutation,phase=phase);initial=fixture(c);put(initial,STACK+phase+0x28,ACTOR);put(initial,ACTOR+0x12,xyz[1],2);want,calls,result=reference(initial,c);put(want,ACTOR+0x7C,result)
  for i,words in enumerate(programs):
   connected=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));connected[0x151161CC]=0;m=Oracle(window2,initial,c,entry=0x151161A4,connected=connected,raw=i==2);m.f[4]=u32(xyz[0]);m.f[6]=u32(xyz[1]);m.f[8]=u32(xyz[2]);m.before=m.r[:];m.expected_target_ra=0x151161B8;m.code=WindowCode(m.code,m);m.code.ends=(0x151161CC,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing second float caller boundary')
   assert(public(m.memory),m.calls)==(public(want),[(ENTRY,(c.x,c.y,c.z))]+calls)
  caller2+=1
 q=dict(private_only=True,installed=False,matching_credit=0,cases=count,executions=count*3,covered_words=54,frame=48,guards=7,insertions=0,omissions=0,retail_padded_literal_full_state_equal=True,raw_C_public_registers_calls_and_mapped_traces_equal=True,raw_stack_padding_full_equality_claimed=False,raw_pointer_register_mapping='A2 only after output-address formation through query delay slot',sparse_branch_cases=sparse,closed_local_slot_mapping={'raw_SP+24':'retail_SP+28','raw_SP+28':'retail_SP+32','raw_SP+36':'retail_SP+40'},FP_ABI=True,float_invalid_guest_model_only=True,providers_bounded=True,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,original_caller_windows=[dict(entry='0x15058A38',ROM='0x85EE8',words=5,cases=caller_count,float_result_stored=True,complete_parent_claimed=False),dict(entry='0x151161A4',ROM='0x143654',words=10,cases=caller2,float_result_stored=True,complete_parent_claimed=False)],hardware_or_complete_parent_claimed=False)
 return q


import sys
from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 q=sys.modules[__name__]
 F='func_1510F648';prefix=selected[:selected.index('/* Return')];body=selected[selected.index('/* Return'):]
 mutants=dict(wrong_context=body.replace('func_1510F800(2)','func_1510F800(1)'),wrong_axis=body.replace('intZ = z','intZ = y'),narrow_final_x=body.replace('func_150A43E0(intX,','func_150A43E0((s16)intX,'),wrong_scale=body.replace('256.0f','128.0f'),cached_height=body.replace('    f32 result;','    f32 result;\n    s32 captured = D_800D3300;').replace('result = D_800D3300 *','result = captured *'),wrong_fallback=body.replace('result = D_800A2D98;','result = 0.0f;'),cached_output=body.replace('    f32 result;','    f32 result;\n    s32 captured;').replace('    func_150A44F0(value,','    captured = value;\n    func_150A44F0(value,').replace('intZ, value, D_800D3830','intZ, captured, D_800D3830'),wrong_branch=body.replace('if (func_150A43E0(','if (!func_150A43E0('));assert all(v!=body for v in mutants.values())
 text=prefix+r'''
 typedef struct {u32 x,y,z,height,fallback,token,verdict,mutation,narrowX,narrowZ,intY,intX,intZ,finalValue,result,finalHeight,finalFallback;} Fixture;
 static const Fixture*current;u8 D_800D3830[128];s32 D_800D3300;f32 D_800A2D98;static s32 stage,badArgs;static s32*outPointer;
 static f32 asFloat(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
 static u32 asBits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
 static s32 isNan(u32 u){return(u&0x7F800000u)==0x7F800000u&&(u&0x7FFFFFu)!=0;}
 void func_1510F800(s32 context){if(stage++!=0||context!=2)badArgs=1;if(current->mutation==1){D_800D3300=(s32)0x80000001u;D_800A2D98=1.0f;}}
 s32 func_150A64C8(s16 x,s16 z,s32*out,s32 y){if(stage++!=1||(u32)(s32)x!=current->narrowX||(u32)(s32)z!=current->narrowZ||(u32)y!=current->intY||!out)badArgs=1;outPointer=out;*out=(s32)current->token;return (s32)0xDEADBEEFu;}
 void func_150A44F0(s32 value,void*scratch,s32 mode){if(stage++!=2||(u32)value!=current->token||scratch!=D_800D3830||mode!=0)badArgs=1;*(u32*)D_800D3830=current->token^0x13579BDFu;if(current->mutation==2)*outPointer=(s32)(current->token^0x5A5A5A5Au);}
 s32 func_150A43E0(s32 x,s32 z,s32 value,void*scratch){if(stage++!=3||(u32)x!=current->intX||(u32)z!=current->intZ||(u32)value!=current->finalValue||scratch!=D_800D3830)badArgs=1;
  if(current->mutation){D_800D3300=current->mutation==1?0x7FFFFFFF:(s32)0xFFFFFE00u;D_800A2D98=asFloat(current->mutation==1?0xBFC00000u:0x80000000u);}return(s32)current->verdict;}
 '''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items());cases=[c for c in q.cases()if c.phase==0 and all(math.isfinite(q.floating(x))and -(2**31)<=q.floating(x)<2**31 for x in(c.x,c.y,c.z))];rows=[]
 for c in cases:
  initial=q.fixture(c);want,calls,result=q.reference(initial,c);query=calls[1][1];final=calls[3][1];rows.append((c.x,c.y,c.z,c.height,c.fallback,c.token,c.verdict,c.mutation,query[0],query[1],query[3],final[0],final[1],final[2],result,q.read(want,q.SYMS['D_800D3300']),q.read(want,q.SYMS['D_800A2D98'])))
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join('{'+','.join('0x%08Xu'%x for x in row)+'}'for row in rows)+'\n};\n'
 text+=r'''
 typedef f32(*Fn)(f32,f32,f32);
 static s32 check(Fn fn){s32 n,i;for(n=0;n<CASE_COUNT;n++){const Fixture*c=fixtures+n;u32 result;current=c;D_800D3300=(s32)c->height;D_800A2D98=asFloat(c->fallback);for(i=0;i<128;i++)D_800D3830[i]=(u8)(i*13+0x33);stage=badArgs=0;outPointer=NULL;
  result=asBits(fn(asFloat(c->x),asFloat(c->y),asFloat(c->z)));if(badArgs||stage!=4)return 1;
  if(result!=c->result&&!(isNan(result)&&isNan(c->result)))return 2;
  if((u32)D_800D3300!=c->finalHeight||asBits(D_800A2D98)!=c->finalFallback||*(u32*)D_800D3830!=(c->token^0x13579BDFu))return 3;
  for(i=4;i<128;i++)if(D_800D3830[i]!=(u8)(i*13+0x33))return 4;
  }return 0;}
 static int run(void){if(sizeof(void*)!=4)return 90;if(check(test_selected))return 10;
 '''.replace('CASE_COUNT',str(len(cases)))
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
