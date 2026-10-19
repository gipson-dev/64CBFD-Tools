"""Complete route layout, source loop contracts, returns and actual caller windows."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_route_actor_update_layout as layout
from tools.experiments import game_route_actor_update_integration as integration
from tools.experiments import game_route_actor_update_native as native
from tools.tests import test_game_route_actor_update as guest


class FullOracle(guest.UpdateOracle):
    def __init__(self, words, memory, args, phase=0, helpers=None, effect=0,
            steps=(100.,10.,50.), raw=False, count_effect=None):
        super().__init__(words,memory,args,phase,helpers,effect,steps)
        self.tail = guest.ENTRY + (481 if raw else 490)*4
        self.caller_accesses,self.caller_fault = 0,None
        self.tail_cuts,self.tail_stores = [],[]
        self.count_effect,self.count_gate = count_effect,False

    def access(self):
        if self.own_instruction and guest.ENTRY <= self.current_pc < guest.ENTRY+2416:
            if self.tail <= self.current_pc:
                self.tail_cuts.append(self.caller_accesses)
            if self.caller_accesses == self.caller_fault:
                raise guest.base.faults.AccessBoundary
            self.caller_accesses += 1
        super().access()

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.own_instruction and self.tail <= self.current_pc < guest.ENTRY+2416:
            self.tail_stores.append((address,size,value & ((1 << (size*8))-1)))

    def hook(self,target):
        super().hook(target)
        if target == guest.SELECT and self.count_effect is not None:
            guest.put(self.memory,guest.COUNT,self.count_effect,1)
            self.count_gate = True


def state(model):
    return (model.memory,model.r,model.f,model.events,model.calls,model.provider_calls,
        model.current_pc,model.delay_of,model.lo,model.condition,model.caller_accesses)


class RouteActorUpdateLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        context = integration.historical_view(cls.root,cls.root/integration.BUILD)
        context.__enter__()
        cls.addClassCleanup(context.__exit__,None,None,None)
        cls.out = cls.root/layout.BUILD
        cls.values = layout.source.source.freeze(cls.root,cls.out)
        obj,cls.raw_words,cls.row = layout.source.qualify(cls.root,cls.root/layout.source.BUILD)
        cls.raw,cls.bindings = layout.source.checked(obj)
        cls.normalized,cls.moved = layout.normalize(cls.raw,cls.bindings)
        aliases = dict(bcopy=guest.COPY,sinf=guest.SIN,cosf=guest.COS)
        cls.anchors = {name:aliases[name] if name in aliases else int(name.rsplit('_',1)[1],16)
            for entries in cls.moved.values() for _,name in entries}
        cls.candidate = layout.relocate(cls.normalized,cls.moved,cls.anchors)
        cls.rom = cls.values['conker/conker.us.bin']
        cls.retail = list(struct.unpack_from('>604I',cls.rom,guest.ROM))
        cls.helpers = {}
        for address,count in guest.HELPERS.items():
            at = layout.source.source.prior.elf_slot_offset(cls.values['conker/build/conker.us.elf'],address,count*4)
            words = list(struct.unpack_from('>%dI'%count,cls.values['conker/build/conker.us.elf'],at))
            if words != list(struct.unpack_from('>%dI'%count,cls.rom,address-0x14FD2B50)):
                raise ValueError('Changed full-layout real helper')
            cls.helpers.update(zip(range(address,address+count*4,4),words))
        cls.constants = native.static_constants(cls.root)
        context = patch.dict(guest.STATIC_BYTES,cls.constants)
        context.start()
        cls.addClassCleanup(context.stop)

    def receipt(self,name,**values):
        values.update(raw_SHA256=layout.source.RAW_SHA,normalized_SHA256=layout.NORMALIZED_SHA,
            words=604,frame=456,qualification_reads_predecessor=True,matching_credit_from_suite=0)
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def model(self,words,memory,args,phase=0,real=True,effect=0,steps=(100.,10.,50.),raw=False,count_effect=None):
        return FullOracle(words,memory,args,phase,self.helpers if real else None,effect,steps,raw,count_effect)

    def compare(self,memory,args,phase=0,real=True,effect=0,bodies=None,steps=(100.,10.,50.)):
        pair = [self.model(words,memory,args,phase,real,effect,steps).run()
            for words in (bodies or (self.retail,self.candidate))]
        self.assertEqual(state(pair[0]),state(pair[1]))
        if real:
            expected,calls = guest.reference(memory,args,effect)
            self.assertTrue(guest.public(pair[0].memory)==guest.public(expected),'Ordered reference public mismatch')
            self.assertEqual(pair[0].provider_calls,calls)
        original = self.model(self.raw_words,memory,args,phase,real,effect,steps,raw=True).run()
        self.assertTrue(guest.public(original.memory)==guest.public(pair[0].memory),'Source/layout public mismatch')
        self.assertEqual(original.calls,pair[0].calls)
        self.assertEqual(original.provider_calls,pair[0].provider_calls)
        frame = guest.STACK+phase-456
        for start,length in ((0x70,68),(0xB4,32),(0xD4,132),(0x164,48)):
            self.assertEqual([original.memory[frame+start+i] for i in range(length)],
                [pair[0].memory[frame+start+i] for i in range(length)])
        # This is the declared arena, not a promise for arbitrary public/stack aliases.
        count = max(0,guest.signed(guest.read(memory,guest.COUNT,1),8))
        ranks = {(guest.read(memory,guest.TABLE)+i*132+0x29)&0xFFFFFFFF for i in range(count)}
        for model in (*pair,original):
            for address,size,_ in model.tail_stores:
                self.assertTrue((size==4 and frame+0x70 <= address < frame+0xB4 and not address&3) or
                    (size==1 and frame+0xB4 <= address < frame+0xD4) or (size==1 and address in ranks),
                    'Unclassified tail store %08X/%d'%(address,size))
                self.assertFalse(any(address <= a < address+size for a in (guest.COUNT,0x8009D9F8,0x8009D9FC)))
        return pair

    def test_01_all_604_words_bindings_and_preserved_core(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('No files or retail input in normalizer')):
            raw,moved = layout.normalize(self.raw,self.bindings)
        self.assertEqual(layout.relocate(raw,moved,self.anchors),self.retail)
        core,earlier = layout.core.normalize(self.raw,self.bindings)
        self.assertEqual(raw[:len(core)],core)
        self.assertEqual({i:e for i,e in moved.items() if i<1960},earlier)
        self.assertEqual((len(moved),len(raw),self.row['neighbors']),(70,2416,72))
        self.assertEqual(sum(word>>26==3 for word in self.candidate),20)
        self.assertFalse(any(word>>26==3 or word>>26==0 and word&63==9 for word in self.candidate[490:]))
        self.assertEqual(moved[505*4],[('R_MIPS_LO16','D_8009D9F8')])
        self.assertEqual(moved[539*4],[('R_MIPS_LO16','D_8009D9FC')])
        self.receipt('literal-match',all604_words_equal=True,all70_bindings_preserved=True,
            all20_calls_preserved=True,core490_unchanged=True,retail_not_read_by_recipe=True)

    def test_02_complete_source_corpus_and_fired_count_changes(self):
        for row in native.cases():
            memory,args = native.fixture(row,self.constants)
            self.compare(memory,args,effect=row.get('effect',0))
        for phase,count in itertools.product((0,8),(-128,-1,0,1,2,16,17)):
            memory,args = native.fixture(dict(mode=1),self.constants)
            models = [self.model(words,memory,args,phase,count_effect=count,raw=raw).run()
                for words,raw in ((self.retail,False),(self.candidate,False),(self.raw_words,True))]
            self.assertEqual(state(models[0]),state(models[1]))
            for model in models:
                self.assertTrue(model.count_gate)
                self.assertEqual(guest.signed(guest.read(model.memory,guest.COUNT,1),8),count)
                self.assertTrue(guest.public(model.memory)==guest.public(models[0].memory))
                self.assertEqual(model.provider_calls,models[0].provider_calls)
        self.receipt('connected-corpus',same_native_inputs=553,post_SELECTOR_count_cases=14,
            actual_count_write_gate_fired=True,full_source_and_normalized_public_calls_and_array_payloads_equal=True,
            no_calls_or_unclassified_writes_during_ranking=True,native_builds_reused_not_rerun=True)

    test_03_ranking_domain = guest.RouteActorUpdateTests.test_05_signed_lap_scores_stable_ties_and_all_17_slots
    test_04_indices_and_signed_actor = guest.RouteActorUpdateTests.test_06_null_table_modular_index_and_signed_actor
    test_05_active_and_ticks = guest.RouteActorUpdateTests.test_07_full_width_active_and_signed_tick_divisor
    test_06_error_limits = guest.RouteActorUpdateTests.test_08_exact_error_limits_and_eleven_iteration_stop
    test_07_actual_caller_windows = guest.RouteActorUpdateTests.test_11_whole_Game_direct_scan_and_both_actual_caller_windows

    def test_08_actual_counter_predicates_and_adjacent_addresses(self):
        memory,args = native.fixture({},self.constants)
        score_steps = sort_steps = 0
        for count in range(-128,18):
            last = count-1
            for current in range(max(count,0)):
                a = guest.UpdateOracle([0],memory,args)
                b = guest.UpdateOracle([0],memory,args)
                a.r[6],a.r[11] = current,count&0xFFFFFFFF
                b.r[5],b.r[13] = current+1,count&0xFFFFFFFF
                a.execute(self.raw_words[504]);a.execute(self.raw_words[506])
                b.execute(self.candidate[513]);b.execute(self.candidate[515]);b.execute(self.candidate[542])
                self.assertEqual((a.r[6],a.r[1]),(b.r[8],b.r[1]))
                self.assertEqual(b.r[5],current+2)
                score_steps += 1
            for current in range(1,max(last,0)+1):
                model = guest.UpdateOracle([0],memory,args)
                model.r[8],model.r[11] = current,last
                model.execute(self.candidate[569])
                self.assertEqual(bool(model.r[1]),current!=last)
                self.assertEqual(0x70+(current-1)*4+4,0x70+current*4)
                self.assertEqual(0xB4+(current-1)+1,0xB4+current)
                sort_steps += 1
        self.receipt('induction',signed_count_domain=[-128,17],actual_score_increment_predicate_steps=score_steps,
            actual_sort_less_vs_source_not_equal_steps=sort_steps,adjacent_address_identities=True,
            counters_never_wrap_in_qualified_positive_domain=True,larger_positive_counts_not_qualified=True)

    def test_09_complete_return_and_tail_access_cuts(self):
        cuts = 0
        for phase,profile in itertools.product((0,8),((0,0),(2,1),(17,0))):
            count,mask = profile
            memory,args = native.fixture(dict(mode=0,count=count),self.constants)
            guest.put(memory,guest.MASK,mask,2)
            for i in range(17):
                guest.put(memory,guest.RECORDS+i*132+8,guest.bits(.2))
            complete = self.model(self.retail,memory,args,phase).run()
            for cut in complete.tail_cuts:
                pair = [self.model(words,memory,args,phase) for words in (self.retail,self.candidate)]
                for model in pair:
                    model.caller_fault = cut
                    with self.assertRaises(guest.base.faults.AccessBoundary):
                        model.run()
                    self.assertEqual(model.caller_accesses,cut)
                self.assertEqual(state(pair[0]),state(pair[1]))
                cuts += 1
        self.receipt('tail-cuts',fired_cuts=cuts,equal_full_states=cuts,phases=2,profiles=3,
            return_restore_loads_included=True,core_cuts_reused_from_prior_receipts=True,
            hardware_FCSR_and_arbitrary_aliases_not_claimed=True)

    def test_10_raw_bindings_and_all_tail_recipe_controls(self):
        for i in range(594):
            changed = bytearray(self.raw);changed[i*4] ^= 1
            with self.assertRaises(ValueError):layout.normalize(changed,self.bindings)
        for at in self.bindings:
            changed = dict(self.bindings);changed.pop(at)
            with self.assertRaises(ValueError):layout.normalize(self.raw,changed)
        controls = 0
        for table in (layout.GP,layout.FP):
            for i,rename in table.items():
                changed = dict(rename);changed[next(iter(changed))] ^= 1
                with patch.dict(table,{i:changed}),self.assertRaises(ValueError):layout.normalize(self.raw,self.bindings)
                controls += 1
        order = layout.origins()
        derived = [i for i,v in enumerate(order) if not isinstance(v,int)]
        for i in derived:
            changed = list(order);entry = list(changed[i]);entry[1] += 1;changed[i] = tuple(entry)
            with patch.object(layout,'origins',return_value=changed),self.assertRaises(ValueError):layout.normalize(self.raw,self.bindings)
        for name in ('CURRENT','NEXT'):
            with patch.object(layout,name,getattr(layout,name)^1),self.assertRaises(ValueError):layout.normalize(self.raw,self.bindings)
        self.receipt('closed-controls',raw_word_mutations=594,binding_removals=70,
            tail_register_recipe_mutations=controls,derived_operation_mutations=len(derived),role_mutations=2)

    def test_11_effective_finite_wrong_rank_controls(self):
        for name in ('ascending','zero-based','wrong-constant'):
            memory,args = native.fixture(dict(mode=1),self.constants)
            changed = list(self.candidate)
            if name == 'ascending':changed[555] = layout.core.swap(changed[555],16,11)
            elif name == 'zero-based':changed[586] = changed[586]&~(31<<16) | 8<<16
            else:
                guest.put(memory,guest.RECORDS+0x2A,0,1)
                bonus = guest.floating(guest.read(self.constants,0x8009D9F8))
                penalty = guest.floating(guest.read(self.constants,0x8009D9FC))
                self.assertNotEqual(bonus,penalty)
                guest.put(memory,guest.RECORDS+132+8,guest.bits((bonus+penalty)*.5))
                changed[505] = changed[505]&0xFFFF0000 | self.anchors['D_8009D9FC']&65535
            expected = self.model(self.retail,memory,args).run()
            actual = self.model(changed,memory,args).run()
            self.assertTrue(guest.public(expected.memory)!=guest.public(actual.memory),name+' did not change public ranks')
        self.receipt('semantic-controls',effective_controls=3,ordinary_wrong_public_results=True,
            crashes_timeouts_or_loop_budget_failures_not_credited=True)

    def test_12_production_inputs_and_native_source_stay_frozen(self):
        layout.source.source.freeze(self.root,self.out)
        old = self.root/layout.source.BUILD/'native'
        record = json.loads((old/'native32.json').read_text())
        self.assertEqual(record['raw_target_SHA256'],layout.source.RAW_SHA)
        text = (old/'native-O2.c').read_text();a,b = native.function_span(text,layout.source.source.FUNCTION)
        body = native.strip_externs(layout.source.selected());lo,hi = native.function_span(body,layout.source.source.FUNCTION)
        self.assertEqual(text[a:b],body[lo:hi])
        self.receipt('frozen',protected_inputs=len(self.values),no_production_installation=True,
            source_native_and_old_capture_reused_not_rerun=True)

    def test_13_independent_all_binding_GNU_maps_and_code_rebased_execution(self):
        pairs = ((13,14,'D_800872A0'),(24,25,'D_800CC2D0'),(38,42,'D_800D2390'),
            (43,56,'D_8009D9E0'),(60,67,'D_8009D9E4'),(77,78,'D_8009D9E8'),(214,216,'D_800BE9E4'),
            (259,260,'D_800D239C'),(266,267,'D_800D23A0'),(273,274,'D_800D2398'),(277,278,'D_800D23A4'),
            (283,286,'D_800CC310'),(287,288,'D_8009D9F0'),(313,316,'D_800D2104'),(319,356,'D_800D2390'),
            (430,431,'D_800D2398'),(451,452,'D_800D2398'),(456,458,'D_800D23A9'),
            (463,467,'D_800D18A0'),(472,474,'D_800BE9E4'),(500,505,'D_8009D9F8'),
            (501,504,'D_800D18A0'),(502,503,'D_800872A0'),(518,539,'D_8009D9FC'),(580,581,'D_800872A0'))
        calls = ((89,'func_15088F30'),(107,'func_150498A4'),(113,'func_150498A4'),(196,'func_15088A08'),
            (210,'func_15042D78'),(242,'bcopy'),(248,'func_15088A08'),(253,'func_15088F30'),
            (257,'func_150497E0'),(264,'func_150497E0'),(271,'func_150497E0'),(292,'sinf'),(304,'cosf'),
            (385,'func_15088F30'),(389,'func_150497E0'),(394,'func_150497E0'),(403,'func_15088F30'),
            (407,'func_150497E0'),(413,'func_150497E0'),(488,'func_1508802C'))
        locations = {}
        for hi,lo,name in pairs:
            locations[hi],locations[lo] = ('R_MIPS_HI16',name),('R_MIPS_LO16',name)
        for i,name in calls:locations[i] = ('R_MIPS_26',name)
        self.assertEqual({i*4:[value] for i,value in locations.items()},self.moved)
        lines = ['.set noreorder','.text','.globl route','.type route,@function','route:']
        for i,word in enumerate(self.retail):
            if i in locations:
                kind,name = locations[i]
                mask = 0x3FFFFFF if kind=='R_MIPS_26' else 65535
                lines += ['.word 0x%08X'%(word&~mask),'.reloc .-4,%s,%s'%(kind,name)]
            else:lines.append('.word 0x%08X'%word)
        lines.append('.size route,.-route')
        unit,obj = self.out/'independent.s',self.out/'independent.o'
        unit.write_text('\n'.join(lines)+'\n')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(unit)],check=True,capture_output=True)
        maps = [(guest.ENTRY,self.anchors,False)]
        for base in (0x80000000,0):
            anchors = dict(self.anchors)
            for i,name in enumerate(sorted(name for name in anchors if name.startswith('D_'))):
                anchors[name] = base+(i+1)*0x10000+(0x7FFC,0x8000,0x8004)[i%3]
            for i,name in enumerate(sorted({name for _,name in calls})):
                anchors[name] = 0x15300000+i*0x10000
            maps.append((guest.ENTRY,anchors,False))
        maps += [(0x16218004,self.anchors,True),(0x18FFF000,self.anchors,True)]
        runtime = 0
        for i,(entry,anchors,execute) in enumerate(maps):
            script,elf,binary = (self.out/('map%d.%s'%(i,ext)) for ext in ('ld','elf','bin'))
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e','route',
                *['--defsym=%s=0x%X'%item for item in sorted(anchors.items())],'-o',str(elf),str(obj)],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-objcopy','-O','binary','--only-section=.text',str(elf),str(binary)],check=True,capture_output=True)
            data = binary.read_bytes()
            self.assertEqual(data[2416:],bytes(len(data)-2416))
            independent = list(struct.unpack('>604I',data[:2416]))
            actual = layout.relocate(self.normalized,self.moved,anchors)
            self.assertEqual(independent,actual)
            if not execute:continue
            for row,phase in itertools.product((dict(mode=0),dict(mode=1,count=17),dict(index=1,mode=2,active=256)),(0,8)):
                memory,args = native.fixture(row,self.constants)
                with patch.object(guest,'ENTRY',entry):
                    models = [self.model(words,memory,args,phase).run() for words in (independent,actual)]
                self.assertEqual(state(models[0]),state(models[1]))
                expected,calls = guest.reference(memory,args)
                self.assertTrue(guest.public(models[0].memory)==guest.public(expected))
                self.assertEqual(models[0].provider_calls,calls)
                runtime += 1
        self.receipt('GNU-rebases',independent_links=5,complete_bindings=70,calls=20,
            two_distinct_data_and_call_maps=True,two_code_rebases=True,code_rebased_runtime_cases=runtime,
            changed_global_or_provider_runtime_not_claimed=True)


if __name__ == '__main__':
    unittest.main()
