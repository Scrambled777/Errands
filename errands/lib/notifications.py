# Copyright 2024 Vlad Krupinskii <mrvladus@yandex.ru>
# SPDX-License-Identifier: MIT

from datetime import datetime

from gi.repository import Gio, GLib  # type:ignore

from errands.lib.data import TaskData, UserData
from errands.lib.gsettings import GSettings
from errands.lib.logging import Log
from errands.state import State


class ErrandsNotificationsDaemon:
    CHECK_INTERVAL_SEC: int = 30  # Check tasks every _ seconds

    def __init__(self) -> None:
        State.notifications_daemon = self
        self.start()

    # ------ PROPERTIES ------ #

    @property
    def due_tasks(self) -> list[TaskData]:
        """Get due tasks that haven't been notified yet"""

        return [
            t
            for t in UserData.tasks
            if t.due_date
            and datetime.fromisoformat(t.due_date).now() < datetime.now()
            and not t.notified
        ]

    # ------ PUBLIC METHODS ------ #

    def send(self, id: str, notification: Gio.Notification) -> None:
        """Send desktop Notification"""

        State.application.send_notification(id, notification)

    def start(self) -> None:
        """Start notifications daemon"""

        GLib.timeout_add_seconds(self.CHECK_INTERVAL_SEC, self.__check_data)

    # ------ PRIVATE METHODS ------ #

    def __check_data(self) -> bool:
        """Get due tasks and send notifications"""

        # If notifications is disabled - stop daemon
        if not GSettings.get("notifications-enabled"):
            return False

        Log.debug("Notifications: Check")

        for task in self.due_tasks:
            self.__send_due_notification(task)
            UserData.update_props(task.list_uid, task.uid, ["notified"], [True])

        return True

    def __send_due_notification(self, task: TaskData) -> None:
        Log.debug(f"Notifications: Send: {task.uid}")

        notification = Gio.Notification()
        notification.set_title(_("Task is Due"))
        notification.set_body(task.text)
        self.send(task.uid, notification)
