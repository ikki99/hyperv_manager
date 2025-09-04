

import PySimpleGUI as sg
import sys
import os
import webbrowser
from powershell_utils import (
    get_vms_data, start_vm, shutdown_vm, stop_vm, delete_vm, connect_vm,
    check_hyperv_status, install_hyperv, get_vswitches, 
    remove_vswitch, get_network_adapters, create_vswitch, 
    get_nat_networks, get_nat_rules, add_nat_rule, remove_nat_rule, 
    get_online_images, get_local_images, create_new_vm,
    set_vswitch_ip, create_nat_network, get_vswitch_ip_addresses,
    get_vm_network_adapters, connect_vm_to_switch, disconnect_vm_from_switch,
    get_vm_network_adapter_status
)

# --- Helper Functions ---
def refresh_vm_table(window):
    vms = get_vms_data()
    vm_data = []
    if vms:
        for vm in vms:
            # Check network status
            net_status = "未知"
            adapters_status = get_vm_network_adapter_status(vm.get('Name'))
            if not adapters_status:
                net_status = "无网卡"
            else:
                is_connected = False
                has_error = False
                for adapter in adapters_status:
                    # In PowerShell, status is an enum, e.g., {Degraded, NotConnected, Ok}
                    # We get it as a string 'Degraded', 'NotConnected', 'Ok'
                    if adapter.get('Status') != 'Ok':
                        has_error = True
                        break
                    if adapter.get('SwitchName'):
                        is_connected = True
                
                if has_error:
                    net_status = "状态异常"
                elif is_connected:
                    net_status = "已连接"
                else:
                    net_status = "未连接"

            vm_data.append([
                vm.get('Name', 'N/A'), 
                vm.get('State', 'N/A'), 
                net_status,
                vm.get('GuestOS', 'N/A'), 
                ", ".join(vm.get('IPAddresses') if isinstance(vm.get('IPAddresses'), list) else [])
            ])

    window["-VM_TABLE-"].update(values=vm_data)
    # Disable buttons after refresh
    window["-START_VM-"].update(disabled=True)
    window["-SHUTDOWN_VM-"].update(disabled=True)
    window["-STOP_VM-"].update(disabled=True)
    window["-DELETE_VM-"].update(disabled=True)
    window["-CONNECT_VM-"].update(disabled=True)
    window["-CONFIG_VM_NET-"].update(disabled=True)


def refresh_vswitch_table(window):
    switches = get_vswitches()
    nats = get_nat_networks()
    nat_names = [n['Name'] for n in nats] if nats else []
    ip_addresses = get_vswitch_ip_addresses()
    
    vswitch_data = []
    if switches:
        for switch in switches:
            details = ""
            switch_name = switch.get('Name', 'N/A')
            if switch.get('SwitchType') == 'Internal':
                nat_status = "NAT: 已启用" if switch_name in nat_names else "NAT: 未启用"
                gateway = ip_addresses.get(switch_name, "未设置")
                details = f"{nat_status}, 网关: {gateway}"
            else:
                details = "不适用"

            vswitch_data.append([
                switch_name,
                switch.get('SwitchType', 'N/A'),
                details,
                switch.get('Notes', '')
            ])
    window["-VSWITCH_TABLE-"].update(values=vswitch_data)
    window["-DELETE_VSWITCH-"].update(disabled=True)
    window["-NAT_PANEL-"].update(visible=False)

def create_vswitch_window():
    adapter_list = get_network_adapters()

    type_mapping = {"外部": "External", "内部": "Internal", "专用": "Private"}
    reverse_type_mapping = {v: k for k, v in type_mapping.items()}

    descriptions = {
        "External": "将虚拟机连接到物理网络。需要绑定一个物理网卡。\n警告: 这会改变物理网卡的网络配置，可能导致现有网络连接(包括远程桌面)中断。",
        "Internal": "创建一个仅在当前主机上的虚拟机之间以及虚拟机与主机之间通信的交换机。\n虚拟机无法访问外部网络，但可以和主机互相访问。",
        "Private": "创建一个仅在当前主机上的虚拟机之间通信的交换机。\n虚拟机之间可以互相通信，但无法与主机或外部网络通信。"
    }
    
    layout = [
        [sg.Text("交换机名称:"), sg.Input(key="-NAME-")],
        [sg.Text("交换机类型:"), sg.Combo(list(type_mapping.keys()), default_value=reverse_type_mapping["Internal"], key="-TYPE-", readonly=True, enable_events=True)],
        [sg.Text("物理网卡:", visible=False, key="-ADAPTER_LABEL-"), sg.Combo(adapter_list, key="-ADAPTER-", visible=False, readonly=True)],
        [sg.Frame('说明', [[sg.Text(descriptions["Internal"], key="-DESC-", size=(50, 4))]])],
        [sg.Button("创建", key="-SUBMIT-"), sg.Button("取消")]
    ]
    
    window = sg.Window("创建虚拟交换机", layout, modal=True)
    
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "取消"):
            break
        
        if event == "-TYPE-":
            selected_type_chinese = values["-TYPE-"]
            switch_type_english = type_mapping[selected_type_chinese]
            is_external = switch_type_english == "External"
            window["-ADAPTER_LABEL-"].update(visible=is_external)
            window["-ADAPTER-"].update(visible=is_external)
            window["-DESC-"].update(descriptions[switch_type_english])
            
        if event == "-SUBMIT-":
            name = values["-NAME-"]
            selected_type_chinese = values["-TYPE-"]
            switch_type_english = type_mapping[selected_type_chinese]
            adapter = values["-ADAPTER-"] if switch_type_english == "External" else None
            
            if not name:
                sg.popup_error("交换机名称不能为空！")
                continue
            if switch_type_english == "External" and not adapter:
                sg.popup_error("外部交换机必须选择一个物理网卡！")
                continue
                
            success, output = create_vswitch(name, switch_type_english, adapter)
            if success:
                sg.popup("交换机创建成功！")
                break
            else:
                sg.popup_error(f"创建失败: {output}")
                
    window.close()


