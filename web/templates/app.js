// =====================
// SPA NAVIGATION
// =====================

function navigateTo(screenName) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const target = document.getElementById('screen-' + screenName);
    if (target) target.classList.add('active');
    document.querySelectorAll('.nav-item').forEach(n => {
        n.classList.toggle('active', n.dataset.screen === screenName);
    });
    if (screenName === 'recordings') {
        window.isRecordingsPage = true;
        fetchRecordings();
    } else {
        window.isRecordingsPage = false;
    }
}

function desktopNavigateTo(pageId) {
    document.querySelectorAll('.dt-page').forEach(p => p.classList.remove('active'));
    const target = document.getElementById(pageId);
    if (target) target.classList.add('active');
    document.querySelectorAll('.sidebar-item').forEach(n => {
        n.classList.toggle('active', n.dataset.dtscreen === pageId);
    });
    if (pageId === 'dt-recordings') {
        window.isDtRecordingsPage = true;
        fetchRecordings();
    } else {
        window.isDtRecordingsPage = false;
    }
}

window.addEventListener('load', () => {
    if (window.location.hash === '#recordings') {
        navigateTo('recordings');
        desktopNavigateTo('dt-recordings');
    }
});

// =====================
// STATUS
// =====================

let systemRunning = false;

async function updateStatus() {
    try {
        const response = await fetch("/api/status");
        const data = await response.json();
        systemRunning = data.status === "started";

        const statusClass = systemRunning ? 'online' : 'offline';
        const statusText = systemRunning ? 'Online' : 'Offline';

        document.querySelectorAll('#systemStatus, #mobileStatus, #cameraStatus').forEach(el => {
            if (el) {
                el.innerText = statusText;
                el.className = 'status-pill ' + statusClass;
            }
        });

        const powerLabel = document.getElementById('powerLabel');
        const powerDesc = document.getElementById('powerDesc');
        if (powerLabel) powerLabel.innerText = systemRunning ? 'Stop System' : 'Start System';
        if (powerDesc) powerDesc.innerText = systemRunning ? 'Power off' : 'Power on';
    } catch (err) {
        console.error(err);
    }
}

async function toggleSystem() {
    if (systemRunning) {
        await stopSystem();
    } else {
        await startSystem();
    }
}

async function startSystem() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    }
    if (audioContext.state === 'suspended') {
        await audioContext.resume();
    }
    await fetch("/start");
    updateStatus();
}

async function stopSystem() {
    await fetch("/stop");
    updateStatus();
}

// =====================
// DOOR LOCK
// =====================

async function unlockDoor() {
    try {
        await fetch("/api/unlock", { method: "POST" });
        const icon = document.getElementById("visualLock");
        if (icon) { icon.className = "lock-icon unlocked"; icon.innerText = "🔓"; }
    } catch (err) { console.error(err); }
}

async function lockDoor() {
    try {
        await fetch("/api/lock", { method: "POST" });
        const icon = document.getElementById("visualLock");
        if (icon) { icon.className = "lock-icon locked"; icon.innerText = "🔒"; }
    } catch (err) { console.error(err); }
}

// =====================
// SIMULATE MOTION
// =====================

async function simulatePIR() {
    try {
        await fetch("/api/pir-trigger", { method: "POST" });
    } catch (err) { console.error(err); }
}

// =====================
// RECORDINGS
// =====================

function populateRecordingList(listEl, recordings, showAll) {
    if (!listEl) return;
    if (recordings.length > 0) {
        listEl.innerHTML = "";
        let displayList = showAll ? recordings : recordings.slice(0, 3);
        displayList.forEach(vid => {
            const li = document.createElement("li");
            li.innerHTML = `
                <span class="recording-date">📅 ${vid}</span>
                <div style="display: flex; gap: 6px;">
                    <button onclick="playVideo('/storage/${vid}')" style="background: rgba(16,185,129,0.15); color: #10b981;">▶ Play</button>
                    <button onclick="deleteVideo('${vid}')" style="background: rgba(239,68,68,0.15); color: #ef4444;">🗑️</button>
                </div>
            `;
            listEl.appendChild(li);
        });
        if (!showAll && recordings.length > 3) {
            const li = document.createElement("li");
            li.style.cssText = "justify-content:center;background:transparent;border:none;";
            li.innerHTML = `<span style="color:var(--text-muted);font-size:0.85rem;">+ ${recordings.length - 3} more</span>`;
            listEl.appendChild(li);
        }
    } else {
        listEl.innerHTML = "<li style='justify-content:center;color:var(--text-muted);'>No recordings found.</li>";
    }
}

