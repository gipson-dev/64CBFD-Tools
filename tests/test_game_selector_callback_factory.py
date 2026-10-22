"""Selector callback: captured byte, reserved payload bytes, caller and original wrapper."""
from dataclasses import dataclass
import itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_selector_callback_factory as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command

ROOT=Path(__file__).resolve().parents[2]
NAME='func_1515D088'
ENTRY,FACTORY,SPAWN,COPY,CALLER=0x1515D088,0x151491F4,0x15149130,0x10022EC0,0x1501374C
SOURCE,OBJECT,OTHER=0x20000,0x30000,0x32000
ANCHORS=dict(func_151491F4=FACTORY,memcpy=COPY)


@dataclass(frozen=True)
class Case:
    word:int=0xABCDEF01
    allocated:int=1
    mode:int=0
    alias:int=0


def locations(c,phase=0):
    src={1:OBJECT+0x10,2:STACK+phase-0x18,4:STACK+phase-0x28}.get(c.alias,SOURCE)
    obj=STACK+phase-0x34 if c.alias==3 else OBJECT
    return src,obj if c.allocated else 0


def fixture(c,phase=0):
    assert all(not STACK-0x800<=p<STACK+0x300 for p in (SOURCE,OBJECT,OTHER))
    m={STACK+phase+i:(i*17+0xA5+(c.word>>24))&255 for i in range(-0x800,0x300)}
    for base,size in ((SOURCE,96),(OBJECT-16,160),(OTHER,96)):
        m.update({base+i:(i*37+0x81)&255 for i in range(size)})
    put(m,locations(c,phase)[0]+0x18,c.word);return m


def public(m):
    return {a:v for a,v in m.items()if not STACK-0x800<=a<STACK+0x300}


def forward(m,dst,src,size):
    for i in range(size):m[dst+i]=m[src+i]


def effect(m,c,src,sp):
    if c.mode==1:put(m,src+0x18,0xFFFFFFFF)
    elif c.mode==2:
        for i in range(3):m[sp-7+i]=0xB1+i*17
    elif c.mode==3:put(m,sp,OTHER)


def reference(c,memory,phase=0,anchors=None,wrapper=False):
    syms=anchors or ANCHORS;m=dict(memory);src,obj=locations(c,phase);sp=STACK+phase
    put(m,sp,src);selector=read(m,src+0x18)&255;m[sp-8]=selector;calls=[]
    if selector>=2:return public(m),calls,0
    put(m,sp-16,src);put(m,sp-12,0)
    calls.append((syms['func_151491F4'],(300,0xFFFFFFFF,17,0,13,12,255,1)))
    if wrapper:calls.append((SPAWN,(300,0xFFFFFFFF,17,0xFFFFFFFF,0,13,12,255,1)))
    effect(m,c,src,sp)
    if obj:
        put(m,sp-4,obj);calls.append((syms['memcpy'],(obj+0x28,sp-16,12)))
        forward(m,obj+0x28,sp-16,12);result=read(m,sp-4)
    else:result=0
    return public(m),calls,result


class SelectorOracle(TimingOracle):
    def __init__(self,words,c=Case(),phase=0,entry=ENTRY,anchors=None,connected=None,memory=None):
        self.case,self.anchors=c,anchors or ANCHORS
        self.target_sp,self.target_source=STACK+phase,locations(c,phase)[0]
        super().__init__(words,fixture(c,phase)if memory is None else memory,phase=phase,entry=entry,
            arguments=(self.target_source,),connected=connected)

    def record_call(self,target):
        widths={self.anchors['func_151491F4']:8,self.anchors['memcpy']:3,SPAWN:9,ENTRY:1}
        args=self.arguments(widths[target])
        self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==ENTRY:self.target_sp,self.target_source=self.r[29],args[0]

    def hook(self,target):
        args=self.calls[-1][1]
        if target in (self.anchors['func_151491F4'],SPAWN):
            effect(self.memory,self.case,self.target_source,self.target_sp)
            value=locations(self.case,self.phase)[1]
        elif target==self.anchors['memcpy']:
            forward(self.memory,*args);value=0xBAD00BAD if self.case.mode==4 else args[0]
        else:raise AssertionError(hex(target))
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678
        self.r[2]=value


