"""Phase cycle spawn: soft-float ABI, exact packet padding, allocation and original helpers."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_phase_cycle_spawn_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_command_stream_relocator import StopCode,WindowEnd
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2];EFFECT=0x50000
PAIRS=((0,0x80000000),(0x80000000,0x80000000),(0x3F800000,0x40200000),(1,0x80000001),(0x7F7FFFFF,0x7F7FFFFF),(0x7F800000,0xFF800000),(0x7FC12345,0x3F800000))
@dataclass(frozen=True)
class Case:
    life:int=300
    first:int=0x3F800000
    second:int=0x40200000
    color0:int=0x12
    color1:int=0x34
    priority:int=255
    owner:int=0x12345678
    count:int=255
    allocated:bool=True
    seed:int=0xA5
    mutation:int=0
    destination:int=0
    alias:int=0
    phase:int=0

def counter(c,address=source.COUNTER):return(address,STACK+c.phase-23,STACK+c.phase)[c.alias]
def pointer(c):
    payload=STACK+c.phase-24
    return(EFFECT,payload-40,payload+1-40,STACK+c.phase+4-40)[c.destination]if c.allocated else 0

def fixture(c,address=source.COUNTER):
    sp=STACK+c.phase;m={sp+i:(i*17+c.seed)&255 for i in range(-768,256)};m.update({EFFECT+i:(i*13+0x59)&255 for i in range(160)});m[counter(c,address)]=c.count
    for i,v in enumerate((c.color1,c.priority,c.owner),4):put(m,sp+4*i,v)
    return m

def public(m):return{a:b for a,b in m.items()if not STACK-768<=a<STACK+256}
def narrowed(x):return(((x&65535)^32768)-32768)&0xFFFFFFFF
def spawned_args(c):return(narrowed(c.life),0xFFFFFFFF,47,2,1,38,24,c.priority&255,c.owner&0xFFFFFFFF)
def change(m,c,address):
    payload=STACK+c.phase-24
    if c.mutation&1:
        for i in(1,2,3,22,23):m[payload+i]=(i*7+0x19)&255
    if c.mutation&2:m[address]=0x71
    if c.mutation&4:
        for i in range(7):put(m,STACK+c.phase+4*i,0xC5000000+i)

def reference(initial,c,address=source.COUNTER):
    m=dict(initial);sp=STACK+c.phase;payload=sp-24;put(m,sp,c.life);put(m,sp+12,c.color0);address=counter(c,address);m[address]=(m[address]+1)&255
    put(m,payload+8,c.first);put(m,payload+12,c.second);put(m,payload+16,bits(floating(c.first)+floating(c.second)));m[payload]=0;put(m,payload+4,0);m[payload+20]=c.color0&255;m[payload+21]=c.color1&255
    snapshot=bytes(m[payload+i]for i in range(24));calls=[(source.SPAWN,spawned_args(c))];change(m,c,address);copied=None
    if c.allocated:
        dst=pointer(c)+40;calls.append((source.COPY,(dst,payload,24)));copied=bytes(m[payload+i]for i in range(24))
        for i in range(24):m[dst+i]=m[payload+i]
    return public(m),calls,snapshot,copied

class PhaseOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,address=source.COUNTER,spawn=source.SPAWN,copy=source.COPY,connected=None):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(c.life,c.first,c.second,c.color0,c.color1,c.priority,c.owner),connected=connected);self.case,self.address,self.spawn,self.copy,self.trace=c,address,spawn,copy,[];self.snapshot,self.copied=None,None
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        sizes={source.ENTRY:7,self.spawn:9,self.copy:3,source.ALLOC:6,source.ZERO:2};assert target in sizes,hex(target);args=self.arguments(sizes[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==self.spawn:self.snapshot=bytes(self.memory[STACK+self.case.phase-24+i]for i in range(24))
        if target==self.copy:self.copied=bytes(self.memory[args[1]+i]for i in range(args[2]))
    def hook(self,target):
        c=self.case;args=self.calls[-1][1]
        if target==self.spawn:change(self.memory,c,self.address);result=pointer(c)
        elif target==source.ALLOC:result=pointer(c)
        elif target==source.ZERO:
            for i in range(args[1]):self.put(args[0]+i,0,1)
            result=0
        else:
            assert target==self.copy
            for i in range(args[2]):self.put(args[0]+i,self.get(args[1]+i,1),1)
            result=args[0]
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result;self.hi,self.lo=0xA5000010,0xA5000011

def controls():
    b=source.SELECTED
    return dict(no_count=b.replace('    D_800D9900++;',''),wrong_period=b.replace('activeDuration + inactiveDuration','activeDuration - inactiveDuration'),swap_colors=b.replace('cycle.activeColor = activeColor','cycle.activeColor = inactiveColor').replace('cycle.inactiveColor = inactiveColor','cycle.inactiveColor = activeColor'),nonzero_phase=b.replace('cycle.phase = 0.0f','cycle.phase = 1.0f'),active_initial=b.replace('cycle.active = 0','cycle.active = 1'),wrong_size=b.replace('sizeof(PhaseCycle), priority','20, priority'),skip_copy=b.replace('if (effect != NULL)','if (effect != NULL && 0)'),wrong_priority=b.replace('sizeof(PhaseCycle), priority','sizeof(PhaseCycle), priority ^ 1U'))

def native_harness():
    t=source.HEADERS+source.DECLARATIONS+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(PhaseCycle)==24&&__builtin_offsetof(PhaseCycle,phase)==4&&__builtin_offsetof(PhaseCycle,threshold)==8&&__builtin_offsetof(PhaseCycle,inactiveDuration)==12&&__builtin_offsetof(PhaseCycle,period)==16&&__builtin_offsetof(PhaseCycle,activeColor)==20&&__builtin_offsetof(PhaseCycle,inactiveColor)==21)?1:-1];
u8 D_800D9900;static union{u64 align;u8 data[160];} object;static u32 allocation,count0,ctor,copy,bad;static s16 expectedLife;static u8 expectedPriority;static s32 expectedOwner;static PhaseCycle captured;
static u32 word(f32 v){union{f32 f;u32 u;}x;x.f=v;return x.u;}static f32 real(u32 v){union{f32 f;u32 u;}x;x.u=v;return x.f;}
static void copy_bytes(void*d,const void*s,u32 n){volatile u8*a=d;const u8*b=s;u32 i;for(i=0;i<n;i++)a[i]=b[i];}
struct260*func_15149130(s16 life,s8 a,s8 b,s8 c,u8 flags,u8 kind,s32 size,u8 priority,s32 owner){ctor++;if(D_800D9900!=(u8)(count0+1)||life!=expectedLife||a!=-1||b!=47||c!=2||flags!=1||kind!=38||size!=24||priority!=expectedPriority||owner!=expectedOwner)bad=1;return allocation?(struct260*)object.data:0;}
void*memcpy(void*d,const void*s,u32 n){copy++;if(!allocation||d!=object.data+40||n!=24){bad=1;return d;}copy_bytes(&captured,s,24);copy_bytes(d,s,24);return d;}
'''
    for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('void '+source.FUNCTION,'static void '+name)+'\n'
    t+=r'''
typedef void(*Spawn)(s16,f32,f32,u8,u8,u8,s32);
static int check(Spawn fn){const u32 values[]={0,0x80000000,0x3F800000,0x40200000,1,0x80000001,0x7F7FFFFF,0x7F800000};u32 count,i,j,color,k;volatile f32 sum;
 for(count=0;count<256;count++)for(i=0;i<8;i++)for(j=0;j<8;j++)for(color=0;color<2;color++)for(allocation=0;allocation<2;allocation++){
  for(k=0;k<160;k++)object.data[k]=(u8)(k*13+0x59);count0=count;D_800D9900=(u8)count;ctor=copy=bad=0;expectedLife=(s16)(i?0x8000:0x7FFF);expectedPriority=color?255:0;expectedOwner=color?-1:0x12345678;
  sum=real(values[i])+real(values[j]);fn(expectedLife,real(values[i]),real(values[j]),color?0xA5:0,color?0x5A:255,expectedPriority,expectedOwner);
  if(bad||ctor!=1||copy!=allocation||D_800D9900!=(u8)(count+1))return 1;
  if(allocation&&(captured.active||word(captured.phase)||word(captured.threshold)!=values[i]||word(captured.inactiveDuration)!=values[j]||word(captured.period)!=word(sum)||captured.activeColor!=(color?0xA5:0)||captured.inactiveColor!=(color?0x5A:255)))return 1;
  for(k=0;k<160;k++)if((!allocation||k<40||k>=64)&&object.data[k]!=(u8)(k*13+0x59))return 1;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
    for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START

class PhaseCycleSpawnTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>47I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>47I',data,fs[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def linked(self,entry,address,spawn,copy):
        key=(entry,address,spawn,copy)
        if not hasattr(self,'links'):self.links={}
        if key in self.links:return self.links[key]
        symbols=dict(D_800D9900=address,func_15149130=spawn,memcpy=copy);pair=[];number=len(self.links)
        for j,obj in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o')):
            p=self.fresh/('layout-%d-%d.ld'%(number,j));elf=p.with_suffix('.elf');p.write_text(('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }'%entry)+chr(10));subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,check=True);pair.append(list(struct.unpack_from('>47I',sections(elf)['.text'][1])))
        self.assertEqual(*pair);self.links[key]=pair;return pair
    def compare(self,c=Case(),images=None,entry=source.ENTRY,address=source.COUNTER,spawn=source.SPAWN,copy=source.COPY):
        if c.alias:address=counter(c,address);images=self.linked(entry,address,spawn,copy)
        initial=fixture(c,address);want,calls,snapshot,copied=reference(initial,c,address);calls=[(spawn if t==source.SPAWN else copy,a)for t,a in calls];pair=[]
        for words in images or(self.truth,self.words):
            m=PhaseOracle(words,initial,c,entry,address,spawn,copy).run();self.assertEqual((public(m.memory),m.calls,m.snapshot,m.copied),(want,calls,snapshot,copied),c);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
    def test_01_owner_actual_Make_ABI_and_literal_census(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFB0)
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),7)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),6);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_FF5C0.c.o.compact'),7);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==0x0C000000|(source.ENTRY>>2&0x3FFFFFF)],[0xFF8A8]);self.assertFalse(any(w in(source.ENTRY,0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text())
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=47,frame=80,bindings=4,guards=0,neighbors=6,compact_functions=7,Make_commands=3,ABI='void(s16,f32,f32,u8,u8,u8,s32)',retained_PhaseCycle_prefix_and_color_extension=True,no_diagnostics=True)
    def test_02_packet_fields_padding_allocation_and_aliases(self):
        count=0;visits=set()
        for byte,pair,allocated,phase in itertools.product(range(256),PAIRS,(False,True),(0,8)):
            c=Case(life=0xA5A50000|byte,first=pair[0],second=pair[1],color0=0x12340000|byte,color1=0xA5A50000|(255-byte),priority=0x5A5A0000|byte,allocated=allocated,phase=phase,seed=byte);m=self.compare(c);visits.update(m.visits);count+=1
        for life,mutation,destination,alias in itertools.product((0,0x7FFF,0x8000,0xFFFF,0x80000000,0xFFFFFFFF),range(8),range(4),range(3)):
            self.compare(Case(life=life,mutation=mutation,destination=destination,alias=alias));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+188,4)));self.receipt['guest']=dict(cases=count,all47words_visited=True,all_counter_and_byte_arguments=True,signed_lifetime_and_softfloat_bits=True,full24byte_snapshot_and_five_padding_bytes=True,allocation_success_failure_and_mutations=True,guest_destinations=4,GNU_counter_alias_layouts=3,full_private_state_and_access_trace=True,NaN_payload_reference_bounded_not_FCSR_hardware_claim=True)
    def test_03_original_caller_and_original_retained_constructor_copy(self):
        start,stop=0x150D23BC,0x150D2400;body=list(struct.unpack_from('>17I',self.rom,start-0x15000000+0x2D4B0));ACTOR=0x60000;count=0
        for allocated,phase in itertools.product((False,True),(0,8)):
            c=Case(allocated=allocated,phase=phase);initial=fixture(c);initial.update({ACTOR+i:0 for i in range(96)});put(initial,ACTOR+56,c.first);put(initial,ACTOR+60,c.second);initial[ACTOR+64]=c.color0;initial[ACTOR+65]=c.color1;initial[ACTOR+12]=c.priority;initial[ACTOR+1]=c.owner&255;pair=[]
            for target in(self.truth,self.words):
                connected={source.ENTRY+4*i:w for i,w in enumerate(target)};m=PhaseOracle(body,initial,c,entry=start,connected=connected);m.r[3]=ACTOR+40;m.r[16]=ACTOR;m.r[14]=c.color1;m.r[9]=1;m.r[11]=c.life;m.hi=0;m.code[stop]=0;m.code=StopCode(m.code,m,stop)
                with self.assertRaises(WindowEnd):m.run()
                self.assertEqual(m.calls[0],(source.ENTRY,(c.life,c.first,c.second,c.color0,c.color1,c.priority,c.owner&255)));pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        old=self.values['conker/build/conker.us.elf'];ctor=list(struct.unpack_from('>49I',self.rom,0x1765E0));copy=list(struct.unpack_from('>11I',self.rom,0x22EC0));ret_ctor=list(struct.unpack_from('>49I',old,source.elf_slot_offset(old,source.SPAWN,196)));ret_copy=list(struct.unpack_from('>11I',old,source.elf_slot_offset(old,source.COPY,44)));self.assertEqual(ctor,ret_ctor);self.assertEqual(copy,ret_copy);helpers=0
        for allocated,count0 in itertools.product((False,True),(0,255)):
            c=Case(allocated=allocated,count=count0);initial=fixture(c);pair=[]
            for target in(self.truth,self.words):
                connected={source.SPAWN+4*i:w for i,w in enumerate(ctor)}|{source.COPY+4*i:w for i,w in enumerate(copy)};m=PhaseOracle(target,initial,c,connected=connected).run();allocator=[a for t,a in m.calls if t==source.ALLOC];self.assertEqual(allocator,[(35,c.owner,64,1,c.priority,1)])
                if allocated:
                    self.assertEqual(bytes(m.memory[EFFECT+40+i]for i in range(24)),m.snapshot);self.assertEqual(m.memory[EFFECT+13],1);self.assertEqual(read(m.memory,EFFECT+14,2),c.life&65535);self.assertTrue(all(m.memory[EFFECT+20+i]==0 for i in range(16)))
                else:self.assertFalse(any(t in(source.ZERO,source.COPY)for t,a in m.calls))
                pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));helpers+=1
        self.receipt['caller']=dict(original_window_words=17,cases=count,seven_physical_arguments_and_ignored_return=True,parent_C_stub_uncredited=True,original_and_retained_ctor_words=49,original_and_retained_copy_words=11,helper_cases=helpers,real_header_stores_and_payload_copy=True,bounded_allocator_and_bzero=True,no_full_parent_allocator_or_gameplay_claim=True)
    def test_04_native32_fields_without_padding_claim_and_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=65536,effective_controls=8,trapping_UBSan=True,disjoint_valid_payload_and_typed_providers=True,defined_fields_and_outside_destination_preserved=True,padding_contents_and_guest_aliases_excluded=True)
    def test_05_fired_access_prefixes_and_null_copy_suppression(self):
        cuts=0
        for c in(Case(),Case(allocated=False),Case(mutation=7),Case(destination=1),Case(destination=2),Case(alias=1),Case(alias=2)):
            address=counter(c);initial=fixture(c,address);good=self.compare(c);images=self.linked(source.ENTRY,address,source.SPAWN,source.COPY)if c.alias else(self.truth,self.words)
            for cut in range(good.root_accesses):
                pair=[]
                for words in images:
                    m=PhaseOracle(words,initial,c,address=address);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut);pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        c=Case(allocated=False);initial=fixture(c);initial={a:b for a,b in initial.items()if not EFFECT<=a<EFFECT+160}
        for words in(self.truth,self.words):m=PhaseOracle(words,initial,c).run();self.assertEqual(len(m.calls),1)
        self.receipt['faults']=dict(fired_prefix_pairs=cuts,full_private_state_trace_PC_delay=True,null_allocation_needs_no_destination_or_copy=True)
    def test_06_actual_padder_corruptions_and_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[100]^=1
        for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,rs|{144:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());cases=0
        for entry,address,spawn,copy in((source.ENTRY,source.COUNTER,source.SPAWN,source.COPY),(0x17007FFC,0x81008000,0x17149130,0x10028000),(0x2500FFFC,0x8120FFFF,0x25149130,0x20022EC0)):
            images=self.linked(entry,address,spawn,copy)
            for c in(Case(),Case(allocated=False),Case(mutation=7),Case(destination=2),Case(alias=1),Case(alias=2)):self.compare(c,images,entry,address,spawn,copy);cases+=1
        self.receipt['rebases']=dict(layouts=3,guest_cases=cases,four_bindings_and_signed_low_carries=True,GNU_original_and_compiled_objects=True,raw_corruption_controls=3,guards=0)
    def test_07_compiled_zero_initialized_packet_is_rejected(self):
        body=source.SELECTED.replace('PhaseCycle cycle;','PhaseCycle cycle = {0};');obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-zero-padding');self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));c=Case(seed=0xA5);memory=fixture(c)
        for name,(address,chunk)in sections(obj.with_suffix('.elf')).items():
            if name.startswith(('.data','.rodata')):memory.update({address+i:b for i,b in enumerate(chunk)})
        m=PhaseOracle(words,memory,c).run();self.assertNotEqual(m.copied,reference(fixture(c),c)[3]);self.receipt['negative_padding']=dict(compiled_zero_initializer_rejected=True,seeded_five_guest_padding_bytes_preserved=True,no_portable_C_padding_claim=True)
    def test_08_strict_full_image_metadata_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+188];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,188);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+100,at+188,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        self.assertEqual(sum(x!=y for x,y in zip(before,expected)),140);self.receipt['image']=dict(changed_bytes=140,code_bytes=139,metadata_bytes=1,other6055_bodies_and6056_addresses_fixed=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,guards_and_shared_headers_unchanged=True)
