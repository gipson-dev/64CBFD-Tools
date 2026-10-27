"""Owner radial-height callback: complete source, guarded spill, real caller and image."""
import csv,hashlib,io,itertools,json,struct,subprocess,time,unittest
from pathlib import Path
from tools.experiments import game_owner_radial_height_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths,load_symbol_addrs,function_vram,DEFAULT_SEGMENTS
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_actor_mask_scan_match import AccessFault
from tools.tests.game_view_render_pass_oracle import STACK
ROOT=Path(__file__).resolve().parents[2]
ENTRY,RNG,UNIT,DIRECTION,LOOKUP,TABLE,SEED,FACTOR=0x151A8F6C,0x150ADA20,0x150ADA68,0x15143874,0x151423D8,0x8009A220,0x800885B0,0x8009F740
OWNER,VECTOR,Q0,Q1=0x32000,0x36000,0x38000,0x38010;MASK64=(1<<64)-1
CALLER,SELECT,ALT=0x151A8E0C,0x3C000,0x151A8F1C
POINTS=(0,0x80000000,0x3F800000,0xBF800000,0x41200000,0xC2480000,0x00800000,1,0x7F7FFFFF,0x7F800000,0x7FC12345,0xFFA54321)
def step(seed):
 mixed=(((seed<<63)&MASK64)>>31)|(((seed<<31)&MASK64)>>32)
 mixed^=((seed<<44)&MASK64)>>32
 return((mixed>>20)&0xFFF)^mixed

def pointers(alias):
 vector=VECTOR if alias==0 else OWNER+0x28+((alias-1)%10)*4
 a=(Q0,vector,vector+4,vector+8,OWNER+0x3C,OWNER+0x38,OWNER+0x40,OWNER+0x44)[alias%8]
 b=(Q1,a,vector+4,OWNER+0x3C,OWNER+0x44,vector,OWNER+0x48,OWNER+0x40)[alias%8]
 return vector,a,b

def fixture(n,alias,edge=False):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-0x300,0x100)}
 for base,size in((OWNER,0xA0),(VECTOR,32),(Q0,32),(TABLE,260),(SEED,8),(FACTOR,4)):
  m.update({base+i:(i*13+0xA5)&255 for i in range(size)})
 patterns=POINTS if edge else POINTS[:8]
 for j in range(24):put(m,OWNER+0x28+j*4,patterns[(n+j)%len(patterns)])
 for j in range(3):put(m,VECTOR+j*4,patterns[(n+j*3)%len(patterns)])
 put(m,SEED,(n*0x9E3779B97F4A7C15)&MASK64,8);put(m,FACTOR,factor);m.update({TABLE+i:b for i,b in enumerate(table)})
 return m,(OWNER,*pointers(alias))

def lookup(m,angle):
 angle&=255;index=64-(angle&63)if angle&64 else angle&63
 value=read(m,TABLE+index*4)
 return value if angle&192 in(0,192)else value^0x80000000

def reference(initial,args):
 m=dict(initial);owner,vector,a,b=args;seed=step(read(m,SEED,8));put(m,SEED,seed,8);code=seed&255
 seed=step(seed);put(m,SEED,seed,8);unit=bits(float(seed&65535)*floating(read(m,FACTOR)));radius=bits(floating(unit)*floating(read(m,owner+0x48)))
 x=bits(floating(radius)*floating(lookup(m,code-64)));z=bits(floating(radius)*floating(lookup(m,code)))
 put(m,vector,x);put(m,vector+8,z)
 vx=read(m,vector);vz=read(m,vector+8)
 put(m,vector,bits(floating(vx)+floating(read(m,owner+0x38))))
 put(m,vector+8,bits(floating(vz)+floating(read(m,owner+0x40))))
 put(m,vector+4,read(m,owner+0x3C));put(m,a,read(m,owner+0x3C));put(m,b,read(m,owner+0x44))
 return m,code,radius

