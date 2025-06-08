# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

sys.path.insert(0, ROOT)
sys.path.insert(0, BASE_DIR)


def gen_ref(ver, title, names):
    refdir = os.path.join(BASE_DIR, "ref")
    pkg = "aodhclient"
    if ver:
        pkg = "{}.{}".format(pkg, ver)
        refdir = os.path.join(refdir, ver)
    if not os.path.exists(refdir):
        os.makedirs(refdir)
    idxpath = os.path.join(refdir, "index.rst")
    with open(idxpath, "w") as idx:
        idx.write(("%(title)s\n"
                   "%(signs)s\n"
                   "\n"
                   ".. toctree::\n"
                   "   :maxdepth: 1\n"
                   "\n") % {"title": title, "signs": "=" * len(title)})
        for name in names:
            idx.write("   %s\n" % name)
            rstpath = os.path.join(refdir, "%s.rst" % name)
            with open(rstpath, "w") as rst:
                rst.write(("%(title)s\n"
                           "%(signs)s\n"
                           "\n"
                           ".. automodule:: %(pkg)s.%(name)s\n"
                           "   :members:\n"
                           "   :undoc-members:\n"
                           "   :show-inheritance:\n"
                           "   :noindex:\n")
                          % {"title": " ".join([n.capitalize()
                                                for n in name.split("_")]),
                             "signs": "=" * len(name),
                             "pkg": pkg, "name": name})


gen_ref("v2", "Version 2 API", ["client"])

# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'openstackdocstheme',
    # 'sphinx.ext.intersphinx',
]

# autodoc generation is a bit aggressive and a nuisance when doing heavy
# text edit cycles.
# execute "export SPHINX_DEBUG=1" in your terminal to disable

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# openstackdocstheme options
openstackdocs_repo_name = 'openstack/python-aodhclient'
openstackdocs_bug_project = 'python-aodhclient'
openstackdocs_bug_tag = ''
copyright = '2015, OpenStack Foundation'

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'native'

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
# html_theme_path = ["."]
# html_theme = '_theme'
# html_static_path = ['static']
html_theme = 'openstackdocs'

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = ['_theme']

# Output file base name for HTML help builder.
htmlhelp_basename = 'aodhclientdoc'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
    ('index',
     'aodhclient.tex',
     'aodhclient Documentation',
     'OpenStack Foundation', 'manual'),
]

# Example configuration for intersphinx: refer to the Python standard library.
# intersphinx_mapping = {'http://docs.python.org/': None}
