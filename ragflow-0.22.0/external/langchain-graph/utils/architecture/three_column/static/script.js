// 主题配色数据 (Static, can be in external JS)
const themeColors = {
    blue: {
        layerBg: "#f1f5f9",
        border: "#94a3b8",
        title: "#475569",
        serviceBg: "linear-gradient(135deg, #cbd5e1 0%, #94a3b8 100%)",
        serviceBorder: "#64748b",
        serviceText: "#334155",
        serviceShadow: "0 2px 8px rgba(148, 163, 184, 0.2)"
    },
    green: {
        layerBg: "#f0fdf4",
        border: "#86bc86",
        title: "#4a5a4a",
        serviceBg: "linear-gradient(135deg, #a7d4a7 0%, #86bc86 100%)",
        serviceBorder: "#6b9b6b",
        serviceText: "#2d4a2d",
        serviceShadow: "0 2px 8px rgba(134, 188, 134, 0.2)"
    },
    purple: {
        layerBg: "#f4f1ff",
        border: "#b4a5d6",
        title: "#5a4d6b",
        serviceBg: "linear-gradient(135deg, #c7b8e0 0%, #b4a5d6 100%)",
        serviceBorder: "#9a89b8",
        serviceText: "#4a3d5a",
        serviceShadow: "0 2px 8px rgba(180, 165, 214, 0.2)"
    },
    yellow: {
        layerBg: "#fefce8",
        border: "#d4c590",
        title: "#6b5a2d",
        serviceBg: "linear-gradient(135deg, #e8d5a3 0%, #d4c590 100%)",
        serviceBorder: "#b8a676",
        serviceText: "#5a4d2d",
        serviceShadow: "0 2px 8px rgba(212, 197, 144, 0.2)"
    },
    red: {
        layerBg: "#fef2f2",
        border: "#f87171",
        title: "#7f1d1d",
        serviceBg: "linear-gradient(135deg, #fca5a5 0%, #f87171 100%)",
        serviceBorder: "#dc2626",
        serviceText: "#7f1d1d",
        serviceShadow: "0 2px 8px rgba(248, 113, 113, 0.2)"
    },
    cyan: {
        layerBg: "#ecfeff",
        border: "#67e8f9",
        title: "#164e63",
        serviceBg: "linear-gradient(135deg, #a5f3fc 0%, #67e8f9 100%)",
        serviceBorder: "#0891b2",
        serviceText: "#164e63",
        serviceShadow: "0 2px 8px rgba(103, 232, 249, 0.2)"
    },
    orange: {
        layerBg: "#fef3c7",
        border: "#fb923c",
        title: "#9a3412",
        serviceBg: "linear-gradient(135deg, #fdba74 0%, #fb923c 100%)",
        serviceBorder: "#ea580c",
        serviceText: "#9a3412",
        serviceShadow: "0 2px 8px rgba(251, 146, 60, 0.2)"
    },
    pink: {
        layerBg: "#fce7f3",
        border: "#f472b6",
        title: "#831843",
        serviceBg: "linear-gradient(135deg, #f9a8d4 0%, #f472b6 100%)",
        serviceBorder: "#db2777",
        serviceText: "#831843",
        serviceShadow: "0 2px 8px rgba(244, 114, 182, 0.2)"
    },
    gray: {
        layerBg: "#f3f4f6",
        border: "#9ca3af",
        title: "#374151",
        serviceBg: "linear-gradient(135deg, #d1d5db 0%, #9ca3af 100%)",
        serviceBorder: "#6b7280",
        serviceText: "#374151",
        serviceShadow: "0 2px 8px rgba(156, 163, 175, 0.2)"
    },
    indigo: {
        layerBg: "#e0f2fe",
        border: "#60a5fa",
        title: "#1e3a8a",
        serviceBg: "linear-gradient(135deg, #93c5fd 0%, #60a5fa 100%)",
        serviceBorder: "#2563eb",
        serviceText: "#1e3a8a",
        serviceShadow: "0 2px 8px rgba(96, 165, 250, 0.2)"
    }
};

// currentState, leftPanelConfigured, rightPanelConfigured are defined in an inline script in template.html

// 切换侧面板显示
function togglePanel(side) {
    const panel = document.getElementById(`${side}-panel`);
    const toggle = document.getElementById(`${side}-panel-toggle`);

    if (side === 'left') {
        currentState.leftPanelEnabled = !currentState.leftPanelEnabled;
        if (toggle) {
            toggle.textContent = currentState.leftPanelEnabled ? '启用' : '禁用';
            toggle.classList.toggle('disabled', !currentState.leftPanelEnabled);
        }
        if (panel) {
            panel.style.display = currentState.leftPanelEnabled ? 'flex' : 'none'; // Use flex for side panels
        }
    } else {
        currentState.rightPanelEnabled = !currentState.rightPanelEnabled;
        if (toggle) {
            toggle.textContent = currentState.rightPanelEnabled ? '启用' : '禁用';
            toggle.classList.toggle('disabled', !currentState.rightPanelEnabled);
        }
        if (panel) {
            panel.style.display = currentState.rightPanelEnabled ? 'flex' : 'none'; // Use flex for side panels
        }
    }
    generateSidePanelColorControls(); // Regenerate if visibility changes
    updateSidePanelColorInputs();
    updateGridLayout();
    saveColorSettings(); // Save panel state
}

