# -*- coding: utf-8 -*-
import csv, math, heapq, json, numpy as np
from datetime import date
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
fp="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
fm.fontManager.addfont(fp)
NF=fm.FontProperties(fname=fp).get_name()
plt.rcParams['font.family']=NF; plt.rcParams['axes.unicode_minus']=False
PAN="#08519c"; SON="#d7301f"
OUT="/sessions/epic-eager-bohr/mnt/스시론 기말 과제/"
D="/sessions/epic-eager-bohr/mnt/.projects/019eb978-ac1c-7129-8c8d-bcbdd2ceb136/docs"
U="/sessions/epic-eager-bohr/mnt/uploads/"
OX,OY=900000.0,1900000.0

# ---- grid pop ----
gx=[];gy=[];gp=[]
for row in csv.reader(open(U+"2024년_인구_다사_100M.csv",encoding='cp949',errors='replace')):
    if row[2]!='to_in_001':continue
    d=row[1].replace('다사',''); gx.append(OX+int(d[:3])*100+50); gy.append(OY+int(d[3:])*100+50)
    try:gp.append(int(row[3]))
    except:gp.append(0)
gx=np.array(gx);gy=np.array(gy);gp=np.array(gp,float)
# ---- emp points ----
xy={}
for fn in ["centroid_11.csv","centroid_23-e35fbbea.csv","centroid_31-997df9d5.csv"]:
    for r in csv.DictReader(open(U+fn)):
        try: xy[r['TOT_OA_CD']]=(float(r['X']),float(r['Y']))
        except: pass
empv=defaultdict(int)
for fn in ["11_2023년_산업분류별(10차_대분류)_종사자수.csv","23_2023년_산업분류별(10차_대분류)_종사자수.csv","31_2023년_산업분류별(10차_대분류)_종사자수.csv"]:
    for r in csv.reader(open(U+fn,encoding='cp949',errors='replace')):
        try: empv[r[1]]+=int(r[3])
        except: pass
ex=[];ey=[];ev=[]
for c,v in empv.items():
    if c in xy: ex.append(xy[c][0]);ey.append(xy[c][1]);ev.append(v)
ex=np.array(ex);ey=np.array(ey);ev=np.array(ev,float)
# ---- graph ----
nodes={}
for r in csv.DictReader(open(f"{D}/nodes.tsv"),delimiter='\t'):
    nodes[int(r['id'])]=(float(r['x_5179']),float(r['y_5179']))
def pdte(s):
    s=(s or '').strip()
    if not s:return None
    try:y,m,dd=s.split('-');return date(int(y),int(m),int(dd))
    except:return None
CUT=date(2026,6,18); adj=defaultdict(list)
for r in csv.DictReader(open(f"{D}/links.tsv"),delimiter='\t'):
    b=pdte(r['begin'])
    if b and b>CUT:continue
    fr=int(r['fromNode']);t=int(r['toNode'])
    if fr in nodes and t in nodes:
        adj[fr].append((t,float(r['timeFT'])));adj[t].append((fr,float(r['timeTF'])))
def dij(srcs):
    dist={s:0.0 for s in srcs};pq=[(0.0,s) for s in srcs];heapq.heapify(pq)
    while pq:
        d,u=heapq.heappop(pq)
        if d>dist.get(u,1e18):continue
        for v,w in adj[u]:
            nd=d+w
            if nd<dist.get(v,1e18):dist[v]=nd;heapq.heappush(pq,(nd,v))
    return dist
WALK=1.2;DET=1.3
def celltime(srcs,X,Y):
    dist=dij(srcs); ct=np.full(len(X),1e18)
    for n,ts in dist.items():
        if ts>3600:continue
        sx,sy=nodes[n]; R=(3600-ts)*WALK/DET
        m=(np.abs(X-sx)<=R)&(np.abs(Y-sy)<=R)
        if not m.any():continue
        tt=ts+np.hypot(X[m]-sx,Y[m]-sy)*DET/WALK
        ct[m]=np.minimum(ct[m],tt)
    return ct
pan_pop=celltime([26,824],gx,gy); son_pop=celltime([249],gx,gy)
pan_emp=celltime([26,824],ex,ey); son_emp=celltime([249],ex,ey)
mins=np.arange(0,61,1)
def cum(ct,val): return [val[ct<=t*60].sum()/1e4 for t in mins]  # 만명

