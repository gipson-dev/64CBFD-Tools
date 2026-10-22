"""Guarded runtime-block factory: ABI, byte copies, helper/caller windows and strict image."""
from dataclasses import dataclass
import itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_runtime_block_factory as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command

ROOT=Path(__file__).resolve().parents[2]
NAME='func_15189FF0'
ENTRY,FACTORY,COPY,LOWER,COUNTER,FOLLOW=0x15189FF0,0x151407D0,0x10022EC0,0x1513D524,0x800DC9F0,0x1514EC1C
DESC,SOURCE,RUNTIME,OBJECT=0x20000,0x22000,0x24000,0x30000
ANCHORS=dict(func_151407D0=FACTORY,memcpy=COPY)


@dataclass(frozen=True)
class Case:
    allocated:int=1
    mode:int=0
    alias:int=0
    values:tuple=(0xABCDEF02,0xDEADBE03,0xA5A5FF80,0xFFFFFFFE)


def locations(c,phase=0):
    descriptor=SOURCE+0x20 if c.alias==2 else DESC
    runtime={1:SOURCE+0x50,3:OBJECT+0x16C,4:STACK+phase+12,5:STACK+phase-64}.get(c.alias,RUNTIME)
    obj=STACK+phase-0x174 if c.alias==6 else OBJECT
    return descriptor,SOURCE,runtime,obj if c.allocated else 0


def fixture(c,phase=0):
    assert all(not STACK-0x800<=p<STACK+0x300 for p in (DESC,SOURCE,RUNTIME,OBJECT))
    m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-0x800,0x300)}
    for base,size in ((DESC,96),(SOURCE,160),(RUNTIME,64),(OBJECT-16,0x220),(COUNTER,4)):
        m.update({base+i:(i*37+0x81)&255 for i in range(size)})
    return m


def public(m):
    return {a:v for a,v in m.items()if not STACK-0x800<=a<STACK+0x300}


def forward(m,dst,src,size):
    for i in range(size):m[dst+i]=m[src+i]


def mutate(m,c,args):
    if c.mode==1:
        for i in range(32):m[args[2]+i]=(i*19+7)&255
    elif c.mode==3:
        for i in range(128):m[args[1]+i]=(i*11+0x35)&255


def reference(c,m,phase=0,anchors=None):
    syms=anchors or ANCHORS;descriptor,src,runtime,obj=locations(c,phase);m=dict(m)
    args=(descriptor,src,runtime,*c.values);m[src+0x58]=11
    calls=[(syms['func_151407D0'],(src,128,descriptor,*[v&255 for v in c.values],0xFFFFFFFF,255,1))]
    mutate(m,c,args)
    if obj:
        calls.append((syms['memcpy'],(obj+0x170,runtime,32)));forward(m,obj+0x170,runtime,32)
    return public(m),calls,obj


class CallerBoundary(Exception):
    pass


class FactoryOracle(TimingOracle):
    def __init__(self,words,c=Case(),phase=0,entry=ENTRY,anchors=None,connected=None,
                 memory=None,arguments=None,frame_offset=0,stop_follow=False):
        self.case,self.anchors=c,anchors or ANCHORS
        self.outer_args=locations(c,phase)[:3]+c.values
        self.stop_follow=stop_follow
        super().__init__(words,fixture(c,phase)if memory is None else memory,phase=phase,entry=entry,
            arguments=self.outer_args if arguments is None else arguments,connected=connected)
        self.r[29]=self.before[29]=STACK+phase+frame_offset

    def execute(self,word):
        if word>>26==32:
            self.dispatched_word=word;self.own_instruction=True
            try:
                rs,rt=word>>21&31,word>>16&31;imm=word&65535
                address=(self.r[rs]+(imm if imm<32768 else imm-65536))&0xFFFFFFFF
                value=self.get(address,1);self.r[rt]=((value^128)-128)&0xFFFFFFFF;self.r[0]=0
            finally:self.own_instruction=False
        else:super().execute(word)

    def record_call(self,target):
        widths={self.anchors['func_151407D0']:10,self.anchors['memcpy']:3,LOWER:9,ENTRY:7,FOLLOW:3}
        args=self.arguments(widths[target])
        self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==FOLLOW and self.stop_follow:raise CallerBoundary

    def hook(self,target):
        args=self.calls[-1][1]
        if target==self.anchors['func_151407D0']:
            mutate(self.memory,self.case,self.outer_args);value=locations(self.case,self.phase)[3]
        elif target==LOWER:value=locations(self.case,self.phase)[3]
        elif target==self.anchors['memcpy']:
            forward(self.memory,*args);value=0xBAD00BAD if self.case.mode==2 else args[0]
        else:raise AssertionError(hex(target))
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678
        self.r[2]=value