// 更新网格布局
function updateGridLayout() {
    const grid = document.getElementById('architecture-grid');
    const container = document.getElementById('architecture-container');
    if (!grid || !container) return;

    let columnStyles = [];

    const leftWidthInput = document.getElementById('left-width-input');
    const rightWidthInput = document.getElementById('right-width-input');

    // Use currentState for panel widths, fallback to input value or default
    let leftPanelWidth = currentState.leftPanelWidth;
    if (leftWidthInput && currentState.leftPanelEnabled) {
        leftPanelWidth = parseInt(leftWidthInput.value) || currentState.leftPanelWidth;
        currentState.leftPanelWidth = leftPanelWidth; // Update state from input if enabled
    }

    let rightPanelWidth = currentState.rightPanelWidth;
    if (rightWidthInput && currentState.rightPanelEnabled) {
        rightPanelWidth = parseInt(rightWidthInput.value) || currentState.rightPanelWidth;
        currentState.rightPanelWidth = rightPanelWidth; // Update state from input if enabled
    }

    const centerMinWidth = 300; // Adjusted minimum width for center

    let activeColumns = 0;
    if (leftPanelConfigured && currentState.leftPanelEnabled) activeColumns++;
    if (rightPanelConfigured && currentState.rightPanelEnabled) activeColumns++;
    activeColumns++; // For center column

    if (leftPanelConfigured && currentState.leftPanelEnabled) {
        columnStyles.push(leftPanelWidth + 'px');
    }

    columnStyles.push(`minmax(${centerMinWidth}px, 1fr)`);


    if (rightPanelConfigured && currentState.rightPanelEnabled) {
        columnStyles.push(rightPanelWidth + 'px');
    }

    if (columnStyles.length === 1 && columnStyles[0] === `minmax(${centerMinWidth}px, 1fr)`) {
        container.classList.add('single-column');
        grid.style.gridTemplateColumns = '1fr';
    } else {
        container.classList.remove('single-column');
        grid.style.gridTemplateColumns = columnStyles.join(' ');
    }
}

// 切换连接线显示（最终优化版本）
function toggleConnections() {
    const toggle = document.getElementById('connections-toggle');
    const svg = document.getElementById('connections-svg');
    const arrows = document.querySelectorAll('.arrow-up');
    const container = document.getElementById('architecture-container');

    currentState.connectionsVisible = !currentState.connectionsVisible;
    
    if (toggle) {
        toggle.textContent = currentState.connectionsVisible ? '隐藏' : '显示';
        toggle.classList.toggle('disabled', !currentState.connectionsVisible);
    }
    
    // 控制SVG连接线
    if (svg) {
        svg.style.display = currentState.connectionsVisible ? 'block' : 'none';
    }
    
    // 控制HTML箭头
    arrows.forEach(arrow => {
        arrow.style.display = currentState.connectionsVisible ? 'flex' : 'none';
    });
    
    // 通过CSS类控制整体布局紧凑性
    if (container) {
        if (currentState.connectionsVisible) {
            container.classList.remove('connections-hidden');
        } else {
            container.classList.add('connections-hidden');
        }
    }
    
    saveColorSettings(); // Save connection visibility
}

// 应用最大宽度限制和缩放
function applyResize() {
    const container = document.getElementById('architecture-container');
    const widthInput = document.getElementById('width-input');
    const scaleInput = document.getElementById('scale-input');
    if (!container) return;

    const width = widthInput ? widthInput.value : currentState.containerWidth;
    const scale = scaleInput ? scaleInput.value / 100 : currentState.scale / 100;

    if (width) {
        container.style.maxWidth = width + 'px';
        currentState.containerWidth = parseInt(width);
    }

    container.style.transform = `scale(${scale})`;
    container.style.transformOrigin = 'top center'; // Changed to top center for better scaling effect
    currentState.scale = parseInt(scaleInput ? scaleInput.value : currentState.scale);

    saveColorSettings(); // Save width and scale
}

// 初始化事件监听
function initializeEventListeners() {
    const widthInput = document.getElementById('width-input');
    const scaleInput = document.getElementById('scale-input');
    const leftWidthInput = document.getElementById('left-width-input');
    const rightWidthInput = document.getElementById('right-width-input');

    if (widthInput) widthInput.addEventListener('input', applyResize);
    if (scaleInput) scaleInput.addEventListener('input', applyResize);

    if (leftWidthInput) {
        leftWidthInput.addEventListener('input', () => {
            currentState.leftPanelWidth = parseInt(leftWidthInput.value);
            updateGridLayout();
            saveColorSettings();
        });
    }
    if (rightWidthInput) {
        rightWidthInput.addEventListener('input', () => {
            currentState.rightPanelWidth = parseInt(rightWidthInput.value);
            updateGridLayout();
            saveColorSettings();
        });
    }

    const leftToggle = document.getElementById('left-panel-toggle');
    const rightToggle = document.getElementById('right-panel-toggle');
    const connectionsToggle = document.getElementById('connections-toggle');

    if (leftToggle) {
        leftToggle.textContent = currentState.leftPanelEnabled ? '启用' : '禁用';
        leftToggle.classList.toggle('disabled', !currentState.leftPanelEnabled);
        const leftPanel = document.getElementById('left-panel');
        if (leftPanel) leftPanel.style.display = currentState.leftPanelEnabled ? 'flex' : 'none';
    }
    if (rightToggle) {
        rightToggle.textContent = currentState.rightPanelEnabled ? '启用' : '禁用';
        rightToggle.classList.toggle('disabled', !currentState.rightPanelEnabled);
        const rightPanel = document.getElementById('right-panel');
        if (rightPanel) rightPanel.style.display = currentState.rightPanelEnabled ? 'flex' : 'none';
    }
    if (connectionsToggle) {
        connectionsToggle.textContent = currentState.connectionsVisible ? '隐藏' : '显示';
        connectionsToggle.classList.toggle('disabled', !currentState.connectionsVisible);
        
        // 初始化时同时控制SVG和HTML箭头
        const svg = document.getElementById('connections-svg');
        const arrows = document.querySelectorAll('.arrow-up');
        const container = document.getElementById('architecture-container');
        
        if (svg) svg.style.display = currentState.connectionsVisible ? 'block' : 'none';
        arrows.forEach(arrow => {
            arrow.style.display = currentState.connectionsVisible ? 'flex' : 'none';
        });
        
        // 初始化容器CSS类
        if (container) {
            if (currentState.connectionsVisible) {
                container.classList.remove('connections-hidden');
            } else {
                container.classList.add('connections-hidden');
            }
        }
    }
}

