"""Closed isolated match and explicit experimental installation/proof boundary."""
import hashlib
import itertools
import json
from pathlib import Path
import re
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_spline_payload_layout as layout
from tools.experiments import game_route_spline_payload_roles as roles
from tools.pad_generated_object import emit_padded_assembly
from tools.tests import test_game_route_spline_payload_recovery as guest

DATA={'COUNT':'D_80087290','GLOBAL':'D_800D2350','MODE':'D_800D23A8','FRAMES':'D_800BE9E4',
    'STOP_VALUE':'D_8009DA0C','RATE':'D_8009DA10','SCALE':'D_8009DA18','QUEUES':'D_800DC2B0'}
CALLS={'POSITION':'func_15086CBC','SELECTOR':'func_1508907C','ENQUEUE':'func_1512D560',
    'SPLINE':'func_150497E0','SIN':'sinf','COS':'cosf'}
ANCHORS={name:getattr(guest,key) for key,name in dict(DATA,**CALLS).items()}


def retail_bindings(root):
    body=(root/'conker/asm/B3020.s').read_text().split('glabel func_150896EC\n')[1].split('endlabel func_150896EC')[0]
    result={};words=[]
    for line in body.splitlines():
        m=re.search(r'/\* [0-9A-F]+ ([0-9A-F]+) ([0-9A-F]{8}) \*/\s*(.*)',line)
        if not m:continue
        index=(int(m[1],16)-layout.source.source.ENTRY)//4;words.append(int(m[2],16))
        binding=re.search(r'%((?:hi)|(?:lo))\((\w+)\)',m[3])
        if binding:result[index]=('R_MIPS_HI16' if binding[1]=='hi' else 'R_MIPS_LO16',binding[2])
        elif call:=re.search(r'\bjal\s+(\w+)',m[3]):result[index]=('R_MIPS_26',call[1])
    return words,result


