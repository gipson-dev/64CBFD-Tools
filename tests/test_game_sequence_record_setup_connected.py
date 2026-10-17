"""Execute real setup callers and six installed helpers with bounded SDK resources."""
import itertools
import json
from pathlib import Path
import re
import struct
import unittest

from tools.experiments import game_sequence_record_setup as source
from tools.experiments import game_sequence_record_setup_matching as fit
from tools.experiments import game_sequence_record_setup_installation as install
from tools.experiments.game_sequence_record_setup_frame import WITNESS_ENTRY
from tools.tests import game_sequence_record_setup_oracle as model
from tools.tests import game_sequence_state_reset_oracle as reset
from tools.tests.test_game_record_constructor_match import elf_slot_offset

RESOURCE = 0x1502B6BC
HELPERS = ((model.RESET,100), (reset.HELPER,10), (model.LOAD,33),
    (model.SUM,19), (model.COUNTER,37), (model.MAXIMUM,105))
ARITIES = dict(model.ARITIES)
ARITIES.update({source.ENTRY:5, reset.HELPER:0, RESOURCE:7,
    0x151E530C:0, 0x1517EFDC:0, 0x151E5034:0})


def half(value): return (value ^ 32768) - 32768


def helper_effects(target, memory, slot):
    count = model.read(memory, model.COUNTS + slot, 1)
    if target == model.SUM:
        base = model.read(memory, model.PREFERRED + slot*4)
        return sum(model.read(memory, base+i*2, 2) for i in range(count))
    if target == model.COUNTER:
        for i in range(count):
            record = model.read(memory, 0x800C3960 + slot*120 + i*4)
            for j in range(16): memory[record+j] = 255
    if target == model.MAXIMUM:
        primary = model.read(memory, model.PREFERRED + slot*4)
        enabled = model.read(memory, model.ENABLED + slot*4)
        fallback = model.read(memory, model.FALLBACK + slot*4)
        maximum = 0
        if count and model.read(memory, primary, 2) >= 4:
            record = model.read(memory, 0x800C3688 + slot*120)
            value = half(model.read(memory, record+0x12, 2))
            if value != -9999:
                model.put(memory, 0x800C3640 + slot*4, value & model.MASK)
                return 0
        preferred = []
        for i in range(count):
            if model.read(memory, enabled+i*2, 2) and model.read(memory, primary+i*2, 2):
                record = model.read(memory, 0x800C3688 + slot*120 + i*4)
                preferred.append(half(model.read(memory, record+0xA, 2)))
        if preferred: maximum = max(0, *preferred)
        if maximum == 0:
            for i in range(count):
                entries = model.read(memory, fallback+i*2, 2)
                if model.read(memory, enabled+i*2, 2) and entries:
                    record = model.read(memory, 0x800C3778 + slot*120 + i*4)
                    maximum = max(maximum, half(model.read(memory, record+entries*8-2, 2)))
        model.put(memory, 0x800C3640 + slot*4, maximum & model.MASK)
    return 0


class Reference(model.Reference):
    def call(self, target, *args):
        if target in (model.SUM, model.COUNTER, model.MAXIMUM):
            value = helper_effects(target, self.memory, args[0])
            if target == model.SUM: self.config = dict(self.config, total=value)
        return super().call(target, *args)


def fixture(slot=0, count=2, maximum=0, fail=0, state=0, gate=0, scene=37, hook=0):
    memory, args, config = model.fixture(slot=slot, counts=(count,count,count,1),
        state=state, gate=gate, scene=scene, hook=hook, fail=fail)
    for i in range(1,64):
        record = model.PAYLOAD + i*256
        memory.update({record+j:0xA5 for j in range(256)})
        model.put(memory, record+0xA, (23 if maximum == 0 else -3) & 65535, 2)
        model.put(memory, record+0x12, (17 if maximum == 2 else -9999) & 65535, 2)
        model.put(memory, record+6, (-5 if maximum == 4 else 41) & 65535, 2)
        model.put(memory, record+14, (-5 if maximum == 4 else 53) & 65535, 2)
    if maximum >= 2:
        descriptor = 2*count+2
        model.put(memory, model.BUNDLE+descriptor*8+4, 32)
    return memory, args, config


