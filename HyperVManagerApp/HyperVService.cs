using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Management.Automation;
using System.Collections.ObjectModel;
using System.Diagnostics;

namespace HyperVManager
{
    public class HyperVService
    {
        public async Task<List<VM>> GetVMsAsync()
        {
            List<VM> vms = new List<VM>();
            using (PowerShell ps = PowerShell.Create())
            {
                ps.AddCommand("Get-VM");
                Collection<PSObject> results = await Task.Run(() => ps.Invoke());

                foreach (PSObject psObject in results)
                {
                    VM vm = new VM
                    {
                        Name = psObject.Members["Name"].Value?.ToString(),
                        State = (int)psObject.Members["State"].Value,
                        Uptime = (TimeSpan)psObject.Members["Uptime"].Value,
                        MemoryAssigned = (long)psObject.Members["MemoryAssigned"].Value,
                        CPUUsage = (int)psObject.Members["CPUUsage"].Value,
                        GuestOS = psObject.Members["GuestOS"].Value?.ToString()
                    };

                    // Handle IPAddresses (which is a collection of strings in PowerShell)
                    if (psObject.Members["NetworkAdapters"]?.Value is Collection<PSObject> networkAdapters)
                    {
                        foreach (PSObject adapter in networkAdapters)
                        {
                            if (adapter.Members["IPAddresses"]?.Value is Collection<string> ipAddresses)
                            {
                                vm.IPAddresses.AddRange(ipAddresses);
                            }
                        }
                    }
                    vms.Add(vm);
                }
            }
            return vms;
        }

        public async Task<bool> StartVMAsync(string vmName)
        {
            return await ExecutePowerShellCommandAsync($"Start-VM -Name \"{vmName}\"");
        }

        public async Task<bool> ShutdownVMAsync(string vmName)
        {
            return await ExecutePowerShellCommandAsync($"Shutdown-VM -Name \"{vmName}\" -Force");
        }

        public async Task<bool> StopVMAsync(string vmName)
        {
            return await ExecutePowerShellCommandAsync($"Stop-VM -Name \"{vmName}\" -Force");
        }

        public async Task<bool> DeleteVMAsync(string vmName)
        {
            // Stop VM first, then remove
            await StopVMAsync(vmName); // Ensure it's stopped before deleting
            return await ExecutePowerShellCommandAsync($"Remove-VM -Name \"{vmName}\" -Force");
        }

        public void ConnectVM(string vmName)
        {
            // vmconnect.exe is a separate process, no need for PowerShell here
            Process.Start(new ProcessStartInfo
            {
                FileName = "vmconnect.exe",
                Arguments = $"localhost \"{vmName}\"",
                UseShellExecute = true
            });
        }

        public async Task<List<VSwitch>> GetVSwitchesAsync()
        {
            List<VSwitch> vswitches = new List<VSwitch>();
            using (PowerShell ps = PowerShell.Create())
            {
                ps.AddCommand("Get-VMSwitch");
                Collection<PSObject> results = await Task.Run(() => ps.Invoke());

                foreach (PSObject psObject in results)
                {
                    VSwitch vswitch = new VSwitch
                    {
                        Name = psObject.Members["Name"].Value?.ToString(),
                        SwitchType = psObject.Members["SwitchType"].Value?.ToString(),
                        Notes = psObject.Members["Notes"].Value?.ToString()
                    };

                    // Get IP address for Internal switches
                    if (vswitch.SwitchType == "Internal")
                    {
                        using (PowerShell ipPs = PowerShell.Create())
                        {
                            ipPs.AddScript($"Get-NetAdapter -Name 'vEthernet ({vswitch.Name})' | Get-NetIPAddress -AddressFamily IPv4 | Select-Object IPAddress | ConvertTo-Json -Compress");
                            Collection<PSObject> ipResults = await Task.Run(() => ipPs.Invoke());
                            if (ipResults.Any() && ipResults.First().BaseObject is string jsonIp)
                            {
                                // This is a simplified parsing. In a real app, use a JSON deserializer.
                                // Example: {"IPAddress":"192.168.1.1"}
                                var ipMatch = System.Text.RegularExpressions.Regex.Match(jsonIp, "\"IPAddress\":\"([^\"]+)\"");
                                if (ipMatch.Success)
                                {
                                    vswitch.IPAddress = ipMatch.Groups[1].Value;
                                }
                            }
                        }

                        // Check NAT status
                        using (PowerShell natPs = PowerShell.Create())
                        {
                            natPs.AddScript($"Get-NetNat -Name \"{vswitch.Name}\" | Select-Object Name | ConvertTo-Json -Compress");
                            Collection<PSObject> natResults = await Task.Run(() => natPs.Invoke());
                            vswitch.NatStatus = natResults.Any() ? "已启用" : "未启用";
                        }
                    }
                    vswitches.Add(vswitch);
                }
            }
            return vswitches;
        }

        public async Task<bool> CreateVSwitchAsync(string name, string type, string netAdapterName = null)
        {
            string command = $"New-VMSwitch -Name \"{name}\" -SwitchType {type}";
            if (type == "External" && !string.IsNullOrEmpty(netAdapterName))
            {
                command += $" -NetAdapterName \"{netAdapterName}\"";
            }
            return await ExecutePowerShellCommandAsync(command);
        }

        public async Task<bool> DeleteVSwitchAsync(string name)
        {
            return await ExecutePowerShellCommandAsync($"Remove-VMSwitch -Name \"{name}\" -Force");
        }

