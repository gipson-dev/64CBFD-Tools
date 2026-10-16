"""Full timing recovery, overlapping labels and explicit remaining match gaps."""
import csv
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_frame_timing_update as source
from tools.tests import game_frame_timing_oracle as model
from tools.tests import game_frame_timing_native as native
from tools.tests import test_game_actor_burst_consumer_match as tracking
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_one_shot_timer_match import canonical_symbols,symbol_rows


class FrameTimingUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.raw,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>192I',cls.rom,source.ROM))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_raw191_frame_15_neighbors_and_no_new_guards(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['real_word_differences']),(191,24,141))
        self.assertFalse(self.row['byte_exact']);self.assertEqual(self.row['new_guards'],0)
        old,new=parse_object(self.out/'neighbor-before.o'),parse_object(self.obj)
        self.assertEqual(set(old[1]),set(new[1]));self.assertEqual(len(old[1])-1,15)
        binding=lambda p,f:{a-f['value']:v for a,v in p[2].items() if f['value']<=a<f['value']+f['size']}
        for name,f in old[1].items():
            if name==source.FUNCTION:continue
            g=new[1][name]
            self.assertEqual(old[0][f['value']:f['value']+f['size']],new[0][g['value']:g['value']+g['size']],name)
            self.assertEqual(binding(old,f),binding(new,g),name)
        rows=csv.DictReader((self.out/'before-guards').read_text().splitlines())
        self.assertFalse(any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in rows))
        data,functions=source.build.link_owner(self.root,self.out,self.padded,source.OWNER);f=functions[source.FUNCTION]
        self.assertEqual((f['size'],data[f['value']:f['value']+768]),(764,struct.pack('>191I',*self.raw)+bytes(4)))

    def test_02_full_byte_domains_overlap_float_rounding_and_legal_instruction_coverage(self):
        count=0;seen=[set(),set()];different_orders=0;negative_zero=infinite=False
        for memory,mode,args in model.corpus():
            expected,calls,observations=model.reference(memory,mode)
            for phase in (0,8):
                models=[]
                for i,words in enumerate((self.truth,self.raw)):
                    m=model.TimingOracle(words,memory,mode,phase).run()
                    self.assertEqual((model.public(m.memory),m.calls,m.observations),
                        (model.public(expected),calls,observations),(args,phase))
                    seen[i].update(m.visits);models.append(m)
                events=lambda m:[e for e in m.events if e[0] in ('R','W') and model.BASE<=e[1]<model.BASE+model.LENGTH]
                different_orders+=events(models[0])!=events(models[1]);count+=1
            negative_zero|=model.read(expected,model.MEAN)==0x80000000
            infinite|=model.read(expected,model.MEAN_INV) in (0x7F800000,0xFF800000)
        body=set(range(source.ENTRY,source.ENTRY+764,4))
        cold=((0x84,0x88,0x8C,0x90,0xDC),(0x88,0x8C,0x90,0x94,0xE0))
        for visits,excluded in zip(seen,cold):self.assertEqual(visits,body-{source.ENTRY+x for x in excluded})
        self.assertTrue(negative_zero);self.assertTrue(infinite);self.assertGreater(different_orders,0)
        self.receipt('guest',retail_C_cases=count,cases=len(list(model.corpus())),legal_words_visited_each=186,
            cold_words_each=5,trailing_padding_words=1,all256_divisor_phase_index_sample_bytes=True,
            all_indices_in_one_mapped_history_region=True,negative_zero_mean_and_infinite_reciprocal=True,
            different_access_orders=different_orders,fault_prefix_equivalence_not_claimed=True,
            nearest_single_no_NaN_payload_or_hardware_FCSR_claim=True)

    def test_03_native32_O2_O0_UBSan_and_ten_effective_controls(self):
        harness=self.out/'native.c';harness.write_text(native.program());exits={}
        for name,opt,body in [('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[
                (name,'-O2',body) for name,body in native.controls().items()]:
            unit=self.out/('native-'+name+'.c');unit.write_text(native.HEADER+body+'\n');exe=unit.with_suffix('.elf')
            result=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',
                str(unit.relative_to(self.root)),str(harness.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            run=subprocess.run([str(exe)],capture_output=True,text=True);exits[name]=run.returncode
            if name in ('o2','o0'):self.assertEqual(run.returncode,0,run.stderr)
            else:self.assertIn(run.returncode,range(21,25),name)
        self.receipt('native',cases_each=len(list(model.corpus())),exits=exits,actual_C_O2_O0_UBSan=True,
            no_fwrapv_needed=True,one_valid1104_byte_union=True,big_endian_byte_views=True,
            full_memory_canaries_and_final_callback_snapshot=True,all256_index_aliases=True)

    def test_04_all191_words_59_bindings_extra_binding_and_pools_fail_closed(self):
        text,functions,relocations=parse_object(self.obj);f=functions[source.FUNCTION]
        for i in range(191):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,relocations)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        _,bindings=source.checked_object(self.obj)
        for offset in (*bindings,0):
            bad=dict(relocations);bad[f['value']+offset]=[('R_MIPS_26','wrong')]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        with patch.object(source.previous.previous,'sections',return_value={'.rodata':(0,b'bad')}):
            with self.assertRaises(ValueError):source.checked_object(self.obj)

    def test_05_independent_source_rebases_and_all_three_history_addend_carries(self):
        text,functions,relocations=parse_object(self.obj);f=functions[source.FUNCTION]
        raw,bindings=source.checked_object(self.obj)
        names=sorted({name for rows in bindings.values() for _,name in rows});high_addends={596:4,608:8,612:40}
        for index in range(3):
            entry=0x15207FF0+index*0x100000
            symbols={name:(entry+0x10000 if name.startswith('func_') else
                0x80100000+n*0x10000+((0x7FFC,0x8004,0x7FD0)[index])) for n,name in enumerate(names)}
            emitted,unresolved=emit_function(text,f,relocations,source.FUNCTION,symbols);self.assertFalse(unresolved)
            path=self.out/('rebase-%d.s'%index);path.write_text(emitted);obj=path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
            script=path.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            elf=path.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,check=True)
            expected=list(raw)
            for offset,((kind,name),) in bindings.items():
                word=raw[offset//4];value=symbols[name]
                if kind=='R_MIPS_HI16':word=(word&0xFFFF0000)|(((value+high_addends.get(offset,0)+0x8000)>>16)&65535)
                elif kind=='R_MIPS_LO16':word=(word&0xFFFF0000)|((value+((word&65535)^0x8000)-0x8000)&65535)
                elif kind=='R_MIPS_26':word=(word&0xFC000000)|((value>>2)&0x3FFFFFF)
                else:self.fail(kind)
                expected[offset//4]=word
            self.assertEqual(sections(elf)['.text'][1][:764],struct.pack('>191I',*expected))
        self.receipt('rebases',independent_source_links=3,all191_words=True,all59_bindings=True,
            history_high_addends=[4,8,40],original_source_word_identity_not_claimed=True)

    def test_06_actual53_word_caller_void_call_and_ignored_result(self):
        caller,join,published=0x15019088,0x15019094,0x800BE728
        class Join(Exception):pass
        class CallerCode(tracking.TrackedCode):
            def __getitem__(self,pc):
                if pc==join:raise Join
                return super().__getitem__(pc)
        class CallerOracle(model.TimingOracle):
            def record_call(self,target):
                if target==source.ENTRY:
                    self.calls.append((target,()));self.events.append(('CALL',target,()))
                    self.observations.append(model.digest(self.memory))
                else:super().record_call(target)
        data,functions=source.build.link_owner(self.root,self.out,self.padded,source.OWNER);f=functions['func_1501905C']
        full=list(struct.unpack_from('>53I',data,f['value']))
        self.assertEqual(full,list(struct.unpack_from('>53I',self.rom,0x4650C)))
        cut=full[11:14];self.assertEqual(len(cut),3);count=0
        for ticks,divisor,index,samples,mode in ((t,d,i,n,m) for t in (0,0xFFFFFFFF)
                for d in (0,1,3) for i in (9,12,80,240,255) for n in (9,10) for m in (0,1,2)):
            memory=model.fixture(ticks,divisor,1,255,index,samples,3,0x7FFFFFFF)
            previous_return=0x12345678^ticks
            before=dict(memory);model.put(before,published,previous_return)
            expected,calls,observations=model.reference(before,mode)
            for words in (self.truth,self.raw):
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)};connected[join]=0
                m=CallerOracle(cut,memory,mode,entry=caller,connected=connected);m.code=CallerCode(m.code,m)
                m.r[2]=previous_return
                with self.assertRaises(Join):m.run()
                self.assertEqual((model.public(m.memory),m.calls,m.observations),
                    (model.public(expected),[(source.ENTRY,())]+calls,[model.digest(before)]+observations))
                for register in (*range(16,24),28,29,30):self.assertEqual(m.r[register],m.before[register])
                self.assertEqual(m.r[31],join)
            count+=1
        self.receipt('caller',cases=count,fresh_full_caller_words=53,actual_call_cut_words=3,
            caller='func_1501905C',prior_result_publication_in_call_delay=True,
            no_arguments_no_consumed_return=True,full_frame_pipeline_not_claimed=True)

    def test_07_named_metadata_permutations_and_integer_HI_LO_primitives(self):
        data=(self.out/'structural-prediction.elf').read_bytes();after=source.serialize_metadata(data)
        self.assertEqual(canonical_symbols(data),canonical_symbols(after))
        self.assertEqual(sum(a!=b for a,b in zip(data,after)),173)
        names={n for group,_,_ in source.SERIALIZATION for n in group}
        rows={r[1]:r for r in symbol_rows(data) if r[1] in names};self.assertEqual(len(rows),15)
        for name,row in rows.items():
            for at in (row[0],row[0]+4,row[0]+8,row[0]+12,row[0]+13,row[0]+14,row[3]):
                bad=bytearray(data);bad[at]^=1
                with patch.object(source,'STRUCTURAL_SHA256',hashlib.sha256(bad).hexdigest()):
                    with self.assertRaises((AssertionError,ValueError)):source.serialize_metadata(bytes(bad))
        m=model.TimingOracle(self.raw,model.fixture())
        for fn,left,right,q,r in ((26,0xFFFFFFE1,30,0xFFFFFFFF,0xFFFFFFFF),
                (26,0x80000000,30,0xFBBBBBBC,0xFFFFFFF8),(27,0xFFFFFFFF,2,0x7FFFFFFF,1)):
            m.r[4],m.r[5]=left,right;m.execute((4<<21)|(5<<16)|fn)
            self.assertEqual((m.lo,m.hi),(q,r))
        m.r[4]=m.r[5]=0xFFFFFFFF;m.execute((4<<21)|(5<<16)|25)
        self.assertEqual((m.hi,m.lo),(0xFFFFFFFE,1));m.execute((2<<11)|16);self.assertEqual(m.r[2],m.hi)


if __name__=='__main__':unittest.main()
