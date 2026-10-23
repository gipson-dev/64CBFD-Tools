"""Masked 0x34-byte records: direct C, six-argument ABI and emitted order."""
from dataclasses import dataclass
from pathlib import Path
import itertools, json, struct, subprocess, unittest

from tools.experiments import game_masked_record_fields as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT = Path(__file__).resolve().parents[2]
SLOT, TABLE, OTHER, PACKET = 0x800D3098, 0x70000, 0x50000, 0x60000
PARENT, PARENT_ROM = 0x150A03B0, 0xCD860
WORDS = (0, 1, 255, 256, 0x12345678, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)
ALIASES = ('ordinary', 'global_byte', 'global_word', 'global_late_word',
           'home_mask_byte', 'home_mask_word', 'home_value1C', 'home_value20')


@dataclass(frozen=True)
class Case:
    index: int = 0
    mask: int = 15
    values: tuple = (0x12345678, 0x87654321, 0x80000000, 0xFFFFFFFF)
    alias: str = 'ordinary'


def pointer(c, sp, slot):
    off = (c.index * 52) & 0xFFFFFFFF
    bases = dict(ordinary=TABLE, global_byte=slot-0x14-off,
        global_word=slot-0x18-off, global_late_word=slot-0x1C-off,
        home_mask_byte=sp-0x10-off, home_mask_word=sp+4-0x18-off,
        home_value1C=sp+0x10-0x18-off, home_value20=sp+0x14-0x18-off)
    return bases[c.alias] & 0xFFFFFFFF


def fixture(c, phase=0, slot=SLOT):
    sp = STACK + phase
    m = {sp+i: (i*17+0xA5)&255 for i in range(-0x100, 0x100)}
    off = (c.index*52)&0xFFFFFFFF
    for base in (slot, (TABLE+off)&0xFFFFFFFF, (OTHER+off)&0xFFFFFFFF,
                 (pointer(c,sp,slot)+off)&0xFFFFFFFF):
        for i in range(-32, 80): m.setdefault((base+i)&0xFFFFFFFF, (i*13+37)&255)
    put(m, slot, pointer(c,sp,slot))
    put(m, sp+0x10, c.values[2]); put(m, sp+0x14, c.values[3])
    return m


def reference(c, memory, sp, slot=SLOT):
    m = dict(memory)
    put(m, sp+4, c.mask & 0xFFFFFFFF)
    mask = c.mask & 65535
    off = (c.index*52)&0xFFFFFFFF
    for bit, offset, size, value in ((1,0x17,1,c.values[0]), (2,0x18,4,c.values[1]),
            (4,0x1C,4,None), (8,0x20,4,None)):
        if mask & bit:
            address = (read(m,slot)+off+offset)&0xFFFFFFFF
            if bit == 4: value = read(m,sp+0x10)
            if bit == 8: value = read(m,sp+0x14)
            put(m,address,value & ((1 << (8*size))-1),size)
    return m


class FieldsOracle(TimingOracle):
    def __init__(self, words, c=Case(), phase=0, slot=SLOT, entry=source.ENTRY,
                 connected=None, memory=None, arguments=None):
        self.visits = set()
        args = (c.index&0xFFFFFFFF,c.mask&0xFFFFFFFF,*c.values) if arguments is None else arguments
        super().__init__(words,fixture(c,phase,slot) if memory is None else memory,
            phase=phase,entry=entry,arguments=args,connected=connected)

    def record_call(self, target):
        assert target == source.ENTRY, hex(target)
        args = self.arguments(6)
        self.calls.append((target,args)); self.events.append(('CALL',target,args))

    def hook(self, target):
        raise AssertionError(('Unexpected opaque helper', target))


def controls():
    b = source.SELECTED
    return dict(selected=b,
        bit1=b.replace('mask & 1)', 'mask & 2)'), bit2=b.replace('mask & 2)', 'mask & 4)'),
        bit4=b.replace('mask & 4)', 'mask & 8)'), bit8=b.replace('mask & 8)', 'mask & 1)'),
        byteValue=b.replace('field17 = value17', 'field17 = value18'),
        word18=b.replace('field18 = value18', 'field18 = value1C'),
        word1C=b.replace('field1C = value1C', 'field1C = value20'),
        word20=b.replace('field20 = value20', 'field20 = value18'),
        alwaysByte=b.replace('if (mask & 1)', 'if (1)'),
        anyMask=b.replace('if (mask & 1)', 'if (mask)'),
        nextIndex=b.replace('[index]', '[index + 1]'),
        clampByte=b.replace('field17 = value17', 'field17 = value17 > 255 ? 255 : value17'))