async function fetchRecordings() {
    try {
        const sortEl = document.getElementById("sortOrder") || document.getElementById("dtSortOrder");
        const filterEl = document.getElementById("filterDate") || document.getElementById("dtFilterDate");
        const sortOrder = sortEl ? sortEl.value : "newest";
        const filterDate = filterEl ? filterEl.value : "";

        let url = `/api/recordings?sort=${sortOrder}`;
        if (filterDate) url += `&filter_date=${filterDate}`;

        const res = await fetch(url);
        const data = await res.json();
        const recordings = data.recordings || [];

        populateRecordingList(document.getElementById("recordingList"), recordings, window.isRecordingsPage);
        populateRecordingList(document.getElementById("dtRecordingList"), recordings, window.isDtRecordingsPage);
    } catch (err) { console.error("Failed to fetch recordings", err); }
}

function playVideo(url) {
    const modal = document.getElementById("videoModal") || document.getElementById("dtVideoModal");
    const video = document.getElementById("playbackVideo") || document.getElementById("dtPlaybackVideo");
    if (modal && video) {
        video.src = url;
        modal.style.display = "flex";
        video.play();
    } else {
        window.open(url, '_blank');
    }
}

function closeVideo() {
    ['videoModal', 'dtVideoModal'].forEach(id => {
        const modal = document.getElementById(id);
        if (modal) modal.style.display = "none";
    });
    ['playbackVideo', 'dtPlaybackVideo'].forEach(id => {
        const video = document.getElementById(id);
        if (video) { video.pause(); video.src = ""; }
    });
}

async function deleteVideo(path) {
    if (!confirm("Delete this recording?")) return;
    try {
        const response = await fetch('/api/recordings/' + path, { method: 'DELETE' });
        const data = await response.json();
        if (response.ok && data.status === "deleted") fetchRecordings();
    } catch (err) { console.error(err); }
}

// =====================
// POLLING
// =====================

updateStatus();
fetchRecordings();
setInterval(updateStatus, 3000);
setInterval(fetchRecordings, 5000);

// =====================
// PUSH SUBSCRIPTION
// =====================

function urlB64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) outputArray[i] = rawData.charCodeAt(i);
    return outputArray;
}

const PUBLIC_VAPID_KEY = 'BEo_xhdr9ziVise1izYb0DVhOFhaacTVr9um8-LuqDu8W174q2Ey6woF8RG9VFt3KEzk4-j4hpnrABvjFLsIyuc';

async function subscribeUserToPush(registration) {
    try {
        const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlB64ToUint8Array(PUBLIC_VAPID_KEY)
        });
        await fetch('/api/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(subscription)
        });
    } catch (err) { console.error('Push subscribe failed:', err); }
}

if ('serviceWorker' in navigator && 'PushManager' in window) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(reg => subscribeUserToPush(reg))
            .catch(err => console.error('SW Registration Failed', err));
    });
}

// =====================
// TWO-WAY AUDIO INTERCOM (role-aware PTT)
// =====================
//
// Role is detected automatically:
//   mobile  → screen width < 900 px  (phone/tablet)
//   desktop → screen width >= 900 px
//
// Protocol:
//   connect → send {"type":"register","role":"mobile"|"desktop"}
//   PTT press  → send {"type":"ptt_start"} then stream binary PCM
//   PTT release → send {"type":"ptt_stop"}, stop streaming
//   Server forwards audio only to the OTHER role.
//   Server broadcasts {"type":"ptt_state","talker":"mobile"|"desktop"|null}
//     to all clients so each side can show who is speaking.

let audioWS = null;
let audioContext = null;
let mediaStream = null;
let processor = null;
let isRecording = false;

