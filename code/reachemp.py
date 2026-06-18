import csv, math, heapq, json, numpy as np
from datetime import date
from collections import defaultdict
D="/sessions/epic-eager-bohr/mnt/.projects/019eb978-ac1c-7129-8c8d-bcbdd2ceb136/docs"
U="/sessions/epic-eager-bohr/mnt/uploads/"
# 1) centroid code->xy
xy={}
for fn in ["centroid_11.csv","centroid_23-e35fbbea.csv","centroid_31-997df9d5.csv"]:
    for r in csv.DictReader(open(U+fn)):
        try: xy[r['TOT_OA_CD']]=(float(r['X']),float(r['Y']))
        except: pass
print("centroids:",len(xy))
# 2) emp per code (sum cp_bem_*)
emp=defaultdict(int)
for fn in ["11_2023년_산업분류별(10차_대분류)_종사자수.csv","23_2023년_산업분류별(10차_대분류)_종사자수.csv","31_2023년_산업분류별(10차_대분류)_종사자수.csv"]:
    for r in csv.reader(open(U+fn,encoding='cp949',errors='replace')):
        try: emp[r[1]]+=int(r[3])
        except: pass
print("codes with emp:",len(emp),"total emp:",sum(emp.values()))
# 3) join
ex=[];ey=[];ev=[]
miss=0
for code,v in emp.items():
    if code in xy:
        ex.append(xy[code][0]);ey.append(xy[code][1]);ev.append(v)
    else: miss+=1
ex=np.array(ex);ey=np.array(ey);ev=np.array(ev,float)
print("joined points:",len(ev),"emp covered:",int(ev.sum()),"codes missing centroid:",miss)
# 4) dijkstra
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
def reach(label,srcs):
    dist=dij(srcs); ct=np.full(len(ev),1e18)
    for n,ts in dist.items():
        if ts>3600:continue
        sx,sy=nodes[n]; R=(3600-ts)*WALK/DET
        m=(np.abs(ex-sx)<=R)&(np.abs(ey-sy)<=R)
        if not m.any():continue
        tt=ts+np.hypot(ex[m]-sx,ey[m]-sy)*DET/WALK
        ct[m]=np.minimum(ct[m],tt)
    e30=ev[ct<=1800].sum(); e60=ev[ct<=3600].sum()
    print(f"{label}: 30분 도달종사자 {int(e30):,} | 60분 {int(e60):,}")
    return int(e30),int(e60)
res={}
res['판교']=reach("판교",[26,824])
res['송도']=reach("송도",[249])
json.dump(res,open("reachemp_result.json","w"))
print("ratio30 판교/송도 %.2f"%(res['판교'][0]/res['송도'][0]))
