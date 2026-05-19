from __future__ import annotations

import htpy as h


# To update Bootstrap, follow their docs
# https://getbootstrap.com/docs/5.3/getting-started/download/#cdn-via-jsdelivr
BOOTSTRAP_CSS = (
    "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css"
)


def layout(*, content: h.Node, page_title: str = "Karsk") -> h.Element:
    return h.html(lang="en")[
        h.head[
            h.meta(charset="utf-8"),
            h.meta(name="viewport", content="width=device-width, initial-scale=1"),
            h.title[page_title],
            h.link(
                rel="stylesheet",
                href=BOOTSTRAP_CSS,
                crossorigin="anonymous",
            ),
        ],
        h.body(".bg-light")[header(), main(content)],
    ]


def header() -> h.Element:
    return h.div(".container-flud.bg-white.border-bottom.box-shadow")[
        h.div(".container")[
            h.header(".navbar.navbar-expand-lg.bg-navbar")[
                h.a(
                    ".link-body-emphasis.text-decoration-none",
                    href="/",
                )[h.span(".fs-1.ml-4")["Karsk 🥃"]]
            ]
        ]
    ]


def main(content: h.Node) -> h.Element:
    return h.main(".container")[h.div(".d-flex.flex-column.gap-4.p-4")[content]]
