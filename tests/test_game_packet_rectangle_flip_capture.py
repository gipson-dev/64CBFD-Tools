"""Qualify the shorter flag lifetime without claiming the remaining 18 words."""
import hashlib
import itertools
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_flip_capture as source
from tools.tests import test_game_packet_rectangle_fitting as fitting
from tools.tests import game_packet_rectangle_oracle as guest
from tools.pad_generated_object import parse_object


class PacketRectangleFlipCaptureTests(fitting.PacketRectangleFittingTests):
    @classmethod
    def setUpClass(cls):
        cls.source_patch=patch.object(fitting,'source',source)
        cls.source_patch.start()
        cls.addClassCleanup(cls.source_patch.stop)
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>346I',cls.rom,source.ROM))

    def test_03_eighteen_neighbors_and_explicit_nonmatch(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),
            (346,136,18,''))
        self.assertFalse(self.row['pools'])
        self.assertNotEqual(self.words,self.truth)
        self.assertEqual(self.words[:148],self.truth[:148])
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
        self.receipt('shape',words=346,frame=136,unresolved_differences=18,neighbors=18,
            new_target_guards=0,raw_match=False,literal_prefix_words=148,literal_suffix_words=91)

    def test_12_literal_prefix_full_boundary_state_and_private_home_control(self):
        class Boundary(Exception):
            pass
        class Prefix(guest.RectangleOracle):
            def execute(model,instruction):
                if any(pc>=source.ENTRY+0x250 for pc in model.visits):
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
        self.receipt('prefix',full_boundary_pairs=count,literal_words=148,boundary='first PC >= 0x15095F84',
            private_home_control_observed_with_identical_public_memory=True,
            no_complete_later_private_or_hardware_fault_claim=True)


if __name__=='__main__':
    unittest.main()
