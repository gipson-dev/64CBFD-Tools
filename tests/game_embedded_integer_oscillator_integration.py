"""Original callback dispatch and return gate; retain parent-stub boundary."""
import itertools
import json
import struct

PARENT, TABLE, CLEANUPS, RELEASE, DETACH = 0x1513C060, 0x80089C70, 0x80089CA8, 0x1516972C, 0x1513F6C0

def aligned_hits(data, word):
    needle=struct.pack('>I',word);start=0;found=[]
    while True:
        at=data.find(needle,start)
        if at<0:return found
        if at%4==0:found.append(at)
        start=at+1

def qualify(root, output, oracle):
    g=oracle;rom=(root/'conker/conker.us.bin').read_bytes();image=(root/'conker/build/conker.us.elf').read_bytes()
    parent=struct.unpack_from('>188I',rom,0x169510)
    registry=struct.unpack_from('>14I',rom,0x22E730)
    cleanup_table=struct.unpack_from('>4I',rom,0x22E778-16)
    assert registry[7:9]==(0x151AB090,0x150C5E0C)
    assert cleanup_table[1:3]==(0x151AB180,0x150C5EFC)
    for address,offset,n in ((TABLE,0x22E730,56),(CLEANUPS,0x22E768,16)):
        at=g.elf_slot_offset(image,address,n);assert image[at:at+n]==rom[offset:offset+n]
    census=[]
    for target,offset in ((0x150C5E0C,0x22E750),(0x151AB090,0x22E74C)):
        direct=aligned_hits(rom,0x0C000000|(target>>2&0x3FFFFFF));literal=aligned_hits(rom,target)
        assert not direct and literal==[offset]
        census.append(dict(function=hex(target),direct_JAL_sites=direct,literal_ROM=literal))

    class ParentOracle(g.Oracle):
        def __init__(self, words, memory, c, symbols, target, raw, cleanup_mode, connected):
            self.cleanup_mode=cleanup_mode
            super().__init__(words,memory,c,symbols,PARENT,raw=raw,connected=connected,target_entry=target)
        def record_call(self,t):
            if t in (self.target_entry,0x150C5EFC,0x151AB180,RELEASE):
                self.calls.append((t,(g.u32(self.r[4]),)))
            elif t==DETACH:self.calls.append((t,tuple(g.u32(v)for v in self.r[4:7])))
            else:super().record_call(t)
        def hook(self,t):
            if t in (self.s['integer'],self.s['floating']):return super().hook(t)
            if t==RELEASE:g.put(self.memory,self.r[4]+0x10,0)
            elif t==DETACH:pass
            else:assert t in (0x150C5EFC,0x151AB180)
            for j in range(4):self.put(self.r[29]+j*4,0xB5000000+j,4)
            for j in (1,2,3,*range(4,16),24,25):self.r[j]=0xA5000000+j
            self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
            self.r[2]=int(self.cleanup_mode==2)

    count=0;visits=set();cleanup_seen=set();witnesses=0
    for target in range(2):
        entry,s,roots=g.programs(output,target,0);slot=8 if target==0 else 7;cleanup=0x150C5EFC if target==0 else 0x151AB180
        cleanup_rom=0xF33AC if target==0 else 0x1D8630
        real_cleanup=dict(zip(range(cleanup,cleanup+68,4),struct.unpack_from('>17I',rom,cleanup_rom)))
        for active,timer,counter,ticks,notification,remaining,phase,mode,mutation in itertools.product((0,1),(0,1),(-1,4),(0,1,3),(0,255),(-1,2),(0,8),range(4),(0,2)):
            c=g.Case(remaining=remaining,ticks=ticks,notification=notification,phase=phase,mutation=mutation)
            initial=g.fixture(c,s);p=g.OWNER
            for at,v,n in ((0x10,active,4),(0x18,timer,4),(0x1C,counter,2),(0x1E,0,1),(0x20,5,4),(0x24,0,4),(0x80,slot,1),(0x81,0 if mode==0 else (2 if target==0 else 1),1),(0xB0,g.SECOND,4),(0xB8,0,4),(0xBC,0,4),(0xC0,0,4)):
                g.put(initial,p+at,v,n)
            g.put(initial,0x80090B64,3,1)
            for i,v in enumerate(registry):g.put(initial,TABLE+4*i,v)
            for i,v in enumerate(cleanup_table):g.put(initial,CLEANUPS+4*i,v)
            expected=g.public(dict(initial),c);calls=[];stop=False
            if active:
                if timer:
                    new=g.half(counter-ticks);g.put(expected,p+0x1C,new,2);stop=new<0
                before=dict(initial);before.update(expected)
                expected,subcalls,result=g.reference(before,c,s,home=g.STACK+phase-32)
                calls=[(entry,(p,)),*subcalls];stop=stop or not result
                if not stop:
                    delta=g.signed(g.read(expected,p+0x24))
                    if delta:
                        value=g.u32(5+delta*g.read(expected,s['clock']))
                        assert 0<=g.signed(value)<=0x2FFFF,'Bounded animation domain'
                        g.put(expected,p+0x20,value)
                if stop:
                    if mode:
                        calls.append((cleanup,(p,)))
                        if mode==3:
                            g.put(expected,g.SECOND+(0x58 if target==0 else 0x70),0)
                            g.put(expected,p+0xB0,0);g.put(expected,p+0x18,timer|2)
                            calls.append((DETACH,(p,0,0)))
                    if mode in (0,2):calls.append((RELEASE,(p,)));g.put(expected,p+0x10,0)
            models=[]
            for i,words in enumerate(roots):
                connected=dict(zip(range(entry,entry+240,4),words))
                if mode==3:connected.update(real_cleanup)
                m=ParentOracle(parent,initial,c,s,entry,i==2,mode,connected).run()
                assert (g.public(m.memory,c),m.calls)==(expected,calls),(target,c,active,timer,counter,mode,m.calls,calls)
                assert m.r[29]==g.STACK+phase
                models.append(m);visits.update(m.visits);cleanup_seen.update(set(real_cleanup)&m.visits)
            assert g.state(models[0])==g.state(models[1])==g.state(models[2])
            count+=1
            if active and not timer and notification and mode==0 and mutation==0 and remaining==2 and ticks==0 and phase==0:
                old=struct.unpack_from('>3I',image,g.elf_slot_offset(image,entry,12));stale_code=dict(zip(range(entry,entry+12,4),old))
                stale=ParentOracle(parent,initial,c,s,entry,False,mode,stale_code).run()
                assert (RELEASE,(p,)) in stale.calls and (RELEASE,(p,))not in calls
                witnesses+=1
    assert cleanup_seen==set(range(0x150C5EFC,0x150C5EFC+68,4))|set(range(0x151AB180,0x151AB180+68,4))
    retained=struct.unpack_from('>3I',image,g.elf_slot_offset(image,PARENT,12));assert retained==(0x00001025,0x03E00008,0)
    report=dict(success=True,private_only=True,matching_credit=0,cases=count,executions=count*3,parent='func_1513C060',parent_words=188,visited_parent_words=len(set(range(PARENT,PARENT+752,4))&visits),callback_slots=[7,8],registry_entries=14,cleanup_registry_entries=4,original_cleanup_words_each=17,all34_cleanup_words_executed=True,wrong_target_stub_return_rejected=witnesses,complete_parent_coverage_claimed=False,retained_parent_parity_claimed=False,retained_parent_stub_bytes=12,bounded_no_fade_and_no_animation_wrap=True,scripted_release_and_detach_providers=True,census=census)
    (output/'private-callers-v17.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
