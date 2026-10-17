"""Certified full setup match, actual padder/rebases, functional controls and faults."""
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_sequence_record_setup as source
from tools.experiments import game_sequence_record_setup_frame as frame
from tools.experiments import game_sequence_record_setup_preheader as screens
from tools.experiments import game_sequence_record_setup_matching as fit
from tools.experiments import game_sequence_state_reset as reset
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import game_sequence_record_setup_native as native
from tools.tests import game_sequence_record_setup_oracle as model
from tools.tests import test_game_sequence_record_setup_frame as frame_tests
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command


def runtime(root,out,obj):
    data,functions=source.build.link_owner(root,out,obj,source.OWNER)
    f=functions[source.FUNCTION]
    return list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))


def machine_state(m):
    return (m.memory,m.r,m.f,m.lo,m.events,m.calls,m.cuts,m.provider.snapshots,
        m.provider.fired,m.provider.allocations,m.current_pc,m.delay_of,m.all_accesses)


class SequenceRecordSetupMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/fit.BUILD
        cls.obj,cls.padded,cls.raw_unlinked,cls.normalized,cls.qualification=fit.guarded(cls.root,cls.out)
        cls.original=cls.out/'original-setup-match.o'
        cls.wanted,cls.wanted_bindings,_=fit.parts(cls.original)
        _,cls.bindings,_=fit.parts(cls.obj)
        cls.raw=runtime(cls.root,cls.out,cls.obj)
        cls.truth=list(struct.unpack_from('>473I',(cls.out/'before-retail_rom').read_bytes(),source.ROM))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_actual473_word_padder_match_and_all56_raw_and_padded_neighbors(self):
        self.assertEqual(self.normalized,self.truth)
        self.assertEqual(runtime(self.root,self.out,self.original),self.truth)
        self.assertEqual(self.qualification['guards'],165)
        self.assertEqual(self.qualification['roles']['call_sites'],32)
        self.assertEqual(self.qualification['roles']['commutative_words'],[])
        self.assertEqual(self.qualification['cursor']['CFG_words_reached'],474)
        self.assertEqual(self.qualification['roles']['words_reached'],473)
        self.assertEqual(fit.SELECTED,frame.PREHEADER)
        before,diagnostics=source.compile_owner(self.root,self.out,
            (self.out/'before-view_list_caller_owner').read_text(),'match-neighbor-before',True)
        self.assertEqual(diagnostics,'');self.assertEqual(same_functions(before,self.obj,(source.FUNCTION,)),56)
        script=self.out/'match-neighbor-before-padded.s'
        script.write_text(emit_padded_assembly(before,self.out/'before-view_list_caller_original',
            word_patches_path=self.out/'before-guards',filename=source.OWNER))
        padded=script.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],capture_output=True,check=True)
        self.assertEqual(same_functions(padded,self.padded,(source.FUNCTION,)),56)
        before_bytes=(self.out/'before-guards').read_bytes();after=(self.out/'qualified-guards.csv').read_bytes()
        fit.checked_guard_bytes(before_bytes,after)
        self.assertEqual(before_bytes.count(b'\r\n'),298)
        self.receipt('matched-owner',all473_words_exact=True,direct=False,installed=False,
            unchanged_raw_neighbors=56,unchanged_padded_neighbors=56,guards=165,
            omissions=1,insertions=0,frame=120,old_guard_bytes_and_298_CRLF_lines_preserved=True)

    def test_02_full_three_way_cases_events_private_homes_and_every_word(self):
        count=0;seen=[set(),set(),set()];fired=set()
        for memory,args,config in model.cases():
            reference=model.Reference(memory,args,config).run()
            for phase in (0,8):
                machines=[]
                for i,words in enumerate((self.truth,self.raw,self.normalized)):
                    entry=frame.WITNESS_ENTRY if i==1 else source.ENTRY
                    m=frame_tests.Observed(words,memory,args,config,reference.allocations,phase,entry=entry).run()
                    self.assertTrue(model.public(m.memory)==model.public(reference.memory),(i,args,config,phase))
                    self.assertEqual(m.calls,reference.calls);self.assertEqual(m.provider.snapshots,reference.snapshots)
                    self.assertEqual(m.provider.fired,reference.fired)
                    seen[i].update(m.visits);fired.update(m.provider.fired);machines.append(m)
                for m in machines[1:]:
                    self.assertTrue(m.memory==machines[0].memory,(args,config,phase))
                    self.assertEqual(m.cuts,machines[0].cuts)
                    self.assertEqual([e for e in m.events if e[0] in ('R','W')],
                        [e for e in machines[0].events if e[0] in ('R','W')])
                self.assertTrue(machine_state(machines[0])==machine_state(machines[2]),(args,config,phase))
                count+=1
        for i,(words,entry) in enumerate(((self.truth,source.ENTRY),(self.raw,frame.WITNESS_ENTRY),(self.normalized,source.ENTRY))):
            self.assertEqual(seen[i]&set(range(entry,entry+len(words)*4,4)),set(range(entry,entry+len(words)*4,4)))
        self.assertEqual(len(fired),8)
        self.receipt('matched-guest',three_way_cases=count,all473_474_473_words=True,
            full_memory_events_and_all_provider_cut_roles_homes=True,
            original_guarded_literal_GPR_FPR_PC_delay_state=True,positive_gates=sorted(fired),
            raw_private_entry=frame.WITNESS_ENTRY,opaque_providers_not_gameplay=True)

    def test_03_native32_complete_body_O2_O0_UBSan_and_eight_functional_controls(self):
        caller=self.out/'match-native-caller.c';caller.write_text(native.program())
        unit_reset=self.out/'match-native-reset.c'
        unit_reset.write_text(native.BODY_HEADER+reset.SELECTED.replace('func_1501D044','actual_reset')+'\n')
        exits={}
        for label,opt,body in [('o2','-O2',fit.SELECTED),('o0','-O0',fit.SELECTED)]+[
                (label,'-O2',body) for label,body in frame_tests.controls(fit.SELECTED).items()]:
            if label not in ('o2','o0'):self.assertNotEqual(body,fit.SELECTED)
            unit=self.out/('match-native-'+label+'.c');unit.write_text(native.BODY_HEADER+body+'\n');exe=unit.with_suffix('.elf')
            built=subprocess.run([*native_command(opt),'-g','-mstackrealign','-malign-double','-fno-strict-aliasing',
                str(unit.relative_to(self.root)),str(unit_reset.relative_to(self.root)),str(caller.relative_to(self.root)),
                '-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120);exits[label]=ran.returncode
            if label in ('o2','o0'):self.assertEqual(ran.returncode,0,(label,ran.stdout,ran.stderr))
            else:self.assertIn(ran.returncode,(21,22),(label,ran.stdout,ran.stderr))
        self.receipt('matched-native',cases_each_profile=sum(1 for _ in native.cases()),exits=exits,
            actual_full_C_body_and_actual_reset_separate_from_caller_providers=True,
            all756_fields_bank_padding_canaries_heap_gaps_bytes=True,UBSan=True,no_fwrapv=True,
            native_checks_C_not_MIPS_guard_execution=True)

    def test_04_symbolic_invariant_liveness_ABI_loop_and_operand_controls(self):
        raw=self.raw_unlinked;bindings=self.bindings
        writes=[i for i,w in enumerate(raw) if w==0x24130001]
        self.assertEqual(writes,[89,95])
        changed=list(raw)
        for i in writes:changed[i]=0x24130002
        with self.assertRaisesRegex(ValueError,'invariant one'):fit.cursor_certificate(changed,bindings)
        changed=list(raw);changed[280]=changed[280]&~(31<<21)|(24<<21)
        with self.assertRaisesRegex(ValueError,'another live use'):fit.cursor_certificate(changed,bindings)
        changed=list(raw);changed[280]=changed[280]&~(31<<21)|(31<<21)
        with self.assertRaisesRegex(ValueError,'Return links'):fit.cursor_certificate(changed,bindings)
        changed=list(raw);changed[278]=0x10000001
        with self.assertRaisesRegex(ValueError,'delay instruction'):fit.cursor_certificate(changed,bindings)
        changed=list(raw);changed[19]=changed[19]&~65535|(fit.OMIT-20)&65535
        with self.assertRaisesRegex(ValueError,'branch target'):fit.cursor_certificate(changed,bindings)
        folded,moved,_=fit.fold_cursor(raw,bindings)
        for index,shift,register in ((15,16,14),(56,11,5),(104,16,11)):
            changed=list(self.wanted);changed[index]=changed[index]&~(31<<shift)|(register<<shift)
            with self.assertRaises(ValueError):fit.operand_certificate(folded,changed,moved)
        changed=list(self.wanted);changed[104]^=4
        with self.assertRaisesRegex(ValueError,'Non-register'):fit.operand_certificate(folded,changed,moved)
        self.receipt('matched-proof-controls',five_invariant_liveness_link_delay_target_controls=True,
            three_live_store_call_and_loop_backedge_controls=True,nonregister_control=True,
            proofs_execute_beyond_fingerprint_gates=True)

    def test_05_all_words_bindings_pools_guard_fields_and_production_inputs_fail_closed(self):
        raw=self.raw_unlinked;wanted=self.wanted;b=self.bindings;wb=self.wanted_bindings
        for original,words in ((False,raw),(True,wanted)):
            for i in range(len(words)):
                changed=list(words);changed[i]^=1
                with self.assertRaises(ValueError):fit.checked_pair(raw if original else changed,b,changed if original else wanted,wb)
        for original,uses in ((False,b),(True,wb)):
            for at in (*uses,-4):
                changed=dict(uses);changed[at]=[('R_MIPS_HI16','wrong')]
                with self.assertRaises(ValueError):fit.checked_pair(raw,b if original else changed,wanted,changed if original else wb)
        with patch.object(fit,'sections',return_value={'.data':(0,b'bad')}):
            for obj in (self.obj,self.original):
                with self.assertRaises(ValueError):fit.parts(obj)
        before=(self.out/'before-guards').read_bytes();after=(self.out/'qualified-guards.csv').read_bytes()
        names=next(csv.reader(io.StringIO(before.decode())))
        rows=list(csv.DictReader(io.StringIO(after[len(before):].decode()),fieldnames=names));count=0
        for row in rows:
            for name in names:
                old=row[name];row[name]='bad';stream=io.StringIO(newline='')
                csv.DictWriter(stream,fieldnames=names,lineterminator='\n').writerows(rows)
                with self.assertRaises(ValueError):fit.checked_guard_bytes(before,before+stream.getvalue().encode())
                row[name]=old;count+=1
        self.assertEqual(count,1815)
        read=Path.read_bytes
        for relative in source.PATHS.values():
            target=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==target else read(p)):
                with self.assertRaises(ValueError):source.freeze(self.root,self.out)
        source.freeze(self.root,self.out)
        self.receipt('matched-fail-closed',raw_words=474,original_words=473,binding_corruptions=180,
            private_pools_rejected=True,guard_field_corruptions=count,unknown_inputs=len(source.PATHS),
            all136_production_inputs_unchanged=True)

    def test_06_three_independent_original_guarded_HI_LO_carry_rebases(self):
        text,functions,relocations=parse_object(self.padded)
        names=sorted({name for uses in self.bindings.values() for _,name in uses})
        code={name for uses in self.bindings.values() for kind,name in uses if kind=='R_MIPS_26'}
        for index in range(3):
            entry=0x15207FF0+index*0x100000
            symbols={name:entry+0x10000+n*0x1000 if name in code else
                0x80100000+n*0x10000+(0x7FFC,0x8004,0x7FD0)[index] for n,name in enumerate(names)}
            emitted,unresolved=emit_function(text,functions[source.FUNCTION],relocations,source.FUNCTION,symbols)
            self.assertFalse(unresolved);asm=self.out/('match-rebase-C-%d.s'%index);asm.write_text(emitted);obj=asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],capture_output=True,check=True)
            images=[]
            for label,path in (('original',self.original),('C',obj)):
                script=self.out/('match-rebase-%s-%d.ld'%(label,index));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(path)],capture_output=True,check=True)
                images.append(sections(elf)['.text'][1][:1892])
            self.assertEqual(images[0],images[1])
        self.receipt('matched-rebases',independent_original_links=3,independent_guarded_links=3,
            all473_words=True,HI_LO_carries=True,SDK_and_game_call_symbols_in_same_jump_region=True)

    def test_07_literal_original_guarded_memory_access_fault_prefixes(self):
        count=0
        for fixture,phase in ((model.fixture(mode=63),0),(model.fixture(slot=1),8),
                (model.fixture(scene=99,mode=1),0),(model.fixture(fail=1),8)):
            memory,args,config=fixture;reference=model.Reference(*fixture).run()
            full=frame_tests.Observed(self.truth,*fixture,reference.allocations,phase).run()
            for fault in range(full.all_accesses):
                machines=[]
                for words in (self.truth,self.normalized):
                    m=frame_tests.Observed(words,memory,args,config,reference.allocations,phase);m.access_fault=fault
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault);machines.append(m)
                self.assertTrue(machine_state(machines[0])==machine_state(machines[1]),(args,config,phase,fault));count+=1
        self.receipt('matched-faults',original_guarded_prefixes=count,
            literal_memory_GPR_FPR_events_PC_delay_access_and_provider_state=True,
            bounded_ABI_hook_accesses_included=True,opaque_provider_bytes_not_SDK_instruction_emulation=True,
            raw_C_fault_equivalence_not_claimed=True)

    def test_08_seven_new_source_screens_do_not_resolve_the_address_shape(self):
        rows=[]
        for label,body in screens.forms():
            row=frame.run(self.root,self.out,'screen-'+label,body)
            self.assertEqual(row['frame'],120);self.assertEqual(row['diagnostics'],'');self.assertFalse(row['pools'])
            rows.append({key:row[key] for key in ('label','words','differences','raw_sha256')})
        self.assertEqual(len(rows),7)
        self.receipt('matched-screens',rows=rows,two_witnesses_each_only=True,
            selected_source_unchanged=True,no_production_installation=True)


if __name__=='__main__':unittest.main()
