"""Alternate descriptor callback, real dispatcher/release bounds and checked branch fit."""
from dataclasses import dataclass
import csv,io,itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_alternate_pair_command as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command

ROOT=Path(__file__).resolve().parents[2]
ENTRY,ACTOR,STATE,EVENT,ALT=0x151A8A78,0x20000,0x22000,0x24000,0x26000
PARENT,TABLE,HELPER,PRE,FALLBACK,CALLBACK,HELPER_TABLE=0x151A8A20,0x8008F964,0x1516972C,0x151696DC,0x15169804,0x17100000,0x8008B4D0
OTHER=0x150F07E4
WORDS=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678)


@dataclass(frozen=True)
class Case:
    command:int=45
    relation:int=0
    pattern:int=0
    alias:int=0
    mode:int=0


def fixture(c,phase=0):
    m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-0x400,0x180)}
    for b,n in ((ACTOR-16,0xB0),(STATE-16,80),(EVENT-16,80),(ALT-16,80),(TABLE,12)):
        m.update({b+i:0xA5 for i in range(n)})
    state=ACTOR+0x60 if c.alias==5 else STACK+phase+8 if c.alias==6 else STATE
    event={1:STATE,2:STATE+4,3:STATE-4,4:ACTOR+0x60,7:STACK+phase+8}.get(c.alias,EVENT)
    first=WORDS[c.pattern%len(WORDS)];second=first^0x87654321
    put(m,event,first);put(m,event+4,second);m[event+8]=0x12;m[event+9]=0xE7
    put(m,ACTOR+0x60,state)
    first,second=read(m,event),read(m,event+4)
    put(m,state,first if c.relation in (0,3)else second if c.relation==1 else first^second^0xB5B5B5B5)
    if c.alias==5:put(m,ACTOR+0x60,state)
    m[state+4]=(m[event+4] if c.relation==3 else m[event+4]^1)
    m[ACTOR+0x5C]=1;m[ACTOR]=2
    for i,w in enumerate((0,OTHER,ENTRY)):put(m,TABLE+i*4,w)
    for i in range(256):put(m,HELPER_TABLE+i*52,0)
    return m,event


def public(memory):
    return {a:v for a,v in memory.items()if not STACK-0x400<=a<STACK+0x200}


def effects(memory,actor,mode):
    if mode&1:memory[actor+0x31]^=0x55
    if mode&2:put(memory,actor+0x60,ALT)


def reference(memory,args,mode=0,sp=STACK,ra=0xDEAD0000):
    m=dict(memory);actor,event,command=args;trace=[];calls=[]
    def wr(a,w,n=4):
        put(m,a,w,n);trace.append(('W',a,n,w&((1<<(8*n))-1)))
    def rd(a,n=4):
        w=read(m,a,n);trace.append(('R',a,n,w));return w
    wr(sp+8,command);wr(sp-4,ra)
    state=rd(actor+0x60);command&=255
    if command==0:
        first=rd(event);value=rd(state)
        if first==value or rd(event+4,1)==rd(state+4,1):
            calls.append((HELPER,(actor,)));effects(m,actor,mode)
    elif command==45:
        first=rd(event);value=rd(state)
        if first==value:
            wr(state,rd(event+4));wr(state+4,rd(event+9,1),1)
        elif rd(event+4)==value:
            wr(state,first);wr(state+4,rd(event+8,1),1)
    return m,calls,trace


class CommandOracle(TimingOracle):
    def __init__(self,words,memory,args,phase=0,mode=0,entry=ENTRY,connected=None,helper=HELPER):
        self.trace=[];self.effect_mode=mode;self.helper_address=helper
        super().__init__(words,memory,phase=phase,entry=entry,arguments=args,connected=connected)
    def get(self,address,size):
        w=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,w))
        return w
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        if target==self.helper_address:target=HELPER
        assert target in (ENTRY,HELPER,PRE,FALLBACK,CALLBACK,OTHER),hex(target)
        args=self.arguments(3 if target in (ENTRY,OTHER)else 1)
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        if target==self.helper_address:target=HELPER
        assert target in (HELPER,PRE,FALLBACK,CALLBACK,OTHER)
        actor=self.calls[-1][1][0]
        effects(self.memory,actor,self.effect_mode)
        if target==PRE and self.effect_mode&4:self.memory[actor]=2
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x12345678,0x87654321


