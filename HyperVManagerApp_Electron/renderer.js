let selectedVmName = null;

// --- Page Initializers ---

/**
 * Initializes the event listeners and loads data for the VM page.
 */
function initVmsPage() {
    loadVMs();
    initWizard(); // Load the wizard modal and its logic

    // Attach event listeners for VM action buttons
    const refreshBtn = document.getElementById('refresh-vms');
    if(refreshBtn) refreshBtn.addEventListener('click', loadVMs);

    const startBtn = document.getElementById('start-vm');
    if(startBtn) startBtn.addEventListener('click', () => handleVmAction('startVM'));

    const shutdownBtn = document.getElementById('shutdown-vm');
    if(shutdownBtn) shutdownBtn.addEventListener('click', () => handleVmAction('shutdownVM'));

    const stopBtn = document.getElementById('stop-vm');
    if(stopBtn) stopBtn.addEventListener('click', () => handleVmAction('stopVM'));

    const deleteBtn = document.getElementById('delete-vm');
    if(deleteBtn) deleteBtn.addEventListener('click', () => {
        if (selectedVmName && confirm(`确定要删除虚拟机 ${selectedVmName} 吗？此操作不可逆！`)) {
            handleVmAction('deleteVM');
        }
    });

    const connectBtn = document.getElementById('connect-vm');
    if(connectBtn) connectBtn.addEventListener('click', () => handleVmAction('connectVM'));

    const settingsBtn = document.getElementById('settings-vm');
    if(settingsBtn) settingsBtn.addEventListener('click', () => {
        if (selectedVmName) {
            const vmSettingsModal = new bootstrap.Modal(document.getElementById('vmSettingsModal'));
            document.getElementById('vm-settings-title').textContent = selectedVmName;
            // Populate switches and show
            window.electronAPI.getVSwitches().then(switches => {
                const switchSelect = document.getElementById('vm-network-switch');
                switchSelect.innerHTML = switches.map(s => `<option value="${s.Name}">${s.Name} (${s.SwitchType})</option>`).join('');
                vmSettingsModal.show();
            });
        }
    });

    const remoteExecBtn = document.getElementById('remote-exec-vm');
    if(remoteExecBtn) remoteExecBtn.addEventListener('click', () => {
        if (selectedVmName) {
            const remoteExecModal = new bootstrap.Modal(document.getElementById('remoteExecModal'));
            document.getElementById('remote-exec-vm-name').textContent = selectedVmName;
            document.getElementById('remote-exec-output').textContent = '等待执行...';
            document.getElementById('remote-exec-command').value = '';
            remoteExecModal.show();
        }
    });

    // Handle remote execution
    document.getElementById('execute-remote-command').addEventListener('click', async () => {
        const vmName = document.getElementById('remote-exec-vm-name').textContent;
        const username = document.getElementById('remote-exec-username').value;
        const password = document.getElementById('remote-exec-password').value;
        const command = document.getElementById('remote-exec-command').value;
        const outputDiv = document.getElementById('remote-exec-output');

        if (!username || !password || !command) {
            outputDiv.textContent = '用户名、密码和命令不能为空！';
            outputDiv.classList.add('text-danger');
            return;
        }

        outputDiv.textContent = '正在执行命令...';
        outputDiv.classList.remove('text-danger');
        outputDiv.classList.remove('text-success');

        try {
            const result = await window.electronAPI.invokeCommandInVM(vmName, username, password, command);
            outputDiv.textContent = result;
            outputDiv.classList.add('text-success');
        } catch (error) {
            outputDiv.textContent = `执行失败: ${error.message || error}`;
            outputDiv.classList.add('text-danger');
        }
    });

    // Common scripts dropdown
    document.getElementById('common-scripts').addEventListener('change', (e) => {
        const commandTextarea = document.getElementById('remote-exec-command');
        const selectedScript = e.target.value;

        switch (selectedScript) {
            case 'ipconfig':
                commandTextarea.value = 'ipconfig /all';
                break;
            case 'ifconfig':
                commandTextarea.value = 'ifconfig';
                break;
            case 'install-choco':
                commandTextarea.value = "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))";
                break;
            case 'install-git-vscode':
                commandTextarea.value = 'choco install git vscode -y';
                break;
            case 'update-apt':
                commandTextarea.value = 'sudo apt update';
                break;
            case 'install-nginx':
                commandTextarea.value = 'sudo apt install nginx -y';
                break;
            default:
                commandTextarea.value = '';
        }
    });

    // This listener needs to be attached to the main content area to catch the modal's save button
    document.getElementById('main-content').addEventListener('click', async (e) => {
        if (e.target && e.target.id === 'save-vm-settings') {
            const newSwitch = document.getElementById('vm-network-switch').value;
            await window.electronAPI.setVMNetworkAdapter(selectedVmName, newSwitch);
            bootstrap.Modal.getInstance(document.getElementById('vmSettingsModal')).hide();
            alert(`虚拟机 ${selectedVmName} 的网络已更新。`);
        }
    });
}

