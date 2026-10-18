"""Ordered queue reloads, wrap/alias boundaries, closed guards and linked image."""
from contextlib import nullcontext
import csv
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_object_command_enqueue as source
from tools.tests.test_game_route_neighbor_preference import NeighborOracle
from tools.tests import game_view_point_projection_oracle as base
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_route_projection_setup as parent
from tools.tests.test_game_route_projection_lifetime_fit import cases as parent_cases
from tools.experiments import game_route_projection_node_expression_fit as nodes

GLOBAL,TABLE,OTHER,OBJECT=0x800DC2B0,0x30000,0x40000,0x50000
put,read=base.put,base.read


def fixture(bank=0,cursor=0,command=0x12345678,payload=0x87654321,alias=0,global_address=GLOBAL):
    table=TABLE;memory={base.STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x500)}
    if alias==1:table=OBJECT+0x23C;bank=0;cursor=0;command=0x00010000
    if alias==2:table=global_address;bank=0;cursor=0;command=OTHER
    if alias==3:bank=0;cursor=21
    if alias==4:table=global_address-4;bank=0;cursor=0;payload=OTHER
    if alias==5:table=OBJECT+0x238;bank=0;cursor=0;payload=0x00010000
    if alias==6:table=base.STACK-0x200
    if alias==7:bank=0;cursor=0x80000015
    for address,length in ((table,0xC0),(table+176,0xC0),(OTHER,0xC0),(OBJECT,0x400),(global_address,4)):
        memory.update({(address+i)&0xFFFFFFFF:0xA5 for i in range(length)})
    for address in (table+bank*176,table+176,OTHER):
        put(memory,address+0xAC,0)
    put(memory,table+bank*176+0xAC,cursor)
    put(memory,OBJECT+0x23D,bank,1);put(memory,global_address,table)
    for address in (table+bank*176+cursor*8,table+176,OTHER):
        for i in range(8):memory.setdefault((address+i)&0xFFFFFFFF,0xA5)
    return memory,(OBJECT,command&0xFFFFFFFF,payload&0xFFFFFFFF)


def reference(initial,args,global_address=GLOBAL):
    memory=dict(initial);trace=[];obj,command,payload=args
    def get(address,size=4):
        address&=0xFFFFFFFF;value=read(memory,address,size);trace.append(('R',address,size,value));return value
    def store(address,value):
        address&=0xFFFFFFFF;put(memory,address,value);trace.append(('W',address,4,value&0xFFFFFFFF))
    def row():
        bank=get(obj+0x23D,1);table=get(global_address)
        return (table+bank*176)&0xFFFFFFFF
    queue=row();store(queue+get(queue+0xAC)*8,command)
    queue=row();store(queue+get(queue+0xAC)*8+4,payload)
    queue=row();store(queue+0xAC,get(queue+0xAC)+1)
    queue=row()
    if get(queue+0xAC)==20:store(queue+0xAC,0)
    return memory,trace


def corpus():
    for bank,cursor,command,payload in itertools.product((0,1,127,128,254,255),
            (0,1,18,19,20,21,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,0x80000000,0xFFFFFFFF),(0,0x12345678)):
        yield fixture(bank,cursor,command,payload)
    for alias,payload in itertools.product(range(1,8),(0,19,20,0xFFFFFFFF)):
        yield fixture(payload=payload,alias=alias)


def controls():
    body=source.SELECTED
    return {
        'signed-bank':body.replace('object[0x23D]','*(s8 *)(object + 0x23D)'),
        'wrong-stride':body.replace('0xB0','0xA8'),
        'wrap-too-early':body.replace('== 20','== 19'),
        'wrap-out-of-range':body.replace('== 20','>= 20'),
        'missing-increment':body.replace('+= 1','+= 0'),
        'wrong-payload-offset':body.replace('* 8 + 4','* 8 + 0'),
        'cached-row':body.replace('    queue = D_800DC2B0 + object[0x23D] * stride;\n','',3).replace(
            '    u8 *queue;','    u8 *queue = D_800DC2B0 + object[0x23D] * stride;'),
    }


