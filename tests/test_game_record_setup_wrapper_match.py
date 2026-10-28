"""Quad setup wrapper: thirteen-slot ABI, late reads, original helpers and strict image."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_record_setup_wrapper_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_command_stream_relocator import StopCode,WindowEnd
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2];EFFECT,IMAGES,INDIRECT,OTHER=0x50000,0x60000,0x70000,0x71000
FLOATS=(0,0x80000000,0x3F800000,0xC0200000,1,0x80000001,0x7F7FFFFF,0x7FC12345)
VALUES=(0,1,127,128,255,256,32767,32768,65535,65536,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x87654321)
MUTATED=(0x80000000,0x3FA00000,0xBF800000,OTHER,0xDEAD8000,0xFFFF1234,255,0x87654321,0x12345678,0x80000000,1,255,0xFFFFFFFF)
@dataclass(frozen=True)
class Case:
    pattern:int=0
    byte:int=37
    index:int=91
    allocated:bool=True
    result:int=1
    mutation:int=0
    destination:int=0
    alias:int=0
    phase:int=0
    override:object=None

def arguments(c):
    if c.override is not None:return c.override
    v=tuple(VALUES[(c.pattern+i*3)%len(VALUES)]for i in range(13))
    return(FLOATS[c.pattern%8],FLOATS[(c.pattern+1)%8],FLOATS[(c.pattern+2)%8],INDIRECT,v[4],0xA5A50000|(c.byte*257),0xCCDD0000|c.byte,v[7],v[8],v[9],v[10],0xDDCC0000|(255-c.byte),v[12])
def pointer(c):return(EFFECT,STACK+c.phase-88,STACK+c.phase-68,STACK+c.phase-56)[c.destination]if c.allocated else 0
def table_address(c,address):return STACK+c.phase+12 if c.alias else address
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def half(v):return(((v&65535)^32768)-32768)&0xFFFFFFFF

def fixture(c,address=source.TABLE):
    sp=STACK+c.phase;m={sp+i:(i*17+0xA5)&255 for i in range(-2048,2048)}
    for base,n in((EFFECT,128),(IMAGES,2048),(INDIRECT,16),(OTHER,16)):m.update({base+i:(i*13+0x59)&255 for i in range(n)})
    for i in range(256):put(m,address+i*4,IMAGES+i*8);put(m,IMAGES+i*8+6,(i*257+0x1234)&65535,2)
    put(m,INDIRECT+6,0x8123,2);put(m,OTHER+6,0xFEDC,2)
    for i,v in enumerate(arguments(c)):put(m,sp+i*4,v)
    return m

def constructor_packet(m,sp):return(half(read(m,sp+18,2)),read(m,sp+22,2),m[sp+27],read(m,sp+32),read(m,sp+36),read(m,sp+40),m[sp+47],read(m,sp+48))
def change(m,c,address):
    if c.mutation&1:
        for i,v in enumerate(MUTATED):put(m,STACK+c.phase+4*i,v)
    if c.allocated:m[pointer(c)+88]=c.index
    if c.mutation&2:put(m,address+c.index*4,OTHER)
def clobber(m,frame):
    for i in range(4):put(m,frame+4*i,0xB5000000+i)
def geometry_effect(m,p):put(m,p+16,0x1234,2);put(m,p+68,0xFB2E,2)
def reference(initial,c,address):
    m=dict(initial);sp=STACK+c.phase;frame=sp-48;a=arguments(c)
    for i in range(4):put(m,sp+i*4,a[i])
    packet=constructor_packet(m,sp)
    for i,v in enumerate(packet[4:],4):put(m,frame+i*4,v)
    calls=[(source.CONSTRUCTOR,packet)];change(m,c,address);clobber(m,frame)
    if c.allocated:
        z=read(m,sp+8);scale=read(m,sp+28);put(m,frame+16,z);put(m,frame+20,0);put(m,frame+24,scale)
        index=m[pointer(c)+88];metadata=read(m,address+4*index);image=read(m,metadata+6,2)
        query=(pointer(c)+16,read(m,sp+12),read(m,sp),read(m,sp+4),z,0,scale,image)
        calls.append((source.GEOMETRY,query));put(m,frame+44,pointer(c));put(m,frame+28,image);geometry_effect(m,pointer(c));clobber(m,frame)
        if not c.result:calls.append((source.FREE,(pointer(c),)));m[pointer(c)+94]=0xD3;clobber(m,frame)
    return public(m),calls

class SetupOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,address=source.TABLE,constructor=source.CONSTRUCTOR,geometry=source.GEOMETRY,free=source.FREE,connected=None):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=arguments(c),connected=connected)
        self.f[12],self.f[14]=arguments(c)[:2];self.r[4],self.r[5]=0xA1000004,0xA1000005
        self.case,self.address,self.constructor,self.geometry,self.free,self.trace=c,address,constructor,geometry,free,[]
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        sizes={source.ENTRY:13,self.constructor:8,self.geometry:8,self.free:1,source.ALLOC:6,source.QUERY:4};assert target in sizes,hex(target);args=self.arguments(sizes[target])
        if target==source.ENTRY:args=(self.f[12],self.f[14],*args[2:])
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        c=self.case;a=self.calls[-1][1]
        if target==self.constructor:change(self.memory,c,self.address);result=pointer(c)
        elif target==source.ALLOC:result=pointer(c)
        elif target==self.geometry:geometry_effect(self.memory,a[0]-16);result=c.result
        elif target==source.QUERY:
            put(self.memory,a[2],0);put(self.memory,a[3],0);result=0
        else:assert target==self.free;self.memory[a[0]+94]=0xD3;result=0xDEAD0001
        clobber(self.memory,self.r[29])
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result;self.hi,self.lo=0xA5000010,0xA5000011

def controls():
    b=source.SELECTED
    return dict(wrong_lifetime=b.replace('func_15171CA0(lifetime,','func_15171CA0((u8)lifetime,'),wrong_color=b.replace('lifetime, color,','lifetime, color ^ 1,'),wrong_slot=b.replace('alternate, slot, context','alternate, slot ^ 1, context'),lost_context=b.replace('alternate, slot, context','alternate, slot, 0'),swap_axes=b.replace('indirectVertices, x, y, z','indirectVertices, y, x, z'),wrong_vertex_pointer=b.replace('record->vertices,','(Vtx *)((u8 *)record + 0x20),'),wrong_scale=b.replace('scale, *(u16 *)','scale ^ 1, *(u16 *)'),cached_image=b.replace('D_8008CA4C[record->imageIndex]','D_8008CA4C[imageIndex]'),wrong_descriptor=b.replace('] + 6)','] + 4)'),nonzero_is_exact_one=b.replace(' + 6)) == 0',' + 6)) != 1'),missing_release=b.replace('func_1516972C((struct102 *)record);',''))

def native_harness():
    t=source.HEADERS+source.DECLARATIONS+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(QuadEffect19F150)==96&&sizeof(Vtx)==16&&__builtin_offsetof(QuadEffect19F150,vertices)==16&&__builtin_offsetof(QuadEffect19F150,imageIndex)==88)?1:-1];
u8 *D_8008CA4C[256];static u16 images[256][4];static struct{u32 pre[4];QuadEffect19F150 record;u32 post[4];}actual,expected;
static u32 calls,bad,allocated,answer,mutation,expectedIndex;static u32 expectedArgs[13];static void*vertexSource;
static u32 word(f32 v){union{f32 f;u32 u;}x;x.f=v;return x.u;}static f32 real(u32 v){union{f32 f;u32 u;}x;x.u=v;return x.f;}
void *func_15171CA0(s16 life,u16 color,u8 image,s32 flags,s32 step,s32 alternate,u8 slot,s32 context){
 if(calls++||life!=(s16)expectedArgs[4]||color!=(u16)expectedArgs[5]||image!=(u8)expectedArgs[6]||(u32)flags!=expectedArgs[8]||(u32)step!=expectedArgs[9]||(u32)alternate!=expectedArgs[10]||slot!=(u8)expectedArgs[11]||(u32)context!=expectedArgs[12])bad=1;
 if(!allocated)return 0;
 actual.record.lifetime=life;actual.record.color=color;actual.record.frame=0;actual.record.frameStep=(s16)step;actual.record.imageIndex=(u8)expectedIndex;actual.record.flags=(u8)flags;
 for(u32 i=0;i<4;i++)actual.record.vertices[i].v.flag=0;
 for(u32 i=0;i<256;i++)D_8008CA4C[i]=(u8*)&images[(i+(mutation?11:0))&255];
 return &actual.record;
}
s32 func_151725FC(Vtx*v,void*p,f32 x,f32 y,f32 z,f32 rotation,s32 scale,u8 image){
 if(calls++!=1||!allocated||v!=actual.record.vertices||p!=vertexSource||word(x)!=expectedArgs[0]||word(y)!=expectedArgs[1]||word(z)!=expectedArgs[2]||word(rotation)||(u32)scale!=expectedArgs[7]||image!=(u8)images[(expectedIndex+(mutation?11:0))&255][3]){bad=1;return (s32)answer;}
 v[0].v.ob[0]=0x1234;v[3].v.ob[2]=-1234;return (s32)answer;
}
void func_1516972C(struct102*p){if(calls++!=2||!allocated||answer||p!=(struct102*)&actual.record)bad=1;else actual.record.opaque5A[4]=0xD3;}
'''
    for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('void '+source.FUNCTION,'static void '+name)+'\n'
    t+=r'''
typedef void(*Setup)(f32,f32,f32,void*,s16,u16,u8,s32,s32,s32,s32,u8,s32);
static int check(Setup fn){const u32 fp[]={0,0x80000000,0x3F800000,0xC0200000,1,0x80000001,0x7F7FFFFF,0x7FC12345};const u32 values[]={0,1,127,128,255,256,32767,32768,65535,65536,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu,0x87654321u};u32 byte,p,a,result,change,i,j;u8 *aa=(u8*)&actual,*ee=(u8*)&expected;
 for(byte=0;byte<256;byte++)for(p=0;p<8;p++)for(a=0;a<2;a++)for(result=0;result<3;result++)for(change=0;change<2;change++){
  for(i=0;i<sizeof(actual);i++)aa[i]=ee[i]=(u8)(i*13+p+byte);
  for(i=0;i<13;i++)expectedArgs[i]=values[(p+i*3)%14];expectedArgs[0]=fp[p];expectedArgs[1]=fp[(p+1)%8];expectedArgs[2]=fp[(p+2)%8];expectedArgs[5]=byte*257;expectedArgs[6]=byte;expectedArgs[11]=255-byte;
  for(i=0;i<256;i++){for(j=0;j<4;j++)images[i][j]=(u16)(i*257+j*0x1234);D_8008CA4C[i]=(u8*)&images[i];}
  vertexSource=&images[(byte+17)&255];calls=bad=0;allocated=a;answer=result==2?0xFFFFFFFFu:result;mutation=change;expectedIndex=(byte+(change?37:0))&255;
  if(a){expected.record.lifetime=(s16)expectedArgs[4];expected.record.color=(u16)expectedArgs[5];expected.record.frame=0;expected.record.frameStep=(s16)expectedArgs[9];expected.record.imageIndex=(u8)expectedIndex;expected.record.flags=(u8)expectedArgs[8];for(j=0;j<4;j++)expected.record.vertices[j].v.flag=0;expected.record.vertices[0].v.ob[0]=0x1234;expected.record.vertices[3].v.ob[2]=-1234;if(!answer)expected.record.opaque5A[4]=0xD3;}
  fn(real(expectedArgs[0]),real(expectedArgs[1]),real(expectedArgs[2]),vertexSource,(s16)expectedArgs[4],(u16)expectedArgs[5],(u8)byte,(s32)expectedArgs[7],(s32)expectedArgs[8],(s32)expectedArgs[9],(s32)expectedArgs[10],(u8)expectedArgs[11],(s32)expectedArgs[12]);
  if(bad||calls!=(a?(answer?2:3):1))return 1;for(i=0;i<sizeof(actual);i++)if(aa[i]!=ee[i])return 1;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
    for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START

class RecordSetupWrapperTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>47I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>47I',data,fs[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def linked(self,entry,address,constructor,geometry,free):
        key=(entry,address,constructor,geometry,free)
        if not hasattr(self,'links'):self.links={}
        if key in self.links:return self.links[key]
        symbols=dict(D_8008CA4C=address,func_15171CA0=constructor,func_151725FC=geometry,func_1516972C=free);pair=[];number=len(self.links)
        for j,obj in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o')):
            p=self.fresh/('layout-%d-%d.ld'%(number,j));elf=p.with_suffix('.elf');p.write_text(('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }'%entry)+chr(10));subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,check=True);pair.append(list(struct.unpack_from('>47I',sections(elf)['.text'][1])))
        self.assertEqual(*pair);self.links[key]=pair;return pair
    def compare(self,c=Case(),images=None,entry=source.ENTRY,address=source.TABLE,constructor=source.CONSTRUCTOR,geometry=source.GEOMETRY,free=source.FREE):
        address=table_address(c,address)
        if c.alias:images=self.linked(entry,address,constructor,geometry,free)
        initial=fixture(c,address);want,calls=reference(initial,c,address);calls=[(constructor if t==source.CONSTRUCTOR else geometry if t==source.GEOMETRY else free,a)for t,a in calls];pair=[]
        for words in images or(self.truth,self.words):
            m=SetupOracle(words,initial,c,entry,address,constructor,geometry,free).run();self.assertEqual((public(m.memory),m.calls),(want,calls),c);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
    def test_01_owner_actual_Make_ABI_and_literal_census(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFD0)
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),7)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,'func_151725FC')),5);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_19F150.c.o.compact'),7);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
        from tools.experiments.game_four_head_lookup_match import payload
        self.assertEqual(payload(self.out/'after-owner.o','func_151725FC'),(source.PROVIDER_RAW,{}))
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==0x0C000000|(source.ENTRY>>2&0x3FFFFFF)],[0x111B94]);self.assertFalse(any(w in(source.ENTRY,0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text())
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=47,frame=48,bindings=5,guards=0,unchanged_neighbors=5,typed_provider_stub_words=7,provider_matching_credit=0,compact_functions=7,Make_commands=3,thirteen_argument_slots_and_void_return=True,no_diagnostics=True)
    def test_02_argument_widths_late_reads_aliases_and_all_results(self):
        count=0;visits=set()
        for byte,pattern,allocated,result,phase in itertools.product(range(256),range(8),(False,True),(0,1,0xFFFFFFFF),(0,8)):
            m=self.compare(Case(byte=byte,index=255-byte,pattern=pattern,allocated=allocated,result=result,phase=phase));visits.update(m.visits);count+=1
        for mutation,destination,result,phase in itertools.product(range(4),range(4),(0,1,0xFFFFFFFF),(0,8)):
            self.compare(Case(mutation=mutation,destination=destination,result=result,phase=phase));count+=1
        for mutation,result,phase in itertools.product((0,1),(0,1,0xFFFFFFFF),(0,8)):
            self.compare(Case(index=0,alias=1,mutation=mutation,result=result,phase=phase));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+188,4)));self.receipt['guest']=dict(cases=count,all47words_visited=True,all_image_slot_bytes=True,signed_lifetime_unsigned_color_bytes_and_full_words=True,raw_three_float_patterns_and_void_pointer=True,returned_record_index_and_late_table_lookup=True,guest_destinations=4,GNU_table_home_alias=True,provider_incoming_home_mutations=True,full_private_state_and_access_trace=True)
    def test_03_original_caller_constructor_and_geometry_failure_path(self):
        start,stop=0x150E46A8,0x150E474C;window=list(struct.unpack_from('>19I',self.rom,0x111B58));ROW=0x72000;count=0
        for allocated,result,phase in itertools.product((False,True),(0,1,0xFFFFFFFF),(0,8)):
            a=(0x3F800000,0xC0200000,0x80000000,INDIRECT,0xA5A58000,0xB5AD,19,0x87654321,0,0,0,255,0);c=Case(allocated=allocated,result=result,phase=phase,override=a);initial=fixture(c);sp=STACK+phase
            for i in range(3):put(initial,sp+0x118+4*i,a[i])
            initial.update({ROW+i:0x5A for i in range(16)});pair=[]
            for target in(self.truth,self.words):
                connected={source.ENTRY+4*i:w for i,w in enumerate(target)}|{0x150E4748:0x91020005};m=SetupOracle(window,initial,c,entry=start,connected=connected);m.r[5]=a[4];m.r[2]=a[6];m.r[3]=a[7];m.r[8]=ROW;m.r[13]=a[3];m.code[stop]=0;m.code=StopCode(m.code,m,stop)
                with self.assertRaises(WindowEnd):m.run()
                self.assertEqual(m.calls[0],(source.ENTRY,a));self.assertEqual(m.r[2],0x5A);pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        ctor=list(struct.unpack_from('>43I',self.rom,0x19F150));old=self.values['conker/build/conker.us.elf'];self.assertEqual(ctor,list(struct.unpack_from('>43I',old,source.elf_slot_offset(old,source.CONSTRUCTOR,172))))
        release=list(struct.unpack_from('>28I',self.rom,0x196BDC));self.assertEqual(release,list(struct.unpack_from('>28I',old,source.elf_slot_offset(old,source.FREE,112))))
        helpers=0;visited=set()
        for pattern,allocated,result,phase in itertools.product(range(14),(False,True),(0,1),(0,8)):
            c=Case(pattern=pattern,byte=(pattern*19)&255,index=(pattern*19)&255,allocated=allocated,result=result,phase=phase);initial=fixture(c);a=arguments(c);pair=[]
            for target in(self.truth,self.words):
                connected={source.CONSTRUCTOR+4*i:w for i,w in enumerate(ctor)};m=SetupOracle(target,initial,c,connected=connected).run();self.assertEqual([v for t,v in m.calls if t==source.ALLOC],[(15 if not a[10]else 67,a[12],96,1,a[11]&255,1)])
                if allocated:
                    for off,value,size in((80,a[4],2),(82,0,2),(84,a[9],2),(86,a[5],2),(88,a[6],1),(89,a[8],1),*( (off,0,2)for off in(22,38,54,70))):self.assertEqual(read(m.memory,EFFECT+off,size),value&((1<<(size*8))-1))
                    self.assertEqual(read(m.memory,EFFECT+16,2),0x1234);self.assertEqual(read(m.memory,EFFECT+68,2),0xFB2E)
                else:self.assertFalse(any(t in(source.GEOMETRY,source.FREE)for t,a in m.calls))
                visited.update(p for p in m.visits if source.CONSTRUCTOR<=p<source.CONSTRUCTOR+172);pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));helpers+=1
        self.assertEqual(visited,set(range(source.CONSTRUCTOR,source.CONSTRUCTOR+172,4)))
        geometry=list(struct.unpack_from('>329I',self.rom,0x19FAAC));failure_cases=0
        for phase in(0,8):
            c=Case(result=0,phase=phase);initial=fixture(c);pair=[]
            for target in(self.truth,self.words):
                connected={source.GEOMETRY+4*i:w for i,w in enumerate(geometry)};m=SetupOracle(target,initial,c,connected=connected).run();self.assertTrue(any(t==source.QUERY and a[:2]==(INDIRECT,0)for t,a in m.calls));self.assertEqual(m.calls[-1],(source.FREE,(EFFECT,)));pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));failure_cases+=1
        self.receipt['caller']=dict(original_window_words=19,cases=count,thirteen_slots_and_actual_return_overwrite=True,parent_C_uncredited=True,original_and_retained_constructor_words=43,constructor_cases=helpers,all43constructor_words_visited=True,retained_release_words_exact=28,original_geometry_words_mapped=329,original_geometry_query_failure_cases=failure_cases,bounded_allocator_geometry_success_and_release=True,no_full_parent_geometry_or_gameplay_claim=True)
    def test_04_native32_valid_objects_and_effective_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=24576,effective_controls=len(controls()),trapping_UBSan=True,valid_disjoint_typed_objects=True,whole_record_and_fences=True,last_provider_argument_semantic_low_byte=True,no_guest_home_alias_or_FCSR_claim=True)
    def test_05_fired_access_prefixes_and_null_table_suppression(self):
        cuts=0
        for c in(Case(),Case(allocated=False),Case(result=0),Case(result=0xFFFFFFFF,mutation=3),Case(destination=1),Case(destination=3),Case(alias=1,index=0,mutation=1)):
            address=table_address(c,source.TABLE);initial=fixture(c,address);good=self.compare(c);images=self.linked(source.ENTRY,address,source.CONSTRUCTOR,source.GEOMETRY,source.FREE)if c.alias else(self.truth,self.words)
            for cut in range(good.root_accesses):
                pair=[]
                for words in images:
                    m=SetupOracle(words,initial,c,address=address);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut);pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        c=Case(allocated=False);initial=fixture(c);initial={a:b for a,b in initial.items()if STACK-2048<=a<STACK+2048}
        for words in(self.truth,self.words):m=SetupOracle(words,initial,c).run();self.assertEqual(len(m.calls),1)
        self.receipt['faults']=dict(fired_prefix_pairs=cuts,full_private_state_trace_PC_delay=True,null_allocation_needs_no_record_table_or_descriptor=True)
    def test_06_actual_padder_corruptions_and_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[100]^=1
        for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,rs|{148:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());cases=0
        for entry,address,ctor,geo,free in((source.ENTRY,source.TABLE,source.CONSTRUCTOR,source.GEOMETRY,source.FREE),(0x17007FFC,0x81008000,0x17171CA0,0x171725FC,0x1716972C),(0x2500FFFC,0x8120FFFC,0x25171CA0,0x251725FC,0x2516972C)):
            images=self.linked(entry,address,ctor,geo,free)
            for c in(Case(),Case(allocated=False),Case(result=0),Case(mutation=3),Case(destination=1),Case(alias=1,index=0,mutation=1)):self.compare(c,images,entry,address,ctor,geo,free);cases+=1
        self.receipt['rebases']=dict(layouts=3,guest_cases=cases,five_bindings_and_signed_low_carries=True,GNU_original_and_compiled_objects=True,raw_corruption_controls=3,guards=0)
    def test_07_compiled_cached_argument_index_is_rejected(self):
        body=controls()['cached_image'];obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-cached-index');self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));c=Case(byte=37,index=91);m=SetupOracle(words,fixture(c),c).run();wanted=reference(fixture(c),c,source.TABLE)[1];self.assertNotEqual(m.calls,wanted);self.receipt['negative_index']=dict(actually_compiled_wrong_C_rejected=True,returned_record_index_not_cached_argument=True,result_failure_not_unmapped_read=True)
    def test_08_strict_full_image_two_extents_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+188];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,188);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8;provider=source.elf_slot_offset(before,source.GEOMETRY,28)
        for offset in(20,at,at+100,at+188,source.elf_slot_offset(before,0x80082B20,4),symbol,provider):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        self.assertEqual(sum(x!=y for x,y in zip(before,expected)),165);self.receipt['image']=dict(changed_bytes=165,wrapper_code_bytes=145,provider_code_bytes=18,metadata_bytes=2,other6054_bodies_and6056_addresses_fixed=True,provider_stub_uncredited=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=7,guards_and_shared_headers_unchanged=True)
