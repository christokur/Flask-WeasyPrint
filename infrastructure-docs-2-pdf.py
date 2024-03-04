import os
import pathlib
import re
import sys
import urllib.parse

from weasyprint import HTML
from weasyprint.urls import get_url_attribute

# Set site name and base URL
DEBUG_ENABLED = "DEBUG enabled"
DEBUG_ENABLED_SHOW_STACKTRACE = f"{DEBUG_ENABLED} - Showing stacktrace\n"
SITE_NAME = 'infrastructure-docs'
BASE_URL = 'http://localhost:1313'
OVERWRITE_IF_EXISTS = False

def handle_exception(exception: Exception) -> None:
    # TRACEBACK_PATTERN
    import os
    import sys
    import traceback

    pytest = any(k for k, _ in os.environ.items() if k.startswith("PYTEST"))
    # pycharm = any(k for k, _ in os.environ.items() if k.startswith("PYCHARM"))
    is_debug = not pytest and os.getenv("DEBUG", "no").lower() in ["true", "1", "yes", "on"]
    if is_debug:
        sys.stderr.write(DEBUG_ENABLED_SHOW_STACKTRACE)
        traceback.print_exception(exception.__class__, exception, exception.__traceback__)
        sys.stderr.write(DEBUG_ENABLED_SHOW_STACKTRACE)


def create_pdf_page(
    site_path: pathlib.Path,
    path: pathlib.Path,
    html: HTML,
    base_uri: urllib.parse.ParseResult,
    map:dict,
    pages:dict | None=None,
    links: dict | None=None,
) -> tuple[dict, dict]:
    """Create a PDF page and return a dictionary of links.
    :param map:
    """
    if pages is None:
        pages = {}
    if links is None:
        links = {}
    if path and not isinstance(path, pathlib.Path):
        path = pathlib.Path(path)
    for wrapper in html.wrapper_element.query_all('a'):
        element = wrapper.etree_element
        if element.tag == 'a' and element.get('href'):
            href = get_url_attribute(element, 'href', BASE_URL)
            if href is not None:
                uri = urllib.parse.urlparse(href)
                if BASE_URL in href or base_uri.netloc == uri.netloc:
                    href_ = re.sub(pattern=str(urllib.parse.urlunparse(base_uri)), repl="", string=href) or "/"
                    href_ = re.sub(pattern=r"#.*", repl="", string=href_) or "/"
                    doc = map.get(href_, None)
                    pag = href_.rstrip('/').lstrip('/')
                    pth = doc or str(site_path / f"{pag}.pdf")
                    element.attrib['href'] = f"file://{pth}"
                    if href not in links:
                        print(f"{href=}")
                        links[href] = (pth, path)
    try:
        sys.stdout.write(f"{path=!s}\n")
        pages[str(path)] = str(path).replace(str(site_path), "")
        path.parent.mkdir(exist_ok=True, parents=True)
        html.write_pdf(target=path) if not path.is_file() or OVERWRITE_IF_EXISTS else None
    except Exception as exc:
        handle_exception(exception=exc)
        sys.stderr.write(f"Error: {exc=!s}\n")
    return links, pages


def create_pdf_site(site_name: str=SITE_NAME, base_url:str=BASE_URL) -> None:
    # Parse base URI
    base_uri = urllib.parse.urlparse(base_url)
    # Create output directory if it doesn't exist
    site_path = pathlib.Path(SITE_NAME)
    site_path.mkdir(exist_ok=True)
    # Create HTML object and write to PDF
    sys.stdout.write(f"url={BASE_URL}\n")
    html = HTML(url=BASE_URL, base_url=BASE_URL)
    path = site_path / f"index.pdf"
    map = {
        "/": f"{site_name}/{path.name}"
    }
    links, pages = create_pdf_page(
        site_path=site_path,
        path=path,
        html=html,
        base_uri=base_uri,
        map=map,
    )

    links_pages = set([tup[0] for tup in links.values()])
    while len(links_pages) > len(pages):
        links, pages = create_pdf_links_pages(
            base_uri=base_uri,
            links=links,
            map=map,
            pages=pages,
            site_path=site_path,
        )
        links_pages = set([tup[0] for tup in links.values()])


def create_pdf_links_pages(
    base_uri,
    links,
    map,
    pages,
    site_path,
) -> tuple[dict, dict]:
    _links = links.copy()
    for href, tup in _links.items():
        pdf, parent = tup
        if pdf not in pages:
            try:
                sys.stdout.write(f"url={href}\n")
                html = HTML(url=href, base_url=BASE_URL)
                links, pages = create_pdf_page(
                    site_path=site_path,
                    path=pdf,
                    html=html,
                    base_uri=base_uri,
                    map=map,
                    links=links,
                    pages=pages,
                )
                sys.stdout.write(f"url={href} done\n")
            except Exception as exc:
                handle_exception(exception=exc)
                sys.stderr.write(f"Bad link: {href} on {str(parent)};{exc=!s}\n")
                sys.stderr.flush()
                pages[pdf] = None
    sys.stdout.write(f"Generated {len(pages)} pages\n")
    return links, pages


if __name__ == "__main__":
    create_pdf_site(site_name=SITE_NAME, base_url=BASE_URL)
