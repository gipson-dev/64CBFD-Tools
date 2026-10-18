"""Exhaustive neighbor categories, byte ABI, priority, and whole live C caller."""
import csv
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_record_neighbor_selector as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_view_point_projection_oracle as base
from tools.tests.test_game_record_heading_setter import SetterOracle
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command

put,read,STACK=base.put,base.read,base.STACK
RECORDS,ACTOR_TABLE,ACTOR_ROWS=0x30000,0x800872A0,0x50000
HEADER='#include <ultra64.h>\nextern u8 *D_800D2350;\n'


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x400<=a<STACK+0x400}
def signed8(v):return ((v&255)^128)-128


def fixture(code=0,excluded=3,index=7,alternate=0,override=256,table=source.TABLE):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x400)}
    memory.update({RECORDS+i:0xA5 for i in range(4096)})
    put(memory,table,RECORDS);row=RECORDS+(index&255)*16
    for i in range(5):
        digit=code%6;code//=6;candidate=255 if digit==0 else (excluded&255) if digit==1 else 8+i
        if digit>=2:
            put(memory,RECORDS+candidate*16+14,128 if digit==2 else 0,1)
            put(memory,RECORDS+candidate*16+15,max(0,digit-3),1)
        put(memory,row+9+i,candidate,1)
    if override<256:
        put(memory,row+9,override,1);put(memory,RECORDS+override*16+14,0,1);put(memory,RECORDS+override*16+15,255,1)
    return memory,(excluded&0xFFFFFFFF,index&0xFFFFFFFF,alternate&0xFFFFFFFF)


def reference(memory,args,table=source.TABLE):
    bank=read(memory,table);trace=[(table,4,bank)];row=bank+(args[1]&255)*16;eligible=[]
    for i in range(5):
        candidate=read(memory,row+9+i,1);trace.append((row+9+i,1,candidate))
        if candidate in (255,args[0]&255):continue
        entry=bank+candidate*16;disabled=read(memory,entry+14,1);trace.append((entry+14,1,disabled))
        if disabled:continue
        kind=read(memory,entry+15,1);trace.append((entry+15,1,kind));eligible.append((candidate,kind))
    requested=1 if args[2]&255 else 2
    nonzero=[c for c,k in eligible if k!=requested and k!=0]
    zeros=[c for c,k in eligible if k==0]
    fallback=[c for c,k in eligible if k==requested]
    return nonzero[-1] if nonzero else zeros[0] if zeros else fallback[-1] if fallback else 255,trace


class NeighborOracle(SetterOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY,connected=None):
        self.setter_reads=[];self.setter_writes=[];self.forwarded=[]
        base.PointProjectionOracle.__init__(self,words,memory,args,[],phase,entry,connected)
        self.initial_f=list(self.f)

    def record_call(self,target):
        if target!=source.ENTRY:raise AssertionError('Unexpected neighbor selector call')
        self.forwarded.append(self.arguments(3))

    def hook(self,target):raise AssertionError('Neighbor selector must not use opaque helpers')


def reachable(words):
    pending=[0];seen=set()
    while pending:
        i=pending.pop()
        if i in seen:continue
        if not 0<=i<len(words):raise AssertionError('Control flow outside neighbor slot')
        seen.add(i);w=words[i];op,rs,rt=w>>26,(w>>21)&31,(w>>16)&31
        if op in (4,5,20,21):
            seen.add(i+1);pending.append(i+1+((w&65535)^32768)-32768)
            if not (op==4 and rs==rt==0):pending.append(i+2)
        elif op==0 and w&63==8:seen.add(i+1)
        else:pending.append(i+1)
    return seen


def controls():
    b=source.SELECTED
    return {
        'wrong-requested-class':b.replace('requested = 1;', 'requested = 2;'),
        'ignore-first-excluded':b.replace('excluded != firstCandidate','1'),
        'ignore-first-disabled':b.replace('firstEntry[0xE] == 0','1'),
        'overwrite-with-zero':b.replace('current == 0xFF || kind != 0','1').replace('current == 0xFF || secondKind != 0','1'),
        'keep-first-nonzero':b.replace('current == 0xFF || kind != 0','current == 0xFF').replace(
            'current == 0xFF || secondKind != 0','current == 0xFF'),
        'wrong-stride':b.replace('* 0x10','* 0xF'),
        'signed-return':b.replace('return selected;', 'return (s8)selected;'),
        'no-requested-fallback':b.replace('selected = fallback & 0xFF;', 'selected = 0xFF;'),
        'first-requested-fallback':b.replace('fallback = candidate & 0xFF;', 'if (fallback == 0xFF) fallback = candidate & 0xFF;').replace(
            'fallback = second & 0xFF;', 'if (fallback == 0xFF) fallback = second & 0xFF;'),
    }


