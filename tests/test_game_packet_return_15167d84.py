"""Nullable packet return, overlapping bcopy, and the real emitter copy window."""
from dataclasses import dataclass, replace
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_packet_return_15167d84 as m
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode, WindowBoundary
from tools.tests.test_game_point_transform_match import put
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

PACKET, OUTPUT, CURVE, INPUT = 0x30000, 0x50000, 0x60000, 0x70000
WINDOW, END = 0x151A16C0, 0x151A16E8
u32 = lambda n: n & 0xFFFFFFFF
data = lambda mem, p, n: bytes(mem[p+i] for i in range(n))
public = lambda mem: {a:b for a,b in mem.items() if not STACK-2048 <= a < STACK+1024}


@dataclass(frozen=True)
class Case:
    seed: int = 0
    phase: int = 0
    alternate: int = 0
    extra: int = 34
    marker: int = -1
    mode: int = 0x123400FF
    owner: int = 0x87654321
    success: int = 1
    alias: int = 0
    mutation: int = 0


def packet(c):
    return (PACKET, OUTPUT+8, OUTPUT+24, OUTPUT+16)[c.alias]


def arguments(c):
    return tuple(map(u32, (packet(c), c.alternate, c.extra, c.marker, c.mode, c.owner)))


def fixture(c):
    mem = {STACK+i: (i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
    for base in (PACKET,OUTPUT,CURVE,INPUT):
        mem.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(256)})
    mem[INPUT+12] = c.mode&255
    mem[INPUT+1] = c.owner&255
    return mem


def reference(c, window=False, syms=None):
    s = m.symbols() if syms is None else syms
    mem = fixture(c)
    if window:
        c = replace(c, alternate=0, extra=34, marker=-1, mode=c.mode&255, owner=c.owner&255)
    calls = [(m.ENTRY, arguments(c))] if window else []
    calls.append((s['func_15167A68'], (5 if c.alternate==0 else 66, u32(c.owner), u32(c.extra+80), 0, c.mode&255, 1)))
    if c.mutation&1: mem[packet(c)] ^= 0x5A
    result = OUTPUT if c.success else 0
    if result:
        calls.append((s['bcopy'], (packet(c),result+16,56)))
        saved = data(mem,packet(c),56)
        for i,v in enumerate(saved): mem[result+16+i]=v
        if c.mutation&2: mem[result+72]=0x33
        mem[result+72]=c.marker&255
        if window:
            calls.append((s['memcpy'], (result+80,CURVE,34)))
            for i,v in enumerate(data(mem,CURVE,34)):mem[result+80+i]=v
    return mem,calls,result


class Machine(FactoryOracle):
    def __init__(self, words, c, window=False, syms=None):
        self.services=m.symbols() if syms is None else syms
        if window:
            c=replace(c,alternate=0,extra=34,marker=-1,mode=c.mode&255,owner=c.owner&255)
        connected=dict(zip(range(m.ENTRY,m.ENTRY+len(words)*4,4),words)) if window else {}
        if window:
            connected[END]=0
            words=struct.unpack_from('>10I',(m.ROOT/'conker/conker.us.bin').read_bytes(),WINDOW-0x15000000+0x2D4B0)
        super().__init__(words,fixture(c),c,entry=WINDOW if window else m.ENTRY,arguments=arguments(c),connected=connected)
        if window:
            self.r[19]=INPUT;self.r[23]=CURVE
            self.code=WindowCode(self.code,self);self.code.ends=(END,)
        self.window=window

    def record_call(self,t):
        s=self.services
        n={m.ENTRY:6,s['func_15167A68']:6,s['bcopy']:3,s['memcpy']:3}[t]
        a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a))

    def hook(self,t):
        s=self.services;c=self.case;a=self.calls[-1][1]
        if t==s['func_15167A68']:
            if c.mutation&1:self.memory[packet(c)]^=0x5A
            value=OUTPUT if c.success else 0
        else:
            assert t in (s['bcopy'],s['memcpy'])
            src,dst,n=(a[0],a[1],a[2]) if t==s['bcopy'] else (a[1],a[0],a[2])
            assert n==(56 if t==s['bcopy'] else 34)
            saved=data(self.memory,src,n)
            for i,v in enumerate(saved):self.memory[dst+i]=v
            if t==s['bcopy'] and c.mutation&2:self.memory[OUTPUT+72]=0x33
            # bcopy is void; its arbitrary v0 must not become the helper result.
            value=0xDEADBEEF if t==s['bcopy'] else dst
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0xA5000010,0xA5000011
        self.r[2]=u32(value)


