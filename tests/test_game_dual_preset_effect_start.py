"""Effect-group restart: direct body, argument homes, original caller and bounded helpers."""
import itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_dual_preset_effect_start as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command

ROOT=Path(__file__).resolve().parents[2]
ENTRY,RESET,EFFECT,FACTORY=0x1519E3BC,0x1519E688,0x1519D030,0x151491F4
BYTE,DISPATCH,SUBMIT,CORE,CALLER=0x1519CF70,0x15147D64,0x15169260,0x15149130,0x1519E754
ACTOR,OTHER,RESULT,CONTROL=0x20000,0x22000,0x24000,0x26000
TICKS,SLOT,TABLE=0x800BE9E4,0x800E0920,0x800A5760
ANCHORS=dict(func_1519E688=RESET,func_1519D030=EFFECT,func_151491F4=FACTORY)
WORDS=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x87654321)


def half(w):
    return ((w&65535)^0x8000)-0x8000


def fixture(phase=0):
    m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-0x900,0x200)}
    for b in (ACTOR,OTHER,RESULT,CONTROL):m.update({b+i:0xA5 for i in range(256)})
    put(m,TICKS,1);put(m,SLOT,0x87654321)
    return m


def public(m):
    return {a:v for a,v in m.items()if not STACK-0x900<=a<STACK+0x300}


def effect(m,sp,stage,mode):
    if mode==1:put(m,ACTOR+4,0x12340000+stage)
    elif mode==2:
        for i,v in enumerate((OTHER+stage*16,0xABCD8001+stage,0x998877EE+stage,0x87654321+stage)):
            put(m,sp+i*4,v)
    elif mode==3:
        put(m,sp,0 if stage==0 else OTHER);put(m,sp+8,0xAB000000|(stage*71&255))


def reference(memory,args,sp,mode=0):
    m=dict(memory);calls=[];trace=[]
    def wr(a,v,n=4):put(m,a,v,n);trace.append(('W',a,n,v&((1<<(8*n))-1)))
    def rd(a,n=4):
        v=read(m,a,n);trace.append(('R',a,n,v));return v
    wr(sp-4,0xDEAD0000)
    for i,v in enumerate(args):wr(sp+i*4,v)
    calls.append((RESET,()));effect(m,sp,0,mode)
    for stage,preset in enumerate((3,4),1):
        slot=rd(sp+11,1);ctx=rd(sp+12);actor=rd(sp)
        wr(sp-40+16,slot);wr(sp-40+20,ctx)
        calls.append((EFFECT,(actor,preset,300,0,slot,ctx)));effect(m,sp,stage,mode)
    slot=rd(sp+11,1);ctx=rd(sp+12);wr(sp-40+16,3)
    duration=half(rd(sp+6,2))&0xFFFFFFFF
    wr(sp-40+20,0);wr(sp-40+24,slot);wr(sp-40+28,ctx)
    calls.append((FACTORY,(duration,6,0xFFFFFFFF,1,3,0,slot,ctx)));effect(m,sp,3,mode)
    rd(sp-4)
    return m,calls,trace


