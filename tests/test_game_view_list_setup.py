"""Two-row SDK semantics, live aliases, closed guards and original call cuts."""
import csv
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_view_list_setup as source
from tools.tests import game_view_list_setup_oracle as model
from tools.tests import game_view_list_setup_native as native
from tools.tests import test_game_actor_burst_consumer_match as tracking
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_view_initialization as initialization
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object


class ViewListSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2];cls.out = cls.root/source.BUILD
        cls.obj,cls.padded,cls.raw,cls.row = source.qualify(cls.root,cls.out)
        cls.rom = (cls.out/'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>61I',cls.rom,source.ROM))
        data,functions = source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        cls.normalized = list(struct.unpack_from('>61I',data,functions[source.FUNCTION]['value']))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    @classmethod
    def original(cls,label,text,name):
        start,end = 'glabel '+name+'\n','endlabel '+name
        if text.count(start)!=1 or text.count(end)!=1:raise ValueError('Unknown original function boundary')
        block = start+text.split(start,1)[1].split(end,1)[0]+end+'\n'
        return initialization.ViewInitializationTests.original.__func__(cls,label,block)

    def test_01_exact_61word_slot_target_only_profile_and_ten_neighbors(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(61,24,38))
        self.assertEqual(self.row['unchanged_normal_neighbors'],10)
        self.assertEqual(self.row['diagnostics'],'');self.assertFalse(self.row['pools'])
        self.assertEqual(self.normalized,self.truth)
        self.assertEqual(set(source.ROLES),set(source.ROLES.values()))
        self.assertEqual(set(source.ROUTING),set(source.ROUTING.values()))
        primary = parse_object(self.out/'qualified-normal.o')
        self.assertEqual(primary[1][source.FUNCTION]['size'],126*4)
        self.assertEqual(len(source.RELOCATIONS),12)
        for at in (*range(0,0x18,4),*range(0xD8,244,4)):
            self.assertEqual(source.normalized_instructions(self.obj)[at],(source.checked_object(self.obj)[0][at//4],[]))
        make = source.recovered_makefile((self.out/'before-makefile').read_text())
        self.assertEqual(make.count(source.MAKE_RULE),1)
        self.assertIn('--function-object func_1501A39C=$@.nounroll.compact',source.MAKE_RULE)
        self.assertEqual(make.replace(source.MAKE_RULE,''),(self.out/'before-makefile').read_text())
        self.receipt('emission',body_words=61,slot_words=61,frame=24,new_guards=38,
            normal_target_words=126,unchanged_normal_neighbors=10,target_only_no_unroll=True,
            saved_S0_through_S4_homes_unchanged=True,no_padding_or_private_pools=True)

    def test_02_complete_guest_aliases_wrap_and_all61_words(self):
        count = 0;seen = [set(),set(),set()];changed_next=False;changed_depth=False;changed_views=False
        for memory,args in model.corpus():
            expected = model.reference(memory)
            changed_next |= model.read(expected,model.INPUT+4)!=args[1]
            changed_depth |= model.read(expected,model.DEPTH)!=args[2]
            changed_views |= model.read(expected,model.VIEWS)!=args[3]
            for phase in (0,8):
                machines = []
                for i,words in enumerate((self.truth,self.raw,self.normalized)):
                    m = model.ListSetupOracle(words,memory,phase).run()
                    self.assertEqual(model.public(m.memory),model.public(expected),(args,phase))
                    for reg in (*range(16,24),28,29,30,31):self.assertEqual(m.r[reg],m.before[reg])
                    self.assertFalse(m.calls);seen[i].update(m.visits);machines.append(m)
                for m in machines[1:]:self.assertEqual((m.memory,m.f),(machines[0].memory,machines[0].f))
                self.assertEqual(machines[2].r,machines[0].r)
                count += 1
        wanted = set(range(source.ENTRY,source.ENTRY+244,4))
        for visits in seen:self.assertEqual(visits,wanted)
        self.assertTrue(changed_next and changed_depth and changed_views)
        self.receipt('guest',fixtures=count//2,three_way_cases=count,all61_words_visited_each=True,
            complete_memory_and_preserved_ABI_checked=True,normalized_full_private_state=True,
            mutable_second_cursor_depth_and_view_aliases=True,word_address_model_not_hardware_MMU=True)

    def test_03_raw_and_normalized_exact_memory_access_sequence(self):
        cases = 0
        for memory,args in model.corpus():
            machines = [model.ListSetupOracle(words,memory).run() for words in (self.truth,self.raw,self.normalized)]
            for m in machines[1:]:self.assertEqual(m.trace,machines[0].trace,args)
            self.assertEqual(len(machines[0].trace),38)
            cases += 1
        self.receipt('access-order',cases=cases,accesses_each=38,raw_and_normalized_exact_memory_sequence=True,
            save_restore_and_two_ordered_row_publications=True,raw_private_register_fault_state_not_claimed=True)

    def test_04_actual_native32_SDK_O2_O0_UBSan_and_seven_controls(self):
        harness = self.out/'native.c';harness.write_text(native.program());exits={}
        for name,opt,body in [('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[
                (name,'-O2',body) for name,body in native.controls().items()]:
            if name not in ('o2','o0'):self.assertNotEqual(body,source.SELECTED)
            unit = self.out/('native-'+name+'.c');unit.write_text(native.HEADER+body+'\n')
            exe = unit.with_suffix('.elf')
            built = subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',
                str(unit.relative_to(self.root)),str(harness.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            run = subprocess.run([str(exe)],capture_output=True,text=True,timeout=30)
            exits[name] = run.returncode
            self.assertEqual(run.returncode,0 if name in ('o2','o0') else 21,(name,run.stderr))
        self.receipt('native',cases_each=sum(1 for _ in model.corpus()),exits=exits,
            separate_actual_C_and_real_SDK_macros=True,UBSan=True,no_fwrapv=True,
            all2320_public_words_and_canaries_checked=True,translated_live_pointer_aliases=True)

    def test_05_all61_words_bindings_guard_fields_and_real_padder_fail_closed(self):
        text,functions,relocations = parse_object(self.obj);f = functions[source.FUNCTION]
        for i in range(61):
            bad = bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,relocations)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for at in (*source.RELOCATIONS,0):
            bad = dict(relocations);bad[f['value']+at]=[('R_MIPS_HI16','wrong')]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        with patch.object(source.previous,'sections',return_value={'.rodata':(0,b'bad')}):
            with self.assertRaises(ValueError):source.checked_object(self.obj)
        before=(self.out/'before-guards').read_bytes();good=(self.out/'normalized-guards.csv').read_bytes()
        fields=next(csv.reader(io.StringIO(before.decode())))
        rows=list(csv.DictReader(io.StringIO(good[len(before):].decode()),fieldnames=fields));self.assertEqual(len(rows),38)
        def manifest(rows):
            out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');w.writerows(rows)
            return before+out.getvalue().encode()
        for i in range(38):
            for key in ('filename','function','offset','expected','replacement','expected_relocations','replacement_relocations','insert_after','omit'):
                bad=[dict(row) for row in rows];bad[i][key]='bad'
                with self.assertRaises(ValueError):source.checked_manifest(manifest(bad),self.out,self.obj)
        for key,value in (('expected','0x00000000'),('expected_relocations','R_MIPS_HI16:wrong')):
            bad=[dict(row) for row in rows];bad[0][key]=value
            path=self.out/('bad-'+key+'.csv');path.write_bytes(manifest(bad))
            with self.assertRaises((ValueError,AssertionError)):
                source.pad_c_object.emit_padded_assembly(self.out/'qualified-normal.o',self.root/source.PATHS['layout'],source.OWNER,
                    word_patches_path=path,function_objects={source.FUNCTION:self.obj})
        with self.assertRaises(ValueError):source.recovered_makefile(source.recovered_makefile((self.out/'before-makefile').read_text()))
        self.receipt('fail-closed',raw_words=61,bindings=12,extra_binding=1,private_pool=1,
            guard_field_mutations=342,real_padder_expected_word_and_binding_rejections=2)

    def test_06_independent_original_and_normalized_rebases(self):
        original=self.original('retail-original',(self.out/'before-view_list_original').read_text(),source.FUNCTION)
        text,functions,bindings=parse_object(self.padded)
        names=sorted({name for rows in source.RELOCATIONS.values() for _,name in rows})
        for index in range(3):
            entry=0x15207FF0+index*0x100000
            symbols={name:0x80100000+n*0x10000+(0x7FFC,0x8004,0x7FD0)[index] for n,name in enumerate(names)}
            symbols['D_800BE9E0']=symbols['D_800BE9D8']+8
            emitted,unresolved=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols)
            self.assertFalse(unresolved)
            asm=self.out/('normalized-rebase-%d.s'%index);asm.write_text(emitted);obj=asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],capture_output=True,check=True)
            images=[]
            for label,path in (('original',original),('normalized',obj)):
                script=self.out/('rebase-%s-%d.ld'%(label,index));script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                elf=script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(path)],capture_output=True,check=True)
                images.append(sections(elf)['.text'][1][:244])
            self.assertEqual(images[0],images[1])
        self.receipt('rebases',original_GNU_links=3,normalized_independent_links=3,all61_words_compared=True,
            moved_HI_LO_pairs_and_carries=True,two_row_output_end_relationship=True)

    def test_07_two_full_original_callers_and_actual_delay_store_boundaries(self):
        callers=(('upstream','game_45B80','func_1501878C',0x45C3C,412,0x150188B8,3),
            ('view_list_caller_original','generated_49D30','func_1501C880',0x49D30,239,0x1501C91C,2))
        cases=0
        for key,owner,name,rom,words,entry,cut_words in callers:
            obj=self.original('original-'+name,(self.out/('before-'+key)).read_text(),name)
            data,functions=source.build.link_owner(self.root,self.out,obj,owner);f=functions[name]
            full=data[f['value']:f['value']+f['size']]
            self.assertEqual(len(full),words*4);self.assertEqual(full,self.rom[rom:rom+len(full)])
            va=0x1501878C if key=='upstream' else 0x1501C880
            cut=list(struct.unpack_from('>%dI'%cut_words,full,entry-va))
            self.assertEqual(cut[0],0x0D4068E7)
            self.assertEqual(cut[1],0 if key=='upstream' else 0xAFA90024)
            join=entry+cut_words*4
            class Join(Exception):pass
            class Code(tracking.TrackedCode):
                def __getitem__(self,pc):
                    if pc==join:raise Join
                    return super().__getitem__(pc)
            for memory,args in itertools.islice(model.corpus(),12):
                expected=model.reference(memory)
                if key=='upstream':model.put(expected,0x800BE614,0,1)
                for phase in (0,8):
                    for emitted in (self.truth,self.raw,self.normalized):
                        connected={source.ENTRY+i*4:w for i,w in enumerate(emitted)};connected[join]=0
                        m=model.ListSetupOracle(cut,memory,phase,entry,connected)
                        m.r[16]=m.before[16]=0x800BE614;m.r[9]=0x12345678
                        m.code=Code(m.code,m)
                        with self.assertRaises(Join):m.run()
                        self.assertEqual(model.public(m.memory),model.public(expected))
                        self.assertEqual(m.calls,[(source.ENTRY,())])
                        for reg in (*range(16,24),28,29,30):self.assertEqual(m.r[reg],m.before[reg])
                        if key!='upstream':self.assertEqual(model.read(m.memory,m.r[29]+0x24),0x12345678)
                    cases+=1
        self.receipt('callers',full_original_words=[412,239],actual_cut_cases=cases,
            actual_T1_stack_delay_store_and_S0_flag_clear=True,no_consumed_return=True,
            complete_caller_startup_or_gameplay_not_claimed=True)

    def test_08_normalized_literal_retail_fault_prefixes(self):
        cases=0
        fixtures=[model.fixture(),model.fixture(model.VIEWS-32),model.fixture(model.DEPTH-32),
            model.fixture(model.OUTPUT),model.fixture(model.BUFFERS+64,model.INPUT),
            model.fixture(model.DEPTH-12,model.BUFFERS+0x1020)]
        fixtures=[m for m in fixtures if set(model.reference(m))==set(m)]
        self.assertGreaterEqual(len(fixtures),5)
        for memory in fixtures:
            for phase in (0,8):
                full=model.ListSetupOracle(self.truth,memory,phase).run()
                for fault in range(full.root_accesses):
                    machines=[]
                    for words in (self.truth,self.normalized):
                        m=model.ListSetupOracle(words,memory,phase);m.root_fault=fault
                        with self.assertRaises(tracking.AccessBoundary):m.run()
                        self.assertEqual(m.root_accesses,fault);machines.append(m)
                    state=lambda m:(m.memory,m.r,m.f,m.events,m.calls,m.trace,m.current_pc,m.delay_of)
                    self.assertEqual(state(machines[0]),state(machines[1]));cases+=1
        self.receipt('faults',fired_prefix_pairs=cases,normalized_literal_retail=True,
            raw_register_fault_equivalence_not_claimed=True,hardware_exceptions_not_emulated=True)


if __name__=='__main__':unittest.main()