from download_manager import DownloadManager

def create_add_nat_rule_window(nat_name):
    layout = [
        [sg.Text("协议:"), sg.Combo(["TCP", "UDP"], default_value="TCP", key="-PROTO-", readonly=True)],
        [sg.Text("外部端口:"), sg.Input(key="-EXT_PORT-")],
        [sg.Text("内部IP地址:"), sg.Input(key="-INT_IP-")],
        [sg.Text("内部端口:"), sg.Input(key="-INT_PORT-")],
        [sg.Button("添加"), sg.Button("取消")]
    ]
    window = sg.Window("添加端口转发规则", layout, modal=True)
    rule_added = False
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "取消"):
            break
        if event == "添加":
            if not all([values["-EXT_PORT-"], values["-INT_IP-"], values["-INT_PORT-"]]):
                sg.popup_error("所有字段都不能为空！")
                continue
            try:
                ext_port = int(values["-EXT_PORT-"])
                int_port = int(values["-INT_PORT-"])
            except ValueError:
                sg.popup_error("端口号必须是数字！")
                continue

            success, output = add_nat_rule(
                nat_name=nat_name,
                protocol=values["-PROTO-"],
                external_port=ext_port,
                internal_ip=values["-INT_IP-"],
                internal_port=int_port
            )
            if success:
                sg.popup("规则添加成功！")
                rule_added = True
                break
            else:
                sg.popup_error(f"添加失败: {output}")
    window.close()
    return rule_added


def build_online_images_layout():
    images = get_online_images()
    layout = []
    # Create a grid with 2 columns
    for i in range(0, len(images), 2):
        row = []
        # Column 1
        img1 = images[i]
        url1 = img1.get("download_url")
        frame1_layout = [
            [sg.Text(img1.get("name"), font=("Any 14"))],
            [sg.Text(f"版本: {img1.get('version')} | 大小: {img1.get('size')}")],
            [sg.Text(img1.get("description"), size=(35, 2))],
            [sg.Button("在浏览器中打开", key=f"-OPEN_URL-{url1}", expand_x=True)]
        ]
        row.append(sg.Frame(title="", layout=frame1_layout, pad=(5,5), expand_x=True))

        # Column 2
        if i + 1 < len(images):
            img2 = images[i+1]
            url2 = img2.get("download_url")
            frame2_layout = [
                [sg.Text(img2.get("name"), font=("Any 14"))],
                [sg.Text(f"版本: {img2.get('version')} | 大小: {img2.get('size')}")],
                [sg.Text(img2.get("description"), size=(35, 2))],
                [sg.Button("在浏览器中打开", key=f"-OPEN_URL-{url2}", expand_x=True)]
            ]
            row.append(sg.Frame(title="", layout=frame2_layout, pad=(5,5), expand_x=True))
        
        layout.append(row)
    return layout

def create_vm_network_window(vm_name):
    adapters = get_vm_network_adapters(vm_name)
    switches = get_vswitches()
    switch_names = [s['Name'] for s in switches]

    if not adapters:
        sg.popup_error(f"虚拟机 '{vm_name}' 没有找到网络适配器。")
        return

    # For simplicity, this UI handles the first network adapter.
    adapter_name = adapters[0].get('Name')
    current_switch = adapters[0].get('SwitchName') or "未连接"

    layout = [
        [sg.Text(f"正在为虚拟机 '{vm_name}' 配置网络")],
        [sg.Text(f"网卡: {adapter_name}")],
        [sg.Text(f"当前连接: {current_switch}")],
        [sg.HSep()],
        [sg.Text("选择要连接的交换机:"), sg.Combo(switch_names, key="-SWITCH_TO_CONNECT-", readonly=True)],
        [sg.Button("连接"), sg.Button("断开连接"), sg.Button("关闭")]
    ]

    window = sg.Window("设置虚拟机网络", layout, modal=True)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "关闭"):
            break
        
        if event == "连接":
            selected_switch = values["-SWITCH_TO_CONNECT-"]
            if not selected_switch:
                sg.popup_error("请先选择一个交换机。")
                continue
            success, output = connect_vm_to_switch(vm_name, adapter_name, selected_switch)
            if success:
                sg.popup("连接成功！")
                break
            else:
                sg.popup_error(f"连接失败: {output}")

        if event == "断开连接":
            if current_switch == "未连接":
                sg.popup("该网卡尚未连接到任何交换机。")
            else:
                success, output = disconnect_vm_from_switch(vm_name, adapter_name)
                if success:
                    sg.popup("已断开连接。")
                    break
                else:
                    sg.popup_error(f"操作失败: {output}")
    window.close()