// 颜色处理函数
function hexToRgba(hex, alpha = 1) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function adjustBrightness(hex, percent) {
    const num = parseInt(hex.slice(1), 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.min(255, Math.max(0, (num >> 16) + amt));
    const G = Math.min(255, Math.max(0, (num >> 8 & 0x00FF) + amt));
    const B = Math.min(255, Math.max(0, (num & 0x0000FF) + amt));
    return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
}

// 生成层级颜色控制器
function generateLayerColorControls() {
    const layerColorControlsContainer = document.getElementById('layer-color-controls');
    if (!layerColorControlsContainer) return;

    layerColorControlsContainer.innerHTML = ''; // Clear previous controls
    const layers = document.querySelectorAll('.architecture-layer');

    layers.forEach((layer, index) => {
        const layerTitleElement = layer.querySelector('.layer-title');
        const titleText = layerTitleElement ? layerTitleElement.textContent.split('、').slice(1).join('、').trim() : `Layer ${index + 1}`;

        const controlDiv = document.createElement('div');
        controlDiv.className = 'layer-color-controls'; // This class is for the sub-section for each layer
        controlDiv.innerHTML = `
                <h4>${titleText} (第${index + 1}层)</h4>
                
                <!-- 层级专用主题选择器 -->
                <div class="layer-theme-presets" style="margin-bottom: 12px;">
                    <label style="font-size: 0.7rem; color: #64748b; margin-bottom: 4px; display: block;">快速主题</label>
                    <div class="theme-preset-grid">
                        <button class="layer-theme-preset" data-layer="${index}" data-theme="blue" style="background: linear-gradient(135deg, #cbd5e1 0%, #94a3b8 100%); width: 24px; height: 24px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.6rem; color: white;">蓝</button>
                        <button class="layer-theme-preset" data-layer="${index}" data-theme="green" style="background: linear-gradient(135deg, #a7d4a7 0%, #86bc86 100%); width: 24px; height: 24px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.6rem; color: white;">绿</button>
                        <button class="layer-theme-preset" data-layer="${index}" data-theme="purple" style="background: linear-gradient(135deg, #c7b8e0 0%, #b4a5d6 100%); width: 24px; height: 24px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.6rem; color: white;">紫</button>
                        <button class="layer-theme-preset" data-layer="${index}" data-theme="yellow" style="background: linear-gradient(135deg, #e8d5a3 0%, #d4c590 100%); width: 24px; height: 24px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.6rem; color: white;">黄</button>
                        <button class="layer-theme-preset" data-layer="${index}" data-theme="red" style="background: linear-gradient(135deg, #fca5a5 0%, #f87171 100%); width: 24px; height: 24px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.6rem; color: white;">红</button>
                        <button class="layer-theme-preset" data-layer="${index}" data-theme="cyan" style="background: linear-gradient(135deg, #a5f3fc 0%, #67e8f9 100%); width: 24px; height: 24px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.6rem; color: white;">青</button>
                    </div>
                </div>
                
                <!-- 详细颜色控制 -->
                <div class="color-row">
                    <label>背景色</label>
                    <input type="color" id="layer-${index}-bg" value="#f1f5f9" data-type="layer" data-index="${index}" data-property="bg">
                </div>
                <div class="color-row">
                    <label>边框色</label>
                    <input type="color" id="layer-${index}-border" value="#94a3b8" data-type="layer" data-index="${index}" data-property="border">
                </div>
                <div class="color-row">
                    <label>标题色</label>
                    <input type="color" id="layer-${index}-title" value="#475569" data-type="layer" data-index="${index}" data-property="title">
                </div>
                <div class="color-row">
                    <label>服务块</label>
                    <input type="color" id="layer-${index}-service" value="#94a3b8" data-type="layer" data-index="${index}" data-property="service">
                </div>
            `;
        layerColorControlsContainer.appendChild(controlDiv);
    });

    // 添加事件监听器给颜色输入框
    const colorInputs = layerColorControlsContainer.querySelectorAll('input[type="color"]');
    colorInputs.forEach(input => {
        input.addEventListener('input', handleColorChange);
    });

    // 添加事件监听器给层级主题按钮
    const layerThemeButtons = layerColorControlsContainer.querySelectorAll('.layer-theme-preset');
    layerThemeButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const layerIndex = e.target.dataset.layer;
            const themeName = e.target.dataset.theme;
            applyThemeToLayer(parseInt(layerIndex), themeName);
            
            // 更新按钮状态
            const layerButtons = layerColorControlsContainer.querySelectorAll(`[data-layer="${layerIndex}"]`);
            layerButtons.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            saveColorSettings();
        });
    });
}

