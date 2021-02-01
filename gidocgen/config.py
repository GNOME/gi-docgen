# SPDX-FileCopyrightText: 2021 GNOME Foundation <https://gnome.org>
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import os
import toml

from . import log



class GIDocConfig:
    """Load and represent the configuration for gidocgen"""
    def __init__(self, config_file = None):
        self._config_file = config_file

        self._config = {}
        if self._config_file is not None:
            try:
                log.debug(f"Reading configuration file: {self._config_file}")
                self._config = toml.load(self._config_file)
            except toml.TomlDecodeError as err:
                log.error(f"Invalid configuration file: {self._config_file}: {err}")

    def get_templates_dir(self, default = None):
        theme = self._config.get('theme', {})
        return theme.get('templates_dir', default)

    def get_theme_name(self, default = None):
        theme = self._config.get('theme', {})
        return theme.get('name', default)

    def get_library_name(self, default = None):
        library = self._config.get('library', {})
        return library.get('name', default)

    def get_website_url(self, default = None):
        library = self._config.get('library', {})
        return library.get('website_url', default)

    @property
    def namespace(self):
        library = self._config.get('library', {})
        namespace = library['namespace']
        version = library['version']
        return f"{namespace}-{version}"

    @property
    def authors(self):
        library = self._config.get('library', {})
        return library.get('authors', 'Unknown authors')

    @property
    def license(self):
        library = self._config.get('library', {})
        return library.get('license', 'All rights reserved')

    @property
    def website_url(self):
        library = self._config.get('library', {})
        return library.get('website_url', '')

    @property
    def browse_url(self):
        library = self._config.get('library', {})
        return library.get('browse_url', '')

    @property
    def dependencies(self):
        library = self._config.get('library', None)
        if library is None:
            return {}

        retval = {}
        dependencies = self._config.get('dependencies', {})
        for gir_name, dep in dependencies.items():
            res = {}
            res['name'] = dep.get('name', 'Unknown')
            res['description'] = dep.get('description', 'No description provided')
            res['docs_url'] = dep.get('docs_url', '#')
            retval[gir_name] = res
            log.info(f"Found dependency {gir_name}: {res}")

        return retval

    @property
    def content_files(self):
        extra = self._config.get('extra', {})
        return extra.get('content_files', [])



class GITemplateConfig:
    """Load and represent the template configuration"""
    def __init__(self, templates_dir, template_name):
        self._templates_dir = templates_dir
        self._template_name = template_name
        self._config_file = os.path.join(templates_dir, template_name, f"{template_name}.toml")

        self._config = {}
        try:
            log.debug(f"Reading template configuration file: {self._config_file}")
            self._config = toml.load(self._config_file)
        except toml.TomlDecodeError as err:
            log.error(f"Invalid template configuration file: {self._config_file}: {err}")

    @property
    def name(self):
        metadata = self._config.get('metadata', {})
        return metadata.get('name', self._template_name)

    @property
    def css(self):
        css = self._config.get('css', {})
        return css.get('style', None)

    @property
    def extra_files(self):
        extra = self._config.get('extra_files', {})
        return extra.get('files', [])

    @property
    def templates(self):
        return self._config.get('templates', {})

    @property
    def class_template(self):
        templates = self._config.get('templates', {})
        return templates.get('class', 'class.html')

    @property
    def interface_template(self):
        templates = self._config.get('templates', {})
        return templates.get('interface', 'interface.html')

    @property
    def namespace_template(self):
        templates = self._config.get('templates', {})
        return templates.get('namespace', 'namespace.html')

    @property
    def content_template(self):
        templates = self._config.get('templates', {})
        return templates.get('content', 'content.html')

    @property
    def enum_template(self):
        templates = self._config.get('templates', {})
        return templates.get('enum', 'enum.html')

    @property
    def flags_template(self):
        templates = self._config.get('templates', {})
        return templates.get('flags', 'flags.html')

    @property
    def error_template(self):
        templates = self._config.get('templates', {})
        return templates.get('error', 'error.html')
