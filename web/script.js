// v2.1.0 - Google OAuth 2026-01-06

// === GLOBAL STATE (Nuclear Reliability) ===
let selectedPdfFile = null;
let currentPreviewImages = [];

// === GLOBAL FUNCTIONS ===
window.switchTab = function (targetMode) {
    console.log("Switching to tab:", targetMode);

    // 1. Update Buttons
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        const btnTarget = btn.getAttribute('data-target') || (btn.getAttribute('onclick') ? btn.getAttribute('onclick').match(/'([^']+)'/)[1] : null);
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
    const youtubeFeatures = document.getElementById('youtubeFeatures');
    const slideFeatures = document.getElementById('slideFeatures');
    const youtubeComparison = document.getElementById('youtubeComparison');

    if (targetMode === 'slideMode') {
        if (appSubtitle) appSubtitle.textContent = "上傳 NotebookLM 匯出的 PDF，AI 自動為您生成圖文並茂的 PowerPoint 簡報。";
        // 切換特色區塊
        if (youtubeFeatures) youtubeFeatures.classList.add('hidden');
        if (slideFeatures) slideFeatures.classList.remove('hidden');
        // 隱藏 NotebookLM 比較區塊 (只在 YouTube 模式顯示)
        if (youtubeComparison) youtubeComparison.classList.add('hidden');
    } else {
        if (appSubtitle) appSubtitle.textContent = "不僅僅是摘要。這是您的第二大腦作業系統，將雜亂的影音與原本內容轉化為可執行的結構化洞察。";
        // 切換特色區塊
        if (youtubeFeatures) youtubeFeatures.classList.remove('hidden');
        if (slideFeatures) slideFeatures.classList.add('hidden');
        // 顯示 NotebookLM 比較區塊
        if (youtubeComparison) youtubeComparison.classList.remove('hidden');
    }
};

// Editor State
let editorData = {
    analyses: [],
    cleanedImages: [],
    filename: ""
};
let currentEditIndex = 0;