// 生成侧面板颜色控制器
function generateSidePanelColorControls() {
    const sidePanelColorControlsContainer = document.getElementById('side-panel-color-controls');
    if (!sidePanelColorControlsContainer) return;

    sidePanelColorControlsContainer.innerHTML = ''; // Clear previous controls
    const panelsInfo = [
        { id: 'left-panel', name: '左侧面板', prefix: 'left', enabled: currentState.leftPanelEnabled && leftPanelConfigured },
        { id: 'right-panel', name: '右侧面板', prefix: 'right', enabled: currentState.rightPanelEnabled && rightPanelConfigured }
    ];

    panelsInfo.forEach(panelInfo => {
        if (panelInfo.enabled) {
            const controlDiv = document.createElement('div');
            controlDiv.className = 'side-panel-color-controls'; // This class is for the sub-section for each side panel
            controlDiv.innerHTML = `
                    <h4>${panelInfo.name}</h4>
                    
                    <!-- 侧面板专用主题选择器 -->
                    <div class="panel-theme-presets" style="margin-bottom: 12px;">
                        <label style="font-size: 0.7rem; color: #64748b; margin-bottom: 4px; display: block;">快速主题</label>
                        <div class="theme-preset-grid">
                            <button class="panel-theme-preset" data-panel="${panelInfo.prefix}" data-theme="blue" style="background: linear-gradient(135deg, #cbd5e1 0%, #94a3b8 100%); width: 24px; height: 24px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.6rem; color: white;">蓝</button>
                            <button class="panel-theme-preset" data-panel="${panelInfo.prefix}" data-theme="green" style="background: linear-gradient(135deg, #a7d4a7 0%, #86bc86 100%); width: 24px; height: 24px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.6rem; color: white;">绿</button>
                            <button class="panel-theme-preset" data-panel="${panelInfo.prefix}" data-theme="purple" style="background: linear-gradient(135deg, #c7b8e0 0%, #b4a5d6 100%); width: 24px; height: 24px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.6rem; color: white;">紫</button>
                            <button class="panel-theme-preset" data-panel="${panelInfo.prefix}" data-theme="yellow" style="background: linear-gradient(135deg, #e8d5a3 0%, #d4c590 100%); width: 24px; height: 24px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.6rem; color: white;">黄</button>
                            <button class="panel-theme-preset" data-panel="${panelInfo.prefix}" data-theme="red" style="background: linear-gradient(135deg, #fca5a5 0%, #f87171 100%); width: 24px; height: 24px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.6rem; color: white;">红</button>
                            <button class="panel-theme-preset" data-panel="${panelInfo.prefix}" data-theme="cyan" style="background: linear-gradient(135deg, #a5f3fc 0%, #67e8f9 100%); width: 24px; height: 24px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.6rem; color: white;">青</button>
                            <button class="panel-theme-preset" data-panel="${panelInfo.prefix}" data-theme="gray" style="background: linear-gradient(135deg, #d1d5db 0%, #9ca3af 100%); width: 24px; height: 24px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.6rem; color: white;">灰</button>
                            <button class="panel-theme-preset" data-panel="${panelInfo.prefix}" data-theme="orange" style="background: linear-gradient(135deg, #fdba74 0%, #fb923c 100%); width: 24px; height: 24px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.6rem; color: white;">橙</button>
                        </div>
                    </div>
                    
                    <!-- 详细颜色控制 -->
                    <div class="color-row">
                        <label>背景色</label>
                        <input type="color" id="${panelInfo.prefix}-panel-bg" value="#f8fafc" data-type="side" data-prefix="${panelInfo.prefix}" data-property="panel-bg">
                    </div>
                    <div class="color-row">
                        <label>边框色</label>
                        <input type="color" id="${panelInfo.prefix}-panel-border" value="#e2e8f0" data-type="side" data-prefix="${panelInfo.prefix}" data-property="panel-border">
                    </div>
                    <div class="color-row">
                        <label>标题色</label>
                        <input type="color" id="${panelInfo.prefix}-panel-title" value="#374151" data-type="side" data-prefix="${panelInfo.prefix}" data-property="panel-title">
                    </div>
                    <div class="color-row">
                        <label>块背景</label>
                        <input type="color" id="${panelInfo.prefix}-block-bg" value="#f1f5f9" data-type="side" data-prefix="${panelInfo.prefix}" data-property="block-bg">
                    </div>
                     <div class="color-row">
                        <label>块边框</label>
                        <input type="color" id="${panelInfo.prefix}-block-border" value="#cbd5e1" data-type="side" data-prefix="${panelInfo.prefix}" data-property="block-border">
                    </div>
                    <div class="color-row">
                        <label>块文字</label>
                        <input type="color" id="${panelInfo.prefix}-block-text" value="#475569" data-type="side" data-prefix="${panelInfo.prefix}" data-property="block-text">
                    </div>
                `;
            sidePanelColorControlsContainer.appendChild(controlDiv);
        }
    });

    // 添加事件监听器给颜色输入框
    const colorInputs = sidePanelColorControlsContainer.querySelectorAll('input[type="color"]');
    colorInputs.forEach(input => {
        input.addEventListener('input', handleColorChange);
    });

    // 添加事件监听器给侧面板主题按钮
    const panelThemeButtons = sidePanelColorControlsContainer.querySelectorAll('.panel-theme-preset');
    panelThemeButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const panelPrefix = e.target.dataset.panel;
            const themeName = e.target.dataset.theme;
            applyThemeToPanel(panelPrefix, themeName);
            
            // 更新按钮状态
            const panelButtons = sidePanelColorControlsContainer.querySelectorAll(`[data-panel="${panelPrefix}"]`);
            panelButtons.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            saveColorSettings();
        });
    });
}


