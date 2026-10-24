"""Phase-cycle wrapping: literal words, bounded floats, callback ABI and native C."""
from pathlib import Path
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_phase_cycle_gate as source
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_linked_owner_retirement import parent_harness
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
OWNER,TIME,COLOR,PRIORITY,DIRTY=0x30000,0x800BE9A4,0x800DCD20,0x800DCD27,0x800DCD7C
HELPER,PARENT,TABLE,EXIT_TABLE,TICKS,RELEASE=0x1515D4D4,0x15149264,0x8008A4E8,0x8008A4C0,0x800BE9E4,0x1516972C


class LoopBudget(Exception):
    pass


def corpus():
    phases=(0,0x80000000,1,0x80000001,bits(-3),bits(.5),bits(1),bits(2),bits(17),bits(1)-1,bits(1)+1)
    for p,dt,period,threshold in itertools.product(phases,(0,bits(.25),bits(-.5)),(bits(.5),bits(1),bits(3)),(bits(-1),0,bits(.5),bits(1),bits(3))):
        yield p,dt,period,threshold


def fixture(case,owner=OWNER):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    for base,n in ((owner-32,128),(TIME-16,48),(COLOR-16,128),(TICKS-8,20)):
        m.update({base+i:(i*13+0xA5)&255 for i in range(n)})
    m[PRIORITY]=255
    p,dt,period,threshold=case
    put(m,owner+0x2C,p);put(m,owner+0x30,threshold);put(m,owner+0x38,period);put(m,TIME,dt)
    return m


def reference(initial,owner=OWNER,connected=True):
    m=dict(initial);p=owner+0x2C;period=owner+0x38;threshold=owner+0x30
    put(m,p,bits(floating(read(m,p))+floating(read(m,TIME))))
    for _ in range(256):
        if not floating(read(m,p))>floating(read(m,period)):break
        put(m,p,bits(floating(read(m,p))-floating(read(m,period))))
    else:raise LoopBudget
    active=floating(read(m,p))<=floating(read(m,threshold));m[owner+0x28]=int(active)
    calls=[(HELPER,(255,255,255,255))] if active else []
    if active and connected:
        for i in range(3):m[COLOR+i]=255
        put(m,DIRTY,1);m[PRIORITY]=255
    return m,calls


def public(m):
    return {a:b for a,b in m.items() if not STACK-2048<=a<STACK+512}


class PhaseOracle(RayOracle):
    def __init__(self,words,memory,owner=OWNER,phase=0,entry=source.ENTRY,connected=None,callbacks=(),fault=None,arguments=None):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,arguments=arguments or(owner,),connected=connected)
        self.callbacks=set(callbacks);self.steps=0;self.root_fault=fault

    def execute(self,word):
        self.steps+=1
        if self.steps>512:raise LoopBudget
        return super().execute(word)

    def record_call(self,target):
        n=4 if target==HELPER else 1
        assert target in self.callbacks or target in (source.ENTRY,HELPER,RELEASE),('unbounded callback',hex(target))
        args=self.arguments(n);self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        assert target in self.callbacks or target==RELEASE
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678


def controls():
    b=source.SELECTED[source.FUNCTION]
    return dict(selected=b,
        wrap_equal=b.replace('phase > cycle->period','phase >= cycle->period'),
        missing_step=b.replace('cycle->phase += D_800BE9A4;',''),
        wrong_threshold=b.replace('phase <= cycle->threshold','phase < cycle->threshold'),
        wrong_flag=b.replace('cycle->active = 1','cycle->active = 2'),
        wrong_color=b.replace('255, 255, 255, 255','254, 255, 255, 255'),
        missing_color=b.replace('        func_1515D4D4(255, 255, 255, 255);',''))


def fnv(data):
    h=2166136261
    for byte in data:h=((h^byte)*16777619)&0xFFFFFFFF
    return h


