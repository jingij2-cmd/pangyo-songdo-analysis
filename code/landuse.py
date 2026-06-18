import json, math, numpy as np
from collections import defaultdict

U = "/sessions/epic-eager-bohr/mnt/uploads/"

# ---- EPSG:5174 (Korean1985 / Modified Central Belt, Bessel) inverse TM -> geographic(Bessel) ----
a=6377397.155; f=1/299.1528128; e2=f*(2-f)
lat0=math.radians(38.0); lon0=math.radians(127.0028902777778)
k0=1.0; FE=200000.0; FN=500000.0
def Mlat(phi):
    return a*((1-e2/4-3*e2**2/64-5*e2**3/256)*phi
        -(3*e2/8+3*e2**2/32+45*e2**3/1024)*math.sin(2*phi)
        +(15*e2**2/256+45*e2**3/1024)*math.sin(4*phi)
        -(35*e2**3/3072)*math.sin(6*phi))
M0=Mlat(lat0)
e1=(1-math.sqrt(1-e2))/(1+math.sqrt(1-e2))
def tm_inv(E,N):
    M=M0+(N-FN)/k0
    mu=M/(a*(1-e2/4-3*e2**2/64-5*e2**3/256))
    phi1=mu+(3*e1/2-27*e1**3/32)*math.sin(2*mu)+(21*e1**2/16-55*e1**4/32)*math.sin(4*mu)+(151*e1**3/96)*math.sin(6*mu)+(1097*e1**4/512)*math.sin(8*mu)
    ep2=e2/(1-e2)
    C1=ep2*math.cos(phi1)**2
    T1=math.tan(phi1)**2
    N1=a/math.sqrt(1-e2*math.sin(phi1)**2)
    R1=a*(1-e2)/(1-e2*math.sin(phi1)**2)**1.5
    D=(E-FE)/(N1*k0)
    lat=phi1-(N1*math.tan(phi1)/R1)*(D**2/2-(5+3*T1+10*C1-4*C1**2-9*ep2)*D**4/24+(61+90*T1+298*C1+45*T1**2-252*ep2-3*C1**2)*D**6/720)
    lon=lon0+(D-(1+2*T1+C1)*D**3/6+(5-2*C1+28*T1-3*C1**2+8*ep2+24*T1**2)*D**5/120)/math.cos(phi1)
    return lat,lon
# geodetic(Bessel)->geocentric
def geod2ecef(lat,lon,aa,ee2,h=0):
    N=aa/math.sqrt(1-ee2*math.sin(lat)**2)
    x=(N+h)*math.cos(lat)*math.cos(lon)
    y=(N+h)*math.cos(lat)*math.sin(lon)
    z=(N*(1-ee2)+h)*math.sin(lat)
    return x,y,z
# Helmert Bessel(Korean1985)->WGS84 (towgs84 of EPSG:5174, position-vector)
dx,dy,dz=-115.80,474.99,674.11
rx,ry,rz=[math.radians(v/3600) for v in (1.16,-2.31,-1.63)]
ds=6.43e-6
def helmert(x,y,z):
    s=1+ds
    X=dx+s*(x - rz*y + ry*z)
    Y=dy+s*(rz*x + y - rx*z)
    Z=dz+s*(-ry*x + rx*y + z)
    return X,Y,Z
aw=6378137.0; fw=1/298.257223563; ew2=fw*(2-fw)
def ecef2geod(x,y,z):
    lon=math.atan2(y,x); p=math.hypot(x,y)
    lat=math.atan2(z,p*(1-ew2))
    for _ in range(6):
        N=aw/math.sqrt(1-ew2*math.sin(lat)**2)
        h=p/math.cos(lat)-N
        lat=math.atan2(z,p*(1-ew2*N/(N+h)))
    return math.degrees(lat),math.degrees(lon)
def to_wgs(E,N):
    lat,lon=tm_inv(E,N)
    x,y,z=geod2ecef(lat,lon,a,e2)
    X,Y,Z=helmert(x,y,z)
    la,lo=ecef2geod(X,Y,Z)
    return lo,la  # lon,lat

def load_boundary(fn):
    d=json.load(open(U+fn)); ft=d['features'][0]
    g=ft['geometry']; polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
    out=[]
    for poly in polys:
        rings=[]
        for ring in poly:
            rings.append([to_wgs(x,y) for x,y in ring])
        out.append(rings)
    return out, ft['properties']

def load_uq(fn):
    d=json.load(open(U+fn))['response']['result']['featureCollection']['features']
    feats=[]
    for ft in d:
        g=ft['geometry']; polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
        feats.append((ft['properties']['uname'],polys))  # already lon,lat WGS84
    return feats