class StartOracle(TimingOracle):
    def __init__(self,words,memory,args,phase=0,mode=0,result=RESULT,entry=ENTRY,connected=None,anchors=None):
        self.trace=[];self.in_provider=True;self.effect_mode=mode;self.result=result
        self.anchors=anchors or ANCHORS;self.root_sp=STACK+phase;self.effect_calls=0;self.submissions=[]
        self.root_address=ENTRY if entry==CALLER else entry
        super().__init__(words,memory,phase=phase,entry=entry,arguments=args,connected=connected)
        self.in_provider=False
    def root_instruction(self):
        return self.own_instruction and not self.in_provider and self.root_address<=self.current_pc<self.root_address+168
    def get(self,address,size):
        v=super().get(address,size)
        if self.root_instruction():self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.root_instruction():self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def execute(self,word):
        if word>>26==32:
            rs,rt,imm=word>>21&31,word>>16&31,word&65535
            a=(self.r[rs]+(imm if imm<32768 else imm-65536))&0xFFFFFFFF
            v=self.get(a,1);self.r[rt]=(v if v<128 else v|0xFFFFFF00)
        else:super().execute(word)
    def record_call(self,target):
        canonical={v:{'func_1519E688':RESET,'func_1519D030':EFFECT,'func_151491F4':FACTORY}[k]for k,v in self.anchors.items()}.get(target,target)
        widths={ENTRY:4,RESET:0,EFFECT:6,FACTORY:8,CORE:9,BYTE:1,DISPATCH:2,SUBMIT:4}
        self.in_provider=True;args=self.arguments(widths[canonical]);self.in_provider=False
        self.calls.append((canonical,args));self.events.append(('CALL',canonical,args))
        if canonical==ENTRY:self.root_sp=self.r[29]
        if canonical==EFFECT:self.effect_calls+=1
        if canonical==SUBMIT:
            self.submissions.append((self.memory[args[2]] if args[3]==6 else None,args[3]))
    def hook(self,target):
        canonical,args=self.calls[-1];self.in_provider=True
        if canonical==RESET:effect(self.memory,self.root_sp,0,self.effect_mode)
        elif canonical==EFFECT:effect(self.memory,self.root_sp,self.effect_calls,self.effect_mode)
        elif canonical in (FACTORY,CORE):effect(self.memory,self.root_sp,3,self.effect_mode)
        elif canonical==SUBMIT:
            if args[3]==9:effect(self.memory,self.root_sp,0,self.effect_mode)
        else:raise AssertionError(hex(canonical))
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678
        self.r[2]=self.result if canonical in (FACTORY,CORE)else (0,0xFFFFFFFF,0x81234567)[self.effect_calls%3]
        self.in_provider=False