// 处理颜色变化
function handleColorChange(e) {
    const type = e.target.dataset.type;
    const color = e.target.value;

    if (type === 'layer') {
        const layerIndex = e.target.dataset.index;
        const property = e.target.dataset.property;
        updateLayerColor(layerIndex, property, color);
    } else if (type === 'side') {
        const prefix = e.target.dataset.prefix;
        const property = e.target.dataset.property;
        updateSidePanelColor(prefix, property, color);
    }
    saveColorSettings();
}

// 更新层级颜色
function updateLayerColor(layerIndex, property, color) {
    const root = document.documentElement;

    switch(property) {
        case 'bg':
            root.style.setProperty(`--layer-${layerIndex}-bg`, color);
            break;
        case 'border':
            root.style.setProperty(`--layer-${layerIndex}-border`, color);
            break;
        case 'title':
            root.style.setProperty(`--layer-${layerIndex}-title`, color);
            break;
        case 'service':
            const serviceColor = color;
            const darkerColor = adjustBrightness(serviceColor, -20);
            const textColor = adjustBrightness(serviceColor, -60); // Ensure good contrast
            const shadowColorRgba = hexToRgba(darkerColor, 0.2); // Shadow based on darker color for depth

            root.style.setProperty(`--layer-${layerIndex}-service-bg`, `linear-gradient(135deg, ${serviceColor} 0%, ${darkerColor} 100%)`);
            root.style.setProperty(`--layer-${layerIndex}-service-border`, darkerColor);
            root.style.setProperty(`--layer-${layerIndex}-service-text`, textColor);
            root.style.setProperty(`--layer-${layerIndex}-service-shadow`, `0 2px 8px ${shadowColorRgba}`);
            break;
    }
}

// 更新侧面板颜色
function updateSidePanelColor(prefix, property, color) {
    const root = document.documentElement;
    root.style.setProperty(`--${prefix}-${property}`, color);

    // Optional: Auto-derive related colors if a base color changes, e.g., block-bg
    if (property === 'block-bg') {
        // const baseColor = color;
        // const darkerBorder = adjustBrightness(baseColor, -15);
        // const contrastText = adjustBrightness(baseColor, -50); // Or determine if light/dark base and choose black/white
        // root.style.setProperty(`--${prefix}-block-border`, darkerBorder);
        // root.style.setProperty(`--${prefix}-block-text`, contrastText);
    }
    if (property === 'panel-bg') {
        // const baseColor = color;
        // const darkerBorder = adjustBrightness(baseColor, -10); // panel border slightly darker than bg
        // root.style.setProperty(`--${prefix}-panel-border`, darkerBorder);
    }
}


