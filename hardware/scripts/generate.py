"""Generate Rev B direct-WROOM hardware. Run with KiCad's bundled Python.
Canonical projects stay at hardware/{left,right,hub}; Rev A is preserved in git.
"""
import json,math,pathlib,re,subprocess,sys,uuid,xml.etree.ElementTree as ET
import pcbnew as p
ROOT=pathlib.Path(__file__).resolve().parents[1]
LIB=pathlib.Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport')
K='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'palmpilot-revb/'+s))
def q(s):return json.dumps(str(s))
def mm(n):return p.FromMM(n)
def V(x,y):return p.VECTOR2I(mm(x),mm(y))
def block(s,start):
 depth=0;quoted=False;escape=False
 for i in range(start,len(s)):
  c=s[i]
  if quoted:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c=='"':quoted=False
  elif c=='"':quoted=True
  elif c=='(':depth+=1
  elif c==')':
   depth-=1
   if depth==0:return s[start:i+1]
 raise ValueError('Unbalanced symbol')
def source(lib,name):
 s=(LIB/'symbols'/(lib+'.kicad_sym')).read_text();s=block(s,s.index('(symbol "'+name+'"'))
 parent=re.search(r'\(extends "([^"]+)"\)',s)
 if parent:
  base=source(lib,parent[1]); children=[]
  for m in re.finditer(r'\(symbol "'+re.escape(parent[1])+r'_[^"]+"',base):children.append(block(base,m.start()).replace(parent[1]+'_',name+'_'))
  s=s.replace(parent[0],'')[:-1]+''.join(children)+')'
 return s.replace('(symbol "'+name+'"','(symbol "'+lib+':'+name+'"',1)
def pins(s):
 out={}
 for m in re.finditer(r'\(pin (?:power_in|power_out|passive|input|output|bidirectional|no_connect|open_collector|tri_state|unspecified) ',s):
  t=block(s,m.start());a=re.search(r'\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)',t);n=re.search(r'\(number "([^"]+)"',t);name=re.search(r'\(name "([^"]*)"',t)
  if a and n:out[n[1]]={'x':float(a[1]),'y':float(a[2]),'angle':float(a[3]),'name':name[1] if name else ''}
 return out

def connector(name,n,names=None,right=False):
 s=f'(symbol "PalmPilot:{name}" (pin_names (offset 1)) (in_bom yes) (on_board yes) (property "Reference" "J" (at 0 0 0) (effects (font (size 1.27 1.27)))) (property "Value" "{name}" (at 0 0 0) (effects (font (size 1.27 1.27))))'
 s+=f'(symbol "{name}_0_1" (rectangle (start -2.54 5.08) (end 2.54 {-2.54*n}) (stroke (width .254) (type default)) (fill (type background)))) (symbol "{name}_1_1"'
 for i in range(n):s+=f'(pin passive line (at {7.62 if right else -7.62} {2.54-i*2.54:.4f} {180 if right else 0}) (length 5.08) (name {q(names[i] if names else "")} (effects (font (size 1.0 1.0)))) (number "{i+1}" (effects (font (size 1.0 1.0)))))'
 return s+'))'
def regulator():
 s='(symbol "PalmPilot:TLV1117LV33" (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 6.35 0) (effects (font (size 1.27 1.27)))) (property "Value" "TLV1117LV33" (at 0 3.81 0) (effects (font (size 1.27 1.27)))) (symbol "TLV1117LV33_0_1" (rectangle (start -5.08 2.54) (end 5.08 -5.08) (stroke (width .254) (type default)) (fill (type background)))) (symbol "TLV1117LV33_1_1"'
 for n,name,typ,x,y,a in [('3','IN','power_in',-7.62,0,0),('2','OUT','power_out',7.62,0,180),('1','GND','power_in',0,-7.62,90)]:s+=f'(pin {typ} line (at {x} {y} {a}) (length 2.54) (name "{name}" (effects (font (size 1.27 1.27)))) (number "{n}" (effects (font (size 1.27 1.27)))))'
 return s+'))'
