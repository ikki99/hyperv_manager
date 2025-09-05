const { exec } = require('child_process');
const sudo = require('sudo-prompt');

class PowerShellService {
    /**
     * Executes a PowerShell command with administrator privileges and returns its output.
     * @param {string} command The PowerShell command to execute.
     * @returns {Promise<string>}
     */
    executePowerShellCommand(command) {
        const encodedCommand = Buffer.from(command, 'utf16le').toString('base64');
        const fullCommand = `powershell.exe -EncodedCommand ${encodedCommand}`;

        const options = {
            name: 'HyperV Manager'
        };

        return new Promise((resolve, reject) => {
            sudo.exec(fullCommand, options, (error, stdout, stderr) => {
                if (error) {
                    console.error(`sudo-prompt error: ${error}`);
                    reject(error.message || stderr);
                    return;
                }
                if (stderr) {
                    console.warn(`PowerShell stderr: ${stderr}`);
                }
                resolve(stdout);
            });
        });
    }

    /**
     * Gets a list of Hyper-V VMs.
     * @returns {Promise<Array<Object>>}
     */
    async getVMs() {
        const command = 'Get-VM | Select-Object Name, State, Uptime, MemoryAssigned, CPUUsage, GuestOS | ConvertTo-Json -Compress';
        try {
            const jsonOutput = await this.executePowerShellCommand(command);
            // PowerShell's ConvertTo-Json might output an array of objects or a single object.
            // Handle both cases.
            const data = JSON.parse(jsonOutput);
            return Array.isArray(data) ? data : [data];
        } catch (error) {
            console.error('Error getting VMs:', error);
            return [];
        }
    }

    /**
     * Executes a PowerShell command to start a VM.
     * @param {string} vmName The name of the VM to start.
     * @returns {Promise<boolean>}
     */
    async startVM(vmName) {
        const command = `Start-VM -Name "${vmName}"`;
        try {
            await this.executePowerShellCommand(command);
            return true;
        } catch (error) {
            console.error(`Error starting VM ${vmName}:`, error);
            return false;
        }
    }

    /**
     * Executes a PowerShell command to shut down a VM.
     * @param {string} vmName The name of the VM to shut down.
     * @returns {Promise<boolean>}
     */
    async shutdownVM(vmName) {
        const command = `Stop-VM -Name "${vmName}"`; // Graceful shutdown without params
        try {
            await this.executePowerShellCommand(command);
            return true;
        } catch (error) {
            console.error(`Error shutting down VM ${vmName}:`, error);
            return false;
        }
    }

    /**
     * Executes a PowerShell command to stop a VM.
     * @param {string} vmName The name of the VM to stop.
     * @returns {Promise<boolean>}
     */
    async stopVM(vmName) {
        const command = `Stop-VM -Name "${vmName}" -Force`;
        try {
            await this.executePowerShellCommand(command);
            return true;
        } catch (error) {
            console.error(`Error stopping VM ${vmName}:`, error);
            return false;
        }
    }

    /**
     * Executes a PowerShell command to delete a VM.
     * @param {string} vmName The name of the VM to delete.
     * @returns {Promise<boolean>}
     */
    async deleteVM(vmName) {
        // Ensure VM is off before deleting
        await this.stopVM(vmName);
        const command = `Remove-VM -Name "${vmName}" -Force`;
        try {
            await this.executePowerShellCommand(command);
            return true;
        } catch (error) {
            console.error(`Error deleting VM ${vmName}:`, error);
            return false;
        }
    }

    /**
     * Connects to a VM using vmconnect.exe.
     * @param {string} vmName The name of the VM to connect to.
     */
    connectVM(vmName) {
        const command = `vmconnect.exe localhost "${vmName}"`;
        const options = {
            name: 'HyperV Manager'
        };
        sudo.exec(command, options, (error) => {
            if (error) {
                console.error(`Error connecting to VM ${vmName}: ${error}`);
            }
        });
    }

    /**
     * Gets a list of physical network adapters.
     * @returns {Promise<Array<Object>>}
     */
    async getNetAdapters() {
        const command = 'Get-NetAdapter -Physical | Select-Object Name, InterfaceDescription | ConvertTo-Json -Compress';
        try {
            const jsonOutput = await this.executePowerShellCommand(command);
            const data = JSON.parse(jsonOutput);
            return Array.isArray(data) ? data : [data];
        } catch (error) {
            console.error('Error getting network adapters:', error);
            return [];
        }
    }

