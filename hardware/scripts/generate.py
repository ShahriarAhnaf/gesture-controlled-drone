"""Rebuild the two USB-powered carrier boards using KiCad's bundled Python.
Run: /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 hardware/scripts/generate.py
"""
import json, math, pathlib, uuid, re, os
import pcbnew as p
ROOT=pathlib.Path(__file__).resolve().parents[1]
LIB=pathlib.Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport')
os.environ['KICAD10_3DMODEL_DIR']=str(LIB/'3dmodels')
def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL,'palmpilot/'+s))
def q(s): return json.dumps(str(s))
def mm(x): return p.FromMM(x)
def V(x,y): return p.VECTOR2I(mm(x),mm(y))
def symbol_source(lib,name):
 s=(LIB/'symbols'/f'{lib}.kicad_sym').read_text(); start=s.index(f'(symbol "{name}"'); i=start;depth=0;quoted=False;esc=False
 for i in range(start,len(s)):
  c=s[i]
  if quoted:
   if esc:esc=False
   elif c=='\\':esc=True
   elif c=='"':quoted=False
  elif c=='"':quoted=True
  elif c=='(':depth+=1
  elif c==')':
   depth-=1
   if depth==0:return s[start:i+1].replace(f'(symbol "{name}"',f'(symbol "{lib}:{name}"',1)

def connector(name,n,names=None,right=False):
 body=f'(symbol "PalmPilot:{name}" (pin_names (offset 1.0)) (in_bom yes) (on_board yes) (property "Reference" "J" (at 0 0 0) (effects (font (size 1.27 1.27)))) (property "Value" "{name}" (at 0 0 0) (effects (font (size 1.27 1.27))))'
 if n==22:
  body+='(symbol "'+name+'_0_1" (rectangle (start -12.7 29.21) (end 12.7 -29.21) (stroke (width 0.254) (type default)) (fill (type background))))'
  x=-17.78; orient=0; top=26.67;length=5.08
 else:
  body+='(symbol "'+name+'_0_1" (rectangle (start -2.54 5.08) (end 2.54 '+str(-2.54*(n-1)-2.54)+') (stroke (width 0.254) (type default)) (fill (type background))))'
  x=7.62 if right else -7.62;orient=180 if right else 0;top=2.54;length=5.08
 body+='(symbol "'+name+'_1_1"'
 for i in range(n):
  body+=f'(pin passive line (at {x} {top-i*2.54:.4f} {orient}) (length {length}) (name {q(names[i] if names else "")} (effects (font (size 1.0 1.0)))) (number "{i+1}" (effects (font (size 1.0 1.0)))))'
 return body+'))'
