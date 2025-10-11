# SPDX-FileCopyrightText: 2021 GNOME Foundation
#
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

project('gi-docgen',
  version: '2025.6',
  meson_version: '>= 0.55.0',
)

py = import('python').find_installation('python3',
  modules: [
    'jinja2',
    'markdown',
    'markupsafe',
    'packaging',
    'pygments',
    'typogrify',
  ],
)

markdown_version = run_command(
  py, '-c', 'import markdown; print(markdown.__version__)',
  check: true,
).stdout().strip()

if not markdown_version.version_compare('>=3.2')
  error('gi-docgen requires at least markdown >= 3.2')
endif

if py.language_version().version_compare('<3.11')
  tomli_version = run_command(
    py, '-c', 'import tomli; print(tomli.__version__)',
    check: false,
  ).stdout().strip()
  if tomli_version.version_compare('>=1.0')
    message('Falling back to toml on Python <3.11')
  else
    toml_version = run_command(
      py, '-c', 'import toml; print(toml.__version__)',
      check: false,
    ).stdout().strip()
    if toml_version.version_compare('>=0.10.2')
      warning('Falling back to deprecated toml module; please update to tomli')
    else
      error('tomli 1.0 or newer required on Python 3.10 and older')
    endif
  endif
endif

configure_file(
  input: 'gi-docgen.py',
  output: 'gi-docgen',
  copy: true,
  install: not meson.is_subproject(),
  install_dir: get_option('bindir'),
)

# When using gi-docgen as a sub-project
dummy_dep = declare_dependency()
meson.override_find_program('gi-docgen', find_program('gi-docgen.py'))

pkgconf = configuration_data()
pkgconf.set('VERSION', meson.project_version())
configure_file(
  input: 'gi-docgen.pc.in',
  output: 'gi-docgen.pc',
  configuration: pkgconf,
  install: not meson.is_subproject(),
  install_dir: get_option('datadir') / 'pkgconfig',
)

if not meson.is_subproject()
  install_subdir('gidocgen', install_dir: py.get_install_dir())
endif

# Development tests should not be run when in a subproject
if get_option('development_tests') and not meson.is_subproject()
  flake8 = find_program('flake8', required: false)
  if flake8.found()
    test('flake8',
      flake8,
      args: [
        '--show-source',
        meson.current_source_dir() / 'gidocgen',
      ],
    )
  endif

#  mypy = find_program('mypy', required: false)
#  if mypy.found()
#    test('mypy',
#      mypy,
#      args: [
#        '--ignore-missing-imports',
#        '--disallow-incomplete-defs',
#        meson.current_source_dir() / 'gidocgen',
#      ],
#      should_fail: true,
#    )
#  endif
endif
