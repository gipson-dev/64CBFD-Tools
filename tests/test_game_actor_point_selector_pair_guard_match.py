"""Paired actor-point selectors: semantics, guards, callers, owner and image."""

import csv
import itertools
from pathlib import Path
import struct
import subprocess
import unittest

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_actor_point_selector_pair_guard_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset, same_functions, symbol_rows)
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import game_actor_point_interval_oracle as base
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]


def assemble(source, output):
    subprocess.run([
        "mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(ROOT / "conker/include"), "-o", str(output),
        str(source)], check=True, capture_output=True)


def linked(obj, name, label, entry=None, symbols=None):
    symbols = match.SYMBOLS if symbols is None else symbols
    entry = match.TARGETS[name]["entry"] if entry is None else entry
    text, functions, relocations = parse_object(obj)
    source, unknown = emit_function(text, functions[name], relocations, name, symbols)
    if unknown:
        raise ValueError("Unknown selector bindings: %r" % (unknown,))
    prefix = ROOT / match.BUILD / label
    prefix.with_suffix(".s").write_text(source)
    prefix.with_suffix(".ld").write_text(
        "SECTIONS { .text 0x%X : { *(.text) } }\n" % entry +
        "\n".join("%s = 0x%X;" % item for item in symbols.items()) + "\n")
    assemble(prefix.with_suffix(".s"), prefix.with_suffix(".o"))
    subprocess.run([
        "mips-linux-gnu-ld", "-m", "elf32btsmip", "-T",
        str(prefix.with_suffix(".ld")), "-e", name, "-o",
        str(prefix.with_suffix(".elf")), str(prefix.with_suffix(".o"))],
        check=True, capture_output=True)
    size = functions[name]["size"]
    return list(struct.unpack(">%dI" % (size // 4),
                              sections(prefix.with_suffix(".elf"))[".text"][1][:size]))


def home(case):
    return base.STACK + case.phase if case.child_home is None else case.child_home


def resolver_effect(memory, case, position, index):
    for offset in range(3):
        value = base.legacy.VALUES[(case.pattern + offset + index) %
                                   len(base.legacy.VALUES)]
        base.put(memory, position + offset * 4, value)
    if case.private & 1:
        base.put(memory, home(case) + 4, base.OTHER)
        base.put(memory, home(case) + 8, base.ALT_RESULT)


def reference(initial, case, spec, symbols=match.SYMBOLS):
    memory = dict(initial)
    position = base.position(case)
    result = base.result(case)
    mode = case.fourth & 0xFF
    index = {4: spec["point4"], 5: spec["point5"], 6: 0xC}.get(mode, 0x10)
    calls = [(symbols["func_15142314"],
              (base.read(memory, base.ACTOR + 0x1D4), index, position))]
    resolver_effect(memory, case, position, index)
    if case.private & 1:
        result = base.read(memory, home(case) + 8)
    if not result:
        return memory, calls, [], 1
    start = home(case) - 12
    base.put(memory, start, base.read(memory, position))
    base.put(memory, start + 4,
             base.bits(base.floating(base.read(memory, position + 4)) + 10.0))
    base.put(memory, start + 8, base.read(memory, position + 8))
    actor = base.read(memory, home(case) + 4) if case.private & 1 else base.ACTOR
    calls.append((symbols["func_1504715C"], (result, actor)))
    base.initialize_effect(memory, case, result, position)
    if case.private & 3:
        result = base.read(memory, home(case) + 8)
    lower = base.bits(base.floating(base.read(memory, position + 4)) - 50.0)
    calls.append((symbols["func_15046C80"], (start, 0, lower, result)))
    packet = [tuple(base.read(memory, start + offset * 4) for offset in range(3))]
    base.legacy.query_effect(memory, case, result, position)
    return memory, calls, packet, case.returned & 0xFFFFFFFF


class PairOracle(base.legacy.HeightOracle):
    def __init__(self, words, memory, case, name, symbols=match.SYMBOLS,
                 entry=None):
        self.name = name
        self.spec = match.TARGETS[name]
        self.syms = symbols
        entry = self.spec["entry"] if entry is None else entry
        super().__init__(
            words, memory, case, entry=entry,
            initialize=symbols["func_1504715C"],
            query=symbols["func_15046C80"], connected=None,
            arguments=(base.position(case), base.ACTOR, base.result(case),
                       case.fourth))

    def record_call(self, target):
        if target == self.syms["func_15142314"]:
            args = tuple(self.arguments(3))
            self.calls.append((target, args))
            self.events.append(("CALL", target, args))
        else:
            super().record_call(target)

    def hook(self, target):
        case = self.case
        args = self.calls[-1][1]
        position = base.position(case)
        if target == self.syms["func_15142314"]:
            resolver_effect(self.memory, case, args[2], args[1])
            value = 0x12345678
        elif target == self.initialize:
            base.initialize_effect(self.memory, case, args[0], position)
            value = 0x76543210
        else:
            if target != self.query:
                raise AssertionError(hex(target))
            base.legacy.query_effect(self.memory, case, args[3], position)
            value = case.returned & 0xFFFFFFFF
        for offset in range(4):
            self.put(self.r[29] + offset * 4, 0xB5000000 + offset, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.r[2] = value
        self.f[:20] = [0xA5000000 + value for value in range(20)]
        self.hi, self.lo = 0xA5000010, 0xA5000011


def state(machine):
    return (machine.r, machine.f, machine.memory, machine.calls, machine.events,
            machine.trace, machine.hi, machine.lo, machine.packets)


def native_source():
    declarations = "#include <ultra64.h>\n" + match.DECLARATIONS
    selected = [match.selected_body(name) for name in match.TARGETS]
    variants = []
    controls = (
        ("point4", "index = 0x17", "index = 0x18"),
        ("point5", "index = 0x14", "index = 0x15"),
        ("point6", "index = 0xC", "index = 0xB"),
        ("upper", "position[1] + 10.0f", "position[1] + 9.0f"),
        ("lower", "position[1] - 50.0f", "position[1] - 49.0f"),
        ("selector", "func_15046C80(start, 0,", "func_15046C80(start, 1,"),
    )
    for label, old, new in controls:
        body = selected[0]
        if old not in body:
            raise ValueError("Native selector mutation became ineffective: " + label)
        variants.append(body.replace("func_150BE9B0", "bad_" + label, 1)
                        .replace(old, new, 1))
    support = r'''
typedef s32 (*SelectorFn)(f32 *, u8 *, HeightResult71820 *, u8);
static u8 actor[0x300], result[0x40]; static f32 position[3];
static u32 current_mode, current_pair, mutation, returned, calls, error, cases;
static u32 bits(f32 value) { union { f32 f; u32 u; } item; item.f=value; return item.u; }
static s32 wanted_index(void) {
    if (current_mode == 4) return current_pair ? 0x19 : 0x17;
    if (current_mode == 5) return current_pair ? 0x16 : 0x14;
    if (current_mode == 6) return 0xC;
    return 0x10;
}
void func_15142314(u8 *matrix, s32 index, f32 *output) {
    if (matrix != (u8 *)0x12345678 || index != wanted_index() ||
        output != position || calls++ != 0) error = 1;
    output[0] = 2.0f; output[1] = 20.0f; output[2] = -3.0f;
}
void func_1504715C(HeightResult71820 *output, HeightActor71820 *input) {
    u32 i; if ((u8 *)output != result || (u8 *)input != actor || calls++ != 1) error=1;
    for (i=0;i<0x40;i++) result[i]=(u8)(i*7+3); if (mutation) position[1]=30.0f;
}
s32 func_15046C80(f32 *start, u16 selector, f32 lower, HeightResult71820 *output) {
    if (calls++ != 2 || selector || (u8 *)output != result ||
        bits(start[0]) != bits(2.0f) || bits(start[1]) != bits(30.0f) ||
        bits(start[2]) != bits(-3.0f) ||
        bits(lower) != bits((mutation ? 30.0f : 20.0f)-50.0f)) error=1;
    return (s32)returned;
}
static int corpus(SelectorFn fn, u32 pair) {
    u32 mode, query, m, answer; current_pair=pair;
    for (mode=0;mode<256;mode++) for (query=0;query<2;query++) for (m=0;m<2;m++) {
        current_mode=mode; mutation=m; returned=(mode&1)?0xFFFFFFFFu:0x12345678u;
        *(u32 *)(actor+0x1D4)=0x12345678u; calls=error=0;
        answer=(u32)fn(position,actor,query?(HeightResult71820 *)result:0,(u8)mode); cases++;
        if (error || calls!=(query?3u:1u) || answer!=(query?returned:1u)) return 1;
    } return 0;
}
static int run(void) {
    u32 i; SelectorFn bad[] = { BAD_LIST }; cases=0;
    if (corpus(func_150BE9B0,0) || corpus(func_150BEC30,1)) return 90;
    if (cases != 2048) return 91;
    for (i=0;i<sizeof(bad)/sizeof(bad[0]);i++) if (!corpus(bad[i],0)) return 92;
    return 0;
}
'''.replace("BAD_LIST", ",".join("bad_" + item[0] for item in controls))
    return declarations + "\n".join(selected + variants) + support + \
        START.replace("void _start(void)",
                      "__attribute__((force_align_arg_pointer)) void _start(void)")


class ActorPointSelectorPairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / match.BUILD
        cls.output.mkdir(parents=True, exist_ok=True)
        cls.compact = match.compile_candidate(ROOT, cls.output)
        cls.rows = match.all_rows(ROOT, cls.compact)
        cls.current_guards = ROOT / "conker/retail_word_patches.us.csv"
        with cls.current_guards.open(newline="") as stream:
            installed = [row for row in csv.DictReader(stream)
                         if row["function"] in match.TARGETS]
        cls.installed = bool(installed)
        if installed and installed != cls.rows:
            raise ValueError("Installed actor point selector guards differ")
        combined = cls.current_guards.read_bytes()
        if not installed:
            combined += match.suffix_bytes(cls.rows)
        cls.combined = cls.output / "qualified-guards.csv"
        cls.combined.write_bytes(combined)
        cls.guarded = {}
        for name, spec in match.TARGETS.items():
            text, functions, relocations = parse_object(cls.compact)
            info = functions[name]
            lines = [".section .text", ".balign 4", ".globl " + name,
                     ".type " + name + ", @function", name + ":"]
            for offset in range(info["value"], info["value"] + info["size"], 4):
                for kind, symbol in relocations.get(offset, ()):
                    lines.append(".reloc ., %s, %s" % (kind, symbol))
                lines.append(".word 0x%08X" % struct.unpack_from(">I", text, offset)[0])
            lines.append(".size %s, . - %s" % (name, name))
            isolated = cls.output / (name + "-raw.o")
            source = cls.output / (name + "-raw.s")
            source.write_text("\n".join(lines) + "\n")
            assemble(source, isolated)
            layout = cls.output / (name + "-layout.s")
            layout.write_text("glabel " + name + "\n" + "".join(
                "/* %06X %08X 00000000 */ nop\n" %
                (spec["rom"] + index * 4, spec["entry"] + index * 4)
                for index in range(match.WORDS)))
            isolated_rows = cls.output / (name + "-guards.csv")
            match.write_rows(isolated_rows, match.guard_rows(ROOT, cls.compact, name))
            guarded_source = cls.output / (name + "-guarded.s")
            guarded_source.write_text(emit_padded_assembly(
                isolated, layout, word_patches_path=isolated_rows,
                filename=match.FILENAME))
            guarded = cls.output / (name + "-guarded.o")
            assemble(guarded_source, guarded)
            cls.guarded[name] = guarded
        owner_source = cls.output / "qualified-owner.s"
        owner_source.write_text(emit_padded_assembly(
            cls.compact, ROOT / match.ASM, word_patches_path=cls.combined,
            filename=match.FILENAME))
        cls.owner = cls.output / "qualified-owner.o"
        assemble(owner_source, cls.owner)
        linker = (ROOT / "conker/build/conker.ld").read_text()
        old = match.OBJECT.replace("conker/", "")
        new = str(cls.owner.relative_to(ROOT / "conker")).replace("\\", "/")
        if linker.count(old) != 1:
            raise ValueError("Actor point selector owner linker reference changed")
        script = cls.output / "qualified-image.ld"
        script.write_text(linker.replace(old, new))
        cls.elf = cls.output / "qualified-image.elf"
        subprocess.run([
            "mips-linux-gnu-ld", "-T", str(script.relative_to(ROOT / "conker")),
            "-Map", str((cls.output / "qualified-image.map").relative_to(ROOT / "conker")),
            "-T", "undefined_syms.us.txt", "-T", "undefined_funcs.us.txt",
            "-T", "undefined_syms_auto.txt", "-T", "undefined_funcs_auto.txt",
            "--no-check-sections", "--no-warn-mismatch", "-o",
            str(cls.elf.relative_to(ROOT / "conker"))], cwd=ROOT / "conker",
            check=True, capture_output=True)

    def test_01_guarded_words_relocations_and_fail_closed_rows(self):
        self.assertEqual((len(self.rows), sum(bool(row["insert_after"])
                                             for row in self.rows)), (34, 2))
        rom = (ROOT / "conker/conker.us.bin").read_bytes()
        failures = 0
        for name, spec in match.TARGETS.items():
            retail = list(struct.unpack_from(">%dI" % match.WORDS, rom, spec["rom"]))
            guarded = linked(self.guarded[name], name, name + "-linked-guarded")
            self.assertEqual(guarded, retail)
            self.assertEqual(len(linked(self.compact, name, name + "-linked-raw")),
                             match.RAW_WORDS)
            rows = match.guard_rows(ROOT, self.compact, name)
            for index, row in enumerate(rows):
                for field, value in (("expected", "0x%08X" %
                                      (int(row["expected"], 0) ^ 1)),
                                     ("expected_relocations", "R_MIPS_26:wrong")):
                    changed = [dict(item) for item in rows]
                    changed[index][field] = value
                    path = self.output / ("stale-%s-%02d-%s.csv" %
                                          (name, index, field))
                    match.write_rows(path, changed)
                    with self.assertRaisesRegex(ValueError,
                                                "stale word patch|stale relocations"):
                        emit_padded_assembly(
                            self.output / (name + "-raw.o"),
                            self.output / (name + "-layout.s"),
                            word_patches_path=path, filename=match.FILENAME)
                    failures += 1
        self.assertEqual(failures, 68)

    def test_02_guest_semantics_aliases_and_rebases(self):
        rom = (ROOT / "conker/conker.us.bin").read_bytes()
        total = 0
        for name, spec in match.TARGETS.items():
            programs = [
                list(struct.unpack_from(">%dI" % match.WORDS, rom, spec["rom"])),
                linked(self.compact, name, name + "-guest-raw"),
                linked(self.guarded[name], name, name + "-guest-guarded"),
            ]
            cases = [base.Case(fourth=0xABCD0000 | mode, query=query,
                               mode=mutation, returned=(0, 1, 0xFFFFFFFF,
                                                        0x80000000)[mutation],
                               pattern=(mode + mutation) % 12, phase=phase)
                     for mode, query, mutation, phase in itertools.product(
                         range(256), (False, True), range(4), (0, 8))]
            cases += [base.Case(fourth=mode, query=True, position_layout=layout,
                                result_layout=result_layout, private=private,
                                pattern=layout + result_layout)
                      for mode, layout, result_layout, private in itertools.product(
                          (4, 5, 6, 7, 255), range(6), range(4), range(4))]
            visited = set()
            for case in cases:
                initial = base.fixture(case)
                want, calls, packets, value = reference(initial, case, spec)
                machines = []
                for words in programs:
                    machine = PairOracle(words, initial, case, name).run()
                    self.assertEqual((base.visible(machine.memory, case), machine.calls,
                                      machine.packets, machine.r[2]),
                                     (base.visible(want, case), calls, packets, value))
                    machines.append(machine)
                self.assertEqual(state(machines[0]), state(machines[1]))
                self.assertEqual(state(machines[0]), state(machines[2]))
                visited.update(machines[0].visits)
            self.assertEqual(
                set(range(spec["entry"], spec["entry"] + match.WORDS * 4, 4)) -
                visited, {spec["entry"] + 0x90})
            for layout, (entry, symbols) in enumerate((
                    (0x15001000, dict(func_15142314=0x10007FF0,
                                      func_1504715C=0x10008000,
                                      func_15046C80=0x1000FFF0)),
                    (0x1F008000, dict(func_15142314=0x1F108000,
                                      func_1504715C=0x1000FFF0,
                                      func_15046C80=0x10008000)))):
                rebased = [
                    linked(self.compact, name,
                           "%s-rebase-%d-raw" % (name, layout), entry, symbols),
                    linked(self.guarded[name], name,
                           "%s-rebase-%d-guarded" % (name, layout), entry, symbols),
                ]
                for mode, query, mutation in itertools.product(
                        (0, 4, 5, 6, 7, 255), (False, True), (0, 3)):
                    case = base.Case(fourth=mode, query=query, mode=mutation,
                                     returned=0xFFFFFFFF, pattern=mutation * 3)
                    initial = base.fixture(case)
                    want, calls, packets, value = reference(
                        initial, case, spec, symbols)
                    machines = [PairOracle(words, initial, case, name, symbols,
                                           entry).run() for words in rebased]
                    for machine in machines:
                        self.assertEqual(
                            (base.visible(machine.memory, case), machine.calls,
                             machine.packets, machine.r[2]),
                            (base.visible(want, case), calls, packets, value))
                    self.assertEqual(state(machines[0]), state(machines[1]))
            total += len(cases)
        self.assertEqual(total, 9152)

    def test_03_native32_semantics_and_six_effective_controls(self):
        source = self.output / "native.c"
        source.write_text(native_source())
        for option in ("-O0", "-O2", "-O3"):
            executable = self.output / ("native" + option)
            build = subprocess.run(native_command(option) + [
                "-fno-strict-aliasing", "-mstackrealign", str(source), "-o",
                str(executable)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(executable)], capture_output=True)
            self.assertEqual(run.returncode, 0, (option, run.returncode, run.stderr))

    def test_04_callers_owner_allocated_image_and_protected_data(self):
        rom = (ROOT / "conker/conker.us.bin").read_bytes()
        for name, spec in match.TARGETS.items():
            jal = 0x0C000000 | (spec["entry"] >> 2 & 0x03FFFFFF)
            locations = [offset for offset in range(0, len(rom) - 3, 4)
                         if struct.unpack_from(">I", rom, offset)[0] == jal]
            self.assertEqual(locations, [spec["call_rom"]])
            self.assertEqual(struct.unpack_from(">2I", rom, spec["call_rom"] - 4),
                             (0x27A60028, 0x0C000000 |
                              (spec["entry"] >> 2 & 0x03FFFFFF)))
            self.assertEqual(struct.unpack_from(">I", rom, spec["call_rom"] + 4)[0],
                             0xAFA70024)
        production = ROOT / match.OBJECT
        self.assertGreaterEqual(same_functions(production, self.owner,
                                               tuple(match.TARGETS)), 5)
        self.assertEqual(normalized_pools(production), normalized_pools(self.owner))
        for name, spec in match.TARGETS.items():
            at = elf_slot_offset(self.elf.read_bytes(), spec["entry"],
                                 match.WORDS * 4)
            self.assertEqual(self.elf.read_bytes()[at:at + match.WORDS * 4],
                             rom[spec["rom"]:spec["rom"] + match.WORDS * 4])
        before = ROOT / "conker/build/conker.us.elf"
        old_functions, _, old_addresses = load_elf_functions(
            str(before), "mips-linux-gnu-objdump")
        new_functions, _, new_addresses = load_elf_functions(
            str(self.elf), "mips-linux-gnu-objdump")
        self.assertEqual((old_functions.keys(), old_addresses),
                         (new_functions.keys(), new_addresses))
        changed = [name for name in old_functions
                   if old_functions[name] != new_functions[name]]
        if self.installed:
            self.assertEqual(changed, [])
        else:
            self.assertEqual(set(changed), set(match.TARGETS))
        old_symbols = {(name, fields[1], fields[3], fields[4], fields[5])
                       for _, name, fields, _ in symbol_rows(before.read_bytes())}
        new_symbols = {(name, fields[1], fields[3], fields[4], fields[5])
                       for _, name, fields, _ in symbol_rows(self.elf.read_bytes())}
        self.assertEqual(old_symbols, new_symbols)
        report = audit_layout(self.elf, ROOT / "conker")
        self.assertEqual((report["exact"], report["bytes"], report["owner_count"],
                          report["different_bytes"]), (True, 189088, 720, 0))


if __name__ == "__main__":
    unittest.main()
