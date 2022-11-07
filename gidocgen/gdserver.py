# SPDX-FileCopyrightText: 2022  Emmanuele Bassi
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import os
import posixpath
import urllib

from http import server

try:
    from magic import from_file as magic_from_file
except ImportError:
    magic_from_file = None

from . import config, gir, log, gdgenerate, utils


HELP_MSG = "Serve the gi-docgen output locally"


class GDHTTPRequestHandler(server.SimpleHTTPRequestHandler):
    SUFFIXES = [
        '.html',
        '/index.html',
        '/',
        '',
    ]

    extensions_map = {
        **server.SimpleHTTPRequestHandler.extensions_map,
        ** {
            ".ttf": "font/ttf",
            ".woff": "font/woff",
            ".woff2": "font/woff2",
        },
    }

    def translate_path(self, path):
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        trailing_slash = path.rstrip().endswith('/')
        path = urllib.parse.unquote(path)
        path = posixpath.normpath(path)
        words = path.split('/')
        words = filter(None, words)
        path = self.base_path
        for word in words:
            if os.path.dirname(word) or word in (os.curdir, os.pardir):
                # Ignore components that are not a simple file/directory name
                continue
            path = os.path.join(path, word)
        if trailing_slash:
            path += '/'
        return path

    def do_GET(self):
        # cut off a query string
        original_path = self.path.split('?', 1)[0]
        # try to find file
        self.path = self.get_path_that_exists(original_path)
        if not self.path:
            return
        server.SimpleHTTPRequestHandler.do_GET(self)

    def get_path_that_exists(self, original_path):
        # Try to strip trailing slash
        trailing_slash = original_path.endswith('/')
        original_path = original_path.rstrip('/')
        # Try to detect file by applying various suffixes
        tries = []
        for suffix in self.SUFFIXES:
            if not trailing_slash and suffix == '/':
                # if original request does not have trailing slash, skip the '/' suffix
                # so that base class can redirect if needed
                continue
            path = original_path + suffix
            if os.path.exists(self.translate_path(path)):
                return path
            tries.append(path)
        log.warning(f"Unable to find '{original_path}' or variations: {tries}")
        return None

    def guess_type(self, path):
        mimetype = server.SimpleHTTPRequestHandler.guess_type(self, path)
        # If the default guess is too generic, try the python-magic library
        if mimetype == 'application/octet-stream' and magic_from_file:
            mimetype = magic_from_file(path, mime=True)
        return mimetype

    def log_message(self, fmt, *args):
        log.info(fmt % args)


class RootedHTTPServer(server.HTTPServer):
    def __init__(self, base_path, *args, **kwargs):
        server.HTTPServer.__init__(self, *args, **kwargs)
        self.RequestHandlerClass.base_path = base_path


def add_args(parser):
    # Reuse the generate arguments
    gdgenerate.add_args(parser)
    # Add the local server arguments
    parser.add_argument("--bind", "-b", dest="server", default="127.0.0.1",
                        help="The IP used to serve HTTP requests")
    parser.add_argument("--port", "-p", dest="port", type=int, default=8080,
                        help="The port used to serve HTTP requests")


def run(options):
    log.info(f"Loading config file: {options.config}")

    # We need to re-implement gdgenerate.run() here, because the output
    # directory is computed from the configuration and/or the namespace
    # of the introspection data; we could reuse gdgenerate.run(), but it
    # would mean doing the configuration and GIR parsing twice
    conf = config.GIDocConfig(options.config)

    output_dir = options.output_dir or os.getcwd()

    content_dirs = options.content_dirs
    if content_dirs == []:
        content_dirs = [os.getcwd()]

    if options.templates_dir is not None:
        templates_dir = options.templates_dir
    else:
        templates_dir = conf.get_templates_dir()
        if templates_dir is None:
            templates_dir = os.path.join(os.path.dirname(__file__), 'templates')

    theme_name = conf.get_theme_name(default=options.theme_name)
    theme_conf = config.GITemplateConfig(templates_dir, theme_name)

    log.debug(f"Templates directory: {templates_dir}")
    log.info(f"Theme name: {theme_conf.name}")
    log.info(f"Output directory: {output_dir}")

    paths = []
    paths.extend(options.include_paths)
    paths.extend(utils.default_search_paths())
    log.debug(f"Search paths: {paths}")

    log.info("Parsing GIR file")
    parser = gir.GirParser(search_paths=paths)
    parser.parse(options.infile)

    log.checkpoint()
    if options.dry_run:
        return 0

    gdgenerate.gen_reference(conf, options, parser.get_repository(),
                             templates_dir, theme_conf,
                             content_dirs, output_dir)

    if options.no_namespace_dir:
        ns_dir = output_dir
    else:
        namespace = parser.get_repository().namespace
        ns_dir = os.path.join(output_dir, f"{namespace.name}-{namespace.version}")

    RootedHTTPServer.allow_reuse_address = True

    log.checkpoint()
    try:
        httpd = RootedHTTPServer(ns_dir,
                                 (options.server, options.port),
                                 GDHTTPRequestHandler)
    except OSError as e:
        log.error(f"Could not listen on port {options.port}, server {options.server}: {e}")
        return 1
    try:
        log.info(f"Serving site at: http://{options.server}:{options.port} - Press CTRL-C to stop")
        httpd.serve_forever()
    except Exception as e:
        log.warning(f"Error: {e}")
        return 1
    except KeyboardInterrupt:
        log.info("Terminating local server")
        httpd.socket.close()

    return 0
