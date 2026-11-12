import json,struct
from tools.tests import game_twin_view_vertices_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
START=0x1513DC00;NULL_END=0x1513DC38;NONNULL_END=0x1513DC68
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>14I',rom,START-0x15000000+0x2d4b0);assert 0x0320f809 in window;reports=[]
 for target,owner,index in g.TARGETS:
  entry=int(target,16);retail=struct.unpack_from('>119I',rom,entry-0x15000000+0x2d4b0);candidate=g.words(target);assert struct.unpack_from('>I',rom,0x22e8dc+4*index)[0]==entry;count=0;branches=set()
  for c in g.cases():
   for ws in (retail,candidate):
    m=g.Oracle(ws,c,entry);m.r[16]=g.ACTOR;m.r[6]=g.u32(c.view);m.memory[g.ACTOR+0x73]=index;g.wr(m.memory,g.TABLE+4*index,entry,4);m.initial=dict(m.memory);expected=g.reference(m.initial,c,home=m.r[29]);home=m.r[29]
    code=dict(zip(range(START,NULL_END,4),window));code.update(zip(range(entry,entry+4*len(ws),4),ws));code.update(g.base.helpers(c));code[NULL_END]=0;code[NONNULL_END]=0;m.code=WindowCode(code,m);m.code.ends=(NULL_END,NONNULL_END);m.entry=START
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('caller boundary not reached')
    called=(entry,(g.ACTOR,g.u32(g.half(c.view))));assert m.calls==[called]+expected['calls'],(target,c,m.calls,expected['calls']);assert g.base.public(m.memory,c)==expected['observed'] and m.r[2]==expected['value'];assert g.rd(m.memory,home+0x6c,4)==expected['value']
    expected_end=NONNULL_END if expected['value'] else NULL_END;assert expected_end in m.visits,(target,c,expected_end,m.visits[-5:]);branches.add(expected_end)
   count+=1
  assert branches=={NULL_END,NONNULL_END};reports.append(dict(target=target,index=index,cases=count,null_and_nonnull_branches=True))
 report=dict(targets=reports,caller='func_1513DB00 renderer dispatch window',table='D_80089E1C',full_parent_qualified=False,source_installed=False);(g.out/'window_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