SYMS={}
for lib,name in [('RF_Module','ESP32-S3-WROOM-1'),('Interface_USB','CH340C'),('Connector','USB_B_Micro'),('Power_Protection','USBLC6-2SC6'),('Device','R_Small_US'),('Device','C'),('Switch','SW_Push'),('power','+3V3'),('power','+5V'),('power','GND'),('power','PWR_FLAG')]:SYMS[lib+':'+name]=source(lib,name)
# WCH specifies V3 tied to VCC in 3.3 V mode. Pin 4 is an input in this mode.
ch=SYMS.pop('Interface_USB:CH340C');oldpins=pins(ch);ch=ch.replace('Interface_USB:CH340C','PalmPilot:CH340C_3V3').replace('CH340C_0','CH340C_3V3_0').replace('CH340C_1','CH340C_3V3_1');ch=ch.replace('(pin power_out line','(pin power_in line');assert pins(ch)==oldpins;SYMS['PalmPilot:CH340C_3V3']=ch
SYMS['PalmPilot:TLV1117LV33']=regulator()
for name,n,names,right in [('Flex',2,None,True),('IMU',4,['GND','3V3','SDA','SCL'],False),('Switch',2,['SW','GND'],False)]:SYMS['PalmPilot:'+name]=connector(name,n,names,right)
META={name:pins(s) for name,s in SYMS.items()}
(RootLib:=ROOT/'libraries').mkdir(exist_ok=True)
(RootLib/'PalmPilot.kicad_sym').write_text('(kicad_symbol_lib (version 20250114) (generator "palmpilot")'+''.join(s.replace('PalmPilot:','',1) for n,s in SYMS.items() if n.startswith('PalmPilot:'))+')')
# Local derivative: native land pattern and STEP, with off-board antenna silk removed.
custom=ROOT/'libraries'/'PalmPilotModules.pretty';custom.mkdir(exist_ok=True)
ft=(LIB/'footprints'/'RF_Module.pretty'/'ESP32-S3-WROOM-1.kicad_mod').read_text()
for match in list(re.finditer(r'\(fp_(?:line|poly)',ft))[::-1]:
 piece=block(ft,match.start())
 ys=[float(m[2]) for m in re.findall(r'\((start|end|xy) ([-\d.]+) ([-\d.]+)\)',piece)]
 if '(layer "F.SilkS")' in piece and ys and min(ys)<-5.85:ft=ft[:match.start()]+ft[match.start()+len(piece):]
(custom/'ESP32-S3-WROOM-1.kicad_mod').write_text('\n'.join(line.rstrip() for line in ft.splitlines())+'\n')
RFP='Resistor_SMD:R_0805_2012Metric';CFP='Capacitor_SMD:C_0805_2012Metric';BIGC='Capacitor_SMD:C_1206_3216Metric';JST2='Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical';JST4='Connector_JST:JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical';BUTTON='Button_Switch_THT:SW_PUSH_6mm'
INFO={
 'U1':('ESP32-S3-WROOM-1-N16R8','Espressif Systems','C2913202','https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf'),
 'U2':('CH340C','WCH','C84681','https://www.wch-ic.com/downloads/CH340DS1_PDF.html'),
 'U3':('TLV1117LV33DCYR','Texas Instruments','C15578','https://www.ti.com/lit/ds/symlink/tlv1117lv.pdf'),
 'D1':('USBLC6-2SC6','STMicroelectronics','C7519','https://www.st.com/resource/en/datasheet/usblc6-2.pdf'),
 'J1':('1050170001','Molex','C136000','https://www.molex.com/en-us/products/part-detail/1050170001')}

