*What a lovely idea !* :)

**Few points though:**

### Dafuq is dat moulinette ?
We decided to regroup all YunoHost related operations into a single program called "moulinette". This will allow us to entirely manipulate our YunoHost instances through a wonderful CLI. Additionally the web interface will just have to call the same "moulinette" functions. Magic power inside :p

### Important files
* `` parse_args `` File executed on function calling - i.e `` ./parse_args user create ``. Will be renamed `` yunohost `` when packaged.
* `` yunohost.py `` Contains all YunoHost functions likely to be shared between moulinette files. Also contains service connections classes (erk). Refers to "Service connections" paragraph.
* `` yunohost_*.py `` Files containing action functions. `` * `` is the category: user, domain, firewall, etc.

### How to add a function ?
1. Check if the action is already in the `` action_map `` dictionary in the `` parse_args `` file. If not, follow the dict documentation to add it.
2. Also check if the file `` yunohost_category.py `` is created in the working tree. If not, just create it (you may take example of `` yunohost_user.py `` file).
3. Add your function `` category_action() `` in this file - i.e `` user_create() ``

**Note:** `` category_action() `` takes one parameter plus an optional one : `` args `` and `` connections `` if connections were set. `` args `` contains the arguments passed to the command. Refers to `` action_map `` documentation for more informations.

### Service connections
The so called 'service connection' could actually be multiple things. It just is the resource used for a specific action: a file opening, a SQL or a LDAP connection. For example, I need to access LDAP base for YunoHost's user manipulations, so I have to declare it. It could be a file opening (for repositories for example).

Because of potential complexity of its operations, the moulinette has a specific way to handle connections. A connection is initialized once if the action is requiring it.
If you want to add a new connection (not yet implemented), you just have to put the connect and the disconnect method in `` connect_service() `` and `` disconnect_services() `` in the `` yunohost.py `` file. Then add your connection name to the action in the `` action_map `` dictionary.

We chose to make a class for some connections (i.e LDAP), in order to simplify some operations. Feel free to do the same.

**Note:** We could have used singleton classes. We probably need a Python expert to clarify this. :D

### Error handling
Moulinette has a unified way to handle errors. First, you need to import the ``YunoHostError`` exception:
`` from yunohost import YunoHostError ``

Then you need to raise errors like this:
`` raise YunoHostError(<ERROR CODE>, <MESSAGE>) ``

For example:
`` raise YunoHostError(125, _("Interrupted, user not created")) ``

**Note:** Standard error codes can be found in the ``YunoHostError`` class in `` yunohost.py `` file.

### Print results
Moulinette also have a unified way to print results. In fact we don't only print result for the CLI, but we also have to export the result in a JSON way.
Results are automatically printed OR exported, you don't have to print it yourself in the action's functions. Your function just need is to return results as a dictionary, for example:
`` return { 'Fullname' : 'Homer Simpson', 'Mail' : 'homer@simpson.org', 'Username' : 'hsimpson' } ``

### i18n
We will have to translate YunoHost, and we have already initialized i18n module in the moulinette. As a result, do not forget to put potentially translated strings into `` _() `` function. For example:
`` raise YunoHostError(125, _("Interrupted, user not created")) ``

### Git is pissing me off !
OK, this is the workflow !

**For gitlab:**
Development is handle with git branches and you have your own (i.e dev_beudbeud).
```
git clone git@dev.yunohost.org:moulinette.git
git checkout -b dev_beudbeud ``
git rebase origin/dev 
```

Do your modifications, then :
```
git commit -am 'My commit message'
git pull origin dev (merge manually if conflicts)
git push origin dev_beudbeud 
```

Then you could ask for a 'merge request' in gitlab.

**For github (here):**
Development is handle with forked repos and you have your own (i.e beudbeud/moulinette).
```
git clone https://github.com/beudbeud/moulinette.git ``
git checkout -b dev
git rebase origin/dev 
```

Do your modifications, then:
```
git commit -am 'My commit message'
git remote add vanilla https://github.com/YunoHost/moulinette.git
git pull vanilla dev (merge manually if conflicts)
git push origin dev
```

Then you could ask for a 'pull request' in github.