/**
 * Initializes the network page.
 */
function initNetworkPage() {
    const createSwitchModal = new bootstrap.Modal(document.getElementById('createSwitchModal'));
    const portMappingModal = new bootstrap.Modal(document.getElementById('portMappingModal'));

    loadVSwitches();
    loadNatNetworks();

    // --- Event Listeners ---
    document.getElementById('switch-type').addEventListener('change', async (e) => {
        const selection = e.target.value;
        const netAdapterDiv = document.getElementById('net-adapter-selection');
        if (selection === 'External') {
            netAdapterDiv.style.display = 'block';
            const adapters = await window.electronAPI.getNetAdapters();
            document.getElementById('net-adapter').innerHTML = adapters.map(a => `<option value="${a.Name}">${a.InterfaceDescription} (${a.Name})</option>`).join('');
        } else {
            netAdapterDiv.style.display = 'none';
        }
    });

    document.getElementById('confirm-create-switch').addEventListener('click', async () => {
        const name = document.getElementById('switch-name').value;
        const type = document.getElementById('switch-type').value;
        const netAdapter = document.getElementById('net-adapter').value;
        if (!name) return alert('交换机名称不能为空！');
        await window.electronAPI.createVSwitch(name, type, type === 'External' ? netAdapter : null);
        createSwitchModal.hide();
        loadVSwitches();
    });

    document.getElementById('add-nat-rule-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const natName = e.target.dataset.natName;
        const rule = {
            natName,
            protocol: document.getElementById('nat-protocol').value,
            externalPort: document.getElementById('nat-external-port').value,
            internalIp: document.getElementById('nat-internal-ip').value,
            internalPort: document.getElementById('nat-internal-port').value,
        };
        if(!rule.externalPort || !rule.internalIp || !rule.internalPort) return alert('端口和IP地址不能为空！');
        await window.electronAPI.addNatRule(rule);
        loadNatRules(natName);
        e.target.reset();
    });
}