# local equirectangular meters
def make_proj(lon0d,lat0d):
    cl=math.cos(math.radians(lat0d))
    return lambda lon,lat:((lon-lon0d)*111320.0*cl,(lat-lat0d)*110540.0)

def rings_to_xy(rings,proj):
    return [np.array([proj(x,y) for x,y in r]) for r in rings]

def pip_evenodd(pts, ring):  # pts (N,2), ring (M,2) -> bool inside this single ring (numpy)
    x=pts[:,0]; y=pts[:,1]; n=len(ring); inside=np.zeros(len(pts),bool)
    j=n-1
    for i in range(n):
        xi,yi=ring[i]; xj,yj=ring[j]
        cond=((yi>y)!=(yj>y))
        with np.errstate(divide='ignore',invalid='ignore'):
            xint=(xj-xi)*(y-yi)/(yj-yi)+xi
        inside^=cond&(x<xint)
        j=i
    return inside

def inside_multipoly(pts, polys_xy):  # polys_xy: list of polys; poly=list of rings(np) ; even-odd per poly (handles holes), OR across polys
    res=np.zeros(len(pts),bool)
    for rings in polys_xy:
        pin=np.zeros(len(pts),bool)
        for r in rings: pin^=pip_evenodd(pts,r)
        res|=pin
    return res

def analyze(name, bfn, ufn):
    bnd,props=load_boundary(bfn)
    # centroid for proj
    allpts=[p for poly in bnd for r in poly for p in r]
    lon0d=np.mean([p[0] for p in allpts]); lat0d=np.mean([p[1] for p in allpts])
    proj=make_proj(lon0d,lat0d)
    bnd_xy=[rings_to_xy(poly,proj) for poly in bnd]
    uq=load_uq(ufn)
    # grid
    xs=np.concatenate([poly[0][:,0] for poly in bnd_xy]); ys=np.concatenate([poly[0][:,1] for poly in bnd_xy])
    # use all rings extent
    allx=np.concatenate([r[:,0] for poly in bnd_xy for r in poly]); ally=np.concatenate([r[:,1] for poly in bnd_xy for r in poly])
    step=4.0
    gx=np.arange(allx.min(),allx.max(),step); gy=np.arange(ally.min(),ally.max(),step)
    GX,GY=np.meshgrid(gx,gy); pts=np.column_stack([GX.ravel(),GY.ravel()])
    inb=inside_multipoly(pts,bnd_xy)
    bpts=pts[inb]
    cell=step*step
    bnd_area=len(bpts)*cell
    # assign each boundary pt to a uname
    labels=np.full(len(bpts),'',dtype=object)
    for uname,polys in uq:
        polys_xy=[rings_to_xy(poly,proj) for poly in polys]
        ins=inside_multipoly(bpts,polys_xy)
        take=ins & (labels=='')
        labels[take]=uname
    from collections import Counter
    cnt=Counter(labels)
    print(f"\n===== {name} =====")
    print("boundary dgm_ar(field):",props.get('dgm_ar'),"| grid boundary area(m2): %.0f"%bnd_area)
    assigned=sum(v for k,v in cnt.items() if k!='')
    print("coverage by 용도지역: %.1f%%"%(100*assigned/len(bpts)))
    # detailed
    res={}
    for k,v in cnt.items():
        res[k]=v*cell
    # broad class
    def broad(u):
        if u=='':return '미지정/공지'
        if '주거' in u:return '주거'
        if '상업' in u:return '상업'
        if '공업' in u:return '공업'
        if '녹지' in u:return '녹지'
        return '기타'
    broadarea=defaultdict(float)
    for k,v in res.items(): broadarea[broad(k)]+=v
    tot=bnd_area
    print("-- 용도지역(대분류) 구성비 --")
    for k in sorted(broadarea,key=lambda x:-broadarea[x]):
        print(f"  {k:8s} {broadarea[k]:12.0f} m2  {100*broadarea[k]/tot:5.1f}%")
    # entropy (broad, excluding 미지정 from mix? include all present)
    ps=[broadarea[k]/tot for k in broadarea if broadarea[k]>0]
    K=len(ps); ent=-sum(p*math.log(p) for p in ps); lum=ent/math.log(K) if K>1 else 0
    print(f"  혼합도 LUM(엔트로피, 대분류 {K}종): {lum:.3f}")
    return name,props,bnd_area,broadarea,res,lum,tot,assigned/len(bpts)

R=[]
R.append(analyze("판교 제1테크노밸리","pangyo_boundary.geojson","pangyo_uq.json"))
R.append(analyze("송도 IBD","songdo_boundary.geojson","songdo_uq.json"))
import pickle; pickle.dump(R,open("/sessions/epic-eager-bohr/mnt/outputs/landuse_result.pkl","wb"))