    /**
     * Sets the virtual switch for a VM's network adapter.
     * @param {string} vmName The name of the VM.
     * @param {string} switchName The name of the virtual switch.
     * @returns {Promise<boolean>}
     */
    async setVMNetworkAdapter(vmName, switchName) {
        const command = `Set-VMNetworkAdapter -VMName "${vmName}" -SwitchName "${switchName}"`;
        try {
            await this.executePowerShellCommand(command);
            return true;
        } catch (error) {
            console.error(`Error setting network adapter for VM ${vmName}:`, error);
            return false;
        }
    }

    /**
     * Gets a list of NAT networks.
     * @returns {Promise<Array<Object>>}
     */
    async getNatNetworks() {
        const command = '@(Get-NetNat) | Select-Object Name, InternalIPInterfaceAddressPrefix | ConvertTo-Json -Compress';
        try {
            const jsonOutput = await this.executePowerShellCommand(command);
            const data = JSON.parse(jsonOutput);
            return Array.isArray(data) ? data : [data];
        } catch (error) {
            console.error('Error getting NAT networks:', error);
            return [];
        }
    }

    /**
     * Gets a list of Hyper-V virtual switches.
     * @returns {Promise<Array<Object>>}
     */
    async getVSwitches() {
        const command = '@(Get-VMSwitch) | Select-Object Name, SwitchType, Notes | ConvertTo-Json -Compress';
        try {
            const jsonOutput = await this.executePowerShellCommand(command);
            const data = JSON.parse(jsonOutput);
            return Array.isArray(data) ? data : [data];
        } catch (error) {
            console.error('Error getting vSwitches:', error);
            return [];
        }
    }

    /**
     * Creates a Hyper-V virtual switch.
     * @param {string} name The name of the new switch.
     * @param {string} type The type of the switch (External, Internal, Private).
     * @param {string} [netAdapterName] The network adapter name for External switches.
     * @returns {Promise<boolean>}
     */
    async createVSwitch(name, type, netAdapterName = null) {
        let command = `New-VMSwitch -Name "${name}" -SwitchType ${type}`;
        if (type === 'External' && netAdapterName) {
            command += ` -NetAdapterName "${netAdapterName}"`;
        }
        try {
            await this.executePowerShellCommand(command);
            return true;
        } catch (error) {
            console.error(`Error creating vSwitch ${name}:`, error);
            return false;
        }
    }

    /**
     * Deletes a Hyper-V virtual switch.
     * @param {string} name The name of the switch to delete.
     * @returns {Promise<boolean>}
     */
    async deleteVSwitch(name) {
        const command = `Remove-VMSwitch -Name "${name}" -Force`;
        try {
            await this.executePowerShellCommand(command);
            return true;
        } catch (error) {
            console.error(`Error deleting vSwitch ${name}:`, error);
            return false;
        }
    }

    /**
     * Gets NAT rules for a given NAT network.
     * @param {string} natName The name of the NAT network.
     * @returns {Promise<Array<Object>>}
     */
    async getNatRules(natName) {
        const command = `Get-NetNatStaticMapping -NatName "${natName}" | Select-Object Protocol, ExternalPort, InternalIPAddress, InternalPort | ConvertTo-Json -Compress`;
        try {
            const jsonOutput = await this.executePowerShellCommand(command);
            const data = JSON.parse(jsonOutput);
            return Array.isArray(data) ? data : [data];
        } catch (error) {
            console.error(`Error getting NAT rules for ${natName}:`, error);
            return [];
        }
    }

    /**
     * Adds a NAT rule.
     * @param {string} natName The name of the NAT network.
     * @param {string} protocol The protocol (TCP/UDP).
     * @param {number} externalPort The external port.
     * @param {string} internalIp The internal IP address.
     * @param {number} internalPort The internal port.
     * @returns {Promise<boolean>}
     */
    async addNatRule(natName, protocol, externalPort, internalIp, internalPort) {
        const command = `Add-NetNatStaticMapping -NatName "${natName}" -Protocol ${protocol} -ExternalIPAddress 0.0.0.0 -ExternalPort ${externalPort} -InternalIPAddress "${internalIp}" -InternalPort ${internalPort}`;
        try {
            await this.executePowerShellCommand(command);
            return true;
        } catch (error) {
            console.error(`Error adding NAT rule to ${natName}:`, error);
            return false;
        }
    }

