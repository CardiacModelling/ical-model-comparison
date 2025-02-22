import sys
from typing import Generator
import numpy as np
import myokit
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec

# create a figure with subplots
fig = plt.figure(figsize=(12,6))
grid = GridSpec(4, 3)
v0 = fig.add_subplot(grid[0:2, :2])
iv0 = fig.add_subplot(grid[:2, 2])
c0 = fig.add_subplot(grid[2:, :2])
iv0n = fig.add_subplot(grid[2:, 2])

# Set font
matplotlib.rc('font', family='arial')

c0.set_ylim(-8.5, 1)
iv0.set_ylim(-8.5, 1)
c0.set_xlabel('Time (ms)')
c0.set_ylabel('Current (A/F)')
v0.set_ylabel('Voltage (mV)')
iv0.set_ylabel('Current (A/F)')
iv0n.set_ylabel('Normalised Current')

def split_list_ind(l):
    """
    ind: index at which the list should break
    l: python list
    """
    ind = []
    for i in range(len(l)):
        try:
            if l[i] > l[i+1]:
                ind.append(i+1)
        except:
            return ind
    return ind

def split_list(a, l):
    """
    lists: list of split lists
    a: array of index at which the list should break
    l: python list
    """
    if len(a) == 0:
        return [l]
    lists = [l[:a[0]]]
    if len(a) == 1:
        lists.append(l[a[0]:])
        return lists
    for i in range(len(a)-1):
        lists.append(l[a[i]: a[i+1]])
    lists.append(l[a[i+1]:])
    return lists

m = myokit.load_model('grandi.mmt')

vm = m.get('membrane_potential.V_m')
vm.demote()

inp = input('Enter protocol: ')
if inp == 'activation':
    ptest = np.arange(-60.01, 61, 5)
    iv0.set_title('I-V Curve')
    v0.set_ylim(-95, 80)
    iv0.set_xlim(-95, 80)
    c0.set_xlim(-10, 120)
    v0.set_xlim(-10, 120)
    iv0n.set_ylim(-1.1, 0.1)
    iv0n.set_xlim(-95, 80)
    frames = len(ptest)* 130 + 1
    iv0n.set_xlabel('Voltage (mV)')
    plt.suptitle('Activation Protocol')
    fps = frames/60
elif inp == 'inactivation':
    ptest = np.arange(-90.01, 31, 5)
    iv0.set_title('I-V Curve')
    v0.set_ylim(-95, 60)
    iv0.set_xlim(-95, 60)
    c0.set_xlim(-10, 620)
    v0.set_xlim(-10, 620)
    iv0n.set_ylim(-0.1, 1.1)
    iv0n.set_xlim(-95, 60)
    frames = (len(ptest))* 630 +1
    iv0n.set_xlabel('Voltage (mV)')
    plt.suptitle('Inactivation Protocol')
    fps = frames/90
elif inp == 'recovery':
    ptest = np.arange(5, 400, 20)
    iv0.set_title('I-time Curve')
    v0.set_ylim(-95, 20)
    c0.set_xlim(-10, 1120)
    v0.set_xlim(-10, 1120)
    iv0.set_xlim(0, 400)
    iv0n.set_ylim(-0.1, 1.1)
    iv0n.set_xlim(0, 400)
    frames = sum([630 + l for l in ptest]) 
    iv0n.set_xlabel('Time between pulses (ms)')
    plt.suptitle('Recovery Protocol')
    fps = frames/90
else:
    raise ValueError('Enter activation, inactivation or recovery')

cmap = matplotlib.cm.get_cmap('jet')(np.linspace(0, 1, len(ptest)+2))

def activation():
    p1_dur = 120 #ms
    hold_dur = 20000 #ms
    hold_v = -90.01 #mV

    s = myokit.Simulation(m)
    s.set_constant('membrane_potential.V_m', hold_v)
    s.run(hold_dur - 10, log=[])
    
    for i in range(len(ptest)):
        curr_time = s.time()
        d = s.run(10, log=['I_Ca.I_Catot', 'environment.time'], log_times=np.arange(curr_time, curr_time+10, 1))
        s.set_constant('membrane_potential.V_m', ptest[i])
        s.run(p1_dur, log=d, log_times=np.arange(curr_time+10, curr_time+10+p1_dur, 1))

        d = d.npview()
        d['environment.time'] -= d['environment.time'][0] + 10
        s.set_constant('membrane_potential.V_m', hold_v)
        s.run(hold_dur -10, log=[])

        if max(d['I_Ca.I_Catot'])>0:
            ind = np.argmax(d['I_Ca.I_Catot'])
        else:
            ind = np.argmin(d['I_Ca.I_Catot'])

        time = curr_time/1000
        for j in range(len(d['environment.time'])):    
            if d['environment.time'][j] < 0:
                yield d['environment.time'][j], d['I_Ca.I_Catot'][j], False, \
                    hold_v, 0, round(time, 3)
            else:
                if j == ind:
                    yield d['environment.time'][j], d['I_Ca.I_Catot'][j], True, \
                        ptest[i], ptest[i], round(time, 3)
                else:
                    yield d['environment.time'][j], d['I_Ca.I_Catot'][j], False,\
                         ptest[i], 0, round(time, 3)
            time += 1/1000

    time = round((s.time() - (hold_dur -10))/1000, 3)
    for _ in range(100):
        yield None, None, None, None, None, time

