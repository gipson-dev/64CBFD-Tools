"""Actor reference callback: derived branch swap, actual dispatcher and strict image."""
from dataclasses import dataclass
from pathlib import Path
import csv
import io
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_owner_reference_event as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
PAIR,OWNER,NEXT=0x20000,0x30000,0x34000
RELEASE,BOOKKEEP,FALLBACK,CALLBACK=0x1516972C,0x151696DC,0x15169804,0x16200000
PARENT,TABLE,RELEASE_TABLE=0x15149434,0x8008A8D8,0x8008B4D0
VALUES=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678)


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


def owner_at(c,phase=0):
    return (OWNER,PAIR-0x28,PAIR-0x24,PAIR-0x20,PAIR-0x2C,PAIR,STACK+phase-32)[c.alias]


def fixture(c,phase=0):
    owner=owner_at(c,phase);m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    for base,n in ((PAIR-64,256),(owner-32,128)):
        m.update({base+i:0xA5 for i in range(n)})
    first,second=VALUES[c.pattern%6],VALUES[(c.pattern+1)%6]
    put(m,PAIR,first);put(m,PAIR+4,second);m[PAIR+8]=17;m[PAIR+9]=231
    put(m,owner+0x28,(first,second,0xBEEFF00D)[c.match]);m[owner+0x2C]=c.tag;m[owner]=c.kind
    for kind in (c.kind,7):put(m,RELEASE_TABLE+52*kind,CALLBACK if c.callback else 0)
    return m


def mutation(m,c,owner):
    if c.mutate:m[owner]=7;put(m,owner+0x28,0xCAFEBABE)


def reference(initial,c,phase=0,chain=False,owner=None):
    owner=owner_at(c,phase) if owner is None else owner;m=dict(initial);calls=[]
    # The byte parameter has a full incoming register home, including its upper bits.
    put(m,STACK+phase+8,c.command)
    command=c.command&255
    if command==45:
        first=read(m,PAIR);current=read(m,owner+0x28)
        if first==current:put(m,owner+0x28,read(m,PAIR+4));m[owner+0x2C]=m[PAIR+9]
        elif read(m,PAIR+4)==current:put(m,owner+0x28,first);m[owner+0x2C]=m[PAIR+8]
    elif command==0:
        first=read(m,PAIR)
        if first==read(m,owner+0x28) or m[owner+0x2C]==m[PAIR+4]:
            calls.append((RELEASE,(owner,)))
            if chain:
                calls.append((BOOKKEEP,(owner,)));mutation(m,c,owner)
                if m[owner]>=2:calls.append((CALLBACK if c.callback else FALLBACK,(owner,)))
            else:mutation(m,c,owner)
    return m,calls


def public(m,c,phase=0):
    owner=owner_at(c,phase)
    return {a:b for a,b in m.items() if not STACK-2048<=a<STACK+512 or owner+0x28<=a<owner+0x2D}


class PairOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),phase=0,entry=source.ENTRY,connected=None,arguments=None,fault=None,release=RELEASE):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,
            arguments=arguments or(owner_at(c,phase),PAIR,c.command),connected=connected)
        self.case,self.owner,self.phase=c,owner_at(c,phase),phase
        self.root_fault,self.release=fault,release

    def record_call(self,target):
        assert target in(source.ENTRY,self.release,BOOKKEEP,FALLBACK,CALLBACK),('unbounded reference service',hex(target))
        args=self.arguments(3 if target==source.ENTRY else 1)
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        if target in(self.release,BOOKKEEP):mutation(self.memory,self.case,self.arguments(1)[0])
        else:assert target in(FALLBACK,CALLBACK)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678


def controls():
    b=source.SELECTED[source.FUNCTION]
    return dict(selected=b,
        and_gate=b.replace(' || ',' && '),
        wrong_command=b.replace('command == 0x2D','command == 0x2E'),
        wrong_release_gate=b.replace('command == 0)', 'command == 1)'),
        wrong_identity=b.replace('packet[4]','packet[5]'),
        wrong_first_tag=b.replace('packet[9]','packet[8]'),
        wrong_second_tag=b.replace('packet[8]','packet[9]'),
        missing_second=b.replace('*(s32 *)(packet + 4) == current','0'),
        wrong_replacement=b.replace('link->value = *(s32 *)(packet + 4);','link->value = first;'),
        wrong_owner=b.replace('(struct102 *)owner','(struct102 *)packet'),
        early_tag=b.replace('link->value = *(s32 *)(packet + 4);\n                link->tag = packet[9];',
            'link->tag = packet[9];\n                link->value = *(s32 *)(packet + 4);'))


