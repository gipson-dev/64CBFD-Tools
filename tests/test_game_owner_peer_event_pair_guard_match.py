"""Paired owner identity events: ABI, semantics, guards, parent and image."""

from dataclasses import dataclass
import csv
import itertools
from pathlib import Path
import struct
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.check_game_data_layout import audit_layout
from tools.experiments import game_owner_peer_event_pair_guard_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import (
    elf_slot_offset, same_functions, symbol_rows)
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]
OWNER, EVENT = 0x30000, 0x20000
RELEASE = 0x1516972C
PARENT, PARENT_ROM, PARENT_WORDS = 0x151604A0, 0x18D950, 88
REGISTRY, REGISTRY_ROM, REGISTRY_WORDS = 0x8008B150, 0x22FC10, 41
TABLES = {
    "func_15163FEC": (0x8008B374, (0, 0x151640C0)),
    "func_15164134": (0x8008B37C, (0, 0x151643A8, 0, 0, 0)),
}
VALUES = (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0x12345678)


@dataclass(frozen=True)
class Case:
    kind: int = 0
    pattern: int = 0
    relation: int = 0
    selector: int = 0
    alias: int = 0
    phase: int = 0
    mutate: bool = False


def addresses(case):
    choices = (
        (OWNER, EVENT),
        (EVENT - 0x18, EVENT),
        (EVENT - 0x14, EVENT),
        (OWNER, OWNER + 0x18),
        (OWNER, STACK + case.phase + 8),
        (STACK + case.phase - 0x10, EVENT),
    )
    return choices[case.alias]


def fixture(case, name, registry=True):
    owner, event = addresses(case)
    memory = {STACK + offset: (offset * 17 + 0xA5) & 0xFF
              for offset in range(-2048, 512)}
    for base, size in ((owner - 32, 0x100), (event - 32, 128)):
        memory.update({base + offset: (offset * 13 + 0x5A) & 0xFF
                       for offset in range(size)})
    first = VALUES[case.pattern % len(VALUES)]
    second = VALUES[(case.pattern + 1) % len(VALUES)]
    put(memory, event, first)
    put(memory, event + 4, second)
    memory[event + 8], memory[event + 9] = 17, 231
    current = (first, second, 0xBEEFF00D)[case.relation % 3]
    put(memory, owner + 0x18, current)
    memory[owner + 0x1C] = (memory[event + 4] if case.relation == 3
                            else (17, 231, 0x7F, 0x80)[case.pattern % 4])
    spec = match.TARGETS[name]
    memory[owner + spec["selector"]] = case.selector
    memory[owner + 0x12] = spec["registry_index"]
    table, entries = TABLES[name]
    for index, target in enumerate(entries):
        put(memory, table + index * 4, target)
    if registry:
        for index in range(REGISTRY_WORDS):
            put(memory, REGISTRY + index * 4, 0)
        put(memory, REGISTRY + spec["registry_index"] * 4, spec["entry"])
    return memory


def reference(initial, case, name, incoming_sp=None, symbols=None):
    owner, event = addresses(case)
    memory = dict(initial)
    calls = []
    sp = STACK + case.phase if incoming_sp is None else incoming_sp
    put(memory, sp + 8, case.kind)
    kind = case.kind & 0xFF
    state = owner + 0x18
    if kind == 0:
        first = read(memory, event)
        current = read(memory, state)
        if first == current or memory[event + 4] == memory[state + 4]:
            release = RELEASE if symbols is None else symbols["func_1516972C"]
            calls.append((release, (owner,)))
            if case.mutate:
                put(memory, state, 0xCAFEBABE)
                memory[state + 4] = 0xA5
            for index in range(4):
                put(memory, sp - 0x18 + index * 4, 0xB5000000 + index)
    elif kind == 0x2D:
        current = read(memory, state)
        first = read(memory, event)
        if first == current:
            put(memory, state, read(memory, event + 4))
            memory[state + 4] = memory[event + 9]
        elif read(memory, event + 4) == current:
            put(memory, state, first)
            memory[state + 4] = memory[event + 8]
    else:
        table, entries = TABLES[name]
        selector = memory[owner + match.TARGETS[name]["selector"]]
        target = entries[selector]
        if target:
            calls.append((target, (owner, event, kind)))
            put(memory, owner + 0x34, target ^ kind)
            for index in range(4):
                put(memory, sp - 0x18 + index * 4, 0xB5000000 + index)
    return memory, calls


