"""Matrix-bound interpolation: six-argument O32 ABI, original callers and helper routes."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,math,os,struct,subprocess,unittest
from tools.experiments import game_matrix_point_interpolation_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.test_game_point_transform_match import PointOracle,put,read,STATUS,DIAGNOSTIC,FLAG,CONVERT,TRANSFORM,TRANSLATE
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
BINDING,ACTOR,MATRICES,OUTPUT,ALTERNATE,ASSET,OWNER=0x28000,0x30000,0x50000,0x44000,0x45000,0x48000,0x46000

@dataclass(frozen=True)
class Case:
    present:bool=True
    index:int=0
    origin:tuple=(0x3F800000,0xC0000000,0x40400000)
    amount:int=0x3F000000
    transformed:tuple=(0x41300000,0xC1400000,0x41500000)
    point:tuple=(0x3F800000,0xC0000000,0x3F000000)
    layout:int=0
    phase:int=0
    mode:int=0
    fixed:int=0

def output_address(c):
    sp=STACK+c.phase
    return(OUTPUT,BINDING+8,BINDING,ACTOR+0x1D4,sp+16,sp+20,sp+8,sp-8,sp-12,sp+4)[c.layout]

def fixture(c):
    m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-2048,1024)}
    for base,size in((BINDING,0x100),(ACTOR,0x400),(OUTPUT,0x100),(ALTERNATE,0x100),(OWNER,0x200),(ASSET,0x80),(STATUS-4,32)):
        for i in range(size):m[base+i]=(i*13+(base>>16))&255
    put(m,BINDING,ACTOR);m[BINDING+5]=c.index;put(m,ACTOR+0x1D4,MATRICES if c.present else 0)
    for i,v in enumerate(c.point):put(m,BINDING+8+4*i,v)
    put(m,STACK+c.phase+16,c.origin[2]);put(m,STACK+c.phase+20,c.amount)
    matrix=MATRICES+c.index*64;values=[0.0]*16;values[0],values[5],values[10],values[15]=.5,1.0,2.0,1.0;values[12:15]=3.0,-4.0,5.0
    if c.fixed:
        integers=[int(x*65536)&0xFFFFFFFF for x in values];data=struct.pack('>32H',*[x>>16 for x in integers],*[x&65535 for x in integers])
    else:data=struct.pack('>16I',*[bits(x)for x in values])
    m.update({matrix+i:v for i,v in enumerate(data)});m[FLAG]=c.fixed
    return m

def interpolate(a,b,t):return bits(floating(bits(floating(bits(floating(a)-floating(b)))*floating(t)))+floating(b))
def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+1024}

def effects(m,c,p,sp):
    if c.mode==1:
        m[p+5]^=128;put(m,read(m,p)+0x1D4,0);put(m,p+8,bits(42))
    elif c.mode in(2,3):
        for i,v in enumerate((bits(4),bits(-5),bits(6),bits(.25)),2):put(m,sp+4*i,v)
        if c.mode==3:put(m,sp+4,ALTERNATE)

def reference(initial,c,p=BINDING,out=None):
    m=dict(initial);sp=STACK+c.phase;out=output_address(c)if out is None else out;put(m,sp,p);put(m,sp+4,out);actor=read(m,p);matrix=read(m,actor+0x1D4)
    if not matrix:return m,0,[]
    matrix+=m[p+5]*64;put(m,sp+12,c.origin[1]);put(m,sp+8,c.origin[0]);local=sp-12
    for i,v in enumerate(c.transformed):put(m,local+4*i,v)
    effects(m,c,p,sp)
    for i in range(4):put(m,sp-40+4*i,0xB5000000+i)
    origins=(read(m,sp+8),read(m,sp+12),read(m,sp+16));amount=read(m,sp+20);out=read(m,sp+4)
    for i,v in enumerate(origins):put(m,out+4*i,interpolate(read(m,local+4*i),v,amount))
    return m,1,[(source.HELPER,(p+8,local,matrix))]

# Reuse point-helper hooks with the tracked timing oracle through one MRO.
class InterpolationOracle(PointOracle,TimingOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,helper=source.HELPER,p=BINDING,out=None):
        out=output_address(c)if out is None else out
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(p,out,*c.origin,c.amount),connected=connected)
        self.c,self.helper,self.binding=c,helper,p;self.mutate=False;self.input_args=(p+8,STACK+c.phase-12,MATRICES+c.index*64);self.observed=[];self.hi=0x89ABCDEF;self.lo=0x76543210;self.condition=True
    def record_call(self,target):
        if target in(self.helper,source.ENTRY):
            args=self.arguments(3 if target==self.helper else 6);self.calls.append((target,args));self.events.append(('CALL',target,args))
            if target==self.helper:self.input_args=args;self.observed.append(tuple(read(self.memory,args[0]+4*i)for i in range(3)))
        else:PointOracle.record_call(self,target)
    def hook(self,target):
        if target!=self.helper:return PointOracle.hook(self,target)
        point,out,matrix=self.arguments(3)
        for i,v in enumerate(self.c.transformed):put(self.memory,out+4*i,v)
        effects(self.memory,self.c,self.binding,STACK+self.c.phase)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678
    def execute(self,word):
        if word>>26 not in(33,41):return super().execute(word)
        rs,rt,imm=word>>21&31,word>>16&31,word&65535;at=(self.r[rs]+(imm if imm<32768 else imm-65536))&0xFFFFFFFF;self.dispatched_word=word;self.own_instruction=True
        try:
            if word>>26==33:self.r[rt]=((self.get(at,2)^32768)-32768)&0xFFFFFFFF
            else:self.put(at,self.r[rt]&65535,2)
            self.r[0]=0
        finally:self.own_instruction=False

class WindowDone(Exception):pass
class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc in self.owner.window_ends:self.owner.stopped=pc;raise WindowDone
        return super().__getitem__(pc)

def controls():
    b=source.SELECTED
    result=dict(wrong_null=b.replace('        return 0;','        return 1;'),wrong_success=b.replace('    return 1;','    return 0;'),
        index_mask=b.replace('matrices[binding->matrixIndex]','matrices[binding->matrixIndex & 0x7F]'),
        wrong_point=b.replace('func_15143134(binding->point,','func_15143134(binding->point + 1,'),
        wrong_y=b.replace('transformed[1] - y','transformed[0] - y'),
        reversed_x=b.replace('transformed[0] - x','x - transformed[0]'),
        wrong_amount_z=b.replace('(transformed[2] - z) * amount','(transformed[2] - z) * z'),
        missing_origin_x=b.replace('* amount + x;','* amount + 0.0f;'))
    assert all(v!=b for v in result.values());return result

def corpus():
    values=(0,0x80000000,1,0x80000001,0x007FFFFF,bits(1),bits(-2.5),bits(16777216),0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345)
    for p,axis,amount,present,phase in itertools.product(values,range(3),(bits(0),bits(-0.0),bits(.5),bits(1),bits(-1)),(0,1),(0,8)):
        origins=[bits(1),bits(-2),bits(3)];target=[bits(11),bits(-12),bits(13)];origins[axis]=p;target[(axis+1)%3]=p
        yield Case(bool(present),(p+axis)&255,tuple(origins),amount,tuple(target),phase=phase)
    for index in range(256):yield Case(index=index)

def native_harness(cases):
    rows=[]
    for c in cases:
        initial=fixture(c);m,result,_=reference(initial,c);out=output_address(c);expected=tuple(read(m,out+4*i)for i in range(3))
        if not c.present:expected=(bits(71),bits(-72),bits(73))
        rows.append('{%d,%d,%d,{%s},0x%Xu,{%s},{%s}}'%(c.present,c.index,c.mode,','.join('0x%Xu'%x for x in c.origin),c.amount,','.join('0x%Xu'%x for x in c.transformed),','.join('0x%Xu'%x for x in expected)))
    text=source.HEADERS+source.DECLARATIONS+'''
static struct {u8 reserved[0x1D4];u8(*matrices)[64];} actor;
static u8 matrices[256][64];static MatrixPointBinding binding;
static f32 output[3],origins[3],desired[3];
static u32 calls,error,expectedIndex,mode;
typedef s32(*Handler)(MatrixPointBinding*,f32*,f32,f32,f32,f32);
typedef char ABI[(sizeof(void*)==4&&sizeof(f32)==4&&sizeof(MatrixPointBinding)==20&&
 __builtin_offsetof(MatrixPointBinding,matrixIndex)==5&&__builtin_offsetof(MatrixPointBinding,point)==8&&
 __builtin_offsetof(__typeof__(actor),matrices)==0x1D4)?1:-1];
static f32 real(u32 b){f32 v;__builtin_memcpy(&v,&b,4);return v;}
static u32 word(f32 v){u32 b;__builtin_memcpy(&b,&v,4);return b;}
static int same(u32 a,u32 b){return(a&0x7FFFFFFFu)>0x7F800000u&&(b&0x7FFFFFFFu)>0x7F800000u?1:a==b;}
__attribute__((noinline,noclone)) void func_15143134(f32 *point,f32 *out,u8 *matrix){
 u32 i;if(point!=binding.point||matrix!=matrices[expectedIndex]||calls++)error=1;
 for(i=0;i<3;i++)out[i]=desired[i];
 if(mode==1){binding.matrixIndex^=128;actor.matrices=0;binding.point[0]=42.0f;}
}
'''
    for name,body in dict(selected=source.SELECTED,**controls()).items():text+=body.replace(source.FUNCTION,name)+'\n'
    text+='static const struct{u32 present,index,mode,origin[3],amount,target[3],expected[3];}cases[]={'+',\n'.join(rows)+'};\n'
    text+='''static int one(Handler fn,u32 n,u32 alias,u32 indirect){
 const __typeof__(cases[0])*c=&cases[n];u32 i;f32 *out=alias==1?binding.point:alias==2?origins:output;
 for(i=0;i<3;i++){output[i]=(f32)(i==1?-72:i==2?73:71);binding.point[i]=(f32)(i+1);origins[i]=real(c->origin[i]);desired[i]=real(c->target[i]);}
 binding.owner=(u8*)&actor;binding.matrixIndex=c->index;actor.matrices=c->present?matrices:0;expectedIndex=c->index;mode=c->mode;calls=error=0;
 if(!c->present&&alias) return 0;
 s32 result;if(indirect){Handler volatile dispatch=fn;result=dispatch(&binding,out,origins[0],origins[1],origins[2],real(c->amount));}
 else result=fn(&binding,out,origins[0],origins[1],origins[2],real(c->amount));
 if(error||result!=(s32)c->present||calls!=c->present)return 1;
 for(i=0;i<3;i++)if(!same(word(out[i]),c->expected[i]))return 1;
 return 0;
}
static int variant(Handler fn,u32 all){u32 n,a,d;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(a=0;a<(all?3u:1u);a++)for(d=0;d<2;d++)if(one(fn,n,a,d))return 23;return 0;}
int run(void){if(variant(selected,1))return 1;
'''
    for i,name in enumerate(controls()):text+='if(variant(%s,0)!=23)return %d;\n'%(name,11+i)
    return text+'return 0;}\n'+START,len(cases)

class MatrixPointInterpolationTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
        rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>46I',rom,source.ROM));cls.helper=list(struct.unpack_from('>98I',rom,source.HELPER_ROM));old=cls.values['conker/build/conker.us.elf'];cls.retained_helper=list(struct.unpack_from('>98I',old,source.elf_slot_offset(old,source.HELPER,392)))
        data,fs=source.link_owner(ROOT,cls.fresh,cls.out/'qualified-padded.o',source.OWNER);cls.words=list(struct.unpack_from('>46I',data,fs[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),initial=None,images=None,entry=source.ENTRY,helper=source.HELPER):
        initial=fixture(c)if initial is None else initial;expected,result,calls=reference(initial,c);pair=[]
        for words in images or(self.truth,self.words):
            m=InterpolationOracle(words,initial,c,entry=entry,helper=helper).run();self.assertEqual(public(m.memory),public(expected),c)
            out=ALTERNATE if c.mode==3 and c.present else output_address(c);self.assertEqual(tuple(read(m.memory,out+4*i)for i in range(3)),tuple(read(expected,out+4*i)for i in range(3)),c);self.assertEqual(m.r[2],result,c)
            self.assertEqual([(source.HELPER if t==helper else t,a)for t,a in m.calls],calls);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));return pair[0]
    def test_01_complete_owner_Make_six_argument_ABI_and_reference_census(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.helper,self.retained_helper);self.assertEqual(self.words[0],0x27BDFFD8);self.assertEqual(self.words[4],0xAFBF0014)
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),23)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),22);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
        self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_1CA420.c.o.compact'),23);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
        rom=self.values['conker/conker.us.bin'];jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);hits=[];pointers=[]
        for i in range(0,len(rom)-3,4):
            word=struct.unpack_from('>I',rom,i)[0]
            if word==jal:hits.append(i)
            if word==source.ENTRY:pointers.append(i)
        self.assertEqual(hits,[0x1CA640,0x1CA998,0x1CAA10]);self.assertFalse(pointers)
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=46,frame=40,guards=0,bindings=1,neighbors=22,compact_functions=23,Make_commands=3,diagnostics_empty=True,six_argument_ABI='s32(binding*,f32*,f32,f32,f32,f32)',original_direct_callers=3,unreachable_original_word=15,actual_64_byte_matrix_table=True)
    def test_02_float32_boundaries_and_unsigned_matrix_indices(self):
        cases=list(corpus());visits=set()
        for c in cases:visits.update(self.compare(c).visits)
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+184,4))-visits,{source.ENTRY+60})
        self.receipt['guest']=dict(cases=len(cases),all_256_matrix_bytes=True,origin_amount_subtract_multiply_add_separately_rounded=True,signed_zero_subnormal_infinity_qNaN_model_cases=True,reachable_words=45,all_46_literal_words_retained=True,complete_private_state_equal=True,FCSR_or_hardware_acceptance_claimed=False)
    def test_03_output_aliases_live_argument_homes_and_sparse_failure(self):
        count=0
        for layout,mode,phase in itertools.product(range(10),range(4),(0,8)):
            self.compare(Case(layout=layout,mode=mode,phase=phase));count+=1
        c=Case(present=False);m=fixture(c);keep={BINDING+i for i in range(4)}|{ACTOR+0x1D4+i for i in range(4)}|{a for a in m if STACK-40<=a<STACK+8};sparse={a:v for a,v in m.items()if a in keep}
        for words in(self.truth,self.words):
            x=InterpolationOracle(words,sparse,c).run();self.assertEqual(x.r[2],0);self.assertFalse(x.calls)
        self.receipt['aliases']=dict(cases=count,output_layouts=10,provider_modes=4,live_output_x_y_z_and_amount_homes=True,local_point_reads_follow_output_writes=True,sparse_null_table_needs_no_index_point_output_or_stack_floats=True,private_homes_and_frame_aliases_guest_only=True)
    def test_04_native32_typed_six_argument_callers_and_controls(self):
        cases=[c for c in corpus()if c.phase==0];cases.extend(Case(index=i,mode=1)for i in(0,1,128,255));text,count=native_harness(cases)
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(text);binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],vectors_per_profile=count,typed_six_argument_indirect_calls=True,three_output_alias_choices=True,effective_controls=len(controls()),trapping_UBSan=True,finite_values_and_signed_zero_bit_exact=True,NaN_classification_only=True,opaque_transform_contract_not_full_helper_acceptance=True)
    def test_05_fault_prefixes_and_complete_original_retained_helper_routes(self):
        count=0
        for c in(Case(present=False),Case(),Case(layout=7),Case(mode=3)):
            initial=fixture(c);m=self.compare(c)
            for cut in range(m.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=InterpolationOracle(words,initial,c);x.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,cut);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));count+=1
        rom=self.values['conker/conker.us.bin'];lower={}
        for entry,at,n in((CONVERT,0x21D368,46),(TRANSFORM,0xD4E10,40),(TRANSLATE,0x16F7C4,49)):lower.update({entry+4*i:w for i,w in enumerate(struct.unpack_from('>%dI'%n,rom,at))})
        integration=0;visits=set()
        for helper in(self.helper,self.retained_helper):
            for fixed,zero,phase in itertools.product((0,1,255),(0,1),(0,8)):
                c=Case(index=255,fixed=fixed,point=(0,0x80000000,0)if zero else Case().point,phase=phase);initial=fixture(c);point=(bits(3),bits(-4),bits(5))if zero else(bits(3.5),bits(-6),bits(6));expected=tuple(interpolate(a,b,c.amount)for a,b in zip(point,c.origin));pair=[]
                connected=lower|{source.HELPER+4*i:w for i,w in enumerate(helper)}
                for words in(self.truth,self.words):
                    m=InterpolationOracle(words,initial,c,connected=connected).run();self.assertEqual(tuple(read(m.memory,OUTPUT+4*i)for i in range(3)),expected);self.assertEqual(m.r[2],1);self.assertEqual(read(m.memory,STATUS),0);pair.append(m);visits.update(m.visits)
                self.assertEqual(complete(pair[0]),complete(pair[1]));integration+=1
        self.assertTrue(set(range(TRANSFORM,TRANSFORM+160,4))<=visits);self.assertTrue(set(range(TRANSLATE,TRANSLATE+196,4))<=visits)
        self.receipt['faults_helper']=dict(fired_fault_prefix_pairs=count,helper_integration_cases=integration,complete_original_and_retained_98_words=True,actual_original_fixed_converter_transform_and_translation=True,zero_point_and_float_fixed_matrix_routes=True,full_hardware_FCSR_gameplay_acceptance_claimed=False)
    def test_06_three_original_caller_windows_and_return_consumers(self):
        rom=self.values['conker/conker.us.bin'];windows=((0x1519D0C8,0x1519D1A0,{0x1519D1A0,0x1519D1C8}),(0x1519D4B8,0x1519D4F8,{0x1519D4F8,0x1519D524,0x1519D52C}),(0x1519D52C,0x1519D570,{0x1519D570,0x1519D628}));count=0
        for which,(start,end,ends)in enumerate(windows):
            window=list(struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2D4B0))
            for present,index,phase,skip in itertools.product((0,1),(0,128,255),(0,8),(0,1)if which else(0,)):
                c=Case(bool(present),index,phase=phase);initial=fixture(c);sp=STACK+phase;p=sp+0x4C if which==0 else BINDING;out=sp+0xAC if which==0 else OWNER+0x10
                if which==0:
                    put(initial,p,ACTOR);initial[p+5]=index;put(initial,ASSET+0x10,index,1)
                    for i,v in enumerate(c.point):put(initial,ASSET+0x14+4*i,v)
                    origins=(0,0,0);amount=bits(1)
                elif which==1:origins=(0,0,0);amount=bits(1)
                else:
                    origins=c.origin;amount=c.amount;put(initial,BINDING+0x3C,amount)
                    for i,v in enumerate(origins):put(initial,OWNER+0x10+4*i,v)
                pair=[]
                for words in(self.truth,self.words):
                    connected={source.ENTRY+4*i:w for i,w in enumerate(words)};m=InterpolationOracle(window,initial,c,entry=start,connected=connected,p=p,out=out);m.window_ends=ends;m.code=WindowCode(dict(m.code),m);m.r[2]=ASSET if which==0 else skip if which==2 else 0;m.r[17]=OWNER;m.r[18]=BINDING;m.r[25]=4 if skip else 0;m.f[0]=0;m.f[22]=bits(1)
                    with self.assertRaises(WindowDone):m.run()
                    calls=[args for target,args in m.calls if target==source.ENTRY]
                    if skip:self.assertFalse(calls)
                    else:
                        self.assertEqual(calls,[(p,out,*origins,amount)]);self.assertEqual(m.r[2],present)
                        if present:self.assertEqual(tuple(read(m.memory,out+4*i)for i in range(3)),tuple(interpolate(a,b,amount)for a,b in zip(c.transformed,origins)))
                    pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].stopped,pair[1].stopped);count+=1
        self.receipt['callers']=dict(cases=count,authentic_windows=3,six_argument_envelopes_and_branch_consumers=True,first_caller_owner_home_seed_matches_original_1519D090_store=True,large_caller_bodies_remain_unrestored_placeholders=True,no_full_caller_acceptance_claimed=True)
    def test_07_padder_raw_controls_and_independent_GNU_rebases(self):
        raw,bindings=source.checked_payload(*source.payload(self.out/'selected.o'))
        for data,rs in((raw[:-4],bindings),(bytes([raw[0]^1])+raw[1:],bindings),(raw,bindings|{76:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(data,rs)
        p=self.fresh/'padded.s';p.write_text(emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        asm,missing=emit_function(raw,dict(value=0,size=184),bindings,source.FUNCTION,dict(func_15143134=source.HELPER));self.assertFalse(missing);p=self.fresh/'independent.s';p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True);count=0
        for i,(entry,helper)in enumerate(((source.ENTRY,source.HELPER),(0x1539E304,0x15443134),(0x2519E304,0x25143134))):
            images=[]
            for j,object_ in enumerate((self.out/('original-'+source.FUNCTION+'.o'),obj)):
                p=self.fresh/('rebase-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=func_15143134=0x%X'%helper,'-o',str(elf),str(object_)],capture_output=True,check=True);images.append(list(struct.unpack_from('>46I',sections(elf)['.text'][1])))
            self.assertEqual(*images)
            for c in(Case(present=False),Case(),Case(index=255),Case(mode=3,layout=7)):
                self.compare(c,images=images,entry=entry,helper=helper);count+=1
        self.receipt['rebases']=dict(layouts=3,GNU_links=6,guest_cases=count,different_JAL_region=True,one_call_binding=True,raw_negative_controls=3,guards=0)
    def test_08_strict_full_image_inputs_and_corruptions(self):
        values=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=values['conker/build/conker.us.elf'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+184];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,184);symbol=next(pos for pos,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+184,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        for bad in(expected[:-1],expected+bytes([0])):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        for b,t in((before[:-1],truth),(before,truth[:-1]),(before,bytes([truth[0]^1])+truth[1:])):
            with self.assertRaises(ValueError):source.check_image(b,expected,t)
        q=json.loads((self.out/'preparation.json').read_text());self.assertEqual((q['changed_bytes'],q['code_bytes'],q['metadata_bytes'],q['exclusions']),(142,141,1,0));self.receipt['strict']=dict(changed_bytes=142,code_bytes=141,metadata_bytes=1,exclusions=0,corruptions=7,wrong_inputs=3,focused_inputs=len(values))
if __name__=='__main__':unittest.main()