window.generateSlides = async function (btnElement) {
    // 兼容性處理：如果未傳入按鈕，則嘗試獲取預設 ID (支援舊版調用)
    const btn = btnElement || document.getElementById('generateSlideBtn');
    const settingsModal = document.getElementById('settingsModal');
    const analysisLoading = document.getElementById('analysisLoading');
    const previewStep = document.getElementById('previewStep');
    const editorStep = document.getElementById('editorStep');

    if (!btn) return;

    // 立即給予視覺回饋 (防止重複點擊)
    const originalText = btn.innerHTML;
    btn.classList.add('btn-disabled'); // Visual Disable
    btn.style.opacity = '0.7';
    btn.style.cursor = 'wait';
    // 這裡不改變 innerHTML 以免破壞 icon 結構，用 CSS class 控制即可，或顯示 spinner

    // 安全檢查 - 使用 CSS class 而非 disabled 狀態
    const isVisuallyDisabled = btn.classList.contains('btn-disabled') && !btn.style.cursor === 'wait'; // Allow if we just set it? No.

    // Resume checks...

    // ...

    // UI 切換：進入 Loading (這會覆蓋整個畫面，所以按鈕狀態其實只顯示一瞬間，但這瞬間很重要)
    if (analysisLoading) {
        analysisLoading.classList.remove('hidden');
        // UX: 滾動到進度條區域，讓用戶看到處理進度
        setTimeout(() => {
            analysisLoading.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }
    if (previewStep) previewStep.classList.add('hidden');

    // 取得必要變數 (來自全域狀態)
    const file = selectedPdfFile;
    const geminiKey = localStorage.getItem('gemini_api_key') || '';
    const selectedIndices = currentPreviewImages
        .filter(item => item.selected)
        .map(item => item.index);

    if (!file) {
        alert('請先上傳 PDF 檔案');
        if (analysisLoading) analysisLoading.classList.add('hidden');
        if (previewStep) previewStep.classList.remove('hidden');
        btn.classList.remove('btn-disabled');
        btn.style.opacity = '';
        btn.style.cursor = '';
        return;
    }

    // API Key 檢查警告 (前端提示，後端有備援機制)
    if (!geminiKey) {
        const proceed = confirm('您尚未設定 Gemini API Key。\n\n如果伺服器有設定環境變數，將自動使用伺服器金鑰。\n否則分析將會失敗。\n\n是否繼續？\n（建議先點擊右上角「設定 API Key」按鈕設定您的金鑰）');
        if (!proceed) {
            if (analysisLoading) analysisLoading.classList.add('hidden');
            if (previewStep) previewStep.classList.remove('hidden');
            btn.classList.remove('btn-disabled');
            btn.style.opacity = '';
            btn.style.cursor = '';
            return;
        }
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('gemini_key', geminiKey);
    formData.append('selected_pages', JSON.stringify(selectedIndices));

    // Add Remove Icon Flag
    const removeIconCheckbox = document.getElementById('removeIconCheckbox');
    if (removeIconCheckbox && removeIconCheckbox.checked) {
        formData.append('remove_icon', 'true');
    }

    try {
        // Step 1: Call Analyze API (Streaming Response)
        const response = await fetch('/api/analyze-slides', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || '分析失敗');
        }

        // Reading the stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalResult = null;

        // Reset Progress Bar & Log
        const pBar = document.getElementById('analysisProgressBar');
        const analysisLog = document.getElementById('analysisLog');
        if (pBar) pBar.style.width = '0%';
        if (analysisLog) {
            analysisLog.innerHTML = '<div class="log-entry latest">> 系統初始化...</div>';
        }

        function appendAnalysisLog(msg, type = "info") {
            if (!analysisLog) return;
            const now = new Date().toLocaleTimeString('en-US', { hour12: false });

            // Remove 'latest' from previous
            const prev = analysisLog.querySelector('.latest');
            if (prev) prev.classList.remove('latest');

            const div = document.createElement('div');
            div.className = `log-entry latest ${type}`;
            div.innerText = `[${now}] ${msg}`;
            analysisLog.appendChild(div);
            analysisLog.scrollTop = analysisLog.scrollHeight;
        }

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep the last incomplete line

            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const data = JSON.parse(line);

                    // 1. Log Messages (Real-time Feedback)
                    if (data.type === 'log') {
                        appendAnalysisLog(data.data);
                        continue;
                    }

                    if (data.message) {
                        // 處理純訊息通知 (例如: 正在轉換 PDF...)
                        const pText = document.getElementById('progressText');
                        if (pText) pText.innerText = data.message;
                        appendAnalysisLog(data.message);
                    }

                    if (data.progress !== undefined) {
                        // Update UI
                        const total = data.total || 1; // Prevent div by zero
                        const percent = Math.round((data.progress / total) * 100);
                        const pText = document.getElementById('progressText');
                        const pPct = document.getElementById('progressPercent');

                        if (pBar) pBar.style.width = `${percent}%`;
                        if (pText && !data.message) pText.innerText = `正在分析第 ${data.progress} / ${total} 頁...`;
                        if (pPct) pPct.innerText = `${percent}%`;

                    } else if (data.analyses) {
                        finalResult = data;
                        appendAnalysisLog("分析完成，正在準備編輯器...", "success");
                    } else if (data.error) {
                        appendAnalysisLog(`錯誤: ${data.error}`, "error");
                        throw new Error(data.error);
                    }
                } catch (e) {
                    console.warn("Stream parse error:", e);
                }
            }
        }

        if (!finalResult) {
            throw new Error("伺服器未回傳分析結果");
        }

        const result = finalResult;

        // Initialize Editor State
        editorData.analyses = result.analyses;
        editorData.cleanedImages = result.cleaned_images;
        editorData.filename = file.name;
        currentEditIndex = 0;

        // Setup Editor UI
        window.updateEditorUI();

        // Switch to Editor Step
        if (analysisLoading) analysisLoading.classList.add('hidden');
        if (editorStep) {
            editorStep.classList.remove('hidden');
            // UX Improvement: Auto scroll to editor so user knows it's ready
            setTimeout(() => {
                editorStep.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }

    } catch (error) {
        console.error("Analysis Error:", error);
        alert(`錯誤: ${error.message}`);
        // 回到預覽
        if (analysisLoading) analysisLoading.classList.add('hidden');
        if (previewStep) previewStep.classList.remove('hidden');
    }
}

// Editor Navigation & Logic
window.updateEditorUI = function () {
    if (editorData.analyses.length === 0) return;

    const currentData = editorData.analyses[currentEditIndex];
    const currentImage = editorData.cleanedImages[currentEditIndex];

    // Update Counts
    document.getElementById('currentEditPage').textContent = currentEditIndex + 1;
    document.getElementById('totalEditPages').textContent = editorData.analyses.length;

    // Update Image
    const imgEl = document.getElementById('editorImage');
    if (imgEl) imgEl.src = currentImage;

    // Update Form Inputs
    const titleInput = document.getElementById('editTitle');
    const contentInput = document.getElementById('editContent');

    if (titleInput) titleInput.value = currentData.title || "";
    if (contentInput) {
        // Join content array into newline-separated string
        contentInput.value = (currentData.content || []).join('\n');
    }

    // Update Buttons State
    const prevBtn = document.getElementById('prevSlideBtn');
    const nextBtn = document.getElementById('nextSlideBtn');

    if (prevBtn) prevBtn.disabled = currentEditIndex === 0;
    if (nextBtn) nextBtn.disabled = currentEditIndex === editorData.analyses.length - 1;
}

window.saveCurrentSlideData = function () {
    // Save UI inputs back to data object
    const titleInput = document.getElementById('editTitle');
    const contentInput = document.getElementById('editContent');

    if (!titleInput || !contentInput) return;

    const newTitle = titleInput.value.trim();
    // Split by newline and filter empty items
    const newContent = contentInput.value.split('\n').map(line => line.trim()).filter(line => line.length > 0);

    // Update State
    editorData.analyses[currentEditIndex].title = newTitle;
    editorData.analyses[currentEditIndex].content = newContent;
}

window.prevEditSlide = function () {
    if (currentEditIndex > 0) {
        window.saveCurrentSlideData(); // Save before move
        currentEditIndex--;
        window.updateEditorUI();
    }
}

window.nextEditSlide = function () {
    if (currentEditIndex < editorData.analyses.length - 1) {
        window.saveCurrentSlideData(); // Save before move
        currentEditIndex++;
        window.updateEditorUI();
    }
}

window.backToPreview = function () {
    if (confirm("確定要返回嗎？這將會遺失目前的分析與編輯進度。")) {
        document.getElementById('editorStep').classList.add('hidden');
        document.getElementById('previewStep').classList.remove('hidden');
    }
}

// Final Generation Step
window.generatePresentations = async function () {
    window.saveCurrentSlideData(); // Save current page first

    const btn = document.getElementById('finalGenerateBtn');
    if (!btn) return;

    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '生成中... <i class="ri-loader-4-line ri-spin"></i>';

    try {
        // Fix Schema Mismatch: Backend expects snake_case for Pydantic
        const payload = {
            analyses: editorData.analyses,
            cleaned_images: editorData.cleanedImages,
            filename: editorData.filename
        };

        const response = await fetch('/api/generate-slides-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            let errorMsg = '生成失敗';
            const text = await response.text();
            try {
                const err = JSON.parse(text);
                errorMsg = err.error || err.detail || errorMsg;
                if (err.detail && typeof err.detail === 'object') {
                    errorMsg = `資料格式錯 (422): ${JSON.stringify(err.detail)}`;
                }
            } catch (e) {
                console.error("Server returned non-JSON:", text);
                // Extract title from HTML if possible (e.g. 504 Gateway Timeout)
                const match = text.match(/<title>(.*?)<\/title>/i);
                if (match) {
                    errorMsg = `伺服器錯誤: ${match[1]}`;
                } else {
                    errorMsg = `伺服器回傳無效內容 (${response.status})`;
                }
            }
            throw new Error(errorMsg);
        }

        // Download logic
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;

        // 使用原始 PDF 檔名，只替換副檔名為 .pptx
        let baseName = editorData.filename.replace(/\.(pdf|PDF)$/i, '');
        let fileName = baseName + '.pptx';
        a.download = fileName;

        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);

        alert('PPTX 生成成功！');

    } catch (error) {
        console.error("Final Gen Error:", error);
        alert(`生成錯誤: ${error.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

window.loadSettings = function () {
    const geminiKeyInput = document.getElementById('geminiKeyInput');
    const openaiKeyInput = document.getElementById('openaiKeyInput');

    const geminiKey = localStorage.getItem('gemini_api_key');
    const openaiKey = localStorage.getItem('openai_api_key');

    if (geminiKey && geminiKeyInput) geminiKeyInput.value = geminiKey;
    if (openaiKey && openaiKeyInput) openaiKeyInput.value = openaiKey;
};

window.openSettings = function () {
    console.log("Opening Settings Modal");
    const modal = document.getElementById('settingsModal');
    const geminiKeyInput = document.getElementById('geminiKeyInput');
    const openaiKeyInput = document.getElementById('openaiKeyInput');

    if (modal) {
        modal.classList.remove('hidden');

        // Load Settings
        const geminiKey = localStorage.getItem('gemini_api_key');
        const openaiKey = localStorage.getItem('openai_api_key');
        if (geminiKey && geminiKeyInput) geminiKeyInput.value = geminiKey;
        if (openaiKey && openaiKeyInput) openaiKeyInput.value = openaiKey;
    }
};

window.closeSettings = function () {
    const modal = document.getElementById('settingsModal');
    if (modal) modal.classList.add('hidden');
};

window.saveSettings = function () {
    const geminiKeyInput = document.getElementById('geminiKeyInput');
    const openaiKeyInput = document.getElementById('openaiKeyInput');
    const modal = document.getElementById('settingsModal');

    const geminiKey = geminiKeyInput ? geminiKeyInput.value.trim() : "";
    const openaiKey = openaiKeyInput ? openaiKeyInput.value.trim() : "";

    if (geminiKey) localStorage.setItem('gemini_api_key', geminiKey);
    else localStorage.removeItem('gemini_api_key');

    if (openaiKey) localStorage.setItem('openai_api_key', openaiKey);
    else localStorage.removeItem('openai_api_key');

    alert('設定已儲存！將優先使用您的 API Key 進行分析。');
    if (modal) modal.classList.add('hidden');
};

// === 全域 PDF 處理函式 (Global PDF Handlers) ===
window.triggerUpload = function () {
    const pdfInput = document.getElementById('pdfInput');
    if (pdfInput) pdfInput.click();
};

window.handleFileChange = function (input) {
    if (input.files && input.files.length > 0) {
        window.handleFileSelect(input.files[0]);
    }
};

window.handleDragOver = function (e) {
    e.preventDefault();
    const dropZone = document.getElementById('dropZone');
    if (dropZone) dropZone.classList.add('dragover');
};

window.handleDragLeave = function (e) {
    e.preventDefault();
    const dropZone = document.getElementById('dropZone');
    if (dropZone) dropZone.classList.remove('dragover');
};

window.handleDrop = function (e) {
    e.preventDefault();
    const dropZone = document.getElementById('dropZone');
    if (dropZone) dropZone.classList.remove('dragover');

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        window.handleFileSelect(e.dataTransfer.files[0]);
    }
};

window.handleFileSelect = async function (file) {
    if (file.type !== 'application/pdf') {
        alert('請上傳 PDF 檔案');
        return;
    }

    selectedPdfFile = file;

    // 更新檔案資訊 UI
    const fileInfo = document.getElementById('fileInfo');
    const fileNameDisplay = document.getElementById('fileName');
    const dropZone = document.getElementById('dropZone');
    const startPreviewBtn = document.getElementById('startPreviewBtn');

    if (fileNameDisplay) fileNameDisplay.textContent = file.name;
    if (fileInfo) fileInfo.classList.remove('hidden');
    if (dropZone) dropZone.classList.add('has-file');

    // 顯示「開始解析」按鈕，讓使用者手動觸發 (比自動觸發更穩健)
    if (startPreviewBtn) startPreviewBtn.classList.remove('hidden');
};

window.triggerPreview = async function (event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    if (selectedPdfFile) {
        await window.startPreview(selectedPdfFile);
    } else {
        alert("請先上傳檔案");
    }
}

window.removeFile = function (e) {
    if (e) e.stopPropagation();

    const pdfInput = document.getElementById('pdfInput');
    const fileInfo = document.getElementById('fileInfo');
    const dropZone = document.getElementById('dropZone');
    const startPreviewBtn = document.getElementById('startPreviewBtn');

    if (pdfInput) pdfInput.value = '';
    selectedPdfFile = null;
    currentPreviewImages = [];

    if (fileInfo) fileInfo.classList.add('hidden');
    if (dropZone) dropZone.classList.remove('has-file');
    if (startPreviewBtn) startPreviewBtn.classList.add('hidden');

    // 隱藏預覽
    const uploadStep = document.getElementById('uploadStep');
    const previewStep = document.getElementById('previewStep');
    if (uploadStep) uploadStep.classList.remove('hidden');
    if (previewStep) previewStep.classList.add('hidden');
};

window.startPreview = async function (file) {
    const previewLoading = document.getElementById('previewLoading');
    const uploadStep = document.getElementById('uploadStep');
    const previewStep = document.getElementById('previewStep');
    const startPreviewBtn = document.getElementById('startPreviewBtn');

    // 顯示載入中
    if (previewLoading) previewLoading.classList.remove('hidden');

    // 禁用按鈕防止重複點擊
    if (startPreviewBtn) {
        startPreviewBtn.classList.add('btn-disabled');
        startPreviewBtn.style.cursor = 'wait';
        startPreviewBtn.innerHTML = '<span>處理中...</span><i class="ri-loader-4-line ri-spin"></i>';
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/preview-pdf', {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error || '預覽生成失敗');
        }

        const data = await res.json();

        // 初始化狀態
        currentPreviewImages = data.images.map((url, index) => ({
            url: url,
            index: index,
            selected: true // 預設全選
        }));

        window.renderGrid();

        // 切換 UI
        if (uploadStep) uploadStep.classList.add('hidden');
        if (previewStep) previewStep.classList.remove('hidden');

        // 啟用生成按鈕
        const generateSlideBtn = document.getElementById('generateSlideBtn');
        if (generateSlideBtn) {
            generateSlideBtn.classList.remove('btn-disabled');
        }

    } catch (e) {
        console.error(e);
        alert(`預覽生成失敗: ${e.message || '請確認 PDF 格式'}`);
        // 重置
        selectedPdfFile = null;
    } finally {
        if (previewLoading) previewLoading.classList.add('hidden');

        // 恢復「下一步」按鈕狀態 (無論成功失敗都恢復，因為如果成功它只是隱藏了)
        const startPreviewBtn = document.getElementById('startPreviewBtn');
        if (startPreviewBtn) {
            startPreviewBtn.classList.remove('btn-disabled');
            startPreviewBtn.style.cursor = 'pointer';
            startPreviewBtn.innerHTML = '<span>下一步：解析頁面</span><i class="ri-arrow-right-line"></i>';
        }

        // UX Improvement: Auto scroll to preview step
        if (previewStep && !previewStep.classList.contains('hidden')) {
            setTimeout(() => {
                previewStep.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
    }
};

// === GRID 與選擇邏輯 ===

window.renderGrid = function () {
    const pageGrid = document.getElementById('pageGrid');
    const selectedCountSpan = document.getElementById('selectedCount');
    const totalCountSpan = document.getElementById('totalCount');

    // 更新所有生成按鈕
    const resultBtn = document.getElementById('generateSlideBtnResult');
    const previewBtn = document.getElementById('generateSlideBtn');
    const generateButtons = [previewBtn, resultBtn].filter(b => b !== null);

    if (!pageGrid) return;
    pageGrid.innerHTML = '';

    let selectedCount = 0;

    currentPreviewImages.forEach((item) => {
        if (item.selected) selectedCount++;

        const div = document.createElement('div');
        div.className = `grid-item ${item.selected ? 'selected' : ''}`;
        div.onclick = () => window.toggleSelection(item.index);

        div.innerHTML = `
        <img src="${item.url}" loading="lazy">
        <div class="checkbox-overlay">
            <i class="ri-check-line"></i>
        </div>
        <span class="page-number">${item.index + 1}</span>
    `;

        pageGrid.appendChild(div);
    });

    // 更新計數
    if (selectedCountSpan) selectedCountSpan.textContent = selectedCount;
    if (totalCountSpan) totalCountSpan.textContent = currentPreviewImages.length;

    // 更新生成按鈕狀態 (使用 CSS class 而非 disabled 屬性，確保 mousedown 永遠能觸發)
    generateButtons.forEach(btn => {
        // 移除 disabled 屬性，改用 CSS class
        btn.removeAttribute('disabled');
        if (selectedCount === 0) {
            btn.classList.add('btn-disabled');
        } else {
            btn.classList.remove('btn-disabled');
        }
        const span = btn.querySelector('span');
        if (span) span.textContent = selectedCount === 0 ? '請選擇頁面' : `生成簡報 (${selectedCount} 頁)`;
    });
};

window.toggleSelection = function (index) {
    if (currentPreviewImages[index]) {
        currentPreviewImages[index].selected = !currentPreviewImages[index].selected;
        window.renderGrid();
    }
};

window.selectAll = function () {
    currentPreviewImages.forEach(i => i.selected = true);
    window.renderGrid();
};

window.deselectAll = function () {
    currentPreviewImages.forEach(i => i.selected = false);
    window.renderGrid();
};

window.cancelPreview = function () {
    selectedPdfFile = null;
    const uploadStep = document.getElementById('uploadStep');
    const previewStep = document.getElementById('previewStep');
    const pdfInput = document.getElementById('pdfInput');

    if (uploadStep) uploadStep.classList.remove('hidden');
    if (previewStep) previewStep.classList.add('hidden');
    if (pdfInput) pdfInput.value = '';
};

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

    // [Fix] Re-attach Event Listeners for Settings Button
    // [Fix] Re-attach Event Listeners for Settings Button
    // Nuclear Option: Use both addEventListener and onclick property to ensure binding
    console.log("Binding UI Events (v2.10.7)...");

    if (settingsBtn) {
        const handler = () => { console.log("Settings Clicked"); if (window.openSettings) window.openSettings(); };
        settingsBtn.onclick = handler;
        settingsBtn.addEventListener('click', handler);
    }

    if (closeSettingsBtn) {
        const handler = () => { if (window.closeSettings) window.closeSettings(); };
        closeSettingsBtn.onclick = handler;
    }

    if (saveSettingsBtn) {
        const handler = () => { if (window.saveSettings) window.saveSettings(); };
        saveSettingsBtn.onclick = handler;
    }

    if (submitBtn) {
        console.log("Binding Submit Button...");
        const handler = () => { console.log("Submit Clicked"); startAnalysis(); };
        submitBtn.onclick = handler;
        submitBtn.addEventListener('click', handler);
    }

    // [Fix] Re-attach Event Listeners for Tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        const handler = (e) => {
            console.log("Tab Clicked:", btn.getAttribute('data-target'));
            e.preventDefault();
            const target = btn.getAttribute('data-target');
            if (target && window.switchTab) {
                window.switchTab(target);
            } else {
                console.error("switchTab func or target missing");
            }
        };
        btn.onclick = handler;
        btn.addEventListener('click', handler);
    });

    // Load API Keys from local storage
    try {
        if (typeof window.loadSettings === 'function') {
            window.loadSettings();
        } else {
            console.error("window.loadSettings is not defined");
        }
    } catch (e) {
        console.error("Failed to load settings:", e);
    }

    // Check authentication on page load
    try {
        if (typeof checkAuth === 'function') {
            checkAuth();
        } else {
            // Fallback if checkAuth missing (e.g. syntax error prevented definition)
            console.error("checkAuth not defined, forcing UI visible");
            if (inputSection) inputSection.classList.remove('hidden');
        }
    } catch (e) {
        console.error("Error invoking checkAuth:", e);
        if (inputSection) inputSection.classList.remove('hidden');
    }

    async function checkAuth() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000); // 3s timeout
            const res = await fetch('/api/check-auth', { signal: controller.signal });
            clearTimeout(timeoutId);
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

    // Use Global openSettings/closeSettings/saveSettings
    // Settings Listeners removed to prevent race conditions

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

        // [v6.2.2] Check API Keys
        const geminiKey = localStorage.getItem('gemini_api_key') || "";
        const openaiKey = localStorage.getItem('openai_api_key') || "";

        if (!geminiKey && !openaiKey) {
            const proceed = confirm('您尚未設定任何 API Key (Gemini/OpenAI)。\n\n如果伺服器有設定環境變數，將自動使用伺服器金鑰。\n否則分析將會失敗。\n\n是否繼續？\n（建議先點擊右上角「設定 API Key」按鈕設定您的金鑰）');
            if (!proceed) {
                return;
            }
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
        // Keys already retrieved above (geminiKey, openaiKey)

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
    const modeContents = document.querySelectorAll('.mode-content');

    // Slide Gen Elements
    const dropZone = document.getElementById('dropZone');
    const pdfInput = document.getElementById('pdfInput');
    const fileInfo = document.getElementById('fileInfo');
    const fileNameDisplay = document.getElementById('fileName');
    const removeFileBtn = document.getElementById('removeFileBtn');
    const generateSlideBtn = document.getElementById('generateSlideBtn');

    // Use Global selectedPdfFile (defined at top)
    // let selectedPdfFile = null;

    // Inner switchTab removed (Moved to Global)

    // Keep existing listeners as backup, but inline onclick in HTML will take precedence
    // Keep existing listeners as backup
    // tabBtns is already defined above
    // Keep existing listeners as backup
    // (Redundant loop removed to prevent double-firing)

    // File Upload Handling - REMOVED (Moved to Global)
    // if (dropZone) { ... }

    // State for Preview
    // Use Global currentPreviewImages
    // let currentPreviewImages = [];

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


    // (Moved to Global Scope above)



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



    // Inner generateSlides removed (Moved to Global)

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


    // [Fix] Start Preview Button uses onmousedown in HTML to prevent double-click
    // No JS listener needed here.

});
