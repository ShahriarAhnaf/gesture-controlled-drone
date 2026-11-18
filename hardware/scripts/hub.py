"""Generate the hub carrier. Shares exact socket pin definitions with generate.py."""
import json,pathlib,uuid,math
import pcbnew as p
from generate import ROOT,LIB,J1,J3,SOCKET,RFP,CFP,LIBSYMS,symbol_source,uid,q,mm,V
D=ROOT/'hub';D.mkdir(exist_ok=True);name='hub';sid=uid('hub');items=[];comps={}
def snap(n):return round(round(n/1.27)*1.27,4)
def wire(a,b):
 a=tuple(map(snap,a));b=tuple(map(snap,b));items.append(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid {uid("hub-wire"+str(a)+str(b))}))')
def label(s,x,y):items.append(f'(label {q(s)} (at {snap(x)} {snap(y)} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid {uid("hub-label"+s+str(x)+str(y))}))')
def text(s,x,y,size=1.27):items.append(f'(text {q(s)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left)) (uuid {uid("hub-text"+s)}))')
def rect(x,y,w,h):items.append(f'(rectangle (start {x} {y}) (end {x+w} {y+h}) (stroke (width .254) (type default)) (fill (type none)) (uuid {uid("hub-rect"+str((x,y)))}))')
def sym(lib,ref,value,x,y,fp='',nets=None,props=None):
 x,y=snap(x),snap(y);ident=uid('hub'+ref);s=f'(symbol (lib_id {q(lib)}) (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {ident})'
 for (key,val),pos in zip([('Reference',ref),('Value',value)],props or [(x+3,y-1),(x+3,y+1.5)]):
  hide=ref.startswith('#') and (key=='Reference' or ref.startswith('#FLG'));s+=f'(property {q(key)} {q(val)} (at {snap(pos[0])} {snap(pos[1])} 0) (effects (font (size 1.27 1.27)) (justify left)'+(' (hide yes)' if hide else '')+'))'
 s+=f'(property "Footprint" {q(fp)} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes))) (instances (project "hub" (path "/{sid}" (reference {q(ref)}) (unit 1)))))';items.append(s)
 if fp:comps[ref]={'uuid':ident,'value':value,'footprint':fp,'nets':nets or {}}
def power(net,x,y):sym('power:'+net,'#PWR'+str(len(items)),net,x,y,props=[(x,y),(x-1.3,y+3 if net=='GND' else y-3)])
rect(10,15,101,103);text('HUB / ESP32-S3 SOCKETS',14,20,1.7)
for ref,lib,x,m in [('J1','DevKit_J1',38,{1:'+3V3',2:'+3V3',7:'CALIBRATE',22:'GND'}),('J3','DevKit_J3',88,{1:'GND',21:'GND',22:'GND'})]:
 sym('PalmPilot:'+lib,ref,'1x22 SOCKET',x,61.5,SOCKET,{str(k):v for k,v in m.items()},[(x-12,29),(x-12,32)])
 for i in range(1,23):
  px=x-17.78;py=61.5-26.67+(i-1)*2.54
  if i in m:wire((px,py),(px-5.08,py));label(m[i],px-5.08,py)
  else:items.append(f'(no_connect (at {snap(px)} {snap(py)}) (uuid {uid("hub-nc"+ref+str(i))}))')
