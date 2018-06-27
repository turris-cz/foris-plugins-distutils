import copy
import glob
import os
import shutil

from distutils import log
from distutils.cmd import Command


class ForisPluginCommand(Command):
    def get_plugin_name(self):
        for package in self.distribution.packages:
            if package.startswith("foris_plugins."):
                return package[len("foris_plugins."):]
        raise RuntimeError(
            "This package doesn't seem like a Foris plugin. No foris plugin package found!"
        )


class make_messages(ForisPluginCommand):
    """Extracts and merges transation of foris plugin"""

    MESSAGE_EXTRACTORS = [
        ('**.py', 'python', None),
        ('**/templates/**.j2', 'jinja2', {'encoding': 'utf-8'}),
    ]

    description = __doc__
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from babel.messages import frontend

        plugin_name = self.get_plugin_name()
        plugin_path = os.path.join("foris_plugins", plugin_name)

        # set message extractors in distribution
        distribution = copy.copy(self.distribution)
        setattr(distribution, "message_extractors", {plugin_path: self.MESSAGE_EXTRACTORS})

        # run extract messages
        log.info("Starting to extract messages for foris plugin")
        cmd = frontend.extract_messages(copy.copy(distribution))
        cmd.no_location = True
        cmd.output_file = os.path.join(plugin_path, "locale", "foris.pot")
        cmd.ensure_finalized()
        cmd.run()

        # run update catalogs
        log.info("Starting to update foris translations")
        cmd = frontend.update_catalog(copy.copy(distribution))
        cmd.domain = "foris"
        cmd.input_file = os.path.join(plugin_path, "locale", "foris.pot")
        cmd.output_dir = os.path.join(plugin_path, "locale")
        cmd.ensure_finalized()
        cmd.run()


class clean(ForisPluginCommand):
    """Removes files created by foris commands"""

    description = __doc__
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        plugin_name = self.get_plugin_name()
        plugin_path = os.path.join("foris_plugins", plugin_name)

        # remove all css files (excpecting that all .css file are generated using sass)
        css_path = os.path.join(plugin_path, "static", "css", "*.css")
        for path in glob.glob(css_path):
            log.info("Removing css file %s." % path)
            try:
                os.remove(path)
            except OSError:
                pass

        # remove generated translations
        generated_translations_path = os.path.join(
            plugin_path, "locale", "*", "LC_MESSAGES", "messages.po")
        for path in glob.glob(generated_translations_path):
            log.info("Removing generated translation file %s." % path)
            try:
                os.remove(path)
            except OSError:
                pass

        # remove compiled translations
        compiled_translations_path = os.path.join(plugin_path, "locale", "*", "LC_MESSAGES", "*.mo")
        for path in glob.glob(compiled_translations_path):
            log.info("Removing compiled translation file %s." % path)
            try:
                os.remove(path)
            except OSError:
                pass


class build(ForisPluginCommand):
    """Builds all foris files needed before creating a packages"""

    description = __doc__
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        plugin_name = self.get_plugin_name()
        plugin_path = os.path.join("foris_plugins", plugin_name)

        # rename foris.po to messages to match the foris domain
        for path in glob.glob(
            os.path.join(plugin_path, "locale", "*", "LC_MESSAGES", "foris.po")
        ):
            shutil.copyfile(path, os.path.join(os.path.dirname(path), "messages.po"))

        # compile translation
        from babel.messages import frontend as babel
        distribution = copy.copy(self.distribution)
        cmd = babel.compile_catalog(distribution)
        cmd.directory = os.path.join(plugin_path, "locale")
        cmd.domain = "messages"
        cmd.ensure_finalized()
        cmd.run()

        # compile sass
        from sassutils import distutils as sass
        distribution = copy.copy(self.distribution)
        setattr(
            distribution, "sass_manifests",
            {"foris_plugins." + plugin_name: ('static/sass/', 'static/css/')}
        )
        cmd = sass.build_sass(distribution)
        # cmd.output_style = "compressed"
        cmd.ensure_finalized()
        cmd.run()
        # rename xxx.sass.css -> xxx.css
        # there is a MR on github to strip it, but in hasn't been merge yet
        for path in glob.glob(os.path.join(plugin_path, "static", "css", "*.sass.css")):
            filename = os.path.basename(path)[:-len("sass.css")] + "css"
            os.rename(path, os.path.join(os.path.dirname(path), filename))