def build(side):
 d=ROOT/side;d.mkdir(exist_ok=True);stem='hub' if side=='hub' else side+'-hand';sid=uid(side);items=[];cs={};wireids=set()
 def snap(x):return round(round(x/1.27)*1.27,4)
 def w(a,b):
  a=tuple(map(snap,a));b=tuple(map(snap,b));key=tuple(sorted([a,b]))
  if a==b or key in wireids:return
  wireids.add(key);items.append(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid {uid(side+str(key))}))')
 def dot(x,y):items.append(f'(junction (at {snap(x)} {snap(y)}) (diameter 0) (color 0 0 0 0) (uuid {uid(side+"dot"+str((x,y)))}))')
 def label(net,x,y,a=0,justify="left"):items.append(f'(label {q(net)} (at {snap(x)} {snap(y)} {a}) (effects (font (size 1.27 1.27)) (justify {justify} bottom)) (uuid {uid(side+net+str((x,y)))}))')
 def text(t,x,y,size=1.27):items.append(f'(text {q(t)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left)) (uuid {uid(side+t+str((x,y)))}))')
 def rect(x,y,ww,hh,title):items.append(f'(rectangle (start {x} {y}) (end {x+ww} {y+hh}) (stroke (width .254) (type default) (color 70 100 140 1)) (fill (type none)) (uuid {uid(side+title)}))');text(title,x+4,y+3.5,1.6)
 def sym(lib,ref,value,x,y,fp='',nets=None,props=None,info=None):
  x,y=snap(x),snap(y);ident=uid(side+ref);s=f'(symbol (lib_id {q(lib)}) (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {ident})'
  positions=props or [(x+3,y-1.27),(x+3,y+1.27)]
  fields=[('Reference',ref),('Value',value),('Footprint',fp)]
  info=info or INFO.get(ref)
  if info:fields += list(zip(['MPN','Manufacturer','LCSC','Datasheet'],info))
  elif ref.startswith('C'):fields += list(zip(['MPN','Manufacturer','LCSC'],('CL31A226KAHNNNE','Samsung Electro-Mechanics','C12891') if value.startswith('22u') else ('CL21B105KBFNNNE','Samsung Electro-Mechanics','C28323') if value.startswith('1u') else ('CC0805KRX7R9BB104','Yageo','C49678')))
  for i,(k,v) in enumerate(fields):
   px,py=positions[i] if i<2 else (x,y);hide=i>1 or ref.startswith('#') and (k=='Reference' or ref.startswith('#FLG'))
   s+=f'(property {q(k)} {q(v)} (at {snap(px)} {snap(py)} 0) (effects (font (size 1.27 1.27)) (justify left)'+(' (hide yes)' if hide else '')+'))'
  s+=f'(instances (project {q(stem)} (path "/{sid}" (reference {q(ref)}) (unit 1)))))';items.append(s)
  if fp:cs[ref]={'uuid':ident,'lib':lib,'value':value,'footprint':fp,'nets':nets or {},'at':[x,y],'fields':dict(fields)}
 def power(net,x,y):sym('power:'+net,'#PWR'+str(len(items)),net,x,y,props=[(x,y),(x-1.27,y+5.08 if net=='GND' else y-3.81)])
 def endpoint(ref,n):
  c=cs[ref];t=META[c['lib']][str(n)];return(snap(c['at'][0]+t['x']),snap(c['at'][1]-t['y']),t['angle'])
 def expose(ref,skip=()):
  c=cs[ref];done=set()
  for n,t in META[c['lib']].items():
   if n in skip:continue
   x,y,a=endpoint(ref,n);net=c['nets'].get(n)
   if net:
    if (x,y,net) in done:continue
    done.add((x,y,net));dx,dy=-round(math.cos(math.radians(a))),round(math.sin(math.radians(a)));xx,yy=x+dx*5.08,y+dy*5.08;w((x,y),(xx,yy))
    if net in ['+3V3','+5V','GND'] and dx==0:power(net,xx,yy)
    else:label(net,xx,yy,0,'right' if dx<0 else 'left')
   else:items.append(f'(no_connect (at {x} {y}) (uuid {uid(side+ref+n+"nc")}))')
 def passive(ref,value,x,y,a,b,cap=False,big=False):
  sym('Device:C' if cap else 'Device:R_Small_US',ref,value,x,y,BIGC if big else CFP if cap else RFP,{'1':a,'2':b});return 3.81 if cap else 2.54
 # Direct module, complete pin map; all unused pins are intentional NCs.
 mn={'1':'GND','2':'+3V3','3':'EN','27':'BOOT','36':'UART_RX','37':'UART_TX','40':'GND','41':'GND'}
 if side!='hub':mn.update({'4':'MIDDLE','5':'RING','6':'LITTLE','12':'SDA','17':'SCL','38':'INDEX','39':'THUMB'})
 if side!='right':mn['7']='CALIBRATE' if side=='hub' else 'ENABLE'
 rect(10,15,105,107,'DIRECT ESP32-S3-WROOM MODULE')
 sym('RF_Module:ESP32-S3-WROOM-1','U1','ESP32-S3-WROOM-1-N16R8',65,77.47,'PalmPilotModules:ESP32-S3-WROOM-1',mn,[(40,30),(18,34)]);expose('U1',skip=('2',))
 # Local bulk and bypass are directly wired to the module supply.
 for ref,x,val,big in [('C10',20,'22uF 25V X5R',True),('C11',37,'100nF',False)]:
  dd=passive(ref,val,x,44.45,'+3V3','GND',True,big);w((x,44.45-dd),(x,38.1));w((x,44.45+dd),(x,52.07));power('GND',x,52.07)
 w((20,38.1),(65,38.1));w((37,38.1),(37,40.64));w((65,38.1),(65,49.53));power('+3V3',65,38.1);dot(37,38.1)
 rect(120,15,115,107,'USB-UART / 3.3 V LOGIC')
 un={'1':'GND','2':'UART_RX','3':'UART_TX','4':'+3V3','5':'USB_P','6':'USB_M','16':'+3V3'}
 sym('PalmPilot:CH340C_3V3','U2','CH340C / 3V3 MODE',175,72.39,'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',un,[(180,50),(143,45)]);expose('U2',skip=('4','16'))
 for n in ['4','16']:
  x,y,_=endpoint('U2',n);w((x,y),(x,53.34));w((x,53.34),(175,53.34))
 power('+3V3',175,53.34)
 for ref,x in [('C22',145),('C23',195)]:
  dd=passive(ref,'100nF',x,112,'+3V3','GND',True);power('+3V3',x,108.14);w((x,112-dd),(x,108.14));w((x,112+dd),(x,118.3));power('GND',x,118.3)
 text('VCC and V3 tied to 3V3; internal oscillator.',124,96,1.1);text('BOOT + RESET for manual flashing; UART0 unchanged.',124,101,1.1)
 rect(240,15,165,107,'USB POWER / 1 A CERAMIC-STABLE LDO')
 sym('Connector:USB_B_Micro','J1','USB MICRO-B',267,55,'Connector_USB:USB_Micro-B_Molex-105017-0001',{'1':'+5V','2':'USB_M','3':'USB_P','5':'GND','SH':'GND'},[(250,37),(250,41)]);expose('J1')
 sym('PalmPilot:TLV1117LV33','U3','TLV1117LV33DCYR',351,60,'Package_TO_SOT_SMD:SOT-223-3_TabPin2',{'1':'GND','2':'+3V3','3':'+5V'},[(344,50),(332,54)])
 for ref,x,net in [('C12',328,'+5V'),('C13',382,'+3V3')]:
  dd=passive(ref,'22uF 25V X5R',x,75,net,'GND',True,True);w((x,75-dd),(x,60));w((x,75+dd),(x,86.36));power(net,x,56);w((x,56),(x,60))
 w((328,60),(343.38,60));w((358.62,60),(382,60));w((328,86.36),(382,86.36));w((351,67.62),(351,86.36));power('GND',351,86.36);dot(351,86.36)
 text('USB 5 V only. No cell input or charger.',245,104,1.1);text('Verify rail droop and worn thermal behavior before release.',245,112,1.1)
 # EN RC and reset switch.
 rect(10,130,105,67,'RESET / POWER-UP DELAY')
 dd=passive('R20','10kR',25,145,'+3V3','EN');power('+3V3',25,139);w((25,139),(25,145-dd));w((25,145+dd),(25,152));w((25,152),(80,152));label('EN',80,152)
 dd=passive('C20','1uF',50,164,'EN','GND',True);w((50,152),(50,164-dd));w((50,164+dd),(50,173));power('GND',50,173);dot(50,152)
 sym('Switch:SW_Push','SW1','RESET',80,180,BUTTON,{'1':'EN','2':'GND'},[(75,174),(75,186)]);expose('SW1')
 rect(120,130,115,67,'BOOT / GPIO0')
 dd=passive('R21','10kR',143,150,'+3V3','BOOT');power('+3V3',143,143);w((143,143),(143,150-dd));w((143,150+dd),(143,160));w((143,160),(205,160));label('BOOT',205,160)
 sym('Switch:SW_Push','SW2','BOOT',175,179,BUTTON,{'1':'BOOT','2':'GND'},[(170,173),(170,185)]);expose('SW2');text('Hold BOOT; tap RESET; release BOOT to flash.',125,192,1.1)
 if side!='right':
  net='CALIBRATE' if side=='hub' else 'ENABLE';rect(240,130,80,67,net+' / GPIO7')
  dd=passive('R6','10kR',251,146,'+3V3',net);power('+3V3',251,139);w((251,139),(251,146-dd));w((251,146+dd),(251,154));w((251,154),(307,154));label(net,307,154)
  dd=passive('C6','100nF',276,166,net,'GND',True);w((276,154),(276,166-dd));w((276,166+dd),(276,174));power('GND',276,174);dot(276,154)
  dd=passive('R7','1kR',251,168,net,'SW');w((251,154),(251,168-dd));w((251,168+dd),(251,179));label('SW',251,179)
  if side=='hub':sym('Switch:SW_Push','SW3','CALIBRATE',294,184,BUTTON,{'1':'SW','2':'GND'},[(287,178),(287,190)]);expose('SW3')
  else:sym('PalmPilot:Switch','J9','ENABLE N.O.',302,184,JST2,{'1':'SW','2':'GND'},[(288,193),(288,197)]);expose('J9')
 if side!='hub':
  rect(325,130,80,67,'EXTERNAL MOTION / #5543')
  sym('PalmPilot:IMU','J2','PH-4 HARNESS',352,157,JST4,{'1':'GND','2':'+3V3','3':'SDA','4':'SCL'},[(354,146),(355,170)]);expose('J2')
  text('VIN = 3V3; no extra pull-ups.',329,179,1.1);text('GPIO8 SDA / GPIO9 SCL; 100 kHz.',329,186,1.1);text('Keep calibrated module axes.',329,192,1.1)
  rect(10,205,275,51,'FIVE FLEX INPUTS / FROZEN ADC1 GPIO MAP')
  for i,(net,gpio) in enumerate(zip(['THUMB','INDEX','MIDDLE','RING','LITTLE'],[1,2,4,5,6]),1):
   x=18+(i-1)*53;y=223;jn='J'+str(i+3)
   sym('PalmPilot:Flex',jn,net,x,y,JST2,{'1':'+3V3','2':net},[(x-5,y-6),(x-5,y-9)])
   w((x+7.62,y-2.54),(x+14,y-2.54));power('+3V3',x+14,y-2.54);w((x+7.62,y),(x+31,y));label(net,x+31,y)
   for ref,xx,val,cap in [('R'+str(i),x+15,'47kR 1%',False),('C'+str(i),x+31,'100nF',True)]:
    dd=passive(ref,val,xx,y+7.62,net,'GND',cap);w((xx,y),(xx,y+7.62-dd));w((xx,y+7.62+dd),(xx,y+13.97));dot(xx,y)
   w((x+15,y+13.97),(x+31,y+13.97));power('GND',x+31,y+13.97);text('GPIO'+str(gpio),x,y+24,1.1)
 rect(290,205,115,43,'USB ESD / CONNECTOR-SIDE')
 sym('Power_Protection:USBLC6-2SC6','D1','USBLC6-2SC6',342,229,'Package_TO_SOT_SMD:SOT-23-6',{'1':'USB_P','2':'GND','3':'USB_M','4':'USB_M','5':'+5V','6':'USB_P'},[(337,218),(321,221)]);expose('D1')
 text('Rev B: soldered WROOM module; no DevKit or socket headers.',12,266,1.27)
 text('Module antenna overhangs the front edge; USB-UART and regulator are on this PCB.',12,273,1.1)
 text('GPIO10, strapping GPIO3/45/46, native USB19/20 and PSRAM35-37 remain unconnected.',12,280,1.1)
 sch=f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {sid}) (paper "A3") (title_block (title "PalmPilot {side.upper()} / DIRECT WROOM") (rev "B") (date "2026-11-18") (company "USB powered / built-in PCB antenna")) (lib_symbols '+''.join(SYMS.values())+')'+''.join(items)+'(embedded_fonts no))'
 (d/(stem+'.kicad_sch')).write_text('\n'.join(line.rstrip() for line in sch.splitlines())+'\n');(d/'sym-lib-table').write_text('(sym_lib_table (lib (name "PalmPilot") (type "KiCad") (uri "${KIPRJMOD}/../libraries/PalmPilot.kicad_sym") (options "") (descr "Direct-module support symbols")))')
 build=ROOT/'build'/side;build.mkdir(exist_ok=True)
 with (build/'netlist.log').open('w') as log:subprocess.run([K,'sch','export','netlist','--format','kicadxml','--output',str(build/'netlist.xml'),str(d/(stem+'.kicad_sch'))],stdout=log,stderr=subprocess.STDOUT,check=True)
 xml=ET.parse(build/'netlist.xml').getroot();netmap={}
 for net in xml.findall('nets/net'):
  for nd in net.findall('node'):netmap[(nd.get('ref'),nd.get('pin'))]=net.get('name')
 b=p.BOARD();b.SetCopperLayerCount(4);b.GetDesignSettings().SetBoardThickness(mm(1.6));nets={};fps={}
 for n in sorted(set(netmap.values())):ni=p.NETINFO_ITEM(b,n);b.Add(ni);nets[n]=ni
 def actual(n):return n if n in nets else '/'+n
 def add(ref,x,y,a=0):
  c=cs[ref];lib,fn=c['footprint'].split(':');fpdir=ROOT/'libraries'/'PalmPilotModules.pretty' if ref=='U1' else LIB/'footprints'/(lib+'.pretty');fp=p.FootprintLoad(str(fpdir),fn);assert fp,ref;fp.SetReference(ref);fp.SetValue(c['value']);fp.SetPosition(V(x,y));fp.SetOrientationDegrees(a);fp.SetFPID(p.LIB_ID(lib,fn));fp.SetPath(p.KIID_PATH('/'+sid+'/'+c['uuid']));b.Add(fp)
  for pad in fp.Pads():
   n=netmap.get((ref,pad.GetNumber()))
   if n:pad.SetNet(nets[n])

  for key,value in c['fields'].items():
   if key not in ['Reference','Value','Footprint']:
    fp.SetField(key,value);fp.GetField(key).SetVisible(False)
  fp.Reference().SetVisible(False);fp.Value().SetVisible(False);fps[ref]=fp
 def pp(ref,n,idx=0):
  ps=[a for a in fps[ref].Pads() if a.GetNumber()==str(n)];z=ps[idx].GetPosition();return(round(p.ToMM(z.x),6),round(p.ToMM(z.y),6))
 def seg(net,a,c,layer=p.F_Cu,width=.25):
  if math.dist(a,c)<1e-5:return
  t=p.PCB_TRACK(b);t.SetStart(V(*a));t.SetEnd(V(*c));t.SetLayer(layer);t.SetWidth(mm(width));t.SetNet(nets[actual(net)]);b.Add(t)
 def path(net,pts,layer=p.F_Cu,width=.25):
  for a,c in zip(pts,pts[1:]):
   dx=c[0]-a[0];dy=c[1]-a[1];dd=min(abs(dx),abs(dy));mid=(a[0]+math.copysign(dd,dx),a[1]+math.copysign(dd,dy));seg(net,a,mid,layer,width);seg(net,mid,c,layer,width)
 def via(net,x,y):
  v=p.PCB_VIA(b);v.SetPosition(V(x,y));v.SetWidth(mm(.65));v.SetDrill(mm(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(nets[actual(net)]);b.Add(v)
 def supply(ref,n,xy,net='+3V3',width=.5):path(net,[pp(ref,n),xy],width=width);via(net,*xy)
 def silk(s,x,y,size=.8):
  size=max(size,.8);t=p.PCB_TEXT(b);t.SetText(s);t.SetPosition(V(x,y));t.SetTextSize(V(size,size));t.SetTextThickness(mm(.13));t.SetLayer(p.F_SilkS);b.Add(t)
 add('U1',25,6.5);add('U2',25,40);add('U3',42,42);add('J1',25,55);add('D1',25,48,90)
 add('C10',9,2.51,180);add('C11',9,5,180);add('C12',33,43,180);add('C13',42,36,0);add('C22',30,38,-90);add('C23',18.5,39.365,180)
 add('R20',7,8);add('C20',12,10.5,-90);add('R21',35.5,39);add('SW1',4,50);add('SW2',36.5,50)
 # Module supply, local bypass loops and full ground reference on In1.Cu.
 supply('U1',2,(13.8,2.51),width=.65);via('+3V3',14.5,2.51);path('+3V3',[pp('U1',2),(14.5,2.51)],width=.65)
 supply('C10',1,(12,2.51),width=.65);supply('C11',1,(11.2,5),width=.4)
 for ref,n,xy in [('U1',1,(14.6,1.24)),('U1',40,(35.4,1.24)),('C10',2,(6.5,2.51)),('C11',2,(7,5))]:supply(ref,n,xy,'GND',.4)
 # Regulator IN/OUT pads, both physical OUT lands and local capacitors.
 path('+3V3',[pp('U3',2),pp('U3',2,1)],width=.8);supply('U3',2,(37.3,42),width=.7);via('+3V3',38.1,42)
 supply('C13',1,(39.2,36),width=.65);via('+3V3',39.9,36)
 supply('C13',2,(45,36),'GND',.5);supply('U3',1,(37.5,39.7),'GND',.5)
 path('+5V',[pp('U3',3),(35.35,44.3),pp('C12',1)],width=.65);supply('C12',2,(30.3,43),'GND',.5)
 # Bridge supply/return. 3.3 V mode ties V3 and VCC, so UART is never 5 V.
 supply('U2',16,(29,35.555));path('+3V3',[pp('U2',16),(29.495,35.555),(30,36.05),pp('C22',1)],width=.4)
 supply('C22',2,(31,38.95),'GND',.35);supply('U2',1,(21.1,35.555),'GND',.4)
 supply('U2',4,(20.3,39.365),width=.4);path('+3V3',[pp('U2',4),pp('C23',1)],width=.4);supply('C23',2,(16.5,39.365),'GND',.35)
 # UART0: ESP TX -> bridge RX; bridge TX -> ESP RX. All slow routes reference In1 GND.
 for net,pin,x,cy,chip in [('UART_TX',37,31.5,29.12,3),('UART_RX',36,30.5,28.85,2)]:
  yy=pp('U1',pin)[1];path(net,[pp('U1',pin),(x,yy)]);via(net,x,yy);end=(20.8,pp('U2',chip)[1]);path(net,[(x,yy),(x,cy),end],p.B_Cu);via(net,*end);path(net,[end,pp('U2',chip)])
 # Reset/boot: 10k / 1uF EN delay and physical manual-flash buttons.
 supply('R20',1,(5,8),width=.35)
 path('EN',[pp('U1',3),(14.7,3.78),(12.2,6.28),(12.2,9.35),pp('C20',1)])
 path('EN',[pp('R20',2),(10,8),(11,9),(11,9.55),pp('C20',1)]);via('EN',11,9.55)
 path('EN',[(11,9.55),(10,10.55),(10,44),(4,50)],p.B_Cu);path('EN',[pp('SW1',1),pp('SW1',1,1)])
 supply('C20',2,(12,12.6),'GND',.35);path('GND',[pp('SW1',2),pp('SW1',2,1)])
 path('BOOT',[pp('U1',27),(32.9,17.75),(32.2,17.05)]);via('BOOT',32.2,17.05)
 path('BOOT',[(32.2,17.05),(32.2,21.8)],p.B_Cu);via('BOOT',32.2,21.8)
 path('BOOT',[(32.2,21.8),(32.2,40)]);via('BOOT',32.2,40);path('BOOT',[(32.2,40),(32.2,45.7)],p.B_Cu);via('BOOT',32.2,45.7);path('BOOT',[(32.2,45.7),(36.5,50),pp('SW2',1,1)]);path('GND',[pp('SW2',2),pp('SW2',2,1)])
 supply('R21',1,(34,39),width=.35);path('BOOT',[pp('R21',2),(36.4125,40),(32.2,40)])
 if side!='hub':
  # Complete repeated flex-conditioning cells before hand-to-module fan-out.
  adc=[('MIDDLE','J6','R3','C3',4,19,0,4,17.5),('RING','J7','R4','C4',4,29,0,5,18.6),('LITTLE','J8','R5','C5',4,39,0,6,19.7),('THUMB','J4','R1','C1',44,22,180,39,35.8),('INDEX','J5','R2','C2',44,32,180,38,37.0)]
  for net,j,r,c,x,y,a,pin,lane in adc:
   add(j,x,y,a);rx,cx=(37.2,34.2) if a else (10.7,14)
   add(r,rx,y,-90);add(c,cx,y,-90);ny=y-2;vx=lane if a else 14
   pp2=pp(j,2);k=(pp2[0]+(-2 if a else 2),ny);path(net,[pp2,k,(min(cx,vx),ny),(max(rx,cx,vx),ny)])
   path(net,[(rx,ny),pp(r,1)]);path(net,[(cx,ny),pp(c,1)]);via(net,vx,ny)
   if a:
    supply(r,2,(38.5,pp(r,2)[1]),'GND',.25);supply(c,2,(cx,y+2.2),'GND',.25)
   else:
    supply(r,2,(rx,y+2.2),'GND',.25);supply(c,2,(cx,y+2.2),'GND',.25)
   supply(j,1,(x+(-1.5 if a else 1.5),y+1.8),width=.4)
   my=pp('U1',pin)[1];path(net,[pp('U1',pin),(lane,my)]);via(net,lane,my)
   if a:path(net,[(lane,my),(lane,ny)],p.B_Cu)
   else:path(net,[(lane,my),(lane,ny-(lane-vx)),(vx,ny)],p.B_Cu)
   silk(net,37.1 if a else x+1,y+3 if a else y+4.7,.8)
  add('J2',45,10,90)
  path('SDA',[pp('U1',12),(17.7,15.21)]);via('SDA',17.7,15.21)
  path('SDA',[(17.7,15.21),(35,15.21),(37,13.21),(37,7.5),(38.5,6),pp('J2',3)],p.In2_Cu)
  path('SCL',[pp('U1',17),(20.555,21)]);via('SCL',20.555,21)
  path('SCL',[(20.555,21),(39,21),(48,12),(48,4),pp('J2',4)],p.In2_Cu)
  silk('IMU',46,13.2,.8)
 if side!='right':
  net='CALIBRATE' if side=='hub' else 'ENABLE'
  add('R6',21,25,-90);add('C6',25,25,-90);add('R7',22,29,180)
  path(net,[pp('U1',7),(21,8.86)]);via(net,21,8.86);path(net,[(21,8.86),(21,19),(25,23)],p.B_Cu);via(net,25,23)
  path(net,[(25,23),pp('C6',1)]);path(net,[pp('R6',2),(22.1375,25.9125),(24,24.05),pp('C6',1)]);path(net,[(25,23),(28,23),(28,29),pp('R7',1)])
  supply('R6',1,(21,22.8),width=.35);supply('C6',2,(25,27.2),'GND',.35)
  path('SW',[pp('R7',2),(20.5,29),(20.5,29.5),(22,31)]);via('SW',22,31)
  if side=='hub':
   add('SW3',8,31);path('SW',[(22,31),pp('SW3',1,1)],p.B_Cu);path('SW',[pp('SW3',1),pp('SW3',1,1)]);path('GND',[pp('SW3',2),pp('SW3',2,1)]);silk('CALIBRATE',11.3,38,.8)
  else:
   add('J9',12,43.5);path('SW',[(22,31),(12,41),(12,43.5)],p.B_Cu);silk('ENABLE',13,47.7,.75)
 # USB connector, ESD pass-through and 5 V input. Short full-speed pair; reference plane intact.
 path('+5V',[pp('J1',1),(23.7,51.3),(22.4,50)]);via('+5V',22.4,50)
 path('+5V',[(22.4,50),(22.4,47.2),(35.3,47.2),(35.3,43.825),pp('C12',1)],p.In2_Cu,.65)
 # D1 pass-through lands are explicitly joined, including both physical pins.
 path('USB_P',[pp('J1',3),(25,52.2)]);via('USB_P',25,52.2)
 path('USB_P',[(25,52.2),(24.05,51.25),(24.05,50.2)],p.B_Cu);via('USB_P',24.05,50.2)
 path('USB_P',[(24.05,50.2),pp('D1',1),pp('D1',6)],width=.25)
 path('USB_M',[pp('J1',2),(24.35,51.5),(25.95,49.9),pp('D1',3),pp('D1',4)],width=.25)
 path('USB_P',[pp('D1',6),(24.05,46),(19.5,46),(19.5,40.635),pp('U2',5)],width=.25)
 path('USB_M',[pp('D1',4),(25.95,45.4),(20.3,45.4),(20.3,41.905),pp('U2',6)],width=.25)
 supply('D1',5,(25,46.1),'+5V',.35)
 path('+5V',[(25,46.1),(25,47.2)],p.In2_Cu,.4)
 supply('D1',2,(25,48.2),'GND',.3)
 supply('J1',5,(27,51.6),'GND',.3);via('+5V',*pp('C12',1));via('GND',22,52)
 # Ground reference and quiet power plane. No routing or copper beneath the overhanging antenna.
 for layer,net in [(p.F_Cu,'GND'),(p.In1_Cu,'GND'),(p.In2_Cu,'+3V3'),(p.B_Cu,'GND')]:
  z=p.ZONE(b);z.SetLayer(layer);z.SetNet(nets[net]);z.SetLocalClearance(mm(.25));z.SetThermalReliefGap(mm(.25));z.SetThermalReliefSpokeWidth(mm(.25));z.SetMinThickness(mm(.2));o=z.Outline();o.NewOutline()
  for x,y in [(0.5,.5),(49.5,.5),(49.5,57.5),(.5,57.5)]:o.Append(mm(x),mm(y))
  b.Add(z)
 # Local VOUT spreading copper for SOT-223; solid In2 plane carries the load to the module.
 z=p.ZONE(b);z.SetLayer(p.F_Cu);z.SetNet(nets['+3V3']);z.SetAssignedPriority(2);z.SetLocalClearance(mm(.25));z.SetThermalReliefGap(mm(.25));z.SetThermalReliefSpokeWidth(mm(.35));z.SetMinThickness(mm(.2));o=z.Outline();o.NewOutline()
 for x,y in [(38,38),(48,38),(48,46),(38,46)]:o.Append(mm(x),mm(y))
 b.Add(z)
 for x,y in [(3,10),(3,25),(3,35),(47,18),(47,35),(16,45),(29,49),(35,52),(7,55),(45,55),(29,13)]:via('GND',x,y)
 outline=[(3,0),(47,0),(50,3),(50,55),(47,58),(3,58),(0,55),(0,3)]
 for a,c in zip(outline,outline[1:]+outline[:1]):
  e=p.PCB_SHAPE();e.SetShape(p.SHAPE_T_SEGMENT);e.SetStart(V(*a));e.SetEnd(V(*c));e.SetWidth(mm(.05));e.SetLayer(p.Edge_Cuts);b.Add(e)
 for i,(x,y) in enumerate([(3,3),(39,13),(17,53),(48.3,51)],1):
  fp=p.FootprintLoad(str(LIB/'footprints'/'MountingHole.pretty'),'MountingHole_2.7mm_M2.5');fp.SetReference('H'+str(i));fp.SetPosition(V(x,y));fp.SetAttributes(p.FP_BOARD_ONLY|p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES);fp.Reference().SetVisible(False);fp.Value().SetVisible(False);b.Add(fp)
 silk('PALMPILOT '+side.upper()+' / B',25,31.7,.8);silk('RESET',7,48.5,.7);silk('BOOT',40,48.5,.7)
 project={'meta':{'filename':stem+'.kicad_pro','version':1},'board':{'design_settings':{'rules':{'min_clearance':.17,'min_track_width':.2,'min_via_diameter':.6,'min_through_hole_diameter':.2,'min_copper_edge_clearance':.25}}},'net_settings':{'classes':[{'name':'Default','clearance':.17,'track_width':.25,'via_diameter':.65,'via_drill':.3,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.25,'diff_pair_gap':.2,'diff_pair_via_gap':.25}]}}
 p.SaveBoard(str(d/(stem+'.kicad_pcb')),b)
 (d/'fp-lib-table').write_text('(fp_lib_table (lib (name "PalmPilotModules") (type "KiCad") (uri "${KIPRJMOD}/../libraries/PalmPilotModules.pretty") (options "") (descr "Native WROOM land pattern; antenna silk clipped to host edge")))')
 (d/(stem+'.kicad_pro')).write_text(json.dumps(project,indent=2)+'\n')
 (ROOT/'build'/(side+'-expected.json')).write_text(json.dumps(cs,indent=2)+'\n');print(side,'direct module;',len(cs),'components;',len(list(b.GetTracks())),'copper items',flush=True)
if __name__=='__main__':
 for side in (sys.argv[1:] or ['left','right','hub']):build(side)