async function loadNatNetworks() {
    const container = document.getElementById('nat-management-area');
    try {
        const nats = await window.electronAPI.getNatNetworks();
        if (!nats || nats.length === 0) {
            container.innerHTML = '<p class="text-muted">未找到 NAT 网络。</p>';
            return;
        }
        container.innerHTML = nats.map(nat => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span><strong>${nat.Name}</strong> (${nat.InternalIPInterfaceAddressPrefix})</span>
                <button class="btn btn-sm btn-outline-primary manage-nat-btn" data-nat-name="${nat.Name}">管理规则</button>
            </div>
        `).join('');

        document.querySelectorAll('.manage-nat-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const natName = e.currentTarget.dataset.natName;
                const modalTitle = document.getElementById('nat-name-title');
                modalTitle.textContent = natName;
                document.getElementById('add-nat-rule-form').dataset.natName = natName;
                loadNatRules(natName);
                new bootstrap.Modal(document.getElementById('portMappingModal')).show();
            });
        });
    } catch (error) {
        console.error('Failed to load NAT networks:', error);
        container.innerHTML = '<p class="text-danger">加载 NAT 网络失败。</p>';
    }
}

async function loadNatRules(natName) {
    const tableBody = document.querySelector('#nat-rules-table tbody');
    tableBody.innerHTML = '<tr><td colspan="5" class="text-center">加载中...</td></tr>';
    try {
        const rules = await window.electronAPI.getNatRules(natName);
        tableBody.innerHTML = '';
        if (!rules || rules.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">无现有规则。</td></tr>';
            return;
        }
        rules.forEach(r => {
            const row = tableBody.insertRow();
            row.innerHTML = `
                <td>${r.Protocol}</td>
                <td>${r.ExternalPort}</td>
                <td>${r.InternalIPAddress}</td>
                <td>${r.InternalPort}</td>
                <td><button class="btn btn-sm btn-danger remove-nat-rule" data-protocol="${r.Protocol}" data-ext-port="${r.ExternalPort}"><i class="fas fa-times"></i></button></td>
            `;
        });

        document.querySelectorAll('.remove-nat-rule').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const rule = {
                    natName,
                    protocol: e.currentTarget.dataset.protocol,
                    externalPort: e.currentTarget.dataset.extPort,
                };
                await window.electronAPI.removeNatRule(rule);
                loadNatRules(natName);
            });
        });
    } catch (error) {
        console.error('Failed to load NAT rules:', error);
        tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">加载规则失败。</td></tr>';
    }
}

async function loadVSwitches() {
    const tableBody = document.querySelector('#vswitches-table tbody');
    if (!tableBody) return;

    tableBody.innerHTML = '<tr><td colspan="4" class="text-center"><div class="spinner-border spinner-border-sm"></div> 加载中...</td></tr>';

    try {
        const switches = await window.electronAPI.getVSwitches();
        tableBody.innerHTML = '';
        if (!switches || switches.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="4" class="text-center">未找到任何虚拟交换机。</td></tr>';
            return;
        }

        switches.forEach(s => {
            const row = tableBody.insertRow();
            row.innerHTML = `
                <td>${s.Name}</td>
                <td><span class="badge bg-info">${s.SwitchType}</span></td>
                <td>${s.Notes || '-'}</td>
                <td>
                    <button class="btn btn-sm btn-danger delete-vswitch" data-switch-name="${s.Name}"><i class="fas fa-trash-alt"></i></button>
                </td>
            `;
        });

        // Add event listeners for the new delete buttons
        document.querySelectorAll('.delete-vswitch').forEach(button => {
            button.addEventListener('click', async (e) => {
                const switchName = e.currentTarget.getAttribute('data-switch-name');
                if (confirm(`确定要删除虚拟交换机 "${switchName}" 吗？`)) {
                    await window.electronAPI.deleteVSwitch(switchName);
                    loadVSwitches();
                }
            });
        });

    } catch (error) {
        console.error('Failed to load vSwitches:', error);
        tableBody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">加载交换机失败: ${error}</td></tr>`;
    }
}

/**
 * Initializes the images page.
 */
function initImagesPage() {
    console.log("Images page loaded.");

    async function scanLocalImages() {
        const tableBody = document.querySelector('#local-images-table tbody');
        tableBody.innerHTML = '<tr><td colspan="3" class="text-center"><div class="spinner-border spinner-border-sm"></div> 扫描中...</td></tr>';
        
        const isoPath = await window.electronAPI.getSetting('localIsoPath');
        if (!isoPath) {
            tableBody.innerHTML = '<tr><td colspan="3" class="text-center">请先在“设置”页面指定本地镜像扫描路径。</td></tr>';
            return;
        }

        try {
            const images = await window.electronAPI.getLocalImages(isoPath);
            tableBody.innerHTML = '';
            if (!images || images.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="3" class="text-center">在指定目录未找到任何 .iso 文件。</td></tr>';
                return;
            }
            images.forEach(img => {
                const row = tableBody.insertRow();
                row.innerHTML = `
                    <td><i class="fas fa-compact-disc me-2"></i>${img.Name}</td>
                    <td>${img.Size}</td>
                    <td class="text-muted">${img.Path}</td>
                `;
            });
        } catch (error) {
            console.error('Failed to scan local images:', error);
            tableBody.innerHTML = `<tr><td colspan="3" class="text-center text-danger">扫描失败: ${error}</td></tr>`;
        }
    }

    async function displayOnlineImages() {
        const listContainer = document.getElementById('online-images-list');
        const images = await window.electronAPI.getOnlineImages();
        if (!images || images.length === 0) {
            listContainer.innerHTML = '<p class="text-muted">无法加载在线镜像列表。</p>';
            return;
        }
        listContainer.innerHTML = images.map(img => `
            <div class="col-md-6 mb-3">
                <div class="card h-100">
                    <div class="card-body">
                        <h5 class="card-title">${img.Name}</h5>
                        <h6 class="card-subtitle mb-2 text-muted">版本: ${img.Version} | 大小: ${img.Size}</h6>
                        <p class="card-text">${img.Description}</p>
                        <button class="btn btn-success download-btn" data-url="${img.DownloadUrl}"><i class="fas fa-download me-1"></i>获取</button>
                    </div>
                </div>
            </div>
        `).join('');

        // Add event listeners to new download buttons
        document.querySelectorAll('.download-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const url = e.currentTarget.dataset.url;
                window.electronAPI.openExternalLink(url);
            });
        });
    }

    document.getElementById('rescan-local-images').addEventListener('click', scanLocalImages);

    scanLocalImages();
    displayOnlineImages();
}