def main():
    sg.theme("SystemDefaultForReal")

    # --- Layouts ---
    nav_column = sg.Column([
        [sg.Button("虚拟机", key="-NAV_VMS-", size=(12, 2))],
        [sg.Button("网络设置", key="-NAV_NETWORK-", size=(12, 2))],
        [sg.Button("创建虚拟机", key="-NAV_CREATE-", size=(12, 2))],
        [sg.Button("系统镜像", key="-NAV_IMAGES-", size=(12, 2))],
        [sg.Button("系统检查", key="-NAV_SYSTEM-", size=(12, 2))],
    ])

    system_check_layout = [
        [sg.Text("系统状态检查", font=("Any 20"))],
        [sg.Button("检查Hyper-V状态", key="-CHECK_HYPERV-")],
        [sg.Text("点击上方按钮检查Hyper-V状态...", key="-STATUS_TEXT-", size=(60, 3))],
        [sg.Button("一键安装 Hyper-V", key="-INSTALL_HYPERV-", visible=False, button_color=("white", "green"))],
        [sg.Text("警告：安装过程需要管理员权限...", key="-INSTALL_WARN-", visible=False, text_color="orange")]
    ]

    vm_list_layout = [
        [sg.Text("虚拟机列表", font=("Any 20"))],
        [sg.Button("刷新", key="-REFRESH_VMS-"), 
         sg.Button("连接", key="-CONNECT_VM-", disabled=True),
         sg.Button("启动", key="-START_VM-", disabled=True),
         sg.Button("设置网络", key="-CONFIG_VM_NET-", disabled=True),
         sg.Button("关机", key="-SHUTDOWN_VM-", disabled=True),
         sg.Button("强制停止", key="-STOP_VM-", disabled=True),
         sg.Button("删除", key="-DELETE_VM-", disabled=True, button_color=("white", "red"))],
        [sg.Table(values=[], headings=["名称", "状态", "网络状态", "操作系统", "IP地址"], 
                  key="-VM_TABLE-", auto_size_columns=False, col_widths=[20, 10, 10, 30, 20],
                  justification='left', enable_events=True, num_rows=20)]
    ]

    network_layout = [
        [sg.Text("网络管理", font=("Any 20"))],
        [sg.Button("刷新", key="-REFRESH_VSWITCHES-"),
         sg.Button("创建交换机", key="-CREATE_VSWITCH-"),
         sg.Button("删除所选交换机", key="-DELETE_VSWITCH-", disabled=True, button_color=("white", "red"))],
        [sg.Table(values=[], headings=["名称", "类型", "详情", "备注"], 
                  key="-VSWITCH_TABLE-", auto_size_columns=False, col_widths=[20, 10, 10, 35],
                  justification='left', enable_events=True, num_rows=10)],
        [sg.Frame("NAT 网络详情", [
            [sg.Text("说明: NAT网络允许虚拟机通过主机访问外网，但外部无法直接访问虚拟机。\n步骤: 1. 创建一个'内部'交换机 -> 2. 选中它 -> 3. 点击下方'创建NAT网络'", font=("Any 9"), text_color="grey")],
            [sg.Text("", key="-NAT_STATUS-")],
            [sg.Button("创建NAT网络", key="-CREATE_NAT-"), sg.Button("设置网关IP", key="-SET_GW_IP-"), sg.Button("添加端口转发", key="-ADD_NAT_RULE-")],
            [sg.Table(values=[], headings=["协议", "外部端口", "内部IP", "内部端口"], 
                      key="-NAT_RULES_TABLE-", auto_size_columns=False, col_widths=[8, 10, 15, 10],
                      justification='left', num_rows=5)],
            [sg.Button("删除所选规则", key="-DELETE_NAT_RULE-")]
        ], key="-NAT_PANEL-", visible=False)]
    ]

    download_mgr = DownloadManager()

    online_images_layout_content = build_online_images_layout()

    online_images_tab_content = [
        [sg.Text("提示: 点击按钮后将在外部浏览器打开下载页面，您可以使用第三方下载工具。", font=("Any 9"), text_color="grey")],
        [sg.Column(online_images_layout_content, scrollable=True, vertical_scroll_only=True, expand_x=True, expand_y=True,  key='-IMAGE_LIST_COL-')]
    ]

    local_images_layout = [
        [sg.Text("选择包含镜像文件的文件夹:")],
        [sg.Input(key="-SCAN_PATH-", expand_x=True), sg.FolderBrowse("选择文件夹", target="-SCAN_PATH-")],
        [sg.Button("开始扫描", key="-SCAN_LOCAL-", expand_x=True)],
        [sg.HorizontalSeparator()],
        [sg.Table(values=[], headings=["文件名", "路径", "大小"], 
                  key="-LOCAL_IMG_TABLE-", auto_size_columns=False, col_widths=[20, 50, 15],
                  justification='left', enable_events=True, num_rows=11, expand_x=True)],
        [sg.Button("使用选中镜像创建虚拟机", key="-CREATE_FROM_LOCAL-", disabled=True, expand_x=True)]
    ]

    images_layout = [
        [sg.TabGroup([
            [sg.Tab("在线镜像市场", online_images_tab_content, expand_x=True, expand_y=True)],
            [sg.Tab("本地镜像", local_images_layout, expand_x=True, expand_y=True)]
        ], key="-IMAGE_TABS-", expand_x=True, expand_y=True)]
    ]

    # --- VM Wizard Layouts ---
    step1_layout = sg.Column([
        [sg.Text("步骤 1: 名称和位置", font=("Any 16"))],
        [sg.Text("虚拟机名称", size=(15,1)), sg.Input(key="-VM_NAME-")],
        [sg.Text("存储位置", size=(15,1)), sg.Input(os.path.join(os.path.expanduser("~"), "Hyper-V"), key="-VM_PATH-"), sg.FolderBrowse("浏览")],
        [sg.Checkbox("启用安全启动", key="-SECURE_BOOT-", default=True), sg.Text("", tooltip="推荐用于 Windows 11 和其他现代操作系统。\n如果安装旧版系统（如 Windows 7），请取消勾选。")]
    ], key="-WIZARD_STEP_1-")

    step2_layout = sg.Column([
        [sg.Text("步骤 2: 内存和处理器", font=("Any 16"))],
        [sg.Text("内存 (MB)", size=(15,1)), sg.Slider(range=(1024, 16384), default_value=2048, resolution=1024, orientation='h', size=(30, 20), key="-VM_MEM-"), sg.Text("", tooltip="为虚拟机分配的内存大小。\n此向导目前不支持动态内存。")],
        [sg.Text("CPU核心数", size=(15,1)), sg.Slider(range=(1, 8), default_value=2, orientation='h', size=(30, 20), key="-VM_CPU-"), sg.Text("", tooltip="为虚拟机分配的CPU逻辑核心数量。\n建议不要超过主机物理核心数的一半。")]
    ], key="-WIZARD_STEP_2-", visible=False)

    step3_layout = sg.Column([
        [sg.Text("步骤 3: 硬盘", font=("Any 16"))],
        [sg.Radio("创建新的虚拟硬盘", "DISK", key="-DISK_NEW-", default=True, enable_events=True), 
         sg.Text("", tooltip="将为虚拟机创建一个全新的、空白的虚拟硬盘文件 (.vhdx)。\n您需要在虚拟机启动后手动安装操作系统。")],
        [sg.Text("大小 (GB)", size=(15,1)), sg.Input("50", key="-DISK_SIZE-", size=(10,1))],
        [sg.Radio("使用现有虚拟硬盘", "DISK", key="-DISK_EXIST-", enable_events=True), 
         sg.Text("", tooltip="使用一个已经存在的虚拟硬盘文件 (.vhd 或 .vhdx)。\n这通常用于恢复虚拟机，或使用已预装好系统的硬盘文件。")],
        [sg.Text("路径", size=(15,1)), sg.Input(key="-DISK_PATH-", disabled=True), sg.FileBrowse("浏览", file_types=(("Virtual Hard Disks", "*.vhdx *.vhd"),))]
    ], key="-WIZARD_STEP_3-", visible=False)

    step4_layout = sg.Column([
        [sg.Text("步骤 4: 网络", font=("Any 16"))],
        [sg.Text("虚拟交换机", size=(15,1)), sg.Combo([], key="-VM_VSWITCH-", readonly=True, size=(30,1)), sg.Text("", tooltip="为虚拟机选择一个网络连接。\nDefault Switch: 可访问外网的默认交换机。\nInternal/Private: 仅用于内部网络的交换机。")]
    ], key="-WIZARD_STEP_4-", visible=False)

    # --- Step 5 Layout with Tabs ---
    install_from_file_layout = [
        [sg.Text("选择一个本地的 .iso 镜像文件用于安装系统。")],
        [sg.Text("镜像路径", size=(15,1)), sg.Input(key="-ISO_PATH-"), sg.FileBrowse("浏览", file_types=(("ISO Files", "*.iso"),))]
    ]

    install_from_download_layout = [
        [sg.Text("从通过本软件下载的镜像列表中选择一个进行安装。")],
        [sg.Table(values=[], headings=["文件名", "大小"], 
                  key="-DOWNLOADED_IMG_TABLE-", auto_size_columns=False, col_widths=[40, 15],
                  justification='left', enable_events=True, num_rows=8, expand_x=True)],
    ]

    step5_layout = sg.Column([
        [sg.Text("步骤 5: 安装选项", font=("Any 16"))],
        [sg.Text("说明: 如果您在步骤3中选择了'使用现有虚拟硬盘'，则无需在此选择安装介质。", font=("Any 9"), text_color="grey")],
        [sg.TabGroup([
            [sg.Tab("从本地文件", install_from_file_layout, key="-TAB_ISO_LOCAL-")],
            [sg.Tab("从已下载镜像", install_from_download_layout, key="-TAB_ISO_DOWNLOADED-")]
        ], key="-ISO_TAB_GROUP-")]
    ], key="-WIZARD_STEP_5-", visible=False)

    step6_layout = sg.Column([
        [sg.Text("步骤 6: 摘要", font=("Any 16"))],
        [sg.Text("请在创建前最后检查一遍您的配置：")],
        [sg.Multiline(size=(60, 15), key="-VM_SUMMARY-", disabled=True)]
    ], key="-WIZARD_STEP_6-", visible=False)

    create_vm_layout = [
        [sg.Text("创建虚拟机向导", font=("Any 20"))],
        [sg.HorizontalSeparator()],
        [step1_layout, step2_layout, step3_layout, step4_layout, step5_layout, step6_layout],
        [sg.HorizontalSeparator()],
        [sg.Button("上一步", key="-WIZARD_BACK-", disabled=True), sg.Button("下一步", key="-WIZARD_NEXT-")]
    ]

    content_column = sg.Column([
        [
            sg.Column(vm_list_layout, key="-VIEW_VMS-", visible=True, expand_x=True, expand_y=True),
            sg.Column(network_layout, key="-VIEW_NETWORK-", visible=False, expand_x=True, expand_y=True),
            sg.Column(create_vm_layout, key="-VIEW_CREATE-", visible=False, expand_x=True, expand_y=True),
            sg.Column(images_layout, key="-VIEW_IMAGES-", visible=False, expand_x=True, expand_y=True),
            sg.Column(system_check_layout, key="-VIEW_SYSTEM-", visible=False, expand_x=True, expand_y=True)
        ]
    ], expand_x=True, expand_y=True)

    layout = [[nav_column, sg.VerticalSeparator(), content_column]]

    window = sg.Window("Hyper-V 统一管理器", layout, resizable=True, finalize=True, size=(900, 650))
    
    # Initial Load
    refresh_vm_table(window)
    refresh_vswitch_table(window)

    # --- Event Loop ---
    active_view = "-VIEW_VMS-"
    selected_vm_name = None
    selected_vswitch_name = None
    selected_local_image = None
    wizard_step = 1

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break

        # --- Navigation --- 
        if event.startswith("-NAV_"):
            nav_key = event.replace("-NAV_", "-VIEW_")
            window[active_view].update(visible=False)
            window[nav_key].update(visible=True)
            active_view = nav_key
            if active_view == "-VIEW_VMS-": refresh_vm_table(window)
            if active_view == "-VIEW_NETWORK-": refresh_vswitch_table(window)

        # --- VM List Events ---
        if event == "-REFRESH_VMS-":
            refresh_vm_table(window)
            selected_vm_name = None

        if event == "-VM_TABLE-":
            selected_indices = values["-VM_TABLE-"]
            if selected_indices:
                # Access the table's data directly using .Values property
                table_current_data = window["-VM_TABLE-"].Values
                selected_row_index = selected_indices[0]
                # Ensure the selected index is valid for the current data
                if selected_row_index < len(table_current_data):
                    selected_vm_name = table_current_data[selected_row_index][0]
                    window["-CONNECT_VM-"].update(disabled=False)
                    window["-START_VM-"].update(disabled=False)
                    window["-CONFIG_VM_NET-"].update(disabled=False)
                    window["-SHUTDOWN_VM-"].update(disabled=False)
                    window["-STOP_VM-"].update(disabled=False)
                    window["-DELETE_VM-"].update(disabled=False)
                else: # Should not happen if selected_indices is not empty, but for safety
                    selected_vm_name = None
            else:
                selected_vm_name = None

        def handle_vm_action(action, vm_name):
            if not vm_name: return sg.popup_error("请先在表格中选择一个虚拟机！")
            if action == "delete" and sg.popup_ok_cancel(f"您确定要永久删除虚拟机 '{vm_name}' 吗？", title="确认删除") != "OK": return
            
            actions = {"start": start_vm, "shutdown": shutdown_vm, "stop": stop_vm, "delete": delete_vm}
            success, output = actions[action](vm_name)
            if success: sg.popup_quick_message(f"'{vm_name}' 的 '{action}' 命令已发送。", auto_close_duration=3)
            else: sg.popup_error(f"操作失败: {output}")
            refresh_vm_table(window)

        if event == "-START_VM-": handle_vm_action("start", selected_vm_name)
        if event == "-SHUTDOWN_VM-": handle_vm_action("shutdown", selected_vm_name)
        if event == "-STOP_VM-": handle_vm_action("stop", selected_vm_name)
        if event == "-DELETE_VM-": handle_vm_action("delete", selected_vm_name)

        if event == "-CONNECT_VM-":
            if selected_vm_name:
                success, output = connect_vm(selected_vm_name)
                if not success:
                    sg.popup_error(f"无法连接到虚拟机: {output}")
            else:
                sg.popup_error("请先在表格中选择一个虚拟机！")

        if event == "-CONFIG_VM_NET-":
            if selected_vm_name:
                create_vm_network_window(selected_vm_name)
                refresh_vm_table(window) # Refresh to show updated IP/network info
            else:
                sg.popup_error("请先在表格中选择一个虚拟机！")

        # --- Network Events ---
        if event == "-REFRESH_VSWITCHES-":
            refresh_vswitch_table(window)
            selected_vswitch_name = None

        if event == "-VSWITCH_TABLE-":
            selected_indices = values["-VSWITCH_TABLE-"]
            if selected_indices:
                table_data = window["-VSWITCH_TABLE-"].Values
                selected_row_index = selected_indices[0]
                if selected_row_index < len(table_data):
                    selected_vswitch_name, switch_type, nat_status_text, _ = table_data[selected_row_index]
                    window["-DELETE_VSWITCH-"].update(disabled=False)

                    # NAT Panel Logic
                    if switch_type == 'Internal':
                        window["-NAT_PANEL-"].update(visible=True)
                        is_nat_enabled = "NAT: 已启用" in nat_status_text
                        
                        nat_rules_data = []
                        if is_nat_enabled:
                            nat_rules = get_nat_rules(selected_vswitch_name)
                            nat_rules_data = [[r.get('Protocol', 'N/A'), r.get('ExternalPort', 'N/A'), r.get('InternalIPAddress', 'N/A'), r.get('InternalPort', 'N/A')] for r in nat_rules]
                        
                        window["-NAT_RULES_TABLE-"].update(values=nat_rules_data)
                        window["-CREATE_NAT-"].update(disabled=is_nat_enabled)
                        window["-ADD_NAT_RULE-"].update(disabled=not is_nat_enabled)
                        window["-DELETE_NAT_RULE-"].update(disabled=not is_nat_enabled)
                        window["-NAT_STATUS-"].update(f"交换机 '{selected_vswitch_name}' 的NAT状态: {'已启用' if is_nat_enabled else '未启用'}")
                    else:
                        window["-NAT_PANEL-"].update(visible=False)
                else:
                    selected_vswitch_name = None
                    window["-NAT_PANEL-"].update(visible=False)
            else:
                selected_vswitch_name = None
                window["-NAT_PANEL-"].update(visible=False)

        if event == "-DELETE_VSWITCH-":
            if selected_vswitch_name == "Default Switch":
                sg.popup_error("不能删除系统默认的交换机 'Default Switch'。")
            elif selected_vswitch_name and sg.popup_ok_cancel(f"确定要删除交换机 '{selected_vswitch_name}' 吗？", title="确认删除") == "OK":
                success, output = remove_vswitch(selected_vswitch_name)
                if success: sg.popup_quick_message("交换机已删除。")
                else: sg.popup_error(f"删除失败: {output}")
                refresh_vswitch_table(window)

        if event == "-CREATE_VSWITCH-":
            create_vswitch_window()
            refresh_vswitch_table(window)

        # --- Image Events ---
        if isinstance(event, str) and event.startswith("-OPEN_URL-"):
            url = event.replace("-OPEN_URL-", "")
            try:
                webbrowser.open(url, new=2)
            except Exception as e:
                sg.popup_error(f"无法打开链接: {e}")

        if event == "-SCAN_LOCAL-":
            scan_path = values["-SCAN_PATH-"]
            if scan_path and os.path.isdir(scan_path):
                window["-SCAN_LOCAL-"].update(disabled=True, text="扫描中...")
                window.refresh()
                images = get_local_images([scan_path])
                image_data = [[img.get('name'), img.get('path'), img.get('size')] for img in images]
                window["-LOCAL_IMG_TABLE-"].update(values=image_data)
                window["-SCAN_LOCAL-"].update(disabled=False, text="开始扫描")
            else:
                sg.popup_error("请输入一个有效的文件夹路径进行扫描。")

        if event == "-LOCAL_IMG_TABLE-":
            if values["-LOCAL_IMG_TABLE-"]:
                window["-CREATE_FROM_LOCAL-"].update(disabled=False)
            else:
                window["-CREATE_FROM_LOCAL-"].update(disabled=True)

        if event == "-CREATE_FROM_LOCAL-":
            if values["-LOCAL_IMG_TABLE-"]:
                selected_row_index = values["-LOCAL_IMG_TABLE-"][0]
                selected_local_image = window["-LOCAL_IMG_TABLE-"].Values[selected_row_index]
                image_path = selected_local_image[1]
                
                # Navigate to Create VM view
                window[active_view].update(visible=False)
                active_view = "-VIEW_CREATE-"
                window[active_view].update(visible=True)
                
                # Pre-fill the path
                if image_path.lower().endswith(".iso"):
                    # Go to step 5 and pre-fill
                    window["-WIZARD_STEP_1-"].update(visible=False)
                    window["-WIZARD_STEP_5-"].update(visible=True)
                    window["-ISO_TAB_GROUP-"].Widget.select(0) # Select the first tab (local)
                    window["-ISO_PATH-"].update(image_path)
                    wizard_step = 5
                    window["-WIZARD_BACK-"].update(disabled=False)
                    window["-WIZARD_NEXT-"].update("下一步")
                else: # VHDX/VHD
                    # Go to step 3 and pre-fill
                    window["-WIZARD_STEP_1-"].update(visible=False)
                    window["-WIZARD_STEP_3-"].update(visible=True)
                    window["-DISK_EXIST-"].update(value=True)
                    window["-DISK_NEW-"].update(value=False)
                    window["-DISK_SIZE-"].update(disabled=True)
                    window["-DISK_PATH-"].update(image_path, disabled=False)
                    wizard_step = 3
                    window["-WIZARD_BACK-"].update(disabled=False)
                    window["-WIZARD_NEXT-"].update("下一步")
                sg.popup_quick_message(f"已跳转到创建向导并预填好镜像路径: {os.path.basename(image_path)}")

        if event == "-OPEN_DOWNLOAD_FOLDER-":
            download_path = download_mgr.downloads_dir
            try:
                os.startfile(download_path)
            except Exception as e:
                sg.popup_error(f"无法打开文件夹: {download_path}\n错误: {e}")

        if event == "-CREATE_NAT-":
            if selected_vswitch_name:
                subnet = sg.popup_get_text("请输入NAT网络的子网地址 (例如: 192.168.100.0/24):", "创建NAT网络")
                if subnet:
                    gateway = sg.popup_get_text(f"请输入 {selected_vswitch_name} 交换机的网关IP地址 (例如: 192.168.100.1):", "设置网关")
                    if gateway:
                        # Extract prefix from subnet, e.g., 24 from 192.168.100.0/24
                        try:
                            prefix = subnet.split('/')[1]
                            # Create NAT Network
                            success, output = create_nat_network(selected_vswitch_name, subnet)
                            if success:
                                # Set IP on the vSwitch to act as gateway
                                success_ip, output_ip = set_vswitch_ip(selected_vswitch_name, gateway, prefix)
                                if success_ip:
                                    sg.popup_quick_message("NAT网络创建并配置成功！")
                                else:
                                    if "already exists" in output_ip:
                                        sg.popup_error(f"设置网关IP失败: IP地址 {gateway} 已被占用或已配置。", title="IP冲突")
                                    else:
                                        sg.popup_error(f"设置网关IP失败: {output_ip}")
                            else:
                                if "重名" in output or "duplicate" in output.lower():
                                    error_message = f"""创建NAT网络失败: 名称 '{selected_vswitch_name}' 已被系统其他网络占用。

请为此虚拟交换机更换一个名称后重试。"""
                                    sg.popup_error(error_message, title="名称冲突")
                                else:
                                    sg.popup_error(f"创建NAT网络失败: {output}")
                            
                            refresh_vswitch_table(window)
                            # Manually trigger table event to refresh NAT panel
                            window.write_event_value("-VSWITCH_TABLE-", window["-VSWITCH_TABLE-"].SelectedRows)

                        except IndexError:
                            sg.popup_error("子网地址格式不正确，请确保包含前缀长度，例如: /24")
        
        if event == "-ADD_NAT_RULE-":
            if selected_vswitch_name:
                if create_add_nat_rule_window(selected_vswitch_name):
                    # Refresh NAT panel by re-selecting the row
                    window.write_event_value("-VSWITCH_TABLE-", window["-VSWITCH_TABLE-"].SelectedRows)

        if event == "-DELETE_NAT_RULE-":
            if selected_vswitch_name and values["-NAT_RULES_TABLE-"]:
                selected_rule_index = values["-NAT_RULES_TABLE-"][0]
                rules_data = window["-NAT_RULES_TABLE-"].Values
                if selected_rule_index < len(rules_data):
                    proto, ext_port, _, _ = rules_data[selected_rule_index]
                    rule_to_delete = {"Protocol": proto, "RemotePort": ext_port}
                    
                    if sg.popup_ok_cancel(f"确定要删除端口 {ext_port} ({proto}) 的转发规则吗？", title="确认删除") == "OK":
                        success, output = remove_nat_rule(selected_vswitch_name, rule_to_delete)
                        if success:
                            sg.popup_quick_message("规则已删除。")
                        else:
                            sg.popup_error(f"删除失败: {output}")
                        # Refresh NAT panel by re-selecting the row
                        window.write_event_value("-VSWITCH_TABLE-", window["-VSWITCH_TABLE-"].SelectedRows)

        if event == "-SET_GW_IP-":
            if selected_vswitch_name:
                ip_address_prefix = sg.popup_get_text("请输入网关的IP地址和前缀长度 (例如: 192.168.100.1/24):", "设置网关IP")
                if ip_address_prefix:
                    try:
                        ip_address, prefix = ip_address_prefix.split('/')
                        success, output = set_vswitch_ip(selected_vswitch_name, ip_address, prefix)
                        if success:
                            sg.popup_quick_message("网关IP设置成功！")
                        else:
                            if "already exists" in output:
                                sg.popup_error(f"设置失败: IP地址 {ip_address} 已被占用或已配置。", title="IP冲突")
                            else:
                                sg.popup_error(f"设置失败: {output}")
                    except ValueError:
                        sg.popup_error("格式不正确。请确保使用 IP/前缀 的格式, 例如: 192.168.100.1/24")
            else:
                sg.popup_error("请先选择一个内部交换机。")

        # --- Image Events ---
        if event == "-BROWSE_LOCAL_IMG-":
            path = values["-LOCAL_IMG_PATH-"]
            if path:
                images = get_local_images([path])
                image_data = [[img.get('name'), img.get('size'), img.get('path')] for img in images]
                window["-LOCAL_IMG_TABLE-"].update(values=image_data)

        # --- System Check Events ---
        if event == "-CHECK_HYPERV-":
            window["-STATUS_TEXT-"].update("正在检查...")
            window.refresh()
            status = check_hyperv_status()
            color = "red"
            if "permissions" in status or "access is denied" in status: status_text = "权限不足，无法检查Hyper-V状态。"
            elif status == "Enabled": status_text, color = "Hyper-V 已安装并启用。", "green"
            elif status in ["Disabled", "Absent"]: 
                status_text, color = "Hyper-V 未安装或未启用。", "orange"
                window["-INSTALL_HYPERV-"].update(visible=True)
                window["-INSTALL_WARN-"].update(visible=True)
            else: status_text = status
            window["-STATUS_TEXT-"].update(status_text, text_color=color)

        if event == "-INSTALL_HYPERV-":
            if sg.popup_ok_cancel("此操作将安装Hyper-V功能并可能需要重启电脑，确定吗？", title="确认安装") == "OK":
                window["-INSTALL_HYPERV-"].update(disabled=True)
                success, output = install_hyperv()
                if success: sg.popup("Hyper-V 安装命令已成功执行！请手动重启电脑以完成安装。")
                else: sg.popup_error(f"安装失败: {output}")
                window["-INSTALL_HYPERV-"].update(disabled=False)

        # --- VM Wizard Events ---
        if event == "-WIZARD_NEXT-":
            if wizard_step < 6:
                window[f"-WIZARD_STEP_{wizard_step}-"].update(visible=False)
                wizard_step += 1
                window[f"-WIZARD_STEP_{wizard_step}-"].update(visible=True)
                window["-WIZARD_BACK-"].update(disabled=False)
                if wizard_step == 4: # Network
                    switches = [s['Name'] for s in get_vswitches() if s.get("SwitchType") != "Private"]
                    window["-VM_VSWITCH-"].update(values=switches, value=switches[0] if switches else "")
                if wizard_step == 5: # Installation Options
                    # Populate downloaded images table
                    completed_downloads = []
                    all_downloads = download_mgr.get_all_downloads()
                    for url, data in all_downloads.items():
                        if data.get('status') == 'completed':
                            filepath = os.path.join(download_mgr.downloads_dir, data['filename'])
                            try:
                                size = os.path.getsize(filepath)
                                size_str = f"{size / _1GB:.2f} GB" if size > _1GB else f"{size / _1MB:.2f} MB"
                                completed_downloads.append([data['filename'], size_str])
                            except FileNotFoundError:
                                continue # Skip if file is missing
                    window["-DOWNLOADED_IMG_TABLE-"].update(values=completed_downloads)

                if wizard_step == 6: # Summary
                    # Determine which ISO path to use
                    iso_path = ""
                    if values["-ISO_TAB_GROUP-"] == "-TAB_ISO_LOCAL-":
                        iso_path = values["-ISO_PATH-"]
                    elif values["-ISO_TAB_GROUP-"] == "-TAB_ISO_DOWNLOADED-":
                        selected_indices = values["-DOWNLOADED_IMG_TABLE-"]
                        if selected_indices:
                            selected_row = window["-DOWNLOADED_IMG_TABLE-"].Values[selected_indices[0]]
                            filename = selected_row[0]
                            iso_path = os.path.join(download_mgr.downloads_dir, filename)

                    summary = f"虚拟机名称: {values['-VM_NAME-']}\n"
                    summary += f"存储位置: {values['-VM_PATH-']}\n"
                    summary += f"内存: {int(values['-VM_MEM-'])} MB\n"
                    summary += f"CPU核心数: {int(values['-VM_CPU-'])}\n"
                    if values['-DISK_NEW-']:
                        summary += f"硬盘: 创建新硬盘 ({values['-DISK_SIZE-']} GB)\n"
                    else:
                        summary += f"硬盘: 使用现有硬盘 ({values['-DISK_PATH-']})\n"
                    summary += f"网络: {values['-VM_VSWITCH-']}\n"
                    summary += f"安装介质: {os.path.basename(iso_path) if iso_path else '无'}\n"
                    window["-VM_SUMMARY-"].update(summary)
                    window["-WIZARD_NEXT-"].update("创建虚拟机")
            else: # Create VM
                # Validation
                if not all([values["-VM_NAME-"], values["-VM_PATH-"], values["-VM_VSWITCH-"]]):
                    sg.popup_error("请填写所有必填字段！")
                else:
                    # Determine ISO path again before creation
                    iso_path = None
                    # Check if the user wants to install from an image
                    if values["-DISK_NEW-"]: # Only consider ISO if creating a new disk
                        if values["-ISO_TAB_GROUP-"] == "-TAB_ISO_LOCAL-":
                            iso_path = values["-ISO_PATH-"]
                        elif values["-ISO_TAB_GROUP-"] == "-TAB_ISO_DOWNLOADED-":
                            selected_indices = values["-DOWNLOADED_IMG_TABLE-"]
                            if selected_indices:
                                selected_row = window["-DOWNLOADED_IMG_TABLE-"].Values[selected_indices[0]]
                                filename = selected_row[0]
                                iso_path = os.path.join(download_mgr.downloads_dir, filename)

                    success, output = create_new_vm(
                        name=values["-VM_NAME-"],
                        memory_mb=int(values["-VM_MEM-"]),
                        cpu_cores=int(values["-VM_CPU-"]),
                        vhd_path=os.path.join(values["-VM_PATH-"], values["-VM_NAME-"], f"{values["-VM_NAME-"]}.vhdx") if values["-DISK_NEW-"] else None,
                        vhd_size_gb=int(values["-DISK_SIZE-"]) if values["-DISK_NEW-"] else None,
                        existing_vhd_path=values["-DISK_PATH-"] if values["-DISK_EXIST-"] else None,
                        vswitch_name=values["-VM_VSWITCH-"],
                        iso_path=iso_path,
                        enable_secure_boot=values["-SECURE_BOOT-"]
                    )
                    if success:
                        sg.popup("虚拟机创建成功！")
                        refresh_vm_table(window)
                    else:
                        sg.popup_error(f"创建失败: {output}")

        if event == "-WIZARD_BACK-":
            if wizard_step > 1:
                window[f"-WIZARD_STEP_{wizard_step}-"].update(visible=False)
                wizard_step -= 1
                window[f"-WIZARD_STEP_{wizard_step}-"].update(visible=True)
                window["-WIZARD_NEXT-"].update("下一步")
                if wizard_step == 1:
                    window["-WIZARD_BACK-"].update(disabled=True)

        if event == "-DISK_EXIST-":
            window["-DISK_PATH-"].update(disabled=False)
            window["-DISK_SIZE-"].update(disabled=True)
        if event == "-DISK_NEW-":
            window["-DISK_PATH-"].update(disabled=True)
            window["-DISK_SIZE-"].update(disabled=False)

    window.close()

if __name__ == "__main__":
    import ctypes, sys
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    if is_admin():
        main()
    else:
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
