// v2.0.1 - Password fix 2026-01-06
document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('urlInput');
    const submitBtn = document.getElementById('submitBtn');
    const statusSection = document.getElementById('statusSection');
    const terminalOutput = document.getElementById('terminalOutput');
    const resultSection = document.getElementById('resultSection');
    const markdownOutput = document.getElementById('markdownOutput');
    const copyBtn = document.getElementById('copyBtn');
    const downloadBtn = document.getElementById('downloadBtn');

    // Password modal elements
    const passwordModal = document.getElementById('passwordModal');
    const passwordInput = document.getElementById('passwordInput');
    const passwordSubmitBtn = document.getElementById('passwordSubmitBtn');
    const passwordError = document.getElementById('passwordError');

    let currentEventSource = null;
    let currentResult = "";
    let currentFilename = "summary.md";
    let accessPassword = localStorage.getItem('accessPassword') || "";

    // Check if password is required on page load
    checkAuth();

    async function checkAuth() {
        try {
            const res = await fetch('/api/check-auth');
            const data = await res.json();

            if (data.password_required && !accessPassword) {
                passwordModal.classList.remove('hidden');
            } else if (data.password_required && accessPassword) {
                // Verify stored password still works
                const verifyRes = await fetch(`/api/verify-password?password=${encodeURIComponent(accessPassword)}`);
                const verifyData = await verifyRes.json();
                if (!verifyData.success) {
                    localStorage.removeItem('accessPassword');
                    accessPassword = "";
                    passwordModal.classList.remove('hidden');
                }
            }
        } catch (e) {
            console.log('Auth check failed, continuing without auth');
        }
    }

    // Password submit
    passwordSubmitBtn.addEventListener('click', verifyPassword);
    passwordInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') verifyPassword();
    });

    async function verifyPassword() {
        const password = passwordInput.value.trim();
        if (!password) return;

        try {
            const res = await fetch(`/api/verify-password?password=${encodeURIComponent(password)}`);
            const data = await res.json();

            if (data.success) {
                accessPassword = password;
                localStorage.setItem('accessPassword', password);
                passwordModal.classList.add('hidden');
                passwordError.classList.add('hidden');
            } else {
                passwordError.classList.remove('hidden');
            }
        } catch (e) {
            passwordError.textContent = '驗證時發生錯誤';
            passwordError.classList.remove('hidden');
        }
    }

    submitBtn.addEventListener('click', startAnalysis);

    // Allow Enter key to trigger
    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') startAnalysis();
    });

    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(currentResult).then(() => {
            const originalText = copyBtn.innerHTML;
            copyBtn.innerHTML = '<i class="ri-check-line"></i> 已複製！';
            setTimeout(() => {
                copyBtn.innerHTML = originalText;
            }, 2000);
        });
    });

    downloadBtn.addEventListener('click', () => {
        const blob = new Blob([currentResult], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = currentFilename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    function startAnalysis() {
        const url = urlInput.value.trim();

        if (!url) {
            alert("請輸入有效的 Youtube 網址");
            return;
        }

        // Reset UI
        statusSection.classList.remove('hidden');
        resultSection.classList.add('hidden');
        terminalOutput.innerHTML = '';
        markdownOutput.innerHTML = '';
        currentResult = "";

        // Disable button
        submitBtn.disabled = true;
        submitBtn.innerHTML = 'AI 分析中 <i class="ri-loader-4-line ri-spin"></i>';

        // Close previous connection if any
        if (currentEventSource) {
            currentEventSource.close();
        }

        // Connect to SSE with password
        const sseUrl = `/api/summarize?url=${encodeURIComponent(url)}&password=${encodeURIComponent(accessPassword)}`;
        currentEventSource = new EventSource(sseUrl);

        currentEventSource.onmessage = function (event) {
            try {
                const payload = JSON.parse(event.data);
                handleEvent(payload);
            } catch (e) {
                console.error("Error parsing event data:", e);
                appendLog("解析伺服器回應時發生錯誤", "error");
            }
        };

        currentEventSource.onerror = function (err) {
            console.error("EventSource failed:", err);
            appendLog("連線中斷或發生錯誤，請檢查伺服器狀態。", "error");
            stopProcessing();
        };
    }

    function handleEvent(payload) {
        switch (payload.type) {
            case 'log':
                appendLog(payload.data);
                break;
            case 'result':
                currentResult = payload.data;
                currentFilename = payload.filename || "summary.md";
                renderResult(payload.data);
                break;
            case 'done':
                appendLog("分析流程成功完成。", "latest");
                stopProcessing();
                break;
            case 'error':
                appendLog(payload.message, "error");
                stopProcessing();
                break;
        }
    }

    function appendLog(message, type = "") {
        const div = document.createElement('div');
        div.className = `log-entry ${type}`;
        div.textContent = `> ${message}`;

        // Remove 'latest' class from previous logs
        const previousLatest = terminalOutput.querySelector('.latest');
        if (previousLatest) previousLatest.classList.remove('latest');

        if (!type) div.classList.add('latest');

        terminalOutput.appendChild(div);

        // Auto scroll
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }

    function renderResult(markdown) {
        resultSection.classList.remove('hidden');
        // Use marked.js to render
        markdownOutput.innerHTML = marked.parse(markdown);

        // Scroll to result
        resultSection.scrollIntoView({ behavior: 'smooth' });
    }

    function stopProcessing() {
        if (currentEventSource) {
            currentEventSource.close();
            currentEventSource = null;
        }
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span>開始分析</span><i class="ri-arrow-right-line"></i>';
    }
});