NATIVE=HEADER+r'''
u8 *D_800D2350;static u8 records[4096],before[4096];
s32 func_150888A8(u8,u8,s8);
static u32 count;
static int check(u32 code,u32 excluded,u32 index,u32 mode,u32 override){
 u32 i,d,id,row=(index&255u)*16u,requested=mode?1u:2u,zero=255,other=255,last=255,wanted; s32 got;
 for(i=0;i<4096;i++)records[i]=0xA5;
 for(i=0;i<5;i++){d=code%6;code/=6;id=d==0?255:d==1?excluded:8+i;
 if(d>=2){records[id*16+14]=d==2?128:0;records[id*16+15]=d>=3?(u8)(d-3):0;}
 records[row+9+i]=(u8)id;}
 if(override<256){records[row+9]=(u8)override;records[override*16+14]=0;records[override*16+15]=255;}
 for(i=0;i<5;i++){id=records[row+9+i];if(id==255||id==excluded||records[id*16+14])continue;
 d=records[id*16+15];if(d==requested)last=id;else if(d)other=id;else if(zero==255)zero=id;}
 wanted=other!=255?other:zero!=255?zero:last;for(i=0;i<4096;i++)before[i]=records[i];D_800D2350=records;
 got=func_150888A8((u8)excluded,(u8)index,(s8)mode);
 if(got!=(s32)wanted||D_800D2350!=records)return 23;
 for(i=0;i<4096;i++)if(records[i]!=before[i])return 23;count++;return 0;}
static int run(void){u32 code,m,v;int s;
 if(sizeof(void*)!=4)return 29;
 for(code=0;code<7776;code++)for(m=0;m<2;m++){s=check(code,3,7,m,256);if(s)return s;}
 for(v=0;v<256;v++){
 s=check(5432,v,7,1,256);if(s)return s;s=check(5432,3,v,0,256);if(s)return s;
 s=check(5432,3,7,v,256);if(s)return s;
 for(m=0;m<2;m++){s=check(3,m?255:3,7,1,v);if(s)return s;}}
 return count==16832?0:28;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class NeighborSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD;cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin');cls.truth=struct.unpack_from('>88I',cls.rom,source.ROM)
        cls.fixed=source.normalized(cls.words)

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,args,phase=0,bodies=None,entry=source.ENTRY,table=source.TABLE):
        wanted,reads=reference(memory,args,table);models=[]
        for w in bodies or (self.words,self.fixed,self.truth):
            m=NeighborOracle(w,memory,args,phase,entry).run()
            self.assertEqual((public(m.memory),m.r[2],m.setter_reads),(public(memory),wanted,reads))
            self.assertFalse(m.setter_writes);self.assertFalse(m.calls);self.assertEqual(m.f,m.initial_f)
            for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            models.append(m)
        self.assertEqual((models[1].r,models[1].f),(models[2].r,models[2].f));return models

    def test_01_all_neighbor_categories_byte_boundaries_and_reachable_words(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['neighbors']),(88,8,60,72))
        self.assertEqual(self.fixed,list(self.truth));seen=set();count=0
        for code,mode in itertools.product(range(7776),(0,1)):
            memory,args=fixture(code,alternate=mode);models=self.compare(memory,args,mode*8);seen.update(models[0].visits);count+=1
        for v,which in itertools.product(range(256),range(3)):
            values=[3,7,1];values[which]=v;memory,args=fixture(5432,*values);self.compare(memory,args,(v&1)*8);count+=1
        for v in range(256):
            memory,args=fixture(3,override=v);self.compare(memory,args);count+=1
        for a,b,c in itertools.product((0x100,0xFFFFFF03),(0x107,0xFFFFFFFF),(0x100,0xFFFFFF80)):
            memory,args=fixture(5432,a,b,c);self.compare(memory,args);count+=1
        expected=reachable(self.truth);self.assertEqual(set(range(88))-expected,{35,59,79})
        self.assertEqual({(pc-source.ENTRY)//4 for pc in seen},expected)
        self.receipt('guest',three_way_cases=count,category_combinations=7776,both_modes=True,
            all256_each_input_bytes=True,all256_candidate_IDs=True,wide_word_inputs=8,
            reachable_words=len(expected),unreachable_tail_duplicates=[35,59,79],exact_reads_and_no_public_writes=True)

    def test_02_native32_O2_O0_UBSan_and_controls(self):
        harness=self.out/'native-driver.c';harness.write_text(NATIVE)
        for name,opt,body,status in [('O2','-O2',source.SELECTED,0),('O0','-O0',source.SELECTED,0)]+[
                (n,'-O2',b,23) for n,b in controls().items()]:
            # The disabled-fallback control intentionally leaves its last-assigned local unused.
            if name=='no-requested-fallback':body=body.replace('    return selected;', '    (void)fallback;\n    return selected;')
            unit=self.out/('native-'+name+'.c');unit.write_text(HEADER+body);exe=unit.with_suffix('')
            c=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),str(harness),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(c.returncode,0,c.stderr)
            self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=180).returncode,status,name)
        self.receipt('native',cases_per_profile=16832,UBSan=True,controls=len(controls()),full4096_byte_table_unchanged=True,
            actual_byte_prototype=True,all256_input_bytes_and_candidate_IDs=True)

    def test_03_guest_controls_change_full_return_values(self):
        for name,body in controls().items():
            obj,diagnostics=source.compile_owner(self.root,self.out,HEADER+body,'negative-'+name);self.assertFalse(diagnostics)
            data,functions=source.link_owner(self.root,self.out,obj,source.OWNER);f=functions[source.FUNCTION]
            words=struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])
            cases=itertools.chain((fixture(3,override=3),),
                (fixture(code,alternate=mode) for code,mode in itertools.product(range(7776),(0,1))))
            for memory,args in cases:
                wanted,_=reference(memory,args)
                m=NeighborOracle(words,memory,args).run()
                if m.r[2]!=wanted:break
            else:self.fail('Ineffective neighbor control: '+name)
        self.receipt('controls',observable_guest_controls=len(controls()),native_wrong_result_status=23)

    def test_04_independent_original_raw_padded_rebased_links(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-neighbor',source.raw_text(self.root/'conker/asm/B3020.s'),source.FUNCTION)
        raws=[]
        for obj in (self.obj,self.padded):
            text,functions,rel=source.parse_object(obj);f=functions[source.FUNCTION]
            raws.append((text[f['value']:f['value']+f['size']],{a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}))
        count=0
        for k,(entry,table) in enumerate(((source.ENTRY,source.TABLE),(0x16218004,0x12347FFC),(0x18FFF000,0x12348004))):
            objects=[original]
            for label,(raw,bindings) in zip(('raw','padded'),raws):
                text,missing=emit_function(raw,dict(value=0,size=len(raw)),bindings,source.FUNCTION,dict(D_800D2350=table));self.assertFalse(missing)
                path=self.out/('rebase-%s-%d.s'%(label,k));path.write_text(text);obj=path.with_suffix('.o')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],check=True,capture_output=True);objects.append(obj)
            bodies=[]
            for j,obj in enumerate(objects):
                script=self.out/('rebase-%d-%d.ld'%(k,j));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=D_800D2350=0x%X'%table,'-o',str(elf),str(obj)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>88I',sections(elf)['.text'][1])))
            self.assertEqual(bodies[0],bodies[2]);self.assertEqual(source.normalized(bodies[1]),bodies[0])
            for code,mode,phase in itertools.product((0,3,4,5,7775,5432),(0,1,0x100,0xFFFFFF80),(0,8)):
                memory,args=fixture(code,alternate=mode,table=table)
                self.compare(memory,args,phase,(bodies[1],bodies[2],bodies[0]),entry,table);count+=1
        self.receipt('rebases',independent_original_raw_padded_links=9,three_way_cases=count,two_bindings=True)

    def test_05_all_access_fault_prefixes(self):
        count=0
        for code,mode,phase in itertools.product((0,1,2,3,4,5,5432,7775),(0,1),(0,8)):
            memory,args=fixture(code,alternate=mode);full=NeighborOracle(self.fixed,memory,args,phase).run()
            for fault in range(full.all_accesses):
                models=[]
                for w in (self.words,self.fixed,self.truth):
                    m=NeighborOracle(w,memory,args,phase);m.access_fault=fault
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual((models[0].memory,models[0].setter_reads),(models[2].memory,models[2].setter_reads))
                self.assertEqual(base.state(models[1]),base.state(models[2]));count+=1
        self.receipt('faults',states=32,equal_public_and_stack_memory_prefixes=count,full_normalized_retail_state=True,
            raw_dead_GPR_values_not_claimed=True,hardware_fault_emulation_not_claimed=True)

    def test_06_whole_live_C_caller_executes_two_queries_and_stores(self):
        image=source.raw_read(self.out/'before-01');at=source.elf_slot_offset(image,0x15087DCC,136)
        caller=struct.unpack_from('>34I',image,at);self.assertEqual(image[at:at+136],self.rom[0xB527C:0xB5304]);count=0
        for code,tag,old,index,active,phase in itertools.product((0,5432,7775),(0,1,-128),(0,1),(0,3),(False,True),(0,8)):
            memory,_=fixture(code,excluded=3,index=7,alternate=1)
            put(memory,ACTOR_TABLE,ACTOR_ROWS if active else 0)
            for i in range(4*0x84):memory[ACTOR_ROWS+i]=0xA5
            row=ACTOR_ROWS+index*0x84;put(memory,row+0x2F,old,1);put(memory,row+0x2B,3,1);put(memory,row+0x2C,7,1)
            expected=dict(memory);calls=[]
            if active and old!=tag:
                if tag:
                    args=(3,7,1);first,_=reference(expected,args);calls.append(args);put(expected,row+0x2D,first,1)
                    args=(7,first&255,1);second,_=reference(expected,args);calls.append(args);put(expected,row+0x2E,second,1)
                put(expected,row+0x2F,tag,1)
            for w in (self.words,self.fixed):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+352,4),w))
                m=NeighborOracle(caller,memory,(index,tag&0xFFFFFFFF),phase,0x15087DCC,connected).run()
                self.assertEqual((public(m.memory),m.forwarded),(public(expected),calls));self.assertFalse(m.calls)
            count+=1
        self.receipt('caller',paired_whole_C_caller_cases=count,caller_words=34,two_real_queries_and_low_byte_stores=True,
            raw_caller_and_relative_bindings_unchanged=True,full_gameplay_not_claimed=True)

    def test_07_fail_closed_words_bindings_guards_inputs_and_installation(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION];raw,bindings=source.checked_object(self.obj)
        for i in range(88):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for i in bindings:
            bad=dict(rel);bad[f['value']+i]=[]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        reader=csv.DictReader(io.StringIO(source.raw_read(self.out/'qualified-guards.csv').decode()));all_rows=list(reader)
        for row in source.owner_guards(raw,bindings):
            path=self.out/'bad-guard.csv';wrong=[dict(r,expected='0x%08X'%(int(r['expected'],16)^1))
                if (r['filename'],r['function'],r['offset'])==(row['filename'],row['function'],row['offset']) else r for r in all_rows]
            with path.open('w',newline='') as stream:
                w=csv.DictWriter(stream,fieldnames=reader.fieldnames);w.writeheader();w.writerows(wrong)
            with self.assertRaisesRegex(ValueError,source.FUNCTION):
                source.emit_padded_assembly(self.obj,self.root/'conker/asm/B3020.s',filename=source.OWNER,word_patches_path=path)
        with source.historical_view(self.root,self.out):
            read_bytes=Path.read_bytes
            for index,p in enumerate(source.INPUTS):
                for path in (self.root/p,self.out/('before-%02d'%index)):
                    with patch.object(Path,'read_bytes',lambda x:read_bytes(x)+b'\n' if x==path else read_bytes(x)):
                        with self.assertRaises(ValueError):source.freeze(self.root,self.out)
            with self.assertRaisesRegex(RuntimeError,'cannot nest'):
                with source.historical_view(self.root,self.out):pass
        self.assertEqual(source.verify(self.root,self.out),self.stage)
        if self.stage=='after':self.assertEqual(source.audit(self.root,self.out)['functions'],6057)


if __name__=='__main__':unittest.main()
