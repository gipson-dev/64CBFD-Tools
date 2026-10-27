"""Registered rebound callback: binary32 order, six-argument ABI and strict ELF image."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,math,os,struct,subprocess,time,unittest
from tools.experiments import game_record_rebound_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.test_game_record_bounce_response import BounceOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
RECORD,SURFACE=0x30000,0x36000
@dataclass(frozen=True)
class Case:
    vy:int=0xC0800000
    damping:int=0x3F000000
    flags:int=0x8000006F
    extent:int=0x3F800000
    height:int=0x40A00000
    layout:int=0
    phase:int=0
    unused:tuple=(0x3F800000,0xC0000000,0x7FC12345)
    normal:int=0xDEAD4320

def address(c,scale=source.SCALE):return (RECORD,scale-0x44,scale-0x3C,STACK+c.phase-0x38,STACK+c.phase-0x50)[c.layout]
def fixture(c,scale=source.SCALE):
    p=address(c,scale);m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-2048,1024)}
    for base,size in((p,0x180),(SURFACE,0x100)):
        for i in range(size):m[base+i]=(i*13+0x5A)&255
    for at,v in((0x10,c.extent),(0x14,c.damping),(0x38,bits(17)),(0x3C,bits(-10)),(0x40,bits(23)),(0x44,bits(13)),(0x48,c.vy),(0x4C,bits(-29)),(0x50,bits(7)),(0x54,bits(-11)),(0x58,bits(19)),(0x60,c.flags),(0x110,c.height),(0x130,0)):put(m,p+at,v)
    m[p+0x73]=2;put(m,scale,source.SCALE_BITS);put(m,STACK+c.phase+16,c.height);put(m,STACK+c.phase+20,c.normal)
    return m

def mul(a,b):return bits(floating(a)*floating(b))
def add(a,b):return bits(floating(a)+floating(b))
def reference(initial,c,scale=source.SCALE,sp=None,unused=None):
    m=dict(initial);p=address(c,scale);sp=STACK+c.phase if sp is None else sp
    for i,v in enumerate(c.unused if unused is None else unused,1):put(m,sp+4*i,v)
    height=add(mul(read(m,p+0x10),read(m,scale)),read(m,sp+16));vy=read(m,p+0x48);put(m,p+0x3C,height)
    if floating(vy)>-2.0:
        put(m,p+0x44,0);put(m,p+0x60,read(m,p+0x60)&0xFFFFFF90);put(m,p+0x48,0);put(m,p+0x4C,0)
    else:
        damping=read(m,p+0x14)
        for at in(0x44,0x48,0x4C,0x50,0x54,0x58):put(m,p+at,mul(read(m,p+at)^(0x80000000 if at==0x48 else 0),damping))
    return m

def public(m):return {a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
def corpus():
    vertical=(0,0x80000000,1,0x80000001,bits(1),bits(-1),0xBFFFFFFF,0xC0000000,0xC0000001,bits(-4),bits(-16))
    for vy,damping,flags,(extent,height)in itertools.product(vertical,map(bits,(0,-0.0,.25,.5,1,-1,2,-2)),(0,0x6F,0x8000006F,0xFFFFFFFF),((bits(1),bits(5)),(bits(-1),bits(-5)),(0x3F8CCCCD,0xBF9AE148))):yield Case(vy,damping,flags,extent,height)
    for low,high,vy,damping in itertools.product(range(256),(0,0x80000000,0xFFFFFF00),(bits(0),bits(-3)),(bits(.5),bits(-1))):yield Case(vy,damping,high|low)
    for vy,damping in itertools.product((0x7FC00000,0xFFC00000,0x7F800000,0xFF800000),(bits(0),bits(1),bits(-1))):yield Case(vy,damping)

class ReboundOracle(BounceOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,arguments=None,scale=source.SCALE,mode=1,query=1,attached=0,method=2,other_return=1,providers=()):
        p=address(c,scale)
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=arguments or(p,*c.unused,c.height,c.normal),connected=connected)
        self.case,self.scale,self.parent_mode,self.query_result=c,scale,mode,query
        self.attached,self.method,self.other_return,self.registry=attached,method,other_return,set(providers)
        self.attempted=[]
    def record_call(self,target):
        self.attempted.append(target)
        if target==source.PRE:args=self.arguments(1)
        elif target==source.GROUND:args=self.arguments(4)
        else:
            assert target==source.ENTRY or target in self.registry,('unbounded rebound callback',hex(target));args=self.arguments(6)
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        p=address(self.case,self.scale);value=0xDEADBEEF
        if target==source.PRE:
            if self.parent_mode==1:put(self.memory,p+0x3C,bits(-20))
            elif self.parent_mode==2:put(self.memory,p+0x3C,bits(-20));put(self.memory,p+0x60,0)
            elif self.parent_mode==3:put(self.memory,p+0x3C,0x7FC00000)
        elif target==source.GROUND:
            put(self.memory,p+0x110,self.case.height);put(self.memory,p+0x14,self.case.damping)
            self.memory[p+0x73]=self.method
            put(self.memory,p+0x130,SURFACE if self.attached else 0);self.memory[SURFACE+0x4F]=self.attached
            value=self.query_result
        elif target in self.registry:
            put(self.memory,p+0x100,self.other_return^target);value=self.other_return
        else:raise AssertionError(hex(target))
        for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678;self.r[2]=value

def controls():
    b=source.SELECTED
    result=dict(wrong_extent=b.replace('record->extent *','record->damping *'),wrong_scale=b.replace('D_8009FEF8','1.0f'),
        wide_height=b.replace('record->extent * D_8009FEF8 + groundHeight','(f32)((f64)record->extent * (f64)D_8009FEF8 + (f64)groundHeight)'),
        equal_settles=b.replace('> -2.0f','>= -2.0f'),unordered_settles=b.replace('record->velocity[1] > -2.0f','!(record->velocity[1] <= -2.0f)'),
        wrong_mask=b.replace('0xFFFFFF90U','0xFFFFFF80U'),narrow_mask=b.replace('0xFFFFFF90U','0x90U'),
        no_reflection=b.replace('-record->velocity[1] * damping','record->velocity[1] * damping'),
        missing_motion=b.replace('        record->velocity[2] = 0.0f;',''),
        missing_rotation=b.replace('        record->rotationVelocity[2] *= damping;',''),wrong_return=b.replace('return 1;','return 0;'))
    assert all(v!=b for v in result.values());return result

def native_harness():
    rows=[]
    for c in corpus():
        m=fixture(c);out=reference(m,c)
        rows.append('{'+','.join('0x%Xu'%x for x in(c.vy,c.damping,c.flags,c.extent,c.height))+',{'+','.join('0x%Xu'%read(out,RECORD+at)for at in(0x3C,0x44,0x48,0x4C,0x50,0x54,0x58,0x60))+'}}')
    text=source.HEADERS+source.DECLARATIONS+'''
f32 D_8009FEF8;
typedef union {u32 u;f32 f;} Float;
typedef char ABI[(sizeof(void*)==4&&sizeof(ReboundRecordE8C10)==0x64&&
 __builtin_offsetof(ReboundRecordE8C10,extent)==0x10&&__builtin_offsetof(ReboundRecordE8C10,damping)==0x14&&
 __builtin_offsetof(ReboundRecordE8C10,height)==0x3C&&__builtin_offsetof(ReboundRecordE8C10,velocity)==0x44&&
 __builtin_offsetof(ReboundRecordE8C10,rotationVelocity)==0x50&&__builtin_offsetof(ReboundRecordE8C10,flags)==0x60)?1:-1];
'''
    for name,body in dict(selected=source.SELECTED,**controls()).items():text+=body.replace(source.FUNCTION,name)+'\n'
    text+='''
typedef struct {u32 vy,damping,flags,extent,height,out[8];} Row;
static const Row rows[]={\n'''+',\n'.join(rows)+'''};
typedef s32(*Callback)(ReboundRecordE8C10*,f32,f32,f32,f32,f32*);
__attribute__((noinline,noclone)) static s32 invoke(Callback fn,ReboundRecordE8C10*r,f32 height,f32*n){return fn(r,1.0f,-2.0f,3.0f,height,n);}
static u32 word(f32 value){Float f;f.f=value;return f.u;}
static f32 value(u32 word){Float f;f.u=word;return f.f;}
static u32 same(u32 a,u32 b){return(a&0x7FFFFFFF)>0x7F800000?(b&0x7FFFFFFF)>0x7F800000:a==b;}
static int variant(Callback fn,u32 wrapped){u32 i,j,k,observed[8],at[]={0x3C,0x44,0x48,0x4C,0x50,0x54,0x58,0x60};ReboundRecordE8C10 r;f32 normal[3]={17,-19,23};s32 result;
 for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
  const Row*v=rows+i;for(j=0;j<sizeof(r);j++)((u8*)&r)[j]=(u8)(j*13+0x5A);
  D_8009FEF8=value(0x3F8CCCCD);r.extent=value(v->extent);r.damping=value(v->damping);r.height=-10;r.velocity[0]=13;r.velocity[1]=value(v->vy);r.velocity[2]=-29;
  r.rotationVelocity[0]=7;r.rotationVelocity[1]=-11;r.rotationVelocity[2]=19;r.flags=v->flags;
  result=wrapped?invoke(fn,&r,value(v->height),normal):fn(&r,1,-2,3,value(v->height),normal);if(result!=1)return 23;
  observed[0]=word(r.height);for(j=0;j<3;j++){observed[1+j]=word(r.velocity[j]);observed[4+j]=word(r.rotationVelocity[j]);}observed[7]=r.flags;
  for(j=0;j<8;j++)if(j==7?observed[j]!=v->out[j]:!same(v->out[j],observed[j]))return 23;
  if(word(r.extent)!=v->extent||word(r.damping)!=v->damping||word(D_8009FEF8)!=0x3F8CCCCD||normal[0]!=17||normal[1]!=-19||normal[2]!=23)return 23;
  for(j=0;j<sizeof(r);j++){u32 changed=(j>=0x10&&j<0x18);for(k=0;k<8;k++)changed|=j>=at[k]&&j<at[k]+4;
   if(!changed&&((u8*)&r)[j]!=(u8)(j*13+0x5A))return 23;}
 }return 0;}
int run(void){if(variant(selected,0)||variant(selected,1))return 1;
'''
    for i,name in enumerate(controls(),2):text+='if(!variant('+name+',0))return '+str(i)+';\n'
    return text+'return 0;}\n'+START,len(rows)

class RecordReboundTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.receipt={};cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        source.check_inputs(ROOT,cls.out,cls.installed);source.verify_prepared(cls.out);cls.fresh=cls.out/('fresh-run-'+str(os.getpid())+'-'+str(time.time_ns()));cls.fresh.mkdir()
        cls.obj,diag=source.compile_owner(ROOT,cls.fresh,source.HEADERS+source.DECLARATIONS+'\n'+source.SELECTED+'\n','fresh-selected')
        if diag:raise ValueError(diag)
        source.checked_payload(*source.payload(cls.obj));data,fs=source.link_owner(ROOT,cls.fresh,cls.obj,source.OWNER);cls.words=list(struct.unpack_from('>46I',data,fs[source.FUNCTION]['value']))
        rom=cls.values['conker/conker.us.bin'];old=cls.values['conker/build/conker.us.elf'];cls.truth=list(struct.unpack_from('>46I',rom,source.ROM));cls.parent=list(struct.unpack_from('>80I',rom,source.PARENT_ROM));cls.retained_parent=list(struct.unpack_from('>80I',old,source.elf_slot_offset(old,source.PARENT,320)));cls.registry=struct.unpack_from('>15I',rom,source.TABLE_ROM)
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),initial=None,images=None,entry=source.ENTRY,scale=source.SCALE):
        initial=fixture(c,scale)if initial is None else initial;expected=reference(initial,c,scale);pair=[];p=address(c,scale)
        for words in images or(self.truth,self.words):
            m=ReboundOracle(words,initial,c,entry,scale=scale).run();self.assertEqual(public(m.memory),public(expected),c)
            self.assertEqual({a:v for a,v in m.memory.items()if p<=a<p+0x64},{a:v for a,v in expected.items()if p<=a<p+0x64},c);self.assertEqual(m.r[2],1);self.assertFalse(m.calls);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));return pair[0]
    def test_01_complete_owner_actual_Make_registry_and_six_argument_ABI(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.parent,self.retained_parent);self.assertEqual(self.registry[2],source.ENTRY)
        self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()).encode(),(self.out/'proposed-owner.c').read_bytes())
        for label,text in(('before',self.values[source.SOURCE].decode()),('after',(self.out/'proposed-owner.c').read_text())):
            obj,diag=source.compile_owner(ROOT,self.fresh,text,'fresh-owner-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),9)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),8);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
        self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_E8C10.c.o.compact'),9);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
        rom=self.values['conker/conker.us.bin'];jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF)
        self.assertEqual([i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==source.ENTRY],[0x22E3FC]);self.assertFalse(any(struct.unpack_from('>I',rom,i)[0]==jal for i in range(0,len(rom)-3,4)))
        old=self.values['conker/build/conker.us.elf'];self.assertEqual(old[source.elf_slot_offset(old,source.TABLE,60):][:60],rom[source.TABLE_ROM:source.TABLE_ROM+60]);self.assertEqual(struct.unpack_from('>I',rom,source.SCALE_ROM)[0],source.SCALE_BITS)
        for site in('1513300C','151339B0'):self.assertIn(site,self.values['conker/asm/15F680.s'].decode())
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=46,frame=0,guards=0,bindings=2,neighbors=8,compact_functions=9,actual_Make_commands=3,all_diagnostics_empty=True,actual_registry_slot=2,entries=15,six_argument_ABI='s32(record*,f32,f32,f32,f32,f32*)',both_retail_indirect_sites_inspected=True)
    def test_02_binary32_boundaries_flags_and_ordered_aliases(self):
        cases=list(corpus());visits=set();count=0
        for c in cases:
            visits.update(self.compare(c).visits);count+=1
        for layout,vy,damping,phase in itertools.product(range(1,5),(bits(0),bits(-4),0x7FC00000),(bits(0),bits(.5),bits(-1)),(0,8)):
            self.compare(Case(vy,damping,layout=layout,phase=phase));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+184,4)))
        self.receipt['guest']=dict(cases=count,all_46_words_visited=True,all_low_flag_bytes=True,signed_zero_and_subnormals=True,ordered_qNaN_and_infinity_model_cases=True,alias_layouts=5,ignored_incoming_homes_observable=True,full_private_state_equal=True,R4300_FCSR_or_hardware_acceptance_claimed=False)
    def parent_compare(self,parent,c,mode,query,attached,method,other_return=1,initial_method=2):
        initial=fixture(c);p=address(c);initial[p+0x73]=initial_method
        for i,v in enumerate(self.registry):put(initial,source.TABLE+4*i,v)
        expected=dict(initial);shadow=tuple(read(expected,p+at)for at in(0x38,0x3C,0x40));calls=[(source.PRE,(p,))];result=1
        if mode==1:put(expected,p+0x3C,bits(-20))
        elif mode==2:put(expected,p+0x3C,bits(-20));put(expected,p+0x60,0)
        elif mode==3:put(expected,p+0x3C,0x7FC00000)
        if read(expected,p+0x60)&1 and expected[p+0x73]and floating(read(expected,p+0x3C))<floating(shadow[1]):
            args=(STACK+c.phase-0x50+0x34,0,add(read(expected,p+0x3C),read(expected,p+0x10)^0x80000000),p+0x110);calls.append((source.GROUND,args))
            put(expected,p+0x110,c.height);put(expected,p+0x14,c.damping);expected[p+0x73]=method;put(expected,p+0x130,SURFACE if attached else 0);expected[SURFACE+0x4F]=attached
            if query and attached&0x60!=0x40:
                target=self.registry[method];args=(p,*shadow,c.height,p+0x114);calls.append((target,args))
                if target==source.ENTRY:
                    sp=STACK+c.phase-0x50;put(expected,sp+16,c.height);put(expected,sp+20,p+0x114);expected=reference(expected,c,sp=sp,unused=shadow);result=1
                else:
                    put(expected,p+0x100,other_return^target);byte=other_return&255;result=(byte if byte<128 else byte-256)&0xFFFFFFFF
        pair=[]
        for words in(self.truth,self.words):
            connected={source.ENTRY+4*i:w for i,w in enumerate(words)}
            m=ReboundOracle(parent,initial,c,source.PARENT,connected,arguments=(p,),mode=mode,query=query,attached=attached,method=method,other_return=other_return,providers=self.registry[1:]).run()
            self.assertEqual(m.calls,calls,(mode,query,attached,method));self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.r[2],result);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));return pair[0]
    def test_03_complete_original_and_retained_dispatcher(self):
        count=0;visits=set()
        for parent in(self.parent,self.retained_parent):
            for mode,query,attached,method,phase in itertools.product(range(4),(0,1),(0,0x20,0x40,0x60),(1,2,14),(0,8)):
                c=Case(vy=bits(-4),flags=0x80000001,phase=phase);m=self.parent_compare(parent,c,mode,query,attached,method,0x80);visits.update(m.visits);count+=1
            for phase in(0,8):
                c=Case(flags=0x80000001,phase=phase);m=self.parent_compare(parent,c,1,1,0,2,initial_method=0);visits.update(m.visits);count+=1
        self.assertEqual(set(range(source.PARENT,source.PARENT+320,4))-visits,set())
        self.receipt['caller']=dict(cases=count,original_and_retained_80_words=True,six_callback_arguments_checked=True,shadow_position_survives_pre_provider=True,method_and_surface_reloaded_after_ground_provider=True,return_truncated_to_signed_byte=True,other_registry_entries_are_bounded_contracts=True,whole_helper_gameplay_acceptance_claimed=False)
    def test_04_native32_actual_C_and_effective_controls(self):
        text,count=native_harness()
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(text);binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr)
            self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=120).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],cases_per_profile=count*2,typed_six_argument_indirect_call=True,actual_record_layout_asserted=True,effective_controls=len(controls()),trapping_UBSan=True,finite_outputs_bit_exact=True,NaN_results_classification_only=True,FCSR_exceptions_not_claimed=True)
    def test_05_fault_prefixes_sparse_settling_and_effective_compiled_negatives(self):
        count=0
        for c in(Case(),Case(vy=bits(0)),Case(layout=1),Case(layout=4)):
            initial=fixture(c);m=self.compare(c)
            for fault in range(m.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=ReboundOracle(words,initial,c);x.root_fault=fault
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,fault);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        c=Case(vy=bits(0));initial=fixture(c);p=address(c)
        sparse={a:v for a,v in initial.items()if not(p+0x14<=a<p+0x18 or p+0x50<=a<p+0x5C)};self.compare(c,sparse)
        for name,line in(('damping','    (void)*(volatile f32 *)&record->damping;'),('normal','    (void)*(volatile f32 *)normal;')):
            body=source.SELECTED.replace('    record->height =',line+'\n    record->height =',1);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-early-'+name);self.assertFalse(diag)
            data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);info=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
            with self.assertRaisesRegex(AssertionError,'unmapped read'):ReboundOracle(words,sparse,c).run()
        self.receipt['faults']=dict(fired_prefix_pairs=count,sparse_settling_needs_no_damping_or_angular_mapping=True,compiled_early_damping_and_unused_normal_negatives_effective=True,guest_only_memory_order_claim=True)
    def test_06_real_padder_and_GNU_rebases(self):
        raw,bindings=source.checked_payload(*source.payload(self.obj))
        for data,rs in((raw[:-4],bindings),(bytes([raw[0]^1])+raw[1:],bindings),(raw,bindings|{12:[('R_MIPS_HI16','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(data,rs)
        p=self.fresh/'fresh-padded.s';p.write_text(emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        asm,missing=emit_function(raw,dict(value=0,size=184),bindings,source.FUNCTION,dict(D_8009FEF8=source.SCALE));self.assertFalse(missing);p=self.fresh/'independent.s';p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True)
        count=0
        for i,(entry,scale)in enumerate(((source.ENTRY,source.SCALE),(0x152BCFB8,0x81207FFC),(0x154BCFB8,0x81208000))):
            images=[]
            for j,object_ in enumerate((self.out/'original-func_150BCFB8.o',obj)):
                p=self.fresh/('rebase-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=D_8009FEF8=0x%X'%scale,'-o',str(elf),str(object_)],capture_output=True,check=True);images.append(list(struct.unpack_from('>46I',sections(elf)['.text'][1])))
            self.assertEqual(*images)
            for vy,damping,layout,phase in itertools.product((bits(0),bits(-2),bits(-4),0x7FC00000),(bits(.5),bits(-1)),range(3),(0,8)):
                self.compare(Case(vy,damping,layout=layout,phase=phase),images=images,entry=entry,scale=scale);count+=1
        self.receipt['rebases']=dict(layouts=3,GNU_links=6,guest_cases=count,HI16_LO16_signed_low_carry=True,both_bindings=True,guards=0,raw_negative_controls=3)
    def test_07_closed_symbol_serialization_and_unchanged_named_definitions(self):
        before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+184];source.check_image(before,actual,truth)
        rows={n:(pos,f,s)for pos,n,f,s in source.symbol_rows(before)};a,fa,sa=rows['func_151417C4'];b,fb,sb=rows['D_8009EF5C'];names=(b'func_151417C4\0',b'D_8009EF5C\0')
        self.assertEqual(actual[sa:sb+len(names[1])],names[1]+names[0]);after={n:f[1:]for _,n,f,_ in source.symbol_rows(actual)}
        self.assertEqual(after['func_151417C4'],fa[1:]);self.assertEqual(after['D_8009EF5C'],fb[1:])
        self.receipt['serialization']=dict(closed_symbol_rows=2,string_bytes=25,serialization_bytes_changed=38,named_definitions_unchanged_except_target_size=True,not_an_image_exclusion=True)
    def test_08_strict_full_image_frozen_inputs_and_corruptions(self):
        values=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=values['conker/build/conker.us.elf'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+184];expected=source.predicted_image(before,truth)
        source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,184);rows={n:(pos,f,s)for pos,n,f,s in source.symbol_rows(before)};symbol=rows[source.FUNCTION][0]+8
        for offset in(20,at,at+184,source.elf_slot_offset(before,0x80082B20,4),symbol,rows['func_151417C4'][0],rows['D_8009EF5C'][2]):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        for bad in(expected[:-1],expected+bytes([0])):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        for b,t in((before[:-1],truth),(before,truth[:-1]),(before,bytes([truth[0]^1])+truth[1:])):
            with self.assertRaises(ValueError):source.check_image(b,expected,t)
        q=json.loads((self.out/'preparation.json').read_text());self.assertEqual((q['changed_bytes'],q['code_bytes'],q['metadata_bytes'],q['exclusions']),(182,143,39,0));self.receipt['strict']=dict(changed_bytes=182,code_bytes=143,metadata_bytes=39,exclusions=0,corruptions=9,wrong_inputs=3,focused_inputs=len(values))

if __name__=='__main__':unittest.main()
