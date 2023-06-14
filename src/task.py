# MIT License

# Copyright (c) 2023 Vlad Krupinski <mrvladus@yandex.ru>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from gi.repository import Gtk, Adw
from .application import gsettings
from .sub_task import SubTask
from .utils import Markup, TaskUtils, UserData


@Gtk.Template(resource_path="/io/github/mrvladus/List/task.ui")
class Task(Gtk.Box):
    __gtype_name__ = "Task"

    # Template items
    task_box = Gtk.Template.Child()
    task_delete_btn = Gtk.Template.Child()
    task_text = Gtk.Template.Child()
    task_status = Gtk.Template.Child()
    expand_btn = Gtk.Template.Child()
    accent_colors_btn = Gtk.Template.Child()
    accent_colors_popover = Gtk.Template.Child()
    task_edit_btn = Gtk.Template.Child()
    task_completed_btn = Gtk.Template.Child()
    task_edit_box = Gtk.Template.Child()
    task_edit_entry = Gtk.Template.Child()
    task_move_up_btn = Gtk.Template.Child()
    task_move_down_btn = Gtk.Template.Child()
    task_cancel_edit_btn = Gtk.Template.Child()
    sub_tasks_revealer = Gtk.Template.Child()
    delete_completed_btn_revealer = Gtk.Template.Child()
    delete_completed_btn = Gtk.Template.Child()
    sub_tasks = Gtk.Template.Child()

    # State
    expanded: bool = None

    def __init__(self, task: dict, window: Adw.ApplicationWindow):
        super().__init__()
        print("Add task:", task["text"])
        self.window = window
        self.parent = self.window.tasks_list
        self.task = task
        # Escape text and find URL's'
        self.text = Markup.escape(self.task["text"])
        self.text = Markup.find_url(self.text)
        # Check if task completed and toggle checkbox
        if self.task["completed"]:
            self.task_completed_btn.props.active = True
        # Set text
        self.task_text.props.label = self.text
        # Set accent color
        if self.task["color"] != "":
            self.add_css_class(f'task-{self.task["color"]}')
            self.task_status.add_css_class(f'progress-{self.task["color"]}')
        # Expand if sub-tasks exists
        if self.task["sub"] != [] and gsettings.get_value("tasks-expanded").unpack():
            self.expand(True)
        # Show or hide accent colors menu
        print(gsettings.get_value("show-accent-colors-menu").unpack())
        self.accent_colors_btn.props.visible = gsettings.get_value(
            "show-accent-colors-menu"
        ).unpack()

        # Add sub tasks
        for task in self.task["sub"]:
            self.sub_tasks.append(SubTask(task, self))
        self.update_statusbar()
        self.update_move_buttons()

    def expand(self, expanded: bool) -> None:
        self.expanded = expanded
        self.sub_tasks_revealer.set_reveal_child(expanded)
        self.expand_btn.set_icon_name(
            "go-up-symbolic" if expanded else "go-down-symbolic"
        )
        self.update_statusbar()

    def toggle_edit_mode(self) -> None:
        self.task_box.props.visible = not self.task_box.props.visible
        self.task_edit_box.props.visible = not self.task_edit_box.props.visible

    def update_statusbar(self) -> None:
        self.n_completed = 0
        self.n_total = 0
        for sub in self.task["sub"]:
            self.n_total += 1
            if sub["completed"]:
                self.n_completed += 1
        if self.n_total > 0:
            self.task_status.props.fraction = self.n_completed / self.n_total
        if not self.expanded and self.n_completed == 0:
            self.task_status.props.visible = False
        else:
            self.task_status.props.visible = True
        # Show delete completed button
        self.delete_completed_btn_revealer.set_reveal_child(self.n_completed > 0)

    def update_task(self, new_task: dict) -> None:
        new_data: dict = UserData.get()
        for i, task in enumerate(new_data["tasks"]):
            if task["text"] == self.task["text"]:
                new_data["tasks"][i] = new_task
                UserData.set(new_data)
                return

    def update_move_buttons(self) -> None:
        data: dict = UserData.get()
        idx: int = data["tasks"].index(self.task)
        length: int = len(data["tasks"])
        self.task_move_up_btn.props.sensitive = False if idx == 0 else True
        self.task_move_down_btn.props.sensitive = False if idx == length - 1 else True

    # --- Template handlers --- #

    @Gtk.Template.Callback()
    def on_task_delete(self, _) -> None:
        new_data: dict = UserData.get()
        for task in new_data["tasks"]:
            if task["text"] == self.task["text"]:
                new_data["tasks"].remove(task)
                break
        UserData.set(new_data)
        self.parent.remove(self)
        self.window.update_status()

    @Gtk.Template.Callback()
    def on_delete_completed_btn_clicked(self, _) -> None:
        # Remove data
        self.task["sub"] = [sub for sub in self.task["sub"] if not sub["completed"]]
        new_data: dict = UserData.get()
        for i, task in enumerate(new_data["tasks"]):
            if task["text"] == self.task["text"]:
                new_data["tasks"][i] = self.task
                UserData.set(new_data)
                break
        # Remove widgets
        to_remove = []
        childrens = self.sub_tasks.observe_children()
        for i in range(childrens.get_n_items()):
            child = childrens.get_item(i)
            if child.task["completed"]:
                to_remove.append(child)
        for task in to_remove:
            print("Remove:", task.task["text"])
            self.sub_tasks.remove(task)
        # Update statusbar
        self.update_statusbar()

    @Gtk.Template.Callback()
    def on_task_completed_btn_toggled(self, btn: Gtk.Button) -> None:
        self.task["completed"] = btn.props.active
        self.update_task(self.task)
        if self.task["completed"]:
            self.text = Markup.add_crossline(self.text)
        else:
            self.text = Markup.rm_crossline(self.text)
        self.task_text.props.label = self.text
        self.window.update_status()

    @Gtk.Template.Callback()
    def on_expand_btn_clicked(self, _) -> None:
        """Expand task row"""
        self.expand(not self.sub_tasks_revealer.get_child_revealed())

    @Gtk.Template.Callback()
    def on_sub_task_added(self, entry: Gtk.Entry) -> None:
        # Return if entry is empty
        if entry.get_buffer().props.text == "":
            return
        # Return if task exists
        for sub in self.task["sub"]:
            if sub["text"] == entry.get_buffer().props.text:
                return
        # Add new sub-task
        new_sub_task = TaskUtils.new_sub_task(entry.get_buffer().props.text)
        self.task["sub"].append(new_sub_task)
        self.update_task(self.task)
        # Add row
        sub_task = SubTask(new_sub_task, self)
        self.sub_tasks.append(sub_task)
        if sub_task.get_prev_sibling():
            sub_task.get_prev_sibling().update_move_buttons()
        self.update_statusbar()
        # Clear entry
        entry.get_buffer().props.text = ""

    @Gtk.Template.Callback()
    def on_task_edit_btn_clicked(self, _) -> None:
        self.toggle_edit_mode()
        # Set entry text and select it
        self.task_edit_entry.get_buffer().props.text = self.task["text"]
        self.task_edit_entry.select_region(0, len(self.task["text"]))
        self.task_edit_entry.grab_focus()

    @Gtk.Template.Callback()
    def on_task_cancel_edit_btn_clicked(self, _) -> None:
        self.toggle_edit_mode()

    @Gtk.Template.Callback()
    def on_task_edit(self, entry: Gtk.Entry) -> None:
        old_text: str = self.task["text"]
        new_text: str = entry.get_buffer().props.text
        # Return if text the same or empty
        if new_text == old_text or new_text == "":
            return
        # Return if task exists
        new_data: dict = UserData.get()
        for task in new_data["tasks"]:
            if task["text"] == new_text:
                return
        # Change task
        print(f"Change '{old_text}' to '{new_text}'")
        # Set new text
        self.task["text"] = new_text
        self.task["completed"] = False
        # Set new data
        for i, task in enumerate(new_data["tasks"]):
            if task["text"] == old_text:
                new_data["tasks"][i] = self.task
                UserData.set(new_data)
                break
        # Escape text and find URL's'
        self.text = Markup.escape(self.task["text"])
        self.text = Markup.find_url(self.text)
        # Check if text crosslined and toggle checkbox
        self.task_completed_btn.props.active = False
        # Set text
        self.task_text.props.label = self.text
        self.toggle_edit_mode()

    @Gtk.Template.Callback()
    def on_style_selected(self, btn: Gtk.Button) -> None:
        """Apply accent color"""
        self.accent_colors_popover.popdown()
        for i in btn.get_css_classes():
            color = ""
            if i.startswith("btn-"):
                color = i.split("-")[1]
                break
        # Color card
        self.set_css_classes(["card"] if color == "" else ["card", f"task-{color}"])
        # Color statusbar
        for c in self.task_status.get_css_classes():
            if "progress-" in c:
                self.task_status.remove_css_class(c)
        if color != "":
            self.task_status.add_css_class(f"progress-{color}")
        # Set new color
        self.task["color"] = color
        self.update_task(self.task)

    @Gtk.Template.Callback()
    def on_task_move_up_btn_clicked(self, _) -> None:
        new_data: dict = UserData.get()
        idx: int = new_data["tasks"].index(self.task)
        if idx == 0:
            return
        print(f"""Move task "{self.task['text']}" up""")
        # Move widget
        self.get_parent().reorder_child_after(self.get_prev_sibling(), self)
        # Update data
        new_data["tasks"][idx - 1], new_data["tasks"][idx] = (
            new_data["tasks"][idx],
            new_data["tasks"][idx - 1],
        )
        UserData.set(new_data)
        # Update task
        self.task = new_data["tasks"][idx - 1]
        # Update buttons
        self.update_move_buttons()
        self.get_next_sibling().update_move_buttons()

    @Gtk.Template.Callback()
    def on_task_move_down_btn_clicked(self, _) -> None:
        new_data: dict = UserData.get()
        idx: int = new_data["tasks"].index(self.task)
        if idx + 1 == len(new_data["tasks"]):
            return
        print(f"""Move task "{self.task['text']}" down""")
        # Move widget
        self.get_parent().reorder_child_after(self, self.get_next_sibling())
        # Update data
        new_data["tasks"][idx + 1], new_data["tasks"][idx] = (
            new_data["tasks"][idx],
            new_data["tasks"][idx + 1],
        )
        UserData.set(new_data)
        # Update task
        self.task = new_data["tasks"][idx + 1]
        # Update buttons
        self.update_move_buttons()
        self.get_prev_sibling().update_move_buttons()
