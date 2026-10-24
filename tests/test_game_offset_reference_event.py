"""Variable-tail event: raw semantics, fitted literal state and complete caller."""
from dataclasses import dataclass
from pathlib import Path
import csv
import io
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_offset_reference_event as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
PAIR,OWNER=0x20000,0x30000
REFS=(0x40000,0x44000,0x80040000,0xFFFF0000,0,0x140000)
RELEASE,BOOKKEEP,FALLBACK,CALLBACK,OTHER=0x1516972C,0x151696DC,0x15169804,0x16200000,0x15109064
PARENT,RELEASE_TABLE=0x1513BA78,0x8008B4D0


@dataclass(frozen=True)
class Case:
    command:int=0
    pattern:int=0
    match:int=0
    tag:int=255
    alias:int=0
    offset:int=0
    mutate:bool=False
    kind:int=2
    callback:bool=True


def tail_at(c,phase=0):
    return (OWNER+0xF8+c.offset,PAIR,PAIR+4,PAIR+8,PAIR-4,OWNER,STACK+phase+8)[c.alias]


def fixture(c,phase=0):
    tail=tail_at(c,phase);m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    for base,n in((PAIR-64,256),(OWNER-64,1024),(tail,8)):
        m.update({base+i:0xA5 for i in range(n)})
    first,second=REFS[c.pattern%6],REFS[(c.pattern+1)%6]
    put(m,PAIR,first);put(m,PAIR+4,second);m[PAIR+8]=17;m[PAIR+9]=231
    put(m,tail,(first,second,0x12340000)[c.match]);m[tail+4]=c.tag
    m[OWNER]=c.kind;m[OWNER+0x48]=2;put(m,OWNER+0x50,(tail-OWNER-0xF8)&0xFFFFFFFF)
    for kind in(c.kind,7,m[OWNER]):put(m,RELEASE_TABLE+52*kind,CALLBACK if c.callback else 0)
    current=c.command if c.alias==6 else read(m,tail)
    m.setdefault((current+0x3B)&0xFFFFFFFF,c.tag)
    return m


def mutation(m,c):
    if c.mutate:m[OWNER]=7;put(m,OWNER+0x50,0x80)


def reference(initial,c,phase=0,chain=False,home=True):
    m=dict(initial);calls=[]
    if home:put(m,STACK+phase+8,c.command)
    offset=read(m,OWNER+0x50);tail=(OWNER+offset+0xF8)&0xFFFFFFFF;current=read(m,tail)
    command=c.command&255
    if command==0:
        first=read(m,PAIR)
        if current==first or m[(current+0x3B)&0xFFFFFFFF]==m[PAIR+4]:
            calls.append((RELEASE,(OWNER,)))
            if chain:
                calls.append((BOOKKEEP,(OWNER,)));mutation(m,c)
                if m[OWNER]>=2:calls.append((CALLBACK if c.callback else FALLBACK,(OWNER,)))
            else:mutation(m,c)
    elif command==45:
        first=read(m,PAIR)
        if first==current:put(m,tail,read(m,PAIR+4));m[tail+4]=m[PAIR+9]
        elif read(m,PAIR+4)==current:put(m,tail,first);m[tail+4]=m[PAIR+8]
    return m,calls


def public(m,c,phase=0):
    tail=tail_at(c,phase)
    return {a:b for a,b in m.items()if not STACK-2048<=a<STACK+512 or tail<=a<tail+8}


def observable(m):
    return m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,tuple(m.r[i]for i in(*range(16,24),28,29,30,31))


class EventOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),phase=0,entry=source.ENTRY,connected=None,arguments=None,fault=None,release=RELEASE):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,
            arguments=arguments or(OWNER,PAIR,c.command),connected=connected)
        self.case,self.phase,self.root_fault,self.release=c,phase,fault,release

    def record_call(self,target):
        assert target in(source.ENTRY,self.release,BOOKKEEP,FALLBACK,CALLBACK,OTHER),('unbounded event service',hex(target))
        args=self.arguments(3 if target in(source.ENTRY,OTHER)else 1)
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        if target in(self.release,BOOKKEEP):mutation(self.memory,self.case)
        else:assert target in(FALLBACK,CALLBACK,OTHER)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678