    /**
     * Removes a NAT rule.
     * @param {string} natName The name of the NAT network.
     * @param {string} protocol The protocol (TCP/UDP).
     * @param {number} externalPort The external port.
     * @returns {Promise<boolean>}
     */
    async removeNatRule(natName, protocol, externalPort) {
        const command = `Get-NetNatStaticMapping -NatName "${natName}" | Where-Object { $_.Protocol -eq '${protocol}' -and $_.ExternalPort -eq ${externalPort} } | Remove-NetNatStaticMapping -Confirm:$false`;
        try {
            await this.executePowerShellCommand(command);
            return true;
        } catch (error) {
            console.error(`Error removing NAT rule from ${natName}:`, error);
            return false;
        }
    }

    /**
     * Creates a NAT network.
     * @param {string} name The name of the NAT network.
     * @param {string} internalIpInterfaceAddressPrefix The internal IP address prefix (e.g., '192.168.100.0/24').
     * @returns {Promise<boolean>}
     */
    async createNatNetwork(name, internalIpInterfaceAddressPrefix) {
        const command = `New-NetNat -Name "${name}" -InternalIPInterfaceAddressPrefix ${internalIpInterfaceAddressPrefix}`;
        try {
            await this.executePowerShellCommand(command);
            return true;
        } catch (error) {
            console.error(`Error creating NAT network ${name}:`, error);
            return false;
        }
    }

    /**
     * Sets the IP address for a vSwitch.
     * @param {string} switchName The name of the vSwitch.
     * @param {string} ipAddress The IP address.
     * @param {string} prefixLength The prefix length.
     * @returns {Promise<boolean>}
     */
    async setVSwitchIP(switchName, ipAddress, prefixLength) {
        const adapterName = `vEthernet (${switchName})`;
        const command = `Get-NetAdapter -Name '${adapterName}' | New-NetIPAddress -IPAddress ${ipAddress} -PrefixLength ${prefixLength}`;
        try {
            await this.executePowerShellCommand(command);
            return true;
        } catch (error) {
            console.error(`Error setting IP for vSwitch ${switchName}:`, error);
            return false;
        }
    }

    /**
     * Sets the ISO path for a VM's DVD drive.
     * @param {string} vmName The name of the VM.
     * @param {string} isoPath The local path to the ISO file. Pass null or empty string to eject.
     * @returns {Promise<boolean>}
     */
    async setVMDvdDrive(vmName, isoPath) {
        const command = `Set-VMDvdDrive -VMName "${vmName}" -Path ${isoPath ? `"${isoPath}"` : '""'}`;
        try {
            await this.executePowerShellCommand(command);
            return true;
        } catch (error) {
            console.error(`Error setting DVD drive for VM ${vmName}:`, error);
            return false;
        }
    }

    /**
     * Invokes a command inside a VM using PowerShell Direct.
     * @param {string} vmName The name of the VM.
     * @param {string} username The username for the VM.
     * @param {string} password The password for the VM.
     * @param {string} command The command to execute inside the VM.
     * @returns {Promise<string>}
     */
    async invokeCommandInVM(vmName, username, password, command) {
        const script = `
            $vm_name = "${vmName}"
            $username = "${username}"
            $password = ConvertTo-SecureString -String "${password}" -AsPlainText -Force
            $cred = New-Object System.Management.Automation.PSCredential($username, $password)
            
            try {
                $result = Invoke-Command -VMName $vm_name -Credential $cred -ScriptBlock { ${command} }
                Write-Output $result
            } catch {
                Write-Error $_.Exception.Message
            }
        `;
        try {
            const output = await this.executePowerShellCommand(script);
            return output;
        } catch (error) {
            console.error(`Error invoking command in VM ${vmName}:`, error);
            return `Error: ${error}`;
        }
    }

    /**
     * Checks if Hyper-V is enabled.
     * @returns {Promise<boolean>}
     */
    async checkHyperVStatus() {
        const command = '(Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All).State -eq \'Enabled\'';
        try {
            const output = await this.executePowerShellCommand(command);
            return output.trim() === 'True';
        } catch (error) {
            console.error('Error checking Hyper-V status:', error);
            return false;
        }
    }

    /**
     * Installs Hyper-V.
     * @returns {Promise<boolean>}
     */
    async installHyperV() {
        const command = 'Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -All -NoRestart';
        try {
            await this.executePowerShellCommand(command);
            return true;
        } catch (error) {
            console.error(`Error installing Hyper-V:`, error);
            return false;
        }
    }