def native_harness(bodies,helper_source,runner):
    return '#include <ultra64.h>\n#include "structs.h"\n'+r'''
static u8 actorBytes[256];static struct260 objects[2];
static u32 bad,calls,submitted,slotWord,contextWord,plan;static s16 wantedDuration;static u8*wantedActor;
typedef char Width[(sizeof(void*)==4&&sizeof(s32)==4)?1:-1];
void func_15147D64(void*p,u8 kind){
 const u8 codes[]={3,4};
 if(submitted<2){if(kind!=6||p==0||*(u8*)p!=codes[submitted])bad=1;}
 else if(submitted!=2||kind!=9||p!=0)bad=1;
 submitted++;}
'''+helper_source+r'''
void func_1519E688(void){if(calls!=0)bad=1;calls++;actual_reset();}
s32 func_1519D030(u8*p,s32 preset,s16 duration,u8 active,u8 slot,s32 context){
 if(calls<1||calls>2||p!=wantedActor||preset!=(s32)(calls+2)||duration!=300||active||slot!=(u8)slotWord||(u32)context!=contextWord)bad=1;
 calls++;return plan==0?0:plan==1?(s32)0xFFFFFFFFu:(s32)0x81234567u;}
struct260 *func_151491F4(s16 duration,s8 first,s8 second,u8 flags,u8 kind,s32 size,u8 slot,s32 context){
 if(calls!=3||duration!=wantedDuration||first!=6||second!=-1||flags!=1||kind!=3||size||slot!=(u8)slotWord||(u32)context!=contextWord)bad=1;
 calls++;return plan==0?0:objects+plan-1;}
'''+bodies+r'''
static int runVariant(void(*target)(u8*,s16,u8,s32)){
 const u32 durations[]={0,1,0x7FFFu,0x8000u,0xFFFFu,0xABCD8001u};
 const u32 contexts[]={0,1,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu,0x87654321u};
 u32 d,c,slot,p,i,n=0;u8*all=(u8*)objects;
 for(d=0;d<6;d++)for(c=0;c<6;c++)for(slot=0;slot<256;slot++)for(p=0;p<2;p++)for(plan=0;plan<3;plan++){
  wantedDuration=(s16)durations[d];contextWord=contexts[c];slotWord=0xABCD0000u|slot;wantedActor=p?actorBytes:0;
  for(i=0;i<sizeof(objects);i++)all[i]=(u8)(i*13+0xA5);
  bad=calls=submitted=0;target(wantedActor,wantedDuration,(u8)slotWord,(s32)contextWord);
  if(bad||calls!=4||submitted!=3)return 23;
  for(i=0;i<sizeof(objects);i++)if(all[i]!=(u8)(i*13+0xA5))return 23;n++;
 }return n==55296u?0:24;}
'''+runner+r'''
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''


class DualPresetEffectStartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.out.mkdir(parents=True,exist_ok=True);cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_text()==source.recovered_owner(cls.values[source.SOURCE].decode())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin']
        cls.obj,diag=source.compile_owner(ROOT,cls.out,source.ISOLATED_HEADER+source.DECLARATIONS+source.SELECTED[source.FUNCTIONS[0]],'fresh-selected')
        if diag:raise ValueError(diag)
        cls.truth=list(struct.unpack_from('>42I',cls.rom,0x1CB86C));cls.raw=cls.link_words(cls.obj,ENTRY,ANCHORS,'fresh-link')
        cls.helper_specs=((RESET,0x1CBB38,13),(BYTE,0x1CA420,12),(DISPATCH,0x175214,13),(FACTORY,0x1766A4,28),(EFFECT,0x1CA4E0,132),(CALLER,0x1CBC04,49))
        cls.helpers={e:list(struct.unpack_from('>%dI'%n,cls.rom,o))for e,o,n in cls.helper_specs}
        text=cls.values[source.SOURCE].decode();parts=[]
        for name in ('func_1519CF70','func_1519E688'):
            a,b=source.function_span(text,name);parts.append(text[a:b].replace('func_1519E688','actual_reset'))
        cls.native_helpers='\n'.join(parts);cls.receipt=dict(installed=cls.installed)
    @classmethod
    def link_words(cls,obj,entry,anchors,label):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        t,fs,rs=source.parse_object(obj);asm,unknown=emit_function(t,fs[source.FUNCTIONS[0]],rs,source.FUNCTIONS[0],anchors);assert not unknown
        p=cls.out/label;ap=p.with_suffix('.s');op=p.with_suffix('.o');ld=p.with_suffix('.ld');elf=p.with_suffix('.elf')
        ap.write_text(asm);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(op),str(ap)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),*['--defsym=%s=0x%X'%(k,v)for k,v in anchors.items()],'-e',source.FUNCTIONS[0],'-o',str(elf),str(op)],capture_output=True,check=True)
        return list(struct.unpack_from('>42I',sections(elf)['.text'][1]))
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)
    def compare(self,args,phase=0,mode=0,result=RESULT):
        memory=fixture(phase);expected,calls,trace=reference(memory,args,STACK+phase,mode)
        models=[StartOracle(code,memory,args,phase,mode,result).run()for code in (self.truth,self.raw)]
        for m in models:
            self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,calls);self.assertEqual(m.r[2],result);self.assertEqual(m.trace,trace)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0]
    def test_01_direct_GNU_owner_Make_and_old_stub(self):
        self.assertEqual(self.truth,self.raw)
        self.assertEqual(source.payload(self.obj,source.FUNCTIONS[0]),source.payload(source.original(ROOT,self.out,source.FUNCTIONS[0]),source.FUNCTIONS[0]))
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['total_words'],q['new_guards'],q['compiler_only']),(42,0,True))
        m=fixture();args=(ACTOR,300,255,0x87654321)
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,ENTRY,168)
        stub=StartOracle(struct.unpack_from('>42I',old,at),m,args).run();self.assertNotEqual(stub.calls,reference(m,args,STACK)[1])
        at=source.elf_slot_offset(old,EFFECT,12);self.assertEqual(list(struct.unpack_from('>3I',old,at)),[0x00001025,0x03E00008,0])
        self.receipt.update(words=42,frame=40,bindings=4,new_guards=0,neighbors=q['preserved_neighbors'],unmatched_effect_stub_unchanged=True,old_stub_effectively_rejected=True)
    def test_02_byte_widths_signed_duration_returns_and_late_homes(self):
        count=0;seen=set()
        for byte,upper,duration,mode,phase in itertools.product(range(256),(0,0xABCD0000),(0,0x12347FFF,0xABCD8000,0xFFFFFFFF),range(4),(0,8)):
            args=(ACTOR,duration,upper|byte,WORDS[(byte+mode)%6])
            m=self.compare(args,phase,mode,(0,RESULT,OTHER,0xFFFFFFFF)[mode]);seen.update(m.visits);count+=1
        nulls=0
        for duration,slot,phase in itertools.product(WORDS,WORDS,(0,8)):
            self.compare((0,duration,slot,0x80000000),phase);nulls+=1
        self.assertEqual(seen,set(range(ENTRY,ENTRY+168,4)))
        self.receipt.update(guest_phases=count,null_actor_phases=nulls,reachable_words=42,all_four_original_homes_preserved=True,late_home_mutations=True,factory_V0_retained_but_caller_ignores_it=True)
    def test_03_native32_actual_reset_body_and_wrong_C_batch(self):
        body=source.SELECTED[source.FUNCTIONS[0]]
        changes=(('first','actor, 3, 300','actor, 2, 300'),('second','actor, 4, 300','actor, 5, 300'),
          ('reset-order','    func_1519E688();',''),('duration','func_151491F4(duration','func_151491F4((s8)duration'),
          ('flags','duration, 6, -1, 1, 3','duration, 6, -1, 0, 3'),('slot','3, 0, slot, context','3, 0, (u8)(slot ^ 1), context'),
          ('context',', context);',', (u8)context);'),('NULL-skip','    func_1519D030(actor, 3','    if (actor != NULL) func_1519D030(actor, 3'))
        bodies=[body];names=[source.FUNCTIONS[0]]
        for i,(label,a,b)in enumerate(changes):
            self.assertIn(a,body);name=source.FUNCTIONS[0]+'_control'+str(i)
            bodies.append(body.replace(a,b).replace(source.FUNCTIONS[0],name));names.append(name)
        runner='static int run(void){int r;'+''.join('r=runVariant(%s);if(r!=%d)return %d;'%(n,0 if i==0 else 23,80+i)for i,n in enumerate(names))+'return 0;}'
        for opt in ('-O0','-O2','-O3'):
            p=self.out/('native-batch'+opt+'.c');exe=p.with_suffix('.elf');p.write_text(native_harness('\n'.join(bodies),self.native_helpers,runner))
            q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(q.returncode,0,q.stderr);self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=30).returncode,0)
        self.receipt.update(native_cases_per_optimization=55296,native_optimizations=3,trap_UBSan=True,effective_wrong_C_controls=8,controls_each_optimization=True,native_compile_invocations=3,actual_reset_and_byte_helpers=True,dispatcher_provider_pointer_view=True)
    def test_04_original_full_caller_and_static_references(self):
        jal=struct.pack('>I',0x0C000000|(ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0x1CBC88])
        self.assertFalse(any(self.rom[i:i+4]==struct.pack('>I',ENTRY)for i in range(0,len(self.rom),4)))
        count=0;seen=set()
        for empty,match,kind,timer,ticks,phase in itertools.product((0,1),(0,1),(0x7C,0x84),(0,200,201,0x7FFFFFFF),(0,1,0xFFFFFFFF),(0,8)):
            memory=fixture(phase);actor=ACTOR
            put(memory,CONTROL+0x28,actor);put(memory,actor,0 if empty else 1)
            memory[CONTROL+0x2C]=2 if match else 3;memory[actor+0x3B]=2
            put(memory,actor+0x84,kind,2);put(memory,CONTROL+0x30,timer);put(memory,TICKS,ticks)
            memory[CONTROL+0xC]=0xE7;memory[CONTROL+1]=0x91;memory[CONTROL+0xD]=0xA4;put(memory,CONTROL+0xE,0x1234,2)
            models=[]
            for code in (self.truth,self.raw):
                connected=dict(zip(range(ENTRY,ENTRY+168,4),code));m=StartOracle(self.helpers[CALLER],memory,(CONTROL,),phase,entry=CALLER,connected=connected).run();models.append(m);seen.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));m=models[0]
            total=(timer+ticks)&0xFFFFFFFF;fire=not empty and match and kind!=0x7C and signed(total)>=201
            stop=bool(empty or not match or kind!=0x7C)
            self.assertEqual([x for x in m.calls if x[0]==ENTRY],[(ENTRY,(actor,300,0xE7,0x91))]if fire else [])
            self.assertEqual(read(m.memory,SLOT),0 if stop else 0x87654321)
            self.assertEqual(read(m.memory,CONTROL+0x30),total if not empty and match else timer)
            self.assertEqual(read(m.memory,CONTROL+0xE,2),0xFFFF if stop else 0x1234);count+=1
            self.assertEqual(m.memory[CONTROL+0xD],0xA5 if stop else 0xA4)
            if not empty and match and kind!=0x7C:self.assertIn(0x1519E7C8,m.visits)
        self.assertTrue(set(range(CALLER,CALLER+196,4))<=seen)
        before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,CALLER,12)
        self.assertEqual(list(struct.unpack_from('>3I',before,at)),[0x00001025,0x03E00008,0])
        self.receipt.update(original_caller_words=49,caller_phases=count,all_original_caller_words_visited=True,current_caller_still_stub=True,inline_descriptor_and_backed_actor=True,actor_header_zero_is_not_a_NULL_pointer_test=True,timer_branch_delay_sets_cleanup_flag=True)
    def test_05_actual_reset_chain_factory_and_effect_NULL_gate(self):
        old=self.values['conker/build/conker.us.elf'];seen=set();count=0
        current=(RESET,BYTE,DISPATCH,FACTORY)
        for e,rom,n in self.helper_specs:
            if e in current:
                at=source.elf_slot_offset(old,e,n*4);self.assertEqual(self.helpers[e],list(struct.unpack_from('>%dI'%n,old,at)))
        for null,result,phase in itertools.product((0,1),(0,RESULT,OTHER),(0,8)):
            connected={pc:w for e in current for pc,w in zip(range(e,e+len(self.helpers[e])*4,4),self.helpers[e])}
            if null:connected.update(zip(range(EFFECT,EFFECT+528,4),self.helpers[EFFECT]))
            args=(0 if null else ACTOR,0xABCD8001,0x998877EE,0x87654321);memory=fixture(phase);models=[]
            for code in (self.truth,self.raw):
                m=StartOracle(code,memory,args,phase,result=result,connected=connected).run();models.append(m);seen.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));m=models[0]
            self.assertEqual([x for x in m.calls if x[0]in(RESET,EFFECT,FACTORY)],reference(memory,args,STACK+phase)[1])
            self.assertEqual(m.submissions,[(3,6),(4,6),(None,9)])
            self.assertEqual([x[1]for x in m.calls if x[0]==CORE],[(0xFFFF8001,6,0xFFFFFFFF,0xFFFFFFFF,1,3,0,0xEE,0x87654321)])
            self.assertEqual(m.r[2],result);count+=1
        for e in current:self.assertTrue(set(range(e,e+len(self.helpers[e])*4,4))<=seen)
        self.receipt.update(connected_helper_phases=count,reset_words=13,byte_words=12,dispatcher_words=13,factory_words=28,all_connected_wrapper_words_visited=True,original_effect_NULL_visited_words=sum(e in seen for e in range(EFFECT,EFFECT+528,4)),effect_non_NULL_body_not_emulated=True,core_and_submit_providers_bounded=True)
    def test_06_rebased_links_and_fired_root_fault_prefixes(self):
        original=source.original(ROOT,self.out,source.FUNCTIONS[0]);links=cuts=0
        for i in range(3):
            entry=0x17001000+i*0x10000;syms=dict(func_1519E688=0x17107FFC+i*0x20000,func_1519D030=0x17208000+i*0x20000,func_151491F4=0x1730FFFC+i*0x20000)
            images=[self.link_words(o,entry,syms,'rebase-%s-%d'%(n,i))for n,o in (('original',original),('C',self.obj))]
            self.assertEqual(*images);links+=2
            for mode in range(4):
                args=(ACTOR,0xABCD8001,0xFFFF00EE,0x87654321);memory=fixture();models=[StartOracle(w,memory,args,mode=mode,entry=entry,anchors=syms).run()for w in images]
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].calls,reference(memory,args,STACK,mode)[1])
        for phase,mode in itertools.product((0,8),range(4)):
            args=(ACTOR,0xABCD8001,0xFFFF00EE,0x87654321);memory=fixture(phase);good=StartOracle(self.truth,memory,args,phase,mode).run()
            for cut in range(good.root_accesses):
                models=[StartOracle(w,memory,args,phase,mode)for w in (self.truth,self.raw)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=links,fired_root_fault_prefixes=cuts,portable_C_fault_MMU_claimed=False)
    def test_07_strict_image_corruptions_and_unchanged_guards(self):
        before=self.values['conker/build/conker.us.elf'];pred=source.predicted_image(before,self.rom)
        for at in (0,len(pred)-1,source.elf_slot_offset(pred,ENTRY,168),source.elf_slot_offset(pred,EFFECT,12),source.elf_slot_offset(pred,0x80082B20,4)):
            b=bytearray(pred);b[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(b),self.rom)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
        self.receipt.update(strict_image_corruption_controls=5,metadata_exclusions=0,entire_guard_manifest_unchanged=True)
    def test_08_pinned_inputs_and_installed_identity(self):
        for name,old in self.values.items():
            self.assertEqual(source.digest(old),source.INPUTS[name])
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else source.predicted_image(old,self.rom)if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),expected,name)
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(pinned_inputs=len(self.values),old_object_pinned=True)


if __name__=='__main__':unittest.main()
