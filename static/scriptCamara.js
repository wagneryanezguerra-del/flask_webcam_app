const video = document.getElementById('video-webcam');
const btnAccion = document.getElementById('btn-accion');
const btnCapturar = document.getElementById('btn-capturar');
const mensajeEstado = document.getElementById('mensaje-estado');

let streamCamara = null;

const iniciarCamara = async () => {
    if (streamCamara) {
        streamCamara.getTracks().forEach(track => track.stop());
        video.srcObject = null;
        streamCamara = null;
        btnAccion.textContent = "Encender Cámara";
        btnAccion.classList.remove('apagar');
        mensajeEstado.textContent = "Cámara apagada";
        mensajeEstado.className = "";
    } else {
        try {
            const camara = await navigator.mediaDevices.getUserMedia({ video: true });
            streamCamara = camara;
            video.srcObject = camara;
            btnAccion.textContent = "Apagar Cámara";
            btnAccion.classList.add('apagar');
            mensajeEstado.textContent = "Cámara encendida";
            mensajeEstado.className = "ok";
        } catch (error) {
            console.error("Error al acceder a la cámara: ", error);
            mensajeEstado.textContent = "No se pudo acceder a la cámara.";
            mensajeEstado.className = "error";
        }
    }
};

btnAccion.addEventListener('click', iniciarCamara);

btnCapturar.addEventListener('click', () => {
    if (!streamCamara) {
        mensajeEstado.textContent = "Primero enciende la cámara";
        mensajeEstado.className = "error";
        return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');

    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const dataURL = canvas.toDataURL('image/png');

    fetch('/capturar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ imagen: dataURL })
    })
    .then(res => res.json())
    .then(data => {
        mensajeEstado.textContent = `Foto guardada: ${data.filename}`;
        mensajeEstado.className = "ok";
    })
    .catch(err => {
        console.error("Error al enviar la foto:", err);
        mensajeEstado.textContent = "Error al guardar foto";
        mensajeEstado.className = "error";
    });
});
