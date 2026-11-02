"""Tagged effect-overlap scanner words, semantics, ABI and owner integration."""

from dataclasses import dataclass
from pathlib import Path
import csv
import io
import itertools
import struct
import subprocess
import unittest

from tools.experiments import game_effect_overlap_scanner_match as source
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.check_game_data_layout import audit_layout
from tools.pad_generated_object import parse_object
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK, put, read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]
TABLE = 0x800DCE50
COLUMNS = 0x800A6030
NODES = 0x00200000
CENTER = 0x00300000
EXTENT = 0x00300010
TAGS = 0x00300020


def put_float(memory, address, value):
    for index, byte in enumerate(struct.pack(">f", value)):
        memory[address + index] = byte


def get_float(memory, address):
    return struct.unpack(">f", bytes(memory[address + i] for i in range(4)))[0]


@dataclass(frozen=True)
class Case:
    slot: int = 0
    node_index: int = 0
    tag_index: int = 3
    count: int = 4
    mode: str = "inside"
    empty: bool = False
    phase: int = 0


def fixture(case):
    memory = {STACK + i: (i * 17 + 0xA5) & 0xFF for i in range(-0x400, 0x100)}
    memory.update({TABLE + i: 0 for i in range(0x340)})
    memory.update({NODES + i: (i * 13 + 0x5A) & 0xFF for i in range(0x400)})
    memory.update({CENTER + i: 0 for i in range(0x40)})
    put(memory, COLUMNS, 3)
    put(memory, COLUMNS + 4, 7)
    put_float(memory, CENTER, 10.0)
    put_float(memory, CENTER + 4, 20.0)
    put_float(memory, EXTENT, 2.0)
    put_float(memory, EXTENT + 4, 3.0)
    tags = (11, 22, 33, 44)
    for index, tag in enumerate(tags):
        put(memory, TAGS + index * 4, tag)
    positions = {
        "inside": (10.0, 20.0),
        "x-low-boundary": (7.0, 20.0),
        "x-high-boundary": (13.0, 20.0),
        "y-low-boundary": (10.0, 16.0),
        "y-high-boundary": (10.0, 24.0),
        "x-low-miss": (6.5, 20.0),
        "x-high-miss": (13.5, 20.0),
        "y-low-miss": (10.0, 15.5),
        "y-high-miss": (10.0, 24.5),
        "unmatched": (10.0, 20.0),
    }
    for slot in range(4):
        head = 0 if case.empty else NODES + slot * 0x80
        row, column = divmod(slot, 2)
        selected = (3, 7)[column]
        put(memory, TABLE + row * 0x1A0 + selected * 4, head)
        if not head:
            continue
        for node_index in range(2):
            node = head + node_index * 0x30
            put(memory, node + 8, head + 0x30 if node_index == 0 else 0)
            put_float(memory, node + 0x10, -100.0)
            put_float(memory, node + 0x14, -100.0)
            put_float(memory, node + 0x18, 1.0)
            put_float(memory, node + 0x1C, 1.0)
            memory[node + 0x2A] = 0xE0 + slot * 2 + node_index
    if not case.empty:
        node = NODES + case.slot * 0x80 + case.node_index * 0x30
        x, y = positions[case.mode]
        put_float(memory, node + 0x10, x)
        put_float(memory, node + 0x14, y)
        memory[node + 0x2A] = 0xFE if case.mode == "unmatched" else tags[case.tag_index]
    return memory


def reference(initial, case):
    memory = dict(initial)
    tag_count = case.count
    for row in range(2):
        for column_index in range(2):
            column = read(memory, COLUMNS + column_index * 4)
            node = read(memory, TABLE + row * 0x1A0 + column * 4)
            while node:
                next_node = read(memory, node + 8)
                matched = False
                if tag_count > 0:
                    for index in range(tag_count - 1, -1, -1):
                        if memory[node + 0x2A] == read(memory, TAGS + index * 4):
                            matched = True
                            break
                if matched:
                    extent_x = get_float(memory, node + 0x18) + get_float(memory, EXTENT)
                    extent_y = get_float(memory, node + 0x1C) + get_float(memory, EXTENT + 4)
                    node_x = get_float(memory, node + 0x10)
                    node_y = get_float(memory, node + 0x14)
                    center_x = get_float(memory, CENTER)
                    center_y = get_float(memory, CENTER + 4)
                    if (center_x - extent_x <= node_x <= center_x + extent_x and
                            center_y - extent_y <= node_y <= center_y + extent_y):
                        return memory, 1
                node = next_node
    return memory, 0


