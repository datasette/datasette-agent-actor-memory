import logging

from datasette import hookimpl, Response
from datasette_vite import vite_entry

from .router import router
from . import routes  # noqa: F401 — triggers decorator registration

logger = logging.getLogger(__name__)


def _method_dispatch_routes(raw_routes):
    """Combine routes with the same path pattern into method-dispatching views.

    ``datasette_plugin_router`` registers GET and POST for the same URL as
    separate ``(pattern, view)`` tuples, but Datasette matches only the
    *first* pattern that fits. Here we group by path and build a single
    wrapper that returns 405 for unsupported methods.

    Lifted from datasette-paper.
    """
    from collections import defaultdict

    by_path = defaultdict(dict)
    order = []

    for entry in raw_routes:
        path = entry.path
        method = entry.method.upper()
        if path not in by_path:
            order.append(path)
        by_path[path][method] = entry.fn

    result = []
    for path in order:
        method_map = by_path[path]
        if len(method_map) == 1:
            result.append((path, next(iter(method_map.values()))))
        else:

            def _make_dispatcher(m):
                async def dispatcher(
                    request,
                    datasette=None,
                    scope=None,
                    receive=None,
                    send=None,
                ):
                    method = request.method.upper()
                    handler = m.get(method)
                    if handler is None:
                        allowed = ", ".join(sorted(m.keys()))
                        return Response(
                            f"Method {method} not allowed",
                            status=405,
                            headers={"Allow": allowed},
                        )
                    return await handler(
                        request,
                        datasette=datasette,
                        scope=scope,
                        receive=receive,
                        send=send,
                    )

                return dispatcher

            result.append((path, _make_dispatcher(dict(method_map))))

    return result


@hookimpl
def register_routes():
    return _method_dispatch_routes(router._routes)


@hookimpl
def extra_template_vars(datasette):
    return {
        "datasette_agent_actor_memory_vite_entry": vite_entry(
            datasette=datasette,
            plugin_package="datasette_agent_actor_memory",
        ),
    }


@hookimpl
def register_agent_tools(datasette):
    from .tools import TOOLS

    return TOOLS


@hookimpl
def menu_links(datasette, actor, request=None):
    if not actor:
        return []
    return [
        {
            "href": datasette.urls.path("/-/agents-actor-memory/"),
            "label": "Memories",
        }
    ]


@hookimpl
async def startup(datasette):
    from .migrations import ensure_migrations

    internal = datasette.get_internal_database()
    if getattr(internal, "is_temp_disk", False):
        logger.warning(
            "datasette-agent-actor-memory: internal DB is ephemeral "
            "(default --internal is a tempfile that gets deleted on exit). "
            "Memories will not persist across restarts. Pass "
            "--internal <path> to retain memories."
        )
    await ensure_migrations(internal)
