

import flet as ft
import os
from powershell_utils import get_vms_data, start_vm, shutdown_vm, stop_vm, check_hyperv_status, install_hyperv, get_vswitches, remove_vswitch, get_network_adapters, create_vswitch, get_nat_networks, get_nat_rules, add_nat_rule, remove_nat_rule, get_online_images, get_local_images, create_new_vm
from download_manager import DownloadManager
from config import load_config, save_config

def main(page: ft.Page):
    page.title = "Hyper-V 统一管理器"
    page.window_width = 1200
    page.window_height = 800

    config = load_config()

    # --- Download Manager Setup ---
    download_tasks_list = ft.Column([], scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    def on_download_progress(download_id, progress, downloaded_size, total_size):
        for item in download_tasks_list.controls:
            if isinstance(item, ft.Card) and item.data == download_id:
                item.content.content.controls[1].controls[0].value = progress / 100
                item.content.content.controls[1].controls[1].value = f"{progress:.1f}% ({downloaded_size / (1024*1024):.2f}MB / {total_size / (1024*1024):.2f}MB)"
                page.update()
                return

    def on_download_complete(download_id, filepath):
        for item in download_tasks_list.controls:
            if isinstance(item, ft.Card) and item.data == download_id:
                item.content.content.controls[0].controls[1].value = "已完成"
                item.content.content.controls[0].controls[1].color = "green"
                item.content.content.controls[1].controls[0].value = 1.0
                item.content.content.controls[1].controls[1].value = "100%"
                page.update()
                return

    def on_download_error(download_id, error_message):
        for item in download_tasks_list.controls:
            if isinstance(item, ft.Card) and item.data == download_id:
                item.content.content.controls[0].controls[1].value = f"失败: {error_message}"
                item.content.content.controls[0].controls[1].color = "red"
                page.update()
                return

    dm = DownloadManager(download_folder=config.get("download_folder", "./downloads"), on_progress=on_download_progress, on_complete=on_download_complete, on_error=on_download_error)

    # --- Helper Functions ---
    def create_help_button(title, content_text):
        def open_help_dialog(e):
            page.dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(title),
                content=ft.Text(content_text),
                actions=[ft.TextButton("关闭", on_click=lambda e: setattr(page.dialog, "open", False) or page.update())],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.dialog.open = True
            page.update()
        return ft.IconButton(icon=ft.Icons.HELP_OUTLINE, on_click=open_help_dialog)

    # --- VM View ---
    vm_table = ft.DataTable(columns=[
        ft.DataColumn(ft.Text("名称")),
        ft.DataColumn(ft.Text("状态")),
        ft.DataColumn(ft.Text("操作系统")),
        ft.DataColumn(ft.Text("IP地址")),
        ft.DataColumn(ft.Text("CPU使用率")),
        ft.DataColumn(ft.Text("内存(MB)"))
    ], rows=[])

    selected_vm_name = ft.Text(size=20, weight=ft.FontWeight.BOLD)
    detail_state = ft.Text()
    detail_os = ft.Text()
    detail_ip = ft.Text()
    detail_cpu = ft.Text()
    detail_mem = ft.Text()

    start_button = ft.ElevatedButton("开机")
    shutdown_button = ft.ElevatedButton("安全关机", color="white", bgcolor="orange700")
    stop_button = ft.ElevatedButton("强制关闭", color="white", bgcolor="red700")

    details_view = ft.Column([
        ft.Row([ft.Icon(ft.Icons.COMPUTER_OUTLINED), selected_vm_name]),
        ft.Divider(height=10),
        ft.Row([ft.Text("状态:", weight=ft.FontWeight.BOLD, width=60), detail_state]),
        ft.Row([ft.Text("系统:", weight=ft.FontWeight.BOLD, width=60), detail_os]),
        ft.Row([ft.Text("IP地址:", weight=ft.FontWeight.BOLD, width=60), detail_ip]),
        ft.Row([ft.Text("CPU:", weight=ft.FontWeight.BOLD, width=60), detail_cpu]),
        ft.Row([ft.Text("内存:", weight=ft.FontWeight.BOLD, width=60), detail_mem]),
    ])

    actions_view = ft.Row([start_button, shutdown_button, stop_button], spacing=10)
    actions_panel = ft.Column(controls=[
        ft.Card(content=ft.Container(details_view, padding=15)),
        ft.Card(content=ft.Container(actions_view, padding=15))
    ], visible=False, spacing=10)

    def update_actions_panel(vm_details):
        selected_vm_name.value = vm_details.get('name', '')
        detail_state.value = vm_details.get('state', '')
        detail_os.value = vm_details.get('os', '')
        detail_ip.value = vm_details.get('ip', '')
        detail_cpu.value = vm_details.get('cpu', '')
        detail_mem.value = vm_details.get('mem', '')
        is_running = (vm_details.get('state') == 'Running')
        start_button.disabled = is_running
        shutdown_button.disabled = not is_running
        stop_button.disabled = not is_running
        actions_panel.visible = True
        page.update()

    def handle_vm_select(e):
        if e.control.selected:
            row = e.control
            vm_details = {
                "name": row.cells[0].content.value,
                "state": row.cells[1].content.value,
                "os": row.cells[2].content.value,
                "ip": row.cells[3].content.value,
                "cpu": row.cells[4].content.value,
                "mem": row.cells[5].content.value,
            }
            update_actions_panel(vm_details)
        else:
            actions_panel.visible = False
            page.update()
    vm_table.on_select_changed = handle_vm_select

    def refresh_vms_table(e=None):
        vm_table.rows.clear()
        vm_data = get_vms_data()
        if vm_data:
            for vm in vm_data:
                ip_addresses = vm.get('IPAddresses')
                ip_text = ', '.join(ip_addresses) if ip_addresses else 'N/A'
                vm_table.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(vm.get('Name'))),
                    ft.DataCell(ft.Text(vm.get('State'))),
                    ft.DataCell(ft.Text(vm.get('GuestOS', 'N/A'))),
                    ft.DataCell(ft.Text(ip_text)),
                    ft.DataCell(ft.Text(f"{vm.get('CPUUsage', 0)}%")),
                    ft.DataCell(ft.Text(f"{vm.get('MemoryAssigned', 0) // 1048576}"))
                ]))
        else:
             vm_table.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text("Hyper-V未安装或无虚拟机", color="orange")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text(""))]))
        page.update()

    def perform_vm_action(action_func, vm_name):
        success, _ = action_func(vm_name)
        if success:
            refresh_vms_table()
            actions_panel.visible = False
            page.update()
    start_button.on_click = lambda e: perform_vm_action(start_vm, selected_vm_name.value)
    shutdown_button.on_click = lambda e: perform_vm_action(shutdown_vm, selected_vm_name.value)

    view_vms = ft.Row([ft.Column([ft.ElevatedButton("刷新列表", on_click=refresh_vms_table), vm_table], scroll=ft.ScrollMode.ALWAYS, expand=True), ft.VerticalDivider(width=1), ft.Column([actions_panel], width=350)], expand=True)
    
    # --- System Check View ---
    status_text = ft.Text("点击下方按钮检查Hyper-V状态...", size=16)
    install_button = ft.ElevatedButton("一键安装 Hyper-V", icon=ft.Icons.ADD, on_click=lambda e: show_install_confirmation(), bgcolor="green", color="white")
    warning_text = ft.Text("警告：安装过程需要管理员权限...", color="orange", weight=ft.FontWeight.BOLD)
    confirm_install_button = ft.ElevatedButton("确认安装", on_click=lambda e: do_install(), bgcolor="red")
    cancel_install_button = ft.TextButton("取消", on_click=lambda e: hide_install_confirmation())
    confirmation_row = ft.Row([ft.Text("此操作将重启电脑，确定吗？"), confirm_install_button, cancel_install_button], visible=False)

    def show_install_confirmation():
        install_button.visible = False
        confirmation_row.visible = True
        page.update()

    def hide_install_confirmation():
        install_button.visible = True
        confirmation_row.visible = False
        page.update()

    def do_install():
        hide_install_confirmation()
        status_text.value = "正在安装Hyper-V..."
        install_button.disabled = True
        page.update()
        success, output = install_hyperv()
        status_text.value = "Hyper-V 安装命令已成功执行！请手动重启电脑。" if success else f"安装失败: {output}"
        install_button.disabled = False
        page.update()

    def check_status_click(e):
        status_text.value = "正在检查..."
        install_button.visible = False
        warning_text.visible = False
        hide_install_confirmation()
        page.update()
        status = check_hyperv_status()
        if status == "Enabled":
            status_text.value = "Hyper-V 已安装并启用。"
            status_text.color = "green"
        elif status in ["Disabled", "Absent"]:
            status_text.value = "Hyper-V 未安装或未启用。"
            status_text.color = "orange"
            install_button.visible = True
            warning_text.visible = True
        else:
            status_text.value = status
            status_text.color = "red"
        page.update()

    install_button.visible = False
    warning_text.visible = False
    view_system = ft.Column(controls=[
        ft.Text("系统状态检查", size=30),
        ft.Row([ft.ElevatedButton("检查Hyper-V状态", on_click=check_status_click, icon=ft.Icons.SYNC), create_help_button("Hyper-V状态检查", "检查当前系统是否已安装并启用了Hyper-V功能。 ")]),
        status_text,
        warning_text,
        ft.Row([install_button, create_help_button("一键安装 Hyper-V", "点击此按钮将自动安装Hyper-V功能。 ")]),
        confirmation_row,
    ], spacing=20)

    # --- Network View ---
    vswitch_table = ft.DataTable(columns=[ft.DataColumn(ft.Text("名称")), ft.DataColumn(ft.Text("类型")), ft.DataColumn(ft.Text("备注"))], rows=[])
    delete_button = ft.ElevatedButton("删除所选", icon=ft.Icons.DELETE, color="white", bgcolor="red700", disabled=True)
    nat_rules_table = ft.DataTable(columns=[ft.DataColumn(ft.Text("协议")), ft.DataColumn(ft.Text("外部端口")), ft.DataColumn(ft.Text("内部IP")), ft.DataColumn(ft.Text("内部端口")), ft.DataColumn(ft.Text("操作"))], rows=[])
    add_nat_rule_button = ft.ElevatedButton("添加规则", icon=ft.Icons.ADD)
    nat_rules_panel = ft.Column([ft.Text("端口映射规则", size=20), ft.Row([add_nat_rule_button]), nat_rules_table], visible=False)
    new_nat_external_port = ft.TextField(label="外部端口")
    new_nat_internal_ip = ft.TextField(label="内部IP地址")
    new_nat_internal_port = ft.TextField(label="内部端口")
    new_nat_protocol = ft.Dropdown(label="协议", options=[ft.dropdown.Option("TCP"), ft.dropdown.Option("UDP")], value="TCP")
    current_selected_nat_switch_name = ""

    def refresh_nat_rules_table():
        nat_rules_table.rows.clear()
        if current_selected_nat_switch_name:
            rules = get_nat_rules(current_selected_nat_switch_name)
            if rules:
                for rule in rules:
                    nat_rules_table.rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(rule.get('Protocol', 'N/A'))),
                        ft.DataCell(ft.Text(str(rule.get('RemotePort', 'N/A')))),
                        ft.DataCell(ft.Text(rule.get('InternalIPAddress', 'N/A'))),
                        ft.DataCell(ft.Text(str(rule.get('InternalPort', 'N/A')))),
                        ft.DataCell(ft.IconButton(icon=ft.Icons.DELETE, on_click=lambda e, r=rule: delete_nat_rule_click(r))),
                    ]))
        page.update()

    def delete_nat_rule_click(rule):
        pass

    def close_add_nat_rule_dialog(e):
        page.dialog.open = False
        page.update()

    def add_nat_rule_submit(e):
        pass

    add_nat_rule_dialog = ft.AlertDialog(title=ft.Text("添加端口映射规则"), content=ft.Column([new_nat_external_port, new_nat_internal_ip, new_nat_internal_port, new_nat_protocol]), actions=[ft.TextButton("取消", on_click=close_add_nat_rule_dialog), ft.ElevatedButton("添加", on_click=add_nat_rule_submit)])

    def open_add_nat_rule_dialog(e):
        page.dialog = add_nat_rule_dialog
        page.dialog.open = True
        page.update()
    add_nat_rule_button.on_click = open_add_nat_rule_dialog

    def refresh_vswitches_table(e=None):
        vswitch_table.rows.clear()
        switches = get_vswitches()
        if switches:
            for switch in switches:
                vswitch_table.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(switch.get('Name'))),
                    ft.DataCell(ft.Text(switch.get('SwitchType'))),
                    ft.DataCell(ft.Text(switch.get('Notes'))),
                ]))
        delete_button.disabled = True
        nat_rules_panel.visible = False
        page.update()

    def delete_vswitch_click(e):
        pass
    delete_button.on_click = delete_vswitch_click

    def handle_vswitch_select(e):
        selected_row = next((r for r in vswitch_table.rows if r.selected), None)
        delete_button.disabled = not selected_row
        if selected_row and selected_row.cells[1].content.value == "NAT":
            global current_selected_nat_switch_name
            current_selected_nat_switch_name = selected_row.cells[0].content.value
            refresh_nat_rules_table()
            nat_rules_panel.visible = True
        else:
            nat_rules_panel.visible = False
        page.update()
    vswitch_table.on_select_changed = handle_vswitch_select

    view_network = ft.Row([ft.Column([ft.Row([ft.Text("虚拟交换机管理", size=30), ft.ElevatedButton("刷新", on_click=refresh_vswitches_table), ft.ElevatedButton("创建", on_click=lambda e: open_create_vswitch_dialog()), delete_button]), vswitch_table], expand=True), ft.VerticalDivider(), ft.Column([nat_rules_panel], expand=True)])
    
    # --- Create VM View ---
    current_step = 0
    
    vm_name_field = ft.TextField(label="虚拟机名称", expand=True)
    vm_location_field = ft.TextField(label="虚拟机存储位置", expand=True)
    vm_location_picker = ft.FilePicker(on_result=lambda e: setattr(vm_location_field, "value", e.path) if e.path else None)
    page.overlay.append(vm_location_picker)
    step1_content = ft.Column([
        ft.Row([vm_name_field, create_help_button("虚拟机名称", "为您的虚拟机指定一个唯一的名称。 ")]),
        ft.Row([vm_location_field, ft.ElevatedButton("浏览", on_click=lambda e: vm_location_picker.get_directory_path())])
    ])

    vm_memory_slider = ft.Slider(min=512, max=16384, divisions=31, value=2048, label="内存: {value} MB", expand=True)
    vm_cpu_slider = ft.Slider(min=1, max=8, divisions=7, value=2, label="CPU核心数: {value}", expand=True)
    step2_content = ft.Column([
        ft.Row([vm_memory_slider, create_help_button("内存", "分配给虚拟机的内存大小。 ")]),
        ft.Row([vm_cpu_slider, create_help_button("CPU核心数", "分配给虚拟机的CPU核心数量。 ")])
    ])

    vm_disk_option = ft.RadioGroup(content=ft.Row([ft.Radio(value="new", label="创建新虚拟硬盘"), ft.Radio(value="existing", label="使用现有虚拟硬盘")]), value="new")
    vm_new_disk_size_field = ft.TextField(label="新硬盘大小 (GB)", value="60")
    vm_existing_disk_path_field = ft.TextField(label="现有硬盘路径", expand=True)
    vm_existing_disk_picker = ft.FilePicker(on_result=lambda e: setattr(vm_existing_disk_path_field, "value", e.path) if e.path else None)
    page.overlay.append(vm_existing_disk_picker)
    step3_content = ft.Column([
        ft.Row([vm_disk_option, create_help_button("硬盘选项", "选择创建新硬盘或使用现有硬盘。 ")]),
        ft.Row([vm_new_disk_size_field]),
        ft.Row([vm_existing_disk_path_field, ft.ElevatedButton("浏览", on_click=lambda e: vm_existing_disk_picker.pick_files(allowed_extensions=["vhdx", "vhd"]))])
    ])

    vm_network_dropdown = ft.Dropdown(label="选择虚拟交换机", options=[ft.dropdown.Option(s.get("Name")) for s in get_vswitches() if s.get("SwitchType") != "Private"], expand=True)
    step4_content = ft.Column([ft.Row([vm_network_dropdown, create_help_button("选择虚拟交换机", "选择一个虚拟交换机连接虚拟机。 ")])])

    vm_install_media_option = ft.RadioGroup(content=ft.Row([ft.Radio(value="local_iso", label="本地ISO文件"), ft.Radio(value="downloaded_image", label="已下载镜像")]), value="local_iso")
    vm_local_iso_path_field = ft.TextField(label="本地ISO路径", expand=True)
    vm_local_iso_picker = ft.FilePicker(on_result=lambda e: setattr(vm_local_iso_path_field, "value", e.path) if e.path else None)
    page.overlay.append(vm_local_iso_picker)
    vm_downloaded_image_dropdown = ft.Dropdown(label="选择已下载镜像", options=[ft.dropdown.Option(d["filename"]) for d in dm.get_all_downloads().values() if d["status"] == "completed"], expand=True)
    step5_content = ft.Column([
        ft.Row([vm_install_media_option, create_help_button("安装介质", "选择用于安装操作系统的介质。 ")]),
        ft.Row([vm_local_iso_path_field, ft.ElevatedButton("浏览", on_click=lambda e: vm_local_iso_picker.pick_files(allowed_extensions=["iso"]))]),
        ft.Row([vm_downloaded_image_dropdown])
    ])

    summary_text = ft.Text("")
    step6_content = ft.Column([summary_text])

    all_steps = [step1_content, step2_content, step3_content, step4_content, step5_content, step6_content]
    for i, step in enumerate(all_steps):
        step.visible = (i == 0)

    def update_summary():
        summary = f"虚拟机名称: {vm_name_field.value}\n"
        summary += f"存储位置: {vm_location_field.value}\n"
        summary += f"内存: {vm_memory_slider.value} MB\n"
        summary += f"CPU核心数: {vm_cpu_slider.value}\n"
        summary += f"硬盘选项: {vm_disk_option.value}\n"
        if vm_disk_option.value == "new":
            summary += f"  新硬盘大小: {vm_new_disk_size_field.value} GB\n"
        else:
            summary += f"  现有硬盘路径: {vm_existing_disk_path_field.value}\n"
        summary += f"网络: {vm_network_dropdown.value}\n"
        summary += f"安装介质: {vm_install_media_option.value}\n"
        if vm_install_media_option.value == "local_iso":
            summary += f"  本地ISO: {vm_local_iso_path_field.value}\n"
        else:
            summary += f"  已下载镜像: {vm_downloaded_image_dropdown.value}\n"
        summary_text.value = summary

    def go_to_step(step_index):
        nonlocal current_step
        current_step = step_index
        for i, step in enumerate(all_steps):
            step.visible = (i == current_step)
        back_button.disabled = (current_step == 0)
        if current_step == len(all_steps) - 1:
            update_summary()
            next_button.text = "创建虚拟机"
            next_button.icon = ft.Icons.ADD_CIRCLE
            next_button.on_click = create_vm_submit
        else:
            next_button.text = "下一步"
            next_button.icon = None
            next_button.on_click = lambda e: go_to_step(current_step + 1)
        page.update()

    back_button = ft.ElevatedButton("上一步", on_click=lambda e: go_to_step(current_step - 1), disabled=True)
    next_button = ft.ElevatedButton("下一步", on_click=lambda e: go_to_step(current_step + 1))

    view_create = ft.Column([
        ft.Text("创建虚拟机向导", size=30),
        ft.Column(all_steps, expand=True, scroll=ft.ScrollMode.ADAPTIVE),
        ft.Row([back_button, next_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    ])

    # --- Image View ---
    local_image_paths_list = ft.Column([])
    local_images_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("名称")),
            ft.DataColumn(ft.Text("大小")),
            ft.DataColumn(ft.Text("路径")),
        ],
        rows=[]
    )

    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)

    def refresh_local_images_list():
        local_image_paths_list.controls.clear()
        for path in config["local_image_paths"]:
            local_image_paths_list.controls.append(
                ft.Row([
                    ft.Text(path, expand=True),
                    ft.IconButton(icon=ft.Icons.DELETE, on_click=lambda e, p=path: remove_local_image_path(p))
                ])
            )
        refresh_local_images_table()
        page.update()

    def add_local_image_path(e):
        if file_picker.result and file_picker.result.path:
            new_path = file_picker.result.path
            if new_path not in config["local_image_paths"]:
                config["local_image_paths"].append(new_path)
                save_config(config)
                refresh_local_images_list()
        page.update()

    def pick_folder_dialog(e):
        file_picker.on_result = add_local_image_path
        file_picker.get_directory_path()

    def remove_local_image_path(path_to_remove):
        config["local_image_paths"].remove(path_to_remove)
        save_config(config)
        refresh_local_images_list()

    def refresh_local_images_table():
        local_images_table.rows.clear()
        images = get_local_images(config["local_image_paths"])
        if images:
            for img in images:
                local_images_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(img.get("name") )),
                        ft.DataCell(ft.Text(img.get("size") )),
                        ft.DataCell(ft.Text(img.get("path") )),
                    ])
                )
        else:
            local_images_table.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text("未找到本地镜像", color="orange")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text(""))
            ]))
        page.update()

    def build_local_images_view():
        return ft.Column([
            ft.Row([
                ft.Text("本地镜像目录", size=16, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton("添加目录", on_click=pick_folder_dialog, icon=ft.Icons.FOLDER_OPEN),
                ft.ElevatedButton("刷新镜像", on_click=lambda e: refresh_local_images_table(), icon=ft.Icons.REFRESH),
            ]),
            local_image_paths_list,
            ft.Divider(),
            ft.Text("本地镜像列表", size=16, weight=ft.FontWeight.BOLD),
            local_images_table,
        ], scroll=ft.ScrollMode.ALWAYS, expand=True)

    def build_online_images_view():
        online_images = get_online_images()
        image_cards = []
        for img in online_images:
            def start_download_click(e, url, filename):
                download_id = dm.start_download(url, filename)
                download_tasks_list.controls.append(
                    ft.Card(
                        data=download_id,
                        content=ft.Container(
                            padding=15,
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(filename, size=16, weight=ft.FontWeight.BOLD, expand=True),
                                    ft.Text("等待中", color="grey")
                                ]),
                                ft.Row([
                                    ft.ProgressBar(width=200, value=0),
                                    ft.Text("0%")
                                ]),
                                ft.Row([
                                    ft.ElevatedButton("暂停", on_click=lambda e, did=download_id: dm.pause_download(did)),
                                    ft.ElevatedButton("继续", on_click=lambda e, did=download_id: dm.resume_download(did)),
                                    ft.ElevatedButton("取消", on_click=lambda e, did=download_id: dm.cancel_download(did)),
                                ])
                            ])
                        )
                    )
                )
                navigate_to_view(3, 2) # Switch to Image view, Downloads tab
                page.update()

            card = ft.Card(
                content=ft.Container(
                    padding=15,
                    content=ft.Column([
                        ft.Text(img.get("name"), size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(img.get("description")),
                        ft.Text(f"分类: {img.get("category")}"),
                        ft.Text(f"版本: {img.get("version")}"),
                        ft.Text(f"大小: {img.get("size")}"),
                        ft.ElevatedButton("下载", icon=ft.Icons.DOWNLOAD, on_click=lambda e, url=img.get("download_url"), filename=img.get("name") + ".iso": start_download_click(e, url, filename))
                    ])
                )
            )
            image_cards.append(card)
        return ft.Column(image_cards, scroll=ft.ScrollMode.ALWAYS, expand=True)

    image_tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="本地镜像", content=build_local_images_view()),
            ft.Tab(text="在线市场", content=build_online_images_view()),
            ft.Tab(text="下载任务", content=download_tasks_list),
        ],
        expand=1,
    )

    view_images = ft.Column([
        ft.Text("系统镜像管理", size=30),
        image_tabs,
        create_help_button("系统镜像管理", "管理本地的ISO/VHDX镜像文件，以及从在线市场获取常用操作系统镜像。 ")
    ])

    refresh_local_images_list()

    # --- Main Layout ---
    all_views = [view_vms, view_network, view_create, view_images, view_system]
    for i, view in enumerate(all_views):
        view.visible = (i == 0)

    def navigate_to_view(index, tab_index=None):
        rail.selected_index = index
        for i, view in enumerate(all_views):
            view.visible = (i == index)
        if index == 3 and tab_index is not None: # Special handling for image tabs
            image_tabs.selected_index = tab_index
        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.COMPUTER_OUTLINED, selected_icon=ft.Icons.COMPUTER, label="虚拟机"),
            ft.NavigationRailDestination(icon=ft.Icons.ROUTER_OUTLINED, selected_icon=ft.Icons.ROUTER, label="网络设置"),
            ft.NavigationRailDestination(icon=ft.Icons.ADD_BOX_OUTLINED, selected_icon=ft.Icons.ADD_BOX, label="创建虚拟机"),
            ft.NavigationRailDestination(icon=ft.Icons.IMAGE_OUTLINED, selected_icon=ft.Icons.IMAGE, label="系统镜像"),
            ft.NavigationRailDestination(icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label="系统检查"),
        ],
        on_change=lambda e: navigate_to_view(e.control.selected_index),
    )

    page.add(ft.Row([rail, ft.VerticalDivider(width=1), ft.Column(all_views, expand=True)], expand=True))
    
    # Initial data load
    refresh_vms_table()
    refresh_vswitches_table()

ft.app(target=main)
