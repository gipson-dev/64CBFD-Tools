"""Finite signed interpolation, with separately rounded binary32 operations."""
import math
import struct
from tools.tests.test_game_trig_match import TrigOracle
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_point_transform_match import put, read

ENTRY = 0x150488C8
NAMES = ('D_80098E00', 'D_8009900C', 'D_80099010', 'D_80099014')
CONSTANTS = (0x437FFFFF, 0x477FFF00, 0x3FC90FDB)

def symbols(delta=0):
    return dict(zip(NAMES, (v + delta for v in (0x80098E00, 0x8009900C, 0x80099010, 0x80099014))))

def fixture(table, delta=0):
    s = symbols(delta)
    m = {s[NAMES[0]] + i: v for i, v in enumerate(table)}
    for n, v in zip(NAMES[1:], CONSTANTS):
        put(m, s[n], v)
    return m

def corpus():
    values = {0, 0x80000000, 1, 0x80000001, 0x3F800000, 0xBF800000}
    scale = floating(CONSTANTS[0])
    for i in range(256):
        for x in (i / scale, (i + 0.5) / scale, (i + 1) / scale):
            w = bits(x)
            for v in (w - 1, w, w + 1):
                if 0 <= v <= 0x3F800000:
                    values.update((v, v | 0x80000000))
    for i in range(512):
        v = ((i * 1664525 + 1013904223) & 0x7FFFFFFF) % 0x3F800001
        values.update((v, v | 0x80000000))
    return sorted(values)

def reference(word, table):
    x = floating(word)
    scaled = floating(bits(abs(x) * floating(CONSTANTS[0])))
    index = math.trunc(scaled)
    base = float(struct.unpack_from('>H', table, index * 2)[0])
    fraction = floating(bits(scaled - float(index)))
    next_value = float(struct.unpack_from('>H', table, (index + 1) * 2)[0]) if index < 255 else floating(CONSTANTS[1])
    difference = floating(bits(next_value - base))
    weighted = floating(bits(difference * fraction))
    interpolated = floating(bits(weighted + base))
    radians = floating(bits(interpolated * floating(CONSTANTS[2])))
    result = bits(radians / 65536.0)
    return result ^ (0x80000000 if x < 0.0 else 0)

class LookupOracle(TrigOracle):
    def __init__(self, words, memory, word, entry=ENTRY, fault=None):
        super().__init__(words, memory, word=word, entry=entry, fault=fault)
        self.trace = []

    def execute(self, w):
        op, fmt, fs, ft, fd, fn = w >> 26, w >> 21 & 31, w >> 11 & 31, w >> 16 & 31, w >> 6 & 31, w & 63
        if op == 17 and fmt == 16 and fn == 5:
            self.f[fd] = self.f[fs] & 0x7FFFFFFF
        elif op == 17 and fmt == 16 and fn == 3:
            self.f[fd] = bits(floating(self.f[fs]) / floating(self.f[ft]))
        else:
            super().execute(w)

    def get(self, p, n):
        v = super().get(p, n)
        if self.own_instruction:
            self.trace.append((p, n, v))
        return v

def state(m):
    return m.memory, m.r, m.f, m.calls, m.events, m.trace, m.current_pc, m.delay_of, m.accesses

from pathlib import Path
import hashlib,json,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