/**
 * Initializes the settings page.
 */
async function initSettingsPage() {
    console.log("Settings page loaded.");
    const isoPathInput = document.getElementById('local-iso-path');
    const browseBtn = document.getElementById('browse-iso-path');
    const saveBtn = document.getElementById('save-settings');
    const feedbackDiv = document.getElementById('settings-feedback');

    // Load existing setting
    const savedPath = await window.electronAPI.getSetting('localIsoPath');
    if (savedPath) {
        isoPathInput.value = savedPath;
    }

    // Handle browse button click
    browseBtn.addEventListener('click', async () => {
        const directoryPath = await window.electronAPI.selectDirectory();
        if (directoryPath) {
            isoPathInput.value = directoryPath;
        }
    });

    // Handle save button click
    saveBtn.addEventListener('click', async () => {
        const newPath = isoPathInput.value;
        await window.electronAPI.setSetting('localIsoPath', newPath);
        feedbackDiv.innerHTML = '<div class="alert alert-success">设置已保存！</div>';
        setTimeout(() => feedbackDiv.innerHTML = '', 3000);
    });
}

// --- VM Page Logic ---

async function handleVmAction(action) {
    if (!selectedVmName) return;
    // Show some visual feedback, e.g., a spinner
    console.log(`Performing action: ${action} on ${selectedVmName}`);
    await window.electronAPI[action](selectedVmName);
    loadVMs(); // Refresh the list after the action
}

function updateButtonStates() {
    const isVmSelected = selectedVmName !== null;
    const startBtn = document.getElementById('start-vm');
    if (startBtn) {
        startBtn.disabled = !isVmSelected;
        document.getElementById('shutdown-vm').disabled = !isVmSelected;
        document.getElementById('stop-vm').disabled = !isVmSelected;
        document.getElementById('delete-vm').disabled = !isVmSelected;
        document.getElementById('connect-vm').disabled = !isVmSelected;
        document.getElementById('settings-vm').disabled = !isVmSelected;
    }
}

async function loadVMs() {
    const vmsTableBody = document.querySelector('#vms-table tbody');
    if (!vmsTableBody) return;

    vmsTableBody.innerHTML = '<tr><td colspan="6" class="text-center"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div> 加载中...</td></tr>';
    selectedVmName = null;
    updateButtonStates();

    try {
        const vms = await window.electronAPI.getVMs();
        vmsTableBody.innerHTML = '';
        if (!vms || vms.length === 0) {
            vmsTableBody.innerHTML = '<tr><td colspan="6" class="text-center">未找到任何虚拟机。</td></tr>';
            return;
        }

        vms.forEach(vm => {
            const row = vmsTableBody.insertRow();
            row.dataset.vmName = vm.Name;
            row.className = vm.State === 'Running' ? 'table-success' : '';

            const uptime = vm.Uptime;
            let uptimeString = '-'; // Default if Uptime is not available or not an object
            if (uptime && typeof uptime === 'object') {
                const days = uptime.Days || 0;
                const hours = String(uptime.Hours || 0).padStart(2, '0');
                const minutes = String(uptime.Minutes || 0).padStart(2, '0');
                const seconds = String(uptime.Seconds || 0).padStart(2, '0');
                uptimeString = `${days > 0 ? `${days}天 ` : ''}${hours}:${minutes}:${seconds}`;
            }

            row.innerHTML = `
                <td>${vm.Name}</td>
                <td><span class="badge bg-${vm.State === 'Running' ? 'success' : 'secondary'}">${vm.State}</span></td>
                <td>${vm.CPUUsage || 0}</td>
                <td>${(vm.MemoryAssigned / (1024 * 1024)).toFixed(0)}</td>
                <td>${uptimeString}</td>
                <td>${vm.IPAddresses ? vm.IPAddresses.join(', ') : '-'}</td>
            `;
            row.addEventListener('click', () => {
                document.querySelectorAll('#vms-table tbody tr').forEach(r => r.classList.remove('selected'));
                row.classList.add('selected');
                selectedVmName = vm.Name;
                updateButtonStates();
            });

            // Right-click context menu
            row.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                document.querySelectorAll('#vms-table tbody tr').forEach(r => r.classList.remove('selected'));
                row.classList.add('selected');
                selectedVmName = vm.Name;
                updateButtonStates();

                const contextMenu = document.getElementById('context-menu');
                contextMenu.style.display = 'block';
                contextMenu.style.left = `${e.pageX}px`;
                contextMenu.style.top = `${e.pageY}px`;

                // Hide menu when clicking elsewhere
                document.addEventListener('click', () => {
                    contextMenu.style.display = 'none';
                }, { once: true });
            });
        });

        // Bind context menu actions
        document.getElementById('context-start').addEventListener('click', () => handleVmAction('startVM'));
        document.getElementById('context-shutdown').addEventListener('click', () => handleVmAction('shutdownVM'));
        document.getElementById('context-stop').addEventListener('click', () => handleVmAction('stopVM'));
        document.getElementById('context-settings').addEventListener('click', () => {
            const vmSettingsModal = new bootstrap.Modal(document.getElementById('vmSettingsModal'));
            document.getElementById('vm-settings-title').textContent = selectedVmName;
            window.electronAPI.getVSwitches().then(switches => {
                const switchSelect = document.getElementById('vm-network-switch');
                switchSelect.innerHTML = switches.map(s => `<option value="${s.Name}">${s.Name} (${s.SwitchType})</option>`).join('');
                vmSettingsModal.show();
            });
        });
        document.getElementById('context-delete').addEventListener('click', () => {
            if (selectedVmName && confirm(`您确定要删除虚拟机 ${selectedVmName} 吗？此操作将永久删除虚拟机及其所有数据，不可逆！`)) {
                handleVmAction('deleteVM');
            }
        });

    } catch (error) {
        console.error('Failed to load VMs:', error);
        vmsTableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">加载虚拟机失败: ${error}</td></tr>`;
    }
}