def visible(memory, case):
    owner, event = addresses(case)
    relevant = {}
    for address, value in memory.items():
        if (owner <= address < owner + 0x40 or
                event <= address < event + 12 or
                any(base <= address < base + len(entries) * 4
                    for base, entries in TABLES.values()) or
                REGISTRY <= address < REGISTRY + REGISTRY_WORDS * 4):
            relevant[address] = value
    return relevant


class PairOracle(RayOracle):
    def __init__(self, words, memory, case, name, entry=None, connected=None,
                 symbols=None):
        self.event_case, self.name = case, name
        self.owner_address, self.event_address = addresses(case)
        self.target_symbols = match.SYMBOLS if symbols is None else symbols
        entry = match.TARGETS[name]["entry"] if entry is None else entry
        TimingOracle.__init__(
            self, words, memory, phase=case.phase, entry=entry,
            arguments=(self.owner_address, self.event_address, case.kind),
            connected=connected)
        self.hi, self.lo, self.condition = 0x89ABCDEF, 0x76543210, True
        self.attempted = []

    def record_call(self, target):
        self.attempted.append(target)
        target_entries = {spec["entry"] for spec in match.TARGETS.values()}
        providers = {value for _, entries in TABLES.values() for value in entries}
        release = self.target_symbols["func_1516972C"]
        if target not in target_entries | providers | {release}:
            raise AssertionError(hex(target))
        args = self.arguments(1 if target == release else 3)
        self.calls.append((target, args))
        self.events.append(("CALL", target, args))

    def hook(self, target):
        release = self.target_symbols["func_1516972C"]
        if target == release:
            if self.event_case.mutate:
                put(self.memory, self.owner_address + 0x18, 0xCAFEBABE)
                self.memory[self.owner_address + 0x1C] = 0xA5
        else:
            owner, event, kind = self.arguments(3)
            put(self.memory, owner + 0x34, target ^ kind)
        for index in range(4):
            self.put(self.r[29] + index * 4, 0xB5000000 + index, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]
        self.hi, self.lo = 0x87654321, 0x12345678


def assemble(source, output):
    subprocess.run([
        "mips-linux-gnu-as", "-EB", "-mtune=vr4300", "-march=vr4300",
        "-mabi=32", "-I", str(ROOT / "conker/include"), "-o", str(output),
        str(source)], check=True, capture_output=True)