def inactivation():
    ptest_dur = 120 #ms
    hold_dur = 20000 #ms
    hold_v = -90.01 #mV
    pcond_dur = 500 #ms

    s = myokit.Simulation(m)
    s.set_constant('membrane_potential.V_m', hold_v)
    s.run(hold_dur - 10, log=[])
    
    for i in range(len(ptest)):
        curr_time = s.time()
        d = s.run(10, log=['I_Ca.I_Catot', 'environment.time'], log_times = \
            np.arange(curr_time, curr_time+10, 1))
        s.set_constant('membrane_potential.V_m', ptest[i])
        s.run(pcond_dur, log=d, log_times = \
            np.arange(curr_time+10, curr_time+10+pcond_dur, 1))
        s.set_constant('membrane_potential.V_m', -0.01)
        s.run(ptest_dur, log=d, log_times = np.arange(curr_time+10 + pcond_dur, \
            curr_time+10 + pcond_dur + ptest_dur, 1))

        d = d.npview()
        d['environment.time'] -= d['environment.time'][0] + 10
        s.set_constant('membrane_potential.V_m', hold_v)
        s.run(hold_dur -10, log=[])

        ind_p2 = np.where(d['environment.time'] == pcond_dur)[0][0]
        
        ind = np.argmin(d['I_Ca.I_Catot'][ind_p2:])

        time = curr_time/1000
        for j in range(len(d['environment.time'])):
            if d['environment.time'][j] < 0:
                yield d['environment.time'][j], d['I_Ca.I_Catot'][j], False, hold_v, 0, round(time, 3)
            elif d['environment.time'][j] < pcond_dur:
                yield d['environment.time'][j], d['I_Ca.I_Catot'][j], False, ptest[i], 0, round(time, 3) 
            elif j == ind + ind_p2:
                if ind == 0:
                    ind_max = np.argmax(d['I_Ca.I_Catot'][ind_p2:])
                    yield d['environment.time'][j], d['I_Ca.I_Catot'][ind_p2 + ind_max], True, -0.01, ptest[i], round(time, 3)    
                else:
                    yield d['environment.time'][j], d['I_Ca.I_Catot'][j], True, -0.01, ptest[i], round(time, 3)
            else:
                yield d['environment.time'][j], d['I_Ca.I_Catot'][j], False, -0.01, 0, round(time, 3)
            time += 1/1000

    time = round((s.time() - (hold_dur -10))/1000, 3)
    for _ in range(500):
        yield None, None, None, None, None, time

def recovery():
    ptest_dur = 120 #ms
    hold_dur = 10000 #ms
    hold_v = -90.01 #mV
    pcond_dur = 500 #ms

    s = myokit.Simulation(m)
    s.set_constant('membrane_potential.V_m', hold_v)
    s.run(hold_dur - 10, log=[])
    
    for i in range(len(ptest)):
        curr_time = s.time()
        d = s.run(10, log=['I_Ca.I_Catot', 'environment.time'], log_times = \
            np.arange(curr_time, curr_time+10, 1))
        s.set_constant('membrane_potential.V_m', -0.01)
        s.run(pcond_dur, log=d, log_times = \
            np.arange(curr_time+10, curr_time+10+pcond_dur, 1))
        s.set_constant('membrane_potential.V_m', hold_v)
        s.run(ptest[i], log=d, log_times = np.arange(curr_time+10+pcond_dur, \
            curr_time+10+pcond_dur + ptest[i], 1))
        s.set_constant('membrane_potential.V_m', -0.01)
        s.run(ptest_dur, log=d, log_times = np.arange(curr_time+10+pcond_dur + ptest[i], \
            curr_time+10+pcond_dur + ptest[i] + ptest_dur, 1))

        d = d.npview()
        d['environment.time'] -= d['environment.time'][0] + 10
        s.set_constant('membrane_potential.V_m', hold_v)
        s.run(hold_dur -10, log=[])

        # ind just before the test pulse
        ind_pc = np.where(d['environment.time'] == pcond_dur + ptest[i])[0][0]
        
        ind = np.argmin(d['I_Ca.I_Catot'][ind_pc:])
       
        time = curr_time/1000
        for j in range(len(d['environment.time'])):
            if d['environment.time'][j] < 0:
                yield d['environment.time'][j], d['I_Ca.I_Catot'][j], False, hold_v, 0, round(time, 3)
            elif d['environment.time'][j] < pcond_dur:
                yield d['environment.time'][j], d['I_Ca.I_Catot'][j], False, -0.01, 0, round(time, 3)
            elif j < ind_pc :
                yield d['environment.time'][j], d['I_Ca.I_Catot'][j], False, hold_v, 0, round(time, 3)
            elif j == ind + ind_pc:
                yield d['environment.time'][j], d['I_Ca.I_Catot'][j], True, -0.01, ptest[i], round(time, 3)
            else:
                yield d['environment.time'][j], d['I_Ca.I_Catot'][j], False, -0.01, 0, round(time, 3)
            time += 1/1000
    
    time = round((s.time() - (hold_dur -10))/1000, 3)
    ind_pc = np.where(d['environment.time'] == pcond_dur)[0][0]
    ind = np.argmin(d['I_Ca.I_Catot'][:ind_pc])
    for _ in range(500):
        yield None, None, None, d['environment.time'][ind], d['I_Ca.I_Catot'][ind], time