def public(memory):
    return {address: value for address, value in memory.items()
            if not STACK - 0x400 <= address < STACK + 0x100}


class OverlapOracle(TimingOracle):
    def __init__(self, words, memory, case, entry=source.ENTRY):
        super().__init__(words, memory, phase=case.phase, entry=entry,
                         arguments=(CENTER, EXTENT, TAGS, case.count))

    def hook(self, target):
        raise AssertionError(("Unexpected overlap helper", target))


def cases():
    modes = ("inside", "x-low-boundary", "x-high-boundary",
             "y-low-boundary", "y-high-boundary", "x-low-miss",
             "x-high-miss", "y-low-miss", "y-high-miss", "unmatched")
    for slot, node_index, tag_index, mode in itertools.product(
            range(4), range(2), range(4), modes):
        yield Case(slot, node_index, tag_index, tag_index + 1, mode,
                   phase=8 * ((slot + node_index + tag_index) & 1))
    for count in (-3, 0):
        yield Case(3, 1, 3, count, "inside")
    yield Case(empty=True)


def controls():
    selected = source.SELECTED
    return {
        "one-column": selected.replace("column < 2", "column < 1"),
        "one-row": selected.replace("row += 0x1A0", "row += 0x340"),
        "wrong-tag": selected.replace("node[0x2A] == *(cursor - 1)",
                                      "node[0x2A] != *(cursor - 1)"),
        "strict-first-bound": selected.replace("center[0] - extentX <= nodeX",
                                                "center[0] - extentX < nodeX"),
        "omit-request-extent": selected.replace(
            "*(f32 *)(node + 0x18) + extent[0]", "*(f32 *)(node + 0x18)"),
        "omit-second-node": selected.replace(
            "                } while ((node = next) != NULL);",
            "                    next = NULL;\n"
            "                } while ((node = next) != NULL);"),
    }


class EffectOverlapScannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD
        cls.selected, cls.owner, cls.guards, cls.qualified = source.prepare(ROOT)
        cls.baseline = source.freeze(ROOT, cls.output)
        linked_retail, retail_functions = link_owner(
            ROOT, cls.output, ROOT / source.OBJECT, source.OWNER)
        retail_info = retail_functions[source.FUNCTION]
        cls.retail = list(struct.unpack_from(">96I", linked_retail,
                                             retail_info["value"]))
        linked, functions = link_owner(ROOT, cls.output, cls.selected, source.OWNER)
        info = functions[source.FUNCTION]
        cls.raw = list(struct.unpack_from(">96I", linked, info["value"]))

    def test_01_complete_words_bindings_guards_and_owner(self):
        raw, bindings = source.checked_payload(
            self.selected, source.RAW_SHA, source.RAW_BINDINGS)
        self.assertEqual((len(raw) // 4, source.FRAME, len(bindings)), (96, 72, 6))
        self.assertEqual(self.qualified.read_bytes(), (ROOT / source.OBJECT).read_bytes())
        rows = list(csv.DictReader(io.StringIO(self.guards.read_text())))
        target = [row for row in rows if row["function"] == source.FUNCTION]
        self.assertEqual(len(target), 81)
        self.assertTrue(all(not row["insert_after"] and row["omit"] == "false"
                            for row in target))
        self.assertEqual(sum(row["expected_relocations"] != "-" for row in target), 6)
        self.assertEqual(sum(row["replacement_relocations"] != "-" for row in target), 6)
        current = self.output / "private-current-owner.o"
        self.assertEqual(same_functions(current, self.owner, (source.FUNCTION,)), 40)
        self.assertEqual(len(parse_object(current)[1]), 41)

    def test_02_guest_raw_and_retail_semantics_and_branch_coverage(self):
        visits = set()
        count = 0
        for case in cases():
            initial = fixture(case)
            expected_memory, expected_result = reference(initial, case)
            for label, words in (("raw", self.raw), ("retail", self.retail)):
                with self.subTest(case=case, image=label):
                    machine = OverlapOracle(words, initial, case)
                    saved = tuple(machine.r[16:24]) + tuple(machine.r[28:32])
                    machine.run()
                    self.assertEqual(public(machine.memory), public(expected_memory), case)
                    self.assertEqual(machine.r[2], expected_result, case)
                    self.assertEqual(tuple(machine.r[16:24]) + tuple(machine.r[28:32]), saved)
                    self.assertFalse(machine.calls)
                    visits.update(machine.visits)
            count += 1
        self.assertGreaterEqual(len(visits & set(range(source.ENTRY, source.ENTRY + source.SIZE, 4))), 94)
        self.assertEqual(count, 323)

    def test_03_native32_semantics_and_effective_controls(self):
        variants = {"selected": source.SELECTED, **controls()}
        prelude = source.HEADERS.replace(
            "extern u8 D_800DCE50[];\nextern s8 D_800DD190;",
            "struct TableStorage { u8 table[0x340]; s8 end; };\n"
            "static struct TableStorage storage __attribute__((aligned(4)));\n"
            "#define D_800DCE50 storage.table\n#define D_800DD190 storage.end")
        text = prelude + "\ns32 D_800A6030[2];\n" + r'''
typedef struct Node Node;
struct Node { u8 pad00[8]; Node *next; u8 pad0C[4]; f32 x,y,ex,ey; u8 pad20[10]; u8 tag; };
static Node nodes[4][2];
static f32 center[2],extent[2];
static s32 tags[4];
typedef char ABI[(sizeof(void*)==4&&__builtin_offsetof(Node,next)==8&&
 __builtin_offsetof(Node,x)==16&&__builtin_offsetof(Node,tag)==42&&
 sizeof(storage.table)==0x340)?1:-1];
static void clear(u8*p,u32 n){u32 i;for(i=0;i<n;i++)p[i]=0;}
static void setup(u32 slot,u32 second,u32 tagIndex,u32 mode){
 u32 i,row,col;Node*n;
 clear(storage.table,sizeof(storage.table));clear((u8*)nodes,sizeof(nodes));
 D_800A6030[0]=3;D_800A6030[1]=7;center[0]=10.;center[1]=20.;extent[0]=2.;extent[1]=3.;
 for(i=0;i<4;i++)tags[i]=(s32)(11+i*11);
 for(i=0;i<4;i++){row=i/2;col=i%2;*(Node**)(void*)(storage.table+row*0x1A0+(col?7:3)*4)=nodes[i];
  nodes[i][0].next=&nodes[i][1];nodes[i][1].next=0;
  nodes[i][0].x=nodes[i][1].x=-100.;nodes[i][0].y=nodes[i][1].y=-100.;
  nodes[i][0].ex=nodes[i][1].ex=1.;nodes[i][0].ey=nodes[i][1].ey=1.;
  nodes[i][0].tag=(u8)(0xE0+i*2);nodes[i][1].tag=(u8)(0xE1+i*2);}
 n=&nodes[slot][second];n->tag=(u8)tags[tagIndex];
 n->x=(f32[]){10.,7.,13.,6.5,13.5}[mode%5];
 n->y=(f32[]){20.,16.,24.,15.5,24.5}[(mode/5)%5];
}
static s32 model(s32 count){u32 row,col;Node*n;f32 ax,ay;
 for(row=0;row<2;row++)for(col=0;col<2;col++){
  n=*(Node**)(void*)(storage.table+row*0x1A0+(u32)D_800A6030[col]*4);
  while(n){s32 i,matched=0;for(i=count-1;i>=0;i--)if(n->tag==tags[i]){matched=1;break;}
   if(matched){ax=n->ex+extent[0];ay=n->ey+extent[1];
    if(center[0]-ax<=n->x&&n->x<=center[0]+ax&&center[1]-ay<=n->y&&n->y<=center[1]+ay)return 1;}n=n->next;}}
 return 0;}
'''
        for name, body in variants.items():
            text += body.replace(source.FUNCTION, "variant_" + name.replace("-", "_")) + "\n"
        text += "typedef s32(*Fn)(f32*,f32*,s32*,s32);\nstatic s32 check(Fn fn){u32 s,n,t,m;int differed=0;"
        text += "for(s=0;s<4;s++)for(n=0;n<2;n++)for(t=0;t<4;t++)for(m=0;m<25;m++){"
        text += "s32 wanted,actual;setup(s,n,t,m);wanted=model((s32)t+1);actual=fn(center,extent,tags,(s32)t+1);if(actual!=wanted)differed=1;}return differed;}\n"
        text += "int run(void){if(check(variant_selected))return 10;"
        for index, name in enumerate(controls(), 20):
            text += "if(!check(variant_%s))return %d;" % (name.replace("-", "_"), index)
        text += "return 0;}\n" + START
        for optimization in ("-O0", "-O2", "-O3"):
            path = self.output / ("native-overlap-" + optimization[1:] + ".c")
            path.write_text(text)
            binary = path.with_suffix("")
            result = subprocess.run(native_command(optimization) + ["-mstackrealign", str(path),
                "-o", str(binary)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(subprocess.run([str(binary)], timeout=60).returncode, 0,
                             optimization)

    def test_04_original_caller_and_four_argument_abi(self):
        rom = (ROOT / "conker/conker.us.bin").read_bytes()
        jal = 0x0C000000 | ((source.ENTRY >> 2) & 0x03FFFFFF)
        direct = [offset for offset in range(0, len(rom) - 3, 4)
                  if struct.unpack_from(">I", rom, offset)[0] == jal]
        literal = [offset for offset in range(0, len(rom) - 3, 4)
                   if struct.unpack_from(">I", rom, offset)[0] == source.ENTRY]
        self.assertEqual(direct, [0x182974])
        self.assertEqual(literal, [])
        caller = (ROOT / source.SOURCE).read_text()
        old_call = "func_151555AC(descriptor, position, pair, pairCount)"
        new_call = "func_151555AC((f32 *)descriptor, position, pair, pairCount)"
        self.assertEqual(caller.count(old_call) + caller.count(new_call), 1)
        self.assertEqual(caller.count(source.FUNCTION), 3)

    def test_05_guard_staleness_and_full_object_controls(self):
        raw, bindings = source.checked_payload(self.selected, source.RAW_SHA,
                                               source.RAW_BINDINGS)
        retail, retail_bindings = source.checked_payload(
            self.baseline[source.OBJECT], source.RETAIL_SHA, source.RETAIL_BINDINGS)
        prefix = self.baseline["conker/retail_word_patches.us.csv"].read_bytes()
        expected = source.guard_manifest(prefix, raw, bindings, retail, retail_bindings)
        self.assertEqual(expected, self.guards.read_bytes())
        for offset in (0, 0x1C, 0x20, 0x3C, 0x17C):
            bad = bytearray(raw)
            bad[offset + 3] ^= 1
            with self.assertRaises(ValueError):
                source.guard_manifest(prefix, bytes(bad), bindings, retail, retail_bindings)
        for offset in bindings:
            bad = {key: list(value) for key, value in bindings.items()}
            del bad[offset]
            with self.assertRaises(ValueError):
                source.guard_manifest(prefix, raw, bad, retail, retail_bindings)
        baseline_elf = self.baseline["conker/build/conker.us.elf"]
        self.assertEqual((ROOT / "conker/build/conker.us.elf").read_bytes(),
                         baseline_elf.read_bytes())
        protected = audit_layout(baseline_elf, ROOT / "conker")
        self.assertEqual((protected["exact"], protected["bytes"],
                          protected["owner_count"], protected["different_bytes"]),
                         (True, 189088, 720, 0))


if __name__ == "__main__":
    unittest.main()
