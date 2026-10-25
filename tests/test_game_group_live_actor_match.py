"""Grouped live actor walk: native ABI, live providers, exact caller and image."""
from pathlib import Path
import hashlib
import itertools
import json
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch
from tools.experiments import game_group_live_actor_match as source
from tools import pad_c_object
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_record_callback_loop_match import put, get, public
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT = Path(__file__).resolve().parents[2]
ENTRY, COUNT, ROWS, ACTORS, HELPER = 0x150228E4, 0x800C3510, 0x800C3518, 0x800CC2D0, 0x15060F28
selected = source.SELECTED

def fixture(group, count, pattern, kind):
    m = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-1024, 512)}
    row = (ROWS + group * 25) & 0xffffffff
    for i in range(256):
        put(m, row + i, (kind + 17 * i) & 255, 1)
        put(m, ACTORS + i * 0x32c, (0, 1, 0x100, 0x80000000, 0xffffffff)[(i + pattern) % 5] if pattern != 5 else 1)
    put(m, COUNT + group, count, 1)
    return m

def mutate(m, group, actor, mode, number):
    if mode & 1:
        put(m, COUNT + group, 0, 1)
    elif mode & 2 and number == 1:
        put(m, COUNT + group, 25, 1)
    row = (ROWS + group * 25) & 0xffffffff
    if mode & 4:
        put(m, row + 1, 255, 1)
    if mode & 8:
        put(m, ACTORS + get(m, row + 1, 1) * 0x32c, 0)
    if mode & 16:
        put(m, actor, 0)

def reference(initial, group, mode):
    m, calls, index = dict(initial), [], 0
    while index < get(m, COUNT + group, 1):
        assert index < 256
        actor = ACTORS + get(m, ROWS + group * 25 + index, 1) * 0x32c
        if get(m, actor):
            calls.append((HELPER, (actor, 0)))
            mutate(m, group, actor, mode, len(calls))
        index += 1
    return public(m), calls