// --- Router Logic ---

const pageInitializers = {
    'vms.html': initVmsPage,
    'network.html': initNetworkPage,
    'images.html': initImagesPage,
    'settings.html': initSettingsPage,
};

async function loadPage(page) {
    const mainContent = document.getElementById('main-content');
    try {
        const response = await fetch(page);
        if (!response.ok) {
            throw new Error(`Failed to load page: ${response.statusText}`);
        }
        mainContent.innerHTML = await response.text();
        
        // Run the specific initializer for the loaded page
        if (pageInitializers[page]) {
            pageInitializers[page]();
        }
    } catch (error) {
        mainContent.innerHTML = `<div class="alert alert-danger">Error loading page: ${error.message}</div>`;
        console.error(error);
    }
}

// --- Global Initializer ---

document.addEventListener('DOMContentLoaded', () => {
    

    // Sidebar toggle functionality
    const sidebarToggle = document.body.querySelector('#sidebarToggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', event => {
            event.preventDefault();
            document.body.querySelector('#wrapper').classList.toggle('toggled');
        });
    }

    // Sidebar navigation
    const sidebarLinks = document.querySelectorAll('#sidebar-wrapper .list-group-item');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            const page = link.getAttribute('data-page');

            // Update active state
            sidebarLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            loadPage(page);
        });
    });

    // Load the default page on startup
    loadPage('vms.html');
});