def native_harness(body):
    return source.ISOLATED_HEADER+source.DECLARATIONS+"""
typedef char Width[(sizeof(void*)==4&&sizeof(u32)==4&&sizeof(size_t)==4&&sizeof(SelectorCallbackPayload)==12&&
 __builtin_offsetof(SelectorCallbackPayload,value)==4&&__builtin_offsetof(SelectorCallbackPayload,selector)==8)?1:-1];
static u32 sourceWords[16],original,allocated,mode,calls,bad;
static u8 objectBytes[128],expected[128];
__attribute__((noinline)) void *memcpy(void *dst,const void *src,size_t size){
 u8 *d=dst;const u8 *s=src;size_t i;
 if(calls!=1||d!=objectBytes+0x28||size!=12)bad=1;
 calls++;for(i=0;i<size;i++)d[i]=s[i];return mode==4?(void*)0xBAD00BAD:dst;
}
void *func_151491F4(s16 duration,s8 first,s8 second,u8 flags,u8 kind,s32 size,u8 channel,s32 context){
 if(calls||duration!=300||first!=-1||second!=17||flags||kind!=13||size!=12||channel!=255||context!=1)bad=1;
 calls++;if(mode==1)sourceWords[6]=0xFFFFFFFFu;return allocated?objectBytes:0;
}
"""+body+"""
static int run(void){
 u32 upper,byte,i,j,word;void *result,*sourcePtr=sourceWords;u8 *pointerBytes=(u8*)&sourcePtr;
 for(allocated=0;allocated<=1;allocated++)for(j=0;j<3;j++)for(upper=0;upper<4;upper++)for(byte=0;byte<256;byte++){
  mode=j==2?4:j;original=byte;word=((u32[]){0,0x7FFFFF00u,0x80000000u,0xFFFFFF00u})[upper]|byte;
  for(i=0;i<16;i++)sourceWords[i]=0xAD000000u+i;sourceWords[6]=word;
  for(i=0;i<128;i++)objectBytes[i]=expected[i]=(u8)(i*37+0x81);
  calls=bad=0;result=func_1515D088(sourceWords);
  if(bad||calls!=(byte<2?1+allocated:0)||result!=(byte<2&&allocated?objectBytes:0))return 23;
  if(byte<2&&allocated){
   for(i=0;i<4;i++)if(objectBytes[0x28+i]!=pointerBytes[i])return 23;
   for(i=0;i<4;i++)if(objectBytes[0x2C+i]!=0)return 23;
   if(objectBytes[0x30]!=(u8)original)return 23;
  }
  for(i=0;i<128;i++)if(!(byte<2&&allocated&&i>=0x28&&i<0x34)&&objectBytes[i]!=expected[i])return 23;
 }return 0;
}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class SelectorCallbackFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.obj,diag=source.compile_owner(ROOT,cls.out,source.ISOLATED_HEADER+source.DECLARATIONS+source.SELECTED[NAME],'fresh-selected')
        if diag:raise ValueError(diag)
        cls.raw,cls.bindings=source.payload(cls.obj,NAME)
        text,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER)
        cls.words=list(struct.unpack_from('>42I',text,fs[NAME]['value']))
        cls.truth=list(struct.unpack_from('>42I',cls.rom,0x18A538));cls.receipt=dict(installed=cls.installed)

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)

    def compare(self,c,phase=0,images=None,anchors=None,entry=ENTRY,connected=None,wrapper=False):
        memory=fixture(c,phase);models=[SelectorOracle(code,c,phase,entry,anchors,connected,memory).run()for code in images or (self.truth,self.words)]
        expected,calls,result=reference(c,memory,phase,anchors,wrapper)
        for m in models:self.assertEqual(public(m.memory),expected);self.assertEqual(m.calls,calls);self.assertEqual(m.r[2],result)
        self.assertEqual(complete(models[0]),complete(models[1]));return models

    def test_01_direct_body_GNU_bindings_owner_caller_and_Make(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.bindings,source.BINDINGS)
        self.assertEqual(source.payload(source.original(ROOT,self.out,NAME),NAME),(self.raw,self.bindings))
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['total_words'],q['compiler_only'],q['new_guards'],q['preserved_neighbors'],q['caller_functions']),(42,True,0,7,32))
        self.assertEqual(json.loads((self.out/'make-shadow.json').read_text())['actual_Make_commands'],8)
        before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,ENTRY,168)
        old=SelectorOracle(list(struct.unpack_from('>42I',before,at)),Case()).run()
        current=self.compare(Case())[0]
        self.assertNotEqual(bytes(old.memory[OBJECT+0x28+i]for i in range(12)),bytes(current.memory[OBJECT+0x28+i]for i in range(12)))
        self.receipt.update(direct_C_words=42,frame=64,bindings=2,new_guards=0,neighbors=7,caller_functions=32,caller_object_identical=True,
            predecessor_reserved_stack_bytes_differ=True)

    def test_02_all_selector_bytes_upper_bits_late_effects_and_aliases(self):
        count=aliases=0;visits=set();padding=set()
        for byte,upper,allocated,mode,phase in itertools.product(range(256),(0,0x7FFFFF00,0x80000000,0xFFFFFF00),(0,1),range(5),(0,8)):
            c=Case(upper|byte,allocated,mode);m=self.compare(c,phase)[0];visits.update(m.visits);count+=1
            if byte<2 and allocated:padding.add(bytes(m.memory[OBJECT+0x31+i]for i in range(3)))
        for byte,allocated,mode,alias,phase in itertools.product((0,1,2,255),(0,1),range(5),range(1,5),(0,8)):
            self.compare(Case(0xABCDEF00|byte,allocated,mode,alias),phase);aliases+=1
        self.assertEqual(visits,set(range(ENTRY,ENTRY+168,4)));self.assertGreater(len(padding),2)
        self.receipt.update(exhaustive_selector_phases=count,guest_alias_phases=aliases,reachable_words=42,
            reserved_byte_patterns=len(padding),all_12_payload_bytes_observed=True,full_volatile_and_argument_home_clobbers=True,
            guest_stack_aliases_not_portable_C=True,redundant_negative_branch_never_taken=True)

    def native(self,body,label,opt='-O2'):
        path=self.out/(label+opt+'.c');exe=path.with_suffix('.elf');path.write_text(native_harness(body))
        p=subprocess.run(native_command(opt)+['-mstackrealign',str(path),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        return subprocess.run([str(exe)],capture_output=True,timeout=20).returncode

    def test_03_native32_defined_fields_fences_and_wrong_C(self):
        body=source.SELECTED[NAME]
        for opt in ('-O0','-O2','-O3'):self.assertEqual(self.native(body,'native',opt),0)
        controls=[('gate','selector >= 2','selector > 2'),('selector-offset','source + 0x18','source + 0x1C'),
          ('zero','data.value = 0.0f','data.value = 1.0f'),('copy-size','sizeof(data)','9'),
          ('destination','created + 0x28','created + 0x2C'),('duration','0x12C, -1','0x12D, -1'),
          ('return','return created;','return created == NULL ? NULL : created + 0x28;'),
          ('late-selector','if (created != NULL) {','data.selector = *(s32 *)((u8 *)source + 0x18);\n    if (created != NULL) {')]
        for label,a,b in controls:
            wrong=body.replace(a,b);self.assertNotEqual(wrong,body);self.assertNotEqual(self.native(wrong,'wrong-'+label),0,label)
        self.receipt.update(native_cases_per_optimization=6144,native_optimizations=3,trap_UBSan=True,effective_wrong_C_controls=8,
            native_checks_nine_defined_payload_bytes_and_destination_fences=True,
            native_reserved_byte_values_not_asserted=True,exact_reserved_bytes_qualified_in_guest=True)

    def test_04_original_factory_wrapper_and_byte_memcpy(self):
        connected={};visits=set();count=0
        for entry,rom,words in ((FACTORY,0x1766A4,28),(COPY,0x22EC0,11)):
            raw=self.rom[rom:rom+words*4];at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],entry,words*4)
            self.assertEqual(self.values['conker/build/conker.us.elf'][at:at+words*4],raw)
            connected.update(zip(range(entry,entry+words*4,4),struct.unpack('>%dI'%words,raw)))
        for byte,allocated,mode,alias,phase in itertools.product((0,1,2,255),(0,1),range(5),(0,1,3,4),(0,8)):
            models=self.compare(Case(0xABCDEF00|byte,allocated,mode,alias),phase,connected=connected,wrapper=True)
            visits.update(models[0].visits);count+=1
        self.assertTrue(set(range(FACTORY,FACTORY+112,4))<=visits);self.assertTrue(set(range(COPY,COPY+44,4))<=visits)
        self.receipt.update(connected_helper_phases=count,original_wrapper_words=28,original_memcpy_words=11,
            actual_forward_byte_copy_and_overlap=True,nine_argument_spawn_bounded=True,full_constructor_or_gameplay_claimed=False)

    def test_05_complete_original_and_current_caller(self):
        raw=self.rom[0x40BFC:0x40BFC+44];at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],CALLER,44)
        self.assertEqual(self.values['conker/build/conker.us.elf'][at:at+44],raw)
        words=list(struct.unpack('>11I',raw));count=0
        for byte,allocated,mode,flag,phase in itertools.product((0,1,2,255),(0,1),(0,1,2,3,4),(0,0xFF),(0,8)):
            c=Case(0xABCDEF00|byte,allocated,mode);models=[]
            for code in (self.truth,self.words):
                memory=fixture(c,phase);memory[SOURCE+0x16]=flag
                connected=dict(zip(range(ENTRY,ENTRY+168,4),code));m=SelectorOracle(words,c,phase,CALLER,connected=connected,memory=memory).run()
                self.assertEqual(m.r[2],1);self.assertEqual(m.memory[SOURCE+0x16],flag|4)
                self.assertEqual(m.calls[0],(ENTRY,(SOURCE,)));self.assertEqual(sum(t==FACTORY for t,_ in m.calls),int(byte<2));models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt.update(complete_original_and_current_caller_phases=count,caller_words=11,caller_returns_one_and_ignores_target_result=True)

    def test_06_independent_GNU_symbol_rebases(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        original=source.original(ROOT,self.out,NAME);links=count=0
        for i in range(3):
            entry=0x17007FFC+i*0x10000;syms=dict(func_151491F4=0x17203000+i*0x1000,memcpy=0x1730FFFC+i*0x20000);images=[]
            for label,obj in [('original',original),('C',self.obj)]:
                text,fs,rs=source.parse_object(obj);assembly,unknown=emit_function(text,fs[NAME],rs,NAME,syms);self.assertFalse(unknown)
                stem=self.out/('rebase-%d-%s'%(i,label));asm=stem.with_suffix('.s');out=stem.with_suffix('.o');ld=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                asm.write_text(assembly);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(out),str(asm)],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',NAME,*['--defsym=%s=0x%X'%p for p in syms.items()],'-o',str(elf),str(out)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>42I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(images[0],images[1])
            for byte,allocated,mode,phase in itertools.product((0,1,2,255),(0,1),(0,1,2,3,4),(0,8)):
                self.compare(Case(0xABCDEF00|byte,allocated,mode),phase,images,syms,entry);count+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=count,both_R26_bindings=True)

    def test_07_fired_root_fault_prefixes(self):
        count=0
        for byte,allocated,mode,alias,phase in itertools.product((0,1,2,255),(0,1),(0,2,3),(0,1,3),(0,8)):
            c=Case(0xABCDEF00|byte,allocated,mode,alias);good=SelectorOracle(self.truth,c,phase).run()
            for cut in range(good.root_accesses):
                models=[SelectorOracle(code,c,phase)for code in (self.truth,self.words)]
                for m in models:m.root_fault=cut
                for m in models:
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));count+=1
        self.assertGreater(count,100);self.receipt.update(fired_root_fault_prefixes=count,portable_fault_or_MMU_claimed=False)

    def test_08_strict_image_28_inputs_and_corruptions(self):
        before=self.values['conker/build/conker.us.elf'];expected=source.predicted_image(before,self.rom)
        self.assertEqual(expected,(self.out/'first-linked.elf').read_bytes());at=source.elf_slot_offset(before,ENTRY,168)
        sym=next(pos for pos,n,f,_ in source.symbol_rows(before)if n==NAME and f[1:3]==(ENTRY,164))
        for pos in (0,len(expected)-1,at,at+159,at+167,at+168,sym+8):
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),self.rom)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],self.rom)
        self.assertEqual(len(self.values),28)
        for name,old in self.values.items():
            self.assertEqual(source.digest(old),source.INPUTS[name]);current=old
            if self.installed:
                if name==source.SOURCE:current=source.recovered_owner(old.decode()).encode()
                elif name==source.CALLER_SOURCE:current=source.recovered_caller(old.decode()).encode()
                elif name=='conker/build/conker.us.elf':current=expected
            self.assertEqual((ROOT/name).read_bytes(),current)
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(strict_image_corruptions_rejected=8,live_and_historical_inputs=28,old_object_pinned=True,
            metadata_exclusions=0,guard_manifest_unchanged=True,complete_caller_object_unchanged=True)


if __name__=='__main__':
    unittest.main()
