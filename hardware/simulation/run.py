"""Run reproducible ngspice checks tied to exported KiCad netlists.
Uses standard library + numpy/matplotlib (available in KiCad's bundled Python).
All semiconductor/ADC limitations are documented in REPORT.md.
"""
import csv,hashlib,itertools,json,math,os,pathlib,subprocess,xml.etree.ElementTree as ET
R=pathlib.Path(__file__).resolve().parents[1]; OUT=R/'simulation'/'results';OUT.mkdir(exist_ok=True)
os.environ['MPLCONFIGDIR']=str(OUT/'mpl-cache')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(side):
 f=R/'build'/side/'netlist.xml';root=ET.parse(f).getroot();cs={x.get('ref'):x.findtext('value') for x in root.findall('components/comp')};ns={}
 for net in root.findall('nets/net'):
  for node in net.findall('node'):ns[(node.get('ref'),node.get('pin'))]=net.get('name')
 return cs,ns
checks=[]
for side in ['left','right']:
 cs,ns=load(side)
 for i,(net,h,pin) in enumerate([('THUMB','J3','4'),('INDEX','J3','5'),('MIDDLE','J1','4'),('RING','J1','5'),('LITTLE','J1','6')],1):
  assert ns[(h,pin)]==ns[('J'+str(i+3),'2')]==ns[('R'+str(i),'1')]==ns[('C'+str(i),'1')]=='/'+net
  assert ns[('J'+str(i+3),'1')]=='+3V3'
  assert ns[('R'+str(i),'2')]==ns[('C'+str(i),'2')]=='GND'
 assert ns[('J2','1')]=='GND' and ns[('J2','2')]=='+3V3' and ns[('J2','3')]==ns[('J1','12')]=='/SDA' and ns[('J2','4')]==ns[('J1','15')]=='/SCL'
 assert ns[('J1','16')].startswith('unconnected-')
 if side=='left':
  assert ns[('J1','7')]==ns[('R6','2')]==ns[('R7','1')]==ns[('C6','1')]=='/ENABLE'
  assert ns[('R6','1')]=='+3V3' and ns[('R7','2')]==ns[('J9','1')]=='/SW' and ns[('J9','2')]==ns[('C6','2')]=='GND'
 else:assert ns[('J1','7')].startswith('unconnected-')
 checks.append({'side':side,'result':'PASS','schematic_sha256':digest(R/side/(side+'-hand.kicad_sch')),'netlist_sha256':digest(R/'build'/side/'netlist.xml'),'board_sha256':digest(R/side/(side+'-hand.kicad_pcb'))})
cs_hub,ns_hub=load('hub')
assert ns_hub[('J1','7')]==ns_hub[('R6','2')]==ns_hub[('R7','1')]==ns_hub[('C6','1')]=='/CALIBRATE'
assert ns_hub[('R6','1')]=='+3V3' and ns_hub[('R7','2')]==ns_hub[('SW1','1')]=='/SW'
assert ns_hub[('SW1','2')]==ns_hub[('C6','2')]=='GND'
assert all(ns_hub[('J1',str(p))].startswith('unconnected-') for p in [4,5,6,12,15,16])
assert (cs_hub['R6'],cs_hub['R7'],cs_hub['C6'])==('10kR','1kR','100nF')
checks.append({'side':'hub','result':'PASS','schematic_sha256':digest(R/'hub'/'hub.kicad_sch'),'netlist_sha256':digest(R/'build'/'hub'/'netlist.xml'),'board_sha256':digest(R/'hub'/'hub.kicad_pcb'),'simulation':'Same verified passive button topology and values as LEFT; the ENABLE SPICE deck also represents HUB CALIBRATE.'})
# Values come from the verified actual schematic, not a duplicated numeric circuit.
cs,_=load('left')
assert all(cs['R'+str(i)]=='47kR 1%' and cs['C'+str(i)]=='100nF' for i in range(1,6))
assert (cs['R6'],cs['R7'],cs['C6'])==('10kR','1kR','100nF')

def sim(name,body,cmd,signals):
 deck=OUT/(name+'.cir');data=OUT/(name+'.dat')
 deck.write_text('* PalmPilot '+name+'; extracted passive topology, explicit approximations\n'+body+'\n.options reltol=1e-6 abstol=1e-12 vntol=1e-8\n.control\nset wr_singlescale\nset wr_vecnames\n'+cmd+'\nwrdata '+str(data)+' '+' '.join(signals)+'\nquit\n.endc\n.end\n')
 with (OUT/(name+'.log')).open('w') as f:subprocess.run(['ngspice','-b',str(deck)],stdout=f,stderr=subprocess.STDOUT,check=True)
 log=(OUT/(name+'.log')).read_text()
 assert 'Error:' not in log and 'timestep too small' not in log.lower(),name
 return np.loadtxt(data,skiprows=1)
