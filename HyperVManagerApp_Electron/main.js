const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const PowerShellService = require('./powershell-service');
const Store = require('electron-store');

const fs = require('fs').promises;

const psService = new PowerShellService();
const store = new Store();

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1000,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadFile('index.html');

  // Open the DevTools.
   mainWindow.webContents.openDevTools();
}

app.whenReady().then(() => {
  createWindow();

  // IPC Handlers
  ipcMain.handle('get-vms', async () => {
    return await psService.getVMs();
  });

  ipcMain.handle('start-vm', async (event, vmName) => {
    return await psService.startVM(vmName);
  });

  ipcMain.handle('shutdown-vm', async (event, vmName) => {
    return await psService.shutdownVM(vmName);
  });

  ipcMain.handle('stop-vm', async (event, vmName) => {
    return await psService.stopVM(vmName);
  });

  ipcMain.handle('delete-vm', async (event, vmName) => {
    return await psService.deleteVM(vmName);
  });

  ipcMain.handle('connect-vm', async (event, vmName) => {
    return await psService.connectVM(vmName);
  });

  // Network IPC Handlers
  ipcMain.handle('get-vswitches', async () => {
    return await psService.getVSwitches();
  });

  ipcMain.handle('create-vswitch', async (event, name, type, netAdapter) => {
    return await psService.createVSwitch(name, type, netAdapter);
  });

  ipcMain.handle('delete-vswitch', async (event, name) => {
    return await psService.deleteVSwitch(name);
  });

  ipcMain.handle('get-net-adapters', async () => {
    return await psService.getNetAdapters();
  });

  // Settings IPC Handlers
  ipcMain.handle('settings:get', (event, key) => {
    return store.get(key);
  });

  ipcMain.handle('settings:set', (event, key, value) => {
    store.set(key, value);
  });

  ipcMain.handle('dialog:openDirectory', async () => {
    const { canceled, filePaths } = await dialog.showOpenDialog({
        properties: ['openDirectory']
    });
    if (canceled) {
        return null;
    } else {
        return filePaths[0];
    }
  });

  // Image Management IPC Handlers
  ipcMain.handle('images:getLocal', async (event, path) => {
      if (!path) return [];
      return await psService.getLocalImages(path);
  });

  ipcMain.handle('images:getOnline', async () => {
      try {
          const repoPath = path.join(app.getAppPath(), '..', 'online_images_repository.json');
          const data = await fs.readFile(repoPath, 'utf-8');
          return JSON.parse(data);
      } catch (error) {
          console.error("Failed to read online image repository:", error);
          return []; // Return empty on error
      }
  });

  // Wizard IPC Handlers
  ipcMain.handle('wizard:create-vm', async (event, vmDetails) => {
      const { name, path, memory, cpu, diskSize, switchName, isoPath, secureBoot } = vmDetails;
      return await psService.createVM(name, memory, cpu, path, diskSize, switchName, isoPath, null, secureBoot);
  });

  ipcMain.handle('vm:set-network-adapter', async (event, vmName, switchName) => {
      return await psService.setVMNetworkAdapter(vmName, switchName);
  });

  // NAT IPC Handlers
  ipcMain.handle('nat:get-networks', async () => {
      return await psService.getNatNetworks();
  });
  ipcMain.handle('nat:get-rules', async (event, natName) => {
      return await psService.getNatRules(natName);
  });
  ipcMain.handle('nat:add-rule', async (event, rule) => {
      return await psService.addNatRule(rule.natName, rule.protocol, rule.externalPort, rule.internalIp, rule.internalPort);
  });
  ipcMain.handle('nat:remove-rule', async (event, rule) => {
      return await psService.removeNatRule(rule.natName, rule.protocol, rule.externalPort);
  });

  ipcMain.handle('shell:open-external', (event, url) => {
      shell.openExternal(url);
  });

  ipcMain.handle('vm:invoke-command', async (event, vmName, username, password, command) => {
      return await psService.invokeCommandInVM(vmName, username, password, command);
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});