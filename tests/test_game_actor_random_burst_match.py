"""Attached actor burst: callback O32, RNG/point providers, native C and literal image."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_actor_random_burst_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_random_selector_outputs_match import RandomOutputsOracle,next_seed,SEEDS
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
ACTOR,MATRIX,NODE,RECORD=0x30000,0x40000,0x50000,0x51000
DISPATCH,REGISTRY,REGISTRY_ROM=0x15141A7C,0x8008A0B4,0x22EB74
CLASSIFY,MASK,CATEGORY,POSITIVE,SEARCH,CLASSIFIER=0x15141C0C,0x1510F8CC,0x15141CC0,0x15141E38,0x1514ECE0,0x15146970
U32=0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    context:int=1
    unused:int=0x87654321
    attached:int=1
    rng:int=0xFFFFFFFF
    random:int=bits(.5)
    point:tuple=(bits(1.75),bits(-2.75),bits(32768.25))
    mode:int=0
    write:bool=True
    phase:int=0
    alias:int=0

def fixture(c):
    sp=STACK+c.phase;actor=ACTOR if not c.alias else sp+(4,8,-12)[c.alias-1]-0x1D4
    m={sp+i:(i*17+0xA5)&255 for i in range(-768,256)}
    m.update({ACTOR+i:(i*13+0x59)&255 for i in range(-16,0x350)})
    put(m,actor+0x1D4,c.attached);return m,actor

def public(m):return{a:b for a,b in m.items()if not STACK-768<=a<STACK+256}
def signed16(x):return((x&65535)^32768)-32768

def packet(initial,c,actor,sp=None):
    m=dict(initial);sp=STACK+c.phase if sp is None else sp
    put(m,sp,actor);put(m,sp+4,c.context);put(m,sp+8,c.unused)
    if not read(m,actor+0x1D4):return None
    pos=sp-12
    if c.write:
        for i,v in enumerate(c.point):put(m,pos+4*i,v)
    if c.mode==1:
        for i in range(3):put(m,pos+4*i,bits(100.+i))
    count=c.rng%11+5;put(m,pos-2,count,2)
    if c.mode==2:
        for i in range(3):put(m,pos+4*i,bits(200.+i))
    if c.mode==3:put(m,pos-2,0xFFF9,2)
    return(*(read(m,pos+4*i)for i in range(3)),bits(floating(c.random)*11.),0,255,signed16(read(m,pos-2,2))&U32,22,0,0,0,255)

class BurstOracle(RandomOutputsOracle,RayOracle):
    def __init__(self,words,memory,c=Case(),actor=ACTOR,entry=source.ENTRY,connected=None,helpers=None,selected=5,list_path=False):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(actor,c.context,c.unused),connected=connected)
        self.c,self.actor=c,actor;self.helpers=helpers or(source.POINT,source.INTEGER_RNG,source.FLOAT_RNG,source.SUBMIT);self.position=None;self.packets=[];self.selected=selected;self.list_path=list_path;self.searches=0
    def execute(self,word):
        if word>>26==0 and word&63==27:
            rs,rt=word>>21&31,word>>16&31;left,right=self.r[rs]&U32,self.r[rt]&U32;assert right;self.lo=left//right;self.hi=left%right;self.r[0]=0
        else:super().execute(word)
    def record_call(self,target):
        if target==self.helpers[0]:args=self.arguments(4);self.position=args[0]
        elif target in self.helpers[1:3]:args=()
        elif target==self.helpers[3]:args=(self.f[12],self.f[14],self.r[6]&U32,self.r[7]&U32,*(self.get(self.r[29]+16+4*i,4)for i in range(8)));self.packets.append(args)
        elif target==source.ENTRY:args=self.arguments(3)
        elif target in(CLASSIFY,MASK,CATEGORY):args=self.arguments(1)
        elif target in(CLASSIFIER,POSITIVE):args=self.arguments(2)
        elif target==SEARCH:args=self.arguments(3)
        elif target==0x15142314:args=self.arguments(3)
        else:raise AssertionError(('Unmapped burst provider',hex(target)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        result=0x76543210;position=self.position
        if target==self.helpers[0]:
            if self.c.write:
                for i,v in enumerate(self.c.point):self.put(position+4*i,v,4)
            result=0
        elif target==self.helpers[1]:
            if self.c.mode==1:
                for i in range(3):self.put(position+4*i,bits(100.+i),4)
            result=self.c.rng
        elif target==self.helpers[2]:
            if self.c.mode==2:
                for i in range(3):self.put(position+4*i,bits(200.+i),4)
            if self.c.mode==3:self.put(position-2,0xFFF9,2)
        elif target==self.helpers[3]:pass
        elif target in(CLASSIFY,MASK,CATEGORY):result=0
        elif target==CLASSIFIER:result=self.selected&U32
        elif target==SEARCH:
            result=NODE if self.list_path and not self.searches else 0;self.put(self.r[6],result,4);self.searches+=1
        else:raise AssertionError(('Unbounded helper',hex(target)))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.r[2]=result;self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0x87654321,0x12345678,True
        if target==self.helpers[2]:self.f[0]=self.c.random

def controls():
    b=source.SELECTED
    early=b.replace('    count =','    f32 savedX = position[0];\n    count =').replace('func_1514C678(position[0],','func_1514C678(savedX,')
    return dict(signed_rng=b.replace('(u32)func_150ADA20() % 11U','func_150ADA20() % 11'),wrong_mod=b.replace('% 11U','% 12U'),wrong_base=b.replace('+ 5;','+ 6;'),wrong_scale=b.replace('* 11.0f','* 12.0f'),wrong_kind=b.replace('count, 0x16','count, 0x17'),wrong_alpha=b.replace('NULL, 255','NULL, 254'),wrong_gate=b.replace('== NULL','!= NULL'),early_position=early)

def native_harness():
    t=source.HEADERS+source.DECLARATIONS+r'''
static union{u32 align;u8 bytes[0x340];}actor;
static u32 calls,error,rngWord,randomWord,contextWord,mode,present,wanted[12];static f32*position;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
typedef void(*Handler)(u8*,u8,s32);
__attribute__((noinline,noclone)) s32 func_15146890(f32*p,u8*a,s32 zero,s32 context){u32 i;if(calls++!=0||a!=actor.bytes||zero||context!=(s32)(u8)contextWord)error=1;position=p;for(i=0;i<3;i++)p[i]=real(wanted[i]);return 0;}
__attribute__((noinline,noclone)) s32 func_150ADA20(void){u32 i;if(calls++!=1)error=2;if(mode==1)for(i=0;i<3;i++)position[i]=100.0f+i;return(s32)rngWord;}
__attribute__((noinline,noclone)) f32 func_150ADA68(void){u32 i;if(calls++!=2)error=3;if(mode==2)for(i=0;i<3;i++)position[i]=200.0f+i;return real(randomWord);}
__attribute__((noinline,noclone)) void func_1514C678(f32 x,f32 y,f32 z,f32 scale,s16 low,s16 high,s16 count,u8 kind,s32 flags,f32 extra,void*data,u8 alpha){
 u32 actual[12]={word(x),word(y),word(z),word(scale),(u32)low,(u32)high,(u32)count,kind,(u32)flags,word(extra),(u32)data,alpha},i;
 if(calls++!=3)error=4;
 for(i=0;i<12;i++){u32 v=wanted[i];if(i<3&&mode)v=word((mode==1?100.0f:200.0f)+i);if(actual[i]!=v)error=5;}position=0;
}
'''
    for name,body in dict(selected=source.SELECTED,**controls()).items():t+=body.replace(source.FUNCTION,name)+'\n'
    t+=r'''
static int check(Handler h){
 const u32 randoms[]={0,1,10,11,0x80000000,0xFFFFFFFF};const u32 samples[]={0x3F000000,0x3F7FFFFF};
 u32 c,r,p,k,s,i;
 for(c=0;c<256;c++)for(r=0;r<6;r++)for(p=0;p<2;p++)for(k=0;k<3;k++)for(s=0;s<2;s++){
  calls=error=0;mode=k;present=p;rngWord=randoms[r];randomWord=samples[s];contextWord=c;
  for(i=0;i<0x340;i++)actor.bytes[i]=0xA5;*(void**)(actor.bytes+0x1D4)=p?actor.bytes:0;
  wanted[0]=0x3FE00000;wanted[1]=0xC0300000;wanted[2]=0x47000040;wanted[3]=word(real(randomWord)*11.0f);
  wanted[4]=0;wanted[5]=255;wanted[6]=rngWord%11u+5;wanted[7]=22;wanted[8]=wanted[9]=wanted[10]=0;wanted[11]=255;
  h(actor.bytes,(u8)c,(s32)(0x87654321u^c));if(error||calls!=(p?4u:0u))return 1;
  for(i=0;i<0x340;i++)if((i<0x1D4||i>=0x1D8)&&actor.bytes[i]!=0xA5)return 2;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
    for i,n in enumerate(controls()):t+='if(!check('+n+'))return '+str(i+20)+';\n'
    return t+'return 0;}\n'+START

class ActorRandomBurstTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
        rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>47I',rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>47I',data,fs[source.FUNCTION]['value']));cls.registry=struct.unpack_from('>42I',rom,REGISTRY_ROM);cls.classifiers=struct.unpack_from('>12I',rom,0x22EB44);cls.dispatch=list(struct.unpack_from('>100I',rom,0x16EF2C));cls.real={}
        old=cls.values['conker/build/conker.us.elf'];cls.retained_dispatch=list(struct.unpack_from('>100I',old,source.elf_slot_offset(old,DISPATCH,400)))
        for entry,n in((source.POINT,56),(0x15142314,49),(source.INTEGER_RNG,18),(source.FLOAT_RNG,25)):
            cls.real[entry]=list(struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2D4B0))
        cls.retained_rng={e:list(struct.unpack_from('>%dI'%len(cls.real[e]),old,source.elf_slot_offset(old,e,4*len(cls.real[e]))))for e in(source.INTEGER_RNG,source.FLOAT_RNG)}
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),images=None,entry=source.ENTRY,helpers=None):
        initial,actor=fixture(c);want=packet(initial,c,actor);pair=[];hs=helpers or(source.POINT,source.INTEGER_RNG,source.FLOAT_RNG,source.SUBMIT)
        for words in images or(self.truth,self.words):
            m=BurstOracle(words,initial,c,actor,entry,helpers=hs).run();self.assertEqual(m.packets,[]if want is None else[want],c);self.assertEqual(public(m.memory),public(initial),c)
            expected=[]if want is None else[(hs[0],(STACK+c.phase-12,actor,0,c.context&255)),(hs[1],()),(hs[2],()),(hs[3],want)]
            self.assertEqual(m.calls,expected,c);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));return pair[0]
    def test_01_complete_owner_actual_Make_ABI_and_reference_census(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFB0);self.assertEqual(self.dispatch,self.retained_dispatch);self.assertEqual(tuple(self.registry[10:12]),(source.ENTRY,U32))
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),13)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),12);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_173D40.c.o.compact'),13);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
        rom=self.values['conker/conker.us.bin'];ws=struct.unpack('>%dI'%(len(rom)//4),rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22EB9C]);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws))
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=47,frame=80,guards=0,bindings=4,neighbors=12,compact_functions=13,Make_commands=3,ABI='void(u8*,u8,s32)',registry_slot=5,entries=21,default_promoted_point_helper_call=True,point_home=68,count_home=66)
    def test_02_context_bytes_unsigned_rng_boundaries_aliases_and_private_state(self):
        count=0;visits=set()
        for byte,high,attached,phase in itertools.product(range(256),(0,0x12340000,0xFFFFFF00),(0,1),(0,8)):
            c=Case(byte|high,byte^U32,attached,rng=(byte*1664525+1013904223)&U32,random=bits((byte%65)/64.));visits.update(self.compare(replace(c,phase=phase)).visits);count+=1
        for rng,random,mode,write,alias in itertools.product((0,1,10,11,12,0x7FFFFFFF,0x80000000,0xFFFFFFFE,U32),(0,1,bits(.5),bits(-.25),bits(1e20)),range(4),(False,True),range(4)):
            self.compare(Case(rng=rng,random=random,mode=mode,write=write,alias=alias));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+188,4)));self.receipt['guest']=dict(cases=count,all_47_words_visited=True,all_context_bytes_and_high_word_noise=True,full_unsigned_RNG_boundaries=True,three_incoming_homes_and_unused_word_preserved=True,four_alias_layouts=True,late_point_and_signed_short_count_loads=True,unwritten_output_seed_guest_only=True,complete_private_state_equal=True)
    def test_03_original_and_retained_dispatcher_real_callback_registry(self):
        rom=self.values['conker/conker.us.bin'];count=0;visits=set()
        for context,attached,path,amount,phase in itertools.product((0,1,2,0xFFFFFF80),(0,1),(0,1),(0x8000,0,0x7FFF),(0,8)):
            c=Case(context=context,unused=signed16(amount)&U32 if path else 0,attached=attached,phase=phase);initial,actor=fixture(c);initial[0x800BE616]=0;put(initial,actor+0x184,0x12345678);put(initial,actor+0x2F4,NODE if path else 0);put(initial,NODE+0x10,RECORD);put(initial,NODE+0x14,0);put(initial,RECORD+0x28,5);put(initial,RECORD+0xE,amount,2)
            for i,v in enumerate(self.registry):put(initial,REGISTRY+4*i,v)
            for i,v in enumerate(self.classifiers):put(initial,0x8008A084+4*i,v)
            pair=[]
            for target in(self.truth,self.words):
                connected={source.ENTRY+4*i:w for i,w in enumerate(target)};m=BurstOracle(self.dispatch,initial,c,actor,DISPATCH,connected,selected=-1 if path else 5,list_path=bool(path)).run();pair.append(m);visits.update(m.visits)
            self.assertEqual(complete(pair[0]),complete(pair[1]));m=pair[0];want=packet(initial,c,actor,STACK+phase-72);self.assertEqual(m.packets,[]if want is None else[want]);calls=[args for target,args in m.calls if target==source.ENTRY];self.assertEqual(calls,[(actor,context,c.unused)]);self.assertEqual(public(m.memory),public(initial));count+=1
        self.receipt['caller']=dict(cases=count,original_retained_100_word_dispatcher_equal=True,dispatcher_words_visited=len(set(range(DISPATCH,DISPATCH+400,4))&visits),actual_21_entry_registry_slot5_count_minus1=True,direct_and_linked_record_paths=True,third_signed_halfword_ignored_by_target=True,classification_and_search_are_bounded_contracts=True,no_complete_classifier_list_or_gameplay_claim=True)
    def test_04_native32_typed_calls_and_effective_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=18432,effective_controls=8,trapping_UBSan=True,typed_byte_context_and_void_return=True,all_context_bytes=True,valid_initialized_point_provider_only=True,no_incompatible_function_pointer_call=True,retained_position_pointer_mutation_is_defined=True)
    def test_05_fault_prefixes_and_original_point_matrix_RNG_chain(self):
        cuts=0
        for c in(Case(attached=0),Case(),Case(mode=1),Case(mode=2),Case(mode=3),Case(write=False),Case(alias=1)):
            initial,actor=fixture(c);good=self.compare(c)
            for cut in range(good.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=BurstOracle(words,initial,c,actor);x.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,cut);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        self.assertEqual(self.retained_rng,{e:self.real[e]for e in self.retained_rng});n=0;seen=set();rom=self.values['conker/conker.us.bin'];factor=struct.unpack_from('>I',rom,0x8009F740-0x80082B20+0x2275E0)[0]
        for context,attached,seed,phase in itertools.product((0,1,2,255),(0,1),SEEDS,(0,8)):
            c=Case(context=context,attached=attached,phase=phase);initial,actor=fixture(c);put(initial,actor+0x1D4,MATRIX if attached else 0);initial[0x800C3E90]=0;put(initial,0x800885B0,seed,8);put(initial,0x8009F740,factor)
            for joint in(19,23):
                for i,v in enumerate(c.point):put(initial,MATRIX+joint*64+0x30+4*i,v)
            connected={a+4*i:w for a,body in self.real.items()for i,w in enumerate(body)};pair=[]
            for target in(self.truth,self.words):m=BurstOracle(target,initial,c,actor,connected=connected).run();pair.append(m);seen.update(m.visits)
            self.assertEqual(complete(pair[0]),complete(pair[1]));m=pair[0]
            if attached:
                first=next_seed(seed);second=next_seed(first);self.assertEqual(read(m.memory,0x800885B0,8),second);pos=c.point if context in(1,2)else tuple(read(initial,STACK+phase-12+4*i)for i in range(3));scale=bits(floating(bits(float(second&65535)))*floating(factor));expected=(*pos,bits(floating(scale)*11.),0,255,(first&U32)%11+5,22,0,0,0,255);self.assertEqual(m.packets,[expected]);self.assertEqual([args[1]for target,args in m.calls if target==0x15142314],[]if context not in(1,2)else[19 if context==1 else 23])
            else:self.assertFalse(m.calls);self.assertFalse(m.packets);self.assertEqual(read(m.memory,0x800885B0,8),seed)
            n+=1
        self.receipt['faults_helpers']=dict(fired_prefix_pairs=cuts,original_point_matrix_and_retained_RNG_integrations=n,original_point_helper_words=56,original_matrix_words=49,RNG_words=[18,25],visited_helper_words={hex(e):len(set(range(e,e+4*len(body),4))&seen)for e,body in self.real.items()},floating_matrix_path_only=True,unsupported_selectors_preserve_seeded_guest_point=True,point_helper_C_stub_stays_uncredited=True,submit_is_bounded_contract=True,portable_C_fault_uninitialized_or_hardware_claim=False)
    def test_06_actual_padder_raw_controls_and_independent_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'))
        for b,bindings in((raw[:-4],rs),(bytes([raw[0]^1])+raw[1:],rs),(raw,rs|{48:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        links=0;cases=0
        for i,delta in enumerate((0,0x200000,0x10000000)):
            entry=source.ENTRY+delta;hs=tuple(x+delta for x in(source.POINT,source.INTEGER_RNG,source.FLOAT_RNG,source.SUBMIT));symbols={'func_%08X'%a:b for a,b in zip((source.POINT,source.INTEGER_RNG,source.FLOAT_RNG,source.SUBMIT),hs)};asm,missing=emit_function(raw,dict(value=0,size=188),rs,source.FUNCTION,symbols);self.assertFalse(missing);p=self.fresh/('rebase-%d.s'%i);p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True);images=[]
            for j,obj_ in enumerate((self.out/('original-'+source.FUNCTION+'.o'),obj)):
                p=self.fresh/('link-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj_)],capture_output=True,check=True);images.append(list(struct.unpack_from('>47I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(*images)
            for c in(Case(attached=0),Case(),Case(mode=2),Case(mode=3),Case(alias=1),Case(write=False)):self.compare(c,images,entry,hs);cases+=1
        self.receipt['rebases']=dict(GNU_links=links,layouts=3,guest_cases=cases,different_JAL_region=True,four_bindings_preserved=True,raw_negative_controls=3,guards=0)
    def test_07_compiled_short_home_negative_controls(self):
        b=source.SELECTED.replace('s16 count;','s32 count;');obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+b,'negative-wide-count');self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));c=Case(mode=3);initial,actor=fixture(c);want=packet(initial,c,actor);m=BurstOracle(words,initial,c,actor).run();self.assertNotEqual(m.packets,[want]);self.receipt['negative_order']=dict(actual_compiled_wide_count_home_mutant_rejected=True,signed_halfword_home_change_observable=True)
    def test_08_strict_full_image_inputs_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+188];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,188);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+188,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        for bad in(expected[:-1],expected+bytes([0])):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        for b,t in((before[:-1],truth),(before,truth[:-1]),(before,bytes([truth[0]^1])+truth[1:])):
            with self.assertRaises(ValueError):source.check_image(b,expected,t)
        q=json.loads((self.out/'preparation.json').read_text());self.assertEqual((q['changed_bytes'],q['code_bytes'],q['metadata_bytes'],q['exclusions']),(141,140,1,0));self.receipt['strict']=dict(changed_bytes=141,code_bytes=140,metadata_bytes=1,exclusions=0,corruptions=7,wrong_inputs=3,focused_inputs=len(v))
if __name__=='__main__':unittest.main()
