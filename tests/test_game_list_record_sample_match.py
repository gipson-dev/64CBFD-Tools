"""RGBA16 sampling, bounded IEEE values, late global loads and scheduler ABI."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,math,struct,subprocess,unittest
from unittest.mock import patch

from tools.experiments import game_list_record_sample_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests import game_frame_driver_oracle as driver
from tools.tests import test_game_list_record_constructor_match as constructor
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

ROOT=Path(__file__).resolve().parents[2]
HEAD,WIDTH,HEIGHT,BUFFER=0x800DDD64,0x800BE620,0x800BE624,0x800BE9C4
IMAGE=0x70000
NODES=(0x30000,0x30100,0x30200)
VALUES=(0,0x80000000,1,0x80000001,0x00800000,0x80800000,bits(-0.25),bits(0.25),
    bits(1.75),bits(7.999),bits(8.0),bits(15.75),bits(239.75),bits(240.0),
    bits(319.75),bits(320.0),0x4EFFFFFF,0x4F000000,0x7F7FFFFF,0x7F800000,
    0xFF800000,0x7FC12345,0x7FA12345,0xFFC12345)
POINTS=tuple((v,bits(0.25))for v in VALUES)+tuple((bits(0.25),v)for v in VALUES)+(
    (bits(319.75),bits(239.75)),(bits(7.999),bits(7.999)))
DIMS=((8,8),(3,8),(8,3),(0,8),(8,0),(-1,8),(8,-1),(-0x80000000,8),
    (0x7FFFFFFF,8),(320,240),(292,216))
ALIASES=('head','width','height','buffer','sample-record','pending')
IMAGE_CAP=131072


@dataclass(frozen=True)
class Case:
    count:int=1
    point:tuple=(bits(0.25),bits(0.25))
    width:int=8
    height:int=8
    alias:str='disjoint'


def node_addresses(c):
    first={'head':HEAD-0x28,'width':WIDTH-0x28,'height':HEIGHT-0x28,
        'buffer':BUFFER-0x28,'pending':driver.PENDING-0x28}.get(c.alias,NODES[0])
    return(first,*NODES[1:])[:c.count]


def coordinates(c,i):
    if c.alias=='width':return(bits((0.0,4.5,1.5)[i]),0)
    if c.alias in ALIASES:return(bits(float(i)),0)
    return(c.point,(c.point[1],c.point[0]),(bits(1.75),bits(2.5)))[i]


def selected_index(point,width,height):
    x,y=map(floating,point)
    if x>=0.0 and x<floating(bits(float(width)))and y>=0.0 and y<floating(bits(float(height))):
        return(math.trunc(x)+math.trunc(y)*width)&0xFFFFFFFF
    return None


def fixture(c=Case(),phase=0,initial=None):
    memory=dict(initial or {})
    for i in range(-0x800,0x200):memory.setdefault(STACK+phase+i,(i*17+0xA5)&255)
    nodes=node_addresses(c)
    for base in nodes:memory.update({base+i:(i*13+0x5A)&255 for i in range(-16,0x44)})
    for offset in range(0,0x600,2):put(memory,IMAGE+offset,(offset//2*73+0x1234)&65535,2)
    for i,base in enumerate(nodes):
        x,y=coordinates(c,i);put(memory,base+0xC,x);put(memory,base+0x10,y)
        put(memory,base+0x24,nodes[i+1]if i+1<len(nodes)else 0)
        put(memory,base+0x2A,0xA55A,2)
    width=NODES[1]if c.alias=='height'else c.width
    height=2 if c.alias=='height'else c.height
    image=nodes[0]+0xC if c.alias=='sample-record'else IMAGE
    put(memory,HEAD,nodes[0]if nodes else 0);put(memory,WIDTH,width);put(memory,HEIGHT,height)
    put(memory,BUFFER,image)
    special={'width':3,'height':0,'buffer':0x100,'pending':1}
    if c.alias in special:put(memory,IMAGE,special[c.alias],2)
    for i in range(c.count):
        index=selected_index(coordinates(c,i),width,height)
        if index is not None:
            at=(image+2*index)&0xFFFFFFFF
            if not all(at+j in memory for j in range(2)):put(memory,at,(index*73+0x1234)&65535,2)
    return memory


def reference(initial):
    memory=dict(initial);node=read(memory,HEAD)
    while node:
        x=floating(read(memory,node+0xC))
        if x>=0.0:
            width=signed(read(memory,WIDTH))
            if x<floating(bits(float(width))):
                y=floating(read(memory,node+0x10))
                if y>=0.0 and y<floating(bits(float(signed(read(memory,HEIGHT))))):
                    index=(math.trunc(x)+math.trunc(y)*width)&0xFFFFFFFF
                    address=(read(memory,BUFFER)+2*index)&0xFFFFFFFF
                    put(memory,node+0x2A,read(memory,address,2),2)
        node=read(memory,node+0x24)
    return memory


def public(memory):
    return{address:value for address,value in memory.items()if not STACK-0x800<=address<STACK+0x200}


def corpus():
    for count,point,(width,height),phase in itertools.product((1,3),POINTS,DIMS,(0,8)):
        yield Case(count,point,width,height),phase
    for phase in(0,8):
        yield Case(0),phase
        for alias in ALIASES:yield Case(3,alias=alias),phase
        for width,height,point in((65536,65537,(bits(1.25),bits(65536.75))),
                (0x7FFFFFFF,8,(bits(3.5),bits(2.5))),
                (65537,65538,(bits(1.25),bits(65536.25))),
                (0x7FFFFFFF,8,(0x4EFFFFFF,0))):
            yield Case(1,point,width,height),phase


class SampleOracle(RayOracle):
    def __init__(self,words,memory,phase=0,entry=source.ENTRY,connected=None):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,connected=connected)
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,True
    def access(self):
        if self.own_instruction:
            if self.root_accesses==self.root_fault:raise faults.AccessBoundary
            self.root_accesses+=1
    def put(self,address,value,size):
        if self.recording and self.own_instruction:
            self.access()
            assert all(address+i in self.memory for i in range(size)),('unmapped write',address,size)
            own=self.own_instruction;self.own_instruction=False
            try:return super().put(address,value,size)
            finally:self.own_instruction=own
        return super().put(address,value,size)
    def record_call(self,target):raise AssertionError(('unexpected sample call',hex(target)))
    def hook(self,target):raise AssertionError(('unexpected sample provider',hex(target)))


class SchedulerOracle(SampleOracle):
    def __init__(self,words,memory,phase=0,connected=None):
        super().__init__(words,memory,phase,source.PARENT,connected)
        self.phase=phase;self.driver_counts={};self.observations=[];self.child_stack=[]
    def record_call(self,target):
        assert target in(driver.RECV,source.ENTRY,0x151412BC,0x10004074),hex(target)
        count=0 if target==source.ENTRY else driver.SIGNATURES[target][2]
        args=self.arguments(count);self.calls.append((target,args));self.events.append(('CALL',target,args))
        self.observations.append((target,driver.snapshot(self.memory)))
        self.driver_counts[target]=self.driver_counts.get(target,0)+1
        if target==source.ENTRY:
            assert args==()and self.r[31]==0x15018810
            assert self.r[29]==STACK+self.phase-104
            self.child_stack.append(self.r[29])
    def hook(self,target):
        assert target!=source.ENTRY,'The sampler must execute its actual connected body'
        args=self.calls[-1][1]
        if target==driver.RECV:
            assert args==(driver.QUEUE,STACK+self.phase-4,1)
            assert self.get(args[1],4)==0
            self.put(args[1],driver.MESSAGE,4)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in(1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678
        self.r[2]=driver.returned(target,args,self.driver_counts[target],0,0)


def controls():
    body=source.SELECTED
    assignment='            node->sample2A = ((u16 *)D_800BE9C4)[(s32)node->valueC + (s32)node->value10 * D_800BE620];\n'
    return dict(upper_inclusive=body.replace(' < D_800BE620',' <= D_800BE620').replace(' < D_800BE624',' <= D_800BE624'),
        wrong_stride=body.replace('* D_800BE620','* D_800BE624'),
        wrong_offset=body.replace('node->sample2A =','node->state28 ='),
        missing_store=body.replace(assignment,''),
        clear_skipped=body.replace('        }\n        node =','        } else {\n            node->sample2A = 0;\n        }\n        node ='),
        rounded_coordinates=body.replace('(s32)node->valueC','(s32)(node->valueC + 0.5f)').replace('(s32)node->value10','(s32)(node->value10 + 0.5f)'),
        first_only=body.replace('node = node->next;','node = NULL;'))


def native_cases():
    seen=set();rows=[]
    for c,_ in corpus():
        if c.alias!='disjoint'or c.width>320 or c.height>240:continue
        if c in seen:continue
        expected=[]
        for i in range(c.count):
            index=selected_index(coordinates(c,i),c.width,c.height)
            if index is not None and index>=IMAGE_CAP:break
            expected.append(0xA55A if index is None else(index*73+0x1234)&65535)
        else:
            seen.add(c);rows.append((c,expected))
    return rows


def native_harness():
    rows=[]
    for c,expected in native_cases():
        points=[v for i in range(3)for v in coordinates(c,i)]
        rows.append('{%d,%d,%d,{%s},{%s}}'%(c.count,c.width,c.height,
            ','.join('0x%Xu'%v for v in points),','.join(map(str,expected+[0xA55A]*(3-len(expected))))))
    text=source.HEADERS+source.DECLARATIONS+'''
ListRecord1AB530 *D_800DDD64;
s32 D_800BE620,D_800BE624,D_800BE9C4;
typedef char ABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(ListRecord1AB530)==0x34&&
 __builtin_offsetof(ListRecord1AB530,valueC)==0xC&&__builtin_offsetof(ListRecord1AB530,value10)==0x10&&
 __builtin_offsetof(ListRecord1AB530,next)==0x24&&__builtin_offsetof(ListRecord1AB530,sample2A)==0x2A&&
 __builtin_offsetof(ListRecord1AB530,flags2E)==0x2E)?1:-1];
typedef void (*Sampler)(void);
typedef struct {s32 count,width,height;u32 point[6];u16 expected[3];} Case;
static const Case cases[]={
'''+',\n'.join(rows)+'''};
static u8 *arena,*expected;
static f32 real(u32 bits){union{u32 bits;f32 value;}v;v.bits=bits;return v.value;}
'''
    for name,body in dict(selected=source.SELECTED,**controls()).items():text+=body.replace(source.FUNCTION,name)+'\n'
    text+='''static int one(Sampler fn,const Case *c){u32 i,n;u16 *image=(u16*)(void*)(arena+0x2000);
 ListRecord1AB530 *p;
 for(i=0;i<0x1000;i++)arena[i]=(u8)(i*13+0x5A);
 for(i=0;i<131072;i++)image[i]=(u16)(i*73+0x1234);
 for(n=0;n<3;n++){p=(ListRecord1AB530*)(void*)(arena+0x100+n*0x80);
  p->valueC=real(c->point[n*2]);p->value10=real(c->point[n*2+1]);p->sample2A=0xA55A;
  p->next=n+1<(u32)c->count?(ListRecord1AB530*)(void*)(arena+0x100+(n+1)*0x80):0;}
 for(i=0;i<0x1000;i++)expected[i]=arena[i];
 for(n=0;n<(u32)c->count;n++)*(u16*)(void*)(expected+0x100+n*0x80+0x2A)=c->expected[n];
 D_800DDD64=c->count?(ListRecord1AB530*)(void*)(arena+0x100):0;
 D_800BE620=c->width;D_800BE624=c->height;D_800BE9C4=(s32)(u32)image;
 fn();
 if(D_800DDD64!=(c->count?(ListRecord1AB530*)(void*)(arena+0x100):0)||
  D_800BE620!=c->width||D_800BE624!=c->height||(u32)D_800BE9C4!=(u32)image)return 23;
 for(i=0;i<0x1000;i++)if(arena[i]!=expected[i])return 23;
 for(i=0;i<131072;i++)if(image[i]!=(u16)(i*73+0x1234))return 23;
 return 0;}
static int variant(Sampler fn){u32 i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++)
 if(one(fn,&cases[i]))return 23;return 0;}
static void *allocate(u32 n){u32 p,end;
 __asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");end=p+n;
 __asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;}
static int run(void){arena=allocate(0x43000);if(!arena)return 97;expected=arena+0x1000;
 if(variant(selected))return 10;
'''
    for i,name in enumerate(controls()):text+=' if(variant(%s)!=23)return %d;\n'%(name,20+i)
    return text+' return 0;\n}\n'+START


class ListRecordSampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.receipt={}
        proof=json.loads((cls.out/'qualification-producer.json').read_text())
        if proof['experiment_SHA256']!=source.digest(Path(source.__file__).read_bytes()):
            raise ValueError('Sample qualification producer differs from the loaded module')
        cls.truth=list(struct.unpack('>56I',cls.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE]))
        source.checked_payload(*source.payload(cls.out/'after-owner.o',source.FUNCTION))
        linked=(cls.out/'first-linked.elf').read_bytes()
        cls.words=list(struct.unpack_from('>56I',linked,source.elf_slot_offset(linked,source.ENTRY,source.SIZE)))
        cls.parent=list(struct.unpack_from('>412I',cls.values['conker/conker.us.bin'],source.PARENT_ROM))
        cls.typed_parent=list(struct.unpack_from('>412I',linked,source.elf_slot_offset(linked,source.PARENT,1648)))
        cls.addClassCleanup(lambda:(cls.out/'focused-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n'))

    def compare(self,c=Case(),phase=0,initial=None,images=None):
        initial=fixture(c,phase)if initial is None else initial
        expected=reference(initial);pair=[]
        for words in(images or(self.truth,self.words)):
            m=SampleOracle(words,initial,phase).run();self.assertEqual(m.memory,expected)
            self.assertEqual(m.calls,[]);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));return pair[0]

    def test_01_complete_owner_actual_Make_and_canonical_caller(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.parent,self.typed_parent)
        rom=self.values['conker/conker.us.bin'];jal=0x0C000000|((source.ENTRY>>2)&0x03FFFFFF)
        calls=[];pointers=[]
        for i,(word,)in enumerate(struct.iter_unpack('>I',rom[:len(rom)//4*4])):
            if word==jal:calls.append(i*4)
            if word==source.ENTRY:pointers.append(i*4)
        self.assertEqual(calls,[0x45CB8]);self.assertEqual(pointers,[])
        q=json.loads((self.out/'qualification.json').read_text());make=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual((q['new_guards'],q['preserved_global_asm'],q['preserved_neighbors']),(0,1,7))
        self.assertEqual(q['typed_caller_compact_functions_unchanged'],16)
        self.assertTrue(make['target']['complete_padded_object_equal'])
        self.assertTrue(make['caller']['complete_caller_object_unchanged'])
        self.assertIn(b'extern s32  D_800BE9C4;',self.values['conker/include/variables.h'])
        self.receipt['shape']=dict(q,encoded_JAL_sites=calls,literal_pointer_sites=pointers,
            actual_Make=make,canonical_void_function_pointer=True)

    def test_02_guest_float_bounds_lazy_access_aliases_and_fault_prefixes(self):
        count=0;seen=set()
        for c,phase in corpus():
            m=self.compare(c,phase);seen.update(m.visits);count+=1
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+source.SIZE,4)))
        lazy=0
        for c,missing,omit_y in((Case(0),(WIDTH,HEIGHT,BUFFER),False),
                (Case(point=(bits(-0.25),0)),(WIDTH,HEIGHT,BUFFER),True),
                (Case(point=(bits(8.0),0)),(HEIGHT,BUFFER),True),
                (Case(point=(0,bits(-0.25))),(HEIGHT,BUFFER),False),
                (Case(point=(0,bits(8.0))),(BUFFER,),False),
                (Case(point=(0x7FA12345,0)),(WIDTH,HEIGHT,BUFFER),True)):
            initial=fixture(c)
            for address in missing:
                for i in range(4):initial.pop(address+i,None)
            for address in list(initial):
                if IMAGE<=address<IMAGE+0x600:del initial[address]
            if omit_y:
                for i in range(4):initial.pop(NODES[0]+0x10+i,None)
            self.compare(c,initial=initial);lazy+=1
        prefixes=0
        for c in(Case(),Case(0),Case(3),Case(3,alias='width'),Case(3,alias='buffer'),
                Case(3,alias='head'),Case(point=(0x7FC12345,0))):
            initial=fixture(c);m=self.compare(c)
            for fault in range(m.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=SampleOracle(words,initial);x.root_fault=fault
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,fault);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));prefixes+=1
        self.receipt['guest']=dict(cases=count,reachable_words=56,lazy_unmapped_cases=lazy,
            fault_prefix_pairs=prefixes,global_and_record_aliases=list(ALIASES),
            signed_bounds_and_low_word_index_wrap=True,NaN_infinity_signed_zero_subnormal_values=True,
            bounded_IEEE_single_values=True,full_FCSR_exception_emulation_claimed=False,
            guest_fault_order_only=True,acyclic_list_contract=True)

    def test_03_compiled_guest_controls_detect_late_global_loads(self):
        body=source.SELECTED;anchor='    ListRecord1AB530 *node = D_800DDD64;'
        cached=body.replace(anchor,anchor+'\n    s32 width = D_800BE620;\n    s32 height = D_800BE624;')
        cached=cached.replace('node->valueC < D_800BE620','node->valueC < width')
        cached=cached.replace('node->value10 < D_800BE624','node->value10 < height').replace('* D_800BE620','* width')
        image=body.replace(anchor,anchor+'\n    u16 *image = (u16 *)D_800BE9C4;')
        image=image.replace('((u16 *)D_800BE9C4)[','image[')
        results=[]
        for name,text,c in(('cached_bounds',cached,Case(3,alias='width')),
                ('cached_image',image,Case(3,alias='buffer'))):
            self.assertNotEqual(text,body)
            obj,diag=source.compile_owner(ROOT,self.out,source.HEADERS+source.DECLARATIONS+text,'negative-'+name)
            self.assertFalse(diag);linked,fs=source.link_owner(ROOT,self.out,obj,source.OWNER)
            info=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(info['size']//4),linked,info['value']))
            initial=fixture(c);actual=SampleOracle(words,initial).run()
            self.assertNotEqual(actual.memory,reference(initial));results.append(name)
        self.receipt['compiled_guest_controls']=results

    def test_04_actual_scheduler_message2_and_skip_paths_connected(self):
        count=0;original_effects=driver.effects
        def effects(memory,target,args,ordinal,mode):
            if target==source.ENTRY:
                expected=reference(memory);memory.clear();memory.update(expected);return False
            return original_effects(memory,target,args,ordinal,mode)
        for message,stop,pending,counter,phase,c in itertools.product((2,),
                (0,1),(0,1),(0,1,65535),(0,8),(Case(0),Case(3),Case(3,alias='pending'))):
            initial=fixture(c,phase,driver.fixture(message,stop=stop))
            initial[driver.STOP]=stop;put(initial,driver.PENDING,pending)
            put(initial,0x800BEAA8,counter,2)
            with patch.object(driver,'effects',side_effect=effects):expected=driver.reference(initial,phase=phase)
            pair=[]
            for parent,child in((self.parent,self.truth),(self.typed_parent,self.words)):
                connected={source.ENTRY+i*4:w for i,w in enumerate(child)}
                x=SchedulerOracle(parent,initial,phase,connected).run()
                self.assertEqual(public(x.memory),public(expected[0]))
                self.assertEqual(x.calls,expected[1]);self.assertEqual(x.observations,expected[2])
                self.assertEqual(x.r[2],expected[5]);self.assertEqual(x.child_stack,[STACK+phase-104]);pair.append(x)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        for message,phase in itertools.product((0,1,3,65535),(0,8)):
            initial=fixture(Case(0),phase,driver.fixture(message,stop=1));initial[driver.STOP]=1
            pair=[SchedulerOracle(parent,initial,phase,{source.ENTRY+i*4:w for i,w in enumerate(child)}).run()
                for parent,child in((self.parent,self.truth),(self.typed_parent,self.words))]
            self.assertEqual(complete(pair[0]),complete(pair[1]))
            self.assertFalse(pair[0].child_stack);self.assertEqual(pair[0].calls,[(driver.RECV,(driver.QUEUE,STACK+phase-4,1))])
            count+=1
        self.receipt['caller']=dict(connected_cases=count,retained_original_words=412,frame=104,
            actual_no_argument_child=True,message2_and_nonselected_paths=True,typed_object_unchanged=True,
            sample_can_activate_pending_gate=True,OS_queue_and_followup_helpers_bounded=True,
            not_a_new_caller_match=True,complete_scheduler_hardware_acceptance_claimed=False)

    def test_05_native32_defined_domain_partial_store_and_effective_controls(self):
        profiles=[];neighbors=[];folder=self.out/'native';folder.mkdir(exist_ok=True)
        original=self.values[source.SOURCE].decode();recovered=source.recovered_owner(original)
        self.assertEqual(original.count(source.records.SELECTED),1)
        self.assertEqual(recovered.count(source.records.SELECTED),1)
        old=source.records.DECLARATIONS.replace('extern ListRecord1AB530 *D_800DDD64;','ListRecord1AB530 *D_800DDD64;')
        new=source.DECLARATIONS.replace('extern ListRecord1AB530 *D_800DDD64;','ListRecord1AB530 *D_800DDD64;')
        neighbor=constructor.native_harness(self.values);self.assertEqual(neighbor.count(old),1)
        neighbor=neighbor.replace(old,new,1)
        for opt in('-O0','-O2','-O3'):
            path=folder/('sampler-'+opt[1:]+'.c');path.write_text(native_harness());binary=path.with_suffix('')
            result=subprocess.run(native_command(opt)+['-mstackrealign',str(path),'-o',str(binary)],
                cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            result=subprocess.run([str(binary)],cwd=ROOT,capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            profiles.append(dict(profile=opt,binary_SHA256=source.digest(binary.read_bytes()),exit=0))
            path=folder/('constructor-new-view-'+opt[1:]+'.c');path.write_text(neighbor);binary=path.with_suffix('')
            result=subprocess.run(native_command(opt)+['-mstackrealign',str(path),'-o',str(binary)],
                cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            result=subprocess.run([str(binary)],cwd=ROOT,capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            neighbors.append(dict(profile=opt,binary_SHA256=source.digest(binary.read_bytes()),exit=0))
        self.receipt['native']=dict(profiles=profiles,cases_per_profile=len(native_cases()),trap_UBSan=True,
            heap_backed_typeless=True,effective_controls=list(controls()),layout_bytes=52,sample_offset=42,
            canonical_s32_buffer_address=True,proper_void_function_pointer=True,
            complete_record_fences_and_image_immutability=True,
            native_storage_and_arithmetic_defined=True,guest_global_aliases_and_wrap_not_native_claims=True,
            constructor_new_view_profiles=neighbors,constructor_cases_per_profile=5120,
            constructor_body_identical_to_frozen_source=True)

    def test_06_raw_controls_independent_rebases_and_strict_full_image(self):
        raw,bindings=source.payload(self.out/'after-owner.o',source.FUNCTION)
        for i in range(56):
            bad=bytearray(raw);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.checked_payload(bytes(bad),bindings)
        with self.assertRaises(ValueError):source.checked_payload(raw[:-4],bindings)
        for offset in bindings:
            bad=dict(bindings);kind,_=bad[offset][0];bad[offset]=[(kind,'D_800BAD00')]
            with self.assertRaises(ValueError):source.checked_payload(raw,bad)
        layouts=((source.ENTRY,HEAD,WIDTH,HEIGHT,BUFFER),
            (source.ENTRY+0x200000,0x80127FFC,0x80128000,0x80127FF8,0x8012FFF8),
            (source.ENTRY+0x400000,0x7FFE8000,0x8021FFF0,0x80220004,0x80217FF0))
        links=0
        for i,(entry,head,width,height,buffer)in enumerate(layouts):
            images=[]
            for j,obj in enumerate((source.original(ROOT,self.out),self.out/'selected.o')):
                ld=self.out/('rebase-%d-%d.ld'%(i,j));elf=ld.with_suffix('.elf')
                ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                symbols=dict(D_800DDD64=head,D_800BE620=width,D_800BE624=height,D_800BE9C4=buffer)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,check=True)
                images.append(sections(elf)['.text'][1][:source.SIZE]);links+=1
            self.assertEqual(*images)
            initial=fixture();expected=reference(initial)
            for old,new in((HEAD,head),(WIDTH,width),(HEIGHT,height),(BUFFER,buffer)):
                a=bytes(initial.pop(old+k)for k in range(4));b=bytes(expected.pop(old+k)for k in range(4))
                initial.update({new+k:v for k,v in enumerate(a)});expected.update({new+k:v for k,v in enumerate(b)})
            for image in images:
                m=SampleOracle(list(struct.unpack('>56I',image)),initial,entry=entry).run()
                self.assertEqual(m.memory,expected)
        before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE]
        pred=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth)
        symbol=next(at for at,n,_,_ in source.symbol_rows(before)if n==source.FUNCTION)
        for at in(0,len(pred)-1,source.elf_slot_offset(pred,source.ENTRY,source.SIZE),
                source.elf_slot_offset(pred,source.ENTRY+source.SIZE-4,4),symbol+8,
                source.elf_slot_offset(pred,source.PARENT,1648)):
            bad=bytearray(pred);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        source.check_inputs(ROOT,self.out,(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE])
        self.receipt['image']=dict(raw_word_corruptions=56,extent_controls=1,binding_controls=8,GNU_links=links,
            layouts=3,all_four_global_pairs_rebased=True,rebased_execution_cases=6,
            strict_image_corruptions=6,exclusions=0,prediction=json.loads((self.out/'first-link.json').read_text()))


if __name__=='__main__':unittest.main()
