const { contextBridge, ipcRenderer } = require('electron');

// Expose a secure API to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  getVMs: () => ipcRenderer.invoke('get-vms'),
  startVM: (vmName) => ipcRenderer.invoke('start-vm', vmName),
  shutdownVM: (vmName) => ipcRenderer.invoke('shutdown-vm', vmName),
  stopVM: (vmName) => ipcRenderer.invoke('stop-vm', vmName),
  deleteVM: (vmName) => ipcRenderer.invoke('delete-vm', vmName),
  connectVM: (vmName) => ipcRenderer.invoke('connect-vm', vmName),
  // Network related APIs
  getVSwitches: () => ipcRenderer.invoke('get-vswitches'),
  createVSwitch: (name, type, netAdapter) => ipcRenderer.invoke('create-vswitch', name, type, netAdapter),
  deleteVSwitch: (name) => ipcRenderer.invoke('delete-vswitch', name),
  getNetAdapters: () => ipcRenderer.invoke('get-net-adapters'),
  // Settings and Dialog APIs
  selectDirectory: () => ipcRenderer.invoke('dialog:openDirectory'),
  getSetting: (key) => ipcRenderer.invoke('settings:get', key),
  setSetting: (key, value) => ipcRenderer.invoke('settings:set', key, value),
  // Image Management APIs
  getLocalImages: (path) => ipcRenderer.invoke('images:getLocal', path),
  getOnlineImages: () => ipcRenderer.invoke('images:getOnline'),
  // Wizard APIs
  createVM: (vmDetails) => ipcRenderer.invoke('wizard:create-vm', vmDetails),
  setVMNetworkAdapter: (vmName, switchName) => ipcRenderer.invoke('vm:set-network-adapter', vmName, switchName),
  // NAT APIs
  getNatNetworks: () => ipcRenderer.invoke('nat:get-networks'),
  getNatRules: (natName) => ipcRenderer.invoke('nat:get-rules', natName),
  addNatRule: (ruleDetails) => ipcRenderer.invoke('nat:add-rule', ruleDetails),
  removeNatRule: (ruleDetails) => ipcRenderer.invoke('nat:remove-rule', ruleDetails),
  openExternalLink: (url) => ipcRenderer.invoke('shell:open-external', url),
  invokeCommandInVM: (vmName, username, password, command) => ipcRenderer.invoke('vm:invoke-command', vmName, username, password, command),
});