def native_harness(parent,helper):
    rows=[]
    # Expected byte images are computed independently in Python, not by a C twin.
    cases=list(corpus())
    for i,c in enumerate(cases):
        for selector in (47,-1,0,97):
            flags=0xA4|(i&1);life=(-1,0,32767)[i%3];ticks=(0,1,30)[i%3];destructor=(-1,0,9)[i%3]
            owner=bytearray((j*13+0xA5)&255 for j in range(64));owner[13]=flags
            struct.pack_into('<hbb',owner,14,life,destructor,selector)
            p,dt,period,threshold=c
            for at,value in ((0x2C,p),(0x30,threshold),(0x38,period)):struct.pack_into('<I',owner,at,value)
            color=bytearray((j*13+0xA5)&255 for j in range(96));color[7]=255;trace=[]
            if flags&1:life=((life-ticks+32768)&65535)-32768;struct.pack_into('<h',owner,14,life)
            if selector!=-1:
                trace.append(selector)
                if selector==47:
                    value=bits(floating(p)+floating(dt))
                    for _ in range(256):
                        if not floating(value)>floating(period):break
                        value=bits(floating(value)-floating(period))
                    else:raise LoopBudget
                    struct.pack_into('<I',owner,0x2C,value);active=floating(value)<=floating(threshold);owner[0x28]=int(active)
                    if active:
                        trace.append(500);color[:3]=b'\xff'*3;struct.pack_into('<I',color,0x5C,1);color[7]=255
            if life<0 and destructor!=-1:trace.append(100+destructor)
            if life<0:trace.append(200)
            row=(*c,selector,flags,(-1,0,32767)[i%3],ticks,destructor,fnv(owner+struct.pack('<I',dt)+color),len(trace),*(trace+[0]*4)[:4])
            values=[str(v) if v<0 else '0x%Xu'%v for v in row]
            rows.append('{'+','.join(values[:-4])+',{'+','.join(values[-4:])+'}}')
    text=source.HEADERS+source.DECLARATIONS+'''
typedef struct {struct260 header;u8 gap[0x28-sizeof(struct260)];PhaseCycle cycle;u8 tail[4];} NativeOwner;
typedef char phase_offset[__builtin_offsetof(NativeOwner,cycle)==0x28?1:-1];
typedef char owner_size[sizeof(NativeOwner)==64?1:-1];
static NativeOwner actual;f32 D_800BE9A4;s32 D_800BE9E4;
static u8 D_800DCD20[96];
#define D_800DCD27 D_800DCD20[7]
#define D_800DCD7C (*(s32*)(void*)(D_800DCD20+0x5C))
static u32 calls,trace[4],error;
static void capture(u32 id){if(calls>=4){error=1;return;}trace[calls++]=id;}
'''
    # Give the dirty word a declared s32 object, not a cast into a byte array.
    text=text.replace('static u8 D_800DCD20[96];','static union {s32 words[24];u8 bytes[96];} color;\n#define D_800DCD20 color.bytes')
    text=text.replace('(*(s32*)(void*)(D_800DCD20+0x5C))','color.words[23]')
    text+=helper.replace('func_1515D4D4','retained_color')+'\n'
    text+='void func_1515D4D4(s32 r,s32 g,s32 b,u8 priority){capture(500);retained_color(r,g,b,priority);}\n'
    for name,body in controls().items():text+=body.replace(source.FUNCTION,name)+'\n'
    text+='''typedef void(*Update)(struct260*);static Update update;
void(*D_8008A4E8[98])(struct260*);void(*D_8008A4C0[10])(struct260*);
static void slot0(struct260*p){if(p!=&actual.header)error=1;capture(0);}
static void slot97(struct260*p){if(p!=&actual.header)error=1;capture(97);}
static void slot47(struct260*p){capture(47);update(p);}
static void exit0(struct260*p){if(p!=&actual.header)error=1;capture(100);}
static void exit9(struct260*p){if(p!=&actual.header)error=1;capture(109);}
void func_1516972C(struct260*p){if(p!=&actual.header)error=1;capture(200);}
'''+parent+'''
typedef struct {u32 p,dt,period,threshold;s32 selector;u32 flags;s32 life,ticks,destructor;u32 hash,n,trace[4];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+'''};
typedef union {u32 u;f32 f;} Float;
static int variant(Update fn){u32 i,j,h;Float f;const Row*r;
 update=fn;D_8008A4E8[0]=slot0;D_8008A4E8[47]=slot47;D_8008A4E8[97]=slot97;D_8008A4C0[0]=exit0;D_8008A4C0[9]=exit9;
 for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
  r=rows+i;for(j=0;j<sizeof(actual);j++)((u8*)&actual)[j]=(u8)(j*13+0xA5);
  for(j=0;j<96;j++)color.bytes[j]=(u8)(j*13+0xA5);D_800DCD27=255;
  actual.header.unkD=(u8)r->flags;actual.header.unkE=(s16)r->life;actual.header.unk10=(s8)r->destructor;actual.header.unk11=(s8)r->selector;
  f.u=r->p;actual.cycle.phase=f.f;f.u=r->threshold;actual.cycle.threshold=f.f;f.u=r->period;actual.cycle.period=f.f;f.u=r->dt;D_800BE9A4=f.f;D_800BE9E4=r->ticks;
  calls=error=0;func_15149264(&actual.header);h=2166136261u;
  for(j=0;j<64;j++)h=(h^((u8*)&actual)[j])*16777619u;
  for(j=0;j<4;j++)h=(h^((u8*)&D_800BE9A4)[j])*16777619u;
  for(j=0;j<96;j++)h=(h^color.bytes[j])*16777619u;
  if(error||h!=r->hash||calls!=r->n)return 23;
  for(j=0;j<calls;j++)if(trace[j]!=r->trace[j])return 23;
 }return 0;}
