"""Route dispatch semantics, opaque helper mutations, native32 and linked gates."""
from contextlib import nullcontext
import csv
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_route_dispatcher_match as source
from tools.tests import test_game_route_projection_setup as guest
from tools.tests import test_game_route_projection_integration as connected
from tools.tests.test_game_projected_packet_draw import native_command

put,read,STACK=guest.put,guest.read,guest.STACK
SYMBOLS={'D_800872A0':0x800872A0,'D_800D23A9':0x800D23A9,'D_800D2398':0x800D2398,
    'D_800CC2D0':0x800CC2D0,'func_150891E8':0x150891E8,'func_150896EC':0x150896EC}
TABLE,OTHER=0x30000,0x90000


def signed(v):return ((v&255)^128)-128


def effects(mode,n,args,symbols):
    if n!=1:return []
    count,glob,request=(symbols[k] for k in ('D_800D2398','D_800872A0','D_800D23A9'))
    return {
        0:[],1:[(count,0,1)],2:[(count,255,1)],3:[(count,3,1)],4:[(glob,OTHER,4)],
        5:[(request,0x99,1)],6:[(TABLE+132+0x30,3,1)],7:[(TABLE+132+0x31,128,1)],
        8:[(symbols['D_800CC2D0']+792,0,4)],9:[(count,128,1)],
    }[mode]


def fixture(count=1,state=2,slot=0,gate=0,alternate=0,active=1,null=False,alias=0,symbols=SYMBOLS):
    table=(TABLE,symbols['D_800D23A9']-0x30,STACK-0x40,STACK,STACK-0x31)[alias]
    for base in (table,OTHER):
        if base<STACK+0x500 and base+128*132>STACK-0x400 and not (base==table and alias>=2):
            raise ValueError('Ordinary dispatcher table overlaps private stack')
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x500)}
    for base in (table,OTHER):
        memory.update({(base+i)&0xFFFFFFFF:0xA5 for i in range(128*132)})
        for i in range(128):
            put(memory,base+i*132+0x30,state,1);put(memory,base+i*132+0x31,slot,1)
            put(memory,base+i*132+0x48,gate,1);put(memory,base+i*132+0x49,alternate,1)
    for i in range(-128,128):put(memory,(symbols['D_800CC2D0']+i*812+792)&0xFFFFFFFF,active)
    put(memory,symbols['D_800872A0'],0 if null else table)
    put(memory,symbols['D_800D2398'],count,1);put(memory,symbols['D_800D23A9'],0x5A,1)
    return memory


def reference(initial,mode=0,symbols=SYMBOLS):
    memory=dict(initial);trace=[];calls=[]
    def get(at,n=4):
        value=read(memory,at,n);trace.append(('R',at,n,value));return value
    request,glob,limit,actors=(symbols[k] for k in ('D_800D23A9','D_800872A0','D_800D2398','D_800CC2D0'))
    put(memory,request,0,1);trace.append(('W',request,1,0))
    if get(glob):
        count=signed(get(limit,1));index=0
        while index<count:
            rec=(get(glob)+index*132)&0xFFFFFFFF
            actor=(actors+signed(get(rec+49,1))*812)&0xFFFFFFFF
            call=None
            if get(actor+792):
                if signed(get(rec+48,1))>=2:call=(symbols['func_150891E8'],(rec,actor))
                elif get(rec+72,1)==0:call=(symbols['func_150896EC'],(rec,actor,0))
                elif signed(get(rec+73,1))!=0:call=(symbols['func_150896EC'],(rec,actor,1))
            if call is not None:
                calls.append(call)
                for at,value,n in effects(mode,len(calls),call[1],symbols):put(memory,at,value,n)
                count=signed(get(limit,1))
            index+=1
    return guest.public(memory),calls,trace


