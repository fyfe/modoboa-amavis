# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.db.models import Count

from modoboa.admin import models as admin_models
from modoboa.parameters import tools as param_tools

from modoboa_amavis.models.policy import User, Policy
from modoboa_amavis.utils import ConvertFrom, smart_bytes


def create_user_and_policy(name, priority, fullname, policy=None):
    if policy is None:
        policy = Policy.objects.create(policy_name=fullname[:32])

    user, created = User.objects.get_or_create(
        email=smart_bytes(name),
        defaults={
            "priority": priority,
            "fullname": fullname,
            "policy": policy,
        }
    )

    return user, created


def delete_user_and_policy(name, priority=None):
    # priority is used to filter aliases
    if priority:
        users = User.objects.filter(email=smart_bytes(name), priority=priority)
    else:
        users = User.objects.filter(email=smart_bytes(name))

    deleted_count, by_model_ = users.delete()

    # delete any unused Policy objects
    (
        Policy.objects
        .annotate(Count('user'))
        .filter(user__count=0)
        .delete()
    )

    return deleted_count


def rename_user_and_policy(old_name, new_name, fullname):
    user = User.objects.get(email=smart_bytes(old_name))
    user.email = smart_bytes(new_name)
    user.fullname = fullname
    user.save(update_fields=["email", "fullname"])
    user.policy.policy_name = fullname[:32]
    user.policy.save(update_fields=["policy_name"])


def create_catachall():
    """Create the catch all policy if it doesn't already exist."""
    user, created = create_user_and_policy(
        "@.", User.Priority.CATCHALL, "catchall"
    )
    if created:
        conf = dict(param_tools.get_global_parameters("modoboa_amavis"))
        user.policy.sa_username = conf["default_user"]
        user.policy.save(update_fields=["sa_username"])


def setup_domain_policy(domain):
    """Setup Amavis policy for a domain."""
    name = "@%s" % domain.name
    user, created_ = create_user_and_policy(
        name, User.Priority.DOMAIN, domain.name
    )
    user.policy.sa_username = name
    user.policy.save(update_fields=["sa_username"])


def setup_domain_alias_policy(domain_alias):
    """Setup Amavis policy for a domain alias."""
    name = "@%s" % domain_alias.name
    target_name = "@%s" % domain_alias.target.name
    target_user = User.objects.get(email=smart_bytes(target_name))
    create_user_and_policy(
        name, User.Priority.DOMAIN_ALIAS, domain_alias.name,
        policy=target_user.policy
    )


def setup_mailbox_policy(mailbox):
    """Setup Amavis policy for a mailbox."""
    name = mailbox.full_address
    user, created_ = create_user_and_policy(
        name, User.Priority.USER, mailbox.full_address
    )
    user.policy.sa_username = name
    user.policy.save(update_fields=["sa_username"])


def setup_mailbox_alias_policy(alias):
    """Setup Amavis policy for an alias recipient.

    FIXME: how to deal with distibution lists ?
    """
    if alias.address.startswith("@"):
        # domain aliases aren't created here
        return

    if alias.alias.internal:
        # don't create a policy for existing Mailbox
        return

    if alias.r_mailbox is None:
        # don't create a policy for external aliases
        return

    # link to the target mailbox policy
    target_name = smart_bytes(alias.address)
    target_user = User.objects.get(email=target_name)
    create_user_and_policy(
        alias.alias.address, User.Priority.USER_ALIAS, alias.alias.address,
        policy=target_user.policy
    )


def migrate_policy_setup():
    """Migrate from =< 1.1.3"""
    create_catachall()

    for domain in admin_models.Domain.objects.all():
        name = "@%s" % domain.name
        user, created = create_user_and_policy(
            name, User.Priority.DOMAIN, domain.name
        )
        if not created:
            # update existing user and policy
            user.priority = User.Priority.DOMAIN
            user.fullname = domain.name
            user.save(update_fields=["priority", "fullname"])
            user.policy.policy_name = domain.name[:32]
            user.policy.sa_username = name
            user.policy.save(update_fields=["policy_name", "sa_username"])

    # existing domain alias, mailbox and alias User and Policy objects can be
    # safely deleted and recreated.
    users_to_delete = [
        "@%s" % name
        for name in admin_models.DomainAlias.objects
                                .values_list("name", flat=True)
    ]
    users_to_delete += [
        "%s@%s" % (address, domain)
        for address, domain in admin_models.Mailbox.objects
                                           .values_list("address", "domain")
    ]
    users_to_delete += [
        address
        for address in admin_models.AliasRecipient.objects
                                   .values_list("address", flat=True)
    ]
    (
        User.objects
        .annotate(str_email=ConvertFrom("email"))
        .filter(str_email__in=users_to_delete)
        .delete()
    )

    # delete any unused Policy objects
    (
        Policy.objects
        .annotate(Count('user'))
        .filter(user__count=0)
        .delete()
    )

    for domain_alias in admin_models.DomainAlias.objects.all():
        setup_domain_alias_policy(domain_alias)

    for mailbox in admin_models.Mailbox.objects.all():
        setup_mailbox_policy(mailbox)

    for alias in admin_models.AliasRecipient.objects.all():
        setup_mailbox_alias_policy(alias)
