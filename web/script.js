// v2.1.0 - Google OAuth 2026-01-06
document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('urlInput');
    const submitBtn = document.getElementById('submitBtn');
    const statusSection = document.getElementById('statusSection');
    const terminalOutput = document.getElementById('terminalOutput');
    const resultSection = document.getElementById('resultSection');
    const markdownOutput = document.getElementById('markdownOutput');
    const copyBtn = document.getElementById('copyBtn');
    const downloadBtn = document.getElementById('downloadBtn');

    // OAuth elements
    const loginModal = document.getElementById('loginModal');
    const userInfo = document.getElementById('userInfo'); // was userBar
    const userAvatar = document.getElementById('userAvatar');
    const userName = document.getElementById('userName');

    let currentEventSource = null;
    let currentResult = "";
    let currentFilename = "summary.md";
    let retryCount = 0;

    // Sections
    const landingSection = document.getElementById('landingSection');
    const inputSection = document.getElementById('inputSection');

    // Settings Modal Elements
    const settingsBtn = document.getElementById('settingsBtn');
    const settingsModal = document.getElementById('settingsModal');
    const closeSettingsBtn = document.getElementById('closeSettingsBtn');
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');
    const geminiKeyInput = document.getElementById('geminiKeyInput');
    const openaiKeyInput = document.getElementById('openaiKeyInput');

    // Load API Keys from local storage
    loadSettings();

    // Check authentication on page load
    checkAuth();

    async function checkAuth() {
        try {
            const res = await fetch('/api/check-auth');
            const data = await res.json();

            if (data.auth_required && !data.logged_in) {
                // Public Access Mode (BYOK)
                // Always show accessible UI
                landingSection.classList.add('hidden');
                inputSection.classList.remove('hidden');
                loginModal.classList.add('hidden');

                // Optionally show a toast or message? No, keep it clean.
            } else {
                // Logged in (or Local mode) -> Show Feature
                landingSection.classList.add('hidden');
                inputSection.classList.remove('hidden');
                loginModal.classList.add('hidden');
                loadUserInfo();
            }
        } catch (e) {
            console.log('Auth check failed, continuing');
            // Fallback: Show input in case of error (e.g. local dev offline)
            landingSection.classList.add('hidden');
            inputSection.classList.remove('hidden');
        }
    }

    async function loadUserInfo() {
        try {
            const res = await fetch('/api/user');
            const user = await res.json();

            if (user.email && user.email !== 'local') {
                userAvatar.src = user.picture || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(user.name);
                userName.textContent = user.name || user.email;
                if (userInfo) userInfo.classList.remove('hidden');
            }
        } catch (e) {
            console.log('Failed to load user info');
        }
    }

    submitBtn.addEventListener('click', startAnalysis);
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

    // Settings Modal Listeners
    if (settingsBtn) {
        settingsBtn.addEventListener('click', () => {
            loadSettings(); // Reload just in case
            settingsModal.classList.remove('hidden');
        });
    }

    if (closeSettingsBtn) {
        closeSettingsBtn.addEventListener('click', () => {
            settingsModal.classList.add('hidden');
        });
    }

    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', saveSettings);
    }

    // Close modal on outside click
    window.addEventListener('click', (e) => {
        if (e.target === settingsModal) {
            settingsModal.classList.add('hidden');
        }
    });

    function saveSettings() {
        const geminiKey = geminiKeyInput.value.trim();
        const openaiKey = openaiKeyInput.value.trim();

        if (geminiKey) localStorage.setItem('gemini_api_key', geminiKey);
        else localStorage.removeItem('gemini_api_key');

        if (openaiKey) localStorage.setItem('openai_api_key', openaiKey);
        else localStorage.removeItem('openai_api_key');

        alert('設定已儲存！將優先使用您的 API Key 進行分析。');
        settingsModal.classList.add('hidden');
    }

    function loadSettings() {
        const geminiKey = localStorage.getItem('gemini_api_key');
        const openaiKey = localStorage.getItem('openai_api_key');

        if (geminiKey && geminiKeyInput) geminiKeyInput.value = geminiKey;
        if (openaiKey && openaiKeyInput) openaiKeyInput.value = openaiKey;
    }

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

    function startAnalysis(isRetry = false) {
        if (!isRetry) retryCount = 0;
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

        // Connect to SSE (session-based auth, no password needed)
        // Connect to SSE (session-based auth, no password needed)
        // Inject API Keys from Local Storage
        const geminiKey = localStorage.getItem('gemini_api_key') || "";
        const openaiKey = localStorage.getItem('openai_api_key') || "";

        const sseUrl = `/api/summarize?url=${encodeURIComponent(url)}&gemini_key=${encodeURIComponent(geminiKey)}&openai_key=${encodeURIComponent(openaiKey)}`;
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
            let state = currentEventSource ? currentEventSource.readyState : "Unknown";

            // Auto-retry logic for Cold Starts (State 0 usually means connection refused/timeout)
            if (state === 0 && retryCount < 3) {
                appendLog(`伺服器喚醒中 (嘗試 ${retryCount + 1}/3)...`, "warn");
                retryCount++;
                currentEventSource.close();
                setTimeout(() => {
                    startAnalysis(true); // Retry flag
                }, 3000);
            } else {
                appendLog(`連線中斷或發生錯誤 (State: ${state})。若為 Render 免費版，請稍候重試。`, "error");
                stopProcessing();
            }
        };
    }

    function handleEvent(payload) {
        // Reset retry count on successful message
        retryCount = 0;
        switch (payload.type) {
            case 'log':
                appendLog(payload.data);
                break;
            case 'result':
                currentResult = payload.data;
                currentFilename = payload.filename || "summary.md";
                renderResult(payload.data);
                break;
            case 'ping':
                // Keeping connection alive, no action needed
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

        const previousLatest = terminalOutput.querySelector('.latest');
        if (previousLatest) previousLatest.classList.remove('latest');

        if (!type) div.classList.add('latest');

        terminalOutput.appendChild(div);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }

    function renderResult(markdown) {
        resultSection.classList.remove('hidden');
        markdownOutput.innerHTML = marked.parse(markdown);
        resultSection.scrollIntoView({ behavior: 'smooth' });
    }

    function stopProcessing() {
        if (currentEventSource) {
            currentEventSource.close();
            currentEventSource = null;
        }
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span>開始分析</span><i class="ri-flashlight-line"></i>';
    }

    // === Mode Switching & Slide Generator logic ===
    const tabBtns = document.querySelectorAll('.tab-btn');
    const modeContents = document.querySelectorAll('.mode-content');

    // Slide Gen Elements
    const dropZone = document.getElementById('dropZone');
    const pdfInput = document.getElementById('pdfInput');
    const fileInfo = document.getElementById('fileInfo');
    const fileNameDisplay = document.getElementById('fileName');
    const removeFileBtn = document.getElementById('removeFileBtn');
    const generateSlideBtn = document.getElementById('generateSlideBtn');

    // 用於存儲拖曳上傳或點擊上傳的檔案
    let selectedPdfFile = null;

    // === Global Tab Switching (Nuclear Option) ===
    window.switchTab = function (targetMode) {
        console.log("Switching to tab:", targetMode);

        // 1. Update Buttons
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            const btnTarget = btn.getAttribute('data-target') || btn.getAttribute('onclick').match(/'([^']+)'/)[1];
            if (btnTarget === targetMode) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // 2. Update Content
        const modeContents = document.querySelectorAll('.mode-content');
        modeContents.forEach(content => {
            if (content.id === targetMode) {
                content.classList.add('active');
            } else {
                content.classList.remove('active');
            }
        });

        // 3. Update Text/Features
        const appSubtitle = document.getElementById('appSubtitle');
        if (appSubtitle) {
            if (targetMode === 'slideMode') {
                appSubtitle.textContent = "上傳 NotebookLM 匯出的 PDF，AI 自動為您生成圖文並茂的 PowerPoint 簡報。";
            } else {
                appSubtitle.textContent = "不僅僅是摘要。這是您的第二大腦作業系統，將雜亂的影音與原本內容轉化為可執行的結構化洞察。";
            }
        }
    };

    // Keep existing listeners as backup, but inline onclick in HTML will take precedence
    // Keep existing listeners as backup
    // tabBtns is already defined above
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-target');
            if (target) window.switchTab(target);
        });
    });

    // File Upload Handling
    if (dropZone) {
        dropZone.addEventListener('click', (e) => {
            // 如果已選擇檔案，或點擊的是移除按鈕，則不再觸發檔案選擇
            if (dropZone.classList.contains('has-file')) return;
            if (e.target !== removeFileBtn && !removeFileBtn.contains(e.target)) {
                pdfInput.click();
            }
        });

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                handleFileSelect(e.dataTransfer.files[0]);
            }
        });

        pdfInput.addEventListener('change', () => {
            if (pdfInput.files.length) {
                handleFileSelect(pdfInput.files[0]);
            }
        });
    }

    // State for Preview
    let currentPreviewImages = [];

    // DOM Elements for Preview
    const uploadStep = document.getElementById('uploadStep');
    const previewStep = document.getElementById('previewStep');
    const pageGrid = document.getElementById('pageGrid');
    const previewLoading = document.getElementById('previewLoading');
    const selectedCountSpan = document.getElementById('selectedCount');
    const totalCountSpan = document.getElementById('totalCount');
    const selectAllBtn = document.getElementById('selectAllBtn');
    const deselectAllBtn = document.getElementById('deselectAllBtn');
    const cancelPreviewBtn = document.getElementById('cancelPreviewBtn');


    async function handleFileSelect(file) {
        if (file.type !== 'application/pdf') {
            alert('請上傳 PDF 檔案');
            return;
        }

        selectedPdfFile = file;

        // Start Preview Flow
        await startPreview(file);
    }

    async function startPreview(file) {
        // Show Loading
        previewLoading.classList.remove('hidden');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('/api/preview-pdf', {
                method: 'POST',
                body: formData
            });

            if (!res.ok) throw new Error('預覽生成失敗');

            const data = await res.json();

            // Init State
            currentPreviewImages = data.images.map((url, index) => ({
                url: url,
                index: index,
                selected: true // Default select all
            }));

            renderGrid();

            // Switch UI
            uploadStep.classList.add('hidden');
            previewStep.classList.remove('hidden');

            // Enable Generate Button
            if (generateSlideBtn) generateSlideBtn.disabled = false;

        } catch (e) {
            console.error(e);
            alert('無法產生預覽，請確認 PDF 格式');
            // Reset
            selectedPdfFile = null;
        } finally {
            previewLoading.classList.add('hidden');
        }
    }

    function renderGrid() {
        if (!pageGrid) return;
        pageGrid.innerHTML = '';

        let selectedCount = 0;

        currentPreviewImages.forEach((item) => {
            if (item.selected) selectedCount++;

            const div = document.createElement('div');
            div.className = `grid-item ${item.selected ? 'selected' : ''}`;
            div.onclick = () => toggleSelection(item.index);

            div.innerHTML = `
                <img src="${item.url}" loading="lazy">
                <div class="checkbox-overlay">
                    <i class="ri-check-line"></i>
                </div>
                <span class="page-number">${item.index + 1}</span>
            `;

            pageGrid.appendChild(div);
        });

        // Update Counts
        if (selectedCountSpan) selectedCountSpan.textContent = selectedCount;
        if (totalCountSpan) totalCountSpan.textContent = currentPreviewImages.length;

        // Update Generate Button State
        if (generateSlideBtn) {
            generateSlideBtn.disabled = selectedCount === 0;
            const span = generateSlideBtn.querySelector('span');
            if (span) span.textContent = selectedCount === 0 ? '請選擇頁面' : `生成簡報 (${selectedCount} 頁)`;
        }
    }

    function toggleSelection(index) {
        if (currentPreviewImages[index]) {
            currentPreviewImages[index].selected = !currentPreviewImages[index].selected;
            renderGrid();
        }
    }

    // Preview Actions
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', () => {
            currentPreviewImages.forEach(i => i.selected = true);
            renderGrid();
        });
    }

    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', () => {
            currentPreviewImages.forEach(i => i.selected = false);
            renderGrid();
        });
    }

    if (cancelPreviewBtn) {
        cancelPreviewBtn.addEventListener('click', () => {
            selectedPdfFile = null;
            uploadStep.classList.remove('hidden');
            previewStep.classList.add('hidden');
            if (pdfInput) pdfInput.value = '';
        });
    }


    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Stop bubbling to dropZone
            pdfInput.value = '';
            selectedPdfFile = null; // 清空存儲的檔案
            fileInfo.classList.add('hidden');
            generateSlideBtn.disabled = true;
            dropZone.classList.remove('has-file');
        });
    }

    // === Global Generation Function (Bulletproof for click handling) ===
    // === Global Generation Function (Bulletproof for click handling) ===
    window.generateSlides = async function () {
        const btn = document.getElementById('generateSlideBtn');
        if (!btn) return;

        console.log(">>> Generate Slide Button Clicked (Global Function) <<<");
        console.log("Button Disabled State:", btn.disabled);
        console.log("Selected PDF:", selectedPdfFile);

        // Immediate Feedback to prove click reception
        const originalText = btn.innerHTML;
        // Don't change text yet if disabled, just log

        // Safety Check
        if (btn.disabled) {
            console.warn("Click ignored: Button is disabled");
            // FORCE ENABLE if it was disabled by mistake? 
            // This is a "Heal" strategy.
            // If user clicks and it's disabled, maybe we should check if we can enable it?
            // Re-run validation:
            if (selectedPdfFile && currentPreviewImages.some(i => i.selected)) {
                console.warn("Button was disabled but valid state detected. Re-enabling and proceeding...");
                btn.disabled = false;
                // Continues...
            } else {
                return;
            }
        }

        const file = selectedPdfFile;
        if (!file) {
            console.error("No file selected");
            alert("未偵測到檔案 (Internal State Missing)");
            return;
        }

        const geminiKey = localStorage.getItem('gemini_api_key');
        if (!geminiKey) {
            console.log("Missing API Key");
            alert('請先在設定中輸入 Google Gemini API Key (BYOK)');
            settingsModal.classList.remove('hidden');
            return;
        }

        // Get Selected Indices
        const selectedIndices = currentPreviewImages
            .filter(i => i.selected)
            .map(i => i.index);

        if (selectedIndices.length === 0) {
            alert("請至少選擇一頁");
            return;
        }

        console.log(`Generating slides for ${selectedIndices.length} pages...`);

        // UI Loading State
        btn.disabled = true;
        const originalBtnText = btn.innerHTML;
        btn.innerHTML = '生成中... <i class="ri-loader-4-line ri-spin"></i>';

        const formData = new FormData();
        formData.append('file', file);
        formData.append('gemini_key', geminiKey);
        formData.append('selected_pages', JSON.stringify(selectedIndices));

        try {
            // Use local timeout logic just in case connection hangs
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 900000); // 15 min timeout (matching Cloud Run)

            const response = await fetch('/api/generate-slides', {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || '生成失敗');
            }

            console.log("Generation success, downloading...");

            // Handle file download
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;

            // Get filename from header or default
            const contentDisposition = response.headers.get('Content-Disposition');
            let fileName = 'slides.pptx';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
                if (filenameMatch.length === 2) fileName = filenameMatch[1];
            }

            a.download = fileName;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(downloadUrl);

            alert('簡報生成成功！下載即將開始。');

        } catch (error) {
            console.error("Slide Gen Error:", error);
            if (error.name === 'AbortError') {
                alert('請求超時 (15分鐘)，請嘗試減少頁數再試。');
            } else {
                alert(`錯誤: ${error.message}`);
            }
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalBtnText;
            }
        }
    };

    // if (generateSlideBtn) {
    //    generateSlideBtn.disabled = true; // Initial state
    // }

    // === Demo Terminal Animation ===
    const demoBody = document.getElementById('demoTerminalBody');
    const typewriter = document.getElementById('typewriter');
    const replayBtn = document.getElementById('replayDemoBtn');

    if (demoBody && typewriter) {
        // Sequence of events for the demo
        const demoSequence = [
            { text: "youtu-brain analyze https://youtu.be/demo123", type: "command" },
            { text: "🔌 連線建立中...", type: "info", delay: 500 },
            { text: "🚀 系統核心已啟動", type: "info", delay: 800 },
            { text: "🔒 安全模組: ✅ 已啟用 (Google OAuth)", type: "info", delay: 1000 },
            { text: "處理影片 ID: demo123 (Google DeepMind Dev Day)", type: "info", delay: 1500 },
            { text: "嘗試使用 Gemini 直接分析影片...", type: "highlight", delay: 2000 },
            { text: "正在使用 Gemini 3 Flash Preview (最新預覽版)...", type: "system", delay: 2500 },
            { text: "影片 URL: https://www.youtube.com/watch?v=demo123", type: "info", delay: 2600 },
            { text: "Gemini 分析中 (Understanding Visuals & Audio)...", type: "warn", delay: 3500 },
            { text: "> [DeepMind]: Multimodal understanding achieved.", type: "info", delay: 5000 },
            { text: "> [DeepMind]: Context window usage: 45K tokens.", type: "info", delay: 5500 },
            { text: "生成結構化筆記 (Markdown)...", type: "highlight", delay: 7000 },
            { text: "分析流程成功完成。", type: "success", delay: 8500 }
        ];

        let isAnimating = false;

        async function runDemo() {
            if (isAnimating) return;
            isAnimating = true;

            // Clear previous content except cursor line
            const existingLogs = demoBody.querySelectorAll('.log-line');
            existingLogs.forEach(el => el.remove());
            replayBtn.classList.add('hidden');
            typewriter.textContent = "";

            // Step 1: Type the command
            await typeCommand(demoSequence[0].text);

            // Step 2: Process logs
            for (let i = 1; i < demoSequence.length; i++) {
                const item = demoSequence[i];
                await new Promise(r => setTimeout(r, item.delay - (i > 1 ? demoSequence[i - 1].delay : 0)));
                appendDemoLog(item.text, item.type);
                // Scroll to bottom
                demoBody.scrollTop = demoBody.scrollHeight;
            }

            isAnimating = false;
            replayBtn.classList.remove('hidden');
        }

        function typeCommand(text) {
            return new Promise(resolve => {
                let charIndex = 0;
                typewriter.textContent = "";
                const interval = setInterval(() => {
                    if (charIndex < text.length) {
                        typewriter.textContent += text.charAt(charIndex);
                        charIndex++;
                    } else {
                        clearInterval(interval);
                        setTimeout(() => {
                            // "Enter" key effect
                            const cmdLine = document.createElement('div');
                            cmdLine.className = 'cursor-line';
                            cmdLine.innerHTML = `<span class="prompt">$</span> <span class="command-text">${text}</span>`;
                            demoBody.insertBefore(cmdLine, demoBody.firstChild);
                            typewriter.textContent = ""; // Clear for next input implication
                            resolve();
                        }, 500);
                    }
                }, 50); // Typing speed
            });
        }

        function appendDemoLog(message, type) {
            const div = document.createElement('div');
            div.className = `log-entry log-line ${type}`;
            div.textContent = `> ${message}`;
            // Insert before the cursor line (which is always last)
            const cursorLine = demoBody.querySelector('.cursor-line');
            demoBody.insertBefore(div, cursorLine);
        }

        // Auto run on load
        setTimeout(runDemo, 1000);

        // Replay handler
        replayBtn.addEventListener('click', runDemo);
    }

});