    /**
     * Gets details of a VM's network adapter.
     * @param {string} vmName The name of the VM.
     * @returns {Promise<Object|null>}
     */
    async getVMNetworkAdapterDetails(vmName) {
        const command = `Get-VMNetworkAdapter -VMName "${vmName}" | Select-Object Name, SwitchName, MacAddress, IPAddresses | ConvertTo-Json -Compress`;
        try {
            const jsonOutput = await this.executePowerShellCommand(command);
            if (!jsonOutput) return null;
            const data = JSON.parse(jsonOutput);
            return Array.isArray(data) ? data[0] : data; // Assuming one network adapter for simplicity
        } catch (error) {
            console.error(`Error getting network adapter details for VM ${vmName}:`, error);
            return null;
        }
    }

    /**
     * Gets a list of online images (hardcoded for now).
     * @returns {Array<Object>}
     */
    getOnlineImages() {
        return [
            { Name: 'Windows 11 Dev', Version: '22H2', Size: '4.5 GB', Description: 'Latest developer build from the Insider Program.', DownloadUrl: 'https://www.microsoft.com/software-download/windows11' },
            { Name: 'Ubuntu Server LTS', Version: '22.04', Size: '1.8 GB', Description: 'Long-term support version of Ubuntu Server.', DownloadUrl: 'https://ubuntu.com/download/server' },
        ];
    }

    /**
     * Scans a local path for ISO images.
     * @param {string} path The path to scan.
     * @returns {Promise<Array<Object>>}
     */
    async getLocalImages(path) {
        const command = `Get-ChildItem -Path "${path}" -Filter "*.iso" -Recurse | Select-Object Name, FullName, Length | ConvertTo-Json -Compress`;
        try {
            const jsonOutput = await this.executePowerShellCommand(command);
            if (!jsonOutput) return []; // Handle empty output
            const data = JSON.parse(jsonOutput);
            const dataArray = Array.isArray(data) ? data : [data]; // Ensure it's always an array
            return dataArray.map(f => ({ Name: f.Name, Path: f.FullName, Size: `${(f.Length / (1024 * 1024 * 1024)).toFixed(2)} GB` }));
        } catch (error) {
            console.error(`Error scanning local images in ${path}:`, error);
            return [];
        }
    }

    /**
     * Creates a new VM.
     * @param {string} vmName
     * @param {number} memoryMB
     * @param {number} cpuCores
     * @param {string} vmPath
     * @param {number} diskSizeGB
     * @param {string} vSwitchName
     * @param {string} isoPath
     * @param {string} existingDiskPath
     * @param {boolean} secureBootEnabled
     * @returns {Promise<boolean>}
     */
    async createVM(vmName, memoryMB, cpuCores, vmPath, diskSizeGB, vSwitchName, isoPath, existingDiskPath, secureBootEnabled) {
        const vhdxPath = `${vmPath}\\${vmName}.vhdx`;
        // Command to create the VM, set memory, and processor count
        let command = `New-VM -Name "${vmName}" -MemoryStartupBytes ${memoryMB}MB -Generation 2 -Path "${vmPath}"; Set-VMProcessor -VMName "${vmName}" -Count ${cpuCores};`;

        // Command to create a new VHD and add it
        if (!existingDiskPath) {
            command += ` New-VHD -Path "${vhdxPath}" -SizeBytes ${diskSizeGB}GB; Add-VMHardDiskDrive -VMName "${vmName}" -Path "${vhdxPath}";`;
        } else {
            command += ` Add-VMHardDiskDrive -VMName "${vmName}" -Path "${existingDiskPath}";`;
        }

        // Command to add network adapter
        if (vSwitchName) {
            command += ` Connect-VMNetworkAdapter -VMName "${vmName}" -SwitchName "${vSwitchName}";`;
        }

        // Command for secure boot
        if (secureBootEnabled) {
            command += ` Set-VMFirmware -VMName "${vmName}" -EnableSecureBoot On -SecureBootTemplate MicrosoftWindows;`;
        }

        // Command to add DVD drive
        if (isoPath) {
            command += ` Add-VMDvdDrive -VMName "${vmName}" -Path "${isoPath}";`;
        }

        try {
            await this.executePowerShellCommand(command);
            return true;
        } catch (error) {
            console.error(`Error creating VM ${vmName}:`, error);
            return false;
        }
    }
}

module.exports = PowerShellService;