function getRole() {
    return window.innerWidth < 900 ? 'mobile' : 'desktop';
}

function initAudioIntercom() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    audioWS = new WebSocket(`${protocol}//${window.location.host}/ws/audio`);
    audioWS.binaryType = "arraybuffer";

    audioWS.onopen = () => {
        // Register role immediately on connect
        audioWS.send(JSON.stringify({ type: "register", role: getRole() }));
        setAudioStatus("Intercom Connected");
    };
    audioWS.onclose = () => {
        setAudioStatus("Reconnecting...");
        setTimeout(initAudioIntercom, 3000);
    };
    audioWS.onerror = (err) => console.error("Audio WS Error:", err);

    audioWS.onmessage = async (event) => {
        // JSON control frame (ArrayBuffer containing valid JSON)
        if (event.data instanceof ArrayBuffer) {
            // Try to parse as JSON first (ptt_state messages arrive as binary text)
            try {
                const text = new TextDecoder().decode(event.data);
                const msg = JSON.parse(text);
                if (msg.type === "ptt_state") {
                    _handlePttState(msg.talker);
                    return;
                }
            } catch (_) { /* not JSON — fall through to audio */ }

            // Audio frame — play it
            if (!audioContext) return;
            try {
                const int16Array = new Int16Array(event.data);
                const float32Array = new Float32Array(int16Array.length);
                for (let i = 0; i < int16Array.length; i++) float32Array[i] = int16Array[i] / 32768.0;
                const audioBuffer = audioContext.createBuffer(1, float32Array.length, 16000);
                audioBuffer.getChannelData(0).set(float32Array);
                const source = audioContext.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioContext.destination);
                source.start(0);
            } catch (e) { console.error("Audio playback error:", e); }
        }
    };
}

function _handlePttState(talker) {
    // talker is "mobile", "desktop", or null
    const role = getRole();
    const otherTalking = talker && talker !== role;
    const iAmTalking  = talker === role;

    // Update status text for all intercom status elements
    if (iAmTalking) {
        setAudioStatus("You are speaking...");
    } else if (otherTalking) {
        const label = talker === 'mobile' ? 'Phone' : 'Desktop';
        setAudioStatus(`${label} is speaking...`);
        // Flash the mic buttons to indicate incoming audio
        document.querySelectorAll('#micButton, #desktopMicButton').forEach(b => {
            if (b) b.style.boxShadow = "0 0 0 4px rgba(16,185,129,0.4)";
        });
    } else {
        setAudioStatus("Intercom Connected");
        document.querySelectorAll('#micButton, #desktopMicButton').forEach(b => {
            if (b) b.style.boxShadow = "";
        });
    }
}

function setAudioStatus(text) {
    ['audioStatus', 'desktopAudioStatus'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerText = text;
    });
}

async function startAudio() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    }
    if (audioContext.state === 'suspended') await audioContext.resume();

    try {
        // Signal PTT start to server
        if (audioWS && audioWS.readyState === WebSocket.OPEN) {
            audioWS.send(JSON.stringify({ type: "ptt_start" }));
        }

        isRecording = true;
        document.querySelectorAll('#micButton, #desktopMicButton').forEach(b => {
            if (b) b.style.backgroundColor = "#ef4444";
        });
        setAudioStatus("Speaking...");

        if (!mediaStream) {
            mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        }

        const source = audioContext.createMediaStreamSource(mediaStream);
        processor = audioContext.createScriptProcessor(1024, 1, 1);

        processor.onaudioprocess = (e) => {
            // Silence output buffer to prevent local echo
            const out = e.outputBuffer.getChannelData(0);
            for (let i = 0; i < out.length; i++) out[i] = 0;

            if (!isRecording || !audioWS || audioWS.readyState !== WebSocket.OPEN) return;

            const input = e.inputBuffer.getChannelData(0);
            const int16 = new Int16Array(input.length);
            for (let i = 0; i < input.length; i++) {
                const s = Math.max(-1, Math.min(1, input[i]));
                int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
            audioWS.send(int16.buffer);
        };

        const silencer = audioContext.createGain();
        silencer.gain.value = 0;
        source.connect(processor);
        processor.connect(silencer);
        silencer.connect(audioContext.destination);

    } catch (err) {
        console.error("Mic error:", err);
        setAudioStatus("Mic Access Denied");
    }
}

