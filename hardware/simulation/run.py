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
for side in ['left','right','hub']:
 cs,ns=load(side)
 def same(net,*pads):assert all(ns[pad]==net for pad in pads),(side,net,pads)
 assert cs['U1']=='ESP32-S3-WROOM-1-N16R8'
 assert not any('DevKit' in value or 'Socket' in value for value in cs.values())
 same('+3V3',('U1','2'),('U2','4'),('U2','16'),('U3','2'),('C10','1'),('C11','1'),('C13','1'),('R20','1'),('R21','1'))
 same('GND',('U1','1'),('U1','40'),('U1','41'),('U2','1'),('U3','1'),('C10','2'),('C11','2'),('C12','2'),('C13','2'),('SW1','2'),('SW2','2'),('J1','SH'))
 same('+5V',('J1','1'),('U3','3'),('C12','1'),('D1','5'))
 same('/UART_TX',('U1','37'),('U2','3'));same('/UART_RX',('U1','36'),('U2','2'))
 same('/USB_P',('J1','3'),('U2','5'),('D1','1'),('D1','6'));same('/USB_M',('J1','2'),('U2','6'),('D1','3'),('D1','4'))
 same('/EN',('U1','3'),('R20','2'),('C20','1'),('SW1','1'));same('/BOOT',('U1','27'),('R21','2'),('SW2','1'))
 assert all(ns[('U1',str(pin))].startswith('unconnected-') for pin in [13,14,15,16,18,26,28,29,30])
 assert (cs['R20'],cs['C20'],cs['R21'])==('10kR','1uF','10kR')
 if side!='hub':
  for i,(net,pin) in enumerate([('THUMB','39'),('INDEX','38'),('MIDDLE','4'),('RING','5'),('LITTLE','6')],1):
   same('/'+net,('U1',pin),('J'+str(i+3),'2'),('R'+str(i),'1'),('C'+str(i),'1'))
   same('+3V3',('J'+str(i+3),'1'));same('GND',('R'+str(i),'2'),('C'+str(i),'2'))
  same('/SDA',('U1','12'),('J2','3'));same('/SCL',('U1','17'),('J2','4'))
  same('GND',('J2','1'));same('+3V3',('J2','2'))
 if side!='right':
  same('/CALIBRATE' if side=='hub' else '/ENABLE',('U1','7'),('R6','2'),('R7','1'),('C6','1'))
  same('/SW',('R7','2'),('SW3' if side=='hub' else 'J9','1'));same('GND',('SW3' if side=='hub' else 'J9','2'),('C6','2'))
 else:assert ns[('U1','7')].startswith('unconnected-')
 stem='hub' if side=='hub' else side+'-hand'
 checks.append({'side':side,'result':'PASS','schematic_sha256':digest(R/side/(stem+'.kicad_sch')),'netlist_sha256':digest(R/'build'/side/'netlist.xml'),'board_sha256':digest(R/side/(stem+'.kicad_pcb'))})
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
# Rev B EN startup and a manual 10 ms reset pulse; passives only, no ESP model.
en_results=[]
for rc,cc in itertools.product([.99,1.01],[.8,1.2]):
 name='module_en_'+str(len(en_results))
 body=f'VDD vdd 0 PWL(0 0 1m 0 2m 3.3)\nRpull vdd en {10000*rc}\nCen en 0 {1e-6*cc}\nVreset ctl 0 PULSE(0 1 80m 1u 1u 10m 1)\nSreset en 0 ctl 0 BTN\n.model BTN SW(Ron=1 Roff=1e12 Vt=.5 Vh=.05)\n'
 en=sim(name,body,'tran 1u 130m 0 1u',['v(en)','v(vdd)'])
 t=crossing(en,2.475,.002);assert t is not None and t-.002>.00005
 assert at(en,.085)<.1 and at(en,.129)>2.475
 en_results.append({'R_ohm':10000*rc,'C_F':1e-6*cc,'enable_75percent_after_rail_ms':(t-.002)*1000,'reset_held_V':at(en,.085),'released_V':at(en,.129)})