def public(memory):return{a:b for a,b in memory.items()if not STACK-0x300<=a<STACK+0x100}
class Oracle(TimingOracle):
 def __init__(self,words,memory,args,phase=0,fault=None,connected=True,entry=ENTRY):
  self.trace=[];super().__init__(words,memory,phase=phase,entry=entry,arguments=args,connected=base_connected if connected else None);self.fault=fault
 def access(self):
  if self.own_instruction:
   if self.accesses==self.fault:raise AccessFault
   self.accesses+=1
 def execute(self,word):
  if word>>26==17 and word>>21&31==16 and word&63==7:
   self.f[word>>6&31]=self.f[word>>11&31]^0x80000000
  else:super().execute(word)
 def get(self,at,size):
  v=super().get(at,size)
  if self.own_instruction:self.trace.append(('R',at,size,v))
  return v
 def put(self,at,value,size):
  if self.recording and self.own_instruction:assert all(at+i in self.memory for i in range(size)),('unmapped write',at,size)
  super().put(at,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',at,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  assert target in(RNG,UNIT,DIRECTION,LOOKUP),hex(target)
  args=self.arguments(4)if target==DIRECTION else self.arguments(1)if target==LOOKUP else()
  self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target in(RNG,UNIT),('unexpected opaque helper',hex(target))
  seed=step(read(self.memory,SEED,8));put(self.memory,SEED,seed,8)
  value=seed&0xFFFFFFFF if target==RNG else bits(float(seed&65535)*floating(read(self.memory,FACTOR)))
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678
  if target==RNG:self.r[2]=value
  else:self.f[0]=value


class Caller(Oracle):
 def __init__(self,code,memory,args,flags,field,phase):
  connected=dict(base_connected);connected.update(zip(range(ENTRY,ENTRY+184,4),code));self.trace=[]
  TimingOracle.__init__(self,window,memory,phase=phase,entry=CALLER,arguments=(0xBAD0BEEF,),connected=connected)
  self.fault=None;self.tail=True;self.r[16]=self.before[16]=SELECT;self.r[19]=self.before[19]=args[0];self.r[17]=self.before[17]=args[1];self.r[20]=self.before[20]=args[2];self.r[21]=self.before[21]=args[3]
  self.r[30]=self.before[30]=self.before[31]
  # S7 is an output of this selector window; its materialization is executed, then checked.
  self.before[23]=ALT if flags&2 and field else ENTRY;self.r[23]=0xDEADC0DE;self.selected=[]
 def record_call(self,target):
  if target in(ENTRY,ALT):
   args=self.arguments(4);self.selected.append((target,args));self.calls.append((target,args));self.events.append(('CALL',target,args))
  else:super().record_call(target)
 def hook(self,target):
  if target!=ALT:return super().hook(target)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)]
  self.r[2]=0xF1000000|self.memory[SELECT]

