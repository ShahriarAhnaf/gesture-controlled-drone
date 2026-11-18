"""Refill, verify, then export the canonical carriers. Native KiCad 10 required."""
import os,pathlib,subprocess,sys,csv,hashlib,json
import pcbnew as p
R=pathlib.Path(__file__).resolve().parents[1]
K='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
os.environ['KICAD10_3DMODEL_DIR']='/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels'
def run(args,log):
 with log.open('w') as f:subprocess.run([K]+list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True)
for side in (sys.argv[1:] or ['left','right','hub']):
 stem=side+'-hand' if side!='hub' else 'hub';d=R/side;out=R/'build'/side;out.mkdir(exist_ok=True);pcb=d/(stem+'.kicad_pcb');sch=d/(stem+'.kicad_sch')
 project=d/(stem+'.kicad_pro');project_text=project.read_text();b=p.LoadBoard(str(pcb));p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(pcb),b);project.write_text(project_text)
 run(['sch','erc','--output',out/'erc.rpt','--exit-code-violations',sch],out/'erc.log')
 run(['pcb','drc','--output',out/'drc.rpt','--schematic-parity','--exit-code-violations',pcb],out/'drc.log')
 run(['sch','export','pdf','--output',out/'schematic.pdf',sch],out/'sch-pdf.log')
 run(['sch','export','svg','--output',out/'schematic-svg',sch],out/'sch-svg.log')
 run(['sch','export','netlist','--format','kicadxml','--output',out/'netlist.xml',sch],out/'netlist.log')
 run(['pcb','export','svg','--output',out/'layers','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Silkscreen,Edge.Cuts','--page-size-mode','2','--mode-multi','--exclude-drawing-sheet',pcb],out/'layers.log')
 run(['pcb','export','pdf','--output',out/'pcb-layers.pdf','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Silkscreen,Edge.Cuts','--mode-multipage',pcb],out/'layers-pdf.log')
 run(['pcb','export','gerbers','--output',out/'gerbers','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,Edge.Cuts',pcb],out/'gerbers.log')
 run(['pcb','export','drill','--output',out/'gerbers','--format','excellon',pcb],out/'drill.log')
 run(['pcb','export','pos','--output',out/'positions.csv','--format','csv','--units','mm','--side','both',pcb],out/'positions.log')
 run(['pcb','render','--output',out/'pcb-top.png','--width','1400','--height','1600','--side','top','--zoom','.78','--quality','basic','--background','opaque',pcb],out/'render.log')
 run(['pcb','export','glb','--output',out/'carrier.glb','--force','--subst-models','--include-pads','--include-silkscreen','--include-soldermask',pcb],out/'glb.log')
 # BOM is an engineering BOM. LCSC substitutions and assembly ordering are not selected.
 expected=json.loads((R/'build'/(side+'-expected.json')).read_text())
 with (out/'bom.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['Reference','Value','Footprint','Quantity','Manufacturer','MPN','LCSC'])
  for ref,c in expected.items():w.writerow([ref,c['value'],c['footprint'],1]+[c.get('fields',{}).get(k,'') for k in ['Manufacturer','MPN','LCSC']])
  if side!='hub':w.writerow(['IMU','Adafruit #5543','External cabled breakout',1]);w.writerow(['FLEX','Adafruit #1070','External flex sensor',5])
 print(side,'ERC/DRC passed; exported',flush=True)