def independent_rebase(words,bindings,anchors):
    result=list(words)
    for index,(kind,name) in bindings.items():
        value=anchors[name]
        immediate=(value>>2)&0x3FFFFFF if kind=='R_MIPS_26' else ((value+32768)//65536)&65535 if kind=='R_MIPS_HI16' else value&65535
        mask=0xFC000000 if kind=='R_MIPS_26' else 0xFFFF0000
        result[index]=result[index]&mask|immediate
    return result


def state(m):return m.memory,m.r,m.f,m.trace,m.calls,m.events,m.current_pc,m.delay_of,m.all_accesses,m.dispatched_word


def extrapolation_terms(words,registers):
    floats=[('incoming-float',i) for i in range(32)];reads=[];stores={}
    for word in words:
        op,rs,rt=word>>26,word>>21&31,word>>16&31
        address=registers.get(rs,0)+(((word&65535)^32768)-32768)
        if op==49:
            if address in stores:raise ValueError('Read crossed an aliasing write')
            floats[rt]=('read',address);reads.append(address)
        elif op==57:
            if address in stores:raise ValueError('Duplicate extrapolation destination')
            stores[address]=floats[rt]
        elif op==17 and rs==16 and word&63 in (0,1):
            fs,fd=word>>11&31,word>>6&31;left,right=floats[fs],floats[rt]
            floats[fd]=('sub',left,right) if word&63==1 else ('add',*sorted((left,right),key=repr))
        else:raise ValueError('Unexpected extrapolation instruction')
    if set(reads)&set(stores):raise ValueError('History and outputs alias')
    return stores,sorted(reads)


class SplinePayloadLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/roles.BUILD
        cls.obj,cls.raw_words,_=layout.source.qualify(cls.root,cls.out,joint=True)
        cls.raw,cls.bindings=layout.source.checked(cls.obj,True)
        cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.words=layout.relocate(cls.normalized,cls.moved,ANCHORS)
        rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.truth=list(struct.unpack_from('>305I',rom,layout.source.source.ROM))
        cls.assembly,cls.retail_bindings=retail_bindings(cls.root)
        elf=(cls.root/'conker/build/conker.us.elf').read_bytes();cls.helper_bodies={};cls.helpers={}
        for entry,count in guest.HELPERS.items():
            at=layout.source.source.prior.prior.elf_slot_offset(elf,entry,count*4)
            if elf[at:at+count*4]!=rom[entry-0x14FD2B50:entry-0x14FD2B50+count*4]:raise ValueError('Helper differs from retail')
            body=list(struct.unpack_from('>%dI'%count,elf,at));cls.helper_bodies[entry]=body
            cls.helpers.update(zip(range(entry,entry+count*4,4),body))

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_all_305_words_and_independent_retail_bindings(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('Recipe must not read files')),\
                patch.object(Path,'read_text',side_effect=AssertionError('Recipe must not read text')):
            normalized,moved=layout.normalize(self.raw,self.bindings)
        self.assertEqual(self.words,self.truth);self.assertEqual(self.assembly,self.truth)
        self.assertEqual(moved,{index*4:[entry] for index,entry in self.retail_bindings.items()})
        self.assertEqual(hashlib.sha256(normalized).hexdigest(),layout.NORMALIZED_SHA)
        self.assertEqual(sorted(layout.origins()),list(range(305)))
        self.assertEqual(sum(self.raw_words[i]!=v for i,v in enumerate(self.truth)),140)
        self.assertEqual(self.words[0]&65535,0xFF08)
        self.receipt('isolated-match',raw_words=305,normalized_words=305,frame=248,retail_differences=0,
            unique_source_origins=305,omitted_words=0,inserted_words=0,bindings=33,
            file_free_recipe=True,normalized_SHA256=layout.NORMALIZED_SHA,installed=False,matching_credit=0)

    def test_02_complete_guest_states_real_helpers_and_literal_calls(self):
        count=0
        for kw in guest.cases():
            initial,args=guest.fixture(**kw)
            a,b=[guest.PayloadOracle(w,initial,args,self.helpers,retail=True,literal=True).run() for w in (self.words,self.truth)]
            self.assertEqual(state(a),state(b),kw);count+=1
        for stop,bank in itertools.product((1,-1),(0,1)):
            initial,args=guest.fixture(stop=stop,bank=bank,alias=2)
            a,b=[guest.PayloadOracle(w,initial,args,self.helpers,retail=True,literal=True).run() for w in (self.words,self.truth)]
            self.assertEqual(state(a),state(b))
        self.assertEqual(count,1069)
        self.receipt('normalized-guest',complete_states_equal=count,stop_queue_aliases=4,
            helper_words=216,trig_providers_opaque=True,native32_qualified=False,installed=False)

    def test_03_fired_instruction_memory_prefixes_include_the_saved_roles(self):
        examples=[dict(null=True),dict(stop=1),dict(initialized=0,valid=2),dict(valid=4),
            dict(valid=1,heading=.625),dict(valid=2),dict(valid=4,fraction=1.5),dict(valid=2,fraction=1.5)]
        cuts=helper_cuts=0;rows=[]
        for kw in examples:
            initial,args=guest.fixture(**kw)
            completed=guest.PayloadOracle(self.truth,initial,args,self.helpers,retail=True,literal=True).run()
            for cut in range(completed.all_accesses):
                machines=[]
                for words in (self.words,self.truth):
                    m=guest.PayloadOracle(words,initial,args,self.helpers,retail=True,literal=True);m.access_fault=cut
                    with self.assertRaises(guest.guest.base.faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,cut);machines.append(m)
                a,b=machines;self.assertEqual(state(a),state(b),(kw,cut));cuts+=1
                helper_cuts+=a.current_pc in self.helpers
            rows.append(dict(case=kw,fired_prefixes=completed.all_accesses))
        self.receipt('normalized-fault-prefixes',cases=rows,all_fired_prefixes=cuts,
            helper_instruction_prefixes=helper_cuts,all_compared_states_equal=True,hardware_traps_unqualified=True)

    def test_04_extrapolation_dependencies_and_defined_history_addresses(self):
        homes=(-44,-60,-76,-92,-108,-124);count=0
        for index in (2,3):
            addresses=[guest.STACK+offset+index*4 for offset in homes]
            raw_registers=dict(zip((23,17,18,19,20,16),addresses))
            normalized_registers=dict(zip((17,18,19,20,21,16),addresses))
            raw,_=extrapolation_terms(self.raw_words[205:235],raw_registers)
            normalized,reads=extrapolation_terms(self.words[205:235],normalized_registers)
            expected={at:('add',*sorted((('sub',('read',at-4),('read',at-8)),('read',at-4)),key=repr)) for at in addresses}
            self.assertEqual(raw,expected);self.assertEqual(normalized,expected)
            self.assertEqual((len(reads),len(set(reads)),len(expected)),(12,12,6));count+=1
        self.receipt('extrapolation-dependencies',defined_history_indices=count,
            independent_history_reads=12,independent_outputs=6,source_origins_retained=30,
            FP_add_commutative_term_policy=True,strict_FP_exception_or_NaN_payload_equivalence_not_claimed=True)

    def test_05_two_complete_independent_data_and_call_rebases(self):
        data_maps=((0x18000,0x27FFC,0x38004,0x47FFC,0x88000,0x98004,0xA8000,0xB7FFC),
            (0x80097FFC,0x800A8000,0x800B8004,0x800C7FFC,0x800D8000,0x800E7FFC,0x800F8000,0x80107FFC))
        samples=[dict(null=True),dict(stop=1,bank=255),dict(initialized=0),dict(valid=1,heading=.625),dict(valid=2),dict(valid=4,fraction=1.5)]
        total=0
        for number,values in enumerate(data_maps):
            anchors=dict(zip(DATA.values(),values))
            anchors.update({name:0x15300000+number*0x100000+i*0x10000 for i,name in enumerate(CALLS.values())})
            expected=independent_rebase(self.truth,self.retail_bindings,anchors)
            actual=layout.relocate(self.normalized,self.moved,anchors);self.assertEqual(actual,expected)
            helpers={}
            pairs={guest.POSITION:((1,2,'D_80087290'),(3,4,'D_800D2350')),
                guest.SELECTOR:((14,15,'D_80087290'),(17,23,'D_800D2350')),
                guest.ENQUEUE:((0,1,'D_800DC2B0'),),guest.SPLINE:()}
            for key,name in CALLS.items():
                entry=getattr(guest,key)
                if entry not in self.helper_bodies:continue
                bindings={i:(kind,symbol) for hi,lo,symbol in pairs[entry] for i,kind in ((hi,'R_MIPS_HI16'),(lo,'R_MIPS_LO16'))}
                body=independent_rebase(self.helper_bodies[entry],bindings,anchors);start=anchors[name]
                helpers.update(zip(range(start,start+len(body)*4,4),body))
            updates={key:anchors[name] for key,name in dict(DATA,**CALLS).items()}
            with patch.multiple(guest,**updates):
                for kw in samples:
                    initial,args=guest.fixture(**kw)
                    a,b=[guest.PayloadOracle(w,initial,args,helpers,retail=True,literal=True).run() for w in (actual,expected)]
                    self.assertEqual(state(a),state(b),(number,kw));total+=1
        self.assertEqual(total,12)
        self.receipt('normalized-rebases',independent_full_maps=2,all_root_words_equal=True,
            all_four_actual_helpers_rebased=True,trig_provider_addresses_rebased=True,complete_guest_cases=total)

    def test_06_all_raw_words_bindings_and_recipe_controls_fail_closed(self):
        for index in range(305):
            bad=bytearray(self.raw);bad[index*4+3]^=1
            with self.assertRaises(ValueError):layout.normalize(bytes(bad),self.bindings)
        for at in self.bindings:
            bad=dict(self.bindings);bad.pop(at)
            with self.assertRaises(ValueError):layout.normalize(self.raw,bad)
        controls=0
        for name in ('SCAN','LOOP'):
            table=getattr(layout,name)
            for key,value in table.items():
                with patch.dict(table,{key:value^1}),self.assertRaises(ValueError):layout.normalize(self.raw,self.bindings)
                controls+=1
        for index,rename in layout.SPECIAL.items():
            for key,value in rename.items():
                bad=dict(rename);bad[key]=value^1
                with patch.dict(layout.SPECIAL,{index:bad}),self.assertRaises(ValueError):layout.normalize(self.raw,self.bindings)
                controls+=1
        for index in layout.COMMUTED:
            with patch.object(layout,'COMMUTED',tuple(i for i in layout.COMMUTED if i!=index)),self.assertRaises(ValueError):
                layout.normalize(self.raw,self.bindings)
            controls+=1
        for i in range(29):
            order=list(layout.EXTRAPOLATION);order[i],order[i+1]=order[i+1],order[i]
            with patch.object(layout,'EXTRAPOLATION',tuple(order)),self.assertRaises(ValueError):layout.normalize(self.raw,self.bindings)
            controls+=1
        for name in CALLS.values():
            for value in (0x5000000,0x15300001):
                with self.assertRaises(ValueError):layout.relocate(self.normalized,self.moved,dict(ANCHORS,**{name:value}))
        self.receipt('normalizer-controls',raw_word_changes=305,binding_removals=33,recipe_changes=controls,invalid_call_rebases=12)

    def test_07_lower_difference_screen_still_fails_private_memory(self):
        obj,words,row=roles.measure(self.root,self.out,'private-rejected-targetZ',roles.cursor_capture('targetZCursor',True))
        self.assertEqual((row['words'],row['frame'],row['differences']),(305,248,113))
        initial,args=guest.fixture(valid=4)
        a,b=[guest.PayloadOracle(w,initial,args,self.helpers,retail=retail,front=True,literal=True).run()
            for retail,w in ((False,words),(True,self.truth))]
        self.assertEqual((guest.guest.public(a.memory),a.calls),(guest.guest.public(b.memory),b.calls))
        self.assertNotEqual(a.memory,b.memory)
        layout.source.source.freeze(self.root,self.out)
        self.receipt('screen-rejection',words=305,frame=248,differences=113,public_memory_and_calls_equal=True,
            complete_memory_equal=False,installed=False,all22_production_inputs_unchanged=True)

    def test_08_actual_private_padder_preserves_mixed_profile_owner(self):
        source=layout.source.source;integration=source.prior.prior
        values=source.freeze(self.root,self.out);before=values['conker/src/game/generated_B3020.c'].decode()
        recovered=source.recovered_owner(before,layout.source.joint_selected())
        old,diag=integration.compile_profile(self.root,self.out,before,'padded-before-primary')
        old_override,old_diag=integration.compile_profile(self.root,self.out,before,'padded-before-normal',True)
        override,new_diag=integration.compile_profile(self.root,self.out,recovered,'padded-after-normal',True)
        self.assertFalse(diag or old_diag or new_diag)
        self.assertEqual(source.prior.same_functions(old_override,override,(source.FUNCTION,)),72)
        guards=values['conker/retail_word_patches.us.csv'];private=layout.private_guards(guards,self.raw,self.bindings)
        self.assertTrue(private.startswith(guards));guard_path=self.out/'private-guards.csv';guard_path.write_bytes(private)
        old_path=self.out/'unchanged-guards.csv';old_path.write_bytes(guards)
        with self.assertRaises(ValueError):layout.private_guards(private,self.raw,self.bindings)
        old_padded=integration.padded(self.root,self.out,old,'private-before-padded',old_path,old_override)
        padded=integration.padded(self.root,self.out,self.obj,'private-after-padded',guard_path,override)
        old_text,old_functions=integration.link_owner(self.root,self.out,old_padded,source.OWNER)
        text,functions=integration.link_owner(self.root,self.out,padded,source.OWNER)
        self.assertEqual(set(functions),set(old_functions));self.assertEqual(len(text),len(old_text))
        at=functions[source.FUNCTION]['value'];self.assertEqual(at,old_functions[source.FUNCTION]['value'])
        self.assertEqual(text[at:at+1220],struct.pack('>305I',*self.truth))
        self.assertEqual((text[:at],text[at+1220:]),(old_text[:at],old_text[at+1220:]))
        self.assertEqual(source.prior.same_functions(old_padded,padded,(source.FUNCTION,)),72)
        self.assertNotIn('.rodata',layout.source.sections(padded))
        for primary,selected in ((old,override),(self.obj,old)):
            with self.assertRaises(ValueError):emit_padded_assembly(primary,self.root/'conker/asm/B3020.s',
                function_objects={integration.FUNCTION:selected},word_patches_path=guard_path,filename=source.OWNER)
        source.freeze(self.root,self.out)
        self.receipt('private-padder',guard_rows=305,guard_prefix_bytes_unchanged=len(guards),
            private_root_words_exact=305,primary_neighbors_unchanged=72,normal_neighbors_unchanged=72,
            mixed_profile_override_preserved=True,all_other_padded_bytes_unchanged=True,compiled_literal_pool_not_copied=True,
            stale_primary_or_wrong_profile_controls=2,production_guards_changed=False,installed=False,matching_credit=0)


if __name__=='__main__':unittest.main()
