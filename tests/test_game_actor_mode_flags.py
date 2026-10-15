"""Real-table actor dispatch, raw owner isolation, native32 and fault-prefix checks."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_mode_flags as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments import game_texture_vertex_span_returns as returns
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import test_game_actor_mask_scan_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object

ACTOR=0x21000
PATTERNS=(0,1,0xFFFFFFFF,0xAAAAAAAA,0x55555555,0x80000000,0x7FFFFFFF,0xDEADBEEF)
MODES=(*range(-2,13),0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x10004)


def fixture(a,b,mask=0x87654321):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x100,0x140)}
    memory.update({ACTOR+i:(i*13+0x5A)&255 for i in range(-16,0x32C+16)})
    for offset,value in ((0x94,a),(0x9C,b),(0x2E4,mask)):
        put(memory,ACTOR+offset,value)
    for i,offset in enumerate(source.TABLE_OFFSETS):
        put(memory,source.TABLE+i*4,source.ENTRY+offset)
    return memory


def reference(memory,mode):
    result=dict(memory)
    a,b,mask=[read(memory,ACTOR+x) for x in (0x94,0x9C,0x2E4)]
    mode&=0xFFFFFFFF
    if mode==9:
        a,b,mask=a|0x20,b|0x78,1
    elif mode==8:
        a,b,mask=(a|0x40)&~0x200,b|0xF00,2
    elif mode in (6,7):
        a,b,mask=(a|0xE)&~0x410,b|0xEE0000,4
    elif mode in (4,5):
        a,mask=(a|0x80)&~0x500,8
    for offset,value in ((0x94,a),(0x9C,b),(0x2E4,mask)):
        put(result,ACTOR+offset,value)
    return result


class ModeOracle(machine.MaskOracle):
    def __init__(self,words,memory,mode,phase=0,fault=None,entry=source.ENTRY):
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(ACTOR,mode&0xFFFFFFFF),fault=fault)
        self.current_pc=self.delay_of=None
        self.code=faults.TrackedCode(self.code,self)


def state(instance):
    return (tuple(instance.r),tuple(instance.f),dict(instance.memory),list(instance.events),
        instance.current_pc,instance.delay_of,instance.accesses,tuple(instance.calls))


def native_program(body,rows):
    cases=[]
    for mode,a,b in rows:
        m=reference(fixture(a,b),mode)
        cases.append('{'+','.join('0x%Xu'%(value&0xFFFFFFFF) for value in
            (mode,a,b,read(m,ACTOR+0x94),read(m,ACTOR+0x9C),read(m,ACTOR+0x2E4)))+'}')
    return '''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
typedef struct {u8 pad0[0x94];u32 unk94;u8 pad98[4];u32 unk9C;u8 padA0[0x244];s32 unk2E4;u8 tail[0x44];} struct127;
typedef struct{u32 mode,a,b,expectedA,expectedB,expectedMask;} Case;
static Case cases[]={'''+',\n'.join(cases)+'''};
static u32 bank[211];
'''+body+'''
static int run(void){u32 n,i,offset,expected,actual;struct127 *actor=(struct127*)(bank+4);u8 *bytes=(u8*)actor;
 if(sizeof(void*)!=4||sizeof(struct127)!=0x32C||__builtin_offsetof(struct127,unk2E4)!=0x2E4)return 90;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  for(i=0;i<211;i++)bank[i]=0xA55A1234;
  for(i=0;i<sizeof(*actor);i++)bytes[i]=(u8)(i*13+0x5A);
  actor->unk94=cases[n].a;actor->unk9C=cases[n].b;actor->unk2E4=(s32)0x87654321u;
  func_1507DF10(actor,(s32)cases[n].mode);
  for(i=0;i<sizeof(*actor);i++){
   expected=(u8)(i*13+0x5A);
   for(offset=0;offset<3;offset++){
    u32 at=offset==0?0x94:offset==1?0x9C:0x2E4;
    if(i>=at&&i<at+4){u32 v=offset==0?cases[n].expectedA:offset==1?cases[n].expectedB:cases[n].expectedMask;
     expected=(v>>((i-at)*8))&255;}
   }
   actual=bytes[i];if(actual!=expected)return 2;
  }
  for(i=0;i<4;i++)if(bank[i]!=0xA55A1234u||bank[207+i]!=0xA55A1234u)return 3;
 }return 0;}
void _start(void){int value=run();__asm__ volatile("int $0x80"::"a"(1),"b"(value));__builtin_unreachable();}
'''


class ActorModeFlagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.obj,cls.words,cls.record=source.qualify(cls.root,cls.out)
        cls.before=(cls.out/'before-actor_owner').read_text()
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>53I',cls.rom,source.ROM))
        cls.rows=list(itertools.product(MODES,PATTERNS,PATTERNS))

    def receipt(self,name,**record):
        (self.out/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n')

    def native(self,label,body,rows):
        path=self.out/('native-'+label+'.c')
        path.write_text(native_program(body,rows))
        statuses=[]
        for profile in ('O2','O0'):
            binary=path.with_suffix('.'+profile)
            result=subprocess.run(['cc','-m32','-'+profile,'-std=c11','-fno-strict-aliasing',
                '-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector',
                '-Wall','-Wextra','-Werror',str(path),'-o',str(binary)],capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stderr),(0,''))
            statuses.append(subprocess.run([str(binary)],capture_output=True).returncode)
        return statuses

    def test_01_actual_donor_table_and_all_53_words(self):
        self.assertEqual(self.words,self.retail)
        self.assertEqual((self.record['words'],self.record['differences'],self.record['diagnostics']),(53,0,''))
        audit=self.root/'conker/build/alternative-source-byte-audit-20261014/commented-c-compile-profile-qualified.json'
        rows=json.loads(audit.read_text())['definitions']
        donor=next(row for row in rows if row['function']==source.FUNCTION and row['variant']==1)
        actual=source.BODY.split('*/\n',1)[1].strip().replace('actor','arg0').replace('mode','arg1')
        self.assertEqual(actual,donor['body'])
        self.assertEqual(donor['source_sha256'],'c4d2be7fdec3564d91686b8518f4e9d01e7910b342fb45f5a5df365aa74f18a2')
        self.receipt('donor',words=53,differences=0,guards_added=0,real_original_six_entry_table=True,
            archive_semantics_unchanged_except_argument_names=True)

    def test_02_all_raw_neighbors_and_owned_pool(self):
        old,diagnostics=build.compile_owner(self.root,self.out,self.before,'before')
        a,af,ar=parse_object(old)
        b,bf,br=parse_object(self.obj)
        self.assertEqual((diagnostics,set(af)),('',set(bf)))
        relative=lambda r,f:{at-f['value']:v for at,v in r.items() if f['value']<=at<f['value']+f['size']}
        for name in set(af)-{source.FUNCTION}:
            x,y=af[name],bf[name]
            self.assertEqual((x['size'],a[x['value']:x['value']+x['size']],relative(ar,x)),
                (y['size'],b[y['value']:y['value']+y['size']],relative(br,y)),name)
        oldp,newp=normalized_pools(old),normalized_pools(self.obj)
        self.assertEqual(oldp['.data'],newp['.data'])
        self.assertIsNone(oldp['.rodata'])
        raw,identities=newp['.rodata']
        self.assertFalse(any(raw))
        self.assertEqual(identities,tuple((i*4,source.FUNCTION,offset) for i,offset in enumerate(source.TABLE_OFFSETS)))
        self.receipt('neighbors',raw_neighbors=len(af)-1,all_bytes_sizes_relative_relocations_fixed=True,
            sole_new_pool_is_owned_six_entry_jump_table=True,all_retail_data_preserved=True)

    def test_03_complete_guest_public_private_and_all_reachable_words(self):
        coverage=set()
        for mode,a,b in self.rows:
            memory=fixture(a,b)
            expected=reference(memory,mode)
            for phase in (0,8):
                instances=[ModeOracle(words,memory,mode,phase).run() for words in (self.retail,self.words)]
                self.assertEqual(state(instances[0]),state(instances[1]))
                self.assertEqual(instances[1].memory,expected)
                coverage.update(instances[0].visits)
        self.assertEqual(len(coverage),53)
        self.receipt('guest',cases=len(self.rows)*2,all_53_retail_words=True,
            public_and_full_private_state_match=True,whole_backing_memory_and_real_table_fixed=True)

    def test_04_native32_actual_C_and_three_effective_returned_controls(self):
        self.assertEqual(self.native('selected',source.BODY,self.rows),[0,0])
        witnesses=[]
        for label,before,after,mode in (('mode9-mask','|= 0x20;','|= 0x21;',9),
                ('mode6-clear','~0x410','~0x400',6),('mode4-class','= 8;','= 16;',4)):
            body=source.BODY.replace(before,after)
            obj,diagnostics=build.compile_owner(self.root,self.out,source.recover(self.before,body),'negative-'+label)
            self.assertEqual(diagnostics,'')
            words=source.pad_and_link(self.root,self.out,obj,'negative-'+label+'-padded')
            memory=fixture(0xFFFFFFFF if mode!=9 else 0,0)
            instance=ModeOracle(words,memory,mode).run()
            self.assertNotEqual(instance.memory,reference(memory,mode))
            values=(mode,read(memory,ACTOR+0x94),read(memory,ACTOR+0x9C))
            statuses=self.native(label,body,[values])
            self.assertEqual(statuses,[2,2])
            witnesses.append(dict(label=label,statuses=statuses,returned_guest_mismatch=True))
        self.receipt('native',cases_per_profile=len(self.rows),profiles=['O2','O0'],
            zero_diagnostics=True,all_812_actor_bytes_and_canaries=True,controls=witnesses)

    def test_05_paired_fired_access_prefixes(self):
        count=0
        for mode in MODES:
            memory=fixture(0xFFFFFFFF,0xAAAAAAAA)
            total=ModeOracle(self.retail,memory,mode).run().accesses
            for cut in range(total):
                instances=[]
                for words in (self.retail,self.words):
                    instance=ModeOracle(words,memory,mode,fault=cut)
                    with self.assertRaises(machine.AccessFault):
                        instance.run()
                    self.assertEqual(instance.accesses,cut)
                    instances.append(instance)
                self.assertEqual(state(instances[0]),state(instances[1]))
                count+=1
        self.receipt('prefixes',paired_fired_prefixes=count,all_complete_states_match=True,
            hardware_exception_behavior_not_claimed=True)

    def test_06_three_independent_table_carry_and_text_rebases(self):
        text,functions,relocations=parse_object(self.obj)
        f=functions[source.FUNCTION]
        assembly,unresolved=emit_function(text,f,relocations,source.FUNCTION,{})
        self.assertEqual(unresolved,['.rodata'])
        assembly=assembly.replace(', .rodata',', '+source.TABLE_SYMBOL)
        for delta,table in ((0,source.TABLE),(0x7000,0x8009FFF0),(-0x5000,0x800A0000)):
            entry=source.ENTRY+delta
            stem=self.out/('rebase-'+str(delta))
            asm,obj,script,elf=[stem.with_suffix(ext) for ext in ('.s','.o','.ld','.elf')]
            asm.write_text(assembly)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],capture_output=True,check=True)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                '--defsym=%s=0x%X'%(source.TABLE_SYMBOL,table),'-o',str(elf),str(obj)],capture_output=True,check=True)
            from tools.experiments.game_actor_classifier_candidates import sections
            actual=list(struct.unpack_from('>53I',sections(elf)['.text'][1]))
            expected=self.retail[:]
            expected[4]=0x3C010000|((table+0x8000)>>16)
            expected[6]=0x8C2E0000|(table&65535)
            self.assertEqual(actual,expected)
            for mode in (4,5,6,7,8,9):
                memory=fixture(0xFFFFFFFF,0xAAAAAAAA)
                for i,offset in enumerate(source.TABLE_OFFSETS):
                    put(memory,table+i*4,entry+offset)
                instance=ModeOracle(actual,memory,mode,entry=entry).run()
                self.assertEqual(instance.memory,reference(memory,mode))
        self.receipt('rebases',text_table_pairs=3,signed_low_carry=True,
            all_six_cases_per_pair=True,no_synthetic_production_table=True)

    def test_07_return_screens_are_complete_and_not_new_matches(self):
        out=self.root/returns.BUILD
        baseline=(out/'homes.o')
        def signature(path):
            data,fs,rs=parse_object(path)
            f=fs['func_1510BF60']
            return data[f['value']:f['value']+f['size']],{a-f['value']:v for a,v in rs.items()
                if f['value']<=a<f['value']+f['size']}
        literal=signature(baseline)
        counts,identical=[],[]
        for group,variants in (('scalar',returns.scalar_variants),('locals',returns.local_variants),('exits',returns.exit_variants)):
            path=out/(group+'-screens.json')
            saved=path.read_bytes()
            rows=json.loads(saved)
            self.assertEqual([r['label'] for r in rows],[name for name,_ in variants()])
            self.assertTrue(all(not r['diagnostics'] and r['differences']>=258 for r in rows))
            counts.append(len(rows))
            identical.append(sum(signature(out/(r['label']+'.o'))==literal for r in rows))
            self.assertEqual(path.read_bytes(),saved)
        self.assertEqual(counts,[11,13,8])
        self.receipt('return-screen-summary',groups=counts,total=sum(counts),
            identical_target_and_relative_relocations=identical,no_exact_form=True)

    def test_08_real_table_pool_and_relocation_binding_controls(self):
        section_reader=source.sections
        def wrong_pool(path):
            result=dict(section_reader(path))
            meta,payload=result['.rodata']
            changed=bytearray(payload)
            changed[3]^=4
            result['.rodata']=(meta,bytes(changed))
            return result
        with patch.object(source,'sections',side_effect=wrong_pool):
            with self.assertRaisesRegex(ValueError,'compact actor mode jump table'):
                source.qualify(self.root,self.out)
        parser=source.parse_object
        def wrong_relocation(path):
            data,functions,relocations=parser(path)
            f=functions[source.FUNCTION]
            relocations=dict(relocations)
            relocations[f['value']+0x10]=[('R_MIPS_HI16','.unbound_pool')]
            return data,functions,relocations
        with patch.object(source,'parse_object',side_effect=wrong_relocation):
            with self.assertRaisesRegex(ValueError,'code relocations'):
                source.qualify(self.root,self.out)
        with patch.object(source,'TABLE',source.TABLE+4):
            with self.assertRaisesRegex(ValueError,'Original actor mode jump table'):
                source.qualify(self.root,self.out)
        self.receipt('binding-controls',effective=3,actual_original_and_pool_bindings_proven=True,
            no_unknown_symbol_assigned_a_fake_address=True)


if __name__=='__main__':
    unittest.main()
