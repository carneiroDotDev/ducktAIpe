const createForm = document.getElementById('create-form');
const topicInput = document.getElementById('topic-input');
const createButton = document.getElementById('create-button');
const progressContainer = document.getElementById('progress-container');
const statusText = document.getElementById('status-text');
const gatekeeperMessage = document.getElementById('gatekeeper-message');

// Generate a random session ID for this browser session
const sessionId = 'session-' + Math.random().toString(36).substring(2, 15);

function showProgress() {
    createForm.classList.add('hidden'); // Optionally hide form, or just disable
    topicInput.disabled = true;
    createButton.disabled = true;
    createButton.innerHTML = 'Building...';
    gatekeeperMessage.classList.add('hidden');
    progressContainer.classList.remove('hidden');
}

function resetForm(errorMessage) {
    createForm.classList.remove('hidden');
    topicInput.disabled = false;
    createButton.disabled = false;
    createButton.innerHTML = `
        <span>Start Fixing</span>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
            <path fill-rule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clip-rule="evenodd" />
        </svg>
    `;
    progressContainer.classList.add('hidden');
    gatekeeperMessage.textContent = errorMessage;
    gatekeeperMessage.classList.remove('hidden');
}

function updateStatus(text) {
    statusText.textContent = text;
    
    // Simple logic to highlight steps based on text content
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
    
    if (text.toLowerCase().includes('research')) {
        document.getElementById('step-researcher').classList.add('active');
    } else if (text.toLowerCase().includes('judge') || text.toLowerCase().includes('evaluating')) {
        document.getElementById('step-judge').classList.add('active');
    } else if (text.toLowerCase().includes('writ') || text.toLowerCase().includes('build')) {
        document.getElementById('step-builder').classList.add('active');
    }
}

// Image upload elements
const imageUpload = document.getElementById('image-upload');
const imageLoading = document.getElementById('image-loading');
const imagePreviewContainer = document.getElementById('image-preview-container');
const imagePreview = document.getElementById('image-preview');
const removeImageBtn = document.getElementById('remove-image-btn');

let currentImageFile = null;

imageUpload.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 3 * 1024 * 1024) {
        alert('Image exceeds the 3MB limit. Please upload a smaller image.');
        imageUpload.value = '';
        return;
    }

    // Start loading
    topicInput.classList.add('hidden');
    imagePreviewContainer.classList.add('hidden');
    imageLoading.classList.remove('hidden');
    createButton.disabled = true;

    // Simulate upload delay
    setTimeout(() => {
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            imageLoading.classList.add('hidden');
            imagePreviewContainer.classList.remove('hidden');
            
            // Extract base64 payload and mime type separately for the backend
            const dataUrl = e.target.result;
            const match = dataUrl.match(/^data:(.*?);base64,(.*)$/);
            
            if (match) {
                currentImageFile = {
                    file: file,
                    mimeType: match[1],
                    base64: match[2]
                };
            }
            createButton.disabled = false;
        };
        reader.readAsDataURL(file);
    }, 1500); // 1.5s mock upload time for authenticity effect
});

removeImageBtn.addEventListener('click', () => {
    imageUpload.value = '';
    currentImageFile = null;
    imagePreviewContainer.classList.add('hidden');
    topicInput.classList.remove('hidden');
});

createForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const topic = topicInput.value.trim();
    
    // Require either a topic or an image to be present
    if (!topic && !currentImageFile) return;

    // Use user prompt. If empty, instruct the gatekeeper to check the image.
    const finalMessage = topic || "Please tell me what this broken object is and how to fix it.";

    showProgress();

    try {
        const payload = {
            message: finalMessage,
            session_id: sessionId
        };
        
        if (currentImageFile) {
            payload.image_base64 = currentImageFile.base64;
            payload.image_mime_type = currentImageFile.mimeType;
        }

        const response = await fetch('/api/chat_stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const data = JSON.parse(line);
                    if (data.type === 'progress') {
                        updateStatus(data.text);
                    } else if (data.type === 'gatekeeper_reject') {
                        resetForm(data.text);
                        return; // Break out of this stream and let user retry
                    } else if (data.type === 'gatekeeper_accept') {
                        updateStatus(data.text); // Just updates the loading screen message!
                    } else if (data.type === 'result') {
                        // Save result and redirect
                        localStorage.setItem('currentTutorial', data.text);
                        window.location.href = '/tutorial.html';
                        return;
                    }
                } catch (e) {
                    console.error('Error parsing JSON:', e, line);
                }
            }
        }

    } catch (error) {
        console.error('Error:', error);
        statusText.textContent = 'Something went wrong. Please refresh and try again.';
        // Re-enable form if needed, or just let them refresh
    }
});