class Oracle(RayOracle):
    def __init__(self, words, memory, group, mode, phase, fault=None):
        self.group, self.mode, self.fault_at, self.own_accesses = group, mode, fault, 0
        self.in_root_instruction = False
        TimingOracle.__init__(self, words, memory, phase=phase, entry=ENTRY, arguments=(group,))
        self.group, self.mode = group, mode
        self.saved = tuple(self.r[16:24])
        self.saved_sp, self.saved_fp, self.saved_ra = self.r[29:32]

    def execute(self, word):
        self.dispatched_word = word
        self.in_root_instruction = True
        try:
            return super().execute(word)
        finally:
            self.in_root_instruction = False

    def access(self):
        if self.in_root_instruction:
            if self.own_accesses == self.fault_at:
                raise faults.AccessBoundary
            self.own_accesses += 1

    def record_call(self, target):
        assert target == HELPER
        args = self.arguments(2)
        assert args[1] == 0
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        assert target == HELPER
        mutate(self.memory, self.group, self.arguments(2)[0], self.mode, len(self.calls))
        for i in range(4):
            self.put(self.r[29] + 4 * i, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.hi, self.lo = 0x76543210, 0x89ABCDEF

class WindowBoundary(Exception):
    pass

class WindowCode(faults.TrackedCode):
    def __getitem__(self, pc):
        if pc == 0x1501EB84:
            raise WindowBoundary
        return super().__getitem__(pc)

class WindowOracle(Oracle):
    def __init__(self, window, words, memory, group, mode, phase):
        self.in_root_instruction = False
        TimingOracle.__init__(self, window, memory, phase=phase, entry=0x1501EB60,
            arguments=(0xdeadbeef,), connected={0x150228E4 + 4 * i: word for i, word in enumerate(words)})
        self.group, self.mode, self.fault_at, self.own_accesses = group, mode, None, 0
        self.r[11] = group
        self.caller_sp = self.r[29]
        put(self.memory, self.caller_sp + 0x28, group)
        self.code = WindowCode(self.code, self)
    def record_call(self, target):
        assert target in (0x150228E4, 0x15060F28, 0x150227BC)
        args = self.arguments(2 if target == 0x15060F28 else 1)
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))
    def hook(self, target):
        if target == 0x15060F28:
            mutate(self.memory, self.group, self.arguments(2)[0], self.mode,
                sum(target == 0x15060F28 for target, _ in self.calls))
            if self.mode & 64:
                put(self.memory, self.caller_sp + 0x28, self.group ^ 1)
        else:
            assert target == 0x150227BC
        for i in range(4):
            self.put(self.r[29] + 4 * i, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.hi, self.lo = 0x76543210, 0x89abcdef

class AliasTerminal(Exception):
    pass

class AliasOracle(Oracle):
    def execute(self, word):
        super().execute(word)
        if word == 0x27BD0030 and self.current_pc == 0x15022994:
            assert self.r[31] == 0xDEAD0000 and self.r[29] == self.before[29]
            # The deliberate count/saved-s0 overlap may corrupt saved s0.
            # Capture the executed return delay slot without calling that an
            # ABI-preserving input. Normal and caller tests keep their ABI gate.
            raise AliasTerminal

NATIVE_PREFIX = '#include <ultra64.h>\n#include "structs.h"\nu8 D_800C3510[2],D_800C3518[2][25];\nstruct127 D_800CC2D0[257];\nstatic u8 expectedCounts[2],expectedRows[2][25];\nstatic u32 expectedStates[257],expectedIDs[25],wanted,calls,error,mode,group;\ntypedef char ABI[(sizeof(void*)==4 && sizeof(struct127)==0x32C && __builtin_offsetof(struct127,interaction_state)==0)?1:-1];\nstatic void expected_mutation(u32 actor,u32 number){\n if(mode&1)expectedCounts[group]=0;else if((mode&2)&&number==1)expectedCounts[group]=25;\n if(mode&4)expectedRows[group][1]=255;\n if(mode&8)expectedStates[expectedRows[group][1]]=0;\n if(mode&16)expectedStates[actor]=0;\n}\nvoid func_15060F28(struct127 *actor,s32 flag){\n u32 id;\n if(calls>=wanted){error=1;return;}\n id=expectedIDs[calls++];\n if(actor!=&D_800CC2D0[id]||flag!=0){error=1;return;}\n if(mode&1)D_800C3510[group]=0;else if((mode&2)&&calls==1)D_800C3510[group]=25;\n if(mode&4)D_800C3518[group][1]=255;\n if(mode&8)D_800CC2D0[D_800C3518[group][1]].interaction_state=0;\n if(mode&16)actor->interaction_state=0;\n}\n'
NATIVE_SUFFIX = '\nstatic int one(u32 g,u32 count,u32 kind,u32 pattern,u32 mut){\n static const u32 states[]={0,1,0x100,0x80000000u,0xffffffffu};\n u32 i,j,actor,index;\n group=g;mode=mut;error=calls=wanted=0;\n for(i=0;i<257;i++){D_800CC2D0[i].interaction_state=(s32)(expectedStates[i]=states[(i+pattern)%5]);D_800CC2D0[i].id=0xA5;}\n for(i=0;i<2;i++){\n  D_800C3510[i]=expectedCounts[i]=(u8)count;\n  for(j=0;j<25;j++)D_800C3518[i][j]=expectedRows[i][j]=(u8)(kind+17*j);\n }\n index=0;\n while(index<expectedCounts[g]){\n  if(index>=25)return 25;\n  actor=expectedRows[g][index++];\n  if(expectedStates[actor]){if(wanted>=25)return 25;expectedIDs[wanted++]=actor;expected_mutation(actor,wanted);}\n }\n func_150228E4((s32)g);\n if(error||calls!=wanted)return 23;\n for(i=0;i<2;i++){\n  if(D_800C3510[i]!=expectedCounts[i])return 23;\n  for(j=0;j<25;j++)if(D_800C3518[i][j]!=expectedRows[i][j])return 23;\n }\n for(i=0;i<257;i++)if((u32)D_800CC2D0[i].interaction_state!=expectedStates[i]||D_800CC2D0[i].id!=0xA5)return 23;\n return 0;\n}\nint run(void){\n static const u32 counts[]={0,1,2,5,25},modes[]={0,1,2,4,8,16,12,31};\n u32 g,n,k,p,m;int result;\n for(g=0;g<2;g++)for(n=0;n<5;n++)for(k=0;k<256;k++)for(p=0;p<5;p++)for(m=0;m<8;m++){\n  result=one(g,counts[n],k,p,modes[m]);if(result)return result;\n }\n return 0;\n}\n'

def native_harness(body):
    return NATIVE_PREFIX + body + NATIVE_SUFFIX + START

class GroupLiveActorMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, cls.out = ROOT, ROOT / source.BUILD
        cls.pins = source.verify_prepared(cls.out)
        cls.values = source.snapshot(cls.out)
        cls.receipt = {}
        cls.truth = list(struct.unpack('>45I', cls.values['conker/conker.us.bin'][source.ROM:source.ROM + source.SIZE]))
        data, funcs = link_owner(ROOT, cls.out, cls.out / 'typed-after.o', source.OWNER)
        info = funcs[source.FUNCTION]
        cls.raw = list(struct.unpack('>45I', data[info['value']:info['value'] + 180]))
        data, funcs = link_owner(ROOT, cls.out, cls.out / 'typed-padded.o', source.OWNER)
        info = funcs[source.FUNCTION]
        cls.words = list(struct.unpack('>45I', data[info['value']:info['value'] + 180]))

    @classmethod
    def tearDownClass(cls):
        assert source.verify_prepared(cls.out) == cls.pins

    def _link_set(self, label, mapped, entry=ENTRY):
        link = self.out / (label + '.ld')
        link.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        spans = []
        for index, name in enumerate(('original', 'padded', 'after')):
            elf = self.out / (label + '-%d.elf' % index)
            obj = self.out / ('gnu-' + name + '.o')
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(link), '-e', source.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in mapped.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            data = sections(elf)['.text'][1]
            self.assertFalse(any(data[180:]))
            spans.append(list(struct.unpack('>45I', data[:180])))
        self.assertEqual(spans[0], spans[1])
        return spans

    def test_01_full_owner_derived_schedule_and_actual_generated_Make(self):
        self.assertEqual(self.words, self.truth)
        raw, bindings = source.payload(self.out / 'typed-after.o')
        normalized, rebound = source.normalized_payload(raw, bindings)
        self.assertEqual((normalized, rebound), source.payload(self.out / 'typed-original.o'))
        self.assertEqual(source.payload(self.out / 'typed-isolated.o'), (raw, bindings))
        self.assertEqual([4*i for i,(a,b) in enumerate(zip(self.raw,self.truth)) if a!=b], [0x30,0x38,0x50,0x54])
        self.assertEqual((-self.raw[0]) & 0xffff, 48)
        self.assertEqual(len(bindings), 7)
        q = json.loads((self.out / 'typed-qualification.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['guard_rows'],q['preserved_raw_neighbors']), (45,48,4,56))
        b = json.loads((self.out / 'boundary-qualification.json').read_text())
        self.assertEqual((b['actual_Make_commands'], b['normal_no_unroll_profile'], b['raw_and_padded_Make_equal']), (3,True,True))
        before = self.values['conker/retail_word_patches.us.csv']
        guards = (self.out / 'typed-proposed-guards.csv').read_bytes()
        self.assertTrue(guards.startswith(before))
        self.assertEqual(len(guards[len(before):].splitlines()), 4)
        self.assertEqual(source.digest((self.out / 'typed-proposed-owner.c').read_bytes()), '7475b4acd1e1984979c5de36359bf3568a3d3828bcb6433a39ad0ce5bacbc885')
        self.assertEqual(source.same_functions(self.out/'typed-before.o',self.out/'typed-after.o',(source.FUNCTION,)),56)
        self.assertEqual(source.normalized_pools(self.out/'typed-before.o'), source.normalized_pools(self.out/'typed-after.o'))
        self.assertEqual(source.same_functions(self.out/'before-padded.o',self.out/'typed-padded.o',(source.FUNCTION,)),56)
        self.assertEqual(source.normalized_pools(self.out/'before-padded.o'), source.normalized_pools(self.out/'typed-padded.o'))
        self.receipt.update(words=45,frame=48,bindings=7,guards=4,preserved_neighbors=56,actual_Make_commands=3)

    def test_02_guest_live_count_rows_and_all_instruction_paths(self):
        raw, guarded, retail = self.raw, self.words, self.truth
        vectors = [(k % 2, 1, k % 5, k, k % 32, phase) for k in range(256) for phase in (0, 8)]
        vectors += list(itertools.product((0, 1), (0, 1, 2, 5, 25), (0, 5), (0,), range(32), (0, 8)))
        vectors += list(itertools.product((0xffffffff, 0x7fffffff, 0x80000000, 0x10000), (0, 1, 2), (5,), (0,), (0, 1, 2, 4, 8, 16, 31), (0, 8)))
        vectors += list(itertools.product((0, 1), (128, 255), (5,), (0,), (1,), (0, 8)))
        visited = set()
        for group, count, pattern, kind, mode, phase in vectors:
            memory = fixture(group, count, pattern, kind)
            expected = reference(memory, group, mode)
            models = [Oracle(words, memory, group, mode, phase).run() for words in (retail, guarded, raw)]
            assert complete(models[0]) == complete(models[1]) == complete(models[2])
            actual_public = public(models[1].memory)
            assert (actual_public, models[1].calls) == expected, dict(
                vector=(group, count, pattern, kind, mode, phase), actual_calls=models[1].calls,
                expected_calls=expected[1], memory_differences=[(hex(a), actual_public.get(a), expected[0].get(a))
                    for a in sorted(set(actual_public) | set(expected[0])) if actual_public.get(a) != expected[0].get(a)][:16])
            visited.update(models[1].visits)
        assert len(visited) == 45, len(visited)
        self.receipt.update(guest_phases=len(vectors),guest_runs=len(vectors)*3,all_words_visited=len(visited))

    def test_03_SDK_native32_profiles_and_effective_negatives(self):
        o,r = self.out,ROOT
        controls = {
            'nonpositive_gate': selected.replace('interaction_state != 0', 'interaction_state > 0'),
            'masked_actor_index': selected.replace('[*cursor]', '[*cursor & 0x7F]'),
            'wrong_helper_flag': selected.replace('[*cursor], 0)', '[*cursor], 1)'),
            'next_actor_argument': selected.replace('func_15060F28(&D_800CC2D0[*cursor], 0)', 'func_15060F28(&D_800CC2D0[*cursor + 1], 0)'),
            'missing_gate': selected.replace('D_800CC2D0[*cursor].interaction_state != 0', '1'),
            'cached_count': selected.replace('    s32 index;', '    s32 index;\n    u8 count = D_800C3510[group];').replace('D_800C3510[group] > 0', 'count > 0').replace('index < D_800C3510[group]', 'index < count'),
        }
        native_rows = []
        for name, body, profile in [('selected', selected, opt) for opt in ('-O0', '-O2', '-O3')] + [(name, text, '-O2') for name, text in controls.items()]:
            assert name == 'selected' or body != selected
            path = o / ('private-native-' + name + profile + '.c')
            exe = path.with_suffix('.elf')
            path.write_text(native_harness(body))
            result = subprocess.run([*native_command(profile), str(path), '-o', str(exe)], cwd=r, capture_output=True, text=True, timeout=120)
            assert (result.returncode, result.stdout, result.stderr) == (0, '', ''), (name, result.stdout, result.stderr)
            result = subprocess.run([str(exe)], cwd=r, capture_output=True, timeout=120)
            assert result.returncode == (0 if name == 'selected' else 23), (name, profile, result.returncode, result.stderr)
            native_rows.append(dict(name=name, profile=profile, exit=result.returncode))
        self.receipt.update(native_profiles=native_rows,native_cases_per_profile=102400,trap_UBSan=True)

    def test_04_original_caller_and_actual_live_home_window(self):
        b = json.loads((self.out/'boundary-qualification.json').read_text())
        self.assertEqual(b['original_caller_words'],136)
        original, funcs = link_owner(ROOT,self.out,self.out/'actual-caller.o',source.OWNER)
        f=funcs['func_1501EA18']
        self.assertEqual((f['size'], original[f['value']:f['value']+544]), (544,self.values['conker/conker.us.bin'][0x4BEC8:0x4C0E8]))
        window=list(struct.unpack('>9I',self.values['conker/conker.us.bin'][0x4C010:0x4C034]))
        self.assertEqual((window[5],window[7]),(0x0D408A39,0x0D4089EF))
        count=0
        for group,total,mode,phase,mask in itertools.product((0,1,0xffffffff),(0,1,5),(0,1,31,64,65),(0,8),(0,1)):
            memory=fixture(group,total,5,0)
            put(memory,0x800C365A+group,mask,1)
            models=[WindowOracle(window,words,memory,group,mode,phase) for words in (self.truth,self.words,self.raw)]
            for model in models:
                with self.assertRaises(WindowBoundary):model.run()
                child=[(target,args) for target,args in model.calls if target==ENTRY]
                self.assertEqual(child,[] if mask else [(ENTRY,(group,))])
                changed=any(target==HELPER for target,_ in model.calls) and mode&64
                self.assertEqual(model.calls[-1],(0x150227BC,((group^1) if changed else group,)))
            self.assertEqual(complete(models[0]),complete(models[1]))
            self.assertEqual(complete(models[0]),complete(models[2]))
            count+=1
        self.assertEqual(count,180)
        self.receipt.update(caller_words=136,actual_window_words=9,actual_window_phases=count,caller_home_reload_observed=True)

    def test_05_literal_access_faults_and_deliberate_guest_aliases(self):
        guarded,retail=self.words,self.truth
        fault_cases = 0
        for group, count, pattern, kind, mode, phase in itertools.product((0, 1), (0, 1, 5), (5,), (0,), (0, 1, 31), (0, 8)):
            memory = fixture(group, count, pattern, kind)
            normal = Oracle(guarded, memory, group, mode, phase).run()
            for cut in range(normal.own_accesses):
                pair = [Oracle(words, memory, group, mode, phase, fault=cut) for words in (retail, guarded)]
                for model in pair:
                    try:
                        model.run()
                    except faults.AccessBoundary:
                        pass
                    else:
                        raise AssertionError(('Unfired own-access boundary', cut))
                    assert model.own_accesses == cut
                assert complete(pair[0]) == complete(pair[1])
                assert (pair[0].current_pc, pair[0].dispatched_word, pair[0].delay_of) == (pair[1].current_pc, pair[1].dispatched_word, pair[1].delay_of)
                fault_cases += 1
        aliases=(
            ('actor-incoming-home',dict(D_800CC2D0=STACK)),
            ('actor-saved-s0',dict(D_800CC2D0=STACK-48+24)),
            ('actor-saved-ra',dict(D_800CC2D0=STACK-48+44)),
            ('row-saved-s0',dict(D_800C3518=STACK-48+24)),
            ('count-incoming-home',dict(D_800C3510=STACK+0x28)),
            ('count-saved-s0',dict(D_800C3510=STACK-48+24)),
            ('actor-count',dict(D_800CC2D0=COUNT)))
        count=0
        symbols=dict(D_800C3510=COUNT,D_800C3518=ROWS,D_800CC2D0=ACTORS,func_15060F28=HELPER)
        for label,changes in aliases:
            mapped=dict(symbols,**changes)
            spans=self._link_set('alias-'+label,mapped)
            with patch.multiple(sys.modules[__name__],COUNT=mapped['D_800C3510'],ROWS=mapped['D_800C3518'],ACTORS=mapped['D_800CC2D0']):
                for phase,mode in itertools.product((0,8),(0,1)):
                    memory=fixture(0,1,5,0)
                    models=[AliasOracle(words,memory,0,mode,phase) for words in spans]
                    for model in models:
                        with self.assertRaises(AliasTerminal):model.run()
                    self.assertEqual(complete(models[0]),complete(models[1]))
                    self.assertEqual(complete(models[0]),complete(models[2]))
                    count+=1
        self.assertEqual((fault_cases,count),(588,28))
        self.receipt.update(fired_access_prefixes=fault_cases,guest_alias_phases=count,delay_slot_metadata_compared=True,
            intentional_saved_slot_corruption_not_ABI_preservation=True,portable_C_fault_claim=False)

    def test_06_GNU_rebases_execution_and_corruption_controls(self):
        raw_obj=self.out/'typed-after.o'
        raw,raw_bindings=source.payload(raw_obj)
        for at in range(45):
            damaged=bytearray(raw);damaged[at*4+3]^=1
            with self.assertRaises(ValueError):source.normalized_payload(damaged,raw_bindings)
        binding_controls=0
        for at,values in raw_bindings.items():
            for variant in ([('R_MIPS_NONE',values[0][1])],[(values[0][0],'D_800C3511')]):
                damaged=dict(raw_bindings);damaged[at]=variant
                with self.assertRaises(ValueError):source.normalized_payload(raw,damaged)
                binding_controls+=1
        f=source.parse_object(raw_obj)[1][source.FUNCTION]
        o,r=self.out,ROOT
        data = raw_obj.read_bytes()
        header = struct.unpack_from('>16sHHIIIIIHHHHHH', data)
        shoff, entsize, count, strings_index = header[6], header[11], header[12], header[13]
        rows = [struct.unpack_from('>10I', data, shoff + i * entsize) for i in range(count)]
        strings = data[rows[strings_index][4]:rows[strings_index][4] + rows[strings_index][5]]
        named = {strings[row[0]:].split(b'\0', 1)[0].decode(): row for row in rows}
        guard_controls = 0
        for at in (0x30, 0x38, 0x50, 0x54):
            damaged = bytearray(data)
            damaged[named['.text'][4] + f['value'] + at + 3] ^= 1
            path = o / ('corrupt-guard-%x.o' % at)
            path.write_bytes(damaged)
            self.assertRaises(ValueError, lambda: pad_c_object.emit_padded_assembly(path, r / 'conker/retail_layout.us.txt', 'generated_49D30', word_patches_path=o / 'typed-proposed-guards.csv'))
            guard_controls += 1
        rel = named['.rel.text']
        target = next(at for at in range(rel[4], rel[4] + rel[5], 8) if struct.unpack_from('>I', data, at)[0] == f['value'] + 0x54)
        info = struct.unpack_from('>I', data, target + 4)[0]
        assert info & 255 == 6
        for label, replacement in (('kind', (info & ~255) | 5), ('symbol', info ^ 256)):
            damaged = bytearray(data)
            struct.pack_into('>I', damaged, target + 4, replacement)
            path = o / ('corrupt-guard-relocation-' + label + '.o')
            path.write_bytes(damaged)
            self.assertRaises(ValueError, lambda: pad_c_object.emit_padded_assembly(path, r / 'conker/retail_layout.us.txt', 'generated_49D30', word_patches_path=o / 'typed-proposed-guards.csv'))
            guard_controls += 1

        rows=json.loads((self.out/'boundary-qualification.json').read_text())['independent_GNU_rebases']
        count=0
        for index,row in enumerate(rows):
            mapped=row['symbols'];entry=row['entry']
            spans=self._link_set('fresh-rebase-%d'%index,mapped,entry)
            self.assertEqual(source.digest(struct.pack('>45I',*spans[0])),row['SHA256'])
            with patch.multiple(sys.modules[__name__],ENTRY=entry,COUNT=mapped['D_800C3510'],ROWS=mapped['D_800C3518'],ACTORS=mapped['D_800CC2D0'],HELPER=mapped['func_15060F28']):
                for total,mode,phase in itertools.product((0,1,5),(0,1,2,31),(0,8)):
                    group=index%2;memory=fixture(group,total,5,0x80)
                    expected=reference(memory,group,mode)
                    models=[Oracle(words,memory,group,mode,phase).run() for words in spans]
                    self.assertEqual(complete(models[0]),complete(models[1]))
                    self.assertEqual(complete(models[0]),complete(models[2]))
                    self.assertEqual((public(models[1].memory),models[1].calls),expected)
                    count+=1
        self.assertEqual((len(rows),count,binding_controls,guard_controls),(9,216,14,6))
        self.receipt.update(GNU_rebases=9,rebased_guest_phases=count,rebased_guest_runs=count*3,
            raw_word_controls=45,raw_binding_controls=binding_controls,actual_padder_controls=guard_controls)

    def test_07_strict_image_and_installed_input_negatives(self):
        values=self.values
        before=values['conker/build/conker.us.elf'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+180]
        predicted=source.predicted_image(before,truth)
        self.assertEqual((self.out/'first-linked.elf').read_bytes(),predicted)
        self.assertEqual((source.digest(predicted),sum(a!=b for a,b in zip(before,predicted))),('08f3110edeb2864ff15ffb896bbfb76573dcd62bcfcb31bf569af0e3511a5820',144))
        for at in (0,len(predicted)-1,source.elf_slot_offset(before,ENTRY,180),source.elf_slot_offset(before,ENTRY,180)+179):
            bad=bytearray(predicted);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        with self.assertRaises(ValueError):source.check_image(before,predicted+b'\0',truth)
        actual={name:(ROOT/name).read_bytes() for name in source.INPUTS}
        installed=actual[source.SOURCE]!=values[source.SOURCE]
        source.check_input_map(values,actual,self.out,installed)
        accepted=source.expected_inputs(values,self.out,True)
        source.check_input_map(values,accepted,self.out,True)
        names=(source.SOURCE,source.OBJECT,'conker/build/conker.us.elf','conker/retail_word_patches.us.csv',
            'conker/Makefile','conker/progress.csv','conker/retail_layout.us.txt',source.ASM,
            'conker/include/structs.h','conker/include/functions.h','conker/src/game_83300.c','conker/symbol_addrs.us.txt')
        for name in names:
            bad=dict(accepted);data=bytearray(bad[name]);data[0]^=1;bad[name]=bytes(data)
            with self.assertRaises(ValueError):source.check_input_map(values,bad,self.out,True)
        stale=dict(accepted);stale[source.OBJECT]=values[source.OBJECT]
        with self.assertRaises(ValueError):source.check_input_map(values,stale,self.out,True)
        audit=source.audit(ROOT,self.out)
        self.assertEqual((audit['functions'],audit['metadata_exclusions']),(6055,0))
        self.receipt.update(strict_image_bytes=144,strict_image_negatives=5,installed_input_negatives=12,
            valid_installed_map=True,stale_object_rejected=True,linked_audit=audit)

    def test_08_actual_old_placeholder_is_effectively_wrong(self):
        data,funcs=link_owner(ROOT,self.out,self.out/'typed-before.o',source.OWNER)
        f=funcs[source.FUNCTION]
        self.assertEqual(f['size'],12)
        old=list(struct.unpack('>3I',data[f['value']:f['value']+12]))
        memory=fixture(0,1,5,0)
        model=Oracle(old,memory,0,0,0).run()
        expected=reference(memory,0,0)
        self.assertNotEqual((public(model.memory),model.calls),expected)
        self.assertEqual(model.calls,[])
        self.assertEqual(len(expected[1]),1)
        self.receipt.update(old_target_words=3,old_target_effectively_rejected=True)

if __name__=='__main__':
    unittest.main()
