"""Reuse semantic qualification and verify the restored extent and literal spans."""
import hashlib
import itertools
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_fitting as source
from tools.tests import test_game_packet_rectangle_recovery as prior
from tools.tests import game_packet_rectangle_oracle as guest
from tools.pad_generated_object import parse_object


def controls():
    with patch.object(prior.source,'SELECTED',source.SELECTED):
        rows=prior.controls()
    rows['wrong-inset']=source.SELECTED.replace('(width + width) / D_800D2C80','width / D_800D2C80')
    rows['wrong-animation-modulo']=source.SELECTED.replace(
        'packet->animationFrame -= packet->descriptor->unkA << 3;',
        'packet->animationFrame %= packet->descriptor->unkA << 3;')
    if any(body==source.SELECTED for body in rows.values()):
        raise ValueError('Ineffective rectangle-fitting source control')
    return rows


# The packet ABI is unchanged; override only candidate-specific gates.
class PacketRectangleFittingTests(prior.PacketRectangleRecoveryTests):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>346I',cls.rom,source.ROM))

    def test_02_native32_O2_O0_UBSan_and_effective_controls(self):
        rows=controls()
        with patch.object(prior.source,'SELECTED',source.SELECTED),patch.object(prior,'controls',return_value=rows):
            super().test_02_native32_O2_O0_UBSan_and_effective_controls()

    def test_03_eighteen_neighbors_and_explicit_nonmatch(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),
            (346,136,71,''))
        self.assertFalse(self.row['pools'])
        self.assertNotEqual(self.words,self.truth)
        self.assertEqual(self.words[:104],self.truth[:104])
        self.assertEqual(self.words[-91:],self.truth[-91:])
        obj,diag=source.build.compile_owner(self.root,self.out,(self.out/'before-packet_owner').read_text(),'neighbor-predecessor')
        self.assertFalse(diag)
        old,new=parse_object(obj),parse_object(self.obj)
        self.assertEqual(set(old[1]),set(new[1]))
        for name,f in old[1].items():
            if name==source.FUNCTION:
                continue
            g=new[1][name]
            self.assertEqual(old[0][f['value']:f['value']+f['size']],new[0][g['value']:g['value']+g['size']],name)
            relative=lambda o,f:{a-f['value']:v for a,v in o[2].items() if f['value']<=a<f['value']+f['size']}
            self.assertEqual(relative(old,f),relative(new,g),name)
        self.assertEqual(len(old[1])-1,18)
        self.receipt('shape',words=346,frame=136,unresolved_differences=71,neighbors=18,
            new_target_guards=0,raw_match=False,literal_prefix_words=104,literal_suffix_words=91)

    def test_06_effective_compiled_guest_controls(self):
        rejected=[]
        for label,body in controls().items():
            _,words,_=source.measure(self.root,self.out,'negative-'+label,body)
            for memory,args in prior.cases():
                expected,cursor,trap=guest.reference(memory,args)
                self.assertIsNone(trap)
                m=guest.RectangleOracle(words,memory,args).run()
                if (guest.base.public(m.memory),m.r[2])!=(guest.base.public(expected),cursor):
                    rejected.append(label)
                    break
            else:
                self.fail('Ineffective compiled guest control: '+label)
        self.receipt('negatives',compiled_observable_rejections=rejected,
            no_compile_failures_or_unsupported_instructions_accepted=True)

    def test_08_physical_object_and_all_input_corruption_controls(self):
        source.checked_object(self.obj)
        text,funcs,rel=parse_object(self.obj)
        f=funcs[source.FUNCTION]
        for i in range(346):
            bad=bytearray(text)
            bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),funcs,rel)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        for at in source.RELOCATIONS:
            bad=dict(rel)
            bad[f['value']+at]=[(rel[f['value']+at][0][0],'wrong')]
            with patch.object(source,'parse_object',return_value=(text,funcs,bad)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        with patch.object(source,'sections',return_value={'.rodata':(0,b'x')}):
            with self.assertRaises(ValueError):
                source.checked_object(self.obj)
        rb=Path.read_bytes
        for key in source.PATHS:
            path=self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaisesRegex(ValueError,'fixture'):
                    source.freeze(self.root,self.out)
        manifest=(self.out/'baseline.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'Reserved'):
            source.measure(self.root,self.out,'baseline')
        self.assertEqual((self.out/'baseline.json').read_bytes(),manifest)
        self.receipt('corruptions',raw_words=346,bindings=28,extra_pool=True,frozen_inputs=100,
            reserved_manifest_screen_name_rejected=True)

    def test_11_first_full_image_prediction_uses_emitted_C_not_retail(self):
        row=source.prelink_prediction(self.root,self.out)
        self.assertEqual((row['metadata_exclusions'],row['metadata_serialization_bytes'],row['raw_match']),(0,0,False))
        expected=source.expected_inputs(self.root,self.out)
        self.assertEqual(row['after'],{k:hashlib.sha256(v).hexdigest() for k,v in expected.items()})
        slot=(self.out/'predicted-slot.bin').read_bytes()
        self.assertEqual(slot,struct.pack('>346I',*self.words))
        self.assertNotEqual(slot,self.rom[source.ROM:source.ROM+1384])
        for at in (0,416,1020,1380):
            bad=bytearray(slot)
            bad[at]^=1
            with self.assertRaises(ValueError):
                source.candidate_slot(bytes(bad))
        self.receipt('scope',inputs=100,unchanged_inputs=98,prediction=row)

    def test_12_literal_prefix_full_boundary_state_and_private_home_control(self):
        class Boundary(Exception):
            pass

        class Prefix(guest.RectangleOracle):
            def execute(model,instruction):
                if source.ENTRY+0x1A0 in model.visits:
                    raise Boundary()
                super().execute(instruction)

        def run(words,memory,args,phase):
            model=Prefix(words,memory,args,phase=phase)
            with self.assertRaises(Boundary):
                model.run()
            return model

        count=0
        for scale,position,flip,inset,tint,phase in itertools.product((2.5,-2.5),(-4.75,4.25),(0,3),(0,1),(0,1),(0,8)):
            memory,args=guest.fixture((scale,3.25,position,-2.125,4096.,32.5,20.25),flip=flip,tint=tint,
                offsets=(17,inset,5),animation=129,frame=127,speed=255,timestep=255)
            original=run(self.truth,memory,args,phase)
            fitted=run(self.words,memory,args,phase)
            self.assertEqual(guest.base.edge.state(original),guest.base.edge.state(fitted))
            self.assertEqual((original.fcsr,original.condition),(fitted.fcsr,fitted.condition))
            bad=list(self.words)
            bad[2]^=1<<16
            corrupted=run(bad,memory,args,phase)
            self.assertEqual(guest.base.public(corrupted.memory),guest.base.public(original.memory))
            self.assertNotEqual(guest.base.edge.state(corrupted),guest.base.edge.state(original))
            count+=1
        self.receipt('prefix',full_boundary_pairs=count,literal_words=104,boundary='0x15095ED4',
            private_home_control_observed_with_identical_public_memory=True,
            no_complete_later_private_or_hardware_fault_claim=True)


if __name__=='__main__':
    unittest.main()