def controls():
    b=source.SELECTED[source.FUNCTION]
    return dict(selected=b,and_gate=b.replace(' || ',' && '),wrong_command=b.replace('command == 0x2D','command == 0x2E'),
        wrong_tag=b.replace('reference[0x3B]','reference[0x3A]'),wrong_first_tag=b.replace('packet[9]','packet[8]'),
        wrong_second_tag=b.replace('packet[8]','packet[9]'),missing_second=b.replace('*(s32 *)(packet + 4) == current','0'),
        wrong_replacement=b.replace('link->value = *(s32 *)(packet + 4);','link->value = first;'),
        wrong_owner=b.replace('(struct102 *)owner','(struct102 *)packet'),missing_release=b.replace('func_1516972C((struct102 *)owner);',';'),
        early_tag=b.replace('link->value = *(s32 *)(packet + 4);\n                link->tag = packet[9];',
            'link->tag = packet[9];\n                link->value = *(s32 *)(packet + 4);'))


def native_harness(values):
    helper=values['conker/src/game_1944C0.c'].decode();lo,hi=source.function_span(helper,'func_1516972C');helper=helper[lo:hi].replace('func_1516972C','real_release')
    text=source.HEADERS+source.DECLARATIONS+'''
static u8 *arena,*expected,*currentOwner;static u32 error,releases,bookkeeps,callbacks,fallbacks,other,mutation,present,expectedRelease;
struct115 D_8008B4D0[256];
typedef char header_size[sizeof(struct132)==0x50?1:-1];
__attribute__((noinline,noclone)) void func_151696DC(void*p){if(p!=currentOwner)error=1;bookkeeps++;if(mutation){currentOwner[0]=7;*(u32*)(void*)(currentOwner+0x50)=0x80;}}
__attribute__((noinline,noclone)) void func_15169804(struct102*p){if((void*)p!=currentOwner)error=1;fallbacks++;}
static void callback(struct102*p){if((void*)p!=currentOwner)error=1;callbacks++;}
'''+helper+'''
__attribute__((noinline,noclone)) void func_1516972C(struct102*p){if(!expectedRelease||(void*)p!=currentOwner||releases++){error=1;return;}real_release(p);}
s32 func_15109064(struct132*p,s32 packet,u8 command){if((void*)p!=currentOwner||(void*)packet!=arena+0x100)error=1;other++;return 0;}
'''
    for name,body in controls().items():
        if name!='selected'and body==source.SELECTED[source.FUNCTION]:raise ValueError(name)
        text+=body.replace(source.FUNCTION,name)+'\n'
    parent=source.caller_owner(values[source.CALLER_SOURCE].decode());lo,hi=source.function_span(parent,'func_1513BA78')
    text+='void func_151BA468(struct132*,s32,u8);\n'
    text+=parent[lo:hi].replace('func_151BA468','active_handler')+'\n'
    text=text.replace('void func_151BA468(struct132*,s32,u8);','static void(*active_handler)(struct132*,s32,u8);')
    text+='''typedef void(*Handler)(struct132*,s32,u8);
static int one(Handler fn,u32 command,u32 tag,u32 alias,u32 mutate,u32 wrapper){
 u32 i,first,current,release,afterKind,invoke,selector=tag,tail,offset,at=0x300;
 static const s32 offsets[]={-0x80,0,0x80,0x200};
 tail=(u32[]){at+0xF8+offsets[(command>>1)&3],0x100,0x104,0x108,0xFC,at}[alias];offset=tail-at-0xF8;
 for(i=0;i<0x1000;i++)arena[i]=0xA5;
 *(u32*)(void*)(arena+0x100)=(u32)(arena+0x800);*(u32*)(void*)(arena+0x104)=(u32)(arena+0x900);
 arena[0x108]=17;arena[0x109]=231;arena[at]=(u8)(tag&3);arena[at+0x48]=(u8)selector;
 *(u32*)(void*)(arena+at+0x50)=offset;
 *(u32*)(void*)(arena+tail)=(u32)(arena+(tag%3==0?0x800:tag%3==1?0x900:0xA00));
 arena[tail+4]=(u8)tag;
 current=*(u32*)(void*)(arena+tail);((u8*)current)[0x3B]=(u8)tag;((u8*)current)[0x3A]=(u8)(tag+1);
 for(i=0;i<0x1000;i++)expected[i]=arena[i];
 first=*(u32*)(void*)(arena+0x100);invoke=!wrapper||selector==2;
 release=invoke&&(u8)command==0&&(current==first||((u8*)current)[0x3B]==arena[0x104]);
 if(invoke&&(u8)command==45){if(first==current){*(u32*)(void*)(expected+tail)=*(u32*)(void*)(expected+0x104);expected[tail+4]=expected[0x109];}
 else if(*(u32*)(void*)(expected+0x104)==current){*(u32*)(void*)(expected+tail)=first;expected[tail+4]=expected[0x108];}}
 mutation=mutate;present=tag&1;afterKind=arena[at];currentOwner=arena+at;
 if(release&&mutation){expected[at]=7;*(u32*)(void*)(expected+at+0x50)=0x80;afterKind=7;}
 for(i=0;i<256;i++)D_8008B4D0[i].unk0=present?callback:0;
 error=releases=bookkeeps=callbacks=fallbacks=other=0;expectedRelease=release;
 if(wrapper){active_handler=fn;func_1513BA78((struct132*)(void*)currentOwner,(s32)(arena+0x100),(u8)command);}
 else fn((struct132*)(void*)currentOwner,(s32)(arena+0x100),(u8)command);
 if(error||releases!=release||bookkeeps!=release||callbacks!=(release&&afterKind>=2&&present)||fallbacks!=(release&&afterKind>=2&&!present)||other!=(wrapper&&selector==1))return 23;
 for(i=0;i<0x1000;i++)if(arena[i]!=expected[i])return 23;return 0;
}
static int variant(Handler fn,u32 full){u32 c,t,a,m;
 for(c=0;c<(full?512u:3u);c++)for(t=0;t<256;t++)for(a=0;a<6;a++)for(m=0;m<2;m++)
  if(one(fn,full?c:(u32[]){0,45,255}[c],t,a,m,0))return 23;return 0;}
static void*allocate(u32 n){u32 p,end;__asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");
 end=p+n;__asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;}
int run(void){u32 c,t;arena=allocate(0x2000);if(!arena)return 97;expected=arena+0x1000;
'''
    for i,label in enumerate(controls()):text+='if(variant(%s,%d)!=%d)return %d;\n'%(label,int(label=='selected'),0 if label=='selected'else 23,11 if label=='selected'else 40+i)
    return text+'for(c=0;c<512;c++)for(t=0;t<256;t++)if(one(selected,c,t,0,0,1))return 70;\nreturn 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')


class OffsetReferenceEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.receipt={}
        if(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.old=cls.values['conker/build/conker.us.elf']
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER)
        cls.words=list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value']));cls.truth=list(struct.unpack_from('>44I',cls.rom,source.ROM))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER);cls.raw=list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value']))
        cls.helper=list(struct.unpack_from('>28I',cls.rom,RELEASE-0x15000000+0x2D4B0));cls.parent=list(struct.unpack_from('>23I',cls.rom,0x168F28))

    def compare(self,c,phase=0,chain=False):
        initial=fixture(c,phase);expected,calls=reference(initial,c,phase,chain)
        connected={RELEASE+4*i:w for i,w in enumerate(self.helper)}if chain else None
        models=[EventOracle(w,initial,c,phase,connected=connected).run()for w in(self.truth,self.raw,self.words)]
        for m in models:self.assertEqual(public(m.memory,c,phase),public(expected,c,phase),c);self.assertEqual(m.calls,calls,c)
        self.assertEqual(complete(models[0]),complete(models[2]));self.assertEqual(observable(models[0]),observable(models[1]));return models[0]

    def test_01_derived_lifetime_guard_body_neighbors_and_caller_prototype(self):
        self.assertEqual(self.words,self.truth);raw,rs=source.payload(self.out/'after-owner.o',source.FUNCTION)
        self.assertEqual(source.normalized(raw,rs),source.payload(source.original(ROOT,self.out,source.FUNCTION),source.FUNCTION))
        self.assertEqual(sum(a!=b for a,b in zip(self.raw,self.truth)),18)
        for i in range(44):
            bad=bytearray(raw);bad[4*i]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),rs)
        with self.assertRaises(ValueError):source.normalized(raw,{})
        with self.assertRaises(ValueError):source.normalized(raw[:-4],rs)
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual(q['preserved_neighbors'],56);self.assertEqual(q['caller_functions_preserved'],13)
        self.assertEqual([r['actual_Make_commands']for r in json.loads((self.out/'make-shadow.json').read_text())],[5,3])
        self.receipt.update(words=44,frame=24,bindings=1,new_guards=18,compiler_only=False,preserved_neighbors=56,
            caller_owner_functions_preserved=13,normalizer_negative_controls=46,caller_padded_object_identical=True)

    def test_02_byte_commands_reference_object_tags_offsets_and_aliases(self):
        count=0;visits=set()
        for command,pattern,match,phase in itertools.product(range(512),range(6),range(3),(0,8)):
            c=Case(command,pattern,match,(command*37+pattern)&255,offset=(-0x80,0,0x80,0x200)[pattern%4],mutate=bool(pattern&1))
            m=self.compare(c,phase);visits.update(m.visits);count+=1
        for command,tag,alias,match,phase in itertools.product((0,45,255,0x1234002D,0x80000000,0xFFFFFFFF),(0,17,231,255),range(7),range(3),(0,8)):
            m=self.compare(Case(command,4,match,tag,alias,mutate=True),phase);visits.update(m.visits);count+=1
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+176,4))-visits,{source.ENTRY+0x88})
        self.receipt.update(guest_root_phases=count,guest_alias_layouts=7,signed_tail_offsets=4,root_reachable_words_visited=43,
            unreachable_duplicate_words=1,full_incoming_A2_home_qualified=True,raw_volatile_registers_not_equated=True)

    def test_03_actual_retained_release_chain_late_kind_and_mutation(self):
        count=0;visits=set()
        for command,kind,present,mutate,match,phase in itertools.product((0,45,255),(0,1,2,255),(False,True),(False,True),range(3),(0,8)):
            m=self.compare(Case(command,2,match,0,mutate=mutate,kind=kind,callback=present),phase,True);visits.update(m.visits);count+=1
        self.assertTrue(set(range(RELEASE,RELEASE+112,4))<=visits)
        at=source.elf_slot_offset(self.old,RELEASE,112);self.assertEqual(self.old[at:at+112],struct.pack('>28I',*self.helper))
        self.receipt.update(retained_release_words=28,release_chain_phases=count,all_release_words_visited=True,bookkeep_destructor_fallback_bounded=True)

    def test_04_actual_complete_C_caller_and_original_kind_routing(self):
        ptr=struct.pack('>I',source.ENTRY);jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertFalse(any(self.rom[i:i+4]==ptr for i in range(0,len(self.rom),4)))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0x168F6C])
        at=source.elf_slot_offset(self.old,PARENT,92);self.assertEqual(self.old[at:at+92],struct.pack('>23I',*self.parent))
        count=0;visits=set()
        for selector,command,match in itertools.product(range(256),(0,45,255,0x1234002D),range(3)):
            c=Case(command,2,match,17,mutate=True);initial=fixture(c);initial[OWNER+0x48]=selector
            expected=dict(initial);calls=[]
            if selector==2:
                expected,calls=reference(initial,c,phase=-24);calls=[(source.ENTRY,(OWNER,PAIR,command&255)),*calls]
            elif selector==1:calls=[(OTHER,(OWNER,PAIR,command&255))]
            models=[]
            for words in(self.truth,self.raw,self.words):
                m=EventOracle(self.parent,initial,c,entry=PARENT,connected={source.ENTRY+4*i:w for i,w in enumerate(words)}).run()
                self.assertEqual(public(m.memory,c),public(expected,c));self.assertEqual(m.calls,calls);visits.update(m.visits);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[2]));self.assertEqual(observable(models[0]),observable(models[1]));count+=1
        self.assertTrue(set(range(PARENT,PARENT+92,4))<=visits)
        self.receipt.update(actual_parent_words=23,actual_parent_phases=count,all_256_selector_bytes=True,all_parent_words_visited=True,retained_parent_byte_exact=True)

    def test_05_native32_actual_root_parent_release_and_defined_controls(self):
        unit=self.out/'native32.c';unit.write_text(native_harness(self.values))
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native32'+opt);p=subprocess.run([*native_command(opt),str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,(p.stdout+p.stderr)[:12000]);p=subprocess.run([str(exe)],capture_output=True,timeout=180)
            self.assertEqual(p.returncode,0,(opt,p.stdout,p.stderr))
        self.receipt.update(native_optimizations=['O0','O2','O3'],native_root_cases_per_optimization=1572864,
            native_actual_parent_cases_per_optimization=131072,effective_wrong_C_controls=10,full_allocated_backing=True,
            trap_UBSan=True,actual_retained_parent_and_release_C_compiled=True,private_home_alias_native_claimed=False)

    def test_06_literal_fault_prefixes_and_ignored_packet_not_owner(self):
        count=0
        for c in(Case(45,0,0),Case(45,0,1),Case(0,0,2,255),Case(255),Case(45,alias=6)):
            initial=fixture(c);done=EventOracle(self.words,initial,c).run()
            for cut in range(done.root_accesses):
                models=[]
                for words in(self.truth,self.raw,self.words):
                    m=EventOracle(words,initial,c,fault=cut)
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(complete(models[0]),complete(models[2]));self.assertEqual(observable(models[0]),observable(models[1]));count+=1
        for command in(1,15,16,255,0xFFFFFFFF):
            c=Case(command);m=EventOracle(self.words,fixture(c),c,arguments=(OWNER,0,command)).run();self.assertFalse(m.calls)
            with self.assertRaises(AssertionError):EventOracle(self.words,fixture(c),c,arguments=(0,0,command)).run()
        self.receipt.update(fired_root_access_prefixes=count,ignored_NULL_packet_commands=5,ignored_commands_still_require_owner_tail=True,
            complete_fitted_private_state_equal=True,raw_public_memory_trace_saved_state_equal=True)

    def test_07_original_and_fitted_independent_GNU_rebases(self):
        from tools.experiments.game_actor_classifier_candidates import sections
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        links=count=0
        objects=(source.original(ROOT,self.out,source.FUNCTION),self.out/'qualified-padded.o',self.out/'make-shadow-target/src/game/generated_1E73B0.c.o')
        for index,(entry,target)in enumerate(((source.ENTRY,RELEASE),(0x18017FFC,0x18208000),(0x1A028000,0x1B04FFFC))):
            images=[]
            for k,obj in enumerate(objects):
                data,fs,rs=source.parse_object(obj);asm,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,{'func_1516972C':target});self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(index,k));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,
                    '--defsym=func_1516972C=0x%X'%target,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>44I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for command,alias,phase in itertools.product((0,45,255),range(7),(0,8)):
                c=Case(command,2,0,255,alias);initial=fixture(c,phase);expected,calls=reference(initial,c,phase)
                calls=[(target if t==RELEASE else t,args)for t,args in calls];models=[]
                for words in images:
                    m=EventOracle(words,initial,c,phase,entry=entry,release=target).run();models.append(m)
                    self.assertEqual(public(m.memory,c,phase),public(expected,c,phase));self.assertEqual(m.calls,calls)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=count)

    def test_08_strict_image_guard_history_and_real_padder_corruptions(self):
        bodies=source.truths(self.values);expected=source.predicted_image(self.old,bodies);self.assertEqual(expected,(self.out/'first-linked.elf').read_bytes())
        for at in(0,len(expected)-1,source.elf_slot_offset(expected,source.ENTRY,176)):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(self.old,bytes(bad),bodies)
        old=self.values['conker/retail_word_patches.us.csv'];wanted=source.guard_bytes(old,*source.payload(self.out/'after-owner.o',source.FUNCTION))
        self.assertTrue(wanted.startswith(old));rows=list(csv.DictReader(io.StringIO(wanted.decode())));prior=list(csv.DictReader(io.StringIO(old.decode())))
        self.assertEqual(rows[:-18],prior);self.assertTrue(all(r['function']==source.FUNCTION for r in rows[-18:]));self.assertEqual(sum(bool(r['insert_after']or r['omit']!='false')for r in rows[-18:]),0)
        from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,read_c_string
        obj=self.out/'after-owner.o';blob=bytearray(obj.read_bytes());header=ELF_HEADER.unpack_from(blob)
        sections=[SECTION_HEADER.unpack_from(blob,header[6]+i*header[11])for i in range(header[12])];strings=sections[header[13]];names=blob[strings[4]:strings[4]+strings[5]]
        text=next(s for s in sections if read_c_string(names,s[0])=='.text');_,fs,_=source.parse_object(obj)
        at=text[4]+fs[source.FUNCTION]['value']+0x18;blob[at+3]^=1;wrong=self.out/'wrong-expected.o';wrong.write_bytes(blob)
        with self.assertRaises(ValueError):source.emit_padded_assembly(wrong,ROOT/source.ASM,word_patches_path=self.out/'qualified-guards.csv',filename=source.OWNER)
        rows[-1]['expected_relocations']='R_MIPS_26:func_1516972C';stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[-1]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
        bad=self.out/'wrong-relocations.csv';bad.write_text(stream.getvalue())
        with self.assertRaises(ValueError):source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=bad,filename=source.OWNER)
        with self.assertRaises(ValueError):source.guard_bytes(old+b'\n',*source.payload(obj,source.FUNCTION))
        self.receipt.update(strict_image_negative_controls=3,actual_padder_corruptions=2,guard_history_preserved=True,
            guard_prefix_corruption_control=True,new_guard_rows=18,metadata_exclusions=0)