def native_harness(body):
    return '#include <ultra64.h>\n'+source.DECLARATIONS+"""
typedef char Width[(sizeof(void*)==4&&sizeof(u32)==4&&sizeof(size_t)==4)?1:-1];
static u8 descriptor[96],sourceBytes[160],runtimeBytes[64],objectBytes[0x210],expected[0x210];
static u32 allocated,mode,inputs[4],calls,bad;
void *memcpy(void *dst,const void *src,size_t size){
 u8 *d=dst;const u8 *s=src;size_t i;
 if(calls!=1||d!=objectBytes+0x170||s!=runtimeBytes||size!=32)bad=1;
 calls++;for(i=0;i<size;i++)d[i]=s[i];return mode==2?(void*)0xBAD00BAD:dst;
}
u8 *func_151407D0(void *src,s32 size,u8 *desc,u8 kind,u8 m,u8 first,u8 variant,s8 selector,u8 channel,s32 context){
 u32 i;
 if(calls||src!=sourceBytes||size!=128||desc!=descriptor||kind!=(u8)inputs[0]||m!=(u8)inputs[1]||
 first!=(u8)inputs[2]||variant!=(u8)inputs[3]||selector!=-1||channel!=255||context!=1||sourceBytes[0x58]!=11)bad=1;
 calls++;
 if(mode==1)for(i=0;i<32;i++)runtimeBytes[i]=(u8)(i*19+7);
 return allocated?objectBytes:0;
}
"""+body+"""
static int run(void){
 u32 field,byte,i;u8 *result;
 for(allocated=0;allocated<=1;allocated++)for(mode=0;mode<3;mode++)for(field=0;field<4;field++)for(byte=0;byte<256;byte++){
  for(i=0;i<4;i++)inputs[i]=0xFFFF0080u+i;
  inputs[field]=0xABCDEF00u|byte;
  for(i=0;i<160;i++)sourceBytes[i]=(u8)(i*37+0x81);
  for(i=0;i<64;i++)runtimeBytes[i]=(u8)(i*37+0x81);
  for(i=0;i<sizeof(objectBytes);i++)objectBytes[i]=expected[i]=(u8)(i*37+0x81);
  for(i=0;i<32;i++)if(allocated)expected[0x170+i]=mode==1?(u8)(i*19+7):runtimeBytes[i];
  calls=bad=0;result=func_15189FF0(descriptor,sourceBytes,runtimeBytes,(u8)inputs[0],(u8)inputs[1],(u8)inputs[2],(u8)inputs[3]);
  if(bad||calls!=1+allocated||result!=(allocated?objectBytes:0)||sourceBytes[0x58]!=11)return 23;
  for(i=0;i<sizeof(objectBytes);i++)if(objectBytes[i]!=expected[i])return 23;
 }return 0;
}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class RuntimeBlockFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.obj,diag=source.compile_owner(ROOT,cls.out,source.ISOLATED_HEADER+source.DECLARATIONS+source.SELECTED[NAME],'fresh-selected')
        if diag:raise ValueError(diag)
        cls.raw,cls.bindings=source.payload(cls.obj,NAME)
        text,fs=source.link_owner(ROOT,cls.out,cls.out/'fitted-selected.o',source.OWNER)
        cls.words=list(struct.unpack_from('>41I',text,fs[NAME]['value']))
        cls.truth=list(struct.unpack_from('>41I',cls.rom,0x1B74A0));cls.receipt=dict(installed=cls.installed)

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)

    def compare(self,c,phase=0,images=None,anchors=None,entry=ENTRY,semantic=True,connected=None):
        memory=fixture(c,phase);models=[FactoryOracle(code,c,phase,entry,anchors,connected,memory).run()for code in images or (self.truth,self.words)]
        if semantic:
            expected,calls,result=reference(c,memory,phase,anchors)
            for m in models:self.assertEqual(public(m.memory),expected);self.assertEqual(m.calls,calls);self.assertEqual(m.r[2],result)
        self.assertEqual(complete(models[0]),complete(models[1]));return models

    def test_01_closed_return_join_GNU_bindings_neighbors_and_Make(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.bindings,source.BINDINGS)
        fitted=source.normalized(self.raw,self.bindings)
        self.assertEqual(source.payload(source.original(ROOT,self.out,NAME),NAME),fitted)
        self.assertEqual(len(self.raw),160);self.assertEqual(len(fitted[0]),164)
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['total_words'],q['raw_words'],q['compiler_only'],q['new_guards'],q['preserved_neighbors']),(41,40,False,2,5))
        self.assertEqual(json.loads((self.out/'make-shadow.json').read_text())['actual_Make_commands'],3)
        self.receipt.update(raw_C_words=40,linked_words=41,frame=56,bindings=2,new_guards=2,inserted_pure_branch_words=1,neighbors=5,compiler_only=False)

    def test_02_exhaustive_argument_bytes_order_aliases_and_ABI(self):
        count=aliases=0;visits=set()
        for field,byte,allocated,phase in itertools.product(range(4),range(256),(0,1),(0,8)):
            values=[0xFFFF0080+i for i in range(4)];values[field]=0xABCDEF00|byte
            m=self.compare(Case(allocated,byte%4,0,tuple(values)),phase)[0];visits.update(m.visits);count+=1
        for alias,mode,allocated,phase in itertools.product(range(1,7),range(4),(0,1),(0,8)):
            self.compare(Case(allocated,mode,alias),phase,semantic=alias<4);aliases+=1
        self.assertEqual(visits,set(range(ENTRY,ENTRY+164,4)))
        self.receipt.update(exhaustive_byte_phases=count,guest_alias_phases=aliases,reachable_words=41,
            full_volatile_and_argument_home_clobbers=True,source_subtype_before_factory=True,
            guest_stack_aliases_not_portable_C=True)

    def native(self,body,label,opt='-O2'):
        path=self.out/(label+opt+'.c');exe=path.with_suffix('.elf');path.write_text(native_harness(body))
        p=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        return subprocess.run([str(exe)],capture_output=True,timeout=20).returncode

    def test_03_native32_failure_live_copy_return_and_wrong_C(self):
        body=source.SELECTED[NAME]
        for opt in ('-O0','-O2','-O3'):self.assertEqual(self.native(body,'native',opt),0)
        controls=[('subtype','source[0x58] = 0x0B','source[0x58] = 0x0C'),
          ('size','source, 0x80','source, 0x7F'),('runtime-offset','result + 0x170','result + 0x174'),
          ('runtime-length','runtime, 0x20','runtime, 0x1F'),('return','return result;','return result + 0x170;'),
          ('variant','first, variant, -1','first, first, -1'),('channel','-1, 0xFF, 1','-1, 0xFE, 1')]
        for label,a,b in controls:
            wrong=body.replace(a,b);self.assertNotEqual(wrong,body);self.assertNotEqual(self.native(wrong,'wrong-'+label),0,label)
        self.receipt.update(native_cases_per_optimization=6144,native_optimizations=3,trap_UBSan=True,effective_wrong_C_controls=7,
            valid_nonoverlapping_native_memcpy=True,helper_is_bounded_provider=True)

    def test_04_original_factory_and_byte_memcpy_with_bounded_allocator(self):
        connected={};helper_visits=set();count=0
        for entry,rom,words in ((FACTORY,0x16DC80,53),(COPY,0x22EC0,11)):
            raw=self.rom[rom:rom+words*4];at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],entry,words*4)
            self.assertEqual(self.values['conker/build/conker.us.elf'][at:at+words*4],raw)
            connected.update(zip(range(entry,entry+words*4,4),struct.unpack('>%dI'%words,raw)))
        for allocated,alias,counter,phase in itertools.product((0,1),(0,1,2,3),(0,0xFFFFFFFF),(0,8)):
            c=Case(allocated,0,alias);memory=fixture(c,phase);put(memory,COUNTER,counter);models=[]
            for code in (self.truth,self.words):
                m=FactoryOracle(code,c,phase,connected=connected,memory=memory).run()
                lower=next(args for target,args in m.calls if target==LOWER)
                descriptor,src,runtime,obj=locations(c,phase)
                self.assertEqual(lower,(descriptor,2,3,128,1,254,128,255,1))
                self.assertEqual(m.r[2],obj);self.assertEqual(m.memory[descriptor+1],3)
                self.assertEqual(read(m.memory,descriptor+64),read(memory,descriptor+64)|0x40400000)
                self.assertEqual(read(m.memory,COUNTER),(counter+allocated)&0xFFFFFFFF)
                copies=[args for target,args in m.calls if target==COPY]
                self.assertEqual(copies,[(obj+0x110,src,128),(obj+0x170,runtime,32)]if allocated else [])
                if allocated:self.assertEqual(m.memory[obj+0x169],255);self.assertEqual(read(m.memory,obj+0x154),0)
                helper_visits.update(m.visits);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(FACTORY,FACTORY+212,4))<=helper_visits)
        self.assertTrue(set(range(COPY,COPY+44,4))<=helper_visits)
        self.receipt.update(connected_helper_phases=count,original_factory_words=53,original_memcpy_words=11,
            actual_forward_byte_copy_and_overlap=True,lower_9_argument_allocator_bounded=True,
            complete_constructor_or_gameplay_claimed=False)

    def test_05_original_caller_windows(self):
        # Execute original setup, call, and continuation only; parent C remains a stub.
        windows=[(0x1514D76C,0x1514D7AC,0x74,0xCC,0x54,9,0),
                 (0x1514D8A8,0x1514D8F8,0x74,0xCC,0x54,10,0),
                 (0x1514E124,0x1514E16C,0x4C,0xA4,0x2C,6,0x100),
                 (0x1514E2AC,0x1514E2F4,0x4C,0xA4,0x2C,6,0x100),
                 (0x1514E404,0x1514E480,0x7C,0xD4,0x5C,7,0x130)]
        count=0
        for start,end,do,so,ro,tag,actor_home in windows:
            rom=start-0x1514CA80+0x179F30
            words=list(struct.unpack_from('>%dI'%((end-start)//4),self.rom,rom))
            for allocated,phase in itertools.product((0,1),(0,8)):
                c=Case(allocated);models=[]
                for code in (self.truth,self.words):
                    connected=dict(zip(range(ENTRY,ENTRY+164,4),code));frame=STACK+phase
                    m=FactoryOracle(words,c,phase,entry=start,connected=connected,arguments=(0,0,0,0),stop_follow=True)
                    m.r[16]=0x32000
                    if actor_home:put(m.memory,frame+actor_home,0x32000)
                    with self.assertRaises(CallerBoundary):m.run()
                    call=next(args for target,args in m.calls if target==ENTRY)
                    self.assertEqual(call[:4],(frame+do,frame+so,frame+ro,2))
                    self.assertEqual(tuple(v&255 for v in call[4:]),(3 if tag==7 else 0,0,0))
                    self.assertEqual(m.calls[-1],(FOLLOW,(OBJECT if allocated else 0,0x32000,tag)))
                    models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        for allocated,phase in itertools.product((0,1),(0,8)):
            models=[];start=0x1514F0CC;rom=start-0x1514CA80+0x179F30
            words=list(struct.unpack_from('>17I',self.rom,rom))
            for code in (self.truth,self.words):
                frame=STACK+phase-0x120;connected=dict(zip(range(ENTRY,ENTRY+164,4),code))
                m=FactoryOracle(words,Case(allocated),phase,entry=start,connected=connected,
                    arguments=(frame+0xC4,frame+0x68,frame+0x48,0),frame_offset=-0x120)
                m.r[9]=frame+0x54
                put(m.memory,frame+0x44,m.before[31]);m.before[29]+=0x120;m.run()
                self.assertEqual(next(args for target,args in m.calls if target==ENTRY),
                    (frame+0xC4,frame+0x68,frame+0x48,2,0,0,0))
                self.assertEqual(m.r[2],OBJECT if allocated else 0);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt.update(original_caller_window_phases=count,original_call_sites_covered=6,
            sixth_site_setup_inputs_seeded_at_selected_boundary=True,complete_parent_execution_not_claimed=True)

    def test_06_independent_GNU_symbol_rebases(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        original=source.original(ROOT,self.out,NAME);links=count=0
        for i in range(3):
            entry=0x17007FFC+i*0x10000;syms=dict(func_151407D0=0x17203000+i*0x1000,memcpy=0x1730FFFC+i*0x20000);images=[]
            for label,obj in [('original',original),('C',self.out/'fitted-selected.o')]:
                text,fs,rs=source.parse_object(obj);assembly,unknown=emit_function(text,fs[NAME],rs,NAME,syms);self.assertFalse(unknown)
                stem=self.out/('rebase-%d-%s'%(i,label));asm=stem.with_suffix('.s');out=stem.with_suffix('.o');ld=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                asm.write_text(assembly);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(out),str(asm)],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',NAME,*['--defsym=%s=0x%X'%p for p in syms.items()],'-o',str(elf),str(out)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>41I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(images[0],images[1])
            for allocated,mode,phase in itertools.product((0,1),range(4),(0,8)):
                self.compare(Case(allocated,mode),phase,images,syms,entry);count+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=count,both_R26_bindings=True)

    def test_07_fired_root_fault_prefixes(self):
        count=0
        for allocated,mode,alias,phase in itertools.product((0,1),(0,1,2),(0,1,4,6),(0,8)):
            c=Case(allocated,mode,alias);good=FactoryOracle(self.truth,c,phase).run()
            for cut in range(good.root_accesses):
                models=[FactoryOracle(code,c,phase)for code in (self.truth,self.words)]
                for m in models:m.root_fault=cut
                for m in models:
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));count+=1
        self.assertGreater(count,100);self.receipt.update(fired_root_fault_prefixes=count,portable_fault_or_MMU_claimed=False)

    def test_08_strict_image_28_inputs_guards_and_corruptions(self):
        before=self.values['conker/build/conker.us.elf'];expected=source.predicted_image(before,self.rom)
        self.assertEqual(expected,(self.out/'first-linked.elf').read_bytes());at=source.elf_slot_offset(before,ENTRY,164)
        sym=next(pos for pos,n,f,_ in source.symbol_rows(before)if n==NAME and f[1:3]==(ENTRY,12))
        for pos in (0,len(expected)-1,at,at+159,at+163,at+164,sym+8):
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),self.rom)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],self.rom)
        self.assertEqual(len(self.values),28)
        for name,old in self.values.items():
            self.assertEqual(source.digest(old),source.INPUTS[name]);current=old
            if self.installed:
                if name==source.SOURCE:current=source.recovered_owner(old.decode()).encode()
                elif name=='conker/build/conker.us.elf':current=expected
                elif name=='conker/retail_word_patches.us.csv':current=source.guard_bytes(old)
            self.assertEqual((ROOT/name).read_bytes(),current)
        old=self.values['conker/retail_word_patches.us.csv'];new=source.guard_bytes(old);self.assertTrue(new.startswith(old))
        for raw,bindings in [(self.raw[:-4],self.bindings),(self.raw,{}),(bytes([self.raw[0]^1])+self.raw[1:],self.bindings)]:
            with self.assertRaises(ValueError):source.normalized(raw,bindings)
        with self.assertRaises(ValueError):source.guard_bytes(new)
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(strict_image_corruptions_rejected=8,live_and_historical_inputs=28,old_object_pinned=True,
            metadata_exclusions=0,complete_old_guard_prefix_preserved=True,guard_normalizer_controls=4)


if __name__=='__main__':
    unittest.main()
