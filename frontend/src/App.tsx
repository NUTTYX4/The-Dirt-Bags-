import { ChangeEvent, useEffect, useRef, useState } from 'react';
import {
  BookOpen,
  Camera,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  ImagePlus,
  Leaf,
  LoaderCircle,
  RotateCcw,
  Upload,
  WifiOff
} from 'lucide-react';
import { ApiStatus, getApiStatus } from './api';

type View = 'scan' | 'checking' | 'help';

const emptyStatus: ApiStatus = { online: false, models: [] };

export default function App() {
  const [view, setView] = useState<View>('scan');
  const [apiStatus, setApiStatus] = useState<ApiStatus>(emptyStatus);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [photoName, setPhotoName] = useState<string | null>(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const video = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    getApiStatus(controller.signal).then(setApiStatus);
    return () => controller.abort();
  }, []);

  useEffect(() => () => stream?.getTracks().forEach((track) => track.stop()), [stream]);

  const selectPhoto = (file: File) => {
    if (!file.type.startsWith('image/')) return;
    if (photoUrl) URL.revokeObjectURL(photoUrl);
    setPhotoUrl(URL.createObjectURL(file));
    setPhotoName(file.name);
    stopCamera();
    setView('checking');
  };

  const chooseFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) selectPhoto(file);
    event.target.value = '';
  };

  const stopCamera = () => {
    stream?.getTracks().forEach((track) => track.stop());
    setStream(null);
    setCameraOpen(false);
  };

  const openCamera = async () => {
    setCameraError(null);
    try {
      const nextStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false
      });
      setStream(nextStream);
      setCameraOpen(true);
      window.setTimeout(() => {
        if (video.current) video.current.srcObject = nextStream;
      }, 0);
    } catch {
      setCameraError('Camera access is not available. Choose a photo instead.');
    }
  };

  const takePhoto = () => {
    if (!video.current) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.current.videoWidth || 1280;
    canvas.height = video.current.videoHeight || 720;
    const context = canvas.getContext('2d');
    if (!context) return;
    context.drawImage(video.current, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (blob) selectPhoto(new File([blob], 'phytora-plant-photo.jpg', { type: 'image/jpeg' }));
    }, 'image/jpeg', 0.9);
  };

  const readyModels = apiStatus.models.filter((model) => model.ready);

  return (
    <div className="app-shell">
      <header className="top-bar">
        <button className="brand" onClick={() => setView('scan')} aria-label="Phytora home">
          <span className="brand-mark"><Leaf size={20} fill="currentColor" /></span>
          <span>Phytora</span>
        </button>
        <span className={apiStatus.online ? 'service online' : 'service'}>
          {apiStatus.online ? 'Service connected' : 'Service offline'}
        </span>
      </header>

      <main className="content">
        {view === 'scan' && (
          <>
            <section className="intro">
              <p className="eyebrow">Plant helper</p>
              <h1>Take a photo of your plant</h1>
              <p>We will find the crop for you. You do not need to choose it first.</p>
            </section>

            <section className="photo-card" aria-label="Take or upload a plant photo">
              <div className="plant-art"><Leaf size={90} strokeWidth={1.4} /></div>
              <h2>Start a plant check</h2>
              <p>Use a clear photo of one leaf, fruit, stem, flower, root, or the whole plant.</p>
              <div className="action-stack">
                <button className="primary-action" onClick={openCamera}><Camera size={21} /> Use camera</button>
                <button className="secondary-action" onClick={() => fileInput.current?.click()}><Upload size={20} /> Choose photo</button>
              </div>
              <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" onChange={chooseFile} hidden />
              {cameraError && <p className="inline-message"><CircleHelp size={18} /> {cameraError}</p>}
            </section>

            <section className="tips" aria-label="Photo tips">
              <Tip icon={<ImagePlus />} title="Good light" text="Use daylight when you can." />
              <Tip icon={<Leaf />} title="Show one part" text="Keep the leaf or fruit clear." />
              <Tip icon={<Camera />} title="Hold still" text="Avoid blurry photos." />
            </section>

            <section className="supported-note">
              <Leaf size={19} />
              <div><strong>Currently supported</strong><span>Tomato and chilli. More crops can be added later.</span></div>
            </section>
          </>
        )}

        {view === 'checking' && photoUrl && (
          <>
            <img className="photo-preview" src={photoUrl} alt="Selected plant for checking" />
            <section className="checking-card">
              <div className="scan-icon"><LoaderCircle size={42} /></div>
              <h1>Checking your plant</h1>
              <p className="file-name">{photoName}</p>
              <ProgressItem done icon={<CheckCircle2 />} title="Photo ready" />
              <ProgressItem icon={<Leaf />} title="Finding crop" />
              <ProgressItem icon={<Leaf />} title="Checking plant part" />
              <ProgressItem icon={<CheckCircle2 />} title="Looking for problems" />
            </section>

            {apiStatus.online && readyModels.length > 0 ? (
              <section className="notice-card">
                <h2>Automatic checking needs one more backend service</h2>
                <p>The connected API has disease models, but it does not yet identify the crop and route this photo to the right model automatically. Phytora will not guess or run a model against the wrong crop.</p>
              </section>
            ) : (
              <section className="notice-card warning">
                <WifiOff size={24} />
                <div><h2>Plant check is not ready</h2><p>{apiStatus.message || 'No ready plant models were found.'}</p></div>
              </section>
            )}

            <section className="safe-card">
              <CheckCircle2 size={23} />
              <div><strong>We will not guess.</strong><span>If the crop cannot be identified, Phytora will ask for a clearer photo instead of showing a diagnosis.</span></div>
            </section>
            <button className="secondary-action full" onClick={() => setView('scan')}><RotateCcw size={19} /> Take another photo</button>
          </>
        )}

        {view === 'help' && (
          <>
            <section className="intro"><p className="eyebrow">Simple photo tips</p><h1>Get a clear plant photo</h1></section>
            <section className="help-list">
              <HelpStep number="1" title="Use daylight" text="Stand where the leaf is bright but not shiny." />
              <HelpStep number="2" title="Keep one part in view" text="Show the leaf, fruit, stem, flower, root, or whole plant." />
              <HelpStep number="3" title="Hold your phone still" text="Wait until the image is clear before taking the photo." />
            </section>
          </>
        )}
      </main>

      <nav className="bottom-nav" aria-label="Main navigation">
        <button className={view === 'scan' || view === 'checking' ? 'active' : ''} onClick={() => setView('scan')}><Camera size={21} /><span>Scan</span></button>
        <button disabled title="Saved checks will be available when the inspection-history API is connected."><BookOpen size={21} /><span>My plants</span></button>
        <button className={view === 'help' ? 'active' : ''} onClick={() => setView('help')}><CircleHelp size={21} /><span>Help</span></button>
      </nav>

      {cameraOpen && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Take plant photo">
          <section className="camera-modal">
            <div className="modal-title"><h2>Keep the plant inside the frame</h2><button onClick={stopCamera} aria-label="Close camera">×</button></div>
            <video ref={video} autoPlay playsInline muted />
            <button className="primary-action" onClick={takePhoto}><Camera size={21} /> Take photo</button>
          </section>
        </div>
      )}
    </div>
  );
}

function Tip({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return <article><span>{icon}</span><strong>{title}</strong><p>{text}</p></article>;
}

function ProgressItem({ icon, title, done = false }: { icon: React.ReactNode; title: string; done?: boolean }) {
  return <div className={done ? 'progress-row done' : 'progress-row'}><span>{icon}</span><strong>{title}</strong>{done ? <CheckCircle2 size={19} /> : <span className="waiting-dot" />}</div>;
}

function HelpStep({ number, title, text }: { number: string; title: string; text: string }) {
  return <article className="help-step"><span>{number}</span><div><h2>{title}</h2><p>{text}</p></div><ChevronRight size={20} /></article>;
}
