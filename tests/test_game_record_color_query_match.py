"""Live packed-byte extraction, overlapping outputs and original record lookup."""
from dataclasses import dataclass,replace
import csv,itertools,json,struct,subprocess,unittest
from tools.experiments import game_record_color_query_candidates as candidate
from tools.experiments import game_record_color_query_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=candidate.ROOT
QUERY,PRED=0x1515EB84,0x150A1DA0
R0,R1,N0,N1,OUT,ALT=0x20000,0x21000,0x30000,0x30100,0x50000,0x50100
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
    coords:tuple=(0,0x80000000,0x7FFFFFFF)
    unused:int=0xAABBCCDD
    outputs:tuple=(OUT,OUT+4,OUT+8,OUT+9)
    record:int=R0
    head:int=N0
    mutation:int=0
    phase:int=0
    seed:int=0
    scenario:int=1

def syms(base=0x800DCD24,query=QUERY):
    return dict(D_800DCD24=base,D_800DCD28=base+4,D_800DCD3C=base+24,D_800DCD3D=base+25,D_800DCD84=base+96,func_1515EB84=query)
def fixture(c=Case(),s=None):
    s=s or syms();h=STACK+c.phase;m={STACK+i:(i*17+c.seed*11+165)&255 for i in range(-2048,2048)}
    for base,n in((R0,64),(R1,64),(N0,64),(N1,64),(OUT,64),(ALT,64),(s['D_800DCD24']-16,128)):
        m.update({base+i:(i*29+c.seed*37+91)&255 for i in range(n)})
    put(m,R0+0x18,u32(0xA1B2C3D4+c.seed*0x1020304));put(m,R0+0x1C,u32(0xE5F60718+c.seed*0x112233))
    put(m,R1+0x18,0x12345678);put(m,R1+0x1C,0x9ABCDEF0)
    put(m,N0,N1);put(m,N0+4,R0);put(m,N1,0);put(m,N1+4,R1);put(m,s['D_800DCD84'],c.head)
    for record in(R0,R1):m[record+0x14]=0;m[record+0x15]=96
    if c.scenario==0:put(m,s['D_800DCD84'],0)
    if c.scenario==2:m[R0+0x14]=1
    if c.scenario==3:m[R0+0x15]=0;put(m,R0+0x18,0x80010203)
    if c.scenario==7:m[R0+0x14]=1;m[R1+0x14]=1
    put(m,h+12,c.unused)
    for i,p in enumerate(c.outputs):put(m,h+16+4*i,p)
    return m

def effects(m,c,h,s,record):
    if c.mutation&1:
        if record:put(m,record+0x18,0xFEDCBA98);put(m,record+0x1C,0x76543210)
        for j,name in enumerate(('D_800DCD24','D_800DCD28')):
            for i in range(3):m[s[name]+i]=0x31+i*19+j*37
        m[s['D_800DCD3C']]=0xE1;m[s['D_800DCD3D']]=0xD2
    if c.mutation&2:put(m,s['D_800DCD84'],N1)
    if c.mutation&4:
        for i,p in enumerate((ALT,ALT+4,ALT+8,ALT+9)):put(m,h+16+4*i,p)
    if c.mutation&8:
        for i in range(4):put(m,h+4*i,0x12345678+i)

def reference(initial,c,ra,s=None,h=None,connected=False):
    s=s or syms();h=STACK+c.phase if h is None else h;m=dict(initial);calls=[]
    put(m,h-4,ra);put(m,h+12,c.unused);head=read(m,s['D_800DCD84']);put(m,h-16,head)
    calls.append((s['func_1515EB84'],tuple(map(u32,(*c.coords,0,head)))))
    record=c.record
    if connected:
        record=0;node=head
        while node:
            r=read(m,node+4)
            if m[r+0x14]==0 and(m[r+0x15]>>2==24 or read(m,r+0x18)>>31==0):
                calls.append((PRED,(h-32-0x360+0x34,r,0)));effects(m,c,h,s,r)
                if c.scenario==5 and node==N0:put(m,node+4,R1)
                answer=1 if c.scenario==6 or(c.scenario==4 and r==R0)else 0
                if not answer:record=read(m,node+4);break
            node=read(m,node)
    else:effects(m,c,h,s,record)
    primary=read(m,h+16);secondary=read(m,h+20)
    if record:
        for p,offset in((primary,0x18),(secondary,0x1C)):
            for i in range(3):m[p+i]=(read(m,record+offset)>>(8*i))&255
        value=read(m,record+0x1C)>>24;m[read(m,h+24)]=value
        value=read(m,record+0x18)>>24;m[read(m,h+28)]=value
    else:
        for p,name in((primary,'D_800DCD24'),(secondary,'D_800DCD28')):
            for i in range(3):m[p+i]=m[s[name]+i]
        m[read(m,h+24)]=m[s['D_800DCD3C']];m[read(m,h+28)]=m[s['D_800DCD3D']]
    return m,calls,record
