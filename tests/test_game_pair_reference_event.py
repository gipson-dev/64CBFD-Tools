"""Paired references: byte commands, late tag reads, original callers and release routing."""
from dataclasses import dataclass
from pathlib import Path
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_pair_reference_event as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
PAIR,OWNER=0x20000,0x30000
RELEASE,BOOKKEEP,FALLBACK,CALLBACK,TABLE=0x1516972C,0x151696DC,0x15169804,0x16200000,0x8008B4D0
WORDS=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,OWNER)
SITES=(0x150B0D08,0x150C09D8,0x150ECB74,0x150F31BC,0x150F31FC,0x150F63E8,0x150F6878,
 0x15102D78,0x1510790C,0x15107FC0,0x1514952C,0x15157DB0,0x1515C0E0,0x1518F4C4,
 0x15191A68,0x15191B70,0x151927A4,0x151ACBBC,0x151B2EEC,0x151B306C,0x151B308C,
 0x151BE120,0x151BE62C,0x151BE7B0,0x151CF880,0x151D1350,0x151D70F4)


@dataclass(frozen=True)
class Case:
    command:int=0
    pattern:int=0
    match:int=0
    tag:int=255
    alias:int=0
    mutate:bool=False
    kind:int=2
    callback:bool=True


def locations(case,phase=0):
    value=(OWNER+0x28,PAIR,PAIR+4,OWNER+0x28,PAIR+8,OWNER+0x28,STACK+phase+16,PAIR)[case.alias]
    tag=(OWNER+0x2C,PAIR+9,PAIR+8,PAIR+4,OWNER+0x2C,value,value+3,value+3)[case.alias]
    return value,tag


def fixture(case,phase=0):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
    for base in(PAIR,OWNER):m.update({base+i:0xA5 for i in range(-16,0x200)})
    first=WORDS[case.pattern%6];second=WORDS[(case.pattern+1)%6]
    put(m,PAIR,first);put(m,PAIR+4,second);m[PAIR+8]=17;m[PAIR+9]=231
    value,tag=locations(case,phase);put(m,value,(first,second,0x12345678)[case.match]);m[tag]=case.tag
    put(m,STACK+phase+16,OWNER);m[OWNER]=case.kind
    for kind in(case.kind,7):put(m,TABLE+52*kind,CALLBACK if case.callback else 0)
    return m


def effects(memory,case):
    if case.mutate:memory[OWNER]=7;put(memory,OWNER+0x28,0xBEEFF00D)


def reference(initial,case,phase=0,release=RELEASE,chain=False):
    m=dict(initial);calls=[];value,tag=locations(case,phase);command=case.command&255
    if command==0:
        if read(m,PAIR)==read(m,value)or m[PAIR+4]==m[tag]:
            owner=read(m,STACK+phase+16);calls.append((release,(owner,)))
            if chain:
                calls.append((BOOKKEEP,(owner,)));effects(m,case)
                if m[owner]>=2:calls.append((CALLBACK if case.callback else FALLBACK,(owner,)))
            else:effects(m,case)
    elif command==45:
        first,current=read(m,PAIR),read(m,value)
        if first==current:put(m,value,read(m,PAIR+4));m[tag]=m[PAIR+9]
        elif read(m,PAIR+4)==current:put(m,value,first);m[tag]=m[PAIR+8]
    return m,calls


def public(memory,case,phase):
    value,tag=locations(case,phase)
    return {a:b for a,b in memory.items()if not STACK-1024<=a<STACK+1024 or value<=a<value+4 or a==tag}


class PairOracle(TimingOracle):
    def __init__(self,words,memory,case=Case(),phase=0,entry=source.ENTRY,connected=None,release=RELEASE,arguments=None):
        value,tag=locations(case,phase)
        super().__init__(words,memory,phase=phase,entry=entry,
            arguments=arguments or(PAIR,case.command,value,tag,OWNER),connected=connected)
        self.case,self.release,self.entered=case,release,STACK+phase

    def record_call(self,target):
        if target==source.ENTRY:self.entered=self.r[29];args=self.arguments(5)
        else:
            assert target in(self.release,BOOKKEEP,FALLBACK,CALLBACK),('Unbounded pair service',hex(target))
            args=self.arguments(1)
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        assert target in(self.release,BOOKKEEP,FALLBACK,CALLBACK)
        if target in(self.release,BOOKKEEP):effects(self.memory,self.case)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678