class DispatchOracle(guest.ProjectionOracle):
    def __init__(self,words,memory,mode=0,phase=0,symbols=SYMBOLS,entry=source.ENTRY):
        self.trace=[];self.mutation=mode
        guest.base.PointProjectionOracle.__init__(self,words,memory,(),[],phase,entry,{})
        self.symbols=symbols

    def record_call(self,target):
        if target not in (self.symbols['func_150891E8'],self.symbols['func_150896EC']):
            raise AssertionError('Unexpected route dispatcher provider')
        self.calls.append((target,self.arguments(2 if target==self.symbols['func_150891E8'] else 3)))

    def hook(self,target):
        for at,value,n in effects(self.mutation,len(self.calls),self.calls[-1][1],self.symbols):self.put(at,value,n)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]


def cases():
    for value in range(256):yield dict(count=value)
    for value in range(256):yield dict(state=value,slot=value,gate=value&1,alternate=value>>1)
    for value,branch in itertools.product(range(256),range(3)):
        yield dict(slot=value,state=2 if branch==0 else 1,gate=branch==2,alternate=1)
    for value,field in itertools.product(range(256),('gate','alternate')):
        yield dict(state=0,gate=value if field=='gate' else 1,alternate=value if field=='alternate' else 1)
    for mode,branch in itertools.product(range(10),range(3)):
        yield dict(mode=mode,count=1 if mode==3 else 3,state=2 if branch==0 else 1,gate=branch==2,alternate=1)
    for null in (False,True):yield dict(null=null,count=1 if null else 128)
    for alias,phase in itertools.product(range(1,5),(0,8)):yield dict(alias=alias,phase=phase,state=1,alternate=1)
    for active,state in itertools.product((0,0x80000000,0xFFFFFFFF),(0,1,2,127,128,255)):
        yield dict(active=active,state=state,count=3,gate=1,alternate=255)


class RouteDispatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.installed=source.raw_read(cls.root/'conker/src/game/generated_B3020.c')==source.expected_inputs(cls.root,cls.out)['conker/src/game/generated_B3020.c']
        with source.historical_view(cls.root,cls.out) if cls.installed else nullcontext():
            cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
            cls.prediction=source.predict(cls.root,cls.out,cls.padded)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin')
        if cls.installed:
            elf=source.raw_read(cls.root/'conker/build/conker.us.elf')
            cls.words=list(struct.unpack_from('>67I',elf,source.prior.elf_slot_offset(elf,source.ENTRY,268)))
        cls.truth=list(struct.unpack_from('>67I',cls.rom,source.ROM))

    def receipt(self,name,**values):(self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_direct_words_owner_padding_and_prediction(self):
        self.assertEqual(self.words,self.truth);source.checked(self.obj)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(67,48,0))
        self.assertEqual(self.row['unchanged_primary_neighbors'],72)
        self.assertGreater(self.row['unchanged_caller_functions'],0)
        self.assertEqual(self.prediction['after'],source.AFTER)

    def test_02_complete_guest_semantics_traces_and_ABI(self):
        total=independent=0;visits=set()
        for kw in cases():
            kw=dict(kw);mode=kw.pop('mode',0);phase=kw.pop('phase',(total&1)*8)
            initial=fixture(**kw)
            machines=[DispatchOracle(w,initial,mode,phase) for w in (self.words,self.truth)]
            saved=list(machines[0].r[16:24]);a,b=[m.run() for m in machines]
            if kw.get('alias',0)<2:
                self.assertEqual((guest.public(a.memory),a.calls,a.trace),reference(initial,mode),(total,kw,mode))
                independent+=1
            self.assertEqual((a.memory,a.r,a.f,a.calls),(b.memory,b.r,b.f,b.calls))
            self.assertEqual(a.r[16:24],saved)
            self.assertEqual(a.r[29],STACK+phase);self.assertEqual(a.f[20:],a.saved_f)
            visits.update(a.visits);total+=1
        self.receipt('guest',paired_cases=total,visited_words=len(visits),full_memory_GP_FP_calls_equal=True,
            independent_public_reference_cases=independent,private_stack_alias_cases=total-independent,
            helpers_opaque_and_clobber_caller_saved=True)
        self.assertEqual((total,independent,len(visits)),(1850,1844,65))

    def test_03_every_fired_root_access_fault_prefix(self):
        total=0;complete=0
        for mode,state,phase in itertools.product((0,3,4),(1,2),(0,8)):
            initial=fixture(count=1 if mode==3 else 3,state=state,gate=state==1,alternate=1)
            full=DispatchOracle(self.truth,initial,mode,phase).run()
            for cut in range(full.all_accesses):
                machines=[]
                for words in (self.words,self.truth):
                    m=DispatchOracle(words,initial,mode,phase);m.access_fault=cut
                    with self.assertRaises(guest.base.faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,cut);machines.append(m)
                a,b=machines
                self.assertEqual((a.memory,a.r,a.f,a.calls,a.current_pc,a.delay_of),
                    (b.memory,b.r,b.f,b.calls,b.current_pc,b.delay_of));total+=1
            complete+=1
        self.assertEqual((complete,total),(12,396))
        self.receipt('faults',complete_cases=complete,paired_fired_prefixes=total,synthetic_not_hardware=True,
            opaque_provider_accesses_excluded=True)

    def test_04_connected_projection_and_actual_upstream_call_window(self):
        helpers={}
        for entry,count in {source.prior.ENTRY:321,**guest.HELPERS}.items():
            helpers.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,self.rom,entry-0x14FD2B50)))
        total=0
        for state,slot,flag,phase in itertools.product((2,3),(0,1,127,-1,-128),(0,64),(0,8)):
            memory,args=guest.fixture(state,1,flag=flag);actor=(SYMBOLS['D_800CC2D0']+slot*812)&0xFFFFFFFF
            for i in range(0x400):memory[actor+i]=memory[guest.ACTOR+i]
            put(memory,guest.RECORD+49,slot,1);put(memory,SYMBOLS['D_800872A0'],guest.RECORD)
            put(memory,SYMBOLS['D_800D2398'],1,1);put(memory,SYMBOLS['D_800D23A9'],0xA5,1)
            a,b=[connected.CallerOracle(w,memory,helpers,phase).run() for w in (self.words,self.truth)]
            self.assertEqual((a.memory,a.r,a.f,a.calls),(b.memory,b.r,b.f,b.calls));total+=1
        with (self.root/'conker/retail_layout.us.txt').open() as stream:rows=list(csv.DictReader(stream))
        opcode=(3<<26)|((source.ENTRY>>2)&0x3FFFFFF);sites=[]
        for row in rows:
            if row['section']!='game':continue
            start,end=int(row['address'],0),int(row['end'],0)
            for at in range(start,end,4):
                if struct.unpack_from('>I',self.rom,at-0x14FD2B50)[0]==opcode:sites.append((row['function'],at))
        self.assertEqual(sites,[('func_15019130',0x15019208)])
        self.assertEqual(struct.unpack_from('>I',self.rom,0x15019210-0x14FD2B50)[0],0x0D448AB8)
        self.assertEqual(total,40)
        self.receipt('connected',projection_cases=total,actual_projection_selector_enqueue=True,
            other_callee_opaque=True,direct_sites=sites,upstream_V0_not_consumed_before_next_JAL=True)

    def test_05_word_binding_input_and_successor_controls(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION];checks=0
        for i in range(67):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)),self.assertRaises(ValueError):source.checked(self.obj)
            checks+=1
        for at in source.BINDINGS:
            bad=dict(rel);bad.pop(f['value']+at)
            with patch.object(source,'parse_object',return_value=(text,functions,bad)),self.assertRaises(ValueError):source.checked(self.obj)
            checks+=1
        with source.historical_view(self.root,self.out) if self.installed else nullcontext():
            original=Path.read_bytes
            for path in source.INPUTS:
                target=self.root/path
                def changed(p):return original(p)+b'\0' if p==target else original(p)
                with patch.object(Path,'read_bytes',changed),self.assertRaisesRegex(ValueError,'Changed route dispatcher input'):
                    source.freeze(self.root,self.out)
        original=source.raw_read
        for path,name in source.SUCCESSOR_FILES.items():
            target=self.out/name
            def changed(p):return original(p)+b'\0' if p==target else original(p)
            with patch.object(source,'raw_read',changed),self.assertRaisesRegex(ValueError,'Changed first dispatcher successor'):
                source.expected_inputs(self.root,self.out)
            checkpoint=source.prior.candidate.source.checkpoint;raw=checkpoint.raw_read
            other=source.raw_read(self.out/('before-%02d'%list(source.INPUTS).index(path))) if self.installed else source.expected_inputs(self.root,self.out)[path]
            def mixed(p):return other if p==self.root/path else raw(p)
            with patch.object(checkpoint,'raw_read',mixed),self.assertRaisesRegex(ValueError,'Mixed or uninstalled'):
                source.verify(self.root,self.out)
        self.assertEqual(checks,84);self.receipt('controls',words_and_bindings=checks,inputs=len(source.INPUTS),successors=3,mixed_live_stages=3)

    def test_06_installed_whole_ELF_audit(self):
        self.assertEqual(source.verify(self.root,self.out),'after' if self.installed else 'before')
        if self.installed:
            row=source.audit(self.root,self.out);self.assertEqual(row['functions'],6057)
            self.assertEqual(row['changed_ELF_bytes'],self.prediction['changed_ELF_bytes'])

    def test_07_independent_symbol_rebases(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        from tools.experiments.game_actor_classifier_candidates import sections
        text,functions,bindings=source.parse_object(self.obj);f=functions[source.FUNCTION]
        code,unresolved=emit_function(text,f,bindings,source.FUNCTION,SYMBOLS)
        self.assertEqual(unresolved,[]);asm=self.out/'rebase.s';asm.write_text(code);obj=asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],check=True,capture_output=True)
        count=0
        for trial in range(4):
            symbols=dict(zip(SYMBOLS,(0x80097FFC+trial*0x10000,0x80098004+trial*0x10000,
                0x80098008+trial*0x10000,0x80108000+trial*0x10000,0x15301000+trial*0x10000,0x15302000+trial*0x10000)))
            entry=0x15200000+trial*0x10000;ld=self.out/('rebase-%d.ld'%trial);elf=ld.with_suffix('.elf')
            ld.write_text('SECTIONS { .text 0x%X : { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-ld','-T',str(ld),'-e',source.FUNCTION,
                *['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            words=list(struct.unpack_from('>67I',sections(elf)['.text'][1]));expected=list(self.truth)
            for at,[(kind,name)] in source.BINDINGS.items():
                value=symbols[name];i=at//4
                expected[i]=(expected[i]&0xFC000000)|((value>>2)&0x3FFFFFF) if kind=='R_MIPS_26' else \
                    (expected[i]&0xFFFF0000)|(((value+0x8000)>>16) if kind=='R_MIPS_HI16' else value)&65535
            self.assertEqual(words,expected)
            for state,slot,phase in itertools.product((1,2,128),(0,127,128,255),(0,8)):
                initial=fixture(state=state,slot=slot,gate=1,alternate=1,symbols=symbols)
                m=DispatchOracle(words,initial,phase=phase,symbols=symbols,entry=entry).run()
                self.assertEqual((guest.public(m.memory),m.calls,m.trace),reference(initial,symbols=symbols));count+=1
        self.assertEqual(count,96);self.receipt('rebases',independent_links=4,cases=count)

    def test_08_native32_actual_C_and_effective_controls(self):
        from tools.experiments import game_route_dispatcher_native as native
        with source.historical_view(self.root,self.out) if self.installed else nullcontext():row=native.qualify(self.root,self.out)
        self.assertEqual((row['cases_per_profile'],row['profiles'],row['effective_controls']),(1824,3,7))


if __name__=='__main__':unittest.main()
