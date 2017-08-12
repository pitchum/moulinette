=================================================
Common LDAP operation (for YunoHost but not only)
=================================================

Moulinette is deeply integrated with LDAP which is used for a series of things
like:

* storing users
* storing domains (for users emails)
* SSO

This page document how to uses it on a programming side in YunoHost.

Getting access to LDAP in a command
===================================

To get access to LDAP you need to authenticate against it, for that you need to
declare you command with requiring authentication in the :ref:`actionsmap` this way:

::

    configuration:
        authenticate: all


Here is a complete example:

::

    somecommand:
        category_help: ..
        actions:

            ### somecommand_stuff()
            stuff:
                action_help: ...
                api: GET /...
                configuration:
                    authenticate: all

This will prompt the user for a password in CLI.

If you only need to **read** LDAP (and not modify it, for example by listing
domains), then you prevent the need for a password by using the
:file:`ldap-anonymous` authenticator this way:

::

    configuration:
        authenticate: all
        authenticator: ldap-anonymous


Once you have declared your command like that, your python function will
received the :file:`auth` object as first argument, it will be used to talk to
LDAP, so you need to declare your function this way:

::

    def somecommand_stuff(auth, ...):
        ...

Reading from LDAP
=================

Reading data from LDAP is done using the :file:`auth` object received as first
argument of the python function. To see how to get this object read the
previous section.

The API looks like this:

::

    auth.search(ldap_path, ldap_query)

This will return a list of dictionary with strings as keys and list as values.

You can also specify a list of attributes you want to access from LDAP using a list of string (on only one string apparently):

::

    auth.search(ldap_path, ldap_query, ['first_attribute', 'another_attribute'])

For example, if we request the user :file:`alice` with its :file:`homeDirectory`, this would look like this:

::

    auth.search('ou=users,dc=yunohost,dc=org', '(&(objectclass=person)(uid=alice))', ['homeDirectory', 'another_attribute'])

And as a result we will get:

::

    [{'homeDirectory': ['/home/alice']}]

Notice that even for a single result we get a **list** of result and that every
value in the dictionary is also a **list** of values. This is not really convenient and it would be better to have a real ORM, but for now we are stuck with that.

Apparently if we don't specify the list of attributes it seems that we get all attributes (need to be confirmed).

Reading users from LDAP
-----------------------

The user table (or I don't how you are supposed to call this thing in LDAP) is located at this path: :file:`ou=users,dc=yunohost,dc=org`

According to already existing code, the queries we uses are:

* :file:`'(&(objectclass=person)(!(uid=root))(!(uid=nobody)))'` to get all users (not that I've never encountered users with :file:`root` or :file:`nobody` uid in the ldap database, those might be there for historical reason)
* :file:`'(&(objectclass=person)(uid=%s))' % username` to access one user data

This give us the 2 following python calls:

::

    # all users
    auth.search('ou=users,dc=yunohost,dc=org', '(&(objectclass=person)(!(uid=root))(!(uid=nobody)))')

    # one user
    auth.search('ou=users,dc=yunohost,dc=org', '(&(objectclass=person)(uid=some_username))')


Apparently we could also access one user using the following path (and not query): :file:`uid=user_username,ou=users,dc=yunohost,dc=org` but I haven't test it.