# シェーダと同じ計算式を CPU で再現して、プレビュー画像を描くスクリプト（検証用）
import numpy as np
from PIL import Image
P='Packages/com.sizimityper.fake-interior-shader/Samples/'
room=np.asarray(Image.open(P+'SampleRoom.png').convert('RGBA')).astype(float)/255
cur=np.asarray(Image.open(P+'SampleCurtain.png').convert('RGBA')).astype(float)/255
def samp(t,uv):
    h,w=t.shape[:2]
    x=np.clip((uv[...,0]*w).astype(int),0,w-1); y=np.clip(((1-uv[...,1])*h).astype(int),0,h-1)
    return t[y,x]
def render(cam,W=480,H=480,size=(1.0,1.0),depth=1.0,f=0.5,mid=None):
    fwd=-cam/np.linalg.norm(cam)
    right=np.cross(fwd,[0,1,0]); right/=np.linalg.norm(right); up=np.cross(right,fwd)
    ys,xs=np.mgrid[0:H,0:W]; fov=np.tan(np.radians(30))
    d=fwd+((xs+.5)/W*2-1)[...,None]*fov*right+(1-(ys+.5)/H*2)[...,None]*fov*up
    t=-cam[2]/d[...,2]; p=cam+d*t[...,None]
    hx,hy=size[0]/2,size[1]/2
    on=(abs(p[...,0])<=hx)&(abs(p[...,1])<=hy)&(t>0)
    uv=np.stack([p[...,0]/size[0]+.5,p[...,1]/size[1]+.5],-1)
    v=cam-p
    dv=np.stack([-v[...,0],-v[...,1],np.maximum(v[...,2],1e-5)],-1)
    dv=np.where(abs(dv)<1e-5,1e-5,dv)
    half=np.array([hx,hy,depth/2])
    st=np.stack([(uv[...,0]-.5)*size[0],(uv[...,1]-.5)*size[1],np.full(uv.shape[:2],-depth/2)],-1)
    tA=(np.sign(dv)*half-st)/dv; tH=tA.min(-1); hit=st+dv*tH[...,None]
    zf=np.clip((hit[...,2]+half[2])/depth,0,1); nrm=hit[...,:2]/half[:2]
    ruv=nrm/(1+zf*(1/f-1))[...,None]*.5+.5
    col=samp(room,ruv)[...,:3]
    if mid is not None:
        tm=mid*depth/dv[...,2]; mxy=st[...,:2]+dv[...,:2]*tm[...,None]
        ins=((tm<=tH)&(abs(mxy[...,0])<=hx)&(abs(mxy[...,1])<=hy)).astype(float)
        m=samp(cur,mxy/np.array(size)+.5); a=(m[...,3]*ins)[...,None]
        col=col*(1-a)+m[...,:3]*a
    return np.where(on[...,None],col,np.array([0.25,0.27,0.3]))
imgs=[render(np.array([0,0,2.0])),render(np.array([-1.4,0.5,1.4]),mid=0.15),
      render(np.array([1.2,-0.8,1.2]),size=(1.6,1.0),depth=2.0,mid=0.15)]
Image.fromarray((np.concatenate(imgs,1)*255).astype(np.uint8)).save('Docs~/preview.png')
