"""Scheduler-message semantics, guarded instruction identity and live pass state."""
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_frame_driver as source
from tools.tests import frame_driver_checkpoint as checkpoint
from tools.tests import game_frame_driver_oracle as model
from tools.tests import test_game_frame_sequence as sequence
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests.test_game_projected_packet_draw import native_command


def cases():
    for count,pattern,disabled,mode,phase in itertools.product((-1,0,1,3),range(4),(0,1,128,255),range(10),(0,8)):
        yield 1,count,pattern,disabled,0,mode,phase
    for pattern,stop,mode,phase in itertools.product(range(4),(0,1,128,255),(0,8,9),(0,8)):
        yield 2,0,pattern,0,stop,mode,phase
    for code,pattern,stop,phase in itertools.product((-32768,-1,0,3,4,32767),range(4),(0,1),(0,8)):
        yield code,0,pattern,0,stop,0,phase
    for pattern,stop,phase in itertools.product(range(4),(1,128,255),(0,8)):
        yield 1,0,pattern,0,stop,0,phase


class FrameDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.raw,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>412I',cls.rom,source.ROM))
        data,functions=source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        cls.words=list(struct.unpack_from('>412I',data,functions[source.FUNCTION]['value']))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def run_model(self,words,memory,pattern,mode,phase=0,connected=None):
        m=model.DriverOracle(words,memory,pattern,mode,phase,connected=connected)
        halted=False
        try:m.run()
        except model.HaltBoundary:halted=True
        return m,halted

    def test_01_full412_words_derived55_guards_original_frame_homes_and_neighbors(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['slot_words'],
            self.row['new_guards'],self.row['inserted_nops']),(411,104,138,412,55,1))
        self.assertEqual(self.words[8],0xAFA00064)
        self.assertEqual(self.words[211],0xAFA40044)
        original,changed=parse_object(self.out/'neighbor-before.o'),parse_object(self.obj)
        bindings=lambda parsed,f:{a-f['value']:v for a,v in parsed[2].items() if f['value']<=a<f['value']+f['size']}
        self.assertEqual(set(original[1]),set(changed[1]))
        for name,f in original[1].items():
            if name==source.FUNCTION:continue
            g=changed[1][name]
            self.assertEqual(original[0][f['value']:f['value']+f['size']],changed[0][g['value']:g['value']+g['size']],name)
            self.assertEqual(bindings(original,f),bindings(changed,g),name)
        self.assertEqual(len(original[1])-1,15)
        before=(self.out/'before-dispatch_owner').read_text()
        after=source.recovered_owner(before,source.SELECTED)
        self.assertIn('s32 func_15019BB8(Gfx *arg0, s32 arg1)',after)
        self.assertIn('s32 func_15019E60(Gfx *arg0)',after)
        self.assertNotIn('FrameDriverLegacyDisplayListAddress',changed[1])
        self.assertEqual(source.warning_sites(before,(self.out/'neighbor-before-diagnostics.txt').read_text()),
            source.warning_sites(after,self.row['diagnostics']))
        self.assertEqual(len(source.RELOCATIONS),125)
        text,functions,_=changed
        f=functions[source.FUNCTION]
        raw=struct.unpack_from('>411I',text,f['value'])
        classes=dict(branch=0,graphics=0,condition=0,schedule=0)
        for row in source.derived_guards(self.obj):
            offset=int(row['offset'],0)
            if offset in (source.CALL_OFFSET,source.STORE_OFFSET):classes['schedule']+=1
            elif any(lo<=offset<hi for lo,hi in source.ROLE_RANGES):classes['graphics']+=1
            elif source.CONDITION_RANGE[0]<=offset<source.CONDITION_RANGE[1]:classes['condition']+=1
            else:classes['branch']+=1
        self.assertEqual(classes,dict(branch=8,graphics=36,condition=9,schedule=2))
        self.assertEqual(source.normalized_word(raw[0x5AC//4],0x5AC),0x24020001)
        for index,word in enumerate(raw):
            if word>>26 in (1,4,5,6,7,20,21,22,23):
                target=index*4+4+((word&65535)^0x8000)*4-0x20000
                self.assertNotIn(target,(source.CALL_OFFSET,source.STORE_OFFSET))
        targets={int(name[5:],16) if name.startswith('func_') else model.RECV
            for rows in source.RELOCATIONS.values() for kind,name in rows if kind=='R_MIPS_26'}
        self.assertTrue(targets<=set(model.SIGNATURES))

    def test_02_all_message_paths_live_effects_and_public_source_equivalence(self):
        count,visits,actions=0,set(),set()
        for code,views,pattern,disabled,stop,mode,phase in cases():
            memory=model.fixture(code,views,pattern,disabled,stop)
            expected,calls,observations,_,fired,value,halt=model.reference(memory,pattern,mode,phase)
            models=[]
            for words in (self.truth,self.raw,self.words):
                m,halted=self.run_model(words,memory,pattern,mode,phase)
                self.assertEqual(halted,halt)
                self.assertEqual(model.public(m.memory),model.public(expected),(code,views,pattern,disabled,stop,mode,phase))
                self.assertEqual((m.calls,m.observations,m.driver_actions),(calls,observations,fired))
                if not halted:self.assertEqual(m.r[2],value)
                models.append(m)
            self.assertEqual(model.state(models[0]),model.state(models[2]))
            visits.update(models[0].visits)
            actions.update(fired)
            count+=1
        for pattern,old,next_,phase in itertools.product(range(4),(0,1,128,255),(0,1,128,255),(0,8)):
            memory=model.fixture(1,-1,pattern,old)
            memory[model.NEXT]=next_
            expected,calls,observations,_,fired,value,halt=model.reference(memory,pattern,phase=phase)
            models=[]
            for words in (self.truth,self.raw,self.words):
                m,halted=self.run_model(words,memory,pattern,0,phase)
                self.assertEqual((model.public(m.memory),m.calls,m.observations,m.driver_actions,m.r[2],halted),
                    (model.public(expected),calls,observations,fired,value,halt))
                models.append(m)
            self.assertEqual(model.state(models[0]),model.state(models[2]))
            visits.update(models[0].visits)
            count+=1
        for disabled in range(256):
            memory=model.fixture(1,-1,disabled%4,disabled)
            expected,calls,observations,_,fired,value,halt=model.reference(memory,disabled%4)
            m,halted=self.run_model(self.words,memory,disabled%4,0)
            self.assertEqual((model.public(m.memory),m.calls,m.observations,m.driver_actions,m.r[2],halted),
                (model.public(expected),calls,observations,fired,value,halt))
        # The self-loop delay NOP is statically compared; reaching its branch is the declared halt boundary.
        missing=set(range(source.ENTRY,source.ENTRY+1648,4))-visits
        self.assertEqual(missing,{source.ENTRY+0x648})
        self.assertEqual({mode for _,_,mode in actions},set(range(1,10))-{3})
        self.receipt('guest',three_way_cases=count,disabled_byte_sweep=256,root_words_visited=411,
            statically_compared_halt_delay_nop=True,fired_effect_sites=len(actions),
            raw_C_public_protocol_equivalence=True,guarded_original_complete_modeled_state=True,
            SDK_and_other_opaque_helpers_are_contract_fixtures_not_hardware_or_gameplay=True)

    def test_03_every_root_access_prefix_and_signed_halfword_loop_cut(self):
        cuts=0
        representatives=((1,3,0,0,0,0),(1,1,2,0,0,4),(1,1,2,0,0,5),(1,0,2,1,0,6),
            (2,0,1,0,1,9),(2,0,0,0,0,8),(4,0,3,0,0,0))
        for code,views,pattern,disabled,stop,mode in representatives:
            memory=model.fixture(code,views,pattern,disabled,stop)
            complete,_=self.run_model(self.words,memory,pattern,mode)
            for cut in range(complete.root_accesses):
                models=[model.DriverOracle(words,memory,pattern,mode,fault=cut) for words in (self.truth,self.words)]
                for m in models:
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut)
                self.assertEqual(model.state(models[0]),model.state(models[1]))
                cuts+=1
        # Start at the actual first-loop increment to qualify s16 wrap without
        # running tens of thousands of opaque callbacks or changing production bounds.
        entry=0x1501897C
        loop=list(struct.unpack_from('>8I',self.rom,source.ROM+entry-source.ENTRY))
        records=[]
        for views in (0x7FFF,0x8000,0x7FFFFFFF):
            memory=model.fixture(1,views,0,1)
            connected={source.ENTRY+i*4:w for i,w in enumerate(self.words)}
            m=model.DriverOracle(loop,memory,entry=entry,connected=connected,target_limit=(0x15018F80,1))
            for register,value in ((16,0x7FFF),(17,model.CURSOR),(18,model.INDEX),(19,model.COUNT),(20,model.MAP),(2,model.BUFFERS[0])):
                m.r[register]=m.before[register]=value
            m.memory[model.MAP-0x8000]=255
            with self.assertRaises(model.CallBoundary):m.run()
            self.assertEqual(m.r[16],0xFFFF8000)
            self.assertEqual(m.calls[-1],(0x15018F80,(255,)))
            records.append(views)
        self.receipt('faults',every_access_prefixes=cuts,representative_paths=len(representatives),
            actual_first_loop_cut_words=8,signed_halfword_wrap_counts=records,portable_C_fault_claim=False)

    def test_04_real_coordinator_preparation_sdk_and_product_pipeline(self):
        read=Path.read_bytes
        with patch.object(Path,'read_bytes',lambda p:checkpoint.previous_input(read(p),p,self.root)):
            sequence.FrameSequenceTests.setUpClass()
        helper=sequence.FrameSequenceTests
        self.assertEqual(helper.words,list(struct.unpack_from('>185I',self.rom,0x465E0)))
        connected=dict(helper.connected)
        connected.update({0x15019130+i*4:w for i,w in enumerate(helper.words)})
        targets={int(name[5:],16) if name.startswith('func_') else model.RECV
            for rows in source.RELOCATIONS.values() for kind,name in rows if kind=='R_MIPS_26'}
        count=0
        for views,pattern,phase in itertools.product((-1,0,1,3),range(4),(0,8)):
            memory=model.fixture(1,views,pattern,0)
            expected,calls,observations,_,_,value,halt=model.reference(memory,pattern,phase=phase,connected=True)
            models=[]
            for words in (self.truth,self.words):
                m,halted=self.run_model(words,memory,pattern,0,phase,connected)
                self.assertEqual((model.public(m.memory),m.calls,m.r[2],halted),(model.public(expected),calls,value,halt))
                self.assertEqual([row for row in m.observations if row[0] in targets],observations)
                models.append(m)
            self.assertEqual(model.state(models[0]),model.state(models[1]))
            count+=1
        self.receipt('connected',cases=count,real_words=[185,40,46,78],
            callbacks_other_than_connected_helpers_remain_contracts=True,full_gameplay_or_hardware_not_claimed=True)

    def test_05_all_screens_word_binding_guard_warning_and_frozen_controls(self):
        before=(self.out/'before-dispatch_owner').read_text()
        for label,body in source.forms():
            row=json.loads((self.out/(label+'.json')).read_text())
            self.assertEqual((self.out/(label+'.c')).read_text(),source.recovered_owner(before,body))
            text,functions,rel=parse_object(self.out/(label+'.o'))
            f=functions[source.FUNCTION]
            self.assertEqual(hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),row['raw_sha256'])
            binding={str(a-f['value']):v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
            self.assertEqual(binding,{a:[tuple(v) for v in rows] for a,rows in row['relocations'].items()})
            data=sections(self.out/(label+'.elf'))['.text'][1]
            words=struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])
            differences=sum(a!=b for a,b in zip(words,self.truth))+abs(len(words)-412)
            self.assertEqual((len(words),(-words[0])&65535,differences),(row['words'],row['frame'],row['differences']))
            self.assertFalse(row['pools'])
        text,functions,rel=parse_object(self.obj)
        f=functions[source.FUNCTION]
        for i in range(411):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for offset in source.RELOCATIONS:
            bad=dict(rel);bad[f['value']+offset]=[('R_MIPS_26','wrong')]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        with patch.object(source,'sections',return_value={'.rodata':(0,b'x')}):
            with self.assertRaises(ValueError):source.checked_object(self.obj)
        guards=source.guarded_manifest(self.out,self.obj)
        self.assertTrue(guards.startswith((self.out/'before-guards').read_bytes()))
        added=list(csv.DictReader(io.StringIO(guards[len((self.out/'before-guards').read_bytes()):].decode()),
            fieldnames=list(csv.DictReader(io.StringIO(guards.decode())).fieldnames)))
        self.assertEqual(len(added),55)
        old=source.pad_c_object.load_word_patches(self.out/'qualified-guards.csv',source.OWNER)
        for index,row in enumerate(added):
            key=(row['function'],int(row['offset'],0))
            bad={k:dict(v) for k,v in old.items()};bad[key]['expected']^=1
            with patch.object(source.pad_c_object,'load_word_patches',return_value=bad):
                with self.assertRaisesRegex(ValueError,'stale'):
                    source.pad_c_object.emit_padded_assembly(self.obj,self.root/source.PATHS['layout'],source.OWNER,
                        word_patches_path=self.out/'qualified-guards.csv')
            for field in ('replacement','expected_relocations','replacement_relocations','insert_after','insert_after_relocations','omit'):
                bad=dict(row);bad[field]=bad[field]+'x'
                stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(row),lineterminator='\n')
                writer.writerows(bad if i==index else original for i,original in enumerate(added))
                with self.assertRaises(ValueError):source.checked_manifest((self.out/'before-guards').read_bytes()+stream.getvalue().encode(),self.out,self.obj)
        for diagnostic in ('',self.row['diagnostics']+'\n',self.row['diagnostics'].replace('Warning 712','Warning 713',1)):
            with self.assertRaises(ValueError):source.warning_sites(source.recovered_owner(before,source.SELECTED),diagnostic)
        read=Path.read_bytes
        for key in source.PATHS:
            path=self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                with self.assertRaisesRegex((ValueError,AssertionError),'fixture'):source.freeze(self.root,self.out)

    def test_06_independent_rebases_branch_targets_and_complete_prediction(self):
        text,functions,rel=parse_object(self.padded)
        f=functions[source.FUNCTION]
        template=list(struct.unpack_from('>412I',text,f['value']))
        bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
        names=sorted({n for rows in bindings.values() for _,n in rows})
        for seed in (0,1):
            anchors={n:(0x15120000+i*0x40 if n.startswith('func_') or n=='osRecvMesg' else
                0x90000000+i*0x20000+(0x7FF0 if (i+seed)%2 else 0xFFF0)) for i,n in enumerate(names)}
            assembly,unresolved=emit_function(text,f,rel,source.FUNCTION,anchors)
            self.assertFalse(unresolved)
            path=self.out/('rebase-%d.s'%seed);path.write_text(assembly)
            obj=path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
            script=path.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
            elf=path.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                *['--defsym=%s=0x%X'%item for item in anchors.items()],'-o',str(elf),str(obj)],capture_output=True,check=True)
            expected=template.copy()
            for offset,rows in bindings.items():
                kind,name=rows[0];value=anchors[name];word=expected[offset//4]
                self.assertEqual(word&(0x03FFFFFF if kind=='R_MIPS_26' else 65535),0)
                expected[offset//4]=((word&0xFC000000)|((value>>2)&0x03FFFFFF)) if kind=='R_MIPS_26' else (
                    (word&0xFFFF0000)|(((value+0x8000)>>16)&65535 if kind=='R_MIPS_HI16' else value&65535))
            self.assertEqual(list(struct.unpack_from('>412I',sections(elf)['.text'][1])),expected)
        row=source.prelink_prediction(self.root,self.out)
        self.assertEqual(row['after'],checkpoint.AFTER)
        self.assertEqual((row['changed_ELF_bytes'],row['metadata_serialization_bytes'],row['metadata_exclusions']),(1301,111,0))
        slot=(self.out/'predicted-slot.bin').read_bytes()
        for i in range(412):
            bad=bytearray(slot);bad[i*4]^=1
            with self.assertRaises(ValueError):source.slot_expected_image((self.out/'before-elf').read_bytes(),bytes(bad))
        structural=source.slot_expected_image((self.out/'before-elf').read_bytes(),slot)
        for at in (0,2897680,3160371,2947040,3200727,2952160,3205001):
            bad=bytearray(structural);bad[at]^=1
            with self.assertRaises(ValueError):source.serialize_metadata(bytes(bad))

    def test_07_native32_actual_C_opaque_protocols_and_effective_controls(self):
        from tools.tests import game_frame_driver_native as native
        harness=self.out/'native-harness.c'
        harness.write_text(native.program())
        exits={}
        for label,opt,body,valid in [('O2','-O2',source.SELECTED,True),('O0','-O0',source.SELECTED,True)]+[
                (name,'-O2',body,False) for name,body in native.controls().items()]:
            if not valid:self.assertNotEqual(body,source.SELECTED)
            path=self.out/('native-body-'+label+'.c');path.write_text(native.HEADER+body)
            exe=self.out/('native-'+label)
            result=subprocess.run([*native_command(opt,valid),'-mstackrealign','-fno-strict-aliasing',str(path),str(harness),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,timeout=30)
            self.assertIn(result.returncode,(0,) if valid else tuple(range(21,27)),(label,result.stderr))
            exits[label]=result.returncode
        self.receipt('native',cases_per_selected=sum(1 for _ in native.corpus()),separate_units_native32_O2_O0_UBSan=True,
            actual_selected_driver_C=True,providers_are_guest_qualified_packet_fixtures=True,
            SDK_hardware_and_shutdown_sink_not_native_claims=True,exits=exits)


if __name__=='__main__':unittest.main()
