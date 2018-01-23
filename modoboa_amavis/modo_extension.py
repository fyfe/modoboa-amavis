# -*- coding: utf-8 -*-

"""
Amavis management frontend.

Provides:

* SQL quarantine management
* Per-domain settings

"""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy

from modoboa.core.extensions import ModoExtension, exts_pool
from modoboa.parameters import tools as param_tools

from modoboa_amavis import __version__, forms
from modoboa_amavis.lib import policy_management as pm
from modoboa_amavis.models.policy import User
from modoboa_amavis.utils import smart_bytes


class Amavis(ModoExtension):
    """The Amavis extension."""

    name = "modoboa_amavis"
    label = ugettext_lazy("Amavis frontend")
    version = __version__
    description = ugettext_lazy("Simple amavis management frontend")
    url = "quarantine"
    available_for_topredirection = True

    def load(self):
        param_tools.registry.add("global", forms.ParametersForm, "Amavis")
        param_tools.registry.add(
            "user", forms.UserSettings, ugettext_lazy("Quarantine"))

        if not User.objects.filter(email=smart_bytes("@.")).exists():
            # either a new install or migrating from <= 1.1.3
            # modoboa-amavis models are unmanaged so we can't use Django
            # migrations, this needs to be done manually.
            pm.migrate_policy_setup()

    def load_initial_data(self):
        """Create initial data for new install."""
        pm.create_catachall()


exts_pool.register_extension(Amavis)