def native_harness(body,parent):
    return '#include <ultra64.h>\n#include "structs.h"\n'+r'''
typedef union{u32 align;s32 words[8];u8 bytes[32];}Pair;
typedef struct{u8 prefix[0x60];u8*state;u8*alternate;u8 tail[0x10];}Owner;
typedef struct{u32 before[4];Owner owner;Pair state,event,alt;u32 after[4];}Arena;
typedef char Width[(sizeof(void*)==4&&sizeof(s32)==4&&__builtin_offsetof(Owner,state)==0x60)?1:-1];
static Arena arena,expected;static u32 calls,last,mode;
static void effect(u8*p){if(mode&1)p[0x31]^=0x55;}
void func_1516972C(struct102*p){calls++;last=(u32)p;effect((u8*)p);}
static void other(u8*p,s32 event,u8 command){calls++;last=(u32)p;effect(p);}
static void(*D_8008F964[3])(u8*,s32,u8);
'''+body+'\n'+parent+r'''
static u32 rd(u8*b,u32 at){union{u32 w;u8 b[4];}v;u32 i;for(i=0;i<4;i++)v.b[i]=b[at+i];return v.w;}
static void wr(u8*b,u32 at,u32 w){union{u32 w;u8 b[4];}v;u32 i;v.w=w;for(i=0;i<4;i++)b[at+i]=v.b[i];}
static int runVariant(void(*target)(u8*,s32,u8)){u32 j,iface,command,relation,pattern,alias,effectPlan,at,st,first,value,selected,want,count=0;
 u8*a=(u8*)&arena,*b=(u8*)&expected,*owner=(u8*)&arena.owner,*event,*state;
 const u32 words[]={0,0x80000000u,0xFFFFFFFFu,0x12345678u};const u8 slots[]={0,2,1,3,255};
 D_8008F964[0]=0;D_8008F964[1]=other;D_8008F964[2]=target;
 for(iface=0;iface<6;iface++)for(command=0;command<256;command++)for(relation=0;relation<4;relation++)
 for(pattern=0;pattern<4;pattern++)for(alias=0;alias<3;alias++)for(effectPlan=0;effectPlan<2;effectPlan++){
  for(j=0;j<sizeof(Arena);j++)a[j]=(u8)(j*13+0xA5);
  state=arena.state.bytes;event=alias==0?arena.event.bytes:state+(alias==1?0:4);
  arena.owner.state=state;arena.owner.alternate=arena.alt.bytes;
  wr(event,0,words[pattern]);wr(event,4,words[pattern]^0x87654321u);event[8]=0x12;event[9]=0xE7;
  first=rd(event,0);value=rd(event,4);wr(state,0,relation==0||relation==3?first:relation==1?value:first^value^0xB5B5B5B5u);
  state[4]=(u8)(event[4]^(relation==3?0:1));owner[0x5C]=iface?slots[iface-1]:2;
  mode=effectPlan;calls=last=0;for(j=0;j<sizeof(Arena);j++)b[j]=a[j];
  at=(u32)(event-a);st=(u32)(state-a);selected=iface?owner[0x5C]:2;if(selected>=3)selected=0;want=0;
  if(selected==2){
   first=rd(b,at);value=rd(b,st);
   if(command==0){if(first==value||b[st+4]==b[at+4])want=1;}
   else if(command==45){if(first==value){wr(b,st,rd(b,at+4));b[st+4]=b[at+9];}
    else if(rd(b,at+4)==value){wr(b,st,first);b[st+4]=b[at+8];}}
  }else if(selected==1)want=1;
  if(want&&mode&1)((u8*)&expected.owner)[0x31]^=0x55;
  if(iface)func_151A8A20(owner,(s32)event,(u8)command);else target(owner,(s32)event,(u8)command);
  if(calls!=want||(want&&last!=(u32)owner))return 23;
  for(j=0;j<sizeof(Arena);j++)if(a[j]!=b[j])return 23;count++;
 }
 return count==147456u?0:24;}
BATCH_RUNNER
void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


class AlternatePairCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.out.mkdir(parents=True,exist_ok=True)
        cls.installed=(ROOT/source.SOURCE).read_text()==source.recovered_owner(source.snapshot(cls.out)[source.SOURCE].decode())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED[source.FUNCTIONS[0]],'fresh-selected')
        if diag:raise ValueError(diag)
        raw,bindings=source.payload(cls.obj,source.FUNCTIONS[0]);fitted,_=source.normalized(raw,bindings)
        cls.raw=cls.link_words(cls.obj,ENTRY,HELPER,'fresh-link')
        cls.truth=list(struct.unpack_from('>42I',cls.rom,0x1D5F28));cls.fitted=list(cls.raw);cls.fitted[33]=struct.unpack_from('>I',fitted,132)[0]
        before=cls.values['conker/src/game/generated_1D4E00.c'].decode();lo,hi=source.function_span(before,'func_151A8A20');cls.parent_source=before[lo:hi]
        cls.parent=list(struct.unpack_from('>22I',cls.rom,0x1D5ED0));cls.helper=list(struct.unpack_from('>28I',cls.rom,0x196BDC))
        cls.receipt=dict(installed=cls.installed)
    @classmethod
    def link_words(cls,obj,entry,helper,label):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        text,fs,rs=source.parse_object(obj);asm,unknown=emit_function(text,fs[source.FUNCTIONS[0]],rs,source.FUNCTIONS[0],dict(func_1516972C=helper));assert not unknown
        stem=cls.out/label;ap=stem.with_suffix('.s');op=stem.with_suffix('.o');lp=stem.with_suffix('.ld');ep=stem.with_suffix('.elf')
        ap.write_text(asm);lp.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(op),str(ap)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(lp),'--defsym=func_1516972C=0x%X'%helper,'-e',source.FUNCTIONS[0],'-o',str(ep),str(op)],capture_output=True,check=True)
        return list(struct.unpack_from('>42I',sections(ep)['.text'][1]))
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)
    def compare(self,c,phase=0,images=None,entry=ENTRY):
        memory,event=fixture(c,phase);args=(ACTOR,event,c.command)
        expected,calls,trace=reference(memory,args,c.mode,STACK+phase)
        models=[CommandOracle(w,memory,args,phase,c.mode,entry).run()for w in images or (self.truth,self.raw,self.fitted)]
        for m in models:
            self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,calls)
            observed=[x for x in m.trace if not STACK-0x400<=x[1]<STACK+0x200]
            self.assertEqual(observed,[x for x in trace if not STACK-0x400<=x[1]<STACK+0x200])
        for m in models[1:]:self.assertEqual(complete(models[0]),complete(m));self.assertEqual(models[0].trace,m.trace)
        return models
    def test_01_owner_Make_GNU_guard_and_old_stub(self):
        self.assertEqual(self.fitted,self.truth);self.assertEqual(sum(a!=b for a,b in zip(self.raw,self.truth)),1)
        self.assertEqual(source.payload(source.original(ROOT,self.out,source.FUNCTIONS[0]),source.FUNCTIONS[0]),source.normalized(*source.payload(self.obj,source.FUNCTIONS[0])))
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['total_words'],q['new_guards'],q['compiler_only']),(42,1,False))
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,ENTRY,168);words=list(struct.unpack_from('>42I',old,at))
        memory,event=fixture(Case());old_model=CommandOracle(words,memory,(ACTOR,event,45)).run()
        self.assertNotEqual(public(old_model.memory),public(reference(memory,(ACTOR,event,45))[0]))
        self.receipt.update(words=42,frame=24,bindings=1,new_guards=1,guarded_commutative_branch_only=True,old_stub_effectively_rejected=True,neighbors=q['preserved_neighbors'])
    def test_02_all_commands_word_widths_read_order_and_aliases(self):
        count=0;visits=set()
        for command,relation,pattern,phase in itertools.product(range(256),range(4),range(6),(0,8)):
            c=Case(command,relation,pattern,0,pattern%4);m=self.compare(c,phase)[0];visits.update(m.visits);count+=1
        aliases=0
        for alias,command,relation,phase in itertools.product(range(1,8),(0,45,255,0xAB00002D),range(4),(0,8)):
            self.compare(Case(command,relation,3,alias),phase);aliases+=1
        self.assertEqual(visits,set(range(ENTRY,ENTRY+168,4))-{ENTRY+128})
        self.receipt.update(guest_phases=count,guest_alias_phases=aliases,reachable_words=41,unreachable_duplicate_words=1,full_argument_home_and_exact_read_order=True)
    def test_03_native32_real_dispatcher_and_effective_wrong_C(self):
        body=source.SELECTED[source.FUNCTIONS[0]]
        changes=(('command','value == 0x2D','value == 0x2E'),('and-gate','|| event[4]','&& event[4]'),
          ('forward-word','*(s32 *)(event + 4);','*(s32 *)event;'),('forward-byte','event[9]','event[8]'),
          ('reverse-byte','event[8]','event[9]'),('reverse-word','*(s32 *)state = first;','*(s32 *)state = first ^ 1;'),
          ('word-width','first == value','(u8)first == value'),('wrong-state','owner + 0x60','owner + 0x64'))
        bodies=[body];names=[source.FUNCTIONS[0]]
        for index,(label,a,b)in enumerate(changes):
            self.assertIn(a,body);name=source.FUNCTIONS[0]+'_control'+str(index)
            bodies.append(body.replace(a,b).replace(source.FUNCTIONS[0],name));names.append(name)
        runner='static int run(void){int r;'+''.join('r=runVariant(%s);if(r!=%d)return %d;'%(name,0 if i==0 else 23,80+i)for i,name in enumerate(names))+'return 0;}'
        for opt in ('-O0','-O2','-O3'):
            p=self.out/('native-batch'+opt+'.c');exe=p.with_suffix('.elf')
            p.write_text(native_harness('\n'.join(bodies),self.parent_source).replace('BATCH_RUNNER',runner))
            q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(q.returncode,0,q.stderr)
            self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=30).returncode,0)
        self.receipt.update(native_cases_per_optimization=147456,native_optimizations=3,trap_UBSan=True,effective_defined_wrong_C_controls=8,negative_controls_each_optimization=True,native_compile_invocations=3,actual_C_dispatcher=True,native_indices_backed_and_in_range=True)
    def test_04_complete_original_current_dispatcher_and_table_registration(self):
        self.assertEqual([struct.unpack_from('>I',self.rom,0x234424+i*4)[0]for i in range(3)],[0,OTHER,ENTRY])
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==struct.pack('>I',ENTRY)],[0x23442C])
        jal=struct.pack('>I',0x0C000000|(ENTRY>>2&0x3FFFFFF))
        self.assertFalse(any(self.rom[i:i+4]==jal for i in range(0,len(self.rom),4)))
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,PARENT,88);self.assertEqual(list(struct.unpack_from('>22I',old,at)),self.parent)
        visits=set();count=0
        for slot,command,relation,phase in itertools.product((0,1,2,3,255),(0,45,255,0xAB00002D),range(4),(0,8)):
            c=Case(command,relation,3,0,1);memory,event=fixture(c,phase);memory[ACTOR+0x5C]=slot;models=[]
            for code in (self.truth,self.raw,self.fitted):
                connected=dict(zip(range(ENTRY,ENTRY+168,4),code));m=CommandOracle(self.parent,memory,(ACTOR,event,command),phase,1,PARENT,connected).run();models.append(m);visits.update(m.visits)
            for m in models[1:]:self.assertEqual(complete(models[0]),complete(m))
            expected_calls=[]
            if slot==2:expected_calls=[(ENTRY,(ACTOR,event,command&255))]+reference(memory,(ACTOR,event,command&255),1,STACK+phase-24)[1]
            elif slot==1:expected_calls=[(OTHER,(ACTOR,event,command&255))]
            self.assertEqual(models[0].calls,expected_calls);count+=1
        self.assertTrue(set(range(PARENT,PARENT+88,4))<=visits)
        self.receipt.update(caller_words=22,caller_phases=count,all_caller_words_visited=True,callback_result_unused=True,NULL_and_out_of_range_slots=True,other_callback_bounded=True)
    def test_05_original_release_helper_and_provider_limits(self):
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,HELPER,112);self.assertEqual(list(struct.unpack_from('>28I',old,at)),self.helper)
        visits=set();count=0
        for kind,callback,mode,phase in itertools.product((0,1,2,255),(0,CALLBACK),(0,4),(0,8)):
            c=Case(0,0,3);memory,event=fixture(c,phase);memory[ACTOR]=kind;put(memory,HELPER_TABLE+kind*52,callback);put(memory,HELPER_TABLE+2*52,callback);models=[]
            for code in (self.truth,self.raw,self.fitted):
                connected=dict(zip(range(HELPER,HELPER+112,4),self.helper));m=CommandOracle(code,memory,(ACTOR,event,0),phase,mode,ENTRY,connected).run();models.append(m);visits.update(m.visits)
            for m in models[1:]:self.assertEqual(complete(models[0]),complete(m))
            want=[HELPER,PRE]
            if (2 if mode&4 else kind)>=2:want.append(CALLBACK if callback else FALLBACK)
            self.assertEqual([x[0]for x in models[0].calls],want);count+=1
        self.assertTrue(set(range(HELPER,HELPER+112,4))<=visits)
        self.receipt.update(original_helper_words=28,helper_phases=count,all_helper_words_visited=True,pre_helper_mutation_reload=True,lower_release_providers_not_emulated=True)
    def test_06_independent_links_and_fired_root_faults(self):
        count=cuts=0;original=source.original(ROOT,self.out,source.FUNCTIONS[0])
        phases=0
        for i,helper in enumerate((0x17107FFC,0x17208000,0x1730FFFC)):
            entry=0x17001000+i*0x10000;images=[];raw_image=None
            for label,obj in (('original',original),('C',self.obj)):
                code=self.link_words(obj,entry,helper,'rebase-%s-%d'%(label,i));
                if label=='C':
                    raw_image=list(code);self.assertEqual(code[33],self.raw[33]);code[33]=self.truth[33]
                images.append(code)
            self.assertEqual(images[0],images[1]);count+=2
            for command,relation,phase in itertools.product((0,45,255,0xAB00002D),range(4),(0,8)):
                c=Case(command,relation,3);memory,event=fixture(c,phase);models=[]
                expected,calls,_=reference(memory,(ACTOR,event,command),sp=STACK+phase)
                for code in (images[0],raw_image,images[1]):
                    m=CommandOracle(code,memory,(ACTOR,event,command),phase,entry=entry,helper=helper).run();models.append(m)
                    self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,calls)
                for m in models[1:]:self.assertEqual(complete(models[0]),complete(m))
                phases+=1
        for command,relation,alias,phase in itertools.product((0,45,255),range(4),(0,1,6,7),(0,8)):
            c=Case(command,relation,3,alias);memory,event=fixture(c,phase);good=CommandOracle(self.truth,memory,(ACTOR,event,command),phase).run()
            for cut in range(good.root_accesses):
                models=[CommandOracle(code,memory,(ACTOR,event,command),phase)for code in (self.truth,self.raw,self.fitted)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                for m in models[1:]:self.assertEqual(complete(models[0]),complete(m));self.assertEqual((models[0].current_pc,models[0].delay_of),(m.current_pc,m.delay_of))
                cuts+=1
        self.receipt.update(independent_GNU_links=count,rebase_phases=phases,fired_root_fault_prefixes=cuts,portable_C_fault_or_MMU_claimed=False)
    def test_07_guard_and_full_image_corruptions(self):
        raw,bindings=source.payload(self.obj,source.FUNCTIONS[0]);old=self.values['conker/retail_word_patches.us.csv'];after=source.guard_bytes(old)
        self.assertTrue(after.startswith(old));rows=list(csv.DictReader(io.StringIO(after[len(old):].decode()),fieldnames=list(csv.DictReader(io.StringIO(old.decode())).fieldnames)));self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['offset'],rows[0]['expected'],rows[0]['replacement']),('0x084','0x546A0005','0x55430005'))
        for at in (0,64,132,164):
            wrong=bytearray(raw);wrong[at]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(wrong),bindings)
        with self.assertRaises(ValueError):source.normalized(raw,{})
        with self.assertRaises(ValueError):source.guard_bytes(old+b'\n')
        before=self.values['conker/build/conker.us.elf'];predicted=source.predicted_image(before,self.rom)
        for at in (0,len(predicted)-1,source.elf_slot_offset(predicted,ENTRY,168),source.elf_slot_offset(predicted,PARENT,88),source.elf_slot_offset(predicted,0x80082B20,4)):
            wrong=bytearray(predicted);wrong[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),self.rom)
        self.receipt.update(strict_guard_corruption_controls=6,strict_image_corruption_controls=5,only_one_guard_appended=True,metadata_exclusions=0)
    def test_08_all_pinned_inputs_and_installed_identity(self):
        for name,old in self.values.items():
            self.assertEqual(source.digest(old),source.INPUTS[name])
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else source.guard_bytes(old)if self.installed and name=='conker/retail_word_patches.us.csv'else source.predicted_image(old,self.rom)if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),expected,name)
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(pinned_inputs=len(self.values),guard_prefix_byte_identical=True,old_object_pinned=True)


if __name__=='__main__':unittest.main()