NATIVE_HEAD="typedef unsigned int u32;typedef int s32;typedef unsigned short u16;typedef short s16;typedef unsigned char u8;typedef unsigned long long u64;typedef float f32;\n"
NATIVE_POST="\ntypedef struct{u8 prefix[0x28];f32 data[24];}NativeOwner;\ntypedef struct{u32 pre[4];NativeOwner owner;f32 vector[3],out[2];u32 post[4];u64 seed;}State;\ntypedef char Width[(sizeof(void*)==4&&sizeof(f32)==4&&sizeof(u64)==8&&__builtin_offsetof(NativeOwner,data)==0x28&&sizeof(NativeOwner)==0x88)?1:-1];\nstatic State actual,expected;static u32 stage,error,expected_angle,expected_radius;\nstatic const u32 table[65]={@TABLE@};static const u32 patterns[8]={0,0x80000000u,0x3F800000u,0xBF800000u,0x41200000u,0xC2480000u,0x00800000u,1};\nstatic f32 real(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}\nstatic u32 word(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}\nstatic u64 step(u64 x){u64 m=((x<<63)>>31)|((x<<31)>>32);m^=(x<<44)>>32;return((m>>20)&0xFFF)^m;}\nstatic f32 lookup(u32 angle){u32 index,x;angle&=255;index=angle&64?64-(angle&63):angle&63;x=table[index];if((angle&192)!=0&&(angle&192)!=192)x^=0x80000000u;return real(x);}\n__attribute__((noinline))s32 func_150ADA20(void){union{u32 u;s32 s;}v;if(stage++!=0)error=1;actual.seed=step(actual.seed);v.u=(u32)actual.seed;return v.s;}\n__attribute__((noinline))f32 func_150ADA68(void){if(stage++!=1)error=1;actual.seed=step(actual.seed);return(f32)((u32)actual.seed&65535)*real(@FACTOR@);}\n__attribute__((noinline))void func_15143874(s16 angle,f32 radius,f32 *x,f32 *z){f32 a,b;if(stage++!=2||(u16)angle!=expected_angle||word(radius)!=expected_radius||z!=x+2)error=1;a=lookup((u32)(s32)angle-64);b=lookup((u32)(s32)angle);*x=radius*a;*z=radius*b;}\nstatic void pointers(State *state,u32 alias,f32 **v,f32 **a,f32 **b){\n *v=alias?&state->owner.data[(alias-1)%10]:state->vector;\n switch(alias%8){case 0:*a=&state->out[0];*b=&state->out[1];break;\n case 1:*a=*v;*b=*a;break;case 2:*a=*v+1;*b=*v+1;break;\n case 3:*a=*v+2;*b=&state->owner.data[5];break;\n case 4:*a=&state->owner.data[5];*b=&state->owner.data[7];break;\n case 5:*a=&state->owner.data[4];*b=*v;break;\n case 6:*a=&state->owner.data[6];*b=&state->owner.data[8];break;\n default:*a=&state->owner.data[7];*b=&state->owner.data[6];break;}}\nstatic void reference(u32 alias){f32 *v,*a,*b,unit,radius,x,z,vx,vz;u32 angle;\n pointers(&expected,alias,&v,&a,&b);expected.seed=step(expected.seed);angle=(u32)expected.seed&255;\n expected.seed=step(expected.seed);unit=(f32)((u32)expected.seed&65535)*real(@FACTOR@);radius=unit*expected.owner.data[8];expected_angle=angle;expected_radius=word(radius);\n x=radius*lookup(angle-64);z=radius*lookup(angle);*v=x;v[2]=z;\n vx=v[0];vz=v[2];v[0]=vx+expected.owner.data[4];v[2]=vz+expected.owner.data[6];\n v[1]=expected.owner.data[5];*a=expected.owner.data[5];*b=expected.owner.data[7];}\nstatic int test_all(void){u32 n,i,alias;f32 *v,*a,*b;\n for(n=0;n<4096;n++){alias=n%16;stage=error=0;\n  for(i=0;i<sizeof(State);i++)((u8*)&actual)[i]=(u8)(i*13+0xA5);\n  for(i=0;i<24;i++)actual.owner.data[i]=real(patterns[(n+i)%8]);\n  for(i=0;i<3;i++)actual.vector[i]=real(patterns[(n+i*3)%8]);\n  actual.seed=(u64)n*0x9E3779B97F4A7C15ULL;\n  for(i=0;i<sizeof(State);i++)((u8*)&expected)[i]=((u8*)&actual)[i];\n  reference(alias);pointers(&actual,alias,&v,&a,&b);func_151A8F6C((u8*)&actual.owner,v,a,b);\n  if(error||stage!=3)return 23;\n  for(i=0;i<sizeof(State);i++)if(((u8*)&actual)[i]!=((u8*)&expected)[i])return 23;\n }\n return 0;}\n__attribute__((noreturn))void _start(void){int status=test_all();__asm__ volatile(\"int $0x80\"::\"a\"(1),\"b\"(status):\"memory\");__builtin_unreachable();}\n"

