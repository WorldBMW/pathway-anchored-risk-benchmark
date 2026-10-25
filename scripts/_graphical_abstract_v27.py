"""Code-drawn scientific schematic; no experimental values are synthesized."""
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
P=Path('papers/20_MRP-ST-Repair_Patterns/figures')
fig=plt.figure(figsize=(4,4),dpi=300);ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
fig.text(.07,.94,'Auditing grouped representations',fontsize=10,weight='bold')
fig.text(.07,.90,'Repeated units can inflate evaluation',fontsize=8,color='#444444')
boxes=[(.67,'Declare the evaluation target','Unit and independent group identifiers\nEncoder training data and probe folds'),(.44,'Report separate measurements','Unit holdout and group holdout\nLabel association and identity decoding\nRetained signal and downstream utility'),(.23,'Interpret the intervention','LDI is a label-association reference\nLow LDI does not prove identity removal\nFixed-scale overlap does not guarantee a dose')]
for y,title,body in boxes:
 ax.add_patch(FancyBboxPatch((.06,y),.88,.18,boxstyle='round,pad=.008',facecolor='#eef3f7',edgecolor='#46718d',linewidth=.8))
 ax.text(.09,y+.15,title,fontsize=8,weight='bold',va='top')
 ax.text(.09,y+.105,body,fontsize=6.5,va='top',linespacing=1.25)
ax.annotate('',xy=(.5,.64),xytext=(.5,.665),arrowprops={'arrowstyle':'->','color':'#46718d'})
ax.annotate('',xy=(.5,.42),xytext=(.5,.435),arrowprops={'arrowstyle':'->','color':'#46718d'})
ax.text(.07,.18,'Evidence scope',fontsize=8,weight='bold',va='top')
ax.text(.07,.14,'ST: controls and biological readouts\nHAR and gas drift: exploratory audits\nNo demonstrated downstream benefit',fontsize=6.5,linespacing=1.25,va='top')
fig.savefig(P/'graphical_abstract_v27.png',dpi=300,facecolor='white')
fig.savefig(P/'graphical_abstract_v27.pdf',facecolor='white')
fig.savefig(P/'graphical_abstract_v27.tif',dpi=300,facecolor='white')
print('Generated corrected 1200 x 1200 graphical abstract')