def run_machine(words,c,window=False,syms=None):
    q=Machine(words,c,window,syms)
    try:q.run()
    except WindowBoundary:
        assert window and q.r[29]==STACK+c.phase
    expected,calls,result=reference(c,window,syms)
    assert public(q.memory)==public(expected), ('public bytes',c,window)
    assert q.calls==calls, ('calls',c,window,q.calls,calls)
    if not window:assert q.r[2]==result, ('nullable pointer return',c,q.r[2],result)
    return q


class PacketReturnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=m.qualify()
        cls.raw,cls.refs=m.checked_payload(*payload(m.OUT/'owner0-after.o',m.NAME))
        cls.words=bound_blob(cls.raw,cls.refs,m.symbols())
        cls.retail=struct.unpack_from('>34I',(m.ROOT/'conker/conker.us.bin').read_bytes(),m.ROM)

    def test_nullable_return_aliases_and_real_copy_window(self):
        visits=set();runs=0
        for i,success,alias,mutation,phase in itertools.product(range(16),range(2),range(4),range(4),(0,8)):
            c=Case(seed=i,success=success,alias=alias,mutation=mutation,phase=phase,alternate=(0,1,-1,-2147483648)[i%4],extra=(0,34,-80,2147483647)[i%4],marker=(-128,-1,0,127)[i%4],mode=0x12340000|i*17,owner=u32(i*0x12345678))
            a=run_machine(self.words,c);b=run_machine(self.retail,c)
            self.assertEqual((a.memory,a.trace,a.r),(b.memory,b.trace,b.r));visits.update(a.visits)
            run_machine(self.words,c,True);runs+=3
        self.assertEqual(visits,set(range(m.ENTRY,m.ENTRY+136,4)))
        (m.OUT/'guest.json').write_text(json.dumps(dict(runs=runs,helper_words_visited=len(visits),original_emitter_window_words=10,allocator_and_copy_opaque=True),indent=2)+'\n')

    def test_source_fingerprint_and_relocation_controls(self):
        for i in range(34):
            changed=bytearray(self.raw);changed[4*i+3]^=1
            with self.assertRaises(AssertionError):m.checked_payload(bytes(changed),self.refs)
        for at in self.refs:
            with self.assertRaises(AssertionError):m.checked_payload(self.raw,{**self.refs,at:[('R_MIPS_26','wrong')]})
        # Effective result corruption is caught by the public C-ABI expectation.
        changed=list(self.words)
        site=next(i for i,w in enumerate(changed)if w==0x8FA20024)
        changed[site]=0x00001025
        with self.assertRaises(AssertionError):run_machine(changed,Case())

    def test_independent_service_rebases(self):
        for delta in (0x10000,0x20000,0x30000):
            syms={n:v+delta for n,v in m.symbols().items()}
            words=bound_blob(self.raw,self.refs,syms)
            for success,alias,mutation in itertools.product(range(2),range(4),range(4)):
                run_machine(words,Case(success=success,alias=alias,mutation=mutation),syms=syms)

    def test_native32_and_source_controls(self):
        prefix='''typedef unsigned char u8;typedef signed char s8;typedef signed int s32;
        #define NULL ((void *)0)
        static u8 arena[512],input[256],curve[34];static u8 *src;static s32 alternate,extra,owner;static u8 mode,marker;static int success,mutation,stage,error;
        static void check(int x){if(!x)error=1;}
        static void copy(const void *a,void *b,unsigned n){u8 saved[56];for(unsigned i=0;i<n;i++)saved[i]=((const u8*)a)[i];for(unsigned i=0;i<n;i++)((u8*)b)[i]=saved[i];}
        void *func_15167A68(s32 kind,s32 o,s32 n,s32 zero,u8 m,u8 one){check(stage++==0&&kind==(alternate?66:5)&&o==owner&&n==extra+80&&zero==0&&m==mode&&one==1);if(mutation&1)src[0]^=0x5a;return success?arena:NULL;}
        void bcopy(const void *s,void *d,unsigned n){check(stage++==1&&s==src&&d==arena+16&&n==56);copy(s,d,n);if(mutation&2)arena[72]=0x33;}
        '''
        suffix='''
        _Static_assert(sizeof(void*)==4,"native32");
        static int run(void){
          for(unsigned seed=0;seed<256;seed++)for(int out=0;out<2;out++)for(int alias=0;alias<4;alias++)for(int mut=0;mut<4;mut++){
            u8 expected[512],snapshot[56];for(int i=0;i<512;i++)arena[i]=(i*29+seed*11+0x5a)&255;
            for(int i=0;i<256;i++)input[i]=(i*17+seed*13+0xa5)&255;
            for(int i=0;i<34;i++)curve[i]=(i*31+seed)&255;
            src=alias==0?input:arena+(alias==1?8:alias==2?24:16);
            alternate=seed%4==0?0:seed%4==1?1:seed%4==2?-1:(s32)0x80000000u;extra=seed%3==0?-80:seed%3==1?0:34;
            owner=(s32)(seed*0x12345678u);mode=seed;marker=seed;success=out;mutation=mut;stage=error=0;
            for(int i=0;i<512;i++)expected[i]=arena[i];
            for(int i=0;i<56;i++)snapshot[i]=src[i];if(mut&1)snapshot[0]^=0x5a;
            if(mut&1&&alias)expected[src-arena]^=0x5a;
            if(out){for(int i=0;i<56;i++)expected[16+i]=snapshot[i];expected[72]=marker;}
            u8 *p=func_15167D84(src,alternate,extra,(s8)marker,mode,owner);
            check(p==(out?arena:NULL));check(stage==(out?2:1));
            for(int i=0;i<512;i++)check(arena[i]==expected[i]);
            if(error)return 3;
            if(p){copy(curve,p+80,34);for(int i=0;i<34;i++)check(p[80+i]==curve[i]);}
            if(error)return 4;
          }return 0;
        }
        '''
        controls={'zero-return':m.SELECTED.replace('    return particle;\n}', '    return NULL;\n}'),
                  'wrong-marker':m.SELECTED.replace('particle[0x48] = marker','particle[0x49] = marker'),
                  'short-copy':m.SELECTED.replace('0x38);','0x34);')}
        rows=[]
        for label,body in [('selected',m.SELECTED),*controls.items()]:
            for opt in (('-O0','-O2')if label=='selected'else('-O2',)):
                source=m.OUT/('native-'+label+opt+'.c');exe=source.with_suffix('')
                source.write_text(prefix+body+suffix+START)
                p=subprocess.run(native_command(opt)+[str(source),'-o',str(exe)],cwd=m.ROOT,capture_output=True,text=True)
                self.assertEqual((p.returncode,p.stderr),(0,''))
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode==0,label=='selected',(label,opt,result.returncode))
                rows.append(dict(label=label,opt=opt,exit_code=result.returncode))
        (m.OUT/'native.json').write_text(json.dumps(dict(cases_per_run=8192,undefined_behavior_traps=True,runs=rows),indent=2)+'\n')


if __name__=='__main__':unittest.main()
