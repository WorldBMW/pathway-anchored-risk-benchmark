import matplotlib
import numpy
import pandas
print('matplotlib', matplotlib.__version__)
print('pandas', pandas.__version__)
try:
    import lifelines
    print('lifelines', lifelines.__version__)
except Exception as e:
    print('no lifelines:', e)