def qualify(root,output):
 r=root;o=output;F='func_150488C8';E=ENTRY;g=sys.modules[__name__]
 obj,diag=compile_owner(r,o,(o/'selected-headers.c').read_text()+(o/'selected-input.c').read_text(),'public-oracle-selected');assert not diag,diag
 raw,refs=payload(obj,F);original=o/('original-'+F+'.o');assert(raw,refs)==payload(original,F)
 rom=(r/'conker/conker.us.bin').read_bytes();truth=struct.unpack_from('>55I',rom,0x75D78)
 layouts=[]
 for delta in (0,0x17FFC,-0x8004):
  outputs=[]
  for label,source in(('original',original),('selected',obj)):
   p=o/('public-%s-rebase-%s'%(label,hex(delta).replace('-','m')));p.with_suffix('.ld').write_text('SECTIONS{.text 0x%X:SUBALIGN(4){*(.text)}}\n'%(E+delta))
   subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,*['--defsym=%s=0x%X'%(n,v)for n,v in g.symbols(delta).items()],'-o',str(p.with_suffix('.elf')),str(source)],capture_output=True,check=True)
   data=p.with_suffix('.elf').read_bytes();a=elf_slot_offset(data,E+delta,220);outputs.append(data[a:a+220])
  assert outputs[0]==outputs[1]
  if delta==0:assert outputs[0]==struct.pack('>55I',*truth)
  layouts.append((delta,struct.unpack('>55I',outputs[0]),struct.unpack('>55I',outputs[1])))
 tables=[(o/'retail-table.bin').read_bytes(),struct.pack('>256H',*[(i*40503+0xFEDC)&65535 for i in range(256)])]
 values=g.corpus();coverage=set();cases=0;cells=set();signs=set()
 for table in tables:
  for delta,original_words,words in layouts:
   initial=g.fixture(table,delta)
   for word in values:
    m=g.LookupOracle(words,initial,word,entry=E+delta).run()
    assert m.f[0]==g.reference(word,table),(hex(word),hex(m.f[0]),hex(g.reference(word,table)))
    assert m.memory==initial and not m.calls and not m.stores
    coverage.update(v-delta for v in m.visits)
    cells.add((m.trace[1][0]-g.symbols(delta)['D_80098E00'])//2)
    signs.add(word>>31);cases+=1
 missing=set(range(E,E+220,4))-coverage
 assert missing=={E+v for v in(0x4C,0x50,0x54,0x78,0x7C,0x80,0x84,0x88)},sorted(hex(v-E)for v in missing)
 assert cells==set(range(256))and signs=={0,1}
 prefixes=0
 for delta,original_words,words in layouts:
  for word in (0,0x80000000,0x3F000000,0xBF000000,0x3F800000,0xBF800000):
   initial=g.fixture(tables[0],delta);full=g.LookupOracle(words,initial,word,entry=E+delta).run()
   for cut in range(full.accesses):
    models=[g.LookupOracle(body,initial,word,entry=E+delta,fault=cut)for body in(original_words,words)]
    for m in models:
     try:m.run()
     except AccessBoundary:pass
     else:raise AssertionError('Fault did not fire')
    assert g.state(models[0])==g.state(models[1]);prefixes+=1
   # Remove every accessed field in turn: sparse guest memory must fault identically.
   for address,n,_ in full.trace:
    sparse=dict(initial)
    for i in range(n):sparse.pop(address+i,None)
    for body in (original_words,words):
     try:g.LookupOracle(body,sparse,word,entry=E+delta).run()
     except AssertionError as exc:assert exc.args and exc.args[0]==('unmapped read',address,n),exc
     else:raise AssertionError('Sparse memory unexpectedly succeeded')
 out_of_domain_prefixes=0
 for delta,original_words,words in layouts:
  for word in(0x3F800001,0xBF800001):
   initial=g.fixture(tables[0],delta);models=[]
   for body in(original_words,words):
    m=g.LookupOracle(body,initial,word,entry=E+delta)
    try:m.run()
    except AssertionError as exc:assert exc.args[0]==('unmapped read',g.symbols(delta)['D_80098E00']+512,2),exc
    else:raise AssertionError('Unchecked index unexpectedly clamped')
    assert m.memory==initial and not m.calls;models.append(m)
   assert g.state(models[0])==g.state(models[1]);out_of_domain_prefixes+=1
 literal=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==E]
 direct=[i for i in range(0,len(rom)-3,4)if(struct.unpack_from('>I',rom,i)[0]>>26)in(2,3)and(struct.unpack_from('>I',rom,i)[0]&0x3FFFFFF)==(E>>2)&0x3FFFFFF]
 assert not literal and not direct,(literal,direct)
 report=dict(success=True,private_only=True,installed=False,matching_credit=0,words=55,slot_words=58,frame=0,guards=0,raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings={str(k):v for k,v in refs.items()},guest_cases=cases,inputs=len(values),tables=2,layouts=3,all_cells=256,reachable_words=47,unreachable_offsets=sorted(v-E for v in missing),fault_prefixes=prefixes,out_of_domain_guest_only_prefixes=out_of_domain_prefixes,ABI='f32(F12) -> f32(F0), frame zero, all callee-saved roles checked by machine',direct_ROM_transfers=direct,aligned_ROM_function_pointers=literal,indirect_callers_unknown=True,finite_native_domain='abs(input) <= 1',NaN_FCSR_hardware_gameplay_not_qualified=True)
 (o/'private-guest-v8.json').write_text(json.dumps(report,indent=2)+'\n');return report
