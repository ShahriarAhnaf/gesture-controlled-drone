"""Read-only native connectivity and H/V/45 geometry audit of saved KiCad boards.
Native DRC remains the acceptance authority, including separate zone islands.
"""
import collections,hashlib,json,pathlib
import pcbnew as p
R=pathlib.Path(__file__).resolve().parents[1]
for side in ['left','right','hub']:
 stem=side+'-hand' if side!='hub' else 'hub';path=R/side/(stem+'.kicad_pcb');before=hashlib.sha256(path.read_bytes()).hexdigest();b=p.LoadBoard(str(path));b.BuildConnectivity();conn=b.GetConnectivity();pads={};nets=collections.defaultdict(list);items={}
 key=lambda o:o.m_Uuid.AsString()
 for fp in b.GetFootprints():
  for pad in fp.Pads():
   k=key(pad);pt=pad.GetPosition();name=fp.GetReference()+'.'+pad.GetNumber()+('@%.4f,%.4f'%(p.ToMM(pt.x),p.ToMM(pt.y)));pads[k]=name;items[k]=pad
   if pad.GetNetname():nets[pad.GetNetname()].append(k)
 groups={}
 for net,ids in nets.items():
  remaining=set(ids);gs=[]
  while remaining:
   first=next(iter(remaining));todo=[items[first]];seen=set();members=[]
   while todo:
    item=todo.pop();k=key(item)
    if k in seen:continue
    seen.add(k)
    if k in remaining:remaining.remove(k);members.append(pads[k])
    todo.extend(o for o in conn.GetConnectedItems(item) if key(o) not in seen)
   gs.append(sorted(members))
  groups[net]=gs
 angles=[]
 for t in b.GetTracks():
  if isinstance(t,p.PCB_VIA):continue
  a,z=t.GetStart(),t.GetEnd();dx,dy=abs(z.x-a.x),abs(z.y-a.y)
  if min(dx,dy)>100 and abs(dx-dy)>100:angles.append(key(t))
 opens={n:g for n,g in groups.items() if not n.startswith('unconnected-') and len(g)>1}
 after=hashlib.sha256(path.read_bytes()).hexdigest();report={'inputs':{'board':{'sha256':before}},'source_changed_during_audit':[] if before==after else [str(path)],'connected_pad_groups':groups,'nonconforming_track_ids':angles,'disconnected_functional_nets':opens,'notes':'Read-only traversal of KiCad native connectivity. Native DRC separately checks zone islands and all physical pads.'}
 (R/'build'/side/'native-connectivity.json').write_text(json.dumps(report,indent=2)+'\n');assert not opens and not angles and before==after
 print(side,': native functional pad groups connected; H/V/45 tracks passed')