// 应用预设主题
function applyTheme(themeName) {
    const theme = themeColors[themeName];
    if (!theme) return;

    const layers = document.querySelectorAll('.architecture-layer');
    layers.forEach((layer, index) => {
        updateLayerFromTheme(index, theme);
        updateLayerColorInputs(index, theme); // Update pickers for layers
    });

    // For simplicity, side panels are not part of these themes directly.
    // They can be reset to a "default" or their specific initial colors.
    // Or, you could define side panel colors within each theme object too.
    // For now, let's assume they are reset/re-initialized by loadSettings or resetAllColors logic.

    document.querySelectorAll('.theme-preset').forEach(btn => {
        btn.classList.remove('active');
    });
    const activeBtn = document.querySelector(`.theme-preset[data-theme="${themeName}"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
    saveColorSettings();
}

// 应用主题到特定层级
function applyThemeToLayer(layerIndex, themeName) {
    const theme = themeColors[themeName];
    if (!theme) return;

    updateLayerFromTheme(layerIndex, theme);
    updateLayerColorInputs(layerIndex, theme);
    
    // 全局主题状态设为custom，因为现在是混合主题
    document.querySelectorAll('.theme-preset').forEach(btn => {
        btn.classList.remove('active');
    });
    
    saveColorSettings();
}

// 应用主题到特定侧面板
function applyThemeToPanel(panelPrefix, themeName) {
    const theme = themeColors[themeName];
    if (!theme) return;

    // 将层级主题映射到侧面板颜色
    const panelTheme = {
        'panel-bg': theme.layerBg,
        'panel-border': theme.border,
        'panel-title': theme.title,
        'block-bg': adjustBrightness(theme.layerBg, -3), // 稍微深一点的背景
        'block-border': theme.serviceBorder,
        'block-text': theme.serviceText
    };

    // 应用颜色到侧面板
    Object.keys(panelTheme).forEach(property => {
        updateSidePanelColor(panelPrefix, property, panelTheme[property]);
    });
    
    // 更新颜色选择器
    updateSidePanelColorInputs();
    
    // 全局主题状态设为custom，因为现在是混合主题
    document.querySelectorAll('.theme-preset').forEach(btn => {
        btn.classList.remove('active');
    });
    
    saveColorSettings();
}

// 从主题更新层级
function updateLayerFromTheme(layerIndex, theme) {
    const root = document.documentElement;
    root.style.setProperty(`--layer-${layerIndex}-bg`, theme.layerBg);
    root.style.setProperty(`--layer-${layerIndex}-border`, theme.border);
    root.style.setProperty(`--layer-${layerIndex}-title`, theme.title);
    root.style.setProperty(`--layer-${layerIndex}-service-bg`, theme.serviceBg);
    root.style.setProperty(`--layer-${layerIndex}-service-border`, theme.serviceBorder);
    root.style.setProperty(`--layer-${layerIndex}-service-text`, theme.serviceText);
    root.style.setProperty(`--layer-${layerIndex}-service-shadow`, theme.serviceShadow);
}

// 更新层级颜色选择器的值
function updateLayerColorInputs(layerIndex, themeColorsForLayer) {
    const bgInput = document.getElementById(`layer-${layerIndex}-bg`);
    const borderInput = document.getElementById(`layer-${layerIndex}-border`);
    const titleInput = document.getElementById(`layer-${layerIndex}-title`);
    const serviceInput = document.getElementById(`layer-${layerIndex}-service`); // This corresponds to the base color for service blocks

    if (bgInput) bgInput.value = themeColorsForLayer.layerBg;
    if (borderInput) borderInput.value = themeColorsForLayer.border;
    if (titleInput) titleInput.value = themeColorsForLayer.title;
    // For serviceInput, we used theme.serviceBorder as the 'base' for the picker in previous logic
    // If theme.serviceBg is a gradient, we need to pick a representative color.
    // Let's assume theme.serviceBorder is a good representative hex color.
    if (serviceInput) serviceInput.value = themeColorsForLayer.serviceBorder; // Or a base hex from which gradient is derived
}

// 更新侧面板颜色选择器的值
function updateSidePanelColorInputs() {
    const rootStyle = getComputedStyle(document.documentElement);
    const panelsInfo = [
        { prefix: 'left', enabled: currentState.leftPanelEnabled && leftPanelConfigured },
        { prefix: 'right', enabled: currentState.rightPanelEnabled && rightPanelConfigured }
    ];

    panelsInfo.forEach(panelInfo => {
        if (panelInfo.enabled) {
            const panelBGInput = document.getElementById(`${panelInfo.prefix}-panel-bg`);
            if (panelBGInput) panelBGInput.value = rootStyle.getPropertyValue(`--${panelInfo.prefix}-panel-bg`).trim() || '#f8fafc';

            const panelBorderInput = document.getElementById(`${panelInfo.prefix}-panel-border`);
            if (panelBorderInput) panelBorderInput.value = rootStyle.getPropertyValue(`--${panelInfo.prefix}-panel-border`).trim() || '#e2e8f0';

            const panelTitleInput = document.getElementById(`${panelInfo.prefix}-panel-title`);
            if (panelTitleInput) panelTitleInput.value = rootStyle.getPropertyValue(`--${panelInfo.prefix}-panel-title`).trim() || '#374151';

            const blockBGInput = document.getElementById(`${panelInfo.prefix}-block-bg`);
            if (blockBGInput) blockBGInput.value = rootStyle.getPropertyValue(`--${panelInfo.prefix}-block-bg`).trim() || '#f1f5f9';

            const blockBorderInput = document.getElementById(`${panelInfo.prefix}-block-border`);
            if (blockBorderInput) blockBorderInput.value = rootStyle.getPropertyValue(`--${panelInfo.prefix}-block-border`).trim() || '#cbd5e1';

            const blockTextInput = document.getElementById(`${panelInfo.prefix}-block-text`);
            if (blockTextInput) blockTextInput.value = rootStyle.getPropertyValue(`--${panelInfo.prefix}-block-text`).trim() || '#475569';
        }
    });
}


// 重置所有颜色
function resetAllColors() {
    // Apply a default theme (e.g., 'blue') for layers
    applyTheme('blue');

    // Reset side panel colors to their initial/default CSS variable values
    // These defaults should be defined in your main CSS or as initial JS variables
    const defaultSidePanelColors = {
        'panel-bg': '#f8fafc',
        'panel-border': '#e2e8f0',
        'panel-title': '#374151',
        'block-bg': '#f1f5f9',
        'block-border': '#cbd5e1',
        'block-text': '#475569',
    };

    ['left', 'right'].forEach(prefix => {
        if ((prefix === 'left' && currentState.leftPanelEnabled && leftPanelConfigured) ||
            (prefix === 'right' && currentState.rightPanelEnabled && rightPanelConfigured)) {
            for (const prop in defaultSidePanelColors) {
                updateSidePanelColor(prefix, prop, defaultSidePanelColors[prop]);
            }
        }
    });

    generateSidePanelColorControls(); // Regenerate to ensure they are present if panels were toggled
    updateSidePanelColorInputs(); // Update pickers to reflect these defaults
    saveColorSettings();
}


// 保存设置到localStorage
function saveColorSettings() {
    const settings = {
        width: currentState.containerWidth,
        scale: currentState.scale,
        leftPanelEnabled: currentState.leftPanelEnabled,
        rightPanelEnabled: currentState.rightPanelEnabled,
        connectionsVisible: currentState.connectionsVisible,
        leftPanelWidth: currentState.leftPanelWidth,
        rightPanelWidth: currentState.rightPanelWidth,
        colors: {
            layers: {},
            sidePanels: { left: {}, right: {} }
        },
        activeTheme: 'custom' // Default to custom, update if a theme is active
    };

    const layers = document.querySelectorAll('.architecture-layer');
    layers.forEach((layer, index) => {
        const bgInput = document.getElementById(`layer-${index}-bg`);
        const borderInput = document.getElementById(`layer-${index}-border`);
        const titleInput = document.getElementById(`layer-${index}-title`);
        const serviceInput = document.getElementById(`layer-${index}-service`);

        settings.colors.layers[index] = {
            bg: bgInput?.value || getComputedStyle(document.documentElement).getPropertyValue(`--layer-${index}-bg`).trim(),
            border: borderInput?.value || getComputedStyle(document.documentElement).getPropertyValue(`--layer-${index}-border`).trim(),
            title: titleInput?.value || getComputedStyle(document.documentElement).getPropertyValue(`--layer-${index}-title`).trim(),
            service: serviceInput?.value || adjustBrightness(getComputedStyle(document.documentElement).getPropertyValue(`--layer-${index}-service-border`).trim(), 20) // approximate base from border
        };
    });

    ['left', 'right'].forEach(prefix => {
        if ((prefix === 'left' && currentState.leftPanelEnabled && leftPanelConfigured) ||
            (prefix === 'right' && currentState.rightPanelEnabled && rightPanelConfigured)) {
            settings.colors.sidePanels[prefix] = {
                'panel-bg': document.getElementById(`${prefix}-panel-bg`)?.value || getComputedStyle(document.documentElement).getPropertyValue(`--${prefix}-panel-bg`).trim(),
                'panel-border': document.getElementById(`${prefix}-panel-border`)?.value || getComputedStyle(document.documentElement).getPropertyValue(`--${prefix}-panel-border`).trim(),
                'panel-title': document.getElementById(`${prefix}-panel-title`)?.value || getComputedStyle(document.documentElement).getPropertyValue(`--${prefix}-panel-title`).trim(),
                'block-bg': document.getElementById(`${prefix}-block-bg`)?.value || getComputedStyle(document.documentElement).getPropertyValue(`--${prefix}-block-bg`).trim(),
                'block-border': document.getElementById(`${prefix}-block-border`)?.value || getComputedStyle(document.documentElement).getPropertyValue(`--${prefix}-block-border`).trim(),
                'block-text': document.getElementById(`${prefix}-block-text`)?.value || getComputedStyle(document.documentElement).getPropertyValue(`--${prefix}-block-text`).trim(),
            };
        }
    });

    const activeThemeBtn = document.querySelector('.theme-preset.active');
    if (activeThemeBtn) {
        settings.activeTheme = activeThemeBtn.dataset.theme;
    }

    localStorage.setItem('three-column-architecture-settings', JSON.stringify(settings));
}


// 加载设置
function loadSettings() {
    const saved = localStorage.getItem('three-column-architecture-settings');
    if (!saved) {
        applyTheme('blue'); // Apply default theme if no settings saved
        // Set initial side panel colors from CSS variables (or defaults if not set)
        resetSidePanelColorsToDefaults();
        saveColorSettings(); // Save these initial defaults
        return;
    }

    try {
        const settings = JSON.parse(saved);

        // Layout settings
        currentState.containerWidth = settings.width || currentState.containerWidth;
        currentState.scale = settings.scale || currentState.scale;
        currentState.leftPanelEnabled = typeof settings.leftPanelEnabled === 'boolean' ? settings.leftPanelEnabled : currentState.leftPanelEnabled;
        currentState.rightPanelEnabled = typeof settings.rightPanelEnabled === 'boolean' ? settings.rightPanelEnabled : currentState.rightPanelEnabled;
        currentState.connectionsVisible = typeof settings.connectionsVisible === 'boolean' ? settings.connectionsVisible : currentState.connectionsVisible;
        currentState.leftPanelWidth = settings.leftPanelWidth || currentState.leftPanelWidth;
        currentState.rightPanelWidth = settings.rightPanelWidth || currentState.rightPanelWidth;

        const widthInput = document.getElementById('width-input');
        if (widthInput) widthInput.value = currentState.containerWidth;
        const scaleInput = document.getElementById('scale-input');
        if (scaleInput) scaleInput.value = currentState.scale;
        const leftWidthInput = document.getElementById('left-width-input');
        if (leftWidthInput) leftWidthInput.value = currentState.leftPanelWidth;
        const rightWidthInput = document.getElementById('right-width-input');
        if (rightWidthInput) rightWidthInput.value = currentState.rightPanelWidth;

        initializeEventListeners(); // Re-apply button states and panel visibility based on loaded currentState

        // Load layer colors
        if (settings.colors && settings.colors.layers) {
            Object.keys(settings.colors.layers).forEach(layerIndex => {
                const colors = settings.colors.layers[layerIndex];
                if (colors) {
                    updateLayerColor(layerIndex, 'bg', colors.bg);
                    updateLayerColor(layerIndex, 'border', colors.border);
                    updateLayerColor(layerIndex, 'title', colors.title);
                    updateLayerColor(layerIndex, 'service', colors.service); // This will derive service-bg, service-border etc.
                }
            });
        } else if (settings.activeTheme && settings.activeTheme !== 'custom' && themeColors[settings.activeTheme]) {
            applyTheme(settings.activeTheme); // Apply saved theme if no specific layer colors
        } else {
            applyTheme('blue'); // Fallback to default theme
        }

        // Load side panel colors
        if (settings.colors && settings.colors.sidePanels) {
            ['left', 'right'].forEach(prefix => {
                const panelColors = settings.colors.sidePanels[prefix];
                if (panelColors && Object.keys(panelColors).length > 0) { // Check if there are saved colors for this panel
                    if ((prefix === 'left' && currentState.leftPanelEnabled && leftPanelConfigured) ||
                        (prefix === 'right' && currentState.rightPanelEnabled && rightPanelConfigured)) {
                        Object.keys(panelColors).forEach(property => {
                            updateSidePanelColor(prefix, property, panelColors[property]);
                        });
                    }
                } else {
                    // If no saved colors for a panel, reset it to defaults
                    resetSidePanelColorsToDefaults(prefix);
                }
            });
        } else {
            resetSidePanelColorsToDefaults('left');
            resetSidePanelColorsToDefaults('right');
        }


        if (settings.activeTheme && settings.activeTheme !== 'custom') {
            const activeBtn = document.querySelector(`.theme-preset[data-theme="${settings.activeTheme}"]`);
            if (activeBtn) {
                document.querySelectorAll('.theme-preset').forEach(btn => btn.classList.remove('active'));
                activeBtn.classList.add('active');
            }
        } else {
            document.querySelectorAll('.theme-preset').forEach(btn => btn.classList.remove('active'));
        }

        applyResize(); // Apply width/scale
        updateGridLayout(); // Apply panel layout

    } catch (e) {
        console.error('Error loading saved settings:', e);
        applyTheme('blue');
        resetSidePanelColorsToDefaults();
    }
}

function resetSidePanelColorsToDefaults(specificPanelPrefix = null) {
    const defaultSidePanelColors = {
        'panel-bg': '#f8fafc', 'panel-border': '#e2e8f0', 'panel-title': '#374151',
        'block-bg': '#f1f5f9', 'block-border': '#cbd5e1', 'block-text': '#475569',
    };

    const prefixesToReset = specificPanelPrefix ? [specificPanelPrefix] : ['left', 'right'];

    prefixesToReset.forEach(prefix => {
        if ((prefix === 'left' && leftPanelConfigured) || (prefix === 'right' && rightPanelConfigured)) {
            for (const prop in defaultSidePanelColors) {
                updateSidePanelColor(prefix, prop, defaultSidePanelColors[prop]);
            }
        }
    });
}


// 页面加载完成后初始化
window.addEventListener('DOMContentLoaded', function() {
    // Initial generation of controls must happen before loadSettings if loadSettings might update their values
    generateLayerColorControls();
    generateSidePanelColorControls();

    loadSettings(); // Load settings first, this will set initial state and colors

    // Then update inputs to reflect loaded state
    updateLayerColorInputsAfterLoad();
    updateSidePanelColorInputs(); // Ensure side panel pickers are correct after load

    initializeEventListeners(); // Set up listeners and initial UI state based on possibly loaded settings
    updateGridLayout(); // Apply layout based on loaded panel states and widths
    applyResize(); // Apply loaded container width and scale

    document.querySelectorAll('.theme-preset').forEach(btn => {
        btn.addEventListener('click', () => {
            applyTheme(btn.dataset.theme);
            // After applying a theme, layer color inputs need to be updated
            updateLayerColorInputsAfterLoad();
            // Side panels are not part of themes in this setup, so their pickers remain as is or could be reset
        });
    });

    loadHtml2Canvas(); // Load the library for downloads
});

function updateLayerColorInputsAfterLoad() {
    const layers = document.querySelectorAll('.architecture-layer');
    layers.forEach((layer, index) => {
        const rootStyle = getComputedStyle(document.documentElement);
        const currentThemeForLayer = {
            layerBg: rootStyle.getPropertyValue(`--layer-${index}-bg`).trim(),
            border: rootStyle.getPropertyValue(`--layer-${index}-border`).trim(),
            title: rootStyle.getPropertyValue(`--layer-${index}-title`).trim(),
            // For service, picker expects a base color. We stored 'service' as the base color.
            // Or, we derive it from one of the resulting CSS variables, e.g., service-border
            serviceBorder: rootStyle.getPropertyValue(`--layer-${index}-service-border`).trim()
        };
        updateLayerColorInputs(index, currentThemeForLayer);
    });
}


// 下载功能实现
function downloadAsPNG() {
    alert('下载功能已被禁用');
}

function downloadAsJPEG() {
    alert('下载功能已被禁用');
}

function downloadAsImage(format) {
    if (typeof html2canvas === 'undefined') {
        alert('正在加载下载库，请稍后再试...');
        // Attempt to load it again if missed
        if (!document.querySelector('script[src*="html2canvas"]')) {
            loadHtml2Canvas();
        }
        return;
    }

    const container = document.getElementById('architecture-container');
    if (!container) {
        alert('无法找到截图区域!');
        return;
    }
    const originalTransform = container.style.transform;

    const button = event.target;
    const originalText = button.textContent;
    button.textContent = '⏳ 生成中...';
    button.disabled = true;

    container.style.transform = 'none'; // Remove scaling for capture

    html2canvas(container, {
        backgroundColor: '#f8fafc', // Match body background or choose a specific one
        scale: window.devicePixelRatio * 2, // Higher scale for better quality
        useCORS: true,
        allowTaint: true, // May be needed for external images/fonts if any
        scrollX: -window.scrollX, // Capture from the top-left of the element
        scrollY: -window.scrollY,
        windowWidth: container.scrollWidth,
        windowHeight: container.scrollHeight,
        width: container.scrollWidth, // Explicitly set width
        height: container.scrollHeight, // Explicitly set height
        foreignObjectRendering: true // For SVG rendering
    }).then(canvas => {
        container.style.transform = originalTransform; // Restore transform

        const link = document.createElement('a');
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
        link.download = `architecture-diagram-${timestamp}.${format}`;
        link.href = canvas.toDataURL(`image/${format}`, format === 'jpeg' ? 0.90 : 1.0); // Quality for JPEG

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        button.textContent = originalText;
        button.disabled = false;
    }).catch(error => {
        container.style.transform = originalTransform;
        button.textContent = originalText;
        button.disabled = false;
        alert('图片生成失败: ' + error.message);
        console.error('Download failed:', error);
    });
}

// 检查并加载html2canvas库
function loadHtml2Canvas() {
    console.log('下载功能已被禁用，跳过html2canvas库加载');
}
