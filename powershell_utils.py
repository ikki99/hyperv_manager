import subprocess
import json
import os

# 定义常量
_1MB = 1024 * 1024
_1GB = 1024 * 1024 * 1024

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
    ps_command = """
    Get-VM | Select-Object Name, State, Uptime, MemoryAssigned, CPUUsage, @{Name='GuestOS';Expression={$_.Guest.OS}}, @{Name='IPAddresses';Expression={$_.NetworkAdapters.IPAddresses}} | ConvertTo-Json -Compress
    """
    success, output = _run_powershell_command(ps_command)
    if success and output:
        try:
            parsed_json = json.loads(output)
            if isinstance(parsed_json, dict):
                return [parsed_json]
            return parsed_json
        except json.JSONDecodeError:
            return None
    return None

def start_vm(vm_name):
    """Start the specified virtual machine"""
    ps_command = f"Start-VM -Name \"{vm_name}\"";
    return _run_powershell_command(ps_command)

def shutdown_vm(vm_name):
    """Safely shut down the specified virtual machine"""
    ps_command = f"Shutdown-VM -Name \"{vm_name}\"";
    return _run_powershell_command(ps_command)

def stop_vm(vm_name):
    """Forcibly stop the specified virtual machine"""
    ps_command = f"Stop-VM -Name \"{vm_name}\"";
    return _run_powershell_command(ps_command)

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
    ps_command = "Get-VMSwitch | Select-Object Name, SwitchType, Notes | ConvertTo-Json -Compress"
    success, output = _run_powershell_command(ps_command)
    if success and output:
        try:
            parsed_json = json.loads(output)
            if isinstance(parsed_json, dict):
                return [parsed_json]
            return parsed_json
        except json.JSONDecodeError:
            return None
    return None

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
            return None
    return None

def get_nat_rules(nat_name):
    """Get all port mapping rules for the specified NAT network"""
    ps_command = f"Get-NetNatStaticMapping -NatName \"{nat_name}\" | Select-Object RemotePort, InternalPort, InternalIPAddress, Protocol | ConvertTo-Json -Compress"
    success, output = _run_powershell_command(ps_command)
    if success and output:
        try:
            parsed_json = json.loads(output)
            if isinstance(parsed_json, dict):
                return [parsed_json]
            return parsed_json
        except json.JSONDecodeError:
            return None
    return None

def add_nat_rule(nat_name, external_port, internal_ip, internal_port, protocol):
    """Add a NAT port mapping rule"""
    ps_command = f"Add-NetNatStaticMapping -NatName \"{nat_name}\" -ExternalPort {external_port} -InternalIPAddress \"{internal_ip}\" -InternalPort {internal_port} -Protocol {protocol}"
    return _run_powershell_command(ps_command)

def remove_nat_rule(nat_name, external_port, internal_ip, internal_port, protocol):
    """Delete a NAT port mapping rule"""
    ps_command = f"Remove-NetNatStaticMapping -NatName \"{nat_name}\" -ExternalPort {external_port} -InternalIPAddress \"{internal_ip}\" -InternalPort {internal_port} -Protocol {protocol} -Confirm:$false"
    return _run_powershell_command(ps_command)

def get_online_images():
    """获取在线系统镜像列表"""
    # 在实际应用中，这里会从一个远程URL动态获取JSON数据
    # 为安全起见，所有URL都是示例，并非真实链接
    online_images_data = [
        {
            "name": "Ubuntu 22.04 LTS",
            "description": "最受欢迎的Linux发行版之一，长期支持，稳定可靠。",
            "category": "Linux / Ubuntu",
            "download_url": "https://releases.ubuntu.com/22.04/ubuntu-22.04.3-desktop-amd64.iso",
            "size": "4.6 GB",
            "version": "22.04.3 LTS",
            "arch": "x86_64"
        },
        {
            "name": "Debian 12 (Bookworm)",
            "description": "以其稳定性、可靠性和庞大的软件库而闻名。",
            "category": "Linux / Debian",
            "download_url": "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.1.0-amd64-netinst.iso",
            "size": "650 MB",
            "version": "12.1.0",
            "arch": "x86_64"
        },
        {
            "name": "Fedora Workstation 38",
            "description": "由Red Hat赞助，提供最新的开源软件和技术。",
            "category": "Linux / Fedora",
            "download_url": "https://download.fedoraproject.org/pub/fedora/linux/releases/38/Workstation/x86_64/iso/Fedora-Workstation-Live-x86_64-38-1.6.iso",
            "size": "2.1 GB",
            "version": "38",
            "arch": "x86_64"
        },
        {
            "name": "CentOS Stream 9",
            "description": "作为RHEL的上游开发分支，适合需要企业级特性的开发者。",
            "category": "Linux / CentOS",
            "download_url": "https://mirror.stream.centos.org/9-stream/BaseOS/x86_64/iso/CentOS-Stream-9-20230925.0-x86_64-dvd1.iso",
            "size": "8.9 GB",
            "version": "9 Stream",
            "arch": "x86_64"
        },
        {
            "name": "Manjaro Linux (Gnome)",
            "description": "基于Arch Linux，用户友好，对新手友好，滚动更新。",
            "category": "第三方 / Arch Linux",
            "download_url": "https://download.manjaro.org/gnome/23.0.0/manjaro-gnome-23.0.0-230911-linux61.iso",
            "size": "4.2 GB",
            "version": "23.0.0",
            "arch": "x86_64"
        },
        {
            "name": "CachyOS (KDE)",
            "description": "一个预配置的Arch Linux发行版，以性能优化和易用性著称。",
            "category": "第三方 / Arch Linux",
            "download_url": "https://mirror.cachyos.org/ISO/cachyos-kde-linux-230827.iso",
            "size": "2.8 GB",
            "version": "230827",
            "arch": "x86_64"
        },
        {
            "name": "Windows 11 (评估版)",
            "description": "来自微软官方的Windows 11企业版评估版本，90天试用。",
            "category": "Windows",
            "download_url": "https://software.download.prss.microsoft.com/dbazure/Win11_22H2_English_x64v1.iso",
            "size": "5.2 GB",
            "version": "22H2",
            "arch": "x86_64"
        }
    ]
    return online_images_data

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

def create_new_vm(name, memory_mb, cpu_cores, vhd_path, vhd_size_gb, vswitch_name, iso_path=None, existing_vhd_path=None):
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
        
        # Set the DVD drive as the first boot device (optional, but usually necessary)
        # ps_command = f"Set-VMFirmware -VMName \"{name}\" -FirstBootDevice (Get-VMDvdDrive -VMName \"{name}\")"
        # success, output = _run_powershell_command(ps_command)
        # if not success:
        #     return False, f"Failed to set boot device: {output}"

    return True, "Virtual machine created successfully"