def at(a,t,col=1):return float(np.interp(t,a[:,0],a[:,col]))
def crossing(a,value,start,col=1):
 s=a[a[:,0]>=start];idx=np.where((s[:-1,col]<value)&(s[1:,col]>=value))[0]
 if not len(idx):return None
 i=idx[0];return float(np.interp(value,s[i:i+2,col],s[i:i+2,0]))
body='Vevent evt 0 PWL(0 0 5m 0 5.000001m 1 45m 1 45.000001m 2)\n';cases=[('nominal',3.3,47000.,100e-9,0.)]
for k,(s,r,c,l) in enumerate(itertools.product([.95,1.05],[.99,1.01],[.8,1.2],[-50e-9,50e-9])):cases.append(('corner'+str(k),3.3*s,47000*r,100e-9*c,l))
cases.extend([('leak_stress_plus_1uA',3.3,47000,100e-9,1e-6),('leak_stress_minus_1uA',3.3,47000,100e-9,-1e-6)])
for i,(name,v,r,c,l) in enumerate(cases):body+=f'V{i} v{i} 0 {v}\nB{i} v{i} a{i} I=V(v{i},a{i})/(V(evt)<.5 ? 25000 : (V(evt)<1.5 ? 100000 : 1e12))\nR{i} a{i} 0 {r}\nC{i} a{i} 0 {c}\nI{i} 0 a{i} {l}\n'
a=sim('flex_corners',body,'tran 10u 120m 0 10u',[f'v(a{i})' for i in range(len(cases))]);rows=[]
for i,(name,v,r,c,l) in enumerate(cases):
 vf=(v/100000+l)/(1/100000+1/r);tau=r*100000/(r+100000)*c
 rows.append({'case':name,'supply_V':v,'shunt_ohm':r,'cap_F':c,'leak_A':l,'open_V_at_50ms':at(a,.095,i+1),'normal_low_V':at(a,.044,i+1),'normal_high_V':at(a,.004,i+1),'step_1percent_ms':-math.log(.01)*tau*1000,'error_at_10ms_mV':abs(at(a,.015,i+1)-vf)*1000,'tau_ms':tau*1000})