function stopAudio() {
    isRecording = false;

    // Signal PTT stop to server
    if (audioWS && audioWS.readyState === WebSocket.OPEN) {
        audioWS.send(JSON.stringify({ type: "ptt_stop" }));
    }

    document.querySelectorAll('#micButton, #desktopMicButton').forEach(b => {
        if (b) b.style.backgroundColor = "";
    });
    setAudioStatus("Intercom Connected");

    if (processor) { processor.disconnect(); processor = null; }
    // Keep mediaStream alive for low-latency re-press; it will be released on page unload
}

// =====================
// IN-APP ALERT SYSTEM
// =====================

let lastAlertTime = Date.now() / 1000;

function isMobile() { return window.innerWidth < 900; }

function playAlarmSound() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        [0, 0.2, 0.4].forEach(delay => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = 880;
            osc.type = 'square';
            gain.gain.value = 0.3;
            osc.start(ctx.currentTime + delay);
            osc.stop(ctx.currentTime + delay + 0.15);
        });
    } catch (e) { console.error("Alarm error:", e); }
}

function showToast(message) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:12px;max-width:380px;width:calc(100% - 40px);';
        document.body.appendChild(container);
    }

    const callBtn = isMobile()
        ? `<a href="tel:100" style="display:inline-flex;align-items:center;gap:6px;margin-top:10px;padding:8px 16px;border-radius:50px;background:rgba(239,68,68,0.2);color:#ef4444;text-decoration:none;font-weight:600;font-size:0.85rem;">📞 Call Police</a>`
        : '';

    const toast = document.createElement('div');
    toast.style.cssText = 'background:#1a1a2e;border:1px solid rgba(239,68,68,0.3);border-left:4px solid #ef4444;border-radius:16px;padding:16px 20px;color:#f3f4f6;font-family:Inter,sans-serif;font-size:0.95rem;box-shadow:0 10px 40px rgba(0,0,0,0.5);animation:slideIn 0.3s ease;';
    toast.innerHTML = `
        <div style="display:flex;align-items:flex-start;gap:12px;">
            <span style="font-size:1.4rem;line-height:1;">🚨</span>
            <div style="flex:1;">
                <div style="font-weight:600;margin-bottom:4px;color:#ef4444;">Security Alert</div>
                <div style="color:#d1d5db;font-size:0.9rem;">${message}</div>
                ${callBtn}
            </div>
            <button onclick="this.closest('[style*=slideIn]').remove()" style="background:none;border:none;color:#6b7280;cursor:pointer;font-size:1.1rem;padding:0;line-height:1;font-family:Inter;">✕</button>
        </div>
    `;
    container.prepend(toast);
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 10000);
}

const toastStyle = document.createElement('style');
toastStyle.textContent = `
@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
@keyframes slideOut { from { transform: translateX(0); opacity: 1; } to { transform: translateX(100%); opacity: 0; } }
`;
document.head.appendChild(toastStyle);

setInterval(async () => {
    try {
        const res = await fetch(`/api/alerts?since=${lastAlertTime}`);
        const data = await res.json();
        if (data.alerts && data.alerts.length > 0) {
            data.alerts.forEach(alert => {
                showToast(alert.message);
                if (alert.time > lastAlertTime) lastAlertTime = alert.time;
            });
            playAlarmSound();
            const lastMsg = data.alerts[data.alerts.length - 1].message;
            ['threatLevel', 'heroThreatLevel', 'desktopThreat', 'desktopCamThreat'].forEach(id => {
                const el = document.getElementById(id);
                if (el) { el.innerText = lastMsg; el.style.color = '#ef4444'; }
            });
            ['lastEvent', 'heroLastEvent', 'desktopEvent', 'desktopCamEvent'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.innerText = new Date().toLocaleTimeString();
            });
        }
    } catch (e) { }
}, 2000);

// =====================
// INIT
// =====================
initAudioIntercom();
