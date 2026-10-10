"""Full dispatch matching: private traces, closed guards, padding and linked audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_render_dispatch_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,parse_object,emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_render_dispatch_recovery as recovery
from tools.tests import test_game_actor_render_dispatch_layout as layout
from tools.tests import test_game_actor_distance_tier_match as distance
from tools.tests.test_game_owner_points_initializer_match import metadata
from tools.tests import test_game_owner_points_initializer_match as initializer
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools


class CallerOracle(recovery.DispatchOracle):
    ENTRY=0x1502BAD0
    EXTRA={0x150368C4:3,0x15030E08:3,0x1502C408:2,screen.ENTRY:5}

    def __init__(self,words,memory,connected,mode,view,phase,plan):
        distance.attachment.AttachmentOracle.__init__(self,words,memory,
            symbols=(self.ENTRY,0,0),phase=phase,entry=self.ENTRY,
            arguments=(recovery.OUTPUT,mode,view),connected=connected)
        self.symbols,self.identity=distance.LINKS[0],1
        self.actions,self.update_actions=(),()
        self.plan,self.counts,self.pending=plan,{},None
        self.parent_pending=None

    def record_call(self,target):
        if target not in self.EXTRA:
            return super().record_call(target)
        args=self.arguments(self.EXTRA[target])
        self.parent_pending=(target,args)
        event=('CALL','func_%08X'%target,args)
        self.calls.append(event)
        self.events.append(event)

    def hook(self,target):
        if target not in self.EXTRA:
            return super().hook(target)
        self.assert_external(target)
        cursor=self.parent_pending[1][0]
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=cursor

    def assert_external(self,target):
        assert target!=screen.ENTRY,'complete dispatch body must execute, not a hook'


class GameActorRenderDispatchMatchTests(recovery.GameActorRenderDispatchRecoveryTests):
    assemble=classmethod(distance.GameActorDistanceTierMatchTests.assemble.__func__)
    write_rows=classmethod(distance.GameActorDistanceTierMatchTests.write_rows.__func__)

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-render-dispatch-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=recovery.PATHS
        if not (cls.out/'baseline.json').exists():
            baseline={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                baseline[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(baseline,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        with (cls.out/'before-guards').open(newline='') as stream:
            reader=csv.DictReader(stream)
            cls.fields,cls.old_rows=reader.fieldnames,list(reader)
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>176I',cls.rom,screen.ROM))
        assembly=(cls.root/'conker/asm/58F80.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        cls.slot_asm=cls.out/'slot.s'
        cls.slot_asm.write_text('glabel '+screen.FUNCTION+assembly+'endlabel '+screen.FUNCTION+'\n')
        cls.rows=screen.guard_rows(cls.out/'selected.o')
        cls.write_rows(cls.out/'isolated.csv',cls.rows)
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',cls.slot_asm,
            word_patches_path=cls.out/'isolated.csv',filename='generated_58F80'))
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+
            screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+assembly+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.layout=cls.link('fitted',recovery.S)
        cls.fitted=cls.layout
        cls.current=cls.fitted
        cls.elf=(cls.root/cls.paths['elf']).read_bytes()
        if screen.recovery.ORIGINAL not in (cls.root/screen.SOURCE).read_text():
            cls.current=list(struct.unpack_from('>176I',cls.elf,elf_slot_offset(cls.elf,screen.ENTRY,704)))
            cls.layout=cls.current
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path=Path(cls.directory.name)
        cls.coverage=set()

    @classmethod
    def link(cls,name,symbols):
        script=cls.out/('link-%s-%X.ld'%(name,symbols['D_800CC2D0']))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%screen.ENTRY)
        elf=script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        size=parse_object(cls.out/(name+'.o'))[1][screen.FUNCTION]['size']//4
        return list(struct.unpack_from('>%dI'%size,sections(elf)['.text'][1]))

    def compare(self,*args,**kwargs):
        models=super().compare(*args,**kwargs)
        self.assertEqual((models[0].memory,models[0].events),(models[2].memory,models[2].events))
        return models

    def test_06_owner_neighbors_and_unchanged_production_gate(self):
        before=(self.out/'before-source').read_text()
        objects=[]
        for name,body in (('owner-before',before),('owner-after',screen.install(before))):
            obj,diagnostics=compile_owner(self.root,self.out,body,name)
            self.assertEqual(diagnostics,[])
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',
                check=True,capture_output=True)
            objects.append(obj)
        first,second=(parse_object(obj) for obj in objects)
        relative=lambda data,meta:{offset-meta['value']:uses for offset,uses in data[2].items()
            if meta['value']<=offset<meta['value']+meta['size']}
        self.assertEqual(first[1].keys(),second[1].keys())
        neighbors=0
        for name,a in first[1].items():
            if name==screen.FUNCTION:
                continue
            b=second[1][name]
            self.assertEqual((a['size'],first[0][a['value']:a['value']+a['size']],relative(first,a)),
                (b['size'],second[0][b['value']:b['value']+b['size']],relative(second,b)),name)
            neighbors+=1
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertEqual(screen.guard_rows(objects[1]),self.rows)
        guards=self.out/'qualified-guards.csv'
        self.write_rows(guards,self.old_rows+self.rows)
        padded=[]
        for index,obj in enumerate(objects):
            name='padded-owner-%d'%index
            self.assemble(name,emit_padded_assembly(obj,self.root/'conker/asm/58F80.s',
                word_patches_path=self.out/'before-guards' if index==0 else guards,
                filename='generated_58F80',rodata_symbol='jtbl_80096DF8_game'))
            padded.append(parse_object(self.out/(name+'.o')))
        start=padded[1][1][screen.FUNCTION]['value']
        self.assertEqual(padded[1][1][screen.FUNCTION]['size'],704)
        self.assertEqual(padded[0][0][:start],padded[1][0][:start])
        self.assertEqual(padded[0][0][start+704:],padded[1][0][start+704:])
        self.receipt('owner',neighbors=neighbors,body_relocations_pools_exact=True,
            copied_target_equals_complete_isolated_recipe=True,only_target_padded_slot_changes=True)

    def test_07_actual_native32_complete_C(self):
        with patch.object(recovery.screen,'SELECTED',screen.SELECTED):
            super().test_07_actual_native32_complete_C()

    def test_10_measured_physical_gates_and_retail_coverage(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],
            self.meta['diagnostics']), (177,0x60,0,''))
        self.assertEqual(self.fitted,self.retail)
        self.assertEqual(self.current,self.retail)
        self.assertEqual(len(self.rows),177)
        self.assertEqual(sum(row['omit']=='true' for row in self.rows),1)
        self.assertFalse(any(row['insert_after'] for row in self.rows))
        self.assertEqual([i for i in range(176) if screen.ENTRY+i*4 not in self.coverage],[171])
        self.receipt('shape',raw_words=177,raw_frame=0x60,fitted_words=176,fitted_frame=0x58,
            guards=177,changed_words=sum(r['expected']!=r['replacement'] for r in self.rows),
            omissions=1,insertions=0,padding=0,relocations=len(screen.RELOCATIONS),
            omitted_redundant_mask_retains_portable_C=True,unreachable_words=[171])

    def test_11_private_aliases_and_actual_pointer_homes(self):
        cases=0
        for phase,mode,offset in itertools.product((0,8),(0,3,4,5),
                (0x24,0x2C,0x34,0x38,0x40,0x44,0x48,0x4C,0x50,0x54,0x58,0x60)):
            memory=recovery.fixture(enabled=1)
            base=recovery.STACK+phase-0x58
            actor=recovery.S['D_800CC2D0']
            recovery.distance.put(memory,actor+0x318,base+offset-0x2C,4)
            plan=recovery.Plan(second=-1)
            models=[layout.PointerOracle(body,memory,mode=mode,phase=phase,plan=plan).run()
                for body in (self.retail,self.current)]
            self.assertEqual((models[0].memory,models[0].events,models[0].private_arguments),
                (models[1].memory,models[1].events,models[1].private_arguments))
            cases+=1
        for phase,home,mode in itertools.product((0,8),(0x34,0x40,0x44,0x48,0x4C,0x54),(0,3,4,5)):
            memory=recovery.fixture(enabled=1)
            actions={('func_1506196C',1):((recovery.STACK+phase-0x58+home,0x12345678,4),)}
            plan=recovery.Plan(second=-1,actions=actions)
            models=[layout.PointerOracle(body,memory,mode=mode,phase=phase,plan=plan).run()
                for body in (self.retail,self.current)]
            self.assertEqual((models[0].r[2],models[0].memory,models[0].events,models[0].private_arguments),
                (models[1].r[2],models[1].memory,models[1].events,models[1].private_arguments))
            cases+=1
        self.receipt('private-aliases',cases=cases,complete_frame_and_private_callback_addresses_exact=True,
            raw_frame_not_claimed_private_equivalent=True)

    def test_12_full_verified_private_and_public_fault_prefixes(self):
        prefixes=0
        for phase,(mode,first,second,enabled,owner) in itertools.product((0,8),
                ((0,0,255,0,0),(0,255,-1,0,0),(4,255,-1,1,0),
                 (3,255,254,1,0x100),(5,255,255,0,0),(6,255,256,1,7))):
            memory=recovery.fixture(first_gate=1,enabled=enabled,owner=owner)
            plan=recovery.Plan(first=first,second=second)
            full=recovery.DispatchOracle(self.retail,memory,mode=mode,phase=phase,plan=plan).run()
            for ordinal in range(full.accesses):
                models=[]
                for body in (self.retail,self.current):
                    model=recovery.DispatchOracle(body,memory,mode=mode,phase=phase,plan=plan)
                    model.fault=ordinal
                    with self.assertRaises(distance.attachment.AccessFault) as caught:
                        model.run()
                    self.assertEqual(caught.exception.args,(ordinal,))
                    self.assertEqual(model.accesses,ordinal)
                    models.append(model)
                self.assertEqual((models[0].memory,models[0].events),(models[1].memory,models[1].events))
                prefixes+=1
        self.receipt('full-faults',verified_prefixes=prefixes,executions=prefixes*2,
            all_private_public_gates_fired=True,complete_prefixes_exact=True)

    def test_13_independent_links_and_all_stale_dependencies(self):
        cases=0
        for delta in (0,0x48034,0x98004):
            symbols={name:value+delta for name,value in recovery.S.items()}
            bodies=tuple(self.link(name,symbols) for name in ('original','fitted'))
            self.assertEqual(*bodies)
            with patch.dict(recovery.S,symbols,clear=True):
                for slot,view,mode,alpha in itertools.product((0,25),(0,0x12340002),(0,3,4,5),(-1,255)):
                    memory=recovery.fixture(slot,view,enabled=1)
                    plan=recovery.Plan(second=alpha)
                    models=[layout.PointerOracle(body,memory,slot,view,mode,plan=plan).run() for body in bodies]
                    self.assertEqual((models[0].memory,models[0].events,models[0].private_arguments),
                        (models[1].memory,models[1].events,models[1].private_arguments))
                    cases+=1
        data=(self.out/'selected.o').read_bytes()
        h=ELF_HEADER.unpack_from(data)
        headers=[SECTION_HEADER.unpack_from(data,h[6]+i*h[11]) for i in range(h[12])]
        ns=headers[h[13]]
        names=data[ns[4]:ns[4]+ns[5]]
        text=next(s for s in headers if names[s[0]:].split(b'\0',1)[0]==b'.text')
        for index in range(177):
            stale=list(screen.RAW)
            stale[index]^=0x10000
            with self.assertRaisesRegex(ValueError,'stale complete'):
                screen.recipe(stale)
            damaged=bytearray(data)
            struct.pack_into('>I',damaged,text[4]+index*4,stale[index])
            path=self.out/'stale.o'
            path.write_bytes(damaged)
            with self.assertRaisesRegex(ValueError,'stale word patch'):
                emit_padded_assembly(path,self.slot_asm,word_patches_path=self.out/'isolated.csv',filename='generated_58F80')
        for offset in screen.RELOCATIONS:
            rows=[dict(row) for row in self.rows]
            rows[offset//4]['expected_relocations']='-'
            path=self.out/'stale-relocations.csv'
            self.write_rows(path,rows)
            with self.assertRaisesRegex(ValueError,'stale relocations'):
                emit_padded_assembly(self.out/'selected.o',self.slot_asm,word_patches_path=path,filename='generated_58F80')
        self.receipt('links-and-stale',cases=cases,independent_links=6,actual_word_rejections=177,
            actual_relocation_rejections=len(screen.RELOCATIONS),signed_LO16_carries=True)

    def test_14_whole_linked_installation(self):
        source=(self.root/screen.SOURCE).read_text()
        if screen.recovery.ORIGINAL in source:
            self.assertEqual({name:hashlib.sha256((self.root/path).read_bytes()).hexdigest()
                for name,path in self.paths.items()},self.baseline)
            self.receipt('installation',installed=False,baseline_unchanged=True)
            return
        self.assertEqual(source,screen.install((self.out/'before-source').read_text()))
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertEqual(list(csv.DictReader(stream)),self.old_rows+self.rows)
        self.assertTrue((self.root/self.paths['guards']).read_bytes().startswith((self.out/'before-guards').read_bytes()))
        for name in ('progress','rodata'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        before=(self.out/'before-elf').read_bytes()
        expected=bytearray(before)
        struct.pack_into('>176I',expected,elf_slot_offset(before,screen.ENTRY,704),*self.retail)
        with patch.multiple(initializer.base,FUNCTION=screen.FUNCTION,ENTRY=screen.ENTRY):
            struct.pack_into('>I',expected,initializer.target_symbol_size_offset(before),704)
        actual=(self.root/self.paths['elf']).read_bytes()
        em,am=metadata(bytes(expected)),metadata(actual)
        self.assertEqual(em[:4],am[:4])
        for section in em[4:]:
            offset,length=section[4],section[5]
            expected[offset:offset+length]=actual[offset:offset+length]
        self.assertEqual(bytes(expected),actual)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,only_target_704_bytes_and_symbol_extent_changed=True,
            old_guards_exact_prefix_conversion_unchanged=True,protected_data=audit)

    def test_15_complete_actual_banked_parent_caller(self):
        parent=list(struct.unpack_from('>173I',self.elf,
            elf_slot_offset(self.elf,CallerOracle.ENTRY,692)))
        self.assertEqual(parent,list(struct.unpack_from('>173I',self.rom,0x58F80)))
        cases=0
        for slot,view,mode,phase,first in itertools.product((0,24),(0,3),range(7),(0,8),(0,255)):
            memory=recovery.fixture(slot,view,enabled=1)
            base=recovery.S['D_800CC2D0']
            selected={a:v for a,v in memory.items() if base+slot*0x32C<=a<base+(slot+1)*0x32C}
            memory.update({base+i:0 for i in range(26*0x32C)})
            memory.update(selected)
            actor=base+slot*0x32C
            for offset,value,size in ((0,1,4),(4,0,1),(5,7 if mode==6 else 1 if mode==2 else 4,1),
                    (0x184,0x200,4),(0x74,0,1),(0x318,0,4)):
                recovery.distance.put(memory,actor+offset,value,size)
            recovery.distance.put(memory,0x8003C8E0,0,4)
            plan=recovery.Plan(first=first,second=-1)
            models=[]
            for body in (self.retail,self.current):
                connected={screen.ENTRY+i*4:word for i,word in enumerate(body)}
                models.append(CallerOracle(parent,memory,connected,mode,view,phase,plan).run())
            self.assertEqual((models[0].r[2],models[0].memory,models[0].events),
                (models[1].r[2],models[1].memory,models[1].events))
            for model in models:
                self.assertIn(screen.ENTRY,model.visits)
                dispatch_calls=[event for event in model.calls if event[1]=='func_1502C974']
                self.assertEqual(len(dispatch_calls),1)
                self.assertEqual(dispatch_calls[0][2],(recovery.OUTPUT+8,slot,view,mode,0))
            cases+=1
        self.receipt('complete-parent',cases=cases,banked_parent_words=173,complete_dispatch_words=176,
            both_original_and_fitted_execute=True,first_and_last_parent_slots=True,
            other_render_callbacks_explicitly_bounded=True)


if __name__=='__main__':
    import unittest
    unittest.main()
