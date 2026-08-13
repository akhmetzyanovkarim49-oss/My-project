// === 1. КОНФИГУРАЦИЯ И ИНИЦИАЛИЗАЦИЯ ===
const firebaseConfig = {
    databaseURL: "https://mesanger-1157b-default-rtdb.firebaseio.com/"
};

if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}
const db = firebase.database();

// ICE-серверы (STUN + TURN) для надежного пробития 4G/Wi-Fi
const iceConfig = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' },
        { urls: 'turn:openrelay.metered.ca:80', username: 'openrelay', credential: 'openrelay' },
        { urls: 'turn:openrelay.metered.ca:443', username: 'openrelay', credential: 'openrelay' }
    ]
};

// === 2. АВТОРИЗАЦИЯ И ПОЛУЧЕНИЕ ID ===
function getMyId() {
    let id = localStorage.getItem("user_id");
    if (!id) {
        id = Math.floor(100000 + Math.random() * 900000).toString();
        localStorage.setItem("user_id", id);
    }
    return id;
}

const MY_ID = getMyId();
let currentChatPartner = null;

document.addEventListener("DOMContentLoaded", () => {
    const el = document.getElementById("my-id-display");
    if (el) el.innerText = `ID: ${MY_ID}`;
    
    // Подписка на входящие звонки
    listenForIncomingCalls();
});

// === 3. ЛОГИКА ЧАТА ===
function startNewChat() {
    const input = document.getElementById("target-id-input");
    const targetId = input.value.trim();
    if (!targetId) return alert("Введите ID собеседника");
    if (targetId === MY_ID) return alert("Нельзя создать чат с самим собой");
    
    currentChatPartner = targetId;
    loadMessages();
}

function sendMessage() {
    const input = document.getElementById("message-input");
    const text = input.value.trim();
    if (!text || !currentChatPartner) return alert("Выберите чат перед отправкой!");

    const chatId = [MY_ID, currentChatPartner].sort().join("_");
    
    db.ref(`chats/${chatId}/messages`).push({
        sender: MY_ID,
        text: text,
        timestamp: Date.now()
    });

    input.value = "";
}

function loadMessages() {
    if (!currentChatPartner) return;
    const chatId = [MY_ID, currentChatPartner].sort().join("_");
    const chatBox = document.getElementById("chat-box");

    db.ref(`chats/${chatId}/messages`).on("value", (snapshot) => {
        chatBox.innerHTML = "";
        const data = snapshot.val();
        if (!data) {
            chatBox.innerHTML = '<div class="placeholder-text">Сообщений пока нет. Напишите первым!</div>';
            return;
        }

        Object.values(data).forEach(msg => {
            const msgDiv = document.createElement("div");
            msgDiv.className = `message ${msg.sender === MY_ID ? 'my' : 'other'}`;
            msgDiv.innerText = msg.text;
            chatBox.appendChild(msgDiv);
        });
        chatBox.scrollTop = chatBox.scrollHeight;
    });
}

// === 4. ДВИЖОК ЗВОНКОВ (WebRTC + TURN) ===
let peerConnection = null;
let localStream = null;
let currentCallId = null;

async function makeCall() {
    if (!currentChatPartner) return alert("Сначала введите ID и нажмите '+ Чат'");
    
    currentCallId = `call_${MY_ID}_${currentChatPartner}`;
    peerConnection = new RTCPeerConnection(iceConfig);

    try {
        localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));
    } catch (err) {
        return alert("Ошибка доступа к микрофону: " + err);
    }

    // Слушаем удаленный аудиопоток
    peerConnection.ontrack = (event) => {
        const audio = new Audio();
        audio.srcObject = event.streams[0];
        audio.play();
    };

    peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
            db.ref(`calls/${currentCallId}/caller_candidates`).push(event.candidate.toJSON());
        }
    };

    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);

    await db.ref(`calls/${currentCallId}`).set({
        caller: MY_ID,
        receiver: currentChatPartner,
        status: "OFFER",
        offer: { type: offer.type, sdp: offer.sdp }
    });

    // Отслеживаем ответ
    db.ref(`calls/${currentCallId}`).on('value', async (snapshot) => {
        const data = snapshot.val();
        if (!data) return;

        if (data.status === "ANSWER" && data.answer && !peerConnection.currentRemoteDescription) {
            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
        }

        if (data.status === "ENDED") {
            endCallLocally();
        }
    });
}

// Прослушивание входящих звонков
function listenForIncomingCalls() {
    db.ref("calls").on("child_added", async (snapshot) => {
        const callData = snapshot.val();
        if (!callData) return;

        if (callData.receiver === MY_ID && callData.status === "OFFER") {
            const accept = confirm(`Входящий звонок от ID: ${callData.caller}. Принять?`);
            if (accept) {
                acceptCall(snapshot.key, callData.offer);
            } else {
                db.ref(`calls/${snapshot.key}`).update({ status: "ENDED" });
            }
        }
    });
}

async function acceptCall(callId, offerData) {
    currentCallId = callId;
    peerConnection = new RTCPeerConnection(iceConfig);

    try {
        localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));
    } catch (err) {
        return alert("Ошибка доступа к микрофону: " + err);
    }

    peerConnection.ontrack = (event) => {
        const audio = new Audio();
        audio.srcObject = event.streams[0];
        audio.play();
    };

    peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
            db.ref(`calls/${currentCallId}/receiver_candidates`).push(event.candidate.toJSON());
        }
    };

    await peerConnection.setRemoteDescription(new RTCSessionDescription(offerData));
    const answer = await peerConnection.createAnswer();
    await peerConnection.setLocalDescription(answer);

    await db.ref(`calls/${currentCallId}`).update({
        status: "ANSWER",
        answer: { type: answer.type, sdp: answer.sdp }
    });
}

function endCallLocally() {
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localStream = null;
    }
    currentCallId = null;
}