# Output impedance/inductance sensitivity, not a vendor LDO loop/stability model.
# Each 22 uF MLCC is conservatively represented as 10 uF effective; total 20 uF.
rail_results=[]
for rs in [.05,.15,.3]:
 name='module_rail_'+str(len(rail_results))
 body=f'Vreg reg 0 3.3\nRsource reg a {rs}\nLfeed a rail .5u\nResr rail cap .02\nCbulk cap 0 20u\nIload rail 0 PULSE(.03 .5 1m 1u 1u 5m 12m)\n'
 rail=sim(name,body,'tran .05u 10m 0 .05u',['v(rail)'])
 lo=float(rail[:,1].min());hi=float(rail[:,1].max());assert lo>=3.0 and hi<=3.6
 rail_results.append({'source_R_ohm':rs,'feed_L_uH':.5,'bulk_effective_uF':20,'load_A':[.03,.5],'min_V':lo,'max_V':hi})
fig2,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained')
axs[0].plot(en[:,0]*1000,en[:,1]);axs[0].set(title='Module EN / startup and manual reset',xlabel='Time (ms)',ylabel='EN voltage (V)')
axs[1].plot(rail[:,0]*1000,rail[:,1]);axs[1].set(title='Assumed rail impedance: 0.3 ohm / 0.5 uH',xlabel='Time (ms)',ylabel='3V3 rail (V)')
fig2.suptitle('Rev B passive sensitivity — not a semiconductor or regulator-loop model');fig2.savefig(OUT/'module-power-reset.png',dpi=170);plt.close(fig2)
# Reproducible standalone figure: circuit envelopes and explicit failing I2C corners.
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
ax[0,0].plot(a[:,0]*1000,a[:,1],label='nominal',color='#007f84')
corner=a[:,2:18];ax[0,0].fill_between(a[:,0]*1000,corner.min(axis=1),corner.max(axis=1),alpha=.2,color='#007f84',label='tolerance + ±50 nA envelope')
ax[0,0].set(title='Flex: 25 kΩ → 100 kΩ → unplugged',xlabel='Time (ms)',ylabel='ADC node (V)',xlim=(0,100));ax[0,0].legend(fontsize=8)
ax[0,1].plot(button[:,0]*1000,button[:,1],color='#007f84');ax[0,1].axhline(.825,color='#c05a36',ls='--',label='VIL max');ax[0,1].axhline(2.475,color='#4c5ba7',ls='--',label='VIH min');ax[0,1].set(title='ENABLE: press/release with bounce stimulus',xlabel='Time (ms)',ylabel='GPIO7 node (V)',xlim=(8,56));ax[0,1].legend(fontsize=8)
ax[1,0].bar([str(x['capacitance_pF']) for x in i2c],[x['rise_ns'] for x in i2c],color=['#007f84' if x['result']=='PASS' else '#c05a36' for x in i2c]);ax[1,0].axhline(1000,color='black',ls='--');ax[1,0].set(title='I²C RC envelope: 10.5 kΩ pull-up',xlabel='Assumed total high-side capacitance (pF)',ylabel='30–70% rise time (ns)')
ax[1,1].plot((kick[:,0]-.001)*1e6,(vf-kick[:,1])*1000,color='#007f84');ax[1,1].set(title='Assumed ADC 62 pC charge removal / 80 nF',xlabel='Time after sampling pulse (µs)',ylabel='Node droop (mV)',xlim=(-.1,5))
fig.suptitle('PalmPilot Rev B module schematic simulation — ngspice 47\nPassive circuit evidence; ADC, RF and physical harness remain unqualified',fontsize=15)
fig.savefig(OUT/'schematic-simulation.png',dpi=170);fig.savefig(OUT/'schematic-simulation.pdf');plt.close(fig)
summary={'module_en':en_results,'module_rail_sensitivity':rail_results,'thermal_reference':{'VIN_V':5.25,'VOUT_V':3.3,'load_A':.5,'LDO_dissipation_W':.975,'TI_reference_theta_JA_C_per_W':62.9,'reference_rise_C':61.3275,'note':'Reference-board estimate only. Actual PCB and skin temperatures require measurement.'},'solver':subprocess.check_output(['ngspice','--version'],text=True).splitlines()[1:3],'inputs':checks,'flex':rows,'i2c':i2c,'enable':{'pressed_V':button_low,'released_V':button_high,'worst_pressed_V':button_worst_low},'faults':{'hard_short_V':short_v,'unplug_50ms_V':open50,'startup_50ms_error_mV':startup_err*1000},'adc_charge_stress_droop_mV':kick_mV,'refinement_max_difference_uV':convergence*1e6,'nominal_analytical_difference_uV':abs(at(a,.015)-pred)*1e6,'criteria':{'flex_1percent_settling_ms':20,'unplug_50ms_mV':5,'i2c_rise_ns':1000,'adc_charge_assumption_droop_mV':1}}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k not in ['flex','inputs']},indent=2))
