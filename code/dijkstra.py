import csv, heapq
from collections import defaultdict
from datetime import date
D="/sessions/epic-eager-bohr/mnt/.projects/019eb978-ac1c-7129-8c8d-bcbdd2ceb136/docs"
CUTOFF=date(2026,6,18)
def pd(s):
    s=(s or '').strip()
    if not s: return None
    try: y,m,d=s.split('-'); return date(int(y),int(m),int(d))
    except: return None
nodes={}
for r in csv.DictReader(open(f"{D}/nodes.tsv"),delimiter='\t'):
    nodes[int(r['id'])]=r
# operational filter: node begin (effective_begin overrides) <= cutoff
def node_ok(r):
    b=pd(r['effective_begin']) or pd(r['begin'])
    return (b is None) or (b<=CUTOFF)
adj=defaultdict(list)
nlink=0
for r in csv.DictReader(open(f"{D}/links.tsv"),delimiter='\t'):
    b=pd(r['begin'])
    if b and b>CUTOFF: continue
    f=int(r['fromNode']); t=int(r['toNode'])
    if f not in nodes or t not in nodes: continue
    if not node_ok(nodes[f]) or not node_ok(nodes[t]): continue
    adj[f].append((t,float(r['timeFT'])))
    adj[t].append((f,float(r['timeTF'])))
    nlink+=1
print("operational links:",nlink,"nodes:",len(nodes))

def dijkstra(sources):
    dist={s:0.0 for s in sources}
    pq=[(0.0,s) for s in sources]; heapq.heapify(pq)
    while pq:
        d,u=heapq.heappop(pq)
        if d>dist.get(u,1e18): continue
        for v,w in adj[u]:
            nd=d+w
            if nd<dist.get(v,1e18):
                dist[v]=nd; heapq.heappush(pq,(nd,v))
    return dist

def station_times(dist):
    # min time per (statnm,linenm) node already; collapse to station name (min across lines)
    best={}
    for nid,t in dist.items():
        nm=nodes[nid]['statnm']
        if nm not in best or t<best[nm][0]:
            best[nm]=(t,nid)
    return best

for label,srcs in [("판교 (신분당·경강)",[26,824]),("국제업무지구 (인천1호선)",[249])]:
    dist=dijkstra(srcs)
    st=station_times(dist)
    n30=sum(1 for nm,(t,_) in st.items() if t<=1800)
    n60=sum(1 for nm,(t,_) in st.items() if t<=3600)
    print(f"\n===== {label} =====")
    print(f"도달 가능 역(전체): {len(st)}  | 30분 이내: {n30}개  | 60분 이내: {n60}개")
    # save reachable stations csv
    safe=label.split()[0]
    with open(f"reach_{safe}.csv","w",newline='') as f:
        w=csv.writer(f); w.writerow(["statnm","linenm","minutes","lng","lat","within30","within60"])
        for nm,(t,nid) in sorted(st.items(),key=lambda x:x[1][0]):
            r=nodes[nid]
            w.writerow([nm,r['linenm'],round(t/60,1),r['lng'],r['lat'],int(t<=1800),int(t<=3600)])
    # sample nearest farthest within 30
    within30=sorted([(t,nm) for nm,(t,_) in st.items() if t<=1800])
    print("  30분권 대표역(먼 쪽 5개):",[f"{nm} {t/60:.0f}분" for t,nm in within30[-5:]])
print("\nsaved reach_*.csv")