def controls():
    b=source.SELECTED
    return dict(selected=b,
        and_gate=b.replace(' || ',' && '),
        wrong_command=b.replace('command == 0x2D','command == 0x2E'),
        wrong_gate=b.replace('command == 0)', 'command == 1)'),
        wrong_identity=b.replace('pair)[4]','pair)[5]'),
        wrong_first_tag=b.replace('pair)[9]','pair)[8]'),
        wrong_second_tag=b.replace('pair)[8]','pair)[9]'),
        missing_second=b.replace('pair[1] == *value','0'),
        wrong_replacement=b.replace('*value = pair[1]','*value = pair[0]'),
        wrong_owner=b.replace('(struct102 *)owner','(struct102 *)pairAddress'),
        early_tag=b.replace('*value = pair[1];\n            *tag = ((u8 *)pair)[9];','*tag = ((u8 *)pair)[9];\n            *value = pair[1];'))


def native_harness(values):
    owner=values[source.SOURCE].decode();helper=owner[slice(*source.function_span(owner,'func_1516972C'))]
    helper=helper.replace('void func_1516972C(', 'static void real_release(')
    text=source.HEADERS+r'''
static struct102 object;static u8 *arena,*expected;static u32 error,releases,bookkeeps,callbacks,fallbacks,mutation,present;
static u32 expectedRelease;
struct115 D_8008B4D0[256];
typedef char stride[sizeof(struct115)==52?1:-1];
__attribute__((noinline,noclone)) void func_151696DC(void *p){if(p!=&object)error=1;bookkeeps++;if(mutation){object.unk0=7;*(s32*)(arena+0xA8)=(s32)0xBEEFF00D;}}
__attribute__((noinline,noclone)) void func_15169804(struct102 *p){if(p!=&object)error=1;fallbacks++;}
static void callback(struct102 *p){if(p!=&object)error=1;callbacks++;}
'''+helper+r'''
__attribute__((noinline,noclone)) void func_1516972C(struct102 *p){
 if(!expectedRelease||p!=&object||releases++){error=1;return;}real_release(p);
}
'''
    for label,body in controls().items():
        if label!='selected'and body==source.SELECTED:raise ValueError('Ineffective control '+label)
        text+=body.replace(source.FUNCTION,source.FUNCTION+'_'+label)+'\n'
    for path,name in(('conker/src/game/done/game_1765E0.c','func_15149514'),):
        body=values[path].decode();text+=body[slice(*source.function_span(body,name))].replace(source.FUNCTION,source.FUNCTION+'_selected')+'\n'
    text+=r'''
typedef void(*Handler)(s32,u8,s32,s32,s32);
static s32 *word(u32 at){return(s32*)(arena+at);}
static u32 vals[]={0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x30000};
static int one(Handler fn,u32 command,u32 tag,u32 alias,u32 mutate,u32 wrapper){
 u32 i,pattern=command%6,match=tag%3,kind=(tag&3)==3?255:tag&3;
 u32 value=(u32[]){0xA8,0x40,0x44,0xA8,0x48,0xA8}[alias];
 u32 tagAt=(u32[]){0xAC,0x49,0x48,0x44,0xAC,value}[alias];
 u8 objectBefore[sizeof(object)];s32 first,current;u32 release,afterKind;
 for(i=0;i<0x200;i++)arena[i]=0xA5;
 for(i=0;i<sizeof(object);i++)((u8*)&object)[i]=0xA5;
 object.unk0=(u8)kind;*word(0x40)=(s32)vals[pattern];*word(0x44)=(s32)vals[(pattern+1)%6];arena[0x48]=17;arena[0x49]=231;
 *word(value)=match==0?*word(0x40):match==1?*word(0x44):0x12345678;arena[tagAt]=(u8)tag;
 for(i=0;i<0x200;i++)expected[i]=arena[i];for(i=0;i<sizeof(object);i++)objectBefore[i]=((u8*)&object)[i];
 first=*word(0x40);current=*word(value);release=command==0&&(first==current||arena[0x44]==arena[tagAt]);
 if(command==45){if(first==current){*(s32*)(expected+value)=*word(0x44);expected[tagAt]=expected[0x49];}
 else if(*word(0x44)==current){*(s32*)(expected+value)=first;expected[tagAt]=expected[0x48];}}
 mutation=mutate;present=tag&1;afterKind=kind;
 if(release&&mutation){objectBefore[0]=7;*(s32*)(expected+0xA8)=(s32)0xBEEFF00D;afterKind=7;}
 for(i=0;i<256;i++)D_8008B4D0[i].unk0=present?callback:0;
 error=releases=bookkeeps=callbacks=fallbacks=0;expectedRelease=release;
 if(wrapper==1)func_15149514((s32)(arena+0x40),(u8)command,(s32)(arena+value),(s32)(arena+tagAt),(s32)&object);
 else fn((s32)(arena+0x40),(u8)command,(s32)(arena+value),(s32)(arena+tagAt),(s32)&object);
 if(error||releases!=release||bookkeeps!=release||callbacks!=(release&&afterKind>=2&&present)||fallbacks!=(release&&afterKind>=2&&!present))return 23;
 for(i=0;i<0x200;i++)if(arena[i]!=expected[i])return 23;
 for(i=0;i<sizeof(object);i++)if(((u8*)&object)[i]!=objectBefore[i])return 23;
 return 0;
}
static int variant(Handler fn,u32 full){
 u32 c,t,a,m;for(c=0;c<(full?256u:3u);c++)for(t=0;t<256;t++)for(a=0;a<6;a++)for(m=0;m<2;m++)
  if(one(fn,full?c:(u32[]){0,45,255}[c],t,a,m,0))return 23;return 0;
}
static void *allocate(u32 n){u32 p,end;__asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");
 end=p+n;__asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;}
int run(void){u32 c,t;arena=allocate(0x400);if(!arena)return 97;expected=arena+0x200;
'''
    for i,label in enumerate(controls()):
        text+='if(variant(%s_%s,%d)!=%d)return %d;\n'%(source.FUNCTION,label,int(label=='selected'),0 if label=='selected'else 23,11 if label=='selected'else 40+i)
    text+='for(c=0;c<256;c++)for(t=0;t<256;t++)if(one(func_15169850_selected,c,t,0,0,1))return 70;\n'
    text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    return text


class PairReferenceEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER);at=fs[source.FUNCTION]['value']
        cls.words=list(struct.unpack_from('>41I',data,at));cls.truth=list(struct.unpack_from('>41I',cls.rom,source.ROM))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER);at=fs[source.FUNCTION]['value']
        cls.raw=list(struct.unpack_from('>41I',data,at));cls.helper=list(struct.unpack_from('>28I',cls.rom,RELEASE-0x15000000+0x2D4B0));cls.receipt={}

    def compare(self,case,phase=0,chain=False,images=None,entry=None,release=RELEASE):
        memory=fixture(case,phase);expected,calls=reference(memory,case,phase,release,chain)
        connected=dict(zip(range(RELEASE,RELEASE+112,4),self.helper))if chain else None
        models=[PairOracle(w,memory,case,phase,source.ENTRY if entry is None else entry,connected,release).run()for w in(images or(self.truth,self.words))]
        for m in models:self.assertEqual(public(m.memory,case,phase),public(expected,case,phase));self.assertEqual(m.calls,calls)
        for m in models[1:]:self.assertEqual(complete(models[0]),complete(m))
        return models[0]

    def test_01_raw_cycle_guards_actual_Make_and_neighbors(self):
        raw,bindings=source.payload(self.out/'after-owner.o');truth=source.payload(source.original(ROOT,self.out))
        self.assertEqual(source.normalized(raw,bindings),truth);self.assertEqual(self.words,self.truth)
        for at in source.EXPECTED:
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),bindings)
        with self.assertRaises(ValueError):source.normalized(raw,{})
        old=self.values['conker/retail_word_patches.us.csv'];new=source.guard_bytes(old);self.assertTrue(new.startswith(old));self.assertEqual(len(new.splitlines())-len(old.splitlines()),5)
        with self.assertRaises(ValueError):source.guard_bytes(new)
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual(q['preserved_neighbors'],41)
        self.assertTrue(json.loads((self.out/'make-shadow.json').read_text())['complete_padded_object_equal'])
        self.receipt.update(body_words=41,slot_words=44,alignment_words=3,new_guards=5,raw_real_word_differences=5,preserved_neighbors=41)

    def test_02_guest_byte_commands_aliases_and_raw_semantics(self):
        phases=aliases=0;visits=set()
        for command,match,tag,mode,phase in itertools.product(range(256),range(3),(0,255),(False,True),(0,8)):
            case=Case(command,command%6,match,tag,mutate=mode);m=self.compare(case,phase);visits.update(m.visits);phases+=1
        for command,pattern,match,tag,alias,phase in itertools.product((0,45,255),range(6),range(3),(0,128,255),range(8),(0,8)):
            case=Case(command,pattern,match,tag,alias);m=self.compare(case,phase);visits.update(m.visits);memory=fixture(case,phase);expected,calls=reference(memory,case,phase)
            raw=PairOracle(self.raw,memory,case,phase).run();self.assertEqual(public(raw.memory,case,phase),public(expected,case,phase));self.assertEqual(raw.calls,calls);aliases+=1
        for command in(0x12340000,0xFFFF002D,0xFFFFFF00,0xFFFFFFFF):self.compare(Case(command,2,1))
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+164,4))-visits,{source.ENTRY+0x7C})
        self.assertEqual(self.truth[31],self.truth[25]);self.assertEqual(self.truth[29],0x10000007)
        self.assertEqual(24+1+(self.truth[24]&65535),32)
        for command in(1,128,255):
            models=[PairOracle(w,fixture(Case(command)),Case(command),arguments=(0,command,0,0,0)).run()for w in(self.truth,self.words)]
            self.assertEqual(complete(models[0]),complete(models[1]));self.assertFalse(models[0].calls)
        self.receipt.update(guest_phases=phases,guest_alias_phases=aliases,all_40_reachable_words_visited=True,unreachable_body_words=1,
            ignored_unmapped_arguments=True,raw_C_public_semantics_verified=True,portable_private_alias_claimed=False)

    def test_03_native_actual_C_release_chain_and_controls(self):
        c=self.out/'native.c';c.write_text(native_harness(self.values))
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native-'+opt[1:]);p=subprocess.run(native_command(opt)+[str(c),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''),p.stdout+p.stderr)
            p=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''),opt)
        self.receipt.update(native_selected_cases_per_optimization=256*256*6*2,native_optimizations=3,trap_UBSan=True,defined_wrong_C_controls=10,native_real_release_C=True,native_direct_wrapper_cases=256*256)

    def test_04_all_call_sites_and_two_complete_retained_callers(self):
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertEqual([0x15000000+i-0x2D4B0 for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],list(SITES))
        self.assertFalse(any(self.rom[i:i+4]==struct.pack('>I',source.ENTRY)for i in range(0,len(self.rom),4)))
        phases=0
        for entry,n in((0x15149514,12),(0x150ECB4C,16)):
            at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],entry,n*4);rom=entry-0x15000000+0x2D4B0
            self.assertEqual(self.values['conker/build/conker.us.elf'][at:at+4*n],self.rom[rom:rom+4*n]);code=list(struct.unpack_from('>%dI'%n,self.rom,rom))
            for command,match,phase in itertools.product((0,45,128,255,0xABCD002D),range(3),(0,8)):
                case=Case(command,2,match);value,tag=locations(case,phase);args=(PAIR,command,value,tag,OWNER)if entry==0x15149514 else(OWNER,PAIR,command)
                models=[]
                for words in(self.truth,self.words):
                    m=PairOracle(code,fixture(case,phase),case,phase,entry,dict(zip(range(source.ENTRY,source.ENTRY+164,4),words)),arguments=args).run()
                    self.assertEqual(m.calls[0],(source.ENTRY,(PAIR,command&255,value,tag,OWNER)));models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));phases+=1
        self.receipt.update(original_direct_JAL_sites=27,complete_retained_callers=2,caller_phases=phases,all_27_parent_execution_claimed=False,caller_declarations_unchanged=True)

    def test_05_original_and_live_release_routing(self):
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,RELEASE,112);rom=RELEASE-0x15000000+0x2D4B0
        self.assertEqual(old[at:at+112],self.rom[rom:rom+112]);visits=set();phases=0
        for kind,callback,mutate,match,phase in itertools.product((0,1,2,255),(False,True),(False,True),(0,1),(0,8)):
            m=self.compare(Case(0,2,match,128,mutate=mutate,kind=kind,callback=callback),phase,True);visits.update(m.visits);phases+=1
        self.assertTrue(set(range(RELEASE,RELEASE+112,4))<=visits)
        self.receipt.update(retained_release_words=28,helper_phases=phases,all_28_release_words_visited=True,bookkeeping_destructor_and_fallback_providers_bounded=True)

    def linked(self,obj,entry,release,label):
        text,functions,bindings=source.parse_object(obj);asm,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,{'func_1516972C':release});self.assertFalse(unknown)
        p=self.out/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'--defsym=func_1516972C=0x%X'%release,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack_from('>41I',sections(p.with_suffix('.elf'))['.text'][1]))

    def test_06_GNU_rebases_and_fired_fault_prefixes(self):
        links=phases=cuts=0
        for i,(entry,release)in enumerate(((source.ENTRY,RELEASE),(0x18017FFC,0x18208000),(0x1A028000,0x1B04FFFC))):
            objects=(source.original(ROOT,self.out),self.out/'qualified-padded.o',self.out/'make-shadow/src/game_1944C0.c.o')
            images=[self.linked(obj,entry,release,'rebase-%d-%d'%(i,j))for j,obj in enumerate(objects)];links+=3;self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for command,alias,phase in itertools.product((0,45,255),range(8),(0,8)):
                self.compare(Case(command,2,0,255,alias),phase,images=images,entry=entry,release=release);phases+=1
        for command,match,alias,phase in itertools.product((0,45,255),range(3),range(8),(0,8)):
            case=Case(command,2,match,128,alias);memory=fixture(case,phase);done=PairOracle(self.truth,memory,case,phase).run()
            for cut in range(done.root_accesses):
                models=[PairOracle(w,memory,case,phase)for w in(self.truth,self.words)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=phases,fired_root_fault_prefixes=cuts,portable_C_fault_claimed=False)

    def test_07_strict_image_corruption_and_alignment(self):
        old=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+176];wanted=source.predicted_image(old,truth)
        positions=[0,len(wanted)-1,source.elf_slot_offset(old,source.ENTRY,176),source.elf_slot_offset(old,source.ENTRY+164,12),source.elf_slot_offset(old,RELEASE,4),source.elf_slot_offset(old,0x80082B20,4)]
        positions.extend(at+8 for at,name,_,_ in source.symbol_rows(old)if name==source.FUNCTION)
        for pos in positions:
            wrong=bytearray(wanted);wrong[pos]^=1
            with self.assertRaises(ValueError):source.check_image(old,bytes(wrong),truth)
        with self.assertRaises(ValueError):source.check_image(old,wanted[:-1],truth)
        with self.assertRaises(ValueError):source.predicted_image(old,bytes(176))
        self.assertEqual(truth[164:],bytes(12));self.receipt.update(strict_image_negatives=len(positions)+2,metadata_exclusions=0)

    def test_08_frozen_inputs_and_installed_identity(self):
        source.check_inputs(ROOT,self.out,self.installed)
        old=self.values['conker/retail_word_patches.us.csv'];self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),source.guard_bytes(old)if self.installed else old)
        self.receipt.update(focused_inputs=58,guard_prefix_byte_identical=True,installed=self.installed)


if __name__=='__main__':unittest.main()
