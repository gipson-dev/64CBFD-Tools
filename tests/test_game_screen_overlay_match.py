"""Screen-overlay SDK words, live aliases, exact callers, real rectangle and strict image."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_screen_overlay_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
CURSOR,CALLBACK,TEXT_TABLE,MODE=0x30000,0x15100004,0x40000,0x8003C8E0
PARENT_GLOBALS=(0x800E0B94,0x80000300,0x800BE616,0x8008FD90,0x800BE740,0x800E0BD3,0x800E0BD8)
DIMS=(-2147483646,-1,0,1,2,3,319,320,1023,1024,2147483647)
signed=lambda x:(x^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
    alpha:int=127
    width:int=320
    height:int=240
    phase:int=0
    gate_offset:int=-1
    width_offset:int=-1
    height_offset:int=-1
    real:bool=False
    callback:bool=False
    enabled:int=1
    alternate:int=0
    players:int=2
    blink:int=0
    text:int=1
    mutation:int=0

def addresses(c,delta=0):
    return(CURSOR+c.gate_offset if c.gate_offset>=0 else source.GATE+delta,CURSOR+c.width_offset if c.width_offset>=0 else source.WIDTH+delta,CURSOR+c.height_offset if c.height_offset>=0 else source.HEIGHT+delta)
def fixture(c,delta=0):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,512)}
    m.update({CURSOR+i:(i*13+0x59)&255 for i in range(-16,128)})
    gate,width,height=addresses(c,delta);put(m,width,c.width&0xFFFFFFFF);put(m,height,c.height&0xFFFFFFFF);m[gate]=c.alpha
    idx,on,alt,players,blink,text,table=PARENT_GLOBALS
    for a,v,n in((idx,0,1),(on,c.enabled,4),(alt,c.alternate,1),(players,c.players&255,1),(blink,c.blink,1),(text,c.text&255,1),(table,TEXT_TABLE,4),(MODE,0xA5A5A5A5,4),(0x8008FFF4,CALLBACK if c.callback else 0,4)):put(m,a,v,n)
    for i in range(64):put(m,TEXT_TABLE+4*i,0x50000+i*8)
    return m

def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+512}
def overlay_reference(initial,c,delta=0):
    m=dict(initial);gate,width,height=addresses(c,delta)
    if not m[gate]:return m,CURSOR,[]
    for off,v in((0,0xE7000000),(4,0),(8,0xEF082C3F),(12,0x00504340),(16,0xFCFFFFFF),(20,0xFFFEFB7D),(24,0xFB000000)):put(m,CURSOR+off,v)
    put(m,CURSOR+28,m[gate]);h,w=read(m,height),read(m,width);calls=[(source.HELPER,(CURSOR+32,0,0,w,h))]
    if c.real:
        limit=(read(m,width)-2)&0xFFFFFFFF;right=limit if signed(w)>=signed(limit)else w;bottom=read(m,height)if signed(h)>=signed(read(m,height))else h
        put(m,CURSOR+36,2<<14);put(m,CURSOR+32,0xF6000000|((right&1023)<<14)|((bottom&1023)<<2));return m,CURSOR+40,calls
    return m,CURSOR+48,calls

def provider_changes(m,c):
    if c.mutation&1:m[PARENT_GLOBALS[2]]=1;m[PARENT_GLOBALS[3]]=2;m[PARENT_GLOBALS[4]]=0;m[PARENT_GLOBALS[5]]=2
    if c.mutation&2:put(m,STACK+c.phase,0x30060)
def text_index(m):
    _,on,alt,players,blink,text,_=PARENT_GLOBALS
    if not read(m,on):return 0
    alternative=m[alt]and((m[players]^128)-128)>=2
    if m[blink]&(15 if alternative else 1):return 0
    return((0x33 if alternative else 0x32)if m[text]==1 else(0x16 if alternative else 0x15)if m[text]==2 else 0)
def parent_reference(initial,c):
    m=dict(initial);put(m,MODE,0x09000001);m,end,calls=overlay_reference(m,c);calls=[(source.ENTRY,(CURSOR,))]+calls
    if c.callback:calls.append((CALLBACK,(end,)));provider_changes(m,c);end+=8
    put(m,STACK+c.phase,end);idx=text_index(m)
    if idx:
        calls.append((0x1504332C,(255,255,255,255)))
        if c.mutation&4:put(m,TEXT_TABLE+idx*4,0x55550)
        calls.append((0x15042D94,(148,200,129,read(m,TEXT_TABLE+idx*4))))
        if c.mutation&8:put(m,STACK+c.phase,0x30070)
    put(m,MODE,0);return m,read(m,STACK+c.phase),calls

class OverlayOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,helper=source.HELPER,connected=None):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(CURSOR,),connected=connected)
        self.case,self.helper,self.trace=c,helper,[]
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        sizes={source.CALLER:1,source.ENTRY:1,self.helper:5,CALLBACK:1,0x1504332C:4,0x15042D94:4};assert target in sizes,hex(target)
        a=self.arguments(sizes[target]);self.calls.append((target,a));self.events.append(('CALL',target,a))
    def hook(self,target):
        c=self.case;a=self.calls[-1][1]
        if target==self.helper:result=a[0]+16
        elif target==CALLBACK:provider_changes(self.memory,c);result=a[0]+8
        elif target==0x1504332C:
            idx=text_index(self.memory)
            if c.mutation&4:put(self.memory,TEXT_TABLE+idx*4,0x55550)
            result=0xDEAD0001
        else:
            assert target==0x15042D94
            if c.mutation&8:put(self.memory,STACK+c.phase,0x30070)
            result=0xDEAD0002
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result;self.hi,self.lo=0xA5000010,0xA5000011

class UpperBoundary(Exception):pass
class UpperCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==0x15018C58:raise UpperBoundary
        return super().__getitem__(pc)

def controls():
    b=source.SELECTED
    return dict(exact_one=b.replace('D_800E0B96 == 0','D_800E0B96 != 1'),wrong_alpha=b.replace('0, 0, 0, D_800E0B96','0, 0, 0, (D_800E0B96 ^ 1U)'),wrong_mode=b.replace('G_RM_CLD_SURF | G_RM_CLD_SURF2','G_RM_XLU_SURF | G_RM_XLU_SURF2'),wrong_combine=b.replace('ENVIRONMENT','PRIMITIVE'),wrong_reserved=b.replace('(0xF << G_MDSFT_BLENDMASK)','(0xE << G_MDSFT_BLENDMASK)'),wrong_cursor=b.replace('func_1501A6CC(commands,','func_1501A6CC(commands - 1,'),ignored_return=b.replace('return func_1501A6CC(commands, 0, 0, D_800BE620, D_800BE624);','func_1501A6CC(commands, 0, 0, D_800BE620, D_800BE624); return commands;'),cached_alpha=b.replace('    if (D_800E0B96 == 0)', '    u8 captured = D_800E0B96;\n    if (captured == 0)').replace('0, 0, 0, D_800E0B96','0, 0, 0, captured'),early_dimensions=b.replace('    if (D_800E0B96 == 0)','    s32 width = D_800BE620; s32 height = D_800BE624;\n    if (D_800E0B96 == 0)').replace('commands, 0, 0, D_800BE620, D_800BE624','commands, 0, 0, width, height'))

def helper_source(root):
    text=(root/'conker/src/game_476D0.c').read_text();begin=text.index('Gfx *func_1501A6CC(');end=text.index(chr(10)+'}',begin)+2;return text[begin:end]

def native_harness():
    t=source.HEADERS+r'''
static u8 flag,*gate;static s32 screenWidth,screenHeight,*widthPointer,*heightPointer;
#define D_800E0B96 (*gate)
#define D_800BE620 (*widthPointer)
#define D_800BE624 (*heightPointer)
static Gfx output[20],expected[20];static u32 calls,bad,realHelper;static s32 wantW,wantH;
'''+helper_source(ROOT).replace('func_1501A6CC','rectangle')+r'''
Gfx *func_1501A6CC(Gfx*p,s32 a,s32 b,s32 c,s32 d){if(p!=output+6||a||b||c!=wantW||d!=wantH||calls++)bad=1;return realHelper?rectangle(p,a,b,c,d):p+2;}
typedef char ABI[(sizeof(void*)==4&&sizeof(Gfx)==8)?1:-1];
'''
    for n,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('Gfx *'+source.FUNCTION,'static Gfx *'+n)+chr(10)
    t+=r'''
typedef Gfx*(*Draw)(Gfx*);
static int check(Draw fn){const s32 dims[]={-2147483646,-1,0,1,2,3,319,320,1023,1024,2147483647};u32 alpha,layout,mode,d,i;Gfx*end;u8*egate; s32*ewidth,*eheight;u8*p=(u8*)output,*q=(u8*)expected;
 for(alpha=0;alpha<256;alpha++)for(layout=0;layout<39;layout++)for(mode=0;mode<2;mode++)for(d=0;d<11;d++){
  for(i=0;i<sizeof(output);i++)p[i]=q[i]=(u8)(i*13+0x59);flag=(u8)alpha;screenWidth=dims[d];screenHeight=dims[(d+3)%11];
  gate=layout<32?(u8*)(output+2)+layout:&flag;egate=layout<32?(u8*)(expected+2)+layout:&flag;
  widthPointer=layout>=32&&layout<36?(s32*)&output[2+(layout-32)].words.w0:&screenWidth;ewidth=layout>=32&&layout<36?(s32*)&expected[2+(layout-32)].words.w0:&screenWidth;
  heightPointer=layout>=36?(s32*)&output[2+(layout-36)].words.w1:&screenHeight;eheight=layout>=36?(s32*)&expected[2+(layout-36)].words.w1:&screenHeight;
  *widthPointer=*ewidth=screenWidth;*heightPointer=*eheight=screenHeight;*gate=*egate=(u8)alpha;realHelper=mode;calls=bad=0;
  if(*egate){expected[2].words.w0=0xE7000000u;expected[2].words.w1=0;expected[3].words.w0=0xEF082C3Fu;expected[3].words.w1=0x00504340;expected[4].words.w0=0xFCFFFFFFu;expected[4].words.w1=0xFFFEFB7Du;expected[5].words.w0=0xFB000000u;expected[5].words.w1=*egate;wantW=*ewidth;wantH=*eheight;
   if(mode){s32 right=wantW,bottom=wantH;if(right>=*ewidth-2)right=*ewidth-2;if(bottom>=*eheight)bottom=*eheight;expected[6].words.w1=2u<<14;expected[6].words.w0=0xF6000000u|(((u32)right&1023)<<14)|(((u32)bottom&1023)<<2);}
  }
  end=fn(output+2);if(bad||calls!=(alpha!=0)||end!=output+(alpha?(mode?7:8):2))return 1;
  for(i=0;i<sizeof(output);i++)if(p[i]!=q[i])return 1;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
    for i,n in enumerate(controls()):t+='if(!check('+n+'))return '+str(20+i)+';'+chr(10)
    return t+'return 0;}'+chr(10)+START

class ScreenOverlayTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>47I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>47I',data,fs[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+chr(10))
    def linked(self,entry,gate,width,height,helper):
        key=(entry,gate,width,height,helper)
        if not hasattr(self,'links'):self.links={}
        if key in self.links:return self.links[key]
        syms=dict(D_800E0B96=gate,D_800BE620=width,D_800BE624=height,func_1501A6CC=helper);pair=[];number=len(self.links)
        for j,obj in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o')):
            p=self.fresh/('layout-%d-%d.ld'%(number,j));elf=p.with_suffix('.elf');p.write_text(('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }'%entry)+chr(10));subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in syms.items()],'-o',str(elf),str(obj)],capture_output=True,check=True);pair.append(list(struct.unpack_from('>47I',sections(elf)['.text'][1])))
        self.assertEqual(*pair);self.links[key]=pair;return pair
    def helper(self):
        old=self.values['conker/build/conker.us.elf'];words=list(struct.unpack_from('>38I',old,source.elf_slot_offset(old,source.HELPER,152)));self.assertEqual(words,list(struct.unpack_from('>38I',self.rom,0x47B7C)));return{source.HELPER+4*i:w for i,w in enumerate(words)}
    def compare(self,c=Case(),images=None,entry=source.ENTRY,helper=source.HELPER,delta=0):
        initial=fixture(c,delta);want,end,calls=overlay_reference(initial,c,delta);calls=[(helper,a)for t,a in calls];pair=[];connected=self.helper()if c.real else None
        for words in images or(self.truth,self.words):
            m=OverlayOracle(words,initial,c,entry,helper,connected).run();self.assertEqual((public(m.memory),m.r[2],m.calls),(public(want),end,calls),c);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
    def test_01_owner_actual_Make_and_both_pointer_interfaces(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFE0)
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),27)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),26);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
        self.assertEqual(source.payload(self.out/'selected.o'),source.payload(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_215960.c.o.compact'),27)
        self.assertEqual(source.function_payload(self.out/'before-owner.o','func_151E84B0'),source.function_payload(self.out/'after-owner.o','func_151E84B0'))
        self.assertEqual(source.same_functions(self.out/'before-aux.o',self.out/'after-aux.o'),16)
        for label in('aux-before-make','aux-after-make'):self.assertEqual((self.out/(label+'/src/game_45B80.c.o')).read_bytes(),self.values[source.AUX_OBJECT]);self.assertEqual(len(json.loads((self.out/(label+'-commands.json')).read_text())),3)
        self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text());self.assertEqual(source.recovered_aux(self.values[source.AUX_SOURCE].decode()),(self.out/'proposed-aux.c').read_text())
        for a,b in((source.ENTRY,0x21A690),(source.CALLER,0x215960)):
            word=0x0C000000|(a>>2&0x3FFFFFF);positions=[i for i in range(0,len(self.rom),4)if struct.unpack_from('>I',self.rom,i)[0]==word];self.assertEqual(positions,[0x215978]if a==source.ENTRY else[0x460FC])
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=47,frame=32,bindings=7,guards=0,neighbors=26,parent_words_unchanged=92,aux_functions_unchanged=16,aux_padded_objects_identical=True,Make_commands=5,aux_Make_commands=3,old_debug_gap_preserved=True,proper_Gfx_pointer_interfaces=True,main_diagnostics=0,aux_existing_warnings=3)
    def test_02_all_alpha_bytes_and_GNU_linked_live_aliases(self):
        visits=set();count=0
        for alpha,phase,w in itertools.product(range(256),(0,8),(0,320,0x7FFFFFFF,-1)):
            m=self.compare(Case(alpha=alpha,phase=phase,width=w));visits.update(m.visits);count+=1
        for c in([Case(gate_offset=i,alpha=a)for i in range(32)for a in(0,1,127,128,255)]+[Case(width_offset=i)for i in range(0,32,4)]+[Case(height_offset=i)for i in range(0,32,4)]):
            g,w,h=addresses(c);images=self.linked(source.ENTRY,g,w,h,source.HELPER);self.compare(c,images);count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+188,4)));self.receipt['guest']=dict(cases=count,all47words_visited=True,all256_unsigned_gate_values=True,gate_aliases_all32_command_bytes=True,width_height_aliases_all8_command_words=True,late_environment_alpha_and_dimensions=True,full_private_state_and_trace=True,opaque_helper_return_preserved=True)
    def test_03_complete_retained_parent_real_rectangle_and_upper_window(self):
        old=self.values['conker/build/conker.us.elf'];parent=list(struct.unpack_from('>92I',self.rom,0x215960));self.assertEqual(parent,list(struct.unpack_from('>92I',old,source.elf_slot_offset(old,source.CALLER,368))));visited=set();count=0
        for alpha,callback,on,alt,players,blink,text,mutation in itertools.product((0,255),(False,True),(0,1),(0,1),(-128,1,2,127),(0,1,2,16),(-1,1,2),(0,1,4,8)):
            c=Case(alpha=alpha,callback=callback,enabled=on,alternate=alt,players=players,blink=blink,text=text,mutation=mutation);initial=fixture(c);want,end,calls=parent_reference(initial,c);pair=[]
            for words in(self.truth,self.words):
                connected={source.ENTRY+4*i:w for i,w in enumerate(words)};m=OverlayOracle(parent,initial,c,entry=source.CALLER,connected=connected).run();self.assertEqual((public(m.memory),m.r[2],m.calls),(public(want),end,calls),c);visited.update(p for p in m.visits if source.CALLER<=p<source.CALLER+368);pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);count+=1
        self.assertEqual(set(range(source.CALLER,source.CALLER+368,4))-visited,{0x151E8578,0x151E85B8})
        helpers=0
        for alpha,w,h in itertools.product((0,1,128,255),DIMS,DIMS):self.compare(Case(alpha=alpha,width=w,height=h,real=True));helpers+=1
        window=list(struct.unpack_from('>3I',self.rom,0x460FC));self.assertEqual(window,list(struct.unpack_from('>3I',old,source.elf_slot_offset(old,0x15018C4C,12))));upper_cases=0
        for alpha,callback,mutation in itertools.product((0,1,255),(False,True),(0,1,4,8)):
            c=Case(alpha=alpha,callback=callback,mutation=mutation);initial=fixture(c);put(initial,0x800BE9D0,CURSOR);want,end,calls=parent_reference(initial,c);put(want,0x800BE9D0,end);pair=[]
            for words in(self.truth,self.words):
                connected={source.CALLER+4*i:w for i,w in enumerate(parent)};connected.update({source.ENTRY+4*i:w for i,w in enumerate(words)});m=OverlayOracle(window,initial,c,entry=0x15018C4C,connected=connected);m.r[17]=0x800BE9D0;m.code=UpperCode(m.code,m)
                with self.assertRaises(UpperBoundary):m.run()
                self.assertEqual((public(m.memory),m.r[2],m.calls),(public(want),end,[(source.CALLER,(CURSOR,))]+calls));pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);upper_cases+=1
        self.receipt['caller']=dict(actual_upper_window_words=3,upper_connected_cases=upper_cases,parent_words=92,feasible_parent_words_visited=len(visited),unreachable_duplicate_constants=[hex(x)for x in sorted(set(range(source.CALLER,source.CALLER+368,4))-visited)],cases=count,optional_pointer_callback_and_late_global_text_decision=True,actual_parent_result_home_reload=True,original_and_retained_rectangle_words=38,helper_cases=helpers,bounded_color_text_and_callback_providers=True,upper_JAL_ROM='0x460FC',upper_source_and_all16functions_and_padded_object_unchanged=True,no_full_RDP_or_gameplay_claim=True)
    def test_04_native32_real_SDK_aliases_rectangle_and_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=256*39*2*11,effective_controls=len(controls()),trapping_UBSan=True,real_SDK_headers=True,all256_gate_bytes=True,all32_host_byte_aliases_and_dimension_word_aliases=True,real_retained_rectangle_source=True,valid_signed_subtraction_domain=True,Gfx32_pointer_and_arena_fences=True,no_native_guest_stack_or_big_endian_claim=True)
    def test_05_all_fired_access_prefixes_and_disabled_sparse_mapping(self):
        cuts=0
        for c in(Case(),Case(alpha=0),Case(real=True),Case(real=True,width=-1,height=-1)):
            initial=fixture(c);good=self.compare(c)
            for cut in range(good.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m=OverlayOracle(words,initial,c,connected=self.helper()if c.real else None);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut);pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        initial={a:b for a,b in fixture(Case(alpha=0)).items()if not CURSOR-16<=a<CURSOR+128 and not source.WIDTH<=a<source.HEIGHT+4}
        for words in(self.truth,self.words):m=OverlayOracle(words,initial,Case(alpha=0)).run();self.assertFalse(m.calls);self.assertEqual(m.r[2],CURSOR)
        self.receipt['faults']=dict(fired_prefix_pairs=cuts,full_private_state_trace_PC_delay=True,disabled_needs_no_output_or_dimension_mapping=True)
    def test_06_actual_padder_corruptions_and_independent_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[100]^=1
        for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,rs|{164:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());cases=0
        for entry,delta,helper in((source.ENTRY,0,source.HELPER),(0x17007FFC,0x20000,0x1701A6CC),(0x2500FFFC,0x40000,0x2501A6CC)):
            images=self.linked(entry,source.GATE+delta,source.WIDTH+delta,source.HEIGHT+delta,helper)
            for alpha in(0,1,127,128,255):self.compare(Case(alpha=alpha),images,entry,helper,delta);cases+=1
        self.receipt['rebases']=dict(layouts=3,guest_cases=cases,all7_HI_LO_J26_bindings=True,GNU_original_and_compiled_objects=True,raw_corruption_controls=3,guards=0)
    def test_07_actually_compiled_cached_alpha_and_dimensions_rejected(self):
        cases=dict(cached_alpha=Case(gate_offset=3,alpha=127),early_dimensions=Case(width_offset=0));results={}
        for name,c in cases.items():
            obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+controls()[name],'negative-'+name);self.assertFalse(diag);g,w,h=addresses(c);p=self.fresh/(name+'.ld');elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x151ED1E0 : SUBALIGN(4) { *(.text) } }'+chr(10));syms=dict(D_800E0B96=g,D_800BE620=w,D_800BE624=h,func_1501A6CC=source.HELPER);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in syms.items()],'-o',str(elf),str(obj)],capture_output=True,check=True);raw=sections(elf)['.text'][1];words=list(struct.unpack('>%dI'%(len(raw)//4),raw));m=OverlayOracle(words,fixture(c),c).run();want,end,calls=overlay_reference(fixture(c),c);self.assertNotEqual((public(m.memory),m.calls),(public(want),calls));results[name]=dict(result_failure_not_unmapped_read=True)
        self.receipt['compiled_controls']=results
    def test_08_strict_entire_image_metadata_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+188];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,188);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+100,at+188,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        self.assertEqual(sum(x!=y for x,y in zip(before,expected)),145);self.receipt['image']=dict(changed_bytes=145,code_bytes=144,metadata_bytes=1,other6055_bodies_and6056_addresses_fixed=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,guards_and_shared_headers_unchanged=True,both_sources_and_aux_actual_padded_object_audited=True)