NATIVE='''#include <ultra64.h>
u8 *D_800DC2B0;
'''+source.SELECTED+r'''
static u8 data[0xB000],saved[0xB000],object[0x400];
static int run(void){u32 bank,cursor,i,cases=0;u8 *queue;u32 command,payload;
 for(bank=0;bank<256;bank++)for(cursor=0;cursor<20;cursor++){
  for(i=0;i<sizeof(data);i++)data[i]=saved[i]=(u8)(i*17+0xA5);
  D_800DC2B0=data;object[0x23D]=(u8)bank;queue=data+bank*0xB0;
  *(u32 *)(queue+0xAC)=cursor;*(u32 *)(saved+bank*0xB0+0xAC)=cursor;
  command=0x80000000U+bank*257+cursor;payload=0xF1234567U+cursor;
  *(u32 *)(saved+bank*0xB0+cursor*8)=command;
  *(u32 *)(saved+bank*0xB0+cursor*8+4)=payload;
  *(u32 *)(saved+bank*0xB0+0xAC)=cursor==19?0:cursor+1;
  func_1512D560(object,(s32)command,(void *)payload);
  for(i=0;i<sizeof(data);i++)if(data[i]!=saved[i])return 23;
  if(D_800DC2B0!=data||object[0x23D]!=bank)return 24;cases++;
 }
 return cases==5120?0:25;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''


class EnqueueOracle(NeighborOracle):
    def execute(self,word):
        if word>>26!=32:return super().execute(word)
        old=self.own_instruction;self.own_instruction=True;self.dispatched_word=word
        try:
            rs,rt=word>>21&31,word>>16&31;offset=((word&65535)^32768)-32768
            self.r[rt]=((self.get((self.r[rs]+offset)&0xFFFFFFFF,1)^128)-128)&0xFFFFFFFF
            self.r[0]=0
        finally:self.own_instruction=old


class EnqueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        owner='conker/src/game/'+source.OWNER+'.c'
        cls.installed=bool(source.AFTER) and source.raw_read(cls.root/owner)==source.expected_inputs(cls.root,cls.out)[owner]
        with source.historical_view(cls.root,cls.out) if cls.installed else nullcontext():
            cls.obj,cls.padded,cls.raw,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin')
        cls.truth=list(struct.unpack_from('>41I',cls.rom,source.ROM))

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def machine(self,words,memory,args,phase=0,entry=source.ENTRY):
        return EnqueueOracle(words,memory,args,phase,entry)

    def test_01_complete_body_owner_and_all_memory_aliases(self):
        self.assertEqual((self.row['words'],self.row['differences'],self.row['neighbors']),(41,30,3))
        count=0;visits=[set(),set()];changed_banks=changed_tables=changed_cursor=0
        for memory,args in corpus():
            expected,trace=reference(memory,args)
            changed_banks+=read(expected,OBJECT+0x23D,1)!=read(memory,OBJECT+0x23D,1)
            changed_tables+=read(expected,GLOBAL)!=read(memory,GLOBAL)
            changed_cursor+=read(memory,read(memory,GLOBAL)+0xAC)==21
            for index,words in enumerate((self.raw,self.truth)):
                m=self.machine(words,memory,args,(count&1)*8).run()
                self.assertEqual((m.memory,m.trace),(expected,trace),(count,index));self.assertEqual(m.calls,[])
                visits[index].update(m.visits)
            count+=1
        self.assertEqual(count,352)
        self.assertTrue(changed_banks and changed_tables and changed_cursor)
        self.assertEqual([len(v) for v in visits],[41,41])
        self.receipt('guest',paired_cases=count,full_memory_ordered_trace_equal=True,all_words_visited=True,
            effective_bank_changes=changed_banks,effective_table_changes=changed_tables,frame=0)

    def test_02_every_fired_memory_fault_prefix(self):
        count=0
        for alias,phase in itertools.product(range(8),(0,8)):
            memory,args=fixture(cursor=19,alias=alias);complete=self.machine(self.truth,memory,args,phase).run()
            for cut in range(complete.all_accesses):
                stopped=[]
                for words in (self.raw,self.truth):
                    m=self.machine(words,memory,args,phase);m.access_fault=cut
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,cut);stopped.append(m)
                self.assertEqual((stopped[0].memory,stopped[0].trace),(stopped[1].memory,stopped[1].trace))
                count+=1
        self.receipt('fault-prefixes',paired_fired_prefixes=count,dead_caller_GPRs_not_compared=True)

    def test_03_independent_rebases_and_symbolic_controls(self):
        raw,bindings=source.checked_object(self.obj);count=0
        normalized,moved=source.normalize(raw,bindings)
        for global_address,entry in itertools.product((0x800D7FFC,0x800D8000,0x800E8004,0x12000),(0x15000000,0x16007FFC)):
            truth=list(self.truth)
            truth[0]=(truth[0]&0xFFFF0000)|((global_address+0x8000)>>16&65535)
            truth[1]=(truth[1]&0xFFFF0000)|(global_address&65535)
            source.normalization_proof(raw,bindings,truth,global_address)
            memory,args=fixture(cursor=19,alias=2,global_address=global_address);expected,trace=reference(memory,args,global_address)
            for words in (source.relocate(raw,bindings,global_address),source.relocate(normalized,moved,global_address),truth):
                m=self.machine(words,memory,args,entry=entry).run();self.assertEqual((m.memory,m.trace),(expected,trace))
            count+=1
        bad=list(self.raw);bad[21]^=4
        self.assertNotEqual(source.symbolic_paths(bad),source.symbolic_paths(self.truth))
        self.receipt('rebases',independent_symbol_and_function_rebases=count,symbolic_paths=2,
            HI16_carry_and_LO16_sign=True,changed_payload_store_effective=True)

    def test_04_compiled_semantic_negatives(self):
        witnesses={};fixtures=list(corpus())
        with source.historical_view(self.root,self.out) if self.installed else nullcontext():
            for name,body in controls().items():
                _,words,row=source.measure(self.root,self.out,'negative-'+name,body);self.assertFalse(row['diagnostics'])
                for index,(memory,args) in enumerate(fixtures):
                    expected,trace=reference(memory,args)
                    try:m=self.machine(words,memory,args).run()
                    except AssertionError as error:
                        if not str(error).startswith("('unmapped "):raise
                        witnesses[name]=dict(case=index,fault=str(error));break
                    if (m.memory,m.trace)!=(expected,trace):witnesses[name]=index;break
                else:self.fail('Ineffective enqueue control: '+name)
                if name=='cached-row':
                    memory,args=fixture(alias=1);expected,_=reference(memory,args)
                    actual=self.machine(words,memory,args).run()
                    self.assertNotEqual(actual.memory,expected)
                    witnesses['cached-row-public-alias']=True
        self.receipt('controls',witnesses=witnesses,compiled_controls=len(controls()))

    def test_05_native32_all_banks_and_valid_cursor_positions(self):
        path=self.out/'native.c';path.write_text(NATIVE)
        for name,opt,valid in (('o0','-O0',False),('o2','-O2',False),('ubsan','-O2',True)):
            exe=self.out/('native-'+name)
            subprocess.run([*native_command(opt,valid),'-mstackrealign','-fno-strict-aliasing',str(path),'-o',str(exe)],
                cwd=self.root,check=True,capture_output=True,text=True)
            subprocess.run([str(exe)],check=True,capture_output=True)
        control=self.out/'native-negative.c';control.write_text(NATIVE.replace(source.SELECTED,controls()['wrap-too-early']))
        exe=self.out/'native-negative'
        subprocess.run([*native_command('-O2',True),'-mstackrealign','-fno-strict-aliasing',str(control),'-o',str(exe)],
            cwd=self.root,check=True,capture_output=True,text=True)
        self.assertEqual(subprocess.run([str(exe)],capture_output=True).returncode,23)
        self.receipt('native32',cases_per_build=5120,builds=['O0','O2','O2+UBSAN'],valid_domain=True,
            high_pointer_bits_passed_not_dereferenced=True,forged_alias_cases_guest_only=True,
            effective_compiled_native_wrap_control=True)

    def test_06_real_projection_parent_and_selector(self):
        parent_words=list(struct.unpack_from('>321I',self.rom,parent.source.ROM));count=0
        helpers={}
        for entry,length in parent.HELPERS.items():
            helpers.update(zip(range(entry,entry+length*4,4),struct.unpack_from('>%dI'%length,self.rom,entry-0x14FD2B50)))
        for memory,args in parent_cases():
            expected,calls,_=parent.reference(memory,args)
            for words in (self.raw,self.truth):
                connected=dict(helpers);connected.update(zip(range(source.ENTRY,source.ENTRY+164,4),words))
                m=parent.ProjectionOracle(parent_words,memory,args,connected,(count&1)*8).run()
                self.assertEqual((parent.public(m.memory),m.calls),(parent.public(expected),calls))
            count+=1
        self.assertEqual(count,575)
        self.receipt('connected-parent',paired_cases=count,actual_retail_parent_and_selector=True,
            raw_and_normalized_enqueue=True,production_parent_still_stub=True,gameplay_claim=False)

    def test_07_inputs_bindings_and_word_guards_fail_closed(self):
        raw,bindings=source.checked_object(self.obj);text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION]
        for at in range(f['value'],f['value']+f['size'],4):
            bad=bytearray(text);bad[at]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)),self.assertRaises(ValueError):source.checked_object(self.obj)
        for at in rel:
            if not f['value']<=at<f['value']+f['size']:continue
            bad=dict(rel);bad.pop(at)
            with patch.object(source,'parse_object',return_value=(text,functions,bad)),self.assertRaises(ValueError):source.checked_object(self.obj)
        with source.historical_view(self.root,self.out) if self.installed else nullcontext():
            original=Path.read_bytes;checks=0
            for index,name in enumerate(source.INPUTS):
                for target in (self.root/name,self.out/('before-%02d'%index)):
                    def changed(path,*args,**kwargs):
                        data=original(path,*args,**kwargs);return data+b'\0' if path==target else data
                    with patch.object(Path,'read_bytes',changed),self.assertRaises(ValueError):source.freeze(self.root,self.out)
                    checks+=1
        self.receipt('input-controls',raw_words=41,removed_bindings=2,changed_live_and_snapshot_inputs=checks)

    def test_08_installed_image_gate_when_applicable(self):
        if not self.installed:self.skipTest('Pre-install qualification; exact prediction is checked separately')
        self.assertTrue(source.audit(self.root,self.out)['only_target_code_and_size_changed'])

    def test_09_rejected_node_expression_shapes_and_sampled_public_behavior(self):
        with source.historical_view(self.root,self.out) if self.installed else nullcontext():
            rows=nodes.audit(self.root,self.root/nodes.BUILD)
        helpers={};count=0
        for entry,length in parent.HELPERS.items():
            helpers.update(zip(range(entry,entry+length*4,4),struct.unpack_from('>%dI'%length,self.rom,entry-0x14FD2B50)))
        for row in rows:
            obj=self.root/nodes.BUILD/(row['name']+'.o')
            data,functions=nodes.source.neighbor.baseline.model.link_owner(self.root,self.root/nodes.BUILD,obj,nodes.source.OWNER)
            f=functions[nodes.source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            self.assertNotEqual(len(words),321)
            for state,position,flag in itertools.product((2,3,0),range(8),(0,64)):
                memory,args=parent.fixture(state,position,flag=flag);expected,calls,_=parent.reference(memory,args)
                m=parent.ProjectionOracle(words,memory,args,helpers,(count&1)*8).run()
                self.assertEqual((parent.public(m.memory),m.calls),(parent.public(expected),calls));count+=1
        self.assertEqual(count,192)
        self.receipt('node-rejections',rejected_screens=len(rows),sampled_public_cases=count,
            neighbors_preserved_each=72,matching_credit=0)

    def test_10_each_guard_expectation_and_relocation_is_effective(self):
        path=self.out/'qualified-guards.csv';reader=csv.DictReader(io.StringIO(path.read_text()));rows=list(reader)
        positions=[i for i,r in enumerate(rows) if (r['filename'],r['function'])==(source.OWNER,source.FUNCTION)]
        self.assertEqual(len(positions),30);bad=self.out/'negative-guard.csv'
        def reject(changed):
            stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=reader.fieldnames,lineterminator='\n')
            writer.writeheader();writer.writerows(changed);bad.write_text(stream.getvalue())
            with self.assertRaises((ValueError,SystemExit)):
                source.emit_padded_assembly(self.obj,self.root/'conker/asm/15AA10.s',filename=source.OWNER,word_patches_path=bad)
        for index in positions:
            changed=[dict(r) for r in rows];changed[index]['expected']='0x%08X'%(int(changed[index]['expected'],0)^1)
            reject(changed)
        for index in positions[:2]:
            changed=[dict(r) for r in rows];changed[index]['expected_relocations']='-';reject(changed)
        self.receipt('guard-controls',changed_expected_words=30,changed_relocation_expectations=2)


if __name__=='__main__':unittest.main()