def native_harness():
    bodies = '\n'.join(body.replace(source.FUNCTION,name) for name,body in controls().items())
    checks = '\n'.join(('if(variant(%s)!=%d)return %d;' % (name,0 if name=='selected' else 23,30+i))
        for i,name in enumerate(controls()))
    return '''typedef unsigned char u8;typedef unsigned short u16;typedef short s16;typedef int s32;typedef unsigned int u32;
''' + source.DECLARATIONS + '''
GeneratedCDE80Record *D_800D3098;
typedef char record_size[sizeof(GeneratedCDE80Record)==52?1:-1];
typedef char byte_offset[__builtin_offsetof(GeneratedCDE80Record,field17)==23?1:-1];
typedef char word18_offset[__builtin_offsetof(GeneratedCDE80Record,field18)==24?1:-1];
typedef char word1C_offset[__builtin_offsetof(GeneratedCDE80Record,field1C)==28?1:-1];
typedef char word20_offset[__builtin_offsetof(GeneratedCDE80Record,field20)==32?1:-1];
static struct{u32 left[4];GeneratedCDE80Record nodes[7];u32 right[4];} actual,expected;
typedef void(*Update)(s32,u16,s32,s32,s32,s32);
''' + bodies + '''
static int one(Update fn,s32 index,u32 mask,u32 a,u32 b,u32 c,u32 d){
 u32 i;u8 *p=(u8*)&actual,*q=(u8*)&expected;
 for(i=0;i<sizeof(actual);i++)p[i]=q[i]=(u8)(i*13+37);
 D_800D3098=&actual.nodes[3];
 if(mask&1)expected.nodes[3+index].field17=(u8)a;
 if(mask&2)expected.nodes[3+index].field18=(s32)b;
 if(mask&4)expected.nodes[3+index].field1C=(s32)c;
 if(mask&8)expected.nodes[3+index].field20=(s32)d;
 fn(index,(u16)mask,(s32)a,(s32)b,(s32)c,(s32)d);
 if(D_800D3098!=&actual.nodes[3])return 23;
 for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 23;
 return 0;
}
static int variant(Update fn){
 const u32 words[]={0,1,255,256,0x12345678,0x7FFFFFFF,0x80000000,0xFFFFFFFF};
 u32 m,w,n=0;s32 i;
 for(m=0;m<65536;m++){if(one(fn,0,m,0x12345678,0x87654321,0x80000000,0xFFFFFFFF))return 23;n++;}
 for(i=-2;i<=2;i++)for(m=0;m<16;m++)for(w=0;w<8;w++){
  if(one(fn,i,m,words[w],words[(w+1)%8],words[(w+2)%8],words[(w+3)%8]))return 23;n++;
 }
 return n==66176?0:24;
}
static int run(void){
''' + checks + '''
 return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


class MaskedRecordFieldsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD; cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_text()==source.recovered_owner(cls.values[source.SOURCE].decode())
        if cls.installed: source.audit(ROOT,cls.out)
        else: source.qualify(ROOT,cls.out); source.make_shadow(ROOT,cls.out); source.predict(ROOT,cls.out)
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag: raise ValueError(diag)
        data,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER)
        cls.rom=cls.values['conker/conker.us.bin']
        cls.words=list(struct.unpack_from('>43I',data,fs[source.FUNCTION]['value']))
        cls.truth=list(struct.unpack_from('>43I',cls.rom,source.ROM))
        cls.receipt=dict(installed=cls.installed)

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)

    def compare(self,c,phase=0,images=None,slot=SLOT,entry=source.ENTRY):
        initial=fixture(c,phase,slot); expected=reference(c,initial,STACK+phase,slot); models=[]
        for words in images or (self.truth,self.words):
            m=FieldsOracle(words,c,phase,slot,entry,memory=initial).run()
            self.assertEqual(m.memory,expected,c);self.assertEqual(m.calls,[]);models.append(m)
        self.assertEqual(complete(models[0]),complete(models[1]));return models

    def test_01_direct_words_owner_Make_and_effective_stub(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(source.payload(self.obj),source.payload(source.original(ROOT,self.out)))
        q=json.loads((self.out/'qualification.json').read_text());m=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['relocations'],q['preserved_neighbors']),(43,0,4,27))
        self.assertEqual(m['actual_Make_commands'],5)
        self.assertEqual(q['raw_SHA256'],'1a386fb81ce4c3a1c28e6382dc9fd2f9e0e07ef2c1f8ac3aec1ebfd61eb43a15')
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,source.ENTRY,172)
        stale=FieldsOracle(struct.unpack_from('>43I',old,at)).run()
        self.assertNotEqual(stale.memory,self.compare(Case())[0].memory)
        self.receipt.update(words=43,frame=0,bindings=4,neighbors=q['preserved_neighbors'],new_guards=0,
            compiler_only=True,old_stub_rejected=True,actual_Make_commands=5)

    def test_02_guest_mask_words_indices_and_all_instruction_paths(self):
        count=0;visits=set()
        for mask,w,index,phase in itertools.product(range(16),range(8),(0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF),(0,8)):
            c=Case(index,mask|(0xA5A50000 if w&1 else 0),tuple(WORDS[(w+i)%8]for i in range(4)))
            m=self.compare(c,phase)[0];visits.update(m.visits);count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+172,4)))
        self.receipt.update(guest_phases=count,all43_words_visited=True,raw_mask_home_preserved=True,
            high_index_wrap_guest_only=True)

    def test_03_native32_all_masks_three_optimizations_and_twelve_defined_wrong_C(self):
        for opt in ('-O0','-O2','-O3'):
            p=self.out/('native'+opt);c=p.with_suffix('.c');c.write_text(native_harness())
            q=subprocess.run([*native_command(opt),str(c),'-o',str(p)],cwd=ROOT,capture_output=True,text=True)
            (self.out/('native'+opt+'-diagnostics.txt')).write_text(q.stdout+q.stderr)
            self.assertEqual(q.returncode,0,q.stdout+q.stderr)
            result=subprocess.run([str(p)],capture_output=True,timeout=60)
            self.assertEqual(result.returncode,0,(opt,result.stdout,result.stderr))
        self.receipt.update(native_cases_per_optimization=66176,exhaustive_u16_masks=65536,
            native_optimizations=['O0','O2','O3'],defined_wrong_C_controls=12,trap_UBSan=True,
            native_valid_indices_only=True,all_record_bytes_and_fences_checked=True)

    def linked(self,obj,entry,slot,label):
        data,fs,rs=source.parse_object(obj)
        asm,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,dict(D_800D3098=slot));self.assertFalse(unknown)
        p=self.out/label;a=p.with_suffix('.s');o=p.with_suffix('.o');ld=p.with_suffix('.ld');elf=p.with_suffix('.elf')
        a.write_text(asm);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(o),str(a)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,
            '--defsym=D_800D3098=0x%X'%slot,'-o',str(elf),str(o)],capture_output=True,check=True)
        return struct.unpack_from('>43I',sections(elf)['.text'][1])

    def test_04_independent_rebases_and_fired_root_access_prefixes(self):
        phases=cuts=0
        for i,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            slot=(SLOT,0x80348000,0x80457FFC)[i]
            images=[self.linked(obj,entry,slot,'rebase-%d-%d'%(i,j))for j,obj in enumerate((source.original(ROOT,self.out),self.obj,self.out/'qualified-padded.o'))]
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for mask,phase in itertools.product(range(16),(0,8)):
                self.compare(Case(mask=mask),phase,images[:2],slot,entry);phases+=1
        for alias,mask,phase in itertools.product(ALIASES,(0,1,2,4,8,15),(0,8)):
            c=Case(mask=mask,values=(0x80,OTHER,OTHER,0xFEDCBA98),alias=alias)
            good=FieldsOracle(self.truth,c,phase).run()
            for cut in range(good.root_accesses):
                models=[FieldsOracle(w,c,phase)for w in(self.truth,self.words)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=9,rebase_phases=phases,fired_root_access_prefixes=cuts,
            portable_C_fault_claimed=False)

    def test_05_actual_parent_selected_path_six_arguments_and_delay_store(self):
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF));ptr=struct.pack('>I',source.ENTRY)
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0xCD910])
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[])
        parent=struct.unpack_from('>74I',self.rom,PARENT_ROM)
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,0x8009F550,24)
        table=old[at:at+24];self.assertEqual(struct.unpack_from('>I',table,16)[0],0x150A0444)
        count=0
        self.assertFalse(STACK-0x100<=TABLE<STACK+0x108)
        for mask,index,phase in itertools.product((*range(16),0x8000,65535),(0,1,0xFFFFFFFF),(0,8)):
            c=Case(index,mask);initial=fixture(c,phase)
            for i,v in enumerate(table):initial[0x8009F550+i]=v
            for i in range(32):initial[PACKET+i]=(i*19+7)&255
            put(initial,PACKET+0xA,mask,2)
            for i,v in enumerate(c.values):put(initial,PACKET+0xC+4*i,v)
            setup=dict(initial)
            put(setup,STACK+phase-0x28+0x10,c.values[2])
            put(setup,STACK+phase-0x28+0x14,c.values[3])
            expected=reference(c,setup,STACK+phase-0x28)
            models=[]
            for words in(self.truth,self.words):
                connected={source.ENTRY+i*4:v for i,v in enumerate(words)}
                m=FieldsOracle(parent,c,phase,entry=PARENT,connected=connected,memory=initial,
                    arguments=(index,4,PACKET)).run()
                self.assertEqual(m.calls,[(source.ENTRY,(index,mask,*c.values))])
                self.assertEqual({a:v for a,v in m.memory.items()if not STACK-0x100<=a<STACK+0x108},
                    {a:v for a,v in expected.items()if not STACK-0x100<=a<STACK+0x108})
                self.assertEqual(m.r[2],0);self.assertIn(0x150A0464,m.visits)
                self.assertEqual(read(m.memory,STACK+phase-0x28+0x10),c.values[2])
                self.assertEqual(read(m.memory,STACK+phase-0x28+0x14),c.values[3]);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        at=source.elf_slot_offset(old,PARENT,12)
        self.assertEqual(struct.unpack_from('>3I',old,at),(0x00001025,0x03E00008,0))
        self.receipt.update(actual_parent_selected_path_phases=count,parent_frame=40,parent_words=74,
            actual_caller_window_words=9,JAL_delay_stack_store_executed=True,parent_stub_bytes=12,
            all_six_parent_cases_qualified=False,parent_recovery_claimed=False)

    def test_06_guest_pointer_and_home_aliases(self):
        count=0
        for alias,mask,high,phase in itertools.product(ALIASES,range(16),(0,0xFFFF0000),(0,8)):
            self.compare(Case(mask=mask|high,values=(0x80,OTHER,OTHER,0xFEDCBA98),alias=alias),phase);count+=1
        self.receipt.update(guest_alias_phases=count,guest_alias_kinds=list(ALIASES),
            portable_C_private_home_or_global_pointer_alias_claimed=False)

    def test_07_shape_control_and_effective_cached_pointer_guest_negative(self):
        narrow=source.SELECTED.replace('s32 value17','u8 value17')
        obj,diag=source.compile_owner(ROOT,self.out,'#include <ultra64.h>\n'+source.DECLARATIONS+narrow,'narrow-shape')
        self.assertFalse(diag);raw,_=source.payload(obj)
        self.assertEqual(len(raw)//4,46);self.assertNotEqual(source.payload(obj),source.payload(self.obj))
        cached=source.SELECTED.replace('    if (mask & 1)',
            '    GeneratedCDE80Record *table = D_800D3098;\n    if (mask & 1)',1).replace('D_800D3098[index]','table[index]')
        obj,diag=source.compile_owner(ROOT,self.out,'#include <ultra64.h>\n'+source.DECLARATIONS+cached,'cached-pointer')
        self.assertFalse(diag);raw,_=source.payload(obj);data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER)
        words=struct.unpack_from('>%dI'%(len(raw)//4),data,fs[source.FUNCTION]['value'])
        c=Case(values=(0x80,OTHER,OTHER,0xFEDCBA98),alias='global_word')
        bad=FieldsOracle(words,c).run();good=self.compare(c)[0]
        self.assertNotEqual(read(bad.memory,OTHER+0x1C),read(good.memory,OTHER+0x1C))
        self.receipt.update(narrow_argument_shape_words=46,narrow_shape_not_functional_negative=True,
            cached_pointer_rejected_by_guest_output=True,no_native_alias_equivalence_claimed=True)

    def test_08_history_strict_image_and_guard_identity(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+172]
        pred=source.predicted_image(before,truth);source.check_image(before,pred,truth)
        at=source.elf_slot_offset(before,source.ENTRY,172)
        for pos in(0,at-1,at,at+168,at+172,len(before)-1):
            wrong=bytearray(pred);wrong[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        with self.assertRaises(ValueError):source.check_image(before,pred[:-1],truth)
        for name,wanted in source.INPUTS.items():
            old=self.values[name];self.assertEqual(source.digest(old),wanted)
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else pred if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),expected,name)
        self.receipt.update(pinned_inputs=len(source.INPUTS),strict_image_negatives=7,guard_manifest_unchanged=True)
