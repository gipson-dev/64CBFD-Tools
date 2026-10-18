"""Audit owned projection compiler evidence and fail-closed observation controls."""
import itertools
import json
from pathlib import Path
import re
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_projection_allocation_trace as source
from tools.experiments import game_route_projection_grouped_fit as groups
from tools.tests import test_game_route_projection_setup as guest


def event_change(log,index,change):
    lines=log.splitlines();positions=[i for i,line in enumerate(lines) if line.startswith('RECT_COLOR ')]
    at=positions[index];event=json.loads(lines[at].removeprefix('RECT_COLOR '));change(event)
    lines[at]='RECT_COLOR '+json.dumps(event)
    return '\n'.join(lines)+'\n'


class AllocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        if not (cls.out/'selected-mode-5/trace.json').exists():source.observe(cls.root)
        if not (cls.out/'selected-colors/trace.json').exists():source.observe(cls.root,True)
        cls.printed=source.audit(cls.root);cls.native=source.audit(cls.root,True)
        cls.work=cls.out/'selected-colors';cls.log=(cls.work/'debugger.txt').read_text()
        cls.text=(cls.work/'uoptlist').read_text();cls.events,_=source.color_events(cls.log,cls.native['constraints'])
        cls.groupout=cls.root/groups.BUILD
        if not (cls.groupout/'qualified-screens.json').exists():groups.qualify(cls.root,cls.groupout)
        cls.screens=groups.audit(cls.root,cls.groupout)

    def test_01_isolated_and_observed_complete_identity(self):
        self.assertEqual(self.printed['constraints'],self.native['constraints'])
        self.assertEqual(self.native['color_facts']['choice_order'],[109,27,113,262,18,2])
        self.assertEqual(self.native['color_facts']['event_count'],168)
        self.assertFalse(self.native['color_facts']['initially_forbidden_saved_colors'])
        self.assertEqual(self.native['lifecycle']['child_and_driver_exit_codes'],[0]*5)
        self.assertTrue(self.native['lifecycle']['final_inferior_null'])
        source.source.checked(self.work/'baseline.o');source.source.checked(self.work/'trace.o')
        self.assertFalse(self.native['installable'])

    def test_02_fact_and_constraint_negative_controls(self):
        count=0
        for expression in source.COLORS:
            pattern=r'(>>>active<<<\{[^}]+\}\s+'+str(expression)+r'\s+)(-?\d+)'
            bad,n=re.subn(pattern,lambda m:m[1]+str(int(m[2])+1),self.text,count=1)
            self.assertEqual(n,1)
            with self.assertRaises(ValueError):source.facts(bad)
            count+=1
        bad,n=re.subn(r'(>>>active<<<\{715\|0\}\s+15\s+)-1',r'\g<1>14',self.text,count=1)
        self.assertEqual(n,1)
        with self.assertRaises(ValueError):source.facts(bad)
        count+=1
        for marker in ('IN LOCAL OPTIMIZATION OF ','IN REEMISSION OF '):
            with self.assertRaises(ValueError):source.facts(self.text.replace(marker,'MISSING ',1))
            count+=1
        for offset in (0,4):
            bad,n=re.subn(r'(isvar\s+P\s+749\s+)'+str(offset)+r'vreg',r'\g<1>99vreg',self.text,count=1)
            self.assertEqual(n,1)
            with self.assertRaises(ValueError):source.facts(bad)
            count+=1
        lo=self.text.index('>>>active<<<{875|0}');hi=self.text.index('>>>active<<<',lo+1)
        block=self.text[lo:hi];line=next(l for l in block.splitlines() if l.startswith(':::interfere with:::'))
        changed,n=re.subn(r'(?<!\d)262(?!\d)','',line,count=1);self.assertEqual(n,1)
        bad=self.text[:lo]+block.replace(line,changed,1)+self.text[hi:]
        with self.assertRaises(ValueError):source.facts(bad)
        count+=1
        (self.out/'fact-controls.json').write_text(json.dumps(dict(effective_controls=count),indent=2)+'\n')

    def test_03_native_event_and_lifecycle_controls(self):
        controls=[self.log.replace('RECT_COLOR_INSTALLED','MISSING',1),
            self.log.replace('TRACE_EXIT inferior=3 code=0','TRACE_EXIT inferior=3 code=1',1),
            self.log.replace('RECT_COLOR_REMOVED','MISSING',1)]
        controls.append(event_change(self.log,0,lambda e:e.update(pid=e['pid']+1)))
        controls.append(event_change(self.log,0,lambda e:e.update(host_pc=0)))
        controls.append(event_change(self.log,0,lambda e:e.update(sequence=7)))
        controls.append(event_change(self.log,0,lambda e:e['rows'].pop()))
        controls.append(event_change(self.log,0,lambda e:e['rows'][0].update(live=e['rows'][0]['live']+4)))
        controls.append(event_change(self.log,1,lambda e:e['rows'][0].update(units=[])))
        def forbidden(e):
            raw=bytearray.fromhex(e['rows'][0]['head']);word=struct.unpack_from('<I',raw,40)[0]|(0x80000000>>14)
            struct.pack_into('<I',raw,40,word);e['rows'][0]['head']=raw.hex()
        controls.append(event_change(self.log,3,forbidden))
        def final_color(e):
            raw=bytearray.fromhex(e['rows'][0]['head']);raw[35]=0;e['rows'][0]['head']=raw.hex()
        controls.append(event_change(self.log,len(self.events)-1,final_color))
        chosen=next(i for i,e in enumerate(self.events) if e['event']=='chosen' and e['active']['index']==109)
        controls.append(event_change(self.log,chosen,lambda e:e['active'].update(ichain=e['active']['ichain']+4)))
        for index,bad in enumerate(controls):
            with self.assertRaises(ValueError,msg=index):source.color_events(bad,self.native['constraints'])
        with self.assertRaises(ValueError):source.lifecycle(self.root.resolve(),self.log.replace('TRACE_EXIT inferior=2 code=0','MISSING',1))
        (self.out/'native-controls.json').write_text(json.dumps(dict(event_controls=len(controls),
            producer_exit_controls=1),indent=2)+'\n')

    def test_04_captured_source_listing_and_probe_corruption(self):
        old_text,old_bytes=Path.read_text,Path.read_bytes;checks=0
        for path,old,new in ((self.work/'baseline.c','void func_150891E8','void altered'),
                (self.work/'debugger.txt','Allocate diagnostic stream buffer','MISSING'),
                (self.work/'debugger.txt','Suppress diagnostic real-number printer','MISSING')):
            def alter(actual,*args,**kwargs):
                data=old_text(actual,*args,**kwargs);return data.replace(old,new) if actual==path else data
            with patch.object(Path,'read_text',alter),self.assertRaises(ValueError):source.audit(self.root,True)
            checks+=1
        path=self.work/'uoptlist'
        def altered_bytes(actual,*args,**kwargs):
            data=old_bytes(actual,*args,**kwargs);return data+b'\0' if actual==path else data
        with patch.object(Path,'read_bytes',altered_bytes),self.assertRaises(ValueError):source.audit(self.root,True)
        checks+=1
        (self.out/'capture-controls.json').write_text(json.dumps(dict(corruptions=checks),indent=2)+'\n')

    def test_05_grouped_shapes_and_sampled_public_behavior(self):
        rom=(self.root/'conker/conker.us.bin').read_bytes();helpers={}
        for entry,count in guest.HELPERS.items():
            helpers.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,rom,entry-0x14FD2B50)))
        count=0
        for name,_ in groups.forms():
            obj=self.groupout/('owner-'+name+'.o')
            data,functions=groups.source.neighbor.baseline.model.link_owner(self.root,self.groupout,obj,groups.source.OWNER)
            f=functions[groups.source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            self.assertNotEqual(len(words),321)
            for state,position,flag in itertools.product((2,3,0),range(8),(0,64)):
                memory,args=guest.fixture(state,position,flag=flag);expected,calls,_=guest.reference(memory,args)
                actual=guest.ProjectionOracle(words,memory,args,helpers,(count&1)*8).run()
                self.assertEqual((guest.public(actual.memory),actual.calls),(guest.public(expected),calls))
                count+=1
        self.assertEqual(count,192)
        (self.out/'grouped-public.json').write_text(json.dumps(dict(sampled_cases=count,
            rejected_screens=len(self.screens),matching_credit=0),indent=2)+'\n')

    def test_06_live_and_frozen_inputs_fail_closed(self):
        count=0;checkpoint=source.source.source
        for index,name in enumerate(checkpoint.INPUTS):
            for target in (self.root/name,self.out/('before-%02d'%index)):
                def altered(path,*args,**kwargs):
                    data=checkpoint.raw_read(path,*args,**kwargs);return data+b'\0' if path==target else data
                with patch.object(Path,'read_bytes',altered),self.assertRaises(ValueError):source.audit(self.root,True)
                count+=1
        self.assertEqual(count,30)
        (self.out/'input-controls.json').write_text(json.dumps(dict(corruptions=count),indent=2)+'\n')


if __name__=='__main__':unittest.main()