class Connected(model.SetupOracle):
    def record_call(self, target):
        packet = self.arguments(ARITIES[target])
        self.calls.append((target,packet)); self.events.append(('CALL',target,packet))

    def hook(self, target):
        packet = self.calls[-1][1]
        if target == RESOURCE:
            if (packet[1],packet[3:]) != (0,(3,6,self.provider.args[0],self.provider.args[1])):
                raise ValueError('Unexpected actual resource-loader packet')
            result = 0 if self.provider.config['fail'] else model.BUNDLE
        elif target in (0x151E530C,0x1517EFDC,0x151E5034):
            result = self.provider.config.get('menu_result',0) if target == 0x1517EFDC else 0
        else:
            if target == model.ZERO and packet == (reset.TABLE,168):
                result = self.provider.call(target,*packet)
            elif target in dict(HELPERS): raise ValueError('A connected helper fell back to an opaque hook')
            else: return super().hook(target)
        for i in range(4): self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25): self.r[reg] = 0xA5000000+reg
        self.f[:20] = [0xA5000000+i for i in range(20)]; self.r[2] = result


class CallBoundary(Exception): pass


class CallerCut(Connected):
    def record_call(self,target):
        if target != source.ENTRY: raise ValueError('Unexpected call in setup ABI cut')
        super().record_call(target)
        raise CallBoundary


class SequenceRecordSetupConnectedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]; cls.out = cls.root / install.BUILD
        install.freeze(cls.root,cls.out)
        cls.obj,cls.padded,_,cls.guarded,_ = fit.guarded(cls.root,cls.out)
        install.qualify_callers(cls.root,cls.out)
        data, functions = source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        raw, raw_functions = source.build.link_owner(cls.root,cls.out,cls.obj,source.OWNER)
        f = raw_functions[source.FUNCTION]
        cls.raw = list(struct.unpack_from('>474I',raw,f['value']))
        cls.truth = list(struct.unpack_from('>473I',(cls.out/'before-retail_rom').read_bytes(),source.ROM))
        cls.helpers = {}; image = (cls.out/'before-elf').read_bytes(); rom = (cls.out/'before-retail_rom').read_bytes()
        for entry, words in HELPERS:
            f = functions['func_%08X'%entry]; body = data[f['value']:f['value']+words*4]
            if f['size'] != words*4: raise ValueError('Connected helper extent changed')
            at = elf_slot_offset(image,entry,words*4)
            if body != image[at:at+words*4] or body != rom[entry-0x15000000+0x2D4B0:entry-0x15000000+0x2D4B0+words*4]:
                raise ValueError('Connected helper is not independently retail-exact')
            cls.helpers.update(zip(range(entry,entry+words*4,4),struct.unpack('>%dI'%words,body)))
        cls.callers = {}
        for key,owner,_,_ in install.CALLERS:
            data, fs = source.build.link_owner(cls.root,cls.out,cls.out/(key+'-after-padded.o'),owner)
            name = 'func_150082CC' if key == 'view_init_caller_owner' else 'func_151E83E8'
            entry = int(name[5:],16); f = fs[name]; body = data[f['value']:f['value']+f['size']]
            at = elf_slot_offset(image,entry,f['size'])
            if body != image[at:at+f['size']]: raise ValueError('Typed setup caller changed installed instructions')
            cls.callers[entry] = list(struct.unpack('>%dI'%(len(body)//4),body))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def check(self,memory,args,config,phase=0,entry=None,caller=None):
        reference = Reference(memory,args,dict(config)).run(); machines = []
        for index,words in enumerate((self.truth,self.raw,self.guarded)):
            helpers = dict(self.helpers)
            if caller is not None:
                helpers.update(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words))
                m = Connected(caller,memory,args,config,reference.allocations,phase,entry=entry,helpers=helpers).run()
            else:
                m = Connected(words,memory,args,config,reference.allocations,phase,
                    entry=WITNESS_ENTRY if index == 1 else source.ENTRY,helpers=helpers).run()
            self.assertTrue(model.public(m.memory) == model.public(reference.memory),(args,config,index))
            self.assertEqual(m.provider.allocations,reference.allocations)
            top_calls = [c for c in m.calls if c[0] not in (source.ENTRY,reset.HELPER,RESOURCE)
                and c != (model.ZERO,(reset.TABLE,168))]
            self.assertEqual(top_calls,reference.calls)
            machines.append(m)
        for m in machines[1:]:
            self.assertEqual(m.calls,machines[0].calls)
            self.assertEqual(model.public(m.memory),model.public(machines[0].memory))
        return machines

    def test_01_real_six_helper_chain_and_independent_sum_clear_and_maximum(self):
        count = 0; seen = set()
        for slot,records,maximum,fail,state,hook in itertools.product((0,1),(0,1,3),range(5),(0,1),(0,2),(0,1)):
            for phase in (0,8):
                machines = self.check(*fixture(slot,records,maximum,fail,state,hook=hook),phase=phase)
                seen.update(machines[0].visits); count += 1
        self.assertTrue(set(self.helpers) <= seen)
        self.receipt('connected-helpers',three_way_cases=count,helpers=[['%08X'%e,w] for e,w in HELPERS],
            all304_helper_words_executed=True,independent_public_memory_and_allocation_reference=True,
            actual_resource_loader_with_bounded_seven_argument_resource_provider=True,
            not_DMA_allocator_or_gameplay_acceptance=True)

    def test_02_actual_29_word_pending_sequence_caller_with_setup_and_helpers(self):
        entry = 0x150082CC; count = 0
        for gate,flag,state,hook in itertools.product((0,1,2,255),(0,1),(0,1,2),(0,1)):
            memory,args,config = fixture(state=state,hook=hook)
            model.put(memory,0x800C35C4,gate,1); model.put(memory,0x800C35C5,flag,1)
            model.put(memory,0x800C3C90,hook,1); model.put(memory,0x800C3C94,args[4])
            expected = dict(memory)
            if gate:
                if flag == 0: model.put(expected,model.STATUS,2,1)
                model.put(expected,0x800C35C4,0,1)
                setup_args = (37,gate-1,0,hook,args[4]); reference = Reference(expected,setup_args,config).run()
            else: setup_args = args; reference = Reference(expected,setup_args,config)
            for words in (self.truth,self.guarded):
                helpers = dict(self.helpers); helpers.update(zip(range(source.ENTRY,source.ENTRY+1892,4),words))
                m = Connected(self.callers[entry],memory,setup_args,config,reference.allocations,entry=entry,helpers=helpers).run()
                self.assertEqual(model.public(m.memory),model.public(reference.memory),(gate,flag,state,hook))
            count += 1
        self.receipt('connected-pending-caller',actual_caller_words=29,original_guarded_cases=count,
            zero_gate_and_delayed_fifth_argument=True,reset_load_and_record_helpers_connected=True,
            all_caller_instructions_preserved=True,not_full_startup_acceptance=True)

    def test_03_actual_50_word_scene_caller_and_postcall_threshold_branches(self):
        entry = 0x151E83E8; count = 0
        for started,current,elapsed,result,state in itertools.product((0,1),(29,37),(0,100,101),(0,1),(0,1)):
            memory,args,config = fixture(state=state,scene=29)
            args = (29,6,0,0,0); config = dict(config,menu_result=result)
            for at,size,value in ((0x800E0A80,2,started),(0x800BE9F0,4,current),(0x800E0A90,4,elapsed),
                    (0x8008FDA4,1,0xA5),(0x800E0B94,1,0xA5),(0x800D2E40,4,0xA5A5A5A5)):
                model.put(memory,at,value,size)
            expected = dict(memory)
            if started == 0:
                model.put(expected,0x800E0A80,65535,2); reference = Reference(expected,args,config).run()
            else: reference = Reference(expected,args,config)
            if not result: model.put(reference.memory,0x800E0A90,0)
            if result and elapsed >= 101:
                for at,size,value in ((0x8008FDA4,1,0),(0x800E0B94,1,1),(0x800E0A90,4,0),(0x800D2E40,1,0)):
                    model.put(reference.memory,at,value,size)
            for phase in (0,8):
                machines = []
                for words in (self.truth,self.guarded):
                    helpers = dict(self.helpers); helpers.update(zip(range(source.ENTRY,source.ENTRY+1892,4),words))
                    m = Connected(self.callers[entry],memory,args,config,reference.allocations,phase,
                        entry=entry,helpers=helpers).run()
                    self.assertEqual(model.public(m.memory),model.public(reference.memory),(started,current,elapsed,result,state))
                    machines.append(m)
                self.assertEqual(machines[0].calls,machines[1].calls)
                count += 1
        self.receipt('connected-scene-caller',actual_caller_words=50,original_guarded_cases=count,
            actual_setup_and_six_helpers=True,postcall_threshold_and_request_packet=True,
            unrelated_scene_providers_bounded=True,not_menu_or_gameplay_acceptance=True)

    def test_04_real_helper_effect_controls_are_observed(self):
        memory,args,config = fixture(count=3); reference = Reference(memory,args,config).run()
        mutations = {}
        for entry in (model.RESET,model.COUNTER,model.MAXIMUM):
            changed = dict(self.helpers); changed[entry] = 0x03E00008; changed[entry+4] = 0
            mutations['skip-%08X'%entry] = changed
        changed = dict(self.helpers)
        at = next(a for a in range(model.SUM,model.SUM+76,4) if changed[a] == 0x00001025)
        changed[at] = 0x24020001; mutations['sum-off-by-one'] = changed
        for label,helpers in mutations.items():
            m = Connected(self.guarded,memory,args,config,reference.allocations,helpers=helpers).run()
            self.assertNotEqual(model.public(m.memory),model.public(reference.memory),label)
        self.receipt('connected-controls',four_actual_helper_effect_mutations_rejected=list(mutations))

    def test_05_all_nine_original_assembly_call_packets_and_delay_slots(self):
        windows = ((0x1509C514,0x1509C520),(0x1509C58C,0x1509C5AC),
            (0x1509C658,0x1509C668),(0x150A1CD4,0x150A1CDC),(0x1501E988,0x1501E99C),
            (0x151DE9B4,0x151DE9C4),(0x151E4388,0x151E438C),
            (0x151E44D4,0x151E44D8),(0x151E8410,0x151E8418))
        words = {}; sites = set(); rom = (self.out/'before-retail_rom').read_bytes()
        for key in ('view_list_caller_original','scene_caller_original','event_caller_original','other_caller_original'):
            for line in (self.out/('before-'+key)).read_text().splitlines():
                match = re.search(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',line)
                if not match: continue
                offset,entry,word = (int(v,16) for v in match.groups())
                if struct.unpack_from('>I',rom,offset)[0] != word: raise ValueError('Assembly comment differs from retail')
                words[entry] = word
                if re.search(r'\bjal\s+func_1501D348\b',line): sites.add(entry)
        self.assertEqual(sites,{call for _,call in windows})
        count = 0
        for start,call in windows:
            for parameter in (0,0x12345678,0x80000000,0xFFFFFFFF):
                memory,args,config = fixture(); m = CallerCut([words[a] for a in range(start,call+8,4)],
                    memory,args,config,[],entry=start)
                stack = m.r[29]; record = 0x65000
                for at,value in ((stack+0x30,3),(stack+0x34,37),(stack+0x40,6),
                        (record+0x18,6),(0x800C3C94,parameter)):
                    model.put(m.memory,at,value)
                model.put(m.memory,record,37,2); model.put(m.memory,0x800C3C90,3,1)
                m.r[2] = m.r[8] = record; m.r[3] = parameter
                m.r[4:8] = [37,6,0,0]
                if start == 0x150A1CD4: m.r[4] = 0x800C0000
                if start == 0x1501E988: m.r[6:8] = [1,0x800C0000]
                if start == 0x151DE9B4: m.r[4] = 0x800C0000
                if start == 0x151E8410: m.r[4:6] = [29,6]
                expected = (37,6,0,0,0)
                if start == 0x1509C658: expected = (37,6,0,3,parameter)
                if start == 0x1501E988: expected = (37,6,1,3,parameter)
                if start == 0x151DE9B4: expected = (37,1,0,0,0)
                if start == 0x151E8410: expected = (29,6,0,0,0)
                with self.assertRaises(CallBoundary): m.run()
                self.assertEqual(m.calls,[(source.ENTRY,expected)],hex(call)); count += 1
        self.receipt('connected-all-call-cuts',actual_assembly_sites=9,positive_packet_and_delay_cuts=count,
            pending_C_caller_also_executed_separately=True,prewindow_registers_explicit_fixtures=True,
            original_assembly_words_checked_against_ROM=True,not_full_assembly_caller_acceptance=True)


if __name__ == '__main__': unittest.main()