sym('power:PWR_FLAG','#FLG1','PWR_FLAG',15.14,34.83);sym('power:PWR_FLAG','#FLG2','PWR_FLAG',65.14,34.83)
text('BLE receives both hands; no wired glove connections.',14,103,1.1);text('GPIO43/44 remain on the DevKit UART bridge.',14,109,1.1)
rect(116,15,169,103);text('CALIBRATE / ACTIVE LOW GPIO7',121,21,1.7)
sym('Device:R_Small_US','R6','10kR',150,40,RFP,{'1':'+3V3','2':'CALIBRATE'});power('+3V3',150,34);wire((150,34),(150,37.46));wire((150,42.54),(150,50));wire((150,50),(220,50));label('CALIBRATE',220,50)
sym('Device:C','C6','100nF',180,60,CFP,{'1':'CALIBRATE','2':'GND'});wire((180,50),(180,56.19));wire((180,63.81),(180,69));power('GND',180,69)
items.append(f'(junction (at {snap(180)} {snap(50)}) (diameter 0) (color 0 0 0 0) (uuid {uid("hub-junction")}))')
sym('Device:R_Small_US','R7','1kR',150,62,RFP,{'1':'CALIBRATE','2':'SW'});wire((150,50),(150,59.46));wire((150,64.54),(150,72));wire((150,72),(140,72));wire((140,72),(140,82));wire((140,82),(149.92,82))
label('SW',150,72)
sym('Switch:SW_Push','SW1','CALIBRATE',155,82,'Button_Switch_THT:SW_PUSH_6mm',{'1':'SW','2':'GND'},[(151,76),(164,82)]);wire((160.08,82),(178,82));power('GND',178,82)
text('Momentary normally-open button.',125,99);text('10kR pull-up / 100nF shunt / 1kR series.',125,106)
text('HOST LINK',15,130,1.7);text('Connect the DevKit port labelled UART to the laptop with a USB data cable.',15,139);text('UART0 / 115200 baud / JSON lines. The same USB connection powers the hub.',15,147)
text('The native ESP32-S3 USB port is not the firmware host transport.',15,155)
text('No flex sensors, no IMU and no battery circuit on the hub.',15,163)
text('Rev A / USB-powered prototype. Calibrate input is disabled in the upstream bench profile.',15,178,1.15)
libs=LIBSYMS+[symbol_source('Switch','SW_Push')]
(D/'hub.kicad_sch').write_text(f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {sid}) (paper "A4") (title_block (title "PalmPilot HUB carrier") (date "2026-11-17") (rev "A") (company "USB-UART host / GPIO7 CALIBRATE")) (lib_symbols '+''.join(libs)+')'+''.join(items)+'(embedded_fonts no))')
(D/'sym-lib-table').write_text('(sym_lib_table (lib (name "PalmPilot") (type "KiCad") (uri "${KIPRJMOD}/../libraries/PalmPilot.kicad_sym") (options "") (descr "Carrier connector symbols")))')
b=p.BOARD();b.SetCopperLayerCount(2);nets={}
for n in ['+3V3','GND','CALIBRATE','SW']:
 ni=p.NETINFO_ITEM(b,n if n in ['+3V3','GND'] else '/'+n);b.Add(ni);nets[n]=ni
fps={}
def add(ref,x,y,ang=0):
 c=comps[ref];lib,fn=c['footprint'].split(':');fp=p.FootprintLoad(str(LIB/'footprints'/(lib+'.pretty')),fn);fp.SetReference(ref);fp.SetValue(c['value']);fp.SetFPID(p.LIB_ID(lib,fn));fp.SetPosition(V(x,y));fp.SetOrientationDegrees(ang);fp.SetPath(p.KIID_PATH('/'+sid+'/'+c['uuid']));b.Add(fp)
 for pad in fp.Pads():
  n=pad.GetNumber();net=c['nets'].get(n)
  if net:pad.SetNet(nets[net])
  elif ref in ['J1','J3']:
   pn=(J1 if ref=='J1' else J3)[int(n)-1];ni=p.NETINFO_ITEM(b,'unconnected-('+ref+'-'+pn+'-Pad'+n+')');b.Add(ni);pad.SetNet(ni)
 fp.Reference().SetVisible(False);fp.Value().SetVisible(False);fps[ref]=fp

def pos(ref,n):
 z=next(x for x in fps[ref].Pads() if x.GetNumber()==str(n)).GetPosition();return(p.ToMM(z.x),p.ToMM(z.y))
def track(net,pts,layer=p.F_Cu,width=.25):
 for a,c in zip(pts,pts[1:]):
  t=p.PCB_TRACK(b);t.SetStart(V(*a));t.SetEnd(V(*c));t.SetWidth(mm(width));t.SetLayer(layer);t.SetNet(nets[net]);b.Add(t)
