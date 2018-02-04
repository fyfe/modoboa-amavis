# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from modoboa_amavis.models.policy import Mailaddr, Policy, Users, Wblist
from modoboa_amavis.models.quarantine import Maddr, Msgrcpt, Msgs, Quarantine

__all__ = [
    # Policy Models
    "Mailaddr",
    "Policy",
    "Users",
    "Wblist",
    # Quarantine Models
    "Maddr",
    "Msgrcpt",
    "Msgs",
    "Quarantine",
]
