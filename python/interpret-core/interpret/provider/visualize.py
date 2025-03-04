# Copyright (c) 2019 Microsoft Corporation
# Distributed under the MIT software license

from abc import ABC, abstractmethod
import logging

log = logging.getLogger(__name__)


class VisualizeProvider(ABC):
    @abstractmethod
    def render(self, explanation, key=-1, **kwargs):
        pass  # pragma: no cover


class AutoVisualizeProvider(VisualizeProvider):
    def __init__(self, **kwargs):
        self.provider = None
        self.kwargs = kwargs

    def render(self, explanation, key=-1, **kwargs):
        if self.provider is None:
            self.provider = DashProvider(**self.kwargs)

        self.provider.render(explanation, key=key, **kwargs)


class PreserveProvider(VisualizeProvider):
    def render(self, explanation, key=-1, **kwargs):
        file_name = kwargs.pop("file_name", None)

        # NOTE: Preserve didn't support returning everything. If key is -1 default to key is None.
        # This is for backward-compatibility. All of this will be deprecated shortly anyway.
        if key == -1:
            key = None

        # Get visual object
        visual = explanation.visualize(key=key)

        # Output to front-end/file
        self._preserve_output(
            explanation.name, visual, selector_key=key, file_name=file_name, **kwargs
        )
        return None

    def _preserve_output(
        self, explanation_name, visual, selector_key=None, file_name=None, **kwargs
    ):
        from plotly.offline import iplot, plot, init_notebook_mode
        from IPython.display import display, display_html
        from base64 import b64encode

        from plotly import graph_objs as go
        from pandas.core.generic import NDFrame
        import dash.development.base_component as dash_base

        init_notebook_mode(connected=True)

        def render_html(html_string):
            base64_html = b64encode(html_string.encode("utf-8")).decode("ascii")
            final_html = """<iframe src="data:text/html;base64,{data}" width="100%" height=400 frameBorder="0"></iframe>""".format(
                data=base64_html
            )
            display_html(final_html, raw=True)

        if visual is None:  # pragma: no cover
            msg = "No visualization for explanation [{0}] with selector_key [{1}]".format(
                explanation_name, selector_key
            )
            log.error(msg)
            if file_name is None:
                render_html(msg)
            else:
                pass
            return False

        if isinstance(visual, go.Figure):
            if file_name is None:
                iplot(visual, **kwargs)
            else:
                plot(visual, filename=file_name, **kwargs)
        elif isinstance(visual, NDFrame):
            if file_name is None:
                display(visual, **kwargs)
            else:
                visual.to_html(file_name, **kwargs)
        elif isinstance(visual, str):
            if file_name is None:
                render_html(visual)
            else:
                with open(file_name, "w") as f:
                    f.write(visual)
        elif isinstance(visual, dash_base.Component):  # pragma: no cover
            msg = "Preserving dash components is currently not supported."
            if file_name is None:
                render_html(msg)
            log.error(msg)
            return False
        else:  # pragma: no cover
            msg = "Visualization cannot be preserved for type: {0}.".format(
                type(visual)
            )
            if file_name is None:
                render_html(msg)
            log.error(msg)
            return False

        return True


class DashProvider(VisualizeProvider):
    def __init__(self, addr=None, base_url=None, use_relative_links=False):
        from ..visual.dashboard import AppRunner

        self.app_runner = AppRunner(
            addr, base_url=base_url, use_relative_links=use_relative_links
        )

    def _idempotent_start(self):
        status = self.app_runner.status()
        if not status["thread_alive"]:
            self.app_runner.start()

    def link(self, explanation, **kwargs):
        self._idempotent_start()

        # Register
        share_tables = kwargs.pop("share_tables", None)
        self.app_runner.register(explanation, share_tables=share_tables)

        url = self.app_runner.display_link(explanation)
        return url

    def render(self, explanation, **kwargs):
        self._idempotent_start()

        # Register
        share_tables = kwargs.pop("share_tables", None)
        self.app_runner.register(explanation, share_tables=share_tables)

        # Display
        open_link = isinstance(explanation, list)
        self.app_runner.display(explanation, open_link=open_link)
