# -*- coding: utf-8 -*-

"""Amavis handlers."""

from __future__ import unicode_literals

from django.urls import reverse
from django.db.models import signals
from django.dispatch import receiver
from django.utils.translation import ugettext as _
from django.template import Template, Context

from modoboa.admin import models as admin_models
from modoboa.admin import signals as admin_signals
from modoboa.core import signals as core_signals
from modoboa.lib import signals as lib_signals
from modoboa.parameters import tools as param_tools

from modoboa_amavis import forms
from modoboa_amavis.lib import policy_management as pm
from modoboa_amavis.models import policy as policy_models
from modoboa_amavis.sql_connector import SQLconnector


@receiver(core_signals.extra_user_menu_entries)
def menu(sender, location, user, **kwargs):
    """Add extra menu entry."""
    if location == "top_menu":
        return [
            {"name": "quarantine",
             "label": _("Quarantine"),
             "url": reverse("modoboa_amavis:index")}
        ]
    return []


@receiver(core_signals.extra_static_content)
def extra_static_content(sender, caller, st_type, user, **kwargs):
    """Send extra javascript."""
    condition = (
        user.role == "SimpleUsers" or
        st_type != "js" or
        caller != "domains")
    if condition:
        return ""
    tpl = Template("""<script type="text/javascript">
$(document).bind('domform_init', function() {
    activate_widget.call($('#id_spam_subject_tag2_act'));
});
</script>
""")
    return tpl.render(Context({}))


@receiver(core_signals.get_top_notifications)
def check_for_pending_requests(sender, include_all, **kwargs):
    """Check if release requests are pending."""
    request = lib_signals.get_request()
    condition = (
        param_tools.get_global_parameter("user_can_release") or
        request.user.role == "SimpleUsers")
    if condition:
        return []

    nbrequests = SQLconnector(user=request.user).get_pending_requests()
    if not nbrequests:
        return [{"id": "nbrequests", "counter": 0}] if include_all \
            else []

    url = reverse("modoboa_amavis:index")
    url += "#listing/?viewrequests=1"
    return [{
        "id": "nbrequests", "url": url, "text": _("Pending requests"),
        "counter": nbrequests, "level": "danger"
    }]


@receiver(admin_signals.extra_domain_forms)
def extra_domain_form(sender, user, domain, **kwargs):
    """Return domain config form."""
    if not user.has_perm("admin.view_domains"):
        return []
    return [{
        "id": "amavis", "title": _("Content filter"),
        "cls": forms.DomainPolicyForm,
        "formtpl": "modoboa_amavis/domain_content_filter.html"
    }]


@receiver(admin_signals.get_domain_form_instances)
def fill_domain_instances(sender, user, domain, **kwargs):
    """Return domain instance."""
    if not user.has_perm("admin.view_domains"):
        return {}
    return {"amavis": domain}


# ------------------------------------------------------------------------------
# Policy Handlers
# ------------------------------------------------------------------------------

@receiver(signals.post_save, sender=admin_models.Domain)
def setup_domain_policy(sender, instance, created, **kwargs):
    """Setup Amavis policy for a domain."""
    if created:
        pm.setup_domain_policy(instance)
    elif instance.oldname != instance.name:
        old_name = "@%s" % instance.oldname
        new_name = "@%s" % instance.name
        pm.rename_user_and_policy(old_name, new_name, instance.name)


@receiver(signals.pre_delete, sender=admin_models.Domain)
def remove_domain_policy(sender, instance, **kwargs):
    """Remove Amavis policy for a domain."""
    name = "@%s" % instance.name
    pm.delete_user_and_policy(name)


@receiver(signals.post_save, sender=admin_models.DomainAlias)
def setup_domain_alias_policy(sender, instance, created, **kwargs):
    """Setup Amavis policy for a domain alias."""
    if created:
        pm.setup_domain_alias_policy(instance)


@receiver(signals.pre_delete, sender=admin_models.DomainAlias)
def remove_domain_alias_policy(sender, instance, **kwargs):
    """Remove Amavis policy for a domain alias."""
    name = "@%s" % instance.name
    pm.delete_user_and_policy(name)


@receiver(signals.post_save, sender=admin_models.Mailbox)
def setup_mailbox_policy(sender, instance, created, **kwargs):
    """Setup Amavis policy for a mailbox."""
    if created:
        pm.setup_mailbox_policy(instance)
    elif instance.old_full_address != instance.full_address:
        pm.rename_user_and_policy(
            instance.old_full_address,
            instance.full_address,
            instance.full_address
        )


@receiver(signals.pre_delete, sender=admin_models.Mailbox)
def remove_mailbox_policy(sender, instance, **kwargs):
    """Remove Amavis policy for a mailbox."""
    pm.delete_user_and_policy(instance.full_address)


@receiver(signals.post_save, sender=admin_models.AliasRecipient)
def setup_mailbox_alias_policy(sender, instance, created, **kwargs):
    """Setup Amavis policy for an alias recipient.

    FIXME: how to deal with distibution lists ?
    """
    if created:
        pm.setup_mailbox_alias_policy(instance)


@receiver(signals.pre_delete, sender=admin_models.Alias)
def remove_alias_policy(sender, instance, **kwargs):
    """Remove Amavis policy for a mailbox alias.
    The on delete signal watches Alias because it's deleted before
    AliasRecipient and it's Alias.address we need."""
    pm.delete_user_and_policy(
        instance.address,
        priority=policy_models.User.Priority.USER_ALIAS
    )
