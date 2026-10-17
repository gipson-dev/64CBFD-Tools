"""Full uninstalled movement recovery, ABI packets, byte widths and explicit fit rejection."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest

from tools.experiments import game_actor_input_movement_recovery as source
from tools.tests import game_actor_input_movement_oracle as model
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout


def core_specs():
    for held,yaw,gate in itertools.product((0,100,101,124),(-32768,-1,0,32767),range(5)):
        yield dict(disabled=1,held=held,yaw=yaw,gate=gate,cooldown=255,pattern=1)
    for gate,buttons,xy in itertools.product(range(5),(0,0x10,0x4000,0x8000,0xC000),
            ((-128,-128),(-1,0),(0,-1),(0,0),(1,1),(72,73),(127,127))):
        yield dict(mode=0,gate=gate,buttons=buttons,x=xy[0],y=xy[1],
                   magnitude=(0.,1.,1.000000119,32.5)[(gate+buttons)%4],nearby=101,
                   depth=(30.,30.000002,100.,100.00001)[gate%4],
                   position=-101. if gate&1 else 100.)
    for buttons,xy,velocity in itertools.product((0,0x10,0x4000,0x8000,0xC000,0x4010,0x8010,0xFFFF),
            ((-128,-128),(-1,0),(0,-1),(0,0),(1,1),(72,73),(127,127)),
            (-40.,-1.5,1.5,30.)):
        yield dict(buttons=buttons,x=xy[0],y=xy[1],velocity=velocity)
    for held,below,depth,speed in itertools.product((0,101),(0,1),(-1.,0.,25.,50.,101.),(-2.,0.,19.,60.,61.,200.)):
        yield dict(held=held,below=below,depth=depth,speed=speed,
                   position=-101. if below else 2101.,velocity=-20.,control=2 if held else 0)
    for pressed,count,cooldown,category in itertools.product((0,0x2000),range(7),(0,1,2),(0x3B,0x3C)):
        yield dict(pressed=pressed,count=count,cooldown=cooldown,category=category,depth=0.,y=0)


def record_specs():
    for index,kind,eligible,depth,animation,active in itertools.product((0,1,12,24),(0x9B,0x9C,0x9D,0x9E),
            (0,1),(0.,-0.,1.),(0,0x21),(0,1)):
        yield dict(eligible=((index,active,eligible,depth,animation,kind),))
    for first,second,values in itertools.product((0,1,12),(1,12,24),((2.,2.),(1000.,999.),(-2.,-1.),(float('nan'),3.))):
        if first==second:continue
        yield dict(eligible=((first,1,1,0.,0,0x9C),(second,1,1,0.,0,0x9D)),
                   distances=((first,values[0]),(second,values[1])))


def mutation_specs():
    eligible=((1,1,1,0.,0,0x9C),(24,1,1,0.,0,0x9D))
    for mutation,mode,held,buttons in itertools.product(range(1,10),(0,1),(0,101),(0,0x10,0x4000)):
        yield dict(mutation=mutation,mode=mode,held=held,buttons=buttons,eligible=eligible,
            nearby=101,disabled=1 if mutation==2 and mode==0 else 0,control=2,depth=0.)


def targeted_specs():
    yield dict(mode=0,pressed=0xC000,depth=0.)
    yield dict(position=2101.,velocity=-40.)
    yield dict(position=-101.,below=0)
    yield dict(position=100.,below=1)
    yield dict(x=0,y=0,velocity=0.)
    yield dict(held=101,velocity=30.)
    yield dict(held=101,control=0,depth=25.,velocity=-20.)
    yield dict(position=-101.,threshold=0.,y=0,buttons=0)
    yield dict(position=-101.,threshold=0.,y=0,buttons=0x4000)
    yield dict(pressed=0x2000,eligible=((24,1,1,0.,0,0x9C),))


class MovementRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.words,cls.row=source.measure(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>959I',cls.rom,source.ROM))
        cls.curve=list(struct.unpack_from('>21I',cls.rom,0x120950))
        cls.connected={0x150F34A0+i*4:w for i,w in enumerate(cls.curve)}
        cls.coverage=set();cls.providers=set()

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,spec,images=None,entry=source.ENTRY):
        memory,case=model.fixture(self.rom,**spec);expected=model.reference(memory,case)
        for words in images or (self.truth,self.words):
            actual=model.Oracle(words,memory,case,self.connected,entry).run()
            self.assertEqual(model.public(actual.memory),model.public(expected[0]),spec)
            self.assertEqual(actual.calls,expected[1],spec)
            self.assertEqual(actual.observations,expected[2],spec)
            self.assertEqual(actual.fired,expected[3],spec)
            if words is self.truth:self.coverage.update(actual.visits)
            self.providers.update(t for t,_ in actual.calls)
        return memory,case,expected

    def test_01_complete_body_rejects_extent_frame_and_matching_credit(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(962,112,811))
        self.assertEqual(self.row['raw_sha'],'704bac447c0f4f30022a305d7f24ec2c315766bfff235294704c1148da1fff3f')
        self.assertEqual(self.row['raw_neighbors'],11)
        self.assertTrue(self.row['owner_pools_unchanged']);self.assertTrue(self.row['padder_rejected'])
        self.assertIn('retail span',self.row['padder_error'])
        self.assertEqual((self.row['new_guards'],self.row['matching_credit']),(0,0))
        self.assertEqual((self.words[1],self.words[4]),(0xAFB00028,0xAFBF002C))
        self.assertEqual((self.truth[1],self.truth[4]),(self.words[1],self.words[4]))
        self.assertEqual((self.words[5]&65535,self.truth[5]&65535),(0x60,0x58))
        self.assertIn('#pragma intrinsic (fabsf)',source.TYPE)
        self.receipt('shape',**{k:v for k,v in self.row.items() if k!='bindings'})

    def test_02_all_three_paths_and_numeric_boundaries(self):
        count=0
        for spec in core_specs():self.compare(spec);count+=1
        self.receipt('core',complete_cases=count,three_state_paths=True,full_public_memory_and_call_snapshots=True)

    def test_03_every_signed_stick_byte_and_cooldown(self):
        count=0
        for value,mode,axis in itertools.product(range(256),(0,1),('x','y')):
            self.compare(dict(mode=mode,**{axis:value}));count+=1
        for value in range(256):self.compare(dict(disabled=1,cooldown=value));count+=1
        for actor in (model.TABLE,model.TABLE+12*0x32C,model.TABLE+24*0x32C):
            self.compare(dict(actor=actor,held=101,control=2,buttons=0x4000));count+=1
        self.receipt('widths',complete_cases=count,all_256_stick_bytes_and_cooldowns=True,actor_table_aliases=3)

    def test_04_record_filters_nearest_ties_and_mutating_providers(self):
        count=0;fired=set()
        for spec in record_specs():self.compare(spec);count+=1
        for spec in mutation_specs():
            _,case,expected=self.compare(spec);count+=1
            if expected[3]:fired.add(case['mutation'])
        for spec in targeted_specs():self.compare(spec);count+=1
        self.assertEqual(fired,set(range(1,10)))
        missing=sorted(set(range(source.ENTRY,source.ENTRY+source.SIZE,4))-self.coverage)
        self.receipt('records-mutations',complete_cases=count,effective_mutation_modes=sorted(fired),
            coverage_scope='retail runs in this unittest class so far',
            reachable_target_words=len(self.coverage&set(range(source.ENTRY,source.ENTRY+source.SIZE,4))),
            unvisited_target_words=[hex(v) for v in missing],providers=[hex(v) for v in sorted(self.providers)],
            actual_21_word_curve_connected=True,opaque_remaining_providers=True,no_general_FCSR_or_hardware_claim=True)

    def test_05_two_independent_text_rebases(self):
        count=0
        for group,entry in enumerate((0x15207FF0,0x15610000)):
            words=source.linked(self.root,self.out,self.obj,'rebase-'+str(group),entry)
            for spec in (dict(mode=0,x=-128,y=127),dict(disabled=1,held=101),
                    dict(buttons=0x4000,held=101,control=2),dict(pressed=0x2000,depth=0.),
                    dict(eligible=((24,1,1,0.,0,0x9D),)),dict(mutation=4)):
                self.compare(spec,[words],entry);count+=1
        self.receipt('rebases',links=2,complete_cases=count,real_external_bindings_only=True,data_rebases_not_claimed=True)

    def test_06_private_fault_zero_is_still_rejected(self):
        memory,case=model.fixture(self.rom,held=101,pattern=1)
        machines=[model.Oracle(w,memory,case,self.connected) for w in (self.truth,self.words)]
        for machine in machines:
            machine.access_fault=0
            with self.assertRaises(model.point.faults.AccessBoundary):machine.run()
        self.assertNotEqual(model.point.state(machines[0]),model.point.state(machines[1]))
        self.assertEqual(machines[0].r[29]-machines[1].r[29],-16)
        self.receipt('private-gap',first_fault_cut=0,retail_frame=128,candidate_frame=112,
            mismatch_effective=True,no_private_fault_matching_credit=True)

    def test_07_production_baseline_and_callback_preserved(self):
        source.freeze(self.root,self.out)
        for key,path in source.PATHS.items():self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+key)).read_bytes())
        self.assertEqual(struct.unpack_from('>I',self.rom,0x22AB28)[0],source.ENTRY)
        functions,_,_=load_elf_functions(str(self.root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
        data=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('production',protected_entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),
            whole_ELF_sha256=hashlib.sha256((self.root/'conker/build/conker.us.elf').read_bytes()).hexdigest(),
            function_bodies=len(functions),callback_slot='0x80086068',new_guards=0,installed=False,matching_credit=0)

    def test_08_effective_semantic_and_ABI_controls(self):
        controls=(
            ('signed-stick','(f32)D_800CC284->y','(f32)(u8)D_800CC284->y',dict(y=-128)),
            ('angle-third','(f32)D_800CC284->y, 0)','(f32)D_800CC284->y, 1)',dict(mode=0)),
            ('signed-yaw','actor->yaw + 0x4000','(u16)actor->yaw + 0x4000',dict(disabled=1,yaw=-32768)),
            ('nearest-tail','index != 25','index != 24',dict(eligible=((24,1,1,0.,0,0x9D),))),
            ('nearest-tie','value < distance','value <= distance',dict(eligible=((1,1,1,0.,0,0x9C),(24,1,1,0.,0,0x9D)),distances=((1,2.),(24,2.)))),
            ('spawn-limit','count < 5','count <= 5',dict(pressed=0x2000,count=5)),
            ('floor-boundary','actor->depth <= contactHeight','actor->depth < contactHeight',dict(depth=0.)),
            ('acceleration-ABI','actor->valueC0, actor, speed, rate, 1','actor->valueC0, actor, speed, rate, 0',dict()),
        )
        for label,old,new,spec in controls:
            self.assertIn(old,source.SELECTED)
            body=source.SELECTED.replace(old,new)
            _,words,_=source.measure(self.root,self.out,'negative-'+label,body)
            memory,case=model.fixture(self.rom,**spec);expected=model.reference(memory,case)
            actual=model.Oracle(words,memory,case,self.connected).run()
            self.assertTrue(model.public(actual.memory)!=model.public(expected[0]) or
                actual.calls!=expected[1] or actual.observations!=expected[2],label)
        self.receipt('negative-controls',effective_controls=len(controls),complete_C_bodies=True)

    def test_09_native32_complete_records_and_semantic_packets(self):
        from tools.tests import game_actor_input_movement_native as native
        specs=[*list(core_specs())[::7],*list(mutation_specs())[::5],*targeted_specs()]
        native.qualify(self.root,self.out,self.rom,specs)

    def test_10_modeled_float_edges_not_hardware_FCSR(self):
        count=0
        for field,value in itertools.product(('velocity','position','depth','speed'),
                (-0.,float('inf'),float('-inf'),float('nan'),1.e30)):
            self.compare(dict(held=101,**{field:value}));count+=1
        self.receipt('FP-edges',complete_cases=count,nontrapping_model_only=True,
            invalid_signed_conversion_native_and_hardware_FCSR_not_qualified=True)

    def test_11_retail_duplicate_words_are_statically_unreachable_not_removed(self):
        dead=(0x150F36A8,0x150F388C,0x150F3924,0x150F3B84,0x150F3D70,0x150F3DD0,
            0x150F3E4C,0x150F3E90,0x150F41B0,0x150F421C,0x150F4274,0x150F42E4)
        targets={source.ENTRY};returns=set()
        for index,word in enumerate(self.truth):
            op,rs=word>>26,word>>21&31;pc=source.ENTRY+4*index
            if op in (1,4,5,6,7,20,21,22,23) or op==17 and rs==8:
                targets.add(pc+4+4*model.signed(word,16))
            elif op in (2,3):
                targets.add(((pc+4)&0xF0000000)|((word&0x3FFFFFF)<<2))
                if op==3:returns.add(pc+8)
            elif op==0 and word&63 in (8,9):
                self.assertEqual((word&63,rs),(8,31))
        for pc in dead:
            self.assertEqual(self.truth[(pc-source.ENTRY)//4-2]>>16,0x1000)
            self.assertNotIn(pc,targets|returns)
        self.receipt('static-dead',unreachable_words=len(dead),addresses=[hex(v) for v in dead],
            immediate_predecessor_unconditional_branch_and_delay=True,no_direct_target_or_call_return=True,
            no_internal_indirect_jump=True,original_words_preserved=True)


if __name__=='__main__':unittest.main()
