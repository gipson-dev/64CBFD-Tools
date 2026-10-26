"""Plane-component pair: original words, ABI, aliases, inventory and strict image."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,math,struct,subprocess,unittest
from tools.experiments import game_planar_direction_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
OUT,INPUT,ACTOR,RECORD=0x20000,0x30000,0x40000,0x41000
VALUES=tuple(bits(x)for x in(0.0,-0.0,1.0,-1.0,3.0,4.0,-7.0,1e-10,1e10))
CALLS=(0x1504B7C8,0x15051298,0x150512E0,0x15051604,0x15051720)
WINDOWS=((0x1504B794,0x1504B7E8,0x1504B824,(0x58,0x54,0x50,0x4C,0x48)),
         (0x150511FC,0x150512A0,0x15051510,(0x64,0x60,0x5C,0x6C,0x68)),
         (0x150512A0,0x150512E8,0x15051358,(0x64,0x60,0x5C,0x6C,0x68)),
         (0x150515CC,0x15051614,0x150516D8,(0x6C,0x68,0x64,0x94,0x90)),
         (0x150516F4,0x15051728,0x15051734,(0x6C,0x68,0x64,0x94,0x90)))


@dataclass(frozen=True)
class Case:
    first:int=0x40400000
    second:int=0x40800000
    alias:int=0
    phase:int=0
    mode:int=0


def arguments(c):
    sp=STACK+c.phase
    layouts=((OUT,OUT+4,OUT+8,OUT+12,OUT+16),
        (OUT,OUT,OUT+8,OUT+12,OUT+16),(OUT,OUT+4,OUT+8,OUT,OUT+4),
        (OUT,OUT+4,OUT+8,OUT+4,OUT),(OUT,OUT+4,OUT+8,OUT+12,OUT+12),
        (OUT,OUT+4,OUT+8,sp-4,sp-8),(sp-8,OUT+4,OUT+8,OUT+12,OUT+16),
        (OUT,OUT+4,OUT+8,source.SCALE,OUT+16),(OUT,OUT+4,OUT+8,OUT+12,source.SCALE),
        (OUT,OUT+4,0xDEAD0001,OUT+12,OUT+16),(OUT,OUT+4,OUT+8,sp+8,sp+12),
        (OUT,OUT+4,OUT+8,sp+24,OUT+16),(OUT,OUT+4,OUT+8,sp+20,OUT+16),
        (OUT,OUT+4,OUT+8,OUT+12,sp-4))
    return(INPUT,INPUT+0x40,*layouts[c.alias])


def fixture(c,args=None):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-768,384)}
    for base,size in((OUT-16,128),(INPUT-32,256),(ACTOR,0x400),(RECORD,0x100)):
        memory.update({base+i:(i*13+0x5A)&255 for i in range(size)})
    put(memory,source.SCALE,0x3CA3D70A)
    for i,value in enumerate((args or arguments(c))[4:]):put(memory,STACK+c.phase+16+4*i,value)
    return memory


def divide(a,b):
    a,b=floating(a),floating(b)
    return bits(a/b if b else math.nan if not a else math.copysign(math.inf,a*math.copysign(1.0,b)))


def reference(initial,c,args=None):
    memory=dict(initial);args=args or arguments(c);sp=STACK+c.phase
    for i,value in enumerate(args[4:]):put(memory,sp+16+4*i,value)
    put(memory,sp+8,args[2]);put(memory,sp+12,args[3])
    for i in range(4):put(memory,sp-40+4*i,0xB5000000+i)
    put(memory,sp-4,c.first);put(memory,sp-8,c.second)
    if c.mode:put(memory,source.SCALE,0x3D4CCCCD)
    a,b=floating(c.first),floating(c.second)
    squared=bits(floating(bits(a*a))+floating(bits(b*b)))
    directionA,directionB=read(memory,sp+8),read(memory,sp+12)
    put(memory,read(memory,sp+20),c.first)
    put(memory,read(memory,sp+24),c.second)
    factor=read(memory,source.SCALE)
    length=bits(floating(bits(math.sqrt(floating(squared))))*floating(factor))
    first=read(memory,sp-4)
    if floating(length)==0.0:put(memory,directionA,bits(1.0));put(memory,directionB,0)
    else:
        put(memory,directionA,divide(first,length))
        put(memory,directionB,divide(read(memory,sp-8),length))
    return memory


def public(memory,args,c,caller=False):
    outputs=set(a+i for a in(*args[2:4],*args[5:])for i in range(4))
    # The intentionally unused argument can be unmapped and need not be read.
    return {a:b for a,b in memory.items()if not STACK-768<=a<STACK+384 or a in outputs or caller and STACK+c.phase<=a<STACK+c.phase+160}


def plane_components(vertices):
    def binary(a,b,op):
        a,b=floating(a),floating(b)
        return bits(a*b if op=='mul'else a-b)
    for step in range(6):
        axis=step%3;next_=(axis+1)%3;last=(axis+2)%3
        one=[bits(float(vertices[next_][i]-vertices[axis][i]))for i in range(3)]
        two=[bits(float(vertices[last][i]-vertices[axis][i]))for i in range(3)]
        if step>=3:one,two=two,one
        positive=binary(one[0],two[2],'mul');negative=binary(two[0],one[2],'mul')
        if step==5:return 0,0
        if floating(positive)==floating(negative)or floating(two[0])==0.0:continue
        numerator=binary(binary(two[0],one[1],'mul'),binary(one[0],two[1],'mul'),'sub')
        denominator=binary(negative,positive,'sub');second=divide(numerator,denominator)
        first=divide(binary(two[1],binary(second,two[2],'mul'),'sub'),two[0])
        return first,second
    raise AssertionError('Unreachable triangle retry tail')


class Boundary(Exception):pass


class EndCode(faults.TrackedCode):
    def __contains__(self,pc):
        return pc in self.owner.ends or super().__contains__(pc)
    def __getitem__(self,pc):
        if pc in self.owner.ends:raise Boundary
        return super().__getitem__(pc)


class PlanarOracle(TimingOracle):
    def __init__(self,words,memory,c=Case(),args=None,entry=source.ENTRY,connected=None,ends=(),scale=source.SCALE,helper=source.HELPER):
        args=args or arguments(c)
        super().__init__(words,memory,phase=c.phase,entry=entry,arguments=args,connected=connected)
        self.case,self.initial_args,self.ends,self.scale,self.helper=c,args,set(ends),scale,helper
        self.calls=[];self.target_calls=[];self.hi,self.lo=0x12345678,0x89ABCDEF
        if ends:self.code=EndCode(self.code,self)
    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==4:
            self.f[word>>6&31]=bits(math.sqrt(floating(self.f[word>>11&31])))
            return
        super().execute(word)
    def record_call(self,target):
        if target==source.ENTRY:
            self.target_calls.append(self.arguments(7));self.calls.append((target,self.arguments(7)))
        else:
            assert target==self.helper,hex(target)
            self.calls.append((target,self.arguments(4)))
        self.events.append(('CALL',target,self.calls[-1][1]))
    def hook(self,target):
        assert target==self.helper
        a,b,x,y=self.arguments(4)
        assert(a,b)==self.initial_args[:2],((a,b),self.initial_args[:2])
        assert(x,y)==(STACK+self.case.phase-4,STACK+self.case.phase-8)
        self.put(x,self.case.first,4);self.put(y,self.case.second,4)
        if self.case.mode:self.put(self.scale,0x3D4CCCCD,4)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=(0,0xDEADBEEF)[self.case.mode];self.hi,self.lo=0x76543210,0xFEDCBA98


def controls():
    b=source.SELECTED
    return dict(wrong_fallback=b.replace('*directionA = 1.0f;','*directionA = 0.0f;'),
        wrong_zero=b.replace('length == 0.0f','length < 0.0f'),
        missing_sqrt=b.replace('sqrtf(first * first + second * second)','(first * first + second * second)'),
        swapped_components=b.replace('*rawA = first;','*rawA = second;'),
        missing_raw=b.replace('*rawB = second;',''),
        wrong_direction=b.replace('*directionB = second / length;','*directionB = first / length;'),
        reversed_stores=b.replace('*rawA = first;\n    *rawB = second;','*rawB = second;\n    *rawA = first;'),
        use_unused=b.replace('    length *= D_800A2D9C;','    *unusedOutput = 0.0f;\n    length *= D_800A2D9C;'),
        wrong_helper=b.replace('func_1510E388(indirectVertices, packedVertices','func_1510E388(packedVertices, indirectVertices'))


def native_harness():
    text=source.HEADERS+'#include "structs.h"\n'+source.DECLARATIONS+'''
f32 D_800A2D9C;
static f32 area[32],expected[32],firstValue,secondValue;
static u8 vertices[64],packed[64];
static u32 error,seen,mode;
typedef char ABI[(sizeof(void*)==4&&sizeof(f32)==4&&sizeof(u32)==4&&
 __builtin_offsetof(struct127,pad188)==0x188&&__builtin_offsetof(struct127,unk18C)==0x18C)?1:-1];
static f32 real(u32 v){f32 f;__builtin_memcpy(&f,&v,4);return f;}
static u32 word(f32 f){u32 v;__builtin_memcpy(&v,&f,4);return v;}
f32 sqrtf(f32 value){f32 out;__asm__("sqrtss %1,%0":"=x"(out):"x"(value));return out;}
s32 func_1510E388(void*a,void*b,f32*x,f32*y){
 if(a!=vertices||b!=packed||seen++)error=1;*x=firstValue;*y=secondValue;
 if(mode)D_800A2D9C=real(0x3D4CCCCD);return mode?0:1;
}
'''
    for name,body in dict(selected=source.SELECTED,**controls()).items():
        if name!='selected'and body==source.SELECTED:raise ValueError('Ineffective plane-component control: '+name)
        text+=body.replace(source.FUNCTION,name)+'\n'
    text+=source.LEAF_SELECTED+'\n'+'''
typedef void(*Update)(void*,void*,f32*,f32*,f32*,f32*,f32*);
static const u32 values[]={0,0x80000000u,0x3F800000u,0xBF800000u,0x40400000u,0x40800000u,0xC0E00000u,0x2EDBE6FFu,0x501502F9u};
static int variant(Update fn){u32 i,j,a,m,k;f32 *p[5],*q[5],factor;volatile f32 aa,bb,sum,length;
 for(i=0;i<9;i++)for(j=0;j<9;j++)for(a=0;a<8;a++)for(m=0;m<2;m++){
  for(k=0;k<32;k++)area[k]=expected[k]=real(0x3E800000u+k*113u);
  for(k=0;k<5;k++){p[k]=area+k;q[k]=expected+k;}
  if(a==1){p[1]=p[0];q[1]=q[0];}
  if(a==2){p[3]=p[0];p[4]=p[1];q[3]=q[0];q[4]=q[1];}
  if(a==3){p[3]=p[1];p[4]=p[0];q[3]=q[1];q[4]=q[0];}
  if(a==4){p[4]=p[3];q[4]=q[3];}
  if(a==5){p[3]=p[2];q[3]=q[2];}
  if(a==6){p[3]=&D_800A2D9C;q[3]=&factor;}
  if(a==7){p[4]=&D_800A2D9C;q[4]=&factor;}
  firstValue=real(values[i]);secondValue=real(values[j]);mode=m;error=seen=0;
  factor=real(m?0x3D4CCCCD:0x3CA3D70A);D_800A2D9C=real(0x3CA3D70A);
  aa=firstValue*firstValue;bb=secondValue*secondValue;sum=aa+bb;length=sqrtf(sum);
  *q[3]=firstValue;*q[4]=secondValue;
  if(a==6)factor=firstValue;if(a==7)factor=secondValue;
  length=length*factor;
  if(length==0.0f){*q[0]=1.0f;*q[1]=0.0f;}
  else{*q[0]=firstValue/length;*q[1]=secondValue/length;}
  fn(vertices,packed,p[0],p[1],p[2],p[3],p[4]);
  if(error||seen!=1||word(D_800A2D9C)!=word(factor))return 23;
  for(k=0;k<32;k++)if(word(area[k])!=word(expected[k]))return 23;
 }
 return 0;
}
int run(void){u32 high,low;u32 tops[]={0,0x20u,0x80000000u,0xFFFFFFE0u};
'''
    for i,name in enumerate(dict(selected=source.SELECTED,**controls())):
        text+='if(variant(%s)!=%d)return %d;\n'%(name,0 if name=='selected'else 23,i+1)
    text+='for(high=0;high<4;high++)for(low=0;low<32;low++)if(func_1510F8CC(tops[high]|low)!=low)return 70;\n'
    text+='firstValue=3.0f;secondValue=4.0f;mode=0;seen=error=0;D_800A2D9C=real(0x3CA3D70A);selected(vertices,packed,area,area+1,0,area+3,area+4);if(error||seen!=1)return 71;return 0;}\n'
    return text+START


class PlanarDirectionTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;source.verify_prepared(cls.out);cls.values=source.snapshot(cls.out)
        rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>43I',rom,source.ROM));cls.leaf=list(struct.unpack_from('>3I',rom,source.ROM+172))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER)
        cls.words=list(struct.unpack_from('>43I',data,fs[source.FUNCTION]['value']))
        cls.leaf_words=list(struct.unpack_from('>3I',data,fs[source.LEAF]['value']))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
        cls.raw=list(struct.unpack_from('>43I',data,fs[source.FUNCTION]['value']))
        cls.helper=list(struct.unpack_from('>171I',rom,0x13B838))
    def compare(self,c,args=None):
        args=args or arguments(c);initial=fixture(c,args);expected=reference(initial,c,args);models=[]
        for words in(self.truth,self.words,self.raw):
            m=PlanarOracle(words,initial,c,args).run()
            self.assertEqual(public(m.memory,args,c),public(expected,args,c),c)
            self.assertEqual(m.calls,[(source.HELPER,(*args[:2],STACK+c.phase-4,STACK+c.phase-8))]);models.append(m)
        self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));return models[0]
    def test_01_literal_owner_inventory_and_actual_Make(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.leaf_words,self.leaf)
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['body_words'],q['leaf_words'],q['new_guards'],q['preserved_neighbors']),(43,3,1,12))
        self.assertEqual(q['Make']['commands'],5);self.assertTrue(q['Make']['complete_padded_object_equal'])
        self.assertEqual(source.payload(self.out/'selected.o',source.LEAF)[1],{})
        oldlayout=self.values['conker/retail_layout.us.txt'];oldfallback=self.values['conker/undefined_funcs_auto.txt']
        self.assertEqual((self.out/'qualified-layout.txt').read_bytes(),source.recovered_layout(oldlayout))
        self.assertEqual((self.out/'qualified-undefined-functions.txt').read_bytes(),source.recovered_undefined(oldfallback))
        self.assertNotIn(b'func_1510F8CC =',(self.out/'qualified-undefined-functions.txt').read_bytes())
        direct=[];literals=[];rom=self.values['conker/conker.us.bin'];call=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
        for at in range(0,len(rom)-3,4):
            word=struct.unpack_from('>I',rom,at)[0]
            if word==call:direct.append(at+0x14FD2B50)
            if word==source.ENTRY:literals.append(at)
        self.assertEqual(tuple(direct),CALLS);self.assertFalse(literals)
        self.receipt['owner']=dict(normalizer_words=43,accessor_words=3,frame=40,guards=1,bindings=3,neighbors=12,GLOBAL_ASM=1,actual_Make_commands=5,direct_sites=direct,inventory_added_only=source.LEAF)
    def test_02_guest_float_aliases_and_live_outputs(self):
        count=0;visits=set()
        for first,second,alias,phase,mode in itertools.product(VALUES,VALUES,range(11),(0,8),(0,1)):
            c=Case(first,second,alias,phase,mode);m=self.compare(c);visits.update(m.visits);count+=1
        for alias in(11,12,13):
            for phase in(0,8):self.compare(Case(OUT,0,alias,phase));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+172,4))-{source.ENTRY+34*4})
        self.receipt['guest']=dict(cases=count,aliases=14,phases=2,signed_zero_and_small_large_components=True,live_scale_aliases=True,late_component_reload=True,unused_output_unmapped=True,raw_and_fitted_full_states_equal=True,dead_duplicate_divide_word=34)
    def test_03_low_five_bits_unsigned_word_ABI(self):
        count=0
        for high,low,phase in itertools.product((0,0x20,0x7FFFFFE0,0x80000000,0xFFFFFFE0),range(32),(0,8)):
            value=high|low;models=[]
            for words in(self.leaf,self.leaf_words):
                c=Case(phase=phase);m=PlanarOracle(words,fixture(c),c,(value,),entry=source.LEAF_ENTRY).run();self.assertEqual(m.r[2],low);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        triangles=(((0,0,0),(1,0,0),(0,0,1)),((0,0,0),(1,3,0),(0,4,1)),
            ((0,0,0),(0,1,0),(0,0,0)),((-3,-2,1),(2,7,9),(10,-6,-4)),
            ((32767,-32768,0),(-32768,32767,1),(0,0,-2)),((1,2,3),(1,2,3),(1,2,3)))
        helper_cases=0;helper_visits=set()
        for vertices,style,phase in itertools.product(triangles,('packed','indirect','NULL'),(0,8)):
            first,second=(0,0)if style=='NULL'else plane_components(vertices);c=Case(first,second,phase=phase)
            args=list(arguments(c));args[0]=INPUT if style=='indirect'else 0;args[1]=INPUT+0x40 if style=='packed'else 0;args=tuple(args)
            memory=fixture(c,args)
            for i,vertex in enumerate(vertices):
                put(memory,INPUT+4*i,INPUT+0x80+16*i)
                for axis,value in enumerate(vertex):
                    put(memory,INPUT+0x40+6*i+2*axis,value&65535,2);put(memory,INPUT+0x80+16*i+2*axis,value&65535,2)
            pair=[]
            for words in(self.truth,self.words):
                connected={source.HELPER+4*i:w for i,w in enumerate(self.helper)}
                m=PlanarOracle(words,memory,c,args,connected=connected).run();helper_visits.update(m.visits)
                self.assertEqual(public(m.memory,args,c),public(reference(memory,c,args),args,c));pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));helper_cases+=1
        self.receipt['leaf']=dict(cases=count,all_low_bits=True,high_and_sign_bits_ignored=True,no_guards=True,no_memory_or_calls=True,
            original_triangle_helper_cases=helper_cases,original_helper_words_visited=len(set(range(source.HELPER,source.HELPER+684,4))&helper_visits),
            helper_C_stub_unchanged=True,full_provider_acceptance=False)

    def test_04_all_five_original_call_windows(self):
        count=entered=0;rom=self.values['conker/conker.us.bin']
        for index,(entry,end,skip,offsets)in enumerate(WINDOWS):
            words=list(struct.unpack_from('>%dI'%((end-entry)//4),rom,entry-0x14FD2B50))
            for gate,phase,mode in itertools.product((False,True),(0,8),(0,1)):
                c=Case(phase=phase,mode=mode);sp=STACK+phase
                args=(0 if index==4 else INPUT,ACTOR+0x18C,*(sp+x for x in offsets))
                initial=fixture(c,args);put(initial,ACTOR+0x188,INPUT);put(initial,ACTOR+0x31C,RECORD)
                put(initial,ACTOR+0x28,bits(0.0));initial[ACTOR+4]=0x28 if gate else 0x77
                initial[RECORD+0x4E]=2 if gate else 1;initial[RECORD+0x4F]=0 if gate else 1
                put(initial,ACTOR+0xF8,0x100000 if gate else 0);put(initial,sp+0x38,ACTOR+0x18C)
                for address in range(0x800992D8,0x800992F0,4):put(initial,address,struct.unpack_from('>I',rom,address-0x7FE5B540)[0])
                pair=[]
                for target in(self.truth,self.words):
                    connected={source.ENTRY+4*i:w for i,w in enumerate(target)}
                    m=PlanarOracle(words,initial,c,args,entry,connected,(end,skip));m.r[16]=ACTOR;m.r[3]=RECORD;m.f[0]=bits(1.0 if gate else 40.0);m.f[4]=0;m.f[12]=0
                    with self.assertRaises(Boundary):m.run()
                    if m.target_calls:
                        self.assertEqual(m.target_calls,[args]);entered+=1
                    pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].target_calls,pair[1].target_calls);count+=1
        self.assertGreater(entered,0)
        self.receipt['callers']=dict(cases=count,actual_sites=5,entered_calls=entered,original_windows_only=True,all_seven_arguments=True,local_gate_paths=True,caller_owners_unchanged=True,whole_parent_acceptance=False)
    def test_05_native32_SDK_C_and_effective_negatives(self):
        text=native_harness()
        for opt in('-O0','-O2','-O3'):
            path=self.out/('native-'+opt[1:]+'.c');path.write_text(text);binary=path.with_suffix('')
            p=subprocess.run(native_command(opt)+['-mstackrealign',str(path),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=120).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],cases_per_profile=9*9*8*2,leaf_cases_per_profile=128,negative_controls=len(controls()),trap_UBSan=True,SDK_layout=True,typed_seven_argument_interface=True,NULL_unused_output=True,bounded_helper_provider=True)
    def test_06_fired_access_prefixes_and_unused_output(self):
        count=0
        for c in(Case(),Case(0,0),Case(alias=2),Case(alias=5),Case(alias=6),Case(alias=7),Case(alias=10),Case(OUT,0,11)):
            m=self.compare(c);initial=fixture(c)
            for at in range(m.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=PlanarOracle(words,initial,c);x.root_fault=at
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,at);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        self.compare(Case(alias=9))
        self.receipt['faults']=dict(prefix_pairs=count,emitted_guest_access_order=True,unused_argument_needs_no_mapping=True,portable_C_fault_semantics_claimed=False)
    def test_07_raw_guard_controls_and_GNU_rebases(self):
        raw,bindings=source.payload(self.out/'selected.o',source.FUNCTION)
        for i in range(43):
            bad=bytearray(raw);bad[i*4+3]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),bindings)
        with self.assertRaises(ValueError):source.normalized(raw,{})
        with self.assertRaises(ValueError):source.normalized(raw[:-4],bindings)
        with self.assertRaises(ValueError):source.guard_bytes(self.values['conker/retail_word_patches.us.csv']+b'\n',raw,bindings)
        leaf,leaf_rs=source.payload(self.out/'selected.o',source.LEAF)
        for i in range(3):
            bad=bytearray(leaf);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.checked_leaf(bytes(bad),leaf_rs)
        with self.assertRaises(ValueError):source.checked_leaf(leaf,{0:[('R_MIPS_26','bad')]})
        import csv,io
        guard=(self.out/'qualified-guards.csv').read_text();rows=list(csv.DictReader(io.StringIO(guard)));rows[-1]['expected']='0x%08X'%(int(rows[-1]['expected'],16)^1)
        bad=self.out/'negative-real-padder.csv'
        with bad.open('w',newline='')as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[-1]));writer.writeheader();writer.writerows(rows)
        with self.assertRaises((ValueError,RuntimeError)):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=bad,filename=source.OWNER)
        fitted,rs=source.normalized(raw,bindings);asm,missing=emit_function(fitted,dict(value=0,size=172),rs,source.FUNCTION,dict(func_1510E388=source.HELPER,D_800A2D9C=source.SCALE))
        self.assertFalse(missing);path=self.out/'independent-fitted.s';path.write_text(asm);obj=path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(path)],capture_output=True,check=True)
        links=0
        for index,(entry,helper,scale)in enumerate(((source.ENTRY,source.HELPER,source.SCALE),(source.ENTRY+0x200000,source.HELPER+0x300000,source.SCALE+0x7FF0),(source.ENTRY+0x500000,source.HELPER+0x700000,source.SCALE+0x17000))):
            images=[]
            for j,p in enumerate((source.original(ROOT,self.out),obj)):
                script=self.out/('rebase-%d-%d.ld'%(index,j));elf=script.with_suffix('.elf');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,'--defsym=func_1510E388=0x%X'%helper,'--defsym=D_800A2D9C=0x%X'%scale,'-o',str(elf),str(p)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>43I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(images[0],images[1])
            for c in(Case(),Case(0,0),Case(alias=2)):
                initial=fixture(c);put(initial,scale,0x3CA3D70A);models=[PlanarOracle(w,initial,c,entry=entry,scale=scale,helper=helper).run()for w in images]
                self.assertEqual(complete(models[0]),complete(models[1]))
        self.receipt['guards']=dict(raw_word_controls=43,binding_and_extent_controls=True,history_control=True,GNU_links=links,layouts=3,HI_LO_carry=True,zero_comparison_only=True,leaf_word_controls=3,leaf_binding_control=True,actual_padder_negative=True)
    def test_08_inventory_only_and_strict_complete_image(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+184]
        source.check_image(before,(self.out/'inventory-only.elf').read_bytes(),truth,True)
        source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth)
        reindex=source.linked_function_audit(self.out/'before-conker_build_conker.us.elf',self.out/'first-linked.elf')
        self.assertEqual((reindex['before_disassembly_functions'],reindex['after_disassembly_functions'],reindex['other_bodies_fixed']),(6055,6056,6054))
        expected=source.predicted_image(before,truth)
        leaf=next(off for off,n,f,_ in source.symbol_rows(before)if n==source.LEAF)
        target=next(off for off,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)
        for at in(0,len(expected)-1,source.elf_slot_offset(before,source.ENTRY,184),source.elf_slot_offset(before,source.LEAF_ENTRY,12),leaf+14,target+8,before.index(b'D_800A2D9C\0')):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        source.check_inputs(ROOT,self.out,(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE])
        self.receipt['strict']=dict(changed_bytes=150,code_bytes=127,metadata_bytes=23,exclusions=0,inventory_only_delta=2,corruptions=7,denominator=5506,leaf_separate=True)


if __name__=='__main__':unittest.main()
