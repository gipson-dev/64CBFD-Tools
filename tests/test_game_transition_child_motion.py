"""Full child motion, guarded literal/private parity and first whole-image gate."""
import csv
from functools import lru_cache
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_transition_child_motion as source
from tools.experiments import game_transition_child_motion_installation as install
from tools.tests import game_transition_child_motion_oracle as model
from tools.tests import game_transition_child_motion_native as native
from tools.tests import transition_child_motion_checkpoint as checkpoint
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command
from tools.check_game_data_layout import audit_layout
from tools.experiments.alternative_source_draft_word_screen import emit_function


def public(memory):
    return {a:b for a,b in memory.items() if not model.STACK-0x500<=a<model.STACK+0x120}


class ChildMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]; cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-child',
            (cls.out/'before-tile_original').read_text(),source.FUNCTION)

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_literal48_and_closed_cycle_schedule_operand_order(self):
        self.assertEqual(source.normalize(self.images[0]),self.truth)
        self.assertEqual(self.images[1],self.truth)
        self.assertEqual(self.row['unchanged_raw_padded_neighbors'],24)
        self.assertEqual(len(source.PATCHES),10)
        source.checked_parts(*source.parts(self.obj))

    def test_02_ordered_reference_aliases_fp_edges_and_complete_guarded_state(self):
        count=0; visited=set()
        for memory,args,phase in model.cases():
            expected=model.reference(memory,args)
            original=model.MotionOracle(self.truth,memory,args,phase).run()
            raw=model.MotionOracle(self.images[0],memory,args,phase).run()
            padded=model.MotionOracle(self.images[1],memory,args,phase).run()
            self.assertEqual(original.memory,expected,(args,phase))
            self.assertEqual(raw.memory,expected,(args,phase))
            self.assertEqual(model.state(original),model.state(padded))
            self.assertEqual((original.r[2],raw.r[2],padded.r[2]),(1,1,1))
            visited.update(original.visits); count+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+192,4))<=visited)
        memory,args=model.fixture(5)
        model.put(memory,args[0]+0x74,0x7FC12345); model.put(memory,args[0]+0x78,0x7FC54321)
        original=model.MotionOracle(self.truth,memory,args).run(); raw=model.MotionOracle(self.images[0],memory,args).run()
        padded=model.MotionOracle(self.images[1],memory,args).run()
        self.assertEqual(model.state(original),model.state(padded))
        self.assertNotEqual(model.read(original.memory,args[0]+0x74),model.read(raw.memory,args[0]+0x74))
        self.receipt('guest',three_way_cases=count,natural_words=48,global_aliases=18,modeled_quiet_NaNs_infinities_subnormals=True,
            raw_double_NaN_payload_difference_explicit=True,guarded_full_state_exact=True,not_FCSR_CP0_or_hardware_acceptance=True)

    def test_03_native32_typed_body_caller_and_real_linker_clock_aliases(self):
        caller,driver=self.out/'native-caller.c',self.out/'native-driver.c'
        caller.write_text(native.CALLER); driver.write_text(native.DRIVER); exits={}
        forms=[('o2','-O2',source.SELECTED,0,0)]
        forms += [('o0','-O0',source.SELECTED,a,0) for a in range(3)]
        forms += [(name,'-O0' if name=='cached_clock' else '-O2',body,
                   1 if name=='cached_clock' else 0,22) for name,body in native.controls(source.SELECTED).items()]
        forms += [('optimized-alias-limit','-O2',source.SELECTED,a,22) for a in (1,2)]
        for name,opt,body,alias,wanted in forms:
            label=name+'-'+str(alias); path=self.out/('native-'+label+'.c'); path.write_text(native.HEADER+body+'\n'); exe=path.with_suffix('.elf')
            compiled=subprocess.run([*native_command(opt),
                '-g','-mstackrealign','-malign-double','-DCLOCK_ALIAS=%d'%alias,
                *[str(p.relative_to(self.root)) for p in (path,caller,driver)],'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120)
            self.assertEqual(ran.returncode,wanted,(label,ran.stderr)); exits[label]=ran.returncode
        self.receipt('native',cases_each=360,normal_and_two_real_clock_aliases=True,O2_O0_UBSan=True,
            separate_typed_caller_and_full_body=True,all_record_bytes_outer_canaries=True,exits=exits,
            alias_is_prepared_GNU32_symbol_extension=True,alias_acceptance_at_O0_only=True,
            both_O2_symbol_alias_failures_are_positive_limit_controls=True,
            not_portable_NaN_payload_or_hardware_acceptance=True)

    def test_04_all_positively_fired_guarded_access_fault_prefixes(self):
        count=0; fired=0
        for pattern,alias,phase in itertools.product((0,5),(0,1,8,15),(0,8)):
            memory,args=model.fixture(pattern,alias)
            complete=model.MotionOracle(self.truth,memory,args,phase).run()
            for cut in range(complete.all_accesses):
                states=[]
                for words in (self.truth,self.images[1]):
                    m=model.MotionOracle(words,memory,args,phase); m.access_fault=cut
                    with self.assertRaises(faults.AccessBoundary): m.run()
                    states.append(model.state(m)); fired+=1
                self.assertEqual(states[0],states[1]); count+=1
        self.receipt('faults',paired_prefixes=count,positively_fired_instances=fired,
            full_modeled_state_and_access_order=True,not_portable_C_faults_or_hardware_exceptions=True)

    def test_05_original_kind13_callback_window(self):
        entry,join=0x15154CE8,0x15154D14
        caller=list(struct.unpack_from('>11I',self.rom,0x182198)); count=0
        class Join(Exception): pass
        class Caller(model.MotionOracle):
            def execute(self,w):
                if w==0xFFFFFFFF: raise Join
                if w>>26==32:
                    from tools.tests.game_sequence_event_scan_oracle import load_signed_byte
                    load_signed_byte(self,w)
                else: super().execute(w)
        for pattern,phase in itertools.product(range(8),(0,8)):
            memory,args=model.fixture(pattern); model.put(memory,0x8008ACFC,source.ENTRY)
            expected=model.reference(memory,args)
            for words in (self.truth,self.images[1]):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+192,4),words)); connected[join]=0xFFFFFFFF
                m=Caller(caller,memory,args,phase,entry,connected); m.r[11]=52; m.r[5]=0
                with self.assertRaises(Join): m.run()
                self.assertEqual((m.current_pc,m.forwarded,m.r[2],m.r[4],m.r[5]),(join,args[0],1,args[0],0))
                self.assertEqual(public(m.memory),public(expected))
            count+=1
        self.receipt('caller',paired_cases=count,actual_words=11,kind=13,not_full_dispatcher_acceptance=True)

    def test_06_word_binding_and_expected_guard_corruption_rejects(self):
        raw,bindings=source.parts(self.obj)
        for i in range(48):
            wrong=bytearray(raw); wrong[i*4+3]^=1
            with self.assertRaisesRegex(ValueError,'words/bindings'): source.checked_parts(wrong,bindings)
        for at in bindings:
            wrong=dict(bindings); wrong[at]=[(bindings[at][0][0],bindings[at][0][1]+'-wrong')]
            with self.assertRaisesRegex(ValueError,'words/bindings'): source.checked_parts(raw,wrong)
        rows=list(csv.DictReader(io.StringIO(source.guard_bytes((self.out/'before-guards').read_bytes()).decode())))
        indices=[i for i,r in enumerate(rows) if r['filename']==source.OWNER and r['function']==source.FUNCTION]
        self.assertEqual(len(indices),10)
        for i in indices:
            changed=[dict(r) for r in rows]; changed[i]['expected']='0x%08X'%(int(changed[i]['expected'],16)^1)
            text=io.StringIO(); writer=csv.DictWriter(text,fieldnames=list(changed[0]),lineterminator='\n'); writer.writeheader(); writer.writerows(changed)
            path=self.out/('wrong-guard-%d.csv'%i); path.write_text(text.getvalue())
            with self.assertRaises(ValueError): source.padded_object(self.root,self.out,self.obj,'wrong-guard-%d'%i,path)
        self.receipt('corruption',word_controls=48,binding_controls=len(bindings),fired_expected_guard_controls=10)

    def test_07_first_complete_installed_image_and_all_data(self):
        if not checkpoint.AFTER: self.skipTest('First complete prediction not installed yet')
        expected=install.expected_inputs(self.root,self.root/install.BUILD)
        for key,data in expected.items():
            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)
            self.assertEqual(hashlib.sha256(data).hexdigest(),checkpoint.AFTER[key])
        self.assertEqual(json.loads((self.root/install.BUILD/'initial-prediction.json').read_text()),
            {key:hashlib.sha256(data).hexdigest() for key,data in expected.items()})
        report=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
        self.receipt('installed',first_whole_image_exact=True,all_data=report,guards=10,metadata_exclusions=0)

    def test_08_independent_links_signed_low_carries_and_shared_globals(self):
        names=('D_800BE9A4','D_800A0878','D_800A087C'); count=0
        for index,values in enumerate(((0x80117FFC,0x80128000,0x80138004),
                (0x80128000,)*3,(0x80127FFC,0x80128000,0x80128004))):
            anchors=dict(zip(names,values)); entry=0x15208004+index*0x10000
            targets=[('original',self.original)]
            for label,owner in (('raw',self.obj),('guarded',self.padded)):
                raw,bindings=source.parts(owner)
                text,unresolved=emit_function(raw,dict(value=0,size=source.SIZE),bindings,source.FUNCTION,anchors)
                self.assertFalse(unresolved)
                path=self.out/('rebase-%d-%s.s'%(index,label)); path.write_text(text); obj=path.with_suffix('.o')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
                targets.append((label,obj))
            images=[]
            for label,obj in targets:
                script=self.out/('rebase-%d-%s.ld'%(index,label)); elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(obj)],capture_output=True,check=True)
                images.append(list(struct.unpack('>48I',source.projection.sections(elf)['.text'][1][:source.SIZE])))
            self.assertEqual(images[0],images[2]); self.assertEqual(source.normalize(images[1]),images[0])
            for pattern,phase in itertools.product(range(8),(0,8)):
                memory,args=model.fixture(pattern)
                for old,new in zip((model.CLOCK,model.DAMP_X,model.DAMP_Y),values):
                    model.put(memory,new,model.read(memory,old))
                expected=model.reference(memory,args,*values); states=[]
                for words in images:
                    machine=model.MotionOracle(words,memory,args,phase,entry).run()
                    self.assertEqual(machine.memory,expected); states.append(model.state(machine))
                self.assertEqual(states[0],states[2]); count+=1
        self.receipt('rebases',independent_links=9,symbol_sets=3,three_way_cases=count,
            signed_low_carries_and_shared_global_storage=True,all_guarded_words_exact=True)

    def test_09_every_live_and_frozen_input_corruption_fires(self):
        source.freeze(self.root,self.out); cache={}; real=hashlib.sha256
        for key,path in source.PATHS.items():
            current=self.root/path; frozen=self.out/('before-'+key)
            cache[current]=current.read_bytes(); cache[frozen]=frozen.read_bytes()
            normalized=checkpoint.previous_input(cache[current],path,self.root)
            self.assertEqual(real(normalized).hexdigest(),source.BASELINE[key])
            self.assertEqual(cache[frozen],normalized)
        for key in checkpoint.AFTER:
            for stage in ('before','after'):
                path=self.root/install.BUILD/(stage+'-'+key); cache[path]=path.read_bytes()
        @lru_cache(None)
        def digest(data): return real(data)
        controls=0
        for key,path in source.PATHS.items():
            for target,message in ((self.root/path,'Unknown child motion input'),
                    (self.out/('before-'+key),'Changed child motion fixture')):
                wrong=bytearray(cache[target]); wrong[len(wrong)//2]^=1; wrong=bytes(wrong)
                def read_bytes(path): return wrong if path==target else cache[path]
                with patch.object(Path,'read_bytes',read_bytes),patch.object(Path,'exists',lambda path:path in cache),\
                        patch.object(source.hashlib,'sha256',side_effect=digest):
                    with self.assertRaisesRegex(ValueError,message): source.freeze(self.root,self.out)
                controls+=1
        source.freeze(self.root,self.out)
        self.receipt('inputs',entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),
            positively_fired_live_and_fixture_controls=controls,exact_successors_only=True)

    def test_10_checkpoint_rejects_each_changed_fixture_and_unknown_successor(self):
        if not checkpoint.AFTER: self.skipTest('First complete prediction not installed yet')
        controls=0; read_bytes=Path.read_bytes
        for key in checkpoint.AFTER:
            current=(self.root/source.PATHS[key]).read_bytes()
            wrong=bytearray(current); wrong[len(wrong)//2]^=1; wrong=bytes(wrong)
            self.assertEqual(checkpoint.previous_input(wrong,source.PATHS[key],self.root),wrong)
            controls+=1
            for stage in ('before','after'):
                target=self.root/install.BUILD/(stage+'-'+key)
                wrong=bytearray(target.read_bytes()); wrong[len(wrong)//2]^=1; wrong=bytes(wrong)
                def altered(path): return wrong if path==target else read_bytes(path)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaisesRegex(AssertionError,'Changed child motion fixture'):
                        checkpoint.previous_input(current,source.PATHS[key],self.root)
                controls+=1
        self.receipt('checkpoint',positively_fired_controls=controls,accepted_keys=sorted(checkpoint.AFTER))


if __name__=='__main__': unittest.main()
