import subprocess,re,json,sys
def tighten(src,dst,keep=0.24,thr=-35,mind=0.25):
    out=subprocess.run(["ffmpeg","-nostats","-i",src,"-af",f"silencedetect=n={thr}dB:d={mind}","-f","null","-"],capture_output=True,text=True).stderr
    ss=[float(x) for x in re.findall(r"silence_start: ([0-9.]+)",out)]; se=[float(x) for x in re.findall(r"silence_end: ([0-9.]+)",out)]
    dur=float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",src],capture_output=True,text=True).stdout)
    segs=[];t=0
    for a,b in zip(ss,se):
        if b>=dur-0.05: segs.append((t,min(a+keep/2,dur)));t=None;break
        segs.append((t,a+keep/2)); t=b-keep/2
    if t is not None: segs.append((t,dur))
    f="".join(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[s{i}];" for i,(a,b) in enumerate(segs))+"".join(f"[s{i}]" for i in range(len(segs)))+f"concat=n={len(segs)}:v=0:a=1[o]"
    subprocess.run(["ffmpeg","-v","error","-y","-i",src,"-filter_complex",f,"-map","[o]","-c:a","pcm_s16le","-ar","44100",dst],check=True)
    # new speech starts: each seg start offset by keep/2 (except first)
    starts=[];acc=0
    for i,(a,b) in enumerate(segs):
        starts.append(round(acc+(keep/2 if i else 0),2)); acc+=b-a
    return starts,round(acc,2)
if __name__=="__main__":
    print(tighten(sys.argv[1],sys.argv[2]))
