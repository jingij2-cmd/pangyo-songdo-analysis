import csv, math, heapq, json, numpy as np
from datetime import date
from collections import defaultdict
D="/sessions/epic-eager-bohr/mnt/.projects/019eb978-ac1c-7129-8c8d-bcbdd2ceb136/docs"
GRID="/sessions/epic-eager-bohr/mnt/uploads/2024년_인구_다사_100M.csv"
U="/sessions/epic-eager-bohr/mnt/uploads/"
OX,OY=900000.0,1900000.0
# ---- 5179 inverse (GRS80) ----
a=6378137.0; f=1/298.257222101; e2=f*(2-f); k0=0.9996
lat0=math.radians(38.0); lon0=math.radians(127.5); FE=1000000.0; FN=2000000.0
def Mm(phi): return a*((1-e2/4-3*e2**2/64-5*e2**3/256)*phi-(3*e2/8+3*e2**2/32+45*e2**3/1024)*math.sin(2*phi)+(15*e2**2/256+45*e2**3/1024)*math.sin(4*phi)-(35*e2**3/3072)*math.sin(6*phi))
M0=Mm(lat0); e1=(1-math.sqrt(1-e2))/(1+math.sqrt(1-e2))
def inv5179(E,N):
    mu=(M0+(N-FN)/k0)/(a*(1-e2/4-3*e2**2/64-5*e2**3/256))
    p1=mu+(3*e1/2-27*e1**3/32)*math.sin(2*mu)+(21*e1**2/16)*math.sin(4*mu)+(151*e1**3/96)*math.sin(6*mu)
    C1=(e2/(1-e2))*math.cos(p1)**2; T1=math.tan(p1)**2
    N1=a/math.sqrt(1-e2*math.sin(p1)**2); R1=a*(1-e2)/(1-e2*math.sin(p1)**2)**1.5
    Dd=(E-FE)/(N1*k0); ep2=e2/(1-e2)
    lat=p1-(N1*math.tan(p1)/R1)*(Dd**2/2-(5+3*T1+10*C1-4*C1**2-9*ep2)*Dd**4/24)
    lon=lon0+(Dd-(1+2*T1+C1)*Dd**3/6+(5-2*C1+28*T1)*Dd**5/120)/math.cos(p1)
    return math.degrees(lat),math.degrees(lon)
# ---- 5174 -> wgs (Bessel+helmert) for boundaries ----
ba=6377397.155; bf=1/299.1528128; be2=bf*(2-bf)
blat0=math.radians(38.0); blon0=math.radians(127.0028902777778); bFE=200000.0; bFN=500000.0
def bM(phi): return ba*((1-be2/4-3*be2**2/64)*phi-(3*be2/8+3*be2**2/32)*math.sin(2*phi)+(15*be2**2/256)*math.sin(4*phi))
bM0=bM(blat0); be1=(1-math.sqrt(1-be2))/(1+math.sqrt(1-be2))
def btm_inv(E,N):
    mu=(bM0+(N-bFN))/(ba*(1-be2/4-3*be2**2/64-5*be2**3/256))
    p1=mu+(3*be1/2-27*be1**3/32)*math.sin(2*mu)+(21*be1**2/16)*math.sin(4*mu)+(151*be1**3/96)*math.sin(6*mu)
    C1=(be2/(1-be2))*math.cos(p1)**2; T1=math.tan(p1)**2
    N1=ba/math.sqrt(1-be2*math.sin(p1)**2); R1=ba*(1-be2)/(1-be2*math.sin(p1)**2)**1.5
    Dd=(E-bFE)/(N1); ep2=be2/(1-be2)
    lat=p1-(N1*math.tan(p1)/R1)*(Dd**2/2-(5+3*T1+10*C1-9*ep2)*Dd**4/24)
    lon=blon0+(Dd-(1+2*T1+C1)*Dd**3/6)/math.cos(p1)
    return lat,lon
def g2e(lat,lon,aa,ee2):
    N=aa/math.sqrt(1-ee2*math.sin(lat)**2)
    return ((N)*math.cos(lat)*math.cos(lon),(N)*math.cos(lat)*math.sin(lon),(N*(1-ee2))*math.sin(lat))