def via(n,x,y):
 v=p.PCB_VIA(b);v.SetPosition(V(x,y));v.SetWidth(mm(.65));v.SetDrill(mm(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(nets[n]);b.Add(v)
def silk(s,x,y,size=1):
 t=p.PCB_TEXT(b);t.SetText(s);t.SetPosition(V(x,y));t.SetTextSize(V(size,size));t.SetTextThickness(mm(.15));t.SetLayer(p.F_SilkS);b.Add(t)
add('J1',8.57,14);add('J3',31.43,14);add('R6',39,26,-90);add('C6',44,31,-90);add('R7',40,37,-90);add('SW1',39,47)
track('+3V3',[pos('J1',1),pos('J1',2)],width=.5);track('+3V3',[pos('J1',1),(10.8,14),(11,14.2)],width=.5);via('+3V3',11,14.2)
track('+3V3',[(11,14.2),(12.07,15.27),(36.27,15.27),(39,18),(39,23)],p.B_Cu,.4);via('+3V3',39,23);track('+3V3',[(39,23),pos('R6',1)],width=.4)
track('CALIBRATE',[pos('J1',7),(12.38,33.05),(36,33.05),(39,30.05),pos('R6',2)])
track('CALIBRATE',[(39,30.05),pos('C6',1)]);track('CALIBRATE',[(39,30.05),(40,31.05),pos('R7',1)])
track('SW',[pos('R7',2),(40,44),(39,45),(39,47),(45.5,47)])
via('GND',33,14);track('GND',[pos('J3',1),(33,14)],p.B_Cu)
track('GND',[(39,51.5),(45.5,51.5)]);via('GND',44,34);track('GND',[pos('C6',2),(44,34)])
outline=[(3,0),(5,0),(5,10),(10.2,10),(10.2,13.5),(29.8,13.5),(29.8,10),(35,10),(35,0),(51,0),(54,3),(54,75),(51,78),(3,78),(0,75),(0,3)]
for a,c in zip(outline,outline[1:]+outline[:1]):
 s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(V(*a));s.SetEnd(V(*c));s.SetLayer(p.Edge_Cuts);s.SetWidth(mm(.05));b.Add(s)
for lay in [p.F_Cu,p.B_Cu]:
 z=p.ZONE(b);z.SetLayer(lay);z.SetNet(nets['GND']);z.SetLocalClearance(mm(.25));z.SetThermalReliefGap(mm(.3));z.SetThermalReliefSpokeWidth(mm(.3));z.SetMinThickness(mm(.2));o=z.Outline();o.NewOutline()
 for x,y in [(1,1),(4,1),(4,13.2),(36,13.2),(36,1),(53,1),(53,77),(1,77)]:o.Append(mm(x),mm(y))
 b.Add(z)
for x,y in [(4,20),(4,40),(4,62),(50,20),(50,40),(50,62),(18,30),(24,53),(18,68),(46,70)]:via('GND',x,y)
for i,(x,y) in enumerate([(45,6),(6,73),(48,73)],1):
 fp=p.FootprintLoad(str(LIB/'footprints'/'MountingHole.pretty'),'MountingHole_2.7mm_M2.5');fp.SetReference('H'+str(i));fp.SetPosition(V(x,y));fp.Value().SetVisible(False);fp.Reference().SetVisible(False);fp.SetAttributes(p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES|p.FP_BOARD_ONLY);b.Add(fp)
silk('CALIBRATE',43,56,.85);silk('PALMPILOT',26,70,1.2);silk('HUB / REV A',26,73,1);silk('UART USB TO HOST',26,76,.8);silk('ANTENNA',20,15,.8)
p.SaveBoard(str(D/'hub.kicad_pcb'),b)
project=json.loads((ROOT/'left'/'left-hand.kicad_pro').read_text());project['meta']['filename']='hub.kicad_pro';(D/'hub.kicad_pro').write_text(json.dumps(project,indent=2)+'\n');(ROOT/'build'/'hub-expected.json').write_text(json.dumps(comps,indent=2)+'\n')
print('hub generated',len(comps),'components')
