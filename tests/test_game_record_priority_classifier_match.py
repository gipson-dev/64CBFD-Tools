"""Ordered record classification: writable byte aliases, original parent and strict image."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,os,re,struct,subprocess,unittest
from tools.experiments import game_record_priority_classifier_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2];RECORD,OUTPUT,EFFECT=0x20000,0x30000,0x40000
@dataclass(frozen=True)
class Case:
    gate:int=0
    kind:int=0
    subtype:int=0
    tag:int=0
    output:int=0
    alias:int=0
    seed:int=0xA5
    phase:int=0
    allocated:bool=True
    source_null:bool=False
    flag:int=0
    size:int=24

def gate_address(c,address=source.GATE):return(address,RECORD+4,RECORD+5,RECORD+59)[c.alias]
def output_address(c,address):return(OUTPUT,RECORD+4,RECORD+5,RECORD+59,address,STACK+c.phase+4,RECORD)[c.output]
def fixture(c,address=source.GATE):
    m={STACK+c.phase+i:(i*17+c.seed)&255 for i in range(-256,256)}
    for base,size in((RECORD,64),(EFFECT,96)):m.update({base+i:(i*13+c.seed)&255 for i in range(size)})
    m[RECORD+4]=c.kind;m[RECORD+5]=c.subtype;m[RECORD+59]=c.tag;m[OUTPUT]=c.seed;m[gate_address(c,address)]=c.gate
    return m

def classify(initial,record,out,address):
    m=dict(initial);matched=0
    if m[address]:m[out]=0;matched=1
    if m[record+59]==1:m[out]=0;matched=1
    if m[record+5]in(2,5):m[out]=1;matched=1
    final={8:2,10:3,41:4,42:4}.get(m[record+4])
    if final is not None:m[out]=final;matched=1
    return m,matched

def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+256}
def parent_reference(initial,c):
    m=dict(initial);calls=[]
    if c.source_null:return public(m),calls,0
    calls.append((source.ALLOC,(46,0,(c.size+88)&0xFFFFFFFF,1,255,1)))
    if not c.allocated:return public(m),calls,0
    put(m,EFFECT+24,RECORD);m[EFFECT+28]=m[RECORD+59]
    for offset,value in((44,2),(45,2),(46,2),(47,3),(48,0),(49,int(c.flag!=0))):m[EFFECT+offset]=value
    for dst,src in((32,20),(36,24),(40,28)):put(m,EFFECT+dst,read(m,RECORD+src))
    put(m,EFFECT+16,1);put(m,EFFECT+20,0);calls.append((source.ENTRY,(RECORD,EFFECT+29)));m,result=classify(m,RECORD,EFFECT+29,source.GATE)
    if result:m[EFFECT+80]=0;returned=EFFECT
    else:calls.append((source.FREE,(EFFECT,)));put(m,EFFECT+84,0xDEAD0001);returned=0
    return public(m),calls,returned

class ClassifierOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,address=source.GATE,connected=None,arguments=None):
        address=gate_address(c,address);out=output_address(c,address)
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=arguments if arguments is not None else(RECORD,out),connected=connected);self.case,self.address,self.trace=c,address,[]
    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        n={source.ENTRY:2,source.ALLOC:6,source.FREE:1}[target];args=self.arguments(n);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        if target==source.ALLOC:result=EFFECT if self.case.allocated else 0
        else:
            assert target==source.FREE;put(self.memory,self.arguments(1)[0]+84,0xDEAD0001);result=0
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result;self.hi,self.lo=0xA5000010,0xA5000011

def controls():
    b=source.SELECTED;cached=b.replace('record[0x3B]','tag').replace('record[5]','subtype').replace('record[4]','kind');cached=cached.replace('    s32 matched = 0;','    s32 matched = 0;\n    u8 tag = record[0x3B], subtype = record[5], kind = record[4];')
    return dict(exact_gate=b.replace('D_800BE616 != 0','D_800BE616 == 1'),wrong_tag=b.replace('record[0x3B] == 1','record[0x3B] == 2'),wrong_subtype=b.replace('record[5] == 2','record[5] == 3'),wrong_type8=b.replace('case 8:','case 9:'),wrong_type10=b.replace('case 10:','case 11:'),wrong_type41_42=b.replace('case 0x29:','case 0x28:').replace('case 0x2A:','case 0x2B:'),cached_fields=cached,early_return=b.replace('matched = 1;','return 1;',1))

def native_harness():
    t=source.HEADERS+source.DECLARATIONS+r'''
u8 D_800BE616;typedef struct{u8 data[64];} Record;static Record actual,expected,blank;
static int same(const void*a_,const void*b_,u32 n){const u8*a=a_,*b=b_;u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static s32 oracle(u8*r,u8*out,u8 gate){static const u8 map[256]={[8]=2,[10]=3,[41]=4,[42]=4};s32 result=0;if(gate){*out=0;result=1;}if(r[59]==1){*out=0;result=1;}if(r[5]==2||r[5]==5){*out=1;result=1;}if(map[r[4]]){*out=map[r[4]];result=1;}return result;}
'''
    for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('s32 '+source.FUNCTION,'static s32 '+name)+'\n'
    t+=r'''
typedef s32(*Classifier)(u8*,u8*);
static int check(Classifier fn){u32 i,kind,subtype,gate,tag,layout;u8 outside,expectedOutside,expectedGate,*a,*b;s32 want,got;
 for(i=0;i<64;i++)blank.data[i]=(u8)(i*13+0xA5);
 for(kind=0;kind<256;kind++)for(subtype=0;subtype<256;subtype++)for(gate=0;gate<2;gate++)for(tag=0;tag<2;tag++)for(layout=0;layout<6;layout++){
  actual=blank;actual.data[4]=(u8)kind;actual.data[5]=(u8)subtype;actual.data[59]=(u8)tag;expected=actual;outside=expectedOutside=0xA5;D_800BE616=expectedGate=gate?255:0;
  a=&outside;b=&expectedOutside;
  if(layout>=1&&layout<=3){u32 at=layout==1?4:layout==2?5:59;a=actual.data+at;b=expected.data+at;}
  else if(layout==4){a=&D_800BE616;b=&expectedGate;}else if(layout==5){a=actual.data;b=expected.data;}
  want=oracle(expected.data,b,expectedGate);got=fn(actual.data,a);
  if(want!=got||outside!=expectedOutside||D_800BE616!=expectedGate||!same(&actual,&expected,64))return 1;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
    for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START

class RecordPriorityClassifierTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>47I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>47I',data,fs[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def linked(self,entry,address):
        key=(entry,address)
        if not hasattr(self,'links'):self.links={}
        if key in self.links:return self.links[key]
        pair=[];number=len(self.links)
        for j,obj in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o')):
            p=self.fresh/('layout-%d-%d.ld'%(number,j));elf=p.with_suffix('.elf');p.write_text(('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }'%entry)+chr(10));subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=D_800BE616=0x%X'%address,'-o',str(elf),str(obj)],capture_output=True,check=True);pair.append(list(struct.unpack_from('>47I',sections(elf)['.text'][1])))
        self.assertEqual(*pair);self.links[key]=pair;return pair
    def compare(self,c=Case(),images=None,entry=source.ENTRY,address=source.GATE):
        if c.alias:address=gate_address(c,address);images=self.linked(entry,address)
        initial=fixture(c,address);expected,result=classify(initial,RECORD,output_address(c,address),address);pair=[]
        for words in images or(self.truth,self.words):
            m=ClassifierOracle(words,initial,c,entry,address).run();self.assertEqual((m.memory,m.r[2]),(expected,result),c);self.assertFalse(m.calls);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
    def test_01_owner_GLOBAL_ASM_Make_ABI_and_census(self):
        self.assertEqual(self.words,self.truth);diagnostics=[]
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),37);diagnostics.append(re.findall(r'Warning [0-9]+:.*?line [0-9]+: (.*)',diag))
        self.assertEqual(diagnostics[0],diagnostics[1]);self.assertEqual(len(diagnostics[0]),4);self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),36);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_185560.c.o.compact'),37);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==0x0C000000|(source.ENTRY>>2&0x3FFFFFF)],[0x186148]);self.assertFalse(any(w in(source.ENTRY,0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text())
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=47,frame=0,bindings=2,guards=0,neighbors=36,compact_functions=37,Make_commands=5,GLOBAL_ASM_retained=True,unchanged_owner_warnings=4,ABI='s32(u8*,u8*)')
    def test_02_ordered_rules_all_bytes_and_writable_aliases(self):
        count=0;visits=set()
        for kind,subtype,gate,output in itertools.product(range(256),(0,2,5,255),(0,255),range(4)):
            m=self.compare(Case(gate,kind,subtype,kind%3,output));visits.update(m.visits);count+=1
        for subtype,kind,tag in itertools.product(range(256),(0,8,10,41,42,255),(0,1)):
            self.compare(Case(0,kind,subtype,tag));count+=1
        for gate,kind,tag in itertools.product(range(256),(0,8,10,41,42,255),(0,1)):
            self.compare(Case(gate,kind,5,tag));count+=1
        for alias,output,kind,subtype,gate,phase in itertools.product(range(4),range(7),(0,8,41),(0,2),(0,255),(0,8)):
            self.compare(Case(gate,kind,subtype,1,output,alias,phase=phase));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+188,4)));self.receipt['guest']=dict(cases=count,all47words_visited=True,all_type_subtype_global_bytes=True,ordered_overrides=True,no_match_preserves_output=True,output_layouts=7,global_layouts=4,full_RAM_GPR_FPR_events_visits_trace_equal=True)
    def test_03_complete_original_parent_return_and_release_branches(self):
        parent=list(struct.unpack_from('>65I',self.rom,0x186080));count=0
        for gate,kind,subtype,tag,allocated,null,flag in itertools.product((0,255),(0,8,10,41),(0,2),(0,1),(False,True),(False,True),(0,255)):
            c=Case(gate,kind,subtype,tag,allocated=allocated,source_null=null,flag=flag);initial=fixture(c);want,calls,value=parent_reference(initial,c);pair=[]
            for target in(self.truth,self.words):
                connected={source.ENTRY+4*i:w for i,w in enumerate(target)};m=ClassifierOracle(parent,initial,c,entry=source.PARENT,connected=connected,arguments=(0 if null else RECORD,flag,c.size)).run();self.assertEqual((public(m.memory),m.calls,m.r[2]),(want,calls,value),c);pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        self.receipt['caller']=dict(original_parent_words=65,cases=count,complete_original_parent_with_classifier_connected=True,source_and_allocation_nulls=True,success_initialization_and_reject_release_return_paths=True,bounded_allocator_and_release=True,parent_C_stub_uncredited=True,no_full_allocator_release_or_gameplay_claim=True)
    def test_04_native32_exhaustive_type_pairs_and_alias_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=1572864,effective_controls=8,trapping_UBSan=True,all65536_type_subtype_pairs=True,six_valid_output_alias_layouts=True,full_record_global_and_output_bytes_preserved=True)
    def test_05_fired_read_write_fault_prefixes_and_unmapped_no_match_output(self):
        cuts=0
        for c in(Case(),Case(255,8,5,1),Case(0,10,2),Case(0,41),Case(0,42),Case(255,8,5,1,1),Case(255,8,5,1,2),Case(255,8,5,1,3),Case(255,8,5,1,4,2)):
            address=gate_address(c);initial=fixture(c,address);good=self.compare(c);images=self.linked(source.ENTRY,address)if c.alias else(self.truth,self.words)
            for cut in range(good.root_accesses):
                pair=[]
                for words in images:
                    m=ClassifierOracle(words,initial,c,address=address);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut);pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        c=Case();initial=fixture(c);initial.pop(OUTPUT)
        for words in(self.truth,self.words):m=ClassifierOracle(words,initial,c,arguments=(RECORD,0xDEAD0000)).run();self.assertEqual(m.r[2],0)
        self.receipt['faults']=dict(fired_prefix_pairs=cuts,complete_private_state_trace_PC_delay=True,no_match_needs_no_output_mapping_or_store=True)
    def test_06_actual_padder_raw_controls_and_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[28]^=1
        for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,rs|{0:[('R_MIPS_HI16','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
        for entry,address in((source.ENTRY,source.GATE),(0x17007FFC,0x81008000),(0x2500FFFC,0x8120FFFF)):
            images=self.linked(entry,address)
            for c in(Case(),Case(255,8,5,1),Case(0,10,2),Case(0,41,2,1,1),Case(0,8,5,1,2),Case(255,10,5,1,4,2)):self.compare(c,images,entry,address);count+=1
        self.receipt['rebases']=dict(layouts=3,guest_cases=count,two_bindings_signed_low_carries=True,actual_GNU_original_and_compiled_objects=True,raw_corruption_controls=3,guards=0)
    def test_07_compiled_early_return_mutant_is_rejected(self):
        body=source.SELECTED.replace('matched = 1;','return 1;',1);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-early-return');self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));c=Case(255,8,5,1);initial=fixture(c);m=ClassifierOracle(words,initial,c).run();self.assertNotEqual(m.memory,classify(initial,RECORD,OUTPUT,source.GATE)[0]);self.receipt['negative_priority']=dict(actual_compiled_early_return_rejected=True,global_zero_does_not_suppress_later_type8_output2=True)
    def test_08_strict_full_image_metadata_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+188];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,188);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+28,at+188,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        self.assertEqual(sum(x!=y for x,y in zip(before,expected)),130);self.receipt['image']=dict(changed_bytes=130,code_bytes=129,metadata_bytes=1,other6055_bodies_and6056_addresses_fixed=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,guards_and_shared_headers_unchanged=True)