dxh,dyh,dzh=-115.80,474.99,674.11; rxh,ryh,rzh=[math.radians(v/3600) for v in (1.16,-2.31,-1.63)]; dsh=6.43e-6
def helm(x,y,z):
    s=1+dsh; return (dxh+s*(x-rzh*y+ryh*z),dyh+s*(rzh*x+y-rxh*z),dzh+s*(-ryh*x+rxh*y+z))
aw=6378137.0; ew2=(1/298.257223563)*(2-1/298.257223563)
def e2g(x,y,z):
    lon=math.atan2(y,x); p=math.hypot(x,y); lat=math.atan2(z,p*(1-ew2))
    for _ in range(6):
        N=aw/math.sqrt(1-ew2*math.sin(lat)**2); h=p/math.cos(lat)-N; lat=math.atan2(z,p*(1-ew2*N/(N+h)))
    return math.degrees(lat),math.degrees(lon)
def wgs5174(E,N):
    la,lo=btm_inv(E,N); x,y,z=g2e(la,lo,ba,be2); X,Y,Z=helm(x,y,z); la2,lo2=e2g(X,Y,Z); return [lo2,la2]
def bnd_wgs(fn):
    d=json.load(open(U+fn)); g=d['features'][0]['geometry']
    polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
    return [[[wgs5174(x,y) for x,y in ring] for ring in poly] for poly in polys]

# ---- grid ----
gx=[];gy=[];gp=[]
for row in csv.reader(open(GRID,encoding='cp949',errors='replace')):
    if row[2]!='to_in_001':continue
    dd=row[1].replace('다사',''); gx.append(OX+int(dd[:3])*100+50); gy.append(OY+int(dd[3:])*100+50)
    try:gp.append(int(row[3]))
    except:gp.append(0)
gx=np.array(gx);gy=np.array(gy);gp=np.array(gp,float)
# ---- dijkstra ----
nodes={}
for r in csv.DictReader(open(f"{D}/nodes.tsv"),delimiter='\t'):
    nodes[int(r['id'])]=(float(r['x_5179']),float(r['y_5179']),r['statnm'],r['begin'],r['effective_begin'],float(r['lng']),float(r['lat']))
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
def cells_band(srcs):
    dist=dij(srcs); ct=np.full(len(gp),1e18)
    for n,ts in dist.items():
        if ts>3600:continue
        sx,sy=nodes[n][0],nodes[n][1]; R=(3600-ts)*WALK/DET
        m=(np.abs(gx-sx)<=R)&(np.abs(gy-sy)<=R)
        if not m.any():continue
        tt=ts+np.hypot(gx[m]-sx,gy[m]-sy)*DET/WALK
        ct[m]=np.minimum(ct[m],tt)
    # aggregate to 500m
    keyx=((gx-OX)//500).astype(int); keyy=((gy-OY)//500).astype(int)
    agg={}
    for i in range(len(gp)):
        if ct[i]>3600:continue
        k=(keyx[i],keyy[i])
        cx=OX+keyx[i]*500+250; cy=OY+keyy[i]*500+250
        if k not in agg or ct[i]<agg[k][0]: 
            la,lo=inv5179(cx,cy); agg[k]=[ct[i],lo,la,0]
        agg[k][3]+=gp[i]
    out=[]
    for v in agg.values():
        out.append([round(v[1],5),round(v[2],5),1 if v[0]<=1800 else 2,int(v[3])])
    return out
def stations(srcs):
    dist=dij(srcs); o=[]
    for n,ts in dist.items():
        if ts>3600:continue
        o.append([round(nodes[n][5],5),round(nodes[n][6],5),round(ts/60),nodes[n][2]])
    return o
PAN={"cells":cells_band([26,824]),"stations":stations([26,824]),"name":"판교 제1테크노밸리","core":[127.1114,37.3948]}
SON={"cells":cells_band([249]),"stations":stations([249]),"name":"송도 국제업무지구","core":[126.6305,37.3997]}
BND={"pangyo":bnd_wgs("pangyo_boundary.geojson"),"songdo":bnd_wgs("songdo_boundary.geojson")}
json.dump({"pangyo":PAN,"songdo":SON,"bnd":BND},open("mapdata.json","w"))
print("PAN cells",len(PAN["cells"]),"stations",len(PAN["stations"]))
print("SON cells",len(SON["cells"]),"stations",len(SON["stations"]))
