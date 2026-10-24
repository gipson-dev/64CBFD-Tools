"""Direct randomized vector payload: ABI, callback window and retained helpers."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_random_vector_payload as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.test_game_record_vertical_rate_match import RateOracle
from tools.tests.test_game_actor_mask_scan_match import MaskOracle
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEED,SEEDS
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
OWNER,VECTOR,RESULT,TABLE=0x30000,0x38000,0x40000,0x8008F970
RNG,CREATE,COPY,ALLOC,ZERO=0x150ADA20,0x15149130,0x10022EC0,0x15167A68,0x100226F0
WINDOW,END,WINDOW_ROM=0x151A8E9C,0x151A8EC4,0x1D634C
RANDOMS=(0,1,132,133,0x7FFFFFFF,0x80000000,0xFFFFFFFE,0xFFFFFFFF)
PATTERNS=(0,0x80000000,0x7F812345,0xFF800000,0x3F800000,0xA55A00FF)
SYMBOLS=dict(func_150ADA20=RNG,func_15149130=CREATE,memcpy=COPY)

@dataclass(frozen=True)
class Case:
    random:int=0xFFFFFFFF
    route:int=255
    slot:int=128
    mode:int=0
    layout:int=0
    destination:int=1
    phase:int=0
    seed:int=0

def fixture(c):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
    for base in (OWNER,VECTOR,RESULT):
        m.update({base+i:(i*13+0xA5)&255 for i in range(-64,256)})
    frame=STACK+c.phase-72
    position=(VECTOR,OWNER,frame+0x38,frame+0x34,frame+0x48,frame+0x44)[c.layout]
    for i in range(3):put(m,position+i*4,PATTERNS[(c.slot+i)%len(PATTERNS)])
    put(m,OWNER+1,c.route,1);put(m,OWNER+0xC,c.slot,1);put(m,SEED,c.seed,8)
    result=(0,RESULT,OWNER-0x28,VECTOR-0x28)[c.destination]
    return m,(OWNER,position,0x87654321,0xFEDCBA98),result

def mutate(m,args):
    put(m,OWNER+1,0xE3,1);put(m,OWNER+0xC,0xA7,1)
    for i in range(3):put(m,args[1]+i*4,0x76543210^i)

def public(m):return {a:b for a,b in m.items() if not STACK-1024<=a<STACK+1024}

def reference(initial,args,result,c,actual=False):
    m=dict(initial);frame=STACK+c.phase-72;p=frame+0x38
    for a,v in ((frame+0x2C,0xDEAD0000),(frame+0x48,args[0]),
                (frame+0x50,args[2]),(frame+0x54,args[3])):put(m,a,v)
    for i in range(3):put(m,p+i*4,read(m,args[1]+i*4))
    put(m,p+12,0)
    value=next_seed(c.seed) if actual else c.random
    if actual:put(m,SEED,value,8)
    if c.mode==1:mutate(m,args)
    duration=(value&0xFFFFFFFF)%133+69
    creation=(duration,0xFFFFFFFF,0x49,0xFFFFFFFF,1,0,16,m[OWNER+0xC],m[OWNER+1])
    allocation=(0x23,creation[-1],56,1,creation[-2],1)
    if c.mode==2:mutate(m,args)
    if result:
        for off,v,n in ((0xE,duration,2),(0x10,255,1),(0x11,0x49,1),
                (0x12,255,1),(0xD,1,1),(0x13,0,1)):put(m,result+off,v,n)
        for i in range(16):put(m,result+0x14+i,0,1)
        for i in range(16):put(m,result+0x28+i,m[p+i],1)
    return m,creation,allocation

class PayloadOracle(RateOracle,RayOracle):
    get=MaskOracle.get
    put=MaskOracle.put
    def __init__(self,words,memory,args,result,c,connected=None,entry=source.ENTRY,symbols=None):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=args,connected=connected)
        self.payload_args,self.result,self.case=args,result,c
        self.symbols=symbols or SYMBOLS;self.hi=self.lo=0
    def execute(self,w):
        if w>>26==32:return RayOracle.execute(self,w)
        return RateOracle.execute(self,w)
    def record_call(self,target):
        counts={self.symbols['func_150ADA20']:0,self.symbols['func_15149130']:9,
                self.symbols['memcpy']:3,ALLOC:6,ZERO:2,source.ENTRY:4}
        count=counts.get(target,4)
        assert target in counts or target in (0x151A91AC,0x151A9634,0x1515AA84),hex(target)
        args=self.arguments(count)
        self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==self.symbols['func_150ADA20'] and self.case.mode==1:mutate(self.memory,self.payload_args)
        if target==ALLOC and self.case.mode==2:mutate(self.memory,self.payload_args)
    def hook(self,target):
        if target==ZERO:
            address,length=self.arguments(2);assert length==16
            for i in range(length):self.put(address+i,0,1)
        elif target not in (self.symbols['func_150ADA20'],ALLOC,0x151A91AC,0x151A9634,0x1515AA84):
            raise AssertionError(('unbounded helper',hex(target)))
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=self.case.random&0xFFFFFFFF if target==self.symbols['func_150ADA20'] else self.result if target==ALLOC else 0x98765432

class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==END:raise WindowBoundary
        return super().__getitem__(pc)

def controls():
    b=source.SELECTED[source.FUNCTION]
    return dict(signed_mod=b.replace('% 133U + 69U','% 133 + 69'),
        wrong_mod=b.replace('133U','132U'),wrong_base=b.replace('69U','68U'),
        wrong_kind=b.replace('0x49','0x48'),wrong_sentinel=b.replace('-1, 0x49, -1','-1, 0x49, 0'),
        wrong_route=b.replace('owner[1]','owner[2]'),
        short_copy=b.replace('sizeof(payload)','12'),
        wrong_destination=b.replace('record + 0x28','record + 0x24'),
        negative_zero=b.replace('0.0f','-0.0f'),
        late_vector=b.replace('    payload.position = *position;\n','').replace('    if (record != NULL)', '    payload.position = *position;\n    if (record != NULL)'))

class RandomVectorPayloadTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.root=ROOT;cls.out=ROOT/source.BUILD
        cls.values=source.snapshot(cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.before=cls.values['conker/build/conker.us.elf']
        cls.retail=list(struct.unpack_from('>44I',cls.rom,source.ROM))
        cls.raw=list(struct.unpack('>44I',source.payload(cls.out/'after-owner.o',source.FUNCTION)[0]))
        # Resolve the independent compact object through the same owner linker.
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
        cls.words=list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value']))
        cls.helper={}
        for va,rom,n in ((CREATE,0x1765E0,49),(COPY,0x22EC0,11),(RNG,0xDAED0,18)):
            words=list(struct.unpack_from('>%dI'%n,cls.rom,rom))
            at=source.elf_slot_offset(cls.before,va,n*4)
            assert cls.before[at:at+n*4]==cls.rom[rom:rom+n*4]
            cls.helper[va]=words
        cls.connected={va+i*4:w for va in (CREATE,COPY) for i,w in enumerate(cls.helper[va])}
    def compare(self,c,actual=False):
        memory,args,result=fixture(c);expected,creation,allocation=reference(memory,args,result,c,actual)
        code=dict(self.connected)
        if actual:code.update({RNG+i*4:w for i,w in enumerate(self.helper[RNG])})
        models=[PayloadOracle(w,memory,args,result,c,code).run() for w in (self.retail,self.words)]
        self.assertEqual(complete(models[0]),complete(models[1]))
        for model in models:
            self.assertEqual(public(model.memory),public(expected),c)
            self.assertIn((CREATE,creation),model.calls)
            self.assertIn((ALLOC,allocation),model.calls)
            self.assertEqual(sum(t==RNG for t,_ in model.calls),1)
            self.assertEqual(sum(t==COPY for t,_ in model.calls),bool(result))
            if result:self.assertIn((ZERO,(result+0x14,16)),model.calls)
        return models[0]
    def test_01_direct_words_owner_and_actual_make(self):
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['total_words'],q['preserved_neighbors'],q['new_guards']),(44,4,0))
        self.assertEqual(self.words,self.retail)
        for path in ('after-owner.o','qualified-padded.o','original-'+source.FUNCTION+'.o'):
            self.assertEqual(source.payload(self.out/path,source.FUNCTION),
                             source.payload(self.out/'after-owner.o',source.FUNCTION))
        report=json.loads((self.out/'make-shadow.json').read_text())[0]
        self.assertEqual((report['actual_Make_commands'],report['compact_functions_equal']),(5,5))
        self.assertTrue(report['complete_padded_object_equal'])
        self.receipt['direct']=dict(words=44,frame=72,bindings=3,neighbors=4,new_guards=0,actual_Make_commands=5)
    def test_02_guest_semantics_and_aliases(self):
        count=0
        for random,layout,destination,phase in itertools.product(RANDOMS,range(6),range(4),(0,8)):
            self.compare(Case(random=random,layout=layout,destination=destination,phase=phase));count+=1
        for byte,mode,destination in itertools.product(range(256),range(3),(0,1)):
            self.compare(Case(route=byte,slot=255-byte,mode=mode,destination=destination));count+=1
        self.receipt['guest']=dict(cases=count,all_route_bytes=True,stack_aliases=True,provider_mutations=True,full_states_equal=True)
    def test_03_actual_callback_table_and_call_window(self):
        table=struct.unpack_from('>4I',self.rom,0x234430)
        self.assertEqual(table,(0x151A91AC,0x151A9634,0x1515AA84,source.ENTRY))
        literals=[i for i in range(0,len(self.rom)-3,4) if struct.unpack_from('>I',self.rom,i)[0]==source.ENTRY]
        self.assertEqual(literals,[0x23443C])
        jal=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
        self.assertNotIn(jal,struct.unpack('>%dI'%(len(self.rom)//4),self.rom))
        parent=self.values['conker/src/game/generated_1D4E00.c'].decode()
        self.assertIn('s32 func_151A8CEC() {\n    return 0;\n}',parent)
        window=list(struct.unpack_from('>10I',self.rom,WINDOW_ROM));count=0
        for selector,phase in itertools.product((-1,0,1,2,3),(0,8)):
            c=Case(phase=phase);memory,args,result=fixture(c)
            put(memory,OWNER+0x4E,selector&255,1)
            for i,entry in enumerate(table):put(memory,TABLE+i*4,entry)
            put(memory,STACK+phase+0x5C,args[2])
            for i,v in enumerate(PATTERNS[:3]):put(memory,STACK+phase+0x64+i*4,v)
            models=[]
            for words in (self.retail,self.words):
                code=dict(self.connected);code.update({source.ENTRY+i*4:w for i,w in enumerate(words)})
                callargs=(OWNER,STACK+phase+0x64,args[2],0x98)
                m=PayloadOracle(window,memory,callargs,result,c,code,entry=WINDOW)
                m.code[END]=0
                for r,v in ((16,OWNER+0x28),(19,OWNER),(17,callargs[1]),(22,TABLE),(30,0xFFFFFFFF),(18,args[3])):
                    m.r[r]=m.before[r]=v
                m.code=WindowCode(m.code,m)
                with self.assertRaises(WindowBoundary):m.run()
                callbacks=[(t,a)for t,a in m.calls if t in table]
                self.assertEqual(callbacks,[] if selector==-1 else [(table[selector],callargs)])
                models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt['caller']=dict(cases=count,table_slot=3,original_window_words=10,parent_C_still_uncredited=True)
    def test_04_native32_and_effective_controls(self):
        b=source.SELECTED[source.FUNCTION]
        fixture_c=source.HEADERS+source.DECLARATIONS+"""