# Independent analytic crosscheck of ngspice's nominal result at 10 ms after step.
v0=3.3*47000/(25000+47000);vf=3.3*47000/(100000+47000);tau=47000*100000/(147000)*100e-9
pred=vf+(v0-vf)*math.exp(-.010/tau);assert abs(at(a,.015)-pred)<20e-6
# Refine maximum timestep 2x to check the represented RC transient converges.
fine=sim('flex_refinement',body,'tran 5u 120m 0 5u',[f'v(a{i})' for i in range(len(cases))]);convergence=max(abs(at(a,t,i+1)-at(fine,t,i+1)) for i in range(len(cases)) for t in [.015,.055,.095]);assert convergence<50e-6
with (OUT/'flex-corners.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
# A single 10k pull-up is a conservative high-side RC envelope for the breakout.
# BSS138 level-shifter internal coupling and MCU transistor behavior are not represented.
caps=[20,50,100,112,120,150,200,400];body='VDD vdd 0 3.3\nVC ctl 0 PWL(0 1 1u 1 1.001u 0)\n.model SW SW(Ron=30 Roff=1e12 Vt=.5 Vh=.05)\n'
for i,c in enumerate(caps):body+=f'R{i} vdd bus{i} 10500\nC{i} bus{i} 0 {c}p\nS{i} bus{i} 0 ctl 0 SW\n'
bus=sim('i2c_capacitance',body,'tran .5n 30u 0 .5n',[f'v(bus{i})' for i in range(len(caps))]);i2c=[]
for i,c in enumerate(caps):
 lo=crossing(bus,.3*3.3,1.001e-6,i+1);hi=crossing(bus,.7*3.3,1.001e-6,i+1);tr=(hi-lo)*1e9
 i2c.append({'capacitance_pF':c,'rise_ns':tr,'limit_ns':1000,'result':'PASS' if tr<=1000 else 'FAIL'})
assert abs(i2c[2]['rise_ns']-.84729786*10500*100e-12*1e9)<1
# External ENABLE: bounce for 2 ms, then stable press, release with 1.2 ms bounce.
body='VDD vdd 0 3.3\nRpull vdd en 10k\nCdeb en 0 100n\nRseries en sw 1k\nSbutton sw 0 ctl 0 BTN\n.model BTN SW(Ron=1 Roff=1e12 Vt=.5 Vh=.05)\nVC ctl 0 PWL(0 0 10m 0 10.001m 1 10.3m 1 10.301m 0 10.6m 0 10.601m 1 10.9m 1 10.901m 0 11.2m 0 11.201m 1 11.6m 1 11.601m 0 12m 0 12.001m 1 50m 1 50.001m 0 50.3m 0 50.301m 1 50.6m 1 50.601m 0 50.9m 0 50.901m 1 51.2m 1 51.201m 0)\n'
button=sim('enable_bounce',body,'tran 1u 80m 0 1u',['v(en)','v(ctl)']);button_low=at(button,.04);button_high=at(button,.079)
assert button_low<.25*3.3 and button_high>.75*3.3
# Nominal + all 1%-resistor,20%-capacitor tolerance corners for the DC logic levels.
button_worst_low=3.465*(1010+1)/(9900+1010+1);assert button_worst_low<.25*3.135
# Isolated ADC charge-removal sensitivity: assumed 20pF acquisition capacitance,
# 3.1V charge swing -> 62pC, modeled as a 10ns current pulse. No vendor ADC model.
body='VDD vdd 0 3.3\nRflex vdd adc 100k\nRshunt adc 0 47k\nCshunt adc 0 80n\nIkick adc 0 PULSE(0 6.2m 1m .01n .01n 10n 10m)\n'
kick=sim('adc_charge_sensitivity',body,'tran 1u 4m 0 1u',['v(adc)']);kick_mV=(vf-float(kick[:,1].min()))*1000;assert kick_mV<1
# Sensor hard-short and power-up are separate stimuli, not inferred from open fault.
body='Vrail vdd 0 3.3\nVevent evt 0 PWL(0 0 5m 0 5.000001m 1 45m 1 45.000001m 2)\nBflex vdd adc I=V(vdd,adc)/(V(evt)<.5 ? 25000 : (V(evt)<1.5 ? .5 : 1e12))\nRshunt adc 0 47470\nCshunt adc 0 120n\n'
fault=sim('hard_short_and_open',body,'tran 2u 110m 0 2u',['v(adc)']);short_v=at(fault,.025);open50=at(fault,.095);assert short_v>3.29 and open50<.005
body='Vrail vdd 0 PWL(0 0 1m 0 2m 3.3)\nRflex vdd adc 100k\nRshunt adc 0 47470\nCshunt adc 0 120n\n'
startup=sim('power_up',body,'tran 2u 70m 0 2u',['v(adc)']);startup_target=3.3*47470/147470;startup_err=abs(at(startup,.052)-startup_target);assert startup_err<.001
assert max(x['step_1percent_ms'] for x in rows[1:17])<20
assert max(abs(x['open_V_at_50ms']) for x in rows[1:17])<.005
# Reproducible standalone figure: circuit envelopes and explicit failing I2C corners.
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
ax[0,0].plot(a[:,0]*1000,a[:,1],label='nominal',color='#007f84')
corner=a[:,2:18];ax[0,0].fill_between(a[:,0]*1000,corner.min(axis=1),corner.max(axis=1),alpha=.2,color='#007f84',label='tolerance + ±50 nA envelope')
ax[0,0].set(title='Flex: 25 kΩ → 100 kΩ → unplugged',xlabel='Time (ms)',ylabel='ADC node (V)',xlim=(0,100));ax[0,0].legend(fontsize=8)
ax[0,1].plot(button[:,0]*1000,button[:,1],color='#007f84');ax[0,1].axhline(.825,color='#c05a36',ls='--',label='VIL max');ax[0,1].axhline(2.475,color='#4c5ba7',ls='--',label='VIH min');ax[0,1].set(title='ENABLE: press/release with bounce stimulus',xlabel='Time (ms)',ylabel='GPIO7 node (V)',xlim=(8,56));ax[0,1].legend(fontsize=8)
ax[1,0].bar([str(x['capacitance_pF']) for x in i2c],[x['rise_ns'] for x in i2c],color=['#007f84' if x['result']=='PASS' else '#c05a36' for x in i2c]);ax[1,0].axhline(1000,color='black',ls='--');ax[1,0].set(title='I²C RC envelope: 10.5 kΩ pull-up',xlabel='Assumed total high-side capacitance (pF)',ylabel='30–70% rise time (ns)')
ax[1,1].plot((kick[:,0]-.001)*1e6,(vf-kick[:,1])*1000,color='#007f84');ax[1,1].set(title='Assumed ADC 62 pC charge removal / 80 nF',xlabel='Time after sampling pulse (µs)',ylabel='Node droop (mV)',xlim=(-.1,5))
fig.suptitle('PalmPilot carrier schematic simulation — ngspice 47\nPassive circuit evidence; ADC, RF and physical harness remain unqualified',fontsize=15)
fig.savefig(OUT/'schematic-simulation.png',dpi=170);fig.savefig(OUT/'schematic-simulation.pdf');plt.close(fig)
summary={'solver':subprocess.check_output(['ngspice','--version'],text=True).splitlines()[1:3],'inputs':checks,'flex':rows,'i2c':i2c,'enable':{'pressed_V':button_low,'released_V':button_high,'worst_pressed_V':button_worst_low},'faults':{'hard_short_V':short_v,'unplug_50ms_V':open50,'startup_50ms_error_mV':startup_err*1000},'adc_charge_stress_droop_mV':kick_mV,'refinement_max_difference_uV':convergence*1e6,'nominal_analytical_difference_uV':abs(at(a,.015)-pred)*1e6,'criteria':{'flex_1percent_settling_ms':20,'unplug_50ms_mV':5,'i2c_rise_ns':1000,'adc_charge_assumption_droop_mV':1}}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k not in ['flex','inputs']},indent=2))