def linked(obj, name, label, entry=None, symbols=None):
    symbols = match.SYMBOLS if symbols is None else symbols
    entry = match.TARGETS[name]["entry"] if entry is None else entry
    text, functions, relocations = parse_object(obj)
    source, unknown = emit_function(text, functions[name], relocations, name,
                                    symbols)
    if unknown:
        raise ValueError("Unknown owner identity bindings: %r" % (unknown,))
    prefix = ROOT / match.BUILD / label
    prefix.with_suffix(".s").write_text(source)
    prefix.with_suffix(".ld").write_text(
        "SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n" % entry +
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


def native_source():
    selected = [match.selected_body(name) for name in match.TARGETS]
    base = selected[0]
    controls = (
        ("and_gate", " || ", " && "),
        ("wrong_command", "kind == 0x2D", "kind == 0x2E"),
        ("wrong_second_tag", "replacement->secondTag", "replacement->firstTag"),
        ("wrong_first_tag", "replacement->firstTag", "replacement->secondTag"),
        ("wrong_selector", "+ 0x2d", "+ 0x2c"),
        ("no_callback", "if (callback != NULL)", "if (0)"),
    )
    variants = []
    for label, old, new in controls:
        if old not in base:
            raise ValueError("Ineffective native control: " + label)
        variants.append(base.replace("func_15163FEC", "bad_" + label, 1)
                        .replace(old, new, 1))
    support = r'''
typedef void (*Handler)(void *, void *, u8);
OwnerIdentityCallback D_8008B374[2], D_8008B37C[5];
static u8 owner[0x80], packet[16], expected[0x80];
static u32 releases, callbacks, errors, wantedOwner, wantedEvent, wantedKind;
static const u32 vals[] = {0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678};
void func_1516972C(struct102 *value) {
    if ((u32)value != wantedOwner) errors++;
    releases++;
}
static void provider(void *a, void *b, u8 c) {
    if ((u32)a != wantedOwner || (u32)b != wantedEvent || c != wantedKind) errors++;
    callbacks++;
    *(u32 *)((u8 *)a + 0x34) = 0x151640C0u ^ c;
}
static int one(Handler fn, u32 pair, u32 kind, u32 pattern, u32 selector) {
    u32 i, first, second, current, release, callback;
    for (i=0;i<sizeof(owner);i++) owner[i]=expected[i]=(u8)(i*13+0x5A);
    for (i=0;i<sizeof(packet);i++) packet[i]=(u8)(i*17+3);
    first=vals[pattern%6]; second=vals[(pattern+1)%6];
    *(u32 *)(void *)packet=first; *(u32 *)(void *)(packet+4)=second;
    packet[8]=17; packet[9]=231;
    current=(pattern%3)==0?first:(pattern%3)==1?second:0xBEEFF00Du;
    *(u32 *)(void *)(owner+0x18)=current; owner[0x1C]=(pattern&1)?packet[4]:0x7F;
    owner[pair?0x3D:0x2D]=(u8)selector; expected[pair?0x3D:0x2D]=(u8)selector;
    owner[0x2C]=(selector==1)?0:1; expected[0x2C]=owner[0x2C];
    *(u32 *)(void *)(expected+0x18)=current; expected[0x1C]=owner[0x1C];
    D_8008B374[0]=0; D_8008B374[1]=provider;
    for(i=0;i<5;i++)D_8008B37C[i]=0; D_8008B37C[1]=provider;
    release=(u8)kind==0&&(first==current||packet[4]==owner[0x1C]);
    callback=(u8)kind!=0&&(u8)kind!=45&&selector==1;
    if ((u8)kind==45) {
        if(first==current){*(u32 *)(void *)(expected+0x18)=second;expected[0x1C]=packet[9];}
        else if(second==current){*(u32 *)(void *)(expected+0x18)=first;expected[0x1C]=packet[8];}
    }
    if(callback)*(u32 *)(void *)(expected+0x34)=0x151640C0u^(u8)kind;
    releases=callbacks=errors=0;wantedOwner=(u32)owner;wantedEvent=(u32)packet;wantedKind=(u8)kind;
    fn(owner,packet,(u8)kind);
    if(errors||releases!=release||callbacks!=callback)return 1;
    for(i=0;i<sizeof(owner);i++)if(owner[i]!=expected[i])return 1;
    return 0;
}
static int corpus(Handler fn,u32 pair,u32 full){u32 k,p,s,failed=0;
 for(k=0;k<(full?256u:4u);k++)for(p=0;p<9;p++)for(s=0;s<(pair?5u:2u);s++)
  failed|=one(fn,pair,full?k:(u32[]){0,45,64,255}[k],p,s);return failed;}
static int run(void){u32 i;Handler bad[]={BAD_LIST};
 if(corpus(func_15163FEC,0,1)||corpus(func_15164134,1,1))return 80;
 for(i=0;i<sizeof(bad)/sizeof(bad[0]);i++)if(!corpus(bad[i],0,0))return 81;
 return 0;}
'''.replace("BAD_LIST", ",".join("bad_" + item[0] for item in controls))
    return ("#include <ultra64.h>\n#include \"structs.h\"\n" + match.DECLARATIONS +
            "void func_1516972C(struct102 *);\n"
            "extern OwnerIdentityCallback D_8008B374[];\n"
            "extern OwnerIdentityCallback D_8008B37C[];\n" +
            "\n".join(selected + variants) + support + START)


class OwnerPeerEventPairTests(unittest.TestCase):
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
            raise ValueError("Installed owner identity guards differ")
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
            raw_source = cls.output / (name + "-raw.s")
            raw_source.write_text("\n".join(lines) + "\n")
            raw_obj = cls.output / (name + "-raw.o")
            assemble(raw_source, raw_obj)
            layout = cls.output / (name + "-layout.s")
            layout.write_text("glabel " + name + "\n" + "".join(
                "/* %06X %08X 00000000 */ nop\n" %
                (spec["rom"] + index * 4, spec["entry"] + index * 4)
                for index in range(match.WORDS)))
            rows_path = cls.output / (name + "-guards.csv")
            match.write_rows(rows_path, match.guard_rows(ROOT, cls.compact, name))
            guarded_source = cls.output / (name + "-guarded.s")
            guarded_source.write_text(emit_padded_assembly(
                raw_obj, layout, word_patches_path=rows_path,
                filename=match.FILENAME))
            guarded = cls.output / (name + "-guarded.o")
            assemble(guarded_source, guarded)
            cls.guarded[name] = guarded
        owner_source = cls.output / "qualified-owner.s"
        owner_source.write_text(pad_c_object.emit_padded_assembly(
            cls.compact, ROOT / "conker/retail_layout.us.txt", match.FILENAME,
            word_patches_path=cls.combined))
        cls.owner = cls.output / "qualified-owner.o"
        assemble(owner_source, cls.owner)
        linker = (ROOT / "conker/build/conker.ld").read_text()
        old = match.OBJECT.replace("conker/", "")
        new = str(cls.owner.relative_to(ROOT / "conker")).replace("\\", "/")
        if linker.count(old) != 1:
            raise ValueError("Owner identity linker reference changed")
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

    def test_01_guarded_words_relocations_and_stale_rows(self):
        self.assertEqual((len(self.rows), sum(bool(row["insert_after"])
                                             for row in self.rows)), (14, 2))
        rom = (ROOT / "conker/conker.us.bin").read_bytes()
        stale = 0
        for name, spec in match.TARGETS.items():
            retail = list(struct.unpack_from(">%dI" % match.WORDS, rom,
                                             spec["rom"]))
            self.assertEqual(linked(self.guarded[name], name,
                                    name + "-linked-guarded"), retail)
            self.assertEqual(len(linked(self.compact, name,
                                        name + "-linked-raw")), match.RAW_WORDS)
            rows = match.guard_rows(ROOT, self.compact, name)
            for index, row in enumerate(rows):
                changed = [dict(item) for item in rows]
                changed[index]["expected"] = "0x%08X" % (
                    int(row["expected"], 0) ^ 1)
                path = self.output / ("stale-%s-%d.csv" % (name, index))
                match.write_rows(path, changed)
                with self.assertRaisesRegex(ValueError, "stale word patch"):
                    emit_padded_assembly(
                        self.output / (name + "-raw.o"),
                        self.output / (name + "-layout.s"),
                        word_patches_path=path, filename=match.FILENAME)
                stale += 1
        self.assertEqual(stale, 14)

    def test_02_guest_semantics_aliases_callbacks_and_rebases(self):
        rom = (ROOT / "conker/conker.us.bin").read_bytes()
        total = 0
        for name, spec in match.TARGETS.items():
            programs = [
                list(struct.unpack_from(">%dI" % match.WORDS, rom, spec["rom"])),
                linked(self.compact, name, name + "-guest-raw"),
                linked(self.guarded[name], name, name + "-guest-guarded"),
            ]
            table_entries = TABLES[name][1]
            cases = [Case(0xA5000000 | kind, kind % 6, kind % 4, selector,
                          0, phase, bool(kind & 1))
                     for kind, selector, phase in itertools.product(
                         range(256), range(len(table_entries)), (0, 8))]
            cases += [Case(0xA5000000 | kind, pattern, relation, selector,
                           0, 0, mutate)
                      for kind, pattern, relation, selector, mutate
                      in itertools.product((0, 45, 64, 255), range(6),
                                           range(4), range(len(table_entries)),
                                           (False, True))]
            cases += [Case(0xA5000000 | kind, kind % 6, kind % 4, selector,
                           alias, phase, False)
                      for kind, selector, alias, phase in itertools.product(
                          (0, 45, 64, 255), range(len(table_entries)),
                          range(5), (0, 8))]
            for case in cases:
                initial = fixture(case, name)
                wanted, calls = reference(initial, case, name)
                machines = []
                for program_index, words in enumerate(programs):
                    machine = PairOracle(words, initial, case, name).run()
                    self.assertEqual((visible(machine.memory, case), machine.calls),
                                     (visible(wanted, case), calls),
                                     (name, case, program_index))
                    machines.append(machine)
                self.assertEqual((visible(machines[0].memory, case), machines[0].calls),
                                 (visible(machines[1].memory, case), machines[1].calls))
                total += 1
            for layout, (entry, symbols) in enumerate((
                    (0x15008000, dict(func_1516972C=0x10007FF0,
                                      D_8008B374=0x8009B374,
                                      D_8008B37C=0x8009B37C)),
                    (0x1F008000, dict(func_1516972C=0x1F108000,
                                      D_8008B374=0x8007B374,
                                      D_8008B37C=0x8007B37C)))):
                rebased = linked(self.guarded[name], name,
                                 "%s-rebase-%d" % (name, layout), entry, symbols)
                for kind, pattern, relation, selector in itertools.product(
                        (0, 45, 64, 255), (0, 5), range(3),
                        range(len(table_entries))):
                    case = Case(kind, pattern, relation, selector)
                    initial = fixture(case, name)
                    old_table, entries = TABLES[name]
                    new_table = symbols[match.TARGETS[name]["table"]]
                    for index, target in enumerate(entries):
                        put(initial, new_table + index * 4, target)
                    wanted, calls = reference(initial, case, name, symbols=symbols)
                    machine = PairOracle(rebased, initial, case, name,
                                         entry=entry, symbols=symbols).run()
                    self.assertEqual((visible(machine.memory, case), machine.calls),
                                     (visible(wanted, case), calls))
        self.assertEqual(total, 5208)

    def test_03_original_parent_registry_and_forwarded_three_arg_abi(self):
        rom = (ROOT / "conker/conker.us.bin").read_bytes()
        parent = list(struct.unpack_from(">%dI" % PARENT_WORDS, rom, PARENT_ROM))
        registry = struct.unpack_from(">%dI" % REGISTRY_WORDS, rom, REGISTRY_ROM)
        self.assertEqual((registry[16], registry[17]),
                         (match.TARGETS["func_15163FEC"]["entry"],
                          match.TARGETS["func_15164134"]["entry"]))
        count = 0
        for name, spec in match.TARGETS.items():
            truth = list(struct.unpack_from(">%dI" % match.WORDS, rom, spec["rom"]))
            connected = {spec["entry"] + index * 4: word
                         for index, word in enumerate(truth)}
            for kind, pattern, relation, selector, phase in itertools.product(
                    (0, 45, 64, 65, 255), range(6), range(4),
                    range(len(TABLES[name][1])), (0, 8)):
                case = Case(0xA5000000 | kind, pattern, relation, selector,
                            0, phase, True)
                initial = fixture(case, name)
                child = Case(kind, pattern, relation, selector, 0, phase, True)
                wanted, tail = reference(initial, child, name,
                                         incoming_sp=STACK + phase - 0x48)
                put(wanted, STACK + phase + 8, case.kind)
                expected_calls = [(spec["entry"],
                                   (OWNER, EVENT, kind)), *tail]
                machine = PairOracle(parent, initial, case, name, entry=PARENT,
                                     connected=connected).run()
                self.assertEqual((visible(machine.memory, case), machine.calls),
                                 (visible(wanted, case), expected_calls))
                count += 1
        self.assertEqual(count, 1680)

    def test_04_native32_actual_c_and_six_effective_controls(self):
        source = self.output / "native.c"
        source.write_text(native_source())
        for option in ("-O0", "-O2", "-O3"):
            executable = self.output / ("native" + option)
            build = subprocess.run(native_command(option) + [
                "-fno-strict-aliasing", "-mstackrealign", str(source), "-o",
                str(executable)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(executable)], capture_output=True)
            self.assertEqual(run.returncode, 0,
                             (option, run.returncode, run.stderr))

    def test_05_owner_image_registrations_and_protected_data(self):
        rom = (ROOT / "conker/conker.us.bin").read_bytes()
        for name, spec in match.TARGETS.items():
            jal = 0x0C000000 | (spec["entry"] >> 2 & 0x03FFFFFF)
            direct = [offset for offset in range(0, len(rom) - 3, 4)
                      if struct.unpack_from(">I", rom, offset)[0] == jal]
            literal = [offset for offset in range(0, len(rom) - 3, 4)
                       if struct.unpack_from(">I", rom, offset)[0] == spec["entry"]]
            self.assertEqual(direct, [])
            self.assertEqual(literal, [REGISTRY_ROM + spec["registry_index"] * 4])
            at = elf_slot_offset(self.elf.read_bytes(), spec["entry"],
                                 match.WORDS * 4)
            self.assertEqual(self.elf.read_bytes()[at:at + match.WORDS * 4],
                             rom[spec["rom"]:spec["rom"] + match.WORDS * 4])
        production = ROOT / match.OBJECT
        self.assertGreaterEqual(same_functions(production, self.owner,
                                               tuple(match.TARGETS)), 70)
        self.assertEqual(normalized_pools(production), normalized_pools(self.owner))
        old_functions, _, old_addresses = load_elf_functions(
            str(ROOT / "conker/build/conker.us.elf"), "mips-linux-gnu-objdump")
        new_functions, _, new_addresses = load_elf_functions(
            str(self.elf), "mips-linux-gnu-objdump")
        self.assertEqual((old_functions.keys(), old_addresses),
                         (new_functions.keys(), new_addresses))
        changed = [name for name in old_functions
                   if old_functions[name] != new_functions[name]]
        self.assertEqual(changed, [] if self.installed else list(match.TARGETS))
        old_symbols = {(name, fields[1], fields[3], fields[4], fields[5])
                       for _, name, fields, _ in symbol_rows(
                           (ROOT / "conker/build/conker.us.elf").read_bytes())}
        new_symbols = {(name, fields[1], fields[3], fields[4], fields[5])
                       for _, name, fields, _ in symbol_rows(self.elf.read_bytes())}
        self.assertEqual(old_symbols, new_symbols)
        report = audit_layout(self.elf, ROOT / "conker")
        self.assertEqual((report["exact"], report["bytes"],
                          report["owner_count"], report["different_bytes"]),
                         (True, 189088, 720, 0))


if __name__ == "__main__":
    unittest.main()