# ===== Fig1: 누적 접근성 곡선 =====
fig,ax=plt.subplots(1,2,figsize=(9,3.6))
ax[0].plot(mins,cum(pan_pop,gp),color=PAN,lw=2.2,label="판교")
ax[0].plot(mins,cum(son_pop,gp),color=SON,lw=2.2,label="송도")
ax[0].set_title("도달 가능 인구",fontsize=11); ax[0].set_xlabel("소요시간(분)"); ax[0].set_ylabel("누적 인구(만 명)")
ax[1].plot(mins,cum(pan_emp,ev),color=PAN,lw=2.2,label="판교")
ax[1].plot(mins,cum(son_emp,ev),color=SON,lw=2.2,label="송도")
ax[1].set_title("도달 가능 종사자",fontsize=11); ax[1].set_xlabel("소요시간(분)"); ax[1].set_ylabel("누적 종사자(만 명)")
for a in ax:
    a.axvline(30,ls='--',color='#999',lw=1); a.axvline(60,ls='--',color='#999',lw=1)
    a.legend(fontsize=9); a.grid(alpha=.3); a.set_xlim(0,60)
fig.tight_layout(); fig.savefig(OUT+"fig_accessibility_curve.png",dpi=150); plt.close()

# ===== Fig2: 등시간권 지도 (mapdata.json 500m cells) =====
md=json.load(open("/sessions/epic-eager-bohr/mnt/outputs/mapdata.json"))
fig,ax=plt.subplots(1,2,figsize=(9,4.6))
for i,(key,lab) in enumerate([("pangyo","판교 제1테크노밸리"),("songdo","송도 IBD")]):
    cells=np.array(md[key]["cells"]) # lng,lat,band,pop
    c30=cells[cells[:,2]==1]; c60=cells[cells[:,2]==2]
    ax[i].scatter(c60[:,0],c60[:,1],s=6,c="#9ecae1",label="60분",edgecolors='none')
    ax[i].scatter(c30[:,0],c30[:,1],s=6,c=PAN,label="30분",edgecolors='none')
    core=md[key]["core"]; ax[i].scatter([core[0]],[core[1]],marker='*',s=220,c='k',zorder=5,label="핵심역")
    ax[i].set_title(lab,fontsize=11); ax[i].set_aspect('equal'); ax[i].legend(fontsize=8,loc='upper right')
    ax[i].set_xlabel("경도"); ax[i].set_ylabel("위도")
fig.suptitle("핵심역 기준 지하철 등시간권 (30·60분 도달 인구격자)",fontsize=12)
fig.tight_layout(); fig.savefig(OUT+"fig_isochrone_map.png",dpi=150); plt.close()

# ===== Fig3: 용도지역 구성비 =====
cats=["주거","상업","녹지"]; pan=[87.4,0.0,12.6]; son=[36.9,30.4,32.7]
x=np.arange(len(cats)); w=0.36
fig,ax=plt.subplots(figsize=(6,3.6))
ax.bar(x-w/2,pan,w,color=PAN,label="판교 (LUM 0.27)")
ax.bar(x+w/2,son,w,color=SON,label="송도 (LUM 0.79)")
ax.set_xticks(x); ax.set_xticklabels(cats); ax.set_ylabel("구성비 (%)")
ax.set_title("용도지역 구성비 비교"); ax.legend(fontsize=9); ax.grid(axis='y',alpha=.3)
for i,v in enumerate(pan): ax.text(i-w/2,v+1,f"{v:.0f}",ha='center',fontsize=8)
for i,v in enumerate(son): ax.text(i+w/2,v+1,f"{v:.0f}",ha='center',fontsize=8)
fig.tight_layout(); fig.savefig(OUT+"fig_landuse.png",dpi=150); plt.close()

# ===== Fig4: 오피스 공실률 추이 =====
q=["24.3Q","24.4Q","25.1Q","25.2Q","25.3Q","25.4Q","26.1Q"]
incheon=[20.8,19.6,19.8,19,18.7,16.6,16.9]; nation=[8.6,8.9,8.7,8.6,8.9,8.7,8.8]; bundang=[2.1,2.2,2.9,7.2,15.7,14,14.3]
fig,ax=plt.subplots(figsize=(6.5,3.4))
ax.plot(q,incheon,'-o',color=SON,lw=2,label="인천 권역(송도 포함)")
ax.plot(q,bundang,'-s',color=PAN,lw=2,label="분당역세권(판교 인접)")
ax.plot(q,nation,'--',color='#888',lw=1.6,label="전국")
ax.set_ylabel("오피스 공실률 (%)"); ax.set_title("오피스 공실률 추이 (한국부동산원 R-ONE)")
ax.legend(fontsize=8.5); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(OUT+"fig_vacancy.png",dpi=150); plt.close()
print("figs saved. 판교30분인구 %.1f만 종사자 %.1f만"%(cum(pan_pop,gp)[30],cum(pan_emp,ev)[30]))