static u8 ownerBytes[128],output[128],expected[128],captured[16];
static PayloadVectorDF260 inputVector;
static u32 randomWord;static int error,calls,copies,mode,failed;
static void mutation(void){int i;u8 *p=(u8 *)&inputVector;
 ownerBytes[1]=0xE3;ownerBytes[12]=0xA7;for(i=0;i<12;i++)p[i]=(u8)(i+99);}
s32 func_150ADA20(void){if(mode==1)mutation();return (s32)randomWord;}
struct260 *func_15149130(s16 duration,s8 a,s8 kind,s8 d,u8 active,u8 flags,struct37 *token,u8 slot,s32 route){
 calls++;if(duration!=(s16)(randomWord%133U+69U)||a!=-1||kind!=0x49||d!=-1||
 active!=1||flags!=0||(u32)token!=16||slot!=ownerBytes[12]||route!=ownerBytes[1])error=1;
 if(mode==2)mutation();return failed?NULL:(struct260 *)output;
}
void *memcpy(void *to,const void *from,size_t size){u32 i;copies++;
 if(to!=output+0x28||size!=16)error=2;
 for(i=0;i<size;i++)((u8 *)to)[i]=((const u8 *)from)[i];
 return to;
}
"""+b+"""
int run(void){int r,byte,i;u32 values[8]={0,1,132,133,0x7FFFFFFF,0x80000000,0xFFFFFFFE,0xFFFFFFFF};
 if(sizeof(void*)!=4||sizeof(inputVector)!=12||sizeof(RandomVectorPayloadDF260)!=16)return 9;
 for(r=0;r<8;r++)for(byte=0;byte<256;byte++)for(mode=0;mode<3;mode++)for(failed=0;failed<2;failed++){
  u8 *v=(u8 *)&inputVector;randomWord=values[r];calls=copies=error=0;
  for(i=0;i<128;i++)ownerBytes[i]=output[i]=expected[i]=0xA5;
  ownerBytes[1]=(u8)byte;ownerBytes[12]=(u8)(255-byte);
  for(i=0;i<12;i++)v[i]=captured[i]=(u8)(i*17+byte);
  for(i=12;i<16;i++)captured[i]=0;
  if(!failed)for(i=0;i<16;i++)expected[0x28+i]=captured[i];
  func_150B1EE0(ownerBytes,&inputVector,(s32)0x87654321,(s32)0xFEDCBA98);
  if(error||calls!=1||copies!=!failed)return 10;
  for(i=0;i<128;i++)if(output[i]!=expected[i])return 11;
 }return 0;
}
"""+START
        for opt in ('-O0','-O2','-O3'):
            p=self.out/('native-'+opt[1:]+'.c');p.write_text(fixture_c);binary=p.with_suffix('')
            subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=self.root,capture_output=True,check=True)
            x=subprocess.run([str(binary)],capture_output=True,timeout=20);self.assertEqual(x.returncode,0,(opt,x.stderr))
        for label,body in controls().items():
            p=self.out/('native-negative-'+label+'.c');p.write_text(fixture_c.replace(b,body));binary=p.with_suffix('')
            subprocess.run(native_command('-O2')+['-mstackrealign',str(p),'-o',str(binary)],cwd=self.root,capture_output=True,check=True)
            self.assertNotEqual(subprocess.run([str(binary)],timeout=20).returncode,0,label)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],cases_per_profile=12288,trap_UBSan=True,
            effective_controls=len(controls()),canonical_pointer_token_not_dereferenced=True,full_factory_native_C_not_claimed=True)
    def test_05_root_access_fault_prefixes(self):
        count=0
        for c in (Case(),Case(destination=0),Case(layout=3),Case(mode=2)):
            memory,args,result=fixture(c)
            complete_model=self.compare(c)
            for fault in range(complete_model.root_accesses):
                models=[]
                for words in (self.retail,self.words):
                    m=PayloadOracle(words,memory,args,result,c,self.connected);m.root_fault=fault
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,fault);models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt['faults']=dict(fired_pairs=count,emitted_guest_order_only=True)
    def test_06_independent_relocated_links(self):
        count=0
        for index,delta in enumerate((0,0x200000,0x400000)):
            linked=[];script=self.out/('rebase-'+str(index)+'.ld')
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(source.ENTRY+delta))
            for label,obj in (('original',self.out/('original-'+source.FUNCTION+'.o')),
                    ('raw',self.out/('selected-'+source.FUNCTION+'.o'))):
                elf=self.out/('rebase-%d-%s.elf'%(index,label))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%(k,v+delta)for k,v in SYMBOLS.items()],'-o',str(elf),str(obj)],capture_output=True,check=True)
                data=sections(elf)['.text'][:176];linked.append(data);count+=1
            self.assertEqual(*linked)
        self.receipt['rebases']=dict(independent_GNU_links=count,layouts=3,original_and_compact_C=True)
    def test_07_actual_rng_factory_and_copy(self):
        visits=set();count=0
        for seed,destination,phase in itertools.product(SEEDS,(0,1),(0,8)):
            m=self.compare(Case(seed=seed,destination=destination,phase=phase),actual=True)
            visits.update(m.visits);count+=1
        for va,words in self.helper.items():
            missing=set(range(va,va+len(words)*4,4))-visits
            # This caller always supplies flags=1, so the flag-2 allocator-kind arm is unreachable.
            self.assertEqual(missing,{CREATE+0x34,CREATE+0x38} if va==CREATE else set())
        self.receipt['connected']=dict(cases=count,original_RNG_words=18,original_factory_words=49,original_memcpy_words=11,
            factory_reachable_words=47,all_RNG_and_memcpy_words_visited=True,
            factory_flag2_arm_unreachable=True,allocator_and_bzero_bounded=True,low_word_unsigned_modulo=True,hardware_not_claimed=True)
    def test_08_strict_image_and_immutable_inputs(self):
        bodies=source.truths(self.values);predicted=source.predicted_image(self.before,bodies)
        source.check_image(self.before,(self.out/'first-linked.elf').read_bytes(),bodies)
        self.assertEqual(sum(a!=b for a,b in zip(self.before,predicted)),130)
        for at in (0,source.elf_slot_offset(predicted,source.ENTRY,176),
                   source.elf_slot_offset(predicted,0x150B1DB0,4),len(predicted)-1):
            wrong=bytearray(predicted);wrong[at]^=1
            with self.assertRaises(ValueError):source.check_image(self.before,bytes(wrong),bodies)
        installed=(self.root/source.SOURCE).read_text()!=self.values[source.SOURCE].decode()
        source.check_inputs(self.root,self.out,installed=installed)
        self.receipt['strict']=dict(changed_bytes=130,code_bytes=129,metadata_bytes=1,exclusions=0,controls=4,all_39_inputs_checked=True)

if __name__=='__main__':unittest.main()
