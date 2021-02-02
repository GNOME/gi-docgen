project('gi-docgen',
  version: '0.0.1',
  meson_version: '>= 0.55.0',
)

py = import('python').find_installation('python3',
  modules: [
    'jinja2',
    'markdown',
    'pygments',
    'toml',
    'typogrify',
  ],
)

configure_file(
  input: 'gi-docgen.py',
  output: 'gi-docgen',
  copy: true,
  install: true,
  install_dir: get_option('bindir'),
)

install_subdir('gidocgen', install_dir: py.get_install_dir())