# initialize the data arrays 
xdata, y1data, peak_v, peak_t, peak_c, volt = [], [], [], [], [], []

# Create objects to be modified in run()
lines_t = []
for _ in range(len(ptest)):
    lines_t.append(v0.plot([], [] , lw=2, drawstyle='steps-post')[0])
    lines_t.append(c0.plot([], [] , lw=2)[0])
    lines_t.append(c0.plot([], [], marker = 'x', markersize = 8)[0])
    lines_t.append(iv0.plot([], [], marker = 'x', markersize = 8)[0])
lines_t.append(c0.text(0.02, 0.05, '' , transform = c0.transAxes))
lines_t.append(c0.plot([], [], marker = 'o', markersize = 14, fillstyle = 'none', color = 'grey')[0])
lines_t.append(iv0.text(0.2, 0.05, '' , transform = iv0.transAxes))
lines_t.append(iv0.plot([], [], marker = 'o', markersize = 14, fillstyle = 'none', color = 'grey')[0])
lines_t.append(iv0n.plot([], [], lw = 1.5, color= 'black')[0])
lines_t.append(iv0.plot([], [], lw = 1.5, color= 'black')[0])
lines_t.append(v0.plot([], [], marker = 'o', color = 'black')[0])
lines_t.append(c0.plot([], [], marker = 'o', color = 'black')[0])
lines_t.append(v0.text(0.4, 0.9, f'Time = 0s', transform = v0.transAxes))

def run(data):
    # update the data
    t, y1, y2, v, peak_x, time = data
    if t == None:
        lines_t[-1].set_text(f'Protocol ran for {time}s, post-processing now')
        if inp == 'activation':
            y = -1 * min(peak_c)
        elif inp == 'inactivation':
            y = min(peak_c)
        else:
            y = peak_x
            lines_t[-5].set_data(peak_v, peak_c/y)
            lines_t[-9].set_text('Normalising by the peak at P1')
            lines_t[-8].set_data(v, peak_x)
            return lines_t
        ind = np.argmin(np.array(peak_c))
        lines_t[-7].set_text('Normalising by the largest peak')
        lines_t[-6].set_data(peak_v[ind], peak_c[ind])
        lines_t[-5].set_data(peak_v, peak_c/y)
        
        return lines_t
        
    xdata.append(t)
    y1data.append(y1)
    volt.append(v)

    # Divide the data into sweeps
    ind = split_list_ind(xdata)
    xsweep = split_list(ind, xdata)
    y1sweep = split_list(ind, y1data)
    vsweep = split_list(ind, volt)
    
    # Updates the peak 
    if y2 is True:
        peak_t.append(t)
        peak_c.append(y1)
        peak_v.append(peak_x)

    #plot 
    for i in range(len(y1sweep)):
        lines_t[4*i].set_data(xsweep[i], vsweep[i])
        lines_t[4*i].set_color(cmap[i])
        lines_t[4*i +1].set_data(xsweep[i], y1sweep[i])
        lines_t[4*i + 1].set_color(cmap[i])

    lines_t[-4].set_data(peak_v, peak_c)
    # A marker to see the animation progress with time
    lines_t[-3].set_data(t, v)
    lines_t[-2].set_data(t, y1)
    lines_t[-1].set_text(f'Time = {time}s')
      
    for i in range(len(peak_t)):
        lines_t[4*i + 2].set_data(peak_t[i], peak_c[i])
        lines_t[4*i + 2].set_color(cmap[i])
        lines_t[4*i + 3].set_data(peak_v[i], peak_c[i])
        lines_t[4*i + 3].set_color(cmap[i])

    return lines_t

if inp == 'activation':
    data_gen = activation
elif inp == 'inactivation':
    data_gen = inactivation
else:
    data_gen = recovery

ani = animation.FuncAnimation(fig, run, data_gen, blit=True, interval=5,
    repeat=False, save_count=sys.maxsize) 
plt.tight_layout()
#plt.show()
ani.save(inp + '.mp4', writer='ffmpeg', fps= fps)