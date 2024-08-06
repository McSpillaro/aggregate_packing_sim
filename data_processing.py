import pandas as pd
import numpy as np
from matplotlib import pyplot as plt

data = pd.read_csv('data/0.01radius_5particles_50aggregates.csv') # Importing the data
df = pd.DataFrame(data) # Creating a dataframe of the data

time = df['time'] # Time in simulation in units of frames
pf = df['packing_fraction'] # Packing fraction

plt.plot(time, pf)
plt.show()