        public async Task<List<NatRule>> GetNatRulesAsync(string natName)
        {
            List<NatRule> rules = new List<NatRule>();
            using (PowerShell ps = PowerShell.Create())
            {
                ps.AddScript($"Get-NetNatStaticMapping -NatName \"{natName}\" | Select-Object Protocol, ExternalPort, InternalIPAddress, InternalPort | ConvertTo-Json -Compress");
                Collection<PSObject> results = await Task.Run(() => ps.Invoke());

                foreach (PSObject psObject in results)
                {
                    // This is a simplified parsing. In a real app, use a JSON deserializer.
                    // Example: {\"Protocol\":\"TCP\",\"ExternalPort\":80,\"InternalIPAddress\":\"192.168.1.100\",\"InternalPort\":8080}
                    string jsonString = psObject.BaseObject?.ToString();
                    if (!string.IsNullOrEmpty(jsonString))
                    {
                        // Basic regex parsing for demonstration. Highly recommend a JSON library.
                        var protocolMatch = System.Text.RegularExpressions.Regex.Match(jsonString, "\"Protocol\":\"([^\"]+)\"");
                        var extPortMatch = System.Text.RegularExpressions.Regex.Match(jsonString, "\"ExternalPort\":(\\d+)");
                        var intIpMatch = System.Text.RegularExpressions.Regex.Match(jsonString, "\"InternalIPAddress\":\"([^\"]+)\"");
                        var intPortMatch = System.Text.RegularExpressions.Regex.Match(jsonString, "\"InternalPort\":(\\d+)");

                        if (protocolMatch.Success && extPortMatch.Success && intIpMatch.Success && intPortMatch.Success)
                        {
                            rules.Add(new NatRule
                            {
                                Protocol = protocolMatch.Groups[1].Value,
                                ExternalPort = int.Parse(extPortMatch.Groups[1].Value),
                                InternalIPAddress = intIpMatch.Groups[1].Value,
                                InternalPort = int.Parse(intPortMatch.Groups[1].Value)
                            });
                        }
                    }
                }
            }
            return rules;
        }

        public async Task<bool> AddNatRuleAsync(string natName, string protocol, int externalPort, string internalIp, int internalPort)
        {
            string command = $"Add-NetNatStaticMapping -NatName \"{natName}\" -Protocol {protocol} -ExternalIPAddress 0.0.0.0 -ExternalPort {externalPort} -InternalIPAddress \"{internalIp}\" -InternalPort {internalPort}";
            return await ExecutePowerShellCommandAsync(command);
        }

        public async Task<bool> RemoveNatRuleAsync(string natName, string protocol, int externalPort)
        {
            string command = $"Remove-NetNatStaticMapping -NatName \"{natName}\" -StaticMapping (Get-NetNatStaticMapping -NatName \"{natName}\" | Where-Object {{ $_.Protocol -eq '{protocol}' -and $_.ExternalPort -eq {externalPort} }}) -Confirm:$false";
            return await ExecutePowerShellCommandAsync(command);
        }

        public async Task<bool> CreateNatNetworkAsync(string name, string internalIpInterfaceAddressPrefix)
        {
            string command = $"New-NetNat -Name \"{name}\" -InternalIPInterfaceAddressPrefix {internalIpInterfaceAddressPrefix}";
            return await ExecutePowerShellCommandAsync(command);
        }

        public async Task<bool> SetVSwitchIPAsync(string switchName, string ipAddress, string prefixLength)
        {
            string adapterName = $"vEthernet ({switchName})";
            string command = $"Get-NetAdapter -Name '{adapterName}' | New-NetIPAddress -IPAddress {ipAddress} -PrefixLength {prefixLength}";
            return await ExecutePowerShellCommandAsync(command);
        }

        public async Task<string> InvokeCommandInVMAsync(string vmName, string username, string password, string command)
        {
            using (PowerShell ps = PowerShell.Create())
            {
                // Construct the PowerShell Direct command
                string script = $"\n                    $vm_name = \"{vmName}\"\n                    $username = \"{username}\"\n                    $password = ConvertTo-SecureString -String \"{password}\" -AsPlainText -Force\n                    $cred = New-Object System.Management.Automation.PSCredential($username, $password)\n                    \n                    try {{\n                        $result = Invoke-Command -VMName $vm_name -Credential $cred -ScriptBlock {{ {command} }}\n                        Write-Output $result\n                    }} catch {{\n                        Write-Error $_.Exception.Message\n                    }}\n                ";
                ps.AddScript(script);

                try
                {
                    Collection<PSObject> results = await Task.Run(() => ps.Invoke());
                    if (ps.HadErrors)
                    {
                        StringBuilder errorBuilder = new StringBuilder();
                        foreach (ErrorRecord error in ps.Streams.Error)
                        {
                            errorBuilder.AppendLine(error.ToString());
                        }
                        return $"Error: {errorBuilder.ToString()}";
                    }
                    else
                    {
                        StringBuilder outputBuilder = new StringBuilder();
                        foreach (PSObject psObject in results)
                        {
                            outputBuilder.AppendLine(psObject.ToString());
                        }
                        return outputBuilder.ToString();
                    }
                }
                catch (Exception ex)
                {
                    return $"Unhandled Exception: {ex.Message}";
                }
            }
        }

        private async Task<bool> ExecutePowerShellCommandAsync(string command)
        {
            using (PowerShell ps = PowerShell.Create())
            {
                ps.AddScript(command);
                try
                {
                    Collection<PSObject> results = await Task.Run(() => ps.Invoke());
                    return !ps.HadErrors;
                }
                catch (Exception ex)
                {
                    // Log error or handle it appropriately
                    Console.WriteLine($"PowerShell command failed: {command}\nError: {ex.Message}");
                    return false;
                }
            }
        }
    }
}