def native_harness(values):
    text=values['conker/src/game_1944C0.c'].decode();lo,hi=source.function_span(text,'func_1516972C')
    helper=text[lo:hi].replace('func_1516972C','real_release')
    text=source.HEADERS+source.DECLARATIONS+'''
static u8 *arena,*expected;static u32 error,releases,bookkeeps,callbacks,fallbacks,mutation,present,expectedRelease;
static u8 *currentOwner;struct115 D_8008B4D0[256];\nvoid(*D_8008A8D8[74])(struct260*,s32,u8);
typedef char stride[sizeof(struct115)==52?1:-1];
__attribute__((noinline,noclone)) void func_151696DC(void *p){if(p!=currentOwner)error=1;bookkeeps++;if(mutation){currentOwner[0]=7;*(s32*)(void*)(currentOwner+0x28)=(s32)0xCAFEBABE;}}
__attribute__((noinline,noclone)) void func_15169804(struct102 *p){if((void*)p!=currentOwner)error=1;fallbacks++;}
static void callback(struct102 *p){if((void*)p!=currentOwner)error=1;callbacks++;}
'''+helper+'''
__attribute__((noinline,noclone)) void func_1516972C(struct102*p){if(!expectedRelease||(void*)p!=currentOwner||releases++){error=1;return;}real_release(p);}
'''
    for label,body in controls().items():
        if label!='selected' and body==source.SELECTED[source.FUNCTION]:raise ValueError('Ineffective control '+label)
        text+=body.replace(source.FUNCTION,label)+'\n'
    parent=values['conker/src/game/done/game_1765E0.c'].decode();lo,hi=source.function_span(parent,'func_15149434')
    text+=parent[lo:hi]+'\n'
    text+='''typedef void(*Handler)(struct260*,s32,u8);
static const u32 vals[]={0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678};
static int one(Handler fn,u32 command,u32 tag,u32 alias,u32 mutate,u32 wrapper){
 u32 i,pattern=command%6,match=tag%3,kind=(tag&3)==3?255:tag&3;
 u32 ownerAt=(u32[]){0xA0,0x40-0x28,0x40-0x24,0x40-0x20,0x40-0x2C,0x40}[alias];
 u32 value=ownerAt+0x28,tagAt=ownerAt+0x2C;u32 first,current,release,afterKind,invoke;
 for(i=0;i<0x200;i++)arena[i]=0xA5;
 *(u32*)(void*)(arena+0x40)=vals[pattern];*(u32*)(void*)(arena+0x44)=vals[(pattern+1)%6];arena[0x48]=17;arena[0x49]=231;
 *(u32*)(void*)(arena+value)=match==0?*(u32*)(void*)(arena+0x40):match==1?*(u32*)(void*)(arena+0x44):0xBEEFF00D;
 arena[tagAt]=(u8)tag;arena[ownerAt]=(u8)kind;arena[ownerAt+0x13]=(u8)tag;
 for(i=0;i<0x200;i++)expected[i]=arena[i];
 first=*(u32*)(void*)(arena+0x40);current=*(u32*)(void*)(arena+value);
 invoke=!wrapper||tag==35||((tag==0||tag>=74)&&(command&256));\n release=invoke&&(u8)command==0&&(first==current||arena[tagAt]==arena[0x44]);
 if(invoke&&(u8)command==45){if(first==current){*(u32*)(void*)(expected+value)=*(u32*)(void*)(expected+0x44);expected[tagAt]=expected[0x49];}
 else if(*(u32*)(void*)(expected+0x44)==current){*(u32*)(void*)(expected+value)=first;expected[tagAt]=expected[0x48];}}
 mutation=mutate;present=tag&1;afterKind=kind;currentOwner=arena+ownerAt;
 if(release&&mutation){expected[ownerAt]=7;*(u32*)(void*)(expected+value)=0xCAFEBABE;afterKind=7;}
 for(i=0;i<256;i++)D_8008B4D0[i].unk0=present?callback:0;
 error=releases=bookkeeps=callbacks=fallbacks=0;expectedRelease=release;
 if(wrapper){for(i=0;i<74;i++)D_8008A8D8[i]=0;D_8008A8D8[35]=fn;D_8008A8D8[0]=command&256?fn:0;
 func_15149434((struct260*)(void*)currentOwner,(s32)(arena+0x40),(u8)command);}
 else fn((struct260*)(void*)currentOwner,(s32)(arena+0x40),(u8)command);
 if(error||releases!=release||bookkeeps!=release||callbacks!=(release&&afterKind>=2&&present)||fallbacks!=(release&&afterKind>=2&&!present))return 23;
 for(i=0;i<0x200;i++)if(arena[i]!=expected[i])return 23;
 return 0;
}
static int variant(Handler fn,u32 full){u32 c,t,a,m;
 for(c=0;c<(full?512u:3u);c++)for(t=0;t<256;t++)for(a=0;a<6;a++)for(m=0;m<2;m++)
  if(one(fn,full?c:(u32[]){0,45,255}[c],t,a,m,0))return 23;return 0;}
static void *allocate(u32 n){u32 p,end;__asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");
 end=p+n;__asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;}
int run(void){u32 c,t;arena=allocate(0x400);if(!arena)return 97;expected=arena+0x200;
'''
    for i,label in enumerate(controls()):text+='if(variant(%s,%d)!=%d)return %d;\n'%(label,int(label=='selected'),0 if label=='selected' else 23,11 if label=='selected' else 40+i)
    text+='for(c=0;c<512;c++)for(t=0;t<256;t++)if(one(selected,c,t,0,0,1))return 70;\nreturn 0;}\n'
    return text+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')


class OwnerReferenceEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.receipt={}
        if (ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.old=cls.values['conker/build/conker.us.elf']
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER);at=fs[source.FUNCTION]['value']
        cls.words=list(struct.unpack_from('>43I',data,at));cls.truth=list(struct.unpack_from('>43I',cls.rom,source.ROM))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
        cls.raw=list(struct.unpack_from('>43I',data,fs[source.FUNCTION]['value']))
        cls.helper=list(struct.unpack_from('>28I',cls.rom,RELEASE-0x15000000+0x2D4B0))
        cls.parent=list(struct.unpack_from('>23I',cls.rom,PARENT-0x15000000+0x2D4B0))

    def compare(self,c,phase=0,chain=False):
        initial=fixture(c,phase);expected,calls=reference(initial,c,phase,chain)
        connected={RELEASE+4*i:w for i,w in enumerate(self.helper)} if chain else None
        models=[PairOracle(w,initial,c,phase,connected=connected).run() for w in (self.truth,self.raw,self.words)]
        for m in models:self.assertEqual(public(m.memory,c,phase),public(expected,c,phase),c);self.assertEqual(m.calls,calls,c)
        for m in models[1:]:self.assertEqual(complete(models[0]),complete(m))
        return models[0]

    def test_01_complete_guarded_body_tail_owner_and_make(self):
        self.assertEqual(self.words,self.truth);raw,rs=source.payload(self.out/'after-owner.o',source.FUNCTION)
        self.assertEqual(rs,source.BINDINGS);self.assertEqual(len(raw),172)
        self.assertEqual(source.normalized(raw,rs),source.payload(source.original(ROOT,self.out,source.FUNCTION),source.FUNCTION))
        self.assertEqual([i for i,(a,b)in enumerate(zip(self.raw,self.truth))if a!=b],[34])
        for index in range(43):
            bad=bytearray(raw);bad[index*4]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),rs)
        with self.assertRaises(ValueError):source.normalized(raw,{})
        with self.assertRaises(ValueError):source.normalized(raw[:-4],rs)
        self.assertEqual(self.rom[source.ROM+172:source.ROM+176],bytes(4))
        self.assertEqual(json.loads((self.out/'qualification.json').read_text())['preserved_neighbors'],5)
        self.receipt.update(body_words=43,slot_words=44,alignment_words=1,frame=24,bindings=1,new_guards=1,
            compiler_only=False,preserved_neighbors=5,original_unreachable_duplicate_word_retained=True,
            raw_normalizer_negative_controls=45,raw_differences=1)

    def test_02_byte_commands_reference_tags_alias_order_and_mutations(self):
        count=0;visits=set()
        for command,pattern,match,phase in itertools.product(range(512),range(6),range(3),(0,8)):
            m=self.compare(Case(command,pattern,match,(command*37+pattern)&255,mutate=bool(pattern&1)),phase);visits.update(m.visits);count+=1
        for command,tag,alias,match,phase in itertools.product((0,45,255,0x1234002D,0x80000000,0xFFFFFFFF),(0,17,231,255),range(7),range(3),(0,8)):
            m=self.compare(Case(command,4,match,tag,alias,True),phase);visits.update(m.visits);count+=1
        root=set(range(source.ENTRY,source.ENTRY+172,4));self.assertEqual(root-visits,{source.ENTRY+0x84})
        self.receipt.update(guest_root_phases=count,guest_alias_layouts=7,all_42_executable_root_words_visited=True,
            unreachable_duplicate_load_words=1,full_incoming_byte_register_home_qualified=True,stack_phases=2)

    def test_03_retained_release_helper_late_kind_and_callback_chain(self):
        count=0;visits=set()
        for command,kind,callback,mutate,match,phase in itertools.product((0,45,255),(0,1,2,255),(False,True),(False,True),range(3),(0,8)):
            m=self.compare(Case(command,2,match,0,0,mutate,kind,callback),phase,True);visits.update(m.visits);count+=1
        self.assertTrue(set(range(RELEASE,RELEASE+112,4))<=visits)
        at=source.elf_slot_offset(self.old,RELEASE,112);self.assertEqual(list(struct.unpack_from('>28I',self.old,at)),self.helper)
        self.receipt.update(retained_release_words=28,release_chain_phases=count,all_release_words_visited=True,
            bookkeep_destructor_and_fallback_bounded=True)

    def test_04_registration_full_original_and_retained_dispatcher(self):
        ptr=struct.pack('>I',source.ENTRY);jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[0x22F424])
        self.assertFalse(any(self.rom[i:i+4]==jal for i in range(0,len(self.rom),4)))
        self.assertEqual(TABLE+35*4,0x8008A964)
        for entry,data in((0x8008A964,ptr),(PARENT,struct.pack('>23I',*self.parent))):
            at=source.elf_slot_offset(self.old,entry,len(data));self.assertEqual(self.old[at:at+len(data)],data)
        visits=set();count=0
        for selector,base,command,match in itertools.product(range(256),(False,True),(0,45,255,0x1234002D),range(3)):
            c=Case(command,2,match,17,mutate=True);initial=fixture(c);initial[OWNER+0x13]=selector
            for i in range(74):put(initial,TABLE+4*i,source.ENTRY if i==35 or(i==0 and base)else 0)
            selected=selector if selector<74 else 0
            expected=dict(initial);calls=[]
            if selected==35 or(selected==0 and base):
                expected,calls=reference(initial,c,phase=-24)
                calls=[(source.ENTRY,(OWNER,PAIR,command&255)),*calls]
            models=[]
            for words in(self.truth,self.raw,self.words):
                connected={source.ENTRY+4*i:w for i,w in enumerate(words)}
                m=PairOracle(self.parent,initial,c,entry=PARENT,connected=connected).run()
                self.assertEqual(public(m.memory,c),public(expected,c));self.assertEqual(m.calls,calls)
                visits.update(m.visits);models.append(m)
            for m in models[1:]:self.assertEqual(complete(models[0]),complete(m))
            count+=1
        self.assertTrue(set(range(PARENT,PARENT+92,4))<=visits)
        self.receipt.update(actual_parent_words=23,actual_parent_phases=count,registration_index=35,
            all_256_selector_bytes_qualified=True,table_entries=74,null_and_index_zero_fallback_qualified=True,
            all_parent_words_visited=True,retained_parent_byte_exact=True)

    def test_05_native32_actual_root_helper_and_typed_descriptor_interface(self):
        unit=self.out/'native32.c';unit.write_text(native_harness(self.values))
        for opt in ('-O0','-O2','-O3'):
            exe=self.out/('native32'+opt);p=subprocess.run([*native_command(opt),str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,(p.stdout+p.stderr)[:12000]);p=subprocess.run([str(exe)],capture_output=True,timeout=90)
            self.assertEqual(p.returncode,0,(opt,p.stdout,p.stderr))
        self.receipt.update(native_optimizations=['O0','O2','O3'],native_selected_cases_per_optimization=1572864,
            native_actual_parent_cases_per_optimization=131072,effective_wrong_C_controls=10,
            full_allocated_owner_and_pair_alias_backing=True,trap_UBSan=True,private_stack_alias_native_claimed=False,
            actual_retained_release_C_compiled=True,full_native_parent_claimed=True)

    def test_06_literal_access_fault_prefixes_and_ignored_packet_boundaries(self):
        count=0
        for c in (Case(45,0,0),Case(45,0,1),Case(0,0,2,255),Case(255,0,0)):
            initial=fixture(c);base=PairOracle(self.words,initial,c).run()
            for fault in range(base.root_accesses):
                models=[]
                for w in (self.truth,self.raw,self.words):
                    m=PairOracle(w,initial,c,fault=fault)
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                for m in models[1:]:self.assertEqual(complete(models[0]),complete(m))
                count+=1
        for command in (1,15,16,255,0xFFFFFFFF):
            c=Case(command);m=PairOracle(self.words,fixture(c),c,arguments=(0,0,command)).run();self.assertFalse(m.calls)
        self.receipt.update(fired_root_access_prefixes=count,ignored_NULL_owner_and_pair_commands=5,
            complete_private_guest_state_equal=True)

    def test_07_symbolic_bindings_and_independent_rebases(self):
        from tools.experiments.game_actor_classifier_candidates import sections
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        raw,bindings=source.payload(self.out/'after-owner.o',source.FUNCTION)
        truth,rs=source.payload(source.original(ROOT,self.out,source.FUNCTION),source.FUNCTION)
        self.assertEqual(source.normalized(raw,bindings),(truth,rs))
        links=phases=0
        objects=(source.original(ROOT,self.out,source.FUNCTION),self.out/'qualified-padded.o',
            self.out/'make-shadow-target/src/game/generated_E2880.c.o')
        for index,(entry,target) in enumerate(((source.ENTRY,RELEASE),(0x18017FFC,0x18208000),(0x1A028000,0x1B04FFFC))):
            images=[]
            for j,obj in enumerate(objects):
                text,functions,bindings=source.parse_object(obj)
                asm,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,{'func_1516972C':target})
                self.assertFalse(unknown);p=self.out/('rebase-%d-%d'%(index,j))
                p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,
                    '--defsym=func_1516972C=0x%X'%target,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>43I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for command,alias,phase in itertools.product((0,45,255),range(7),(0,8)):
                c=Case(command,2,0,255,alias);initial=fixture(c,phase);expected,calls=reference(initial,c,phase)
                calls=[(target if t==RELEASE else t,a)for t,a in calls];models=[]
                for words in images:
                    m=PairOracle(words,initial,c,phase,entry=entry,release=target).run()
                    self.assertEqual(public(m.memory,c,phase),public(expected,c,phase));self.assertEqual(m.calls,calls);models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));phases+=1
        self.receipt.update(symbolic_fitted_original_payloads_identical=True,independent_GNU_links=links,rebase_phases=phases)

    def test_08_strict_whole_image_and_entire_guard_file(self):
        bodies=source.truths(self.values);before=self.old;expected=source.predicted_image(before,bodies)
        self.assertEqual(expected,(self.out/'first-linked.elf').read_bytes())
        for at in (0,len(expected)-1,source.elf_slot_offset(expected,source.ENTRY,176)):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),bodies)
        bad=dict(bodies);bad[source.FUNCTION]=bytes(176)
        with self.assertRaises(ValueError):source.predicted_image(before,bad)
        old=self.values['conker/retail_word_patches.us.csv'];wanted=source.guard_bytes(old,*source.payload(self.out/'after-owner.o',source.FUNCTION))
        self.assertTrue(wanted.startswith(old))
        current=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();self.assertIn(current,(old,wanted))
        rows=list(csv.DictReader(io.StringIO(wanted.decode())));prior=list(csv.DictReader(io.StringIO(old.decode())))
        self.assertEqual(rows[:-1],prior);self.assertEqual(rows[-1]['function'],source.FUNCTION)
        from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,read_c_string
        obj=self.out/'after-owner.o';blob=bytearray(obj.read_bytes());header=ELF_HEADER.unpack_from(blob)
        sections=[SECTION_HEADER.unpack_from(blob,header[6]+i*header[11])for i in range(header[12])]
        names=sections[header[13]];strings=blob[names[4]:names[4]+names[5]]
        section=next(x for x in sections if read_c_string(strings,x[0])=='.text')
        _,functions,_=source.parse_object(obj);at=section[4]+functions[source.FUNCTION]['value']+0x88
        blob[at+3]^=1;wrong=self.out/'wrong-expected.o';wrong.write_bytes(blob)
        with self.assertRaises(ValueError):
            source.emit_padded_assembly(wrong,ROOT/source.ASM,word_patches_path=self.out/'qualified-guards.csv',filename=source.OWNER)
        rows[-1]['expected_relocations']='R_MIPS_26:func_1516972C'
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[-1]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows);bad=self.out/'wrong-relocations.csv';bad.write_text(stream.getvalue())
        with self.assertRaises(ValueError):
            source.emit_padded_assembly(obj,ROOT/source.ASM,word_patches_path=bad,filename=source.OWNER)
        with self.assertRaises(ValueError):source.guard_bytes(old+b'\n',*source.payload(obj,source.FUNCTION))
        self.receipt.update(strict_image_negative_controls=4,metadata_exclusions=0,guard_prefix_unchanged=True,
            new_guard_rows=1,actual_padder_corruptions=2,guard_prefix_corruption_control=True)