def public(m):return{p:v for p,v in m.items()if not STACK-2048<=p<STACK+2048}

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=match.ENTRY,connected=None,arguments=None):
        self.s=s or syms();self.home=STACK+c.phase;self.snapshots=[]
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,
            arguments=(*c.coords,c.unused,*c.outputs)if arguments is None else arguments)
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,False
    def record_call(self,t):
        if t==self.s['func_1515EB84']:a=tuple(map(u32,self.arguments(5)))
        elif t==PRED:
            a=tuple(map(u32,self.arguments(3)));p=a[0]
            self.snapshots.append(tuple(read(self.memory,p+i)for i in(0x14,0x18,0x1C,0x2C,0x30,0x34,0x180)))
        elif t==match.ENTRY:a=tuple(map(u32,self.arguments(8)));self.home=self.r[29]
        else:raise AssertionError(('Unbounded color provider',hex(t)))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        if t==self.s['func_1515EB84']:effects(self.memory,self.case,self.home,self.s,self.case.record);answer=self.case.record
        else:
            assert t==PRED;r=self.calls[-1][1][1];effects(self.memory,self.case,self.home,self.s,r)
            if self.case.scenario==5 and r==R0:put(self.memory,N0+4,R1)
            answer=1 if self.case.scenario==6 or(self.case.scenario==4 and r==R0)else 0
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(answer)

def controls():
    b=candidate.SELECTED;first='        primary[0] = (*(u32 *)(record + 0x18)) & 0xFF;';second='        primary[1] = (*(u32 *)(record + 0x18) >> 8) & 0xFF;'
    cached=b.replace('    if (record != 0) {','    if (record != 0) {\n        u32 cached = *(u32 *)(record + 0x18);').replace('(*(u32 *)(record + 0x18))','cached').replace('(*(u32 *)(record + 0x18) >>','(cached >>')
    return dict(mask=b.replace('x, y, z, 0, D_800DCD84','x, y, z, 1, D_800DCD84'),head=b.replace('0, D_800DCD84','0, (LinkedNode *)0'),
        word=b.replace(first,first.replace('0x18','0x1C')),order=b.replace(first+'\n'+second,second+'\n'+first),cached=cached,
        fallback=b.replace('primary[0] = D_800DCD24[0]','primary[0] = D_800DCD24[1]'),
        extra=b.replace('*secondaryExtra =','*TEMP =').replace('*primaryExtra =','*secondaryExtra =').replace('*TEMP =','*primaryExtra ='),
        byte=b.replace('primary[2] =','primary[1] ='))

LAYOUTS=((0,4,8,9),(24,28,31,27),(25,26,24,29),(26,24,30,31),(28,24,27,31),(0,0,0,0),(1,0,2,1),
 (64,72,80,81),(65,73,81,80),(72,64,80,81),(64,65,66,67),(73,72,74,75),(24,72,80,81),(64,28,31,27),(30,25,24,29),(8,4,24,28),(25,4,8,9))