J1=['3V3','3V3','RST','GPIO4','GPIO5','GPIO6','GPIO7','GPIO15','GPIO16','GPIO17','GPIO18','GPIO8','GPIO3','GPIO46','GPIO9','GPIO10','GPIO11','GPIO12','GPIO13','GPIO14','5V','GND']
J3=['GND','TX_GPIO43','RX_GPIO44','GPIO1','GPIO2','GPIO42','GPIO41','GPIO40','GPIO39','GPIO38','GPIO37','GPIO36','GPIO35','GPIO0','GPIO45','GPIO48','GPIO47','GPIO21','USB_D+','USB_D-','GND','GND']
SOCKET='Connector_PinSocket_2.54mm:PinSocket_1x22_P2.54mm_Vertical'
JST2='Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical'
JST4='Connector_JST:JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical'
RFP='Resistor_SMD:R_0805_2012Metric';CFP='Capacitor_SMD:C_0805_2012Metric'
LIBSYMS=[connector('DevKit_J1',22,J1),connector('DevKit_J3',22,J3),connector('Flex',2,right=True),connector('IMU',4,['GND','3V3','SDA','SCL']),connector('Switch',2,['SW','GND'])]+[symbol_source(a,b) for a,b in [('Device','R_Small_US'),('Device','C'),('power','+3V3'),('power','GND'),('power','PWR_FLAG')]]
(ROOT/'libraries'/'PalmPilot.kicad_sym').write_text('(kicad_symbol_lib (version 20250114) (generator "palmpilot")'+''.join(LIBSYMS[:5]).replace('PalmPilot:','')+')')
def generate_hands():
 for side in ['left','right']:
  out=ROOT/side;out.mkdir(exist_ok=True);name=side+'-hand';sid=uid(side);items=[];comps={};b=p.BOARD();b.SetCopperLayerCount(2)
  nets={}
  for net in ['+3V3','GND','THUMB','INDEX','MIDDLE','RING','LITTLE','SDA','SCL']+(['ENABLE','SW'] if side=='left' else []):
   ni=p.NETINFO_ITEM(b,net if net in ['+3V3','GND'] else '/'+net);b.Add(ni);nets[net]=ni
  def snap(x):return round(round(x/1.27)*1.27,4)
  def wire(a,c):
   a=tuple(map(snap,a));c=tuple(map(snap,c));items.append(f'(wire (pts (xy {a[0]} {a[1]}) (xy {c[0]} {c[1]})) (stroke (width 0) (type default)) (uuid {uid(side+str(a)+str(c))}))')
  def label(net,x,y):
   x,y=snap(x),snap(y);items.append(f'(label {q(net)} (at {x} {y} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid {uid(side+net+str(x)+str(y))}))')
  def text(t,x,y,size=1.27):items.append(f'(text {q(t)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left)) (uuid {uid(side+t)}))')
  def rect(x,y,w,h):items.append(f'(rectangle (start {x} {y}) (end {x+w} {y+h}) (stroke (width 0.254) (type default) (color 70 100 140 1)) (fill (type none)) (uuid {uid(side+str((x,y,w,h)))}))')
  def sym(lib,ref,value,x,y,fp='',pins=None,angle=0,prop=None):
   x,y=snap(x),snap(y);ident=uid(side+ref);s=f'(symbol (lib_id {q(lib)}) (at {x} {y} {angle}) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {ident})'
   places=prop or [(x+3,y-1),(x+3,y+1.5)]
   for (key,val),pos in zip([('Reference',ref),('Value',value)],places):s+=f'(property {q(key)} {q(val)} (at {snap(pos[0])} {snap(pos[1])} 0) (effects (font (size 1.27 1.27)) (justify left)'+(' (hide yes)' if (ref.startswith('#') and key=='Reference') or ref.startswith('#FLG') else '')+'))'
   s+=f'(property "Footprint" {q(fp)} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))'
   for pin in pins or []:s+=f'(pin {q(pin)} (uuid {uid(side+ref+str(pin))}))'
   s+=f'(instances (project {q(name)} (path "/{sid}" (reference {q(ref)}) (unit 1)))))';items.append(s)
   if fp:comps[ref]={'uuid':ident,'value':value,'footprint':fp,'nets':{}}
  def power(net,x,y):
   ref='#PWR'+str(len(items));sym('power:'+net,ref,net,x,y,prop=[(x,y),(x-1.5,y-3 if net=='+3V3' else y+3)])
  def passive(ref,val,x,y,net1,net2,cap=False):
   sym('Device:C' if cap else 'Device:R_Small_US',ref,val,x,y,CFP if cap else RFP,pins=['1','2'])
   comps[ref]['nets']={'1':net1,'2':net2}
   return 3.81 if cap else 2.54
  rect(10,15,101,103);text('ESP32-S3-DevKitC-1 / SOCKETS',14,20,1.6)
  for ref,lib,x,mapn in [('J1','DevKit_J1',38,{1:'+3V3',2:'+3V3',4:'MIDDLE',5:'RING',6:'LITTLE',12:'SDA',15:'SCL',22:'GND',**({7:'ENABLE'} if side=='left' else {})}),('J3','DevKit_J3',88,{1:'GND',4:'THUMB',5:'INDEX',21:'GND',22:'GND'})]:
   sym('PalmPilot:'+lib,ref,'1x22 SOCKET',x,61.5,SOCKET,pins=map(str,range(1,23)),prop=[(x-12,29),(x-12,32)])
   for i in range(1,23):
    px=x-17.78;py=round(61.5-26.67+(i-1)*2.54,4)
    if i in mapn:
     wire((px,py),(px-5.08,py));label(mapn[i],px-5.08,py);comps[ref]['nets'][str(i)]=mapn[i]
    else:items.append(f'(no_connect (at {snap(px)} {snap(py)}) (uuid {uid(side+ref+str(i)+"nc")}))')
  sym('power:PWR_FLAG','#FLG01','PWR_FLAG',15.14,34.83,prop=[(15,34),(15,29)])
  sym('power:PWR_FLAG','#FLG02','PWR_FLAG',65.14,34.83,prop=[(65,34),(65,29)])
  text('USB power/programming stays on DevKit.',14,103)
  text('Genuine 22-pin headers; 22.86 mm row spacing.',14,108)
  text('No battery circuit. GPIO10 remains reserved.',14,113)
  rect(116,15,169,114);text('FIVE FLEX INPUTS / EXISTING ADC1 PIN MAP',120,20,1.6)
  for i,net in enumerate(['THUMB','INDEX','MIDDLE','RING','LITTLE']):
   y=29+i*19.5;ref='J'+str(i+4)
   sym('PalmPilot:Flex',ref,net,128,y,JST2,pins=['1','2'],prop=[(120,y-4),(147,y+4)])
   comps[ref]['nets']={'1':'+3V3','2':net}
   a=(135.62,y-2.54);wire(a,(143,y-2.54));power('+3V3',143,y-2.54)
   y=round(y,4);wire((135.62,y),(245,y));label(net,245,y)
   # Directly connected shunts; dots explicitly mark branch points.
   for xx in [184,214]:
    items.append(f'(junction (at {snap(xx)} {snap(y)}) (diameter 0) (color 0 0 0 0) (uuid {uid(side+net+str(xx))}))')
   d=passive('R'+str(i+1),'47kR 1%',184,y+6.35,net,'GND');wire((184,y),(184,y+6.35-d));wire((184,y+6.35+d),(184,y+11.43))
   d=passive('C'+str(i+1),'100nF',214,y+6.35,net,'GND',True);wire((214,y),(214,y+6.35-d));wire((214,y+6.35+d),(214,y+11.43));wire((184,y+11.43),(214,y+11.43));power('GND',214,y+11.43)
  rect(10,124,101,55);text('LEFT ENABLE / ACTIVE LOW' if side=='left' else 'RIGHT HAND / NO ENABLE CIRCUIT',14,130,1.6)
  if side=='left':
   d=passive('R6','10kR',32,142,'+3V3','ENABLE');power('+3V3',32,137);wire((32,137),(32,142-d));wire((32,142+d),(32,149));wire((32,149),(83,149));label('ENABLE',83,149)
   items.append(f'(junction (at {snap(54)} {snap(149)}) (diameter 0) (color 0 0 0 0) (uuid {uid(side+"enable-junction")}))')
   d=passive('C6','100nF',54,158,'ENABLE','GND',True);wire((54,149),(54,158-d));wire((54,158+d),(54,165));power('GND',54,165)
   d=passive('R7','1kR',32,157,'ENABLE','SW');wire((32,149),(32,157-d));wire((32,157+d),(32,167));label('SW',32,167)
   sym('PalmPilot:Switch','J9','EXTERNAL N.O.',92,159,JST2,pins=['1','2'],prop=[(69,169),(69,173)])
   comps['J9']['nets']={'1':'SW','2':'GND'};label('SW',84.38,156.46);wire((84.38,159),(78,159));power('GND',78,159)
  else:
   text('GPIO7 has no PCB connection.',15,141);text('Flash the RIGHT hand firmware configuration.',15,148);text('Thumb / index / middle / ring / little',15,157);text('retain GPIO1 / 2 / 4 / 5 / 6.',15,163)
  rect(116,134,169,29);text('MOTION BREAKOUT / ADAFRUIT #5543',120,140,1.6)
  sym('PalmPilot:IMU','J2','PH-4 HARNESS',156,153,JST4,pins=['1','2','3','4'],prop=[(160,151),(160,155)])
  comps['J2']['nets']={'1':'GND','2':'+3V3','3':'SDA','4':'SCL'}
  for i,net in enumerate(['GND','+3V3','SDA','SCL']):label(net,148.38,round(150.46+2.54*i,4))
  text('1 GND   2 VIN(3V3)   3 SDA   4 SCL',184,147)
  text('Cabled to QT or breakout header; not a QT socket.',184,153,1.1)
  text('100 kHz / 0x6A + 0x1C / no extra pull-ups.',184,157,1.1)
  text('Mount sensor rigidly; preserve calibrated axes.',184,161,1.1)
  text('Flex is external: connector pin 1 = 3V3, pin 2 = ADC. USB-only prototype. Rev A.',12,185,1.2)
  sch=f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {sid}) (paper "A4") (title_block (title "PalmPilot {side.upper()} glove carrier") (date "2026-11-17") (rev "A") (company "USB-powered prototype / frozen GPIO map")) (lib_symbols '+''.join(LIBSYMS)+')'+''.join(items)+'(embedded_fonts no))'
  (out/(name+'.kicad_sch')).write_text(sch)
  (out/'sym-lib-table').write_text('(sym_lib_table (lib (name "PalmPilot") (type "KiCad") (uri "${KIPRJMOD}/../libraries/PalmPilot.kicad_sym") (options "") (descr "Carrier connector symbols")))')
  # PCB locations in mm; top view, antenna toward fingers.
  fps={}
  def add(ref,x,y,angle=0):
   c=comps[ref];lib,fn=c['footprint'].split(':');fp=p.FootprintLoad(str(LIB/'footprints'/(lib+'.pretty')),fn);fp.SetReference(ref);fp.SetValue(c['value']);fp.SetPosition(V(x,y));fp.SetOrientationDegrees(angle)
   fp.SetPath(p.KIID_PATH('/'+sid+'/'+c['uuid']));fp.SetFPID(p.LIB_ID(lib,fn));b.Add(fp)
   for pad in fp.Pads():
    net=c['nets'].get(pad.GetNumber())
    if net:pad.SetNet(nets[net])
    elif ref in ['J1','J3']:
     n=pad.GetNumber();pn=(J1 if ref=='J1' else J3)[int(n)-1];nn='unconnected-('+ref+'-'+pn+'-Pad'+n+')';ni=p.NETINFO_ITEM(b,nn);b.Add(ni);pad.SetNet(ni)
   fp.Value().SetVisible(False);fp.Reference().SetTextSize(V(.8,.8));fp.Reference().SetTextThickness(mm(.12));fp.Reference().SetVisible(False)
   fps[ref]=fp;return fp
  def pos(ref,pad):
   po=next(x for x in fps[ref].Pads() if x.GetNumber()==str(pad)).GetPosition();return(p.ToMM(po.x),p.ToMM(po.y))
  def track(net,pts,layer=p.F_Cu,width=.25):
   for a,c in zip(pts,pts[1:]):
    if math.dist(a,c)<1e-6:continue
    t=p.PCB_TRACK(b);t.SetStart(V(*a));t.SetEnd(V(*c));t.SetWidth(mm(width));t.SetLayer(layer);t.SetNet(nets[net]);b.Add(t)
  def join(net,a,c,layer=p.F_Cu,width=.25):
   # Fixed 45-degree corner plus straight approach.
   dx=c[0]-a[0];dy=c[1]-a[1];d=min(abs(dx),abs(dy));m=(a[0]+math.copysign(d,dx),a[1]+math.copysign(d,dy))
   track(net,[a,m,c],layer,width)
  def via(net,x,y):
   v=p.PCB_VIA(b);v.SetPosition(V(x,y));v.SetWidth(mm(.65));v.SetDrill(mm(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(nets[net]);b.Add(v)
  def silk(s,x,y,size=1):
   t=p.PCB_TEXT(b);t.SetText(s);t.SetPosition(V(x,y));t.SetTextSize(V(size,size));t.SetTextThickness(mm(.15));t.SetLayer(p.F_SilkS);b.Add(t)
  add('J1',21.57,14);add('J3',44.43,14)
  adc=[('THUMB','J4','R1','C1',58,22,180,'J3',4),('INDEX','J5','R2','C2',58,35,180,'J3',5),('MIDDLE','J6','R3','C3',6,22,0,'J1',4),('RING','J7','R4','C4',6,35,0,'J1',5),('LITTLE','J8','R5','C5',6,48,0,'J1',6)]
  for net,j,r,c,x,y,ang,h,pin in adc:
   add(j,x,y,ang);rx,cx,vx=(51,49,48) if ang else (13,17,18)
   add(r,rx,y,-90);add(c,cx,y,-90)
   yy=y-2;target=(vx,yy);a=pos(j,2);join(net,a,(a[0]+(-2 if ang else 2),yy));track(net,[(a[0]+(-2 if ang else 2),yy),target])
   for ref in [r,c]:
    a=pos(ref,1);track(net,[a,(a[0],yy)])
    g=pos(ref,2);via('GND',g[0],g[1]+1.2);track('GND',[g,(g[0],g[1]+1.2)])
   via(net,*target);hp=pos(h,pin)
   if net in ['THUMB','MIDDLE']:join(net,target,hp,p.B_Cu)
   else:
    lane=47 if net=='INDEX' else (19 if net=='RING' else 20)
    dx=abs(lane-hp[0]);sgn=1 if ang else -1
    track(net,[target,(lane,yy-abs(lane-vx)),(lane,hp[1]+dx),hp],p.B_Cu)
   silk(j+' '+net,x+(-1 if ang else 1),y+5,.8)
  # 3V3 perimeter branch. Signal conditioning and IMU loads only; MCU powered on DevKit.
  track('+3V3',[pos('J1',1),(16,14),(14,16),(3,16),(3,68),(5,70),(61,70),(63,68),(63,22)],width=.5)
  track('+3V3',[pos('J1',1),pos('J1',2)],width=.5)
  for net,j,r,c,x,y,ang,h,pin in adc:track('+3V3',[(63 if ang else 3,y),pos(j,1)],width=.5)
  add('J2',54,54)
  track('+3V3',[pos('J2',2),(56,70)],p.B_Cu,width=.5);via('+3V3',56,70)
  track('SDA',[pos('J1',12),(26,46.37),(26,52),(29.91,55.91),(57,55.91),(58,54.91),pos('J2',3)])
  track('SCL',[pos('J1',15),(25,52.99),(25,54.45),(29,58.45),(55.55,58.45),pos('J2',4)])
  silk('J2 IMU  G 3V SDA SCL',54,61,.8)
  if side=='left':
   add('J9',7,63,180);add('R6',14,57,-90);add('R7',14,63,180);add('C6',18,63,-90)
   track('+3V3',[(3,54),(12,54),(14,56),pos('R6',1)],width=.4)
   en=(18,61);via('ENABLE',*en)
   join('ENABLE',pos('R6',2),(16,59.7125));track('ENABLE',[(16,59.7125),(16,61),en]);join('ENABLE',en,pos('C6',1));join('ENABLE',en,(16,63));track('ENABLE',[(16,63),pos('R7',1)])
   track('ENABLE',[pos('J1',7),(22.8,30.47),(22.8,58.45),(20,58.45),(18,60.45),(18,61)],p.B_Cu)
   track('SW',[pos('R7',2),(10,63),pos('J9',1)])
   g=pos('C6',2);track('GND',[g,(18,66)]);via('GND',18,66)
   silk('J9 ENABLE',9,68,.8)
  # Ground planes on both faces, tied through device grounds, bypass vias and stitches.
  poly=[(1,1),(17,1),(17,13.2),(49,13.2),(49,1),(65,1),(65,77),(1,77)]
  for layer in [p.F_Cu,p.B_Cu]:
   z=p.ZONE(b);z.SetLayer(layer);z.SetNet(nets['GND']);z.SetLocalClearance(mm(.25));z.SetThermalReliefGap(mm(.3));z.SetThermalReliefSpokeWidth(mm(.3));z.SetMinThickness(mm(.2));o=z.Outline();o.NewOutline()
   for x,y in poly:o.Append(mm(x),mm(y))
   b.Add(z)
  for x,y in [(5,12),(61,12),(5,29),(61,29),(5,42),(61,42),(5,58),(61,48),(28,38),(38,38),(28,64),(38,64),(9,73),(57,73)]:via('GND',x,y)
  # Chamfered outline and finger-facing antenna notch.
  outline=[(3,0),(18,0),(18,10),(23.2,10),(23.2,13.5),(42.8,13.5),(42.8,10),(48,10),(48,0),(63,0),(66,3),(66,75),(63,78),(3,78),(0,75),(0,3)]
  for a,c in zip(outline,outline[1:]+outline[:1]):
   s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(V(*a));s.SetEnd(V(*c));s.SetLayer(p.Edge_Cuts);s.SetWidth(mm(.05));b.Add(s)
  for i,(x,y) in enumerate([(6,7),(60,7),(6,73),(60,73)]):
   fp=p.FootprintLoad(str(LIB/'footprints'/'MountingHole.pretty'),'MountingHole_2.7mm_M2.5');fp.SetReference('H'+str(i+1));fp.SetPosition(V(x,y));fp.Value().SetVisible(False);fp.Reference().SetVisible(False);fp.SetAttributes(p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES|p.FP_BOARD_ONLY);b.Add(fp)
  silk('PALMPILOT / '+side.upper(),33,73.5,1.2);silk('USB ONLY   /   REV A',33,76,.8);silk('ANTENNA GAP',33,15,.8)
  # Describe fitted DevKit envelope on fabrication layer, not a second electrical footprint.
  silk('USB CABLE TO WRIST',33,70.5,.8)
  settings=b.GetDesignSettings();settings.SetBoardThickness(mm(1.6))
  p.SaveBoard(str(out/(name+'.kicad_pcb')),b)
  project={'board':{'design_settings':{'rules':{'min_clearance':0.17,'min_track_width':0.2,'min_via_diameter':0.6,'min_through_hole_diameter':0.3,'min_copper_edge_clearance':0.25}}},'meta':{'filename':name+'.kicad_pro','version':1},'net_settings':{'classes':[{'name':'Default','clearance':0.17,'track_width':0.25,'via_diameter':0.65,'via_drill':0.3,'microvia_diameter':0.3,'microvia_drill':0.1,'diff_pair_width':0.2,'diff_pair_gap':0.25,'diff_pair_via_gap':0.25}]}}
  (out/(name+'.kicad_pro')).write_text(json.dumps(project,indent=2)+'\n')
  (ROOT/'build'/f'{side}-expected.json').write_text(json.dumps(comps,indent=2))
  print(side,len(comps),'components',len(list(b.GetTracks())),'copper items')

if __name__=='__main__':
 generate_hands()