def native(label,body,opt):
 unit=w/(label+opt+'.c');binary=unit.with_suffix('.bin')
 post=NATIVE_POST.replace('@TABLE@',','.join('0x%Xu'%x for x in struct.unpack('>65I',table))).replace('@FACTOR@','0x%Xu'%factor)
 unit.write_text(NATIVE_HEAD+source.DECLARATIONS+body+post)
 cmd=['gcc','-m32','-msse2','-mfpmath=sse','-std=c99',opt,'-ffreestanding','-fno-builtin','-fno-pie','-no-pie','-fno-stack-protector','-nostdlib','-ffp-contract=off','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Wl,-e,_start','-o',str(binary),str(unit)]
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=60);(w/(label+opt+'-compile.log')).write_text(p.stdout+p.stderr)
 if p.returncode:raise ValueError(p.stdout+p.stderr)
 return subprocess.run([str(binary)],capture_output=True,timeout=30).returncode

class OwnerRadialHeightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global r,rom,table,factor,base_connected,raw,normalized,truth,w,window
        r=ROOT;cls.out=ROOT/source.BUILD;cls.receipt={};cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        source.check_inputs(ROOT,cls.out,cls.installed);source.verify_prepared(cls.out)
        w=cls.out/('fresh-run-'+str(time.time_ns()));w.mkdir()
        cls.obj,diagnostics=source.compile_owner(ROOT,w,'#include <ultra64.h>'+chr(10)+source.ISOLATED_DECLARATIONS+chr(10)+source.SELECTED,'fresh-selected')
        if diagnostics:raise ValueError(diagnostics)
        source.checked_payload(*source.payload(cls.obj));data,functions=source.link_owner(ROOT,w,cls.obj,source.OWNER)
        raw=list(struct.unpack_from('>46I',data,functions[source.FUNCTION]['value']));normalized=raw[:]
        for at,(expected,replacement)in source.GUARDS.items():
            if normalized[at//4]!=expected:raise ValueError('Fresh linked stack guard changed')
            normalized[at//4]=replacement
        rom=cls.values['conker/conker.us.bin'];truth=list(struct.unpack_from('>46I',rom,source.ROM))
        elf=cls.values['conker/build/conker.us.elf'];table=elf[source.elf_slot_offset(elf,TABLE,260):][:260];factor=struct.unpack_from('>I',elf,source.elf_slot_offset(elf,FACTOR,4))[0]
        base_connected={}
        for address,at,n in((DIRECTION,0x170D24,25),(LOOKUP,0x16F888,27)):
            base_connected.update(zip(range(address,address+n*4,4),struct.unpack_from('>%dI'%n,rom,at)))
        window=list(struct.unpack_from('>17I',rom,0x1D62BC))+[0x03C00008,0]
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+chr(10))
    def test_01_complete_owner_actual_Make_and_checked_stack_guards(self):
        self.assertEqual(normalized,truth);unlinked,bindings=source.checked_payload(*source.payload(self.obj))
        self.assertEqual(source.payload(self.out/'after-owner.o'),(unlinked,bindings))
        self.assertEqual(source.payload(self.out/'original-func_151A8F6C.o'),source.normalized_payload(unlinked,bindings))
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),22)
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['words'],q['frame'],q['guards'],q['preserved_neighbors']),(46,48,2,22))
        self.assertEqual((self.out/'make-shadow/src/game/generated_1D4E00.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        manifest=source.guarded_manifest(self.values['conker/retail_word_patches.us.csv'],unlinked,bindings)
        self.assertEqual(manifest,(self.out/'qualified-guards.csv').read_bytes())
        with self.assertRaises(ValueError):source.guarded_manifest(manifest,unlinked,bindings)
        wrong=bytearray(unlinked);wrong[40]^=1
        with self.assertRaises(ValueError):source.normalized_payload(bytes(wrong),bindings)
        wrong_bindings=dict(bindings);wrong_bindings[40]=[('R_MIPS_26','func_150ADA20')]
        with self.assertRaises(ValueError):source.normalized_payload(unlinked,wrong_bindings)
        rows=list(csv.DictReader(io.StringIO(manifest.decode())));selected=next(i for i,row in enumerate(rows)if row['function']==source.FUNCTION)
        for field,value in(('expected','0xAFA20020'),('expected_relocations','R_MIPS_26:func_150ADA20'),('offset','0x2C')):
            changed=[dict(row)for row in rows];changed[selected][field]=value;s=io.StringIO(newline='');writer=csv.DictWriter(s,changed[0].keys(),lineterminator=chr(10));writer.writeheader();writer.writerows(changed);path=w/(field+'-bad-guards.csv');path.write_text(s.getvalue())
            with self.assertRaises(ValueError):emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER)
        if self.installed:source.audit(ROOT,self.out)
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,ENTRY,184);memory,args=fixture(1,0);model=Oracle(struct.unpack_from('>46I',old,at),memory,args).run()
        self.assertNotEqual(public(model.memory),public(reference(memory,args)[0]))
        self.receipt.update(words=46,frame=48,guards=2,bindings=3,neighbors=22,guard_negative_controls=6,actual_Make_commands=3)
    def test_02_actual_math_helpers_aliases_all_angles_and_fired_faults(self):
        count=0;seen=set();angles=set();aliases=set()
        for n,alias,phase,edge in itertools.chain(((n,n%16,n%2*8,False)for n in range(2048)),((n,alias,phase,True)for n,alias,phase in itertools.product(range(24),range(16),(0,8)))):
         m,args=fixture(n,alias,edge);expected,angle,radius=reference(m,args);models=[]
         for words in(truth,normalized):
          model=Oracle(words,m,args,phase).run();assert public(model.memory)==public(expected),(n,alias,phase,edge,'memory')
          calls=[(target,a)for target,a in model.calls if target in(RNG,UNIT,DIRECTION)];assert calls==[(RNG,()),(UNIT,()),(DIRECTION,(angle,radius,args[1],args[1]+8))],calls
          for reg in(*range(16,24),28,29,30,31):assert model.r[reg]==model.before[reg],reg
          models.append(model);seen.update(model.visits)
         assert complete(models[0])==complete(models[1])and models[0].trace==models[1].trace
         # Raw C differs only at the two private stack locations; public data and calls still agree.
         model=Oracle(raw,m,args,phase).run();assert public(model.memory)==public(expected)and model.calls==models[0].calls
         count+=1;angles.add(angle);aliases.add(alias)
        assert set(range(ENTRY,ENTRY+184,4))<=seen and set(base_connected)<=seen and angles==set(range(256))and aliases==set(range(16))
        faults=0
        for alias in(0,3,8,15):
         m,args=fixture(13,alias);done=Oracle(truth,m,args).run()
         for prefix in range(done.accesses):
          models=[]
          for words in(truth,normalized):
           model=Oracle(words,m,args,fault=prefix)
           try:model.run()
           except AccessFault:pass
           else:raise AssertionError(('fault did not fire',prefix))
           models.append(model)
          assert complete(models[0])==complete(models[1])and models[0].trace==models[1].trace;faults+=1
        assert faults>0

        self.assertEqual(faults,184)
        self.receipt.update(guest_cases=count,all_angles=len(angles),alias_shapes=len(aliases),all98_target_helper_words=True,fired_fault_prefixes=faults,raw_C_public_reference=True,PRNG_step_is_bounded_contract=True)
    def test_03_native32_layout_aliases_and_effective_controls(self):
        for opt in('-O0','-O2','-O3'):self.assertEqual(native('selected',source.SELECTED,opt),0)
        changes={'angle-mask':('code & 0xFF','code & 0x7F'),'radius':('state[8] *','state[7] *'),'Z-output':('vector + 2','vector + 1'),'X-origin':('vector[0] += state[4]','vector[0] += state[5]'),'Z-origin':('vector[2] += state[6]','vector[2] += state[4]'),'Y-origin':('vector[1] = state[5]','vector[1] = state[6]'),'first-height':('*out0 = state[5]','*out0 = state[4]'),'second-height':('*out1 = state[7]','*out1 = state[8]')}
        for label,(a,b)in changes.items():
            self.assertEqual(source.SELECTED.count(a),1);self.assertEqual(native(label,source.SELECTED.replace(a,b,1),'-O2'),23)
        self.receipt.update(native_optimizations=3,native_cases_per_run=4096,native_effective_controls=8,finite_native_inputs=True,typed_State_canaries=True,trap_UBSan=True)
    def test_04_actual_callback_selector_and_stack_outputs(self):
        symbols=load_symbol_addrs(str(r/'conker/symbol_addrs.us.txt'));rows=list(csv.DictReader((r/'conker/progress.csv').open()));add_retail_lengths(rows,'us',DEFAULT_SEGMENTS['us'],symbols);sites=[];opcode=0x0C000000|(ENTRY>>2&0x3FFFFFF)
        for row in rows:
         if row['version']!='us'or row['section']not in DEFAULT_SEGMENTS['us']:continue
         base,start=DEFAULT_SEGMENTS['us'][row['section']];at=function_vram(row,symbols);code=struct.unpack_from('>%dI'%row['_retail_nwords'],rom,at-base+start)
         sites.extend((row['function'],hex(at+i*4))for i,x in enumerate(code)if x==opcode)
        assert not sites and not any(rom[i:i+4]==struct.pack('>I',ENTRY)for i in range(0,len(rom),4))
        count=0;selected=0;v0=set();visits=set()
        for flags,field,phase in itertools.product(range(256),(0,1),(0,8)):
         m,_=fixture(flags+3,0);sp=STACK+phase;args=(OWNER+(flags%8)*4,sp+0x64,sp+0x5C,sp+0x60);m.update({SELECT+i:0xA5 for i in range(8)});m[SELECT]=flags;put(m,SELECT+4,field)
         for i,a in enumerate((args[1],args[1]+4,args[1]+8,args[2],args[3])):put(m,a,POINTS[(flags+i)%8])
         if not flags&2:
          for i in range(4):m.pop(SELECT+4+i)
         target=ALT if flags&2 and field else ENTRY
         expected=reference(m,args)[0]if target==ENTRY else m;models=[]
         for code in(truth,normalized):
          model=Caller(code,m,args,flags,field,phase).run();assert model.selected==[(target,args)]and model.r[23]==target
          assert public(model.memory)==public(expected)
          for a in(args[1],args[1]+4,args[1]+8,args[2],args[3]):assert read(model.memory,a)==read(expected,a)
          assert model.r[29]==sp and model.r[16]==SELECT;models.append(model);visits.update(model.visits)
         assert complete(models[0])==complete(models[1])and models[0].trace==models[1].trace
         if target==ENTRY:v0.add(models[0].r[2]);selected+=1
         count+=1
        assert len(v0)==8 and set(range(CALLER,CALLER+17*4,4))<=visits
        # The actual subsequent caller words read flags/outputs without using the callback's V0.
        after=list(struct.unpack_from('>10I',rom,0x1D6300));assert after[0]==0x920F0000 and 0x0D411B20 not in after[:10]

        self.receipt.update(selector_cases=count,selected_target_cases=selected,unused_V0_values=len(v0),actual_selector_words=17,adapter_words=2,S7_is_checked_output=True,lazy_field_unmapped=True,full_parent_claimed=False)
    def test_05_independent_GNU_rebases_and_complete_guest_states(self):
        global ENTRY,RNG,UNIT,DIRECTION,base_connected,truth,normalized,raw
        saved_globals={n:globals()[n]for n in('ENTRY','RNG','UNIT','DIRECTION','base_connected','truth','normalized','raw')};self.addCleanup(lambda:globals().update(saved_globals))
        layouts=((0x151A7FFC,0x150A7FFC,0x150A8000,0x15147FFC),(0x151B8000,0x150B8000,0x150BFFFC,0x15158000),(0x151CFFFC,0x150CFFFC,0x150D0000,0x1516FFFC));rebases=0;links=0
        saved=(ENTRY,RNG,UNIT,DIRECTION,base_connected,truth,normalized,raw)
        for layout in layouts:
         entry,rng,unit,direction=layout;images=[]
         for label,path in(('original',self.out/'original-func_151A8F6C.o'),('C',self.obj)):
          stem='-'.join((label,hex(entry)));script=w/(stem+'.ld');output=w/(stem+'.elf');assert not output.exists();script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
          defs=['--defsym=%s=0x%X'%(n,v)for n,v in(('func_150ADA20',rng),('func_150ADA68',unit),('func_15143874',direction))]
          subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_151A8F6C',*defs,'-o',str(output),str(path)],capture_output=True,check=True)
          words=list(struct.unpack_from('>46I',sections(output)['.text'][1]));images.append(words);links+=1
         raw=images[1];normalized=raw[:];assert(raw[10],raw[12])==(0xAFA20028,0x8FA40028);normalized[10]=0xAFA20024;normalized[12]=0x8FA40024;truth=images[0];assert normalized==truth
         ENTRY,RNG,UNIT,DIRECTION=entry,rng,unit,direction;base_connected={a:v for a,v in saved[4].items()if not saved[3]<=a<saved[3]+25*4};base_connected.update((direction+(a-saved[3]),v)for a,v in saved[4].items()if saved[3]<=a<saved[3]+25*4)
         for n,alias,phase in itertools.product(range(12),(0,3,8,15),(0,8)):
          m,args=fixture(n,alias);expected=reference(m,args)[0];models=[]
          for words in(truth,normalized):
           model=Oracle(words,m,args,phase).run();assert public(model.memory)==public(expected);models.append(model)
          assert complete(models[0])==complete(models[1]);rebases+=1
        ENTRY,RNG,UNIT,DIRECTION,base_connected,truth,normalized,raw=saved

        self.receipt.update(GNU_links=links,GNU_layouts=3,rebased_guest_cases=rebases,bindings=3)
    def test_06_strict_image_current_inputs_and_effective_corruptions(self):
        values=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out)
        before=values['conker/build/conker.us.elf'];truth_bytes=rom[source.ROM:source.ROM+184];expected=source.predicted_image(before,truth_bytes)
        source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth_bytes);at=source.elf_slot_offset(before,ENTRY,184)
        for offset in(20,at,at+184,source.elf_slot_offset(before,0x80082B20,4),next(pos+8 for pos,name,f,_ in source.symbol_rows(before)if name==source.FUNCTION and f[1:3]==(ENTRY,12))):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth_bytes)
        for bad in(expected[:-1],expected+bytes([0])):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth_bytes)
        for b,t in((before[:-1],truth_bytes),(before,truth_bytes[:-1]),(before,bytes([truth_bytes[0]^1])+truth_bytes[1:])):
            with self.assertRaises(ValueError):source.check_image(b,expected,t)
        guards=(self.out/'qualified-guards.csv').read_bytes()if self.installed else values['conker/retail_word_patches.us.csv']
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),guards)
        self.receipt.update(strict_image_corruptions_rejected=7,wrong_input_controls=3,metadata_exclusions=0,frozen_current_inputs=len(values),new_guard_rows=2)

if __name__=='__main__':unittest.main()
