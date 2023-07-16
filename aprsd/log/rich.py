from datetime import datetime
from logging import LogRecord
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterable, List, Optional, Union

from rich._log_render import LogRender
from rich.logging import RichHandler
from rich.text import Text, TextType
from rich.traceback import Traceback


if TYPE_CHECKING:
    from rich.console import Console, ConsoleRenderable, RenderableType
    from rich.table import Table

from aprsd import utils


FormatTimeCallable = Callable[[datetime], Text]


class APRSDRichLogRender(LogRender):

    def __init__(
        self, *args,
        show_thread: bool = False,
        thread_width: Optional[int] = 10,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.show_thread = show_thread
        self.thread_width = thread_width

    def __call__(
            self,
            console: "Console",
            renderables: Iterable["ConsoleRenderable"],
            log_time: Optional[datetime] = None,
            time_format: Optional[Union[str, FormatTimeCallable]] = None,
            level: TextType = "",
            path: Optional[str] = None,
            line_no: Optional[int] = None,
            link_path: Optional[str] = None,
            thread_name: Optional[str] = None,
    ) -> "Table":
        from rich.containers import Renderables
        from rich.table import Table

        output = Table.grid(padding=(0, 1))
        output.expand = True
        if self.show_time:
            output.add_column(style="log.time")
        if self.show_thread:
            rgb = str(utils.rgb_from_name(thread_name)).replace(" ", "")
            output.add_column(style=f"rgb{rgb}", width=self.thread_width)
        if self.show_level:
            output.add_column(style="log.level", width=self.level_width)
        output.add_column(ratio=1, style="log.message", overflow="fold")
        if self.show_path and path:
            output.add_column(style="log.path")
        row: List["RenderableType"] = []
        if self.show_time:
            log_time = log_time or console.get_datetime()
            time_format = time_format or self.time_format
            if callable(time_format):
                log_time_display = time_format(log_time)
            else:
                log_time_display = Text(log_time.strftime(time_format))
            if log_time_display == self._last_time and self.omit_repeated_times:
                row.append(Text(" " * len(log_time_display)))
            else:
                row.append(log_time_display)
                self._last_time = log_time_display
        if self.show_thread:
            row.append(thread_name)
        if self.show_level:
            row.append(level)

        row.append(Renderables(renderables))
        if self.show_path and path:
            path_text = Text()
            path_text.append(
                path, style=f"link file://{link_path}" if link_path else "",
            )
            if line_no:
                path_text.append(":")
                path_text.append(
                    f"{line_no}",
                    style=f"link file://{link_path}#{line_no}" if link_path else "",
                )
            row.append(path_text)

        output.add_row(*row)
        return output


class APRSDRichHandler(RichHandler):
    """APRSD's extension of rich's RichHandler to show threads.

        show_thread (bool, optional): Show the name of the thread in log entry. Defaults to False.
        thread_width (int, optional): The number of characters to show for thread name. Defaults to 10.
     """

    def __init__(
        self, *args,
        show_thread: bool = True,
        thread_width: Optional[int] = 10,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.show_thread = show_thread
        self.thread_width = thread_width
        kwargs["show_thread"] = show_thread
        kwargs["thread_width"] = thread_width
        self._log_render = APRSDRichLogRender(
            show_time=True,
            show_level=True,
            show_path=True,
            omit_repeated_times=False,
            level_width=None,
            show_thread=show_thread,
            thread_width=thread_width,
        )

    def render(
        self, *, record: LogRecord,
        traceback: Optional[Traceback],
        message_renderable: "ConsoleRenderable",
    ) -> "ConsoleRenderable":
        """Render log for display.

        Args:
            record (LogRecord): log Record.
            traceback (Optional[Traceback]): Traceback instance or None for no Traceback.
            message_renderable (ConsoleRenderable): Renderable (typically Text) containing log message contents.

        Returns:
            ConsoleRenderable: Renderable to display log.
        """
        path = Path(record.pathname).name
        level = self.get_level_text(record)
        time_format = None if self.formatter is None else self.formatter.datefmt
        log_time = datetime.fromtimestamp(record.created)
        thread_name = record.threadName

        log_renderable = self._log_render(
            self.console,
            [message_renderable] if not traceback else [
                message_renderable,
                traceback,
            ],
            log_time=log_time,
            time_format=time_format,
            level=level,
            path=path,
            line_no=record.lineno,
            link_path=record.pathname if self.enable_link_path else None,
            thread_name=thread_name,
        )
        return log_renderable
