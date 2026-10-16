"""Reject equal-count rectangle fits with changed private homes or source roles."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_lifetime as source
from tools.experiments import game_packet_rectangle_compiler_trace as provenance
from tools.tests import game_packet_rectangle_oracle as guest


class RectangleLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        source.freeze(cls.root,cls.out)
        cls.before=(cls.out/'before-packet_owner').read_text()
        cls.truth=struct.unpack_from('>346I',(cls.out/'before-retail_rom').read_bytes(),source.ROM)

    def words(self,label):
        _,functions,_=source.parse_object(self.out/(label+'.o'))
        function=functions[source.FUNCTION]
        data=source.sections(self.out/(label+'.elf'))['.text'][1]
        return struct.unpack_from('>%dI'%(function['size']//4),data,function['value'])

    def test_01_all_100_live_inputs_and_selection_unchanged(self):
        self.assertEqual({k:hashlib.sha256((self.root/p).read_bytes()).hexdigest()
            for k,p in source.PATHS.items()},source.BASELINE)
        self.assertEqual(len(source.PATHS),100)
        self.assertEqual(source.SELECTED,source.INITIAL)
        self.assertEqual(source.recovered_owner(self.before),self.before)
        provenance.checked_signature(self.out/'predecessor.o')

    def test_02_all_105_complete_sources_objects_bindings_pools_and_linked_words(self):
        forms=list(source.forms())
        self.assertEqual(len(forms),105)
        self.assertEqual(len(dict(forms)),105)
        self.assertEqual(len({body for _,body in forms}),105)
        best=10000
        for label,body in forms:
            with self.subTest(label=label):
                self.assertEqual((self.out/(label+'.c')).read_text(),source.recovered_owner(self.before,body))
                row=json.loads((self.out/(label+'.json')).read_text())
                text,functions,rel=source.parse_object(self.out/(label+'.o'))
                f=functions[source.FUNCTION]
                self.assertEqual(hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),row['raw_sha256'])
                bindings={str(a-f['value']):v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
                self.assertEqual(bindings,{a:[tuple(v) for v in entries] for a,entries in row['relocations'].items()})
                pools={n:d.hex() for n,(_,d) in source.sections(self.out/(label+'.o')).items()
                    if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
                self.assertEqual(pools,row['pools'])
                words=self.words(label)
                differences=sum(a!=b for a,b in zip(words,self.truth))+abs(len(words)-346)
                self.assertEqual((len(words),(-words[0])&65535,differences,row['diagnostics']),
                    (row['words'],row['frame'],row['differences'],''))
                self.assertEqual(row['different_words'],[[i*4,'0x%08X'%a,'0x%08X'%b]
                    for i,(a,b) in enumerate(zip(words,self.truth)) if a!=b])
                best=min(best,differences)
        self.assertEqual(best,71)

    def test_03_equal_counts_and_spans_do_not_prove_equal_private_homes(self):
        selected=self.words('predecessor')
        stepped=self.words('original-steps-S')
        offsets=[i*4 for i,(a,b) in enumerate(zip(selected,stepped)) if a!=b]
        self.assertEqual(offsets,[0x23C,0x288,0x334,0x348,0x34C,0x380,0x3C8,0x3F8])
        for label in ('predecessor','original-steps-S'):
            row=json.loads((self.out/(label+'.json')).read_text())
            shape=source.shape(self.out,label)
            self.assertEqual((row['words'],row['frame'],row['differences'],shape['prefix'],shape['suffix']),
                (346,136,71,104,91))
        for at in offsets:
            self.assertEqual(selected[at//4]&~65535,stepped[at//4]&~65535)
            self.assertEqual((selected[at//4]&65535)-(stepped[at//4]&65535),4)
        with self.assertRaisesRegex(ValueError,'diagnostic object'):
            provenance.checked_signature(self.out/'original-steps-S.o')

    def test_04_effective_equal_public_but_different_private_execution_control(self):
        selected=self.words('predecessor')
        stepped=self.words('original-steps-S')
        count=0
        for scale,position,flip,inset,phase in itertools.product((2.5,-2.5),(-4.75,4.25),(0,3),(0,1),(0,8)):
            memory,args=guest.fixture((scale,3.25,position,-2.125,4096.,32.5,20.25),
                flip=flip,offsets=(17,inset,5),animation=129,frame=127,speed=255,timestep=255)
            a=guest.RectangleOracle(selected,memory,args,phase=phase).run()
            b=guest.RectangleOracle(stepped,memory,args,phase=phase).run()
            self.assertEqual((guest.base.public(a.memory),a.r[2]),(guest.base.public(b.memory),b.r[2]))
            self.assertNotEqual(a.memory,b.memory)
            count+=1
        self.assertEqual(count,32)

    def test_05_all_100_frozen_input_corruptions_rejected(self):
        read=Path.read_bytes
        for key in source.PATHS:
            path=self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                with self.assertRaisesRegex(ValueError,'fixture'):
                    source.freeze(self.root,self.out)

    def test_06_consistent_parameter_prototypes_and_preserved_manifest(self):
        forms=dict(source.forms())
        body=forms['value-word-arguments-sOffset-insetTOffset']
        owner=source.recovered_owner(self.before,body)
        self.assertIn('s32 func_15095D34(Gfx *, ProjectedPacket95B08 *, u32, u32, s32);',owner)
        with self.assertRaisesRegex(ValueError,'prototype'):
            source.recovered_owner(self.before.replace('s32 func_15095D34(Gfx *,','u32 func_15095D34(Gfx *,'),body)
        manifest=(self.out/'baseline.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'Reserved'):
            source.measure(self.root,self.out,'baseline')
        self.assertEqual((self.out/'baseline.json').read_bytes(),manifest)

    def test_07_external_priority_probe_is_not_free_on_this_function(self):
        for count,mixed in itertools.product((1,2,4),(False,True)):
            label='priority-probe-'+str(count)+('-mixed' if mixed else '')
            row=json.loads((self.out/(label+'.json')).read_text())
            shape=source.shape(self.out,label)
            self.assertEqual((row['words'],row['frame'],shape['prefix']),(351 if mixed else 350,136,17))
            self.assertGreater(row['differences'],71)
            self.assertTrue(any(home[1]=='sw' and home[3]=='0x2c' for home in shape['homes']))
        self.assertNotIn('if (fractionalT) {}',source.SELECTED)

    def test_08_tail_alignment_does_not_hide_the_extra_word(self):
        row=json.loads((self.out/'flags-before-S-mixed.json').read_text())
        shape=source.shape(self.out,'flags-before-S-mixed')
        self.assertEqual((row['words'],row['frame'],row['differences']),(347,136,226))
        self.assertEqual((shape['prefix'],shape['suffix'],shape['slot_suffix']),(109,91,0))
        words=self.words('flags-before-S-mixed')
        self.assertEqual(words[-91:],self.truth[-91:])
        self.assertNotEqual(words,self.truth)


if __name__=='__main__':
    unittest.main()
