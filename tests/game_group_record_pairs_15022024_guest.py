"""Public recovery plus literal normalized private state and caller evidence."""
from dataclasses import replace
import json,struct
from tools.experiments import game_group_record_pairs_15022024_match as p
from tools.tests import game_unmatched_pair_lookup_20261123_guest as old
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_group_record_pairs_15022024_symbolic import proof
r,o=p.ROOT,p.OUT;Case=old.Case;S=old.S;ENTRY=old.ENTRY;MISSING=old.MISSING;ACTIVE=old.ACTIVE;TAGS=old.TAGS;RECORDS=old.RECORDS;OUT=old.OUT;STACK=old.STACK;outputs=old.outputs;reference=old.reference;read=old.read;put=old.put;Oracle=old.Oracle;public=old.public
def cases():
 yield from old.cases()
 for gate in(0,1):
  for count in(0,255):
   for actor in(0,25):
    for match in(-1,0,254):
     for alias in(0,1):yield Case(seed=1000+count+actor,gate=gate,count=count,actor=actor,match=match,alias=alias)
def fixture(c):
 m=old.fixture(c);n=max(4,c.count)
 # The extended scan remains disjoint from private stack and all tables.
 for base,size in((ACTIVE,n*2),(TAGS,n*8),(RECORDS,n*68)):
  for i in range(size):m.setdefault(base+i,(i*29+c.seed*11+0x51)&255)
 m[S['D_800CC2D0']+c.actor*0x32C+0x3B]=(0x48+c.actor)&255
 for i in range(n):
  put(m,ACTIVE+i*2,1 if i==c.match else(c.seed+i)%3,2);put(m,TAGS+i*8,2 if i==c.match else(c.seed+i)%3,2);m[TAGS+i*8+2]=(0x48+c.actor)&255 if i==c.match else(0x49+c.actor+i%255)&255
  put(m,RECORDS+i*68+0x3C,c.primary+i if i!=c.match else c.primary);put(m,RECORDS+i*68+0x40,c.secondary+i if i!=c.match else c.secondary)
 # Nonmatching IDs must never accidentally equal the selected actor.
 for i in range(n):
  if i!=c.match and m[TAGS+i*8+2]==m[S['D_800CC2D0']+c.actor*0x32C+0x3B]:m[TAGS+i*8+2]^=1
 return m
def state(m):return(m.memory,m.trace,m.events,m.calls,m.r,m.f,m.hi,m.lo,m.condition,m.dispatched_word,m.visits)
def main():
 programs={label:bound_blob(*payload(o/path,p.FUNCTION),S)for label,path in {'raw':'selected-final/candidate.o','generic':'qualified-owner/generic.o','generated':'qualified-owner/generated.o','retail':'original-target.o'}.items()}
 assert struct.pack('>91I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0x4F4D4:0x4F640]
 symbolic=proof(programs['raw'],programs['retail']);visits=set();count=0
 for c in cases():
  initial=fixture(c);expected,answer=reference(initial,c);models=[]
  for label,words in programs.items():
   m=Oracle(words,initial,c);m.run();assert public(m.memory,c)==public(expected,c),(label,c,'public');assert m.r[2]==answer;assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:];assert not m.calls;models.append(m)
  assert state(models[1])==state(models[2])==state(models[3]),c
  traces=[[row for row in m.trace if not STACK+c.phase-16<=row[1]<STACK+c.phase]for m in models];assert all(x==traces[0]for x in traces[1:]);visits.update(models[-1].visits);count+=1
 assert[i for i in range(91)if ENTRY+4*i not in visits]==[81]
 q=dict(cases_per_stream=count,streams=4,raw_public_reference_and_access_order_equal=True,normalized_entire_register_private_memory_and_trace_equal=True,symbolic=symbolic,retail_unexecuted_words=[81],source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
def callers():
 # Reuse the measured literal 15-word window with new raw and original bodies.
 old_o=old.o
 try:old.o=o;old.callers();q=json.loads((o/'callers.json').read_text());q['source_installed']=p.installed();(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n')
 finally:old.o=old_o
 return q
def faults():
 from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
 programs=[bound_blob(*payload(o/path,p.FUNCTION),S)for path in('qualified-owner/generic.o','qualified-owner/generated.o','original-target.o')];count=0
 for c in(Case(),Case(count=0),Case(gate=2),Case(match=-1),Case(alias=1),Case(alias=6),Case(alias=7),Case(alias=9),Case(primary=MISSING,secondary=MISSING)):
  initial=fixture(c);complete=Oracle(programs[-1],initial,c);complete.run()
  for cut in range(complete.all_accesses):
   states=[]
   for ws in programs:
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Actual access cut did not fire')
    states.append(state(m))
   assert states[0]==states[1]==states[2];count+=1
 q=dict(full_state_and_dispatched_word_access_prefix_triples=count,source_installed=p.installed(),matching_credit=0);(o/'faults.json').write_text(json.dumps(q,indent=2)+'\n');return q
