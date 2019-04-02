import copy
import shutil
import typing
import pathlib

from distutils import log
from distutils.cmd import Command


class ForisPluginCommand(Command):
    def get_plugin_name(self):
        for package in self.distribution.packages:
            if package.startswith("foris_plugins."):
                return package[len("foris_plugins.") :]
        raise RuntimeError(
            "This package doesn't seem like a Foris plugin. No foris plugin package found!"
        )


class make_messages(ForisPluginCommand):
    """Extracts and merges transation of foris plugin"""

    MESSAGE_EXTRACTORS = [
        ("**.py", "python", None),
        ("**/templates/**.j2", "jinja2", {"encoding": "utf-8"}),
    ]

    description = __doc__
    user_options: typing.List[str] = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from babel.messages import frontend

        plugin_name = self.get_plugin_name()
        plugin_path = pathlib.Path("foris_plugins") / plugin_name

        # make sure that locale directory exists
        (plugin_path / "locale").mkdir(parents=True, exist_ok=True)

        # set message extractors in distribution
        distribution = copy.copy(self.distribution)
        setattr(distribution, "message_extractors", {plugin_path: self.MESSAGE_EXTRACTORS})

        # run extract messages
        log.info("Starting to extract messages for foris plugin")
        cmd = frontend.extract_messages(copy.copy(distribution))
        cmd.no_location = True
        cmd.output_file = plugin_path / "locale/foris.pot"
        cmd.ensure_finalized()
        cmd.run()

        # run update catalogs
        log.info("Starting to update foris translations")
        cmd = frontend.update_catalog(copy.copy(distribution))
        cmd.domain = "foris"
        cmd.input_file = plugin_path / "locale/foris.pot"
        cmd.output_dir = plugin_path / "locale"
        cmd.ensure_finalized()
        cmd.run()


class clean(ForisPluginCommand):
    """Removes files created by foris commands"""

    description = __doc__
    user_options: typing.List[str] = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        plugin_name = self.get_plugin_name()
        plugin_path = pathlib.Path("foris_plugins") / plugin_name

        # remove all css files (excpecting that all .css file are generated using sass)
        css_path = plugin_path / "static/css"
        for path in css_path.glob("*.css"):
            log.info("Removing css file %s." % path)
            try:
                path.unlink()
            except OSError:
                pass

        # remove generated translations
        locale_path = plugin_path / "locale"
        for path in locale_path.glob("*/LC_MESSAGES/messages.po"):
            log.info("Removing generated translation file %s." % path)
            try:
                path.unlink()
            except OSError:
                pass

        # remove compiled translations
        for path in locale_path.glob("*/LC_MESSAGES/*.mo"):
            log.info("Removing compiled translation file %s." % path)
            try:
                path.unlink()
            except OSError:
                pass


class build(ForisPluginCommand):
    """Builds all foris files needed before creating a packages"""

    description = __doc__
    user_options: typing.List[str] = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        plugin_name = self.get_plugin_name()
        plugin_path = pathlib.Path("foris_plugins") / plugin_name

        # rename foris.po to messages.po to match the foris domain
        catalog_exists = False
        for path in plugin_path.glob("locale/*/LC_MESSAGES/foris.po"):
            catalog_exists = True
            shutil.copyfile(path, pathlib.Path(path).parent / "messages.po")

        if catalog_exists:
            # compile translation
            from babel.messages import frontend as babel

            distribution = copy.copy(self.distribution)
            cmd = babel.compile_catalog(distribution)
            cmd.directory = plugin_path / "locale"
            cmd.domain = "messages"
            cmd.ensure_finalized()
            cmd.run()
        else:
            log.info("No translations found. Plugin will not be translated.")
            log.info("To create translations you need to generate .pot file:")
            log.info("    python setup.py foris_make_messages")
            log.info("And prepare at least one catalog:")
            out_dir = plugin_path / "locale"
            pot_file = out_dir / "foris.pot"
            log.info(
                "    python setup.py init_catalog -D foris -i %s -d %s -l <lang>", pot_file, out_dir
            )

        # compile sass
        from sassutils import distutils as sass

        # make sure that sass directory exists
        (plugin_path / "static/sass").mkdir(parents=True, exist_ok=True)

        distribution = copy.copy(self.distribution)
        setattr(
            distribution,
            "sass_manifests",
            {"foris_plugins." + plugin_name: ("static/sass/", "static/css/")},
        )
        cmd = sass.build_sass(distribution)
        # cmd.output_style = "compressed"
        cmd.ensure_finalized()
        cmd.run()
        # rename xxx.sass.css -> xxx.css
        # there is a MR on github to strip it, but in hasn't been merge yet
        for path in plugin_path.glob("static/css/*.sass.css"):
            new_filename = path.name[: -len("sass.css")] + "css"
            path.rename(path.parent / new_filename)