def native_source(body):
    return '''typedef unsigned char u8;typedef int s32;typedef unsigned int u32;typedef struct LinkedNode {struct LinkedNode *next;u8 data[0x30];} LinkedNode;
LinkedNode *D_800DCD84;u8 D_800DCD24[8],D_800DCD28[8],D_800DCD3C,D_800DCD3D;
static LinkedNode node;static u8 *arena;static u8 wanted[82];static int found,mutation,calls,error;
static u8 *ptr(u32 i){return i<64?arena+i:i<72?D_800DCD24+i-64:i<80?D_800DCD28+i-72:i==80?&D_800DCD3C:&D_800DCD3D;}
static void save(u32 p,u32 v){u32 i;for(i=0;i<4;i++)wanted[p+i]=(u8)(v>>(8*i));}
static u32 load(u32 p){return (u32)wanted[p]|(u32)wanted[p+1]<<8|(u32)wanted[p+2]<<16|(u32)wanted[p+3]<<24;}
static void effect(int real){u32 i;if(!mutation)return;
if(real){*(u32*)(arena+24)=0xFEDCBA98;*(u32*)(arena+28)=0x76543210;}else{save(24,0xFEDCBA98);save(28,0x76543210);}
for(i=0;i<3;i++){if(real){D_800DCD24[i]=(u8)(0x31+i*19);D_800DCD28[i]=(u8)(0x56+i*19);}else{wanted[64+i]=(u8)(0x31+i*19);wanted[72+i]=(u8)(0x56+i*19);}}
if(real){D_800DCD3C=0xE1;D_800DCD3D=0xD2;}else{wanted[80]=0xE1;wanted[81]=0xD2;}}
u8 *func_1515EB84(s32 x,s32 y,s32 z,s32 mask,LinkedNode *head){calls++;if((u32)x!=0x80000000u||y!=-17||z!=0x7FFFFFFF||mask||head!=&node)error=1;effect(1);return found?arena:0;}
'''+body+'''
static const u32 layouts[][4]={'''+','.join('{'+','.join(map(str,row))+'}'for row in LAYOUTS)+'''};
typedef void(*Handler)(s32,s32,s32,s32,u8*,u8*,u8*,u8*);
__attribute__((noinline))static void invoke(Handler fn,u8*a,u8*b,u8*c,u8*d){fn((s32)0x80000000u,-17,0x7FFFFFFF,-1,a,b,c,d);}
static int run(void){u32 args[6]={0,4096,3,0x22,0xFFFFFFFFu,0},address,seed,j,i,k,value;int f,m,typed;
__asm__ volatile("int $0x80":"=a"(address):"a"(90),"b"(args):"memory");if(address>=0xFFFFF000u||sizeof(void*)!=4)return 9;arena=(u8*)address;
for(seed=0;seed<32;seed++)for(j=0;j<sizeof(layouts)/sizeof(layouts[0]);j++)for(f=0;f<2;f++)for(m=0;m<2;m++)for(typed=0;typed<2;typed++){
for(i=0;i<82;i++){wanted[i]=(u8)(i*29+seed*37+91);*ptr(i)=wanted[i];}
/* Establish word effective types before any unsigned-char alias writes. */
*(u32*)(arena+24)=load(24);*(u32*)(arena+28)=load(28);
found=f;mutation=m;calls=error=0;D_800DCD84=&node;effect(0);
if(found){for(k=0;k<2;k++)for(i=0;i<3;i++)wanted[layouts[j][k]+i]=(u8)(load(24+4*k)>>(8*i));wanted[layouts[j][2]]=(u8)(load(28)>>24);wanted[layouts[j][3]]=(u8)(load(24)>>24);}
else{for(k=0;k<2;k++)for(i=0;i<3;i++)wanted[layouts[j][k]+i]=wanted[64+8*k+i];wanted[layouts[j][2]]=wanted[80];wanted[layouts[j][3]]=wanted[81];}
if(typed)invoke(func_1515E43C,ptr(layouts[j][0]),ptr(layouts[j][1]),ptr(layouts[j][2]),ptr(layouts[j][3]));
else func_1515E43C((s32)0x80000000u,-17,0x7FFFFFFF,-1,ptr(layouts[j][0]),ptr(layouts[j][1]),ptr(layouts[j][2]),ptr(layouts[j][3]));
if(calls!=1||error)return 1;for(i=0;i<82;i++){value=*ptr(i);if(value!=wanted[i])return 1;}
}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''

class GameRecordColorQueryMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>66I',cls.rom,match.ROM));linked,fs=candidate.link_owner(ROOT,cls.out,cls.prepared['qualified_compact'],candidate.OWNER)
        cls.words=list(struct.unpack_from('>66I',linked,fs[match.FUNCTION]['value']))
    def receipt(self,name,row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    def compare(self,c,initial=None,images=None,s=None,entry=match.ENTRY,connected=None):
        initial=fixture(c,s)if initial is None else initial;models=[]
        for body in images or(self.retail,self.words):models.append(Oracle(body,initial,c,s,entry,connected).run())
        expected,calls,record=reference(initial,c,models[0].before[31],s,connected=bool(connected))
        for m in models:self.assertEqual(public(m.memory),public(expected),c);self.assertEqual(m.calls,calls,c)
        self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].snapshots,models[1].snapshots)
        return models[0]
    def test_01_direct_complete_owner_bindings_and_literal_image_controls(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['relocations'],q['neighbors'],q['raw_neighbors']),(66,32,0,11,34,34));self.assertEqual(self.words,self.retail)
        raw,rs=match.function_blob(self.prepared['qualified_compact']);truth=match.original_bytes(ROOT)
        for i in range(264):
            bad=bytearray(raw);bad[i]^=1
            with self.assertRaises(ValueError):match.checked_payload(bytes(bad),rs,truth)
        for i in rs:
            with self.assertRaises(ValueError):match.checked_payload(raw,{**rs,i:[('R_MIPS_26','wrong')]},truth)
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();self.assertEqual(match.strict_image(before,after,truth),197)
        for i in(0,0x80,match.elf_slot_offset(before,match.ENTRY,264)+264,len(after)-1):
            bad=bytearray(after);bad[i]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        with(ROOT/match.GUARDS).open()as stream:self.assertFalse([r for r in csv.DictReader(stream)if r['function']==match.FUNCTION])
    def test_02_guest_widths_returns_and_live_provider_effects(self):
        count=0;visits=set()
        for coords,unused,record,mutation,phase in itertools.product(((0,0,0),(1,0xFFFFFFFF,32767),(0x80000000,0x7FFFFFFF,0xFEDCBA98),(0x12345678,0x87654321,17)),
                (0,0xAABBCCDD,0xFFFFFFFF),(0,R0,R1),range(16),(0,8)):
            c=Case(coords,unused,record=record,mutation=mutation,phase=phase,seed=count%16);m=self.compare(c);visits.update(m.visits);count+=1
        self.assertEqual(visits,set(range(match.ENTRY,match.ENTRY+264,4)));self.receipt('guest-contract',dict(cases_per_body=count,reachable_words=66,all_eight_arguments=True))
    def test_03_ordered_record_default_output_and_private_aliases(self):
        count=0;s=syms();bases=[OUT+i for i in range(4)]+[R0+i for i in range(0x18,0x20)]+[s['D_800DCD24']+i for i in range(3)]+[s['D_800DCD28']+i for i in range(3)]
        for p,record,phase in itertools.product(bases,(0,R0),(0,8)):
            for outputs in((p,p,p,p),(p,p+1,p+2,p+3),(p+1,p,p+3,p+2)):
                self.compare(Case(outputs=outputs,record=record,phase=phase));count+=1
        for phase in(0,8):
            h=STACK+phase
            for outputs in((h+20,OUT+4,OUT+8,OUT+9),(OUT,h+16,OUT+8,OUT+9),(h-16,OUT+4,h+24,h+28)):
                for record in(0,R0):self.compare(Case(outputs=outputs,record=record,phase=phase));count+=1
        self.receipt('aliases',dict(cases_per_body=count,live_word_reloads=True,live_defaults=True,cached_secondary_and_late_extra_homes=True))
    def test_04_connected_original_linked_record_search(self):
        code=dict(zip(range(QUERY,QUERY+244,4),struct.unpack_from('>61I',self.rom,0x18C034)));count=0
        for scenario,coords,phase,mutation in itertools.product(range(8),((0,0,0),(0x80000000,0x7FFFFFFF,17)),(0,8),(0,4)):
            c=Case(coords=coords,scenario=scenario,phase=phase,mutation=mutation);m=self.compare(c,connected=code)
            x,y,z=(bits(float(signed(v)))for v in coords)
            for snapshot in m.snapshots:self.assertEqual(snapshot,(x,y,z,x,y,z,y))
            count+=1
        self.receipt('connected',dict(cases_per_body=count,original_search_words=61,predicate_bounded=True,live_node_return_reload=True))
    def test_05_two_original_caller_gates_eight_argument_windows(self):
        count=0
        for which,enabled,record,phase in itertools.product((0,1),(0,1),(0,R0),(0,8)):
            c=Case(record=record,phase=phase);initial=fixture(c);h=STACK+phase
            if which==0:
                start,end,skip=0x1515D968,0x1515D9A8,0x1515DA34;outputs=(h+0xB0,h+0xAC,h+0xAB,h+0xAA)
                for i,v in enumerate(c.coords):put(initial,h+0x140+4*i,v)
                put(initial,h+0x160,c.unused)
            else:
                start,end,skip=0x1515E328,0x1515E368,0x1515E42C;outputs=(h+0x4C,h+0x48,h+0x47,h+0x46)
                for i,v in enumerate(c.coords):put(initial,h+0x60+4*i,v)
                put(initial,h+0x6C,c.unused);put(initial,h+0x78,16 if enabled else 0)
            caller=list(struct.unpack_from('>%dI'%((end-start)//4),self.rom,start-0x15000000+0x2D4B0));models=[]
            for body in(self.retail,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+264,4),body));code[end]=code[skip]=0
                m=Oracle(caller,initial,c,entry=start,connected=code,arguments=(*c.coords,c.unused));m.r[18]=2 if enabled else 0
                m.code=WindowCode(m.code,m);m.code.ends=(end,skip)
                with self.assertRaises(WindowBoundary):m.run()
                if enabled:
                    expected_input=dict(initial)
                    for i,p in enumerate(outputs):put(expected_input,h+16+4*i,p)
                    expected,calls,_=reference(expected_input,replace(c,outputs=outputs),end)
                    self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,[(match.ENTRY,tuple(map(u32,(*c.coords,c.unused,*outputs))))]+calls)
                else:self.assertEqual(m.calls,[]);self.assertEqual(public(m.memory),public(initial))
                models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt('callers',dict(cases_per_body=count,original_callers=2,full_parent_not_claimed=True))
    def test_06_fired_fault_prefixes_and_unused_branch_sources(self):
        count=0
        for c in(Case(),Case(record=0,phase=8),Case(outputs=(R0+24,R0+28,R0+31,R0+27))):
            initial=fixture(c);done=Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                models=[]
                for body in(self.retail,self.words):
                    m=Oracle(body,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace);count+=1
        for found in(0,R0):
            c=Case(record=found);initial=fixture(c)
            addresses=([syms()[n]+i for n in('D_800DCD24','D_800DCD28')for i in range(3)]+[syms()['D_800DCD3C'],syms()['D_800DCD3D']])if found else list(range(R0+24,R0+32))
            for p in addresses:initial.pop(p)
            self.compare(c,initial)
        self.receipt('fault-prefixes',dict(fired_prefixes=count,unused_source_branches_unmapped=True))
    def test_07_independent_GNU_links_and_carry_edges(self):
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        ctx=type('ColorOriginal',(),dict(root=ROOT,out=self.out));original=ViewListSetupTests.original.__func__(ctx,'original-color-query',(ROOT/match.ASM).read_text(),match.FUNCTION)
        links=count=0
        for j,(entry,s)in enumerate(((match.ENTRY,syms()),(0x18017FFC,syms(0x800B7FF0,0x18038000)),(0x1A028000,syms(0x800C8000,0x1A048000)))):
            images=[]
            for k,obj in enumerate((original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(j,k));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
                images.append(list(struct.unpack_from('>66I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for record,mutation,phase in itertools.product((0,R0,R1),(0,5),(0,8)):
                self.compare(Case(record=record,mutation=mutation,phase=phase),images=(images[0],images[1]),s=s,entry=entry);count+=1
        self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,all_eleven_bindings=True,carry_edges=True))
    def test_08_native32_ordered_aliases_layout_and_typed_calls(self):
        for label,body,opt,wanted in [('positive-'+o[1:],candidate.SELECTED,o,0)for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in controls().items()]:
            p=self.out/('native-'+label+'.c');p.write_text(native_source(body));exe=p.with_suffix('.elf')
            result=subprocess.run([*native_command(opt),'-mstackrealign',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            (self.out/('native-'+label+'-diagnostics.txt')).write_text(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[:4000]);self.assertEqual(subprocess.run([str(exe)]).returncode,wanted,label)
        self.receipt('native-contract',dict(positive_executions=32*len(LAYOUTS)*2*2*2*3,profiles=['O0','O2','O3'],direct_and_typed=True,alias_layouts=len(LAYOUTS),controls=8,UBSan=True))
    def test_09_actual_IDO_semantic_controls(self):
        found={}
        for label,body in controls().items():
            obj,_=candidate.compile_owner(ROOT,self.out,candidate.source_with(body),'negative-'+label);linked,fs=candidate.link_owner(ROOT,self.out,obj,candidate.OWNER);f=fs[match.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),linked,f['value']));witness=False
            for c in(Case(),Case(record=0),Case(outputs=(R0+24,R0+28,R0+31,R0+27)),Case(outputs=(R0+26,R0+28,R0+31,R0+27)),Case(record=0,outputs=(syms()['D_800DCD24']+1,OUT+4,OUT+8,OUT+9))):
                initial=fixture(c);m=Oracle(words,initial,c).run();expected,calls,_=reference(initial,c,m.before[31])
                if(public(m.memory),m.calls)!=(public(expected),calls):witness=True;break
            self.assertTrue(witness,label);found[label]=True
        self.receipt('compiled-controls',dict(effective_IDO_controls=found))

if __name__=='__main__':unittest.main()