// --- Wizard Logic ---
async function initWizard() {
    // Load wizard HTML into placeholder
    const wizardPlaceholder = document.getElementById('wizard-placeholder');
    try {
        const response = await fetch('wizard.html');
        wizardPlaceholder.innerHTML = await response.text();

        // Now that the HTML is loaded, initialize the logic
        const wizardModal = new bootstrap.Modal(document.getElementById('createVmWizardModal'));
        const tabs = document.querySelectorAll('#pills-tab .nav-link');
        const prevBtn = document.getElementById('wiz-prev-btn');
        const nextBtn = document.getElementById('wiz-next-btn');
        const finishBtn = document.getElementById('wiz-finish-btn');
        let currentStep = 0;

        function updateWizardControls() {
            prevBtn.style.display = currentStep === 0 ? 'none' : 'inline-block';
            nextBtn.style.display = currentStep === tabs.length - 1 ? 'none' : 'inline-block';
            finishBtn.style.display = currentStep === tabs.length - 1 ? 'inline-block' : 'none';
        }

        function goToStep(step) {
            new bootstrap.Tab(tabs[step]).show();
            currentStep = step;
            updateWizardControls();
        }

        prevBtn.addEventListener('click', () => goToStep(currentStep - 1));
        nextBtn.addEventListener('click', () => {
            // Add validation logic here if needed
            if (currentStep === tabs.length - 2) { // Moving to summary step
                populateWizardSummary();
            }
            goToStep(currentStep + 1);
        });

        document.getElementById('createVmWizardModal').addEventListener('show.bs.modal', async () => {
            // Reset to first step and populate dynamic data
            goToStep(0);
            document.getElementById('create-switch-form').reset();
            document.getElementById('wiz-creation-status').innerHTML = '';

            // Populate network switches
            const switches = await window.electronAPI.getVSwitches();
            const switchSelect = document.getElementById('wiz-network-switch');
            switchSelect.innerHTML = switches.map(s => `<option value="${s.Name}">${s.Name} (${s.SwitchType})</option>`).join('');

            // Populate ISOs
            const isoPath = await window.electronAPI.getSetting('localIsoPath');
            const isoSelect = document.getElementById('wiz-iso-path');
            if (isoPath) {
                const isos = await window.electronAPI.getLocalImages(isoPath);
                isoSelect.innerHTML = '<option value="">稍后安装操作系统</option>' + isos.map(i => `<option value="${i.Path}">${i.Name}</option>`).join('');
            }
        });

        document.getElementById('wiz-browse-path').addEventListener('click', async () => {
            const path = await window.electronAPI.selectDirectory();
            if (path) document.getElementById('wiz-vm-path').value = path;
        });

        finishBtn.addEventListener('click', handleFinishWizard);

    } catch (error) {
        console.error("Failed to load wizard:", error);
        wizardPlaceholder.innerHTML = '<p class="text-danger">Failed to load VM creation wizard.</p>';
    }
}

function populateWizardSummary() {
    const summaryList = document.getElementById('wiz-summary-list');
    const vmDetails = getVmDetailsFromWizard();
    summaryList.innerHTML = `
        <li class="list-group-item"><b>名称:</b> ${vmDetails.name}</li>
        <li class="list-group-item"><b>路径:</b> ${vmDetails.path}</li>
        <li class="list-group-item"><b>内存:</b> ${vmDetails.memory} MB</li>
        <li class="list-group-item"><b>CPU:</b> ${vmDetails.cpu} 核心</li>
        <li class="list-group-item"><b>硬盘大小:</b> ${vmDetails.diskSize} GB</li>
        <li class="list-group-item"><b>网络:</b> ${vmDetails.switchName}</li>
        <li class="list-group-item"><b>安全启动:</b> ${vmDetails.secureBoot ? '启用' : '禁用'}</li>
        <li class="list-group-item"><b>安装介质:</b> ${vmDetails.isoPath || '无'}</li>
    `;
}

function getVmDetailsFromWizard() {
    return {
        name: document.getElementById('wiz-vm-name').value,
        path: document.getElementById('wiz-vm-path').value,
        memory: document.getElementById('wiz-memory').value,
        cpu: document.getElementById('wiz-cpu').value,
        diskSize: document.getElementById('wiz-disk-size').value,
        switchName: document.getElementById('wiz-network-switch').value,
        isoPath: document.getElementById('wiz-iso-path').value,
        secureBoot: document.getElementById('wiz-secure-boot').checked,
    };
}

async function handleFinishWizard() {
    const vmDetails = getVmDetailsFromWizard();
    const statusDiv = document.getElementById('wiz-creation-status');

    if (!vmDetails.name || !vmDetails.path) {
        statusDiv.innerHTML = '<div class="alert alert-danger">虚拟机名称和存储路径不能为空！</div>';
        return;
    }

    statusDiv.innerHTML = '<div class="alert alert-info"><div class="spinner-border spinner-border-sm"></div> 正在创建虚拟机，请稍候...</div>';

    try {
        const success = await window.electronAPI.createVM(vmDetails);
        if (success) {
            statusDiv.innerHTML = '<div class="alert alert-success">虚拟机创建成功！</div>';
            // Close modal after a delay and refresh VM list
            setTimeout(() => {
                bootstrap.Modal.getInstance(document.getElementById('createVmWizardModal')).hide();
                loadVMs();
            }, 2000);
        } else {
            throw new Error('PowerShell script returned failure.');
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger">创建失败: ${error.message}</div>`;
        console.error("VM creation failed:", error);
    }
}