int run(void){
'''
    for i,name in enumerate(controls()):text+=' if(variant(%s)!=%d)return %d;\n'%(name,0 if name=='selected' else 23,i+1)
    return text+' return 0;\n}\n'+START,len(rows)


class PhaseCycleGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.receipt={}
        if (ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        obj,diag=source.compile_owner(ROOT,cls.out,source.HEADERS+source.DECLARATIONS+source.SELECTED[source.FUNCTION],'fresh-selected')
        if diag:raise ValueError(diag)
        cls.obj=obj;data,fs=source.link_owner(ROOT,cls.out,obj,source.OWNER)
        cls.words=list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value']))
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>44I',cls.rom,source.ROM))
        cls.helper=list(struct.unpack_from('>19I',cls.rom,0x18A984));cls.parent=list(struct.unpack_from('>45I',cls.rom,0x176714))
        cls.table=list(struct.unpack_from('>98I',cls.rom,0x22EFA8));cls.exits=list(struct.unpack_from('>10I',cls.rom,0x22EF80))
        cls.connected={HELPER+i*4:w for i,w in enumerate(cls.helper)}

    def test_01_direct_words_owner_pools_and_actual_make(self):
        self.assertEqual(self.words,self.truth);raw,bindings=source.payload(self.obj,source.FUNCTION)
        self.assertEqual(bindings,source.BINDINGS)
        self.assertEqual(source.payload(source.original(ROOT,self.out,source.FUNCTION),source.FUNCTION),(raw,bindings))
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual(q['preserved_neighbors'],6)
        self.receipt.update(words=44,frame=24,bindings=3,new_guards=0,compiler_only=True,preserved_neighbors=6)

    def test_02_finite_rounding_aliases_and_executable_coverage(self):
        count=0;visits=set();skipped=0
        for c,owner,phase in itertools.product(corpus(),(OWNER,TIME-0x2C,TIME-0x38,TIME-0x30,COLOR-0x28),(0,8)):
            initial=fixture(c,owner)
            try:expected,calls=reference(initial,owner)
            except LoopBudget:skipped+=1;continue
            models=[PhaseOracle(w,initial,owner,phase,connected=self.connected).run() for w in (self.truth,self.words)]
            for m in models:
                self.assertEqual(public(m.memory),public(expected),(c,hex(owner)));self.assertEqual(m.calls,calls)
                self.assertEqual(m.r[29],STACK+phase);self.assertEqual(m.r[31],0xDEAD0000)
            self.assertEqual(complete(models[0]),complete(models[1]));visits.update(models[0].visits);count+=1
        root=set(range(source.ENTRY,source.ENTRY+176,4));dead=source.ENTRY+0x9C
        self.assertEqual(root-visits,{dead});self.assertTrue(set(self.connected)<=visits)
        self.receipt.update(finite_guest_phases=count,bounded_guest_cases_skipped=skipped,
            executable_root_words_visited=43,unreachable_duplicate_store_words=1,retained_helper_words_visited=19,
            guest_alias_layouts=5,stack_phases=2,FCSR_and_hardware_emulation_claimed=False)

    def test_03_malformed_loops_bounded_and_ordered_nan_comparisons(self):
        malformed=((bits(1),0,0,0),(bits(1),0,bits(-1),0),(0x7F800000,0,bits(1),0),(bits(1e30),0,bits(1),0))
        for c in malformed:
            initial=fixture(c);models=[]
            for w in (self.truth,self.words):
                m=PhaseOracle(w,initial,connected=self.connected)
                with self.assertRaises(LoopBudget):m.run()
                models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].steps,models[1].steps)
        for c in ((0x7FC00000,0,bits(1),0),(bits(1),0,0x7FC00000,bits(2)),(0,0,bits(1),0x7FC00000)):
            initial=fixture(c);expected,calls=reference(initial)
            m=PhaseOracle(self.words,initial,connected=self.connected).run()
            self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,calls)
        self.receipt.update(bounded_nonprogress_cases=4,ordered_nan_model_cases=3,native_malformed_loops_executed=False)

    def test_04_literal_fault_prefixes_and_saved_register_lifetime(self):
        count=0
        for c in ((bits(2),bits(.25),bits(1),bits(.5)),(bits(.75),0,bits(1),bits(.5))):
            initial=fixture(c);baseline=PhaseOracle(self.words,initial,connected=self.connected).run()
            for fault in range(baseline.root_accesses):
                models=[]
                for words in (self.truth,self.words):
                    m=PhaseOracle(words,initial,connected=self.connected,fault=fault)
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt.update(root_access_fault_prefixes=count,complete_private_guest_state_equal=True)

    def test_05_registered_callback_complete_parent_and_color_chain(self):
        ptr=struct.pack('>I',source.ENTRY);jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4) if self.rom[i:i+4]==ptr],[0x22F064])
        self.assertFalse(any(self.rom[i:i+4]==jal for i in range(0,len(self.rom),4)))
        self.assertEqual(self.table[47],source.ENTRY);old=self.values['conker/build/conker.us.elf']
        for entry,words in ((PARENT,self.parent),(HELPER,self.helper)):
            at=source.elf_slot_offset(old,entry,len(words)*4)
            self.assertEqual(list(struct.unpack_from('>%dI'%len(words),old,at)),words)
        visits=set();count=0
        for selector,destructor,flags,life,ticks,active in itertools.product((-1,0,47,97),(-1,0,9),(0xA4,0xA5),(-1,0,32767),(0,1,30),(False,True)):
            c=(bits(.75),0,bits(1),bits(1 if active else .5));m=fixture(c)
            m[OWNER+17]=selector&255;m[OWNER+16]=destructor&255;m[OWNER+13]=flags;put(m,OWNER+14,life,2);put(m,TICKS,ticks)
            for i,v in enumerate(self.table):put(m,TABLE+4*i,v)
            for i,v in enumerate(self.exits):put(m,EXIT_TABLE+4*i,v)
            expected=dict(m);calls=[]
            if flags&1:put(expected,OWNER+14,(life-ticks)&65535,2)
            if selector!=-1:
                calls.append((self.table[selector],(OWNER,)))
                if selector==47:expected,more=reference(expected);calls+=more
            if read(expected,OWNER+14,2)&0x8000:
                if destructor!=-1:calls.append((self.exits[destructor],(OWNER,)))
                calls.append((RELEASE,(OWNER,)))
            models=[]
            for words in (self.truth,self.words):
                connected={**self.connected,**{source.ENTRY+4*i:w for i,w in enumerate(words)}}
                model=PhaseOracle(self.parent,m,entry=PARENT,connected=connected,callbacks=self.table+self.exits).run()
                self.assertEqual(public(model.memory),public(expected));self.assertEqual(model.calls,calls)
                visits.update(model.visits);models.append(model)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(PARENT,PARENT+180,4))<=visits)
        self.receipt.update(actual_parent_words=45,actual_parent_phases=count,registration_index=47,
            update_table_entries=98,destructor_entries=10,all_parent_words_visited=True,other_callbacks_and_release_bounded=True)

    def test_06_native_connected_parent_root_and_actual_helper(self):
        text=self.values['conker/src/game/done/game_1765E0.c'].decode();lo,hi=source.function_span(text,'func_15149264');parent=text[lo:hi]
        text=self.values['conker/src/game/generated_18A8F0.c'].decode();lo,hi=source.function_span(text,'func_1515D4D4');helper=text[lo:hi]
        harness,count=native_harness(parent,helper);unit=self.out/'native32.c';unit.write_text(harness)
        for opt in ('-O0','-O2','-O3'):
            exe=self.out/('native32'+opt);p=subprocess.run([*native_command(opt),str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,(p.stdout+p.stderr)[:12000])
            p=subprocess.run([str(exe)],capture_output=True,timeout=90);self.assertEqual(p.returncode,0,(opt,p.stdout,p.stderr))
        self.receipt.update(native_connected_cases_per_optimization=count,native_optimizations=['O0','O2','O3'],
            effective_wrong_C_controls=6,trap_UBSan=True,full_64_byte_owner_storage=True,typed_callback_ABI=True,
            independently_generated_native_expected_images=True,native_alias_cases_claimed=False)

    def test_07_native_actual_parent_all_slots_and_controls(self):
        text=self.values['conker/src/game/done/game_1765E0.c'].decode();lo,hi=source.function_span(text,'func_15149264')
        unit=self.out/'native-parent.c';unit.write_text(parent_harness(text[lo:hi]))
        for opt in ('-O0','-O2','-O3'):
            exe=self.out/('native-parent'+opt);p=subprocess.run([*native_command(opt),str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=90).returncode,0,opt)
        self.receipt.update(fresh_native_parent_all_98_slots=True,fresh_native_parent_controls=3)

    def test_08_strict_image_and_unchanged_guards_fail_closed(self):
        bodies=source.truths(self.values);before=self.values['conker/build/conker.us.elf'];expected=source.predicted_image(before,bodies)
        self.assertEqual(expected,(self.out/'first-linked.elf').read_bytes())
        for at in (0,len(expected)-1,source.elf_slot_offset(expected,source.ENTRY,176)):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),bodies)
        bad=dict(bodies);bad[source.FUNCTION]=bytes(176)
        with self.assertRaises(ValueError):source.predicted_image(before,bad)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
        self.receipt.update(strict_image_negative_controls=4,metadata_exclusions=0,guard_file_unchanged=True)
