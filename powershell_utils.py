import subprocess
import json
import os

# 定义常量
_1MB = 1024 * 1024
_1GB = 1024 * 1024 * 1024

# 构建指向脚本所在目录的绝对路径
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_FILE = os.path.join(_SCRIPT_DIR, "online_images_repository.json")

def _run_powershell_command(command):
    """Universal PowerShell command execution function"""
    full_command = ["powershell", "-Command", command]
    try:
        # 使用 'oem' 编码来正确解码系统区域语言（如中文GBK）
        result = subprocess.run(
            full_command, 
            capture_output=True, 
            text=True, 
            encoding='oem', 
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"PowerShell Error: {e.stderr}")
        # 修复：在调用.lower()之前，先检查e.stderr是否为None
        stderr_lower = e.stderr.lower() if e.stderr else ""
        if "requires elevation" in stderr_lower or "access is denied" in stderr_lower:
            return False, "Insufficient permissions, please run this program as an administrator."
        return False, e.stderr
    except FileNotFoundError:
        error_msg = "PowerShell not found, please check the system environment."
        print(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"An unknown error occurred: {e}"
        print(error_msg)
        return False, error_msg

def get_vms_data():
    """Get data for all Hyper-V virtual machines"""
    # Select the State object directly, it will be serialized as a string (e.g., "Running", "Off")
    ps_command = """
    Get-VM | Select-Object Name, State, Uptime, MemoryAssigned, CPUUsage, @{Name='GuestOS';Expression={$_.Guest.OS}}, @{Name='IPAddresses';Expression={$_.NetworkAdapters.IPAddresses}} | ConvertTo-Json -Compress
    """
    success, output = _run_powershell_command(ps_command)
    if success and output:
        try:
            # Handle single VM case where JSON is not an array
            parsed_json = json.loads(output)
            if isinstance(parsed_json, dict):
                return [parsed_json]
            return parsed_json
        except json.JSONDecodeError:
            return []
    return []

def start_vm(vm_name):
    """Start the specified virtual machine"""
    ps_command = f"Start-VM -Name \"{vm_name}\"";
    return _run_powershell_command(ps_command)

def shutdown_vm(vm_name):
    """Safely shut down the specified virtual machine"""
    ps_command = f"Shutdown-VM -Name \"{vm_name}\" -Force";
    return _run_powershell_command(ps_command)

def stop_vm(vm_name):
    """Forcibly stop the specified virtual machine"""
    ps_command = f"Stop-VM -Name \"{vm_name}\"";
    return _run_powershell_command(ps_command)

def delete_vm(vm_name):
    """Deletes the specified virtual machine, stopping it first if necessary."""
    # First, ensure the VM is stopped. We run this and ignore the output, as it might already be stopped.
    stop_command = f"Stop-VM -Name \"{vm_name}\" -Force -Confirm:$false"
    success_stop, output_stop = _run_powershell_command(stop_command)
    if not success_stop:
        return False, f"Failed to stop VM before deletion: {output_stop}"
    
    # Then, remove the VM.
    remove_command = f"Remove-VM -Name \"{vm_name}\" -Force"
    return _run_powershell_command(remove_command)

def connect_vm(vm_name):
    """Launches the Virtual Machine Connection tool for the specified VM."""
    command = f"vmconnect.exe $env:COMPUTERNAME \"{vm_name}\""
    try:
        # Using Popen to run in a new process without blocking and with no console window.
        subprocess.Popen(["powershell", "-Command", command], creationflags=subprocess.CREATE_NO_WINDOW)
        return True, "Connection window launched."
    except Exception as e:
        return False, f"Failed to launch vmconnect: {e}"

def check_hyperv_status():
    """Check the status of the Hyper-V feature"""
    ps_command = "(Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V).State"
    success, output = _run_powershell_command(ps_command)
    if success:
        return output.strip()
    return f"Check failed: {output}"

def install_hyperv():
    """Enable the Hyper-V feature"""
    ps_command = "Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All"
    success, output = _run_powershell_command(ps_command)
    return success, output

def get_vswitches():
    """Get all Hyper-V virtual switches"""
    ps_command = "Get-VMSwitch | Select-Object Name, @{Name='SwitchType';Expression={$_.SwitchType.ToString()}}, Notes | ConvertTo-Json -Compress"
    success, output = _run_powershell_command(ps_command)
    if success and output:
        try:
            parsed_json = json.loads(output)
            if isinstance(parsed_json, dict):
                return [parsed_json]
            return parsed_json
        except json.JSONDecodeError:
            return []
    return []

def get_vswitch_ip_addresses():
    """Gets the IP addresses of all vEthernet adapters."""
    ps_command = "Get-NetAdapter -Name 'vEthernet (*' | ForEach-Object { $adapter = $_; $ip = Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue; if ($ip) { [PSCustomObject]@{ SwitchName = $adapter.Name.Replace('vEthernet (','').Replace(')',''); IPAddress = $ip.IPAddress } } } | ConvertTo-Json -Compress"
    success, output = _run_powershell_command(ps_command)
    if success and output:
        try:
            parsed_json = json.loads(output)
            if isinstance(parsed_json, dict): # Handle single item case
                parsed_json = [parsed_json]
            # Convert list of objects to a dictionary for easy lookup
            return {item['SwitchName']: item['IPAddress'] for item in parsed_json}
        except (json.JSONDecodeError, KeyError):
            return {}
    return {}

def remove_vswitch(switch_name):
    """Delete the specified virtual switch"""
    ps_command = f"Remove-VMSwitch -Name \"{switch_name}\" -Force"
    return _run_powershell_command(ps_command)

def get_network_adapters():
    """Get all physical network adapter names"""
    ps_command = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object Name | ConvertTo-Json -Compress"
    success, output = _run_powershell_command(ps_command)
    if success and output:
        try:
            parsed_json = json.loads(output)
            if isinstance(parsed_json, dict):
                return [parsed_json['Name']] if 'Name' in parsed_json else []
            return [item['Name'] for item in parsed_json if 'Name' in item]
        except json.JSONDecodeError:
            return []
    return []

def create_vswitch(name, switch_type, net_adapter_name=None):
    """Create a new virtual switch"""
    ps_command = f"New-VMSwitch -Name \"{name}\" -SwitchType {switch_type}"
    if switch_type == "External" and net_adapter_name:
        ps_command += f" -NetAdapterName \"{net_adapter_name}\"";
    return _run_powershell_command(ps_command)

def set_vswitch_ip(switch_name, ip_address, prefix_length):
    """Set the IP address for a virtual switch's host-side network adapter."""
    adapter_name = f"vEthernet ({switch_name})"
    ps_command = f"Get-NetAdapter -Name '{adapter_name}' | New-NetIPAddress -IPAddress {ip_address} -PrefixLength {prefix_length}"
    return _run_powershell_command(ps_command)

def create_nat_network(name, internal_ip_interface_address_prefix):
    """Create a new NAT network"""
    ps_command = f"New-NetNat -Name \"{name}\" -InternalIPInterfaceAddressPrefix {internal_ip_interface_address_prefix}"
    return _run_powershell_command(ps_command)

def get_nat_networks():
    """Get all NAT network information"""
    ps_command = "Get-NetNat | Select-Object Name, InternalIPInterfaceAddressPrefix | ConvertTo-Json -Compress"
    success, output = _run_powershell_command(ps_command)
    if success and output:
        try:
            parsed_json = json.loads(output)
            if isinstance(parsed_json, dict):
                return [parsed_json]
            return parsed_json
        except json.JSONDecodeError:
            return []
    return []

def get_nat_rules(nat_name):
    """Get all port mapping rules for the specified NAT network"""
    ps_command = f"Get-NetNatStaticMapping -NatName \"{nat_name}\" | Select-Object Protocol, ExternalPort, InternalIPAddress, InternalPort | ConvertTo-Json -Compress"
    success, output = _run_powershell_command(ps_command)
    if success and output:
        try:
            parsed_json = json.loads(output)
            if isinstance(parsed_json, dict):
                return [parsed_json]
            return parsed_json
        except json.JSONDecodeError:
            return []
    return []

def add_nat_rule(nat_name, external_port, internal_ip, internal_port, protocol):
    """Add a NAT port mapping rule"""
    ps_command = f"Add-NetNatStaticMapping -NatName \"{nat_name}\" -Protocol {protocol} -ExternalIPAddress 0.0.0.0 -ExternalPort {external_port} -InternalIPAddress \"{internal_ip}\" -InternalPort {internal_port}"
    return _run_powershell_command(ps_command)

def remove_nat_rule(nat_name, rule):
    """Delete a NAT port mapping rule"""
    # PowerShell needs the specific rule object to remove it. A simple approach is to recreate the command.
    # A more robust way would be to pipe Get-NetNatStaticMapping to Remove-NetNatStaticMapping, but this is harder to form.
    ps_command = f"Remove-NetNatStaticMapping -NatName \"{nat_name}\" -StaticMapping (Get-NetNatStaticMapping -NatName \"{nat_name}\" | Where-Object {{ $_.Protocol -eq '{rule['Protocol']}' -and $_.ExternalPort -eq {rule['ExternalPort']} }}) -Confirm:$false"
    return _run_powershell_command(ps_command)

def get_online_images():
    """
    Reads a curated list of system images from a local JSON repository file.
    """
    try:
        with open(_REPO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Image repository file not found: {_REPO_FILE}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding image repository file: {_REPO_FILE}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while reading the image repository: {e}")
        return []

def get_local_images(paths):
    """Scans for ISO image files in the specified paths"""
    local_images = []
    for path in paths:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    if file.lower().endswith((".iso", ".vhdx", ".vhd")):
                        filepath = os.path.join(root, file)
                        try:
                            size = os.path.getsize(filepath)
                            local_images.append({
                                "name": file,
                                "path": filepath,
                                "size": f"{size / _1GB:.2f} GB" if size > _1GB else f"{size / _1MB:.2f} MB"
                            })
                        except Exception as e:
                            print(f"Error reading file {filepath}: {e}")
    return local_images

def create_new_vm(name, memory_mb, cpu_cores, vhd_path, vhd_size_gb, vswitch_name, iso_path=None, existing_vhd_path=None, enable_secure_boot=True):
    """Create a new virtual machine"""
    # 1. Create virtual machine
    ps_command = f"New-VM -Name \"{name}\" -MemoryStartupBytes {memory_mb * _1MB} -Generation 2" # Default Gen2
    success, output = _run_powershell_command(ps_command)
    if not success:
        return False, f"Failed to create virtual machine: {output}"

    # 2. Set CPU cores
    ps_command = f"Set-VMProcessor -VMName \"{name}\" -Count {cpu_cores}"
    success, output = _run_powershell_command(ps_command)
    if not success:
        return False, f"Failed to set CPU: {output}"

    # 2.5 Set Secure Boot
    secure_boot_ps_bool = "$true" if enable_secure_boot else "$false"
    ps_command = f"Set-VMFirmware -VMName \"{name}\" -EnableSecureBoot {secure_boot_ps_bool}"
    success, output = _run_powershell_command(ps_command)
    if not success:
        # This is not a critical error, so we can just print a warning
        print(f"Warning: Failed to set Secure Boot status: {output}")

    # 3. Add hard drive
    if existing_vhd_path:
        ps_command = f"Add-VMHardDiskDrive -VMName \"{name}\" -Path \"{existing_vhd_path}\"";
        success, output = _run_powershell_command(ps_command)
        if not success:
            return False, f"Failed to add existing hard drive: {output}"
    elif vhd_path and vhd_size_gb:
        # Ensure the directory for the VHD path exists
        vhd_dir = os.path.dirname(vhd_path)
        if vhd_dir and not os.path.exists(vhd_dir):
            os.makedirs(vhd_dir, exist_ok=True)

        # Create a new VHDX
        ps_command = f"New-VHD -Path \"{vhd_path}\" -SizeBytes {vhd_size_gb * _1GB} -Dynamic -Confirm:$false"
        success, output = _run_powershell_command(ps_command)
        if not success:
            return False, f"Failed to create new VHD: {output}"
        
        # Add the new VHDX to the virtual machine
        ps_command = f"Add-VMHardDiskDrive -VMName \"{name}\" -Path \"{vhd_path}\"";
        success, output = _run_powershell_command(ps_command)
        if not success:
            return False, f"Failed to add new hard drive to virtual machine: {output}"
    else:
        return False, "No hard drive configuration specified"

    # 4. Connect to virtual switch
    ps_command = f"Connect-VMNetworkAdapter -VMName \"{name}\" -SwitchName \"{vswitch_name}\"";
    success, output = _run_powershell_command(ps_command)
    if not success:
        return False, f"Failed to connect network adapter: {output}"

    # 5. Add ISO file (if specified)
    if iso_path:
        ps_command = f"Add-VMDvdDrive -VMName \"{name}\" -Path \"{iso_path}\"";
        success, output = _run_powershell_command(ps_command)
        if not success:
            return False, f"Failed to add ISO: {output}"
        
        # Set the DVD drive as the first boot device
        ps_command = f"Set-VMFirmware -VMName \"{name}\" -FirstBootDevice (Get-VMDvdDrive -VMName \"{name}\")"
        success, output = _run_powershell_command(ps_command)
        if not success:
            return False, f"Failed to set boot device: {output}"

    return True, "Virtual machine created successfully"

def get_vm_network_adapters(vm_name):
    """Gets network adapters for a specific VM."""
    ps_command = f"Get-VMNetworkAdapter -VMName \"{vm_name}\" | Select-Object Name, SwitchName, IPAddresses | ConvertTo-Json -Compress"
    success, output = _run_powershell_command(ps_command)
    if success and output:
        try:
            parsed_json = json.loads(output)
            if isinstance(parsed_json, dict):
                return [parsed_json]
            return parsed_json
        except json.JSONDecodeError:
            return []
    return []

def connect_vm_to_switch(vm_name, network_adapter_name, switch_name):
    """Connects a VM's network adapter to a vSwitch."""
    ps_command = f"Connect-VMNetworkAdapter -VMName \"{vm_name}\" -Name \"{network_adapter_name}\" -SwitchName \"{switch_name}\"";
    return _run_powershell_command(ps_command)

def disconnect_vm_from_switch(vm_name, network_adapter_name):
    """Disconnects a VM's network adapter."""
    ps_command = f"Disconnect-VMNetworkAdapter -VMName \"{vm_name}\" -Name \"{network_adapter_name}\"";
    return _run_powershell_command(ps_command)

def get_vm_network_adapter_status(vm_name):
    """Gets the operational status of network adapters for a specific VM."""
    ps_command = f"Get-VMNetworkAdapter -VMName \"{vm_name}\" | Select-Object Name, SwitchName, @{{Name='Status';Expression={{$_.Status.ToString()}}}} | ConvertTo-Json -Compress"
    success, output = _run_powershell_command(ps_command)
    if success and output:
        try:
            parsed_json = json.loads(output)
            if isinstance(parsed_json, dict):
                return [parsed_json]
            return parsed_json
        except json.JSONDecodeError:
            return []
    return []

def invoke_command_in_vm(vm_name, username, password, command):
    """Executes a PowerShell command inside a VM using PowerShell Direct."""
    # Escape quotes and other special characters for PowerShell
    escaped_command = command.replace("'", "''").replace('"', '"' )
    escaped_password = password.replace("'", "''")

    # Using a more robust script block execution with error handling
    ps_command = f"""
        $vm_name = \"{vm_name}\"
        $username = \"{username}\"
        $password = '{escaped_password}' | ConvertTo-SecureString -AsPlainText -Force
        $cred = New-Object System.Management.Automation.PSCredential($username, $password)
        
        $ErrorActionPreference = "Stop"
        try {{
            $result = Invoke-Command -VMName $vm_name -Credential $cred -ScriptBlock {{ {escaped_command} }}
            $output_str = $result | Out-String
            $response = @{{ success = $true; output = $output_str }}
        }} catch {{
            $response = @{{ success = $false; error = $_.Exception.Message }}
        }}
        $response | ConvertTo-Json -Depth 3 -Compress
    """
    success, output = _run_powershell_command(ps_command)
    if success and output:
        try:
            # The entire output is a single JSON string, so we parse it.
            return True, json.loads(output)
        except json.JSONDecodeError as e:
            return False, {"success": False, "error": f"JSON parsing error: {e}\nRaw output: {output}"}
    return success, {"success": False, "error": output}
